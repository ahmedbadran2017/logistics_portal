"""City check — orders whose shipping city Cathedis can't turn into an AWB.

The carrier matches the city against its own list; an Arabic city (or a phone
number typed into the city box) yields no AWB, so the parcel later strands with
no label. Measured on prod: 79% of no-AWB orders have an Arabic city vs 4% of
the ones that got one.

This queue surfaces those orders BEFORE picking, with a searchable picker of
Cathedis-accepted (Latin) cities, so a dispatcher sets the right city and the
order re-enters the pick pool. Arabic / junk-city orders are HELD OUT of the
pool (picking._BAD_CITY); unmatched Latin towns stay pickable but are warned
here. Dispatcher / manager only.
"""

import frappe
from frappe.utils import now_datetime

from logistics_portal.api.picking import _ARABIC_CLASS, _BAD_CITY, _EFF_CITY

_CO = "Justyol Morocco"


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("dispatcher", "manager"):
        frappe.throw("Only a dispatcher or manager can fix shipping cities.",
                     frappe.PermissionError)


def _accepted_cities():
    """The Latin cities that have produced a Cathedis AWB in the last 180 days —
    the ground-truth picker list. Cached 10 min. Arabic entries are dropped from
    the PICKER (we want a Latin target to normalise to)."""
    ck = "lp_cathedis_cities"
    cached = frappe.cache().get_value(ck)
    if cached:
        import json as _j
        try:
            return _j.loads(cached)
        except Exception:
            pass
    rows = frappe.db.sql(
        """SELECT custom_shipping_city c, COUNT(*) n
           FROM `tabSales Order`
           WHERE company = %s AND custom_awb IS NOT NULL AND custom_awb != ''
             AND custom_shipping_city IS NOT NULL AND TRIM(custom_shipping_city) != ''
             AND creation >= DATE_SUB(NOW(), INTERVAL 180 DAY)
           GROUP BY custom_shipping_city ORDER BY n DESC""", _CO, as_dict=True)
    seen, out = set(), []
    for r in rows:
        c = (r.c or "").strip()
        if not c:
            continue
        if any("؀" <= ch <= "ۿ" for ch in c):
            continue  # keep the picker Latin-only
        k = c.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
    import json as _j
    frappe.cache().set_value(ck, _j.dumps(out), expires_in_sec=600)
    return out


@frappe.whitelist()
def cathedis_cities(q=""):
    """Searchable list of Cathedis-accepted (Latin) cities for the picker."""
    _gate()
    cities = _accepted_cities()
    q = (q or "").strip().lower()
    if q:
        cities = [c for c in cities if q in c.lower()]
    return {"cities": cities[:200], "total": len(cities)}


@frappe.whitelist()
def city_check_queue(limit=200):
    """Confirmed-Pending orders whose city needs a human before they can ship:
    BLOCKED (Arabic / junk — held out of the pick pool) first, then WARN
    (unmatched Latin town — still pickable, but its city has never produced an
    AWB, so worth a glance)."""
    _gate()
    limit = min(max(int(limit or 200), 1), 500)
    accepted = _accepted_cities()
    accepted_lc = tuple({c.lower() for c in accepted}) or ("",)
    rows = frappe.db.sql(
        f"""SELECT so.name, so.customer_name customer, so.grand_total total,
                   COALESCE(NULLIF(so.custom_customer_phone,''),
                            so.custom_shipping_phone) phone,
                   {_EFF_CITY} city,
                   TIMESTAMPDIFF(HOUR, so.creation, NOW()) age_h,
                   {_BAD_CITY} blocked
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.custom_sales_status = 'Confirmed'
              AND so.company = %(co)s
              AND so.custom_logistics_status = 'Pending'
              AND so.creation >= DATE_SUB(NOW(), INTERVAL 90 DAY)
              AND NOT EXISTS (SELECT 1 FROM `tabPick List Item` pli
                              JOIN `tabPick List` p ON p.name = pli.parent
                              WHERE pli.sales_order = so.name AND p.docstatus < 2)
              AND ({_BAD_CITY}
                   OR LOWER(TRIM(COALESCE({_EFF_CITY}, ''))) NOT IN %(acc)s)
            ORDER BY blocked DESC, so.creation
            LIMIT %(limit)s""",
        {"co": _CO, "acc": accepted_lc, "limit": limit}, as_dict=True)
    blocked = sum(1 for r in rows if r.blocked)
    return {
        "blocked": blocked, "warn": len(rows) - blocked, "total": len(rows),
        "rows": [{
            "order": r.name, "customer": r.customer or "",
            "city": (r.city or "").strip(), "phone": r.phone or "",
            "total": float(r.total or 0), "ageH": int(r.age_h or 0),
            "blocked": bool(r.blocked),
        } for r in rows],
        "serverNow": str(now_datetime())[:19],
    }


@frappe.whitelist()
def set_shipping_city(order, city):
    """Set an order's shipping city to a carrier-valid value — written to the SO
    and to the linked Address (the field the carrier reads) — so it can get an
    AWB and re-enter the pick pool."""
    _gate()
    order = (order or "").strip()
    city = (city or "").strip()
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    if not city:
        frappe.throw("Pick a city.")
    frappe.db.set_value("Sales Order", order, "custom_shipping_city", city)
    an = (frappe.db.get_value("Sales Order", order, "shipping_address_name")
          or frappe.db.get_value("Sales Order", order, "customer_address"))
    if an:
        frappe.db.set_value("Address", an, "city", city)
    frappe.get_doc("Sales Order", order).add_comment(
        "Comment", f"Shipping city set to '{city}' for the carrier · by "
                   f"{frappe.session.user}")
    frappe.db.commit()
    return {"ok": True, "order": order, "city": city}
