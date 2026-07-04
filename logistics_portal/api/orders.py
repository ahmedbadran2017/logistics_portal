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
def board(stage="to_pick", track=None, limit=50):
    """Counts for every stage + rows for the requested stage."""
    limit = min(int(limit), 100)
    try:
        counts, shipped_tracks, attention = _board_counts()
        rows = _board_rows(stage, track, limit)
        return {"counts": counts, "shippedTracks": shipped_tracks,
                "attention": attention, "rows": rows, "stage": stage}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.orders.board")
        return {}


def _board_counts():
    w, dw = _win(BOARD_WINDOW_DAYS), _win(DONE_WINDOW_DAYS)

    # Status-level counts among Confirmed orders (one cheap grouped pass).
    st = {r.s: int(r.c) for r in frappe.db.sql(
        """SELECT custom_logistics_status s, COUNT(*) c FROM `tabSales Order`
           WHERE docstatus=1 AND custom_sales_status='Confirmed' AND creation >= %s
           GROUP BY custom_logistics_status""", (w,), as_dict=True)}

    # Split 'Pending' into to_pick / picking via Pick List existence.
    pend = frappe.db.sql(
        """SELECT
             SUM(CASE WHEN pl.sales_order IS NULL THEN 1 ELSE 0 END) no_pl,
             SUM(CASE WHEN pl.docstatus = 0 THEN 1 ELSE 0 END) pl_draft
           FROM `tabSales Order` so
           LEFT JOIN (SELECT pli.sales_order, MAX(p.docstatus) docstatus
                      FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name=pli.parent
                      WHERE p.creation >= %s GROUP BY pli.sales_order) pl
             ON pl.sales_order = so.name
           WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
             AND so.custom_logistics_status='Pending' AND so.creation >= %s""",
        (w, w), as_dict=True)[0]

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

    counts = {
        "to_pick": int(pend.no_pl or 0),
        "picking": int(pend.pl_draft or 0),
        "prepared": st.get("Label Generated", 0),
        "ready": st.get("Label Printed", 0),
        "shipped": st.get("Shipped", 0),
        "delivered": frappe.db.count("Sales Order", {
            "docstatus": 1, "custom_sales_status": "Confirmed",
            "custom_logistics_status": "Delivered", "creation": [">=", dw]}),
        "to_return": max(0, int(ret.total or 0) - received),
        "returned": received,
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
    return counts, tracks, attention


_SO_FIELDS = """so.name, so.customer_name, so.grand_total, so.custom_channel,
    so.custom_items_count, so.custom_awb, so.custom_label_url, so.custom_shipping_city,
    so.custom_track_shipment_status, so.creation, so.modified"""


def _row(r, **extra):
    from frappe.utils import time_diff_in_seconds, now_datetime
    age = max(0, int(time_diff_in_seconds(now_datetime(), r.modified) // 60))
    return dict({
        "no": r.name, "customer": r.customer_name, "total": r.grand_total or 0,
        "channel": (r.custom_channel or "").lower() or "manual",
        "items": r.custom_items_count or 1, "city": r.get("custom_shipping_city") or "",
        "awb": r.custom_awb or "", "labelUrl": r.get("custom_label_url") or "",
        "track": r.custom_track_shipment_status or "", "ageMins": age,
    }, **extra)


def _board_rows(stage, track, limit):
    w, dw = _win(BOARD_WINDOW_DAYS), _win(DONE_WINDOW_DAYS)
    pl_join = """LEFT JOIN (SELECT pli.sales_order, MAX(p.name) pl, MAX(p.docstatus) pl_ds,
                        MAX(p.custom_assigned_picker) picker
                 FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name=pli.parent
                 GROUP BY pli.sales_order) pl ON pl.sales_order = so.name"""

    if stage == "to_pick":
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS} FROM `tabSales Order` so {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.sales_order IS NULL
              AND so.creation >= %s ORDER BY so.creation ASC LIMIT {limit}""", (w,), as_dict=True)
        return [_row(r) for r in rows]

    if stage == "picking":
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS}, pl.pl, pl.picker FROM `tabSales Order` so {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.pl_ds = 0
              AND so.creation >= %s ORDER BY so.modified DESC LIMIT {limit}""", (w,), as_dict=True)
        return [_row(r, pl=r.pl, picker=r.picker) for r in rows]

    if stage in ("prepared", "ready"):
        status = "Label Generated" if stage == "prepared" else "Label Printed"
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS}, pl.pl, pl.picker FROM `tabSales Order` so {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status=%s AND so.creation >= %s
            ORDER BY so.modified ASC LIMIT {limit}""", (status, w), as_dict=True)
        return [_row(r, pl=r.pl, picker=r.picker) for r in rows]

    if stage == "shipped":
        cond, args = "", [w]
        if track == "none":
            cond = "AND (so.custom_track_shipment_status IS NULL OR so.custom_track_shipment_status='')"
        elif track:
            cond = "AND so.custom_track_shipment_status = %s"
            args.append(track)
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS}, sh.sh FROM `tabSales Order` so
            LEFT JOIN (SELECT dni.against_sales_order so_name, MAX(sdn.parent) sh
                       FROM `tabDelivery Note Item` dni
                       JOIN `tabShipment Delivery Note` sdn ON sdn.delivery_note = dni.parent
                       GROUP BY dni.against_sales_order) sh ON sh.so_name = so.name
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Shipped' AND so.creation >= %s {cond}
            ORDER BY so.modified ASC LIMIT {limit}""", tuple(args), as_dict=True)
        return [_row(r, sh=r.sh) for r in rows]

    if stage == "delivered":
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS} FROM `tabSales Order` so
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Delivered' AND so.creation >= %s
            ORDER BY so.modified DESC LIMIT {limit}""", (dw,), as_dict=True)
        return [_row(r) for r in rows]

    if stage in ("to_return", "returned"):
        cond = "AND (dn.ret IS NOT NULL AND dn.ret != '')" if stage == "returned" \
            else "AND (dn.ret IS NULL OR dn.ret = '')"
        rows = frappe.db.sql(f"""SELECT {_SO_FIELDS}, dn.ret, dn.dn FROM `tabSales Order` so
            LEFT JOIN (SELECT dni.against_sales_order so_name, MAX(d.custom_return_shipment) ret,
                              MAX(d.name) dn
                       FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name=dni.parent
                       WHERE d.docstatus=1 GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Returned' AND so.creation >= %s {cond}
            ORDER BY so.modified ASC LIMIT {limit}""", (dw,), as_dict=True)
        return [_row(r, ret=r.ret, dn=r.dn) for r in rows]

    if stage == "attention":
        out = []
        for r in frappe.db.sql(f"""SELECT {_SO_FIELDS}, pl.pl, pl.picker, 'cancelled_midflow' kind
            FROM `tabSales Order` so {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Cancelled'
              AND so.custom_logistics_status NOT IN ('Delivered','Returned')
              AND pl.pl IS NOT NULL AND so.creation >= %s
            ORDER BY so.modified DESC LIMIT 30""", (dw,), as_dict=True):
            out.append(_row(r, pl=r.pl, picker=r.picker, kind="cancelled_midflow"))
        for r in frappe.db.sql(f"""SELECT {_SO_FIELDS}, pl.pl, pl.picker, 'no_awb' kind
            FROM `tabSales Order` so {pl_join}
            WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
              AND so.custom_logistics_status='Pending' AND pl.pl_ds = 1
              AND (so.custom_awb IS NULL OR so.custom_awb='') AND so.creation >= %s
            ORDER BY so.modified DESC LIMIT 30""", (dw,), as_dict=True):
            out.append(_row(r, pl=r.pl, picker=r.picker, kind="no_awb"))
        for r in frappe.db.sql(f"""SELECT {_SO_FIELDS}, 'sync_lag' kind FROM `tabSales Order` so
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


@frappe.whitelist()
def detail(name):
    """Full order detail for the shared OrderDetail screen."""
    name = (name or "").lstrip("#")
    if not frappe.db.exists("Sales Order", name):
        return {}
    so = frappe.get_doc("Sales Order", name)
    return {
        "name": "#" + so.name,
        "customer": so.customer_name,
        "channel": so.get("custom_channel"),
        "total": so.grand_total,
        "stage": so.get("custom_logistics_status") or "Pending",
        "awb": so.get("custom_awb"),
        "tracking_status": so.get("custom_track_shipment_status"),
        "tracking_company": so.get("custom_tracking_company") or "Cathedis",
        "picked_at": so.get("custom_picked_at"),
        "labeled_at": so.get("custom_labeled_at"),
        "shipped_at": so.get("custom_shipped_at"),
        "delivered_at": so.get("custom_delivered_at"),
    }
