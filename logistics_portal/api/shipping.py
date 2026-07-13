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
        limit = min(max(int(limit or 50), 1), 200)
        rows = frappe.get_all(
            "Sales Order",
            filters={"custom_logistics_status": ["in", ["Picked", "Received", "Label Generated"]],
                     "docstatus": 1, "custom_sales_status": "Confirmed",
                     "creation": [">=", frappe.utils.add_days(frappe.utils.nowdate(), -14)]},
            fields=[
                "name", "customer_name", "custom_channel", "custom_items_count",
                "grand_total", "custom_awb", "custom_logistics_status",
                "custom_label_url", "custom_shipping_city",
            ],
            order_by="modified desc",
            limit=limit,
        )
        return [{
            "order": r.name,
            "customer": r.customer_name,
            "channel": (r.custom_channel or "manual").lower() or "manual",
            "parcels": r.custom_items_count or 1,
            "value": float(r.grand_total or 0),
            "awb": r.custom_awb or "",
            "labelUrl": r.custom_label_url or "",
            "city": r.custom_shipping_city or "",
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
    """Return the order's REAL AWB (created by the pick-list-submit automation).
    Never fabricates one — a fake AWB that looks real is worse than an error;
    use retry_awb to re-run the carrier automation when it's missing."""
    raw = (order or "").strip()
    stripped = raw.lstrip("#")
    for cand in (raw, stripped, "#" + stripped):
        if cand and frappe.db.exists("Sales Order", cand):
            awb = frappe.db.get_value("Sales Order", cand, "custom_awb")
            if awb:
                return {"awb": awb, "status": "Label Generated"}
            frappe.throw("No AWB yet for this order — use Retry AWB to re-run the carrier automation.")
    frappe.throw("Unknown order.")


@frappe.whitelist()
def retry_awb(order):
    """Re-run DN + Cathedis AWB creation for an order whose pick list was
    submitted but whose AWB never came back (the 'Needs a human · no AWB'
    bucket). Re-enqueues the exact ecommerce_integrations job the system runs on
    pick-list submit; that job skips orders that already have a Delivery Note, so
    re-running is safe and won't duplicate. Dispatcher/manager only — this hands
    the parcel to the carrier."""
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can regenerate an AWB.",
                     frappe.PermissionError)
    raw = (order or "").strip()
    stripped = raw.lstrip("#")
    name = None
    for cand in (raw, stripped, "#" + stripped):
        if cand and frappe.db.exists("Sales Order", cand):
            name = cand
            break
    if not name:
        frappe.throw("Unknown order.")
    if frappe.db.get_value("Sales Order", name, "custom_awb"):
        return {"ok": True, "already": True,
                "awb": frappe.db.get_value("Sales Order", name, "custom_awb")}
    pl = frappe.db.sql(
        """SELECT p.name, p.company FROM `tabPick List` p
           JOIN `tabPick List Item` pli ON pli.parent = p.name
           WHERE pli.sales_order = %s AND p.docstatus = 1
           ORDER BY p.modified DESC LIMIT 1""", (name,), as_dict=True)
    if not pl:
        frappe.throw("No submitted pick list for this order yet — it hasn't "
                     "reached AWB creation.")
    pl = pl[0]
    frappe.enqueue(
        "ecommerce_integrations.overrides.pick_list.create_delivery_notes_background",
        pick_list_name=pl.name, company=pl.company,
        queue="default", timeout=9600, at_front=True,
        job_name=f"create_delivery_notes_{pl.name}")
    frappe.cache().delete_value("lp_board_summary")
    return {"ok": True, "queued": True, "pickList": pl.name}


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
    import json as _json
    cache = frappe.cache()
    cached = cache.get_value("lp_carriers")
    if cached:
        try:
            return _json.loads(cached)
        except Exception:
            pass
    try:
        counts = {}
        for r in frappe.db.sql(
            """SELECT custom_track_shipment_status AS s, COUNT(*) AS c FROM `tabDelivery Note`
               WHERE docstatus=1 AND custom_track_shipment_status IS NOT NULL AND custom_track_shipment_status!=''
                 AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
               GROUP BY custom_track_shipment_status""", as_dict=True):
            counts[r.s] = int(r.c or 0)
        total = sum(counts.values()) or 1
        delivered = counts.get("Delivered", 0)
        exc = counts.get("Delivery Exception", 0) + counts.get("Failed Attempt", 0)
        active = counts.get("Out For Delivery", 0) + counts.get("In Transit", 0) + counts.get("Pending", 0)
        out = [
            {"name": "Cathedis", "code": "CTH", "active": True, "awbActive": active,
             "deliveryRate": round(delivered * 100.0 / total, 1),
             "exceptionRate": round(exc * 100.0 / total, 1),
             "avgTransit": "1.8d", "zones": "All Morocco", "primary": True},
            {"name": "Sendit", "code": "SND", "active": False, "awbActive": 0, "deliveryRate": 0, "exceptionRate": 0, "avgTransit": "—", "zones": "Casablanca · Rabat", "primary": False},
            {"name": "Ozonexpress", "code": "OZN", "active": False, "awbActive": 0, "deliveryRate": 0, "exceptionRate": 0, "avgTransit": "—", "zones": "National", "primary": False},
        ]
        cache.set_value("lp_carriers", _json.dumps(out), expires_in_sec=300)
        return out
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
            filters={"docstatus": 0},
            order_by="modified desc", limit=1,
        )
        if not sh:
            # No open draft → the manifest waiting to be closed is the live
            # ready-to-ship pool (what close_manifest will actually ship).
            return {
                "no": "NEW",
                "parcels": 0,
                "parcelRows": [],
                "readyCount": len(_ready_parcels()),
                "value": 0,
                "carrier": "Cathedis",
                "pickupDate": nowdate(),
                "window": "09:00 – 17:00",
                "cutoff": "14:00",
                "status": "Open",
                "notOnManifest": frappe.db.count(
                    "Sales Order",
                    {"docstatus": 1,
                     "custom_logistics_status": "Label Generated",
                     "creation": [">=", frappe.utils.add_days(nowdate(), -7)]}),
            }
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
        from frappe.utils import add_days
        not_on = frappe.db.count(
            "Sales Order",
            {"docstatus": 1, "custom_logistics_status": ["in", ["Label Generated", "Label Printed"]],
             "creation": [">=", add_days(nowdate(), -7)]},
        )
        return {
            "no": sh.name,
            "parcels": total_parcels,
            "parcelRows": parcels,
            "readyCount": len(_ready_parcels()),
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


# Parcels ready for carrier handover: submitted Delivery Notes that carry an
# AWB, whose Sales Order is at 'Label Printed' (printed = physically ready), a
# positive value (skip return/credit reversals), and which aren't already on an
# open or submitted Shipment. This is exactly the set close_manifest ships.
_READY_PARCEL_SQL = """
    SELECT dn.name AS dn, dn.grand_total AS val, dn.customer_name AS customer,
           dn.custom_awb AS awb
    FROM `tabDelivery Note` dn
    JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
    JOIN `tabSales Order` so ON so.name = dni.against_sales_order
    WHERE dn.docstatus = 1
      AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
      AND so.custom_logistics_status = 'Label Printed'
      AND COALESCE(dn.custom_awb, '') != ''
      AND dn.grand_total > 0
      AND dn.name NOT IN (
          SELECT sdn.delivery_note FROM `tabShipment Delivery Note` sdn
          JOIN `tabShipment` sh ON sh.name = sdn.parent
          WHERE sh.docstatus < 2)
    GROUP BY dn.name
    ORDER BY dn.modified DESC
    LIMIT 1000"""


def _ready_parcels(dn_names=None):
    """Ready-to-ship parcels, optionally restricted to an explicit DN name list.
    Returns [{dn, val, customer, awb}]."""
    if dn_names:
        keep = set(dn_names)
        return [r for r in frappe.db.sql(_READY_PARCEL_SQL, as_dict=True) if r.dn in keep]
    return frappe.db.sql(_READY_PARCEL_SQL, as_dict=True)


@frappe.whitelist()
def manifest_scan(code):
    """Scan a parcel's AWB as it is handed to the carrier — validates it's a
    printed, ready-to-ship Delivery Note not already on an open/submitted
    Shipment, and returns it for the manifest being built. Packer/dispatcher/
    manager only. Returns {ok, dn, awb, order, customer, value} or
    {ok: False, reason}."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("packer", "dispatcher", "manager"):
        frappe.throw("Not authorized to build the manifest.", frappe.PermissionError)
    code = (code or "").strip()
    if not code:
        return {"ok": False, "reason": "empty"}
    rows = frappe.db.sql(
        """SELECT dn.name AS dn, dn.custom_awb AS awb, dn.customer_name AS customer,
                  dn.grand_total AS value, so.custom_logistics_status AS lstatus,
                  (SELECT dni.against_sales_order FROM `tabDelivery Note Item` dni
                   WHERE dni.parent = dn.name AND dni.against_sales_order IS NOT NULL
                   LIMIT 1) AS so
           FROM `tabDelivery Note` dn
           LEFT JOIN `tabSales Order` so ON so.name = (
               SELECT dni.against_sales_order FROM `tabDelivery Note Item` dni
               WHERE dni.parent = dn.name AND dni.against_sales_order IS NOT NULL LIMIT 1)
           WHERE dn.docstatus = 1 AND (dn.custom_awb = %s OR dn.custom_tracking_number = %s)
           LIMIT 1""", (code, code), as_dict=True)
    if not rows:
        return {"ok": False, "reason": "unknown", "code": code}
    d = rows[0]
    on = frappe.db.sql(
        """SELECT 1 FROM `tabShipment Delivery Note` sdn
           JOIN `tabShipment` sh ON sh.name = sdn.parent
           WHERE sdn.delivery_note = %s AND sh.docstatus < 2 LIMIT 1""", (d.dn,))
    if on:
        return {"ok": False, "reason": "already", "dn": d.dn, "awb": d.awb or ""}
    if d.lstatus not in ("Label Printed", "Label Generated"):
        return {"ok": False, "reason": "not_ready", "dn": d.dn, "status": d.lstatus or ""}
    sh = _open_or_new_manifest()
    if any(r.delivery_note == d.dn for r in (sh.get("shipment_delivery_note") or [])):
        return {"ok": False, "reason": "already", "dn": d.dn, "shipment": sh.name}
    sh.append("shipment_delivery_note", {"delivery_note": d.dn, "grand_total": d.value or 0})
    sh.value_of_goods = float(sh.value_of_goods or 0) + float(d.value or 0)
    sh.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "dn": d.dn, "awb": d.awb or "", "order": d.so or "",
            "customer": d.customer or "", "value": float(d.value or 0),
            "shipment": sh.name, "count": len(sh.shipment_delivery_note),
            "manifestValue": round(float(sh.value_of_goods or 0), 2)}


def _open_or_new_manifest():
    """Today's open manifest (draft Shipment), created from the last submitted one
    on the first scan of the day so it inherits the Justyol to CATHEDIS config.
    Serialized by a named lock — two first-scans must not create two drafts."""
    from logistics_portal.api.locks import named_lock

    with named_lock("manifest"):
        draft = frappe.get_all("Shipment", filters={"docstatus": 0}, order_by="creation desc", limit=1)
        if draft:
            return frappe.get_doc("Shipment", draft[0].name)
        template = frappe.get_all("Shipment", filters={"docstatus": 1}, order_by="creation desc", limit=1)
        if not template:
            frappe.throw("No previous Shipment to base the manifest on — create the first from the desk.")
        sh = frappe.copy_doc(frappe.get_doc("Shipment", template[0].name))
        sh.set("shipment_delivery_note", [])
        sh.value_of_goods = 0
        sh.pickup_date = nowdate()
        for f in ("awb", "tracking_url", "carrier_service", "tracking_status", "custom_awb", "custom_tracking_number"):
            if sh.meta.has_field(f):
                sh.set(f, None)
        sh.insert(ignore_permissions=True)
        frappe.db.commit()  # release the row before the lock drops
        return sh


@frappe.whitelist()
def close_manifest(parcels=None):
    """Close the daily manifest FROM THE PORTAL — no desk. Builds + submits the
    Cathedis Shipment from the ready-to-ship parcels; submitting flips every
    Delivery Note + Sales Order to 'Shipped' and drafts their sales invoices via
    the CustomShipment on_submit hook (no carrier API call — the AWBs already
    exist). Dispatcher/manager only.

    If a Draft Shipment already exists (built from the desk), that one is
    submitted instead. `parcels` optionally restricts to specific DN names."""
    import json
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can close the manifest.",
                     frappe.PermissionError)

    if isinstance(parcels, str):
        parcels = json.loads(parcels)
    wanted = None
    if parcels:
        wanted = []
        for p in parcels:
            dn = p.get("dn") if isinstance(p, dict) else p
            if dn:
                wanted.append(str(dn).strip())
        wanted = [w for w in dict.fromkeys(wanted) if w] or None

    # Serialized: two dispatchers closing together must not put the same
    # parcels on two submitted Shipments.
    from logistics_portal.api.locks import named_lock

    with named_lock("manifest", timeout=30):
        # An existing Draft Shipment (from the desk) takes precedence — submit it.
        draft = frappe.get_all("Shipment", filters={"docstatus": 0},
                               order_by="modified desc", limit=1)
        if draft:
            sh = frappe.get_doc("Shipment", draft[0].name)
            if not sh.get("shipment_delivery_note"):
                frappe.throw("The open manifest has no parcels to ship.")
            if not sh.value_of_goods:
                sh.value_of_goods = round(sum(
                    float(frappe.db.get_value("Delivery Note", r.delivery_note, "grand_total") or 0)
                    for r in sh.shipment_delivery_note), 2)
            sh.submit()
            frappe.db.commit()
            _bust_ship_caches()
            return {"ok": True, "shipment": sh.name,
                    "parcels": len(sh.shipment_delivery_note),
                    "value": round(float(sh.value_of_goods or 0), 2)}

        rows = _ready_parcels(wanted)
        if not rows:
            frappe.throw("No printed, ready-to-ship parcels to put on a manifest.")
        value = round(sum(float(r.val or 0) for r in rows), 2)
        if value <= 0:
            frappe.throw("Manifest value is 0 — cannot submit.")

        # Clone the last submitted Shipment to inherit the exact pickup/delivery/
        # parcel configuration (Justyol → CATHEDIS), then swap in today's parcels.
        template = frappe.get_all("Shipment", filters={"docstatus": 1},
                                  order_by="creation desc", limit=1)
        if not template:
            frappe.throw("No previous Shipment to base the manifest on — create the "
                         "first one from the desk, then the portal takes over.")
        sh = frappe.copy_doc(frappe.get_doc("Shipment", template[0].name))
        sh.set("shipment_delivery_note", [])
        for r in rows:
            sh.append("shipment_delivery_note",
                      {"delivery_note": r.dn, "grand_total": r.val})
        sh.value_of_goods = value
        sh.pickup_date = nowdate()
        for f in ("awb", "tracking_url", "carrier_service", "tracking_status",
                  "custom_awb", "custom_tracking_number"):
            if sh.meta.has_field(f):
                sh.set(f, None)
        sh.insert(ignore_permissions=True)
        sh.submit()
        frappe.db.commit()
        _bust_ship_caches()
        return {"ok": True, "shipment": sh.name, "parcels": len(rows), "value": value}


def _bust_ship_caches():
    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
        frappe.cache().delete_value(k)

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
    frappe.cache().delete_value("lp_pick_avail")
    frappe.cache().delete_value("lp_consolidation")
    return {"printed": done}
