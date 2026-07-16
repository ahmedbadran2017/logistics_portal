"""Customer segments — from the only history that matters in COD: did the
parcel actually get taken?

Measured on the live data before this existed (30-day cohort of every phone
with 3+ shipped parcels, asking what happened to parcel #3+ given #1-2):

    first two parcels failed  -> 27.1% of later parcels delivered
    mixed                     -> 31.0%
    first two delivered       -> 74.4%
    baseline                  -> 49.4%

So history predicts, strongly — but it does NOT determine: even the worst
group takes delivery a quarter of the time. That is why nothing here blocks
or cancels anything. The segment is shown to the agent BEFORE the call and
the agent decides. A 27% group auto-excluded is 27% of real revenue thrown
away.

Identity is the PHONE, digits only — not the Customer link (161,348 customer
records exist for 147,210 real phones; Shopify mints a new one per order),
and not RIGHT(phone, 9) either: 2,341 orders carry punctuation like
"+212 691-190596", where the naive key keeps "91-190596" and splits one
customer into several.
"""

import json

import frappe
from frappe.utils import now_datetime

# Digits-only, last 9 — the Moroccan subscriber number without the country
# code or the leading zero, however the phone happens to be punctuated.
_KEY_SQL = "RIGHT(REGEXP_REPLACE(COALESCE(NULLIF({t}.custom_customer_phone, ''), {t}.custom_shipping_phone), '[^0-9]', ''), 9)"

_SEG_KEY = "lp_segment_settings"
_SEG_DEFAULTS = {
    # Below this many shipped parcels there is no history to judge — the
    # customer is "new", which is two thirds of them (99,257 of 148,518 have
    # exactly one order).
    "minParcels": 2,
    "vipMinParcels": 3,
    "vipMinRate": 100,   # % of shipped parcels actually delivered
    "goodMinRate": 80,
    "watchMinRate": 50,
    # A parcel stuck in Delivery Exception may still land. Counting it as a
    # failure is the pessimistic reading; 18,365 parcels sit in that state.
    "exceptionCountsAsFailure": 1,
}

SEGMENTS = ("vip", "good", "watch", "risk", "black", "new")


def _seg_settings():
    raw = frappe.db.get_default(_SEG_KEY)
    out = dict(_SEG_DEFAULTS)
    if raw:
        try:
            saved = json.loads(raw)
            if isinstance(saved, dict):
                out.update({k: saved[k] for k in _SEG_DEFAULTS if k in saved})
        except Exception:
            pass
    return out


def digits(phone):
    d = "".join(ch for ch in str(phone or "") if ch.isdigit())
    return d[-9:] if len(d) >= 9 else ""


def _classify(h, s):
    """Segment from one customer's counted history."""
    shipped = h["delivered"] + h["failed"]
    if shipped < s["minParcels"]:
        return "new"
    rate = h["delivered"] * 100.0 / shipped
    if h["delivered"] == 0:
        return "black"
    if shipped >= s["vipMinParcels"] and rate >= s["vipMinRate"]:
        return "vip"
    if rate >= s["goodMinRate"]:
        return "good"
    if rate >= s["watchMinRate"]:
        return "watch"
    return "risk"


def history_for(phones):
    """{digits: {...}} for a page of customers — one scan, then cached.

    ~306ms for 20 phones cold on the live data; the cache makes a second look
    at the same customer free. Keyed per phone so a board of 50 shares
    whatever the last board already fetched.
    """
    keys = {}
    for p in phones:
        d = digits(p)
        if d:
            keys.setdefault(d, []).append(p)
    if not keys:
        return {}

    cache = frappe.cache()
    out, missing = {}, []
    for d in keys:
        hit = cache.get_value(f"lp_cust:{d}")
        if hit:
            try:
                out[d] = json.loads(hit)
                continue
            except Exception:
                pass
        missing.append(d)

    if missing:
        s = _seg_settings()
        fail_states = (["Delivery Exception", "Failed Attempt"]
                       if s["exceptionCountsAsFailure"] else ["Failed Attempt"])
        rows = frappe.db.sql(
            f"""SELECT {_KEY_SQL.format(t='so')} p,
                       COUNT(DISTINCT so.name) orders,
                       COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status = 'Delivered'
                                           THEN dn.name END) delivered,
                       COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status IN %(fail)s
                                           THEN dn.name END) failed,
                       COUNT(DISTINCT CASE WHEN so.custom_sales_status = 'Cancelled'
                                           THEN so.name END) cancelled,
                       MAX(so.creation) last_order,
                       SUM(CASE WHEN dn.custom_track_shipment_status = 'Delivered'
                                THEN so.grand_total ELSE 0 END) lifetime
                FROM `tabSales Order` so
                LEFT JOIN `tabDelivery Note Item` dni
                       ON dni.against_sales_order = so.name AND dni.docstatus = 1
                LEFT JOIN `tabDelivery Note` dn
                       ON dn.name = dni.parent AND dn.docstatus = 1
                WHERE so.docstatus = 1 AND {_KEY_SQL.format(t='so')} IN %(ph)s
                GROUP BY p""",
            {"ph": tuple(missing), "fail": tuple(fail_states)}, as_dict=True)
        found = set()
        for r in rows:
            h = {
                "orders": int(r.orders or 0),
                "delivered": int(r.delivered or 0),
                "failed": int(r.failed or 0),
                "cancelled": int(r.cancelled or 0),
                "lastOrder": str(r.last_order)[:10] if r.last_order else "",
                "lifetime": round(float(r.lifetime or 0)),
            }
            shipped = h["delivered"] + h["failed"]
            h["shipped"] = shipped
            h["rate"] = round(h["delivered"] * 100.0 / shipped) if shipped else None
            h["seg"] = _classify(h, s)
            out[r.p] = h
            found.add(r.p)
            cache.set_value(f"lp_cust:{r.p}", json.dumps(h), expires_in_sec=1800)
        # A phone with no submitted order at all still needs an answer.
        for d in missing:
            if d not in found:
                out[d] = {"orders": 0, "delivered": 0, "failed": 0, "cancelled": 0,
                          "shipped": 0, "rate": None, "lastOrder": "", "lifetime": 0,
                          "seg": "new"}
    return out


def bust(phone):
    d = digits(phone)
    if d:
        frappe.cache().delete_value(f"lp_cust:{d}")


@frappe.whitelist()
def card(phone):
    """One customer's full history for the panel behind the segment chip."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("confirmation", "manager",
                                                 "dispatcher"):
        frappe.throw("Not authorized.", frappe.PermissionError)
    d = digits(phone)
    if not d:
        return {"seg": "new", "orders": 0, "recent": [], "phone": phone}
    h = history_for([phone]).get(d, {})
    # The actual orders behind the counts — the agent reads them on the call.
    orders = frappe.db.sql(
        f"""SELECT so.name, so.creation, so.grand_total total,
                   so.custom_sales_status status,
                   so.custom_shipping_city city,
                   dn.custom_track_shipment_status track
            FROM `tabSales Order` so
            LEFT JOIN `tabDelivery Note Item` dni
                   ON dni.against_sales_order = so.name AND dni.docstatus = 1
            LEFT JOIN `tabDelivery Note` dn ON dn.name = dni.parent AND dn.docstatus = 1
            WHERE so.docstatus = 1 AND {_KEY_SQL.format(t='so')} = %(d)s
            GROUP BY so.name
            ORDER BY so.creation DESC LIMIT 20""", {"d": d}, as_dict=True)
    # NB: `recent`, not `orders` — h already carries "orders" as the COUNT, and
    # spreading a list over it silently replaced the number with an array.
    return {
        **h, "phone": phone,
        "recent": [{
            "order": o.name, "at": str(o.creation)[:10],
            "total": float(o.total or 0), "status": o.status or "",
            "city": (o.city or "").strip().title(), "track": o.track or "",
        } for o in orders],
    }


def risky_phones():
    """The 'black' set — 2+ parcels, none ever taken. Cached: the scan is ~2.5s
    over every delivery note on the site, and the answer moves slowly."""
    cache = frappe.cache()
    hit = cache.get_value("lp_risky_phones")
    if hit:
        try:
            return json.loads(hit)
        except Exception:
            pass
    s = _seg_settings()
    fail_states = (["Delivery Exception", "Failed Attempt"]
                   if s["exceptionCountsAsFailure"] else ["Failed Attempt"])
    rows = frappe.db.sql(
        f"""SELECT p FROM (
              SELECT {_KEY_SQL.format(t='so')} p,
                     COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status = 'Delivered'
                                         THEN dn.name END) d,
                     COUNT(DISTINCT dn.name) n
              FROM `tabDelivery Note` dn
              JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
              JOIN `tabSales Order` so ON so.name = dni.against_sales_order
              WHERE dn.docstatus = 1
                AND dn.custom_track_shipment_status IN %(states)s
              GROUP BY p
              HAVING n >= %(minp)s AND d = 0
            ) x WHERE p != ''""",
        {"states": tuple(["Delivered"] + fail_states),
         "minp": s["minParcels"]})
    out = [r[0] for r in rows if r[0]]
    cache.set_value("lp_risky_phones", json.dumps(out), expires_in_sec=1800)
    return out


@frappe.whitelist()
def segment_settings():
    from logistics_portal.api.auth import resolve_role
    from logistics_portal.api.confirmation import _is_cf_admin
    if resolve_role(frappe.session.user) not in ("confirmation", "manager"):
        frappe.throw("Not authorized.", frappe.PermissionError)
    return {**_seg_settings(), "canEdit": _is_cf_admin()}


@frappe.whitelist()
def save_segment_settings(settings=None):
    from logistics_portal.api.confirmation import _gate, _is_cf_admin
    _gate()
    if not _is_cf_admin():
        frappe.throw("Only the portal manager or a confirmation section admin "
                     "can change the segment rules.", frappe.PermissionError)
    if isinstance(settings, str):
        settings = json.loads(settings)
    settings = settings or {}
    out = _seg_settings()
    for k in ("minParcels", "vipMinParcels"):
        if k in settings:
            v = int(settings[k])
            if not (1 <= v <= 20):
                frappe.throw(f"{k} must be between 1 and 20.")
            out[k] = v
    for k in ("vipMinRate", "goodMinRate", "watchMinRate"):
        if k in settings:
            v = int(settings[k])
            if not (0 <= v <= 100):
                frappe.throw(f"{k} must be a percentage.")
            out[k] = v
    if out["goodMinRate"] < out["watchMinRate"]:
        frappe.throw("The 'good' threshold can't sit below the 'watch' one.")
    if "exceptionCountsAsFailure" in settings:
        out["exceptionCountsAsFailure"] = 1 if settings["exceptionCountsAsFailure"] else 0
    frappe.db.set_default(_SEG_KEY, json.dumps(out))
    frappe.db.commit()
    # Every cached verdict was computed under the old rules.
    frappe.cache().delete_keys("lp_cust:")
    frappe.cache().delete_value("lp_risky_phones")
    return {"ok": True, **out}


@frappe.whitelist()
def distribution():
    """How the base splits across segments — the section dashboard's headline.
    Heavy (a full scan of the delivery history); cached for an hour."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in ("confirmation", "manager"):
        frappe.throw("Not authorized.", frappe.PermissionError)
    cache = frappe.cache()
    hit = cache.get_value("lp_seg_dist")
    if hit:
        try:
            return json.loads(hit)
        except Exception:
            pass
    s = _seg_settings()
    fail_states = (["Delivery Exception", "Failed Attempt"]
                   if s["exceptionCountsAsFailure"] else ["Failed Attempt"])
    rows = frappe.db.sql(
        f"""SELECT p, d, n FROM (
              SELECT {_KEY_SQL.format(t='so')} p,
                     COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status = 'Delivered'
                                         THEN dn.name END) d,
                     COUNT(DISTINCT dn.name) n
              FROM `tabDelivery Note` dn
              JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
              JOIN `tabSales Order` so ON so.name = dni.against_sales_order
              WHERE dn.docstatus = 1
                AND dn.custom_track_shipment_status IN %(states)s
              GROUP BY p
            ) x WHERE p != ''""",
        {"states": tuple(["Delivered"] + fail_states)}, as_dict=True)
    counts = {k: 0 for k in SEGMENTS}
    for r in rows:
        h = {"delivered": int(r.d or 0), "failed": int(r.n or 0) - int(r.d or 0)}
        counts[_classify(h, s)] += 1
    out = {"counts": counts, "customers": len(rows),
           "at": str(now_datetime())[:19]}
    cache.set_value("lp_seg_dist", json.dumps(out), expires_in_sec=3600)
    return out
