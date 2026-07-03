"""Return Shipment queue + processing."""

import frappe


_STATE_MAP = {"Draft": "open", "AWB Scanning": "inspect", "Item Scanning": "inspect",
              "Ready for Return": "restock", "Returned": "closed", "Cancelled": "closed"}


@frappe.whitelist()
def queue(limit=50):
    """Return shipments in the SPA's RETURNS shape. Order/customer/sku/value are
    blank until linked from the return's items (sparse on the live site today)."""
    try:
        rows = frappe.get_all(
            "Return Shipment",
            fields=["name", "status"],
            order_by="modified desc",
            limit=int(limit),
        )
        return [{
            "no": r.name, "order": "", "customer": "", "reason": "",
            "sku": "", "value": 0, "awb": "",
            "state": _STATE_MAP.get(r.status, "open"),
        } for r in rows]
    except Exception:
        return []


VALID_OUTCOMES = {"Restock", "Defective", "Re-ship"}


@frappe.whitelist()
def process(return_shipment, outcome, reason, notes=None):
    """Record the inspection outcome for a returned parcel.
    outcome: Restock | Defective | Re-ship. Only a returns/manager user may act,
    and only on a real Return Shipment."""
    from logistics_portal.api.auth import resolve_role

    if not frappe.db.exists("Return Shipment", return_shipment):
        frappe.throw("Unknown return shipment.")
    if outcome not in VALID_OUTCOMES:
        frappe.throw("Invalid outcome.")
    if resolve_role(frappe.session.user) not in ("returns", "manager"):
        frappe.throw("You are not authorized to process returns.", frappe.PermissionError)

    # TODO: post stock movement for Restock; flag Defective; clone SO for Re-ship.
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Comment",
        "reference_doctype": "Return Shipment",
        "reference_name": return_shipment,
        "content": f"Processed: {outcome} — {reason}. {notes or ''}",
    }).insert()
    return {"ok": True}
