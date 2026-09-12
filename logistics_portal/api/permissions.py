"""Portal role guards for the Logistics Portal API.

Single source of truth for "can this user touch the portal". Mirrors the
supplier_portal pattern. Every whitelisted endpoint calls require_portal_user()
(or require_portal_admin() for privileged actions) before doing anything.

Role tiers (kept in sync with www/logistics.py and install.py):
    Logistics Portal Admin   — full portal admin
    Logistics Portal User    — portal user
    Warehouse Portal User    — warehouse-floor user
    Stock Manager / Stock User — existing ERPNext stock roles, allowed in
    System Manager / Administrator — always allowed
"""
import frappe
from frappe import _


ROLE_LOGISTICS_ADMIN = "Logistics Portal Admin"
ROLE_LOGISTICS_USER = "Logistics Portal User"
ROLE_WAREHOUSE_USER = "Warehouse Portal User"

# Anyone with one of these may read the portal.
PORTAL_ANY_ROLES = {
    ROLE_LOGISTICS_ADMIN,
    ROLE_LOGISTICS_USER,
    ROLE_WAREHOUSE_USER,
    "Stock Manager",
    "Stock User",
    "System Manager",
}

# Privileged actions (creating Stock Entries, advancing order status, etc.).
PORTAL_ADMIN_ROLES = {
    ROLE_LOGISTICS_ADMIN,
    "Stock Manager",
    "System Manager",
}


def _roles(user=None):
    return set(frappe.get_roles(user or frappe.session.user))


def is_portal_user(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    return user == "Administrator" or bool(_roles(user) & PORTAL_ANY_ROLES)


def is_portal_admin(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    return user == "Administrator" or bool(_roles(user) & PORTAL_ADMIN_ROLES)


# Contact-centre roles live on the other portal surface entirely (/confirmation)
# and have no business in warehouse management screens.
CC_ROLES = {"confirmation", "cs", "tracking"}


def is_ops_admin(user=None):
    """May this user administer the WAREHOUSE side of the portal?

    Deliberately stricter than is_portal_admin(). "Stock Manager" is attached
    to 32 accounts on this site — the contact centre, accounts, outside
    partners — so it says nothing about who runs the floor. Warehouse
    administration means the manager role, or a genuine portal/system
    administrator who is not a contact-centre user.
    """
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    if user == "Administrator":
        return True
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(user)
    if role == "manager":
        return True
    if role in CC_ROLES:
        return False
    return bool(_roles(user) & {ROLE_LOGISTICS_ADMIN, "System Manager"})


def require_portal_user():
    """Throw PermissionError unless the caller may use the portal."""
    if not is_portal_user():
        frappe.throw(_("You don't have access to the Logistics Portal."), frappe.PermissionError)


def require_portal_admin():
    """Throw PermissionError unless the caller may perform privileged actions."""
    if not is_portal_admin():
        frappe.throw(_("This action requires Logistics Admin or Stock Manager access."), frappe.PermissionError)
