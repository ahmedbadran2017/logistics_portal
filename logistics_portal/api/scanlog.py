"""One row per scan — the floor's heartbeat.

The outbound cycle's middle was a black box: scan_pick and sort_scan write
raw UPDATEs to quantity columns (deliberately, so ERPNext's modified-tracking
doesn't fight the PDA), which means the columns change and NOTHING records
who scanned, when, or how fast. Audited 2026-09-10: picking-to-label runs at
a median 1.1h — the floor is fast — but per-PERSON activity inside that hour
is unknowable: no timeline, no gaps, no scans/hour. Every question the
manager asks about movement ("who was idle 14:00-15:00?") had no data to
answer from.

This log answers it at the only honest grain: the scan itself. Each row is
(station, who=owner, when=creation, pick list, order, item, qty). Writers
never let logging break the scan — a lost log row costs a data point, a
failed scan costs a parcel.

The doctype is created idempotently on migrate (custom doctype, no fixture
files), indexed on (owner, creation) and (station, creation) — the two axes
every activity question slices on.
"""

import frappe

DT = "LP Scan Event"


def log_scan(station, pick_list=None, sales_order=None, item_code=None, qty=1):
    """Fire-and-forget. Called INSIDE hot scan paths; must never raise."""
    try:
        frappe.get_doc({
            "doctype": DT,
            "station": station,
            "pick_list": (pick_list or "")[:140],
            "sales_order": (sales_order or "")[:140],
            "item_code": (item_code or "")[:140],
            "qty": int(qty or 1),
        }).insert(ignore_permissions=True)
    except Exception:
        # The scan already happened physically; the log is a witness, not a
        # gate. Losing one row is better than a picker stuck at a shelf.
        pass


def ensure_doctype():
    """Create the doctype on migrate. Custom doctype: lives in the DB, no
    schema files, safe to run every time."""
    try:
        if frappe.db.exists("DocType", DT):
            return
        frappe.get_doc({
            "doctype": "DocType",
            "name": DT,
            "module": "Core",
            "custom": 1,
            "naming_rule": "Autoincrement",
            "autoname": "autoincrement",
            "fields": [
                {"fieldname": "station", "fieldtype": "Select", "label": "Station",
                 "options": "pick\nsort\nmanifest", "in_standard_filter": 1},
                {"fieldname": "pick_list", "fieldtype": "Data", "label": "Pick List"},
                {"fieldname": "sales_order", "fieldtype": "Data", "label": "Sales Order"},
                {"fieldname": "item_code", "fieldtype": "Data", "label": "Item"},
                {"fieldname": "qty", "fieldtype": "Int", "label": "Qty", "default": "1"},
            ],
            "permissions": [
                {"role": "System Manager", "read": 1, "write": 1, "create": 1},
            ],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "scanlog.ensure_doctype")


def backfill_manifest_history():
    """Seed the log from the one station that always HAD a witness.

    manifest_scan appends a Shipment Delivery Note child row, and child rows
    carry owner + creation — so the manifest station's history exists even
    though nobody wrote it here. Copy the last 30 days in once, and the
    activity screen opens with a month of real manifest data instead of an
    empty room; pick and sort genuinely have no past (raw UPDATEs) and start
    from the deploy. Idempotent via a site-default flag.
    """
    if frappe.db.get_default("lp_scanlog_backfilled"):
        return {"seeded": 0}
    if not frappe.db.exists("DocType", DT):
        return {"seeded": 0}
    rows = frappe.db.sql(
        """SELECT sdn.owner, sdn.creation,
                  (SELECT dni.against_sales_order FROM `tabDelivery Note Item` dni
                   WHERE dni.parent = sdn.delivery_note
                     AND dni.against_sales_order IS NOT NULL LIMIT 1) so
           FROM `tabShipment Delivery Note` sdn
           WHERE sdn.creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)""",
        as_dict=True)
    n = 0
    for r in rows:
        try:
            d = frappe.get_doc({"doctype": DT, "station": "manifest",
                                "sales_order": r.so or "", "qty": 1})
            d.insert(ignore_permissions=True)
            # The witness must carry the ORIGINAL actor and moment, not the
            # migration's — db_set after insert, because insert stamps its own.
            frappe.db.set_value(DT, d.name,
                                {"owner": r.owner, "creation": r.creation},
                                update_modified=False)
            n += 1
        except Exception:
            continue
    frappe.db.set_default("lp_scanlog_backfilled", "1")
    frappe.db.commit()
    return {"seeded": n}


@frappe.whitelist()
def floor_activity(day=None):
    """Per-person movement for one floor day — manager's answer to "who was
    actually working, and when". Timeline at 30-minute grain, scans/hour,
    and the longest silent gap inside their own active span.

    Reads only this log, so it is exactly as honest as the scanners: a person
    whose job has no scanner (dispatcher at a desk) does not appear here and
    must not be judged here.
    """
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Managers only.", frappe.PermissionError)
    from logistics_portal.api import clock
    day = (day or clock.floor_today())[:10]
    d0, d1 = clock.day_bounds(day)
    rows = frappe.db.sql(
        """SELECT owner, station, creation, qty FROM `tabLP Scan Event`
           WHERE creation >= %s AND creation < %s
           ORDER BY owner, creation""", (d0, d1), as_dict=True)
    out = {}
    for r in rows:
        at = clock.to_floor(r.creation)
        p = out.setdefault(r.owner, {
            "user": r.owner, "scans": 0, "units": 0,
            "stations": {}, "first": None, "last": None,
            "slots": {},          # 30-min buckets: "HH:MM" -> scans
            "maxGapMin": 0, "_prev": None})
        p["scans"] += 1
        p["units"] += int(r.qty or 1)
        p["stations"][r.station] = p["stations"].get(r.station, 0) + 1
        t = str(at)[11:16]
        if p["first"] is None:
            p["first"] = t
        p["last"] = t
        slot = "%02d:%02d" % (at.hour, 0 if at.minute < 30 else 30)
        p["slots"][slot] = p["slots"].get(slot, 0) + 1
        if p["_prev"] is not None:
            gap = (at - p["_prev"]).total_seconds() / 60.0
            if gap > p["maxGapMin"]:
                p["maxGapMin"] = int(gap)
        p["_prev"] = at
    # Who are these emails, and when did HR see them arrive? First punch of
    # the floor day, so "clocked in 09:07, first scan 10:40" is one glance.
    users = tuple(out) or ("",)
    emp = {r.user_id: r for r in frappe.db.sql(
        """SELECT user_id, name emp, employee_name FROM `tabEmployee`
           WHERE user_id IN %s""", (users,), as_dict=True)}
    punch = {}
    if emp:
        for r in frappe.db.sql(
                """SELECT e.user_id, MIN(c.time) t
                   FROM `tabEmployee Checkin` c
                   JOIN `tabEmployee` e ON e.name = c.employee
                   WHERE e.user_id IN %s AND c.log_type = 'IN'
                     AND c.time >= %s AND c.time < %s
                   GROUP BY e.user_id""", (users, d0, d1), as_dict=True):
            punch[r.user_id] = str(clock.to_floor(r.t))[11:16]
    people = []
    for p in out.values():
        p.pop("_prev", None)
        p["maxGapMin"] = int(p["maxGapMin"])
        p["name"] = (emp.get(p["user"], {}) or {}).get("employee_name") \
            or p["user"].split("@")[0]
        p["punchIn"] = punch.get(p["user"])
        people.append(p)
    people.sort(key=lambda x: -x["scans"])
    return {"day": day, "people": people, "totalScans": len(rows)}
