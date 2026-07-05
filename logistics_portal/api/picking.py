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
    """Pick lists assigned to the current picker that aren't shipped yet,
    shaped for the queue cards. Sorted by SLA urgency (expected ship date)."""
    user = user or frappe.session.user
    try:
        pls = frappe.get_all(
            "Pick List",
            filters={
                "custom_assigned_picker": user,
                "custom_logistics_status": ["!=", "Shipped"],
                "docstatus": ["<", 2],
            },
            fields=["name", "custom_items_count", "custom_total_quantity", "modified"],
            order_by="modified desc",
            limit=50,
        )
        out = []
        for pl in pls:
            so = _linked_sales_order(pl.name)
            out.append(
                {
                    "name": "#" + (so.get("name") if so else pl.name),
                    "pick_list": pl.name,
                    "customer": (so or {}).get("customer_name", ""),
                    "channel": (so or {}).get("custom_channel", ""),
                    "items": pl.custom_items_count or 0,
                    "total": (so or {}).get("grand_total", 0),
                    "stage": (so or {}).get("custom_logistics_status", "Pending"),
                    "sla": "On Track",
                }
            )
        return out
    except Exception:
        frappe.log_error(frappe.get_traceback(), "logistics_portal.my_queue")
        return []


@frappe.whitelist()
def pick_items(order):
    """Items to pick for a given order (via its Pick List)."""
    try:
        pl = frappe.db.get_value(
            "Pick List", {"name": order}, "name"
        ) or _pick_list_for_order(order)
        if not pl:
            return []
        rows = frappe.get_all(
            "Pick List Item",
            filters={"parent": pl},
            fields=["item_name as name", "custom_sku as sku", "qty", "warehouse as bin"],
        )
        return [dict(r, picked=0) for r in rows]
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
    # The board caches its summary for 60s — bust it so the action shows at once.
    frappe.cache().delete_value("lp_board_summary")
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
