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
    def validate(self):
        # A bank-transfer order is not prepared before accounting posts the
        # transfer (picking._TRANSFER_HELD). The portal's pool and gate
        # already keep it out; this is the Desk's door. Dropped, not refused:
        # one unpaid order must not block the rest of a list.
        if self.docstatus == 0 and self.get("locations"):
            from logistics_portal.api.picking import transfer_held_orders
            held = transfer_held_orders({l.sales_order for l in self.locations if l.sales_order})
            if held:
                self.set("locations", [l for l in self.locations if l.sales_order not in held])
                for i, l in enumerate(self.locations, start=1):
                    l.idx = i
                frappe.msgprint(
                    "Removed — bank transfer not confirmed by accounting yet: "
                    + ", ".join(sorted(held)), indicator="orange", alert=True)
        # An order cancelled while its list was being picked must leave the
        # list at the submit: the submit is what creates every order's
        # Delivery Note and books its carrier label. Stop told the floor to
        # pull the piece but left the row on the list, so the submit cut a
        # label for it anyway — #264068 cancelled 11:29, labelled 11:56 with
        # its list (PL-56599), five times since 2026-09-22, one of them now
        # In Transit. The sort wall already sends the piece to the stop bin;
        # the row goes with it.
        if getattr(self, "_action", "") == "submit" and self.get("locations"):
            from logistics_portal.api.stop import stopped_set
            stopped = stopped_set({l.sales_order for l in self.locations if l.sales_order})
            if stopped:
                keep = [l for l in self.locations if l.sales_order not in stopped]
                if not keep:
                    frappe.throw("Every order on this list is cancelled — cancel the list "
                                 "and put the pieces back instead of submitting it.")
                self.set("locations", keep)
                for i, l in enumerate(self.locations, start=1):
                    l.idx = i
                self.flags.lp_stopped_dropped = sorted(stopped)
                frappe.msgprint(
                    "Removed — cancelled while picking, no label will be made: "
                    + ", ".join(sorted(stopped)), indicator="orange", alert=True)
        # A row whose order line is gone (picking.dropped_lines): the item was
        # dropped from the order after the list was made. Left on the list it
        # breaks the order's Delivery Note at the submit, and the parcel goes
        # out with none (#263123). The piece, if already picked, goes back to
        # its shelf.
        if getattr(self, "_action", "") == "submit" and self.get("locations"):
            from logistics_portal.api.picking import dropped_lines
            gone = dropped_lines(self.locations)
            if gone:
                names = {l.name for l in gone}
                keep = [l for l in self.locations if l.name not in names]
                if not keep:
                    frappe.throw("Every line on this list was removed from its order — cancel the "
                                 "list and put the pieces back instead of submitting it.")
                self.set("locations", keep)
                for i, l in enumerate(self.locations, start=1):
                    l.idx = i
                self.flags.lp_lines_dropped = [
                    {"so": l.sales_order, "item_code": l.item_code, "shelf": l.warehouse or "",
                     "picked": int(l.get("custom_scanned_qty") or 0)} for l in gone]
                back = [f"{l.item_code} → {l.warehouse}" for l in gone if int(l.get("custom_scanned_qty") or 0)]
                frappe.msgprint("Removed — no longer on the order: "
                                + ", ".join(sorted({l.sales_order for l in gone}))
                                + (" · put back: " + ", ".join(back) if back else ""),
                                indicator="orange", alert=True)
        # The same edit, smaller: the order's quantity went DOWN after the list
        # was made. J-010973 on 2026-10-09: on PL-56650 at 19:17 for 2, cut to
        # 1 at 19:20, both pieces scanned — and ERPNext refused every submit
        # with "Total Picked Quantity 2.0 is more than ordered qty 1.0", which
        # the floor never saw (the toast showed a progress note). Each row is
        # trimmed to what the order still allows (its quantity, less what
        # other submitted lists picked for the same line); the extra piece
        # goes back to its shelf.
        if getattr(self, "_action", "") == "submit" and self.get("locations"):
            self._trim_to_order()
        super().validate()

    def _trim_to_order(self):
        rows = [l for l in self.locations if l.get("sales_order_item") and not l.get("product_bundle_item")]
        names = tuple({l.sales_order_item for l in rows})
        if not names:
            return
        ordered = {r[0]: flt(r[1]) for r in frappe.db.sql(
            "SELECT name, stock_qty FROM `tabSales Order Item` WHERE name IN %s", (names,))}
        elsewhere = {r[0]: flt(r[1]) for r in frappe.db.sql(
            """SELECT pli.sales_order_item, SUM(pli.picked_qty) FROM `tabPick List Item` pli
               JOIN `tabPick List` p ON p.name = pli.parent
               WHERE p.docstatus = 1 AND p.name != %s AND pli.sales_order_item IN %s
               GROUP BY pli.sales_order_item""", (self.name or "", names))}
        left = {n: ordered[n] - elsewhere.get(n, 0) for n in names if n in ordered}
        drop, trimmed = set(), []
        for l in sorted(rows, key=lambda x: x.idx):
            if l.sales_order_item not in left:
                continue          # line gone: dropped_lines' business
            cf = flt(l.get("conversion_factor") or 1) or 1
            want = flt(l.stock_qty or l.qty * cf)
            room = max(left[l.sales_order_item], 0)
            if want <= room + 1e-9:
                left[l.sales_order_item] = room - want
                continue
            extra = want - room
            trimmed.append({"so": l.sales_order, "item_code": l.item_code, "shelf": l.warehouse or "",
                            "picked": int(min(flt(l.get("custom_scanned_qty") or 0), extra)), "extra": extra})
            left[l.sales_order_item] = 0
            if room <= 0:
                drop.add(l.name)
                continue
            l.qty = room / cf
            l.stock_qty = room
            l.picked_qty = min(flt(l.picked_qty), room)
        if not trimmed:
            return
        keep = [l for l in self.locations if l.name not in drop]
        if not keep:
            frappe.throw("Nothing on this list is still owed by its orders — cancel the list and put the pieces back.")
        if drop:
            self.set("locations", keep)
            for i, l in enumerate(self.locations, start=1):
                l.idx = i
        self.flags.lp_lines_dropped = (self.flags.get("lp_lines_dropped") or []) + trimmed
        frappe.msgprint("Trimmed to the order's quantity: "
                        + ", ".join(f"{t['so']} −{t['extra']:g}" for t in trimmed)
                        + " · put the extra back on its shelf", indicator="orange", alert=True)

    def on_submit(self):
        super().on_submit()
        for d in self.flags.get("lp_lines_dropped") or []:
            try:
                what = (f"{d['item_code']} trimmed by {d['extra']:g} on {self.name} at its submit — the order "
                        "now asks for less" if d.get("extra") else
                        f"{d['item_code']} removed from {self.name} at its submit — it is no longer on this order")
                frappe.get_doc("Sales Order", d["so"]).add_comment(
                    "Comment", what + (f"; the extra piece goes back to {d['shelf']}" if d["picked"] else "") + ".")
            except Exception:
                frappe.log_error(frappe.get_traceback()[:2000], "pick_list dropped-line comment")
        for so in self.flags.get("lp_stopped_dropped") or []:
            try:
                frappe.get_doc("Sales Order", so).add_comment(
                    "Comment", f"Removed from {self.name} at its submit — the order was cancelled "
                               "while picking, so no Delivery Note or label was made. Its piece "
                               "goes back to the shelf.")
            except Exception:
                frappe.log_error(frappe.get_traceback()[:2000], "pick_list stopped comment")

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
