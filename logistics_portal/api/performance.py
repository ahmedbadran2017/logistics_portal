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
        # The funnel = work in progress (in-flight stages), touched recently — NOT
        # the historical Delivered/Returned archive (which would dwarf the bars).
        # Delivered/Returned are shown as *today's* completions instead.
        wip_since = add_days(nowdate(), -FLOOR_DAYS)
        rows = frappe.db.sql(
            """
            SELECT custom_logistics_status AS status,
                   COUNT(*) AS cnt, ROUND(SUM(grand_total)) AS value
            FROM `tabSales Order`
            WHERE docstatus = 1 AND modified >= %s
              AND custom_logistics_status IN
                  ('Pending','Picked','In transit','Received','Label Generated','Label Printed','Shipped')
            GROUP BY custom_logistics_status
            """,
            (wip_since,),
            as_dict=True,
        )
        agg = {k: {"count": 0, "value": 0} for k in PIPELINE_KEYS}
        for r in rows:
            key = STAGE_MAP.get(r.status)
            if key:
                agg[key]["count"] += int(r.cnt or 0)
                agg[key]["value"] += float(r.value or 0)
        # today's completions for the two end-states
        today = add_days(nowdate(), -1)
        agg["delivered"]["count"] = frappe.db.count(
            "Sales Order", {"docstatus": 1, "custom_logistics_status": "Delivered", "modified": [">=", today]}
        )
        agg["returned"]["count"] = frappe.db.count(
            "Sales Order", {"docstatus": 1, "custom_logistics_status": "Returned", "modified": [">=", today]}
        )
        pipeline = [{"key": k, "count": agg[k]["count"], "value": agg[k]["value"]} for k in PIPELINE_KEYS]

        total = sum(p["count"] for p in pipeline)
        orders_in = frappe.db.count(
            "Sales Order", {"docstatus": 1, "transaction_date": [">=", add_days(nowdate(), -1)]}
        )
        by = {p["key"]: p["count"] for p in pipeline}

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
        ) or by.get("transit", 0)
        # Orders created today before the 14:00 cutoff (same-day ship window).
        before_cutoff = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSales Order` WHERE docstatus=1 AND DATE(creation)=%s AND TIME(creation) < '14:00:00'",
            (nowdate(),),
        )[0][0]

        summary = {
            "ordersIn": orders_in,
            "shipped": by.get("shipped", 0),
            "printed": by.get("label", 0),
            "toShip": by.get("pending", 0) + by.get("picked", 0) + by.get("labelgen", 0) + by.get("label", 0),
            "inTransit": in_transit,
            "breaches": breaches,
            "atRisk": at_risk,
            "returns": by.get("returned", 0),
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
    """Andon floor board: real hourly order intake today + headline counts."""
    try:
        rows = frappe.db.sql(
            """
            SELECT HOUR(creation) AS h, COUNT(*) AS c
            FROM `tabSales Order`
            WHERE DATE(creation) = %s AND docstatus = 1
            GROUP BY HOUR(creation) ORDER BY h
            """,
            (nowdate(),), as_dict=True,
        )
        by_hour = {int(r.h): int(r.c) for r in rows}
        # 8:00 → 20:00 window like the design
        hours = [{"h": h, "count": by_hour.get(h, 0)} for h in range(8, 21)]
        total_today = sum(by_hour.values())
        picked_today = frappe.db.count(
            "Pick List", {"docstatus": 1, "modified": [">=", nowdate()]}
        )
        shipped_today = frappe.db.count(
            "Sales Order", {"docstatus": 1, "custom_logistics_status": "Shipped", "modified": [">=", nowdate()]}
        )
        return {
            "hours": hours,
            "ordersToday": total_today,
            "pickedToday": picked_today,
            "shippedToday": shipped_today,
            "perHour": round(total_today / max(1, len([h for h in by_hour if by_hour[h]])), 1),
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
