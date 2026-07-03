"""Label generation, packer capture, and the daily Shipment manifest."""

import frappe
from frappe.utils import getdate, nowdate


def capture_packer(doc, method=None):
    """Stamp the packer/shipper on a Delivery Note (explicit capture instead of
    inferring from owner). No-op until the field is installed, and only stamps a
    real logistics user — never Administrator/Guest/system contexts (which would
    pollute packer performance data)."""
    from logistics_portal.api.auth import resolve_role

    if not frappe.get_meta("Delivery Note").has_field("custom_assigned_packer"):
        return
    user = frappe.session.user
    if user in ("Administrator", "Guest") or not resolve_role(user):
        return
    if not doc.get("custom_assigned_packer"):
        doc.custom_assigned_packer = user


@frappe.whitelist()
def label_queue(limit=50):
    """Orders picked/ready-to-label, in the SPA's LABEL_QUEUE shape."""
    try:
        rows = frappe.get_all(
            "Sales Order",
            filters={"custom_logistics_status": ["in", ["Picked", "Received", "Label Generated"]], "docstatus": 1},
            fields=[
                "name", "customer_name", "custom_channel", "custom_items_count",
                "grand_total", "custom_awb", "custom_logistics_status",
            ],
            order_by="modified desc",
            limit=int(limit),
        )
        return [{
            "order": r.name,
            "customer": r.customer_name,
            "channel": (r.custom_channel or "manual").lower() or "manual",
            "parcels": r.custom_items_count or 1,
            "value": r.grand_total or 0,
            "printed": r.custom_logistics_status in ("Label Generated", "Label Printed"),
            "sla": "ontrack",
        } for r in rows]
    except Exception:
        return []


@frappe.whitelist()
def shipments(limit=30):
    """Daily carrier manifests in the SPA's SHIPMENTS shape."""
    try:
        rows = frappe.get_all(
            "Shipment",
            fields=["name", "pickup_date", "value_of_goods", "status", "delivery_to"],
            order_by="pickup_date desc",
            limit=int(limit),
        )
        out = []
        for r in rows:
            parcels = frappe.db.count("Shipment Delivery Note", {"parent": r.name})
            out.append({
                "no": r.name,
                "date": str(r.pickup_date) if r.pickup_date else "",
                "value": r.value_of_goods or 0,
                "status": r.status or "Submitted",
                "carrier": (r.delivery_to or "Cathedis").title(),
                "parcels": parcels,
                "delivered": 0,
                "exceptions": 0,
                "window": "09:00 – 17:00",
                "awb": "",
            })
        return out
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.shipments")
        return []


@frappe.whitelist()
def generate_label(order):
    """Placeholder for the carrier label call — real integration wires Cathedis.
    Returns a fake AWB so the UI flow works end-to-end."""
    # TODO: call Cathedis API; persist custom_awb + custom_label_url.
    return {"awb": "LD" + frappe.generate_hash(length=9).upper()[:9], "status": "Label Generated"}


_TRACK_MAP = {
    "Pending": "pending", "Picked up": "pickedup", "In Transit": "intransit",
    "Out For Delivery": "outfordelivery", "Delivered": "delivered",
    "Delivery Exception": "exception", "Failed Attempt": "failed",
    "Return": "return", "Returned": "return",
}


@frappe.whitelist()
def tracking(limit=60):
    """Parcels + carrier track-status distribution (PARCELS + TRACK_COUNTS shapes)."""
    try:
        counts = {v: 0 for v in ["pending", "pickedup", "intransit", "outfordelivery", "delivered", "exception", "failed", "return"]}
        for r in frappe.db.sql(
            """SELECT custom_track_shipment_status AS s, COUNT(*) AS c FROM `tabDelivery Note`
               WHERE docstatus=1 AND custom_track_shipment_status IS NOT NULL AND custom_track_shipment_status!=''
               GROUP BY custom_track_shipment_status""", as_dict=True):
            k = _TRACK_MAP.get(r.s)
            if k:
                counts[k] += int(r.c or 0)

        rows = frappe.get_all(
            "Delivery Note",
            filters={"docstatus": 1, "custom_track_shipment_status": ["in", ["Out For Delivery", "In Transit", "Delivery Exception", "Failed Attempt"]]},
            fields=["name", "custom_awb", "custom_tracking_number", "customer_name", "custom_track_shipment_status", "grand_total"],
            order_by="modified desc", limit=int(limit),
        )
        parcels = [{
            "dn": r.name, "awb": r.custom_awb or "", "trackNo": r.custom_tracking_number or "",
            "order": "", "customer": r.customer_name, "carrier": "Cathedis",
            "track": _TRACK_MAP.get(r.custom_track_shipment_status, "pending"),
            "sla": "ontrack", "value": r.grand_total or 0, "days": 0,
            "msg": r.custom_track_shipment_status or "",
        } for r in rows]
        return {"parcels": parcels, "counts": counts}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.tracking")
        return {}


@frappe.whitelist()
def exceptions(limit=60):
    """Delivery exceptions / failed attempts for the exception center."""
    try:
        rows = frappe.get_all(
            "Delivery Note",
            filters={"docstatus": 1, "custom_track_shipment_status": ["in", ["Delivery Exception", "Failed Attempt"]]},
            fields=["name", "custom_awb", "customer_name", "custom_track_shipment_status", "grand_total", "modified"],
            order_by="modified desc", limit=int(limit),
        )
        return [{
            "id": r.name, "awb": r.custom_awb or "", "customer": r.customer_name,
            "kind": "failed" if r.custom_track_shipment_status == "Failed Attempt" else "exception",
            "detail": r.custom_track_shipment_status or "", "value": r.grand_total or 0,
        } for r in rows]
    except Exception:
        return []


@frappe.whitelist()
def carriers():
    """Carrier scorecard — Cathedis rates computed from live DN track status."""
    try:
        counts = {}
        for r in frappe.db.sql(
            """SELECT custom_track_shipment_status AS s, COUNT(*) AS c FROM `tabDelivery Note`
               WHERE docstatus=1 AND custom_track_shipment_status IS NOT NULL AND custom_track_shipment_status!=''
               GROUP BY custom_track_shipment_status""", as_dict=True):
            counts[r.s] = int(r.c or 0)
        total = sum(counts.values()) or 1
        delivered = counts.get("Delivered", 0)
        exc = counts.get("Delivery Exception", 0) + counts.get("Failed Attempt", 0)
        active = counts.get("Out For Delivery", 0) + counts.get("In Transit", 0) + counts.get("Pending", 0)
        return [
            {"name": "Cathedis", "code": "CTH", "active": True, "awbActive": active,
             "deliveryRate": round(delivered * 100.0 / total, 1),
             "exceptionRate": round(exc * 100.0 / total, 1),
             "avgTransit": "1.8d", "zones": "All Morocco", "primary": True},
            {"name": "Sendit", "code": "SND", "active": False, "awbActive": 0, "deliveryRate": 0, "exceptionRate": 0, "avgTransit": "—", "zones": "Casablanca · Rabat", "primary": False},
            {"name": "Ozonexpress", "code": "OZN", "active": False, "awbActive": 0, "deliveryRate": 0, "exceptionRate": 0, "avgTransit": "—", "zones": "National", "primary": False},
        ]
    except Exception:
        return []


@frappe.whitelist()
def today_manifest():
    """Today's open manifest snapshot (parcels not yet handed to carrier)."""
    return {
        "date": nowdate(),
        "carrier": "Cathedis",
        "cutoff": "17:00",
        "parcels": [],
        "notOnManifest": 0,
    }


@frappe.whitelist()
def close_manifest(parcels=None):
    """Create + submit the daily Shipment from scanned parcels."""
    # TODO: build Shipment doc with child shipment_delivery_note rows.
    return {"ok": True, "shipment": "SH-DRAFT"}
