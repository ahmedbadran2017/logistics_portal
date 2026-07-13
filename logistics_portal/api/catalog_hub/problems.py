"""Catalog Hub — Phase 0 problem dashboard.

Reads the Shopify status mirrored by catalog_hub.sync to surface the money-losing
situations the investigation found:
  - STRANDED STOCK: real inventory sitting under item codes whose Shopify listing
    is archived / draft / deleted, or whose variant no longer exists — stock that
    cannot sell as-is (e.g. J.SHORTS, 57 units under an ARCHIVED product).
Everything here is read-only; it only reports what the sync recorded.
"""

import json

import frappe

# Pickable JM warehouses (same definition the board/pick engine use).
_JM = ("b.warehouse LIKE %s AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s "
       "AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s")
_JM_ARGS = ["% - JM", "Defective%", "Container%", "Air Freight%", "%Old%", "CORRECTING%"]

# A listing that cannot sell the stock as-is.
_DEAD = "(it.custom_shopify_status IN ('ARCHIVED','DRAFT','DELETED') OR it.custom_variant_live = 0)"


@frappe.whitelist()
def overview():
    """Top-line Catalog Hub state: whether the sync has run, the status spread of
    the duplicate-SKU items, and the total stranded stock value. Manager only,
    cached 300s."""
    _require_manager()
    cache = frappe.cache()
    cached = cache.get_value("lp_catalog_problems")
    if cached:
        return json.loads(cached)
    try:
        synced = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabItem` WHERE custom_shopify_synced_on IS NOT NULL")[0][0]
        last = frappe.db.sql(
            "SELECT MAX(custom_shopify_synced_on) FROM `tabItem`")[0][0]
        by_status = {}
        for r in frappe.db.sql(
            """SELECT COALESCE(NULLIF(custom_shopify_status,''),'UNSYNCED') s, COUNT(*) n
               FROM `tabItem` WHERE custom_shopify_synced_on IS NOT NULL
               GROUP BY s""", as_dict=True):
            by_status[r.s] = int(r.n or 0)

        strand = frappe.db.sql(
            f"""SELECT COUNT(*) c, ROUND(SUM(v)) val, COUNT(DISTINCT sku) skus FROM (
                    SELECT it.name,
                        it.custom_sku sku,
                        SUM((b.actual_qty-b.reserved_qty)*b.valuation_rate) v,
                        SUM(b.actual_qty-b.reserved_qty) q
                    FROM `tabItem` it JOIN `tabBin` b ON b.item_code=it.name AND {_JM}
                    WHERE it.custom_shopify_synced_on IS NOT NULL AND {_DEAD}
                    GROUP BY it.name HAVING q > 0
                ) x""", tuple(_JM_ARGS), as_dict=True)[0]

        out = {
            "synced": int(synced or 0),
            "lastSync": str(last)[:16] if last else "",
            "byStatus": by_status,
            "strandedValue": int(strand.val or 0),
            "strandedCount": int(strand.c or 0),
            "strandedSkus": int(strand.skus or 0),
        }
        cache.set_value("lp_catalog_problems", json.dumps(out), expires_in_sec=300)
        return out
    except Exception:
        frappe.log_error(frappe.get_traceback(), "catalog_hub.overview")
        return {"synced": 0, "lastSync": "", "byStatus": {},
                "strandedValue": 0, "strandedCount": 0, "strandedSkus": 0}


@frappe.whitelist()
def stranded_stock(limit=100):
    """Items holding real stock under a dead Shopify listing, worst value first.
    Manager only."""
    _require_manager()
    try:
        rows = frappe.db.sql(
            f"""SELECT it.name AS code, it.custom_sku AS sku,
                    COALESCE(NULLIF(it.item_name,''), it.name) AS name,
                    it.custom_shopify_status AS status, it.custom_variant_live AS vlive,
                    ROUND(SUM(b.actual_qty-b.reserved_qty)) AS units,
                    ROUND(SUM((b.actual_qty-b.reserved_qty)*b.valuation_rate)) AS value
                FROM `tabItem` it JOIN `tabBin` b ON b.item_code=it.name AND {_JM}
                WHERE it.custom_shopify_synced_on IS NOT NULL AND {_DEAD}
                GROUP BY it.name HAVING units > 0
                ORDER BY value DESC LIMIT %s""",
            tuple(_JM_ARGS) + (min(int(limit), 500),), as_dict=True)
        return [{"code": r.code, "sku": r.sku or "", "name": r.name,
                 "status": r.status or "", "variantLive": int(r.vlive or 0),
                 "units": int(r.units or 0), "value": int(r.value or 0)} for r in rows]
    except Exception:
        frappe.log_error(frappe.get_traceback(), "catalog_hub.stranded_stock")
        return []


def _require_manager():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can open the Catalog Hub.", frappe.PermissionError)
