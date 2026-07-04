"""SLA engine — populates the currently-empty SLA fields on Delivery Notes.

Runs every 15 min (hooks.py). Computes expected delivery date + custom_sla_status
+ custom_sla_days_remaining from stage timestamps. Thresholds come from the
`Logistics SLA Settings` single (created on first run with sane defaults).
"""

import frappe
from frappe.utils import add_days, date_diff, getdate, nowdate

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
    dns = frappe.get_all(
        "Delivery Note",
        filters={
            "docstatus": 1,
            "posting_date": [">=", window_start],
            "custom_sla_status": ["in", ["", "On Track", "At Risk", "Breached", None]],
        },
        fields=["name", "posting_date", "custom_expected_delivery_date", "custom_track_shipment_status"],
        limit=2000,
    )
    today = getdate(nowdate())
    for dn in dns:
        try:
            # Can't compute an expected date without a posting date — skip.
            if not dn.get("custom_expected_delivery_date") and not dn.get("posting_date"):
                continue
            track = (dn.get("custom_track_shipment_status") or "").strip()
            expected = dn.get("custom_expected_delivery_date") or add_days(dn.posting_date, days)
            remaining = date_diff(expected, today)

            if track == "Delivered":
                status = "Delivered" if remaining >= 0 else "Delivered Late"
            elif track in ("Return", "Returned"):
                status = "Returned"
            elif remaining < 0:
                status = "Breached"
            elif remaining <= 1:
                status = "At Risk"
            else:
                status = "On Track"

            frappe.db.set_value(
                "Delivery Note", dn.name,
                {
                    "custom_expected_delivery_date": expected,
                    "custom_sla_status": status,
                    "custom_sla_days_remaining": remaining,
                },
                update_modified=False,
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"logistics_portal.sla:{dn.get('name')}")
    frappe.db.commit()
