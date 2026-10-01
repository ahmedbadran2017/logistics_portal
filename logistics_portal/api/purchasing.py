"""PO-first receiving — Goods In.

The audit that led here: a hand-typed valuation rate on a loose Material Receipt
put 676M MAD into Aisles E. Rates must come from Purchase Orders, never keyboards.

Model (replaced the old supplier-first FIFO): a receiving session is against ONE
Purchase Order. A container arrives against a known PO, so pinning the PO makes
one Purchase Receipt map cleanly to one PO — correct rates, one currency, and a
clean landed-cost base (freight distributes over exactly that shipment). The PO
is opened either by scanning/typing its number, or by scanning the first piece:
84% of stocked items sit on exactly one open PO, so that piece auto-pins its PO;
the rest offer a short chooser.

Over-receipt (a piece not on the PO, or beyond its pending) still rides the same
receipt as an unlinked row — manager only.
"""

import json

import frappe

from logistics_portal.api.stock_moves import RECEIVING_WH, _movable_condition

COMPANY = "Justyol Morocco"
_OPEN_PO = ("po.docstatus = 1 AND po.company = %(company)s "
            "AND po.status NOT IN ('Closed', 'Completed', 'Cancelled')")


# --- Cross-dock POs belong to their own lane ---------------------------------
# A Cross-dock supplier's PO is per-order, and its goods must land in
# Cross-dock - JM: a pickable staging bin the order's own reservation protects
# (crossdock_in). Received through Goods In instead, they went to the default
# target Receiving Zone - JM, which ee's pick controller vetoes — so the order
# starved with its goods already on site. Measured 2026-09-30: 2,352 receipts /
# 2,946u of cross-dock stock sat in Receiving, and one is_rejected_warehouse
# tick on 2026-09-29 took 714 items / 6,116u dark at once. One person was
# posting through both doors, so closing this one is a gate, not training.
#
# The test is the Cross-dock lane's OWN condition, imported rather than copied,
# so the two can never drift apart. It deliberately blocks only what that lane
# can actually receive: a cross-dock PO whose order already shipped or closed
# is invisible to it, and blocking that one would leave it receivable nowhere.


def _crossdock_ready():
    return (frappe.db.has_column("Supplier", "custom_fulfillment_model")
            and frappe.db.has_column("Purchase Order", "custom_sales_order"))


def _not_lane_owned():
    """SQL tail for the PO lists: hide every PO the Cross-dock in lane shows.
    Correlated on the OUTER `po`/`poi` aliases; `s` and `so` are subquery-local,
    and the fragment needs the %(company)s arg every caller already passes."""
    if not _crossdock_ready():
        return ""
    from logistics_portal.api.crossdock_in import _EXPECTED
    return f"""
              AND NOT EXISTS (
                  SELECT 1 FROM `tabSupplier` s
                  JOIN `tabSales Order` so ON so.name = po.custom_sales_order
                  WHERE s.name = po.supplier AND {_EXPECTED})"""


def _lane_owns(po):
    """Is this exact PO one the Cross-dock in lane is waiting at the door for?"""
    if not _crossdock_ready():
        return False
    so = frappe.db.get_value("Purchase Order", po, "custom_sales_order") or ""
    if not so:
        return False
    from logistics_portal.api.crossdock_in import _expected_lines
    return any(l.po == po for l in _expected_lines(so=so))


# --- A cross-dock order that has already left ------------------------------
# The Cross-dock in lane receives goods for orders still waiting. Most of this
# lane's history runs the other way: the order shipped and its PO was never
# received — 922 such POs open on 2026-10-01.
#
# Receiving one is NOT paperwork. This site does not allow negative stock, so
# the parcel that went out took a piece that was already on the books — very
# often another order's piece: one Awani board shipped with #262269 was the
# one received for #261946, and #262269's own piece then went out with
# #262762. Post #262762's PO with nothing in hand and a piece appears in a bin
# pickers are sent to. The first version of this guard said the receipt "nets
# to zero" and steered it to the bin the Delivery Note shipped from; that was
# wrong, and it is gone.
#
# So the only honest receipt is a piece physically at the counter. It is
# allowed — and needed: it is usually owed to a waiting order whose own piece
# left with someone else (#261946 above, PO "received", nothing to pick). The
# person posting must confirm the piece is in front of them, and the screen
# names the orders it is owed to. Without a piece, the supplier delivered
# fewer pieces than orders and the PO is purchasing's to close.


def _paperwork(po):
    """None for an ordinary PO; {so, status} for a Cross-dock PO whose order
    has already left the floor."""
    if not _crossdock_ready():
        return None
    r = frappe.db.sql(
        """SELECT po.custom_sales_order AS so, s.custom_fulfillment_model AS model,
                  IFNULL(so.custom_logistics_status, '') AS status
           FROM `tabPurchase Order` po
           JOIN `tabSupplier` s ON s.name = po.supplier
           LEFT JOIN `tabSales Order` so ON so.name = po.custom_sales_order
           WHERE po.name = %s""", (po,), as_dict=True)
    if not r:
        return None
    r = r[0]
    # Still waiting = the Cross-dock in lane's business.
    if not r.so or r.model != "Cross-dock" or r.status in ("", "Pending"):
        return None
    return {"so": r.so, "status": r.status}


def _owed_to(item_codes):
    """{item_code: [waiting orders, oldest first]} for items nothing on the
    floor can currently cover — the orders a late piece should serve."""
    codes = [c for c in set(item_codes or []) if c]
    if not codes:
        return {}
    from logistics_portal.api.picking import availability
    free = (availability(codes) or [{}])[0] or {}
    starving = tuple(c for c in codes if float(free.get(c) or 0) <= 0)
    if not starving:
        return {}
    # Two indexed lookups (plain lines, then bundle components) instead of one
    # COALESCE over a join: same rows, 1 ms against 305 ms on prod.
    waiting = """so.docstatus = 1 AND so.custom_sales_status = 'Confirmed'
                 AND IFNULL(so.custom_logistics_status, '') IN ('', 'Pending')
                 AND so.status NOT IN ('Closed', 'Completed', 'Cancelled')"""
    out = {}
    for r in frappe.db.sql(
            f"""SELECT code, name, creation FROM (
                  SELECT soi.item_code AS code, so.name, so.creation
                  FROM `tabSales Order Item` soi JOIN `tabSales Order` so ON so.name = soi.parent
                  WHERE soi.item_code IN %(c)s AND soi.qty > IFNULL(soi.delivered_qty, 0)
                    AND {waiting}
                  UNION
                  SELECT pk.item_code, so.name, so.creation
                  FROM `tabPacked Item` pk JOIN `tabSales Order` so ON so.name = pk.parent
                  JOIN `tabSales Order Item` soi ON soi.name = pk.parent_detail_docname
                  WHERE pk.item_code IN %(c)s AND pk.parenttype = 'Sales Order'
                    AND soi.qty > IFNULL(soi.delivered_qty, 0) AND {waiting}
                ) t ORDER BY creation""", {"c": starving}, as_dict=True):
        out.setdefault(r.code, []).append(r.name)
    return {k: v[:5] for k, v in out.items()}


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("manager", "dispatcher", "returns", "packer"):
        frappe.throw("Not authorized to receive stock.", frappe.PermissionError)


def _is_manager():
    from logistics_portal.api.auth import resolve_role
    return resolve_role(frappe.session.user) == "manager"


def _po_card(r):
    return {"po": r.name, "supplier": r.supplier or "", "currency": r.currency or "MAD",
            "pending": int(r.pending or 0), "lines": int(r.nlines or 0),
            "date": str(r.transaction_date or "")}


@frappe.whitelist()
def receive_boot():
    """Open POs to receive against (biggest pending first) + target zones + recent
    receipts. The PO list is a suggestion strip; a session usually opens by
    scanning the PO or the first piece."""
    _gate()
    pos = frappe.db.sql(
        f"""SELECT po.name, po.supplier, po.currency, po.transaction_date,
                   ROUND(SUM(poi.qty - poi.received_qty)) AS pending,
                   COUNT(*) AS nlines
            FROM `tabPurchase Order` po
            JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            WHERE {_OPEN_PO} AND poi.qty > poi.received_qty{_not_lane_owned()}
            GROUP BY po.name
            ORDER BY pending DESC LIMIT 24""",
        {"company": COMPANY}, as_dict=True)
    cond, args = _movable_condition("name")
    warehouses = [w[0] for w in frappe.db.sql(
        f"""SELECT name FROM `tabWarehouse`
            WHERE is_group = 0 AND disabled = 0 AND {cond} ORDER BY name""",
        tuple(args))]
    return {
        "openPos": [_po_card(r) for r in pos],
        "warehouses": warehouses,
        "defaultTarget": RECEIVING_WH,
        "isManager": _is_manager(),
        "recent": _recent_prs(10),
    }


@frappe.whitelist()
def find_po(q=""):
    """Search open POs by number or supplier."""
    _gate()
    q = (q or "").strip()
    if len(q) < 2:
        return {"rows": []}
    like = f"%{q}%"
    rows = frappe.db.sql(
        f"""SELECT po.name, po.supplier, po.currency, po.transaction_date,
                   ROUND(SUM(poi.qty - poi.received_qty)) AS pending, COUNT(*) AS nlines
            FROM `tabPurchase Order` po
            JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            WHERE {_OPEN_PO} AND poi.qty > poi.received_qty
              AND (po.name LIKE %(q)s OR po.supplier LIKE %(q)s){_not_lane_owned()}
            GROUP BY po.name ORDER BY pending DESC LIMIT 20""",
        {"company": COMPANY, "q": like}, as_dict=True)
    return {"rows": [_po_card(r) for r in rows]}


def _po_lines(po):
    """One PO's still-open lines, with the item card fields the screen shows."""
    return frappe.db.sql(
        """SELECT poi.name AS po_item, poi.item_code, i.custom_sku AS sku,
                  i.item_name, i.image, poi.qty AS ordered, poi.received_qty AS received,
                  (poi.qty - poi.received_qty) AS pending, poi.rate, poi.uom,
                  COALESCE(poi.conversion_factor, 1) AS cf
           FROM `tabPurchase Order Item` poi
           JOIN `tabItem` i ON i.name = poi.item_code
           WHERE poi.parent = %s AND poi.qty > poi.received_qty
           ORDER BY poi.idx""", po, as_dict=True)


def _po_head(po):
    return frappe.db.get_value(
        "Purchase Order", po,
        ["name", "supplier", "currency", "conversion_rate", "docstatus", "status", "company"],
        as_dict=True)


@frappe.whitelist()
def open_po(po):
    """Load a receiving session for one PO — its open lines + header."""
    _gate()
    po = (po or "").strip()
    h = _po_head(po)
    if not h or h.docstatus != 1 or h.company != COMPANY \
            or h.status in ("Closed", "Completed", "Cancelled"):
        return {"ok": False, "reason": "not_open", "po": po}
    if _lane_owns(po):
        return {"ok": False, "reason": "crossdock", "po": po,
                "so": frappe.db.get_value("Purchase Order", po, "custom_sales_order") or ""}
    pw = _paperwork(po)
    lines = _po_lines(po)
    return {
        # Present => the screen locks each item to the bin its parcel left from.
        "paperwork": ({"so": pw["so"], "status": pw["status"],
                       "owedTo": _owed_to([l.item_code for l in lines])} if pw else None),
        "ok": True, "po": po, "supplier": h.supplier or "",
        "currency": h.currency or "MAD",
        "pending": int(round(sum(float(l.pending) for l in lines))),
        "ordered": int(round(sum(float(l.ordered) for l in lines))),
        "lines": [{
            "itemCode": l.item_code, "sku": (l.sku or "").strip(),
            "name": l.item_name or l.item_code, "image": l.image or "",
            "ordered": int(l.ordered or 0), "received": int(l.received or 0),
            "pending": int(l.pending or 0),
        } for l in lines],
    }


@frappe.whitelist()
def resolve_piece(code):
    """Scan a piece with no PO chosen yet: which open PO(s) is it on? Exactly one
    (the 84% case) lets the screen auto-open that PO; several offer a chooser."""
    _gate()
    from logistics_portal.api.picking import resolve_scan
    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item", "code": (code or "").strip()}
    pos = frappe.db.sql(
        f"""SELECT po.name, po.supplier, po.currency, po.transaction_date,
                   (poi.qty - poi.received_qty) AS pending, 1 AS nlines
            FROM `tabPurchase Order` po
            JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            WHERE {_OPEN_PO} AND poi.item_code = %(item)s AND poi.qty > poi.received_qty{_not_lane_owned()}
            ORDER BY po.transaction_date DESC, po.creation DESC""",
        {"company": COMPANY, "item": item_code}, as_dict=True)
    return {
        "ok": True, "itemCode": item_code, "sku": r.get("sku") or "",
        "name": r.get("name") or item_code,
        "image": frappe.db.get_value("Item", item_code, "image") or "",
        "pos": [_po_card(p) for p in pos],
    }


@frappe.whitelist()
def receive_scan(po, code):
    """Scan a piece inside an open PO session — is it on this PO, and how much is
    still pending on it."""
    _gate()
    from logistics_portal.api.picking import resolve_scan
    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item", "code": (code or "").strip()}
    pending = frappe.db.sql(
        """SELECT ROUND(SUM(poi.qty - poi.received_qty))
           FROM `tabPurchase Order Item` poi
           WHERE poi.parent = %s AND poi.item_code = %s AND poi.qty > poi.received_qty""",
        (po, item_code))
    pend = int(pending[0][0] or 0) if pending and pending[0][0] else 0
    return {"ok": True, "itemCode": item_code, "sku": r.get("sku") or "",
            "name": r.get("name") or item_code,
            "image": frappe.db.get_value("Item", item_code, "image") or "",
            "pending": pend, "onPo": pend > 0}


@frappe.whitelist()
def post_purchase_receipt(po, items=None, target=None, note=None, piece_in_hand=0):
    """One PO session -> one submitted Purchase Receipt. Scanned qty is allocated
    against that PO's open lines (rate/currency from the PO). Qty beyond the PO's
    pending, or a piece not on the PO, becomes an unlinked over-receipt row —
    manager only."""
    _gate()
    po = (po or "").strip()
    h = _po_head(po)
    if not h or h.docstatus != 1 or h.company != COMPANY \
            or h.status in ("Closed", "Completed", "Cancelled"):
        frappe.throw("That PO is not open.")
    if _lane_owns(po):
        frappe.throw(
            "This is a Cross-dock order — receive it on the Cross-dock in screen. "
            "Posted here the goods land in Receiving Zone, which picking vetoes, "
            f"and order {frappe.db.get_value('Purchase Order', po, 'custom_sales_order')} "
            "would starve with its stock already in the building.")

    if isinstance(items, str):
        items = json.loads(items)
    items = items or []
    if not items:
        frappe.throw("Scan at least one item.")
    if len(items) > 300:
        frappe.throw("Too many lines for one receipt — post and start a new one.")

    pw = _paperwork(po)
    if pw and not frappe.utils.cint(piece_in_hand):
        frappe.throw(
            f"Order {pw['so']} has already left ({pw['status']}). Its parcel shipped with "
            "a piece that was already on the books, so receiving this PO creates stock. "
            "Post it only with the piece physically in front of you — if it isn't, the "
            "supplier delivered fewer pieces than orders, and purchasing should close "
            "this PO.")
    target = (target or "").strip() or RECEIVING_WH
    cond, args = _movable_condition("name")
    if not frappe.db.sql(
            f"""SELECT 1 FROM `tabWarehouse` WHERE name = %s
                AND is_group = 0 AND disabled = 0 AND {cond}""", tuple([target, *args])):
        frappe.throw(f"{target} is not a valid receiving bin.")

    wanted = {}
    for it in items:
        code = (it.get("item_code") or "").strip()
        qty = int(it.get("qty") or 0)
        if not code or qty <= 0:
            continue
        wanted[code] = wanted.get(code, 0) + qty
    if not wanted:
        frappe.throw("Scan at least one item.")

    # This PO's open lines, per item (a piece can span two lines of the same PO).
    by_item = {}
    for l in _po_lines(po):
        by_item.setdefault(l.item_code, []).append(l)

    rows, extras = [], []
    for code, qty in wanted.items():
        remaining = qty
        for l in by_item.get(code, []):
            if remaining <= 0:
                break
            take = min(remaining, int(l.pending))
            if take <= 0:
                continue
            row = {"item_code": code, "qty": take, "warehouse": target,
                   "rate": float(l.rate or 0), "uom": l.uom,
                   "conversion_factor": float(l.cf or 1),
                   "purchase_order": po, "purchase_order_item": l.po_item}
            if not row["rate"]:
                row["allow_zero_valuation_rate"] = 1
            rows.append(row)
            remaining -= take
        if remaining > 0:
            extras.append({"item_code": code, "qty": remaining})

    if extras and not _is_manager():
        detail = ", ".join(f"{e['item_code']} ×{e['qty']}" for e in extras[:5])
        frappe.throw("These pieces are not on this PO (or beyond its pending) — "
                     f"only a manager can post an over-receipt: {detail}")
    is_mad = (h.currency or "MAD") == "MAD"
    for e in extras:
        rate = float(frappe.db.get_value("Item", e["item_code"], "valuation_rate") or 0) if is_mad else 0
        row = {"item_code": e["item_code"], "qty": e["qty"], "warehouse": target, "rate": rate}
        if not rate:
            row["allow_zero_valuation_rate"] = 1  # foreign-currency PO: value later
        rows.append(row)
    if not rows:
        frappe.throw("Nothing to receive.")

    note = (note or "").strip()
    pr = frappe.get_doc({
        "doctype": "Purchase Receipt", "supplier": h.supplier, "company": COMPANY,
        "currency": h.currency or "MAD", "conversion_rate": float(h.conversion_rate or 1),
        "set_warehouse": target,
        "remarks": f"Portal goods-in by {frappe.session.user} — PO {po}"
                   + (f" — late piece: order {pw['so']} had already left ({pw['status']}); "
                      "piece confirmed in hand" if pw else "")
                   + (f" — {note}" if note else "")
                   + (f" — over-receipt: {len(extras)} lines" if extras else ""),
        "items": rows,
    })
    pr.flags.ignore_permissions = True
    pr.insert(ignore_permissions=True)
    pr.submit()
    frappe.db.commit()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    frappe.cache().delete_keys("lp_suggest")
    total = sum(int(r["qty"]) for r in rows)
    extra_units = sum(e["qty"] for e in extras)
    return {"ok": True, "receipt": pr.name, "receipts": [pr.name], "units": total,
            "matched": total - extra_units, "extras": extra_units,
            "target": target, "latePiece": bool(pw)}


def _recent_prs(limit=10):
    rows = frappe.db.sql(
        """SELECT pr.name, pr.supplier, pr.owner, pr.creation, pr.remarks,
                  COUNT(*) AS ln, ROUND(SUM(pri.qty)) AS units,
                  MAX(pri.warehouse) AS target
           FROM `tabPurchase Receipt` pr
           JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
           WHERE pr.docstatus = 1 AND pr.creation >= CURDATE() - INTERVAL 7 DAY
           GROUP BY pr.name, pr.supplier, pr.owner, pr.creation, pr.remarks
           ORDER BY pr.creation DESC LIMIT %s""", (limit,), as_dict=True)
    return [{
        "receipt": r.name, "supplier": r.supplier or "", "owner": r.owner or "",
        "time": str(r.creation)[5:16], "lines": int(r.ln or 0),
        "units": int(r.units or 0), "target": r.target or "",
        "viaPortal": bool((r.remarks or "").startswith("Portal")),
    } for r in rows]


@frappe.whitelist()
def recent_purchase_receipts(limit=10):
    _gate()
    return {"rows": _recent_prs(min(max(int(limit or 10), 1), 50))}
