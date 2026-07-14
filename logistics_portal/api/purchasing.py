"""PO-linked receiving — Goods In v2.

The audit that led here: 2,085 Purchase Receipts vs 925 loose Material
Receipts in 180 days, same people, same zones — and the 676M MAD Aisles E
corruption was a Material Receipt with a hand-typed valuation rate
(STE-05935). Rates must come from Purchase Orders, not keyboards.

Flow: pick the supplier → scan pieces → ONE submitted Purchase Receipt per
currency (a supplier can hold USD and MAD POs at once), each scan allocated
FIFO against the supplier's oldest open PO lines. Pieces with no open PO
line ride the same receipt as over-receipt rows — but only a manager can
post a session containing them.
"""

import json

import frappe

from logistics_portal.api.stock_moves import RECEIVING_WH, _movable_condition

COMPANY = "Justyol Morocco"
_OPEN_PO = ("po.docstatus = 1 AND po.company = %(company)s "
            "AND po.status NOT IN ('Closed', 'Completed', 'Cancelled')")


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("manager", "dispatcher", "returns", "packer"):
        frappe.throw("Not authorized to receive stock.", frappe.PermissionError)


def _is_manager():
    from logistics_portal.api.auth import resolve_role
    return resolve_role(frappe.session.user) == "manager"


@frappe.whitelist()
def receive_boot():
    """Suppliers with something to receive + target zones + recent receipts."""
    _gate()
    suppliers = frappe.db.sql(
        f"""SELECT po.supplier,
                   COUNT(DISTINCT po.name) AS pos,
                   ROUND(SUM(poi.qty - poi.received_qty)) AS pending,
                   MIN(po.transaction_date) AS oldest
            FROM `tabPurchase Order` po
            JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            WHERE {_OPEN_PO} AND poi.qty > poi.received_qty
            GROUP BY po.supplier ORDER BY pending DESC""",
        {"company": COMPANY}, as_dict=True)
    cond, args = _movable_condition("name")
    warehouses = [w[0] for w in frappe.db.sql(
        f"""SELECT name FROM `tabWarehouse`
            WHERE is_group = 0 AND disabled = 0 AND {cond} ORDER BY name""",
        tuple(args))]
    return {
        "suppliers": [{"name": s.supplier, "pos": int(s.pos or 0),
                       "pending": int(s.pending or 0), "oldest": str(s.oldest or "")}
                      for s in suppliers],
        "warehouses": warehouses,
        "defaultTarget": RECEIVING_WH,
        "isManager": _is_manager(),
        "recent": _recent_prs(10),
    }


@frappe.whitelist()
def receive_scan(supplier, code):
    """Resolve a scanned piece against the supplier's open PO lines."""
    _gate()
    from logistics_portal.api.picking import resolve_scan
    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item", "code": (code or "").strip()}
    row = frappe.db.sql(
        f"""SELECT ROUND(SUM(poi.qty - poi.received_qty)) AS pending
            FROM `tabPurchase Order` po
            JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            WHERE {_OPEN_PO} AND poi.item_code = %(item)s
              AND poi.qty > poi.received_qty AND po.supplier = %(supplier)s""",
        {"company": COMPANY, "item": item_code, "supplier": (supplier or "").strip()},
        as_dict=True)
    pending = int(row[0].pending or 0) if row else 0
    image = frappe.db.get_value("Item", item_code, "image") or ""
    return {"ok": True, "itemCode": item_code, "sku": r.get("sku") or "",
            "name": r.get("name") or item_code, "image": image,
            "pending": pending, "hasPo": pending > 0}


def _open_lines(supplier, item_codes):
    """The supplier's open PO lines for these items, oldest PO first."""
    return frappe.db.sql(
        f"""SELECT poi.name AS po_item, poi.parent AS po, poi.item_code,
                   (poi.qty - poi.received_qty) AS pending, poi.rate,
                   poi.uom, COALESCE(poi.conversion_factor, 1) AS cf,
                   po.currency, po.conversion_rate
            FROM `tabPurchase Order` po
            JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            WHERE {_OPEN_PO} AND po.supplier = %(supplier)s
              AND poi.qty > poi.received_qty AND poi.item_code IN %(items)s
            ORDER BY po.transaction_date, po.creation, poi.idx""",
        {"company": COMPANY, "supplier": supplier, "items": tuple(item_codes)},
        as_dict=True)


@frappe.whitelist()
def post_purchase_receipt(supplier, items=None, target=None, note=None):
    """One scan session → submitted Purchase Receipt(s): scans allocated FIFO
    against the supplier's open PO lines; one receipt per PO currency.
    Leftover qty with no PO line = over-receipt rows (manager only)."""
    _gate()
    supplier = (supplier or "").strip()
    if not supplier or not frappe.db.exists("Supplier", supplier):
        frappe.throw("Pick a supplier.")
    if isinstance(items, str):
        items = json.loads(items)
    items = items or []
    if not items:
        frappe.throw("Scan at least one item.")
    if len(items) > 300:
        frappe.throw("Too many lines for one receipt — post and start a new one.")
    target = (target or "").strip() or RECEIVING_WH
    cond, args = _movable_condition("name")
    if not frappe.db.sql(
            f"""SELECT 1 FROM `tabWarehouse` WHERE name = %s
                AND is_group = 0 AND disabled = 0 AND {cond}""",
            tuple([target, *args])):
        frappe.throw(f"{target} is not a valid receiving bin.")

    wanted = {}
    for it in items:
        code = (it.get("item_code") or "").strip()
        qty = int(it.get("qty") or 0)
        if not code or qty <= 0:
            continue
        if not frappe.db.exists("Item", code):
            frappe.throw(f"Unknown item: {code}")
        wanted[code] = wanted.get(code, 0) + qty
    if not wanted:
        frappe.throw("Scan at least one item.")

    # FIFO allocation against open PO lines, partitioned by PO currency.
    groups = {}   # currency → {"rows": [...], "conversion_rate": flt}
    extras = []   # qty with no open PO line
    lines = _open_lines(supplier, list(wanted))
    by_item = {}
    for ln in lines:
        by_item.setdefault(ln.item_code, []).append(ln)
    for code, qty in wanted.items():
        remaining = qty
        for ln in by_item.get(code, []):
            if remaining <= 0:
                break
            take = min(remaining, int(ln.pending))
            if take <= 0:
                continue
            g = groups.setdefault(ln.currency or "MAD",
                                  {"rows": [], "conversion_rate": float(ln.conversion_rate or 1)})
            row = {"item_code": code, "qty": take, "warehouse": target,
                   "rate": float(ln.rate or 0), "uom": ln.uom,
                   "conversion_factor": float(ln.cf or 1),
                   "purchase_order": ln.po, "purchase_order_item": ln.po_item}
            if not row["rate"]:
                row["allow_zero_valuation_rate"] = 1
            g["rows"].append(row)
            remaining -= take
        if remaining > 0:
            extras.append({"item_code": code, "qty": remaining})

    if extras and not _is_manager():
        detail = ", ".join(f"{e['item_code']} ×{e['qty']}" for e in extras[:5])
        frappe.throw("These pieces have no open PO line at this supplier — "
                     f"only a manager can post an over-receipt: {detail}")
    if extras:
        # Over-receipt rides a MAD receipt (local valuation), no PO link.
        g = groups.setdefault("MAD", {"rows": [], "conversion_rate": 1})
        for e in extras:
            rate = float(frappe.db.get_value("Item", e["item_code"], "valuation_rate") or 0)
            row = {"item_code": e["item_code"], "qty": e["qty"],
                   "warehouse": target, "rate": rate}
            if not rate:
                row["allow_zero_valuation_rate"] = 1
            g["rows"].append(row)
    if not groups:
        frappe.throw("Nothing to receive.")

    note = (note or "").strip()
    made, total_units = [], 0
    for currency, g in groups.items():
        pr = frappe.get_doc({
            "doctype": "Purchase Receipt",
            "supplier": supplier,
            "company": COMPANY,
            "currency": currency,
            "conversion_rate": g["conversion_rate"] or 1,
            "set_warehouse": target,
            "remarks": f"Portal goods-in by {frappe.session.user}"
                       + (f" — {note}" if note else "")
                       + (f" — over-receipt: {len(extras)} lines" if extras and currency == "MAD" else ""),
            "items": g["rows"],
        })
        pr.flags.ignore_permissions = True
        pr.insert(ignore_permissions=True)
        pr.submit()
        made.append(pr.name)
        total_units += sum(int(r["qty"]) for r in g["rows"])
    frappe.db.commit()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    frappe.cache().delete_keys("lp_suggest")
    return {"ok": True, "receipts": made, "units": total_units,
            "matched": total_units - sum(e["qty"] for e in extras),
            "extras": sum(e["qty"] for e in extras), "target": target}


def _recent_prs(limit=10):
    rows = frappe.db.sql(
        """SELECT pr.name, pr.supplier, pr.owner, pr.creation, pr.remarks,
                  COUNT(*) AS ln, ROUND(SUM(pri.qty)) AS units,
                  MAX(pri.warehouse) AS target
           FROM `tabPurchase Receipt` pr
           JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
           WHERE pr.docstatus = 1 AND pr.creation >= CURDATE() - INTERVAL 7 DAY
           GROUP BY pr.name, pr.supplier, pr.owner, pr.creation, pr.remarks
           ORDER BY pr.creation DESC LIMIT %s""", (limit,), as_dict=True)
    return [{
        "receipt": r.name, "supplier": r.supplier or "", "owner": r.owner or "",
        "time": str(r.creation)[5:16], "lines": int(r.ln or 0),
        "units": int(r.units or 0), "target": r.target or "",
        "viaPortal": bool((r.remarks or "").startswith("Portal")),
    } for r in rows]


@frappe.whitelist()
def recent_purchase_receipts(limit=10):
    _gate()
    return {"rows": _recent_prs(min(max(int(limit or 10), 1), 50))}
