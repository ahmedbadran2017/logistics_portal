"""Supplier pickup — handing a Cross-dock supplier back their returned goods.

A Cross-dock order the customer sent back lands in our Return Zone. The goods
are the supplier's: they come to collect them, and until now the purchasing
team booked each hand-back by hand in Desk (304 Purchase Receipt returns in
90 days, one person, ~1.2 lines each). This lane does it at the counter:

  * pick the supplier (or scan a piece): every returned line of theirs that
    is still here — the order came back (return Delivery Note) and no
    Purchase Receipt return has been booked for it yet. The same test the
    supplier portal's Returns page uses ("Waiting for pickup").
  * scan each piece as it is handed over (or tick it), write who collects.
  * one "Hand over" books a Purchase Receipt return per original receipt
    (make_return_doc — rates, PO link and accounting from the original),
    out of the bin that actually holds the piece: Return Zone first, then
    where the return was received, then any bin with it.
  * the supplier portal flips those lines to "Collected" on its own.

Lines with no original receipt (old orders, shipped without one) cannot be
returned against anything — they are listed as "needs the purchasing team".
"""

import json

import frappe
from frappe.utils import cint, flt

COMPANY = "Justyol Morocco"
RETURN_WH = "Return Zone - JM"
TAG = "Supplier pickup"


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("manager", "dispatcher", "returns", "packer"):
        frappe.throw("Not authorized.", frappe.PermissionError)


def _crossdock_suppliers():
    if not frappe.db.has_column("Supplier", "custom_fulfillment_model"):
        return []
    return frappe.get_all("Supplier", filters={"custom_fulfillment_model": "Cross-dock"}, pluck="name")


_RETURNED = ("(IFNULL(so.custom_logistics_status, '') = 'Returned' "
             "OR LOWER(TRIM(IFNULL(so.custom_track_shipment_status, ''))) IN ('return', 'returned'))")


def _waiting_lines(supplier=None):
    """Returned Cross-dock lines still at our warehouse, not yet handed back."""
    sups = [supplier] if supplier else _crossdock_suppliers()
    if not sups:
        return []
    rows = frappe.db.sql(f"""
        SELECT soi.supplier, so.name AS so, soi.item_code, i.item_name, i.custom_sku AS sku, i.image,
               soi.qty AS ordered,
               (SELECT MIN(rdn.posting_date) FROM `tabDelivery Note Item` rdi
                  JOIN `tabDelivery Note` rdn ON rdn.name = rdi.parent
                 WHERE rdi.against_sales_order = so.name AND rdi.item_code = soi.item_code
                   AND rdn.is_return = 1 AND rdn.docstatus = 1) AS returned_on,
               (SELECT ABS(SUM(rdi.qty)) FROM `tabDelivery Note Item` rdi
                  JOIN `tabDelivery Note` rdn ON rdn.name = rdi.parent
                 WHERE rdi.against_sales_order = so.name AND rdi.item_code = soi.item_code
                   AND rdn.is_return = 1 AND rdn.docstatus = 1) AS returned_qty,
               (SELECT MAX(rdi.warehouse) FROM `tabDelivery Note Item` rdi
                  JOIN `tabDelivery Note` rdn ON rdn.name = rdi.parent
                 WHERE rdi.against_sales_order = so.name AND rdi.item_code = soi.item_code
                   AND rdn.is_return = 1 AND rdn.docstatus = 1) AS returned_to,
               (SELECT MAX(pri.name) FROM `tabPurchase Order Item` poi
                  JOIN `tabPurchase Receipt Item` pri ON pri.purchase_order_item = poi.name
                  JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent AND pr.docstatus = 1 AND pr.is_return = 0
                 WHERE poi.sales_order = so.name AND poi.item_code = soi.item_code) AS orig_pri,
               (SELECT MIN(cpr.posting_date) FROM `tabPurchase Receipt Item` cpri
                  JOIN `tabPurchase Receipt` cpr ON cpr.name = cpri.parent
                  JOIN `tabPurchase Order Item` cpoi ON cpoi.parent = cpri.purchase_order
                 WHERE cpoi.sales_order = so.name AND cpri.item_code = soi.item_code
                   AND cpr.is_return = 1 AND cpr.docstatus = 1) AS collected_on
        FROM `tabSales Order Item` soi
        JOIN `tabSales Order` so ON so.name = soi.parent
        LEFT JOIN `tabItem` i ON i.name = soi.item_code
        WHERE soi.supplier IN %(sups)s AND so.docstatus = 1 AND {_RETURNED}
          AND so.transaction_date >= CURDATE() - INTERVAL 365 DAY
        ORDER BY so.transaction_date""", {"sups": tuple(sups)}, as_dict=True)
    out = []
    for r in rows:
        if not r.returned_on or r.collected_on:
            continue
        qty = cint(r.returned_qty or r.ordered or 0)
        if qty <= 0:
            continue
        orig = None
        if r.orig_pri:
            orig = frappe.db.get_value("Purchase Receipt Item", r.orig_pri,
                                       ["parent", "qty", "returned_qty"], as_dict=True)
        out.append({"supplier": r.supplier, "so": r.so, "itemCode": r.item_code,
                    "name": r.item_name or r.item_code, "sku": (r.sku or "").strip(),
                    "image": r.image or "", "qty": qty,
                    "returnedOn": str(r.returned_on), "returnedTo": r.returned_to or "",
                    "origReceipt": orig.parent if orig else None,
                    "origItem": r.orig_pri if orig else None,
                    "returnable": bool(orig) and flt(orig.qty) - flt(orig.returned_qty or 0) > 0})
    _attach_sources(out)
    return out


def _attach_sources(lines):
    """Where each piece physically is: Return Zone, else where the return was
    received, else any bin holding it."""
    items = list({l["itemCode"] for l in lines})
    if not items:
        return
    bins = {}
    for b in frappe.db.sql("""SELECT item_code, warehouse, actual_qty FROM `tabBin`
                              WHERE item_code IN %s AND actual_qty > 0""", (tuple(items),), as_dict=True):
        bins.setdefault(b.item_code, {})[b.warehouse] = flt(b.actual_qty)
    used = {}
    for l in lines:
        have = bins.get(l["itemCode"], {})
        src = None
        for wh in [RETURN_WH, l["returnedTo"]] + sorted(have, key=lambda w: -have[w]):
            if wh and have.get(wh, 0) - used.get((l["itemCode"], wh), 0) >= l["qty"]:
                src = wh
                break
        if src:
            used[(l["itemCode"], src)] = used.get((l["itemCode"], src), 0) + l["qty"]
        l["source"] = src


@frappe.whitelist()
def boot():
    _gate()
    sup = {}
    today = frappe.utils.getdate()
    for l in _waiting_lines():
        s = sup.setdefault(l["supplier"], {"supplier": l["supplier"], "lines": 0, "units": 0, "oldestDays": 0})
        s["lines"] += 1
        s["units"] += l["qty"]
        s["oldestDays"] = max(s["oldestDays"], (today - frappe.utils.getdate(l["returnedOn"])).days)
    return {"suppliers": sorted(sup.values(), key=lambda s: -s["oldestDays"]), "recent": _recent()}


@frappe.whitelist()
def supplier_lines(supplier):
    _gate()
    return {"supplier": supplier,
            "supplierName": frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier,
            "lines": _waiting_lines(supplier)}


@frappe.whitelist()
def resolve(code, supplier=None):
    """A scanned piece → its supplier and item code (the screen ticks the
    oldest waiting line of that item)."""
    _gate()
    from logistics_portal.api.picking import resolve_scan
    r = resolve_scan((code or "").strip()) or {}
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown"}
    lines = [l for l in _waiting_lines(supplier or None) if l["itemCode"] == item_code]
    if not lines:
        return {"ok": False, "reason": "not_waiting", "name": r.get("name") or item_code}
    return {"ok": True, "itemCode": item_code, "name": r.get("name") or item_code,
            "supplier": lines[0]["supplier"]}


@frappe.whitelist(methods=["POST"])
def hand_over(supplier, lines, collector, collector_id=None, note=None):
    """lines: [{so, item_code, qty}] — one Purchase Receipt return per original
    receipt, out of the bin holding the piece. Each return commits on its own."""
    _gate()
    from erpnext.controllers.sales_and_purchase_return import make_return_doc
    if isinstance(lines, str):
        lines = json.loads(lines)
    collector = frappe.utils.strip_html(collector or "").strip()[:80]
    if not collector:
        frappe.throw("Write the name of the person collecting.")
    collector_id = frappe.utils.strip_html(collector_id or "").strip()[:40]
    note = frappe.utils.strip_html(note or "").strip()[:120]
    wanted = {(l.get("so"), l.get("item_code")): cint(l.get("qty")) for l in (lines or []) if cint(l.get("qty")) > 0}
    if not wanted:
        frappe.throw("Tick at least one piece.")
    waiting = {(l["so"], l["itemCode"]): l for l in _waiting_lines(supplier)}
    groups, skipped = {}, []
    for key, qty in wanted.items():
        l = waiting.get(key)
        if not l or not l["returnable"] or not l["source"]:
            skipped.append({"so": key[0], "item_code": key[1],
                            "reason": "no_receipt" if l and not l["returnable"] else "no_stock" if l else "not_waiting"})
            continue
        groups.setdefault(l["origReceipt"], []).append((l, min(qty, l["qty"])))
    done, failed = [], []
    who = f"{collector}" + (f" (ID {collector_id})" if collector_id else "")
    for orig, items in groups.items():
        try:
            ret = make_return_doc("Purchase Receipt", orig)
            keep = {l["origItem"]: (l, q) for l, q in items}
            rows = []
            for it in ret.items:
                if it.purchase_receipt_item in keep:
                    l, q = keep[it.purchase_receipt_item]
                    it.qty = -abs(q)
                    it.received_qty = -abs(q)
                    it.stock_qty = -abs(q) * flt(it.conversion_factor or 1)
                    it.received_stock_qty = it.stock_qty
                    it.rejected_qty = 0
                    it.warehouse = l["source"]
                    rows.append(it)
            if not rows:
                raise frappe.ValidationError("nothing left to return on " + orig)
            ret.set("items", rows)
            ret.remarks = (f"{TAG} by {frappe.session.user} — handed to {who}"
                           + (f" — {note}" if note else ""))
            ret.flags.ignore_permissions = True
            ret.insert()
            ret.submit()
            frappe.db.commit()
            for l, q in items:
                done.append({"so": l["so"], "item_code": l["itemCode"], "name": l["name"], "sku": l["sku"],
                             "qty": q, "return": ret.name})
        except Exception as ex:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback()[:2000], f"crossdock_pickup.hand_over {orig}")
            for l, q in items:
                failed.append({"so": l["so"], "item_code": l["itemCode"], "error": str(ex)[:160]})
    return {"ok": not failed, "done": done, "failed": failed, "skipped": skipped,
            "supplierName": frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier,
            "collector": collector, "collectorId": collector_id, "note": note,
            "by": frappe.session.user, "at": str(frappe.utils.now_datetime())[:16]}


def _recent(limit=15):
    rows = frappe.db.sql("""
        SELECT pr.name, pr.supplier, pr.owner, pr.creation, pr.remarks, ROUND(ABS(SUM(pri.qty))) AS units
        FROM `tabPurchase Receipt` pr JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
        WHERE pr.docstatus = 1 AND pr.is_return = 1 AND pr.remarks LIKE %s
          AND pr.creation >= CURDATE() - INTERVAL 7 DAY
        GROUP BY pr.name ORDER BY pr.creation DESC LIMIT %s""", (TAG + "%", limit), as_dict=True)
    return [{"receipt": r.name, "supplier": r.supplier, "units": int(r.units or 0),
             "time": str(r.creation)[5:16],
             "to": (r.remarks or "").split("handed to ", 1)[-1].split(" — ", 1)[0]} for r in rows]
