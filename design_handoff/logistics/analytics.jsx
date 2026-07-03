/* global React, I, Badge, Avatar, Sparkline, Button, Panel, KpiCard, StageBadge, SlaBadge, SlaRing, PageHead */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// SLA BOARD — the computed Pillar-1 layer (currently empty in ERPNext)
// ─────────────────────────────────────────────────────────────────────
function SlaBoard() {
  const { t, openOrder, go } = window.useLg();
  const D = window.LG_DATA;
  const S = D.SLA_STATS;
  const breaches = D.ORDERS.filter((o) => o.sla === "breached");
  const atRisk = D.ORDERS.filter((o) => o.sla === "atrisk");
  const late = D.ORDERS.filter((o) => o.sla === "late");

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("nav.sla")} sub={t("sb.computed")}>
        <Button variant="secondary" size="md" icon={I.Sliders}>SLA settings</Button>
      </PageHead>

      {/* hero target ring + KPIs */}
      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-4 mb-4">
        <Panel bodyClass="p-5 flex items-center gap-4">
          <SlaRing pct={S.sameDay/100} size={84} stroke={9} />
          <div>
            <div className="text-[28px] font-bold text-stone-900 tabular-nums leading-none">{S.sameDay}%</div>
            <div className="text-[12px] text-stone-500 mt-1">{t("ck.sameday")}</div>
            <div className="text-[11px] text-stone-400 mt-2">Target {S.target}% · avg ship {S.avgShipHrs}h</div>
          </div>
        </Panel>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard icon={I.AlertCircle} tone="rose" label={t("sla.breached")} value={S.breached} trend={-2} trendGood="down" spark={[3,2,4,3,2,1,2]} />
          <KpiCard icon={I.Clock} tone="amber" label={t("sla.atrisk")} value={S.atRisk} spark={[1,2,2,3,2,2,4]} />
          <KpiCard icon={I.TrendDown} tone="violet" label={t("sla.late")} value={S.deliveredLate} spark={[22,20,19,18,20,19,18]} />
          <KpiCard icon={I.Zap} tone="emerald" label="Avg ship time" value={S.avgShipHrs} unit="h" trend={-6} trendGood="down" spark={[7,6.5,6,5.8,5.5,5.4,5.4]} />
        </div>
      </div>

      {/* Delivery SLA — carrier promise, days-remaining buckets */}
      <Panel title={t("sb.delivery")} sub={t("sb.deliverySub")} className="mb-4" right={<div className="flex items-center gap-2"><span className="text-[12px] text-stone-500">{t("sb.onTime")}</span><span className="text-[15px] font-bold text-emerald-600 tabular-nums">{D.SLA_DELIVERY.onTime}%</span></div>} bodyClass="p-4">
        <div className="text-[11px] font-medium text-stone-400 uppercase tracking-wide mb-2">{t("sb.daysRemaining")}</div>
        <div className="flex items-end gap-2 h-[120px]">
          {D.SLA_DELIVERY.buckets.map((b) => {
            const max = Math.max(...D.SLA_DELIVERY.buckets.map((x) => x.count));
            return (
              <button key={b.key} onClick={() => { window.__ordersInit = { sla: b.key === "overdue" ? "breached" : b.key === "today" ? "atrisk" : "ontrack" }; go("orders"); }}
                className="flex-1 flex flex-col items-center gap-1.5 group">
                <span className={`text-[12px] font-semibold tabular-nums ${b.txt}`}><window.CountUp value={b.count} /></span>
                <div className="w-full flex items-end justify-center" style={{ height: 76 }}>
                  <div className={`w-full max-w-[44px] rounded-t-md ${b.tone} group-hover:opacity-80 transition-opacity`} style={{ height: `${(b.count / max) * 100}%` }} />
                </div>
                <span className="text-[10.5px] text-stone-500 text-center leading-tight">{b.label}</span>
              </button>
            );
          })}
        </div>
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* SLA by stage */}
        <Panel title="SLA hit-rate by stage" bodyClass="p-4 space-y-2.5">
          {D.SLA_BY_STAGE.map((r) => {
            const col = r.hit >= 92 ? "bg-emerald-500" : r.hit >= 86 ? "bg-amber-500" : "bg-rose-500";
            return (
              <div key={r.key} className="flex items-center gap-3">
                <span className="w-[96px] text-[12px] text-stone-700 truncate">{t("s." + r.key)}</span>
                <div className="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${col}`} style={{ width: `${r.hit}%` }} /></div>
                <span className="w-[40px] text-end text-[12px] font-semibold text-stone-800 tabular-nums">{r.hit}%</span>
              </div>
            );
          })}
        </Panel>

        {/* SLA by picker */}
        <Panel title="SLA hit-rate by picker" bodyClass="p-2">
          {D.LEADERBOARD.map((p) => (
            <div key={p.id} className="flex items-center gap-2.5 px-2 py-1.5">
              <Avatar name={D.byId(p.id).name} size={26} />
              <span className="text-[12.5px] text-stone-800 flex-1">{D.byId(p.id).short}</span>
              <div className="w-[90px] h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${p.sla>=90?"bg-emerald-500":p.sla>=85?"bg-amber-500":"bg-rose-500"}`} style={{ width: `${p.sla}%` }} /></div>
              <span className="w-[36px] text-end text-[12px] font-semibold text-stone-800 tabular-nums">{p.sla}%</span>
            </div>
          ))}
        </Panel>
      </div>

      {/* breach board */}
      <Panel title="Breach & at-risk board" className="mt-4" right={<Badge tone="red" dot>{breaches.length + atRisk.length} active</Badge>} bodyClass="p-0">
        <div className="divide-y divide-stone-100">
          {[...breaches, ...atRisk, ...late].map((o) => (
            <button key={o.no} onClick={() => openOrder(o.no)} className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-stone-50 text-start transition-colors">
              <span className="font-mono text-[12px] font-semibold text-stone-900 w-[88px] flex-shrink-0 truncate">{o.no}</span>
              <span className="text-[12.5px] text-stone-800 flex-1 truncate">{o.customer}</span>
              <span className="text-[11px] text-stone-400 hidden md:block w-[120px] truncate">{o.zone}</span>
              <StageBadge stage={o.stage} size="sm" />
              <SlaBadge sla={o.sla} size="sm" />
              {o.mins > 0 && <span className="text-[11px] text-stone-400 tabular-nums w-[52px] text-end">{o.mins}{t("c.min")}</span>}
            </button>
          ))}
        </div>
      </Panel>
    </div>
  );
}
window.SlaBoard = SlaBoard;

// ─────────────────────────────────────────────────────────────────────
// INVENTORY / STOCK — levels across zones
// ─────────────────────────────────────────────────────────────────────
const STOCK_TONE = { ok: "green", low: "yellow", out: "red" };
function Stock() {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const S = D.STOCK_STATS;
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [open, setOpen] = useState(null);
  const rows = D.STOCK_ITEMS.filter((it) => {
    if (filter !== "all" && it.state !== filter) return false;
    if (q && !(`${it.sku} ${it.name}`.toLowerCase().includes(q.toLowerCase()))) return false;
    return true;
  });

  if (open) return <ItemDetail it={D.STOCK_ITEMS.find((x) => x.sku === open)} onClose={() => setOpen(null)} />;

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("nav.stock")} sub={`Live from Bin · ${S.skuCount} SKUs · ${D.WAREHOUSE}`}>
        <Button variant="secondary" size="md" icon={I.Download}>Export</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <KpiCard icon={I.Inventory} tone="stone" label="Units on hand" value={window.fmtMAD(S.totalUnits)} />
        <KpiCard icon={I.Cash} tone="emerald" label="Stock value" value={window.fmtMAD(S.totalValue)} unit="MAD" />
        <KpiCard icon={I.Box} tone="violet" label="Reserved" value={S.reserved} />
        <KpiCard icon={I.AlertCircle} tone="amber" label={t("c.lowStock")} value={S.lowSku} />
        <KpiCard icon={I.AlertCircle} tone="rose" label={t("c.outOfStock")} value={S.outSku} />
      </div>

      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <I.Search width={14} height={14} className="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search SKU or product…"
            className="w-full h-9 ps-9 pe-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none" />
        </div>
        <div className="flex items-center gap-1.5">
          {[["all","All"],["ok",t("iv.healthy")],["low",t("c.lowStock")],["out",t("c.outOfStock")]].map(([k,l]) => (
            <button key={k} onClick={() => setFilter(k)} className={`px-2.5 h-7 text-[12px] font-medium rounded-lg ring-1 whitespace-nowrap ${filter===k?"bg-stone-900 text-white ring-stone-900":"bg-white text-stone-600 ring-stone-200 hover:ring-stone-300"}`}>{l}</button>
          ))}
        </div>
      </div>

      <Panel bodyClass="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead>
              <tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th className="text-start px-4 py-2.5">SKU / Product</th>
                <th className="text-start px-4 py-2.5 hidden md:table-cell">{t("c.bin")}</th>
                <th className="text-end px-4 py-2.5">{t("c.onHand")}</th>
                <th className="text-end px-4 py-2.5 hidden sm:table-cell">Reserved</th>
                <th className="text-end px-4 py-2.5">Available</th>
                <th className="text-end px-4 py-2.5 hidden md:table-cell">Projected</th>
                <th className="text-end px-4 py-2.5 hidden lg:table-cell">{t("c.reorder")}</th>
                <th className="text-end px-4 py-2.5 hidden lg:table-cell">{t("c.value")}</th>
                <th className="text-end px-4 py-2.5">State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {rows.map((it) => (
                <tr key={it.sku} onClick={() => setOpen(it.sku)} className={`cursor-pointer hover:bg-stone-50 transition-colors ${it.state === "out" ? "bg-rose-50/30" : ""}`}>
                  <td className="px-4 py-2.5"><div className="text-[12.5px] font-medium text-stone-900 truncate max-w-[180px]">{it.name}</div><div className="font-mono text-[10.5px] text-stone-400">{it.sku} · {it.zone}</div></td>
                  <td className="px-4 py-2.5 font-mono text-[11.5px] text-stone-500 hidden md:table-cell">{it.bin}</td>
                  <td className="px-4 py-2.5 text-end text-[13px] font-semibold tabular-nums"><span className={it.state==="out"?"text-rose-600":it.state==="low"?"text-amber-600":"text-stone-900"}>{it.onHand}</span></td>
                  <td className="px-4 py-2.5 text-end text-[12px] text-stone-500 tabular-nums hidden sm:table-cell">{it.reserved}</td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] font-medium text-stone-800 tabular-nums">{it.available}</td>
                  <td className="px-4 py-2.5 text-end text-[12px] tabular-nums hidden md:table-cell"><span className={(it.available + (it.incoming||0)) < it.reorder ? "text-amber-600" : "text-stone-500"}>{it.available + (it.incoming || 0)}{it.incoming ? <span className="text-emerald-500 text-[10px]"> +{it.incoming}</span> : ""}</span></td>
                  <td className="px-4 py-2.5 text-end text-[12px] text-stone-500 tabular-nums hidden lg:table-cell">{it.reorder}</td>
                  <td className="px-4 py-2.5 text-end text-[12px] text-stone-600 tabular-nums hidden lg:table-cell">{window.fmtMAD(it.value)}</td>
                  <td className="px-4 py-2.5 text-end"><Badge tone={STOCK_TONE[it.state]} dot>{it.state==="ok"?t("iv.healthy"):it.state==="out"?t("c.outOfStock"):t("c.lowStock")}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
window.Stock = Stock;

// ── Item / SKU detail page ───────────────────────────────────────────
function ItemDetail({ it, onClose }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const tone = { ok: "green", low: "yellow", out: "red" }[it.state];
  const sold30 = Math.round((it.reorder || 10) * 4.2);
  const trend = Array.from({ length: 30 }, (_, i) => Math.round((it.onHand + 30) - i * 0.8 + 8 * Math.sin(i / 3)));
  // stock spread across bins (primary + reserve)
  const bins = [
    { bin: it.bin, qty: it.onHand, zone: it.zone, primary: true },
    { bin: "Stores - JM", qty: it.incoming ? Math.round(it.incoming * 1.5) : Math.round(it.onHand * 0.6), zone: "Reserve", primary: false },
  ];
  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onClose} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"><I.Back width={15} height={15} className="rtl:rotate-180" />{t("nav.stock")}</button>

      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="w-12 h-12 rounded-xl bg-stone-100 ring-1 ring-stone-200/70 flex items-center justify-center flex-shrink-0" style={{ backgroundImage: "repeating-linear-gradient(45deg, #f5f5f4 0 6px, #ececeb 6px 12px)" }}><I.Box width={20} height={20} className="text-stone-400" /></span>
            <div><div className="flex items-center gap-2 flex-wrap"><h1 className="text-[18px] font-semibold text-stone-900">{it.name}</h1><Badge tone={tone} dot>{it.state === "ok" ? t("iv.healthy") : it.state === "out" ? t("c.outOfStock") : t("c.lowStock")}</Badge></div>
            <div className="font-mono text-[12px] text-stone-500 mt-1">{it.sku} · {it.zone}</div></div>
          </div>
          <div className="flex items-center gap-2">
            {it.state !== "ok" && <Button variant="brand" size="md" icon={I.Upload}>Material Request</Button>}
            <Button variant="secondary" size="md" iconRight={I.External}>{t("c.openInErp")}</Button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
          {[[t("c.onHand"), it.onHand], ["Available", it.available], [t("it.reorderPt"), it.reorder], [t("it.sold30"), sold30], [t("it.valuation"), window.fmtMAD(it.value) + " MAD"]].map(([k, v], i) => (
            <div key={i} className="bg-stone-50 rounded-xl px-3 py-2.5"><div className="text-[18px] font-semibold text-stone-900 tabular-nums leading-none truncate">{v}</div><div className="text-[11px] text-stone-500 mt-1">{k}</div></div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
        <Panel title={t("it.movement")} sub="Units on hand" bodyClass="p-4"><window.LineChart data={trend} height={180} /></Panel>
        <div className="space-y-4">
          <Panel title={t("it.byBin")} bodyClass="p-0">
            <div className="divide-y divide-stone-100">
              {bins.map((b, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-2.5">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-stone-900 text-white text-[11px] font-bold font-mono"><I.Pin width={10} height={10} />{b.bin}</span>
                  <span className="text-[11.5px] text-stone-500 flex-1">{b.zone.replace(" - JM", "")}{b.primary && <span className="text-[10px] text-[var(--accent-700)] ms-1">primary</span>}</span>
                  <span className="text-[12.5px] font-semibold text-stone-900 tabular-nums">{b.qty}</span>
                </div>
              ))}
            </div>
          </Panel>
          {it.incoming > 0 && (
            <Panel title={t("it.inbound")} bodyClass="p-3">
              <div className="flex items-center gap-2 rounded-lg bg-emerald-50 ring-1 ring-emerald-200/60 px-3 py-2"><I.Inventory width={14} height={14} className="text-emerald-600" /><span className="text-[12px] text-emerald-800 flex-1">+{it.incoming} units inbound</span><span className="text-[11px] text-emerald-600">Material Receipt</span></div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
window.ItemDetail = ItemDetail;

// ─────────────────────────────────────────────────────────────────────
// RESTOCKING — move tasks (Stores → zone bins)
// ─────────────────────────────────────────────────────────────────────
const RT_TONE = { pending: "yellow", inprogress: "blue", done: "green" };
const RT_LABEL = { pending: "Pending", inprogress: "In progress", done: "Done" };
function Restocking({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [rows, setRows] = useState(() => D.RESTOCK_TASKS.map((r) => ({ ...r })));
  const pending = rows.filter((r) => r.status === "pending").length;
  const inprog = rows.filter((r) => r.status === "inprogress").length;

  function advance(id) {
    setRows((rs) => rs.map((r) => {
      if (r.id !== id) return r;
      const next = r.status === "pending" ? "inprogress" : "done";
      onToast?.({ type: "success", text: `${r.id} → ${RT_LABEL[next]}` });
      return { ...r, status: next };
    }));
  }

  return (
    <div className="max-w-[1100px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("nav.restocking")} sub="Stock Entry · Material Transfer · Stores → zone bins">
        <Button variant="brand" size="md" icon={I.Plus}>New restock task</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Clock} tone="amber" label="Pending" value={pending} />
        <KpiCard icon={I.Box} tone="blue" label="In progress" value={inprog} />
        <KpiCard icon={I.CheckCircle} tone="emerald" label="Done today" value={rows.filter(r=>r.status==="done").length} />
        <KpiCard icon={I.AlertCircle} tone="rose" label="High priority" value={rows.filter(r=>r.priority==="high"&&r.status!=="done").length} />
      </div>

      <Panel bodyClass="p-0">
        <div className="divide-y divide-stone-100">
          {rows.map((r) => (
            <div key={r.id} className="flex items-center gap-3 px-4 py-3 hover:bg-stone-50 transition-colors">
              <span className="font-mono text-[12px] font-semibold text-stone-900 w-[70px] flex-shrink-0">{r.id}</span>
              <div className="min-w-0 flex-1">
                <div className="text-[12.5px] font-medium text-stone-900 truncate">{r.name}</div>
                <div className="text-[11px] text-stone-500 flex items-center gap-1.5 mt-0.5"><span className="font-mono">{r.from}</span><I.ArrowRight width={10} height={10} className="text-stone-300 rtl:rotate-180" /><span className="font-mono">{r.to}</span></div>
              </div>
              {r.priority === "high" && <Badge tone="red">High</Badge>}
              <span className="text-[12px] font-semibold text-stone-800 tabular-nums w-[48px] text-end">×{r.qty}</span>
              <div className="flex items-center gap-1.5 w-[120px]"><Avatar name={D.byId(r.assignee).name} size={20} /><span className="text-[11.5px] text-stone-600 truncate hidden sm:inline">{D.byId(r.assignee).short}</span></div>
              <div className="w-[120px] flex justify-end">
                {r.status === "done"
                  ? <Badge tone="green" dot>Done</Badge>
                  : <Button variant={r.status === "pending" ? "secondary" : "success"} size="sm" icon={r.status === "pending" ? I.Box : I.Check} onClick={() => advance(r.id)}>{r.status === "pending" ? "Start" : "Complete"}</Button>}
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
window.Restocking = Restocking;

// ─────────────────────────────────────────────────────────────────────
// STOCK ANALYSIS — movers, dead stock, return-by-SKU
// ─────────────────────────────────────────────────────────────────────
function StockAnalysis() {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const S = D.STOCK_STATS;
  const deadValue = D.DEAD_STOCK.reduce((a, d) => a + d.value, 0);

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("nav.analysis")} sub={`${D.WAREHOUSE} · last 7 days`}>
        <Button variant="secondary" size="md" icon={I.Download}>Export</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Cash} tone="emerald" label="Stock value" value={window.fmtMAD(S.totalValue)} unit="MAD" />
        <KpiCard icon={I.TrendUp} tone="cyan" label="Turnover" value={S.turnover} unit="×" trend={+5} />
        <KpiCard icon={I.Pause} tone="amber" label="Dead SKUs" value={S.deadSku} />
        <KpiCard icon={I.AlertCircle} tone="rose" label="Dead value" value={window.fmtMAD(deadValue)} unit="MAD" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* top movers */}
        <Panel title="Top movers · 7d" bodyClass="p-2">
          {D.TOP_MOVERS.map((m, i) => (
            <div key={m.sku} className="flex items-center gap-2.5 px-2 py-2 rounded-lg hover:bg-stone-50">
              <span className="w-5 text-center text-[12px] font-bold text-stone-400 tabular-nums">{i+1}</span>
              <div className="min-w-0 flex-1">
                <div className="text-[12.5px] font-medium text-stone-900 truncate">{m.name}</div>
                <div className="font-mono text-[10.5px] text-stone-400">{m.sku} · {m.zone}</div>
              </div>
              <Sparkline data={m.trend} width={56} height={20} />
              <div className="text-end w-[52px]"><div className="text-[13px] font-semibold text-stone-900 tabular-nums">{m.sold7d}</div><div className="text-[9.5px] text-stone-400 uppercase">sold</div></div>
            </div>
          ))}
        </Panel>

        {/* return by SKU */}
        <Panel title="Return rate by SKU" right={<Badge tone="amber" dot>quality signal</Badge>} bodyClass="p-0">
          <div className="divide-y divide-stone-100">
            {D.RETURN_BY_SKU.map((r) => (
              <div key={r.sku} className="flex items-center gap-3 px-4 py-2.5">
                <div className="min-w-0 flex-1"><div className="text-[12.5px] font-medium text-stone-900 truncate">{r.name}</div><div className="font-mono text-[10.5px] text-stone-400">{r.sku} · {r.reason}</div></div>
                <div className="w-[80px] h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className="h-full rounded-full bg-rose-500" style={{ width: `${Math.min(100, r.rate*8)}%` }} /></div>
                <span className="text-[12.5px] font-semibold text-rose-600 tabular-nums w-[44px] text-end">{r.rate}%</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* dead stock */}
      <Panel title="Dead / slow stock" className="mt-4" sub="Idle > 30 days — consider clearance" bodyClass="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px]">
            <thead>
              <tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th className="text-start px-4 py-2.5">SKU / Product</th>
                <th className="text-start px-4 py-2.5 hidden sm:table-cell">{t("c.zone")}</th>
                <th className="text-end px-4 py-2.5">{t("c.onHand")}</th>
                <th className="text-end px-4 py-2.5">Days idle</th>
                <th className="text-end px-4 py-2.5">{t("c.value")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {D.DEAD_STOCK.map((d) => (
                <tr key={d.sku} className="hover:bg-stone-50">
                  <td className="px-4 py-2.5"><div className="text-[12.5px] font-medium text-stone-900">{d.name}</div><div className="font-mono text-[10.5px] text-stone-400">{d.sku}</div></td>
                  <td className="px-4 py-2.5 text-[11.5px] text-stone-500 hidden sm:table-cell">{d.zone}</td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{d.onHand}</td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] text-amber-600 font-medium tabular-nums">{d.idle}d</td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] text-stone-600 tabular-nums">{window.fmtMAD(d.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
window.StockAnalysis = StockAnalysis;

// ─────────────────────────────────────────────────────────────────────
// REPORTS HUB — operational analytics, export-ready
// ─────────────────────────────────────────────────────────────────────
function Reports({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const exp = (name) => onToast?.({ type: "success", text: `${name} · CSV exported` });
  const sla30 = Array.from({ length: 30 }, (_, i) => Math.round(80 + 10 * Math.sin(i / 4) + i * 0.2));
  const tput = Array.from({ length: 30 }, (_, i) => Math.round(180 + 40 * Math.sin(i / 3) + i));
  const maxZone = Math.max(...D.RESTOCK.map((z) => z.skus));

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("rp.title")} sub={t("rp.sub")}>
        <Button variant="secondary" size="md" icon={I.Download} onClick={() => exp("All reports")}>{t("rp.export")}</Button>
      </PageHead>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <RepCard title={t("rp.throughput")} sub={t("rp.last30")} onExport={() => exp(t("rp.throughput"))}>
          <window.LineChart data={tput} height={170} />
        </RepCard>
        <RepCard title={t("rp.slaTrend")} sub={t("rp.last30")} onExport={() => exp(t("rp.slaTrend"))}>
          <window.LineChart data={sla30} height={170} stroke="#10b981" />
        </RepCard>

        <RepCard title={t("rp.carrierPerf")} sub={D.CARRIER} onExport={() => exp(t("rp.carrierPerf"))}>
          <div className="space-y-2.5 pt-1">
            {[["Delivered", 91, "bg-emerald-500"], ["Out for delivery", 38, "bg-cyan-500"], ["Exceptions", 5, "bg-rose-500"], ["Failed attempts", 2, "bg-orange-500"]].map(([l, v, c]) => (
              <div key={l} className="flex items-center gap-3"><span className="w-[120px] text-[12px] text-stone-600 truncate">{l}</span><div className="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${c}`} style={{ width: `${v}%` }} /></div><span className="w-[38px] text-end text-[12px] font-semibold text-stone-800 tabular-nums">{v}%</span></div>
            ))}
          </div>
        </RepCard>

        <RepCard title={t("rp.zoneHeat")} sub={`${D.RESTOCK.length} zones`} onExport={() => exp(t("rp.zoneHeat"))}>
          <div className="grid grid-cols-3 gap-2 pt-1">
            {D.RESTOCK.map((z) => {
              const intensity = z.skus / maxZone;
              return <div key={z.zone} className="rounded-lg p-2.5 text-center" style={{ background: `rgba(196,73,42,${0.08 + intensity * 0.32})` }}>
                <div className="text-[15px] font-semibold text-stone-900 tabular-nums">{z.skus}</div>
                <div className="text-[9.5px] text-stone-500 mt-0.5 truncate">{z.zone.replace(" - JM", "")}</div>
              </div>;
            })}
          </div>
        </RepCard>

        <RepCard title={t("rp.returnsReason")} sub={t("rp.last7")} onExport={() => exp(t("rp.returnsReason"))}>
          <div className="space-y-2 pt-1">
            {D.RETURN_BY_SKU.map((r) => (
              <div key={r.sku} className="flex items-center gap-3"><span className="flex-1 text-[12px] text-stone-700 truncate">{r.reason} · {r.name}</span><div className="w-[80px] h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className="h-full bg-rose-500 rounded-full" style={{ width: `${Math.min(100, r.rate * 8)}%` }} /></div><span className="text-[12px] font-semibold text-rose-600 tabular-nums w-[40px] text-end">{r.rate}%</span></div>
            ))}
          </div>
        </RepCard>

        <RepCard title={t("rp.channelPerf")} sub="all orders" onExport={() => exp(t("rp.channelPerf"))}>
          <div className="space-y-2.5 pt-1">
            {D.CHANNEL_MIX.map((ch) => { const c = D.CHANNELS[ch.key]; const tones = { emerald: "bg-emerald-500", violet: "bg-violet-500", amber: "bg-amber-500", slate: "bg-stone-400" }; return (
              <div key={ch.key} className="flex items-center gap-3"><span className="w-[90px] text-[12px] text-stone-600">{c.label}</span><div className="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${tones[c.tone]}`} style={{ width: `${ch.pct}%` }} /></div><span className="w-[60px] text-end text-[11.5px] text-stone-500 tabular-nums">{ch.count}</span></div>
            ); })}
          </div>
        </RepCard>
      </div>
    </div>
  );
}
window.Reports = Reports;

function RepCard({ title, sub, onExport, children }) {
  return (
    <Panel title={title} sub={sub} right={<button onClick={onExport} className="inline-flex items-center gap-1 text-[11.5px] font-medium text-stone-500 hover:text-stone-900"><I.Download width={12} height={12} />CSV</button>} bodyClass="p-4">
      {children}
    </Panel>
  );
}
