"""Live stock levels from ERPNext Bins (real, rich data) in the SPA shapes."""

import frappe

LOW_THRESHOLD = 10  # units at/below which a SKU is "low" (until Item reorder levels are wired)


def _grp_case(col="b.warehouse"):
    """SQL expression mapping a warehouse to its physical family — the same
    grouping the Warehouse floor map uses (named zones as-is, lettered aisles
    per rack letter, AG/BAB racks as blocks)."""
    return f"""CASE
      WHEN TRIM(REPLACE({col}, ' - JM', '')) REGEXP '^[A-Za-z][0-9]{{1,2}}[A-Za-z]?[.]?$'
        THEN CONCAT('Aisles ', UPPER(LEFT(TRIM(REPLACE({col}, ' - JM', '')), 1)))
      WHEN UPPER({col}) LIKE 'AG-%%' THEN 'AG racks'
      WHEN UPPER({col}) LIKE 'BAB-%%' THEN 'BAB racks'
      ELSE TRIM(REPLACE({col}, ' - JM', ''))
    END"""


@frappe.whitelist()
def stock(limit=30, offset=0, q="", state="", group=""):
    """Sellable stock PER SKU across the pickable network (the same scope the
    Orders board's OOS split uses). The old version listed raw Bin rows over
    every warehouse ever created — legacy Morocco/V-Turkey/ERPNext included —
    with the same SKU repeating per bin and no search. Returns
    {rows, total, limit, offset}."""
    try:
        from logistics_portal.api.warehouses import pickable_condition
        cond, args = pickable_condition("b.warehouse")
        limit = min(max(int(limit or 30), 1), 100)
        offset = max(int(offset or 0), 0)

        filters = [cond, "b.actual_qty > 0"]
        vals = list(args)
        if group:
            filters.append(_grp_case() + " = %s")
            vals.append(group)
        if q:
            like = f"%{str(q).strip()}%"
            filters.append("(b.item_code LIKE %s OR i.custom_sku LIKE %s OR i.item_name LIKE %s)")
            vals += [like, like, like]
        having = f"HAVING SUM(b.actual_qty) <= {int(LOW_THRESHOLD)}" if state == "low" else ""
        base = f"""FROM `tabBin` b
            LEFT JOIN `tabItem` i ON i.name = b.item_code
            WHERE {' AND '.join(filters)}"""

        rows = frappe.db.sql(
            f"""SELECT b.item_code,
                       MAX(COALESCE(NULLIF(i.item_name, ''), b.item_code)) AS name,
                       MAX(i.custom_sku) AS sku, MAX(i.image) AS image,
                       ROUND(SUM(b.actual_qty)) AS on_hand,
                       ROUND(SUM(b.reserved_qty)) AS reserved,
                       ROUND(SUM(b.actual_qty * b.valuation_rate)) AS value,
                       COUNT(*) AS bins,
                       SUBSTRING_INDEX(GROUP_CONCAT(b.warehouse
                           ORDER BY b.actual_qty DESC SEPARATOR '||'), '||', 1) AS top_bin
                {base}
                GROUP BY b.item_code
                {having}
                ORDER BY on_hand DESC
                LIMIT %s OFFSET %s""",
            tuple(vals + [limit, offset]), as_dict=True)
        total = frappe.db.sql(
            f"""SELECT COUNT(*) FROM (
                    SELECT b.item_code {base} GROUP BY b.item_code {having}) t""",
            tuple(vals))[0][0]

        out = []
        for r in rows:
            on_hand = int(r.on_hand or 0)
            reserved = int(r.reserved or 0)
            out.append({
                "itemCode": r.item_code,
                "sku": r.sku or r.item_code,
                "name": r.name,
                "image": r.image or "",
                "bins": int(r.bins or 0),
                "topBin": (r.top_bin or "").replace(" - JM", ""),
                "onHand": on_hand,
                "reserved": reserved,
                "available": on_hand - reserved,
                "value": int(r.value or 0),
                "state": "low" if on_hand <= LOW_THRESHOLD else "ok",
            })
        return {"rows": out, "total": int(total or 0), "limit": limit, "offset": offset}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.inventory.stock")
        return {"rows": [], "total": 0, "limit": 30, "offset": 0}


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
def stats():
    """Headline stock KPIs, per SKU over the PICKABLE network. The old version
    counted Bin rows over every warehouse ever created — 'Out of stock: 49,600'
    was the number of zero-qty bin rows in history, not an ops number.

    strandedSku is the number that matters here: SKUs with ZERO sellable stock
    whose units are sitting in excluded zones (Return/Receiving/containers…) —
    the false-OOS the catalog work keeps hitting."""
    try:
        from logistics_portal.api.warehouses import pickable_condition
        cond, args = pickable_condition("b.warehouse")

        row = frappe.db.sql(
            f"""SELECT COUNT(*) AS sku_count,
                       ROUND(SUM(t.units)) AS total_units,
                       ROUND(SUM(t.value)) AS total_value,
                       SUM(CASE WHEN t.units <= %s THEN 1 ELSE 0 END) AS low_sku,
                       ROUND(SUM(t.reserved)) AS reserved
                FROM (
                    SELECT b.item_code, SUM(b.actual_qty) AS units,
                           SUM(b.actual_qty * b.valuation_rate) AS value,
                           SUM(b.reserved_qty) AS reserved
                    FROM `tabBin` b
                    WHERE {cond} AND b.actual_qty > 0
                    GROUP BY b.item_code
                ) t""",
            tuple([LOW_THRESHOLD] + list(args)), as_dict=True)[0]

        # Stock exists somewhere in JM, but ZERO of it is on a sellable shelf.
        stranded = frappe.db.sql(
            f"""SELECT COUNT(*) FROM (
                    SELECT b.item_code
                    FROM `tabBin` b
                    WHERE b.warehouse LIKE '%% - JM' AND b.actual_qty > 0
                    GROUP BY b.item_code
                    HAVING SUM(CASE WHEN {cond} THEN b.actual_qty ELSE 0 END) <= 0
                ) t""",
            tuple(args))[0][0]

        return {
            "skuCount": int(row.sku_count or 0),
            "totalUnits": int(row.total_units or 0),
            "totalValue": int(row.total_value or 0),
            "lowSku": int(row.low_sku or 0),
            "strandedSku": int(stranded or 0),
            "reserved": int(row.reserved or 0),
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.inventory.stats")
        return {}


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
    # The manager-configured pickable policy — the same scope every other
    # screen uses, so the Settings toggles govern this report too.
    from logistics_portal.api.warehouses import pickable_condition
    jm, wp = pickable_condition("b.warehouse")
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
            from logistics_portal.api.warehouses import pickable_condition
            cond, wargs = pickable_condition("warehouse")
            cph = ", ".join(["%s"] * len(codes))
            for b in frappe.db.sql(
                f"""SELECT item_code, warehouse,
                       ROUND(actual_qty - reserved_qty) AS net, ROUND(actual_qty) AS onhand
                    FROM `tabBin`
                    WHERE item_code IN ({cph}) AND actual_qty <> 0 AND {cond}""",
                tuple(codes) + tuple(wargs), as_dict=True):
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
