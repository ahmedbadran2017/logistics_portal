"""Configurable pickable-warehouse policy.

Single source of truth for "which JM warehouses can stock be pulled from" — used
by the Orders board OOS split and the pick-batching engine. Structural families
(defective / transit / correcting / old) are always excluded; the named ZONES
(Return, Receiving, Slow, PLT, Yakuplu, …) are toggled by a manager in Settings.
"""

import json
import re

import frappe

# Always-off structural families (LIKE patterns) — transit/quarantine stock that
# is never sellable off the shelf, whatever the settings say.
_FAMILY = ["Defective%", "Container%", "Air Freight%", "%Old%", "CORRECTING%"]

# Configurable zones excluded by default (returned goods, per ops' new policy).
DEFAULT_EXCLUDED = ["Return Zone - JM", "Returns Adjustment - JM"]

_KEY = "lp_excluded_zones"
_AISLE_RE = re.compile(r"^[A-Za-z]{1,2}\d{1,2}[A-Za-z]?\.?$")  # e.g. F1, H14A, B1C.


def excluded_zones():
    """The manager-configured list of excluded warehouse names (exact), or the
    default returns-zones if never set."""
    raw = frappe.db.get_default(_KEY)
    if raw:
        try:
            v = json.loads(raw)
            if isinstance(v, list):
                return [str(x) for x in v]
        except Exception:
            pass
    return list(DEFAULT_EXCLUDED)


def pickable_condition(col="warehouse"):
    """(sql, args) — a WHERE fragment on the given warehouse column selecting
    pickable JM bins: '% - JM', minus the structural families, minus the
    configured excluded zones. All values are %s params."""
    zones = excluded_zones()
    parts = [f"{col} LIKE %s"] + [f"{col} NOT LIKE %s"] * len(_FAMILY)
    args = ["% - JM"] + list(_FAMILY)
    if zones:
        parts.append(f"{col} NOT IN ({', '.join(['%s'] * len(zones))})")
        args += zones
    return " AND ".join(parts), args


def _family_excluded(name):
    n = (name or "").lower()
    return any(k in n for k in ("defective", "container", "air freight", "old", "correcting"))


@frappe.whitelist()
def warehouse_settings():
    """Manager: the configurable pick ZONES (named, non-aisle JM warehouses that
    hold stock) and whether each is currently pickable. Aisle bins are always
    pickable and not listed; structural families show locked-off."""
    _require_manager()
    excluded = set(excluded_zones())
    rows = frappe.db.sql(
        """SELECT warehouse, ROUND(SUM(actual_qty)) qty, COUNT(DISTINCT item_code) items
           FROM `tabBin` WHERE warehouse LIKE %s
           GROUP BY warehouse HAVING qty <> 0""", ("% - JM",), as_dict=True)
    zones = []
    for r in rows:
        name = r.warehouse or ""
        short = name[:-5] if name.endswith(" - JM") else name
        if _AISLE_RE.match(short.strip()):
            continue  # a shelf bin, always pickable — not a configurable zone
        if _family_excluded(name):
            zones.append({"name": name, "short": short.strip(), "qty": int(r.qty or 0),
                          "items": int(r.items or 0), "pickable": False, "locked": True})
        else:
            zones.append({"name": name, "short": short.strip(), "qty": int(r.qty or 0),
                          "items": int(r.items or 0), "pickable": name not in excluded,
                          "locked": False})
    zones.sort(key=lambda z: (z["locked"], -z["qty"]))
    return {"zones": zones}


@frappe.whitelist()
def save_warehouse_settings(excluded=None):
    """Manager: persist the excluded (non-pickable) zone names."""
    _require_manager()
    if isinstance(excluded, str):
        excluded = json.loads(excluded)
    excluded = [str(x).strip() for x in (excluded or []) if str(x).strip()]
    frappe.db.set_default(_KEY, json.dumps(excluded))
    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return {"ok": True, "excluded": excluded}


def _require_manager():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can change pickable warehouses.", frappe.PermissionError)
