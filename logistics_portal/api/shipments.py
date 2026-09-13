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
    for k, lo, hi in (("defaultCityDays", 1, 20), ("chaseDays", 1, 30)):
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
           WHERE d.docstatus = 1 AND d.is_return = 0
           GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name
LEFT JOIN (SELECT dni2.against_sales_order so_name, MIN(s.creation) t
           FROM `tabShipment Delivery Note` sdn JOIN `tabShipment` s ON s.name = sdn.parent
           JOIN `tabDelivery Note Item` dni2 ON dni2.parent = sdn.delivery_note
           WHERE s.docstatus = 1
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
    """The raw clock rows, shared for a minute.

    Measured on prod: 1.2s for 8,027 rows, and the board, the wave strip, the
    blocked screen and the alert cron each ran it in full. Rows are cached
    RAW (before shaping) so every caller still sees the current minute's
    clock; shaping 8k rows in Python is ~100ms and needs today's `now`.
    """
    days = int(days)
    key = f"lp_ship_rows:{days}"
    try:
        cached = frappe.cache().get_value(key)
        if cached is not None:
            return cached
    except Exception:
        pass
    rows = frappe.db.sql(_BOARD_SQL, {"co": _CO, "days": days, "vdays": days + 30}, as_dict=True)
    try:
        frappe.cache().set_value(key, rows, expires_in_sec=60)
    except Exception:
        pass
    return rows


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
    closed = clock.to_floor(r.dn_at) if r.dn_at else None
    delivered = clock.to_floor(r.delivered_at) if r.delivered_at else None
    return {
        "order": r.name, "customer": r.customer or "", "city": (r.city or "").strip(),
        "phone": r.phone or "", "value": round(float(r.value or 0)),
        "stage": stage, "owner": owner, "awb": r.awb or "", "track": track,
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
    week = str(frappe.utils.add_days(now, -7))[:16]
    judged = [r for r in rows if r["stage"] == "delivered" and r["kept"] is not None
              and r["deliveredAt"] >= week]
    counts = {
        "kept7d": {"n": len(judged), "ok": sum(1 for r in judged if r["kept"])},
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
        sel = [r for r in in_house if r["late"]]
    elif view == "to_pick":
        sel = [r for r in in_house if r["stage"] == "to_pick"]
    elif view == "late_carrier":
        sel = [r for r in carrier if r["late"]]
    elif view == "chase":
        sel = [r for r in carrier if r["lateMin"] > chase_h * 60]
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
            "nextWave": _next_wave(in_house, cfg, now),
            "now": str(now)[:16]}


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
    rows = [_shape(r, cfg, now) for r in _rows(days)]
    in_house = [r for r in rows if r["stage"] in ("to_pick", "picking", "to_hand_over")]
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
            "fix": _FIX, "rows": hit[:2000], "now": str(now)[:16]}


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
    "chase": {
        "en": ("Parcels past the chase line with the carrier",
               "{n} parcels moving for more than {days} days beyond the city promise — not late, lost. Chase them with the carrier."),
        "fr": ("Colis au-delà de la ligne de relance chez le transporteur",
               "{n} colis en mouvement depuis plus de {days} jours au-delà de la promesse de la ville — pas en retard, perdus. Relancez le transporteur."),
        "ar": ("طرود عدّت خط المطاردة عند الكارير",
               "{n} طرد ماشي أكتر من {days} يوم بعد وعد المدينة — مش متأخر، ضايع. طارده مع الكارير."),
    },
}


def _emit(kind, params, severity="warning", cooldown_h=4, order=None):
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
        for user in _tracking_users() or []:
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
        "audience": "tracking"})


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
                _emit("wave_risk", {"n": n, "due": due[11:]}, "critical", cooldown_h=1)

        # 2) Past their wave and still in the building.
        late = [r for r in in_house if r["late"]]
        if len(late) >= 20:
            oldest = max(late, key=lambda r: r["lateMin"])
            _emit("late_house", {"n": len(late), "order": oldest["order"],
                                 "h": oldest["lateMin"] // 60, "due": oldest["dueAt"][11:]},
                  "critical", order=oldest["order"])

        # 3) Parcels the carrier has had too long to still call in transit.
        chase_h = int(cfg.get("chaseDays") or 5) * 24 * 60
        chase = [r for r in carrier if r["lateMin"] > chase_h]
        if len(chase) >= 10:
            _emit("chase", {"n": len(chase), "days": cfg.get("chaseDays")}, "warning", cooldown_h=12)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "shipments.run_alerts")
