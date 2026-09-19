"""Customer service — the desk that receives a problem from anywhere.

Audited 2026-09-18, before writing any of this. Four ticket systems already
exist on the site and none of them is a working customer desk:

  JoyAgent Conversation  12,747 rows, WhatsApp + Messenger, very much alive —
                         but it is a CONVERSATION store, not a request desk.
                         607 conversations are flagged "Handed Off" to a
                         human; 572 of those never got a human reply and the
                         oldest has been waiting since 19 August. The handoff
                         exists and lands in a field nobody opens.
  Hub Ticket             alive (75/30d) and correctly used — for INTERNAL
                         staff issues between departments. Not customers.
  HD Ticket              244 rows, 243 of them still Open, 239 written by
                         Administrator. A machine-fed graveyard.
  Issue                  8 rows, ever, from January.

So the gap is real and a fifth table is justified — but only if it is
clearly a CUSTOMER REQUEST, distinct from Hub Ticket's internal work and
from a conversation.

One request, three doors:
  a person hands it over  an agent (AI or human) on any channel, or an agent
                          in the confirmation/tracking lanes, presses one
                          button on the order in front of them
  the system raises it    problems already detectable and currently owned by
                          nobody: a confirmed order whose stock is gone, an
                          exchange stuck for weeks, a parcel with no trace
  the customer answers    the post-delivery feedback loop: an unhappy reply
                          becomes a request with the customer's words on it

The conversation is LINKED, never absorbed: a request must be able to exist
before the customer has said anything (the system raised it), and must show
the thread when there is one.
"""

import re

import frappe
from frappe.utils import add_to_date, now_datetime

DT = "LP CS Request"
_CO = "Justyol Morocco"

# What the customer's problem IS. Deliberately short: six buttons an agent
# can hit mid-conversation without reading. A longer list is a form, and the
# Issue lane proved what happens to forms here — eight tickets in a year.
KINDS = ("stock", "wrong_item", "exchange", "late", "damaged", "refund", "other")

# Where it came from, kept separate from WHO raised it: the channel tells you
# how to answer, the person tells you who to ask.
SOURCES = ("agent", "social", "confirmation", "tracking", "system", "feedback")

STATES = ("new", "open", "waiting_customer", "waiting_team", "done")
_LIVE = ("new", "open", "waiting_customer", "waiting_team")


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("cs", "confirmation", "tracking", "manager"):
        frappe.throw("lp:csOnly", frappe.PermissionError)
    return role


def _desk_gate():
    """Working the queue is the CS team's job; every other lane may only
    RAISE a request, never take one. A tracking agent who could claim a CS
    request would be the handover quietly failing to hand anything over."""
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("cs", "manager"):
        frappe.throw("lp:csOnly", frappe.PermissionError)
    return role


def ensure_doctype():
    """Create the request table on migrate. Custom doctype: lives in the DB,
    no schema files, safe to run every time."""
    try:
        if frappe.db.exists("DocType", DT):
            return
        frappe.get_doc({
            "doctype": "DocType", "name": DT, "module": "Core",
            "custom": 1, "naming_rule": "Expression (old style)",
            "autoname": "naming_series:", "title_field": "customer_name",
            "fields": [
                {"fieldname": "naming_series", "fieldtype": "Data",
                 "label": "Series", "default": "CSR-.YY..MM.-.####", "hidden": 1},
                {"fieldname": "kind", "fieldtype": "Data", "label": "Kind",
                 "in_standard_filter": 1, "in_list_view": 1},
                {"fieldname": "state", "fieldtype": "Data", "label": "State",
                 "default": "new", "in_standard_filter": 1, "in_list_view": 1},
                {"fieldname": "source", "fieldtype": "Data", "label": "Source",
                 "in_standard_filter": 1},
                {"fieldname": "customer_name", "fieldtype": "Data", "label": "Customer",
                 "in_list_view": 1},
                {"fieldname": "phone", "fieldtype": "Data", "label": "Phone"},
                {"fieldname": "so", "fieldtype": "Data", "label": "Order",
                 "in_standard_filter": 1, "in_list_view": 1},
                {"fieldname": "conversation", "fieldtype": "Data",
                 "label": "JoyAgent Conversation"},
                {"fieldname": "note", "fieldtype": "Small Text", "label": "What happened"},
                {"fieldname": "raised_by", "fieldtype": "Data", "label": "Raised by"},
                {"fieldname": "owner_agent", "fieldtype": "Data", "label": "Held by",
                 "in_standard_filter": 1},
                {"fieldname": "claimed_at", "fieldtype": "Datetime", "label": "Taken at"},
                {"fieldname": "wait_until", "fieldtype": "Datetime", "label": "Sleeping until"},
                {"fieldname": "resolved_at", "fieldtype": "Datetime", "label": "Resolved"},
                {"fieldname": "resolved_by", "fieldtype": "Data", "label": "Resolved by"},
                {"fieldname": "resolution", "fieldtype": "Small Text", "label": "Resolution"},
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "cs.ensure_doctype")


# ── raising one ───────────────────────────────────────────────────────────

def _digits(p):
    d = re.sub(r"\D", "", str(p or ""))
    if d.startswith("212"):
        d = d[3:]
    return d.lstrip("0")


def _order_context(order):
    """Customer, phone and conversation for an order — so the agent raising
    the request types nothing but the one line that matters."""
    row = frappe.db.get_value(
        "Sales Order", order,
        ["customer_name", "custom_customer_phone", "custom_shipping_phone"],
        as_dict=True) or {}
    phone = (row.get("custom_customer_phone") or row.get("custom_shipping_phone") or "").strip()
    conv = ""
    tail = _digits(phone)
    if tail and len(tail) >= 6:
        conv = frappe.db.sql(
            """SELECT name FROM `tabJoyAgent Conversation`
               WHERE REGEXP_REPLACE(COALESCE(customer_phone,''), '[^0-9]', '') LIKE %(p)s
               ORDER BY COALESCE(last_message_at, creation) DESC LIMIT 1""",
            {"p": "%" + tail}) or ""
        conv = conv[0][0] if conv else ""
    return {"customer_name": row.get("customer_name") or "", "phone": phone,
            "conversation": conv}


def _dupe(order, phone, kind):
    """The same problem raised twice is one problem. Two agents noticing the
    same late parcel must not produce two requests for the desk to reconcile
    — the second one becomes a note on the first."""
    if not (order or phone):
        return ""
    conds, vals = ["state IN %(live)s", "kind = %(k)s"], {"live": _LIVE, "k": kind}
    if order:
        conds.append("so = %(o)s")
        vals["o"] = order
    else:
        conds.append("phone = %(p)s")
        vals["p"] = phone
    hit = frappe.db.sql(
        f"SELECT name FROM `tab{DT}` WHERE {' AND '.join(conds)} ORDER BY creation DESC LIMIT 1",
        vals)
    return hit[0][0] if hit else ""


@frappe.whitelist(methods=["POST"])
def raise_request(kind, note="", order="", phone="", source="", conversation=""):
    """Hand a customer problem to CS. Two taps from anywhere in the portal.

    Everything except the kind and one line is inferred from where the agent
    pressed it — an agent mid-call will not fill a form, which is exactly how
    the Issue lane reached eight tickets in a year."""
    role = _gate()
    kind = (kind or "").strip().lower()
    if kind not in KINDS:
        frappe.throw("Unknown problem type.")
    order = (order or "").strip()
    note = (note or "").strip()[:1000]
    if order and frappe.db.get_value("Sales Order", order, "company") != _CO:
        frappe.throw("Unknown order.")

    ctx = _order_context(order) if order else {}
    phone = (phone or ctx.get("phone") or "").strip()
    conversation = (conversation or ctx.get("conversation") or "").strip()
    source = (source or "").strip().lower()
    if source not in SOURCES:
        source = {"confirmation": "confirmation", "tracking": "tracking",
                  "cs": "agent", "manager": "agent"}.get(role, "agent")

    same = _dupe(order, phone, kind)
    if same:
        try:
            frappe.get_doc(DT, same).add_comment(
                "Comment", f"Also seen by {frappe.session.user}"
                           + (f" — {note}" if note else ""))
        except Exception:
            pass
        return {"ok": True, "request": same, "merged": True}

    doc = frappe.get_doc({
        "doctype": DT, "kind": kind, "state": "new", "source": source,
        "customer_name": ctx.get("customer_name") or "", "phone": phone,
        "so": order, "conversation": conversation, "note": note,
        "raised_by": frappe.session.user,
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    _bust()
    return {"ok": True, "request": doc.name, "merged": False}


# ── the desk ──────────────────────────────────────────────────────────────

_CACHE = "lp_cs_counts"


def _bust():
    try:
        frappe.cache().delete_value(_CACHE)
    except Exception:
        pass


TABS = ("new", "mine", "waiting", "done")
_TAB_STATE = {"new": ("new",), "waiting": ("waiting_customer", "waiting_team"),
              "done": ("done",)}


def _tab_where(tab, vals):
    me = frappe.session.user
    if tab == "mine":
        vals["me"] = me
        return "state IN %(live)s AND owner_agent = %(me)s", {"live": _LIVE}
    if tab == "done":
        # Today's closures only: a desk measures the day, and an all-time
        # list of finished work is a report, not a queue.
        vals["d0"] = str(add_to_date(now_datetime(), days=-1))[:19]
        return "state = 'done' AND resolved_at >= %(d0)s", {}
    if tab == "waiting":
        vals["w"] = _TAB_STATE["waiting"]
        return "state IN %(w)s", {}
    # new: nobody has taken it, and it is not asleep
    vals["snow"] = str(now_datetime())[:19]
    return ("state = 'new' AND (wait_until IS NULL OR wait_until <= %(snow)s)", {})


@frappe.whitelist()
def board(tab="new", q="", kind="", limit=30, offset=0):
    _gate()
    if not frappe.db.exists("DocType", DT):
        return {"tab": tab, "tabs": list(TABS), "counts": {}, "rows": [], "total": 0,
                "available": False}
    if tab not in TABS:
        tab = "new"
    limit = min(max(int(limit or 30), 1), 100)
    offset = max(int(offset or 0), 0)
    vals = {"live": _LIVE, "limit": limit, "offset": offset}
    where, extra = _tab_where(tab, vals)
    vals.update(extra)
    if kind and kind in KINDS:
        where += " AND kind = %(k)s"
        vals["k"] = kind
    if q and str(q).strip():
        vals["q"] = f"%{str(q).strip()}%"
        where += (" AND (customer_name LIKE %(q)s OR so LIKE %(q)s OR name LIKE %(q)s"
                  " OR note LIKE %(q)s)")

    counts = {}
    for t in TABS:
        v = {"live": _LIVE}
        w, e = _tab_where(t, v)
        v.update(e)
        counts[t] = int(frappe.db.sql(f"SELECT COUNT(*) FROM `tab{DT}` WHERE {w}", v)[0][0])
    counts["byKind"] = {r[0]: int(r[1]) for r in frappe.db.sql(
        f"SELECT kind, COUNT(*) FROM `tab{DT}` WHERE state IN %(live)s GROUP BY 1",
        {"live": _LIVE})}

    total = int(frappe.db.sql(f"SELECT COUNT(*) FROM `tab{DT}` WHERE {where}", vals)[0][0])
    rows = frappe.db.sql(
        f"""SELECT name, kind, state, source, customer_name, phone, so, conversation,
                   note, raised_by, owner_agent, wait_until, creation
            FROM `tab{DT}` WHERE {where}
            ORDER BY creation DESC LIMIT %(limit)s OFFSET %(offset)s""",
        vals, as_dict=True)

    # The parcel's live state, in one read for the whole page: a CS agent
    # answering "where is my order" must not have to leave the card.
    parcels = {}
    orders = [r.so for r in rows if r.so]
    if orders:
        for p in frappe.db.sql(
                """SELECT dni.against_sales_order so, dn.custom_track_shipment_status trk,
                          dn.custom_awb awb, dn.posting_date shipped
                   FROM `tabDelivery Note` dn
                   JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
                   WHERE dn.docstatus = 1 AND dni.against_sales_order IN %(o)s""",
                {"o": tuple(orders)}, as_dict=True):
            parcels.setdefault(p.so, {"track": p.trk or "", "awb": p.awb or "",
                                      "shipped": str(p.shipped or "")[:10]})

    now = now_datetime()
    me = frappe.session.user
    return {
        "tab": tab, "tabs": list(TABS), "counts": counts, "total": total,
        "kinds": list(KINDS),
        "rows": [{
            "name": r.name, "kind": r.kind, "state": r.state, "source": r.source,
            "customer": r.customer_name or "", "phone": (r.phone or "").strip(),
            "order": r.so or "", "conversation": r.conversation or "",
            "note": r.note or "", "raisedBy": (r.raised_by or "").split("@")[0],
            "heldBy": (r.owner_agent or "").split("@")[0],
            "heldMine": r.owner_agent == me,
            "waitUntil": str(r.wait_until or "")[:16],
            "ageMin": max(0, int((now - r.creation).total_seconds() // 60)),
            "parcel": parcels.get(r.so or "", {}),
        } for r in rows],
        "available": True,
    }


# ── working one ───────────────────────────────────────────────────────────

def _req(name):
    name = (name or "").strip()
    if not frappe.db.exists(DT, name):
        frappe.throw("Unknown request.")
    return name


@frappe.whitelist(methods=["POST"])
def claim(name):
    """Take it. Serialized on the request, and committed inside the lock —
    the named lock spans workers but an uncommitted write is invisible to
    the next transaction, so both agents would otherwise be told yes."""
    _desk_gate()
    name = _req(name)
    from logistics_portal.api.locks import named_lock
    me = frappe.session.user
    with named_lock(f"cs_claim_{name}"):
        cur = frappe.db.get_value(DT, name, ["owner_agent", "state"], as_dict=True)
        if cur.owner_agent and cur.owner_agent != me:
            return {"ok": False, "reason": "taken", "by": cur.owner_agent}
        frappe.db.set_value(DT, name, {
            "owner_agent": me, "claimed_at": now_datetime(),
            "state": "open" if cur.state == "new" else cur.state,
        }, update_modified=False)
        frappe.db.commit()
    _bust()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def release(name, reason=""):
    _desk_gate()
    name = _req(name)
    me = frappe.session.user
    who = frappe.db.get_value(DT, name, "owner_agent")
    if who and who != me:
        from logistics_portal.api.auth import resolve_role
        if resolve_role(me) != "manager":
            return {"ok": False, "reason": "taken", "by": who}
    frappe.db.set_value(DT, name, {"owner_agent": "", "claimed_at": None,
                                   "state": "new"}, update_modified=False)
    try:
        frappe.get_doc(DT, name).add_comment(
            "Comment", f"Handed back by {me}" + (f" — {reason}" if reason else ""))
    except Exception:
        pass
    _bust()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def note(name, text=""):
    _gate()
    name = _req(name)
    text = (text or "").strip()
    if not text:
        frappe.throw("Nothing to save.")
    frappe.get_doc(DT, name).add_comment(
        "Comment", f"{text[:900]} · by {frappe.session.user}")
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def wait(name, days=1, who="customer", reason=""):
    """Park it. A request waiting on a customer or another team must leave
    the queue until it is due, or the desk learns to scroll past a list that
    is mostly things nobody can act on today."""
    _desk_gate()
    name = _req(name)
    days = min(max(int(days or 1), 1), 30)
    until = add_to_date(now_datetime(), days=days)
    frappe.db.set_value(DT, name, {
        "state": "waiting_customer" if who == "customer" else "waiting_team",
        "wait_until": until, "owner_agent": frappe.session.user,
    }, update_modified=False)
    try:
        frappe.get_doc(DT, name).add_comment(
            "Comment", f"Waiting on {who} until {str(until)[:16]}"
                       + (f" — {reason}" if reason else "")
                       + f" · by {frappe.session.user}")
    except Exception:
        pass
    _bust()
    return {"ok": True, "until": str(until)[:16]}


@frappe.whitelist(methods=["POST"])
def resolve(name, resolution=""):
    _desk_gate()
    name = _req(name)
    resolution = (resolution or "").strip()
    if not resolution:
        frappe.throw("Say what was done.")
    now = now_datetime()
    frappe.db.set_value(DT, name, {
        "state": "done", "resolved_at": now, "resolved_by": frappe.session.user,
        "resolution": resolution[:1000], "wait_until": None,
    }, update_modified=False)
    try:
        frappe.get_doc(DT, name).add_comment(
            "Comment", f"Resolved — {resolution[:500]} · by {frappe.session.user}")
    except Exception:
        pass
    _bust()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def set_kind(name, kind):
    """Retype it. The intake guesses from thin evidence on purpose (see
    _guess_kind), so correcting it has to be one tap on the card rather
    than an edit screen."""
    _desk_gate()
    name = _req(name)
    kind = (kind or "").strip().lower()
    if kind not in KINDS:
        frappe.throw("Unknown problem type.")
    was = frappe.db.get_value(DT, name, "kind")
    if was == kind:
        return {"ok": True}
    frappe.db.set_value(DT, name, "kind", kind, update_modified=False)
    try:
        frappe.get_doc(DT, name).add_comment(
            "Comment", f"Type {was or '—'} → {kind} · by {frappe.session.user}")
    except Exception:
        pass
    _bust()
    return {"ok": True}


@frappe.whitelist()
def timeline(name, limit=40):
    _gate()
    name = _req(name)
    rows = frappe.db.sql(
        """SELECT content, owner, creation FROM `tabComment`
           WHERE reference_doctype = %(dt)s AND reference_name = %(n)s
           ORDER BY creation DESC LIMIT %(l)s""",
        {"dt": DT, "n": name, "l": min(max(int(limit or 40), 1), 100)}, as_dict=True)
    doc = frappe.db.get_value(
        DT, name, ["kind", "state", "so", "phone", "conversation", "note",
                   "raised_by", "owner_agent", "resolution"], as_dict=True)
    thread = []
    if doc.conversation:
        thread = [{
            "from": "customer" if (m.direction or "") == "Inbound" else "us",
            "who": m.sender or "", "text": (m.content or "")[:400],
            "at": str(m.creation)[:16],
        } for m in frappe.db.sql(
            """SELECT content, direction, sender, creation FROM `tabJoyAgent Message`
               WHERE conversation = %(c)s ORDER BY creation DESC LIMIT 20""",
            {"c": doc.conversation}, as_dict=True)]
    return {"request": dict(doc), "events": [{
        "text": re.sub(r"<[^>]+>", "", r.content or "")[:300],
        "by": (r.owner or "").split("@")[0], "at": str(r.creation)[:16],
    } for r in rows], "thread": thread}


@frappe.whitelist()
def pulse(since=""):
    """Has anything landed since the screen last looked? One indexed count,
    the same shape the rescue and confirmation desks already use."""
    _gate()
    if not frappe.db.exists("DocType", DT):
        return {"n": 0, "now": str(now_datetime())[:19]}
    since = str(since or "")[:19]
    if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", since):
        since = str(add_to_date(now_datetime(), minutes=-10))[:19]
    r = frappe.db.sql(
        f"""SELECT COUNT(*) n, MIN(creation) oldest FROM `tab{DT}`
            WHERE state = 'new' AND creation > %(s)s""", {"s": since}, as_dict=True)[0]
    waiting = int(frappe.db.sql(
        f"SELECT COUNT(*) FROM `tab{DT}` WHERE state = 'new'")[0][0] or 0)
    return {"n": int(r.n or 0), "waiting": waiting, "now": str(now_datetime())[:19]}


# ── the doors that open themselves ────────────────────────────────────────

_KIND_HINTS = (
    ("stock", ("rupture", "stock", "indispo", "نفد", "مش متوفر")),
    ("late", ("retard", "late", "delay", "اتأخر", "متأخر", "فين الطلب")),
    ("wrong_item", ("mauvais", "wrong", "غلط", "مش اللي طلبت")),
    ("damaged", ("cassé", "abim", "damaged", "مكسور", "تالف")),
    ("exchange", ("échange", "echange", "exchange", "تبديل", "استبدال")),
    ("refund", ("remboursement", "refund", "استرجاع", "فلوسي")),
)


# The AI's own label, when it bothered to set one. Better evidence than
# anything we can infer, and it is already in the row.
_CAT_KIND = {
    "shipping issue": "late", "return/exchange": "exchange",
    "payment/cod": "refund", "complaint": "other", "other": "other",
}


def _guess_kind(text, category=""):
    """The AI's category first, the customer's words second, "other" last.

    Checked against the 606 live handoffs before trusting this: the keyword
    pass alone answers "other" for essentially all of them, because the last
    inbound message is a greeting, the standard help-button text, an emoji
    or "[audio]" — nobody types "ma commande est en retard". A classifier
    that always says "other" is not a classifier, so it is a fallback here
    rather than the mechanism, and the desk sets the kind in one tap on the
    card. Guessing confidently from evidence this thin would be worse than
    admitting we do not know."""
    cat = _CAT_KIND.get((category or "").strip().lower())
    if cat:
        return cat
    t = (text or "").lower()
    for kind, words in _KIND_HINTS:
        for w in words:
            if w in t:
                return kind
    return "other"


def intake_joyagent():
    """Scheduled: turn a conversation the AI handed to a human into a request.

    Measured 2026-09-18: 607 conversations sit at "Handed Off", 572 of them
    never answered and the oldest since 19 August, because the handoff is a
    field and nobody has a screen on it. This is that screen's intake. It
    also explains why the reason is usually blank — 591 of the 607 carry no
    handoff_reason and no handed_off_at at all, so the request falls back to
    the customer's own last words, which is better evidence anyway."""
    try:
        if not frappe.db.exists("DocType", DT):
            return
        rows = frappe.db.sql(
            """SELECT c.name, c.customer_phone, c.customer_name, c.linked_sales_order,
                      c.handoff_reason, c.category, c.summary
               FROM `tabJoyAgent Conversation` c
               WHERE c.status = 'Handed Off'
                 AND NOT EXISTS (SELECT 1 FROM `tab%s` r WHERE r.conversation = c.name)
               ORDER BY COALESCE(c.handed_off_at, c.last_message_at, c.creation) DESC
               LIMIT 200""" % DT, as_dict=True)
        made = 0
        for c in rows:
            last = frappe.db.sql(
                """SELECT content FROM `tabJoyAgent Message`
                   WHERE conversation = %(c)s AND direction = 'Inbound'
                   ORDER BY creation DESC LIMIT 1""", {"c": c.name})
            words = (last[0][0] if last else "") or c.summary or ""
            note = (c.handoff_reason or "").strip() or words[:400]
            frappe.get_doc({
                "doctype": DT, "kind": _guess_kind(words, c.category), "state": "new",
                "source": "agent", "customer_name": c.customer_name or "",
                "phone": c.customer_phone or "", "so": c.linked_sales_order or "",
                "conversation": c.name, "note": note,
                "raised_by": "joyagent",
            }).insert(ignore_permissions=True)
            made += 1
        if made:
            frappe.db.commit()
            _bust()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "cs.intake_joyagent")


def release_stale_claims():
    """Hourly: a claim is a promise to finish. Anything held four hours with
    no movement goes back, so the queue never drains into private piles."""
    try:
        if not frappe.db.exists("DocType", DT):
            return
        cut = str(add_to_date(now_datetime(), hours=-4))[:19]
        rows = frappe.db.sql(
            f"""SELECT name FROM `tab{DT}` WHERE COALESCE(owner_agent,'') <> ''
                AND state = 'open' AND COALESCE(claimed_at,'1900-01-01') < %(c)s
                AND modified < %(c)s LIMIT 200""", {"c": cut})
        for (n,) in rows:
            frappe.db.set_value(DT, n, {"owner_agent": "", "claimed_at": None,
                                        "state": "new"}, update_modified=False)
        if rows:
            frappe.db.commit()
            _bust()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "cs.release_stale_claims")


def wake_due():
    """Hourly: a parked request whose date has arrived comes back by itself,
    or parking quietly becomes forgetting."""
    try:
        if not frappe.db.exists("DocType", DT):
            return
        now = str(now_datetime())[:19]
        rows = frappe.db.sql(
            f"""SELECT name FROM `tab{DT}` WHERE state IN ('waiting_customer','waiting_team')
                AND wait_until IS NOT NULL AND wait_until <= %(n)s LIMIT 200""", {"n": now})
        for (n,) in rows:
            frappe.db.set_value(DT, n, {"state": "new", "wait_until": None},
                                update_modified=False)
        if rows:
            frappe.db.commit()
            _bust()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "cs.wake_due")


_STALE_CLOSE = "Closed: the conversation went quiet"


@frappe.whitelist()
def close_stale(days=30, apply=0, limit=1000):
    """Close requests whose conversation has been silent for a month.

    The first intake produced 607 requests, and that number is honest about
    the handoff backlog but dishonest about the work: measured 2026-09-18,
    337 of them sit on conversations whose last message is older than thirty
    days — the oldest from 18 June. A customer who has not written since
    June is not waiting for an answer, and a queue that opens on 607 rows
    teaches a new team to scroll rather than work.

    Age alone decides it. The obvious alternative was to also judge the
    TEXT — close the ones that only say "Salam" or "[audio]" — and that was
    the wrong instinct: a real complaint can be four words, and being
    silently closed is a much worse failure than being read and dismissed.
    Silence for a month is evidence; brevity is not.

    Read-only unless `apply` is set, because this writes a resolution onto
    hundreds of live rows."""
    _desk_gate()
    days = min(max(int(days or 30), 7), 365)
    limit = min(max(int(limit or 1000), 1), 5000)
    cut = str(add_to_date(now_datetime(), days=-days))[:19]
    rows = frappe.db.sql(
        f"""SELECT r.name, c.last_message_at FROM `tab{DT}` r
            JOIN `tabJoyAgent Conversation` c ON c.name = r.conversation
            WHERE r.state = 'new'
              AND (c.last_message_at IS NULL OR c.last_message_at < %(cut)s)
            ORDER BY c.last_message_at LIMIT %(l)s""",
        {"cut": cut, "l": limit}, as_dict=True)
    total = int(frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tab{DT}` r
            JOIN `tabJoyAgent Conversation` c ON c.name = r.conversation
            WHERE r.state = 'new'
              AND (c.last_message_at IS NULL OR c.last_message_at < %(cut)s)""",
        {"cut": cut})[0][0] or 0)
    if not int(apply or 0):
        return {"ok": True, "applied": 0, "matched": total, "days": days,
                "oldest": str(rows[0].last_message_at or "")[:10] if rows else "",
                "sample": [r.name for r in rows[:5]]}
    now = now_datetime()
    done = 0
    for r in rows:
        try:
            frappe.db.set_value(DT, r.name, {
                "state": "done", "resolved_at": now, "resolved_by": "system",
                "resolution": f"{_STALE_CLOSE} ({days}d silent)",
            }, update_modified=False)
            done += 1
        except Exception:
            continue
    frappe.db.commit()
    _bust()
    return {"ok": True, "applied": done, "matched": total, "left": max(0, total - done)}


def close_stale_daily():
    """Keep it closed, not just clean it once. A conversation that goes
    quiet for a month while nobody answered has stopped being work whether
    it arrived today or in June."""
    try:
        if not frappe.db.exists("DocType", DT):
            return
        cut = str(add_to_date(now_datetime(), days=-30))[:19]
        rows = frappe.db.sql(
            f"""SELECT r.name FROM `tab{DT}` r
                JOIN `tabJoyAgent Conversation` c ON c.name = r.conversation
                WHERE r.state = 'new'
                  AND (c.last_message_at IS NULL OR c.last_message_at < %(cut)s)
                LIMIT 500""", {"cut": cut})
        now = now_datetime()
        for (n,) in rows:
            frappe.db.set_value(DT, n, {
                "state": "done", "resolved_at": now, "resolved_by": "system",
                "resolution": f"{_STALE_CLOSE} (30d silent)",
            }, update_modified=False)
        if rows:
            frappe.db.commit()
            _bust()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "cs.close_stale_daily")


# ── the lookup: any order, any customer, when the phone rings ─────────────
#
# Measured on production before writing this (2026-09-19), because the shape
# of the answer depended entirely on what the data actually is:
#
#   There is no customer entity. 175,711 Customer records carry 267,163
#   orders — one record per order. Anything keyed on `customer` is empty.
#
#   The phone IS the identity: present on 28,675 of 28,702 orders in 90 days
#   (99.9%) and on all three order sources — Shopify (#), J-, and the
#   landing/agent SAL-ORD series. `custom_shipping_phone` is not an option:
#   it is empty on every Shopify order.
#
#   53,139 phones carry 2+ orders — 160,302 orders, 60% of everything. So
#   the repeat customer is the norm here, not the exception.
#
#   The same person is stored three ways: +212XXXXXXXXX (65%), 0XXXXXXXXX
#   (34%), 212XXXXXXXXX. 99.6% of numbers reduce to the same 9 national
#   digits, and 99.6% of those begin 6 or 7 (Moroccan mobile). Checked 4,000
#   keys that hold more than one stored form: 3,981 are pure format variants
#   of one number; the 19 that are not are foreign (+90, +32) or 000000000.
#   So the last nine digits are a sound identity, and matching the literal
#   string is not.
#
# On speed, all measured warm on the live table (an early 788ms reading was
# a cold cache and is not the number to design against):
#
#   phone match, no ORDER BY          364 ms   type=ALL, one sequential pass
#   phone match, ORDER BY date DESC   838 ms   type=index on transaction_date
#   COUNT(*) alone                    270 ms
#   name prefix, ORDER BY date        4 ms
#   order number + company            100 ms
#
# So the phone branch does NOT sort or count in SQL. With `ORDER BY
# transaction_date DESC` the optimiser walks the date index and runs the
# regex row by row looking for a page of matches that mostly is not there —
# 2.3x the cost of simply reading the table once. A phone has a handful of
# orders: fetch them unsorted under a cap, then sort and count in Python.
# That also drops the separate COUNT query, so one 364ms call replaces
# 838 + 270.
#
# An index plus a list of literal phone formats would make it ~5ms, and was
# rejected: it finds 99.65% and fails SILENTLY on the rest — a new format
# appears and the agent sees part of a customer's history with nothing to
# say so. For a desk that answers a person on the phone, 364ms and the whole
# truth beats 5ms and a quiet lie. The desk is three people and ~130
# conversations a day: one search every four minutes. There is nothing here
# to optimise. Revisit if the table doubles — measured, on a staging copy.
#
# The frontend must search on SUBMIT, never per keystroke.

_PHONE_DIGITS = "REGEXP_REPLACE(COALESCE(so.custom_customer_phone,''), '[^0-9]', '')"
_PHONE_KEY = f"RIGHT({_PHONE_DIGITS}, 9)"


# One number's whole history, with headroom — the longest seen on
# production is a few dozen orders. The cap is a floor under the worst
# case: a junk key like 000000000 must not pull the table into memory.
_PHONE_CAP = 300


def _mine(rows):
    """Morocco only, newest first — applied in Python on purpose.

    Adding `company = ...` to the phone query flips the optimiser onto the
    company/date index and costs 3x for a filter that removes 5% of the
    table (256,790 of 269,308 orders are Justyol Morocco). On a handful of
    rows it is free here."""
    rows = [r for r in rows if (r.get("company") or _CO) == _CO]
    rows.sort(key=lambda r: (str(r.get("transaction_date") or ""), r.get("name") or ""),
              reverse=True)
    return rows


def _phone_key(q):
    """The last nine digits of anything that looks like a Moroccan number."""
    d = re.sub(r"\D", "", str(q or ""))
    return d[-9:] if len(d) >= 9 else ""


@frappe.whitelist()
def search(q="", limit=25, offset=0):
    """Find any order by phone, customer name, or order number.

    Not `shipping.tracking`: that board is windowed to the last 14-90 days
    because 24k stale parcel statuses are history, not work. A customer on
    the phone asking about an order from March needs the whole table, and
    needs it whether the parcel ever moved at all.

    Routing a typed string. Both halves of this were wrong on the first
    pass and both were caught against real order ids:

      contains a letter  an order id ('J-007748', 'SAL-ORD-2026-03373') or,
                         with no digits at all, a customer name. Letters
                         settle it: SAL-ORD-2026-03373 carries nine digits
                         and was being answered as a phone with a confident
                         zero.
      9 digits starting  a Moroccan mobile -> phone. Measured over the whole
      6 or 7             table: the last nine digits begin 6 (234,043) or 7
                         (30,849) on 99.6% of stored numbers, so the prefix
                         is what separates a number from a numeral.
      any other digits   an order number first ('#260443'), and only if that
                         finds nothing does a 6+ digit string fall back to a
                         phone tail. Six digits is far more often a short
                         order number here than half a dictated phone.
    """
    _gate()
    q = (str(q or "")).strip()[:60]
    if len(q) < 3:
        return {"rows": [], "total": 0, "mode": "", "hasMore": False}
    limit = min(max(int(limit or 25), 1), 50)
    offset = max(int(offset or 0), 0)

    digits = re.sub(r"\D", "", q)
    has_alpha = bool(re.search(r"[A-Za-z]", q))
    key = "" if has_alpha else _phone_key(q)

    if key and key[0] in "67":
        return _by_phone(_PHONE_KEY + " = %(key)s", {"key": key}, key, limit, offset)

    if digits:
        hit = _cheap(
            "so.name LIKE %(o)s", {"o": "%" + q.lstrip("#").strip() + "%"},
            "order", "", limit, offset)
        if hit["rows"] or has_alpha or len(digits) < 6:
            return hit
        # Nothing by order number and enough digits to be half a phone.
        if key:
            return _by_phone(_PHONE_KEY + " = %(key)s", {"key": key},
                             key, limit, offset)
        return _by_phone(_PHONE_DIGITS + " LIKE %(tail)s",
                         {"tail": "%" + digits}, "", limit, offset)

    return _cheap("so.customer_name LIKE %(n)s", {"n": q + "%"}, "name",
                  "ORDER BY so.transaction_date DESC, so.creation DESC",
                  limit, offset)


_SEARCH_COLS = (
    "so.name, so.customer_name, so.custom_customer_phone phone, "
    "so.transaction_date, so.grand_total, so.status, so.company, "
    "so.custom_sales_status, so.custom_logistics_status, "
    "so.custom_shipping_city city, so.custom_tracking_number awb")


def _by_phone(cond, vals, key, limit, offset):
    """One unsorted capped pass. See the speed note: sorting this branch in
    SQL costs 2.3x, and one number's whole history fits in the cap, so the
    sort and the exact count both happen in Python instead."""
    rows = _mine(frappe.db.sql(
        "SELECT " + _SEARCH_COLS + " FROM `tabSales Order` so "
        "WHERE so.docstatus < 2 AND (" + cond + ") LIMIT " + str(_PHONE_CAP),
        vals, as_dict=True))
    page = rows[offset:offset + limit]
    return {"mode": "phone", "key": key, "total": len(rows),
            "capped": len(rows) >= _PHONE_CAP,
            "hasMore": offset + limit < len(rows),
            "rows": [_order_row(r) for r in page]}


def _cheap(cond, vals, mode, order_by, limit, offset):
    """Name and order number are index-friendly (4ms and 100ms measured),
    and company narrows the order-number scan threefold — the opposite of
    what it does to the phone branch. No COUNT: a common first name matches
    thousands and counting them cost more than the page itself, while
    nobody needs the number. One extra row answers 'is there more'."""
    vals["co"] = _CO
    where = "so.docstatus < 2 AND so.company = %(co)s AND (" + cond + ")"
    rows = frappe.db.sql(
        "SELECT " + _SEARCH_COLS + " FROM `tabSales Order` so WHERE " + where
        + " " + order_by + " LIMIT " + str(limit + 1) + " OFFSET " + str(offset),
        vals, as_dict=True)
    more = len(rows) > limit
    rows = rows[:limit]
    return {"mode": mode, "key": "", "total": offset + len(rows),
            "capped": False, "hasMore": more,
            "rows": [_order_row(r) for r in rows]}


def _order_row(r):
    return {
        "order": r.name, "customer": r.customer_name or "",
        "phone": (r.phone or "").strip(),
        "date": str(r.transaction_date or "")[:10],
        "total": float(r.grand_total or 0),
        "city": (r.city or "").strip().title(),
        "awb": r.awb or "",
        "sales": r.custom_sales_status or "",
        "logistics": r.custom_logistics_status or "",
        "status": r.status or "",
    }


# A parcel state that says the delivery went wrong. Same vocabulary the
# rescue board uses, so a CS agent and a tracking agent never disagree about
# what "failed" means.
_BAD_TRACK = ("Delivery Exception", "Failed Attempt", "Return")

# Past this age, silence from the carrier means the status was never
# synced, not that the parcel is in flight.
_STALE_AFTER_D = 60


@frappe.whitelist()
def customer(phone="", order=""):
    """Everything we know about the person on the line.

    Either a phone or an order to take the phone from. Returns the whole
    order history on that number — never a window — plus what it adds up to,
    the CS requests already raised, and the conversation if there is one.

    The history is the point: 60% of orders belong to a number that has
    ordered before, and an agent who cannot see the previous five is
    answering blind."""
    _gate()
    phone = (str(phone or "")).strip()
    if not phone and order:
        phone = (frappe.db.get_value("Sales Order", order,
                                     "custom_customer_phone") or "").strip()
    key = _phone_key(phone)
    if not key:
        return {"found": False, "phone": phone}

    rows = frappe.db.sql(
        f"""SELECT so.name, so.customer_name, so.custom_customer_phone phone,
                   so.transaction_date, so.grand_total, so.status, so.company,
                   so.custom_sales_status, so.custom_logistics_status,
                   so.custom_shipping_city city, so.custom_tracking_number awb,
                   so.custom_delivered_at delivered_at,
                   (SELECT MAX(dn.custom_track_shipment_status)
                      FROM `tabDelivery Note Item` di
                      JOIN `tabDelivery Note` dn
                        ON dn.name = di.parent AND dn.docstatus = 1
                     WHERE di.against_sales_order = so.name) track
            FROM `tabSales Order` so
            WHERE so.docstatus < 2 AND {_PHONE_KEY} = %(key)s
            LIMIT {_PHONE_CAP}""", {"key": key}, as_dict=True)
    rows = _mine(rows)
    if not rows:
        return {"found": False, "phone": phone, "key": key}

    _stale_cut = str(add_to_date(now_datetime(), days=-_STALE_AFTER_D))[:10]
    orders, delivered, failed, cancelled, spend, landed = [], 0, 0, 0, 0.0, 0.0
    unknown = 0
    for r in rows:
        row = _order_row(r)
        row["track"] = r.track or ""
        row["deliveredAt"] = str(r.delivered_at or "")[:10]
        is_del = (r.track == "Delivered") or bool(r.delivered_at)
        is_can = (r.custom_sales_status or "") == "Cancelled"
        if is_del:
            row["outcome"] = "delivered"
        elif is_can:
            row["outcome"] = "cancelled"
        elif r.track in _BAD_TRACK:
            row["outcome"] = "failed"
        elif not r.track and str(r.transaction_date or "") < _stale_cut:
            # 23,602 orders older than 60 days carry no carrier status and no
            # delivery stamp. Calling those "open" would tell an agent a
            # parcel from last year is still moving. We do not know, and
            # saying so is the only honest answer.
            row["outcome"] = "unknown"
        else:
            row["outcome"] = "open"
        orders.append(row)
        spend += float(r.grand_total or 0)
        if is_del:
            delivered += 1
            landed += float(r.grand_total or 0)
        elif is_can:
            cancelled += 1
        elif r.track in _BAD_TRACK:
            failed += 1
        elif row["outcome"] == "unknown":
            unknown += 1

    n = len(orders)
    # The one thing worth flagging on sight. Measured over 180 days: 1,275
    # numbers with 3+ orders and 2+ gone bad account for 5,424 orders, 3,892
    # of them bad, 1,111,637 MAD. Not a blocklist — the agent decides what to
    # do with it (ask for prepayment, confirm harder, or nothing).
    risky = n >= 3 and (failed + cancelled) >= 2

    names = []
    for r in rows:
        nm = (r.customer_name or "").strip()
        if nm and nm.lower() not in [x.lower() for x in names]:
            names.append(nm)

    reqs = []
    if frappe.db.exists("DocType", DT):
        reqs = frappe.db.sql(
            f"""SELECT name, kind, state, so, note, creation, owner_agent
                FROM `tab{DT}` WHERE REGEXP_REPLACE(COALESCE(phone,''),'[^0-9]','')
                                     LIKE %(t)s
                ORDER BY creation DESC LIMIT 20""",
            {"t": "%" + key}, as_dict=True)

    # WhatsApp stores 212XXXXXXXXX, so the last nine match. Messenger stores
    # a 17-digit page-scoped id that is not a phone at all — matching its
    # tail would hand the agent a stranger's conversation, so the length
    # guard is doing real work here.
    conv = frappe.db.sql(
        """SELECT name, channel, status, last_message_at, summary, unread
           FROM `tabJoyAgent Conversation`
           WHERE REGEXP_REPLACE(COALESCE(customer_phone,''),'[^0-9]','') LIKE %(t)s
             AND LENGTH(REGEXP_REPLACE(COALESCE(customer_phone,''),'[^0-9]','')) <= 13
           ORDER BY COALESCE(last_message_at, creation) DESC LIMIT 5""",
        {"t": "%" + key}, as_dict=True)

    return {
        "found": True, "phone": phone or (rows[0].phone or ""), "key": key,
        "names": names[:4], "name": names[0] if names else "",
        "city": (rows[0].city or "").strip().title(),
        "totals": {
            "orders": n, "delivered": delivered, "failed": failed,
            "cancelled": cancelled, "unknown": unknown,
            "open": n - delivered - failed - cancelled - unknown,
            "spend": round(spend), "landed": round(landed),
            "deliveryRate": round(delivered * 100 / n) if n else 0,
        },
        "risky": risky,
        "firstOrder": orders[-1]["date"] if orders else "",
        "lastOrder": orders[0]["date"] if orders else "",
        "orders": orders,
        "requests": [{"name": r.name, "kind": r.kind, "state": r.state,
                      "order": r.so or "", "note": (r.note or "")[:120],
                      "at": str(r.creation)[:19], "by": (r.owner_agent or "")}
                     for r in reqs],
        "conversations": [{"name": c.name, "channel": c.channel or "",
                           "status": c.status or "", "unread": int(c.unread or 0),
                           "at": str(c.last_message_at or "")[:19],
                           "summary": (c.summary or "")[:160]} for c in conv],
    }
