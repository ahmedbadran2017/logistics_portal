"""Contact Center — the manager's one-glance view across the three lanes.

Queues, today's decisions, SLA breaches and the cross-lane leaderboard in a
single call. Gated to the portal manager and the sections' own admins (a team
lead follows her floor without portal-manager powers).
"""

import frappe
from frappe.utils import now_datetime


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) == "manager":
        return
    from logistics_portal.api.confirmation import _is_cf_admin
    from logistics_portal.api.rescue import _is_rs_admin
    from logistics_portal.api.tickets import _is_cs_admin
    if _is_cf_admin() or _is_rs_admin() or _is_cs_admin():
        return
    frappe.throw("The Contact Center overview is for the portal manager or a "
                 "section admin.", frappe.PermissionError)


def _today_by_prefix(prefix, doctypes=("Sales Order",)):
    """Today's decision tallies from the Comment trail: {action: n, ...}."""
    today = str(now_datetime())[:10]
    out = {}
    for r in frappe.db.sql(
            """SELECT c.content, COUNT(*) n FROM `tabComment` c
               WHERE c.reference_doctype IN %(dts)s AND c.creation >= %(since)s
                 AND c.content LIKE %(pfx)s
               GROUP BY c.content""",
            {"dts": tuple(doctypes), "since": f"{today} 00:00:00",
             "pfx": prefix + ": %"}, as_dict=True):
        action = (r.content.split(": ", 1)[1] or "").split(" ", 1)[0].strip("()—-→ ")
        out[action] = out.get(action, 0) + int(r.n or 0)
    return out


# ── Bonus system ─────────────────────────────────────────────────────────
# Points per unit of work, straight from the trail the work itself writes.
# Bulk actions never score, so mass triage can't farm points.
#
# Two GROUPS, because comparing a picker to a confirmation agent is comparing
# nothing: the floor moves thousands of orders a month, the contact centre
# makes tens of decisions a day. Each group has its own target and its own
# board; a manager can look at either.
#   cc     contact centre — confirmation / rescue / tickets decisions
#   floor  picking — distinct orders on submitted pick lists
# Packing/dispatch have no per-person attribution in the data (the label's
# custom_allocated_to holds the CONFIRMATION agent, not the packer), so they
# get no scheme rather than a scheme of zeros.
_BONUS_KEY = "lp_bonus_settings"
GROUPS = ("cc", "floor")
_ROLE_GROUP = {"confirmation": "cc", "picker": "floor"}
# What a point is WORTH. The old handoff design paid money and gated it on
# quality — a much better idea than bare points, so it comes back here, wired
# to real numbers. Every figure below is a default for the manager to tune in
# Settings; none of it is a business decision this code gets to make.
#
# Calibrated against production, not invented:
#   floor  top picker moves ~3,124 orders/month -> 0.4 MAD each = ~1,250 MAD
#   cc     a busy agent works ~2,000 orders/month -> 0.5 MAD each = ~1,000 MAD
#   kicker the floor's real same-day rate is 41%, so the old design's 90% team
#          target could never once have paid out. 55% is a reachable stretch.
_MONEY_DEFAULTS = {
    "on": 0,                  # off until the manager sets the numbers
    "currency": "MAD",
    "perPoint": {"cc": 1.0, "floor": 4.0},   # MAD per point earned
    "monthlyCap": {"cc": 1500, "floor": 1500},
    # Quality gate: no payout above the base until the agent clears it.
    # cc is gated on confirm rate — a number the agent actually controls.
    # floor has NO honest per-person quality signal yet (same-day measures the
    # dispatcher's list timing, not the picker's work), so it stays off.
    "gateOn": {"cc": 1, "floor": 0},
    # 65.3% is the measured company average — a gate above it would fail most
    # of the team on day one. 60 asks the laggards to reach the middle.
    "gatePct": {"cc": 60, "floor": 0},
    # Streak: +N% per 5 consecutive working days, capped.
    "streakStepPct": 10,
    "streakCapPct": 30,
    # Team kicker: every member of the group gets this if the floor's same-day
    # rate clears the target. Collective, so the team pulls together.
    "kickerOn": 0,
    "kickerAmount": 120,
    "kickerTargetPct": 55,
    "weeklyTop": [200, 100, 50],
}

_BONUS_DEFAULTS = {
    # Priced off June: the best agent earns ~1,374 points, the smallest ~100.
    "targets": {"cc": 1200, "floor": 300},
    "money": dict(_MONEY_DEFAULTS),
    # Weights, priced against a real completed month (June): the top agent
    # lands near the cap and the rest spread out beneath. The first cut of
    # these was ~13x too generous — every single agent hit the 1,500 cap,
    # including the one delivering 50.4%, and a cap everybody reaches is not a
    # cap, it is a salary. One point ≈ one MAD at the default perPoint.
    "points": {
        # The work.
        "cf.confirm": 0.1, "cf.cancel": 0.05, "cf.duplicate": 0.05,
        "cf.dna": 0.02, "cf.followup": 0.02, "cf.onhold": 0.02,
        "rs.redeliver": 0.5, "rs.reship": 0.5, "rs.returnreq": 0.1,
        "rs.dna": 0.02, "rs.cancel": 0.1, "rs.resolve": 0.1,
        "cs.resolve": 0.3, "cs.reply": 0.05, "cs.create": 0.05,
        "cs.take": 0.02, "cs.hold": 0.0, "cs.reopen": 0.0,
        # THE OUTCOME. A confirm is a promise; a delivered parcel is the money.
        # Paying most of the reward here aligns the agent by construction:
        # confirm carelessly and the parcel comes back — no point. Cancel
        # carelessly and no parcel ships — no point. The only way to earn is
        # orders that actually arrive. Measured on 90 days of live data, agents
        # range from 71.0% delivered to 58.1% on comparable volumes and basket
        # sizes — a 13-point spread worth real money.
        # Credited in the month the parcel LANDED, not the month of the call:
        # that is when the cash arrived.
        # Four times a confirm: the outcome is what the company is buying.
        "cf.delivered": 0.4,
        # A returned parcel is not a penalty — it is simply an unearned point.
        # Fining it on top would push agents to cancel anything doubtful.
        "cf.returned": 0.0,
        # Floor: the live top picker moves ~3,100 orders a month.
        "pick.picked": 0.1,
    },
}


def _portal_gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if not role:
        frappe.throw("Not authorized.", frappe.PermissionError)
    return role


def bonus_group_for(role):
    """Which board this role competes on — None if their work isn't scorable."""
    if role == "manager":
        return "cc"
    return _ROLE_GROUP.get(role)


def _bonus_settings():
    import json as _json
    raw = frappe.db.get_default(_BONUS_KEY)
    out = {"targets": dict(_BONUS_DEFAULTS["targets"]),
           "points": dict(_BONUS_DEFAULTS["points"]),
           "money": dict(_MONEY_DEFAULTS)}
    if raw:
        try:
            saved = _json.loads(raw)
            if isinstance(saved, dict):
                # Pre-groups schemes stored one flat monthlyTarget.
                if "monthlyTarget" in saved:
                    out["targets"]["cc"] = int(saved["monthlyTarget"])
                if isinstance(saved.get("targets"), dict):
                    for g in GROUPS:
                        if g in saved["targets"]:
                            out["targets"][g] = int(saved["targets"][g])
                if isinstance(saved.get("points"), dict):
                    for k in out["points"]:
                        if k in saved["points"]:
                            out["points"][k] = float(saved["points"][k])
                if isinstance(saved.get("money"), dict):
                    m = saved["money"]
                    for k, v in _MONEY_DEFAULTS.items():
                        if k not in m:
                            continue
                        if isinstance(v, dict):
                            out["money"][k] = {g: m[k].get(g, v[g]) for g in v}
                        else:
                            out["money"][k] = m[k]
        except Exception:
            pass
    return out


@frappe.whitelist()
def bonus_settings():
    role = _portal_gate()
    return {**_bonus_settings(), "canEdit": role == "manager",
            "group": bonus_group_for(role), "groups": list(GROUPS)}


@frappe.whitelist()
def save_bonus_settings(settings=None):
    import json as _json
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only the portal manager can change the bonus scheme.",
                     frappe.PermissionError)
    if isinstance(settings, str):
        settings = _json.loads(settings)
    settings = settings or {}
    out = _bonus_settings()
    if isinstance(settings.get("targets"), dict):
        for g in GROUPS:
            if g in settings["targets"]:
                v = int(settings["targets"][g])
                if not (1 <= v <= 100000):
                    frappe.throw(f"{g} target must be between 1 and 100000.")
                out["targets"][g] = v
    if isinstance(settings.get("points"), dict):
        for k in out["points"]:
            if k in settings["points"]:
                v = float(settings["points"][k])
                if not (0 <= v <= 100):
                    frappe.throw(f"{k}: points must be between 0 and 100.")
                out["points"][k] = v
    if isinstance(settings.get("money"), dict):
        m = settings["money"]
        mo = out["money"]
        for flag in ("on", "kickerOn"):
            if flag in m:
                mo[flag] = 1 if m[flag] else 0
        for grp_key, lo, hi in (("perPoint", 0, 1000), ("monthlyCap", 0, 100000),
                                ("gatePct", 0, 100)):
            if isinstance(m.get(grp_key), dict):
                for g in GROUPS:
                    if g in m[grp_key]:
                        v = float(m[grp_key][g])
                        if not (lo <= v <= hi):
                            frappe.throw(f"{grp_key}.{g} must be between {lo} and {hi}.")
                        mo[grp_key][g] = v
        if isinstance(m.get("gateOn"), dict):
            for g in GROUPS:
                if g in m["gateOn"]:
                    mo["gateOn"][g] = 1 if m["gateOn"][g] else 0
        for k, lo, hi in (("streakStepPct", 0, 50), ("streakCapPct", 0, 200),
                          ("kickerAmount", 0, 10000), ("kickerTargetPct", 0, 100)):
            if k in m:
                v = float(m[k])
                if not (lo <= v <= hi):
                    frappe.throw(f"{k} must be between {lo} and {hi}.")
                mo[k] = v
        if isinstance(m.get("weeklyTop"), list):
            mo["weeklyTop"] = [max(0, float(x)) for x in m["weeklyTop"][:3]]
    frappe.db.set_default(_BONUS_KEY, _json.dumps(out))
    frappe.db.commit()
    return {"ok": True, **out}


def _board(group, month, pts):
    """Cached board. The uncached board is 3 full-month tabComment GROUP BYs
    plus a month-wide SO/DNI/DN join, and it is recomputed by the confirmation
    board and My Performance on EVERY load just to read one agent's row. The
    numbers move at the speed of a phone call, so 120s of staleness is free.
    Keyed on the points too: change a weight in settings and the board is new.
    """
    import json as _json
    key = "lp_bonus_board:" + group + ":" + month + ":" + str(
        abs(hash(_json.dumps(pts, sort_keys=True))))
    cache = frappe.cache()
    hit = cache.get_value(key)
    if hit is not None:
        try:
            return _json.loads(hit)
        except Exception:
            pass
    rows = (_cc_board if group == "cc" else _floor_board)(month, pts)
    try:
        cache.set_value(key, _json.dumps(rows), expires_in_sec=120)
    except Exception:
        pass
    return rows


def _cc_board(month, pts):
    per_agent = {}
    for prefix, lane, dts in (("Confirmation", "cf", ("Sales Order",)),
                              ("Rescue", "rs", ("Sales Order",)),
                              ("CS", "cs", ("Issue",))):
        for r in frappe.db.sql(
                """SELECT c.owner, c.content, COUNT(*) n FROM `tabComment` c
                   WHERE c.reference_doctype IN %(dts)s
                     AND c.creation >= %(start)s
                     AND c.creation < DATE_ADD(%(start)s, INTERVAL 1 MONTH)
                     AND c.content LIKE %(pfx)s
                   GROUP BY c.owner, c.content""",
                {"dts": dts, "start": f"{month}-01 00:00:00",
                 "pfx": prefix + ": %"}, as_dict=True):
            if " bulk " in r.content or "(bulk)" in r.content:
                continue
            action = (r.content.split(": ", 1)[1] or "").split(" ", 1)[0].strip("()—-→ ")
            key = f"{lane}.{action}"
            if key not in pts:
                continue
            a = per_agent.setdefault(r.owner, {"cf": 0.0, "rs": 0.0, "cs": 0.0,
                                               "actions": 0})
            a[lane] += pts[key] * int(r.n or 0)
            a["actions"] += int(r.n or 0)
    # The outcome points: parcels that LANDED this month, per agent. Credited
    # to the month of delivery — that is when the money arrived, whenever the
    # call happened.
    d_rate = pts.get("cf.delivered", 0)
    outcome = {}
    if d_rate:
        for r in frappe.db.sql(
                # COUNT(DISTINCT dn.name), never SUM/COUNT(*): the DN Item join
                # fans out one row PER LINE, so a 3-item parcel counted 3× —
                # and unevenly, since the inflation IS the basket size. An agent
                # selling 3-packs earned 3× a colleague's points for the same
                # parcel, which is the one thing the points table is designed
                # not to do. A fifth of delivery notes carry 2+ lines, so this
                # was never a rounding error.
                """SELECT so.custom_allocated_to u,
                          COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status
                                = 'Delivered' THEN dn.name END) d,
                          COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status IN
                                ('Delivery Exception', 'Failed Attempt') THEN dn.name END) f
                   FROM `tabSales Order` so
                   JOIN `tabDelivery Note Item` dni
                     ON dni.against_sales_order = so.name AND dni.docstatus = 1
                   JOIN `tabDelivery Note` dn ON dn.name = dni.parent AND dn.docstatus = 1
                   WHERE so.docstatus = 1 AND COALESCE(so.custom_allocated_to,'') != ''
                     AND dn.posting_date >= %(start)s
                     AND dn.posting_date < DATE_ADD(%(start)s, INTERVAL 1 MONTH)
                     AND dn.custom_track_shipment_status IN
                         ('Delivered', 'Delivery Exception', 'Failed Attempt')
                   GROUP BY u""",
                {"start": f"{month}-01"}, as_dict=True):
            outcome[r.u] = {"delivered": int(r.d or 0), "returned": int(r.f or 0)}
            per_agent.setdefault(r.u, {"cf": 0.0, "rs": 0.0, "cs": 0.0,
                                       "actions": 0})

    rows = []
    for u, a in per_agent.items():
        o = outcome.get(u, {"delivered": 0, "returned": 0})
        shipped = o["delivered"] + o["returned"]
        dpts = o["delivered"] * d_rate
        rows.append({
            "agent": u.split("@")[0], "user": u,
            "cols": [round(a["cf"], 1), round(a["rs"], 1), round(a["cs"], 1),
                     round(dpts, 1)],
            "points": round(a["cf"] + a["rs"] + a["cs"] + dpts, 1),
            "actions": a["actions"],
            # The two numbers the agent has to see. A careless confirm is a
            # return, and a return is a round trip paid for nothing.
            "delivered": o["delivered"], "returned": o["returned"],
            "deliveryRate": round(o["delivered"] * 100.0 / shipped, 1) if shipped else None,
            "returnRate": round(o["returned"] * 100.0 / shipped, 1) if shipped else None,
        })
    return sorted(rows, key=lambda x: -x["points"])


def _floor_board(month, pts):
    rate = pts.get("pick.picked", 0)
    rows = frappe.db.sql(
        """SELECT COALESCE(NULLIF(pl.custom_assigned_picker, ''), pl.owner) u,
                  COUNT(DISTINCT pli.sales_order) n
           FROM `tabPick List` pl
           JOIN `tabPick List Item` pli ON pli.parent = pl.name
           WHERE pl.docstatus = 1 AND pl.creation >= %(start)s
             AND pl.creation < DATE_ADD(%(start)s, INTERVAL 1 MONTH)
             AND COALESCE(NULLIF(pl.custom_assigned_picker, ''), pl.owner)
                 NOT IN ('Administrator', 'Guest')
           GROUP BY u""",
        {"start": f"{month}-01 00:00:00"}, as_dict=True)
    return sorted(
        ({"agent": (r.u or "").split("@")[0], "user": r.u,
          "cols": [int(r.n or 0)],
          "points": round(int(r.n or 0) * rate, 1),
          "actions": int(r.n or 0)} for r in rows),
        key=lambda x: -x["points"])


def _floor_sameday_pct(month):
    """The floor's same-day rate for the month — what the team kicker rides on.
    Measured baseline: 41%."""
    r = frappe.db.sql(
        """SELECT COUNT(DISTINCT pli.sales_order) n,
                  COUNT(DISTINCT CASE WHEN DATE(pl.creation) = DATE(so.creation)
                                      THEN pli.sales_order END) same
           FROM `tabPick List` pl
           JOIN `tabPick List Item` pli ON pli.parent = pl.name
           LEFT JOIN `tabSales Order` so ON so.name = pli.sales_order
           WHERE pl.docstatus = 1 AND pl.creation >= %(start)s
             AND pl.creation < DATE_ADD(%(start)s, INTERVAL 1 MONTH)""",
        {"start": f"{month}-01 00:00:00"})[0]
    n = int(r[0] or 0)
    return round(int(r[1] or 0) * 100.0 / n, 1) if n else 0.0


def delivery_rate(user, month=None):
    """Of the parcels this agent's orders produced, how many were actually
    taken. THE quality number for a confirmation agent — and the one they
    should see: a careless confirm becomes a return, and a return costs the
    round trip.

    Not confirm rate, which rewards the opposite of quality: an agent who
    confirms everything scores 100%.
    """
    where = "AND dn.posting_date >= %(start)s AND dn.posting_date < DATE_ADD(%(start)s, INTERVAL 1 MONTH)" if month else ""
    vals = {"u": user}
    if month:
        vals["start"] = f"{month}-01"
    r = frappe.db.sql(
        # DISTINCT dn.name — the DN Item join fans out per line, so without it
        # a multi-item parcel counts once per item and the rate is weighted by
        # basket size instead of by outcome. See _cc_board.
        f"""SELECT COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status
                         = 'Delivered' THEN dn.name END) d,
                   COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status IN
                         ('Delivery Exception', 'Failed Attempt') THEN dn.name END) f
            FROM `tabSales Order` so
            JOIN `tabDelivery Note Item` dni
              ON dni.against_sales_order = so.name AND dni.docstatus = 1
            JOIN `tabDelivery Note` dn ON dn.name = dni.parent AND dn.docstatus = 1
            WHERE so.docstatus = 1 AND so.custom_allocated_to = %(u)s
              AND dn.custom_track_shipment_status IN
                  ('Delivered', 'Delivery Exception', 'Failed Attempt')
              {where}""", vals, as_dict=True)[0]
    d, f = int(r.d or 0), int(r.f or 0)
    n = d + f
    return {"delivered": d, "returned": f, "shipped": n,
            "rate": round(d * 100.0 / n, 1) if n else None,
            "returnRate": round(f * 100.0 / n, 1) if n else None}


def _quality_pct(user, group, month):
    """The number the gate reads. Only where the person actually controls it.

    cc: DELIVERY rate — of what they confirmed and shipped, what stuck.
    floor: None. Same-day would be the obvious candidate and it is NOT honest:
    the dispatcher creates the pick lists, so same-day measures HIS timing.
    Gating a picker's pay on it would dock them for someone else's work.
    """
    if group != "cc":
        return None
    return delivery_rate(user, month)["rate"]


def _streak_days(user, group, month):
    """Consecutive working days ending at the last day worked this month."""
    if group == "cc":
        rows = frappe.db.sql(
            """SELECT DISTINCT DATE(c.creation) d FROM `tabComment` c
               WHERE c.owner = %(u)s AND c.creation >= %(start)s
                 AND c.creation < DATE_ADD(%(start)s, INTERVAL 1 MONTH)
                 AND (c.content LIKE 'Confirmation: %%' OR c.content LIKE 'Rescue: %%'
                      OR c.content LIKE 'CS: %%')
               ORDER BY d""", {"u": user, "start": f"{month}-01 00:00:00"})
    else:
        rows = frappe.db.sql(
            """SELECT DISTINCT DATE(pl.creation) d FROM `tabPick List` pl
               WHERE pl.docstatus = 1
                 AND COALESCE(NULLIF(pl.custom_assigned_picker, ''), pl.owner) = %(u)s
                 AND pl.creation >= %(start)s
                 AND pl.creation < DATE_ADD(%(start)s, INTERVAL 1 MONTH)
               ORDER BY d""", {"u": user, "start": f"{month}-01 00:00:00"})
    days = [str(r[0]) for r in rows]
    if not days:
        return 0
    from datetime import date as _date, timedelta as _td
    best = run = 1
    prev = _date.fromisoformat(days[0])
    for d in days[1:]:
        cur = _date.fromisoformat(d)
        run = run + 1 if (cur - prev).days == 1 else 1
        best = max(best, run)
        prev = cur
    return run   # the streak they're ON, not their best ever


def _payout(agent, group, s, month, kicker_on):
    """Points -> money. Every knob is a setting; nothing here is hardcoded
    business policy."""
    m = s["money"]
    if not m["on"]:
        return None
    pts = agent["points"]
    rate = float(m["perPoint"].get(group, 0))
    base = pts * rate

    gate_pct = None
    gate_pass = True
    if m["gateOn"].get(group):
        gate_pct = _quality_pct(agent["user"], group, month)
        # No measurement yet = no penalty. Silence is not failure.
        gate_pass = gate_pct is None or gate_pct >= float(m["gatePct"].get(group, 0))

    streak = _streak_days(agent["user"], group, month)
    streak_pct = min(float(m["streakCapPct"]),
                     (streak // 5) * float(m["streakStepPct"]))

    gross = base * (1 + streak_pct / 100) if gate_pass else base
    kicker = float(m["kickerAmount"]) if (kicker_on and gate_pass) else 0
    cap = float(m["monthlyCap"].get(group, 0)) or None
    total = gross + kicker
    capped = bool(cap and total > cap)
    if capped:
        total = cap
    return {
        "base": round(base), "streakDays": streak, "streakPct": streak_pct,
        "gatePct": gate_pct, "gatePass": gate_pass,
        "kicker": round(kicker), "capped": capped,
        "total": round(total), "currency": m["currency"],
    }


def bonus_points_for(user, group, month):
    """One person's points this month — used by My Performance too."""
    if not group:
        return None
    s = _bonus_settings()
    board = (_cc_board if group == "cc" else _floor_board)(month, s["points"])
    for a in board:
        if a["user"] == user:
            return {"month": a["points"], "target": s["targets"][group]}
    return {"month": 0.0, "target": s["targets"][group]}


@frappe.whitelist()
def bonus(month=None, group=None):
    """The month's points for a group, ranked — plus the caller's own card."""
    role = _portal_gate()
    import re as _re
    month = (month or "").strip()
    if not _re.match(r"^\d{4}-\d{2}$", month):
        month = str(now_datetime())[:7]

    my_group = bonus_group_for(role)
    group = (group or "").strip() or my_group
    if group not in GROUPS:
        # Packing / dispatch / returns: no honest per-person source yet.
        return {"available": False, "month": month, "group": None,
                "agents": [], "me": {"points": 0, "rank": 0, "actions": 0},
                "target": 0, "meUser": frappe.session.user}
    if role != "manager" and group != my_group:
        frappe.throw("You can only see your own board.", frappe.PermissionError)

    s = _bonus_settings()
    agents = (_cc_board if group == "cc" else _floor_board)(month, s["points"])

    # Money, if the manager has switched the scheme on.
    money = s["money"]
    sameday = pool = None
    kicker_on = False
    if money["on"]:
        if money["kickerOn"]:
            sameday = _floor_sameday_pct(month)
            kicker_on = sameday >= float(money["kickerTargetPct"])
        for a in agents:
            a["pay"] = _payout(a, group, s, month, kicker_on)
        pool = sum(a["pay"]["total"] for a in agents if a.get("pay"))
        # The weekly-top prizes ride on the same board, top three by points.
        for i, a in enumerate(agents[:3]):
            prize = (money["weeklyTop"] or [0, 0, 0])[i] if i < 3 else 0
            if prize:
                a["prize"] = round(float(prize))

    me = {"points": 0.0, "rank": 0, "actions": 0, "pay": None}
    for i, a in enumerate(agents):
        if a["user"] == frappe.session.user:
            me = {"points": a["points"], "rank": i + 1, "actions": a["actions"],
                  "pay": a.get("pay")}
            break

    cols = (["nav.confirmation", "nav.rescue", "nav.tickets", "bn.colDelivered"]
            if group == "cc" else ["bn.colOrders"])
    return {"available": True, "month": month, "group": group,
            "groups": list(GROUPS) if role == "manager" else [my_group],
            "cols": cols, "target": s["targets"][group], "agents": agents,
            "me": me, "meUser": frappe.session.user,
            "money": {"on": money["on"], "currency": money["currency"],
                      "pool": round(pool) if pool is not None else None,
                      "kickerOn": money["kickerOn"], "kickerHit": kicker_on,
                      "kickerAmount": money["kickerAmount"],
                      "kickerTargetPct": money["kickerTargetPct"],
                      "sameday": sameday},
            "serverNow": str(now_datetime())[:19]}


@frappe.whitelist()
def overview():
    _gate()
    from logistics_portal.api.confirmation import QUEUES, _cf_settings
    from logistics_portal.api.rescue import _rs_settings, _BACKLOG_TRACKS
    from logistics_portal.api.tickets import _cs_settings, _has_wa, _OPEN_STATUSES

    cf_s, rs_s, cs_s = _cf_settings(), _rs_settings(), _cs_settings()

    # ── Lane 1: confirmation ────────────────────────────────────────────
    cf_counts = {k: 0 for k in QUEUES}
    for r in frappe.db.sql(
            """SELECT custom_sales_status s, COUNT(*) n FROM `tabSales Order`
               WHERE docstatus = 1 AND custom_sales_status IN %(sts)s
                 AND creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)
               GROUP BY custom_sales_status""",
            {"sts": tuple(QUEUES.values())}, as_dict=True):
        for k, v in QUEUES.items():
            if v == r.s:
                cf_counts[k] = int(r.n or 0)
    cf_breached = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabSales Order`
           WHERE docstatus = 1 AND custom_sales_status = 'Pending'
             AND creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)
             AND creation < DATE_SUB(NOW(), INTERVAL %(h)s HOUR)
             AND COALESCE(custom_call_attempts, 0) = 0""",
        {"h": cf_s.get("slaFirstCallH", 6)})[0][0])

    # ── Lane 2: rescue ──────────────────────────────────────────────────
    rs_counts = {}
    for key, track in (("exceptions", "Delivery Exception"),
                       ("failed", "Failed Attempt")):
        rs_counts[key] = int(frappe.db.sql(
            """SELECT COUNT(*) FROM `tabDelivery Note` dn
               WHERE dn.docstatus = 1 AND COALESCE(dn.custom_exception_action,'') = ''
                 AND dn.custom_track_shipment_status = %(t)s
                 AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)""",
            {"t": track})[0][0])
    rs_counts["backlog"] = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabDelivery Note` dn
           WHERE dn.docstatus = 1 AND COALESCE(dn.custom_exception_action,'') = ''
             AND dn.custom_track_shipment_status IN %(tracks)s
             AND dn.posting_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY)""",
        {"tracks": _BACKLOG_TRACKS})[0][0])
    rs_breached = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabDelivery Note` dn
           LEFT JOIN (SELECT dni.parent p, MAX(dni.against_sales_order) so_n
                      FROM `tabDelivery Note Item` dni GROUP BY dni.parent) m
                  ON m.p = dn.name
           LEFT JOIN `tabSales Order` so ON so.name = m.so_n
           WHERE dn.docstatus = 1 AND COALESCE(dn.custom_exception_action,'') = ''
             AND dn.custom_track_shipment_status IN ('Delivery Exception', 'Failed Attempt')
             AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
             AND dn.posting_date < DATE_SUB(CURDATE(), INTERVAL CEIL(%(h)s / 24) DAY)
             AND COALESCE(so.custom_call_attempts, 0) = 0""",
        {"h": rs_s.get("slaTriageH", 24)})[0][0])

    # ── Lane 3: tickets ─────────────────────────────────────────────────
    cs_open = int(frappe.db.sql(
        "SELECT COUNT(*) FROM `tabIssue` WHERE status IN %s",
        (_OPEN_STATUSES,))[0][0])
    cs_resolved7 = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabIssue`
           WHERE status IN ('Resolved', 'Closed')
             AND modified >= DATE_SUB(NOW(), INTERVAL 7 DAY)""")[0][0])
    cs_breached = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabIssue`
           WHERE status IN %(sts)s AND first_responded_on IS NULL
             AND creation < DATE_SUB(NOW(), INTERVAL %(h)s HOUR)""",
        {"sts": _OPEN_STATUSES, "h": cs_s.get("firstResponseH", 4)})[0][0])
    cs_inbox = 0
    if _has_wa():
        cs_inbox = int(frappe.db.sql(
            """SELECT COUNT(DISTINCT wm.`from`) FROM `tabWhatsApp Message` wm
               WHERE wm.type = 'Incoming' AND COALESCE(wm.custom_lp_handled, 0) = 0
                 AND wm.creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                 AND (wm.content_type IN ('text', 'image')
                      OR (wm.content_type = 'button' AND wm.message LIKE %(b)s))""",
            {"b": "%خدمة العملاء%"})[0][0])

    # ── Cross-lane leaderboard, 7 days ──────────────────────────────────
    board = {}
    for prefix, dts in (("Confirmation", ("Sales Order",)),
                        ("Rescue", ("Sales Order",)),
                        ("CS", ("Issue",))):
        for r in frappe.db.sql(
                """SELECT c.owner, c.content FROM `tabComment` c
                   WHERE c.reference_doctype IN %(dts)s
                     AND c.creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                     AND c.content LIKE %(pfx)s""",
                {"dts": dts, "pfx": prefix + ": %"}, as_dict=True):
            action = (r.content.split(": ", 1)[1] or "").split(" ", 1)[0].strip("()—-→ ")
            a = board.setdefault(r.owner, {"cf": 0, "rs": 0, "cs": 0, "wins": 0})
            lane = {"Confirmation": "cf", "Rescue": "rs", "CS": "cs"}[prefix]
            a[lane] += 1
            if (prefix == "Confirmation" and action == "confirm") \
                    or (prefix == "Rescue" and action in ("redeliver", "reship")) \
                    or (prefix == "CS" and action == "resolve"):
                a["wins"] += 1
    leaderboard = sorted(
        ({"agent": u.split("@")[0], "user": u, **a,
          "total": a["cf"] + a["rs"] + a["cs"]} for u, a in board.items()),
        key=lambda x: -x["wins"])[:8]

    return {
        "cf": {"counts": cf_counts, "breached": cf_breached,
               "today": _today_by_prefix("Confirmation"),
               "slaH": cf_s.get("slaFirstCallH", 6)},
        "rs": {"counts": rs_counts, "breached": rs_breached,
               "today": _today_by_prefix("Rescue"),
               "slaH": rs_s.get("slaTriageH", 24)},
        "cs": {"open": cs_open, "inbox": cs_inbox, "resolved7": cs_resolved7,
               "breached": cs_breached,
               "today": _today_by_prefix("CS", ("Issue",)),
               "slaH": cs_s.get("firstResponseH", 4)},
        "leaderboard": leaderboard,
        "serverNow": str(now_datetime())[:19],
    }
