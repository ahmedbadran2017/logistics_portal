"""Shopify stock guard: stock on a shelf Shopify was never told about.

The Shopify fork pushes an item's stock only when that item's stock moves
(SLE / SRE submit → sync_single_item_inventory_to_shopify), and it counts only
the warehouses in Shopify Setting's mapping. Two holes follow:

1. A new consignment shelf is not in the mapping until somebody adds it on
   the Desk. Its stock is invisible to Shopify meanwhile. CN - l'oreal paris
   was created 2026-10-15 and mapped 2026-11-04; CN - Awani was created
   11-10 and mapped 11-16; CN - LALUNA was created 2026-11-26 with 47 SKUs
   and no mapping at all.
2. Adding the mapping row re-pushes nothing. An item moved onto the shelf
   before the row existed keeps the number Shopify got at the move. Example:
   HUILE EXTRAORDINAIRE JOJOBA (9057182220542) moved C3 → CN - l'oreal paris
   on 11-03 13:37. It was synced a second later as 0, because the shelf was
   unmapped. It was still 0 on Shopify on 11-26 with 6 on the shelf
   (Khadija's report).

The guard closes both:
- every enabled leaf under Consignment - JM gets a mapping row to the
  location the other consignment shelves use; consignment stock is for sale
  by definition, and all 23 existing sections were already mapped;
- every item with stock on a mapped shelf whose last push is older than that
  shelf's mapping row is pushed again through the fork's own function, so
  the number is the fork's number, not ours.

It runs hourly, when a Warehouse is created or re-parented, and when Shopify
Setting is saved (that is when a person adds a row by hand). It does nothing
while the Shopify stock push is switched off.
"""

import frappe

SETTING = "Shopify Setting"
TABLE = "shopify_warehouse_mapping"
SYNC_FN = "ecommerce_integrations.shopify.inventory.sync_single_item_inventory_to_shopify"
CN_PARENT = "Consignment - JM"
BATCH = 300


def _on():
    try:
        return bool(frappe.db.get_single_value(SETTING, "enable_shopify")) and \
            bool(frappe.db.get_single_value(SETTING, "update_erpnext_stock_levels_to_shopify"))
    except Exception:
        return False


def _location():
    """(id, name) the consignment shelves already point at; else the most
    used location."""
    r = frappe.db.sql(
        """SELECT shopify_location_id, shopify_location_name
           FROM `tabShopify Warehouse Mapping`
           WHERE parent = %s AND parentfield = %s AND IFNULL(shopify_location_id, '') != ''
           GROUP BY shopify_location_id, shopify_location_name
           ORDER BY SUM(erpnext_warehouse LIKE 'CN -%%') DESC, COUNT(*) DESC LIMIT 1""",
        (SETTING, TABLE))
    return r[0] if r else None


def map_consignment_shelves():
    """Mapping rows for the consignment shelves that have none. Rows go in
    directly: saving Shopify Setting would run its validate, which talks to
    Shopify about webhooks. Returns the shelves it mapped."""
    missing = frappe.db.sql_list(
        """SELECT w.name FROM `tabWarehouse` w
           WHERE w.parent_warehouse = %s AND w.is_group = 0 AND w.disabled = 0
             AND w.name NOT IN (SELECT erpnext_warehouse FROM `tabShopify Warehouse Mapping`
                                WHERE parent = %s AND parentfield = %s)""",
        (CN_PARENT, SETTING, TABLE))
    if not missing:
        return []
    loc = _location()
    if not loc:
        return []
    idx = frappe.db.sql(
        "SELECT IFNULL(MAX(idx), 0) FROM `tabShopify Warehouse Mapping` WHERE parent = %s AND parentfield = %s",
        (SETTING, TABLE))[0][0]
    for w in missing:
        idx += 1
        row = frappe.get_doc({
            "doctype": "Shopify Warehouse Mapping", "parent": SETTING, "parenttype": SETTING,
            "parentfield": TABLE, "idx": idx, "erpnext_warehouse": w,
            "shopify_location_id": loc[0], "shopify_location_name": loc[1],
        })
        row.db_insert()
    # The fork reads the setting through get_cached_doc: drop only that doc,
    # never the whole site cache (see kv.set_default).
    frappe.clear_document_cache(SETTING, SETTING)
    frappe.get_doc({
        "doctype": "Comment", "comment_type": "Info", "reference_doctype": SETTING,
        "reference_name": SETTING,
        "content": "Stock guard mapped consignment shelves to Shopify: " + ", ".join(missing),
    }).insert(ignore_permissions=True)
    return missing


def stale_items(limit=BATCH):
    """Items with stock on a mapped shelf whose last push predates that
    shelf's mapping row."""
    return frappe.db.sql_list(
        """SELECT DISTINCT ei.erpnext_item_code
           FROM `tabShopify Warehouse Mapping` m
           JOIN `tabBin` b ON b.warehouse = m.erpnext_warehouse AND b.actual_qty <> 0
           JOIN `tabEcommerce Item` ei ON ei.erpnext_item_code = b.item_code AND ei.integration = 'shopify'
           WHERE m.parent = %s AND m.parentfield = %s
             AND (ei.inventory_synced_on IS NULL OR ei.inventory_synced_on < m.creation)
           LIMIT %s""",
        (SETTING, TABLE, int(limit)))


def resync_stale(limit=BATCH):
    items = stale_items(limit)
    for ic in items:
        # Same queue and job id as the fork's own hook, so a stock move in
        # the same minute does not push twice.
        frappe.enqueue(SYNC_FN, queue="short", item_code=ic,
                       job_id="shopify_inv_sync_" + ic, deduplicate=True)
    return items


def run():
    """Hourly, and after a shelf or the mapping changes."""
    if not _on():
        return {"off": True}
    try:
        frappe.get_attr(SYNC_FN)
    except Exception:
        return {"noFork": True}
    mapped = map_consignment_shelves()
    if mapped:
        frappe.db.commit()
    pushed = resync_stale()
    frappe.db.commit()
    return {"mapped": mapped, "pushed": len(pushed)}


def on_warehouse_change(doc, method=None):
    """A consignment shelf appears or is moved under Consignment - JM."""
    if doc.parent_warehouse == CN_PARENT and not doc.is_group:
        frappe.enqueue("logistics_portal.api.shopify_stock_guard.run", queue="short",
                       job_id="lp_shopify_stock_guard", deduplicate=True, enqueue_after_commit=True)


def on_setting_update(doc, method=None):
    """Somebody saved the mapping by hand: push what it newly covers."""
    frappe.enqueue("logistics_portal.api.shopify_stock_guard.run", queue="short",
                   job_id="lp_shopify_stock_guard", deduplicate=True, enqueue_after_commit=True)
