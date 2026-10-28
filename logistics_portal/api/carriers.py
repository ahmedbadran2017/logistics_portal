"""Which carrier takes a parcel — the settings, the rule, and the router.

Until 2026-10 the carrier was fixed by company: ecommerce_integrations'
pick-list job built a CathedisShipping for Justyol Morocco and handed it to
CustomPickList.create_delivery_note_on_submit, which calls
provider.create_delivery_note_shipment(dn) for every order. Sendit is the
second carrier (deal signed 2026-10). The label must stay automatic, so the
decision sits at exactly that call: overrides/pick_list.py passes a
CarrierRouter instead of the bare provider, and the router sends each note
to Cathedis untouched or to sendit.create_for_delivery_note. Nothing before
or after that call changes.

Settings live in defaults (JSON, lp_carrier_settings), keys in the password
store — no doctype, no migrate:

    kill            everything to Cathedis, now
    sendit.mode     off | test (only the listed test orders) | on (rules)
    rules           first match wins: cities, payment types, share %, max/day
    test_orders     order numbers that go to Sendit while in test mode
    city_map        our city -> a chosen Sendit district id

A city Sendit does not serve (or that is not mapped) goes to Cathedis with a
comment, never to a stuck parcel. The share split is by a hash of the order
number: random across orders, and the same answer if the AWB is retried.
"""

import hashlib
import json

import frappe
from frappe.utils import nowdate

CATHEDIS, SENDIT = "Cathedis", "Sendit"
_KEY = "lp_carrier_settings"

DEFAULTS = {
    "kill": False,
    "sendit": {"mode": "off", "pickup_district_id": None, "pickup_name": "Justyol",
               "pickup_phone": "", "pickup_address": "", "allow_open": 1, "allow_try": 0,
               "label_format": 1},
    "rules": [],
    "test_orders": [],
    "city_map": {},
}


def settings():
    raw = frappe.db.get_default(_KEY)
    try:
        s = json.loads(raw) if raw else {}
    except Exception:
        s = {}
    out = json.loads(json.dumps(DEFAULTS))
    for k, v in (s or {}).items():
        if k == "sendit" and isinstance(v, dict):
            out["sendit"].update(v)
        else:
            out[k] = v
    return out


def _save(s):
    frappe.db.set_default(_KEY, json.dumps(s, ensure_ascii=False))
    frappe.db.commit()


def _gate():
    from logistics_portal.api.permissions import is_ops_admin
    if not is_ops_admin():
        frappe.throw("Warehouse management only.", frappe.PermissionError)


# ── the decision ──────────────────────────────────────────────────────────

def _bucket(order):
    return int(hashlib.md5(order.encode()).hexdigest()[:8], 16) % 100


def _city(so_name, dn=None):
    addr = (dn.get("shipping_address_name") if dn else None) or \
        frappe.db.get_value("Sales Order", so_name, "shipping_address_name")
    city = frappe.db.get_value("Address", addr, "city") if addr else ""
    return (city or frappe.db.get_value("Sales Order", so_name, "custom_shipping_city") or "").strip()


def _street(so_name, dn=None):
    addr = (dn.get("shipping_address_name") if dn else None) or \
        frappe.db.get_value("Sales Order", so_name, "shipping_address_name")
    if not addr:
        return ""
    a = frappe.db.get_value("Address", addr, ["address_line1", "address_line2"], as_dict=True) or {}
    return " ".join(x for x in [a.get("address_line1"), a.get("address_line2")] if x)


def _sendit_today():
    # Parcels CREATED today: the order's `modified` moves with every Sendit
    # webhook, so counting by it filled the cap with last week's parcels.
    return int(frappe.db.sql(
        """SELECT COUNT(DISTINCT reference_name) FROM `tabComment`
           WHERE reference_doctype = 'Sales Order' AND content LIKE 'Sendit parcel %% created%%'
             AND creation >= %s""", (nowdate(),))[0][0] or 0)


def choose(so_name, dn=None):
    """(carrier, why) for one order. Pure read: nothing is written."""
    from logistics_portal.api import sendit
    from logistics_portal.api.sendit import _norm
    s = settings()
    if s.get("kill"):
        return CATHEDIS, "kill switch on"
    mode = s["sendit"].get("mode", "off")
    if mode == "off":
        return CATHEDIS, "Sendit off"
    if not sendit.has_keys():
        return CATHEDIS, "Sendit keys not set"
    city = _city(so_name, dn)
    why = ""
    if so_name in (s.get("test_orders") or []):
        why = "test order"
    elif mode == "test":
        return CATHEDIS, "Sendit in test mode — not a test order"
    else:
        pt = frappe.db.get_value("Sales Order", so_name, "payment_type") or ""
        for i, r in enumerate(s.get("rules") or []):
            cities = {_norm(c) for c in (r.get("cities") or []) if c}
            if cities and _norm(city) not in cities:
                continue
            pts = [p for p in (r.get("payment_types") or []) if p]
            if pts and pt not in pts:
                continue
            if (r.get("carrier") or CATHEDIS) != SENDIT:
                return CATHEDIS, f"rule {i + 1}"
            share = int(r.get("share") if r.get("share") is not None else 100)
            if _bucket(so_name) >= share:
                return CATHEDIS, f"rule {i + 1}: outside the {share}% Sendit share"
            cap = int(r.get("max_per_day") or 0)
            if cap and _sendit_today() >= cap:
                return CATHEDIS, f"rule {i + 1}: Sendit daily cap {cap} reached"
            why = f"rule {i + 1} ({share}%)"
            break
        else:
            return CATHEDIS, "no rule"
    did, label = sendit.district_for(city, s.get("city_map"), _street(so_name, dn))
    if not did:
        return CATHEDIS, f"Sendit does not serve / map {city or 'this city'}"
    return SENDIT, f"{why} · {label}"


class CarrierRouter:
    """Stands in for the provider the pick-list job built (CathedisShipping):
    every attribute is the provider's, except the one call that creates the
    carrier parcel, which goes to the carrier choose() names."""

    def __init__(self, base):
        self._base = base

    def __getattr__(self, name):
        return getattr(self._base, name)

    def create_delivery_note_shipment(self, delivery_note):
        so = next((i.against_sales_order for i in (delivery_note.get("items") or [])
                   if i.get("against_sales_order")), None)
        if not so or delivery_note.get("company") != "Justyol Morocco":
            return self._base.create_delivery_note_shipment(delivery_note)
        # Already a Sendit parcel (an AWB retry, a second note for the same
        # order): never a second parcel — the note gets the parcel's fields.
        cur = frappe.db.get_value("Sales Order", so, ["custom_tracking_company", "custom_awb",
                                                      "custom_label_url"], as_dict=True) or {}
        if cur.get("custom_tracking_company") == SENDIT and cur.get("custom_awb"):
            for k in ("custom_tracking_company", "custom_awb", "custom_label_url"):
                if cur.get(k) and frappe.db.has_column("Delivery Note", k):
                    frappe.db.set_value("Delivery Note", delivery_note.name, k, cur[k], update_modified=False)
            return None
        try:
            carrier, why = choose(so, delivery_note)
        except Exception:
            # The decision itself must never cost an order its label.
            frappe.log_error(frappe.get_traceback()[:2000], f"carrier choice failed {so} — Cathedis")
            carrier, why = CATHEDIS, "choice failed"
        if carrier == SENDIT:
            from logistics_portal.api import sendit
            try:
                return sendit.create_for_delivery_note(delivery_note, so, why)
            except sendit.SenditError as e:
                # Refused, definitively, before any parcel existed at Sendit:
                # the order must not sit label-less, so Cathedis takes it.
                frappe.log_error(str(e)[:1500], f"Sendit refused {so} — sent to Cathedis")
                _note(so, f"Sendit refused the parcel ({str(e)[:200]}) — created with Cathedis instead")
            except Exception as e:
                # A timeout, a 5xx, an answer without a code, or a bug: the
                # parcel MAY exist at Sendit. A Cathedis label now could be
                # the second label for one box — so none. The order stays
                # label-less, visible on the wall and on "Labelled, never left".
                frappe.log_error(frappe.get_traceback()[:2000], f"Sendit uncertain {so} — no label made")
                _note(so, f"Sendit did not confirm the parcel ({str(e)[:160]}). No label was made — "
                          "check the Sendit dashboard, then retry the label from the wall.")
                return None
        return self._base.create_delivery_note_shipment(delivery_note)


def _note(so, text):
    try:
        frappe.get_doc("Sales Order", so).add_comment("Comment", text)
    except Exception:
        pass


def create_awb(dn_doc):
    """The portal's own retry path (picking.relabel_order) — same decision."""
    import logistics_portal.overrides.cathedis  # noqa: F401 — prepaid AWBs at 0
    from ecommerce_integrations.shipping.cathedis import CathedisShipping
    return CarrierRouter(CathedisShipping()).create_delivery_note_shipment(dn_doc)


def carrier_of(so_name):
    return frappe.db.get_value("Sales Order", so_name, "custom_tracking_company") or CATHEDIS


# ── the settings screen ───────────────────────────────────────────────────

def _webhook_url():
    # get_url() carries the bench's host_name — "admin.justyol.com:8000" on
    # prod, an address Sendit cannot reach. The public host is the one the
    # manager opened this screen on.
    path = "/api/method/logistics_portal.api.sendit.webhook"
    host = (getattr(frappe.local, "request", None) and frappe.local.request.host) or ""
    host = host.split(":")[0]
    return f"https://{host}{path}" if host else frappe.utils.get_url(path)


@frappe.whitelist()
def get_config():
    _gate()
    from logistics_portal.api import sendit
    s = settings()
    ds = sendit.districts()
    pub, _ = sendit.keys()
    counts = {r[0] or "—": int(r[1]) for r in frappe.db.sql(
        """SELECT custom_track_shipment_status, COUNT(*) FROM `tabSales Order`
           WHERE custom_tracking_company = %s GROUP BY 1""", (SENDIT,))}
    return {"settings": s, "keysSet": sendit.has_keys(),
            "publicKeyHint": (pub[:4] + "…" + pub[-3:]) if len(pub) > 8 else ("set" if pub else ""),
            "webhookUrl": _webhook_url(), "districts": len(ds),
            "sendit": counts}


@frappe.whitelist(methods=["POST"])
def save_config(config):
    _gate()
    c = json.loads(config) if isinstance(config, str) else (config or {})
    s = settings()
    s["kill"] = bool(c.get("kill"))
    sd = c.get("sendit") or {}
    if sd.get("mode") in ("off", "test", "on"):
        s["sendit"]["mode"] = sd["mode"]
    for k in ("pickup_name", "pickup_phone", "pickup_address"):
        if k in sd:
            s["sendit"][k] = str(sd[k] or "")[:200]
    for k in ("pickup_district_id", "allow_open", "allow_try", "label_format"):
        if k in sd and sd[k] not in (None, ""):
            s["sendit"][k] = int(sd[k])
    rules = []
    for r in (c.get("rules") or [])[:20]:
        rules.append({"cities": [str(x).strip() for x in (r.get("cities") or []) if str(x).strip()][:60],
                      "payment_types": [str(x) for x in (r.get("payment_types") or []) if x][:10],
                      "carrier": SENDIT if r.get("carrier") == SENDIT else CATHEDIS,
                      "share": max(0, min(100, int(r.get("share") if r.get("share") is not None else 100))),
                      "max_per_day": max(0, int(r.get("max_per_day") or 0))})
    s["rules"] = rules
    tests = []
    for x in (c.get("test_orders") or [])[:50]:
        x = str(x).strip()
        if not x:
            continue
        # "266999" typed for "#266999": store the real order name, or it
        # never matches at submit.
        if not frappe.db.exists("Sales Order", x) and frappe.db.exists("Sales Order", "#" + x.lstrip("#")):
            x = "#" + x.lstrip("#")
        tests.append(x)
    s["test_orders"] = tests
    if isinstance(c.get("city_map"), dict):
        s["city_map"] = {str(k): int(v) for k, v in c["city_map"].items() if v}
    _save(s)
    frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "User",
                    "reference_name": frappe.session.user,
                    "content": f"Carrier settings saved: kill={s['kill']} sendit={s['sendit']['mode']} "
                               f"rules={len(rules)} tests={len(s['test_orders'])}"}).insert(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "settings": s}


@frappe.whitelist(methods=["POST"])
def set_sendit_keys(public_key="", secret_key=""):
    _gate()
    from logistics_portal.api import sendit
    sendit.set_keys(public_key, secret_key)
    frappe.db.commit()
    return {"ok": True, "keysSet": sendit.has_keys()}


@frappe.whitelist(methods=["POST"])
def test_connection():
    """Log in, read the pickup cities, sync the destination list."""
    _gate()
    from logistics_portal.api import sendit
    try:
        sendit._token(force=True)
        pickups = sendit.pickup_cities()
        ds = sendit.sync_districts()
        return {"ok": True, "pickupCities": pickups, "districts": len(ds)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:400]}


@frappe.whitelist()
def city_coverage(days=30):
    """Our busiest cities and the Sendit district each would go to."""
    _gate()
    from logistics_portal.api import sendit
    s = settings()
    rows = frappe.db.sql(
        """SELECT COALESCE(NULLIF(a.city, ''), so.custom_shipping_city) AS city, COUNT(*) AS n
           FROM `tabSales Order` so LEFT JOIN `tabAddress` a ON a.name = so.shipping_address_name
           WHERE so.docstatus = 1 AND so.company = 'Justyol Morocco'
             AND so.transaction_date >= DATE_SUB(%s, INTERVAL %s DAY)
           GROUP BY 1 ORDER BY n DESC LIMIT 80""", (nowdate(), int(days)), as_dict=True)
    out = []
    for r in rows:
        did, label = sendit.district_for(r.city, s.get("city_map"))
        out.append({"city": r.city or "", "orders": int(r.n), "districtId": did, "district": label or ""})
    return {"rows": out, "districts": [{"id": d["id"], "label": f"{d['ville']} / {d['name']}",
                                        "price": d.get("price"), "delay": d.get("delay")}
                                       for d in sendit.districts()]}


@frappe.whitelist()
def preview(order):
    """Which carrier this order would get right now, and why."""
    _gate()
    so = (order or "").strip()
    if not frappe.db.exists("Sales Order", so):
        so = "#" + so.lstrip("#") if frappe.db.exists("Sales Order", "#" + so.lstrip("#")) else so
    if not frappe.db.exists("Sales Order", so):
        frappe.throw("Unknown order.")
    c, why = choose(so)
    return {"order": so, "carrier": c, "why": why, "city": _city(so),
            "current": frappe.db.get_value("Sales Order", so, "custom_tracking_company") or ""}


@frappe.whitelist()
def sendit_parcels(limit=100):
    _gate()
    rows = frappe.db.sql(
        """SELECT so.name, so.customer_name, so.custom_awb, so.custom_logistics_status,
                  so.custom_track_shipment_status, so.grand_total, so.modified,
                  (SELECT COUNT(*) FROM `tabFile` f WHERE f.attached_to_doctype = 'Sales Order'
                   AND f.attached_to_name = so.name AND f.file_name LIKE 'Sendit_Label_%%') AS labels
           FROM `tabSales Order` so WHERE so.custom_tracking_company = %s
           ORDER BY so.modified DESC LIMIT %s""", (SENDIT, int(limit)), as_dict=True)
    return {"rows": [{"order": r.name, "customer": r.customer_name or "", "code": r.custom_awb or "",
                      "status": r.custom_logistics_status or "", "track": r.custom_track_shipment_status or "",
                      "mad": float(r.grand_total or 0), "label": bool(r.labels),
                      "at": str(r.modified)[:16]} for r in rows]}


@frappe.whitelist(methods=["POST"])
def sendit_action(order, action):
    """refresh | label | cancel for one Sendit parcel."""
    _gate()
    from logistics_portal.api import sendit
    code, carrier, ls = frappe.db.get_value("Sales Order", order,
                                            ["custom_awb", "custom_tracking_company", "custom_logistics_status"]) or (None, None, None)
    if carrier != SENDIT or not code:
        frappe.throw("Not a Sendit parcel.")
    try:
        if action == "refresh":
            d = sendit.detail(code)
            st = d.get("status") or d.get("statut") or ""
            return {"ok": True, "status": st, "applied": sendit.apply_status(code, st) if st else None}
        if action == "label":
            sendit.attach_label(order, code)
            frappe.db.commit()
            return {"ok": True}
        if action == "cancel":
            if ls in ("Shipped", "Delivered", "Returned"):
                frappe.throw("Already collected by Sendit — cancel it with Sendit directly.")
            sendit.cancel(code)
            frappe.get_doc("Sales Order", order).add_comment(
                "Comment", f"Sendit parcel {code} cancelled by {frappe.session.user}")
            frappe.db.commit()
            return {"ok": True}
    except sendit.SenditError as e:
        return {"ok": False, "error": str(e)[:300]}
    frappe.throw("Unknown action.")


@frappe.whitelist(methods=["POST"])
def sendit_pickup(orders=None):
    """Ask Sendit to collect: the given orders, or every labelled Sendit
    parcel still in the building (Label Printed / Generated)."""
    _gate()
    from logistics_portal.api import sendit
    names = json.loads(orders) if isinstance(orders, str) else (orders or [])
    cond, args = "", [SENDIT]
    if names:
        cond = " AND name IN %s"
        args.append(tuple(names))
    rows = frappe.db.sql(f"""SELECT name, custom_awb FROM `tabSales Order`
                             WHERE custom_tracking_company = %s AND COALESCE(custom_awb, '') <> ''
                               AND custom_logistics_status IN ('Label Generated', 'Label Printed'){cond}""",
                         tuple(args), as_dict=True)
    if not rows:
        return {"ok": False, "error": "No Sendit parcel waiting for collection."}
    try:
        code = sendit.request_pickup([r.custom_awb for r in rows], note=f"{len(rows)} colis Justyol")
    except sendit.SenditError as e:
        return {"ok": False, "error": str(e)[:300]}
    for r in rows:
        frappe.get_doc("Sales Order", r.name).add_comment(
            "Comment", f"Sendit collection requested ({code or 'no code'}) by {frappe.session.user}")
    frappe.db.commit()
    return {"ok": True, "pickup": code, "parcels": len(rows)}
