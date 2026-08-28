"""Return Repair — credit the returns a Return Shipment marked received but
never posted to stock.

The forensic chain (2026-08-28, RET-26-3656905): the document carried 75 rows,
every one flagged `is_complete = 1` with `actual_qty` filled — the floor had
physically inspected and accepted all 75 pieces — yet only 15 return Delivery
Notes existed. The credited rows are ALWAYS a contiguous prefix of the child
table (1..15, 1..16, 1..88, 1..182 on four sampled documents), and the return
DNs are created ~0.5s apart, so the pattern is a row-by-row loop that dies
part-way: everything before the failing row is already inserted and committed,
everything after it never runs, the parent still submits, and every row keeps
its "received" flag. Nothing is logged.

Consequence: stock the warehouse is holding does not exist in ERPNext. The
Restock Returns screen shows an empty Return Zone, the pieces are unpickable,
and the value sits invisible. Measured over 21 days: 585 pieces across 11 of
12 return shipments.

The loop itself lives in the Return Shipment app (not this one) — that fix
belongs to its owner. This module is the safety net: it MEASURES the gap and,
on demand, posts the missing credits.

Safety model:
  * Only rows the floor marked `is_complete` are ever credited — the flag is
    the human statement "this piece is physically here".
  * Every row is re-checked against what is ALREADY returned for that exact
    (original delivery note, item) pair, so a repeated run cannot double-credit.
  * A row is skipped when the original has nothing left to return.
  * Each credit is a normal ERPNext return Delivery Note (the same shape the
    app itself produces) posted TODAY — the stock is being counted now, and
    back-dating would trigger ledger reposts across weeks of history.
  * Per-row try/except: one bad row can never abort the batch (the exact
    failure this tool exists to repair).
  * Manager only, batched by `limit`, and every run leaves a comment on the
    Return Shipment naming what was credited.
"""

import frappe
from frappe.utils import now_datetime, nowdate

_CO = "Justyol Morocco"
_RETURN_ZONE = "Return Zone - JM"


def _gate():
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can repair returns.", frappe.PermissionError)


def _credited_map(ret):
    """(delivery_note, item_code) → units already returned, from ANY return DN
    (not just this shipment's) — the guard against double-crediting."""
    rows = frappe.db.sql(
        """SELECT dn.return_against, dni.item_code, SUM(-dni.qty)
           FROM `tabDelivery Note` dn
           JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
           WHERE dn.is_return = 1 AND dn.docstatus = 1
             AND dn.return_against IN (
                 SELECT DISTINCT i.delivery_note FROM `tabReturn Shipment Item` i
                 WHERE i.parent = %s AND COALESCE(i.delivery_note, '') != '')
           GROUP BY dn.return_against, dni.item_code""",
        (ret,))
    return {(r[0], r[1]): float(r[2] or 0) for r in rows}


def _pending_rows(ret):
    """Rows this shipment says are received but stock never got."""
    rows = frappe.db.sql(
        """SELECT idx, delivery_note, delivery_note_item, item_code, item_name,
                  COALESCE(actual_qty, ordered_qty, 1) qty
           FROM `tabReturn Shipment Item`
           WHERE parent = %s AND COALESCE(is_complete, 0) = 1
             AND COALESCE(delivery_note, '') != ''
           ORDER BY idx""", (ret,), as_dict=True)
    credited = _credited_map(ret)
    out = []
    for r in rows:
        have = credited.get((r.delivery_note, r.item_code), 0)
        want = float(r.qty or 0)
        if want - have <= 0:
            continue
        # Never credit more than the original shipped out.
        shipped = float(frappe.db.get_value(
            "Delivery Note Item",
            {"parent": r.delivery_note, "item_code": r.item_code}, "qty") or 0)
        room = max(0.0, shipped - have)
        missing = min(want - have, room)
        if missing <= 0:
            continue
        credited[(r.delivery_note, r.item_code)] = have + missing
        out.append({"idx": r.idx, "dn": r.delivery_note,
                    "dnItem": r.delivery_note_item, "item": r.item_code,
                    "name": r.item_name or r.item_code, "qty": missing})
    return out


@frappe.whitelist()
def scan(days=30):
    """Return shipments whose received rows never became stock, newest first."""
    _gate()
    days = min(max(int(days or 30), 1), 180)
    docs = frappe.db.sql(
        """SELECT r.name, DATE(r.creation) d,
                  (SELECT COUNT(*) FROM `tabReturn Shipment Item` i
                   WHERE i.parent = r.name) rows_n,
                  (SELECT COALESCE(SUM(i.is_complete), 0)
                   FROM `tabReturn Shipment Item` i WHERE i.parent = r.name) done_n,
                  (SELECT COUNT(*) FROM `tabDelivery Note` dn
                   WHERE dn.custom_return_shipment = r.name
                     AND dn.docstatus = 1) dns
           FROM `tabReturn Shipment` r
           WHERE r.docstatus = 1
             AND r.creation >= DATE_SUB(NOW(), INTERVAL %s DAY)
           ORDER BY r.creation DESC""", (days,), as_dict=True)

    out, units, value = [], 0, 0.0
    for d in docs:
        # The cheap counter (complete − created DNs) only flags candidates;
        # the row-level check is the one that decides, because a later
        # shipment may already have credited some of them.
        if int(d.done_n or 0) - int(d.dns or 0) <= 0:
            continue
        pending = _pending_rows(d.name)
        if not pending:
            continue
        n = sum(p["qty"] for p in pending)
        units += n
        val = frappe.db.sql(
            """SELECT COALESCE(SUM(i.item_rate * COALESCE(i.actual_qty, 1)), 0)
               FROM `tabReturn Shipment Item` i
               WHERE i.parent = %s AND i.idx IN %s""",
            (d.name, tuple(p["idx"] for p in pending)))[0][0]
        value += float(val or 0)
        out.append({"ret": d.name, "date": str(d.d), "rows": int(d.rows_n or 0),
                    "received": int(d.done_n or 0), "credited": int(d.dns or 0),
                    "missing": len(pending), "units": round(n),
                    "value": round(float(val or 0)),
                    "sample": pending[:6]})
    return {"docs": out, "totalDocs": len(out), "totalUnits": round(units),
            "totalValue": round(value), "days": days}


@frappe.whitelist(methods=["POST"])
def complete(ret, limit=10):
    """Post the missing return credits for ONE shipment, oldest row first."""
    _gate()
    ret = (ret or "").strip()
    if not frappe.db.exists("Return Shipment", ret):
        frappe.throw("Unknown return shipment.")
    if frappe.db.get_value("Return Shipment", ret, "docstatus") != 1:
        frappe.throw("The return shipment is not submitted.")
    limit = min(max(int(limit or 10), 1), 200)

    pending = _pending_rows(ret)[:limit]
    if not pending:
        return {"created": 0, "failed": 0, "units": 0, "rows": [],
                "remaining": 0}

    from erpnext.controllers.sales_and_purchase_return import make_return_doc

    created, failed, units, done_rows = 0, 0, 0.0, []
    for p in pending:
        try:
            doc = make_return_doc("Delivery Note", p["dn"])
            # Keep ONLY this row's line: the shipment credits piece by piece,
            # and the rest of the parcel may not have come back at all.
            line = None
            for it in doc.items:
                if p["dnItem"] and it.get("dn_detail") == p["dnItem"]:
                    line = it
                    break
            if line is None:
                for it in doc.items:
                    if it.item_code == p["item"]:
                        line = it
                        break
            if line is None:
                failed += 1
                continue
            line.qty = -abs(p["qty"])
            line.stock_qty = line.qty
            line.warehouse = _RETURN_ZONE
            doc.items = [line]
            doc.set_warehouse = _RETURN_ZONE
            doc.posting_date = nowdate()
            doc.set_posting_time = 0
            if doc.meta.has_field("custom_return_shipment"):
                doc.custom_return_shipment = ret
            doc.flags.ignore_permissions = True
            doc.insert(ignore_permissions=True)
            doc.submit()
            created += 1
            units += abs(p["qty"])
            done_rows.append({"idx": p["idx"], "dn": doc.name,
                              "item": p["item"], "qty": abs(p["qty"])})
        except Exception:
            failed += 1
            frappe.log_error(frappe.get_traceback()[:3000],
                             f"returns_repair.complete {ret} idx {p['idx']}")

    frappe.db.commit()
    if created:
        try:
            frappe.get_doc("Return Shipment", ret).add_comment(
                "Comment",
                f"Return repair: credited {created} piece(s) ({units:g}u) that "
                f"were marked received but never posted to stock "
                f"· by {frappe.session.user} · {str(now_datetime())[:16]}")
        except Exception:
            pass
        # The Return Zone just changed — every stock view built on it.
        cache = frappe.cache()
        for k in ("lp_pick_avail", "lp_board_summary", "lp_problem_radar",
                  "lp_restock_zone"):
            cache.delete_value(k)

    return {"created": created, "failed": failed, "units": round(units),
            "rows": done_rows, "remaining": len(_pending_rows(ret))}
