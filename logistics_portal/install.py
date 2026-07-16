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
    # Cockpit breach counts / breached_list / the 10-min audit engine all
    # filter DNs by SLA status within a posting window.
    ("Delivery Note", ["custom_sla_status", "posting_date"], "lp_dn_sla_idx"),
    # manifest_scan / ready-parcels NOT-IN / shipped-stage rows join on the
    # child table's delivery_note (parent is indexed by default; this isn't).
    ("Shipment Delivery Note", ["delivery_note"], "lp_sdn_dn_idx"),
    # Board counts + intake filter Confirmed orders by creation window.
    ("Sales Order", ["custom_sales_status", "creation"], "lp_so_sales_creation_idx"),
    # Contact Center my-day tallies filter Comments by owner+today, and the
    # section reports scan by doctype+window. tabComment is 2.6M rows with no
    # index on either — measured 31s per board load on the live site without
    # these.
    ("Comment", ["owner", "creation"], "lp_comment_owner_idx"),
    ("Comment", ["reference_doctype", "creation"], "lp_comment_dt_idx"),
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
    # Sorting-station progress: units of this line allocated to its order at
    # the sort wall (independent of the shelf-side custom_scanned_qty).
    {"fieldname": "custom_sorted_qty", "label": "Sorted Qty", "fieldtype": "Int",
     "default": "0", "read_only": 1, "no_copy": 1, "in_list_view": 0},
]


_DN_EXC_FIELDS = [
    # Exceptions triage: the recorded decision per failed parcel. Turns the
    # exceptions pile into a worked queue (who decided what, when).
    {"fieldname": "custom_exception_action", "label": "Exception Action",
     "fieldtype": "Select", "options": "\nRedeliver\nReturn Requested\nResolved",
     "read_only": 1, "no_copy": 1, "hidden": 1},
    {"fieldname": "custom_exception_actioned_at", "label": "Exception Actioned At",
     "fieldtype": "Datetime", "read_only": 1, "no_copy": 1, "hidden": 1},
]

# Contact Center lane 3 — CS tickets ride the stock ERPNext Issue doctype;
# these fields tie a ticket to the COD reality (phone, order, channel, agent).
_ISSUE_FIELDS = [
    {"fieldname": "custom_phone", "label": "Customer Phone", "fieldtype": "Data",
     "in_standard_filter": 1, "no_copy": 1},
    {"fieldname": "custom_order", "label": "Sales Order", "fieldtype": "Data", "no_copy": 1},
    {"fieldname": "custom_channel", "label": "Channel", "fieldtype": "Select",
     "options": "\nwhatsapp\nphone\nmanual", "no_copy": 1},
    {"fieldname": "custom_category", "label": "Category", "fieldtype": "Data", "no_copy": 1},
    {"fieldname": "custom_agent", "label": "Agent", "fieldtype": "Data", "no_copy": 1},
]

# Inbox marker on the third-party WhatsApp Message doctype: which incoming
# messages the CS lane has already turned into tickets / dismissed.
_WA_FIELDS = [
    {"fieldname": "custom_lp_handled", "label": "LP Handled", "fieldtype": "Check",
     "default": "0", "read_only": 1, "no_copy": 1, "hidden": 1},
]


def ensure_cs_fields():
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        payload = {"Issue": _ISSUE_FIELDS}
        if frappe.db.exists("DocType", "WhatsApp Message"):
            payload["WhatsApp Message"] = _WA_FIELDS
        create_custom_fields(payload, ignore_validate=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.ensure_cs_fields")


_SO_CONTACT_FIELDS = [
    # Contact Center (confirmation lane): when the call happened, how many
    # times, and when to retry. The WhatsApp automation stays first-line;
    # these track the human tail it can't close.
    # NB: WHO owns the order is custom_allocated_to — an existing Link->User
    # field the business already runs on (17 agents live on it, the desk's
    # confirmation dashboard reports off it). Do not add a second one.
    {"fieldname": "custom_call_attempts", "label": "Call Attempts", "fieldtype": "Int",
     "default": "0", "read_only": 1, "no_copy": 1, "hidden": 1},
    {"fieldname": "custom_last_call_at", "label": "Last Call At", "fieldtype": "Datetime",
     "read_only": 1, "no_copy": 1, "hidden": 1},
    {"fieldname": "custom_next_call_at", "label": "Next Call At", "fieldtype": "Datetime",
     "read_only": 1, "no_copy": 1, "hidden": 1},
]

_SO_SHORT_FIELDS = [
    # Set when a picker reports the item physically missing (short pick):
    # batching skips the order for 24h so it doesn't bounce straight back
    # onto the next pick list while the shelf is still empty.
    {"fieldname": "custom_short_picked_at", "label": "Short Picked At",
     "fieldtype": "Datetime", "read_only": 1, "no_copy": 1, "hidden": 1},
]


def ensure_pick_fields():
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
        create_custom_fields({"Pick List Item": _PLI_FIELDS,
                              "Sales Order": _SO_SHORT_FIELDS + _SO_CONTACT_FIELDS,
                              "Delivery Note": _DN_EXC_FIELDS}, ignore_validate=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.ensure_pick_fields")
