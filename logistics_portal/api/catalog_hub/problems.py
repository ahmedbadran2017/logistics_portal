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


# ── Selling air ───────────────────────────────────────────────────────────
#
# The exact mirror of stranded stock. That one is real inventory under a
# listing that cannot sell it; this one is a listing still selling inventory
# that is not there.
#
# Traced from WN-BG-094-blk on 2026-09-21. Of 65 live orders on items with no
# sellable Morocco stock, 57 were placed AFTER the last unit was gone —
# 11,273 MAD. Shopify 30, the landing page 24, manual 3.
#
# THREE THINGS IT IS NOT, each checked and ruled out before the fourth:
#   Not the oversell policy. Every variant checked reads inventoryPolicy DENY,
#     tracked true, availableForSale false. Shopify refuses correctly.
#   Not the warehouse map. All 327 warehouses mapped to the Shopify location
#     are sellable by our own definition — zero mismatch.
#   Not "the landing page has no stock check, as a rule". It has the LOWEST
#     rate of the three channels: 1.8% of its week against Shopify's 8.4%.
#
# What it is: Shopify was deciding on a stock number that was days old. Only
# 89 of 177,448 Ecommerce Items had been stock-synced in the last 24 hours;
# 9,714 were three days stale or worse. MN-SH-005-bej-43 ran dry at 19:30 and
# was not pushed for 21 hours — two orders landed in that window.
# JST0673-Rose-6y went nine days. And WN-BG-094-blk was pushed one minute
# after its last unit left, which is exactly why it has no Shopify orders at
# all and only landing-page ones.
#
# Each row therefore carries two clocks and NOT a verdict.
#
# The verdict was the first draft and it was wrong: it compared the LAST sync
# against the moment the stock ran out, and called the row a sync problem if
# the sync came first. But the sync has usually caught up by the time anyone
# reads the list, so on live data it labelled 63 of 65 orders "no gate" —
# confidently, and without evidence. Only the per-item sync HISTORY could
# answer what Shopify knew when each order was placed, and this table keeps
# one timestamp, not a history.
#
# So the row reports what is true and checkable: how long the item has been
# dry, and how old the number Shopify is holding right now is. A row that
# has been dry for twenty days whose number was last pushed five days ago is
# a sync problem whoever reads it can see for themselves. One selling on the
# landing page, which reads no number at all, is named by its channel.

_STALE_H = 24   # a stock figure older than a day is not a stock figure


@frappe.whitelist()
def selling_air(days=7, limit=60):
    """Items with nothing sellable in Morocco that are still taking orders.

    Excludes product bundles — the box holds no stock, its components do, and
    one bundle alone would have added 166 phantom orders to this list — and
    local-supplier items, whose stock lives at the supplier and whose zero is
    not a shortage."""
    _require_manager()
    days = min(max(int(days or 7), 1), 30)
    limit = min(max(int(limit or 60), 1), 200)
    from logistics_portal.api.warehouses import sellable_condition
    # The shared definition, not this module's older hand-rolled copy of it:
    # sellable counts SLOW ZONE, which is the working reserve, and excludes
    # disabled warehouses, which can hold nothing anyone may touch.
    cond, wargs = sellable_condition("b.warehouse")
    try:
        rows = frappe.db.sql(
            f"""SELECT soi.item_code AS code, it.custom_sku AS sku,
                       COALESCE(NULLIF(it.item_name,''), soi.item_code) AS name,
                       it.image,
                       COUNT(DISTINCT so.name) AS orders,
                       ROUND(SUM(soi.qty)) AS units,
                       ROUND(SUM(DISTINCT so.grand_total)) AS mad,
                       SUM(so.custom_sales_status = 'Confirmed') AS confirmed,
                       MAX(so.creation) AS last_order,
                       GROUP_CONCAT(DISTINCT COALESCE(NULLIF(so.custom_channel,''),'Shopify')) AS chans
                FROM `tabSales Order` so
                JOIN `tabSales Order Item` soi ON soi.parent = so.name
                JOIN `tabItem` it ON it.name = soi.item_code AND it.disabled = 0
                LEFT JOIN `tabSupplier` sup ON sup.name = it.default_supplier
                WHERE so.docstatus = 1 AND so.company = 'Justyol Morocco'
                  AND so.creation >= DATE_SUB(NOW(), INTERVAL %s DAY)
                  AND COALESCE(so.custom_logistics_status,'') IN ('', 'Pending')
                  AND COALESCE(sup.supplier_group,'') <> 'Morocco Local Suppliers'
                  AND soi.item_code NOT IN (SELECT new_item_code FROM `tabProduct Bundle`)
                  AND NOT EXISTS (SELECT 1 FROM `tabBin` b
                        WHERE b.item_code = soi.item_code AND b.actual_qty > 0 AND {cond})
                GROUP BY soi.item_code, sku, name, it.image
                ORDER BY orders DESC, mad DESC
                LIMIT %s""",
            tuple([days] + wargs + [limit]), as_dict=True)
        if not rows:
            return {"rows": [], "orders": 0, "mad": 0, "days": days, "capped": False}

        codes = [r.code for r in rows]
        ph = ", ".join(["%s"] * len(codes))
        # When the last unit actually left — the clock this whole list is
        # about. One grouped read, not one per row.
        dry = {r[0]: r[1] for r in frappe.db.sql(
            f"""SELECT item_code, MAX(creation) FROM `tabStock Ledger Entry`
                WHERE item_code IN ({ph}) AND is_cancelled = 0
                  AND warehouse LIKE '%% - JM' AND qty_after_transaction > 0
                GROUP BY item_code""", tuple(codes))}
        synced = {r[0]: r[1] for r in frappe.db.sql(
            f"""SELECT erpnext_item_code, MAX(inventory_synced_on)
                FROM `tabEcommerce Item` WHERE erpnext_item_code IN ({ph})
                GROUP BY erpnext_item_code""", tuple(codes))}

        now = frappe.utils.now_datetime()
        out, t_orders, t_mad = [], 0, 0
        for r in rows:
            zero_at = dry.get(r.code)
            push_at = synced.get(r.code)
            if push_at and push_at < frappe.utils.get_datetime("2000-01-01"):
                push_at = None
            age_h = (round((now - push_at).total_seconds() / 3600)
                     if push_at else None)
            t_orders += int(r.orders or 0)
            t_mad += int(r.mad or 0)
            out.append({
                "code": r.code, "sku": r.sku or "", "name": r.name,
                "image": r.image or "",
                "orders": int(r.orders or 0), "units": int(r.units or 0),
                "mad": int(r.mad or 0), "confirmed": int(r.confirmed or 0),
                "channels": sorted((r.chans or "").split(",")) if r.chans else [],
                "lastOrder": str(r.last_order or "")[:19],
                "dryDays": (now - zero_at).days if zero_at else None,
                # How old the number Shopify is holding is, right now.
                "syncAgeH": age_h,
                "neverSynced": push_at is None,
                "staleSync": age_h is not None and age_h >= _STALE_H,
            })
        # The totals sum the ROWS RETURNED, so on a capped list they are a
        # floor, not a total — at 30 days the list hits the limit and the
        # real figures are higher. Say so rather than let a headline read as
        # complete when it is the top of a longer list.
        return {"rows": out, "orders": t_orders, "mad": t_mad, "days": days,
                "capped": len(rows) >= limit}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "catalog_hub.selling_air")
        return {"rows": [], "orders": 0, "mad": 0, "days": days, "capped": False}


# The oldest of these is from 2024. Nobody knew because nothing ever said.
_LOST_METHODS = ("ecommerce_integrations.shopify.order.sync_sales_order",)
# A row younger than this may simply still be in the queue.
_LOST_GRACE_MIN = 15


@frappe.whitelist()
def lost_orders(days=90, limit=60):
    """Shopify orders that reached ERPNext and then vanished without a word.

    `create_sales_order` swallows its own failures: the save and the submit are
    each wrapped in a bare `except Exception: return`, and `create_order` writes
    its Success log only `if so:`. So when either step raises, nothing is
    logged, nothing is retried, and the Ecommerce Integration Log row stays at
    'Queued' for ever. The customer ordered, Shopify charged the intent, and no
    order exists.

    That is not a hypothesis. Replayed against the real payload of #261583 on
    2026-09-23: get_order_items returns the line correctly and the save
    succeeds, so the loss happens at or after the submit — inside the second
    bare except. The 'no items mapped' branch is NOT this class; it logs a real
    Error and shows up as one.

    The check is deliberately the crude one — does a Sales Order with that name
    exist — because that is the only question the floor cares about. Rows that
    a later re-sync rescued therefore drop off by themselves."""
    _require_manager()
    days = min(max(int(days or 90), 1), 3650)
    limit = min(max(int(limit or 60), 1), 200)
    try:
        rows = frappe.db.sql(
            """SELECT name, creation, status, request_data
               FROM `tabEcommerce Integration Log`
               WHERE status IN ('Queued', 'In Progress')
                 AND method IN %(m)s
                 AND creation <= DATE_SUB(NOW(), INTERVAL %(g)s MINUTE)
                 AND creation >= DATE_SUB(NOW(), INTERVAL %(d)s DAY)
               ORDER BY creation DESC
               LIMIT 400""",
            {"m": _LOST_METHODS, "g": _LOST_GRACE_MIN, "d": days}, as_dict=True)

        import json as _json
        now = frappe.utils.now_datetime()
        out, seen, mad, recovered = [], set(), 0.0, 0
        for r in rows:
            try:
                d = _json.loads(r.request_data or "{}")
            except Exception:
                continue
            order = d.get("name")
            if not order or order in seen:
                continue
            seen.add(order)
            if frappe.db.exists("Sales Order", order):
                recovered += 1
                continue
            total = float(d.get("total_price") or 0)
            mad += total
            cust = d.get("customer") or {}
            ship = d.get("shipping_address") or {}
            out.append({
                "log": r.name,
                "order": order,
                "shopifyId": str(d.get("id") or ""),
                "at": str(r.creation)[:16],
                "ageH": round((now - r.creation).total_seconds() / 3600.0, 1),
                "mad": round(total, 2),
                "customer": (cust.get("first_name") or ship.get("first_name") or "")
                            + " " + (cust.get("last_name") or ship.get("last_name") or ""),
                "phone": (ship.get("phone") or cust.get("phone") or ""),
                "city": (ship.get("city") or ""),
                "source": d.get("source_name") or "",
                "financial": d.get("financial_status") or "",
                "skus": [str(li.get("sku") or "") for li in (d.get("line_items") or [])][:6],
                "lines": len(d.get("line_items") or []),
            })
            if len(out) >= limit:
                break
        return {"rows": out, "lost": len(out), "mad": round(mad, 2),
                "recovered": recovered, "scanned": len(rows), "days": days,
                "capped": len(out) >= limit}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "catalog_hub.lost_orders")
        return {"rows": [], "lost": 0, "mad": 0, "recovered": 0,
                "scanned": 0, "days": days, "capped": False}
