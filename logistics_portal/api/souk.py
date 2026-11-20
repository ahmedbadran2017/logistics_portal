"""Souk sourcing — buying new products in the wholesale market (Derb Omar),
from the buyer's phone to a Live product.

Phase 1 (this module): the custody cash (العهدة), the purchase, buy-again,
and the launch board. Receiving with good / broken / short, the studio
samples and the photo/content/review stages follow on the same records.

The one rule everything else rests on: the product is born on SHOPIFY, as a
DRAFT, at the moment of purchase. 99.6% of the items since September were
born there (12,367 / 12,422) and the item code IS the Shopify variant id; an
item made by hand in Next is an orphan the sync never adopts. So a buy here
creates the Draft (title, vendor = our house brand, one variant per colour ×
size, SKU, price, cost) and the products/create webhook already running on
prod (ecommerce_integrations.shopify.product.sync_product_from_webhook —
measured: it syncs drafts, 39 of its last 60 calls) creates the Next items
with custom_sku filled. If the webhook is late we call the same sync
ourselves. Nobody types an item code.

Who is who on the paper (Ahmed, 2026-11-17):
* the STALL is the Supplier — PO, invoice, Debit Note, its money;
* the website shows a HOUSE BRAND by category (JHome / JWomen / JMen /
  JKids) as the Shopify vendor. ee writes the vendor into
  Item.default_supplier, so the real stall is read from the PO, never from
  the item. House brands have no fulfillment model: their products are our
  own stock, never consignment (consignment keys on the item's supplier
  model, see consignment.py).

The cycle (Ahmed, 2026-11-19): the souk makes the Purchase Order and says
how the stall is paid — cash, cheque (number, date), bank transfer or on
credit (due date). Receiving makes the Purchase Receipt; the Purchase
Invoice and the payment are the accountant's, on his own portal. Accounting
closes the loop, so a purchase is never blocked on a custody.

The custody (العهدة) is optional: the accountant hands the buyer cash and
opens a trip; a CASH purchase is linked to the buyer's open trip (if any)
and deducted from it; at close the buyer hands back what is left and the
accountant counts it. Cash beyond the custody, or cash with no trip, is
allowed — accounting settles the difference. A purchase with no receipt
carries a substitute (photo of the goods + the stall's phone) that the
accountant approves.

Storage follows the app's pattern: two custom doctypes created on migrate
(no fixture files), a few custom fields on Purchase Order, settings in
defaults.
"""

import json
import math
import re
from contextlib import contextmanager

import frappe
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime, nowdate, time_diff_in_hours

COMPANY = "Justyol Morocco"
DT_TRIP = "LP Souk Trip"
DT_PRODUCT = "LP Souk Product"
SETTINGS_KEY = "lp_souk_settings"
SUPPLIER_GROUP = "Souk Suppliers"
RECEIVING_WH = "Receiving Zone - JM"
# A 13-character Code128B SKU on the 50 mm shelf label prints a ≈0.25 mm
# module — the smallest the floor scanners read (shelf-label work, 2026-10).
SKU_MAX = 13

# Each stage is the QUEUE a card waits in (its days = that queue's deadline):
# bought → receiving; photos → in-house photos (floor, 24 h); studio → the
# finals (marketing, 3 days); content; review; then live.
STAGES = ["buying", "bought", "photos", "studio", "content", "review", "live", "dropped"]

DEFAULT_SETTINGS = {
    "skuPrefix": "SK",
    "skuStart": 100,
    "custodyAccount": "",          # empty = PO only, accountant books it
    "categories": [
        {"key": "kitchen", "ar": "المطبخ", "fr": "Cuisine", "productType": "Cuisine", "brand": "JHome"},
        {"key": "home", "ar": "الديكور والمنزل", "fr": "Maison & Déco", "productType": "Maison", "brand": "JHome"},
        {"key": "storage", "ar": "التخزين والتنظيم", "fr": "Rangement", "productType": "Rangement", "brand": "JHome"},
        {"key": "women", "ar": "نسائي", "fr": "Femme", "productType": "Femme", "brand": "JWomen"},
        {"key": "men", "ar": "رجالي", "fr": "Homme", "productType": "Homme", "brand": "JMen"},
        {"key": "kids", "ar": "أطفال", "fr": "Enfants", "productType": "Enfants", "brand": "JKids"},
    ],
    # The storefront is French-first: the variant shows the French name; the
    # code goes into the SKU; Arabic is for the buyer's screen.
    "colors": [
        {"code": "RED", "fr": "Rouge", "ar": "أحمر"},
        {"code": "BLU", "fr": "Bleu", "ar": "أزرق"},
        {"code": "GRN", "fr": "Vert", "ar": "أخضر"},
        {"code": "BLK", "fr": "Noir", "ar": "أسود"},
        {"code": "WHT", "fr": "Blanc", "ar": "أبيض"},
        {"code": "BEI", "fr": "Beige", "ar": "بيج"},
        {"code": "BRN", "fr": "Marron", "ar": "بني"},
        {"code": "GRY", "fr": "Gris", "ar": "رمادي"},
        {"code": "PNK", "fr": "Rose", "ar": "وردي"},
        {"code": "YEL", "fr": "Jaune", "ar": "أصفر"},
        {"code": "ORG", "fr": "Orange", "ar": "برتقالي"},
        {"code": "PUR", "fr": "Violet", "ar": "بنفسجي"},
        {"code": "NAV", "fr": "Bleu marine", "ar": "كحلي"},
        {"code": "GLD", "fr": "Doré", "ar": "ذهبي"},
        {"code": "SLV", "fr": "Argenté", "ar": "فضي"},
        {"code": "NAT", "fr": "Naturel", "ar": "طبيعي"},
        {"code": "MLT", "fr": "Multicolore", "ar": "متعدد الألوان"},
    ],
    # Days a card may sit in a stage before it is late (alerts repeat daily).
    "stageDays": {"bought": 2, "photos": 1, "studio": 3, "content": 2, "review": 1},
    "escalateDays": 21,
    # Target from receipt to Live, in days (the board's headline number).
    "launchDays": 5,
    # Receiving: pieces of each new product that go to the studio first.
    "studioSamples": 3,
    # The selling price is a formula (Ahmed 2026-11-20): cost HT + margin %,
    # + TVA % on the total, rounded UP to the whole dirham.
    "priceMargin": 50,
    "priceVat": 20,
    # Sales channels a souk product is published to; empty = whatever the
    # last product published on Shopify uses. Remembered at each publish.
    "publishChannels": [],
    # Breakage that is OURS, each in its own account (Ahmed, 2026-11-17).
    # Empty = the pieces wait in Defective Items as stock until the
    # accountant names the account; nothing is guessed.
    "transportLossAccount": "",
    "warehouseLossAccount": "",
    # The studio's web pack (souk_ai.py): off until the manager enables it
    # and saves the provider key. monthlyCap = images per month, 0 = no cap.
    "aiWebPack": {"enabled": False, "auto": True, "model": "bria/rmbg-3", "monthlyCap": 300,
                  "set": False, "setModel": "openai/gpt-image-2.6/flare/edit"},
    "aiContent": {"enabled": False, "model": "claude-opus-5-5", "arabic": "msa", "monthlyCap": 300},
}
STUDIO_WH = "Studio - JM"
DEFECTIVE_WH = "Defective Items - JM"
SOFT_PARENT = "Soft Warehouse - JM"
LABEL_STATION = "souk"


# --- schema ------------------------------------------------------------------

def ensure_doctype():
    """Create the two doctypes, the PO fields and the stall supplier group.
    Custom doctypes: live in the DB, no schema files, safe to run every time."""
    try:
        _ensure_trip()
        _ensure_product()
        _add_missing_fields(DT_TRIP, TRIP_LATER_FIELDS)
        _add_missing_fields(DT_PRODUCT, PRODUCT_LATER_FIELDS)
        _sync_stage_options()
        _ensure_po_fields()
        _ensure_studio()
        try:
            # Selection (souk_picks): its own doctypes; a failure there must
            # not stop the rest of the souk from installing.
            from logistics_portal.api import souk_picks
            souk_picks.ensure()
        except Exception:
            frappe.log_error(frappe.get_traceback()[:2000], "souk_picks.ensure")
        if not frappe.db.exists("Supplier Group", SUPPLIER_GROUP):
            frappe.get_doc({"doctype": "Supplier Group", "supplier_group_name": SUPPLIER_GROUP,
                            "parent_supplier_group": "All Supplier Groups"}).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "souk.ensure_doctype")


def _ensure_trip():
    if frappe.db.exists("DocType", DT_TRIP):
        return
    frappe.get_doc({
        "doctype": "DocType", "name": DT_TRIP, "module": "Core", "custom": 1,
        "naming_rule": "Autoincrement", "autoname": "autoincrement",
        "track_changes": 1,
        "fields": [
            {"fieldname": "buyer", "fieldtype": "Data", "label": "Buyer (user)", "reqd": 1, "in_list_view": 1},
            {"fieldname": "place", "fieldtype": "Data", "label": "Market"},
            {"fieldname": "status", "fieldtype": "Select", "label": "Status",
             "options": "Open\nClosed\nCounted", "default": "Open", "in_list_view": 1},
            {"fieldname": "cash_given", "fieldtype": "Currency", "label": "Cash handed out", "in_list_view": 1},
            {"fieldname": "opened_by", "fieldtype": "Data", "label": "Handed out by"},
            {"fieldname": "transport_cost", "fieldtype": "Currency", "label": "Transport"},
            {"fieldname": "transport_receipt", "fieldtype": "Attach Image", "label": "Transport receipt"},
            {"fieldname": "closed_at", "fieldtype": "Datetime", "label": "Closed at"},
            {"fieldname": "expected_back", "fieldtype": "Currency", "label": "Expected back at close"},
            {"fieldname": "counted_cash", "fieldtype": "Currency", "label": "Counted back"},
            {"fieldname": "counted_by", "fieldtype": "Data", "label": "Counted by"},
            {"fieldname": "counted_at", "fieldtype": "Datetime", "label": "Counted at"},
            {"fieldname": "note", "fieldtype": "Small Text", "label": "Note"},
        ],
        "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}],
    }).insert(ignore_permissions=True)


# Fields added after the doctype first shipped: appended on migrate.
TRIP_LATER_FIELDS = [
    {"fieldname": "transport_lcv", "fieldtype": "Data", "label": "Transport landed cost voucher"},
]


def _add_missing_fields(dt, fields):
    doc = frappe.get_doc("DocType", dt)
    have = {f.fieldname for f in doc.fields}
    missing = [f for f in fields if f["fieldname"] not in have]
    if not missing:
        return
    for f in missing:
        doc.append("fields", f)
    doc.save(ignore_permissions=True)


def _ensure_product():
    if frappe.db.exists("DocType", DT_PRODUCT):
        return
    frappe.get_doc({
        "doctype": "DocType", "name": DT_PRODUCT, "module": "Core", "custom": 1,
        "naming_rule": "By fieldname", "autoname": "field:sku_base",
        "track_changes": 1,
        "fields": [
            {"fieldname": "sku_base", "fieldtype": "Data", "label": "SKU", "reqd": 1, "unique": 1, "in_list_view": 1},
            {"fieldname": "title", "fieldtype": "Data", "label": "Title", "in_list_view": 1},
            {"fieldname": "stage", "fieldtype": "Select", "label": "Stage",
             "options": "\n".join(STAGES), "default": "buying", "in_list_view": 1, "in_standard_filter": 1},
            {"fieldname": "stage_at", "fieldtype": "Datetime", "label": "In this stage since"},
            {"fieldname": "category", "fieldtype": "Data", "label": "Category"},
            {"fieldname": "product_type", "fieldtype": "Data", "label": "Shopify product type"},
            {"fieldname": "brand", "fieldtype": "Data", "label": "Website brand (vendor)"},
            {"fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "label": "Stall (supplier)"},
            {"fieldname": "trip", "fieldtype": "Data", "label": "Trip"},
            {"fieldname": "buyer", "fieldtype": "Data", "label": "Buyer"},
            {"fieldname": "bought_at", "fieldtype": "Datetime", "label": "Bought at"},
            {"fieldname": "units", "fieldtype": "Int", "label": "Units bought"},
            {"fieldname": "total_cost", "fieldtype": "Currency", "label": "Paid"},
            {"fieldname": "shopify_product_id", "fieldtype": "Data", "label": "Shopify product"},
            {"fieldname": "purchase_order", "fieldtype": "Data", "label": "Purchase Order"},
            {"fieldname": "purchase_invoice", "fieldtype": "Data", "label": "Purchase Invoice"},
            {"fieldname": "ref_image", "fieldtype": "Attach Image", "label": "Reference photo"},
            {"fieldname": "receipt_image", "fieldtype": "Attach Image", "label": "Receipt"},
            {"fieldname": "variants_json", "fieldtype": "Long Text", "label": "Variants"},
            {"fieldname": "error", "fieldtype": "Small Text", "label": "Last error"},
        ],
        "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}],
    }).insert(ignore_permissions=True)


PRODUCT_LATER_FIELDS = [
    {"fieldname": "photos_json", "fieldtype": "Long Text", "label": "In-house photos"},
    {"fieldname": "finals_json", "fieldtype": "Long Text", "label": "Final photos"},
    {"fieldname": "specs", "fieldtype": "Small Text", "label": "Measurements & material"},
    {"fieldname": "shopify_media", "fieldtype": "Long Text", "label": "Shopify media we pushed"},
    {"fieldname": "content_json", "fieldtype": "Long Text", "label": "Content (FR/AR, SEO, prices)"},
    {"fieldname": "shopify_collections", "fieldtype": "Long Text", "label": "Collections we joined"},
    {"fieldname": "content_by", "fieldtype": "Data", "label": "Content written by"},
    {"fieldname": "content_at", "fieldtype": "Datetime", "label": "Content sent at"},
    {"fieldname": "reject_count", "fieldtype": "Int", "label": "Times sent back by review"},
    {"fieldname": "reviewed_by", "fieldtype": "Data", "label": "Published by"},
    {"fieldname": "published_at", "fieldtype": "Datetime", "label": "Published at"},
    {"fieldname": "review_note", "fieldtype": "Small Text", "label": "Last review note"},
    # Every stage the card went through, [{s, at, by}] — stage_at alone
    # forgets the past, and the board's timings need it.
    {"fieldname": "stage_log", "fieldtype": "Long Text", "label": "Stage history"},
    # Who took the card in its current stage ("mine" on the board).
    {"fieldname": "claimed_by", "fieldtype": "Data", "label": "Claimed by"},
    # The phone's id for the purchase: a retry after a dropped connection
    # finds the product it already made instead of buying it twice.
    {"fieldname": "client_key", "fieldtype": "Data", "label": "Client request id", "unique": 1},
    {"fieldname": "dropped_from", "fieldtype": "Data", "label": "Dropped from stage"},
    # How the stall is paid, as the buyer chose it ({method, ref, due}) —
    # kept until finish_buy writes it on the PO.
    {"fieldname": "pay_json", "fieldtype": "Small Text", "label": "Payment (buyer's choice)"},
    # The studio's web pack: its job state and the suggestions nobody has
    # accepted yet (souk_ai.py).
    {"fieldname": "ai_json", "fieldtype": "Long Text", "label": "Web pack (suggestions)"},
]


def _sync_stage_options():
    """The stage list was renamed to queues before anything shipped; keep the
    Select in step and move any card that carries an old name."""
    want = "\n".join(STAGES)
    df = frappe.db.get_value("DocField", {"parent": DT_PRODUCT, "fieldname": "stage"},
                             ["name", "options"], as_dict=True)
    if df and (df.options or "") != want:
        frappe.db.set_value("DocField", df.name, "options", want, update_modified=False)
        frappe.clear_cache(doctype=DT_PRODUCT)
    frappe.db.sql(f"UPDATE `tab{DT_PRODUCT}` SET stage = 'photos' WHERE stage = 'received'")
    frappe.db.sql(f"UPDATE `tab{DT_PRODUCT}` SET stage = 'studio' WHERE stage = 'photographed'")


def _ensure_po_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({"Purchase Order": [
        {"fieldname": "custom_souk_trip", "fieldtype": "Data", "label": "Souk trip",
         "insert_after": "supplier", "read_only": 1, "no_copy": 1},
        {"fieldname": "custom_souk_product", "fieldtype": "Data", "label": "Souk product",
         "insert_after": "custom_souk_trip", "read_only": 1, "no_copy": 1},
        {"fieldname": "custom_souk_receipt", "fieldtype": "Select", "label": "Souk receipt",
         "options": "\nreceipt\nvoucher", "insert_after": "custom_souk_product", "no_copy": 1},
        {"fieldname": "custom_souk_receipt_image", "fieldtype": "Attach Image", "label": "Souk receipt photo",
         "insert_after": "custom_souk_receipt", "no_copy": 1},
        {"fieldname": "custom_souk_voucher_phone", "fieldtype": "Data", "label": "Stall phone (no receipt)",
         "insert_after": "custom_souk_receipt_image", "no_copy": 1},
        {"fieldname": "custom_souk_voucher_ok", "fieldtype": "Data", "label": "Voucher approved by",
         "insert_after": "custom_souk_voucher_phone", "read_only": 1, "no_copy": 1},
        # Receiving outcome: what arrived, what the stall owes us, the papers.
        {"fieldname": "custom_souk_received", "fieldtype": "Data", "label": "Souk receipt (PR)",
         "insert_after": "custom_souk_voucher_ok", "read_only": 1, "no_copy": 1},
        {"fieldname": "custom_souk_owed", "fieldtype": "Currency", "label": "Owed by the stall",
         "insert_after": "custom_souk_received", "read_only": 1, "no_copy": 1},
        {"fieldname": "custom_souk_debit_note", "fieldtype": "Data", "label": "Souk debit note",
         "insert_after": "custom_souk_owed", "read_only": 1, "no_copy": 1},
        {"fieldname": "custom_souk_outcome", "fieldtype": "Long Text", "label": "Souk receiving outcome",
         "insert_after": "custom_souk_debit_note", "read_only": 1, "no_copy": 1},
        # The substitute for a missing receipt: the goods' photo and the
        # stall's name as the buyer wrote them, for the accountant.
        {"fieldname": "custom_souk_voucher_photo", "fieldtype": "Attach Image", "label": "Substitute: goods photo",
         "insert_after": "custom_souk_outcome", "no_copy": 1},
        {"fieldname": "custom_souk_voucher_stall", "fieldtype": "Data", "label": "Substitute: stall name",
         "insert_after": "custom_souk_voucher_photo", "no_copy": 1},
        {"fieldname": "custom_souk_client_key", "fieldtype": "Data", "label": "Souk client request id",
         "insert_after": "custom_souk_voucher_stall", "read_only": 1, "no_copy": 1},
        # The purchase is not tied to a custody (2026-11-19): the souk makes
        # the PO and says how the stall is paid; receiving makes the PR and
        # the accountant makes the PI and the payment from his own screens.
        {"fieldname": "custom_souk_buyer", "fieldtype": "Data", "label": "Souk buyer",
         "insert_after": "custom_souk_client_key", "read_only": 1, "no_copy": 1},
        {"fieldname": "custom_souk_pay", "fieldtype": "Select", "label": "Souk payment",
         "options": "\ncash\ncheque\ntransfer\ncredit", "insert_after": "custom_souk_buyer", "no_copy": 1},
        {"fieldname": "custom_souk_pay_ref", "fieldtype": "Data", "label": "Cheque / transfer reference",
         "insert_after": "custom_souk_pay", "no_copy": 1},
        {"fieldname": "custom_souk_pay_due", "fieldtype": "Date", "label": "Payment due",
         "insert_after": "custom_souk_pay_ref", "no_copy": 1},
    ]}, ignore_validate=True)


def _ensure_studio():
    """Studio - JM: where the samples sit while they are photographed. Like
    Defective Items: rejected (ee's pick controller vetoes it) and never in
    the Shopify Warehouse Mapping (its pieces are not for sale)."""
    if frappe.db.exists("Warehouse", STUDIO_WH):
        return
    frappe.get_doc({"doctype": "Warehouse", "warehouse_name": "Studio", "company": COMPANY,
                    "parent_warehouse": SOFT_PARENT if frappe.db.exists("Warehouse", SOFT_PARENT) else None,
                    "is_group": 0, "is_rejected_warehouse": 1}).insert(ignore_permissions=True)


# --- gates & settings --------------------------------------------------------

ACCOUNT_ROLES = {"Accounts Manager", "Accounts User"}


def _role():
    from logistics_portal.api.auth import resolve_role
    return resolve_role(frappe.session.user)


def _is_accountant():
    """The accountant hands out and counts the custody: a portal manager, the
    portal 'accountant' role, or anyone with an ERPNext accounts role."""
    if _role() in ("manager", "accountant"):
        return True
    return bool(ACCOUNT_ROLES & set(frappe.get_roles(frappe.session.user)))


def _gate_view():
    if _role() not in ("manager", "sourcing", "accountant", "marketing", "content") and not _is_accountant():
        frappe.throw("Not authorized for souk sourcing.", frappe.PermissionError)


def _gate_buy():
    if _role() not in ("manager", "sourcing"):
        frappe.throw("Only buyers record purchases.", frappe.PermissionError)


def _gate_accountant():
    if not _is_accountant():
        frappe.throw("Only the accountant hands out and counts the custody.", frappe.PermissionError)


def settings():
    raw = frappe.db.get_default(SETTINGS_KEY)
    try:
        saved = json.loads(raw) if raw else {}
    except Exception:
        saved = {}
    out = json.loads(json.dumps(DEFAULT_SETTINGS))
    if isinstance(saved, dict):
        out.update({k: v for k, v in saved.items() if k in DEFAULT_SETTINGS})
    return out


# The settings screen (/souk/settings). Everything below validates what the
# owner types there, so a typo can no longer reach a SKU, a deadline or the
# books. Saves are PARTIAL: the screen sends only the keys it changed, so a
# publish that remembered its channels meanwhile is not overwritten.
SETTINGS_LOG_KEY = "lp_souk_settings_log"
ACCOUNT_KEYS = ("custodyAccount", "transportLossAccount", "warehouseLossAccount")
STAGE_DAY_KEYS = ("bought", "photos", "studio", "content", "review")
# The longest SKU a buy can make is PREFIX<n>-COL-SIZE. Colour codes are 3
# letters; the size code is the buyer's own (up to 4 characters, _size_code)
# but 3 covers every size the market sells under a short code — 2XL, 3XL,
# XXL, 42, 128. A 4-letter one (XXXL) is rare and the buy screen already
# refuses it with "use a shorter size code" when it does not fit.
SKU_ASSUMED_SIZE = 3
SKU_ASSUMED_COLOR = 3


def _sku_numbers_used(prefix):
    """The highest number already used after this prefix (Items and souk
    cards) — the same two reads as _next_sku_number, without its settings."""
    pat = "^" + re.escape(prefix) + "[0-9]+"
    hi = cint(frappe.db.sql(
        """SELECT MAX(CAST(SUBSTRING(custom_sku, %s) AS UNSIGNED)) FROM `tabItem`
           WHERE custom_sku REGEXP %s""", (len(prefix) + 1, pat + "(-|$)"))[0][0])
    hi2 = cint(frappe.db.sql(
        f"""SELECT MAX(CAST(SUBSTRING(sku_base, %s) AS UNSIGNED)) FROM `tab{DT_PRODUCT}`
            WHERE sku_base REGEXP %s""", (len(prefix) + 1, pat + "$"))[0][0])
    return max(hi, hi2)


def _longest_sku(prefix, number):
    return len(prefix) + len(str(number)) + 1 + SKU_ASSUMED_COLOR + 1 + SKU_ASSUMED_SIZE


def _as_int(v, what, lo, hi):
    if isinstance(v, bool):
        v = None
    elif isinstance(v, float) and v.is_integer():
        v = int(v)
    elif isinstance(v, str) and re.fullmatch(r"\s*-?\d+\s*", v):
        v = int(v)
    if not isinstance(v, int) or not lo <= v <= hi:
        frappe.throw(f"{what} must be a whole number from {lo} to {hi}.")
    return v


def _text(v, what, cap):
    v = re.sub(r"\s+", " ", str(v or "")).strip() if not isinstance(v, (dict, list)) else ""
    if not v:
        frappe.throw(f"{what} is empty.")
    if len(v) > cap:
        frappe.throw(f"{what} is longer than {cap} characters.")
    return v


def _clean_colors(rows):
    if not isinstance(rows, list) or not rows:
        frappe.throw("Keep at least one colour.")
    if len(rows) > 80:
        frappe.throw("At most 80 colours.")
    out, seen = [], set()
    for i, r in enumerate(rows, 1):
        if not isinstance(r, dict):
            frappe.throw(f"Colour {i} is malformed.")
        code = str(r.get("code") or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", code):
            frappe.throw(f"Colour {i}: the code must be exactly 3 letters A–Z (it goes into the SKU), not “{code}”.")
        if code in seen:
            frappe.throw(f"Colour code {code} appears twice.")
        seen.add(code)
        out.append({"code": code, "fr": _text(r.get("fr"), f"The French name of {code}", 40),
                    "ar": _text(r.get("ar"), f"The Arabic name of {code}", 40)})
    return out


def _clean_categories(rows):
    if not isinstance(rows, list) or not rows:
        frappe.throw("Keep at least one category.")
    if len(rows) > 40:
        frappe.throw("At most 40 categories.")
    out, seen = [], set()
    for i, r in enumerate(rows, 1):
        if not isinstance(r, dict):
            frappe.throw(f"Category {i} is malformed.")
        key = str(r.get("key") or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9_-]{1,30}", key):
            frappe.throw(f"Category {i}: the key must be 1–30 of a–z, 0–9, _ or -, not “{key}”.")
        if key in seen:
            frappe.throw(f"Category key {key} appears twice.")
        seen.add(key)
        out.append({"key": key,
                    "ar": _text(r.get("ar"), f"The Arabic name of {key}", 40),
                    "fr": _text(r.get("fr"), f"The French name of {key}", 40),
                    "productType": _text(r.get("productType"), f"The product type of {key}", 80),
                    "brand": _text(r.get("brand"), f"The brand of {key}", 80)})
    return out


def _clean_stage_days(v):
    if not isinstance(v, dict) or set(v) != set(STAGE_DAY_KEYS):
        frappe.throw("Deadlines need exactly these stages: " + ", ".join(STAGE_DAY_KEYS) + ".")
    return {k: _as_int(v[k], f"The deadline for {k}", 1, 30) for k in STAGE_DAY_KEYS}


def _clean_channels(v, cur):
    if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
        frappe.throw("Sales channels are malformed.")
    v = list(dict.fromkeys(x.strip() for x in v))
    if v and v != (cur or []):
        try:
            known = {p["id"] for p in _channels()[0]}
        except Exception:
            known = None   # Shopify unreachable: keep what was chosen, check at publish
        if known is not None:
            bad = [x for x in v if x not in known]
            if bad:
                frappe.throw("Unknown sales channel: " + ", ".join(bad) + ". Reload the page.")
    return v


def _clean_settings(s, cur):
    """s = only the keys being changed; cur = the settings before. Returns
    the normalised keys. Throws a readable message on the first bad one."""
    out = {}
    for key in ACCOUNT_KEYS:
        if key in s:
            out[key] = str(s.get(key) or "").strip()
    acct = out.get("custodyAccount")
    if acct and frappe.db.get_value("Account", {"name": acct, "company": COMPANY, "is_group": 0},
                                    "account_type") not in ("Cash", "Bank"):
        frappe.throw(f"{acct} is not a cash account of {COMPANY}.")
    for key in ("transportLossAccount", "warehouseLossAccount"):
        a = out.get(key)
        if a and frappe.db.get_value("Account", {"name": a, "company": COMPANY, "is_group": 0},
                                     "root_type") != "Expense":
            frappe.throw(f"{a} is not an expense account of {COMPANY}.")
    if "skuPrefix" in s:
        p = str(s.get("skuPrefix") or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{1,4}", p):
            frappe.throw("The SKU prefix must be 1 to 4 letters A–Z.")
        out["skuPrefix"] = p
    if "skuStart" in s:
        out["skuStart"] = _as_int(s.get("skuStart"), "The first SKU number", 1, 999999)
    prefix = out.get("skuPrefix", cur.get("skuPrefix"))
    start = out.get("skuStart", cint(cur.get("skuStart")))
    if (prefix != cur.get("skuPrefix") or start != cint(cur.get("skuStart"))):
        n = max(_sku_numbers_used(prefix), start - 1) + 1
        longest = _longest_sku(prefix, n)
        # Refuse only what makes it worse: if the numbers already outgrew the
        # label, a change that shortens (or keeps) the SKU must still pass.
        now = _longest_sku(cur.get("skuPrefix") or "",
                           max(_sku_numbers_used(cur.get("skuPrefix") or ""), cint(cur.get("skuStart")) - 1) + 1)
        if longest > SKU_MAX and longest > now:
            frappe.throw(f"The next SKU would be {prefix}{n}: with a colour and a size "
                         f"({prefix}{n}-RED-2XL) it is {longest} characters, and the shelf label scans "
                         f"at most {SKU_MAX}. Use a shorter prefix or a lower first number.")
    if "colors" in s:
        out["colors"] = _clean_colors(s.get("colors"))
    if "categories" in s:
        out["categories"] = _clean_categories(s.get("categories"))
    if "stageDays" in s:
        out["stageDays"] = _clean_stage_days(s.get("stageDays"))
    if "escalateDays" in s:
        out["escalateDays"] = _as_int(s.get("escalateDays"), "Escalate after (days)", 1, 90)
    if "launchDays" in s:
        out["launchDays"] = _as_int(s.get("launchDays"), "The launch target (days)", 1, 60)
    if "studioSamples" in s:
        out["studioSamples"] = _as_int(s.get("studioSamples"), "Studio samples", 0, 10)
    if "priceMargin" in s:
        out["priceMargin"] = _as_int(s.get("priceMargin"), "The margin (%)", 0, 500)
    if "priceVat" in s:
        out["priceVat"] = _as_int(s.get("priceVat"), "The TVA (%)", 0, 30)
    if "publishChannels" in s:
        out["publishChannels"] = _clean_channels(s.get("publishChannels"), cur.get("publishChannels"))
    if "aiWebPack" in s:
        from logistics_portal.api import souk_ai
        out["aiWebPack"] = souk_ai.clean_cfg(s.get("aiWebPack"))
    if "aiContent" in s:
        from logistics_portal.api import souk_write
        out["aiContent"] = souk_write.clean_cfg(s.get("aiContent"))
    return out


def _settings_log():
    try:
        log = json.loads(frappe.db.get_default(SETTINGS_LOG_KEY) or "[]")
    except Exception:
        log = []
    return log if isinstance(log, list) else []


@frappe.whitelist(methods=["POST"])
def save_settings(settings_json):
    """Managers set everything; the accountant sets the accounts. Send only
    the keys that change; returns the whole settings after the save."""
    _gate_accountant()
    try:
        s = json.loads(settings_json or "{}")
    except ValueError:
        s = None
    if not isinstance(s, dict):
        frappe.throw("Bad settings.")
    if _role() != "manager":
        s = {k: v for k, v in s.items() if k in ACCOUNT_KEYS}
    s = {k: v for k, v in s.items() if k in DEFAULT_SETTINGS}
    cur = settings()
    clean = _clean_settings(s, cur)
    changed = [k for k, v in clean.items() if cur.get(k) != v]
    if not changed:
        return cur
    cur.update(clean)
    frappe.db.set_default(SETTINGS_KEY, json.dumps(cur, ensure_ascii=False))
    log = [{"at": str(now_datetime())[:19], "by": frappe.session.user, "keys": changed}] + _settings_log()
    frappe.db.set_default(SETTINGS_LOG_KEY, json.dumps(log[:20], ensure_ascii=False))
    frappe.db.commit()
    return cur


def _house_brands(cats):
    """The website brands a category can carry. The brand is the Shopify
    vendor, and ee writes the vendor into Item.default_supplier — so a brand
    is a Supplier name. Offered: every brand in use (settings + souk cards)
    and whether a Supplier of that name exists. A new name is allowed (the
    screen says it is not a supplier yet); nothing else is guessed."""
    names = [c.get("brand") for c in cats] + [c["brand"] for c in DEFAULT_SETTINGS["categories"]]
    try:
        names += frappe.get_all(DT_PRODUCT, filters={"brand": ["is", "set"]}, pluck="brand", distinct=True)
    except Exception:
        pass
    names = sorted({(n or "").strip() for n in names if (n or "").strip()}, key=str.lower)
    sup = set()
    if names:
        for r in frappe.db.sql("""SELECT name, supplier_name FROM `tabSupplier`
                                  WHERE name IN %(n)s OR supplier_name IN %(n)s""", {"n": tuple(names)}, as_dict=True):
            sup.update({r.name, r.supplier_name})
    return [{"name": n, "supplier": n in sup} for n in names]


def _settings_usage():
    """How many souk cards use each colour / category: the screen warns
    before one in use is removed (removing only hides it from new buys)."""
    colors, cats = {}, {}
    try:
        for r in frappe.get_all(DT_PRODUCT, fields=["category", "variants_json"], limit_page_length=0):
            if r.category:
                cats[r.category] = cats.get(r.category, 0) + 1
            for code in {v.get("color") for v in (_loads(r.variants_json) or []) if isinstance(v, dict)}:
                if code:
                    colors[code] = colors.get(code, 0) + 1
    except Exception:
        pass
    return {"colors": colors, "categories": cats}


@frappe.whitelist()
def settings_boot():
    """The settings screen. Manager: everything. Accountant: the accounts."""
    _gate_accountant()
    s = settings()
    mgr = _role() == "manager"
    accounts = {
        "cash": frappe.get_all("Account", filters={"company": COMPANY, "is_group": 0,
                                                   "account_type": ["in", ["Cash", "Bank"]],
                                                   "account_currency": "MAD"},
                               pluck="name", order_by="name"),
        "expense": frappe.get_all("Account", filters={"company": COMPANY, "is_group": 0, "root_type": "Expense"},
                                  pluck="name", order_by="name", limit_page_length=0),
    }
    log = [dict(e, byName=_user_name(e.get("by"))) for e in _settings_log() if isinstance(e, dict)]
    out = {"isManager": mgr, "canEditAccounts": True, "accounts": accounts, "log": log,
           "settings": {k: s.get(k) or "" for k in ACCOUNT_KEYS}}
    if not mgr:
        return out
    channels, channels_error = [], ""
    try:
        channels = _channels()[0]
    except Exception as e:
        channels_error = str(e)[:300] or "Shopify did not answer."
    used = _sku_numbers_used(s["skuPrefix"])
    # A stageDays saved before a stage existed lacks it: show the default.
    days = s.get("stageDays") if isinstance(s.get("stageDays"), dict) else {}
    s["stageDays"] = {k: days.get(k, DEFAULT_SETTINGS["stageDays"][k]) for k in STAGE_DAY_KEYS}
    out.update({
        "settings": s,
        "skuMax": SKU_MAX, "skuUsed": used,
        "nextSku": f"{s['skuPrefix']}{_next_sku_number(s['skuPrefix'])}",
        "brands": _house_brands(s.get("categories") or []),
        "channels": channels, "channelsError": channels_error,
        "usage": _settings_usage(),
        "stages": list(STAGE_DAY_KEYS),
        "ai": _ai_settings(),
        "write": _write_settings(),
    })
    return out


def _write_settings():
    from logistics_portal.api import souk_write
    try:
        return souk_write.settings_block()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "souk._write_settings")
        return None


def _ai_settings():
    from logistics_portal.api import souk_ai
    try:
        return souk_ai.settings_block()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "souk._ai_settings")
        return None


def _user_name(user):
    if not user:
        return ""
    return frappe.db.get_value("User", user, "full_name") or user.split("@")[0]


def _has_col(dt, col):
    """A field added by this release exists only after migrate; reads and
    writes of it must not break the deploy window between code and migrate."""
    key = f"{dt}.{col}"
    # frappe.local is a werkzeug Local: no __dict__, plain attributes only.
    cache = getattr(frappe.local, "souk_cols", None)
    if cache is None:
        cache = {}
        frappe.local.souk_cols = cache
    if key not in cache:
        cache[key] = bool(frappe.db.has_column(dt, col))
    return cache[key]


def _stage_log(doc_or_raw):
    raw = doc_or_raw.get("stage_log") if hasattr(doc_or_raw, "get") else doc_or_raw
    log = _loads(raw) if isinstance(raw, str) else raw
    return log if isinstance(log, list) else []


def _set_stage(doc, stage, **extra):
    """Every stage change goes through here: it appends the card's history
    (who, when) so the board can time each stage after the card left it.
    A stage change also frees the card: the next stage's people claim it."""
    now = now_datetime()
    vals = {"stage": stage, "stage_at": now, **extra}
    if _has_col(DT_PRODUCT, "stage_log"):
        log = _stage_log(doc)
        if not log and doc.get("stage_at"):
            # A card from before the history: its current stage, as known.
            log.append({"s": doc.stage, "at": str(doc.stage_at)[:19], "by": ""})
        log.append({"s": stage, "at": str(now)[:19], "by": frappe.session.user})
        vals["stage_log"] = json.dumps(log[-80:])
    if _has_col(DT_PRODUCT, "claimed_by"):
        vals["claimed_by"] = ""
    doc.db_set(vals)


# --- custody (trips) ---------------------------------------------------------

def _trip_buys(trip):
    """Every PO bought on this trip, newest first (new products and buy-again)."""
    return frappe.db.sql(
        """SELECT po.name, po.supplier, po.grand_total, po.docstatus, po.creation,
                  po.custom_souk_product AS product, po.custom_souk_receipt AS receipt,
                  po.custom_souk_receipt_image AS receipt_image,
                  po.custom_souk_voucher_phone AS phone, po.custom_souk_voucher_ok AS voucher_ok,
                  po.custom_souk_received AS received, po.custom_souk_owed AS owed,
                  po.custom_souk_debit_note AS debit_note, {extra}
                  (SELECT SUM(qty) FROM `tabPurchase Order Item` WHERE parent = po.name) AS units
           FROM `tabPurchase Order` po
           WHERE po.custom_souk_trip = %s AND po.docstatus = 1
           ORDER BY po.creation DESC""".format(
            extra="po.custom_souk_voucher_photo AS voucher_photo, po.custom_souk_voucher_stall AS voucher_stall,"
            if _has_col("Purchase Order", "custom_souk_voucher_photo") else ""),
        (str(trip),), as_dict=True)


def _receipt_state(b):
    if b.receipt == "receipt" and b.receipt_image:
        return "ok"
    if b.receipt == "voucher":
        return "voucher_ok" if b.voucher_ok else "voucher_pending"
    return "missing"


def _trip_card(t):
    buys = _trip_buys(t.name)
    goods = sum(flt(b.grand_total) for b in buys)
    # A product still being created on Shopify has no PO yet but its money
    # has left the buyer's hand.
    pending = 0.0
    baskets = set()
    for total, pay in frappe.db.sql(
            """SELECT total_cost, {pay} FROM `tab{dt}`
               WHERE trip = %s AND stage = 'buying' AND IFNULL(purchase_order, '') = ''""".format(
                dt=DT_PRODUCT, pay="pay_json" if _has_col(DT_PRODUCT, "pay_json") else "''"),
            (str(t.name),)):
        pending += flt(total)
        pj = _loads(pay) or {}
        if pj.get("basket") and pj["basket"] not in baskets:
            # The basket's buy-again lines wait with its new products.
            baskets.add(pj["basket"])
            pending += sum(cint(a.get("qty")) * flt(a.get("cost")) for a in pj.get("again") or [])
    pending = round(pending, 2)
    goods += flt(pending)
    transport = flt(t.transport_cost)
    expected = flt(t.cash_given) - goods - transport
    titles, by_po = {}, {}
    names = [b.product for b in buys if b.product]
    if names:
        for r in frappe.get_all(DT_PRODUCT, filters={"name": ["in", names]}, fields=["name", "title", "ref_image"]):
            titles[r.name] = r
    if buys:
        for r in frappe.get_all(DT_PRODUCT, filters={"purchase_order": ["in", [b.name for b in buys]]},
                                fields=["name", "title", "ref_image", "purchase_order"], order_by="creation asc"):
            by_po.setdefault(r.purchase_order, []).append(r)
    rows = []
    for b in buys:
        p = titles.get(b.product) or {}
        cards = by_po.get(b.name) or []
        title = p.get("title") or ""
        if len(cards) > 1:
            # A basket: every product on it, the lead one first.
            title = " · ".join(c.title for c in cards)
        rows.append({
            "po": b.name, "supplier": b.supplier, "amount": flt(b.grand_total), "units": cint(b.units),
            "product": b.product or "", "title": title, "image": p.get("ref_image") or "",
            "products": [{"name": c.name, "title": c.title} for c in cards],
            "receipt": _receipt_state(b), "receiptImage": b.receipt_image or "", "phone": b.phone or "",
            "received": b.received or "", "owed": flt(b.owed), "debitNote": b.debit_note or "",
            "voucherPhoto": b.get("voucher_photo") or p.get("ref_image") or "",
            "voucherStall": b.get("voucher_stall") or "", "voucherBy": _user_name(b.voucher_ok) if b.voucher_ok else "",
            "at": str(b.creation)[:16],
        })
    missing = [r for r in rows if r["receipt"] == "missing"]
    return {
        "name": t.name, "buyer": t.buyer, "buyerName": _user_name(t.buyer), "place": t.place or "",
        "status": t.status, "cashGiven": flt(t.cash_given), "openedBy": _user_name(t.opened_by),
        "opened": str(t.creation)[:16], "goods": round(goods, 2), "transport": transport,
        "transportReceipt": t.transport_receipt or "", "expected": round(expected, 2),
        "expectedBack": flt(t.expected_back), "counted": flt(t.counted_cash),
        "countedBy": _user_name(t.counted_by), "countedAt": str(t.counted_at or "")[:16],
        "closedAt": str(t.closed_at or "")[:16], "note": t.note or "",
        "buys": rows, "missingReceipts": len([r for r in rows if r["receipt"] == "missing"]),
        "pendingVouchers": len([r for r in rows if r["receipt"] == "voucher_pending"]),
        "canClose": t.status == "Open" and not missing and not flt(pending),
        "creating": frappe.db.count(DT_PRODUCT, {"trip": str(t.name), "stage": "buying"}),
        "transportLcv": t.get("transport_lcv") or "",
        "allReceived": bool(rows) and all(r["received"] for r in rows),
        "owed": round(sum(r["owed"] for r in rows), 2),
    }


def _my_open_trip(user=None):
    user = user or frappe.session.user
    name = frappe.db.get_value(DT_TRIP, {"buyer": user, "status": "Open"}, "name", order_by="creation desc")
    return frappe.get_doc(DT_TRIP, name) if name else None


@frappe.whitelist()
def trips_boot():
    _gate_view()
    acc = _is_accountant()
    if acc:
        rows = frappe.get_all(DT_TRIP, filters={"status": ["in", ["Open", "Closed"]]},
                              fields=["*"], order_by="creation desc", limit=30)
    else:
        rows = frappe.get_all(DT_TRIP, filters={"buyer": frappe.session.user, "status": ["in", ["Open", "Closed"]]},
                              fields=["*"], order_by="creation desc", limit=5)
    done = frappe.get_all(DT_TRIP, filters={"status": "Counted"} if acc else
                          {"status": "Counted", "buyer": frappe.session.user},
                          fields=["*"], order_by="counted_at desc", limit=10)
    buyers = []
    if acc:
        buyers = [{"user": u.name, "name": u.full_name or u.name} for u in frappe.db.sql(
            """SELECT name, full_name FROM `tabUser`
               WHERE enabled = 1 AND custom_logistics_role IN ('sourcing', 'manager')
               ORDER BY full_name""", as_dict=True)]
    accounts = None
    if acc:
        s = settings()
        accounts = {
            "custody": s.get("custodyAccount") or "",
            "transportLoss": s.get("transportLossAccount") or "",
            "warehouseLoss": s.get("warehouseLossAccount") or "",
            "cashOptions": frappe.get_all("Account", filters={"company": COMPANY, "is_group": 0,
                                                              "account_type": ["in", ["Cash", "Bank"]],
                                                              "account_currency": "MAD"},
                                          pluck="name", order_by="name"),
            "expenseOptions": frappe.get_all("Account", filters={"company": COMPANY, "is_group": 0,
                                                                 "root_type": "Expense"},
                                             pluck="name", order_by="name", limit=600),
        }
    return {
        "accounts": accounts, "canReceive": _can_receive(),
        "isAccountant": acc, "canBuy": _role() in ("manager", "sourcing"), "me": frappe.session.user,
        "open": [_trip_card(t) for t in rows],
        "counted": [_trip_card(t) for t in done],
        "buyers": buyers,
    }


@frappe.whitelist(methods=["POST"])
def open_trip(buyer, cash, place=""):
    """The accountant hands the buyer the custody: one open trip per buyer."""
    _gate_accountant()
    buyer = (buyer or "").strip()
    cash = flt(cash)
    if not frappe.db.exists("User", buyer):
        frappe.throw("Unknown buyer.")
    if cash <= 0:
        frappe.throw("Cash handed out must be more than zero.")
    if _my_open_trip(buyer):
        frappe.throw(f"{_user_name(buyer)} already has an open trip. Close and count it first.")
    t = frappe.get_doc({"doctype": DT_TRIP, "buyer": buyer, "cash_given": cash,
                        "place": (place or "").strip()[:80] or "Derb Omar",
                        "status": "Open", "opened_by": frappe.session.user}).insert(ignore_permissions=True)
    frappe.db.commit()
    return _trip_card(t)


def _trip_for_write(trip):
    t = frappe.get_doc(DT_TRIP, cint(trip))
    if t.buyer != frappe.session.user and not _is_accountant():
        frappe.throw("Not your trip.", frappe.PermissionError)
    return t


@frappe.whitelist(methods=["POST"])
def set_transport(trip, amount):
    t = _trip_for_write(trip)
    if t.status != "Open":
        frappe.throw("The trip is closed.")
    t.db_set("transport_cost", max(flt(amount), 0))
    frappe.db.commit()
    return _trip_card(frappe.get_doc(DT_TRIP, t.name))


@frappe.whitelist(methods=["POST"])
def set_voucher(po, phone, stall_name="", photo=""):
    """No receipt from the stall: the substitute is a photo of the goods +
    the stall's name and phone; the accountant approves. The photo is
    uploaded first (upload_photo kind=voucher); without one, the product's
    reference photo stands in, as before."""
    po_doc = _souk_po(po)
    phone = re.sub(r"[^\d+]", "", phone or "")
    if len(phone) < 9:
        frappe.throw("Write the stall's phone number.")
    vals = {"custom_souk_receipt": "voucher", "custom_souk_voucher_phone": phone,
            "custom_souk_voucher_ok": ""}
    if _has_col("Purchase Order", "custom_souk_voucher_stall"):
        vals["custom_souk_voucher_stall"] = re.sub(r"\s+", " ", stall_name or "").strip()[:120]
        if photo and str(photo).startswith("/files/"):
            vals["custom_souk_voucher_photo"] = photo
    frappe.db.set_value("Purchase Order", po_doc.name, vals, update_modified=False)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def refuse_voucher(po, note=""):
    """The substitute does not hold up: the purchase goes back to 'receipt
    missing' and the buyer brings a real receipt or a better substitute."""
    _gate_accountant()
    po_doc = _souk_po(po)
    if po_doc.get("custom_souk_receipt") != "voucher":
        frappe.throw("No substitute receipt to refuse.")
    frappe.db.set_value("Purchase Order", po_doc.name, {"custom_souk_receipt": "", "custom_souk_voucher_ok": ""},
                        update_modified=False)
    frappe.get_doc("Purchase Order", po_doc.name).add_comment(
        "Comment", f"Souk: substitute receipt REFUSED by {_user_name(frappe.session.user)}"
                   + (f" · {(note or '').strip()[:200]}" if (note or "").strip() else "") + ".")
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def approve_voucher(po):
    _gate_accountant()
    po_doc = _souk_po(po)
    if po_doc.get("custom_souk_receipt") != "voucher":
        frappe.throw("No substitute receipt to approve.")
    frappe.db.set_value("Purchase Order", po_doc.name, "custom_souk_voucher_ok",
                        frappe.session.user, update_modified=False)
    frappe.get_doc("Purchase Order", po_doc.name).add_comment(
        "Comment", f"Souk: substitute receipt approved by {_user_name(frappe.session.user)}.")
    frappe.db.commit()
    return {"ok": True}


def _souk_po(po):
    fields = ["name", "custom_souk_trip", "custom_souk_receipt"]
    if _has_col("Purchase Order", "custom_souk_buyer"):
        fields.append("custom_souk_buyer")
    d = frappe.db.get_value("Purchase Order", po, fields, as_dict=True)
    if not d or not _is_souk_po(d):
        frappe.throw("Not a souk purchase.")
    if d.custom_souk_trip:
        _trip_for_write(d.custom_souk_trip)
    elif d.get("custom_souk_buyer") != frappe.session.user and not _is_accountant() and _role() != "manager":
        frappe.throw("Not your purchase.", frappe.PermissionError)
    return d


@frappe.whitelist(methods=["POST"])
def close_trip(trip):
    """The buyer closes the day: every purchase has a receipt or an approved
    substitute, and the cash to hand back is frozen for the count."""
    t = _trip_for_write(trip)
    if t.status != "Open":
        frappe.throw("Already closed.")
    card = _trip_card(t)
    if not card["canClose"]:
        frappe.throw("Every purchase needs a receipt photo or a substitute (stall phone) before closing.")
    if frappe.db.exists(DT_PRODUCT, {"trip": str(t.name), "stage": "buying"}):
        frappe.throw("A product is still being created on Shopify. Wait a minute and retry.")
    t.db_set({"status": "Closed", "closed_at": now_datetime(), "expected_back": card["expected"]})
    frappe.db.commit()
    return _trip_card(frappe.get_doc(DT_TRIP, t.name))


@frappe.whitelist(methods=["POST"])
def count_trip(trip, counted, note=""):
    """The accountant counts what came back. A difference stays on the trip
    under the buyer's name — recorded, not posted."""
    _gate_accountant()
    t = frappe.get_doc(DT_TRIP, cint(trip))
    if t.status != "Closed":
        frappe.throw("The buyer has not closed this trip yet.")
    if _trip_card(t)["pendingVouchers"]:
        frappe.throw("Approve or refuse the substitute receipts first.")
    counted = flt(counted)
    if counted < 0:
        frappe.throw("Counted cash cannot be negative.")
    t.db_set({"status": "Counted", "counted_cash": counted, "counted_by": frappe.session.user,
              "counted_at": now_datetime(), "note": (note or "").strip()[:280]})
    diff = round(counted - flt(t.expected_back), 2)
    t.add_comment("Comment", f"Counted {counted:,.2f} MAD back (expected {flt(t.expected_back):,.2f}; "
                             f"difference {diff:+,.2f}) by {_user_name(frappe.session.user)}.")
    frappe.db.commit()
    return _trip_card(frappe.get_doc(DT_TRIP, t.name))


# --- photos ------------------------------------------------------------------

def _read_upload(max_mb=12):
    f = (frappe.request.files or {}).get("file")
    if not f:
        frappe.throw("No photo.")
    content = f.stream.read()
    if len(content) > max_mb * 1024 * 1024:
        frappe.throw(f"Photo too large ({max_mb} MB max).")
    ext = (f.filename or "").rsplit(".", 1)[-1].lower() if "." in (f.filename or "") else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "heic"):
        frappe.throw("Photos only.")
    return content, ext


def _insert_file(kind, dt, dn, content, ext):
    """Public with an unguessable name: the accountant, the board and
    marketing must see a photo somebody else took, and none of them has rights
    on the others' private files (the souk doctypes are System Manager only;
    the portal gates). Public also lets Shopify fetch a final by its URL."""
    return frappe.get_doc({
        "doctype": "File", "file_name": f"souk-{kind}-{frappe.generate_hash(length=16)}.{ext}",
        "content": content, "attached_to_doctype": dt, "attached_to_name": str(dn), "is_private": 0,
    }).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def upload_photo(kind, target):
    """One photo from the phone. kind: ref (product reference photo), receipt
    (stall receipt on a PO or on a product still being created), transport
    (the trip's taxi receipt). Attached to its record."""
    _gate_view()
    content, ext = _read_upload()
    if kind == "transport":
        t = _trip_for_write(target)
        dt, dn, field = DT_TRIP, t.name, "transport_receipt"
    elif kind == "ref":
        _gate_buy()
        dt, dn, field = DT_PRODUCT, target, "ref_image"
    elif kind == "voucher":
        # The substitute receipt: a photo of the goods at the stall.
        _souk_po(target)
        dt, dn, field = "Purchase Order", target, (
            "custom_souk_voucher_photo" if _has_col("Purchase Order", "custom_souk_voucher_photo") else None)
    elif kind == "broken":
        # Proof for the stall (Debit Note) or for our loss accounts.
        _gate_receive()
        dt, dn, field = "Purchase Order", target, None
    elif kind == "stall":
        # The storefront, on the Supplier's own image.
        from logistics_portal.api import souk_stalls
        souk_stalls._gate()
        if frappe.db.get_value("Supplier", target, "supplier_group") != SUPPLIER_GROUP:
            frappe.throw("Unknown stall.")
        dt, dn, field = "Supplier", target, "image"
    elif kind == "receipt":
        if frappe.db.exists("Purchase Order", target):
            _souk_po(target)
            dt, dn, field = "Purchase Order", target, "custom_souk_receipt_image"
        else:
            _gate_buy()
            dt, dn, field = DT_PRODUCT, target, "receipt_image"
    else:
        frappe.throw("Unknown photo kind.")
    if not frappe.db.exists(dt, dn):
        frappe.throw("Record not found.")
    fdoc = _insert_file(kind, dt, dn, content, ext)
    if not field:
        frappe.db.commit()
        return {"url": fdoc.file_url}
    frappe.db.set_value(dt, dn, field, fdoc.file_url, update_modified=False)
    po = dn if dt == "Purchase Order" else None
    if dt == DT_PRODUCT and field == "receipt_image":
        # The PO may already exist (finish_buy ran in the same call as the buy).
        po = frappe.db.get_value(DT_PRODUCT, dn, "purchase_order") or None
    if po and kind == "receipt":
        frappe.db.set_value("Purchase Order", po, {
            "custom_souk_receipt": "receipt", "custom_souk_receipt_image": fdoc.file_url},
            update_modified=False)
    frappe.db.commit()
    return {"url": fdoc.file_url}


# --- buying ------------------------------------------------------------------

def _next_sku_number(prefix):
    s = settings()
    pat = "^" + re.escape(prefix) + "[0-9]+"
    hi = cint(frappe.db.sql(
        """SELECT MAX(CAST(SUBSTRING(custom_sku, %s) AS UNSIGNED)) FROM `tabItem`
           WHERE custom_sku REGEXP %s""", (len(prefix) + 1, pat + "(-|$)"))[0][0])
    hi2 = cint(frappe.db.sql(
        f"""SELECT MAX(CAST(SUBSTRING(sku_base, %s) AS UNSIGNED)) FROM `tab{DT_PRODUCT}`
            WHERE sku_base REGEXP %s""", (len(prefix) + 1, pat + "$"))[0][0])
    return max(hi, hi2, cint(s.get("skuStart")) - 1) + 1


def _size_code(size):
    return re.sub(r"[^A-Z0-9]", "", (size or "").upper())[:4]


def _variant_sku(base, color, size):
    parts = [base]
    if color:
        parts.append(color)
    if size:
        parts.append(_size_code(size))
    return "-".join(parts)


def _last_stall(item_code):
    r = frappe.db.sql(
        """SELECT po.supplier, poi.rate FROM `tabPurchase Order Item` poi
           JOIN `tabPurchase Order` po ON po.name = poi.parent
           WHERE poi.item_code = %s AND po.docstatus = 1
           ORDER BY po.transaction_date DESC, po.creation DESC LIMIT 1""", (item_code,), as_dict=True)
    return r[0] if r else None


@frappe.whitelist()
def buy_boot():
    _gate_view()
    s = settings()
    trip = _my_open_trip()
    stalls = frappe.db.sql(
        """SELECT s.name, s.supplier_name,
                  (SELECT MAX(po.creation) FROM `tabPurchase Order` po WHERE po.supplier = s.name) AS last
           FROM `tabSupplier` s WHERE s.supplier_group = %s AND s.disabled = 0
           ORDER BY last DESC, s.name""", (SUPPLIER_GROUP,), as_dict=True)
    return {
        "canBuy": _role() in ("manager", "sourcing"),
        "trip": _trip_card(trip) if trip else None,
        "categories": s["categories"], "colors": s["colors"],
        "skuPrefix": s["skuPrefix"], "skuMax": SKU_MAX,
        "nextSku": f"{s['skuPrefix']}{_next_sku_number(s['skuPrefix'])}",
        "skuNext": _next_sku_number(s["skuPrefix"]),
        # The selling price is computed, never typed (sell_price).
        "priceMargin": flt(s.get("priceMargin") if s.get("priceMargin") is not None else 50),
        "priceVat": flt(s.get("priceVat") if s.get("priceVat") is not None else 20),
        "basketMax": BASKET_MAX,
        "stalls": [{"name": r.name, "label": r.supplier_name or r.name} for r in stalls],
        "books": bool(s.get("custodyAccount")),
        # The way each stall was paid last time: the buyer's default for it.
        "lastPay": _last_pay_by_stall(),
    }


def _last_pay_by_stall():
    if not _has_col("Purchase Order", "custom_souk_pay"):
        return {}
    out = {}
    for r in frappe.db.sql(
            """SELECT supplier, custom_souk_pay FROM `tabPurchase Order`
               WHERE docstatus = 1 AND IFNULL(custom_souk_pay, '') != ''
               ORDER BY creation DESC LIMIT 500""", as_dict=True):
        out.setdefault(r.supplier, r.custom_souk_pay)
    return out


# --- do we already have it? -----------------------------------------------------
# Two ways in (Ahmed, 2026-11-20): the barcode printed on the box — exact,
# 47k catalogue items carry one — and the words of the name, each on its own
# and in any order ("boite rangement" finds "Boîte de rangement"; the old
# whole-phrase LIKE missed half). The catalogue is French (19 Arabic names in
# 160k), so Arabic words mostly find souk products, whose titles the buyer wrote.

_STOP = {"de", "du", "des", "la", "le", "les", "un", "une", "et", "en", "pour", "avec", "au", "aux",
         "sur", "the", "of", "and", "for", "with", "pcs", "pc", "pieces", "piece",
         "من", "في", "على", "مع", "او", "عن", "الى", "قطعه", "قطع"}
_AR_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي", "ـ": ""})


def _fold(text):
    """Lower case, no accents, no Arabic diacritics, one alef / ya / ha."""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch)).translate(_AR_FOLD)


def _tokens(q):
    out = []
    for w in re.findall(r"\w+", _fold(q)):
        if w in _STOP or len(w) < 2:
            continue
        if re.fullmatch(r"[\u0600-\u06ff]+", w) and w.startswith("ال") and len(w) >= 5:
            w = w[2:]                       # الصحون → صحون
        elif re.fullmatch(r"[a-z]+", w) and len(w) >= 5 and w[-1] in "sx":
            w = w[:-1]                      # boites → boite, plateaux → plateau
        if w not in out:
            out.append(w)
    return out[:6]


def _need(n):
    """Words that must match: all of one or two, all but one of more."""
    return n if n <= 2 else n - 1


def _barcode_norm(v):
    # Code128/39 may carry . / + _ — kept; never % or quotes (they reach LIKE).
    v = re.sub(r"\s+", "", str(v or ""))[:40]
    return v if re.fullmatch(r"[A-Za-z0-9./+_-]{4,40}", v) else ""


def _upce_to_upca(c):
    """UPC-E (8 digits, number system 0/1) → its 12-digit UPC-A."""
    if len(c) != 8 or not c.isdigit() or c[0] not in "01":
        return ""
    ns, d, chk = c[0], c[1:7], c[7]
    last = d[5]
    if last in "012":
        body = d[0:2] + last + "0000" + d[2:5]
    elif last == "3":
        body = d[0:3] + "00000" + d[3:5]
    elif last == "4":
        body = d[0:4] + "00000" + d[4]
    else:
        body = d[0:5] + "0000" + last
    return ns + body + chk


def _barcode_forms(code):
    """One product, several spellings of its number: EAN-13 ⇄ UPC-A (leading
    0), a carton's GTIN-14 (leading 0s), and a short UPC-E expanded."""
    out = [code]
    if code.isdigit():
        n = code
        if len(n) == 14 and n.startswith("0"):
            n = n[1:]
            out.append(n)
        if len(n) == 8:
            a = _upce_to_upca(n)
            if a:
                out += [a, "0" + a]
        if len(n) == 12:
            out.append("0" + n)
        elif len(n) == 13 and n.startswith("0"):
            out.append(n[1:])
    seen = []
    for f in out:
        if f not in seen:
            seen.append(f)
    return tuple(seen)


def _barcode_hits(code):
    forms = _barcode_forms(code)
    out, seen = [], set()
    for p in frappe.db.sql(
            f"""SELECT name, title, stage, supplier, ref_image, variants_json FROM `tab{DT_PRODUCT}`
                WHERE stage != 'dropped' AND ({" OR ".join(["variants_json LIKE %s"] * len(forms))})
                ORDER BY creation DESC LIMIT 5""",
            tuple(f'%"boxBarcode": "{f}"%' for f in forms), as_dict=True):
        codes = [v.get("itemCode") for v in (_loads(p.variants_json) or []) if v.get("itemCode")]
        seen.update(codes)
        out.append({"kind": "souk", "key": p.name, "sku": p.name, "title": p.title, "stage": p.stage,
                    "stall": p.supplier or "", "image": p.ref_image or "", "codes": codes, "exact": True})
    # Three indexed lookups (barcode, SKU — many catalogue SKUs ARE the EAN —
    # and the item code), each on its own: one OR / UNION subquery makes the
    # planner scan the 160k items (2.3 s on prod, 2026-11-20).
    names = set()
    for sql in ("SELECT parent FROM `tabItem Barcode` WHERE barcode IN %(f)s",
                "SELECT name FROM `tabItem` WHERE custom_sku IN %(f)s",
                "SELECT name FROM `tabItem` WHERE name IN %(f)s"):
        names.update(r[0] for r in frappe.db.sql(sql, {"f": forms}))
    found = frappe.db.sql(
        """SELECT name, custom_sku, item_name, image FROM `tabItem`
           WHERE name IN %(n)s AND disabled = 0 AND has_variants = 0 LIMIT 6""",
        {"n": tuple(names)}, as_dict=True) if names else []
    for i in found:
        if i.name in seen:
            continue
        last = _last_stall(i.name)
        out.append({"kind": "item", "key": i.name, "sku": i.custom_sku or i.name, "title": i.item_name,
                    "stage": "", "stall": (last or {}).get("supplier") or "", "image": i.image or "",
                    "codes": [i.name], "exact": True})
    return out


def _word_hits(q, category=""):
    toks = _tokens(q)
    if not toks:
        return []
    need = _need(len(toks))
    scored = []
    # Souk products: a small table, matched here so Arabic folds as it should.
    for p in frappe.db.sql(
            f"""SELECT name, title, stage, supplier, ref_image, variants_json, category FROM `tab{DT_PRODUCT}`
                WHERE stage != 'dropped' ORDER BY creation DESC LIMIT 3000""", as_dict=True):
        hay = _fold(f"{p.title} {p.name}")
        n = sum(1 for t in toks if t in hay)
        if n >= need:
            codes = [v.get("itemCode") for v in (_loads(p.variants_json) or []) if v.get("itemCode")]
            scored.append((n / len(toks) + (0.25 if category and p.category == category else 0) + 0.05, {
                "kind": "souk", "key": p.name, "sku": p.name, "title": p.title, "stage": p.stage,
                "stall": p.supplier or "", "image": p.ref_image or "", "codes": codes}))
    # The catalogue: every word on its own (the DB collation ignores accents).
    if max(len(t) for t in toks) >= 3:
        # A word with a digit may be a SKU; plain words are looked for in the
        # name only (half the scanning).
        parts, likes = [], []
        for t in toks:
            if re.search(r"\d", t):
                parts.append("(i.item_name LIKE %s OR i.custom_sku LIKE %s)")
                likes += [f"%{t}%", f"%{t}%"]
            else:
                parts.append("(i.item_name LIKE %s)")
                likes.append(f"%{t}%")
        rows = frappe.db.sql(
            f"""SELECT i.name, i.custom_sku, i.item_name, i.image, i.variant_of, ({" + ".join(parts)}) AS score
                FROM `tabItem` i WHERE i.disabled = 0 AND i.has_variants = 0 AND ({" OR ".join(parts)})
                HAVING score >= %s ORDER BY score DESC, i.modified DESC LIMIT 80""",
            tuple(likes + likes + [need]), as_dict=True)
        souk_codes = {c for _, r in scored for c in r["codes"]}
        tmpl_seen = set()
        for i in rows:
            # One line per product: ten sizes of one template are one answer.
            group = i.variant_of or i.name
            if group in tmpl_seen or i.name in souk_codes:
                continue
            tmpl_seen.add(group)
            scored.append((cint(i.score) / len(toks), {
                "kind": "item", "key": i.name, "sku": i.custom_sku or i.name, "title": i.item_name,
                "stage": "", "stall": "", "image": i.image or "", "codes": [i.name]}))
            if len(tmpl_seen) >= 12:
                break
    scored.sort(key=lambda x: -x[0])
    out = [r for _, r in scored[:10]]
    for r in out:
        if r["kind"] == "item":
            r["stall"] = (_last_stall(r["key"]) or {}).get("supplier") or ""
    return out


@frappe.whitelist()
def similar(q="", barcode="", category=""):
    """Before buying: do we already sell this? By the box's barcode (exact)
    or by the words of its name. Each answer says what is on the shelf and
    when it last sold."""
    _gate_view()
    code = _barcode_norm(barcode)
    if code:
        out = _barcode_hits(code)
    else:
        q = (q or "").strip()
        if len(q) < 3:
            return {"rows": []}
        out = _word_hits(q, category)
    # On the shelf now, and when it last sold: "we have 12" and "sold out
    # since March" are different reasons not to buy it again.
    codes = sorted({c for r in out for c in r["codes"]})
    stock, sold = {}, {}
    if codes:
        for c, qty in frappe.db.sql(
                """SELECT item_code, SUM(actual_qty) FROM `tabBin`
                   WHERE item_code IN %s AND warehouse IN (SELECT erpnext_warehouse FROM `tabShopify Warehouse Mapping`)
                   GROUP BY item_code""", (tuple(codes),)):
            stock[c] = flt(qty)
        for c, last in frappe.db.sql(
                """SELECT soi.item_code, MAX(so.transaction_date) FROM `tabSales Order Item` soi
                   JOIN `tabSales Order` so ON so.name = soi.parent
                   WHERE soi.item_code IN %s AND so.docstatus = 1
                   GROUP BY soi.item_code""", (tuple(codes),)):
            sold[c] = str(last or "")
    for r in out:
        r["stock"] = cint(sum(stock.get(c, 0) for c in r["codes"]))
        r["lastSold"] = max((sold.get(c, "") for c in r["codes"]), default="")
        r.pop("codes")
    return {"rows": out, "barcode": code}


def _attach_barcode(item_code, code):
    """Teach the catalogue the box's barcode, so the next buy finds it. A
    child row written directly: saving the Item would run the Shopify hooks."""
    code = _barcode_norm(code)
    if not code or not item_code or not frappe.db.exists("Item", item_code):
        return False
    if frappe.db.sql("SELECT 1 FROM `tabItem Barcode` WHERE barcode IN %s LIMIT 1", (_barcode_forms(code),)):
        return False
    idx = cint(frappe.db.sql("SELECT MAX(idx) FROM `tabItem Barcode` WHERE parent = %s", item_code)[0][0]) + 1
    frappe.get_doc({"doctype": "Item Barcode", "parent": item_code, "parenttype": "Item",
                    "parentfield": "barcodes", "idx": idx, "barcode": code}).db_insert()
    return True


def _client_key(p):
    """The phone's id for one request (a uuid). Only letters, digits and
    dashes; empty when an old bundle sends none."""
    k = re.sub(r"[^A-Za-z0-9-]", "", str((p or {}).get("clientKey") or ""))[:64]
    return k if len(k) >= 8 else ""


PAY_METHODS = ("cash", "cheque", "transfer", "credit")


def _clean_pay(v):
    """How the stall is paid: cash (on the buyer's custody when one is open,
    else the books settle it), cheque, transfer or credit. The reference and
    the due date are optional — a cheque is often written later."""
    v = v or {}
    m = str(v.get("method") or "").strip()
    if m not in PAY_METHODS:
        frappe.throw("Choose how the stall is paid.")
    ref = re.sub(r"\s+", " ", str(v.get("ref") or "")).strip()[:60] if m in ("cheque", "transfer") else ""
    due = str(v.get("due") or "").strip()[:10] if m in ("cheque", "credit") else ""
    if due:
        try:
            due = str(getdate(due))
        except Exception:
            frappe.throw("The due date is not a date.")
    return {"method": m, "ref": ref, "due": due}


def _is_souk_po(h):
    """Before 2026-11-19 every souk PO carried its trip; now the buyer."""
    return bool(h.get("custom_souk_trip") or h.get("custom_souk_buyer"))


def _souk_po_sql(alias="po"):
    cond = f"IFNULL({alias}.custom_souk_trip, '') != ''"
    if _has_col("Purchase Order", "custom_souk_buyer"):
        cond = f"({cond} OR IFNULL({alias}.custom_souk_buyer, '') != '')"
    return cond


def _resolve_stall(stall, new_stall):
    """An existing stall, or a new one: one Supplier per stall, in the souk
    group, plain English capitals so it reads the same on every paper. A new
    stall whose phone is already a stall's is refused unless the buyer said
    it is another one (souk_stalls.create)."""
    if stall:
        if not frappe.db.exists("Supplier", stall):
            frappe.throw("Unknown stall.")
        return stall
    from logistics_portal.api import souk_stalls
    ns = new_stall or {}
    return souk_stalls.create(ns, sure=bool(ns.get("sure")))


def _validate_variants(base, colors, sizes, lines, color_map):
    """lines: [{color, size, qty, cost, price}] — one per colour × size the
    buyer actually bought. Returns the normalised variant list."""
    if not lines:
        frappe.throw("Enter at least one quantity.")
    seen = set()
    out = []
    for ln in lines:
        color = (ln.get("color") or "").upper()
        size = re.sub(r"\s+", " ", (ln.get("size") or "")).strip()[:40]
        # The size the customer reads ("24 cm") and the short code in the
        # SKU ("S"); without a code the label's own letters are the code.
        scode = _size_code(ln.get("sizeCode") or size)
        if colors and color not in color_map:
            frappe.throw(f"Unknown colour {color}.")
        if not colors:
            color = ""
        if not sizes:
            size = ""
        qty = cint(ln.get("qty"))
        cost = flt(ln.get("cost"))
        price = flt(ln.get("price"))
        if qty <= 0:
            continue
        if cost <= 0 or price <= 0:
            frappe.throw("Every line needs a cost and a selling price.")
        if price <= cost:
            frappe.throw("The selling price must be above the cost.")
        sku = "-".join(x for x in (base, color, scode if size else "") if x)
        if len(sku) > SKU_MAX:
            frappe.throw(f"{sku} is longer than {SKU_MAX} characters — the shelf label can't scan it. "
                         "Use a shorter size code (S, M, L, XL, 2XL, 28…).")
        if sku in seen:
            frappe.throw(f"{sku} appears twice.")
        seen.add(sku)
        out.append({"sku": sku, "color": color, "colorFr": color_map.get(color, {}).get("fr", ""),
                    "size": scode if size else "", "sizeLabel": size, "qty": qty,
                    "cost": cost, "price": price, "itemCode": ""})
    if not out:
        frappe.throw("Enter at least one quantity.")
    return out


@frappe.whitelist(methods=["POST"])
def create_buy(payload):
    """A new product bought on the trip. Reserves the SKU, creates the Shopify
    Draft, and hands over to finish_buy (items → PO → paid invoice), which the
    phone calls again until the product reaches 'bought'."""
    _gate_buy()
    p = json.loads(payload) if isinstance(payload, str) else (payload or {})
    s = settings()
    ckey = _client_key(p)
    if ckey and _has_col(DT_PRODUCT, "client_key"):
        # The phone retried a purchase whose answer it never got (Derb Omar
        # drops the line): finish the one already made, never a second.
        done = frappe.db.get_value(DT_PRODUCT, {"client_key": ckey}, "name")
        if done:
            return finish_buy(done)
    pay = _clean_pay(p.get("payment") or {"method": "cash"})
    # Cash counts against the buyer's custody when one is open; without one,
    # or paid another way, the purchase stands alone and the books settle it.
    trip = _my_open_trip() if pay["method"] == "cash" else None
    title = re.sub(r"\s+", " ", (p.get("title") or "")).strip()
    if len(title) < 3:
        frappe.throw("Write the product's name.")
    cat = next((c for c in s["categories"] if c["key"] == p.get("category")), None)
    if not cat:
        frappe.throw("Choose a category.")
    color_map = {c["code"]: c for c in s["colors"]}
    colors = [c for c in (p.get("colors") or []) if c]
    sizes = [z for z in (p.get("sizes") or []) if (z or "").strip()]
    barcode = _barcode_norm(p.get("barcode"))
    if barcode and not p.get("barcodeSure"):
        hit = (_barcode_hits(barcode) or [None])[0]
        if hit:
            frappe.throw(f"This barcode is already {hit['sku']} · {hit['title']}. Buy it again instead "
                         "of making a new product, or confirm that the product is different.")
    stall = _resolve_stall(p.get("stall"), p.get("newStall"))

    # Reserve the SKU number: the unique name is the lock.
    prefix = s["skuPrefix"]
    doc = None
    for _ in range(5):
        base = f"{prefix}{_next_sku_number(prefix)}"
        variants = _validate_variants(base, colors, sizes, p.get("lines") or [], color_map)
        if barcode:
            # The box's barcode, on every variant: the next buy finds the
            # product by it; the catalogue learns it once the item exists.
            for v in variants:
                v["boxBarcode"] = barcode
        total = round(sum(v["qty"] * v["cost"] for v in variants), 2)
        try:
            doc = frappe.get_doc({
                "doctype": DT_PRODUCT, "sku_base": base, "title": title[:140],
                "stage": "buying", "stage_at": now_datetime(),
                "category": cat["key"], "product_type": cat["productType"], "brand": cat["brand"],
                "supplier": stall, "trip": str(trip.name) if trip else "", "buyer": frappe.session.user,
                "units": sum(v["qty"] for v in variants), "total_cost": total,
                "variants_json": json.dumps(variants, ensure_ascii=False),
                **({"client_key": ckey} if ckey and _has_col(DT_PRODUCT, "client_key") else {}),
                **({"pay_json": json.dumps(pay)} if _has_col(DT_PRODUCT, "pay_json") else {}),
                **({"stage_log": json.dumps([{"s": "buying", "at": str(now_datetime())[:19],
                                               "by": frappe.session.user}])}
                   if _has_col(DT_PRODUCT, "stage_log") else {}),
            }).insert(ignore_permissions=True)
            frappe.db.commit()
            break
        except frappe.DuplicateEntryError:
            frappe.db.rollback()
            if ckey and _has_col(DT_PRODUCT, "client_key"):
                # Two copies of the same request raced: the other one won.
                done = frappe.db.get_value(DT_PRODUCT, {"client_key": ckey}, "name")
                if done:
                    return finish_buy(done)
            continue
    if not doc:
        frappe.throw("Could not reserve a SKU, retry.")
    doc.add_comment("Comment", f"Souk: bought from {stall} · {doc.units} pcs · {doc.total_cost:,.2f} MAD "
                               f"· {_pay_text(pay)}" + (f" · trip {trip.name}" if trip else "")
                               + f" · by {_user_name(frappe.session.user)}.")
    frappe.db.commit()

    try:
        _create_shopify_draft(doc)
    except Exception as e:
        frappe.db.rollback()
        doc.reload()
        doc.db_set("error", f"Shopify: {str(e)[:400]}")
        frappe.db.commit()
        frappe.log_error(frappe.get_traceback()[:3000], f"souk.create_buy {doc.name}")
        return {"name": doc.name, "pending": True, "error": doc.error}
    return finish_buy(doc.name)


# productSet, not productCreate: it makes the product WITH its options and
# variants in one operation, so the products/create webhook that builds the
# Next items sees the finished product. (productCreate + a second variants
# call would let the webhook sync a lone default variant first.) Prod pins
# ee's API_VERSION 2024-01, which Shopify no longer serves — it answers with
# its oldest supported version, where ProductInput.variants is gone; the
# productSet shape below is the current one.
_PRODUCT_SET = """
mutation souk($input: ProductSetInput!) {
  productSet(input: $input, synchronous: true) {
    product { id variants(first: 100) { nodes { id sku } } }
    userErrors { field message code }
  }
}"""


def _shopify_location():
    loc = frappe.db.sql("""SELECT shopify_location_id, COUNT(*) n FROM `tabShopify Warehouse Mapping`
                           WHERE IFNULL(shopify_location_id, '') != ''
                           GROUP BY shopify_location_id ORDER BY n DESC LIMIT 1""")
    return loc[0][0] if loc else None


def _create_shopify_draft(doc):
    """Idempotent: a product that already has its Shopify id is left alone."""
    if doc.shopify_product_id:
        return
    from logistics_portal.api.catalog_hub.sync import shopify_graphql
    variants = json.loads(doc.variants_json or "[]")
    has_color = any(v["color"] for v in variants)
    has_size = any(v["size"] for v in variants)
    loc = _shopify_location()

    def _vals(key):
        out = []
        for v in variants:
            x = v[key]
            if x and x not in out:
                out.append(x)
        return out

    options = []
    if has_color:
        options.append({"name": "Color", "values": [{"name": x} for x in _vals("colorFr")]})
    if has_size:
        options.append({"name": "Size", "values": [{"name": x} for x in _vals("sizeLabel")]})
    if not options:
        # Shopify's own shape for a product without options.
        options = [{"name": "Title", "values": [{"name": "Default Title"}]}]
    vinputs = []
    for v in variants:
        ov = []
        if has_color:
            ov.append({"optionName": "Color", "name": v["colorFr"]})
        if has_size:
            ov.append({"optionName": "Size", "name": v["sizeLabel"]})
        if not ov:
            ov = [{"optionName": "Title", "name": "Default Title"}]
        vi = {"optionValues": ov, "price": str(v["price"]), "inventoryPolicy": "DENY",
              "inventoryItem": {"sku": v["sku"], "tracked": True, "cost": str(v["cost"])}}
        if loc:
            # Stocked at our location at zero: ee's inventory push fills it
            # the moment receiving moves the bin.
            vi["inventoryQuantities"] = [{"locationId": f"gid://shopify/Location/{loc}",
                                          "name": "available", "quantity": 0}]
        vinputs.append(vi)
    inp = {"title": doc.title, "vendor": doc.brand, "productType": doc.product_type,
           "status": "DRAFT", "tags": ["souk", doc.sku_base] + ([f"souk-trip-{doc.trip}"] if doc.trip else []),
           "productOptions": options, "variants": vinputs}
    data = shopify_graphql(_PRODUCT_SET, {"input": inp})
    res = (data.get("data") or {}).get("productSet") or {}
    errs = res.get("userErrors") or []
    if errs:
        raise Exception("; ".join(f"{'.'.join(e.get('field') or [])}: {e.get('message')}" for e in errs)[:400])
    prod = res.get("product") or {}
    pid = (prod.get("id") or "").rsplit("/", 1)[-1]
    if not pid:
        raise Exception("Shopify returned no product id")
    by_sku = {n.get("sku"): (n.get("id") or "").rsplit("/", 1)[-1]
              for n in ((prod.get("variants") or {}).get("nodes") or [])}
    for v in variants:
        v["variantId"] = by_sku.get(v["sku"], "")
    doc.db_set({"shopify_product_id": pid, "variants_json": json.dumps(variants, ensure_ascii=False),
                "error": ""})
    doc.add_comment("Comment", f"Souk: Shopify Draft {pid} created · vendor {doc.brand} · {len(variants)} variants.")
    frappe.db.commit()


def _map_items(doc, variants):
    """variant id → Next item, through ee's own Ecommerce Item rows."""
    rows = frappe.db.sql(
        """SELECT erpnext_item_code, variant_id FROM `tabEcommerce Item`
           WHERE integration = 'shopify' AND integration_item_code = %s""",
        (doc.shopify_product_id,), as_dict=True)
    by_variant = {str(r.variant_id or ""): r.erpnext_item_code for r in rows}
    for v in variants:
        code = by_variant.get(str(v.get("variantId") or ""))
        # A single-variant product's item code is its variant id too.
        if not code and v.get("variantId") and frappe.db.exists("Item", v["variantId"]):
            code = v["variantId"]
        v["itemCode"] = code or ""
    return all(v["itemCode"] for v in variants)


@frappe.whitelist(methods=["POST"])
def finish_buy(name):
    """Drive a bought product to 'bought'. Safe to call any number of times:
    each step checks what already exists. Returns pending while the webhook
    has not made the items yet."""
    _gate_view()
    doc = frappe.get_doc(DT_PRODUCT, name)
    basket = (_loads(doc.get("pay_json")) or {}).get("basket") if _has_col(DT_PRODUCT, "pay_json") else None
    if basket:
        return finish_basket(basket)
    if doc.stage != "buying":
        return {"name": doc.name, "pending": False, "stage": doc.stage, "po": doc.purchase_order}
    if not doc.shopify_product_id:
        try:
            _ensure_draft(doc.name)
        except Exception as e:
            frappe.db.rollback()
            doc.reload()
            doc.db_set("error", f"Shopify: {str(e)[:400]}")
            frappe.db.commit()
            return {"name": doc.name, "pending": True, "error": doc.error}
        doc.reload()

    variants = json.loads(doc.variants_json or "[]")
    if not _map_items(doc, variants):
        # The products/create webhook normally lands in seconds. Past 20 s we
        # run the same sync ourselves (ee skips a product already synced).
        if time_diff_in_hours(now_datetime(), doc.stage_at) * 3600 > 20:
            try:
                from ecommerce_integrations.shopify.product import ShopifyProduct
                ShopifyProduct(doc.shopify_product_id).sync_product()
                frappe.db.commit()
            except Exception:
                frappe.db.rollback()
                frappe.log_error(frappe.get_traceback()[:3000], f"souk.finish_buy sync {doc.name}")
        if not _map_items(doc, variants):
            return {"name": doc.name, "pending": True, "error": "",
                    "waiting": "items"}

    # The SKU must be on the item: the label, the scanner and SKU search key on it.
    for v in variants:
        if frappe.db.get_value("Item", v["itemCode"], "custom_sku") != v["sku"]:
            frappe.db.set_value("Item", v["itemCode"], "custom_sku", v["sku"], update_modified=False)
    doc.db_set("variants_json", json.dumps(variants, ensure_ascii=False))
    # One variant: the box's barcode is that item's. Several: it is one of
    # them and we do not know which — the souk card keeps it for matching.
    if len(variants) == 1 and variants[0].get("boxBarcode"):
        try:
            _attach_barcode(variants[0]["itemCode"], variants[0]["boxBarcode"])
        except Exception:
            frappe.log_error(frappe.get_traceback()[:2000], f"souk barcode {doc.name}")

    try:
        # Two calls at once (the phone's outbox and a manual retry) must not
        # make two POs: hold the row, then look again under the lock.
        doc = _lock_product(doc.name)
        if doc.stage != "buying":
            frappe.db.commit()
            return {"name": doc.name, "pending": False, "stage": doc.stage, "po": doc.purchase_order}
        if not doc.purchase_order:
            pay = _loads(doc.get("pay_json")) if _has_col(DT_PRODUCT, "pay_json") else None
            po = _make_po(doc.supplier, doc.trip, doc.name,
                          [(v["itemCode"], v["qty"], v["cost"]) for v in variants],
                          receipt_image=doc.receipt_image,
                          pay=pay or {"method": "cash"}, buyer=doc.buyer)
            doc.db_set("purchase_order", po.name)
            frappe.db.commit()
        # No invoice here: PO → PR (receiving) → PI, and the PI and the
        # payment are the accountant's (Ahmed, 2026-11-19).
    except Exception as e:
        frappe.db.rollback()
        doc.reload()
        doc.db_set("error", f"Next: {str(e)[:400]}")
        frappe.db.commit()
        frappe.log_error(frappe.get_traceback()[:3000], f"souk.finish_buy {doc.name}")
        return {"name": doc.name, "pending": True, "error": doc.error}

    _set_stage(doc, "bought", bought_at=now_datetime(), error="")
    doc.add_comment("Comment", f"Souk: {doc.purchase_order} · waiting for receiving.")
    frappe.db.commit()
    return {"name": doc.name, "pending": False, "stage": "bought", "po": doc.purchase_order,
            "pi": "", "variants": variants, "left": _trip_left(doc.trip)}


def _make_po(supplier, trip, product, lines, receipt_image="", client_key="", pay=None, buyer=None):
    today = nowdate()
    pay = pay or {}
    po = frappe.new_doc("Purchase Order")
    po.update({
        "company": COMPANY, "supplier": supplier, "transaction_date": today, "schedule_date": today,
        "set_warehouse": RECEIVING_WH, "currency": "MAD", "taxes_and_charges": "",
        "custom_souk_trip": str(trip or ""), "custom_souk_product": product or "",
    })
    if _has_col("Purchase Order", "custom_souk_buyer"):
        po.custom_souk_buyer = buyer or frappe.session.user
        po.custom_souk_pay = pay.get("method") or ""
        po.custom_souk_pay_ref = pay.get("ref") or ""
        po.custom_souk_pay_due = pay.get("due") or None
    if client_key:
        po.custom_souk_client_key = client_key
    if receipt_image:
        po.custom_souk_receipt = "receipt"
        po.custom_souk_receipt_image = receipt_image
    for code, qty, rate in lines:
        # Units set here, not left to set_missing_values: the ecommerce
        # PurchaseOrder override validates the stock-UOM qty before ERPNext
        # fills them, and throws "Conversion Factor is mandatory" — no souk
        # PO had ever been made on prod (found 2026-11-19).
        uom = frappe.db.get_value("Item", code, "stock_uom") or "Nos"
        po.append("items", {"item_code": code, "qty": qty, "rate": rate,
                            "uom": uom, "stock_uom": uom, "conversion_factor": 1,
                            "schedule_date": today, "warehouse": RECEIVING_WH})
    po.set("taxes", [])
    # The ecommerce_integrations PurchaseOrder override replaces validate and
    # never fills the defaults (exchange rate, item name, base amounts) that
    # the Desk form would. Fill them here, as the form does; the rate stays
    # what the buyer paid.
    po.run_method("set_missing_values")
    po.run_method("calculate_taxes_and_totals")
    po.insert(ignore_permissions=True)
    po.submit()
    return po


def _trip_left(trip):
    """Custody left on the trip a cash purchase counted against, else None."""
    return _trip_card(frappe.get_doc(DT_TRIP, cint(trip)))["expected"] if trip else None


def _pay_text(pay):
    m = (pay or {}).get("method") or "cash"
    out = {"cash": "cash", "cheque": "cheque", "transfer": "transfer", "credit": "on credit"}[m]
    if pay.get("ref"):
        out += f" {pay['ref']}"
    if pay.get("due"):
        out += f" due {pay['due']}"
    return out


# --- buy again ----------------------------------------------------------------

@frappe.whitelist()
def rebuy_lookup(key, kind="souk"):
    """What to buy again: the product's variants with the last stall and cost."""
    _gate_view()
    rows = []
    title = ""
    if kind == "souk":
        doc = frappe.get_doc(DT_PRODUCT, key)
        title = doc.title
        for v in json.loads(doc.variants_json or "[]"):
            if v.get("itemCode"):
                rows.append({"itemCode": v["itemCode"], "sku": v["sku"],
                             "label": " · ".join(x for x in (v.get("colorFr"), v.get("sizeLabel")) if x),
                             "cost": v.get("cost")})
    else:
        it = frappe.db.get_value("Item", key, ["name", "item_name", "custom_sku", "variant_of"], as_dict=True)
        if not it:
            frappe.throw("Unknown item.")
        title = it.item_name
        codes = [it.name]
        if it.variant_of:
            codes = frappe.get_all("Item", filters={"variant_of": it.variant_of, "disabled": 0}, pluck="name")
        for c in codes:
            i = frappe.db.get_value("Item", c, ["item_name", "custom_sku"], as_dict=True)
            rows.append({"itemCode": c, "sku": i.custom_sku or c, "label": i.item_name, "cost": 0})
    stall = None
    for r in rows:
        last = _last_stall(r["itemCode"])
        if last:
            r["cost"] = r["cost"] or flt(last.rate)
            stall = stall or last.supplier
    return {"title": title, "rows": rows, "lastStall": stall or ""}


@frappe.whitelist(methods=["POST"])
def create_rebuy(payload):
    """Buy again a product we already have: a PO on the trip, nothing new on
    Shopify. Linked to its souk card when there is one."""
    _gate_buy()
    p = json.loads(payload) if isinstance(payload, str) else (payload or {})
    ckey = _client_key(p)
    keyed = ckey and _has_col("Purchase Order", "custom_souk_client_key")
    if keyed:
        # Two copies of the same request (outbox + a second tap) wait for
        # each other here; the second finds the first one's PO.
        with _named_lock(ckey):
            return _rebuy(p, ckey, keyed)
    return _rebuy(p, ckey, keyed)


def _rebuy(p, ckey, keyed):
    if keyed:
        done = frappe.db.get_value("Purchase Order", {"custom_souk_client_key": ckey, "docstatus": 1},
                                   ["name", "custom_souk_trip"], as_dict=True)
        if done:
            return {"po": done.name, "pi": "", "repeat": True, "left": _trip_left(done.custom_souk_trip)}
    pay = _clean_pay(p.get("payment") or {"method": "cash"})
    trip = _my_open_trip() if pay["method"] == "cash" else None
    stall = _resolve_stall(p.get("stall"), p.get("newStall"))
    lines = []
    for ln in p.get("lines") or []:
        qty, cost = cint(ln.get("qty")), flt(ln.get("cost"))
        if qty <= 0:
            continue
        if cost <= 0:
            frappe.throw("Every line needs a cost.")
        if not frappe.db.exists("Item", ln.get("itemCode")):
            frappe.throw("Unknown item.")
        lines.append((ln["itemCode"], qty, cost))
    if not lines:
        frappe.throw("Enter at least one quantity.")
    total = sum(q * c for _, q, c in lines)
    # Found by name, then its box scanned: the catalogue learns the barcode
    # (only when one item is bought — with several we would not know whose).
    if len(lines) == 1 and _barcode_norm(p.get("barcode")):
        try:
            _attach_barcode(lines[0][0], p.get("barcode"))
        except Exception:
            frappe.log_error(frappe.get_traceback()[:2000], "souk rebuy barcode")
    product = p.get("product") if p.get("kind") == "souk" else ""
    po = _make_po(stall, trip.name if trip else "", product, lines, client_key=ckey if keyed else "",
                  pay=pay, buyer=frappe.session.user)
    if product and frappe.db.exists(DT_PRODUCT, product):
        frappe.get_doc(DT_PRODUCT, product).add_comment(
            "Comment", f"Souk: bought again from {stall} · {sum(q for _, q, _ in lines)} pcs · "
                       f"{total:,.2f} MAD · {_pay_text(pay)} · {po.name}" + (f" · trip {trip.name}" if trip else "") + ".")
    frappe.db.commit()
    return {"po": po.name, "pi": "", "left": _trip_left(trip.name if trip else "")}


# --- the basket: one stall visit, one payment, one PO (Ahmed 2026-11-20) -----
# The buyer adds every product bought at one stall to one basket; each new
# product still gets its own card, SKU and Shopify Draft, and moves on alone
# (receiving, photos, studio, content, review). The basket lives on its cards:
# pay_json carries {basket, idx, again} — no new field, no migrate. The PO is
# made once every card's items exist and carries the basket key as its
# custom_souk_client_key, so a retry finds it instead of making a second.

BASKET_MAX = 12


@contextmanager
def _named_lock(name, timeout=20):
    """A MariaDB named lock for one request id: two copies of the same
    request (the outbox retry, a second tab) run one after the other."""
    name = ("souk:" + name)[:64]
    got = frappe.db.sql("SELECT GET_LOCK(%s, %s)", (name, timeout))[0][0]
    if not got:
        frappe.throw("This purchase is being saved by another request — try again in a moment.")
    try:
        yield
    finally:
        frappe.db.sql("SELECT RELEASE_LOCK(%s)", (name,))


def sell_price(cost, s=None):
    """The selling price is a formula, not a choice (Ahmed 2026-11-20): cost
    HT + margin, + TVA on the total, rounded up to the next dirham."""
    s = s or settings()
    m = flt(s.get("priceMargin") if s.get("priceMargin") is not None else 50)
    vat = flt(s.get("priceVat") if s.get("priceVat") is not None else 20)
    raw = flt(cost) * (1 + m / 100.0) * (1 + vat / 100.0)
    return float(math.ceil(round(raw, 6))) if raw > 0 else 0.0


def _basket_cards(key, with_dropped=False):
    if not key or not _has_col(DT_PRODUCT, "pay_json"):
        return []
    rows = frappe.db.sql(
        f"""SELECT name FROM `tab{DT_PRODUCT}` WHERE pay_json LIKE %s ORDER BY creation""",
        (f'%"basket": "{key}"%',))
    out = []
    for (n,) in rows:
        d = frappe.get_doc(DT_PRODUCT, n)
        if d.stage == "dropped" and not with_dropped:
            continue
        out.append(d)
    out.sort(key=lambda d: cint((_loads(d.pay_json) or {}).get("idx")))
    return out


def _basket_po(key):
    if not key or not _has_col("Purchase Order", "custom_souk_client_key"):
        return None
    return frappe.db.get_value("Purchase Order", {"custom_souk_client_key": key, "docstatus": 1}, "name")


def _basket_trip(pay, sent):
    """Cash counts against the custody that was open when the buyer pressed
    buy (the phone sends it), not whichever is open when the request lands —
    an offline purchase replayed tomorrow belongs to yesterday's trip."""
    if pay["method"] != "cash":
        return None
    if sent:
        t = frappe.db.get_value(DT_TRIP, cint(sent), ["name", "buyer", "status"], as_dict=True)
        if not t or t.buyer != frappe.session.user:
            frappe.throw("That custody is not yours.")
        if t.status != "Open":
            frappe.throw(f"Custody #{t.name} was closed before this purchase reached the server. "
                         "Ask the accountant to reopen it, or record the purchase with another payment method.")
        return frappe.get_doc(DT_TRIP, t.name)
    return _my_open_trip()


def _clean_again(lines):
    out = []
    for ln in lines or []:
        code, qty, cost = ln.get("itemCode"), cint(ln.get("qty")), flt(ln.get("cost"))
        if qty <= 0:
            continue
        if cost <= 0:
            frappe.throw("Every line needs a cost.")
        if not code or not frappe.db.exists("Item", code):
            frappe.throw("Unknown item.")
        prod = ln.get("product") or ""
        if prod and not frappe.db.exists(DT_PRODUCT, prod):
            prod = ""
        out.append({"itemCode": code, "qty": qty, "cost": cost, "product": prod,
                    "barcode": _barcode_norm(ln.get("barcode"))})
    return out


def _basket_product(p, s, color_map):
    """One new product of the basket, checked — nothing written yet."""
    title = re.sub(r"\s+", " ", (p.get("title") or "")).strip()
    if len(title) < 3:
        frappe.throw("Write each product's name.")
    cat = next((c for c in s["categories"] if c["key"] == p.get("category")), None)
    if not cat:
        frappe.throw(f"Choose a category for {title}.")
    colors = [c for c in (p.get("colors") or []) if c]
    sizes = [z for z in (p.get("sizes") or []) if (z or "").strip()]
    lines = []
    for ln in p.get("lines") or []:
        ln = dict(ln)
        ln["price"] = sell_price(ln.get("cost"), s)
        lines.append(ln)
    # A dry run of the variants against a placeholder base: the real SKU is
    # reserved later, under the unique-name lock.
    _validate_variants("X0", colors, sizes, lines, color_map)
    sure = bool(p.get("barcodeSure"))
    mine = [b for b in (_barcode_norm(ln.get("barcode")) for ln in lines if cint(ln.get("qty")) > 0) if b]
    if len(mine) != len(set(mine)):
        frappe.throw(f"{title}: two variants have the same barcode.")
    for ln in lines:
        bc = _barcode_norm(ln.get("barcode") or p.get("barcode"))
        if bc and not (sure or ln.get("barcodeSure")):
            hit = (_barcode_hits(bc) or [None])[0]
            if hit:
                frappe.throw(f"{title}: the barcode {bc} is already {hit['sku']} · {hit['title']}. "
                             "Buy it again instead, or confirm that the product is different.")
    return {"title": title, "cat": cat, "colors": colors, "sizes": sizes, "lines": lines,
            "barcode": _barcode_norm(p.get("barcode")), "refImage": str(p.get("refImage") or "")[:300],
            # Bought from the shopping list (souk_picks): its photo is the
            # reference until the buyer's own arrives, and the pick is done.
            "pick": str(p.get("pick") or "")[:20]}


def _line_key(ln, prod):
    color = (ln.get("color") or "").upper() if prod["colors"] else ""
    size = re.sub(r"\s+", " ", (ln.get("size") or "")).strip()
    return color + "|" + (_size_code(ln.get("sizeCode") or size) if prod["sizes"] and size else "")


def _new_card(prod, i, key, pay, again, stall, trip, s, color_map):
    prefix = s["skuPrefix"]
    for _ in range(5):
        base = f"{prefix}{_next_sku_number(prefix)}"
        variants = _validate_variants(base, prod["colors"], prod["sizes"], prod["lines"], color_map)
        own = {_line_key(ln, prod): _barcode_norm(ln.get("barcode")) for ln in prod["lines"]}
        for v in variants:
            bc = own.get(v["color"] + "|" + v["size"])
            if bc:
                v["boxBarcode"], v["ownBarcode"] = bc, True
            elif prod["barcode"]:
                # One barcode for the whole product: which variant it is, we
                # do not know — kept on the card for matching, not attached.
                v["boxBarcode"] = prod["barcode"]
        total = round(sum(v["qty"] * v["cost"] for v in variants), 2)
        ref = prod["refImage"] if prod["refImage"].startswith("/files/") else ""
        if not ref and prod.get("pick"):
            from logistics_portal.api import souk_picks
            ref = souk_picks.pick_photo(prod["pick"])
        try:
            doc = frappe.get_doc({
                "doctype": DT_PRODUCT, "sku_base": base, "title": prod["title"][:140],
                "stage": "buying", "stage_at": now_datetime(),
                "category": prod["cat"]["key"], "product_type": prod["cat"]["productType"],
                "brand": prod["cat"]["brand"], "supplier": stall, "trip": str(trip.name) if trip else "",
                "buyer": frappe.session.user, "units": sum(v["qty"] for v in variants), "total_cost": total,
                "variants_json": json.dumps(variants, ensure_ascii=False),
                **({"ref_image": ref} if ref else {}),
                **({"client_key": f"{key}-{i}"} if _has_col(DT_PRODUCT, "client_key") else {}),
                "pay_json": json.dumps({**pay, "basket": key, "idx": i, "again": again,
                                        **({"pick": prod["pick"]} if prod.get("pick") else {})}),
                **({"stage_log": json.dumps([{"s": "buying", "at": str(now_datetime())[:19],
                                               "by": frappe.session.user}])}
                   if _has_col(DT_PRODUCT, "stage_log") else {}),
            }).insert(ignore_permissions=True)
            if prod.get("pick"):
                from logistics_portal.api import souk_picks
                souk_picks.link_card(prod["pick"], doc.name)
            return doc
        except frappe.DuplicateEntryError:
            frappe.db.rollback()
            continue
    frappe.throw("Could not reserve a SKU, retry.")


@frappe.whitelist(methods=["POST"])
def create_basket(payload):
    """Everything bought at one stall: N new products + buy-again lines, one
    payment, one PO. Safe to send again with the same clientKey."""
    _gate_buy()
    p = json.loads(payload) if isinstance(payload, str) else (payload or {})
    key = _client_key(p)
    if not key:
        frappe.throw("Update the app: this purchase has no request id.")
    if _basket_cards(key, with_dropped=True) or _basket_po(key):
        return finish_basket(key)
    if not _has_col(DT_PRODUCT, "pay_json"):
        frappe.throw("The souk is being updated — try again in a minute.")
    s = settings()
    color_map = {c["code"]: c for c in s["colors"]}
    pay = _clean_pay(p.get("payment"))
    trip = _basket_trip(pay, p.get("trip"))
    prods = [_basket_product(x, s, color_map) for x in (p.get("products") or [])]
    codes = [b for pr in prods for b in ({_barcode_norm(ln.get("barcode")) for ln in pr["lines"]} | {pr["barcode"]}) if b]
    if len(codes) != len(set(codes)):
        frappe.throw("Two products in the basket have the same barcode.")
    again = _clean_again(p.get("again"))
    if not prods and not again:
        frappe.throw("The basket is empty.")
    if len(prods) > BASKET_MAX:
        frappe.throw(f"At most {BASKET_MAX} new products in one basket.")
    receipt = str(p.get("receiptImage") or "")
    receipt = receipt if receipt.startswith("/files/") else ""

    with _named_lock(key):
        # A second copy of this request that was waiting on the lock finds
        # the first one's work and only finishes it.
        if not (_basket_cards(key, with_dropped=True) or _basket_po(key)):
            stall = _resolve_stall(p.get("stall"), p.get("newStall"))
            # A lead from the shopping list (souk_picks) becomes a stall here.
            from logistics_portal.api import souk_picks
            souk_picks.promote_lead(stall)
            if stall and frappe.db.get_value("Supplier", stall, "supplier_group") != SUPPLIER_GROUP:
                frappe.throw("Choose a souk stall.")
            for code in {a["itemCode"] for a in again}:
                if sum(1 for a in again if a["itemCode"] == code) > 1:
                    frappe.throw("The same item appears twice in the basket.")
            if not prods:
                # Buy-again only: nothing waits for Shopify, the PO is made now.
                po = _make_po(stall, trip.name if trip else "", _again_product(again),
                              [(a["itemCode"], a["qty"], a["cost"]) for a in again],
                              receipt_image=receipt, client_key=key, pay=pay, buyer=frappe.session.user)
                _again_after_po(po.name, stall, again, pay, trip)
                frappe.db.commit()
            else:
                cards = []
                for i, prod in enumerate(prods):
                    d = _new_card(prod, i, key, pay, again, stall, trip, s, color_map)
                    if receipt:
                        d.db_set("receipt_image", receipt, update_modified=False)
                    cards.append(d)
                total = sum(flt(d.total_cost) for d in cards) + sum(a["qty"] * a["cost"] for a in again)
                for d in cards:
                    d.add_comment("Comment", f"Souk: bought from {stall} · {d.units} pcs · {d.total_cost:,.2f} MAD "
                                             f"· basket of {len(cards) + len(again)} line(s), {total:,.2f} MAD "
                                             f"· {_pay_text(pay)}" + (f" · trip {trip.name}" if trip else "")
                                             + f" · by {_user_name(frappe.session.user)}.")
                frappe.db.commit()
    return finish_basket(key)


def _again_product(again):
    prods = {a["product"] for a in again if a.get("product")}
    return prods.pop() if len(prods) == 1 else ""


def _again_after_po(po, stall, again, pay, trip):
    # Found by name, then its box scanned: the catalogue learns the barcode.
    for a in again:
        if a.get("barcode"):
            try:
                _attach_barcode(a["itemCode"], a["barcode"])
            except Exception:
                frappe.log_error(frappe.get_traceback()[:2000], "souk basket barcode")
    for prod in {a["product"] for a in again if a.get("product")}:
        n = sum(a["qty"] for a in again if a.get("product") == prod)
        frappe.get_doc(DT_PRODUCT, prod).add_comment(
            "Comment", f"Souk: bought again from {stall} · {n} pcs · {_pay_text(pay)} · {po}"
                       + (f" · trip {trip.name}" if trip else "") + ".")


def _card_ready(doc):
    """Shopify Draft made and every variant's item made: True, else the
    reason it waits ('' = still waiting, text = an error)."""
    if not doc.shopify_product_id:
        try:
            _ensure_draft(doc.name)
        except Exception as e:
            frappe.db.rollback()
            frappe.db.set_value(DT_PRODUCT, doc.name, "error", f"Shopify: {str(e)[:400]}", update_modified=False)
            frappe.db.commit()
            frappe.log_error(frappe.get_traceback()[:3000], f"souk.basket draft {doc.name}")
            return False
        doc.reload()
    variants = json.loads(doc.variants_json or "[]")
    if not _map_items(doc, variants):
        if time_diff_in_hours(now_datetime(), doc.stage_at) * 3600 > 20:
            try:
                from ecommerce_integrations.shopify.product import ShopifyProduct
                ShopifyProduct(doc.shopify_product_id).sync_product()
                frappe.db.commit()
            except Exception:
                frappe.db.rollback()
                frappe.log_error(frappe.get_traceback()[:3000], f"souk.basket sync {doc.name}")
        if not _map_items(doc, variants):
            return False
    for v in variants:
        if frappe.db.get_value("Item", v["itemCode"], "custom_sku") != v["sku"]:
            frappe.db.set_value("Item", v["itemCode"], "custom_sku", v["sku"], update_modified=False)
        # Each variant's own box barcode is that item's.
        if v.get("boxBarcode") and (len(variants) == 1 or v.get("ownBarcode")):
            try:
                _attach_barcode(v["itemCode"], v["boxBarcode"])
            except Exception:
                frappe.log_error(frappe.get_traceback()[:2000], f"souk barcode {doc.name}")
    doc.db_set("variants_json", json.dumps(variants, ensure_ascii=False))
    frappe.db.commit()
    return True


@frappe.whitelist(methods=["POST"])
def finish_basket(key):
    """Drive a basket to its PO. Safe to call any number of times."""
    _gate_buy()
    key = re.sub(r"[^A-Za-z0-9-]", "", str(key or ""))[:64]
    cards = _basket_cards(key)
    po = _basket_po(key)
    buying = [d for d in cards if d.stage == "buying"]
    waiting = [d.name for d in buying if not _card_ready(d)]
    if waiting:
        return _basket_answer(key, po, pending=True)
    if not po and (cards or _basket_cards(key, with_dropped=True)):
        with _named_lock(key):
            po = _basket_po(key)
            if not po:
                lead = cards[0] if cards else _basket_cards(key, with_dropped=True)[0]
                pay = _loads(lead.pay_json) or {}
                again = pay.get("again") or []
                lines = [(v["itemCode"], v["qty"], v["cost"])
                         for d in cards for v in json.loads(d.variants_json or "[]")]
                lines += [(a["itemCode"], a["qty"], a["cost"]) for a in again]
                if not lines:
                    return _basket_answer(key, None, pending=False)
                try:
                    doc = _make_po(lead.supplier, lead.trip, cards[0].name if len(cards) == 1 else
                                   (cards[0].name if cards else _again_product(again)),
                                   lines, client_key=key,
                                   receipt_image=next((d.receipt_image for d in _basket_cards(key, with_dropped=True)
                                                       if d.receipt_image), ""),
                                   pay={k: pay.get(k) for k in ("method", "ref", "due")}, buyer=lead.buyer)
                except Exception as e:
                    frappe.db.rollback()
                    for d in cards:
                        frappe.db.set_value(DT_PRODUCT, d.name, "error", f"Next: {str(e)[:400]}", update_modified=False)
                    frappe.db.commit()
                    frappe.log_error(frappe.get_traceback()[:3000], f"souk.finish_basket {key}")
                    return _basket_answer(key, None, pending=True)
                po = doc.name
                trip = frappe.get_doc(DT_TRIP, cint(lead.trip)) if lead.trip else None
                _again_after_po(po, lead.supplier, again, pay, trip)
                frappe.db.commit()
    if po:
        for d in cards:
            if d.stage == "buying":
                d.reload()
                d.db_set("purchase_order", po)
                _set_stage(d, "bought", bought_at=now_datetime(), error="")
                d.add_comment("Comment", f"Souk: {po} · waiting for receiving.")
        frappe.db.commit()
    return _basket_answer(key, po, pending=not po)


def _basket_answer(key, po, pending):
    cards = _basket_cards(key, with_dropped=True)
    trip = cards[0].trip if cards else (frappe.db.get_value("Purchase Order", po, "custom_souk_trip") if po else "")
    return {"basket": key, "pending": pending, "po": po or "",
            "cards": [{"name": d.name, "title": d.title, "stage": d.stage, "error": d.error or "",
                       "variants": [{"sku": v["sku"], "qty": v["qty"], "cost": v["cost"], "price": v.get("price")}
                                    for v in json.loads(d.variants_json or "[]")]} for d in cards],
            "error": next((d.error for d in cards if d.error and d.stage == "buying"), ""),
            "left": _trip_left(trip) if trip else None}


_FIND_BY_TAG = """
query souk($q: String!) {
  products(first: 2, query: $q) { nodes { id tags variants(first: 100) { nodes { id sku } } } }
}"""


def _ensure_draft(name):
    """The card's Shopify Draft, exactly once: the row is held while Shopify
    answers, and a Draft an earlier call made but never recorded (the answer
    timed out) is found by its SKU tag and adopted, not made again."""
    from logistics_portal.api.catalog_hub.sync import shopify_graphql
    doc = _lock_product(name)
    if doc.shopify_product_id:
        frappe.db.commit()
        return
    try:
        found = (((shopify_graphql(_FIND_BY_TAG, {"q": f"tag:'{doc.sku_base}' AND tag:souk"}).get("data") or {})
                  .get("products") or {}).get("nodes")) or []
    except Exception:
        found = []
    hit = next((n for n in found if doc.sku_base in (n.get("tags") or [])), None)
    if hit:
        variants = json.loads(doc.variants_json or "[]")
        by_sku = {n.get("sku"): (n.get("id") or "").rsplit("/", 1)[-1]
                  for n in ((hit.get("variants") or {}).get("nodes") or [])}
        for v in variants:
            v["variantId"] = by_sku.get(v["sku"], v.get("variantId") or "")
        doc.db_set({"shopify_product_id": hit["id"].rsplit("/", 1)[-1],
                    "variants_json": json.dumps(variants, ensure_ascii=False), "error": ""})
        doc.add_comment("Comment", "Souk: the Shopify Draft made by an earlier try was found and kept.")
        frappe.db.commit()
        return
    _create_shopify_draft(doc)


# --- launch board --------------------------------------------------------------

def _age_days(dt):
    if not dt:
        return 0
    return round(time_diff_in_hours(now_datetime(), dt) / 24, 1)


def _variant_counts(variants):
    colors = {v.get("color") for v in variants if v.get("color")}
    sizes = {v.get("sizeLabel") for v in variants if v.get("sizeLabel")}
    return {"variants": len(variants), "colors": len(colors), "sizes": len(sizes)}


def _sold_since(products):
    """Units customers ordered of each product since it went live: Sales
    Order Item rows of submitted orders (cancelled ones are docstatus 2).
    One row per order line — no Delivery Note join, no basket fan-out."""
    by_code, since = {}, {}
    for p in products:
        for code in p["codes"]:
            by_code[code] = p["name"]
        since[p["name"]] = p["since"]
    if not by_code:
        return {}
    first = min(x for x in since.values() if x) if any(since.values()) else nowdate()
    out = {}
    for code, day, qty in frappe.db.sql(
            """SELECT soi.item_code, so.transaction_date, SUM(soi.qty) FROM `tabSales Order Item` soi
               JOIN `tabSales Order` so ON so.name = soi.parent
               WHERE soi.item_code IN %s AND so.docstatus = 1 AND so.transaction_date >= %s
               GROUP BY soi.item_code, so.transaction_date""", (tuple(by_code), str(first)[:10])):
        name = by_code[code]
        if not since[name] or str(day) >= str(since[name])[:10]:
            out[name] = out.get(name, 0) + cint(qty)
    return out


def _durations(log, upto=None):
    """[(stage, days)] for each stage the card finished; the open one last,
    measured up to now."""
    out = []
    for i, e in enumerate(log):
        try:
            a = get_datetime(e["at"])
            b = get_datetime(log[i + 1]["at"]) if i + 1 < len(log) else (upto or now_datetime())
        except Exception:
            continue
        out.append((e.get("s"), round(time_diff_in_hours(b, a) / 24, 2), i + 1 < len(log)))
    return out


@frappe.whitelist()
def board():
    """The launch board. Every card in the cycle (no cap — a missing card is
    a card nobody chases), Live of the last 7 days, and the cards that left
    the cycle in the last 30 for the 'dropped' filter."""
    _gate_view()
    s = settings()
    stage_days = s.get("stageDays") or {}
    me = frappe.session.user
    fields = ["name", "title", "stage", "stage_at", "supplier", "brand", "trip", "buyer", "category",
              "units", "total_cost", "ref_image", "bought_at", "creation", "error", "variants_json",
              "shopify_product_id", "purchase_order", "published_at", "review_note", "content_by",
              "finals_json"]
    for f in ("stage_log", "claimed_by", "dropped_from"):
        if _has_col(DT_PRODUCT, f):
            fields.append(f)
    active = frappe.get_all(DT_PRODUCT, filters={"stage": ["not in", ["live", "dropped"]]},
                            fields=fields, order_by="stage_at asc", limit_page_length=0)
    week = add_days(nowdate(), -6)
    live = frappe.get_all(DT_PRODUCT, filters={"stage": "live", "stage_at": [">=", week]},
                          fields=fields, order_by="stage_at desc", limit_page_length=0)
    gone = frappe.get_all(DT_PRODUCT, filters={"stage": "dropped", "stage_at": [">=", add_days(nowdate(), -30)]},
                          fields=fields, order_by="stage_at desc", limit_page_length=0)
    # Launched in the last 30 days: the timings and the sell-through.
    month = frappe.get_all(DT_PRODUCT, filters={"stage": "live", "published_at": [">=", add_days(nowdate(), -30)]},
                           fields=["name", "units", "variants_json", "published_at"]
                           + (["stage_log"] if _has_col(DT_PRODUCT, "stage_log") else []),
                           limit_page_length=0)

    names = {}

    def who(u):
        if u and u not in names:
            names[u] = _user_name(u)
        return names.get(u, "") if u else ""

    sold = _sold_since(
        [{"name": r.name, "since": r.published_at,
          "codes": [v.get("itemCode") for v in (_loads(r.variants_json) or []) if v.get("itemCode")]}
         for r in live + [m for m in month if m.name not in {x.name for x in live}]])

    def card(r):
        variants = _loads(r.variants_json) or []
        age = _age_days(r.stage_at)
        limit = cint(stage_days.get(r.stage)) or 0
        claimed = r.get("claimed_by") or ""
        finals = _loads(r.finals_json) or []
        return {
            "name": r.name, "title": r.title, "stage": r.stage, "age": age,
            "late": bool(limit and age > limit) or bool(r.error and r.stage not in ("live", "dropped")),
            "limit": limit, "stall": r.supplier or "", "brand": r.brand or "", "trip": r.trip or "",
            "category": r.category or "", "buyer": r.buyer or "", "buyerName": who(r.buyer),
            "claimedBy": claimed, "claimedName": who(claimed),
            "mine": me in (r.buyer, claimed, r.content_by),
            "units": cint(r.units), "cost": flt(r.total_cost),
            "image": (finals[0].get("url") if finals and r.stage in ("review", "live") else "") or r.ref_image or "",
            "error": r.error or "", "sinceBuy": _age_days(r.bought_at or r.creation),
            "po": r.purchase_order or "", **_variant_counts(variants),
            "escalate": _age_days(r.bought_at or r.creation) > cint(s.get("escalateDays") or 21)
                        and r.stage not in ("live", "dropped"),
            "sold": sold.get(r.name) if r.stage == "live" else None,
            "publishedAt": str(r.published_at or "")[:16],
            "droppedFrom": r.get("dropped_from") or "", "note": (r.review_note or "") if r.stage == "dropped" else "",
        }

    cards = [card(r) for r in active] + [card(r) for r in live]
    dropped = [card(r) for r in gone]
    late = sum(1 for c in cards if c["late"])
    tied = sum(c["cost"] for c in cards if c["stage"] != "live")

    # Receipt → Live, and the time each stage really takes, from the cards'
    # history. Cards launched before the history existed are not counted.
    spans, per_stage = [], {}
    for m in month:
        log = _stage_log(m.get("stage_log"))
        rec = next((e["at"] for e in log if e.get("s") == "photos"), None)
        lv = next((e["at"] for e in reversed(log) if e.get("s") == "live"), None)
        if rec and lv:
            spans.append(time_diff_in_hours(get_datetime(lv), get_datetime(rec)) / 24)
        for st, d, done in _durations(log):
            if done and st in stage_days:
                per_stage.setdefault(st, []).append(d)
    for r in active:
        for st, d, done in _durations(_stage_log(r.get("stage_log"))):
            if done and st in stage_days:
                per_stage.setdefault(st, []).append(d)
    bought_m = sum(cint(m.units) for m in month)
    sold_m = sum(sold.get(m.name, 0) for m in month)
    return {
        "stages": STAGES[:-1], "cards": cards, "droppedCards": dropped, "late": late,
        "notLive": round(tied, 2), "dropped": len(dropped), "stageDays": stage_days,
        "kpi": {
            "launchDays": cint(s.get("launchDays") or 5),
            "receiptToLive": round(sum(spans) / len(spans), 1) if spans else None,
            "receiptToLiveN": len(spans),
            "stageTime": {k: {"avg": round(sum(v) / len(v), 1), "n": len(v)} for k, v in per_stage.items()},
            "liveWeek": len(live), "launchedMonth": len(month),
            "sellThrough": round(sold_m * 100.0 / bought_m) if bought_m else None,
            "soldMonth": sold_m, "boughtMonth": bought_m,
            "inCycle": len(active), "units": sum(cint(r.units) for r in active),
        },
        "openTrips": frappe.db.count(DT_TRIP, {"status": "Open"}),
        "escalateDays": cint(s.get("escalateDays") or 21),
        "me": me, "isManager": _role() == "manager",
        "canBuy": _role() in ("manager", "sourcing"),
        "canReceive": _can_receive(), "canPhoto": _can_photo(), "canStudio": _can_studio(),
        "canContent": _can_content(), "canReview": _can_review()}


@frappe.whitelist(methods=["POST"])
def claim(name, release=0):
    """'This one is mine' in the card's current stage; a stage change frees it."""
    _gate_view()
    if not _has_col(DT_PRODUCT, "claimed_by"):
        frappe.throw("Update in progress — try again in a minute.")
    doc = _lock_product(name)
    if doc.stage in ("live", "dropped"):
        frappe.throw("This card left the cycle.")
    cur = doc.get("claimed_by") or ""
    if cint(release):
        if cur and cur != frappe.session.user and _role() != "manager":
            frappe.throw(f"{_user_name(cur)} has it.")
        doc.db_set("claimed_by", "", update_modified=False)
    else:
        if cur and cur != frappe.session.user and _role() != "manager":
            frappe.throw(f"{_user_name(cur)} already took it.")
        doc.db_set("claimed_by", frappe.session.user, update_modified=False)
        doc.add_comment("Comment", f"Souk: {_user_name(frappe.session.user)} took it ({doc.stage}).")
    frappe.db.commit()
    return {"claimedBy": doc.get("claimed_by") or "", "claimedName": _user_name(doc.get("claimed_by"))}


@frappe.whitelist()
def product(name):
    _gate_view()
    doc = frappe.get_doc(DT_PRODUCT, name)
    variants = json.loads(doc.variants_json or "[]")
    codes = [v["itemCode"] for v in variants if v.get("itemCode")]
    stock = {}
    if codes:
        for b in frappe.db.sql(
                """SELECT item_code, warehouse, actual_qty FROM `tabBin`
                   WHERE item_code IN %s AND actual_qty != 0""", (tuple(codes),), as_dict=True):
            stock.setdefault(b.item_code, []).append({"warehouse": b.warehouse, "qty": flt(b.actual_qty)})
    pos = frappe.db.sql(
        """SELECT po.name, po.supplier, po.grand_total, po.status, po.per_received, po.transaction_date,
                  po.custom_souk_trip AS trip, po.custom_souk_received AS pr, po.custom_souk_owed AS owed,
                  po.custom_souk_debit_note AS debit_note, po.custom_souk_outcome AS outcome{pay}
           FROM `tabPurchase Order` po
           WHERE (po.custom_souk_product = %s OR po.name = %s) AND po.docstatus = 1
           ORDER BY po.creation""".format(
            pay=", po.custom_souk_pay AS pay, po.custom_souk_pay_ref AS pay_ref, po.custom_souk_pay_due AS pay_due"
            if _has_col("Purchase Order", "custom_souk_pay") else ""),
        (doc.name, doc.purchase_order or "-"), as_dict=True)
    for p in pos:
        # A basket PO: this card's own share of it (its lines, its receipt,
        # what the stall owes back on them), not the whole basket's.
        if p.name != doc.purchase_order:
            continue
        parts = _po_parts(p.name)
        if len(parts) < 2:
            continue
        mine = next((x["codes"] for x in parts if x["key"] == doc.name), [])
        part = _parts_done(p.outcome).get(doc.name) or {}
        p.pr, p.owed, p.debit_note = part.get("pr") or "", flt(part.get("owed")), part.get("debitNote") or ""
        p.outcome = json.dumps({"lines": part.get("lines") or [], "target": part.get("target") or "",
                                "notes": part.get("notes") or []}) if part else None
        p.grand_total = round(sum(cint(v.get("qty")) * flt(v.get("cost")) for v in variants
                                  if v.get("itemCode") in mine), 2)
        p.basket = len(parts)
    money_eyes = _role() == "manager" or _is_accountant()
    events = [{"at": str(c.creation)[:16], "text": c.content, "by": _user_name(c.owner)}
              for c in frappe.get_all("Comment", filters={"reference_doctype": DT_PRODUCT,
                                                           "reference_name": doc.name,
                                                           "comment_type": "Comment"},
                                      fields=["creation", "content", "owner"], order_by="creation asc")]
    return {
        "name": doc.name, "title": doc.title, "stage": doc.stage, "stageAt": str(doc.stage_at or "")[:16],
        "age": _age_days(doc.stage_at), "category": doc.category, "brand": doc.brand,
        "stall": doc.supplier, "trip": doc.trip, "buyer": _user_name(doc.buyer),
        "boughtAt": str(doc.bought_at or "")[:16], "units": cint(doc.units), "cost": flt(doc.total_cost),
        "shopifyId": doc.shopify_product_id or "", "po": doc.purchase_order or "",
        "pi": doc.purchase_invoice or "", "image": doc.ref_image or "", "receipt": doc.receipt_image or "",
        "error": doc.error or "",
        "variants": [{**v, "stock": stock.get(v.get("itemCode"), [])} for v in variants],
        "purchases": [{"po": p.name, "stall": p.supplier, "amount": flt(p.grand_total), "status": p.status,
                       "received": flt(p.per_received), "date": str(p.transaction_date), "trip": p.trip,
                       "pr": p.pr or "", "owed": flt(p.owed), "debitNote": p.debit_note or "",
                       "outcome": _loads(p.outcome), "pay": p.get("pay") or "", "basket": cint(p.get("basket")),
                       # The cheque number and due date are the books' business.
                       "payRef": (p.get("pay_ref") or "") if money_eyes else "",
                       "payDue": str(p.get("pay_due") or "") if money_eyes else ""}
                      for p in pos],
        "owed": round(sum(flt(p.owed) for p in pos), 2),
        "events": events,
        "canBuy": _role() in ("manager", "sourcing"),
        "canReceive": _can_receive(),
        "canPhoto": _can_photo(), "canStudio": _can_studio(),
        "canContent": _can_content(), "canReview": _can_review(),
        "content": _loads(doc.content_json) or {}, "contentBy": _user_name(doc.content_by),
        "rejects": cint(doc.reject_count), "publishedBy": _user_name(doc.reviewed_by),
        "publishedAt": str(doc.published_at or "")[:16], "shopifyAdmin": _shopify_admin_url(doc.shopify_product_id),
        "photos": _loads(doc.photos_json) or [], "finals": _loads(doc.finals_json) or [],
        "specs": doc.specs or "",
        "money": _money(doc, variants, pos),
        "stockSplit": _stock_block(variants),
        "stages": _stage_rows(doc),
        "claimedBy": doc.get("claimed_by") or "", "claimedName": _user_name(doc.get("claimed_by")),
        "droppedFrom": doc.get("dropped_from") or "", "reviewNote": doc.review_note or "",
        "canDrop": _role() == "manager" and doc.stage not in ("live", "dropped")
                   and not (doc.stage == "buying" and doc.purchase_order),
        "me": frappe.session.user, "isManager": _role() == "manager",
        "canClaim": doc.stage not in ("live", "dropped"),
    }


def _money(doc, variants, pos):
    """Where the money went, per piece: what we paid the stall, the share
    of the taxi, what broke on our side, and what the stall owes back."""
    costs = _costs(doc, variants) if any(v.get("itemCode") for v in variants) else {}
    units = sum(cint(v.get("qty")) for v in variants) or cint(doc.units)
    paid = sum(flt(v.get("cost")) * cint(v.get("qty")) for v in variants) or flt(doc.total_cost)
    landed = sum(flt((costs.get(v.get("itemCode")) or {}).get("landed") or v.get("cost")) * cint(v.get("qty"))
                 for v in variants)
    allocated = bool(costs) and all(k.get("allocated") for k in costs.values())
    broken_ours, broken_units = 0.0, 0
    for p in pos:
        out = _loads(p.outcome) or {}
        for ln in out.get("lines") or []:
            n = cint(ln.get("brokenTransport")) + cint(ln.get("brokenWarehouse"))
            broken_units += n
            broken_ours += n * flt(ln.get("rate"))
    owed = sum(flt(p.owed) for p in pos)
    return {
        "paid": round(paid, 2), "units": units,
        "perPiece": round(paid / units, 2) if units else 0,
        "transport": round(landed - paid, 2) if allocated else None,
        "landedPerPiece": round(landed / units, 2) if units and allocated else None,
        "allocated": allocated,
        "brokenOurs": round(broken_ours, 2), "brokenUnits": broken_units,
        "owed": round(owed, 2),
    }


def _stock_block(variants):
    codes = [v["itemCode"] for v in variants if v.get("itemCode")]
    if not codes:
        return {"shelf": 0, "studio": 0, "defective": 0, "receiving": 0}
    shelf, studio = _stock_split(variants)
    r = frappe.db.sql("""SELECT SUM(CASE WHEN warehouse = %s THEN actual_qty ELSE 0 END),
                                SUM(CASE WHEN warehouse = %s THEN actual_qty ELSE 0 END)
                         FROM `tabBin` WHERE item_code IN %s""", (DEFECTIVE_WH, RECEIVING_WH, tuple(codes)))
    return {"shelf": shelf, "studio": studio, "defective": cint(r[0][0]), "receiving": cint(r[0][1])}


def _stage_rows(doc):
    """Each stage the card went through: when, by whom, how long, late."""
    days = settings().get("stageDays") or {}
    log = _stage_log(doc)
    if not log:
        log = [{"s": doc.stage, "at": str(doc.stage_at or doc.creation)[:19], "by": ""}]
    out = []
    rows = _durations(log)
    for i, e in enumerate(log):
        st, d, done = rows[i] if i < len(rows) else (e.get("s"), 0, False)
        limit = cint(days.get(st)) or 0
        out.append({"stage": st, "at": str(e.get("at") or "")[:16], "by": _user_name(e.get("by")),
                    "days": d, "limit": limit, "late": bool(limit and d > limit), "current": not done})
    return out


# --- receiving ----------------------------------------------------------------
#
# One delivery per purchase: the taxi brings the trip's goods the same day,
# so a souk PO is received ONCE and then closed. Per variant the floor counts
#   good    — onto a real shelf (mapped to Shopify, pickable), minus the
#             studio samples, which go to Studio - JM;
#   broken  — by where it broke (Ahmed, 2026-11-17):
#               at the stall      → not ours: not received, the stall owes it;
#               in transport      → ours: Defective Items, transport-loss account;
#               in our warehouse  → ours: Defective Items, warehouse-loss account;
#   short   — ordered − good − broken: the stall owes it.
# The stall's debt = (short + broken at the stall) × the price paid. With a
# paid invoice it is a Debit Note (a return invoice that is NOT paid: the
# stall owes the money, nothing came back into the custody); without one
# (no custody account in the books yet) it is recorded on the PO for the
# accountant. The PO is then closed: nothing else is coming.
#
# Never Receiving Zone - JM: it is a rejected warehouse (picking vetoes it)
# and has no Shopify mapping, so the Draft would never get its quantity.

BROKEN_WHERE = ("supplier", "transport", "warehouse")


def _can_receive():
    return _role() in ("manager", "dispatcher", "returns", "packer")


def _gate_receive():
    if not _can_receive():
        frappe.throw("Not authorized to receive stock.", frappe.PermissionError)


def _loads(raw):
    try:
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _shelves():
    """Shelves a souk product can be received onto: movable, not rejected
    (pickable), and mapped to Shopify (sellable). Never a consignment section
    (CN - <supplier> / Consignment Receiving): souk goods are OURS, and a
    consignment shelf means the supplier owns what sits on it."""
    from logistics_portal.api.stock_moves import _movable_condition
    cond, args = _movable_condition("w.name")
    return [r[0] for r in frappe.db.sql(
        f"""SELECT w.name FROM `tabWarehouse` w
            WHERE w.is_group = 0 AND w.disabled = 0 AND IFNULL(w.is_rejected_warehouse, 0) = 0
              AND w.name NOT LIKE 'CN - %%' AND w.name NOT LIKE 'Consignment%%'
              AND {cond}
              AND EXISTS (SELECT 1 FROM `tabShopify Warehouse Mapping` m WHERE m.erpnext_warehouse = w.name)
            ORDER BY w.name""", tuple(args))]


# A new product's sales speed is unknown: it starts in the slotting plan's
# B zone (H/J/F today) until its picks say otherwise (slotting.zone_roles).
NEW_PRODUCT_CLASS = "B"


def _shelf_fill(shelves):
    """shelf -> distinct SKUs stocked on it (how crowded the face is)."""
    if not shelves:
        return {}
    return {w: cint(n) for w, n in frappe.db.sql(
        """SELECT warehouse, COUNT(DISTINCT item_code) FROM `tabBin`
           WHERE actual_qty > 0 AND warehouse IN %s GROUP BY warehouse""", (tuple(shelves),))}


def _shelf_suggest(item_codes, shelves, fill):
    """Up to three shelves, each with its reason, best first:
    1. where these very items already sit (a rebuy: never split one SKU),
    2. where the product's other colours/sizes sit (one product, one face),
    3. the emptiest bins of the new-product zone, one per aisle letter."""
    ok, out, seen = set(shelves), [], set()

    def add(w, why, n=0):
        if w in ok and w not in seen and len(out) < 3:
            seen.add(w)
            out.append({"shelf": w, "why": why, "n": cint(n)})

    codes = [c for c in item_codes if c]
    if codes:
        for w, q in frappe.db.sql(
                """SELECT warehouse, SUM(actual_qty) FROM `tabBin` WHERE item_code IN %s AND actual_qty > 0
                   GROUP BY warehouse ORDER BY SUM(actual_qty) DESC""", (tuple(codes),)):
            add(w, "stock", q)
        tpl = [t for t in frappe.get_all("Item", filters={"name": ["in", codes]}, pluck="variant_of") if t]
        if tpl:
            for w, q in frappe.db.sql(
                    """SELECT b.warehouse, SUM(b.actual_qty) FROM `tabBin` b JOIN `tabItem` i ON i.name = b.item_code
                       WHERE i.variant_of IN %s AND b.item_code NOT IN %s AND b.actual_qty > 0
                       GROUP BY b.warehouse ORDER BY SUM(b.actual_qty) DESC""", (tuple(tpl), tuple(codes))):
                add(w, "family", q)
    if len(out) < 3:
        try:
            from logistics_portal.api.slotting import _SHELF_RE, zone_roles
            letters = set(zone_roles().get(NEW_PRODUCT_CLASS) or ())
        except Exception:
            letters, _SHELF_RE = set(), None
        cand = [w for w in shelves if w[:1] in letters and (_SHELF_RE is None or _SHELF_RE.match(w))]
        cand.sort(key=lambda w: (fill.get(w, 0), w))
        used = {o["shelf"][:1] for o in out}
        for w in cand:
            if len(out) >= 3:
                break
            if w[:1] in used:
                continue
            used.add(w[:1])
            add(w, "empty" if not fill.get(w) else "light", fill.get(w, 0))
    return out


def _po_lines_for(po):
    return frappe.db.sql(
        """SELECT poi.name AS po_item, poi.item_code, poi.item_name, poi.qty, poi.received_qty,
                  poi.rate, poi.uom, poi.conversion_factor AS cf, i.custom_sku AS sku,
                  i.weight_per_unit AS kg, i.weight_uom
           FROM `tabPurchase Order Item` poi JOIN `tabItem` i ON i.name = poi.item_code
           WHERE poi.parent = %s ORDER BY poi.idx""", (po,), as_dict=True)


def _po_invoice(po):
    r = frappe.db.sql(
        """SELECT DISTINCT pi.name FROM `tabPurchase Invoice` pi
           JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
           WHERE pii.purchase_order = %s AND pi.docstatus = 1 AND pi.is_return = 0
           ORDER BY pi.creation LIMIT 1""", (po,))
    return r[0][0] if r else None


# A basket PO carries several products. Each is received on its own (it may
# come on another taxi): a "part" is one card's lines, or AGAIN_PART for the
# buy-again lines. Parts done so far live in custom_souk_outcome["parts"];
# custom_souk_received is written only when the last part is in.
AGAIN_PART = "_again"


def _po_parts(po, lines=None):
    lines = lines if lines is not None else _po_lines_for(po)
    have = {l.item_code for l in lines}
    parts, taken = [], set()
    for c in frappe.get_all(DT_PRODUCT, filters={"purchase_order": po},
                            fields=["name", "title", "ref_image", "stage", "variants_json"], order_by="creation asc"):
        codes = [v.get("itemCode") for v in json.loads(c.variants_json or "[]")
                 if v.get("itemCode") in have and v.get("itemCode") not in taken]
        if codes:
            taken.update(codes)
            parts.append({"key": c.name, "card": c, "codes": codes})
    rest = [l.item_code for l in lines if l.item_code not in taken]
    if rest:
        parts.append({"key": AGAIN_PART, "card": None, "codes": rest})
    return parts


def _parts_done(outcome_raw):
    out = _loads(outcome_raw) or {}
    return out.get("parts") or {}


def _part_amount(lines, codes):
    return round(sum(flt(l.qty) * flt(l.rate) for l in lines if l.item_code in codes), 2)


@frappe.whitelist()
def receive_queue():
    """Souk purchases waiting for the taxi: submitted, not yet received."""
    _gate_receive()
    rows = frappe.db.sql(
        f"""SELECT po.name, po.supplier, po.grand_total, po.transaction_date, po.custom_souk_trip AS trip,
                   po.custom_souk_product AS product, po.custom_souk_outcome AS outcome, p.title, p.ref_image
            FROM `tabPurchase Order` po
            LEFT JOIN `tab{DT_PRODUCT}` p ON p.name = po.custom_souk_product
            WHERE po.docstatus = 1 AND {_souk_po_sql()}
              AND IFNULL(po.custom_souk_received, '') = ''
              AND po.status NOT IN ('Closed', 'Completed', 'Cancelled')
            ORDER BY po.creation""", as_dict=True)
    out = []
    for r in rows:
        lines = _po_lines_for(r.name)
        parts = _po_parts(r.name, lines)
        done = _parts_done(r.outcome)
        single = len(parts) == 1
        for pt in parts:
            if pt["key"] in done:
                continue
            c = pt["card"]
            out.append({"po": r.name, "part": pt["key"], "stall": r.supplier,
                        "amount": _part_amount(lines, pt["codes"]), "date": str(r.transaction_date),
                        "trip": r.trip or "", "product": c.name if c else (r.product or "" if single else ""),
                        "title": c.title if c else (r.title or "" if single else ""),
                        "image": c.ref_image if c else (r.ref_image or "" if single else ""),
                        "again": pt["key"] == AGAIN_PART, "lines": len(pt["codes"]),
                        "units": cint(sum(flt(l.qty) for l in lines if l.item_code in pt["codes"])),
                        "basket": len(parts), "basketLeft": len([x for x in parts if x["key"] not in done])})
    return {"rows": out}


@frappe.whitelist()
def receive_boot(po, part=None):
    _gate_receive()
    h = frappe.db.get_value("Purchase Order", po, ["name", "supplier", "docstatus", "status",
                                                    "custom_souk_trip", "custom_souk_product",
                                                    "custom_souk_received", "custom_souk_outcome"]
                            + (["custom_souk_buyer"] if _has_col("Purchase Order", "custom_souk_buyer") else []),
                            as_dict=True)
    if not h or not _is_souk_po(h):
        frappe.throw("Not a souk purchase.")
    all_lines = _po_lines_for(po)
    parts = _po_parts(po, all_lines)
    done = _parts_done(h.custom_souk_outcome)
    pt = _pick_part(parts, done, part)
    prod = pt["card"] if pt and pt["card"] else (
        frappe.db.get_value(DT_PRODUCT, h.custom_souk_product,
                            ["name", "title", "ref_image", "stage", "variants_json"], as_dict=True)
        if h.custom_souk_product and len(parts) == 1 else None)
    labels, colors, sizes = {}, {}, {}
    if prod:
        for v in json.loads(prod.variants_json or "[]"):
            labels[v.get("itemCode")] = " · ".join(x for x in (v.get("colorFr"), v.get("sizeLabel")) if x)
            colors[v.get("itemCode")] = v.get("color") or ""
            sizes[v.get("itemCode")] = v.get("sizeLabel") or ""
    s = settings()
    lines = []
    for l in all_lines:
        if pt and l.item_code not in pt["codes"]:
            continue
        uom = (l.weight_uom or "Kg").lower()
        # Grams for the screen, whatever unit the item was weighed in (the
        # server takes any weight > 0 as already weighed).
        kg = flt(l.kg) * {"kg": 1, "kilogram": 1, "": 1, "g": 0.001, "gram": 0.001, "gm": 0.001}.get(uom, 0)
        lines.append({"itemCode": l.item_code, "sku": l.sku or l.item_code, "label": labels.get(l.item_code) or l.item_name,
                      "ordered": flt(l.qty), "already": flt(l.received_qty), "rate": flt(l.rate),
                      "grams": round(kg * 1000) if kg else None, "color": colors.get(l.item_code, ""),
                      "size": sizes.get(l.item_code, "")})
    first_variant = lines[0]["itemCode"] if lines else ""
    shelves = _shelves()
    fill = _shelf_fill(shelves)
    return {
        "po": h.name, "stall": h.supplier, "trip": h.custom_souk_trip,
        "done": h.custom_souk_received or (((done.get(pt["key"]) or {}).get("pr") or "") if pt else ""),
        "part": pt["key"] if pt else "", "again": bool(pt and pt["key"] == AGAIN_PART),
        "parts": [{"key": x["key"], "title": x["card"].title if x["card"] else "", "done": x["key"] in done,
                   "lines": len(x["codes"])} for x in parts],
        "closed": h.status in ("Closed", "Completed"),
        "product": prod.name if prod else "", "title": prod.title if prod else "",
        "image": prod.ref_image if prod else "", "isNew": bool(prod and prod.stage == "bought"),
        "lines": lines, "shelves": shelves, "shelfFill": fill,
        "suggest": _shelf_suggest([x["itemCode"] for x in lines], shelves, fill),
        "newZone": NEW_PRODUCT_CLASS,
        "studioSamples": cint(s.get("studioSamples")) if prod and prod.stage == "bought" else 0,
        "studioDefault": first_variant,
        # One sample of each colour (the studio shoots every colour), the
        # first size of it.
        "studioPerColor": list(dict.fromkeys(
            next(x["itemCode"] for x in lines if x["color"] == c) for c in [x["color"] for x in lines])),
        "lossAccounts": {"transport": bool(s.get("transportLossAccount")),
                         "warehouse": bool(s.get("warehouseLossAccount"))},
        "hasInvoice": bool(_po_invoice(po)),
    }


@frappe.whitelist(methods=["POST"])
def receive(po, payload):
    """Post the one receiving of a souk purchase. payload:
    {target, lines: [{itemCode, good, broken: {supplier, transport, warehouse}, grams}],
     studio: {itemCode: n}, labels: 1, note}"""
    _gate_receive()
    p = json.loads(payload) if isinstance(payload, str) else (payload or {})
    # Held for the whole receiving: two phones (or a retried tap) on the same
    # purchase must not post two receipts for the same pieces.
    if not frappe.db.sql("SELECT name FROM `tabPurchase Order` WHERE name = %s FOR UPDATE", (po,)):
        frappe.throw("Purchase not found.")
    h = frappe.get_doc("Purchase Order", po)
    if not _is_souk_po(h):
        frappe.throw("Not a souk purchase.")
    if h.get("custom_souk_received"):
        frappe.throw(f"Already received ({h.custom_souk_received}).")
    all_lines = _po_lines_for(po)
    parts = _po_parts(po, all_lines)
    done = _parts_done(h.get("custom_souk_outcome"))
    if len(parts) > 1 and not p.get("part"):
        frappe.throw("This purchase has several products: receive them one by one (update the app).")
    pt = _pick_part(parts, done, p.get("part"))
    if not pt:
        frappe.throw("Nothing left to receive on this purchase.")
    if pt["key"] in done:
        frappe.throw(f"Already received ({done[pt['key']].get('pr')}).")
    if h.docstatus != 1 or h.status in ("Closed", "Completed", "Cancelled"):
        frappe.throw("That PO is not open.")
    target = (p.get("target") or "").strip()
    if target and target not in _shelves():
        frappe.throw("Choose a shelf: a sellable bin that is on Shopify.")
    studio = {k: cint(v) for k, v in (p.get("studio") or {}).items() if cint(v) > 0}

    po_lines = {l.item_code: l for l in all_lines if l.item_code in pt["codes"]}
    counted = {}
    for ln in p.get("lines") or []:
        code = ln.get("itemCode")
        if code not in po_lines:
            frappe.throw(f"{code} is not on this purchase.")
        br = ln.get("broken") or {}
        c = {"good": cint(ln.get("good")), **{w: cint(br.get(w)) for w in BROKEN_WHERE},
             "grams": flt(ln.get("grams"))}
        if min(c["good"], *(c[w] for w in BROKEN_WHERE)) < 0:
            frappe.throw("Counts cannot be negative.")
        counted[code] = c
    if not counted:
        frappe.throw("Count the pieces first.")
    # Weight is optional (Ahmed 2026-11-20): only a typed weight must be sane.
    bad_w = [po_lines[c].sku or c for c, v in counted.items()
             if v["grams"] and not (1 <= v["grams"] <= 100000)]
    if bad_w:
        frappe.throw("A weight must be between 1 and 100000 grams: " + ", ".join(bad_w))
    nothing_came = not any(c["good"] + c["transport"] + c["warehouse"] + c["supplier"] for c in counted.values())
    if nothing_came and not cint(p.get("nothingCame")):
        frappe.throw("Nothing counted. If nothing arrived at all, confirm it as fully short.")

    rows, outcome, owed, owed_lines = [], [], 0.0, {}
    for code, l in po_lines.items():
        c = counted.get(code) or {"good": 0, "supplier": 0, "transport": 0, "warehouse": 0, "grams": 0}
        pending = flt(l.qty) - flt(l.received_qty)
        arrived = c["good"] + c["supplier"] + c["transport"] + c["warehouse"]
        if arrived > pending:
            frappe.throw(f"{l.sku or code}: {arrived} counted, only {int(pending)} were bought.")
        smp = studio.get(code, 0)
        if smp > c["good"]:
            frappe.throw(f"{l.sku or code}: more studio samples than good pieces.")
        short = int(pending - arrived)
        base = {"rate": flt(l.rate), "uom": l.uom, "conversion_factor": flt(l.cf or 1),
                "purchase_order": po, "purchase_order_item": l.po_item, "item_code": code}
        if c["good"] - smp > 0:
            rows.append({**base, "qty": c["good"] - smp, "warehouse": target})
        if smp:
            rows.append({**base, "qty": smp, "warehouse": STUDIO_WH})
        if c["transport"] + c["warehouse"]:
            rows.append({**base, "qty": c["transport"] + c["warehouse"], "warehouse": DEFECTIVE_WH})
        stall_qty = short + c["supplier"]
        if stall_qty:
            owed += stall_qty * flt(l.rate)
            owed_lines[code] = stall_qty
        outcome.append({"itemCode": code, "sku": l.sku or code, "ordered": int(pending), "good": c["good"],
                        "studio": smp, "short": short, "brokenSupplier": c["supplier"],
                        "brokenTransport": c["transport"], "brokenWarehouse": c["warehouse"],
                        "rate": flt(l.rate)})
    owed = round(owed, 2)

    pr = None
    if rows and not target:
        frappe.throw("Choose a shelf: a sellable bin that is on Shopify.")
    if rows:
        pr = _post_receipt(h, po, target, rows, p.get("note"))
    s = settings()
    notes = []
    if not rows:
        notes.append("Nothing of ours arrived: no receipt, the stall owes the whole purchase.")
    want = cint(p.get("labels", 1))
    mode = "here" if p.get("labelsMode") == "here" else "station"
    return _after_receive(h, po, pr, target, rows, outcome, owed, owed_lines, counted, studio, s, notes,
                          want and mode == "station", print_here=want and mode == "here",
                          part=pt, parts=parts, done=done)


def _pick_part(parts, done, key):
    if key:
        pt = next((x for x in parts if x["key"] == key), None)
        if not pt:
            frappe.throw("That product is not on this purchase.")
        return pt
    return next((x for x in parts if x["key"] not in done), parts[0] if parts else None)


def _post_receipt(h, po, target, rows, note):
    pr = frappe.get_doc({
        "doctype": "Purchase Receipt", "supplier": h.supplier, "company": COMPANY,
        "currency": h.currency or "MAD", "conversion_rate": flt(h.conversion_rate or 1),
        # Header warehouse only when every row agrees (as Goods In does): rows
        # here are split between the shelf, the studio and Defective Items.
        "set_warehouse": rows[0]["warehouse"] if len({r["warehouse"] for r in rows}) == 1 else None,
        "remarks": f"Portal souk receiving by {frappe.session.user} — PO {po} (trip {h.custom_souk_trip})"
                   + (f" — {note.strip()[:200]}" if (note or "").strip() else ""),
        "items": rows,
    })
    pr.flags.ignore_permissions = True
    frappe.flags.lp_souk_receiving = True
    try:
        pr.insert(ignore_permissions=True)
        pr.submit()
    finally:
        frappe.flags.lp_souk_receiving = False
    return pr


def guard_souk_receipt(doc, method=None):
    """Purchase Receipt validate: a souk PO is received on Souk receiving only
    (portal or Desk alike). Elsewhere the goods land unweighed, without the
    studio sample, often in Receiving Zone, and the product card never moves
    on. Returns (is_return) are left alone."""
    if doc.get("is_return") or frappe.flags.get("lp_souk_receiving"):
        return
    try:
        pos = {r.get("purchase_order") for r in (doc.get("items") or []) if r.get("purchase_order")}
        if not pos or not _has_col("Purchase Order", "custom_souk_trip"):
            return
        fields = ["name", "custom_souk_trip"] + (
            ["custom_souk_buyer"] if _has_col("Purchase Order", "custom_souk_buyer") else [])
        souk = [h.name for h in frappe.get_all("Purchase Order", filters={"name": ["in", list(pos)]},
                                               fields=fields) if _is_souk_po(h)]
    except Exception:
        # A guard must never be the reason a legitimate document cannot save.
        frappe.log_error(frappe.get_traceback()[:2000], "souk.guard_souk_receipt")
        return
    if souk:
        frappe.throw(
            f"{', '.join(souk)} is a souk purchase — receive it on Souk receiving "
            "(/logistics/souk/receive). There a sample goes to the studio, a piece is "
            "weighed, the shelf is checked against Shopify and the product moves on to "
            "the photos.", title="Souk purchase")


def _after_receive(h, po, pr, target, rows, outcome, owed, owed_lines, counted, studio, s, notes, want_labels,
                   print_here=False, part=None, parts=None, done=None):
    parts = parts or [{"key": AGAIN_PART, "card": None, "codes": [o["itemCode"] for o in outcome]}]
    part = part or parts[0]
    done = dict(done or {})
    last = all(x["key"] in done or x["key"] == part["key"] for x in parts)
    pr_name = pr.name if pr else "NONE"
    # Our breakage leaves the books into its own account — or waits for one.
    write_offs = []
    for where, key in (("transport", "transportLossAccount"), ("warehouse", "warehouseLossAccount")):
        qty_by = {o["itemCode"]: o["broken" + where.capitalize()] for o in outcome if o["broken" + where.capitalize()]}
        if not qty_by:
            continue
        acct = s.get(key)
        if not acct:
            notes.append(f"{sum(qty_by.values())} broken in {where} wait in {DEFECTIVE_WH}: "
                         f"no {where}-loss account set yet.")
            continue
        se = frappe.get_doc({
            "doctype": "Stock Entry", "stock_entry_type": "Material Issue", "purpose": "Material Issue",
            "company": COMPANY,
            "remarks": f"Souk breakage in {where} — PO {po} / {pr_name}",
            "items": [{"item_code": code, "qty": q, "s_warehouse": DEFECTIVE_WH, "expense_account": acct}
                      for code, q in qty_by.items()],
        })
        se.insert(ignore_permissions=True)
        se.submit()
        write_offs.append(se.name)

    debit_note = ""
    if owed_lines:
        pi = _po_invoice(po)
        if pi:
            debit_note = _make_debit_note(pi, owed_lines, po)
        else:
            notes.append(f"The stall owes {owed:,.2f} MAD — no invoice in the books yet, "
                         "the accountant posts the Debit Note with the invoice.")

    # Weights: entered in grams, stored in kg (the catalogue is Kg).
    for code, c in counted.items():
        if c["grams"] and 1 <= c["grams"] <= 100000:
            frappe.db.set_value("Item", code, {"weight_per_unit": round(c["grams"] / 1000.0, 4),
                                               "weight_uom": "Kg"})

    done[part["key"]] = {"pr": pr_name, "owed": owed, "debitNote": debit_note, "lines": outcome,
                         "target": target, "writeOffs": write_offs, "notes": notes,
                         "by": frappe.session.user, "at": str(now_datetime())[:16]}
    every = [done[x["key"]] for x in parts if x["key"] in done]
    total_owed = round(sum(flt(d.get("owed")) for d in every), 2)
    prs = [d["pr"] for d in every if d.get("pr") and d["pr"] != "NONE"]
    frappe.db.set_value("Purchase Order", po, {
        # Written once the last product of the purchase is in: the queue,
        # the trip and the stall read it as "received".
        "custom_souk_received": (prs[-1] if prs else "NONE") if last else "",
        "custom_souk_owed": total_owed,
        "custom_souk_debit_note": ", ".join(d["debitNote"] for d in every if d.get("debitNote"))[:140],
        "custom_souk_outcome": json.dumps({"lines": [ln for d in every for ln in d["lines"]], "target": target,
                                           "writeOffs": [w for d in every for w in d.get("writeOffs") or []],
                                           "notes": [n for d in every for n in d.get("notes") or []],
                                           "by": frappe.session.user, "at": str(now_datetime())[:16],
                                           **({"parts": done} if len(parts) > 1 else {})},
                                          ensure_ascii=False),
    }, update_modified=False)
    if last and total_owed:
        # Short or broken at the stall: those pieces never come, so the PO is
        # closed (only now: the other products still had to be received).
        h.reload()
        if h.status not in ("Closed", "Completed"):
            h.update_status("Closed")

    labels = 0
    on_shelf = [(o["itemCode"], o["good"]) for o in outcome if o["good"]]
    if want_labels:
        from logistics_portal.api.labelprint import queue_items
        labels = queue_items(on_shelf, LABEL_STATION)
    # Printed on the receiving device itself: the same payloads the station
    # would print, handed back for the browser to print now.
    print_items = []
    if print_here and on_shelf:
        from logistics_portal.api.labelprint import label_items
        print_items = label_items(on_shelf)

    good = sum(o["good"] for o in outcome)
    summary = (f"Souk: received {good} good on {target.replace(' - JM', '')}"
               + (f" ({sum(studio.values())} to the studio)" if studio else "")
               + "".join(f" · {n} broken {w}" for w, n in (
                   ("at the stall", sum(o["brokenSupplier"] for o in outcome)),
                   ("in transport", sum(o["brokenTransport"] for o in outcome)),
                   ("in the warehouse", sum(o["brokenWarehouse"] for o in outcome))) if n)
               + (f" · {sum(o['short'] for o in outcome)} short" if any(o["short"] for o in outcome) else "")
               + (f" · {pr.name}" if pr else " · nothing of ours arrived")
               + (f" · the stall owes {owed:,.2f} MAD" + (f" ({debit_note})" if debit_note else "") if owed else "")
               + (f" · {labels} labels" if labels else ""))
    product = part["card"].name if part.get("card") else (h.get("custom_souk_product") if len(parts) == 1 else "")
    if product and frappe.db.exists(DT_PRODUCT, product):
        d = frappe.get_doc(DT_PRODUCT, product)
        d.add_comment("Comment", summary)
        for n in notes:
            d.add_comment("Comment", "Souk: " + n)
        if d.stage == "bought" and pr:
            # Waiting for the in-house photos: the samples are in the studio.
            _set_stage(d, "photos")
        elif d.stage == "bought":
            # Nothing of ours ever arrived: the card leaves the cycle; the
            # stall's debt stays on the PO.
            _set_stage(d, "dropped", review_note="nothing arrived: the stall owes the whole purchase")
    else:
        frappe.get_doc("Purchase Order", po).add_comment("Comment", summary)
    frappe.db.commit()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return {"ok": True, "receipt": pr_name, "good": good, "owed": owed, "debitNote": debit_note,
            "writeOffs": write_offs, "notes": notes, "labels": labels, "product": product or "",
            "printItems": print_items, "station": _station_state() if labels else None,
            "nextParts": [{"key": x["key"], "title": x["card"].title if x["card"] else ""}
                          for x in parts if x["key"] not in done]}


def _station_state():
    try:
        from logistics_portal.api.labelprint import station_state
        return station_state()
    except Exception:
        return None


def _make_debit_note(pi_name, qty_by_item, po):
    """A return invoice for what the stall owes — NOT paid: no cash came back
    into the custody, the stall's account carries the debt."""
    from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_debit_note
    dn = make_debit_note(pi_name)
    left = dict(qty_by_item)
    keep = []
    for it in dn.items:
        q = left.get(it.item_code, 0)
        if q <= 0:
            continue
        take = min(q, abs(flt(it.qty)))
        it.qty = -take
        it.received_qty = 0
        left[it.item_code] = q - take
        keep.append(it)
    if not keep:
        return ""
    dn.set("items", keep)
    dn.update_stock = 0
    dn.is_paid = 0
    dn.paid_amount = 0
    dn.base_paid_amount = 0
    dn.cash_bank_account = None
    dn.mode_of_payment = None
    dn.set("taxes", [])
    dn.remarks = f"Souk: short / broken at the stall on {po}"
    dn.run_method("calculate_taxes_and_totals")
    dn.insert(ignore_permissions=True)
    dn.submit()
    return dn.name


# --- transport by weight ------------------------------------------------------

@frappe.whitelist(methods=["POST"])
def allocate_transport(trip):
    """Spread the trip's taxi over what it carried, by weight (by value for a
    piece with no weight), as a Landed Cost Voucher credited to the custody
    account: the cash left the custody, the pieces carry it in their cost."""
    _gate_accountant()
    t = frappe.get_doc(DT_TRIP, cint(trip))
    amount = flt(t.transport_cost)
    if amount <= 0:
        frappe.throw("No transport on this trip.")
    acct = settings().get("custodyAccount")
    if not acct:
        frappe.throw("Name the custody cash account in the souk settings first.")
    if t.get("transport_lcv") and frappe.db.get_value("Landed Cost Voucher", t.transport_lcv, "docstatus") == 1:
        frappe.throw(f"Transport already spread on this trip ({t.transport_lcv}).")
    if t.status == "Open":
        # A purchase can still be added to an open custody; spreading now
        # would leave it out of the taxi's cost.
        frappe.throw("Close the custody first: purchases can still be added to it.")
    # The receipts themselves, not the PO's marker: a purchase where nothing
    # arrived is marked "NONE", and a basket has one receipt per product.
    prs = [r[0] for r in frappe.db.sql(
        """SELECT DISTINCT pri.parent FROM `tabPurchase Receipt Item` pri
           JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
           JOIN `tabPurchase Order` po ON po.name = pri.purchase_order
           WHERE po.custom_souk_trip = %s AND po.docstatus = 1 AND pr.docstatus = 1 AND pr.is_return = 0""",
        (str(t.name),))]
    if not prs:
        frappe.throw("Nothing received on this trip yet.")
    waiting = frappe.db.sql(
        """SELECT COUNT(*) FROM `tabPurchase Order` WHERE custom_souk_trip = %s AND docstatus = 1
           AND IFNULL(custom_souk_received, '') = '' AND status NOT IN ('Closed', 'Cancelled')""",
        (str(t.name),))[0][0]
    if waiting:
        frappe.throw(f"{waiting} purchase(s) of this trip are not received yet.")
    lcv = frappe.new_doc("Landed Cost Voucher")
    lcv.company = COMPANY
    lcv.distribute_charges_based_on = "Distribute Manually"
    for pr in prs:
        lcv.append("purchase_receipts", {"receipt_document_type": "Purchase Receipt", "receipt_document": pr,
                                         "supplier": frappe.db.get_value("Purchase Receipt", pr, "supplier")})
    lcv.get_items_from_purchase_receipts()
    weights = []
    for it in lcv.items:
        w = frappe.db.get_value("Item", it.item_code, ["weight_per_unit", "weight_uom"], as_dict=True) or {}
        kg = flt(w.get("weight_per_unit")) if (w.get("weight_uom") or "Kg").lower() == "kg" else 0
        weights.append(kg * flt(it.qty))
    total_w = sum(weights)
    total_v = sum(flt(it.amount) for it in lcv.items) or 1
    use_weight = total_w > 0 and all(weights)
    shares = [(w / total_w) if use_weight else (flt(it.amount) / total_v) for w, it in zip(weights, lcv.items)]
    run = 0.0
    for i, it in enumerate(lcv.items):
        part = round(amount * shares[i], 2) if i < len(lcv.items) - 1 else round(amount - run, 2)
        it.applicable_charges = part
        run += part
    lcv.append("taxes", {"description": f"Souk taxi — trip {t.name}", "expense_account": acct,
                         "amount": amount})
    lcv.insert(ignore_permissions=True)
    lcv.submit()
    t.db_set("transport_lcv", lcv.name)
    t.add_comment("Comment", f"Transport {amount:,.2f} MAD spread {'by weight' if use_weight else 'by value'} "
                             f"over {len(prs)} receipt(s): {lcv.name}.")
    frappe.db.commit()
    return {"lcv": lcv.name, "byWeight": use_weight}


# --- photos & studio ------------------------------------------------------------
#
# In-house photos (the floor, on the phone, 24 h from receiving): the first
# colour needs six angles, every other colour one front shot. They land on the
# card itself, so marketing never asks for them on WhatsApp. The person
# shooting also notes the measurements and the material.
#
# The finals (marketing, 3 days): uploaded on the card, put in order (the
# first is the main photo) and tied to a colour or to all colours. Handing to
# content puts them on the Shopify Draft as its media; each colour's first
# final becomes the image of that colour's variants. A resend replaces only
# the media WE pushed (ids kept on the card), never anything added by hand.

RAW_SLOTS = ("front", "back", "side", "detail", "size", "hand")
EXTRA_SLOT = "extra"
MAX_EXTRAS = 10
MAX_FINALS = 20


def _can_photo():
    return _role() in ("manager", "dispatcher", "returns", "packer")


def _can_studio():
    return _role() in ("manager", "marketing")


def _gate_photo():
    if not _can_photo():
        frappe.throw("Not authorized to photograph souk products.", frappe.PermissionError)


def _gate_studio():
    if not _can_studio():
        frappe.throw("Only marketing hands in the final photos.", frappe.PermissionError)


def _colors(variants):
    """The product's colours in buying order; one blank colour when the
    product has none."""
    names = {c["code"]: c for c in settings().get("colors") or []}
    out, seen = [], set()
    for v in variants:
        c = v.get("color") or ""
        if c in seen:
            continue
        seen.add(c)
        out.append({"code": c, "fr": v.get("colorFr") or (names.get(c) or {}).get("fr", ""),
                    "ar": (names.get(c) or {}).get("ar", "")})
    return out or [{"code": "", "fr": "", "ar": ""}]


def _required(colors):
    req = []
    for i, c in enumerate(colors):
        for slot in (RAW_SLOTS if i == 0 else ("front",)):
            req.append((c["code"], slot))
    return req


def _missing(colors, photos):
    have = {(p.get("color") or "", p.get("slot")) for p in photos}
    return [{"color": c, "slot": s} for c, s in _required(colors) if (c, s) not in have]


def _lock_product(name):
    """Row lock: two phones uploading at once must not lose a photo."""
    if not frappe.db.sql(f"SELECT name FROM `tab{DT_PRODUCT}` WHERE name = %s FOR UPDATE", (name,)):
        frappe.throw("Product not found.")
    return frappe.get_doc(DT_PRODUCT, name)


def _drop_files(dn, urls):
    for url in urls:
        for f in frappe.get_all("File", filters={"file_url": url, "attached_to_doctype": DT_PRODUCT,
                                                 "attached_to_name": dn}, pluck="name"):
            frappe.delete_doc("File", f, ignore_permissions=True, force=True)


def _hours_left(doc_stage_at, stage):
    days = cint((settings().get("stageDays") or {}).get(stage)) or 0
    if not days:
        return None
    return round(days * 24 - time_diff_in_hours(now_datetime(), doc_stage_at), 1)


def _studio_stock(variants):
    codes = [v["itemCode"] for v in variants if v.get("itemCode")]
    if not codes:
        return {}
    return {r[0]: flt(r[1]) for r in frappe.db.sql(
        "SELECT item_code, actual_qty FROM `tabBin` WHERE warehouse = %s AND item_code IN %s AND actual_qty > 0",
        (STUDIO_WH, tuple(codes)))}


def _samples(variants):
    st = _studio_stock(variants)
    return [{"sku": v["sku"], "color": v.get("color") or "", "colorFr": v.get("colorFr") or "",
             "size": v.get("sizeLabel") or "", "qty": st.get(v.get("itemCode"), 0)}
            for v in variants if st.get(v.get("itemCode"))]


@frappe.whitelist()
def photo_queue():
    _gate_photo()
    rows = frappe.get_all(DT_PRODUCT, filters={"stage": "photos"},
                          fields=["name", "title", "stage_at", "ref_image", "variants_json", "photos_json"],
                          order_by="stage_at asc", limit=200)
    out = []
    for r in rows:
        variants = _loads(r.variants_json) or []
        colors = _colors(variants)
        photos = _loads(r.photos_json) or []
        req = len(_required(colors))
        left = _hours_left(r.stage_at, "photos")
        out.append({"name": r.name, "title": r.title, "image": r.ref_image or "", "colors": len(colors),
                    "required": req, "done": req - len(_missing(colors, photos)),
                    "hoursLeft": left, "late": left is not None and left < 0,
                    "samples": sum(s["qty"] for s in _samples(variants))})
    return {"queue": out}


@frappe.whitelist()
def photo_boot(name):
    _gate_photo()
    doc = frappe.get_doc(DT_PRODUCT, name)
    variants = _loads(doc.variants_json) or []
    colors = _colors(variants)
    photos = _loads(doc.photos_json) or []
    return {"name": doc.name, "title": doc.title, "stage": doc.stage, "image": doc.ref_image or "",
            "colors": colors, "slots": list(RAW_SLOTS), "photos": photos,
            "missing": _missing(colors, photos), "specs": doc.specs or "",
            "hoursLeft": _hours_left(doc.stage_at, "photos") if doc.stage == "photos" else None,
            "canEdit": doc.stage == "photos", "samples": _samples(variants),
            "sizes": [x for x in dict.fromkeys(v.get("sizeLabel") for v in variants) if x]}


@frappe.whitelist(methods=["POST"])
def photo_add(name, color="", slot="front"):
    """One in-house photo for a colour × angle; a retake replaces the old one.
    'extra' adds an optional photo (up to ten)."""
    _gate_photo()
    content, ext = _read_upload()
    doc = _lock_product(name)
    if doc.stage != "photos":
        frappe.throw("This product is not waiting for in-house photos.")
    colors = _colors(_loads(doc.variants_json) or [])
    color = (color or "").upper()
    if color not in [c["code"] for c in colors]:
        frappe.throw(f"Unknown colour {color}.")
    if slot not in RAW_SLOTS + (EXTRA_SLOT,):
        frappe.throw("Unknown angle.")
    photos = _loads(doc.photos_json) or []
    replaced = []
    if slot == EXTRA_SLOT:
        if len([p for p in photos if p.get("slot") == EXTRA_SLOT]) >= MAX_EXTRAS:
            frappe.throw(f"{MAX_EXTRAS} extra photos at most.")
    else:
        keep = []
        for p in photos:
            if (p.get("color") or "") == color and p.get("slot") == slot:
                replaced.append(p["url"])
            else:
                keep.append(p)
        photos = keep
    fdoc = _insert_file("raw", DT_PRODUCT, doc.name, content, ext)
    photos.append({"url": fdoc.file_url, "color": color, "slot": slot,
                   "by": _user_name(frappe.session.user), "at": str(now_datetime())[:16]})
    doc.db_set("photos_json", json.dumps(photos, ensure_ascii=False), update_modified=False)
    _drop_files(doc.name, replaced)
    frappe.db.commit()
    return {"photos": photos, "missing": _missing(colors, photos)}


@frappe.whitelist(methods=["POST"])
def photo_remove(name, url, which="raw"):
    """Take one photo off the card: an in-house one while it is being shot,
    a final while marketing works on it."""
    if which == "final":
        _gate_studio()
    else:
        _gate_photo()
    doc = _lock_product(name)
    if doc.stage != ("studio" if which == "final" else "photos"):
        frappe.throw("This product is no longer at that step.")
    field = "finals_json" if which == "final" else "photos_json"
    rows = _loads(doc.get(field)) or []
    keep = [p for p in rows if p.get("url") != url]
    if len(keep) == len(rows):
        frappe.throw("Photo not found on this product.")
    doc.db_set(field, json.dumps(keep, ensure_ascii=False), update_modified=False)
    _drop_files(doc.name, [url])
    frappe.db.commit()
    colors = _colors(_loads(doc.variants_json) or [])
    return {"photos": keep, "missing": _missing(colors, keep) if which != "final" else []}


@frappe.whitelist(methods=["POST"])
def photos_send(name, specs=""):
    """In-house photos done → marketing's queue."""
    _gate_photo()
    doc = _lock_product(name)
    if doc.stage != "photos":
        frappe.throw("This product is not waiting for in-house photos.")
    colors = _colors(_loads(doc.variants_json) or [])
    photos = _loads(doc.photos_json) or []
    miss = _missing(colors, photos)
    if miss:
        frappe.throw(f"{len(miss)} required photo(s) still missing.")
    specs = (specs or "").strip()[:1000]
    _set_stage(doc, "studio", specs=specs)
    doc.add_comment("Comment", f"Souk: {len(photos)} in-house photos by {_user_name(frappe.session.user)}"
                               + (f" · {specs}" if specs else "") + " · to marketing.")
    frappe.db.commit()
    from logistics_portal.api import souk_ai
    souk_ai.auto_start(doc.name)
    return {"ok": True}


@frappe.whitelist()
def raw_zip(name):
    """All in-house photos of a product in one download, named
    <sku>-<colour>-<angle>."""
    if not (_can_studio() or _can_photo()):
        frappe.throw("Not authorized.", frappe.PermissionError)
    import io
    import zipfile

    doc = frappe.get_doc(DT_PRODUCT, name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for i, p in enumerate(_loads(doc.photos_json) or []):
            fname = frappe.db.get_value("File", {"file_url": p.get("url")}, "name")
            if not fname:
                continue
            ext = (p.get("url") or "").rsplit(".", 1)[-1]
            z.writestr(f"{doc.name}-{p.get('color') or 'ALL'}-{p.get('slot')}-{i + 1}.{ext}",
                       frappe.get_doc("File", fname).get_content())
    frappe.local.response.filename = f"{doc.name}-raw.zip"
    frappe.local.response.filecontent = buf.getvalue()
    frappe.local.response.type = "download"


def _studio_detail(name):
    doc = frappe.get_doc(DT_PRODUCT, name)
    variants = _loads(doc.variants_json) or []
    colors = _colors(variants)
    finals = _loads(doc.finals_json) or []
    weights = {}
    codes = [v["itemCode"] for v in variants if v.get("itemCode")]
    if codes:
        for r in frappe.get_all("Item", filters={"name": ["in", codes]},
                                fields=["name", "weight_per_unit", "weight_uom"]):
            if flt(r.weight_per_unit):
                weights[r.name] = round(flt(r.weight_per_unit) * (1000 if (r.weight_uom or "").lower() in ("kg", "kilogram") else 1))
    tied = {f.get("color") for f in finals}
    return {
        "name": doc.name, "title": doc.title, "stage": doc.stage, "image": doc.ref_image or "",
        "category": doc.category, "brand": doc.brand, "age": _age_days(doc.stage_at),
        "hoursLeft": _hours_left(doc.stage_at, "studio") if doc.stage == "studio" else None,
        "colors": colors, "photos": _loads(doc.photos_json) or [], "finals": finals,
        "specs": doc.specs or "", "shopifyId": doc.shopify_product_id or "", "error": doc.error or "",
        "variants": [{"sku": v["sku"], "color": v.get("color") or "", "colorFr": v.get("colorFr") or "",
                      "size": v.get("sizeLabel") or "", "grams": weights.get(v.get("itemCode"))}
                     for v in variants],
        "samples": _samples(variants),
        # Only colours that really are colours need their own final.
        "colorsWithout": [c["code"] for c in colors if c["code"] and c["code"] not in tied]
        if len(colors) > 1 else [],
        "canEdit": doc.stage == "studio",
        "deadline": _deadline(doc),
        "ai": _ai_block(doc),
        "aiSet": _set_block(doc),
    }


def _set_block(doc):
    from logistics_portal.api import souk_set
    try:
        return souk_set.block(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], f"souk._set_block {doc.name}")
        return None


def _ai_block(doc):
    from logistics_portal.api import souk_ai
    try:
        return souk_ai.block(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], f"souk._ai_block {doc.name}")
        return None


@frappe.whitelist()
def studio_boot(name=None):
    _gate_studio()
    limit = cint((settings().get("stageDays") or {}).get("studio")) or 0
    rows = frappe.get_all(DT_PRODUCT, filters={"stage": "studio"},
                          fields=["name", "title", "stage_at", "ref_image", "variants_json", "photos_json"],
                          order_by="stage_at asc", limit=200)
    queue = []
    for r in rows:
        age = _age_days(r.stage_at)
        queue.append({"name": r.name, "title": r.title, "image": r.ref_image or "", "age": age,
                      "late": bool(limit and age > limit),
                      "colors": len(_colors(_loads(r.variants_json) or [])),
                      "raw": len(_loads(r.photos_json) or [])})
    sel = name or (queue[0]["name"] if queue else None)
    return {"queue": queue, "limit": limit,
            "detail": _studio_detail(sel) if sel and frappe.db.exists(DT_PRODUCT, sel) else None}


@frappe.whitelist(methods=["POST"])
def final_add(name, color=""):
    """One final photo; it goes to the end of the list."""
    _gate_studio()
    content, ext = _read_upload(max_mb=20)
    doc = _lock_product(name)
    if doc.stage != "studio":
        frappe.throw("This product is not waiting for its final photos.")
    color = (color or "").upper()
    if color and color not in [c["code"] for c in _colors(_loads(doc.variants_json) or [])]:
        frappe.throw(f"Unknown colour {color}.")
    finals = _loads(doc.finals_json) or []
    if len(finals) >= MAX_FINALS:
        frappe.throw(f"{MAX_FINALS} final photos at most.")
    fdoc = _insert_file("final", DT_PRODUCT, doc.name, content, ext)
    finals.append({"url": fdoc.file_url, "color": color, "by": _user_name(frappe.session.user),
                   "at": str(now_datetime())[:16]})
    doc.db_set("finals_json", json.dumps(finals, ensure_ascii=False), update_modified=False)
    frappe.db.commit()
    return _studio_detail(doc.name)


@frappe.whitelist(methods=["POST"])
def final_set(name, finals):
    """New order and colour ties: [{url, color}] — the same photos, nothing
    added or lost."""
    _gate_studio()
    want = json.loads(finals) if isinstance(finals, str) else (finals or [])
    doc = _lock_product(name)
    if doc.stage != "studio":
        frappe.throw("This product is not waiting for its final photos.")
    cur = {f["url"]: f for f in (_loads(doc.finals_json) or [])}
    if sorted(cur) != sorted(w.get("url") for w in want):
        frappe.throw("The photo list changed meanwhile — reload.")
    codes = [c["code"] for c in _colors(_loads(doc.variants_json) or [])]
    out = []
    for w in want:
        color = (w.get("color") or "").upper()
        if color and color not in codes:
            frappe.throw(f"Unknown colour {color}.")
        out.append({**cur[w["url"]], "color": color})
    doc.db_set("finals_json", json.dumps(out, ensure_ascii=False), update_modified=False)
    frappe.db.commit()
    return _studio_detail(doc.name)


@frappe.whitelist(methods=["POST"])
def studio_return(name, reason):
    """Marketing cannot work with the in-house photos: back to the floor."""
    _gate_studio()
    reason = (reason or "").strip()
    if not reason:
        frappe.throw("Say what is missing.")
    doc = _lock_product(name)
    if doc.stage != "studio":
        frappe.throw("This product is not with marketing.")
    from logistics_portal.api import souk_ai
    souk_ai.clear(doc)
    _set_stage(doc, "photos")
    doc.add_comment("Comment", f"Souk: sent back to in-house photos by {_user_name(frappe.session.user)} · {reason[:280]}")
    frappe.db.commit()
    return {"ok": True}


_PRODUCT_MEDIA = """
query($id: ID!) { product(id: $id) { media(first: 100) { nodes { id } } } }
"""
_FILES_UNLINK = """
mutation($files: [FileUpdateInput!]!) {
  fileUpdate(files: $files) { userErrors { field message } }
}
"""
_VARIANTS_MEDIA = """
mutation($pid: ID!, $media: [CreateMediaInput!], $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $pid, media: $media, variants: $variants) {
    userErrors { field message }
  }
}
"""


def _gql_errors(data, key):
    errs = ((data.get("data") or {}).get(key) or {}).get("userErrors") or []
    if errs:
        raise Exception("; ".join(f"{'.'.join(e.get('field') or [])}: {e.get('message')}" for e in errs)[:400])


def _media_ids(pid):
    from logistics_portal.api.catalog_hub.sync import shopify_graphql
    data = shopify_graphql(_PRODUCT_MEDIA, {"id": pid})
    prod = (data.get("data") or {}).get("product") or {}
    return [n["id"] for n in ((prod.get("media") or {}).get("nodes") or [])]


def _public_url(path):
    """The address Shopify fetches a file from. Behind the proxy get_url can
    say http and carry the bench port (JY101: https://admin.justyol.com:8000/…
    → every photo FAILED on Shopify); the site only answers https on 443."""
    from urllib.parse import urlsplit, urlunsplit

    from frappe.utils import get_url
    u = urlsplit(get_url(path))
    return urlunsplit(("https", u.hostname or "", u.path, u.query, ""))


def _push_finals(doc, finals, variants, colors):
    """Finals → the Draft's media, in order; each colour's first final → its
    variants' image. Returns the media ids we now own on the product."""
    from logistics_portal.api.catalog_hub.sync import shopify_graphql
    pid = f"gid://shopify/Product/{doc.shopify_product_id}"
    ours = set(_loads(doc.shopify_media) or [])
    before = _media_ids(pid)
    stale = [m for m in before if m in ours]
    if stale:
        # Unlinking a file from the product removes it from the gallery and
        # from any variant that used it.
        _gql_errors(shopify_graphql(_FILES_UNLINK, {"files": [{"id": m, "referencesToRemove": [pid]}
                                                               for m in stale]}), "fileUpdate")
        doc.db_set("shopify_media", "[]", update_modified=False)
        frappe.db.commit()
    fr = {c["code"]: c["fr"] for c in colors}
    media, first_of = [], {}
    for f in finals:
        src = _public_url(f["url"])
        alt = (doc.title or doc.name) + (f" - {fr.get(f['color'])}" if f.get("color") and fr.get(f["color"]) else "")
        media.append({"originalSource": src, "mediaContentType": "IMAGE", "alt": alt[:500]})
        if f.get("color"):
            first_of.setdefault(f["color"], src)
    vin = []
    for v in variants:
        if not v.get("variantId"):
            continue
        row = {"id": f"gid://shopify/ProductVariant/{v['variantId']}"}
        if first_of.get(v.get("color") or ""):
            row["mediaSrc"] = [first_of[v["color"]]]
        vin.append(row)
    if not vin:
        raise Exception("the Draft's variant ids are missing on the card")
    _gql_errors(shopify_graphql(_VARIANTS_MEDIA, {"pid": pid, "media": media, "variants": vin}),
                "productVariantsBulkUpdate")
    keep = set(before) - set(stale)
    return [m for m in _media_ids(pid) if m not in keep]


@frappe.whitelist(methods=["POST"])
def studio_send(name):
    """Finals done → onto the Shopify Draft → content's queue."""
    _gate_studio()
    doc = _lock_product(name)
    if doc.stage != "studio":
        frappe.throw("This product is not waiting for its final photos.")
    variants = _loads(doc.variants_json) or []
    colors = _colors(variants)
    finals = _loads(doc.finals_json) or []
    if not finals:
        frappe.throw("Upload the final photos first.")
    det = _studio_detail(doc.name)
    if det["colorsWithout"]:
        frappe.throw("Every colour needs at least one final photo: " + ", ".join(det["colorsWithout"]))
    if not doc.shopify_product_id:
        frappe.throw("This product has no Shopify Draft.")
    try:
        mine = _push_finals(doc, finals, variants, colors)
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback()[:3000], f"souk.studio_send {name}")
        frappe.db.set_value(DT_PRODUCT, name, "error", f"Shopify photos: {str(e)[:400]}", update_modified=False)
        frappe.db.commit()
        frappe.throw(f"Shopify did not take the photos: {str(e)[:300]}")
    from logistics_portal.api import souk_ai
    souk_ai.clear(doc)
    _set_stage(doc, "content", shopify_media=json.dumps(mine), error="")
    doc.add_comment("Comment", f"Souk: {len(finals)} final photos on the Shopify Draft by "
                               f"{_user_name(frappe.session.user)} · to content.")
    frappe.db.commit()
    return {"ok": True, "media": len(mine)}


# --- content, review, live -------------------------------------------------------
#
# Content (2 days): French first (the storefront's primary language), Arabic
# as the shop's translation, product type, collections, tags, the final price
# per variant, SEO. The specs from the buy and the floor come ready. Sending
# to review writes it all onto the Shopify Draft.
#
# Review (1 day, never by the writer): the system checks what it can measure
# (a photo per colour, price above the cost WITH transport, weights, Shopify's
# quantity = what ee pushes from Next, vendor = house brand, French colour
# names); the reviewer ticks what only an eye sees. Sending back goes to the
# responsible step with a note and is counted; "won't publish" drops the card.
#
# Live: published to the chosen channels (default: what the last published
# product uses), status ACTIVE, the studio samples back onto their shelf.

TITLE_MAX = 70
META_TITLE_MAX = 60
META_DESC_MAX = 160
MANUAL_CHECKS = ("photos", "text", "sizes", "arabic")
REJECT_TO = ("content", "studio", "photos")
DROP_WHY = ("return", "clearance")
_HANDLE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _can_content():
    return _role() in ("manager", "content", "marketing")


def _can_review():
    return _role() in ("manager", "content", "marketing")


def _gate_content():
    if not _can_content():
        frappe.throw("Not authorized to write souk content.", frappe.PermissionError)


def _gate_review():
    if not _can_review():
        frappe.throw("Not authorized to review souk products.", frappe.PermissionError)


def _shopify_admin_url(pid):
    if not pid:
        return ""
    shop = (frappe.db.get_single_value("Shopify Setting", "shopify_url") or "")
    shop = shop.replace("https://", "").replace("http://", "").split(".")[0]
    return f"https://admin.shopify.com/store/{shop}/products/{pid}" if shop else ""


def _gql():
    from logistics_portal.api.catalog_hub.sync import shopify_graphql
    return shopify_graphql


def _costs(doc, variants):
    """Per item: what we paid, and the cost WITH transport once the trip's
    transport is spread (the receipt row's valuation rate after the LCV)."""
    out = {v["itemCode"]: {"paid": flt(v.get("cost")), "landed": flt(v.get("cost")), "allocated": False}
           for v in variants if v.get("itemCode")}
    if not out:
        return out
    seen = set()
    for r in frappe.db.sql(
            """SELECT pri.item_code, pri.valuation_rate, pri.landed_cost_voucher_amount AS lcv
               FROM `tabPurchase Receipt Item` pri
               JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
               JOIN `tabPurchase Order` po ON po.name = pri.purchase_order
               WHERE (po.custom_souk_product = %s OR po.name = %s) AND pr.docstatus = 1 AND pri.item_code IN %s
               ORDER BY pr.posting_date DESC, pr.creation DESC""",
            (doc.name, doc.purchase_order or "-", tuple(out)), as_dict=True):
        if r.item_code in seen:
            continue
        seen.add(r.item_code)
        if flt(r.valuation_rate):
            out[r.item_code]["landed"] = flt(r.valuation_rate)
        out[r.item_code]["allocated"] = flt(r.lcv) > 0
    return out


def _next_qty(code, loc):
    """Exactly what ee pushes to Shopify for one item and location
    (ecommerce_integrations.shopify.inventory.get_total_stock_for_location)."""
    r = frappe.db.sql(
        """SELECT SUM(b.actual_qty - b.reserved_stock) FROM `tabBin` b
           WHERE b.item_code = %s AND b.warehouse IN (
               SELECT m.erpnext_warehouse FROM `tabShopify Warehouse Mapping` m
               WHERE m.shopify_location_id = %s)""", (code, str(loc)))
    return cint(r[0][0]) if r and r[0][0] is not None else 0


def _weights(variants):
    codes = [v["itemCode"] for v in variants if v.get("itemCode")]
    out = {}
    if codes:
        for r in frappe.get_all("Item", filters={"name": ["in", codes]},
                                fields=["name", "weight_per_unit", "weight_uom"]):
            if flt(r.weight_per_unit):
                out[r.name] = round(flt(r.weight_per_unit) * (1000 if (r.weight_uom or "").lower() in ("kg", "kilogram") else 1))
    return out


def _content_of(doc, variants):
    c = _loads(doc.content_json) or {}
    fr = c.get("fr") or {}
    ar = c.get("ar") or {}
    prices = c.get("prices") or {}
    for v in variants:
        prices.setdefault(v["sku"], flt(v.get("price")))
    return {
        "fr": {"title": fr.get("title") if fr.get("title") is not None else (doc.title or ""),
               "description": fr.get("description") or ""},
        "ar": {"title": ar.get("title") or "", "description": ar.get("description") or ""},
        "productType": c.get("productType") if c.get("productType") is not None else (doc.product_type or ""),
        "collections": c.get("collections") or [], "tags": c.get("tags") or [],
        "handle": c.get("handle") or "", "metaTitle": c.get("metaTitle") or "",
        "metaDescription": c.get("metaDescription") or "", "prices": prices,
        "pushed": c.get("pushed") or {},
    }


def _content_checks(c, variants, costs):
    below = [v["sku"] for v in variants
             if flt(c["prices"].get(v["sku"])) <= flt((costs.get(v.get("itemCode")) or {}).get("landed"))]
    return [
        {"key": "frTitle", "ok": bool(c["fr"]["title"].strip()) and len(c["fr"]["title"]) <= TITLE_MAX},
        {"key": "frDesc", "ok": len(c["fr"]["description"].strip()) >= 40},
        # A warning, as the design has it: the French page sells; the Arabic
        # one is wanted, and review sees it missing.
        {"key": "arText", "soft": True, "ok": bool(c["ar"]["title"].strip() and c["ar"]["description"].strip())},
        {"key": "prices", "ok": not below, "detail": ", ".join(below)},
        {"key": "collection", "ok": len(c["collections"]) >= 1},
        {"key": "seo", "ok": bool(c["metaTitle"].strip()) and len(c["metaTitle"]) <= META_TITLE_MAX
            and bool(c["metaDescription"].strip()) and len(c["metaDescription"]) <= META_DESC_MAX
            and bool(_HANDLE_RE.match(c["handle"] or ""))},
    ]


def _desc_html(text):
    """Plain text from the portal → the storefront's HTML: lines starting
    with •, - or * become a list, the rest paragraphs. Everything escaped."""
    from html import escape
    out, items = [], []

    def flush():
        if items:
            out.append("<ul>" + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>")
            items.clear()

    for line in (text or "").splitlines():
        t = line.strip()
        if not t:
            flush()
            continue
        if t[:1] in ("•", "-", "*"):
            items.append(t[1:].strip())
            continue
        flush()
        out.append(f"<p>{escape(t)}</p>")
    flush()
    return "".join(out)


_COLLECTIONS_Q = """
query($after: String) {
  collections(first: 250, after: $after, query: "collection_type:custom") {
    nodes { id title handle } pageInfo { hasNextPage endCursor }
  }
}
"""


def _collections():
    """Shopify's manual collections (a smart one fills itself from its rules)."""
    key = "lp_souk_collections2"     # 2: with the handle, searched too
    hit = frappe.cache().get_value(key)
    if hit:
        return hit
    out, after = [], None
    for _i in range(8):
        con = ((_gql()(_COLLECTIONS_Q, {"after": after}).get("data") or {}).get("collections") or {})
        out += [{"id": n["id"], "title": n["title"], "handle": n.get("handle") or ""} for n in (con.get("nodes") or [])]
        pi = con.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        after = pi.get("endCursor")
    out.sort(key=lambda x: (x["title"] or "").lower())
    frappe.cache().set_value(key, out, expires_in_sec=3600)
    return out


def _stock_split(variants):
    """Pieces on sellable (Shopify-mapped) shelves vs in the studio."""
    codes = [v["itemCode"] for v in variants if v.get("itemCode")]
    if not codes:
        return 0, 0
    r = frappe.db.sql(
        """SELECT
             SUM(CASE WHEN b.warehouse IN (SELECT erpnext_warehouse FROM `tabShopify Warehouse Mapping`)
                      THEN b.actual_qty ELSE 0 END),
             SUM(CASE WHEN b.warehouse = %s THEN b.actual_qty ELSE 0 END)
           FROM `tabBin` b WHERE b.item_code IN %s""", (STUDIO_WH, tuple(codes)))
    return cint(r[0][0]), cint(r[0][1])


def _content_detail(name, with_collections=True):
    doc = frappe.get_doc(DT_PRODUCT, name)
    variants = _loads(doc.variants_json) or []
    c = _content_of(doc, variants)
    costs = _costs(doc, variants)
    grams = _weights(variants)
    shelf, studio = _stock_split(variants)
    cols, cols_err = [], ""
    if with_collections:
        try:
            cols = _collections()
        except Exception as e:
            cols_err = str(e)[:300]
    return {
        "name": doc.name, "title": doc.title, "stage": doc.stage, "image": doc.ref_image or "",
        "brand": doc.brand, "stall": doc.supplier, "category": doc.category, "specs": doc.specs or "",
        "finals": _loads(doc.finals_json) or [], "colors": _colors(variants),
        "variants": [{"sku": v["sku"], "itemCode": v.get("itemCode"), "color": v.get("color") or "",
                      "colorFr": v.get("colorFr") or "", "size": v.get("sizeLabel") or "",
                      "grams": grams.get(v.get("itemCode")), **(costs.get(v.get("itemCode")) or {})}
                     for v in variants],
        "content": c, "checks": _content_checks(c, variants, costs),
        "stock": {"shelf": shelf, "studio": studio},
        "collections": cols, "collectionsError": cols_err,
        "canEdit": doc.stage == "content",
        "hoursLeft": _hours_left(doc.stage_at, doc.stage) if doc.stage in ("content", "review") else None,
        "rejects": cint(doc.reject_count), "reviewNote": doc.review_note or "",
        "shopifyAdmin": _shopify_admin_url(doc.shopify_product_id),
        "productTypes": _product_types(c.get("productType")),
        "writer": _user_name(doc.content_by), "deadline": _deadline(doc), "age": _age_days(doc.stage_at),
        "write": _write_block(doc.name) if doc.stage == "content" else None,
    }


def _write_block(name):
    from logistics_portal.api import souk_write
    try:
        return souk_write.block(name)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], f"souk._write_block {name}")
        return None


def _product_types(current=""):
    out = []
    for c in settings().get("categories") or []:
        t = (c.get("productType") or "").strip()
        if t and t not in out:
            out.append(t)
    if current and current not in out:
        out.append(current)
    return out


def _deadline(doc):
    days = cint((settings().get("stageDays") or {}).get(doc.stage)) or 0
    if not days or not doc.stage_at:
        return ""
    return str(add_days(get_datetime(doc.stage_at), days))[:16]


def _queue(stage):
    limit = cint((settings().get("stageDays") or {}).get(stage)) or 0
    out = []
    for r in frappe.get_all(DT_PRODUCT, filters={"stage": stage},
                            fields=["name", "title", "stage_at", "ref_image", "finals_json", "reject_count",
                                    "content_by"],
                            order_by="stage_at asc", limit=200):
        finals = _loads(r.finals_json) or []
        age = _age_days(r.stage_at)
        out.append({"name": r.name, "title": r.title, "age": age, "late": bool(limit and age > limit),
                    "image": (finals[0]["url"] if finals else "") or r.ref_image or "",
                    "rejects": cint(r.reject_count), "writer": _user_name(r.content_by),
                    "mine": r.content_by == frappe.session.user})
    return out, limit


@frappe.whitelist()
def content_boot(name=None):
    _gate_content()
    queue, limit = _queue("content")
    sel = name or (queue[0]["name"] if queue else None)
    return {"queue": queue, "limit": limit,
            "detail": _content_detail(sel) if sel and frappe.db.exists(DT_PRODUCT, sel) else None}


def _clean_content(raw, variants):
    def txt(x, n):
        return str(x or "").strip()[:n]

    fr = raw.get("fr") or {}
    ar = raw.get("ar") or {}
    cols = [str(x) for x in (raw.get("collections") or []) if str(x).startswith("gid://shopify/Collection/")][:20]
    tags = []
    for t in raw.get("tags") or []:
        t = txt(t, 40)
        if t and t not in tags:
            tags.append(t)
    prices = {}
    given = raw.get("prices") or {}
    for v in variants:
        p = flt(given.get(v["sku"]))
        if p <= 0:
            frappe.throw(f"Price missing for {v['sku']}.")
        prices[v["sku"]] = round(p, 2)
    handle = re.sub(r"[^a-z0-9-]+", "-", txt(raw.get("handle"), 200).lower()).strip("-")
    handle = re.sub(r"-{2,}", "-", handle)
    return {"fr": {"title": txt(fr.get("title"), 255), "description": txt(fr.get("description"), 6000)},
            "ar": {"title": txt(ar.get("title"), 255), "description": txt(ar.get("description"), 6000)},
            "productType": txt(raw.get("productType"), 120), "collections": cols, "tags": tags[:20],
            "handle": handle, "metaTitle": txt(raw.get("metaTitle"), 120),
            "metaDescription": txt(raw.get("metaDescription"), 320), "prices": prices}


@frappe.whitelist()
def content_draft(name):
    """A first draft from what the cycle already knows — the buyer's name for
    it, the category, the colours and sizes, the floor's measurements. No AI:
    nothing leaves the server. The screen fills only the fields still empty."""
    _gate_content()
    doc = frappe.get_doc(DT_PRODUCT, name)
    variants = _loads(doc.variants_json) or []
    s = settings()
    cat = next((c for c in s.get("categories") or [] if c.get("key") == doc.category), {}) or {}
    cmap = {c["code"]: c for c in s.get("colors") or []}
    title = re.sub(r"\s+", " ", doc.title or "").strip()
    title = title[:1].upper() + title[1:]
    cols = [x for x in dict.fromkeys(v.get("color") for v in variants) if x]
    sizes = [x for x in dict.fromkeys(v.get("sizeLabel") for v in variants) if x]
    fr_cols = [cmap.get(c, {}).get("fr") or c for c in cols]
    ar_cols = [cmap.get(c, {}).get("ar") or c for c in cols]
    specs = [ln.strip(" -•\t") for ln in (doc.specs or "").splitlines() if ln.strip(" -•\t")]
    fr = [f"{title}."]
    if specs:
        fr.append("\n".join(f"• {x}" for x in specs))
    if fr_cols:
        fr.append(("Couleurs disponibles : " if len(fr_cols) > 1 else "Couleur : ") + ", ".join(fr_cols) + ".")
    if sizes:
        fr.append(("Tailles : " if len(sizes) > 1 else "Taille : ") + ", ".join(sizes) + ".")
    fr.append("Livraison partout au Maroc · paiement à la livraison.")
    ar = []
    if cat.get("ar"):
        ar.append(f"{cat['ar']} — {title}")
    if specs:
        ar.append("\n".join(f"• {x}" for x in specs))
    if ar_cols:
        ar.append("الألوان المتوفرة: " + "، ".join(ar_cols))
    if sizes:
        ar.append("المقاسات: " + "، ".join(sizes))
    ar.append("التوصيل لجميع مدن المغرب · الدفع عند الاستلام")
    fr_desc = "\n\n".join(fr)
    tags = [x for x in dict.fromkeys(["souk", cat.get("fr") or doc.category, doc.brand] + fr_cols) if x]
    handle = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", frappe.scrub(title).replace("_", "-").lower())).strip("-")
    return {
        "fr": {"title": title[:TITLE_MAX], "description": fr_desc},
        "ar": {"title": "", "description": "\n\n".join(ar)},
        "tags": tags[:20], "productType": cat.get("productType") or doc.product_type or "",
        "handle": f"{handle}-{doc.name.lower()}"[:200],
        "metaTitle": f"{title} | {doc.brand}"[:META_TITLE_MAX] if doc.brand else title[:META_TITLE_MAX],
        "metaDescription": re.sub(r"\s+", " ", fr_desc.replace("•", ""))[:META_DESC_MAX].strip(),
    }


@frappe.whitelist(methods=["POST"])
def content_save(name, content):
    _gate_content()
    raw = json.loads(content) if isinstance(content, str) else (content or {})
    doc = _lock_product(name)
    if doc.stage != "content":
        frappe.throw("This product is not waiting for its content.")
    variants = _loads(doc.variants_json) or []
    c = _clean_content(raw, variants)
    c["pushed"] = (_loads(doc.content_json) or {}).get("pushed") or {}
    doc.db_set("content_json", json.dumps(c, ensure_ascii=False), update_modified=False)
    frappe.db.commit()
    return _content_detail(doc.name, with_collections=False)


_PRODUCT_UPDATE = """
mutation($product: ProductUpdateInput!) {
  productUpdate(product: $product) { product { id handle } userErrors { field message } }
}
"""
_VARIANT_PRICES = """
mutation($pid: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $pid, variants: $variants) { userErrors { field message } }
}
"""
_TRANSLATABLE = """
query($id: ID!) { translatableResource(resourceId: $id) { translatableContent { key digest } } }
"""
_TRANSLATE = """
mutation($id: ID!, $t: [TranslationInput!]!) {
  translationsRegister(resourceId: $id, translations: $t) { userErrors { field message } }
}
"""


def _push_arabic(pid, c):
    data = _gql()(_TRANSLATABLE, {"id": pid})
    digest = {x["key"]: x["digest"] for x in
              ((((data.get("data") or {}).get("translatableResource") or {}).get("translatableContent")) or [])}
    vals = {"title": c["ar"]["title"], "body_html": _desc_html(c["ar"]["description"])}
    t = [{"key": k, "value": v, "locale": "ar", "translatableContentDigest": digest[k]}
         for k, v in vals.items() if v and digest.get(k)]
    if not t:
        raise Exception("Shopify offered nothing to translate")
    _gql_errors(_gql()(_TRANSLATE, {"id": pid, "t": t}), "translationsRegister")


def _push_content(doc, c, variants):
    """The content onto the Shopify Draft (still DRAFT: nobody sees it)."""
    pid = f"gid://shopify/Product/{doc.shopify_product_id}"
    joined = set(_loads(doc.shopify_collections) or [])
    want = set(c["collections"])
    tags = []
    for t in ["souk", doc.sku_base] + ([f"souk-trip-{doc.trip}"] if doc.trip else []) + c["tags"]:
        if t and t not in tags:
            tags.append(t)
    prod = {"id": pid, "title": c["fr"]["title"], "descriptionHtml": _desc_html(c["fr"]["description"]),
            "productType": c["productType"] or doc.product_type or "", "tags": tags,
            "seo": {"title": c["metaTitle"], "description": c["metaDescription"]}}
    if c["handle"]:
        prod["handle"] = c["handle"]
    if want - joined:
        prod["collectionsToJoin"] = sorted(want - joined)
    if joined - want:
        prod["collectionsToLeave"] = sorted(joined - want)
    data = _gql()(_PRODUCT_UPDATE, {"product": prod})
    _gql_errors(data, "productUpdate")
    handle = ((((data.get("data") or {}).get("productUpdate") or {}).get("product")) or {}).get("handle")
    doc.db_set("shopify_collections", json.dumps(sorted(want)), update_modified=False)
    vin = [{"id": f"gid://shopify/ProductVariant/{v['variantId']}", "price": str(c["prices"][v["sku"]])}
           for v in variants if v.get("variantId")]
    if vin:
        _gql_errors(_gql()(_VARIANT_PRICES, {"pid": pid, "variants": vin}), "productVariantsBulkUpdate")
    try:
        _push_arabic(pid, c)
        arabic = {"ok": True, "error": ""}
    except Exception as e:
        # The French page stands on its own; review sees the Arabic gap.
        arabic = {"ok": False, "error": str(e)[:300]}
    return handle, arabic


@frappe.whitelist(methods=["POST"])
def content_send(name):
    """Content done → onto the Shopify Draft → review."""
    _gate_content()
    doc = _lock_product(name)
    if doc.stage != "content":
        frappe.throw("This product is not waiting for its content.")
    variants = _loads(doc.variants_json) or []
    c = _content_of(doc, variants)
    failed = [x["key"] for x in _content_checks(c, variants, _costs(doc, variants))
              if not x["ok"] and not x.get("soft")]
    if failed:
        frappe.throw("Not complete yet: " + ", ".join(failed))
    if not doc.shopify_product_id:
        frappe.throw("This product has no Shopify Draft.")
    try:
        handle, arabic = _push_content(doc, c, variants)
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback()[:3000], f"souk.content_send {name}")
        frappe.db.set_value(DT_PRODUCT, name, "error", f"Shopify content: {str(e)[:400]}", update_modified=False)
        frappe.db.commit()
        frappe.throw(f"Shopify did not take the content: {str(e)[:300]}")
    c["pushed"] = {"at": str(now_datetime())[:16], "handle": handle or c["handle"], "arabic": arabic}
    if handle:
        c["handle"] = handle
    for v in variants:
        v["price"] = c["prices"][v["sku"]]
    _set_stage(doc, "review", content_json=json.dumps(c, ensure_ascii=False),
               variants_json=json.dumps(variants, ensure_ascii=False),
               title=c["fr"]["title"], content_by=frappe.session.user, content_at=now_datetime(), error="")
    doc.add_comment("Comment", f"Souk: content on the Shopify Draft by {_user_name(frappe.session.user)}"
                               + ("" if arabic["ok"] else f" · Arabic NOT on Shopify ({arabic['error'][:120]})")
                               + " · to review.")
    frappe.db.commit()
    return {"ok": True, "arabic": arabic}


_SHOPIFY_STATE = """
query($id: ID!, $loc: ID!) {
  product(id: $id) {
    status vendor onlineStorePreviewUrl
    options { name optionValues { name } }
    media(first: 100) { nodes { status } }
    variants(first: 100) { nodes { id sku price
      inventoryItem { inventoryLevel(locationId: $loc) { quantities(names: ["available"]) { name quantity } } } } }
  }
  translatableResource(resourceId: $id) { translations(locale: "ar") { key } }
}
"""
_PUBLICATIONS = """
{ publications(first: 30) { nodes { id catalog { title } app { title } } } }
"""
_LAST_PUBLISHED = """
{ products(first: 1, sortKey: CREATED_AT, reverse: true, query: "status:active") {
    nodes { resourcePublications(first: 30, onlyPublished: true) { nodes { publication { id } } } } } }
"""
_PUBLISH = """
mutation($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) { userErrors { field message } }
}
"""


def _channels():
    """Sales channels + the default ticks (the last publish's, else what the
    newest active product on Shopify is published to)."""
    key = "lp_souk_publications_v2"
    pubs = frappe.cache().get_value(key)
    if not pubs:
        nodes = (((_gql()(_PUBLICATIONS).get("data") or {}).get("publications") or {}).get("nodes")) or []
        pubs = []
        for n in nodes:
            # The ee token gets catalog = null (no catalog scope); the app's
            # title ("Online Store", "TikTok") is what the team calls it.
            title = ((n.get("catalog") or {}).get("title")) or ""
            m = re.search(r" for (.+)$", title)
            app = ((n.get("app") or {}).get("title")) or ""
            pubs.append({"id": n["id"], "name": app or (m.group(1) if m else (title or n["id"].rsplit("/", 1)[-1]))})
        frappe.cache().set_value(key, pubs, expires_in_sec=3600)
    ids = {p["id"] for p in pubs}
    chosen = [c for c in (settings().get("publishChannels") or []) if c in ids]
    if not chosen:
        try:
            prods = (((_gql()(_LAST_PUBLISHED).get("data") or {}).get("products") or {}).get("nodes")) or []
            if prods:
                chosen = [x["publication"]["id"] for x in
                          ((prods[0].get("resourcePublications") or {}).get("nodes") or [])
                          if x["publication"]["id"] in ids]
        except Exception:
            chosen = []
    return pubs, chosen or sorted(ids)


def _review_checks(doc, variants, c, costs):
    """What the system can measure. hard = blocks the publish."""
    checks = []
    colors = _colors(variants)
    finals = _loads(doc.finals_json) or []
    tied = {f.get("color") for f in finals}
    need = [x["code"] for x in colors if x["code"]] if len(colors) > 1 else []
    have = [x for x in need if x in tied]
    checks.append({"key": "colorPhotos", "hard": True, "ok": bool(finals) and len(have) == len(need),
                   "detail": f"{len(have)}/{len(need)}" if need else str(len(finals))})
    margins, low = [], []
    allocated = True
    for v in variants:
        k = costs.get(v.get("itemCode")) or {}
        landed = flt(k.get("landed"))
        price = flt(c["prices"].get(v["sku"]))
        allocated = allocated and bool(k.get("allocated"))
        if price <= landed:
            low.append(v["sku"])
        elif price:
            margins.append((price - landed) / price * 100)
    checks.append({"key": "margin", "hard": True, "ok": not low,
                   "detail": ", ".join(low) if low else (f"{round(min(margins))}%" if margins else "")})
    checks.append({"key": "transport", "hard": False, "ok": allocated})
    grams = _weights(variants)
    w = len([v for v in variants if grams.get(v.get("itemCode"))])
    checks.append({"key": "weights", "hard": True, "ok": w == len(variants), "detail": f"{w}/{len(variants)}"})
    checks.append({"key": "supplier", "hard": True,
                   "ok": bool(doc.supplier and frappe.db.exists("Supplier", doc.supplier)), "detail": doc.supplier or ""})

    loc = _shopify_location()
    try:
        data = _gql()(_SHOPIFY_STATE, {"id": f"gid://shopify/Product/{doc.shopify_product_id}",
                                       "loc": f"gid://shopify/Location/{loc}"})
    except Exception as e:
        checks.append({"key": "shopify", "hard": True, "ok": False, "detail": str(e)[:200]})
        return checks, {}
    prod = (data.get("data") or {}).get("product") or {}
    if not prod:
        checks.append({"key": "shopify", "hard": True, "ok": False, "detail": "product not found"})
        return checks, {}
    by_id = {}
    for n in ((prod.get("variants") or {}).get("nodes") or []):
        lvl = ((n.get("inventoryItem") or {}).get("inventoryLevel") or {})
        q = 0
        for x in (lvl.get("quantities") or []):
            if x.get("name") == "available":
                q = cint(x.get("quantity"))
        by_id[n["id"].rsplit("/", 1)[-1]] = {"sku": n.get("sku"), "price": flt(n.get("price")), "qty": q}
    off, rows = [], []
    for v in variants:
        sv = by_id.get(str(v.get("variantId") or "")) or {}
        nq = _next_qty(v.get("itemCode"), loc) if v.get("itemCode") else 0
        rows.append({"sku": v["sku"], "shopify": sv.get("qty", 0), "next": nq})
        if not sv or sv.get("qty", 0) != nq:
            off.append(f"{v['sku']} {sv.get('qty', 0)}≠{nq}")
    tot_s = sum(r["shopify"] for r in rows)
    tot_n = sum(r["next"] for r in rows)
    checks.append({"key": "qty", "hard": True, "ok": not off,
                   "detail": "; ".join(off) if off else f"{tot_s} = {tot_n}"})
    st = [n.get("status") for n in ((prod.get("media") or {}).get("nodes") or [])]
    bad = st.count("FAILED")
    waiting = len([x for x in st if x in ("UPLOADED", "PROCESSING")])
    checks.append({"key": "shopifyPhotos", "hard": True, "ok": bool(st) and not bad and not waiting,
                   "detail": (f"{bad} failed" if bad else f"{waiting} processing" if waiting else str(len(st)))})
    checks.append({"key": "vendor", "hard": True, "ok": (prod.get("vendor") or "") == (doc.brand or ""),
                   "detail": prod.get("vendor") or ""})
    if any(v.get("color") for v in variants):
        opt = next((o for o in (prod.get("options") or []) if o.get("name") == "Color"), None)
        got = sorted(x["name"] for x in ((opt or {}).get("optionValues") or []))
        want = sorted({v.get("colorFr") for v in variants if v.get("colorFr")})
        checks.append({"key": "frColors", "hard": True, "ok": got == want, "detail": " · ".join(got)})
    wrong = [v["sku"] for v in variants
             if abs((by_id.get(str(v.get("variantId") or "")) or {}).get("price", 0) - flt(c["prices"].get(v["sku"]))) > 0.009]
    checks.append({"key": "priceOnShopify", "hard": True, "ok": not wrong, "detail": ", ".join(wrong)})
    ar = {t["key"] for t in ((((data.get("data") or {}).get("translatableResource")) or {}).get("translations") or [])}
    checks.append({"key": "arabicOnShopify", "hard": False, "ok": "title" in ar and "body_html" in ar})
    return checks, {"preview": prod.get("onlineStorePreviewUrl") or "", "status": prod.get("status") or "",
                    "qty": rows}


def _review_detail(name):
    det = _content_detail(name, with_collections=False)
    doc = frappe.get_doc(DT_PRODUCT, name)
    variants = _loads(doc.variants_json) or []
    c = _content_of(doc, variants)
    costs = _costs(doc, variants)
    checks, shop = _review_checks(doc, variants, c, costs) if doc.stage == "review" else ([], {})
    try:
        pubs, chosen = _channels()
        pub_err = ""
    except Exception as e:
        pubs, chosen, pub_err = [], [], str(e)[:300]
    same = doc.content_by == frappe.session.user
    det.update({
        "checks": checks, "shopify": shop, "channels": pubs, "chosen": chosen, "channelsError": pub_err,
        "writer": _user_name(doc.content_by), "sameWriter": same, "manual": list(MANUAL_CHECKS),
        "descHtml": {"fr": _desc_html(c["fr"]["description"]), "ar": _desc_html(c["ar"]["description"])},
        "canPublish": doc.stage == "review" and not same,
        "samples": _samples(variants),
    })
    return det


@frappe.whitelist()
def review_boot(name=None):
    _gate_review()
    queue, limit = _queue("review")
    sel = name or next((q["name"] for q in queue if not q["mine"]), None) or (queue[0]["name"] if queue else None)
    return {"queue": queue, "limit": limit,
            "detail": _review_detail(sel) if sel and frappe.db.exists(DT_PRODUCT, sel) else None}


def _gate_not_writer(doc):
    if doc.content_by and doc.content_by == frappe.session.user:
        frappe.throw("You wrote this content — another person reviews it.")


@frappe.whitelist(methods=["POST"])
def review_reject(name, to, note):
    """Back to the step that owns the problem, with a note; counted."""
    _gate_review()
    note = (note or "").strip()
    if to not in REJECT_TO:
        frappe.throw("Unknown step.")
    if not note:
        frappe.throw("Write what is wrong.")
    doc = _lock_product(name)
    if doc.stage != "review":
        frappe.throw("This product is not in review.")
    _gate_not_writer(doc)
    _set_stage(doc, to, reject_count=cint(doc.reject_count) + 1, review_note=note[:500])
    doc.add_comment("Comment", f"Souk: review sent it back to {to} ({cint(doc.reject_count)}×) by "
                               f"{_user_name(frappe.session.user)} · {note[:280]}")
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def review_drop(name, why, note):
    """Won't be published: poor quality or does not photograph well. The
    goods go back to the stall or to clearance — decided here, done by hand.
    Review drops it at review; the manager can stop it at any stage."""
    if _role() != "manager":
        _gate_review()
    note = (note or "").strip()
    if why not in DROP_WHY:
        frappe.throw("Unknown reason.")
    if not note:
        frappe.throw("Write why.")
    doc = _lock_product(name)
    if doc.stage in ("live", "dropped"):
        frappe.throw("Only a card still in the cycle can be dropped.")
    if doc.stage == "buying":
        # Stuck before its PO (Shopify refused it, its items never came):
        # the manager takes it out so the rest of its basket and the custody
        # can move on. Nothing was ordered for it yet.
        if _role() != "manager":
            frappe.throw("Only the manager can stop a purchase that is still being saved.")
        if doc.purchase_order:
            frappe.throw("This purchase already has its PO; cancel the PO first.")
        if doc.shopify_product_id:
            try:
                _gql_errors(_gql()(_PRODUCT_UPDATE, {"product": {"id": f"gid://shopify/Product/{doc.shopify_product_id}",
                                                                 "status": "ARCHIVED"}}), "productUpdate")
            except Exception:
                frappe.log_error(frappe.get_traceback()[:2000], f"souk drop archive {doc.name}")
    if doc.stage != "review" and _role() != "manager":
        # Before review only the manager stops a product: the goods are
        # bought, and somebody has to own sending them back.
        frappe.throw("This product is not in review.")
    if doc.stage == "review":
        _gate_not_writer(doc)
    extra = {"dropped_from": doc.stage} if _has_col(DT_PRODUCT, "dropped_from") else {}
    _set_stage(doc, "dropped", review_note=f"{why}: {note[:480]}", **extra)
    doc.add_comment("Comment", f"Souk: will NOT be published ({'back to the stall' if why == 'return' else 'clearance'}) "
                               f"by {_user_name(frappe.session.user)} · {note[:280]}")
    frappe.db.commit()
    basket = (_loads(doc.get("pay_json")) or {}).get("basket") if _has_col(DT_PRODUCT, "pay_json") else None
    if basket and not doc.purchase_order:
        # The rest of its basket was waiting for this one: let it reach its PO.
        try:
            finish_basket(basket)
        except Exception:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback()[:2000], f"souk drop basket {basket}")
    return {"ok": True}


def _samples_home(doc, variants):
    """The studio samples back onto the shelf holding most of that item."""
    st = _studio_stock(variants)
    if not st:
        return None, 0
    shelves = set(_shelves())
    items, skipped = [], []
    for v in variants:
        code = v.get("itemCode")
        q = cint(st.get(code))
        if not q:
            continue
        dest = None
        for (wh,) in frappe.db.sql("""SELECT warehouse FROM `tabBin` WHERE item_code = %s AND actual_qty > 0
                                       ORDER BY actual_qty DESC""", (code,)):
            if wh in shelves:
                dest = wh
                break
        if not dest:
            skipped.append(v["sku"])
            continue
        items.append({"item_code": code, "qty": q, "s_warehouse": STUDIO_WH, "t_warehouse": dest})
    if skipped:
        doc.add_comment("Comment", "Souk: samples left in the studio (no shelf holds this item): " + ", ".join(skipped))
    if not items:
        return None, 0
    se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Transfer", "company": COMPANY,
                         "remarks": f"Souk {doc.name}: studio samples back on the shelf at publish", "items": items})
    se.flags.ignore_permissions = True
    se.insert(ignore_permissions=True)
    se.submit()
    try:
        from logistics_portal.api.labelprint import queue_items
        queue_items([(i["item_code"], i["qty"]) for i in items], LABEL_STATION)
    except Exception:
        pass
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return se.name, sum(i["qty"] for i in items)


@frappe.whitelist(methods=["POST"])
def publish(name, channels, manual):
    """Review passed → published to the chosen channels → ACTIVE → samples
    back on the shelf."""
    _gate_review()
    channels = json.loads(channels) if isinstance(channels, str) else (channels or [])
    manual = json.loads(manual) if isinstance(manual, str) else (manual or [])
    doc = _lock_product(name)
    if doc.stage != "review":
        frappe.throw("This product is not in review.")
    _gate_not_writer(doc)
    if sorted(set(manual)) != sorted(MANUAL_CHECKS):
        frappe.throw("Tick every eye check first.")
    variants = _loads(doc.variants_json) or []
    c = _content_of(doc, variants)
    checks, _shop = _review_checks(doc, variants, c, _costs(doc, variants))
    failed = [x["key"] for x in checks if x.get("hard") and not x["ok"]]
    if failed:
        frappe.throw("System checks failing: " + ", ".join(failed))
    pubs, _chosen = _channels()
    ids = {p["id"] for p in pubs}
    channels = [x for x in channels if x in ids]
    if not channels:
        frappe.throw("Choose at least one sales channel.")
    pid = f"gid://shopify/Product/{doc.shopify_product_id}"
    try:
        _gql_errors(_gql()(_PUBLISH, {"id": pid, "input": [{"publicationId": x} for x in channels]}),
                    "publishablePublish")
        _gql_errors(_gql()(_PRODUCT_UPDATE, {"product": {"id": pid, "status": "ACTIVE"}}), "productUpdate")
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback()[:3000], f"souk.publish {name}")
        frappe.db.set_value(DT_PRODUCT, name, "error", f"Shopify publish: {str(e)[:400]}", update_modified=False)
        frappe.db.commit()
        frappe.throw(f"Shopify did not publish it: {str(e)[:300]}")
    cur = settings()
    cur["publishChannels"] = channels
    frappe.db.set_default(SETTINGS_KEY, json.dumps(cur, ensure_ascii=False))
    _set_stage(doc, "live", reviewed_by=frappe.session.user, published_at=now_datetime(),
               error="", review_note="")
    names = {p["id"]: p["name"] for p in pubs}
    doc.add_comment("Comment", f"Souk: LIVE by {_user_name(frappe.session.user)} on "
                               + ", ".join(names.get(x, x) for x in channels) + ".")
    frappe.db.commit()
    moved, se = 0, None
    try:
        se, moved = _samples_home(doc, variants)
        if se:
            doc.add_comment("Comment", f"Souk: {moved} studio sample(s) back on the shelf · {se}.")
        frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback()[:3000], f"souk.publish samples {name}")
        doc.add_comment("Comment", f"Souk: samples still in the studio — move them by hand ({str(e)[:160]}).")
        frappe.db.commit()
    return {"ok": True, "samples": moved, "stockEntry": se or "", "channels": len(channels)}


@frappe.whitelist(methods=["POST"])
def qty_nudge(name):
    """Shopify's quantity differs from Next: mark the items so ee's next
    inventory run (every few minutes) pushes them again."""
    _gate_review()
    doc = frappe.get_doc(DT_PRODUCT, name)
    codes = [v["itemCode"] for v in (_loads(doc.variants_json) or []) if v.get("itemCode")]
    if codes:
        frappe.db.sql("""UPDATE `tabEcommerce Item` SET inventory_synced_on = '2000-01-01 00:00:00'
                         WHERE integration = 'shopify' AND erpnext_item_code IN %s""", (tuple(codes),))
        frappe.db.commit()
    return {"ok": True, "items": len(codes)}


# --- late alerts ---------------------------------------------------------------
#
# A late card pages the people of its stage EVERY day it stays late. The
# floor alerts went silent once (alerts-silenced-by-unread): they deduped on
# "an unread row exists" at any age, so one unread bell muted a standing
# problem forever. Here the dedupe is the DAY: at most one row per person per
# day, read or not.

STAGE_OWNERS = {
    "bought": ("dispatcher",),            # receiving: the floor leads
    "photos": ("dispatcher",),            # in-house photos: the floor
    "studio": ("marketing",),             # finals
    "content": ("content", "marketing"),
    "review": ("content", "marketing"),
}


def _users_with(roles):
    return frappe.get_all("User", filters={"enabled": 1, "custom_logistics_role": ["in", list(roles)]},
                          pluck="name")


def run_late_alerts():
    """Daily: one bell per person with the souk cards late in their stage;
    the manager gets the escalations (past escalateDays since purchase)."""
    if not frappe.db.exists("DocType", DT_PRODUCT):
        return
    s = settings()
    days = s.get("stageDays") or {}
    fields = ["name", "title", "stage", "stage_at", "bought_at", "creation", "content_by"]
    if _has_col(DT_PRODUCT, "claimed_by"):
        fields.append("claimed_by")
    rows = frappe.get_all(DT_PRODUCT, filters={"stage": ["in", list(STAGE_OWNERS)]}, fields=fields,
                          limit_page_length=0)
    per_user = {}
    managers = _users_with(("manager",))
    for r in rows:
        limit = cint(days.get(r.stage)) or 0
        age = _age_days(r.stage_at)
        if not limit or age <= limit:
            continue
        who = [r.get("claimed_by")] if r.get("claimed_by") else _users_with(STAGE_OWNERS[r.stage])
        if r.stage == "review" and r.content_by:
            who = [u for u in who if u != r.content_by] or who
        # Nobody holds the stage's role yet (prod 2026-11-18: no marketing or
        # content user): the managers hear it rather than nobody.
        who = who or managers
        for u in who:
            per_user.setdefault(u, []).append(r)
        if _age_days(r.bought_at or r.creation) > cint(s.get("escalateDays") or 21):
            for u in managers:
                per_user.setdefault(u, []).append(r)
    today = nowdate()
    for user, cards in per_user.items():
        if frappe.db.sql("""SELECT 1 FROM `tabNotification Log` WHERE for_user = %s AND subject LIKE %s
                            AND creation >= %s LIMIT 1""", (user, "Souk:%late%", today + " 00:00:00")):
            continue
        seen, uniq = set(), []
        for c in cards:
            if c.name not in seen:
                seen.add(c.name)
                uniq.append(c)
        stages = sorted({c.stage for c in uniq})
        subject = (f"Souk: {len(uniq)} late in " + ", ".join(stages) + " · "
                   + ", ".join(c.name for c in uniq[:4]) + ("…" if len(uniq) > 4 else ""))
        body = "<br>".join(f"{c.name} · {frappe.utils.escape_html(c.title or '')} · {c.stage} "
                           f"{_age_days(c.stage_at)} d" for c in uniq[:30])
        try:
            frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert",
                            "subject": subject[:140], "email_content": body,
                            "document_type": DT_PRODUCT, "document_name": uniq[0].name}).insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback()[:2000], "souk.run_late_alerts")
    frappe.db.commit()
