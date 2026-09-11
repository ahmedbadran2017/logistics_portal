"""SKU label printing as a STAGE — the PDA asks, the print station obeys.

Some stock arrives with no scannable label on the piece. The picker (or the
labeling bench before picking) hits Print on the PDA; the job lands in a tiny
server-side queue; a laptop on the floor keeps /logistics/print-station open
in a Chrome started with --kiosk-printing, polls the queue, and the label
comes out of the attached Zebra silently — no dialog, no person at the
laptop. Same barcode brain as the shelf labels (warehouses._label_payloads),
so what prints here scans back in every flow.

One GLOBAL queue on purpose, not per-account: the floor has one printer, and
scoping jobs to the requesting account would strand them the day the laptop
is signed in as someone else."""

import frappe
from frappe.utils import now_datetime

DT = "LP Label Job"


def ensure_doctype():
    """Create the queue doctype on migrate. Custom doctype, safe every time."""
    try:
        if frappe.db.exists("DocType", DT):
            return
        frappe.get_doc({
            "doctype": "DocType",
            "name": DT,
            "module": "Core",
            "custom": 1,
            "naming_rule": "Autoincrement",
            "autoname": "autoincrement",
            "fields": [
                {"fieldname": "item_code", "fieldtype": "Data", "label": "Item"},
                {"fieldname": "sku", "fieldtype": "Data", "label": "SKU"},
                {"fieldname": "barcode", "fieldtype": "Data", "label": "Barcode payload"},
                {"fieldname": "item_name", "fieldtype": "Data", "label": "Name"},
                {"fieldname": "wide", "fieldtype": "Int", "label": "Needs wide stock"},
                {"fieldname": "qty", "fieldtype": "Int", "label": "Copies", "default": "1"},
                {"fieldname": "station", "fieldtype": "Data", "label": "Station"},
                {"fieldname": "status", "fieldtype": "Select", "label": "Status",
                 "options": "queued\nprinted\ncancelled", "default": "queued",
                 "in_standard_filter": 1},
                {"fieldname": "printed_by", "fieldtype": "Data", "label": "Printed by"},
                {"fieldname": "printed_at", "fieldtype": "Datetime", "label": "Printed at"},
            ],
            "permissions": [
                {"role": "System Manager", "read": 1, "write": 1, "create": 1},
            ],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "labelprint.ensure_doctype")


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if not role:
        frappe.throw("Portal users only.", frappe.PermissionError)
    return role


@frappe.whitelist(methods=["POST"])
def request(code=None, qty=1, station=""):
    """Queue one label job from any scan-shaped identifier (SKU / barcode /
    item code). The barcode payload is decided HERE, by the same rules as the
    shelf labels — a label printed at the bench must scan back identically."""
    _gate()
    from logistics_portal.api.picking import resolve_scan
    from logistics_portal.api.warehouses import _label_payloads
    code = (code or "").strip()
    if not code:
        frappe.throw("Nothing to print.")
    it = resolve_scan(code)
    if not it:
        return {"ok": False, "reason": "unknown"}
    qty = min(max(int(qty or 1), 1), 50)
    pay = _label_payloads([(it["itemCode"], it.get("sku") or "")]) \
        .get(it["itemCode"]) or {}
    frappe.get_doc({
        "doctype": DT,
        "item_code": it["itemCode"],
        "sku": it.get("sku") or "",
        "barcode": pay.get("barcode") or it.get("sku") or it["itemCode"],
        "item_name": (it.get("name") or "")[:140],
        "wide": 1 if pay.get("barcodeWide") else 0,
        "qty": qty,
        "station": (station or "")[:40],
        "status": "queued",
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    pending = frappe.db.count(DT, {"status": "queued"})
    return {"ok": True, "item": it["itemCode"], "sku": it.get("sku") or "",
            "name": it.get("name") or "", "pending": pending}


@frappe.whitelist(methods=["POST"])
def pull(limit=10):
    """The print station's heartbeat: claim the oldest queued jobs and hand
    them over. Claiming = marking printed, so a second station never prints
    the same label twice; a job that jams is re-queued by hand from Desk."""
    _gate()
    limit = min(max(int(limit or 10), 1), 30)
    names = [r[0] for r in frappe.db.sql(
        f"""SELECT name FROM `tab{DT}` WHERE status = 'queued'
            ORDER BY creation LIMIT {limit}""")]
    if not names:
        return {"jobs": [], "pending": 0}
    frappe.db.sql(
        f"""UPDATE `tab{DT}` SET status = 'printed', printed_by = %s,
                printed_at = %s
            WHERE name IN %s AND status = 'queued'""",
        (frappe.session.user, str(now_datetime())[:19], tuple(names)))
    frappe.db.commit()
    jobs = frappe.db.sql(
        f"""SELECT name, item_code, sku, barcode, item_name, wide, qty, station
            FROM `tab{DT}` WHERE name IN %s AND printed_by = %s""",
        (tuple(names), frappe.session.user), as_dict=True)
    pending = frappe.db.count(DT, {"status": "queued"})
    return {"jobs": jobs, "pending": pending}


@frappe.whitelist()
def state():
    """Station screen furniture: depth + the last few printed."""
    _gate()
    pending = frappe.db.count(DT, {"status": "queued"})
    recent = frappe.db.sql(
        f"""SELECT item_code, sku, item_name, qty, station, printed_at
            FROM `tab{DT}` WHERE status = 'printed'
            ORDER BY printed_at DESC LIMIT 12""", as_dict=True)
    return {"pending": pending, "recent": recent}
