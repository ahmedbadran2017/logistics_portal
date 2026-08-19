"""Catalog Hub — Shopify product/variant status mirror (Shopify -> ERPNext).

Mirrors each mapped Item's live Shopify status into ERPNext so ops can tell which
code is ACTIVE vs archived/draft/deleted — the authoritative signal (found during
investigation) that resolves stranded stock and false-OOS. READ-ONLY against
Shopify (reuses ecommerce_integrations' authenticated session); writes only the
status fields below, via db.set_value so it never re-triggers the Shopify item
sync (no echo loop).

Three paths, one writer:
  * bulk_reconcile  — the scheduled Phase A path: one Bulk Operations export of
                      the WHOLE catalog, diffed against Next, writing only drift.
  * webhook         — real-time single-product updates (catalog_hub/webhook.py),
                      via write_product_status below. Currently optional/dormant.
  * sync_status / _run_sync — the targeted nodes-based sync, kept for manual runs.

Direction is one-way: catalog/status flows IN. Stock is the opposite direction
(Next is the source of physical truth) — that is Phase B, and nothing here writes
stock.

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


def write_product_status(product_id, status, live_variant_ids, now=None):
    """Write ACTIVE/ARCHIVED/DRAFT/DELETED + variant_live onto every ERPNext item
    mapped to one Shopify product. Shared by the real-time webhook and any manual
    replay. `live_variant_ids` = set of bare Shopify variant ids that still exist
    on the product (None => the product is gone, so every variant is dead). Uses
    db.set_value(update_modified=False) so it never re-triggers the ecommerce_
    integrations item sync (no echo loop). Returns the number of items written."""
    product_id = str(product_id)
    status = (status or "").upper()
    live_ids = {str(v) for v in (live_variant_ids or set())}
    items = frappe.db.sql(
        """SELECT it.name AS item_code, ei.variant_id
           FROM `tabItem` it
           JOIN `tabEcommerce Item` ei
             ON ei.erpnext_item_code = it.name AND ei.integration = 'shopify'
           WHERE ei.integration_item_code = %s""", product_id, as_dict=True)
    if not items:
        return 0
    now = now or frappe.utils.now()
    n = 0
    for it in items:
        live = 0 if status == "DELETED" else (1 if str(it.variant_id) in live_ids else 0)
        frappe.db.set_value("Item", it.item_code, {
            STATUS_FIELD: status,
            VARIANT_LIVE_FIELD: live,
            SYNCED_ON_FIELD: now,
        }, update_modified=False)
        n += 1
    frappe.db.commit()
    frappe.cache().delete_value("lp_catalog_problems")
    return n


def reconcile_sweep(limit=8000):
    """Scheduled safety net for the real-time webhook. Webhook deliveries can be
    dropped or arrive out of order; this re-pulls the live Shopify status for the
    target set and rewrites any that drifted. The webhook keeps Next current
    minute-to-minute; this guarantees it can never silently fall behind.

    Bounded so one run stays cheap; the ORDER BY in _target_items makes a capped
    run deterministic. Runs unattended from the scheduler — never throws."""
    try:
        res = _run_sync(int(limit), dry_run=False)
        frappe.cache().set_value("lp_catalog_last_sweep", frappe.utils.now())
        return res
    except Exception:
        frappe.log_error(frappe.get_traceback(), "catalog_hub.reconcile_sweep")
        return {"error": True}


def _shopify_endpoint():
    """(url, headers) for the Shopify Admin GraphQL endpoint, built from the
    ecommerce_integrations Shopify Setting credentials. Shared by the status
    reconcile and by the webhook registration helper."""
    from ecommerce_integrations.shopify.constants import API_VERSION, SETTING_DOCTYPE

    setting = frappe.get_doc(SETTING_DOCTYPE)
    shop = (setting.shopify_url or "").replace("https://", "").replace("http://", "").strip("/")
    token = setting.get_password("password")
    if not shop or not token:
        frappe.throw("Shopify Setting is missing a URL or access token.")
    url = f"https://{shop}/admin/api/{API_VERSION}/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    return url, headers


def shopify_graphql(query, variables=None, retries=3):
    """POST a GraphQL operation to Shopify's Admin API. A trustworthy answer has
    a `data` object and no top-level errors; anything else (real errors, missing
    data, or persistent throttling) RAISES so the caller can SKIP rather than act
    on a bad reply — never mistaking a failed query for a real result. Retries a
    couple of times on HTTP 429 or a GraphQL THROTTLED (cost-based) error."""
    import time

    import requests

    url, headers = _shopify_endpoint()
    body = {"query": query, "variables": variables or {}}
    for attempt in range(retries):
        r = requests.post(url, json=body, headers=headers, timeout=30)
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        data = r.json() or {}
        errs = data.get("errors") or []
        if errs:
            throttled = False
            for e in errs:
                if (e.get("extensions") or {}).get("code") == "THROTTLED":
                    throttled = True
                    break
            if throttled:
                time.sleep(2 * (attempt + 1))
                continue
            raise Exception("Shopify GraphQL errors: " + json.dumps(errs)[:300])
        if data.get("data") is None:
            raise Exception("Shopify GraphQL response missing data")
        return data
    raise Exception("Shopify GraphQL throttled after retries")


def _fetch_status(product_gids):
    """The nodes-based product-status query (status + live variant ids per
    product). Kept for the manual/targeted sync and as a fallback; the scheduled
    path is bulk_reconcile below."""
    return shopify_graphql(_NODES_QUERY, {"ids": product_gids})


# ---------------------------------------------------------------------------
# Whole-catalog reconcile via Shopify Bulk Operations (the scheduled path).
#
# One async bulk query exports EVERY product's status + variant ids as a JSONL
# file; we diff it against what Next stores and write only the rows that changed.
# Whole-catalog, not just stocked items, on purpose:
#   * a zero-stock ACTIVE product is exactly the oversell tap we must see, and a
#     stocked-only sweep structurally never would;
#   * DELETED can only be detected by ABSENCE from the full export.
# Bulk keeps it cheap at catalog scale (Shopify Plus raises the budget further),
# and diff-only writes keep the DB churn tiny even across 150k variants.
# ---------------------------------------------------------------------------

_BULK_PRODUCTS_QUERY = (
    "{ products { edges { node { id status "
    "variants { edges { node { id } } } } } } }"
)


def _run_bulk_products_query(poll_secs=5, max_polls=120):
    """Start the products bulk export, wait for it, and return the JSONL result
    URL (None if the export held zero objects). Returns the string 'BUSY' if the
    shop already has a bulk query running (we simply skip this tick and let the
    next one try). Raises on a real failure."""
    import time

    # Don't collide with an in-flight bulk op (only one QUERY runs per shop).
    cur = shopify_graphql(
        "{ currentBulkOperation(type: QUERY) { id status } }")
    node = ((cur.get("data") or {}).get("currentBulkOperation") or {})
    if node.get("status") in ("CREATED", "RUNNING"):
        return "BUSY"

    started = shopify_graphql(
        "mutation($q: String!) { bulkOperationRunQuery(query: $q) { "
        "bulkOperation { id status } userErrors { field message } } }",
        {"q": _BULK_PRODUCTS_QUERY})
    run = ((started.get("data") or {}).get("bulkOperationRunQuery") or {})
    errs = run.get("userErrors") or []
    if errs:
        raise Exception("bulkOperationRunQuery: " + json.dumps(errs)[:300])

    for _ in range(max_polls):
        time.sleep(poll_secs)
        cur = shopify_graphql(
            "{ currentBulkOperation(type: QUERY) { status errorCode url objectCount } }")
        node = ((cur.get("data") or {}).get("currentBulkOperation") or {})
        st = node.get("status")
        if st == "COMPLETED":
            return node.get("url")  # None when objectCount == 0
        if st in ("FAILED", "CANCELED", "EXPIRED"):
            raise Exception(f"bulk op {st}: {node.get('errorCode')}")
    raise Exception("bulk op did not complete in time")


def _parse_bulk_jsonl(url):
    """Stream the JSONL export into {product_id: {status, variants:set}}.

    Bulk flattens nested connections: each product is one line, each variant a
    separate line carrying `__parentId`. A variant line can arrive before its
    product line, so we setdefault on both."""
    import requests

    products = {}
    r = requests.get(url, timeout=120, stream=True)
    r.raise_for_status()
    for raw in r.iter_lines():
        if not raw:
            continue
        obj = json.loads(raw)
        gid = obj.get("id", "")
        if "/Product/" in gid:
            pid = gid.rsplit("/", 1)[-1]
            p = products.setdefault(pid, {"status": "", "variants": set()})
            p["status"] = (obj.get("status") or "").upper()
        elif "/ProductVariant/" in gid:
            pid = (obj.get("__parentId") or "").rsplit("/", 1)[-1]
            if not pid:
                continue
            products.setdefault(pid, {"status": "", "variants": set()})
            products[pid]["variants"].add(gid.rsplit("/", 1)[-1])
    return products


def bulk_reconcile():
    """Whole-catalog status reconcile via Bulk Operations. Diffs the live Shopify
    export against every mapped Item and writes only what changed. This is the
    scheduled Phase A path — called by the scheduler as Administrator, so it is
    intentionally NOT whitelisted and NOT role-gated (see trigger_reconcile for
    the manager-gated manual entry). Safe to run unattended; never throws."""
    try:
        url = _run_bulk_products_query()
        if url == "BUSY":
            return {"skipped": "bulk op already running"}

        # A COMPLETED export with no URL means zero products — refuse to act on
        # that (it would flip the entire catalog to DELETED). Treat as a no-op.
        products = _parse_bulk_jsonl(url) if url else {}
        if not products:
            frappe.log_error("bulk export returned no products", "catalog_hub.bulk_reconcile")
            return {"checked": 0, "changed": 0, "note": "empty export ignored"}

        mapped = frappe.db.sql(
            """SELECT it.name AS item_code, ei.integration_item_code AS pid,
                      ei.variant_id, it.custom_shopify_status AS st,
                      it.custom_variant_live AS vl
               FROM `tabItem` it
               JOIN `tabEcommerce Item` ei
                 ON ei.erpnext_item_code = it.name AND ei.integration = 'shopify'
               WHERE COALESCE(ei.integration_item_code, '') != ''""", as_dict=True)

        now = frappe.utils.now()
        checked = changed = deleted = 0
        counts = {}
        for row in mapped:
            checked += 1
            info = products.get(str(row.pid))
            if not info or not info["status"]:
                want_status, want_live = "DELETED", 0
                deleted += 1
            else:
                want_status = info["status"]
                # Only trust variant_live when the product actually exported
                # variants (guards against a partial line set flipping it to 0).
                if info["variants"]:
                    want_live = 1 if str(row.variant_id) in info["variants"] else 0
                else:
                    want_live = int(row.vl or 0)
            counts[want_status] = counts.get(want_status, 0) + 1
            if want_status != (row.st or "") or want_live != int(row.vl or 0):
                frappe.db.set_value("Item", row.item_code, {
                    STATUS_FIELD: want_status,
                    VARIANT_LIVE_FIELD: want_live,
                    SYNCED_ON_FIELD: now,
                }, update_modified=False)
                changed += 1
                if changed % 500 == 0:
                    frappe.db.commit()

        frappe.db.commit()
        frappe.cache().delete_value("lp_catalog_problems")
        frappe.cache().set_value("lp_catalog_last_sweep", now)
        return {"checked": checked, "changed": changed, "deleted": deleted,
                "products": len(products), "byStatus": counts}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "catalog_hub.bulk_reconcile")
        return {"error": True}


@frappe.whitelist()
def trigger_reconcile():
    """Manager-only manual 'Run now' for the whole-catalog reconcile. Runs in the
    background (the bulk export can take a minute) so the request returns at once."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can run the catalog reconcile.", frappe.PermissionError)
    frappe.enqueue("logistics_portal.api.catalog_hub.sync.bulk_reconcile",
                   queue="long", timeout=1800, job_name="catalog_bulk_reconcile")
    return {"queued": True}
