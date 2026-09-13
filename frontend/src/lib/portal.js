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
const _P = window.location.pathname;
export const PORTAL_BASE = _P.startsWith("/confirmation") ? "/confirmation"
  : _P.startsWith("/tracking") ? "/tracking"
  : "/logistics";

export const IS_CC = PORTAL_BASE === "/confirmation";
export const IS_SHIP = PORTAL_BASE === "/tracking";
// Which shell the nav/home helpers should build for: "cc" | "ship" | false (floor).
export const SURFACE = IS_CC ? "cc" : IS_SHIP ? "ship" : false;

/** The portal a role belongs to ("cc" | "ship" | "floor" | "both"). */
export function portalOf(role) {
  // Tracking moved out of the contact centre on 2026-09-13: watching an
  // order's clock from confirmation to the door is its own job, with its own
  // cut-offs and its own settings, and it was borrowing the CC's shell.
  if (role === "tracking") return "ship";
  if (role === "confirmation" || role === "cs") return "cc";
  if (role === "manager") return "both";
  return "floor";
}
