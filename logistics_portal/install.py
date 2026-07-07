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
]


def ensure_indexes():
    for doctype, fields, name in INDEXES:
        try:
            frappe.db.add_index(doctype, fields, index_name=name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"logistics_portal.ensure_indexes {doctype}")
