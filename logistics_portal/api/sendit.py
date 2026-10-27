"""Sendit — the second carrier, spoken to through its REST API.

API: https://app.sendit.ma/api/v1/ (swagger at /api/documentation, read
2026-10-27). Bearer token from POST /login with the account's public and
secret keys; 1,000 requests an hour. What this module uses:

    POST /login                       token
    GET  /districts?page=             destination cities (district ids, price, delay)
    GET  /districts/pickup-cities     where Sendit collects from
    POST /deliveries                  create a parcel -> its code ("DH…")
    POST /deliveries/getlabels        label PDF (printFormat 1 = thermal 10x10)
    GET  /deliveries/{code}           status, for the pull that backs the webhook
    DELETE /deliveries/{code}         cancel before collection
    POST /pickups                     ask for a collection of these codes

Status changes arrive by webhook (event delivery.status.update), signed
HMAC-SHA256 of the raw body with the API key chosen when the webhook was
created, in X-Sendit-Signature.

A Sendit parcel lands on the order exactly where a Cathedis one does —
custom_tracking_company / custom_awb / custom_tracking_number / the label
PDF attached as "Sendit_Label_<code>.pdf" — so the sort wall, the label
print, Pulse and every tracking screen read it unchanged. Its events are
written as comments in the same sentences carrier_events already knows,
owned by sendit@justyol.com.

Which parcels come here is carriers.choose(); this module never decides.
"""

import hashlib
import hmac
import json
import re
import unicodedata

import frappe
import requests
from frappe.utils import now_datetime

BASE = "https://app.sendit.ma/api/v1/"
CARRIER = "Sendit"
COMMENT_USER = "sendit@justyol.com"
_KEYS_DT, _KEYS_NAME = "LP Carrier", "Sendit"
_TOKEN = "lp_sendit_token"
_DISTRICTS = "lp_sendit_districts"
_TIMEOUT = 30


class SenditError(Exception):
    """Sendit refused, definitively (a 4xx answer, or a check before any call):
    no parcel exists there, so another carrier may take the order."""

    def __init__(self, msg, status=0):
        super().__init__(msg)
        self.status = status


class SenditAmbiguous(Exception):
    """The parcel MAY exist at Sendit (timeout, 5xx, an answer without a code).
    Never fall back to another carrier on this: that is two labels for one
    parcel. The order stays label-less, in sight on the wall and on
    "Labelled, never left", until someone looks."""


# ── keys and token ────────────────────────────────────────────────────────

def keys():
    from frappe.utils.password import get_decrypted_password
    pub = get_decrypted_password(_KEYS_DT, _KEYS_NAME, "public_key", raise_exception=False) or ""
    sec = get_decrypted_password(_KEYS_DT, _KEYS_NAME, "secret_key", raise_exception=False) or ""
    return pub, sec


def set_keys(public_key, secret_key):
    from frappe.utils.password import set_encrypted_password
    if public_key:
        set_encrypted_password(_KEYS_DT, _KEYS_NAME, public_key.strip(), "public_key")
    if secret_key:
        set_encrypted_password(_KEYS_DT, _KEYS_NAME, secret_key.strip(), "secret_key")
    frappe.cache().delete_value(_TOKEN)


def has_keys():
    pub, sec = keys()
    return bool(pub and sec)


def _token(force=False):
    if not force:
        t = frappe.cache().get_value(_TOKEN)
        if t:
            return t
    pub, sec = keys()
    if not (pub and sec):
        raise SenditError("Sendit keys are not set (Transporteurs settings).")
    r = requests.post(BASE + "login", json={"public_key": pub, "secret_key": sec},
                      headers={"Accept": "application/json"}, timeout=_TIMEOUT)
    body = _json(r)
    tok = ((body or {}).get("data") or {}).get("token")
    if r.status_code >= 400 or not tok:
        raise SenditError(f"Sendit login failed ({r.status_code}): {_msg(body) or r.text[:200]}")
    # The token's lifetime is not documented; six hours, and any 401/403
    # re-logs once (_req), so a shorter one only costs one extra call.
    frappe.cache().set_value(_TOKEN, tok, expires_in_sec=6 * 3600)
    return tok


def _json(r):
    try:
        return r.json()
    except Exception:
        return None


def _msg(body):
    if not isinstance(body, dict):
        return ""
    m = body.get("message") or body.get("error") or ""
    errs = body.get("errors")
    if isinstance(errs, dict):
        m = (m + " — " if m else "") + "; ".join(
            f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in errs.items())
    return str(m)[:400]


def _req(method, path, payload=None, params=None, _retry=True):
    """One API call. Returns the JSON body; raises SenditError with Sendit's
    own words when the call is refused."""
    r = requests.request(method, BASE + path.lstrip("/"), json=payload, params=params,
                         headers={"Authorization": f"Bearer {_token()}", "Accept": "application/json"},
                         timeout=_TIMEOUT)
    body = _json(r)
    if r.status_code in (401, 403) and _retry and "authentifi" in (_msg(body) or "").lower():
        frappe.cache().delete_value(_TOKEN)
        return _req(method, path, payload, params, _retry=False)
    if r.status_code >= 400 or (isinstance(body, dict) and body.get("success") is False):
        raise SenditError(f"Sendit {method} {path} → {r.status_code}: {_msg(body) or (r.text or '')[:300]}",
                          status=r.status_code)
    return body if body is not None else {}


# ── cities ────────────────────────────────────────────────────────────────

def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def sync_districts():
    """Every destination district, all pages, stored for the mapping."""
    out, page, seen = [], 1, set()
    while page < 200:
        body = _req("GET", "districts", params={"page": page})
        data = body.get("data")
        rows = data.get("data") if isinstance(data, dict) else data
        rows = rows or []
        # An API that ignores `page` would hand back page 1 for ever.
        if rows and str(rows[0].get("id")) in seen:
            break
        seen.update(str(d.get("id")) for d in rows)
        for d in rows:
            out.append({"id": int(d.get("id")), "ville": d.get("ville") or "", "name": d.get("name") or "",
                        "ar": d.get("arabic_name") or "", "price": d.get("price"), "delay": d.get("delais") or ""})
        last = (data.get("last_page") if isinstance(data, dict) else None) or (body.get("last_page"))
        if not rows or (last and page >= int(last)):
            break
        page += 1
    if out:
        _store_districts(out)
    return out


# The district list is hundreds of rows: a DefaultValue is TEXT (64 KB) and
# would truncate it. It lives in one private File, cached in redis.
_DFILE = "lp_sendit_districts.json"


def _store_districts(rows):
    content = json.dumps(rows, ensure_ascii=False)
    old = frappe.db.get_value("File", {"file_name": _DFILE, "attached_to_doctype": ["is", "not set"]}, "name")
    if old:
        frappe.delete_doc("File", old, ignore_permissions=True, force=True)
    frappe.get_doc({"doctype": "File", "file_name": _DFILE, "is_private": 1,
                    "content": content}).insert(ignore_permissions=True)
    frappe.cache().set_value(_DISTRICTS, content)
    frappe.db.commit()


def districts():
    raw = frappe.cache().get_value(_DISTRICTS)
    if not raw:
        name = frappe.db.get_value("File", {"file_name": _DFILE}, "name", order_by="creation desc")
        if name:
            try:
                raw = frappe.get_doc("File", name).get_content()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                frappe.cache().set_value(_DISTRICTS, raw)
            except Exception:
                raw = None
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


def pickup_cities():
    body = _req("GET", "districts/pickup-cities")
    rows = body.get("data") or []
    return [{"id": int(r.get("id")), "name": r.get("name") or "", "ar": r.get("arabic_name") or ""} for r in rows]


def district_for(city, overrides=None):
    """Our city -> (district id, label) or (None, None). A manual choice in the
    settings wins; then the district named like its city; then the city's
    first district. Our addresses carry the city only, never the quarter."""
    key = _norm(city)
    if not key:
        return None, None
    ov = (overrides or {}).get(key)
    if ov:
        d = next((x for x in districts() if x["id"] == int(ov)), None)
        return int(ov), (f"{d['ville']} / {d['name']}" if d else str(ov))
    same_city = [d for d in districts() if key in (_norm(d["ville"]), _norm(d["ar"]))]
    if not same_city:
        same_city = [d for d in districts() if _norm(d["name"]) == key]
    if not same_city:
        return None, None
    best = next((d for d in same_city if _norm(d["name"]) == _norm(d["ville"])), same_city[0])
    return best["id"], f"{best['ville']} / {best['name']}"


# ── parcels ───────────────────────────────────────────────────────────────

def _phone(p):
    d = re.sub(r"\D", "", str(p or ""))
    if d.startswith("212"):
        d = "0" + d[3:]
    elif len(d) == 9:
        d = "0" + d
    return d


def _amount(so, dn=None):
    """What the courier collects: the same arithmetic and the same two
    exceptions as the Cathedis label (overrides/cathedis.py) — a prepaid
    order collects nothing, and a remainder under 1 MAD (positive or, as
    on #266195, negative) is paid. The total is the Delivery Note's: after
    an edit (a line dropped at the wall) it is what is really in the box."""
    from logistics_portal.overrides.cathedis import PREPAID
    if (so.get("payment_type") or "") in PREPAID:
        return 0
    total = float((dn.grand_total if dn and dn.get("grand_total") else so.grand_total) or 0)
    amt = round(total - float(so.advance_paid or 0), 2)
    return 0 if amt < 1 else amt


def find_existing(so_name, phone):
    """A live Sendit parcel already carrying this order's reference. Sendit
    searches by code, name, phone or address — not by reference — so ask by
    phone and match the reference: the guard against a second parcel when
    an earlier call's answer was lost."""
    if not phone:
        return ""
    try:
        body = _req("GET", "deliveries", params={"querystring": phone})
    except Exception:
        return ""
    data = body.get("data")
    rows = data.get("data") if isinstance(data, dict) else (data or [])
    for d in rows or []:
        if str(d.get("reference") or "").strip() == so_name and \
                str(d.get("status") or "").upper() not in ("CANCELED",):
            return d.get("code") or ""
    return ""


def _items_note(dn):
    rows = []
    for it in dn.get("items") or []:
        sku = frappe.db.get_value("Item", it.item_code, "custom_sku") or it.item_code
        rows.append(f"{sku} x{int(it.qty or 0)}")
    return " | ".join(rows)[:480]


def _code_of(body):
    data = (body or {}).get("data")
    if isinstance(data, list):
        data = data[0] if data else {}
    if isinstance(data, dict):
        return data.get("code") or (data.get("delivery") or {}).get("code") or ""
    return ""


def create_for_delivery_note(dn, so_name, why=""):
    """Create the Sendit parcel for one Delivery Note and record it on the
    order and the note the way the Cathedis integration does."""
    from logistics_portal.api import carriers
    cfg = carriers.settings()["sendit"]
    so = frappe.get_doc("Sales Order", so_name)
    addr_name = dn.get("shipping_address_name") or so.get("shipping_address_name")
    addr = frappe.get_doc("Address", addr_name) if addr_name else None
    city = (addr.city if addr else "") or so.get("custom_shipping_city") or ""
    district_id, district_label = district_for(city, carriers.settings().get("city_map"))
    if not district_id:
        raise SenditError(f"City not served by Sendit / not mapped: {city or '—'}")
    if not cfg.get("pickup_district_id"):
        raise SenditError("Sendit pickup city is not set (Transporteurs settings).")
    address = ", ".join(x for x in [(addr.address_line1 if addr else ""), (addr.address_line2 if addr else "")] if x) \
        or (so.get("shipping_address") or "")
    phone = _phone((addr.phone if addr else "") or so.get("custom_customer_phone") or so.get("custom_shipping_phone")
                   or so.get("contact_phone"))
    payload = {
        "pickup_district_id": int(cfg["pickup_district_id"]),
        "district_id": int(district_id),
        "name": (so.customer_name or "")[:120],
        "amount": _amount(so),
        "address": frappe.utils.strip_html(address)[:250] or city,
        "phone": phone,
        "comment": _items_note(dn),
        "reference": so_name,
        "allow_open": int(cfg.get("allow_open", 1)),
        "allow_try": int(cfg.get("allow_try", 0)),
        "products_from_stock": 0,
    }
    payload["amount"] = _amount(so, dn)
    code = find_existing(so_name, phone)
    reused = bool(code)
    if not code:
        try:
            body = _req("POST", "deliveries", payload)
        except requests.RequestException as e:
            raise SenditAmbiguous(f"No answer from Sendit ({type(e).__name__}) — the parcel may exist") from e
        except SenditError as e:
            if e.status >= 500:
                raise SenditAmbiguous(str(e)) from e
            raise
        code = _code_of(body)
        if not code:
            raise SenditAmbiguous(f"Sendit answered without a parcel code: {json.dumps(body)[:300]}")

    # custom_tracking_number stays EMPTY for Sendit: codx's Cathedis resync
    # selects every order that has one, prefixes "LD00" and asks Cathedis —
    # a Sendit code there is a "Missing in Cathedis" row on every run.
    vals = {"custom_tracking_company": CARRIER, "custom_awb": code,
            "custom_track_shipment_status": "Pending"}
    label_url = ""
    try:
        label_url = attach_label(so_name, code)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], f"Sendit label {so_name} {code}")
    if label_url:
        vals["custom_label_url"] = label_url
    for doctype, name in (("Sales Order", so_name), ("Delivery Note", dn.name)):
        for k, v in vals.items():
            if frappe.db.has_column(doctype, k):
                frappe.db.set_value(doctype, name, k, v, update_modified=False)
    frappe.db.sql("""UPDATE `tabSales Order` SET custom_logistics_status = 'Label Generated'
                     WHERE name = %s AND COALESCE(custom_logistics_status, '') IN ('', 'Pending', 'Picked')""",
                  (so_name,))
    _comment(so_name, f"Sendit parcel {code} {'found again' if reused else 'created'} — {district_label}, "
                      f"COD {payload['amount']} MAD" + (f" · {why}" if why else ""), owner=None)
    frappe.db.commit()
    return {"code": code, "district": district_label, "amount": payload["amount"], "label": bool(label_url)}


def attach_label(so_name, code):
    """Fetch the parcel's label (thermal 10x10 unless set to A4) and attach it
    to the order, where label_pdf / has_label look first."""
    from logistics_portal.api import carriers
    fmt = int(carriers.settings()["sendit"].get("label_format", 1))
    body = _req("POST", "deliveries/getlabels", {"codesToPrint": code, "printFormat": fmt})
    url = ((body.get("data") or {}).get("fileUrl")) or ""
    if not url:
        raise SenditError(f"No label URL for {code}")
    r = requests.get(url, timeout=_TIMEOUT)
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        raise SenditError(f"Label download failed for {code} ({r.status_code})")
    frappe.get_doc({"doctype": "File", "file_name": f"Sendit_Label_{code}.pdf", "is_private": 1,
                    "attached_to_doctype": "Sales Order", "attached_to_name": so_name,
                    "content": r.content}).insert(ignore_permissions=True)
    return url


def cancel(code):
    return _req("DELETE", f"deliveries/{code}")


def detail(code):
    body = _req("GET", f"deliveries/{code}")
    return body.get("data") or {}


def request_pickup(codes, note=""):
    from logistics_portal.api import carriers
    cfg = carriers.settings()["sendit"]
    payload = {"district_id": int(cfg["pickup_district_id"]), "name": cfg.get("pickup_name") or "Justyol",
               "phone": _phone(cfg.get("pickup_phone")), "address": cfg.get("pickup_address") or "",
               "note": note or "Justyol", "deliveries": ",".join(codes)}
    body = _req("POST", "pickups", payload)
    data = body.get("data") or {}
    return (data.get("code") if isinstance(data, dict) else "") or ""


# ── statuses ──────────────────────────────────────────────────────────────
#
# Sendit status -> (custom_track_shipment_status, custom_logistics_status or
# None to leave it, the comment in carrier_events' own vocabulary). The
# track values are the ones Cathedis already writes (measured 2026-10-27),
# so every board groups a Sendit parcel with its Cathedis twin.
STATUS = {
    "PENDING": ("Pending", None, None),
    "TO_PREPARE": ("Pending", None, None),
    "TO_PICKUP": ("Pending", None, None),
    "NEW_DESTINATION": ("Delivery Exception", None, "The parcel needs a new destination (Sendit: À changer)"),
    "PICKEDUP": ("Picked up", "Shipped", "Picked up by SENDIT"),
    "WAREHOUSE": ("In Transit", "Shipped", "The parcel is present on Sendit hub"),
    "TRANSIT": ("In Transit", "Shipped", "Shipped to destination hub (Sendit)"),
    "DISTRIBUTED": ("In Transit", "Shipped", "Shipped to destination hub (Sendit: Distribué)"),
    "DELIVERING": ("Out For Delivery", "Shipped", "Out for delivery (Sendit)"),
    "UNREACHABLE": ("Failed Attempt", "Shipped", "Customer unreachable (Sendit)"),
    "POSTPONED": ("Failed Attempt", "Shipped", "The driver has postponed the delivery (Sendit: Reporté)"),
    "DELIVERED": ("Delivered", "Delivered", "Package Delivered (Sendit)"),
    "CANCELED": ("Delivery Exception", None, "Cancellation Reason: Sendit — Annulé"),
    "REJECTED": ("Delivery Exception", None, "The customer has cancelled the order on the spot (Sendit: Refusé)"),
}
_FINAL = ("Delivered", "Returned", "Not Delivered")


def _comment(so_name, text, owner=COMMENT_USER):
    try:
        c = frappe.get_doc({"doctype": "Comment", "comment_type": "Comment",
                            "reference_doctype": "Sales Order", "reference_name": so_name,
                            "content": text})
        c.insert(ignore_permissions=True)
        if owner:
            # insert() stamps the session user (Guest, for a webhook); the
            # carrier's comments are read by owner, as Cathedis's are.
            frappe.db.set_value("Comment", c.name, {"owner": owner, "comment_email": owner},
                                update_modified=False)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:1500], f"Sendit comment {so_name}")


def apply_status(code, status, message="", at="", extra=None):
    """One status for one parcel. Idempotent: the same status twice writes
    nothing the second time."""
    status = (status or "").upper().strip()
    so_name = frappe.db.get_value("Sales Order", {"custom_awb": code, "docstatus": 1}, "name")
    if not so_name or status not in STATUS:
        return {"ok": False, "reason": "unknown_parcel" if not so_name else "unknown_status", "code": code}
    trk, ls, sentence = STATUS[status]
    cur = frappe.db.get_value("Sales Order", so_name, ["custom_track_shipment_status", "custom_logistics_status"],
                              as_dict=True) or {}
    last = frappe.cache().get_value(f"lp_sendit_last:{code}")
    if last == status and cur.get("custom_track_shipment_status") == trk:
        return {"ok": True, "order": so_name, "unchanged": True}
    frappe.db.set_value("Sales Order", so_name, "custom_track_shipment_status", trk, update_modified=True)
    dns = frappe.db.sql_list("""SELECT DISTINCT dn.name FROM `tabDelivery Note` dn
                                JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
                                WHERE dni.against_sales_order = %s AND dn.docstatus = 1 AND dn.is_return = 0""",
                             (so_name,))
    for dn in dns:
        if frappe.db.has_column("Delivery Note", "custom_track_shipment_status"):
            frappe.db.set_value("Delivery Note", dn, "custom_track_shipment_status", trk, update_modified=False)
    if ls and (cur.get("custom_logistics_status") or "") not in _FINAL:
        frappe.db.set_value("Sales Order", so_name, "custom_logistics_status", ls, update_modified=False)
    if sentence:
        detail_txt = " — ".join(x for x in [message, (extra or {}).get("deliverBy") and f"next try {extra['deliverBy']}"] if x)
        _comment(so_name, sentence + (f": {detail_txt}" if detail_txt else ""))
    frappe.cache().set_value(f"lp_sendit_last:{code}", status, expires_in_sec=30 * 86400)
    frappe.db.commit()
    return {"ok": True, "order": so_name, "status": status, "track": trk}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook():
    """Sendit → us, on every status change. Verified before anything is read."""
    import base64
    raw = frappe.request.get_data() or b""
    sig = (frappe.request.headers.get("X-Sendit-Signature") or "").strip()
    if sig.lower().startswith("sha256="):
        sig = sig[7:]
    pub, sec = keys()
    good = []
    for k in (sec, pub):
        if k:
            mac = hmac.new(k.encode(), raw, hashlib.sha256)
            good += [mac.hexdigest(), base64.b64encode(mac.digest()).decode()]
    if not sig or not any(hmac.compare_digest(sig.lower() if len(sig) == 64 else sig, g) for g in good):
        frappe.log_error(f"bad signature · {len(raw)} bytes · {raw[:300]!r}", "Sendit webhook rejected")
        frappe.local.response.http_status_code = 401
        return {"ok": False}
    # Verified: from here the request acts for the integration, not as Guest.
    frappe.set_user("Administrator")
    try:
        p = json.loads(raw.decode("utf-8"))
    except Exception:
        frappe.local.response.http_status_code = 400
        return {"ok": False}
    if (p.get("event") or "") != "delivery.status.update":
        return {"ok": True, "ignored": p.get("event")}
    return apply_status(p.get("code") or "", p.get("newStatus") or "", p.get("message") or "",
                        p.get("lastActionAt") or "", extra=p)


def pull_sync(limit=150):
    """The pull behind the webhook (scheduler): open Sendit parcels of the last
    30 days, asked one by one, oldest news first."""
    from logistics_portal.api import carriers
    if carriers.settings()["sendit"].get("mode", "off") == "off" or not has_keys():
        return
    rows = frappe.db.sql("""SELECT name, custom_awb FROM `tabSales Order`
                            WHERE custom_tracking_company = %s AND COALESCE(custom_awb, '') <> ''
                              AND COALESCE(custom_logistics_status, '') NOT IN ('Delivered', 'Returned', 'Not Delivered')
                              AND creation >= DATE_SUB(%s, INTERVAL 30 DAY)
                            ORDER BY modified LIMIT %s""",
                         (CARRIER, str(now_datetime())[:10], int(limit)), as_dict=True)
    for r in rows:
        try:
            d = detail(r.custom_awb)
            st = d.get("status") or d.get("statut") or ""
            if st:
                apply_status(r.custom_awb, st, d.get("last_message") or "", d.get("last_action_at") or "")
        except Exception:
            frappe.log_error(frappe.get_traceback()[:1500], f"Sendit pull {r.name}")
