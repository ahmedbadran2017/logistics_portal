/**
 * Realistic demo data drawn from the conception's Part VIII, used as a graceful
 * fallback so every screen renders meaningfully before the live backend is wired.
 * Pages call `withDemo(apiPromise, demoKey)` — if the API errors (method not yet
 * deployed), the demo payload is shown instead.
 */
export const DEMO = {
  queue: [
    { name: "#242615", customer: "Fouzia Fouzia", channel: "Shopify", items: 2, total: 512, stage: "Pending", sla: "At Risk", remaining: "20m", ratio: 0.15, urgent: true },
    { name: "#242613", customer: "Hasnaa Zine", channel: "YouCan", items: 1, total: 280, stage: "Pending", sla: "Breached", remaining: "40m", ratio: 0, urgent: true },
    { name: "#242611", customer: "Khadija abhaoui", channel: "Manual", items: 3, total: 349, stage: "Picked", sla: "On Track", remaining: "3h 10m", ratio: 0.7 },
    { name: "#242620", customer: "Salima Elgaadi", channel: "Landing Page", items: 5, total: 1240, stage: "Pending", sla: "On Track", remaining: "5h", ratio: 0.85 },
  ],
  pickItems: [
    { sku: "MCH100013-box", name: "Machine Box Set", bin: "X1C - JM", qty: 1, picked: 0, image: "" },
    { sku: "COS200441", name: "Cosmetic Serum 30ml", bin: "COS-A4 - JM", qty: 2, picked: 0, image: "" },
    { sku: "TXT300112", name: "Textile Wrap", bin: "TXT-B2 - JM", qty: 1, picked: 0, image: "" },
  ],
  cockpit: {
    status: "attention", // green | attention
    headline: "12 breaches — needs attention",
    shippedToday: 142, inPipeline: 318, breaches: 12, returns: 9, slaHit: 96,
    pipeline: [
      { stage: "Pending", count: 84, value: 41200 },
      { stage: "Picked", count: 63, value: 30150 },
      { stage: "In transit", count: 21, value: 9800 },
      { stage: "Label Printed", count: 48, value: 22600 },
      { stage: "Shipped", count: 142, value: 65019 },
      { stage: "Delivered", count: 96, value: 44100 },
      { stage: "Returned", count: 9, value: 3200 },
    ],
    atRisk: [
      { name: "#242615", customer: "Fouzia Fouzia", stage: "Pending", sla: "At Risk", remaining: "20m", ratio: 0.15 },
      { name: "#242613", customer: "Hasnaa Zine", stage: "Pending", sla: "Breached", remaining: "40m", ratio: 0 },
      { name: "#232609", customer: "Salima Elgaadi", stage: "Label Printed", sla: "At Risk", remaining: "55m", ratio: 0.3 },
    ],
    leaderboard: [
      { name: "Marouane El Messaoudi", role: "picker", throughput: 47, avg: "3m 10s", slaHit: 98, trend: 6 },
      { name: "Reda Zaari", role: "packer", throughput: 302, avg: "1m 40s", slaHit: 95, trend: 2 },
      { name: "Said Ennakri", role: "picker", throughput: 38, avg: "4m 02s", slaHit: 91, trend: -3 },
      { name: "Asmaa Zirary", role: "picker", throughput: 33, avg: "4m 20s", slaHit: 89, trend: -5 },
    ],
    digest: [
      { observation: "Marouane's pick time doubled after 4pm three days running.", why: "End-of-shift fatigue on the FAST zone; SLA risk rises after 16:00.", action: "Rotate a second picker into FAST after 16:00." },
      { observation: "Returns for SKU COS200441 up 40%, all from the FAST zone.", why: "Possible mis-pick or damage at that bin.", action: "Audit bin COS-A4 and recent picks." },
    ],
  },
  labels: [
    { name: "#242611", customer: "Khadija abhaoui", items: 3, carrier: "Cathedis", awb: "", status: "Picked" },
    { name: "#232609", customer: "Salima Elgaadi", items: 5, carrier: "Cathedis", awb: "LD007706673", status: "Label Generated" },
  ],
  manifest: { date: "2026-07-02", carrier: "Cathedis", cutoff: "17:00", parcels: [
    { awb: "LD007706673", order: "MAT-DN-2026-74477", customer: "Salima Elgaadi", value: 1240 },
    { awb: "LD007659616", order: "MAT-DN-2026-74476", customer: "Khadija abhaoui", value: 349 },
  ], notOnManifest: 4 },
  returns: [
    { name: "RET-26-3098119", order: "#241002", customer: "Yassine B.", awb: "LD007612000", reason: "Refused on delivery", received: "2026-07-01", status: "Returned" },
  ],
  shipments: [
    { name: "SH-000173", date: "2026-07-01", carrier: "Cathedis", parcels: 302, value: 65019, status: "Submitted" },
    { name: "SH-000172", date: "2026-06-30", carrier: "Cathedis", parcels: 288, value: 61400, status: "Submitted" },
  ],
  performance: {
    todayCount: 38, avgTime: "3m 10s", slaHit: 98, rank: 1, target: 40,
    spark: [22, 31, 28, 35, 40, 33, 38],
    bests: [{ label: "Best day", value: "52 picks" }, { label: "Best SLA", value: "100%" }],
  },
};

export async function withDemo(promise, demoKey) {
  try {
    const res = await promise;
    // Treat empty arrays/objects as "no live data yet" and prefer demo for a full UI.
    if (res == null || (Array.isArray(res) && res.length === 0)) return DEMO[demoKey];
    return res;
  } catch (_) {
    return DEMO[demoKey];
  }
}
