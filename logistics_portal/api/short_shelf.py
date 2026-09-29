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


# ---------------------------------------------------------------------------
# The manager's radar — every order a picker said was short, and whether the
# building agrees.
#
# A short pick is one person's glance, and it decides an order's fate: the
# order leaves the list and reads as out of stock. Measured 2026-09-30 over 30
# days: 2,748 reports on 628 orders, one order short-picked 62 times in six
# days. On 152 of those orders the SAME item that was "not on the shelf" later
# shipped on that same order — the piece was in the building all along, and
# that is only the floor of it, since -ex / J- orders ship without a Delivery
# Note and are invisible to that test.
#
# count_worklist above is the FLOOR's view (which shelf to count). This is the
# MANAGER's view of the same evidence, per order: who said it, how many times,
# what the ledger says right now, and a verdict to record. The verdict is a
# comment on the order — the audit trail this module already writes — so a
# pair drops off the radar once checked and comes back on its own if a picker
# reports it short again afterwards.
# ---------------------------------------------------------------------------
import re as _re

_CHECK = "Short pick check:"
_ITEM_RE = _re.compile(r"item \(([^)]+)\)")
_WHO_RE = _re.compile(r" by (\S+) — pulled off ([^;]+);")


def _radar_gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("manager", "dispatcher"):
        frappe.throw("Not authorized.", frappe.PermissionError)


def _bin_classes():
    """(pickable, movable) warehouse sets. Pickable = the policy AND ee's veto,
    exactly what availability uses. Movable-but-not-pickable is stock that is
    in the building and one Move Stock away from a shelf."""
    from logistics_portal.api.picking import _ee_rejected
    from logistics_portal.api.stock_moves import _movable_condition
    from logistics_portal.api.warehouses import pickable_condition
    pc, pa = pickable_condition("name")
    pickable = set(frappe.db.sql_list(
        f"SELECT name FROM `tabWarehouse` WHERE is_group = 0 AND {pc}", tuple(pa)))
    pickable -= set(_ee_rejected())
    mc, ma = _movable_condition("name")
    movable = set(frappe.db.sql_list(
        f"SELECT name FROM `tabWarehouse` WHERE is_group = 0 AND disabled = 0 AND {mc}",
        tuple(ma)))
    return pickable, movable


@frappe.whitelist()
def radar(days=14, show="open"):
    """Short-picked (order, item) pairs on orders still waiting to ship.

    show = "open"     pairs nobody has checked since the last report (default)
           "checked"  pairs a manager already ruled on
    Verdict per pair, from the ledger as it stands now:
      ready    free stock on a pickable bin — the picker is probably wrong
      zone     free stock only in a zone picking skips — it needs a move
      nostock  the ledger agrees nothing is free anywhere we can move from
    """
    _radar_gate()
    days = min(max(int(days or 14), 1), 60)
    since = frappe.utils.add_days(frappe.utils.now_datetime(), -days)

    reports = frappe.db.sql(
        """SELECT reference_name AS so, content, creation
           FROM `tabComment`
           WHERE reference_doctype = 'Sales Order' AND comment_type = 'Comment'
             AND content LIKE 'Short pick:%%' AND creation >= %s
           ORDER BY creation""", (since,), as_dict=True)
    pairs = {}
    for r in reports:
        m = _ITEM_RE.search(r.content or "")
        if not m:
            continue
        k = (r.so, m.group(1))
        p = pairs.get(k)
        if not p:
            p = pairs[k] = {"so": r.so, "item": m.group(1), "times": 0,
                            "first": r.creation, "last": r.creation,
                            "picker": "", "list": "", "tote": False}
        p["times"] += 1
        p["last"] = r.creation
        w = _WHO_RE.search(r.content or "")
        if w:
            p["picker"], p["list"] = w.group(1), w.group(2).strip()
        if "STILL IN THE TOTE" in (r.content or ""):
            p["tote"] = True
    if not pairs:
        return _empty_radar(days)

    sos = tuple({k[0] for k in pairs})
    orders = {r.name: r for r in frappe.db.sql(
        """SELECT name, customer_name, transaction_date,
                  IFNULL(custom_logistics_status, '') AS log
           FROM `tabSales Order`
           WHERE name IN %s AND docstatus = 1
             AND status NOT IN ('Closed', 'Completed', 'Cancelled')
             AND IFNULL(custom_logistics_status, '') IN ('', 'Pending')""",
        (sos,), as_dict=True)}

    # The latest ruling per pair. A ruling older than the latest report is
    # stale: a picker came back and said short again after it was checked.
    ruled = {}
    for r in frappe.db.sql(
            """SELECT reference_name AS so, content, creation, owner
               FROM `tabComment`
               WHERE reference_doctype = 'Sales Order' AND comment_type = 'Comment'
                 AND content LIKE %s AND reference_name IN %s
               ORDER BY creation""", (_CHECK + "%", sos), as_dict=True):
        m = _ITEM_RE.search(r.content or "")
        if m:
            verdict = "present" if " present " in (r.content or "") else "missing"
            ruled[(r.so, m.group(1))] = {"at": r.creation, "by": r.owner,
                                        "verdict": verdict}

    # Is the order back on a list right now? Then a picker is on it already.
    on_list = {}
    for r in frappe.db.sql(
            """SELECT pli.sales_order AS so, MAX(p.name) AS pl
               FROM `tabPick List Item` pli
               JOIN `tabPick List` p ON p.name = pli.parent
               WHERE p.docstatus = 0 AND pli.sales_order IN %s
               GROUP BY pli.sales_order""", (sos,), as_dict=True):
        on_list[r.so] = r.pl

    live = [p for k, p in pairs.items() if k[0] in orders]
    if not live:
        return _empty_radar(days)
    codes = tuple({p["item"] for p in live})
    pickable, movable = _bin_classes()
    marks = active()
    bins = {}
    for r in frappe.db.sql(
            """SELECT item_code, warehouse, actual_qty,
                      GREATEST(actual_qty - reserved_qty, 0) AS free
               FROM `tabBin` WHERE item_code IN %s AND actual_qty > 0
               ORDER BY actual_qty DESC""", (codes,), as_dict=True):
        cls = ("pick" if r.warehouse in pickable
               else "zone" if r.warehouse in movable else "other")
        bins.setdefault(r.item_code, []).append({
            "warehouse": r.warehouse, "qty": int(r.actual_qty or 0),
            "free": int(r.free or 0), "cls": cls,
            "held": int(marks.get((r.item_code, r.warehouse), 0))})
    info = {r.name: r for r in frappe.db.sql(
        """SELECT name, item_name, custom_sku, image FROM `tabItem`
           WHERE name IN %s""", (codes,), as_dict=True)}

    now = frappe.utils.now_datetime()
    rows, counts, checked = [], {"ready": 0, "zone": 0, "nostock": 0}, 0
    for p in live:
        rule = ruled.get((p["so"], p["item"]))
        fresh = rule and rule["at"] > p["last"]
        if fresh:
            checked += 1
        if (show == "checked") != bool(fresh):
            continue
        bs = bins.get(p["item"], [])
        pick = sum(b["free"] for b in bs if b["cls"] == "pick")
        zone = sum(b["free"] for b in bs if b["cls"] == "zone")
        verdict = "ready" if pick > 0 else "zone" if zone > 0 else "nostock"
        counts[verdict] += 1
        o, it = orders[p["so"]], info.get(p["item"])
        rows.append({
            "order": p["so"], "customer": o.customer_name or "",
            "item": p["item"], "sku": (it.custom_sku if it else "") or "",
            "name": (it.item_name if it else "") or p["item"],
            "image": (it.image if it else "") or "",
            "times": p["times"], "firstAt": str(p["first"])[:16],
            "lastAt": str(p["last"])[:16],
            "hours": int((now - p["first"]).total_seconds() // 3600),
            "picker": p["picker"], "pickList": p["list"], "tote": p["tote"],
            "onList": on_list.get(p["so"], ""),
            "verdict": verdict, "pickFree": pick, "zoneFree": zone,
            "bins": [b for b in bs if b["cls"] != "other"][:6],
            "ruling": ({"verdict": rule["verdict"], "by": rule["by"],
                        "at": str(rule["at"])[:16]} if fresh else None),
        })
    rank = {"ready": 0, "zone": 1, "nostock": 2}
    rows.sort(key=lambda x: (rank[x["verdict"]], -x["times"], x["firstAt"]))
    return {"rows": rows, "counts": counts, "checked": checked,
            "open": len(live) - checked, "days": days}


def _empty_radar(days):
    return {"rows": [], "counts": {"ready": 0, "zone": 0, "nostock": 0},
            "checked": 0, "open": 0, "days": days}


@frappe.whitelist()
def rule(order, item_code, verdict, warehouse=None, note=None):
    """Record a manager's double-check on one short-picked (order, item).

    present  They found it. Every shelf belief about the item is dropped — the
             glance was wrong, and a held bin would keep the order unpickable.
             If the ledger has pickable stock the order is back in the pool at
             once; if it does not, the piece is physically there but the books
             say otherwise, and only a count can fix that — say so rather than
             pretend the order is ready.
    missing  Confirmed not on the shelf. The belief stays; if the ledger still
             claims stock there, that bin is what needs counting.
    """
    _radar_gate()
    order, item_code = (order or "").strip(), (item_code or "").strip()
    if verdict not in ("present", "missing"):
        frappe.throw("Verdict must be present or missing.")
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    if not frappe.db.exists("Item", item_code):
        frappe.throw("Unknown item.")
    warehouse = (warehouse or "").strip() or None
    user = frappe.session.user

    cleared = 0
    if verdict == "present":
        cleared = clear(item_code)
        for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
            frappe.cache().delete_value(k)

    where = f" at {warehouse}" if warehouse else ""
    extra = f" — {note.strip()}" if (note or "").strip() else ""
    text = (f"{_CHECK} present — item ({item_code}) found{where} by {user}"
            if verdict == "present" else
            f"{_CHECK} missing — item ({item_code}) confirmed not on the shelf{where} by {user}")
    frappe.get_doc("Sales Order", order).add_comment("Comment", text + extra)

    pickable, _mv = _bin_classes()
    pick_free = sum(float(r.free or 0) for r in frappe.db.sql(
        """SELECT warehouse, GREATEST(actual_qty - reserved_qty, 0) AS free
           FROM `tabBin` WHERE item_code = %s AND actual_qty > 0""",
        (item_code,), as_dict=True) if r.warehouse in pickable)
    frappe.db.commit()
    return {"ok": True, "verdict": verdict, "cleared": cleared,
            "pickFree": int(pick_free),
            # Found it, but the books have nothing to allocate: the order
            # cannot become ready until the shelf is counted up.
            "needsCount": verdict == "present" and pick_free <= 0}
