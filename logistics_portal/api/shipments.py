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
}

_TERMINAL_OK = ("Delivered",)
_TERMINAL_BAD = ("Returned", "Not Delivered", "Failed Attempt", "Delivery Exception")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

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
    return out


def _gate():
    """Who works this portal. The tracking team owns it; managers oversee it."""
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("tracking", "manager", "cs", "dispatcher"):
        frappe.throw("Shipment tracking team only.", frappe.PermissionError)
    return role


def _admin_gate():
    from logistics_portal.api.auth import resolve_role
    from logistics_portal.api.permissions import is_ops_admin
    if resolve_role(frappe.session.user) != "tracking" and not is_ops_admin():
        frappe.throw("Tracking leads only.", frappe.PermissionError)


@frappe.whitelist()
def settings():
    _gate()
    s = get_settings()
    s["isAdmin"] = True
    try:
        _admin_gate()
    except Exception:
        s["isAdmin"] = False
    return s


@frappe.whitelist(methods=["POST"])
def save_settings(payload=None):
    _admin_gate()
    if isinstance(payload, str):
        payload = json.loads(payload or "{}")
    cur = get_settings()
    for k in ("waves", "restDays", "cityDays", "defaultCityDays", "chaseDays"):
        if isinstance(payload, dict) and k in payload:
            cur[k] = payload[k]
    frappe.db.set_default(_SETTINGS_KEY, json.dumps(cur))
    frappe.db.commit()
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
    days = int((cfg.get("cityDays") or {}).get(
        canon_city(city), cfg.get("defaultCityDays") or 5))
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


_BOARD_SQL = """
SELECT so.name, so.customer_name AS customer, so.grand_total AS value,
       so.creation AS created, so.custom_sales_status AS sales_status,
       COALESCE(NULLIF(so.custom_shipping_city, ''), addr.city, '') AS city,
       COALESCE(NULLIF(so.custom_customer_phone, ''), so.custom_shipping_phone) AS phone,
       cf.t AS confirmed_at, pl.t AS picklist_at, dn.t AS dn_at,
       sh.t AS handed_at, dn.awb AS awb, trk.st AS track,
       so.custom_delivered_at AS delivered_at
FROM `tabSales Order` so
LEFT JOIN `tabAddress` addr
       ON addr.name = COALESCE(NULLIF(so.shipping_address_name, ''), so.customer_address)
LEFT JOIN (SELECT docname, MIN(creation) t FROM `tabVersion`
           WHERE ref_doctype = 'Sales Order' AND data LIKE '%%Confirmed%%'
             AND creation >= DATE_SUB(NOW(), INTERVAL 60 DAY)
           GROUP BY docname) cf ON cf.docname = so.name
LEFT JOIN (SELECT pli.sales_order so_name, MIN(p.creation) t
           FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name = pli.parent
           WHERE p.docstatus < 2 GROUP BY pli.sales_order) pl ON pl.so_name = so.name
LEFT JOIN (SELECT dni.against_sales_order so_name, MIN(d.creation) t,
                  MAX(COALESCE(NULLIF(d.custom_awb, ''), '')) awb
           FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name = dni.parent
           WHERE d.docstatus = 1 AND d.is_return = 0
           GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name
LEFT JOIN (SELECT dni2.against_sales_order so_name, MIN(s.creation) t
           FROM `tabShipment Delivery Note` sdn JOIN `tabShipment` s ON s.name = sdn.parent
           JOIN `tabDelivery Note Item` dni2 ON dni2.parent = sdn.delivery_note
           GROUP BY dni2.against_sales_order) sh ON sh.so_name = so.name
LEFT JOIN (SELECT dni3.against_sales_order so_name,
                  MAX(d3.custom_track_shipment_status) st
           FROM `tabDelivery Note Item` dni3 JOIN `tabDelivery Note` d3 ON d3.name = dni3.parent
           WHERE d3.docstatus = 1 AND d3.is_return = 0
           GROUP BY dni3.against_sales_order) trk ON trk.so_name = so.name
WHERE so.company = %(co)s AND so.docstatus = 1
  AND so.custom_sales_status = 'Confirmed'
  AND so.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)
"""


def _rows(days=30):
    return frappe.db.sql(_BOARD_SQL, {"co": _CO, "days": days}, as_dict=True)


def _shape(r, cfg, now):
    """One order's clock: where it is, who owns it, and what it owes."""
    from logistics_portal.api import clock
    conf = clock.to_floor(r.confirmed_at) if r.confirmed_at else \
        (clock.to_floor(r.created) if r.created else None)
    handed = clock.to_floor(r.handed_at) if r.handed_at else None
    track = r.track or ""

    if track in _TERMINAL_OK:
        stage, owner = "delivered", ""
    elif track in _TERMINAL_BAD:
        stage, owner = "failed", "tracking"
    elif handed:
        stage, owner = "with_carrier", "carrier"
    elif r.dn_at:
        stage, owner = "to_hand_over", "dispatcher"
    elif r.picklist_at:
        stage, owner = "picking", "floor"
    else:
        # The leg that holds 57% of the in-house clock.
        stage, owner = "to_pick", "dispatcher"

    wave_id, wave_due = (None, None)
    due, late_min = None, 0
    if stage in ("to_pick", "picking", "to_hand_over"):
        wave_id, wave_due = wave_for(conf, cfg)
        due = wave_due
    elif stage == "with_carrier":
        due = carrier_due(handed, r.city, cfg)
    if due:
        late_min = int((now - due).total_seconds() / 60)

    return {
        "order": r.name, "customer": r.customer or "", "city": (r.city or "").strip(),
        "phone": r.phone or "", "value": round(float(r.value or 0)),
        "stage": stage, "owner": owner, "awb": r.awb or "", "track": track,
        "confirmedAt": str(conf)[:16] if conf else "",
        "handedAt": str(handed)[:16] if handed else "",
        "wave": wave_id, "dueAt": str(due)[:16] if due else "",
        "lateMin": late_min,
        "late": bool(due and late_min > 0 and stage not in ("delivered", "failed")),
        "ageH": int((now - conf).total_seconds() / 3600) if conf else 0,
    }


@frappe.whitelist()
def board(view="live", days=30, limit=300):
    """The live clock. view: live | late | wave | carrier | blocked."""
    _gate()
    from logistics_portal.api import clock
    cfg = get_settings()
    now = clock.floor_now()
    days = min(max(int(days or 30), 1), 90)
    limit = min(max(int(limit or 300), 1), 1000)

    rows = [_shape(r, cfg, now) for r in _rows(days)]
    live = [r for r in rows if r["stage"] not in ("delivered", "failed")]
    in_house = [r for r in live if r["stage"] in ("to_pick", "picking", "to_hand_over")]
    carrier = [r for r in live if r["stage"] == "with_carrier"]

    chase_h = int(cfg.get("chaseDays") or 5) * 24
    counts = {
        "live": len(live),
        "inHouse": len(in_house),
        "lateInHouse": sum(1 for r in in_house if r["late"]),
        "toPick": sum(1 for r in in_house if r["stage"] == "to_pick"),
        "carrier": len(carrier),
        "lateCarrier": sum(1 for r in carrier if r["late"]),
        "chase": sum(1 for r in carrier
                     if r["handedAt"] and r["ageH"] and r["lateMin"] > chase_h * 60),
    }

    if view == "late":
        sel = [r for r in live if r["late"]]
    elif view == "carrier":
        sel = carrier
    elif view == "wave":
        sel = in_house
    else:
        sel = live
    # Most urgent first: whoever is furthest past their promise, then whoever
    # is closest to it. A board sorted by date buries exactly the wrong rows.
    sel.sort(key=lambda r: (-r["lateMin"] if r["late"] else 10 ** 6 - r["lateMin"]))
    return {"view": view, "counts": counts, "rows": sel[:limit],
            "total": len(sel), "waves": cfg.get("waves"),
            "now": str(now)[:16]}


@frappe.whitelist()
def wave_board(days=7):
    """Today's waves: what each one has to carry, and what is going to miss."""
    _gate()
    from logistics_portal.api import clock
    cfg = get_settings()
    now = clock.floor_now()
    rows = [_shape(r, cfg, now) for r in _rows(days)]
    in_house = [r for r in rows if r["stage"] in ("to_pick", "picking", "to_hand_over")]
    buckets = {}
    for r in in_house:
        key = r["dueAt"][:16] or "—"
        b = buckets.setdefault(key, {"dueAt": key, "wave": r["wave"], "n": 0,
                                     "late": 0, "toPick": 0, "value": 0})
        b["n"] += 1
        b["value"] += r["value"]
        if r["late"]:
            b["late"] += 1
        if r["stage"] == "to_pick":
            b["toPick"] += 1
    out = sorted(buckets.values(), key=lambda b: b["dueAt"])
    return {"waves": out, "now": str(now)[:16], "config": cfg.get("waves")}


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
    from logistics_portal.api.picking import _available_totals
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
    free = _available_totals(codes) if codes else {}
    try:
        short = {it for (it, wh) in short_active().keys()}
    except Exception:
        short = set()
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
            for code, need in lines.get(r["order"], []):
                if float(free.get(code, 0)) < need:
                    why.append("oos")
                    break
            for code, _ in lines.get(r["order"], []):
                if code in short:
                    why.append("shelf")
                    break
        # City: the label will be refused, so the parcel closes and then stalls.
        city = r.get("city") or ""
        if not city or _has_arabic(city) or (accepted and canon_city(city) not in accepted):
            why.append("city")
        # Paperwork: a closed parcel with no label cannot be handed over.
        if r["stage"] == "to_hand_over" and not r.get("awb"):
            why.append("no_awb")
        # Picking that never closes: the list exists, the parcel does not.
        if r["stage"] == "picking" and r["ageH"] >= 24:
            why.append("stuck_pick")
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
    rows = [_shape(r, cfg, now) for r in _rows(min(max(int(days or 30), 1), 90))]
    rows = [r for r in rows if r["stage"] in ("to_pick", "picking", "to_hand_over")]
    _blockers(rows)
    hit = [r for r in rows if r["why"]]
    groups = {}
    for r in hit:
        for w in r["why"]:
            groups[w] = groups.get(w, 0) + 1
    hit.sort(key=lambda r: (-len(r["why"]), -r["lateMin"]))
    return {"total": len(hit), "inHouse": len(rows), "groups": groups,
            "fix": _FIX, "rows": hit[:400], "now": str(now)[:16]}


# ---------------------------------------------------------------------------
# Alerts: the portal that pages you before the van leaves.
#
# Same log and the same toast as the audit engine, but addressed to the
# tracking team rather than the managers, because a wave about to leave
# thirty orders behind is their phone call to make. Runs on the 15-minute
# cron; each title is written once while it is still unread, so a standing
# problem is one row and not one row per tick.
# ---------------------------------------------------------------------------

def _tracking_users():
    from logistics_portal.api.auth import SEED_ROLES
    users = [u for u, r in SEED_ROLES.items() if r == "tracking"]
    for u in frappe.db.sql("""SELECT name FROM `tabUser`
                              WHERE enabled = 1 AND custom_logistics_role = 'tracking'"""):
        if u[0] not in users:
            users.append(u[0])
    return users


def _emit(title, detail, severity="warning"):
    try:
        if frappe.db.exists("Notification Log", {"subject": title, "read": 0}):
            return
        for user in _tracking_users() or []:
            frappe.get_doc({
                "doctype": "Notification Log", "subject": title,
                "email_content": detail, "type": "Alert",
                "document_type": "Sales Order", "for_user": user,
            }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "shipments._emit")
    frappe.publish_realtime("logistics_alert", {
        "severity": severity, "title": title, "detail": detail, "audience": "tracking"})


def run_alerts():
    """Scheduled: warn about the wave that is about to leave orders behind,
    the orders already left behind, and parcels the carrier has lost."""
    try:
        from logistics_portal.api import clock
        cfg = get_settings()
        now = clock.floor_now()
        rows = [_shape(r, cfg, now) for r in _rows(30)]
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
                _emit(f"{n} orders may miss the {due[11:]} wave",
                      f"Confirmed, promised to the {due} wave, and still without a "
                      f"pick list with under 90 minutes to go.", "critical")

        # 2) Past their wave and still in the building.
        late = [r for r in in_house if r["late"]]
        if len(late) >= 20:
            oldest = max(late, key=lambda r: r["lateMin"])
            _emit(f"{len(late)} orders past their wave, still in the building",
                  f"Oldest is {oldest['order']}, {oldest['lateMin'] // 60}h past "
                  f"its {oldest['dueAt'][11:]} wave.", "critical")

        # 3) Parcels the carrier has had too long to still call in transit.
        chase_h = int(cfg.get("chaseDays") or 5) * 24 * 60
        chase = [r for r in carrier if r["lateMin"] > chase_h]
        if len(chase) >= 10:
            _emit(f"{len(chase)} parcels past the chase line with the carrier",
                  f"Moving for more than {cfg.get('chaseDays')} days beyond the city "
                  "promise — not late, lost. Chase them with the carrier.", "warning")
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "shipments.run_alerts")
