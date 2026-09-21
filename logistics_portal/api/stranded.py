"""Confirmed orders that never became a parcel.

The gap nothing in the portal showed. A confirmation agent gets a customer to
say yes; the order is submitted, allocated, Confirmed — and then, if no pick
list is ever built for it, it simply sits. Nobody owns it. It does not appear
on the confirmation board (it is decided), it does not appear on the pick floor
(there is no pick list), and it does not appear in Tracking (there is no
parcel). It ages out in silence.

On the live data these split into roughly equal thirds, with a long tail of
much older orders behind them that are effectively dead — the customer moved
on months ago, and those need closing, not picking. Hence the two windows:
the recent one is the work, "everything" is the cleanup.

The split into three is the whole point: each third needs a DIFFERENT person
to do a DIFFERENT thing, and a single "stuck orders" list would hide that.

  ready    -> the dispatcher. Nothing is wrong; a pick list was never built.
  zone     -> the floor. The stock exists in Morocco, in the wrong warehouse.
              We name the warehouse and the quantity so it is one trip.
  nostock  -> the confirmation agent. We cannot ship this. Tell the customer,
              cancel with a real reason, or flag it for purchase. Doing nothing
              is the one option that is currently automatic.

Read-only. Every action a user takes from this screen goes through the existing
endpoints (picking.create_pick_list_from_orders, confirmation.act, stock_moves)
so that the audit trail, the gates and the bonus attribution all stay put.
"""

import frappe

from logistics_portal.api.warehouses import pickable_condition

# Same sanity ceiling, and for the same reason, as confirmation._SANE_MAX: a
# handful of seeded rows carry absurd totals that would swamp every sum here.
_SANE_MAX = 100000

# Morocco is the only market. Stock under Justyol China / Maslak LTD is real
# but unreachable, and counting it would tell the floor to go fetch a bag from
# Shanghai.
_COMPANY = "Justyol Morocco"

# Never a source, whatever the settings say.
_NEVER = ["%Defective%", "%Rejected%"]

_CITY = ("COALESCE(NULLIF(TRIM(so.custom_shipping_city), ''), "
         "NULLIF(TRIM(addr.city), ''))")
_CITY_JOIN = ("LEFT JOIN `tabAddress` addr ON addr.name = "
              "COALESCE(so.shipping_address_name, so.customer_address)")

BUCKETS = ("ready", "zone", "nostock")


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("dispatcher", "confirmation", "manager"):
        frappe.throw("Not authorized for the stranded-orders queue.",
                     frappe.PermissionError)
    return role


def _no_pick_list():
    """Orders with no pick list of ANY docstatus — a cancelled pick list still
    means somebody looked at this order, and a draft means it is already queued.
    Only a total absence is stranded."""
    return """NOT EXISTS (SELECT 1 FROM `tabPick List Item` pli
                          JOIN `tabPick List` pl ON pl.name = pli.parent
                          WHERE pli.sales_order = so.name)"""


def _stock_cte():
    """(sql_fragments, args) for the two per-item stock numbers we need.

    `pickable` is the app's own configured policy (warehouses.pickable_condition
    — the same predicate the pick engine allocates against), so this screen can
    never disagree with what the floor can actually pull.

    `elsewhere` is everything else under the Morocco company that isn't
    structurally dead. That is what makes an order recoverable by moving stock
    rather than by buying it.
    """
    pick_sql, pick_args = pickable_condition("b.warehouse")
    never = " AND ".join(["w.name NOT LIKE %s"] * len(_NEVER))
    pickable = f"""COALESCE((SELECT SUM(GREATEST(b.actual_qty - b.reserved_qty, 0))
                             FROM `tabBin` b
                             WHERE b.item_code = soi.item_code AND {pick_sql}), 0)"""
    elsewhere = f"""COALESCE((SELECT SUM(GREATEST(b.actual_qty, 0))
                              FROM `tabBin` b
                              JOIN `tabWarehouse` w ON w.name = b.warehouse
                              WHERE b.item_code = soi.item_code
                                AND w.company = %s AND {never}
                                AND NOT ({pick_sql})), 0)"""
    args = list(pick_args) + [_COMPANY] + list(_NEVER) + list(pick_args)
    return pickable, elsewhere, args


def _bundle_flag():
    """1 when this order line is a product BUNDLE — a box that holds no stock
    of its own because its pieces do.

    Without this the screen judged the box by its own Bin balance, which is
    always zero by design, and called three live orders "No stock" while
    every piece inside them sat on the shelf in the hundreds (#261381 and
    #261384, JUSTYOL Top 5 Box: 702 to 3,187 pickable of each of its five
    pieces). orders.detail already knew this; this screen never learned."""
    return """EXISTS (SELECT 1 FROM `tabPacked Item` pk
                      WHERE pk.parent = so.name
                        AND pk.parenttype = 'Sales Order'
                        AND pk.parent_item = soi.item_code)"""


def _bundle_stock(orders, pickable, elsewhere, stock_args):
    """Re-judge every bundle line on its pieces: the box is available as many
    times as its scarcest piece allows.

    One grouped read for all of them, not one per order — the boxes are a
    handful of lines but the query is the same shape as the main one."""
    names = sorted({o for o, _c in orders})
    if not names:
        return {}
    pk = pickable.replace("soi.item_code", "pki.item_code")
    el = elsewhere.replace("soi.item_code", "pki.item_code")
    rows = frappe.db.sql(
        f"""SELECT pki.parent so, pki.parent_item box, pki.item_code,
                   pki.item_name, pki.qty,
                   {pk} pickable, {el} elsewhere
            FROM `tabPacked Item` pki
            WHERE pki.parenttype = 'Sales Order' AND pki.parent IN %s""",
        # Order matters: the stock sub-selects carry their placeholders in
        # the SELECT list, so their args come first and the IN tuple last.
        tuple(list(stock_args) + [tuple(names)]), as_dict=True)
    out = {}
    for r in rows:
        key = (r.so, r.box)
        if key not in orders:
            continue
        # The box goes as many times as its scarcest piece allows; one piece
        # per box is the overwhelming case, and a piece needing two is
        # already written into pki.qty.
        per = float(r.qty or 0) or 1.0
        fits_pick = float(r.pickable or 0) / per
        fits_all = (float(r.pickable or 0) + float(r.elsewhere or 0)) / per
        cur = out.setdefault(key, {"pickable": fits_pick, "elsewhere": fits_all,
                                   "worst": r})
        if fits_pick < cur["pickable"]:
            cur["pickable"], cur["worst"] = fits_pick, r
        cur["elsewhere"] = min(cur["elsewhere"], fits_all)
    for key, v in out.items():
        v["elsewhere"] = max(0.0, v["elsewhere"] - v["pickable"])
    return out


def _classify(rows, bundle_stock=None):
    """Fold order/item rows into one verdict per order.

    An order is only as good as its worst line: one missing item and the whole
    parcel cannot go — except a BUNDLE line, whose stock lives in its pieces
    and is handed in through `bundle_stock`.
    """
    bundle_stock = bundle_stock or {}
    out = {}
    for r in rows:
        o = out.setdefault(r["name"], {
            "order": r["name"], "customer": r.get("customer_name") or "—",
            "phone": r.get("phone") or "", "city": r.get("city") or "—",
            "agent": (r.get("agent") or "").split("@")[0] or "—",
            "agentUser": r.get("agent") or "",
            "value": float(r.get("grand_total") or 0),
            "ageDays": int(r.get("age_d") or 0),
            "bucket": "ready", "short": [],
        })
        want = float(r.get("qty") or 0)
        pick = float(r.get("pickable") or 0)
        away = float(r.get("elsewhere") or 0)
        bs = bundle_stock.get((r["name"], r.get("item_code")))
        if bs:
            # The box's own Bin balance is zero by design. What can be picked
            # is however many boxes its scarcest piece can fill.
            pick, away = bs["pickable"], bs["elsewhere"]
        if pick >= want:
            continue
        line = {
            # Both, deliberately. custom_sku is the SKU a human says out loud;
            # item_code is the Shopify variant id and the only thing tabBin
            # joins on. Sending only the SKU back would make the stock lookup
            # silently miss.
            "sku": (bs["worst"].get("item_code") if bs
                    else (r.get("sku") or r.get("item_code"))),
            "itemCode": (bs["worst"].get("item_code") if bs else r.get("item_code")),
            # Name the PIECE that is short, not the box it came in: "no stock
            # of JUSTYOL Top 5 Box" tells the floor nothing it can act on.
            "item": ((bs["worst"].get("item_name") or "") if bs
                     else (r.get("item_name") or ""))[:60],
            "inBox": ((r.get("item_name") or "")[:60] if bs else ""),
            "want": want, "pickable": pick, "elsewhere": away,
            "missing": round(want - pick, 2),
        }
        if pick + away >= want:
            o["short"].append({**line, "why": "zone"})
            if o["bucket"] != "nostock":
                o["bucket"] = "zone"
        else:
            o["short"].append({**line, "why": "nostock"})
            o["bucket"] = "nostock"
    return out


@frappe.whitelist()
def board(bucket="", min_age=3, max_age=60, limit=50, offset=0):
    """The queue, split by what is actually wrong with each order."""
    _gate()
    bucket = (bucket or "").strip()
    if bucket and bucket not in BUCKETS:
        frappe.throw("Unknown bucket.")
    min_age = max(0, min(int(min_age or 0), 3650))
    max_age = max(min_age, min(int(max_age or 60), 3650))
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))

    pickable, elsewhere, stock_args = _stock_cte()
    bundled = _bundle_flag()

    # One pass over the window; the verdict is per order and cannot be expressed
    # as a WHERE (it depends on every line), so we fold in Python and page after.
    rows = frappe.db.sql(
        f"""SELECT so.name, so.customer_name, so.grand_total,
                   so.custom_allocated_to agent,
                   COALESCE(NULLIF(so.custom_customer_phone, ''),
                            so.custom_shipping_phone) phone,
                   {_CITY} city,
                   DATEDIFF(NOW(), so.creation) age_d,
                   soi.item_code, soi.qty, i.custom_sku sku, i.item_name,
                   {pickable} pickable,
                   {elsewhere} elsewhere,
                   {bundled} bundled
            FROM `tabSales Order` so
            JOIN `tabSales Order Item` soi ON soi.parent = so.name
            JOIN `tabItem` i ON i.name = soi.item_code
            {_CITY_JOIN}
            WHERE so.docstatus = 1
              AND so.company = %s
              AND so.custom_sales_status = 'Confirmed'
              AND so.grand_total <= %s
              AND COALESCE(so.custom_logistics_status, '') IN ('', 'Pending')
              AND DATEDIFF(NOW(), so.creation) BETWEEN %s AND %s
              AND {_no_pick_list()}""",
        tuple(stock_args) + (_COMPANY, _SANE_MAX, min_age, max_age),
        as_dict=True)

    # Re-price the bundle lines on their pieces before judging anything.
    # One extra read, only for the boxes, and only when there are any.
    boxes = {(r["name"], r.get("item_code")) for r in rows if r.get("bundled")}
    bundle_stock = (_bundle_stock(boxes, pickable, elsewhere, stock_args)
                    if boxes else {})
    by_order = _classify(rows, bundle_stock)
    orders = list(by_order.values())

    counts = {k: {"orders": 0, "value": 0.0} for k in BUCKETS}
    for o in orders:
        c = counts[o["bucket"]]
        c["orders"] += 1
        c["value"] += o["value"]
    for c in counts.values():
        c["value"] = round(c["value"])

    shown = [o for o in orders if not bucket or o["bucket"] == bucket]
    # Oldest money first: an order that has been waiting a month is both the
    # most likely to be lost and the most likely to have been forgotten.
    shown.sort(key=lambda o: (-o["ageDays"], -o["value"]))
    total = len(shown)
    page = shown[offset:offset + limit]

    return {
        "rows": page, "total": total, "counts": counts,
        "window": {"minAge": min_age, "maxAge": max_age},
        "value": round(sum(o["value"] for o in shown)),
    }


@frappe.whitelist()
def where_is(item_code):
    """Which Morocco warehouses hold this item, and is each one pickable.

    The answer to "the system says no stock but I know we have it". Pickability
    is read from the same configured policy the pick engine uses, so a bin that
    shows pickable=0 here is genuinely one the floor cannot pull from.
    """
    _gate()
    pick_sql, pick_args = pickable_condition("b.warehouse")
    rows = frappe.db.sql(
        f"""SELECT b.warehouse, b.actual_qty qty, b.reserved_qty resv,
                   ({pick_sql}) pickable
            FROM `tabBin` b
            JOIN `tabWarehouse` w ON w.name = b.warehouse
            WHERE b.item_code = %s AND w.company = %s AND b.actual_qty > 0
            ORDER BY pickable DESC, b.actual_qty DESC
            LIMIT 40""",
        tuple(pick_args) + (item_code, _COMPANY), as_dict=True)
    return [{"warehouse": r.warehouse, "qty": float(r.qty or 0),
             "reserved": float(r.resv or 0), "pickable": bool(r.pickable)}
            for r in rows]


@frappe.whitelist()
def summary():
    """Headline for the dashboards: how much confirmed demand is stuck, and how
    old it is. Cheap enough to poll; cached briefly."""
    _gate()
    import json as _json
    cache = frappe.cache()
    hit = cache.get_value("lp_stranded_summary")
    if hit is not None:
        try:
            return _json.loads(hit)
        except Exception:
            pass
    rows = frappe.db.sql(
        f"""SELECT CASE
                     WHEN DATEDIFF(NOW(), so.creation) <= 2  THEN '0-2d'
                     WHEN DATEDIFF(NOW(), so.creation) <= 7  THEN '3-7d'
                     WHEN DATEDIFF(NOW(), so.creation) <= 30 THEN '8-30d'
                     WHEN DATEDIFF(NOW(), so.creation) <= 180 THEN '1-6mo'
                     ELSE '6mo+' END band,
                   COUNT(*) orders, SUM(so.grand_total) value
            FROM `tabSales Order` so
            WHERE so.docstatus = 1
              AND so.company = %s
              AND so.custom_sales_status = 'Confirmed'
              AND so.grand_total <= %s
              AND COALESCE(so.custom_logistics_status, '') IN ('', 'Pending')
              AND {_no_pick_list()}
            GROUP BY band""",
        (_COMPANY, _SANE_MAX), as_dict=True)
    order = ["0-2d", "3-7d", "8-30d", "1-6mo", "6mo+"]
    by = {r.band: {"orders": int(r.orders or 0), "value": round(float(r.value or 0))}
          for r in rows}
    out = {
        "bands": [{"band": b, **by.get(b, {"orders": 0, "value": 0})} for b in order],
        "orders": sum(v["orders"] for v in by.values()),
        "value": sum(v["value"] for v in by.values()),
        # Under a month old = still recoverable. Older than that and the
        # customer has moved on; those need closing, not picking.
        "liveOrders": sum(by.get(b, {"orders": 0})["orders"] for b in order[:3]),
        "liveValue": sum(by.get(b, {"value": 0})["value"] for b in order[:3]),
    }
    try:
        cache.set_value("lp_stranded_summary", _json.dumps(out), expires_in_sec=300)
    except Exception:
        pass
    return out
