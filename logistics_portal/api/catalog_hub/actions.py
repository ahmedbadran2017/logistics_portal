"""Catalog Hub — Phase 1: human-confirmed fix actions.

Two fixes for the stranded-stock situations Phase 0 surfaces, both explicit
manager decisions (two-tap in the UI, never automatic):

  CONSOLIDATE  stock sits under a dead duplicate code while an ACTIVE sibling
               (same real SKU) sells — one Repack Stock Entry moves the qty
               onto the survivor code, bin by bin, at the same valuation, and
               disables the dead code so it can't be reused.
  REACTIVATE   stock sits under an ARCHIVED/DRAFT product whose variant still
               exists and no sibling sells it — flip the product back to
               ACTIVE on Shopify (productChangeStatus) and mirror the result.

Variant-deleted cases (the variant itself is gone) can't be fixed by either —
they need re-listing, which is Phase 2's onboarding gateway.
"""

import json

import frappe

from logistics_portal.api.catalog_hub.problems import _DEAD, _JM, _JM_ARGS, _require_manager
from logistics_portal.api.catalog_hub.sync import (
    STATUS_FIELD,
    SYNCED_ON_FIELD,
    VARIANT_LIVE_FIELD,
)

_CHANGE_STATUS = (
    "mutation($id: ID!, $status: ProductStatus!){"
    " productChangeStatus(productId: $id, status: $status){"
    " product { id status } userErrors { field message } } }"
)


@frappe.whitelist()
def fix_candidates(limit=100):
    """The two actionable queues + the count of what only Phase 2 can fix."""
    _require_manager()
    limit = min(max(int(limit or 100), 1), 300)

    # CONSOLIDATE: dead code holding stock + an ACTIVE, variant-live sibling
    # on the same real SKU. Survivor = newest ACTIVE sibling (the re-imported
    # product is the one the store actually sells).
    consolidations = frappe.db.sql(
        f"""SELECT it.name AS dead, it.custom_sku AS sku,
                   COALESCE(NULLIF(it.item_name,''), it.name) AS name,
                   it.custom_shopify_status AS status,
                   it.custom_variant_live AS vlive,
                   ROUND(SUM(b.actual_qty - b.reserved_qty)) AS units,
                   ROUND(SUM((b.actual_qty - b.reserved_qty) * b.valuation_rate)) AS value,
                   (SELECT s.name FROM `tabItem` s
                     WHERE s.custom_sku = it.custom_sku AND s.name != it.name
                       AND s.custom_shopify_status = 'ACTIVE' AND s.custom_variant_live = 1
                     ORDER BY s.creation DESC LIMIT 1) AS survivor
            FROM `tabItem` it
            JOIN `tabBin` b ON b.item_code = it.name AND {_JM}
            WHERE it.custom_shopify_synced_on IS NOT NULL AND {_DEAD}
              AND COALESCE(it.custom_sku, '') != '' AND it.disabled = 0
            GROUP BY it.name HAVING units > 0
            ORDER BY value DESC""",
        tuple(_JM_ARGS), as_dict=True)
    consolidations = [c for c in consolidations if c.survivor][:limit]

    # REACTIVATE: product merely ARCHIVED/DRAFT, variant intact, and nothing
    # else sells this SKU — flipping the product live un-strands the stock.
    reactivations = frappe.db.sql(
        f"""SELECT it.name AS code, it.custom_sku AS sku,
                   COALESCE(NULLIF(it.item_name,''), it.name) AS name,
                   it.custom_shopify_status AS status,
                   ei.integration_item_code AS product_id,
                   ROUND(SUM(b.actual_qty - b.reserved_qty)) AS units,
                   ROUND(SUM((b.actual_qty - b.reserved_qty) * b.valuation_rate)) AS value
            FROM `tabItem` it
            JOIN `tabBin` b ON b.item_code = it.name AND {_JM}
            JOIN `tabEcommerce Item` ei
              ON ei.erpnext_item_code = it.name AND ei.integration = 'shopify'
                 AND COALESCE(ei.integration_item_code, '') != ''
            WHERE it.custom_shopify_status IN ('ARCHIVED', 'DRAFT')
              AND it.custom_variant_live = 1 AND it.disabled = 0
              AND NOT EXISTS (SELECT 1 FROM `tabItem` s
                  WHERE s.custom_sku = it.custom_sku AND s.name != it.name
                    AND s.custom_shopify_status = 'ACTIVE' AND s.custom_variant_live = 1)
            GROUP BY it.name HAVING units > 0
            ORDER BY value DESC LIMIT %s""",
        tuple(_JM_ARGS) + (limit,), as_dict=True)

    # Only Phase 2 (re-listing) can fix these: the VARIANT itself is gone.
    unfixable = frappe.db.sql(
        f"""SELECT COUNT(*) FROM (
              SELECT it.name FROM `tabItem` it
              JOIN `tabBin` b ON b.item_code = it.name AND {_JM}
              WHERE it.custom_shopify_synced_on IS NOT NULL
                AND it.custom_variant_live = 0 AND it.disabled = 0
                AND NOT EXISTS (SELECT 1 FROM `tabItem` s
                    WHERE s.custom_sku = it.custom_sku AND s.name != it.name
                      AND s.custom_shopify_status = 'ACTIVE' AND s.custom_variant_live = 1)
              GROUP BY it.name HAVING SUM(b.actual_qty - b.reserved_qty) > 0
            ) x""", tuple(_JM_ARGS))[0][0]

    return {
        "consolidations": [{
            "dead": c.dead, "sku": c.sku or "", "name": c.name,
            "status": c.status or "", "variantLive": int(c.vlive or 0),
            "units": int(c.units or 0), "value": int(c.value or 0),
            "survivor": c.survivor,
        } for c in consolidations],
        "reactivations": [{
            "code": r.code, "sku": r.sku or "", "name": r.name,
            "status": r.status or "", "productId": str(r.product_id),
            "units": int(r.units or 0), "value": int(r.value or 0),
        } for r in reactivations],
        "unfixable": int(unfixable or 0),
    }


@frappe.whitelist()
def consolidate(dead_item, survivor_item):
    """Move ALL free stock from the dead duplicate code onto the ACTIVE
    survivor (same real SKU), bin by bin, in ONE submitted Repack Stock Entry
    at the source valuation — then disable the dead code. Manager only."""
    _require_manager()
    dead_item = (dead_item or "").strip()
    survivor_item = (survivor_item or "").strip()
    for code in (dead_item, survivor_item):
        if not frappe.db.exists("Item", code):
            frappe.throw(f"Unknown item: {code}")
    if dead_item == survivor_item:
        frappe.throw("Dead code and survivor are the same item.")
    d_sku, d_status, d_live = frappe.db.get_value(
        "Item", dead_item, ["custom_sku", STATUS_FIELD, VARIANT_LIVE_FIELD])
    s_sku, s_status, s_live = frappe.db.get_value(
        "Item", survivor_item, ["custom_sku", STATUS_FIELD, VARIANT_LIVE_FIELD])
    if not d_sku or d_sku != s_sku:
        frappe.throw("These two codes don't share the same real SKU — refusing to merge stock.")
    if s_status != "ACTIVE" or not int(s_live or 0):
        frappe.throw(f"{survivor_item} is not an ACTIVE live variant — not a valid survivor.")
    if d_status == "ACTIVE" and int(d_live or 0):
        frappe.throw(f"{dead_item} is itself ACTIVE and live — nothing to consolidate.")

    bins = frappe.db.sql(
        f"""SELECT b.warehouse, (b.actual_qty - b.reserved_qty) AS qty, b.valuation_rate
            FROM `tabBin` b
            WHERE b.item_code = %s AND (b.actual_qty - b.reserved_qty) > 0 AND {_JM}""",
        tuple([dead_item] + _JM_ARGS), as_dict=True)
    if not bins:
        frappe.throw("No free stock left under the dead code.")

    company = frappe.db.get_value("Warehouse", bins[0].warehouse, "company") \
        or frappe.defaults.get_global_default("company")
    rows = []
    total = 0
    for b in bins:
        qty = int(b.qty)
        total += qty
        rows.append({"item_code": dead_item, "qty": qty, "s_warehouse": b.warehouse})
        fg = {"item_code": survivor_item, "qty": qty, "t_warehouse": b.warehouse,
              "is_finished_item": 1, "basic_rate": float(b.valuation_rate or 0)}
        if not fg["basic_rate"]:
            fg["allow_zero_valuation_rate"] = 1
        rows.append(fg)

    se = frappe.get_doc({
        "doctype": "Stock Entry",
        "stock_entry_type": "Repack",
        "company": company,
        "remarks": f"Catalog Hub consolidation: {dead_item} → {survivor_item} "
                   f"(SKU {d_sku}) by {frappe.session.user}",
        "items": rows,
    })
    se.flags.ignore_permissions = True
    se.insert(ignore_permissions=True)
    se.submit()

    # The dead code must never be picked or re-imported into again.
    frappe.db.set_value("Item", dead_item, "disabled", 1, update_modified=False)
    for code, note in ((dead_item, f"Stock consolidated onto {survivor_item} via {se.name}; item disabled."),
                       (survivor_item, f"Received consolidated stock from {dead_item} via {se.name}.")):
        frappe.get_doc({
            "doctype": "Comment", "comment_type": "Comment",
            "reference_doctype": "Item", "reference_name": code,
            "content": note,
        }).insert(ignore_permissions=True)
    frappe.db.commit()
    _bust()
    return {"ok": True, "entry": se.name, "units": total, "bins": len(bins),
            "dead": dead_item, "survivor": survivor_item, "disabled": True}


@frappe.whitelist()
def reactivate(item_code):
    """Flip the item's Shopify PRODUCT back to ACTIVE (productChangeStatus) —
    a write to the live store, so it is a manager decision confirmed in the
    UI. Mirrors the new status onto every ERPNext item of that product."""
    _require_manager()
    item_code = (item_code or "").strip()
    if not frappe.db.exists("Item", item_code):
        frappe.throw("Unknown item.")
    status = frappe.db.get_value("Item", item_code, STATUS_FIELD)
    if status not in ("ARCHIVED", "DRAFT"):
        frappe.throw(f"{item_code} is {status or 'unsynced'} — only ARCHIVED/DRAFT "
                     "products can be re-activated.")
    product_id = frappe.db.get_value(
        "Ecommerce Item", {"erpnext_item_code": item_code, "integration": "shopify"},
        "integration_item_code")
    if not product_id:
        frappe.throw("No Shopify product mapping for this item.")

    data = _graphql(_CHANGE_STATUS,
                    {"id": f"gid://shopify/Product/{product_id}", "status": "ACTIVE"})
    payload = ((data.get("data") or {}).get("productChangeStatus") or {})
    errs = payload.get("userErrors") or []
    if errs:
        frappe.throw("Shopify refused: " + "; ".join(e.get("message", "") for e in errs)[:200])
    new_status = ((payload.get("product") or {}).get("status") or "").upper()
    if new_status != "ACTIVE":
        frappe.throw(f"Shopify returned status {new_status or 'unknown'} — not applied.")

    # Mirror onto every item of this product (variants share the fate).
    now = frappe.utils.now()
    siblings = [r[0] for r in frappe.db.sql(
        """SELECT erpnext_item_code FROM `tabEcommerce Item`
           WHERE integration = 'shopify' AND integration_item_code = %s""",
        (str(product_id),))]
    for code in siblings or [item_code]:
        frappe.db.set_value("Item", code, {STATUS_FIELD: "ACTIVE", SYNCED_ON_FIELD: now},
                            update_modified=False)
    frappe.get_doc({
        "doctype": "Comment", "comment_type": "Comment",
        "reference_doctype": "Item", "reference_name": item_code,
        "content": f"Shopify product {product_id} re-activated from the Catalog Hub "
                   f"by {frappe.session.user}.",
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    _bust()
    return {"ok": True, "productId": str(product_id), "status": "ACTIVE",
            "itemsUpdated": len(siblings) or 1}


def _graphql(query, variables):
    """POST to the Shopify Admin GraphQL endpoint with the
    ecommerce_integrations credentials (same transport as sync._fetch_status,
    without the nodes-specific handling)."""
    import time

    import requests
    from ecommerce_integrations.shopify.constants import API_VERSION, SETTING_DOCTYPE

    setting = frappe.get_doc(SETTING_DOCTYPE)
    shop = (setting.shopify_url or "").replace("https://", "").replace("http://", "").strip("/")
    token = setting.get_password("password")
    if not shop or not token:
        frappe.throw("Shopify Setting is missing a URL or access token.")
    url = f"https://{shop}/admin/api/{API_VERSION}/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    for attempt in range(3):
        r = requests.post(url, json={"query": query, "variables": variables},
                          headers=headers, timeout=30)
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        data = r.json() or {}
        errs = data.get("errors") or []
        if errs:
            throttled = any(
                ((e.get("extensions") or {}).get("code") == "THROTTLED") for e in errs)
            if throttled:
                time.sleep(2 * (attempt + 1))
                continue
            frappe.throw("Shopify GraphQL errors: " + json.dumps(errs)[:300])
        if data.get("data") is None:
            frappe.throw("Shopify GraphQL response missing data")
        return data
    frappe.throw("Shopify GraphQL throttled after retries")


def _bust():
    for k in ("lp_catalog_problems", "lp_pick_avail", "lp_board_summary",
              "lp_consolidation", "lp_sku_dupes"):
        frappe.cache().delete_value(k)
    frappe.cache().delete_keys("lp_suggest")
