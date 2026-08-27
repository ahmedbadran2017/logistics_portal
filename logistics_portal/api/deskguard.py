"""Keep the logistics team out of the ERPNext Desk — without touching a single
role or permission.

The floor team works entirely in the portal (/logistics). When the portal has a
hiccup they used to fall back to the raw Desk (/app), edit documents by hand, and
bypass every guard the portal enforces — creating worse, harder-to-trace data
problems and a firefighting loop. The fix is to remove that escape hatch: the
Desk is simply off-limits for them.

We do it at the request layer instead of by stripping Desk-granting roles,
because their roles also carry things they legitimately need (Raven chat,
Employee Self Service) and their doc permissions are what let the portal's own
server methods (and codx) save on their behalf. So we keep every role and
permission exactly as-is and just refuse to render /app for them, bouncing them
back to the portal where they belong.

Who is affected: any user with a `custom_logistics_role` set (the portal's own
team marker) — unless they hold the `Logistics Desk Override` role, the escape
valve an admin can grant for a genuine one-off. Administrator and non-team users
are never touched, so emergency Desk access lives on a separate admin account.

Fail-open by design: this runs on every request, so any error here must let the
request through, never blort the whole site.
"""

import frappe

# An admin can grant this role to temporarily hand a team member back the Desk
# (a real emergency) without a code change; revoke it to re-lock.
_OVERRIDE_ROLE = "Logistics Desk Override"
_PORTAL_HOME = "/logistics"


def block_desk_for_portal_team():
    """before_request hook: send logistics-team members away from /app."""
    try:
        req = getattr(frappe.local, "request", None)
        if req is None:
            return
        path = (getattr(req, "path", "") or "")
        # Only the Desk itself — never /api, /assets, /logistics, website pages.
        if path != "/app" and not path.startswith("/app/"):
            return

        user = getattr(getattr(frappe, "session", None), "user", None)
        if not user or user in ("Guest", "Administrator"):
            return

        # The portal's own team marker — non-team System Users (admins, other
        # departments) are untouched, so emergency Desk access stays with them.
        role = frappe.db.get_value("User", user, "custom_logistics_role")
        if not role:
            return

        # Per-user escape valve an admin can grant/revoke with no deploy.
        if _OVERRIDE_ROLE in (frappe.get_roles(user) or []):
            return

        # Bounce to the user's OWN portal instead of a dead-end error page:
        # the contact center is a separate surface since 2026-08-27.
        frappe.flags.redirect_location = (
            "/confirmation" if role == "confirmation" else _PORTAL_HOME)
        raise frappe.Redirect
    except frappe.Redirect:
        raise
    except Exception:
        # Never let the guard take the site down — fail open.
        return
