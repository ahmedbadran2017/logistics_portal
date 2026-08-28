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
# Morocco only. The instance also carries China / Maslak / Holding, whose
# orders share this database. Carrier exceptions happen to be Morocco-only in
# practice (Cathedis is the Moroccan carrier), but the SO-backed "Not
# Delivered" tab is not, so every query here is company-scoped for safety.
_CO = "Justyol Morocco"

_DN_TRACK = {"exceptions": "Delivery Exception", "failed": "Failed Attempt"}
_STALE_TRACKS = ("Out For Delivery", "In Transit", "Pending")
_STALE_DAYS = 7
# Everything the working queues track, for the older-than-window backlog.
_BACKLOG_TRACKS = ("Delivery Exception", "Failed Attempt") + _STALE_TRACKS


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("confirmation", "tracking", "manager"):
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
    role = resolve_role(frappe.session.user)
    if role == "manager":
        return True
    # Capability requires a live portal role — leaving the team must revoke
    # it even if the admins list is stale.
    if role not in ("confirmation", "cs", "tracking"):
        return False
    return frappe.session.user in _rs_settings().get("admins", [])


@frappe.whitelist()
def rs_settings():
    _gate()
    return {**_rs_settings(), "canEdit": _is_rs_admin()}


@frappe.whitelist(methods=["POST"])
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
            # The _is_*_admin checks ignore users without a live CC role —
            # accepting one here would be a silent no-op.
            if resolve_role(a) not in ("confirmation", "cs", "tracking",
                                       "manager"):
                frappe.throw(f"{a} has no contact-center role — assign one "
                             "in Team first.")
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
           DATEDIFF(CURDATE(), dn.posting_date) AS age_d,
           TIMESTAMPDIFF(HOUR, dn.creation, NOW()) AS age_h
    FROM `tabDelivery Note` dn
    LEFT JOIN `tabSales Order` so
      ON so.name = (SELECT MIN(dni.against_sales_order)
                    FROM `tabDelivery Note Item` dni WHERE dni.parent = dn.name)
"""
# NB the SO link is a correlated MIN, not a whole-table GROUP BY: the old
# derived table materialised every DN line on the site per board load (the
# slowest query in the section), and MAX here vs an arbitrary row in act()
# could show one order and act on another. MIN everywhere, evaluated only for
# the filtered page.


def _dn_where(tab, vals):
    vals["co"] = _CO
    if tab == "backlog":
        # The pile OLDER than the working window — 17k untriaged parcels were
        # invisible when every queue clipped at `days`. Worked by bulk triage.
        vals["backtracks"] = _BACKLOG_TRACKS
        return " AND ".join([
            "dn.docstatus = 1", "dn.company = %(co)s",
            "COALESCE(dn.custom_exception_action,'') = ''",
            "dn.custom_track_shipment_status IN %(backtracks)s",
            "dn.posting_date < DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)"])
    conds = ["dn.docstatus = 1", "dn.company = %(co)s",
             "COALESCE(dn.custom_exception_action,'') = ''",
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
           WHERE docstatus = 1 AND company = %(co)s
             AND custom_sales_status = 'Not Delivered'
             AND creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)""",
        {"days": max(days, 60), "co": _CO})[0][0])

    if tab == "notdelivered":
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status = 'Not Delivered'",
                 "so.creation >= DATE_SUB(NOW(), INTERVAL %(ndays)s DAY)"]
        vals["ndays"] = max(days, 60)
        vals["co"] = _CO
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
                       DATEDIFF(NOW(), so.creation) AS age_d,
                       TIMESTAMPDIFF(HOUR, so.creation, NOW()) AS age_h
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
            # Triage SLA in HOURS: the old day-grain math (age_d * 24) needed
            # a full 2 days to breach a 24h target, understating every breach.
            "slaBreached": bool(int(r.attempts or 0) == 0
                                and int(getattr(r, "age_h", 0) or 0) > sla_h),
        } for r in rows],
        "mine": mine,
        "reasons": _rs_settings().get("reasons", []),
        "serverNow": now[:19],
    }


@frappe.whitelist()
def my_report(days=7, frm=None, to=None):
    """The tracking agent's OWN numbers — measured in THEIR craft: rescue
    decisions, the save rate (kept moving vs. sent back), and how many of the
    parcels they touched actually got delivered afterwards."""
    _gate()
    from logistics_portal.api.confirmation import _range
    me = frappe.session.user
    rng, rng_vals = _range(days, frm, to)
    rng_vals = {**rng_vals, "me": me}
    c_rng = rng.format(col="c.creation")

    acts = {"redeliver": 0, "reship": 0, "returnreq": 0, "dna": 0,
            "cancel": 0, "resolve": 0}
    daily = {}
    for r in frappe.db.sql(
            f"""SELECT DATE(c.creation) d, c.content, COUNT(*) n
                FROM `tabComment` c
                WHERE c.owner = %(me)s AND c.content LIKE 'Rescue: %%' AND {c_rng}
                GROUP BY DATE(c.creation), c.content""", rng_vals, as_dict=True):
        if "(bulk)" in (r.content or ""):
            continue
        action = (r.content.split("Rescue: ", 1)[1] or "").split(" ", 1)[0].strip("()—-→ ")
        if action not in acts:
            continue
        n = int(r.n or 0)
        acts[action] += n
        day = daily.setdefault(str(r.d), {"save": 0, "dna": 0, "back": 0})
        if action in ("redeliver", "reship"):
            day["save"] += n
        elif action == "dna":
            day["dna"] += n
        elif action in ("returnreq", "cancel"):
            day["back"] += n

    saves = acts["redeliver"] + acts["reship"]
    closed = saves + acts["returnreq"] + acts["cancel"]

    # Of the orders this agent touched in the window: how many are DELIVERED
    # now — the number that says the rescue actually worked.
    outcome = frappe.db.sql(
        f"""SELECT COUNT(DISTINCT c.reference_name),
                   COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status
                                            = 'Delivered'
                                       THEN c.reference_name END)
            FROM `tabComment` c
            JOIN `tabDelivery Note Item` dni
              ON dni.against_sales_order = c.reference_name AND dni.docstatus = 1
            JOIN `tabDelivery Note` dn
              ON dn.name = dni.parent AND dn.docstatus = 1
            WHERE c.owner = %(me)s AND c.reference_doctype = 'Sales Order'
              AND c.content LIKE 'Rescue: %%' AND {c_rng}""", rng_vals)[0]

    return {
        "acts": acts,
        "daily": [{"date": d, **v} for d, v in sorted(daily.items())],
        "saveRate": round(saves * 100 / closed) if closed else None,
        "acted": int(outcome[0] or 0),
        "deliveredAfter": int(outcome[1] or 0),
    }


@frappe.whitelist(methods=["POST"])
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
    # Every rescue queue is company-scoped; the write must be too.
    if frappe.db.get_value("Delivery Note" if is_dn else "Sales Order",
                           id, "company") != _CO:
        frappe.throw("Unknown parcel/order.")
    dn = id if is_dn else ""
    # MIN, matching the board's SO link — get_value picked an arbitrary line,
    # so on multi-order parcels the agent could act on a different order than
    # the one the row displayed.
    order = id if is_so else (frappe.db.sql(
        """SELECT MIN(against_sales_order) FROM `tabDelivery Note Item`
           WHERE parent = %s""", (dn,))[0][0] or "")

    # Ownership fence for the per-agent Not-Delivered scope: the confirmation
    # board filters rows by _assign, but this endpoint used to accept ANY order
    # id — one call could act on (and, worse, claim credit for) a colleague's
    # order. Managers and section admins stay unrestricted; the shared DN
    # queues (exceptions/failed/stale/backlog) are team-worked by design.
    if is_so and not _is_rs_admin():
        assigned = frappe.db.get_value("Sales Order", id, "_assign") or ""
        if f'"{frappe.session.user}"' not in assigned:
            frappe.throw("This order is assigned to another agent.",
                         frappe.PermissionError)

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

    # Order-side record + state. Attribution: a rescue touch must NOT steal
    # the confirming agent's credit — custom_allocated_to feeds the done tabs,
    # the money report and the delivered bonus points, and this line used to
    # overwrite it unconditionally (a one-call transfer of a colleague's
    # delivered-parcel bonus). Claim it only when nobody holds it.
    if order:
        so_updates = {"custom_last_call_at": now}
        if not (frappe.db.get_value("Sales Order", order, "custom_allocated_to") or ""):
            so_updates["custom_allocated_to"] = frappe.session.user
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


@frappe.whitelist(methods=["POST"])
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
        # Per-item isolation: one bad parcel must not abort (and discard) the
        # rest of a 200-parcel triage batch.
        try:
            if frappe.db.get_value("Delivery Note", dn, "company") != _CO:
                skipped.append(dn)
                continue
            doc = frappe.get_doc("Delivery Note", dn)
            if has_field:
                doc.db_set("custom_exception_action", dn_action, update_modified=False)
                doc.db_set("custom_exception_actioned_at", now, update_modified=False)
            doc.add_comment("Comment", tag)
            # Mirror the tag on the ORDER too: the board's "mine" tally and the
            # section report count SO comments only, so bulk triage — the tool
            # built for the 17k backlog — was invisible in every rescue metric.
            # The "(bulk)" marker keeps it out of bonus scoring.
            so = frappe.db.sql(
                """SELECT MIN(against_sales_order) FROM `tabDelivery Note Item`
                   WHERE parent = %s""", (dn,))[0][0]
            if so and frappe.db.exists("Sales Order", so):
                frappe.get_doc("Sales Order", so).add_comment("Comment", tag)
            done.append(dn)
        except Exception:
            skipped.append(dn)
            frappe.log_error(frappe.get_traceback(), "rescue.bulk_act")
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


@frappe.whitelist()
def dashboard():
    """The rescue lane's queue-health view — the sibling the other two lanes
    always had. All panels describe RIGHT NOW (there is no snapshot history):
    queue depths with value at stake, how long failing parcels have waited
    untouched, and the day-by-day inflow vs. decisions for two weeks.

    Team-level view — with the ten oldest failures' customer names and
    phones. Section admins and the manager only."""
    _gate()
    if not _is_rs_admin():
        frappe.throw("Not authorized.", frappe.PermissionError)
    sla_h = _rs_settings().get("slaTriageH", 24)

    cards = {}
    for tab in ("exceptions", "failed", "stale", "backlog"):
        vals = {"days": 30}
        where = _dn_where(tab, vals)
        r = frappe.db.sql(
            f"""SELECT COUNT(*), ROUND(COALESCE(SUM(dn.grand_total), 0))
                FROM `tabDelivery Note` dn WHERE {where}""", vals)[0]
        cards[tab] = {"n": int(r[0] or 0), "value": int(r[1] or 0)}

    # Untouched-vs-SLA and age spread of the two active failure queues.
    vals = {"days": 30}
    where = _dn_where("exceptions", vals)
    where = where.replace("dn.custom_track_shipment_status = %(track)s",
                          "dn.custom_track_shipment_status IN "
                          "('Delivery Exception', 'Failed Attempt')")
    vals.pop("track", None)
    aging = frappe.db.sql(
        f"""SELECT
              SUM(TIMESTAMPDIFF(HOUR, dn.creation, NOW()) <= 24),
              SUM(TIMESTAMPDIFF(HOUR, dn.creation, NOW()) BETWEEN 25 AND 72),
              SUM(TIMESTAMPDIFF(HOUR, dn.creation, NOW()) > 72),
              SUM(COALESCE(so.custom_call_attempts, 0) = 0
                  AND TIMESTAMPDIFF(HOUR, dn.creation, NOW()) > %(sla)s)
            FROM `tabDelivery Note` dn
            LEFT JOIN `tabSales Order` so
              ON so.name = (SELECT MIN(dni.against_sales_order)
                            FROM `tabDelivery Note Item` dni
                            WHERE dni.parent = dn.name)
            WHERE {where}""", {**vals, "sla": sla_h})[0]
    ages = {"d1": int(aging[0] or 0), "d3": int(aging[1] or 0),
            "older": int(aging[2] or 0), "breached": int(aging[3] or 0)}

    # 14 days: parcels that STARTED failing vs. rescue decisions taken.
    inflow = {str(r[0]): int(r[1] or 0) for r in frappe.db.sql(
        """SELECT dn.posting_date, COUNT(*) FROM `tabDelivery Note` dn
           WHERE dn.docstatus = 1 AND dn.company = %s
             AND dn.custom_track_shipment_status IN
                 ('Delivery Exception', 'Failed Attempt')
             AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
           GROUP BY dn.posting_date""", (_CO,))}
    decided = {str(r[0]): int(r[1] or 0) for r in frappe.db.sql(
        """SELECT DATE(c.creation), COUNT(*) FROM `tabComment` c
           JOIN `tabSales Order` so ON so.name = c.reference_name
           WHERE c.reference_doctype = 'Sales Order'
             AND so.company = %s
             AND c.content LIKE 'Rescue: %%'
             AND c.creation >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
           GROUP BY DATE(c.creation)""", (_CO,))}
    days_axis = [str(r[0]) for r in frappe.db.sql(
        """SELECT DATE_SUB(CURDATE(), INTERVAL n DAY) FROM
           (SELECT 13 n UNION SELECT 12 UNION SELECT 11 UNION SELECT 10
            UNION SELECT 9 UNION SELECT 8 UNION SELECT 7 UNION SELECT 6
            UNION SELECT 5 UNION SELECT 4 UNION SELECT 3 UNION SELECT 2
            UNION SELECT 1 UNION SELECT 0) t ORDER BY 1""")]
    daily = [{"d": d, "inflow": inflow.get(d, 0), "decided": decided.get(d, 0)}
             for d in days_axis]

    # The ten longest-waiting untouched failures — the call list.
    oldest = frappe.db.sql(
        _DN_SELECT + """ WHERE dn.docstatus = 1 AND dn.company = %(co)s
              AND COALESCE(dn.custom_exception_action,'') = ''
              AND dn.custom_track_shipment_status IN
                  ('Delivery Exception', 'Failed Attempt')
              AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            ORDER BY dn.posting_date LIMIT 10""",
        {"co": _CO}, as_dict=True)

    return {
        "cards": cards, "ages": ages, "slaH": sla_h, "daily": daily,
        "oldest": [{
            "dn": r.dn, "order": r.so_name or "", "customer": r.customer or "",
            "phone": (r.phone or "").strip(), "track": r.track or "",
            "ageD": int(r.age_d or 0), "attempts": int(r.attempts or 0),
            "value": float(r.total or 0),
        } for r in oldest],
        "serverNow": str(now_datetime())[:19],
    }
