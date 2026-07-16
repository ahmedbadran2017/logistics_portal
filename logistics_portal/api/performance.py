"""Cockpit, team leaderboard, and personal performance aggregation.

Returns data in the exact shapes the SPA screens expect (see
frontend/src/lib/handoffData.js), so screens can swap `handoffData` for a live
`api('performance.*')` call via the `liveOr` helper.
"""

import frappe
from frappe.utils import nowdate, add_days

# ERPNext custom_logistics_status -> design pipeline key (handoffData STAGE keys).
STAGE_MAP = {
    "Pending": "pending",
    "Picked": "picked",
    "In transit": "transit",
    "Received": "labelgen",
    "Label Generated": "labelgen",
    "Label Printed": "label",
    "Shipped": "shipped",
    "Delivered": "delivered",
    "Returned": "returned",
}
# Fixed display order of the funnel (design keys).
PIPELINE_KEYS = ["pending", "picking", "picked", "labelgen", "label", "shipped", "transit", "delivered", "returned"]
# The board's document-derived stages — the cockpit funnel mirrors these so the
# manager sees the SAME numbers on the cockpit and the Orders board.
BOARD_STAGES = ["to_pick", "picking", "prepared", "ready", "shipped", "delivered", "to_return", "returned"]


def _board_summary():
    """Counts/values from the Orders board model (shared 60s cache — one source
    of truth, so cockpit and board never disagree)."""
    import json as _json
    from logistics_portal.api import orders as _orders

    cache = frappe.cache()
    cached = cache.get_value("lp_board_summary")
    if cached:
        s = _json.loads(cached)
        return s["counts"], s["values"], s["tracks"], s["attention"]
    counts, values, tracks, attention = _orders._board_counts()
    cache.set_value("lp_board_summary", _json.dumps({
        "counts": counts, "values": values, "tracks": tracks, "attention": attention,
    }), expires_in_sec=60)
    return counts, values, tracks, attention

# Known team emails -> handoffData TEAM id (so the leaderboard matches byId()).
EMAIL_TO_ID = {
    "marouaneelmessaoudi07@gmail.com": "marouane",
    "mouakkalanass@gmail.com": "anass",
    "asmaazirary7@gmail.com": "asmaa",
    "lamdanisaad12@gmail.com": "saad",
    "ossamanahila@gmail.com": "oussama",
    "saidnakri65@gmail.com": "said",
    "redazaari47@gmail.com": "reda",
}

# How many days back "the floor" spans. Tune per the team's definition of the
# active window (kept short so the cockpit reflects current work, not history).
FLOOR_DAYS = 7


@frappe.whitelist()
def cockpit(date=None):
    """Live floor snapshot in the SPA's cockpit shape: {summary, pipeline,
    leaderboard, atRisk}. The flow card is scoped to `date` (default today);
    the funnel/leaderboard/SLA alerts are always the current state."""
    try:
        from frappe.utils import getdate

        day = str(getdate(date)) if date else nowdate()
        is_today = day == nowdate()

        # Funnel = the Orders-board stage model (document-derived, cached 60s).
        counts, values, _tracks, attention = _board_summary()
        pipeline = [{"key": k, "count": int(counts.get(k, 0) or 0),
                     "value": round(float(values.get(k, 0) or 0))} for k in BOARD_STAGES]
        by = {p["key"]: p["count"] for p in pipeline}

        total = sum(p["count"] for p in pipeline)
        # ── Flow, scoped to the selected day ──
        orders_in = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSales Order` WHERE docstatus=1 AND creation >= %s AND creation < %s + INTERVAL 1 DAY",
            (day, day))[0][0] or 0
        printed = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabDelivery Note` WHERE docstatus=1 AND creation >= %s AND creation < %s + INTERVAL 1 DAY",
            (day, day))[0][0] or 0
        # Shipped that day = parcels on that day's submitted manifest(s) — real
        # and historical, unlike status counts which keep moving after the day.
        shipped_day = frappe.db.sql(
            """SELECT COUNT(*) FROM `tabShipment Delivery Note` sdn
               JOIN `tabShipment` sh ON sh.name = sdn.parent
               WHERE sh.docstatus = 1 AND sh.pickup_date >= %s AND sh.pickup_date < %s + INTERVAL 1 DAY""",
            (day, day))[0][0] or 0
        if is_today:
            to_ship = by.get("to_pick", 0) + by.get("picking", 0) + by.get("prepared", 0) + by.get("ready", 0)
            shipped = int(shipped_day) or by.get("shipped", 0)
        else:
            # For a past day: how many of that day's orders never went out.
            to_ship = frappe.db.sql(
                """SELECT COUNT(*) FROM `tabSales Order`
                   WHERE docstatus=1 AND creation >= %s AND creation < %s + INTERVAL 1 DAY
                     AND COALESCE(custom_logistics_status,'') NOT IN
                         ('Shipped','In transit','Delivered','Returned')""",
                (day, day))[0][0] or 0
            shipped = int(shipped_day)

        # ── SLA alerts: recent window, OPEN only (a delivered parcel is not
        # "needs attention now" even if it breached on the way). ──
        sla_since = add_days(nowdate(), -14)
        breaches = frappe.db.sql(
            """SELECT COUNT(*) FROM `tabDelivery Note`
               WHERE custom_sla_status='Breached' AND posting_date >= %s
                 AND COALESCE(custom_track_shipment_status,'') <> 'Delivered'""",
            (sla_since,))[0][0] or 0
        at_risk = frappe.db.sql(
            """SELECT COUNT(*) FROM `tabDelivery Note`
               WHERE custom_sla_status='At Risk' AND posting_date >= %s
                 AND COALESCE(custom_track_shipment_status,'') <> 'Delivered'""",
            (sla_since,))[0][0] or 0
        # In-transit is truest from carrier tracking on recent DNs (SO stage lags).
        in_transit = frappe.db.count(
            "Delivery Note",
            {"custom_track_shipment_status": ["in", ["In Transit", "Out For Delivery"]],
             "posting_date": [">=", sla_since]},
        ) or by.get("shipped", 0)
        # Orders created that day before the manifest cutoff (ops setting).
        from logistics_portal.api.settings import get_ops
        _cut = get_ops("cutoff")
        before_cutoff = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSales Order` WHERE docstatus=1 AND creation >= %s AND creation < CONCAT(%s, ' ', %s, ':00')",
            (day, day, _cut),
        )[0][0]

        summary = {
            "date": day,
            "isToday": is_today,
            "ordersIn": int(orders_in),
            "shipped": int(shipped),
            "printed": int(printed),
            "toShip": int(to_ship),
            "inTransit": in_transit,
            "breaches": int(breaches),
            "atRisk": int(at_risk),
            "returns": by.get("to_return", 0) + by.get("returned", 0),
            "attention": sum(int(v or 0) for v in (attention or {}).values()),
            "totalOrders": total,
            "sameDayPct": _sla_hit_rate(sla_since),
            "cutoff": _cut,
            "beforeCutoff": int(before_cutoff or 0),
            "cutoffPct": round((before_cutoff or 0) * 100 / max(1, orders_in)),
        }

        return {"summary": summary, "pipeline": pipeline, "leaderboard": _leaderboard(), "atRisk": _at_risk()}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.cockpit")
        return {}


@frappe.whitelist()
def breached_list(limit=500):
    """Open SLA problems (breached + at-risk, not yet delivered) for the
    cockpit's 'Breached orders' panel and CSV export."""
    try:
        limit = min(max(int(limit or 500), 1), 2000)
        rows = frappe.db.sql(
            """SELECT dn.name AS dn, dn.customer_name AS customer,
                      dn.custom_sla_status AS sla,
                      COALESCE(dn.custom_track_shipment_status,'') AS track,
                      dn.posting_date AS date, dn.custom_awb AS awb,
                      COALESCE(so.custom_shipping_city, '') AS city,
                      so.name AS so
               FROM `tabDelivery Note` dn
               LEFT JOIN `tabSales Order` so ON so.name = (
                   SELECT dni.against_sales_order FROM `tabDelivery Note Item` dni
                   WHERE dni.parent = dn.name AND dni.against_sales_order IS NOT NULL LIMIT 1)
               WHERE dn.custom_sla_status IN ('Breached','At Risk')
                 AND dn.posting_date >= %s
                 AND COALESCE(dn.custom_track_shipment_status,'') <> 'Delivered'
               ORDER BY FIELD(dn.custom_sla_status,'Breached','At Risk'), dn.posting_date ASC
               LIMIT %s""",
            (add_days(nowdate(), -14), limit), as_dict=True)
        return [{"dn": r.dn, "order": r.so or "", "customer": r.customer or "",
                 "city": r.city or "", "sla": r.sla, "track": r.track,
                 "awb": r.awb or "", "date": str(r.date or "")} for r in rows]
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.breached_list")
        return []


@frappe.whitelist()
def floor():
    """Andon floor board — every number real, from today's documents:
      Picking  = distinct orders on Pick Lists submitted today
      Labeling = Delivery Notes created today (DN creation == label/AWB moment)
      Packing  = orders that reached Label Printed today (incl. those already
                 Shipped since packing precedes the manifest the same day)
      Shipping = orders whose status is Shipped as of today
    Rates are per hour elapsed since the 8:00 floor start; the bottleneck is
    the station furthest below target. Cutoff counts down to the 17:00
    manifest hand-off."""
    try:
        from frappe.utils import now_datetime

        today = nowdate()
        rows = frappe.db.sql(
            """
            SELECT HOUR(creation) AS h, COUNT(*) AS c
            FROM `tabSales Order`
            WHERE creation >= %s AND creation < %s + INTERVAL 1 DAY AND docstatus = 1
            GROUP BY HOUR(creation) ORDER BY h
            """,
            (today, today), as_dict=True,
        )
        by_hour = {int(r.h): int(r.c) for r in rows}
        from logistics_portal.api.settings import get_ops
        ops = get_ops()
        f_start, f_end = int(ops["floorStart"]), int(ops["floorEnd"])
        hours = [{"h": h, "count": by_hour.get(h, 0)} for h in range(f_start, f_end + 1)]
        total_today = sum(by_hour.values())

        picked = frappe.db.sql(
            """SELECT COUNT(DISTINCT pli.sales_order) FROM `tabPick List` pl
               JOIN `tabPick List Item` pli ON pli.parent = pl.name
               WHERE pl.docstatus = 1 AND pl.creation >= %s AND pl.creation < %s + INTERVAL 1 DAY""",
            (today, today))[0][0] or 0
        labeled = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabDelivery Note` WHERE docstatus = 1 AND creation >= %s AND creation < %s + INTERVAL 1 DAY",
            (today, today))[0][0] or 0
        printed = frappe.db.sql(
            """SELECT COUNT(*) FROM `tabSales Order`
               WHERE custom_logistics_status = 'Label Printed' AND modified >= %s AND modified < %s + INTERVAL 1 DAY""",
            (today, today))[0][0] or 0
        shipped = frappe.db.sql(
            """SELECT COUNT(*) FROM `tabSales Order`
               WHERE custom_logistics_status = 'Shipped' AND modified >= %s AND modified < %s + INTERVAL 1 DAY""",
            (today, today))[0][0] or 0
        packed = int(printed) + int(shipped)

        now = now_datetime()
        elapsed = max(1.0, (now.hour + now.minute / 60.0) - f_start)
        target = int(ops["dayTarget"])

        def station(name, count):
            rate = round(count / elapsed, 1)
            return {"name": name, "rate": rate, "target": target, "count": int(count),
                    "status": "ok" if rate >= target * 0.85 else "warn"}

        stations = [
            station("Picking", picked), station("Packing", packed),
            station("Labeling", labeled), station("Shipping", shipped),
        ]
        bottleneck = min(stations, key=lambda s: s["rate"] / (s["target"] or 1))
        ch, cm = (int(x) for x in str(ops["cutoff"]).split(":"))
        cutoff_min = max(0, ch * 60 + cm - (now.hour * 60 + now.minute))

        return {
            "hours": hours,
            "ordersToday": total_today,
            "pickedToday": int(picked),
            "packedToday": packed,
            "shippedToday": int(shipped),
            "perHour": round(total_today / elapsed, 1),
            "target": target,
            "stations": stations,
            "bottleneck": bottleneck["name"],
            "cutoffMin": cutoff_min,
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.floor")
        return {}


@frappe.whitelist()
def team():
    return {"leaderboard": _leaderboard()}


# ── My Performance ─────────────────────────────────────────────────────────
# Every number below comes from the trail the work itself writes: the lanes'
# "Confirmation:/Rescue:/CS:" comments and the pickers' submitted pick lists.
# Nothing is estimated — a metric with no source is simply absent.

# Which comment prefixes each lane writes, and which of its actions count as
# a "win" (the outcome the lane exists to produce).
_LANES = {
    "cf": {"prefix": "Confirmation", "dt": "Sales Order", "wins": ("confirm",)},
    "rs": {"prefix": "Rescue", "dt": "Sales Order", "wins": ("redeliver", "reship")},
    "cs": {"prefix": "CS", "dt": "Issue", "wins": ("resolve",)},
}


def _comment_action(content, prefix):
    return (content.split(f"{prefix}: ", 1)[-1] or "").split(" ", 1)[0].strip("()—-→ ")


def _agent_me(user, days=7):
    """Contact-center agent: today's decisions, pace, rate, trend, rank."""
    today = nowdate()
    by_action, today_total, today_wins = {}, 0, 0
    trend_map, hours, recent = {}, {}, []

    for lane, cfg in _LANES.items():
        rows = frappe.db.sql(
            """SELECT c.content, c.creation, c.reference_name,
                      DATE(c.creation) d, HOUR(c.creation) h
               FROM `tabComment` c
               WHERE c.owner = %(u)s AND c.reference_doctype = %(dt)s
                 AND c.creation >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)
                 AND c.content LIKE %(pfx)s
               ORDER BY c.creation DESC""",
            {"u": user, "dt": cfg["dt"], "days": days - 1,
             "pfx": cfg["prefix"] + ": %"}, as_dict=True)
        for r in rows:
            if "(bulk)" in r.content or " bulk " in r.content:
                continue
            action = _comment_action(r.content, cfg["prefix"])
            key = f"{lane}.{action}"
            is_win = action in cfg["wins"]
            d = str(r.d)
            t = trend_map.setdefault(d, {"date": d, "total": 0, "wins": 0})
            t["total"] += 1
            t["wins"] += 1 if is_win else 0
            if d == today:
                by_action[key] = by_action.get(key, 0) + 1
                today_total += 1
                today_wins += 1 if is_win else 0
                hours[int(r.h)] = hours.get(int(r.h), 0) + 1
                if len(recent) < 12:
                    recent.append({"ref": r.reference_name, "lane": lane,
                                   "action": action, "win": is_win,
                                   "at": str(r.creation)[11:16]})

    # Confirm rate: the decisions that actually closed an order today.
    closed = by_action.get("cf.confirm", 0) + by_action.get("cf.cancel", 0)
    rate = round(by_action.get("cf.confirm", 0) * 100.0 / closed, 1) if closed else None

    # Rank among everyone who worked a lane today (wins decide it).
    board = {}
    for lane, cfg in _LANES.items():
        for r in frappe.db.sql(
                """SELECT c.owner, c.content, COUNT(*) n FROM `tabComment` c
                   WHERE c.reference_doctype = %(dt)s AND c.creation >= %(since)s
                     AND c.content LIKE %(pfx)s
                   GROUP BY c.owner, c.content""",
                {"dt": cfg["dt"], "since": f"{today} 00:00:00",
                 "pfx": cfg["prefix"] + ": %"}, as_dict=True):
            if "(bulk)" in r.content or " bulk " in r.content:
                continue
            action = _comment_action(r.content, cfg["prefix"])
            b = board.setdefault(r.owner, {"total": 0, "wins": 0})
            b["total"] += int(r.n or 0)
            if action in cfg["wins"]:
                b["wins"] += int(r.n or 0)
    ranked = sorted(board.items(), key=lambda x: (-x[1]["wins"], -x[1]["total"]))
    rank = next((i + 1 for i, (u, _) in enumerate(ranked) if u == user), 0)

    # Best day in the window — something to beat.
    best = max(trend_map.values(), key=lambda x: x["total"], default=None)

    trend = []
    for i in range(days - 1, -1, -1):
        d = add_days(today, -i)
        trend.append(trend_map.get(d, {"date": d, "total": 0, "wins": 0}))

    # Days worked in a row, ending today (0 if nothing done today yet).
    streak = 0
    for row in reversed(trend):
        if row["total"] > 0:
            streak += 1
        else:
            break

    from logistics_portal.api.settings import get_ops
    # The pace window: the configured floor day, WIDENED to cover every hour
    # the person actually worked. The contact centre isn't bound by floor
    # hours — a decision at 03:00 is real work and has to appear, or the chart
    # reads empty while the ring says 7.
    lo, hi = int(get_ops("floorStart") or 8), int(get_ops("floorEnd") or 20)
    if hours:
        lo, hi = min(lo, min(hours)), max(hi, max(hours))
    return {
        "kind": "agent",
        "today": today_total, "wins": today_wins,
        "byAction": by_action,
        "target": int(get_ops("dayTarget") or 40),
        "rate": rate, "rateLabel": "confirmRate",
        "rank": rank, "of": len(ranked),
        "streak": streak,
        "hours": [{"h": h, "n": hours.get(h, 0)} for h in range(lo, hi + 1)],
        "trend": trend,
        "best": best,
        "recent": recent,
    }


def _picker_me(user, days=7):
    """Picker: distinct ORDERS on their submitted pick lists (a list is a
    multi-order batch), attributed to the list's creation day — the same
    definition the team leaderboard uses, so the two screens never disagree.

    No hourly pace here: on the live floor a dispatcher creates the lists
    through the day and they're submitted in one batch at night, so neither
    timestamp marks when the picker actually worked. A chart of that would be
    a chart of the batch job, not of the person.
    """
    today = nowdate()
    rows = frappe.db.sql(
        """SELECT DATE(pl.creation) d, COUNT(DISTINCT pli.sales_order) n
           FROM `tabPick List` pl
           JOIN `tabPick List Item` pli ON pli.parent = pl.name
           WHERE pl.docstatus = 1
             AND COALESCE(NULLIF(pl.custom_assigned_picker, ''), pl.owner) = %(u)s
             AND pl.creation >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)
           GROUP BY DATE(pl.creation)""",
        {"u": user, "days": days - 1}, as_dict=True)
    trend_map = {str(r.d): {"date": str(r.d), "total": int(r.n or 0),
                            "wins": int(r.n or 0)} for r in rows}
    trend = []
    for i in range(days - 1, -1, -1):
        d = add_days(today, -i)
        trend.append(trend_map.get(d, {"date": d, "total": 0, "wins": 0}))

    board = {r[0]: int(r[1]) for r in frappe.db.sql(
        """SELECT COALESCE(NULLIF(pl.custom_assigned_picker, ''), pl.owner) u,
                  COUNT(DISTINCT pli.sales_order) n
           FROM `tabPick List` pl
           JOIN `tabPick List Item` pli ON pli.parent = pl.name
           WHERE pl.docstatus = 1 AND DATE(pl.creation) = CURDATE()
             AND COALESCE(NULLIF(pl.custom_assigned_picker, ''), pl.owner)
                 NOT IN ('Administrator', 'Guest')
           GROUP BY u""")}
    ranked = sorted(board.items(), key=lambda x: -x[1])
    rank = next((i + 1 for i, (u, _) in enumerate(ranked) if u == user), 0)

    best = max(trend, key=lambda x: x["total"], default=None)
    streak = 0
    for row in reversed(trend):
        if row["total"] > 0:
            streak += 1
        else:
            break

    from logistics_portal.api.settings import get_ops
    today_total = trend[-1]["total"] if trend else 0
    return {
        "kind": "picker",
        "today": today_total, "wins": today_total,
        "byAction": {"pick.picked": today_total},
        "target": int(get_ops("dayTarget") or 40),
        "rate": None, "rateLabel": "",
        "rank": rank, "of": len(ranked),
        "streak": streak,
        "hours": [],
        "trend": trend, "best": best if best and best["total"] else None,
        "recent": [],
    }


@frappe.whitelist()
def me(user=None):
    """Personal performance for the logged-in employee.

    Role-aware: contact-center agents get their lane decisions, pickers get
    their picked orders. A manager may look at any user; nobody else can.
    """
    from logistics_portal.api.auth import resolve_role
    me_user = frappe.session.user
    role = resolve_role(me_user)
    if user and user != me_user:
        if role != "manager":
            frappe.throw("You can only see your own performance.",
                         frappe.PermissionError)
        target_user = user
        role = resolve_role(user)
    else:
        target_user = me_user

    data = (_agent_me(target_user) if role in ("confirmation", "manager")
            else _picker_me(target_user))
    data["user"] = target_user
    data["role"] = role

    # This month's bonus standing, so the reward is on the same screen as the
    # work. None when the role has no scorable board — the page then shows no
    # tile rather than a dead link to a board that would reject them.
    try:
        from logistics_portal.api.contact_center import (bonus_group_for,
                                                         bonus_points_for)
        data["points"] = bonus_points_for(target_user, bonus_group_for(role),
                                          nowdate()[:7])
    except Exception:
        data["points"] = None
    return data


# ---------------------------------------------------------------------------
def _sla_hit_rate(since=None):
    filters = {"custom_sla_status": ["not in", ["", None]]}
    if since:
        filters["posting_date"] = [">=", since]
    total = frappe.db.count("Delivery Note", dict(filters))
    if not total:
        return 0
    filters["custom_sla_status"] = ["in", ["On Track", "Delivered"]]
    good = frappe.db.count("Delivery Note", dict(filters))
    return round(good * 100 / total)


def _at_risk(limit=8):
    rows = frappe.get_all(
        "Delivery Note",
        filters={
            "custom_sla_status": ["in", ["At Risk", "Breached"]],
            "posting_date": [">=", add_days(nowdate(), -14)],
        },
        fields=["name", "customer_name as customer", "custom_sla_status as sla"],
        order_by="posting_date desc",
        limit=limit,
    )
    out = []
    for r in rows:
        out.append({
            "no": r.name, "customer": r.customer, "stage": "transit",
            "sla": "breached" if r.sla == "Breached" else "atrisk", "mins": 0,
        })
    return out


def _leaderboard(limit=8):
    """Per-picker, last 30 days, all real:
      picks = distinct ORDERS on their submitted pick lists (not PL count —
              PLs are multi-order batches)
      avg   = orders per active day
      sla   = same-day pick rate: % of their orders picked the day the order
              arrived. Carrier SLA is NOT attributed to pickers — delivery
              failures are the carrier's, not the floor's.
    Picker = custom_assigned_picker, falling back to owner (pickers create
    their own PLs; the autopilot sets the assignment).
    Cached 300s — it re-aggregates 30 days of PL⨝PLI⨝SO and runs on every
    cockpit AND team load."""
    import json as _json
    cache = frappe.cache()
    cached = cache.get_value("lp_leaderboard")
    if cached:
        try:
            return _json.loads(cached)[: int(limit)]
        except Exception:
            pass
    since = add_days(nowdate(), -30)
    rows = frappe.db.sql(
        """
        SELECT COALESCE(NULLIF(pl.custom_assigned_picker,''), pl.owner) AS picker,
               COUNT(DISTINCT pli.sales_order) AS orders,
               COUNT(DISTINCT DATE(pl.creation)) AS days,
               COUNT(DISTINCT CASE WHEN DATE(pl.creation) = DATE(so.creation)
                                   THEN pli.sales_order END) AS sameday
        FROM `tabPick List` pl
        JOIN `tabPick List Item` pli ON pli.parent = pl.name
        LEFT JOIN `tabSales Order` so ON so.name = pli.sales_order
        WHERE pl.docstatus = 1 AND pl.creation >= %s
          AND COALESCE(NULLIF(pl.custom_assigned_picker,''), pl.owner)
              NOT IN ('Administrator', 'Guest')
        GROUP BY picker
        ORDER BY orders DESC LIMIT %s
        """,
        (since, limit),
        as_dict=True,
    )
    emails = [r.picker for r in rows]
    names = {}
    if emails:
        for u in frappe.get_all("User", filters={"name": ["in", emails]},
                                fields=["name", "full_name"]):
            names[u.name] = u.full_name
    out = []
    for i, r in enumerate(rows):
        pid = EMAIL_TO_ID.get(r.picker)
        name = names.get(r.picker)
        if not name:
            # Never surface a raw email — prettify the local part.
            name = (r.picker or "").split("@")[0].capitalize()
        orders = int(r.orders or 0)
        days = max(1, int(r.days or 1))
        target = int(frappe.db.get_default("lp_floor_target") or 40)
        out.append({
            "id": pid or r.picker,
            "name": name,
            "short": name.split(" ")[0],
            "picks": orders,
            "avg": f"{round(orders / days)}/day",
            "sla": round(int(r.sameday or 0) * 100 / max(1, orders)),
            "rank": i + 1,
            "trend": [],
            "target": target,
        })
    cache.set_value("lp_leaderboard", _json.dumps(out), expires_in_sec=300)
    return out
