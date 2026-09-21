"""Contact Center — Lane 1: order confirmation.

The WhatsApp automation stays first-line (it confirms ~85% of orders as
Administrator); this workspace is for the TAIL the automation can't close:
new Pending orders, Did-not-Answer retries, Follow Ups and On Holds — worked
by named agents (role `confirmation`) with an attempt counter, a next-call
time, and a per-agent trail, instead of the shared Administrator desk login.

Lane 2 (post-ship rescue) and Lane 3 (CS tickets) plug into the same
customer-card model later.
"""

import json

import frappe
from datetime import date
from frappe.utils import add_to_date, flt, now_datetime

from logistics_portal.api import clock as _clock

# The queues this lane owns. Orders leave the lane on Confirm/Cancel.
QUEUES = {
    "pending": "Pending",
    "dna": "Did not Answer",
    "followup": "Follow Up",
    # "onhold" retired 2026-09-09 (Ahmed): the team stopped using it — zero
    # On Hold orders exist on prod, in-hand or otherwise. The STATUS string
    # stays readable everywhere (search, history, _PARKED legacy guard); only
    # the tab, the button and the retry timer are gone, so nothing new can
    # enter the state.
}
# Where an order GOES when the lane is done with it. The agent has to be able
# to look at their own decisions — to check one, to answer "what did I do with
# this customer", to catch a mistake — so every terminal state is a tab too,
# not a black hole the order falls into.
# What this lane may still decide. Not Delivered joins the live queues: the
# customer refused a delivery, so "does he still want it?" is a confirmation
# question again, answered with the same verbs and ending in the same two
# statuses as any other order. Deliberately NOT in QUEUES — that map drives
# the tabs and the retry engine, and this pile belongs to Rescue's tab.
_DECIDABLE = set(QUEUES.values()) | {"Not Delivered"}

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
    "cancel": "Cancelled",
    # Desk parity: agents mark ~23 duplicate orders a month there.
    "duplicate": "Duplicated",
    # Undo: pull a wrongly-decided order back into the pending queue.
    "reopen": "Pending",
}
# How long an order rests before it resurfaces at the top of its queue.
_RETRY_HOURS = {"dna": 4, "followup": 24}

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

# When is a retry order due? ONE definition, because next_up draws the plan
# and next_order hands out the work, and a queue pane that disagrees with the
# queue is worse than no pane.
#
# It used to mean "it has a timer and the timer has passed". That is only ever
# true of orders decided in the PORTAL: custom_next_call_at is written by
# act(), and a decision taken in the DESK writes none. So a Desk "Did not
# Answer" landed in the agent's tab and was never handed back — not resting,
# not due, simply unreachable by the one screen built to work the queue.
#
# Measured on prod 2026-09-09: 127 of the 140 retry-status orders in hand (105
# Did not Answer, 22 Follow Up) carried no timer, every one with zero call
# attempts logged, 36 of them past 72 hours and the oldest 14 days. Workspace
# was handing the two agents who carry that queue 3 orders and 2 orders; this
# gives them 56 and 68 — work they already own and had no way to reach.
#
# An order with no timer has been waiting since it was created and nobody
# scheduled a call for it: overdue, not resting. Dating it by creation says
# that, and also floats the most neglected to the top. It is the same
# expression the board's retry tabs already window on, so Workspace serves
# exactly what those tabs show.
#
# _PARKED stays out — On Hold with no attempt AND no timer is the legacy pile
# that never entered the call flow. That pile is 0 today, so this guard holds
# a door rather than closing one.
# Status a decision landed on -> the tally key. Shared by the "my day" tally
# and anything else reading the Desk trail in this module.
_ST_ACTION_MAP = {"Confirmed": "confirm", "Cancelled": "cancel",
                  "Did not Answer": "dna", "Follow Up": "followup",
                  "Duplicated": "duplicate"}

# Worked, but never before the live queue.
#
# Deliberately NOT added to QUEUES: that map drives the tabs, the retry
# timers and the holding cap, and these two belong to none of those. They are
# a TAIL on the serve order — real work an agent should be handed once the
# live queue is empty, and last every time.
#
# Duplicated is here because Ahmed settled it on 2026-09-16: "a Duplicated
# order is a parked call, not a closed one" — act() already lets an agent
# decide one on the spot. Not Delivered is here because all 16 live ones
# carry no parcel at all (logistics status Pending, no AWB, no pick list):
# the status is a verdict on the CUSTOMER, which makes "does he still want
# it?" a confirmation question.
_TAIL_STS = ("Duplicated", "Not Delivered")

_DUE_AT = "COALESCE(so.custom_next_call_at, so.creation)"
_DUE = f"{_DUE_AT} <= %(now)s AND NOT ({_PARKED})"


from logistics_portal.api.orders import (  # noqa: E402
    PHONE_SOURCE as _PHONE_SOURCE, seller_from_tags as _seller_from_tags)


def _not_cold():
    """Work an agent may be HANDED. A phone sale is not.

    One of ours already had this conversation: the order was written as a
    Shopify draft from the admin, which is what the team does after selling
    over the phone. Handing it to the queue as Pending phones a customer who
    said yes minutes ago — Ahmed reported it on 2026-09-21, and it is a real
    call, to a real person, for the second time.

    Only PENDING is held back, and that is the whole of the rule. The moment
    a human decides something on a phone order — a Follow Up, a Did not
    Answer — it is ordinary lane work again and comes back through every
    pass. Nothing is hidden: the order still counts, still appears in the
    Pending tab wearing its seller's name, and can still be opened and
    decided. It is only never THRUST at somebody.

    Keyed on Shopify's source_name, never on the tag. Measured on prod over
    4,000 tagged orders: 3,086 distinct tag values, 6% of drafts carrying no
    tag at all, and a seller nobody had listed. See install._SO_SOURCE_FIELDS.

    Degrades open, not shut: before the field exists (or on an order that
    predates it) the expression is true, so the queue behaves exactly as it
    does today."""
    if not frappe.get_meta("Sales Order").has_field("custom_order_source"):
        return "1 = 1"
    return ("NOT (so.custom_sales_status = 'Pending' AND "
            "COALESCE(so.custom_order_source, '') = 'shopify_draft_order')")


# ── The day's target ─────────────────────────────────────────────────────
# A single number for everyone was fiction. Measured over 30 days of live
# work: the median working day in this lane is 70 decisions, p75 is 91 and
# p90 is 115, while the setting said 40 — under the median, so most people
# "hit target" before lunch and the ring stopped meaning anything. And on the
# same day one agent had 68 workable orders in front of her and another had
# one; the same 40 was absurd at both ends.
#
# So the target is the work actually in front of THIS person today —
# what they have already decided plus what they can still decide right now —
# held inside a band the team itself defines. The floor keeps an empty queue
# from producing a target of zero; the ceiling keeps a dumped backlog from
# setting a bar nobody in this lane has ever cleared.
#
# It stays stable through the day by construction: as an order moves from
# "workable" to "decided" the sum does not change. It only rises when new
# work is genuinely allocated.
_CEIL_CACHE = "lp_cf_day_ceiling"


def _team_day_ceiling():
    """p90 of per-agent working-day decision counts over 30 days.

    p90 and not the maximum: one agent once put 1,659 orders through the Desk
    in a single day with a bulk operation, and a ceiling set by that would be
    a bar nobody could reach by making phone calls.

    Counts Version ROWS rather than parsing each one's payload — a save that
    touches the status is a decision, and this only has to be accurate enough
    to place a percentile. Cached 6h; the shape of a working day does not
    move faster than that.
    """
    hit = frappe.cache().get_value(_CEIL_CACHE)
    if hit:
        try:
            return int(hit)
        except Exception:
            pass
    rows = frappe.db.sql(
        """SELECT n FROM (
             SELECT COUNT(*) n FROM `tabVersion` v
             JOIN `tabSales Order` so ON so.name = v.docname
             WHERE v.ref_doctype = 'Sales Order' AND so.company = %(co)s
               AND v.owner NOT IN %(auto)s
               AND v.creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)
               AND v.data LIKE '%%custom_sales_status%%'
             GROUP BY v.owner, DATE(v.creation)
           ) x ORDER BY n""", {"co": _CO, "auto": _AUTOMATION_USERS})
    vals = [int(r[0] or 0) for r in rows]
    if not vals:
        return 0
    ceiling = vals[int(round((len(vals) - 1) * 0.9))]
    frappe.cache().set_value(_CEIL_CACHE, ceiling, expires_in_sec=21600)
    return ceiling


def day_target(user=None):
    """How many decisions this person should get through today.

    A manager who sets `dayTargetMode` to "fixed" gets the old flat number
    back — this is a default, not a policy the code is entitled to impose.
    """
    s = _cf_settings()
    fixed = int(s.get("dayTarget", 40) or 40)
    if str(s.get("dayTargetMode", "auto")).lower() != "auto":
        return fixed
    user = user or frappe.session.user
    today = _clock.floor_today()
    _t0, _t1 = _clock.day_bounds(today)
    # Cached per person per day. The two halves are cheap to want and dear to
    # fetch — reading "what have I decided today" out of `tabVersion` costs
    # 1.7s on its own and 7.0s with the company join, on a 2.95M-row table
    # whose owner+creation index only lands with the pending migrate. This is
    # called on every board load, so without a cache it would undo the work
    # that made the board fast. A target that is up to three minutes old is
    # still the same target.
    _tk = "lp_cf_target_%s_%s" % (user, today)
    _hit = frappe.cache().get_value(_tk)
    if _hit:
        try:
            return int(_hit)
        except Exception:
            pass
    done = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabComment`
           WHERE reference_doctype = 'Sales Order' AND owner = %s
             AND content LIKE 'Confirmation: %%'
             AND creation >= %s AND creation < %s""",
        (user, _t0, _t1))[0][0] or 0)
    done += int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabVersion` v
           JOIN `tabSales Order` so ON so.name = v.docname
           WHERE v.ref_doctype = 'Sales Order' AND so.company = %s
             AND v.owner = %s AND v.creation >= %s AND v.creation < %s
             AND v.data LIKE '%%custom_sales_status%%'""",
        (_CO, user, _t0, _t1))[0][0] or 0)
    ahead = int(frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(sts)s AND {_IN_HAND}
              AND (so.custom_sales_status = 'Pending' OR ({_DUE}))
              AND so._assign LIKE %(me_like)s""",
        {"co": _CO, "sts": tuple(QUEUES.values()),
         "now": str(now_datetime())[:19],
         "me_like": f'%"{user}"%'})[0][0] or 0)
    ceiling = _team_day_ceiling() or fixed
    floor = max(10, int(round(ceiling * 0.15)))
    out = int(min(max(done + ahead, floor), ceiling))
    frappe.cache().set_value(_tk, out, expires_in_sec=180)
    return out


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
        # A day the person picking it lives in. Timestamps are stored on the
        # SITE's clock (Istanbul) and the floor is in Morocco, so "9 September"
        # is not the stored 00:00-24:00 of that date — see api/clock. The
        # BOUNDARIES move, never the column: `col >= a AND col < b` still uses
        # an index, and the indexes are what made this lane fast.
        conds, v = [], {}
        if ok(frm):
            conds.append("{col} >= %(frm)s")
            v["frm"] = _clock.day_bounds(str(frm).strip())[0]
        if ok(to):
            conds.append("{col} < %(to)s")
            v["to"] = _clock.day_bounds(str(to).strip())[1]
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
    if tab not in QUEUES and tab not in DONE_QUEUES and tab not in (
            "monitor", "notdelivered", "citycheck"):
        tab = "pending"
    days = min(max(int(days or 30), 1), 365)
    limit = min(max(int(limit or 30), 1), 100)
    offset = max(int(offset or 0), 0)
    rng, rng_vals = _range(days, frm, to)
    custom_range = "frm" in rng_vals or "to" in rng_vals
    # Site clock, not the DB server's — fresh orders were reading "-2h".
    vals = {"days": days, "limit": limit, "offset": offset,
            "now": str(now_datetime())[:19], **rng_vals}

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
    # Desk/automation confirms never stamp custom_last_call_at (measured:
    # 9,163 of 9,178 Confirmed in 30d carry none) — requiring it emptied the
    # agent's own Confirmed/Cancelled tabs. In the agent scope the
    # custom_allocated_to fence already keeps the automation's mass out, so
    # fall back to the order's last touch; the TEAM scope keeps the strict
    # portal-decision clock (the fallback would pour ~167k automation rows in).
    #
    # Written as two disjoint branches rather than a COALESCE around the
    # column, because COALESCE(a, b) hides BOTH columns from every index: the
    # three queries the done tabs run (the GROUP BY count, the total, the row
    # page) each fell back to a full scan of the 265,656-row table. Measured
    # 2026-09-09 on prod for one agent's Confirmed tab: 1,061 ms for 20 rows
    # (type=range over 103,336 rows + filesort), 322 ms for the count
    # (type=ALL), 1,079 ms for the GROUP BY — 2.0 s of a 2.2 s board load,
    # three queries. Split, each branch is a plain range on a real column and
    # `lp_so_agent_status_idx` covers the whole predicate.
    #
    # The two branches are exactly the COALESCE's two cases, so the rows the
    # tab shows do not change. (custom_last_call_at is set on 67 of 265,656
    # rows — the human decisions taken through this workspace — so the first
    # branch is a handful and the second is the tab.)
    def _decided(a=""):
        return "((%s IS NOT NULL AND %s) OR (%s IS NULL AND %s))" % (
            a + "custom_last_call_at", rng.format(col=a + "custom_last_call_at"),
            a + "custom_last_call_at", rng.format(col=a + "modified"))

    if mine_only:
        d_rng = _decided()
    else:
        d_rng = ("custom_last_call_at IS NOT NULL AND "
                 + rng.format(col="custom_last_call_at"))

    # A search makes every tab chip a question: "is my customer in THIS one?"
    # The counts used to ignore the search box entirely, so typing a phone left
    # all ten chips showing their unfiltered totals while the list underneath
    # showed the one match — click "Follow up 13" and get one row, or none.
    # Measured 2026-09-09: searching a phone gave counts 13 / rows 1 for one
    # agent and counts 1 / rows 0 for another. Now the same predicate the rows
    # use narrows the chips, which also turns the chip strip into the answer to
    # "which tab is this customer's order in".
    #
    # Built here, used by both — and like the row search it drops the date
    # window, because a lookup that answers "not found" for an order sitting
    # right there is worse than no search at all.
    # Some count queries alias the table (`so.`) and some do not, so both forms
    # are built from the SAME parts rather than string-munged out of each other.
    q_txt = str(q or "").strip()
    q_cnt = q_cnt_so = ""
    _q_vals = {}
    if q_txt:
        _d = q_txt.lstrip("#").strip()

        def _cols(a):
            if _d.isdigit():
                cols = [f"{a}name = %(qexact)s", f"{a}name LIKE %(qpre)s"]
                if len(_d) >= 8:
                    cols += [f"{a}custom_customer_phone LIKE %(qphone)s",
                             f"{a}custom_shipping_phone LIKE %(qphone)s"]
            else:
                cols = [f"{a}customer_name LIKE %(qlike)s",
                        f"{a}name LIKE %(qpre)s"]
            return " AND (" + " OR ".join(cols) + ")"

        if _d.isdigit():
            _q_vals["qexact"] = "#" + _d
            _q_vals["qpre"] = _d + "%"
            # Anchored on purpose: the row search only reaches the phone
            # columns for 8+ digits because one unanchored LIKE over them
            # costs 1.13s on this table. The chips obey the same rule.
            if len(_d) >= 8:
                _q_vals["qphone"] = "%" + _d
        else:
            _q_vals["qlike"] = f"%{q_txt}%"
            _q_vals["qpre"] = q_txt + "%"
        q_cnt, q_cnt_so = _cols(""), _cols("so.")
        rng_vals.update(_q_vals)
        vals.update(_q_vals)

    def _rng_or_all(sql_range):
        """During a search the window is irrelevant — same rule the rows follow."""
        return "1 = 1" if q_txt else sql_range

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
                      AND custom_sales_status IN %(sts)s{me_q}{q_cnt}
                      AND {in_hand} AND {_rng_or_all(rng_sql)}
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
                  AND custom_sales_status IN %(sts)s{me_done}{q_cnt}
                  AND {_rng_or_all(d_rng)}
                GROUP BY custom_sales_status""",
            {"sts": tuple(_AUTOMATION_DONE.values()), "co": _CO, **rng_vals}, as_dict=True):
        for k, v in _AUTOMATION_DONE.items():
            if v == r.s:
                counts[k] = int(r.n or 0)
    # Duplicated is NOT a portal decision on this site: measured 2026-09-15,
    # 59 of 61 marked in 30 days came from the Administrator automation and
    # none through act(). So it is scoped like a WORKING queue — by the
    # ERPNext assignment (_assign), the owner the desk divides work by — not
    # by custom_allocated_to (the intake round-robin), which agreed with the
    # assignee on only 16 of those 59 and showed each agent somebody else's
    # duplicates. Its rows predate custom_last_call_at, so it is dated by
    # creation as well.
    counts["duplicated"] = int(frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabSales Order`
            WHERE docstatus = 1 AND company = %(co)s
              AND custom_sales_status = 'Duplicated'{me_q}{q_cnt}
              AND {_rng_or_all(q_rng)}""",
        {"co": _CO, **rng_vals})[0][0])

    # Monitoring: live orders whose customer has taken 2+ parcels and kept
    # none of them. Nothing is blocked — the team looks and decides. Measured:
    # this group still takes delivery 27% of the time.
    # Both heavy sets below are fetched ONLY if something on this load
    # actually needs them. They used to be computed unconditionally, above
    # the very caches that exist to avoid them: risky_phones() is a ~2.5s
    # scan of every Delivery Note (cached 30 min) and _accepted_cities() a
    # 180-day scan of shipped orders (cached 10 min), so whichever board load
    # happened to land on an expired key paid the full scan for a tab that
    # wasn't even open. Measured 2026-09-09 on prod: 1,817 ms + 256 ms of a
    # 5,320 ms cold load, versus 0 ms once warm.
    _lazy = {}

    def risky_set():
        if "risky" not in _lazy:
            from logistics_portal.api.customers import risky_phones
            _lazy["risky"] = tuple(risky_phones()) or ("",)
        return _lazy["risky"]

    def accepted_set():
        if "acc" not in _lazy:
            from logistics_portal.api.city import _accepted_cities
            _lazy["acc"] = tuple({c.lower() for c in _accepted_cities()}) or ("",)
        return _lazy["acc"]
    # The monitor count crosses a ~6.8k-phone IN list with a per-row REGEXP —
    # the single heaviest piece of a cold board load. Cache it per scope; the
    # exact rows are only computed when the monitor tab itself is open.
    _mck = "lp_cf_monitor_" + (me if mine_only else "all")
    _mc = frappe.cache().get_value(_mck)
    if _mc is not None and tab != "monitor" and not q_txt:
        counts["monitor"] = int(_mc)
    else:
        counts["monitor"] = int(frappe.db.sql(
            f"""SELECT COUNT(*) FROM `tabSales Order` so
                WHERE so.docstatus = 1 AND so.company = %(co)s
                  AND so.custom_sales_status IN %(sts)s{me_so}
                  AND {_IN_HAND} AND {_CUST_KEY} IN %(risky)s{q_cnt_so}""",
            {"sts": tuple(QUEUES.values()), "co": _CO, "risky": risky_set(), **_q_vals,
             **({"me_like": f'%"{me}"%'} if mine_only else {})})[0][0])
        if not q_txt:
            # 900s: these two counts are the last cold pieces left in a board
            # load (~1.7s together per scope). Opening the tab itself always
            # recomputes, so the chip being minutes stale costs nothing.
            frappe.cache().set_value(_mck, counts["monitor"], expires_in_sec=900)

    # City check: the agent's own confirmed orders whose city Cathedis can't
    # turn into an AWB (Arabic / junk / never-seen town). SAME predicate as
    # the floor's City Check page — one shared pool, whoever fixes it first
    # (confirmation or logistics) clears it for both.
    from logistics_portal.api.picking import _BAD_CITY, _EFF_CITY
    # Four correlated address subqueries deep and it ran on EVERY board load,
    # for every tab — cache it per scope exactly like the monitor count above.
    _cck = "lp_cf_citycheck_" + (me if mine_only else "all")
    _cc = frappe.cache().get_value(_cck)
    if _cc is not None and tab != "citycheck" and not q_txt:
        counts["citycheck"] = int(_cc)
    else:
        counts["citycheck"] = int(frappe.db.sql(
            f"""SELECT COUNT(*) FROM `tabSales Order` so
                WHERE so.docstatus = 1 AND so.company = %(co)s
                  AND so.custom_sales_status = 'Confirmed'
                  AND so.custom_logistics_status = 'Pending'
                  AND so.creation >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                  AND NOT EXISTS (SELECT 1 FROM `tabPick List Item` pli
                                  JOIN `tabPick List` p ON p.name = pli.parent
                                  WHERE pli.sales_order = so.name
                                    AND p.docstatus < 2)
                  AND ({_BAD_CITY}
                       OR LOWER(TRIM(COALESCE({_EFF_CITY}, ''))) NOT IN %(acc)s)
                  {me_so}{q_cnt_so}""",
            {"co": _CO, "acc": accepted_set(), **_q_vals,
             **({"me_like": f'%"{me}"%'} if mine_only else {})})[0][0])
        if not q_txt:
            frappe.cache().set_value(_cck, counts["citycheck"], expires_in_sec=900)

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
              AND custom_sales_status = 'Not Delivered'{me_q}{q_cnt}
              AND {_rng_or_all(nd_rng)}""", nd_vals)[0][0])

    vals["co"] = _CO
    if tab == "monitor":
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status IN %(statuses)s", _IN_HAND,
                 f"{_CUST_KEY} IN %(risky)s"]
        vals["statuses"] = tuple(QUEUES.values())
        vals["risky"] = risky_set()
    elif tab in _AUTOMATION_DONE:
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status = %(status)s"]
        # Same clock split as the counts: agents (allocated_to-fenced) see
        # their desk-era decisions too; the team view stays portal-stamped.
        if mine_only:
            conds.append(_decided("so."))
        else:
            conds.append("so.custom_last_call_at IS NOT NULL")
            conds.append(rng.format(col="so.custom_last_call_at"))
        vals["status"] = _AUTOMATION_DONE[tab]
    elif tab == "duplicated":
        # Human-only decision with legacy rows that predate custom_last_call_at
        # — date by creation (mirrors the count above) so the tab isn't empty.
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status = 'Duplicated'",
                 rng.format(col="so.creation")]
    elif tab == "citycheck":
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status = 'Confirmed'",
                 "so.custom_logistics_status = 'Pending'",
                 "so.creation >= DATE_SUB(NOW(), INTERVAL 90 DAY)",
                 """NOT EXISTS (SELECT 1 FROM `tabPick List Item` pli
                     JOIN `tabPick List` p ON p.name = pli.parent
                     WHERE pli.sales_order = so.name AND p.docstatus < 2)""",
                 f"""({_BAD_CITY}
                     OR LOWER(TRIM(COALESCE({_EFF_CITY}, ''))) NOT IN %(acc)s)"""]
        vals["acc"] = accepted_set()
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
    # Duplicated rides with the working queues: the mark is the automation's,
    # the order is still the assignee's (see the count above).
    if mine_only:
        if tab in _AUTOMATION_DONE:
            conds.append("so.custom_allocated_to = %(me)s")
        else:
            conds.append("so._assign LIKE %(me_like)s")
    q = str(q or "").strip()
    if q:
        # A search is a LOOKUP, not a report: the date window is dropped, or
        # an order older than the picked range answers "not found" while it
        # sits right there in the system.
        # Drop EVERY date/recency fence, whatever placeholder it used: the
        # notdelivered tab dates on %(ndays)s and the team-scope done tabs add
        # a bare `custom_last_call_at IS NOT NULL` — a name-based strip left
        # both standing, so searching still answered "not found" for 99.8% of
        # confirmed orders (measured: 9,163 of 9,178 carry no last_call_at).
        _date_marks = ("%(days)s", "%(frm)s", "%(to)s", "%(ndays)s",
                       "custom_last_call_at IS NOT NULL")
        conds = [c for c in conds if not any(m in c for m in _date_marks)]
        digits_only = q.lstrip("#").strip()
        if digits_only.isdigit():
            # Order numbers are '#257135'. Anchored patterns keep the index
            # usable; the old '%…%' over four columns scanned the whole table.
            # Measured on prod: the order-number lookup is 0.00s while ONE
            # phone LIKE '%digits' costs 1.13s — so the phone columns are only
            # searched when the query is long enough to actually be a phone.
            vals["qexact"] = "#" + digits_only
            vals["qpre"] = digits_only + "%"
            parts = ["so.name = %(qexact)s", "so.name LIKE %(qpre)s"]
            if len(digits_only) >= 8:
                vals["qphone"] = "%" + digits_only
                parts += ["so.custom_customer_phone LIKE %(qphone)s",
                          "so.custom_shipping_phone LIKE %(qphone)s"]
            conds.append("(" + " OR ".join(parts) + ")")
        else:
            vals["qlike"] = f"%{q}%"
            vals["qpre"] = q + "%"
            conds.append("""(so.customer_name LIKE %(qlike)s
                            OR so.name LIKE %(qpre)s)""")
    where = " AND ".join(conds)
    total = frappe.db.sql(f"SELECT COUNT(*) FROM `tabSales Order` so WHERE {where}",
                          vals)[0][0]
    # Retry queues surface what's DUE first (next_call in the past, oldest
    # deferral first); pending is simply oldest-first.
    if tab in _AUTOMATION_DONE:
        # newest decision first (desk decisions fall back to last touch)
        order_by = "COALESCE(so.custom_last_call_at, so.modified) DESC"
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
    src_col = ("so.custom_order_source"
               if _m.has_field("custom_order_source") else "NULL")
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
                   GREATEST(0, TIMESTAMPDIFF(HOUR, so.creation, %(now)s)) AS age_h,
                   COALESCE(so.custom_call_attempts, 0) AS attempts,
                   so.custom_last_call_at AS last_call,
                   so.custom_next_call_at AS next_call,
                   so.custom_allocated_to AS agent,
                   so.custom_sales_status AS status,
                   so.custom_logistics_status AS stage,
                   so.custom_track_shipment_status AS track,
                   so.custom_awb AS awb,
                   COALESCE({s_r1}, 0) AS r1,
                   COALESCE({s_r2}, 0) AS r2,
                   {reason_col} AS reason,
                   {src_col} AS src,
                   so._user_tags AS tags
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

    today = _clock.floor_today()
    _d0, _d1 = _clock.day_bounds(today)
    mine = {"confirm": 0, "cancel": 0, "dna": 0, "followup": 0, "onhold": 0,
            "duplicate": 0}
    for r in frappe.db.sql(
            """SELECT c.content, COUNT(*) n FROM `tabComment` c
               WHERE c.reference_doctype = 'Sales Order' AND c.owner = %s
                 AND c.creation >= %s AND c.creation < %s
                 AND c.content LIKE 'Confirmation: %%'
               GROUP BY c.content""",
            (me, _d0, _d1), as_dict=True):
        for k in mine:
            if r.content.startswith(f"Confirmation: {k}"):
                mine[k] += int(r.n or 0)
    # ...and the SAME day's Desk decisions. The scoreboard the agent stares at
    # all day read the comment trail alone, so an hour worked in the Desk left
    # the ring at zero while day_target() counted that hour into the goal —
    # the bar grows, the fill doesn't, and the agent concludes the game is
    # rigged. The trails are disjoint (verified: 0 of 39 portal decisions also
    # write a Version row), so adding them cannot double-count. Cheap since
    # lp_version_owner_idx: one agent-day is a few hundred rows.
    import json as _mj
    for (data,) in frappe.db.sql(
            """SELECT v.data FROM `tabVersion` v
               WHERE v.ref_doctype = 'Sales Order' AND v.owner = %s
                 AND v.creation >= %s AND v.creation < %s
                 AND v.data LIKE '%%custom_sales_status%%'""",
            (me, _d0, _d1)):
        try:
            changed = _mj.loads(data or "{}").get("changed") or []
        except Exception:
            continue
        for f in changed:
            if f and f[0] == "custom_sales_status":
                a = _ST_ACTION_MAP.get(f[2])
                if a in mine:
                    mine[a] += 1

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
        "myTotal": my_total, "myTarget": day_target(),
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
            # Where the warehouse and the carrier have taken it — a confirmed
            # order's next question is always "and where is it now?".
            "stage": (r.stage or "").strip(),
            "track": (r.track or "").strip(),
            "awb": (r.awb or "").strip(),
            "reason": (r.reason or "").strip(),
            # One of ours already spoke to this customer. The chip is why the
            # order sits in the tab without ever being handed out.
            "phoneSale": (r.src or "") == _PHONE_SOURCE,
            "soldBy": _seller_from_tags(r.tags),
            "cust": hist.get(digits(r.phone)) if r.phone else None,
            # How hard the automation already chased this one.
            "chased": int(r.r2 or 0) and 2 or (int(r.r1 or 0) and 1 or 0),
            # First-call SLA: never touched and older than the target. Only
            # meaningful while the order is still ours to call.
            # Only the LIVE call queues carry a first-call clock: a citycheck
            # row is already confirmed and a notdelivered parcel already
            # shipped — the red badge was a lie on both tabs.
            "slaBreached": bool(tab in QUEUES
                                and int(r.attempts or 0) == 0
                                and int(r.age_h or 0) > sla_h),
        } for r in rows],
        "mine": mine,
        "reasons": effective_reasons(),
        "serverNow": str(now_datetime())[:19],
    }


def _free_card(order):
    """A decision ends the hold. Leaving it set would keep the order out of
    every list for three minutes after it stopped being anybody's work."""
    try:
        if order and _has_open_fields():
            frappe.db.set_value("Sales Order", order,
                                {"custom_cc_open_by": "", "custom_cc_open_at": None},
                                update_modified=False)
    except Exception:
        pass


def _first_touch_summary(mins, untouched, sla_min):
    """median / p90 / inside-SLA over the orders a human actually touched."""
    ms = sorted(mins)
    if not ms:
        return {"median": None, "p90": None, "slaPct": None,
                "n": 0, "untouched": untouched}
    return {
        "median": round(ms[len(ms) // 2] / 60.0, 1),
        "p90": round(ms[min(int(len(ms) * 0.9), len(ms) - 1)] / 60.0, 1),
        "slaPct": round(100.0 * sum(1 for m in ms if m <= sla_min) / len(ms), 1),
        "n": len(ms), "untouched": untouched,
        "slaH": round(sla_min / 60.0, 1),
    }


def _first_touch(order, user=None):
    """Stamp the moment a human first laid hands on this order.

    Write-once, by design. Everything else in this lane is a LAST-touch
    field — custom_last_call_at is rewritten by every act() — and that is
    why the section report claimed a 40–174 hour first response: it was
    reading the final decision and calling it the first touch.

    Cheap enough to call from every touch point: one indexed read, and a
    write only the first time. Never raises — a metric must not be able to
    break a decision."""
    try:
        if not order or not frappe.get_meta("Sales Order").has_field("custom_first_touch_at"):
            return
        if frappe.db.get_value("Sales Order", order, "custom_first_touch_at"):
            return
        who = user or frappe.session.user
        if who in _AUTOMATION_USERS:
            return
        frappe.db.set_value("Sales Order", order, {
            "custom_first_touch_at": now_datetime(), "custom_first_touch_by": who,
        }, update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "confirmation._first_touch")


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
    # Somebody is on the phone with this customer right now. _assign says
    # whose queue it is; this says whose call it is, and only the second one
    # stops two people talking to the same person at once.
    for n in names:
        who, since = _open_holder(n)
        if who and who != frappe.session.user:
            frappe.throw(f"lp:ccBusy|{who.split('@')[0]}", frappe.PermissionError)
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
    if so.custom_sales_status not in _DECIDABLE:
        # Reopening a decision the lane already took: allowed only while the
        # order hasn't moved on physically. Once it's picked or shipped, the
        # warehouse owns it and a status flip here would lie about reality.
        if so.custom_sales_status not in DONE_QUEUES.values():
            frappe.throw(f"Order is {so.custom_sales_status or 'unset'} — outside the "
                         "confirmation lane. Refresh the queue.")
        # A Duplicated order is a parked call, not a closed one: the agent
        # who opens it and reaches the customer decides on the spot — the
        # reopen-then-decide detour was two clicks for one truth (Ahmed,
        # 2026-09-16). Same fences as reopen: nothing the warehouse holds.
        direct = so.custom_sales_status == "Duplicated" and action in ("confirm", "dna", "followup", "cancel")
        if action != "reopen" and not direct:
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
    if so.custom_sales_status == "Not Delivered":
        # Decidable only while the order carries no parcel — which is what a
        # Not Delivered IS here. Measured 2026-09-12: all 29 had no delivery
        # note, no AWB and no pick list, because the status is a verdict on
        # the CUSTOMER (never takes delivery), not a parcel that failed in
        # transit. Should one ever arrive carrying a live parcel, it is a
        # rescue case and this lane must keep its hands off it.
        stage = frappe.db.get_value("Sales Order", order, "custom_logistics_status")
        if stage and stage not in ("Pending", ""):
            frappe.throw(f"Can't decide — the order is already {stage} in the "
                         "warehouse. Route it through Rescue.")
        if frappe.db.exists("Pick List Item",
                            {"sales_order": order, "docstatus": ["<", 2]}):
            frappe.throw("Can't decide — the order is already on a pick list.")
    note = (note or "").strip()
    if action == "cancel":
        if not note:
            frappe.throw("A cancel needs a reason.")
        opts = reason_options()
        if opts and note not in opts:
            frappe.throw("Pick a reason from the list — free text here would "
                         "invent a category the reports can't group.")
        # This used to be a wall. It told the agent, in English, on a French
        # and Arabic screen, to "route it through Rescue/Exceptions" or "ask
        # the dispatcher to pull it first" — and neither of those exists. No
        # dispatcher pull was ever built, and Rescue lists parcels the CARRIER
        # has already failed, so a healthy parcel on its way appears in none
        # of its tabs. The cancel was simply lost: the order stayed Confirmed
        # and shipped. September: 180 parcels refused at the customer's door,
        # 309 more returned by Cathedis as "customer cancelled by phone", and
        # 302 of those are still marked Confirmed here.
        #
        # So this is a HANDOVER now, not a refusal. The key routes the agent
        # into api.stop, which accepts the customer's words at any stage and
        # decides what can be done about them from where the goods actually
        # are.
        from logistics_portal.api.stop import stage_of
        st_stage, st_mode = stage_of(order)
        if st_mode != "cancel_now":
            frappe.throw(f"lp:stopNeeded|{st_stage}")

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
    # Reaching the customer counts, however the call ended. This used to
    # count only the retries (dna/followup), so the field answered "how many
    # times did we fail to reach them" while every report read it as "how
    # many calls did this take". Measured 2026-09-21: only 714 of 11,123
    # decided orders carried any attempt at all — 6.4% — which made
    # avgAttempts read 0.0 for the whole team and put the one coaching
    # number Ahmed wants out of reach.
    #
    # reopen and duplicate stay out: an undo is not a call, and spotting a
    # duplicate is a desk observation, not a conversation.
    if action in _ATTEMPT_ACTIONS:
        attempts += 1
        updates["custom_call_attempts"] = attempts
    if action in _RETRY_HOURS:
        s = _cf_settings()
        hours = {"dna": s["retryDna"], "followup": s["retryFollowup"],
                 }[action]
        updates["custom_next_call_at"] = add_to_date(now, hours=hours)
    else:
        updates["custom_next_call_at"] = None
    if action == "cancel" and frappe.get_meta("Sales Order").has_field(
            "custom_cancellation_reason"):
        # Validated against the Select above, so the desk's reports and the
        # existing dashboard group portal cancels alongside desk ones.
        updates["custom_cancellation_reason"] = note
    frappe.db.set_value("Sales Order", order, updates, update_modified=True)
    _first_touch(order)

    doc = frappe.get_doc("Sales Order", order)
    doc.add_comment("Comment",
                    f"Confirmation: {action}"
                    + (" (from duplicated)" if so.custom_sales_status == "Duplicated" and action != "reopen" else "")
                    + (" (bulk)" if _bulk else "")
                    + (f" (attempt {attempts})" if action in _RETRY_HOURS else "")
                    + (f" — {note}" if note else "")
                    + f" · by {frappe.session.user}")
    _free_card(order)
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
    # The decision that was just taken belongs on the agent's own dashboard
    # now, not up to a minute from now — their cached report is theirs alone,
    # so dropping it costs nobody else anything.
    frappe.cache().delete_keys("lp_myrep_%s" % frappe.session.user)
    unpin_after_decision(order)
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
            "Sales Order", name,
            ["docstatus", "custom_sales_status", "company",
             "custom_logistics_status"], as_dict=True)
        if not so or so.docstatus != 1 or so.company != _CO \
                or so.custom_sales_status not in QUEUES.values():
            skipped.append(name)
            continue
        # Same physical guards as a single cancel: an order the warehouse has
        # already picked must not become a cancelled parcel in a tote.
        if (so.custom_logistics_status or "") not in ("", "Pending") \
                or frappe.db.exists("Pick List Item",
                                    {"sales_order": name, "docstatus": ["<", 2]}):
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
    frappe.cache().delete_keys("lp_myrep_%s" % frappe.session.user)
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
    if frappe.db.get_value("Sales Order", order, "company") != _CO:
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
    # "auto" (default): each agent's target is the work in front of them
    # today, inside the band the team's own 30 days define — see day_target().
    # "fixed" pins everyone to dayTarget below, which is what the lane had
    # before and is kept so a manager can take the wheel back.
    "dayTargetMode": "auto",
    "dayTarget": 40,      # the FIXED-mode number, and the fallback when the
                          # team has no history to measure a band from. NOT
                          # the floor's dayTarget (200 on production: that
                          # counts orders picked in a warehouse, not calls
                          # made at a desk)
    # `reasons` is the manager's QUICK-PICK subset of the real vocabulary —
    # never a list of our own words. The vocabulary itself lives on the Select
    # field custom_cancellation_reason (15 options the desk, the existing
    # dashboard and every historical report already group by). Empty = show
    # them all.
    "reasons": [],
    # Cancels that are OURS, not the agent's.
    #
    # Measured on production over 30 days: of 1,970 cancels charged to the
    # team, 693 worth 162,659 MAD were an out-of-stock, a duplicate, or bad
    # data on the order. Scoring an agent on those is scoring them on the
    # warehouse and the website. Excluding them moves the best agent from
    # 58.5% to 75.7% and changes who is first.
    #
    # A SETTING and not a constant, because the bucketing is a business call
    # and not a technical one: whether "Modification" is our fault or the
    # customer changing their mind is Ahmed's to decide, and the answer can
    # change without a deploy. The default is the three nobody argues about;
    # Modification is deliberately left OUT of it.
    #
    # An empty list is honest too — it means "charge everything to the agent",
    # which is exactly what the report did before this existed.
    # All four verified against the field's own 15 options before being
    # written here — a name that does not match exactly would silently
    # exclude nothing, and the rate would move for no visible reason.
    # "Out of stock & Modified" is one order in the window; it is in anyway,
    # because it is unambiguously a stock failure and costs nothing to be
    # right about.
    "ownReasons": ["Out of stock", "Out of stock & Modified",
                   "Duplicated", "Wrong Info"],
    "admins": [],         # section admins (user emails)
    # Save-the-sale discount caps for a plain agent (managers/section admins
    # are uncapped). Measured need: 438 discount edits/30d were happening on
    # the desk with no cap and no trail.
    "discountCapPct": 15,
    "discountCapAmt": 50,
    # ── the shared pool ──
    # The lane's work is fenced by the Desk's "Sales Person Assignment Rule",
    # a record with exactly three names in it that nobody opens. Anyone not on
    # that list gets no orders however free they are, and an order sitting in
    # a busy agent's slice is invisible to an idle colleague. Measured
    # 2026-09-18: first touch is 9.5h at the median and 2.4 DAYS at p90, while
    # 80 of the 138 open orders were due and untouched for over two hours.
    #
    # So when an agent's own slice runs dry, serve-next reaches into everyone
    # else's — but only work that is actually waiting. An order with a
    # next_call_at in the future is a promise to a customer (58 of those 138)
    # and is never taken, whoever holds it. That line is what makes this
    # colleagues covering for each other instead of the system stealing work.
    "poolEnabled": True,
    "poolAfterH": 2,      # untouched this long and it belongs to whoever is free
    # Phase 2. With the Desk rule off, orders arrive belonging to nobody and
    # the pool is the only way they reach a person — so an UNASSIGNED order
    # is available at once, not after poolAfterH. Waiting two hours to hand
    # out work nobody owns would be the old 9.5-hour first touch with extra
    # steps.
    #
    # Presence answers the question the old rule could not: a fixed list of
    # names keeps feeding someone who went home. The floor already clocks in
    # and out on HRMS with GPS (247 punches in seven days, IN/OUT clean), and
    # all four agents have Active employee records, so the portal can simply
    # read it. It NEVER blocks an agent from their own queue — only from
    # taking more out of the shared one.
    "poolPresence": True,
    # Nobody should be able to hoover the pool. Applies to pool draws only;
    # their own work is always theirs.
    "poolMax": 20,
    # WHO is on confirmation duty. Empty = everyone the portal calls a
    # confirmation agent, which is the safe default and what shipped first.
    #
    # It turned out that default is wrong here: the role comes from a
    # hard-coded seed map, and five people carry it who have never made a
    # confirmation decision — two of them work social media. The pool would
    # have handed them live customers.
    #
    # Yes, this is a list of names again, which is what the Desk rule was.
    # The difference is what the list DOES. That one was the assignment, so
    # being off it meant getting nothing while the work piled into one
    # person's slice, invisibly, in a record nobody opened. This one only
    # says who may draw from the shared pool: everyone still sees their own
    # work, the lead edits it in the portal, and the team panel right next to
    # it shows who is on duty, who is present and who is idle. A list you can
    # see and a list you cannot are not the same object.
    "poolRoster": [],
    # A customer who ordered five minutes ago is the warmest call in the
    # building; a Did-not-Answer from yesterday is the coldest. The queue was
    # ordered purely by "who has waited longest", which reads fair and is
    # exactly backwards: measured 2026-09-18, a brand-new order sat at
    # position 47 of 47 behind 34 DNAs and 6 follow-ups, so the freshest lead
    # in the pool was the last one anybody would reach.
    #
    # New orders now go first, oldest new first among themselves; everything
    # else keeps the oldest-waiting order behind them. Set false to go back
    # to one strict waiting line.
    "poolNewFirst": True,
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
    for k in ("retryDna", "retryFollowup", "retryOnhold", "slaFirstCallH",
              "poolAfterH"):
        if k in settings:
            v = int(settings[k])
            if not (1 <= v <= 168):
                frappe.throw(f"{k} must be between 1 and 168 hours.")
            out[k] = v
    if "poolEnabled" in settings:
        out["poolEnabled"] = bool(settings["poolEnabled"])
    if "poolPresence" in settings:
        out["poolPresence"] = bool(settings["poolPresence"])
    if "poolMax" in settings:
        v = int(settings["poolMax"])
        if not (1 <= v <= 500):
            frappe.throw("poolMax must be between 1 and 500.")
        out["poolMax"] = v
    if "poolNewFirst" in settings:
        out["poolNewFirst"] = bool(settings["poolNewFirst"])
    if "poolRoster" in settings:
        from logistics_portal.api.auth import resolve_role as _rr
        roster = [str(a).strip().lower() for a in (settings["poolRoster"] or []) if str(a).strip()]
        for a in roster:
            if not frappe.db.exists("User", a):
                frappe.throw(f"Unknown user: {a}")
            # A roster entry without a live lane role is a silent no-op — the
            # gate reads the role first, so the name would simply never match.
            if _rr(a) not in ("confirmation", "manager"):
                frappe.throw(f"{a} has no confirmation role.")
        out["poolRoster"] = roster[:50]
    if "dayTargetMode" in settings:
        v = str(settings["dayTargetMode"]).strip().lower()
        if v not in ("auto", "fixed"):
            frappe.throw("dayTargetMode must be 'auto' or 'fixed'.")
        out["dayTargetMode"] = v
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
    if "ownReasons" in settings:
        opts = reason_options()
        own = [str(r).strip() for r in (settings["ownReasons"] or []) if str(r).strip()]
        bad = [r for r in own if r not in opts]
        if bad:
            frappe.throw("Not a cancellation reason on the Sales Order: "
                         + ", ".join(bad[:3]))
        # No floor: clearing it is a real choice — it puts every cancel back
        # on the agent, which is what the report did before.
        out["ownReasons"] = own
    if "admins" in settings:
        from logistics_portal.api.auth import resolve_role
        if resolve_role(frappe.session.user) != "manager":
            frappe.throw("Only the portal manager can change section admins.",
                         frappe.PermissionError)
        admins = [str(a).strip().lower() for a in (settings["admins"] or []) if str(a).strip()]
        for a in admins:
            if not frappe.db.exists("User", a):
                frappe.throw(f"Unknown user: {a}")
            # The _is_*_admin checks ignore users without a live CC role —
            # accepting one here would be a silent no-op.
            if resolve_role(a) not in ("confirmation", "cs", "tracking",
                                       "manager"):
                frappe.throw(f"{a} has no contact-center role — assign one "
                             "in Team first.")
        out["admins"] = admins[:10]
    frappe.db.set_default(_CF_KEY, _json.dumps(out))
    frappe.db.commit()
    return {"ok": True, **out}


# ── Who actually decided? ────────────────────────────────────────────────────
# The WhatsApp automation confirms at scale (measured 2026-08-31: 1,174 orders
# in 7 days, 983 of them ALLOCATED to an agent). Crediting an agent for the
# orders merely sitting in their queue therefore inflates every personal
# number. The Version trail records WHO changed the status, so attribution
# comes from there — the automation posts as Administrator and is excluded,
# and its contribution is reported separately instead of being hidden.
_AUTOMATION_USERS = ("Administrator", "Guest")

# Decisions that mean somebody actually tried to reach the customer.
_ATTEMPT_ACTIONS = ("confirm", "cancel", "dna", "followup")

# What counts as HANDLING an order in the section report — deliberately a
# superset of the line above, and deliberately not the same constant.
#
# _ATTEMPT_ACTIONS answers "did somebody try to reach this customer", which is
# what bumps custom_call_attempts. Marking an order Duplicated is not an
# attempt to reach anybody, but it IS a decision the agent took on an order
# they worked — Ahmed settled on 2026-09-16 that a Duplicated order is a
# parked call rather than a closed one, and act() lets an agent decide one on
# the spot. Leaving it out would delete that work from the person who did it.
#
# `onhold` stays out: the status is retired and nothing new can enter it.
# "Not Delivered" is absent on purpose too — it is not in the desk action map
# at all, because nobody SETS it: the carrier does, and the lane then gets the
# order back as a question to re-decide.
_HANDLED_ACTIONS = _ATTEMPT_ACTIONS + ("duplicate",)

# A day nobody worked — they cleaned up. Khadija Koutubi's 28 August is the
# case: 1,659 decisions against a 3-decision median day, an operations
# cleanup on the Desk that made her look like the team's worst performer at
# a 6.3% confirm rate and dragged every team average with it.
#
# The obvious rule — "more than 4x the agent's median day" — was tried first
# and rejected on the data: it flagged two of aithammou's ordinary good days
# (174 and 153) because a quiet July drags his median to 30 while his p90 is
# 130. A person whose workload grew has a meaningless median.
#
# Against the p90 of their own recent days, and with a floor, only the real
# cleanup flags: 1,659 > 3 x 74, while 174 < 3 x 130.
_BATCH_MULT = 3.0
_BATCH_FLOOR = 200
_BATCH_BASELINE_D = 90
_ST_ACTION = {"Confirmed": "confirm", "Cancelled": "cancel",
              "Did not Answer": "dna", "Follow Up": "followup",
              "On Hold": "onhold", "Duplicated": "duplicate"}


def _status_action_map():
    """English statuses → action, PLUS every translation the desk can write.

    Two agents run the desk in French (User.language = fr), and the Version
    log captured their edits as the TRANSLATED label — 'Confirmé', 'Annulé(e)'
    — while the stored field stayed English. Attribution reads that log, so it
    must understand those labels; guessing the strings would rot, so they come
    from Frappe's own translations for the languages the team actually uses.
    Cached: it is a handful of dictionary lookups, but it runs per report."""
    cache = frappe.cache()
    hit = cache.get_value("lp_status_action_map")
    if hit:
        import json as _j
        try:
            return _j.loads(hit)
        except Exception:
            pass
    out = dict(_ST_ACTION)
    langs = [l[0] for l in frappe.db.sql(
        """SELECT DISTINCT language FROM `tabUser`
           WHERE enabled = 1 AND COALESCE(language, '') NOT IN ('', 'en')""")]
    for lang in langs:
        for en, action in _ST_ACTION.items():
            try:
                label = frappe._(en, lang=lang)
            except Exception:
                continue
            if label and label not in out:
                out[label] = action
    import json as _j
    cache.set_value("lp_status_action_map", _j.dumps(out), expires_in_sec=3600)
    return out


def _decisions_by(user, rng, rng_vals, limit=6000):
    """Status decisions this PERSON made in the window, from the Version trail.
    Returns (acts, daily) — the same shape the comment trail produced."""
    import json as _j
    st_map = _status_action_map()
    acts = {"confirm": 0, "cancel": 0, "dna": 0, "followup": 0,
            "onhold": 0, "duplicate": 0}
    daily = {}
    # Company-fenced like every other read in this lane: the site also holds
    # Maslak and China orders in the identical statuses, and a desk agent who
    # touches one must not have it counted as Morocco confirmation work.
    confirmed, touched = set(), {}
    rows = frappe.db.sql(
        f"""SELECT {_clock.sql_local("v.creation")} d, v.creation at, v.docname, v.data
            FROM `tabVersion` v
            JOIN `tabSales Order` so ON so.name = v.docname
            WHERE v.ref_doctype = 'Sales Order' AND v.owner = %(u)s
              AND so.company = %(co)s
              AND v.data LIKE '%%custom_sales_status%%'
              AND {rng.format(col="v.creation")}
            ORDER BY v.creation DESC LIMIT {int(limit)}""",
        {**rng_vals, "u": user, "co": _CO}, as_dict=True)
    for r in rows:
        try:
            changed = _j.loads(r.data or "{}").get("changed") or []
        except Exception:
            continue
        for f in changed:
            if not f or f[0] != "custom_sales_status":
                continue
            action = st_map.get(f[2])
            if not action:
                continue
            acts[action] += 1
            if action == "confirm":
                confirmed.add(r.docname)
            if r.docname not in touched or r.at < touched[r.docname]:
                touched[r.docname] = r.at
            day = daily.setdefault(str(r.d), {"confirm": 0, "cancel": 0, "dna": 0})
            if action in day:
                day[action] += 1
    return acts, daily, confirmed, touched


def _auto_closed_for(user, rng, rng_vals):
    """How many of THIS agent's orders the automation closed in the window —
    context for the agent, never credit."""
    return int(frappe.db.sql(
        f"""SELECT COUNT(DISTINCT v.docname) FROM `tabVersion` v
            JOIN `tabSales Order` so ON so.name = v.docname
            WHERE v.ref_doctype = 'Sales Order'
              AND v.owner IN %(auto)s
              AND v.data LIKE '%%custom_sales_status%%'
              AND so.company = %(co)s
              AND so.custom_allocated_to = %(u)s
              AND {rng.format(col="v.creation")}""",
        {**rng_vals, "u": user, "co": _CO,
         "auto": _AUTOMATION_USERS})[0][0] or 0)


@frappe.whitelist()
def my_report(days=7, frm=None, to=None, as_user=None):
    """The agent's OWN numbers over a window — zero team data, and zero of
    the automation's: decisions from THEIR two trails, money and delivery
    outcome over the orders THEY confirmed. Any CC role."""
    role = _gate()
    me = frappe.session.user
    # "Viewing as <agent>" showed the VIEWER'S numbers, because this endpoint
    # never took the parameter the rest of the lane does — a manager checking
    # on an agent read four zeroes and a flat chart while that agent was
    # having a heavy day. Same gate as board()/next_up: only someone who is
    # not already scoped to themselves can look through another pair of eyes.
    as_user = (as_user or "").strip()
    if as_user and (role == "manager" or _is_cf_admin()):
        me = as_user
    rng, rng_vals = _range(days, frm, to)
    rng_vals = {**rng_vals, "co": _CO, "me": me}
    c_rng = rng.format(col="c.creation")

    # Cached per agent and window. This is a report, not a queue: the screen
    # opens with TWO calls (this period and the one before, for the deltas)
    # and every period chip — Today, Yesterday, 7 days, This month, Last
    # month — fires two more. Without this, clicking along that row pays the
    # full cost five times over for windows that mostly cannot have changed.
    # A window that already ended cannot change at all, so it is held far
    # longer than one still running.
    import json as _cj
    _closed = bool(to) and str(to)[:10] < str(now_datetime())[:10]
    _ck = "lp_myrep_%s_%s_%s_%s" % (me, days, frm or "", to or "")
    _hit = frappe.cache().get_value(_ck)
    if _hit:
        try:
            return _cj.loads(_hit)
        except Exception:
            pass

    acts = {"confirm": 0, "cancel": 0, "dna": 0, "followup": 0,
            "onhold": 0, "duplicate": 0}
    daily = {}
    # Rows, not a GROUP BY, because the money and delivery cards below need to
    # know WHICH orders the agent confirmed — not just how many.
    mine_confirmed, mine_touched = set(), {}
    for r in frappe.db.sql(
            f"""SELECT {_clock.sql_local("c.creation")} d, c.creation at,
                       c.content, c.reference_name so
                FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order' AND c.owner = %(me)s
                  AND c.content LIKE 'Confirmation: %%' AND {c_rng}""",
            rng_vals, as_dict=True):
        if "(bulk)" in (r.content or ""):
            continue
        action = (r.content.split("Confirmation: ", 1)[1] or "").split(" ", 1)[0]
        action = action.strip("()\u2014- ")
        if action not in acts:
            continue
        acts[action] += 1
        if action == "confirm":
            mine_confirmed.add(r.so)
        if r.so and (r.so not in mine_touched or r.at < mine_touched[r.so]):
            mine_touched[r.so] = r.at
        day = daily.setdefault(str(r.d), {"confirm": 0, "cancel": 0, "dna": 0})
        if action in day:
            day[action] += 1

    # The portal writes a comment and no Version row; the desk writes a Version
    # row and no comment. Disjoint trails → SUM them, so an agent who works in
    # both places sees one honest total instead of whichever half was bigger.
    d_acts, d_daily, d_confirmed, d_touched = _decisions_by(me, rng, rng_vals)
    mine_confirmed |= d_confirmed
    for _o, _at in d_touched.items():
        if _o not in mine_touched or _at < mine_touched[_o]:
            mine_touched[_o] = _at
    portal_n = sum(acts.values())
    desk_n = sum(d_acts.values())
    source = ("portal" if not desk_n else "desk" if not portal_n else "both")
    for k, v in d_acts.items():
        acts[k] = acts.get(k, 0) + v
    for d, v in d_daily.items():
        day = daily.setdefault(d, {"confirm": 0, "cancel": 0, "dna": 0})
        for k2 in day:
            day[k2] += v.get(k2, 0)

    sane = 100000
    # Money and delivery used to be measured over everything ALLOCATED to the
    # agent in the window. On prod that is mostly not their work: for one
    # agent over seven days, 1,042 orders were allocated and she had touched
    # 326 of them — the WhatsApp automation had closed 621 by itself. So the
    # card said "your confirmed value" while two thirds of it was the bot's,
    # which is the opposite of a number somebody can be proud of or judged on.
    #
    # Both now run over the orders THIS agent confirmed, from the same two
    # trails the decisions come from. `autoClosed` still reports the bot's
    # share beside them, as context and never as credit.
    if mine_confirmed:
        names = tuple(mine_confirmed)
        money = frappe.db.sql(
            """SELECT COUNT(*) n,
                      SUM(CASE WHEN so.grand_total <= %(sane)s
                          THEN so.grand_total ELSE 0 END) confirmed_value
               FROM `tabSales Order` so
               WHERE so.name IN %(names)s AND so.custom_sales_status = 'Confirmed'""",
            {"sane": sane, "names": names})[0]
        stick = frappe.db.sql(
            """SELECT COUNT(DISTINCT so.name),
                      COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status
                                               = 'Delivered'
                                          THEN so.name END)
               FROM `tabSales Order` so
               JOIN `tabDelivery Note Item` dni
                 ON dni.against_sales_order = so.name AND dni.docstatus = 1
               JOIN `tabDelivery Note` dn
                 ON dn.name = dni.parent AND dn.docstatus = 1
               WHERE so.name IN %(names)s""", {"names": names})[0]
    else:
        money, stick = (0, 0), (0, 0)

    # How long an order waited for this agent's FIRST action on it. Shown,
    # never scored: a metric like this is satisfied by opening the queue and
    # marking everything "no answer" in one sweep, and this team demonstrably
    # sweeps — 416 cancels in a single minute, measured. So it is a number to
    # look at and to argue with, not one that moves money.
    touch = {"median": None, "withinPct": None, "n": 0,
             "slaH": int(_cf_settings().get("slaFirstCallH", 6))}
    if mine_touched:
        born = dict(frappe.db.sql(
            "SELECT name, creation FROM `tabSales Order` WHERE name IN %s",
            (tuple(mine_touched),)))
        gaps = sorted(
            (mine_touched[o] - born[o]).total_seconds() / 3600.0
            for o in mine_touched
            if born.get(o) and mine_touched[o] >= born[o])
        if gaps:
            touch["n"] = len(gaps)
            touch["median"] = round(gaps[len(gaps) // 2], 1)
            touch["withinPct"] = round(
                100.0 * len([g for g in gaps if g <= touch["slaH"]]) / len(gaps))

    out = {
        "acts": acts,
        "touch": touch,
        "daily": [{"date": d, **v} for d, v in sorted(daily.items())],
        "cohort": {"n": int(money[0] or 0),
                   "value": round(float(money[1] or 0))},
        "source": source,
        # The bot's share of this agent's queue — shown, never credited.
        "autoClosed": _auto_closed_for(me, rng, rng_vals),
        "stick": {"shipped": int(stick[0] or 0), "delivered": int(stick[1] or 0)},
        "target": day_target(me),
    }
    frappe.cache().set_value(_ck, _cj.dumps(out, default=str),
                             expires_in_sec=900 if _closed else 60)
    return out


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
    # Every query below is company-fenced; the param has to travel WITH the
    # range or the ones binding %(co)s die — the section report was a 500
    # (KeyError 'co') on every single load until this line existed.
    rng_vals["co"] = _CO
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
    # ONE population, and it is a set of ORDERS.
    #
    # This table used to count key-presses. An order marked Did not Answer
    # twice and then confirmed added three rows to it: one to CONFIRM and two
    # to NO ANSWER, and three to the TOTAL a column header called "orders".
    # Measured on production 2026-09-21 over 30 days, that inflated the
    # section's busiest agent from 1,438 real orders to 2,157.
    #
    # `owned` is the set of orders each person actually decided; `calls` keeps
    # the old action count, which is a real and useful number — it is how many
    # times they had to go back to a customer — so it becomes its own column
    # instead of masquerading as volume.
    per_agent, owned, calls, decided_on = {}, {}, {}, {}
    for r in frappe.db.sql(
            f"""SELECT c.owner, c.reference_name ord, c.content, COUNT(*) n
                       , MIN(c.creation) first_at
                FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order'
                  AND c.content LIKE 'Confirmation: %%' AND {c_rng}
                GROUP BY c.owner, c.reference_name, c.content""",
            rng_vals, as_dict=True):
        r.day = str(_clock.to_floor(r.first_at))[:10] if r.first_at else ""
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
        if action in _HANDLED_ACTIONS:
            owned.setdefault(r.owner, set()).add(r.ord)
            calls[r.owner] = calls.get(r.owner, 0) + int(r.n or 0)
            # When they decided it — for the per-agent trend. Earliest wins,
            # so an order re-touched later is dated to the shift that took it
            # on rather than the one that closed it.
            _k = (r.owner, r.ord)
            if r.day and (_k not in decided_on or r.day < decided_on[_k]):
                decided_on[_k] = r.day

    # ── the SAME people working on the DESK. The portal writes a comment and
    # no Version row (act() goes through db.set_value), the desk writes a
    # Version row and no comment — disjoint trails, so this is a sum, not a
    # merge. Counting only the portal made the section read 6 decisions in a
    # month while the team had taken ~5,900 (measured 2026-08-31), which put
    # the headline confirm rate on a sample of five.
    import json as _j_desk
    _st_map = _status_action_map()
    # The chart and the hour strip below merge these desk tallies in — they
    # were comment-trail-only, so a day worked mostly on the Desk drew as a
    # near-empty column while the leaderboard right above it counted the
    # same day in the hundreds. Same fix, same buckets, same floor clock.
    desk_daily = {}
    desk_hours = {}
    for r in frappe.db.sql(
            f"""SELECT v.owner, v.docname, v.creation, v.data FROM `tabVersion` v
                JOIN `tabSales Order` so ON so.name = v.docname
                WHERE v.ref_doctype = 'Sales Order' AND so.company = %(co)s
                  AND v.owner NOT IN %(auto)s
                  AND v.data LIKE '%%custom_sales_status%%'
                  AND {rng.format(col="v.creation")}
                ORDER BY v.creation DESC LIMIT 40000""",
            {**rng_vals, "auto": _AUTOMATION_USERS}, as_dict=True):
        try:
            changed = _j_desk.loads(r.data or "{}").get("changed") or []
        except Exception:
            continue
        for f in changed:
            if not f or f[0] != "custom_sales_status":
                continue
            action = _st_map.get(f[2])
            if not action:
                continue
            a = per_agent.setdefault(r.owner, {"confirm": 0, "cancel": 0, "dna": 0,
                                               "followup": 0, "onhold": 0,
                                               "duplicate": 0, "reopen": 0,
                                               "bulk": 0})
            if action in a:
                a[action] += 1
            if action in _HANDLED_ACTIONS:
                owned.setdefault(r.owner, set()).add(r.docname)
                calls[r.owner] = calls.get(r.owner, 0) + 1
                _d = str(_clock.to_floor(r.creation))[:10]
                _k = (r.owner, r.docname)
                if _k not in decided_on or _d < decided_on[_k]:
                    decided_on[_k] = _d
            if action in ("confirm", "cancel", "dna"):
                _at = _clock.to_floor(r.creation)
                dd = desk_daily.setdefault(str(_at)[:10], {"confirm": 0,
                                                           "cancel": 0, "dna": 0})
                dd[action] += 1
                _dh = desk_hours.setdefault(_at.hour, [0, 0])
                _dh[0] += 1
                _dh[1] += 1 if action != "dna" else 0

    # ── per-agent outcome + money, on the ORDERS THEY DECIDED ───────────
    #
    # This used to run on a different population than the columns beside it:
    # keyed on custom_allocated_to and windowed on when the order ARRIVED,
    # while the decision columns were keyed on who acted and windowed on when
    # they acted. Two questions, one row. It showed on production as the
    # impossible pair "BOT 2,268 / TOTAL 2,206" — a bot column larger than the
    # total it was supposed to be part of — because the cohort holds every
    # order allocated to the agent, including the ones the automation closed
    # without them. One agent's row read 33 orders on the left and 358 MAD on
    # the right.
    #
    # Both halves now describe the same orders: the ones this person decided.
    #
    # NB `collected` is the money that actually arrived — a confirm whose
    # parcel comes back refused is not revenue. `leak` is deliberately NOT
    # per-agent: an order confirmed and never shipped is the warehouse or the
    # clock, not the agent, and blaming them for it would be a lie with their
    # bonus attached. stickRate is the part they own.
    _all_owned = set()
    for _s in owned.values():
        _all_owned |= _s
    # Absent on a site that never had the desk's Select — every reason then
    # reads as missing, which is true rather than wrong.
    _reason_col = ("so.custom_cancellation_reason"
                   if frappe.get_meta("Sales Order").has_field(
                       "custom_cancellation_reason") else "NULL")
    # Cancels that are not the agent's to answer for. Manager-set — see
    # _CF_DEFAULTS["ownReasons"].
    _own_rz = set(_cf_settings().get("ownReasons") or [])
    # order -> (status, value, attempts); then outcome from the parcels.
    _o_st, _o_del, _o_fail, _o_coll = {}, set(), set(), {}
    _names = list(_all_owned)
    for _i in range(0, len(_names), 900):
        _chunk = tuple(_names[_i:_i + 900])
        for _r in frappe.db.sql(
                f"""SELECT so.name, so.custom_sales_status st, so.grand_total gt,
                           COALESCE(so.custom_call_attempts, 0) att,
                           {_reason_col} rz
                    FROM `tabSales Order` so WHERE so.name IN %s""",
                (_chunk,), as_dict=True):
            _o_st[_r.name] = (_r.st or "", float(_r.gt or 0), int(_r.att or 0),
                              (_r.rz or "").strip())
        # One row per ORDER, never per line: joining Delivery Note Item and
        # summing without collapsing first multiplies every money figure by
        # the basket size. An order that failed once and landed on the
        # redelivery is delivered, not both.
        for _r in frappe.db.sql(
                """SELECT x.name, x.gt,
                          MAX(x.is_del) is_del, MAX(x.is_fail) is_fail
                   FROM (SELECT so.name, so.grand_total gt,
                                dn.custom_track_shipment_status = 'Delivered' is_del,
                                dn.custom_track_shipment_status IN
                                    ('Delivery Exception', 'Failed Attempt') is_fail
                         FROM `tabSales Order` so
                         JOIN `tabDelivery Note Item` dni
                           ON dni.against_sales_order = so.name AND dni.docstatus = 1
                         JOIN `tabDelivery Note` dn
                           ON dn.name = dni.parent AND dn.docstatus = 1
                         WHERE so.name IN %s) x
                   GROUP BY x.name, x.gt""", (_chunk,), as_dict=True):
            if _r.is_del:
                _o_del.add(_r.name)
                if float(_r.gt or 0) <= _SANE_MAX:
                    _o_coll[_r.name] = float(_r.gt or 0)
            elif _r.is_fail:
                _o_fail.add(_r.name)

    # Still genuinely unresolved — which is what the old NO ANSWER column was
    # mistaken for. Of one agent's 1,438 orders, 712 carried a "no answer"
    # and 30 were actually still open: the rest were the same orders, called
    # again and closed.
    # Still open, and the tail belongs here.
    #
    # _TAIL_STS ("Duplicated", "Not Delivered") is work the lane has NOT
    # finished with — Workspace serves both, last, once the live queue is
    # empty. Filing them anywhere else left the row not adding up: `handled`
    # counted them and no visible column did, so the confirm rate quietly
    # dropped for a reason nobody on the screen could see. It is empty on
    # production today (the eight agent rows all balance exactly), which is
    # precisely why it had to be closed now rather than after it filled.
    _OPEN_STS = ("Pending", "Did not Answer", "Follow Up",
                 "On Hold") + _TAIL_STS
    money = {}
    for _u, _set in owned.items():
        d = {"orders": 0, "confirm": 0, "cancel": 0, "open": 0, "other": 0,
             "confirmed_value": 0.0, "collected": 0.0, "delivered": 0,
             "failed": 0, "att_sum": 0,
             # Cancels split by whose problem they were.
             "cx_ours": 0, "cx_ours_value": 0.0, "cx_noreason": 0}
        for _n in _set:
            st, gt, att, rz = _o_st.get(_n, ("", 0.0, 0, ""))
            d["orders"] += 1
            d["att_sum"] += att
            if st == "Confirmed":
                d["confirm"] += 1
                if gt <= _SANE_MAX:
                    d["confirmed_value"] += gt
            elif st == "Cancelled":
                d["cancel"] += 1
                if rz in _own_rz:
                    d["cx_ours"] += 1
                    if gt <= _SANE_MAX:
                        d["cx_ours_value"] += gt
                elif not rz:
                    # A cancel nobody explained. 326 of them in 30 days on
                    # production — every one is a hole in the line above, so
                    # the number is shown per agent rather than totalled into
                    # a footnote nobody acts on.
                    d["cx_noreason"] += 1
            elif st in _OPEN_STS:
                d["open"] += 1
            else:
                d["other"] += 1
            if _n in _o_del:
                d["delivered"] += 1
                d["collected"] += _o_coll.get(_n, 0.0)
            elif _n in _o_fail:
                d["failed"] += 1
        d["attempts"] = round(d["att_sum"] / max(d["orders"], 1), 1)
        money[_u] = d

    # ── is this person getting better? ──────────────────────────────────
    #
    # The day-by-day chart answers that for the TEAM (54.2% to 58.1% over the
    # last five weeks). For a person there was nothing at all, so a manager
    # could not tell somebody who is improving from somebody who was always
    # good — which is the difference between a coaching conversation and a
    # pointless one.
    #
    # Buckets, not raw days: one agent's day is often under twenty orders and
    # a rate on that is noise drawn as a trend. Days while the window is
    # short enough to be read, weeks after that, and a bucket under the floor
    # reports its volume but no rate at all rather than a number that will
    # move ten points tomorrow for no reason.
    _TREND_MIN = 15
    _by_week = days > 21
    trend = {}
    for (_u, _n), _d in decided_on.items():
        if _u not in owned or _n not in owned[_u]:
            continue
        if _by_week:
            try:
                _y, _w, _ = date.fromisoformat(_d).isocalendar()
                _b = "%d-W%02d" % (_y, _w)
            except Exception:
                continue
        else:
            _b = _d
        _st_n = _o_st.get(_n, ("",))[0]
        _t = trend.setdefault(_u, {}).setdefault(_b, [0, 0, 0])
        _t[0] += 1                                   # handled
        _t[1] += 1 if _st_n == "Confirmed" else 0    # confirmed
        # SETTLED — the order reached a verdict. An order touched an hour ago
        # and still ringing is in neither column yet, and dividing by it is
        # how a young bucket is made to look like a collapse.
        _t[2] += 1 if _st_n in ("Confirmed", "Cancelled") else 0

    # ── the AUTOMATION as its own worker ─────────────────────────────────
    # The WhatsApp flow runs as Administrator and it is not a rounding error:
    # measured 2026-08-31, it took 4,686 of the ~10,600 status decisions in
    # August — 44% of everything the section decided. Leaving it out of the
    # headline made the dashboard describe a minority of the work; folding it
    # into the agents made every human average wrong. So it gets its own
    # block, exactly the way the desk's own dashboard treats it (that screen
    # renders `Administrator` as a pinned "Automation" row and excludes it
    # from the team average — same contract, same numbers).
    auto_acts = {"confirm": 0, "cancel": 0, "dna": 0, "followup": 0,
                 "onhold": 0, "duplicate": 0, "reopen": 0, "bulk": 0}
    auto_orders = set()
    for r in frappe.db.sql(
            f"""SELECT v.docname, v.data FROM `tabVersion` v
                JOIN `tabSales Order` so ON so.name = v.docname
                WHERE v.ref_doctype = 'Sales Order' AND so.company = %(co)s
                  AND v.owner IN %(auto)s
                  AND v.data LIKE '%%custom_sales_status%%'
                  AND {rng.format(col="v.creation")}
                ORDER BY v.creation DESC LIMIT 40000""",
            {**rng_vals, "auto": _AUTOMATION_USERS}, as_dict=True):
        try:
            changed = _j_desk.loads(r.data or "{}").get("changed") or []
        except Exception:
            continue
        for f in changed:
            if not f or f[0] != "custom_sales_status":
                continue
            action = _st_map.get(f[2])
            if action in auto_acts:
                auto_acts[action] += 1
                auto_orders.add(r.docname)
    _ad = auto_acts["confirm"] + auto_acts["cancel"]
    auto_value = 0.0
    if auto_orders:
        auto_value = float(frappe.db.sql(
            """SELECT COALESCE(SUM(so.grand_total), 0) FROM `tabSales Order` so
               WHERE so.name IN %(n)s AND so.custom_sales_status = 'Confirmed'
                 AND so.grand_total < %(sane)s""",
            {"n": tuple(auto_orders), "sane": _SANE_MAX})[0][0] or 0)
    automation = {
        **auto_acts,
        "total": sum(auto_acts[k] for k in
                     ("confirm", "cancel", "dna", "followup", "onhold", "duplicate")),
        "confirmRate": round(auto_acts["confirm"] * 100.0 / _ad, 1) if _ad else None,
        "confirmedValue": round(auto_value),
        "orders": len(auto_orders),
    }

    # ── time to first human touch, per agent ────────────────────────────
    # Rows, not aggregates: a median cannot be had from GROUP BY here, and
    # the honest denominator is only the orders somebody actually touched —
    # the ones the bot closed untouched are reported beside it, never folded
    # into it.
    # ── which days were a cleanup, not a shift ──────────────────────────
    # Baselined over a FIXED 90 days, not the report's window: a p90 cannot
    # be had from a seven-day range, and a cleanup inside that range would
    # set the baseline it is supposed to fail.
    batch = {}
    _bd = {}
    for r in frappe.db.sql(
            """SELECT c.owner u, DATE(c.creation) d, COUNT(*) n
               FROM `tabComment` c
               WHERE c.reference_doctype = 'Sales Order'
                 AND c.content LIKE 'Confirmation: %%'
                 AND c.owner NOT IN %(auto)s
                 AND c.creation >= DATE_SUB(NOW(), INTERVAL %(bd)s DAY)
               GROUP BY u, d
               UNION ALL
               SELECT v.owner, DATE(v.creation), COUNT(*)
               FROM `tabVersion` v
               JOIN `tabSales Order` so ON so.name = v.docname
               WHERE v.ref_doctype = 'Sales Order' AND so.company = %(co)s
                 AND v.owner NOT IN %(auto)s
                 AND v.data LIKE '%%custom_sales_status%%'
                 AND v.creation >= DATE_SUB(NOW(), INTERVAL %(bd)s DAY)
               GROUP BY v.owner, DATE(v.creation)""",
            {"auto": _AUTOMATION_USERS, "co": _CO, "bd": _BATCH_BASELINE_D},
            as_dict=True):
        _bd.setdefault(r.u, {})
        _bd[r.u][str(r.d)] = _bd[r.u].get(str(r.d), 0) + int(r.n or 0)
    for u, days in _bd.items():
        v = sorted(days.values())
        p90 = v[min(int(len(v) * 0.9), len(v) - 1)] if v else 0
        hits = [{"d": d, "n": n} for d, n in sorted(days.items())
                if n >= _BATCH_FLOOR and n > _BATCH_MULT * p90]
        if hits:
            batch[u] = {"days": hits, "n": sum(h["n"] for h in hits),
                        "p90": p90}

    # Who is actually ON this team. Khadija Koutubi is the operations
    # manager — she watches the lane, she does not work it — and a manager
    # sitting in the agent table is a manager dragging the team's averages.
    # By ROLE, never by a list of emails in the code: the next manager would
    # be back in the table on their first day.
    _role_cache = {}

    def _rr_safe(u):
        if u not in _role_cache:
            try:
                from logistics_portal.api.auth import resolve_role as _rr
                _role_cache[u] = _rr(u) or ""
            except Exception:
                _role_cache[u] = ""
        return _role_cache[u]

    _role_of = {u: _rr_safe(u) for u in set(list(per_agent) + list(money))}

    sla_min = int(_cf_settings().get("slaFirstCallH", 6)) * 60
    _touch, _team_mins, _team_untouched, _raw = {}, [], 0, {}
    if frappe.get_meta("Sales Order").has_field("custom_first_touch_at"):
        # Same population as every other column on the row: the orders this
        # person decided. Read off the cohort it described a different set.
        _ft = {}
        for _i in range(0, len(_names), 900):
            for r in frappe.db.sql(
                    """SELECT so.name,
                              TIMESTAMPDIFF(MINUTE, so.creation,
                                            so.custom_first_touch_at) mins
                       FROM `tabSales Order` so WHERE so.name IN %s""",
                    (tuple(_names[_i:_i + 900]),), as_dict=True):
                _ft[r.name] = r.mins
        for u, _set in owned.items():
            d = _raw.setdefault(u, {"mins": [], "untouched": 0})
            for _n in _set:
                _m = _ft.get(_n)
                if _m is not None and int(_m) >= 0:
                    d["mins"].append(int(_m))
                else:
                    d["untouched"] += 1
        for u, d in _raw.items():
            ms = sorted(d["mins"])
            if ms:
                _touch[u] = {
                    "median": round(ms[len(ms) // 2] / 60.0, 1),
                    "p90": round(ms[min(int(len(ms) * 0.9), len(ms) - 1)] / 60.0, 1),
                    "slaPct": round(100.0 * sum(1 for m in ms if m <= sla_min) / len(ms), 1),
                    "n": len(ms), "untouched": d["untouched"],
                }
            else:
                _touch[u] = {"median": None, "p90": None, "slaPct": None,
                             "n": 0, "untouched": d["untouched"]}

    # The lane's response time is the lane's people. A manager's cleanup or
    # another team's stray touch does not belong in it.
    for _u, _d in _raw.items():
        _r = _role_of.get(_u) or _rr_safe(_u)
        if not _r or _r == "manager":
            continue
        _team_mins.extend(_d["mins"])
        _team_untouched += _d["untouched"]

    agents = []
    for user in set(list(per_agent) + list(money)):
        a = per_agent.get(user, {"confirm": 0, "cancel": 0, "dna": 0,
                                 "followup": 0, "onhold": 0, "duplicate": 0,
                                 "reopen": 0, "bulk": 0})
        m = money.get(user) or {}
        g = lambda k: m.get(k) or 0          # money rows are plain dicts, and an
                                             # agent may appear in only one of
                                             # the two queries above.
        handled = int(g("orders"))
        settled = int(g("confirm")) + int(g("cancel"))
        shipped = int(g("delivered")) + int(g("failed"))
        agents.append({
            "agent": user.split("@")[0], "user": user,
            # The ACTION tallies stay available under their own name. They
            # are a real number — how many times a verb was pressed — but
            # they are not volume, and leaving them spread across the row
            # under `confirm`/`cancel` is exactly how they got read as one.
            "actions": a,
            "bulk": a["bulk"], "reopen": a["reopen"],
            "calls": calls.get(user, 0),
            # Orders, not key-presses. One row per order this person decided.
            "handled": handled,
            "total": handled,
            # The order's FATE, not the verb that was typed at it. These
            # disagree: one agent pressed Confirm on 17 orders in 30 days and
            # 15 of them are Confirmed today — the rest were reversed after
            # they left. Scoring the keystroke put that person top of the
            # leaderboard at 81% when the orders they handled came out at
            # 51.7%, five places lower.
            "confirmed": int(g("confirm")),
            "cancelled": int(g("cancel")),
            # Still genuinely unresolved. NOT the old NO ANSWER column, which
            # counted re-dials: 712 of them against 30 orders actually open.
            # Includes the tail (Duplicated, Not Delivered) — see _OPEN_STS.
            "open": int(g("open")),
            # A status no bucket above claims. It should always be zero and it
            # is on production today; it is emitted rather than dropped so
            # that a new status can never make a row stop adding up in
            # silence. The screen shows it only when it is not zero, which is
            # the only time anybody needs to see it.
            "other": int(g("other")),
            # Over SETTLED orders, not over everything touched.
            #
            # The trap this closes is the one the funnel taught in the
            # morning and this table walked into by the afternoon: an order
            # decided today and still ringing counts in the denominator and
            # cannot be in the numerator, so the most recent work always
            # reads worst. Read over everything touched, one agent's current
            # week showed 38.0% — 20 of her 50 orders simply had no verdict
            # yet. Over settled orders it is 63.3%, and the "five weeks of
            # decline" I reported from this number was an artefact of it.
            #
            # This is NOT the old confirm/(confirm+cancel), which counted
            # ACTIONS and let re-dials out of the denominator. `open` here is
            # the order's own state, it sits in its own column beside this
            # one, and it is under 3% of a normal agent's window.
            "settled": settled,
            "confirmRate": round(int(g("confirm")) * 100.0 / settled, 1) if settled else None,
            # Cancels that were not this person's to answer for: an item we
            # could not ship, an order placed twice, contact data that was
            # wrong when it arrived. Which reasons those are is a manager
            # setting, never a constant in here.
            "cancelOurs": int(g("cx_ours")),
            "cancelOursValue": round(float(g("cx_ours_value"))),
            # The same rate with those taken out of the denominator. Shown
            # BESIDE the raw one, never instead of it: an agent's real score
            # and the company's real loss are two different questions and the
            # screen should not answer one by hiding the other.
            "adjRate": (round(int(g("confirm")) * 100.0
                              / (settled - int(g("cx_ours"))), 1)
                        if settled - int(g("cx_ours")) > 0 else None),
            # A cancel with no reason recorded. This is the input to the two
            # numbers above — the emptier it is, the less they can say.
            "noReason": int(g("cx_noreason")),
            # Bucketed rate over the window. `rate` is None under the floor —
            # the bucket still reports its volume, so a quiet week reads as
            # quiet rather than as a collapse.
            "trend": [{"b": _b, "n": _v[0], "open": _v[0] - _v[2],
                       "rate": (round(_v[1] * 100.0 / _v[2], 1)
                                if _v[2] >= _TREND_MIN else None)}
                      for _b, _v in sorted((trend.get(user) or {}).items())],
            # How many times they had to go back to a customer per order —
            # the real question the "no answer" column was groping at.
            "callsPerOrder": round(calls.get(user, 0) / float(handled), 2) if handled else None,
            "avgAttempts": round(float(g("attempts")), 1),
            # How fast the first human touch lands after the order arrives.
            #
            # A MEDIAN, over the orders a human actually touched. Both halves
            # of that sentence were wrong before: it averaged, and it read
            # custom_last_call_at — the LAST decision, rewritten by every
            # act() — over the 30.6% of orders that carry the field. It
            # reported 40 to 174 hours per agent. The truth, measured on the
            # same orders with a real first-touch stamp, is a median of 10.4
            # hours with 42.4% inside the six-hour SLA.
            #
            # An average is the wrong summary here whatever it measures: the
            # tail is orders picked up days later, and it drags the number
            # somewhere nobody recognises.
            "role": _role_of.get(user, ""),
            # Everyone who WORKS the lane, which is not the same as everyone
            # whose role string says "confirmation". Checked on production
            # before settling this: basbousalina and cakhadija34 resolve as
            # `cs` and youssrajustyol as `tracking`, and all three are taking
            # confirmation decisions this week — 527 of them in basbousalina's
            # case. Excluding by role name would have deleted real work from
            # the team's numbers to tidy up one manager.
            #
            # So the rule is the narrow one that answers the actual question:
            # a manager watches the lane, everybody else works it.
            "inTeam": bool(_role_of.get(user)) and _role_of.get(user) != "manager",
            # A cleanup day, named. Shown beside the totals rather than
            # quietly subtracted: the work happened, it just was not a shift.
            "batchDays": (batch.get(user) or {}).get("days") or [],
            "batchN": (batch.get(user) or {}).get("n", 0),
            "respH": _touch.get(user, {}).get("median"),
            "slaPct": _touch.get(user, {}).get("slaPct"),
            "touched": _touch.get(user, {}).get("n", 0),
            "neverTouched": _touch.get(user, {}).get("untouched", 0),
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

    # ── the three paths an order can take to Confirmed ───────────────────
    #
    # Without this the agent table is unreadable, and it was being read wrong.
    # Measured on production over 30 days: the company confirms 80.8% of what
    # arrives, but that single number is three populations with nothing in
    # common. 63% of orders are decided before any agent sees them — 15% are
    # born Confirmed at import (a paid order, or a customer who has taken a
    # delivery before) and 48% the WhatsApp automation closes on its own at
    # 96.7%. What reaches a person is the 37% neither path could settle, and
    # it is measurably the harder end of the pile: 33% of it needed a chase
    # reminder against 12% of what the automation closed alone.
    #
    # So the team's confirm rate is 57.1%, and it is not the company's rate,
    # and the two were never comparable. A manager looking at one agent row
    # has no way to know that unless the screen says it.
    #
    # One grouped query rather than loading the window into python: the
    # buckets were verified against a row-by-row JSON parse of the Version
    # trail on production and agree exactly (the only gap was the four orders
    # that arrived between the two runs), and this form has no row cap to
    # silently mis-file an order as "never touched".
    cov = {}
    for _r in frappe.db.sql(
            f"""SELECT CASE
                  WHEN EXISTS (SELECT 1 FROM `tabComment` c
                               WHERE c.reference_doctype = 'Sales Order'
                                 AND c.reference_name = so.name
                                 AND c.content LIKE 'Confirmation: %%')
                    OR EXISTS (SELECT 1 FROM `tabVersion` v
                               WHERE v.ref_doctype = 'Sales Order'
                                 AND v.docname = so.name
                                 AND v.data LIKE '%%custom_sales_status%%'
                                 AND v.owner NOT IN %(auto)s)
                  THEN 'team'
                  WHEN EXISTS (SELECT 1 FROM `tabVersion` v
                               WHERE v.ref_doctype = 'Sales Order'
                                 AND v.docname = so.name
                                 AND v.data LIKE '%%custom_sales_status%%'
                                 AND v.owner IN %(auto)s)
                  THEN 'bot' ELSE 'born' END k,
                COUNT(*) n,
                SUM(so.custom_sales_status = 'Confirmed') c,
                SUM(CASE WHEN so.grand_total <= %(sane)s
                         THEN so.grand_total ELSE 0 END) v,
                SUM(CASE WHEN so.custom_sales_status = 'Confirmed'
                              AND so.grand_total <= %(sane)s
                         THEN so.grand_total ELSE 0 END) cv
                FROM `tabSales Order` so
                WHERE so.company = %(co)s AND {so_rng}
                GROUP BY k""",
            {**rng_vals, "auto": _AUTOMATION_USERS, "sane": _SANE_MAX},
            as_dict=True):
        cov[_r.k] = {"n": int(_r.n or 0), "c": int(_r.c or 0),
                     "v": float(_r.v or 0), "cv": float(_r.cv or 0)}
    _tn = 0
    for _k in ("born", "bot", "team"):
        cov.setdefault(_k, {"n": 0, "c": 0, "v": 0.0, "cv": 0.0})
        _tn += cov[_k]["n"]
    cov["all"] = {"n": _tn,
                  "c": sum(cov[_k]["c"] for _k in ("born", "bot", "team")),
                  "v": sum(cov[_k]["v"] for _k in ("born", "bot", "team")),
                  "cv": sum(cov[_k]["cv"] for _k in ("born", "bot", "team"))}
    for _k, _d in cov.items():
        _d["rate"] = round(_d["c"] * 100.0 / _d["n"], 1) if _d["n"] else None
        _d["share"] = (round(_d["n"] * 100.0 / _tn, 1)
                       if _tn and _k != "all" else None)
        _d["value"] = round(_d["v"])
        _d["confirmedValue"] = round(_d["cv"])
        _d["valueRate"] = round(_d["cv"] * 100.0 / _d["v"], 1) if _d["v"] else None
        _d.pop("v", None)
        _d.pop("cv", None)

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
    funnel_map = {}
    for f in frappe.db.sql(
            f"""SELECT {_clock.sql_local("c.creation")} d,
                   SUM(c.content LIKE 'Confirmation: confirm%%') conf,
                   SUM(c.content LIKE 'Confirmation: cancel%%') canc,
                   SUM(c.content LIKE 'Confirmation: dna%%') dna
            FROM `tabComment` c
            WHERE c.reference_doctype = 'Sales Order'
              AND c.content LIKE 'Confirmation: %%' AND {c_rng}
            GROUP BY d ORDER BY d""", rng_vals, as_dict=True):
        funnel_map[str(f.d)] = {"confirm": int(f.conf or 0),
                                "cancel": int(f.canc or 0),
                                "dna": int(f.dna or 0)}
    # BOTH trails, like the leaderboard: the Desk day joins the chart.
    for dstr, dd in desk_daily.items():
        row = funnel_map.setdefault(dstr, {"confirm": 0, "cancel": 0, "dna": 0})
        for k in ("confirm", "cancel", "dna"):
            row[k] += dd[k]
    funnel = [{"d": k, "conf": v["confirm"], "canc": v["cancel"],
               "dna": v["dna"]} for k, v in sorted(funnel_map.items())]

    # ── the hour of the day the work actually happens ────────────────────
    # Floor-clock hours, both trails: HOUR(creation) was the SITE's clock, so
    # the whole strip sat two hours late — "the team works at 21h" was 19h
    # Morocco — and the Desk's calls were missing from it entirely.
    _hoff = int(round(_clock.offset_hours() * 60))
    _hcol = f"HOUR(DATE_ADD(c.creation, INTERVAL {_hoff} MINUTE))" \
        if _hoff else "HOUR(c.creation)"
    # Volume AND whether the customer picked up.
    #
    # The strip has always answered "when does the team work", which nobody
    # was asking. The question is when a customer ANSWERS, and the two are
    # not the same hour: measured on production over 30 days, 10:00 connects
    # on 46.4% of calls and carries 448 of them, while 16:00 connects on
    # 64.7% and carries 258. The heaviest hour of the day is the worst one.
    #
    # Checked for the obvious confound before building it — that mornings go
    # on the Did-not-Answer backlog, which would make the hour look bad
    # because of the order mix rather than the hour. Restricted to FIRST
    # touches the spread is if anything wider: 45.5% at 10:00 against 69.3%
    # at 16:00. It is the hour.
    hours = {}
    for r in frappe.db.sql(
            f"""SELECT {_hcol} h, COUNT(*) n,
                       SUM(c.content NOT LIKE 'Confirmation: dna%%') ok
                FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order'
                  AND c.content LIKE 'Confirmation: %%' AND {c_rng}
                GROUP BY 1""", rng_vals):
        hours[int(r[0])] = [int(r[1] or 0), int(r[2] or 0)]
    for h, (n, ok) in desk_hours.items():
        d = hours.setdefault(h, [0, 0])
        d[0] += n
        d[1] += ok


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
    # ── delivery outcome of what shipped in the window (parcel grain):
    # confirming a lot that never gets taken is a double loss — this is the
    # honesty check on the confirm rate above it.
    dn_rng = rng.format(col="dn.posting_date")
    stick = frappe.db.sql(
        f"""SELECT dn.posting_date d, COUNT(*) shipped,
                   SUM(dn.custom_track_shipment_status = 'Delivered') delivered
            FROM `tabDelivery Note` dn
            WHERE dn.docstatus = 1 AND dn.company = %(co)s AND {dn_rng}
            GROUP BY dn.posting_date ORDER BY dn.posting_date""",
        rng_vals, as_dict=True)

    # ── where parcels die: top failing cities for the same window ──
    cities = frappe.db.sql(
        f"""SELECT t.city, COUNT(*) parcels, SUM(t.bad) failed FROM (
              SELECT COALESCE(NULLIF(TRIM(so.custom_shipping_city), ''),
                              NULLIF(TRIM(addr.city), ''), '?') city,
                     dn.custom_track_shipment_status IN
                       ('Delivery Exception', 'Failed Attempt') bad
              FROM `tabDelivery Note` dn
              LEFT JOIN `tabSales Order` so
                ON so.name = (SELECT MIN(dni.against_sales_order)
                              FROM `tabDelivery Note Item` dni
                              WHERE dni.parent = dn.name)
              LEFT JOIN `tabAddress` addr ON addr.name = so.shipping_address_name
              WHERE dn.docstatus = 1 AND dn.company = %(co)s AND {dn_rng}
            ) t GROUP BY t.city HAVING failed > 0
            ORDER BY failed DESC LIMIT 8""",
        rng_vals, as_dict=True)

    # Headline intake for the window — every order that arrived, allocated
    # or not (the per-agent cohort above only sees allocated ones).
    _oi = frappe.db.sql(
        f"""SELECT COUNT(*), COALESCE(SUM(so.grand_total), 0)
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s AND {so_rng}""",
        rng_vals)[0]

    _out = {
        "days": days, "frm": frm or "", "to": to or "",
        "ordersIn": {"n": int(_oi[0] or 0), "value": round(float(_oi[1] or 0))},
        "stick": [{"d": str(r_.d), "shipped": int(r_.shipped or 0),
                   "delivered": int(r_.delivered or 0)} for r_ in stick],
        "cities": [{"city": (r_.city or "?").title(), "parcels": int(r_.parcels or 0),
                    "failed": int(r_.failed or 0)} for r_ in cities],
        # The lane's own answer to "how fast do we reach a customer", which
        # is the number this report existed to give and never did. Median,
        # p90 and the share inside the SLA — and, separately, how many the
        # bot closed with nobody ever touching them, because folding those
        # into a response time would flatter it beyond recognition.
        "firstTouch": _first_touch_summary(_team_mins, _team_untouched, sla_min),
        "agents": agents,
        # What the agent table is a slice OF.
        "coverage": cov,
        # Kept OUT of `agents` on purpose: everything that iterates that list
        # (leaderboard, bonus, team averages) must stay human-only.
        "automation": automation,
        "reasons": reason_rows,
        "funnel": [{"date": f["d"], "confirm": f["conf"],
                    "cancel": f["canc"], "dna": f["dna"]} for f in funnel],
        # `reached` is None below 25 calls: a 100% built on three dials is a
        # worse answer than no answer, and this strip is meant to move a
        # shift pattern.
        "hours": [{"h": h, "n": hours.get(h, [0, 0])[0],
                   "reached": (round(hours[h][1] * 100.0 / hours[h][0], 1)
                               if h in hours and hours[h][0] >= 25 else None)}
                  for h in range(min(hours) if hours else 8,
                                 (max(hours) if hours else 20) + 1)],
        "ladder": ladder,
        "target": day_target(),
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
                   SUM(TIMESTAMPDIFF(HOUR, so.creation, %(now)s) > %(sla)s
                       AND COALESCE(so.custom_call_attempts, 0) = 0) late
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s {active}{me_cond}
            GROUP BY st""",
        {"live": live, "sla": sla_h, "sane": _SANE_MAX,
         "now": str(now_datetime())[:19], **rng_vals}, as_dict=True)
    queue = {r.st: {"n": int(r.n or 0), "value": round(float(r.value or 0)),
                    "late": int(r.late or 0)} for r in q}
    absurd = sum(int(r.absurd or 0) for r in q)

    # ── how old is the pile ──────────────────────────────────────────────
    aging = frappe.db.sql(
        f"""SELECT CASE
                     WHEN TIMESTAMPDIFF(HOUR, so.creation, %(now)s) <= 6 THEN '0-6h'
                     WHEN TIMESTAMPDIFF(HOUR, so.creation, %(now)s) <= 24 THEN '6-24h'
                     WHEN TIMESTAMPDIFF(HOUR, so.creation, %(now)s) <= 72 THEN '1-3d'
                     WHEN TIMESTAMPDIFF(HOUR, so.creation, %(now)s) <= 168 THEN '3-7d'
                     ELSE '7d+' END bucket,
                   COUNT(*) n,
                   COALESCE(SUM(CASE WHEN so.grand_total <= %(sane)s
                                     THEN so.grand_total ELSE 0 END), 0) value
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s {active}{me_cond}
            GROUP BY bucket""",
        {"live": live, "sane": _SANE_MAX,
         "now": str(now_datetime())[:19], **rng_vals}, as_dict=True)
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
                   GREATEST(0, TIMESTAMPDIFF(HOUR, so.creation, %(now)s)) age_h,
                   COALESCE(so.custom_call_attempts, 0) attempts
            FROM `tabSales Order` so {_CITY_JOIN}
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s {active}{me_cond}
            ORDER BY so.creation LIMIT 20""",
        {"live": live, "now": str(now_datetime())[:19], **rng_vals}, as_dict=True)

    # ── where the queue is, geographically ───────────────────────────────
    cities = frappe.db.sql(
        f"""SELECT COALESCE({_CITY}, '(none)') city, COUNT(*) n
            FROM `tabSales Order` so {_CITY_JOIN}
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(live)s {active}{me_cond}
            GROUP BY city ORDER BY n DESC LIMIT 8""",
        {"live": live, "now": str(now_datetime())[:19], **rng_vals}, as_dict=True)

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
                     AND so.amended_from IS NULL
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

    # Re-read immediately before the write phase. The carrier sweep writes
    # ~60 Sales Orders every ten minutes (measured 2026-09-21: 59 rows in 32s
    # under one agent's click), and any of them landing on this row between
    # the guards above and the cancel below would throw a timestamp mismatch
    # at the agent. Reloading narrows that window from seconds to microseconds.
    so.reload()

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
        # BY ROW, not by code. ERPNext allows the same item_code on several
        # lines (routine after a consolidation merge), and a code-keyed map
        # applied one edit to EVERY matching row — zeroing one short line
        # silently removed the others too.
        wanted_idx = {int(i["idx"]): flt(i.get("qty")) for i in items
                      if str(i.get("idx") or "").strip().isdigit()}
        wanted = {str(i.get("item_code")): flt(i.get("qty")) for i in items
                  if i.get("item_code") and not str(i.get("idx") or "").strip().isdigit()}
        rows = []
        for r in new.items:
            q = wanted_idx.get(int(r.idx), None)
            if q is None:
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
    # THE reason this feature never once worked on production; the full
    # story lives in utils.submit_new_sales_order, which reship and the
    # consolidation merge turned out to need too — all three were dead for
    # the same missing line.
    from logistics_portal.api.utils import submit_new_sales_order
    submit_new_sales_order(new)
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


# ── Pinned work: "I want this one next" ─────────────────────────────────────
#
# next_order deliberately does not let an agent cherry-pick — that is what moved
# the first-touch time, and it stays. But it only ever serves two things: a
# call-back that is due, and the oldest untouched Pending. Six of the ten tabs
# an agent can browse — monitor, not-delivered, city-check, cancelled,
# duplicated, confirmed — have no route into the workspace at all. An agent who
# spots an order that needs a call in one of those has nowhere to put it except
# their memory.
#
# So pinning is the one deliberate exception: the agent says "this one next",
# and it is served BEFORE the automatic order. It is not cherry-picking the
# queue — the queue still decides everything the agent did not explicitly ask
# for — and it is per agent, capped, and dropped the moment the order stops
# being workable.
_PIN_KEY = "lp_ws_pins"
_PIN_CAP = 20


def _pins_all():
    raw = frappe.db.get_default(_PIN_KEY)
    if not raw:
        return {}
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def unpin_after_decision(order, user=None):
    """A decided order leaves the workspace queue on its own.

    Nothing ever removed a pin: _pins_write had exactly one caller —
    pin_order itself — so a pinned order was served again after every
    decision, forever, until the agent noticed and unpinned it by hand.
    Called from confirmation.act and rescue.act; safe on a name that was
    never pinned, and rescue may hand it a Delivery Note name (its DN
    queues), which simply matches nothing.
    """
    user = user or frappe.session.user
    mine = _pins_all().get(user) or []
    if order in mine:
        _pins_write(user, [x for x in mine if x != order])


def _pins_for(user):
    """This agent's pins, newest first, with anything no longer workable
    dropped — an order someone else already decided must not sit at the front
    of the queue forever."""
    mine = [x for x in (_pins_all().get(user) or []) if x]
    if not mine:
        return []
    rows = frappe.db.sql(
        f"""SELECT so.name FROM `tabSales Order` so
            WHERE so.name IN %s AND so.docstatus = 1 AND so.company = %s
              AND {_IN_HAND}""", (tuple(mine), _CO))
    alive = {r[0] for r in rows}
    return [x for x in mine if x in alive]


def _pins_write(user, names):
    data = _pins_all()
    if names:
        data[user] = names[:_PIN_CAP]
    else:
        data.pop(user, None)
    frappe.db.set_default(_PIN_KEY, json.dumps(data))


@frappe.whitelist(methods=["POST"])
def pin_order(order, on=1):
    """Put an order at the front of MY workspace, or take it back off."""
    _gate()
    order = (order or "").strip()
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    co = frappe.db.get_value("Sales Order", order, "company")
    if co != _CO:
        frappe.throw("That order is not on this market.")
    me = frappe.session.user
    mine = [x for x in (_pins_all().get(me) or []) if x != order]
    if int(on or 0):
        mine.insert(0, order)
        if len(mine) > _PIN_CAP:
            frappe.throw(
                f"You already have {_PIN_CAP} orders waiting in your workspace. "
                "Work some of them before adding more.")
    _pins_write(me, mine)
    frappe.db.commit()
    return {"ok": True, "order": order, "pinned": bool(int(on or 0)),
            "count": len(mine)}


@frappe.whitelist()
def my_pins():
    """What this agent has queued up, for the workspace pane and the tab chips."""
    _gate()
    return {"orders": _pins_for(frappe.session.user)}


# ── Serve-next: the workspace engine (Phase B) ──────────────────────────────


# ── the shared pool ───────────────────────────────────────────────────────

def _last_touch_sql():
    """When a human last worked this order through the portal. NULL means
    nobody ever has — the oldest kind of waiting there is."""
    return ("(SELECT MAX(c.creation) FROM `tabComment` c "
            "WHERE c.reference_doctype = 'Sales Order' AND c.reference_name = so.name "
            "AND (c.content LIKE 'Confirmation:%%' OR c.content LIKE 'CC:%%' "
            "     OR c.content LIKE 'Note —%%'))")


def _pool_cond():
    """Work that is waiting for anybody.

    Two ways in. An order belonging to NOBODY is available at once — with the
    Desk assignment rule off this is how every new order arrives, and making
    it wait would just be the old first-touch delay wearing a new name. An
    order that does belong to someone joins only after it has been quiet
    longer than poolAfterH, which is the evidence that they are not on it.

    `_DUE` guards both: it excludes a future next_call_at, the promise made
    to a customer, so a scheduled call-back is never taken from the agent who
    made the promise."""
    # A parcel somebody took minutes ago is not waiting for anybody.
    #
    # This is the bug that put two agents on one customer. Taking from the
    # pool moved the assignment but left no TOUCH, so the order still read as
    # "quiet since 1900" and stayed on offer: Khadija took SAL-ORD-2026-03458
    # at 19:44, Salma was handed the same order at 19:46, Salma's take
    # stripped Khadija's assignment, and Khadija's Confirm came back "you can
    # only act on orders assigned to you". Forty-seven live orders were in
    # that state at once. The five-minute serve lock was the only thing
    # standing in the way, and it lives in the cache: it dies on a restart
    # and is deleted outright when an agent skips.
    #
    # The durable signal is the assignment's own ToDo — written by
    # assign_to.add, removed when the assignment is, and already timestamped.
    # No new field, and it cannot drift from _assign because Frappe writes
    # them together.
    held = ("NOT EXISTS (SELECT 1 FROM `tabToDo` t WHERE t.reference_type = 'Sales Order' "
            "AND t.reference_name = so.name AND t.status = 'Open' "
            "AND t.creation > %(quiet)s)")
    return (f"{_DUE} AND {held} AND {_open_free_cond()} AND ("
            f"COALESCE(so._assign, '', '[]') IN ('', '[]') "
            f"OR COALESCE({_last_touch_sql()}, '1900-01-01') <= %(quiet)s)")


def _on_shift(user):
    """Is this person at work right now, by the clock they punch themselves?

    Fails OPEN. No employee record and no punch means we do not know, and an
    absence of evidence must not lock someone out of work — only a punch that
    actually says OUT does. Attendance is HRMS's to write; the portal only
    ever reads it (see the attendance note in the project memory)."""
    try:
        emp = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
        if not emp:
            return True
        row = frappe.db.sql(
            """SELECT log_type FROM `tabEmployee Checkin`
               WHERE employee = %(e)s AND time >= DATE_SUB(%(s)s, INTERVAL 18 HOUR)
               ORDER BY time DESC LIMIT 1""",
            {"e": emp, "s": str(now_datetime())[:19]}, as_dict=True)
        if not row:
            return True
        return (row[0].log_type or "IN") != "OUT"
    except Exception:
        return True


def _holding(user):
    """How many live orders this person already has in hand.

    The tail counts: it is work someone is holding, and leaving it out would
    make it a way around the pool ceiling rather than the bottom of it."""
    held_sts = tuple(v for k, v in QUEUES.items() if k != "pending") + _TAIL_STS
    return int(frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s AND {_IN_HAND}
              AND (so.custom_sales_status IN %(sts)s OR so.custom_sales_status = 'Pending')
              AND so._assign LIKE %(me)s""",
        {"co": _CO, "sts": held_sts, "me": f'%"{user}"%'})[0][0] or 0)


def _pool_block(user):
    """Why this person may not draw from the pool right now — "" if they may.
    Their OWN queue is never affected by any of this."""
    cfg = _cf_settings()
    if not cfg.get("poolEnabled"):
        return "off"
    roster = cfg.get("poolRoster") or []
    if roster and user not in roster:
        return "notroster"
    if cfg.get("poolPresence") and not _on_shift(user):
        return "offshift"
    cap = int(cfg.get("poolMax") or 20)
    if _holding(user) >= cap:
        return "full"
    return ""


def _serve_order():
    """One ordering for every queue this lane serves from, so an agent's own
    list and the shared pool cannot disagree about what matters."""
    if _cf_settings().get("poolNewFirst"):
        return f"(so.custom_sales_status = 'Pending') DESC, {_DUE_AT}"
    return _DUE_AT


def _pool_vals(vals):
    _open_vals(vals)
    cfg = _cf_settings()
    h = min(max(int(cfg.get("poolAfterH") or 2), 1), 168)
    vals["quiet"] = str(add_to_date(now_datetime(), hours=-h))[:19]
    return vals


def _take_from_pool(order):
    """Move the ERPNext assignment to the person who just picked this up.

    _assign is what the board filters by and what _own_guard reads, so
    without this the agent would be handed an order they are not allowed to
    act on. The handover is written on the order as well: taking a colleague's
    work silently is the one thing that would make the team distrust this."""
    try:
        from frappe.desk.form import assign_to
        was = frappe.db.get_value("Sales Order", order, "_assign") or ""
        me = frappe.session.user
        if f'"{me}"' in was:
            return ""
        prev = ""
        try:
            import json as _json
            holders = [u for u in (_json.loads(was) or []) if u]
            prev = holders[0] if holders else ""
            for u in holders:
                assign_to.remove("Sales Order", order, u)
        except Exception:
            pass
        assign_to.add({"doctype": "Sales Order", "name": order,
                       "assign_to": [me], "description": "Confirmation pool"})
        # Always, not only when it came off somebody: the take IS the touch,
        # and an unassigned order taken silently left no evidence at all that
        # anyone had picked it up.
        frappe.get_doc("Sales Order", order).add_comment(
            "Comment", f"Pool: taken{f' from {prev}' if prev and prev != me else ''} · by {me}")
        _first_touch(order, me)
        return prev
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "confirmation._take_from_pool")
        return ""


@frappe.whitelist()
def pool_depth():
    """How much work is waiting for anybody, and whether I may take it.

    The reason travels with the number: an agent who sees 40 waiting and a
    dead button will decide the portal is broken, and be right to."""
    _gate()
    me = frappe.session.user
    if not _cf_settings().get("poolEnabled"):
        return {"n": 0, "enabled": False, "block": "off"}
    vals = _pool_vals({"co": _CO, "now": str(now_datetime())[:19]})
    # The tail counts too. A depth of zero while 42 orders sit unreachable is
    # exactly how this looked to the team: the screen said there was nothing
    # and the work was simply invisible.
    vals["sts"] = (tuple(v for k, v in QUEUES.items() if k != "pending")
                   + _TAIL_STS)
    n = frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s AND {_IN_HAND}
              AND (so.custom_sales_status IN %(sts)s OR so.custom_sales_status = 'Pending')
              AND {_not_cold()}
              AND {_pool_cond()}""", vals)[0][0]
    return {"n": int(n or 0), "enabled": True, "block": _pool_block(me),
            "holding": _holding(me), "max": int(_cf_settings().get("poolMax") or 20)}


@frappe.whitelist()
def fresh_waiting():
    """How many customers have ordered and nobody has spoken to them yet.

    Ordering new work to the front only helps an agent who presses Next. The
    one sitting between calls with an empty queue never learns that a fresh
    order landed — so this is the number the screen shouts. One indexed
    count, cheap enough to ask every half minute."""
    _gate()
    if not _cf_settings().get("poolEnabled"):
        return {"n": 0, "oldestMin": 0}
    vals = _pool_vals({"co": _CO, "now": str(now_datetime())[:19]})
    r = frappe.db.sql(
        f"""SELECT COUNT(*) n, MIN(so.creation) oldest FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s AND {_IN_HAND}
              AND so.custom_sales_status = 'Pending'
              AND {_not_cold()}
              AND {_pool_cond()}""", vals, as_dict=True)[0]
    mins = 0
    if r.oldest:
        mins = max(0, int((now_datetime() - r.oldest).total_seconds() // 60))
    return {"n": int(r.n or 0), "oldestMin": mins,
            "canTake": not _pool_block(frappe.session.user)}


@frappe.whitelist()
def pool_team():
    """Who is at their desk, what they are holding, what they have decided
    today. The question the old assignment rule could not answer: a fixed
    list of three names kept feeding work to whoever was on it, present or
    not, while somebody clocked in sat with nothing."""
    role = _gate()
    if role != "manager" and not _is_cf_admin():
        frappe.throw("lp:leadsOnly", frappe.PermissionError)
    d0, d1 = _clock.day_bounds(_clock.floor_today())
    # Who is IN this lane. Not "anyone resolve_role calls a manager" — that is
    # every System Manager in the building, and the first run of this listed
    # 27 people including HR and the chat bot, at 680 ms. The lane is whoever
    # carries the explicit role, plus whoever has actually decided something
    # here lately: the busiest agent on production has no role field set and
    # would otherwise be missing from her own team's list.
    from logistics_portal.api.auth import resolve_role as _rr
    lane = {u.name for u in frappe.get_all(
        "User", filters={"enabled": 1}, fields=["name"], limit=500)
        if _rr(u.name) == "confirmation"}
    lane |= {r[0] for r in frappe.db.sql(
        """SELECT DISTINCT owner FROM `tabComment`
           WHERE reference_doctype = 'Sales Order'
             AND creation >= DATE_SUB(%(s)s, INTERVAL 14 DAY)
             AND (content LIKE 'Confirmation:%%' OR content LIKE 'CC:%%')""",
        {"s": str(now_datetime())[:19]})}
    names = sorted(lane)
    if not names:
        return {"team": [], "pool": pool_depth()}

    # Three set-based reads, not four per person. The per-person version was
    # 842 ms for eight people — thirty-two round trips for a popover.
    users = {u.name: (u.full_name or u.name.split("@")[0]) for u in frappe.get_all(
        "User", filters={"enabled": 1, "name": ("in", names)},
        fields=["name", "full_name"], limit=200)}
    if not users:
        return {"team": [], "pool": pool_depth()}
    keys = list(users)

    done = {r[0]: int(r[1]) for r in frappe.db.sql(
        """SELECT owner, COUNT(*) FROM `tabComment`
           WHERE owner IN %(u)s AND reference_doctype = 'Sales Order'
             AND creation BETWEEN %(a)s AND %(b)s
             AND (content LIKE 'Confirmation:%%' OR content LIKE 'CC:%%')
           GROUP BY owner""", {"u": tuple(keys), "a": d0, "b": d1})}

    # _assign is a JSON array, so it cannot be grouped in SQL. There are a
    # couple of hundred open orders — read the column once and count here.
    retry_sts = tuple(v for k, v in QUEUES.items() if k != "pending")
    holding = {k: 0 for k in keys}
    for (assigned,) in frappe.db.sql(
            f"""SELECT so._assign FROM `tabSales Order` so
                WHERE so.docstatus = 1 AND so.company = %(co)s AND {_IN_HAND}
                  AND (so.custom_sales_status IN %(sts)s
                       OR so.custom_sales_status = 'Pending')
                  AND COALESCE(so._assign, '') <> ''""",
            {"co": _CO, "sts": retry_sts}):
        for k in keys:
            if f'"{k}"' in (assigned or ""):
                holding[k] += 1

    # Presence: one pass over the punches, newest first, first hit per person
    # wins. Same fail-open rule as _on_shift — silence is not an OUT.
    shift = {}
    for r in frappe.db.sql(
            """SELECT e.user_id, ci.log_type FROM `tabEmployee Checkin` ci
               JOIN `tabEmployee` e ON e.name = ci.employee AND e.status = 'Active'
               WHERE e.user_id IN %(u)s AND ci.time >= DATE_SUB(%(s)s, INTERVAL 18 HOUR)
               ORDER BY ci.time DESC""",
            {"u": tuple(keys), "s": str(now_datetime())[:19]}, as_dict=True):
        shift.setdefault(r.user_id, (r.log_type or "IN") != "OUT")

    # `punched` separates "clocked in" from "we have no punch and assumed so".
    # Three of the eight on production have no check-in record at all; showing
    # them with the same green dot as someone who really punched IN would be
    # the screen asserting something it does not know.
    roster = _cf_settings().get("poolRoster") or []
    out = [{"user": k, "name": users[k], "onShift": bool(shift.get(k, True)),
            "punched": k in shift,
            # No roster set = everyone is on duty, which is what the gate does.
            "onDuty": (not roster) or k in roster,
            "holding": holding.get(k, 0), "doneToday": done.get(k, 0)}
           for k in keys]
    out.sort(key=lambda r: (not r["onShift"], -r["holding"]))
    return {"team": out, "pool": pool_depth()}


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
    # The DB server's NOW() runs on a different clock than the site (fresh
    # orders read negative ages; due call-backs fired an hour late) — every
    # time comparison here uses the SITE clock.
    vals = {"co": _CO, "now": str(now_datetime())[:19]}
    if mine:
        vals["me_like"] = f'%"{scope_user}"%'
        me_q = " AND so._assign LIKE %(me_like)s"

    # What the agent explicitly asked for comes first — that is the whole point
    # of pinning. Everything they did NOT ask for is still decided by the queue
    # below, so the ordering discipline survives.
    for name in _pins_for(scope_user):
        if cache.get_value(f"lp_skip_{me}_{name}"):
            continue
        lock = f"lp_serve_{name}"
        if cache.get_value(lock) and cache.get_value(lock) != me:
            continue
        if not view_as:
            cache.set_value(lock, me, expires_in_sec=300)
        return {"order": name, "pinned": True}

    retry_sts = tuple(v for k, v in QUEUES.items() if k != "pending")
    # Priority is WHAT the work is, not WHOSE it is.
    #
    # The passes used to run "everything of mine, then the pool", so an agent
    # holding retries never reached the pool's new orders. Measured on
    # production: the red button told Salma 22 customers were waiting and
    # then handed her a Follow Up, with 21 more retries to clear before the
    # pool came into view. The button was honest about the pool and the
    # server was answering from somewhere else.
    #
    # A customer who ordered minutes ago outranks a call-back from yesterday
    # whoever is holding it, so Pending sweeps own-then-pool before retries
    # do. Mine still comes before the pool INSIDE each kind: covering for a
    # colleague should not jump my own queue of the same thing.
    _own = me_q + " AND " + _open_free_cond()
    _open_vals(vals)
    _retry_own = (f"""SELECT so.name FROM `tabSales Order` so
                      WHERE so.docstatus = 1 AND so.company = %(co)s
                        AND so.custom_sales_status IN %(sts)s AND {_IN_HAND}
                        AND {_DUE}{_own}
                      ORDER BY {_DUE_AT} LIMIT 25""", {"sts": retry_sts})
    _fresh_own = (f"""SELECT so.name FROM `tabSales Order` so
                      WHERE so.docstatus = 1 AND so.company = %(co)s
                        AND so.custom_sales_status = 'Pending' AND {_IN_HAND}
                        AND {_not_cold()}
                        AND so.creation >= DATE_SUB(NOW(), INTERVAL 30 DAY){_own}
                      ORDER BY so.creation LIMIT 25""", {})

    can_pool = mine and not view_as and not _pool_block(me)
    if can_pool:
        _pool_vals(vals)
    _fresh_pool = (f"""SELECT so.name FROM `tabSales Order` so
                       WHERE so.docstatus = 1 AND so.company = %(co)s AND {_IN_HAND}
                         AND so.custom_sales_status = 'Pending'
                         AND {_not_cold()}
                         AND {_pool_cond()}
                       ORDER BY so.creation LIMIT 25""", {})
    _retry_pool = (f"""SELECT so.name FROM `tabSales Order` so
                       WHERE so.docstatus = 1 AND so.company = %(co)s AND {_IN_HAND}
                         AND so.custom_sales_status IN %(sts)s
                         AND {_pool_cond()}
                       ORDER BY {_DUE_AT} LIMIT 25""", {"sts": retry_sts})

    # The tail. Same shape as the retries, its own status list, and it runs
    # after everything else whichever way the new-first setting is set — a
    # customer waiting on a live order always outranks a parked one.
    _tail_own = (f"""SELECT so.name FROM `tabSales Order` so
                     WHERE so.docstatus = 1 AND so.company = %(co)s
                       AND so.custom_sales_status IN %(tail)s AND {_IN_HAND}
                       AND {_DUE}{_own}
                     ORDER BY {_DUE_AT} LIMIT 25""", {"tail": _TAIL_STS})
    _tail_pool = (f"""SELECT so.name FROM `tabSales Order` so
                      WHERE so.docstatus = 1 AND so.company = %(co)s AND {_IN_HAND}
                        AND so.custom_sales_status IN %(tail)s
                        AND {_pool_cond()}
                      ORDER BY {_DUE_AT} LIMIT 25""", {"tail": _TAIL_STS})

    if _cf_settings().get("poolNewFirst"):
        passes = [(_fresh_own, 0), (_fresh_pool, 1), (_retry_own, 0), (_retry_pool, 1)]
    else:
        passes = [(_retry_own, 0), (_fresh_own, 0), (_retry_pool, 1), (_fresh_pool, 1)]
    passes += [(_tail_own, 0), (_tail_pool, 1)]

    for (sql, extra), from_pool in passes:
        if from_pool and not can_pool:
            continue
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
            if not from_pool:
                return {"order": name}
            prev = _take_from_pool(name)
            return {"order": name, "fromPool": True, "tookFrom": prev}
    return {"order": None}


# ── who has the card open ─────────────────────────────────────────────────
#
# A cache lock used to be the only answer to "is somebody on this customer",
# and on 2026-09-18 it failed in the way that matters: two agents were handed
# the same order ninety seconds apart and both called. In twenty-four hours
# 22 orders reached two people and 2 customers were actually decided twice,
# one of them by two agents in the SAME minute.
#
# Three things were wrong and all three are fixed here. The lock was in the
# cache, so a restart or a skip erased it — it is a field now. It expired on
# a flat five minutes whether or not the call was still going — the open card
# refreshes it, so a long call holds and a closed laptop lets go. And it was
# invisible: the other agent saw the order, opened it, phoned the customer,
# and only met the refusal when they pressed a button. The block is at OPEN
# now, which is the only place it protects anybody.

_OPEN_TTL_MIN = 3


def _open_cut():
    return str(add_to_date(now_datetime(), minutes=-_OPEN_TTL_MIN))[:19]


def _has_open_fields():
    try:
        return frappe.get_meta("Sales Order").has_field("custom_cc_open_by")
    except Exception:
        return False


def _open_holder(order):
    """(who, since) for a LIVE hold — "" when free or gone stale."""
    if not _has_open_fields():
        return ("", "")
    r = frappe.db.get_value("Sales Order", order,
                            ["custom_cc_open_by", "custom_cc_open_at"], as_dict=True)
    if not r or not r.custom_cc_open_by:
        return ("", "")
    if str(r.custom_cc_open_at or "")[:19] < _open_cut():
        return ("", "")
    return (r.custom_cc_open_by, str(r.custom_cc_open_at or "")[:16])


def _open_free_cond(alias="so"):
    """Rows nobody else has open. Used by every list the order can be
    reached from — the pool was filtered and the queue list was not, which
    is exactly how an agent found a colleague's customer to click on."""
    if not _has_open_fields():
        return "1 = 1"
    return (f"(COALESCE({alias}.custom_cc_open_by,'') = '' "
            f" OR {alias}.custom_cc_open_by = %(me)s "
            f" OR COALESCE({alias}.custom_cc_open_at,'1900-01-01') < %(opencut)s)")


def _open_vals(vals):
    vals["me"] = frappe.session.user
    vals["opencut"] = _open_cut()
    return vals


@frappe.whitelist(methods=["POST"])
def open_order(order):
    """Take the card. Serialized, and committed inside the lock: the named
    lock spans workers, but an uncommitted write is invisible to the next
    transaction and both agents would be told yes."""
    role = _gate()
    order = (order or "").strip()
    if frappe.db.get_value("Sales Order", order, "company") != _CO:
        frappe.throw("Unknown order.")
    if not _has_open_fields():
        return {"ok": True, "fields": False}
    me = frappe.session.user
    # A lead looking is not a lead working: the manager sees who holds it and
    # reads the card, and never takes it away by opening it.
    if role == "manager" or _is_cf_admin():
        who, since = _open_holder(order)
        return {"ok": True, "readOnly": bool(who and who != me),
                "by": who, "since": since}
    from logistics_portal.api.locks import named_lock
    with named_lock(f"cc_open_{order}"):
        who, since = _open_holder(order)
        if who and who != me:
            return {"ok": False, "by": who, "since": since}
        frappe.db.set_value("Sales Order", order, {
            "custom_cc_open_by": me, "custom_cc_open_at": now_datetime(),
        }, update_modified=False)
        # Ownership is TAKEN by doing the work, not granted in advance.
        #
        # Every tab, the search and _own_guard all key on _assign, and the
        # auto-assignment was the only thing writing it at scale. When it was
        # switched off on 18 September the share of orders carrying one fell
        # from 100% to 18% in three days, and three whole tabs emptied:
        # measured 2026-09-21, 16 of 16 Not Delivered, 26 of 27 Duplicated
        # and 34 of 54 Follow Up had no assignment, so nobody could see them.
        #
        # The fix is not to loosen the guard — showing an agent an order that
        # would then refuse them is worse than hiding it. It is to let them
        # acquire the order by opening it. Only when it belongs to NOBODY:
        # a colleague's order is still theirs, and _own_guard still says so.
        if not (frappe.db.get_value("Sales Order", order, "_assign") or "").strip(" []"):
            _take_from_pool(order)
        # Opening the card IS the first touch — the agent is looking at this
        # customer. Every other stamp below is a fallback for a decision that
        # reached the order some other way.
        _first_touch(order)
        frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def hold_open(order):
    """The open card says it is still here. Called on a timer, so the hold
    lasts exactly as long as the call does."""
    _gate()
    order = (order or "").strip()
    if not _has_open_fields():
        return {"ok": True}
    who, _since = _open_holder(order)
    me = frappe.session.user
    if who and who != me:
        return {"ok": False, "by": who}
    frappe.db.set_value("Sales Order", order,
                        {"custom_cc_open_by": me, "custom_cc_open_at": now_datetime()},
                        update_modified=False)
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def release_order(order):
    """The agent skipped / navigated away — free the serve lock and the card."""
    _gate()
    order = (order or "").strip()
    lock = f"lp_serve_{order}"
    if frappe.cache().get_value(lock) == frappe.session.user:
        frappe.cache().delete_value(lock)
    if _has_open_fields():
        who, _s = _open_holder(order)
        if not who or who == frappe.session.user:
            frappe.db.set_value("Sales Order", order,
                                {"custom_cc_open_by": "", "custom_cc_open_at": None},
                                update_modified=False)
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
    if frappe.db.get_value("Sales Order", order, "company") != _CO:
        frappe.throw("Unknown order.")
    _own_guard(role, order)
    frappe.get_doc("Sales Order", order).add_comment(
        "Comment", f"Note — {note[:400]} · by {frappe.session.user}")
    _first_touch(order)
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
    # Desk comments arrive as Quill HTML — the timeline was rendering raw
    # '<div class="ql-editor...' markup. Strip to text before slicing.
    import re as _re
    from frappe.utils import strip_html_tags

    def _plain(c):
        c = strip_html_tags(c or "")
        c = c.replace("&nbsp;", " ").replace("&amp;", "&")
        return _re.sub(r"\s+", " ", c).strip()

    return {"rows": [{
        "by": (r.owner or "").split("@")[0],
        "text": _plain(r.content)[:300],
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
    # The plan has to match what next_order will actually do, or the pane lies:
    # pinned work is served first, so it is listed first.
    pinned = _pins_for(scope_user)
    me_q = ""
    vals = {"co": _CO, "limit": limit, "now": str(now_datetime())[:19]}
    if mine:
        vals["me_like"] = f'%"{scope_user}"%'
        me_q = " AND so._assign LIKE %(me_like)s"

    retry_sts = tuple(v for k, v in QUEUES.items() if k != "pending")
    sel = """SELECT so.name, so.customer_name customer, so.grand_total total,
                    so.custom_sales_status status,
                    COALESCE(so.custom_call_attempts, 0) attempts,
                    so.custom_next_call_at next_call,
                    GREATEST(0, TIMESTAMPDIFF(HOUR, so.creation, %(now)s)) age_h"""
    _open_vals(vals)
    _free = " AND " + _open_free_cond()
    due = frappe.db.sql(
        f"""{sel} FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(sts)s AND {_IN_HAND}
              AND {_DUE}{me_q}{_free}
            ORDER BY {_DUE_AT} LIMIT %(limit)s""",
        {**vals, "sts": retry_sts}, as_dict=True)
    room = max(0, limit - len(due))
    fresh = frappe.db.sql(
        f"""{sel} FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status = 'Pending' AND {_IN_HAND}
              AND so.creation >= DATE_SUB(NOW(), INTERVAL 30 DAY){me_q}{_free}
            ORDER BY so.creation LIMIT %(room)s""",
        {**vals, "room": room}, as_dict=True) if room else []

    upcoming = frappe.db.sql(
        f"""SELECT MIN(so.custom_next_call_at) FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status IN %(sts)s AND {_IN_HAND}
              AND so.custom_next_call_at > %(now)s{me_q}""",
        {**vals, "sts": retry_sts})[0][0]

    status_tab = {"Did not Answer": "dna", "Follow Up": "followup",
                  "Not Delivered": "nd", "Duplicated": "duplicated"}

    def _when(dt):
        # HH:MM reads as "today" — a call-back due TOMORROW 08:30 must say so.
        # Shown on the floor's clock, not the site's: a call-back the portal
        # printed as 16:30 was due at 14:30 where the person taking it stands.
        if not dt:
            return ""
        v = str(_clock.to_floor(dt))
        return v[11:16] if v[:10] == _clock.floor_today() else v[5:16]

    rows = [{
        "order": r.name, "customer": r.customer or "",
        "total": float(r.total or 0), "ageH": int(r.age_h or 0),
        "attempts": int(r.attempts or 0),
        "due": bool(r.status != "Pending"),
        "kind": status_tab.get(r.status, "pending"),
        "nextCall": _when(r.next_call),
    } for r in list(due) + list(fresh)]
    if pinned:
        # Pinned rows lead, and anything also present below is de-duplicated so
        # the same order is not promised twice in one plan.
        seen = set(pinned)
        head = []
        for pr in frappe.db.sql(
                """SELECT so.name, so.customer_name AS customer, so.grand_total AS total,
                          so.custom_sales_status AS status,
                          TIMESTAMPDIFF(HOUR, so.creation, %s) AS age_h,
                          COALESCE(so.custom_call_attempts, 0) AS attempts
                   FROM `tabSales Order` so WHERE so.name IN %s""",
                (str(now_datetime())[:19], tuple(pinned)), as_dict=True):
            head.append({
                "order": pr.name, "customer": pr.customer or "",
                "total": float(pr.total or 0), "ageH": int(pr.age_h or 0),
                "attempts": int(pr.attempts or 0), "due": False,
                "kind": status_tab.get(pr.status, "pending"),
                "nextCall": "", "pinned": True})
        head.sort(key=lambda x: pinned.index(x["order"]))
        rows = head + [r for r in rows if r["order"] not in seen]
        rows = rows[:limit]
    return {"rows": rows, "pinned": pinned, "nextDueAt": _when(upcoming),
            "dueCount": len(due),
            # Admin scope serves the whole pool — the pane must not call the
            # team's plan "my queue".
            "scope": "mine" if mine else "team"}


def run_alerts():
    """Scheduled every 15 min: the stage before confirmation belongs to this
    lane, so this lane is paged when it slips — Pending orders older than the
    first-call target (slaFirstCallH) with no call logged, the same test the
    queue's red badge makes. Same alert store and Alerts page as the tracking
    portal; the audience is the confirmation team."""
    try:
        from logistics_portal.api.shipments import _emit
        now = _clock.floor_now()
        if not (8 <= now.hour < 22):
            return
        sla_h = int(_cf_settings().get("slaFirstCallH", 6))
        row = frappe.db.sql(
            """SELECT COUNT(*), MAX(TIMESTAMPDIFF(HOUR, creation, NOW()))
               FROM `tabSales Order`
               WHERE docstatus = 1 AND company = %(co)s
                 AND custom_sales_status = 'Pending'
                 AND COALESCE(custom_call_attempts, 0) = 0
                 AND creation <= DATE_SUB(NOW(), INTERVAL %(h)s HOUR)
                 AND creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)""",
            {"co": _CO, "h": sla_h})[0]
        n, oldest = int(row[0] or 0), int(row[1] or 0)
        if n >= 5:
            _emit("cf_first_call", {"n": n, "h": sla_h, "oldest": oldest},
                  severity="critical" if n >= 30 else "warning", cooldown_h=4,
                  audience="confirmation")
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "confirmation.run_alerts")
    run_stock_gap_alert()


# ---------------------------------------------------------------------------
# The stock gap — orders this lane PROMISED that the warehouse cannot ship.
#
# A confirmation is a promise made on the phone: the customer said yes and was
# told it is coming. When the shelf turns out to be empty the order does not
# fail loudly — it sits in the picking pool marked "out of stock" and nobody
# tells the person who made the promise. Measured 2026-09-17: 79 confirmed
# orders were in that state, the oldest six days old, and not one of their
# customers had been called back.
#
# So this is the other half of the confirm button. The agent who said yes is
# the one shown the gap, with the customer's number in the same row, because
# the only useful action here is a call: offer a swap, agree to wait, or
# cancel honestly. Anything else leaves a customer waiting for a parcel that
# was never going to come.
# ---------------------------------------------------------------------------

def _gap_rows(me=None, days=45, limit=60):
    """Confirmed orders with no pick list whose lines the floor cannot cover."""
    from logistics_portal.api.picking import availability, _LINE_CODE, _LINE_NAME, _LINE_NEED, _LINE_JOIN
    vals = {"co": _CO, "days": min(max(int(days or 45), 1), 180)}
    scope = ""
    if me:
        scope = " AND so.custom_allocated_to = %(me)s"
        vals["me"] = me
    rows = frappe.db.sql(
        f"""SELECT so.name AS `order`, so.customer_name AS customer, so.grand_total AS total,
                   so.creation, so.custom_customer_phone AS phone,
                   so.custom_shipping_phone AS phone2, so.custom_allocated_to AS agent,
                   TIMESTAMPDIFF(HOUR, so.creation, NOW()) AS age_h,
                   {_LINE_CODE} AS item_code, {_LINE_NAME} AS item_name, {_LINE_NEED} AS need
            FROM `tabSales Order` so
            JOIN `tabSales Order Item` soi ON soi.parent = so.name {_LINE_JOIN}
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status = 'Confirmed'
              AND so.custom_logistics_status = 'Pending'
              AND so.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY){scope}
              AND NOT EXISTS (SELECT 1 FROM `tabPick List Item` pli
                              JOIN `tabPick List` p ON p.name = pli.parent
                              WHERE pli.sales_order = so.name AND p.docstatus < 2)
            ORDER BY so.creation""", vals, as_dict=True)
    if not rows:
        return []
    codes = list({r.item_code for r in rows if r.item_code})
    if not codes:
        return []
    _totals, _sre, free = availability(codes)
    orders = {}
    for r in rows:
        need = float(r.need or 0)
        if need <= 0:
            continue
        o = orders.setdefault(r.order, {
            "order": r.order, "customer": r.customer or "", "total": float(r.total or 0),
            "phone": (r.phone or r.phone2 or "").strip(), "agent": r.agent or "",
            # The floor's clock runs two hours behind the stored one, so a
            # fresh order can measure as negative hours old. Nobody needs to
            # read "-2h waiting".
            "ageH": max(0, int(r.age_h or 0)), "short": []})
        have = float(free(r.order, r.item_code) or 0)
        if have + 0.001 < need:
            # A bundle's components arrive as separate rows of the same item:
            # one line per missing PIECE, not one per row of the join.
            hit = next((x for x in o["short"] if x["itemCode"] == r.item_code), None)
            if hit:
                hit["need"] = max(hit["need"], int(need))
                continue
            sku = frappe.db.get_value("Item", r.item_code, "custom_sku") or r.item_code
            o["short"].append({
                "itemCode": r.item_code, "sku": sku, "name": r.item_name or sku,
                "need": int(need), "have": int(max(0, have)),
                "eta": _incoming_eta(r.item_code),
            })
    out = [o for o in orders.values() if o["short"]]
    # Oldest promise first: the customer who has waited longest is owed the
    # call first, and the money is only a tie-breaker.
    out.sort(key=lambda x: (-x["ageH"], -x["total"]))
    return out[:min(max(int(limit or 60), 1), 200)]


def _incoming_eta(item_code):
    """Is more of this on its way? The answer decides what the agent says:
    a date means "it is late", nothing means "it is not coming"."""
    row = frappe.db.sql(
        """SELECT MIN(COALESCE(poi.schedule_date, po.schedule_date)) AS d,
                  SUM(poi.qty - poi.received_qty) AS q
           FROM `tabPurchase Order Item` poi
           JOIN `tabPurchase Order` po ON po.name = poi.parent
           WHERE poi.item_code = %s AND po.docstatus = 1
             AND po.status NOT IN ('Closed', 'Completed', 'Cancelled')
             AND poi.received_qty < poi.qty""", (item_code,), as_dict=True)
    if not row or not row[0].q:
        return None
    return {"date": str(row[0].d or "")[:10], "qty": int(float(row[0].q or 0))}


@frappe.whitelist()
def stock_gap(days=45, limit=60, as_user=None):
    """The agent's own promises the warehouse cannot keep. A manager (or a
    section admin) sees the whole lane, and may look through one agent's eyes
    with `as_user`, the same way the board does."""
    role = _gate()
    mine_only = role != "manager" and not _is_cf_admin()
    me = frappe.session.user
    as_user = (as_user or "").strip()
    if as_user and not mine_only:
        me, mine_only = as_user, True
    rows = _gap_rows(me if mine_only else None, days=days, limit=limit)
    return {
        "rows": rows, "n": len(rows),
        "value": round(sum(r["total"] for r in rows)),
        "oldestH": max([r["ageH"] for r in rows], default=0),
        "scope": "mine" if mine_only else "team",
        "reasons": reason_options(),
    }


def run_stock_gap_alert():
    """Page the lane when promises start piling up against an empty shelf."""
    try:
        from logistics_portal.api.shipments import _emit
        now = _clock.floor_now()
        if not (8 <= now.hour < 22):
            return
        rows = _gap_rows(None, days=45, limit=200)
        if len(rows) < 5:
            return
        oldest = max(r["ageH"] for r in rows)
        _emit("cf_stock_gap",
              {"n": len(rows), "d": max(1, oldest // 24),
               "value": round(sum(r["total"] for r in rows)),
               "order": rows[0]["order"], "customer": rows[0]["customer"]},
              severity="critical" if oldest >= 72 else "warning",
              cooldown_h=6, audience=("confirmation", "manager"))
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "confirmation.run_stock_gap_alert")


@frappe.whitelist()
def new_orders_ping(since=None):
    """The "new orders just landed" heartbeat — TKT-2609-3803989, item 1.

    Returns how many Pending orders ARRIVED (creation, site clock) after
    `since`, in the caller's own scope — an agent counts only their _assign,
    a manager or section admin the whole section — plus the server clock so
    the client can baseline the next call without trusting its own clock.
    Deliberately one indexed COUNT and nothing else: it polls forever from
    every open confirmation tab, so it must stay too cheap to notice.
    """
    import re as _re
    role = _gate()
    since = (since or "").strip()[:19]
    now = str(now_datetime())[:19]
    if not _re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", since):
        # First call of a session: no baseline yet — hand one out.
        return {"count": 0, "serverNow": now}
    vals = {"co": _CO, "since": since}
    scope = ""
    if role != "manager" and not _is_cf_admin():
        vals["me_like"] = f'%"{frappe.session.user}"%'
        scope = " AND so._assign LIKE %(me_like)s"
    n = frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s
              AND so.custom_sales_status = 'Pending'
              AND so.creation > %(since)s{scope}""", vals)[0][0]
    return {"count": int(n or 0), "serverNow": now}


# ── the lane's pulse: is the funnel healthy ───────────────────────────────
#
# The section already had three screens and none of them answered the
# question a manager actually asks in the morning. `dashboard` describes the
# queue standing right now, `activity` is the trail, `reports` is a per-agent
# table. What was missing is the shape of the whole thing: of the orders that
# ARRIVED, how many became a promise, how many became a parcel, and how many
# reached a customer — and where the rest went.
#
# Everything here is a COHORT: the window selects orders by when they
# arrived, and every number follows those same orders forward. That is the
# only framing in which "80% confirm" and "78% of those stick" can be
# multiplied into a truth about the business. An activity window — decisions
# taken this week, on orders from any week — cannot be chained like that, and
# mixing the two is how a funnel starts lying.
#
# Measured while building it, 14 days: 5,651 arrived, 4,551 confirmed
# (80.5%), 3,573 delivered (78.5% of confirmed) — 63.2% of everything that
# came in reached a customer, and the daily numbers barely move.

_PULSE_CACHE = "lp_cf_pulse"


def _range_before(days, frm, to):
    """The SAME LENGTH of time, immediately before the window asked for.

    The only honest "is this better than it was". Comparing a rolling 30 days
    against "last month" compares 30 days with 28 or 31, and the difference
    shows up as a trend that is really a calendar."""
    import re as _re
    ok = lambda d: bool(d and _re.match(r"^\d{4}-\d{2}-\d{2}$", str(d).strip()))
    if ok(frm) or ok(to):
        from frappe.utils import add_days, getdate
        a = getdate(str(frm).strip()) if ok(frm) else None
        b = getdate(str(to).strip()) if ok(to) else None
        if not (a and b):
            return None, {}
        span = (b - a).days + 1
        pa, pb = add_days(a, -span), add_days(a, -1)
        return ("{col} >= %(pfrm)s AND {col} < %(pto)s",
                {"pfrm": _clock.day_bounds(str(pa))[0],
                 "pto": _clock.day_bounds(str(pb))[1]})
    days = min(max(int(days or 30), 1), 365)
    return ("{col} >= DATE_SUB(NOW(), INTERVAL %(d2)s DAY) "
            "AND {col} < DATE_SUB(NOW(), INTERVAL %(d1)s DAY)",
            {"d1": days, "d2": days * 2})


def _period(days, frm, to):
    """What the header should call this window."""
    if frm or to:
        return f"{frm or '…'} → {to or '…'}"
    return f"{int(days)}d"


def _pulse_speed(rng, vals):
    """How long a customer waits for a human, over this cohort.

    Median, never an average: the tail is orders picked up days later and it
    drags a mean somewhere nobody recognises. Only over the orders a human
    actually touched — the ones the automation closed untouched are reported
    beside it, because folding them in would flatter the number beyond
    recognition."""
    if not frappe.get_meta("Sales Order").has_field("custom_first_touch_at"):
        return {"median": None, "p90": None, "slaPct": None, "n": 0,
                "untouched": 0, "slaH": None, "missing": True}
    mins, untouched = [], 0
    for r in frappe.db.sql(
            f"""SELECT so.custom_first_touch_at ft,
                       TIMESTAMPDIFF(MINUTE, so.creation, so.custom_first_touch_at) m
                FROM `tabSales Order` so
                WHERE so.docstatus = 1 AND so.company = %(co)s
                  AND {rng.format(col="so.creation")}""", vals, as_dict=True):
        if r.ft and r.m is not None and int(r.m) >= 0:
            mins.append(int(r.m))
        else:
            untouched += 1
    sla_min = int(_cf_settings().get("slaFirstCallH", 6)) * 60
    return _first_touch_summary(mins, untouched, sla_min)


def _pulse_funnel(rng, vals):
    """One pass over a cohort: what arrived and what became of it."""
    r = frappe.db.sql(
        f"""SELECT COUNT(*) arrived,
                   COALESCE(SUM(CASE WHEN so.grand_total <= %(sane)s
                                     THEN so.grand_total ELSE 0 END), 0) value,
                   SUM(so.custom_sales_status = 'Confirmed') confirmed,
                   SUM(so.custom_sales_status = 'Cancelled') cancelled,
                   SUM(so.custom_sales_status IN %(live)s) still_open,
                   SUM(so.custom_track_shipment_status = 'Delivered') delivered,
                   SUM(so.custom_track_shipment_status IN %(bad)s) failed,
                   COALESCE(SUM(CASE WHEN so.custom_sales_status = 'Confirmed'
                                      AND so.grand_total <= %(sane)s
                                     THEN so.grand_total ELSE 0 END), 0) confirmed_value,
                   COALESCE(SUM(CASE WHEN so.custom_track_shipment_status = 'Delivered'
                                      AND so.grand_total <= %(sane)s
                                     THEN so.grand_total ELSE 0 END), 0) collected,
                   COALESCE(SUM(CASE WHEN so.custom_sales_status = 'Cancelled'
                                      AND so.grand_total <= %(sane)s
                                     THEN so.grand_total ELSE 0 END), 0) lost_cancel,
                   COALESCE(SUM(CASE WHEN so.custom_track_shipment_status IN %(bad)s
                                      AND so.grand_total <= %(sane)s
                                     THEN so.grand_total ELSE 0 END), 0) lost_door
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s AND {rng.format(col="so.creation")}""",
        vals, as_dict=True)[0]
    arrived = int(r.arrived or 0)
    confirmed = int(r.confirmed or 0)
    delivered = int(r.delivered or 0)
    failed = int(r.failed or 0)
    # A cohort is not finished the day it is measured. Of the 9,121 orders
    # confirmed in the last 30 days, 1,220 are still moving — no verdict yet,
    # neither delivered nor failed. Divide by `confirmed` and a young cohort
    # always looks worse than an old one, whatever anybody did.
    #
    # Measured while building this, and it is not a rounding matter: the
    # naive rate read 68.7% against 73.3% the month before and said quality
    # had FALLEN 4.7 points. Over the parcels that actually reached a verdict
    # it is 79.3% against 74.2% — quality ROSE 5.1. The dashboard would have
    # had the manager fixing a problem that did not exist.
    settled = delivered + failed
    in_flight = max(0, confirmed - settled)
    return {
        "arrived": arrived, "value": round(float(r.value or 0)),
        "confirmed": confirmed, "cancelled": int(r.cancelled or 0),
        "open": int(r.still_open or 0),
        "delivered": delivered, "failed": failed,
        # Named, never hidden: a number that quietly excludes 13% of the
        # cohort has to say so on the screen.
        "settled": settled, "inFlight": in_flight,
        "confirmedValue": round(float(r.confirmed_value or 0)),
        "collected": round(float(r.collected or 0)),
        "lostCancel": round(float(r.lost_cancel or 0)),
        "lostDoor": round(float(r.lost_door or 0)),
        # The two rates that chain: of what came in, what was promised; of
        # what was promised, what actually arrived.
        "confirmRate": round(confirmed * 100.0 / arrived, 1) if arrived else None,
        # Of the parcels that reached a verdict — the only form of this that
        # can be compared with last month.
        "stickRate": round(delivered * 100.0 / settled, 1) if settled else None,
        # Of everything that came in, what reached a customer. Same maturity
        # caveat, so it is measured against the part of the cohort that is
        # actually finished rather than against everything that arrived.
        "reachRate": round(delivered * 100.0 / (arrived - in_flight), 1)
                     if (arrived - in_flight) > 0 else None,
        "matured": round(100.0 - (in_flight * 100.0 / confirmed), 1) if confirmed else None,
    }


@frappe.whitelist()
def pulse_board(days=30, frm=None, to=None):
    """The funnel, its leaks, and how it compares with the period before it."""
    _gate()
    if not _is_cf_admin():
        frappe.throw("Only the portal manager or a section admin can open the "
                     "section pulse.", frappe.PermissionError)
    import json as _pj
    days = min(max(int(days or 30), 1), 365)
    ck = f"{_PULSE_CACHE}_{days}_{frm or ''}_{to or ''}"
    hit = frappe.cache().get_value(ck)
    if hit:
        try:
            return _pj.loads(hit)
        except Exception:
            pass

    rng, rv = _range(days, frm, to)
    base = {"co": _CO, "sane": _SANE_MAX, "live": tuple(QUEUES.values()),
            "bad": ("Delivery Exception", "Failed Attempt", "Return")}
    now = _period(days, frm, to)

    cur = _pulse_funnel(rng, {**base, **rv})
    # The same length of time, immediately before — the only honest "is this
    # better than it was". Comparing a 30-day window with "last month" would
    # compare 30 days against 28 or 31.
    prv_rng, prv_v = _range_before(days, frm, to)
    prev = _pulse_funnel(prv_rng, {**base, **prv_v}) if prv_rng else None

    daily = [{"d": str(r.d), "arrived": int(r.arrived or 0),
              "confirmed": int(r.confirmed or 0), "delivered": int(r.delivered or 0)}
             for r in frappe.db.sql(
                 f"""SELECT DATE(so.creation) d, COUNT(*) arrived,
                            SUM(so.custom_sales_status = 'Confirmed') confirmed,
                            SUM(so.custom_track_shipment_status = 'Delivered') delivered
                     FROM `tabSales Order` so
                     WHERE so.docstatus = 1 AND so.company = %(co)s
                       AND {rng.format(col="so.creation")}
                     GROUP BY d ORDER BY d""", {**base, **rv}, as_dict=True)]

    # Why the money left, in the order it costs: a cancel is a sale that
    # never happened, a door failure is one that cost a round trip as well.
    reasons = [{"reason": (r.reason or "—"), "n": int(r.n or 0),
                "value": round(float(r.value or 0))}
               for r in frappe.db.sql(
                   f"""SELECT COALESCE(NULLIF(so.custom_cancellation_reason,''),'—') reason,
                              COUNT(*) n,
                              COALESCE(SUM(CASE WHEN so.grand_total <= %(sane)s
                                                THEN so.grand_total ELSE 0 END),0) value
                       FROM `tabSales Order` so
                       WHERE so.docstatus = 1 AND so.company = %(co)s
                         AND so.custom_sales_status = 'Cancelled'
                         AND {rng.format(col="so.creation")}
                       GROUP BY reason ORDER BY value DESC LIMIT 8""",
                   {**base, **rv}, as_dict=True)]

    # The city lives on the linked ADDRESS, not on the order: the order's own
    # custom_shipping_city is filled on well under 1% of rows. Reading the raw
    # field put a blank at the top of this panel with 3,171 parcels behind it
    # — the single most prominent row on the card, and meaningless. _EFF_CITY
    # is the expression the picking lane and the city screens already share.
    from logistics_portal.api.picking import _EFF_CITY
    cities = [{"city": (r.city or "—").title(), "n": int(r.n or 0),
               "value": round(float(r.value or 0))}
              for r in frappe.db.sql(
                  f"""SELECT COALESCE(NULLIF(TRIM({_EFF_CITY}),''),'—') city,
                             COUNT(*) n,
                             COALESCE(SUM(CASE WHEN so.grand_total <= %(sane)s
                                               THEN so.grand_total ELSE 0 END),0) value
                      FROM `tabSales Order` so
                      WHERE so.docstatus = 1 AND so.company = %(co)s
                        AND so.custom_track_shipment_status IN %(bad)s
                        AND {rng.format(col="so.creation")}
                      GROUP BY city ORDER BY n DESC LIMIT 9""",
                  {**base, **rv}, as_dict=True)]

    out = {"funnel": cur, "prev": prev, "daily": daily,
           "reasons": reasons, "cities": cities,
           "speed": _pulse_speed(rng, {**base, **rv}),
           "days": days, "frm": frm or "", "to": to or "", "period": now,
           "serverNow": str(now_datetime())[:19]}
    try:
        frappe.cache().set_value(ck, _pj.dumps(out), expires_in_sec=180)
    except Exception:
        pass
    return out
