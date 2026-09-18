"""Shared utilities for the Logistics Portal API.

Mirrors the supplier_portal pattern: small, dependency-free helpers for
validation, sanitization, and Frappe-side defensiveness used across the
api/ modules.
"""
import re

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


def clamp_item_names(doc, method=None):
    """Shopify writes product titles well past 140 characters and this site
    stores them whole (Item.item_name is TEXT). The sales-side child tables
    were widened to match long ago — but Stock Entry Detail and Stock
    Reconciliation Item still carry varchar(140), and Frappe force-fetches
    the full title into them AFTER any value we set, then refuses the whole
    document for the overflow. Runs as the validate doc-event (after the
    fetch, before the length check) and slices the display copy to fit —
    a count or a move must never be refused over a label.
    """
    for row in doc.get("items") or []:
        v = row.get("item_name")
        if not v:
            continue
        df = row.meta.get_field("item_name")
        if not df or df.fieldtype not in ("Data", "Small Text"):
            continue
        limit = frappe.utils.cint(df.get("length")) or 140
        if len(v) > limit:
            row.item_name = v[:limit]


# ── phone search ──────────────────────────────────────────────────────────
# Moroccan numbers reach this database in every shape a human can type.
# Measured 2026-09-18 over 30 days of orders: 5,598 stored as "+212 …" and
# ALL of them carry spaces inside the digits ("+212 6 79 48 19 93"), 4,436 as
# "0…", 599 as "212…", plus "+0661225251" and a handful of others. A plain
# LIKE on the stored text therefore finds almost nothing — searching that
# customer's real number returned zero rows.
#
# So both sides are reduced to digits and compared by the TAIL. Reducing the
# column costs a scan, but the screens that use this are already windowed to
# a couple of thousand parcels: 62 ms measured, against 27 ms for the query
# with no search at all.

_PHONE_MIN = 4


def phone_digits(q):
    """The national part of whatever the agent typed, or "" if that is not a
    phone number at all. 0679481993, 212679481993, +212 6 79 48 19 93 and
    679481993 all reduce to the same thing, which is the point."""
    raw = str(q or "").strip()
    if not raw:
        return ""
    # A name with a digit in it is not a phone number; anything but digits and
    # the punctuation people put IN numbers disqualifies the string.
    if re.search(r"[^0-9+()\-. ]", raw):
        return ""
    d = re.sub(r"\D", "", raw)
    if d.startswith("212"):
        d = d[3:]
    d = d.lstrip("0")
    return d if len(d) >= _PHONE_MIN else ""


def phone_tail_sql(col, key="ph"):
    """Match `col` against the %(key)s param by tail, ignoring formatting.

    `col` is spliced into a COALESCE, so several columns may be passed as one
    comma-separated string to fall back between them.

    Anchored at the END on purpose: a floating match turns a six-digit query
    into a hit on the country code — 127605 matched +212760553141 through the
    "2127605" that a "212" prefix creates. The end of a number is also how
    people quote one back over the phone."""
    return f"REGEXP_REPLACE(COALESCE({col}, ''), '[^0-9]', '') LIKE %({key})s"
