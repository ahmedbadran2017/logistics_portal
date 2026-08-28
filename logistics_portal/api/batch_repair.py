"""Batch Repair — release stale Pick List batch holds.

The forensic chain (2026-08-26, item 47249811374334 @ E5A): the item's SLE
history at the shelf is perfectly consistent with Bin (+5), yet ee's batch-aware
availability said 0. The gap was SEVEN live Outward `Serial and Batch Bundle`
docs belonging to SUBMITTED Pick Lists whose orders had long shipped. A Pick
List submit reserves batches with an Outward bundle; the Delivery Note that ee
creates in the background consumes the stock with a FRESH bundle of its own, so
the Pick List's hold is never released — every shipped batched unit is counted
twice at batch level, forever.

Site-wide at discovery: 21,896 live PL bundles holding −33,836 units; 9,203 of
them (−20,950 units) belonged to fully-delivered pick lists. That is what made
physically-stocked items unpickable (37 items, 444 pending orders touched).

Safety model:
  * Only bundles with ZERO Stock Ledger references are touched — a PL hold never
    posts stock, so releasing it moves NO stock; Bin is untouched by design.
  * Only bundles whose Pick List's orders are ALL fully delivered (or whose PL
    was cancelled/deleted) qualify — active flows keep their holds.
  * Release = the framework's own cancel; falls back to flagging is_cancelled
    when links block it. Each release is audited with a Comment on the PL.
"""

import json

import frappe

# A bundle qualifies when: it is a live Outward PL hold, it never touched the
# stock ledger, and its pick list is finished (all orders fully delivered) or
# gone (cancelled/deleted).
_STALE_FROM = """
    FROM `tabSerial and Batch Bundle` sbb
    LEFT JOIN `tabPick List` pl ON pl.name = sbb.voucher_no
    WHERE sbb.voucher_type = 'Pick List' AND sbb.docstatus = 1
      AND sbb.is_cancelled = 0
      AND NOT EXISTS (SELECT 1 FROM `tabStock Ledger Entry` sle
                      WHERE sle.serial_and_batch_bundle = sbb.name
                        AND sle.is_cancelled = 0)
      AND (pl.name IS NULL OR pl.docstatus = 2
           OR (pl.docstatus = 1 AND NOT EXISTS (
                 SELECT 1 FROM `tabPick List Item` pli
                 JOIN `tabSales Order` so ON so.name = pli.sales_order
                 WHERE pli.parent = pl.name
                   AND COALESCE(so.per_delivered, 0) < 100)))
"""


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can run batch repair.", frappe.PermissionError)


@frappe.whitelist()
def scan():
    """The evidence: how many stale holds exist, how many units they eat, and
    which stocked items they currently block."""
    _gate()
    stale = frappe.db.sql(
        f"""SELECT COUNT(DISTINCT sbb.name),
                   ROUND(COALESCE(SUM(sbe.qty), 0))
            {_STALE_FROM.replace('WHERE', 'JOIN `tabSerial and Batch Entry` sbe ON sbe.parent = sbb.name WHERE', 1)}""")[0]
    all_holds = frappe.db.sql(
        """SELECT COUNT(DISTINCT sbb.name), ROUND(COALESCE(SUM(sbe.qty), 0))
           FROM `tabSerial and Batch Bundle` sbb
           JOIN `tabSerial and Batch Entry` sbe ON sbe.parent = sbb.name
           WHERE sbb.voucher_type = 'Pick List' AND sbb.docstatus = 1
             AND sbb.is_cancelled = 0""")[0]
    return {
        "staleBundles": int(stale[0] or 0),
        "staleUnits": abs(int(stale[1] or 0)),
        "allHoldBundles": int(all_holds[0] or 0),
        "allHoldUnits": abs(int(all_holds[1] or 0)),
    }


@frappe.whitelist(methods=["POST"])
def release(limit=50):
    """Release up to `limit` stale holds (oldest first). Framework cancel with a
    raw-flag fallback; every release leaves an audit Comment on the pick list.
    Returns what was freed so the manager can verify item availability jumped."""
    _gate()
    limit = min(max(int(limit or 50), 1), 1000)
    names = [r[0] for r in frappe.db.sql(
        f"SELECT DISTINCT sbb.name {_STALE_FROM} ORDER BY sbb.creation LIMIT %s",
        (limit,))]
    if not names:
        return {"released": 0, "unitsFreed": 0, "failed": 0, "items": []}

    released, failed = 0, 0
    items_touched = {}
    for nm in names:
        try:
            doc = frappe.get_doc("Serial and Batch Bundle", nm)
            pl_name = doc.voucher_no
            qty = abs(sum(float(e.qty or 0) for e in (doc.entries or [])))
            for e in (doc.entries or []):
                items_touched[doc.item_code] = items_touched.get(doc.item_code, 0) + abs(float(e.qty or 0))
            try:
                doc.flags.ignore_permissions = True
                doc.cancel()
            except Exception:
                # Links can block a formal cancel; the hold has no SLE (query
                # guard), so flagging it cancelled only affects availability.
                frappe.db.set_value("Serial and Batch Bundle", nm,
                                    {"is_cancelled": 1}, update_modified=False)
            if pl_name and frappe.db.exists("Pick List", pl_name):
                try:
                    frappe.get_doc("Pick List", pl_name).add_comment(
                        "Comment",
                        f"Batch hold {nm} released ({qty:g}u) — orders delivered, "
                        f"hold was double-counting batch stock · by {frappe.session.user}")
                except Exception:
                    pass
            released += 1
        except Exception:
            failed += 1
            frappe.log_error(frappe.get_traceback(), "batch_repair.release")
    frappe.db.commit()

    # The availability caches these holds poisoned.
    cache = frappe.cache()
    for it in items_touched:
        cache.delete_value(f"lp_bt_{it}")
    for k in ("lp_pick_avail", "lp_board_summary", "lp_problem_radar"):
        cache.delete_value(k)

    top = sorted(items_touched.items(), key=lambda x: -x[1])[:10]
    return {"released": released, "failed": failed,
            "unitsFreed": round(sum(items_touched.values())),
            "items": [{"itemCode": k, "units": round(v)} for k, v in top]}


# ── The SRE sibling (found 2026-08-28, item 45779760283902): the sales flow
# flips custom_sales_status to Cancelled WITHOUT cancelling the Sales Order
# document, so ERPNext never releases its Stock Reservation Entries. Measured:
# 497 live SREs on Cancelled orders holding 539 units across 212 items — each
# one a false-OOS in the pick pool (the pool subtracts every active SRE).
_SRE_STALE = """
    FROM `tabStock Reservation Entry` sre
    JOIN `tabSales Order` so ON so.name = sre.voucher_no
    WHERE sre.docstatus = 1
      AND sre.status IN ('Reserved', 'Partially Delivered')
      AND so.custom_sales_status IN ('Cancelled', 'Duplicated')
"""


@frappe.whitelist()
def sre_scan():
    """The evidence: reservations still alive on orders sales already killed."""
    _gate()
    tot = frappe.db.sql(
        f"""SELECT COUNT(*), COALESCE(SUM(sre.reserved_qty - sre.delivered_qty), 0),
                   COUNT(DISTINCT sre.item_code) {_SRE_STALE}""")[0]
    sample = frappe.db.sql(
        f"""SELECT sre.item_code, sre.voucher_no,
                   (sre.reserved_qty - sre.delivered_qty), DATE(sre.creation)
            {_SRE_STALE} ORDER BY sre.creation LIMIT 12""")
    return {
        "staleRes": int(tot[0] or 0),
        "staleResUnits": round(float(tot[1] or 0)),
        "staleResItems": int(tot[2] or 0),
        "sample": [{"item": r[0], "order": r[1], "qty": round(float(r[2] or 0)),
                    "since": str(r[3])} for r in sample],
    }


@frappe.whitelist(methods=["POST"])
def sre_release(limit=50):
    """Cancel up to `limit` stale reservations (oldest first) — the framework's
    own cancel, so ERPNext updates Bin.reserved_qty itself. Audited with a
    Comment on each order."""
    _gate()
    limit = min(max(int(limit or 50), 1), 1000)
    names = [r[0] for r in frappe.db.sql(
        f"SELECT sre.name {_SRE_STALE} ORDER BY sre.creation LIMIT %s", (limit,))]
    if not names:
        return {"released": 0, "unitsFreed": 0, "failed": 0, "items": []}
    released, failed = 0, 0
    items_touched = {}
    for nm in names:
        try:
            doc = frappe.get_doc("Stock Reservation Entry", nm)
            qty = float(doc.reserved_qty or 0) - float(doc.delivered_qty or 0)
            doc.flags.ignore_permissions = True
            doc.cancel()
            items_touched[doc.item_code] = items_touched.get(doc.item_code, 0) + qty
            if doc.voucher_no and frappe.db.exists("Sales Order", doc.voucher_no):
                try:
                    frappe.get_doc("Sales Order", doc.voucher_no).add_comment(
                        "Comment",
                        f"Stale stock reservation {nm} released ({qty:g}u) — the "
                        f"order is sales-cancelled, the reservation was blocking "
                        f"live orders · by {frappe.session.user}")
                except Exception:
                    pass
            released += 1
        except Exception:
            failed += 1
            frappe.log_error(frappe.get_traceback(), "batch_repair.sre_release")
    frappe.db.commit()
    cache = frappe.cache()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_problem_radar"):
        cache.delete_value(k)
    top = sorted(items_touched.items(), key=lambda x: -x[1])[:10]
    return {"released": released, "failed": failed,
            "unitsFreed": round(sum(items_touched.values())),
            "items": [{"itemCode": k, "units": round(v)} for k, v in top]}


@frappe.whitelist()
def probe(item_code):
    """Before/after check for one item: Bin on shelves vs ee's batch-aware
    availability — after a release the two should converge."""
    _gate()
    item_code = (item_code or "").strip()
    binq = frappe.db.sql(
        """SELECT ROUND(COALESCE(SUM(GREATEST(actual_qty - reserved_qty, 0)), 0))
           FROM `tabBin`
           WHERE item_code = %s
             AND warehouse REGEXP '^[A-Z][0-9]{1,2}[A-Z]?[.]? - JM$'""",
        (item_code,))[0][0]
    try:
        resolver = frappe.get_attr(
            "ecommerce_integrations.overrides.pick_list.get_available_item_locations")
        locs = resolver(item_code, [], 1000000.0, "Justyol Morocco")
        ee = sum(float(l.get("qty") or 0) for l in (locs or []))
    except Exception:
        ee = 0
    return {"itemCode": item_code, "shelfBin": int(binq or 0), "eeAvailable": round(ee)}
