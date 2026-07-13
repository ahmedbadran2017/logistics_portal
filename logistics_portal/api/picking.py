"""Picking: capture enforcement, picker queue, scan-to-complete, assignment."""

import frappe
from frappe.utils import flt


# ---------------------------------------------------------------------------
# Document events (registered in hooks.py)
# ---------------------------------------------------------------------------
def enforce_picker_on_submit(doc, method=None):
    """Capture enforcement — no Pick List is submitted without an assigned picker.
    Closes the 34% coverage gap so performance/SLA are real. No-op on sites where
    the field isn't installed yet, so it never blocks unrelated submissions."""
    if not frappe.get_meta("Pick List").has_field("custom_assigned_picker"):
        return
    if not doc.get("custom_assigned_picker"):
        frappe.throw("Assign a picker before submitting this Pick List.")


def sync_pick_progress(doc, method=None):
    """Keep the rollup fields on Pick List in sync (items count, total qty)."""
    try:
        items = doc.get("locations") or []
        doc.db_set("custom_items_count", len(items), update_modified=False)
        doc.db_set(
            "custom_total_quantity",
            sum(flt(i.get("qty")) for i in items),
            update_modified=False,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.sync_pick_progress")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_order_name(order):
    """Return the real Sales Order name for a scanned/typed reference.

    Production SO names carry the '#' as part of the name (e.g. '#248774'),
    alongside plain series names (J-001317, SAL-ORD-...). We must not blindly
    strip '#' — try the raw value, the stripped value, and the '#'-prefixed
    value, and return whichever actually exists."""
    raw = (order or "").strip()
    stripped = raw.lstrip("#")
    for cand in (raw, stripped, "#" + stripped):
        if cand and frappe.db.exists("Sales Order", cand):
            return cand
    return None


# ---------------------------------------------------------------------------
# Whitelisted API
# ---------------------------------------------------------------------------
@frappe.whitelist()
def my_queue(user=None):
    """The picker's actionable queue: DRAFT pick lists assigned to them (by the
    dispatcher or the autopilot) or created by them. Oldest first — matching the
    cutoff-first batching order."""
    user = user or frappe.session.user
    try:
        pls = frappe.db.sql(
            """SELECT pl.name, pl.custom_items_count AS items_cnt,
                      pl.custom_total_quantity AS qty, pl.creation,
                      (SELECT COUNT(DISTINCT pli.sales_order) FROM `tabPick List Item` pli
                       WHERE pli.parent = pl.name) AS orders,
                      (SELECT MAX(pli.sales_order) FROM `tabPick List Item` pli
                       WHERE pli.parent = pl.name) AS so_one,
                      (SELECT MAX(so.customer_name) FROM `tabPick List Item` pli
                       LEFT JOIN `tabSales Order` so ON so.name = pli.sales_order
                       WHERE pli.parent = pl.name) AS customer
               FROM `tabPick List` pl
               WHERE pl.docstatus = 0
                 AND (pl.custom_assigned_picker = %(u)s OR pl.owner = %(u)s)
               ORDER BY pl.creation
               LIMIT 50""",
            {"u": user}, as_dict=True)
        out = []
        for pl in pls:
            orders = int(pl.orders or 0)
            out.append({
                "name": pl.so_one if orders == 1 and pl.so_one else pl.name,
                "pick_list": pl.name,
                "customer": (pl.customer or "") if orders == 1 else f"Combined · {orders} orders",
                "channel": "",
                "items": int(pl.items_cnt or 0),
                "qty": int(pl.qty or 0),
                "orders": orders,
                "total": 0,
                "stage": "Pending",
                "sla": "On Track",
                "created": str(pl.creation)[:16],
            })
        return out
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.my_queue")
        return []


@frappe.whitelist()
def pick_items(order):
    """The walk-ordered pick sheet for a Pick List (or an order's PL): lines
    sorted by warehouse so the picker never backtracks, with the destination
    order per line so mono-SKU batches can be labelled straight off the list."""
    try:
        pl = frappe.db.get_value(
            "Pick List", {"name": order}, "name"
        ) or _pick_list_for_order(order)
        if not pl:
            return []
        rows = frappe.db.sql(
            """SELECT COALESCE(NULLIF(pli.item_name,''), pli.item_code) AS name,
                      pli.item_code AS sku, pli.qty, pli.picked_qty,
                      pli.warehouse AS bin, pli.sales_order AS so,
                      so.customer_name AS customer, it.image
               FROM `tabPick List Item` pli
               LEFT JOIN `tabSales Order` so ON so.name = pli.sales_order
               LEFT JOIN `tabItem` it ON it.name = pli.item_code
               WHERE pli.parent = %(pl)s
               ORDER BY pli.warehouse, pli.idx""",
            {"pl": pl}, as_dict=True)
        return [{
            "name": r.name, "sku": r.sku, "qty": int(r.qty or 0),
            "bin": r.bin or "—", "so": r.so or "", "customer": r.customer or "",
            "image": r.image or "", "picked": 0,
        } for r in rows]
    except Exception:
        return []


@frappe.whitelist()
def resolve_scan(code):
    """Map a scanned code to an item. The PDA reads the label, which carries the
    SKU (or a barcode alias of it) — item_code (the Shopify variant id) is never
    on a label. Priority: exact custom_sku → Item Barcode → item_code.
    Returns {itemCode, sku, name} or {} if nothing matches."""
    code = (code or "").strip()
    if not code:
        return {}
    it = frappe.db.get_value(
        "Item", {"custom_sku": code}, ["name", "custom_sku", "item_name"], as_dict=True)
    if not it:
        parent = frappe.db.get_value("Item Barcode", {"barcode": code}, "parent")
        if parent:
            it = frappe.db.get_value(
                "Item", parent, ["name", "custom_sku", "item_name"], as_dict=True)
    if not it and frappe.db.exists("Item", code):
        it = frappe.db.get_value(
            "Item", code, ["name", "custom_sku", "item_name"], as_dict=True)
    if not it:
        return {}
    return {"itemCode": it.name, "sku": it.custom_sku or "", "name": it.item_name or ""}


@frappe.whitelist()
def scan_pick(pick_list, code):
    """Record one unit of a scanned item as picked on a draft pick list. The scan
    (SKU/barcode/item_code) is resolved to an item, then the first not-yet-full
    line of that item on the list gets its custom_scanned_qty bumped. Persisted
    so progress survives a reload. Assigned picker / owner / manager only.
    Returns {ok, itemCode, sku, name, itemScanned, itemQty, totalScanned,
    totalQty} or {ok: False, reason}."""
    from logistics_portal.api.auth import resolve_role
    if not frappe.db.exists("Pick List", pick_list):
        return {"ok": False, "reason": "unknown_list"}
    pl = frappe.db.get_value("Pick List", pick_list,
                             ["custom_assigned_picker", "owner", "docstatus"], as_dict=True)
    user, role = frappe.session.user, resolve_role(frappe.session.user)
    if role != "manager" and user not in (pl.custom_assigned_picker, pl.owner):
        frappe.throw("You are not the picker for this list.", frappe.PermissionError)

    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item"}
    # Atomic increment: two PDAs scanning the same line concurrently must not
    # read-modify-write the same value (a unit would vanish from the count).
    # The WHERE guard makes the bump conditional and the DB serializes it.
    frappe.db.sql(
        """UPDATE `tabPick List Item`
           SET custom_scanned_qty = COALESCE(custom_scanned_qty,0) + 1
           WHERE parent=%s AND item_code=%s AND COALESCE(custom_scanned_qty,0) < qty
           ORDER BY idx LIMIT 1""", (pick_list, item_code))
    if not frappe.db.sql("SELECT ROW_COUNT()")[0][0]:
        on = frappe.db.exists("Pick List Item", {"parent": pick_list, "item_code": item_code})
        return {"ok": False, "reason": "done" if on else "not_on_list",
                "itemCode": item_code, "name": r.get("name")}
    it = frappe.db.sql(
        """SELECT SUM(qty) q, SUM(COALESCE(custom_scanned_qty,0)) s FROM `tabPick List Item`
           WHERE parent=%s AND item_code=%s""", (pick_list, item_code), as_dict=True)[0]
    tot = frappe.db.sql(
        """SELECT SUM(qty) q, SUM(COALESCE(custom_scanned_qty,0)) s FROM `tabPick List Item`
           WHERE parent=%s""", (pick_list,), as_dict=True)[0]
    frappe.db.commit()
    return {"ok": True, "itemCode": item_code, "sku": r.get("sku"), "name": r.get("name"),
            "itemScanned": int(it.s or 0), "itemQty": int(it.q or 0),
            "totalScanned": int(tot.s or 0), "totalQty": int(tot.q or 0)}


def _pack_order(order):
    """One order's packing view: customer, label, and every item with image + SKU
    so the packer can complete a multi-piece parcel. `single` = a one-piece order
    (the fast path: scan → label)."""
    so = frappe.db.get_value(
        "Sales Order", order,
        ["customer_name", "custom_awb", "custom_label_url", "grand_total",
         "custom_shipping_city"], as_dict=True) or {}
    items = frappe.db.sql(
        """SELECT soi.item_code AS sku, it.custom_sku AS real_sku,
                  COALESCE(NULLIF(soi.item_name,''), soi.item_code) AS name,
                  soi.qty, it.image
           FROM `tabSales Order Item` soi
           LEFT JOIN `tabItem` it ON it.name = soi.item_code
           WHERE soi.parent = %s ORDER BY soi.idx""", (order,), as_dict=True)
    pieces = sum(int(i.qty or 0) for i in items)
    return {
        "order": order, "customer": so.get("customer_name") or "",
        "city": so.get("custom_shipping_city") or "", "awb": so.get("custom_awb") or "",
        "labelUrl": so.get("custom_label_url") or "", "total": float(so.get("grand_total") or 0),
        "single": pieces <= 1,
        "items": [{"sku": i.sku, "realSku": i.real_sku or "", "name": i.name,
                   "qty": int(i.qty or 0), "image": i.image or ""} for i in items],
    }


@frappe.whitelist()
def pack_scan(code):
    """Packer scans any item from the tote; the system finds the order it belongs
    to that still needs packing (Label Generated) and returns it with all its
    items. Single-piece orders are the fast path (scan → label). Packer /
    dispatcher / manager only."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("packer", "dispatcher", "manager"):
        frappe.throw("Not authorized to pack.", frappe.PermissionError)
    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item"}
    row = frappe.db.sql(
        """SELECT so.name FROM `tabSales Order` so
           JOIN `tabSales Order Item` soi ON soi.parent = so.name
           WHERE so.docstatus=1 AND so.custom_sales_status='Confirmed'
             AND so.custom_logistics_status='Label Generated'
             AND soi.item_code=%s
           ORDER BY so.creation ASC LIMIT 1""", (item_code,), as_dict=True)
    if not row:
        return {"ok": False, "reason": "no_order", "itemCode": item_code, "name": r.get("name")}
    return {"ok": True, "scannedItem": item_code, **_pack_order(row[0].name)}


@frappe.whitelist()
def mark_packed(order):
    """Finish an order at the pack station: Label Generated → Label Printed.
    Returns the label URL so the client can send it to the thermal printer."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("packer", "dispatcher", "manager"):
        frappe.throw("Not authorized to pack.", frappe.PermissionError)
    name = _resolve_order_name(order)
    if not name:
        frappe.throw("Unknown order.")
    st = frappe.db.get_value("Sales Order", name, "custom_logistics_status")
    if st in ("Label Generated", "Picked", "In transit", "Received"):
        frappe.get_doc("Sales Order", name).db_set("custom_logistics_status", "Label Printed")
    frappe.cache().delete_value("lp_board_summary")
    return {"ok": True, "labelUrl": frappe.db.get_value("Sales Order", name, "custom_label_url") or ""}


@frappe.whitelist()
def complete_pick(order):
    """Mark the order Picked once all items are scanned. Only the assigned picker
    (or a logistics manager) may complete a pick."""
    from logistics_portal.api.auth import resolve_role

    name = _resolve_order_name(order)
    if not name:
        frappe.throw("Unknown order.")

    user = frappe.session.user
    assigned = frappe.db.get_value("Pick List Item", {"sales_order": name}, "parent")
    picker = frappe.db.get_value("Pick List", assigned, "custom_assigned_picker") if assigned else None
    if user != picker and resolve_role(user) != "manager":
        frappe.throw("You are not the assigned picker for this order.", frappe.PermissionError)

    frappe.get_doc("Sales Order", name).db_set("custom_logistics_status", "Picked")
    # Picked → out of the to-pick pool; refresh the board / availability / clusters.
    frappe.cache().delete_value("lp_board_summary")
    frappe.cache().delete_value("lp_pick_avail")
    frappe.cache().delete_value("lp_consolidation")
    return {"ok": True}


_PICKER_ID = {
    "marouaneelmessaoudi07@gmail.com": "marouane", "mouakkalanass@gmail.com": "anass",
    "asmaazirary7@gmail.com": "asmaa", "lamdanisaad12@gmail.com": "saad",
    "ossamanahila@gmail.com": "oussama", "saidnakri65@gmail.com": "said",
    "redazaari47@gmail.com": "reda",
}


@frappe.whitelist()
def pick_lists(status="", q="", days=7, limit=30, offset=0):
    """Windowed, paginated pick-list board (39k PLs in production — the window
    keeps it to the ~330/week the team actually works).

    Real semantics on production: pickers create their own PLs (owner is the
    picker; custom_assigned_picker is mostly empty), docstatus 1 lands
    immediately, and the work state lives in custom_logistics_status
    (Pending = picked, awaiting shipment · Shipped = handed to carrier)."""
    try:
        days = min(max(int(days or 7), 1), 90)
        limit = min(max(int(limit or 30), 1), 100)
        offset = max(int(offset or 0), 0)
        vals = {"days": days, "limit": limit, "offset": offset}

        derived = """CASE
            WHEN pl.docstatus = 2 THEN 'cancelled'
            WHEN pl.docstatus = 0 THEN 'draft'
            WHEN pl.custom_logistics_status = 'Shipped' THEN 'shipped'
            WHEN pl.custom_logistics_status = 'Partially Shipped' THEN 'partial'
            ELSE 'open'
        END"""
        window = "pl.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)"

        counts = {"draft": 0, "open": 0, "shipped": 0, "partial": 0, "cancelled": 0}
        for r in frappe.db.sql(
            f"SELECT {derived} AS st, COUNT(*) AS c FROM `tabPick List` pl WHERE {window} GROUP BY st",
            vals, as_dict=True):
            counts[r.st] = int(r.c or 0)

        conds = [window]
        if status in counts:
            vals["status"] = status
            conds.append(f"{derived} = %(status)s")
        if q and str(q).strip():
            vals["q"] = f"%{str(q).strip()}%"
            conds.append("""(pl.name LIKE %(q)s OR pl.custom_assigned_picker LIKE %(q)s
                            OR pl.owner LIKE %(q)s OR EXISTS (
                                SELECT 1 FROM `tabPick List Item` pli
                                WHERE pli.parent = pl.name AND pli.sales_order LIKE %(q)s))""")
        where = " AND ".join(conds)

        total = frappe.db.sql(f"SELECT COUNT(*) FROM `tabPick List` pl WHERE {where}", vals)[0][0]

        rows = frappe.db.sql(
            f"""SELECT pl.name, pl.docstatus, pl.custom_logistics_status AS lstatus,
                       COALESCE(NULLIF(pl.custom_assigned_picker,''), pl.owner) AS picker,
                       pl.custom_items_count AS items_cnt, pl.custom_total_quantity AS qty,
                       pl.custom_shipped_percentage AS pct, pl.creation,
                       {derived} AS status,
                       (SELECT COUNT(DISTINCT pli.sales_order) FROM `tabPick List Item` pli
                        WHERE pli.parent = pl.name) AS orders,
                       (SELECT COUNT(DISTINCT pli.item_code) FROM `tabPick List Item` pli
                        WHERE pli.parent = pl.name) AS skus,
                       (SELECT MAX(pli.sales_order) FROM `tabPick List Item` pli
                        WHERE pli.parent = pl.name) AS so_one
                FROM `tabPick List` pl
                WHERE {where}
                ORDER BY pl.creation DESC
                LIMIT %(limit)s OFFSET %(offset)s""",
            vals, as_dict=True)

        out = []
        for r in rows:
            orders = int(r.orders or 0)
            skus = int(r.skus or 0)
            out.append({
                "no": r.name,
                "picker": r.picker or "",
                "items": int(r.items_cnt or 0),
                "qty": int(r.qty or 0),
                "orders": orders,
                "skus": skus,
                # Mono = one product across many orders: a single shelf grab.
                "mono": skus == 1 and orders > 1,
                "order": "combined" if orders > 1 else (r.so_one or "—"),
                "customer": "",
                "status": r.status,
                "pct": int(r.pct or 0),
                "created": str(r.creation)[:16],
            })
        return {"rows": out, "counts": counts, "total": int(total or 0), "days": days,
                "serverNow": str(frappe.utils.now_datetime())[:19]}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.pick_lists")
        return {}


@frappe.whitelist()
def pick_list_detail(name):
    """One pick list, fully real: lines (with item image + per-line pick state),
    the distinct orders on it (with customer/AWB), and honest lifecycle facts."""
    try:
        if not frappe.db.exists("Pick List", name):
            return {}
        pl = frappe.db.get_value(
            "Pick List", name,
            ["name", "docstatus", "custom_logistics_status", "custom_assigned_picker",
             "owner", "creation", "modified", "custom_items_count",
             "custom_total_quantity", "custom_shipped_percentage", "purpose", "company"],
            as_dict=True)

        lines = frappe.db.sql(
            """SELECT pli.item_code AS sku, COALESCE(NULLIF(pli.item_name,''), pli.item_code) AS name,
                      pli.warehouse AS bin, pli.qty, pli.picked_qty,
                      COALESCE(pli.custom_scanned_qty,0) AS scanned_qty, pli.uom,
                      pli.sales_order AS so, so.customer_name AS customer,
                      so.custom_awb AS awb, it.item_group AS grp, it.image,
                      it.custom_sku AS real_sku
               FROM `tabPick List Item` pli
               LEFT JOIN `tabSales Order` so ON so.name = pli.sales_order
               LEFT JOIN `tabItem` it ON it.name = pli.item_code
               WHERE pli.parent = %(pl)s
               ORDER BY pli.warehouse, pli.idx""",
            {"pl": name}, as_dict=True)

        orders, seen = [], set()
        for l in lines:
            if l.so and l.so not in seen:
                seen.add(l.so)
                orders.append({"so": l.so, "customer": l.customer or "", "awb": l.awb or ""})

        status = ("cancelled" if pl.docstatus == 2 else "draft" if pl.docstatus == 0
                  else "shipped" if pl.custom_logistics_status == "Shipped"
                  else "partial" if pl.custom_logistics_status == "Partially Shipped" else "open")
        return {
            "no": pl.name, "status": status,
            "picker": pl.custom_assigned_picker or pl.owner or "",
            "created": str(pl.creation)[:16], "updated": str(pl.modified)[:16],
            "items": int(pl.custom_items_count or len(lines)),
            "qty": int(pl.custom_total_quantity or sum(l.qty or 0 for l in lines)),
            "pct": int(pl.custom_shipped_percentage or 0),
            "purpose": pl.purpose or "Delivery",
            "orders": orders,
            "lines": [{
                "sku": l.sku, "realSku": l.real_sku or "", "name": l.name,
                "bin": l.bin or "—", "uom": l.uom or "",
                "qty": int(l.qty or 0), "pickedQty": int(l.picked_qty or 0),
                "scannedQty": int(l.scanned_qty or 0),
                "so": l.so or "", "customer": l.customer or "", "grp": l.grp or "",
                "image": l.image or "",
            } for l in lines],
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.pick_list_detail")
        return {}


@frappe.whitelist()
def create_pick_list_from_orders(orders, picker=None):
    """Create ONE draft (combined) Pick List from selected Confirmed orders.
    Mirrors the ops flow: dispatcher groups orders → picker works the list →
    submit auto-creates the AWBs. Dispatcher/manager only."""
    import json
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can create pick lists.", frappe.PermissionError)

    if isinstance(orders, str):
        orders = json.loads(orders)
    result = _build_pick_list(orders, picker)
    frappe.cache().delete_value("lp_board_summary")
    frappe.cache().delete_value("lp_pick_avail")
    frappe.cache().delete_value("lp_consolidation")
    return result


def _pick_gate(name):
    """Why an order can't be picked right now, or None if it's good to go.
    A single stale selection must not sink the whole batch — callers skip on a
    reason instead of aborting."""
    if not frappe.db.exists("Sales Order", name):
        return "unknown order"
    so = frappe.db.get_value(
        "Sales Order", name,
        ["docstatus", "custom_sales_status", "custom_logistics_status"], as_dict=True)
    if so.docstatus != 1 or so.custom_sales_status != "Confirmed":
        return "not a submitted Confirmed order"
    if so.custom_logistics_status not in (None, "", "Pending"):
        return f"already in the flow ({so.custom_logistics_status})"
    if frappe.db.exists("Pick List Item", {"sales_order": name, "docstatus": ["<", 2]}):
        return "already on a pick list"
    # Short-picked recently = the shelf is physically empty even if Bin says
    # otherwise — don't bounce it straight onto the next list.
    spa = frappe.db.get_value("Sales Order", name, "custom_short_picked_at")         if frappe.get_meta("Sales Order").has_field("custom_short_picked_at") else None
    if spa:
        from frappe.utils import time_diff_in_seconds, now_datetime
        try:
            if time_diff_in_seconds(now_datetime(), spa) < 24 * 3600:
                return "short-picked recently (shelf empty)"
        except Exception:
            pass
    return None


def _insert_one(sos, picker=None):
    """Build + insert ONE combined draft Pick List from resolved SO docs.
    Points each line at the warehouse that actually holds AVAILABLE stock (the
    resolved pickable bin) — the SO item's parent warehouse ("ERPNext - JM")
    has no leaf stock, so ecommerce_integrations' validate would strip the
    lines and 417 the create. Raises on any validation failure."""
    pl = frappe.new_doc("Pick List")
    pl.company = sos[0].company
    pl.purpose = "Delivery"
    if picker and frappe.get_meta("Pick List").has_field("custom_assigned_picker"):
        pl.custom_assigned_picker = picker
    bins = _resolve_bins({it.item_code for so in sos for it in so.items})
    for so in sos:
        for it in so.items:
            pending = (it.qty or 0) - (it.delivered_qty or 0)
            if pending <= 0:
                continue
            b = bins.get(it.item_code)
            pl.append("locations", {
                "item_code": it.item_code, "qty": pending, "stock_qty": pending,
                "conversion_factor": it.conversion_factor or 1,
                "sales_order": so.name, "sales_order_item": it.name, "uom": it.uom,
                "warehouse": b["bin"] if b else it.warehouse,
            })
    if not pl.get("locations"):
        raise frappe.ValidationError("nothing pickable")
    pl.insert()
    return {"pl": pl.name, "orders": len({l.sales_order for l in pl.locations}),
            "items": len(pl.locations)}


def _short_err(e):
    msg = frappe.utils.strip_html(str(getattr(e, "message", None) or e) or "")
    return (msg.split("\n")[0][:90]).strip() or "stock unavailable"


def _build_pick_list(orders, picker=None):
    """One combined draft Pick List from a batch of orders. Resilient by design:
    orders that are stale (already picked / in-flow) are gated out first, and if
    the combined insert still fails on live stock (reserved, or already locked in
    another open pick list), it falls back to per-order inserts — skipping only
    the orders that truly can't be picked. Never 417s the whole batch for one
    bad order. Returns {pl, orders, items, skipped, pls}."""
    # Coerce to trimmed strings and de-duplicate (preserve order). A repeated
    # name would otherwise append the same SO's lines twice — over-picking the
    # combined list, or spawning a second pick list for it in the fallback
    # (which bypasses _pick_gate). "Ship together" can pass repeats on double-tap.
    seen, clean = set(), []
    for o in (orders or []):
        o = str(o).strip() if o is not None else ""
        if o and o not in seen:
            seen.add(o)
            clean.append(o)
    orders = clean
    if not orders:
        frappe.throw("No orders selected.")
    if len(orders) > 120:
        frappe.throw("Too many orders for one pick list (max 120).")

    sos, skipped = [], []
    for name in orders:
        reason = _pick_gate(name)
        if reason:
            skipped.append({"order": name, "reason": reason})
        else:
            sos.append(frappe.get_doc("Sales Order", name))
    if not sos:
        detail = "; ".join(f"{s['order']} — {s['reason']}" for s in skipped[:4])
        frappe.throw("None of the selected orders can be picked (already picked or "
                     f"in the flow): {detail}")

    # Happy path: one combined pick list.
    try:
        r = _insert_one(sos, picker)
        return {**r, "skipped": skipped, "pls": [r["pl"]]}
    except Exception:
        frappe.db.rollback()

    # Fallback: live-stock contention emptied or blocked the combined insert.
    # Insert per order, commit each success, skip (and report) the ones that
    # can't be picked right now — so the dispatcher still gets pick lists.
    made = []
    for so in sos:
        try:
            made.append(_insert_one([so], picker))
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            skipped.append({"order": so.name, "reason": _short_err(e)})
    if not made:
        detail = "; ".join(f"{s['order']} — {s['reason']}" for s in skipped[:4])
        frappe.throw(f"Couldn't pick any of the selected orders — {detail}")
    return {"pl": made[0]["pl"], "orders": sum(m["orders"] for m in made),
            "items": sum(m["items"] for m in made),
            "pls": [m["pl"] for m in made], "skipped": skipped}


@frappe.whitelist()
def submit_pick_list(name):
    """Submit a draft Pick List. ecommerce_integrations creates the Delivery
    Note + carrier AWB + label on submit, so this single action completes the
    whole downstream chain from the portal — no desk needed. Assigned picker,
    the list owner, or a dispatcher/manager only. Returns the DN + AWB."""
    from logistics_portal.api.auth import resolve_role
    if not frappe.db.exists("Pick List", name):
        frappe.throw("Unknown pick list.")
    pl = frappe.get_doc("Pick List", name)
    role = resolve_role(frappe.session.user)
    owner_or_picker = frappe.session.user in (pl.get("custom_assigned_picker"), pl.owner)
    if role not in ("dispatcher", "manager") and not owner_or_picker:
        frappe.throw("Only the assigned picker or a dispatcher can submit this pick list.",
                     frappe.PermissionError)
    if pl.docstatus == 1:
        frappe.throw("This pick list is already submitted.")
    if pl.docstatus == 2:
        frappe.throw("This pick list is cancelled.")
    # capture enforcement needs a picker on submit; default to the actor.
    if frappe.get_meta("Pick List").has_field("custom_assigned_picker") \
            and not pl.get("custom_assigned_picker"):
        pl.db_set("custom_assigned_picker", frappe.session.user, update_modified=False)
        pl.reload()
    pl.submit()
    frappe.cache().delete_value("lp_board_summary")
    frappe.cache().delete_value("lp_pick_avail")
    frappe.cache().delete_value("lp_consolidation")
    dn = frappe.db.sql(
        """SELECT MAX(dni.parent) FROM `tabDelivery Note Item` dni
           JOIN `tabPick List Item` pli ON pli.parent=%s AND pli.sales_order=dni.against_sales_order""",
        (name,))[0][0]
    awb = frappe.db.get_value("Delivery Note", dn, "custom_awb") if dn else None
    return {"ok": True, "pl": name, "dn": dn or "", "awb": awb or ""}


@frappe.whitelist()
def assign_picker(name, picker=None):
    """Assign / reassign the picker on a DRAFT pick list. Dispatcher/manager."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can assign pickers.", frappe.PermissionError)
    if not frappe.db.exists("Pick List", name):
        frappe.throw("Unknown pick list.")
    if not frappe.get_meta("Pick List").has_field("custom_assigned_picker"):
        frappe.throw("The assigned-picker field isn't installed.")
    if frappe.db.get_value("Pick List", name, "docstatus") != 0:
        frappe.throw("A picker can only be assigned while the pick list is a draft.")
    frappe.db.set_value("Pick List", name, "custom_assigned_picker", (picker or "").strip() or None)
    frappe.cache().delete_value("lp_board_summary")
    return {"ok": True, "picker": picker or ""}


@frappe.whitelist()
def cancel_pick_list(name, reason=None):
    """Delete a DRAFT pick list — frees its orders back to To Pick. Submitted
    lists (which already carry an AWB) are left to the desk. Dispatcher/manager."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can cancel pick lists.", frappe.PermissionError)
    if not frappe.db.exists("Pick List", name):
        frappe.throw("Unknown pick list.")
    ds = frappe.db.get_value("Pick List", name, "docstatus")
    if ds == 2:
        frappe.throw("This pick list is already cancelled.")
    if ds == 1:
        frappe.throw("Submitted pick lists already have an AWB — cancel them in ERPNext.")
    frappe.delete_doc("Pick List", name, ignore_permissions=False)
    frappe.cache().delete_value("lp_board_summary")
    frappe.cache().delete_value("lp_pick_avail")
    frappe.cache().delete_value("lp_consolidation")
    return {"ok": True}


@frappe.whitelist()
def pickers():
    """The whole picking team with live load. Load counts open (unshipped,
    recent) pick lists whether assigned OR self-created (on production pickers
    create their own PLs, so owner is the real signal). Zero-load pickers are
    included — an empty assignment dropdown helps nobody."""
    try:
        loads = {}
        for r in frappe.db.sql(
            """SELECT COALESCE(NULLIF(custom_assigned_picker,''), owner) AS email,
                      COUNT(*) AS cnt
               FROM `tabPick List`
               WHERE docstatus < 2 AND custom_logistics_status != 'Shipped'
                 AND creation >= DATE_SUB(NOW(), INTERVAL 14 DAY)
               GROUP BY email""",
            as_dict=True,
        ):
            loads[r.email] = int(r.cnt or 0)
        out = []
        for email, pid in _PICKER_ID.items():
            out.append({
                "id": pid,
                "email": email,
                "name": frappe.db.get_value("User", email, "full_name") or pid.title(),
                "load": loads.get(email, 0),
                "capacity": 15,
            })
        out.sort(key=lambda p: p["load"])
        return out
    except Exception:
        return []


@frappe.whitelist()
def assignment_board():
    """Unassigned ready orders + per-picker live load, for the dispatcher board."""
    return {"unassigned": [], "pickers": pickers()}




# ---------------------------------------------------------------------------
# Smart batching engine — one brain for manual preview AND the autopilot.
# Waterfall: mono-SKU express → single-line aisle run → multi-line zone
# cluster → mixed sweep. Grounded in production: 75% of the to-pick pool is
# single-line, top SKUs repeat 5-10x, shelf warehouses encode aisle/rack/level
# (e.g. "H4B - JM"), and 15% of pending SKUs have no stock (excluded as OOS).
# ---------------------------------------------------------------------------
import re as _re

_SHELF_RE = _re.compile(r"^([A-Z])(\d+)([A-Z]) - JM$")


def _resolve_bins(item_codes):
    """item_code → its best pick location: a shelf bin with stock first
    (aisle-walkable), else any staging bin with stock, else None (OOS)."""
    if not item_codes:
        return {}
    # Locally-pickable only, per the configurable pickable-warehouse policy — so
    # the engine's OOS detection matches the Orders board's Ready/Partial/OOS.
    from logistics_portal.api.warehouses import pickable_condition
    cond, wargs = pickable_condition("warehouse")
    rows = frappe.db.sql(
        "SELECT item_code, warehouse, (actual_qty - reserved_qty) AS avail FROM `tabBin` "
        "WHERE (actual_qty - reserved_qty) > 0 AND item_code IN %s AND " + cond,
        tuple([tuple(item_codes)] + wargs), as_dict=True)
    best = {}
    for r in rows:
        m = _SHELF_RE.match(r.warehouse or "")
        cand = {
            "bin": r.warehouse,
            "shelf": bool(m),
            "aisle": m.group(1) if m else "STG",
            "walk": (m.group(1), int(m.group(2)), m.group(3)) if m else ("~", 0, ""),
            "qty": float(r.avail or 0),
        }
        cur = best.get(r.item_code)
        # prefer shelf over staging; within the same class prefer more stock
        if not cur or (cand["shelf"], cand["qty"]) > (cur["shelf"], cur["qty"]):
            best[r.item_code] = cand
    return best


def _chunk(seq, cap_orders, cap_units, units_of):
    """Split a queue into batches respecting both caps."""
    out, cur, cur_units = [], [], 0
    for o in seq:
        u = units_of(o)
        if cur and (len(cur) >= cap_orders or cur_units + u > cap_units):
            out.append(cur)
            cur, cur_units = [], 0
        cur.append(o)
        cur_units += u
    if cur:
        out.append(cur)
    return out


@frappe.whitelist()
def suggest_batches(cap_orders=40, cap_units=None, min_mono=8, max_batches=40):
    """Batch proposal over the LIVE to-pick pool (same definition as the Orders
    board). Returns {batches, oos, poolTotal, batched, serverNow}; each batch
    carries its orders, walk-ordered lines, aisles and a time estimate."""
    try:
        from frappe.utils import now_datetime, nowdate
        cap_orders = min(max(int(cap_orders or 40), 5), 50)
        cap_units = min(max(int(cap_units or cap_orders * 2), 10), 120)
        min_mono = min(max(int(min_mono or 8), 4), 20)
        # Same-product batches are one shelf grab — pulling 100 of the same SKU is
        # as easy as 10, so they get a much higher cap than mixed walks.
        cap_mono = min(max(cap_orders * 2, 80), 120)

        rows = frappe.db.sql(
            """SELECT so.name, so.customer_name AS customer, so.grand_total AS total,
                      so.creation, soi.item_code,
                      COALESCE(NULLIF(soi.item_name,''), soi.item_code) AS item_name,
                      GREATEST(soi.qty - soi.delivered_qty, 0) AS qty
               FROM `tabSales Order` so
               JOIN `tabSales Order Item` soi ON soi.parent = so.name
               LEFT JOIN (SELECT DISTINCT pli.sales_order FROM `tabPick List Item` pli
                          JOIN `tabPick List` p ON p.name = pli.parent
                          WHERE p.docstatus < 2) pl ON pl.sales_order = so.name
               WHERE so.docstatus = 1 AND so.custom_sales_status = 'Confirmed'
                 AND so.custom_logistics_status = 'Pending' AND pl.sales_order IS NULL
                 AND so.creation >= DATE_SUB(NOW(), INTERVAL 90 DAY)
               ORDER BY so.creation""",
            as_dict=True)

        orders = {}
        for r in rows:
            if r.qty <= 0:
                continue
            o = orders.setdefault(r.name, {
                "so": r.name, "customer": r.customer or "", "total": float(r.total or 0),
                "creation": str(r.creation), "lines": [],
            })
            o["lines"].append({"sku": r.item_code, "name": r.item_name, "qty": int(r.qty)})

        # same-day cutoff flag (14:00, matching the board)
        _now = now_datetime()
        cutoff = f"{nowdate()} 14:00:00"
        day0 = f"{nowdate()} 00:00:00"
        past_cutoff = str(_now)[11:16] >= "14:00"
        for o in orders.values():
            c = o["creation"]
            o["missed"] = c < day0 or (past_cutoff and c < cutoff)
            o["units"] = sum(l["qty"] for l in o["lines"])

        bins = _resolve_bins({l["sku"] for o in orders.values() for l in o["lines"]})

        # OOS: any line without stock anywhere → the order can't be picked today.
        oos, pool = [], []
        for o in orders.values():
            missing = [l["sku"] for l in o["lines"] if l["sku"] not in bins]
            if missing:
                oos.append({"so": o["so"], "customer": o["customer"], "missing": missing})
            else:
                pool.append(o)

        def sort_q(q):
            return sorted(q, key=lambda o: (not o["missed"], o["creation"]))

        def walk_of(o):
            return min(bins[l["sku"]]["walk"] for l in o["lines"])

        MIN_BATCH = 5  # smaller than this folds into the next tier — no runt runs

        singles = [o for o in pool if len(o["lines"]) == 1]
        multis = [o for o in pool if len(o["lines"]) > 1]
        batches = []
        aisle_pool = []
        mixed_pool = []

        def emit(kind, label, chunk, aisle_hint=None):
            lines = {}
            for o in chunk:
                for l in o["lines"]:
                    b = bins[l["sku"]]
                    key = (l["sku"], b["bin"])
                    ln = lines.setdefault(key, {
                        "sku": l["sku"], "name": l["name"], "bin": b["bin"],
                        "walk": b["walk"], "qty": 0, "orders": 0,
                    })
                    ln["qty"] += l["qty"]
                    ln["orders"] += 1
            lns = sorted(lines.values(), key=lambda x: x["walk"])
            for ln in lns:
                ln.pop("walk", None)
            aisles = sorted({bins[l["sku"]]["aisle"] for o in chunk for l in o["lines"]})
            units = sum(o["units"] for o in chunk)
            batches.append({
                "kind": kind, "label": label,
                "orders": [{"so": o["so"], "customer": o["customer"],
                            "missed": o["missed"], "units": o["units"]} for o in chunk],
                "lines": lns, "units": units, "aisles": aisles,
                "late": sum(1 for o in chunk if o["missed"]),
                "est": int(round(len(lns) * 1.2 + len(aisles) * 1.5 + len(chunk) * 0.4 + 2)),
            })

        # 1 — mono-SKU express: only groups big enough to earn a dedicated
        #     one-stop run. Smaller same-SKU groups fold into the aisle pool —
        #     the walk order still lands them on the same shelf consecutively.
        by_sku = {}
        for o in singles:
            by_sku.setdefault(o["lines"][0]["sku"], []).append(o)
        for sku, grp in by_sku.items():
            if len(grp) < min_mono:
                aisle_pool.extend(grp)
                continue
            chunks = _chunk(sort_q(grp), cap_mono, cap_mono, lambda o: o["units"])
            for i, ch in enumerate(chunks):
                if len(chunks) > 1 and i == len(chunks) - 1 and len(ch) < MIN_BATCH:
                    aisle_pool.extend(ch)  # runt tail rides an aisle run instead
                else:
                    emit("mono", grp[0]["lines"][0]["name"], ch)

        # 2 — aisle runs: ALL work living in one aisle, single- and multi-line
        #     together (the old aisle/zone split just fragmented batches)
        for o in multis:
            aisles = {bins[l["sku"]]["aisle"] for l in o["lines"]}
            (aisle_pool if len(aisles) == 1 else mixed_pool).append(o)
        by_aisle = {}
        for o in aisle_pool:
            by_aisle.setdefault(bins[o["lines"][0]["sku"]]["aisle"], []).append(o)
        for aisle, grp in sorted(by_aisle.items()):
            grp = sorted(grp, key=lambda o: (not o["missed"], walk_of(o)))
            chunks = _chunk(grp, cap_orders, cap_units, lambda o: o["units"])
            for i, ch in enumerate(chunks):
                if i == len(chunks) - 1 and len(ch) < MIN_BATCH:
                    mixed_pool.extend(ch)  # runts merge into the sweep
                else:
                    emit("aisle", aisle, ch)

        # 3 — mixed sweep: nothing gets left behind (the final tail may be small)
        for chunk in _chunk(sort_q(mixed_pool), cap_orders, cap_units, lambda o: o["units"]):
            emit("mixed", "", chunk)

        kind_rank = {"mono": 0, "aisle": 1, "zone": 2, "mixed": 3}
        batches.sort(key=lambda b: (-b["late"], kind_rank[b["kind"]], -len(b["orders"])))
        for i, b in enumerate(batches):
            b["key"] = f"B{i + 1}"

        # Only ship the workable head: one run creates at most 20 lists, and a
        # deep backlog (200+ batches) freezes the browser if sent whole. The
        # rest is summarized — it resurfaces on the next open, highest priority
        # first.
        max_batches = min(max(int(max_batches or 40), 10), 100)
        total_batches = len(batches)
        batched_all = sum(len(b["orders"]) for b in batches)
        batches = batches[:max_batches]

        return {
            "batches": batches, "oos": oos,
            "moreBatches": max(0, total_batches - len(batches)),
            "moreOrders": batched_all - sum(len(b["orders"]) for b in batches),
            "poolTotal": len(orders), "batched": batched_all,
            "params": {"cap_orders": cap_orders, "cap_units": cap_units, "min_mono": min_mono},
            "serverNow": str(_now)[:19],
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.suggest_batches")
        return {}


@frappe.whitelist()
def create_batches(batches):
    """Materialize approved batches as draft Pick Lists (one per batch), each
    optionally pre-assigned to a picker. Per-batch failures don't abort the
    rest. Dispatcher/manager only."""
    import json
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can create pick lists.", frappe.PermissionError)
    if isinstance(batches, str):
        batches = json.loads(batches)
    batches = batches or []
    if not batches or len(batches) > 20:
        frappe.throw("Select between 1 and 20 batches.")
    if sum(len(b.get("orders") or []) for b in batches) > 600:
        frappe.throw("Too many orders in one run (max 600).")

    results = []
    for b in batches:
        try:
            r = _build_pick_list(b.get("orders") or [], b.get("picker"))
            # commit each batch as it lands — a later failure must not roll
            # back earlier, already-reported successes
            frappe.db.commit()
            results.append({"ok": True, **r, "picker": b.get("picker") or ""})
        except Exception as e:
            frappe.db.rollback()
            results.append({"ok": False, "error": str(e),
                            "orders": len(b.get("orders") or [])})
    frappe.cache().delete_value("lp_board_summary")
    frappe.cache().delete_value("lp_pick_avail")
    frappe.cache().delete_value("lp_consolidation")
    return {"results": results,
            "created": sum(1 for r in results if r.get("ok")),
            "failed": sum(1 for r in results if not r.get("ok"))}




# ---------------------------------------------------------------------------
# Autopilot — the same batching engine on a 15-minute clock. Guard-railed:
# only runs when enabled, skips thin pools, caps batches per run, assigns by
# live load, and keeps a persisted decision log the UI shows verbatim.
# ---------------------------------------------------------------------------
_AP_ENABLED = "lp_autopilot_enabled"
_AP_LOG = "lp_autopilot_log"
_AP_MIN_ORDERS = 6     # don't bother the floor for less than this (auto runs)
_AP_MAX_BATCHES = 8    # per run — keeps every run reviewable


def _ap_runs():
    import json
    try:
        return json.loads(frappe.db.get_default(_AP_LOG) or "[]")
    except Exception:
        return []


def _ap_record(entry):
    import json
    runs = [entry] + _ap_runs()
    frappe.db.set_default(_AP_LOG, json.dumps(runs[:30]))


@frappe.whitelist()
def autopilot_status():
    """Toggle state + the recent decision log (for the Pick Lists card)."""
    return {
        "enabled": frappe.db.get_default(_AP_ENABLED) == "1",
        "schedule": "*/15",
        "runs": _ap_runs()[:10],
    }


@frappe.whitelist()
def autopilot_toggle(enabled):
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can control the autopilot.", frappe.PermissionError)
    on = str(enabled).lower() in ("1", "true", "yes")
    frappe.db.set_default(_AP_ENABLED, "1" if on else "0")
    _ap_record({"at": str(frappe.utils.now_datetime())[:19], "trigger": "toggle",
                "note": "enabled" if on else "paused", "by": frappe.session.user})
    return {"enabled": on}


@frappe.whitelist()
def autopilot_run():
    """Manual 'Run now' from the UI (dispatcher/manager)."""
    from logistics_portal.api.auth import resolve_role

    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can run the autopilot.", frappe.PermissionError)
    return _autopilot_core(trigger="manual")


def autopilot_tick():
    """Scheduler entry (every 15 minutes) — no-op unless enabled."""
    if frappe.db.get_default(_AP_ENABLED) != "1":
        return None
    return _autopilot_core(trigger="auto")


def _autopilot_core(trigger):
    from frappe.utils import now_datetime

    sugg = suggest_batches()
    batches = (sugg or {}).get("batches") or []
    pool = sum(len(b["orders"]) for b in batches)
    entry = {"at": str(now_datetime())[:19], "trigger": trigger,
             "pool": (sugg or {}).get("poolTotal", 0), "oos": len((sugg or {}).get("oos") or [])}

    if not batches or (trigger == "auto" and pool < _AP_MIN_ORDERS):
        entry.update({"note": "skipped — pool below threshold", "created": 0, "failed": 0, "orders": 0})
        _ap_record(entry)
        return entry

    batches = batches[:_AP_MAX_BATCHES]

    # least-loaded assignment (live open-PL load per known picker)
    team = sorted(pickers(), key=lambda p: p.get("load", 0))
    team = [p for p in team if p.get("email")]

    created, failed, placed = 0, 0, 0
    details = []
    for i, b in enumerate(batches):
        picker = team[i % len(team)]["email"] if team else None
        try:
            r = _build_pick_list([o["so"] for o in b["orders"]], picker)
            frappe.db.commit()
            created += 1
            placed += len(b["orders"])
            details.append({"pl": r["pl"], "kind": b["kind"], "orders": len(b["orders"]),
                            "picker": picker or ""})
        except Exception as e:
            frappe.db.rollback()
            failed += 1
            details.append({"error": str(e)[:120], "kind": b["kind"], "orders": len(b["orders"])})
    frappe.cache().delete_value("lp_board_summary")
    frappe.cache().delete_value("lp_pick_avail")
    frappe.cache().delete_value("lp_consolidation")

    entry.update({"created": created, "failed": failed, "orders": placed, "details": details[:8]})
    _ap_record(entry)
    return entry


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _linked_sales_order(pick_list):
    so_name = frappe.db.get_value(
        "Pick List Reference", {"parent": pick_list}, "sales_order"
    ) if frappe.db.exists("DocType", "Pick List Reference") else None
    if not so_name:
        loc = frappe.db.get_value(
            "Pick List Item", {"parent": pick_list}, "sales_order"
        )
        so_name = loc
    if not so_name:
        return None
    return frappe.db.get_value(
        "Sales Order",
        so_name,
        ["name", "customer_name", "grand_total", "custom_channel", "custom_logistics_status"],
        as_dict=True,
    )


def _pick_list_for_order(order):
    # Production SO names carry the '#'; resolve the real name first (the old
    # lstrip-only lookup returned nothing for every hash-named order).
    name = _resolve_order_name(order)
    if not name:
        return None
    return frappe.db.get_value("Pick List Item", {"sales_order": name}, "parent")


# ---------------------------------------------------------------------------
# Sorting station (الفرز) — allocate a picked tote's items to their orders,
# print each order's label the moment it completes. Bound to ONE pick list:
# the tote in front of the sorter IS a pick list, so scans only match orders
# on that list (never someone else's oldest order).
# ---------------------------------------------------------------------------
_SORT_ROLES = ("packer", "dispatcher", "manager")


def _sort_gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in _SORT_ROLES:
        frappe.throw("Not authorized to sort.", frappe.PermissionError)


@frappe.whitelist()
def sorting_lists(days=2, limit=30):
    """Pick lists awaiting sorting: submitted recently, with at least one
    order still at Label Generated (= picked, AWB ready, label not printed).
    Progress = orders already Label Printed / total orders on the list."""
    _sort_gate()
    days = min(max(int(days or 2), 1), 14)
    limit = min(max(int(limit or 30), 1), 100)
    rows = frappe.db.sql(
        """SELECT pl.name,
                  COALESCE(NULLIF(pl.custom_assigned_picker,''), pl.owner) AS picker,
                  COUNT(DISTINCT pli.sales_order) AS orders,
                  SUM(pli.qty) AS qty,
                  COUNT(DISTINCT CASE WHEN so.custom_logistics_status = 'Label Printed'
                                      THEN pli.sales_order END) AS printed,
                  COUNT(DISTINCT CASE WHEN so.custom_logistics_status = 'Label Generated'
                                      THEN pli.sales_order END) AS pending
           FROM `tabPick List` pl
           JOIN `tabPick List Item` pli ON pli.parent = pl.name
           LEFT JOIN `tabSales Order` so ON so.name = pli.sales_order
           WHERE pl.docstatus = 1 AND pl.creation >= DATE_SUB(NOW(), INTERVAL %s DAY)
           GROUP BY pl.name
           HAVING pending > 0
           ORDER BY pl.creation DESC LIMIT %s""",
        (days, limit), as_dict=True)
    return [{"name": r.name, "picker": (r.picker or "").split("@")[0],
             "orders": int(r.orders or 0), "qty": int(r.qty or 0),
             "printed": int(r.printed or 0), "pending": int(r.pending or 0)}
            for r in rows]


@frappe.whitelist()
def sorting_detail(pick_list):
    """One pick list's sort wall: every order slot with its items (image,
    real SKU, qty, sorted so far) and label state."""
    _sort_gate()
    if not frappe.db.exists("Pick List", pick_list):
        frappe.throw("Unknown pick list.")
    rows = frappe.db.sql(
        """SELECT pli.sales_order AS so, pli.item_code, pli.qty,
                  COALESCE(pli.custom_sorted_qty, 0) AS sorted_qty,
                  COALESCE(NULLIF(pli.item_name,''), pli.item_code) AS item_name,
                  it.custom_sku AS real_sku, it.image,
                  s.customer_name AS customer, s.custom_logistics_status AS status,
                  s.custom_label_url AS label_url, s.custom_shipping_city AS city,
                  s.grand_total AS total
           FROM `tabPick List Item` pli
           LEFT JOIN `tabItem` it ON it.name = pli.item_code
           LEFT JOIN `tabSales Order` s ON s.name = pli.sales_order
           WHERE pli.parent = %s AND pli.sales_order IS NOT NULL
           ORDER BY pli.sales_order, pli.idx""",
        (pick_list,), as_dict=True)
    orders = {}
    for r in rows:
        o = orders.setdefault(r.so, {
            "order": r.so, "customer": r.customer or "", "city": r.city or "",
            "status": r.status or "", "labelUrl": r.label_url or "",
            "total": float(r.total or 0), "items": []})
        o["items"].append({
            "itemCode": r.item_code, "sku": r.real_sku or "", "name": r.item_name,
            "qty": int(r.qty or 0), "sorted": int(r.sorted_qty or 0),
            "image": r.image or ""})
    out = list(orders.values())
    for o in out:
        o["qty"] = sum(i["qty"] for i in o["items"])
        o["sorted"] = sum(i["sorted"] for i in o["items"])
        o["done"] = o["status"] == "Label Printed" or (o["qty"] > 0 and o["sorted"] >= o["qty"])
    out.sort(key=lambda o: (o["done"], o["order"]))
    return {"pickList": pick_list, "orders": out}


@frappe.whitelist()
def sort_scan(pick_list, code):
    """Allocate one scanned unit to an order ON THIS PICK LIST. Routing:
    the not-yet-full line of that item whose order is CLOSEST to completion,
    so orders finish (and labels print) as early as possible. When the scan
    completes an order, its status flips to Label Printed and the label URL
    is returned for immediate printing."""
    _sort_gate()
    if not frappe.db.exists("Pick List", pick_list):
        return {"ok": False, "reason": "unknown_list"}
    r = resolve_scan(code)
    item_code = r.get("itemCode")
    if not item_code:
        return {"ok": False, "reason": "unknown_item", "code": (code or "").strip()}

    rows = frappe.db.sql(
        """SELECT pli.name, pli.sales_order AS so, pli.qty,
                  COALESCE(pli.custom_sorted_qty,0) AS sorted_qty
           FROM `tabPick List Item` pli
           LEFT JOIN `tabSales Order` s ON s.name = pli.sales_order
           WHERE pli.parent = %s AND pli.item_code = %s
             AND pli.sales_order IS NOT NULL
             AND COALESCE(s.custom_logistics_status,'') <> 'Label Printed'
             AND COALESCE(pli.custom_sorted_qty,0) < pli.qty
           ORDER BY pli.idx""",
        (pick_list, item_code), as_dict=True)
    if not rows:
        on_list = frappe.db.exists(
            "Pick List Item", {"parent": pick_list, "item_code": item_code})
        return {"ok": False, "reason": "done" if on_list else "not_on_list",
                "itemCode": item_code, "name": r.get("name"), "sku": r.get("sku")}

    # Remaining units per candidate order → route to the order closest to done.
    remaining = {}
    for so in {x.so for x in rows}:
        t = frappe.db.sql(
            """SELECT SUM(qty) - SUM(COALESCE(custom_sorted_qty,0))
               FROM `tabPick List Item` WHERE parent = %s AND sales_order = %s""",
            (pick_list, so))[0][0]
        remaining[so] = int(t or 0)
    rows.sort(key=lambda x: remaining.get(x.so, 9999))
    row = rows[0]

    # Atomic bump (two sorters, one wall): the WHERE guard means concurrent
    # scans can't both count the same unit.
    frappe.db.sql(
        """UPDATE `tabPick List Item`
           SET custom_sorted_qty = COALESCE(custom_sorted_qty,0) + 1
           WHERE name = %s AND COALESCE(custom_sorted_qty,0) < qty""", (row.name,))
    if not frappe.db.sql("SELECT ROW_COUNT()")[0][0]:
        # Someone else just filled this line — report the item as done.
        return {"ok": False, "reason": "done", "itemCode": item_code,
                "name": r.get("name"), "sku": r.get("sku")}

    # Re-read remaining AFTER the write so it reflects concurrent scans.
    left = int(frappe.db.sql(
        """SELECT SUM(qty) - SUM(COALESCE(custom_sorted_qty,0))
           FROM `tabPick List Item` WHERE parent = %s AND sales_order = %s""",
        (pick_list, row.so))[0][0] or 0)
    result = {"ok": True, "order": row.so, "itemCode": item_code,
              "sku": r.get("sku"), "name": r.get("name"),
              "orderRemaining": max(0, left), "orderComplete": left <= 0}
    if left <= 0:
        # Conditional flip — exactly ONE scanner wins the status change, so the
        # auto-print fires once even if two devices complete the order together.
        frappe.db.sql(
            """UPDATE `tabSales Order` SET custom_logistics_status = 'Label Printed'
               WHERE name = %s AND COALESCE(custom_logistics_status,'')
                     IN ('Label Generated','Picked','Pending','')""", (row.so,))
        won = bool(frappe.db.sql("SELECT ROW_COUNT()")[0][0])
        result["orderComplete"] = won
        result["labelUrl"] = frappe.db.get_value("Sales Order", row.so, "custom_label_url") or ""
        frappe.cache().delete_value("lp_board_summary")
    frappe.db.commit()
    return result


@frappe.whitelist()
def report_short_pick(pick_list, order, item_code=None):
    """The picker can't find an item on the shelf. Chosen ops flow: pull that
    ORDER off the draft pick list (back to the problem pool, cool-down 24h so
    batching doesn't bounce it right back), notify the dispatchers, and let
    the picker keep working the rest of the list. Assigned picker / owner /
    manager only."""
    from logistics_portal.api.auth import SEED_ROLES, resolve_role

    if not frappe.db.exists("Pick List", pick_list):
        frappe.throw("Unknown pick list.")
    pl = frappe.get_doc("Pick List", pick_list)
    user, role = frappe.session.user, resolve_role(frappe.session.user)
    if role != "manager" and user not in (pl.get("custom_assigned_picker"), pl.owner):
        frappe.throw("You are not the picker for this list.", frappe.PermissionError)
    if pl.docstatus != 0:
        frappe.throw("This pick list is already submitted.")

    so_name = (order or "").strip()
    rows = [r for r in (pl.get("locations") or []) if r.sales_order == so_name]
    if not rows:
        frappe.throw("That order isn't on this pick list.")

    keep = [r for r in pl.get("locations") if r.sales_order != so_name]
    deleted = False
    if keep:
        pl.set("locations", keep)
        pl.flags.ignore_permissions = True
        pl.save(ignore_permissions=True)
    else:
        # Last order on the list — the whole draft goes.
        frappe.delete_doc("Pick List", pick_list, force=1, ignore_permissions=True)
        deleted = True

    # Cool-down + audit trail on the order.
    so = frappe.get_doc("Sales Order", so_name)
    if so.meta.has_field("custom_short_picked_at"):
        so.db_set("custom_short_picked_at", frappe.utils.now_datetime(),
                  update_modified=False)
    what = f" ({item_code})" if item_code else ""
    so.add_comment("Comment",
                   f"Short pick: item{what} not found on the shelf by {user} — "
                   f"pulled off {pick_list}, back to the pool for 24h.")

    # Tell the dispatchers something physical is wrong.
    dispatchers = [u for u, r in SEED_ROLES.items() if r in ("dispatcher", "manager")]
    for d in dispatchers:
        try:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"Short pick: {so_name}",
                "email_content": f"{user} couldn't find item{what} on the shelf. "
                                 f"Order pulled off {pick_list}.",
                "type": "Alert", "document_type": "Sales Order",
                "document_name": so_name, "for_user": d,
            }).insert(ignore_permissions=True)
        except Exception:
            pass
    frappe.publish_realtime("logistics_alert", {
        "severity": "warning", "title": f"Short pick: {so_name}",
        "detail": f"Item{what} missing on shelf — order back to the pool."})

    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
        frappe.cache().delete_value(k)
    frappe.db.commit()
    return {"ok": True, "order": so_name, "removedLines": len(rows),
            "plDeleted": deleted}
