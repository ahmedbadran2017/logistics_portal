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


def _site_now():
    """The SITE clock as a bound param. The DB server runs on its own
    time zone, so NOW() made fresh rows read negative ages."""
    from frappe.utils import now_datetime
    return str(now_datetime())[:19]
from frappe.utils import now_datetime

from logistics_portal.api.picking import _ARABIC_CLASS, _BAD_CITY, _EFF_CITY

_CO = "Justyol Morocco"


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("dispatcher", "manager", "tracking"):
        frappe.throw("lp:cityFixRole",
                     frappe.PermissionError)


# Cities a dispatcher/manager entered by hand that the 180-day AWB history
# hasn't seen (small towns, new routes). Persisted so a typed city STICKS — it
# joins the picker list AND stops its orders being flagged as unmatched forever.
JUNK = "\"'\\ \t"   # quotes/backslashes that survive the order feed and break the payload
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


# City strings Cathedis itself refused ("Ville introuvable: X" in the error
# log). This is the ground truth the accepted list was missing: the old list
# was "any city that ever ended up with an AWB", and an order whose city a
# human FIXED later still carried the broken spelling — so "Azamour",
# "CASABLNACA" and even phone numbers became "accepted" forever, and the
# check waved through exactly the orders it existed to stop (measured
# 2026-09-11: 660 carrier rejections in 30 days while the queue showed zero).
def _refused_cities():
    ck = "lp_cathedis_refused"
    cached = frappe.cache().get_value(ck)
    if cached:
        import json as _j
        try:
            return set(_j.loads(cached))
        except Exception:
            pass
    import re as _re
    out = set()
    for (err,) in frappe.db.sql(
            """SELECT error FROM `tabError Log`
               WHERE error LIKE '%%Ville introuvable%%'
                 AND creation >= DATE_SUB(NOW(), INTERVAL 120 DAY)"""):
        for m in _re.finditer(r"Ville introuvable: ([^\"\\\n]+)", err or ""):
            v = m.group(1).strip().lower()
            if v:
                out.add(v)
    import json as _j
    frappe.cache().set_value(ck, _j.dumps(sorted(out)), expires_in_sec=600)
    return out


def _hygienic(c):
    """A string that could actually be a city. Phone numbers, house addresses
    and two-letter fragments all made it into the AWB history."""
    c = (c or "").strip()
    if not (3 <= len(c) <= 32):
        return False
    if any(ch.isdigit() for ch in c) or "\n" in c or "\r" in c:
        return False
    low = c.lower()
    for frag in ("secteur", "point de relais", "rue ", "avenue ", "lot ",
                 "immeuble", "residence", "r\u00e9sidence", "\u00e9tage", "app "):
        if frag in low:
            return False
    return True


def _accepted_cities():
    """The Latin cities that can produce a Cathedis AWB: those seen on an AWB in
    the last 180 days that look like a city (hygiene) and were never REFUSED by
    Cathedis, PLUS the ones a dispatcher/manager added by hand (manual wins over
    everything). Cached 10 min."""
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
    refused = _refused_cities()
    seen, out = set(), []
    for r in rows:
        c = (r.c or "").strip()
        if not c:
            continue
        if any("؀" <= ch <= "ۿ" for ch in c):
            continue  # keep the picker Latin-only
        k = c.lower()
        if k in seen or k in refused or not _hygienic(c):
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
                   TIMESTAMPDIFF(HOUR, so.creation, %(now)s) age_h,
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
        {"now": _site_now(), "co": _CO, "acc": accepted_lc, "limit": limit}, as_dict=True)
    # IN-FLOW casualties: on a SUBMITTED pick list with no AWB back yet.
    #
    # The status list used to be ('Picked', 'Label Generated') and that missed
    # the ones that matter most: an order whose AWB never came back never
    # leaves 'Pending'. Between the pre-pick query, which excludes anything
    # already on a pick list, and this one, which only looked past Pending,
    # such an order was invisible on both halves of this screen — measured
    # 2026-09-08, 57 of 57 orders in that state appeared on neither. Drafts
    # stay out on purpose: a draft is live work, not a casualty.
    inflow = frappe.db.sql(
        f"""SELECT so.name, so.customer_name customer, so.grand_total total,
                   COALESCE(NULLIF(so.custom_customer_phone,''),
                            so.custom_shipping_phone) phone,
                   {_EFF_CITY} city,
                   TIMESTAMPDIFF(HOUR, so.creation, %(now)s) age_h,
                   {_BAD_CITY} blocked
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.custom_sales_status = 'Confirmed'
              AND so.company = %(co)s
              AND so.custom_logistics_status IN ('Pending', 'Picked', 'Label Generated')
              AND COALESCE(so.custom_awb, '') = ''
              AND COALESCE(so.custom_label_url, '') = ''
              AND so.creation >= DATE_SUB(NOW(), INTERVAL 90 DAY)
              AND EXISTS (SELECT 1 FROM `tabPick List Item` pli
                          JOIN `tabPick List` p ON p.name = pli.parent
                          WHERE pli.sales_order = so.name AND p.docstatus = 1)
            ORDER BY so.creation LIMIT 100""",
        {"now": _site_now(), "co": _CO}, as_dict=True)

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


def apply_city(order, city):
    """The city write itself, with NO gate of its own.

    Split out of set_shipping_city because the sort wall's repair now runs for
    packers too, and it has already checked its own roles by the time it gets
    here — calling the whitelisted function would re-check against the stricter
    city-module gate and refuse the very people it just authorised. Callers are
    responsible for their own permission check.
    """
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


@frappe.whitelist()
def set_shipping_city(order, city):
    """Set an order's shipping city to a carrier-valid value — written to the SO
    and to the linked Address (the field the carrier reads) — so it can get an
    AWB and re-enter the pick pool."""
    _gate()
    return apply_city(order, city)


def _tokens(s):
    """Words of 3+ chars, lowercased, punctuation stripped — no regex so the
    Latin-1 accents in the carrier's own list survive the split."""
    out, cur = [], []
    for ch in (s or "").lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if len(cur) > 2:
                out.append("".join(cur))
            cur = []
    if len(cur) > 2:
        out.append("".join(cur))
    return out


def _suggest_gate():
    """Reading candidate cities is part of sorting, so the sort-wall roles get
    it — unlike the city QUEUE, which stays a dispatcher board."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("packer", "dispatcher", "manager"):
        frappe.throw("Not authorized.", frappe.PermissionError)


@frappe.whitelist()
def suggest_city(order, limit=8):
    """Rank carrier-valid cities against what the customer actually typed.

    Fixing a label-less parcel is a matching exercise, not a search: the address
    reads 'Marrakech tamansourt' and Cathedis knows BOTH 'Marrakech' and
    'TAMANSOURT' — it just doesn't know the two glued together. Making a human
    scroll 505 entries to discover that is how these parcels end up abandoned,
    so score the accepted list against the words in the order's own city and put
    the plausible ones first. Returns {city, exact, suggestions} — `exact` true
    means nothing needs fixing and the AWB failed for another reason.
    """
    _suggest_gate()
    order = (order or "").strip()
    if not frappe.db.exists("Sales Order", order):
        frappe.throw("Unknown order.")
    # Score the ADDRESS city, not the sales-order field: the carrier reads the
    # Address, and the SO field is empty on most orders (measured 2026-09-08:
    # 5,499 of 9,726 in thirty days), so scoring it answered about the wrong
    # string. A stray quote reaches the API mangled -- J-005948 was stored as
    # '"Al Aaroui' and Cathedis received a lone backslash -- so match the clean
    # form and the real town comes back.
    an = (frappe.db.get_value("Sales Order", order, "shipping_address_name")
          or frappe.db.get_value("Sales Order", order, "customer_address"))
    raw = ((frappe.db.get_value("Address", an, "city") if an else "") or "").strip()
    if not raw:
        raw = (frappe.db.get_value("Sales Order", order, "custom_shipping_city") or "").strip()
    raw = raw.strip(JUNK).strip()
    cities = _accepted_cities()
    low = {}
    for c in cities:
        low.setdefault(c.strip().lower(), c)
    k = raw.lower().strip()
    if k and k in low:
        return {"city": raw, "exact": low[k], "suggestions": []}

    toks = _tokens(raw)
    scored = []
    for c in cities:
        ct = _tokens(c)
        cl = c.lower()
        s = 0
        for t in toks:
            if t in ct:
                s += 100                     # a whole word of the address IS this city
            elif t and (cl.startswith(t) or t.startswith(cl)):
                s += 40                      # one is a prefix of the other
            elif t and t in cl:
                s += 15                      # appears somewhere inside
        if s:
            # Prefer the shorter, cleaner entry when two score alike: the
            # carrier's list carries free-text junk ('Marrakech Massira 1').
            scored.append((-s, len(c), c))
    scored.sort()
    lim = min(max(int(limit or 8), 1), 25)
    return {"city": raw, "exact": "", "suggestions": [x[2] for x in scored[:lim]]}


def pool_city_literals():
    """The accepted set as escaped SQL literals — the pick pool's city fence.
    Empty string = fence open (never let a broken cache empty the pool)."""
    try:
        cities = _accepted_cities()
    except Exception:
        return ""
    if not cities:
        return ""
    lits = []
    for c in cities:
        v = c.strip().lower().replace("\\", "").replace("'", "''")
        if v:
            lits.append("'" + v + "'")
    return ",".join(lits)


# ---------------------------------------------------------------------------
# City performance matrix — how the GEOGRAPHY performs, with nobody's name on
# it. Two rates that must be read together: how many orders a city confirms,
# and how many of those actually get taken. A city can be excellent at one and
# poor at the other, and that pair is the whole point — measured 2026-09-13,
# El Jadida confirms 88.7% and delivers 68.1% while Tetouan confirms 80.9% and
# delivers 80.5%. A confirmed order that comes back cost the pick, the pack
# and the freight; one that was never confirmed cost a phone call.
# ---------------------------------------------------------------------------

# One city, one row. The raw field carries accents, case, trailing newlines and
# Arabic spellings of the same place, which split a city's volume across
# several rows and make every rate in them thinner and noisier than it is.
_CANON_FOLD = {
    "a": "àáâäãå", "e": "èéêë", "i": "ìíîï", "o": "òóôöõ", "u": "ùúûü",
    "c": "ç", "n": "ñ",
}
_FOLD = {ch: base for base, chars in _CANON_FOLD.items() for ch in chars}

# Same place, written differently. Kept small and explicit: a fuzzy matcher
# would quietly merge two real towns that share a prefix.
_CITY_ALIASES = {
    "MOHAMMEDIA": "MOHAMMADIA", "SALA AL JADIDA": "SALE", "EL JADIDA": "ELJADIDA",
    "AL HOCEIMA": "ALHOCEIMA", "ALHOCEIMA": "ALHOCEIMA",
    "KSAR L KBIR": "KSAR LKBIR", "TAROUDANT": "TAROUDANTE",
    "DAR BOUAZZA": "DARBOUAZZA", "MDIQ": "M DIQ",
}


def canon_city(raw):
    """The row a city belongs to: accent-folded, upper, single-spaced."""
    s = (raw or "").strip().lower()
    s = "".join(_FOLD.get(ch, ch) for ch in s)
    out, prev_space = [], False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_space = False
        elif not prev_space:
            out.append(" ")
            prev_space = True
    s = "".join(out).strip().upper()
    return _CITY_ALIASES.get(s, s)


# A delivery rate may only be taken over parcels whose journey ENDED. A parcel
# still in transit is not a failure, but counting it in the denominator makes
# it one — and because the newest week holds the most parcels still moving,
# every city appeared to collapse in the last column. Measured 2026-09-13:
# every one of the top twelve dropped six to ten points in the final week,
# uniformly, which is the shape of an artefact and not of a real decline.
_RESOLVED = ("Delivered", "Returned", "Not Delivered",
             "Failed Attempt", "Delivery Exception")


def _matrix_gate():
    from logistics_portal.api.permissions import is_ops_admin
    if not is_ops_admin():
        frappe.throw("Warehouse management only.", frappe.PermissionError)


def _shrink(raw, n, mean, k=40.0):
    """Pull a thin cell toward the network mean.

    Twelve orders at 100% is not a better city than four hundred at 78% — it
    is a city we have barely seen. The weight n/(n+k) makes a cell earn its
    distance from the average, so the matrix stops rewarding small samples.
    """
    if raw is None:
        return None
    w = n / (n + k) if (n + k) else 0.0
    return round(raw * w + mean * (1 - w), 1)


@frappe.whitelist()
def matrix(weeks=8, basis="overall", limit=14, min_orders=40):
    """City × week performance. basis: overall | confirm | deliver."""
    _matrix_gate()
    weeks = min(max(int(weeks or 8), 2), 26)
    limit = min(max(int(limit or 14), 1), 40)
    min_orders = max(int(min_orders or 40), 1)
    basis = basis if basis in ("overall", "confirm", "deliver") else "overall"
    # 0.56 s of aggregation over weeks of orders; the picture moves by the
    # day, so ten minutes shared across the team costs nothing.
    ck = f"lp_city_matrix:{weeks}:{basis}:{limit}:{min_orders}"
    try:
        hit = frappe.cache().get_value(ck, expires=True)
        if hit is not None:
            return hit
    except Exception:
        pass
    res = _matrix(weeks, basis, limit, min_orders)
    try:
        frappe.cache().set_value(ck, res, expires_in_sec=600)
    except Exception:
        pass
    return res


def _matrix(weeks, basis, limit, min_orders):
    rows = frappe.db.sql(
        """SELECT COALESCE(NULLIF(so.custom_shipping_city, ''), addr.city, '') AS raw,
                  YEARWEEK(so.creation, 3) AS wk,
                  COUNT(*) AS touched,
                  SUM(CASE WHEN so.custom_sales_status = 'Confirmed' THEN 1 ELSE 0 END) AS confirmed,
                  SUM(CASE WHEN so.custom_sales_status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled,
                  SUM(CASE WHEN dn.st = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
                  SUM(CASE WHEN dn.st IN %(done)s THEN 1 ELSE 0 END) AS shipped
           FROM `tabSales Order` so
           LEFT JOIN `tabAddress` addr
                  ON addr.name = COALESCE(NULLIF(so.shipping_address_name, ''),
                                          so.customer_address)
           LEFT JOIN (SELECT dni.against_sales_order AS so_name,
                             MAX(d.custom_track_shipment_status) AS st
                      FROM `tabDelivery Note Item` dni
                      JOIN `tabDelivery Note` d ON d.name = dni.parent
                      WHERE d.docstatus = 1 AND d.is_return = 0
                      GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name
           WHERE so.company = %(co)s AND so.docstatus = 1
             AND so.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)
             AND so.custom_sales_status IN ('Confirmed', 'Cancelled', 'Not Delivered',
                                            'Follow Up', 'Did not Answer')
           GROUP BY raw, wk""",
        {"co": _CO, "days": weeks * 7, "done": _RESOLVED}, as_dict=True)

    agg, cells = {}, {}
    for r in rows:
        c = canon_city(r.raw)
        if not c:
            continue
        a = agg.setdefault(c, {"n": 0, "dec": 0, "conf": 0, "ship": 0, "del": 0})
        dec = int(r.confirmed or 0) + int(r.cancelled or 0)
        a["n"] += int(r.touched or 0)
        a["dec"] += dec
        a["conf"] += int(r.confirmed or 0)
        a["ship"] += int(r.shipped or 0)
        a["del"] += int(r.delivered or 0)
        k = (c, int(r.wk))
        w = cells.setdefault(k, {"n": 0, "dec": 0, "conf": 0, "ship": 0, "del": 0})
        w["n"] += int(r.touched or 0)
        w["dec"] += dec
        w["conf"] += int(r.confirmed or 0)
        w["ship"] += int(r.shipped or 0)
        w["del"] += int(r.delivered or 0)

    def rate(hit, tot):
        return round(100.0 * hit / tot, 1) if tot else None

    def score_of(d):
        cf = rate(d["conf"], d["dec"])
        dl = rate(d["del"], d["ship"])
        if basis == "confirm":
            return cf, (d["dec"] or 0)
        if basis == "deliver":
            return dl, (d["ship"] or 0)
        if cf is None and dl is None:
            return None, 0
        # A parcel that came back cost the pick, the pack and the freight; an
        # order never confirmed cost a call. Delivery carries the heavier half.
        if cf is None:
            return dl, d["ship"]
        if dl is None:
            return cf, d["dec"]
        return round(dl * 0.6 + cf * 0.4, 1), min(d["dec"], d["ship"]) or d["dec"]

    # The mean every thin cell is pulled toward is this window's own network
    # average, not a number written into the code.
    net = {"n": 0, "dec": 0, "conf": 0, "ship": 0, "del": 0}
    for d in agg.values():
        for k2 in net:
            net[k2] += d[k2]
    net_score = score_of(net)[0] or 0.0

    wk_list = sorted({int(r.wk) for r in rows})[-weeks:]
    ranked = sorted(
        [(c, d) for c, d in agg.items() if d["n"] >= min_orders],
        key=lambda kv: -kv[1]["n"])[:limit]

    out = []
    for c, d in ranked:
        raw_s, n = score_of(d)
        row_cells = []
        for w in wk_list:
            cd = cells.get((c, w))
            if not cd or not cd["n"]:
                row_cells.append({"wk": w, "covered": False})
                continue
            cs, cn = score_of(cd)
            if cs is None:
                row_cells.append({"wk": w, "covered": False})
                continue
            row_cells.append({
                "wk": w, "covered": True, "n": cd["n"],
                "score": _shrink(cs, cn, net_score),
                "raw": cs, "conf": "high" if cn >= 40 else "low",
            })
        out.append({
            "city": c, "orders": d["n"],
            "confirmPct": rate(d["conf"], d["dec"]),
            "deliveredPct": rate(d["del"], d["ship"]),
            "decided": d["dec"], "shipped": d["ship"], "delivered": d["del"],
            "score": _shrink(raw_s, n, net_score),
            "cells": row_cells,
        })
    return {
        "basis": basis, "weeks": wk_list, "netScore": round(net_score, 1),
        "netConfirm": rate(net["conf"], net["dec"]),
        "netDeliver": rate(net["del"], net["ship"]),
        "cities": out, "cityCount": len(agg),
    }


@frappe.whitelist()
def city_card(city, weeks=8):
    """One city's funnel and the reasons behind its two rates."""
    _matrix_gate()
    weeks = min(max(int(weeks or 8), 2), 26)
    target = canon_city(city)
    rows = frappe.db.sql(
        """SELECT COALESCE(NULLIF(so.custom_shipping_city, ''), addr.city, '') AS raw,
                  so.custom_sales_status AS st, so.custom_cancellation_reason AS why,
                  dn.st AS track, so.grand_total AS total
           FROM `tabSales Order` so
           LEFT JOIN `tabAddress` addr
                  ON addr.name = COALESCE(NULLIF(so.shipping_address_name, ''),
                                          so.customer_address)
           LEFT JOIN (SELECT dni.against_sales_order AS so_name,
                             MAX(d.custom_track_shipment_status) AS st
                      FROM `tabDelivery Note Item` dni
                      JOIN `tabDelivery Note` d ON d.name = dni.parent
                      WHERE d.docstatus = 1 AND d.is_return = 0
                      GROUP BY dni.against_sales_order) dn ON dn.so_name = so.name
           WHERE so.company = %(co)s AND so.docstatus = 1
             AND so.creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)""",
        {"co": _CO, "days": weeks * 7}, as_dict=True)
    f = {"orders": 0, "confirmed": 0, "cancelled": 0, "shipped": 0,
         "delivered": 0, "failed": 0, "value": 0.0, "lostValue": 0.0}
    reasons, fails = {}, {}
    for r in rows:
        if canon_city(r.raw) != target:
            continue
        f["orders"] += 1
        f["value"] += float(r.total or 0)
        if r.st == "Confirmed":
            f["confirmed"] += 1
        elif r.st == "Cancelled":
            f["cancelled"] += 1
            if r.why:
                reasons[r.why] = reasons.get(r.why, 0) + 1
        if r.track in _RESOLVED:
            f["shipped"] += 1
            if r.track == "Delivered":
                f["delivered"] += 1
            else:
                f["failed"] += 1
                f["lostValue"] += float(r.total or 0)
                fails[r.track] = fails.get(r.track, 0) + 1
    top = lambda d: sorted([{"label": k, "n": v} for k, v in d.items()],
                           key=lambda x: -x["n"])[:6]
    dec = f["confirmed"] + f["cancelled"]
    return {
        "city": target, "weeks": weeks, "funnel": {
            "orders": f["orders"], "confirmed": f["confirmed"],
            "cancelled": f["cancelled"], "shipped": f["shipped"],
            "delivered": f["delivered"], "failed": f["failed"],
        },
        "confirmPct": round(100.0 * f["confirmed"] / dec, 1) if dec else None,
        "deliveredPct": round(100.0 * f["delivered"] / f["shipped"], 1) if f["shipped"] else None,
        "value": round(f["value"]), "lostValue": round(f["lostValue"]),
        "cancelReasons": top(reasons), "failReasons": top(fails),
    }
