"""Cockpit, team leaderboard, and personal performance aggregation.

Returns data in the exact shapes the SPA screens expect (see
frontend/src/lib/handoffData.js), so screens can swap `handoffData` for a live
`api('performance.*')` call via the `liveOr` helper.
"""

import frappe
from frappe.utils import nowdate, add_days

# ERPNext custom_logistics_status -> design pipeline key (handoffData STAGE keys).
STAGE_MAP = {
    "Pending": "pending",
    "Picked": "picked",
    "In transit": "transit",
    "Received": "labelgen",
    "Label Generated": "labelgen",
    "Label Printed": "label",
    "Shipped": "shipped",
    "Delivered": "delivered",
    "Returned": "returned",
}
# Fixed display order of the funnel (design keys).
PIPELINE_KEYS = ["pending", "picking", "picked", "labelgen", "label", "shipped", "transit", "delivered", "returned"]
# The board's document-derived stages — the cockpit funnel mirrors these so the
# manager sees the SAME numbers on the cockpit and the Orders board.
BOARD_STAGES = ["to_pick", "picking", "prepared", "ready", "shipped", "delivered", "to_return", "returned"]


def _board_summary():
    """Counts/values from the Orders board model (shared 60s cache — one source
    of truth, so cockpit and board never disagree)."""
    import json as _json
    from logistics_portal.api import orders as _orders

    cache = frappe.cache()
    cached = cache.get_value("lp_board_summary")
    if cached:
        s = _json.loads(cached)
        return s["counts"], s["values"], s["tracks"], s["attention"]
    counts, values, tracks, attention = _orders._board_counts()
    cache.set_value("lp_board_summary", _json.dumps({
        "counts": counts, "values": values, "tracks": tracks, "attention": attention,
    }), expires_in_sec=60)
    return counts, values, tracks, attention

# Known team emails -> handoffData TEAM id (so the leaderboard matches byId()).
EMAIL_TO_ID = {
    "marouaneelmessaoudi07@gmail.com": "marouane",
    "mouakkalanass@gmail.com": "anass",
    "asmaazirary7@gmail.com": "asmaa",
    "lamdanisaad12@gmail.com": "saad",
    "ossamanahila@gmail.com": "oussama",
    "saidnakri65@gmail.com": "said",
    "redazaari47@gmail.com": "reda",
}

# How many days back "the floor" spans. Tune per the team's definition of the
# active window (kept short so the cockpit reflects current work, not history).
FLOOR_DAYS = 7


@frappe.whitelist()
def cockpit():
    """Live floor snapshot in the SPA's cockpit shape: {summary, pipeline,
    leaderboard, atRisk}. Date-scoped to the recent floor window."""
    try:
        # Funnel = the Orders-board stage model (document-derived, cached 60s).
        counts, values, _tracks, attention = _board_summary()
        pipeline = [{"key": k, "count": int(counts.get(k, 0) or 0),
                     "value": round(float(values.get(k, 0) or 0))} for k in BOARD_STAGES]
        by = {p["key"]: p["count"] for p in pipeline}

        total = sum(p["count"] for p in pipeline)
        orders_in = frappe.db.count(
            "Sales Order", {"docstatus": 1, "transaction_date": [">=", add_days(nowdate(), -1)]}
        )

        # SLA-derived numbers: scoped to the recent window so historical archive
        # never reads as "breached now".
        sla_since = add_days(nowdate(), -14)
        breaches = frappe.db.count(
            "Delivery Note", {"custom_sla_status": "Breached", "posting_date": [">=", sla_since]}
        )
        at_risk = frappe.db.count(
            "Delivery Note", {"custom_sla_status": "At Risk", "posting_date": [">=", sla_since]}
        )
        # In-transit is truest from carrier tracking on recent DNs (SO stage lags).
        in_transit = frappe.db.count(
            "Delivery Note",
            {"custom_track_shipment_status": ["in", ["In Transit", "Out For Delivery"]],
             "posting_date": [">=", sla_since]},
        ) or by.get("shipped", 0)
        # Orders created today before the 14:00 cutoff (same-day ship window).
        before_cutoff = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSales Order` WHERE docstatus=1 AND DATE(creation)=%s AND TIME(creation) < '14:00:00'",
            (nowdate(),),
        )[0][0]

        summary = {
            "ordersIn": orders_in,
            "shipped": by.get("shipped", 0),
            "printed": by.get("ready", 0),
            "toShip": by.get("to_pick", 0) + by.get("picking", 0) + by.get("prepared", 0) + by.get("ready", 0),
            "inTransit": in_transit,
            "breaches": breaches,
            "atRisk": at_risk,
            "returns": by.get("to_return", 0) + by.get("returned", 0),
            "attention": sum(int(v or 0) for v in (attention or {}).values()),
            "totalOrders": total,
            "sameDayPct": _sla_hit_rate(sla_since),
            "cutoff": "14:00",
            "beforeCutoff": int(before_cutoff or 0),
            "cutoffPct": round((before_cutoff or 0) * 100 / max(1, orders_in)),
        }

        return {"summary": summary, "pipeline": pipeline, "leaderboard": _leaderboard(), "atRisk": _at_risk()}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.cockpit")
        return {}


@frappe.whitelist()
def floor():
    """Andon floor board — every number real, from today's documents:
      Picking  = distinct orders on Pick Lists submitted today
      Labeling = Delivery Notes created today (DN creation == label/AWB moment)
      Packing  = orders that reached Label Printed today (incl. those already
                 Shipped since packing precedes the manifest the same day)
      Shipping = orders whose status is Shipped as of today
    Rates are per hour elapsed since the 8:00 floor start; the bottleneck is
    the station furthest below target. Cutoff counts down to the 17:00
    manifest hand-off."""
    try:
        from frappe.utils import now_datetime

        today = nowdate()
        rows = frappe.db.sql(
            """
            SELECT HOUR(creation) AS h, COUNT(*) AS c
            FROM `tabSales Order`
            WHERE DATE(creation) = %s AND docstatus = 1
            GROUP BY HOUR(creation) ORDER BY h
            """,
            (today,), as_dict=True,
        )
        by_hour = {int(r.h): int(r.c) for r in rows}
        # 8:00 → 20:00 window like the design
        hours = [{"h": h, "count": by_hour.get(h, 0)} for h in range(8, 21)]
        total_today = sum(by_hour.values())

        picked = frappe.db.sql(
            """SELECT COUNT(DISTINCT pli.sales_order) FROM `tabPick List` pl
               JOIN `tabPick List Item` pli ON pli.parent = pl.name
               WHERE pl.docstatus = 1 AND DATE(pl.creation) = %s""",
            (today,))[0][0] or 0
        labeled = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabDelivery Note` WHERE docstatus = 1 AND DATE(creation) = %s",
            (today,))[0][0] or 0
        printed = frappe.db.sql(
            """SELECT COUNT(*) FROM `tabSales Order`
               WHERE custom_logistics_status = 'Label Printed' AND DATE(modified) = %s""",
            (today,))[0][0] or 0
        shipped = frappe.db.sql(
            """SELECT COUNT(*) FROM `tabSales Order`
               WHERE custom_logistics_status = 'Shipped' AND DATE(modified) = %s""",
            (today,))[0][0] or 0
        packed = int(printed) + int(shipped)

        now = now_datetime()
        elapsed = max(1.0, (now.hour + now.minute / 60.0) - 8)  # floor opens 8:00
        target = int(frappe.db.get_default("lp_floor_target") or 40)

        def station(name, count):
            rate = round(count / elapsed, 1)
            return {"name": name, "rate": rate, "target": target, "count": int(count),
                    "status": "ok" if rate >= target * 0.85 else "warn"}

        stations = [
            station("Picking", picked), station("Packing", packed),
            station("Labeling", labeled), station("Shipping", shipped),
        ]
        bottleneck = min(stations, key=lambda s: s["rate"] / (s["target"] or 1))
        cutoff_min = max(0, 17 * 60 - (now.hour * 60 + now.minute))  # 17:00 manifest

        return {
            "hours": hours,
            "ordersToday": total_today,
            "pickedToday": int(picked),
            "packedToday": packed,
            "shippedToday": int(shipped),
            "perHour": round(total_today / elapsed, 1),
            "target": target,
            "stations": stations,
            "bottleneck": bottleneck["name"],
            "cutoffMin": cutoff_min,
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.floor")
        return {}


@frappe.whitelist()
def team():
    return {"leaderboard": _leaderboard()}


@frappe.whitelist()
def me(user=None):
    """Personal stats for the My Performance screen."""
    user = user or frappe.session.user
    try:
        today = frappe.db.count(
            "Pick List", {"custom_assigned_picker": user, "modified": [">=", nowdate()]}
        )
        return {"todayCount": today, "avgTime": "—", "slaHit": 0, "rank": 0, "target": 40, "spark": [], "bests": []}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
def _sla_hit_rate(since=None):
    filters = {"custom_sla_status": ["not in", ["", None]]}
    if since:
        filters["posting_date"] = [">=", since]
    total = frappe.db.count("Delivery Note", dict(filters))
    if not total:
        return 0
    filters["custom_sla_status"] = ["in", ["On Track", "Delivered"]]
    good = frappe.db.count("Delivery Note", dict(filters))
    return round(good * 100 / total)


def _at_risk(limit=8):
    rows = frappe.get_all(
        "Delivery Note",
        filters={
            "custom_sla_status": ["in", ["At Risk", "Breached"]],
            "posting_date": [">=", add_days(nowdate(), -14)],
        },
        fields=["name", "customer_name as customer", "custom_sla_status as sla"],
        order_by="posting_date desc",
        limit=limit,
    )
    out = []
    for r in rows:
        out.append({
            "no": r.name, "customer": r.customer, "stage": "transit",
            "sla": "breached" if r.sla == "Breached" else "atrisk", "mins": 0,
        })
    return out


def _leaderboard(limit=8):
    since = add_days(nowdate(), -30)
    rows = frappe.db.sql(
        """
        SELECT custom_assigned_picker AS picker, COUNT(*) AS picks
        FROM `tabPick List`
        WHERE custom_assigned_picker IS NOT NULL AND custom_assigned_picker != ''
          AND modified >= %s
        GROUP BY custom_assigned_picker
        ORDER BY picks DESC LIMIT %s
        """,
        (since, limit),
        as_dict=True,
    )
    out = []
    for i, r in enumerate(rows):
        pid = EMAIL_TO_ID.get(r.picker)
        name = frappe.db.get_value("User", r.picker, "full_name") or r.picker
        out.append({
            "id": pid or r.picker,
            "name": name,
            "picks": int(r.picks or 0),
            "avg": "—",
            "sla": 0,          # populated once the SLA engine runs
            "rank": i + 1,
            "trend": [],
            "target": 40,
        })
    return out
