/**
 * Minimal Frappe RPC client (replaces frappe-ui's `call`, whose barrel pulls a
 * heavy TextEditor graph we don't use). Whitelisted methods live under
 * `logistics_portal.api.*`. Reads the CSRF token injected by the SPA page boot.
 */
function csrf() {
  return window.csrf_token || (window.frappe_boot && window.frappe_boot.csrf_token) || "";
}

export async function call(method, args = {}) {
  const res = await fetch(`/api/method/${method}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": csrf(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify(args),
  });
  if (!res.ok) throw new Error(`${method} → ${res.status}`);
  const data = await res.json();
  return data.message; // Frappe wraps the return value in `message`
}

/** Invoke a whitelisted portal method: api('picking.my_queue', {user}). */
export function api(method, args = {}) {
  return call(`logistics_portal.api.${method}`, args);
}

/**
 * Live-or-demo: await a real API call and return its result when it yields
 * usable data; otherwise fall back to `demo`. Screens wire live data by passing
 * the api() promise + their handoffData fallback, so they render real numbers
 * once the app is installed and degrade gracefully in preview / before go-live.
 */
export async function liveOr(demo, promiseOrFn) {
  try {
    const p = typeof promiseOrFn === "function" ? promiseOrFn() : promiseOrFn;
    const res = await p;
    if (res == null) return demo;
    if (Array.isArray(res)) return res.length ? res : demo;
    if (typeof res === "object" && Object.keys(res).length === 0) return demo;
    return res;
  } catch (_) {
    return demo;
  }
}

/** Format an integer amount as MAD with thousands separators, 0 decimals. */
export function mad(value) {
  const n = Number(value || 0);
  return `MAD ${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

/** Compact count formatter (1240 -> "1,240"). */
export function num(value) {
  return Number(value || 0).toLocaleString("en-US");
}
