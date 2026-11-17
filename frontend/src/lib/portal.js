/**
 * One SPA, four portals — the same bundle serves:
 *   /logistics     the warehouse floor (pick/pack/ship/inventory)
 *   /confirmation  the contact center (confirmation / rescue / CS tickets)
 *   /tracking      shipment tracking (confirmation → the door)
 *   /souk          souk sourcing (buy → receive → photos → content → Live)
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
  // The souk sourcing cycle (buy → receive → photos → content → Live) moved
  // out of /logistics on 2026-11-17: the buyer, the accountant, marketing and
  // content are not floor people, and the floor never needed the cycle's nav.
  // Note the trailing slash test: "/souk" alone, or "/souk/…", never "/soukX".
  : (_P === "/souk" || _P.startsWith("/souk/")) ? "/souk"
  : "/logistics";

export const IS_CC = PORTAL_BASE === "/confirmation";
export const IS_SHIP = PORTAL_BASE === "/tracking";
export const IS_SOUK = PORTAL_BASE === "/souk";
// Which shell the nav/home helpers should build for: "cc" | "ship" | "souk" | false (floor).
export const SURFACE = IS_CC ? "cc" : IS_SHIP ? "ship" : IS_SOUK ? "souk" : false;

/** Each surface's URL base, keyed like portalOf() answers. */
export const BASES = { cc: "/confirmation", ship: "/tracking", souk: "/souk", floor: "/logistics" };

/** The portal a role belongs to ("cc" | "ship" | "souk" | "floor" | "both"). */
export function portalOf(role) {
  // Tracking moved out of the contact centre on 2026-09-13: watching an
  // order's clock from confirmation to the door is its own job, with its own
  // cut-offs and its own settings, and it was borrowing the CC's shell.
  if (role === "tracking") return "ship";
  if (role === "confirmation" || role === "cs") return "cc";
  // The floor's own souk work (receiving the bags, the in-house photos) stays
  // on /logistics for dispatcher / packer / returns — only these four live
  // on the souk portal.
  if (role === "sourcing" || role === "accountant" || role === "marketing" || role === "content") return "souk";
  if (role === "manager") return "both";
  return "floor";
}
