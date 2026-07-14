"""SLA engine — populates the currently-empty SLA fields on Delivery Notes.

Runs every 15 min (hooks.py). Computes expected delivery date + custom_sla_status
+ custom_sla_days_remaining from stage timestamps. Thresholds come from the
`Logistics SLA Settings` single (created on first run with sane defaults).
"""

import frappe
from frappe.utils import nowdate

DEFAULT_DELIVERY_DAYS = 3  # Casablanca metro default; region overrides later.


def _delivery_days():
    if frappe.db.exists("DocType", "Logistics SLA Settings"):
        v = frappe.db.get_single_value("Logistics SLA Settings", "default_delivery_days")
        if v:
            return int(v)
    return DEFAULT_DELIVERY_DAYS


def run_sla_engine():
    """Scheduled: refresh SLA state on in-flight Delivery Notes."""
    meta = frappe.get_meta("Delivery Note")
    if not meta.has_field("custom_sla_status"):
        return

    days = _delivery_days()
    # Scope to the recent operational window — historical DNs are archive, not
    # "breached now". Also clear any stale SLA status the engine may have set on
    # old documents (one-time cleanup, cheap when nothing matches).
    from frappe.utils import add_days as _add_days
    window_start = _add_days(nowdate(), -14)
    frappe.db.sql(
        """UPDATE `tabDelivery Note`
           SET custom_sla_status = '', custom_sla_days_remaining = NULL
           WHERE posting_date < %s AND custom_sla_status IN ('Breached', 'At Risk', 'On Track')""",
        (window_start,),
    )
    # Set-based passes instead of a 2000-row Python loop. The old version
    # re-selected the same first 2000 rows every tick (its filter included the
    # statuses it had just written, ordered by modified) so the tail of the
    # window NEVER got an SLA status and breach counts were understated.
    #
    # 1) Every windowed DN gets an expected date.
    frappe.db.sql(
        """UPDATE `tabDelivery Note`
           SET custom_expected_delivery_date = DATE_ADD(posting_date, INTERVAL %s DAY)
           WHERE docstatus = 1 AND posting_date >= %s
             AND custom_expected_delivery_date IS NULL""",
        (days, window_start))

    # 2) Terminal transitions — evaluated ONCE, then never reprocessed. This
    # also fixes the old bug where an on-time delivery flipped to 'Delivered
    # Late' whenever the engine looked at it again after the expected date.
    frappe.db.sql(
        """UPDATE `tabDelivery Note`
           SET custom_sla_days_remaining = DATEDIFF(custom_expected_delivery_date, CURDATE()),
               custom_sla_status = IF(custom_expected_delivery_date >= CURDATE(),
                                      'Delivered', 'Delivered Late')
           WHERE docstatus = 1 AND posting_date >= %s
             AND custom_track_shipment_status = 'Delivered'
             AND COALESCE(custom_sla_status,'') NOT IN ('Delivered','Delivered Late')""",
        (window_start,))
    frappe.db.sql(
        """UPDATE `tabDelivery Note`
           SET custom_sla_status = 'Returned'
           WHERE docstatus = 1 AND posting_date >= %s
             AND custom_track_shipment_status IN ('Return','Returned')
             AND COALESCE(custom_sla_status,'') != 'Returned'""",
        (window_start,))

    # 3) Everything still in flight: recompute remaining + bucket.
    frappe.db.sql(
        """UPDATE `tabDelivery Note`
           SET custom_sla_days_remaining = DATEDIFF(custom_expected_delivery_date, CURDATE()),
               custom_sla_status = CASE
                   WHEN DATEDIFF(custom_expected_delivery_date, CURDATE()) < 0 THEN 'Breached'
                   WHEN DATEDIFF(custom_expected_delivery_date, CURDATE()) <= 1 THEN 'At Risk'
                   ELSE 'On Track' END
           WHERE docstatus = 1 AND posting_date >= %s
             AND COALESCE(custom_track_shipment_status,'')
                 NOT IN ('Delivered','Return','Returned')
             AND COALESCE(custom_sla_status,'')
                 NOT IN ('Delivered','Delivered Late','Returned')""",
        (window_start,))
    frappe.db.commit()


@frappe.whitelist()
def board(days=14):
    """Everything the SLA screen shows, all real, one call:
    status mix, on-time delivery rate, same-day-ship rate, days-remaining
    buckets for open parcels, worst cities, and the open-breach list."""
    from logistics_portal.api.auth import resolve_role
    if not resolve_role(frappe.session.user):
        frappe.throw("Not authorized.", frappe.PermissionError)
    days = min(max(int(days or 14), 1), 60)
    since = add_days(nowdate(), -days)

    counts = {}
    for r in frappe.db.sql(
        """SELECT COALESCE(custom_sla_status,'') s, COUNT(*) c
           FROM `tabDelivery Note`
           WHERE docstatus = 1 AND posting_date >= %s
           GROUP BY COALESCE(custom_sla_status,'')""", (since,), as_dict=True):
        counts[r.s or "none"] = int(r.c or 0)
    delivered = counts.get("Delivered", 0)
    late = counts.get("Delivered Late", 0)
    on_time_pct = round(delivered * 100.0 / max(1, delivered + late), 1)

    # Same-day ship: parcels whose order arrived the same day the manifest left.
    sd = frappe.db.sql(
        """SELECT COUNT(*) total,
                  SUM(CASE WHEN so.creation >= sh.pickup_date
                            AND so.creation < sh.pickup_date + INTERVAL 1 DAY
                      THEN 1 ELSE 0 END) same_day
           FROM `tabShipment Delivery Note` sdn
           JOIN `tabShipment` sh ON sh.name = sdn.parent AND sh.docstatus = 1
           JOIN `tabDelivery Note Item` dni ON dni.parent = sdn.delivery_note
           JOIN `tabSales Order` so ON so.name = dni.against_sales_order
           WHERE sh.pickup_date >= %s""", (since,), as_dict=True)[0]
    same_day_pct = round(int(sd.same_day or 0) * 100.0 / max(1, int(sd.total or 0)), 1)

    # Open parcels by days remaining (negative = overdue).
    buckets = [
        {"key": "ok", "label": "> 2 days left", "count": 0},
        {"key": "soon", "label": "1–2 days left", "count": 0},
        {"key": "today", "label": "due today", "count": 0},
        {"key": "over1", "label": "1–3 days late", "count": 0},
        {"key": "over3", "label": "> 3 days late", "count": 0},
    ]
    for r in frappe.db.sql(
        """SELECT custom_sla_days_remaining d, COUNT(*) c FROM `tabDelivery Note`
           WHERE docstatus = 1 AND posting_date >= %s
             AND custom_sla_status IN ('On Track','At Risk','Breached')
           GROUP BY custom_sla_days_remaining""", (since,), as_dict=True):
        d = int(r.d if r.d is not None else 0)
        c = int(r.c or 0)
        i = 0 if d > 2 else 1 if d >= 1 else 2 if d == 0 else 3 if d >= -3 else 4
        buckets[i]["count"] += c

    cities = frappe.db.sql(
        """SELECT COALESCE(NULLIF(so.custom_shipping_city,''),'?') city,
                  COUNT(*) breached
           FROM `tabDelivery Note` dn
           JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
           JOIN `tabSales Order` so ON so.name = dni.against_sales_order
           WHERE dn.docstatus = 1 AND dn.posting_date >= %s
             AND dn.custom_sla_status = 'Breached'
             AND COALESCE(dn.custom_track_shipment_status,'') <> 'Delivered'
           GROUP BY city ORDER BY breached DESC LIMIT 6""",
        (since,), as_dict=True)

    from logistics_portal.api.performance import breached_list
    return {
        "days": days,
        "onTimePct": on_time_pct,
        "sameDayPct": same_day_pct,
        "counts": {
            "onTrack": counts.get("On Track", 0),
            "atRisk": counts.get("At Risk", 0),
            "breached": counts.get("Breached", 0),
            "delivered": delivered,
            "deliveredLate": late,
            "returned": counts.get("Returned", 0),
            "unscored": counts.get("none", 0),
        },
        "buckets": buckets,
        "cities": [{"city": (c.city or "?").title(), "breached": int(c.breached or 0)}
                   for c in cities],
        "breaches": breached_list(limit=8),
    }
