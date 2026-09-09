"""What a picker saw: this item is not on this shelf.

The short-pick report used to be written on the ORDER — a 24-hour cool-down on
`custom_short_picked_at` — and the item it was about went into the text of a
comment, where nothing can query it. That put the mark on the wrong object, and
the numbers say so plainly. Measured 2026-09-09 over one day: 195 reports for
116 distinct items, one item reported TWELVE times and another eight. Every
repeat is a picker walking to the same empty shelf, because the next order
carrying that item was never held back — only the orders already reported were.

So the cool-down punished orders (38 of the 40 the board called ready) while
failing at the one thing it existed for.

The evidence is about a SHELF, so it is recorded against (item, warehouse) and
subtracted from availability the same way an open draft's claim is. The order is
not punished at all — it simply is not ready while the piece is unfindable, and
becomes ready the moment the item turns up in another bin or is restocked.

What a report subtracts is the QUANTITY the picker went looking for, not the
bin's whole balance. Emptying the bin was the first version and it was wrong in
a way that only bulk locations reveal: one picker failing to find one piece in
PLT hid all 223 units of it, and J-005384 — a single order for a single unit —
was told "out of stock" while the shelf held 223. Measured 2026-09-09: of 68
live marks, 5 sat on bins holding 20+ units and between them hid 830, almost
all of it in PLT and Receiving Zone, which are staging areas rather than pick
faces. On a face holding one or two pieces the subtraction still empties it, so
the repeat walk is still prevented where that reading is true; on a pallet
holding hundreds it says what it actually means — one piece was misplaced —
and the count worklist is where that gets resolved.

The belief expires on its own (shortPickCooldownH), and a cycle count clears it
immediately: a human counting the shelf is a stronger observation than a human
glancing at it, and should replace it rather than wait behind it.

Stored as a site default rather than a doctype: it is small, it is transient,
and the audit trail already lives in the order's comment.
"""

import json

import frappe

_KEY = "lp_short_shelf"
_CACHE = "lp_short_shelf_active"


def _hours():
    try:
        from logistics_portal.api.settings import get_ops
        return int(get_ops("shortPickCooldownH") or 0)
    except Exception:
        return 0


def _load():
    raw = frappe.db.get_default(_KEY)
    if not raw:
        return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _prune(data):
    """Drop what has expired. Called on every write, so the default stays small
    without a scheduled job to tend it."""
    h = _hours()
    if not h:
        return {}
    from frappe.utils import now_datetime, time_diff_in_seconds
    now = now_datetime()
    out = {}
    for k, v in data.items():
        try:
            at, _q = _entry(v)
            if time_diff_in_seconds(now, at) < h * 3600:
                out[k] = v
        except Exception:
            continue
    return out


def _entry(v):
    """Rows are {at, qty}. Older rows are a bare timestamp — read as one unit,
    which is what a single report meant before the quantity was recorded."""
    if isinstance(v, dict):
        return str(v.get("at") or "")[:19], float(v.get("qty") or 1)
    return str(v or "")[:19], 1.0


def mark(item_code, warehouse, qty=1):
    """A picker stood at `warehouse` and could not find `qty` of `item_code`.

    Repeats accumulate: two pickers failing to find one piece each is evidence
    about two pieces, not the same one twice."""
    item_code = (item_code or "").strip()
    warehouse = (warehouse or "").strip()
    try:
        qty = max(1.0, float(qty or 1))
    except Exception:
        qty = 1.0
    if not (item_code and warehouse and _hours()):
        return
    from frappe.utils import now_datetime
    data = _prune(_load())
    k = "%s||%s" % (item_code, warehouse)
    prev = _entry(data[k])[1] if k in data else 0.0
    data[k] = {"at": str(now_datetime())[:19], "qty": prev + qty}
    frappe.db.set_default(_KEY, json.dumps(data))
    frappe.cache().delete_value(_CACHE)


def clear(item_code, warehouse=None):
    """A stronger observation replaces the glance — a counted shelf, or stock
    booked into it. Clears one bin, or every bin holding that item."""
    item_code = (item_code or "").strip()
    if not item_code:
        return 0
    data = _prune(_load())
    gone = 0
    for k in list(data):
        it, _, wh = k.partition("||")
        if it == item_code and (warehouse is None or wh == warehouse):
            data.pop(k, None)
            gone += 1
    if gone:
        frappe.db.set_default(_KEY, json.dumps(data))
        frappe.cache().delete_value(_CACHE)
    return gone


def active():
    """{(item_code, warehouse): qty_not_found}. Cached 60s — every availability
    call asks, and the answer only changes when a picker reports or a shelf is
    counted."""
    cached = frappe.cache().get_value(_CACHE)
    if cached is not None:
        try:
            return {(x[0], x[1]): float(x[2]) for x in json.loads(cached)}
        except Exception:
            pass
    data = _prune(_load())
    out = {}
    for k, v in data.items():
        it, _, wh = k.partition("||")
        if it and wh:
            out[(it, wh)] = _entry(v)[1]
    frappe.cache().set_value(
        _CACHE, json.dumps([[a, b, q] for (a, b), q in out.items()]),
        expires_in_sec=60)
    return out


def _entries():
    """Rows with their timestamps, newest first."""
    data = _prune(_load())
    rows = []
    for k, v in data.items():
        it, _, wh = k.partition("||")
        if it and wh:
            at, q = _entry(v)
            rows.append({"item": it, "warehouse": wh, "at": at, "qty": int(q)})
    rows.sort(key=lambda r: r["at"], reverse=True)
    return rows


@frappe.whitelist()
def count_worklist(limit=60):
    """Shelves a picker found empty that the ledger still calls stocked.

    This is the backlog the cool-down was hiding. Measured the day it was
    written: of 116 items reported empty in 24 hours, 62 still showed pickable
    stock in Bin — every one of them counted as availability by the board and
    by the create. A count is the fix; the entries where Bin already agrees are
    not listed, because there is nothing to reconcile.

    Ranked by how many waiting orders the shelf is holding up, so the first row
    is the most expensive count in the building.
    """
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("picker", "packer", "dispatcher", "manager"):
        frappe.throw("Not authorized.", frappe.PermissionError)
    limit = min(max(int(limit or 60), 1), 200)
    rows = _entries()
    if not rows:
        return {"rows": [], "items": 0, "orders": 0}

    codes = tuple({r["item"] for r in rows})
    bin_free, name_of = {}, {}
    for r in frappe.db.sql(
            """SELECT item_code, warehouse, GREATEST(actual_qty - reserved_qty, 0) AS free
               FROM `tabBin` WHERE item_code IN %s""", (codes,), as_dict=True):
        bin_free[(r.item_code, r.warehouse)] = float(r.free or 0)
    for r in frappe.db.sql(
            """SELECT name, item_name, custom_sku FROM `tabItem` WHERE name IN %s""",
            (codes,), as_dict=True):
        name_of[r.name] = (r.item_name or r.name, r.custom_sku or "")

    from logistics_portal.api.orders import BOARD_WINDOW_DAYS, _win
    waiting = {}
    for r in frappe.db.sql(
            """SELECT soi.item_code AS code, COUNT(DISTINCT so.name) AS n
               FROM `tabSales Order` so
               JOIN `tabSales Order Item` soi ON soi.parent = so.name
               LEFT JOIN (SELECT pli.sales_order FROM `tabPick List Item` pli
                          JOIN `tabPick List` p ON p.name = pli.parent
                          WHERE p.docstatus < 2 GROUP BY pli.sales_order) pl
                      ON pl.sales_order = so.name
               WHERE so.docstatus = 1 AND so.custom_sales_status = 'Confirmed'
                 AND so.custom_logistics_status = 'Pending' AND pl.sales_order IS NULL
                 AND so.creation >= %s AND soi.item_code IN %s
               GROUP BY soi.item_code""",
            (_win(BOARD_WINDOW_DAYS), codes), as_dict=True):
        waiting[r.code] = int(r.n or 0)

    out = []
    for r in rows:
        claims = bin_free.get((r["item"], r["warehouse"]), 0.0)
        if claims <= 0:
            continue          # the ledger already agrees — nothing to count
        nm, sku = name_of.get(r["item"], (r["item"], ""))
        out.append({"item": r["item"], "sku": sku, "name": nm,
                    "warehouse": r["warehouse"], "at": r["at"],
                    "ledger": int(claims), "orders": waiting.get(r["item"], 0)})
    out.sort(key=lambda x: (-x["orders"], -x["ledger"]))
    return {"rows": out[:limit], "items": len(out),
            "orders": sum(x["orders"] for x in out)}


def on_stock_reconciliation(doc, method=None):
    """A counted shelf answers the question the picker raised — clear it."""
    try:
        for it in (doc.get("items") or []):
            clear(it.get("item_code"), it.get("warehouse"))
    except Exception:
        # A hook on a stock document must never be the reason a count fails.
        pass


def seed_from_comments():
    """Carry today's reports across the cutover.

    The mark used to live on the order, so on the day this ships the shelf-level
    store is empty and every shelf a picker emptied this morning reads as
    stocked again — the knowledge would be lost exactly once, and the floor
    would re-walk it. The comment left by report_short_pick names the item, and
    the order's own pick-list rows name the bin it was standing at, so the pair
    can be rebuilt for the window that is still within the cool-down.

    Idempotent: marks expire on their own, and re-running only refreshes them.
    """
    h = _hours()
    if not h:
        return {"marks": 0}
    import re as _re
    rows = frappe.db.sql(
        """SELECT reference_name AS so, content FROM `tabComment`
           WHERE content LIKE 'Short pick:%%'
             AND creation >= DATE_SUB(NOW(), INTERVAL %s HOUR)""", (h,), as_dict=True)
    want = []
    for r in rows:
        m = _re.search(r"item \(([^)]+)\)", r.content or "")
        if m and r.so:
            want.append((r.so, m.group(1)))
    if not want:
        return {"marks": 0}
    sos = tuple({x[0] for x in want})
    codes = tuple({x[1] for x in want})
    where = {}
    for x in frappe.db.sql(
            """SELECT sales_order AS so, item_code AS c, warehouse AS wh
               FROM `tabPick List Item`
               WHERE sales_order IN %s AND item_code IN %s
               GROUP BY sales_order, item_code, warehouse""",
            (sos, codes), as_dict=True):
        where.setdefault("%s||%s" % (x.so, x.c), set()).add(x.wh)
    n = 0
    for so, code in want:
        for wh in where.get("%s||%s" % (so, code), ()):
            mark(code, wh)
            n += 1
    return {"marks": n}
