"""Shared utilities for the Logistics Portal API.

Mirrors the supplier_portal pattern: small, dependency-free helpers for
validation, sanitization, and Frappe-side defensiveness used across the
api/ modules.
"""
import frappe
from frappe import _


# Single source of truth for the operating company.
JUSTYOL_COMPANY = "Justyol Morocco"

# Root of the warehouse tree everything lives under.
SOFT_WAREHOUSE = "Soft Warehouse - JM"


def escape_like(value):
    """Escape LIKE special characters (%, _, \\) in search strings."""
    if not value:
        return value
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def validate_pagination(page=1, page_size=20, max_page_size=200):
    """Validate and normalize pagination parameters.

    Returns (page, page_size, offset) with safe values.
    """
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(max(1, int(page_size)), max_page_size)
    except (TypeError, ValueError):
        page_size = 20
    return page, page_size, (page - 1) * page_size


def clamp_int(value, lo, hi, default):
    """Parse `value` to int and clamp into [lo, hi], falling back to default."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def item_has_field(fieldname):
    """True if the Item DocType has the given (custom) field. Cached per request."""
    return bool(frappe.get_meta("Item").has_field(fieldname))


def sql_in_list(values):
    """Build a safe, escaped comma-separated SQL list from trusted/untrusted strings.

    Each value is passed through frappe.db.escape, so this is injection-safe even
    for user-supplied values. Returns "''" for an empty input so `IN (...)` stays valid.
    """
    if not values:
        return "''"
    return ", ".join(frappe.db.escape(v) for v in values)
