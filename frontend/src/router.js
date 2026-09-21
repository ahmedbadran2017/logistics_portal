import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "@/composables/useAuth";
import { homeRouteFor } from "@/lib/roles";
import { PORTAL_BASE, IS_CC, IS_SHIP, SURFACE, portalOf } from "@/lib/portal";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";

const AppLayout = () => import("@/components/layout/AppLayout.vue");
const LaneShell = () => import("@/components/layout/LaneShell.vue");

// Paths are RELATIVE to the portal base (/logistics or /confirmation) — the
// base comes from createWebHistory below, so both portals share this tree and
// every {name:…} push works unchanged in either.
const routes = [
  { path: "/login", name: "Login", component: () => import("@/pages/auth/Login.vue"), meta: { guest: true } },
  {
    path: "/",
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      { path: "", name: "Home", redirect: () => ({ name: "Home2" }) },
      // Home2 is a resolver that bounces to the role's landing screen.
      { path: "home", name: "Home2", beforeEnter: roleRedirect, component: { render: () => null } },

      // Picker
      { path: "queue", name: "Queue", component: () => import("@/pages/Queue.vue") },
      { path: "pick/:id", name: "PickMode", component: () => import("@/pages/PickMode.vue"), props: true },

      // Packer / Shipper
      { path: "labels", name: "LabelQueue", component: () => import("@/pages/LabelQueue.vue") },
      { path: "manifest", name: "Manifest", component: () => import("@/pages/Manifest.vue") },

      // Contact center — each lane is a self-contained nested group: the lane
      // shell (its tab bar + nested view) owns the lane's sub-pages. Route NAMES
      // are unchanged so every {name:…} link keeps working; only the tree nests.
      {
        path: "confirmation",
        component: LaneShell,
        children: [
          { path: "", name: "Confirmation", component: () => import("@/pages/Confirmation.vue") },
          { path: "dashboard", name: "ConfirmationDashboard", component: () => import("@/pages/ConfirmationDashboard.vue") },
          { path: "activity", name: "ConfirmationActivity", component: () => import("@/pages/ConfirmationActivity.vue") },
          { path: "reports", name: "ConfirmationReports", component: () => import("@/pages/ConfirmationReports.vue") },
          // The lane's funnel: what arrived, what survived each step, and
          // where the rest went. The three screens beside it answer the
          // queue, the trail and the per-agent table — none answered this.
          //
          // NOT "pulse". The app already has a Floor Pulse at the top level,
          // and the contact centre's router base IS /confirmation — so
          // /confirmation/pulse strips to /pulse and lands on the warehouse
          // screen instead of this one. Two pulses would have been confusing
          // even with the collision fixed; "funnel" is what the page shows.
          { path: "funnel", name: "ConfirmationFunnel", component: () => import("@/pages/ConfirmationFunnel.vue") },
          { path: "settings", name: "ConfirmationSettings", component: () => import("@/pages/ConfirmationSettings.vue") },
        ],
      },
      {
        path: "rescue",
        component: LaneShell,
        children: [
          { path: "", name: "Rescue", component: () => import("@/pages/Rescue.vue") },
          { path: "dashboard", name: "RescueDashboard", component: () => import("@/pages/RescueDashboard.vue") },
          { path: "reports", name: "RescueReports", component: () => import("@/pages/RescueReports.vue") },
          { path: "settings", name: "RescueSettings", component: () => import("@/pages/RescueSettings.vue") },
        ],
      },
      // Customer service: the desk that receives a problem from anywhere.
      { path: "cs", name: "CsDesk", component: () => import("@/pages/CsDesk.vue") },
      { path: "cs-lookup", name: "CsLookup", component: () => import("@/pages/CsLookup.vue") },
      {
        path: "tickets",
        component: LaneShell,
        children: [
          { path: "", name: "Tickets", component: () => import("@/pages/Tickets.vue") },
          { path: "exchanges", name: "Exchanges", component: () => import("@/pages/Exchanges.vue") },
          { path: "reports", name: "TicketsReports", component: () => import("@/pages/TicketsReports.vue") },
          { path: "settings", name: "TicketsSettings", component: () => import("@/pages/TicketsSettings.vue") },
        ],
      },
      // The single-pane agent workspace — the confirmation portal's real home.
      { path: "work", name: "Workspace", component: () => import("@/pages/Workspace.vue") },
      { path: "cc-dashboard", name: "CCDashboard", component: () => import("@/pages/CCDashboard.vue") },
      { path: "contact-center", name: "ContactCenter", component: () => import("@/pages/ContactCenter.vue") },
      { path: "print-station", name: "PrintStation", component: () => import("@/pages/PrintStation.vue") },
      { path: "bonus", name: "Bonus", component: () => import("@/pages/Bonus.vue") },

      // Dispatcher
      { path: "assign", name: "Assign", component: () => import("@/pages/Assign.vue") },
      { path: "pipeline", name: "Pipeline", component: () => import("@/pages/Pipeline.vue") },
      // Confirmed orders that never became a parcel — nothing else surfaces them.
      { path: "stranded", name: "Stranded", component: () => import("@/pages/Stranded.vue") },
      // Orders whose shipping city can't be turned into a carrier label (Arabic / junk).
      { path: "city-check", name: "CityCheck", component: () => import("@/pages/CityCheck.vue") },
      // How the GEOGRAPHY performs — confirm and deliver per city, no names.
      { path: "city-matrix", name: "CityMatrix", component: () => import("@/pages/CityMatrix.vue") },
      // Confirmation-team review: same-customer clusters → one merged order.
      { path: "consolidation", name: "Consolidation", component: () => import("@/pages/Consolidation.vue") },
      { path: "team", name: "Team", component: () => import("@/pages/Team.vue") },

      // Returns
      { path: "returns", name: "Returns", component: () => import("@/pages/Returns.vue") },
      { path: "returns/receive", name: "ReturnReceiving", component: () => import("@/pages/ReturnReceiving.vue") },
      { path: "returns/restock", name: "RestockZone", component: () => import("@/pages/RestockZone.vue") },

      // Manager
      { path: "cockpit", name: "Cockpit", component: () => import("@/pages/Cockpit.vue") },
      { path: "pulse", name: "Pulse", component: () => import("@/pages/Pulse.vue") },
      { path: "team-performance", name: "TeamPerformance", component: () => import("@/pages/TeamPerformance.vue") },
      // Each person judged against a like-for-like column: agents inside one
      // city, floor workers against the same station.
      { path: "team-matrix", name: "TeamMatrix", component: () => import("@/pages/TeamMatrix.vue") },
      { path: "floor-activity", name: "FloorActivity", component: () => import("@/pages/FloorActivity.vue") },
      { path: "velocity", name: "VelocityBoard", component: () => import("@/pages/VelocityBoard.vue") },
      // The full tail behind one of the velocity board's stuck cards.
      { path: "stuck/:key", name: "StuckOrders", component: () => import("@/pages/StuckOrders.vue") },
      { path: "shipments", name: "Shipments", component: () => import("@/pages/Shipments.vue") },
      // The tracking portal's own screens (served under the /tracking base).
      { path: "board", name: "ShipBoard", component: () => import("@/pages/ShipBoard.vue") },
      { path: "ship-settings", name: "ShipSettings", component: () => import("@/pages/ShipSettings.vue") },
      { path: "ship-team", name: "ShipTeam", component: () => import("@/pages/ShipTeam.vue") },
      { path: "blocked", name: "ShipBlocked", component: () => import("@/pages/ShipBlocked.vue") },
      { path: "feedback", name: "ShipFeedback", component: () => import("@/pages/ShipFeedback.vue") },
      { path: "audit", name: "Audit", component: () => import("@/pages/Audit.vue") },

      // Manager — overview
      { path: "floor", name: "FloorBoard", component: () => import("@/pages/FloorBoard.vue") },
      { path: "sla", name: "SlaBoard", component: () => import("@/pages/SlaBoard.vue") },
      { path: "alerts", name: "Alerts", component: () => import("@/pages/Alerts.vue") },

      // Fulfillment
      { path: "picklists", name: "PickLists", component: () => import("@/pages/PickLists.vue") },
      { path: "pack", name: "PackStation", component: () => import("@/pages/PackStation.vue") },
      // The packing desk is its own screen: the sort wall is a WALL (a big
      // screen with slots), this is one parcel in two hands on a PDA.
      { path: "packing", name: "PackDesk", component: () => import("@/pages/PackDesk.vue") },
      // Walking a zone to find out which shelves are real, and in what order.
      { path: "zone-survey", name: "ZoneSurvey", component: () => import("@/pages/ZoneSurvey.vue") },
      { path: "tracking", name: "Tracking", component: () => import("@/pages/Tracking.vue") },
      { path: "exceptions", name: "Exceptions", component: () => import("@/pages/Exceptions.vue") },
      { path: "carriers", name: "Carriers", component: () => import("@/pages/Carriers.vue") },

      // Inventory
      { path: "warehouse", name: "Warehouse", component: () => import("@/pages/Warehouse.vue") },
      { path: "move", name: "MoveStock", component: () => import("@/pages/MoveStock.vue") },
      { path: "goods-in", name: "GoodsIn", component: () => import("@/pages/GoodsIn.vue") },
      { path: "count", name: "CycleCount", component: () => import("@/pages/CycleCount.vue") },
      // The manager's view OF the counting campaign (the screen above is the
      // floor's view FROM inside it).
      { path: "count-control", name: "CountControl", component: () => import("@/pages/CountControl.vue") },
      { path: "inventory", name: "Inventory", component: () => import("@/pages/Inventory.vue") },
      { path: "sku", name: "SkuLookup", component: () => import("@/pages/SkuLookup.vue") },
      { path: "shelf-labels", name: "ShelfLabels", component: () => import("@/pages/ShelfLabels.vue") },
      { path: "weights", name: "Weights", component: () => import("@/pages/Weights.vue") },
      { path: "slotting", name: "Slotting", component: () => import("@/pages/Slotting.vue") },
      { path: "catalog", name: "CatalogHub", component: () => import("@/pages/CatalogHub.vue") },
      { path: "batch-repair", name: "BatchRepair", component: () => import("@/pages/BatchRepair.vue") },

      // Team

      // Shared
      { path: "performance", name: "Performance", component: () => import("@/pages/Performance.vue") },
      { path: "my-dashboard", name: "MyDashboard", component: () => import("@/pages/MyDashboard.vue") },
      { path: "my-cs-dashboard", name: "MyCsDashboard", component: () => import("@/pages/MyCsDashboard.vue") },
      { path: "my-tracking-dashboard", name: "MyTrackingDashboard", component: () => import("@/pages/MyTrackingDashboard.vue") },
      { path: "settings", name: "Settings", component: () => import("@/pages/Settings.vue") },
      { path: "order/:name", name: "OrderDetail", component: () => import("@/pages/OrderDetail.vue"), props: true },
      // Anything unknown (incl. links to removed demo pages) → role home.
      { path: ":pathMatch(.*)*", redirect: () => ({ name: "Home2" }) },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

// ── where the app left off ────────────────────────────────────────────────
// The PWA's start_url is /home, so every cold start — Android killing the
// installed app on a PDA, the phone being locked long enough, a tab reopened
// — landed the person on the role's home screen and threw away the queue,
// the tab and the page they were working. sessionStorage cannot help: it
// dies with exactly the tab we are trying to survive.
const _LAST_KEY = "lp_last_route:" + PORTAL_BASE;
// A new shift starts at home. Coming back from lunch, or from the camera
// app, does not.
const _LAST_MAX_MS = 10 * 60 * 60 * 1000;

function rememberRoute(fullPath, name) {
  // Home is a resolver, Login is a door, and a hidden page would bounce on
  // the way back in — none of them are a place to return to.
  if (!name || name === "Home" || name === "Home2" || name === "Login") return;
  try {
    localStorage.setItem(_LAST_KEY, JSON.stringify({ p: fullPath, t: Date.now() }));
  } catch (_) { /* private mode: the app simply forgets, as before */ }
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
  const home = { name: homeRouteFor(role.value, hiddenPages.value, SURFACE) };
  // Only on a COLD start. `from.name` is empty only for the first navigation
  // of a page load; pressing Home in the nav must still go home, or the
  // button would look broken.
  if (from.name) { next(home); return; }
  const back = lastRoute();
  if (!back || back === to.fullPath) { next(home); return; }
  next(back);
}

const router = createRouter({
  history: createWebHistory(PORTAL_BASE),
  routes,
});

router.beforeEach(async (to, from, next) => {
  // Remember which list an order was opened from, so the detail page's Back
  // returns there (Orders / Consolidation / Stranded …) instead of falling
  // through to the role's home. Chained detail→detail keeps the original list.
  if (to.name === "OrderDetail" && from.name && from.name !== "OrderDetail") {
    try { sessionStorage.setItem("lp_order_ref", from.fullPath); } catch (_) { /* private mode */ }
  }

  const { init, isLoggedIn, role, hiddenPages } = useAuth();
  await init();

  // Portal fence: each role lives on its own side. Confirmation agents landing
  // on /logistics are moved to /confirmation and vice versa for floor roles;
  // managers may use both portals. Hard navigation on purpose — the history
  // base differs, so an in-router redirect can't cross it.
  if (isLoggedIn.value && role.value) {
    // Three surfaces now, so the fence is a table rather than a pair of ifs:
    // each side names its base, and anyone standing on the wrong one is sent
    // home. Managers ("both") are never moved.
    const side = portalOf(role.value);
    const here = IS_CC ? "cc" : IS_SHIP ? "ship" : "floor";
    const BASE = { cc: "/confirmation", ship: "/tracking", floor: "/logistics" };
    if (side !== "both" && side !== here) {
      window.location.replace(BASE[side] + "/home");
      return;
    }
  }

  if (to.meta.requiresAuth && !isLoggedIn.value) {
    next({ name: "Login", query: { redirect: to.fullPath } });
  } else if (to.meta.guest && isLoggedIn.value) {
    next({ name: "Home2" });
  } else if (isLoggedIn.value && to.name && hiddenPages.value.includes(to.name)) {
    // A page the manager hid for this user — deep links bounce home too,
    // and say so, or a link that "does nothing" gets reported as a bug.
    try { useToast().warn(useI18n().t("nav.hiddenBounce"), ""); } catch (_) { /* never block navigation */ }
    next({ name: homeRouteFor(role.value, hiddenPages.value, SURFACE) });
  } else {
    next();
  }
});

// Belt-and-suspenders: if a dynamically-imported asset ever fails to load
// (stale cache after a deploy), hard-reload ONCE so the browser refetches the
// freshly ?ver-busted entry instead of showing a blank route.
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
