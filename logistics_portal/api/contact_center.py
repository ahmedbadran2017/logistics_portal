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
# Points per decision, straight from the Comment trail the lanes already
# write. Bulk actions are excluded so mass triage can't farm points.
_BONUS_KEY = "lp_bonus_settings"
_BONUS_DEFAULTS = {
    "monthlyTarget": 400,
    "points": {
        "cf.confirm": 1.0, "cf.cancel": 0.5, "cf.duplicate": 0.5,
        "cf.dna": 0.25, "cf.followup": 0.25, "cf.onhold": 0.25,
        "rs.redeliver": 3.0, "rs.reship": 3.0, "rs.returnreq": 1.0,
        "rs.dna": 0.25, "rs.cancel": 1.0, "rs.resolve": 0.5,
        "cs.resolve": 2.0, "cs.reply": 0.5, "cs.create": 0.5,
        "cs.take": 0.25, "cs.hold": 0.0, "cs.reopen": 0.0,
    },
}


def _lane_gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("confirmation", "manager"):
        frappe.throw("Not authorized for the bonus board.", frappe.PermissionError)
    return role


def _bonus_settings():
    import json as _json
    raw = frappe.db.get_default(_BONUS_KEY)
    out = {"monthlyTarget": _BONUS_DEFAULTS["monthlyTarget"],
           "points": dict(_BONUS_DEFAULTS["points"])}
    if raw:
        try:
            saved = _json.loads(raw)
            if isinstance(saved, dict):
                if "monthlyTarget" in saved:
                    out["monthlyTarget"] = int(saved["monthlyTarget"])
                if isinstance(saved.get("points"), dict):
                    for k in out["points"]:
                        if k in saved["points"]:
                            out["points"][k] = float(saved["points"][k])
        except Exception:
            pass
    return out


@frappe.whitelist()
def bonus_settings():
    _lane_gate()
    from logistics_portal.api.auth import resolve_role
    return {**_bonus_settings(),
            "canEdit": resolve_role(frappe.session.user) == "manager"}


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
    if "monthlyTarget" in settings:
        v = int(settings["monthlyTarget"])
        if not (1 <= v <= 100000):
            frappe.throw("monthlyTarget must be between 1 and 100000.")
        out["monthlyTarget"] = v
    if isinstance(settings.get("points"), dict):
        for k in out["points"]:
            if k in settings["points"]:
                v = float(settings["points"][k])
                if not (0 <= v <= 100):
                    frappe.throw(f"{k}: points must be between 0 and 100.")
                out["points"][k] = v
    frappe.db.set_default(_BONUS_KEY, _json.dumps(out))
    frappe.db.commit()
    return {"ok": True, **out}


@frappe.whitelist()
def bonus(month=None):
    """The month's points per agent, ranked — plus the caller's own card."""
    _lane_gate()
    import re as _re
    month = (month or "").strip()
    if not _re.match(r"^\d{4}-\d{2}$", month):
        month = str(now_datetime())[:7]
    s = _bonus_settings()
    pts = s["points"]

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

    agents = sorted(
        ({"agent": u.split("@")[0], "user": u,
          "cf": round(a["cf"], 1), "rs": round(a["rs"], 1), "cs": round(a["cs"], 1),
          "points": round(a["cf"] + a["rs"] + a["cs"], 1),
          "actions": a["actions"]} for u, a in per_agent.items()),
        key=lambda x: -x["points"])

    me = {"points": 0.0, "rank": 0, "actions": 0}
    for i, a in enumerate(agents):
        if a["user"] == frappe.session.user:
            me = {"points": a["points"], "rank": i + 1, "actions": a["actions"]}
            break

    return {"month": month, "target": s["monthlyTarget"], "agents": agents,
            "me": me, "meUser": frappe.session.user,
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
