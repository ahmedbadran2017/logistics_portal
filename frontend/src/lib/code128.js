// Code 128 (subsets B and C) → inline SVG. No external library — the artifact
// CSP blocks CDN scripts, and the label sheet must render self-contained.
//
// Subset C is not an optimisation here, it is the thing that makes the label
// readable. Every character in subset B costs 11 modules; subset C encodes a
// PAIR of digits in the same 11. A 14-digit code is 189 modules in B and 112
// in C — on a 50mm label that is the difference between a 0.24mm bar (which a
// handheld will not decode) and a 0.38mm bar (which it will).
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
const START_C = 105;
const CODE_B = 100;   // switch to B from C
const CODE_C = 99;    // switch to C from B
const STOP = 106;

/** Length of the digit run starting at i. */
function digitRun(s, i) {
  let n = 0;
  while (i + n < s.length && s[i + n] >= "0" && s[i + n] <= "9") n++;
  return n;
}

/** Encode an ASCII string (32–126) as an ordered list of Code-128 symbol
 *  values, with the mod-103 checksum. Characters outside the printable range
 *  are dropped rather than corrupting the symbol. */
function encode(text) {
  // Keep only printable ASCII: anything else would corrupt the symbol.
  let t = "";
  for (const ch of String(text)) {
    const c = ch.charCodeAt(0);
    if (c >= 32 && c <= 126) t += ch;
  }

  const codes = [];
  let inC = false;
  let i = 0;
  // Start in C when the whole payload opens with an even digit run of 4+ —
  // the usual case for a numeric item code, and it saves the switch symbol.
  const lead = digitRun(t, 0);
  if (lead >= 4 || (lead === t.length && lead >= 2 && lead % 2 === 0)) {
    codes.push(START_C);
    inC = true;
  } else {
    codes.push(START_B);
  }

  while (i < t.length) {
    const run = digitRun(t, i);
    // Entering C is worth one symbol, so it pays from 4 digits (2 while
    // already in C). Only an even count can be encoded as pairs.
    const want = inC ? 2 : 4;
    if (run >= want) {
      const use = run % 2 === 0 ? run : run - 1;
      if (!inC) { codes.push(CODE_C); inC = true; }
      for (let k = 0; k < use; k += 2) codes.push(parseInt(t.substr(i + k, 2), 10));
      i += use;
      continue;
    }
    if (inC) { codes.push(CODE_B); inC = false; }
    codes.push(t.charCodeAt(i) - 32);
    i += 1;
  }

  let sum = codes[0];
  for (let k = 1; k < codes.length; k++) sum += codes[k] * k;
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
  const codes = encode(text);

  // Total module count, so a caller printing to a fixed stock can size the
  // module from the paper instead of letting CSS shrink the finished SVG —
  // which is what produced sub-0.2mm bars no scanner could read.
  let totalModules = 0;
  for (const code of codes) {
    for (const w of PATTERNS[code]) totalModules += parseInt(w, 10);
  }
  const module = opts.module || 1.6;

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
  return { svg, width, modules: totalModules };
}
