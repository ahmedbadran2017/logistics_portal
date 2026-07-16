"""Contact Center — Lane 1: order confirmation.

The WhatsApp automation stays first-line (it confirms ~85% of orders as
Administrator); this workspace is for the TAIL the automation can't close:
new Pending orders, Did-not-Answer retries, Follow Ups and On Holds — worked
by named agents (role `confirmation`) with an attempt counter, a next-call
time, and a per-agent trail, instead of the shared Administrator desk login.

Lane 2 (post-ship rescue) and Lane 3 (CS tickets) plug into the same
customer-card model later.
"""

import frappe
from frappe.utils import add_to_date, now_datetime

# The queues this lane owns. Orders leave the lane on Confirm/Cancel.
QUEUES = {
    "pending": "Pending",
    "dna": "Did not Answer",
    "followup": "Follow Up",
    "onhold": "On Hold",
}
# Where an order GOES when the lane is done with it. The agent has to be able
# to look at their own decisions — to check one, to answer "what did I do with
# this customer", to catch a mistake — so every terminal state is a tab too,
# not a black hole the order falls into.
DONE_QUEUES = {
    "confirmed": "Confirmed",
    "cancelled": "Cancelled",
    "duplicated": "Duplicated",
}
_ACTIONS = {
    "confirm": "Confirmed",
    "dna": "Did not Answer",
    "followup": "Follow Up",
    "onhold": "On Hold",
    "cancel": "Cancelled",
    # Desk parity: agents mark ~23 duplicate orders a month there.
    "duplicate": "Duplicated",
    # Undo: pull a wrongly-decided order back into the pending queue.
    "reopen": "Pending",
}
# How long an order rests before it resurfaces at the top of its queue.
_RETRY_HOURS = {"dna": 4, "followup": 24, "onhold": 48}

# Money above this is not a Moroccan COD order, it is a typo or seed data.
# Measured: the average real order is 233 MAD and every one of the 247,409
# orders under 10k sums to 57.6M — while SEVEN rows (Turkish seed data, e.g.
# SAL-ORD-2025-00942 at 489,990,000,000) carry 930 BILLION between them, some
# of them sitting in the live Pending queue. Any total that includes them is
# off by four orders of magnitude. Excluded from sums and COUNTED, never
# silently dropped.
_SANE_MAX = 100000

# The city lives on the linked Address, not the order: custom_shipping_city is
# filled on 2,167 of 247,500 orders (0.9%), the Address on 99.9%.
_CITY = ("COALESCE(NULLIF(TRIM(so.custom_shipping_city), ''), "
         "NULLIF(TRIM(addr.city), ''))")
_CITY_JOIN = ("LEFT JOIN `tabAddress` addr ON addr.name = "
              "COALESCE(so.shipping_address_name, so.customer_address)")


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("confirmation", "manager"):
        frappe.throw("Not authorized for the confirmation workspace.",
                     frappe.PermissionError)
    return role


# The customer key, identical to customers.py: digits only, last 9.
_CUST_KEY = ("RIGHT(REGEXP_REPLACE(COALESCE(NULLIF(so.custom_customer_phone, ''),"
             " so.custom_shipping_phone), '[^0-9]', ''), 9)")


def _range(days, frm, to):
    """The window the board looks at.

    `days` is the rolling default the tabs are counted on. An explicit
    from/to overrides it — the manager reviewing last month's cancels needs a
    calendar range, not "the last N days from right now".
    Returns (sql_condition_template, extra_vals) where the template takes a
    {col} placeholder so each tab can point it at its own date column.
    """
    import re as _re
    ok = lambda d: bool(d and _re.match(r"^\d{4}-\d{2}-\d{2}$", str(d).strip()))
    if ok(frm) or ok(to):
        conds, v = [], {}
        if ok(frm):
            conds.append("{col} >= %(frm)s")
            v["frm"] = str(frm).strip() + " 00:00:00"
        if ok(to):
            conds.append("{col} <= %(to)s")
            v["to"] = str(to).strip() + " 23:59:59"
        return " AND ".join(conds), v
    days = min(max(int(days or 30), 1), 365)
    return "{col} >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)", {"days": days}


@frappe.whitelist()
def board(tab="pending", days=30, q="", limit=30, offset=0, frm=None, to=None):
    """The queues + counts + my day so far, one call."""
    role = _gate()
    if tab not in QUEUES and tab not in DONE_QUEUES and tab != "monitor":
        tab = "pending"
    days = min(max(int(days or 30), 1), 365)
    limit = min(max(int(limit or 30), 1), 100)
    offset = max(int(offset or 0), 0)
    rng, rng_vals = _range(days, frm, to)
    custom_range = "frm" in rng_vals or "to" in rng_vals
    vals = {"days": days, "limit": limit, "offset": offset, **rng_vals}

    # Each family of tabs is dated by its OWN column: the working queues by
    # when the order arrived, the done tabs by when the decision was taken.
    q_rng = rng.format(col="creation")
    # NB: strictly custom_last_call_at — the column only a human decision
    # through this workspace sets. The WhatsApp automation confirms ~85% of
    # orders without ever touching it, so a COALESCE(..., modified) fallback
    # put 167,046 automation-confirmed orders in the agent's "Confirmed" tab.
    # These tabs answer "what did WE decide", and the search box still reaches
    # any order.
    d_rng = "custom_last_call_at IS NOT NULL AND " + rng.format(col="custom_last_call_at")

    # Seed the DONE tabs too: the board increments these optimistically
    # after an action, and a window with no prior decisions would leave
    # them absent -> `undefined++` -> NaN in the tab badge.
    counts = {k: 0 for k in list(QUEUES) + list(DONE_QUEUES)}
    for r in frappe.db.sql(
            f"""SELECT custom_sales_status s, COUNT(*) n FROM `tabSales Order`
                WHERE docstatus = 1 AND custom_sales_status IN %(sts)s
                  AND {q_rng}
                GROUP BY custom_sales_status""",
            {"sts": tuple(QUEUES.values()), **rng_vals}, as_dict=True):
        for k, v in QUEUES.items():
            if v == r.s:
                counts[k] = int(r.n or 0)
    # Done tabs: keyed on when the DECISION was taken (custom_last_call_at),
    # not when the order arrived — the agent looks for "what I did today",
    # and a 40-day-old order confirmed an hour ago has to be in reach.
    for r in frappe.db.sql(
            f"""SELECT custom_sales_status s, COUNT(*) n FROM `tabSales Order`
                WHERE docstatus = 1 AND custom_sales_status IN %(sts)s
                  AND {d_rng}
                GROUP BY custom_sales_status""",
            {"sts": tuple(DONE_QUEUES.values()), **rng_vals}, as_dict=True):
        for k, v in DONE_QUEUES.items():
            if v == r.s:
                counts[k] = int(r.n or 0)

    # Monitoring: live orders whose customer has taken 2+ parcels and kept
    # none of them. Nothing is blocked — the team looks and decides. Measured:
    # this group still takes delivery 27% of the time.
    from logistics_portal.api.customers import risky_phones
    risky = tuple(risky_phones()) or ("",)
    counts["monitor"] = int(frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.custom_sales_status IN %(sts)s
              AND {_CUST_KEY} IN %(risky)s""",
        {"sts": tuple(QUEUES.values()), "risky": risky})[0][0])

    if tab == "monitor":
        conds = ["so.docstatus = 1", "so.custom_sales_status IN %(statuses)s",
                 f"{_CUST_KEY} IN %(risky)s"]
        vals["statuses"] = tuple(QUEUES.values())
        vals["risky"] = risky
    elif tab in DONE_QUEUES:
        conds = ["so.docstatus = 1", "so.custom_sales_status = %(status)s",
                 "so.custom_last_call_at IS NOT NULL",
                 rng.format(col="so.custom_last_call_at")]
        vals["status"] = DONE_QUEUES[tab]
    else:
        conds = ["so.docstatus = 1", "so.custom_sales_status = %(status)s",
                 rng.format(col="so.creation")]
        vals["status"] = QUEUES[tab]
    if q and str(q).strip():
        vals["q"] = f"%{str(q).strip()}%"
        conds.append("""(so.name LIKE %(q)s OR so.customer_name LIKE %(q)s
                        OR so.custom_customer_phone LIKE %(q)s
                        OR so.custom_shipping_phone LIKE %(q)s)""")
    where = " AND ".join(conds)
    total = frappe.db.sql(f"SELECT COUNT(*) FROM `tabSales Order` so WHERE {where}",
                          vals)[0][0]
    # Retry queues surface what's DUE first (next_call in the past, oldest
    # deferral first); pending is simply oldest-first.
    if tab in DONE_QUEUES:
        order_by = "so.custom_last_call_at DESC"  # newest decision first
    elif tab in ("pending", "monitor"):
        order_by = "so.creation"
    else:
        order_by = "COALESCE(so.custom_next_call_at, so.creation), so.creation"
    # custom_cancellation_reason is the desk's field — absent on sites that
    # never had it, so only select it when the meta says it exists.
    _m = frappe.get_meta("Sales Order")
    reason_col = ("so.custom_cancellation_reason"
                  if _m.has_field("custom_cancellation_reason") else "NULL")
    if not _m.has_field("custom_first_reminder"):
        # A site without the WhatsApp automation's ladder.
        s_r1 = s_r2 = "0"
    else:
        s_r1, s_r2 = "so.custom_first_reminder", "so.custom_second_reminder"
    rows = frappe.db.sql(
        f"""SELECT so.name, so.customer_name AS customer, so.grand_total AS total,
                   COALESCE(NULLIF(so.custom_customer_phone,''),
                            so.custom_shipping_phone) AS phone,
                   {_CITY} AS city,
                   so.custom_items_count AS item_count,
                   TIMESTAMPDIFF(HOUR, so.creation, NOW()) AS age_h,
                   COALESCE(so.custom_call_attempts, 0) AS attempts,
                   so.custom_last_call_at AS last_call,
                   so.custom_next_call_at AS next_call,
                   so.custom_allocated_to AS agent,
                   so.custom_sales_status AS status,
                   COALESCE({s_r1}, 0) AS r1,
                   COALESCE({s_r2}, 0) AS r2,
                   {reason_col} AS reason
            FROM `tabSales Order` so {_CITY_JOIN}
            WHERE {where}
            ORDER BY {order_by}
            LIMIT %(limit)s OFFSET %(offset)s""", vals, as_dict=True)

    # What's IN each order — the agent reads it to the customer on the call.
    items_text = {}
    if rows:
        for parent, txt in frappe.db.sql(
                """SELECT parent,
                          GROUP_CONCAT(CONCAT(CAST(qty AS UNSIGNED), '× ', item_name)
                                       ORDER BY idx SEPARATOR ' · ')
                   FROM `tabSales Order Item` WHERE parent IN %s
                   GROUP BY parent""", (tuple(r.name for r in rows),)):
            items_text[parent] = (txt or "")[:240]

    # Who is this customer? One batched lookup for the page — the agent sees
    # the verdict BEFORE the call, not after the parcel comes back.
    from logistics_portal.api.customers import digits, history_for
    hist = history_for([r.phone for r in rows if r.phone]) if rows else {}

    sla_h = _cf_settings().get("slaFirstCallH", 6)

    today = str(now_datetime())[:10]
    mine = {"confirm": 0, "cancel": 0, "dna": 0, "followup": 0, "onhold": 0,
            "duplicate": 0}
    for r in frappe.db.sql(
            """SELECT c.content, COUNT(*) n FROM `tabComment` c
               WHERE c.reference_doctype = 'Sales Order' AND c.owner = %s
                 AND c.creation >= %s AND c.content LIKE 'Confirmation: %%'
               GROUP BY c.content""",
            (frappe.session.user, f"{today} 00:00:00"), as_dict=True):
        for k in mine:
            if r.content.startswith(f"Confirmation: {k}"):
                mine[k] += int(r.n or 0)

    cf_s = _cf_settings()
    my_total = sum(mine.values())
    points = None
    try:
        from logistics_portal.api.contact_center import (bonus_group_for,
                                                         bonus_points_for)
        from frappe.utils import nowdate
        points = bonus_points_for(frappe.session.user,
                                  bonus_group_for(role), nowdate()[:7])
    except Exception:
        pass

    return {
        "tab": tab, "counts": counts, "total": int(total or 0),
        "myTotal": my_total, "myTarget": int(cf_s.get("dayTarget", 40)),
        "points": points,
        "rows": [{
            "order": r.name, "customer": r.customer or "",
            "total": float(r.total or 0), "phone": (r.phone or "").strip(),
            # NB: the alias is item_count, NOT `items` — on a frappe._dict row
            # `r.items` resolves to the dict METHOD and int(method) TypeErrors
            # (same trap that blanked the Settings zones panel once).
            "city": (r.city or "").strip().title(), "items": int(r.item_count or 1),
            "itemsText": items_text.get(r.name, ""),
            "ageH": int(r.age_h or 0), "attempts": int(r.attempts or 0),
            "lastCall": str(r.last_call)[:16] if r.last_call else "",
            "nextCall": str(r.next_call)[:16] if r.next_call else "",
            "agent": (r.agent or "").split("@")[0],
            "due": bool(r.next_call and str(r.next_call) <= str(now_datetime())),
            "status": r.status or "",
            "reason": (r.reason or "").strip(),
            "cust": hist.get(digits(r.phone)) if r.phone else None,
            # How hard the automation already chased this one.
            "chased": int(r.r2 or 0) and 2 or (int(r.r1 or 0) and 1 or 0),
            # First-call SLA: never touched and older than the target. Only
            # meaningful while the order is still ours to call.
            "slaBreached": bool(tab not in DONE_QUEUES
                                and int(r.attempts or 0) == 0
                                and int(r.age_h or 0) > sla_h),
        } for r in rows],
        "mine": mine,
        "reasons": _cf_settings().get("reasons", []),
        "serverNow": str(now_datetime())[:19],
    }


@frappe.whitelist()
def act(order, action, note=None):
    """One call decision. confirm → enters the logistics pool; cancel needs a
    reason; dna/followup/onhold re-queue with a retry time and bump the
    attempt counter."""
    role = _gate()
    order = (order or "").strip()
    if action not in _ACTIONS:
        frappe.throw("Unknown action.")
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    so = frappe.db.get_value(
        "Sales Order", order,
        ["docstatus", "custom_sales_status", "custom_call_attempts"], as_dict=True)
    if so.docstatus != 1:
        frappe.throw("Order is not submitted.")
    if so.custom_sales_status not in QUEUES.values():
        # Reopening a decision the lane already took: allowed only while the
        # order hasn't moved on physically. Once it's picked or shipped, the
        # warehouse owns it and a status flip here would lie about reality.
        if so.custom_sales_status not in DONE_QUEUES.values():
            frappe.throw(f"Order is {so.custom_sales_status or 'unset'} — outside the "
                         "confirmation lane. Refresh the queue.")
        if action != "reopen":
            frappe.throw(f"Order is already {so.custom_sales_status}. Reopen it "
                         "first if the decision was wrong.")
        stage = frappe.db.get_value("Sales Order", order, "custom_logistics_status")
        if stage and stage not in ("Pending", ""):
            frappe.throw(f"Can't reopen — the order is already {stage} in the "
                         "warehouse.")
        if frappe.db.exists("Pick List Item", {"sales_order": order, "docstatus": ["<", 2]}):
            frappe.throw("Can't reopen — the order is already on a pick list.")
    elif action == "reopen":
        frappe.throw("The order is already in the queue.")
    note = (note or "").strip()
    if action == "cancel":
        if not note:
            frappe.throw("A cancel needs a reason.")
        opts = reason_options()
        if opts and note not in opts:
            frappe.throw("Pick a reason from the list — free text here would "
                         "invent a category the reports can't group.")

    now = now_datetime()
    attempts = int(so.custom_call_attempts or 0)
    updates = {
        "custom_sales_status": _ACTIONS[action],
        "custom_allocated_to": frappe.session.user,
        "custom_last_call_at": now,
    }
    if action in _RETRY_HOURS:
        attempts += 1
        updates["custom_call_attempts"] = attempts
        s = _cf_settings()
        hours = {"dna": s["retryDna"], "followup": s["retryFollowup"],
                 "onhold": s["retryOnhold"]}[action]
        updates["custom_next_call_at"] = add_to_date(now, hours=hours)
    else:
        updates["custom_next_call_at"] = None
    if action == "cancel" and frappe.get_meta("Sales Order").has_field(
            "custom_cancellation_reason"):
        # Validated against the Select above, so the desk's reports and the
        # existing dashboard group portal cancels alongside desk ones.
        updates["custom_cancellation_reason"] = note
    frappe.db.set_value("Sales Order", order, updates, update_modified=True)

    doc = frappe.get_doc("Sales Order", order)
    doc.add_comment("Comment",
                    f"Confirmation: {action}"
                    + (f" (attempt {attempts})" if action in _RETRY_HOURS else "")
                    + (f" — {note}" if note else "")
                    + f" · by {frappe.session.user}")
    frappe.db.commit()
    if action in ("confirm", "cancel", "reopen"):
        # This customer's counts just moved.
        try:
            from logistics_portal.api.customers import bust
            bust(frappe.db.get_value("Sales Order", order, "custom_customer_phone")
                 or frappe.db.get_value("Sales Order", order, "custom_shipping_phone"))
        except Exception:
            pass
        # The order entered / left the logistics pool.
        for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
            frappe.cache().delete_value(k)
        frappe.cache().delete_keys("lp_suggest")
    return {"ok": True, "order": order, "action": action, "attempts": attempts}


@frappe.whitelist()
def bulk_act(orders=None, action=None, reason=None):
    """Mark a batch duplicate, or undo a batch of decisions.

    Deliberately NOT here: bulk confirm. A confirmation asserts the customer
    said yes on a call — there is no honest way to assert that for 50 rows at
    once, and every downstream number (confirm rate, bonus, the picking pool)
    would inherit the lie.
    """
    import json as _json
    _gate()
    if not _is_cf_admin():
        frappe.throw("Only the portal manager or a confirmation section admin "
                     "can act in bulk.", frappe.PermissionError)
    if action not in ("duplicate", "reopen"):
        frappe.throw("Unknown bulk action.")
    if isinstance(orders, str):
        orders = _json.loads(orders)
    orders = [str(x).strip() for x in (orders or []) if str(x).strip()]
    if not orders:
        frappe.throw("Nothing selected.")
    if len(orders) > 200:
        frappe.throw("200 orders max per batch.")
    reason = (reason or "").strip()
    done, skipped = [], []
    for name in orders:
        try:
            # Reuse the single-order path: it owns the reopen guards (a picked
            # order can't be pulled back) and writes the same comment trail.
            act(name, action, reason)
            done.append(name)
        except Exception:
            skipped.append(name)
            frappe.db.rollback()
    frappe.db.commit()
    return {"ok": True, "done": len(done), "skipped": skipped}


@frappe.whitelist()
def bulk_cancel(orders=None, reason=None):
    """Expire a slice of the confirmation backlog in one move. Section
    admins/manager only — one reason applies to the whole batch."""
    import json as _json
    _gate()
    if not _is_cf_admin():
        frappe.throw("Only the portal manager or a confirmation section admin "
                     "can bulk-cancel.", frappe.PermissionError)
    if isinstance(orders, str):
        orders = _json.loads(orders)
    orders = [str(x).strip() for x in (orders or []) if str(x).strip()]
    if not orders:
        frappe.throw("Nothing selected.")
    if len(orders) > 200:
        frappe.throw("200 orders max per batch.")
    reason = (reason or "").strip()
    if not reason:
        frappe.throw("A bulk cancel needs a reason.")
    opts = reason_options()
    if opts and reason not in opts:
        frappe.throw("Pick a reason from the list.")
    now = now_datetime()
    has_reason_field = frappe.get_meta("Sales Order").has_field(
        "custom_cancellation_reason")
    done, skipped = [], []
    for name in orders:
        so = frappe.db.get_value(
            "Sales Order", name, ["docstatus", "custom_sales_status"], as_dict=True)
        if not so or so.docstatus != 1 or so.custom_sales_status not in QUEUES.values():
            skipped.append(name)
            continue
        updates = {"custom_sales_status": "Cancelled",
                   "custom_allocated_to": frappe.session.user,
                   "custom_last_call_at": now, "custom_next_call_at": None}
        if has_reason_field:
            updates["custom_cancellation_reason"] = reason
        frappe.db.set_value("Sales Order", name, updates, update_modified=True)
        frappe.get_doc("Sales Order", name).add_comment(
            "Comment", f"Confirmation: cancel — {reason} · bulk by {frappe.session.user}")
        done.append(name)
    frappe.db.commit()
    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
        frappe.cache().delete_value(k)
    frappe.cache().delete_keys("lp_suggest")
    return {"ok": True, "done": len(done), "skipped": skipped}


@frappe.whitelist()
def update_contact(order, phone=None, city=None):
    """Fix the customer's phone / city before confirming — the #1 reason
    deliveries fail later. Logged old → new on the order."""
    _gate()
    order = (order or "").strip()
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    phone = (phone or "").strip()
    city = (city or "").strip()
    if not phone and not city:
        frappe.throw("Nothing to update.")
    old = frappe.db.get_value(
        "Sales Order", order,
        ["custom_customer_phone", "custom_shipping_phone", "custom_shipping_city"],
        as_dict=True)
    updates, log = {}, []
    if phone:
        updates["custom_customer_phone"] = phone
        old_phone = old.custom_customer_phone or old.custom_shipping_phone or "—"
        if old_phone != phone:
            log.append(f"phone {old_phone} → {phone}")
    if city:
        updates["custom_shipping_city"] = city
        if (old.custom_shipping_city or "—") != city:
            log.append(f"city {old.custom_shipping_city or '—'} → {city}")
    if not log:
        return {"ok": True, "unchanged": True}
    frappe.db.set_value("Sales Order", order, updates, update_modified=True)
    frappe.get_doc("Sales Order", order).add_comment(
        "Comment", "Contact updated: " + "; ".join(log) + f" · by {frappe.session.user}")
    frappe.db.commit()
    # The phone IS the customer identity (_CUST_KEY). Correcting a typo moves
    # this order between two customers, so BOTH cached histories are now wrong:
    # the old key still counts an order that left it, and the new one doesn't
    # count the one that arrived. Bust both, not just the new number.
    if "custom_customer_phone" in updates:
        from logistics_portal.api.customers import bust
        for ph in (updates["custom_customer_phone"], old.custom_customer_phone,
                   old.custom_shipping_phone):
            if ph:
                bust(ph)
    return {"ok": True, "updated": log}


# ── Section administration: settings + reports, gated to the portal manager
# OR designated section admins (a team lead can run her section without
# portal-wide manager powers). Same pattern will serve lanes 2 and 3.
_CF_KEY = "lp_cf_settings"
_CF_DEFAULTS = {
    "retryDna": 4,        # hours before a Did-not-Answer resurfaces
    "retryFollowup": 24,
    "retryOnhold": 48,
    "slaFirstCallH": 6,   # a Pending order untouched longer than this is late
    "dayTarget": 40,      # decisions per agent per day — NOT the floor's
                          # dayTarget (200 on production: that counts orders
                          # picked in a warehouse, not calls made at a desk)
    # `reasons` is the manager's QUICK-PICK subset of the real vocabulary —
    # never a list of our own words. The vocabulary itself lives on the Select
    # field custom_cancellation_reason (15 options the desk, the existing
    # dashboard and every historical report already group by). Empty = show
    # them all.
    "reasons": [],
    "admins": [],         # section admins (user emails)
}


def _cf_settings():
    import json as _json
    raw = frappe.db.get_default(_CF_KEY)
    out = dict(_CF_DEFAULTS)
    if raw:
        try:
            saved = _json.loads(raw)
            if isinstance(saved, dict):
                out.update({k: saved[k] for k in _CF_DEFAULTS if k in saved})
        except Exception:
            pass
    return out


def reason_options():
    """The cancellation vocabulary, straight off the Select field. Writing
    anything else invents a junk category in every report that groups by it."""
    f = frappe.get_meta("Sales Order").get_field("custom_cancellation_reason")
    if not f or not f.options:
        return []
    return [o.strip() for o in f.options.split("\n") if o.strip()]


def _is_cf_admin():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) == "manager":
        return True
    return frappe.session.user in _cf_settings().get("admins", [])


@frappe.whitelist()
def cf_settings():
    _gate()
    s = _cf_settings()
    opts = reason_options()
    return {**s, "canEdit": _is_cf_admin(), "reasonOptions": opts,
            # No subset chosen = the whole vocabulary.
            "reasons": [r for r in (s.get("reasons") or []) if r in opts] or opts}


@frappe.whitelist()
def save_cf_settings(settings=None):
    """Section settings — portal manager or a designated section admin."""
    import json as _json
    _gate()
    if not _is_cf_admin():
        frappe.throw("Only the portal manager or a confirmation section admin "
                     "can change these settings.", frappe.PermissionError)
    if isinstance(settings, str):
        settings = _json.loads(settings)
    settings = settings or {}
    out = dict(_cf_settings())
    for k in ("retryDna", "retryFollowup", "retryOnhold", "slaFirstCallH"):
        if k in settings:
            v = int(settings[k])
            if not (1 <= v <= 168):
                frappe.throw(f"{k} must be between 1 and 168 hours.")
            out[k] = v
    if "dayTarget" in settings:
        v = int(settings["dayTarget"])
        if not (1 <= v <= 500):
            frappe.throw("dayTarget must be between 1 and 500 decisions.")
        out["dayTarget"] = v
    if "reasons" in settings:
        opts = reason_options()
        reasons = [str(r).strip() for r in (settings["reasons"] or []) if str(r).strip()]
        bad = [r for r in reasons if r not in opts]
        if bad:
            frappe.throw("Not a cancellation reason on the Sales Order: "
                         + ", ".join(bad[:3])
                         + ". The list comes from the field itself — add it "
                           "there first if it's genuinely new.")
        if not reasons:
            frappe.throw("Keep at least one cancel reason.")
        out["reasons"] = reasons
    if "admins" in settings:
        from logistics_portal.api.auth import resolve_role
        if resolve_role(frappe.session.user) != "manager":
            frappe.throw("Only the portal manager can change section admins.",
                         frappe.PermissionError)
        admins = [str(a).strip().lower() for a in (settings["admins"] or []) if str(a).strip()]
        for a in admins:
            if not frappe.db.exists("User", a):
                frappe.throw(f"Unknown user: {a}")
        out["admins"] = admins[:10]
    frappe.db.set_default(_CF_KEY, _json.dumps(out))
    frappe.db.commit()
    return {"ok": True, **out}


@frappe.whitelist()
def report(days=7, frm=None, to=None):
    """The section's report. Manager or section admin.

    Everything here is counted from the SAME sources the desk's own
    confirmation dashboard uses, so the two can never disagree:
      - decisions from the Comment trail this workspace writes
      - the agent from custom_allocated_to (the field the company runs on)
      - cancel reasons from custom_cancellation_reason (the Select)
      - revenue split into CONFIRMED vs actually COLLECTED — a confirm that
        comes back as a refused parcel is not revenue, and the old dashboard's
        single "Revenue" column couldn't tell the difference.
    """
    _gate()
    if not _is_cf_admin():
        frappe.throw("Only the portal manager or a section admin can open the "
                     "section report.", frappe.PermissionError)
    days = min(max(int(days or 7), 1), 365)
    rng, rng_vals = _range(days, frm, to)
    # Two windows, on purpose — the desk's own dashboard learned this too
    # ("Agents Leaderboard" vs "Agent Performance (By Order Creation Date)"):
    #   c_rng   ACTIVITY: decisions taken in the period. Answers "what did the
    #           team do this week".
    #   so_rng  COHORT: orders that ARRIVED in the period. Answers "of the work
    #           that came in, how much turned into money".
    # A window on `modified` would answer neither: it sweeps in every order
    # merely touched, and inflated a single agent to 33,651 orders in 30 days.
    c_rng = rng.format(col="c.creation")
    so_rng = rng.format(col="so.creation")

    # ── per-agent decisions, from the trail ──────────────────────────────
    per_agent = {}
    for r in frappe.db.sql(
            f"""SELECT c.owner, c.content, COUNT(*) n FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order'
                  AND c.content LIKE 'Confirmation: %%' AND {c_rng}
                GROUP BY c.owner, c.content""", rng_vals, as_dict=True):
        bulk = "(bulk)" in r.content or " bulk " in r.content
        action = (r.content.split("Confirmation: ", 1)[1] or "").split(" ", 1)[0]
        action = action.strip("()—- ")
        a = per_agent.setdefault(r.owner, {"confirm": 0, "cancel": 0, "dna": 0,
                                           "followup": 0, "onhold": 0,
                                           "duplicate": 0, "reopen": 0,
                                           "bulk": 0})
        if action in a:
            a[action] += int(r.n or 0)
        if bulk:
            a["bulk"] += int(r.n or 0)

    # ── per-agent money, on the COHORT of orders that arrived in the window.
    # NB: `collected` is the money that actually reached us — a confirm whose
    # parcel comes back refused is not revenue, and the desk dashboard's single
    # "Revenue" column cannot tell the two apart. `leak` is deliberately NOT
    # computed per agent: an order confirmed but never shipped is usually the
    # warehouse or the clock, not the agent, and blaming them for it would be
    # a lie with their bonus attached. stickRate (delivered / shipped) is the
    # part they own. ─────────────────────────────────────────────────────
    # Two queries, not one, and both at ORDER grain. The single query this
    # replaces LEFT JOINed Delivery Note Item, which fans out one row PER LINE
    # — so a 3-item order counted 3 orders, 3 confirms and 3× its grand_total.
    # Every money number on this report was weighted by basket size. An order
    # with no DN produced one row and stayed honest, which is exactly why it
    # was invisible: the error grew with how well the order shipped.
    money = {}
    for r in frappe.db.sql(
            f"""SELECT so.custom_allocated_to u,
                       COUNT(*) orders,
                       SUM(so.custom_sales_status = 'Confirmed') confirmed,
                       SUM(CASE WHEN so.custom_sales_status = 'Confirmed'
                                     AND so.grand_total <= %(sane)s
                                THEN so.grand_total ELSE 0 END) confirmed_value,
                       AVG(CASE WHEN so.custom_last_call_at IS NOT NULL
                                THEN TIMESTAMPDIFF(MINUTE, so.creation,
                                                   so.custom_last_call_at) END) resp_min,
                       AVG(COALESCE(so.custom_call_attempts, 0)) attempts
                FROM `tabSales Order` so
                WHERE so.docstatus = 1 AND COALESCE(so.custom_allocated_to,'') != ''
                  AND {so_rng}
                GROUP BY u""", {"sane": _SANE_MAX, **rng_vals}, as_dict=True):
        money[r.u] = dict(r)

    # Outcome + collected cash. Collapsed to one row per ORDER first: an order
    # that failed once and landed on the redelivery is delivered, not both.
    for r in frappe.db.sql(
            f"""SELECT u, SUM(is_del) delivered, SUM(is_fail AND NOT is_del) failed,
                       SUM(CASE WHEN is_del AND gt <= %(sane)s THEN gt ELSE 0 END) collected
                FROM (SELECT so.custom_allocated_to u, so.name, so.grand_total gt,
                             MAX(dn.custom_track_shipment_status = 'Delivered') is_del,
                             MAX(dn.custom_track_shipment_status IN
                                 ('Delivery Exception', 'Failed Attempt')) is_fail
                      FROM `tabSales Order` so
                      JOIN `tabDelivery Note Item` dni
                        ON dni.against_sales_order = so.name AND dni.docstatus = 1
                      JOIN `tabDelivery Note` dn
                        ON dn.name = dni.parent AND dn.docstatus = 1
                      WHERE so.docstatus = 1 AND COALESCE(so.custom_allocated_to,'') != ''
                        AND {so_rng}
                      GROUP BY so.name) x
                GROUP BY u""", {"sane": _SANE_MAX, **rng_vals}, as_dict=True):
        money.setdefault(r.u, {}).update(
            {"delivered": r.delivered, "failed": r.failed, "collected": r.collected})

    agents = []
    for user in set(list(per_agent) + list(money)):
        a = per_agent.get(user, {"confirm": 0, "cancel": 0, "dna": 0,
                                 "followup": 0, "onhold": 0, "duplicate": 0,
                                 "reopen": 0, "bulk": 0})
        m = money.get(user) or {}
        g = lambda k: m.get(k) or 0          # money rows are plain dicts, and an
                                             # agent may appear in only one of
                                             # the two queries above.
        decided = a["confirm"] + a["cancel"]
        shipped = int(g("delivered")) + int(g("failed"))
        agents.append({
            "agent": user.split("@")[0], "user": user, **a,
            "total": a["confirm"] + a["cancel"] + a["dna"] + a["followup"]
                     + a["onhold"] + a["duplicate"],
            "confirmRate": round(a["confirm"] * 100.0 / decided, 1) if decided else None,
            "avgAttempts": round(float(g("attempts")), 1),
            # How fast the first human touch lands after the order arrives.
            "respH": round(float(g("resp_min")) / 60, 1) if g("resp_min") else None,
            "confirmedValue": round(float(g("confirmed_value"))),
            # The money that actually arrived. A confirm that bounces is not revenue.
            "collected": round(float(g("collected"))),
            "delivered": int(g("delivered")),
            "failedParcels": int(g("failed")),
            # Of what they confirmed AND shipped, how much stuck.
            "stickRate": round(int(g("delivered")) * 100.0 / shipped, 1)
                         if shipped else None,
        })
    agents.sort(key=lambda x: -x["total"])

    # ── cancel reasons, from the Select the whole company groups by ──────
    reason_rows = []
    if frappe.get_meta("Sales Order").has_field("custom_cancellation_reason"):
        reason_rows = [{"reason": r[0] or "(none)", "n": int(r[1] or 0)}
                       for r in frappe.db.sql(
            f"""SELECT COALESCE(NULLIF(so.custom_cancellation_reason, ''), '(none)'),
                       COUNT(*) n
                FROM `tabSales Order` so
                WHERE so.docstatus = 1 AND so.custom_sales_status = 'Cancelled'
                  AND {so_rng}
                GROUP BY 1 ORDER BY n DESC LIMIT 15""", rng_vals)]

    # ── day by day ───────────────────────────────────────────────────────
    funnel = frappe.db.sql(
        f"""SELECT DATE(c.creation) d,
                   SUM(c.content LIKE 'Confirmation: confirm%%') conf,
                   SUM(c.content LIKE 'Confirmation: cancel%%') canc,
                   SUM(c.content LIKE 'Confirmation: dna%%') dna
            FROM `tabComment` c
            WHERE c.reference_doctype = 'Sales Order'
              AND c.content LIKE 'Confirmation: %%' AND {c_rng}
            GROUP BY DATE(c.creation) ORDER BY d""", rng_vals, as_dict=True)

    # ── the hour of the day the work actually happens ────────────────────
    hours = {int(r[0]): int(r[1]) for r in frappe.db.sql(
        f"""SELECT HOUR(c.creation), COUNT(*) FROM `tabComment` c
            WHERE c.reference_doctype = 'Sales Order'
              AND c.content LIKE 'Confirmation: %%' AND {c_rng}
            GROUP BY HOUR(c.creation)""", rng_vals)}


    # ── the chase ladder the automation ran before we ever called ────────
    ladder = None
    if frappe.get_meta("Sales Order").has_field("custom_first_reminder"):
        ladder = frappe.db.sql(
            f"""SELECT SUM(so.custom_first_reminder = 1) r1,
                       SUM(so.custom_second_reminder = 1) r2,
                       COUNT(*) n
                FROM `tabSales Order` so
                WHERE so.docstatus = 1 AND {so_rng}""", rng_vals, as_dict=True)[0]
        ladder = {"r1": int(ladder.r1 or 0), "r2": int(ladder.r2 or 0),
                  "n": int(ladder.n or 0)}

    from logistics_portal.api.settings import get_ops
    return {
        "days": days, "frm": frm or "", "to": to or "",
        "agents": agents,
        "reasons": reason_rows,
        "funnel": [{"date": str(f.d), "confirm": int(f.conf or 0),
                    "cancel": int(f.canc or 0), "dna": int(f.dna or 0)} for f in funnel],
        "hours": [{"h": h, "n": hours.get(h, 0)}
                  for h in range(min(hours) if hours else 8,
                                 (max(hours) if hours else 20) + 1)],
        "ladder": ladder,
        "target": int(_cf_settings().get("dayTarget", 40)),
    }


@frappe.whitelist()
def dashboard(days=30, frm=None, to=None, mine=0):
    """The section's analytical view: the state of the queue RIGHT NOW and what
    it is worth — as opposed to report(), which asks who did what last week.

    Any agent may open it; `mine=1` narrows every number to their own orders,
    so the same screen answers both "how is the section doing" and "how am I
    doing inside it".
    """
    role = _gate()
    days = min(max(int(days or 30), 1), 365)
    rng, rng_vals = _range(days, frm, to)
    mine = int(mine or 0)
    me_cond = ""
    if mine:
        rng_vals["me"] = frappe.session.user
        me_cond = " AND so.custom_allocated_to = %(me)s"
    live = tuple(QUEUES.values())
    s = _cf_settings()
    sla_h = int(s.get("slaFirstCallH", 6))

    # ── the live queue: what is waiting, and what is it worth ────────────
    q = frappe.db.sql(
        f"""SELECT so.custom_sales_status st, COUNT(*) n,
                   COALESCE(SUM(CASE WHEN so.grand_total <= %(sane)s
                                     THEN so.grand_total ELSE 0 END), 0) value,
                   SUM(so.grand_total > %(sane)s) absurd,
                   SUM(TIMESTAMPDIFF(HOUR, so.creation, NOW()) > %(sla)s
                       AND COALESCE(so.custom_call_attempts, 0) = 0) late
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.custom_sales_status IN %(live)s{me_cond}
            GROUP BY st""",
        {"live": live, "sla": sla_h, "sane": _SANE_MAX, **rng_vals}, as_dict=True)
    queue = {r.st: {"n": int(r.n or 0), "value": round(float(r.value or 0)),
                    "late": int(r.late or 0)} for r in q}
    absurd = sum(int(r.absurd or 0) for r in q)

    # ── how old is the pile ──────────────────────────────────────────────
    aging = frappe.db.sql(
        f"""SELECT CASE
                     WHEN TIMESTAMPDIFF(HOUR, so.creation, NOW()) <= 6 THEN '0-6h'
                     WHEN TIMESTAMPDIFF(HOUR, so.creation, NOW()) <= 24 THEN '6-24h'
                     WHEN TIMESTAMPDIFF(HOUR, so.creation, NOW()) <= 72 THEN '1-3d'
                     WHEN TIMESTAMPDIFF(HOUR, so.creation, NOW()) <= 168 THEN '3-7d'
                     ELSE '7d+' END bucket,
                   COUNT(*) n,
                   COALESCE(SUM(CASE WHEN so.grand_total <= %(sane)s
                                     THEN so.grand_total ELSE 0 END), 0) value
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.custom_sales_status IN %(live)s{me_cond}
            GROUP BY bucket""",
        {"live": live, "sane": _SANE_MAX, **rng_vals}, as_dict=True)
    order = ["0-6h", "6-24h", "1-3d", "3-7d", "7d+"]
    ag = {r.bucket: r for r in aging}
    aging_rows = [{"bucket": b,
                   "n": int(ag[b].n or 0) if b in ag else 0,
                   "value": round(float(ag[b].value or 0)) if b in ag else 0}
                  for b in order]

    # ── WHO is waiting: the segment mix of the live queue ────────────────
    # Nothing else in the company can answer this. 6,775 customers have taken
    # 2+ parcels and kept none; knowing how many of them are in today's queue
    # (and what they are worth) is the difference between shipping revenue and
    # shipping returns.
    from logistics_portal.api.customers import digits, history_for
    rows = frappe.db.sql(
        f"""SELECT COALESCE(NULLIF(so.custom_customer_phone, ''),
                            so.custom_shipping_phone) phone,
                   LEAST(so.grand_total, %(sane)s) total
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.custom_sales_status IN %(live)s{me_cond}
            ORDER BY so.creation DESC LIMIT 400""",
        {"live": live, "sane": _SANE_MAX, **rng_vals}, as_dict=True)
    hist = history_for([r.phone for r in rows if r.phone]) if rows else {}
    seg_mix = {}
    for r in rows:
        h = hist.get(digits(r.phone)) if r.phone else None
        k = (h or {}).get("seg", "new")
        b = seg_mix.setdefault(k, {"n": 0, "value": 0})
        b["n"] += 1
        b["value"] += float(r.total or 0)
    for b in seg_mix.values():
        b["value"] = round(b["value"])
    seg_sampled = len(rows)

    # ── the oldest orders still waiting ──────────────────────────────────
    top = frappe.db.sql(
        f"""SELECT so.name, so.customer_name customer, so.grand_total total,
                   so.custom_sales_status st, {_CITY} city,
                   so.custom_allocated_to agent,
                   TIMESTAMPDIFF(HOUR, so.creation, NOW()) age_h,
                   COALESCE(so.custom_call_attempts, 0) attempts
            FROM `tabSales Order` so {_CITY_JOIN}
            WHERE so.docstatus = 1 AND so.custom_sales_status IN %(live)s{me_cond}
            ORDER BY so.creation LIMIT 20""",
        {"live": live, **rng_vals}, as_dict=True)

    # ── where the queue is, geographically ───────────────────────────────
    cities = frappe.db.sql(
        f"""SELECT COALESCE({_CITY}, '(none)') city, COUNT(*) n
            FROM `tabSales Order` so {_CITY_JOIN}
            WHERE so.docstatus = 1 AND so.custom_sales_status IN %(live)s{me_cond}
            GROUP BY city ORDER BY n DESC LIMIT 8""",
        {"live": live, **rng_vals}, as_dict=True)

    # ── the outcome of the window's intake ───────────────────────────────
    so_rng = rng.format(col="so.creation")
    intake = frappe.db.sql(
        f"""SELECT so.custom_sales_status st, COUNT(*) n
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND {so_rng}{me_cond}
            GROUP BY st""", rng_vals, as_dict=True)

    total_late = sum(v["late"] for v in queue.values())
    total_n = sum(v["n"] for v in queue.values())
    return {
        "mine": mine, "canSeeAll": role == "manager" or _is_cf_admin(),
        "slaHours": sla_h,
        "queue": queue,
        "queueTotal": total_n,
        "queueValue": sum(v["value"] for v in queue.values()),
        # Never a silent drop: say how many rows the sums refused, and why.
        "absurd": absurd, "saneMax": _SANE_MAX,
        "sla": {"late": total_late, "ok": max(0, total_n - total_late)},
        "aging": aging_rows,
        "segMix": seg_mix, "segSampled": seg_sampled,
        "topPending": [{
            "order": r.name, "customer": r.customer or "",
            "total": float(r.total or 0), "status": r.st or "",
            "city": (r.city or "").strip().title(),
            "agent": (r.agent or "").split("@")[0],
            "ageH": int(r.age_h or 0), "attempts": int(r.attempts or 0),
        } for r in top],
        "cities": [{"city": (r.city or "").strip().title(), "n": int(r.n or 0)}
                   for r in cities],
        "intake": [{"status": r.st or "(none)", "n": int(r.n or 0)}
                   for r in sorted(intake, key=lambda x: -int(x.n or 0))],
        "serverNow": str(now_datetime())[:19],
    }
