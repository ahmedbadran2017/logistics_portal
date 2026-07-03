/* global React, I, Badge, Button, Panel, KpiCard */
const { useState } = React;

// ─────────────────────────────────────────────────────────────────────
// INVENTORY — Zone Restock. Bin health, low/out stock, pick-blocking.
// Mirrors the existing zone-restock page; real bin codes (- JM).
// ─────────────────────────────────────────────────────────────────────
function Inventory() {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [zone, setZone] = useState(null);
  const items = zone ? D.RESTOCK_ITEMS.filter((i) => i.zone === zone) : D.RESTOCK_ITEMS;
  const totalLow = D.RESTOCK.reduce((a, z) => a + z.low, 0);
  const totalOut = D.RESTOCK.reduce((a, z) => a + z.out, 0);
  const blocking = D.RESTOCK.reduce((a, z) => a + z.blocking, 0);

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <div className="mb-5">
        <h1 className="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{t("iv.title")}</h1>
        <p className="text-[12.5px] text-stone-500 mt-0.5">{t("iv.sub")} · {D.WAREHOUSE}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <KpiCard icon={I.Inventory} tone="stone" label="SKUs tracked" value={D.RESTOCK.reduce((a, z) => a + z.skus, 0)} />
        <KpiCard icon={I.AlertCircle} tone="amber" label={t("c.lowStock")} value={totalLow} />
        <KpiCard icon={I.AlertCircle} tone="rose" label={t("c.outOfStock")} value={totalOut} />
        <KpiCard icon={I.Box} tone="violet" label={t("c.blocking")} value={blocking} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.3fr] gap-4">
        {/* Zone health */}
        <Panel title={t("iv.zoneHealth")} bodyClass="p-2">
          {D.RESTOCK.map((z) => {
            const active = zone === z.zone;
            const needs = z.out > 0 || z.low > 0;
            return (
              <button key={z.zone} onClick={() => setZone(active ? null : z.zone)}
                className={`w-full text-start rounded-lg px-3 py-2.5 transition-colors ${active ? "bg-[var(--accent-50)]/50 ring-1 ring-[var(--accent-200)]" : "hover:bg-stone-50"}`}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[12.5px] font-medium text-stone-900">{z.zone}</span>
                  <div className="flex items-center gap-1.5">
                    {z.out > 0 && <Badge tone="red" dot>{z.out} out</Badge>}
                    {z.low > 0 && <Badge tone="yellow" dot>{z.low} low</Badge>}
                    {!needs && <Badge tone="green" dot>{t("iv.healthy")}</Badge>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden">
                    <div className={`h-full rounded-full ${z.fill >= 0.85 ? "bg-emerald-500" : z.fill >= 0.7 ? "bg-amber-500" : "bg-rose-500"}`} style={{ width: `${z.fill * 100}%` }} />
                  </div>
                  <span className="text-[11px] text-stone-500 tabular-nums w-[120px] text-end">{Math.round(z.fill * 100)}% {t("c.fill")} · {z.skus} SKU</span>
                </div>
                <div className="text-[10.5px] text-stone-400 mt-1 font-mono">{z.bins.join(" · ")}</div>
              </button>
            );
          })}
        </Panel>

        {/* Restock list */}
        <Panel title={t("iv.restockList")} sub={zone || "All zones"} right={<Button variant="brand" size="sm" icon={I.Upload}>Create restock task</Button>} bodyClass="p-0">
          <table className="w-full">
            <thead>
              <tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th className="text-start px-4 py-2.5">SKU</th>
                <th className="text-start px-4 py-2.5 hidden sm:table-cell">{t("c.bin")}</th>
                <th className="text-end px-4 py-2.5">{t("c.onHand")}</th>
                <th className="text-end px-4 py-2.5 hidden md:table-cell">{t("c.reorder")}</th>
                <th className="text-end px-4 py-2.5">{t("c.demand")}</th>
                <th className="text-end px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {items.map((it) => {
                const tone = { out: "red", low: "yellow", ok: "green" }[it.state];
                return (
                  <tr key={it.sku} className={it.state === "out" ? "bg-rose-50/30" : ""}>
                    <td className="px-4 py-2.5">
                      <div className="text-[12.5px] font-medium text-stone-900 truncate max-w-[160px]">{it.name}</div>
                      <div className="font-mono text-[10.5px] text-stone-400">{it.sku}</div>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-[11.5px] text-stone-500 hidden sm:table-cell">{it.bin}</td>
                    <td className="px-4 py-2.5 text-end"><span className={`text-[13px] font-semibold tabular-nums ${it.state === "out" ? "text-rose-600" : it.state === "low" ? "text-amber-600" : "text-stone-800"}`}>{it.onHand}</span></td>
                    <td className="px-4 py-2.5 text-end text-[12.5px] text-stone-500 tabular-nums hidden md:table-cell">{it.reorder}</td>
                    <td className="px-4 py-2.5 text-end text-[12.5px] text-stone-600 tabular-nums">{it.demand}</td>
                    <td className="px-4 py-2.5 text-end"><Badge tone={tone} dot>{it.state === "ok" ? t("iv.healthy") : it.state === "out" ? t("c.outOfStock") : t("c.lowStock")}</Badge></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}
window.Inventory = Inventory;
