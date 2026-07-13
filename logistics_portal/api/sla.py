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
