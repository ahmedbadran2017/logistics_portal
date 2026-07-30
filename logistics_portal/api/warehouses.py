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
# is never sellable off the shelf, whatever the settings say. Goods In Transit /
# WIP / Cathedis hold stock that is physically NOT on the floor (carrier hands,
# containers at sea) — they were toggleable-by-omission before, a policy hole.
_FAMILY = ["Defective%", "Container%", "Air Freight%", "%Old%", "CORRECTING%",
           "Goods In Transit%", "Work In Progress%", "Cathedis%"]

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
    return any(k in n for k in ("defective", "container", "air freight", "old",
                                "correcting", "goods in transit",
                                "work in progress", "cathedis"))


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
    """Manager: EVERY configurable pick zone (named, non-aisle, enabled leaf JM
    warehouse) and whether each is currently pickable. Starts from the
    Warehouse tree, not from Bins — zero-stock zones must be listed too, so a
    zone can be turned off BEFORE stock lands in it (the old Bin-based query
    hid 33 of the 62 zones). Aisle/rack shelf bins are always pickable and not
    listed; structural families show locked-off; empty locked ones (16 idle
    Containers) are noise and skipped."""
    _require_manager()
    excluded = set(excluded_zones())
    # NB: the SKU-count column is aliased item_count, NOT `items` — on a
    # frappe._dict row `r.items` resolves to the dict METHOD, and int(method)
    # raised TypeError on every call. That's why the Settings panel showed
    # "No configurable zones" since day one.
    rows = frappe.db.sql(
        """SELECT w.name AS warehouse,
                  COALESCE(ROUND(b.qty), 0) AS qty,
                  COALESCE(b.item_count, 0) AS item_count
           FROM `tabWarehouse` w
           LEFT JOIN (SELECT warehouse, SUM(actual_qty) qty,
                             COUNT(DISTINCT item_code) item_count
                      FROM `tabBin` GROUP BY warehouse) b ON b.warehouse = w.name
           WHERE w.name LIKE %s AND w.is_group = 0 AND w.disabled = 0""",
        ("% - JM",), as_dict=True)
    zones = []
    for r in rows:
        name = r.warehouse or ""
        short = (name[:-5] if name.endswith(" - JM") else name).strip()
        if _AISLE_RE.match(short) or short.upper().startswith(("AG-", "BAB-")):
            continue  # a shelf bin/rack, always pickable — not a configurable zone
        qty = int(r.qty or 0)
        if _family_excluded(name):
            if qty == 0:
                continue  # empty AND permanently locked — nothing to decide
            zones.append({"name": name, "short": short, "qty": qty,
                          "items": int(r.item_count or 0), "pickable": False, "locked": True})
        else:
            zones.append({"name": name, "short": short, "qty": qty,
                          "items": int(r.item_count or 0), "pickable": name not in excluded,
                          "locked": False})
    zones.sort(key=lambda z: (z["locked"], -z["qty"], z["short"].lower()))
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


# ---------------------------------------------------------------------------
# Shelf label studio — reprint SKU barcodes for stock whose labels have faded
# or were never there. Works one shelf at a time: pick a shelf, get its items
# with live piece counts, print Code-128(custom_sku) labels that the floor
# scanner reads straight back. The barcode is rendered client-side.
# ---------------------------------------------------------------------------
def _floor_gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in (
            "manager", "dispatcher", "picker", "returns"):
        frappe.throw("Not authorized.", frappe.PermissionError)


# A shelf bin: single letter, 1–2 digits, optional trailing letter (e.g. H14A),
# under Justyol Morocco. Same shape the pick engine treats as a real shelf.
_SHELF_REGEXP = "warehouse REGEXP '^[A-Z][0-9]{1,2}[A-Z]? - JM$'"


@frappe.whitelist()
def label_shelves():
    """Every shelf currently holding stock, grouped by zone (leading letter),
    for the shelf picker. Only shelves with stock — you can't label an empty
    one."""
    _floor_gate()
    rows = frappe.db.sql(
        f"""SELECT warehouse, COUNT(DISTINCT item_code) skus, SUM(actual_qty) units
            FROM `tabBin`
            WHERE {_SHELF_REGEXP} AND actual_qty > 0
            GROUP BY warehouse ORDER BY warehouse""", as_dict=True)
    zones = {}
    for r in rows:
        shelf = r.warehouse.replace(" - JM", "")
        zone = shelf[0]
        zones.setdefault(zone, []).append(
            {"shelf": shelf, "warehouse": r.warehouse,
             "skus": int(r.skus or 0), "units": int(r.units or 0)})
    return {"zones": [{"zone": z, "shelves": zones[z]} for z in sorted(zones)]}


@frappe.whitelist()
def shelf_items(warehouse):
    """The items sitting on one shelf, with piece counts and the SKU to print.
    Items with no custom_sku are returned flagged, not dropped — the operator
    needs to see they exist and can't be labelled until a SKU is assigned."""
    _floor_gate()
    warehouse = (warehouse or "").strip()
    if not warehouse:
        frappe.throw("No shelf given.")
    # Confirm it's a real shelf bin, not an arbitrary warehouse name posted in.
    if not frappe.db.sql(
            f"SELECT 1 FROM `tabBin` WHERE warehouse = %s AND {_SHELF_REGEXP} LIMIT 1",
            (warehouse,)):
        frappe.throw("Not a shelf.")
    rows = frappe.db.sql(
        """SELECT b.item_code, b.actual_qty AS qty,
                  i.custom_sku AS sku,
                  COALESCE(NULLIF(i.item_name,''), b.item_code) AS name, i.image
           FROM `tabBin` b
           LEFT JOIN `tabItem` i ON i.name = b.item_code
           WHERE b.warehouse = %s AND b.actual_qty > 0
           ORDER BY i.custom_sku""", (warehouse,), as_dict=True)
    items = [{
        "itemCode": r.item_code, "sku": (r.sku or "").strip(),
        "name": r.name, "qty": int(r.qty or 0), "image": r.image or "",
        "noSku": not (r.sku or "").strip(),
    } for r in rows]
    return {
        "shelf": warehouse.replace(" - JM", ""),
        "warehouse": warehouse,
        "items": items,
        "skus": len(items),
        "units": sum(i["qty"] for i in items),
        "noSkuCount": sum(1 for i in items if i["noSku"]),
    }
