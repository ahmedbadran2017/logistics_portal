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

The custody (العهدة): the accountant hands the buyer cash and opens the
trip; every purchase is deducted; at close the buyer hands back what is
left and the accountant counts it on the portal. A purchase with no
receipt carries a substitute (photo of the goods + the stall's phone) that
the accountant approves. If settings name a custody cash account, each
purchase also posts a PAID Purchase Invoice on it; until the accountant has
that account, the PO is the record and the books are his to post.

Storage follows the app's pattern: two custom doctypes created on migrate
(no fixture files), a few custom fields on Purchase Order, settings in
defaults.
"""

import json
import re

import frappe
from frappe.utils import cint, flt, now_datetime, nowdate, time_diff_in_hours

COMPANY = "Justyol Morocco"
DT_TRIP = "LP Souk Trip"
DT_PRODUCT = "LP Souk Product"
SETTINGS_KEY = "lp_souk_settings"
SUPPLIER_GROUP = "Souk Suppliers"
RECEIVING_WH = "Receiving Zone - JM"
MODE_OF_PAYMENT = "Cash MAD"
# A 13-character Code128B SKU on the 50 mm shelf label prints a ≈0.25 mm
# module — the smallest the floor scanners read (shelf-label work, 2026-10).
SKU_MAX = 13

STAGES = ["buying", "bought", "received", "photographed", "studio",
          "content", "review", "live", "dropped"]

DEFAULT_SETTINGS = {
    "skuPrefix": "SK",
    "skuStart": 100,
    "custodyAccount": "",          # empty = PO only, accountant books it
    "categories": [
        {"key": "kitchen", "ar": "مطبخ", "fr": "Cuisine", "productType": "Cuisine", "brand": "JHome"},
        {"key": "home", "ar": "ديكور وبيت", "fr": "Maison & Déco", "productType": "Maison", "brand": "JHome"},
        {"key": "storage", "ar": "تخزين وتنظيم", "fr": "Rangement", "productType": "Rangement", "brand": "JHome"},
        {"key": "women", "ar": "حريمي", "fr": "Femme", "productType": "Femme", "brand": "JWomen"},
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
        {"code": "GLD", "fr": "Doré", "ar": "دهبي"},
        {"code": "SLV", "fr": "Argenté", "ar": "فضي"},
        {"code": "NAT", "fr": "Naturel", "ar": "طبيعي"},
        {"code": "MLT", "fr": "Multicolore", "ar": "ملون"},
    ],
    # Days a card may sit in a stage before it is late (alerts repeat daily).
    "stageDays": {"bought": 2, "received": 1, "photographed": 3, "studio": 3,
                  "content": 2, "review": 1},
    "escalateDays": 21,
}


# --- schema ------------------------------------------------------------------

def ensure_doctype():
    """Create the two doctypes, the PO fields and the stall supplier group.
    Custom doctypes: live in the DB, no schema files, safe to run every time."""
    try:
        _ensure_trip()
        _ensure_product()
        _ensure_po_fields()
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
    ]}, ignore_validate=True)


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
    if _role() not in ("manager", "sourcing", "accountant") and not _is_accountant():
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


@frappe.whitelist(methods=["POST"])
def save_settings(settings_json):
    if _role() != "manager":
        frappe.throw("Managers only.", frappe.PermissionError)
    s = json.loads(settings_json or "{}")
    if not isinstance(s, dict):
        frappe.throw("Bad settings.")
    acct = (s.get("custodyAccount") or "").strip()
    if acct and frappe.db.get_value("Account", acct, "account_type") not in ("Cash", "Bank"):
        frappe.throw(f"{acct} is not a cash account.")
    cur = settings()
    cur.update({k: v for k, v in s.items() if k in DEFAULT_SETTINGS})
    frappe.db.set_default(SETTINGS_KEY, json.dumps(cur, ensure_ascii=False))
    frappe.db.commit()
    return cur


def _user_name(user):
    if not user:
        return ""
    return frappe.db.get_value("User", user, "full_name") or user.split("@")[0]


# --- custody (trips) ---------------------------------------------------------

def _trip_buys(trip):
    """Every PO bought on this trip, newest first (new products and buy-again)."""
    return frappe.db.sql(
        """SELECT po.name, po.supplier, po.grand_total, po.docstatus, po.creation,
                  po.custom_souk_product AS product, po.custom_souk_receipt AS receipt,
                  po.custom_souk_receipt_image AS receipt_image,
                  po.custom_souk_voucher_phone AS phone, po.custom_souk_voucher_ok AS voucher_ok,
                  (SELECT SUM(qty) FROM `tabPurchase Order Item` WHERE parent = po.name) AS units
           FROM `tabPurchase Order` po
           WHERE po.custom_souk_trip = %s AND po.docstatus = 1
           ORDER BY po.creation DESC""", (str(trip),), as_dict=True)


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
    pending = frappe.db.sql(
        """SELECT COALESCE(SUM(total_cost), 0) FROM `tab{dt}`
           WHERE trip = %s AND stage = 'buying' AND IFNULL(purchase_order, '') = ''""".format(dt=DT_PRODUCT),
        (str(t.name),))[0][0]
    goods += flt(pending)
    transport = flt(t.transport_cost)
    expected = flt(t.cash_given) - goods - transport
    titles = {}
    names = [b.product for b in buys if b.product]
    if names:
        for r in frappe.get_all(DT_PRODUCT, filters={"name": ["in", names]}, fields=["name", "title", "ref_image"]):
            titles[r.name] = r
    rows = []
    for b in buys:
        p = titles.get(b.product) or {}
        rows.append({
            "po": b.name, "supplier": b.supplier, "amount": flt(b.grand_total), "units": cint(b.units),
            "product": b.product or "", "title": p.get("title") or "", "image": p.get("ref_image") or "",
            "receipt": _receipt_state(b), "receiptImage": b.receipt_image or "", "phone": b.phone or "",
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
        "canClose": t.status == "Open" and not missing,
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
    return {
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
def set_voucher(po, phone):
    """No receipt from the stall: the substitute is a photo of the goods (the
    product's reference photo) + the stall's phone; the accountant approves."""
    po_doc = _souk_po(po)
    phone = re.sub(r"[^\d+]", "", phone or "")
    if len(phone) < 9:
        frappe.throw("Write the stall's phone number.")
    frappe.db.set_value("Purchase Order", po_doc.name, {
        "custom_souk_receipt": "voucher", "custom_souk_voucher_phone": phone,
        "custom_souk_voucher_ok": ""}, update_modified=False)
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
    d = frappe.db.get_value("Purchase Order", po, ["name", "custom_souk_trip", "custom_souk_receipt"], as_dict=True)
    if not d or not d.custom_souk_trip:
        frappe.throw("Not a souk purchase.")
    _trip_for_write(d.custom_souk_trip)
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

@frappe.whitelist(methods=["POST"])
def upload_photo(kind, target):
    """One photo from the phone. kind: ref (product reference photo), receipt
    (stall receipt on a PO or on a product still being created), transport
    (the trip's taxi receipt). Attached to its record."""
    _gate_view()
    f = (frappe.request.files or {}).get("file")
    if not f:
        frappe.throw("No photo.")
    content = f.stream.read()
    if len(content) > 12 * 1024 * 1024:
        frappe.throw("Photo too large (12 MB max).")
    if kind == "transport":
        t = _trip_for_write(target)
        dt, dn, field = DT_TRIP, t.name, "transport_receipt"
    elif kind == "ref":
        _gate_buy()
        dt, dn, field = DT_PRODUCT, target, "ref_image"
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
    # Public with an unguessable name: the accountant and the board must see a
    # photo the buyer took, and none of them has rights on the other's private
    # files (the souk doctypes are System Manager only; the portal gates).
    ext = (f.filename or "").rsplit(".", 1)[-1].lower() if "." in (f.filename or "") else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "heic"):
        frappe.throw("Photos only.")
    fdoc = frappe.get_doc({
        "doctype": "File", "file_name": f"souk-{kind}-{frappe.generate_hash(length=16)}.{ext}",
        "content": content, "attached_to_doctype": dt, "attached_to_name": str(dn), "is_private": 0,
    }).insert(ignore_permissions=True)
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
        "stalls": [{"name": r.name, "label": r.supplier_name or r.name} for r in stalls],
        "books": bool(s.get("custodyAccount")),
    }


@frappe.whitelist()
def similar(q=""):
    """Before buying: do we already sell something like this? Souk products
    first (with their last stall), then the catalogue by name."""
    _gate_view()
    q = (q or "").strip()
    if len(q) < 3:
        return {"rows": []}
    like = f"%{q}%"
    out = []
    for p in frappe.db.sql(
            f"""SELECT name, title, stage, supplier, ref_image FROM `tab{DT_PRODUCT}`
                WHERE (title LIKE %s OR name LIKE %s) AND stage != 'dropped'
                ORDER BY creation DESC LIMIT 5""", (like, like), as_dict=True):
        out.append({"kind": "souk", "key": p.name, "sku": p.name, "title": p.title,
                    "stage": p.stage, "stall": p.supplier or "", "image": p.ref_image or ""})
    for i in frappe.db.sql(
            """SELECT name, custom_sku, item_name, image FROM `tabItem`
               WHERE disabled = 0 AND has_variants = 0 AND (item_name LIKE %s OR custom_sku LIKE %s)
               ORDER BY modified DESC LIMIT 6""", (like, like), as_dict=True):
        out.append({"kind": "item", "key": i.name, "sku": i.custom_sku or i.name,
                    "title": i.item_name, "stage": "", "stall": "", "image": i.image or ""})
    return {"rows": out[:10]}


def _resolve_stall(stall, new_stall):
    """An existing stall, or a new one: one Supplier per stall, in the souk
    group, plain English capitals so it reads the same on every paper."""
    if stall:
        if not frappe.db.exists("Supplier", stall):
            frappe.throw("Unknown stall.")
        return stall
    ns = new_stall or {}
    name = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 &'.-]", "", (ns.get("name") or ""))).strip().upper()
    if len(name) < 3:
        frappe.throw("The stall's name, in Latin letters (e.g. AMINE DERB OMAR).")
    if frappe.db.exists("Supplier", name):
        return name
    phone = re.sub(r"[^\d+]", "", ns.get("phone") or "")
    sup = frappe.get_doc({
        "doctype": "Supplier", "supplier_name": name, "supplier_group": SUPPLIER_GROUP,
        "supplier_type": "Company", "country": "Morocco", "default_currency": "MAD",
        "supplier_details": f"Souk stall · {ns.get('place') or 'Derb Omar'}" + (f" · {phone}" if phone else ""),
    }).insert(ignore_permissions=True)
    return sup.name


def _validate_variants(base, colors, sizes, lines, color_map):
    """lines: [{color, size, qty, cost, price}] — one per colour × size the
    buyer actually bought. Returns the normalised variant list."""
    if not lines:
        frappe.throw("Enter at least one quantity.")
    seen = set()
    out = []
    for ln in lines:
        color = (ln.get("color") or "").upper()
        size = (ln.get("size") or "").strip()
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
        sku = _variant_sku(base, color, size)
        if len(sku) > SKU_MAX:
            frappe.throw(f"{sku} is longer than {SKU_MAX} characters — the shelf label can't scan it. "
                         "Use a shorter size code (S, M, L, XL, 2XL, 28…).")
        if sku in seen:
            frappe.throw(f"{sku} appears twice.")
        seen.add(sku)
        out.append({"sku": sku, "color": color, "colorFr": color_map.get(color, {}).get("fr", ""),
                    "size": _size_code(size) if size else "", "sizeLabel": size, "qty": qty,
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
    trip = _my_open_trip()
    if not trip:
        frappe.throw("No open custody. The accountant opens the trip and hands you the cash first.")
    title = re.sub(r"\s+", " ", (p.get("title") or "")).strip()
    if len(title) < 3:
        frappe.throw("Write the product's name.")
    cat = next((c for c in s["categories"] if c["key"] == p.get("category")), None)
    if not cat:
        frappe.throw("Choose a category.")
    color_map = {c["code"]: c for c in s["colors"]}
    colors = [c for c in (p.get("colors") or []) if c]
    sizes = [z for z in (p.get("sizes") or []) if (z or "").strip()]
    stall = _resolve_stall(p.get("stall"), p.get("newStall"))

    # Reserve the SKU number: the unique name is the lock.
    prefix = s["skuPrefix"]
    doc = None
    for _ in range(5):
        base = f"{prefix}{_next_sku_number(prefix)}"
        variants = _validate_variants(base, colors, sizes, p.get("lines") or [], color_map)
        total = round(sum(v["qty"] * v["cost"] for v in variants), 2)
        card = _trip_card(trip)
        if total > card["expected"] + 0.01:
            frappe.throw(f"This costs {total:,.0f} MAD and you have {card['expected']:,.0f} MAD of custody left.")
        try:
            doc = frappe.get_doc({
                "doctype": DT_PRODUCT, "sku_base": base, "title": title[:140],
                "stage": "buying", "stage_at": now_datetime(),
                "category": cat["key"], "product_type": cat["productType"], "brand": cat["brand"],
                "supplier": stall, "trip": str(trip.name), "buyer": frappe.session.user,
                "units": sum(v["qty"] for v in variants), "total_cost": total,
                "variants_json": json.dumps(variants, ensure_ascii=False),
            }).insert(ignore_permissions=True)
            frappe.db.commit()
            break
        except frappe.DuplicateEntryError:
            frappe.db.rollback()
            continue
    if not doc:
        frappe.throw("Could not reserve a SKU, retry.")
    doc.add_comment("Comment", f"Souk: bought from {stall} · {doc.units} pcs · {doc.total_cost:,.2f} MAD "
                               f"· trip {trip.name} · by {_user_name(frappe.session.user)}.")
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
           "status": "DRAFT", "tags": ["souk", f"souk-trip-{doc.trip}", doc.sku_base],
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
    if doc.stage != "buying":
        return {"name": doc.name, "pending": False, "stage": doc.stage, "po": doc.purchase_order}
    if not doc.shopify_product_id:
        try:
            _create_shopify_draft(doc)
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

    try:
        if not doc.purchase_order:
            po = _make_po(doc.supplier, doc.trip, doc.name,
                          [(v["itemCode"], v["qty"], v["cost"]) for v in variants],
                          receipt_image=doc.receipt_image)
            doc.db_set("purchase_order", po.name)
            frappe.db.commit()
        if not doc.purchase_invoice:
            pi = _make_paid_invoice(doc.purchase_order)
            if pi:
                doc.db_set("purchase_invoice", pi)
                frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        doc.reload()
        doc.db_set("error", f"Next: {str(e)[:400]}")
        frappe.db.commit()
        frappe.log_error(frappe.get_traceback()[:3000], f"souk.finish_buy {doc.name}")
        return {"name": doc.name, "pending": True, "error": doc.error}

    doc.db_set({"stage": "bought", "stage_at": now_datetime(), "bought_at": now_datetime(), "error": ""})
    doc.add_comment("Comment", f"Souk: {doc.purchase_order}"
                               + (f" + paid {doc.purchase_invoice}" if doc.purchase_invoice else "")
                               + " · waiting for receiving.")
    frappe.db.commit()
    return {"name": doc.name, "pending": False, "stage": "bought", "po": doc.purchase_order,
            "pi": doc.purchase_invoice or "", "variants": variants,
            "left": _trip_card(frappe.get_doc(DT_TRIP, cint(doc.trip)))["expected"]}


def _make_po(supplier, trip, product, lines, receipt_image=""):
    today = nowdate()
    po = frappe.new_doc("Purchase Order")
    po.update({
        "company": COMPANY, "supplier": supplier, "transaction_date": today, "schedule_date": today,
        "set_warehouse": RECEIVING_WH, "currency": "MAD", "taxes_and_charges": "",
        "custom_souk_trip": str(trip), "custom_souk_product": product or "",
    })
    if receipt_image:
        po.custom_souk_receipt = "receipt"
        po.custom_souk_receipt_image = receipt_image
    for code, qty, rate in lines:
        po.append("items", {"item_code": code, "qty": qty, "rate": rate,
                            "schedule_date": today, "warehouse": RECEIVING_WH})
    po.set("taxes", [])
    po.insert(ignore_permissions=True)
    po.submit()
    return po


def _make_paid_invoice(po_name):
    """Paid on the custody account — only once the accountant has named it."""
    acct = settings().get("custodyAccount")
    if not acct:
        return None
    from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
    pi = make_purchase_invoice(po_name)
    pi.update_stock = 0
    pi.is_paid = 1
    pi.mode_of_payment = MODE_OF_PAYMENT
    pi.cash_bank_account = acct
    pi.set("taxes", [])
    pi.run_method("set_missing_values")
    pi.run_method("calculate_taxes_and_totals")
    pi.paid_amount = pi.grand_total
    pi.base_paid_amount = pi.base_grand_total
    pi.insert(ignore_permissions=True)
    pi.submit()
    return pi.name


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
    trip = _my_open_trip()
    if not trip:
        frappe.throw("No open custody. The accountant opens the trip and hands you the cash first.")
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
    if total > _trip_card(trip)["expected"] + 0.01:
        frappe.throw(f"This costs {total:,.0f} MAD and you have {_trip_card(trip)['expected']:,.0f} MAD of custody left.")
    product = p.get("product") if p.get("kind") == "souk" else ""
    po = _make_po(stall, trip.name, product, lines)
    pi = _make_paid_invoice(po.name)
    if product and frappe.db.exists(DT_PRODUCT, product):
        frappe.get_doc(DT_PRODUCT, product).add_comment(
            "Comment", f"Souk: bought again from {stall} · {sum(q for _, q, _ in lines)} pcs · "
                       f"{total:,.2f} MAD · {po.name} · trip {trip.name}.")
    frappe.db.commit()
    return {"po": po.name, "pi": pi or "", "left": _trip_card(frappe.get_doc(DT_TRIP, trip.name))["expected"]}


# --- launch board --------------------------------------------------------------

def _age_days(dt):
    if not dt:
        return 0
    return round(time_diff_in_hours(now_datetime(), dt) / 24, 1)


@frappe.whitelist()
def board():
    _gate_view()
    s = settings()
    rows = frappe.get_all(DT_PRODUCT, filters={"stage": ["!=", "dropped"]},
                          fields=["name", "title", "stage", "stage_at", "supplier", "brand", "trip",
                                  "units", "total_cost", "ref_image", "bought_at", "creation", "error",
                                  "shopify_product_id"],
                          order_by="stage_at asc", limit=500)
    cards = []
    late = 0
    tied = 0.0
    for r in rows:
        age = _age_days(r.stage_at)
        limit = cint((s.get("stageDays") or {}).get(r.stage)) or 0
        is_late = bool(limit and age > limit) or bool(r.error)
        late += 1 if is_late else 0
        if r.stage != "live":
            tied += flt(r.total_cost)
        cards.append({
            "name": r.name, "title": r.title, "stage": r.stage, "age": age, "late": is_late,
            "limit": limit, "stall": r.supplier or "", "brand": r.brand or "", "trip": r.trip or "",
            "units": cint(r.units), "cost": flt(r.total_cost), "image": r.ref_image or "",
            "error": r.error or "", "sinceBuy": _age_days(r.bought_at or r.creation),
            "escalate": _age_days(r.bought_at or r.creation) > cint(s.get("escalateDays") or 21) and r.stage != "live",
        })
    dropped = frappe.db.count(DT_PRODUCT, {"stage": "dropped"})
    return {"stages": STAGES[:-1], "cards": cards, "late": late, "notLive": round(tied, 2),
            "dropped": dropped, "stageDays": s.get("stageDays"), "canBuy": _role() in ("manager", "sourcing")}


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
                  po.custom_souk_trip AS trip
           FROM `tabPurchase Order` po
           WHERE po.custom_souk_product = %s AND po.docstatus = 1 ORDER BY po.creation""",
        (doc.name,), as_dict=True)
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
                       "received": flt(p.per_received), "date": str(p.transaction_date), "trip": p.trip}
                      for p in pos],
        "events": events,
        "canBuy": _role() in ("manager", "sourcing"),
    }
