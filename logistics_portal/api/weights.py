"""Product weights — capture the missing per-unit weight on stocked items.

Weight lives on the Item master (`weight_per_unit` / `weight_uom`), which is the
value receipts and transactions default from — so setting it here is what feeds
accounting and landed-cost distribution downstream.

Entry is in GRAMS (what a scale reads); storage is in KILOGRAMS, because the rest
of the catalog (115k items) is already on `weight_uom = 'Kg'`. Mixing units would
silently corrupt any weight total a landed-cost report sums, so the UI speaks
grams and the Item stores kg — always.

Scope = items physically in stock in a real JM warehouse (the ones you can put on
the scale), missing-weight first, most-recently-received first so the next
landed-cost voucher finds them already weighed.
"""

import frappe

_ROLES = ("manager", "dispatcher", "returns")

# In-stock, real JM warehouses — same universe the floor works, minus the
# structurally-dead ones (transit / defective / old / correcting).
_JM = ("b.warehouse LIKE %s AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s "
       "AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s")
_JM_ARGS = ["% - JM", "Defective%", "Container%", "Air Freight%", "%Old%", "CORRECTING%"]

_MIN_G = 1        # 1 gram floor
_MAX_G = 50000    # 50 kg — a parcelled item above this is almost surely a typo


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in _ROLES:
        frappe.throw("Not authorized to edit product weights.", frappe.PermissionError)


def _row(it):
    kg = float(it.get("weight_per_unit") or 0)
    return {
        "itemCode": it.get("item_code"),
        "sku": (it.get("custom_sku") or "").strip(),
        "name": it.get("item_name") or it.get("item_code"),
        "image": it.get("image") or "",
        "qty": int(it.get("qty") or 0),
        "grams": round(kg * 1000) if kg else 0,
        "hasWeight": kg > 0,
    }


@frappe.whitelist()
def coverage():
    """Headline for the progress bar: of the stocked items, how many are weighed."""
    _gate()
    r = frappe.db.sql(
        f"""SELECT COUNT(DISTINCT it.name) stocked,
                   COUNT(DISTINCT CASE WHEN COALESCE(it.weight_per_unit,0)>0
                                       THEN it.name END) done
            FROM `tabItem` it JOIN `tabBin` b ON b.item_code = it.name
            WHERE it.disabled = 0 AND b.actual_qty > 0 AND {_JM}""",
        tuple(_JM_ARGS), as_dict=True)[0]
    stocked, done = int(r.stocked or 0), int(r.done or 0)
    return {"stocked": stocked, "done": done, "missing": stocked - done,
            "pct": round(100 * done / stocked, 1) if stocked else 100.0}


@frappe.whitelist()
def queue(limit=40, q="", missing_only=1):
    """The worklist: stocked items (missing-weight only by default), most recently
    received first."""
    _gate()
    limit = min(max(int(limit or 40), 1), 100)
    q = (q or "").strip()
    where = ["it.disabled = 0", "b.actual_qty > 0", _JM]
    args = list(_JM_ARGS)
    if int(missing_only or 0):
        where.append("COALESCE(it.weight_per_unit,0) = 0")
    if q:
        like = f"%{q}%"
        where.append("(it.custom_sku LIKE %s OR it.name LIKE %s OR it.item_name LIKE %s "
                     "OR EXISTS(SELECT 1 FROM `tabItem Barcode` bc "
                     "WHERE bc.parent = it.name AND bc.barcode LIKE %s))")
        args += [like, like, like, like]
    rows = frappe.db.sql(
        f"""SELECT it.name item_code, it.custom_sku, it.item_name, it.image,
                   it.weight_per_unit, SUM(b.actual_qty) qty, MAX(b.modified) recv
            FROM `tabItem` it JOIN `tabBin` b ON b.item_code = it.name
            WHERE {' AND '.join(where)}
            GROUP BY it.name
            ORDER BY recv DESC
            LIMIT %s""",
        tuple(args) + (limit,), as_dict=True)
    return {"rows": [_row(r) for r in rows]}


@frappe.whitelist()
def lookup(code):
    """Resolve one scanned/typed code to its stocked item — even if it already
    has a weight, so a wrong one can be corrected."""
    _gate()
    code = (code or "").strip()
    if not code:
        return {"ok": False, "reason": "empty"}
    row = frappe.db.sql(
        f"""SELECT it.name item_code, it.custom_sku, it.item_name, it.image,
                   it.weight_per_unit, COALESCE(SUM(b.actual_qty), 0) qty
            FROM `tabItem` it
            LEFT JOIN `tabBin` b ON b.item_code = it.name AND {_JM}
            WHERE it.disabled = 0
              AND (it.name = %s OR it.custom_sku = %s
                   OR EXISTS(SELECT 1 FROM `tabItem Barcode` bc
                             WHERE bc.parent = it.name AND bc.barcode = %s))
            GROUP BY it.name LIMIT 1""",
        tuple(_JM_ARGS) + (code, code, code), as_dict=True)
    if not row:
        return {"ok": False, "reason": "unknown", "code": code}
    return {"ok": True, "item": _row(row[0])}


@frappe.whitelist()
def set_weight(item_code, grams, apply_siblings=0):
    """Store a per-unit weight. Entry grams -> stored kg (weight_uom='Kg') to keep
    the catalog single-unit. Optionally copies to same-SKU sibling codes (variant-
    level, 2-8 codes = the same physical unit, so the same weight). Written with
    db.set_value so it never fires the Item on_update / Shopify item sync."""
    _gate()
    item_code = (item_code or "").strip()
    try:
        g = float(grams)
    except Exception:
        frappe.throw("Enter a weight in grams.")
    if g < _MIN_G or g > _MAX_G:
        frappe.throw(f"Weight must be between {_MIN_G} g and {int(_MAX_G / 1000)} kg.")
    if not frappe.db.exists("Item", item_code):
        frappe.throw("Unknown item.")
    kg = round(g / 1000.0, 4)

    frappe.db.set_value("Item", item_code, {"weight_per_unit": kg, "weight_uom": "Kg"})
    applied = 1
    if int(apply_siblings or 0):
        sku = frappe.db.get_value("Item", item_code, "custom_sku")
        if sku:
            codes = frappe.db.get_all(
                "Item", filters={"custom_sku": sku, "disabled": 0}, pluck="name")
            # Only variant-level SKUs (<=8 codes) are the same sellable unit; a
            # bare style SKU spans different sizes/colours with different weights.
            if 2 <= len(codes) <= 8:
                for c in codes:
                    if c != item_code:
                        frappe.db.set_value(
                            "Item", c, {"weight_per_unit": kg, "weight_uom": "Kg"})
                        applied += 1
    frappe.db.commit()
    return {"ok": True, "itemCode": item_code, "grams": round(g), "kg": kg,
            "applied": applied}
