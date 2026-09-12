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


@frappe.whitelist(methods=["POST"])
def floor_note(user, day, text):
    """The floor manager's margin note on a person's day — "he was unloading
    the 14:10 truck", "sent to help returns". This is what makes a red card
    fair: the station discipline is the manager's to certify, so their word
    is recorded next to the silence it explains, with their name and the
    moment they wrote it. Stored as a Comment on the Employee record, so it
    outlives this screen and joins the person's own history."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Managers only.", frappe.PermissionError)
    user = (user or "").strip()
    text = (text or "").strip()[:280]
    day = (day or "").strip()[:10]
    if not (user and text and day):
        frappe.throw("Missing note details.")
    emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not emp:
        frappe.throw("No employee record for that user.")
    frappe.get_doc("Employee", emp).add_comment(
        "Comment", f"Floor {day}: {text}")
    frappe.db.commit()
    return {"ok": True}


def silent_now(threshold_min=20):
    """Who on the floor is silent RIGHT NOW — the alert engine's feed.

    A person counts when they hold a scanner-station role, punched in on the
    floor day, and either their last scan is older than the threshold or
    they have scanned nothing at all for twice the threshold since punching
    in. Evaluated only INSIDE the floor's working window (ops floorStart..
    floorEnd): without that fence the engine would cry wolf every evening
    the moment the shift ends, and a wolf-crying alert is muted within a
    week. Returns [{name, user, min, station}], empty outside the window.
    """
    from logistics_portal.api import clock
    from logistics_portal.api.auth import resolve_role
    from logistics_portal.api.settings import get_ops
    fnow = clock.floor_now()
    lo = int(get_ops("floorStart") or 9)
    hi = int(get_ops("floorEnd") or 19)
    # Half an hour of grace at the start: nobody scans at 09:00 sharp.
    if not (lo * 60 + 30 <= fnow.hour * 60 + fnow.minute < hi * 60):
        return []
    day = str(fnow)[:10]
    d0, d1 = clock.day_bounds(day)
    last = {r.owner: r.t for r in frappe.db.sql(
        """SELECT owner, MAX(creation) t FROM `tabLP Scan Event`
           WHERE creation >= %s AND creation < %s GROUP BY owner""",
        (d0, d1), as_dict=True)}
    # System actions count as presence too: a picker mid stock-move must not
    # page as "silent".
    for owner, when, _st, _u in _sys_actions(d0, d1):
        if owner not in last or when > last[owner]:
            last[owner] = when
    st_of = {r.owner: r.st for r in frappe.db.sql(
        """SELECT owner, SUBSTRING_INDEX(GROUP_CONCAT(station ORDER BY creation DESC), ',', 1) st
           FROM `tabLP Scan Event`
           WHERE creation >= %s AND creation < %s GROUP BY owner""",
        (d0, d1), as_dict=True)}
    out = []
    for r in frappe.db.sql(
            """SELECT e.user_id u, e.employee_name nm, MIN(c.time) t
               FROM `tabEmployee Checkin` c
               JOIN `tabEmployee` e ON e.name = c.employee
               WHERE c.log_type = 'IN' AND c.time >= %s AND c.time < %s
                 AND e.user_id IS NOT NULL AND e.user_id != ''
               GROUP BY e.user_id, e.employee_name""", (d0, d1), as_dict=True):
        try:
            if resolve_role(r.u) not in ("picker", "packer", "returns"):
                continue
        except Exception:
            continue
        anchor = last.get(r.u) or r.t
        silent = (fnow - clock.to_floor(anchor)).total_seconds() / 60.0
        limit = threshold_min if r.u in last else threshold_min * 2
        if silent >= limit:
            out.append({"name": r.nm or r.u.split("@")[0], "user": r.u,
                        "min": int(silent),
                        "station": st_of.get(r.u, "")})
    out.sort(key=lambda x: -x["min"])
    return out


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


def _sys_actions(d0, d1):
    """Non-scanner witnesses of floor work (Ahmed 2026-09-11: 'track the
    other actions too — more logical'). A dispatcher building pick lists,
    a supervisor moving stock, a counter filing a reconciliation — all of
    it leaves documents with an owner and a moment, and all of it belongs
    on the same timeline as the scans. Returns [(owner, creation, station,
    units)] with stations: move / receive / count / dispatch."""
    ev = []
    for r in frappe.db.sql(
            """SELECT se.owner, se.creation, se.purpose,
                      (SELECT ROUND(SUM(sed.qty)) FROM `tabStock Entry Detail` sed
                       WHERE sed.parent = se.name) units
               FROM `tabStock Entry` se
               WHERE se.docstatus = 1 AND se.creation >= %s AND se.creation < %s
                 AND se.purpose IN ('Material Transfer', 'Material Receipt')
                 AND se.owner NOT IN ('Administrator', 'Guest')""",
            (d0, d1), as_dict=True):
        st = "move" if r.purpose == "Material Transfer" else "receive"
        ev.append((r.owner, r.creation, st, int(r.units or 1)))
    for r in frappe.db.sql(
            """SELECT owner, creation FROM `tabStock Reconciliation`
               WHERE creation >= %s AND creation < %s AND docstatus < 2
                 AND owner NOT IN ('Administrator', 'Guest')""",
            (d0, d1), as_dict=True):
        ev.append((r.owner, r.creation, "count", 1))
    for r in frappe.db.sql(
            """SELECT owner, creation FROM `tabPick List`
               WHERE creation >= %s AND creation < %s AND docstatus < 2
                 AND owner NOT IN ('Administrator', 'Guest')""",
            (d0, d1), as_dict=True):
        ev.append((r.owner, r.creation, "dispatch", 1))
    return ev


@frappe.whitelist()
def floor_history(days=14):
    """The run of floor days: actions per day, and each person's own line.

    Twin of contact_center.team_history, same shape so the two boards read as
    one language. floor_activity answers "how did today run"; a date picker on
    top of it still hands back one day at a time with nothing to compare
    against, which is not history — this is.

    Deliberately an aggregate: the day board pulls every event row because it
    draws a 30-minute timeline, and a fortnight of that is tens of thousands
    of rows to produce two numbers a day, so the counting happens in SQL. Day
    buckets use the floor's clock, not the site's — the same seam the day
    board reads. Only people who actually did something appear: a punched-but
    silent row is a question about ONE day, and carries no meaning spread
    across a fortnight.
    """
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Managers only.", frappe.PermissionError)
    from logistics_portal.api import clock

    days = min(max(int(days or 14), 2), 60)
    today = clock.floor_today()[:10]
    first = str(frappe.utils.add_days(today, -(days - 1)))[:10]
    d0 = clock.day_bounds(first)[0]
    d1 = clock.day_bounds(today)[1]

    counts = {}

    def bump(owner, day_str, n):
        if not owner or owner in ("Administrator", "Guest"):
            return
        counts.setdefault(owner, {})
        counts[owner][day_str] = counts[owner].get(day_str, 0) + int(n or 0)

    # The scanners.
    for r in frappe.db.sql(
            f"""SELECT owner, {clock.sql_local("creation")} AS d, COUNT(*) AS n
                FROM `tabLP Scan Event`
                WHERE creation >= %s AND creation < %s
                GROUP BY owner, d""", (d0, d1), as_dict=True):
        bump(r.owner, str(r.d), r.n)

    # The system's own witnesses — the same four the day board folds in, so a
    # dispatcher's day is no more invisible here than it is there.
    for table in ("`tabStock Entry`", "`tabStock Reconciliation`",
                  "`tabPick List`"):
        extra = "AND purpose IN ('Material Transfer', 'Material Receipt')" \
            if "Stock Entry" in table else ""
        docst = "= 1" if "Stock Entry" in table else "< 2"
        for r in frappe.db.sql(
                f"""SELECT owner, {clock.sql_local("creation")} AS d,
                           COUNT(*) AS n
                    FROM {table}
                    WHERE creation >= %s AND creation < %s
                      AND docstatus {docst} {extra}
                      AND owner NOT IN ('Administrator', 'Guest')
                    GROUP BY owner, d""", (d0, d1), as_dict=True):
            bump(r.owner, str(r.d), r.n)

    axis = [str(frappe.utils.add_days(first, i))[:10] for i in range(days)]
    totals = {d: {"actions": 0, "people": 0} for d in axis}
    people = []
    for user, by_day in counts.items():
        by_day = {d: n for d, n in by_day.items() if d in totals}
        if not by_day:
            continue
        try:
            role = resolve_role(user) or "none"
        except Exception:
            role = "none"
        for d, n in by_day.items():
            totals[d]["actions"] += n
            totals[d]["people"] += 1
        people.append({
            "user": user, "role": role,
            "name": frappe.db.get_value("User", user, "full_name") or user,
            "total": sum(by_day.values()), "byDay": by_day,
        })
    people.sort(key=lambda p: -p["total"])
    return {
        "days": axis, "today": today,
        "totals": [{"day": d, "actions": totals[d]["actions"],
                    "people": totals[d]["people"]} for d in axis],
        "people": people,
    }


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

    # The system's own witnesses join the same timeline — a move, a receipt,
    # a count, a built pick list. They fill the exact gaps the honesty box
    # apologized for: the dispatcher's day was invisible here.
    sys_ev = sorted(_sys_actions(d0, d1), key=lambda e: (e[0], e[1]))
    for owner, when, st, units in sys_ev:
        at = clock.to_floor(when)
        p = out.setdefault(owner, {
            "user": owner, "scans": 0, "units": 0,
            "stations": {}, "first": None, "last": None,
            "slots": {}, "maxGapMin": 0, "_prev": None})
        p["scans"] += 1
        p["units"] += max(1, int(units or 1))
        p["stations"][st] = p["stations"].get(st, 0) + 1
        t = str(at)[11:16]
        if p["first"] is None or t < p["first"]:
            p["first"] = t
        if p["last"] is None or t > p["last"]:
            p["last"] = t
        slot = "%02d:%02d" % (at.hour, 0 if at.minute < 30 else 30)
        p["slots"][slot] = p["slots"].get(slot, 0) + 1
        if p["_prev"] is None or at > p["_prev"]:
            p["_prev"] = at
    # NB: maxGapMin stays a SCAN-chain measure for scanner people, but a
    # person with only system actions gets first/last/pulse from them.

    # Who are these emails, and when did HR see them arrive? First punch of
    # the floor day, so "clocked in 09:07, first scan 10:40" is one glance.
    # NB: the punched-but-silent merge below adds people to `out`, so the
    # employee map is rebuilt after it via _emp_for.
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
    # People who PUNCHED IN today, hold a scanner-station role, and have not
    # scanned once — the loudest signal on the board, and the one the old
    # payload could not show because it only knew people who had scanned.
    # Scanner roles only: judging a desk job by scan silence would be unjust
    # noise, and unjust noise is how a board loses the team.
    # Tuned twice on the manager's calls (2026-09-10): the first cut
    # whitelisted picker/packer/returns and hid the dispatcher; the second
    # cut showed EVERYONE punched in — and flooded the board with office
    # staff who never touch the floor. The final rule: zero-scan rows only
    # for the scanner roles plus the dispatcher plus the named floor
    # supervisors (lp_floor_extra); anyone who actually SCANNED appears
    # regardless of role. The ALERT keeps the narrow scanner-role whitelist
    # — see silent_now — so nobody is paged about a desk job.
    import json as _j
    from logistics_portal.api.auth import resolve_role
    # The floor's own supervisor watches from the wall, not a scanner — on
    # the manager's call he belongs on the board. More names can join via
    # the lp_floor_extra default (JSON list of emails) without a deploy.
    extra = {"ossamanahila@gmail.com"}
    try:
        extra |= set(_j.loads(frappe.db.get_default("lp_floor_extra") or "[]"))
    except Exception:
        pass
    roles = {}
    for r in frappe.db.sql(
            """SELECT DISTINCT e.user_id, e.employee_name, MIN(c.time) t
               FROM `tabEmployee Checkin` c
               JOIN `tabEmployee` e ON e.name = c.employee
               WHERE c.log_type = 'IN' AND c.time >= %s AND c.time < %s
                 AND e.user_id IS NOT NULL AND e.user_id != ''
               GROUP BY e.user_id, e.employee_name""", (d0, d1), as_dict=True):
        try:
            role = resolve_role(r.user_id)
        except Exception:
            role = None
        roles[r.user_id] = role or "none"
        if r.user_id in out:
            continue
        if role not in ("picker", "packer", "returns", "dispatcher") \
                and r.user_id not in extra:
            continue
        out[r.user_id] = {"user": r.user_id, "scans": 0, "units": 0,
                          "stations": {}, "first": None, "last": None,
                          "slots": {}, "maxGapMin": 0, "_prev": None}
        punch.setdefault(r.user_id, str(clock.to_floor(r.t))[11:16])

    # Role tags for people who scanned WITHOUT punching in — the roles map
    # above only knows the punched, so a packer who skipped the HR clock
    # showed a generic "floor" tag.
    for u in out:
        if u not in roles:
            try:
                roles[u] = resolve_role(u) or "none"
            except Exception:
                roles[u] = "none"

    # Rebuild the employee map AFTER the merge — the silent-but-punched rows
    # were not in it, and without this they would lose their names and their
    # notes.
    users = tuple(out) or ("",)
    emp = {r.user_id: r for r in frappe.db.sql(
        """SELECT user_id, name emp, employee_name FROM `tabEmployee`
           WHERE user_id IN %s""", (users,), as_dict=True)}

    # The floor manager's margin notes — "was unloading the truck 14:10-14:40"
    # — kept on the Employee record so they outlive this screen.
    notes = {}
    emp_users = {v["emp"]: k for k, v in emp.items()}
    if emp:
        for r in frappe.db.sql(
                """SELECT c.reference_name emp, c.owner, c.creation, c.content
                   FROM `tabComment` c
                   WHERE c.reference_doctype = 'Employee'
                     AND c.reference_name IN %s
                     AND c.content LIKE %s
                   ORDER BY c.creation""",
                (tuple(v["emp"] for v in emp.values()), f"Floor {day}:%"),
                as_dict=True):
            u = emp_users.get(r.emp)
            if u:
                notes.setdefault(u, []).append({
                    "by": (r.owner or "").split("@")[0],
                    "at": str(clock.to_floor(r.creation))[11:16],
                    "text": (r.content or "").split(":", 2)[-1].strip()})

    fnow = clock.floor_now()
    people = []
    for p in out.values():
        prev_at = p.pop("_prev", None)
        p["maxGapMin"] = int(p["maxGapMin"])
        p["name"] = (emp.get(p["user"], {}) or {}).get("employee_name") \
            or p["user"].split("@")[0]
        p["punchIn"] = punch.get(p["user"])
        # Minutes of silence since their last scan — the live board's pulse.
        # None when they have not scanned at all today.
        p["lastAgoMin"] = int((fnow - prev_at).total_seconds() // 60) \
            if prev_at else None
        p["role"] = roles.get(p["user"], "")
        p["notes"] = notes.get(p["user"], [])
        people.append(p)
    people.sort(key=lambda x: -x["scans"])
    # The axis is the WHOLE working day, not just the hours that happen to
    # hold scans: a strip that starts at the first scan hides exactly the
    # thing a morning gap is — before this, a 14:04 first scan drew an axis
    # that began at 14:00 and the silent morning simply did not exist.
    # Bounds: the floor's configured day, widened by any scan outside it,
    # and today never extends past the current half-hour (the future is not
    # silence, it just has not happened).
    from logistics_portal.api.settings import get_ops
    lo = int(get_ops("floorStart") or 9) * 2
    hi = int(get_ops("floorEnd") or 19) * 2
    slots_all = [int(k[:2]) * 2 + (1 if k[3:] == "30" else 0)
                 for p in people for k in p["slots"]]
    if slots_all:
        lo = min(lo, min(slots_all))
        hi = max(hi, max(slots_all) + 1)
    if day == str(fnow)[:10]:
        hi = min(hi, fnow.hour * 2 + (1 if fnow.minute >= 30 else 0) + 1)
    axis = ["%02d:%s" % (x // 2, "30" if x % 2 else "00")
            for x in range(lo, max(hi, lo + 1))]
    # The sum of the rows on screen, not just the scanner log: once the
    # system's own witnesses joined each person's count, a headline built
    # from `rows` alone contradicted the board under it (measured 2026-09-10:
    # header 668, rows adding to 821 — the 153 moves, counts and pick lists).
    return {"day": day, "people": people,
            "totalScans": sum(x["scans"] for x in people),
            "axis": axis, "floorNow": str(fnow)[11:16]}
