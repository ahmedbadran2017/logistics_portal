/**
 * Minimal Frappe RPC client (replaces frappe-ui's `call`, whose barrel pulls a
 * heavy TextEditor graph we don't use). Whitelisted methods live under
 * `logistics_portal.api.*`.
 *
 * READS go over GET: Frappe does not require a CSRF token for GET requests, so
 * the portal works regardless of how the page boot injects the token (the
 * sandboxed Jinja can't expose the session token reliably). The same-origin
 * session cookie authenticates the call. WRITES use POST + CSRF via `post()`.
 */
function csrf() {
  return window.csrf_token || (window.frappe_boot && window.frappe_boot.csrf_token) || "";
}

/** Build an Error carrying the server's human message (Frappe packs it into
 *  `_server_messages` / `exception`), falling back to "method → status". */
async function serverError(method, res) {
  let msg = `${method} → ${res.status}`;
  try {
    const body = await res.json();
    const sm = body._server_messages ? JSON.parse(body._server_messages) : null;
    const first = sm && sm.length ? JSON.parse(sm[0]) : null;
    if (first && first.message) {
      msg = String(first.message).replace(/<[^>]+>/g, "").trim() || msg;
    } else if (body.exception) {
      // "frappe.exceptions.XError: the message" → keep the message part.
      msg = String(body.exception).split(/Error:|Exception:/).pop().trim() || msg;
    }
  } catch (_) { /* keep the generic message */ }
  return new Error(msg);
}

export async function call(method, args = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(args || {})) {
    if (v === undefined || v === null) continue;
    qs.set(k, typeof v === "object" ? JSON.stringify(v) : String(v));
  }
  const q = qs.toString();
  const res = await fetch(`/api/method/${method}${q ? `?${q}` : ""}`, {
    method: "GET",
    headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
  });
  if (!res.ok) throw await serverError(method, res);
  const data = await res.json();
  return data.message; // Frappe wraps the return value in `message`
}

/** State-changing calls (POST + CSRF token). */
export async function post(method, args = {}) {
  const res = await fetch(`/api/method/${method}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": csrf(),
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify(args),
  });
  if (!res.ok) throw await serverError(method, res);
  const data = await res.json();
  return data.message;
}

/** Read a whitelisted portal method over GET: api('performance.cockpit'). */
export function api(method, args = {}) {
  return call(`logistics_portal.api.${method}`, args);
}

/** Invoke a state-changing portal method over POST: apiPost('picking.complete_pick', {order}). */
export function apiPost(method, args = {}) {
  return post(`logistics_portal.api.${method}`, args);
}

/**
 * Await a live API call; on failure or empty result return the empty shape of
 * `fallback` (array → [], object → null). NO demo substitution, ever — pages
 * render skeletons while loading and honest empty/error states after. The
 * first param is kept for its SHAPE only (legacy callers pass demo consts).
 */
function emptyLike(shape) {
  if (Array.isArray(shape)) return [];
  return shape && typeof shape === "object" ? null : shape;
}

export async function liveOr(fallback, promiseOrFn) {
  try {
    const p = typeof promiseOrFn === "function" ? promiseOrFn() : promiseOrFn;
    const res = await p;
    if (res == null) return emptyLike(fallback);
    if (typeof res === "object" && !Array.isArray(res) && Object.keys(res).length === 0)
      return emptyLike(fallback);
    return res;
  } catch (e) {
    console.warn("liveOr: live call failed", e);
    return emptyLike(fallback);
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
