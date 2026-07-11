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


# Valid pickable JM warehouses (exclude transit/defective/containers/old/correcting).
_SKU_WH_PATTERNS = ["% - JM", "Defective%", "Container%", "Air Freight%", "%Old%", "CORRECTING%"]


@frappe.whitelist()
def sku_duplicates(limit=60):
    """Merge-candidate report: **variant-level** SKUs (≤8 item codes, so the codes
    are the same sellable unit — not a style's size/colour spread) that are
    duplicated across item_codes with the stock SPLIT — real stock sitting on one
    code while a duplicate code shows empty, which is what makes an order falsely
    OOS. Style-level SKUs (many codes = different variants) are excluded. Cached
    600s. Returns [{sku, codes, codesInStock, stock, name}] by stock desc."""
    import json as _json
    cache = frappe.cache()
    cached = cache.get_value("lp_sku_dupes")
    if cached:
        return _json.loads(cached)[: min(int(limit), 200)]
    wp = _SKU_WH_PATTERNS
    jm = ("b.warehouse LIKE %s AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s "
          "AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s")
    try:
        rows = frappe.db.sql(
            f"""SELECT it.custom_sku AS sku,
                   COUNT(DISTINCT it.name) AS codes,
                   COUNT(DISTINCT CASE WHEN bs.net > 0 THEN it.name END) AS codes_in_stock,
                   ROUND(SUM(GREATEST(COALESCE(bs.net, 0), 0))) AS stock,
                   MAX(it.item_name) AS name
                FROM `tabItem` it
                LEFT JOIN (SELECT item_code, SUM(actual_qty - reserved_qty) net
                           FROM `tabBin` b WHERE {jm} GROUP BY item_code) bs
                  ON bs.item_code = it.name
                WHERE COALESCE(it.custom_sku, '') != ''
                GROUP BY it.custom_sku
                HAVING codes BETWEEN 2 AND 8 AND codes_in_stock >= 1
                   AND codes > codes_in_stock AND stock > 0
                ORDER BY stock DESC
                LIMIT 200""", tuple(wp), as_dict=True)
        out = [{"sku": r.sku, "codes": int(r.codes or 0),
                "codesInStock": int(r.codes_in_stock or 0),
                "stock": int(r.stock or 0), "name": r.name or ""} for r in rows]
        cache.set_value("lp_sku_dupes", _json.dumps(out), expires_in_sec=600)
        return out[: min(int(limit), 200)]
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.sku_duplicates")
        return []


@frappe.whitelist()
def sku_lookup(query, limit=80):
    """Answer 'is this SKU actually in the warehouse — maybe under a different
    item code?'. Many physical products are duplicated as several ERPNext Items
    (different item_code, one Shopify SKU in custom_sku); an order can show OOS
    on an empty code while a sibling code has stock.

    Accepts a custom_sku, an item_code, an order number, or a name fragment.
    Returns groups by custom_sku, each listing every sibling item_code with its
    NET available stock (actual − reserved across JM warehouses) and the bins
    holding it, flagging the one that was actually ordered."""
    try:
        q = (query or "").strip()
        if not q:
            return {"query": "", "groups": []}
        ordered_codes, skus, so_name = set(), [], None

        oname = q.lstrip("#").strip()
        for cand in (q, oname, "#" + oname):
            if frappe.db.exists("Sales Order", cand):
                so_name = cand
                break
        if so_name:
            for r in frappe.db.sql(
                """SELECT soi.item_code AS code, it.custom_sku AS sku
                   FROM `tabSales Order Item` soi
                   LEFT JOIN `tabItem` it ON it.name = soi.item_code
                   WHERE soi.parent = %s""", (so_name,), as_dict=True):
                ordered_codes.add(r.code)
                if r.sku:
                    skus.append(r.sku)
        elif frappe.db.exists("Item", q):
            ordered_codes.add(q)
            sku = frappe.db.get_value("Item", q, "custom_sku")
            if sku:
                skus.append(sku)
        elif frappe.db.exists("Item", {"custom_sku": q}):
            skus.append(q)
        else:
            like = f"%{q}%"
            for r in frappe.db.sql(
                """SELECT DISTINCT custom_sku FROM `tabItem`
                   WHERE COALESCE(custom_sku,'') != '' AND (custom_sku LIKE %s OR item_name LIKE %s)
                   LIMIT 8""", (like, like), as_dict=True):
                skus.append(r.custom_sku)

        skus = list(dict.fromkeys([s for s in skus if s]))[:6]
        if not skus:
            return {"query": q, "order": so_name, "groups": []}

        ph = ", ".join(["%s"] * len(skus))
        items = frappe.db.sql(
            f"""SELECT name AS code, item_name AS name, custom_sku AS sku
                FROM `tabItem` WHERE custom_sku IN ({ph})
                ORDER BY custom_sku LIMIT %s""",
            tuple(skus) + (min(int(limit), 300),), as_dict=True)

        codes = [it.code for it in items]
        binmap = {}
        if codes:
            cph = ", ".join(["%s"] * len(codes))
            wp = _SKU_WH_PATTERNS
            for b in frappe.db.sql(
                f"""SELECT item_code, warehouse,
                       ROUND(actual_qty - reserved_qty) AS net, ROUND(actual_qty) AS onhand
                    FROM `tabBin`
                    WHERE item_code IN ({cph}) AND actual_qty <> 0
                      AND warehouse LIKE %s AND warehouse NOT LIKE %s AND warehouse NOT LIKE %s
                      AND warehouse NOT LIKE %s AND warehouse NOT LIKE %s AND warehouse NOT LIKE %s""",
                tuple(codes) + tuple(wp), as_dict=True):
                binmap.setdefault(b.item_code, []).append(
                    {"bin": b.warehouse, "net": int(b.net or 0), "onHand": int(b.onhand or 0)})

        groups = {}
        for it in items:
            g = groups.setdefault(it.sku, {"sku": it.sku, "items": [], "anyStock": False})
            bins = sorted(binmap.get(it.code, []), key=lambda x: -x["net"])
            avail = sum(x["net"] for x in bins)
            if avail > 0:
                g["anyStock"] = True
            g["items"].append({
                "code": it.code, "name": it.name or it.code, "avail": avail,
                "ordered": it.code in ordered_codes, "bins": bins[:4],
            })
        out = []
        for g in groups.values():
            # Ordered code first, then most-available.
            g["items"].sort(key=lambda x: (not x["ordered"], -x["avail"]))
            out.append(g)
        out.sort(key=lambda g: (not g["anyStock"],))
        return {"query": q, "order": so_name, "groups": out}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.sku_lookup")
        return {"query": query, "groups": []}
