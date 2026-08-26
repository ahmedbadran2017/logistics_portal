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


# Cities a dispatcher/manager entered by hand that the 180-day AWB history
# hasn't seen (small towns, new routes). Persisted so a typed city STICKS — it
# joins the picker list AND stops its orders being flagged as unmatched forever.
_MANUAL_KEY = "lp_manual_cities"


def _has_arabic(s):
    for ch in (s or ""):
        if "؀" <= ch <= "ۿ":
            return True
    return False


def _manual_cities():
    import json as _j
    raw = frappe.db.get_default(_MANUAL_KEY)
    if raw:
        try:
            v = _j.loads(raw)
            if isinstance(v, list):
                return [str(x) for x in v]
        except Exception:
            pass
    return []


def _add_manual_city(city):
    """Persist a hand-entered Latin city (dedup, case-insensitive) and drop the
    picker cache so it shows up — and clears its orders — immediately."""
    import json as _j
    city = (city or "").strip()
    # Arabic / empty / digit-bearing is exactly what the queue exists to fix
    # (a phone number typed into the city box) — never accept those.
    if not city or _has_arabic(city) or any(ch.isdigit() for ch in city):
        return
    cur = _manual_cities()
    if city.lower() in {c.lower() for c in cur}:
        return
    cur.append(city)
    frappe.db.set_default(_MANUAL_KEY, _j.dumps(cur))
    frappe.cache().delete_value("lp_cathedis_cities")


def _accepted_cities():
    """The Latin cities that can produce a Cathedis AWB: those seen on an AWB in
    the last 180 days, PLUS the ones a dispatcher/manager added by hand. Cached
    10 min. Arabic entries are dropped from the PICKER (we want a Latin target)."""
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
    # Manager-entered cities join the accepted set, so a hand-typed city both
    # appears in the picker and clears its orders from the unmatched queue.
    for c in _manual_cities():
        c = (c or "").strip()
        if not c or _has_arabic(c) or c.lower() in seen:
            continue
        seen.add(c.lower())
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
    # IN-FLOW casualties: already picked (Picked / Label Generated) but the AWB
    # never came back — usually the same bad-city cause, discovered only at the
    # sort wall ("no carrier label" cards). They used to be invisible here
    # because this queue was pre-pick only; the dispatcher fixes the city then
    # retries the AWB from this same screen.
    inflow = frappe.db.sql(
        f"""SELECT so.name, so.customer_name customer, so.grand_total total,
                   COALESCE(NULLIF(so.custom_customer_phone,''),
                            so.custom_shipping_phone) phone,
                   {_EFF_CITY} city,
                   TIMESTAMPDIFF(HOUR, so.creation, NOW()) age_h,
                   {_BAD_CITY} blocked
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.custom_sales_status = 'Confirmed'
              AND so.company = %(co)s
              AND so.custom_logistics_status IN ('Picked', 'Label Generated')
              AND COALESCE(so.custom_awb, '') = ''
              AND so.creation >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            ORDER BY so.creation LIMIT 100""",
        {"co": _CO}, as_dict=True)

    def _row(r, in_flow=False):
        return {"order": r.name, "customer": r.customer or "",
                "city": (r.city or "").strip(), "phone": r.phone or "",
                "total": float(r.total or 0), "ageH": int(r.age_h or 0),
                "blocked": bool(r.blocked), "inFlow": in_flow}

    blocked = sum(1 for r in rows if r.blocked)
    return {
        "blocked": blocked, "warn": len(rows) - blocked,
        "inFlow": len(inflow), "total": len(rows) + len(inflow),
        # In-flow first: those parcels are physically waiting at the sort wall.
        "rows": [_row(r, True) for r in inflow] + [_row(r) for r in rows],
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
    # Remember it: a valid city a human set once should never re-flag its own or
    # other orders, and should be offered in the picker next time.
    _add_manual_city(city)
    frappe.db.commit()
    return {"ok": True, "order": order, "city": city}
