"""Returns: the awaiting-return queue (carrier-flagged, parcel not yet back)
and the RET receiving batches (barcode-scanned Return Shipment docs)."""

import frappe


@frappe.whitelist()
def board(tab="awaiting", days=30, q="", limit=30, offset=0):
    """Returns workspace. tab=awaiting → orders flagged Returned with no parcel
    received yet; tab=batches → Return Shipment receiving sessions. KPIs and the
    top-missing-SKUs analytic ride along on every response."""
    try:
        days = min(max(int(days or 30), 1), 180)
        limit = min(max(int(limit or 30), 1), 100)
        offset = max(int(offset or 0), 0)
        vals = {"days": days, "limit": limit, "offset": offset}

        dn_join = """LEFT JOIN (SELECT dni.against_sales_order so_name,
                            MAX(d.custom_return_shipment) ret, MAX(d.name) dn_name
                        FROM `tabDelivery Note Item` dni
                        JOIN `tabDelivery Note` d ON d.name = dni.parent
                        WHERE d.docstatus = 1 AND d.posting_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                        GROUP BY dni.against_sales_order) dn
                     ON dn.so_name = so.name"""
        addr_join = """LEFT JOIN `tabAddress` addr
                     ON addr.name = COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address)"""
        awaiting_where = """so.docstatus = 1 AND so.custom_sales_status = 'Confirmed'
                    AND so.custom_logistics_status = 'Returned'
                    AND so.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)
                    AND (dn.ret IS NULL OR dn.ret = '')"""

        # ── KPIs (window-scoped) ──
        k = frappe.db.sql(
            f"""SELECT COUNT(*) c, COALESCE(SUM(so.grand_total),0) v
                FROM `tabSales Order` so {dn_join} WHERE {awaiting_where}""",
            vals, as_dict=True)[0]
        b = frappe.db.sql(
            """SELECT COUNT(*) c, COALESCE(SUM(total_orders),0) orders,
                      COALESCE(SUM(total_missing_qty),0) missing,
                      COALESCE(AVG(return_percentage),0) pct
               FROM `tabReturn Shipment`
               WHERE posting_date >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)""",
            vals, as_dict=True)[0]
        top_missing = frappe.db.sql(
            """SELECT rsi.sku, COALESCE(NULLIF(rsi.item_name,''), rsi.item_code) AS name,
                      SUM(rsi.missing_qty) AS qty
               FROM `tabReturn Shipment Item` rsi
               JOIN `tabReturn Shipment` rs ON rs.name = rsi.parent
               WHERE rs.posting_date >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)
                 AND rsi.missing_qty > 0
               GROUP BY rsi.sku, name ORDER BY qty DESC LIMIT 6""",
            vals, as_dict=True)
        kpis = {
            "awaiting": int(k.c or 0), "awaitingValue": round(float(k.v or 0)),
            "batches": int(b.c or 0), "receivedOrders": int(b.orders or 0),
            "missingQty": int(b.missing or 0), "avgPct": round(float(b.pct or 0), 1),
            "topMissing": [{"sku": r.sku or "—", "name": r.name or r.sku or "—",
                            "qty": int(r.qty or 0)} for r in top_missing],
        }

        # ── rows for the active tab ──
        if tab == "batches":
            bconds = ["rs.posting_date >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)"]
            if q and str(q).strip():
                vals["q"] = f"%{str(q).strip()}%"
                bconds.append("(rs.name LIKE %(q)s OR rs.owner LIKE %(q)s)")
            bwhere = " AND ".join(bconds)
            total = frappe.db.sql(
                f"SELECT COUNT(*) FROM `tabReturn Shipment` rs WHERE {bwhere}", vals)[0][0]
            rows = frappe.db.sql(
                f"""SELECT rs.name, rs.posting_date, rs.status, rs.owner,
                           rs.total_orders, rs.total_ordered_qty, rs.total_actual_qty,
                           rs.total_missing_qty, rs.return_percentage, rs.sales_returns_created
                    FROM `tabReturn Shipment` rs WHERE {bwhere}
                    ORDER BY rs.posting_date DESC, rs.modified DESC
                    LIMIT %(limit)s OFFSET %(offset)s""",
                vals, as_dict=True)
            out = [{
                "no": r.name, "date": str(r.posting_date or ""), "status": r.status or "Draft",
                "owner": r.owner or "", "orders": int(r.total_orders or 0),
                "ordered": int(r.total_ordered_qty or 0), "actual": int(r.total_actual_qty or 0),
                "missing": int(r.total_missing_qty or 0),
                "pct": round(float(r.return_percentage or 0), 1),
                "srCreated": bool(r.sales_returns_created),
            } for r in rows]
        else:
            aconds = [awaiting_where]
            if q and str(q).strip():
                vals["q"] = f"%{str(q).strip()}%"
                aconds.append("""(so.name LIKE %(q)s OR so.customer_name LIKE %(q)s
                                 OR so.custom_awb LIKE %(q)s)""")
            awhere = " AND ".join(aconds)
            total = frappe.db.sql(
                f"SELECT COUNT(*) FROM `tabSales Order` so {dn_join} WHERE {awhere}",
                vals)[0][0]
            rows = frappe.db.sql(
                f"""SELECT so.name, so.customer_name AS customer, so.grand_total AS value,
                           so.custom_awb AS awb, dn.dn_name AS dn,
                           DATEDIFF(CURDATE(), DATE(so.modified)) AS age,
                           COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
                           COALESCE(NULLIF(so.custom_shipping_city,''), addr.city) AS city
                    FROM `tabSales Order` so {dn_join} {addr_join}
                    WHERE {awhere}
                    ORDER BY so.modified DESC
                    LIMIT %(limit)s OFFSET %(offset)s""",
                vals, as_dict=True)
            out = [{
                "order": r.name, "customer": r.customer or "", "value": r.value or 0,
                "awb": r.awb or "", "dn": r.dn or "", "age": int(r.age or 0),
                "phone": r.phone or "", "city": (r.city or "").strip().title(),
            } for r in rows]

        return {"rows": out, "tab": tab, "total": int(total or 0), "kpis": kpis,
                "days": days, "serverNow": str(frappe.utils.now_datetime())[:19]}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.returns_board")
        return {}


@frappe.whitelist()
def batch_detail(name):
    """One RET receiving batch: header totals + every scanned line with its
    complete/missing state, plus the free-text missing-SKUs note."""
    try:
        if not frappe.db.exists("Return Shipment", name):
            return {}
        rs = frappe.db.get_value(
            "Return Shipment", name,
            ["name", "posting_date", "status", "owner", "shipping_company",
             "total_orders", "total_ordered_qty", "total_actual_qty",
             "total_missing_qty", "return_percentage", "sales_returns_created",
             "missing_skus", "creation", "modified"],
            as_dict=True)
        items = frappe.db.sql(
            """SELECT rsi.awb, rsi.sku, COALESCE(NULLIF(rsi.item_name,''), rsi.item_code) AS name,
                      rsi.ordered_qty, rsi.actual_qty, rsi.missing_qty,
                      rsi.is_complete, rsi.item_rate, rsi.delivery_note
               FROM `tabReturn Shipment Item` rsi
               WHERE rsi.parent = %(rs)s
               ORDER BY rsi.is_complete ASC, rsi.idx""",
            {"rs": name}, as_dict=True)
        return {
            "no": rs.name, "date": str(rs.posting_date or ""), "status": rs.status or "Draft",
            "owner": rs.owner or "", "carrier": (rs.shipping_company or "Cathedis").title(),
            "orders": int(rs.total_orders or 0), "ordered": int(rs.total_ordered_qty or 0),
            "actual": int(rs.total_actual_qty or 0), "missing": int(rs.total_missing_qty or 0),
            "pct": round(float(rs.return_percentage or 0), 1),
            "srCreated": bool(rs.sales_returns_created),
            "missingSkus": rs.missing_skus or "",
            "created": str(rs.creation)[:16], "updated": str(rs.modified)[:16],
            "items": [{
                "awb": i.awb or "", "sku": i.sku or "", "name": i.name or "",
                "ordered": int(i.ordered_qty or 0), "actual": int(i.actual_qty or 0),
                "missing": int(i.missing_qty or 0), "complete": bool(i.is_complete),
                "rate": i.item_rate or 0, "dn": i.delivery_note or "",
            } for i in items],
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.batch_detail")
        return {}


# ── kept for compatibility (legacy queue shape + inspection comments) ──────
_STATE_MAP = {"Draft": "open", "AWB Scanning": "inspect", "Item Scanning": "inspect",
              "Ready for Return": "restock", "Returned": "closed", "Cancelled": "closed"}


@frappe.whitelist()
def queue(limit=50):
    """Legacy list shape (superseded by `board`)."""
    try:
        rows = frappe.get_all(
            "Return Shipment",
            fields=["name", "status"],
            order_by="modified desc",
            limit=int(limit),
        )
        return [{
            "no": r.name, "order": "", "customer": "", "reason": "",
            "sku": "", "value": 0, "awb": "",
            "state": _STATE_MAP.get(r.status, "open"),
        } for r in rows]
    except Exception:
        return []


VALID_OUTCOMES = {"Restock", "Defective", "Re-ship"}


@frappe.whitelist()
def process(return_shipment, outcome, reason, notes=None):
    """Record the inspection outcome for a returned parcel.
    outcome: Restock | Defective | Re-ship. Only a returns/manager user may act,
    and only on a real Return Shipment."""
    from logistics_portal.api.auth import resolve_role

    if not frappe.db.exists("Return Shipment", return_shipment):
        frappe.throw("Unknown return shipment.")
    if outcome not in VALID_OUTCOMES:
        frappe.throw("Invalid outcome.")
    if resolve_role(frappe.session.user) not in ("returns", "manager"):
        frappe.throw("You are not authorized to process returns.", frappe.PermissionError)

    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Comment",
        "reference_doctype": "Return Shipment",
        "reference_name": return_shipment,
        "content": f"Processed: {outcome} — {reason}. {notes or ''}",
    }).insert()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Shipment-return receiving (استلام المرتجع) — the stage where refused parcels
# come BACK from the carrier. Wraps the existing codx_erp Return Shipment
# engine (scan_awb / scan_sku / on_submit→sales returns into Return Zone - JM)
# so the whole session runs from the portal instead of the desk.
# ---------------------------------------------------------------------------
_CODX = "codx_erp.codx_erp.doctype.return_shipment.return_shipment"


def _recv_gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("returns", "manager"):
        frappe.throw("Not authorized to receive returns.", frappe.PermissionError)


def _batch_state(name):
    """The receiving screen's full state: parcels grouped by AWB + totals."""
    doc = frappe.get_doc("Return Shipment", name)
    parcels, order = {}, []
    for it in doc.items:
        key = it.awb or it.delivery_note
        if key not in parcels:
            order.append(key)
            parcels[key] = {"awb": it.awb or "", "dn": it.delivery_note or "",
                            "items": [], "ordered": 0, "actual": 0}
        p = parcels[key]
        p["items"].append({
            "sku": it.sku or it.item_code or "", "name": it.item_name or it.item_code or "",
            "ordered": int(it.ordered_qty or 0), "actual": int(it.actual_qty or 0),
            "complete": bool(it.is_complete)})
        p["ordered"] += int(it.ordered_qty or 0)
        p["actual"] += int(it.actual_qty or 0)
    out = []
    for key in reversed(order):  # newest scan first
        p = parcels[key]
        p["done"] = p["ordered"] > 0 and p["actual"] >= p["ordered"]
        out.append(p)
    return {
        "batch": doc.name, "status": doc.status or "Draft",
        "docstatus": int(doc.docstatus),
        "parcels": out,
        "orders": int(doc.total_orders or 0),
        "ordered": int(doc.total_ordered_qty or 0),
        "actual": int(doc.total_actual_qty or 0),
        "missing": int(doc.total_missing_qty or 0),
        "pct": round(float(doc.return_percentage or 0), 1),
    }


@frappe.whitelist()
def open_batch():
    """Today's open receiving batch — resume the draft if one exists, else
    start a new Return Shipment (same doc the desk flow used)."""
    _recv_gate()
    draft = frappe.get_all("Return Shipment", filters={"docstatus": 0},
                           order_by="creation desc", limit=1)
    if draft:
        return _batch_state(draft[0].name)
    company = frappe.defaults.get_global_default("company") \
        or frappe.db.get_value("Company", {}, "name")
    doc = frappe.get_doc({
        "doctype": "Return Shipment", "company": company,
        "posting_date": frappe.utils.nowdate(), "shipping_company": "cathedis",
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    return _batch_state(doc.name)


@frappe.whitelist()
def receive_scan(batch, code):
    """One scan, auto-detected: an AWB pulls the parcel's items into the batch
    (single-piece parcels auto-complete); anything else is treated as a SKU
    and bumps the matching line's received qty."""
    _recv_gate()
    code = (code or "").strip()
    if not code:
        return {"ok": False, "reason": "empty"}
    if not frappe.db.exists("Return Shipment", batch):
        return {"ok": False, "reason": "unknown_batch"}

    # Cross-batch duplicate guard (codx only checks within the same doc).
    dup = frappe.db.sql(
        """SELECT rs.name FROM `tabReturn Shipment Item` rsi
           JOIN `tabReturn Shipment` rs ON rs.name = rsi.parent
           WHERE rsi.awb = %s AND rs.docstatus < 2 AND rs.name != %s LIMIT 1""",
        (code, batch))
    if dup:
        return {"ok": False, "reason": "in_other_batch", "batch": dup[0][0], "code": code}

    # AWB first: does a delivery note carry this code?
    dn = frappe.get_attr(_CODX + ".find_delivery_note_by_awb")(code)
    if dn:
        res = frappe.get_attr(_CODX + ".scan_awb")(batch, code)
        frappe.db.commit()
        if not res.get("success"):
            return {"ok": False, "reason": "awb_rejected", "message": res.get("message") or ""}
        return {"ok": True, "kind": "awb", "dn": res.get("delivery_note") or "",
                "single": bool(res.get("is_single_item_order")),
                "state": _batch_state(batch)}

    # Otherwise: a SKU/barcode being verified out of an opened parcel.
    res = frappe.get_attr(_CODX + ".scan_sku")(batch, code)
    frappe.db.commit()
    if not res.get("success"):
        return {"ok": False, "reason": "unknown", "message": res.get("message") or "", "code": code}
    return {"ok": True, "kind": "sku", "sku": res.get("sku") or code,
            "actual": int(res.get("actual_qty") or 0),
            "ordered": int(res.get("ordered_qty") or 0),
            "allComplete": bool(res.get("all_complete")),
            "state": _batch_state(batch)}


@frappe.whitelist()
def close_batch(batch):
    """Submit the receiving batch: codx on_submit creates the sales returns
    (stock re-enters Return Zone - JM, one return DN per parcel)."""
    _recv_gate()
    doc = frappe.get_doc("Return Shipment", batch)
    if doc.docstatus != 0:
        frappe.throw("This batch is already closed.")
    doc.submit()
    frappe.db.commit()
    state = _batch_state(batch)
    state["salesReturns"] = len((doc.sales_returns_created or "").splitlines())
    return state


# ---------------------------------------------------------------------------
# Return-Zone restock (إعادة التخزين) — the step AFTER receiving: inspect each
# returned piece and either put it back on a sellable shelf (Material Transfer
# to a pickable warehouse) or park it as defective (Returns Adjustment). This
# is what un-strands the stock sitting in Return Zone - JM.
# ---------------------------------------------------------------------------
RETURN_ZONE = "Return Zone - JM"
ADJUST_WH = "Returns Adjustment - JM"


@frappe.whitelist()
def restock_summary(limit=30):
    """What's sitting in the Return Zone right now: totals + the most valuable
    items first, plus the list of valid shelf targets for the move dropdown."""
    _recv_gate()
    limit = min(max(int(limit or 30), 1), 100)
    tot = frappe.db.sql(
        """SELECT COUNT(DISTINCT item_code), COALESCE(SUM(actual_qty),0),
                  COALESCE(SUM(stock_value),0)
           FROM `tabBin` WHERE warehouse = %s AND actual_qty > 0""",
        (RETURN_ZONE,))[0]
    rows = frappe.db.sql(
        """SELECT b.item_code, b.actual_qty AS qty, b.stock_value AS value,
                  it.custom_sku AS sku,
                  COALESCE(NULLIF(it.item_name,''), b.item_code) AS name, it.image
           FROM `tabBin` b
           LEFT JOIN `tabItem` it ON it.name = b.item_code
           WHERE b.warehouse = %s AND b.actual_qty > 0
           ORDER BY b.stock_value DESC LIMIT %s""",
        (RETURN_ZONE, limit), as_dict=True)

    from logistics_portal.api.warehouses import excluded_zones, pickable_condition
    cond, args = pickable_condition("name")
    excluded = set(excluded_zones()) | {RETURN_ZONE, ADJUST_WH}
    targets = [w[0] for w in frappe.db.sql(
        f"SELECT name FROM `tabWarehouse` WHERE is_group = 0 AND {cond} ORDER BY name",
        tuple(args)) if w[0] not in excluded]

    return {
        "items": int(tot[0] or 0), "qty": int(tot[1] or 0),
        "value": round(float(tot[2] or 0)),
        "rows": [{"itemCode": r.item_code, "sku": r.sku or "", "name": r.name,
                  "qty": int(r.qty or 0), "value": round(float(r.value or 0)),
                  "image": r.image or ""} for r in rows],
        "targets": targets,
        "adjustWh": ADJUST_WH,
    }


@frappe.whitelist()
def restock_scan(code):
    """Resolve a scanned returned piece: its Return-Zone qty and where its
    siblings live (best shelf suggestions, by existing stock)."""
    _recv_gate()
    from logistics_portal.api.picking import resolve_scan
    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item", "code": (code or "").strip()}
    in_zone = int(frappe.db.get_value(
        "Bin", {"warehouse": RETURN_ZONE, "item_code": item_code}, "actual_qty") or 0)
    if in_zone <= 0:
        return {"ok": False, "reason": "not_in_zone", "itemCode": item_code,
                "name": r.get("name"), "sku": r.get("sku")}
    from logistics_portal.api.warehouses import pickable_condition
    cond, args = pickable_condition("b.warehouse")
    suggestions = frappe.db.sql(
        f"""SELECT b.warehouse, b.actual_qty AS qty FROM `tabBin` b
            WHERE b.item_code = %s AND b.actual_qty > 0 AND {cond}
              AND b.warehouse NOT IN (%s, %s)
            ORDER BY b.actual_qty DESC LIMIT 3""",
        tuple([item_code, *args, RETURN_ZONE, ADJUST_WH]), as_dict=True)
    image = frappe.db.get_value("Item", item_code, "image") or ""
    return {"ok": True, "itemCode": item_code, "sku": r.get("sku") or "",
            "name": r.get("name") or item_code, "image": image,
            "inZone": in_zone,
            "suggestions": [{"warehouse": s.warehouse, "qty": int(s.qty or 0)}
                            for s in suggestions]}


@frappe.whitelist()
def restock_move(item_code, qty, target=None, disposition="restock"):
    """Move inspected pieces out of the Return Zone: 'restock' → the chosen
    shelf warehouse (sellable again); 'defective' → Returns Adjustment. One
    submitted Material Transfer per action — fully auditable stock ledger."""
    _recv_gate()
    qty = int(qty or 0)
    if qty <= 0:
        frappe.throw("Quantity must be at least 1.")
    if not frappe.db.exists("Item", item_code):
        frappe.throw("Unknown item.")
    available = int(frappe.db.get_value(
        "Bin", {"warehouse": RETURN_ZONE, "item_code": item_code}, "actual_qty") or 0)
    if qty > available:
        frappe.throw(f"Only {available} in the Return Zone.")

    if disposition == "defective":
        target = ADJUST_WH
    else:
        if not target or not frappe.db.exists("Warehouse", target):
            frappe.throw("Pick a target shelf.")
        if target in (RETURN_ZONE,):
            frappe.throw("Target can't be the Return Zone itself.")

    company = frappe.defaults.get_global_default("company") \
        or frappe.db.get_value("Warehouse", RETURN_ZONE, "company")
    se = frappe.get_doc({
        "doctype": "Stock Entry",
        "stock_entry_type": "Material Transfer",
        "company": company,
        "items": [{
            "item_code": item_code, "qty": qty,
            "s_warehouse": RETURN_ZONE, "t_warehouse": target,
        }],
    })
    se.flags.ignore_permissions = True
    se.insert(ignore_permissions=True)
    se.submit()
    frappe.db.commit()
    # Stock moved — availability and OOS buckets changed.
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return {"ok": True, "entry": se.name, "itemCode": item_code, "qty": qty,
            "target": target, "disposition": disposition,
            "remaining": max(0, available - qty)}
