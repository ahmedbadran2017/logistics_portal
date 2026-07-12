/**
 * Role model — mirrors the backend Logistics Role Map, styled to the Claude
 * Design handoff's grouped navigation.
 *
 * Nav is a list of SECTION groups: { section, items: [{ to, label, icon }] }.
 *   - `to`    is an EXISTING vue-router route name (each item now has its own).
 *   - `label` is an i18n key resolved via useI18n().t().
 *   - `icon`  is a name in components/ui/Icon.vue's PATHS map.
 */
export const ROLE_CONFIG = {
  manager: {
    home: "Cockpit",
    nav: [
      {
        section: "nav.overview",
        items: [
          { to: "Cockpit", label: "nav.cockpit", icon: "gauge" },
          { to: "FloorBoard", label: "nav.floor", icon: "trending-up" },
          { to: "SlaBoard", label: "nav.sla", icon: "shield-alert" },
          { to: "Alerts", label: "nav.alerts", icon: "bell" },
          { to: "Audit", label: "nav.audit", icon: "activity" },
          { to: "Copilot", label: "nav.copilot", icon: "sparkles" },
        ],
      },
      {
        section: "nav.fulfillment",
        items: [
          { to: "Pipeline", label: "nav.orders", icon: "shopping-bag" },
          { to: "Waves", label: "nav.waves", icon: "layers" },
          { to: "PickLists", label: "nav.picklists", icon: "package" },
          { to: "PackStation", label: "nav.pack", icon: "tag" },
          { to: "Shipments", label: "nav.shipments", icon: "truck" },
          { to: "Routes", label: "nav.routes", icon: "route" },
          { to: "Tracking", label: "nav.tracking", icon: "map-pin" },
          { to: "Exceptions", label: "nav.exceptions", icon: "alert-circle" },
          { to: "Returns", label: "nav.returns", icon: "rotate-ccw" },
          { to: "COD", label: "nav.cod", icon: "wallet" },
          { to: "Carriers", label: "nav.carriers", icon: "send" },
        ],
      },
      {
        section: "nav.inventoryGrp",
        items: [
          { to: "Warehouse", label: "nav.warehouse", icon: "warehouse" },
          { to: "Inventory", label: "nav.stock", icon: "boxes" },
          { to: "SkuLookup", label: "nav.skuLookup", icon: "search" },
          { to: "CatalogHub", label: "nav.catalogHub", icon: "refresh-cw" },
          { to: "Reports", label: "nav.reports", icon: "file-text" },
        ],
      },
      {
        section: "nav.team",
        items: [
          { to: "Team", label: "nav.team", icon: "users" },
          { to: "Roster", label: "nav.roster", icon: "calendar" },
          { to: "Bonus", label: "nav.bonus", icon: "zap" },
          { to: "Settings", label: "nav.settings", icon: "settings" },
        ],
      },
    ],
  },
  dispatcher: {
    home: "Assign",
    nav: [
      {
        section: "nav.operations",
        items: [
          { to: "Assign", label: "nav.assign", icon: "layout-grid" },
          { to: "Pipeline", label: "nav.orders", icon: "shopping-bag" },
          { to: "PickLists", label: "nav.picklists", icon: "package" },
          { to: "Waves", label: "nav.waves", icon: "layers" },
        ],
      },
      {
        section: "nav.inventoryGrp",
        items: [
          { to: "Warehouse", label: "nav.warehouse", icon: "warehouse" },
          { to: "Inventory", label: "nav.stock", icon: "boxes" },
          { to: "SkuLookup", label: "nav.skuLookup", icon: "search" },
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "Tracking", label: "nav.tracking", icon: "map-pin" },
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
        ],
      },
    ],
  },
  picker: {
    home: "Queue",
    mobile: true,
    nav: [
      {
        section: "nav.operations",
        items: [
          { to: "Queue", label: "nav.queue", icon: "list-checks" },
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
        ],
      },
    ],
  },
  packer: {
    home: "LabelQueue",
    nav: [
      {
        section: "nav.operations",
        items: [
          { to: "LabelQueue", label: "nav.label", icon: "printer" },
          { to: "PackStation", label: "nav.pack", icon: "tag" },
          { to: "Manifest", label: "nav.manifest", icon: "package-check" },
          { to: "Shipments", label: "nav.shipments", icon: "truck" },
          { to: "Carriers", label: "nav.carriers", icon: "send" },
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
        ],
      },
    ],
  },
  returns: {
    home: "Returns",
    nav: [
      {
        section: "nav.operations",
        items: [
          { to: "Returns", label: "nav.returns", icon: "rotate-ccw" },
          { to: "Tracking", label: "nav.tracking", icon: "map-pin" },
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
        ],
      },
    ],
  },
};

export function homeRouteFor(role) {
  return (ROLE_CONFIG[role] || ROLE_CONFIG.picker).home;
}

/** Grouped nav for a role: [{ section, items:[{to,label,icon}] }]. */
export function navFor(role) {
  return (ROLE_CONFIG[role] || ROLE_CONFIG.picker).nav;
}

/** Flat list of nav items (for the command palette). */
export function navItemsFor(role) {
  return navFor(role).flatMap((g) => g.items);
}

export function isMobileRole(role) {
  return !!(ROLE_CONFIG[role] && ROLE_CONFIG[role].mobile);
}
