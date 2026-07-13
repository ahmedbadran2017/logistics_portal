"""Post-migrate setup: performance indexes the board queries depend on.

The portal filters Sales Orders by custom status fields and anti-joins Pick
List Items on every board request; without these indexes each request scans
30k+ rows (~4-8s measured on the live bench — 0.3-0.6s after indexing).
frappe.db.add_index is idempotent, so this is safe to run on every migrate.
"""

import frappe


INDEXES = [
    ("Sales Order", ["custom_logistics_status", "custom_sales_status"], "lp_logistics_status_idx"),
    ("Pick List Item", ["sales_order"], "lp_pli_so_idx"),
    ("Delivery Note Item", ["against_sales_order"], "lp_dni_so_idx"),
    ("Delivery Note", ["custom_track_shipment_status"], "lp_dn_track_idx"),
    # SKU lookup scans 151k Items by custom_sku — index it.
    ("Item", ["custom_sku"], "lp_item_sku_idx"),
]


def ensure_indexes():
    for doctype, fields, name in INDEXES:
        try:
            frappe.db.add_index(doctype, fields, index_name=name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"logistics_portal.ensure_indexes {doctype}")


# Catalog Hub status fields on Item — populated by catalog_hub.sync (read-only
# mirror of the live Shopify product/variant state).
_CATALOG_FIELDS = [
    {"fieldname": "custom_shopify_status", "label": "Shopify Status", "fieldtype": "Data",
     "read_only": 1, "no_copy": 1, "in_standard_filter": 1,
     "description": "ACTIVE / ARCHIVED / DRAFT / DELETED / UNMAPPED — mirrored from Shopify by Catalog Hub"},
    {"fieldname": "custom_variant_live", "label": "Shopify Variant Live", "fieldtype": "Check",
     "read_only": 1, "no_copy": 1,
     "description": "1 if this item's Shopify variant still exists"},
    {"fieldname": "custom_shopify_synced_on", "label": "Shopify Status Synced On",
     "fieldtype": "Datetime", "read_only": 1, "no_copy": 1},
]


def ensure_catalog_fields():
    """Create the Catalog Hub status fields on Item (idempotent)."""
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        create_custom_fields({"Item": _CATALOG_FIELDS}, ignore_validate=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.ensure_catalog_fields")


# Scan-to-pick progress: how many units of a Pick List line the picker has
# scanned off the shelf (persisted so it survives a reload / device switch).
_PLI_FIELDS = [
    {"fieldname": "custom_scanned_qty", "label": "Scanned Qty", "fieldtype": "Int",
     "default": "0", "read_only": 1, "no_copy": 1, "in_list_view": 0},
]


def ensure_pick_fields():
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        create_custom_fields({"Pick List Item": _PLI_FIELDS}, ignore_validate=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.ensure_pick_fields")
