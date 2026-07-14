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
def floor_map():
    """The REAL floor: every JM warehouse holding stock, rolled up into
    physical families — named zones as-is, lettered pick aisles grouped per
    rack letter, AG-*/BAB-* racks as one block each. No fabricated capacities
    or owners; share bars are relative to the biggest group."""
    groups = frappe.db.sql(
        """SELECT grp,
                  COUNT(DISTINCT item_code) AS skus,
                  COUNT(DISTINCT wh) AS bins,
                  ROUND(SUM(qty)) AS units,
                  ROUND(SUM(val)) AS value
           FROM (
             SELECT b.item_code, b.actual_qty AS qty,
                    b.actual_qty * b.valuation_rate AS val, b.warehouse AS wh,
                    CASE
                      WHEN TRIM(REPLACE(b.warehouse, ' - JM', ''))
                           REGEXP '^[A-Za-z][0-9]{1,2}[A-Za-z]?[.]?$'
                        THEN CONCAT('Aisles ', UPPER(LEFT(TRIM(REPLACE(b.warehouse, ' - JM', '')), 1)))
                      WHEN UPPER(b.warehouse) LIKE 'AG-%%' THEN 'AG racks'
                      WHEN UPPER(b.warehouse) LIKE 'BAB-%%' THEN 'BAB racks'
                      ELSE TRIM(REPLACE(b.warehouse, ' - JM', ''))
                    END AS grp
             FROM `tabBin` b
             WHERE b.warehouse LIKE '%% - JM' AND b.actual_qty > 0
           ) t
           GROUP BY grp
           ORDER BY units DESC""", as_dict=True)
    tot = frappe.db.sql(
        """SELECT COUNT(DISTINCT b.item_code), ROUND(SUM(b.actual_qty)),
                  ROUND(SUM(b.actual_qty * b.valuation_rate))
           FROM `tabBin` b
           WHERE b.warehouse LIKE '%% - JM' AND b.actual_qty > 0""")[0]
    excluded = set(excluded_zones())
    out = []
    for g in groups:
        name_jm = f"{g.grp} - JM"
        out.append({
            "key": g.grp, "label": g.grp,
            "aisleGroup": g.grp.startswith("Aisles ") or g.grp in ("AG racks", "BAB racks"),
            "bins": int(g.bins or 0), "skus": int(g.skus or 0),
            "units": int(g.units or 0), "value": int(g.value or 0),
            "offPick": name_jm in excluded or _family_excluded(name_jm),
        })
    return {
        "groups": out,
        "skus": int(tot[0] or 0), "units": int(tot[1] or 0),
        "value": int(tot[2] or 0),
        "offCount": sum(1 for g in out if g["offPick"]),
    }


@frappe.whitelist()
def warehouse_settings():
    """Manager: the configurable pick ZONES (named, non-aisle JM warehouses that
    hold stock) and whether each is currently pickable. Aisle bins are always
    pickable and not listed; structural families show locked-off."""
    _require_manager()
    excluded = set(excluded_zones())
    # NB: the SKU-count column is aliased item_count, NOT `items` — on a
    # frappe._dict row `r.items` resolves to the dict METHOD, and int(method)
    # raised TypeError on every call. That's why the Settings panel showed
    # "No configurable zones" since day one.
    rows = frappe.db.sql(
        """SELECT warehouse, ROUND(SUM(actual_qty)) qty,
                  COUNT(DISTINCT item_code) item_count
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
                          "items": int(r.item_count or 0), "pickable": False, "locked": True})
        else:
            zones.append({"name": name, "short": short.strip(), "qty": int(r.qty or 0),
                          "items": int(r.item_count or 0), "pickable": name not in excluded,
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
    # The policy scopes EVERY stock view — bust every cache built on it so a
    # toggle takes effect immediately across the portal, not after TTLs.
    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation",
              "lp_sku_dupes", "lp_problem_radar"):
        frappe.cache().delete_value(k)
    return {"ok": True, "excluded": excluded}


def _require_manager():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can change pickable warehouses.", frappe.PermissionError)
