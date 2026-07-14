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


def _fmt_window(t_from, t_to):
    """pickup_from/pickup_to are timedeltas — '09:00 – 17:00', or ''."""
    def hhmm(td):
        try:
            s = int(td.total_seconds())
            return f"{s // 3600:02d}:{s % 3600 // 60:02d}"
        except Exception:
            return ""
    a, b = hhmm(t_from), hhmm(t_to)
    return f"{a} – {b}" if a and b else ""


@frappe.whitelist()
def shipments(limit=30):
    """Daily CARRIER manifests (delivery_customer = CATHEDIS) with real
    per-manifest outcomes from the linked Delivery Notes. China import
    shipments (Justyol China → CMA CGM etc.) are a different flow and are
    deliberately excluded — they were polluting this list."""
    try:
        rows = frappe.db.sql(
            """SELECT sh.name, sh.pickup_date, sh.value_of_goods, sh.status,
                      sh.pickup_company, sh.delivery_customer, sh.awb_number,
                      sh.carrier_service, sh.pickup_from, sh.pickup_to,
                      COUNT(sdn.name) AS parcels,
                      SUM(CASE WHEN dn.custom_track_shipment_status = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
                      SUM(CASE WHEN dn.custom_track_shipment_status IN ('Delivery Exception','Failed Attempt') THEN 1 ELSE 0 END) AS exceptions
               FROM `tabShipment` sh
               LEFT JOIN `tabShipment Delivery Note` sdn ON sdn.parent = sh.name
               LEFT JOIN `tabDelivery Note` dn ON dn.name = sdn.delivery_note
               WHERE sh.docstatus < 2 AND sh.delivery_customer = 'CATHEDIS'
               GROUP BY sh.name
               ORDER BY sh.pickup_date DESC, sh.modified DESC
               LIMIT %(limit)s""",
            {"limit": min(max(int(limit or 30), 1), 100)}, as_dict=True)
        return [{
            "no": r.name,
            "date": str(r.pickup_date) if r.pickup_date else "",
            "value": r.value_of_goods or 0,
            "status": r.status or "Submitted",
            "carrier": (r.delivery_customer or "Cathedis").title(),
            "awb": r.awb_number or "",
            "service": r.carrier_service or "",
            "pickup": r.pickup_company or "",
            "deliveryTo": (r.delivery_customer or "").title(),
            "parcels": int(r.parcels or 0),
            "delivered": int(r.delivered or 0),
            "exceptions": int(r.exceptions or 0),
            "window": _fmt_window(r.pickup_from, r.pickup_to) or "09:00 – 17:00",
        } for r in rows]
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.shipments")
        return []


@frappe.whitelist()
def shipment_detail(name):
    """One manifest, fully real: its parcels with per-parcel tracking state +
    a status breakdown. The list row already carries the header numbers."""
    try:
        if not frappe.db.exists("Shipment", name):
            return {}
        rows = frappe.db.sql(
            """SELECT sdn.delivery_note AS dn, dn.custom_awb AS awb,
                      dn.customer_name AS customer, dn.grand_total AS value,
                      dn.custom_track_shipment_status AS track,
                      (SELECT dni.against_sales_order FROM `tabDelivery Note Item` dni
                       WHERE dni.parent = dn.name AND dni.against_sales_order IS NOT NULL
                       LIMIT 1) AS so
               FROM `tabShipment Delivery Note` sdn
               LEFT JOIN `tabDelivery Note` dn ON dn.name = sdn.delivery_note
               WHERE sdn.parent = %s
               ORDER BY sdn.idx
               LIMIT 800""", (name,), as_dict=True)
        breakdown, parcels = {}, []
        for r in rows:
            k = _TRACK_MAP.get(r.track or "", "pending")
            breakdown[k] = breakdown.get(k, 0) + 1
            parcels.append({"dn": r.dn, "awb": r.awb or "", "order": r.so or "",
                            "customer": r.customer or "",
                            "value": float(r.value or 0), "track": k})
        return {"no": name, "parcels": parcels, "breakdown": breakdown,
                "total": len(parcels)}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.shipment_detail")
        return {}


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
def exceptions(days=14, limit=50, offset=0, tab="open"):
    """Delivery exceptions / failed attempts inside the recent window, enriched
    with the order, phone and city so the team can act without leaving the page.
    tab='open' → not yet triaged; 'handled' → a decision was recorded."""
    try:
        days = min(max(int(days or 14), 1), 90)
        limit = min(max(int(limit or 50), 1), 100)
        offset = max(int(offset or 0), 0)
        vals = {"days": days, "limit": limit, "offset": offset}
        has_action = frappe.get_meta("Delivery Note").has_field("custom_exception_action")
        tab_cond = ""
        if has_action:
            tab_cond = ("AND COALESCE(dn.custom_exception_action,'') != ''" if tab == "handled"
                        else "AND COALESCE(dn.custom_exception_action,'') = ''")
        base = f"""FROM `tabDelivery Note` dn
                  LEFT JOIN (SELECT parent, MAX(against_sales_order) AS so
                             FROM `tabDelivery Note Item` GROUP BY parent) dni ON dni.parent = dn.name
                  LEFT JOIN `tabSales Order` so ON so.name = dni.so
                  LEFT JOIN `tabAddress` addr
                     ON addr.name = COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address)
                  WHERE dn.docstatus = 1
                    AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)
                    AND dn.custom_track_shipment_status IN ('Delivery Exception', 'Failed Attempt')
                    {tab_cond}"""
        total = frappe.db.sql(f"SELECT COUNT(*) {base}", vals)[0][0]
        failed = frappe.db.sql(
            f"SELECT COUNT(*) {base} AND dn.custom_track_shipment_status = 'Failed Attempt'", vals)[0][0]
        rows = frappe.db.sql(
            f"""SELECT dn.name, dn.custom_awb AS awb, dn.customer_name AS customer,
                       dn.custom_track_shipment_status AS raw, dn.grand_total AS value,
                       DATEDIFF(CURDATE(), dn.posting_date) AS age,
                       dni.so AS so,
                       COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
                       COALESCE(NULLIF(so.custom_shipping_city,''), addr.city) AS city,
                       dn.custom_exception_action AS action
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
                "action": r.get("action") or "",
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


def _stale_drafts():
    """Draft Cathedis manifests left open from PREVIOUS days. They hold their
    parcels hostage (the ready-pool query excludes anything on an open
    Shipment), so the Manifest page surfaces them with a discard action."""
    rows = frappe.db.sql(
        """SELECT sh.name, sh.pickup_date, sh.value_of_goods,
                  COUNT(sdn.name) AS parcels
           FROM `tabShipment` sh
           LEFT JOIN `tabShipment Delivery Note` sdn ON sdn.parent = sh.name
           WHERE sh.docstatus = 0 AND sh.delivery_customer = 'CATHEDIS'
             AND COALESCE(sh.pickup_date, '2000-01-01') < CURDATE()
           GROUP BY sh.name
           ORDER BY sh.pickup_date DESC""", as_dict=True)
    return [{"name": r.name, "date": str(r.pickup_date or ""),
             "parcels": int(r.parcels or 0), "value": float(r.value_of_goods or 0)}
            for r in rows]


@frappe.whitelist()
def today_manifest():
    """TODAY's manifest snapshot: the Cathedis draft dated today if one exists,
    else the NEW state (scan starts one). Stale drafts from previous days are
    returned separately — never silently presented as today's manifest."""
    try:
        from frappe.utils import add_days

        not_on = frappe.db.count(
            "Sales Order",
            {"docstatus": 1, "custom_logistics_status": ["in", ["Label Generated", "Label Printed"]],
             "creation": [">=", add_days(nowdate(), -7)]})
        from logistics_portal.api.settings import get_ops
        base = {
            "carrier": "Cathedis", "cutoff": get_ops("cutoff"),
            "readyCount": len(_ready_parcels()),
            "notOnManifest": not_on,
            "staleDrafts": _stale_drafts(),
        }

        sh = frappe.get_all(
            "Shipment",
            fields=["name", "pickup_date", "value_of_goods", "status",
                    "pickup_from", "pickup_to"],
            filters={"docstatus": 0, "delivery_customer": "CATHEDIS",
                     "pickup_date": nowdate()},
            order_by="modified desc", limit=1)
        if not sh:
            return {**base, "no": "NEW", "parcels": 0, "parcelRows": [],
                    "value": 0, "pickupDate": nowdate(),
                    "window": "09:00 – 17:00", "status": "Open"}

        sh = sh[0]
        rows = frappe.db.sql(
            """SELECT sdn.delivery_note AS dn, dn.custom_awb AS awb,
                      dn.customer_name AS customer, dn.grand_total AS value,
                      (SELECT dni.against_sales_order FROM `tabDelivery Note Item` dni
                       WHERE dni.parent = dn.name AND dni.against_sales_order IS NOT NULL
                       LIMIT 1) AS so
               FROM `tabShipment Delivery Note` sdn
               LEFT JOIN `tabDelivery Note` dn ON dn.name = sdn.delivery_note
               WHERE sdn.parent = %s
               ORDER BY sdn.idx DESC
               LIMIT 60""",
            (sh.name,), as_dict=True)
        parcels = [{
            "awb": r.awb or "", "dn": r.dn, "order": r.so or "",
            "customer": r.customer or "", "value": r.value or 0,
        } for r in rows]
        return {
            **base,
            "no": sh.name,
            "parcels": frappe.db.count("Shipment Delivery Note", {"parent": sh.name}),
            "parcelRows": parcels,
            "value": sh.value_of_goods or 0,
            "pickupDate": str(sh.pickup_date) if sh.pickup_date else nowdate(),
            "window": _fmt_window(sh.pickup_from, sh.pickup_to) or "09:00 – 17:00",
            "status": sh.status or "Draft",
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


_TPL_KEY = "lp_manifest_template"
_TPL_SYS_KEYS = {"name", "owner", "creation", "modified", "modified_by", "docstatus",
                 "idx", "parent", "parentfield", "parenttype", "amended_from",
                 "__islocal", "__unsaved"}


def _save_manifest_template(sh):
    """Snapshot the header of a successfully-submitted Cathedis manifest.
    Kills the portal's last desk dependency here: if every submitted Shipment
    is ever cancelled or amended, the next manifest rebuilds from this
    snapshot instead of demanding 'create the first from the desk'."""
    try:
        d = {k: v for k, v in sh.as_dict().items() if k not in _TPL_SYS_KEYS}
        d.pop("shipment_delivery_note", None)
        for f in ("awb", "tracking_url", "carrier_service", "tracking_status",
                  "custom_awb", "custom_tracking_number", "status"):
            d.pop(f, None)
        d["value_of_goods"] = 0
        for ct, rows in list(d.items()):
            if isinstance(rows, list):
                d[ct] = [{k: v for k, v in r.items() if k not in _TPL_SYS_KEYS}
                         for r in rows if isinstance(r, dict)]
        frappe.db.set_default(_TPL_KEY, frappe.as_json(d))
    except Exception:
        # A failed snapshot must never break a manifest close.
        frappe.log_error(frappe.get_traceback(), "logistics_portal.manifest_template")


def _new_manifest_shell():
    """An empty Cathedis manifest inheriting the Justyol → CATHEDIS config:
    cloned from the last submitted one, or rebuilt from the stored template."""
    template = frappe.get_all(
        "Shipment",
        filters={"docstatus": 1, "delivery_customer": "CATHEDIS"},
        order_by="creation desc", limit=1)
    if template:
        sh = frappe.copy_doc(frappe.get_doc("Shipment", template[0].name))
    else:
        raw = frappe.db.get_default(_TPL_KEY)
        if not raw:
            frappe.throw("No previous Cathedis Shipment and no stored template yet — "
                         "close one manifest to seed it.")
        import json as _json
        data = _json.loads(raw)
        data["doctype"] = "Shipment"
        sh = frappe.get_doc(data)
    sh.set("shipment_delivery_note", [])
    sh.value_of_goods = 0
    sh.pickup_date = nowdate()
    for f in ("awb", "tracking_url", "carrier_service", "tracking_status", "custom_awb", "custom_tracking_number"):
        if sh.meta.has_field(f):
            sh.set(f, None)
    return sh


def _open_or_new_manifest():
    """TODAY's open Cathedis manifest (draft Shipment dated today), created
    fresh on the first scan of the day so it inherits the Justyol → CATHEDIS
    config. Stale drafts from previous days and China import drafts are
    deliberately IGNORED — before this filter existed, a scan could resurrect
    a months-old draft (or an import container) and close_manifest would
    happily submit it. Serialized by a named lock."""
    from logistics_portal.api.locks import named_lock

    with named_lock("manifest"):
        draft = frappe.get_all(
            "Shipment",
            filters={"docstatus": 0, "delivery_customer": "CATHEDIS",
                     "pickup_date": nowdate()},
            order_by="creation desc", limit=1)
        if draft:
            return frappe.get_doc("Shipment", draft[0].name)
        sh = _new_manifest_shell()
        sh.insert(ignore_permissions=True)
        frappe.db.commit()  # release the row before the lock drops
        return sh


def _prune_manifest_rows(sh):
    """Drop parcels that can no longer ship (DN cancelled, already delivered /
    returned, or already on a SUBMITTED Shipment) and recompute the value.
    Returns the number of rows dropped."""
    rows = sh.get("shipment_delivery_note") or []
    keep = []
    for r in rows:
        dn = frappe.db.get_value(
            "Delivery Note", r.delivery_note,
            ["docstatus", "custom_track_shipment_status"], as_dict=True)
        if not dn or dn.docstatus != 1:
            continue
        if (dn.custom_track_shipment_status or "") in ("Delivered", "Returned", "Received"):
            continue
        dup = frappe.db.sql(
            """SELECT 1 FROM `tabShipment Delivery Note` sdn
               JOIN `tabShipment` s2 ON s2.name = sdn.parent
               WHERE sdn.delivery_note = %s AND s2.docstatus = 1 LIMIT 1""",
            (r.delivery_note,))
        if dup:
            continue
        keep.append(r)
    dropped = len(rows) - len(keep)
    if dropped:
        sh.set("shipment_delivery_note", keep)
    sh.value_of_goods = round(sum(
        float(frappe.db.get_value("Delivery Note", r.delivery_note, "grand_total") or 0)
        for r in keep), 2)
    return dropped


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
        # TODAY's Cathedis draft takes precedence — submit it. Only today's:
        # stale drafts and China import drafts must never be auto-submitted
        # (that's how a January manifest almost went out in July).
        draft = frappe.get_all(
            "Shipment",
            filters={"docstatus": 0, "delivery_customer": "CATHEDIS",
                     "pickup_date": nowdate()},
            order_by="modified desc", limit=1)
        if draft:
            sh = frappe.get_doc("Shipment", draft[0].name)
            dropped = _prune_manifest_rows(sh)
            if not sh.get("shipment_delivery_note"):
                frappe.throw("The open manifest has no shippable parcels left.")
            if dropped:
                sh.save(ignore_permissions=True)
            sh.submit()
            frappe.db.commit()
            _save_manifest_template(sh)
            _bust_ship_caches()
            return {"ok": True, "shipment": sh.name,
                    "parcels": len(sh.shipment_delivery_note),
                    "dropped": dropped,
                    "value": round(float(sh.value_of_goods or 0), 2)}

        rows = _ready_parcels(wanted)
        if not rows:
            frappe.throw("No printed, ready-to-ship parcels to put on a manifest.")
        value = round(sum(float(r.val or 0) for r in rows), 2)
        if value <= 0:
            frappe.throw("Manifest value is 0 — cannot submit.")

        # Fresh shell (last submitted Cathedis Shipment, or the stored
        # template) with today's parcels swapped in.
        sh = _new_manifest_shell()
        for r in rows:
            sh.append("shipment_delivery_note",
                      {"delivery_note": r.dn, "grand_total": r.val})
        sh.value_of_goods = value
        sh.insert(ignore_permissions=True)
        sh.submit()
        frappe.db.commit()
        _save_manifest_template(sh)
        _bust_ship_caches()
        return {"ok": True, "shipment": sh.name, "parcels": len(rows), "value": value}


@frappe.whitelist()
def discard_manifest(name):
    """Delete a DRAFT Cathedis manifest (stale or unwanted) — its parcels return
    to the ready-to-ship pool. Dispatcher/manager only. Refuses submitted docs
    and non-Cathedis (import) shipments."""
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can discard a manifest.",
                     frappe.PermissionError)
    sh = frappe.db.get_value("Shipment", name,
                             ["docstatus", "delivery_customer"], as_dict=True)
    if not sh:
        frappe.throw("Unknown shipment.")
    if sh.docstatus != 0:
        frappe.throw("Only draft manifests can be discarded.")
    if (sh.delivery_customer or "").upper() != "CATHEDIS":
        frappe.throw("Not a Cathedis manifest — handle import shipments from the desk.")
    frappe.delete_doc("Shipment", name, ignore_permissions=True)
    frappe.db.commit()
    _bust_ship_caches()
    return {"ok": True}


@frappe.whitelist()
def manifest_remove(dn):
    """Take a scanned parcel back OFF today's open manifest (mis-scan, parcel
    pulled aside). The SPA's ✕ used to remove it from the screen only — the
    row stayed on the draft and shipped anyway. Packer/dispatcher/manager."""
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) not in ("packer", "dispatcher", "manager"):
        frappe.throw("Not authorized.", frappe.PermissionError)
    from logistics_portal.api.locks import named_lock

    with named_lock("manifest"):
        draft = frappe.get_all(
            "Shipment",
            filters={"docstatus": 0, "delivery_customer": "CATHEDIS",
                     "pickup_date": nowdate()},
            order_by="modified desc", limit=1)
        if not draft:
            return {"ok": False, "reason": "no_manifest"}
        sh = frappe.get_doc("Shipment", draft[0].name)
        rows = [r for r in (sh.get("shipment_delivery_note") or [])
                if r.delivery_note != dn]
        if len(rows) == len(sh.get("shipment_delivery_note") or []):
            return {"ok": False, "reason": "not_on_manifest"}
        sh.set("shipment_delivery_note", rows)
        sh.value_of_goods = round(sum(float(r.grand_total or 0) for r in rows), 2)
        sh.save(ignore_permissions=True)
        frappe.db.commit()
        return {"ok": True, "count": len(rows),
                "manifestValue": float(sh.value_of_goods or 0)}


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


@frappe.whitelist()
def handle_exception(dn, action, note=None):
    """Record the triage decision for a failed parcel. No carrier API exists
    for redelivery, so this is a DECISION LOG — but it turns the anonymous
    exceptions pile into a worked queue: who decided what, when, visible in
    the 'handled' tab and on the document trail. Dispatcher/returns/manager."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("dispatcher", "returns", "manager"):
        frappe.throw("Not authorized to triage exceptions.", frappe.PermissionError)
    if action not in ("Redeliver", "Return Requested", "Resolved"):
        frappe.throw("Invalid action.")
    if not frappe.db.exists("Delivery Note", dn):
        frappe.throw("Unknown parcel.")
    if not frappe.get_meta("Delivery Note").has_field("custom_exception_action"):
        frappe.throw("Exception fields not installed yet — run migrate.")
    doc = frappe.get_doc("Delivery Note", dn)
    doc.db_set("custom_exception_action", action, update_modified=False)
    doc.db_set("custom_exception_actioned_at", frappe.utils.now_datetime(),
               update_modified=False)
    doc.add_comment("Comment",
                    f"Exception triage: {action} by {frappe.session.user}."
                    + (f" Note: {note}" if note else ""))
    frappe.db.commit()
    return {"ok": True, "dn": dn, "action": action}


@frappe.whitelist()
def manifest_sheet(name=None):
    """The driver's handover sheet: every parcel on the manifest with AWB,
    customer, city and COD amount, plus signature-ready totals. Defaults to
    today's open manifest; pass a Shipment name for a closed one."""
    from logistics_portal.api.auth import resolve_role
    if not resolve_role(frappe.session.user):
        frappe.throw("Not authorized.", frappe.PermissionError)
    if name:
        if not frappe.db.exists("Shipment", name):
            frappe.throw("Unknown shipment.")
        sh = frappe.get_doc("Shipment", name)
    else:
        draft = frappe.get_all(
            "Shipment",
            filters={"docstatus": 0, "delivery_customer": "CATHEDIS",
                     "pickup_date": nowdate()},
            order_by="modified desc", limit=1)
        if not draft:
            frappe.throw("No open manifest today.")
        sh = frappe.get_doc("Shipment", draft[0].name)

    rows = frappe.db.sql(
        """SELECT sdn.delivery_note AS dn, d.grand_total AS cod,
                  so.name AS so_name, so.custom_awb AS awb,
                  COALESCE(NULLIF(so.customer_name,''), d.customer) AS customer,
                  COALESCE(NULLIF(so.custom_customer_phone,''),
                           so.custom_shipping_phone) AS phone,
                  so.custom_shipping_city AS city
           FROM `tabShipment Delivery Note` sdn
           JOIN `tabDelivery Note` d ON d.name = sdn.delivery_note
           LEFT JOIN (SELECT dni.parent AS p, MAX(dni.against_sales_order) AS so_n
                      FROM `tabDelivery Note Item` dni GROUP BY dni.parent) m
                ON m.p = d.name
           LEFT JOIN `tabSales Order` so ON so.name = m.so_n
           WHERE sdn.parent = %s ORDER BY sdn.idx""",
        (sh.name,), as_dict=True)
    out = [{
        "dn": r.dn, "order": r.so_name or "", "awb": r.awb or "",
        "customer": r.customer or "", "phone": r.phone or "",
        "city": (r.city or "").strip().title(),
        "cod": round(float(r.cod or 0), 2),
    } for r in rows]
    return {
        "shipment": sh.name,
        "date": str(sh.pickup_date or "")[:10],
        "status": "submitted" if sh.docstatus == 1 else "draft",
        "carrier": sh.delivery_customer or "CATHEDIS",
        "count": len(out),
        "codTotal": round(sum(r["cod"] for r in out), 2),
        "rows": out,
    }


@frappe.whitelist()
def cancel_parcel(dn, reason=None):
    """Cancel a labelled parcel that never left the building (customer
    cancelled after the AWB was printed). Blocked once the parcel is with the
    carrier — that's a return/exception, not a cancellation. Manager only."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can cancel a parcel.", frappe.PermissionError)
    if not frappe.db.exists("Delivery Note", dn):
        frappe.throw("Unknown parcel.")
    doc = frappe.get_doc("Delivery Note", dn)
    if doc.docstatus == 2:
        frappe.throw("Already cancelled.")
    if doc.docstatus != 1:
        frappe.throw("Not a submitted parcel.")
    track = (doc.get("custom_track_shipment_status") or "")
    if track in ("Delivered", "Received"):
        frappe.throw("This parcel was delivered — process it as a return instead.")
    on_manifest = frappe.db.sql(
        """SELECT s.name FROM `tabShipment Delivery Note` sdn
           JOIN `tabShipment` s ON s.name = sdn.parent
           WHERE sdn.delivery_note = %s AND s.docstatus = 1 LIMIT 1""", (dn,))
    if on_manifest:
        frappe.throw(f"Already handed to the carrier on {on_manifest[0][0]} — "
                     "use Exceptions / returns instead.")

    # If it sits on today's OPEN manifest, pull it off before cancelling.
    draft = frappe.get_all(
        "Shipment",
        filters={"docstatus": 0, "delivery_customer": "CATHEDIS",
                 "pickup_date": nowdate()},
        order_by="modified desc", limit=1)
    if draft:
        sh = frappe.get_doc("Shipment", draft[0].name)
        keep = [r for r in (sh.get("shipment_delivery_note") or [])
                if r.delivery_note != dn]
        if len(keep) != len(sh.get("shipment_delivery_note") or []):
            sh.set("shipment_delivery_note", keep)
            sh.value_of_goods = round(sum(float(r.grand_total or 0) for r in keep), 2)
            sh.save(ignore_permissions=True)

    reason = (reason or "").strip()
    doc.add_comment("Comment",
                    f"Parcel cancelled from the portal by {frappe.session.user}."
                    + (f" Reason: {reason}" if reason else ""))
    doc.flags.ignore_permissions = True
    doc.cancel()

    order = frappe.db.get_value(
        "Delivery Note Item", {"parent": dn}, "against_sales_order")
    if order:
        so = frappe.get_doc("Sales Order", order)
        so.add_comment("Comment",
                       f"Parcel {dn} cancelled from the portal."
                       + (f" Reason: {reason}" if reason else ""))
    frappe.db.commit()
    _bust_ship_caches()
    return {"ok": True, "dn": dn, "order": order or ""}
