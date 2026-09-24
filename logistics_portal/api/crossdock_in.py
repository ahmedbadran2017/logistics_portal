"""Cross-dock in — receiving goods a Cross-dock supplier brings for orders.

Why a separate lane from Goods In (purchasing.py): a Cross-dock supplier keeps
the stock at their place, so every confirmed customer order gets its OWN
Purchase Order ("{order}-{supplier}-JM", custom_sales_order). A supplier who
walks in with 15 parcels is 15 POs — 15 Goods In sessions — and scanning a
piece there offers every open PO carrying that item. Measured before this lane
(2026-09-24, last 30 days): the Purchase Receipt was posted on average ~9 days
AFTER the order had already shipped, so the receipt was paperwork, not the
moment the goods arrived, and the supplier's hand-over time was unmeasurable.

Model
  * The screen is supplier-first: pick the supplier who is at the door (or scan
    an order number / a piece), see every order still waiting on them, scan the
    pieces — each scan goes to the OLDEST waiting order that still needs it.
  * One "Receive" posts one submitted Purchase Receipt per PO (rates from the
    PO, never typed) into Cross-dock - JM: a staging bin, not a shelf — these
    goods leave the same day, so they are never queued for put-away.
  * The received units are RESERVED for their own order (Stock Reservation
    Entry), so an older order for the same SKU cannot take them. The pick-list
    engine already credits an order its own reservation and releases it when
    picking starts (picking._release_order_reservations).
  * Next's own tracking fields are kept true (PO custom_purchase_status
    "Delivered in WH", item custom_received, SO item custom_status) — written
    directly, so no save cascade fires; the purchasing team stops editing them
    by hand.
  * A problem (missing / damaged / wrong item) is recorded on the PO and the
    order as a comment the supplier portal can read.
"""

import json

import frappe
from frappe.utils import cint, flt, now_datetime

COMPANY = "Justyol Morocco"
CROSSDOCK_WH = "Cross-dock - JM"
PARENT_WH = "Soft Warehouse - JM"
COMMENT_TAG = "Cross-dock in"
PROBLEMS = ("missing", "damaged", "wrong_item", "other")

# An order is still expected from its supplier while it is confirmed and the
# floor has not started on it. Orders already shipped / returned with an open
# PO are old paperwork (cleanup), not goods at the door.
_EXPECTED = """
    po.docstatus = 1 AND po.company = %(company)s
    AND po.status NOT IN ('Closed', 'Completed', 'Cancelled')
    AND IFNULL(po.custom_sales_order, '') != ''
    AND s.custom_fulfillment_model = 'Cross-dock'
    AND so.docstatus = 1
    AND so.status NOT IN ('Closed', 'Completed', 'Cancelled')
    AND IFNULL(so.custom_sales_status, '') = 'Confirmed'
    AND IFNULL(so.custom_logistics_status, 'Pending') IN ('', 'Pending')
    AND poi.qty > poi.received_qty
"""


def ensure_warehouse():
    """after_migrate: the staging bin must exist (idempotent)."""
    if frappe.db.exists("Warehouse", CROSSDOCK_WH):
        return
    try:
        wh = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "Cross-dock",
                             "company": COMPANY, "is_group": 0,
                             "parent_warehouse": PARENT_WH if frappe.db.exists("Warehouse", PARENT_WH) else None})
        wh.flags.ignore_permissions = True
        wh.insert()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "crossdock_in.ensure_warehouse")


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("manager", "dispatcher", "returns", "packer"):
        frappe.throw("Not authorized to receive stock.", frappe.PermissionError)


def _ready():
    return frappe.db.has_column("Supplier", "custom_fulfillment_model")


def _expected_lines(supplier=None, so=None):
    """Every still-open line on a Cross-dock PO whose order is waiting."""
    if not _ready():
        return []
    cond, args = _EXPECTED, {"company": COMPANY}
    if supplier:
        cond += " AND po.supplier = %(supplier)s"
        args["supplier"] = supplier
    if so:
        cond += " AND po.custom_sales_order = %(so)s"
        args["so"] = so
    return frappe.db.sql(
        f"""SELECT po.name AS po, po.supplier, po.custom_sales_order AS so,
                   po.creation AS po_created, poi.name AS po_item,
                   poi.sales_order_item, poi.item_code, i.custom_sku AS sku,
                   i.item_name, i.image, poi.qty AS ordered, poi.received_qty AS received,
                   (poi.qty - poi.received_qty) AS pending
            FROM `tabPurchase Order` po
            JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            JOIN `tabSupplier` s ON s.name = po.supplier
            JOIN `tabSales Order` so ON so.name = po.custom_sales_order
            JOIN `tabItem` i ON i.name = poi.item_code
            WHERE {cond}
            ORDER BY po.creation, poi.idx""", args, as_dict=True)


def _hours(since):
    try:
        return round((now_datetime() - since).total_seconds() / 3600, 1)
    except Exception:
        return None


def _orders(lines):
    """Group expected lines into order cards, oldest first."""
    out, by = [], {}
    for l in lines:
        o = by.get(l.po)
        if not o:
            o = by[l.po] = {"po": l.po, "so": l.so, "supplier": l.supplier,
                            "confirmedAt": str(l.po_created)[:16], "ageH": _hours(l.po_created),
                            "lines": []}
            out.append(o)
        o["lines"].append({
            "poItem": l.po_item, "itemCode": l.item_code, "sku": (l.sku or "").strip(),
            "name": l.item_name or l.item_code, "image": l.image or "",
            "ordered": int(l.ordered or 0), "received": int(l.received or 0),
            "pending": int(l.pending or 0),
        })
    for o in out:
        o["pending"] = sum(x["pending"] for x in o["lines"])
    return out


@frappe.whitelist()
def boot():
    """Suppliers with orders waiting at their place + today's receipts."""
    _gate()
    sup = {}
    for o in _orders(_expected_lines()):
        s = sup.setdefault(o["supplier"], {"supplier": o["supplier"], "orders": 0,
                                           "units": 0, "oldestH": 0})
        s["orders"] += 1
        s["units"] += o["pending"]
        s["oldestH"] = max(s["oldestH"], o["ageH"] or 0)
    return {
        "ready": _ready() and bool(frappe.db.exists("Warehouse", CROSSDOCK_WH)),
        "target": CROSSDOCK_WH,
        "suppliers": sorted(sup.values(), key=lambda s: -s["oldestH"]),
        "recent": _recent(),
    }


@frappe.whitelist()
def supplier_orders(supplier):
    _gate()
    return {"supplier": supplier, "orders": _orders(_expected_lines(supplier=supplier))}


def _norm_order(code):
    c = (code or "").strip()
    if not c:
        return None
    for cand in (c, "#" + c.lstrip("#")):
        if frappe.db.exists("Sales Order", cand):
            return cand
    po_so = frappe.db.get_value("Purchase Order", c, "custom_sales_order")
    return po_so or None


@frappe.whitelist()
def resolve(code, supplier=None):
    """A scan: an order number (or its PO) → that order; otherwise a piece →
    the oldest waiting order (of this supplier, if one is open) that needs it."""
    _gate()
    code = (code or "").strip()
    so = _norm_order(code)
    if so:
        lines = _expected_lines(so=so)
        if not lines:
            return {"ok": False, "reason": "order_not_expected", "so": so}
        return {"ok": True, "kind": "order", "supplier": lines[0].supplier, "so": so,
                "po": lines[0].po}
    from logistics_portal.api.picking import resolve_scan
    r = resolve_scan(code) or {}
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown", "code": code}
    cands = [l for l in _expected_lines(supplier=supplier or None) if l.item_code == item_code]
    if not cands:
        return {"ok": False, "reason": "not_expected", "itemCode": item_code,
                "name": r.get("name") or item_code}
    return {"ok": True, "kind": "piece", "itemCode": item_code, "name": r.get("name") or item_code,
            "supplier": cands[0].supplier,
            # every order (oldest first) that still needs it — the screen fills
            # them in this order as the same SKU is scanned again.
            "targets": [{"po": l.po, "poItem": l.po_item, "pending": int(l.pending or 0)} for l in cands]}


def _reserve(pr, so_item_rows):
    """Hold the received units for their own order. Never blocks the receipt."""
    try:
        from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
            get_available_qty_to_reserve)
    except Exception:
        get_available_qty_to_reserve = None
    made = 0
    for r in so_item_rows:
        try:
            soi = frappe.db.get_value(
                "Sales Order Item", r["sales_order_item"],
                ["parent", "item_code", "stock_qty", "delivered_qty", "conversion_factor", "stock_uom"],
                as_dict=True)
            if not soi:
                continue
            held = flt(frappe.db.sql(
                """SELECT SUM(reserved_qty - delivered_qty) FROM `tabStock Reservation Entry`
                   WHERE docstatus = 1 AND status NOT IN ('Delivered', 'Cancelled')
                     AND voucher_type = 'Sales Order' AND voucher_detail_no = %s""",
                r["sales_order_item"])[0][0])
            need = flt(soi.stock_qty) - flt(soi.delivered_qty) * flt(soi.conversion_factor or 1) - held
            avail = flt(get_available_qty_to_reserve(soi.item_code, CROSSDOCK_WH)) \
                if get_available_qty_to_reserve else flt(r["qty"])
            qty = min(flt(r["qty"]), need, avail)
            if qty <= 0:
                continue
            sre = frappe.get_doc({
                "doctype": "Stock Reservation Entry", "company": COMPANY,
                "item_code": soi.item_code, "warehouse": CROSSDOCK_WH,
                "voucher_type": "Sales Order", "voucher_no": soi.parent,
                "voucher_detail_no": r["sales_order_item"],
                "available_qty": avail, "voucher_qty": flt(soi.stock_qty),
                "reserved_qty": qty, "stock_uom": soi.stock_uom,
                "reservation_based_on": "Qty",
                "from_voucher_type": "Purchase Receipt", "from_voucher_no": pr.name,
                "from_voucher_detail_no": r.get("pr_item"),
            })
            sre.flags.ignore_permissions = True
            sre.insert()
            sre.submit()
            made += 1
        except Exception:
            frappe.log_error(frappe.get_traceback()[:2000], f"crossdock_in.reserve {pr.name}")
    return made


def _sync_next_fields(po):
    """Keep ecommerce_integrations' purchase tracking true without a save
    cascade: received lines ticked, PO "Delivered in WH" once nothing is
    pending, the order's lines stamped the same."""
    rows = frappe.db.sql(
        """SELECT name, qty, received_qty, sales_order_item FROM `tabPurchase Order Item`
           WHERE parent = %s""", po, as_dict=True)
    has_soi_status = frappe.db.has_column("Sales Order Item", "custom_status")
    done = 0
    for r in rows:
        if flt(r.received_qty) >= flt(r.qty):
            done += 1
            frappe.db.set_value("Purchase Order Item", r.name, "custom_received", 1,
                                update_modified=False)
            if has_soi_status and r.sales_order_item:
                frappe.db.set_value("Sales Order Item", r.sales_order_item, "custom_status",
                                    "Delivered in WH", update_modified=False)
    vals = {"custom_received_items_count": done}
    if rows and done == len(rows):
        vals["custom_purchase_status"] = "Delivered in WH"
    frappe.db.set_value("Purchase Order", po, vals, update_modified=False)


def _comment(doctype, name, text):
    try:
        frappe.get_doc(doctype, name).add_comment("Comment", text)
    except Exception:
        pass


def _receive_one(po, items, problem, note):
    h = frappe.db.get_value("Purchase Order", po,
                            ["name", "supplier", "currency", "conversion_rate", "docstatus",
                             "status", "company", "custom_sales_order"], as_dict=True)
    if not h or h.docstatus != 1 or h.company != COMPANY \
            or h.status in ("Closed", "Completed", "Cancelled"):
        frappe.throw(f"{po}: not open.")
    open_lines = {l.po_item: l for l in _expected_lines(so=h.custom_sales_order) if l.po == po}
    if not open_lines:
        frappe.throw(f"{po}: this order is no longer waiting for its supplier.")

    rows, so_rows = [], []
    for it in items or []:
        li = open_lines.get(it.get("po_item"))
        qty = cint(it.get("qty"))
        if not li or qty <= 0:
            continue
        if qty > cint(li.pending):
            frappe.throw(f"{po}: {li.item_code} — only {cint(li.pending)} expected.")
        poi = frappe.db.get_value("Purchase Order Item", li.po_item,
                                  ["rate", "uom", "conversion_factor"], as_dict=True)
        row = {"item_code": li.item_code, "qty": qty, "warehouse": CROSSDOCK_WH,
               "rate": flt(poi.rate), "uom": poi.uom,
               "conversion_factor": flt(poi.conversion_factor or 1),
               "purchase_order": po, "purchase_order_item": li.po_item}
        if not row["rate"]:
            row["allow_zero_valuation_rate"] = 1
        rows.append(row)
        if li.sales_order_item:
            so_rows.append({"po_item": li.po_item, "sales_order_item": li.sales_order_item,
                            "qty": qty * flt(poi.conversion_factor or 1)})

    pr = None
    if rows:
        pr = frappe.get_doc({
            "doctype": "Purchase Receipt", "supplier": h.supplier, "company": COMPANY,
            "currency": h.currency or "MAD", "conversion_rate": flt(h.conversion_rate or 1),
            "set_warehouse": CROSSDOCK_WH,
            "remarks": f"{COMMENT_TAG} by {frappe.session.user} — PO {po} — order {h.custom_sales_order}"
                       + (f" — {note}" if note else ""),
            "items": rows,
        })
        pr.flags.ignore_permissions = True
        pr.insert(ignore_permissions=True)
        pr.submit()
        for pri in pr.items:
            for r in so_rows:
                if r["po_item"] == pri.purchase_order_item:
                    r["pr_item"] = pri.name
        _reserve(pr, so_rows)
        _sync_next_fields(po)

    units = sum(r["qty"] for r in rows)
    left = sum(cint(l.pending) for l in open_lines.values()) - units
    if pr:
        _comment("Sales Order", h.custom_sales_order,
                 f"{COMMENT_TAG}: {units} unit(s) received from {h.supplier} into {CROSSDOCK_WH} "
                 f"({pr.name}) by {frappe.session.user}"
                 + (f" — {left} still expected" if left > 0 else " — complete, reserved for this order"))
    if problem and problem.get("kind") in PROBLEMS:
        txt = (f"{COMMENT_TAG} problem [{problem['kind']}]: "
               + (frappe.utils.strip_html(problem.get("note") or "")[:300] or "—")
               + f" · by {frappe.session.user}")
        _comment("Purchase Order", po, txt)
        _comment("Sales Order", h.custom_sales_order, txt)
    return {"po": po, "so": h.custom_sales_order, "receipt": pr.name if pr else None,
            "units": units, "left": max(0, left), "problem": (problem or {}).get("kind")}


@frappe.whitelist(methods=["POST"])
def receive(entries, note=None):
    """entries: [{po, items: [{po_item, qty}], problem?: {kind, note}}] — one
    Purchase Receipt per PO, each committed on its own so one bad order never
    rolls back the rest of the drop."""
    _gate()
    if not frappe.db.exists("Warehouse", CROSSDOCK_WH):
        ensure_warehouse()
    if isinstance(entries, str):
        entries = json.loads(entries)
    entries = [e for e in (entries or []) if e.get("po")][:60]
    if not entries:
        frappe.throw("Scan at least one piece.")
    note = (note or "").strip()[:80]
    done, failed = [], []
    for e in entries:
        try:
            if not any(cint(i.get("qty")) > 0 for i in e.get("items") or []) and not e.get("problem"):
                continue
            done.append(_receive_one(e["po"], e.get("items"), e.get("problem"), note))
            frappe.db.commit()
        except Exception as ex:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback()[:2000], f"crossdock_in.receive {e.get('po')}")
            failed.append({"po": e.get("po"), "error": str(ex)[:200]})
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    frappe.cache().delete_keys("lp_suggest")
    return {"ok": not failed, "done": done, "failed": failed,
            "receipts": [d["receipt"] for d in done if d["receipt"]],
            "units": sum(d["units"] for d in done)}


def _recent(limit=15):
    rows = frappe.db.sql(
        """SELECT pr.name, pr.supplier, pr.owner, pr.creation, pr.remarks,
                  ROUND(SUM(pri.qty)) AS units
           FROM `tabPurchase Receipt` pr
           JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
           WHERE pr.docstatus = 1 AND pr.remarks LIKE %s
             AND pr.creation >= CURDATE() - INTERVAL 2 DAY
           GROUP BY pr.name ORDER BY pr.creation DESC LIMIT %s""",
        (COMMENT_TAG + "%", limit), as_dict=True)
    out = []
    for r in rows:
        so = ""
        if " — order " in (r.remarks or ""):
            so = r.remarks.split(" — order ", 1)[1].split(" — ", 1)[0]
        out.append({"receipt": r.name, "supplier": r.supplier or "", "so": so,
                    "time": str(r.creation)[5:16], "units": int(r.units or 0),
                    "by": (r.owner or "").split("@")[0]})
    return out


@frappe.whitelist()
def recent():
    _gate()
    return {"rows": _recent()}
