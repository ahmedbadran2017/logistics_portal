"""The souk app's service worker — what makes /souk a real phone app.

Why a server method and not a file: Frappe serves no .js from www/ (its
static-page renderer refuses css/js/json/txt), and a worker served from
/assets/... could only control /assets/. So the worker comes from this
method, and `after_request` below adds `Service-Worker-Allowed: /souk/` so
it may control the app's pages from here.

What it does (the buyer is in Derb Omar, the line comes and goes):
* the app's page: network first (a deploy is picked up at once), the last
  good copy when there is no line — the app still opens;
* the built bundles (/assets/logistics_portal/dist/…, hashed names) and the
  fonts: cache first — a hashed file never changes;
* photos (/files/…): cache first, bounded;
* the screens the buyer needs offline — boot, buy, custody, board — the last
  answer when the network fails. Every other API call goes straight to the
  network: writes are the outbox's job (lib/soukOutbox.js), never the cache's.
Logging out wipes the cached answers (the shell posts 'souk-logout').
"""

import frappe

SW_PATH = "/api/method/logistics_portal.api.souk_pwa.sw"

_SW = r"""
const VERSION = "__VERSION__";
const SHELL = "souk-shell-" + VERSION;
const ASSETS = "souk-assets-v1";
const FILES = "souk-files-v1";
const API = "souk-api-v1";
const KEEP = [SHELL, ASSETS, FILES, API];
const OFFLINE_API = [
  "logistics_portal.api.auth.get_boot",
  "logistics_portal.api.souk.buy_boot",
  "logistics_portal.api.souk.trips_boot",
  "logistics_portal.api.souk.board",
];

self.addEventListener("install", (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(SHELL).then((c) => c.add(new Request("/souk/home", { credentials: "include" })).catch(() => {})));
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith("souk-") && !KEEP.includes(k)) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener("message", (e) => {
  if (e.data === "souk-logout") e.waitUntil(caches.delete(API));
});

function timeout(ms) { return new Promise((_, ko) => setTimeout(() => ko(new Error("timeout")), ms)); }

async function trim(cacheName, max) {
  const c = await caches.open(cacheName);
  const keys = await c.keys();
  for (let i = 0; i < keys.length - max; i++) await c.delete(keys[i]);
}

async function networkFirst(req, cacheName, ms, fallbackUrl) {
  const c = await caches.open(cacheName);
  try {
    const res = await Promise.race([fetch(req), timeout(ms)]);
    if (res && res.ok) c.put(fallbackUrl || req, res.clone());
    return res;
  } catch (err) {
    const hit = await c.match(fallbackUrl || req, { ignoreSearch: !!fallbackUrl });
    if (hit) return hit;
    throw err;
  }
}

async function cacheFirst(req, cacheName, max) {
  const c = await caches.open(cacheName);
  const hit = await c.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res && (res.ok || res.type === "opaque")) {
    c.put(req, res.clone());
    if (max) trim(cacheName, max);
  }
  return res;
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (req.mode === "navigate" && url.origin === location.origin && url.pathname.startsWith("/souk")) {
    // One page serves every /souk route: keep the last good copy of it.
    e.respondWith(networkFirst(req, SHELL, 6000, "/souk/home"));
    return;
  }
  if (url.origin === location.origin && url.pathname.startsWith("/assets/")) {
    // Hashed build output never changes; the rest (manifest, icons) may.
    e.respondWith(url.pathname.includes("/dist/") ? cacheFirst(req, ASSETS, 120)
                                                  : networkFirst(req, ASSETS, 4000));
    return;
  }
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    e.respondWith(cacheFirst(req, ASSETS, 120));
    return;
  }
  if (url.origin === location.origin && url.pathname.startsWith("/files/")) {
    e.respondWith(cacheFirst(req, FILES, 400));
    return;
  }
  if (url.origin === location.origin && url.pathname.startsWith("/api/method/")) {
    const m = url.pathname.slice("/api/method/".length);
    if (OFFLINE_API.includes(m)) e.respondWith(networkFirst(req, API, 8000));
  }
});
"""


def _version():
    try:
        from frappe.utils import get_build_version
        return str(get_build_version())
    except Exception:
        return frappe.utils.now_datetime().strftime("%Y%m%d")


@frappe.whitelist(allow_guest=True, methods=["GET"])
def sw():
    """The worker script itself (no secrets in it: guests may fetch it)."""
    frappe.response["type"] = "download"
    frappe.response["filename"] = "souk-sw.js"
    frappe.response["content_type"] = "application/javascript"
    frappe.response["display_content_as"] = "inline"
    frappe.response["filecontent"] = _SW.replace("__VERSION__", _version())


def after_request(response=None, request=None):
    """Lets the worker above control /souk/ (hooks.after_request)."""
    try:
        if request is not None and request.path == SW_PATH and response is not None:
            response.headers["Service-Worker-Allowed"] = "/souk/"
            response.headers["Cache-Control"] = "no-cache"
    except Exception:
        pass
