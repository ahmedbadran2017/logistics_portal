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
