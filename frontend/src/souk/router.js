import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "@/composables/useAuth";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";
import { homeRouteFor } from "@/lib/roles";
import { BASES, portalOf } from "@/lib/portal";

const SoukShell = () => import("./SoukShell.vue");

// The souk portal's routes, relative to /souk. The route NAMES are the same
// as on /logistics (SoukBoard, SoukPhoto, …) so every page's {name: …} link
// works unchanged in either app. The board is /souk/launch: "board" means
// the tracking portal's ShipBoard everywhere else, and one word should not
// mean two screens.
const routes = [
  { path: "/login", name: "Login", component: () => import("./SoukLogin.vue"), meta: { guest: true } },
  {
    path: "/",
    component: SoukShell,
    meta: { requiresAuth: true },
    children: [
      { path: "", name: "Home", redirect: () => ({ name: "Home2" }) },
      { path: "home", name: "Home2", beforeEnter: roleRedirect, component: { render: () => null } },
      { path: "launch", name: "SoukBoard", component: () => import("@/pages/SoukBoard.vue") },
      { path: "custody", name: "SoukTrip", component: () => import("@/pages/SoukTrip.vue") },
      { path: "buy", name: "SoukBuy", component: () => import("@/pages/SoukBuy.vue") },
      { path: "p/:name", name: "SoukProduct", component: () => import("@/pages/SoukProduct.vue") },
      { path: "receive/:po?", name: "SoukReceive", component: () => import("@/pages/SoukReceive.vue") },
      { path: "photo/:name?", name: "SoukPhoto", component: () => import("@/pages/SoukPhoto.vue") },
      { path: "studio/:name?", name: "SoukStudio", component: () => import("@/pages/SoukStudio.vue") },
      { path: "content/:name?", name: "SoukContent", component: () => import("@/pages/SoukContent.vue") },
      { path: "review/:name?", name: "SoukReview", component: () => import("@/pages/SoukReview.vue") },
      // Roles & access for the souk team — the manager's only.
      { path: "team", name: "Team", component: () => import("@/pages/Team.vue"), meta: { manager: true } },
      { path: ":pathMatch(.*)*", redirect: () => ({ name: "Home2" }) },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

// ── where the app left off ────────────────────────────────────────────────
// The buyer installs /souk on the phone; Android kills the app between two
// stalls, and a cold start must reopen the purchase being entered, not the
// custody screen. Same rule as the floor app: 10 hours, then home.
const _LAST_KEY = "lp_last_route:/souk";
const _LAST_MAX_MS = 10 * 60 * 60 * 1000;

function rememberRoute(fullPath, name) {
  if (!name || name === "Home" || name === "Home2" || name === "Login") return;
  try {
    localStorage.setItem(_LAST_KEY, JSON.stringify({ p: fullPath, t: Date.now() }));
  } catch (_) { /* private mode */ }
}

function lastRoute() {
  try {
    const raw = JSON.parse(localStorage.getItem(_LAST_KEY) || "null");
    if (!raw || !raw.p || Date.now() - (raw.t || 0) > _LAST_MAX_MS) return "";
    return String(raw.p);
  } catch (_) { return ""; }
}

function roleRedirect(to, from, next) {
  const { role, hiddenPages } = useAuth();
  const home = { name: homeRouteFor(role.value, hiddenPages.value, "souk") };
  if (from.name) { next(home); return; }
  const back = lastRoute();
  if (!back || back === to.fullPath) { next(home); return; }
  next(back);
}

// Somebody from another portal who lands here goes back to theirs. A floor
// packer handed a /souk/photo/X or /souk/receive/X link keeps the screen:
// that work is theirs too, on /logistics/souk/… where the floor app lists it.
function elsewhere(side, to) {
  if (side === "floor" && (to.name === "SoukPhoto" || to.name === "SoukReceive")) {
    return BASES.floor + "/souk" + to.fullPath;
  }
  return (BASES[side] || BASES.floor) + "/home";
}

const router = createRouter({
  history: createWebHistory("/souk"),
  routes,
});

router.beforeEach(async (to, from, next) => {
  const { init, isLoggedIn, role, hiddenPages } = useAuth();
  await init();

  if (isLoggedIn.value && role.value) {
    const side = portalOf(role.value);
    if (side !== "souk" && side !== "both") {
      window.location.replace(elsewhere(side, to));
      return;
    }
  }

  if (to.meta.requiresAuth && !isLoggedIn.value) {
    next({ name: "Login", query: { redirect: to.fullPath } });
  } else if (to.meta.guest && isLoggedIn.value) {
    next({ name: "Home2" });
  } else if (isLoggedIn.value && to.matched.some((r) => r.meta.manager) && role.value !== "manager") {
    next({ name: "Home2" });
  } else if (isLoggedIn.value && to.name && hiddenPages.value.includes(to.name)) {
    try { useToast().warn(useI18n().t("nav.hiddenBounce"), ""); } catch (_) { /* never block */ }
    next({ name: homeRouteFor(role.value, hiddenPages.value, "souk") });
  } else {
    next();
  }
});

// Same belt-and-braces as the floor app: a stale bundle after a deploy
// reloads once instead of rendering a blank screen.
router.onError((err) => {
  const msg = String(err && err.message || "");
  if (/dynamically imported module|Failed to fetch|module script failed|Importing a module/i.test(msg)) {
    const KEY = "lp_asset_reload";
    if (!sessionStorage.getItem(KEY)) {
      sessionStorage.setItem(KEY, "1");
      window.location.reload();
    }
  }
});
router.afterEach((to) => {
  sessionStorage.removeItem("lp_asset_reload");
  rememberRoute(to.fullPath, to.name);
});

export default router;
