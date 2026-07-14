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

    # 1) Explicit field (added by this app's fixtures). "none" is an explicit
    # block — it must beat the seed map, or a seeded person can't be removed.
    role = frappe.db.get_value("User", user, "custom_logistics_role")
    if role == "none":
        return None
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


# ---------------------------------------------------------------------------
# Team management — the manager controls WHO has WHICH portal role from the
# Team page, instead of the hardcoded SEED_ROLES map. The explicit
# User.custom_logistics_role always wins ("none" = explicitly blocked).
# ---------------------------------------------------------------------------
def _require_manager():
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can manage the team.", frappe.PermissionError)


@frappe.whitelist()
def team_members(q=""):
    """The portal roster (everyone with a role, and where the role comes from:
    set / seed) + search matches over the remaining system users so the
    manager can grant access. Includes each member's last submitted pick."""
    _require_manager()
    users = frappe.get_all(
        "User", filters={"enabled": 1, "user_type": "System User"},
        fields=["name", "full_name", "custom_logistics_role"],
        limit_page_length=0)

    last_pick = dict(frappe.db.sql(
        """SELECT COALESCE(NULLIF(custom_assigned_picker, ''), owner), MAX(creation)
           FROM `tabPick List` WHERE docstatus = 1
           GROUP BY COALESCE(NULLIF(custom_assigned_picker, ''), owner)"""))

    ql = (q or "").strip().lower()
    members, matches = [], []
    for u in users:
        if u.name in ("Administrator", "Guest"):
            continue
        explicit = u.custom_logistics_role or ""
        if explicit == "none":
            role, source = "", "blocked"
        elif explicit in VALID_ROLES:
            role, source = explicit, "set"
        elif u.name in SEED_ROLES:
            role, source = SEED_ROLES[u.name], "seed"
        else:
            role, source = "", ""
        row = {"user": u.name, "name": u.full_name or u.name,
               "role": role, "source": source,
               "lastPick": str(last_pick.get(u.name) or "")[:10]}
        if role or source == "blocked":
            members.append(row)
        elif ql and (ql in u.name.lower() or ql in (u.full_name or "").lower()):
            matches.append(row)

    order = {"manager": 0, "dispatcher": 1, "picker": 2, "packer": 3, "returns": 4, "": 5}
    members.sort(key=lambda r: (order.get(r["role"], 9), r["name"]))
    return {"members": members, "matches": matches[:8],
            "roles": sorted(VALID_ROLES),
            "target": int(frappe.db.get_default("lp_floor_target") or 40)}


@frappe.whitelist()
def set_member_role(user, role=""):
    """Assign / change / remove a portal role. Empty role = remove access
    (stored as the explicit 'none' so it also overrides the seed map)."""
    _require_manager()
    role = (role or "").strip().lower()
    if role and role not in VALID_ROLES:
        frappe.throw("Unknown role.")
    if not frappe.db.exists("User", user):
        frappe.throw("Unknown user.")
    if user == frappe.session.user and role != "manager":
        frappe.throw("You can't remove your own manager role.")
    frappe.db.set_value("User", user, "custom_logistics_role", role or "none",
                        update_modified=False)
    frappe.db.commit()
    return {"ok": True, "user": user, "role": role}


@frappe.whitelist()
def set_floor_target(value):
    """The daily per-person order target (floor board pace + leaderboard)."""
    _require_manager()
    try:
        v = int(value)
    except Exception:
        frappe.throw("Target must be a number.")
    if not (1 <= v <= 500):
        frappe.throw("Target must be between 1 and 500.")
    frappe.db.set_default("lp_floor_target", v)
    frappe.cache().delete_value("lp_leaderboard")
    return {"ok": True, "target": v}


@frappe.whitelist()
def invite_member(email, full_name=None, role="picker"):
    """Create the ERPNext User FROM THE PORTAL (welcome email lets them set a
    password) and assign their portal role in one step — onboarding without
    the desk. If the user already exists, just assigns the role."""
    _require_manager()
    from frappe.utils import validate_email_address
    email = (email or "").strip().lower()
    validate_email_address(email, throw=True)
    role = (role or "").strip().lower()
    if role not in VALID_ROLES:
        frappe.throw("Unknown role.")

    if frappe.db.exists("User", email):
        frappe.db.set_value("User", email, "custom_logistics_role", role,
                            update_modified=False)
        if not frappe.db.get_value("User", email, "enabled"):
            frappe.db.set_value("User", email, "enabled", 1, update_modified=False)
        frappe.db.commit()
        return {"ok": True, "user": email, "role": role, "existing": True}

    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": (full_name or email.split("@")[0]).strip() or email,
        "user_type": "System User",
        "send_welcome_email": 1,
        "custom_logistics_role": role,
    })
    user.flags.ignore_permissions = True
    user.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "user": email, "role": role, "existing": False}
