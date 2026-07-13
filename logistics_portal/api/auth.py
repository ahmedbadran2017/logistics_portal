"""Authentication & logistics-role resolution for the portal SPA."""

import frappe

# Seed role map — used until User.custom_logistics_role is populated.
# Roles are emergent from the stage a person touches, not their ERPNext title
# (the whole Logistics - JM team shares the "Logistics Agent" designation).
SEED_ROLES = {
    "anaskarrassi@gmail.com": "dispatcher",
    "mouakkalanass@gmail.com": "dispatcher",
    "marouaneelmessaoudi07@gmail.com": "picker",
    "saidnakri65@gmail.com": "picker",
    "asmaazirary7@gmail.com": "picker",
    "lamdanisaad12@gmail.com": "picker",
    "redazaari47@gmail.com": "packer",
    "operation@justyol.com": "manager",
}

VALID_ROLES = {"manager", "dispatcher", "picker", "packer", "returns"}


def resolve_role(user):
    """Resolve a user's logistics role, in priority order:
    1. explicit custom_logistics_role field, 2. seed map, 3. heuristic."""
    if not user or user == "Guest":
        return None

    # 1) Explicit field (added by this app's fixtures).
    role = frappe.db.get_value("User", user, "custom_logistics_role")
    if role in VALID_ROLES:
        return role

    # 2) Seed map for the known team.
    if user in SEED_ROLES:
        return SEED_ROLES[user]

    # 3) Heuristics — deliberately narrow. Manager comes ONLY from real ERPNext
    # roles; membership in the logistics department grants floor access; anyone
    # else gets NO portal role. (The old fallback made every logged-in user a
    # picker and any "…Operations…" department a manager.)
    roles = set(frappe.get_roles(user))
    if {"System Manager", "Logistics Manager"} & roles:
        return "manager"

    dept = frappe.db.get_value("Employee", {"user_id": user}, "department") or ""
    if dept.startswith("Logistics"):
        return "picker"  # safe default for floor staff
    return None


def resolve_zone(user):
    return frappe.db.get_value("User", user, "custom_logistics_zone") or ""


@frappe.whitelist(allow_guest=True)
def get_boot():
    """Return the session user's identity + resolved logistics role for the SPA.
    allow_guest so the pre-login boot returns a clean Guest stub instead of 403."""
    user = frappe.session.user
    if user == "Guest":
        return {"user": "Guest", "role": None, "roles": [], "full_name": "", "zone": ""}

    # The page template can't reliably inject the CSRF token (sandboxed Jinja),
    # so the SPA fetches it here over GET and uses it for POST writes.
    try:
        csrf = frappe.sessions.get_csrf_token()
    except Exception:
        csrf = ""

    role = resolve_role(user)
    return {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
        "role": role,
        "roles": [role] if role else [],
        "zone": resolve_zone(user),
        "csrf_token": csrf,
    }
