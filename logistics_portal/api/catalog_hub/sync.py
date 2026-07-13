"""Catalog Hub — Phase 0: read-only Shopify product/variant status sync.

Pulls the live Shopify status of every in-stock or duplicate-SKU Item into ERPNext so ops can tell
which code is ACTIVE vs archived/draft/deleted — the authoritative signal (found
during investigation) that resolves stranded stock and false-OOS. It is
READ-ONLY against Shopify (reuses ecommerce_integrations' authenticated session)
and writes only two status fields on Item, via db.set_value so it never
re-triggers the Shopify item sync.

Fields written on Item:
  custom_shopify_status  ACTIVE | ARCHIVED | DRAFT | DELETED | UNMAPPED
  custom_variant_live    1 if the item's Shopify variant still exists, else 0
  custom_shopify_synced_on  timestamp of the last status check
"""

import json

import frappe

STATUS_FIELD = "custom_shopify_status"
VARIANT_LIVE_FIELD = "custom_variant_live"
SYNCED_ON_FIELD = "custom_shopify_synced_on"

# Bulk status: for each Product id, its status + the ids of its live variants.
# A deleted product comes back as null in `nodes`, which we map to DELETED.
# first:250 (Shopify's max single page) so a big style product's variant is not
# falsely read as gone; batch kept small to stay under the cost limit.
_NODES_QUERY = (
    "query($ids:[ID!]!){ nodes(ids:$ids){ ... on Product { "
    "id status variants(first:250){ nodes { id } } } } }"
)
_BATCH = 20

# Locally-held JM warehouses (same definition the board/pick engine use).
_JM = ("b.warehouse LIKE %s AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s "
       "AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s")
_JM_ARGS = ["% - JM", "Defective%", "Container%", "Air Freight%", "%Old%", "CORRECTING%"]


def _target_items(limit):
    """Mapped items worth reconciling: everything that HOLDS stock (so the
    stranded-stock report is complete, not just duplicates) plus every item under
    a variant-level duplicate SKU (2..8 codes, for the false-OOS/consolidate
    path). Deterministic order so a capped run resumes predictably. Returns
    [{item_code, product_id, variant_id}]."""
    rows = frappe.db.sql(
        f"""
        SELECT it.name AS item_code, ei.integration_item_code AS product_id,
               ei.variant_id AS variant_id
        FROM `tabItem` it
        JOIN `tabEcommerce Item` ei
          ON ei.erpnext_item_code = it.name AND ei.integration = 'shopify'
             AND COALESCE(ei.integration_item_code, '') != ''
        WHERE it.name IN (
            SELECT item_code FROM `tabBin` b WHERE {_JM}
            GROUP BY item_code HAVING SUM(b.actual_qty - b.reserved_qty) > 0
        )
        OR it.custom_sku IN (
            SELECT sku FROM (
                SELECT custom_sku AS sku FROM `tabItem`
                WHERE COALESCE(custom_sku, '') != ''
                GROUP BY custom_sku HAVING COUNT(*) BETWEEN 2 AND 8
            ) d
        )
        ORDER BY it.name
        LIMIT %s
        """,
        tuple(_JM_ARGS) + (int(limit),), as_dict=True)
    return rows


@frappe.whitelist()
def sync_status(limit=5000, dry_run=0):
    """Reconcile Shopify status for duplicate-SKU items. Manager only. Long runs
    should go through `enqueue_sync`. Returns a counts summary."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can run the catalog sync.", frappe.PermissionError)
    return _run_sync(int(limit), bool(int(dry_run)))


@frappe.whitelist()
def enqueue_sync(limit=20000):
    """Kick the sync off in the background (the full duplicate set can be large)."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can run the catalog sync.", frappe.PermissionError)
    frappe.enqueue("logistics_portal.api.catalog_hub.sync._run_sync", queue="long",
                   timeout=36000, job_name="catalog_shopify_status_sync",
                   limit=int(limit), dry_run=False)
    return {"queued": True}


def _run_sync(limit=20000, dry_run=False):
    items = _target_items(limit)
    if not items:
        return {"checked": 0, "updated": 0, "batches": 0}

    # One product can back several ERPNext items (variants) — dedupe the products
    # we ask Shopify for, then fan the answer back out to every item.
    by_product = {}
    for it in items:
        by_product.setdefault(str(it.product_id), []).append(it)
    product_ids = list(by_product.keys())

    now = frappe.utils.now()
    counts = {"checked": 0, "updated": 0, "batches": 0,
              "ACTIVE": 0, "ARCHIVED": 0, "DRAFT": 0, "DELETED": 0, "UNMAPPED": 0}

    for i in range(0, len(product_ids), _BATCH):
        chunk = product_ids[i:i + _BATCH]
        gids = [f"gid://shopify/Product/{p}" for p in chunk]
        try:
            data = _fetch_status(gids)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "catalog_hub.sync batch")
            continue
        counts["batches"] += 1
        nodes = ((data or {}).get("data") or {}).get("nodes") or []
        # Map product_id -> {status, variant_gids:set}. Missing/null node = DELETED.
        by_gid = {}
        for n in nodes:
            if not n:
                continue
            pid = str(n.get("id", "")).rsplit("/", 1)[-1]
            vg = {v.get("id") for v in (((n.get("variants") or {}).get("nodes")) or [])}
            by_gid[pid] = {"status": (n.get("status") or "").upper(), "variants": vg}

        for pid in chunk:
            info = by_gid.get(pid)
            for it in by_product[pid]:
                counts["checked"] += 1
                if info is None:
                    status, live = "DELETED", 0
                else:
                    status = info["status"] or "UNMAPPED"
                    vgid = f"gid://shopify/ProductVariant/{it.variant_id}"
                    live = 1 if vgid in info["variants"] else 0
                counts[status] = counts.get(status, 0) + 1
                if not dry_run:
                    frappe.db.set_value("Item", it.item_code, {
                        STATUS_FIELD: status,
                        VARIANT_LIVE_FIELD: live,
                        SYNCED_ON_FIELD: now,
                    }, update_modified=False)
                counts["updated"] += 0 if dry_run else 1
        if not dry_run:
            frappe.db.commit()

    frappe.cache().delete_value("lp_catalog_problems")
    return counts


def _fetch_status(product_gids):
    """POST the bulk status query to Shopify's Admin GraphQL endpoint using the
    ecommerce_integrations Shopify Setting credentials. A direct POST (not the
    shopify SDK's GraphQL helper — this SDK build doesn't ship one). Retries a
    couple of times on HTTP 429 or a GraphQL THROTTLED error (cost-based limit)."""
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
    body = {"query": _NODES_QUERY, "variables": {"ids": product_gids}}

    # A trustworthy answer has a `data` object and no top-level errors; only then
    # is a null node a genuine deletion. Anything else (real errors, missing
    # data, or persistent throttling) RAISES so the caller SKIPS the batch —
    # never mistaking a failed query for "all these products are deleted".
    for attempt in range(3):
        r = requests.post(url, json=body, headers=headers, timeout=30)
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
            raise Exception("Shopify GraphQL errors: " + json.dumps(errs)[:300])
        if data.get("data") is None:
            raise Exception("Shopify GraphQL response missing data")
        return data
    raise Exception("Shopify GraphQL throttled after retries")
