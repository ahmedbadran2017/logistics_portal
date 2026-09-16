"""Carrier status sync — the pull that keeps 'Pending' honest.

Measured 2026-09-16: the carrier's status reaches us two ways. A webhook
(the `cathedis@justyol.com` user) updates 200–290 Delivery Notes a day while
350–550 parcels ship a day, so about half of every day's parcels stay
'Pending' in our book although the carrier is moving or has delivered them
(checked against the Cathedis API: LD008506393 'Livré', ours Pending). The
other half was closed by hand — someone ran the Desk report 'Cathedis Status
Comparison → Resync mismatches' on 2 / 7 / 9 / 10 September (500 to 1,200
notes each time) — and nobody ran it after the 10th, so the gap grew to
~1,000 parcels and the tracking board called them 'never scanned by the
carrier'. This module runs that same resync on a clock, for the recent
window only, so the board tells the truth without anyone remembering.

It calls codx_erp's resync as is: one bulk Cathedis search per 500 AWBs,
a Shipment Tracking row per changed status, and the ecommerce_integrations
hook then propagates to Sales Order / Delivery Note / Shipment rows and, on
'Livré', submits the invoices and COD payment entries — exactly what the
webhook does for the parcels it does reach.
"""
import json

import frappe
from frappe.utils import add_days, now_datetime, nowdate

_ON = "lp_carrier_sync"
_LAST = "lp_carrier_sync_last"
_DAYS = 21


def enabled():
    v = frappe.db.get_default(_ON)
    return v is None or str(v) not in ("0", "", "false", "False")


def _is_manager():
    # Same door as the Tracking settings page: managers and the named leads.
    from logistics_portal.api.permissions import is_ops_admin
    return bool(is_ops_admin())


@frappe.whitelist(methods=["POST"])
def set_enabled(on=1):
    if not _is_manager():
        frappe.throw("Only a manager can change this.", frappe.PermissionError)
    frappe.db.set_default(_ON, "1" if int(on or 0) else "0")
    frappe.db.commit()
    return status()


def _pending_count():
    """Parcels handed to the carrier in the window whose status never moved."""
    return int(frappe.db.sql(
        """SELECT COUNT(DISTINCT dn.name)
           FROM `tabShipment` sh
           JOIN `tabShipment Delivery Note` sdn ON sdn.parent = sh.name
           JOIN `tabDelivery Note` dn ON dn.name = sdn.delivery_note AND dn.docstatus = 1
           WHERE sh.docstatus = 1 AND sh.delivery_customer = 'CATHEDIS'
             AND sh.pickup_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
             AND COALESCE(dn.custom_track_shipment_status, '') IN ('', 'Pending')
             AND COALESCE(dn.custom_tracking_number, '') <> ''""", (_DAYS,))[0][0] or 0)


@frappe.whitelist()
def status():
    """For the settings page: on/off, the last run and what it did, and how
    many handed parcels still say Pending right now."""
    if not _is_manager():
        frappe.throw("Not authorized.", frappe.PermissionError)
    raw = frappe.db.get_default(_LAST)
    try:
        last = json.loads(raw) if raw else None
    except Exception:
        last = None
    return {"on": enabled(), "last": last, "pending": _pending_count(), "days": _DAYS}


def _resync(from_date, to_date):
    from codx_erp.codx_erp.report.cathedis_status_comparison.cathedis_status_comparison import (
        resync_mismatches)
    return resync_mismatches({"from_date": str(from_date), "to_date": str(to_date),
                              "company": "Justyol Morocco"})


def run(force=False):
    """Scheduled hourly. One runner at a time; the window is the last
    _DAYS days of orders — the same window the hand-run report used."""
    if not (force or enabled()):
        return {"ok": False, "reason": "off"}
    got = frappe.db.sql("SELECT GET_LOCK('lp_carrier_sync', 5)")[0][0]
    if not got:
        return {"ok": False, "reason": "running"}
    started = now_datetime()
    out = {"startedAt": str(started)[:19], "ok": False}
    try:
        before = _pending_count()
        res = _resync(add_days(nowdate(), -_DAYS), nowdate()) or {}
        frappe.db.commit()
        out.update({"ok": True, "processed": int(res.get("processed") or 0),
                    "inserted": int(res.get("inserted") or 0),
                    "skipped": int(res.get("skipped") or 0),
                    "errors": len(res.get("errors") or []) if isinstance(res.get("errors"), list) else int(res.get("errors") or 0),
                    "pendingBefore": before, "pendingAfter": _pending_count(),
                    "seconds": int((now_datetime() - started).total_seconds())})
    except Exception as e:
        frappe.db.rollback()
        out.update({"ok": False, "error": str(e)[:300],
                    "seconds": int((now_datetime() - started).total_seconds())})
        frappe.log_error(frappe.get_traceback()[-2500:], "carrier_sync.run")
    finally:
        try:
            frappe.db.set_default(_LAST, json.dumps(out))
            frappe.db.commit()
        except Exception:
            pass
        try:
            frappe.db.sql("SELECT RELEASE_LOCK('lp_carrier_sync')")
        except Exception:
            pass
    return out


@frappe.whitelist(methods=["POST"])
def run_now():
    """Manager: run the sync in the background right away."""
    if not _is_manager():
        frappe.throw("Only a manager can run the sync.", frappe.PermissionError)
    frappe.enqueue("logistics_portal.api.carrier_sync.run", queue="long", timeout=1800,
                   job_name="lp_carrier_sync_now", force=True)
    return {"ok": True}
