"""Packing station — the custody handover for multi-piece parcels.

The sort wall already counts every piece into its slot: `sort_scan` fills
`custom_sorted_qty` line by line and the order only turns Label Printed when
the last unit lands. So this station is NOT a second count. It is the moment
a parcel stops being a pile in a slot and becomes a sealed bag with a name
and a time on it. A piece that goes missing between the slot and the bag has
no owner today; after this it has one.

Measured 2026-09-17 over 14 days of real parcels:

    parcels shipped          5,333   (381/day)
    one piece                4,265   (80%)  — these never come here
    more than one piece      1,068   (20%)  — 76/day, 2.8 pieces each
    pieces passing this desk  3,034          — 217/day

An hour of work a day. So the station is built to cost nothing: the packer
scans the AWB, the pieces appear, each scan fills one, and the last scan
seals the parcel by itself. No confirm button, no navigation, no typing.

Progress is not a counter on a row — it is one LP Scan Event per piece
(station 'pack', with the owner and the timestamp). That single choice gives
the audit trail, the per-person performance numbers and the reload-safe
progress from the same rows, and it is the same table the pick and sort
stations already answer "who did what, how fast" from.
"""

import re

import frappe
from frappe.utils import now_datetime

from logistics_portal.api.picking import (_pack_order, _resolve_order_name,
                                          resolve_scan)
from logistics_portal.api.scanlog import log_scan


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("packer", "dispatcher", "manager", "picker"):
        frappe.throw("lp:packOnly", frappe.PermissionError)
    return role


def _is_manager():
    from logistics_portal.api.auth import resolve_role
    return resolve_role(frappe.session.user) == "manager"


# ── resolving what the PDA just read ──────────────────────────────────────

def _order_from_code(code):
    """The parcel a scanned code names. The label carries the AWB, so that is
    the normal path; an order number typed by hand also works, because a label
    that will not read is exactly when someone types."""
    raw = (code or "").strip()
    if not raw:
        return None
    name = _resolve_order_name(raw)
    if name:
        return name
    # AWB: printed as LD00<digits>, scanned sometimes with the prefix and
    # sometimes as bare digits (the same tolerance the manifest scanner needs).
    m = re.search(r"(?:LD0*)?(\d{5,14})", raw.upper())
    cands = [raw]
    if m:
        d = m.group(1)
        cands += [d, f"LD00{d}", f"LD{d}", d.lstrip("0")]
    for c in dict.fromkeys(cands):
        so = frappe.db.get_value("Sales Order", {"custom_awb": c, "docstatus": 1}, "name")
        if so:
            return so
    return None


def _packed_counts(order):
    """Pieces already scanned at this desk, per item — read back from the
    scan events so a reload, a dropped device or a shift change never loses
    a half-packed parcel."""
    rows = frappe.db.sql(
        """SELECT item_code, COALESCE(SUM(qty), 0) AS n FROM `tabLP Scan Event`
           WHERE station = 'pack' AND sales_order = %s AND COALESCE(item_code, '') <> ''
           GROUP BY item_code""", (order,), as_dict=True)
    return {r.item_code: int(r.n or 0) for r in rows}


def _shape(order, card=None):
    """The pack card: the parcel, its pieces, and how far the packer got."""
    card = card or _pack_order(order)
    done = _packed_counts(order)
    items, packed, total = [], 0, 0
    for it in card.get("items") or []:
        qty = int(it.get("qty") or 0)
        got = min(int(done.get(it["sku"], 0)), qty)
        packed += got
        total += qty
        items.append({**it, "packed": got})
    seal = frappe.db.get_value(
        "Sales Order", order, ["custom_packed_at", "custom_packed_by"], as_dict=True) or {}
    return {
        "ok": True, "order": order, "customer": card.get("customer") or "",
        "city": card.get("city") or "", "awb": card.get("awb") or "",
        "items": items, "packed": packed, "pieces": total,
        "done": bool(seal.get("custom_packed_at")),
        "packedAt": str(seal.get("custom_packed_at") or "")[:16],
        "packedBy": (seal.get("custom_packed_by") or "").split("@")[0],
    }


# ── the desk ──────────────────────────────────────────────────────────────

@frappe.whitelist()
def pack_open(code):
    """Scan the AWB: open the parcel, or say plainly why it is not this desk's.

    A one-piece parcel is sent through untouched — 80% of the day's work, and
    the sort wall already proved it complete. Making it stop here would cost
    the floor four hundred scans a day to learn nothing.
    """
    _gate()
    order = _order_from_code(code)
    if not order:
        return {"ok": False, "reason": "unknown", "code": (code or "").strip()}
    card = _pack_order(order)
    pieces = sum(int(i.get("qty") or 0) for i in card.get("items") or [])
    if pieces <= 1:
        return {"ok": False, "reason": "single", "order": order,
                "awb": card.get("awb") or "", "customer": card.get("customer") or ""}
    st = frappe.db.get_value("Sales Order", order, "custom_logistics_status") or ""
    if st in ("Pending", "Picked", ""):
        # It has not been through the wall yet; packing it now would seal a
        # parcel nobody has counted.
        return {"ok": False, "reason": "not_sorted", "order": order, "stage": st}
    if st in ("Shipped", "Delivered", "Returned"):
        return {"ok": False, "reason": "gone", "order": order, "stage": st}
    return _shape(order, card)


@frappe.whitelist(methods=["POST"])
def pack_item(order, code):
    """One piece into the bag. The last one seals the parcel by itself."""
    _gate()
    order = _resolve_order_name(order)
    if not order:
        frappe.throw("Unknown order.")
    if frappe.db.get_value("Sales Order", order, "custom_packed_at"):
        return {"ok": False, "reason": "already_sealed", **_shape(order)}
    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item", "code": (code or "").strip()}

    card = _pack_order(order)
    line = next((i for i in (card.get("items") or []) if i["sku"] == item_code), None)
    if line is None:
        # The piece belongs to a different parcel. Saying WHICH one turns a
        # rejected scan into a found piece.
        return {"ok": False, "reason": "not_on_order", "itemCode": item_code,
                "name": r.get("name") or "", "sku": r.get("sku") or "",
                "belongsTo": _owner_parcel(item_code, order)}

    done = _packed_counts(order)
    if int(done.get(item_code, 0)) >= int(line.get("qty") or 0):
        return {"ok": False, "reason": "line_done", "itemCode": item_code,
                "name": line.get("name") or "", **_shape(order, card)}

    log_scan("pack", sales_order=order, item_code=item_code, qty=1,
             pick_list=frappe.db.get_value("Pick List Item", {"sales_order": order}, "parent"))
    out = _shape(order, card)
    out["scanned"] = item_code
    if out["packed"] >= out["pieces"]:
        out.update(_seal(order, out["pieces"]))
    return out


def _owner_parcel(item_code, not_order):
    """Which parcel at this stage actually wants this piece."""
    row = frappe.db.sql(
        """SELECT so.name, so.custom_awb AS awb, so.customer_name AS customer
           FROM `tabSales Order` so
           JOIN `tabSales Order Item` soi ON soi.parent = so.name
           WHERE so.docstatus = 1 AND soi.item_code = %s AND so.name <> %s
             AND so.custom_logistics_status = 'Label Printed'
             AND so.custom_packed_at IS NULL
             AND so.modified >= DATE_SUB(NOW(), INTERVAL 3 DAY)
           ORDER BY so.modified DESC LIMIT 1""", (item_code, not_order), as_dict=True)
    return row[0] if row else None


def _seal(order, pieces):
    """Every piece is in. Stamp the parcel with who closed it and when."""
    frappe.db.set_value("Sales Order", order, {
        "custom_packed_at": now_datetime(),
        "custom_packed_by": frappe.session.user,
    }, update_modified=False)
    try:
        frappe.get_doc("Sales Order", order).add_comment(
            "Comment", f"Packed: {int(pieces)} pieces scanned in at the packing desk "
                       f"· by {frappe.session.user}")
    except Exception:
        pass
    frappe.db.commit()
    frappe.cache().delete_value("lp_board_summary")
    return {"sealed": True, "packedBy": frappe.session.user.split("@")[0],
            "packedAt": str(now_datetime())[:16]}


@frappe.whitelist(methods=["POST"])
def pack_short(order, item_code, note=None):
    """A piece the sort wall counted in is not in the slot. The parcel stops
    here: it is flagged, the dispatcher is told, and nothing ships half-full."""
    _gate()
    order = _resolve_order_name(order)
    if not order:
        frappe.throw("Unknown order.")
    item_code = (item_code or "").strip()
    name = frappe.db.get_value("Item", item_code, "item_name") or item_code
    sku = frappe.db.get_value("Item", item_code, "custom_sku") or item_code
    note = (note or "").strip()
    frappe.get_doc("Sales Order", order).add_comment(
        "Comment", f"Packing: piece missing — {sku} ({name})"
                   + (f" — {note}" if note else "")
                   + f" · by {frappe.session.user}")
    frappe.db.commit()
    try:
        from logistics_portal.api.shipments import _emit
        _emit("pack_short", {"order": order, "sku": sku},
              severity="critical", cooldown_h=1, audience=("dispatcher", "manager"))
    except Exception:
        pass
    return {"ok": True, "order": order, "sku": sku}


@frappe.whitelist(methods=["POST"])
def pack_reopen(order, reason=None):
    """Open a sealed parcel again. Costly on purpose: the seal is the whole
    point of the station, so breaking it needs a reason and clears the
    progress — the pieces get counted in again from zero."""
    _gate()
    order = _resolve_order_name(order)
    if not order:
        frappe.throw("Unknown order.")
    reason = (reason or "").strip()
    if not reason:
        frappe.throw("lp:reopenReason")
    frappe.db.sql("""DELETE FROM `tabLP Scan Event`
                     WHERE station = 'pack' AND sales_order = %s""", (order,))
    frappe.db.set_value("Sales Order", order, {
        "custom_packed_at": None, "custom_packed_by": None}, update_modified=False)
    frappe.get_doc("Sales Order", order).add_comment(
        "Comment", f"Packing: parcel reopened — {reason} · by {frappe.session.user}")
    frappe.db.commit()
    return {"ok": True, "order": order}


# ── the desk's own view of its day ────────────────────────────────────────

@frappe.whitelist()
def pack_board():
    """What is waiting, and what this packer has done today. Two numbers and
    a short list — anything more does not fit on a PDA and does not help."""
    _gate()
    waiting = frappe.db.sql(
        """SELECT so.name AS `order`, so.custom_awb AS awb, so.customer_name AS customer,
                  (SELECT SUM(soi.qty) FROM `tabSales Order Item` soi
                    WHERE soi.parent = so.name) AS pieces
           FROM `tabSales Order` so
           WHERE so.docstatus = 1 AND so.custom_logistics_status = 'Label Printed'
             AND so.custom_packed_at IS NULL
             AND so.modified >= DATE_SUB(NOW(), INTERVAL 3 DAY)
             AND (SELECT SUM(soi.qty) FROM `tabSales Order Item` soi
                   WHERE soi.parent = so.name) > 1
           ORDER BY so.modified DESC LIMIT 40""", as_dict=True)
    mine = frappe.db.sql(
        """SELECT COUNT(DISTINCT sales_order) AS parcels, COALESCE(SUM(qty), 0) AS pieces
           FROM `tabLP Scan Event`
           WHERE station = 'pack' AND owner = %s AND DATE(creation) = CURDATE()""",
        (frappe.session.user,), as_dict=True)[0]
    return {
        "waiting": [{"order": w.order, "awb": w.awb or "", "customer": w.customer or "",
                     "pieces": int(float(w.pieces or 0))} for w in waiting],
        "waitingN": len(waiting),
        "mine": {"parcels": int(mine.parcels or 0), "pieces": int(mine.pieces or 0)},
    }


@frappe.whitelist()
def pack_stats(days=7):
    """Per-person packing performance, measured the same way the pick and sort
    stations are: seconds per parcel and per piece, from the scans themselves."""
    _gate()
    if not _is_manager():
        frappe.throw("lp:managerOnly", frappe.PermissionError)
    days = min(max(int(days or 7), 1), 90)
    rows = frappe.db.sql(
        """SELECT owner, sales_order, MIN(creation) AS t0, MAX(creation) AS t1,
                  COALESCE(SUM(qty), 0) AS pieces
           FROM `tabLP Scan Event`
           WHERE station = 'pack' AND creation >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
             AND COALESCE(sales_order, '') <> ''
           GROUP BY owner, sales_order""", (days,), as_dict=True)
    agg = {}
    for r in rows:
        a = agg.setdefault(r.owner, {"parcels": 0, "pieces": 0, "secs": 0.0})
        a["parcels"] += 1
        a["pieces"] += int(r.pieces or 0)
        try:
            a["secs"] += max(0.0, (r.t1 - r.t0).total_seconds())
        except Exception:
            pass
    shorts = dict(frappe.db.sql(
        """SELECT owner, COUNT(*) FROM `tabComment`
           WHERE reference_doctype = 'Sales Order' AND comment_type = 'Comment'
             AND content LIKE 'Packing: piece missing%%'
             AND creation >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
           GROUP BY owner""", (days,)))
    people = []
    for user, a in agg.items():
        people.append({
            "user": user,
            "name": frappe.db.get_value("User", user, "full_name") or user.split("@")[0],
            "parcels": a["parcels"], "pieces": a["pieces"],
            "secPerParcel": round(a["secs"] / a["parcels"]) if a["parcels"] else 0,
            "secPerPiece": round(a["secs"] / a["pieces"]) if a["pieces"] else 0,
            "shorts": int(shorts.get(user, 0)),
        })
    people.sort(key=lambda p: -p["pieces"])
    return {"days": days, "people": people,
            "parcels": sum(p["parcels"] for p in people),
            "pieces": sum(p["pieces"] for p in people)}
