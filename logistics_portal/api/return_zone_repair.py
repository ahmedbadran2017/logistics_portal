"""Return Zone repair — supplier-bound returns that are in the building but
not on the books, put back so they can be handed to the supplier.

The case (2026-10-06, sheet "Return" / Feuille 10, 112 lines): pieces
customers sent back, waiting in Return Zone for their supplier (Town Team
mostly). The purchasing team could not book the hand-back because Return
Zone showed nothing. Measured line by line on prod, three different
situations hide behind "not in Return Zone":

  * already handed back — a Purchase Receipt return was booked from Return
    Zone. Nothing to fix (68 of 112 lines).
  * zeroed by a count — Return Zone counts (MAT-RECO-2026-22740, 322 lines,
    15-09; MAT-RECO-2026-00086, 893 lines, 13-07) set the piece to 0 while it
    sat there. Cancelling those counts is not an option: hundreds of other
    lines in them are right, and hundreds of moves came after. So the piece
    is put back with a ONE-line count of today, at the cost the count wrote
    it off at.
  * never booked as a return — the customer's parcel came back but no return
    Delivery Note exists, so the piece left the books on shipping and never
    came back. It is booked now as a return against the order's own
    Delivery Note, into Return Zone (the shape returns_repair uses).

After either fix the line is an ordinary "returned, waiting for the
supplier" line: a Cross-dock supplier's appears on Supplier pickup (which
books the Purchase Receipt return against the original receipt), anyone
else's is returned from Return Zone as before.

Guards, both checked on the server for every action:
  * restore: never more than Return Zone is missing for the item (what its
    non-count moves say it should hold, minus what it holds), and never more
    than counts in Return Zone actually zeroed, minus what this tool already
    put back. The order line must have come back and not been handed over.
  * register: only against a real outward Delivery Note of that order for
    that item; guard_over_return refuses a piece returned twice.
Manager only. Every action leaves a comment on the order.
"""

import json
import re

import frappe
from frappe.utils import flt, nowdate, now_datetime

RZ = "Return Zone - JM"
COMPANY = "Justyol Morocco"
TAG = "Return Zone repair"


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can repair Return Zone.", frappe.PermissionError)


# ── reading the sheet ─────────────────────────────────────────────────────

def _parse(lines):
    """[{sku, order, qty}] from a list or from text pasted out of a sheet
    (SKU, order, qty per line; tab, '|', ';' or ','; an order alone is
    expanded to its items by _expand). A cell holding
    several SKUs ('600024333 /600009368') becomes one line per SKU."""
    if isinstance(lines, str):
        try:
            lines = json.loads(lines)
        except Exception:
            text, lines = lines, []
            for raw in text.splitlines():
                cols = [c.strip() for c in re.split(r"\t|\||;", raw)]
                if len(cols) == 1:
                    cols = [c.strip() for c in raw.split(",")]
                if not cols or not cols[0] or cols[0].upper() in ("SKU",):
                    continue
                q = re.sub(r"\D", "", cols[2]) if len(cols) > 2 else ""
                lines.append({"sku": cols[0], "order": cols[1] if len(cols) > 1 else "",
                              "qty": int(q) if q else 1})
    out = []
    for l in lines or []:
        skus = [s.strip() for s in str(l.get("sku") or "").split("/") if s.strip()]
        if not skus:
            continue
        qty = max(int(l.get("qty") or 1), 1)
        per = qty // len(skus) if qty % len(skus) == 0 else qty
        for s in skus:
            out.append({"sku": s, "order": str(l.get("order") or "").strip(), "qty": per,
                        "item": str(l.get("item") or "").strip()})
    return out[:500]


def _items_for(sku):
    return frappe.db.sql_list(
        "SELECT name FROM `tabItem` WHERE custom_sku = %s OR name = %s", (sku, sku))


def _order_candidates(raw):
    s = re.sub(r"\[merged\]", "", (raw or ""), flags=re.I).strip()
    if not s:
        return []
    up = s.upper().replace(" ", "")
    cands = [s, up]
    if re.fullmatch(r"#?\d{5,7}", up):
        cands.append("#" + up.lstrip("#"))
    if up.startswith("SAL-ORD") or up.startswith("SALORD"):
        digits = re.sub(r"\D", "", up)
        if len(digits) == 9 and digits[:4] in ("2025", "2026"):
            cands.append(f"SAL-ORD-{digits[:4]}-{digits[4:]}")
        elif digits:
            tail = digits[-5:].rjust(5, "0")
            cands += [f"SAL-ORD-2026-{tail}", f"SAL-ORD-2025-{tail}", f"SAL-ORD-{tail}"]
    return list(dict.fromkeys(cands))


def _resolve_order(raw, codes):
    """The Sales Order the sheet names. A year-less 'SAL-ORD-01747' can match
    an order of 2025 and of 2026, so the candidates are ranked by what they
    did with the item: came back > shipped > merely holds it."""
    found = [c for c in _order_candidates(raw) if frappe.db.exists("Sales Order", c)]
    if not found:
        return None
    if not codes:
        return found[0]

    def score(so):
        if not frappe.db.exists("Sales Order Item", {"parent": so, "item_code": ["in", codes]}):
            return 0
        moved = frappe.db.sql(
            """SELECT MAX(dn.is_return) FROM `tabDelivery Note Item` dni
               JOIN `tabDelivery Note` dn ON dn.name = dni.parent
               WHERE dn.docstatus = 1 AND dni.against_sales_order = %s AND dni.item_code IN %s""",
            (so, tuple(codes)))[0][0]
        return 3 if moved == 1 else 2 if moved == 0 else 1

    best = max(found, key=score)
    return best if score(best) else found[0]


# ── what the books say ────────────────────────────────────────────────────

def _zone(code):
    """Return Zone for one item: what its non-count moves say it should hold,
    what it holds, what counts zeroed there, what this tool put back."""
    expected = flt(frappe.db.sql(
        """SELECT SUM(actual_qty) FROM `tabStock Ledger Entry`
           WHERE is_cancelled = 0 AND warehouse = %s AND item_code = %s
             AND voucher_type != 'Stock Reconciliation'""", (RZ, code))[0][0])
    current = flt(frappe.db.get_value("Bin", {"warehouse": RZ, "item_code": code}, "actual_qty"))
    z = frappe.db.sql(
        """SELECT SUM(sri.current_qty - sri.qty), MAX(sr.name),
                  SUBSTRING_INDEX(GROUP_CONCAT(sri.current_valuation_rate ORDER BY sr.posting_date DESC), ',', 1)
           FROM `tabStock Reconciliation Item` sri
           JOIN `tabStock Reconciliation` sr ON sr.name = sri.parent
           WHERE sr.docstatus = 1 AND sri.warehouse = %s AND sri.item_code = %s
             AND sri.qty < sri.current_qty""", (RZ, code))[0]
    restored = flt(frappe.db.sql(
        """SELECT SUM(sri.qty - sri.current_qty)
           FROM `tabStock Reconciliation Item` sri
           JOIN `tabStock Reconciliation` sr ON sr.name = sri.parent
           WHERE sr.docstatus = 1 AND sri.warehouse = %s AND sri.item_code = %s
             AND sri.qty > sri.current_qty
             AND EXISTS (SELECT 1 FROM `tabComment` c
                         WHERE c.reference_doctype = 'Stock Reconciliation'
                           AND c.reference_name = sr.name AND c.content LIKE %s)""",
        (RZ, code, TAG + "%"))[0][0])
    zeroed = flt(z[0])
    missing = max(expected - current, 0)
    return {"expected": expected, "current": current, "zeroed": zeroed, "restored": restored,
            "restorable": max(min(missing, zeroed - restored), 0),
            "count": z[1] or "", "rate": flt(z[2])}


def _line(code, so):
    """The order line's journey: shipped from which note, came back, handed
    to the supplier."""
    if not so:
        return {}
    dn = frappe.db.sql(
        """SELECT dn.name, SUM(dni.qty) FROM `tabDelivery Note Item` dni
           JOIN `tabDelivery Note` dn ON dn.name = dni.parent
           WHERE dn.docstatus = 1 AND dn.is_return = 0
             AND dni.against_sales_order = %s AND dni.item_code = %s
           GROUP BY dn.name ORDER BY dn.posting_date DESC LIMIT 1""", (so, code))
    came = flt(frappe.db.sql(
        """SELECT SUM(-dni.qty) FROM `tabDelivery Note Item` dni
           JOIN `tabDelivery Note` dn ON dn.name = dni.parent
           WHERE dn.docstatus = 1 AND dn.is_return = 1
             AND dni.against_sales_order = %s AND dni.item_code = %s""", (so, code))[0][0])
    collected = flt(frappe.db.sql(
        """SELECT SUM(-pri.qty) FROM `tabPurchase Receipt Item` pri
           JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
           JOIN `tabPurchase Order Item` poi ON poi.parent = pri.purchase_order
                AND poi.item_code = pri.item_code
           WHERE pr.docstatus = 1 AND pr.is_return = 1
             AND poi.sales_order = %s AND pri.item_code = %s""", (so, code))[0][0])
    return {"dn": dn[0][0] if dn else "", "shipped": flt(dn[0][1]) if dn else 0,
            "came": came, "collected": collected}


def _expand(l):
    """A line that names an order and no SKU (a bare '#241854' pasted alone)
    becomes one line per item of that order, at the quantity it shipped."""
    if l["order"] or _items_for(l["sku"]):
        return [l]
    so = _resolve_order(l["sku"], None)
    if not so:
        return [l]
    items = frappe.db.sql(
        """SELECT soi.item_code, IFNULL(NULLIF(i.custom_sku, ''), soi.item_code), SUM(soi.qty)
           FROM `tabSales Order Item` soi LEFT JOIN `tabItem` i ON i.name = soi.item_code
           WHERE soi.parent = %s GROUP BY soi.item_code ORDER BY MIN(soi.idx)""", (so,))
    return [{"sku": sku, "item": code, "order": so, "qty": max(int(flt(q)), 1)}
            for code, sku, q in items] or [l]


def _row(l):
    codes = [l["item"]] if l.get("item") and frappe.db.exists("Item", l["item"]) else _items_for(l["sku"])
    out = {"sku": l["sku"], "orderRaw": l["order"], "qty": l["qty"], "order": "", "item": "",
           "name": "", "supplier": "", "crossdock": False}
    if not codes:
        out["status"] = "unknown_sku"
        return out
    so = _resolve_order(l["order"], codes)
    code = codes[0]
    if so:
        hit = frappe.db.sql_list("SELECT item_code FROM `tabSales Order Item` WHERE parent = %s AND item_code IN %s",
                                 (so, tuple(codes)))
        if hit:
            code = hit[0]
    it = frappe.db.get_value("Item", code, ["item_name", "default_supplier"], as_dict=True) or {}
    sup = it.get("default_supplier") or ""
    out.update({"order": so or "", "item": code, "name": it.get("item_name") or code, "supplier": sup,
                "crossdock": bool(sup) and frappe.db.get_value("Supplier", sup, "custom_fulfillment_model") == "Cross-dock"})
    z = _zone(code)
    out["zone"] = z
    ln = _line(code, so)
    out["line"] = ln
    q = l["qty"]
    if so and ln.get("collected", 0) >= q:
        out["status"] = "collected"
    elif so and ln.get("came", 0) - ln.get("collected", 0) > 0:
        out["status"] = "in_zone" if z["current"] >= q else ("zeroed" if z["restorable"] > 0 else "missing")
    elif so and ln.get("dn"):
        out["status"] = "unregistered"
    elif not so and z["restorable"] > 0:
        out["status"] = "zeroed_no_order"
    else:
        out["status"] = "no_order" if not so else "never_shipped"
    return out


@frappe.whitelist(methods=["POST"])
def check(lines):
    """Every sheet line with what the books say about it and what can be done."""
    _gate()
    rows = [_row(x) for l in _parse(lines) for x in _expand(l)][:500]
    tally = {}
    for r in rows:
        tally[r["status"]] = tally.get(r["status"], 0) + r["qty"]
    return {"rows": rows, "tally": tally}


# ── the two repairs ───────────────────────────────────────────────────────

def _note(so, text):
    if so and frappe.db.exists("Sales Order", so):
        try:
            frappe.get_doc("Sales Order", so).add_comment("Comment", f"{TAG}: {text} · by {frappe.session.user}")
        except Exception:
            pass


@frappe.whitelist(methods=["POST"])
def restore(item_code, qty, order=""):
    """Put back in Return Zone a piece a count zeroed there, at the cost the
    count wrote it off at — a one-line count posted today."""
    _gate()
    qty = flt(qty)
    if qty <= 0:
        frappe.throw("Nothing to restore.")
    z = _zone(item_code)
    if qty > z["restorable"] + 0.001:
        frappe.throw(f"Only {z['restorable']:g} of {item_code} can be put back: Return Zone is missing "
                     f"{max(z['expected'] - z['current'], 0):g}, counts zeroed {z['zeroed']:g} and "
                     f"{z['restored']:g} were already put back.")
    if order:
        ln = _line(item_code, order)
        if ln.get("came", 0) - ln.get("collected", 0) <= 0:
            frappe.throw(f"{order} has no returned, not-handed-back piece of {item_code}.")
    rate = z["rate"] or flt(frappe.db.get_value("Bin", {"warehouse": RZ, "item_code": item_code}, "valuation_rate")) \
        or flt(frappe.db.get_value("Item", item_code, "valuation_rate"))
    # Stock Reconciliation has no remarks column here: the tag that _zone()
    # counts as "already put back" is a comment on the document.
    why = (f"{TAG}: put back {qty:g} wrongly zeroed by {z['count'] or 'a count'}"
           + (f" — order {order}" if order else "") + f" — {frappe.session.user}")
    sr = frappe.get_doc({
        "doctype": "Stock Reconciliation", "company": COMPANY, "purpose": "Stock Reconciliation",
        "posting_date": nowdate(), "set_posting_time": 0,
        "items": [{"item_code": item_code, "warehouse": RZ, "qty": z["current"] + qty,
                   "valuation_rate": rate, "allow_zero_valuation_rate": 0 if rate else 1}],
    })
    sr.flags.ignore_permissions = True
    sr.insert()
    sr.submit()
    sr.add_comment("Comment", why)
    _note(order, f"{qty:g} × {item_code} put back in {RZ} ({sr.name}) — zeroed by {z['count'] or 'a count'}")
    frappe.db.commit()
    return {"ok": True, "doc": sr.name, "qty": qty, "rate": rate}


@frappe.whitelist(methods=["POST"])
def register_return(order, item_code, qty):
    """Book a customer's returned piece that never got its return: a return
    Delivery Note against the order's own outward note, into Return Zone."""
    _gate()
    from erpnext.controllers.sales_and_purchase_return import make_return_doc
    qty = flt(qty)
    ln = _line(item_code, order)
    if not ln.get("dn"):
        frappe.throw(f"{order} has no shipped Delivery Note for {item_code}.")
    left = ln["shipped"] - ln["came"]
    if qty <= 0 or qty > left + 0.001:
        frappe.throw(f"{order} shipped {ln['shipped']:g} of {item_code} and {ln['came']:g} already came back.")
    doc = make_return_doc("Delivery Note", ln["dn"])
    line = next((x for x in doc.items if x.item_code == item_code), None)
    if line is None:
        frappe.throw(f"{ln['dn']} has no line for {item_code}.")
    line.qty = -abs(qty)
    line.stock_qty = line.qty
    line.warehouse = RZ
    doc.items = [line]
    doc.set_warehouse = RZ
    doc.posting_date = nowdate()
    doc.set_posting_time = 0
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    doc.submit()
    doc.add_comment("Comment", f"{TAG}: customer return booked late — {frappe.session.user}")
    _note(order, f"{qty:g} × {item_code} booked as returned into {RZ} ({doc.name})")
    frappe.db.commit()
    return {"ok": True, "doc": doc.name, "qty": qty}
