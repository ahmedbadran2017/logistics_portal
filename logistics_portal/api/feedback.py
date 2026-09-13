"""Post-delivery feedback over WhatsApp — the parcel's last question.

The confirmation automation already talks to every customer before the
parcel leaves (First Contact, Confirmed, reminders: ~15k template sends a
month) and stops the moment the order is confirmed. Nobody asks the customer
anything after the door. This closes that loop with ONE question the day
after delivery — happy or not — and routes the answer: a happy customer gets
a thank-you (with whatever review link or code the team configures), an
unhappy one becomes a CS ticket with the reply attached, so a human calls.

Measured on production before writing this (2026-09-13):

  130–716 deliveries a day, `custom_delivered_at` stamped on 99.8% of them
  and a phone on 99.98%, so the trigger is a plain timestamp, not a Version
  scan. Button replies carry `reply_to_message_id` on 2,230 of 2,232 recent
  presses, so a tap is matched to the exact message we sent, never guessed
  from a phone number. Free-text sends inside the 24h service window already
  work on this account (190 in 90 days), so the thank-you needs no second
  Meta template.

What this does NOT do: it never touches the confirmation automation, its
templates, or the Whatsapp Manager slots; it ships DISABLED and sends nothing
until a tracking lead picks an approved template and switches it on.
"""
import json
import re

import frappe
from frappe.utils import now_datetime, add_to_date

DT = "LP Delivery Feedback"
_CO = "Justyol Morocco"
_SETTINGS_KEY = "lp_feedback_settings"

_DEFAULTS = {
    "enabled": False,
    # An APPROVED WhatsApp template with two quick-reply buttons. Its first
    # body parameter, if any, receives the customer's first name.
    "template": "",
    "delayHours": 20,
    "maxAgeDays": 5,
    "windowStart": "10:00",
    "windowEnd": "20:00",
    "dailyCap": 400,
    # Ask one phone at most once in this many days, whatever they ordered.
    "phoneCooldownDays": 30,
    "replyWindowH": 72,
    # Button labels (or words in a typed reply) that decide the verdict.
    "positiveWords": ["راضي", "ممتاز", "رائع", "شكرا", "شكراً", "satisfait", "merci", "oui", "نعم"],
    "negativeWords": ["غير راضي", "مش راضي", "مشكلة", "مشكل", "سيء", "متأخر", "ناقص", "مكسور", "pas satisfait", "problème", "probleme", "non", "لا"],
    "thanksText": "شكراً لثقتكم بنا! يسعدنا أن الطلب وصلكم كما يجب.\nJustyol | جاستيول",
    "sorryText": "نأسف لتجربتكم. فريق خدمة العملاء سيتواصل معكم خلال 24 ساعة لحل المشكلة.\nJustyol | جاستيول",
    "ticketCategory": "Livraison",
}


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def ensure_doctype():
    """One row per question asked. Custom doctype, created on migrate."""
    try:
        if frappe.db.exists("DocType", DT):
            return
        frappe.get_doc({
            "doctype": "DocType", "name": DT, "module": "Core",
            "custom": 1, "naming_rule": "Autoincrement",
            "autoname": "autoincrement",
            "fields": [
                {"fieldname": "sales_order", "fieldtype": "Data", "label": "Order",
                 "in_standard_filter": 1},
                {"fieldname": "phone", "fieldtype": "Data", "label": "Phone"},
                {"fieldname": "city", "fieldtype": "Data", "label": "City"},
                {"fieldname": "customer_name", "fieldtype": "Data", "label": "Customer"},
                {"fieldname": "status", "fieldtype": "Select", "label": "Status",
                 "options": "asked\npositive\nnegative\nno_reply\nfailed\nskipped",
                 "in_standard_filter": 1},
                {"fieldname": "asked_at", "fieldtype": "Datetime", "label": "Asked"},
                {"fieldname": "wa_message", "fieldtype": "Data", "label": "WA Message"},
                {"fieldname": "wa_message_id", "fieldtype": "Data", "label": "WA Message Id"},
                {"fieldname": "reply", "fieldtype": "Small Text", "label": "Reply"},
                {"fieldname": "replied_at", "fieldtype": "Datetime", "label": "Replied"},
                {"fieldname": "ticket", "fieldtype": "Data", "label": "Ticket"},
                {"fieldname": "handled", "fieldtype": "Check", "label": "Handled"},
                {"fieldname": "handled_by", "fieldtype": "Data", "label": "Handled by"},
                {"fieldname": "error", "fieldtype": "Small Text", "label": "Error"},
            ],
            "permissions": [
                {"role": "System Manager", "read": 1, "write": 1, "create": 1},
            ],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        for col in ("sales_order", "phone", "status", "wa_message_id", "asked_at"):
            try:
                frappe.db.sql(f"ALTER TABLE `tab{DT}` ADD INDEX `lp_{col}` (`{col}`)")
            except Exception:
                pass
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "feedback.ensure_doctype")


def get_settings():
    raw = frappe.db.get_default(_SETTINGS_KEY)
    out = json.loads(json.dumps(_DEFAULTS))
    if raw:
        try:
            saved = json.loads(raw)
            if isinstance(saved, dict):
                out.update(saved)
        except Exception:
            pass
    return out


def _gate():
    from logistics_portal.api.shipments import _gate as g
    return g()


def _admin_gate():
    from logistics_portal.api.shipments import _admin_gate as g
    return g()


def _has_wa():
    return bool(frappe.db.exists("DocType", "WhatsApp Message"))


@frappe.whitelist()
def settings():
    _gate()
    s = get_settings()
    s["isAdmin"] = True
    try:
        _admin_gate()
    except Exception:
        s["isAdmin"] = False
    # Only approved templates can be sent; the lead picks from what Meta
    # has already accepted rather than typing a name that will 400.
    s["templates"] = []
    if frappe.db.exists("DocType", "WhatsApp Templates"):
        s["templates"] = frappe.db.sql(
            """SELECT name, template_name, language_code, LEFT(template, 160) AS body
               FROM `tabWhatsApp Templates` WHERE status = 'APPROVED'
               ORDER BY template_name""", as_dict=True)
    s["hasWa"] = _has_wa()
    return s


@frappe.whitelist(methods=["POST"])
def save_settings(payload=None):
    _admin_gate()
    if isinstance(payload, str):
        payload = json.loads(payload or "{}")
    cur = get_settings()
    for k in _DEFAULTS:
        if isinstance(payload, dict) and k in payload:
            cur[k] = payload[k]
    cur["enabled"] = bool(frappe.utils.sbool(cur.get("enabled"))) and bool(cur.get("template"))
    for k in ("delayHours", "maxAgeDays", "dailyCap", "phoneCooldownDays", "replyWindowH"):
        try:
            cur[k] = max(int(cur.get(k) or 0), 1)
        except Exception:
            cur[k] = _DEFAULTS[k]
    for k in ("positiveWords", "negativeWords"):
        cur[k] = [str(w).strip() for w in (cur.get(k) or []) if str(w).strip()]
    frappe.db.set_default(_SETTINGS_KEY, json.dumps(cur, ensure_ascii=False))
    frappe.db.commit()
    return {"ok": True, "settings": cur}


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def _digits(phone):
    """Morocco-only business: digits, last nine, country code in front."""
    d = re.sub(r"[^0-9]", "", phone or "")
    if len(d) < 9:
        return ""
    return "212" + d[-9:]


def _first_name(s):
    s = (s or "").strip()
    return s.split(" ")[0] if s else "عميلنا"


class _RefDoc:
    """What the template's placeholders read from.

    frappe_whatsapp (verified on the installed build) ignores any
    template_parameters we pass and rebuilds them from the template's
    `field_names` via `ref_doc.get_formatted(field)`, using
    `flags.custom_ref_doc` when set. So the customer-facing fields answer
    with what the message means — a first name, never a Customer link id —
    and anything else falls through to the order itself.
    """

    def __init__(self, order, name):
        self._so = None
        self._order = order
        self._name = name
        if order and frappe.db.exists("Sales Order", order):
            self._so = frappe.get_doc("Sales Order", order)

    def get_formatted(self, field):
        f = (field or "").strip()
        if f in ("customer", "customer_name", "first_name", "name_first"):
            return _first_name(self._name)
        if f in ("name", "shopify_order_number"):
            return self._order or ""
        if self._so is not None:
            try:
                return self._so.get_formatted(f)
            except Exception:
                return str(self._so.get(f) or "")
        return ""

    def get(self, field, default=None):
        return self.get_formatted(field) or default


def _send_template(cfg, phone, name, order):
    """Insert the outgoing message; frappe_whatsapp posts it to Meta in
    before_insert and stores the wamid. Returns (docname, message_id)."""
    doc = frappe.get_doc({
        "doctype": "WhatsApp Message", "type": "Outgoing",
        "message_type": "Template", "use_template": 1,
        "template": cfg["template"],
        "template_parameters": json.dumps([_first_name(name)], ensure_ascii=False),
        "to": "+" + phone, "content_type": "text",
        "reference_doctype": "Sales Order" if order else None,
        "reference_name": order,
    })
    doc.flags.custom_ref_doc = _RefDoc(order, name)
    doc.insert(ignore_permissions=True)
    return doc.name, doc.message_id or ""


def _send_text(phone, text, order=None):
    doc = frappe.get_doc({
        "doctype": "WhatsApp Message", "type": "Outgoing",
        "message_type": "Manual", "content_type": "text",
        "message": text, "to": "+" + phone,
        "reference_doctype": "Sales Order" if order else None,
        "reference_name": order,
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _in_window(cfg):
    from logistics_portal.api import clock
    now = clock.floor_now()
    mins = now.hour * 60 + now.minute
    def hm(s):
        try:
            h, m = str(s).split(":")[:2]
            return int(h) * 60 + int(m)
        except Exception:
            return 0
    return hm(cfg.get("windowStart") or "10:00") <= mins < hm(cfg.get("windowEnd") or "20:00")


def _asked_today():
    from logistics_portal.api import clock
    lo, _hi = clock.day_bounds(clock.floor_now().date())
    return frappe.db.sql(
        f"SELECT COUNT(*) FROM `tab{DT}` WHERE status <> 'failed' AND status <> 'skipped' AND asked_at >= %s",
        (lo,))[0][0]


def run_ask():
    """Hourly: ask the customers whose parcel arrived about a day ago."""
    try:
        cfg = get_settings()
        if not cfg.get("enabled") or not cfg.get("template") or not _has_wa():
            return
        if not frappe.db.exists("DocType", DT):
            return
        if not _in_window(cfg):
            return
        room = int(cfg["dailyCap"]) - int(_asked_today())
        if room <= 0:
            return
        # Two workers passing NOT EXISTS together would ask twice.
        lock = frappe.cache()
        if lock.get_value("lp_feedback_ask_running"):
            return
        lock.set_value("lp_feedback_ask_running", "1", expires_in_sec=600)
        now = now_datetime()
        rows = frappe.db.sql(
            f"""SELECT so.name, so.customer_name, so.custom_delivered_at AS at,
                       COALESCE(NULLIF(so.custom_customer_phone, ''), so.custom_shipping_phone) AS phone,
                       COALESCE(NULLIF(so.custom_shipping_city, ''), '') AS city
                FROM `tabSales Order` so
                WHERE so.company = %(co)s AND so.docstatus = 1
                  AND so.custom_track_shipment_status = 'Delivered'
                  AND so.custom_delivered_at BETWEEN %(lo)s AND %(hi)s
                  AND NOT EXISTS (SELECT 1 FROM `tab{DT}` f WHERE f.sales_order = so.name)
                ORDER BY so.custom_delivered_at
                LIMIT %(lim)s""",
            {"co": _CO, "lo": add_to_date(now, days=-int(cfg["maxAgeDays"])),
             "hi": add_to_date(now, hours=-int(cfg["delayHours"])),
             "lim": min(room, 150)}, as_dict=True)
        if not rows:
            return
        cooldown = add_to_date(now, days=-int(cfg["phoneCooldownDays"]))
        for r in rows:
            phone = _digits(r.phone)
            if not phone:
                _record(r, phone, "failed", error="no phone")
                continue
            # One question per customer per month, whatever they ordered —
            # counting only questions that actually went out.
            if frappe.db.sql(f"""SELECT 1 FROM `tab{DT}` WHERE phone = %s AND asked_at >= %s
                                 AND status IN ('asked', 'positive', 'negative', 'no_reply') LIMIT 1""",
                             (phone, cooldown)):
                _record(r, phone, "skipped", error="cooldown: asked recently")
                frappe.db.commit()
                continue
            wa_name = wamid = None
            err = None
            try:
                wa_name, wamid = _send_template(cfg, phone, r.customer_name, r.name)
            except Exception as e:
                # frappe_whatsapp throws when Meta rejects; keep the row so
                # the order is not retried every hour, and show the reason.
                err = str(e)[:300]
            # The record is written no matter what: a sent message with no
            # row would be sent again next hour.
            try:
                if err:
                    _record(r, phone, "failed", error=err)
                else:
                    _record(r, phone, "asked", wa_name=wa_name, wamid=wamid)
                frappe.db.commit()
            except Exception:
                frappe.db.rollback()
                frappe.log_error(frappe.get_traceback()[:2000], "feedback.run_ask.record")
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "feedback.run_ask")
    finally:
        try:
            frappe.cache().delete_value("lp_feedback_ask_running")
        except Exception:
            pass


def _record(r, phone, status, wa_name=None, wamid=None, error=None):
    frappe.get_doc({
        "doctype": DT, "sales_order": r.name, "phone": phone,
        "city": (r.city or "")[:80], "customer_name": (r.customer_name or "")[:120],
        "status": status, "asked_at": now_datetime(),
        "wa_message": wa_name, "wa_message_id": wamid, "error": error,
    }).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Phone key: an indexed way to find a conversation
# ---------------------------------------------------------------------------

def _phone_key(s):
    d = re.sub(r"[^0-9]", "", s or "")
    return d[-9:] if len(d) >= 9 else ""


def stamp_phone_key(doc, method=None):
    """doc_events hook on WhatsApp Message: the counterpart's last nine digits."""
    try:
        if not frappe.db.has_column("WhatsApp Message", "custom_lp_phone_key"):
            return
        key = _phone_key(doc.get("from") if doc.get("type") == "Incoming" else doc.get("to"))
        if key and doc.get("custom_lp_phone_key") != key:
            frappe.db.set_value("WhatsApp Message", doc.name, "custom_lp_phone_key", key,
                                update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:1000], "feedback.stamp_phone_key")


def backfill_phone_keys(days=90):
    """after_migrate, idempotent: key the recent history once, then index it.
    Older rows stay unkeyed — nothing looks further back than the reply
    window, and the CS inbox reads seven days."""
    try:
        if not _has_wa():
            return
        from logistics_portal.install import ensure_cs_fields
        ensure_cs_fields()
        if not frappe.db.has_column("WhatsApp Message", "custom_lp_phone_key"):
            return
        since = add_to_date(now_datetime(), days=-int(days))
        # In day-sized bites so the migrate never holds one long lock.
        for back in range(int(days), -1, -1):
            lo = add_to_date(now_datetime(), days=-back - 1)
            hi = add_to_date(now_datetime(), days=-back)
            if hi < since:
                continue
            frappe.db.sql(
                """UPDATE `tabWhatsApp Message`
                   SET custom_lp_phone_key = RIGHT(REGEXP_REPLACE(
                         CASE WHEN type = 'Incoming' THEN `from` ELSE `to` END, '[^0-9]', ''), 9)
                   WHERE creation >= %s AND creation < %s
                     AND (custom_lp_phone_key IS NULL OR custom_lp_phone_key = '')""",
                (lo, hi))
            frappe.db.commit()
        try:
            frappe.db.sql("ALTER TABLE `tabWhatsApp Message` ADD INDEX `lp_wa_phone_key` (`custom_lp_phone_key`)")
            frappe.db.commit()
        except Exception:
            pass
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "feedback.backfill_phone_keys")


# ---------------------------------------------------------------------------
# Reading the answer
# ---------------------------------------------------------------------------

# \w already covers Arabic letters; listing the Arabic block here would glue
# the Arabic comma "\u060C" onto the word before it.
_TOKEN = re.compile(r"[^\w]+")


def _tokens(s):
    return [x for x in _TOKEN.split((s or "").strip().lower()) if x]


def _has_phrase(tokens, phrase):
    """Whole-word match: "لا" must not fire inside "السلام", nor "non" inside
    "personne". Multi-word phrases match as consecutive tokens."""
    p = _tokens(phrase)
    if not p:
        return False
    n = len(p)
    return any(tokens[i:i + n] == p for i in range(len(tokens) - n + 1))


def _verdict(text, cfg):
    raw = (text or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"[1-5]", raw):
        return "positive" if int(raw) >= 4 else "negative"
    toks = _tokens(raw)
    # Negative first: "غير راضي" contains "راضي".
    for w in cfg.get("negativeWords") or []:
        if _has_phrase(toks, w) or (w.strip() and not _tokens(w) and w.strip() in raw):
            return "negative"
    for w in cfg.get("positiveWords") or []:
        if _has_phrase(toks, w) or (w.strip() and not _tokens(w) and w.strip() in raw):
            return "positive"
    return None


def run_replies():
    """Every 15 minutes: match replies to open questions, route them."""
    try:
        cfg = get_settings()
        if not _has_wa() or not frappe.db.exists("DocType", DT):
            return
        now = now_datetime()
        window = add_to_date(now, hours=-int(cfg["replyWindowH"]))
        open_rows = frappe.db.sql(
            f"""SELECT name, sales_order, phone, city, customer_name, asked_at, wa_message_id
                FROM `tab{DT}` WHERE status = 'asked' AND asked_at >= %s ORDER BY asked_at""",
            (window,), as_dict=True)
        if open_rows:
            by_wamid = {r.wa_message_id: r for r in open_rows if r.wa_message_id}
            by_phone = {}
            for r in open_rows:
                by_phone.setdefault(r.phone, []).append(r)
            oldest = min(r.asked_at for r in open_rows)
            phones = list(by_phone)
            ph = ", ".join(["%s"] * len(phones))
            msgs = frappe.db.sql(
                f"""SELECT name, `from`, message, content_type, reply_to_message_id, creation
                    FROM `tabWhatsApp Message`
                    WHERE type = 'Incoming' AND creation >= %s
                      AND content_type IN ('button', 'interactive', 'text')
                      AND COALESCE(custom_lp_handled, 0) = 0
                      AND custom_lp_phone_key IN ({ph})
                    ORDER BY creation""",
                tuple([oldest] + [p[-9:] for p in phones]), as_dict=True)
            # Anything ELSE we sent a phone after the question (a confirmation
            # for a new order, a reminder) makes a typed reply ambiguous: it is
            # then left to the CS inbox rather than guessed.
            later_out = {}
            for to, at in frappe.db.sql(
                    """SELECT `to`, MAX(creation) FROM `tabWhatsApp Message`
                       WHERE type = 'Outgoing' AND creation >= %s
                         AND (reference_doctype IS NULL OR reference_doctype <> 'Sales Order'
                              OR reference_name NOT IN (SELECT sales_order FROM `tab{DT}` WHERE status = 'asked'))
                       GROUP BY `to`""".replace("{DT}", DT), (oldest,)):
                later_out[_digits(to)] = at
            done = set()
            for m in msgs:
                row = by_wamid.get(m.reply_to_message_id)
                if not row:
                    # Buttons always carry the wamid of what they answer; a
                    # button without ours belongs to another conversation.
                    if m.content_type != "text":
                        continue
                    # A typed answer: the newest open question for that phone,
                    # asked before it, and nothing else of ours in between.
                    key = _digits(m["from"])
                    cands = [r for r in by_phone.get(key, []) if r.asked_at <= m.creation]
                    row = cands[-1] if cands else None
                    if row and (m.creation - row.asked_at).total_seconds() > 48 * 3600:
                        continue
                    if row and later_out.get(key) and row.asked_at < later_out[key] < m.creation:
                        continue
                if not row or row.name in done:
                    continue
                v = _verdict(m.message, cfg)
                if not v:
                    continue  # unrelated chatter; the CS inbox still sees it
                done.add(row.name)
                _route(row, v, m, cfg)
                frappe.db.commit()
        # Silence past the window is an answer of its own.
        frappe.db.sql(
            f"UPDATE `tab{DT}` SET status = 'no_reply' WHERE status = 'asked' AND asked_at < %s",
            (window,))
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "feedback.run_replies")


def _route(row, verdict, msg, cfg):
    phone = row.phone
    ticket = None
    frappe.db.set_value(DT, row.name, {
        "status": verdict, "reply": (msg.message or "")[:500],
        "replied_at": msg.creation,
    }, update_modified=False)
    if verdict == "negative":
        try:
            ticket = _open_ticket(row, msg, cfg)
        except Exception as e:
            frappe.db.set_value(DT, row.name, "error", ("ticket: " + str(e))[:300],
                                update_modified=False)
        if ticket:
            frappe.db.set_value(DT, row.name, "ticket", ticket, update_modified=False)
    try:
        text = cfg.get("thanksText") if verdict == "positive" else cfg.get("sorryText")
        if text:
            _send_text(phone, text, row.sales_order)
    except Exception as e:
        frappe.db.set_value(DT, row.name, "error", ("reply: " + str(e))[:300],
                            update_modified=False)
    # The reply is consumed here; it must not surface again in the CS inbox.
    try:
        frappe.db.set_value("WhatsApp Message", msg.name, "custom_lp_handled", 1,
                            update_modified=False)
    except Exception:
        pass


def _open_ticket(row, msg, cfg):
    """An unhappy customer is a ticket with the reply attached, so a human
    calls with the context already on screen. Same shape tickets.create_ticket
    writes, without its session gate (this runs from the scheduler)."""
    if not frappe.db.exists("DocType", "Issue"):
        return None
    subject = f"Delivery feedback: {row.sales_order} — {(msg.message or '')[:60]}"
    doc = frappe.get_doc({
        "doctype": "Issue", "company": _CO,
        "subject": subject[:140],
        "description": f"Customer replied to the post-delivery question:\n\n"
                       f"{msg.message or ''}\n\nOrder {row.sales_order} · "
                       f"{row.customer_name or ''} · {row.city or ''}",
        "custom_phone": row.phone, "custom_order": row.sales_order,
        "custom_category": cfg.get("ticketCategory") or "",
        "custom_channel": "whatsapp", "raised_by": "Administrator",
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    try:
        doc.add_comment("Comment", f"CS: create — delivery feedback · automatic")
    except Exception:
        pass
    return doc.name


# ---------------------------------------------------------------------------
# The screen
# ---------------------------------------------------------------------------

@frappe.whitelist()
def board(days=14):
    _gate()
    days = min(max(int(days or 14), 1), 90)
    out = {"days": days, "ready": bool(frappe.db.exists("DocType", DT)) and _has_wa(),
           "enabled": bool(get_settings().get("enabled"))}
    if not out["ready"]:
        out.update({"counts": {}, "series": [], "negatives": [], "cities": [], "recent": []})
        return out
    since = add_to_date(now_datetime(), days=-days)
    counts = {"asked": 0, "positive": 0, "negative": 0, "no_reply": 0, "failed": 0, "skipped": 0}
    for st, n in frappe.db.sql(
            f"SELECT status, COUNT(*) FROM `tab{DT}` WHERE asked_at >= %s GROUP BY status", (since,)):
        counts[st] = int(n)
    sent = counts["asked"] + counts["positive"] + counts["negative"] + counts["no_reply"]
    answered = counts["positive"] + counts["negative"]
    # A question still inside its reply window is not a silence yet.
    settled = sent - counts["asked"]
    out["counts"] = counts
    out["sent"] = sent
    out["responseRate"] = round(100.0 * answered / settled, 1) if settled else None
    out["satisfaction"] = round(100.0 * counts["positive"] / answered, 1) if answered else None
    out["openNegatives"] = int(frappe.db.sql(
        f"SELECT COUNT(*) FROM `tab{DT}` WHERE status = 'negative' AND COALESCE(handled, 0) = 0")[0][0])

    from logistics_portal.api import clock
    day = clock.sql_local("asked_at")
    out["series"] = [{"d": str(d), "sent": int(s), "pos": int(p), "neg": int(n)} for d, s, p, n in
                     frappe.db.sql(
                         f"""SELECT {day} d, COUNT(*), SUM(status = 'positive'), SUM(status = 'negative')
                             FROM `tab{DT}` WHERE asked_at >= %s AND status NOT IN ('failed', 'skipped')
                             GROUP BY {day} ORDER BY d""", (since,))]
    out["negatives"] = frappe.db.sql(
        f"""SELECT name, sales_order, customer_name, city, phone, reply, replied_at, ticket,
                   COALESCE(handled, 0) AS handled, handled_by
            FROM `tab{DT}` WHERE status = 'negative'
              AND (COALESCE(handled, 0) = 0 OR asked_at >= %s)
            ORDER BY handled, replied_at DESC LIMIT 200""", (since,), as_dict=True)
    for r in out["negatives"]:
        r["replied_at"] = str(r["replied_at"] or "")[:16]
    out["cities"] = frappe.db.sql(
        f"""SELECT city, COUNT(*) n, SUM(status = 'positive') pos, SUM(status = 'negative') neg
            FROM `tab{DT}` WHERE asked_at >= %s AND status IN ('positive', 'negative') AND city <> ''
            GROUP BY city HAVING n >= 5 ORDER BY neg / n DESC, n DESC LIMIT 20""", (since,), as_dict=True)
    out["recent"] = frappe.db.sql(
        f"""SELECT sales_order, customer_name, city, status, reply, replied_at
            FROM `tab{DT}` WHERE status IN ('positive', 'negative') ORDER BY replied_at DESC LIMIT 30""",
        as_dict=True)
    for r in out["recent"]:
        r["replied_at"] = str(r["replied_at"] or "")[:16]
    out["failedRecent"] = frappe.db.sql(
        f"""SELECT sales_order, error FROM `tab{DT}` WHERE status = 'failed' AND asked_at >= %s
            ORDER BY asked_at DESC LIMIT 5""", (since,), as_dict=True)
    return out


@frappe.whitelist(methods=["POST"])
def mark_handled(name):
    _gate()
    if not frappe.db.exists(DT, name):
        frappe.throw("lp:unknownRow")
    frappe.db.set_value(DT, name, {"handled": 1, "handled_by": frappe.session.user},
                        update_modified=False)
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def test_send(phone):
    """Lead-only: send the configured question to one number, so the copy and
    the buttons are seen on a real phone before the switch is flipped."""
    _admin_gate()
    cfg = get_settings()
    if not cfg.get("template"):
        frappe.throw("lp:pickTemplate")
    p = _digits(phone)
    if not p:
        frappe.throw("lp:badPhone")
    name, wamid = _send_template(cfg, p, "Test", None)
    frappe.db.commit()
    return {"ok": True, "message": name, "wamid": wamid}
