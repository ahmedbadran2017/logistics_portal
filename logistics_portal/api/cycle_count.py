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

import frappe
from frappe.utils import nowdate, nowtime

from logistics_portal.api.stock_moves import _movable_condition

_REG = "lp_cycle_counts"


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("manager", "dispatcher", "returns", "packer"):
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


@frappe.whitelist()
def submit_count(warehouse, counts=None, note=None):
    """The floor's count for one bin. Only rows that DIFFER from the book go
    into the draft reconciliation — a clean count creates nothing."""
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

    book = {r.item_code: r for r in frappe.db.sql(
        """SELECT item_code, actual_qty, valuation_rate FROM `tabBin`
           WHERE warehouse = %s""", (warehouse,), as_dict=True)}

    diffs, summary = [], []
    seen = set()
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
        return {"ok": True, "clean": True, "counted": len(seen)}

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
    frappe.db.commit()
    return {"ok": True, "clean": False, "draft": doc.name,
            "counted": len(seen), "diffs": summary}


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
