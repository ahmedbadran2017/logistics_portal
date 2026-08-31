/**
 * Shelf label sheet — renders a page of Code-128 SKU labels for one shelf into
 * a printable window, sized for a Zebra thermal label printer (one label per
 * feed via `@page` + a page break after every label).
 *
 * The barcode payload is the raw custom_sku, so resolve_scan() reads it straight
 * back to the same item. Labels are built here (not server-side) because the
 * Code-128 SVG is generated client-side in code128.js.
 */
import { code128SVG } from "@/lib/code128.js";

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// Supported thermal label stocks (width × height, mm). Zebra desktop printers
// (GK420/ZD410) are commonly loaded with one of these for SKU labels.
export const LABEL_SIZES = [
  { key: "50x30", w: 50, h: 30, label: "50 × 30 mm" },
  { key: "40x30", w: 40, h: 30, label: "40 × 30 mm" },
  { key: "57x32", w: 57, h: 32, label: "57 × 32 mm" },
  { key: "38x25", w: 38, h: 25, label: "38 × 25 mm" },
];

/** One printable label's inner HTML: barcode over the human-readable SKU, the
 *  product name, and the shelf it belongs to (so re-shelving is unambiguous). */
// A handheld stops decoding below a ~0.25mm narrow bar; on a 203dpi head that
// is 2 dots, and anything finer prints as an unstable 1-or-2-dot bar. Code 128
// also wants 10 quiet modules each side.
const MIN_MODULE_MM = 0.25;
const QUIET_MODULES = 20;

function labelHTML(item, shelf, sizeMM) {
  // The barcode carries whatever the SERVER decided is safe to scan: the SKU
  // when it fits, the numeric item code when it does not (resolve_scan accepts
  // both). Falling back to the raw SKU keeps old callers working.
  const payload = item.barcode || item.sku;

  // Size the module FROM THE PAPER. The old code drew at a fixed 1.4px and let
  // CSS shrink the finished SVG to fit — which is exactly how a long SKU ended
  // up with 0.2mm bars that no scanner on the floor could read.
  const probe = code128SVG(payload, { height: 10, module: 1 });
  const moduleMM = sizeMM.w / (probe.modules + QUIET_MODULES);
  const tooFine = moduleMM < MIN_MODULE_MM;

  const { svg } = code128SVG(payload, {
    height: sizeMM.h > 28 ? 42 : 34,
    module: moduleMM * 4,     // 4 px per mm in the SVG's own units
  });
  const widthMM = (probe.modules * moduleMM).toFixed(2);

  return `
    <div class="lbl">
      <div class="bc"><div style="width:${widthMM}mm">${svg}</div></div>
      <div class="sku">${esc(item.sku || payload)}</div>
      <div class="nm">${esc(item.name)}</div>
      <div class="loc">${esc(shelf)}${tooFine ? ' <span class="warn">!</span>' : ""}</div>
    </div>`;
}

/**
 * Open a print window with every label for the shelf.
 * @param {object}   opts
 * @param {string}   opts.shelf     shelf code (e.g. "H14A")
 * @param {Array}    opts.items     [{sku, name, qty, noSku}]
 * @param {"sku"|"piece"} opts.copies  one label per SKU, or one per piece
 * @param {object}   opts.size      a LABEL_SIZES entry
 * @returns {boolean}  false if the popup was blocked
 */
export function printShelfLabels({ shelf, items, copies, size }) {
  const sizeMM = size || LABEL_SIZES[0];
  const printable = (items || []).filter((i) => i.sku && !i.noSku);

  const labels = [];
  for (const it of printable) {
    // The per-row editable count is authoritative when present (0 = skip this
    // row). Only when no count was passed do we fall back to the sheet mode:
    // one label per piece in stock, or one per SKU.
    const n = it.copies == null
      ? (copies === "piece" ? Math.max(1, Number(it.qty || 1)) : 1)
      : Math.max(0, Math.floor(Number(it.copies) || 0));
    for (let i = 0; i < n; i++) labels.push(labelHTML(it, shelf, sizeMM));
  }
  if (!labels.length) return false;

  const html = `<!doctype html><html><head><meta charset="utf-8">
<title>${esc(shelf)} — Labels</title>
<style>
  @page { size: ${sizeMM.w}mm ${sizeMM.h}mm; margin: 0; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { font-family: -apple-system, "Segoe UI", Arial, sans-serif; color: #000; }
  .lbl {
    width: ${sizeMM.w}mm; height: ${sizeMM.h}mm;
    padding: 1mm 2mm; overflow: hidden;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    page-break-after: always; break-after: page;
    text-align: center;
  }
  .lbl:last-child { page-break-after: auto; break-after: auto; }
  .bc { line-height: 0; }
  /* The wrapper is sized in mm from the module width; the SVG fills it, so
     the printed bar width is the one we calculated - never a CSS squash. */
  .bc > div { margin: 0 auto; }
  .bc svg { width: 100%; height: auto; display: block; }
  .warn { color: #b91c1c; font-weight: 700; }
  .sku { font-family: ui-monospace, Menlo, monospace; font-size: 10pt; font-weight: 700; margin-top: 0.5mm; letter-spacing: .02em; }
  .nm  { font-size: 6.5pt; line-height: 1.05; margin-top: 0.5mm; max-height: 4.5mm; overflow: hidden; }
  .loc { font-size: 7pt; font-weight: 700; margin-top: 0.3mm; }
  @media screen {
    body { background: #f5f5f4; padding: 16px; }
    .lbl { background: #fff; margin: 0 auto 8px; box-shadow: 0 1px 4px rgba(0,0,0,.15); }
  }
</style></head><body>
  ${labels.join("")}
  <script>window.onload = function () { window.print(); };</` + `script>
</body></html>`;

  const w = window.open("", "_blank");
  if (!w) return false;
  w.document.write(html);
  w.document.close();
  return true;
}
