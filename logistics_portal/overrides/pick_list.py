"""Pick List: a bundle order is picked as it was SOLD, not as the bundle reads today.

ecommerce_integrations replaces the Pick List controller (CustomPickList) and
decides what each sales order needs from the CURRENT Product Bundle — not from
the order's own Packed Items, which hold the bundle as it was when the customer
bought it. Edit a bundle and every order still waiting carries the old pieces
while the controller asks for the new ones.

That is what happened to "JUSTYOL Top 5 Box" on 2026-09-26 15:39 (MCH09045 out
of stock, swapped for MCH09176 in the definition). From that minute an order
holding MCH09045 could not be picked — remove_incomplete_orders found its list
"short" of MCH09176 and threw the whole order off: 686 such orders picked
before the edit, 1 after, 13 stranded for a week with every piece on the
shelf. And had the list survived, the Delivery Note would have been wrong too:
ERPNext counts "how many boxes were picked" against the current definition,
so a fully picked old box counts as zero.

This subclass changes those two readings and nothing else:

  * _get_required_qty_for_sales_order — a bundle line's components come from
    that order's Packed Items. Lines without packed rows, and orders without
    any, go exactly the original way.
  * _get_pick_list_scope_for_sales_order — the per-order scope the Delivery
    Note is built from maps each bundle to THAT order's composition.

Replayed against the original on 800 prod orders (420 with bundles): 663
identical, 137 different — every one an order carrying the old box. No other
difference.

It is a subclass, so every other behaviour of CustomPickList (stock checks,
the SRE release, background Delivery Notes, whitelisted methods) is inherited
untouched. It wins because Frappe takes the LAST override_doctype_class and
logistics_portal is installed after ecommerce_integrations. If that app is
ever missing, it falls back to ERPNext's own controller rather than break.
"""

import frappe
from frappe.utils import flt

try:
    from ecommerce_integrations.overrides.pick_list import CustomPickList as _Base
except Exception:  # never let a missing app take the Pick List down with it
    from erpnext.stock.doctype.pick_list.pick_list import PickList as _Base


def _packed_by_line(sales_order):
    """{Sales Order Item name: [(component item_code, qty for the whole line)]}
    from the order's own Packed Items — the bundle as it was sold."""
    out = {}
    for r in frappe.db.sql(
            """SELECT parent_detail_docname AS line, item_code, qty
               FROM `tabPacked Item`
               WHERE parent = %s AND parenttype = 'Sales Order'""",
            (sales_order,), as_dict=True):
        out.setdefault(r.line, []).append((r.item_code, flt(r.qty)))
    return out


def _bundle_map_for_order(sales_order):
    """{bundle item_code: {component: qty per ONE bundle}} for this order, the
    shape ERPNext's _get_product_bundle_qty_map returns."""
    packed = _packed_by_line(sales_order)
    if not packed:
        return {}
    out = {}
    for line in frappe.get_all("Sales Order Item", filters={"parent": sales_order},
                               fields=["name", "item_code", "qty"]):
        comps = packed.get(line.name)
        q = flt(line.qty)
        if not comps or not q or line.item_code in out:
            continue
        out[line.item_code] = {code: pq / q for code, pq in comps}
    return out


class PickList(_Base):
    def _get_required_qty_for_sales_order(self, sales_order, bundle_cache):
        packed = _packed_by_line(sales_order)
        if not packed or not hasattr(_Base, "_get_required_qty_for_sales_order"):
            return super()._get_required_qty_for_sales_order(sales_order, bundle_cache)
        required = {}
        for item in frappe.get_all("Sales Order Item", filters={"parent": sales_order},
                                   fields=["name", "item_code", "qty", "delivered_qty"]):
            pending = flt(item.qty) - flt(item.delivered_qty)
            if pending <= 0:
                continue
            comps = packed.get(item.name)
            if comps:
                q = flt(item.qty)
                for code, line_qty in comps:
                    required[code] = required.get(code, 0) + (pending * line_qty / q if q else 0)
                continue
            # Not a packed line: the original rule, verbatim in effect.
            bundle = self._get_bundle_component_qty_map(item.item_code, bundle_cache)
            if bundle:
                for code, qty in bundle.items():
                    required[code] = required.get(code, 0) + pending * flt(qty)
            elif frappe.get_cached_value("Item", item.item_code, "is_stock_item"):
                required[item.item_code] = required.get(item.item_code, 0) + pending
        return required

    def _get_pick_list_scope_for_sales_order(self, sales_order_name):
        scope = super()._get_pick_list_scope_for_sales_order(sales_order_name)
        mine = _bundle_map_for_order(sales_order_name)
        current = scope.get("_get_product_bundle_qty_map") if hasattr(scope, "get") else None
        if mine and current:
            def qty_map(bundles):
                bundles = list(bundles)
                out = current(bundles)
                for b in bundles:
                    if b in mine:
                        out[b] = mine[b]
                return out
            scope._get_product_bundle_qty_map = qty_map
        return scope
