/**
 * One clock for the whole portal.
 *
 * Every timestamp the backend stores and hands us is written on the SITE's
 * wall clock (Istanbul, UTC+3) while the floor reads it in Morocco (UTC+1).
 * Printed raw, a carrier event showed "09-18 21:30" next to a header clock
 * reading "19:30" — the same instant, two hours apart, on one screen. An
 * agent reading that sees an event two hours in the future, and anyone who
 * counts "how old is this?" off the number is wrong by two hours every time.
 *
 * The fix is to put stored times back on the READER's own clock, not to
 * subtract a constant: Morocco shifts during Ramadan while the site's
 * Istanbul never does, so any hard-coded "minus two" is a bug waiting for a
 * date. The server sends its UTC offset once at boot; we undo it and let the
 * browser render its own local time. The header clock is already the
 * browser's, so the two agree by construction, wherever the reader is.
 *
 * Until the offset arrives — and on a backend too old to send one — every
 * helper returns the string unchanged. A screen that looks exactly like it
 * does today is far better than one that lies by a made-up amount.
 */

let siteOffsetMin = null;

/** Called once from the auth boot. Anything unparsable disables conversion. */
export function setSiteOffset(min) {
  const n = Number(min);
  siteOffsetMin = Number.isFinite(n) ? n : null;
}

export function hasSiteOffset() {
  return siteOffsetMin != null;
}

// "YYYY-MM-DD HH:MM[:SS]" — also tolerates the ISO "T" the optimistic
// client-side rows used to produce. A DATE alone never matches: converting
// one would shift the day itself, which is worse than leaving it.
const STAMP = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/;

const p2 = (n) => String(n).padStart(2, "0");

/** A stored site-clock timestamp → a real Date, or null when we can't tell. */
export function siteToDate(s) {
  if (siteOffsetMin == null) return null;
  const m = STAMP.exec(String(s || ""));
  if (!m) return null;
  const d = new Date(
    Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) - siteOffsetMin * 60000,
  );
  return isNaN(d.getTime()) ? null : d;
}

/**
 * The reader's local wall clock for a stored timestamp, in the SAME shape
 * the caller was given ("…HH:MM" stays minute-precision, "…HH:MM:SS" keeps
 * its seconds). Shape-preserving on purpose: every existing `.slice(5)`,
 * `.slice(11)` and `.slice(0, 10)` at the call sites keeps meaning exactly
 * what it meant, so this is a display change and nothing else.
 */
export function local(s) {
  const raw = String(s || "");
  const d = siteToDate(raw);
  if (!d) return raw;
  const out = `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} `
    + `${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`;
  return out.slice(0, Math.min(raw.length, 19));
}

/** Now, written on the site clock — for optimistic rows that must sit in the
 *  same list as server ones and go through `local()` identically. */
export function nowSite() {
  const d = new Date(Date.now() + (siteOffsetMin == null ? 0 : siteOffsetMin * 60000));
  return `${d.getUTCFullYear()}-${p2(d.getUTCMonth() + 1)}-${p2(d.getUTCDate())} `
    + `${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}:${p2(d.getUTCSeconds())}`;
}
