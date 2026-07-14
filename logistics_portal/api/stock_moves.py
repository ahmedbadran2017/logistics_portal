"""Move Stock — general bin-to-bin Material Transfers from the portal.

Covers the three flows the team still did from the desk (4,468 transfers in
6 months): shelf→shelf re-slotting, SLOW ZONE→shelf replenishment, and
Receiving Zone→shelf put-away. Every move is a submitted Material Transfer —
same audit trail as the desk, none of the desk.
"""

import frappe

# Movable network = every leaf JM warehouse EXCEPT transit / Turkey / archive /
# quarantine families. Unlike pickable_condition this deliberately INCLUDES the
# settings-excluded zones (SLOW, Receiving, Return) — moving stock in and out
# of them is exactly what this screen is for.
_BLOCK_LIKE = [
    "Goods In Transit%", "Work In Progress%", "Container%", "Air Freight%",
    "Cathedis%", "Turkey%", "V-Turkey%", "dsers%", "ERPNext%", "%Old%",
    "CORRECTING%", "Aria%", "ain sebaa%", "Yakuplu%", "Stores%",
    "Finished Goods%", "Rejected%", "Defective%",
]
_BLOCK_EXACT = ["Morocco - JM"]

SLOW_WH = "SLOW ZONE - JM"
_RECEIVING_LIKE = ["%receiv%", "%reception%"]


def _movable_condition(col="name"):
    """(sql, args) — WHERE fragment selecting warehouses stock may move
    between. Params only, no interpolated names."""
    parts = [f"{col} LIKE %s"] + [f"{col} NOT LIKE %s"] * len(_BLOCK_LIKE)
    args = ["% - JM"] + list(_BLOCK_LIKE)
    parts.append(f"{col} NOT IN ({', '.join(['%s'] * len(_BLOCK_EXACT))})")
    args += _BLOCK_EXACT
    return " AND ".join(parts), args


def _receiving_condition(col):
    return ("(" + " OR ".join([f"LOWER({col}) LIKE %s"] * len(_RECEIVING_LIKE)) + ")",
            list(_RECEIVING_LIKE))


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("manager", "dispatcher", "returns", "packer"):
        frappe.throw("Not authorized to move stock.", frappe.PermissionError)


def _shelf_aisle_regexp():
    # A shelf bin: F1, H14A, B1C., AG-*, BAB-* — the sellable picking face.
    return ("(TRIM(REPLACE({c},' - JM','')) REGEXP '^[A-Za-z][0-9]{{1,2}}[A-Za-z]?[.]?$'"
            " OR UPPER({c}) LIKE 'AG-%%' OR UPPER({c}) LIKE 'BAB-%%')")


@frappe.whitelist()
def move_boot():
    """Everything the Move Stock screen needs on load: the valid warehouse
    list for the datalist, live zone KPIs, and today's transfer activity."""
    _gate()
    cond, args = _movable_condition("name")
    warehouses = [w[0] for w in frappe.db.sql(
        f"""SELECT name FROM `tabWarehouse`
            WHERE is_group = 0 AND disabled = 0 AND {cond} ORDER BY name""",
        tuple(args))]

    rcond, rargs = _receiving_condition("warehouse")
    recv = frappe.db.sql(
        f"""SELECT COUNT(DISTINCT item_code), COALESCE(SUM(actual_qty),0)
            FROM `tabBin` WHERE actual_qty > 0 AND warehouse LIKE %s AND {rcond}""",
        tuple(["% - JM", *rargs]))[0]
    slow = frappe.db.sql(
        """SELECT COUNT(DISTINCT item_code), COALESCE(SUM(actual_qty),0)
           FROM `tabBin` WHERE actual_qty > 0 AND warehouse = %s""", (SLOW_WH,))[0]
    today = frappe.db.sql(
        """SELECT COUNT(*), COALESCE(SUM(sed.qty),0)
           FROM `tabStock Entry` se
           JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
           WHERE se.purpose = 'Material Transfer' AND se.docstatus = 1
             AND se.posting_date = CURDATE()""")[0]

    return {
        "warehouses": warehouses,
        "kpis": {
            "receivingItems": int(recv[0] or 0), "receivingUnits": int(recv[1] or 0),
            "slowItems": int(slow[0] or 0), "slowUnits": int(slow[1] or 0),
            "todayMoves": int(today[0] or 0), "todayUnits": int(today[1] or 0),
        },
        "slowWh": SLOW_WH,
        "recent": _recent_moves(12),
    }


@frappe.whitelist()
def move_lookup(code):
    """Resolve a scanned/typed SKU: where it sits across the movable network
    (source candidates) — biggest holdings first."""
    _gate()
    from logistics_portal.api.picking import resolve_scan
    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item", "code": (code or "").strip()}
    cond, args = _movable_condition("b.warehouse")
    bins = frappe.db.sql(
        f"""SELECT b.warehouse, b.actual_qty AS qty FROM `tabBin` b
            WHERE b.item_code = %s AND b.actual_qty > 0 AND {cond}
            ORDER BY b.actual_qty DESC LIMIT 20""",
        tuple([item_code, *args]), as_dict=True)
    if not bins:
        return {"ok": False, "reason": "no_stock", "itemCode": item_code,
                "name": r.get("name"), "sku": r.get("sku")}
    image = frappe.db.get_value("Item", item_code, "image") or ""
    return {"ok": True, "itemCode": item_code, "sku": r.get("sku") or "",
            "name": r.get("name") or item_code, "image": image,
            "bins": [{"warehouse": b.warehouse, "qty": int(b.qty or 0)} for b in bins]}


@frappe.whitelist()
def move_stock(item_code, qty, source, target):
    """One submitted Material Transfer, server-validated on both ends."""
    _gate()
    qty = int(qty or 0)
    if qty <= 0:
        frappe.throw("Quantity must be at least 1.")
    if not frappe.db.exists("Item", item_code):
        frappe.throw("Unknown item.")
    source = (source or "").strip()
    target = (target or "").strip()
    if not source or not target:
        frappe.throw("Pick a source and a target bin.")
    if source == target:
        frappe.throw("Source and target are the same bin.")
    cond, args = _movable_condition("name")
    valid = {w[0] for w in frappe.db.sql(
        f"""SELECT name FROM `tabWarehouse` WHERE name IN (%s, %s)
            AND is_group = 0 AND disabled = 0 AND {cond}""",
        tuple([source, target, *args]))}
    if source not in valid:
        frappe.throw(f"{source} is not a movable bin.")
    if target not in valid:
        frappe.throw(f"{target} is not a valid target bin.")
    available = int(frappe.db.get_value(
        "Bin", {"warehouse": source, "item_code": item_code}, "actual_qty") or 0)
    if qty > available:
        frappe.throw(f"Only {available} in {source}.")

    # The source warehouse's company, never the global default (Maslak LTD has
    # no Stock Adjustment Account — the wrong order broke restock moves once).
    company = frappe.db.get_value("Warehouse", source, "company") \
        or frappe.defaults.get_global_default("company")
    se = frappe.get_doc({
        "doctype": "Stock Entry",
        "stock_entry_type": "Material Transfer",
        "company": company,
        "remarks": f"Portal move by {frappe.session.user}",
        "items": [{"item_code": item_code, "qty": qty,
                   "s_warehouse": source, "t_warehouse": target}],
    })
    se.flags.ignore_permissions = True
    se.insert(ignore_permissions=True)
    se.submit()
    frappe.db.commit()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return {"ok": True, "entry": se.name, "itemCode": item_code, "qty": qty,
            "source": source, "target": target,
            "remaining": max(0, available - qty)}


@frappe.whitelist()
def putaway_queue(limit=40):
    """What's sitting in the receiving zones waiting for a shelf, with the best
    target suggestion (the shelf already holding the same SKU, if any)."""
    _gate()
    limit = min(max(int(limit or 40), 1), 100)
    rcond, rargs = _receiving_condition("b.warehouse")
    shelf = _shelf_aisle_regexp().format(c="b2.warehouse")
    rows = frappe.db.sql(
        f"""SELECT b.item_code, b.warehouse AS source, b.actual_qty AS qty,
                   it.custom_sku AS sku,
                   COALESCE(NULLIF(it.item_name,''), b.item_code) AS name, it.image,
                   (SELECT b2.warehouse FROM `tabBin` b2
                     WHERE b2.item_code = b.item_code AND b2.actual_qty > 0
                       AND b2.warehouse LIKE '%% - JM' AND {shelf}
                     ORDER BY b2.actual_qty DESC LIMIT 1) AS suggest
            FROM `tabBin` b
            LEFT JOIN `tabItem` it ON it.name = b.item_code
            WHERE b.actual_qty > 0 AND b.warehouse LIKE %s AND {rcond}
            ORDER BY b.actual_qty DESC LIMIT %s""",
        tuple(["% - JM", *rargs, limit]), as_dict=True)
    return {"rows": [{
        "itemCode": r.item_code, "sku": r.sku or "", "name": r.name,
        "image": r.image or "", "source": r.source, "qty": int(r.qty or 0),
        "suggest": r.suggest or "",
    } for r in rows]}


@frappe.whitelist()
def replenish_queue(limit=40):
    """Shelves running dry while SLOW ZONE holds the same SKU: sold recently,
    shelf stock under the low threshold. Suggested qty = a week of cover."""
    _gate()
    from logistics_portal.api.inventory import _low_threshold
    limit = min(max(int(limit or 40), 1), 100)
    low = _low_threshold()
    shelf = _shelf_aisle_regexp().format(c="b.warehouse")
    rows = frappe.db.sql(
        f"""SELECT slow.item_code, slow.q AS slowQty,
                   COALESCE(sh.q, 0) AS shelfQty, s.sold,
                   it.custom_sku AS sku,
                   COALESCE(NULLIF(it.item_name,''), slow.item_code) AS name, it.image,
                   sh.top_wh AS suggest
            FROM (SELECT item_code, SUM(actual_qty) q FROM `tabBin`
                  WHERE warehouse = %s AND actual_qty > 0 GROUP BY item_code) slow
            JOIN (SELECT soi.item_code, SUM(soi.qty) sold FROM `tabSales Order Item` soi
                  JOIN `tabSales Order` so ON so.name = soi.parent
                  WHERE so.docstatus = 1 AND so.creation >= DATE_SUB(NOW(), INTERVAL 14 DAY)
                  GROUP BY soi.item_code) s ON s.item_code = slow.item_code
            LEFT JOIN (SELECT b.item_code, SUM(b.actual_qty) q,
                              SUBSTRING_INDEX(GROUP_CONCAT(b.warehouse ORDER BY b.actual_qty DESC), ',', 1) top_wh
                       FROM `tabBin` b
                       WHERE b.warehouse LIKE '%% - JM' AND b.actual_qty > 0 AND {shelf}
                       GROUP BY b.item_code) sh ON sh.item_code = slow.item_code
            LEFT JOIN `tabItem` it ON it.name = slow.item_code
            WHERE COALESCE(sh.q, 0) < %s
            ORDER BY s.sold DESC LIMIT %s""",
        (SLOW_WH, low, limit), as_dict=True)
    out = []
    for r in rows:
        sold = float(r.sold or 0)
        week_cover = max(int(round(sold / 2.0)), low)  # 14d sales ÷ 2 = a week
        suggested = min(int(r.slowQty or 0), max(1, week_cover - int(r.shelfQty or 0)))
        out.append({
            "itemCode": r.item_code, "sku": r.sku or "", "name": r.name,
            "image": r.image or "", "slowQty": int(r.slowQty or 0),
            "shelfQty": int(r.shelfQty or 0), "sold14": int(sold),
            "suggested": suggested, "suggest": r.suggest or "",
        })
    return {"rows": out, "low": low, "slowWh": SLOW_WH}


def _recent_moves(limit=12):
    rows = frappe.db.sql(
        """SELECT se.name, se.owner, se.creation,
                  se.remarks, sed.item_code, sed.qty, sed.s_warehouse, sed.t_warehouse
           FROM `tabStock Entry` se
           JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
           WHERE se.purpose = 'Material Transfer' AND se.docstatus = 1
             AND se.creation >= CURDATE() - INTERVAL 2 DAY
           ORDER BY se.creation DESC LIMIT %s""", (limit,), as_dict=True)
    return [{
        "entry": r.name, "owner": r.owner or "", "time": str(r.creation)[5:16],
        "itemCode": r.item_code, "qty": int(r.qty or 0),
        "source": r.s_warehouse or "", "target": r.t_warehouse or "",
        "viaPortal": bool((r.remarks or "").startswith("Portal")),
    } for r in rows]


@frappe.whitelist()
def recent_moves(limit=12):
    _gate()
    return {"rows": _recent_moves(min(max(int(limit or 12), 1), 50))}


# ── Goods In (Material Receipt) ─────────────────────────────────────────────
# The desk flow this replaces: 925 Material Receipts in 6 months, avg 6 lines
# × 22 units, targets = Receiving Zone mostly but also SLOW / shelves. Rates
# are never typed by the floor — ERPNext auto-fills the item valuation, and
# zero-valuation items pass with allow_zero_valuation_rate (both observed on
# the desk entries).

RECEIVING_WH = "Receiving Zone - JM"


@frappe.whitelist()
def receive_lookup(code):
    """Resolve a scanned piece for the goods-in session: identity only —
    qty is counted on the floor, value is ERPNext's job."""
    _gate()
    from logistics_portal.api.picking import resolve_scan
    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item", "code": (code or "").strip()}
    image = frappe.db.get_value("Item", item_code, "image") or ""
    return {"ok": True, "itemCode": item_code, "sku": r.get("sku") or "",
            "name": r.get("name") or item_code, "image": image}


@frappe.whitelist()
def post_receipt(items=None, target=None, note=None):
    """One submitted Material Receipt for the whole session.
    items = [{item_code, qty}], target = a movable JM warehouse."""
    _gate()
    import json as _json
    if isinstance(items, str):
        items = _json.loads(items)
    items = items or []
    if not items:
        frappe.throw("Scan at least one item.")
    if len(items) > 300:
        frappe.throw("Too many lines for one receipt — post and start a new one.")
    target = (target or "").strip() or RECEIVING_WH
    cond, args = _movable_condition("name")
    ok = frappe.db.sql(
        f"""SELECT 1 FROM `tabWarehouse` WHERE name = %s
            AND is_group = 0 AND disabled = 0 AND {cond}""",
        tuple([target, *args]))
    if not ok:
        frappe.throw(f"{target} is not a valid receiving bin.")

    lines, total = [], 0
    for it in items:
        code = (it.get("item_code") or "").strip()
        qty = int(it.get("qty") or 0)
        if not code or qty <= 0:
            continue
        if not frappe.db.exists("Item", code):
            frappe.throw(f"Unknown item: {code}")
        # Rate stays empty on purpose: ERPNext fills the item valuation, and
        # allow_zero_valuation_rate lets first-ever receipts through at 0.
        lines.append({"item_code": code, "qty": qty, "t_warehouse": target,
                      "allow_zero_valuation_rate": 1})
        total += qty
    if not lines:
        frappe.throw("Scan at least one item.")

    company = frappe.db.get_value("Warehouse", target, "company") \
        or frappe.defaults.get_global_default("company")
    note = (note or "").strip()
    se = frappe.get_doc({
        "doctype": "Stock Entry",
        "stock_entry_type": "Material Receipt",
        "company": company,
        "remarks": f"Portal goods-in by {frappe.session.user}"
                   + (f" — {note}" if note else ""),
        "items": lines,
    })
    se.flags.ignore_permissions = True
    se.insert(ignore_permissions=True)
    se.submit()
    frappe.db.commit()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return {"ok": True, "entry": se.name, "lines": len(lines), "units": total,
            "target": target}


@frappe.whitelist()
def recent_receipts(limit=10):
    """Last goods-in entries (7 days) — one row per receipt, with totals."""
    _gate()
    limit = min(max(int(limit or 10), 1), 50)
    rows = frappe.db.sql(
        """SELECT se.name, se.owner, se.creation, se.remarks,
                  COUNT(*) AS ln, ROUND(SUM(sed.qty)) AS units,
                  MAX(sed.t_warehouse) AS target
           FROM `tabStock Entry` se
           JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
           WHERE se.purpose = 'Material Receipt' AND se.docstatus = 1
             AND se.creation >= CURDATE() - INTERVAL 7 DAY
           GROUP BY se.name, se.owner, se.creation, se.remarks
           ORDER BY se.creation DESC LIMIT %s""", (limit,), as_dict=True)
    return {"rows": [{
        "entry": r.name, "owner": r.owner or "", "time": str(r.creation)[5:16],
        "lines": int(r.ln or 0), "units": int(r.units or 0),
        "target": r.target or "",
        "viaPortal": bool((r.remarks or "").startswith("Portal")),
    } for r in rows]}
