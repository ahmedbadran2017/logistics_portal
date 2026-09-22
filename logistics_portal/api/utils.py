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


def resolve_order(order):
    """The real Sales Order name behind whatever the UI sent.

    246,701 of the 257,939 Morocco orders — 96% — are NAMED with a leading
    '#', and a URL cannot carry one: '#' opens the fragment, so every link
    into the order screen strips it and the route param reads '261108' for
    an order actually called '#261108'. orders.detail has always put it back
    on its way in; nothing else did, so every other endpoint the order
    screen calls was handed a name that does not exist. "Marquer urgent" and
    the customer-service hand-over both answered "Unknown order." on 96% of
    orders (2026-09-22).

    A no-op for callers that already pass the right name — the boards do —
    so it is safe to put in front of any of them. Returns None when nothing
    matches, which is a real unknown order rather than a punctuation
    accident.
    """
    raw = (order or "").strip()
    if not raw:
        return None
    for cand in (raw, raw.lstrip("#"), "#" + raw.lstrip("#")):
        if cand and frappe.db.exists("Sales Order", cand):
            return cand
    return None


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


def release_unique_identity(old):
    """Free the UNIQUE external ids on an order being replaced by a copy.

    An amend is cancel-the-original, insert-an-amended-copy. `custom_youcan_
    order_id` carries a DB unique index, so the copy collided with the shell
    it replaces and the agent got "YouCan Order ID must be unique" — measured
    on production 2026-09-22, that field is set on 4,611 of the 11,352 orders
    of the last 30 days, so the Change-the-order button was dead for 41% of
    the lane while working fine on the rest. It was tested on a Shopify-only
    order, which is why it looked fixed.

    The id MOVES to the replacement rather than being dropped from it. It is
    the reference the agent reads to the customer (orders.detail serves it as
    `ref`), and every one of the 8,491 values on the site is distinct, so it
    identifies this sale and the live order is the sale. Dropping it would
    silently blank that reference on the orders most likely to need it.

    NB merge does the opposite on purpose — _strip_external_identity() clears
    the ids on the COPY, because a merge is many orders into one and no single
    id can honestly survive. Amend is one-for-one, so the id survives.

    Driven off the meta's `unique` flag rather than a hardcoded name: the next
    unique custom field somebody adds would otherwise break this button again,
    silently and only for the orders that carry it.

    Called AFTER cancel() and BEFORE the copy is inserted. update_modified is
    off so the cancelled shell keeps the timestamp the cancel wrote."""
    moved = []
    for f in old.meta.get("fields", {"unique": 1}):
        if f.fieldtype not in ("Data", "Small Text", "Link"):
            continue
        if not old.get(f.fieldname):
            continue
        moved.append(f.fieldname)
        old.db_set(f.fieldname, None, update_modified=False)
    return moved


def submit_new_sales_order(doc):
    """Submit a Sales Order that was just inserted, in a way that survives
    the other apps' hooks.

    THE BUG THIS EXISTS FOR, measured on production 2026-09-21:

    ecommerce_integrations hooks Sales Order `on_update`, which fires inside
    insert(), and its last line is

        frappe.db.set_value("Sales Order", self.name, "custom_items_count", n)

    with update_modified left at its default True. Document.db_set skips the
    timestamp while a save is in flight — it checks frappe.flags.currently_saving
    — but frappe.db.set_value has no such guard, so it stamps a fresh
    `modified` into the row and leaves the in-memory copy holding the old
    one. submit() is a SECOND save, so it runs check_if_latest, compares the
    two, and refuses with "Document has been modified after you have opened
    it". Deterministic, not intermittent: the hook has no condition beyond
    "the order has items".

    Every other order flow escapes it by inserting already submitted — one
    save, so check_if_latest never runs. Only insert-then-submit is exposed,
    and the portal did that in exactly three places. All three were dead:

        confirmation.amend_order   0 amended orders since it shipped
        orders.reship              0 "Reshipped as" comments, ever
        orders._do_merge           0 "Merged from" comments, ever

    while every neighbouring action — redeliver 160, returnreq 230, cancel
    33 — worked fine. Three separate features, one missing line, and nobody
    could tell because the error blamed a document conflict.

    The cure is one SELECT: re-read so the doc carries whatever the hooks
    wrote. Patching a third-party app we do not own was the alternative.
    """
    doc.reload()
    doc.flags.ignore_permissions = True
    doc.submit()
    return doc
