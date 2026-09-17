"""Zone survey — walking the building to find out which shelves are real.

The cycle count asks what is ON a shelf. This asks a question nobody has ever
asked here: which shelves EXIST, and in what order does a person pass them.

It matters because the warehouse master stopped describing the building a long
time ago. Measured 2026-09-17: 1,510 warehouse records across four companies,
702 of them live leaves in Morocco. Only 276 have moved in a month. Agora and
Babel alone carry 275 shelves, 272 of them empty — 39% of the whole estate,
almost certainly racking that is not there. Meanwhile the floor keeps putting
stock on shelves the system refuses to pick from, and an order sat six days
out of stock with three pieces on C3C.

Two passes, and the second one is blind.

A second walker who can see the first one's answers does not verify, they
agree: the eye goes looking for confirmation instead of error, and you end up
with two signatures and no second opinion. So the second pass shares the
first one's ROUTE — an order, not a judgement, and it makes the walk fast and
comparable — while every verdict stays hidden. Only the disagreements surface.

The route is the other prize. The picking engine orders a list's lines
alphabetically and calls it a walk; with a real sequence per zone, the pick
path, the travel estimate and the autopilot's batch cost stop being guesses.

Nothing closes on one person's word: a shelf is disabled only after two
passes agree it is not there, and never while it holds stock.
"""

import json

import frappe
from frappe.utils import now_datetime

SURVEY_DT = "LP Zone Survey"
_CO = "Justyol Morocco"

SEEN, MISSING, NEW = "seen", "missing", "new"


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("picker", "packer", "dispatcher", "manager", "returns"):
        frappe.throw("lp:floorOnly", frappe.PermissionError)
    return role


def _is_manager():
    from logistics_portal.api.permissions import is_ops_admin
    return bool(is_ops_admin())


def ensure_doctype():
    """Create the survey witness on migrate. Custom doctype: lives in the DB,
    no schema files, safe to run every time."""
    try:
        if frappe.db.exists("DocType", SURVEY_DT):
            return
        frappe.get_doc({
            "doctype": "DocType", "name": SURVEY_DT, "module": "Core",
            "custom": 1, "naming_rule": "Autoincrement", "autoname": "autoincrement",
            "fields": [
                {"fieldname": "zone", "fieldtype": "Data", "label": "Zone", "in_standard_filter": 1},
                {"fieldname": "pass_no", "fieldtype": "Int", "label": "Pass", "in_standard_filter": 1},
                {"fieldname": "surveyor", "fieldtype": "Data", "label": "Surveyor", "in_standard_filter": 1},
                {"fieldname": "state", "fieldtype": "Select", "label": "State",
                 "options": "open\ndone", "default": "open", "in_standard_filter": 1},
                {"fieldname": "seen_n", "fieldtype": "Int", "label": "Shelves seen"},
                {"fieldname": "missing_n", "fieldtype": "Int", "label": "Shelves missing"},
                {"fieldname": "new_n", "fieldtype": "Int", "label": "Shelves found new"},
                {"fieldname": "finished_at", "fieldtype": "Datetime", "label": "Finished"},
                {"fieldname": "verdicts", "fieldtype": "Long Text", "label": "Verdicts (JSON)"},
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "zone_survey.ensure_doctype")


# ── survey documents ──────────────────────────────────────────────────────

def _verdicts(doc):
    try:
        v = json.loads(doc.get("verdicts") or "{}")
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def _passes(zone):
    return frappe.get_all(
        SURVEY_DT, filters={"zone": zone}, order_by="pass_no, creation",
        fields=["name", "pass_no", "surveyor", "state", "seen_n", "missing_n",
                "new_n", "finished_at"])


def _my_open(zone):
    rows = frappe.get_all(SURVEY_DT, filters={"zone": zone, "state": "open",
                                              "surveyor": frappe.session.user},
                          fields=["name"], limit=1)
    return rows[0].name if rows else None


def _zone_bins(zone):
    """Every live leaf warehouse hanging under this zone."""
    return frappe.db.sql(
        f"""SELECT w.name, COALESCE(w.disabled, 0) AS disabled,
                  {"COALESCE(w.custom_walk_order, 0)" if frappe.get_meta("Warehouse").has_field("custom_walk_order") else "0"} AS walk_order,
                  (SELECT COALESCE(SUM(b.actual_qty), 0) FROM `tabBin` b
                    WHERE b.warehouse = w.name) AS qty
           FROM `tabWarehouse` w
           WHERE w.company = %s AND w.is_group = 0 AND w.parent_warehouse = %s
           ORDER BY w.name""", (_CO, zone), as_dict=True)  # noqa: E501


# ── the floor's screen ────────────────────────────────────────────────────

@frappe.whitelist()
def zones():
    """Every zone with how far its survey has got."""
    _gate()
    # The stamp columns arrive with the migrate that ships this module; the
    # page must not 500 on a bench that has the code and not yet the field.
    stamped = ("SUM(w.custom_seen_at IS NOT NULL)"
               if frappe.get_meta("Warehouse").has_field("custom_seen_at") else "0")
    rows = frappe.db.sql(
        f"""SELECT w.parent_warehouse AS zone, COUNT(*) AS bins,
                  SUM((SELECT COALESCE(SUM(b.actual_qty), 0) FROM `tabBin` b
                        WHERE b.warehouse = w.name) > 0) AS with_stock,
                  {stamped} AS stamped
           FROM `tabWarehouse` w
           WHERE w.company = %s AND w.is_group = 0 AND w.parent_warehouse IS NOT NULL
           GROUP BY w.parent_warehouse ORDER BY COUNT(*) DESC""", (_CO,), as_dict=True)
    out = []
    for r in rows:
        ps = _passes(r.zone)
        done = [p for p in ps if p.state == "done"]
        mine_open = _my_open(r.zone)
        # What this walker would be doing if they tapped in: the first pass,
        # the blind second, or nothing (it is finished, or it is their own).
        if len(done) >= 2:
            stage = "confirmed" if _agreed(r.zone) else "disputed"
        elif len(done) == 1:
            stage = "mine" if done[0].surveyor == frappe.session.user else "pass2"
        else:
            stage = "open"
        out.append({
            "zone": r.zone, "bins": int(r.bins or 0),
            "withStock": int(r.with_stock or 0), "stamped": int(r.stamped or 0),
            "passes": [{"pass": p.pass_no, "by": (p.surveyor or "").split("@")[0],
                        "state": p.state, "seen": p.seen_n, "missing": p.missing_n,
                        "new": p.new_n, "at": str(p.finished_at or "")[:16]} for p in ps],
            "stage": stage, "resuming": bool(mine_open),
        })
    return {"zones": out, "canReview": _is_manager()}


@frappe.whitelist(methods=["POST"])
def open_zone(zone):
    """Start (or resume) a walk. The second pass inherits the first one's
    ROUTE and none of its answers — that is the whole point."""
    _gate()
    zone = (zone or "").strip()
    if not frappe.db.exists("Warehouse", zone):
        frappe.throw("Unknown zone.")
    ps = _passes(zone)
    done = [p for p in ps if p.state == "done"]
    if len(done) >= 2:
        return {"ok": False, "reason": "finished"}
    if done and done[0].surveyor == frappe.session.user:
        # Verification has to be somebody else's eyes, or it is not verification.
        return {"ok": False, "reason": "same_person", "first": done[0].surveyor.split("@")[0]}

    name = _my_open(zone)
    if not name:
        doc = frappe.get_doc({
            "doctype": SURVEY_DT, "zone": zone, "pass_no": len(done) + 1,
            "surveyor": frappe.session.user, "state": "open", "verdicts": "{}"})
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        name = doc.name

    mine = _verdicts(frappe.get_doc(SURVEY_DT, name))
    bins = _zone_bins(zone)
    route = {}
    if done:
        # The first walker's order, carried over as the path to walk.
        first = _verdicts(frappe.get_doc(SURVEY_DT, done[0].name))
        route = {k: int(v.get("pos") or 0) for k, v in first.items()}
    bins.sort(key=lambda b: (route.get(b["name"], 9999), b["name"]))
    return {
        "ok": True, "survey": name, "zone": zone, "pass": len(done) + 1,
        "bins": [{"warehouse": b["name"], "short": b["name"].replace(" - JM", ""),
                  "book": int(float(b["qty"] or 0)), "disabled": int(b["disabled"] or 0),
                  "mine": mine.get(b["name"], {}).get("v", ""),
                  "pos": mine.get(b["name"], {}).get("pos")} for b in bins],
        "found": [{"warehouse": k, "short": k} for k, v in mine.items()
                  if v.get("v") == NEW and not frappe.db.exists("Warehouse", k)],
    }


@frappe.whitelist(methods=["POST"])
def mark(zone, warehouse, verdict):
    """One shelf, one verdict. The position is the order it was tapped in —
    the walk writes the route by itself."""
    _gate()
    if verdict not in (SEEN, MISSING):
        frappe.throw("Unknown verdict.")
    name = _my_open((zone or "").strip())
    if not name:
        frappe.throw("lp:noOpenSurvey")
    doc = frappe.get_doc(SURVEY_DT, name)
    v = _verdicts(doc)
    warehouse = (warehouse or "").strip()
    if verdict == SEEN and warehouse not in v:
        pos = 1 + len([x for x in v.values() if x.get("v") == SEEN])
    else:
        pos = v.get(warehouse, {}).get("pos")
    v[warehouse] = {"v": verdict, "pos": pos}
    doc.db_set("verdicts", json.dumps(v, ensure_ascii=False), update_modified=False)
    frappe.db.commit()
    return {"ok": True, "warehouse": warehouse, "verdict": verdict, "pos": pos,
            "seen": len([x for x in v.values() if x.get("v") == SEEN]),
            "missing": len([x for x in v.values() if x.get("v") == MISSING])}


@frappe.whitelist(methods=["POST"])
def add_found(zone, label):
    """A shelf on the floor with no record. Written down here, created by a
    manager from the review — the floor must never be slowed by master data,
    and master data must never be created by a mis-typed label."""
    _gate()
    name = _my_open((zone or "").strip())
    if not name:
        frappe.throw("lp:noOpenSurvey")
    label = (label or "").strip().upper()
    if not label or len(label) > 60:
        frappe.throw("Give the shelf a short label.")
    doc = frappe.get_doc(SURVEY_DT, name)
    v = _verdicts(doc)
    v[label] = {"v": NEW, "pos": 1 + len([x for x in v.values() if x.get("v") == SEEN])}
    doc.db_set("verdicts", json.dumps(v, ensure_ascii=False), update_modified=False)
    frappe.db.commit()
    return {"ok": True, "label": label}


@frappe.whitelist(methods=["POST"])
def finish(zone):
    """Close my pass. When it is the second, the comparison runs at once."""
    _gate()
    zone = (zone or "").strip()
    name = _my_open(zone)
    if not name:
        frappe.throw("lp:noOpenSurvey")
    doc = frappe.get_doc(SURVEY_DT, name)
    v = _verdicts(doc)
    doc.db_set({
        "state": "done", "finished_at": now_datetime(),
        "seen_n": len([x for x in v.values() if x.get("v") == SEEN]),
        "missing_n": len([x for x in v.values() if x.get("v") == MISSING]),
        "new_n": len([x for x in v.values() if x.get("v") == NEW]),
    }, update_modified=False)
    frappe.db.commit()
    done = [p for p in _passes(zone) if p.state == "done"]
    if len(done) < 2:
        return {"ok": True, "pass": doc.pass_no, "awaiting": "second pass"}
    return {"ok": True, "pass": doc.pass_no, **review(zone)}


# ── the comparison ────────────────────────────────────────────────────────

def _compare(zone):
    done = [p for p in _passes(zone) if p.state == "done"][:2]
    if len(done) < 2:
        return None
    a = _verdicts(frappe.get_doc(SURVEY_DT, done[0].name))
    b = _verdicts(frappe.get_doc(SURVEY_DT, done[1].name))
    agree, differ = [], []
    for key in sorted(set(a) | set(b)):
        va, vb = (a.get(key) or {}).get("v", ""), (b.get(key) or {}).get("v", "")
        row = {"warehouse": key, "short": key.replace(" - JM", ""),
               "a": va, "b": vb,
               "posA": (a.get(key) or {}).get("pos"), "posB": (b.get(key) or {}).get("pos"),
               "book": int(float(frappe.db.get_value(
                   "Bin", {"warehouse": key}, "SUM(actual_qty)") or 0))
               if frappe.db.exists("Warehouse", key) else 0}
        if va and va == vb:
            agree.append(row)
        else:
            # A shelf only one person saw is not an argument to settle by vote:
            # a shelf that is there is there. It is flagged for a third look.
            row["kind"] = "one_saw_it" if NEW in (va, vb) or "" in (va, vb) else "contradiction"
            differ.append(row)
    return {"first": done[0], "second": done[1], "agree": agree, "differ": differ}


def _agreed(zone):
    c = _compare(zone)
    return bool(c and not c["differ"])


@frappe.whitelist()
def review(zone):
    """What the two walks said, and only what they disagreed on."""
    _gate()
    zone = (zone or "").strip()
    c = _compare(zone)
    if not c:
        return {"ready": False, "zone": zone}
    seen = [r for r in c["agree"] if r["a"] == SEEN]
    missing = [r for r in c["agree"] if r["a"] == MISSING]
    return {
        "ready": True, "zone": zone,
        "by": [(c["first"].surveyor or "").split("@")[0], (c["second"].surveyor or "").split("@")[0]],
        "seen": len(seen), "missing": len(missing), "differ": c["differ"],
        # Nothing may be closed while it holds stock — the shelf is either
        # really there (and the walkers were wrong) or the book is (and the
        # stock is lost). Either way it is a question, not a cleanup.
        "closable": [r for r in missing if not r["book"]],
        "emptyFirst": [r for r in missing if r["book"]],
        "canApply": _is_manager(),
    }


@frappe.whitelist(methods=["POST"])
def apply_zone(zone):
    """Stamp the map and close what both walks agreed is not there.

    The gate that makes the whole thing safe: two finished passes, no open
    disagreement, and never a shelf with stock on it.
    """
    if not _is_manager():
        frappe.throw("Only a manager can apply a survey.", frappe.PermissionError)
    zone = (zone or "").strip()
    rep = review(zone)
    if not rep.get("ready"):
        frappe.throw("lp:needTwoPasses")
    if rep["differ"]:
        frappe.throw("lp:resolveFirst")
    c = _compare(zone)
    stamped = closed = 0
    for r in c["agree"]:
        if r["a"] != SEEN or not frappe.db.exists("Warehouse", r["warehouse"]):
            continue
        frappe.db.set_value("Warehouse", r["warehouse"], {
            "custom_seen_at": now_datetime(),
            "custom_walk_order": int(r["posA"] or 0)}, update_modified=False)
        stamped += 1
    for r in rep["closable"]:
        if not frappe.db.exists("Warehouse", r["warehouse"]):
            continue
        if float(frappe.db.get_value("Bin", {"warehouse": r["warehouse"]},
                                     "SUM(actual_qty)") or 0) > 0:
            continue                      # it filled up while we were reviewing
        frappe.db.set_value("Warehouse", r["warehouse"], "disabled", 1,
                            update_modified=False)
        closed += 1
    frappe.db.commit()
    frappe.cache().delete_value("lp_pick_avail")
    return {"ok": True, "zone": zone, "stamped": stamped, "closed": closed,
            "emptyFirst": len(rep["emptyFirst"])}
