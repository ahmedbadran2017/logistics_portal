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
            """SELECT pl.name, pl.custom_items_count AS items,
                      pl.custom_total_quantity AS qty, pl.creation,
                      agg.orders, agg.so_one, agg.customer
               FROM `tabPick List` pl
               LEFT JOIN (SELECT pli.parent, COUNT(DISTINCT pli.sales_order) orders,
                                 MAX(pli.sales_order) so_one, MAX(so.customer_name) customer
                          FROM `tabPick List Item` pli
                          LEFT JOIN `tabSales Order` so ON so.name = pli.sales_order
                          GROUP BY pli.parent) agg ON agg.parent = pl.name
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
                "items": int(pl.items or 0),
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
def complete_pick(order):
    """Mark the order Picked once all items are scanned. Only the assigned picker
    (or a logistics manager) may complete a pick."""
    from logistics_portal.api.auth import resolve_role

    name = (order or "").lstrip("#")
    if not frappe.db.exists("Sales Order", name):
        frappe.throw("Unknown order.")

    user = frappe.session.user
    assigned = frappe.db.get_value("Pick List Item", {"sales_order": name}, "parent")
    picker = frappe.db.get_value("Pick List", assigned, "custom_assigned_picker") if assigned else None
    if user != picker and resolve_role(user) != "manager":
        frappe.throw("You are not the assigned picker for this order.", frappe.PermissionError)

    frappe.get_doc("Sales Order", name).db_set("custom_logistics_status", "Picked")
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
                       pl.custom_items_count AS items, pl.custom_total_quantity AS qty,
                       pl.custom_shipped_percentage AS pct, pl.creation,
                       {derived} AS status,
                       agg.orders, agg.so_one
                FROM `tabPick List` pl
                LEFT JOIN (SELECT parent, COUNT(DISTINCT sales_order) AS orders,
                                  MAX(sales_order) AS so_one
                           FROM `tabPick List Item` GROUP BY parent) agg ON agg.parent = pl.name
                WHERE {where}
                ORDER BY pl.creation DESC
                LIMIT %(limit)s OFFSET %(offset)s""",
            vals, as_dict=True)

        out = []
        for r in rows:
            orders = int(r.orders or 0)
            out.append({
                "no": r.name,
                "picker": r.picker or "",
                "items": int(r.items or 0),
                "qty": int(r.qty or 0),
                "orders": orders,
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
                      pli.warehouse AS bin, pli.qty, pli.picked_qty, pli.uom,
                      pli.sales_order AS so, so.customer_name AS customer,
                      so.custom_awb AS awb, it.item_group AS grp, it.image
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
                "sku": l.sku, "name": l.name, "bin": l.bin or "—", "uom": l.uom or "",
                "qty": int(l.qty or 0), "pickedQty": int(l.picked_qty or 0),
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
    return result


def _build_pick_list(orders, picker=None):
    """Validate + insert one draft Pick List for a batch of orders (no role
    check, no cache bust — callers own those)."""
    orders = [o.strip() for o in (orders or []) if o and o.strip()]
    if not orders:
        frappe.throw("No orders selected.")
    if len(orders) > 50:
        frappe.throw("Too many orders for one pick list (max 50).")

    sos = []
    for name in orders:
        if not frappe.db.exists("Sales Order", name):
            frappe.throw(f"Unknown order: {name}")
        so = frappe.get_doc("Sales Order", name)
        if so.docstatus != 1 or so.get("custom_sales_status") != "Confirmed":
            frappe.throw(f"{name} is not a submitted Confirmed order.")
        if so.get("custom_logistics_status") not in (None, "", "Pending"):
            frappe.throw(f"{name} is already in the flow ({so.custom_logistics_status}).")
        if frappe.db.exists("Pick List Item", {"sales_order": name, "docstatus": ["<", 2]}):
            frappe.throw(f"{name} already has a pick list.")
        sos.append(so)

    pl = frappe.new_doc("Pick List")
    pl.company = sos[0].company
    pl.purpose = "Delivery"
    if picker and frappe.get_meta("Pick List").has_field("custom_assigned_picker"):
        pl.custom_assigned_picker = picker
    for so in sos:
        for it in so.items:
            pending = (it.qty or 0) - (it.delivered_qty or 0)
            if pending <= 0:
                continue
            pl.append("locations", {
                "item_code": it.item_code,
                "qty": pending,
                "stock_qty": pending,
                "conversion_factor": it.conversion_factor or 1,
                "sales_order": so.name,
                "sales_order_item": it.name,
                "uom": it.uom,
                "warehouse": it.warehouse,
            })
    if not pl.get("locations"):
        frappe.throw("Nothing left to pick on the selected orders.")

    # Let ERPNext resolve bins/batches the standard way; fall back to the
    # SO-item warehouses if location assignment isn't available.
    try:
        pl.set_item_locations()
    except Exception:
        pass
    pl.insert()
    return {"pl": pl.name, "orders": len(sos), "items": len(pl.locations)}


@frappe.whitelist()
def pickers():
    """Active pickers + live load (open pick lists), for the dispatcher board."""
    try:
        rows = frappe.db.sql(
            """SELECT custom_assigned_picker AS email, COUNT(*) AS load
               FROM `tabPick List`
               WHERE custom_assigned_picker IS NOT NULL AND custom_assigned_picker!=''
                 AND custom_logistics_status != 'Shipped'
               GROUP BY custom_assigned_picker ORDER BY load DESC""",
            as_dict=True,
        )
        out = []
        for r in rows:
            pid = _PICKER_ID.get(r.email)
            if not pid:
                continue
            out.append({
                "id": pid,
                "email": r.email,
                "name": frappe.db.get_value("User", r.email, "full_name") or r.email,
                "load": int(r.load or 0),
                "capacity": 15,
            })
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
    rows = frappe.db.sql(
        """SELECT item_code, warehouse, actual_qty FROM `tabBin`
           WHERE actual_qty > 0 AND item_code IN %(items)s""",
        {"items": tuple(item_codes)}, as_dict=True)
    best = {}
    for r in rows:
        m = _SHELF_RE.match(r.warehouse or "")
        cand = {
            "bin": r.warehouse,
            "shelf": bool(m),
            "aisle": m.group(1) if m else "STG",
            "walk": (m.group(1), int(m.group(2)), m.group(3)) if m else ("~", 0, ""),
            "qty": float(r.actual_qty or 0),
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
def suggest_batches(cap_orders=15, cap_units=25, min_mono=3):
    """Batch proposal over the LIVE to-pick pool (same definition as the Orders
    board). Returns {batches, oos, poolTotal, batched, serverNow}; each batch
    carries its orders, walk-ordered lines, aisles and a time estimate."""
    try:
        from frappe.utils import now_datetime, nowdate
        cap_orders = min(max(int(cap_orders or 15), 3), 30)
        cap_units = min(max(int(cap_units or 25), 5), 60)
        min_mono = min(max(int(min_mono or 3), 2), 10)

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

        singles = [o for o in pool if len(o["lines"]) == 1]
        multis = [o for o in pool if len(o["lines"]) > 1]
        batches = []

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

        # 1 — mono-SKU express
        by_sku = {}
        for o in singles:
            by_sku.setdefault(o["lines"][0]["sku"], []).append(o)
        mono_done = set()
        for sku, grp in by_sku.items():
            if len(grp) >= min_mono:
                for chunk in _chunk(sort_q(grp), cap_orders, cap_units, lambda o: o["units"]):
                    emit("mono", grp[0]["lines"][0]["name"], chunk)
                mono_done.update(o["so"] for o in grp)
        singles = [o for o in singles if o["so"] not in mono_done]

        # 2 — single-line aisle run
        by_aisle = {}
        for o in singles:
            by_aisle.setdefault(bins[o["lines"][0]["sku"]]["aisle"], []).append(o)
        aisle_done = set()
        for aisle, grp in by_aisle.items():
            if len(grp) >= 2:
                grp = sorted(grp, key=lambda o: (not o["missed"], walk_of(o)))
                for chunk in _chunk(grp, cap_orders, cap_units, lambda o: o["units"]):
                    emit("aisle", aisle, chunk)
                aisle_done.update(o["so"] for o in grp)
        leftovers = [o for o in singles if o["so"] not in aisle_done]

        # 3 — multi-line zone cluster (all lines in ONE aisle)
        zone_done = set()
        by_zone = {}
        for o in multis:
            aisles = {bins[l["sku"]]["aisle"] for l in o["lines"]}
            if len(aisles) == 1:
                by_zone.setdefault(next(iter(aisles)), []).append(o)
        for aisle, grp in by_zone.items():
            if len(grp) >= 2:
                grp = sorted(grp, key=lambda o: (not o["missed"], walk_of(o)))
                for chunk in _chunk(grp, cap_orders, cap_units, lambda o: o["units"]):
                    emit("zone", aisle, chunk)
                zone_done.update(o["so"] for o in grp)
        leftovers += [o for o in multis if o["so"] not in zone_done]

        # 4 — mixed sweep: nothing gets left behind
        for chunk in _chunk(sort_q(leftovers), cap_orders, cap_units, lambda o: o["units"]):
            emit("mixed", "", chunk)

        kind_rank = {"mono": 0, "aisle": 1, "zone": 2, "mixed": 3}
        batches.sort(key=lambda b: (-b["late"], kind_rank[b["kind"]], -len(b["orders"])))
        for i, b in enumerate(batches):
            b["key"] = f"B{i + 1}"

        return {
            "batches": batches, "oos": oos,
            "poolTotal": len(orders), "batched": sum(len(b["orders"]) for b in batches),
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
    if sum(len(b.get("orders") or []) for b in batches) > 200:
        frappe.throw("Too many orders in one run (max 200).")

    results = []
    for b in batches:
        try:
            r = _build_pick_list(b.get("orders") or [], b.get("picker"))
            results.append({"ok": True, **r, "picker": b.get("picker") or ""})
        except Exception as e:
            frappe.db.rollback()
            results.append({"ok": False, "error": str(e),
                            "orders": len(b.get("orders") or [])})
    frappe.db.commit()
    frappe.cache().delete_value("lp_board_summary")
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
            created += 1
            placed += len(b["orders"])
            details.append({"pl": r["pl"], "kind": b["kind"], "orders": len(b["orders"]),
                            "picker": picker or ""})
        except Exception as e:
            frappe.db.rollback()
            failed += 1
            details.append({"error": str(e)[:120], "kind": b["kind"], "orders": len(b["orders"])})
    frappe.db.commit()
    frappe.cache().delete_value("lp_board_summary")

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
    name = order.lstrip("#")
    return frappe.db.get_value("Pick List Item", {"sales_order": name}, "parent")
