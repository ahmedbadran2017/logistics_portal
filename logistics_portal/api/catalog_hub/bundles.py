"""Catalog Hub — bundles follow Shopify.

A box sold as one product ("KW-bndl-011", two sets of 12 jars) is a Shopify
bundle: the variant has requiresComponents=true and Shopify keeps the recipe in
productVariantComponents. The Shopify item sync knows nothing about that and
creates the box in ERPNext as an ordinary stock item. Every order then reserves
the box itself, which never has stock, so the order can never be picked
(KW-bndl-011..014, November 2026: 9 orders stuck until fixed by hand).

This tick reads the recipes from Shopify and makes ERPNext agree:

  * box item -> not a stock item (Maintain Stock off);
  * a Product Bundle with the components Shopify lists;
  * open orders that already hold the box get their packed items and their
    reservations moved onto the components, so they become pickable.

Turning Maintain Stock off goes through db.set_value on purpose. Item.validate
refuses the change as soon as any submitted Sales Order holds the item, even a
closed one, because it would leave that order's reserved_qty stale. The order
repair below recomputes those reservations, which is what the check protects.
A box with real stock-ledger entries is a different story (stock was counted
on the box), so it is reported and never touched.

What it never does: change a bundle that already exists. A recipe that differs
from Shopify is reported, because changing it changes what open orders ship.
"""

import json

import frappe
from frappe.utils import now_datetime

from logistics_portal.api.catalog_hub.problems import _require_manager
from logistics_portal.api.catalog_hub.sync import shopify_graphql

_STATE_KEY = "lp_bundle_sync_state"
_LOCK_KEY = "lp_bundle_sync_lock"

_QUERY = (
    "query($after: String){ productVariants(first: 100, after: $after,"
    " query: \"requires_components:true\"){"
    " nodes { id sku product { id title status }"
    " productVariantComponents(first: 50){ nodes { quantity"
    " productVariant { id sku } } } }"
    " pageInfo { hasNextPage endCursor } } }"
)


def _num(gid):
    return str(gid or "").rsplit("/", 1)[-1]


def _fetch_bundles():
    """Every Shopify bundle variant with its recipe:
    [{variant, product, sku, title, status, components: [(variant, sku, qty)]}]."""
    out, after = [], None
    for _ in range(50):
        data = shopify_graphql(_QUERY, {"after": after})["data"]["productVariants"]
        for n in data.get("nodes") or []:
            comps = [(_num((c.get("productVariant") or {}).get("id")),
                      (c.get("productVariant") or {}).get("sku") or "",
                      int(c.get("quantity") or 0))
                     for c in (n.get("productVariantComponents") or {}).get("nodes") or []]
            product = n.get("product") or {}
            out.append({"variant": _num(n.get("id")), "product": _num(product.get("id")),
                        "sku": n.get("sku") or "", "title": product.get("title") or "",
                        "status": product.get("status") or "", "components": comps})
        page = data.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        after = page.get("endCursor")
    return out


def _item_for(variant_id, product_id=None):
    """The ERPNext item a Shopify variant is linked to. The variant link is the
    only trustworthy one; the product id is a fallback for single-variant
    products created from products/create, whose item code is the product id.
    Never by SKU: 7,211 SKUs are shared across variants."""
    code = frappe.db.get_value(
        "Ecommerce Item", {"integration": "shopify", "variant_id": variant_id},
        "erpnext_item_code")
    if code:
        return code
    if frappe.db.exists("Item", variant_id):
        return variant_id
    if product_id:
        rows = frappe.db.sql(
            """SELECT erpnext_item_code FROM `tabEcommerce Item`
               WHERE integration = 'shopify' AND integration_item_code = %s""",
            product_id)
        if len(rows) == 1:
            return rows[0][0]
    return None


def _current_recipe(item_code):
    pb = frappe.db.get_value("Product Bundle", {"new_item_code": item_code}, "name")
    if not pb:
        return None, {}
    rows = frappe.db.sql(
        "SELECT item_code, qty FROM `tabProduct Bundle Item` WHERE parent = %s", pb)
    recipe = {}
    for code, qty in rows:
        recipe[code] = recipe.get(code, 0) + float(qty or 0)
    return pb, recipe


def _open_orders_holding(item_code):
    """Submitted, still-open orders with a row of the box that has no packed
    items yet, nothing delivered, and no live pick list behind it."""
    return [r[0] for r in frappe.db.sql(
        """SELECT DISTINCT so.name
           FROM `tabSales Order Item` soi
           JOIN `tabSales Order` so ON so.name = soi.parent
           WHERE soi.item_code = %s AND so.docstatus = 1
             AND so.status NOT IN ('Closed', 'Completed', 'On Hold')
             AND COALESCE(soi.delivered_qty, 0) = 0
             AND NOT EXISTS (SELECT 1 FROM `tabPacked Item` p
                             WHERE p.parent = so.name AND p.parent_detail_docname = soi.name)
             AND NOT EXISTS (SELECT 1 FROM `tabPick List Item` pli
                             JOIN `tabPick List` pl ON pl.name = pli.parent
                             WHERE pli.sales_order = so.name AND pl.docstatus < 2)""",
        item_code)]


def _repair_order(so_name):
    """Give an open order its packed items and move its reservations from the
    box onto the components: the same thing ERPNext does when the order is
    saved after the bundle exists."""
    from erpnext.stock.doctype.packed_item.packed_item import make_packing_list

    so = frappe.get_doc("Sales Order", so_name)
    # Called outside a save, make_packing_list resets the table and rebuilds
    # every row (rows already in the database come back with name=None). Only
    # rows the database does not hold yet are written, so another bundle
    # already packed on the same order is not duplicated.
    held = set(frappe.db.sql(
        """SELECT parent_detail_docname, item_code FROM `tabPacked Item`
           WHERE parenttype = 'Sales Order' AND parent = %s""", so_name))
    make_packing_list(so)
    added = [p for p in so.packed_items
             if (p.parent_detail_docname, p.item_code) not in held]
    for p in added:
        p.db_insert()
    so.update_reserved_qty()
    if added:
        so.add_comment("Comment", "Bundle contents added from Shopify: " + ", ".join(
            f"{p.item_code} × {p.qty:g}" for p in added))
    return len(added)


def _apply(b, box, recipe):
    """Turn `box` into a bundle of `recipe` ({item_code: qty}) and repair its
    open orders. Returns the list of repaired orders."""
    if frappe.db.get_value("Item", box, "is_stock_item"):
        frappe.db.set_value("Item", box, "is_stock_item", 0, update_modified=False)
        frappe.clear_document_cache("Item", box)
    pb = frappe.get_doc({
        "doctype": "Product Bundle", "new_item_code": box,
        "description": f"From Shopify bundle {b['sku'] or b['variant']}",
        "items": [{"item_code": code, "qty": qty} for code, qty in recipe.items()],
    })
    pb.flags.ignore_permissions = True
    pb.insert()
    frappe.get_doc("Item", box).add_comment(
        "Comment", "Bundle created from Shopify: " + ", ".join(
            f"{code} × {qty:g}" for code, qty in recipe.items()))
    repaired = []
    for so_name in _open_orders_holding(box):
        if _repair_order(so_name):
            repaired.append(so_name)
    return repaired


def _reconcile(dry_run=False):
    rows = []
    for b in _fetch_bundles():
        row = {"sku": b["sku"], "title": b["title"][:80], "variant": b["variant"],
               "shopifyStatus": b["status"], "item": None, "state": "", "detail": ""}
        rows.append(row)
        box = _item_for(b["variant"], b["product"])
        row["item"] = box
        if not box:
            row["state"] = "not_in_erpnext"
            continue
        recipe, missing = {}, []
        for vid, sku, qty in b["components"]:
            code = _item_for(vid)
            if not code or qty <= 0:
                missing.append(sku or vid)
                continue
            recipe[code] = recipe.get(code, 0) + qty
        if missing or not recipe:
            row["state"] = "component_missing"
            row["detail"] = ", ".join(missing) or "no components"
            continue
        if box in recipe:
            row["state"] = "contains_itself"
            continue
        row["recipe"] = [{"item": c, "qty": q} for c, q in recipe.items()]
        pb, current = _current_recipe(box)
        if pb:
            same = {c: round(q, 3) for c, q in current.items()} == \
                   {c: round(float(q), 3) for c, q in recipe.items()}
            row["state"] = "ok" if same else "differs"
            if not same:
                row["detail"] = "ERPNext: " + ", ".join(
                    f"{c} × {q:g}" for c, q in current.items())
            continue
        if frappe.db.exists("Stock Ledger Entry", {"item_code": box, "is_cancelled": 0}):
            row["state"] = "box_has_stock_history"
            continue
        if dry_run:
            row["state"] = "would_create"
            row["orders"] = _open_orders_holding(box)
            continue
        try:
            row["orders"] = _apply(b, box, recipe)
            row["state"] = "created"
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            row["state"] = "error"
            row["detail"] = frappe.get_traceback()[-300:]
            frappe.log_error(frappe.get_traceback()[:3000], f"lp bundle sync {box}")
    return rows


def _orphan_boxes():
    """Boxes Shopify does not know as bundles: a 'bndl' SKU sold as one stock
    item with no bundle behind it (KW-bndl-014 was one). Nothing to copy from,
    so a person has to say what is inside."""
    return [dict(r) for r in frappe.db.sql(
        """SELECT i.name AS item, i.custom_sku AS sku, LEFT(i.item_name, 80) AS title,
                  (SELECT COUNT(DISTINCT so.name) FROM `tabSales Order Item` soi
                   JOIN `tabSales Order` so ON so.name = soi.parent
                   WHERE soi.item_code = i.name AND so.docstatus = 1
                     AND so.status NOT IN ('Closed', 'Completed')) AS openOrders
           FROM `tabItem` i
           WHERE i.disabled = 0 AND i.custom_sku LIKE %s
             AND NOT EXISTS (SELECT 1 FROM `tabProduct Bundle` pb
                             WHERE pb.new_item_code = i.name)""",
        ("%bndl%",), as_dict=True)]


def _save_state(state):
    frappe.db.set_default(_STATE_KEY, json.dumps(state, default=str))
    frappe.db.commit()


def sync_tick():
    """Scheduler entry (every 10 minutes). Never throws."""
    cache = frappe.cache()
    if cache.get_value(_LOCK_KEY):
        return
    cache.set_value(_LOCK_KEY, 1, expires_in_sec=540)
    try:
        rows = _reconcile()
        _save_state({"at": str(now_datetime())[:19], "rows": rows,
                     "orphans": _orphan_boxes()})
    except Exception:
        frappe.log_error(frappe.get_traceback()[:3000], "lp bundle sync")
    finally:
        cache.delete_value(_LOCK_KEY)


@frappe.whitelist()
def status():
    """Last run: every Shopify bundle and where ERPNext stands on it, plus the
    'bndl' boxes Shopify does not list as bundles."""
    _require_manager()
    raw = frappe.db.get_default(_STATE_KEY)
    try:
        state = json.loads(raw) if raw else {}
    except Exception:
        state = {}
    state["orphans"] = _orphan_boxes()
    return state


@frappe.whitelist(methods=["POST"])
def run_now(dry_run=0):
    """Manager: run the reconcile now. dry_run=1 only reports."""
    _require_manager()
    dry = str(dry_run) in ("1", "true", "True")
    rows = _reconcile(dry_run=dry)
    state = {"at": str(now_datetime())[:19], "rows": rows,
             "orphans": _orphan_boxes(), "dryRun": dry}
    if not dry:
        _save_state(state)
    return state
