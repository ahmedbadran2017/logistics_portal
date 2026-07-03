/**
 * Locked color mappings from the conception. Each returns a tailwind text color
 * class + the raw hex (for tinted badge backgrounds via inline style).
 * Keeping this single source of truth means a "Breached" badge looks identical
 * on every screen.
 */
const HEX = {
  slate: "#64748b",
  blue: "#3b82f6",
  cyan: "#06b6d4",
  green: "#10b981",
  yellow: "#f59e0b",
  orange: "#f97316",
  purple: "#8b5cf6",
  red: "#ef4444",
};

// Sales Order custom_logistics_status → color key
export const STAGE_COLOR = {
  Pending: "slate",
  Picked: "orange",
  "In transit": "cyan",
  Received: "blue",
  "Label Generated": "purple",
  "Label Printed": "purple",
  Shipped: "green",
  Delivered: "green",
  Returned: "red",
};

// Delivery Note custom_sla_status → color key
export const SLA_COLOR = {
  "On Track": "green",
  "At Risk": "yellow",
  Breached: "red",
  Delivered: "green",
  "Delivered Late": "orange",
  Returned: "slate",
};

// Carrier tracking status → color key
export const TRACK_COLOR = {
  Pending: "slate",
  "Picked up": "cyan",
  "In Transit": "cyan",
  "Out For Delivery": "blue",
  Delivered: "green",
  "Delivery Exception": "orange",
  "Failed Attempt": "orange",
  Return: "red",
  Returned: "red",
};

export function colorHex(key) {
  return HEX[key] || HEX.slate;
}

export function stageHex(stage) {
  return colorHex(STAGE_COLOR[stage]);
}
export function slaHex(sla) {
  return colorHex(SLA_COLOR[sla]);
}
export function trackHex(t) {
  return colorHex(TRACK_COLOR[t]);
}
