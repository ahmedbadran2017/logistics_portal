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
_CO = "Justyol Morocco"

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

    # The reason is what decides the money, so the board has to show the one
    # on file. Without it the edit panel reopened blank and — because the
    # reason is required to save — the agent picked again from memory, which
    # is 25 MAD moving on a guess. Guarded because the field arrives with a
    # migrate and the board must not 500 on a site that has not run one.
    reason_col = ("se.custom_reason AS reason,"
                  if frappe.db.has_column("Sales Exchange", "custom_reason")
                  else "'' AS reason,")
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
                   {reason_col}
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
            "reason": r.get("reason") or "",
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
_FREE_TAG = "Replacement at no charge"
_MONEY_TAGS = (_FEE_TAG, _FREE_TAG)


def _price_of(doc, code, fallback_order=""):
    """What a replacement row is worth when the agent leaves the rate blank.

    The rate was a blank money box the agent typed by hand, defaulting to 0,
    and 743 of the 1,096 replacement rows on this site are priced at zero
    because of it. Zero is not free — the controller reads

        exchange_total = items + taxes

    so an unpriced replacement makes exchange_total 0 and the settlement then
    reads "Refund 169 to the customer" on an order where we are sending a new
    parcel and owe nothing. Measured in memory on J-007177-ex: rate 0 gives
    -169.00 Refund to Customer; the same row at its real 169 gives 0.00 and
    No Settlement.

    So price it here instead of asking. Like-for-like first — the customer
    already paid that exact rate on the original line, and a same-SKU swap
    then lands on a difference of exactly zero with no rounding to argue
    about.

    WHAT THE CUSTOMER LAST PAID, not the catalogue, is the fallback that
    works. Prices live in Shopify, not in ERPNext: 242 of the 248 items ever
    used as a replacement have no Item Price at all, so a catalogue-only
    lookup priced 17.9% of the 1,096 rows on this site and left 82% at zero.
    Reading the last rate the item actually sold at on a submitted order
    takes that to 96.9%, and the 3.1% left over are items never sold — for
    those the agent is asked, and only when the answer is money we collect.
    """
    order = (doc.sales_order or fallback_order or "").strip()
    if order:
        rate = frappe.db.get_value("Sales Order Item",
                                   {"parent": order, "item_code": code}, "rate")
        if flt(rate) > 0:
            return flt(rate)
    pl = frappe.db.get_single_value("Selling Settings", "selling_price_list")
    if pl:
        rate = frappe.db.get_value("Item Price",
                                   {"item_code": code, "price_list": pl,
                                    "selling": 1}, "price_list_rate")
        if flt(rate) > 0:
            return flt(rate)
    sold = frappe.db.sql("""SELECT i.rate FROM `tabSales Order Item` i
        JOIN `tabSales Order` so ON so.name = i.parent
        WHERE i.item_code = %s AND so.company = %s AND so.docstatus = 1
          AND i.rate > 0
        ORDER BY so.transaction_date DESC, so.creation DESC LIMIT 1""",
        (code, _CO))
    if sold and flt(sold[0][0]) > 0:
        return flt(sold[0][0])
    rate = frappe.db.get_value("Item Price", {"item_code": code, "selling": 1},
                               "price_list_rate")
    if flt(rate) > 0:
        return flt(rate)
    return flt(frappe.db.get_value("Item", code, "standard_rate") or 0)


def _apply_money(doc, reason):
    """The rows the reason implies — the pickup fee, or the no-charge offset.

    Rewritten from scratch every time rather than appended, so changing the
    reason from "we sent the wrong size" to "customer ordered the wrong size"
    moves the money instead of leaving a stale row behind. Only rows this
    function wrote are touched; a tax somebody added by hand is left alone,
    which it would not be if this cleared the table. (Verified on production:
    no exchange on this site has ever carried a tax row, so there is nothing
    pre-existing to disturb.)

    Four outcomes, which are Ahmed's five cases plus the honest extras:

        our fault  + replacement sent -> difference 0
        our fault  + nothing sent     -> full refund, no fee
        their call + replacement sent -> new - original + 25
        their call + nothing sent     -> original - 25

    The first one needs a lever, because `difference_amount` is computed and
    `original_total` is recomputed on every validate() — writing it is
    discarded (measured: set to 0, reads back 169). The only lever the
    controller leaves is the tax table, so the gap between what the customer
    paid and what we are sending back out is closed with one tagged Actual
    row. The Sales Exchange is not submittable and has never produced a
    single GL Entry, so this moves the settlement number and nothing else.
    """
    from logistics_portal.api.tickets import _cs_settings
    cfg = _cs_settings()
    doc.set("taxes", [r for r in (doc.get("taxes") or [])
                      if (r.description or "").strip() not in _MONEY_TAGS])

    def _row(acc, tag, amount):
        if not acc:
            return
        if not frappe.db.exists("Account", acc):
            # Never block a customer's exchange over a chart-of-accounts
            # change: the row is dropped and the trail says so.
            doc.add_comment("Comment", f"{tag} skipped — account {acc} not found.")
            return
        doc.append("taxes", {"charge_type": "Actual", "account_head": acc,
                            "description": tag, "tax_amount": amount, "rate": 0})

    if (cfg.get("reasonFee") or {}).get(reason):
        fee = flt(cfg.get("pickupFee") or 0)
        if fee > 0:
            _row((cfg.get("pickupFeeAccount") or "").strip(), _FEE_TAG, fee)
        return

    # Our own mistake. If we are sending a replacement, the customer owes
    # nothing and is owed nothing — so close the gap to exactly zero.
    #
    # Only when something IS going out. "Damaged on arrival" with no
    # replacement is a customer who wants their money back, not a swap, and
    # the full refund with no pickup fee is the correct answer there; zeroing
    # it would quietly cancel a refund we owe.
    rows = doc.get("exchange_items") or []
    if not rows:
        return
    # Summed from the rows, NOT read off the field.
    #
    # `original_total` is recomputed by validate() from original_items, and
    # this runs before that — so the field still holds the value from before
    # the agent changed what is coming back. Reading it made "a piece was
    # missing, send one out" settle as "collect the whole order" instead of
    # zero. Same arithmetic the controller uses, so the two agree whichever
    # order they run in.
    # No rows means nothing is coming back, and nothing coming back is worth
    # zero — not "fall back to the old field". Falling back left "a piece was
    # missing, send one out" reading as collect-the-whole-order, because the
    # field still held the value from before the agent emptied the table.
    # Every exchange on this site is created with its lines already in there,
    # so an empty table is always a deliberate answer.
    back = doc.get("original_items") or []
    orig = sum(flt(r.rate) * flt(r.qty) for r in back)
    gap = orig - sum(flt(r.rate) * flt(r.qty) for r in rows)
    if abs(gap) < 0.01:
        return
    _row((cfg.get("noChargeAccount") or "").strip(), _FREE_TAG, gap)


def _fill_returning(doc, returning):
    """Which of the order's lines are coming back, on the table built for it.

    Shopify models a return as `returnLineItems`, each one a quantity against
    a line of the order — you cannot name a product that was never bought.
    This doctype has the same idea in `original_items`, and its validate()
    already refuses a row that is not on the Sales Order (verified: it throws
    "Item X is not present in Sales Order Y"). Across every exchange on this
    site the table holds zero rows, so the pickup has never had an item list.

    THE TABLE IS ALREADY THERE AND ALREADY FULL. Creating an exchange copies
    the order's lines into it — all 1,002 exchanges on this site carry
    theirs. What was missing is the ability to say only SOME of it is coming
    back, which is what a partial return is.

    THE RATE COMES WITH IT, and that is not decoration. `original_total` is
    summed from these rows (rate × qty, measured: a row with no rate reads
    0.00), so writing lines without a price collapses it and every settlement
    on the document inverts — a plain return that should refund 126 read as
    "collect 25". The rate is taken from the order line, so a full return
    totals exactly what the customer paid.

    A PARTIAL return therefore settles against what is actually coming back
    rather than against the whole order, which is the correct answer and a
    change from what the desk does today.
    """
    if returning is None:
        return
    doc.set("original_items", [])
    order = (doc.sales_order or "").strip()
    for it in returning:
        code = str(it.get("item_code") or "").strip()
        qty = float(it.get("qty") or 0)
        if not code or qty <= 0:
            continue
        rate = 0.0
        if order:
            rate = flt(frappe.db.get_value(
                "Sales Order Item", {"parent": order, "item_code": code}, "rate"))
        doc.append("original_items", {"item_code": code, "qty": qty, "rate": rate})


def _fill_items(doc, items):
    """Put the replacement rows on the doc and say what they resolved to.

    Shared by set_items and quote so the number the agent is shown BEFORE
    saving cannot disagree with the one that gets saved — the preview is the
    same code, not a second implementation of the same rules.
    """
    doc.set("exchange_items", [])
    resolved, unpriced = [], []
    for it in items:
        code = str(it.get("item_code") or "").strip()
        qty = float(it.get("qty") or 0)
        rate = float(it.get("rate") or 0)
        if not code or qty <= 0:
            frappe.throw("Each row needs an item and a positive quantity.")
        typed = code
        if not frappe.db.exists("Item", code):
            # Portal SKUs: fall back to the real-SKU custom field.
            by_sku = frappe.db.get_value("Item", {"custom_sku": code})
            if not by_sku:
                frappe.throw(f"Unknown item: {code}")
            code = by_sku
        auto = rate <= 0
        if auto:
            # Blank means "the price we already know", not "free".
            rate = _price_of(doc, code)
        doc.append("exchange_items", {"item_code": code, "qty": qty, "rate": rate})
        if rate <= 0:
            unpriced.append(code)
        resolved.append({"typed": typed, "code": code,
                         "name": frappe.db.get_value("Item", code, "item_name") or code,
                         "qty": qty, "rate": float(rate), "auto": auto})
    return resolved, unpriced


@frappe.whitelist()
def quote(name, items=None, reason=None, returning=None):
    """What this exchange WOULD settle at, without saving a thing.

    The agent is on the phone and has to say a number out loud. Until now the
    only way to see it was to save, so the price we would use, the item the
    code resolves to and the money the customer owes were all invisible at
    the moment they were being decided. Nothing here is written: the doc is
    built in memory, validated, and dropped.
    """
    import json as _json
    _gate()
    name = (name or "").strip()
    if not frappe.db.exists("Sales Exchange", name):
        frappe.throw("Unknown exchange.")
    if isinstance(items, str):
        items = _json.loads(items)
    items = [it for it in (items or []) if str(it.get("item_code") or "").strip()]
    if len(items) > 20:
        frappe.throw("20 items max.")
    reason = (reason or "").strip()
    if isinstance(returning, str):
        returning = _json.loads(returning)
    doc = frappe.get_doc("Sales Exchange", name)
    _fill_returning(doc, returning)
    resolved, unpriced = _fill_items(doc, items)
    _apply_money(doc, reason)
    doc.run_method("validate")
    codes = [r["code"] for r in resolved]
    if codes:
        from logistics_portal.api.picking import availability
        _t, _r, free = availability(codes, scope="sell")
        for r in resolved:
            r["avail"] = float(free(doc.sales_order or "", r["code"]) or 0)
    return {"name": name, "reason": reason, "items": resolved,
            "unpriced": sorted(set(unpriced)),
            "originalTotal": float(doc.original_total or 0),
            "exchangeTotal": float(doc.exchange_total or 0),
            "fee": float(doc.taxes_and_shipping_total or 0),
            "difference": float(doc.difference_amount or 0),
            "direction": doc.settlement_direction or ""}


@frappe.whitelist()
def set_items(name, items=None, reason=None, city=None, sector=None,
              address=None, phone=None, returning=None):
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
    from logistics_portal.api.tickets import _cs_settings
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
    if isinstance(returning, str):
        returning = _json.loads(returning)
    _fill_returning(doc, returning)
    resolved, unpriced = _fill_items(doc, items)
    for field, val in (("exchange_city", city), ("exchange_sector", sector),
                       ("exchange_address", address), ("customer_phone", phone)):
        if val and str(val).strip():
            doc.set(field, str(val).strip())
    if doc.meta.has_field("custom_reason"):
        doc.set("custom_reason", reason)
    # A swap the CUSTOMER pays for is the one case where a missing price
    # becomes a number we quote them. On our own mistakes the offset row
    # closes the gap whatever the rate is, so an unpriced row is harmless
    # there; here it would show the wrong difference and be collected.
    if unpriced and (_cs_settings().get("reasonFee") or {}).get(reason):
        frappe.throw(
            "No price on file for " + ", ".join(sorted(set(unpriced))[:5])
            + " — type the rate, because this reason makes the customer pay "
              "the difference and it would be quoted wrong.")
    _apply_money(doc, reason)
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "name": name, "reason": reason,
            "originalTotal": float(doc.original_total or 0),
            "exchangeTotal": float(doc.exchange_total or 0),
            "fee": float(doc.taxes_and_shipping_total or 0),
            "difference": float(doc.difference_amount or 0),
            "direction": doc.settlement_direction or ""}


# Which field changes are worth a line in the history, and what to call them.
# Everything else a save touches (modified, label urls, tracking company) is
# the same event repeated and would bury the four that matter.
_EVENTS = {
    "exchange_status": "status",
    "custom_reason": "reason",
    "new_awb": "label",
    "exchange_sales_order": "replacement",
    "settlement_status": "settlement",
    "exchange_city": "city",
    "customer_phone": "phone",
    "difference_amount": "money",
}


@frappe.whitelist()
def details(name):
    """Everything about one exchange that the row cannot fit, plus its history.

    THE ORIGINAL ORDER'S LINES COME FROM THE ORDER, so the picker can offer
    every line the customer bought — including ones already excluded from
    what is coming back. The doctype's own `original_items` is the SELECTION
    (what the van collects), returned separately as `coming`.

    The history is built from Version rows, which carry (field, old, new) and
    the person who saved: 2,996 of them across the site, never surfaced
    anywhere in the portal until now. Comments are merged in, and the row
    the document was born on is the first entry.
    """
    import json as _json
    _gate()
    name = (name or "").strip()
    if not frappe.db.exists("Sales Exchange", name):
        frappe.throw("Unknown exchange.")
    doc = frappe.get_doc("Sales Exchange", name)

    has = []
    if doc.sales_order:
        has = [{"code": r.item_code, "name": r.item_name or r.item_code,
                "qty": float(r.qty or 0), "rate": float(r.rate or 0),
                "image": (r.image or "").strip(), "sku": (r.sku or "").strip()}
               for r in frappe.db.sql(
                   """SELECT soi.item_code, soi.item_name, soi.qty, soi.rate,
                             it.image, it.custom_sku AS sku
                      FROM `tabSales Order Item` soi
                      LEFT JOIN `tabItem` it ON it.name = soi.item_code
                      WHERE soi.parent = %s ORDER BY soi.idx""",
                   (doc.sales_order,), as_dict=True)]
    # What is already marked as coming back, so reopening the panel shows the
    # choice that was made rather than an empty form.
    coming = [{"code": r.item_code, "qty": float(r.qty or 0)}
              for r in (doc.get("original_items") or [])]
    sending = [{"code": r.item_code, "name": r.item_name or r.item_code,
                "qty": float(r.qty or 0), "rate": float(r.rate or 0)}
               for r in (doc.get("exchange_items") or [])]
    charges = [{"label": (r.description or "").strip() or r.account_head,
                "amount": float(r.tax_amount or 0)}
               for r in (doc.get("taxes") or [])]

    events = [{"at": str(doc.creation)[:16], "who": (doc.owner or "").split("@")[0],
               "what": "created", "detail": doc.sales_order or ""}]
    for v in frappe.db.sql(
            """SELECT owner, creation, data FROM `tabVersion`
               WHERE ref_doctype = 'Sales Exchange' AND docname = %s
               ORDER BY creation""", (name,), as_dict=True):
        try:
            payload = _json.loads(v.data or "{}")
        except ValueError:
            continue
        who, at = (v.owner or "").split("@")[0], str(v.creation)[:16]
        for ch in (payload.get("changed") or []):
            # Length-checked rather than unpacked: this is a history panel, and
            # one malformed Version row out of 2,996 must not 500 the request
            # that shows the other 2,995.
            if not isinstance(ch, (list, tuple)) or len(ch) < 3:
                continue
            field, old, new = ch[0], ch[1], ch[2]
            if field not in _EVENTS:
                continue
            events.append({"at": at, "who": who, "what": _EVENTS[field],
                           "detail": f"{old or '—'} → {new or '—'}"[:90]})
        added = [a for a in (payload.get("added") or [])
                 if a and a[0] == "exchange_items"]
        if added:
            events.append({"at": at, "who": who, "what": "items",
                           "detail": ", ".join(
                               str((a[1] or {}).get("item_code") or "") for a in added)[:90]})
    for c in frappe.db.sql(
            """SELECT owner, creation, content FROM `tabComment`
               WHERE reference_doctype = 'Sales Exchange' AND reference_name = %s
                 AND comment_type = 'Comment' ORDER BY creation""",
            (name,), as_dict=True):
        events.append({"at": str(c.creation)[:16], "who": (c.owner or "").split("@")[0],
                       "what": "note", "detail": (c.content or "")[:160]})
    events.sort(key=lambda e: e["at"])

    return {
        "name": name, "order": doc.sales_order or "",
        "exOrder": doc.exchange_sales_order or "",
        "has": has, "coming": coming, "sending": sending, "charges": charges,
        "originalTotal": float(doc.original_total or 0),
        "exchangeTotal": float(doc.exchange_total or 0),
        "difference": float(doc.difference_amount or 0),
        "direction": doc.settlement_direction or "",
        "settlement": doc.settlement_status or "",
        "address": (doc.exchange_address or "").strip(),
        "sector": (doc.exchange_sector or "").strip(),
        "old": {"awb": doc.old_awb or "", "url": doc.old_tracking_url or "",
                "label": doc.old_label_url or "",
                "company": doc.old_tracking_company or ""},
        "new": {"awb": doc.new_awb or "", "url": doc.new_tracking_url or "",
                "label": doc.new_label_url or "",
                "company": doc.new_tracking_company or ""},
        "events": events,
    }


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
