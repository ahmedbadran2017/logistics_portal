// Stale-while-revalidate for board pages: the last good response is kept in
// sessionStorage so a page paints instantly on re-entry and refreshes behind
// it. Per tab, gone when the tab closes; every read and write is guarded —
// a private window or a full store must never break a page.
const PREFIX = "lp.swr.";
const MAX_AGE_MS = 10 * 60 * 1000;

export function readStale(key) {
  try {
    const raw = sessionStorage.getItem(PREFIX + key);
    if (!raw) return null;
    const { t, v } = JSON.parse(raw);
    if (!t || Date.now() - t > MAX_AGE_MS) return null;
    return v;
  } catch (_) { return null; }
}

export function writeStale(key, v) {
  try { sessionStorage.setItem(PREFIX + key, JSON.stringify({ t: Date.now(), v })); }
  catch (_) { /* quota or private mode: the page simply loads the slow way */ }
}
