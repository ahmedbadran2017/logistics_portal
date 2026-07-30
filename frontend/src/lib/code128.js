// Code 128 (subset B) → inline SVG. No external library — the artifact CSP
// blocks CDN scripts, and the label sheet must render self-contained.
//
// The Zebra SE4710 on the floor reads Code 128, and resolve_scan() matches the
// scanned string against custom_sku first, so the payload IS the raw SKU: a
// label printed here scans back to the same item with no mapping.

// The 107 Code-128 symbol patterns, as bar/space module widths (6 per symbol,
// the standard "212222…" table). Index = code value; 103 Start-B, 106 Stop.
const PATTERNS = [
  "212222","222122","222221","121223","121322","131222","122213","122312",
  "132212","221213","221312","231212","112232","122132","122231","113222",
  "123122","123221","223211","221132","221231","213212","223112","312131",
  "311222","321122","321221","312212","322112","322211","212123","212321",
  "232121","111323","131123","131321","112313","132113","132311","211313",
  "231113","231311","112133","112331","132131","113123","113321","133121",
  "313121","211331","231131","213113","213311","213131","311123","311321",
  "331121","312113","312311","332111","314111","221411","431111","111224",
  "111422","121124","121421","141122","141221","112214","112412","122114",
  "122411","142112","142211","241211","221114","413111","241112","134111",
  "111242","121142","121241","114212","124112","124211","411212","421112",
  "421211","212141","214121","412121","111143","111341","131141","114113",
  "114311","411113","411311","113141","114131","311141","411131","211412",
  "211214","211232","2331112",
];

const START_B = 104;
const STOP = 106;

/** Encode an ASCII string (32–126) as an ordered list of Code-128 symbol
 *  values, with the mod-103 checksum. Characters outside the printable range
 *  are dropped rather than corrupting the symbol. */
function encode(text) {
  const chars = [];
  for (const ch of String(text)) {
    const c = ch.charCodeAt(0);
    if (c >= 32 && c <= 126) chars.push(c - 32);
  }
  const codes = [START_B, ...chars];
  let sum = START_B;
  chars.forEach((v, i) => { sum += v * (i + 1); });
  codes.push(sum % 103);
  codes.push(STOP);
  return codes;
}

/**
 * Build an SVG string for `text` as a Code-128B barcode.
 * @param {string} text     the payload (the SKU)
 * @param {object} [opts]
 * @param {number} [opts.height=48]  bar height in px
 * @param {number} [opts.module=1.6] width of one module in px
 * @returns {{svg:string, width:number}}  self-contained SVG + its pixel width
 */
export function code128SVG(text, opts = {}) {
  const height = opts.height || 48;
  const module = opts.module || 1.6;
  const codes = encode(text);

  // Flatten every symbol's widths into alternating bar/space runs, starting
  // with a bar. x advances by width*module; we draw only the bars.
  let x = 0;
  const rects = [];
  for (const code of codes) {
    const widths = PATTERNS[code];
    for (let i = 0; i < widths.length; i++) {
      const w = parseInt(widths[i], 10) * module;
      if (i % 2 === 0) {   // even index = bar
        rects.push(`<rect x="${x.toFixed(2)}" y="0" width="${w.toFixed(2)}" height="${height}" />`);
      }
      x += w;
    }
  }
  const width = x;
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width.toFixed(2)}" height="${height}" ` +
    `viewBox="0 0 ${width.toFixed(2)} ${height}" shape-rendering="crispEdges">` +
    `<rect width="100%" height="100%" fill="#fff"/>` +
    `<g fill="#000">${rects.join("")}</g></svg>`;
  return { svg, width };
}
