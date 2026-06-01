import frappe

no_cache = 1


def get_context(context):
    """Render the Vue SPA shell. Gate access by role/login + pre-compute the
    shell globals so the Jinja sandbox doesn't try to call Python helpers
    (some return DebugUndefined inside web templates)."""
    context.no_cache = 1

    if frappe.session.user == "Guest":
        try:
            path = frappe.request.path or "/logistics"
            qs = frappe.request.query_string.decode() if frappe.request.query_string else ""
            target = path + ("?" + qs if qs else "")
        except Exception:
            target = "/logistics"
        frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.utils.quote(target)
        raise frappe.Redirect

    allowed = {
        "Logistics Portal Admin",
        "Logistics Portal User",
        "Warehouse Portal User",
        "Stock Manager",
        "Stock User",
        "System Manager",
    }
    if frappe.session.user != "Administrator":
        user_roles = set(frappe.get_roles(frappe.session.user))
        if not (user_roles & allowed):
            frappe.throw(
                "You don't have access to the Logistics Portal. Contact admin.",
                frappe.PermissionError,
            )

    user = frappe.session.user
    try:    full_name = frappe.utils.get_fullname(user) or ""
    except Exception: full_name = ""
    try:    user_image = frappe.db.get_value("User", user, "user_image") or ""
    except Exception: user_image = ""
    try:    roles = list(frappe.get_roles(user))
    except Exception: roles = []
    try:    company = frappe.defaults.get_user_default("Company") or "Justyol Morocco"
    except Exception: company = "Justyol Morocco"
    try:    csrf_token = frappe.sessions.get_csrf_token()
    except Exception: csrf_token = ""
    try:    site_name = frappe.local.site or ""
    except Exception: site_name = ""

    context.portal_shell = {
        "csrf_token": csrf_token,
        "site_name": site_name,
        "user_id": user,
        "full_name": full_name,
        "user_image": user_image,
        "user_roles": roles,
        "company": company,
    }
