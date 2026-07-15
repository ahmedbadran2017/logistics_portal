import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "@/composables/useAuth";
import { homeRouteFor } from "@/lib/roles";

const AppLayout = () => import("@/components/layout/AppLayout.vue");

const routes = [
  { path: "/logistics/login", name: "Login", component: () => import("@/pages/auth/Login.vue"), meta: { guest: true } },
  {
    path: "/logistics",
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

      // Contact center (confirmation lane)
      { path: "confirmation", name: "Confirmation", component: () => import("@/pages/Confirmation.vue") },
      { path: "confirmation/reports", name: "ConfirmationReports", component: () => import("@/pages/ConfirmationReports.vue") },
      { path: "confirmation/settings", name: "ConfirmationSettings", component: () => import("@/pages/ConfirmationSettings.vue") },

      // Contact center (rescue lane)
      { path: "rescue", name: "Rescue", component: () => import("@/pages/Rescue.vue") },
      { path: "rescue/reports", name: "RescueReports", component: () => import("@/pages/RescueReports.vue") },
      { path: "rescue/settings", name: "RescueSettings", component: () => import("@/pages/RescueSettings.vue") },
      // Contact center (customer-service tickets lane)
      { path: "tickets", name: "Tickets", component: () => import("@/pages/Tickets.vue") },
      { path: "tickets/reports", name: "TicketsReports", component: () => import("@/pages/TicketsReports.vue") },
      { path: "tickets/settings", name: "TicketsSettings", component: () => import("@/pages/TicketsSettings.vue") },
      { path: "contact-center", name: "ContactCenter", component: () => import("@/pages/ContactCenter.vue") },

      // Dispatcher
      { path: "assign", name: "Assign", component: () => import("@/pages/Assign.vue") },
      { path: "pipeline", name: "Pipeline", component: () => import("@/pages/Pipeline.vue") },
      // Confirmation-team review: same-customer clusters → one merged order.
      { path: "consolidation", name: "Consolidation", component: () => import("@/pages/Consolidation.vue") },
      { path: "team", name: "Team", component: () => import("@/pages/Team.vue") },

      // Returns
      { path: "returns", name: "Returns", component: () => import("@/pages/Returns.vue") },
      { path: "returns/receive", name: "ReturnReceiving", component: () => import("@/pages/ReturnReceiving.vue") },
      { path: "returns/restock", name: "RestockZone", component: () => import("@/pages/RestockZone.vue") },

      // Manager
      { path: "cockpit", name: "Cockpit", component: () => import("@/pages/Cockpit.vue") },
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
      { path: "catalog", name: "CatalogHub", component: () => import("@/pages/CatalogHub.vue") },

      // Team

      // Shared
      { path: "performance", name: "Performance", component: () => import("@/pages/Performance.vue") },
      { path: "settings", name: "Settings", component: () => import("@/pages/Settings.vue") },
      { path: "order/:name", name: "OrderDetail", component: () => import("@/pages/OrderDetail.vue"), props: true },
      // Anything unknown (incl. links to removed demo pages) → role home.
      { path: ":pathMatch(.*)*", redirect: () => ({ name: "Home2" }) },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/logistics" },
];

function roleRedirect(to, from, next) {
  const { role, hiddenPages } = useAuth();
  next({ name: homeRouteFor(role.value, hiddenPages.value) });
}

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to, from, next) => {
  const { init, isLoggedIn, role, hiddenPages } = useAuth();
  await init();

  if (to.meta.requiresAuth && !isLoggedIn.value) {
    next({ name: "Login", query: { redirect: to.fullPath } });
  } else if (to.meta.guest && isLoggedIn.value) {
    next({ name: "Home2" });
  } else if (isLoggedIn.value && to.name && hiddenPages.value.includes(to.name)) {
    // A page the manager hid for this user — deep links bounce home too.
    next({ name: homeRouteFor(role.value, hiddenPages.value) });
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
