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

    # SLA breaches on Delivery Notes (systemic → managers).
    breached = frappe.db.count("Delivery Note", {"custom_sla_status": "Breached"})
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
        "Pick List", {"custom_assigned_picker": ["in", ["", None]], "docstatus": 1}
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
    """Write to Notification Log (audit trail) + push a realtime toast."""
    try:
        frappe.get_doc(
            {
                "doctype": "Notification Log",
                "subject": alert["title"],
                "email_content": alert.get("detail", ""),
                "type": "Alert",
                "document_type": "Delivery Note",
                "for_user": frappe.session.user,
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
            filters={"type": "Alert"},
            fields=["subject", "email_content", "creation"],
            order_by="creation desc",
            limit=30,
        )
        out = []
        for r in rows:
            title = r.subject or ""
            sev = "red" if ("breach" in title.lower() or "sla" in title.lower()) else "yellow"
            out.append({
                "sev": sev,
                "kind": "alert",
                "t": pretty_date(r.creation),
                "title": title,
                "body": r.email_content or "",
                "action": None,
                "order": None,
            })
        return out
    except Exception:
        return []


@frappe.whitelist()
def copilot_chat(message):
    """Placeholder for the docked AI copilot. Wire to an LLM over live data."""
    # TODO: assemble live logistics context + call the model.
    return {"reply": "The copilot backend is not wired yet."}
