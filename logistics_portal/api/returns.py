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
                        WHERE d.docstatus = 1 GROUP BY dni.against_sales_order) dn
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
