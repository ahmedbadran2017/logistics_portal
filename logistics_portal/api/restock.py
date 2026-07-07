"""Zone Restock Intelligence — read endpoints.

Server-side port of the `zone-restock-intelligence` Web Page. Computes which
items should move from the SOURCE zones into the active DEST zones, based on
recent sales velocity and a safety-stock target, and flags dead stock.

Phase 1 is read-only. The write path (creating Material Transfer Stock Entries)
lands in a later phase via `create_transfer_entries` guarded by
require_portal_admin().
"""
import frappe
from frappe.utils import add_days, nowdate

from logistics_portal.api.permissions import require_portal_user
from logistics_portal.api.utils import (
    JUSTYOL_COMPANY, clamp_int, item_has_field, sql_in_list,
)
from logistics_portal.api import zones as zonemod

# Don't let a single call iterate an unbounded catalogue.
MAX_SOURCE_ITEMS = 5000
MAX_RESULT_ROWS = 3000


@frappe.whitelist()
def get_restock_suggestions(days=7, safety_days=7):
    """Return restock suggestions + dead-stock list for the source→dest flow.

    Args:
        days: sales look-back window (1..90, default 7).
        safety_days: days of cover to target in the dest zone (0..60, default 7).
    """
    require_portal_user()
    days = clamp_int(days, 1, 90, 7)
    safety_days = clamp_int(safety_days, 0, 60, 7)

    source_zones, dest_defs = zonemod.get_zone_topology()
    if not source_zones or not dest_defs:
        return _empty_payload(days, safety_days)

    # 1) Source stock: item × source warehouse with qty on hand.
    source_rows = frappe.db.sql(
        """
        SELECT item_code, warehouse, actual_qty
        FROM `tabBin`
        WHERE warehouse IN ({src}) AND actual_qty > 0
        """.format(src=sql_in_list(source_zones)),
        as_dict=True,
    )
    if not source_rows:
        return _empty_payload(days, safety_days)

    source_stock = {}
    for r in source_rows:
        source_stock.setdefault(r.item_code, {})[r.warehouse] = r.actual_qty
    source_codes = list(source_stock.keys())[:MAX_SOURCE_ITEMS]
    truncated_items = len(source_stock) > MAX_SOURCE_ITEMS

    # 2) Dest stock per zone (sum over each zone's subtree via lft/rgt range).
    lo = min(z["lft"] for z in dest_defs)
    hi = max(z["rgt"] for z in dest_defs)
    dest_rows = frappe.db.sql(
        """
        SELECT b.item_code AS item_code, b.actual_qty AS actual_qty, w.lft AS lft
        FROM `tabBin` b
        INNER JOIN `tabWarehouse` w ON w.name = b.warehouse
        WHERE b.actual_qty <> 0 AND w.lft BETWEEN %(lo)s AND %(hi)s
          AND b.item_code IN ({codes})
        """.format(codes=sql_in_list(source_codes)),
        {"lo": lo, "hi": hi},
        as_dict=True,
    )
    dest_stock = {}  # item -> {zone_name -> qty}
    for r in dest_rows:
        zone = zonemod.zone_for_lft(r.lft, dest_defs)
        if not zone:
            continue
        dest_stock.setdefault(r.item_code, {})[zone] = dest_stock.setdefault(r.item_code, {}).get(zone, 0) + r.actual_qty

    # 3) Sales velocity over the window, with per-warehouse split for zone detection.
    date_from = add_days(nowdate(), -days)
    sales_rows = frappe.db.sql(
        """
        SELECT soi.item_code AS item_code, w.lft AS lft, SUM(soi.qty) AS qty
        FROM `tabSales Order Item` soi
        INNER JOIN `tabSales Order` so ON so.name = soi.parent
        LEFT JOIN `tabWarehouse` w ON w.name = soi.warehouse
        WHERE so.company = %(company)s AND so.docstatus = 1
          AND so.custom_sales_status IN ('Confirmed', 'Shipped')
          AND so.transaction_date >= %(date_from)s
          AND soi.item_code IN ({codes})
        GROUP BY soi.item_code, w.lft
        """.format(codes=sql_in_list(source_codes)),
        {"company": JUSTYOL_COMPANY, "date_from": date_from},
        as_dict=True,
    )
    total_sales = {}            # item -> qty
    zone_sales = {}             # item -> {zone_name -> qty}
    for r in sales_rows:
        total_sales[r.item_code] = total_sales.get(r.item_code, 0) + (r.qty or 0)
        zone = zonemod.zone_for_lft(r.lft, dest_defs)
        if zone:
            zone_sales.setdefault(r.item_code, {})[zone] = zone_sales.setdefault(r.item_code, {}).get(zone, 0) + (r.qty or 0)

    # 4) Item master info for labelling + group-based fallback classification.
    has_sku = item_has_field("custom_sku")
    sku_col = "custom_sku" if has_sku else "NULL AS custom_sku"
    item_rows = frappe.db.sql(
        """
        SELECT name, item_name, item_group, {sku}
        FROM `tabItem`
        WHERE name IN ({codes})
        """.format(sku=sku_col, codes=sql_in_list(source_codes)),
        as_dict=True,
    )
    items = {r.name: r for r in item_rows}

    dest_label = {z["name"]: z for z in dest_defs}
    restock, dead = [], []

    for item_code in source_codes:
        info = items.get(item_code) or {}
        daily = (total_sales.get(item_code, 0) or 0) / days
        zone = _detect_zone(item_code, zone_sales, info, dest_defs)
        zmeta = dest_label.get(zone, {"key": "fast", "label": zone})
        dest_qty = (dest_stock.get(item_code) or {}).get(zone, 0)

        for src_wh, src_qty in source_stock[item_code].items():
            if src_qty <= 0:
                continue
            base = {
                "item_code": item_code,
                "item_name": info.get("item_name") or item_code,
                "sku": info.get("custom_sku") or "",
                "item_group": info.get("item_group") or "",
                "source_warehouse": src_wh,
                "source_qty": src_qty,
                "dest_zone": zone,
                "dest_zone_key": zmeta.get("key"),
                "dest_zone_label": zmeta.get("label"),
                "dest_qty": dest_qty,
            }
            if daily == 0:
                dead.append({**base, "daily_sales": 0, "days_remaining": 999,
                             "suggested_qty": 0, "priority": "dead", "priority_score": 0})
                continue
            safety = daily * safety_days
            days_remaining = dest_qty / daily if daily > 0 else 999
            suggested = max(0, safety - dest_qty)
            suggested = min(suggested, src_qty)
            if days_remaining < 1:
                priority, score = "critical", 3
            elif days_remaining < 3:
                priority, score = "low", 2
            else:
                priority, score = "normal", 1
            if suggested > 0 or priority in ("critical", "low"):
                restock.append({**base, "daily_sales": round(daily, 3),
                                "days_remaining": round(days_remaining, 1),
                                "suggested_qty": round(suggested, 2),
                                "priority": priority, "priority_score": score})

    restock.sort(key=lambda x: (x["priority_score"], x["suggested_qty"]), reverse=True)
    dead.sort(key=lambda x: x["source_qty"], reverse=True)

    truncated_rows = len(restock) > MAX_RESULT_ROWS or len(dead) > MAX_RESULT_ROWS
    restock = restock[:MAX_RESULT_ROWS]
    dead = dead[:MAX_RESULT_ROWS]

    return {
        "days": days,
        "safety_days": safety_days,
        "summary": {
            "total": len(restock) + len(dead),
            "critical": sum(1 for r in restock if r["priority"] == "critical"),
            "low": sum(1 for r in restock if r["priority"] == "low"),
            "normal": sum(1 for r in restock if r["priority"] == "normal"),
            "dead": len(dead),
            "suggested_units": round(sum(r["suggested_qty"] for r in restock), 2),
        },
        "restock": restock,
        "dead": dead,
        "truncated": bool(truncated_items or truncated_rows),
    }


@frappe.whitelist()
def get_recent_transfers(limit=10):
    """Recent Material Transfer Stock Entries (last 7 days), for the activity panel."""
    require_portal_user()
    limit = clamp_int(limit, 1, 50, 10)
    rows = frappe.db.sql(
        """
        SELECT name, creation, docstatus, owner
        FROM `tabStock Entry`
        WHERE stock_entry_type = 'Material Transfer' AND company = %(company)s
          AND creation >= %(since)s
        ORDER BY creation DESC
        LIMIT %(limit)s
        """,
        {"company": JUSTYOL_COMPANY, "since": add_days(nowdate(), -7), "limit": limit},
        as_dict=True,
    )
    return rows


def _detect_zone(item_code, zone_sales, info, dest_defs):
    """Best dest zone: where it sold most historically, else by item_group."""
    sales = zone_sales.get(item_code)
    if sales:
        best = max(sales.items(), key=lambda kv: kv[1])
        if best[1] > 0:
            return best[0]
    return zonemod.detect_zone_by_group(info.get("item_group"))


def _empty_payload(days, safety_days):
    return {
        "days": days, "safety_days": safety_days,
        "summary": {"total": 0, "critical": 0, "low": 0, "normal": 0, "dead": 0, "suggested_units": 0},
        "restock": [], "dead": [], "truncated": False,
    }
