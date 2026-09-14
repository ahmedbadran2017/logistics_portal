"""Floor Pulse — every open pick list as one line with its seven doors, for
the manager who has to see a stall the minute it starts.

Nothing here is typed in by hand. Every door already leaves a witness:
the list's creation (dispatcher), its assigned picker, one LP Scan Event
per unit at the pick and sort stations, the submit (a Version row), the
Delivery Note (the carrier label), the pack station (Label Printed + a
'pack' scan event since 2026-09-14), the Shipment (the manifest) and the
carrier's first status. Measured on prod over 14 days (697 lists):
created→first scan 23 min, picking 5 min, submit→label 2 min,
label→manifest 150 min — the floor is fast, the wait for the van is long.

A list is 'stuck' when its current door has been open longer than the
door's threshold; the thresholds are settings a manager tunes.
"""

import json

import frappe
from frappe.utils import now_datetime

from logistics_portal.api import clock

STAGES = ("to_pick", "picking", "sorting", "label", "packed", "manifest", "shipped")

_DEFAULTS = {
    "startMin": 15,      # created, nobody has scanned yet
    "silentMin": 10,     # picking, last scan this long ago
    "pickMin": 45,       # picking, since the first scan
    "sortMin": 20,       # submitted, sorting not finished
    "labelMin": 10,      # sorted, no carrier label yet
    "packMin": 30,       # labelled, not packed/printed
    "manifestMin": 90,   # packed, not on a manifest
    "hours": 24,         # how far back finished lists are shown
}
_KEY = "lp_pulse_settings"


def _gate():
    from logistics_portal.api.auth import resolve_role
    from logistics_portal.api.permissions import is_ops_admin
    if is_ops_admin():
        return
    if resolve_role(frappe.session.user) not in ("manager", "dispatcher"):
        frappe.throw("lp:managerOnly", frappe.PermissionError)


def settings():
    raw = frappe.db.get_default(_KEY)
    cfg = dict(_DEFAULTS)
    if raw:
        try:
            v = json.loads(raw)
            for k in _DEFAULTS:
                if k in v:
                    cfg[k] = int(v[k])
        except Exception:
            pass
    return cfg


@frappe.whitelist(methods=["POST"])
def save_settings(payload=None):
    _gate()
    if isinstance(payload, str):
        payload = json.loads(payload or "{}")
    cfg = settings()
    for k in _DEFAULTS:
        if k in (payload or {}):
            cfg[k] = max(1, min(int(payload[k] or _DEFAULTS[k]), 1440))
    frappe.db.set_default(_KEY, json.dumps(cfg))
    frappe.db.commit()
    return cfg


_SNOOZE = "lp_pulse_snooze"


def _snoozes():
    raw = frappe.db.get_default(_SNOOZE)
    try:
        v = json.loads(raw) if raw else {}
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _snoozed_until(name, now):
    v = _snoozes().get(name)
    if not v:
        return None
    try:
        until = frappe.utils.get_datetime(v)
    except Exception:
        return None
    return until if until > now else None


_NUDGE = {
    "en": ("A word from the floor manager", "{note}"),
    "fr": ("Un mot du responsable", "{note}"),
    "ar": ("كلمة من مدير المخزن", "{note}"),
}


@frappe.whitelist(methods=["POST"])
def nudge(user, pick_list="", note=""):
    """Manager/dispatcher: tap someone on the shoulder — a bell alert on
    their portal naming the list, plus a comment on the list itself."""
    _gate()
    user = (user or "").strip()
    if not user or not frappe.db.exists("User", user):
        frappe.throw("Unknown user.")
    pick_list = (pick_list or "").strip()
    note = (note or "").strip()[:200]
    who = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
    body = note or (f"{pick_list}" if pick_list else "")
    i18n = {k: {"t": t, "b": (f"{pick_list} — " if pick_list and note else "") + b.format(note=body)} for k, (t, b) in _NUDGE.items()}
    packed = json.dumps({"lp": i18n, "sev": "warning", "kind": "nudge"}, ensure_ascii=False)
    try:
        frappe.get_doc({
            "doctype": "Notification Log", "subject": i18n["en"]["t"] + (f" · {pick_list}" if pick_list else ""),
            "email_content": i18n["en"]["b"] + f" — {who}\n<!--lp-i18n " + packed.replace("--", "- -") + " -->",
            "type": "Alert", "document_type": "Pick List" if pick_list else "Sales Order",
            "document_name": pick_list or None, "for_user": user,
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback()[-1200:], "pulse.nudge")
    try:
        frappe.publish_realtime("logistics_alert", {"severity": "warning", "title": i18n["en"]["t"], "detail": i18n["en"]["b"],
                                                    "i18n": i18n, "audience": "user"}, user=user)
    except Exception:
        pass
    if pick_list and frappe.db.exists("Pick List", pick_list):
        try:
            frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "Pick List",
                            "reference_name": pick_list,
                            "content": f"Pulse: {who} nudged {user}" + (f" — {note}" if note else "")}).insert(ignore_permissions=True)
        except Exception:
            pass
    frappe.db.commit()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def reassign(pick_list, picker=None):
    """Manager/dispatcher: hand a draft list to another picker (or nobody)."""
    _gate()
    from logistics_portal.api.picking import assign_picker
    res = assign_picker(pick_list, picker)
    frappe.db.commit()
    return res


@frappe.whitelist(methods=["POST"])
def snooze(pick_list, minutes=30, note=""):
    """Manager/dispatcher: 'I know, handled' — the stall mark rests for a
    while; the list stays on the board with a snoozed chip."""
    _gate()
    pick_list = (pick_list or "").strip()
    if not frappe.db.exists("Pick List", pick_list):
        frappe.throw("Unknown pick list.")
    minutes = max(5, min(int(minutes or 30), 24 * 60))
    until = frappe.utils.add_to_date(now_datetime(), minutes=minutes)
    v = _snoozes()
    # drop expired entries while here
    v = {k: x for k, x in v.items() if frappe.utils.get_datetime(x) > now_datetime()}
    v[pick_list] = str(until)[:19]
    frappe.db.set_default(_SNOOZE, json.dumps(v))
    try:
        frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "Pick List",
                        "reference_name": pick_list,
                        "content": f"Pulse: snoozed {minutes} min by {frappe.session.user}" + (f" — {(note or '').strip()[:200]}" if note else "")}).insert(ignore_permissions=True)
    except Exception:
        pass
    frappe.db.commit()
    return {"ok": True, "until": _f(until)}


def _min(a, b):
    """Minutes from a to b (both datetimes), or None."""
    if not a or not b:
        return None
    return int((b - a).total_seconds() // 60)


def _f(dt):
    return str(clock.to_floor(dt))[:16] if dt else ""


@frappe.whitelist()
def board(hours=None, stage="", who="", stuck=0, q="", internal=False):
    """Every pick list of the window with its doors, stage, age and stall."""
    if not internal:
        _gate()
    cfg = settings()
    hours = min(max(int(hours or cfg["hours"]), 1), 24 * 7)
    now = now_datetime()
    heads = frappe.db.sql(
        """SELECT pl.name, pl.creation, pl.modified, pl.owner, pl.docstatus, pl.status,
                  pl.custom_assigned_picker AS picker,
                  COUNT(DISTINCT pli.sales_order) AS orders, COUNT(pli.name) AS n_lines,
                  COALESCE(SUM(pli.qty), 0) AS qty,
                  COALESCE(SUM(pli.custom_scanned_qty), 0) AS scanned,
                  COALESCE(SUM(pli.custom_sorted_qty), 0) AS sorted_qty
           FROM `tabPick List` pl JOIN `tabPick List Item` pli ON pli.parent = pl.name
           WHERE pl.docstatus < 2 AND COALESCE(pl.status, '') != 'Cancelled'
             AND (pl.creation >= DATE_SUB(NOW(), INTERVAL %(h)s HOUR)
                  OR (pl.docstatus = 0 AND pl.creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)))
           GROUP BY pl.name ORDER BY pl.creation DESC LIMIT 400""",
        {"h": hours}, as_dict=True)
    if not heads:
        return {"rows": [], "stages": {s: {"n": 0, "stuck": 0, "oldestMin": 0} for s in STAGES},
                "people": [], "now": _f(now), "settings": cfg}
    names = tuple(h.name for h in heads)

    # The witnesses, one query each, grouped by list.
    scans = {r.pick_list: r for r in frappe.db.sql(
        """SELECT pick_list,
                  MIN(CASE WHEN station = 'pick' THEN creation END) AS pick_first,
                  MAX(CASE WHEN station = 'pick' THEN creation END) AS pick_last,
                  MIN(CASE WHEN station = 'sort' THEN creation END) AS sort_first,
                  MAX(CASE WHEN station = 'sort' THEN creation END) AS sort_last,
                  MIN(CASE WHEN station = 'pack' THEN creation END) AS pack_first,
                  MAX(CASE WHEN station = 'pack' THEN creation END) AS pack_last,
                  MAX(CASE WHEN station = 'pick' THEN owner END) AS pick_who,
                  MAX(CASE WHEN station = 'sort' THEN owner END) AS sort_who,
                  MAX(CASE WHEN station = 'pack' THEN owner END) AS pack_who
           FROM `tabLP Scan Event` WHERE pick_list IN %s GROUP BY pick_list""", (names,), as_dict=True)}
    submits = {r.docname: r.t for r in frappe.db.sql(
        """SELECT docname, MIN(creation) AS t FROM `tabVersion`
           WHERE ref_doctype = 'Pick List' AND docname IN %s AND data LIKE '%%"docstatus",0,1%%'
           GROUP BY docname""", (names,), as_dict=True)}
    # Orders of each list → labels (DN with AWB), packed (status), manifest, carrier.
    so_rows = frappe.db.sql(
        """SELECT pli.parent AS pl, pli.sales_order AS so, so.custom_logistics_status AS lstat,
                  dn.name AS dn, dn.creation AS dn_at, NULLIF(dn.custom_awb, '') AS awb,
                  dn.custom_track_shipment_status AS track, dn.custom_assigned_packer AS packer,
                  sh.creation AS man_at, sh.name AS shipment
           FROM (SELECT DISTINCT parent, sales_order FROM `tabPick List Item` WHERE parent IN %s) pli
           LEFT JOIN `tabSales Order` so ON so.name = pli.sales_order
           LEFT JOIN (SELECT dni.against_sales_order AS so, MIN(d.name) AS name
                      FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name = dni.parent
                      WHERE d.docstatus < 2 AND d.is_return = 0 AND dni.against_sales_order IN
                            (SELECT sales_order FROM `tabPick List Item` WHERE parent IN %s)
                      GROUP BY dni.against_sales_order) dl ON dl.so = pli.sales_order
           LEFT JOIN `tabDelivery Note` dn ON dn.name = dl.name
           LEFT JOIN (SELECT sdn.delivery_note AS dn, MIN(s.creation) AS creation, MIN(s.name) AS name
                      FROM `tabShipment Delivery Note` sdn JOIN `tabShipment` s ON s.name = sdn.parent
                      WHERE s.docstatus = 1 GROUP BY sdn.delivery_note) sh ON sh.dn = dn.name""",
        (names, names), as_dict=True)
    per = {}
    for r in so_rows:
        p = per.setdefault(r.pl, {"orders": 0, "labels": 0, "label_first": None, "label_last": None,
                                  "packed": 0, "manifested": 0, "man_first": None, "man_last": None,
                                  "shipped": 0, "packers": set(), "shipments": set(), "sos": []})
        p["orders"] += 1
        p["sos"].append(r.so)
        if r.awb:
            p["labels"] += 1
            p["label_first"] = min(p["label_first"] or r.dn_at, r.dn_at)
            p["label_last"] = max(p["label_last"] or r.dn_at, r.dn_at)
        if (r.lstat or "") in ("Label Printed", "Shipped", "In Transit", "Delivered", "Returned") or r.man_at:
            p["packed"] += 1
        if r.packer:
            p["packers"].add(r.packer)
        if r.man_at:
            p["manifested"] += 1
            p["man_first"] = min(p["man_first"] or r.man_at, r.man_at)
            p["man_last"] = max(p["man_last"] or r.man_at, r.man_at)
            p["shipments"].add(r.shipment)
        if (r.track or "Pending") != "Pending" or (r.lstat or "") in ("Shipped", "In Transit", "Delivered", "Returned"):
            p["shipped"] += 1

    users = set()
    rows = []
    for h in heads:
        s = scans.get(h.name) or frappe._dict()
        p = per.get(h.name) or {"orders": int(h.orders or 0), "labels": 0, "label_first": None, "label_last": None,
                                "packed": 0, "manifested": 0, "man_first": None, "man_last": None,
                                "shipped": 0, "packers": set(), "shipments": set(), "sos": []}
        orders = max(int(h.orders or 0), 1)
        qty = float(h.qty or 0)
        scanned = min(float(h.scanned or 0), qty)
        sorted_qty = min(float(h.sorted_qty or 0), qty)
        submitted = submits.get(h.name) or (h.modified if h.docstatus == 1 else None)
        needs_sort = orders > 1
        # Which door is open, and since when.
        if h.docstatus == 0 and not s.get("pick_first") and scanned == 0:
            stage, since = "to_pick", h.creation
        elif h.docstatus == 0:
            stage, since = "picking", s.get("pick_first") or h.creation
        elif needs_sort and sorted_qty < qty and p["labels"] < orders:
            stage, since = "sorting", submitted or h.modified
        elif p["labels"] < orders:
            stage, since = "label", (s.get("sort_last") if needs_sort else None) or submitted or h.modified
        elif p["packed"] < orders:
            stage, since = "packed", p["label_last"] or submitted
        elif p["manifested"] < orders:
            stage, since = "manifest", s.get("pack_last") or p["label_last"] or submitted
        else:
            stage, since = "shipped", p["man_last"] or submitted
        age = _min(since, now) or 0
        # The stall rules, one per door.
        reason = ""
        if stage == "to_pick" and age > cfg["startMin"]:
            reason = "start"
        elif stage == "picking":
            silent = _min(s.get("pick_last"), now)
            if silent is not None and silent > cfg["silentMin"]:
                reason = "silent"
            elif age > cfg["pickMin"]:
                reason = "slow"
        elif stage == "sorting" and age > cfg["sortMin"]:
            reason = "sort"
        elif stage == "label" and age > cfg["labelMin"]:
            reason = "label"
        elif stage == "packed" and age > cfg["packMin"]:
            reason = "pack"
        elif stage == "manifest" and age > cfg["manifestMin"]:
            reason = "manifest"
        snoozed = _snoozed_until(h.name, now)
        if snoozed and reason:
            reason = ""
        people = {"picker": h.picker or s.get("pick_who") or "", "sorter": s.get("sort_who") or "",
                  "packer": s.get("pack_who") or (sorted(p["packers"])[0] if p["packers"] else "")}
        users.update(u for u in [h.owner, *people.values()] if u)
        rows.append({
            "name": h.name, "createdAt": _f(h.creation), "createdBy": h.owner or "",
            "docstatus": h.docstatus, "orders": int(h.orders or 0), "lines": int(h.n_lines or 0), "qty": int(qty),
            "picker": people["picker"], "sorter": people["sorter"], "packer": people["packer"],
            "stage": stage, "since": _f(since), "ageMin": age, "reason": reason,
            "snoozedUntil": _f(snoozed) if snoozed else "",
            "silentMin": _min(s.get("pick_last"), now) if stage == "picking" else None,
            "doors": {
                "to_pick": {"at": _f(h.creation), "done": True},
                "picking": {"at": _f(s.get("pick_first")), "done": h.docstatus == 1, "n": int(scanned), "of": int(qty),
                            "last": _f(s.get("pick_last")), "min": _min(s.get("pick_first"), submitted or s.get("pick_last"))},
                "sorting": {"at": _f(s.get("sort_first")), "done": (not needs_sort) or sorted_qty >= qty or p["labels"] >= orders,
                            "n": int(sorted_qty), "of": int(qty), "skip": not needs_sort, "min": _min(s.get("sort_first"), s.get("sort_last"))},
                "label": {"at": _f(p["label_first"]), "done": p["labels"] >= orders, "n": p["labels"], "of": orders},
                "packed": {"at": _f(s.get("pack_first")), "done": p["packed"] >= orders, "n": p["packed"], "of": orders},
                "manifest": {"at": _f(p["man_first"]), "done": p["manifested"] >= orders, "n": p["manifested"], "of": orders,
                             "shipments": sorted(p["shipments"])},
                "shipped": {"at": "", "done": p["shipped"] >= orders, "n": p["shipped"], "of": orders},
            },
            "orderNames": p["sos"][:12],
        })

    names_map = {}
    if users:
        names_map = dict(frappe.db.sql("SELECT name, full_name FROM `tabUser` WHERE name IN %s", (tuple(users),)))
    def short(u):
        return (names_map.get(u) or (u or "").split("@")[0]) if u else ""
    for r in rows:
        r["createdByName"] = short(r["createdBy"])
        r["pickerName"] = short(r["picker"])
        r["sorterName"] = short(r["sorter"])
        r["packerName"] = short(r["packer"])

    # The strip on top: how many lists stand at each door, the oldest, the stuck.
    strip = {s: {"n": 0, "stuck": 0, "oldestMin": 0} for s in STAGES}
    for r in rows:
        st = strip[r["stage"]]
        st["n"] += 1
        if r["reason"]:
            st["stuck"] += 1
        st["oldestMin"] = max(st["oldestMin"], r["ageMin"])
    # People on the floor right now: last scan, current list.
    people = frappe.db.sql(
        """SELECT owner, station, MAX(creation) AS last_at, COUNT(*) AS n_today
           FROM `tabLP Scan Event` WHERE creation >= DATE_SUB(NOW(), INTERVAL 12 HOUR)
           GROUP BY owner, station ORDER BY last_at DESC""", as_dict=True)
    ppl = {}
    for x in people:
        d = ppl.setdefault(x.owner, {"user": x.owner, "name": short(x.owner) or (x.owner or "").split("@")[0],
                                     "stations": {}, "lastAt": None, "idleMin": None})
        d["stations"][x.station] = int(x.n_today or 0)
        if not d["lastAt"] or x.last_at > d["lastAt"]:
            d["lastAt"] = x.last_at
    for d in ppl.values():
        d["idleMin"] = _min(d["lastAt"], now)
        d["lastAt"] = _f(d["lastAt"])
        d["current"] = next((r["name"] for r in rows if r["stage"] == "picking" and r["picker"] == d["user"]), "")

    # Filters are applied last so the strip always shows the whole floor.
    out = rows
    if stage in STAGES:
        out = [r for r in out if r["stage"] == stage]
    if who:
        out = [r for r in out if who in (r["picker"], r["sorter"], r["packer"], r["createdBy"])]
    if int(stuck or 0):
        out = [r for r in out if r["reason"]]
    if q and str(q).strip():
        qq = str(q).strip().lower()
        out = [r for r in out if qq in r["name"].lower() or any(qq in (o or "").lower() for o in r["orderNames"])]
    order = {s: i for i, s in enumerate(STAGES)}
    out.sort(key=lambda r: (0 if r["reason"] else 1, order[r["stage"]], -r["ageMin"]))
    try:
        from logistics_portal.api.picking import pickers as _pickers
        picker_opts = [{"email": x["email"], "name": x["name"], "load": x["load"]} for x in _pickers()]
    except Exception:
        picker_opts = []
    return {"rows": out[:250], "total": len(rows), "stages": strip, "pickers": picker_opts,
            "people": sorted(ppl.values(), key=lambda d: (d["idleMin"] if d["idleMin"] is not None else 9999)),
            "now": _f(now), "settings": cfg}


# ---------------------------------------------------------------------------
# Phase 3 — the bell rings before the manager looks, and the thresholds come
# from what the floor actually does.
# ---------------------------------------------------------------------------

_REASON_KIND = {"start": "pulse_start", "silent": "pulse_silent", "slow": "pulse_silent", "sort": "pulse_sort",
                "label": "pulse_label", "pack": "pulse_pack", "manifest": "pulse_manifest"}
_REASON_MIN = {"start": "startMin", "silent": "silentMin", "slow": "pickMin", "sort": "sortMin",
               "label": "labelMin", "pack": "packMin", "manifest": "manifestMin"}


def run_alerts():
    """Every 10 minutes in floor hours: one bell per kind of stall, to the
    managers and the dispatchers, with the lists named. Dedup and cooldown
    are the alert store's (an unread one is not repeated; a read one waits
    an hour)."""
    try:
        now = clock.floor_now()
        if not (7 <= now.hour < 21):
            return
        from logistics_portal.api.shipments import _emit
        b = board(internal=True)
        cfg = b["settings"]
        groups = {}
        for r in b["rows"]:
            if r["reason"]:
                groups.setdefault(r["reason"], []).append(r)
        for reason, rows in groups.items():
            kind = _REASON_KIND.get(reason)
            if not kind:
                continue
            rows.sort(key=lambda x: -x["ageMin"])
            oldest = rows[0]["ageMin"]
            params = {"n": len(rows), "min": cfg.get(_REASON_MIN[reason], 0),
                      "oldest": f"{oldest // 60}h {oldest % 60:02d}m" if oldest >= 60 else f"{oldest} min",
                      "names": ", ".join(x["name"] for x in rows[:6]) + (" …" if len(rows) > 6 else "")}
            sev = "critical" if (reason in ("start", "manifest") and len(rows) >= 5) or oldest >= 180 else "warning"
            _emit(kind, params, severity=sev, cooldown_h=1, audience=("manager", "dispatcher"))
    except Exception:
        frappe.log_error(frappe.get_traceback()[-2000:], "pulse.run_alerts")


def _pct(vals, q):
    vals = sorted(v for v in vals if v is not None and v >= 0)
    if not vals:
        return None
    return int(vals[min(len(vals) - 1, int(round(q * (len(vals) - 1))))])


@frappe.whitelist()
def measure(days=14):
    """What each door actually takes, from the last `days` of finished
    lists: p50 / p75 / p90 in minutes per threshold key, so a manager sets
    the stall lines from evidence. 'silentMin' is the p90 gap between two
    consecutive pick scans on one list."""
    _gate()
    days = min(max(int(days or 14), 3), 60)
    ck = f"lp_pulse_measure:{days}"
    try:
        hit = frappe.cache().get_value(ck, expires=True)
        if hit:
            return hit
    except Exception:
        pass
    rows = frappe.db.sql(
        """SELECT pl.name, pl.creation,
                  fs.t AS first_pick, ls.t AS last_pick, ss.t AS sort_last,
                  sub.t AS submitted, lab.t AS label_first, labl.t AS label_last,
                  pk.t AS pack_first, man.t AS man_first,
                  (SELECT COUNT(DISTINCT sales_order) FROM `tabPick List Item` WHERE parent = pl.name) AS orders
           FROM `tabPick List` pl
           LEFT JOIN (SELECT pick_list, MIN(creation) t FROM `tabLP Scan Event` WHERE station='pick' GROUP BY pick_list) fs ON fs.pick_list = pl.name
           LEFT JOIN (SELECT pick_list, MAX(creation) t FROM `tabLP Scan Event` WHERE station='pick' GROUP BY pick_list) ls ON ls.pick_list = pl.name
           LEFT JOIN (SELECT pick_list, MAX(creation) t FROM `tabLP Scan Event` WHERE station='sort' GROUP BY pick_list) ss ON ss.pick_list = pl.name
           LEFT JOIN (SELECT pick_list, MIN(creation) t FROM `tabLP Scan Event` WHERE station='pack' GROUP BY pick_list) pk ON pk.pick_list = pl.name
           LEFT JOIN (SELECT docname, MIN(creation) t FROM `tabVersion` WHERE ref_doctype='Pick List' AND data LIKE '%%"docstatus",0,1%%' GROUP BY docname) sub ON sub.docname = pl.name
           LEFT JOIN (SELECT pli.parent pl, MIN(dn.creation) t, MAX(dn.creation) t2 FROM `tabPick List Item` pli
                      JOIN `tabDelivery Note Item` dni ON dni.against_sales_order = pli.sales_order
                      JOIN `tabDelivery Note` dn ON dn.name = dni.parent WHERE dn.docstatus < 2 AND dn.is_return = 0 GROUP BY pli.parent) lab ON lab.pl = pl.name
           LEFT JOIN (SELECT pli.parent pl, MAX(dn.creation) t FROM `tabPick List Item` pli
                      JOIN `tabDelivery Note Item` dni ON dni.against_sales_order = pli.sales_order
                      JOIN `tabDelivery Note` dn ON dn.name = dni.parent WHERE dn.docstatus < 2 AND dn.is_return = 0 GROUP BY pli.parent) labl ON labl.pl = pl.name
           LEFT JOIN (SELECT pli.parent pl, MIN(s.creation) t FROM `tabPick List Item` pli
                      JOIN `tabDelivery Note Item` dni ON dni.against_sales_order = pli.sales_order
                      JOIN `tabShipment Delivery Note` sdn ON sdn.delivery_note = dni.parent
                      JOIN `tabShipment` s ON s.name = sdn.parent WHERE s.docstatus = 1 GROUP BY pli.parent) man ON man.pl = pl.name
           WHERE pl.docstatus = 1 AND pl.creation >= DATE_SUB(NOW(), INTERVAL %s DAY)""", (days,), as_dict=True)
    d = {"startMin": [], "pickMin": [], "sortMin": [], "labelMin": [], "packMin": [], "manifestMin": []}
    for r in rows:
        d["startMin"].append(_min(r.creation, r.first_pick))
        d["pickMin"].append(_min(r.first_pick, r.submitted or r.last_pick))
        if r.orders and r.orders > 1:
            d["sortMin"].append(_min(r.submitted, r.sort_last))
        d["labelMin"].append(_min(r.sort_last or r.submitted, r.label_first))
        d["packMin"].append(_min(r.label_last, r.pack_first))
        d["manifestMin"].append(_min(r.label_last, r.man_first))
    gaps = []
    last = {}
    for e in frappe.db.sql(
            """SELECT pick_list, creation FROM `tabLP Scan Event`
               WHERE station = 'pick' AND creation >= DATE_SUB(NOW(), INTERVAL %s DAY)
               ORDER BY pick_list, creation""", (days,), as_dict=True):
        if e.pick_list in last:
            gaps.append(_min(last[e.pick_list], e.creation))
        last[e.pick_list] = e.creation
    d["silentMin"] = gaps
    out = {}
    for k, vals in d.items():
        vals = [v for v in vals if v is not None]
        out[k] = {"n": len(vals), "p50": _pct(vals, .5), "p75": _pct(vals, .75), "p90": _pct(vals, .9)}
    res = {"days": days, "lists": len(rows), "keys": out}
    try:
        frappe.cache().set_value(ck, res, expires_in_sec=3600)   # 3.2 s on prod over 14 days
    except Exception:
        pass
    return res
