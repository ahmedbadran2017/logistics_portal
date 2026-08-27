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
from frappe.utils import add_to_date, flt, now_datetime

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
# Of the done tabs, these two are also produced by the WhatsApp automation at
# scale, so they're dated by the human decision time (custom_last_call_at) to
# keep the automation's mass out of the tab. "Duplicated" is human-only and is
# dated by creation instead — see the counts + row queries below.
_AUTOMATION_DONE = {
    "confirmed": "Confirmed",
    "cancelled": "Cancelled",
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

# The ONLY market this workspace serves. The ERPNext instance also carries
# Maslak LTD and Justyol Holding (Turkey) and Justyol China — and their orders
# sit in the exact same Pending/DNA/Follow-Up states. Without this filter the
# confirmation queue was 40% foreign: 1,107 Maslak + 83 China orders mixed in
# with 1,820 Morocco ones, including year-old Turkish seed data (Çiğdem
# Oduncu, Bursa, İstanbul) the agents were being shown to call. Every SO query
# in this lane is company-scoped through _CO.
_CO = "Justyol Morocco"

# The city lives on the linked Address, not the order: custom_shipping_city is
# filled on 2,167 of 247,500 orders (0.9%), the Address on 99.9%.
_CITY = ("COALESCE(NULLIF(TRIM(so.custom_shipping_city), ''), "
         "NULLIF(TRIM(addr.city), ''))")
_CITY_JOIN = ("LEFT JOIN `tabAddress` addr ON addr.name = "
              "COALESCE(so.shipping_address_name, so.customer_address)")

# The confirmation lane only owns an order while the warehouse hasn't taken it.
# Once it's picked/shipped/delivered the logistics status moves past Pending, and
# a "waiting to be called" panel that still counts it is lying — 181 such orders
# on prod (23 already Delivered) sat in the live queue tagged On Hold. Same rule
# as act()'s reopen guard: "once it's picked or shipped, the warehouse owns it."
_IN_HAND = ("(so.custom_logistics_status IS NULL OR "
            "so.custom_logistics_status IN ('Pending', ''))")

# A parked hold: On Hold that never went through the portal's call flow — no
# attempt logged, no retry timer — so the 48h On-Hold retry can never resurface
# it. On prod this is a legacy pile (a Nov-2025 batch, ~1,576 orders) that
# otherwise drowns every SLA metric on the dashboard. It's counted on its own
# card, OUT of the live queue, not silently dropped.
_PARKED = ("so.custom_sales_status = 'On Hold' AND "
           "COALESCE(so.custom_call_attempts, 0) = 0 AND "
           "so.custom_next_call_at IS NULL")


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
def board(tab="pending", days=30, q="", limit=30, offset=0, frm=None, to=None,
          as_user=None):
    """The queues + counts + my day so far, one call. `as_user` (manager /
    section admin only) scopes the board to that agent — the view-as feature:
    the manager sees exactly the queue the agent sees, read-only fidelity."""
    role = _gate()
    if tab not in QUEUES and tab not in DONE_QUEUES and tab not in ("monitor", "notdelivered"):
        tab = "pending"
    days = min(max(int(days or 30), 1), 365)
    limit = min(max(int(limit or 30), 1), 100)
    offset = max(int(offset or 0), 0)
    rng, rng_vals = _range(days, frm, to)
    custom_range = "frm" in rng_vals or "to" in rng_vals
    vals = {"days": days, "limit": limit, "offset": offset, **rng_vals}

    # Each agent sees ONLY their own orders; a manager or section admin sees the
    # whole section. "Their own" = the ERPNext assignment (_assign), the field
    # the team actually divides work by and the one the desk's "Assigned to me"
    # view uses. It diverges from custom_allocated_to (the intake round-robin):
    # of the live Not-Delivered set the two agreed on 1 order of 19, so scoping
    # by custom_allocated_to showed each agent a different queue than the desk.
    # _assign is set on 100% of the live queue too, so nothing is orphaned.
    # NB _assign is a JSON array string ('["a@x.com"]'); match the QUOTED email
    # so one address can't substring-match another. The DONE tabs stay keyed on
    # custom_allocated_to (me_done) — act() stamps it with the acting agent, so
    # those tabs remain a true "what I decided" trail, not "assigned to me".
    mine_only = role != "manager" and not _is_cf_admin()
    me = frappe.session.user
    as_user = (as_user or "").strip()
    if as_user and not mine_only:
        me = as_user
        mine_only = True
    me_q = me_so = me_done = ""
    if mine_only:
        rng_vals["me"] = me           # counts queries spread rng_vals
        rng_vals["me_like"] = f'%"{me}"%'
        vals["me"] = me
        vals["me_like"] = f'%"{me}"%'
        me_q = " AND _assign LIKE %(me_like)s"       # no alias (count scans)
        me_so = " AND so._assign LIKE %(me_like)s"   # so.-aliased queries
        me_done = " AND custom_allocated_to = %(me)s"  # done tabs: the actor

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
    # Live queues stop counting orders the warehouse already took (_IN_HAND —
    # the dashboard applied it, the board didn't, so the two disagreed and
    # agents were handed shipped orders). Retry queues are windowed on WHEN
    # THEY'RE DUE (next_call), not on order creation: an order deferred past
    # the window used to fall out of the queue exactly when it came due.
    in_hand = _IN_HAND.replace("so.", "")
    retry_rng = rng.format(col="COALESCE(custom_next_call_at, creation)")
    for sts, rng_sql in ((("Pending",), q_rng),
                         (tuple(v for k, v in QUEUES.items() if k != "pending"),
                          retry_rng)):
        for r in frappe.db.sql(
                f"""SELECT custom_sales_status s, COUNT(*) n FROM `tabSales Order`
                    WHERE docstatus = 1 AND company = %(co)s
                      AND custom_sales_status IN %(sts)s{me_q}
                      AND {in_hand} AND {rng_sql}
                    GROUP BY custom_sales_status""",
                {"sts": sts, "co": _CO, **rng_vals}, as_dict=True):
            for k, v in QUEUES.items():
                if v == r.s:
                    counts[k] = int(r.n or 0)
    # Confirmed & Cancelled carry the automation's mass (176k / 59k on prod):
    # keyed on when the DECISION was taken (custom_last_call_at), not when the
    # order arrived — the agent looks for "what I did today", and a 40-day-old
    # order confirmed an hour ago has to be in reach. A COALESCE(..., creation)
    # fallback would instead dump 167k automation-confirmed orders into the tab.
    for r in frappe.db.sql(
            f"""SELECT custom_sales_status s, COUNT(*) n FROM `tabSales Order`
                WHERE docstatus = 1 AND company = %(co)s
                  AND custom_sales_status IN %(sts)s{me_done}
                  AND {d_rng}
                GROUP BY custom_sales_status""",
            {"sts": tuple(_AUTOMATION_DONE.values()), "co": _CO, **rng_vals}, as_dict=True):
        for k, v in _AUTOMATION_DONE.items():
            if v == r.s:
                counts[k] = int(r.n or 0)
    # Duplicated is a human/desk-only decision — the automation never mass-
    # produces it (23 on prod). Its rows also predate custom_last_call_at, so
    # the custom_last_call_at filter used above hid every one of them. Date it
    # by creation, like a working queue, so the tab actually shows its orders.
    counts["duplicated"] = int(frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabSales Order`
            WHERE docstatus = 1 AND company = %(co)s
              AND custom_sales_status = 'Duplicated'{me_done}
              AND {q_rng}""",
        {"co": _CO, **rng_vals})[0][0])

    # Monitoring: live orders whose customer has taken 2+ parcels and kept
    # none of them. Nothing is blocked — the team looks and decides. Measured:
    # this group still takes delivery 27% of the time.
    from logistics_portal.api.customers import risky_phones
    risky = tuple(risky_phones()) or ("",)
    # The monitor count crosses a ~6.8k-phone IN list with a per-row REGEXP —
    # the single heaviest piece of a cold board load. Cache it per scope; the
    # exact rows are only computed when the monitor tab itself is open.
    _mck = "lp_cf_monitor_" + (me if mine_only else "all")
    _mc = frappe.cache().get_value(_mck)
    if _mc is not None and tab != "monitor":
        counts["monitor"] = int(_mc)
    else:
        counts["monitor"] = int(frappe.db.sql(
            f"""SELECT COUNT(*) FROM `tabSales Order` so
                WHERE so.docstatus = 1 AND so.company = %(co)s
                  AND so.custom_sales_status IN %(sts)s{me_so}
                  AND {_IN_HAND} AND {_CUST_KEY} IN %(risky)s""",
            {"sts": tuple(QUEUES.values()), "co": _CO, "risky": risky,
             **({"me_like": f'%"{me}"%'} if mine_only else {})})[0][0])
        frappe.cache().set_value(_mck, counts["monitor"], expires_in_sec=300)

    # Not Delivered: shipped-then-failed parcels the confirmation team calls
    # back to arrange a redelivery/reship or to cancel. Post-shipment work
    # shared with the Rescue lane — the SAME rescue.act engine runs the
    # decisions (the frontend calls it for this tab), so there's one set of
    # transitions, not two. Surfaced per-agent here like the rest of the lane;
    # a 60-day floor keeps a six-week-old failure reachable, matching Rescue.
    nd_rng = (rng.format(col="creation") if custom_range
              else "creation >= DATE_SUB(NOW(), INTERVAL %(ndays)s DAY)")
    nd_vals = {"co": _CO, "ndays": max(days, 60), **rng_vals}
    counts["notdelivered"] = int(frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabSales Order`
            WHERE docstatus = 1 AND company = %(co)s
              AND custom_sales_status = 'Not Delivered'{me_q}
              AND {nd_rng}""", nd_vals)[0][0])

    vals["co"] = _CO
    if tab == "monitor":
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status IN %(statuses)s", _IN_HAND,
                 f"{_CUST_KEY} IN %(risky)s"]
        vals["statuses"] = tuple(QUEUES.values())
        vals["risky"] = risky
    elif tab in _AUTOMATION_DONE:
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status = %(status)s",
                 "so.custom_last_call_at IS NOT NULL",
                 rng.format(col="so.custom_last_call_at")]
        vals["status"] = _AUTOMATION_DONE[tab]
    elif tab == "duplicated":
        # Human-only decision with legacy rows that predate custom_last_call_at
        # — date by creation (mirrors the count above) so the tab isn't empty.
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status = 'Duplicated'",
                 rng.format(col="so.creation")]
    elif tab == "notdelivered":
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status = 'Not Delivered'",
                 (rng.format(col="so.creation") if custom_range
                  else "so.creation >= DATE_SUB(NOW(), INTERVAL %(ndays)s DAY)")]
        vals["ndays"] = max(days, 60)
    else:
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status = %(status)s", _IN_HAND,
                 rng.format(col=("so.creation" if tab == "pending" else
                                 "COALESCE(so.custom_next_call_at, so.creation)"))]
        vals["status"] = QUEUES[tab]
    # Agent scope on the rows AND the search: an agent searching still only
    # reaches their own orders. Working queues scope by the ERPNext assignment
    # (_assign, what the desk divides work by); the done tabs by the actor
    # (custom_allocated_to, what act() stamped) so they stay a "what I did"
    # trail. (both me / me_like are already in vals from the block above.)
    if mine_only:
        if tab in _AUTOMATION_DONE or tab == "duplicated":
            conds.append("so.custom_allocated_to = %(me)s")
        else:
            conds.append("so._assign LIKE %(me_like)s")
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
    if tab in _AUTOMATION_DONE:
        order_by = "so.custom_last_call_at DESC"  # newest decision first
    elif tab == "duplicated":
        order_by = "so.creation DESC"             # newest duplicate first
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
                   addr.address_line1 AS address_line,
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
            (me, f"{today} 00:00:00"), as_dict=True):
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
        points = bonus_points_for(me, bonus_group_for(role), nowdate()[:7])
    except Exception:
        pass

    return {
        "tab": tab, "counts": counts, "total": int(total or 0),
        "myTotal": my_total, "myTarget": int(cf_s.get("dayTarget", 40)),
        "slaHours": int(cf_s.get("slaFirstCallH", 6)),
        "discountCapPct": int(cf_s.get("discountCapPct", 15)),
        "discountCapAmt": int(cf_s.get("discountCapAmt", 50)),
        "points": points,
        "rows": [{
            "order": r.name, "customer": r.customer or "",
            "total": float(r.total or 0), "phone": (r.phone or "").strip(),
            # NB: the alias is item_count, NOT `items` — on a frappe._dict row
            # `r.items` resolves to the dict METHOD and int(method) TypeErrors
            # (same trap that blanked the Settings zones panel once).
            "city": (r.city or "").strip().title(), "items": int(r.item_count or 1),
            "addressLine": (r.address_line or "").strip(),
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
        "reasons": effective_reasons(),
        "serverNow": str(now_datetime())[:19],
    }


def _own_guard(role, orders):
    """A plain agent may only act on orders allocated to them; a manager or
    section admin may act on any. Every write path calls this, so the per-agent
    scope is enforced on the API, not just hidden in the board's row filter —
    an agent can't reach a colleague's order by posting its id directly."""
    if role == "manager" or _is_cf_admin():
        return
    names = [orders] if isinstance(orders, str) else list(orders or [])
    names = [str(n).strip() for n in names if str(n).strip()]
    if not names:
        return
    # Foreign only if the agent is NEITHER the assignee (_assign, the working
    # queue's owner) NOR the actor (custom_allocated_to, stamped by act() on the
    # done tabs). Either claim lets them act, so reopening an order they decided
    # still works even when its ERPNext assignment points at someone else.
    foreign = frappe.db.sql(
        """SELECT name FROM `tabSales Order`
           WHERE name IN %(n)s
             AND COALESCE(custom_allocated_to,'') != %(me)s
             AND (_assign IS NULL OR _assign NOT LIKE %(me_like)s)
           LIMIT 1""",
        {"n": tuple(names), "me": frappe.session.user,
         "me_like": f'%"{frappe.session.user}"%'})
    if foreign:
        frappe.throw("You can only act on orders assigned to you.",
                     frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def act(order, action, note=None, _bulk=False):
    """One call decision. confirm → enters the logistics pool; cancel needs a
    reason; dna/followup/onhold re-queue with a retry time and bump the
    attempt counter. `_bulk` marks the comment "(bulk)" so bonus scoring can
    exclude batch work, as the scheme promises."""
    role = _gate()
    order = (order or "").strip()
    _own_guard(role, order)
    if action not in _ACTIONS:
        frappe.throw("Unknown action.")
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    so = frappe.db.get_value(
        "Sales Order", order,
        ["docstatus", "custom_sales_status", "custom_call_attempts", "company"],
        as_dict=True)
    if so.docstatus != 1:
        frappe.throw("Order is not submitted.")
    if so.company != _CO:
        # Every read in this lane is company-scoped; the write must be too.
        frappe.throw("Unknown order.")
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
        # Same fence as reopen: once the warehouse holds the order, a cancel
        # here leaves the floor with a cancelled parcel in a tote. Those go
        # through the dispatcher / rescue flow instead.
        stage = frappe.db.get_value("Sales Order", order, "custom_logistics_status")
        if stage and stage not in ("Pending", ""):
            frappe.throw(f"Can't cancel — the order is already {stage} in the "
                         "warehouse. Route it through Rescue/Exceptions.")
        if frappe.db.exists("Pick List Item",
                            {"sales_order": order, "docstatus": ["<", 2]}):
            frappe.throw("Can't cancel — the order is already on a pick list. "
                         "Ask the dispatcher to pull it first.")

    now = now_datetime()
    attempts = int(so.custom_call_attempts or 0)
    updates = {
        "custom_sales_status": _ACTIONS[action],
        "custom_last_call_at": now,
    }
    # Attribution: only a real DECISION claims the order. Retry touches
    # (dna/followup/onhold) used to overwrite the owner too, which made
    # spraying DNA a way to farm the delivered-outcome bonus of orders the
    # automation later confirmed; they now claim only an unowned order, and
    # reopen never re-attributes at all.
    if action in ("confirm", "cancel", "duplicate"):
        updates["custom_allocated_to"] = frappe.session.user
    elif action != "reopen" and not (frappe.db.get_value(
            "Sales Order", order, "custom_allocated_to") or ""):
        updates["custom_allocated_to"] = frappe.session.user
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
                    + (" (bulk)" if _bulk else "")
                    + (f" (attempt {attempts})" if action in _RETRY_HOURS else "")
                    + (f" — {note}" if note else "")
                    + f" · by {frappe.session.user}")
    frappe.db.commit()
    # Decided = out of the serve rotation NOW, not when the lock expires.
    frappe.cache().delete_value(f"lp_serve_{order}")
    frappe.cache().delete_value(f"lp_skip_{frappe.session.user}_{order}")
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


@frappe.whitelist(methods=["POST"])
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
            act(name, action, reason, _bulk=True)
            done.append(name)
        except Exception:
            skipped.append(name)
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback(), "confirmation.bulk_act")
    frappe.db.commit()
    return {"ok": True, "done": len(done), "skipped": skipped}


@frappe.whitelist(methods=["POST"])
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
            "Comment", f"Confirmation: cancel (bulk) — {reason} · by {frappe.session.user}")
        done.append(name)
    frappe.db.commit()
    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
        frappe.cache().delete_value(k)
    frappe.cache().delete_keys("lp_suggest")
    return {"ok": True, "done": len(done), "skipped": skipped}


@frappe.whitelist(methods=["POST"])
def update_contact(order, phone=None, city=None, address_line=None):
    """Fix the customer's phone / full address before confirming — the #1
    reason deliveries fail later (Cathedis rejects unknown cities and bad
    numbers). Logged old → new on the order.

    The street + city live on the linked Address (99.9% of orders), NOT on the
    Sales Order — custom_shipping_city is filled on under 1%. Cathedis reads
    the Address (its failures say "Address None not found"), so the edit has to
    land there. We write BOTH: the Address is the real source, and the SO's
    custom_shipping_city is mirrored so the board (_CITY) and every downstream
    reader stay in step. If the order has no Address at all, one is created and
    linked, which is itself one of the failure modes.
    """
    role = _gate()
    order = (order or "").strip()
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    _own_guard(role, order)
    phone = (phone or "").strip()
    city = (city or "").strip()
    address_line = (address_line or "").strip()
    if not phone and not city and not address_line:
        frappe.throw("Nothing to update.")
    old = frappe.db.get_value(
        "Sales Order", order,
        ["custom_customer_phone", "custom_shipping_phone", "custom_shipping_city",
         "shipping_address_name", "customer_address", "customer", "customer_name"],
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

    # ── the Address: where the carrier actually reads the delivery from ──
    addr_name = old.shipping_address_name or old.customer_address
    if (city or address_line or phone):
        if addr_name and frappe.db.exists("Address", addr_name):
            adoc = frappe.get_doc("Address", addr_name)
            if address_line and (adoc.address_line1 or "") != address_line:
                log.append(f"address {(adoc.address_line1 or '—')} → {address_line}")
                adoc.address_line1 = address_line
            if city and (adoc.city or "").strip() != city:
                adoc.city = city
            if phone:
                adoc.phone = phone
            adoc.flags.ignore_permissions = True
            adoc.save(ignore_permissions=True)
        elif address_line or city:
            # No Address on the order — Cathedis logs this as "Address None
            # not found". Build one and link it so the parcel has somewhere to
            # go, instead of failing silently at label time.
            adoc = frappe.get_doc({
                "doctype": "Address",
                "address_title": old.customer_name or old.customer or order,
                "address_type": "Shipping",
                "address_line1": address_line or (city or order),
                "city": city or "",
                "phone": phone or "",
                "country": "Morocco",
                "links": [{"link_doctype": "Customer", "link_name": old.customer}]
                         if old.customer else [],
            })
            adoc.flags.ignore_permissions = True
            adoc.insert(ignore_permissions=True)
            updates["shipping_address_name"] = adoc.name
            if not old.customer_address:
                updates["customer_address"] = adoc.name
            log.append(f"address created ({adoc.name})")

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
    # Save-the-sale discount caps for a plain agent (managers/section admins
    # are uncapped). Measured need: 438 discount edits/30d were happening on
    # the desk with no cap and no trail.
    "discountCapPct": 15,
    "discountCapAmt": 50,
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


def effective_reasons():
    """The list the cancel box actually offers: the manager's quick-pick subset,
    or the whole vocabulary when no subset is set. Same fallback cf_settings()
    uses — the board must never hand back an empty list, or the picker has
    nothing to choose and the UI drops to free text (the exact thing we're
    unifying away)."""
    opts = reason_options()
    sub = [r for r in (_cf_settings().get("reasons") or []) if r in opts]
    return sub or opts


def _is_cf_admin():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role == "manager":
        return True
    # An admin listing is a capability, not a role — a user pulled off the
    # team (role=none) must lose it instantly, whatever the list still says.
    if role not in ("confirmation", "cs", "tracking"):
        return False
    return frappe.session.user in _cf_settings().get("admins", [])


@frappe.whitelist()
def cf_settings():
    _gate()
    s = _cf_settings()
    opts = reason_options()
    return {**s, "canEdit": _is_cf_admin(), "reasonOptions": opts,
            # No subset chosen = the whole vocabulary.
            "reasons": [r for r in (s.get("reasons") or []) if r in opts] or opts}


@frappe.whitelist(methods=["POST"])
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
    for k in ("discountCapPct", "discountCapAmt"):
        if k in settings:
            v = int(settings[k])
            if not (0 <= v <= (100 if k == "discountCapPct" else 100000)):
                frappe.throw(f"{k} out of range.")
            out[k] = v
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
    # Gate FIRST, cache second — a cached team report must never leak past
    # the section-admin check.
    _gate()
    if not _is_cf_admin():
        frappe.throw("Only the portal manager or a section admin can open the "
                     "section report.", frappe.PermissionError)
    import json as _json_r
    _ck = f"lp_cf_report_{days}_{frm or ''}_{to or ''}"
    _hit = frappe.cache().get_value(_ck)
    if _hit:
        try:
            return _json_r.loads(_hit)
        except Exception:
            pass
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
                WHERE so.docstatus = 1 AND so.company = %(co)s
                  AND COALESCE(so.custom_allocated_to,'') != ''
                  AND so.custom_allocated_to NOT IN ('Administrator', 'Guest')
                  AND {so_rng}
                GROUP BY u""", {"sane": _SANE_MAX, "co": _CO, **rng_vals}, as_dict=True):
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
                      WHERE so.docstatus = 1 AND so.company = %(co)s
                        AND COALESCE(so.custom_allocated_to,'') != ''
                        AND so.custom_allocated_to NOT IN ('Administrator', 'Guest')
                        AND {so_rng}
                      GROUP BY so.name) x
                GROUP BY u""", {"sane": _SANE_MAX, "co": _CO, **rng_vals}, as_dict=True):
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
            # Face value of orders with a Delivered parcel (partial returns not
            # deducted) — an approximation of collected cash, not a cash ledger.
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
                WHERE so.docstatus = 1 AND so.company = %(co)s
                  AND so.custom_sales_status = 'Cancelled'
                  AND {so_rng}
                GROUP BY 1 ORDER BY n DESC LIMIT 15""", {"co": _CO, **rng_vals})]

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
                WHERE so.docstatus = 1 AND so.company = %(co)s
                  AND {so_rng}""", {"co": _CO, **rng_vals}, as_dict=True)[0]
        ladder = {"r1": int(ladder.r1 or 0), "r2": int(ladder.r2 or 0),
                  "n": int(ladder.n or 0)}

    from logistics_portal.api.settings import get_ops
    _out = {
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
    frappe.cache().set_value(_ck, _json_r.dumps(_out, default=str), expires_in_sec=300)
    return _out

@frappe.whitelist()
def dashboard(days=30, frm=None, to=None, mine=0):
    """The section's own dashboard.

    NOTE on the range: `days`/`frm`/`to` reach `intake` ONLY. queue, aging,
    segMix, topPending and cities all describe the CURRENT state of the queue
    -- what is waiting, right now, and how old it is. There is no snapshot
    history to replay them from, so a range is not something they can honour;
    asking for June would not make them show June, it would make them show now
    under a header that says June. The screen marks those panels "right now"
    rather than silently ignoring the picker.
    """
    role = _gate()
    days = min(max(int(days or 30), 1), 365)
    rng, rng_vals = _range(days, frm, to)
    rng_vals["co"] = _CO   # every panel below is Morocco-only; see _CO.
    # A plain agent is ALWAYS scoped to their own orders — the "mine" toggle is
    # theirs to leave on, not a way to see the whole section. Only a manager or
    # section admin may drop the scope (mine=0). Same rule as the board.
    can_see_all = role == "manager" or _is_cf_admin()
    mine = int(mine or 0) or (0 if can_see_all else 1)
    me_cond = ""
    if mine:
        rng_vals["me_like"] = f'%"{frappe.session.user}"%'
        # By the ERPNext assignment, same as the board — the dashboard must
        # describe the queue the agent actually owns, not the intake round-robin.
        me_cond = " AND so._assign LIKE %(me_like)s"
    live = tuple(QUEUES.values())
    s = _cf_settings()
    sla_h = int(s.get("slaFirstCallH", 6))
    # Every "waiting" panel below describes the ACTIONABLE queue: still in the
    # lane's hands (not yet picked/shipped) and not a parked legacy hold. The
    # two excluded piles are reported separately (parked / movedButOnHold) so
    # nothing vanishes — the SLA metrics just stop being drowned by them.
    active = f"AND {_IN_HAND} AND NOT ({_PARKED})"

    # ── the live queue: what is waiting, and what is it worth ────────────
    q = frappe.db.sql(
        f"""SELECT so.custom_sales_status st, COUNT(*) n,
                   COALESCE(SUM(CASE WHEN so.grand_total <= %(sane)s
                                     THEN so.grand_total ELSE 0 END), 0) value,
                   SUM(so.grand_total > %(sane)s) absurd,
                   SUM(TIMESTAMPDIFF(HOUR, so.creation, NOW()) > %(sla)s
                       AND COALESCE(so.custom_call_attempts, 0) = 0) late
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s {active}{me_cond}
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
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s {active}{me_cond}
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
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s {active}{me_cond}
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
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s {active}{me_cond}
            ORDER BY so.creation LIMIT 20""",
        {"live": live, **rng_vals}, as_dict=True)

    # ── where the queue is, geographically ───────────────────────────────
    cities = frappe.db.sql(
        f"""SELECT COALESCE({_CITY}, '(none)') city, COUNT(*) n
            FROM `tabSales Order` so {_CITY_JOIN}
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s {active}{me_cond}
            GROUP BY city ORDER BY n DESC LIMIT 8""",
        {"live": live, **rng_vals}, as_dict=True)

    # ── the outcome of the window's intake ───────────────────────────────
    so_rng = rng.format(col="so.creation")
    intake = frappe.db.sql(
        f"""SELECT so.custom_sales_status st, COUNT(*) n
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND {so_rng}{me_cond}
            GROUP BY st""", rng_vals, as_dict=True)

    # ── the two piles held OUT of the live queue, reported on their own ──
    # Parked holds: On Hold with no attempt and no timer — a legacy pile the
    # retry can't resurface. Shown so the manager can decide (cancel/archive),
    # never counted as "waiting to be called".
    parked = frappe.db.sql(
        f"""SELECT COUNT(*) n,
                   COALESCE(SUM(LEAST(so.grand_total, %(sane)s)), 0) value,
                   MAX(TIMESTAMPDIFF(DAY, so.creation, NOW())) oldest_d
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND {_IN_HAND} AND {_PARKED}{me_cond}""",
        {"sane": _SANE_MAX, **rng_vals}, as_dict=True)[0]
    # A live-status order the warehouse already moved (picked/shipped/delivered)
    # while its sales-status stayed On Hold/Pending — a stale label, not waiting
    # work. Surfaced as a data-health count for the manager to get corrected.
    moved = int(frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s
              AND NOT {_IN_HAND}{me_cond}""",
        {"live": live, **rng_vals})[0][0])

    total_late = sum(v["late"] for v in queue.values())
    total_n = sum(v["n"] for v in queue.values())

    # First-touch speed (7d, cached 1h): minutes from order arrival to the
    # FIRST status flip — human or automation. Measured at 7.1h average on
    # 2026-08-27 and displayed nowhere; this is the number the whole section
    # exists to move, so it belongs on the section's own dashboard.
    import json as _json_mod
    ft = None
    ck = "lp_cf_first_touch"
    hit = frappe.cache().get_value(ck)
    if hit:
        try:
            ft = _json_mod.loads(hit)
        except Exception:
            ft = None
    if ft is None:
        try:
            r = frappe.db.sql(
                """SELECT AVG(TIMESTAMPDIFF(MINUTE, so.creation, v.first_v)),
                          COUNT(*)
                   FROM (SELECT docname, MIN(creation) first_v FROM `tabVersion`
                         WHERE ref_doctype = 'Sales Order'
                           AND creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                           AND data LIKE '%%custom_sales_status%%'
                         GROUP BY docname) v
                   JOIN `tabSales Order` so ON so.name = v.docname
                   WHERE so.company = %(co)s
                     AND so.creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)""",
                {"co": _CO})[0]
            ft = {"avgMin": round(float(r[0] or 0)), "orders": int(r[1] or 0)}
            frappe.cache().set_value(ck, _json_mod.dumps(ft), expires_in_sec=3600)
        except Exception:
            # avgMin 0 would read as a PERFECT score — the one failure mode a
            # KPI must never have. null renders as "no data"; the short cache
            # stops a timing-out query from re-running on every load.
            frappe.log_error(frappe.get_traceback()[:3000], "cf first-touch")
            ft = {"avgMin": None, "orders": 0}
            frappe.cache().set_value(ck, _json_mod.dumps(ft), expires_in_sec=600)

    return {
        "firstTouch": ft,
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
        # The two piles held out of the live queue (see above).
        "parked": {"n": int(parked.n or 0), "value": round(float(parked.value or 0)),
                   "oldestDays": int(parked.oldest_d or 0)},
        "movedButOnHold": moved,
        "serverNow": str(now_datetime())[:19],
    }


# ── Save-the-sale: amend a submitted pending order (Phase A of the workspace) ─
#
# Measured 2026-08-27: agents changed discount fields 438×/30d and edited
# order items on the DESK — the two capabilities that kept them off the portal
# entirely (21 portal actions vs 10,058 desk list visits in 30 days). ERPNext's
# only legitimate way to change a SUBMITTED order's money or lines is the
# amend cycle; the desk made them do it by hand, this does it in one call and
# restores everything the cycle loses (assignment, attribution, call state).


@frappe.whitelist(methods=["POST"])
def amend_order(order, discount_amount=None, discount_percent=None,
                items=None, note=None):
    """Cancel → amended copy → apply changes → submit, in one transaction.

    Guards: confirmation-lane statuses only, BEFORE the warehouse touches it
    (no pick list, logistics still Pending), agent within the section's
    discount caps (manager/section admin uncapped), at least one line left.
    `items` = [{"item_code": ..., "qty": n}] — qty 0 removes the line."""
    import json as _json
    role = _gate()
    order = (order or "").strip()
    _own_guard(role, order)
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    so = frappe.get_doc("Sales Order", order)
    if so.docstatus != 1:
        frappe.throw("Order is not submitted.")
    if so.company != _CO:
        frappe.throw("Unknown order.")
    if so.custom_sales_status not in QUEUES.values():
        frappe.throw(f"Order is {so.custom_sales_status or 'unset'} — only live "
                     "confirmation-lane orders can be amended here.")
    stage = so.custom_logistics_status or ""
    if stage not in ("", "Pending"):
        frappe.throw(f"Can't amend — the order is already {stage} in the warehouse.")
    if frappe.db.exists("Pick List Item",
                        {"sales_order": order, "docstatus": ["<", 2]}):
        frappe.throw("Can't amend — the order is already on a pick list.")

    if isinstance(items, str):
        items = _json.loads(items)
    items = items or []
    d_amt = flt(discount_amount) if discount_amount not in (None, "") else None
    d_pct = flt(discount_percent) if discount_percent not in (None, "") else None
    if d_amt is None and d_pct is None and not items:
        frappe.throw("Nothing to change.")
    if d_amt is not None and d_amt < 0:
        frappe.throw("Discount can't be negative.")
    if d_pct is not None and not (0 <= d_pct <= 100):
        frappe.throw("Discount percent must be 0–100.")

    # Agent caps — the desk had no ceiling and no trail; here the ceiling is a
    # section setting and every dirham is on the comment trail.
    if role != "manager" and not _is_cf_admin():
        s = _cf_settings()
        cap_amt = flt(s.get("discountCapAmt", 50))
        if d_pct is not None and d_pct > flt(s.get("discountCapPct", 15)):
            frappe.throw(f"Your discount cap is {s.get('discountCapPct', 15)}% — "
                         "ask a section admin for more.")
        # A percent is still money: 15% of a big basket must not sail past
        # the amount cap. Both caps bind, whichever form the agent typed.
        if d_pct is not None and flt(so.grand_total) * d_pct / 100.0 > cap_amt:
            frappe.throw(f"That's {flt(so.grand_total) * d_pct / 100.0:.0f} MAD — "
                         f"your money cap is {cap_amt:.0f} MAD. "
                         "Ask a section admin for more.")
        if d_amt is not None and d_amt > cap_amt:
            frappe.throw(f"Your discount cap is {cap_amt:.0f} MAD — "
                         "ask a section admin for more.")

    # Snapshot everything the amend cycle would lose.
    keep = {k: so.get(k) for k in (
        "custom_sales_status", "custom_allocated_to", "custom_call_attempts",
        "custom_next_call_at", "custom_last_call_at", "custom_channel")}
    assign_raw = so.get("_assign") or ""
    note = (note or "").strip()

    changes = []
    new = frappe.copy_doc(so)
    new.amended_from = so.name
    new.docstatus = 0
    if items:
        wanted = {str(i.get("item_code")): flt(i.get("qty")) for i in items
                  if i.get("item_code")}
        rows = []
        for r in new.items:
            q = wanted.get(r.item_code, None)
            if q is None:
                rows.append(r)
            elif q > 0:
                if flt(q) != flt(r.qty):
                    changes.append(f"{r.item_code}: {flt(r.qty):g}→{flt(q):g}")
                r.qty = q
                rows.append(r)
            else:
                changes.append(f"removed {r.item_code}")
        if not rows:
            frappe.throw("An order needs at least one item — cancel it instead.")
        new.items = rows
    if d_pct is not None:
        new.apply_discount_on = new.apply_discount_on or "Grand Total"
        new.additional_discount_percentage = d_pct
        new.discount_amount = 0
        changes.append(f"discount {d_pct:g}%")
    elif d_amt is not None:
        new.apply_discount_on = new.apply_discount_on or "Grand Total"
        new.additional_discount_percentage = 0
        new.discount_amount = d_amt
        changes.append(f"discount {d_amt:g} MAD")

    detail = "; ".join(changes) + (f" — {note}" if note else "")
    so.flags.ignore_permissions = True
    so.cancel()
    so.add_comment("Comment",
                   f"Confirmation: amended → replaced ({detail}) "
                   f"· by {frappe.session.user}")
    new.flags.ignore_permissions = True
    new.insert(ignore_permissions=True)
    new.submit()
    # Restore the working state the copy dropped or the cycle reset.
    restore = {k: v for k, v in keep.items() if v is not None}
    # The copy is a NEW row (creation = now) — every age / SLA / cohort metric
    # keys on creation, so a tiny amend would zero a 6-day-old order's age.
    # The replacement inherits the original clock.
    restore["creation"] = so.creation
    if restore:
        frappe.db.set_value("Sales Order", new.name, restore,
                            update_modified=False)
    if assign_raw:
        frappe.db.set_value("Sales Order", new.name, "_assign", assign_raw,
                            update_modified=False)
    new.add_comment("Comment",
                    f"Confirmation: amend of {order} ({detail}) "
                    f"· by {frappe.session.user}")
    frappe.db.commit()
    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return {"ok": True, "order": new.name, "amendedFrom": order,
            "total": flt(new.grand_total), "changes": detail}


# ── Serve-next: the workspace engine (Phase B) ──────────────────────────────


@frappe.whitelist(methods=["POST"])
def next_order(skip=None, as_user=None):
    """Hand the agent the ONE order to work now — due retries first (oldest
    deferral), then the oldest untouched Pending. The agent never cherry-picks;
    this is what moves the 7-hour first-touch. A short cache lock keeps two
    admins (whole-pool scope) off the same order; per-agent scopes can't
    collide by construction.

    `skip` = the order the agent is walking away from UNDECIDED: without a
    marker, releasing it would hand them the very same order back (it is still
    the top priority). Skipped orders sit out for 10 minutes for that agent."""
    role = _gate()
    cache = frappe.cache()
    me = frappe.session.user
    skip = (skip or "").strip()
    view_as = (as_user or "").strip()
    if skip:
        cache.set_value(f"lp_skip_{me}_{skip}", 1, expires_in_sec=600)
        lock = f"lp_serve_{skip}"
        if cache.get_value(lock) == me:
            cache.delete_value(lock)
    mine = role != "manager" and not _is_cf_admin()
    scope_user = frappe.session.user
    if view_as and not mine:
        scope_user = view_as
        mine = True
    me_q = ""
    vals = {"co": _CO}
    if mine:
        vals["me_like"] = f'%"{scope_user}"%'
        me_q = " AND so._assign LIKE %(me_like)s"

    retry_sts = tuple(v for k, v in QUEUES.items() if k != "pending")
    for sql, extra in (
        (f"""SELECT so.name FROM `tabSales Order` so
             WHERE so.docstatus = 1 AND so.company = %(co)s
               AND so.custom_sales_status IN %(sts)s AND {_IN_HAND}
               AND so.custom_next_call_at IS NOT NULL
               AND so.custom_next_call_at <= NOW(){me_q}
             ORDER BY so.custom_next_call_at LIMIT 25""",
         {"sts": retry_sts}),
        (f"""SELECT so.name FROM `tabSales Order` so
             WHERE so.docstatus = 1 AND so.company = %(co)s
               AND so.custom_sales_status = 'Pending' AND {_IN_HAND}
               AND so.creation >= DATE_SUB(NOW(), INTERVAL 30 DAY){me_q}
             ORDER BY so.creation LIMIT 25""", {}),
    ):
        for (name,) in frappe.db.sql(sql, {**vals, **extra}):
            if cache.get_value(f"lp_skip_{me}_{name}"):
                continue
            lock = f"lp_serve_{name}"
            if cache.get_value(lock) and cache.get_value(lock) != me:
                continue
            # View-as is read fidelity: the manager PEEKS at the agent's next
            # order without locking it away from the agent's own serve flow.
            if not view_as:
                cache.set_value(lock, me, expires_in_sec=300)
            return {"order": name}
    return {"order": None}


@frappe.whitelist(methods=["POST"])
def release_order(order):
    """The agent skipped / navigated away — free the serve lock."""
    _gate()
    order = (order or "").strip()
    lock = f"lp_serve_{order}"
    if frappe.cache().get_value(lock) == frappe.session.user:
        frappe.cache().delete_value(lock)
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def add_note(order, note):
    """A free-text note on the order — the call context the status flip can't
    carry ("husband will confirm tonight", "asked for Saturday delivery")."""
    role = _gate()
    order = (order or "").strip()
    note = (note or "").strip()
    if not note:
        frappe.throw("Empty note.")
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    _own_guard(role, order)
    frappe.get_doc("Sales Order", order).add_comment(
        "Comment", f"Note — {note[:400]} · by {frappe.session.user}")
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def order_activity(order, limit=15):
    """The order's human trail, newest first: lane decisions, notes, contact
    fixes, rescue touches — everything a colleague did before this call."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in (
            "confirmation", "cs", "tracking", "manager"):
        frappe.throw("Not authorized.", frappe.PermissionError)
    order = (order or "").strip()
    # The whole lane is company-scoped; the comment trail must be too — this
    # endpoint must not enumerate other companies' order histories.
    if frappe.db.get_value("Sales Order", order, "company") != _CO:
        frappe.throw("Unknown order.")
    limit = min(max(int(limit or 15), 1), 50)
    rows = frappe.db.sql(
        """SELECT c.owner, c.content, c.creation FROM `tabComment` c
           WHERE c.reference_doctype = 'Sales Order' AND c.reference_name = %s
             AND c.comment_type = 'Comment'
           ORDER BY c.creation DESC LIMIT %s""", (order, limit), as_dict=True)
    return {"rows": [{
        "by": (r.owner or "").split("@")[0],
        "text": (r.content or "")[:300],
        "at": str(r.creation)[:16],
    } for r in rows]}


@frappe.whitelist()
def next_up(limit=20, as_user=None):
    """The serve PLAN, in the exact order next_order() will hand it out:
    due call-backs first (oldest deferral), then the oldest Pending. The
    workspace queue pane shows this — the agent sees what's coming, not just
    the pending slice. Also reports the earliest FUTURE call-back, so an
    empty list can say "next call-back at 14:30" instead of lying "all done".
    """
    role = _gate()
    limit = min(max(int(limit or 20), 1), 40)
    mine = role != "manager" and not _is_cf_admin()
    scope_user = frappe.session.user
    as_user = (as_user or "").strip()
    if as_user and not mine:
        scope_user = as_user
        mine = True
    me_q = ""
    vals = {"co": _CO, "limit": limit}
    if mine:
        vals["me_like"] = f'%"{scope_user}"%'
        me_q = " AND so._assign LIKE %(me_like)s"

    retry_sts = tuple(v for k, v in QUEUES.items() if k != "pending")
    sel = """SELECT so.name, so.customer_name customer, so.grand_total total,
                    so.custom_sales_status status,
                    COALESCE(so.custom_call_attempts, 0) attempts,
                    so.custom_next_call_at next_call,
                    TIMESTAMPDIFF(HOUR, so.creation, NOW()) age_h"""
    due = frappe.db.sql(
        f"""{sel} FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(sts)s AND {_IN_HAND}
              AND so.custom_next_call_at IS NOT NULL
              AND so.custom_next_call_at <= NOW(){me_q}
            ORDER BY so.custom_next_call_at LIMIT %(limit)s""",
        {**vals, "sts": retry_sts}, as_dict=True)
    room = max(0, limit - len(due))
    fresh = frappe.db.sql(
        f"""{sel} FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status = 'Pending' AND {_IN_HAND}
              AND so.creation >= DATE_SUB(NOW(), INTERVAL 30 DAY){me_q}
            ORDER BY so.creation LIMIT %(room)s""",
        {**vals, "room": room}, as_dict=True) if room else []

    upcoming = frappe.db.sql(
        f"""SELECT MIN(so.custom_next_call_at) FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(sts)s AND {_IN_HAND}
              AND so.custom_next_call_at > NOW(){me_q}""",
        {**vals, "sts": retry_sts})[0][0]

    status_tab = {"Did not Answer": "dna", "Follow Up": "followup",
                  "On Hold": "onhold"}

    def _when(dt):
        # HH:MM reads as "today" — a call-back due TOMORROW 08:30 must say so.
        if not dt:
            return ""
        v = str(dt)
        return v[11:16] if v[:10] == str(now_datetime())[:10] else v[5:16]

    rows = [{
        "order": r.name, "customer": r.customer or "",
        "total": float(r.total or 0), "ageH": int(r.age_h or 0),
        "attempts": int(r.attempts or 0),
        "due": bool(r.status != "Pending"),
        "kind": status_tab.get(r.status, "pending"),
        "nextCall": _when(r.next_call),
    } for r in list(due) + list(fresh)]
    return {"rows": rows, "nextDueAt": _when(upcoming),
            "dueCount": len(due)}
