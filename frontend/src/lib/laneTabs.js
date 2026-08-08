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
export const LANES = [
  {
    key: "confirmation",
    section: "nav.confirmSection",
    tabs: [
      { to: "Confirmation", label: "nav.confirmation", icon: "phone" },
      { to: "ConfirmationDashboard", label: "nav.cfDashboard", icon: "gauge" },
      { to: "ConfirmationReports", label: "nav.cfReports", icon: "trending-up" },
      { to: "ConfirmationSettings", label: "nav.cfSettings", icon: "settings" },
    ],
  },
  {
    key: "rescue",
    section: "nav.rescueSection",
    tabs: [
      { to: "Rescue", label: "nav.rescue", icon: "route" },
      { to: "RescueReports", label: "nav.rsReports", icon: "trending-up" },
      { to: "RescueSettings", label: "nav.rsSettings", icon: "settings" },
    ],
  },
  {
    key: "tickets",
    section: "nav.ticketsSection",
    tabs: [
      { to: "Tickets", label: "nav.tickets", icon: "message-circle" },
      { to: "Exchanges", label: "nav.exchanges", icon: "refresh-cw" },
      { to: "TicketsReports", label: "nav.tsReports", icon: "trending-up" },
      { to: "TicketsSettings", label: "nav.tsSettings", icon: "settings" },
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
