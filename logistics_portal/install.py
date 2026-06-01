import frappe


PORTAL_ROLES = [
    "Logistics Portal Admin",
    "Logistics Portal User",
    "Warehouse Portal User",
]


def after_install():
    _create_portal_roles()


def _create_portal_roles():
    for role_name in PORTAL_ROLES:
        if not frappe.db.exists("Role", role_name):
            doc = frappe.new_doc("Role")
            doc.role_name = role_name
            doc.desk_access = 1
            doc.insert(ignore_permissions=True)
