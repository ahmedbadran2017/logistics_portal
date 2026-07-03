"""Sales Order stage timestamps + order detail."""

import frappe
from frappe.utils import now_datetime

# Which custom_*_at field each logistics status stamps (first time it is reached).
STAGE_STAMP = {
    "Picked": "custom_picked_at",
    "Label Generated": "custom_labeled_at",
    "Label Printed": "custom_labeled_at",
    "Shipped": "custom_shipped_at",
    "Delivered": "custom_delivered_at",
}


def stamp_stage_timestamps(doc, method=None):
    """Stamp precise stage timestamps as custom_logistics_status advances, so
    time-in-stage and SLA are exact instead of scraped from the Version log.
    No-op if the timestamp custom fields aren't installed yet."""
    # Wrapped so a stamping fault can never break unrelated Sales Order saves
    # (this hook fires on every SO on_update, site-wide).
    try:
        status = doc.get("custom_logistics_status")
        field = STAGE_STAMP.get(status)
        if not field:
            return
        if not frappe.get_meta("Sales Order").has_field(field):
            return
        if not doc.get(field):
            # db_set writes directly (no doc_event re-trigger); update_modified=False
            # keeps it out of the modified-timestamp path.
            doc.db_set(field, now_datetime(), update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.stamp_stage_timestamps")


# ERPNext status -> design stage key + known picker emails -> handoffData id.
_STAGE_MAP = {
    "Pending": "pending", "Picked": "picked", "In transit": "transit",
    "Received": "labelgen", "Label Generated": "labelgen", "Label Printed": "label",
    "Shipped": "shipped", "Delivered": "delivered", "Returned": "returned",
}
_PICKER_ID = {
    "marouaneelmessaoudi07@gmail.com": "marouane", "mouakkalanass@gmail.com": "anass",
    "asmaazirary7@gmail.com": "asmaa", "lamdanisaad12@gmail.com": "saad",
    "ossamanahila@gmail.com": "oussama", "saidnakri65@gmail.com": "said",
    "redazaari47@gmail.com": "reda",
}


@frappe.whitelist()
def list(scope="floor", picker=None, limit=60):
    """Recent orders in the SPA's ORDERS shape (Pipeline + Picker queue).
    scope='queue' narrows to pick-ready stages; `picker` filters to that user's
    assigned pick lists."""
    limit = int(limit)
    statuses = (
        ["Pending", "Picked"] if scope == "queue"
        else ["Pending", "Picked", "In transit", "Received", "Label Generated", "Label Printed", "Shipped"]
    )
    try:
        rows = frappe.get_all(
            "Sales Order",
            filters={"docstatus": 1, "custom_logistics_status": ["in", statuses]},
            fields=[
                "name", "customer_name", "grand_total", "custom_channel",
                "custom_logistics_status", "custom_items_count", "custom_awb", "creation",
            ],
            order_by="modified desc",
            limit=limit,
        )
        out = []
        for r in rows:
            pl = _pick_meta(r.name)
            if picker and pl.get("picker_email") != picker:
                continue
            out.append({
                "no": r.name,
                "customer": r.customer_name,
                "channel": (r.custom_channel or "manual").lower() or "manual",
                "total": r.grand_total,
                "items": r.custom_items_count or 1,
                "stage": _STAGE_MAP.get(r.custom_logistics_status, "pending"),
                "sla": "ontrack",  # populated once the SLA engine runs
                "bin": pl.get("bin") or "",
                "zone": pl.get("bin") or "",
                "picker": pl.get("picker_id"),
                "mins": _age_mins(r.creation),
                "awb": r.custom_awb,
            })
        return out
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.orders.list")
        return []


def _pick_meta(order):
    """Best-effort picker + bin for an order via its Pick List."""
    row = frappe.db.sql(
        """
        SELECT pl.custom_assigned_picker AS picker, pli.warehouse AS bin
        FROM `tabPick List Item` pli
        JOIN `tabPick List` pl ON pl.name = pli.parent
        WHERE pli.sales_order = %s LIMIT 1
        """,
        (order,), as_dict=True,
    )
    if not row:
        return {}
    email = row[0].picker
    return {"picker_email": email, "picker_id": _PICKER_ID.get(email), "bin": row[0].bin}


def _age_mins(creation):
    if not creation:
        return 0
    from frappe.utils import time_diff_in_seconds, now_datetime
    try:
        return max(0, int(time_diff_in_seconds(now_datetime(), creation) // 60))
    except Exception:
        return 0


@frappe.whitelist()
def detail(name):
    """Full order detail for the shared OrderDetail screen."""
    name = (name or "").lstrip("#")
    if not frappe.db.exists("Sales Order", name):
        return {}
    so = frappe.get_doc("Sales Order", name)
    return {
        "name": "#" + so.name,
        "customer": so.customer_name,
        "channel": so.get("custom_channel"),
        "total": so.grand_total,
        "stage": so.get("custom_logistics_status") or "Pending",
        "awb": so.get("custom_awb"),
        "tracking_status": so.get("custom_track_shipment_status"),
        "tracking_company": so.get("custom_tracking_company") or "Cathedis",
        "picked_at": so.get("custom_picked_at"),
        "labeled_at": so.get("custom_labeled_at"),
        "shipped_at": so.get("custom_shipped_at"),
        "delivered_at": so.get("custom_delivered_at"),
    }
