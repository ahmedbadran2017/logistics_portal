"""Kits — a product the floor ASSEMBLES from other products we stock.

MCH09178 (12 square boxes: 4 × 555 ml, 4 × 1205 ml, 4 × 1700 ml) stopped
arriving as a product; the floor builds it from three sets of 12 we hold —
MCH009884 (555 ml), MCH09176 (1205 ml), MCH09177 (1700 ml): one set of each
makes THREE kits. Until 2026-11-16 the floor recorded each batch as a cycle
count (+300 on 13/11, +300 on 16/11): the kit rose out of nowhere at a guessed
rate, 32,236 MAD booked as a stock gain, and the 200 sets of each component
that went into them stayed on the books.

The one honest record of "these became that" is ERPNext's Repack Stock
Entry: the components leave at their own cost and the kit arrives carrying
exactly that cost — no gain, no loss, stock account to stock account. This
module is that, with a screen in front of it:

* recipes — kit = components per batch, and the kits one batch yields;
* assemble — N kits (whole batches only), components from the bins the
  floor took them from, kits onto their shelf, one SKU label per kit;
* account_count — the catch-up: a past count that raised a kit gets its
  missing half, the components leaving, at the same moment;
* warn_kit_count — a count that raises a kit is refused at submit, so the
  next batch goes through Assemble instead.
"""

import datetime
import json

import frappe
from frappe.utils import cint, flt, now_datetime

COMPANY = "Justyol Morocco"
RECIPES_KEY = "lp_kit_recipes"
TAG = "Kit assembly"
LABEL_STATION = "kits"

# Seeded from Ahmed's recipe (2026-11-16). Edited on the Kits screen after.
DEFAULT_RECIPES = [{
    "kit": "45866447077630",                       # MCH09178
    "yield": 3,
    "components": [
        {"item_code": "45779760283902", "qty": 1},  # MCH009884 — 12 × 555 ml
        {"item_code": "45779741180158", "qty": 1},  # MCH09176 — 12 × 1205 ml
        {"item_code": "45862527402238", "qty": 1},  # MCH09177 — 12 × 1700 ml
    ],
    "target": "PLT - JM",
}]


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("manager", "dispatcher", "returns", "packer"):
        frappe.throw("Not authorized to assemble kits.", frappe.PermissionError)


def _is_manager():
    from logistics_portal.api.auth import resolve_role
    return resolve_role(frappe.session.user) == "manager"


def recipes():
    raw = frappe.db.get_default(RECIPES_KEY)
    try:
        out = json.loads(raw) if raw else None
    except Exception:
        out = None
    return out if isinstance(out, list) else [dict(r) for r in DEFAULT_RECIPES]


def recipe_for(kit):
    for r in recipes():
        if r.get("kit") == kit:
            return r
    return None


def kit_items():
    return {r["kit"] for r in recipes() if r.get("kit")}


def _item(code):
    return frappe.db.get_value("Item", code, ["name", "custom_sku", "item_name", "image",
                                              "stock_uom", "is_stock_item"], as_dict=True) or {}


def _sources(item_code):
    """Bins holding the item that stock may leave from, with what is free
    there (actual − held for orders), richest first."""
    from logistics_portal.api.stock_moves import _movable_condition
    from logistics_portal.api.consignment import is_consignment_warehouse
    cond, args = _movable_condition("b.warehouse", as_source=True)
    rows = frappe.db.sql(
        f"""SELECT b.warehouse, b.actual_qty, IFNULL(b.reserved_stock, 0) AS held
            FROM `tabBin` b WHERE b.item_code = %s AND b.actual_qty > 0 AND {cond}
            ORDER BY b.actual_qty DESC""", tuple([item_code, *args]), as_dict=True)
    return [{"warehouse": r.warehouse, "qty": int(flt(r.actual_qty)),
             "free": max(int(flt(r.actual_qty) - flt(r.held)), 0)}
            for r in rows if not is_consignment_warehouse(r.warehouse)]


def _waiting(kit):
    """Pieces of the kit confirmed orders still wait for (sold alone, or
    inside a bundle that names it)."""
    direct = flt(frappe.db.sql(
        """SELECT SUM(soi.stock_qty - soi.delivered_qty * soi.conversion_factor)
           FROM `tabSales Order Item` soi JOIN `tabSales Order` so ON so.name = soi.parent
           WHERE soi.item_code = %s AND so.docstatus = 1 AND so.company = %s
             AND so.status NOT IN ('Closed', 'Completed') AND so.custom_sales_status = 'Confirmed'
             AND soi.delivered_qty < soi.qty""", (kit, COMPANY))[0][0])
    packed = flt(frappe.db.sql(
        """SELECT SUM(pi.qty) FROM `tabPacked Item` pi JOIN `tabSales Order` so ON so.name = pi.parent
           WHERE pi.item_code = %s AND pi.parenttype = 'Sales Order' AND so.docstatus = 1
             AND so.company = %s AND so.status NOT IN ('Closed', 'Completed', 'To Bill')
             AND so.custom_sales_status = 'Confirmed'""", (kit, COMPANY))[0][0])
    return int(direct + packed)


def _card(r):
    kit = _item(r["kit"])
    comps, batches = [], None
    for c in r.get("components") or []:
        it = _item(c["item_code"])
        src = _sources(c["item_code"])
        free = sum(s["free"] for s in src)
        per = max(cint(c.get("qty")), 1)
        b = free // per
        batches = b if batches is None else min(batches, b)
        comps.append({"itemCode": c["item_code"], "sku": it.get("custom_sku") or "",
                      "name": it.get("item_name") or c["item_code"], "image": it.get("image") or "",
                      "perBatch": per, "free": free, "sources": src})
    on_shelf = sum(s["qty"] for s in _sources(r["kit"]))
    y = max(cint(r.get("yield")), 1)
    return {"kit": r["kit"], "sku": kit.get("custom_sku") or "", "name": kit.get("item_name") or r["kit"],
            "image": kit.get("image") or "", "yield": y, "target": r.get("target") or "",
            "onShelf": on_shelf, "waiting": _waiting(r["kit"]),
            "buildable": (batches or 0) * y, "components": comps}


def _recent(limit=15):
    rows = frappe.db.sql(
        """SELECT se.name, se.owner, se.posting_date, se.posting_time, se.docstatus, se.remarks,
                  sed.item_code, sed.qty, sed.basic_rate
           FROM `tabStock Entry` se JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
           WHERE se.purpose = 'Repack' AND se.remarks LIKE %s AND sed.is_finished_item = 1
           ORDER BY se.creation DESC LIMIT %s""", (TAG + "%", limit), as_dict=True)
    return [{"entry": r.name, "by": (r.owner or "").split("@")[0], "at": f"{r.posting_date} {str(r.posting_time)[:5]}",
             "kit": r.item_code, "sku": frappe.db.get_value("Item", r.item_code, "custom_sku") or "",
             "qty": int(flt(r.qty)), "rate": round(flt(r.basic_rate), 2), "cancelled": r.docstatus == 2,
             "note": (r.remarks or "")[len(TAG) + 2:][:120]} for r in rows]


@frappe.whitelist()
def boot():
    _gate()
    from logistics_portal.api.stock_moves import _movable_condition
    cond, args = _movable_condition("name")
    targets = [w[0] for w in frappe.db.sql(
        f"SELECT name FROM `tabWarehouse` WHERE is_group = 0 AND disabled = 0 AND {cond} ORDER BY name",
        tuple(args))]
    return {"kits": [_card(r) for r in recipes()], "recent": _recent(), "targets": targets,
            "isManager": _is_manager(), "station": LABEL_STATION}


def _repack(r, qty, target, sources, remarks, posting=None):
    """Build + submit the Repack for `qty` kits. `sources`: {item_code: warehouse}."""
    y = max(cint(r.get("yield")), 1)
    batches = qty // y
    rows = []
    for c in r["components"]:
        wh = (sources or {}).get(c["item_code"])
        if not wh:
            frappe.throw(f"Choose where {_item(c['item_code']).get('custom_sku') or c['item_code']} was taken from.")
        need = batches * max(cint(c.get("qty")), 1)
        rows.append({"item_code": c["item_code"], "qty": need, "s_warehouse": wh,
                     "uom": _item(c["item_code"]).get("stock_uom") or "Nos", "conversion_factor": 1})
    rows.append({"item_code": r["kit"], "qty": qty, "t_warehouse": target, "is_finished_item": 1,
                 "uom": _item(r["kit"]).get("stock_uom") or "Nos", "conversion_factor": 1})
    se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Repack", "purpose": "Repack",
                         "company": COMPANY, "remarks": remarks, "items": rows})
    if posting:
        se.set_posting_time = 1
        se.posting_date, se.posting_time = posting
    se.flags.ignore_permissions = True
    se.insert()
    se.submit()
    # A rollback inside another app's hook takes the entry with it silently
    # (crossdock_in, 2026-11-10). Only an entry that is still there counts.
    if frappe.db.get_value("Stock Entry", se.name, "docstatus") != 1:
        frappe.throw("The assembly was rolled back by the database — try again.")
    return se


@frappe.whitelist(methods=["POST"])
def assemble(kit, qty, target=None, sources=None, print_labels=1):
    """Record N kits assembled. Whole batches only: a kit whose batch yields
    3 is assembled 3, 6, 9… at a time — the floor cannot split a set."""
    _gate()
    r = recipe_for(kit)
    if not r:
        frappe.throw("This product has no kit recipe.")
    qty = cint(qty)
    y = max(cint(r.get("yield")), 1)
    if qty <= 0:
        frappe.throw("Enter how many kits were assembled.")
    if qty % y:
        frappe.throw(f"lp:kitBatch|{y}")
    target = (target or r.get("target") or "").strip()
    if not target or not frappe.db.exists("Warehouse", target):
        frappe.throw("Choose where the kits are put.")
    if isinstance(sources, str):
        sources = json.loads(sources or "{}")
    for c in r["components"]:
        wh = (sources or {}).get(c["item_code"])
        free = {s["warehouse"]: s["free"] for s in _sources(c["item_code"])}.get(wh, 0)
        need = qty // y * max(cint(c.get("qty")), 1)
        if need > free:
            sku = _item(c["item_code"]).get("custom_sku") or c["item_code"]
            frappe.throw(f"lp:kitShort|{sku} · {wh or '—'} : {free} / {need}")
    sku = _item(kit).get("custom_sku") or kit
    se = _repack(r, qty, target, sources,
                 f"{TAG}: {qty} × {sku} by {frappe.session.user}")
    frappe.db.commit()
    labels = 0
    if cint(print_labels):
        from logistics_portal.api.labelprint import queue_items
        labels = queue_items([(kit, qty)], LABEL_STATION)
        frappe.db.commit()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    rate = next((flt(i.basic_rate) for i in se.items if i.is_finished_item), 0)
    return {"ok": True, "entry": se.name, "qty": qty, "rate": round(rate, 2), "labels": labels}


def _resolve(code):
    """An item code, or the SKU the floor knows it by."""
    code = (code or "").strip()
    if code and frappe.db.exists("Item", code):
        return code
    hits = frappe.db.get_all("Item", filters={"custom_sku": code, "disabled": 0}, pluck="name")
    return hits[0] if len(hits) == 1 else ""


@frappe.whitelist(methods=["POST"])
def save_recipes(recipes_json):
    if not _is_manager():
        frappe.throw("Only a manager can change kit recipes.", frappe.PermissionError)
    data = json.loads(recipes_json) if isinstance(recipes_json, str) else recipes_json
    clean = []
    for r in data or []:
        kit = _resolve(r.get("kit"))
        if not kit or not _item(kit).get("is_stock_item"):
            frappe.throw(f"{kit or '—'}: not a stock item.")
        comps = []
        for c in r.get("components") or []:
            code = _resolve(c.get("item_code"))
            if not code or code == kit:
                frappe.throw(f"{code or '—'}: not a valid component.")
            comps.append({"item_code": code, "qty": max(cint(c.get("qty")), 1)})
        if not comps:
            frappe.throw(f"{kit}: a kit needs at least one component.")
        clean.append({"kit": kit, "yield": max(cint(r.get("yield")), 1), "components": comps,
                      "target": (r.get("target") or "").strip()})
    frappe.db.set_default(RECIPES_KEY, json.dumps(clean))
    frappe.db.commit()
    return {"ok": True, "kits": [_card(r) for r in clean]}


@frappe.whitelist(methods=["POST"])
def account_count(reco, sources=None):
    """A submitted count that RAISED a kit got the kits right and left out
    the other half: the components they were built from. Post that half —
    a Material Issue of the recipe's components, one second after the count,
    charged to the account the count credited — so the count's stock gain
    is offset by the cost of what went into the kits.

    Why not cancel the count and post a Repack in its place: ERPNext refuses
    it. Cancelling a count re-plays the ledger from the quantity the count
    itself stored as "before", not from the Repack sitting under it, and its
    future-negative check ignores allow_negative_stock — measured on
    MAT-RECO-2026-23355 (every variant tried in a rolled-back transaction,
    2026-11-16). What stays is the gap between the count's rate and the
    components' cost, left on the adjustment account for the accountant."""
    if not _is_manager():
        frappe.throw("Only a manager can account for a count.", frappe.PermissionError)
    if isinstance(sources, str):
        sources = json.loads(sources or "{}")
    doc = frappe.get_doc("Stock Reconciliation", reco)
    if doc.docstatus != 1:
        frappe.throw(f"{reco} is not a submitted count.")
    if frappe.db.exists("Stock Entry", {"docstatus": 1, "remarks": ["like", f"%{reco}%"],
                                        "purpose": "Material Issue"}):
        frappe.throw(f"{reco} has already been accounted for.")
    kits = kit_items()
    rows, what = [], []
    for row in doc.items:
        if row.item_code not in kits:
            continue
        r = recipe_for(row.item_code)
        up = int(flt(row.qty) - flt(row.current_qty))
        y = max(cint(r.get("yield")), 1)
        if up <= 0:
            continue
        if up % y:
            frappe.throw(f"{reco}: {row.item_code} rose by {up} — not whole batches of {y}.")
        for c in r["components"]:
            wh = (sources or {}).get(c["item_code"])
            if not wh:
                frappe.throw(f"Choose where {_item(c['item_code']).get('custom_sku') or c['item_code']} was taken from.")
            rows.append({"item_code": c["item_code"], "qty": up // y * max(cint(c.get("qty")), 1),
                         "s_warehouse": wh, "uom": _item(c["item_code"]).get("stock_uom") or "Nos",
                         "conversion_factor": 1, "expense_account": doc.expense_account,
                         "cost_center": doc.cost_center})
        what.append(f"{up} × {_item(row.item_code).get('custom_sku') or row.item_code}")
    if not rows:
        frappe.throw(f"{reco} did not raise any kit.")
    at = frappe.utils.get_datetime(f"{doc.posting_date} {doc.posting_time}") + datetime.timedelta(seconds=1)
    se = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Issue",
                         "purpose": "Material Issue", "company": COMPANY,
                         "set_posting_time": 1, "posting_date": at.date(), "posting_time": at.time(),
                         "remarks": f"{TAG}: components of {', '.join(what)} counted in by {reco} "
                                    f"(the kits were built, not found) — by {frappe.session.user}",
                         "items": rows})
    se.flags.ignore_permissions = True
    se.insert()
    se.submit()
    if frappe.db.get_value("Stock Entry", se.name, "docstatus") != 1:
        frappe.throw("The entry was rolled back by the database — try again.")
    doc.add_comment("Comment", f"Kits counted in here were assembled from their components; the components "
                               f"left on {se.name} ({round(sum(flt(i.amount) for i in se.items))} MAD, "
                               f"charged to {doc.expense_account}).")
    frappe.db.commit()
    for k in ("lp_pick_avail", "lp_board_summary", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return {"ok": True, "reco": reco, "entry": se.name,
            "value": round(sum(flt(i.amount) for i in se.items)),
            "gain": round(flt(doc.difference_amount))}


def warn_kit_count(doc, method=None):
    """Stock Reconciliation validate: a count may not RAISE a kit — kits are
    assembled, and only Assemble moves the components with them. Checked at
    submit only, so a shelf count with a kit on it still saves as a draft
    and the review says why it is held."""
    if getattr(doc, "_action", None) != "submit" or frappe.flags.get("lp_kit_count_ok"):
        return
    kits = kit_items()
    for r in doc.items or []:
        if r.item_code in kits and flt(r.qty) > flt(r.current_qty):
            sku = frappe.db.get_value("Item", r.item_code, "custom_sku") or r.item_code
            frappe.throw(f"lp:kitCount|{sku}")
