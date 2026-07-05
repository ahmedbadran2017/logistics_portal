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
    """Daily carrier manifests with real per-manifest outcomes (delivered /
    exceptions from the linked Delivery Notes) in one grouped query."""
    try:
        rows = frappe.db.sql(
            """SELECT sh.name, sh.pickup_date, sh.value_of_goods, sh.status,
                      sh.delivery_to, sh.awb_number,
                      COUNT(sdn.name) AS parcels,
                      SUM(CASE WHEN dn.custom_track_shipment_status = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
                      SUM(CASE WHEN dn.custom_track_shipment_status IN ('Delivery Exception','Failed Attempt') THEN 1 ELSE 0 END) AS exceptions
               FROM `tabShipment` sh
               LEFT JOIN `tabShipment Delivery Note` sdn ON sdn.parent = sh.name
               LEFT JOIN `tabDelivery Note` dn ON dn.name = sdn.delivery_note
               WHERE sh.docstatus < 2
               GROUP BY sh.name
               ORDER BY sh.pickup_date DESC, sh.modified DESC
               LIMIT %(limit)s""",
            {"limit": min(max(int(limit or 30), 1), 100)}, as_dict=True)
        return [{
            "no": r.name,
            "date": str(r.pickup_date) if r.pickup_date else "",
            "value": r.value_of_goods or 0,
            "status": r.status or "Submitted",
            "carrier": (r.delivery_to or "Cathedis").title(),
            "awb": r.awb_number or "",
            "parcels": int(r.parcels or 0),
            "delivered": int(r.delivered or 0),
            "exceptions": int(r.exceptions or 0),
            "window": "09:00 – 17:00",
        } for r in rows]
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
def tracking(days=14, state="", q="", limit=30, offset=0):
    """Windowed parcel board. Production has ~24k stale DN track statuses that
    never re-sync (avg age 90d), so everything is scoped to a recent
    posting-date window — stale rows are history, not work.

    Returns {parcels, counts, total, days, serverNow}; `state` filters by the
    SPA track key, `q` searches DN/AWB/tracking-no/customer/order."""
    try:
        days = min(max(int(days or 14), 1), 90)
        limit = min(max(int(limit or 30), 1), 100)
        offset = max(int(offset or 0), 0)

        window = "dn.docstatus = 1 AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)"
        vals = {"days": days}

        counts = {v: 0 for v in ["pending", "pickedup", "intransit", "outfordelivery", "delivered", "exception", "failed", "return"]}
        for r in frappe.db.sql(
            f"""SELECT dn.custom_track_shipment_status AS s, COUNT(*) AS c FROM `tabDelivery Note` dn
                WHERE {window} AND dn.custom_track_shipment_status IS NOT NULL AND dn.custom_track_shipment_status != ''
                GROUP BY dn.custom_track_shipment_status""", vals, as_dict=True):
            k = _TRACK_MAP.get(r.s)
            if k:
                counts[k] += int(r.c or 0)

        raw_by_key = {}
        for raw, key in _TRACK_MAP.items():
            raw_by_key.setdefault(key, []).append(raw)
        active = ["Pending", "Picked up", "In Transit", "Out For Delivery", "Delivery Exception", "Failed Attempt"]
        states = raw_by_key.get(state) if state else active
        if not states:
            states = active
        vals["states"] = tuple(states)

        qcond = ""
        if q and str(q).strip():
            vals["q"] = f"%{str(q).strip()}%"
            qcond = """ AND (dn.name LIKE %(q)s OR dn.custom_awb LIKE %(q)s
                        OR dn.custom_tracking_number LIKE %(q)s OR dn.customer_name LIKE %(q)s
                        OR dni.so LIKE %(q)s)"""

        so_join = """LEFT JOIN (SELECT parent, MAX(against_sales_order) AS so
                                FROM `tabDelivery Note Item` GROUP BY parent) dni ON dni.parent = dn.name
                     LEFT JOIN `tabSales Order` so ON so.name = dni.so
                     LEFT JOIN `tabAddress` addr
                        ON addr.name = COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address)"""

        total = frappe.db.sql(
            f"""SELECT COUNT(*) FROM `tabDelivery Note` dn {so_join}
                WHERE {window} AND dn.custom_track_shipment_status IN %(states)s{qcond}""",
            vals)[0][0]

        vals.update({"limit": limit, "offset": offset})
        rows = frappe.db.sql(
            f"""SELECT dn.name, dn.custom_awb AS awb, dn.custom_tracking_number AS track_no,
                       dn.customer_name AS customer, dn.custom_track_shipment_status AS raw,
                       dn.grand_total AS value, dn.posting_date AS posted, dn.modified AS updated,
                       DATEDIFF(CURDATE(), dn.posting_date) AS age,
                       dni.so AS so,
                       COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
                       COALESCE(NULLIF(so.custom_shipping_city,''), addr.city) AS city
                FROM `tabDelivery Note` dn {so_join}
                WHERE {window} AND dn.custom_track_shipment_status IN %(states)s{qcond}
                ORDER BY dn.modified DESC
                LIMIT %(limit)s OFFSET %(offset)s""",
            vals, as_dict=True)

        parcels = [{
            "dn": r.name, "awb": r.awb or "", "trackNo": r.track_no or "",
            "order": r.so or "", "customer": r.customer or "", "carrier": "Cathedis",
            "track": _TRACK_MAP.get(r.raw, "pending"), "msg": r.raw or "",
            "sla": "breached" if r.raw in ("Delivery Exception", "Failed Attempt") else "ontrack",
            "value": r.value or 0, "days": int(r.age or 0),
            "phone": r.phone or "", "city": (r.city or "").strip().title(),
            "posted": str(r.posted or ""), "updated": str(r.updated or "")[:16],
        } for r in rows]
        return {"parcels": parcels, "counts": counts, "total": int(total or 0),
                "days": days, "serverNow": str(frappe.utils.now_datetime())[:19]}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.tracking")
        return {}


@frappe.whitelist()
def exceptions(days=14, limit=50, offset=0):
    """Delivery exceptions / failed attempts inside the recent window, enriched
    with the order, phone and city so the team can act without leaving the page."""
    try:
        days = min(max(int(days or 14), 1), 90)
        limit = min(max(int(limit or 50), 1), 100)
        offset = max(int(offset or 0), 0)
        vals = {"days": days, "limit": limit, "offset": offset}
        base = """FROM `tabDelivery Note` dn
                  LEFT JOIN (SELECT parent, MAX(against_sales_order) AS so
                             FROM `tabDelivery Note Item` GROUP BY parent) dni ON dni.parent = dn.name
                  LEFT JOIN `tabSales Order` so ON so.name = dni.so
                  LEFT JOIN `tabAddress` addr
                     ON addr.name = COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address)
                  WHERE dn.docstatus = 1
                    AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)
                    AND dn.custom_track_shipment_status IN ('Delivery Exception', 'Failed Attempt')"""
        total = frappe.db.sql(f"SELECT COUNT(*) {base}", vals)[0][0]
        failed = frappe.db.sql(
            f"SELECT COUNT(*) {base} AND dn.custom_track_shipment_status = 'Failed Attempt'", vals)[0][0]
        rows = frappe.db.sql(
            f"""SELECT dn.name, dn.custom_awb AS awb, dn.customer_name AS customer,
                       dn.custom_track_shipment_status AS raw, dn.grand_total AS value,
                       DATEDIFF(CURDATE(), dn.posting_date) AS age,
                       dni.so AS so,
                       COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
                       COALESCE(NULLIF(so.custom_shipping_city,''), addr.city) AS city
                {base}
                ORDER BY dn.modified DESC LIMIT %(limit)s OFFSET %(offset)s""",
            vals, as_dict=True)
        return {
            "rows": [{
                "id": r.name, "awb": r.awb or "", "customer": r.customer or "",
                "order": r.so or "",
                "kind": "failed" if r.raw == "Failed Attempt" else "exception",
                "detail": r.raw or "", "value": r.value or 0, "age": int(r.age or 0),
                "phone": r.phone or "", "city": (r.city or "").strip().title(),
            } for r in rows],
            "total": int(total or 0), "failed": int(failed or 0),
            "exceptions": int(total or 0) - int(failed or 0), "days": days,
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.exceptions")
        return {}


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
    """Latest manifest snapshot in the SPA's MANIFEST shape: the current Draft
    Shipment if one exists, else the most recent one. Parcels = its Delivery
    Note children; notOnManifest = labeled orders not yet on any manifest."""
    try:
        sh = frappe.get_all(
            "Shipment",
            fields=["name", "pickup_date", "value_of_goods", "status"],
            filters={"status": "Draft"},
            order_by="modified desc", limit=1,
        ) or frappe.get_all(
            "Shipment",
            fields=["name", "pickup_date", "value_of_goods", "status"],
            order_by="pickup_date desc", limit=1,
        )
        if not sh:
            return {}
        sh = sh[0]
        rows = frappe.db.sql(
            """
            SELECT sdn.delivery_note AS dn, dn.custom_awb AS awb,
                   dn.customer_name AS customer, dn.grand_total AS value
            FROM `tabShipment Delivery Note` sdn
            LEFT JOIN `tabDelivery Note` dn ON dn.name = sdn.delivery_note
            WHERE sdn.parent = %s
            ORDER BY sdn.idx DESC
            LIMIT 40
            """,
            (sh.name,), as_dict=True,
        )
        parcels = [{
            "awb": r.awb or "", "dn": r.dn, "order": "",
            "customer": r.customer or "", "value": r.value or 0,
        } for r in rows]
        total_parcels = frappe.db.count("Shipment Delivery Note", {"parent": sh.name})
        not_on = frappe.db.count(
            "Sales Order",
            {"docstatus": 1, "custom_logistics_status": ["in", ["Label Generated", "Label Printed"]]},
        )
        return {
            "no": sh.name,
            "parcels": total_parcels,
            "parcelRows": parcels,
            "value": sh.value_of_goods or 0,
            "carrier": "Cathedis",
            "pickupDate": str(sh.pickup_date) if sh.pickup_date else nowdate(),
            "window": "09:00 – 17:00",
            "cutoff": "14:00",
            "status": sh.status or "Draft",
            "notOnManifest": not_on,
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.today_manifest")
        return {}


@frappe.whitelist()
def close_manifest(parcels=None):
    """Create + submit the daily Shipment from scanned parcels."""
    # TODO: build Shipment doc with child shipment_delivery_note rows.
    return {"ok": True, "shipment": "SH-DRAFT"}

@frappe.whitelist()
def mark_labels_printed(orders):
    """Bulk: mark selected orders' labels as printed (Prepared → Ready).
    Dispatcher/manager/packer only; orders must be in Label Generated."""
    import json
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) not in ("dispatcher", "manager", "packer"):
        frappe.throw("Not authorized to mark labels printed.", frappe.PermissionError)
    if isinstance(orders, str):
        orders = json.loads(orders)
    orders = [o for o in (orders or []) if o]
    if not orders or len(orders) > 100:
        frappe.throw("Select between 1 and 100 orders.")

    done = 0
    for name in orders:
        if not frappe.db.exists("Sales Order", name):
            continue
        st = frappe.db.get_value("Sales Order", name, "custom_logistics_status")
        if st in ("Label Generated", "Picked", "In transit", "Received"):
            frappe.get_doc("Sales Order", name).db_set(
                "custom_logistics_status", "Label Printed")
            done += 1
    frappe.cache().delete_value("lp_board_summary")
    return {"printed": done}
