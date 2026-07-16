"""One-off / recurring maintenance jobs, manager-triggered from Settings.

Release stale reservations: 62k orders sit with custom_sales_status =
'Cancelled' but docstatus 1 and ERPNext status still 'To Deliver...' — each
one keeps reserving its items in the bins (the root cause of the deeply
negative naive stock math the picking engine works around). The ERPNext-
sanctioned release is Sales Order.update_status("Closed"), which recomputes
the per-bin reserved qty. This runs it over the pile as a background job
with a progress counter.
"""

import json

import frappe
from frappe.utils import now_datetime

_PROG_KEY = "lp_release_progress"


def _manager_gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Manager only.", frappe.PermissionError)


def _progress():
    raw = frappe.db.get_default(_PROG_KEY)
    try:
        p = json.loads(raw) if raw else {}
    except Exception:
        p = {}
    return {"running": bool(p.get("running")), "done": int(p.get("done") or 0),
            "failed": int(p.get("failed") or 0),
            "startedAt": p.get("startedAt") or "",
            "heartbeat": p.get("heartbeat") or ""}


def _save_progress(p):
    frappe.db.set_default(_PROG_KEY, json.dumps(p))
    frappe.db.commit()


def _remaining():
    return int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabSales Order`
           WHERE docstatus = 1 AND custom_sales_status = 'Cancelled'
             AND status NOT IN ('Closed', 'Completed')""")[0][0])


@frappe.whitelist()
def release_status():
    _manager_gate()
    from frappe.utils import add_to_date, get_datetime
    p = _progress()
    # A job that hasn't heartbeat in 10 minutes is dead — unlock the button.
    if p["running"] and p["heartbeat"] and \
            get_datetime(p["heartbeat"]) < add_to_date(now_datetime(), minutes=-10):
        p["running"] = False
        p["stale"] = True
        _save_progress(p)
    return {**p, "remaining": _remaining()}


@frappe.whitelist()
def release_start():
    """Close every Cancelled-status order still holding reservations."""
    _manager_gate()
    p = _progress()
    if p["running"]:
        frappe.throw("The release job is already running.")
    _save_progress({"running": True, "done": 0, "failed": 0,
                    "startedAt": str(now_datetime())[:19],
                    "heartbeat": str(now_datetime())[:19]})
    frappe.enqueue("logistics_portal.api.maintenance.release_job",
                   queue="long", timeout=14400, job_name="lp_release_reservations")
    return {"ok": True, "remaining": _remaining()}


def release_job():
    done = failed = 0
    while True:
        names = [r[0] for r in frappe.db.sql(
            """SELECT name FROM `tabSales Order`
               WHERE docstatus = 1 AND custom_sales_status = 'Cancelled'
                 AND status NOT IN ('Closed', 'Completed')
               ORDER BY creation LIMIT 200""")]
        if not names:
            break
        for name in names:
            try:
                doc = frappe.get_doc("Sales Order", name)
                doc.flags.ignore_permissions = True
                doc.update_status("Closed")
                done += 1
            except Exception:
                failed += 1
                frappe.log_error(frappe.get_traceback()[:3000],
                                 f"lp_release {name}")
                # Don't let one bad order wedge the loop.
                frappe.db.rollback()
        _save_progress({"running": True, "done": done, "failed": failed,
                        "startedAt": _progress()["startedAt"],
                        "heartbeat": str(now_datetime())[:19]})
    p = _progress()
    p.update({"running": False, "done": done, "failed": failed,
              "heartbeat": str(now_datetime())[:19]})
    _save_progress(p)
