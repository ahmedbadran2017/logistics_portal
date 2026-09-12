"""Count campaigns — a numbered, finishable sweep of the warehouse.

A cycle count without a campaign is a stream of unrelated events: you can see
that bins were counted, never that the warehouse WAS counted. A campaign draws
the line. It opens with a frozen list of bins, tracks what is done and what is
left, closes ITSELF the moment nothing is left, and freezes a report at that
instant — the record the stock manager keeps, and the thing the next campaign
is compared against.

Three decisions shape everything here, taken with Ahmed on 2026-09-12:

  Scope is the bins that HOLD STOCK when the campaign opens. An empty bin has
  nothing to correct — it can only reveal stock nobody recorded, which is a
  different job and must not be what stops a campaign from closing. The report
  states how many bins were skipped for being empty so nobody reads "100%" as
  "every shelf in the building was walked".

  The scope is FROZEN. A bin that receives stock mid-campaign does not join it,
  or 100% becomes a target that runs away; it is listed in the report and
  belongs to the next campaign.

  A bin is COUNTED when a portal count exists for it, and BLOCKED while that
  count's reconciliation is still awaiting approval. Not "approved" alone: a
  count that finds the shelf perfect creates no reconciliation at all, so an
  approval-only rule would leave every correct shelf permanently unfinished.
  This is exactly what the count-session witness exists for.
"""
import json

import frappe
from frappe.utils import now_datetime

DT = "LP Count Campaign"


def ensure_doctype():
    """Create the campaign doctype on migrate. Custom: lives in the DB."""
    try:
        if frappe.db.exists("DocType", DT):
            return
        frappe.get_doc({
            "doctype": "DocType", "name": DT, "module": "Core",
            "custom": 1, "naming_rule": "Autoincrement",
            "autoname": "autoincrement",
            "fields": [
                {"fieldname": "campaign_no", "fieldtype": "Int",
                 "label": "Campaign", "in_standard_filter": 1},
                {"fieldname": "status", "fieldtype": "Select",
                 "label": "Status", "options": "Open\nClosed",
                 "in_standard_filter": 1},
                {"fieldname": "started_on", "fieldtype": "Datetime", "label": "Started"},
                {"fieldname": "closed_on", "fieldtype": "Datetime", "label": "Closed"},
                {"fieldname": "opened_by", "fieldtype": "Data", "label": "Opened by"},
                {"fieldname": "scope_json", "fieldtype": "Long Text", "label": "Scope"},
                {"fieldname": "report_json", "fieldtype": "Long Text", "label": "Report"},
            ],
            "permissions": [
                {"role": "System Manager", "read": 1, "write": 1, "create": 1},
            ],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "campaign.ensure_doctype")


def _gate():
    from logistics_portal.api.permissions import is_ops_admin
    if not is_ops_admin():
        frappe.throw("Warehouse management only.", frappe.PermissionError)


def _scope_of(doc):
    try:
        v = json.loads(doc.scope_json or "[]")
        return [str(x) for x in v] if isinstance(v, list) else []
    except Exception:
        return []


def active():
    """The open campaign, or None."""
    name = frappe.db.get_value(DT, {"status": "Open"}, "name",
                               order_by="campaign_no desc")
    return frappe.get_doc(DT, name) if name else None


# ---------------------------------------------------------------------------
# Evidence: which scope bins are counted, and which are waiting on approval.
# ---------------------------------------------------------------------------

def _counts_in(scope, since):
    """{bin: {at, by, reco, pending}} — the LAST portal count per scope bin.

    Two trails, because the campaign began before the session witness shipped:
    session rows (authoritative, and the only record of a clean count) and the
    comment `submit_count` writes on a draft, which outlives approval and is
    the only way an earlier portal count can still be recognised.
    """
    if not scope:
        return {}
    out = {}
    in_scope = set(scope)

    def put(wh, at, by, reco, pending):
        if wh not in in_scope:
            return
        prev = out.get(wh)
        if not prev or at > prev["at"]:
            out[wh] = {"at": at, "by": by, "reco": reco or "", "pending": pending}

    from logistics_portal.api.cycle_count import SESSION_DT
    if frappe.db.exists("DocType", SESSION_DT):
        try:
            for r in frappe.db.sql(
                    f"""SELECT warehouse, counter, draft, creation
                        FROM `tab{SESSION_DT}` WHERE creation >= %s""",
                    (since,), as_dict=True):
                pending = bool(r.draft) and frappe.db.get_value(
                    "Stock Reconciliation", r.draft, "docstatus") == 0
                put(r.warehouse, str(r.creation)[:16], r.counter or "?",
                    r.draft, pending)
        except Exception:
            frappe.log_error(frappe.get_traceback()[:2000], "campaign._counts_in")

    for r in frappe.db.sql(
            """SELECT c.reference_name AS reco, c.owner, c.creation,
                      (SELECT i.warehouse FROM `tabStock Reconciliation Item` i
                       WHERE i.parent = c.reference_name LIMIT 1) AS wh,
                      (SELECT sr.docstatus FROM `tabStock Reconciliation` sr
                       WHERE sr.name = c.reference_name) AS ds
               FROM `tabComment` c
               WHERE c.reference_doctype = 'Stock Reconciliation'
                 AND c.content LIKE 'Portal cycle count%%'
                 AND c.creation >= %s""", (since,), as_dict=True):
        if r.wh and r.ds != 2:
            put(r.wh, str(r.creation)[:16], (r.owner or "?"), r.reco, r.ds == 0)
    return out


def _bins_with_stock():
    from logistics_portal.api.cycle_count import _countable_bins
    return [w for w, lines, units in _countable_bins() if lines > 0]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist()
def open_campaign(started_on=None):
    """Start the next campaign over the bins that hold stock right now."""
    _gate()
    if active():
        frappe.throw("A campaign is already open. Close it first.")
    scope = _bins_with_stock()
    if not scope:
        frappe.throw("No bins hold stock — nothing to count.")
    last = frappe.db.sql(f"SELECT MAX(campaign_no) FROM `tab{DT}`")[0][0] or 0
    if not started_on and not last:
        # The very first campaign starts when the team actually started, not
        # when somebody got around to pressing the button — otherwise the days
        # already walked fall outside #1 and have to be walked again. Later
        # campaigns begin the moment they are opened; only #1 has a past.
        earliest = frappe.db.sql(
            """SELECT MIN(creation) FROM `tabComment`
               WHERE reference_doctype = 'Stock Reconciliation'
                 AND content LIKE 'Portal cycle count%%'
                 AND creation >= DATE_SUB(NOW(), INTERVAL 14 DAY)""")[0][0]
        if earliest:
            started_on = earliest
    doc = frappe.get_doc({
        "doctype": DT, "campaign_no": int(last) + 1, "status": "Open",
        "started_on": started_on or now_datetime(),
        "opened_by": frappe.session.user,
        "scope_json": json.dumps(sorted(scope)),
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "no": doc.campaign_no, "bins": len(scope)}


def _build_state(doc):
    """The live picture of one campaign."""
    from logistics_portal.api.cycle_count import _zone_of
    scope = _scope_of(doc)
    since = str(doc.started_on)
    counts = _counts_in(scope, since)

    done, blocked, left = [], [], []
    for wh in scope:
        c = counts.get(wh)
        if not c:
            left.append(wh)
        elif c["pending"]:
            blocked.append(wh)
        else:
            done.append(wh)

    zones, people, days = {}, {}, {}
    for wh in scope:
        z = zones.setdefault(_zone_of(wh), {"zone": _zone_of(wh), "bins": 0,
                                            "done": 0, "blocked": 0})
        z["bins"] += 1
        c = counts.get(wh)
        if c and not c["pending"]:
            z["done"] += 1
        elif c:
            z["blocked"] += 1
    for wh, c in counts.items():
        u = c["by"]
        p = people.setdefault(u, {"user": u, "bins": 0, "blocked": 0, "last": ""})
        p["bins"] += 1
        if c["pending"]:
            p["blocked"] += 1
        if c["at"] > p["last"]:
            p["last"] = c["at"]
        d = c["at"][:10]
        dd = days.setdefault(d, {"day": d, "bins": 0, "people": set()})
        dd["bins"] += 1
        dd["people"].add(u)

    for p in people.values():
        p["name"] = (frappe.db.get_value("User", p["user"], "full_name")
                     or p["user"].split("@")[0])
    day_rows = []
    for d in sorted(days):
        v = days[d]
        day_rows.append({"day": d, "bins": v["bins"], "people": len(v["people"])})
    # What each day left behind, so the history reads as a countdown and not
    # just a bar chart: the same number the floor was looking at that evening.
    running = len(scope)
    for row in day_rows:
        running -= row["bins"]
        row["left"] = max(0, running)

    pct = round(100.0 * len(done) / len(scope), 1) if scope else 0.0
    return {
        "no": doc.campaign_no, "status": doc.status,
        "startedOn": str(doc.started_on)[:16],
        "closedOn": str(doc.closed_on)[:16] if doc.closed_on else "",
        "scope": len(scope), "done": len(done), "blocked": len(blocked),
        "left": len(left), "pct": pct,
        "complete": not left and not blocked,
        "zones": sorted(zones.values(), key=lambda z: (-z["bins"], z["zone"])),
        "people": sorted(people.values(), key=lambda p: -p["bins"]),
        "days": day_rows,
        "leftBins": [{"bin": w.replace(" - JM", ""), "warehouse": w,
                      "zone": _zone_of(w)} for w in left[:60]],
        "blockedBins": [{"bin": w.replace(" - JM", ""), "warehouse": w,
                         "reco": counts[w]["reco"]} for w in blocked[:40]],
    }


@frappe.whitelist()
def state():
    """The open campaign's live progress, or the last closed one's report."""
    _gate()
    doc = active()
    if doc:
        st = _build_state(doc)
        st["report"] = None
        return {"campaign": st, "history": _history()}
    last = frappe.db.get_value(DT, {"status": "Closed"}, "name",
                               order_by="campaign_no desc")
    if not last:
        return {"campaign": None, "history": [],
                "candidateBins": len(_bins_with_stock())}
    doc = frappe.get_doc(DT, last)
    st = _build_state(doc)
    try:
        st["report"] = json.loads(doc.report_json or "null")
    except Exception:
        st["report"] = None
    return {"campaign": st, "history": _history()}


def _history():
    return [{"no": r.campaign_no, "status": r.status,
             "startedOn": str(r.started_on)[:10],
             "closedOn": str(r.closed_on)[:10] if r.closed_on else ""}
            for r in frappe.db.sql(
                f"""SELECT campaign_no, status, started_on, closed_on
                    FROM `tab{DT}` ORDER BY campaign_no DESC LIMIT 24""",
                as_dict=True)]


def _freeze_report(doc):
    """The record the stock manager keeps — computed once, at the close.

    It is a record of CORRECTIONS, not a photograph of the warehouse. Stock
    kept moving while the count ran (every one of the first 47 bins was picked
    from again within two days), so a bin's line says what its count found and
    fixed at that moment, which is what a cycle count can honestly claim.
    """
    from logistics_portal.api.cycle_count import _zone_of
    scope = _scope_of(doc)
    counts = _counts_in(scope, str(doc.started_on))
    recos = [c["reco"] for c in counts.values() if c.get("reco")]
    lines, diff_bins, plus, minus, value = [], 0, 0, 0, 0.0
    if recos:
        ph = ", ".join(["%s"] * len(recos))
        rows = frappe.db.sql(
            f"""SELECT sr.name, sri.warehouse AS wh, sri.item_code,
                       sri.qty, sri.current_qty, sri.valuation_rate
                FROM `tabStock Reconciliation Item` sri
                JOIN `tabStock Reconciliation` sr ON sr.name = sri.parent
                WHERE sr.name IN ({ph}) AND sr.docstatus = 1""",
            tuple(recos), as_dict=True)
        touched = set()
        for r in rows:
            d = float(r.qty or 0) - float(r.current_qty or 0)
            if not d:
                continue
            touched.add(r.wh)
            if d > 0:
                plus += d
            else:
                minus += -d
            value += d * float(r.valuation_rate or 0)
            lines.append({
                "bin": (r.wh or "").replace(" - JM", ""), "item": r.item_code,
                "book": int(r.current_qty or 0), "counted": int(r.qty or 0),
                "delta": int(d), "by": counts.get(r.wh, {}).get("by", ""),
                "at": counts.get(r.wh, {}).get("at", ""),
            })
        diff_bins = len(touched)
    lines.sort(key=lambda x: -abs(x["delta"]))

    by_zone = {}
    for wh in scope:
        z = by_zone.setdefault(_zone_of(wh), {"zone": _zone_of(wh), "bins": 0})
        z["bins"] += 1
    by_person = {}
    for wh, c in counts.items():
        p = by_person.setdefault(c["by"], {"user": c["by"], "bins": 0})
        p["bins"] += 1
    for p in by_person.values():
        p["name"] = (frappe.db.get_value("User", p["user"], "full_name")
                     or p["user"].split("@")[0])

    # Bins that took stock after the scope was frozen: out of this campaign by
    # design, and the first thing the next one should carry.
    later = [w for w in _bins_with_stock() if w not in set(scope)]
    return {
        "no": doc.campaign_no,
        "startedOn": str(doc.started_on)[:16],
        "closedOn": str(doc.closed_on or now_datetime())[:16],
        "bins": len(scope), "binsWithDifference": diff_bins,
        "linesWithDifference": len(lines),
        "piecesFound": int(plus), "piecesMissing": int(minus),
        "netPieces": int(plus - minus), "valueDelta": round(value),
        "zones": sorted(by_zone.values(), key=lambda z: -z["bins"]),
        "people": sorted(by_person.values(), key=lambda p: -p["bins"]),
        "lines": lines[:500], "linesTotal": len(lines),
        "newBinsSinceStart": sorted(w.replace(" - JM", "") for w in later)[:60],
        "newBinsCount": len(later),
        "scopeNote": "stocked bins at campaign start",
    }


def maybe_close():
    """Close the open campaign the moment nothing is left. Called after an
    approval; never fatal to the approval itself."""
    try:
        doc = active()
        if not doc:
            return None
        st = _build_state(doc)
        if not st["complete"]:
            return None
        doc.status = "Closed"
        doc.closed_on = now_datetime()
        doc.report_json = json.dumps(_freeze_report(doc), default=str)
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return doc.campaign_no
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "campaign.maybe_close")
        return None


@frappe.whitelist()
def report(no=None):
    """A closed campaign's frozen report."""
    _gate()
    name = frappe.db.get_value(
        DT, {"campaign_no": int(no)} if no else {"status": "Closed"}, "name",
        order_by="campaign_no desc")
    if not name:
        frappe.throw("No closed campaign yet.")
    doc = frappe.get_doc(DT, name)
    if doc.status != "Closed":
        frappe.throw("That campaign is still open.")
    try:
        return json.loads(doc.report_json or "null") or _freeze_report(doc)
    except Exception:
        return _freeze_report(doc)


@frappe.whitelist()
def in_scope(warehouse):
    """Is this bin part of the open campaign, and is it already counted?
    The count screen uses it to tell the floor what still needs walking."""
    doc = active()
    if not doc:
        return {"campaign": None}
    scope = set(_scope_of(doc))
    wh = (warehouse or "").strip()
    if wh not in scope:
        return {"campaign": doc.campaign_no, "inScope": False}
    c = _counts_in([wh], str(doc.started_on)).get(wh)
    return {"campaign": doc.campaign_no, "inScope": True,
            "counted": bool(c and not c["pending"]),
            "pending": bool(c and c["pending"]),
            "by": (c or {}).get("by", ""), "at": (c or {}).get("at", "")}
