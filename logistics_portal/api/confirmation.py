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


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("confirmation", "manager"):
        frappe.throw("Not authorized for the confirmation workspace.",
                     frappe.PermissionError)
    return role


@frappe.whitelist()
def board(tab="pending", days=30, q="", limit=30, offset=0):
    """The four queues + counts + my day so far, one call."""
    _gate()
    if tab not in QUEUES and tab not in DONE_QUEUES and tab != "backlog":
        tab = "pending"
    days = min(max(int(days or 30), 1), 90)
    limit = min(max(int(limit or 30), 1), 100)
    offset = max(int(offset or 0), 0)
    vals = {"days": days, "limit": limit, "offset": offset}

    counts = {k: 0 for k in QUEUES}
    for r in frappe.db.sql(
            """SELECT custom_sales_status s, COUNT(*) n FROM `tabSales Order`
               WHERE docstatus = 1 AND custom_sales_status IN %(sts)s
                 AND creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)
               GROUP BY custom_sales_status""",
            {"sts": tuple(QUEUES.values()), "days": days}, as_dict=True):
        for k, v in QUEUES.items():
            if v == r.s:
                counts[k] = int(r.n or 0)
    # Orders that aged past the working window (2,900 were invisible) —
    # an explicit tab with bulk-expire instead of a silent cutoff.
    counts["backlog"] = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabSales Order`
           WHERE docstatus = 1 AND custom_sales_status IN %(sts)s
             AND creation < DATE_SUB(NOW(), INTERVAL %(days)s DAY)""",
        {"sts": tuple(QUEUES.values()), "days": days})[0][0])
    # Done tabs: keyed on when the DECISION was taken (custom_last_call_at),
    # not when the order arrived — the agent looks for "what I did today",
    # and a 40-day-old order confirmed an hour ago has to be in reach.
    for r in frappe.db.sql(
            """SELECT custom_sales_status s, COUNT(*) n FROM `tabSales Order`
               WHERE docstatus = 1 AND custom_sales_status IN %(sts)s
                 AND COALESCE(custom_last_call_at, modified)
                     >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)""",
            {"sts": tuple(DONE_QUEUES.values()), "days": days}, as_dict=True):
        for k, v in DONE_QUEUES.items():
            if v == r.s:
                counts[k] = int(r.n or 0)

    if tab in DONE_QUEUES:
        conds = ["so.docstatus = 1", "so.custom_sales_status = %(status)s",
                 """COALESCE(so.custom_last_call_at, so.modified)
                    >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)"""]
        vals["status"] = DONE_QUEUES[tab]
    elif tab == "backlog":
        conds = ["so.docstatus = 1", "so.custom_sales_status IN %(statuses)s",
                 "so.creation < DATE_SUB(NOW(), INTERVAL %(days)s DAY)"]
        vals["statuses"] = tuple(QUEUES.values())
    else:
        conds = ["so.docstatus = 1", "so.custom_sales_status = %(status)s",
                 "so.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)"]
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
        order_by = "COALESCE(so.custom_last_call_at, so.modified) DESC"  # newest decision first
    elif tab in ("pending", "backlog"):
        order_by = "so.creation"
    else:
        order_by = "COALESCE(so.custom_next_call_at, so.creation), so.creation"
    # custom_cancellation_reason is the desk's field — absent on sites that
    # never had it, so only select it when the meta says it exists.
    reason_col = ("so.custom_cancellation_reason"
                  if frappe.get_meta("Sales Order").has_field("custom_cancellation_reason")
                  else "NULL")
    rows = frappe.db.sql(
        f"""SELECT so.name, so.customer_name AS customer, so.grand_total AS total,
                   COALESCE(NULLIF(so.custom_customer_phone,''),
                            so.custom_shipping_phone) AS phone,
                   so.custom_shipping_city AS city,
                   so.custom_items_count AS item_count,
                   TIMESTAMPDIFF(HOUR, so.creation, NOW()) AS age_h,
                   COALESCE(so.custom_call_attempts, 0) AS attempts,
                   so.custom_last_call_at AS last_call,
                   so.custom_next_call_at AS next_call,
                   so.custom_confirmation_agent AS agent,
                   so.custom_sales_status AS status,
                   {reason_col} AS reason
            FROM `tabSales Order` so WHERE {where}
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

    return {
        "tab": tab, "counts": counts, "total": int(total or 0),
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
    if action == "cancel" and not note:
        frappe.throw("A cancel needs a reason.")

    now = now_datetime()
    attempts = int(so.custom_call_attempts or 0)
    updates = {
        "custom_sales_status": _ACTIONS[action],
        "custom_confirmation_agent": frappe.session.user,
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
        # The desk stores the reason in this field (272 edits/14d) — keep the
        # desk reports seeing portal cancels too, not just the comment trail.
        updates["custom_cancellation_reason"] = note[:140]
    frappe.db.set_value("Sales Order", order, updates, update_modified=True)

    doc = frappe.get_doc("Sales Order", order)
    doc.add_comment("Comment",
                    f"Confirmation: {action}"
                    + (f" (attempt {attempts})" if action in _RETRY_HOURS else "")
                    + (f" — {note}" if note else "")
                    + f" · by {frappe.session.user}")
    frappe.db.commit()
    if action in ("confirm", "cancel", "reopen"):
        # The order entered / left the logistics pool.
        for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
            frappe.cache().delete_value(k)
        frappe.cache().delete_keys("lp_suggest")
    return {"ok": True, "order": order, "action": action, "attempts": attempts}


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
                   "custom_confirmation_agent": frappe.session.user,
                   "custom_last_call_at": now, "custom_next_call_at": None}
        if has_reason_field:
            updates["custom_cancellation_reason"] = reason[:140]
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
    "reasons": ["Prix trop élevé", "Commande par erreur", "Ne répond plus",
                "Adresse hors zone", "Commande dupliquée", "A changé d'avis"],
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


def _is_cf_admin():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) == "manager":
        return True
    return frappe.session.user in _cf_settings().get("admins", [])


@frappe.whitelist()
def cf_settings():
    _gate()
    s = _cf_settings()
    return {**s, "canEdit": _is_cf_admin()}


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
    if "reasons" in settings:
        reasons = [str(r).strip()[:60] for r in (settings["reasons"] or []) if str(r).strip()]
        if not reasons:
            frappe.throw("Keep at least one cancel reason.")
        out["reasons"] = reasons[:20]
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
def report(days=7):
    """The section's own report: per-agent decisions, confirm rate, attempts,
    cancel-reason breakdown and the day-by-day funnel. Manager or section
    admin (agents see their own numbers on the workspace itself)."""
    _gate()
    if not _is_cf_admin():
        frappe.throw("Only the portal manager or a section admin can open the "
                     "section report.", frappe.PermissionError)
    days = min(max(int(days or 7), 1), 90)
    since = f"DATE_SUB(NOW(), INTERVAL {days} DAY)"

    # Per-agent decision counts from the Comment trail the workspace writes.
    per_agent = {}
    for r in frappe.db.sql(
            f"""SELECT c.owner, c.content FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order'
                  AND c.content LIKE 'Confirmation: %%'
                  AND c.creation >= {since}""", as_dict=True):
        action = (r.content.split("Confirmation: ", 1)[1] or "").split(" ", 1)[0]
        action = action.strip("()—- ")
        a = per_agent.setdefault(r.owner, {"confirm": 0, "cancel": 0, "dna": 0,
                                           "followup": 0, "onhold": 0,
                                           "duplicate": 0})
        if action in a:
            a[action] += 1

    agents = []
    for user, a in per_agent.items():
        decided = a["confirm"] + a["cancel"]
        stats = frappe.db.sql(
            f"""SELECT AVG(custom_call_attempts), COUNT(*) FROM `tabSales Order`
                WHERE custom_confirmation_agent = %s
                  AND custom_sales_status = 'Confirmed'
                  AND custom_last_call_at >= {since}""", (user,))[0]
        agents.append({
            "agent": user.split("@")[0], "user": user, **a,
            "total": sum(a.values()),
            "confirmRate": round(a["confirm"] * 100.0 / decided, 1) if decided else 0,
            "avgAttempts": round(float(stats[0] or 0), 1),
        })
    agents.sort(key=lambda x: -x["total"])

    # Cancel reasons breakdown (reason text sits between '—' and '· by').
    reasons = {}
    for r in frappe.db.sql(
            f"""SELECT c.content FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order'
                  AND c.content LIKE 'Confirmation: cancel%%'
                  AND c.creation >= {since}""", as_dict=True):
        txt = r.content
        reason = ""
        if "—" in txt:
            reason = txt.split("—", 1)[1].split("· by", 1)[0].strip()
        reasons[reason or "(no reason)"] = reasons.get(reason or "(no reason)", 0) + 1
    reason_rows = sorted(({"reason": k, "n": v} for k, v in reasons.items()),
                         key=lambda x: -x["n"])[:12]

    # Day-by-day funnel: how many orders ENTERED each terminal state.
    funnel = frappe.db.sql(
        f"""SELECT DATE(c.creation) d,
                   SUM(c.content LIKE 'Confirmation: confirm%%') conf,
                   SUM(c.content LIKE 'Confirmation: cancel%%') canc,
                   SUM(c.content LIKE 'Confirmation: dna%%') dna
            FROM `tabComment` c
            WHERE c.reference_doctype = 'Sales Order'
              AND c.content LIKE 'Confirmation: %%' AND c.creation >= {since}
            GROUP BY DATE(c.creation) ORDER BY d""", as_dict=True)

    return {
        "days": days,
        "agents": agents,
        "reasons": reason_rows,
        "funnel": [{"date": str(f.d), "confirm": int(f.conf or 0),
                    "cancel": int(f.canc or 0), "dna": int(f.dna or 0)} for f in funnel],
    }
