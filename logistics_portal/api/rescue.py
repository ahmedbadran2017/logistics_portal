"""Contact Center — Lane 2: post-ship rescue.

The parcel left the building and the delivery is failing (carrier exception,
failed attempt, customer unreachable, or silently stuck in transit). The same
contact-center agents call the CUSTOMER and decide: redeliver, reship, request
the return, or cancel — every decision recorded on both the parcel (Delivery
Note exception trail) and the order. Shares the confirmation lane's contact
fields (attempt counter, next-call time) — one engine, two lanes.

Production workload at build time: 3,678 untriaged Delivery Exceptions +
1,166 Failed Attempts + 658 parcels silently stuck in transit >7 days.
"""

import frappe
from frappe.utils import add_to_date, now_datetime

TABS = ("exceptions", "failed", "notdelivered", "stale", "backlog")
_DN_TRACK = {"exceptions": "Delivery Exception", "failed": "Failed Attempt"}
_STALE_TRACKS = ("Out For Delivery", "In Transit", "Pending")
_STALE_DAYS = 7
# Everything the working queues track, for the older-than-window backlog.
_BACKLOG_TRACKS = ("Delivery Exception", "Failed Attempt") + _STALE_TRACKS


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("confirmation", "manager"):
        frappe.throw("Not authorized for the rescue workspace.", frappe.PermissionError)
    return role


# ── section settings + admins (same pattern as the confirmation section) ──
_RS_KEY = "lp_rescue_settings"
_RS_DEFAULTS = {
    "retryDna": 6,
    "slaTriageH": 24,   # a failing parcel untouched longer than this is late
    "reasons": ["Client injoignable", "Refuse le colis", "Adresse introuvable",
                "Reporté par le client", "Annulé par le client"],
    "admins": [],
}


def _rs_settings():
    import json as _json
    raw = frappe.db.get_default(_RS_KEY)
    out = dict(_RS_DEFAULTS)
    if raw:
        try:
            saved = _json.loads(raw)
            if isinstance(saved, dict):
                out.update({k: saved[k] for k in _RS_DEFAULTS if k in saved})
        except Exception:
            pass
    return out


def _is_rs_admin():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) == "manager":
        return True
    return frappe.session.user in _rs_settings().get("admins", [])


@frappe.whitelist()
def rs_settings():
    _gate()
    return {**_rs_settings(), "canEdit": _is_rs_admin()}


@frappe.whitelist()
def save_rs_settings(settings=None):
    import json as _json
    _gate()
    if not _is_rs_admin():
        frappe.throw("Only the portal manager or a rescue section admin can "
                     "change these settings.", frappe.PermissionError)
    if isinstance(settings, str):
        settings = _json.loads(settings)
    settings = settings or {}
    out = dict(_rs_settings())
    for k in ("retryDna", "slaTriageH"):
        if k in settings:
            v = int(settings[k])
            if not (1 <= v <= 168):
                frappe.throw(f"{k} must be between 1 and 168 hours.")
            out[k] = v
    if "reasons" in settings:
        reasons = [str(r).strip()[:60] for r in (settings["reasons"] or []) if str(r).strip()]
        if not reasons:
            frappe.throw("Keep at least one reason.")
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
    frappe.db.set_default(_RS_KEY, _json.dumps(out))
    frappe.db.commit()
    return {"ok": True, **out}


# ── the board ───────────────────────────────────────────────────────────────
_DN_SELECT = """
    SELECT dn.name AS dn, dn.customer_name AS customer, dn.grand_total AS total,
           dn.custom_awb AS awb, dn.custom_track_shipment_status AS track,
           so.name AS so_name,
           COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
           so.custom_shipping_city AS city,
           COALESCE(so.custom_call_attempts, 0) AS attempts,
           so.custom_next_call_at AS next_call,
           DATEDIFF(CURDATE(), dn.posting_date) AS age_d
    FROM `tabDelivery Note` dn
    LEFT JOIN (SELECT dni.parent AS p, MAX(dni.against_sales_order) AS so_n
               FROM `tabDelivery Note Item` dni GROUP BY dni.parent) m ON m.p = dn.name
    LEFT JOIN `tabSales Order` so ON so.name = m.so_n
"""


def _dn_where(tab, vals):
    if tab == "backlog":
        # The pile OLDER than the working window — 17k untriaged parcels were
        # invisible when every queue clipped at `days`. Worked by bulk triage.
        vals["backtracks"] = _BACKLOG_TRACKS
        return " AND ".join([
            "dn.docstatus = 1", "COALESCE(dn.custom_exception_action,'') = ''",
            "dn.custom_track_shipment_status IN %(backtracks)s",
            "dn.posting_date < DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)"])
    conds = ["dn.docstatus = 1", "COALESCE(dn.custom_exception_action,'') = ''",
             "dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)"]
    if tab in _DN_TRACK:
        conds.append("dn.custom_track_shipment_status = %(track)s")
        vals["track"] = _DN_TRACK[tab]
    else:  # stale
        conds.append("dn.custom_track_shipment_status IN %(tracks)s")
        conds.append("dn.posting_date <= DATE_SUB(CURDATE(), INTERVAL %(staledays)s DAY)")
        vals["tracks"] = _STALE_TRACKS
        vals["staledays"] = _STALE_DAYS
    return " AND ".join(conds)


@frappe.whitelist()
def board(tab="exceptions", days=30, q="", limit=30, offset=0):
    """The four rescue queues + counts + my day, one call."""
    _gate()
    if tab not in TABS:
        tab = "exceptions"
    days = min(max(int(days or 30), 1), 90)
    limit = min(max(int(limit or 30), 1), 100)
    offset = max(int(offset or 0), 0)
    vals = {"days": days, "limit": limit, "offset": offset}

    counts = {}
    for t in ("exceptions", "failed", "stale", "backlog"):
        v = dict(vals)
        counts[t] = int(frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabDelivery Note` dn WHERE {_dn_where(t, v)}",
            v)[0][0])
    counts["notdelivered"] = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabSales Order`
           WHERE docstatus = 1 AND custom_sales_status = 'Not Delivered'
             AND creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)""",
        {"days": max(days, 60)})[0][0])

    if tab == "notdelivered":
        conds = ["so.docstatus = 1", "so.custom_sales_status = 'Not Delivered'",
                 "so.creation >= DATE_SUB(NOW(), INTERVAL %(ndays)s DAY)"]
        vals["ndays"] = max(days, 60)
        if q and str(q).strip():
            vals["q"] = f"%{str(q).strip()}%"
            conds.append("""(so.name LIKE %(q)s OR so.customer_name LIKE %(q)s
                            OR so.custom_customer_phone LIKE %(q)s OR so.custom_awb LIKE %(q)s)""")
        where = " AND ".join(conds)
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabSales Order` so WHERE {where}", vals)[0][0]
        rows = frappe.db.sql(
            f"""SELECT so.name AS so_name, so.customer_name AS customer,
                       so.grand_total AS total, so.custom_awb AS awb,
                       'Not Delivered' AS track, NULL AS dn,
                       COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
                       so.custom_shipping_city AS city,
                       COALESCE(so.custom_call_attempts, 0) AS attempts,
                       so.custom_next_call_at AS next_call,
                       DATEDIFF(NOW(), so.creation) AS age_d
                FROM `tabSales Order` so WHERE {where}
                ORDER BY COALESCE(so.custom_next_call_at, so.creation)
                LIMIT %(limit)s OFFSET %(offset)s""", vals, as_dict=True)
    else:
        where = _dn_where(tab, vals)
        if q and str(q).strip():
            vals["q"] = f"%{str(q).strip()}%"
            where += """ AND (dn.name LIKE %(q)s OR dn.customer_name LIKE %(q)s
                         OR dn.custom_awb LIKE %(q)s)"""
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabDelivery Note` dn WHERE {where}", vals)[0][0]
        rows = frappe.db.sql(
            _DN_SELECT + f" WHERE {where} ORDER BY dn.posting_date"
                         " LIMIT %(limit)s OFFSET %(offset)s", vals, as_dict=True)

    today = str(now_datetime())[:10]
    mine = {"redeliver": 0, "reship": 0, "returnreq": 0, "dna": 0, "cancel": 0}
    # SO comments only: act() writes the same tag on the parcel AND the order,
    # so counting both doctypes doubled every decision. The section report
    # counts SO comments too — same convention. (A DN-queue decision with no
    # linked order writes only the DN comment and is missed here — rare.)
    for r in frappe.db.sql(
            """SELECT c.content, COUNT(*) n FROM `tabComment` c
               WHERE c.reference_doctype = 'Sales Order'
                 AND c.owner = %s AND c.creation >= %s
                 AND c.content LIKE 'Rescue: %%'
               GROUP BY c.content""",
            (frappe.session.user, f"{today} 00:00:00"), as_dict=True):
        for k in mine:
            if r.content.startswith(f"Rescue: {k}"):
                mine[k] += int(r.n or 0)

    now = str(now_datetime())
    sla_h = _rs_settings().get("slaTriageH", 24)
    return {
        "tab": tab, "counts": counts, "total": int(total or 0),
        "rows": [{
            "id": r.dn or r.so_name, "dn": r.dn or "", "order": r.so_name or "",
            "customer": r.customer or "", "total": float(r.total or 0),
            "awb": r.awb or "", "track": r.track or "",
            "phone": (r.phone or "").strip(), "city": (r.city or "").strip().title(),
            "ageD": int(r.age_d or 0), "attempts": int(r.attempts or 0),
            "nextCall": str(r.next_call)[:16] if r.next_call else "",
            "due": bool(r.next_call and str(r.next_call) <= now),
            # Triage SLA: nobody touched the failing parcel within the target.
            "slaBreached": bool(int(r.attempts or 0) == 0
                                and int(r.age_d or 0) * 24 > sla_h),
        } for r in rows],
        "mine": mine,
        "reasons": _rs_settings().get("reasons", []),
        "serverNow": now[:19],
    }


@frappe.whitelist()
def act(id=None, action=None, note=None):
    """One rescue decision. `id` is the Delivery Note (DN queues) or the Sales
    Order (Not-Delivered queue).

    redeliver  record the Redeliver decision on the parcel (carrier retries)
    reship     new SO copy through the normal flow (orders.reship) + record it
    returnreq  the parcel comes back — Return Requested on the parcel
    dna        customer unreachable: bump attempts, set the retry timer
    cancel     order is dead: Cancelled with a reason (+ return the parcel)
    """
    _gate()
    id = (id or "").strip()
    note = (note or "").strip()
    if action not in ("redeliver", "reship", "returnreq", "dna", "cancel", "resolve"):
        frappe.throw("Unknown action.")

    is_dn = frappe.db.exists("Delivery Note", id)
    is_so = not is_dn and frappe.db.exists("Sales Order", id)
    if not (is_dn or is_so):
        frappe.throw("Unknown parcel/order.")
    dn = id if is_dn else ""
    order = id if is_so else frappe.db.get_value(
        "Delivery Note Item", {"parent": dn}, "against_sales_order")

    if action == "cancel" and not note:
        frappe.throw("A cancel needs a reason.")

    now = now_datetime()
    attempts = 0
    tag = f"Rescue: {action}" + (f" — {note}" if note else "") + f" · by {frappe.session.user}"

    if action == "reship":
        if not order:
            frappe.throw("No order linked to this parcel.")
        from logistics_portal.api.orders import reship
        res = reship(order)
        new_order = res.get("order") if isinstance(res, dict) else ""
        tag = f"Rescue: reship → {new_order}" + (f" — {note}" if note else "") \
              + f" · by {frappe.session.user}"

    # Parcel-side record (turns the exceptions pile into a worked queue).
    if dn and action in ("redeliver", "reship", "returnreq", "cancel", "resolve"):
        dn_action = {"redeliver": "Redeliver", "reship": "Redeliver",
                     "returnreq": "Return Requested",
                     "cancel": "Return Requested",
                     "resolve": "Resolved"}[action]
        doc = frappe.get_doc("Delivery Note", dn)
        if frappe.get_meta("Delivery Note").has_field("custom_exception_action"):
            doc.db_set("custom_exception_action", dn_action, update_modified=False)
            doc.db_set("custom_exception_actioned_at", now, update_modified=False)
        doc.add_comment("Comment", tag)

    # Order-side record + state.
    if order:
        so_updates = {"custom_confirmation_agent": frappe.session.user,
                      "custom_last_call_at": now}
        if action == "dna":
            attempts = int(frappe.db.get_value(
                "Sales Order", order, "custom_call_attempts") or 0) + 1
            so_updates["custom_call_attempts"] = attempts
            so_updates["custom_next_call_at"] = add_to_date(
                now, hours=_rs_settings()["retryDna"])
        else:
            so_updates["custom_next_call_at"] = None
        if action == "cancel":
            so_updates["custom_sales_status"] = "Cancelled"
            if note and frappe.get_meta("Sales Order").has_field(
                    "custom_cancellation_reason"):
                so_updates["custom_cancellation_reason"] = note[:140]
        frappe.db.set_value("Sales Order", order, so_updates, update_modified=True)
        frappe.get_doc("Sales Order", order).add_comment(
            "Comment", tag + (f" (attempt {attempts})" if action == "dna" else ""))

    frappe.db.commit()
    return {"ok": True, "id": id, "action": action, "attempts": attempts,
            "order": order or ""}


@frappe.whitelist()
def bulk_act(ids=None, action=None, note=None):
    """Bulk triage for the backlog pile: mark parcels Return Requested or
    Resolved without the per-customer call flow. Section admins/manager only —
    it moves hundreds of parcels in one click."""
    import json as _json
    _gate()
    if not _is_rs_admin():
        frappe.throw("Only the portal manager or a rescue section admin can "
                     "bulk-triage.", frappe.PermissionError)
    if isinstance(ids, str):
        ids = _json.loads(ids)
    ids = [str(x).strip() for x in (ids or []) if str(x).strip()]
    if not ids:
        frappe.throw("Nothing selected.")
    if len(ids) > 200:
        frappe.throw("200 parcels max per batch.")
    if action not in ("returnreq", "resolve"):
        frappe.throw("Unknown bulk action.")
    note = (note or "").strip()
    dn_action = {"returnreq": "Return Requested", "resolve": "Resolved"}[action]
    now = now_datetime()
    tag = (f"Rescue: {action} (bulk)" + (f" — {note}" if note else "")
           + f" · by {frappe.session.user}")
    done, skipped = [], []
    has_field = frappe.get_meta("Delivery Note").has_field("custom_exception_action")
    for dn in ids:
        if not frappe.db.exists("Delivery Note", dn):
            skipped.append(dn)
            continue
        doc = frappe.get_doc("Delivery Note", dn)
        if has_field:
            doc.db_set("custom_exception_action", dn_action, update_modified=False)
            doc.db_set("custom_exception_actioned_at", now, update_modified=False)
        doc.add_comment("Comment", tag)
        done.append(dn)
    frappe.db.commit()
    return {"ok": True, "done": len(done), "skipped": skipped}


@frappe.whitelist()
def report(days=7):
    """Rescue-section report: per-agent decisions, RESCUE RATE (saved parcels
    vs lost), reasons, day by day. Manager or rescue section admin."""
    _gate()
    if not _is_rs_admin():
        frappe.throw("Only the portal manager or a section admin can open the "
                     "section report.", frappe.PermissionError)
    days = min(max(int(days or 7), 1), 90)
    since = f"DATE_SUB(NOW(), INTERVAL {days} DAY)"

    per_agent = {}
    for r in frappe.db.sql(
            f"""SELECT c.owner, c.content FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order'
                  AND c.content LIKE 'Rescue: %%' AND c.creation >= {since}""",
            as_dict=True):
        action = (r.content.split("Rescue: ", 1)[1] or "").split(" ", 1)[0].strip("()—-→ ")
        a = per_agent.setdefault(r.owner, {"redeliver": 0, "reship": 0,
                                           "returnreq": 0, "dna": 0, "cancel": 0})
        if action in a:
            a[action] += 1

    agents = []
    for user, a in per_agent.items():
        saved = a["redeliver"] + a["reship"]
        lost = a["returnreq"] + a["cancel"]
        agents.append({
            "agent": user.split("@")[0], "user": user, **a,
            "total": sum(a.values()),
            "rescueRate": round(saved * 100.0 / (saved + lost), 1) if (saved + lost) else 0,
        })
    agents.sort(key=lambda x: -x["total"])

    reasons = {}
    for r in frappe.db.sql(
            f"""SELECT c.content FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order'
                  AND (c.content LIKE 'Rescue: cancel%%' OR c.content LIKE 'Rescue: returnreq%%')
                  AND c.creation >= {since}""", as_dict=True):
        txt = r.content
        reason = txt.split("—", 1)[1].split("· by", 1)[0].strip() if "—" in txt else ""
        reasons[reason or "(no reason)"] = reasons.get(reason or "(no reason)", 0) + 1
    reason_rows = sorted(({"reason": k, "n": v} for k, v in reasons.items()),
                         key=lambda x: -x["n"])[:12]

    funnel = frappe.db.sql(
        f"""SELECT DATE(c.creation) d,
                   SUM(c.content LIKE 'Rescue: redeliver%%' OR c.content LIKE 'Rescue: reship%%') saved,
                   SUM(c.content LIKE 'Rescue: returnreq%%' OR c.content LIKE 'Rescue: cancel%%') lost,
                   SUM(c.content LIKE 'Rescue: dna%%') dna
            FROM `tabComment` c
            WHERE c.reference_doctype = 'Sales Order'
              AND c.content LIKE 'Rescue: %%' AND c.creation >= {since}
            GROUP BY DATE(c.creation) ORDER BY d""", as_dict=True)

    return {
        "days": days,
        "agents": agents,
        "reasons": reason_rows,
        "funnel": [{"date": str(f.d), "saved": int(f.saved or 0),
                    "lost": int(f.lost or 0), "dna": int(f.dna or 0)} for f in funnel],
    }
