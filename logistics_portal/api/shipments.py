"""Shipment tracking portal — the order's clock, from confirmation to the door.

The team that watches orders learned about every problem after it had already
happened. This gives them the clock instead: the moment an order is confirmed
it is promised to a WAVE out of the building, and once it leaves it is promised
to the customer within that city's own measured time. An order that is going
to miss either one says so while there is still time to act.

Two facts from production shaped every decision here (measured 2026-09-13):

  The stage timestamp fields are empty — `custom_picked_at` and
  `custom_shipped_at` are NULL on all 10,108 orders of the last month, because
  they are stamped off `custom_logistics_status`, which this codebase already
  distrusts enough to derive its board from documents instead. So the clock is
  read from DOCUMENTS: the Version row that set Confirmed (79% of orders), the
  Pick List (95%), the Delivery Note (95%) and the Shipment (94%).

  The warehouse is not the delay. Picking to parcel-closed runs 0.9h at the
  median and handover 3.6h, but CONFIRMED TO PICK LIST runs 10 hours — 57% of
  all in-house time is an order sitting confirmed that nobody has started.
  That is the number this portal exists to move, so it is the first thing on
  the board and the first thing that turns red.
"""
import json
import re

import frappe
from frappe.utils import now_datetime

_CO = "Justyol Morocco"
_SETTINGS_KEY = "lp_ship_settings"

# Seeded from what the floor ACTUALLY does, not from what anyone believes it
# does: the manifest hours cluster at 11:00-12:00 and 15:00-16:00 Morocco time,
# so the afternoon wave really runs about ninety minutes later than the "2pm
# cut-off" everyone quotes. The team can move these; they start honest.
_DEFAULTS = {
    "waves": [
        {"id": "am", "cutoff": "06:00", "out": "11:00"},
        {"id": "pm", "cutoff": "13:00", "out": "15:30"},
    ],
    # Rest days as Python weekday numbers (Mon=0 … Sun=6).
    "restDays": [6],
    # Carrier promise per city, in calendar days from handover. Seeded with the
    # measured 75th percentile per city, so the promise is one the carrier has
    # actually been keeping three times in four rather than an aspiration.
    "cityDays": {
        "CASABLANCA": 3, "AGADIR": 3, "MEKNES": 3, "KENITRA": 3,
        "TANGER": 4, "FES": 4, "MARRAKECH": 4, "RABAT": 4,
        "SALE": 5, "TEMARA": 5, "OUJDA": 5, "TETOUAN": 4,
    },
    "defaultCityDays": 5,
    # A parcel with the carrier this long is not late, it is lost.
    "chaseDays": 5,
    # Once chased, a parcel leaves the chase list for this many hours.
    "chaseSnoozeH": 24,
    # Section leads: emails that may change these settings and run the
    # feedback engine without a manager role (same pattern as the CS lane).
    "admins": [],
}

_TERMINAL_OK = ("Delivered",)
_TERMINAL_BAD = ("Return", "Returned", "Not Delivered", "Failed Attempt", "Delivery Exception")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def _norm_waves(waves):
    """Zero-padded times, earliest cut-off first — wave_for relies on
    waves[0] being the first wave of the day, whatever was saved."""
    out = []
    for i, w in enumerate(waves or []):
        if not isinstance(w, dict):
            continue
        ch, cm = _hhmm(w.get("cutoff"), (None, None))
        oh, om = _hhmm(w.get("out"), (None, None))
        if ch is None or oh is None:
            continue
        out.append({"id": str(w.get("id") or f"w{i + 1}")[:8],
                    "cutoff": "%02d:%02d" % (ch, cm), "out": "%02d:%02d" % (oh, om)})
    return sorted(out, key=lambda w: w["cutoff"]) or json.loads(json.dumps(_DEFAULTS["waves"]))


def get_settings():
    raw = frappe.db.get_default(_SETTINGS_KEY)
    out = json.loads(json.dumps(_DEFAULTS))
    if raw:
        try:
            saved = json.loads(raw)
            if isinstance(saved, dict):
                out.update(saved)
        except Exception:
            pass
    out["waves"] = _norm_waves(out.get("waves"))
    return out


def _gate():
    """Who works this portal. The tracking team owns it; managers oversee it."""
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("tracking", "manager", "cs", "dispatcher"):
        frappe.throw("lp:shipTeamOnly", frappe.PermissionError)
    return role


def _is_lead():
    """A manager, or a tracking-portal user named in the section's admins list.
    Being on the team is not being its lead."""
    from logistics_portal.api.auth import resolve_role
    from logistics_portal.api.permissions import is_ops_admin
    if is_ops_admin():
        return True
    if resolve_role(frappe.session.user) not in ("tracking", "cs", "dispatcher"):
        return False
    return frappe.session.user in (get_settings().get("admins") or [])


def _admin_gate():
    if not _is_lead():
        frappe.throw("lp:leadsOnly", frappe.PermissionError)


@frappe.whitelist()
def settings():
    _gate()
    from logistics_portal.api.permissions import is_ops_admin
    s = get_settings()
    s["isAdmin"] = _is_lead()
    s["isOpsAdmin"] = bool(is_ops_admin())
    return s


def _hhmm_ok(v):
    try:
        h, m = str(v).split(":")[:2]
        return 0 <= int(h) < 24 and 0 <= int(m) < 60
    except Exception:
        return False


def _clean_settings(cur, payload):
    """Every field the board reads is coerced here, so a blank number box or
    a stringy day list can never take the board down for everyone."""
    from logistics_portal.api.city import canon_city
    if "waves" in payload and isinstance(payload["waves"], list):
        waves = [w for w in payload["waves"]
                 if isinstance(w, dict) and _hhmm_ok(w.get("cutoff")) and _hhmm_ok(w.get("out"))]
        if waves:
            cur["waves"] = _norm_waves(waves)
    if "restDays" in payload and isinstance(payload["restDays"], list):
        days = set()
        for d in payload["restDays"]:
            try:
                d = int(d)
            except Exception:
                continue
            if 0 <= d <= 6:
                days.add(d)
        if len(days) < 7:
            cur["restDays"] = sorted(days)
    if "cityDays" in payload and isinstance(payload["cityDays"], dict):
        cd = {}
        for k, v in payload["cityDays"].items():
            try:
                n = int(v)
            except Exception:
                continue
            key = canon_city(str(k))
            if key and 1 <= n <= 20:
                cd[key] = n
        cur["cityDays"] = cd
    for k, lo, hi in (("defaultCityDays", 1, 20), ("chaseDays", 1, 30), ("chaseSnoozeH", 1, 168)):
        if k in payload:
            try:
                cur[k] = min(max(int(payload[k]), lo), hi)
            except Exception:
                pass
    return cur


@frappe.whitelist(methods=["POST"])
def save_settings(payload=None):
    _admin_gate()
    if isinstance(payload, str):
        payload = json.loads(payload or "{}")
    if not isinstance(payload, dict):
        frappe.throw("lp:badPayload")
    cur = _clean_settings(get_settings(), payload)
    # Only a manager may decide who the leads are.
    if "admins" in payload and isinstance(payload["admins"], list):
        from logistics_portal.api.permissions import is_ops_admin
        if not is_ops_admin():
            frappe.throw("lp:managerOnly", frappe.PermissionError)
        cur["admins"] = [str(u).strip().lower() for u in payload["admins"] if str(u).strip()][:30]
    frappe.db.set_default(_SETTINGS_KEY, json.dumps(cur))
    frappe.db.commit()
    invalidate_cache()
    return {"ok": True, "settings": cur}


# ---------------------------------------------------------------------------
# The clock
# ---------------------------------------------------------------------------

def _hhmm(s, default=(0, 0)):
    try:
        h, m = str(s).split(":")[:2]
        return int(h), int(m)
    except Exception:
        return default


def _next_working(dt, rest_days):
    """Roll a date forward past the days the warehouse does not ship."""
    guard = 0
    while dt.weekday() in rest_days and guard < 14:
        dt = frappe.utils.add_days(dt, 1)
        guard += 1
    return dt


def wave_for(confirmed_at, cfg=None):
    """The wave an order confirmed at this moment is promised to leave in.

    Deliberately a WAVE and not a flat number of hours: the floor ships in two
    bursts, so "you have 14 hours" means nothing to anyone while "this missed
    the 15:30 van" is an instruction. Returns (wave_id, due_datetime).
    """
    cfg = cfg or get_settings()
    waves = cfg.get("waves") or _DEFAULTS["waves"]
    rest = set(cfg.get("restDays") or [])
    if not confirmed_at:
        return None, None
    day = confirmed_at.date()
    mins = confirmed_at.hour * 60 + confirmed_at.minute
    if day.weekday() in rest:
        # Confirmed on a day nothing ships: no cut-off applies, it is simply
        # promised to the first wave of the next working day.
        w = waves[0]
        oh, om = _hhmm(w.get("out"))
        d = _next_working(day, rest)
        return w.get("id"), frappe.utils.get_datetime("%s %02d:%02d:00" % (d, oh, om))
    for w in waves:
        ch, cm = _hhmm(w.get("cutoff"))
        if mins <= ch * 60 + cm:
            oh, om = _hhmm(w.get("out"))
            d = _next_working(day, rest)
            due = frappe.utils.get_datetime(
                "%s %02d:%02d:00" % (d, oh, om))
            if due >= confirmed_at:
                return w.get("id"), due
    # Past every cut-off: the first wave of the next working day.
    w = waves[0]
    oh, om = _hhmm(w.get("out"))
    d = _next_working(frappe.utils.add_days(day, 1), rest)
    return w.get("id"), frappe.utils.get_datetime("%s %02d:%02d:00" % (d, oh, om))


def carrier_due(handed_at, city, cfg=None):
    """When the customer was promised the parcel, skipping the rest days."""
    cfg = cfg or get_settings()
    if not handed_at:
        return None
    from logistics_portal.api.city import canon_city
    try:
        days = int((cfg.get("cityDays") or {}).get(
            canon_city(city), cfg.get("defaultCityDays") or 5))
    except Exception:
        days = 5
    days = min(max(days, 1), 30)
    rest = set(cfg.get("restDays") or [])
    d = handed_at.date()
    added, guard = 0, 0
    while added < days and guard < 40:
        d = frappe.utils.add_days(d, 1)
        guard += 1
        if d.weekday() not in rest:
            added += 1
    return frappe.utils.get_datetime("%s %02d:%02d:00" % (d, handed_at.hour,
                                                         handed_at.minute))


_BOARD_SELECT = """
SELECT so.name, so.customer_name AS customer, so.grand_total AS value,
       so.creation AS created, so.custom_sales_status AS sales_status,
       so.status AS so_status, so.custom_logistics_status AS lstat,
       so.custom_track_shipment_status AS so_track,
       NULLIF(so.custom_tracking_number, '') AS so_awb, so.modified AS modified,
       COALESCE(NULLIF(so.custom_shipping_city, ''), addr.city, '') AS city,
       COALESCE(NULLIF(so.custom_customer_phone, ''), so.custom_shipping_phone) AS phone,
       cf.t AS confirmed_at, pl.t AS picklist_at, dn.t AS dn_at,
       sh.t AS handed_at, dn.awb AS awb, trk.st AS track,
       cw.lab_t AS labeled_at, cw.hub_t AS hub_at,
       ev.content AS ev_text, cw.ev_t AS ev_at,
       so.custom_tracking_url AS track_url,
       so.custom_delivered_at AS delivered_at
FROM `tabSales Order` so
LEFT JOIN `tabAddress` addr
       ON addr.name = COALESCE(NULLIF(so.shipping_address_name, ''), so.customer_address)
LEFT JOIN (SELECT docname, MIN(creation) t FROM `tabVersion`
           WHERE ref_doctype = 'Sales Order'
             AND data LIKE '%%"custom_sales_status",%%,"Confirmed"]%%'
             AND creation >= DATE_SUB(NOW(), INTERVAL %(vdays)s DAY)
           GROUP BY docname) cf ON cf.docname = so.name
LEFT JOIN (SELECT pli.sales_order so_name, MIN(p.creation) t
           FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name = pli.parent
           WHERE p.docstatus < 2 GROUP BY pli.sales_order) pl ON pl.so_name = so.name
LEFT JOIN (SELECT dni.against_sales_order so_name, MIN(d.creation) t,
                  MAX(COALESCE(NULLIF(d.custom_awb, ''), '')) awb
           FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name = dni.parent
           WHERE d.docstatus < 2 AND d.is_return = 0
           GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name
LEFT JOIN (SELECT dni2.against_sales_order so_name, MIN(s.creation) t
           FROM `tabShipment Delivery Note` sdn JOIN `tabShipment` s ON s.name = sdn.parent
           JOIN `tabDelivery Note Item` dni2 ON dni2.parent = sdn.delivery_note
           WHERE s.docstatus = 1
           GROUP BY dni2.against_sales_order) sh ON sh.so_name = so.name
LEFT JOIN (SELECT dni3.against_sales_order so_name,
                  MAX(d3.custom_track_shipment_status) st
           FROM `tabDelivery Note Item` dni3 JOIN `tabDelivery Note` d3 ON d3.name = dni3.parent
           WHERE d3.docstatus < 2 AND d3.is_return = 0
           GROUP BY dni3.against_sales_order) trk ON trk.so_name = so.name
LEFT JOIN (SELECT reference_name,
                  MIN(CASE WHEN content LIKE 'Newly created parcel%%' THEN creation END) AS lab_t,
                  MIN(CASE WHEN content LIKE 'Shipped to destination hub%%'
                             OR content LIKE 'The parcel is present on Hub%%'
                             OR content LIKE 'Out for delivery%%'
                             OR content LIKE 'Package Delivered%%' THEN creation END) AS hub_t,
                  MAX(creation) AS ev_t
           FROM `tabComment`
           WHERE reference_doctype = 'Sales Order' AND comment_type = 'Comment'
             AND creation >= DATE_SUB(NOW(), INTERVAL %(vdays)s DAY)
             AND (content LIKE 'Newly created%%' OR content LIKE 'Shipped to%%'
                  OR content LIKE 'The parcel%%' OR content LIKE 'Out for%%'
                  OR content LIKE 'Package%%' OR content LIKE 'The driver%%'
                  OR content LIKE 'Customer unreachable%%' OR content LIKE 'Customer cancelled%%'
                  OR content LIKE 'The customer has cancelled%%' OR content LIKE 'Cancelled on site%%'
                  OR content LIKE 'Justyol has requested%%')
           GROUP BY reference_name) cw ON cw.reference_name = so.name
LEFT JOIN `tabComment` ev ON ev.reference_doctype = 'Sales Order' AND ev.reference_name = so.name
                          AND ev.comment_type = 'Comment' AND ev.creation = cw.ev_t
"""

_BOARD_WHERE = """
WHERE so.company = %(co)s AND so.docstatus = 1
  AND so.custom_sales_status = 'Confirmed'
  AND so.status NOT IN ('Closed', 'Cancelled')
  AND so.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)
"""


_FRESH_S = 60        # older than this: serve it, refresh in the background
_KEEP_S = 900        # after this the cache is gone and a request computes inline


def _cached(key):
    try:
        v = frappe.cache().get_value(key, expires=True)
    except Exception:
        return None
    return v if isinstance(v, dict) and "at" in v else None


def _age_s(entry):
    try:
        return (now_datetime() - frappe.utils.get_datetime(entry["at"])).total_seconds()
    except Exception:
        return _KEEP_S


def _store(key, body):
    try:
        frappe.cache().set_value(key, dict(body, at=str(now_datetime())[:19]), expires_in_sec=_KEEP_S)
    except Exception:
        pass


def _refresh_later(days):
    """Ask a worker to rebuild the clock; one request per 45 s is enough."""
    days = int(days)
    try:
        if not frappe.cache().set(f"lp_ship_refresh_lock:{days}", 1, nx=True, ex=45):
            return
        frappe.enqueue("logistics_portal.api.shipments.refresh_cache", queue="short",
                       timeout=180, days=days, enqueue_after_commit=False)
    except Exception:
        pass


def _rows(days=30):
    """The raw clock rows.

    Measured on prod 2026-09-14: 2.8 s of SQL for 8,030 rows, and the first
    request of every minute paid it. Now the last answer is served for up to
    fifteen minutes and a worker rebuilds it once it is a minute old — a
    request only computes inline when nothing is cached at all (a restart).
    """
    days = int(days)
    hit = _cached(f"lp_ship_rows:{days}")
    if hit is not None:
        if _age_s(hit) > _FRESH_S:
            _refresh_later(days)
        return hit["rows"]
    return _refresh_rows(days)


def _refresh_rows(days):
    # A confirmation, a label or a carrier scan can only come AFTER the order
    # was created, so the witness tables need no wider window than the orders.
    rows = frappe.db.sql(_BOARD_SELECT + _BOARD_WHERE,
                         {"co": _CO, "days": days, "vdays": days + 2}, as_dict=True)
    _store(f"lp_ship_rows:{days}", {"rows": rows})
    return rows


def _shaped(days, cfg, now):
    """Every row shaped for the clock, shared by every screen and the cron.

    Shaping 8k rows costs ~0.6 s in Python, so it is cached like the rows and
    rebuilt by the same worker job. The rows carry the minute they were shaped
    at; a promise measured in hours is not hurt by a minute or two of that.
    """
    days = int(days)
    hit = _cached(f"lp_ship_shaped:{days}")
    if hit is not None:
        if _age_s(hit) > _FRESH_S:
            _refresh_later(days)
        return hit["rows"]
    return _refresh_shaped(days, cfg, now)


def _refresh_shaped(days, cfg, now):
    rows = [_shape(r, cfg, now) for r in _rows(days)]
    _store(f"lp_ship_shaped:{days}", {"rows": rows, "now": str(now)[:16]})
    return rows


def refresh_cache(days=30):
    """Worker job (and the cron's first step): rebuild rows, shaped rows and
    the blocked screen for one window, so no request ever pays for them."""
    from logistics_portal.api import clock
    days = int(days)
    cfg = get_settings()
    now = clock.floor_now()
    _refresh_rows(days)
    _refresh_shaped(days, cfg, now)
    if days == 30:
        _refresh_blocked(days, cfg, now)
    return {"ok": True, "days": days}


def invalidate_cache():
    """After a settings change: forget the shaped answers (they carry the old
    promises) and rebuild in the background; the raw rows are still good."""
    try:
        for pat in ("lp_ship_shaped:", "lp_ship_blocked:", "lp_ship_tuner:"):
            frappe.cache().delete_keys(pat)   # wildcard delete, site-prefixed once
    except Exception:
        pass
    _refresh_later(30)


_CARRIER_MOVING = ("In Transit", "Out For Delivery", "Picked up", "Picked Up")


def _stage_of(r):
    """Where the parcel is, read from three witnesses that do not all speak
    for every order.

    Audited 2026-09-13 on the 73 rows of the blocked screen: 12 were wrong,
    and every one of them was an order the DOCUMENTS could not describe —
    exchange (-ex) and J- orders get their carrier label straight from the
    Sales Order and never see a Delivery Note; a handful of parcels sit on a
    DRAFT Delivery Note with a label already printed; one was Closed. The
    order's own status stamps (custom_logistics_status, tracking status,
    delivered_at) and the carrier's webhook comments ("Newly created
    parcel", "present on Hub", "Out for delivery", "Package Delivered")
    describe exactly those. So: terminal states first, then the carrier,
    then the label, then the pick list, then nothing.

    Returns (stage, owner, handed_at_raw, closed_at_raw).
    """
    track = r.track or r.so_track or ""
    lstat = r.lstat or ""
    labeled = r.dn_at or r.labeled_at
    has_label = bool(r.awb or r.so_awb or labeled or lstat in ("Label Generated", "Label Printed"))

    if track in _TERMINAL_OK or r.delivered_at or lstat == "Delivered":
        return "delivered", "", r.handed_at or r.hub_at or labeled, labeled
    if track in _TERMINAL_BAD or lstat == "Returned":
        return "failed", "tracking", r.handed_at or r.hub_at or labeled, labeled
    if r.handed_at or r.hub_at or lstat == "Shipped" or track in _CARRIER_MOVING:
        # Manifest first; else the carrier's first scan; else the label —
        # the closest honest moment when the manifest was never written.
        return "with_carrier", "carrier", r.handed_at or r.hub_at or labeled or r.modified, labeled
    if has_label:
        return "to_hand_over", "dispatcher", None, labeled or r.modified
    if r.picklist_at:
        return "picking", "floor", None, None
    # The leg that holds 57% of the in-house clock.
    return "to_pick", "dispatcher", None, None


def _shape(r, cfg, now):
    """One order's clock: where it is, who owns it, and what it owes."""
    from logistics_portal.api import clock
    conf = clock.to_floor(r.confirmed_at) if r.confirmed_at else \
        (clock.to_floor(r.created) if r.created else None)
    stage, owner, handed, closed_raw = _stage_of(r)
    handed = clock.to_floor(handed) if handed else None
    track = (r.track or r.so_track or "")

    wave_id, wave_due = (None, None)
    due, late_min = None, 0
    kept = None
    if stage in ("to_pick", "picking", "to_hand_over"):
        wave_id, wave_due = wave_for(conf, cfg)
        due = wave_due
    elif stage == "with_carrier":
        due = carrier_due(handed, r.city, cfg)
    elif stage == "delivered" and handed and r.delivered_at:
        # The promise, judged after the fact: did the door come in time?
        d = carrier_due(handed, r.city, cfg)
        kept = bool(d and clock.to_floor(r.delivered_at) <= d)
    if due:
        late_min = int((now - due).total_seconds() / 60)

    picked = clock.to_floor(r.picklist_at) if r.picklist_at else None
    closed = clock.to_floor(closed_raw) if closed_raw else None
    delivered = clock.to_floor(r.delivered_at) if r.delivered_at else None
    return {
        "order": r.name, "customer": r.customer or "", "city": (r.city or "").strip(),
        "phone": r.phone or "", "value": round(float(r.value or 0)),
        "stage": stage, "owner": owner, "awb": r.awb or r.so_awb or "", "track": track,
        "confirmedAt": str(conf)[:16] if conf else "",
        "pickedAt": str(picked)[:16] if picked else "",
        "closedAt": str(closed)[:16] if closed else "",
        "handedAt": str(handed)[:16] if handed else "",
        "deliveredAt": str(delivered)[:16] if delivered else "",
        "kept": kept,
        "wave": wave_id, "dueAt": str(due)[:16] if due else "",
        "lateMin": late_min,
        "late": bool(due and late_min > 0 and stage not in ("delivered", "failed")),
        "ageH": int((now - conf).total_seconds() / 3600) if conf else 0,
        # The carrier's last word, for the leg where it is the only news.
        "lastEvent": _clean_text(r.ev_text)[:90] if r.ev_text else "",
        "lastEventAt": str(clock.to_floor(r.ev_at))[:16] if r.ev_at else "",
        # With no event, the age that matters is how long since we handed it.
        "eventAgeH": int((now - clock.to_floor(r.ev_at)).total_seconds() / 3600) if r.ev_at
                     else (int((now - handed).total_seconds() / 3600) if handed else None),
        "verdict": _event_kind(r.ev_text, track, stage),
        "trackUrl": r.track_url or "",
    }


def _clean_text(text):
    """The carrier writes HTML entities into its comments ('Call &amp; SMS')."""
    import html as _html
    return _html.unescape(frappe.utils.strip_html(text or "")).strip()


def _event_kind(text, track="", stage=""):
    """The carrier's last event, as one of a handful of situations the
    chase call starts from. Same vocabulary as the rescue lane.

    Measured 2026-09-13: 824 of 1,000 parcels 'with the carrier' had no
    carrier comment at all, and 636 of those were still 'Pending' — the
    label exists, the manifest was written, and the carrier never scanned
    the parcel. That is not 'no news'; it is the loudest news there is.
    """
    t = (text or "")
    if not t:
        if stage != "with_carrier":
            return ""
        return {"Pending": "noscan", "In Transit": "hub", "Out For Delivery": "ofd",
                "Picked up": "hub", "Picked Up": "hub"}.get(track or "", "none")
    if t.startswith(("Customer cancelled", "The customer has cancelled", "Cancelled on site",
                     "Cancellation Reason", "Justyol has requested")):
        return "cancelled"
    if t.startswith("Customer unreachable"):
        return "unreachable"
    if t.startswith("The driver"):
        return "appointment"
    if t.startswith("Out for"):
        return "ofd"
    if t.startswith(("The parcel", "Shipped to")):
        return "hub"
    if t.startswith("Package"):
        return "delivered"
    if t.startswith("Newly created"):
        return "label"
    return "other"


@frappe.whitelist()
def board(view="live", days=30, limit=300):
    """The live clock. view: live | late | wave | carrier | blocked."""
    _gate()
    from logistics_portal.api import clock
    cfg = get_settings()
    now = clock.floor_now()
    days = min(max(int(days or 30), 1), 90)
    limit = min(max(int(limit or 300), 1), 1000)

    rows = _shaped(days, cfg, now)
    live = [r for r in rows if r["stage"] not in ("delivered", "failed")]
    in_house = [r for r in live if r["stage"] in ("to_pick", "picking", "to_hand_over")]
    carrier = [r for r in live if r["stage"] == "with_carrier"]

    # A parcel the team already chased today leaves the chase list until the
    # snooze runs out; the mark lives on the order as a comment.
    marks = _marks([r["order"] for r in carrier])
    snooze = dict(_MARK_SNOOZE_H, chased=int(cfg.get("chaseSnoozeH") or 24))
    for r in carrier:
        kind, at = marks.get(r["order"], ("", None))
        r["mark"] = kind
        r["markAt"] = str(clock.to_floor(at))[:16] if at else ""
        r["chasedAt"] = r["markAt"] if kind == "chased" else ""
        r["snoozed"] = bool(kind and at and (now - clock.to_floor(at)).total_seconds() < snooze.get(kind, 24) * 3600)
    chase_h = int(cfg.get("chaseDays") or 5) * 24
    week = str(frappe.utils.add_days(now, -7))[:16]
    judged = [r for r in rows if r["stage"] == "delivered" and r["kept"] is not None
              and r["deliveredAt"] >= week]
    counts = {
        "kept7d": {"n": len(judged), "ok": sum(1 for r in judged if r["kept"])},
        "failed": sum(1 for r in rows if r["stage"] == "failed"),
        "live": len(live),
        "inHouse": len(in_house),
        "lateInHouse": sum(1 for r in in_house if r["late"]),
        "toPick": sum(1 for r in in_house if r["stage"] == "to_pick"),
        "carrier": len(carrier),
        "lateCarrier": sum(1 for r in carrier if r["late"]),
        "chase": sum(1 for r in carrier
                     if r["handedAt"] and r["ageH"] and r["lateMin"] > chase_h * 60 and not r["snoozed"]),
    }

    if view == "late":
        sel = [r for r in in_house if r["late"]]
    elif view == "to_pick":
        sel = [r for r in in_house if r["stage"] == "to_pick"]
    elif view == "late_carrier":
        sel = [r for r in carrier if r["late"]]
    elif view == "chase":
        sel = [r for r in carrier if r["lateMin"] > chase_h * 60 and not r["snoozed"]]
    elif view == "carrier":
        sel = carrier
    elif view == "wave":
        sel = in_house
    else:
        sel = live
    # Most urgent first: whoever is furthest past their promise, then whoever
    # is closest to it. A board sorted by date buries exactly the wrong rows.
    sel.sort(key=lambda r: (-r["lateMin"] if r["late"] else 10 ** 6 - r["lateMin"]))
    facets = None
    if view in ("late_carrier", "chase", "carrier"):
        from logistics_portal.api.city import canon_city
        cities, events = {}, {}
        for r in sel:
            ck = canon_city(r["city"]) or "—"
            c = cities.setdefault(ck, {"city": ck, "n": 0, "oldestH": 0})
            c["n"] += 1
            c["oldestH"] = max(c["oldestH"], r["lateMin"] // 60)
            ek = r.get("verdict") or "none"
            e = events.setdefault(ek, {"kind": ek, "n": 0, "oldestH": 0})
            e["n"] += 1
            e["oldestH"] = max(e["oldestH"], (r.get("eventAgeH") or 0))
        facets = {"cities": sorted(cities.values(), key=lambda x: -x["n"])[:10],
                  "events": sorted(events.values(), key=lambda x: -x["n"])}
    return {"view": view, "counts": counts, "rows": sel[:limit],
            "total": len(sel), "waves": cfg.get("waves"), "facets": facets,
            "nextWave": _next_wave(in_house, cfg, now),
            "waveBuckets": _wave_buckets(in_house),
            "now": str(now)[:16]}


# What the team can conclude about a parcel the carrier is silent on. Each
# mark is a comment on the order with a fixed prefix; the chase list hides
# the parcel for the mark's snooze, then brings it back if nothing moved.
_MARKS = {
    "chased": "Tracking: chased carrier",
    "confirmed": "Tracking: carrier confirmed it has the parcel",
    "found": "Tracking: found in the warehouse — needs a new handover",
    "lost": "Tracking: reported lost to the carrier",
}
_MARK_SNOOZE_H = {"chased": 24, "confirmed": 48, "found": 168, "lost": 168}


def _marks(orders):
    """Latest Tracking mark per order: (kind, when)."""
    if not orders:
        return {}
    ph = ", ".join(["%s"] * len(orders))
    out = {}
    for name, content, at in frappe.db.sql(
            f"""SELECT c.reference_name, c.content, c.creation FROM `tabComment` c
                JOIN (SELECT reference_name, MAX(creation) t FROM `tabComment`
                      WHERE reference_doctype = 'Sales Order' AND comment_type = 'Comment'
                        AND creation >= DATE_SUB(NOW(), INTERVAL 14 DAY)
                        AND content LIKE 'Tracking: %%' AND content NOT LIKE 'Tracking: feedback%%'
                        AND reference_name IN ({ph})
                      GROUP BY reference_name) m
                  ON m.reference_name = c.reference_name AND m.t = c.creation
                WHERE c.reference_doctype = 'Sales Order'""", tuple(orders)):
        kind = next((k for k, p in _MARKS.items() if (content or "").startswith(p)), "")
        if kind:
            out[name] = (kind, at)
    return out


def _mark_one(order, kind, note):
    doc = frappe.get_doc("Sales Order", order)
    doc.add_comment("Comment", _MARKS[kind] + (f" — {note}" if note else "")
                    + f" · by {frappe.session.user}")


@frappe.whitelist(methods=["POST"])
def mark(order, outcome="chased", note=None):
    """One conclusion about one parcel the carrier is silent on."""
    _gate()
    if outcome not in _MARKS:
        frappe.throw("lp:badPayload")
    if not frappe.db.exists("Sales Order", {"name": order, "company": _CO}):
        frappe.throw("lp:unknownRow")
    _mark_one(order, outcome, (note or "").strip()[:140])
    frappe.db.commit()
    if outcome == "found":
        _emit("found_in_building", {"n": 1, "order": order}, "warning", cooldown_h=1,
              order=order, audience="dispatcher")
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def bulk_mark(orders=None, outcome="chased", note=None):
    """The same conclusion for a whole hub's worth of parcels."""
    _gate()
    if isinstance(orders, str):
        orders = json.loads(orders or "[]")
    if outcome not in _MARKS:
        frappe.throw("lp:badPayload")
    orders = [str(o).strip() for o in (orders or []) if str(o).strip()][:200]
    note = (note or "").strip()[:140]
    done = 0
    for o in orders:
        if frappe.db.exists("Sales Order", {"name": o, "company": _CO}):
            _mark_one(o, outcome, note)
            done += 1
    frappe.db.commit()
    if outcome == "found" and done:
        _emit("found_in_building", {"n": done, "order": orders[0]}, "warning", cooldown_h=1,
              order=orders[0] if done == 1 else None, audience="dispatcher")
    return {"ok": True, "done": done}


@frappe.whitelist(methods=["POST"])
def chase(order, note=None):
    """Kept for the older client: the 'chased' mark."""
    return mark(order, "chased", note)


def _wave_buckets(in_house):
    buckets = {}
    for r in in_house:
        key = r["dueAt"][:16] or "—"
        b = buckets.setdefault(key, {"dueAt": key, "wave": r["wave"], "n": 0,
                                     "late": 0, "toPick": 0, "picking": 0,
                                     "ready": 0, "value": 0})
        b["n"] += 1
        b["value"] += r["value"]
        if r["late"]:
            b["late"] += 1
        if r["stage"] == "to_pick":
            b["toPick"] += 1
        elif r["stage"] == "picking":
            b["picking"] += 1
        else:
            b["ready"] += 1
    return sorted(buckets.values(), key=lambda b: b["dueAt"])


def _next_wave(in_house, cfg, now):
    """The wave about to leave, and how ready the building is for it."""
    waves = cfg.get("waves") or _DEFAULTS["waves"]
    rest = set(cfg.get("restDays") or [])
    day = _next_working(now.date(), rest)
    due = None
    for w in waves:
        oh, om = _hhmm(w.get("out"))
        cand = frappe.utils.get_datetime("%s %02d:%02d:00" % (day, oh, om))
        if cand > now:
            due, wid = cand, w.get("id")
            break
    if due is None:
        w = waves[0]
        oh, om = _hhmm(w.get("out"))
        d = _next_working(frappe.utils.add_days(day, 1), rest)
        due, wid = frappe.utils.get_datetime("%s %02d:%02d:00" % (d, oh, om)), w.get("id")
    key = str(due)[:16]
    mine = [r for r in in_house if r["dueAt"] == key]
    return {"id": wid, "dueAt": key,
            "minutes": int((due - now).total_seconds() / 60),
            "n": len(mine),
            "ready": sum(1 for r in mine if r["stage"] == "to_hand_over"),
            "picking": sum(1 for r in mine if r["stage"] == "picking"),
            "toPick": sum(1 for r in mine if r["stage"] == "to_pick")}


@frappe.whitelist()
def wave_board(days=7):
    """Today's waves: what each one has to carry, and what is going to miss."""
    _gate()
    from logistics_portal.api import clock
    cfg = get_settings()
    now = clock.floor_now()
    days = min(max(int(days or 7), 1), 90)
    rows = _shaped(days, cfg, now)
    in_house = [r for r in rows if r["stage"] in ("to_pick", "picking", "to_hand_over")]
    return {"waves": _wave_buckets(in_house), "now": str(now)[:16], "config": cfg.get("waves")}


# ---------------------------------------------------------------------------
# Blocked: orders that cannot move, and the one thing each is waiting on.
#
# The board says an order is late; this says WHY, in the words of the fix.
# A short shelf, a city the carrier cannot read, a label that never came back
# — each already has a screen that repairs it, so every row here carries the
# door to that screen. The list is computed over the live in-house set only:
# a parcel with the carrier is not blocked, it is on its way or it is lost,
# and both of those are the board's job.
# ---------------------------------------------------------------------------

def _blockers(rows):
    """Annotate in-house rows with their blockers. One pass, shared lookups."""
    from logistics_portal.api.city import canon_city, _accepted_cities, _has_arabic
    from logistics_portal.api.picking import availability
    from logistics_portal.api.short_shelf import active as short_active

    if not rows:
        return
    names = [r["order"] for r in rows]
    ph = ", ".join(["%s"] * len(names))
    lines = {}
    for l in frappe.db.sql(
            f"""SELECT parent, item_code, qty FROM `tabSales Order Item`
                WHERE parent IN ({ph})""", tuple(names), as_dict=True):
        lines.setdefault(l.parent, []).append((l.item_code, float(l.qty or 0)))
    codes = list({c for ls in lines.values() for c, _ in ls})
    # The one availability contract (reservations decide who, totals decide
    # how many) — a private total here would disagree with the pick board.
    _t, _s, free = availability(codes) if codes else ({}, {}, lambda o, c: 0.0)
    short = {}
    try:
        for (it, wh) in short_active().keys():
            short.setdefault(it, wh)
    except Exception:
        pass
    accepted = set()
    try:
        accepted = {canon_city(c) for c in _accepted_cities()}
    except Exception:
        pass

    for r in rows:
        why = []
        # Stock: a line the pool cannot cover. The order will sit in to_pick
        # forever, and the board's red will be blamed on the floor.
        if r["stage"] == "to_pick":
            need = {}
            for code, q in lines.get(r["order"], []):
                need[code] = need.get(code, 0) + q
            short_codes = [code for code, q in need.items() if float(free(r["order"], code)) < q]
            if short_codes:
                why.append("oos")
                r["shortItems"] = short_codes[:3]
            for code in need:
                if code in short:
                    why.append("shelf")
                    r["shelfBin"] = short[code]
                    break
        # City: the label will be refused, so the parcel closes and then
        # stalls. A parcel that already carries a label has been accepted.
        city = r.get("city") or ""
        if not r.get("awb") and (not city or _has_arabic(city)
                                 or (accepted and canon_city(city) not in accepted)):
            why.append("city")
        # Paperwork: a closed parcel with no label cannot be handed over.
        if r["stage"] == "to_hand_over" and not r.get("awb"):
            why.append("no_awb")
        # Picking that never closes: the list exists, the parcel does not.
        if r["stage"] == "picking" and r["ageH"] >= 24:
            why.append("stuck_pick")
            r["pickH"] = r["ageH"]
        r["why"] = list(dict.fromkeys(why))


_FIX = {
    "oos": "Pipeline", "shelf": "CycleCount", "city": "CityCheck",
    "no_awb": "Shipments", "stuck_pick": "PickLists",
}


@frappe.whitelist()
def blocked(days=30):
    """Every in-house order that cannot move, grouped by what it is waiting on."""
    _gate()
    from logistics_portal.api import clock
    cfg = get_settings()
    now = clock.floor_now()
    days = min(max(int(days or 30), 1), 90)
    # The stock and city lookups behind the blockers cost a second; the
    # answer is served from the last build and rebuilt by the clock's worker.
    hit = _cached(f"lp_ship_blocked:{days}")
    if hit is not None:
        if _age_s(hit) > _FRESH_S:
            _refresh_later(days)
        return hit["out"]
    return _refresh_blocked(days, cfg, now)


def _refresh_blocked(days, cfg, now):
    rows = [dict(r) for r in _shaped(days, cfg, now)
            if r["stage"] in ("to_pick", "picking", "to_hand_over")]
    _blockers(rows)
    hit = [r for r in rows if r["why"]]
    groups = {}
    for r in hit:
        for w in r["why"]:
            groups[w] = groups.get(w, 0) + 1
    hit.sort(key=lambda r: (-len(r["why"]), -r["lateMin"]))
    out = {"total": len(hit), "inHouse": len(rows), "groups": groups,
           "fix": _FIX, "rows": hit[:2000], "now": str(now)[:16]}
    _store(f"lp_ship_blocked:{days}", {"out": out})
    return out


# ---------------------------------------------------------------------------
# Alerts: the portal that pages you before the van leaves.
#
# Same log and the same toast as the audit engine, but addressed to the
# tracking team rather than the managers, because a wave about to leave
# thirty orders behind is their phone call to make. Runs on the 15-minute
# cron; each title is written once while it is still unread, so a standing
# problem is one row and not one row per tick.
# ---------------------------------------------------------------------------

def _tracking_users(role="tracking"):
    from logistics_portal.api.auth import SEED_ROLES
    users = [u for u, r in SEED_ROLES.items() if r == role]
    for u in frappe.db.sql("""SELECT name FROM `tabUser`
                              WHERE enabled = 1 AND custom_logistics_role = %s""", (role,)):
        if u[0] not in users:
            users.append(u[0])
    return users


# The portal's language is chosen in the portal, not on the ERPNext user (every
# account here is "en"), so an alert carries all three renderings and the
# Alerts page shows the one the reader is using. English is also the stored
# subject, which keeps the unread check stable.
_ALERTS = {
    "wave_risk": {
        "en": ("Orders may miss the {due} wave",
               "{n} orders confirmed and promised to the {due} wave are still without a pick list with under 90 minutes to go."),
        "fr": ("Des commandes risquent de manquer le départ de {due}",
               "{n} commandes confirmées et promises au départ de {due} n'ont toujours pas de liste de prélèvement à moins de 90 minutes."),
        "ar": ("أوردرات ممكن تفوّت موجة {due}",
               "{n} أوردر مؤكد وموعود بموجة {due} لسه من غير pick list وباقي أقل من 90 دقيقة."),
    },
    "late_house": {
        "en": ("Orders past their wave, still in the building",
               "{n} orders. Oldest is {order}, {h}h past its {due} wave."),
        "fr": ("Commandes ayant manqué leur départ, encore chez nous",
               "{n} commandes. La plus ancienne est {order}, {h} h après son départ de {due}."),
        "ar": ("أوردرات فوّتت موجتها ولسه جوه المخزن",
               "{n} أوردر. أقدمهم {order}، عدّى موجة {due} بـ {h} ساعة."),
    },
    "found_in_building": {
        "en": ("Manifested parcels found in the building",
               "{n} parcel(s) on a manifest were found still in the warehouse by the tracking team ({order}). They need a new handover — they are not with the carrier."),
        "fr": ("Colis manifestés retrouvés dans l'entrepôt",
               "{n} colis inscrits sur un manifeste ont été retrouvés dans l'entrepôt par l'équipe suivi ({order}). Ils doivent être remis à nouveau — ils ne sont pas chez le transporteur."),
        "ar": ("طرود في المانيفست اتلقت جوه المخزن",
               "{n} طرد مسجّل في مانيفست اتلقى لسه جوه المخزن ({order}). لازم يتسلّم للكارير تاني — مش عنده."),
    },
    "pulse_start": {
        "en": ("Pick lists nobody has started", "{n} lists created more than {min} min ago with no scan yet; the oldest waits {oldest}. {names}"),
        "fr": ("Des listes que personne n'a commencées", "{n} listes créées il y a plus de {min} min sans aucun scan ; la plus ancienne attend depuis {oldest}. {names}"),
        "ar": ("قوائم محدش بدأ فيها", "{n} قائمة اتعملت من أكتر من {min} دقيقة ومفيش scan لسه؛ الأقدم مستنية من {oldest}. {names}"),
    },
    "pulse_silent": {
        "en": ("A picker has gone silent mid-list", "{n} lists in picking with no scan for more than {min} min. {names}"),
        "fr": ("Un préparateur silencieux en pleine liste", "{n} listes en prélèvement sans scan depuis plus de {min} min. {names}"),
        "ar": ("بيكر ساكت في نص القائمة", "{n} قائمة في التجهيز من غير scan من أكتر من {min} دقيقة. {names}"),
    },
    "pulse_sort": {
        "en": ("Sorting is holding lists", "{n} submitted lists still sorting after {min} min; the oldest {oldest}. {names}"),
        "fr": ("Le tri retient des listes", "{n} listes soumises encore au tri après {min} min ; la plus ancienne {oldest}. {names}"),
        "ar": ("الفرز ماسك قوائم", "{n} قائمة اتبعتت ولسه في الفرز بعد {min} دقيقة؛ الأقدم {oldest}. {names}"),
    },
    "pulse_label": {
        "en": ("Lists without a carrier label", "{n} lists sorted but without a label after {min} min; the oldest {oldest}. {names}"),
        "fr": ("Des listes sans étiquette transporteur", "{n} listes triées mais sans étiquette après {min} min ; la plus ancienne {oldest}. {names}"),
        "ar": ("قوائم من غير بوليصة", "{n} قائمة اتفرزت ومفيش بوليصة بعد {min} دقيقة؛ الأقدم {oldest}. {names}"),
    },
    "pulse_pack": {
        "en": ("Labelled lists not packed", "{n} lists labelled but not packed after {min} min; the oldest {oldest}. {names}"),
        "fr": ("Des listes étiquetées non emballées", "{n} listes étiquetées mais non emballées après {min} min ; la plus ancienne {oldest}. {names}"),
        "ar": ("قوائم متبوّلصة وما اتغلّفتش", "{n} قائمة عليها بوليصة وما اتغلّفتش بعد {min} دقيقة؛ الأقدم {oldest}. {names}"),
    },
    "pulse_manifest": {
        "en": ("Packed parcels off the manifest", "{n} lists packed but not on a manifest after {min} min; the oldest {oldest}. {names}"),
        "fr": ("Des colis emballés hors manifeste", "{n} listes emballées mais absentes du manifeste après {min} min ; la plus ancienne {oldest}. {names}"),
        "ar": ("طرود متغلّفة برة المانيفست", "{n} قائمة اتغلّفت ومش على مانيفست بعد {min} دقيقة؛ الأقدم {oldest}. {names}"),
    },
    "manifest_short": {
        "en": ("The manifest closed with printed parcels left behind",
               "{n} printed parcels from {lists} pick lists were not scanned onto {shipment}. They are still in the building — open the sort wall's handover zone: {names}"),
        "fr": ("Le manifeste a fermé en laissant des colis imprimés",
               "{n} colis imprimés de {lists} listes n'ont pas été scannés sur {shipment}. Ils sont encore dans l'entrepôt — ouvrez la zone de remise du mur de tri : {names}"),
        "ar": ("المانيفست اتقفل وفي طرود مطبوعة اتسابت",
               "{n} طرد مطبوع من {lists} قائمة ما اتسكنوش على {shipment}. لسه جوه المخزن — افتح جزء التسليم في حيطة الفرز: {names}"),
    },
    "cf_stock_gap": {
        "en": ("Orders you confirmed cannot be shipped",
               "{n} confirmed orders ({value} MAD) are waiting on stock the shelf does not have, the oldest {d} days. Open Out of stock in the confirmation board and call the customers — {customer} ({order}) first."),
        "fr": ("Des commandes confirmées ne peuvent pas être expédiées",
               "{n} commandes confirmées ({value} MAD) attendent un stock qui n'existe pas, la plus ancienne depuis {d} jours. Ouvrez Rupture de stock et appelez les clients — {customer} ({order}) en premier."),
        "ar": ("أوردرات اتأكدت ومش قادرين نشحنها",
               "{n} أوردر مؤكد ({value} درهم) مستنيين بضاعة مش موجودة على الرف، أقدمهم من {d} يوم. افتح قسم «نفاد المخزون» في بورد الكونفيرميشن وكلّم العملاء — ابدأ بـ{customer} ({order})."),
    },
    "pack_short": {
        "en": ("A piece is missing at the packing desk",
               "{order}: {sku} was counted onto the sort wall but is not in the slot. The parcel is held at packing until someone finds it."),
        "fr": ("Une pièce manque au poste d'emballage",
               "{order} : {sku} a été comptée au mur de tri mais n'est pas dans le casier. Le colis est retenu à l'emballage."),
        "ar": ("في قطعة ناقصة عند محطة التغليف",
               "{order}: {sku} اتعدّت على حيطة الفرز بس مش موجودة في السلوت. الطرد متوقف عند التغليف لحد ما حد يلاقيها."),
    },
    "count_big": {
        "en": ("A count posted a large value difference",
               "{name} on {wh}: {amount} MAD, mostly {sku} ({delta} units at {rate} MAD each). Check the item's valuation before reading it as a real loss or gain."),
        "fr": ("Un comptage a passé un écart de valeur important",
               "{name} sur {wh} : {amount} MAD, surtout {sku} ({delta} unités à {rate} MAD). Vérifiez la valorisation de l'article avant d'y lire une vraie perte ou un vrai gain."),
        "ar": ("عدّة اترحّلت بفرق قيمة كبير",
               "{name} على {wh}: {amount} درهم، معظمها من {sku} ({delta} وحدة بسعر {rate} درهم). راجع تقييم الصنف قبل ما تعتبره خسارة أو زيادة حقيقية."),
    },
    "cf_first_call": {
        "en": ("Orders waiting for a first call past the target",
               "{n} orders have been Pending for more than {h} hours with no call logged. The oldest has waited {oldest} hours."),
        "fr": ("Des commandes attendent un premier appel au-delà de l'objectif",
               "{n} commandes sont en attente depuis plus de {h} h sans aucun appel enregistré. La plus ancienne attend depuis {oldest} h."),
        "ar": ("أوردرات مستنية أول مكالمة بعد الهدف",
               "{n} أوردر Pending من أكتر من {h} ساعة من غير أي مكالمة مسجلة. الأقدم مستني من {oldest} ساعة."),
    },
    "no_scan": {
        "en": ("Parcels handed over with no carrier update",
               "{n} parcels were handed over more than two days ago and our copy of the carrier status never moved. Check the carrier status sync in Tracking settings first; what stays Pending after a sync is a parcel the carrier truly never scanned."),
        "fr": ("Colis remis sans aucune mise à jour du transporteur",
               "{n} colis remis il y a plus de deux jours dont notre statut transporteur n'a jamais bougé. Vérifiez d'abord la synchronisation du statut dans les paramètres du suivi ; ce qui reste en attente après une synchro est un colis que le transporteur n'a réellement jamais scanné."),
        "ar": ("طرود اتسلّمت ومفيش أي تحديث من الكاريير",
               "{n} طرد اتسلّم من أكتر من يومين ونسختنا من حالة الكاريير ما اتحركتش. راجع مزامنة حالة الكاريير في إعدادات المتابعة الأول؛ اللي يفضل Pending بعد المزامنة هو طرد الكاريير فعلًا ما سكنه."),
    },
    "carrier_unack": {
        "en": ("Parcels we handed over that the carrier has not acknowledged",
               "{n} parcels ({value} MAD) were scanned onto a manifest more than a day ago and the carrier still shows them as awaiting pickup. Oldest: {shipment}, {hours}h. The manifest is our proof — open a claim with the carrier for each one."),
        "fr": ("Colis remis que le transporteur n'a pas confirmés",
               "{n} colis ({value} MAD) scannés sur un manifeste il y a plus d'un jour sont toujours « en attente de ramassage » chez le transporteur. Le plus ancien : {shipment}, {hours} h. Le manifeste est notre preuve — ouvrez une réclamation pour chacun."),
        "ar": ("طرود سلّمناها والكاريير ما أكّدش استلامها",
               "{n} طرد ({value} درهم) اتسكنوا على مانيفست من أكتر من يوم والكاريير لسه بيقول إنهم في انتظار الاستلام. الأقدم: {shipment}، {hours} ساعة. المانيفست هو دليلنا، افتح مطالبة مع الكاريير لكل واحد."),
    },
    "chase": {
        "en": ("Parcels past the chase line with the carrier",
               "{n} parcels moving for more than {days} days beyond the city promise — not late, lost. Chase them with the carrier."),
        "fr": ("Colis au-delà de la ligne de relance chez le transporteur",
               "{n} colis en mouvement depuis plus de {days} jours au-delà de la promesse de la ville — pas en retard, perdus. Relancez le transporteur."),
        "ar": ("طرود عدّت خط المطاردة عند الكارير",
               "{n} طرد ماشي أكتر من {days} يوم بعد وعد المدينة — مش متأخر، ضايع. طارده مع الكارير."),
    },
}


def _emit(kind, params, severity="warning", cooldown_h=4, order=None, audience="tracking"):
    """One row per standing problem. The stored subject is the English title
    without counts, so the unread check matches tick after tick; the three
    renderings ride in the body as JSON for the Alerts page. Once read, the
    same problem waits `cooldown_h` before it may page again."""
    texts = _ALERTS.get(kind) or {}
    if not texts:
        return
    def fmt(s):
        try:
            return s.format(**params)
        except Exception:
            return s
    i18n = {lang: {"t": fmt(t), "b": fmt(b)} for lang, (t, b) in texts.items()}
    title, detail = i18n["en"]["t"], i18n["en"]["b"]
    # email_content is HTML: the Desk shows the English line and never the
    # comment; the Alerts page reads the comment for the other languages.
    packed = json.dumps({"lp": i18n, "sev": severity, "kind": kind}, ensure_ascii=False)
    body = detail + "\n<!--lp-i18n " + packed.replace("--", "- -") + " -->"
    try:
        if frappe.db.exists("Notification Log", {"subject": title, "read": 0}):
            return
        if frappe.db.exists("Notification Log", {
                "subject": title,
                "creation": (">=", frappe.utils.add_to_date(now_datetime(), hours=-cooldown_h))}):
            return
        # Several audiences at once: the unread-subject check above runs once
        # per problem, so a second _emit call for the same kind (the old
        # per-audience loop) was skipped and the second audience never heard.
        auds = [audience] if isinstance(audience, str) else list(audience or [])
        users = []
        for aud in auds:
            for u in _tracking_users(aud) or []:
                if u not in users:
                    users.append(u)
        for user in users:
            frappe.get_doc({
                "doctype": "Notification Log", "subject": title,
                "email_content": body, "type": "Alert",
                "document_type": "Sales Order", "document_name": order,
                "for_user": user,
            }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "shipments._emit")
    frappe.publish_realtime("logistics_alert", {
        "severity": severity, "title": title, "detail": detail, "i18n": i18n,
        "audience": audience})


def run_alerts():
    """Scheduled: warn about the wave that is about to leave orders behind,
    the orders already left behind, and parcels the carrier has lost."""
    try:
        from logistics_portal.api import clock
        cfg = get_settings()
        now = clock.floor_now()
        # Nobody is paged at 3am or on a rest day: the van is not leaving.
        if now.weekday() in set(cfg.get("restDays") or []) or not (7 <= now.hour < 21):
            return
        # Rebuild the clock here, in the worker, so the team's first load of
        # the day and every load after it read a cache at most 15 min old;
        # the city tuner too, once an hour.
        refresh_cache(30)
        if _cached("lp_ship_tuner:4") is None:
            refresh_tuner(4)
        rows = _shaped(30, cfg, now)
        in_house = [r for r in rows if r["stage"] in ("to_pick", "picking", "to_hand_over")]
        carrier = [r for r in rows if r["stage"] == "with_carrier"]

        # 1) The next wave, ninety minutes out, still carrying unstarted orders.
        soon = {}
        for r in in_house:
            if not r["dueAt"] or r["late"]:
                continue
            due = frappe.utils.get_datetime(r["dueAt"] + ":00")
            mins = (due - now).total_seconds() / 60
            if 0 < mins <= 90 and r["stage"] == "to_pick":
                soon.setdefault(r["dueAt"], 0)
                soon[r["dueAt"]] += 1
        for due, n in soon.items():
            if n >= 5:
                _emit("wave_risk", {"n": n, "due": due[11:]}, "critical", cooldown_h=1)

        # 2) Past their wave and still in the building.
        late = [r for r in in_house if r["late"]]
        if len(late) >= 20:
            oldest = max(late, key=lambda r: r["lateMin"])
            _emit("late_house", {"n": len(late), "order": oldest["order"],
                                 "h": oldest["lateMin"] // 60, "due": oldest["dueAt"][11:]},
                  "critical", order=oldest["order"])

        # 3) Manifested two days ago, and the carrier has never scanned it.
        noscan = [r for r in carrier if r.get("verdict") == "noscan" and (r.get("eventAgeH") or 0) >= 48]
        if len(noscan) >= 10:
            _emit("no_scan", {"n": len(noscan)}, "critical", cooldown_h=12)

        # 4) Parcels the carrier has had too long to still call in transit.
        chase_h = int(cfg.get("chaseDays") or 5) * 24 * 60
        chase = [r for r in carrier if r["lateMin"] > chase_h]
        if len(chase) >= 10:
            _emit("chase", {"n": len(chase), "days": cfg.get("chaseDays")}, "warning", cooldown_h=12)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "shipments.run_alerts")


# ---------------------------------------------------------------------------
# One order's journey: the clock, and every hand the parcel passed through.
# ---------------------------------------------------------------------------

_CARRIER_EVENT_LIKE = ("Newly created parcel%", "Shipped to destination hub%",
                       "The parcel is present on Hub%", "Out for delivery%",
                       "Package Delivered%", "The driver has confirmed%",
                       "Customer unreachable%", "%Delivery Exception%", "%Failed%",
                       "%Returned%", "Tracking: %", "Rescue: %")


@frappe.whitelist()
def journey(order):
    """The parcel's whole story for the order page: stage and promise as the
    board reads them, the stage timestamps, the documents behind them, and
    the carrier's own events in order. Any portal role — the order page is
    shared — but a role is required (customer name and phone travel here)."""
    from logistics_portal.api.permissions import require_portal_user
    from logistics_portal.api import clock
    require_portal_user()
    # Six indexed point reads, not the board's derived tables: those are
    # materialised for EVERY order before a WHERE on one name applies.
    raw = frappe.db.sql(
        """SELECT so.name, so.customer_name AS customer, so.grand_total AS value,
                  so.creation AS created, so.custom_sales_status AS sales_status,
                  so.status AS so_status, so.custom_logistics_status AS lstat,
                  so.custom_track_shipment_status AS so_track,
                  NULLIF(so.custom_tracking_number, '') AS so_awb, so.modified AS modified,
                  COALESCE(NULLIF(so.custom_shipping_city, ''), addr.city, '') AS city,
                  COALESCE(NULLIF(so.custom_customer_phone, ''), so.custom_shipping_phone) AS phone,
                  so.custom_delivered_at AS delivered_at
           FROM `tabSales Order` so
           LEFT JOIN `tabAddress` addr ON addr.name = COALESCE(NULLIF(so.shipping_address_name, ''), so.customer_address)
           WHERE so.name = %s""", (order,), as_dict=True)
    if not raw:
        return {"found": False}
    raw = raw[0]
    one = lambda q, *a: (frappe.db.sql(q, a) or [[None]])[0]
    # The stage before ours belongs to the confirmation lane; its trail is
    # read here so the order page shows the whole chain, from the moment the
    # order arrived: every status decision (Version rows carry who made it)
    # and every 'Confirmation:' note the lane writes.
    cf_versions = frappe.db.sql("""SELECT owner, creation, data FROM `tabVersion`
                                   WHERE ref_doctype = 'Sales Order' AND docname = %s
                                     AND data LIKE '%%custom_sales_status%%' ORDER BY creation""", (order,), as_dict=True)
    cf_notes = frappe.db.sql("""SELECT owner, creation, content FROM `tabComment`
                                WHERE reference_doctype = 'Sales Order' AND reference_name = %s
                                  AND comment_type = 'Comment' AND content LIKE 'Confirmation:%%'
                                ORDER BY creation""", (order,), as_dict=True)
    raw.confirmed_at = one("""SELECT MIN(creation) FROM `tabVersion` WHERE ref_doctype = 'Sales Order' AND docname = %s
                              AND data LIKE '%%"custom_sales_status",%%,"Confirmed"]%%'""", order)[0]
    raw.picklist_at = one("""SELECT MIN(p.creation) FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name = pli.parent
                             WHERE pli.sales_order = %s AND p.docstatus < 2""", order)[0]
    dn = one("""SELECT MIN(d.creation), MAX(COALESCE(NULLIF(d.custom_awb, ''), '')), MAX(d.custom_track_shipment_status)
                FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name = dni.parent
                WHERE dni.against_sales_order = %s AND d.docstatus < 2 AND d.is_return = 0""", order)
    raw.dn_at, raw.awb, raw.track = (dn + [None, None, None])[:3] if isinstance(dn, list) else (dn[0], dn[1], dn[2])
    raw.handed_at = one("""SELECT MIN(s.creation) FROM `tabShipment Delivery Note` sdn JOIN `tabShipment` s ON s.name = sdn.parent
                           JOIN `tabDelivery Note Item` dni ON dni.parent = sdn.delivery_note
                           WHERE dni.against_sales_order = %s AND s.docstatus = 1""", order)[0]
    raw.labeled_at = one("""SELECT MIN(creation) FROM `tabComment` WHERE reference_doctype = 'Sales Order' AND reference_name = %s
                            AND comment_type = 'Comment' AND content LIKE 'Newly created parcel%%'""", order)[0]
    raw.hub_at = one("""SELECT MIN(creation) FROM `tabComment` WHERE reference_doctype = 'Sales Order' AND reference_name = %s
                        AND comment_type = 'Comment' AND (content LIKE 'Shipped to destination hub%%'
                        OR content LIKE 'The parcel is present on Hub%%' OR content LIKE 'Out for delivery%%'
                        OR content LIKE 'Package Delivered%%')""", order)[0]
    # The carrier's last word, so the order page reads it like the board does.
    ev = frappe.db.sql("""SELECT content, creation FROM `tabComment` WHERE reference_doctype = 'Sales Order' AND reference_name = %s
                          AND comment_type = 'Comment' AND (content LIKE 'Newly created%%' OR content LIKE 'Shipped to%%'
                          OR content LIKE 'The parcel%%' OR content LIKE 'Out for%%' OR content LIKE 'Package%%' OR content LIKE 'The driver%%'
                          OR content LIKE 'Customer unreachable%%' OR content LIKE 'Customer cancelled%%' OR content LIKE 'The customer has cancelled%%'
                          OR content LIKE 'Cancelled on site%%' OR content LIKE 'Justyol has requested%%')
                          ORDER BY creation DESC LIMIT 1""", (order,))
    raw.ev_text, raw.ev_at = (ev[0][0], ev[0][1]) if ev else (None, None)
    cfg = get_settings()
    now = clock.floor_now()
    r = _shape(raw, cfg, now)
    r["live"] = raw.sales_status == "Confirmed" and raw.so_status not in ("Closed", "Cancelled")
    r["soStatus"] = raw.so_status
    r["lstat"] = raw.lstat or ""
    docs = {
        "pickLists": [x[0] for x in frappe.db.sql(
            """SELECT DISTINCT p.name FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name = pli.parent
               WHERE pli.sales_order = %s AND p.docstatus < 2 ORDER BY p.creation""", (order,))],
        "deliveryNotes": [{"name": x[0], "docstatus": x[1], "awb": x[2] or ""} for x in frappe.db.sql(
            """SELECT DISTINCT d.name, d.docstatus, d.custom_awb FROM `tabDelivery Note Item` dni
               JOIN `tabDelivery Note` d ON d.name = dni.parent
               WHERE dni.against_sales_order = %s AND d.docstatus < 2 AND d.is_return = 0 ORDER BY d.creation""", (order,))],
        "shipments": [x[0] for x in frappe.db.sql(
            """SELECT DISTINCT s.name FROM `tabShipment Delivery Note` sdn JOIN `tabShipment` s ON s.name = sdn.parent
               JOIN `tabDelivery Note Item` dni ON dni.parent = sdn.delivery_note
               WHERE dni.against_sales_order = %s AND s.docstatus = 1 ORDER BY s.creation""", (order,))],
    }
    like = " OR ".join(["content LIKE %s"] * len(_CARRIER_EVENT_LIKE))
    events = [{"at": str(clock.to_floor(c.creation))[:16],
               "text": _clean_text(c.content)[:160],
               "team": bool((c.content or "").startswith(("Tracking:", "Rescue:")))}
              for c in frappe.db.sql(
                  f"""SELECT content, creation FROM `tabComment`
                      WHERE reference_doctype = 'Sales Order' AND reference_name = %s
                        AND comment_type = 'Comment' AND ({like})
                      ORDER BY creation""", tuple([order] + list(_CARRIER_EVENT_LIKE)), as_dict=True)]
    # One log, newest first: the order's own milestones, every carrier scan,
    # every note the team left — each with a kind the page can draw.
    timeline = []
    def add(at, kind, text="", who=""):
        if at:
            timeline.append({"at": at, "kind": kind, "text": text, "who": who})
    def _who(u):
        u = u or ""
        return "" if u in ("Administrator", "Guest") else u.split("@")[0]
    add(str(clock.to_floor(raw.created))[:16], "created")
    confirmed_by = ""
    for v in cf_versions:
        try:
            changed = [c for c in (json.loads(v.data or "{}").get("changed") or []) if c and c[0] == "custom_sales_status"]
        except Exception:
            changed = []
        for _f, _old, new in changed:
            if new == "Confirmed":
                confirmed_by = confirmed_by or _who(v.owner)
                continue   # the milestone below carries it
            add(str(clock.to_floor(v.creation))[:16], "cfstatus", new or "", _who(v.owner))
    add(r["confirmedAt"], "confirmed", "", confirmed_by)
    for c in cf_notes:
        text = _clean_text(c.content)
        m = re.search(r"· by (\S+)$", text)
        who = m.group(1).split("@")[0] if m else _who(c.owner)
        text = re.sub(r"\s*· by \S+$", "", text).split(":", 1)[-1].strip()
        # 'confirm' is the Confirmed milestone itself — one entry, not two.
        if text.startswith("confirm"):
            continue
        add(str(clock.to_floor(c.creation))[:16], "cfnote", text, who)
    add(r["pickedAt"], "picklist")
    add(r["closedAt"], "closed")
    if raw.handed_at:
        add(str(clock.to_floor(raw.handed_at))[:16], "manifest")
    if raw.delivered_at and not any(e["text"].startswith("Package Delivered") for e in events):
        add(r["deliveredAt"], "delivered")
    for e in events:
        text = e["text"]
        who = ""
        if e["team"]:
            kind = "mark" if text.startswith("Tracking:") else "rescue"
            m = re.search(r"· by (\S+)$", text)
            who = m.group(1).split("@")[0] if m else ""
            text = re.sub(r"\s*· by \S+$", "", text).split(":", 1)[-1].strip()
        else:
            kind = _event_kind(text) or "other"
        add(e["at"], kind, text, who)
    timeline.sort(key=lambda e: e["at"], reverse=True)
    return {"found": True, "row": r, "docs": docs, "events": events, "timeline": timeline,
            "now": str(now)[:16]}


# ---------------------------------------------------------------------------
# My day: what each person on this team actually did today, from the trail
# their actions already leave on the orders. No new bookkeeping — a chase, a
# rescue decision, a city fix, a handled complaint and a note each write a
# comment with a fixed prefix and the session user as owner.
# ---------------------------------------------------------------------------

_DAY_KINDS = {
    "chases": "Tracking: chased%",
    "rescues": "Rescue: %",
    "cities": "Shipping city set to%",
    "feedback": "Tracking: feedback handled%",
    "notes": "Note —%",
}


@frappe.whitelist()
def my_day():
    _gate()
    from logistics_portal.api import clock
    lo, hi = clock.day_bounds(clock.floor_now().date())
    sums = ", ".join(f"SUM(content LIKE %({k})s) AS {k}" for k in _DAY_KINDS)
    anyof = " OR ".join(f"content LIKE %({k})s" for k in _DAY_KINDS)
    params = dict(_DAY_KINDS, lo=lo, hi=hi)
    rows = frappe.db.sql(
        f"""SELECT owner, {sums} FROM `tabComment`
            WHERE reference_doctype = 'Sales Order' AND comment_type = 'Comment'
              AND creation >= %(lo)s AND creation < %(hi)s AND ({anyof})
            GROUP BY owner""", params, as_dict=True)
    users = [r.owner for r in rows]
    names = {}
    if users:
        names = dict(frappe.db.sql("SELECT name, full_name FROM `tabUser` WHERE name IN %s", (users,)))
    # The same trails are left by other lanes (a confirmation agent's note, a
    # dispatcher's city fix). This is the tracking team's day, so only people
    # holding the tracking role are listed — the manager grants it on Team.
    tracking = set(_tracking_users("tracking"))
    team = []
    for r in rows:
        if r.owner not in tracking:
            continue
        counts = {k: int(r.get(k) or 0) for k in _DAY_KINDS}
        counts["total"] = sum(counts.values())
        team.append({"user": r.owner, "name": names.get(r.owner) or r.owner.split("@")[0], **counts})
    team.sort(key=lambda x: -x["total"])
    me = next((x for x in team if x["user"] == frappe.session.user), None) or \
        {"user": frappe.session.user, **{k: 0 for k in _DAY_KINDS}, "total": 0}
    totals = {k: sum(x[k] for x in team) for k in list(_DAY_KINDS) + ["total"]}
    return {"today": str(lo)[:10], "me": me, "team": team[:12], "totals": totals, "teamSize": len(tracking)}


@frappe.whitelist()
def team_report(days=7):
    """The tracking team over a window, for its lead: what each member did
    (the same five trails as my-day) and what came of it — a rescue decision
    that ended in a delivery, a chased parcel that arrived. Outcomes are read
    from the order's own terminal stamps, so they are as true as the carrier.
    """
    _gate()
    if not _is_lead():
        frappe.throw("lp:leadsOnly", frappe.PermissionError)
    from logistics_portal.api import clock
    days = min(max(int(days or 7), 1), 90)
    now = clock.floor_now()
    lo, _hi = clock.day_bounds(frappe.utils.add_days(now.date(), -(days - 1)))
    _lo0, hi = clock.day_bounds(now.date())
    off_min = int(round(clock.offset_hours() * 60))
    sums = ", ".join(f"SUM(content LIKE %({k})s) AS {k}" for k in _DAY_KINDS)
    anyof = " OR ".join(f"content LIKE %({k})s" for k in _DAY_KINDS)
    params = dict(_DAY_KINDS, lo=lo, hi=hi, off=off_min)
    base = f"""FROM `tabComment`
               WHERE reference_doctype = 'Sales Order' AND comment_type = 'Comment'
                 AND creation >= %(lo)s AND creation < %(hi)s AND ({anyof})"""
    per = frappe.db.sql(f"SELECT owner, {sums} {base} GROUP BY owner", params, as_dict=True)
    daily = frappe.db.sql(
        f"""SELECT DATE(DATE_SUB(creation, INTERVAL %(off)s MINUTE)) AS d, {sums} {base}
            GROUP BY d ORDER BY d""", params, as_dict=True)
    # Outcomes: of the parcels this person decided to save (Redeliver/Reship)
    # or chased, how many the carrier later delivered.
    delivered = """(so.custom_track_shipment_status = 'Delivered' OR so.custom_delivered_at IS NOT NULL
                    OR so.custom_logistics_status = 'Delivered')"""
    outc = frappe.db.sql(
        f"""SELECT c.owner,
                   SUM(c.content LIKE 'Rescue: redeliver%%' OR c.content LIKE 'Rescue: reship%%') AS saved,
                   SUM((c.content LIKE 'Rescue: redeliver%%' OR c.content LIKE 'Rescue: reship%%') AND {delivered}) AS savedOk,
                   SUM(c.content LIKE 'Tracking: chased%%') AS chased,
                   SUM(c.content LIKE 'Tracking: chased%%' AND {delivered}) AS chasedOk
            FROM `tabComment` c JOIN `tabSales Order` so ON so.name = c.reference_name
            WHERE c.reference_doctype = 'Sales Order' AND c.comment_type = 'Comment'
              AND c.creation >= %(lo)s AND c.creation < %(hi)s
              AND (c.content LIKE 'Rescue: redeliver%%' OR c.content LIKE 'Rescue: reship%%'
                   OR c.content LIKE 'Tracking: chased%%')
            GROUP BY c.owner""", params, as_dict=True)
    outcomes = {r.owner: r for r in outc}
    users = [r.owner for r in per]
    names = dict(frappe.db.sql("SELECT name, full_name FROM `tabUser` WHERE name IN %s", (users,))) if users else {}
    members = []
    for r in per:
        counts = {k: int(r.get(k) or 0) for k in _DAY_KINDS}
        o = outcomes.get(r.owner) or {}
        members.append({"user": r.owner, "name": names.get(r.owner) or r.owner.split("@")[0], **counts,
                        "total": sum(counts.values()),
                        "saved": int(o.get("saved") or 0), "savedOk": int(o.get("savedOk") or 0),
                        "chased": int(o.get("chased") or 0), "chasedOk": int(o.get("chasedOk") or 0)})
    # The same trails are left by other lanes too (a confirmation agent's
    # rescue decision, a dispatcher's city fix). This page is about the
    # tracking team, so it is scoped to the users holding that role — and
    # says so when nobody holds it yet, rather than showing an empty table.
    team = set(_tracking_users("tracking"))
    members = [m for m in members if m["user"] != "Administrator"]
    scoped = bool(team) and any(m["user"] in team for m in members)
    if scoped:
        members = [m for m in members if m["user"] in team]
    members.sort(key=lambda x: -x["total"])
    totals = {k: sum(m[k] for m in members) for k in list(_DAY_KINDS) + ["total"]}
    tot_o = {k: sum(m[k] for m in members) for k in ("saved", "savedOk", "chased", "chasedOk")}
    return {"days": days, "since": str(lo)[:10], "until": str(now)[:10], "members": members, "totals": totals,
            "outcomes": tot_o, "scoped": scoped,
            "daily": [{"d": str(x.d), **{k: int(x.get(k) or 0) for k in _DAY_KINDS},
                       "total": sum(int(x.get(k) or 0) for k in _DAY_KINDS)} for x in daily]}


# ---------------------------------------------------------------------------
# City promise tuner: what the carrier has actually been doing per city over
# the last weeks, next to the promise the settings hold. Cities drift; the
# promise was seeded once. A lead accepts a suggestion in one click.
# ---------------------------------------------------------------------------

def _working_days_between(a, b, rest):
    """Calendar days from a to b that the carrier works — the same count the
    promise itself is made in (carrier_due skips the rest days)."""
    d, n, guard = a.date(), 0, 0
    end = b.date()
    while d < end and guard < 60:
        d = frappe.utils.add_days(d, 1)
        guard += 1
        if d.weekday() not in rest:
            n += 1
    return n


@frappe.whitelist()
def city_promises(weeks=4):
    """What the carrier actually kept per city lately, next to the promise.

    Measured 4.5 s on prod (a 42-day window of the clock). The answer changes
    by the day, so it is kept for an hour and rebuilt by the alert cron; a
    request computes it inline only when nothing is cached.
    """
    _gate()
    weeks = min(max(int(weeks or 4), 1), 8)
    hit = _cached(f"lp_ship_tuner:{weeks}")
    if hit is not None:
        return hit["out"]
    return refresh_tuner(weeks)


def refresh_tuner(weeks=4):
    from logistics_portal.api import clock
    from logistics_portal.api.city import canon_city
    weeks = min(max(int(weeks or 4), 1), 8)
    cfg = get_settings()
    now = clock.floor_now()
    rest = set(cfg.get("restDays") or [])
    since = str(frappe.utils.add_days(now, -weeks * 7))[:16]
    rows = _shaped(weeks * 7 + 14, cfg, now)
    per = {}
    for r in rows:
        if r["stage"] != "delivered" or not r["handedAt"] or not r["deliveredAt"] or r["deliveredAt"] < since:
            continue
        key = canon_city(r["city"])
        if not key:
            continue
        h = frappe.utils.get_datetime(r["handedAt"] + ":00")
        d = frappe.utils.get_datetime(r["deliveredAt"] + ":00")
        per.setdefault(key, {"days": [], "kept": 0})
        per[key]["days"].append(_working_days_between(h, d, rest))
        if r["kept"]:
            per[key]["kept"] += 1
    city_days = cfg.get("cityDays") or {}
    default = int(cfg.get("defaultCityDays") or 5)
    out = []
    for key, v in per.items():
        n = len(v["days"])
        if n < 15:
            continue
        ds = sorted(v["days"])
        p75 = ds[min(n - 1, int(round(0.75 * (n - 1))))]
        suggested = max(1, min(20, int(p75) or 1))
        current = int(city_days.get(key, default))
        out.append({"city": key, "n": n, "p75": p75, "median": ds[n // 2],
                    "keptPct": round(100.0 * v["kept"] / n),
                    "current": current, "configured": key in city_days,
                    "suggested": suggested, "delta": suggested - current})
    out.sort(key=lambda x: -x["n"])
    res = {"weeks": weeks, "cities": out, "default": default}
    try:
        frappe.cache().set_value(f"lp_ship_tuner:{weeks}", {"at": str(now_datetime())[:19], "out": res},
                                 expires_in_sec=3600)
    except Exception:
        pass
    return res
