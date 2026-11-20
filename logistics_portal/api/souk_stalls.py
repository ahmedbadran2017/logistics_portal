"""The souk's stalls (المحلات): one ERPNext Supplier per stall in Derb Omar,
in the "Souk Suppliers" group — a directory the buyer searches, and each
stall's account with us (Ahmed, 2026-11-20).

Where a stall's facts live — all native Supplier fields, no migrate:
* phone  → a Contact linked to the Supplier, set as its primary contact
           (Supplier.mobile_no is fetched from it, as for every supplier);
* place  → Supplier.supplier_details, "Souk stall · <row / shop no.>";
* photo  → Supplier.image (the storefront);
* sells  → Supplier.custom_product_categories, the souk category keys, comma
           separated; the categories of what we actually bought are added;
* note   → Supplier.custom_business_description.

The balance — what we owe the stall, net of what it owes us:
    books    = the Supplier's GL balance (credit − debit): invoices, payments,
               debit notes and advances, as the accountant posted them;
  + unbilled = cheque / transfer / credit purchases the accountant has not
               invoiced yet (cash was paid at the stall: nothing owed);
  − owedBack = broken / short at the stall on a purchase with no invoice and
               no Debit Note yet (once invoiced, the books carry it).
A purchase is overdue when it is not cash, its due date has passed and it is
still unpaid.

Who sees what: the buyer sees the balance (and what is overdue) only; the
manager and the accountant also see the statement — every purchase, invoice
and payment. Enforced here, not in the screen.
"""

import difflib
import re

import frappe
from frappe.utils import cint, flt, getdate, nowdate

from logistics_portal.api import souk as S

PLACE_PREFIX = "Souk stall · "
NON_CASH = ("cheque", "transfer", "credit")


# --- gates -------------------------------------------------------------------

def _gate():
    if S._role() not in ("manager", "sourcing", "accountant") and not S._is_accountant():
        frappe.throw("Not authorized for the souk stalls.", frappe.PermissionError)


def _full():
    """The statement: the manager and the accountant. The buyer: balance only."""
    return S._role() == "manager" or S._is_accountant()


# --- small helpers -------------------------------------------------------------

def _norm_name(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _clean_name(s):
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 &'.-]", "", (s or ""))).strip().upper()


def _clean_phone(s):
    p = re.sub(r"[^\d+]", "", s or "")
    if p.startswith("+212"):
        p = "0" + p[4:]
    elif p.startswith("00212"):
        p = "0" + p[5:]
    elif p.startswith("212") and len(p) == 12:
        p = "0" + p[3:]
    return p[:16]


def _phone_key(p):
    d = re.sub(r"\D", "", p or "")
    return d[-9:] if len(d) >= 9 else ""


def _wa(p):
    """wa.me wants the international number without + (06… → 2126…)."""
    d = re.sub(r"\D", "", p or "")
    if d.startswith("0") and len(d) == 10:
        d = "212" + d[1:]
    return d if len(d) >= 9 else ""


def _place_of(details):
    t = (details or "").strip()
    if t.startswith(PLACE_PREFIX):
        t = t[len(PLACE_PREFIX):]
    # The pre-2026-11-20 form appended the phone: "Derb Omar · 06…".
    parts = [x.strip() for x in t.split("·")]
    parts = [x for x in parts if x and not re.fullmatch(r"[\d+ ]{6,}", x)]
    return " · ".join(parts)[:120]


def _phone_in_details(details):
    m = re.search(r"(\+?\d[\d ]{7,}\d)", details or "")
    return _clean_phone(m.group(1)) if m else ""


def _cat_keys():
    return [c["key"] for c in S.settings()["categories"]]


def _clean_sells(v):
    keys = set(_cat_keys())
    if isinstance(v, str):
        v = [x for x in v.split(",")]
    return [k for k in dict.fromkeys(str(x).strip().lower() for x in (v or [])) if k in keys][:12]


def _stall_names():
    return [r[0] for r in frappe.db.sql(
        "SELECT name FROM `tabSupplier` WHERE supplier_group = %s", (S.SUPPLIER_GROUP,))]


# --- the account ---------------------------------------------------------------

def _pos(names):
    if not names:
        return []
    extra = ""
    for c in ("custom_souk_pay", "custom_souk_pay_ref", "custom_souk_pay_due", "custom_souk_buyer"):
        extra += f", po.{c}" if S._has_col("Purchase Order", c) else f", NULL AS {c}"
    return frappe.db.sql(
        f"""SELECT po.name, po.supplier, po.transaction_date, po.grand_total, po.advance_paid,
                   po.per_billed, po.per_received, po.status, po.custom_souk_trip,
                   po.custom_souk_product, po.custom_souk_received, po.custom_souk_owed,
                   po.custom_souk_debit_note, po.custom_souk_receipt_image {extra}
            FROM `tabPurchase Order` po
            WHERE po.docstatus = 1 AND po.supplier IN %s
            ORDER BY po.transaction_date DESC, po.creation DESC""", (tuple(names),), as_dict=True)


def _po_invoices(po_names):
    """{po: {"pis": [names], "outstanding": x}} — the invoices that bill it."""
    out = {}
    if not po_names:
        return out
    rows = frappe.db.sql(
        """SELECT DISTINCT pii.purchase_order AS po, pi.name, pi.outstanding_amount
           FROM `tabPurchase Invoice Item` pii JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
           WHERE pii.purchase_order IN %s AND pi.docstatus = 1 AND pi.is_return = 0""",
        (tuple(po_names),), as_dict=True)
    for r in rows:
        o = out.setdefault(r.po, {"pis": [], "outstanding": 0.0})
        o["pis"].append(r.name)
        o["outstanding"] += flt(r.outstanding_amount)
    return out


def _books(names):
    """The GL: what the books say we owe each stall (credit − debit)."""
    if not names:
        return {}
    return {r[0]: flt(r[1]) for r in frappe.db.sql(
        """SELECT party, SUM(credit_in_account_currency - debit_in_account_currency)
           FROM `tabGL Entry` WHERE party_type = 'Supplier' AND party IN %s
             AND is_cancelled = 0 AND company = %s GROUP BY party""", (tuple(names), S.COMPANY))}


def _line(po, inv, today):
    """One purchase as the account reads it."""
    method = po.custom_souk_pay or ("cash" if po.custom_souk_trip else "")
    total = flt(po.grand_total)
    billed = flt(po.per_billed)
    i = inv.get(po.name) or {}
    invoiced = bool(i.get("pis"))
    if method == "cash":
        state, unpaid, unbilled = "paidAtStall", 0.0, 0.0
    else:
        # Not invoiced: the whole purchase (less any advance) is still owed and
        # the books do not know it yet. Invoiced: the books carry it.
        unbilled = 0.0 if (invoiced and po.status in ("Closed", "Completed")) else total * max(0.0, 1 - billed / 100.0)
        if invoiced:
            unpaid = max(0.0, flt(i.get("outstanding")) + unbilled)
        else:
            unpaid = max(0.0, total - flt(po.advance_paid))
        state = "paid" if unpaid < 0.01 else ("invoiced" if invoiced else "notInvoiced")
    owed = flt(po.custom_souk_owed)
    # Owed back and not in the books yet: no Debit Note and no invoice.
    owed_open = owed if owed and not po.custom_souk_debit_note and not invoiced else 0.0
    due = str(po.custom_souk_pay_due or "") or None
    overdue = bool(method in NON_CASH and unpaid >= 0.01 and due and getdate(due) < today)
    received = po.custom_souk_received or ""
    return {
        "po": po.name, "date": str(po.transaction_date or ""), "total": total, "method": method or "",
        "ref": po.custom_souk_pay_ref or "", "due": due, "state": "overdue" if overdue else state,
        "unpaid": round(unpaid, 2), "unbilled": round(unbilled, 2), "owed": owed, "owedOpen": owed_open,
        "debitNote": po.custom_souk_debit_note or "", "invoices": i.get("pis") or [],
        "received": "" if received == "NONE" else received, "nothingArrived": received == "NONE",
        "product": po.custom_souk_product or "", "receipt": po.custom_souk_receipt_image or "",
        "overdue": overdue,
    }


def _accounts(names):
    """{stall: {balance, books, unbilled, owedBack, overdue, nextDue, lines}}."""
    today = getdate(nowdate())
    pos = _pos(names)
    inv = _po_invoices([p.name for p in pos])
    books = _books(names)
    out = {n: {"books": round(books.get(n, 0.0), 2), "unbilled": 0.0, "owedBack": 0.0,
               "overdue": 0.0, "overdueN": 0, "nextDue": None, "lines": [], "notBilledN": 0} for n in names}
    for p in pos:
        a = out.get(p.supplier)
        if a is None:
            continue
        ln = _line(p, inv, today)
        a["lines"].append(ln)
        a["unbilled"] += ln["unbilled"] if ln["method"] in NON_CASH else 0.0
        a["owedBack"] += ln["owedOpen"]
        if ln["overdue"]:
            a["overdue"] += ln["unpaid"]
            a["overdueN"] += 1
        elif ln["method"] in NON_CASH and ln["unpaid"] >= 0.01 and ln["due"]:
            if not a["nextDue"] or ln["due"] < a["nextDue"]["date"]:
                a["nextDue"] = {"date": ln["due"], "amount": ln["unpaid"]}
        # Received, not invoiced: the accountant's queue.
        if ln["received"] and not ln["invoices"]:
            a["notBilledN"] += 1
    for a in out.values():
        a["unbilled"] = round(a["unbilled"], 2)
        a["owedBack"] = round(a["owedBack"], 2)
        a["overdue"] = round(a["overdue"], 2)
        a["balance"] = round(a["books"] + a["unbilled"] - a["owedBack"], 2)
    return out


def _stats(lines):
    received = [l for l in lines if l["received"] or l["nothingArrived"]]
    issues = [l for l in received if l["owed"] > 0 or l["nothingArrived"]]
    return {"buys": len(lines), "bought": round(sum(l["total"] for l in lines), 2),
            "last": lines[0]["date"] if lines else "",
            "received": len(received), "issues": len(issues),
            "issueRate": round(100.0 * len(issues) / len(received)) if received else None}


# --- the directory -------------------------------------------------------------

def _profiles(names):
    if not names:
        return {}
    rows = frappe.db.sql(
        """SELECT name, supplier_name, mobile_no, supplier_details, image, disabled,
                  custom_product_categories, custom_business_description, creation
           FROM `tabSupplier` WHERE name IN %s""", (tuple(names),), as_dict=True)
    bought_cats = {}
    for sup, cat in frappe.db.sql(
            f"""SELECT DISTINCT po.supplier, p.category FROM `tabPurchase Order` po
                JOIN `tab{S.DT_PRODUCT}` p ON p.name = po.custom_souk_product
                WHERE po.docstatus = 1 AND po.supplier IN %s AND IFNULL(p.category, '') != ''""",
            (tuple(names),)):
        bought_cats.setdefault(sup, []).append(cat)
    out = {}
    for r in rows:
        phone = _clean_phone(r.mobile_no or "") or _phone_in_details(r.supplier_details)
        sells = _clean_sells(r.custom_product_categories or "")
        cats = list(dict.fromkeys(sells + [c for c in bought_cats.get(r.name, []) if c]))
        out[r.name] = {
            "name": r.name, "label": r.supplier_name or r.name, "phone": phone, "wa": _wa(phone),
            "place": _place_of(r.supplier_details), "photo": r.image or "", "sells": sells, "cats": cats,
            "note": r.custom_business_description or "", "disabled": cint(r.disabled),
            "since": str(r.creation or "")[:10],
        }
    return out


@frappe.whitelist()
def stalls_boot():
    _gate()
    names = _stall_names()
    prof = _profiles(names)
    acc = _accounts(names)
    full = _full()
    rows = []
    for n in names:
        p, a = prof.get(n), acc.get(n)
        if not p:
            continue
        st = _stats(a["lines"])
        rows.append({**p, "balance": a["balance"], "overdue": a["overdue"], "overdueN": a["overdueN"],
                     "nextDue": a["nextDue"], "buys": st["buys"], "last": st["last"],
                     "issueRate": st["issueRate"],
                     "notBilledN": a["notBilledN"] if full else None})
    # Overdue first, then the most recently bought from; disabled at the end.
    rows.sort(key=lambda r: r["last"] or "", reverse=True)
    rows.sort(key=lambda r: (r["disabled"], 0 if r["overdue"] else 1))
    s = S.settings()
    return {
        "full": full,
        "canEdit": S._role() in ("manager", "sourcing") or S._is_accountant(),
        "categories": [{"key": c["key"], "ar": c["ar"], "fr": c["fr"]} for c in s["categories"]],
        "stalls": rows,
        "totals": {
            "balance": round(sum(r["balance"] for r in rows), 2),
            "overdue": round(sum(r["overdue"] for r in rows), 2),
            "overdueStalls": sum(1 for r in rows if r["overdue"]),
            "notBilled": sum(r["notBilledN"] or 0 for r in rows) if full else None,
        },
    }


@frappe.whitelist()
def stall(name):
    _gate()
    if not frappe.db.exists("Supplier", {"name": name, "supplier_group": S.SUPPLIER_GROUP}):
        frappe.throw("Unknown stall.")
    p = _profiles([name])[name]
    a = _accounts([name])[name]
    full = _full()
    st = _stats(a["lines"])
    products = []
    codes = [l["product"] for l in a["lines"] if l["product"]]
    if codes:
        pmap = {r.name: r for r in frappe.db.sql(
            f"""SELECT name, title, stage, ref_image, category FROM `tab{S.DT_PRODUCT}`
                WHERE name IN %s""", (tuple(dict.fromkeys(codes)),), as_dict=True)}
        for c in dict.fromkeys(codes):
            r = pmap.get(c)
            if r:
                products.append({"name": r.name, "title": r.title, "stage": r.stage,
                                 "image": r.ref_image or "", "category": r.category or ""})
    out = {
        **p, "full": full,
        "account": {"balance": a["balance"], "overdue": a["overdue"], "overdueN": a["overdueN"],
                    "nextDue": a["nextDue"]},
        "stats": {k: st[k] for k in ("buys", "last", "received", "issues", "issueRate")},
        "products": products[:24],
        "statement": None,
    }
    if full:
        out["account"].update({"books": a["books"], "unbilled": a["unbilled"], "owedBack": a["owedBack"],
                               "notBilledN": a["notBilledN"]})
        out["stats"]["bought"] = st["bought"]
        out["statement"] = {"lines": a["lines"], "payments": _payments(name), "returns": _returns(name)}
    return out


def _payments(name):
    """Money that went to (or came back from) the stall, as booked."""
    return [{"voucher": r.voucher_no, "type": r.voucher_type, "date": str(r.posting_date),
             "amount": round(flt(r.amount), 2)}
            for r in frappe.db.sql(
                """SELECT voucher_type, voucher_no, posting_date,
                          SUM(debit_in_account_currency - credit_in_account_currency) AS amount
                   FROM `tabGL Entry` WHERE party_type = 'Supplier' AND party = %s AND is_cancelled = 0
                     AND company = %s AND voucher_type IN ('Payment Entry', 'Journal Entry')
                   GROUP BY voucher_type, voucher_no, posting_date
                   ORDER BY posting_date DESC LIMIT 100""", (name, S.COMPANY), as_dict=True)]


def _returns(name):
    """Debit Notes: what the stall owes us, in the books."""
    return [{"name": r.name, "date": str(r.posting_date), "amount": round(-flt(r.grand_total), 2),
             "open": round(-flt(r.outstanding_amount), 2), "against": r.return_against or ""}
            for r in frappe.db.sql(
                """SELECT name, posting_date, grand_total, outstanding_amount, return_against
                   FROM `tabPurchase Invoice` WHERE supplier = %s AND docstatus = 1 AND is_return = 1
                   ORDER BY posting_date DESC LIMIT 100""", (name,), as_dict=True)]


# --- the same stall twice? -------------------------------------------------------

def matches(name="", phone="", exclude=""):
    """Stalls that look like this one: the same phone, or a name that reads
    the same (AMINE DERB OMAR / AMIN DERB-OMAR / DERB OMAR AMINE)."""
    nn, pk = _norm_name(name), _phone_key(_clean_phone(phone))
    if len(nn) < 3 and not pk:
        return []
    out = []
    for r in frappe.db.sql(
            """SELECT name, supplier_name, mobile_no, supplier_details, image FROM `tabSupplier`
               WHERE supplier_group = %s AND disabled = 0""", (S.SUPPLIER_GROUP,), as_dict=True):
        if r.name == exclude:
            continue
        rp = _clean_phone(r.mobile_no or "") or _phone_in_details(r.supplier_details)
        why = ""
        if pk and _phone_key(rp) == pk:
            why = "phone"
        elif len(nn) >= 3:
            rn = _norm_name(r.supplier_name or r.name)
            words_a = set(_clean_name(name).split())
            words_b = set(_clean_name(r.supplier_name or r.name).split())
            if rn == nn or (min(len(rn), len(nn)) >= 4 and (rn in nn or nn in rn)):
                why = "name"
            elif difflib.SequenceMatcher(None, rn, nn).ratio() >= 0.82:
                why = "name"
            elif len(words_a) >= 2 and words_a == words_b:
                why = "name"
        if why:
            out.append({"name": r.name, "label": r.supplier_name or r.name, "phone": rp,
                        "place": _place_of(r.supplier_details), "photo": r.image or "", "why": why})
    out.sort(key=lambda m: 0 if m["why"] == "phone" else 1)
    return out[:5]


@frappe.whitelist()
def similar_stalls(name="", phone="", exclude=""):
    _gate()
    return {"rows": matches(name, phone, exclude)}


# --- create / edit ---------------------------------------------------------------

def _set_phone(sup, label, phone):
    """The phone on the stall's primary Contact (Supplier.mobile_no follows),
    as for every other supplier in ERPNext."""
    phone = _clean_phone(phone)
    cur = frappe.db.get_value("Supplier", sup, "supplier_primary_contact")
    if cur and frappe.db.exists("Contact", cur):
        c = frappe.get_doc("Contact", cur)
        rows = [p for p in c.phone_nos if not p.is_primary_mobile_no]
        c.set("phone_nos", rows)
        if phone:
            c.append("phone_nos", {"phone": phone, "is_primary_mobile_no": 1})
        c.mobile_no = phone
        c.save(ignore_permissions=True)
    elif phone:
        c = frappe.get_doc({
            "doctype": "Contact", "first_name": label[:140],
            "phone_nos": [{"phone": phone, "is_primary_mobile_no": 1}],
            "links": [{"link_doctype": "Supplier", "link_name": sup}],
        }).insert(ignore_permissions=True)
        cur = c.name
    frappe.db.set_value("Supplier", sup, {"supplier_primary_contact": cur or None, "mobile_no": phone or None},
                        update_modified=False)


def _apply(sup, data, label):
    upd = {}
    if "place" in data:
        place = re.sub(r"\s+", " ", str(data.get("place") or "")).strip()[:120]
        upd["supplier_details"] = PLACE_PREFIX + (place or "Derb Omar")
    if "sells" in data and S._has_col("Supplier", "custom_product_categories"):
        upd["custom_product_categories"] = ",".join(_clean_sells(data.get("sells")))
    if "note" in data and S._has_col("Supplier", "custom_business_description"):
        upd["custom_business_description"] = str(data.get("note") or "").strip()[:500]
    if upd:
        frappe.db.set_value("Supplier", sup, upd, update_modified=True)
    if "phone" in data:
        _set_phone(sup, label, data.get("phone") or "")


def create(ns, sure=False):
    """A new stall (from the buy form or the stalls screen). Refused when the
    phone already belongs to a stall, unless the buyer said it is another one."""
    ns = ns or {}
    name = _clean_name(ns.get("name"))
    if len(name) < 3:
        frappe.throw("The stall's name, in Latin letters (e.g. AMINE DERB OMAR).")
    if frappe.db.exists("Supplier", name):
        if frappe.db.get_value("Supplier", name, "supplier_group") != S.SUPPLIER_GROUP:
            frappe.throw(f"{name} is already a supplier outside the souk: pick another name.")
        return name
    phone = _clean_phone(ns.get("phone"))
    if phone and len(re.sub(r"\D", "", phone)) < 9:
        frappe.throw("The phone number is too short.")
    if not sure:
        same = [m for m in matches(name, phone) if m["why"] == "phone"]
        if same:
            frappe.throw(f"This phone belongs to the stall {same[0]['label']}. "
                         "Choose it from the list, or confirm that it is another stall.")
    sup = frappe.get_doc({
        "doctype": "Supplier", "supplier_name": name, "supplier_group": S.SUPPLIER_GROUP,
        "supplier_type": "Company", "country": "Morocco", "default_currency": "MAD",
        "supplier_details": PLACE_PREFIX + (re.sub(r"\s+", " ", str(ns.get("place") or "")).strip()[:120] or "Derb Omar"),
    }).insert(ignore_permissions=True)
    rest = {k: ns[k] for k in ("sells", "note") if k in ns}
    if phone:
        rest["phone"] = phone
    _apply(sup.name, rest, name)
    return sup.name


@frappe.whitelist(methods=["POST"])
def create_stall(payload):
    _gate()
    p = frappe.parse_json(payload) if isinstance(payload, str) else (payload or {})
    name = create(p, sure=bool(p.get("sure")))
    frappe.db.commit()
    return stall(name)


@frappe.whitelist(methods=["POST"])
def save_stall(name, payload):
    _gate()
    if not frappe.db.exists("Supplier", {"name": name, "supplier_group": S.SUPPLIER_GROUP}):
        frappe.throw("Unknown stall.")
    p = frappe.parse_json(payload) if isinstance(payload, str) else (payload or {})
    data = {k: p[k] for k in ("phone", "place", "sells", "note") if k in p}
    label = frappe.db.get_value("Supplier", name, "supplier_name") or name
    if "label" in p:
        new = _clean_name(p.get("label"))
        if len(new) < 3:
            frappe.throw("The stall's name, in Latin letters.")
        if new != label:
            # The display name only: the record keeps its id, its POs and its account.
            frappe.db.set_value("Supplier", name, "supplier_name", new)
            label = new
    if "phone" in data:
        ph = _clean_phone(data["phone"])
        if ph and len(re.sub(r"\D", "", ph)) < 9:
            frappe.throw("The phone number is too short.")
        if ph and not p.get("sure"):
            same = [m for m in matches("", ph, exclude=name) if m["why"] == "phone"]
            if same:
                frappe.throw(f"This phone belongs to the stall {same[0]['label']}.")
    _apply(name, data, label)
    if "disabled" in p and _full():
        frappe.db.set_value("Supplier", name, "disabled", 1 if p.get("disabled") else 0)
    frappe.db.commit()
    return stall(name)
