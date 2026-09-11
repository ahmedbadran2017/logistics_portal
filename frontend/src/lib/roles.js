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
      // Six sections, each answering ONE question, in the order a manager's
      // day actually asks them. The old "fulfillment" was a thirteen-item
      // wall that mixed the forward journey with the return loop; the split
      // follows the parcel: watch it, push it out, chase what came back,
      // keep the shelves true, fix what broke, run the people.
      {
        // Live monitoring — is today healthy?
        section: "nav.overview",
        items: [
          { to: "Cockpit", label: "nav.cockpit", icon: "gauge" },
          { to: "FloorBoard", label: "nav.floor", icon: "trending-up" },
          { to: "SlaBoard", label: "nav.sla", icon: "shield-alert" },
          { to: "Alerts", label: "nav.alerts", icon: "bell" },
          { to: "Audit", label: "nav.audit", icon: "activity" },
        ],
      },
      {
        // The forward journey, in the order a parcel travels it.
        section: "nav.fulfillment",
        items: [
          { to: "Pipeline", label: "nav.orders", icon: "shopping-bag" },
          { to: "Consolidation", label: "nav.consolidation", icon: "git-merge" },
          { to: "PickLists", label: "nav.picklists", icon: "package" },
          { to: "Stranded", label: "nav.stranded", icon: "package-x" },
          { to: "CityCheck", label: "nav.cityCheck", icon: "map-pin" },
          { to: "PackStation", label: "nav.pack", icon: "tag" },
          { to: "Shipments", label: "nav.shipments", icon: "truck" },
          { to: "Carriers", label: "nav.carriers", icon: "send" },
        ],
      },
      {
        // After the truck left: track it, rescue it, take it back, reshelve.
        section: "nav.afterShip",
        items: [
          { to: "Tracking", label: "nav.tracking", icon: "map-pin" },
          { to: "Exceptions", label: "nav.exceptions", icon: "alert-circle" },
          { to: "Returns", label: "nav.returns", icon: "rotate-ccw" },
          { to: "ReturnReceiving", label: "nav.receiving", icon: "package-check" },
          { to: "RestockZone", label: "nav.restock", icon: "boxes" },
        ],
      },
      {
        // The shelves: what's on them, what arrives, keeping them honest.
        section: "nav.inventoryGrp",
        items: [
          { to: "Warehouse", label: "nav.warehouse", icon: "warehouse" },
          { to: "Inventory", label: "nav.stock", icon: "boxes" },
          { to: "GoodsIn", label: "nav.goodsIn", icon: "archive" },
          { to: "MoveStock", label: "nav.move", icon: "route" },
          { to: "CycleCount", label: "nav.count", icon: "list-checks" },
          { to: "Slotting", label: "nav.slotting", icon: "layout-grid" },
          { to: "VelocityBoard", label: "nav.velocity", icon: "zap" },
        ],
      },
      {
        // Utilities and repair benches — reached on purpose, not passed daily.
        section: "nav.tools",
        items: [
          { to: "SkuLookup", label: "nav.skuLookup", icon: "search" },
          { to: "ShelfLabels", label: "nav.shelfLabels", icon: "printer" },
          { to: "PrintStation", label: "nav.printStation", icon: "radio" },
          { to: "Weights", label: "nav.weights", icon: "scale" },
          { to: "CatalogHub", label: "nav.catalogHub", icon: "refresh-cw" },
          { to: "BatchRepair", label: "nav.batchRepair", icon: "unlock" },
        ],
      },
      {
        // The people: who they are, how they did, what they earn.
        section: "nav.team",
        items: [
          { to: "Team", label: "nav.team", icon: "users" },
          { to: "TeamPerformance", label: "nav.teamPerf", icon: "award" },
          { to: "FloorActivity", label: "nav.floorActivity", icon: "activity" },
          { to: "Bonus", label: "nav.bonus", icon: "wallet" },
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
          { to: "Stranded", label: "nav.stranded", icon: "package-x" },
          { to: "CityCheck", label: "nav.cityCheck", icon: "map-pin" },
          // The sort wall is where a parcel that finished picking with no
          // carrier label surfaces, and fixing its city + calling the carrier
          // is a DISPATCHER act (relabel_order gates on dispatcher/manager).
          // The server always allowed it; only this menu did not, which made
          // the repair look manager-only. CityCheck catches a bad city before
          // picking, this catches the ones that got through.
          { to: "PackStation", label: "nav.pack", icon: "tag" },
        ],
      },
      {
        // After the truck left — a dispatcher chases parcels too. This lived
        // under "Me", which is where nobody looks for work.
        section: "nav.afterShip",
        items: [
          { to: "Tracking", label: "nav.tracking", icon: "map-pin" },
        ],
      },
      {
        section: "nav.inventoryGrp",
        items: [
          { to: "Warehouse", label: "nav.warehouse", icon: "warehouse" },
          { to: "Inventory", label: "nav.stock", icon: "boxes" },
          { to: "GoodsIn", label: "nav.goodsIn", icon: "archive" },
          { to: "MoveStock", label: "nav.move", icon: "route" },
          { to: "CycleCount", label: "nav.count", icon: "list-checks" },
          { to: "Slotting", label: "nav.slotting", icon: "layout-grid" },
        ],
      },
      {
        section: "nav.tools",
        items: [
          { to: "SkuLookup", label: "nav.skuLookup", icon: "search" },
          { to: "ShelfLabels", label: "nav.shelfLabels", icon: "printer" },
          { to: "Weights", label: "nav.weights", icon: "scale" },
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
          { href: "/hrms", label: "nav.attendance", icon: "clock" },
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
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
          { to: "Bonus", label: "nav.bonus", icon: "wallet" },
          { href: "/hrms", label: "nav.attendance", icon: "clock" },
        ],
      },
    ],
  },
  packer: {
    // Home = the sorting station: that's where the packer's real work starts
    // (scan tote → allocate → print). LabelQueue stays as the reprint queue.
    home: "PackStation",
    nav: [
      {
        section: "nav.operations",
        items: [
          { to: "PackStation", label: "nav.pack", icon: "tag" },
          { to: "LabelQueue", label: "nav.label", icon: "printer" },
          { to: "Manifest", label: "nav.manifest", icon: "package-check" },
          { to: "Shipments", label: "nav.shipments", icon: "truck" },
          { to: "Carriers", label: "nav.carriers", icon: "send" },
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
          { href: "/hrms", label: "nav.attendance", icon: "clock" },
        ],
      },
    ],
  },
  confirmation: {
    // The sub-team split (2026-08-27): confirmation sees CONFIRMATION work
    // only. Rescue/Tracking belong to the tracking team, Tickets to cs —
    // their pages stay reachable to this role at the API level solely for
    // the shared Not-Delivered engine, but never in the nav.
    // Landing = My dashboard (Ahmed 2026-08-28): the agent opens on their
    // own numbers, one click into the Workspace to work.
    home: "MyDashboard",
    nav: [
      {
        section: "nav.contactSection",
        items: [
          { to: "Workspace", label: "nav.workspace", icon: "sparkles" },
          { to: "Confirmation", label: "nav.confirmation", icon: "phone" },
          { to: "Consolidation", label: "nav.consolidation", icon: "git-merge" },
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "MyDashboard", label: "nav.myDashboard", icon: "gauge" },
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
          { to: "Bonus", label: "nav.bonus", icon: "wallet" },
          { href: "/hrms", label: "nav.attendance", icon: "clock" },
        ],
      },
    ],
  },
  // Contact-center sub-teams (Ahmed 2026-08-27): كونفيرميشن / خدمة عملاء
  // وشكاوى / متابعة الشحنات — each sees only its own lane(s).
  cs: {
    // Landing = their own dashboard (same rule as confirmation).
    home: "MyCsDashboard",
    nav: [
      {
        section: "nav.contactSection",
        items: [
          { to: "Tickets", label: "nav.tickets", icon: "message-circle" },
          { to: "Exchanges", label: "nav.exchanges", icon: "refresh-cw" },
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "MyCsDashboard", label: "nav.myDashboard", icon: "gauge" },
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
          { to: "Bonus", label: "nav.bonus", icon: "wallet" },
          { href: "/hrms", label: "nav.attendance", icon: "clock" },
        ],
      },
    ],
  },
  tracking: {
    // Landing = their own dashboard (same rule as confirmation).
    home: "MyTrackingDashboard",
    nav: [
      {
        section: "nav.contactSection",
        items: [
          { to: "Rescue", label: "nav.rescue", icon: "route" },
          { to: "Tracking", label: "nav.tracking", icon: "map-pin" },
          { to: "Stranded", label: "nav.stranded", icon: "package-x" },
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "MyTrackingDashboard", label: "nav.myDashboard", icon: "gauge" },
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
          { to: "Bonus", label: "nav.bonus", icon: "wallet" },
          { href: "/hrms", label: "nav.attendance", icon: "clock" },
        ],
      },
    ],
  },
  returns: {
    home: "Returns",
    nav: [
      {
        // The return loop in the order a parcel travels it: it comes back,
        // gets received, goes back on a shelf — and Tracking to see what is
        // still on the road toward this desk.
        section: "nav.operations",
        items: [
          { to: "Returns", label: "nav.returns", icon: "rotate-ccw" },
          { to: "ReturnReceiving", label: "nav.receiving", icon: "package-check" },
          { to: "RestockZone", label: "nav.restock", icon: "boxes" },
          { to: "Tracking", label: "nav.tracking", icon: "map-pin" },
        ],
      },
      {
        section: "nav.inventoryGrp",
        items: [
          { to: "GoodsIn", label: "nav.goodsIn", icon: "archive" },
          { to: "MoveStock", label: "nav.move", icon: "route" },
          { to: "CycleCount", label: "nav.count", icon: "list-checks" },
          { to: "ShelfLabels", label: "nav.shelfLabels", icon: "printer" },
          { to: "Weights", label: "nav.weights", icon: "scale" },
        ],
      },
      {
        section: "nav.me",
        items: [
          { to: "Performance", label: "nav.performance", icon: "trending-up" },
          { href: "/hrms", label: "nav.attendance", icon: "clock" },
        ],
      },
    ],
  },
};

// The contact-center portal (/confirmation) is a separate surface: the
// confirmation role's config IS its nav; a manager entering it gets this
// dedicated shell instead of the logistics one. Conversely the logistics
// manager nav below holds NO contact-center entries any more — the lanes
// moved out of /logistics entirely (Ahmed, 2026-08-27).
const CC_MANAGER = {
  home: "CCDashboard",
  nav: [
    {
      section: "nav.overview",
      items: [
        { to: "CCDashboard", label: "nav.ccDashboard", icon: "gauge" },
      ],
    },
    {
      section: "nav.contactSection",
      items: [
        { to: "Workspace", label: "nav.workspace", icon: "sparkles" },
        { to: "Confirmation", label: "nav.confirmation", icon: "phone" },
        { to: "Rescue", label: "nav.rescue", icon: "route" },
        { to: "Tickets", label: "nav.tickets", icon: "message-circle" },
      ],
    },
    {
      section: "nav.operations",
      items: [
        { to: "Consolidation", label: "nav.consolidation", icon: "git-merge" },
        { to: "Stranded", label: "nav.stranded", icon: "package-x" },
        { to: "Tracking", label: "nav.tracking", icon: "map-pin" },
      ],
    },
    {
      section: "nav.team",
      items: [
        { to: "Team", label: "nav.team", icon: "users" },
        { to: "Performance", label: "nav.performance", icon: "trending-up" },
        { to: "Bonus", label: "nav.bonus", icon: "wallet" },
        { to: "Settings", label: "nav.settings", icon: "settings" },
        { href: "/hrms", label: "nav.attendance", icon: "clock" },
      ],
    },
  ],
};

function configFor(role, cc) {
  if (cc) {
    if (role === "manager") return CC_MANAGER;
    return ROLE_CONFIG[role] || ROLE_CONFIG.confirmation;
  }
  return ROLE_CONFIG[role] || ROLE_CONFIG.picker;
}

/** Grouped nav for a role, minus the pages a manager hid for this user. */
export function navFor(role, hidden, cc = false) {
  const nav = configFor(role, cc).nav;
  if (!hidden || !hidden.length) return nav;
  const h = new Set(hidden);
  return nav
    .map((g) => ({ ...g, items: g.items.filter((i) => !h.has(i.to)) }))
    .filter((g) => g.items.length);
}

/** Flat list of nav items (for the command palette / route guard). */
export function navItemsFor(role, hidden, cc = false) {
  return navFor(role, hidden, cc).flatMap((g) => g.items);
}

export function homeRouteFor(role, hidden, cc = false) {
  const home = configFor(role, cc).home;
  if (hidden && hidden.includes(home)) {
    const first = navItemsFor(role, hidden, cc)[0];
    return first ? first.to : home;
  }
  return home;
}

export function isMobileRole(role) {
  return !!(ROLE_CONFIG[role] && ROLE_CONFIG[role].mobile);
}
