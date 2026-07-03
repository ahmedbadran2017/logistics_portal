/* global React */
// ─────────────────────────────────────────────────────────────────────
// JUSTYOL LOGISTICS PORTAL — data + i18n  (grounded in live ERPNext data)
// Source: admin.justyol.com · Sales Order / Pick List / Delivery Note /
// Shipment / Return Shipment. Morocco-first, MAD, carrier Cathedis.
// ─────────────────────────────────────────────────────────────────────

function fmtMAD(n) {
  if (n == null || isNaN(n)) return "—";
  return Math.round(n).toLocaleString("en-US");
}
function getInitial(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] || "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}
window.fmtMAD = fmtMAD;
window.getInitial = getInitial;

const WAREHOUSE = "SoftPark Aïn Sebaâ";
const CITY = "Casablanca";
const CARRIER = "Cathedis";
const CUTOFF = "14:00";
const TODAY = "2026-06-20";

// Real bin codes (Warehouse doctype, " - JM" suffix) grouped into logical zones.
const ZONES = ["FAST ZONE - JM", "SLOW ZONE - JM", "Accessory Zone - JM", "Cosmetic zone - JM", "MU Zone - JM", "Textile Zone - JM"];

// ── Sales channels (real custom_channel + naming series) ─────────────
const CHANNELS = {
  shopify:  { key: "shopify",  label: "Shopify",      tone: "emerald", prefix: "#" },
  youcan:   { key: "youcan",   label: "YouCan",       tone: "violet",  prefix: "YC-" },
  landing:  { key: "landing",  label: "Landing Page", tone: "amber",   prefix: "J-" },
  manual:   { key: "manual",   label: "Manual",       tone: "slate",   prefix: "SAL-ORD-" },
  whatsapp: { key: "whatsapp", label: "WhatsApp",     tone: "green",   prefix: "WA-" },
};
// Real channel mix (last 1,000 orders)
const CHANNEL_MIX = [
  { key: "shopify", count: 822, pct: 82 },
  { key: "landing", count: 72,  pct: 7 },
  { key: "youcan",  count: 48,  pct: 5 },
  { key: "manual",  count: 9,   pct: 1 },
];

// ── Team (real users, real pick-list volume) ─────────────────────────
const TEAM = [
  { id: "marouane", name: "Marouane El Messaoudi", short: "Marouane", role: "picker",     top: true,  email: "marouaneelmessaoudi07@gmail.com" },
  { id: "anass",    name: "Anass Mouakkal",        short: "Anass",    role: "dispatcher",             email: "mouakkalanass@gmail.com" },
  { id: "asmaa",    name: "Asmaa Zirary",          short: "Asmaa",    role: "picker",                 email: "asmaazirary7@gmail.com" },
  { id: "saad",     name: "Saad LAMDANI",          short: "Saad",     role: "picker",                 email: "lamdanisaad12@gmail.com" },
  { id: "oussama",  name: "Oussama NAHIL",         short: "Oussama",  role: "picker",                 email: "ossamanahila@gmail.com" },
  { id: "said",     name: "Said Ennakri",          short: "Said",     role: "picker",                 email: "saidnakri65@gmail.com" },
  { id: "reda",     name: "Reda ZAARI",            short: "Reda",     role: "packer",                 email: "redazaari47@gmail.com" },
  { id: "sara",     name: "Sara Benali",           short: "Sara",     role: "manager",                email: "sara.b@justyol.com" },
  { id: "nadia",    name: "Nadia Berrada",         short: "Nadia",    role: "returns",                email: "nadia.b@justyol.com" },
];
const byId = (id) => TEAM.find((t) => t.id === id) || { name: id, short: id };

// ── Stage vocab — the real custom_logistics_status flow (+ ops states)
const STAGE = {
  pending:   { key: "pending",   txt: "text-stone-600",   bg: "bg-stone-100",  ring: "ring-stone-200",   dot: "bg-stone-400",   bar: "bg-stone-400" },
  picking:   { key: "picking",   txt: "text-amber-700",   bg: "bg-amber-50",   ring: "ring-amber-200",   dot: "bg-amber-500",   bar: "bg-amber-500" },
  picked:    { key: "picked",    txt: "text-orange-700",  bg: "bg-orange-50",  ring: "ring-orange-200",  dot: "bg-orange-500",  bar: "bg-orange-500" },
  labelgen:  { key: "labelgen",  txt: "text-violet-700",  bg: "bg-violet-50",  ring: "ring-violet-200",  dot: "bg-violet-400",  bar: "bg-violet-400" },
  label:     { key: "label",     txt: "text-violet-700",  bg: "bg-violet-50",  ring: "ring-violet-200",  dot: "bg-violet-500",  bar: "bg-violet-500" },
  shipped:   { key: "shipped",   txt: "text-emerald-700", bg: "bg-emerald-50", ring: "ring-emerald-200", dot: "bg-emerald-500", bar: "bg-emerald-500" },
  transit:   { key: "transit",   txt: "text-cyan-700",    bg: "bg-cyan-50",    ring: "ring-cyan-200",    dot: "bg-cyan-500",    bar: "bg-cyan-500" },
  exception: { key: "exception", txt: "text-orange-700",  bg: "bg-orange-50",  ring: "ring-orange-200",  dot: "bg-orange-500",  bar: "bg-orange-500" },
  delivered: { key: "delivered", txt: "text-emerald-700", bg: "bg-emerald-50", ring: "ring-emerald-200", dot: "bg-emerald-500", bar: "bg-emerald-500" },
  returned:  { key: "returned",  txt: "text-rose-700",    bg: "bg-rose-50",    ring: "ring-rose-200",    dot: "bg-rose-500",    bar: "bg-rose-500" },
  oos:       { key: "oos",       txt: "text-rose-700",    bg: "bg-rose-50",    ring: "ring-rose-200",    dot: "bg-rose-500",    bar: "bg-rose-500" },
  partial:   { key: "partial",   txt: "text-amber-700",   bg: "bg-amber-50",   ring: "ring-amber-200",   dot: "bg-amber-500",   bar: "bg-amber-500" },
};
const SLA = {
  ontrack:  { key: "ontrack",  txt: "text-emerald-700", bg: "bg-emerald-50", ring: "ring-emerald-200", dot: "bg-emerald-500", stroke: "#10b981" },
  atrisk:   { key: "atrisk",   txt: "text-amber-700",   bg: "bg-amber-50",   ring: "ring-amber-200",   dot: "bg-amber-500",   stroke: "#f59e0b" },
  breached: { key: "breached", txt: "text-rose-700",    bg: "bg-rose-50",    ring: "ring-rose-200",    dot: "bg-rose-500",    stroke: "#ef4444" },
  late:     { key: "late",     txt: "text-orange-700",  bg: "bg-orange-50",  ring: "ring-orange-200",  dot: "bg-orange-500",  stroke: "#f97316" },
  returned: { key: "returned", txt: "text-stone-600",   bg: "bg-stone-100",  ring: "ring-stone-200",   dot: "bg-stone-400",   stroke: "#a8a29e" },
};

// ── Pipeline funnel — real custom_logistics_status counts (last 1,000)
const PIPELINE = [
  { key: "pending",   count: 147, value: 22050 },
  { key: "picking",   count: 62,  value: 9300 },
  { key: "picked",    count: 33,  value: 5180 },
  { key: "labelgen",  count: 6,   value: 894 },
  { key: "label",     count: 230, value: 34270 },
  { key: "shipped",   count: 247, value: 38830 },
  { key: "transit",   count: 206, value: 32140 },
  { key: "delivered", count: 354, value: 56120 },
  { key: "returned",  count: 16,  value: 2390 },
];

// ── Orders — real customers / IDs / channels / AWBs / bins ───────────
// stage∈STAGE · sla∈SLA · channel∈CHANNELS · track∈TRACK_STATES
const ORDERS = [
  // pending — to assign / pick
  { no: "#242646", channel: "shopify", customer: "oualid elmouden",   total: 149,   items: 1, stage: "pending",   sla: "atrisk",   bin: "J8C - JM",  zone: "FAST ZONE - JM",     picker: null,       mins: 41,  awb: null,          dn: null, track: null },
  { no: "#242644", channel: "shopify", customer: "Chada Rami",        total: 198,   items: 2, stage: "pending",   sla: "ontrack",  bin: "H14A - JM", zone: "Accessory Zone - JM",picker: null,       mins: 12,  awb: null,          dn: null, track: null },
  { no: "#242641", channel: "shopify", customer: "Hamid Hamid",       total: 224,   items: 1, stage: "pending",   sla: "atrisk",   bin: "F13C - JM", zone: "Textile Zone - JM",  picker: null,       mins: 28,  awb: null,          dn: null, track: null },
  { no: "SAL-ORD-2026-00299", channel: "manual", customer: "Salma",   total: 149,   items: 1, stage: "pending",   sla: "ontrack",  bin: "J7B - JM",  zone: "FAST ZONE - JM",     picker: null,       mins: 8,   awb: null,          dn: null, track: null },
  { no: "#242638", channel: "shopify", customer: "Mohmad Mohmad",     total: 89,    items: 1, stage: "oos",       sla: "breached", bin: "I4A - JM",  zone: "Cosmetic zone - JM", picker: "asmaa",    mins: 158, awb: null,          dn: null, track: null },
  // picking
  { no: "#242629", channel: "shopify", customer: "Sara Razine",       total: 129,   items: 1, stage: "picking",   sla: "ontrack",  bin: "J8A - JM",  zone: "FAST ZONE - JM",     picker: "marouane", mins: 19,  awb: null,          dn: null, track: null },
  { no: "#242637", channel: "shopify", customer: "Nezili kaoutar",    total: 149,   items: 1, stage: "picking",   sla: "atrisk",   bin: "H13B - JM", zone: "MU Zone - JM",       picker: "asmaa",    mins: 47,  awb: null,          dn: null, track: null },
  { no: "#242640", channel: "shopify", customer: "Redouane Redouane", total: 149,   items: 1, stage: "picking",   sla: "ontrack",  bin: "F14A - JM", zone: "SLOW ZONE - JM",     picker: "said",     mins: 33,  awb: null,          dn: null, track: null },
  // picked
  { no: "#242633", channel: "shopify", customer: "Amal Mourid",       total: 104.5, items: 1, stage: "picked",    sla: "ontrack",  bin: "F14B - JM", zone: "Textile Zone - JM",  picker: "marouane", mins: 12,  awb: null,          dn: null, track: null },
  { no: "YC-000169",channel: "youcan",  customer: "Ghizlane Dargal",   total: 129,   items: 1, stage: "picked",    sla: "ontrack",  bin: "J8C - JM",  zone: "FAST ZONE - JM",     picker: "saad",     mins: 22,  awb: null,          dn: null, track: null },
  // label printed (ready for manifest)
  { no: "#242449", channel: "shopify", customer: "Abbes kalila",      total: 144,   items: 1, stage: "label",     sla: "ontrack",  bin: "H14C - JM", zone: "Accessory Zone - JM",picker: "oussama",  mins: 70,  awb: "LD007758605", dn: "MAT-DN-2026-77111", track: "pending" },
  { no: "J-000117", channel: "landing", customer: "Rahma",            total: 149,   items: 1, stage: "label",     sla: "ontrack",  bin: "J7C - JM",  zone: "FAST ZONE - JM",     picker: "marouane", mins: 54,  awb: "LD007758527", dn: "MAT-DN-2026-77098", track: "pending", city: "Tangier" },
  { no: "#242616", channel: "shopify", customer: "Zineb Zineb",       total: 248,   items: 2, stage: "label",     sla: "atrisk",   bin: "F13A - JM", zone: "Textile Zone - JM",  picker: "asmaa",    mins: 96,  awb: "LD007758401", dn: "MAT-DN-2026-77070", track: "pending" },
  // shipped (on today's manifest)
  { no: "#242624", channel: "shopify", customer: "Widad Widad",       total: 218,   items: 2, stage: "shipped",   sla: "ontrack",  bin: "H13C - JM", zone: "Cosmetic zone - JM", picker: "marouane", mins: 0,   awb: "LD007758377", dn: "MAT-DN-2026-77041", track: "pickedup" },
  { no: "YC-000162",channel: "youcan",  customer: "Hind El Yazami",    total: 149,   items: 1, stage: "shipped",   sla: "ontrack",  bin: "J8B - JM",  zone: "FAST ZONE - JM",     picker: "saad",     mins: 0,   awb: "LD007758537", dn: "MAT-DN-2026-77052", track: "pickedup" },
  // in transit / OFD
  { no: "#241631", channel: "shopify", customer: "Khiyal Khiyal",     total: 154,   items: 1, stage: "transit",   sla: "ontrack",  bin: "F14C - JM", zone: "SLOW ZONE - JM",     picker: "oussama",  mins: 0,   awb: "LD007741906", dn: "MAT-DN-2026-75641", track: "outfordelivery" },
  { no: "#242323", channel: "shopify", customer: "Nezha ghazi",       total: 169,   items: 1, stage: "transit",   sla: "ontrack",  bin: "H14B - JM", zone: "MU Zone - JM",       picker: "marouane", mins: 0,   awb: "LD007753630", dn: "MAT-DN-2026-76402", track: "intransit" },
  // exceptions
  { no: "#242128", channel: "shopify", customer: "Fatima Fatima",     total: 129,   items: 1, stage: "exception", sla: "late",     bin: "J7A - JM",  zone: "FAST ZONE - JM",     picker: "asmaa",    mins: 0,   awb: "LD007748688", dn: "MAT-DN-2026-75988", track: "exception" },
  { no: "#240682", channel: "shopify", customer: "Edghir hanane",     total: 144,   items: 1, stage: "exception", sla: "breached", bin: "F13B - JM", zone: "Textile Zone - JM",  picker: "said",     mins: 0,   awb: "LD007744422", dn: "MAT-DN-2026-75112", track: "failed" },
  // delivered
  { no: "#242232", channel: "shopify", customer: "Hiba Hiba",         total: 149,   items: 1, stage: "delivered", sla: "ontrack",  bin: "J8A - JM",  zone: "FAST ZONE - JM",     picker: "marouane", mins: 0,   awb: "LD007751548", dn: "MAT-DN-2026-76645", track: "delivered" },
];

// ── Pick lists (real PL series, custom_assigned_picker, scan) ────────
const PICKLISTS = [
  { no: "PL-51405", customer: "Combined · 8 orders", sku: "—", item: "Combined pick", bin: "Multiple", qty: 43, items: 8, status: "draft",     pct: 0,   picker: "reda",     order: "combined" },
  { no: "PL-51404", customer: "Combined · 5 orders", sku: "—", item: "Combined pick", bin: "Multiple", qty: 19, items: 5, status: "completed", pct: 100, picker: "anass",    order: "combined" },
  { no: "PL-51402", customer: "Combined · 4 orders", sku: "—", item: "Combined pick", bin: "Multiple", qty: 11, items: 4, status: "draft",     pct: 0,   picker: "saad",     order: "combined" },
  { no: "PL-51433", customer: "Sara Razine",         sku: "MCH100013", item: "Diffuseur huile MCH — box", bin: "J8A - JM", qty: 1, items: 1, status: "open", pct: 0,  picker: "marouane", order: "#242629" },
  { no: "PL-51388", customer: "Nezili kaoutar",      sku: "MUZ22014",  item: "Palette ombres MU",         bin: "H13B - JM",qty: 1, items: 1, status: "open", pct: 50, picker: "asmaa",    order: "#242637", errors: true },
  { no: "PL-51381", customer: "Combined · 3 orders", sku: "—", item: "Combined pick", bin: "Multiple", qty: 9,  items: 3, status: "completed", pct: 100, picker: "marouane", order: "combined" },
  { no: "PL-51324", customer: "Combined · 6 orders", sku: "—", item: "Combined pick", bin: "Multiple", qty: 27, items: 6, status: "completed", pct: 100, picker: "asmaa",    order: "combined" },
];

// ── Picker scan flow — line items for active order ───────────────────
const PICK_ITEMS = [
  { sku: "MCH100013", name: "Diffuseur huile MCH — box", bin: "J8C - JM", qty: 1, scanned: false },
  { sku: "CSM44021",  name: "Sérum éclat 30ml",          bin: "F14B - JM",qty: 1, scanned: false },
  { sku: "ACC11008",  name: "Trousse maquillage zip",    bin: "H14A - JM",qty: 1, scanned: false },
];

// ── Delivery notes / parcels (real MAT-DN series, AWBs, track) ───────
const PARCELS = [
  { dn: "MAT-DN-2026-75641", awb: "LD007741906", trackNo: "CTH7741906MA", order: "#241631", customer: "Khiyal Khiyal",  carrier: CARRIER, track: "outfordelivery", sla: "ontrack", value: 154, days: 0, msg: "Out for delivery — Casablanca hub" },
  { dn: "MAT-DN-2026-76645", awb: "LD007751548", trackNo: "CTH7751548MA", order: "#242232", customer: "Hiba Hiba",      carrier: CARRIER, track: "delivered",      sla: "ontrack", value: 149, days: 0, msg: "Delivered — signed by recipient" },
  { dn: "MAT-DN-2026-75988", awb: "LD007748688", trackNo: "CTH7748688MA", order: "#242128", customer: "Fatima Fatima",  carrier: CARRIER, track: "exception",      sla: "late",    value: 129, days: -1, msg: "Address not found — phone unreachable" },
  { dn: "MAT-DN-2026-76402", awb: "LD007753630", trackNo: "CTH7753630MA", order: "#242323", customer: "Nezha ghazi",    carrier: CARRIER, track: "intransit",      sla: "ontrack", value: 169, days: 1, msg: "In transit — departed Casablanca sort facility" },
  { dn: "MAT-DN-2026-75112", awb: "LD007744422", trackNo: "CTH7744422MA", order: "#240682", customer: "Edghir hanane",  carrier: CARRIER, track: "failed",         sla: "breached",value: 144, days: -2, msg: "2nd failed attempt — recipient absent" },
  { dn: "MAT-DN-2026-77041", awb: "LD007758377", trackNo: "CTH7758377MA", order: "#242624", customer: "Widad Widad",    carrier: CARRIER, track: "pickedup",       sla: "ontrack", value: 218, days: 2, msg: "Picked up by carrier" },
];
const TRACK_STATES = ["pending", "pickedup", "intransit", "outfordelivery", "delivered", "exception", "failed", "return"];
// real DN track distribution (last 1,000)
const TRACK_COUNTS = { pending: 311, pickedup: 0, intransit: 48, outfordelivery: 218, delivered: 355, exception: 48, failed: 18, return: 16 };

// ── Today's manifest (real Shipment SH-000179, building) ─────────────
const MANIFEST = {
  no: "SH-000179", parcels: 242, value: 38420, carrier: CARRIER,
  pickupDate: TODAY, window: "09:00 – 17:00", cutoff: CUTOFF, status: "Draft",
};
const RECENT_MANIFESTS = [
  { no: "SH-000178", date: "2026-06-19", parcels: 287, value: 44310, status: "Submitted" },
  { no: "SH-000177", date: "2026-06-18", parcels: 263, value: 39950, status: "Submitted" },
  { no: "SH-000176", date: "2026-06-17", parcels: 301, value: 47120, status: "Submitted" },
];
// Label / print queue — orders Picked → ready for AWB
const LABEL_QUEUE = [
  { order: "#242633", customer: "Amal Mourid",    channel: "shopify", parcels: 1, value: 104.5,printed: false, sla: "ontrack" },
  { order: "YC-000169",customer: "Ghizlane Dargal",channel: "youcan",  parcels: 1, value: 129,  printed: false, sla: "ontrack" },
  { order: "#242449", customer: "Abbes kalila",   channel: "shopify", parcels: 1, value: 144,  printed: true,  sla: "ontrack" },
  { order: "#242616", customer: "Zineb Zineb",    channel: "shopify", parcels: 2, value: 248,  printed: false, sla: "atrisk" },
  { order: "J-000117",customer: "Rahma",          channel: "landing", parcels: 1, value: 149,  printed: true,  sla: "ontrack" },
];

// ── Returns (real RET series) ────────────────────────────────────────
const RETURNS = [
  { no: "RET-26-3139461", order: "#242088", customer: "Salwa Tahiri",   reason: "wrong_size",   sku: "TXT55012", value: 320, state: "open",    awb: "LD007754880" },
  { no: "RET-26-3137317", order: "#242201", customer: "Nada Squalli",   reason: "defective",    sku: "CSM44021", value: 480, state: "inspect", awb: "LD007752310" },
  { no: "RET-26-3098119", order: "#241955", customer: "Khadija abhaoui",reason: "changed_mind", sku: "ACC11008", value: 150, state: "restock", awb: "LD007740021" },
  { no: "RET-26-3089472", order: "#241803", customer: "Ouidad Ziani",   reason: "defective",    sku: "CSM44021", value: 480, state: "closed",  awb: "LD007731556" },
  { no: "RET-26-3085412", order: "#241744", customer: "Imane Berrada",  reason: "not_as_described", sku: "MUZ22014", value: 210, state: "open", awb: "LD007728904" },
];
const RETURN_REASONS = { wrong_size: "Wrong size", defective: "Defective", changed_mind: "Changed mind", not_as_described: "Not as described" };

// ── Performance / leaderboard (real pickers, scaled daily) ───────────
const LEADERBOARD = [
  { id: "marouane", picks: 34, avg: "2m10s", sla: 94, rank: 1, trend: [26,29,28,31,33,32,34], target: 40 },
  { id: "anass",    picks: 27, avg: "2m22s", sla: 91, rank: 2, trend: [22,24,25,26,25,27,27], target: 40 },
  { id: "asmaa",    picks: 22, avg: "2m31s", sla: 89, rank: 3, trend: [18,20,21,20,22,21,22], target: 40 },
  { id: "saad",     picks: 18, avg: "2m48s", sla: 86, rank: 4, trend: [15,16,17,16,18,17,18], target: 40 },
  { id: "oussama",  picks: 15, avg: "3m02s", sla: 83, rank: 5, trend: [12,13,14,13,15,14,15], target: 40 },
  { id: "said",     picks: 12, avg: "3m18s", sla: 80, rank: 6, trend: [14,12,11,12,11,13,12], target: 40 },
];

// ── Audit feed (Layer A rule alerts + Layer B LLM insights) ──────────
const AUDIT = [
  { sev: "red",    kind: "alert", t: "4m",  title: "SLA breached",       body: "Order #242638 · Mohmad Mohmad has been Out of Stock 2h38m in Cosmetic zone — past the 14:00 cutoff.", action: "Reassign", order: "#242638" },
  { sev: "orange", kind: "alert", t: "12m", title: "Failed delivery",     body: "AWB LD007744422 (#240682 · Edghir hanane) — Cathedis logged a Failed Attempt. 2nd in 24h.", action: "Open order", order: "#240682" },
  { sev: "orange", kind: "alert", t: "26m", title: "Carrier exception",   body: "AWB LD007748688 (#242128 · Fatima Fatima) flagged Delivery Exception by Cathedis.", action: "Open order", order: "#242128" },
  { sev: "yellow", kind: "alert", t: "38m", title: "Manifest cutoff risk", body: "3 picked orders not yet labeled — SH-000179 cutoff in 1h 40m.", action: "View queue", order: null },
  { sev: "insight",kind: "note",  t: "1h",  title: "Daily insight", body: "Said's pick time rose ~22% after 16:00 three days running — likely fatigue on the SLOW zone. Consider rotating him off late-shift.", action: null, order: null },
  { sev: "insight",kind: "note",  t: "1h",  title: "Daily insight", body: "Returns for SKU CSM44021 are +40% this week, all flagged ‘defective’ — worth a supplier quality check.", action: null, order: null },
];

// ── Inventory / Zone restock (real bin codes) ────────────────────────
const RESTOCK = [
  { zone: "FAST ZONE - JM",      bins: ["J7A","J7B","J7C","J8A","J8B","J8C"], skus: 142, low: 6, out: 1, blocking: 1, fill: 0.86 },
  { zone: "SLOW ZONE - JM",      bins: ["F13A","F13B","F13C","F14A","F14B","F14C"], skus: 98, low: 3, out: 0, blocking: 0, fill: 0.93 },
  { zone: "Cosmetic zone - JM",  bins: ["I4A","I4B","H13A","H13B"], skus: 64, low: 8, out: 2, blocking: 1, fill: 0.71 },
  { zone: "MU Zone - JM",        bins: ["H13C","H14A","H14B","H14C"], skus: 51, low: 4, out: 1, blocking: 0, fill: 0.79 },
  { zone: "Accessory Zone - JM", bins: ["I4A","H14A"], skus: 38, low: 2, out: 0, blocking: 0, fill: 0.90 },
  { zone: "Textile Zone - JM",   bins: ["F13A","F13B","F13C"], skus: 44, low: 1, out: 0, blocking: 0, fill: 0.95 },
];
const RESTOCK_ITEMS = [
  { sku: "CSM44021", name: "Sérum éclat 30ml",          bin: "I4A - JM",  zone: "Cosmetic zone - JM", onHand: 0,  reorder: 24, demand: 11, state: "out" },
  { sku: "ACC11008", name: "Trousse maquillage zip",    bin: "H14A - JM", zone: "Accessory Zone - JM",onHand: 3,  reorder: 20, demand: 7,  state: "low" },
  { sku: "MUZ22014", name: "Palette ombres MU",         bin: "H13B - JM", zone: "MU Zone - JM",       onHand: 2,  reorder: 18, demand: 9,  state: "low" },
  { sku: "MCH100013",name: "Diffuseur huile MCH — box", bin: "J8C - JM",  zone: "FAST ZONE - JM",     onHand: 41, reorder: 30, demand: 12, state: "ok" },
  { sku: "TXT55012", name: "Foulard soie imprimé",      bin: "F13C - JM", zone: "Textile Zone - JM",  onHand: 7,  reorder: 12, demand: 4,  state: "low" },
];

// ── Order full-cycle timeline — generated per order, deterministic ───
// Returns the ERPNext doc trail: Sales Order → Pick List → Label → Manifest
// → Carrier events → Delivered/Returned, each with actor, doc ref, time.
const STAGE_SEQ = ["pending","picking","picked","labelgen","label","shipped","transit","exception","delivered","returned"];
function orderTimeline(o) {
  if (!o) return [];
  const idx = STAGE_SEQ.indexOf(o.stage);
  const pk = byId(o.picker)?.short;
  const t = (h, m) => `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}`;
  let h = 8, m = (parseInt((o.no.match(/\d+/)||[7])[0]) % 5) * 9 + 4;
  const step = () => { m += 17 + (idx % 6); if (m >= 60) { h += 1; m -= 60; } return t(h, m); };
  const all = [
    { key: "confirmed", label: "Order confirmed",   actor: "Sales · " + o.channel, doc: o.no,  reached: 0 },
    { key: "picking",   label: "Pick list assigned",actor: pk || "Dispatcher",     doc: "PL-51433", reached: 1 },
    { key: "picked",    label: "Picked & scanned",  actor: pk || "—",              doc: "PL-51433", reached: 2 },
    { key: "labelgen",  label: "Label generated",   actor: "Reda · Cathedis API",  doc: o.awb || "AWB", reached: 3 },
    { key: "label",     label: "Label printed",     actor: "Reda",                 doc: o.awb || "AWB", reached: 4 },
    { key: "shipped",   label: "On manifest",        actor: "Reda",                doc: MANIFEST.no, reached: 5 },
    { key: "transit",   label: "Picked up by carrier",actor: "Cathedis",           doc: o.awb || "AWB", reached: 6 },
    { key: "oos",       label: "Out of stock — blocked", actor: pk || "—",          doc: o.bin, reached: 2, bad: true },
    { key: "exception", label: o.track === "failed" ? "Failed attempt" : "Delivery exception", actor: "Cathedis", doc: o.awb || "AWB", reached: 7, bad: true },
    { key: "delivered", label: "Delivered",          actor: "Cathedis",            doc: o.awb || "AWB", reached: 8 },
    { key: "returned",  label: "Returned",           actor: "Cathedis",            doc: o.awb || "AWB", reached: 9, bad: true },
  ];
  const isException = o.stage === "exception";
  const isOos = o.stage === "oos";
  return all
    .filter((e) => {
      if (e.key === "oos") return isOos;
      if (isOos) return e.reached <= 1;
      if (e.key === "exception") return isException;
      if (e.key === "returned") return o.stage === "returned";
      if (e.key === "delivered") return idx >= 8 && o.stage !== "returned";
      return e.reached <= idx || (isException && e.reached <= 6);
    })
    .map((e) => ({ ...e, at: step(), done: true }));
}

// ── Shipments (real Shipment series, daily carrier handover) ─────────
const SHIPMENTS = [
  { no: "SH-000179", date: TODAY,        parcels: 242, value: 38420, carrier: CARRIER, status: "Draft",     window: "09:00 – 17:00", delivered: 0,   exceptions: 0, weight: 312, pallets: 4, incoterm: "DAP", shipType: "Domestic parcel", service: "Cathedis Express", awb: "—", pickup: "SoftPark Aïn Sebaâ — Dock 1", pickupContact: "Reda ZAARI · +212 661 22 18", deliveryTo: "Cathedis Hub · Casablanca" },
  { no: "SH-000178", date: "2026-06-19", parcels: 287, value: 44310, carrier: CARRIER, status: "Submitted", window: "09:00 – 17:00", delivered: 198, exceptions: 12, weight: 368, pallets: 5, incoterm: "DAP", shipType: "Domestic parcel", service: "Cathedis Express", awb: "CTH-MNF-77841", pickup: "SoftPark Aïn Sebaâ — Dock 1", pickupContact: "Reda ZAARI · +212 661 22 18", deliveryTo: "Cathedis Hub · Casablanca" },
  { no: "SH-000177", date: "2026-06-18", parcels: 263, value: 39950, carrier: CARRIER, status: "Submitted", window: "09:00 – 17:00", delivered: 241, exceptions: 9, weight: 334, pallets: 4, incoterm: "DAP", shipType: "Domestic parcel", service: "Cathedis Express", awb: "CTH-MNF-77702", pickup: "SoftPark Aïn Sebaâ — Dock 1", pickupContact: "Reda ZAARI · +212 661 22 18", deliveryTo: "Cathedis Hub · Casablanca" },
  { no: "SH-000176", date: "2026-06-17", parcels: 301, value: 47120, carrier: CARRIER, status: "Booked",    window: "09:00 – 17:00", delivered: 289, exceptions: 7, weight: 391, pallets: 5, incoterm: "DAP", shipType: "Domestic parcel", service: "Cathedis Express", awb: "CTH-MNF-77588", pickup: "SoftPark Aïn Sebaâ — Dock 1", pickupContact: "Reda ZAARI · +212 661 22 18", deliveryTo: "Cathedis Hub · Casablanca" },
  { no: "SH-000175", date: "2026-06-16", parcels: 274, value: 41880, carrier: CARRIER, status: "Completed", window: "09:00 – 17:00", delivered: 268, exceptions: 4, weight: 356, pallets: 4, incoterm: "DAP", shipType: "Domestic parcel", service: "Cathedis Express", awb: "CTH-MNF-77410", pickup: "SoftPark Aïn Sebaâ — Dock 1", pickupContact: "Reda ZAARI · +212 661 22 18", deliveryTo: "Cathedis Hub · Casablanca" },
];

// ── Carriers (Cathedis live; others configured) ──────────────────────
const CARRIERS = [
  { name: "Cathedis", code: "CTH", active: true,  awbActive: 565, deliveryRate: 91.2, exceptionRate: 4.8, avgTransit: "1.8d", zones: "All Morocco", primary: true },
  { name: "Sendit",   code: "SND", active: false, awbActive: 0,   deliveryRate: 0,    exceptionRate: 0,   avgTransit: "—",   zones: "Casablanca · Rabat", primary: false },
  { name: "Ozonexpress", code: "OZN", active: false, awbActive: 0, deliveryRate: 0,   exceptionRate: 0,   avgTransit: "—",   zones: "National",  primary: false },
];

// ── Return Shipments — real bulk carrier-return batches ──────────────
const RETURN_BATCHES = [
  { no: "RET-26-3139461", date: "2026-06-18", orders: 306, qty: 434, missing: 0, pct: 100, status: "Returned",      owner: "anass",   reconciled: true,  awbScanned: 306, itemsScanned: 434 },
  { no: "RET-26-3137317", date: "2026-06-17", orders: 188, qty: 271, missing: 3, pct: 98,  status: "Item Scanning", owner: "nadia",   reconciled: false, awbScanned: 188, itemsScanned: 244, missingSkus: ["CSM44021", "MUZ22014"] },
  { no: "RET-26-3098119", date: "2026-06-15", orders: 142, qty: 205, missing: 0, pct: 100, status: "Returned",      owner: "oussama", reconciled: true,  awbScanned: 142, itemsScanned: 205 },
  { no: "RET-26-3089472", date: "2026-06-13", orders: 97,  qty: 138, missing: 1, pct: 99,  status: "AWB Scanning",  owner: "nadia",   reconciled: false, awbScanned: 61,  itemsScanned: 0, missingSkus: ["ACC11008"] },
];
// Return Shipment line items (real Return Shipment Item shape)
const RETURN_ITEMS = [
  { dn: "MAT-DN-2026-68961", awb: "7585029", code: "45779757236478", sku: "MCH100013", name: "Set 12 pots à épices — Gris", ordered: 1, actual: 1, complete: true },
  { dn: "MAT-DN-2026-68940", awb: "7585011", code: "46029811200334", sku: "CSM44021", name: "Sérum éclat 30ml", ordered: 2, actual: 1, complete: false },
  { dn: "MAT-DN-2026-68922", awb: "7584998", code: "46772200140088", sku: "MUZ22014", name: "Palette ombres MU", ordered: 1, actual: 0, complete: false },
  { dn: "MAT-DN-2026-68910", awb: "7584977", code: "47594099441918", sku: "ACC11008", name: "Trousse maquillage zip", ordered: 1, actual: 1, complete: true },
  { dn: "MAT-DN-2026-68901", awb: "7584960", code: "46881234500021", sku: "TXT55012", name: "Foulard soie imprimé", ordered: 1, actual: 1, complete: true },
];
const RS_STATUS = { Draft: "neutral", "AWB Scanning": "amber", "Item Scanning": "blue", "Ready for Return": "purple", Returned: "green", Cancelled: "red" };

// ── Inventory / stock levels (Stores - JM + zone bins) ───────────────
const STOCK_STATS = { skuCount: 437, totalUnits: 18420, totalValue: 1284500, lowSku: 24, outSku: 4, deadSku: 12, reserved: 612, turnover: 6.4 };
const STOCK_ITEMS = [
  { sku: "MCH100013", name: "Diffuseur huile MCH — box", zone: "FAST ZONE - JM",     bin: "J8C - JM",  onHand: 41, reserved: 6,  available: 35, reorder: 30, value: 4920, state: "ok" },
  { sku: "CSM44021",  name: "Sérum éclat 30ml",          zone: "Cosmetic zone - JM", bin: "I4A - JM",  onHand: 0,  reserved: 0,  available: 0,  incoming: 24, reorder: 24, value: 0,    state: "out" },
  { sku: "ACC11008",  name: "Trousse maquillage zip",    zone: "Accessory Zone - JM",bin: "H14A - JM", onHand: 3,  reserved: 2,  available: 1,  incoming: 20, reorder: 20, value: 450,  state: "low" },
  { sku: "MUZ22014",  name: "Palette ombres MU",         zone: "MU Zone - JM",       bin: "H13B - JM", onHand: 2,  reserved: 1,  available: 1,  reorder: 18, value: 360,  state: "low" },
  { sku: "TXT55012",  name: "Foulard soie imprimé",      zone: "Textile Zone - JM",  bin: "F13C - JM", onHand: 7,  reserved: 0,  available: 7,  reorder: 12, value: 1120, state: "low" },
  { sku: "MCH100020", name: "Recharge huile lavande",    zone: "FAST ZONE - JM",     bin: "J7B - JM",  onHand: 58, reserved: 4,  available: 54, reorder: 25, value: 6960, state: "ok" },
  { sku: "ACC11015",  name: "Miroir LED pliable",        zone: "Accessory Zone - JM",bin: "H14C - JM", onHand: 22, reserved: 3,  available: 19, reorder: 15, value: 3300, state: "ok" },
];

// ── Restock tasks (move stock zone → bin) ────────────────────────────
const RESTOCK_TASKS = [
  { id: "RT-2041", sku: "CSM44021", name: "Sérum éclat 30ml",       from: "Stores - JM", to: "I4A - JM",  qty: 24, assignee: "oussama", status: "pending",    priority: "high" },
  { id: "RT-2040", sku: "ACC11008", name: "Trousse maquillage zip", from: "Stores - JM", to: "H14A - JM", qty: 20, assignee: "saad",    status: "inprogress", priority: "high" },
  { id: "RT-2039", sku: "MUZ22014", name: "Palette ombres MU",      from: "Stores - JM", to: "H13B - JM", qty: 18, assignee: "oussama", status: "inprogress", priority: "med" },
  { id: "RT-2038", sku: "TXT55012", name: "Foulard soie imprimé",   from: "Stores - JM", to: "F13C - JM", qty: 12, assignee: "saad",    status: "pending",    priority: "med" },
  { id: "RT-2035", sku: "MCH100020",name: "Recharge huile lavande", from: "Stores - JM", to: "J7B - JM",  qty: 30, assignee: "marouane",status: "done",       priority: "low" },
];

// ── Stock analysis ───────────────────────────────────────────────────
const TOP_MOVERS = [
  { sku: "MCH100013", name: "Diffuseur huile MCH — box", sold7d: 312, trend: [38,42,40,45,48,49,50], zone: "FAST ZONE - JM" },
  { sku: "CSM44021",  name: "Sérum éclat 30ml",          sold7d: 268, trend: [30,34,36,38,40,42,48], zone: "Cosmetic zone - JM" },
  { sku: "MCH100020", name: "Recharge huile lavande",    sold7d: 201, trend: [24,26,28,30,29,31,33], zone: "FAST ZONE - JM" },
  { sku: "ACC11015",  name: "Miroir LED pliable",        sold7d: 154, trend: [18,20,22,21,23,24,26], zone: "Accessory Zone - JM" },
];
const DEAD_STOCK = [
  { sku: "TXT55088", name: "Châle hiver laine",      zone: "Textile Zone - JM", onHand: 64, idle: 52, value: 9600 },
  { sku: "ACC11042", name: "Étui lunettes cuir",     zone: "Accessory Zone - JM", onHand: 38, idle: 47, value: 4180 },
  { sku: "MUZ22030", name: "Vernis collection été",  zone: "MU Zone - JM",      onHand: 91, idle: 41, value: 5460 },
];
const RETURN_BY_SKU = [
  { sku: "CSM44021", name: "Sérum éclat 30ml",       rate: 8.4, count: 22, reason: "Defective" },
  { sku: "MUZ22014", name: "Palette ombres MU",      rate: 5.1, count: 13, reason: "Not as described" },
  { sku: "TXT55012", name: "Foulard soie imprimé",   rate: 3.8, count: 9,  reason: "Wrong size" },
];

// ── SLA breakdowns (the computed Pillar-1 layer) ─────────────────────
const SLA_BY_STAGE = [
  { key: "pending",  hit: 88 }, { key: "picking", hit: 92 }, { key: "picked", hit: 95 },
  { key: "label",    hit: 90 }, { key: "shipped", hit: 87 }, { key: "transit", hit: 84 }, { key: "delivered", hit: 91 },
];
const SLA_STATS = { sameDay: 87, breached: 2, atRisk: 4, deliveredLate: 18, avgShipHrs: 5.4, target: 95 };
// Today's floor flow (real ERPNext snapshot — orders in vs shipped vs pending) 
const TODAY_FLOW = { intake: 328, shipped: 124, pending: 205, labeled: 19, cutoff: "14:00" };
// Delivery SLA — carrier promise, from custom_sla_days_remaining buckets (computed layer)
const SLA_DELIVERY = { onTime: 89, buckets: [
  { key: "overdue",  label: "Overdue",   count: 14, tone: "bg-rose-500",    txt: "text-rose-600" },
  { key: "today",    label: "Due today", count: 38, tone: "bg-amber-500",   txt: "text-amber-600" },
  { key: "d1",       label: "1 day",     count: 91, tone: "bg-cyan-500",    txt: "text-cyan-600" },
  { key: "d2",       label: "2 days",    count: 64, tone: "bg-emerald-400", txt: "text-emerald-600" },
  { key: "d3",       label: "3+ days",   count: 47, tone: "bg-emerald-500", txt: "text-emerald-600" },
] };

// ── Team admin — capabilities, members, classification, perms ────────
const CAPS = [
  { key: "assign",     label: "Assign work",    icon: I.Layers },
  { key: "pick",       label: "Pick orders",    icon: I.Box },
  { key: "pack_label", label: "Pack & label",   icon: I.Tag },
  { key: "ship",       label: "Create shipment",icon: I.Send },
  { key: "returns",    label: "Process returns",icon: I.Return },
  { key: "inventory",  label: "Inventory",      icon: I.Inventory },
  { key: "reports",    label: "View reports",   icon: I.TrendUp },
  { key: "admin",      label: "Admin & team",   icon: I.Shield },
];
const TIERS = { top: { label: "Top performer", tone: "green" }, steady: { label: "Steady", tone: "blue" }, coaching: { label: "Coaching", tone: "amber" } };
const MEMBER_STATUS = { active: { label: "Active", tone: "green" }, idle: { label: "Idle", tone: "yellow" }, offline: { label: "Offline", tone: "neutral" } };

const TEAM_MEMBERS = [
  { id: "marouane", role: "picker",     tier: "top",      shift: "Morning", zones: ["FAST ZONE - JM", "Textile Zone - JM"], status: "active",  joined: "2024-09", perms: ["pick", "reports"], perf: { count: 34, unit: "picks", avg: "2m10s", sla: 94, rank: 1, trend: [26,29,28,31,33,32,34] } },
  { id: "anass",    role: "dispatcher", tier: "top",      shift: "Full day",zones: ["All zones"],                          status: "active",  joined: "2024-06", perms: ["assign", "pick", "reports"], perf: { count: 27, unit: "picks", avg: "2m22s", sla: 91, rank: 2, trend: [22,24,25,26,25,27,27] } },
  { id: "asmaa",    role: "picker",     tier: "steady",   shift: "Morning", zones: ["Cosmetic zone - JM", "MU Zone - JM"], status: "active",  joined: "2025-01", perms: ["pick"], perf: { count: 22, unit: "picks", avg: "2m31s", sla: 89, rank: 3, trend: [18,20,21,20,22,21,22] } },
  { id: "saad",     role: "picker",     tier: "coaching", shift: "Evening", zones: ["SLOW ZONE - JM"],                     status: "idle",    joined: "2025-03", perms: ["pick"], perf: { count: 18, unit: "picks", avg: "2m48s", sla: 86, rank: 4, trend: [15,16,17,16,18,17,18] } },
  { id: "oussama",  role: "picker",     tier: "steady",   shift: "Evening", zones: ["Cosmetic zone - JM"],                 status: "active",  joined: "2025-02", perms: ["pick", "inventory"], perf: { count: 15, unit: "picks", avg: "3m02s", sla: 83, rank: 5, trend: [12,13,14,13,15,14,15] } },
  { id: "said",     role: "picker",     tier: "coaching", shift: "Evening", zones: ["SLOW ZONE - JM", "Textile Zone - JM"],status: "offline", joined: "2025-04", perms: ["pick"], perf: { count: 12, unit: "picks", avg: "3m18s", sla: 80, rank: 6, trend: [14,12,11,12,11,13,12] } },
  { id: "reda",     role: "packer",     tier: "top",      shift: "Full day",zones: ["Packing station"],                    status: "active",  joined: "2024-07", perms: ["pack_label", "ship"], perf: { count: 242, unit: "parcels", avg: "—", sla: 92, rank: 1, trend: [210,230,245,260,250,255,242] } },
  { id: "nadia",    role: "returns",    tier: "steady",   shift: "Morning", zones: ["Return Zone - JM"],                   status: "active",  joined: "2024-11", perms: ["returns", "inventory"], perf: { count: 31, unit: "returns", avg: "1m44s", sla: 88, rank: 1, trend: [24,28,26,30,29,32,31] } },
  { id: "sara",     role: "manager",    tier: "top",      shift: "Full day",zones: ["All zones"],                          status: "active",  joined: "2024-05", perms: ["admin", "assign", "ship", "returns", "inventory", "reports"], perf: { count: 0, unit: "—", avg: "—", sla: 0, rank: 0, trend: [0,0,0,0,0,0,0] } },
];

window.LG_DATA_TEAM = { CAPS, TIERS, MEMBER_STATUS, TEAM_MEMBERS };

// ── Bonus & incentives engine ────────────────────────────────────────
const BONUS = {
  perPick: 2, onTime: 1, zeroErrorDay: 15, dailyTargetBonus: 30,
  slaGate: 90, errorGate: 2, monthlyCap: 1500, streakStepPct: 10, streakCapPct: 30,
  tierMult: { top: 1.15, steady: 1.0, coaching: 1.05 }, // coaching rewards improvement
  weeklyTop: [200, 100, 50], teamKicker: 120, teamSameDayTarget: 90, currentSameDay: 87,
  workedDays: 18, monthDays: 22,
};
function computeBonus(m) {
  const p = m.perf; if (!p || !p.sla) return null;
  const daily = p.count || 0;
  const monthlyOut = daily * BONUS.workedDays;
  const tierMult = BONUS.tierMult[m.tier] || 1;
  const targetHitDays = Math.round(BONUS.workedDays * Math.min(1, p.sla / 95));
  const zeroErrDays = Math.max(0, Math.round(BONUS.workedDays * (p.sla / 100) - 2));
  const streakDays = m.tier === "top" ? 7 : m.tier === "steady" ? 4 : 2;
  const streakPct = Math.min(BONUS.streakCapPct, Math.floor(streakDays / 5) * BONUS.streakStepPct);
  const breaches = p.sla >= 90 ? 0 : p.sla >= 85 ? 1 : 3;
  // points
  const base = Math.round(monthlyOut * BONUS.perPick);
  const onTime = Math.round(monthlyOut * (p.sla / 100) * BONUS.onTime);
  const zeroError = zeroErrDays * BONUS.zeroErrorDay;
  const targetBonus = targetHitDays * BONUS.dailyTargetBonus;
  const penalty = breaches * 25;
  const gatePass = p.sla >= BONUS.slaGate;
  let gross = base + onTime + zeroError + targetBonus - penalty;
  gross = Math.round(gross * tierMult * (1 + streakPct / 100));
  const earned = gatePass ? Math.min(BONUS.monthlyCap, Math.round(gross * (BONUS.workedDays / BONUS.monthDays))) : Math.round(base * (BONUS.workedDays / BONUS.monthDays));
  const projected = gatePass ? Math.min(BONUS.monthlyCap, gross) : base;
  const teamKicker = BONUS.currentSameDay >= BONUS.teamSameDayTarget ? BONUS.teamKicker : 0;
  return {
    earned, projected, cap: BONUS.monthlyCap, gatePass, breaches, streakDays, streakPct, tierMult,
    teamKicker, targetHitDays, zeroErrDays,
    points: { base, onTime, zeroError, targetBonus, penalty, total: base + onTime + zeroError + targetBonus - penalty },
    pct: Math.min(1, projected / BONUS.monthlyCap),
  };
}
window.LG_BONUS = BONUS;
window.computeBonus = computeBonus;
const SLA_SETTINGS = { cutoff: "14:00", sameDayTarget: 90, deliveryDays: 3, maxPick: 2, maxLabel: 1, maxShip: 3 };
window.LG_SLA_SETTINGS = SLA_SETTINGS;

// ── Warehouse physical layout (floor-plan grid) + density ────────────
// col/row/w/h position the zone on a 6×4 floor grid. move = velocity class.
const WAREHOUSE_MAP = {
  cols: 6, rows: 4,
  zones: [
    { id: "FAST ZONE - JM",      short: "FAST",     col: 0, row: 0, w: 2, h: 2, skus: 142, units: 4820, cap: 5400, move: "fast",   owner: "marouane", aisles: ["J7","J8"], picks7d: 980 },
    { id: "Cosmetic zone - JM",  short: "Cosmetic", col: 2, row: 0, w: 2, h: 1, skus: 64,  units: 1180, cap: 2000, move: "fast",   owner: "asmaa",    aisles: ["I4","H13"], picks7d: 540 },
    { id: "MU Zone - JM",        short: "Makeup",   col: 4, row: 0, w: 2, h: 1, skus: 51,  units: 1390, cap: 1800, move: "medium", owner: "asmaa",    aisles: ["H13","H14"], picks7d: 360 },
    { id: "Accessory Zone - JM", short: "Accessory",col: 2, row: 1, w: 2, h: 1, skus: 38,  units: 980,  cap: 1500, move: "medium", owner: "oussama",  aisles: ["H14","I4"], picks7d: 290 },
    { id: "Textile Zone - JM",   short: "Textile",  col: 4, row: 1, w: 2, h: 1, skus: 44,  units: 1620, cap: 1700, move: "slow",   owner: "said",     aisles: ["F13","G13"], picks7d: 110 },
    { id: "SLOW ZONE - JM",      short: "SLOW",     col: 0, row: 2, w: 3, h: 2, skus: 98,  units: 5210, cap: 5600, move: "slow",   owner: "saad",     aisles: ["F13","F14"], picks7d: 130 },
    { id: "Stores - JM",         short: "Reserve",  col: 3, row: 2, w: 3, h: 2, skus: 703, units: 12400,cap: 16000,move: "reserve",owner: "reda",     aisles: ["Bulk"], picks7d: 0 },
  ],
};
// Re-slotting suggestions (velocity vs location mismatch)
const RESLOT = [
  { sku: "MCH100020", name: "Recharge huile lavande", from: "SLOW ZONE - JM", fromBin: "F14B - JM", to: "FAST ZONE - JM", toBin: "J7C - JM", picks7d: 201, reason: "High velocity in slow zone", gain: "−18% walk" },
  { sku: "ACC11015", name: "Miroir LED pliable", from: "Textile Zone - JM", fromBin: "G13A - JM", to: "Accessory Zone - JM", toBin: "H14C - JM", picks7d: 154, reason: "Misclassified category", gain: "−12% walk" },
  { sku: "TXT55088", name: "Châle hiver laine", from: "FAST ZONE - JM", fromBin: "J8A - JM", to: "SLOW ZONE - JM", toBin: "F13C - JM", picks7d: 6, reason: "Dead stock in prime slot", gain: "Free fast slot" },
];
// Cycle counts → posted as Stock Reconciliation (MAT-RECO) in ERPNext
const CYCLE_COUNTS = [
  { no: "MAT-RECO-2026-00061", zone: "FAST ZONE - JM", cls: "A", bins: 24, counted: 24, system: 482, actual: 480, variances: 1, status: "review", owner: "marouane" },
  { no: "MAT-RECO-2026-00060", zone: "Cosmetic zone - JM", cls: "A", bins: 14, counted: 6, system: 188, actual: 0, variances: 0, status: "counting", owner: "asmaa" },
  { no: "MAT-RECO-2026-00059", zone: "MU Zone - JM", cls: "B", bins: 12, counted: 12, system: 139, actual: 139, variances: 0, status: "done", owner: "asmaa" },
  { no: "MAT-RECO-2026-00058", zone: "SLOW ZONE - JM", cls: "C", bins: 22, counted: 0, system: 2885, actual: 0, variances: 0, status: "scheduled", owner: "saad" },
];
const CYCLE_VARIANCES = [
  { sku: "CSM44021", bin: "I4A - JM", system: 24, counted: 22, diff: -2, scanned: true },
  { sku: "MCH100013", bin: "J8C - JM", system: 41, counted: 41, diff: 0, scanned: true },
];
// Smart count planner — ABC-driven cadence, auto daily list, coverage
const COUNT_PLAN = {
  coverage: 78, period: "30d", countedSkus: 343, totalSkus: 441,
  cadence: [
    { cls: "A", every: "Weekly", skus: 88, due: 12, color: "#10b981" },
    { cls: "B", every: "Bi-weekly", skus: 142, due: 9, color: "#f59e0b" },
    { cls: "C", every: "Monthly", skus: 211, due: 7, color: "#a8a29e" },
  ],
  today: { bins: 18, mins: 22, zones: ["FAST ZONE - JM", "Cosmetic zone - JM"], skus: 28 },
};
window.LG_COUNT_PLAN = COUNT_PLAN;
// Receiving — inbound stock (ASN / purchase receipt)
const INBOUND = [
  { no: "PR-2026-0418", supplier: "MCH Supplies", items: 12, units: 480, eta: "Today 15:00", status: "putaway", owner: "reda", dock: "Dock 2" },
  { no: "PR-2026-0417", supplier: "Cosmetica MA", items: 8, units: 320, eta: "Arrived", status: "checking", owner: "oussama", dock: "Dock 1" },
  { no: "PR-2026-0415", supplier: "Textil Group", items: 5, units: 140, eta: "Tomorrow", status: "scheduled", owner: "said", dock: "—" },
];
window.LG_WAREHOUSE_MAP = WAREHOUSE_MAP;
window.LG_RESLOT = RESLOT;
window.LG_CYCLE_COUNTS = CYCLE_COUNTS;
window.LG_CYCLE_VARIANCES = CYCLE_VARIANCES;
window.LG_INBOUND = INBOUND;

// ── COD reconciliation (carrier collects cash → remits) ──────────────
const COD = {
  collected: 141368, remitted: 98200, pending: 43168, discrepancy: 1240, codRate: 96,
  remittances: [
    { no: "CR-2026-0142", date: "2026-06-19", carrier: "Cathedis", parcels: 198, expected: 31420, received: 31420, diff: 0, status: "reconciled" },
    { no: "CR-2026-0141", date: "2026-06-18", carrier: "Cathedis", parcels: 241, expected: 38950, received: 37710, diff: -1240, status: "discrepancy" },
    { no: "CR-2026-0140", date: "2026-06-17", carrier: "Cathedis", parcels: 263, expected: 39950, received: 39950, diff: 0, status: "reconciled" },
    { no: "CR-2026-0139", date: "2026-06-20", carrier: "Cathedis", parcels: 124, expected: 43168, received: 0, diff: 0, status: "pending" },
  ],
};
// Exception command center (cross-cycle worklist)
const EXCEPTIONS = [
  { id: "#242638", kind: "oos", label: "Out of stock", detail: "Mohmad Mohmad · Cosmetic zone · 2 items OOS", owner: "asmaa", age: 158, sev: "red", sla: 30 },
  { id: "#240682", kind: "carrier", label: "Failed delivery", detail: "Edghir hanane · 2nd failed attempt · LD007744422", owner: "nadia", age: 142, sev: "red", sla: 60 },
  { id: "#242128", kind: "carrier", label: "Carrier exception", detail: "Fatima Fatima · address not found", owner: "nadia", age: 86, sev: "orange", sla: 60 },
  { id: "PL-51388", kind: "shortpick", label: "Short-pick", detail: "Nezili kaoutar · MUZ22014 missing 1", owner: "asmaa", age: 47, sev: "orange", sla: 45 },
  { id: "RET-26-3137317", kind: "return", label: "Missing on return", detail: "3 SKUs not in carrier return batch", owner: "nadia", age: 220, sev: "yellow", sla: 120 },
  { id: "CR-2026-0141", kind: "cod", label: "COD discrepancy", detail: "Cathedis · −1,240 MAD short on remittance", owner: "sara", age: 300, sev: "red", sla: 240 },
];
const EXC_KIND = { oos: { tone: "rose", icon: "Box" }, carrier: { tone: "orange", icon: "Globe" }, shortpick: { tone: "amber", icon: "AlertCircle" }, return: { tone: "violet", icon: "Return" }, cod: { tone: "rose", icon: "Cash" } };
// Carrier scorecard (per-zone performance + routing)
const CARRIER_SCORES = [
  { carrier: "Cathedis", code: "CTH", deliveryRate: 91.2, exceptionRate: 4.8, avgTransit: 1.8, costPerParcel: 22, active: true,
    zones: [{ zone: "Casablanca", rate: 95, transit: 1.2 }, { zone: "Rabat", rate: 93, transit: 1.6 }, { zone: "Tanger", rate: 84, transit: 2.6 }, { zone: "Marrakech", rate: 88, transit: 2.1 }] },
  { carrier: "Sendit", code: "SND", deliveryRate: 89, exceptionRate: 5.5, avgTransit: 1.9, costPerParcel: 24, active: false,
    zones: [{ zone: "Casablanca", rate: 92, transit: 1.3 }, { zone: "Rabat", rate: 90, transit: 1.5 }] },
  { carrier: "Ozonexpress", code: "OZN", deliveryRate: 90, exceptionRate: 5.0, avgTransit: 2.2, costPerParcel: 20, active: false,
    zones: [{ zone: "Marrakech", rate: 92, transit: 1.8 }, { zone: "Agadir", rate: 91, transit: 2.0 }] },
];
const ROUTING_SUGGESTIONS = [
  { zone: "Tanger", from: "Cathedis", to: "Sendit", reason: "Cathedis 84% vs Sendit 92% in Tanger", gain: "+8% delivery" },
  { zone: "Marrakech", from: "Cathedis", to: "Ozonexpress", reason: "Ozon 92% & faster transit", gain: "+4% · −0.3d" },
];
window.LG_COD = COD;
window.LG_EXCEPTIONS = EXCEPTIONS;
window.LG_EXC_KIND = EXC_KIND;
window.LG_CARRIER_SCORES = CARRIER_SCORES;
window.LG_ROUTING = ROUTING_SUGGESTIONS;

// ── Pack station (scan-verify packing) ───────────────────────────────
const PACK_QUEUE = [
  { order: "#242611", customer: "Khadija abhaoui", items: 2, weight: 0.6, box: "S", zone: "FAST ZONE - JM", sla: "ontrack" },
  { order: "#242605", customer: "Soukaina Idrissi", items: 1, weight: 0.3, box: "XS", zone: "FAST ZONE - JM", sla: "ontrack" },
  { order: "#242598", customer: "Rim Cherkaoui", items: 3, weight: 1.2, box: "M", zone: "Cosmetic zone - JM", sla: "atrisk" },
  { order: "#242590", customer: "Loubna Saidi", items: 1, weight: 0.4, box: "XS", zone: "Accessory Zone - JM", sla: "ontrack" },
];
const BOXES = [{ id: "XS", dim: "15×10×5", max: 0.5 }, { id: "S", dim: "25×18×8", max: 1.5 }, { id: "M", dim: "35×25×12", max: 4 }, { id: "L", dim: "45×35×20", max: 10 }];
window.LG_PACK_QUEUE = PACK_QUEUE; window.LG_BOXES = BOXES;

// ── Wave picking (scheduled batch releases) ──────────────────────────
const WAVES = [
  { no: "WAVE-08", window: "Cutoff 14:00", releaseAt: "11:30", orders: 42, pickers: 4, zones: ["FAST", "Cosmetic"], status: "active", progress: 64, cutoffMin: 156 },
  { no: "WAVE-09", window: "Cutoff 14:00", releaseAt: "12:30", orders: 38, pickers: 4, zones: ["SLOW", "Textile"], status: "queued", progress: 0, cutoffMin: 156 },
  { no: "WAVE-07", window: "Cutoff 14:00", releaseAt: "10:30", orders: 51, pickers: 5, zones: ["MU", "Accessory"], status: "done", progress: 100, cutoffMin: 0 },
];
window.LG_WAVES = WAVES;

// ── Live throughput / Andon board ────────────────────────────────────
const ANDON = {
  ordersPerHour: 73, target: 80, packedToday: 412, shippedToday: 389, cutoffMin: 156,
  hourly: [38, 44, 52, 61, 58, 67, 73],
  stations: [
    { name: "Picking", rate: 78, target: 80, status: "ok" },
    { name: "Packing", rate: 61, target: 75, status: "warn" },
    { name: "Labeling", rate: 84, target: 80, status: "ok" },
    { name: "Shipping", rate: 70, target: 75, status: "ok" },
  ],
  laggingZone: "Cosmetic zone - JM",
};
window.LG_ANDON = ANDON;

// ── Smart inventory: ABC, days-of-cover reorder, bin transfers ───────
const ABC_CLASSES = [
  { cls: "A", share: 72, skus: 88, color: "#10b981", note: "Top 20% SKUs · 72% of picks" },
  { cls: "B", share: 21, skus: 142, color: "#f59e0b", note: "Mid movers" },
  { cls: "C", share: 7, skus: 211, color: "#a8a29e", note: "Long tail · review for clearance" },
];
const REORDER_ALERTS = [
  { sku: "CSM44021", name: "Sérum éclat 30ml", bin: "I4A - JM", onHand: 0, daily: 11, cover: 0, reorder: 24, cls: "A" },
  { sku: "ACC11008", name: "Trousse maquillage zip", bin: "H14A - JM", onHand: 3, daily: 7, cover: 0.4, reorder: 20, cls: "A" },
  { sku: "MUZ22014", name: "Palette ombres MU", bin: "H13B - JM", onHand: 2, daily: 4, cover: 0.5, reorder: 18, cls: "B" },
  { sku: "TXT55012", name: "Foulard soie imprimé", bin: "F13C - JM", onHand: 7, daily: 2, cover: 3.5, reorder: 12, cls: "B" },
  { sku: "MCH100020", name: "Recharge huile lavande", bin: "J7B - JM", onHand: 58, daily: 29, cover: 2, reorder: 25, cls: "A" },
];
const BIN_TRANSFERS = [
  { id: "BT-308", sku: "MCH100013", from: "Stores - JM", to: "J8C - JM", qty: 24, owner: "reda", status: "done" },
  { id: "BT-307", sku: "CSM44021", from: "Stores - JM", to: "I4A - JM", qty: 24, owner: "oussama", status: "inprogress" },
];
window.LG_ABC = ABC_CLASSES;
window.LG_REORDER = REORDER_ALERTS;
window.LG_BIN_TRANSFERS = BIN_TRANSFERS;

// ── Pending pick pool — order lines awaiting a pick list (real shape) ─
// bin "L#x - JM": leading letter = aisle/zone. Used by the smart grouper.
const BIN_ZONE = { J: "FAST ZONE - JM", F: "SLOW ZONE - JM", I: "Cosmetic zone - JM", H: "MU Zone - JM", E: "Accessory Zone - JM", G: "Textile Zone - JM" };
const PICK_POOL = [
  { so: "#242646", sku: "MCH100013", code: "46029739950334", grp: "Home Fragrance", uom: "Nos", name: "Diffuseur huile MCH — box", bin: "J8C - JM", qty: 1, customer: "oualid elmouden" },
  { so: "#242644", sku: "ACC11008", code: "47594099441918", grp: "Accessories", uom: "Nos", name: "Trousse maquillage zip", bin: "H14A - JM", qty: 1, customer: "Chada Rami" },
  { so: "#242644", sku: "ACC11015", code: "47594099442011", grp: "Accessories", uom: "Nos", name: "Miroir LED pliable", bin: "H14C - JM", qty: 1, customer: "Chada Rami" },
  { so: "#242641", sku: "TXT55012", code: "46881234500021", grp: "Textile", uom: "Nos", name: "Foulard soie imprimé", bin: "G13C - JM", qty: 1, customer: "Hamid Hamid" },
  { so: "#242638", sku: "CSM44021", code: "46029811200334", grp: "Cosmetics", uom: "box", name: "Sérum éclat 30ml", bin: "I4A - JM", qty: 2, customer: "Mohmad Mohmad", serial: true },
  { so: "#242620", sku: "MCH100013", code: "46029739950334", grp: "Home Fragrance", uom: "Nos", name: "Diffuseur huile MCH — box", bin: "J8C - JM", qty: 1, customer: "Najat Bennani" },
  { so: "#242620", sku: "MCH100020", code: "46029739950571", grp: "Home Fragrance", uom: "Nos", name: "Recharge huile lavande", bin: "J7B - JM", qty: 1, customer: "Najat Bennani" },
  { so: "#242618", sku: "MUZ22014", code: "46772200140088", grp: "Makeup", uom: "Nos", name: "Palette ombres MU", bin: "H13B - JM", qty: 1, customer: "Imane Tazi", batch: true },
  { so: "#242615", sku: "CSM44021", code: "46029811200334", grp: "Cosmetics", uom: "box", name: "Sérum éclat 30ml", bin: "I4A - JM", qty: 1, customer: "Fouzia Fouzia", serial: true },
  { so: "#242612", sku: "MCH100013", code: "46029739950334", grp: "Home Fragrance", uom: "Nos", name: "Diffuseur huile MCH — box", bin: "J8C - JM", qty: 1, customer: "Sanae R." },
  { so: "#242609", sku: "ACC11015", code: "47594099442011", grp: "Accessories", uom: "Nos", name: "Miroir LED pliable", bin: "H14C - JM", qty: 1, customer: "Loubna T." },
  { so: "#242607", sku: "TXT55012", code: "46881234500021", grp: "Textile", uom: "Nos", name: "Foulard soie imprimé", bin: "G13C - JM", qty: 1, customer: "Nawal B." },
  { so: "#242605", sku: "MCH100020", code: "46029739950571", grp: "Home Fragrance", uom: "Nos", name: "Recharge huile lavande", bin: "J7B - JM", qty: 1, customer: "Soukaina Idrissi" },
  { so: "#242601", sku: "CSM44021", code: "46029811200334", grp: "Cosmetics", uom: "box", name: "Sérum éclat 30ml", bin: "I4A - JM", qty: 1, customer: "Yasmine Alaoui", serial: true },
];
window.LG_PICK_POOL = PICK_POOL;
window.LG_BIN_ZONE = BIN_ZONE;

// ── Smart auto pick-list grouping engine ─────────────────────────────
// strategies: zone (cluster by aisle) · sku (batch same SKU) · single (1-item blitz) · balanced
function binZone(bin) { return BIN_ZONE[(bin || "?")[0]] || "Other"; }
function aisle(bin) { return (bin || "?").match(/^[A-Z]\d*/)?.[0] || "?"; }
function autoPickGroups(strategy, cap = 12) {
  const pool = PICK_POOL;
  const lines = pool.length, units = pool.reduce((a, l) => a + l.qty, 0);
  let groups = [];
  if (strategy === "sku") {
    const m = {};
    pool.forEach((l) => { (m[l.sku] = m[l.sku] || []).push(l); });
    groups = Object.entries(m).map(([sku, ls]) => ({ key: sku, kind: "Batch SKU", label: ls[0].name, lines: ls }));
  } else if (strategy === "single") {
    const orders = {};
    pool.forEach((l) => { (orders[l.so] = orders[l.so] || []).push(l); });
    const singles = Object.values(orders).filter((ls) => ls.length === 1).flat();
    const multi = Object.entries(orders).filter(([, ls]) => ls.length > 1);
    groups = [{ key: "blitz", kind: "Single-item blitz", label: `${singles.length} one-line orders`, lines: singles }];
    multi.forEach(([so, ls]) => groups.push({ key: so, kind: "Multi-line", label: so, lines: ls }));
  } else if (strategy === "zone") {
    const m = {};
    pool.forEach((l) => { const z = binZone(l.bin); (m[z] = m[z] || []).push(l); });
    groups = Object.entries(m).map(([z, ls]) => ({ key: z, kind: "Zone cluster", label: z.replace(" - JM", ""), lines: ls }));
  } else { // balanced — zone clusters, split by cap
    const m = {};
    pool.forEach((l) => { const z = binZone(l.bin); (m[z] = m[z] || []).push(l); });
    Object.entries(m).forEach(([z, ls]) => {
      for (let i = 0; i < ls.length; i += cap) groups.push({ key: z + i, kind: "Balanced", label: z.replace(" - JM", ""), lines: ls.slice(i, i + cap) });
    });
  }
  // enrich each group with stats
  groups = groups.filter((g) => g.lines.length).map((g, i) => {
    const orders = new Set(g.lines.map((l) => l.so)).size;
    const aisles = new Set(g.lines.map((l) => aisle(l.bin))).size;
    const units = g.lines.reduce((a, l) => a + l.qty, 0);
    return { ...g, no: `PL-${51440 + i}`, orders, aisles, units, items: g.lines.length };
  });
  // naive "walk saved": fewer aisles per order = better. baseline = one trip per order.
  const baselineAisles = pool.length; // worst case
  const newAisles = groups.reduce((a, g) => a + g.aisles, 0);
  const saved = Math.max(0, Math.round((1 - newAisles / baselineAisles) * 100));
  return { groups, stats: { lines, units, orders: new Set(pool.map((l) => l.so)).size, batches: groups.length, saved } };
}
window.autoPickGroups = autoPickGroups;
window.lgAisle = aisle; window.lgBinZone = binZone;

// ── Pick Autopilot — AI agent state + activity log ───────────────────
const AUTOPILOT = {
  active: true, nextRunMin: 12, createdToday: 14, assignedToday: 14, efficiency: 41,
  strategy: "zone", schedule: "30m", watching: 6,
  feed: [
    { t: "2m",  act: "Created PL-51440 → PL-51443 · 4 zone batches", kind: "create" },
    { t: "2m",  act: "Auto-assigned to Marouane, Asmaa, Saad, Oussama by load + zone", kind: "assign" },
    { t: "14m", act: "Marouane idle 6 min — re-routed 1 batch to Asmaa", kind: "balance" },
    { t: "31m", act: "Flagged PL-51388 stalled (Short-pick) — alerted dispatcher", kind: "alert" },
    { t: "1h",  act: "Held 8 SLOW-zone orders for next batch (below threshold)", kind: "hold" },
  ],
  recos: [
    { txt: "Batch 6 Cosmetic-zone orders now — saves ~22 min walking before cutoff", strat: "zone" },
    { txt: "Marouane is fastest on FAST zone — assign next FAST batch to him", strat: "sku" },
  ],
};
window.LG_AUTOPILOT = AUTOPILOT;const ROUTES = [
  { no: "TRIP-0043", driver: "Karim Tahiri",   zone: "Mohammedia",            stops: 14, parcels: 19, delivered: 0,  status: "Loading",  eta: "17:20", exceptions: 0 },
  { no: "TRIP-0042", driver: "Younes Bennani",  zone: "Casablanca Centre",     stops: 18, parcels: 24, delivered: 11, status: "En route", eta: "16:40", exceptions: 0 },
  { no: "TRIP-0040", driver: "Said Mernissi",   zone: "Maârif / Gauthier",     stops: 16, parcels: 21, delivered: 14, status: "En route", eta: "16:05", exceptions: 2 },
  { no: "TRIP-0041", driver: "Hamid Raji",      zone: "Aïn Sebaâ / Sidi Moumen",stops: 22, parcels: 31, delivered: 31, status: "Completed",eta: "—",     exceptions: 0 },
];
window.LG_ROUTES = ROUTES;

window.LG_DATA = {
  WAREHOUSE, CITY, CARRIER, CUTOFF, TODAY, ZONES, CHANNELS, CHANNEL_MIX, TEAM, byId,
  STAGE, SLA, PIPELINE, ORDERS, PICKLISTS, PICK_ITEMS, PARCELS, TRACK_STATES, TRACK_COUNTS,
  MANIFEST, RECENT_MANIFESTS, LABEL_QUEUE, RETURNS, RETURN_REASONS, LEADERBOARD, AUDIT,
  RESTOCK, RESTOCK_ITEMS, orderTimeline, STAGE_SEQ,
  SHIPMENTS, CARRIERS, RETURN_BATCHES, RETURN_ITEMS, RS_STATUS, STOCK_STATS, STOCK_ITEMS, RESTOCK_TASKS,
  TOP_MOVERS, DEAD_STOCK, RETURN_BY_SKU, SLA_BY_STAGE, SLA_STATS,
  CAPS, TIERS, MEMBER_STATUS, TEAM_MEMBERS, ROUTES, TODAY_FLOW, SLA_DELIVERY,
};

// ─────────────────────────────────────────────────────────────────────
// i18n — EN / FR / AR(RTL)
// ─────────────────────────────────────────────────────────────────────
const STRINGS = {
  en: {
    _dir: "ltr", _name: "English",
    "role.picker": "Picker", "role.packer": "Packer / Shipper", "role.dispatcher": "Dispatcher", "role.returns": "Returns", "role.manager": "Supervisor",
    "role.picker.home": "My Queue", "role.packer.home": "Label & Manifest", "role.dispatcher.home": "Assignment Board", "role.returns.home": "Returns Queue", "role.manager.home": "Cockpit",
    "nav.cockpit": "Cockpit", "nav.pipeline": "Pipeline", "nav.assign": "Assignment", "nav.queue": "My Queue", "nav.label": "Label & Print", "nav.manifest": "Manifest", "nav.returns": "Returns", "nav.tracking": "Tracking", "nav.performance": "My Performance", "nav.team": "Team", "nav.alerts": "Alerts", "nav.inventory": "Zone Restock",
    "nav.orders": "Orders", "nav.picklists": "Pick Lists", "nav.shipments": "Shipments", "nav.sla": "SLA", "nav.stock": "Inventory", "nav.restocking": "Restocking", "nav.analysis": "Stock Analysis", "nav.carriers": "Carriers", "nav.fulfillment": "Fulfillment", "nav.inventoryGrp": "Inventory",
    "nav.operations": "Operations", "nav.overview": "Overview", "nav.me": "Me",
    "c.search": "Search order, AWB, pick list…", "c.orders": "orders", "c.order": "Order", "c.customer": "Customer", "c.items": "items", "c.value": "Value", "c.stage": "Stage", "c.sla": "SLA", "c.zone": "Zone", "c.bin": "Bin", "c.channel": "Channel", "c.picker": "Picker", "c.assign": "Assign", "c.assigned": "Assigned", "c.unassigned": "Unassigned", "c.today": "Today", "c.parcels": "parcels", "c.carrier": "Carrier", "c.print": "Print", "c.printed": "Printed", "c.reprint": "Re-print", "c.close": "Close", "c.viewAll": "View all", "c.target": "target", "c.rank": "Rank", "c.of": "of", "c.min": "min", "c.left": "left", "c.due": "due", "c.scan": "Scan", "c.confirm": "Confirm", "c.complete": "Complete", "c.next": "Next", "c.done": "Done", "c.qty": "Qty", "c.notifications": "Notifications", "c.markRead": "Mark all read", "c.process": "Process", "c.restock": "Restock", "c.reason": "Reason", "c.cutoff": "cutoff", "c.handToCarrier": "Close & hand to carrier", "c.timeline": "Order timeline", "c.openInErp": "Open in ERPNext", "c.viewTimeline": "View full cycle", "c.onHand": "On hand", "c.reorder": "Reorder pt", "c.demand": "7d demand", "c.lowStock": "Low stock", "c.outOfStock": "Out of stock", "c.blocking": "blocking picks", "c.fill": "fill rate",
    "s.pending": "Pending", "s.picking": "Picking", "s.picked": "Picked", "s.labelgen": "Label Generated", "s.label": "Label Printed", "s.shipped": "Shipped", "s.transit": "In Transit", "s.exception": "Exception", "s.delivered": "Delivered", "s.returned": "Returned", "s.oos": "Out of Stock", "s.partial": "Partial",
    "sla.ontrack": "On Track", "sla.atrisk": "At Risk", "sla.breached": "Breached", "sla.late": "Delivered Late", "sla.returned": "Returned",
    "t.pending": "Pending", "t.pickedup": "Picked up", "t.intransit": "In Transit", "t.outfordelivery": "Out For Delivery", "t.delivered": "Delivered", "t.exception": "Delivery Exception", "t.failed": "Failed Attempt", "t.return": "Return",
    "ck.title": "Floor cockpit", "ck.sub": "Live across the whole floor", "ck.sameday": "Shipped same-day", "ck.breaches": "SLA breaches", "ck.atrisk": "At risk now", "ck.pipeline": "Pipeline", "ck.slaboard": "SLA board", "ck.leaderboard": "Team leaderboard", "ck.audit": "Audit feed", "ck.allgreen": "Floor is on track", "ck.allgreenSub": "No breaches in the last hour. Same-day ship rate is healthy.", "ck.needsAttention": "Needs attention", "ck.drillBreach": "Breached orders", "ck.channelMix": "Channel mix", "ck.exceptions": "Carrier exceptions", "ck.today": "Today's flow", "ck.intake": "Orders in", "ck.shippedToday": "Shipped", "ck.toShip": "To ship", "ck.cutoffIn": "Cutoff in", "ck.afterCutoff": "Past cutoff",
    "dp.title": "Assignment board", "dp.ready": "Ready to assign", "dp.balance": "Balance the load across your pickers", "dp.capacity": "capacity", "dp.load": "load", "dp.combined": "Combined Pick", "dp.assignTo": "Assign to", "dp.instock": "In Stock", "dp.partial": "Partial", "dp.oos": "Out of Stock",
    "pk.hi": "Hi", "pk.todays": "today", "pk.hitrate": "SLA hit-rate", "pk.nextdue": "Next due", "pk.queue": "My queue", "pk.urgent": "Most urgent first", "pk.startPick": "Start picking", "pk.scanItem": "Scan item barcode", "pk.scanned": "Scanned", "pk.allScanned": "All items scanned", "pk.completePick": "Complete pick", "pk.nicework": "Nice work", "pk.advancing": "Loading next order…", "pk.empty": "Queue clear — nice.", "pk.emptySub": "No orders waiting. We'll ping you when one lands.",
    "pc.labelQueue": "Label & print", "pc.manifestTab": "Today's manifest", "pc.buildManifest": "Build today's handover", "pc.running": "Running total", "pc.addParcel": "Scan or add a parcel", "pc.cutoffIn": "Cutoff in", "pc.generateLabel": "Generate AWB", "pc.recent": "Recent manifests",
    "rt.title": "Returns queue", "rt.incoming": "Incoming returns", "rt.rate": "Return rate", "rt.topReason": "Top reason", "rt.inspect": "Inspect", "rt.routeRestock": "Route to restock", "rt.routeDefective": "Route to defective",
    "rt.open": "Open", "rt.inspectS": "Inspecting", "rt.restockS": "Restocking", "rt.closed": "Closed",
    "rs.title": "Return shipments", "rs.sub": "Carrier returns · scan reconciliation", "rs.batch": "Return batch", "rs.batches": "Batches", "rs.toReconcile": "To reconcile", "rs.returnRate": "Return rate", "rs.missingTot": "Missing units", "rs.orders": "orders", "rs.qty": "qty", "rs.missing": "missing", "rs.returnPct": "return %", "rs.scanAwb": "Scan parcel AWB", "rs.scanItem": "Scan item barcode", "rs.awbPhase": "AWB scanning", "rs.itemPhase": "Item scanning", "rs.awbScanned": "AWB scanned", "rs.itemsScanned": "Items scanned", "rs.missingSkus": "Missing SKUs", "rs.markReady": "Mark ready for return", "rs.createReturns": "Create Sales Returns", "rs.complete": "Complete", "rs.short": "Short", "rs.analytics": "Analytics", "rs.list": "Return batches", "rs.lines": "Return lines",
    "pf.title": "My performance", "pf.coaching": "You're doing great — keep it up", "pf.completed": "Completed today", "pf.avgTime": "Avg time / item", "pf.vsTeam": "vs team median", "pf.toGo": "to hit your target", "pf.trend": "Last 7 days", "pf.almostThere": "Almost there",
    "iv.title": "Zone restock", "iv.sub": "Bin health across the warehouse", "iv.needsRestock": "Needs restock", "iv.healthy": "Healthy", "iv.zoneHealth": "Zone health", "iv.restockList": "Restock list",
    "wh.title": "Warehouse", "wh.sub": "SoftPark Aïn Sebaâ · Morocco-JM", "wh.map": "Floor map", "wh.reslot": "Re-slotting", "wh.count": "Cycle count", "wh.receiving": "Receiving", "wh.zones": "Zones & owners", "wh.density": "Density", "wh.fill": "fill", "wh.fast": "Fast movers", "wh.medium": "Medium", "wh.slow": "Slow", "wh.reserve": "Reserve", "wh.velocity": "Velocity", "wh.owner": "Owner", "wh.picks7d": "picks / 7d", "wh.legend": "Capacity fill", "wh.suggested": "Suggested moves", "wh.applyMove": "Apply move", "wh.from": "From", "wh.to": "To", "wh.gain": "Gain", "wh.scanBin": "Scan bin to count", "wh.variance": "Variance", "wh.system": "System", "wh.counted": "Counted", "wh.startCount": "Start count", "wh.newCount": "New cycle count", "wh.putaway": "Put away", "wh.checkIn": "Check in", "wh.dock": "Dock", "wh.eta": "ETA", "wh.inbound": "Inbound", "wh.assignOwner": "Assign owner", "wh.units": "units", "wh.skus": "SKUs", "wh.smart": "Smart", "wh.reorder": "Reorder alerts", "wh.daysCover": "days cover", "wh.abc": "ABC analysis", "wh.transfer": "Bin transfer", "wh.scanFrom": "Scan source bin", "wh.scanTo": "Scan destination bin", "wh.createReorder": "Create purchase order", "wh.coverNow": "Out now", "wh.coverLow": "Critical", "wh.autopilotTie": "Send re-slotting to Autopilot", "wh.planner": "Smart count planner", "wh.coverage": "Coverage", "wh.todayCount": "Today's count", "wh.cadence": "ABC cadence", "wh.due": "due", "wh.startToday": "Start today's count", "wh.autoPlan": "Auto-planned · zero setup", "wh.everyWk": "every", "wh.postReco": "Post as Stock Reconciliation", "wh.recount": "Re-count sooner", "wh.scanned": "scanned",
    "cc.scheduled": "Scheduled", "cc.counting": "Counting", "cc.review": "Review", "cc.posted": "Posted", "cc.bins": "Bins to count", "cc.scanNext": "Scan next bin", "cc.binDone": "Counted", "cc.expected": "Exp.", "cc.found": "Found", "cc.startCount": "Start counting", "cc.toReview": "Finish & review", "cc.confirmPost": "Post Stock Reconciliation", "cc.match": "Match", "cc.off": "Off by", "cc.howto": "Scan each bin → system compares to expected → variances flagged → post as Stock Reconciliation", "cc.recountBin": "Re-count",
    "nc.title": "New cycle count", "nc.method": "Method", "nc.byZone": "By zone", "nc.byAbc": "By ABC class", "nc.byBin": "Bin range", "nc.pickZone": "Select zone", "nc.assignTo": "Assign to", "nc.estBins": "Est. bins", "nc.estTime": "Est. time", "nc.blind": "Blind count (hide system qty)", "nc.create": "Create count", "nc.scheduleFor": "Schedule", "nc.now": "Now", "nc.tomorrow": "Tomorrow",
    "rc.checkin": "Check in", "rc.verify": "Verify items", "rc.putaway": "Put away", "rc.done": "Done", "rc.scanItem": "Scan inbound item", "rc.verifyHow": "Check in → verify items vs PO → scan to destination bins → Material Receipt", "rc.expected": "Expected", "rc.received": "Received", "rc.toBin": "To bin", "rc.confirmReceipt": "Post Material Receipt", "rc.startCheck": "Start check-in", "rc.toPutaway": "Verified · put away",
    "rl.suggested": "Suggested", "rl.scanSource": "Scan source bin", "rl.scanDest": "Scan destination", "rl.moving": "Moving", "rl.moved": "Moved ✓", "it.title": "Item", "it.byBin": "Stock by bin", "it.movement": "Movement · 30 days", "it.velocity": "Velocity", "it.reorderPt": "Reorder point", "it.valuation": "Valuation", "it.inbound": "Inbound", "it.lastCount": "Last counted", "it.sold30": "Sold · 30d", "it.openItem": "Open item",
    "ta.title": "Team management", "ta.sub": "Members, roles, permissions & performance", "ta.members": "Members", "ta.activeNow": "Active now", "ta.onShift": "On shift", "ta.avgSla": "Avg SLA",
    "nav.cod": "COD", "nav.exceptions": "Exceptions", "cod.title": "COD reconciliation", "cod.sub": "Cash collected by carrier → remitted", "cod.collected": "Collected", "cod.remitted": "Remitted", "cod.pending": "Pending remittance", "cod.discrepancy": "Discrepancy", "cod.remittances": "Carrier remittances", "cod.expected": "Expected", "cod.received": "Received", "cod.diff": "Diff", "cod.reconcile": "Reconcile", "cod.reconciled": "Reconciled", "cod.codRate": "COD success", "cod.flagDisc": "Flag discrepancy",
    "ex.title": "Exception center", "ex.sub": "Every blocker across the cycle · one queue", "ex.open": "Open exceptions", "ex.critical": "Critical", "ex.overdue": "Past resolve-SLA", "ex.resolve": "Resolve", "ex.reassign": "Reassign", "ex.age": "age", "ex.slaLeft": "to resolve", "ex.allKinds": "All", "ex.mine": "Mine",
    "cs.title": "Carrier scorecard", "cs.sub": "Performance & smart routing", "cs.deliveryRate": "Delivery rate", "cs.exceptionRate": "Exception rate", "cs.transit": "Avg transit", "cs.cost": "Cost / parcel", "cs.byZone": "By zone", "cs.routing": "Routing suggestions", "cs.reroute": "Re-route zone", "cs.compare": "Compare carriers",
    "nav.pack": "Pack Station", "nav.waves": "Waves", "nav.andon": "Floor Board",
    "ps.title": "Pack station", "ps.sub": "Scan-verify packing · auto box & label", "ps.queue": "Pack queue", "ps.scanOrder": "Scan order or AWB", "ps.suggestedBox": "Suggested box", "ps.scanItems": "Scan each item to verify", "ps.verified": "verified", "ps.weight": "Weight", "ps.printSeal": "Pack, weigh & print AWB", "ps.packed": "Packed today", "ps.mispackGuard": "Mispack guard on", "ps.fastLane": "Single-item fast lane", "ps.fastLaneSub": "1-item orders · pick→pack→label in one step",
    "wv.title": "Wave picking", "wv.sub": "Scheduled batch releases · cutoff-aware", "wv.release": "Release wave", "wv.released": "Released", "wv.queued": "Queued", "wv.active": "In progress", "wv.done": "Completed", "wv.releaseAt": "Release at", "wv.orders": "orders", "wv.pickers": "pickers", "wv.cutoffIn": "Cutoff in", "wv.autoPlan": "Auto-plan next wave",
    "an.title": "Floor board", "an.sub": "Live throughput across the floor", "an.oph": "Orders / hour", "an.target": "target", "an.packed": "Packed", "an.shipped": "Shipped", "an.cutoff": "To cutoff", "an.stations": "Stations", "an.lagging": "Lagging", "an.onPace": "On pace", "an.behind": "Behind pace", "ta.addMember": "Add member", "ta.role": "Role", "ta.tier": "Tier", "ta.shift": "Shift", "ta.zones": "Zones", "ta.status": "Status", "ta.permissions": "Permissions", "ta.classification": "Classification", "ta.activity": "Recent activity", "ta.byRole": "By role", "ta.byTier": "By tier", "ta.byShift": "By shift", "ta.all": "All", "ta.profile": "Profile", "ta.joined": "Joined", "ta.saveChanges": "Save changes", "ta.capabilities": "Capabilities", "ta.perfTitle": "Performance", "ta.editPerms": "Edit permissions",
    "ta.back": "Back to team", "ta.activityFeed": "Recent activity", "ta.thisWeek": "This week · daily output", "ta.trend30": "Output — last 30 days", "ta.vsMedian": "vs median", "ta.viewProfile": "View profile",
    "ta.suspend": "Suspend access", "ta.restore": "Restore access", "ta.suspended": "Access suspended", "ta.suspendedMsg": "This member can't sign in or be assigned work until access is restored.", "ta.newMember": "New member", "ta.fullName": "Full name", "ta.email": "Email", "ta.create": "Create member",
    "bn.title": "Bonus & incentives", "bn.thisMonth": "This month", "bn.earned": "Earned so far", "bn.projected": "Projected payout", "bn.cap": "cap", "bn.gate": "Quality gate", "bn.unlocked": "Unlocked", "bn.locked": "Locked — bonus held", "bn.raiseSla": "Reach 90% SLA to unlock full bonus", "bn.points": "Points breakdown", "bn.base": "Base output", "bn.onTime": "On-time SLA", "bn.zeroError": "Zero-error days", "bn.targetBonus": "Target-hit days", "bn.penalty": "Breach penalty", "bn.streak": "day streak", "bn.teamKicker": "Team kicker", "bn.rules": "How it works", "bn.tierMult": "Tier multiplier",
    "bn.nav": "Bonus", "bn.boardSub": "Monthly payout · coaching incentives", "bn.pool": "Total pool", "bn.avgPer": "Avg / member", "bn.unlockedN": "Unlocked", "bn.runPayout": "Run payout", "bn.weeklyTop": "Weekly top 3", "bn.teamStatus": "Team kicker", "bn.toUnlock": "to unlock team kicker", "bn.output": "Output", "bn.payout": "Projected payout", "bn.reward": "Reward",
    "nav.settings": "Settings", "set.title": "SLA & bonus settings",
    "cmd.placeholder": "Search orders, AWB, pick lists, people…", "cmd.pages": "Pages", "cmd.noResults": "No results",
    "al.title": "Notifications", "al.sub": "Live alerts & daily insights", "al.all": "All", "al.critical": "Critical", "al.warning": "Warning", "al.info": "Insights", "al.unread": "unread", "al.allRead": "All caught up — no alerts", "al.markRead": "Mark all read",
    "tr.exceptions": "Exceptions needing action", "tr.reschedule": "Reschedule pickup", "tr.markReturned": "Mark as returned", "tr.contact": "Contact customer", "tr.sync": "Sync now", "tr.lastSync": "Synced 2m ago", "tr.resolved": "resolved", "tr.trackNo": "Tracking no.", "tr.carrierMsg": "Carrier status", "tr.daysLeft": "days left", "tr.overdue": "overdue", "tr.dueToday": "due today", "tr.searchParcel": "Search DN, AWB, customer…", "tr.allStates": "All states", "tr.timeline": "Carrier timeline",
    "rs.title": "Carrier return batches", "rs.reconcile": "Reconcile", "rs.reconciled": "Reconciled", "rs.scanBack": "Scan parcels back in", "rs.missing": "missing SKUs", "rs.created": "Sales Returns created", "rs.batchOrders": "orders", "rs.batchQty": "items",
    "nav.reports": "Reports", "rp.title": "Reports", "rp.sub": "Operational analytics · export-ready", "rp.throughput": "Daily throughput", "rp.slaTrend": "SLA same-day trend", "rp.carrierPerf": "Carrier performance", "rp.zoneHeat": "Load by zone", "rp.returnsReason": "Returns by reason", "rp.channelPerf": "Channel mix", "rp.export": "Export CSV", "rp.last30": "last 30 days", "rp.last7": "last 7 days",
    "nav.routes": "Routes", "rv.title": "Delivery routes", "rv.sub": "Last-mile trips", "rv.active": "Active trips", "rv.out": "Parcels out", "rv.deliveredToday": "Delivered today", "rv.avgStops": "Avg stops", "rv.stops": "stops", "rv.driver": "Driver", "rv.eta": "ETA", "rv.track": "Track live",
    "nav.roster": "Shifts", "ro.title": "Shifts & roster", "ro.sub": "Who's on the floor today", "ro.onFloor": "on floor now", "ro.capacity": "capacity", "ro.coverage": "Coverage", "ro.scheduled": "scheduled", "ro.gap": "Understaffed", "cmd.recent": "Jump to", "od.openFull": "Open full order", "od.items": "Line items", "od.shipTo": "Ship to", "od.payment": "Payment", "od.documents": "Documents", "od.label": "AWB label", "od.packingSlip": "Packing slip", "od.invoice": "Invoice", "od.lineTotal": "Total", "od.unit": "Unit", "od.cod": "Cash on delivery", "od.grand": "Grand total", "od.status": "Fulfillment status", "od.placed": "Placed", "od.subtotal": "Subtotal", "od.shipping": "Shipping", "od.discount": "Discount", "od.tax": "Tax", "od.phone": "Phone", "od.ref": "Reference", "od.govern": "Governorate", "od.payStatus": "Payment", "od.paid": "Paid", "od.codPending": "COD · pending collection", "od.salesStatus": "Sales status", "od.trackNo": "Tracking no.", "od.delivered": "delivered", "od.linked": "Linked documents", "od.docChain": "ERPNext document chain", "od.confirmedOnly": "Confirmed orders — logistics queue", "od.salesConfirmed": "Sales confirmed", "od.activity": "Activity log", "od.activitySub": "Who changed what · ERPNext audit trail", "od.addNote": "Add a note…", "od.post": "Post", "od.noteAdded": "Note added", "od.you": "You · Supervisor", "od.attachments": "Attachments", "od.attachSub": "Proof of delivery · invoices · photos", "od.dropFiles": "Drop files or click to upload",
    "ap.smart": "Smart auto", "ap.manual": "Manual", "ap.strategy": "Grouping strategy", "ap.zone": "By zone", "ap.zoneSub": "Cluster by aisle — least walking", "ap.sku": "By SKU", "ap.skuSub": "Batch-pick same product", "ap.single": "Single-item blitz", "ap.singleSub": "All 1-line orders in one sweep", "ap.balanced": "Balanced", "ap.balancedSub": "Zone clusters, capped per picker", "ap.preview": "Generated batches", "ap.batches": "batches", "ap.walkSaved": "walk saved", "ap.generate": "Generate {n} pick lists", "ap.orders": "orders", "ap.aisles": "aisles", "ap.units": "units", "ap.assignAll": "Auto-assign to pickers", "ap.walkPath": "Walk path", "ap.optimized": "Optimized by bin", "ap.line": "line", "ap.lines": "lines", "ap.purpose": "Delivery", "ap.scanMode": "Scan mode", "ap.grouped": "Grouped SKUs", "ap.source": "Source", "ap.picked": "picked",
    "au.title": "Pick Autopilot", "au.sub": "AI agent · generates, assigns & monitors picks", "au.on": "Active", "au.off": "Paused", "au.nextRun": "Next run", "au.lastRun": "Last run", "au.todayCreated": "Created today", "au.todayAssigned": "Auto-assigned", "au.efficiency": "Efficiency gain", "au.feed": "Agent activity", "au.config": "Autopilot rules", "au.strategy": "Default strategy", "au.schedule": "Run schedule", "au.autoAssign": "Auto-assign to pickers", "au.alerts": "Watch & alert", "au.runNow": "Run now", "au.configure": "Configure", "au.enable": "Enable Autopilot", "au.disable": "Pause Autopilot", "au.thinking": "Analyzing pending orders…", "au.everyMin": "every 30 min · cutoff-aware", "au.watching": "Watching {n} active picks", "au.recos": "Suggestions", "au.apply": "Apply", "au.dismiss": "Dismiss",
    "pc.cycle": "Pick list lifecycle", "pc.created": "Created", "pc.assigned": "Assigned", "pc.picking": "Picking", "pc.completed": "Completed", "pc.toPack": "To packing", "pc.walk": "Walk path", "pc.bySku": "By SKU", "pc.byOrder": "By order", "pc.estTime": "Est. time", "pc.startPick": "Start pick", "pc.continuePick": "Continue pick", "pc.reassign": "Reassign", "pc.batchPick": "batch-pick", "pc.splits": "splits to", "pc.forOrder": "for order", "mp.mode": "Mode", "mp.selectOrders": "Select orders to pick", "mp.assignTo": "Assign to picker", "mp.createManual": "Create pick list", "mp.selected": "selected", "mp.manualHint": "Use when Autopilot needs an override — hand-pick orders & picker.",
    "sh.pickup": "Pickup", "sh.deliveryTo": "Delivery to", "sh.weight": "Total weight", "sh.pallets": "Pallets", "sh.incoterm": "Incoterm", "sh.masterAwb": "Master AWB", "sh.tracking": "Tracking", "sh.manifest": "Parcel manifest", "sh.shipType": "Shipment type", "sh.service": "Carrier service", "sh.handToCarrier": "Hand to carrier", "sh.trackAll": "Track all", "sh.contents": "Contents", "sh.contact": "Contact", "sh.scanLoad": "Scan to load", "sh.scanDn": "Scan delivery note barcode", "sh.loaded": "Loaded", "sh.loadedN": "loaded", "sh.notLoaded": "Not loaded", "sh.allLoaded": "All parcels loaded", "sh.closeHand": "Close & hand to carrier", "sh.scanned": "Scanned ✓", "sh.cutoffIn": "Carrier cutoff in", "sh.pastCutoff": "Past cutoff", "sh.searchParcel": "Search parcel, AWB, customer…", "sh.excOnly": "Exceptions only", "sh.handoverProof": "Handover proof", "sh.captureProof": "Capture signature / photo", "sh.proofDone": "Handover confirmed", "sh.bulkPrint": "Print manifests",
    "au.page": "Autopilot", "au.open": "Open Autopilot", "au.overview": "Overview", "au.rules": "Rules", "au.history": "Decision log", "au.perf": "Performance", "au.walkSavedTotal": "Walk time saved today", "au.assignAcc": "Assign accuracy", "au.runsToday": "Runs today", "au.batchThresh": "Min orders per batch", "au.zoneThresh": "Hold below threshold", "au.slaWatch": "SLA risk alerts", "au.idleReroute": "Re-route idle pickers", "au.idleMin": "Idle threshold (min)", "au.saveRules": "Save rules", "au.applied": "Applied", "au.dismissed": "Dismissed", "au.pending": "Pending", "au.allDecisions": "All agent decisions today", "c.cancel": "Cancel", "c.undo": "Undo", "c.offline": "Reconnecting… working offline", "c.queued": "actions queued", "set.sub": "Thresholds that drive SLA states and the bonus engine", "set.sla": "SLA & cutoff", "set.bonus": "Bonus engine", "set.cutoff": "Same-day cutoff", "set.sameDayTarget": "Same-day target", "set.deliveryDays": "Delivery target", "set.maxPick": "Max hrs · picking", "set.maxLabel": "Max hrs · label", "set.maxShip": "Max hrs · ship", "set.perPick": "Per pick / parcel", "set.onTime": "On-time bonus", "set.zeroError": "Zero-error day", "set.targetBonus": "Daily target bonus", "set.slaGate": "Quality gate · SLA %", "set.streakStep": "Streak step %", "set.streakCap": "Streak cap %", "set.cap": "Monthly cap", "set.kicker": "Team kicker", "set.kickerTarget": "Kicker same-day %", "set.save": "Save settings", "set.reset": "Reset", "set.synced": "Synced to ERPNext", "set.lastSynced": "Last synced", "set.justNow": "just now", "set.days": "days", "set.hrs": "hrs", "set.preview": "Live preview · sample pickers recompute instantly",
    "sb.fulfil": "Fulfillment SLA", "sb.fulfilSub": "Ship same-day before cutoff", "sb.delivery": "Delivery SLA", "sb.deliverySub": "Carrier on-time promise", "sb.onTime": "On-time delivery", "sb.daysRemaining": "Days remaining · open parcels", "sb.computed": "Computed layer — wired to ship & delivery dates",
  },
  fr: {
    _dir: "ltr", _name: "Français",
    "role.picker": "Préparateur", "role.packer": "Emballeur / Expéditeur", "role.dispatcher": "Répartiteur", "role.returns": "Retours", "role.manager": "Superviseur",
    "role.picker.home": "Ma file", "role.packer.home": "Étiquette & Manifeste", "role.dispatcher.home": "Tableau d'affectation", "role.returns.home": "File des retours", "role.manager.home": "Cockpit",
    "nav.cockpit": "Cockpit", "nav.pipeline": "Pipeline", "nav.assign": "Affectation", "nav.queue": "Ma file", "nav.label": "Étiquette & Impression", "nav.manifest": "Manifeste", "nav.returns": "Retours", "nav.tracking": "Suivi", "nav.performance": "Ma performance", "nav.team": "Équipe", "nav.alerts": "Alertes", "nav.inventory": "Réappro. zones",
    "nav.orders": "Commandes", "nav.picklists": "Prélèvements", "nav.shipments": "Expéditions", "nav.sla": "SLA", "nav.stock": "Inventaire", "nav.restocking": "Réappro.", "nav.analysis": "Analyse stock", "nav.carriers": "Transporteurs", "nav.fulfillment": "Exécution", "nav.inventoryGrp": "Stock",
    "nav.operations": "Opérations", "nav.overview": "Aperçu", "nav.me": "Moi",
    "c.search": "Commande, AWB, picking…", "c.orders": "commandes", "c.order": "Commande", "c.customer": "Client", "c.items": "articles", "c.value": "Valeur", "c.stage": "Étape", "c.sla": "SLA", "c.zone": "Zone", "c.bin": "Casier", "c.channel": "Canal", "c.picker": "Préparateur", "c.assign": "Affecter", "c.assigned": "Affecté", "c.unassigned": "Non affecté", "c.today": "Aujourd'hui", "c.parcels": "colis", "c.carrier": "Transporteur", "c.print": "Imprimer", "c.printed": "Imprimé", "c.reprint": "Réimprimer", "c.close": "Fermer", "c.viewAll": "Tout voir", "c.target": "objectif", "c.rank": "Rang", "c.of": "sur", "c.min": "min", "c.left": "restant", "c.due": "échéance", "c.scan": "Scanner", "c.confirm": "Confirmer", "c.complete": "Terminer", "c.next": "Suivant", "c.done": "Terminé", "c.qty": "Qté", "c.notifications": "Notifications", "c.markRead": "Tout marquer lu", "c.process": "Traiter", "c.restock": "Réapprovisionner", "c.reason": "Motif", "c.cutoff": "limite", "c.handToCarrier": "Clôturer & remettre", "c.timeline": "Chronologie", "c.openInErp": "Ouvrir dans ERPNext", "c.viewTimeline": "Voir le cycle complet", "c.onHand": "En stock", "c.reorder": "Pt réappro", "c.demand": "Demande 7j", "c.lowStock": "Stock bas", "c.outOfStock": "Rupture", "c.blocking": "bloque le picking", "c.fill": "taux de remplissage",
    "s.pending": "En attente", "s.picking": "Préparation", "s.picked": "Préparé", "s.labelgen": "Étiquette générée", "s.label": "Étiquette imprimée", "s.shipped": "Expédié", "s.transit": "En transit", "s.exception": "Exception", "s.delivered": "Livré", "s.returned": "Retourné", "s.oos": "Rupture de stock", "s.partial": "Partiel",
    "sla.ontrack": "Dans les temps", "sla.atrisk": "À risque", "sla.breached": "Dépassé", "sla.late": "Livré en retard", "sla.returned": "Retourné",
    "t.pending": "En attente", "t.pickedup": "Collecté", "t.intransit": "En transit", "t.outfordelivery": "En livraison", "t.delivered": "Livré", "t.exception": "Exception de livraison", "t.failed": "Tentative échouée", "t.return": "Retour",
    "ck.title": "Cockpit de l'entrepôt", "ck.sub": "En direct sur tout l'entrepôt", "ck.sameday": "Expédié le jour même", "ck.breaches": "Dépassements SLA", "ck.atrisk": "À risque", "ck.pipeline": "Pipeline", "ck.slaboard": "Tableau SLA", "ck.leaderboard": "Classement équipe", "ck.audit": "Flux d'audit", "ck.allgreen": "Tout est dans les temps", "ck.allgreenSub": "Aucun dépassement dans la dernière heure.", "ck.needsAttention": "Attention requise", "ck.drillBreach": "Commandes dépassées", "ck.channelMix": "Répartition canaux", "ck.exceptions": "Exceptions transporteur", "ck.today": "Flux du jour", "ck.intake": "Commandes reçues", "ck.shippedToday": "Expédié", "ck.toShip": "À expédier", "ck.cutoffIn": "Limite dans", "ck.afterCutoff": "Après la limite",
    "dp.title": "Tableau d'affectation", "dp.ready": "Prêtes à affecter", "dp.balance": "Équilibrez la charge entre vos préparateurs", "dp.capacity": "capacité", "dp.load": "charge", "dp.combined": "Préparation groupée", "dp.assignTo": "Affecter à", "dp.instock": "En stock", "dp.partial": "Partiel", "dp.oos": "Rupture",
    "pk.hi": "Salut", "pk.todays": "aujourd'hui", "pk.hitrate": "taux SLA", "pk.nextdue": "Prochaine échéance", "pk.queue": "Ma file", "pk.urgent": "Plus urgent d'abord", "pk.startPick": "Commencer", "pk.scanItem": "Scanner le code-barres", "pk.scanned": "Scanné", "pk.allScanned": "Tous les articles scannés", "pk.completePick": "Terminer la préparation", "pk.nicework": "Bravo", "pk.advancing": "Commande suivante…", "pk.empty": "File vide — bravo.", "pk.emptySub": "Aucune commande en attente.",
    "pc.labelQueue": "Étiquette & impression", "pc.manifestTab": "Manifeste du jour", "pc.buildManifest": "Préparer la remise du jour", "pc.running": "Total courant", "pc.addParcel": "Scanner ou ajouter un colis", "pc.cutoffIn": "Limite dans", "pc.generateLabel": "Générer AWB", "pc.recent": "Manifestes récents",
    "rt.title": "File des retours", "rt.incoming": "Retours entrants", "rt.rate": "Taux de retour", "rt.topReason": "Motif principal", "rt.inspect": "Inspecter", "rt.routeRestock": "Vers remise en stock", "rt.routeDefective": "Vers défectueux",
    "rt.open": "Ouvert", "rt.inspectS": "Inspection", "rt.restockS": "Remise en stock", "rt.closed": "Clôturé",
    "pf.title": "Ma performance", "pf.coaching": "Excellent travail — continuez", "pf.completed": "Terminé aujourd'hui", "pf.avgTime": "Temps moyen / article", "pf.vsTeam": "vs médiane équipe", "pf.toGo": "pour atteindre l'objectif", "pf.almostThere": "Presque",
    "iv.title": "Réapprovisionnement zones", "iv.sub": "Santé des casiers de l'entrepôt", "iv.needsRestock": "À réapprovisionner", "iv.healthy": "Sain", "iv.zoneHealth": "Santé des zones", "iv.restockList": "Liste de réappro",
    "ta.title": "Gestion d'équipe", "ta.sub": "Membres, rôles, permissions & performance", "ta.members": "Membres", "ta.activeNow": "Actifs", "ta.onShift": "En poste", "ta.avgSla": "SLA moyen", "ta.addMember": "Ajouter", "ta.role": "Rôle", "ta.tier": "Niveau", "ta.shift": "Poste", "ta.zones": "Zones", "ta.status": "Statut", "ta.permissions": "Permissions", "ta.classification": "Classification", "ta.activity": "Activité récente", "ta.byRole": "Par rôle", "ta.byTier": "Par niveau", "ta.byShift": "Par poste", "ta.all": "Tous", "ta.profile": "Profil", "ta.joined": "Arrivé", "ta.saveChanges": "Enregistrer", "ta.capabilities": "Capacités", "ta.perfTitle": "Performance", "ta.editPerms": "Modifier les permissions",
    "ta.back": "Retour à l'équipe", "ta.activityFeed": "Activité récente", "ta.thisWeek": "Cette semaine · sortie quotidienne", "ta.trend30": "Production — 30 derniers jours", "ta.vsMedian": "vs médiane", "ta.viewProfile": "Voir le profil", "ta.suspend": "Suspendre l'accès", "ta.restore": "Rétablir l'accès", "ta.suspended": "Accès suspendu", "ta.suspendedMsg": "Ce membre ne peut pas se connecter ni recevoir de tâches tant que l'accès n'est pas rétabli.", "ta.newMember": "Nouveau membre", "ta.fullName": "Nom complet", "ta.email": "E-mail", "ta.create": "Créer le membre",
    "bn.title": "Primes & incitations", "bn.thisMonth": "Ce mois", "bn.earned": "Gagné à ce jour", "bn.projected": "Paiement projeté", "bn.cap": "plafond", "bn.gate": "Seuil qualité", "bn.unlocked": "Débloqué", "bn.locked": "Bloqué — prime retenue", "bn.raiseSla": "Atteindre 90% SLA pour débloquer", "bn.points": "Détail des points", "bn.base": "Production de base", "bn.onTime": "SLA à temps", "bn.zeroError": "Jours sans erreur", "bn.targetBonus": "Jours objectif atteint", "bn.penalty": "Pénalité dépassement", "bn.streak": "jours de suite", "bn.teamKicker": "Bonus d'équipe", "bn.rules": "Comment ça marche", "bn.tierMult": "Multiplicateur de niveau", "bn.nav": "Primes", "bn.boardSub": "Paiement mensuel · incitations coaching", "bn.pool": "Cagnotte totale", "bn.avgPer": "Moy / membre", "bn.unlockedN": "Débloqués", "bn.runPayout": "Lancer le paiement", "bn.weeklyTop": "Top 3 de la semaine", "bn.teamStatus": "Bonus d'équipe", "bn.toUnlock": "pour débloquer le bonus d'équipe", "bn.output": "Production", "bn.payout": "Paiement projeté", "bn.reward": "Récompense",
    "nav.settings": "Paramètres", "set.title": "Paramètres SLA & primes", "set.sub": "Seuils qui pilotent les états SLA et le moteur de primes", "set.sla": "SLA & limite", "set.bonus": "Moteur de primes", "set.cutoff": "Limite jour-même", "set.sameDayTarget": "Objectif jour-même", "set.deliveryDays": "Objectif de livraison", "set.maxPick": "H max · prélèvement", "set.maxLabel": "H max · étiquette", "set.maxShip": "H max · expédition", "set.perPick": "Par prélèvement / colis", "set.onTime": "Bonus à temps", "set.zeroError": "Jour sans erreur", "set.targetBonus": "Bonus objectif quotidien", "set.slaGate": "Seuil qualité · SLA %", "set.streakStep": "Pas de série %", "set.streakCap": "Plafond série %", "set.cap": "Plafond mensuel", "set.kicker": "Bonus d'équipe", "set.kickerTarget": "Objectif jour-même bonus", "set.save": "Enregistrer", "set.reset": "Réinitialiser", "set.synced": "Synchronisé avec ERPNext", "set.lastSynced": "Dernière synchro", "set.justNow": "à l'instant", "set.days": "jours", "set.hrs": "h", "set.preview": "Aperçu en direct · recalcul instantané",
    "sb.fulfil": "SLA d'exécution", "sb.fulfilSub": "Expédier le jour même avant la limite", "sb.delivery": "SLA de livraison", "sb.deliverySub": "Promesse de ponctualité transporteur", "sb.onTime": "Livraison à temps", "sb.daysRemaining": "Jours restants · colis ouverts", "sb.computed": "Couche calculée — liée aux dates d'expédition & livraison",
  },
  ar: {
    _dir: "rtl", _name: "العربية",
    "role.picker": "مُجهِّز", "role.packer": "مُغلِّف / شاحن", "role.dispatcher": "موزِّع", "role.returns": "المرتجعات", "role.manager": "مُشرِف",
    "role.picker.home": "قائمتي", "role.packer.home": "الملصق والبيان", "role.dispatcher.home": "لوحة التوزيع", "role.returns.home": "قائمة المرتجعات", "role.manager.home": "القمرة",
    "nav.cockpit": "القمرة", "nav.pipeline": "المسار", "nav.assign": "التوزيع", "nav.queue": "قائمتي", "nav.label": "الملصق والطباعة", "nav.manifest": "البيان", "nav.returns": "المرتجعات", "nav.tracking": "التتبّع", "nav.performance": "أدائي", "nav.team": "الفريق", "nav.alerts": "التنبيهات", "nav.inventory": "تعبئة المناطق",
    "nav.orders": "الطلبات", "nav.picklists": "قوائم التجهيز", "nav.shipments": "الشحنات", "nav.sla": "اتفاقية الخدمة", "nav.stock": "المخزون", "nav.restocking": "التعبئة", "nav.analysis": "تحليل المخزون", "nav.carriers": "الناقلون", "nav.fulfillment": "التنفيذ", "nav.inventoryGrp": "المخزون",
    "nav.operations": "العمليات", "nav.overview": "نظرة عامة", "nav.me": "أنا",
    "c.search": "طلب، AWB، قائمة تجهيز…", "c.orders": "طلب", "c.order": "طلب", "c.customer": "العميل", "c.items": "عناصر", "c.value": "القيمة", "c.stage": "المرحلة", "c.sla": "اتفاقية", "c.zone": "المنطقة", "c.bin": "الرف", "c.channel": "القناة", "c.picker": "المُجهِّز", "c.assign": "إسناد", "c.assigned": "مُسنَد", "c.unassigned": "غير مُسنَد", "c.today": "اليوم", "c.parcels": "طرود", "c.carrier": "الناقل", "c.print": "طباعة", "c.printed": "مطبوع", "c.reprint": "إعادة طباعة", "c.close": "إغلاق", "c.viewAll": "عرض الكل", "c.target": "الهدف", "c.rank": "الترتيب", "c.of": "من", "c.min": "د", "c.left": "متبقٍ", "c.due": "الاستحقاق", "c.scan": "مسح", "c.confirm": "تأكيد", "c.complete": "إنهاء", "c.next": "التالي", "c.done": "تم", "c.qty": "الكمية", "c.notifications": "الإشعارات", "c.markRead": "تحديد الكل كمقروء", "c.process": "معالجة", "c.restock": "إعادة تعبئة", "c.reason": "السبب", "c.cutoff": "الموعد النهائي", "c.handToCarrier": "إغلاق وتسليم للناقل", "c.timeline": "تسلسل الطلب", "c.openInErp": "فتح في ERPNext", "c.viewTimeline": "عرض الدورة كاملة", "c.onHand": "المتوفر", "c.reorder": "نقطة الطلب", "c.demand": "طلب 7 أيام", "c.lowStock": "مخزون منخفض", "c.outOfStock": "نفد المخزون", "c.blocking": "يعيق التجهيز", "c.fill": "نسبة التعبئة",
    "s.pending": "قيد الانتظار", "s.picking": "قيد التجهيز", "s.picked": "مُجهَّز", "s.labelgen": "أُنشئ الملصق", "s.label": "طُبع الملصق", "s.shipped": "شُحن", "s.transit": "في الطريق", "s.exception": "استثناء", "s.delivered": "تم التسليم", "s.returned": "مُرتجَع", "s.oos": "نفد المخزون", "s.partial": "جزئي",
    "sla.ontrack": "ضمن الوقت", "sla.atrisk": "معرّض للخطر", "sla.breached": "متجاوَز", "sla.late": "سُلّم متأخراً", "sla.returned": "مُرتجَع",
    "t.pending": "قيد الانتظار", "t.pickedup": "تم الاستلام", "t.intransit": "في الطريق", "t.outfordelivery": "خارج للتسليم", "t.delivered": "تم التسليم", "t.exception": "استثناء تسليم", "t.failed": "محاولة فاشلة", "t.return": "إرجاع",
    "ck.title": "قمرة الأرضية", "ck.sub": "مباشر عبر الأرضية بالكامل", "ck.sameday": "شُحن نفس اليوم", "ck.breaches": "تجاوزات الاتفاقية", "ck.atrisk": "معرّض للخطر الآن", "ck.pipeline": "المسار", "ck.slaboard": "لوحة الاتفاقية", "ck.leaderboard": "ترتيب الفريق", "ck.audit": "سجل التدقيق", "ck.allgreen": "الأرضية ضمن الوقت", "ck.allgreenSub": "لا تجاوزات في الساعة الأخيرة.", "ck.needsAttention": "يتطلّب انتباهاً", "ck.drillBreach": "الطلبات المتجاوزة", "ck.channelMix": "توزيع القنوات", "ck.exceptions": "استثناءات الناقل", "ck.today": "تدفّق اليوم", "ck.intake": "طلبات واردة", "ck.shippedToday": "شُحن", "ck.toShip": "للشحن", "ck.cutoffIn": "الموعد النهائي خلال", "ck.afterCutoff": "بعد الموعد",
    "dp.title": "لوحة التوزيع", "dp.ready": "جاهزة للإسناد", "dp.balance": "وازِن الحِمل بين المُجهِّزين", "dp.capacity": "السعة", "dp.load": "الحِمل", "dp.combined": "تجهيز مجمّع", "dp.assignTo": "إسناد إلى", "dp.instock": "متوفر", "dp.partial": "جزئي", "dp.oos": "نفد",
    "pk.hi": "مرحباً", "pk.todays": "اليوم", "pk.hitrate": "نسبة الاتفاقية", "pk.nextdue": "الاستحقاق التالي", "pk.queue": "قائمتي", "pk.urgent": "الأكثر إلحاحاً أولاً", "pk.startPick": "ابدأ التجهيز", "pk.scanItem": "امسح الباركود", "pk.scanned": "تم المسح", "pk.allScanned": "تم مسح كل العناصر", "pk.completePick": "إنهاء التجهيز", "pk.nicework": "أحسنت", "pk.advancing": "تحميل الطلب التالي…", "pk.empty": "القائمة فارغة — أحسنت.", "pk.emptySub": "لا طلبات منتظرة.",
    "pc.labelQueue": "الملصق والطباعة", "pc.manifestTab": "بيان اليوم", "pc.buildManifest": "جهّز تسليم اليوم", "pc.running": "الإجمالي الجاري", "pc.addParcel": "امسح أو أضف طرداً", "pc.cutoffIn": "الموعد النهائي خلال", "pc.generateLabel": "إنشاء AWB", "pc.recent": "بيانات حديثة",
    "rt.title": "قائمة المرتجعات", "rt.incoming": "مرتجعات واردة", "rt.rate": "معدل الإرجاع", "rt.topReason": "السبب الأبرز", "rt.inspect": "فحص", "rt.routeRestock": "توجيه للمخزون", "rt.routeDefective": "توجيه للتالف",
    "rt.open": "مفتوح", "rt.inspectS": "قيد الفحص", "rt.restockS": "إعادة للمخزون", "rt.closed": "مغلق",
    "pf.title": "أدائي", "pf.coaching": "عمل رائع — واصل", "pf.completed": "أُنجز اليوم", "pf.avgTime": "متوسط الوقت / عنصر", "pf.vsTeam": "مقابل وسيط الفريق", "pf.toGo": "للوصول إلى هدفك", "pf.almostThere": "اقتربت",
    "iv.title": "تعبئة المناطق", "iv.sub": "حالة الأرفف عبر المستودع", "iv.needsRestock": "يحتاج تعبئة", "iv.healthy": "سليم", "iv.zoneHealth": "حالة المناطق", "iv.restockList": "قائمة التعبئة",
    "ta.title": "إدارة الفريق", "ta.sub": "الأعضاء، الأدوار، الصلاحيات والأداء", "ta.members": "الأعضاء", "ta.activeNow": "نشط الآن", "ta.onShift": "في المناوبة", "ta.avgSla": "متوسط الاتفاقية", "ta.addMember": "إضافة عضو", "ta.role": "الدور", "ta.tier": "الفئة", "ta.shift": "المناوبة", "ta.zones": "المناطق", "ta.status": "الحالة", "ta.permissions": "الصلاحيات", "ta.classification": "التصنيف", "ta.activity": "النشاط الأخير", "ta.byRole": "حسب الدور", "ta.byTier": "حسب الفئة", "ta.byShift": "حسب المناوبة", "ta.all": "الكل", "ta.profile": "الملف", "ta.joined": "انضم", "ta.saveChanges": "حفظ التغييرات", "ta.capabilities": "القدرات", "ta.perfTitle": "الأداء", "ta.editPerms": "تعديل الصلاحيات",
    "ta.back": "العودة للفريق", "ta.activityFeed": "النشاط الأخير", "ta.thisWeek": "هذا الأسبوع · الإنتاج اليومي", "ta.trend30": "الإنتاج — آخر 30 يوم", "ta.vsMedian": "مقابل الوسيط", "ta.viewProfile": "عرض الملف", "ta.suspend": "إيقاف الوصول", "ta.restore": "استعادة الوصول", "ta.suspended": "الوصول موقوف", "ta.suspendedMsg": "لا يمكن لهذا العضو تسجيل الدخول أو استلام مهام حتى تتم استعادة الوصول.", "ta.newMember": "عضو جديد", "ta.fullName": "الاسم الكامل", "ta.email": "البريد الإلكتروني", "ta.create": "إنشاء العضو",
    "bn.title": "المكافآت والحوافز", "bn.thisMonth": "هذا الشهر", "bn.earned": "المكتسب حتى الآن", "bn.projected": "الدفعة المتوقعة", "bn.cap": "السقف", "bn.gate": "بوابة الجودة", "bn.unlocked": "مفتوحة", "bn.locked": "مقفلة — المكافأة محتجزة", "bn.raiseSla": "حقّق 90% اتفاقية لفتح المكافأة كاملة", "bn.points": "تفصيل النقاط", "bn.base": "الإنتاج الأساسي", "bn.onTime": "اتفاقية في الوقت", "bn.zeroError": "أيام بلا أخطاء", "bn.targetBonus": "أيام تحقيق الهدف", "bn.penalty": "غرامة التجاوز", "bn.streak": "يوم متتالٍ", "bn.teamKicker": "مكافأة الفريق", "bn.rules": "كيف تعمل", "bn.tierMult": "مضاعف الفئة", "bn.nav": "المكافآت", "bn.boardSub": "دفع شهري · حوافز تدريبية", "bn.pool": "إجمالي الحصيلة", "bn.avgPer": "المتوسط / عضو", "bn.unlockedN": "مفتوحة", "bn.runPayout": "تنفيذ الدفع", "bn.weeklyTop": "أفضل 3 للأسبوع", "bn.teamStatus": "مكافأة الفريق", "bn.toUnlock": "لفتح مكافأة الفريق", "bn.output": "الإنتاج", "bn.payout": "الدفعة المتوقعة", "bn.reward": "المكافأة",
    "nav.settings": "الإعدادات", "set.title": "إعدادات الاتفاقية والمكافآت", "set.sub": "العتبات التي تتحكم في حالات الاتفاقية ومحرك المكافآت", "set.sla": "الاتفاقية والموعد النهائي", "set.bonus": "محرك المكافآت", "set.cutoff": "موعد نفس اليوم", "set.sameDayTarget": "هدف نفس اليوم", "set.deliveryDays": "هدف التسليم", "set.maxPick": "ساعات قصوى · التجهيز", "set.maxLabel": "ساعات قصوى · الملصق", "set.maxShip": "ساعات قصوى · الشحن", "set.perPick": "لكل تجهيز / طرد", "set.onTime": "مكافأة في الوقت", "set.zeroError": "يوم بلا أخطاء", "set.targetBonus": "مكافأة الهدف اليومي", "set.slaGate": "بوابة الجودة · اتفاقية %", "set.streakStep": "خطوة السلسلة %", "set.streakCap": "سقف السلسلة %", "set.cap": "السقف الشهري", "set.kicker": "مكافأة الفريق", "set.kickerTarget": "هدف نفس اليوم للمكافأة", "set.save": "حفظ الإعدادات", "set.reset": "إعادة تعيين", "set.synced": "تمت المزامنة مع ERPNext", "set.lastSynced": "آخر مزامنة", "set.justNow": "الآن", "set.days": "أيام", "set.hrs": "س", "set.preview": "معاينة مباشرة · إعادة حساب فورية",
    "sb.fulfil": "اتفاقية التنفيذ", "sb.fulfilSub": "الشحن نفس اليوم قبل الموعد", "sb.delivery": "اتفاقية التسليم", "sb.deliverySub": "التزام الناقل بالموعد", "sb.onTime": "تسليم في الوقت", "sb.daysRemaining": "الأيام المتبقية · طرود مفتوحة", "sb.computed": "طبقة محسوبة — مرتبطة بتواريخ الشحن والتسليم",
  },
};
window.LG_STRINGS = STRINGS;
window.LgContext = React.createContext({ t: (k) => k, lang: "en", dir: "ltr", setLang: () => {} });
function makeT(lang) {
  const dict = STRINGS[lang] || STRINGS.en;
  return (key) => (key in dict ? dict[key] : (STRINGS.en[key] ?? key));
}
window.makeT = makeT;
