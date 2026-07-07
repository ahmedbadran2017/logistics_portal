"""Zone topology + classification for the warehouse restock engine.

Ports the constants that were hard-coded in the `zone-restock-intelligence`
Web Page into one server-side place. Stock flows from SOURCE zones
(leaf warehouses holding returns / freshly-received / slow stock) into DEST
zones (the active selling zones, mostly warehouse groups).

Zone lft/rgt boundaries are read live from the Warehouse tree so this keeps
working if the tree is rebuilt — we never hard-code lft/rgt numbers.
"""
import frappe

from logistics_portal.api.utils import JUSTYOL_COMPANY

# Leaf warehouses we pull stock OUT of.
SOURCE_ZONES = [
    "Return Zone - JM",
    "Receiving Zone - JM",
    "SLOW ZONE - JM",
]

# Destination zones we push stock INTO. key/label drive the UI; `name` is the
# warehouse (group or leaf) whose subtree holds the zone's stock.
DEST_ZONES = [
    {"name": "FAST ZONE - JM", "key": "fast", "label": "FAST ZONE"},
    {"name": "Textile Zone - JM", "key": "textile", "label": "Textile Zone"},
    {"name": "MU Zone - JM", "key": "mu", "label": "MU Zone"},
    {"name": "Accessory Zone - JM", "key": "accessory", "label": "Accessory Zone"},
    {"name": "Cosmetic zone - JM", "key": "cosmetic", "label": "Cosmetic Zone"},
]

DEFAULT_DEST = "FAST ZONE - JM"

# item_group keyword -> dest zone name, applied when sales history can't place
# an item. Order matters: first hit wins.
_GROUP_RULES = [
    (("cosmetic", "makeup", "skin", "parfum"), "Cosmetic zone - JM"),
    (("accessory", "bag", "wallet", "card holder", "hand bag"), "Accessory Zone - JM"),
    (("shoe",), "MU Zone - JM"),
    ((
        "textile", "shirt", "dress", "jeans", "jacket", "pant", "short", "polo",
        "sweat", "pajam", "set", "pull", "coat", "blaz", "jogg", "kimono", "mayo",
        "legging", "vest", "salopette", "overalls", "jumpsuit", "cardigan",
        "bonnet", "baby",
    ), "Textile Zone - JM"),
]


def get_zone_topology():
    """Return (source_warehouses, dest_defs) where dest_defs each carry live lft/rgt.

    dest_defs: [{name, key, label, lft, rgt}], skipping any zone missing from the tree.
    """
    names = [z["name"] for z in DEST_ZONES]
    rows = frappe.get_all(
        "Warehouse",
        filters={"name": ["in", names]},
        fields=["name", "lft", "rgt"],
    )
    bounds = {r["name"]: r for r in rows}
    dest_defs = []
    for z in DEST_ZONES:
        b = bounds.get(z["name"])
        if b and b["lft"] is not None:
            dest_defs.append({**z, "lft": b["lft"], "rgt": b["rgt"]})
    return list(SOURCE_ZONES), dest_defs


def zone_for_lft(lft, dest_defs):
    """Return the dest zone `name` whose subtree contains `lft`, or None."""
    if lft is None:
        return None
    for z in dest_defs:
        if z["lft"] <= lft <= z["rgt"]:
            return z["name"]
    return None


def detect_zone_by_group(item_group):
    """Fallback classification by item_group keywords. Returns a dest zone name."""
    if not item_group:
        return DEFAULT_DEST
    g = item_group.lower()
    for keywords, zone in _GROUP_RULES:
        for kw in keywords:
            if kw in g:
                return zone
    return DEFAULT_DEST
