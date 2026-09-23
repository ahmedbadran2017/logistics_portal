"""Sales Order stage timestamps + order detail."""

import frappe
from frappe.utils import now_datetime

def _back_in_house_join(so_col="so.name", alias="bk"):
    from logistics_portal.api.returns import back_in_house_join
    return back_in_house_join(so_col, alias)


def _back_in_house_at(order):
    """The day this order's parcel was scanned back in, or ""."""
    from logistics_portal.api.returns import back_in_house
    return back_in_house([order]).get(order, "")


def _back_in_house(so_col="so.name"):
    """The parcel was scanned back in at our dock -- see returns.back_in_house_sql
    for why that scan, and not the order's status field, is the witness."""
    from logistics_portal.api.returns import back_in_house_sql
    return back_in_house_sql(so_col)


# Which custom_*_at field each logistics status stamps (first time it is reached).
STAGE_STAMP = {
    "Picked": "custom_picked_at",
    "Label Generated": "custom_labeled_at",
    "Label Printed": "custom_labeled_at",
    "Shipped": "custom_shipped_at",
    "Delivered": "custom_delivered_at",
    "Returned": "custom_returned_at",
}


# ── Where the order came from ────────────────────────────────────────────
#
# A phone sale is a conversation that already happened. Serving it to the
# confirmation queue as a cold call phones a customer who has already said
# yes — to a colleague, minutes earlier.
#
# Shopify already answers this on the order: `source_name` is
# "shopify_draft_order" when the team pushes a draft from the admin (which is
# how a phone sale is written), and "web" or an app id for a storefront order.
PHONE_SOURCE = "shopify_draft_order"

# The operational vocabulary of the Shopify tag field. Anything on a phone
# order that is NOT one of these is a person's name — the seller.
#
# A block list, not an allow list, and deliberately: a new seller must appear
# by itself the day they make their first sale. `nidal` sold four orders this
# week and was in nobody's list. The cost of the inversion is that an unknown
# OPERATIONAL tag reads as a name once, which is a wrong word on a chip, not
# a wrong order in a queue — the queue rule keys on the source field, never
# on this.
_OPS_TAGS = {"cod", "express", "picked", "urgent", "checked", "not shipped",
             "possible-duplicate", "label generated", "out of stock",
             "virement", "confirmed", "cancelled", "duplicated", "shipped",
             "delivered", "returned", "local", "ugc"}
_OPS_PREFIX = ("tel:", "ua:", "via:", "utm", "ref:", "sku:", "coupon:")


def seller_from_tags(tags):
    """The human name on a phone order, or "" when the tag says nothing.

    Never raises and never guesses a user account: this is a word to print
    next to the customer, so the agent knows who already spoke to them. Who
    that maps to in ERPNext is a separate question this does not answer —
    `hajar` is two different colleagues, and an order does not stop being a
    phone sale because we cannot tell which."""
    for t in (tags or "").split(","):
        t = t.strip()
        if not t:
            continue
        lo = t.lower()
        if lo in _OPS_TAGS or lo.startswith(_OPS_PREFIX):
            continue
        return t[:40]
    return ""


def stamp_order_source(doc, method=None):
    """Copy Shopify's `source_name` onto the order, during the sync's own save.

    ecommerce_integrations hangs the full raw payload on the document
    (`so.flags.shopiy_order_json`, its spelling) at order.py:244 and saves at
    :254 — so this runs with the payload in hand, inside the write that was
    already happening. No second write, no `modified` bump, no call back out
    to Shopify.

    Write-once: a later portal save must never blank what the sync stamped."""
    try:
        if doc.get("custom_order_source"):
            return
        raw = doc.flags.get("shopiy_order_json") if doc.flags else None
        if not raw:
            return
        import json
        src = (json.loads(raw) or {}).get("source_name")
        if src is None:
            return
        if not frappe.get_meta("Sales Order").has_field("custom_order_source"):
            return
        doc.custom_order_source = str(src)[:140]
    except Exception:
        # Never block a customer's order over a provenance label.
        pass


def stamp_first_touch(doc, method=None):
    """Catch the work done on the ERPNext Desk, where no portal code runs.

    Measured 2026-09-21: 12.1% of decided orders carry a human Version row
    and no portal trail at all — real calls, made by real agents, on the Desk.
    A first-touch stamp written only by the portal would report those people
    as never having touched the order.

    Only a decision counts, and only a human's: the carrier sync writes the
    status through frappe.db.set_value, which never fires this hook, so the
    bot cannot stamp itself by accident."""
    try:
        if frappe.session.user in ("Administrator", "Guest"):
            return
        if not frappe.get_meta("Sales Order").has_field("custom_first_touch_at"):
            return
        if doc.get("custom_first_touch_at"):
            return
        before = doc.get_doc_before_save()
        if not before or (before.get("custom_sales_status")
                          == doc.get("custom_sales_status")):
            return
        doc.db_set("custom_first_touch_at", now_datetime(), update_modified=False)
        doc.db_set("custom_first_touch_by", frappe.session.user, update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000],
                         "logistics_portal.stamp_first_touch")


def stamp_stage_timestamps(doc, method=None):
    """Stamp precise stage timestamps as custom_logistics_status advances, so
    time-in-stage and SLA are exact instead of scraped from the Version log.
    No-op if the timestamp custom fields aren't installed yet."""
    # Wrapped so a stamping fault can never break unrelated Sales Order saves
    # (this hook fires on every SO on_update, site-wide).
    try:
        status = doc.get("custom_logistics_status")
        field = STAGE_STAMP.get(status)
        if not field:
            return
        if not frappe.get_meta("Sales Order").has_field(field):
            return
        if not doc.get(field):
            # db_set writes directly (no doc_event re-trigger); update_modified=False
            # keeps it out of the modified-timestamp path.
            doc.db_set(field, now_datetime(), update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.stamp_stage_timestamps")


# ---------------------------------------------------------------------------
# ORDERS BOARD — the operations theater.
# Stages are derived from DOCUMENT SIGNALS (production-verified), not from the
# half-used custom_logistics_status alone:
#   to_pick   Confirmed + no Pick List
#   picking   PL draft exists (submit auto-creates the AWB)
#   prepared  Label Generated (AWB exists, not printed)
#   ready     Label Printed (awaiting manifest)
#   shipped   with carrier — sub-segmented by custom_track_shipment_status
#   delivered Delivered
#   to_return carrier flagged Returned, parcel NOT yet in a Return Shipment
#   returned  DN.custom_return_shipment set (physically received)
# ---------------------------------------------------------------------------
BOARD_WINDOW_DAYS = 90   # active-flow scope
DONE_WINDOW_DAYS = 30    # delivered/returned history scope


def _win(days):
    from frappe.utils import add_days, nowdate
    return add_days(nowdate(), -days)


@frappe.whitelist()
def board(stage="to_pick", track=None, limit=50, q=None, offset=0, city=None, sort=None, dates=None, pick=None, supplier=None):
    """Counts + MAD value per stage, rows for the requested stage, and a city
    facet for filtering. `q` searches order no / customer / AWB."""
    import json as _json

    limit = min(int(limit), 100)
    offset = min(max(int(offset), 0), 5000)
    try:
        # Counts/values/tracks/attention are global (not filter-dependent) and
        # cost several table scans — cache for 60s so tab switches are instant.
        cache = frappe.cache()
        cached = cache.get_value("lp_board_summary")
        if cached:
            summary = _json.loads(cached)
            counts, values = summary["counts"], summary["values"]
            shipped_tracks, attention = summary["tracks"], summary["attention"]
        else:
            counts, values, shipped_tracks, attention = _board_counts()
            # Writes bust this cache; fresh orders can wait a few minutes for
            # COUNTS (rows are always live) — the cold recompute costs ~4s.
            cache.set_value("lp_board_summary", _json.dumps({
                "counts": counts, "values": values,
                "tracks": shipped_tracks, "attention": attention,
            }), expires_in_sec=60)

        facet_key = f"lp_board_cities:{stage}:{track or ''}"
        cached_facet = cache.get_value(facet_key)
        if cached_facet:
            cities = _json.loads(cached_facet)
        else:
            cities = _city_facet(stage, track)
            cache.set_value(facet_key, _json.dumps(cities), expires_in_sec=600)

        # To-Pick splits by locally-pickable stock: Ready / Partial / OOS.
        pick_avail = pick_buckets = pick_names = None
        sup_by_order, sup_facet = {}, None
        if stage == "to_pick":
            pick_avail = _pick_availability()
            pick_buckets = {k: len(pick_avail.get(k) or [])
                            for k in ("ready", "partial", "oos", "local")}
            # City fence: orders held out of the pool until a dispatcher fixes
            # the city — their own chip, so they stop hiding inside "Ready".
            from logistics_portal.api.picking import city_held as _city_held
            city_hold = _city_held(80)
            pick_buckets["city"] = city_hold["n"]
            if pick in ("ready", "partial", "oos", "local"):
                pick_names = pick_avail.get(pick) or []
            elif pick == "city":
                pick_names = [r["so"] for r in city_hold["rows"]]
                # Who owes us the blocked item. The row already names WHAT is
                # missing; without the supplier the dispatcher has to open each
                # order to find out who to call, and cannot see that eleven of
                # them are one phone call. Same facet contract as the city
                # filter, so the two behave identically.
                sup_by_order, sup_facet = _supplier_facet(pick_avail, pick_names)
                supplier = (supplier or "").strip()
                if supplier:
                    pick_names = [n for n in pick_names
                                  if supplier in (sup_by_order.get(n) or [])]

        rows = _board_rows(stage, track, limit, q, offset, city, sort, dates, pick_names=pick_names)
        # Unfiltered views reuse the cached stage count — the mirrored COUNT(*)
        # scan is only worth paying when q/city/dates narrow the set.
        if stage == "attention":
            total = len(rows)
        elif pick_names is not None:
            total = len(pick_names) if not (q or city or dates) \
                else _board_total(stage, track, q, city, dates, pick_names=pick_names)
        elif not q and not city and not dates and not track:
            total = counts.get(stage, len(rows))
        else:
            total = _board_total(stage, track, q, city, dates)
        from frappe.utils import now_datetime
        # A date filter re-scopes the DONE-stage cards to that period (throughput),
        # while the backlog cards stay live. Only pay for it when a filter is set.
        if dates:
            counts = {**counts, **_done_counts(dates)}
        resp = {"counts": counts, "values": values, "shippedTracks": shipped_tracks,
                "attention": attention, "rows": rows, "cities": cities,
                "total": total, "stage": stage, "intakeToday": _intake_today(),
                "serverNow": str(now_datetime())[:16]}
        if pick_buckets is not None:
            resp["pickBuckets"] = pick_buckets
            resp["cityHeld"] = city_hold
            if pick_names is not None and sup_facet is not None:
                resp["suppliers"] = sup_facet
                resp["pickSuppliers"] = {r["no"]: sup_by_order.get(r["no"], [])
                                         for r in rows}
            resp["pickStuck"] = pick_avail.get("stuck", {})
            resp["blocking"] = pick_avail.get("blocking", [])
            resp["rescuable"] = pick_avail.get("rescuable", {})
            if pick in ("partial", "oos", "local"):
                resp["pickMissing"] = {r["no"]: pick_avail["missing"].get(r["no"], []) for r in rows}
        return resp
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.orders.board")
        return {}


def _board_total(stage, track, q=None, city=None, dates=None, pick_names=None):
    """Filtered row count for the stage — powers real pagination."""
    w, dw = _win(BOARD_WINDOW_DAYS), _win(DONE_WINDOW_DAYS)
    addr = """LEFT JOIN `tabAddress` addr
        ON addr.name = COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address)"""
    base = "so.docstatus=1 AND so.custom_sales_status='Confirmed'"
    args = []

    if stage in ("to_pick", "picking"):
        pl_cond = "pl.sales_order IS NULL" if stage == "to_pick" else "pl.docstatus = 0"
        joins = addr + """ LEFT JOIN (SELECT pli.sales_order, MAX(p.docstatus) docstatus
            FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name=pli.parent
            WHERE p.docstatus < 2
            GROUP BY pli.sales_order) pl ON pl.sales_order = so.name"""
        where = f"{base} AND so.custom_logistics_status='Pending' AND {pl_cond} AND so.creation >= %s"
        args = [w]
    elif stage in ("to_return", "returned"):
        # "Returned" on this board means received in a RET batch, so the scan
        # IS the definition -- the order's own status field does not get a vote
        # (it named 64 of the 981 parcels that came back last month).
        from logistics_portal.api.returns import back_in_house_sql
        joins = addr + """ LEFT JOIN (SELECT dni.against_sales_order so_name,
                MAX(d.custom_return_shipment) ret
            FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name=dni.parent
            WHERE d.docstatus=1 AND d.posting_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                       GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name"""
        if stage == "returned":
            where = f"{base} AND so.creation >= %s AND {back_in_house_sql()}"
        else:
            where = (f"{base} AND so.custom_logistics_status='Returned'"
                     f" AND so.creation >= %s AND NOT {back_in_house_sql()}")
        args = [dw]
    else:
        status_map = {"prepared": ["Label Generated", "Picked", "In transit", "Received"],
                      "ready": ["Label Printed"], "shipped": ["Shipped"],
                      "delivered": ["Delivered"]}
        statuses = status_map.get(stage)
        if not statuses:
            return 0
        joins = addr
        ph = ", ".join(["%s"] * len(statuses))
        where = f"{base} AND so.custom_logistics_status IN ({ph}) AND so.creation >= %s"
        args = statuses + [dw if stage == "delivered" else w]
        if stage == "shipped":
            if track == "none":
                where += " AND (so.custom_track_shipment_status IS NULL OR so.custom_track_shipment_status='')"
            elif track:
                where += " AND so.custom_track_shipment_status = %s"
                args.append(track)

    where += _q_cond(q, args)
    where += _city_cond(city, args)
    where += _period_cond(dates, args, _dcol(stage))
    if pick_names is not None and stage == "to_pick":
        if not pick_names:
            return 0
        where += " AND so.name IN (%s)" % ", ".join(["%s"] * len(pick_names))
        args.extend(pick_names)
    try:
        return int(frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabSales Order` so {joins} WHERE {where}",
            tuple(args))[0][0] or 0)
    except Exception:
        return 0


def _city_facet(stage, track, top=14):
    """Top cities (from the linked Address) for the active stage — drives the
    city filter dropdown. to_return/returned share one status-level facet."""
    w, dw = _win(BOARD_WINDOW_DAYS), _win(DONE_WINDOW_DAYS)
    addr = """LEFT JOIN `tabAddress` addr
        ON addr.name = COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address)"""
    base = "so.docstatus=1 AND so.custom_sales_status='Confirmed'"

    if stage in ("to_pick", "picking"):
        pl_cond = "pl.sales_order IS NULL" if stage == "to_pick" else "pl.docstatus = 0"
        joins = addr + """ LEFT JOIN (SELECT pli.sales_order, MAX(p.docstatus) docstatus
            FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name=pli.parent
            WHERE p.docstatus < 2
            GROUP BY pli.sales_order) pl ON pl.sales_order = so.name"""
        where = f"{base} AND so.custom_logistics_status='Pending' AND {pl_cond} AND so.creation >= %s"
        args = [w]
    else:
        status = {"prepared": "Label Generated", "ready": "Label Printed",
                  "shipped": "Shipped", "delivered": "Delivered",
                  "to_return": "Returned", "returned": "Returned"}.get(stage)
        if not status:
            return []
        joins = addr
        where = f"{base} AND so.custom_logistics_status=%s AND so.creation >= %s"
        args = [status, dw if stage in ("delivered", "to_return", "returned") else w]
        if stage == "shipped" and track and track != "none":
            where += " AND so.custom_track_shipment_status = %s"
            args.append(track)

    try:
        rows = frappe.db.sql(f"""
            SELECT COALESCE(NULLIF(so.custom_shipping_city,''), addr.city) c, COUNT(*) n
            FROM `tabSales Order` so {joins}
            WHERE {where}
            GROUP BY c HAVING c IS NOT NULL AND c != '' AND CHAR_LENGTH(c) <= 28
            ORDER BY n DESC LIMIT {int(top)}""", tuple(args), as_dict=True)
        return [{"city": r.c, "count": int(r.n)} for r in rows]
    except Exception:
        return []


def _board_counts():
    w, dw = _win(BOARD_WINDOW_DAYS), _win(DONE_WINDOW_DAYS)

    # Status-level counts + MAD among Confirmed orders (one cheap grouped pass).
    strows = frappe.db.sql(
        """SELECT custom_logistics_status s, COUNT(*) c, ROUND(SUM(grand_total)) v
           FROM `tabSales Order`
           WHERE docstatus=1 AND custom_sales_status='Confirmed' AND creation >= %s
           GROUP BY custom_logistics_status""", (w,), as_dict=True)
    st = {r.s: int(r.c) for r in strows}
    sv = {r.s: float(r.v or 0) for r in strows}

    # Split 'Pending' into to_pick / picking via Pick List existence.
    pend = frappe.db.sql(
        """SELECT
             SUM(CASE WHEN pl.sales_order IS NULL THEN 1 ELSE 0 END) no_pl,
             SUM(CASE WHEN pl.sales_order IS NULL THEN so.grand_total ELSE 0 END) no_pl_v,
             SUM(CASE WHEN pl.docstatus = 0 THEN 1 ELSE 0 END) pl_draft,
             SUM(CASE WHEN pl.docstatus = 0 THEN so.grand_total ELSE 0 END) pl_draft_v
           FROM `tabSales Order` so
           LEFT JOIN (SELECT pli.sales_order, MAX(p.docstatus) docstatus
                      FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name=pli.parent
                      WHERE p.docstatus < 2 GROUP BY pli.sales_order) pl
             ON pl.sales_order = so.name
           WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
             AND so.custom_logistics_status='Pending' AND so.creation >= %s""",
        (w,), as_dict=True)[0]

    # Shipped sub-segmentation by carrier tracking.
    tracks = {r.t or "none": int(r.c) for r in frappe.db.sql(
        """SELECT custom_track_shipment_status t, COUNT(*) c FROM `tabSales Order`
           WHERE docstatus=1 AND custom_sales_status='Confirmed'
             AND custom_logistics_status='Shipped' AND creation >= %s
           GROUP BY custom_track_shipment_status""", (w,), as_dict=True)}

    # Returned split: physically received (RET linked) vs still with carrier.
    ret = frappe.db.sql(
        """SELECT
             SUM(bk.so_name IS NOT NULL) received,
             COUNT(*) total
           FROM `tabSales Order` so
           """ + _back_in_house_join() + """
           WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
             AND (so.custom_logistics_status='Returned' OR bk.so_name IS NOT NULL)
             AND so.creation >= %s""",
        (dw,), as_dict=True)[0]
    received = int(ret.received or 0)

    # How many To Pick orders already missed today's 14:00 same-day cutoff.
    from frappe.utils import now_datetime, nowdate
    _now = now_datetime()
    from logistics_portal.api.settings import get_ops
    _cut = get_ops("cutoff")
    cutoff_dt = f"{nowdate()} {_cut}:00" if str(_now)[11:16] >= _cut else f"{nowdate()} 00:00:00"
    late = frappe.db.sql(
        """SELECT COUNT(*) FROM `tabSales Order` so
           LEFT JOIN (SELECT DISTINCT pli.sales_order FROM `tabPick List Item` pli) pl
             ON pl.sales_order = so.name
           WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
             AND so.custom_logistics_status='Pending' AND pl.sales_order IS NULL
             AND so.creation >= %s AND so.creation < %s""",
        (w, cutoff_dt))[0][0]

    counts = {
        "to_pick": int(pend.no_pl or 0),
        "to_pick_late": int(late or 0),
        "picking": int(pend.pl_draft or 0),
        "prepared": st.get("Label Generated", 0) + st.get("Picked", 0)
                    + st.get("In transit", 0) + st.get("Received", 0),
        "ready": st.get("Label Printed", 0),
        "shipped": st.get("Shipped", 0),
        "delivered": frappe.db.count("Sales Order", {
            "docstatus": 1, "custom_sales_status": "Confirmed",
            "custom_logistics_status": "Delivered", "creation": [">=", dw]}),
        "to_return": max(0, int(ret.total or 0) - received),
        "returned": received,
    }
    # MAD sitting in each ACTIVE stage (money-at-stage; done stages omitted).
    values = {
        "to_pick": round(float(pend.no_pl_v or 0)),
        "picking": round(float(pend.pl_draft_v or 0)),
        "prepared": round(sv.get("Label Generated", 0)),
        "ready": round(sv.get("Label Printed", 0)),
        "shipped": round(sv.get("Shipped", 0)),
    }

    # Attention: operational faults, not stages.
    attention = {
        # confirmed→cancelled after a PL existed (goods must go back to shelf)
        "cancelled_midflow": int(frappe.db.sql(
            f"""SELECT COUNT(DISTINCT so.name) FROM `tabSales Order` so
               JOIN `tabPick List Item` pli ON pli.sales_order = so.name
               WHERE so.docstatus=1 AND so.custom_sales_status='Cancelled'
                 AND so.custom_logistics_status NOT IN ('Delivered','Returned')
                 AND NOT {_back_in_house()}
                 AND so.creation >= %s""", (dw,))[0][0] or 0),
        # PL submitted but the AWB automation didn't fire
        "no_awb": int(frappe.db.sql(
            """SELECT COUNT(DISTINCT so.name) FROM `tabSales Order` so
               JOIN `tabPick List Item` pli ON pli.sales_order = so.name
               JOIN `tabPick List` p ON p.name = pli.parent AND p.docstatus = 1
               WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
                 AND so.custom_logistics_status='Pending'
                 AND (so.custom_awb IS NULL OR so.custom_awb='')
                 AND so.creation >= %s""", (dw,))[0][0] or 0),
        # carrier says Delivered but the order status is stuck at Shipped
        "sync_lag": frappe.db.count("Sales Order", {
            "docstatus": 1, "custom_sales_status": "Confirmed",
            "custom_logistics_status": "Shipped",
            "custom_track_shipment_status": "Delivered", "creation": [">=", _win(BOARD_WINDOW_DAYS)]}),
    }
    return counts, values, tracks, attention


_SO_FIELDS = """so.name, so.customer_name, so.grand_total, so.custom_channel,
    so.custom_items_count, so.custom_awb, so.custom_label_url, so.custom_shipping_city,
    so.custom_track_shipment_status, so.creation, so.modified,
    COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
    LEFT(so.custom_items_description, 160) AS items_desc,
    so.custom_logistics_status AS lstatus,
    COALESCE(NULLIF(so.custom_shipping_city,''), addr.city) AS city_val"""


def _so_fields():
    """_SO_FIELDS plus the urgent stamp. Lazy, because _urgent_col reads the
    doctype meta and this module is imported before the site is up. Every board
    stage selects through here, so the badge reaches every list at once rather
    than being wired screen by screen."""
    return _SO_FIELDS + ",\n    " + _urgent_col() + " AS urgent_at"


def _q_cond(q, args):
    """Search filter over order no / customer / AWB (parameterized LIKE)."""
    if not q:
        return ""
    like = f"%{q.strip()}%"
    args.extend([like, like, like])
    return " AND (so.name LIKE %s OR so.customer_name LIKE %s OR so.custom_awb LIKE %s)"


_SORTS = {
    "placed_desc": "so.creation DESC", "placed_asc": "so.creation ASC",
    "value_desc": "so.grand_total DESC", "value_asc": "so.grand_total ASC",
    "age_desc": "so.modified ASC", "age_asc": "so.modified DESC",
}


def _order_by(sort, default):
    return _SORTS.get(sort or "", default)


DONE_STAGES = ("shipped", "delivered", "returned")  # events: scoped by period
_DONE_STATUS = {"shipped": "Shipped", "delivered": "Delivered", "returned": "Returned"}


def _period_bounds(dates):
    """(start_date, end_date_inclusive|None) for a filter token, or None.
    today/yesterday/this_week/this_month/7d/30d — anchored to the server date."""
    from frappe.utils import nowdate, add_days, get_first_day, getdate
    if not dates:
        return None
    today = getdate(nowdate())
    if dates == "today":      return (today, today)
    if dates == "yesterday":  y = add_days(today, -1); return (y, y)
    if dates == "this_week":  return (add_days(today, -today.weekday()), today)  # Mon-start
    if dates == "this_month": return (get_first_day(today), today)
    if dates in ("7d", "30d"): return (add_days(today, -int(dates[:-1])), today)
    return None


def _period_cond(dates, args, col="so.creation"):
    """Date-range filter on `col`. Backlog stages scope by creation (when it
    arrived); done stages scope by modified (when it reached the stage)."""
    b = _period_bounds(dates)
    if not b:
        return ""
    start, end = b
    args.append(str(start))
    cond = f" AND DATE({col}) >= %s"
    if end is not None:
        args.append(str(end)); cond += f" AND DATE({col}) <= %s"
    return cond


def _dcol(stage):
    return "so.modified" if stage in DONE_STAGES + ("to_return",) else "so.creation"


def _date_cond(dates, args):  # back-compat shim (creation-scoped)
    return _period_cond(dates, args, "so.creation")


def _done_counts(dates):
    """Throughput counts for the DONE stages within a period (by so.modified =
    when the order reached that stage). Only shipped/delivered/returned are
    events; to_return stays a live in-flight state."""
    out = {}
    for stage in DONE_STAGES:
        args = []
        pc = _period_cond(dates, args, "so.modified")
        if not pc:
            return {}
        out[stage] = int(frappe.db.sql(
            f"""SELECT COUNT(*) FROM `tabSales Order` so
                WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
                  AND so.custom_logistics_status=%s{pc}""",
            tuple([_DONE_STATUS[stage]] + args))[0][0] or 0)
    return out


def _intake_today():
    """Confirmed orders that arrived today. Sargable range (DATE(creation)=%s
    can't use the creation index → full 240k scan) + 60s cache, because the
    Orders board polls this every 120s per open client all day."""
    import json as _json
    cache = frappe.cache()
    cached = cache.get_value("lp_intake_today")
    if cached is not None:
        try:
            return int(_json.loads(cached))
        except Exception:
            pass
    try:
        n = int(frappe.db.sql(
            """SELECT COUNT(*) FROM `tabSales Order`
               WHERE docstatus=1 AND custom_sales_status='Confirmed'
                 AND creation >= CURDATE()""")[0][0] or 0)
        cache.set_value("lp_intake_today", _json.dumps(n), expires_in_sec=60)
        return n
    except Exception:
        return 0


def _city_cond(city, args):
    if not city:
        return ""
    args.append(city)
    return " AND COALESCE(NULLIF(so.custom_shipping_city,''), addr.city) = %s"


def _row(r, **extra):
    from frappe.utils import time_diff_in_seconds, now_datetime
    age = max(0, int(time_diff_in_seconds(now_datetime(), r.modified) // 60))
    return dict({
        "no": r.name, "customer": r.customer_name, "total": r.grand_total or 0,
        "channel": (r.custom_channel or "").lower(),
        "items": r.custom_items_count or 1,
        # >28 chars means the Address "city" field holds a full address line — not a city.
        "city": (r.get("city_val") or "") if len(r.get("city_val") or "") <= 28 else "",
        "status": r.get("lstatus") or "",
        "phone": r.get("phone") or "",
        "awb": r.custom_awb or "", "labelUrl": r.get("custom_label_url") or "",
        "track": r.custom_track_shipment_status or "", "ageMins": age,
        "created": str(r.creation)[:16],
        "itemsDesc": (r.get("items_desc") or "").strip(),
        "urgent": bool(r.get("urgent_at")),
    }, **extra)


# Locally-pickable stock: "- JM" warehouses with available qty, per the
# configurable pickable-warehouse policy (structural families always excluded;
# Return/Receiving/etc. zones toggled by a manager in Settings). Values are %s
# params so this splices safely into queries that also carry %s args.
_EMPTY_AVAIL = {"ready": [], "partial": [], "oos": [], "local": [],
                "missing": {}, "missByOrder": {},
                "blocking": [], "localSupply": {}, "stuck": {"oos": 0, "partial": 0, "local": 0}}


def _pick_availability():
    """Stock split of the current To-Pick pool, cached 120s. Also aggregates the
    SKUs blocking the most orders (a restock worklist) and the MAD stuck out of
    stock. {ready, partial, oos, missing, blocking:[{sku,name,orders,mad,age}],
    stuck:{oos, partial}}."""
    import json as _json
    from frappe.utils import date_diff, nowdate
    cache = frappe.cache()
    cached = cache.get_value("lp_pick_avail")
    if cached:
        return _json.loads(cached)
    w = _win(BOARD_WINDOW_DAYS)
    try:
        rows = frappe.db.sql("""
            SELECT so.name AS so, so.grand_total AS val, so.creation AS created,
                   COALESCE(pk.item_code, soi.item_code) AS code,
                   COALESCE(NULLIF(pk.item_name,''), NULLIF(soi.item_name,''), soi.item_code) AS item_name,
                   SUM(GREATEST(soi.qty - soi.delivered_qty, 0)
                       * COALESCE(pk.qty / NULLIF(soi.qty, 0), 1)) AS need
            FROM `tabSales Order` so
            JOIN `tabSales Order Item` soi ON soi.parent = so.name
            LEFT JOIN `tabPacked Item` pk ON pk.parent = so.name AND pk.parent_detail_docname = soi.name
            LEFT JOIN (SELECT pli.sales_order FROM `tabPick List Item` pli
                       JOIN `tabPick List` p ON p.name=pli.parent
                       WHERE p.docstatus < 2 GROUP BY pli.sales_order) pl ON pl.sales_order = so.name
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.sales_order IS NULL
              AND so.creation >= %s
            GROUP BY so.name, code, item_name, val, created""",
            (w,), as_dict=True)
        # The SAME availability the create runs — audited 2026-08-27, when raw
        # Bin math called 50 orders ready and only 12 could be picked, and again
        # 2026-09-09, when five callers had each grown their own arithmetic on
        # top of it and disagreed. There is now one definition and every screen
        # asks it: picking.availability().
        from logistics_portal.api.picking import availability
        codes = {r.code for r in rows}
        totals, sre, _free_for = availability(codes)

    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal._pick_availability")
        return dict(_EMPTY_AVAIL)

    today = nowdate()
    per = {}
    for r in rows:
        d = per.setdefault(r.so, {"n": 0, "enough": 0, "some": 0, "missing": [],
                                  "miss_codes": [], "lines": [],
                                  "val": float(r.val or 0), "created": r.created})
        d["n"] += 1
        d["lines"].append((r.code, float(r.need or 0), r.item_name))
        # "Some" is about the ITEM, not about this order's turn: it decides
        # OOS ("nothing in stock") vs Partial, and that answer should not
        # change because another order was served first.
        if _free_for(r.so, r.code) > 0:
            d["some"] += 1

    # One unit, one order. The old test asked each order on its own whether the
    # pool covered it and never spent anything, so the same last piece was
    # promised to everybody holding it — and worse, an order's OWN reservation
    # was added on top of a pool that had already been zeroed for a reason that
    # has nothing to do with reservations. Measured 2026-09-09 on the live
    # pool: 81 orders called Ready, of which 28 could not be picked and 9 had a
    # line with no pickable bin anywhere. Three different causes behind those
    # zeros — an open draft pick list already holding the piece (PL-55772 held
    # all 6 of one item), the batch ledger answering nothing for a shelf the
    # Bin says has two, and stock sitting only in warehouses the engine
    # refuses — and the old code's comment assumed away all three: "a genuinely
    # empty item has no reservation to hand back either". It is not empty. It
    # is spoken for, and the reservation is still on the books.
    #
    # So spend from one ceiling, the way create does: _available_totals is
    # already "what the create can actually take", and every order draws from
    # it in turn. A reservation no longer conjures a unit; it buys its holder a
    # place at the front of the queue for one that exists.
    ceiling = {}
    for code in {r.code for r in rows}:
        ceiling[code] = max(0.0, float(totals.get(code, 0)))

    def _has_own(so_name):
        for code, _need, _nm in per[so_name]["lines"]:
            if sre.get((so_name, code), 0) > 0:
                return 0            # sorts first
        return 1

    for name in sorted(per, key=lambda s: (_has_own(s), str(per[s]["created"] or ""))):
        d = per[name]
        short_line = None
        for code, need, _nm in d["lines"]:
            if ceiling.get(code, 0) < need:
                short_line = code
                break
        if short_line is None:
            d["enough"] = d["n"]
            for code, need, _nm in d["lines"]:
                ceiling[code] = ceiling.get(code, 0) - need
        else:
            # Name every line this order cannot have, not just the first — the
            # restock worklist is built from these.
            for code, need, nm in d["lines"]:
                if ceiling.get(code, 0) < need:
                    if len(d["missing"]) < 6:
                        d["missing"].append(nm)
                    d["miss_codes"].append((code, nm))

    # There was briefly a "cooling" bucket here, mirroring _pick_gate's 24-hour
    # cool-down on short-picked ORDERS. Both are gone: the report is about a
    # shelf, not an order, so it is now recorded against (item, warehouse) and
    # subtracted inside _available_totals. An order whose only stock was on
    # that shelf therefore lands in Partial or Out of stock by the ordinary
    # arithmetic, with the right item named — and one whose item sits in
    # another bin stays ready, which the order-level cool-down got wrong.
    ready, partial, oos, local, missing = [], [], [], [], {}
    block = {}  # code -> {name, orders:set, mad, oldest}
    miss_by_order = {}  # order -> [(missing item_code, item_name)] for SKU-rescue
    stuck_oos = stuck_partial = 0.0
    for name, d in per.items():
        if d["enough"] >= d["n"]:
            ready.append(name); continue
        blocked = d["some"] == 0   # nothing at all in stock (vs short = some)
        (oos if blocked else partial).append(name)
        missing[name] = d["missing"]
        miss_by_order[name] = d["miss_codes"]
        if blocked:
            stuck_oos += d["val"]
        else:
            stuck_partial += d["val"]
        try:
            age = max(0, date_diff(today, str(d["created"])[:10]))
        except Exception:
            age = 0
        for code, iname in d["miss_codes"]:
            b = block.setdefault(code, {"sku": code, "name": iname, "orders": set(),
                                        "mad": 0.0, "age": 0})
            if name not in b["orders"]:
                b["orders"].add(name); b["mad"] += d["val"]
            b["age"] = max(b["age"], age)

    blocking = sorted(
        ({"sku": b["sku"], "name": b["name"], "orders": len(b["orders"]),
          "mad": round(b["mad"]), "age": b["age"]} for b in block.values()),
        key=lambda x: (-x["orders"], -x["mad"]))[:12]

    # Khadija (2026-08-27): the floor must tell OUR out-of-stock apart from
    # "the vendor hasn't delivered yet". Per blocking SKU: its supplier, and
    # the quantity still pending on OPEN Purchase Orders (ordered - received).
    if blocking:
        codes = tuple(b["sku"] for b in blocking)
        ph = ",".join(["%s"] * len(codes))
        # Stock sleeping in the RESERVE zones (SLOW/STOCK feed the fast wall):
        # "out of stock" with 3k in SLOW ZONE is a replenishment job, not a
        # purchase — the chip sends the floor to Move Stock, not to a vendor.
        reserve = {r[0]: float(r[1] or 0) for r in frappe.db.sql(
            f"""SELECT item_code, SUM(actual_qty) FROM `tabBin`
                WHERE item_code IN ({ph})
                  AND warehouse IN ('SLOW ZONE - JM', 'STOCK ZONE  - JM')
                  AND actual_qty > 0 GROUP BY item_code""", codes)}
        sup = {r[0]: r[1] for r in frappe.db.sql(
            f"""SELECT name, COALESCE(NULLIF(default_supplier,''),'')
                FROM `tabItem` WHERE name IN ({ph})""", codes)}
        incoming = {r[0]: float(r[1] or 0) for r in frappe.db.sql(
            f"""SELECT poi.item_code, SUM(poi.qty - poi.received_qty)
                FROM `tabPurchase Order Item` poi
                JOIN `tabPurchase Order` po ON po.name = poi.parent
                WHERE po.docstatus = 1 AND po.status NOT IN ('Closed', 'Completed')
                  AND poi.item_code IN ({ph})
                  AND poi.qty > poi.received_qty
                GROUP BY poi.item_code""", codes)}
        # Which of these are a purchase problem rather than a warehouse one.
        # The list is capped at 12 rows: when supplier-owed SKUs take those
        # slots, the restock work the floor can actually do today is pushed
        # off the screen. The flag lets the panel separate the two.
        local_grp = {r[0] for r in frappe.db.sql(
            f"""SELECT i.name FROM `tabItem` i
                JOIN `tabSupplier` s ON s.name = i.default_supplier
                WHERE i.name IN ({ph}) AND s.supplier_group = %s""",
            codes + (LOCAL_SUPPLIER_GROUP,))}
        for b in blocking:
            b["supplier"] = sup.get(b["sku"], "")
            b["incoming"] = round(incoming.get(b["sku"], 0))
            b["reserve"] = round(reserve.get(b["sku"], 0))
            b["local"] = b["sku"] in local_grp

    rescuable = _sku_rescue(miss_by_order)

    # ── "Out of stock" was one word over four different jobs ─────────────
    # Measured 2026-09-01 on the live OOS pile: only 4 of 35 orders had
    # nothing coming at all. 14 were waiting on a local supplier with an open
    # purchase order, 6 were waiting on a local supplier NOBODY HAD ORDERED
    # FROM YET, and 11 were imports. Chasing a local supplier is a phone call
    # today; an import is a different horizon — so imports stay in Out of
    # stock (Ahmed, 2026-09-01) and only the local ones move.
    #
    # An order moves ONLY if EVERY blocking item is local: chasing one
    # supplier cannot unblock an order that is also short an imported item,
    # and putting it here would promise a fix the call can't deliver.
    local_supply = _local_supply({c for lst in miss_by_order.values() for (c, _n) in lst})
    stuck_local = 0.0
    if local_supply:
        # BOTH buckets, not just Out of stock. An order with three lines in
        # stock and one on a supplier's van lands in PARTIAL, and the first
        # cut of this split left it there — 10 of the 16 partial orders were
        # purely a local-supplier wait, invisible to the very tab built for
        # them (found 2026-09-01 from a Maison good and well item). Nothing
        # on this board can be picked until it is complete, so a partial
        # order waiting on a supplier is waiting exactly as hard as an
        # empty one.
        def _carve(names, drop_from):
            keep = []
            for name in names:
                codes = [c for (c, _n) in miss_by_order.get(name, [])]
                if codes and all(c in local_supply for c in codes):
                    local.append(name)
                    drop_from.append(per[name]["val"])
                else:
                    keep.append(name)
            return keep

        moved_oos, moved_partial = [], []
        oos = _carve(oos, moved_oos)
        partial = _carve(partial, moved_partial)
        # The money moves with the order: leaving it behind made the "stuck"
        # chips count parcels that are not short at all, they are waiting on
        # a van.
        stuck_local = sum(moved_oos) + sum(moved_partial)
        stuck_oos -= sum(moved_oos)
        stuck_partial -= sum(moved_partial)

    out = {"ready": ready, "partial": partial, "oos": oos, "local": local,
           "missing": missing, "blocking": blocking, "rescuable": rescuable,
           "localSupply": local_supply,
           # Per-order blocking (code, name) pairs. Every blocked order, not
           # just the local ones: the supplier column and filter on the main
           # table are built from this, and they cover Partial and Out of
           # stock too — those rows have a supplier behind them as well.
           "missByOrder": {n: miss_by_order.get(n, [])
                           for n in (local + oos + partial)},
           "stuck": {"oos": round(max(0.0, stuck_oos)),
                     "partial": round(max(0.0, stuck_partial)),
                     "local": round(stuck_local)}}
    cache.set_value("lp_pick_avail", _json.dumps(out), expires_in_sec=120)
    return out


@frappe.whitelist()
def blocking_orders(sku, limit=60):
    """The To-Pick orders held up by one out-of-stock item — powers the
    'N orders' click on the restock worklist. `sku` is the item_code.
    Returns [{no, customer, total, ageMins, city}] newest first."""
    from frappe.utils import time_diff_in_seconds, now_datetime
    sku = (sku or "").strip()
    if not sku:
        return []
    w = _win(BOARD_WINDOW_DAYS)
    try:
        rows = frappe.db.sql(
            """SELECT so.name AS no, so.customer_name AS customer,
                      so.grand_total AS total, so.creation,
                      COALESCE(NULLIF(so.custom_shipping_city,''), addr.city) AS city
               FROM `tabSales Order` so
               JOIN `tabSales Order Item` soi ON soi.parent = so.name
               LEFT JOIN `tabAddress` addr
                 ON addr.name = COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address)
               LEFT JOIN (SELECT pli.sales_order FROM `tabPick List Item` pli
                          JOIN `tabPick List` p ON p.name=pli.parent
                          WHERE p.docstatus < 2 GROUP BY pli.sales_order) pl ON pl.sales_order = so.name
               WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
                 AND so.custom_logistics_status='Pending' AND pl.sales_order IS NULL
                 AND so.creation >= %s AND soi.item_code = %s
               GROUP BY so.name
               ORDER BY so.creation DESC
               LIMIT %s""",
            (w, sku, min(int(limit), 200)), as_dict=True)
        now = now_datetime()
        out = []
        for r in rows:
            try:
                age = max(0, int(time_diff_in_seconds(now, r.creation) // 60))
            except Exception:
                age = 0
            out.append({"no": r.no, "customer": r.customer or "",
                        "total": float(r.total or 0), "ageMins": age,
                        "city": (r.city or "") if len(r.city or "") <= 28 else ""})
        return out
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.blocking_orders")
        return []


# The supplier group that means "a van, not a container". Ahmed 2026-09-01.
# NOT Supplier.country: three of the local suppliers behind today's blockers
# (GHADA FASHION, First mondial ingenierie, Maison good and well) carry
# country = Turkey while sitting in this group. The group is the truth.
LOCAL_SUPPLIER_GROUP = "Morocco Local Suppliers"

# The promise, in days, for a local supplier to deliver. Grounded in 2,467
# receipts over 120 days: the real median is 2 days, p75 is 7, p90 is 24.
# Ahmed set the promise at 3 — one day of slack over the median, well inside
# the p75 the floor actually lives with.
LOCAL_PROMISE_DAYS = 3


def _supplier_facet(avail, names):
    """(order -> [suppliers], facet rows) for the blocked orders on screen.

    Every supplier, not only the local ones: the dispatcher filtering this
    table wants "show me everything waiting on GHADA FASHION" whether that
    supplier is down the road or overseas. The LOCAL flag rides along so the
    dropdown can say which is which without a second query.

    An order can be blocked by items from more than one supplier, so the map
    is a list and the facet counts an order once per supplier it is waiting
    on — the numbers in the dropdown add up to more than the row count when
    orders straddle two suppliers, which is the truth, not a bug.
    """
    miss = avail.get("missByOrder") or {}
    codes = {c for n in names for (c, _n) in (miss.get(n) or [])}
    if not codes:
        return {}, []
    sup, local = {}, set()
    for r in frappe.db.sql(
            """SELECT i.name, i.default_supplier, COALESCE(s.supplier_group,'') grp
               FROM `tabItem` i
               LEFT JOIN `tabSupplier` s ON s.name = i.default_supplier
               WHERE i.name IN %s AND COALESCE(i.default_supplier,'') != ''""",
            (tuple(codes),), as_dict=True):
        sup[r.name] = r.default_supplier
        if r.grp == LOCAL_SUPPLIER_GROUP:
            local.add(r.default_supplier)

    by_order, counts = {}, {}
    for n in names:
        seen = []
        for (c, _iname) in (miss.get(n) or []):
            nm = sup.get(c)
            if nm and nm not in seen:
                seen.append(nm)
        if seen:
            by_order[n] = seen
            for nm in seen:
                counts[nm] = counts.get(nm, 0) + 1
    facet = sorted(
        ({"supplier": nm, "orders": k, "local": nm in local}
         for nm, k in counts.items()),
        key=lambda x: (-x["orders"], x["supplier"].lower()))
    return by_order, facet


def _local_supply(codes):
    """item_code → what a LOCAL supplier owes us on it.

    {supplier, po, ordered (qty still pending), due (promised date), poDate}
    for every blocking SKU whose default supplier is in the local group. An
    item with no open purchase order is still returned — with po = "" — because
    that is the sharpest finding of all: nobody has ordered it, so it is not
    "on the way", it is not coming. That case reads as a failure, not a wait.
    """
    codes = [c for c in (codes or []) if c]
    if not codes:
        return {}
    out = {}
    for r in frappe.db.sql(
            """SELECT i.name, i.default_supplier
               FROM `tabItem` i
               JOIN `tabSupplier` s ON s.name = i.default_supplier
               WHERE i.name IN %s AND s.supplier_group = %s""",
            (tuple(codes), LOCAL_SUPPLIER_GROUP), as_dict=True):
        out[r.name] = {"supplier": r.default_supplier, "po": "", "ordered": 0,
                       "due": "", "poDate": ""}
    if not out:
        return {}
    for r in frappe.db.sql(
            """SELECT poi.item_code, MIN(po.name) po,
                      SUM(poi.qty - poi.received_qty) pending,
                      MIN(poi.schedule_date) due, MIN(po.transaction_date) placed
               FROM `tabPurchase Order Item` poi
               JOIN `tabPurchase Order` po ON po.name = poi.parent
               WHERE po.docstatus = 1 AND po.status NOT IN ('Closed', 'Completed')
                 AND poi.item_code IN %s AND poi.qty > poi.received_qty
               GROUP BY poi.item_code""", (tuple(out),), as_dict=True):
        e = out.get(r.item_code)
        if e:
            e.update({"po": r.po or "", "ordered": round(float(r.pending or 0)),
                      "due": str(r.due or "")[:10], "poDate": str(r.placed or "")[:10]})
    return out


def _local_state(entry):
    """Where one blocked order stands against the promise.

    'noPO'  nobody ordered it — the order cannot arrive, ever, until someone
            raises a purchase order. Worst state, and invisible until now.
    'late'  past the supplier's own promised date (or past our 3-day promise
            when the PO carries no date).
    'due'   the promise lands today.
    'otw'   inside the promise.
    """
    if not entry or not entry.get("po"):
        return "noPO", None, ""
    from frappe.utils import date_diff, nowdate, add_days
    # The PO's schedule_date is NOT a supplier promise here. Measured over 120
    # days of local purchase orders: 2,462 of 2,553 lines carry a schedule_date
    # EQUAL to the day the PO was raised — it is a copy of the order date, not
    # a delivery commitment. Trusting it would mark every order late the moment
    # it was created. So the promise is PO date + 3, and schedule_date is used
    # only on the rare line where somebody actually set a later date.
    # One try around the whole date arithmetic: add_days raises on a malformed
    # value too, and it sits on the board's critical path — a single bad date
    # must not take the screen down.
    try:
        placed = entry.get("poDate") or nowdate()
        promised = add_days(placed, LOCAL_PROMISE_DAYS)
        due = entry.get("due") or ""
        if not due or str(due)[:10] <= str(placed)[:10]:
            due = promised
        due = str(due)[:10]
        over = date_diff(nowdate(), due)
    except Exception:
        return "otw", None, ""
    if over > 0:
        return "late", over, due
    return ("due" if over == 0 else "otw"), over, due


@frappe.whitelist()
def local_supply_board():
    """Whitelisted wrapper — the gate lives here, the data below."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Not authorized.", frappe.PermissionError)
    return _local_board_data()


def _local_board_data():
    """The local-supplier queue, grouped BY SUPPLIER.

    Grouped that way on purpose: the action is one phone call covering five
    orders, not five calls. A per-order list makes the floor dial the same
    supplier five times and reads as five problems when it is one.

    Sorted so the thing that cannot fix itself comes first — orders with no
    purchase order at all, then late, then on the way.
    """
    avail = _pick_availability()
    names = avail.get("local") or []
    supply = avail.get("localSupply") or {}
    if not names:
        return {"suppliers": [], "orders": 0, "value": 0,
                "promiseDays": LOCAL_PROMISE_DAYS}

    meta = {r.name: r for r in frappe.db.sql(
        """SELECT name, customer_name, grand_total,
                  DATEDIFF(CURDATE(), DATE(creation)) age
           FROM `tabSales Order` WHERE name IN %s""", (tuple(names),), as_dict=True)}

    groups, total_val = {}, 0.0
    for name in names:
        m = meta.get(name)
        if not m:
            continue
        total_val += float(m.grand_total or 0)
        for code, iname in (avail.get("missByOrder") or {}).get(name, []):
            e = supply.get(code)
            if not e:
                continue
            state, over, promised = _local_state(e)
            g = groups.setdefault(e["supplier"], {
                "supplier": e["supplier"], "orders": [], "value": 0.0,
                "noPO": 0, "late": 0, "otw": 0, "oldest": 0, "items": {},
                "seen": set()})
            if name not in g["seen"]:
                g["seen"].add(name)
                g["orders"].append({
                    "order": name, "customer": m.customer_name or "",
                    "value": round(float(m.grand_total or 0)),
                    "age": int(m.age or 0), "state": state,
                    "overdueBy": over if state == "late" else None,
                    "item": iname or code, "itemCode": code,
                    "po": e.get("po") or "",
                    # The date we judge against, not the PO's own field.
                    "due": promised,
                    "ordered": e.get("ordered") or 0,
                })
                g["value"] += float(m.grand_total or 0)
                g["oldest"] = max(g["oldest"], int(m.age or 0))
                g[{"noPO": "noPO", "late": "late"}.get(state, "otw")] += 1
            g["items"][code] = iname or code

    out = []
    for g in groups.values():
        g["value"] = round(g["value"])
        g["skus"] = len(g.pop("items"))
        g.pop("seen", None)
        g["orders"].sort(key=lambda o: ({"noPO": 0, "late": 1, "due": 2, "otw": 3}
                                        .get(o["state"], 9), -o["age"]))
        out.append(g)
    # Worst first: a supplier nobody has ordered from outranks a late one.
    out.sort(key=lambda g: (-g["noPO"], -g["late"], -g["oldest"]))
    return {"suppliers": out, "orders": len(names), "value": round(total_val),
            "promiseDays": LOCAL_PROMISE_DAYS,
            "noPO": sum(g["noPO"] for g in out),
            "late": sum(g["late"] for g in out)}


def local_supply_alerts():
    """Scheduled: one alert per SUPPLIER, once a day.

    Per-order alerts were never on the table — a supplier holding six orders
    would fire six notifications for one phone call, and a feed like that is
    read once and muted forever. One line per supplier, naming what is wrong,
    is something a dispatcher can act on.

    Two things are worth waking someone for: an order nobody has raised a
    purchase order for (it is not late, it is not coming), and one past the
    supplier's promise. Everything inside the promise stays silent.
    """
    try:
        board = _local_board_data()
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "logistics_portal.orders.local_supply_alerts")
        return
    from logistics_portal.api.audit import _emit
    today = frappe.utils.nowdate()
    for g in board.get("suppliers") or []:
        if not (g["noPO"] or g["late"]):
            continue
        bits = []
        if g["noPO"]:
            bits.append(f"{g['noPO']} with no purchase order raised")
        if g["late"]:
            bits.append(f"{g['late']} past the {LOCAL_PROMISE_DAYS}-day promise")
        _emit({
            "severity": "critical" if g["noPO"] else "warning",
            # The date is in the title so the dedup key rolls over daily: the
            # same supplier can raise the same alert tomorrow, not every tick.
            "title": f"{g['supplier']} — {' · '.join(bits)} ({today})",
            "detail": (f"{len(g['orders'])} order(s), {g['value']} MAD, oldest "
                       f"{g['oldest']} days. Local supplier queue."),
            "audience": "manager",
        })


def _sku_rescue(miss_by_order):
    """False-OOS finder: for orders stuck out of stock, spot missing items whose
    SKU (custom_sku) has a NET-positive sibling item_code — i.e. the product IS
    in the building under a different code. Returns
    {order: {sku, missCode, code, net}} for the first rescuable missing line."""
    # NB: [*set] not list(set) — `def list(...)` below shadows the builtin
    # module-wide, which silently invoked the whitelisted endpoint here and
    # killed this whole feature since day one.
    codes = [*{c for lst in miss_by_order.values() for (c, _n) in lst}]
    if not codes:
        return {}
    try:
        cph = ", ".join(["%s"] * len(codes))
        code2sku = {}
        for r in frappe.db.sql(
            f"SELECT name, custom_sku FROM `tabItem` WHERE name IN ({cph}) "
            f"AND COALESCE(custom_sku,'') != ''", tuple(codes), as_dict=True):
            code2sku[r.name] = r.custom_sku
        skus = [*{s for s in code2sku.values()}]
        if not skus:
            return {}
        # custom_sku is used at two granularities: variant-level SKUs (encode the
        # size/colour, e.g. JST0672-NavyBlue-L/XL) where siblings ARE the same
        # sellable unit — safe to rescue; and bare style-level SKUs (e.g. SS10019
        # with 82 codes) whose siblings are DIFFERENT variants — a wrong rescue.
        # Only trust SKUs with few codes (variant-level); skip the big styles.
        sph0 = ", ".join(["%s"] * len(skus))
        safe = [r.custom_sku for r in frappe.db.sql(
            f"SELECT custom_sku, COUNT(*) n FROM `tabItem` WHERE custom_sku IN ({sph0}) "
            f"GROUP BY custom_sku HAVING n <= 8", tuple(skus), as_dict=True)]
        skus = safe
        if not skus:
            return {}
        wp = ["% - JM", "Defective%", "Container%", "Air Freight%", "%Old%", "CORRECTING%"]
        net_sub = ("(SELECT COALESCE(SUM(b.actual_qty-b.reserved_qty),0) FROM `tabBin` b "
                   "WHERE b.item_code=it.name AND b.warehouse LIKE %s "
                   "AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s "
                   "AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s "
                   "AND b.warehouse NOT LIKE %s)")
        sph = ", ".join(["%s"] * len(skus))
        best = {}  # sku -> {code, net}
        for r in frappe.db.sql(
            f"SELECT it.custom_sku AS sku, it.name AS code, {net_sub} AS net "
            f"FROM `tabItem` it WHERE it.custom_sku IN ({sph}) HAVING net > 0",
            tuple(wp) + tuple(skus), as_dict=True):
            if r.sku not in best or r.net > best[r.sku]["net"]:
                best[r.sku] = {"code": r.code, "net": int(r.net or 0)}
        out = {}
        for order, lst in miss_by_order.items():
            for code, iname in lst:
                sku = code2sku.get(code)
                if sku and sku in best:
                    out[order] = {"sku": sku, "missCode": code, "missName": iname,
                                  "code": best[sku]["code"], "net": best[sku]["net"]}
                    break
        return out
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal._sku_rescue")
        return {}


def _norm_phone(p):
    """Bare national number for identity matching: digits only, drop a leading
    212/0 country/trunk prefix, keep the last 9 (Moroccan mobiles are 9 digits
    after the 0). Two orders with the same normalized phone are the same person."""
    d = "".join(c for c in (p or "") if c.isdigit())
    if d.startswith("212"):
        d = d[3:]
    return d[-9:] if len(d) >= 9 else d


def _consol_scope(groups):
    """A confirmation agent sees the clusters of THEIR customers only —
    a cluster is theirs when any of its orders is assigned to them. Managers,
    section admins and the floor see the whole set."""
    from logistics_portal.api.auth import resolve_role
    from logistics_portal.api.confirmation import _is_cf_admin
    u = frappe.session.user
    if resolve_role(u) != "confirmation" or _is_cf_admin():
        return groups
    return [g for g in groups if u in (g.get("assigns") or [])]


@frappe.whitelist()
def consolidation_count():
    """Just the number, for the sidebar badge — same cache, same scope."""
    return {"n": len(consolidation_groups(limit=60))}


@frappe.whitelist()
def consolidation_groups(limit=30):
    """Same-customer clusters still waiting to be picked: 2+ Confirmed orders
    sharing a phone number, none yet on a pick list. Phase 1 consolidation =
    pick & ship them in one go so they leave together (each order keeps its own
    AWB + COD — no carrier/accounting change, fully safe). Cached 120s.
    Returns [{key, customer, phone, city, sameAddress, count, mad, ageMins,
    orders:[{no, total, city, ageMins, items}]}] sorted by size then value."""
    import json as _json
    from frappe.utils import time_diff_in_seconds, now_datetime
    cache = frappe.cache()
    cached = cache.get_value("lp_consolidation")
    if cached:
        groups = _json.loads(cached)
        return _consol_scope(groups)[: min(int(limit), 60)]
    w = _win(BOARD_WINDOW_DAYS)
    try:
        rows = frappe.db.sql("""
            SELECT so.name AS no, so.customer_name AS customer, so.grand_total AS total,
                   so.custom_items_count AS nitems, so.creation AS created,
                   COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
                   so._assign AS assign,
                   COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address) AS addr,
                   COALESCE(NULLIF(so.custom_shipping_city,''), addr.city) AS city
            FROM `tabSales Order` so
            LEFT JOIN `tabAddress` addr
                ON addr.name = COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address)
            LEFT JOIN (SELECT pli.sales_order FROM `tabPick List Item` pli
                       JOIN `tabPick List` p ON p.name=pli.parent
                       WHERE p.docstatus < 2 GROUP BY pli.sales_order) pl ON pl.sales_order = so.name
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.sales_order IS NULL
              AND so.creation >= %s
              AND COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone, '') != ''
            ORDER BY so.creation DESC""", (w,), as_dict=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.consolidation_groups")
        return []

    now = now_datetime()
    clusters = {}
    for r in rows:
        key = _norm_phone(r.phone)
        if len(key) < 6:  # too short to trust as an identity
            continue
        clusters.setdefault(key, []).append(r)

    groups = []
    for key, items in clusters.items():
        if len(items) < 2:
            continue
        addrs = {(it.addr or "") for it in items}
        cities = [it.city for it in items if it.city]
        ages = []
        orders = []
        for it in items:
            try:
                a = max(0, int(time_diff_in_seconds(now, it.created) // 60))
            except Exception:
                a = 0
            ages.append(a)
            orders.append({"no": it.no, "total": float(it.total or 0),  # Decimal → JSON-safe
                           "city": (it.city or "") if len(it.city or "") <= 28 else "",
                           "items": it.nitems or 1, "ageMins": a})
        orders.sort(key=lambda o: o["no"])
        assigns = set()
        for it in items:
            try:
                assigns.update(a for a in _json.loads(it.assign or "[]") if a)
            except Exception:
                pass
        groups.append({
            "key": key,
            "assigns": sorted(assigns),
            "customer": items[0].customer or "",
            "phone": items[0].phone or "",
            "city": (cities[0] if cities else "") if len((cities[0] if cities else "")) <= 28 else "",
            "sameAddress": len(addrs) == 1,  # one drop point vs. same person/diff address
            "count": len(items),
            "mad": round(sum(float(o["total"] or 0) for o in orders)),
            "ageMins": max(ages) if ages else 0,
            "orders": orders,
        })
    groups.sort(key=lambda g: (-g["count"], -g["mad"]))
    cache.set_value("lp_consolidation", _json.dumps(groups), expires_in_sec=120)
    return _consol_scope(groups)[: min(int(limit), 60)]


def _board_rows(stage, track, limit, q=None, offset=0, city=None, sort=None, dates=None, pick_names=None):
    w, dw = _win(BOARD_WINDOW_DAYS), _win(DONE_WINDOW_DAYS)
    addr = """LEFT JOIN `tabAddress` addr
        ON addr.name = COALESCE(NULLIF(so.shipping_address_name,''), so.customer_address)"""
    pl_join = """LEFT JOIN (SELECT pli.sales_order, MAX(p.name) pl, MAX(p.docstatus) pl_ds,
                        MAX(p.custom_assigned_picker) picker, MAX(p.owner) pl_owner
                 FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name=pli.parent
                 WHERE p.docstatus < 2
                 GROUP BY pli.sales_order) pl ON pl.sales_order = so.name"""

    if stage == "to_pick":
        args = [w]
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _period_cond(dates, args, _dcol(stage))
        pc = ""
        if pick_names is not None:
            if not pick_names:
                return []
            pc = " AND so.name IN (%s)" % ", ".join(["%s"] * len(pick_names))
            args.extend(pick_names)
        rows = frappe.db.sql(f"""SELECT {_so_fields()} FROM `tabSales Order` so {addr} {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.sales_order IS NULL
              AND so.creation >= %s {qc} {cc} {dc}{pc}
            ORDER BY {_urgent_col()} IS NULL, {_order_by(sort, 'so.creation ASC')} LIMIT {limit} OFFSET {offset}""",
            tuple(args), as_dict=True)
        return [_row(r) for r in rows]

    if stage == "picking":
        args = [w]
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _period_cond(dates, args, _dcol(stage))
        rows = frappe.db.sql(f"""SELECT {_so_fields()}, pl.pl, pl.picker, pl.pl_owner
            FROM `tabSales Order` so {addr} {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.pl_ds = 0
              AND so.creation >= %s {qc} {cc} {dc}
            ORDER BY {_urgent_col()} IS NULL, {_order_by(sort, 'so.modified DESC')} LIMIT {limit} OFFSET {offset}""",
            tuple(args), as_dict=True)
        return [_row(r, pl=r.pl, picker=r.picker or r.pl_owner) for r in rows]

    if stage in ("prepared", "ready"):
        statuses = ["Label Generated", "Picked", "In transit", "Received"] \
            if stage == "prepared" else ["Label Printed"]
        ph = ", ".join(["%s"] * len(statuses))
        args = statuses + [w]
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _period_cond(dates, args, _dcol(stage))
        rows = frappe.db.sql(f"""SELECT {_so_fields()}, pl.pl, pl.picker, pl.pl_owner
            FROM `tabSales Order` so {addr} {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status IN ({ph}) AND so.creation >= %s {qc} {cc} {dc}
            ORDER BY {_order_by(sort, 'so.modified ASC')} LIMIT {limit} OFFSET {offset}""", tuple(args), as_dict=True)
        return [_row(r, pl=r.pl, picker=r.picker or r.pl_owner) for r in rows]

    if stage == "shipped":
        cond, args = "", [w]
        if track == "none":
            cond = "AND (so.custom_track_shipment_status IS NULL OR so.custom_track_shipment_status='')"
        elif track:
            cond = "AND so.custom_track_shipment_status = %s"
            args.append(track)
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _period_cond(dates, args, _dcol(stage))
        rows = frappe.db.sql(f"""SELECT {_so_fields()}, sh.sh FROM `tabSales Order` so {addr}
            LEFT JOIN (SELECT dni.against_sales_order so_name, MAX(sdn.parent) sh
                       FROM `tabDelivery Note Item` dni
                       JOIN `tabShipment Delivery Note` sdn ON sdn.delivery_note = dni.parent
                       GROUP BY dni.against_sales_order) sh ON sh.so_name = so.name
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Shipped' AND so.creation >= %s {cond} {qc} {cc} {dc}
            ORDER BY {_order_by(sort, 'so.modified ASC')} LIMIT {limit} OFFSET {offset}""", tuple(args), as_dict=True)
        return [_row(r, sh=r.sh) for r in rows]

    if stage == "delivered":
        args = [dw]
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _period_cond(dates, args, _dcol(stage))
        rows = frappe.db.sql(f"""SELECT {_so_fields()} FROM `tabSales Order` so {addr}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Delivered' AND so.creation >= %s {qc} {cc} {dc}
            ORDER BY so.modified DESC LIMIT {limit} OFFSET {offset}""", tuple(args), as_dict=True)
        return [_row(r) for r in rows]

    if stage in ("to_return", "returned"):
        from logistics_portal.api.returns import back_in_house_sql
        cond = ("AND " + back_in_house_sql()) if stage == "returned" \
            else "AND NOT " + back_in_house_sql()
        args = [dw]
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _period_cond(dates, args, _dcol(stage))
        rows = frappe.db.sql(f"""SELECT {_so_fields()}, dn.ret, dn.dn FROM `tabSales Order` so {addr}
            LEFT JOIN (SELECT dni.against_sales_order so_name, MAX(d.custom_return_shipment) ret,
                              MAX(d.name) dn
                       FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name=dni.parent
                       WHERE d.docstatus=1 AND d.posting_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                       GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              {"" if stage == "returned" else "AND so.custom_logistics_status='Returned'"}
              AND so.creation >= %s {cond} {qc} {cc} {dc}
            ORDER BY {_order_by(sort, 'so.modified ASC')} LIMIT {limit} OFFSET {offset}""", tuple(args), as_dict=True)
        return [_row(r, ret=r.ret, dn=r.dn) for r in rows]

    if stage == "attention":
        out = []
        for r in frappe.db.sql(f"""SELECT {_so_fields()}, pl.pl, pl.picker, 'cancelled_midflow' kind
            FROM `tabSales Order` so {addr} {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Cancelled'
              AND so.custom_logistics_status NOT IN ('Delivered','Returned')
              AND NOT {_back_in_house()}
              AND pl.pl IS NOT NULL AND so.creation >= %s
            ORDER BY so.modified DESC LIMIT 30""", (dw,), as_dict=True):
            out.append(_row(r, pl=r.pl, picker=r.picker, kind="cancelled_midflow"))
        for r in frappe.db.sql(f"""SELECT {_so_fields()}, pl.pl, pl.picker, 'no_awb' kind
            FROM `tabSales Order` so {addr} {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.pl_ds = 1
              AND (so.custom_awb IS NULL OR so.custom_awb='') AND so.creation >= %s
            ORDER BY so.modified DESC LIMIT 30""", (dw,), as_dict=True):
            out.append(_row(r, pl=r.pl, picker=r.picker, kind="no_awb"))
        for r in frappe.db.sql(f"""SELECT {_so_fields()}, 'sync_lag' kind FROM `tabSales Order` so {addr}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Shipped'
              AND so.custom_track_shipment_status='Delivered' AND so.creation >= %s
            ORDER BY so.modified DESC LIMIT 30""", (w,), as_dict=True):
            out.append(_row(r, kind="sync_lag"))
        return out

    return []


# ERPNext status -> design stage key + known picker emails -> handoffData id.
_STAGE_MAP = {
    "Pending": "pending", "Picked": "picked", "In transit": "transit",
    "Received": "labelgen", "Label Generated": "labelgen", "Label Printed": "label",
    "Shipped": "shipped", "Delivered": "delivered", "Returned": "returned",
}
_PICKER_ID = {
    "marouaneelmessaoudi07@gmail.com": "marouane", "mouakkalanass@gmail.com": "anass",
    "asmaazirary7@gmail.com": "asmaa", "lamdanisaad12@gmail.com": "saad",
    "ossamanahila@gmail.com": "oussama", "saidnakri65@gmail.com": "said",
    "redazaari47@gmail.com": "reda",
}


def _urgent_col():
    """`so.custom_urgent_at`, or a literal NULL before the field is migrated.
    Mirrors picking._urgent_col; duplicated rather than imported because
    picking imports this module."""
    try:
        if frappe.get_meta("Sales Order").has_field("custom_urgent_at"):
            return "so.custom_urgent_at"
    except Exception:
        pass
    return "NULL"


@frappe.whitelist()
def list(scope="floor", picker=None, limit=60):  # noqa: A001 — public RPC name.
    # WARNING: this shadows the builtin `list` for the WHOLE module. Never call
    # list(...) as a constructor anywhere in this file — use [*iterable].
    """Recent orders in the SPA's ORDERS shape (Pipeline + Picker queue).
    scope='queue' narrows to pick-ready stages; `picker` filters to that user's
    assigned pick lists (in SQL, BEFORE the limit — the old post-LIMIT filter
    silently shrank results). Pick meta comes from one LEFT JOIN instead of a
    per-row query (was N+1 = up to 60 extra queries per call)."""
    limit = min(max(int(limit or 60), 1), 200)
    statuses = (
        ["Pending", "Picked"] if scope == "queue"
        else ["Pending", "Picked", "In transit", "Received", "Label Generated", "Label Printed", "Shipped"]
    )
    try:
        ph = ", ".join(["%s"] * len(statuses))
        args = [*statuses]
        picker_cond = ""
        if picker:
            picker_cond = "AND pl.picker = %s"
            args.append(picker)
        args.append(limit)
        rows = frappe.db.sql(
            f"""SELECT so.name, so.customer_name, so.grand_total, so.custom_channel,
                       so.custom_logistics_status, so.custom_items_count,
                       so.custom_awb, so.creation, {_urgent_col()} AS urgent_at,
                       pl.picker AS pl_picker, pl.bin AS pl_bin
                FROM `tabSales Order` so
                LEFT JOIN (SELECT pli.sales_order,
                                  MAX(p.custom_assigned_picker) AS picker,
                                  MAX(pli.warehouse) AS bin
                           FROM `tabPick List Item` pli
                           JOIN `tabPick List` p ON p.name = pli.parent
                           WHERE p.docstatus < 2
                             AND p.creation >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                           GROUP BY pli.sales_order) pl ON pl.sales_order = so.name
                WHERE so.docstatus = 1 AND so.custom_sales_status = 'Confirmed'
                  AND so.custom_logistics_status IN ({ph})
                  AND so.creation >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                  {picker_cond}
                ORDER BY {_urgent_col()} IS NULL, so.modified DESC LIMIT %s""",
            tuple(args), as_dict=True)
        out = []
        for r in rows:
            pl = {"picker_id": _PICKER_ID.get(r.pl_picker), "bin": r.pl_bin}
            out.append({
                "no": r.name,
                "customer": r.customer_name,
                "channel": (r.custom_channel or "manual").lower() or "manual",
                "total": r.grand_total,
                "items": r.custom_items_count or 1,
                "stage": _STAGE_MAP.get(r.custom_logistics_status, "pending"),
                "sla": "ontrack",  # populated once the SLA engine runs
                "bin": pl.get("bin") or "",
                "zone": pl.get("bin") or "",
                "picker": pl.get("picker_id"),
                "mins": _age_mins(r.creation),
                "awb": r.custom_awb,
                "urgent": bool(r.get("urgent_at")),
            })
        return out
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.orders.list")
        return []


def _pick_meta(order):
    """Best-effort picker + bin for an order via its Pick List."""
    row = frappe.db.sql(
        """
        SELECT pl.custom_assigned_picker AS picker, pli.warehouse AS bin
        FROM `tabPick List Item` pli
        JOIN `tabPick List` pl ON pl.name = pli.parent
        WHERE pli.sales_order = %s LIMIT 1
        """,
        (order,), as_dict=True,
    )
    if not row:
        return {}
    email = row[0].picker
    return {"picker_email": email, "picker_id": _PICKER_ID.get(email), "bin": row[0].bin}


def _age_mins(creation):
    if not creation:
        return 0
    from frappe.utils import time_diff_in_seconds, now_datetime
    try:
        return max(0, int(time_diff_in_seconds(now_datetime(), creation) // 60))
    except Exception:
        return 0


# Version-log fields worth surfacing in the order's logistics activity feed.
_ACT_FIELDS = {
    "custom_logistics_status": ("status", "Status"),
    "custom_sales_status": ("sales", "Sales status"),
    "custom_track_shipment_status": ("track", "Carrier tracking"),
    "custom_awb": ("awb", "AWB"),
    "custom_assigned_picker": ("picker", "Picker assigned"),
}


@frappe.whitelist()
def add_note(name, text):
    """Write a free-text comment onto an order — the ERPNext comment box, from
    the portal. It lands in the same tabComment trail the activity feed reads,
    so it shows up in this order's timeline and in ERPNext itself. Any portal
    role may leave a note; it is attributed to them and timestamped."""
    from logistics_portal.api.auth import resolve_role
    if not resolve_role(frappe.session.user):
        frappe.throw("Not authorized.", frappe.PermissionError)
    # Same #-tolerant resolve the activity feed uses: orders come through as
    # "#250923" or "250923" or "SAL-ORD-...".
    nm = (name or "").lstrip("#")
    order = None
    for c in (name, nm, f"#{nm}"):
        if c and frappe.db.exists("Sales Order", c):
            order = c
            break
    if not order:
        frappe.throw("Unknown order.")
    text = (text or "").strip()
    if not text:
        frappe.throw("Empty note.")
    if len(text) > 1000:
        text = text[:1000]
    # add_comment escapes the content, so a note can't inject markup into the
    # feed (which strips HTML on the way out anyway).
    frappe.get_doc("Sales Order", order).add_comment("Comment", text)
    frappe.db.commit()
    return {"ok": True, "when": str(now_datetime())[:16],
            "actor": frappe.session.user}


@frappe.whitelist()
def activity(name):
    """Merged logistics activity feed for one order: field transitions from the
    Version log + comments + linked-document events, newest first."""
    import json as _json

    name = (name or "").lstrip("#")
    candidates = [name, f"#{name}"]
    so_name = None
    for c in candidates:
        if frappe.db.exists("Sales Order", c):
            so_name = c
            break
    if not so_name:
        return []

    events = []

    # 1) Field transitions (who changed what, when) from the Version log.
    for v in frappe.get_all(
        "Version",
        filters={"ref_doctype": "Sales Order", "docname": so_name},
        fields=["owner", "creation", "data"],
        order_by="creation asc", limit=60,
    ):
        try:
            d = _json.loads(v.data or "{}")
        except Exception:
            continue
        for ch in (d.get("changed") or []):
            f, old, new = str(ch[0]), ch[1], ch[2]
            if f == "docstatus" and old == 0 and new == 1:
                events.append({"when": str(v.creation)[:16], "kind": "submit",
                               "title": "Order submitted", "detail": "", "actor": v.owner})
            elif f in _ACT_FIELDS:
                kind, label = _ACT_FIELDS[f]
                if kind == "awb":
                    events.append({"when": str(v.creation)[:16], "kind": "awb",
                                   "title": "AWB created", "detail": str(new or ""), "actor": v.owner})
                else:
                    events.append({"when": str(v.creation)[:16], "kind": kind,
                                   "title": f"{label}: {old or '—'} → {new or '—'}",
                                   "detail": "", "actor": v.owner})

    # 2) Comments on the order.
    for c in frappe.get_all(
        "Comment",
        filters={"reference_doctype": "Sales Order", "reference_name": so_name,
                 "comment_type": "Comment"},
        fields=["owner", "creation", "content"],
        order_by="creation asc", limit=20,
    ):
        text = frappe.utils.strip_html(c.content or "").strip()
        import re as _re
        text = _re.sub(r"\[([^\]]*)\]\([^\)]*\)", r"\1", text)   # [label](url) → label
        text = _re.sub(r"\S+@\S+\.\S+", "", text)                   # drop raw emails
        text = _re.sub(r"\s{2,}", " ", text).strip(" :·-")
        if text:
            events.append({"when": str(c.creation)[:16], "kind": "comment",
                           "title": "Comment", "detail": text[:200], "actor": c.owner})

    # 3) Linked logistics documents.
    for pl in frappe.get_all(
        "Pick List",
        filters={"name": ["in", [r.parent for r in frappe.get_all(
            "Pick List Item", filters={"sales_order": so_name}, fields=["parent"], limit=5)]]},
        fields=["name", "owner", "creation", "modified", "docstatus", "custom_assigned_picker"],
    ):
        events.append({"when": str(pl.creation)[:16], "kind": "pl",
                       "title": "Pick List created", "detail": pl.name, "actor": pl.owner})
        if pl.docstatus == 1:
            events.append({"when": str(pl.modified)[:16], "kind": "pl",
                           "title": "Pick List submitted", "detail": pl.name,
                           "actor": pl.custom_assigned_picker or pl.owner})

    dns = frappe.get_all(
        "Delivery Note Item", filters={"against_sales_order": so_name},
        fields=["parent"], limit=3)
    for dnr in {r.parent for r in dns}:
        dn = frappe.db.get_value("Delivery Note", dnr,
                                 ["owner", "creation", "custom_return_shipment"], as_dict=True)
        if not dn:
            continue
        events.append({"when": str(dn.creation)[:16], "kind": "dn",
                       "title": "Delivery Note created", "detail": dnr, "actor": dn.owner})
        sh = frappe.db.get_value("Shipment Delivery Note", {"delivery_note": dnr}, "parent")
        if sh:
            shd = frappe.db.get_value("Shipment", sh, ["owner", "creation"], as_dict=True)
            if shd:
                events.append({"when": str(shd.creation)[:16], "kind": "sh",
                               "title": "Added to manifest", "detail": sh, "actor": shd.owner})
        if dn.custom_return_shipment:
            rt = frappe.db.get_value("Return Shipment", dn.custom_return_shipment,
                                     ["owner", "creation"], as_dict=True)
            if rt:
                events.append({"when": str(rt.creation)[:16], "kind": "ret",
                               "title": "Received in return batch",
                               "detail": dn.custom_return_shipment, "actor": rt.owner})

    events.sort(key=lambda e: e["when"], reverse=True)
    return events[:50]


def _off_face(items):
    """[{name, code, qty, where}] for lines that are sellable but not on a
    pick face — one grouped read over the sellable-only zones."""
    plain = {r.get("sku") for r in items
             if r.get("offFace") and not r.get("components") and r.get("sku")}
    comps = {c["sku"] for r in items for c in (r.get("components") or [])
             if c.get("offFace") and c.get("sku")}
    want = plain | comps
    if not want:
        return []
    from logistics_portal.api.warehouses import sell_zones
    zones = sell_zones()
    where = {}
    if zones:
        for b in frappe.db.sql(
                f"""SELECT item_code, warehouse, actual_qty FROM `tabBin`
                    WHERE actual_qty > 0 AND item_code IN %s
                      AND warehouse IN ({', '.join(['%s'] * len(zones))})
                    ORDER BY actual_qty DESC""",
                tuple([tuple(want)] + zones), as_dict=True):
            where.setdefault(b.item_code, []).append(
                (b.warehouse, int(b.actual_qty or 0)))
    out = []
    for r in items:
        if not r.get("offFace"):
            continue
        rows = ([{"sku": c["sku"], "name": c.get("name") or c["sku"]} for c in (r.get("components") or []) if c.get("offFace")]
                or [{"sku": r.get("sku"), "name": r.get("name") or r.get("sku")}])
        for one in rows:
            w = where.get(one["sku"]) or []
            out.append({"name": one["name"], "code": one["sku"],
                        "qty": sum(q for _z, q in w),
                        "where": ", ".join(z.replace(" - JM", "") for z, _q in w[:2])})
    return out


@frappe.whitelist()
def detail(name):
    """Full order detail for the shared OrderDetail screen. Any portal role —
    but a role is REQUIRED: this returns the customer's name, phone and
    address, and it used to be open to every authenticated Frappe user by
    ordinal-name enumeration."""
    from logistics_portal.api.auth import resolve_role
    if not resolve_role(frappe.session.user):
        frappe.throw("Not authorized.", frappe.PermissionError)
    name = (name or "").lstrip("#")
    for cand in (name, f"#{name}"):
        if frappe.db.exists("Sales Order", cand):
            name = cand
            break
    else:
        return {}
    so = frappe.get_doc("Sales Order", name)

    # Line items with the product image (97% of items carry one).
    items = frappe.db.sql(
        """SELECT soi.idx, soi.name row, soi.item_code sku, soi.item_name name, soi.qty, soi.rate price,
                  soi.amount line, soi.warehouse bin, i.image, i.custom_sku real_sku
           FROM `tabSales Order Item` soi
           LEFT JOIN `tabItem` i ON i.name = soi.item_code
           WHERE soi.parent = %s ORDER BY soi.idx""",
        (name,), as_dict=True)

    # Can this order actually be picked? The confirmation agent is on the phone
    # with the customer — finding out days later that a line was out of stock
    # is a cancelled order and a lost call. Same pool math the Orders board
    # runs: free stock across pickable bins minus every live reservation, with
    # THIS order's own reservation credited back.
    try:
        from logistics_portal.api.picking import availability
        # A product bundle line is judged on its components: the box itself
        # holds no stock, its five pieces do (JUSTYOL Top 5 Box, 2026-09-14).
        _packed = {}
        for pk in frappe.db.sql(
                """SELECT parent_detail_docname AS row, item_code, item_name, qty
                   FROM `tabPacked Item` WHERE parent = %s AND parenttype = 'Sales Order'
                   ORDER BY idx""", (name,), as_dict=True):
            _packed.setdefault(pk.row, []).append(pk)
        for r in items:
            comps = _packed.get(r.row) if _packed else None
            if comps:
                r["components"] = [{"sku": c.item_code, "name": c.item_name, "qty": float(c.qty or 0)}
                                   for c in comps]
        _codes = {r.sku for r in items if r.sku and not r.get("components")}
        _codes |= {c["sku"] for r in items for c in (r.get("components") or [])}
        if _codes:
            # One shared definition, so the card, the board and the create can
            # never disagree about the same line again.
            # The confirmation agent is deciding whether to PROMISE the
            # order, so the question is "is it ours to sell", not "can a
            # picker reach it today". Both numbers are computed: the second
            # is what tells the warehouse a transfer is needed before this
            # order can move, and without it a confirmed order would simply
            # strand in the pool with nobody told why.
            _totals, _sre, _free = availability(_codes, scope="sell")
            _ptotals, _psre, _pfree = availability(_codes)
            # A LOCAL supplier's item is never "out of stock" on this card:
            # its stock lives at the supplier, not on our shelves, so our
            # pool math reading zero is a statement about our warehouse, not
            # about the order. Flagging it rose taught agents to refuse
            # perfectly fulfillable orders (Ahmed 2026-09-10). It still gets
            # its own quiet chip — the agent should know it ships from the
            # supplier — and the Orders board keeps its separate `local`
            # bucket with the PO-promise radar for the follow-through.
            _local = set()
            try:
                _local = {r2[0] for r2 in frappe.db.sql(
                    """SELECT i.name FROM `tabItem` i
                       JOIN `tabSupplier` s ON s.name = i.default_supplier
                       WHERE i.name IN %s AND s.supplier_group = %s""",
                    (tuple(_codes), LOCAL_SUPPLIER_GROUP))}
            except Exception:
                pass
            for r in items:
                if r.get("components"):
                    # The bundle is available as many times as its scarcest
                    # component allows; short if any piece is short.
                    fits = []
                    shorts = []
                    offs = []
                    for c in r["components"]:
                        _f = _free(name, c["sku"])
                        _pf = _pfree(name, c["sku"])
                        c["avail"] = int(max(0, _f))
                        c["availFace"] = int(max(0, _pf))
                        c["short"] = bool(_f < c["qty"]) and c["sku"] not in _local
                        c["offFace"] = bool(not c["short"] and _pf < c["qty"]
                                            and c["sku"] not in _local)
                        if c["offFace"]:
                            offs.append(c)
                        if c["short"]:
                            shorts.append(c)
                        per = c["qty"] / float(r.qty or 1) if r.qty else c["qty"]
                        fits.append(int(max(0, _f) // per) if per else 0)
                    r["avail"] = min(fits) if fits else 0
                    r["short"] = bool(shorts)
                    r["offFace"] = bool(offs) and not shorts
                    r["shortComponents"] = shorts
                    continue
                _need = float(r.qty or 0)
                _f = _free(name, r.sku)
                _pf = _pfree(name, r.sku)
                r["avail"] = int(max(0, _f))
                r["availFace"] = int(max(0, _pf))
                if r.sku in _local:
                    r["local"] = True
                    r["short"] = False
                else:
                    r["short"] = bool(_f < _need)
                    # Sellable but not on a pick face: the order can be
                    # confirmed, and somebody has to move the stock first.
                    # Saying "out of stock" here is what made agents cancel
                    # live sales — J-008094 was told out of stock with 1,986
                    # units of its item in the building.
                    r["offFace"] = bool(not r["short"] and _pf < _need)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "orders.detail stock")

    # Real shipping address (city lives on the linked Address, not the SO).
    addr = {}
    addr_name = so.get("shipping_address_name") or so.get("customer_address")
    if addr_name:
        addr = frappe.db.get_value(
            "Address", addr_name,
            ["city", "state", "address_line1"], as_dict=True) or {}

    # Linked logistics documents (the real chain).
    pl = frappe.db.sql(
        """SELECT p.name, p.docstatus, p.custom_assigned_picker picker
           FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name = pli.parent
           WHERE pli.sales_order = %s AND p.docstatus < 2
           ORDER BY p.creation DESC LIMIT 1""", (name,), as_dict=True)
    pl = pl[0] if pl else None
    dn = frappe.db.get_value(
        "Delivery Note Item", {"against_sales_order": name, "docstatus": 1}, "parent")
    sh = frappe.db.get_value("Shipment Delivery Note", {"delivery_note": dn}, "parent") if dn else None
    ret = frappe.db.get_value("Delivery Note", dn, "custom_return_shipment") if dn else None

    return {
        "items": [dict(r) for r in items],
        "name": so.name,
        "customer": so.customer_name,
        "channel": so.get("custom_channel"),
        # Sold on the phone by one of ours — the agent about to dial needs to
        # see that before they press call, not after the customer says "I
        # already ordered this with Meriem".
        "phoneSale": (so.get("custom_order_source") or "") == PHONE_SOURCE,
        "soldBy": seller_from_tags(so.get("_user_tags")),
        "created": str(so.creation)[:16],
        # money — the real ERPNext numbers, not derived
        "subtotal": so.total,
        "discount": so.discount_amount or 0,
        "taxes": so.total_taxes_and_charges or 0,
        "total": so.grand_total,
        "sales_status": so.get("custom_sales_status") or "",
        # Name to read, code to look up: the agent has the customer on the
        # line and needs to check the shelf, not just be told there is none.
        # A short bundle names the PIECE that is short, not the box.
        # Sellable, but a transfer stands between the promise and the parcel.
        # Named with the zone and the quantity, because "somewhere else" is
        # not something a dispatcher can act on.
        "stockOffFace": _off_face(items),
        "stockShort": [x for r in items if r.get("short") for x in (
            [{"name": c.get("name") or c.get("sku"), "code": c.get("sku") or ""}
             for c in r.get("shortComponents") or []]
            or [{"name": r.get("name") or r.get("sku"), "code": r.get("sku") or ""}])],
        "attempts": int(so.get("custom_call_attempts") or 0),
        "next_call": str(so.get("custom_next_call_at") or "")[:16],
        "payment_collection": so.get("custom_payment_collection") or "",
        "stage": so.get("custom_logistics_status") or "Pending",
        # The parcel is on our shelves whatever the stage says. Worth its own
        # line: an agent who cannot see it promises the customer a redelivery
        # the carrier can no longer make, because the carrier does not have it.
        "backAt": _back_in_house_at(name),
        "urgentAt": str(so.get("custom_urgent_at") or "")[:19],
        "urgentBy": (so.get("custom_urgent_by") or "").split("@")[0],
        "urgentReason": so.get("custom_urgent_reason") or "",
        # contact & destination
        "phone": so.get("custom_customer_phone") or so.get("custom_shipping_phone") or "",
        "city": so.get("custom_shipping_city") or addr.get("city") or "",
        "governorate": so.get("custom_shipping_governorate") or addr.get("state") or "",
        "address_line": addr.get("address_line1") or "",
        "ref": so.get("custom_reference_number") or so.get("custom_youcan_order_id") or "",
        # carrier
        "awb": so.get("custom_awb"),
        "label_url": so.get("custom_label_url") or "",
        "tracking_number": so.get("custom_tracking_number") or "",
        "tracking_url": so.get("custom_tracking_url") or "",
        "tracking_status": so.get("custom_track_shipment_status"),
        "tracking_company": so.get("custom_tracking_company") or "Cathedis",
        # linked docs
        "pl": pl["name"] if pl else "",
        "pl_submitted": bool(pl and pl["docstatus"] == 1),
        "picker": (pl or {}).get("picker") or "",
        "dn": dn or "",
        "sh": sh or "",
        "ret": ret or "",
        # stage timestamps (fill as the portal stamps them)
        "picked_at": so.get("custom_picked_at"),
        "labeled_at": so.get("custom_labeled_at"),
        "shipped_at": so.get("custom_shipped_at"),
        "delivered_at": so.get("custom_delivered_at"),
    }


@frappe.whitelist()
def merge_orders(orders, force=0):
    """Confirmation-team merge: combine a same-customer cluster into ONE new
    Sales Order so logistics receives a single order (one AWB, one COD = the
    sum of the originals). The originals are cancelled and marked Duplicated.
    Only safe before logistics touches them — any pick list, AWB or payment
    blocks the merge. Manager only (moves to the confirmation role later)."""
    import json as _json
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can merge orders.", frappe.PermissionError)
    if isinstance(orders, str):
        orders = _json.loads(orders)
    names = [str(o).strip() for o in (orders or []) if str(o).strip()]
    if len(names) < 2:
        frappe.throw("Select at least two orders to merge.")

    # Serialize merges: without this, two agents merging overlapping clusters
    # (or a merge racing a pick-list creation) can cancel an order twice or
    # merge one that just got picked.
    from logistics_portal.api.locks import named_lock

    with named_lock("merge_orders", timeout=20):
        return _do_merge(names, force=frappe.utils.cint(force))


def _strip_external_identity(doc):
    """A copied Sales Order must NOT inherit the source's external identity.
    ecommerce_integrations hooks Sales Order autoname and names the doc from
    `shopify_order_number` — a copy that keeps it collides with the original
    (DuplicateEntryError → HTTP 409). `custom_youcan_order_id` carries a DB
    unique index with the same effect. Clearing these lets naming fall back to
    the SAL-ORD- series and keeps the Shopify/YouCan sync pointed at the
    original order only (provenance lives in the comments)."""
    for f in ("shopify_order_number", "shopify_order_id", "shopify_order_status",
              "custom_youcan_order_id", "order_status_url", "fulfillment_status",
              "financial_status"):
        if doc.meta.has_field(f):
            doc.set(f, None)


def _do_merge(names, force=0):
    docs = []
    for name in names:
        if not frappe.db.exists("Sales Order", name):
            frappe.throw(f"Unknown order: {name}")
        so = frappe.get_doc("Sales Order", name)
        if so.docstatus != 1:
            frappe.throw(f"{name} is not submitted.")
        if (so.custom_sales_status or "") != "Confirmed":
            frappe.throw(f"{name} is not Confirmed ({so.custom_sales_status or 'no status'}).")
        if (so.get("custom_logistics_status") or "Pending") != "Pending":
            frappe.throw(f"{name} already moved to logistics "
                         f"({so.custom_logistics_status}) — too late to merge.")
        if so.get("custom_awb"):
            frappe.throw(f"{name} already has an AWB — too late to merge.")
        docs.append(so)

    if len({d.customer for d in docs}) > 1:
        frappe.throw("These orders belong to different customers.")
    phones = {_norm_phone(d.get("custom_customer_phone") or d.get("custom_shipping_phone") or "")
              for d in docs}
    phones.discard("")
    if len(phones) > 1 and not force:
        # Not a hard block anymore: the manager confirms it's really one
        # person and re-calls with force=1 — no desk detour.
        return {"ok": False, "needsForce": True, "reason": "phones",
                "phones": sorted(phones)}

    on_pl = frappe.db.sql(
        """SELECT pli.sales_order, pli.parent FROM `tabPick List Item` pli
           JOIN `tabPick List` p ON p.name = pli.parent
           WHERE p.docstatus < 2 AND pli.sales_order IN %s LIMIT 1""",
        (tuple(names),))
    if on_pl:
        frappe.throw(f"{on_pl[0][0]} is already on pick list {on_pl[0][1]} — cancel it first.")
    paid = frappe.db.sql(
        """SELECT reference_name FROM `tabPayment Entry Reference` per
           JOIN `tabPayment Entry` pe ON pe.name = per.parent
           WHERE pe.docstatus = 1 AND per.reference_doctype = 'Sales Order'
             AND per.reference_name IN %s LIMIT 1""",
        (tuple(names),))
    if paid:
        frappe.throw(f"{paid[0][0]} already has a payment against it — ask "
                     "accounting to unlink the payment first, then merge.")

    # New order = a copy of the OLDEST one (keeps customer, address, phone,
    # city, taxes) + every other order's items appended.
    docs.sort(key=lambda d: d.creation)
    base = frappe.copy_doc(docs[0])
    _strip_external_identity(base)
    for extra in docs[1:]:
        for it in extra.items:
            base.append("items", {
                "item_code": it.item_code, "item_name": it.item_name,
                "qty": it.qty, "rate": it.rate, "uom": it.uom,
                "warehouse": it.warehouse,
                "delivery_date": it.delivery_date or base.delivery_date,
            })
    base.custom_sales_status = "Confirmed"
    for f in ("custom_logistics_status",):
        if base.meta.has_field(f):
            base.set(f, "Pending")
    for f in ("custom_awb", "custom_label_url", "custom_tracking_number"):
        if base.meta.has_field(f):
            base.set(f, None)
    base.flags.ignore_permissions = True
    base.insert(ignore_permissions=True)
    # Same one line, same reason. The cancel loop below already knew about
    # TimestampMismatchError and reloads to survive it — the submit right
    # here did not, and threw first, every time: zero "Merged from" comments
    # exist on production.
    from logistics_portal.api.utils import submit_new_sales_order
    submit_new_sales_order(base)
    base.add_comment("Comment", "Merged from " + ", ".join(names))

    for d in docs:
        # Cancel each original. A background touch (the Shopify/YouCan sync,
        # which keeps writing to these rows) can bump `modified` in the split
        # second between loading the doc and cancelling it, so cancel's own
        # "is this the latest?" check throws TimestampMismatchError ("Document
        # has been modified after you have opened it"). We hold the merge lock
        # and have already validated every doc's state, so this is a false
        # conflict: reload and retry. The check runs before any write, so a
        # failed attempt leaves nothing partial (no rollback needed, which would
        # also undo the new order we just created).
        fresh = None
        for attempt in range(3):
            fresh = frappe.get_doc("Sales Order", d.name)
            if fresh.docstatus == 2:
                break  # already cancelled
            fresh.flags.ignore_permissions = True
            fresh.flags.ignore_version = True
            try:
                fresh.cancel()
                break
            except frappe.TimestampMismatchError:
                if attempt == 2:
                    raise
        fresh.add_comment("Comment", f"Merged into {base.name}")
        fresh.db_set("custom_sales_status", "Duplicated", update_modified=False)

    for k in ("lp_board_summary", "lp_consolidation", "lp_pick_avail"):
        frappe.cache().delete_value(k)
    frappe.cache().delete_keys("lp_suggest")
    frappe.db.commit()
    return {"ok": True, "order": base.name, "total": float(base.grand_total or 0),
            "items": len(base.items), "cancelled": names}


@frappe.whitelist()
def reship(order):
    """Re-enter a failed delivery into the shipping cycle. Creates a NEW Sales
    Order copy (same customer/address/items) that flows through pick → sort →
    manifest normally and gets its own DN + AWB — the carrier automation skips
    orders that already have a Delivery Note, so reusing the original SO can't
    work. The original keeps its history and its coming-back parcel (which
    re-enters stock through the RET receiving + restock flow).
    Dispatcher/manager only."""
    # The SECOND thing wrong with this button, independent of the first.
    # Reship is reached almost entirely from the rescue board, whose own
    # gate admits confirmation, tracking and manager — and this list left
    # TRACKING out. Measured 2026-09-21: of 580 rescue decisions in 30 days,
    # 517 (89%) were made by the two tracking agents. So the people who do
    # nearly all of this work were refused by the one action that needed a
    # role list of its own, on a board they are trusted to run.
    #
    # dispatcher stays: reship is also reachable outside the rescue board.
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("dispatcher", "manager",
                                                 "confirmation", "tracking"):
        frappe.throw("Only a dispatcher, tracking or confirmation agent can reship.",
                     frappe.PermissionError)

    raw = (order or "").strip()
    stripped = raw.lstrip("#")
    name = None
    for cand in (raw, stripped, "#" + stripped):
        if cand and frappe.db.exists("Sales Order", cand):
            name = cand
            break
    if not name:
        frappe.throw("Unknown order.")
    so = frappe.get_doc("Sales Order", name)
    if so.docstatus != 1:
        frappe.throw("Original order must be submitted.")
    # Guard: one live reship at a time (a Confirmed copy already in flight).
    dup = frappe.db.sql(
        """SELECT c.reference_name FROM `tabComment` c
           WHERE c.reference_doctype='Sales Order' AND c.reference_name=%s
             AND c.content LIKE 'Reshipped as%%' LIMIT 1""", (name,))
    if dup:
        frappe.throw("This order was already reshipped — check its comments.")

    new = frappe.copy_doc(so)
    _strip_external_identity(new)
    new.custom_sales_status = "Confirmed"
    for f in ("custom_logistics_status",):
        if new.meta.has_field(f):
            new.set(f, "Pending")
    for f in ("custom_awb", "custom_label_url", "custom_tracking_number",
              "custom_track_shipment_status", "custom_short_picked_at"):
        if new.meta.has_field(f):
            new.set(f, None)
    new.flags.ignore_permissions = True
    new.insert(ignore_permissions=True)
    # Not new.submit(): see submit_new_sales_order. Reship had produced
    # exactly zero reshipped orders — no "Reshipped as" comment has ever
    # been written — while redeliver, returnreq and cancel on the same board
    # worked all along.
    from logistics_portal.api.utils import submit_new_sales_order
    submit_new_sales_order(new)
    new.add_comment("Comment", f"Reship of {name} (failed delivery).")
    so.add_comment("Comment", f"Reshipped as {new.name} by {frappe.session.user}.")

    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
        frappe.cache().delete_value(k)
    frappe.db.commit()
    return {"ok": True, "order": new.name, "original": name,
            "total": float(new.grand_total or 0)}


def guard_cancelled_resurrect(doc, method=None):
    """A cancelled order stays cancelled unless a HUMAN says otherwise.

    TKT-2609-3709664: the external WhatsApp flow, writing through the API as
    Administrator, was flipping Cancelled orders back to "Follow Up" — 116
    flips on 88 orders in 30 days, every one owned by Administrator, at all
    hours, changing nothing but the status field. The team then cancelled
    the same order a second time, and customers who had said "not
    interested" were called again. Verified end-to-end on one order:
    cancel → resurrect → cancel → resurrect → another call, in six days.

    The guard reverts exactly that transition when the actor is the
    automation identity; an agent or manager reopening on purpose (their own
    session user) is untouched. Runs on validate, so the write simply never
    lands — and one witness comment per order (not per attempt) records that
    the automation keeps trying.
    """
    if doc.get("custom_sales_status") != "Follow Up" or doc.is_new():
        return
    if frappe.session.user not in ("Administrator", "Guest"):
        return
    try:
        old = doc.get_doc_before_save()
    except Exception:
        old = None
    if not old or old.get("custom_sales_status") != "Cancelled":
        return
    doc.custom_sales_status = "Cancelled"
    try:
        marker = "Automation tried to reopen this cancelled order"
        if not frappe.db.exists("Comment", {
                "reference_doctype": "Sales Order",
                "reference_name": doc.name,
                "content": ("like", f"%{marker}%")}):
            doc.add_comment(
                "Comment",
                f"{marker} (Cancelled → Follow Up) — blocked. "
                "TKT-2609-3709664")
    except Exception:
        pass


def restore_resurrected_cancels():
    """One-time repair riding the next deploy — TKT-2609-3709664.

    Six orders were sitting in "Follow Up" because the external automation
    resurrected them after a human cancel (see guard_cancelled_resurrect).
    Restore the human's decision. Conditional on the status STILL being
    Follow Up at migrate time — an agent may have re-cancelled (or genuinely
    reopened) one in the meantime, and either way their newer decision wins.
    Idempotent via a site default.
    """
    if frappe.db.get_default("lp_tkt3709664_restored"):
        return
    names = ("#256787", "#256948", "#257996", "#258007",
             "J-004476", "J-005176")
    for name in names:
        try:
            if frappe.db.get_value("Sales Order", name,
                                   "custom_sales_status") != "Follow Up":
                continue
            frappe.db.set_value("Sales Order", name,
                                "custom_sales_status", "Cancelled",
                                update_modified=False)
            frappe.get_doc("Sales Order", name).add_comment(
                "Comment",
                "Restored to Cancelled — the WhatsApp automation had "
                "reopened this cancelled order as Follow Up. "
                "TKT-2609-3709664")
        except Exception:
            frappe.log_error(frappe.get_traceback()[:2000],
                             "restore_resurrected_cancels")
    frappe.db.set_default("lp_tkt3709664_restored", "1")
    frappe.db.commit()


# ── Urgent: the customer rang and the parcel is still on our floor ────────
#
# Ahmed, 2026-09-21: "if the order is with us in the warehouse and the
# customer called and it is late, there should be an Urgent button".
#
# Measured the same day: 489 confirmed orders sit unpicked in the warehouse
# and 89 of them are older than 48 hours. That is the population — small
# enough for a flag to mean something, which is the whole point. A priority
# every tenth order carries is not a priority.
#
# What it does NOT do is create a pick list. One list per urgent order is
# the pick-list shattering problem wearing a new hat: a picker walking the
# whole warehouse for a single box is the most expensive pick in the
# building. The batch engine already runs every fifteen minutes and already
# sorts by missed-cutoff; urgent simply sorts above that, inside the next
# batch, and wears a badge so the floor can see why.

_URGENT_ROLES = ("cs", "confirmation", "tracking", "manager")


def _urgent_ready():
    try:
        return frappe.get_meta("Sales Order").has_field("custom_urgent_at")
    except Exception:
        return False


_URGENT_I18N = {
    "en": ("Urgent order: {o}", "{who} asked for this one to be pulled forward."),
    "fr": ("Commande urgente : {o}", "{who} demande de la faire passer en premier."),
    "ar": ("أوردر مستعجل: {o}", "{who} طالب إنه يتقدّم في الدور."),
}


def _floor_targets():
    """Who on the floor can actually act on a priority.

    The role table alone cannot answer this. `resolve_role` calls nineteen
    enabled accounts dispatcher-or-manager, because the System Manager
    heuristic sweeps in HR, developers and a test login — while the accounts
    that cut nearly every batch carry no logistics role at all, so a query on
    the role field reaches none of them. Ring the wrong nineteen once and the
    bell is dead for everybody (short-pick did exactly that: 3,462 rings in a
    week, one of them read).

    So the set is MEASURED first — whoever cut a pick list in the last week —
    and only then widened by the two role sources."""
    try:
        from logistics_portal.api.auth import SEED_ROLES
        users = {u for u, r in SEED_ROLES.items() if r in ("dispatcher", "manager")}
        users |= {u for (u,) in frappe.db.sql(
            """SELECT name FROM `tabUser`
               WHERE enabled = 1 AND custom_logistics_role = 'dispatcher'""")}
        users |= {u for (u,) in frappe.db.sql(
            """SELECT DISTINCT owner FROM `tabPick List`
               WHERE creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)""")}
        users.discard("Administrator")
        users.discard("Guest")
        if not users:
            return []
        return [u for (u,) in frappe.db.sql(
            "SELECT name FROM `tabUser` WHERE enabled = 1 AND name IN %s",
            (tuple(users),))]
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "orders._floor_targets")
        return []


def _ring_floor(order, reason=""):
    """Tell the floor a priority just landed, and return how many heard it.

    Until now the flag only re-sorted a pool: it was written, a comment was
    added, and then it waited for a dispatcher to open the batch builder.
    Nothing was pushed anywhere — zero Notification Log rows in the feature's
    whole life — so an agent who marked an order urgent had no way to know
    whether anyone would ever see it. The count comes back so the toast can
    say so instead of pretending.

    Dedup is on the URGENT subject, not on the order: an unread short-pick
    alert on the same parcel is a different message and must not silence
    this one."""
    told = 0
    try:
        who = (frappe.session.user or "").split("@")[0]
        i18n = {k: {"t": t.format(o=order),
                    "b": b.format(who=who) + (f" — {reason.strip()}" if (reason or "").strip() else "")}
                for k, (t, b) in _URGENT_I18N.items()}
        import json as _json
        packed = _json.dumps({"lp": i18n, "sev": "warning", "kind": "urgent"},
                             ensure_ascii=False).replace("--", "- -")
        subject = i18n["en"]["t"]
        quiet = frappe.utils.add_to_date(now_datetime(), hours=-6)
        for d in _floor_targets():
            if d == frappe.session.user:
                continue
            try:
                if frappe.db.sql(
                        """SELECT 1 FROM `tabNotification Log`
                           WHERE for_user = %s AND subject = %s
                             AND (`read` = 0 OR creation >= %s) LIMIT 1""",
                        (d, subject, quiet)):
                    continue
                frappe.get_doc({
                    "doctype": "Notification Log", "type": "Alert",
                    "subject": subject,
                    "email_content": i18n["en"]["b"] + "\n<!--lp-i18n " + packed + " -->",
                    "document_type": "Sales Order", "document_name": order,
                    "for_user": d,
                }).insert(ignore_permissions=True)
                frappe.publish_realtime("logistics_alert", {
                    "severity": "warning", "title": subject,
                    "detail": i18n["en"]["b"], "i18n": i18n, "audience": "user",
                }, user=d)
                told += 1
            except Exception:
                continue
    except Exception:
        # Telling them is the point, but failing to tell them must never undo
        # the flag itself.
        frappe.log_error(frappe.get_traceback()[:2000], "orders._ring_floor")
    return told


@frappe.whitelist(methods=["POST"])
def mark_urgent(order, reason=""):
    """Push one order to the front of the next pick batch.

    Only while it is still OURS. Once the parcel is cut the warehouse has
    nothing left to hurry, and a flag that survives the handover is a flag
    the floor learns to ignore."""
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in _URGENT_ROLES:
        frappe.throw("Not authorized to flag an order urgent.",
                     frappe.PermissionError)
    from logistics_portal.api.utils import resolve_order
    order = resolve_order(order)
    so = frappe.db.get_value(
        "Sales Order", order,
        ["company", "docstatus", "custom_sales_status", "custom_logistics_status"],
        as_dict=True) if order else None
    if not so or so.company != "Justyol Morocco" or so.docstatus != 1:
        frappe.throw("Unknown order.")
    if not _urgent_ready():
        frappe.throw("The urgent flag is not installed on this site yet.")
    if (so.custom_logistics_status or "") not in ("", "Pending"):
        frappe.throw(f"lp:urgentGone|{so.custom_logistics_status}")
    if so.custom_sales_status != "Confirmed":
        # An unconfirmed order has no place in the pick pool to jump to.
        frappe.throw(f"lp:urgentNotConfirmed|{so.custom_sales_status or '—'}")
    # Neither has one that is ALREADY on a list. This is the case that had no
    # guard: the two other fences catch an order the warehouse has moved on
    # from, but an order sitting on a live pick list still reads Confirmed and
    # Pending, so the flag was set, the comment written, the toast shown — and
    # no screen read it. The pool the flag reorders excludes anything already
    # on a list, and the sort wall only shows SUBMITTED ones, so between those
    # two states it is a flag in an empty room. #261108 on PL-56211,
    # 2026-09-22. Say where the order actually is instead.
    from logistics_portal.api.picking import live_pick_list
    on_list = live_pick_list(order)
    if on_list:
        pl, done = on_list
        frappe.throw(("lp:urgentListDone|" if done else "lp:urgentListPicking|") + pl)

    now = now_datetime()
    frappe.db.set_value("Sales Order", order, {
        "custom_urgent_at": now, "custom_urgent_by": frappe.session.user,
        "custom_urgent_reason": (reason or "").strip()[:140],
    }, update_modified=True)
    frappe.get_doc("Sales Order", order).add_comment(
        "Comment", "Urgent: pushed to the front of the pick queue"
                   + (f" — {reason.strip()}" if (reason or "").strip() else "")
                   + f" · by {frappe.session.user}")
    told = _ring_floor(order, reason)
    frappe.db.commit()
    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
        frappe.cache().delete_value(k)
    frappe.cache().delete_keys("lp_suggest")
    return {"ok": True, "order": order, "at": str(now)[:19], "told": told}


@frappe.whitelist(methods=["POST"])
def clear_urgent(order):
    """Take the flag off — the customer was called back, or it was a
    mistake. A flag nobody can remove stops being read."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in _URGENT_ROLES + ("dispatcher",):
        frappe.throw("Not authorized.", frappe.PermissionError)
    from logistics_portal.api.utils import resolve_order
    order = resolve_order(order)
    if not order or frappe.db.get_value("Sales Order", order, "company") != "Justyol Morocco":
        frappe.throw("Unknown order.")
    if not _urgent_ready():
        return {"ok": True}
    frappe.db.set_value("Sales Order", order, {
        "custom_urgent_at": None, "custom_urgent_by": "",
        "custom_urgent_reason": "",
    }, update_modified=True)
    frappe.get_doc("Sales Order", order).add_comment(
        "Comment", f"Urgent: cleared · by {frappe.session.user}")
    frappe.db.commit()
    frappe.cache().delete_keys("lp_suggest")
    return {"ok": True}


def drop_urgent_on_ship(doc, method=None):
    """The flag dies when the parcel leaves. Hooked on Sales Order update so
    nobody has to remember: an urgent badge on a shipped order is noise, and
    noise on a priority is how the floor stops believing the next one."""
    try:
        if not _urgent_ready() or not doc.get("custom_urgent_at"):
            return
        if (doc.get("custom_logistics_status") or "") in ("", "Pending"):
            return
        doc.db_set("custom_urgent_at", None, update_modified=False)
        doc.db_set("custom_urgent_by", "", update_modified=False)
        doc.db_set("custom_urgent_reason", "", update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "orders.drop_urgent_on_ship")


def drop_stale_urgent():
    """Clear urgent flags on parcels that already moved on. Scheduled, because
    the hook above cannot do it.

    `drop_urgent_on_ship` is wired to Sales Order `on_update`, which only fires
    on a real `doc.save()` — the Desk path. Almost nothing else takes it: the
    logistics status is written with `db_set` and with raw UPDATE statements in
    this app's own picking code, and by the carrier integration outside it,
    none of which run document hooks. The result was measured on 2026-09-23:
    two of the nine live flags were sitting on parcels that had already left,
    one of them shipped. That is precisely the noise the flag was built to
    avoid — a badge on a parcel the warehouse cannot hurry teaches the floor
    to ignore the next one.

    Direct SQL on purpose: this must not re-enter the hook it exists to
    replace, and the flag column is indexed (lp_so_urgent_idx)."""
    try:
        if not _urgent_ready():
            return 0
        stale = """custom_urgent_at IS NOT NULL
               AND (COALESCE(custom_logistics_status, '') NOT IN ('', 'Pending')
                    OR COALESCE(custom_sales_status, '') = 'Cancelled'
                    OR docstatus = 2)"""
        cleared = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabSales Order` WHERE {stale}")[0][0]
        if not cleared:
            return 0
        frappe.db.sql(f"""
            UPDATE `tabSales Order`
               SET custom_urgent_at = NULL,
                   custom_urgent_by = '',
                   custom_urgent_reason = ''
             WHERE {stale}""")
        frappe.db.commit()
        frappe.cache().delete_keys("lp_suggest")
        return int(cleared or 0)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "orders.drop_stale_urgent")
        return 0


def drop_callback_when_done(doc, method=None):
    """A call-back timer outlives its reason unless somebody clears it.

    Nothing ever did: 73 of the 159 due call-backs were parcels that had
    already been delivered, the oldest set on 30 July and still ringing
    eight weeks later. The queue's filter now hides them, but a filter only
    hides — this stops them being carried at all, so the list stays honest
    on its own rather than by being cleaned up in front of the reader."""
    try:
        if not doc.get("custom_next_call_at"):
            return
        done = ((doc.get("custom_logistics_status") or "") in ("Delivered", "Returned")
                or (doc.get("custom_track_shipment_status") or "")
                in ("Delivered", "Return", "Returned"))
        if not done:
            return
        doc.db_set("custom_next_call_at", None, update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "orders.drop_callback_when_done")
