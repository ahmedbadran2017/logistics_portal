"""Consignment adapter — supplier_portal owns the policy, this owns the import.

Justyol only HOLDS consignment goods: they belong to the supplier until they
sell. So they live in that supplier's own section (`CN - <supplier> - JM`)
under `Consignment - JM`, and they must never mix into our bins — once two
suppliers' pieces share a shelf nobody can say whose stock sold at settlement.

supplier_portal is the source of truth for every part of that rule. This
module exists so logistics_portal imports it in exactly ONE place and degrades
quietly when the app is absent, the same way `picking._ee_rejected()` does for
ecommerce_integrations. Nothing here re-implements the policy; copying it is
how the two drift apart.

The one fact worth stating twice, because it reads like a bug: a consignment
product is `Item.default_supplier` whose `Supplier.custom_fulfillment_model`
is **"Fulfillment"**. That Select offers only Fulfillment and Cross-dock —
there is no "Consignment" option — and supplier_portal reuses Fulfillment for
it. Measured 2026-09-30: the 20 "Fulfillment" suppliers are exactly the 20
that have a section, set difference empty both ways.

Before go-live (`golive()` is None until site_config `consignment_golive` is
set) supplier_portal's own guards are off. Ours key on the ITEM being
consignment rather than on the date, which is safe either way: routing a
consignment piece to its section is correct today and mandatory later.
"""

import frappe

RECEIVING = "Consignment Receiving - JM"
PARENT = "Consignment - JM"


def _fn(name):
    """The supplier_portal helper, or None when that app isn't installed."""
    try:
        return frappe.get_attr("supplier_portal.api.consignment." + name)
    except Exception:
        return None


def ready():
    return _fn("section_of") is not None


def golive():
    fn = _fn("golive")
    try:
        return fn() if fn else None
    except Exception:
        return None


def section_of(supplier):
    """`CN - <supplier> - JM` for a consignment supplier, else None."""
    fn = _fn("section_of")
    if not fn or not supplier:
        return None
    try:
        return fn(supplier)
    except Exception:
        return None


def section_supplier(warehouse):
    fn = _fn("section_supplier")
    if not fn or not warehouse:
        return None
    try:
        return fn(warehouse)
    except Exception:
        return None


def is_consignment_warehouse(warehouse):
    fn = _fn("is_consignment_warehouse")
    if not fn or not warehouse:
        return False
    try:
        return bool(fn(warehouse))
    except Exception:
        return False


def owner(item_code):
    """(supplier, section) when this item is consignment, else (None, None).

    A supplier whose section is missing or switched off is deliberately NOT
    treated as consignment: better to let the piece move normally than to
    point the floor at a bin ERPNext would refuse the transaction on."""
    if not item_code:
        return None, None
    sup = frappe.db.get_value("Item", item_code, "default_supplier")
    if not sup:
        return None, None
    sec = section_of(sup)
    return (sup, sec) if sec else (None, None)


def sections_for(item_codes):
    """{item_code: section} for the consignment ones — one query for the list,
    then one section lookup per distinct supplier. The pick engine calls this
    per batch, so it must not be a per-item round trip."""
    codes = [c for c in set(item_codes or []) if c]
    if not codes or not ready():
        return {}
    rows = frappe.db.sql(
        """SELECT i.name AS item_code, i.default_supplier AS supplier
           FROM `tabItem` i
           JOIN `tabSupplier` s ON s.name = i.default_supplier
           WHERE i.name IN %(codes)s
             AND s.custom_fulfillment_model = 'Fulfillment'""",
        {"codes": tuple(codes)}, as_dict=True)
    cache, out = {}, {}
    for r in rows:
        if r.supplier not in cache:
            cache[r.supplier] = section_of(r.supplier)
        sec = cache[r.supplier]
        if sec:
            out[r.item_code] = sec
    return out
