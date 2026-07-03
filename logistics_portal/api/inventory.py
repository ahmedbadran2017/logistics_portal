"""Live stock levels from ERPNext Bins (real, rich data) in the SPA shapes."""

import frappe

LOW_THRESHOLD = 10  # units at/below which a SKU is "low" (until Item reorder levels are wired)


@frappe.whitelist()
def stock(limit=60, warehouse_like="%JM%"):
    """Stock-by-SKU in the SPA's STOCK_ITEMS shape, from `tabBin`."""
    try:
        rows = frappe.db.sql(
            """
            SELECT b.item_code, i.item_name, b.warehouse,
                   b.actual_qty, b.reserved_qty, b.projected_qty, b.valuation_rate
            FROM `tabBin` b
            LEFT JOIN `tabItem` i ON i.name = b.item_code
            WHERE b.warehouse LIKE %s AND b.actual_qty IS NOT NULL
            ORDER BY b.actual_qty DESC
            LIMIT %s
            """,
            (warehouse_like, int(limit)),
            as_dict=True,
        )
        out = []
        for r in rows:
            on_hand = r.actual_qty or 0
            reserved = r.reserved_qty or 0
            state = "out" if on_hand <= 0 else ("low" if on_hand <= LOW_THRESHOLD else "ok")
            out.append({
                "sku": r.item_code,
                "name": r.item_name or r.item_code,
                "zone": r.warehouse,
                "bin": r.warehouse,
                "onHand": int(on_hand),
                "reserved": int(reserved),
                "available": int((r.projected_qty if r.projected_qty is not None else on_hand - reserved)),
                "reorder": 0,
                "value": round((on_hand or 0) * (r.valuation_rate or 0)),
                "state": state,
            })
        return out
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.inventory.stock")
        return []


@frappe.whitelist()
def zones(warehouse_like="%JM%"):
    """Per-zone stock health (RESTOCK shape) for the Warehouse floor map."""
    try:
        rows = frappe.db.sql(
            """
            SELECT b.warehouse AS zone, COUNT(DISTINCT b.item_code) AS skus,
                   SUM(CASE WHEN b.actual_qty > 0 AND b.actual_qty <= %s THEN 1 ELSE 0 END) AS low,
                   SUM(CASE WHEN b.actual_qty <= 0 THEN 1 ELSE 0 END) AS oos
            FROM `tabBin` b
            WHERE b.warehouse LIKE %s
            GROUP BY b.warehouse ORDER BY skus DESC
            """,
            (LOW_THRESHOLD, warehouse_like), as_dict=True,
        )
        out = []
        for r in rows:
            skus = int(r.skus or 0)
            oos = int(r.oos or 0)
            out.append({
                "zone": r.zone, "bins": [], "skus": skus,
                "low": int(r.low or 0), "out": oos, "blocking": oos,
                "fill": round(1 - (oos / skus), 2) if skus else 1,
            })
        return out
    except Exception:
        return []


@frappe.whitelist()
def stats(warehouse_like="%JM%"):
    """Headline stock KPIs (STOCK_STATS shape)."""
    try:
        row = frappe.db.sql(
            """
            SELECT COUNT(DISTINCT b.item_code) AS sku_count,
                   ROUND(SUM(b.actual_qty)) AS total_units,
                   ROUND(SUM(b.actual_qty * b.valuation_rate)) AS total_value,
                   SUM(CASE WHEN b.actual_qty > 0 AND b.actual_qty <= %s THEN 1 ELSE 0 END) AS low_sku,
                   SUM(CASE WHEN b.actual_qty <= 0 THEN 1 ELSE 0 END) AS out_sku,
                   ROUND(SUM(b.reserved_qty)) AS reserved
            FROM `tabBin` b
            WHERE b.warehouse LIKE %s
            """,
            (LOW_THRESHOLD, warehouse_like),
            as_dict=True,
        )
        s = row[0] if row else {}
        return {
            "skuCount": int(s.get("sku_count") or 0),
            "totalUnits": int(s.get("total_units") or 0),
            "totalValue": int(s.get("total_value") or 0),
            "lowSku": int(s.get("low_sku") or 0),
            "outSku": int(s.get("out_sku") or 0),
            "deadSku": 0,
            "reserved": int(s.get("reserved") or 0),
            "turnover": 0,
        }
    except Exception:
        return {}
