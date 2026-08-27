/**
 * One SPA, two portals — the same bundle serves:
 *   /logistics     the warehouse floor (pick/pack/ship/inventory)
 *   /confirmation  the contact center (confirmation / rescue / CS tickets)
 *
 * The split is Ahmed's 2026-08-27 directive: the confirmation team must live
 * in its own portal, fully separated from logistics (like joyagent's supplier
 * portal). The base is read once from the URL prefix; every route name works
 * identically under either base, and the router guard keeps each role on its
 * own side (managers may enter both).
 */
export const PORTAL_BASE = window.location.pathname.startsWith("/confirmation")
  ? "/confirmation"
  : "/logistics";

export const IS_CC = PORTAL_BASE === "/confirmation";

/** The portal a role belongs to ("cc" | "floor" | "both"). */
export function portalOf(role) {
  if (role === "confirmation" || role === "cs" || role === "tracking") return "cc";
  if (role === "manager") return "both";
  return "floor";
}
