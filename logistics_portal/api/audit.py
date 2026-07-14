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
    """Return a list of alert dicts. Extend with more checks over time."""
    alerts = []

    from frappe.utils import add_days, nowdate

    # SLA breaches on Delivery Notes (systemic → managers). Open + recent only —
    # unwindowed, this scanned all 100k DNs every 10 minutes and alerted on
    # parcels delivered months ago.
    breached = frappe.db.count("Delivery Note", {
        "custom_sla_status": "Breached",
        "posting_date": [">=", add_days(nowdate(), -14)],
        "custom_track_shipment_status": ["not in", ["Delivered"]],
    })
    if breached:
        alerts.append(
            {
                "severity": "critical",
                "title": f"{breached} deliveries breached SLA",
                "detail": "Review the At-Risk board in the cockpit.",
                "audience": "manager",
            }
        )

    # Submitted Pick Lists missing a picker (data-quality → managers).
    unassigned = frappe.db.count(
        "Pick List", {"custom_assigned_picker": ["in", ["", None]], "docstatus": 1,
                      "creation": [">=", add_days(nowdate(), -7)]}
    )
    if unassigned:
        alerts.append(
            {
                "severity": "info",
                "title": f"{unassigned} pick lists missing a picker",
                "detail": "Capture gap — performance data incomplete.",
                "audience": "manager",
            }
        )
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
