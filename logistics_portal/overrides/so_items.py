"""Editing a confirmed order's items once the warehouse has it.

The confirmation and CS teams change orders after confirmation for good
reasons — the customer agrees to go without a product that is out, or takes
one instead of two — and they do it from the Desk with "Update Items"
(erpnext update_child_qty_rate). The edit was always accepted, and the floor
never heard of it:

  * #263123, 2026-10-05: a bag dropped at 12:23 while the order sat on
    PL-56588; the bag was picked at 13:50 and sorted into the box anyway, the
    Delivery Note failed on the missing line and the parcel left with none.
  * J-010973, 2026-10-09: cut from 2 to 1 three minutes after PL-56650 was
    made; both pieces scanned, every submit refused for over-picking, and the
    list had to be cancelled and rebuilt.

Refusing the edit would only push the team into cancelling and re-creating
orders. So the rule follows where the goods are (the same doctrine as
api/stop.py): the edit goes through while the paperwork can still follow it,
the floor is told what to put back, and it is refused only where it would
send a wrong parcel.

    not on a pick list       anything goes
    on a draft list, nothing scanned yet
                             fewer / removed: the list's rows follow at once
                             more / added:    the order leaves the list and goes
                                              back to the pool, to be picked whole
    on a draft list, pieces already scanned
                             fewer / removed: rows follow, the picker gets a bell
                                              naming the shelf to put back to
                             more / added:    refused — Stop it and re-order
    labelled (AWB / label / Delivery Note) or on a submitted list
                             any change to items, quantities or prices refused:
                             the label carries the old amount — use Stop

overrides/pick_list.py still trims and drops at the submit, for any change
that reaches a list by another road.
"""

import json

import frappe
from frappe.utils import flt

_EI = "ecommerce_integrations.events.whitelisted_methods.sales_order.custom_update_child_qty_rate"


def _erpnext_update(*args, **kwargs):
    """The method this wraps. ecommerce_integrations already overrides it
    (override_whitelisted_methods, its own Sales Order bookkeeping) and the
    LAST override wins — ours — so theirs must still run underneath."""
    try:
        fn = frappe.get_attr(_EI)
    except Exception:
        from erpnext.controllers.accounts_controller import update_child_qty_rate as fn
    return fn(*args, **kwargs)

_LABELLED = ("Label Generated", "Label Printed", "Shipped", "In transit", "In Transit")


@frappe.whitelist()
def update_child_qty_rate(parent_doctype, trans_items, parent_doctype_name, child_docname="items"):
    if parent_doctype != "Sales Order":
        return _erpnext_update(parent_doctype, trans_items, parent_doctype_name, child_docname)
    so = parent_doctype_name
    plan = _plan(so, trans_items)
    result = _erpnext_update(parent_doctype, trans_items, parent_doctype_name, child_docname)
    if plan:
        _follow(so, plan)
    return result


def _plan(so, trans_items):
    """What the edit changes, checked against where the order stands.
    Throws when the edit must not happen; returns what the lists must do."""
    items = json.loads(trans_items) if isinstance(trans_items, str) else (trans_items or [])
    before = {r.name: r for r in frappe.db.sql(
        "SELECT name, item_code, qty, rate FROM `tabSales Order Item` WHERE parent = %s", (so,), as_dict=True)}
    kept = {d.get("docname"): d for d in items if d.get("docname") in before}
    added = [d for d in items if not d.get("docname")]
    removed = [n for n in before if n not in kept]
    more, less, priced = [], {}, False
    for n, d in kept.items():
        q_old, q_new = flt(before[n].qty), flt(d.get("qty"))
        if q_new > q_old:
            more.append(n)
        elif q_new < q_old:
            less[n] = q_new
        if flt(d.get("rate")) != flt(before[n].rate):
            priced = True
    for n in removed:
        less[n] = 0
    if not (added or more or less or priced):
        return None
    if (frappe.db.get_value("Sales Order", so, "custom_logistics_status") or "") in ("Delivered", "Returned"):
        return None       # the parcel's story is over: accounting's edit, not the floor's

    if _labelled(so):
        frappe.throw(
            f"{so} already has its carrier label — the label carries the old amount. "
            "Use Stop on the order and create a new one.<br>"
            f"الأوردر {so} طلعتله بوليصة بالمبلغ القديم — استخدم Stop واعمل أوردر جديد.",
            title="Order already labelled")

    rows = frappe.db.sql(
        """SELECT pli.name, pli.parent, p.docstatus, p.custom_assigned_picker AS picker, p.owner,
                  pli.item_code, pli.warehouse, pli.qty, pli.stock_qty, pli.conversion_factor,
                  COALESCE(pli.custom_scanned_qty, 0) AS scanned, COALESCE(pli.picked_qty, 0) AS picked,
                  pli.sales_order_item, NULLIF(pli.product_bundle_item, '') AS bundle_line
           FROM `tabPick List Item` pli JOIN `tabPick List` p ON p.name = pli.parent
           WHERE pli.sales_order = %s AND p.docstatus < 2""", (so,), as_dict=True)
    if not rows:
        return None
    if any(r.docstatus == 1 for r in rows):
        frappe.throw(
            f"{so} is on a submitted pick list and is being sorted. Use Stop on the order instead.<br>"
            f"الأوردر {so} على pick list اتعمله submit وبيتفرز — استخدم Stop.",
            title="Order is being prepared")
    scanned = any(r.scanned > 0 for r in rows)
    if (added or more) and scanned:
        frappe.throw(
            f"{so} is being picked — pieces are already in the picker's hands, so nothing can be "
            "added to it now. Use Stop on the order and create a new one.<br>"
            f"الأوردر {so} بيتلم دلوقتي — ما ينفعش يتزود عليه. استخدم Stop واعمل أوردر جديد.",
            title="Order is being picked")
    bundle_lines = {r.bundle_line for r in rows if r.bundle_line}
    # A bundle's components cannot be trimmed one by one, and a growing order
    # cannot be completed on this list: either way the order leaves the list.
    pull = bool(added or more) or any(n in bundle_lines for n in less)
    if not (pull or less):
        return None       # a price change: nothing on the list moves
    return {"rows": rows, "less": less, "pull": pull}


def _labelled(so):
    """Labelled and not yet back in our hands as a finished story: once the
    parcel is delivered or returned, an edit is accounting's business (price
    corrections, returns), not a wrong parcel."""
    s = frappe.db.get_value("Sales Order", so, ["custom_awb", "custom_label_url", "custom_logistics_status"],
                           as_dict=True) or {}
    if (s.get("custom_logistics_status") or "") in ("Delivered", "Returned"):
        return False
    if s.get("custom_awb") or s.get("custom_label_url") or (s.get("custom_logistics_status") or "") in _LABELLED:
        return True
    return bool(frappe.db.sql(
        """SELECT 1 FROM `tabDelivery Note Item` dni JOIN `tabDelivery Note` d ON d.name = dni.parent
           WHERE dni.against_sales_order = %s AND d.docstatus = 1 AND d.is_return = 0 LIMIT 1""", (so,)))


def _follow(so, plan):
    """Make the draft list match the edited order; tell the picker what to put back."""
    rows, less = plan["rows"], plan["less"]
    back = []          # (picker, list, item, shelf, pieces)
    if plan["pull"]:
        for r in rows:
            if r.scanned > 0:
                back.append((r.picker or r.owner, r.parent, r.item_code, r.warehouse, int(r.scanned)))
        frappe.db.sql("DELETE FROM `tabPick List Item` WHERE name IN %s", (tuple(r.name for r in rows),))
        note = "left the list: the order changed and goes back to the pool to be picked whole"
    else:
        for line, q_new in less.items():
            mine = sorted([r for r in rows if r.sales_order_item == line and not r.bundle_line],
                          key=lambda r: r.name)
            room = q_new
            for r in mine:
                keep = min(flt(r.qty), max(room, 0))
                room -= keep
                extra = int(max(r.scanned - keep, 0))
                if extra:
                    back.append((r.picker or r.owner, r.parent, r.item_code, r.warehouse, extra))
                if keep <= 0:
                    frappe.db.sql("DELETE FROM `tabPick List Item` WHERE name = %s", (r.name,))
                    continue
                cf = flt(r.conversion_factor or 1) or 1
                frappe.db.sql(
                    """UPDATE `tabPick List Item` SET qty = %s, stock_qty = %s,
                              picked_qty = LEAST(COALESCE(picked_qty, 0), %s),
                              custom_scanned_qty = LEAST(COALESCE(custom_scanned_qty, 0), %s)
                       WHERE name = %s""", (keep, keep * cf, keep * cf, keep, r.name))
        note = "followed the edit on its pick list"
    lists = sorted({r.parent for r in rows})
    by = frappe.session.user
    try:
        frappe.get_doc("Sales Order", so).add_comment(
            "Comment", f"Items edited while on {', '.join(lists)} — {note}"
                       + ("; put back: " + ", ".join(f"{b[4]} × {b[2]} → {b[3]}" for b in back) if back else "")
                       + f" · by {by}")
    except Exception:
        pass
    for user, pl, item, shelf, n in back:
        _bell(user, pl, so, item, shelf, n)


_PUT_BACK = {
    "en": ("Put a piece back", "{so} changed — put {n} × {item} back on {shelf}"),
    "fr": ("Remettre une pièce", "{so} a changé — remettez {n} × {item} en {shelf}"),
    "ar": ("رجّع قطعة", "الأوردر {so} اتعدّل — رجّع {n} × {item} على {shelf}"),
}


def _bell(user, pick_list, so, item, shelf, n):
    if not user:
        return
    shelf = (shelf or "").replace(" - JM", "")
    i18n = {k: {"t": t, "b": b.format(so=so, n=n, item=item, shelf=shelf)} for k, (t, b) in _PUT_BACK.items()}
    packed = json.dumps({"lp": i18n, "sev": "warning", "kind": "put_back"}, ensure_ascii=False)
    try:
        frappe.get_doc({
            "doctype": "Notification Log", "subject": f"{i18n['en']['t']} · {pick_list}",
            "email_content": i18n["en"]["b"] + "\n<!--lp-i18n " + packed.replace("--", "- -") + " -->",
            "type": "Alert", "document_type": "Pick List", "document_name": pick_list, "for_user": user,
        }).insert(ignore_permissions=True)
        frappe.publish_realtime("logistics_alert", {"severity": "warning", "title": i18n["en"]["t"],
                                                    "detail": i18n["en"]["b"], "i18n": i18n,
                                                    "audience": "user"}, user=user)
    except Exception:
        frappe.log_error(frappe.get_traceback()[-1200:], "so_items put-back bell")
