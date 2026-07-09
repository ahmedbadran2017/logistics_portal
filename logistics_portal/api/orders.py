"""Sales Order stage timestamps + order detail."""

import frappe
from frappe.utils import now_datetime

# Which custom_*_at field each logistics status stamps (first time it is reached).
STAGE_STAMP = {
    "Picked": "custom_picked_at",
    "Label Generated": "custom_labeled_at",
    "Label Printed": "custom_labeled_at",
    "Shipped": "custom_shipped_at",
    "Delivered": "custom_delivered_at",
}


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
def board(stage="to_pick", track=None, limit=50, q=None, offset=0, city=None, sort=None, dates=None, pick=None):
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
            }), expires_in_sec=300)

        facet_key = f"lp_board_cities:{stage}:{track or ''}"
        cached_facet = cache.get_value(facet_key)
        if cached_facet:
            cities = _json.loads(cached_facet)
        else:
            cities = _city_facet(stage, track)
            cache.set_value(facet_key, _json.dumps(cities), expires_in_sec=600)

        # To-Pick splits by locally-pickable stock: Ready / Partial / OOS.
        pick_avail = pick_buckets = pick_names = None
        if stage == "to_pick":
            pick_avail = _pick_availability()
            pick_buckets = {k: len(pick_avail[k]) for k in ("ready", "partial", "oos")}
            if pick in ("ready", "partial", "oos"):
                pick_names = pick_avail[pick]

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
        resp = {"counts": counts, "values": values, "shippedTracks": shipped_tracks,
                "attention": attention, "rows": rows, "cities": cities,
                "total": total, "stage": stage, "serverNow": str(now_datetime())[:16]}
        if pick_buckets is not None:
            resp["pickBuckets"] = pick_buckets
            if pick in ("partial", "oos"):
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
        cond = "AND (dn.ret IS NOT NULL AND dn.ret != '')" if stage == "returned" \
            else "AND (dn.ret IS NULL OR dn.ret = '')"
        joins = addr + """ LEFT JOIN (SELECT dni.against_sales_order so_name,
                MAX(d.custom_return_shipment) ret
            FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name=dni.parent
            WHERE d.docstatus=1 GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name"""
        where = f"{base} AND so.custom_logistics_status='Returned' AND so.creation >= %s {cond}"
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
    where += _date_cond(dates, args)
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
             SUM(CASE WHEN dn.ret IS NOT NULL AND dn.ret != '' THEN 1 ELSE 0 END) received,
             COUNT(*) total
           FROM `tabSales Order` so
           LEFT JOIN (SELECT dni.against_sales_order so_name, MAX(d.custom_return_shipment) ret
                      FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name=dni.parent
                      WHERE d.docstatus=1 GROUP BY dni.against_sales_order) dn
             ON dn.so_name = so.name
           WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
             AND so.custom_logistics_status='Returned' AND so.creation >= %s""",
        (dw,), as_dict=True)[0]
    received = int(ret.received or 0)

    # How many To Pick orders already missed today's 14:00 same-day cutoff.
    from frappe.utils import now_datetime, nowdate
    _now = now_datetime()
    cutoff_dt = f"{nowdate()} 14:00:00" if str(_now)[11:16] >= "14:00" else f"{nowdate()} 00:00:00"
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
            """SELECT COUNT(DISTINCT so.name) FROM `tabSales Order` so
               JOIN `tabPick List Item` pli ON pli.sales_order = so.name
               WHERE so.docstatus=1 AND so.custom_sales_status='Cancelled'
                 AND so.custom_logistics_status NOT IN ('Delivered','Returned')
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


def _date_cond(dates, args):
    """dates: today | yesterday | 7d | 30d — anchored to server date."""
    from frappe.utils import nowdate, add_days
    if not dates:
        return ""
    if dates == "today":
        args.append(nowdate()); return " AND DATE(so.creation) = %s"
    if dates == "yesterday":
        args.append(add_days(nowdate(), -1)); return " AND DATE(so.creation) = %s"
    if dates in ("7d", "30d"):
        args.append(add_days(nowdate(), -int(dates[:-1]))); return " AND so.creation >= %s"
    return ""


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
    }, **extra)


# Locally-pickable stock: any "- JM" warehouse with qty (incl. Slow/Receiving/
# Return zones — returned stock IS resold per ops), excluding Turkey/transit/
# containers/defective/correcting/old. Patterns are params (no literal % in the
# SQL) so this splices safely into queries that also carry %s args.
def _pickable_bin_subquery():
    sql = ("SELECT DISTINCT item_code FROM `tabBin` b WHERE b.actual_qty > 0 "
           "AND b.warehouse LIKE %s AND b.warehouse NOT LIKE %s "
           "AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s "
           "AND b.warehouse NOT LIKE %s AND b.warehouse NOT LIKE %s")
    args = ["% - JM", "Defective%", "Container%", "Air Freight%", "%Old%", "CORRECTING%"]
    return sql, args


def _pick_availability():
    """Stock split of the current To-Pick pool, cached 120s.
    {"ready":[so], "partial":[so], "oos":[so], "missing":{so:[item_name,...]}}."""
    import json as _json
    cache = frappe.cache()
    cached = cache.get_value("lp_pick_avail")
    if cached:
        return _json.loads(cached)
    w = _win(BOARD_WINDOW_DAYS)
    pk_sql, pk_args = _pickable_bin_subquery()
    try:
        rows = frappe.db.sql(f"""
            SELECT so.name AS so,
                   COALESCE(NULLIF(soi.item_name,''), soi.item_code) AS item_name,
                   MAX(CASE WHEN pk.item_code IS NOT NULL THEN 1 ELSE 0 END) AS avail
            FROM `tabSales Order` so
            JOIN `tabSales Order Item` soi ON soi.parent = so.name
            LEFT JOIN ({pk_sql}) pk ON pk.item_code = soi.item_code
            LEFT JOIN (SELECT pli.sales_order FROM `tabPick List Item` pli
                       JOIN `tabPick List` p ON p.name=pli.parent
                       WHERE p.docstatus < 2 GROUP BY pli.sales_order) pl ON pl.sales_order = so.name
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.sales_order IS NULL
              AND so.creation >= %s
            GROUP BY so.name, soi.item_code, item_name""",
            tuple(pk_args) + (w,), as_dict=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal._pick_availability")
        return {"ready": [], "partial": [], "oos": [], "missing": {}}

    per = {}
    for r in rows:
        d = per.setdefault(r.so, {"n": 0, "avail": 0, "missing": []})
        d["n"] += 1
        if r.avail:
            d["avail"] += 1
        elif len(d["missing"]) < 6:
            d["missing"].append(r.item_name)
    ready, partial, oos, missing = [], [], [], {}
    for name, d in per.items():
        if d["avail"] >= d["n"]:
            ready.append(name)
        elif d["avail"] == 0:
            oos.append(name); missing[name] = d["missing"]
        else:
            partial.append(name); missing[name] = d["missing"]
    out = {"ready": ready, "partial": partial, "oos": oos, "missing": missing}
    cache.set_value("lp_pick_avail", _json.dumps(out), expires_in_sec=120)
    return out


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
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _date_cond(dates, args)
        pc = ""
        if pick_names is not None:
            if not pick_names:
                return []
            pc = " AND so.name IN (%s)" % ", ".join(["%s"] * len(pick_names))
            args.extend(pick_names)
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS} FROM `tabSales Order` so {addr} {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.sales_order IS NULL
              AND so.creation >= %s {qc} {cc} {dc}{pc} ORDER BY {_order_by(sort, 'so.creation ASC')} LIMIT {limit} OFFSET {offset}""",
            tuple(args), as_dict=True)
        return [_row(r) for r in rows]

    if stage == "picking":
        args = [w]
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _date_cond(dates, args)
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS}, pl.pl, pl.picker, pl.pl_owner
            FROM `tabSales Order` so {addr} {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.pl_ds = 0
              AND so.creation >= %s {qc} {cc} {dc} ORDER BY {_order_by(sort, 'so.modified DESC')} LIMIT {limit} OFFSET {offset}""",
            tuple(args), as_dict=True)
        return [_row(r, pl=r.pl, picker=r.picker or r.pl_owner) for r in rows]

    if stage in ("prepared", "ready"):
        statuses = ["Label Generated", "Picked", "In transit", "Received"] \
            if stage == "prepared" else ["Label Printed"]
        ph = ", ".join(["%s"] * len(statuses))
        args = statuses + [w]
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _date_cond(dates, args)
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS}, pl.pl, pl.picker, pl.pl_owner
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
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _date_cond(dates, args)
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS}, sh.sh FROM `tabSales Order` so {addr}
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
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _date_cond(dates, args)
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS} FROM `tabSales Order` so {addr}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Delivered' AND so.creation >= %s {qc} {cc}
            ORDER BY so.modified DESC LIMIT {limit} OFFSET {offset}""", tuple(args), as_dict=True)
        return [_row(r) for r in rows]

    if stage in ("to_return", "returned"):
        cond = "AND (dn.ret IS NOT NULL AND dn.ret != '')" if stage == "returned" \
            else "AND (dn.ret IS NULL OR dn.ret = '')"
        args = [dw]
        qc = _q_cond(q, args); cc = _city_cond(city, args); dc = _date_cond(dates, args)
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS}, dn.ret, dn.dn FROM `tabSales Order` so {addr}
            LEFT JOIN (SELECT dni.against_sales_order so_name, MAX(d.custom_return_shipment) ret,
                              MAX(d.name) dn
                       FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name=dni.parent
                       WHERE d.docstatus=1 GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Returned' AND so.creation >= %s {cond} {qc} {cc} {dc}
            ORDER BY {_order_by(sort, 'so.modified ASC')} LIMIT {limit} OFFSET {offset}""", tuple(args), as_dict=True)
        return [_row(r, ret=r.ret, dn=r.dn) for r in rows]

    if stage == "attention":
        out = []
        for r in frappe.db.sql(f"""SELECT {_SO_FIELDS}, pl.pl, pl.picker, 'cancelled_midflow' kind
            FROM `tabSales Order` so {addr} {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Cancelled'
              AND so.custom_logistics_status NOT IN ('Delivered','Returned')
              AND pl.pl IS NOT NULL AND so.creation >= %s
            ORDER BY so.modified DESC LIMIT 30""", (dw,), as_dict=True):
            out.append(_row(r, pl=r.pl, picker=r.picker, kind="cancelled_midflow"))
        for r in frappe.db.sql(f"""SELECT {_SO_FIELDS}, pl.pl, pl.picker, 'no_awb' kind
            FROM `tabSales Order` so {addr} {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.pl_ds = 1
              AND (so.custom_awb IS NULL OR so.custom_awb='') AND so.creation >= %s
            ORDER BY so.modified DESC LIMIT 30""", (dw,), as_dict=True):
            out.append(_row(r, pl=r.pl, picker=r.picker, kind="no_awb"))
        for r in frappe.db.sql(f"""SELECT {_SO_FIELDS}, 'sync_lag' kind FROM `tabSales Order` so {addr}
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


@frappe.whitelist()
def list(scope="floor", picker=None, limit=60):
    """Recent orders in the SPA's ORDERS shape (Pipeline + Picker queue).
    scope='queue' narrows to pick-ready stages; `picker` filters to that user's
    assigned pick lists."""
    limit = int(limit)
    statuses = (
        ["Pending", "Picked"] if scope == "queue"
        else ["Pending", "Picked", "In transit", "Received", "Label Generated", "Label Printed", "Shipped"]
    )
    try:
        rows = frappe.get_all(
            "Sales Order",
            filters={"docstatus": 1, "custom_logistics_status": ["in", statuses]},
            fields=[
                "name", "customer_name", "grand_total", "custom_channel",
                "custom_logistics_status", "custom_items_count", "custom_awb", "creation",
            ],
            order_by="modified desc",
            limit=limit,
        )
        out = []
        for r in rows:
            pl = _pick_meta(r.name)
            if picker and pl.get("picker_email") != picker:
                continue
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


@frappe.whitelist()
def detail(name):
    """Full order detail for the shared OrderDetail screen."""
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
        """SELECT soi.item_code sku, soi.item_name name, soi.qty, soi.rate price,
                  soi.amount line, soi.warehouse bin, i.image
           FROM `tabSales Order Item` soi
           LEFT JOIN `tabItem` i ON i.name = soi.item_code
           WHERE soi.parent = %s ORDER BY soi.idx""",
        (name,), as_dict=True)

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
        "created": str(so.creation)[:16],
        # money — the real ERPNext numbers, not derived
        "subtotal": so.total,
        "discount": so.discount_amount or 0,
        "taxes": so.total_taxes_and_charges or 0,
        "total": so.grand_total,
        "sales_status": so.get("custom_sales_status") or "",
        "payment_collection": so.get("custom_payment_collection") or "",
        "stage": so.get("custom_logistics_status") or "Pending",
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
