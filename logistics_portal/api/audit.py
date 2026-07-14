"""Audit & alerts — deterministic rule engine + periodic LLM insight digest.

- run_rule_engine (every 10 min): scans recent docs against thresholds, writes
  Notification Log entries and pushes realtime toasts. Severity-tiered, targeted
  (workers get their own nudges; managers get systemic alerts).
- generate_daily_digest (daily): narrative observations for the manager.
"""

import frappe
from frappe.utils import nowdate


def run_rule_engine():
    """Scheduled deterministic scan. Safe/no-op-friendly."""
    try:
        alerts = _detect()
        for a in alerts:
            _emit(a)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.run_rule_engine")


def _detect():
    """Alerts = the problem radar's CRITICAL findings (one scan, one truth —
    the Audit page and the notifications can never disagree)."""
    frappe.cache().delete_value("lp_problem_radar")  # scheduled tick = fresh scan
    radar = problem_radar()
    alerts = []
    for f in radar.get("findings", []):
        if f.get("sev") != "critical":
            continue
        alerts.append({
            "severity": "critical",
            "title": f"{f['count']} · {f['title']}",
            "detail": f.get("detail", ""),
            "audience": "manager",
        })
    return alerts


def _emit(alert):
    """Write to Notification Log (audit trail) + push a realtime toast.
    Dedup: skip if an identical unread alert already exists (the engine runs
    every 10 minutes — without this it spammed a fresh row each tick). The
    scheduler runs as Administrator, so the log rows target the real portal
    managers, not the session user."""
    from logistics_portal.api.auth import SEED_ROLES

    try:
        if frappe.db.exists("Notification Log",
                            {"subject": alert["title"], "read": 0}):
            return
        managers = [u for u, r in SEED_ROLES.items() if r == "manager"] or [frappe.session.user]
        for user in managers:
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "subject": alert["title"],
                    "email_content": alert.get("detail", ""),
                    "type": "Alert",
                    "document_type": "Delivery Note",
                    "for_user": user,
                }
            ).insert(ignore_permissions=True)
    except Exception:
        pass
    frappe.publish_realtime("logistics_alert", alert)


def generate_daily_digest():
    """Placeholder for the end-of-shift LLM reviewer. Writes a Logistics Audit
    Note the manager reads. Wire to an LLM once the doctype is installed."""
    # TODO: read the day's data + Layer-A events, call the LLM, store observations.
    return {"ok": True}


@frappe.whitelist()
def recent_alerts():
    """Recent alerts for the Audit/Alerts screens, in the SPA's AUDIT item shape
    (sev/kind/t/title/body). Sourced from Notification Log entries written by the
    rule engine — empty until it has run at least once."""
    from frappe.utils import pretty_date

    try:
        rows = frappe.get_all(
            "Notification Log",
            # Scoped to THIS user's logistics alerts. document_type keeps system
            # noise (failed HR emails etc.) out of the operations feed.
            filters={"type": "Alert", "for_user": frappe.session.user,
                     "document_type": ["in", ["Delivery Note", "Sales Order"]]},
            fields=["name", "subject", "email_content", "creation", "read",
                    "document_type", "document_name"],
            order_by="creation desc",
            limit=30,
        )
        out = []
        for r in rows:
            title = r.subject or ""
            sev = "red" if ("breach" in title.lower() or "sla" in title.lower()) else "yellow"
            out.append({
                "id": r.name,
                "read": bool(r.read),
                "sev": sev,
                "kind": "alert",
                "t": pretty_date(r.creation),
                "title": title,
                "body": r.email_content or "",
                "action": None,
                "order": r.document_name if r.document_type == "Sales Order" else None,
            })
        return out
    except Exception:
        return []


@frappe.whitelist()
def unread_count():
    """Bell badge: this user's unread logistics alerts (polled by the shell)."""
    try:
        return frappe.db.count("Notification Log", {
            "type": "Alert", "for_user": frappe.session.user, "read": 0,
            "document_type": ["in", ["Delivery Note", "Sales Order"]],
        })
    except Exception:
        return 0


@frappe.whitelist()
def mark_read(names=None):
    """Mark alerts read — a list of ids, or everything for this user."""
    import json as _json
    if isinstance(names, str):
        try:
            names = _json.loads(names)
        except Exception:
            names = [names]
    user = frappe.session.user
    if names:
        for n in names:
            # Ownership check: only your own rows.
            if frappe.db.get_value("Notification Log", n, "for_user") == user:
                frappe.db.set_value("Notification Log", n, "read", 1,
                                    update_modified=False)
    else:
        frappe.db.sql(
            """UPDATE `tabNotification Log` SET `read` = 1
               WHERE for_user = %s AND `read` = 0 AND type = 'Alert'
                 AND document_type IN ('Delivery Note', 'Sales Order')""",
            (user,))
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist()
def copilot_chat(message):
    """Placeholder for the docked AI copilot. Wire to an LLM over live data."""
    # TODO: assemble live logistics context + call the model.
    return {"reply": "The copilot backend is not wired yet."}


# ---------------------------------------------------------------------------
# Problem radar — the "active agent" of the Audit page. One scan, every known
# operational failure mode, all real SQL over indexed/windowed tables, cached
# 120s. Each finding carries a severity + a route to the screen that fixes it.
# The 10-min rule engine reuses the same scan to emit alerts for criticals.
# ---------------------------------------------------------------------------
@frappe.whitelist()
def problem_radar():
    """Every open operational problem, one call. Cached 120s."""
    import json as _json
    from frappe.utils import add_days, nowdate

    cache = frappe.cache()
    cached = cache.get_value("lp_problem_radar")
    if cached:
        try:
            return _json.loads(cached)
        except Exception:
            pass

    findings = []

    def check(fn):
        try:
            fn()
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"logistics_portal.radar:{fn.__name__}")

    def one(sql, args=()):
        r = frappe.db.sql(sql, args)
        return (int(r[0][0] or 0), float(r[0][1] or 0) if len(r[0]) > 1 else 0)

    since14 = add_days(nowdate(), -14)

    def open_breaches():
        n, _ = one("""SELECT COUNT(*) FROM `tabDelivery Note`
            WHERE custom_sla_status='Breached' AND posting_date >= %s
              AND COALESCE(custom_track_shipment_status,'') <> 'Delivered'""", (since14,))
        if n:
            findings.append({"key": "breaches", "sev": "critical", "count": n,
                "title": "Open SLA breaches",
                "detail": "Past the delivery promise and still not delivered.",
                "route": "/logistics/sla"})

    def at_risk_today():
        n, _ = one("""SELECT COUNT(*) FROM `tabDelivery Note`
            WHERE custom_sla_status='At Risk' AND posting_date >= %s
              AND COALESCE(custom_track_shipment_status,'') <> 'Delivered'""", (since14,))
        if n:
            findings.append({"key": "atRisk", "sev": "warning", "count": n,
                "title": "Parcels at risk",
                "detail": "Due within a day — still moving.",
                "route": "/logistics/sla"})

    def stuck_to_pick():
        n, v = one("""SELECT COUNT(*), COALESCE(SUM(grand_total),0) FROM `tabSales Order`
            WHERE docstatus=1 AND custom_sales_status='Confirmed'
              AND COALESCE(custom_logistics_status,'Pending')='Pending'
              AND creation BETWEEN DATE_SUB(NOW(), INTERVAL 60 DAY)
                               AND DATE_SUB(NOW(), INTERVAL 48 HOUR)
              AND NOT EXISTS (SELECT 1 FROM `tabPick List Item` pli
                              JOIN `tabPick List` p ON p.name = pli.parent
                              WHERE pli.sales_order = `tabSales Order`.name
                                AND p.docstatus < 2)""")
        if n:
            findings.append({"key": "stuckToPick", "sev": "critical", "count": n,
                "value": round(v),
                "title": "Orders stuck before picking (48h+)",
                "detail": "Confirmed, no pick list — usually out-of-stock or forgotten.",
                "route": "/logistics/pipeline?stage=to_pick"})

    def no_awb():
        n, _ = one("""SELECT COUNT(DISTINCT pli.sales_order) FROM `tabPick List` p
            JOIN `tabPick List Item` pli ON pli.parent = p.name
            JOIN `tabSales Order` so ON so.name = pli.sales_order
            WHERE p.docstatus = 1 AND p.creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
              AND p.modified < DATE_SUB(NOW(), INTERVAL 2 HOUR)
              AND so.custom_sales_status='Confirmed'
              AND COALESCE(so.custom_awb,'') = ''""")
        if n:
            findings.append({"key": "noAwb", "sev": "critical", "count": n,
                "title": "Picked but no AWB (2h+)",
                "detail": "The carrier automation failed — retry AWB from the Orders board.",
                "route": "/logistics/pipeline"})

    def unprinted_aging():
        n, _ = one("""SELECT COUNT(*) FROM `tabSales Order`
            WHERE docstatus=1 AND custom_sales_status='Confirmed'
              AND custom_logistics_status='Label Generated'
              AND modified < DATE_SUB(NOW(), INTERVAL 24 HOUR)
              AND creation >= DATE_SUB(NOW(), INTERVAL 14 DAY)""")
        if n:
            findings.append({"key": "unprinted", "sev": "warning", "count": n,
                "title": "Labels generated, never printed (24h+)",
                "detail": "Sorted or skipped? They're not moving toward the truck.",
                "route": "/logistics/labels"})

    def missed_manifest():
        n, v = one("""SELECT COUNT(*), COALESCE(SUM(dn.grand_total),0)
            FROM `tabDelivery Note` dn
            JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
            JOIN `tabSales Order` so ON so.name = dni.against_sales_order
            WHERE dn.docstatus = 1 AND dn.posting_date >= %s
              AND dn.posting_date < CURDATE()
              AND so.custom_logistics_status = 'Label Printed'
              AND COALESCE(dn.custom_awb,'') != ''
              AND NOT EXISTS (SELECT 1 FROM `tabShipment Delivery Note` sdn
                              WHERE sdn.delivery_note = dn.name)""", (since14,))
        if n:
            findings.append({"key": "missedManifest", "sev": "critical", "count": n,
                "value": round(v),
                "title": "Printed parcels that missed the truck",
                "detail": "Label printed before today and never scanned onto a manifest.",
                "route": "/logistics/manifest"})

    def exceptions_open():
        has_action = frappe.get_meta("Delivery Note").has_field("custom_exception_action")
        cond = "AND COALESCE(custom_exception_action,'') = ''" if has_action else ""
        n, _ = one(f"""SELECT COUNT(*) FROM `tabDelivery Note`
            WHERE docstatus=1 AND posting_date >= %s
              AND custom_track_shipment_status IN ('Delivery Exception','Failed Attempt')
              {cond}""", (since14,))
        if n:
            findings.append({"key": "exceptions", "sev": "warning", "count": n,
                "title": "Exceptions waiting for a decision",
                "detail": "Failed deliveries with no triage recorded yet.",
                "route": "/logistics/exceptions"})

    def return_zone():
        n, v = one("""SELECT COALESCE(SUM(actual_qty),0), COALESCE(SUM(stock_value),0)
            FROM `tabBin` WHERE warehouse = 'Return Zone - JM' AND actual_qty > 0""")
        if n:
            findings.append({"key": "returnZone", "sev": "warning", "count": n,
                "value": round(v),
                "title": "Stock stranded in the Return Zone",
                "detail": "Inspect and restock — it counts as OOS while it sits there.",
                "route": "/logistics/returns/restock"})

    def short_picked():
        if not frappe.get_meta("Sales Order").has_field("custom_short_picked_at"):
            return
        n, _ = one("""SELECT COUNT(*) FROM `tabSales Order`
            WHERE custom_short_picked_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)""")
        if n:
            findings.append({"key": "shortPicked", "sev": "warning", "count": n,
                "title": "Short-picked in the last 24h",
                "detail": "Shelf was empty though Bin says in stock — check the shelf/stock mismatch.",
                "route": "/logistics/pipeline?stage=to_pick"})

    def stale_ret_batch():
        n, _ = one("""SELECT COUNT(*) FROM `tabReturn Shipment`
            WHERE docstatus = 0 AND creation < DATE_SUB(NOW(), INTERVAL 24 HOUR)""")
        if n:
            findings.append({"key": "staleRet", "sev": "warning", "count": n,
                "title": "Receiving batch left open (24h+)",
                "detail": "Close it so the stock returns actually post.",
                "route": "/logistics/returns/receive"})

    def consol_waiting():
        from logistics_portal.api.orders import consolidation_groups
        groups = consolidation_groups(limit=60) or []
        extra = sum(max(0, (g.get("count") or 0) - 1) for g in groups)
        if groups:
            findings.append({"key": "consol", "sev": "info", "count": len(groups),
                "value": extra,
                "title": "Same-customer clusters to merge",
                "detail": f"{extra} extra parcels will ship if they're merged/combined.",
                "route": "/logistics/consolidation"})

    for fn in (open_breaches, at_risk_today, stuck_to_pick, no_awb, unprinted_aging,
               missed_manifest, exceptions_open, return_zone, short_picked,
               stale_ret_batch, consol_waiting):
        check(fn)

    sev_rank = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (sev_rank.get(f["sev"], 3), -f["count"]))
    out = {"findings": findings,
           "scannedAt": str(frappe.utils.now_datetime())[:19],
           "critical": sum(1 for f in findings if f["sev"] == "critical"),
           "warning": sum(1 for f in findings if f["sev"] == "warning"),
           "info": sum(1 for f in findings if f["sev"] == "info")}
    cache.set_value("lp_problem_radar", _json.dumps(out), expires_in_sec=120)
    return out
