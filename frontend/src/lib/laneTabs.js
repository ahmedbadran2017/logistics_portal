/**
 * Contact-Center lanes — the in-page tab model.
 *
 * Each lane is ONE sidebar entry (its `primary` route). Its sub-views —
 * dashboard / reports / settings and any lane-specific workflow — render as
 * tabs at the top of the lane's pages instead of stacking in the sidebar.
 * Every tab is still its own vue-router route, so deep links, code-splitting
 * and the existing pages are all untouched; only the presentation changed.
 *
 *   { to, label, icon }  — `to` is a route name, `label` an i18n key.
 */
// Which ccAdmin flag governs each lane's admin-only tabs.
export const LANE_ADMIN_KEY = { confirmation: "cf", rescue: "rs", tickets: "cs" };

export const LANES = [
  {
    key: "confirmation",
    section: "nav.confirmSection",
    tabs: [
      { to: "Confirmation", label: "nav.confirmation", icon: "phone" },
      // First of the admin tabs on purpose: it is the one a manager opens
      // to ask "is the lane healthy", and the other three are details of it.
      { to: "ConfirmationFunnel", label: "nav.cfFunnel", icon: "trending-up", admin: true },
      { to: "ConfirmationDashboard", label: "nav.cfDashboard", icon: "gauge", admin: true },
      { to: "ConfirmationActivity", label: "nav.cfActivity", icon: "activity", admin: true },
      { to: "ConfirmationReports", label: "nav.cfReports", icon: "trending-up", admin: true },
      // Agent x city. It sat on the manager's Team matrix next to the
      // warehouse floor; the section admins who actually read it could not
      // open that page at all.
      { to: "ConfirmationMatrix", label: "nav.cfMatrix", icon: "layout-grid", admin: true },
      { to: "ConfirmationSettings", label: "nav.cfSettings", icon: "settings", admin: true },
    ],
  },
  {
    key: "rescue",
    section: "nav.rescueSection",
    tabs: [
      { to: "Rescue", label: "nav.rescue", icon: "route" },
      { to: "RescueDashboard", label: "nav.rsDashboard", icon: "gauge", admin: true },
      { to: "RescueReports", label: "nav.rsReports", icon: "trending-up", admin: true },
      { to: "RescueSettings", label: "nav.rsSettings", icon: "settings", admin: true },
    ],
  },
  {
    key: "tickets",
    section: "nav.ticketsSection",
    tabs: [
      { to: "Tickets", label: "nav.tickets", icon: "message-circle" },
      { to: "Exchanges", label: "nav.exchanges", icon: "refresh-cw" },
      // Confirmed customers the warehouse cannot ship. Second tab, not last:
      // it is the only one of these where somebody is waiting on a promise
      // we already made.
      { to: "StockWait", label: "nav.stockWait", icon: "package-x" },
      { to: "TicketsReports", label: "nav.tsReports", icon: "trending-up", admin: true },
      { to: "TicketsSettings", label: "nav.tsSettings", icon: "settings", admin: true },
    ],
  },
];

/** The lane whose tabs include this route name, or null. */
export function laneForRoute(routeName) {
  return LANES.find((l) => l.tabs.some((tab) => tab.to === routeName)) || null;
}

/** The primary (first-tab) route name for each lane — what the sidebar links to. */
export const LANE_PRIMARY = Object.fromEntries(
  LANES.map((l) => [l.key, l.tabs[0].to]),
);
