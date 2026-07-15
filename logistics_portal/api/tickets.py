"""Contact Center — Lane 3: customer service tickets.

Rides the stock ERPNext Issue doctype (statuses Open / Replied / On Hold /
Resolved / Closed) instead of inventing a schema — someone already tried
Issues from the desk in January (8 tickets) and gave up on the UX.

Intake:
  WHATSAPP INBOX  the store's automation ships a "contact customer service"
                  button, and customers press it — 5,661 incoming messages a
                  week land in tabWhatsApp Message with nobody watching. The
                  inbox surfaces free-text messages + that button, grouped by
                  phone, matched to the customer's latest order; one tap turns
                  a conversation into a ticket (and marks it handled).
  MANUAL          a call comes in, or an agent spots a problem mid-call in
                  lanes 1/2 — create the ticket from the same workspace.

Section pattern: settings (SLA hours, categories, admins) + reports gated to
the portal manager or the section's own admins.
"""

import frappe
from frappe.utils import add_to_date, now_datetime

_OPEN_STATUSES = ("Open", "Replied", "On Hold")


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("confirmation", "manager"):
        frappe.throw("Not authorized for the tickets workspace.", frappe.PermissionError)
    return role


# ── section settings + admins ──────────────────────────────────────────────
_CS_KEY = "lp_cs_settings"
_CS_DEFAULTS = {
    "firstResponseH": 4,
    "resolutionH": 48,
    "categories": ["Produit défectueux", "Colis incomplet", "Retard de livraison",
                   "Demande de remboursement", "Échange", "Question produit", "Autre"],
    "admins": [],
}


def _cs_settings():
    import json as _json
    raw = frappe.db.get_default(_CS_KEY)
    out = dict(_CS_DEFAULTS)
    if raw:
        try:
            saved = _json.loads(raw)
            if isinstance(saved, dict):
                out.update({k: saved[k] for k in _CS_DEFAULTS if k in saved})
        except Exception:
            pass
    return out


def _is_cs_admin():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) == "manager":
        return True
    return frappe.session.user in _cs_settings().get("admins", [])


@frappe.whitelist()
def cs_settings():
    _gate()
    return {**_cs_settings(), "canEdit": _is_cs_admin()}


@frappe.whitelist()
def save_cs_settings(settings=None):
    import json as _json
    _gate()
    if not _is_cs_admin():
        frappe.throw("Only the portal manager or a CS section admin can change "
                     "these settings.", frappe.PermissionError)
    if isinstance(settings, str):
        settings = _json.loads(settings)
    settings = settings or {}
    out = dict(_cs_settings())
    for k in ("firstResponseH", "resolutionH"):
        if k in settings:
            v = int(settings[k])
            if not (1 <= v <= 720):
                frappe.throw(f"{k} must be between 1 and 720 hours.")
            out[k] = v
    if "categories" in settings:
        cats = [str(c).strip()[:60] for c in (settings["categories"] or []) if str(c).strip()]
        if not cats:
            frappe.throw("Keep at least one category.")
        out["categories"] = cats[:20]
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
    frappe.db.set_default(_CS_KEY, _json.dumps(out))
    frappe.db.commit()
    return {"ok": True, **out}


# ── the board ───────────────────────────────────────────────────────────────
def _has_wa():
    return bool(frappe.db.exists("DocType", "WhatsApp Message"))


def _match_order(phone):
    """The customer's latest order by the trailing 9 digits of their phone."""
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())[-9:]
    if len(digits) < 9:
        return None
    row = frappe.db.sql(
        """SELECT name, customer_name FROM `tabSales Order`
           WHERE docstatus = 1 AND (custom_customer_phone LIKE %(p)s
                 OR custom_shipping_phone LIKE %(p)s)
           ORDER BY creation DESC LIMIT 1""",
        {"p": f"%{digits}"}, as_dict=True)
    return row[0] if row else None


@frappe.whitelist()
def board(tab="inbox", days=7, q="", limit=30, offset=0):
    """inbox (unhandled WhatsApp conversations) + the ticket queues."""
    _gate()
    if tab not in ("inbox", "open", "mine", "resolved"):
        tab = "inbox"
    days = min(max(int(days or 7), 1), 30)
    limit = min(max(int(limit or 30), 1), 100)
    offset = max(int(offset or 0), 0)
    s = _cs_settings()
    now = now_datetime()

    counts = {"inbox": 0, "open": 0, "mine": 0, "resolved": 0}
    if _has_wa():
        counts["inbox"] = int(frappe.db.sql(
            """SELECT COUNT(DISTINCT wm.`from`) FROM `tabWhatsApp Message` wm
               WHERE wm.type = 'Incoming' AND COALESCE(wm.custom_lp_handled, 0) = 0
                 AND wm.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)
                 AND (wm.content_type = 'text'
                      OR (wm.content_type = 'button' AND wm.message LIKE %(csbtn)s))""",
            {"days": days, "csbtn": "%خدمة العملاء%"})[0][0])
    counts["open"] = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabIssue`
           WHERE status IN %(sts)s""", {"sts": _OPEN_STATUSES})[0][0])
    counts["mine"] = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabIssue`
           WHERE status IN %(sts)s AND custom_agent = %(me)s""",
        {"sts": _OPEN_STATUSES, "me": frappe.session.user})[0][0])
    counts["resolved"] = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabIssue`
           WHERE status IN ('Resolved', 'Closed')
             AND modified >= DATE_SUB(NOW(), INTERVAL 7 DAY)""")[0][0])

    rows, total = [], 0
    if tab == "inbox" and _has_wa():
        vals = {"days": days, "limit": limit, "offset": offset,
                "csbtn": "%خدمة العملاء%"}
        conds = """wm.type = 'Incoming' AND COALESCE(wm.custom_lp_handled, 0) = 0
                 AND wm.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)
                 AND (wm.content_type = 'text'
                      OR (wm.content_type = 'button' AND wm.message LIKE %(csbtn)s))"""
        total = counts["inbox"]
        convs = frappe.db.sql(
            f"""SELECT wm.`from` AS phone, MAX(wm.creation) AS last_at,
                       COUNT(*) AS n,
                       SUBSTRING_INDEX(GROUP_CONCAT(wm.message ORDER BY wm.creation DESC
                                       SEPARATOR '\\n'), '\\n', 1) AS last_msg
                FROM `tabWhatsApp Message` wm
                WHERE {conds}
                GROUP BY wm.`from`
                ORDER BY last_at DESC
                LIMIT %(limit)s OFFSET %(offset)s""", vals, as_dict=True)
        for c in convs:
            so = _match_order(c.phone)
            rows.append({
                "id": c.phone, "phone": c.phone,
                "message": (c.last_msg or "")[:140], "msgCount": int(c.n or 0),
                "lastAt": str(c.last_at)[:16],
                "order": so.name if so else "", "customer": so.customer_name if so else "",
            })
    elif tab != "inbox":
        conds = ["1=1"]
        vals = {"limit": limit, "offset": offset, "me": frappe.session.user}
        if tab == "open":
            conds.append("i.status IN ('Open', 'Replied', 'On Hold')")
        elif tab == "mine":
            conds.append("i.status IN ('Open', 'Replied', 'On Hold')")
            conds.append("i.custom_agent = %(me)s")
        else:
            conds.append("i.status IN ('Resolved', 'Closed')")
            conds.append("i.modified >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
        if q and str(q).strip():
            vals["q"] = f"%{str(q).strip()}%"
            conds.append("""(i.subject LIKE %(q)s OR i.custom_phone LIKE %(q)s
                            OR i.custom_order LIKE %(q)s OR i.name LIKE %(q)s)""")
        where = " AND ".join(conds)
        total = frappe.db.sql(f"SELECT COUNT(*) FROM `tabIssue` i WHERE {where}", vals)[0][0]
        data = frappe.db.sql(
            f"""SELECT i.name, i.subject, i.status, i.custom_phone AS phone,
                       i.custom_order AS so_name, i.custom_category AS category,
                       i.custom_channel AS channel, i.custom_agent AS agent,
                       i.opening_date, i.creation, i.first_responded_on,
                       TIMESTAMPDIFF(HOUR, i.creation, NOW()) AS age_h
                FROM `tabIssue` i WHERE {where}
                ORDER BY i.creation {'DESC' if tab == 'resolved' else ''}
                LIMIT %(limit)s OFFSET %(offset)s""", vals, as_dict=True)
        for r in data:
            resp_due = add_to_date(r.creation, hours=s["firstResponseH"])
            reso_due = add_to_date(r.creation, hours=s["resolutionH"])
            rows.append({
                "id": r.name, "subject": r.subject or "", "status": r.status or "Open",
                "phone": (r.phone or "").strip(), "order": r.so_name or "",
                "category": r.category or "", "channel": r.channel or "",
                "agent": (r.agent or "").split("@")[0],
                "mine": (r.agent or "") == frappe.session.user,
                "ageH": int(r.age_h or 0),
                "respBreached": bool(tab != "resolved" and not r.first_responded_on
                                     and str(resp_due) <= str(now)),
                "resoBreached": bool(tab != "resolved" and str(reso_due) <= str(now)),
            })

    today = str(now)[:10]
    mine_today = {"resolve": 0, "reply": 0, "create": 0}
    for r in frappe.db.sql(
            """SELECT c.content, COUNT(*) n FROM `tabComment` c
               WHERE c.reference_doctype = 'Issue' AND c.owner = %s
                 AND c.creation >= %s AND c.content LIKE 'CS: %%'
               GROUP BY c.content""",
            (frappe.session.user, f"{today} 00:00:00"), as_dict=True):
        for k in mine_today:
            if r.content.startswith(f"CS: {k}"):
                mine_today[k] += int(r.n or 0)

    return {
        "tab": tab, "counts": counts, "total": int(total or 0), "rows": rows,
        "mine": mine_today,
        "categories": s.get("categories", []),
        "hasWhatsapp": _has_wa(),
        "serverNow": str(now)[:19],
    }


@frappe.whitelist()
def create_ticket(subject, phone=None, order=None, category=None,
                  description=None, channel="manual", wa_phone=None):
    """New ticket. When `wa_phone` is set the conversation's unhandled inbox
    messages are marked handled (the inbox row turns into this ticket)."""
    _gate()
    subject = (subject or "").strip()
    if not subject:
        frappe.throw("A ticket needs a subject.")
    doc = frappe.get_doc({
        "doctype": "Issue",
        "subject": subject[:140],
        "description": (description or "").strip() or subject,
        "custom_phone": (phone or "").strip(),
        "custom_order": (order or "").strip(),
        "custom_category": (category or "").strip(),
        "custom_channel": channel if channel in ("whatsapp", "phone", "manual") else "manual",
        "custom_agent": frappe.session.user,
        "raised_by": frappe.session.user,
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    doc.add_comment("Comment", f"CS: create — {subject[:80]} · by {frappe.session.user}")
    if wa_phone and _has_wa():
        frappe.db.sql(
            """UPDATE `tabWhatsApp Message` SET custom_lp_handled = 1
               WHERE type = 'Incoming' AND `from` = %s
                 AND COALESCE(custom_lp_handled, 0) = 0""", (wa_phone,))
    frappe.db.commit()
    return {"ok": True, "ticket": doc.name}


@frappe.whitelist()
def wa_dismiss(phone):
    """The conversation needs no ticket (already answered / automation noise)."""
    _gate()
    if not _has_wa():
        frappe.throw("WhatsApp inbox is not available on this site.")
    frappe.db.sql(
        """UPDATE `tabWhatsApp Message` SET custom_lp_handled = 1
           WHERE type = 'Incoming' AND `from` = %s
             AND COALESCE(custom_lp_handled, 0) = 0""", ((phone or "").strip(),))
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def act(name, action, note=None):
    """Ticket lifecycle: take / reply / hold / resolve / reopen."""
    _gate()
    name = (name or "").strip()
    note = (note or "").strip()
    if not frappe.db.exists("Issue", name):
        frappe.throw("Unknown ticket.")
    if action not in ("take", "reply", "hold", "resolve", "reopen"):
        frappe.throw("Unknown action.")
    if action in ("reply", "resolve") and not note:
        frappe.throw("This action needs a note (what was said / how it was fixed).")

    doc = frappe.get_doc("Issue", name)
    updates = {"custom_agent": frappe.session.user}
    if action == "reply":
        updates["status"] = "Replied"
        if not doc.first_responded_on:
            updates["first_responded_on"] = now_datetime()
    elif action == "hold":
        updates["status"] = "On Hold"
    elif action == "resolve":
        updates["status"] = "Resolved"
        if not doc.first_responded_on:
            updates["first_responded_on"] = now_datetime()
    elif action == "reopen":
        updates["status"] = "Open"
    for k, v in updates.items():
        doc.db_set(k, v, update_modified=True)
    doc.add_comment("Comment",
                    f"CS: {action}" + (f" — {note}" if note else "")
                    + f" · by {frappe.session.user}")
    frappe.db.commit()
    return {"ok": True, "ticket": name, "action": action,
            "status": updates.get("status", doc.status)}


@frappe.whitelist()
def report(days=7):
    """CS-section report: per-agent volume, avg first-response and resolution
    hours, category mix, opened-vs-resolved per day."""
    _gate()
    if not _is_cs_admin():
        frappe.throw("Only the portal manager or a section admin can open the "
                     "section report.", frappe.PermissionError)
    days = min(max(int(days or 7), 1), 90)
    since = f"DATE_SUB(NOW(), INTERVAL {days} DAY)"

    agents = frappe.db.sql(
        f"""SELECT COALESCE(NULLIF(i.custom_agent, ''), '—') AS user,
                   COUNT(*) AS handled,
                   SUM(i.status IN ('Resolved', 'Closed')) AS resolved,
                   ROUND(AVG(CASE WHEN i.first_responded_on IS NOT NULL
                       THEN TIMESTAMPDIFF(MINUTE, i.creation, i.first_responded_on) END) / 60, 1)
                       AS avg_first_h,
                   ROUND(AVG(CASE WHEN i.status IN ('Resolved', 'Closed')
                       THEN TIMESTAMPDIFF(MINUTE, i.creation, i.modified) END) / 60, 1)
                       AS avg_reso_h
            FROM `tabIssue` i
            WHERE i.creation >= {since}
            GROUP BY user ORDER BY handled DESC""", as_dict=True)

    cats = frappe.db.sql(
        f"""SELECT COALESCE(NULLIF(custom_category, ''), '(none)') AS cat, COUNT(*) n
            FROM `tabIssue` WHERE creation >= {since}
            GROUP BY cat ORDER BY n DESC LIMIT 12""", as_dict=True)

    funnel = frappe.db.sql(
        f"""SELECT d, SUM(opened) opened, SUM(resolved) resolved FROM (
              SELECT DATE(creation) d, 1 opened, 0 resolved FROM `tabIssue`
                WHERE creation >= {since}
              UNION ALL
              SELECT DATE(modified) d, 0 opened, 1 resolved FROM `tabIssue`
                WHERE status IN ('Resolved', 'Closed') AND modified >= {since}
            ) x GROUP BY d ORDER BY d""", as_dict=True)

    return {
        "days": days,
        "agents": [{
            "agent": a.user.split("@")[0], "user": a.user,
            "handled": int(a.handled or 0), "resolved": int(a.resolved or 0),
            "avgFirstH": float(a.avg_first_h or 0), "avgResoH": float(a.avg_reso_h or 0),
            "resolveRate": round(int(a.resolved or 0) * 100.0 / max(1, int(a.handled or 0)), 1),
        } for a in agents],
        "categories": [{"category": c.cat, "n": int(c.n or 0)} for c in cats],
        "funnel": [{"date": str(f.d), "opened": int(f.opened or 0),
                    "resolved": int(f.resolved or 0)} for f in funnel],
    }
