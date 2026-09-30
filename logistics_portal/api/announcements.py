"""Announcements the team must read — and a record that they did.

The first one is the bonus launch (Ahmed, 2026-09-30): measuring starts on
1 October and October is the first PAID month; September was a trial and is
not paid. A popup that closes on any click is forgotten by lunch, and at the
end of the month "nobody told me" is the one objection a manager cannot
answer. So an announcement here is acknowledged, not dismissed: pressing the
button records who read it and when, and a manager can see who has not.

Stored as user defaults (one tabDefaultValue row per person, keyed on the
announcement) rather than a doctype: nothing to migrate, and one row per user
means two people pressing the button in the same second cannot overwrite each
other the way a shared JSON blob would.

The text lives in the frontend locales; this module only knows which
announcement is live, for whom, and who has acknowledged it.
"""

import frappe
from frappe.utils import getdate, now_datetime, nowdate

# One live announcement at a time. `until` bounds it: someone who first logs
# in after the month is over does not need a launch notice for it.
LIVE = {"key": "bonus-2026-10", "from": "2026-09-30", "until": "2026-10-31"}
_PREFIX = "lp_ack:"


def _role():
    from logistics_portal.api.auth import resolve_role
    return resolve_role(frappe.session.user)


def _live():
    today = getdate(nowdate())
    return (getdate(LIVE["from"]) <= today <= getdate(LIVE["until"]))


def _acked_at(user, key):
    return frappe.db.get_value(
        "DefaultValue", {"parent": user, "defkey": _PREFIX + key}, "defvalue")


@frappe.whitelist()
def pending():
    """What the caller still has to acknowledge (at most one), with enough to
    greet them by name. Nothing for Guest, for a user with no portal role, or
    outside the announcement's window."""
    user = frappe.session.user
    if user in ("Guest", "Administrator") or not _role() or not _live():
        return {"key": None}
    at = _acked_at(user, LIVE["key"])
    full = frappe.db.get_value("User", user, "full_name") or ""
    return {"key": LIVE["key"], "acked": bool(at), "ackedAt": at or None,
            "firstName": (full.split() or [""])[0]}


@frappe.whitelist(methods=["POST"])
def ack(key):
    """Record that the caller read `key`. Idempotent: the FIRST time stands —
    reopening the rules later must not move the date they were informed."""
    user = frappe.session.user
    if user in ("Guest",) or not _role():
        frappe.throw("Not authorized.", frappe.PermissionError)
    if key != LIVE["key"]:
        frappe.throw("Unknown announcement.")
    at = _acked_at(user, key)
    if not at:
        at = str(now_datetime())[:19]
        frappe.defaults.set_user_default(_PREFIX + key, at, user=user)
        frappe.db.commit()
    return {"ok": True, "ackedAt": at}


@frappe.whitelist()
def status(key=None):
    """Manager: the roster against the announcement — who acknowledged and
    when, and who has not. The roster is the Team page's own (an explicit
    role, or the seed map), so the two screens cannot disagree about who is
    on the team."""
    from logistics_portal.api.auth import SEED_ROLES, VALID_ROLES
    if _role() != "manager":
        frappe.throw("Not authorized.", frappe.PermissionError)
    key = key or LIVE["key"]
    acked = dict(frappe.db.sql(
        "SELECT parent, defvalue FROM `tabDefaultValue` WHERE defkey = %s",
        (_PREFIX + key,)))
    rows = []
    for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"},
                            fields=["name", "full_name", "custom_logistics_role"],
                            limit_page_length=0):
        if u.name in ("Administrator", "Guest"):
            continue
        explicit = u.custom_logistics_role or ""
        role = (explicit if explicit in VALID_ROLES
                else SEED_ROLES.get(u.name, "") if explicit != "none" else "")
        if not role and u.name not in acked:
            continue
        rows.append({"user": u.name, "name": u.full_name or u.name, "role": role,
                     "ackedAt": acked.get(u.name)})
    rows.sort(key=lambda r: (bool(r["ackedAt"]), r["role"], r["name"]))
    return {"key": key, "rows": rows,
            "acked": sum(1 for r in rows if r["ackedAt"]), "total": len(rows)}
