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
    out of the RETURN bin that holds the piece (Return Zone first) — never
    a shelf or stock zone, whose units are sellable stock.
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


def _waiting_lines(supplier=None, covered=None):
    """Returned Cross-dock lines still at our warehouse, not yet handed back.

    "Handed back" is decided per supplier and item, not per order. Measured
    2026-10-07: 156 lines waited, 64 of them back from the customer more than
    90 days, and 26 had a Purchase Receipt return for the same item to the
    same supplier booked afterwards on ANOTHER order's receipt — purchasing
    returns from Desk against whichever receipt comes first (PMI49 of #129283
    went back on MAT-PRE-2026-00368, the receipt of #164977). Asked per
    order, the piece looked owed forever, and the order whose receipt was
    used looked collected while its own piece might still be here. So every
    return is a unit given back: first to the order it names, then, if that
    order has nothing left to give back, to the oldest line of the same item
    that came back before the return was posted (_allocate). Only returns out
    of a return bin count for the second step — a Goods In rejection out of
    Receiving is not a customer's parcel.

    `covered`, when a list, collects the lines closed that way or by hand,
    for the "already handed back" list."""
    sups = [supplier] if supplier else _crossdock_suppliers()
    if not sups:
        return []
    rows = frappe.db.sql(f"""
        SELECT soi.supplier, so.name AS so, soi.item_code, i.item_name, i.custom_sku AS sku, i.image,
               soi.qty AS ordered, so.transaction_date,
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
                 WHERE poi.sales_order = so.name AND poi.item_code = soi.item_code) AS orig_pri
        FROM `tabSales Order Item` soi
        JOIN `tabSales Order` so ON so.name = soi.parent
        LEFT JOIN `tabItem` i ON i.name = soi.item_code
        WHERE soi.supplier IN %(sups)s AND so.docstatus = 1 AND {_RETURNED}
          AND so.transaction_date >= CURDATE() - INTERVAL %(days)s DAY
        ORDER BY so.transaction_date""", {"sups": tuple(sups), "days": _ALLOC_DAYS}, as_dict=True)
    lines = []
    for r in rows:
        qty = cint(r.returned_qty or r.ordered or 0)
        if not r.returned_on or qty <= 0:
            continue
        lines.append({"r": r, "supplier": r.supplier, "so": r.so, "itemCode": r.item_code,
                      "qty": qty, "returnedOn": str(r.returned_on), "covered": 0, "by": []})
    _allocate(lines)
    closes = _manual_closes(sups)
    since = str(frappe.utils.add_days(frappe.utils.nowdate(), -_SHOW_DAYS))
    out = []
    for l in lines:
        r = l["r"]
        left = l["qty"] - l["covered"]
        man = closes.get((l["so"], l["itemCode"]))
        if man and left > 0:
            take = min(left, man["qty"])
            left -= take
            l["by"].append({"doc": man["doc"] or man["name"], "qty": take, "so": l["so"],
                            "date": man["at"], "manual": man["name"], "action": man["action"],
                            "note": man["note"], "who": man["who"]})
        if str(r.transaction_date) < since:
            continue
        base = {"supplier": r.supplier, "so": r.so, "itemCode": r.item_code,
                "name": r.item_name or r.item_code, "sku": (r.sku or "").strip(),
                "image": r.image or "", "returnedOn": l["returnedOn"], "returnedTo": r.returned_to or ""}
        if covered is not None and l["by"] and any(b["so"] != l["so"] or b.get("manual") for b in l["by"]):
            covered.append(dict(base, qty=l["qty"] - max(left, 0), by=l["by"]))
        if left <= 0:
            continue
        orig = None
        if r.orig_pri:
            orig = frappe.db.get_value("Purchase Receipt Item", r.orig_pri,
                                       ["parent", "qty", "returned_qty"], as_dict=True)
        out.append(dict(base, qty=left,
                        origReceipt=orig.parent if orig else None,
                        origItem=r.orig_pri if orig else None,
                        returnable=bool(orig) and flt(orig.qty) - flt(orig.returned_qty or 0) > 0))
    _attach_sources(out)
    return out


# Lines are allocated over two years, shown over one: a return can only be
# matched to a line that is loaded, and an old unmatched line must be able to
# absorb the return that was really its own.
_ALLOC_DAYS = 730
_SHOW_DAYS = 365


def _handbacks(keys):
    """(supplier, item) → Purchase Receipt returns: [{doc, date, qty, so, bin}]."""
    sups = tuple({k[0] for k in keys})
    items = tuple({k[1] for k in keys})
    if not sups or not items:
        return {}
    out = {}
    for r in frappe.db.sql("""
            SELECT pr.supplier, pri.item_code, pr.name AS doc, pr.posting_date AS date,
                   -pri.qty AS qty, pri.warehouse AS bin,
                   COALESCE(poi.sales_order,
                            (SELECT MAX(x.sales_order) FROM `tabPurchase Order Item` x
                              WHERE x.parent = pri.purchase_order AND x.item_code = pri.item_code)) AS so
            FROM `tabPurchase Receipt Item` pri
            JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
            LEFT JOIN `tabPurchase Order Item` poi ON poi.name = pri.purchase_order_item
            WHERE pr.docstatus = 1 AND pr.is_return = 1
              AND pr.supplier IN %s AND pri.item_code IN %s
            ORDER BY pr.posting_date, pr.creation""", (sups, items), as_dict=True):
        if flt(r.qty) > 0:
            out.setdefault((r.supplier, r.item_code), []).append(
                {"doc": r.doc, "date": str(r.date), "qty": flt(r.qty), "left": flt(r.qty),
                 "so": r.so or "", "bin": r.bin or ""})
    return out


def _allocate(lines):
    """Spend each supplier's returns on the lines they cover (see _waiting_lines)."""
    keys = {(l["supplier"], l["itemCode"]) for l in lines}
    rets = _handbacks(keys)
    for key in keys:
        pool = rets.get(key) or []
        if not pool:
            continue
        mine = sorted((l for l in lines if (l["supplier"], l["itemCode"]) == key),
                      key=lambda l: (l["returnedOn"], l["so"]))
        # 1. A return that names an order belongs to that order first,
        #    whatever bin it left from (the per-order rule this replaces).
        for l in mine:
            for ret in pool:
                if ret["left"] > 0 and ret["so"] == l["so"] and l["covered"] < l["qty"]:
                    take = min(ret["left"], l["qty"] - l["covered"])
                    ret["left"] -= take
                    l["covered"] += take
                    l["by"].append({"doc": ret["doc"], "qty": take, "so": ret["so"], "date": ret["date"]})
        # 2. What is left of a return out of a return bin covers the oldest
        #    line of the item that had come back by the day it was posted.
        for ret in pool:
            if ret["left"] <= 0 or not _is_return_bin(ret["bin"]):
                continue
            for l in mine:
                if ret["left"] <= 0:
                    break
                if l["covered"] < l["qty"] and l["returnedOn"] <= ret["date"]:
                    take = min(ret["left"], l["qty"] - l["covered"])
                    ret["left"] -= take
                    l["covered"] += take
                    l["by"].append({"doc": ret["doc"], "qty": take, "so": ret["so"], "date": ret["date"]})


def _is_return_bin(wh):
    n = (wh or "").lower()
    return ("return" in n or "retour" in n) and "adjustment" not in n


def _attach_sources(lines):
    """Where each piece physically is — only among RETURN bins: the Return
    Zone, else the bin the return was received into, else any other return
    bin. Never a shelf or a stock zone: a unit there is sellable stock, and
    handing it over would give the supplier our inventory. When the piece is
    only elsewhere, `elsewhere` says where, for a manager to move it first."""
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
        cands = [RETURN_WH] + ([l["returnedTo"]] if _is_return_bin(l["returnedTo"]) else []) \
            + sorted([w for w in have if _is_return_bin(w)], key=lambda w: -have[w])
        for wh in cands:
            if wh and have.get(wh, 0) - used.get((l["itemCode"], wh), 0) >= l["qty"]:
                src = wh
                break
        if src:
            used[(l["itemCode"], src)] = used.get((l["itemCode"], src), 0) + l["qty"]
        l["source"] = src
        l["elsewhere"] = None if src else (max(have, key=lambda w: have[w]) if have else None)


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
            "lines": _waiting_lines(supplier), "canClose": _is_manager()}


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


# ── "Already handed back" — the lines no return will ever explain ──────────
#
# What _allocate cannot match: the piece went back to the supplier with no
# document at all (old orders, a van loaded by hand). A manager closes those
# lines here, with a note, and the books follow what physically happened:
#
#   the ledger still shows the piece in a non-sellable bin (Return Zone, a
#   correcting bin…)  -> it is not there, so it leaves the books: a Purchase
#                         Receipt return when the order has a receipt (the
#                         supplier is credited for what they got back), a
#                         Material Issue when it has none
#   only on a sellable shelf   -> refused: that unit may be real stock; count first
#   nowhere on the books, but a receipt exists  -> closed as "accounting":
#                         the supplier was never credited, a person must say why
#   nowhere, no receipt        -> closed, nothing to book
CLOSE_DT = "LP Pickup Close"


def ensure_doctype():
    try:
        if frappe.db.exists("DocType", CLOSE_DT):
            return
        frappe.get_doc({
            "doctype": "DocType", "name": CLOSE_DT, "module": "Core", "custom": 1,
            "naming_rule": "Expression (old style)", "autoname": "naming_series:", "title_field": "so",
            "fields": [
                {"fieldname": "naming_series", "fieldtype": "Data", "label": "Series",
                 "default": "PKC-.YY..MM.-.####", "hidden": 1},
                {"fieldname": "so", "fieldtype": "Data", "label": "Order", "search_index": 1, "in_list_view": 1},
                {"fieldname": "item_code", "fieldtype": "Data", "label": "Item", "in_list_view": 1},
                {"fieldname": "supplier", "fieldtype": "Data", "label": "Supplier", "search_index": 1,
                 "in_standard_filter": 1},
                {"fieldname": "qty", "fieldtype": "Int", "label": "Qty"},
                {"fieldname": "action", "fieldtype": "Data", "label": "What was booked", "in_list_view": 1,
                 "in_standard_filter": 1},
                {"fieldname": "doc", "fieldtype": "Data", "label": "Document"},
                {"fieldname": "source", "fieldtype": "Data", "label": "Taken from"},
                {"fieldname": "note", "fieldtype": "Small Text", "label": "Note"},
                {"fieldname": "state", "fieldtype": "Data", "label": "State", "default": "active",
                 "search_index": 1},
                {"fieldname": "closed_by", "fieldtype": "Data", "label": "Closed by"},
                {"fieldname": "closed_at", "fieldtype": "Datetime", "label": "Closed at"},
                {"fieldname": "undone_by", "fieldtype": "Data", "label": "Reopened by"},
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "crossdock_pickup.ensure_doctype")


def _manual_closes(sups):
    if not frappe.db.exists("DocType", CLOSE_DT):
        return {}
    out = {}
    for r in frappe.db.sql(f"""SELECT name, so, item_code, qty, action, doc, note, closed_by, closed_at
                               FROM `tab{CLOSE_DT}` WHERE state = 'active' AND supplier IN %s""",
                           (tuple(sups),), as_dict=True):
        e = out.setdefault((r.so, r.item_code), {"name": r.name, "qty": 0, "action": r.action, "doc": r.doc or "",
                                                 "note": r.note or "", "who": r.closed_by or "",
                                                 "at": str(r.closed_at or "")[:10]})
        e["qty"] += cint(r.qty)
    return out


def _manager():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can close a line as already handed back.", frappe.PermissionError)


def _sellable(wh):
    from logistics_portal.api.warehouses import pickable_condition
    cond, args = pickable_condition("w.name")
    return bool(frappe.db.sql(f"SELECT 1 FROM `tabWarehouse` w WHERE w.name = %s AND {cond}",
                              tuple([wh] + list(args))))


def _book_gone(l, qty, src, note):
    """Take a piece that is no longer here off the books. Returns (action, doc)."""
    why = f"{TAG}: handed back earlier, with no document — {note} — {frappe.session.user}"
    if l["returnable"]:
        from erpnext.controllers.sales_and_purchase_return import make_return_doc
        ret = make_return_doc("Purchase Receipt", l["origReceipt"])
        rows = []
        for it in ret.items:
            if it.purchase_receipt_item == l["origItem"]:
                it.qty = it.received_qty = -abs(qty)
                it.stock_qty = it.received_stock_qty = -abs(qty) * flt(it.conversion_factor or 1)
                it.rejected_qty = 0
                it.warehouse = src
                rows.append(it)
        if not rows:
            frappe.throw(f"{l['origReceipt']} has nothing left to return.")
        ret.set("items", rows)
        ret.remarks = why
        ret.flags.ignore_permissions = True
        ret.insert()
        ret.submit()
        return "returned", ret.name
    se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Issue",
                         "purpose": "Material Issue", "company": COMPANY, "remarks": why,
                         "items": [{"item_code": l["itemCode"], "qty": qty, "s_warehouse": src}]})
    se.flags.ignore_permissions = True
    se.insert()
    se.submit()
    return "issued", se.name


@frappe.whitelist(methods=["POST"])
def close_lines(supplier, lines, note=None):
    """lines: [{so, item_code, qty}] the manager says already went back."""
    _manager()
    note = frappe.utils.strip_html(note or "").strip()[:200]
    if not note:
        frappe.throw("Write how they went back (a date, a van, who took them).")
    if isinstance(lines, str):
        lines = json.loads(lines)
    ensure_doctype()
    waiting = {(l["so"], l["itemCode"]): l for l in _waiting_lines(supplier)}
    done, skipped = [], []
    for want in lines or []:
        key = (want.get("so"), want.get("item_code"))
        l = waiting.get(key)
        if not l:
            skipped.append({"so": key[0], "item_code": key[1], "reason": "not_waiting"})
            continue
        qty = min(cint(want.get("qty")) or l["qty"], l["qty"])
        src = l["source"] or (l["elsewhere"] if l["elsewhere"] and not _sellable(l["elsewhere"]) else None)
        if not src and l["elsewhere"]:
            skipped.append({"so": l["so"], "item_code": l["itemCode"], "reason": "on_shelf",
                            "bin": l["elsewhere"]})
            continue
        try:
            if src:
                action, doc = _book_gone(l, qty, src, note)
            else:
                action, doc = ("accounting" if l["returnable"] else "closed"), ""
            frappe.get_doc({"doctype": CLOSE_DT, "so": l["so"], "item_code": l["itemCode"],
                            "supplier": supplier, "qty": qty, "action": action, "doc": doc,
                            "source": src or "", "note": note, "state": "active",
                            "closed_by": frappe.session.user,
                            "closed_at": frappe.utils.now_datetime()}).insert(ignore_permissions=True)
            frappe.get_doc("Sales Order", l["so"]).add_comment(
                "Comment", f"{TAG}: {qty} × {l['sku'] or l['itemCode']} closed as already handed back to "
                           f"{supplier} ({action}{' ' + doc if doc else ''}) — {note} · by {frappe.session.user}")
            frappe.db.commit()
            done.append({"so": l["so"], "item_code": l["itemCode"], "qty": qty, "action": action, "doc": doc})
        except Exception as ex:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback()[:2000], f"crossdock_pickup.close_lines {l['so']}")
            skipped.append({"so": l["so"], "item_code": l["itemCode"], "reason": "failed", "error": str(ex)[:160]})
    return {"ok": not skipped, "done": done, "skipped": skipped}


@frappe.whitelist(methods=["POST"])
def reopen(name):
    """Undo a close that booked nothing. One that booked a document is undone
    by cancelling that document in Desk — then the line comes back by itself."""
    _manager()
    r = frappe.db.get_value(CLOSE_DT, name, ["so", "action", "doc", "state"], as_dict=True)
    if not r or r.state != "active":
        frappe.throw("Nothing to reopen.")
    if r.doc and frappe.db.get_value("Purchase Receipt" if r.action == "returned" else "Stock Entry",
                                     r.doc, "docstatus") == 1:
        frappe.throw(f"{r.doc} took the piece off the books — cancel it in Desk to reopen the line.")
    frappe.db.set_value(CLOSE_DT, name, {"state": "undone", "undone_by": frappe.session.user})
    frappe.get_doc("Sales Order", r.so).add_comment("Comment", f"{TAG}: reopened ({name}) · by {frappe.session.user}")
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def handed_back(supplier):
    """The lines the screen no longer asks for, and why: a return booked on
    another order's receipt, or a manager's close."""
    _gate()
    cov = []
    _waiting_lines(supplier, covered=cov)
    cov.sort(key=lambda c: c["returnedOn"], reverse=True)
    return {"lines": cov[:300], "canClose": _is_manager()}


def _is_manager():
    from logistics_portal.api.auth import resolve_role
    return resolve_role(frappe.session.user) == "manager"
