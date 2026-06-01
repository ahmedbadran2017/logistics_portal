// Thin wrappers around Frappe APIs (cookie-auth, CSRF, JSON only).

// Centralized company — single source of truth (fixes audit H5).
// Allow override via `window.logistics_portal_company` injected by the Jinja template.
export const COMPANY = (typeof window !== "undefined" && window.logistics_portal_company) || "Justyol Morocco";

// User roles — populated by the Jinja shell. Used for client-side role gating UX.
// Server-side enforcement still happens in every whitelisted method.
export function getUserRoles() {
  return (typeof window !== "undefined" && Array.isArray(window.user_roles)) ? window.user_roles : [];
}
export function hasRole(...roles) {
  const have = new Set(getUserRoles());
  if (have.has("Administrator") || have.has("System Manager")) return true;
  return roles.some((r) => have.has(r));
}
export function isApprover() {
  return hasRole("Purchase Manager", "Purchasing Portal Admin");
}

// Strict allow-list for order_by clauses (fixes audit H6).
// Format: "<field> asc|desc", commas allowed.
const ORDER_BY_RE = /^([a-zA-Z_][a-zA-Z0-9_]*)(\s+(asc|desc))?(\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)(\s+(asc|desc))?)*$/i;
function safeOrderBy(s) {
  if (!s) return "creation desc";
  if (ORDER_BY_RE.test(s.trim())) return s;
  console.warn(`[useApi] safeOrderBy: rejected "${s}", falling back to "creation desc"`);
  return "creation desc";
}

function getCsrf() {
  if (typeof window !== "undefined" && window.csrf_token) return window.csrf_token;
  const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  // Return empty string if no token — Frappe will respond with a clear 403 instead of
  // accepting the bogus literal "token".
  return m ? decodeURIComponent(m[1]) : "";
}

// HTML-escape user-supplied text before embedding in a toast HTML body.
export function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Frappe wraps each server message as a JSON string inside a JSON-array string.
// Convert: '["{\\"message\\":\\"foo\\"}"]' → 'foo'  (fixes audit M5)
export function parseServerMessages(raw) {
  if (!raw) return "";
  try {
    const arr = typeof raw === "string" ? JSON.parse(raw) : raw;
    if (!Array.isArray(arr)) return String(raw);
    return arr.map((m) => {
      if (m && typeof m === "object") return m.message || JSON.stringify(m);
      try { return JSON.parse(m).message || m; } catch { return m; }
    }).join(" · ");
  } catch {
    return String(raw);
  }
}

export async function runQueryReport(reportName, filters = {}) {
  // GET keeps things simple (no CSRF needed for read-only call) and works in dev mode
  // even when window.csrf_token isn't injected. If a filter payload ever balloons past
  // ~4KB we transparently fall back to POST.
  const filterStr = JSON.stringify(filters);
  const getUrl =
    "/api/method/frappe.desk.query_report.run" +
    "?report_name=" + encodeURIComponent(reportName) +
    "&filters=" + encodeURIComponent(filterStr);

  let resp;
  // 2000-byte safety margin: some proxies / older nginx setups cap URLs around 2-4KB.
  if (getUrl.length < 2000) {
    resp = await fetch(getUrl, {
      credentials: "include",
      headers: { Accept: "application/json" },
    });
  } else {
    resp = await fetch("/api/method/frappe.desk.query_report.run", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-Frappe-CSRF-Token": getCsrf(),
        Accept: "application/json",
      },
      body: JSON.stringify({ report_name: reportName, filters }),
    });
  }
  if (!resp.ok) {
    let body = "";
    try { body = await resp.text(); } catch {}
    throw new Error("HTTP " + resp.status + (body ? " — " + body.slice(0, 200) : ""));
  }
  const j = await resp.json();
  return (j.message || {});
}

export async function getList(doctype, opts = {}) {
  const params = new URLSearchParams({
    doctype,
    fields: JSON.stringify(opts.fields || ["name"]),
    filters: JSON.stringify(opts.filters || []),
    limit_page_length: String(opts.limit || 50),
    order_by: safeOrderBy(opts.order_by),
  });
  const url = "/api/method/frappe.client.get_list?" + params.toString();
  const resp = await fetch(url, { credentials: "include", headers: { Accept: "application/json" } });
  if (!resp.ok) throw new Error("HTTP " + resp.status);
  const j = await resp.json();
  return j.message || [];
}

// Upload a file to Frappe's /api/method/upload_file endpoint.
// Returns the saved File doc with a `file_url` we can pass to other API calls.
export async function uploadFile(file, { doctype, docname } = {}) {
  const form = new FormData();
  form.append("file", file, file.name);
  if (doctype) form.append("doctype", doctype);
  if (docname) form.append("docname", docname);
  form.append("is_private", "0");
  const resp = await fetch("/api/method/upload_file", {
    method: "POST",
    credentials: "include",
    headers: { "X-Frappe-CSRF-Token": getCsrf() },
    body: form,
  });
  let j = {};
  try { j = await resp.json(); } catch {}
  if (!resp.ok || j.exc) {
    const msg = parseServerMessages(j._server_messages) || j.exc || ("HTTP " + resp.status);
    throw new Error(msg);
  }
  return j.message; // { file_url, file_name, ... }
}

// Generic POST to a whitelisted Frappe method. Handles CSRF + _server_messages parsing.
export async function callMethod(method, args = {}) {
  const resp = await fetch("/api/method/" + method, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": getCsrf(),
      Accept: "application/json",
    },
    body: JSON.stringify(args),
  });
  let j = {};
  try { j = await resp.json(); } catch {}
  if (!resp.ok || j.exc) {
    const msg = parseServerMessages(j._server_messages) || j.exc || ("HTTP " + resp.status);
    throw new Error(msg);
  }
  return j.message;
}

export async function insertDoc(doc) {
  // JSON content-type — cleaner and avoids encodeURIComponent double-decoding pitfalls (fixes audit M7).
  const resp = await fetch("/api/method/frappe.client.insert", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Frappe-CSRF-Token": getCsrf(),
      Accept: "application/json",
    },
    body: JSON.stringify({ doc }),
  });
  let j = {};
  try { j = await resp.json(); } catch {}
  if (!resp.ok || j.exc) {
    const msg = parseServerMessages(j._server_messages) || j.exc || ("HTTP " + resp.status);
    throw new Error(msg);
  }
  return j.message;
}

export function money(n) {
  if (n === null || n === undefined || isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 }) + " MAD";
}

export function num(n, d = 0) {
  if (n === null || n === undefined) return "—";
  const v = Number(n);
  if (isNaN(v)) return "—";
  return v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
}

// Centralized tone map for actions (fixes audit L1).
export const ACTION_TONES = {
  OOS:       { color: "#f43f5e", label: "Out of stock", pill: "red"    },
  REORDER:   { color: "#f59e0b", label: "Reorder now",  pill: "yellow" },
  WATCH:     { color: "#fcd34d", label: "Watch",        pill: "yellow" },
  HEALTHY:   { color: "#10b981", label: "Healthy",      pill: "green"  },
  OVERSTOCK: { color: "#0ea5e9", label: "Overstocked",  pill: "blue"   },
  DEAD:      { color: "#8b5cf6", label: "Dead stock",   pill: "violet" },
};
export function actionColor(a) { return (ACTION_TONES[a] && ACTION_TONES[a].color) || "#a8a29e"; }
export function actionPill(a)  { return (ACTION_TONES[a] && ACTION_TONES[a].pill)  || "gray"; }

// Parse a "YYYY-MM-DD" string as local midnight (avoids UTC off-by-one).
// If the string contains a time component or a 'Z' it's already an absolute
// timestamp — fall through to the native Date parser to preserve UTC semantics.
export function parseLocalDate(s) {
  if (!s) return null;
  if (s instanceof Date) return s;
  const str = String(s);
  if (str.includes("T") || str.endsWith("Z")) return new Date(str);
  const m = str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return new Date(str);
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

// Format a Date or "YYYY-MM-DD" string as a local "YYYY-MM-DD" — safe across
// timezones, unlike `.toISOString().slice(0,10)` which is UTC.
export function toLocalDateStr(d) {
  const date = d instanceof Date ? d : parseLocalDate(d);
  if (!date || isNaN(date.getTime())) return "";
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

// One bucketing of "Stock Analysis Data" rows — used by Dashboard, StockAnalysis,
// Reports so they don't drift when the rules change.
export function bucketizeStockRows(rows) {
  const k = {
    total_items: 0,
    out_of_stock_active: 0,
    reorder_now: 0,
    watch: 0,
    healthy: 0,
    overstocked: 0,
    dead_stock: 0,
    stock_value: 0,
    lost_per_day: 0,
    profit_per_day: 0,
  };
  (rows || []).forEach((it) => {
    k.total_items++;
    switch (it.action) {
      case "OOS":       k.out_of_stock_active++; break;
      case "REORDER":   k.reorder_now++; break;
      case "WATCH":     k.watch++; break;
      case "HEALTHY":   k.healthy++; break;
      case "OVERSTOCK": k.overstocked++; break;
      case "DEAD":      k.dead_stock++; break;
    }
    k.stock_value += Number(it.stock_value) || 0;
    k.lost_per_day += Number(it["lost/day"]) || 0;
    // Profit / day: only count items that are actually selling AND not flagged dead.
    if (it.action !== "DEAD") {
      const margin = (Number(it.selling_rate) || 0) - (Number(it.cost_rate) || 0);
      const daily = Number(it.daily) || 0;
      if (margin > 0 && daily > 0) k.profit_per_day += margin * daily;
    }
  });
  return k;
}
