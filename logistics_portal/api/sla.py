"""SLA engine — populates the currently-empty SLA fields on Delivery Notes.

Runs every 15 min (hooks.py). Computes expected delivery date + custom_sla_status
+ custom_sla_days_remaining from stage timestamps. Thresholds come from the
`Logistics SLA Settings` single (created on first run with sane defaults).
"""

import frappe
from frappe.utils import add_days, nowdate

_CO = "Justyol Morocco"
DEFAULT_DELIVERY_DAYS = 3  # Casablanca metro default; region overrides later.


def _delivery_days():
    if frappe.db.exists("DocType", "Logistics SLA Settings"):
        v = frappe.db.get_single_value("Logistics SLA Settings", "default_delivery_days")
        if v:
            return int(v)
    from logistics_portal.api.settings import get_ops
    return int(get_ops("slaDays") or DEFAULT_DELIVERY_DAYS)


def run_sla_engine():
    """Scheduled: refresh SLA state on in-flight Delivery Notes."""
    meta = frappe.get_meta("Delivery Note")
    if not meta.has_field("custom_sla_status"):
        return

    days = _delivery_days()
    # Scope to the recent operational window — historical DNs are archive, not
    # "breached now". Also clear any stale SLA status the engine may have set on
    # old documents (one-time cleanup, cheap when nothing matches).
    from frappe.utils import add_days as _add_days
    window_start = _add_days(nowdate(), -14)
    # custom_sla_days_remaining is an Int custom field, and Frappe creates Int
    # columns NOT NULL DEFAULT 0. Writing NULL into it raised IntegrityError
    # 1048 on the FIRST statement of the engine, so nothing after this line
    # ever ran: 687 failed runs, zero successes, and 4,493 of the 4,494
    # delivery notes in the window with no SLA status at all. The board read
    # "0 on time, 0 late" and looked like a quiet fortnight.
    # Each pass is run on its own. One statement failing used to take the
    # whole engine with it — and did, 687 times — so a single bad row or a
    # column that will not take a value can now cost that pass and nothing
    # else. The failure is logged with the pass that caused it, instead of a
    # traceback that says only "run_sla_engine".
    def _pass(label, sql, args):
        try:
            frappe.db.sql(sql, args)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback()[:3000],
                             f"logistics_portal.sla.{label}")

    _pass("clear_stale", """UPDATE `tabDelivery Note`
           SET custom_sla_status = '', custom_sla_days_remaining = 0
           WHERE posting_date < %s
             AND custom_sla_status IN ('Breached', 'At Risk', 'On Track')""",
          (window_start,))

    # 1) Every windowed DN gets an expected date.
    _pass("expected_date", """UPDATE `tabDelivery Note`
           SET custom_expected_delivery_date = DATE_ADD(posting_date, INTERVAL %s DAY)
           WHERE docstatus = 1 AND posting_date >= %s
             AND custom_expected_delivery_date IS NULL""",
          (days, window_start))

    # 2) Terminal transitions — evaluated ONCE, then never reprocessed. This
    # also fixes the old bug where an on-time delivery flipped to 'Delivered
    # Late' whenever the engine looked at it again after the expected date.
    _pass("delivered", """UPDATE `tabDelivery Note`
           SET custom_sla_days_remaining = DATEDIFF(custom_expected_delivery_date, CURDATE()),
               custom_sla_status = IF(custom_expected_delivery_date >= CURDATE(),
                                      'Delivered', 'Delivered Late')
           WHERE docstatus = 1 AND posting_date >= %s
             AND custom_track_shipment_status = 'Delivered'
             AND COALESCE(custom_sla_status,'') NOT IN ('Delivered','Delivered Late')""",
          (window_start,))

    _pass("returned", """UPDATE `tabDelivery Note`
           SET custom_sla_status = 'Returned'
           WHERE docstatus = 1 AND posting_date >= %s
             AND custom_track_shipment_status IN ('Return','Returned')
             AND COALESCE(custom_sla_status,'') != 'Returned'""",
          (window_start,))

    # 3) Everything still in flight: recompute remaining + bucket.
    _pass("in_flight", """UPDATE `tabDelivery Note`
           SET custom_sla_days_remaining = DATEDIFF(custom_expected_delivery_date, CURDATE()),
               custom_sla_status = CASE
                   WHEN DATEDIFF(custom_expected_delivery_date, CURDATE()) < 0 THEN 'Breached'
                   WHEN DATEDIFF(custom_expected_delivery_date, CURDATE()) <= 1 THEN 'At Risk'
                   ELSE 'On Track' END
           WHERE docstatus = 1 AND posting_date >= %s
             AND COALESCE(custom_track_shipment_status,'')
                 NOT IN ('Delivered','Return','Returned')
             AND COALESCE(custom_sla_status,'')
                 NOT IN ('Delivered','Delivered Late','Returned')""",
          (window_start,))


def same_day_counts(since, until=None):
    """Parcels shipped, and how many left the same day the order arrived.

    THE definition of same-day for the whole portal. The cockpit had its own —
    _sla_hit_rate, which counted delivery notes whose custom_sla_status reads
    'On Track' or 'Delivered' — so the two screens answered the same question
    differently: 38.8% on the SLA board and 0% on the cockpit, the latter only
    because the SLA engine had never written a status. Two numbers under one
    name is worse than no number.

    Parcel grain (COUNT DISTINCT dn): the DN Item join fans out one row per
    line, and without the DISTINCT the rate is weighted by basket size.
    """
    cond, args = "sh.pickup_date >= %s", [since]
    if until:
        cond += " AND sh.pickup_date <= %s"
        args.append(until)
    return frappe.db.sql(
        f"""SELECT COUNT(DISTINCT sdn.delivery_note) total,
                   COUNT(DISTINCT CASE WHEN so.creation >= sh.pickup_date
                             AND so.creation < sh.pickup_date + INTERVAL 1 DAY
                       THEN sdn.delivery_note END) same_day
            FROM `tabShipment Delivery Note` sdn
            JOIN `tabShipment` sh ON sh.name = sdn.parent AND sh.docstatus = 1
            JOIN `tabDelivery Note Item` dni ON dni.parent = sdn.delivery_note
            JOIN `tabSales Order` so ON so.name = dni.against_sales_order
            WHERE {cond}""", tuple(args), as_dict=True)[0]


@frappe.whitelist()
def inside_day(frm=None, to=None):
    """How the floor actually performed, hour by hour, for a chosen day.

    The SLA board measures the CARRIER's promise. This measures OURS: what
    happened between the order being confirmed and the parcel leaving, which
    is the only part the warehouse controls.

    Measured over 6,391 orders in 30 days, the split matters more than the
    total:
        confirmed -> on a pick list   median 14.0h   p75 25.6h   p90 46.3h
        pick list -> carrier label    median   41m   p75  1.8h   p90  4.5h
        end to end                    median 15.6h   p75 29.7h   p90 49.6h
    The floor does its work in 41 minutes. Nearly the whole cycle is the
    order WAITING to be put on a list. A single "internal SLA" number would
    have buried that, so the two clocks are reported apart.
    """
    from logistics_portal.api.auth import resolve_role
    if not resolve_role(frappe.session.user):
        frappe.throw("Not authorized.", frappe.PermissionError)
    frm = (frm or nowdate())[:10]
    to = (to or frm)[:10]

    # Per-hour flow: what arrived, what was picked, what was labelled, and what
    # left. Hour of the EVENT, so a bar says "in this hour the floor did this".
    def _hourly(sql, args):
        out = {}
        for r in frappe.db.sql(sql, args, as_dict=True):
            out[int(r.h)] = int(r.n or 0)
        return out

    orders_in = _hourly(
        """SELECT HOUR(creation) h, COUNT(*) n FROM `tabSales Order`
           WHERE company = %s AND docstatus = 1
             AND custom_sales_status = 'Confirmed'
             AND DATE(creation) BETWEEN %s AND %s GROUP BY HOUR(creation)""",
        (_CO, frm, to))
    picked = _hourly(
        """SELECT HOUR(p.creation) h, COUNT(DISTINCT pli.sales_order) n
           FROM `tabPick List` p JOIN `tabPick List Item` pli ON pli.parent = p.name
           WHERE p.docstatus < 2 AND DATE(p.creation) BETWEEN %s AND %s
           GROUP BY HOUR(p.creation)""", (frm, to))
    labelled = _hourly(
        """SELECT HOUR(creation) h, COUNT(DISTINCT attached_to_name) n
           FROM `tabFile` WHERE attached_to_doctype = 'Sales Order'
             AND file_name LIKE '%%Cathedis_Label%%'
             AND DATE(creation) BETWEEN %s AND %s GROUP BY HOUR(creation)""",
        (frm, to))
    shipped = _hourly(
        """SELECT HOUR(d.creation) h, COUNT(*) n FROM `tabDelivery Note` d
           WHERE d.docstatus = 1 AND d.company = %s
             AND DATE(d.creation) BETWEEN %s AND %s GROUP BY HOUR(d.creation)""",
        (_CO, frm, to))

    hours = [{"h": h, "in": orders_in.get(h, 0), "picked": picked.get(h, 0),
              "labelled": labelled.get(h, 0), "shipped": shipped.get(h, 0)}
             for h in range(24)]

    # The two clocks, for orders CONFIRMED in the chosen window. Percentiles,
    # not averages: one order stuck for ten days moves a mean and tells the
    # floor nothing about its day.
    rows = frappe.db.sql(
        """SELECT TIMESTAMPDIFF(MINUTE, so.creation, pl.started) wait,
                  TIMESTAMPDIFF(MINUTE, pl.started, f.lbl) work,
                  TIMESTAMPDIFF(MINUTE, so.creation, f.lbl) total
           FROM `tabSales Order` so
           JOIN (SELECT pli.sales_order so, MIN(p.creation) started
                 FROM `tabPick List Item` pli
                 JOIN `tabPick List` p ON p.name = pli.parent
                 WHERE p.docstatus < 2 GROUP BY pli.sales_order) pl ON pl.so = so.name
           JOIN (SELECT attached_to_name so, MIN(creation) lbl FROM `tabFile`
                 WHERE attached_to_doctype = 'Sales Order'
                   AND file_name LIKE '%%Cathedis_Label%%'
                 GROUP BY attached_to_name) f ON f.so = so.name
           WHERE so.company = %s AND so.docstatus = 1
             AND DATE(so.creation) BETWEEN %s AND %s""",
        (_CO, frm, to), as_dict=True)

    def _pct(key):
        v = sorted(int(r[key]) for r in rows
                   if r[key] is not None and 0 <= int(r[key]) <= 60 * 24 * 14)
        if not v:
            return None
        pick = lambda q: v[min(len(v) - 1, int(len(v) * q))]
        return {"n": len(v), "median": pick(.5), "p75": pick(.75), "p90": pick(.9)}

    from logistics_portal.api.settings import get_ops
    cutoff = str(get_ops("cutoff") or "14:00")
    before, after = 0, 0
    for r in frappe.db.sql(
            """SELECT TIME(creation) t FROM `tabSales Order`
               WHERE company = %s AND docstatus = 1
                 AND custom_sales_status = 'Confirmed'
                 AND DATE(creation) BETWEEN %s AND %s""", (_CO, frm, to)):
        if str(r[0])[:5] <= cutoff:
            before += 1
        else:
            after += 1

    return {"frm": frm, "to": to, "hours": hours, "cutoff": cutoff,
            "beforeCutoff": before, "afterCutoff": after,
            "wait": _pct("wait"), "work": _pct("work"), "total": _pct("total"),
            "sameDay": same_day_counts(frm, to)}


@frappe.whitelist()
def board(days=14):
    """Everything the SLA screen shows, all real, one call:
    status mix, on-time delivery rate, same-day-ship rate, days-remaining
    buckets for open parcels, worst cities, and the open-breach list."""
    from logistics_portal.api.auth import resolve_role
    if not resolve_role(frappe.session.user):
        frappe.throw("Not authorized.", frappe.PermissionError)
    days = min(max(int(days or 14), 1), 60)
    since = add_days(nowdate(), -days)

    counts = {}
    for r in frappe.db.sql(
        """SELECT COALESCE(custom_sla_status,'') s, COUNT(*) c
           FROM `tabDelivery Note`
           WHERE docstatus = 1 AND posting_date >= %s
           GROUP BY COALESCE(custom_sla_status,'')""", (since,), as_dict=True):
        counts[r.s or "none"] = int(r.c or 0)
    delivered = counts.get("Delivered", 0)
    late = counts.get("Delivered Late", 0)
    on_time_pct = round(delivered * 100.0 / max(1, delivered + late), 1)

    # Same-day ship: parcels whose order arrived the same day the manifest left.
    # PARCEL grain (COUNT DISTINCT dn): the DN Item join fans out one row per
    # line, so this rate was weighted by basket size — the same bug already
    # fixed in confirmation/contact_center/customers, still live here.
    sd = same_day_counts(since)
    same_day_pct = round(int(sd.same_day or 0) * 100.0 / max(1, int(sd.total or 0)), 1)

    # Open parcels by days remaining (negative = overdue).
    buckets = [
        {"key": "ok", "label": "> 2 days left", "count": 0},
        {"key": "soon", "label": "1–2 days left", "count": 0},
        {"key": "today", "label": "due today", "count": 0},
        {"key": "over1", "label": "1–3 days late", "count": 0},
        {"key": "over3", "label": "> 3 days late", "count": 0},
    ]
    unknown = 0
    for r in frappe.db.sql(
        """SELECT custom_sla_days_remaining d, COUNT(*) c FROM `tabDelivery Note`
           WHERE docstatus = 1 AND posting_date >= %s
             AND custom_sla_status IN ('On Track','At Risk','Breached')
           GROUP BY custom_sla_days_remaining""", (since,), as_dict=True):
        if r.d is None:
            # Unscored parcels are UNKNOWN, not "due today".
            unknown += int(r.c or 0)
            continue
        d = int(r.d)
        c = int(r.c or 0)
        i = 0 if d > 2 else 1 if d >= 1 else 2 if d == 0 else 3 if d >= -3 else 4
        buckets[i]["count"] += c

    # Parcel grain + the Address city: custom_shipping_city is filled on 0.9%
    # of orders, so this panel was ~99% '?' AND multiplied by lines per parcel.
    cities = frappe.db.sql(
        """SELECT COALESCE(NULLIF(TRIM(so.custom_shipping_city),''),
                           NULLIF(TRIM(addr.city),''), '?') city,
                  COUNT(DISTINCT dn.name) breached
           FROM `tabDelivery Note` dn
           JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
           JOIN `tabSales Order` so ON so.name = dni.against_sales_order
           LEFT JOIN `tabAddress` addr
             ON addr.name = COALESCE(so.shipping_address_name, so.customer_address)
           WHERE dn.docstatus = 1 AND dn.posting_date >= %s
             AND dn.custom_sla_status = 'Breached'
             AND COALESCE(dn.custom_track_shipment_status,'') <> 'Delivered'
           GROUP BY city ORDER BY breached DESC LIMIT 6""",
        (since,), as_dict=True)

    from logistics_portal.api.performance import breached_list
    return {
        "days": days,
        "onTimePct": on_time_pct,
        "sameDayPct": same_day_pct,
        "counts": {
            "onTrack": counts.get("On Track", 0),
            "atRisk": counts.get("At Risk", 0),
            "breached": counts.get("Breached", 0),
            "delivered": delivered,
            "deliveredLate": late,
            "returned": counts.get("Returned", 0),
            "unscored": counts.get("none", 0),
        },
        "buckets": buckets,
        "unknown": unknown,
        "cities": [{"city": (c.city or "?").title(), "breached": int(c.breached or 0)}
                   for c in cities],
        # None = the breach query FAILED — the board says "couldn't load"
        # instead of celebrating an empty list on its one critical panel.
        "breaches": breached_list(limit=8),
    }
