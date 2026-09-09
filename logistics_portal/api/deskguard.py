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
request through, never blort the whole site — with one exception, the redirect
itself, which is raised as an HTTPException and must be allowed to escape.
"""

import frappe
from werkzeug.exceptions import HTTPException
from werkzeug.utils import redirect as _wz_redirect

# An admin can grant this role to temporarily hand a team member back the Desk
# (a real emergency) without a code change; revoke it to re-lock.
_OVERRIDE_ROLE = "Logistics Desk Override"
_PORTAL_HOME = "/logistics"


def _bounce(dest):
    """Send the browser to `dest` from inside a before_request hook.

    This used to `raise frappe.Redirect`, and that never redirected anybody: it
    showed a Server Error page with the traceback and a 301 in the corner
    (reported 2026-09-09 on /app/hr). Frappe only honours Redirect inside the
    WEBSITE path resolver — `PathResolver.resolve` / `RedirectPage.render` --
    and /app never goes through it, let alone this early. frappe.app.application
    catches exactly two things around init_request: HTTPException, which it
    returns as the response, and Exception, which becomes the error page.
    Redirect is neither, so it fell through to the error page and the 301 came
    from the exception class rather than from any real redirect.

    So raise what the request layer already knows how to answer: an
    HTTPException carrying a real redirect Response. 302, not 301 — a
    permanent redirect is cached by the browser and would keep bouncing a user
    who is later granted the override role.
    """
    raise HTTPException(response=_wz_redirect(dest, code=302))


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
        # the contact center is a separate surface since 2026-08-27. Both
        # targets are real pages (templates/pages/logistics.html and
        # confirmation.html), so neither lands on a 404.
        _bounce("/confirmation" if role in ("confirmation", "cs", "tracking")
                else _PORTAL_HOME)
    except HTTPException:
        # The bounce itself — must escape, or the fail-open below would swallow
        # the redirect and hand the Desk right back.
        raise
    except Exception:
        # Never let the guard take the site down — fail open.
        return
