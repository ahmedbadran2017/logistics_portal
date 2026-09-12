"""Cycle counting — count a bin on the floor, manager approves, ERPNext
reconciles.

Replaces the desk Stock Reconciliation flow (82/year, and the only way to fix
corrupted bins like Aisles E). The counter never posts stock: submitting a
count creates a DRAFT Stock Reconciliation holding only the differences;
a manager approves (submits) or discards it from the portal.

Portal drafts are tracked in the `lp_cycle_counts` default (the doctype has
no remarks field to mark them with), so desk drafts never leak into the
approval queue.
"""

import json
import re

import frappe
from frappe.utils import nowdate, nowtime

from logistics_portal.api.stock_moves import _movable_condition

_REG = "lp_cycle_counts"


def _gate():
    # The whole team counts (Ahmed 2026-09-11: pickers in their idle time,
    # everyone really). Safe to open wide because a count never posts stock —
    # it files a DRAFT the manager approves. The MOVES a count can carry are
    # real transfers, but they only record what the counter physically did
    # with the pieces in their hands.
    from logistics_portal.api.auth import resolve_role
    if not resolve_role(frappe.session.user):
        frappe.throw("Not authorized to count stock.", frappe.PermissionError)


def _is_manager():
    from logistics_portal.api.auth import resolve_role
    return resolve_role(frappe.session.user) == "manager"


def _registry():
    raw = frappe.db.get_default(_REG)
    if raw:
        try:
            v = json.loads(raw)
            if isinstance(v, list):
                return [str(x) for x in v]
        except Exception:
            pass
    return []


def _save_registry(names):
    frappe.db.set_default(_REG, json.dumps(names))


# ---------------------------------------------------------------------------
# Count sessions — the witness every count leaves behind.
#
# A clean count creates NO Stock Reconciliation (there is nothing to correct),
# which means the work it represents used to vanish: the floor could walk a
# whole aisle, find it perfect, and the books would look identical to an aisle
# nobody ever touched. Coverage is exactly the question a manager needs
# answered, so every count — clean or not — now files one small session row.
# ---------------------------------------------------------------------------
SESSION_DT = "LP Count Session"


def _rename_lines_field():
    """One-time: `lines` was a MariaDB reserved word.

    Every raw query naming it unquoted died with a syntax error — the screen's
    first load did exactly that. Quoting each use would work and leave the trap
    armed for the next person, so the column is renamed instead, while the
    table is new. Idempotent and never fatal: a migrate must not fail over it.
    """
    try:
        fld = frappe.db.get_value(
            "DocField", {"parent": SESSION_DT, "fieldname": "lines"}, "name")
        has_new = frappe.db.sql(
            """SELECT 1 FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                 AND COLUMN_NAME = 'line_count'""", ("tab" + SESSION_DT,))
        if not has_new:
            frappe.db.sql(
                "ALTER TABLE `tab" + SESSION_DT + "` "
                "CHANGE `lines` `line_count` int(11) NOT NULL DEFAULT 0")
        if fld:
            frappe.db.set_value("DocField", fld, "fieldname", "line_count",
                                update_modified=False)
        frappe.clear_cache(doctype=SESSION_DT)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000],
                         "cycle_count._rename_lines_field")


def ensure_doctype():
    """Create the session witness on migrate. Custom doctype: lives in the DB,
    no schema files, safe to run every time."""
    try:
        if frappe.db.exists("DocType", SESSION_DT):
            _rename_lines_field()
            return
        frappe.get_doc({
            "doctype": "DocType", "name": SESSION_DT, "module": "Core",
            "custom": 1, "naming_rule": "Autoincrement",
            "autoname": "autoincrement",
            "fields": [
                {"fieldname": "warehouse", "fieldtype": "Data", "label": "Bin",
                 "in_standard_filter": 1},
                {"fieldname": "zone", "fieldtype": "Data", "label": "Zone",
                 "in_standard_filter": 1},
                {"fieldname": "counter", "fieldtype": "Data", "label": "Counter",
                 "in_standard_filter": 1},
                {"fieldname": "line_count", "fieldtype": "Int", "label": "Lines counted"},
                {"fieldname": "diff_lines", "fieldtype": "Int", "label": "Lines differing"},
                {"fieldname": "units", "fieldtype": "Int", "label": "Units counted"},
                {"fieldname": "moves", "fieldtype": "Int", "label": "Relocations"},
                {"fieldname": "draft", "fieldtype": "Data", "label": "Reconciliation"},
            ],
            "permissions": [
                {"role": "System Manager", "read": 1, "write": 1, "create": 1},
            ],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "cycle_count.ensure_doctype")


def _zone_of(warehouse):
    """The aisle a bin belongs to.

    Shelf codes are letter-then-number (H12B, E5C, D2C.), so the leading
    letters ARE the aisle. Reserve racking is hyphenated (AG-E1-B, BAB-07-C)
    and its short head is the aisle. Everything else — PLT, Return Zone,
    SLOW ZONE, Zone de reception — is a single named place, not an aisle, so
    it keeps its whole name and never merges with a neighbour that happens to
    share a first word."""
    c = (warehouse or "").replace(" - JM", "").strip()
    if not c:
        return "?"
    head = re.split(r"[-\s]", c, 1)[0]
    m = re.match(r"^([A-Za-z]{1,3})\d", head)
    if m:
        return m.group(1).upper()
    if head.isalpha() and len(head) <= 3:
        return head.upper()
    return c.upper()


def _log_session(warehouse, lines, diff_lines, units, moves, draft):
    """File the witness. Never fatal: a count that physically happened must
    not be rejected because its paperwork failed."""
    try:
        frappe.get_doc({
            "doctype": SESSION_DT, "warehouse": warehouse,
            "zone": _zone_of(warehouse), "counter": frappe.session.user,
            "line_count": int(lines or 0), "diff_lines": int(diff_lines or 0),
            "units": int(units or 0), "moves": int(moves or 0),
            "draft": draft or "",
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "cycle_count._log_session")


def _valid_bin(warehouse):
    cond, args = _movable_condition("name")
    return bool(frappe.db.sql(
        f"""SELECT 1 FROM `tabWarehouse` WHERE name = %s
            AND is_group = 0 AND disabled = 0 AND {cond}""",
        tuple([warehouse, *args])))


@frappe.whitelist()
def count_boot():
    """Bin list for the picker + the pending-approval queue."""
    _gate()
    cond, args = _movable_condition("name")
    warehouses = [w[0] for w in frappe.db.sql(
        f"""SELECT name FROM `tabWarehouse`
            WHERE is_group = 0 AND disabled = 0 AND {cond} ORDER BY name""",
        tuple(args))]
    return {"warehouses": warehouses, "pending": _pending(),
            "canApprove": _is_manager()}


@frappe.whitelist()
def bin_contents(warehouse):
    """What the ledger says is in this bin — the counting sheet."""
    _gate()
    warehouse = (warehouse or "").strip()
    if not _valid_bin(warehouse):
        frappe.throw(f"{warehouse} is not a countable bin.")
    rows = frappe.db.sql(
        """SELECT b.item_code, b.actual_qty AS qty, b.valuation_rate,
                  it.custom_sku AS sku,
                  COALESCE(NULLIF(it.item_name,''), b.item_code) AS name, it.image
           FROM `tabBin` b
           LEFT JOIN `tabItem` it ON it.name = b.item_code
           WHERE b.warehouse = %s AND b.actual_qty <> 0
           ORDER BY b.actual_qty DESC""", (warehouse,), as_dict=True)
    return {"warehouse": warehouse, "rows": [{
        "itemCode": r.item_code, "sku": r.sku or "", "name": r.name,
        "image": r.image or "", "book": int(r.qty or 0),
    } for r in rows]}


@frappe.whitelist()
def item_locations(item_code):
    """Everywhere the ledger sees this item — the shelf picker for a count
    move. The counter found 3 of 5 and KNOWS the other 2 sit on another
    shelf: the honest record is a transfer, not two reconciliations."""
    _gate()
    item_code = (item_code or "").strip()
    rows = frappe.db.sql(
        """SELECT warehouse, actual_qty FROM `tabBin`
           WHERE item_code = %s AND actual_qty <> 0
           ORDER BY actual_qty DESC LIMIT 20""", (item_code,), as_dict=True)
    return {"locations": [{"warehouse": r.warehouse,
                           "qty": int(r.actual_qty or 0)} for r in rows]}


# ---------------------------------------------------------------- batches
#
# A batch-tracked item cannot be reconciled by quantity alone: ERPNext throws
# "Row # N: Please add Serial and Batch Bundle for Item X" the moment the
# draft is inserted. That is 27% of the bins holding stock on this site
# (1,979 of 7,274), so the count tool was refusing more than a quarter of the
# floor's work — including every shelf the short-pick worklist points at.
#
# Two of ERPNext's three escapes from that throw are wrong here:
#
#   * `reconcile_all_serial_batch` looks like the answer — "Reconcile All
#     Serial Nos / Batches" is literally what counting a shelf means — but
#     for any non-zero count `set_new_serial_and_batch_bundle` then runs
#     `item.qty = abs(current_doc.total_qty)`: it OVERWRITES the counted
#     number with the book's, copies the same batches straight back in, and
#     the reconciliation becomes a no-op. A count that silently changes
#     nothing is worse than one that refuses.
#   * `use_serial_batch_fields` + `batch_no` reconciles ONE batch, which is
#     right for the 91.3% of these bins holding a single batch and silently
#     wrong for the rest — it would leave the other batches untouched while
#     reporting the whole bin counted.
#
# So the bundle is built here, saying the only thing that is actually known:
# how many units are on the shelf, and therefore what each batch now holds.
# Zero-quantity rows are part of that answer and ERPNext accepts them for
# exactly this case (`voucher_type == "Stock Reconciliation"` and an Inward
# transaction skip the "Qty is mandatory for the batch" throw).


def _available_batches(item_code, warehouse):
    """The batches with stock in this bin, in the order ERPNext hands them out.

    Deliberately `batch.batch`\'s function and not the identically-named one in
    `serial_and_batch_bundle`: TWO different functions carry this name, they
    return different shapes (an OrderedDict of batch->qty against a list of
    rows including empty batches), and this is the one Stock Reconciliation
    itself imports. Reading the bin through any other lens invites the plan
    below and ERPNext\'s own view of the same shelf to disagree.

    Verified on 200 random batched-item bins: the batch totals equal
    Bin.actual_qty in every one, so the book the counter is arguing with and
    the batches here are the same number.
    """
    from erpnext.stock.doctype.batch.batch import get_available_batches
    rows = get_available_batches(frappe._dict({
        "item_code": item_code, "warehouse": warehouse,
        "posting_date": nowdate(), "posting_time": nowtime(),
    })) or {}
    return [(b, float(q or 0)) for b, q in rows.items() if float(q or 0) > 0]


def _plan_batches(avail, counted):
    """Which batch each counted unit is.

    A shortfall comes off the FRONT of the queue — the batch ERPNext was
    about to hand to the next picker, which is both the likeliest place for
    units to have gone missing and the one whose next pick would fail.
    A surplus goes on the back, the batch nothing is waiting for.

    Returns [(batch_no, qty), ...] covering EVERY batch in the bin: one left
    out is one the reconciliation would never touch, so its stock would
    survive a count that said the shelf was empty.
    """
    plan = [[b, q] for b, q in avail]
    have = 0.0
    for _b, q in plan:
        have += q
    if counted < have:
        short = have - counted
        for row in plan:
            take = min(short, row[1])
            row[1] -= take
            short -= take
            if short <= 0:
                break
    elif counted > have and plan:
        plan[-1][1] += counted - have
    return [(b, q) for b, q in plan]


def _batch_bundle(item_code, warehouse, counted, company):
    """A draft Serial and Batch Bundle holding the counted stock. Returns its
    name, or None when the item is not batch-tracked."""
    if not frappe.get_cached_value("Item", item_code, "has_batch_no"):
        return None
    avail = _available_batches(item_code, warehouse)
    if not avail:
        # Nothing on the shelf to reconcile against and the counter found
        # something — the units need a batch to belong to. Minting one is
        # ERPNext's own receiving path; an item that forbids it is a real
        # decision for a human, not something to guess at.
        if not counted:
            return None
        if not frappe.get_cached_value("Item", item_code, "create_new_batch"):
            frappe.throw(
                f"{item_code} is batch-tracked and this shelf has no batch to "
                "count against. It needs a Stock Reconciliation with the batch "
                "named by hand.")
        from erpnext.stock.serial_batch_bundle import SerialBatchCreation
        doc = SerialBatchCreation({
            "item_code": item_code, "warehouse": warehouse,
            "posting_date": nowdate(), "posting_time": nowtime(),
            "voucher_type": "Stock Reconciliation", "company": company,
            "type_of_transaction": "Inward", "qty": counted,
            "do_not_submit": True,
        }).make_serial_and_batch_bundle()
        return doc.name if doc and doc.get("name") else None

    bundle = frappe.get_doc({
        "doctype": "Serial and Batch Bundle",
        "item_code": item_code,
        "warehouse": warehouse,
        "posting_date": nowdate(),
        "posting_time": nowtime(),
        "company": company,
        "voucher_type": "Stock Reconciliation",
        "type_of_transaction": "Inward",
        "entries": [{"batch_no": b, "qty": q, "warehouse": warehouse}
                    for b, q in _plan_batches(avail, float(counted))],
    })
    bundle.flags.ignore_permissions = True
    bundle.save()
    return bundle.name


def _apply_count_moves(warehouse, moves):
    """The count's transfers, as ONE submitted Material Transfer.

    A short count whose missing pieces the counter can SEE on another shelf
    is a relocation, not a loss — recording it as two reconciliations would
    invent an expense and a gain that never happened (and every reco also
    breaks the sum-vs-chain reading of that bin forever). One Stock Entry
    holds every move of this count, so they land atomically.

    Directions: "out" = pieces belong here on the book but physically sit on
    `other` (transfer warehouse -> other); "in" = extra pieces found here
    that came from `other` (transfer other -> warehouse)."""
    if isinstance(moves, str):
        moves = json.loads(moves)
    moves = moves or []
    if not moves:
        return None
    if len(moves) > 100:
        frappe.throw("Too many moves for one count.")
    lines = []
    for m in moves:
        code = (m.get("item_code") or "").strip()
        qty = int(m.get("qty") or 0)
        other = (m.get("other") or "").strip()
        direction = (m.get("dir") or "out").strip()
        if not code or qty <= 0 or not other:
            continue
        if other == warehouse:
            frappe.throw("A count move needs a DIFFERENT shelf.")
        if not _valid_bin(other):
            frappe.throw(f"{other} is not a valid bin.")
        src, tgt = (warehouse, other) if direction == "out" else (other, warehouse)
        available = int(frappe.db.get_value(
            "Bin", {"warehouse": src, "item_code": code}, "actual_qty") or 0)
        if qty > available:
            frappe.throw(f"Only {available} of {code} in {src} — cannot move {qty}.")
        lines.append({"item_code": code, "qty": qty,
                      "s_warehouse": src, "t_warehouse": tgt})
    if not lines:
        return None
    company = frappe.db.get_value("Warehouse", warehouse, "company")         or frappe.defaults.get_global_default("company")
    se = frappe.get_doc({
        "doctype": "Stock Entry",
        "stock_entry_type": "Material Transfer",
        "company": company,
        "remarks": f"Cycle-count relocation of {warehouse} by {frappe.session.user}",
        "items": lines,
    })
    se.flags.ignore_permissions = True
    se.insert(ignore_permissions=True)
    se.submit()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return se.name


@frappe.whitelist()
def submit_count(warehouse, counts=None, note=None, moves=None):
    """The floor's count for one bin. Relocations the counter recorded are
    applied FIRST (they change the book), then only rows that still DIFFER
    from the book go into the draft reconciliation — a clean count creates
    nothing."""
    _gate()
    warehouse = (warehouse or "").strip()
    if not _valid_bin(warehouse):
        frappe.throw(f"{warehouse} is not a countable bin.")
    if isinstance(counts, str):
        counts = json.loads(counts)
    counts = counts or []
    if not counts:
        frappe.throw("Count at least one item.")
    if len(counts) > 500:
        frappe.throw("Too many lines for one count.")
    # Normalise here too: the session witness counts relocations, and over the
    # wire `moves` is still the raw JSON string.
    if isinstance(moves, str):
        moves = json.loads(moves or "[]")
    moves = moves or []

    moved_entry = _apply_count_moves(warehouse, moves)

    book = {r.item_code: r for r in frappe.db.sql(
        """SELECT item_code, actual_qty, valuation_rate FROM `tabBin`
           WHERE warehouse = %s""", (warehouse,), as_dict=True)}

    diffs, summary = [], []
    seen = set()
    units_counted = 0
    for c in counts:
        code = (c.get("item_code") or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        qty = int(c.get("qty") or 0)
        if qty < 0:
            frappe.throw(f"Negative count for {code}.")
        if not frappe.db.exists("Item", code):
            frappe.throw(f"Unknown item: {code}")
        units_counted += qty
        b = book.get(code)
        book_qty = int(b.actual_qty or 0) if b else 0
        if qty == book_qty:
            continue
        rate = float((b.valuation_rate if b else 0) or 0) \
            or float(frappe.db.get_value("Item", code, "valuation_rate") or 0)
        row = {"item_code": code, "warehouse": warehouse, "qty": qty,
               "valuation_rate": rate}
        if not rate:
            row["allow_zero_valuation_rate"] = 1
        diffs.append(row)
        summary.append({"itemCode": code, "counted": qty, "book": book_qty,
                        "delta": qty - book_qty})
    if not diffs:
        # A perfect shelf is the count's best outcome and leaves nothing for
        # ERPNext to correct — the session row is the ONLY proof the walk
        # happened, so it is filed before the commit like any other result.
        _log_session(warehouse, len(seen), 0, units_counted,
                     len(moves), "")
        frappe.db.commit()
        return {"ok": True, "clean": True, "counted": len(seen),
                "moved": moved_entry}

    company = frappe.db.get_value("Warehouse", warehouse, "company") \
        or frappe.defaults.get_global_default("company")

    # Batch-tracked rows carry a bundle saying which batch each counted unit
    # is; without one ERPNext refuses the draft outright. Built after the
    # differences are known so a clean count costs nothing, and rolled back
    # together — a half-attached count would leave drafts nobody can read.
    made = []
    try:
        for row in diffs:
            b = _batch_bundle(row["item_code"], warehouse, row["qty"], company)
            if b:
                made.append(b)
                row["serial_and_batch_bundle"] = b
    except Exception:
        for b in made:
            try:
                frappe.delete_doc("Serial and Batch Bundle", b,
                                  force=1, ignore_permissions=True)
            except Exception:
                pass
        raise

    doc = frappe.get_doc({
        "doctype": "Stock Reconciliation",
        "purpose": "Stock Reconciliation",
        "posting_date": nowdate(),
        "posting_time": nowtime(),
        "company": company,
        "expense_account": frappe.db.get_value("Company", company, "stock_adjustment_account"),
        "cost_center": frappe.db.get_value("Company", company, "cost_center"),
        "items": diffs,
    })
    doc.flags.ignore_permissions = True
    try:
        doc.insert(ignore_permissions=True)
    except Exception:
        for b in made:
            try:
                frappe.delete_doc("Serial and Batch Bundle", b,
                                  force=1, ignore_permissions=True)
            except Exception:
                pass
        raise
    note = (note or "").strip()
    doc.add_comment("Comment",
                    f"Portal cycle count of {warehouse} by {frappe.session.user}"
                    + (f" — {note}" if note else ""))
    reg = _registry()
    reg.append(doc.name)
    _save_registry(reg)
    _log_session(warehouse, len(seen), len(diffs), units_counted,
                 len(moves), doc.name)
    frappe.db.commit()
    return {"ok": True, "clean": False, "draft": doc.name,
            "counted": len(seen), "diffs": summary, "moved": moved_entry}


def _pending():
    """Portal-created draft reconciliations, live-checked against the DB."""
    reg = _registry()
    if not reg:
        return []
    rows = frappe.db.sql(
        """SELECT name, owner, creation, docstatus FROM `tabStock Reconciliation`
           WHERE name IN ({})""".format(", ".join(["%s"] * len(reg))),
        tuple(reg), as_dict=True)
    alive = {r.name: r for r in rows if r.docstatus == 0}
    # self-heal: drop approved/deleted names from the registry
    if len(alive) != len(reg):
        _save_registry([n for n in reg if n in alive])
    out = []
    for name, r in alive.items():
        items = frappe.db.sql(
            """SELECT sri.item_code, sri.warehouse, sri.qty, sri.valuation_rate,
                      it.custom_sku AS sku,
                      COALESCE(NULLIF(it.item_name,''), sri.item_code) AS iname,
                      COALESCE(b.actual_qty, 0) AS live
               FROM `tabStock Reconciliation Item` sri
               LEFT JOIN `tabItem` it ON it.name = sri.item_code
               LEFT JOIN `tabBin` b ON b.item_code = sri.item_code
                    AND b.warehouse = sri.warehouse
               WHERE sri.parent = %s ORDER BY ABS(sri.qty - COALESCE(b.actual_qty,0)) DESC""",
            (name,), as_dict=True)
        value_delta = sum(
            (int(i.qty or 0) - int(i.live or 0)) * float(i.valuation_rate or 0)
            for i in items)
        out.append({
            "name": name, "owner": r.owner or "",
            "created": str(r.creation)[:16],
            "warehouse": items[0].warehouse if items else "",
            "lines": len(items),
            "valueDelta": round(value_delta),
            "items": [{
                "itemCode": i.item_code, "sku": i.sku or "", "name": i.iname,
                "counted": int(i.qty or 0), "book": int(i.live or 0),
                "delta": int(i.qty or 0) - int(i.live or 0),
            } for i in items[:12]],
            "more": max(0, len(items) - 12),
        })
    out.sort(key=lambda x: x["created"], reverse=True)
    return out


@frappe.whitelist()
def pending_counts():
    _gate()
    return {"pending": _pending(), "canApprove": _is_manager()}


@frappe.whitelist()
def approve_count(name):
    """Manager: submit the draft — ERPNext posts the differences."""
    if not _is_manager():
        frappe.throw("Only a manager can approve a count.", frappe.PermissionError)
    if name not in _registry():
        frappe.throw("Not a portal cycle count.")
    doc = frappe.get_doc("Stock Reconciliation", name)
    if doc.docstatus != 0:
        frappe.throw("Already processed.")
    doc.flags.ignore_permissions = True
    doc.submit()
    _save_registry([n for n in _registry() if n != name])
    frappe.db.commit()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return {"ok": True, "name": name,
            "differenceAmount": round(float(doc.difference_amount or 0))}


@frappe.whitelist()
def discard_count(name):
    """Manager or the counter themself: throw the draft away."""
    _gate()
    if name not in _registry():
        frappe.throw("Not a portal cycle count.")
    doc = frappe.get_doc("Stock Reconciliation", name)
    if doc.docstatus != 0:
        frappe.throw("Already processed.")
    if not _is_manager() and doc.owner != frappe.session.user:
        frappe.throw("Only a manager can discard someone else's count.",
                     frappe.PermissionError)
    # The batch bundles the draft carries are only meaningful as part of it —
    # left behind they are unreadable drafts nobody can trace back to a count.
    # Named before the delete, removed after: the reconciliation is what links
    # to them, so it has to go first.
    bundles = [b for b in
               [r.get("serial_and_batch_bundle") for r in doc.items]
               + [r.get("current_serial_and_batch_bundle") for r in doc.items] if b]
    doc.flags.ignore_permissions = True
    doc.delete(ignore_permissions=True)
    for b in bundles:
        try:
            frappe.delete_doc("Serial and Batch Bundle", b,
                              force=1, ignore_permissions=True)
        except Exception:
            # A bundle another document also points at is not ours to remove.
            pass
    _save_registry([n for n in _registry() if n != name])
    frappe.db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Count control — the manager's view of the campaign.
# ---------------------------------------------------------------------------

def _control_gate():
    # is_portal_admin() was too wide a door for this: it trusts "Stock
    # Manager", which on this site reaches the contact centre and accounts.
    # Counting coverage is warehouse management, so the audience is too.
    from logistics_portal.api.permissions import is_ops_admin
    if not is_ops_admin():
        frappe.throw("Warehouse management only.", frappe.PermissionError)


def _countable_bins():
    """[(warehouse, stocked_lines, units)] for every bin the floor may count."""
    cond, args = _movable_condition("name")
    whs = [w[0] for w in frappe.db.sql(
        f"""SELECT name FROM `tabWarehouse`
            WHERE is_group = 0 AND disabled = 0 AND {cond} ORDER BY name""",
        tuple(args))]
    if not whs:
        return []
    ph = ", ".join(["%s"] * len(whs))
    held = {r[0]: (int(r[1] or 0), int(r[2] or 0)) for r in frappe.db.sql(
        f"""SELECT warehouse, COUNT(*), COALESCE(SUM(actual_qty), 0)
            FROM `tabBin` WHERE warehouse IN ({ph}) AND actual_qty <> 0
            GROUP BY warehouse""", tuple(whs))}
    return [(w, held.get(w, (0, 0))[0], held.get(w, (0, 0))[1]) for w in whs]


def _evidence(days, source="all"):
    """What proves a bin was counted, newest first per bin.

    Three kinds of proof, and the board can be filtered to any of them:

      session — a count filed through the portal since the witness shipped.
                The only proof that survives a CLEAN count.
      portal  — an older portal count, recognised by the comment
                `submit_count` writes on the draft. That comment outlives
                approval, so the team's first days with the tool are still
                readable even though no session row existed yet.
      desk    — everything else: a reconciliation posted from the Desk.

    A reconciliation a session already points at is the SAME count seen
    twice; the session wins and the copy is dropped."""
    out = {}
    people = {}

    def credit(user, wh, lines, diffs, units, at, src):
        p = people.setdefault(user, {"user": user, "sessions": 0, "bins": set(),
                                     "lines": 0, "diffs": 0, "units": 0,
                                     "last": "", "src": src})
        p["sessions"] += 1
        p["bins"].add(wh)
        p["lines"] += lines
        p["diffs"] += diffs
        p["units"] += units
        if at > p["last"]:
            p["last"] = at
        prev = out.get(wh)
        if not prev or at > prev["at"]:
            out[wh] = {"at": at, "by": user, "src": src, "lines": lines,
                       "diffs": diffs}

    claimed = set()
    if frappe.db.exists("DocType", SESSION_DT) and source != "desk":
        # Guarded: the reconciliation half of the picture is worth showing on
        # its own, so a schema this read cannot satisfy costs the page its
        # session rows (visible as 0 in the source split) rather than the
        # whole screen.
        try:
            sessions = frappe.db.sql(
                f"""SELECT warehouse, counter, line_count, diff_lines, units,
                           draft, creation
                    FROM `tab{SESSION_DT}`
                    WHERE creation >= DATE_SUB(NOW(), INTERVAL %s DAY)""",
                (days,), as_dict=True)
        except Exception:
            frappe.log_error(frappe.get_traceback()[:2000],
                             "cycle_count._evidence sessions")
            sessions = []
        for r in sessions:
            if r.draft:
                claimed.add(r.draft)
            credit(r.counter or "?", r.warehouse, int(r.line_count or 0),
                   int(r.diff_lines or 0), int(r.units or 0),
                   str(r.creation)[:16], "session")

    # Counts only. Accounts revalue stock with this same doctype — same
    # quantity, new rate — and 388 such rows on the Return Zone
    # (2026-09-12) would otherwise report that zone as freshly counted by
    # someone who never walked it. The ledger cannot tell the two apart (a
    # reconciliation's entries carry actual_qty = 0 either way), so the test
    # is whether any row actually changed a quantity.
    reco_rows = frappe.db.sql(
        """SELECT sr.name, sr.owner, sr.posting_date AS d, sr.creation,
                  sri.warehouse AS wh, COUNT(*) AS rows_n,
                  COALESCE(SUM(sri.qty), 0) AS units
           FROM `tabStock Reconciliation Item` sri
           JOIN `tabStock Reconciliation` sr ON sr.name = sri.parent
           WHERE sr.docstatus = 1
             AND sr.posting_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
             AND EXISTS (SELECT 1 FROM `tabStock Reconciliation Item` i
                         WHERE i.parent = sr.name
                           AND i.qty <> i.current_qty)
           GROUP BY sr.name, sri.warehouse""", (days,), as_dict=True)

    # Which of those came from the portal. `submit_count` comments the draft
    # as it files it and that comment outlives approval, so it is the only
    # thing that can tell a portal count from a Desk one after the fact.
    portal = set()
    rnames = list({r.name for r in reco_rows if r.name not in claimed})
    if rnames:
        ph = ", ".join(["%s"] * len(rnames))
        portal = {x[0] for x in frappe.db.sql(
            f"""SELECT DISTINCT reference_name FROM `tabComment`
                WHERE reference_doctype = 'Stock Reconciliation'
                  AND reference_name IN ({ph})
                  AND content LIKE 'Portal cycle count%%'""", tuple(rnames))}

    for r in reco_rows:
        if r.name in claimed:
            continue
        src = "portal" if r.name in portal else "desk"
        if source == "portal" and src != "portal":
            continue
        if source == "desk" and src != "desk":
            continue
        credit(r.owner or "?", r.wh, int(r.rows_n or 0), int(r.rows_n or 0),
               int(r.units or 0), str(r.creation)[:16], src)

    for p in people.values():
        p["binCount"] = len(p["bins"])
        del p["bins"]
    return out, people


@frappe.whitelist()
def progress(days=30, source="all"):
    """Campaign control: how much of the warehouse has been counted, aisle by
    aisle, and who is doing the counting.

    `source` narrows it to where the count came from — "portal" answers "how
    far has the team got with the tool", which is a different question from
    "how much of the warehouse is trustworthy"."""
    _control_gate()
    days = min(max(int(days or 30), 1), 180)
    source = source if source in ("all", "portal", "desk") else "all"
    bins = _countable_bins()
    seen, people = _evidence(days, source)

    zones, uncounted = {}, []
    tot = {"bins": 0, "stocked": 0, "counted": 0, "countedStocked": 0,
           "units": 0, "unitsCounted": 0}
    for wh, lines, units in bins:
        z = zones.setdefault(_zone_of(wh), {
            "zone": _zone_of(wh), "bins": 0, "stocked": 0, "counted": 0,
            "countedStocked": 0, "units": 0, "unitsCounted": 0,
            "diffBins": 0, "lastAt": "", "lastBy": ""})
        ev = seen.get(wh)
        stocked = 1 if lines > 0 else 0
        z["bins"] += 1
        z["stocked"] += stocked
        z["units"] += units
        tot["bins"] += 1
        tot["stocked"] += stocked
        tot["units"] += units
        if ev:
            z["counted"] += 1
            z["countedStocked"] += stocked
            z["unitsCounted"] += units
            tot["counted"] += 1
            tot["countedStocked"] += stocked
            tot["unitsCounted"] += units
            if ev["diffs"]:
                z["diffBins"] += 1
            if ev["at"] > z["lastAt"]:
                z["lastAt"] = ev["at"]
                z["lastBy"] = ev["by"]
        elif stocked:
            uncounted.append({"bin": wh.replace(" - JM", ""), "warehouse": wh,
                              "zone": _zone_of(wh), "lines": lines,
                              "units": units})

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else 0.0

    zrows = []
    for z in zones.values():
        # An empty bin still needs a walk-by, but the WORK lives in the bins
        # that hold something — so the headline percentage is the stocked one
        # and the all-bins figure rides alongside it, never instead of it.
        z["pct"] = pct(z["countedStocked"], z["stocked"])
        z["pctAll"] = pct(z["counted"], z["bins"])
        z["left"] = z["stocked"] - z["countedStocked"]
        zrows.append(z)
    zrows.sort(key=lambda r: (-r["stocked"], r["zone"]))

    uncounted.sort(key=lambda r: -r["units"])
    prows = sorted(people.values(), key=lambda p: -p["lines"])
    for p in prows:
        p["name"] = (frappe.db.get_value("User", p["user"], "full_name")
                     or p["user"].split("@")[0])

    daily = []
    if frappe.db.exists("DocType", SESSION_DT):
        try:
            daily = [{"day": str(r[0]), "bins": int(r[1] or 0),
                      "lines": int(r[2] or 0)} for r in frappe.db.sql(
                f"""SELECT DATE(creation), COUNT(DISTINCT warehouse), SUM(line_count)
                    FROM `tab{SESSION_DT}`
                    WHERE creation >= DATE_SUB(NOW(), INTERVAL %s DAY)
                    GROUP BY DATE(creation) ORDER BY DATE(creation)""", (days,))]
        except Exception:
            daily = []

    return {
        "days": days,
        "headline": {
            "bins": tot["bins"], "stocked": tot["stocked"],
            "counted": tot["counted"], "countedStocked": tot["countedStocked"],
            "pct": pct(tot["countedStocked"], tot["stocked"]),
            "pctAll": pct(tot["counted"], tot["bins"]),
            "units": tot["units"], "unitsCounted": tot["unitsCounted"],
            "left": tot["stocked"] - tot["countedStocked"],
            "pending": len(_pending()),
            # How much of the picture each source carries. While this is all
            # reconciliations, the coverage number is a FLOOR, not a fact:
            # a clean count left no reconciliation to find.
            "bySession": sum(1 for e in seen.values() if e["src"] == "session"),
            "byPortal": sum(1 for e in seen.values() if e["src"] == "portal"),
            "byDesk": sum(1 for e in seen.values() if e["src"] == "desk"),
        },
        "source": source,
        "zones": zrows,
        "people": prows,
        "uncounted": uncounted[:40],
        "uncountedTotal": len(uncounted),
        "daily": daily,
    }
