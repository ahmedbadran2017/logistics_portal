"""Attendance, read-only — is the person on the clock right now?

The floor punches in and out in Frappe HR's own mobile app (/hrms), which
records a GPS fix on every log. That stays the ONLY writer: `Employee Checkin`
is what payroll reads, and a second thing creating those rows — with its own
idea of shifts, geolocation and the checkin-to-attendance job — would be two
sources of truth for someone's pay.

So this module never writes. It answers one question for the signed-in person,
about themselves, so the portal can show it where they already are instead of
making them open another app to remember whether they clocked in.

Deliberately scoped to the caller: every query is fenced to the Employee record
whose `user_id` is the session user, so there is no way to read anybody else.
"""

import frappe
from frappe.utils import now_datetime, time_diff_in_seconds


def _my_employee():
    """The signed-in user's Employee record, or None.

    Active first: a person who has been re-hired can carry more than one row,
    and the live one is the one to report against.
    """
    user = frappe.session.user
    if not user or user in ("Guest",):
        return None
    rows = frappe.db.sql(
        """SELECT name, employee_name, status FROM `tabEmployee`
           WHERE user_id = %s ORDER BY (status = 'Active') DESC, modified DESC
           LIMIT 1""", (user,), as_dict=True)
    return rows[0] if rows else None


@frappe.whitelist()
def my_status():
    """{state, since, lastAt, workedMin, employeeName, hrApp}.

    `state` is read from the LAST log, whatever day it falls on — not from
    today's logs alone. A picker who forgot to punch out last night is still
    shown as on the clock, which is the truth and is what gets it corrected;
    saying "not checked in" because the calendar rolled over would be a
    confident lie. `workedMin` stays scoped to today, because that is the
    number a person actually wants from it.

    Times come from the log's `time` field, not `creation`: the HR app lets a
    late entry carry the moment it actually happened (measured on production,
    a log created at 11:01 for a 09:01 punch), and `time` is the one payroll
    reads.
    """
    emp = _my_employee()
    if not emp:
        return {"state": "no_employee", "hrApp": "/hrms"}

    last = frappe.db.sql(
        """SELECT log_type, time FROM `tabEmployee Checkin`
           WHERE employee = %s ORDER BY time DESC LIMIT 1""",
        (emp.name,), as_dict=True)

    now = now_datetime()
    today = str(now)[:10]
    logs = frappe.db.sql(
        """SELECT log_type, time FROM `tabEmployee Checkin`
           WHERE employee = %s AND DATE(time) = %s ORDER BY time""",
        (emp.name, today), as_dict=True)

    # Pair the day's logs into IN→OUT stretches. A stray second IN does not
    # restart the clock and a stray OUT with nothing open is ignored, so a
    # messy day degrades to a smaller number rather than to a wrong one.
    worked, open_at = 0.0, None
    for r in logs:
        if (r.log_type or "").upper() == "IN":
            if open_at is None:
                open_at = r.time
        else:
            if open_at is not None:
                worked += max(0.0, time_diff_in_seconds(r.time, open_at))
                open_at = None
    if open_at is not None:
        worked += max(0.0, time_diff_in_seconds(now, open_at))

    out = {"employeeName": emp.employee_name or "", "hrApp": "/hrms",
           "workedMin": int(worked // 60), "serverNow": str(now)[:19]}
    if not last:
        out["state"] = "none"
        return out

    is_in = (last[0].log_type or "").upper() == "IN"
    t = last[0].time
    out["state"] = "in" if is_in else "out"
    out["lastAt"] = str(t)[:19]
    # Same day or not — the UI shows a date only when it is not today, so an
    # unclosed shift from yesterday reads as the anomaly it is.
    out["stale"] = bool(str(t)[:10] != today)
    if is_in:
        out["since"] = str(t)[11:16]
    return out
