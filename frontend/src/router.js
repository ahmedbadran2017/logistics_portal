import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "@/composables/useAuth";
import { homeRouteFor } from "@/lib/roles";
import { PORTAL_BASE, IS_CC, portalOf } from "@/lib/portal";

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
          { path: "reports", name: "ConfirmationReports", component: () => import("@/pages/ConfirmationReports.vue") },
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
      { path: "bonus", name: "Bonus", component: () => import("@/pages/Bonus.vue") },

      // Dispatcher
      { path: "assign", name: "Assign", component: () => import("@/pages/Assign.vue") },
      { path: "pipeline", name: "Pipeline", component: () => import("@/pages/Pipeline.vue") },
      // Confirmed orders that never became a parcel — nothing else surfaces them.
      { path: "stranded", name: "Stranded", component: () => import("@/pages/Stranded.vue") },
      // Orders whose shipping city can't be turned into a carrier label (Arabic / junk).
      { path: "city-check", name: "CityCheck", component: () => import("@/pages/CityCheck.vue") },
      // Confirmation-team review: same-customer clusters → one merged order.
      { path: "consolidation", name: "Consolidation", component: () => import("@/pages/Consolidation.vue") },
      { path: "team", name: "Team", component: () => import("@/pages/Team.vue") },

      // Returns
      { path: "returns", name: "Returns", component: () => import("@/pages/Returns.vue") },
      { path: "returns/receive", name: "ReturnReceiving", component: () => import("@/pages/ReturnReceiving.vue") },
      { path: "returns/restock", name: "RestockZone", component: () => import("@/pages/RestockZone.vue") },

      // Manager
      { path: "cockpit", name: "Cockpit", component: () => import("@/pages/Cockpit.vue") },
      { path: "team-performance", name: "TeamPerformance", component: () => import("@/pages/TeamPerformance.vue") },
      { path: "velocity", name: "VelocityBoard", component: () => import("@/pages/VelocityBoard.vue") },
      { path: "shipments", name: "Shipments", component: () => import("@/pages/Shipments.vue") },
      { path: "audit", name: "Audit", component: () => import("@/pages/Audit.vue") },

      // Manager — overview
      { path: "floor", name: "FloorBoard", component: () => import("@/pages/FloorBoard.vue") },
      { path: "sla", name: "SlaBoard", component: () => import("@/pages/SlaBoard.vue") },
      { path: "alerts", name: "Alerts", component: () => import("@/pages/Alerts.vue") },

      // Fulfillment
      { path: "picklists", name: "PickLists", component: () => import("@/pages/PickLists.vue") },
      { path: "pack", name: "PackStation", component: () => import("@/pages/PackStation.vue") },
      { path: "tracking", name: "Tracking", component: () => import("@/pages/Tracking.vue") },
      { path: "exceptions", name: "Exceptions", component: () => import("@/pages/Exceptions.vue") },
      { path: "carriers", name: "Carriers", component: () => import("@/pages/Carriers.vue") },

      // Inventory
      { path: "warehouse", name: "Warehouse", component: () => import("@/pages/Warehouse.vue") },
      { path: "move", name: "MoveStock", component: () => import("@/pages/MoveStock.vue") },
      { path: "goods-in", name: "GoodsIn", component: () => import("@/pages/GoodsIn.vue") },
      { path: "count", name: "CycleCount", component: () => import("@/pages/CycleCount.vue") },
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
      { path: "settings", name: "Settings", component: () => import("@/pages/Settings.vue") },
      { path: "order/:name", name: "OrderDetail", component: () => import("@/pages/OrderDetail.vue"), props: true },
      // Anything unknown (incl. links to removed demo pages) → role home.
      { path: ":pathMatch(.*)*", redirect: () => ({ name: "Home2" }) },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

function roleRedirect(to, from, next) {
  const { role, hiddenPages } = useAuth();
  next({ name: homeRouteFor(role.value, hiddenPages.value, IS_CC) });
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
    const side = portalOf(role.value);
    if (side === "cc" && !IS_CC) {
      window.location.replace("/confirmation/home");
      return;
    }
    if (side === "floor" && IS_CC) {
      window.location.replace("/logistics/home");
      return;
    }
  }

  if (to.meta.requiresAuth && !isLoggedIn.value) {
    next({ name: "Login", query: { redirect: to.fullPath } });
  } else if (to.meta.guest && isLoggedIn.value) {
    next({ name: "Home2" });
  } else if (isLoggedIn.value && to.name && hiddenPages.value.includes(to.name)) {
    // A page the manager hid for this user — deep links bounce home too.
    next({ name: homeRouteFor(role.value, hiddenPages.value, IS_CC) });
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
router.afterEach(() => sessionStorage.removeItem("lp_asset_reload"));

export default router;
