// One colour family + one icon per stage of the souk cycle, used the same way
// on every screen (board column, stage pill, the working screen's section
// header, the next-step button). Colours live in souk.css (.st-<stage>).
export const STAGE_ICON = {
  buying: "shopping-bag",
  bought: "package",
  photos: "camera",
  studio: "sparkles",
  content: "notebook-pen",
  review: "clipboard-check",
  live: "zap",
  dropped: "ban",
};

/** Class that sets the stage's colour family on an element. */
export const stageClass = (s) => "st-" + (STAGE_ICON[s] ? s : "dropped");
export const stageIcon = (s) => STAGE_ICON[s] || "circle";

// Colour codes (the SKU's colour part) → a dot on screen.
export const SWATCH = {
  RED: "#b4412c", BLU: "#2b5fb4", GRN: "#2f7d4f", BLK: "#1c1917", WHT: "#ffffff", BEI: "#d9c7a7",
  BRN: "#7a4b2a", GRY: "#8a8784", PNK: "#e79bb4", YEL: "#e8c33a", ORG: "#e5792b", PUR: "#7b4fa8",
  NAV: "#1f2f57", GLD: "#c9a227", SLV: "#c4c4c4", NAT: "#cdb38b",
  MLT: "conic-gradient(#b4412c, #e8c33a, #2f7d4f, #2b5fb4, #7b4fa8, #b4412c)",
};
export const swatch = (code) => SWATCH[code] || "#d6d3d1";
