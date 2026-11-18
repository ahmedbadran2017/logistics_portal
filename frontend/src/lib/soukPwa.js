// The souk app as an installed phone app: the service worker (served by
// logistics_portal.api.souk_pwa.sw, scope /souk/) and the install prompt.
//
// Android Chrome hands us `beforeinstallprompt`: we keep it and show our own
// "Install" button in the shell. iOS Safari has no prompt — the button then
// opens a two-line hint (Share → Add to Home Screen). Once installed (or the
// buyer said "not now" twice) the button goes away.

import { reactive } from "vue";

const SW_URL = "/api/method/logistics_portal.api.souk_pwa.sw";
const DISMISS_KEY = "lp_souk_install_dismissed";

export const pwa = reactive({
  canInstall: false,      // Android: a deferred prompt is waiting
  ios: false,             // iOS Safari, not installed: show the hint instead
  installed: false,       // running as the installed app
  updated: false,         // a new version took over: reload when convenient
});

let deferred = null;

function standalone() {
  try {
    return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  } catch (_) { return false; }
}

function dismissed() {
  try { return Number(localStorage.getItem(DISMISS_KEY) || 0) >= 2; } catch (_) { return false; }
}

export function dismissInstall() {
  try { localStorage.setItem(DISMISS_KEY, String(Number(localStorage.getItem(DISMISS_KEY) || 0) + 1)); } catch (_) { /* private */ }
  pwa.canInstall = false;
  pwa.ios = false;
}

export async function install() {
  if (!deferred) return false;
  deferred.prompt();
  const choice = await deferred.userChoice.catch(() => null);
  deferred = null;
  pwa.canInstall = false;
  return !!(choice && choice.outcome === "accepted");
}

export function startPwa() {
  if (typeof window === "undefined") return;
  pwa.installed = standalone();
  document.documentElement.dataset.standalone = pwa.installed ? "1" : "0";

  const ua = navigator.userAgent || "";
  const isIOS = /iPhone|iPad|iPod/.test(ua) && !/CriOS|FxiOS/.test(ua);
  if (isIOS && !pwa.installed && !dismissed()) pwa.ios = true;

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferred = e;
    if (!pwa.installed && !dismissed()) pwa.canInstall = true;
  });
  window.addEventListener("appinstalled", () => {
    pwa.installed = true;
    pwa.canInstall = false;
    deferred = null;
  });

  if ("serviceWorker" in navigator && location.pathname.startsWith("/souk")) {
    const hadController = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      // A deploy shipped a new worker. Not mid-purchase: say so, the buyer reloads.
      if (hadController) pwa.updated = true;
    });
    const reg = () => navigator.serviceWorker.register(SW_URL, { scope: "/souk/" }).catch(() => { /* old browser / blocked */ });
    if (document.readyState === "complete") reg();
    else window.addEventListener("load", reg);
  }
}

/** On logout: forget the cached screens (another person may use the phone). */
export function forgetOffline() {
  try {
    if (navigator.serviceWorker && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage("souk-logout");
    }
    if (window.caches) caches.delete("souk-api-v1");
  } catch (_) { /* nothing cached */ }
}

/** A short buzz on the phone for "done" / "refused" (Android only). */
export function buzz(kind = "ok") {
  try { navigator.vibrate && navigator.vibrate(kind === "ok" ? 18 : [30, 60, 30]); } catch (_) { /* no motor */ }
}
