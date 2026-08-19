"""Catalog Hub — Phase A: real-time Shopify -> ERPNext status mirror.

The Phase 0 status sync was a button someone had to press; between presses Next
drifted from Shopify (a product archived on Shopify still looked ACTIVE here,
stranding its stock). Phase A makes the mirror live: Shopify calls us the moment
a product changes.

  shopify_product_webhook  the HMAC-verified receiver for products/create,
                           products/update, products/delete. The webhook payload
                           already carries the product status and its live
                           variant ids, so we write straight to Next with no
                           call back to Shopify.
  ensure_webhooks          register those three topics against this site's
                           endpoint (idempotent — skips topics already pointed
                           here). Manager only.
  sync_health              what the dashboard reads: last webhook, last sweep,
                           and the current status breakdown.

The scheduled `sync.reconcile_sweep` is the safety net: a dropped or out-of-order
webhook can never leave Next silently behind, because the sweep re-pulls and
rewrites drift every hour.

Direction is deliberately ONE WAY here — Shopify catalog/status flows IN. Stock
is the opposite direction (Next is the source of physical truth) and is Phase B;
this module must never write stock, into Next or out to Shopify.
"""

import base64
import hashlib
import hmac
import json

import frappe

from logistics_portal.api.catalog_hub import sync

# Shopify REST product.status -> our stored status. products/delete has no
# status field; the topic itself means DELETED.
_STATUS_MAP = {"active": "ACTIVE", "archived": "ARCHIVED", "draft": "DRAFT"}

# The topics we own. ecommerce_integrations may subscribe to its own topics for
# order/item sync; Shopify allows several subscriptions per topic to different
# URLs, so ours live alongside without collision.
_TOPICS = ("PRODUCTS_CREATE", "PRODUCTS_UPDATE", "PRODUCTS_DELETE")

_WEBHOOK_METHOD = "logistics_portal.api.catalog_hub.webhook.shopify_product_webhook"


def _shared_secret():
    """The Shopify app secret that signs webhooks (the same `shared_secret` the
    ecommerce_integrations Shopify Setting stores)."""
    from ecommerce_integrations.shopify.constants import SETTING_DOCTYPE
    return (frappe.db.get_single_value(SETTING_DOCTYPE, "shared_secret") or "").strip()


def _shop_host():
    from ecommerce_integrations.shopify.constants import SETTING_DOCTYPE
    url = frappe.db.get_single_value(SETTING_DOCTYPE, "shopify_url") or ""
    return url.replace("https://", "").replace("http://", "").strip("/").lower()


def _verify(raw_body, given_hmac):
    """Constant-time check that the body was signed by our Shopify app secret."""
    secret = _shared_secret()
    if not secret or not given_hmac:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, given_hmac)


def _reject(code=401):
    frappe.local.response["http_status_code"] = code
    return {"ok": False}


@frappe.whitelist(allow_guest=True)
def shopify_product_webhook():
    """Receive one Shopify product webhook and mirror its status into Next.

    Guest endpoint: authentication IS the HMAC signature, not a login. Anything
    that fails the signature (or comes from another shop) is rejected before we
    read a single field. Processing errors still return 200 so Shopify does not
    hammer us with retries — the hourly reconcile sweep is the backstop for a
    genuinely missed event."""
    raw = frappe.request.get_data() if frappe.request else b""
    given = frappe.get_request_header("X-Shopify-Hmac-Sha256")
    if not _verify(raw, given):
        return _reject(401)

    # Defence in depth: only our own shop may post here.
    shop = (frappe.get_request_header("X-Shopify-Shop-Domain") or "").lower()
    host = _shop_host()
    if host and shop and shop != host:
        return _reject(401)

    topic = (frappe.get_request_header("X-Shopify-Topic") or "").lower()
    try:
        payload = json.loads(raw or b"{}")
    except Exception:
        return _reject(400)

    try:
        _apply(topic, payload)
        frappe.cache().set_value("lp_catalog_last_webhook", frappe.utils.now())
    except Exception:
        # Never make Shopify retry on our bug — the sweep will reconcile it.
        frappe.log_error(frappe.get_traceback(), "catalog_hub.webhook")
    return {"ok": True}


def _apply(topic, payload):
    """Translate one product webhook into a status write. Unknown topics no-op."""
    pid = payload.get("id")
    if not pid:
        return

    if topic == "products/delete":
        sync.write_product_status(pid, "DELETED", set())
        return

    if topic in ("products/update", "products/create"):
        status = _STATUS_MAP.get((payload.get("status") or "").lower(), "UNMAPPED")
        live_ids = {str(v.get("id")) for v in (payload.get("variants") or []) if v.get("id")}
        sync.write_product_status(pid, status, live_ids)


@frappe.whitelist()
def ensure_webhooks():
    """Register products/create|update|delete against this site's endpoint, once.
    Idempotent: any topic already pointing at our callback is left alone. Manager
    only. Returns what it created vs. what was already there."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can register catalog webhooks.", frappe.PermissionError)

    callback = frappe.utils.get_url() + "/api/method/" + _WEBHOOK_METHOD
    if not callback.lower().startswith("https://"):
        frappe.throw("Shopify requires an HTTPS callback; this site is not on HTTPS.")

    existing = sync.shopify_graphql(
        """query { webhookSubscriptions(first: 100) { nodes {
             topic endpoint { __typename ... on WebhookHttpEndpoint { callbackUrl } } } } }""")
    have = set()
    for n in (((existing.get("data") or {}).get("webhookSubscriptions") or {}).get("nodes") or []):
        ep = n.get("endpoint") or {}
        if ep.get("callbackUrl") == callback:
            have.add(n.get("topic"))

    created, errors = [], []
    mutation = """mutation($topic: WebhookSubscriptionTopic!, $url: URL!) {
      webhookSubscriptionCreate(topic: $topic,
        webhookSubscription: {callbackUrl: $url, format: JSON}) {
        webhookSubscription { id } userErrors { field message } } }"""
    for topic in _TOPICS:
        if topic in have:
            continue
        res = sync.shopify_graphql(mutation, {"topic": topic, "url": callback})
        node = ((res.get("data") or {}).get("webhookSubscriptionCreate") or {})
        errs = node.get("userErrors") or []
        if errs:
            errors.append({"topic": topic, "errors": errs})
        else:
            created.append(topic)

    return {"callback": callback, "created": created,
            "alreadyRegistered": sorted(have), "errors": errors}


@frappe.whitelist()
def sync_health():
    """Dashboard headline: is the live mirror actually alive, and how does the
    catalog break down by Shopify status right now."""
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can view catalog sync health.", frappe.PermissionError)

    rows = frappe.db.sql(
        """SELECT COALESCE(NULLIF(custom_shopify_status, ''), 'UNSYNCED') status,
                  COUNT(*) n
           FROM `tabItem`
           WHERE custom_shopify_synced_on IS NOT NULL
           GROUP BY status""", as_dict=True)
    by_status = {r.status: int(r.n) for r in rows}
    last_syncd = frappe.db.sql(
        "SELECT MAX(custom_shopify_synced_on) FROM `tabItem`")[0][0]
    return {
        "lastWebhook": frappe.cache().get_value("lp_catalog_last_webhook"),
        "lastSweep": frappe.cache().get_value("lp_catalog_last_sweep"),
        "lastWrite": str(last_syncd)[:19] if last_syncd else None,
        "byStatus": by_status,
        "serverNow": str(frappe.utils.now_datetime())[:19],
    }
