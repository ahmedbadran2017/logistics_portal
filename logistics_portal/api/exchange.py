"""Exchanges — the desk's Sales Exchange flow, portal-side.

The team runs ~250 exchanges a month from the desk today: pick the delivered
order, choose the replacement items, generate the Cathedis exchange shipment
(new AWB + label), and a Confirmed `<order>-ex` Sales Order enters the normal
picking flow. All of that logic already lives in ecommerce_integrations'
Sales Exchange doctype — this module orchestrates its whitelisted entry
points instead of duplicating them:

    create_sales_exchange_from_sales_order(sales_order)  -> `<so>-ex` draft
    create_exchange_shipment(name)                       -> Cathedis AWB+label
    create_sales_order_from_exchange(name)               -> Confirmed -ex SO

Statuses: Draft / Waiting for Cathedis API -> Label Generated -> Settled.
"""

import frappe


def _site_now():
    """The SITE clock as a bound param. The DB server runs on its own
    time zone, so NOW() made fresh rows read negative ages."""
    from frappe.utils import flt, now_datetime
    return str(now_datetime())[:19]
from frappe.utils import flt, now_datetime

_SE_MOD = ("ecommerce_integrations.ecommerce_integrations.doctype."
           "sales_exchange.sales_exchange")

TABS = ("waiting", "labeled", "settled")
_TAB_STATUSES = {
    "waiting": ("Draft", "Waiting for Cathedis API"),
    "labeled": ("Label Generated",),
    "settled": ("Settled", "Cancelled"),
}


def _gate():
    """Exchanges belong to the lane that handles them.

    The page sits in the CS lane's own sidebar — Tickets, Exchanges, Waiting
    on stock — and its gate admitted confirmation and manager only, so the
    three CS agents were refused by a tab that was listed for them. An
    exchange IS the customer-service conversation: a broken piece, a wrong
    size, a change of mind.

    Same role set as the urgent flag and the contact editor, reused rather
    than re-declared so the four cannot drift apart.
    """
    from logistics_portal.api.auth import resolve_role
    from logistics_portal.api.orders import _URGENT_ROLES
    role = resolve_role(frappe.session.user)
    if role not in _URGENT_ROLES:
        frappe.throw("Not authorized for the exchanges workspace.",
                     frappe.PermissionError)
    return role


def _se():
    if not frappe.db.exists("DocType", "Sales Exchange"):
        frappe.throw("Sales Exchange is not installed on this site.")
    return frappe.get_module(_SE_MOD)


@frappe.whitelist()
def board(tab="waiting", q="", limit=30, offset=0):
    _gate()
    if tab not in TABS:
        tab = "waiting"
    limit = min(max(int(limit or 30), 1), 100)
    offset = max(int(offset or 0), 0)
    if not frappe.db.exists("DocType", "Sales Exchange"):
        return {"tab": tab, "counts": {}, "total": 0, "rows": [],
                "available": False}

    counts = {}
    for t, sts in _TAB_STATUSES.items():
        counts[t] = int(frappe.db.sql(
            "SELECT COUNT(*) FROM `tabSales Exchange` WHERE exchange_status IN %s",
            (sts,))[0][0])

    vals = {"sts": _TAB_STATUSES[tab], "limit": limit, "offset": offset}
    conds = ["se.exchange_status IN %(sts)s"]
    if q and str(q).strip():
        vals["q"] = f"%{str(q).strip()}%"
        conds.append("""(se.name LIKE %(q)s OR se.sales_order LIKE %(q)s
                        OR se.customer_name LIKE %(q)s OR se.customer_phone LIKE %(q)s
                        OR se.new_awb LIKE %(q)s)""")
    where = " AND ".join(conds)
    total = frappe.db.sql(
        f"SELECT COUNT(*) FROM `tabSales Exchange` se WHERE {where}", vals)[0][0]
    rows = frappe.db.sql(
        f"""SELECT se.name, se.sales_order, se.exchange_sales_order,
                   se.customer_name AS customer, se.customer_phone AS phone,
                   se.exchange_city AS city, se.exchange_status AS status,
                   se.settlement_status, se.settlement_direction,
                   se.original_total, se.exchange_total, se.difference_amount,
                   se.old_awb, se.new_awb, se.new_label_url,
                   TIMESTAMPDIFF(HOUR, se.creation, %(now)s) AS age_h
            FROM `tabSales Exchange` se WHERE {where}
            ORDER BY se.modified DESC
            LIMIT %(limit)s OFFSET %(offset)s""", {**vals, "now": _site_now()}, as_dict=True)

    items_map = {}
    if rows:
        names = tuple(r.name for r in rows)
        for parent, txt in frappe.db.sql(
                """SELECT parent, GROUP_CONCAT(CONCAT(CAST(qty AS UNSIGNED), '× ',
                          COALESCE(NULLIF(item_name, ''), item_code))
                          ORDER BY idx SEPARATOR ' · ')
                   FROM `tabSales Exchange Item` WHERE parent IN %s
                   GROUP BY parent""", (names,)):
            items_map[parent] = (txt or "")[:200]

    return {
        "tab": tab, "counts": counts, "total": int(total or 0),
        "available": True,
        "rows": [{
            "name": r.name, "order": r.sales_order or "",
            "exOrder": r.exchange_sales_order or "",
            "customer": r.customer or "", "phone": (r.phone or "").strip(),
            "city": (r.city or "").strip().title(),
            "status": r.status or "Draft",
            "settlement": r.settlement_status or "Pending",
            "direction": r.settlement_direction or "",
            "originalTotal": float(r.original_total or 0),
            "exchangeTotal": float(r.exchange_total or 0),
            "difference": float(r.difference_amount or 0),
            "oldAwb": r.old_awb or "", "awb": r.new_awb or "",
            "labelUrl": r.new_label_url or "",
            "itemsText": items_map.get(r.name, ""),
            "ageH": int(r.age_h or 0),
        } for r in rows],
        "serverNow": str(now_datetime())[:19],
    }


@frappe.whitelist()
def start(order):
    """`<order>-ex` draft prefilled from the delivered order (desk parity)."""
    _gate()
    order = (order or "").strip()
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    if frappe.db.exists("Sales Exchange", f"{order}-ex"):
        frappe.throw(f"An exchange already exists for {order} ({order}-ex).")
    _se().create_sales_exchange_from_sales_order(order)
    name = f"{order}-ex"
    if not frappe.db.exists("Sales Exchange", name):
        # The desk helper names it <so>-ex; if that ever changes, find it.
        name = frappe.db.get_value("Sales Exchange", {"sales_order": order})
    frappe.get_doc("Sales Order", order).add_comment(
        "Comment", f"Exchange: created {name} · by {frappe.session.user}")
    frappe.db.commit()
    return {"ok": True, "name": name}


_FEE_TAG = "Pickup fee"


def _apply_pickup_fee(doc, reason):
    """Put the pickup fee on, or take it off, to match the reason.

    Rewritten every time rather than appended, so changing the reason from
    "we sent the wrong size" to "customer ordered the wrong size" moves the
    money instead of leaving a stale row behind.

    Only rows this function wrote are touched — a tax somebody added by hand
    is left alone, which it would not be if this cleared the table.
    """
    from logistics_portal.api.tickets import _cs_settings
    cfg = _cs_settings()
    keep = []
    for row in (doc.get("taxes") or []):
        if (row.description or "").strip() != _FEE_TAG:
            keep.append(row)
    doc.set("taxes", keep)
    if not (cfg.get("reasonFee") or {}).get(reason):
        return
    fee = flt(cfg.get("pickupFee") or 0)
    acc = (cfg.get("pickupFeeAccount") or "").strip()
    if fee <= 0 or not acc:
        return
    if not frappe.db.exists("Account", acc):
        # Never block a customer's exchange over a chart-of-accounts change:
        # the fee is dropped and the trail says so.
        doc.add_comment("Comment",
                        f"Pickup fee skipped — account {acc} not found.")
        return
    doc.append("taxes", {"charge_type": "Actual", "account_head": acc,
                         "description": _FEE_TAG, "tax_amount": fee,
                         "rate": 0})


@frappe.whitelist()
def set_items(name, items=None, reason=None, city=None, sector=None,
              address=None, phone=None):
    """The replacement items, the reason, and the fee the reason implies.

    THE REASON IS REQUIRED, and it is the only question the agent answers
    about money. Measured 2026-09-23: the doctype had no reason field at all,
    so a broken piece, a size the customer picked wrong and a change of mind
    were the same row. The wording of each reason carries whose fault it was,
    and tickets._CS_DEFAULTS["reasonFee"] maps that to "does the customer pay
    the pickup". One choice, and the money follows — no second field that
    could disagree with the first.

    THE FEE IS A TAX ROW, not a field write. The controller computes

        taxes_and_shipping_total = SUM(tax rows)
        exchange_total           = items + taxes_and_shipping_total
        difference_amount        = exchange_total - original_total

    so a single +25 Actual row does BOTH of Ahmed's rules at once: on a
    return it lifts exchange_total from 0 to 25 and the refund falls by 25;
    on a swap it adds 25 to what the customer owes. Writing the field
    directly would be overwritten by the next validate().

    Verified numerically before building: 161 refunded becomes 136, and a 89
    difference becomes 114.

    ITEMS MAY BE EMPTY. A pure return — the customer changed their mind and
    sends everything back — is 680 of the 1,000 exchanges on this site, and
    this function used to refuse it outright ("Add at least one replacement
    item"), which is why every one of them was made on the Desk. The reason
    is the guard against an accidental empty exchange, not the item list.
    """
    import json as _json
    _gate()
    name = (name or "").strip()
    if not frappe.db.exists("Sales Exchange", name):
        frappe.throw("Unknown exchange.")
    if isinstance(items, str):
        items = _json.loads(items)
    items = items or []
    if len(items) > 20:
        frappe.throw("20 items max.")
    reason = (reason or "").strip()
    if not reason:
        frappe.throw("Say why it is coming back — it decides who pays the "
                     "pickup, and nobody can reconstruct it later.")

    doc = frappe.get_doc("Sales Exchange", name)
    if doc.exchange_status not in ("Draft", "Waiting for Cathedis API"):
        frappe.throw(f"Exchange is already {doc.exchange_status}.")
    doc.set("exchange_items", [])
    for it in items:
        code = str(it.get("item_code") or "").strip()
        qty = float(it.get("qty") or 0)
        rate = float(it.get("rate") or 0)
        if not code or qty <= 0:
            frappe.throw("Each row needs an item and a positive quantity.")
        if not frappe.db.exists("Item", code):
            # Portal SKUs: fall back to the real-SKU custom field.
            by_sku = frappe.db.get_value("Item", {"custom_sku": code})
            if not by_sku:
                frappe.throw(f"Unknown item: {code}")
            code = by_sku
        doc.append("exchange_items", {"item_code": code, "qty": qty, "rate": rate})
    for field, val in (("exchange_city", city), ("exchange_sector", sector),
                       ("exchange_address", address), ("customer_phone", phone)):
        if val and str(val).strip():
            doc.set(field, str(val).strip())
    if doc.meta.has_field("custom_reason"):
        doc.set("custom_reason", reason)
    _apply_pickup_fee(doc, reason)
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "name": name, "reason": reason,
            "originalTotal": float(doc.original_total or 0),
            "exchangeTotal": float(doc.exchange_total or 0),
            "fee": float(doc.taxes_and_shipping_total or 0),
            "difference": float(doc.difference_amount or 0),
            "direction": doc.settlement_direction or ""}


@frappe.whitelist()
def generate(name):
    """Cathedis exchange shipment (new AWB + label) + the Confirmed -ex order
    that goes through the normal picking flow."""
    _gate()
    name = (name or "").strip()
    if not frappe.db.exists("Sales Exchange", name):
        frappe.throw("Unknown exchange.")
    # A state guard, like set_items and settle already have. Without it a
    # double-click -- the Cathedis call is slow enough to invite one -- buys a
    # SECOND carrier AWB and creates a second -ex Sales Order for one exchange.
    # Real money, and a second parcel to chase. The vocabulary is the field's
    # own Select: Draft / Waiting for Cathedis API / Label Generated / Settled
    # / Cancelled.
    doc = frappe.get_doc("Sales Exchange", name)
    if doc.exchange_status not in ("Draft", "Waiting for Cathedis API"):
        frappe.throw(f"This exchange is already {doc.exchange_status}"
                     + (f" (AWB {doc.new_awb})." if doc.new_awb else "."))
    if doc.new_awb:
        frappe.throw(f"This exchange already has AWB {doc.new_awb}.")
    m = _se()
    m.create_exchange_shipment(name)
    m.create_sales_order_from_exchange(name)
    doc = frappe.get_doc("Sales Exchange", name)
    if doc.sales_order and frappe.db.exists("Sales Order", doc.sales_order):
        frappe.get_doc("Sales Order", doc.sales_order).add_comment(
            "Comment", f"Exchange: label {doc.new_awb or ''} → {doc.exchange_sales_order or ''}"
                       f" · by {frappe.session.user}")
    frappe.db.commit()
    return {"ok": True, "name": name, "awb": doc.new_awb or "",
            "labelUrl": doc.new_label_url or "",
            "exOrder": doc.exchange_sales_order or ""}


@frappe.whitelist()
def settle(name, note=None):
    """Money squared with the customer — close the exchange."""
    _gate()
    from logistics_portal.api.auth import resolve_role
    from logistics_portal.api.rescue import _is_rs_admin
    from logistics_portal.api.tickets import _is_cs_admin
    if resolve_role(frappe.session.user) != "manager" \
            and not (_is_rs_admin() or _is_cs_admin()):
        frappe.throw("Only the portal manager or a section admin can settle "
                     "an exchange.", frappe.PermissionError)
    name = (name or "").strip()
    if not frappe.db.exists("Sales Exchange", name):
        frappe.throw("Unknown exchange.")
    doc = frappe.get_doc("Sales Exchange", name)
    if doc.exchange_status != "Label Generated":
        frappe.throw(f"Exchange is {doc.exchange_status} — nothing to settle.")
    note = (note or "").strip()
    doc.db_set("settlement_status", "Settled", update_modified=True)
    doc.db_set("exchange_status", "Settled", update_modified=False)
    doc.add_comment("Comment", "Exchange: settled"
                    + (f" — {note}" if note else "")
                    + f" · by {frappe.session.user}")
    frappe.db.commit()
    return {"ok": True, "name": name}
