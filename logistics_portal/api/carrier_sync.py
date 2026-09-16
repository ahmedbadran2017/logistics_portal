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


# ── Two-sided reconciliation: our door scan against the carrier's record ──
#
# Ahmed, 2026-09-16: "sometimes we hand the goods to the carrier and they
# get lost there — the match has to run from both sides." Four outcomes for
# every parcel of the last days:
#
#   ours + theirs      clean.
#   ours, not theirs   we scanned it onto a manifest, the carrier still says
#                      'En Attente Ramassage' after the grace: the parcel is
#                      lost between the door and their hub. This is the claim
#                      list — the manifest is our proof, the carrier owes an
#                      answer. Alert to dispatch + manager.
#   theirs, not ours   the carrier is moving or has delivered a parcel that
#                      never met our door scanner (measured: 13 of 76 in the
#                      handover zone, 12 of them one exchange list handed over
#                      four days before its pick list existed). The parcel is
#                      out; the record is closed with a reconstructed manifest
#                      so the order ships and invoices like any other, and the
#                      leak stays visible as a count — it is a discipline
#                      fault even when the parcel arrives.
#   neither            still in the building: the handover zone's job.

_RECON = "lp_carrier_recon"
_RECON_DAYS = 7
_UNACK_GRACE_H = 24         # the carrier collects in the evening; judge next day
_LEAK_MIN_AGE_H = 3          # printed this long ago and the carrier already has it
_WAITING = ("En Attente Ramassage", "En attente de récupération", "")


def _carrier_statuses(awbs):
    from codx_erp.codx_erp.report.cathedis_status_comparison.cathedis_status_comparison import (
        fetch_cathedis_statuses_by_awb)
    return fetch_cathedis_statuses_by_awb([a for a in awbs if a])


def _manifested_rows(days):
    return frappe.db.sql(
        """SELECT sh.name AS shipment, sh.pickup_date, sh.modified AS closed_at,
                  dn.name AS dn, dn.custom_awb AS awb, dn.customer_name AS customer,
                  dn.grand_total AS value, dn.custom_track_shipment_status AS our_status,
                  (SELECT dni.against_sales_order FROM `tabDelivery Note Item` dni
                   WHERE dni.parent = dn.name AND dni.against_sales_order IS NOT NULL LIMIT 1) AS so
           FROM `tabShipment` sh
           JOIN `tabShipment Delivery Note` sdn ON sdn.parent = sh.name
           JOIN `tabDelivery Note` dn ON dn.name = sdn.delivery_note AND dn.docstatus = 1
           WHERE sh.docstatus = 1 AND sh.delivery_customer = 'CATHEDIS'
             AND sh.pickup_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
             AND COALESCE(dn.custom_awb, '') <> ''""", (days,), as_dict=True)


def _unmanifested_rows():
    """Printed parcels the door never scanned (the handover zone's waiting set)."""
    return frappe.db.sql(
        """SELECT DISTINCT so.name AS so, so.customer_name AS customer, so.custom_awb AS awb,
                  dn.name AS dn, dn.grand_total AS value, pl.name AS pick_list,
                  GREATEST(so.modified, dn.creation) AS printed_at
           FROM `tabPick List` pl
           JOIN `tabPick List Item` pli ON pli.parent = pl.name
           JOIN `tabSales Order` so ON so.name = pli.sales_order
           JOIN `tabDelivery Note Item` dni ON dni.against_sales_order = so.name
           JOIN `tabDelivery Note` dn ON dn.name = dni.parent AND dn.docstatus = 1
           WHERE pl.docstatus = 1 AND pl.creation >= DATE_SUB(NOW(), INTERVAL 14 DAY)
             AND so.custom_logistics_status = 'Label Printed'
             AND COALESCE(so.custom_sales_status, '') <> 'Cancelled'
             AND COALESCE(dn.custom_awb, '') <> ''
             AND NOT EXISTS (SELECT 1 FROM `tabShipment Delivery Note` sdn
                             JOIN `tabShipment` sh ON sh.name = sdn.parent AND sh.docstatus < 2
                             WHERE sdn.delivery_note = dn.name)""", as_dict=True)


def reconcile(days=_RECON_DAYS):
    """Compute the four-way match and store it for the pages. Returns it."""
    from frappe.utils import time_diff_in_hours
    now = now_datetime()
    ours = _manifested_rows(days)
    theirs_only_cands = _unmanifested_rows()
    statuses = _carrier_statuses([r.awb for r in ours] + [r.awb for r in theirs_only_cands])

    manifests, unack = {}, []
    for r in ours:
        m = manifests.setdefault(r.shipment, {"shipment": r.shipment, "date": str(r.pickup_date or "")[:10],
                                              "parcels": 0, "acknowledged": 0, "waiting": 0, "unacknowledged": 0,
                                              "notFound": 0})
        m["parcels"] += 1
        st = statuses.get(r.awb)
        age_h = time_diff_in_hours(now, r.closed_at) if r.closed_at else 0
        if st is None:
            m["notFound"] += 1
            st = "(not found)"
        if st in _WAITING or st == "(not found)":
            if age_h >= _UNACK_GRACE_H:
                m["unacknowledged"] += 1
                unack.append({"shipment": r.shipment, "date": m["date"], "order": r.so or "", "dn": r.dn,
                              "awb": r.awb, "customer": r.customer or "", "value": float(r.value or 0),
                              "carrier": st, "hours": int(age_h)})
            else:
                m["waiting"] += 1
        else:
            m["acknowledged"] += 1

    leaked = []
    for r in theirs_only_cands:
        st = statuses.get(r.awb)
        if not st or st in _WAITING:
            continue
        age_h = time_diff_in_hours(now, r.printed_at) if r.printed_at else 0
        if age_h < _LEAK_MIN_AGE_H:
            continue
        leaked.append({"order": r.so, "dn": r.dn, "awb": r.awb, "customer": r.customer or "",
                       "value": float(r.value or 0), "pickList": r.pick_list, "carrier": st,
                       "hours": int(age_h), "exchange": str(r.so).endswith("-ex")})

    unack.sort(key=lambda x: (-x["hours"], x["shipment"]))
    out = {"at": str(now)[:19], "days": days, "graceH": _UNACK_GRACE_H,
           "manifests": sorted(manifests.values(), key=lambda m: m["date"], reverse=True),
           "unacknowledged": unack[:300], "unackN": len(unack),
           "unackValue": round(sum(x["value"] for x in unack)),
           "leaked": leaked[:300], "leakedN": len(leaked)}
    frappe.db.set_default(_RECON, json.dumps(out, default=str))
    return out


@frappe.whitelist()
def reconciliation():
    """The stored match for the manifest page (computed by the hourly run)."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("packer", "dispatcher", "manager"):
        frappe.throw("Not authorized.", frappe.PermissionError)
    raw = frappe.db.get_default(_RECON)
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def close_leaks(leaked):
    """The parcels the carrier has but our door never scanned: one
    reconstructed Cathedis manifest, submitted, so the orders ship and
    invoice like every other parcel — with the reconstruction named on it."""
    if not leaked:
        return None
    from logistics_portal.api.shipping import _new_manifest_shell, _bust_ship_caches
    from logistics_portal.api.locks import named_lock
    dns = []
    for x in leaked:
        if frappe.db.sql("""SELECT 1 FROM `tabShipment Delivery Note` sdn JOIN `tabShipment` sh ON sh.name = sdn.parent
                            WHERE sdn.delivery_note = %s AND sh.docstatus < 2 LIMIT 1""", (x["dn"],)):
            continue
        dns.append(x)
    if not dns:
        return None
    with named_lock("manifest", timeout=30):
        sh = _new_manifest_shell()
        for x in dns:
            sh.append("shipment_delivery_note", {"delivery_note": x["dn"], "grand_total": x["value"]})
        sh.value_of_goods = round(sum(x["value"] for x in dns), 2)
        sh.flags.ignore_permissions = True
        sh.insert(ignore_permissions=True)
        sh.add_comment("Comment", f"Reconstructed from the carrier's own scans on {nowdate()}: "
                                  f"{len(dns)} parcels the carrier is moving or has delivered that never met the "
                                  f"door scanner. Orders: " + ", ".join(x["order"] for x in dns[:40]))
        sh.submit()
        frappe.db.commit()
    for x in dns:
        try:
            frappe.get_doc("Sales Order", x["order"]).add_comment(
                "Comment", f"Handover recorded from the carrier's scan ({x['carrier']}), not from our door — "
                           f"the parcel left without a manifest scan · {sh.name}")
        except Exception:
            pass
    _bust_ship_caches()
    return sh.name


# ── One parcel, right now ─────────────────────────────────────────────────

def _carrier_events(logs_info, limit=12):
    """Cathedis' own log for one parcel, newest first, as short lines:
    status changes, hub receipts, driver assignment, calls, messages."""
    import re
    out = []
    for entry in (logs_info or {}).get("data", []) or []:
        for lg in (entry.get("values") or {}).get("logs", []) or []:
            at = (lg.get("createdOn") or "")[:16].replace("T", " ")
            subject = (lg.get("subject") or "").strip()
            body = lg.get("body") or ""
            text = ""
            if body.startswith("{"):
                try:
                    b = json.loads(body)
                    for tr in b.get("tracks", []) or []:
                        if tr.get("name") == "deliveryStatus":
                            text = f"{tr.get('oldValue') or ''} → {tr.get('value') or ''}".strip(" →")
                        elif tr.get("name") == "appointmentDate" and not text:
                            text = f"Appointment {tr.get('value') or ''}"
                        elif tr.get("name") == "returnStatus" and not text:
                            text = f"Return {tr.get('value') or ''}"
                    if b.get("title") == "Record created" and text:
                        text = f"Created · {text}"
                    elif not text and b.get("title") and b["title"] != "Record updated":
                        text = b["title"]
                except Exception:
                    text = ""
            elif body and len(body) < 160:
                text = body.strip()
            generic = subject in ("Record updated", "Record created", "")
            line = text if (generic or not subject) else subject
            if not generic and text and text not in subject:
                line = f"{subject} · {text}"
            line = re.sub(r"\s+", " ", line or "").strip()
            if line:
                out.append({"at": at, "who": (lg.get("author") or "").strip(), "text": line[:160]})
    out.sort(key=lambda x: x["at"], reverse=True)
    return out[:limit]


@frappe.whitelist(methods=["POST"])
def check_parcel(order):
    """Ask the carrier about ONE parcel now: write its current status through
    the same path the webhook uses, and return the carrier's own log for the
    page. Any portal role — the person holding the phone needs the truth."""
    from logistics_portal.api.permissions import require_portal_user
    require_portal_user()
    order = (order or "").strip()
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    trk = frappe.db.get_value("Sales Order", order, "custom_tracking_number") or frappe.db.sql(
        """SELECT dn.custom_tracking_number FROM `tabDelivery Note` dn
           JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
           WHERE dni.against_sales_order = %s AND dn.docstatus = 1
             AND COALESCE(dn.custom_tracking_number, '') <> ''
           ORDER BY dn.creation DESC LIMIT 1""", (order,))
    trk = trk[0][0] if isinstance(trk, (list, tuple)) and trk else trk
    trk = str(trk or "").strip()
    if not trk:
        return {"ok": False, "reason": "no_tracking"}
    from ecommerce_integrations.tasks.tracking_shipment import resync_sales_order_tracking
    from ecommerce_integrations.shipping.cathedis import CathedisShipping
    res = resync_sales_order_tracking(order, trk) or {}
    frappe.db.commit()
    cat = CathedisShipping()
    events = []
    try:
        events = _carrier_events(cat.get_delivery_logs(trk).get("logs_info"))
    except Exception:
        events = []
    carrier_name = frappe.db.get_value("Shipment Tracking", {"sales_order": order}, "delivery_status_name",
                                       order_by="creation desc") or ""
    status = frappe.db.get_value("Sales Order", order, "custom_track_shipment_status") or ""
    try:
        from logistics_portal.api.shipments import invalidate_cache
        invalidate_cache()
    except Exception:
        pass
    return {"ok": True, "order": order, "tracking": trk, "status": status,
            "carrierStatus": (carrier_name or "").strip(), "changed": res.get("status") == "inserted",
            "events": events, "checkedAt": str(now_datetime())[:16]}


# ── Webhook replay: the carrier DID tell us, our door slammed on the name ──
#
# Measured 2026-09-16: Cathedis pushes every status change to
# ecommerce_integrations' webhook, for every order. The handler prefixes a
# '#' to any order name that lacks one — right for Shopify orders
# ('#260009'), wrong for 'J-006902' and 'SAL-ORD-2026-03307' — and answers
# 404 'Sales Order not found'. Three days: 3,727 pushes rejected, 3,308 of
# them J- orders, 409 SAL-ORD; every '#' order accepted. Each rejected call
# is kept whole in Shipment Delivery Logs, so the status the carrier sent
# can be applied after the fact, here, without asking the carrier again —
# and keeps being applied hourly until the handler itself is fixed.

_REPLAY_MARK = " | replayed by portal"


def _resolve_order_name(raw):
    s = str(raw or "").strip()
    if not s:
        return None
    if frappe.db.exists("Sales Order", s):
        return s
    if s.startswith("#") and frappe.db.exists("Sales Order", s[1:]):
        return s[1:]
    if not s.startswith("#") and frappe.db.exists("Sales Order", "#" + s):
        return "#" + s
    return None


def replay_rejected_webhooks(hours=48, limit=2000):
    """Apply the carrier pushes the webhook turned away. Newest per order
    wins (a parcel's status is its latest event); each log row is marked so
    it is never replayed twice. Returns counts."""
    rows = frappe.db.sql(
        """SELECT name, body, creation FROM `tabShipment Delivery Logs`
           WHERE author = 'Cathedis Webhook API'
             AND subject LIKE 'Cathedis Shipment Webhook: Failed%%'
             AND summary LIKE 'Sales Order not found%%'
             AND summary NOT LIKE %s
             AND creation >= DATE_SUB(NOW(), INTERVAL %s HOUR)
           ORDER BY creation DESC LIMIT %s""",
        ("%" + _REPLAY_MARK + "%", int(hours), int(limit)), as_dict=True)
    if not rows:
        return {"seen": 0, "applied": 0, "unresolved": 0}
    from ecommerce_integrations.ecommerce_integrations.api.shipment_tracking import (
        _apply_tracking_update_from_webhook)
    applied, unresolved, done_orders = 0, 0, set()
    for r in rows:
        try:
            body = json.loads(r.body or "{}")
            payload = body.get("payload") if isinstance(body, dict) else None
            if not isinstance(payload, dict):
                continue
            so = _resolve_order_name(payload.get("sales_order"))
            if not so:
                unresolved += 1
                continue
            if so in done_orders:
                # An older push for an order whose latest push already
                # landed: nothing to apply, but marked so it is not re-read.
                frappe.db.set_value("Shipment Delivery Logs", r.name, "summary",
                                    (frappe.db.get_value("Shipment Delivery Logs", r.name, "summary") or "")
                                    + _REPLAY_MARK + " (superseded)", update_modified=False)
                continue
            payload["sales_order"] = so
            _apply_tracking_update_from_webhook(so, payload.get("tracking_number"), payload)
            done_orders.add(so)
            frappe.db.set_value("Shipment Delivery Logs", r.name, "summary",
                                (frappe.db.get_value("Shipment Delivery Logs", r.name, "summary") or "")
                                + _REPLAY_MARK, update_modified=False)
            applied += 1
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback()[-1500:], f"carrier_sync.replay {r.name}")
    return {"seen": len(rows), "applied": applied, "unresolved": unresolved}


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
        # First what the carrier already told us and the webhook refused.
        try:
            out["replay"] = replay_rejected_webhooks()
        except Exception:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback()[-2000:], "carrier_sync.replay")
        res = _resync(add_days(nowdate(), -_DAYS), nowdate()) or {}
        frappe.db.commit()
        out.update({"ok": True, "processed": int(res.get("processed") or 0),
                    "inserted": int(res.get("inserted") or 0),
                    "skipped": int(res.get("skipped") or 0),
                    "errors": len(res.get("errors") or []) if isinstance(res.get("errors"), list) else int(res.get("errors") or 0),
                    "pendingBefore": before, "pendingAfter": _pending_count()})
        # Then the match from both sides, and its two consequences.
        try:
            rec = reconcile()
            frappe.db.commit()
            out["unacknowledged"] = rec["unackN"]
            out["leaked"] = rec["leakedN"]
            if rec["leaked"]:
                out["reconstructed"] = close_leaks(rec["leaked"])
                rec = reconcile()
                frappe.db.commit()
            if rec["unackN"]:
                from logistics_portal.api.shipments import _emit
                oldest = rec["unacknowledged"][0]
                _emit("carrier_unack", {"n": rec["unackN"], "value": rec["unackValue"],
                                        "shipment": oldest["shipment"], "hours": oldest["hours"]},
                      severity="critical", cooldown_h=6, audience=("dispatcher", "manager"))
        except Exception:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback()[-2500:], "carrier_sync.reconcile")
        out["seconds"] = int((now_datetime() - started).total_seconds())
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
