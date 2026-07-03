/* global React, I, Badge, Avatar, Button, Panel, KpiCard, PageHead */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// WAREHOUSE — smart floor map, re-slotting, cycle count, receiving, zones
// ─────────────────────────────────────────────────────────────────────
const MOVE_COLOR = { fast: "#10b981", medium: "#f59e0b", slow: "#a8a29e", reserve: "#6366f1" };
const MOVE_TONE = { fast: "green", medium: "amber", slow: "neutral", reserve: "purple" };

function Warehouse({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [tab, setTab] = useState("map");
  const tabs = [["map", t("wh.map")], ["reslot", t("wh.reslot")], ["smart", t("wh.smart")], ["count", t("wh.count")], ["restock", t("nav.restocking")], ["receiving", t("wh.receiving")], ["analysis", t("nav.analysis")], ["zones", t("wh.zones")]];

  return (
    <div className="max-w-[1320px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("wh.title")} sub={t("wh.sub")}>
        <Button variant="secondary" size="md" icon={I.Download}>Export</Button>
      </PageHead>

      <div className="flex items-center gap-1 border-b border-stone-200/70 mb-4 overflow-x-auto">
        {tabs.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} className={`px-3 h-9 text-[13px] font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${tab === k ? "border-[var(--accent-600)] text-stone-900" : "border-transparent text-stone-500 hover:text-stone-800"}`}>{l}</button>
        ))}
      </div>

      {tab === "map" && <WarehouseMap onToast={onToast} />}
      {tab === "reslot" && <Reslotting onToast={onToast} />}
      {tab === "smart" && <SmartInventory onToast={onToast} />}
      {tab === "count" && <CycleCount onToast={onToast} />}
      {tab === "restock" && <window.Restocking onToast={onToast} />}
      {tab === "receiving" && <Receiving onToast={onToast} />}
      {tab === "analysis" && <window.StockAnalysis />}
      {tab === "zones" && <ZoneOwners onToast={onToast} />}
    </div>
  );
}
// ── Smart inventory: reorder (days-cover) · ABC · bin transfer ───────
function SmartInventory({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const abc = window.LG_ABC || [];
  const reorder = window.LG_REORDER || [];
  const transfers = window.LG_BIN_TRANSFERS || [];
  const critical = reorder.filter((r) => r.cover < 1).length;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-4">
        {/* reorder alerts (days of cover) */}
        <Panel title={t("wh.reorder")} sub="Days-of-cover forecast" right={<Badge tone="red" dot>{critical} {t("wh.coverNow").toLowerCase()}</Badge>} bodyClass="p-0">
          <table className="w-full">
            <thead><tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th className="text-start px-4 py-2.5">SKU</th><th className="text-end px-4 py-2.5">{t("c.onHand")}</th><th className="text-end px-4 py-2.5 hidden sm:table-cell">{t("c.demand")}</th><th className="text-start px-4 py-2.5 w-[120px]">{t("wh.daysCover")}</th><th className="px-4 py-2.5"></th>
            </tr></thead>
            <tbody className="divide-y divide-stone-100">
              {reorder.map((r) => { const crit = r.cover < 1; const cap = Math.min(1, r.cover / 7); return (
                <tr key={r.sku} className={crit ? "bg-rose-50/30" : ""}>
                  <td className="px-4 py-2.5"><div className="flex items-center gap-1.5"><span className={`text-[9px] font-bold w-4 h-4 rounded flex items-center justify-center ${r.cls === "A" ? "bg-emerald-100 text-emerald-700" : r.cls === "B" ? "bg-amber-100 text-amber-700" : "bg-stone-100 text-stone-500"}`}>{r.cls}</span><div><div className="text-[12px] font-medium text-stone-900 truncate max-w-[150px]">{r.name}</div><div className="font-mono text-[10px] text-stone-400">{r.sku}</div></div></div></td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] font-semibold tabular-nums"><span className={crit ? "text-rose-600" : "text-stone-900"}>{r.onHand}</span></td>
                  <td className="px-4 py-2.5 text-end text-[12px] text-stone-500 tabular-nums hidden sm:table-cell">{r.daily}/d</td>
                  <td className="px-4 py-2.5"><div className="flex items-center gap-2"><div className="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${Math.max(4, cap * 100)}%`, background: crit ? "#ef4444" : r.cover < 3 ? "#f59e0b" : "#10b981" }} /></div><span className={`text-[11px] tabular-nums w-[34px] ${crit ? "text-rose-600 font-medium" : "text-stone-500"}`}>{r.cover === 0 ? "0d" : r.cover + "d"}</span></div></td>
                  <td className="px-4 py-2.5 text-end">{crit && <Button variant="secondary" size="sm" icon={I.Upload} onClick={() => onToast?.({ type: "success", text: `Material Request drafted · ${r.sku} ×${r.reorder}` })}>PO</Button>}</td>
                </tr>
              ); })}
            </tbody>
          </table>
        </Panel>

        {/* ABC analysis */}
        <Panel title={t("wh.abc")} sub="By pick velocity" bodyClass="p-4">
          <div className="flex h-3 rounded-full overflow-hidden mb-4">
            {abc.map((a) => <div key={a.cls} style={{ width: `${a.share}%`, background: a.color }} />)}
          </div>
          <div className="space-y-2.5">
            {abc.map((a) => (
              <div key={a.cls} className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-lg flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0" style={{ background: a.color }}>{a.cls}</span>
                <div className="min-w-0 flex-1"><div className="text-[12px] font-medium text-stone-900">{a.skus} SKUs · {a.share}% of picks</div><div className="text-[11px] text-stone-500 truncate">{a.note}</div></div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* bin-to-bin transfer */}
      <Panel title={t("wh.transfer")} sub="Scan source → destination" bodyClass="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
          <button className="flex items-center gap-3 px-4 h-12 rounded-xl ring-2 ring-stone-300 bg-white hover:ring-stone-400 transition-all" onClick={() => onToast?.({ type: "success", text: "Source bin scanned" })}><span className="w-8 h-8 rounded-lg bg-stone-900 text-white flex items-center justify-center flex-shrink-0"><I.Search width={15} height={15} /></span><span className="text-[13px] font-medium text-stone-600">{t("wh.scanFrom")}</span></button>
          <button className="flex items-center gap-3 px-4 h-12 rounded-xl ring-2 ring-stone-300 bg-white hover:ring-stone-400 transition-all" onClick={() => onToast?.({ type: "success", text: "Destination bin scanned · transfer logged" })}><span className="w-8 h-8 rounded-lg bg-emerald-500 text-white flex items-center justify-center flex-shrink-0"><I.Pin width={15} height={15} /></span><span className="text-[13px] font-medium text-stone-600">{t("wh.scanTo")}</span></button>
        </div>
        <div className="divide-y divide-stone-100 -mx-4">
          {transfers.map((tr) => (
            <div key={tr.id} className="flex items-center gap-3 px-4 py-2.5">
              <span className="font-mono text-[11.5px] font-semibold text-stone-900 w-[60px]">{tr.id}</span>
              <span className="font-mono text-[11px] text-stone-600 flex-1 truncate">{tr.sku} · {tr.from.replace(" - JM","")} → {tr.to}</span>
              <span className="text-[12px] font-semibold text-stone-800 tabular-nums">×{tr.qty}</span>
              <Badge tone={tr.status === "done" ? "green" : "blue"} dot>{tr.status === "done" ? "Done" : "In progress"}</Badge>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
window.Warehouse = Warehouse;

// ── Floor map + density heatmap ──────────────────────────────────────
function WarehouseMap({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const M = D.LG_WAREHOUSE_MAP || window.LG_WAREHOUSE_MAP;
  const [sel, setSel] = useState(null);
  const totSku = M.zones.reduce((a, z) => a + z.skus, 0);
  const totUnits = M.zones.reduce((a, z) => a + z.units, 0);
  const cell = 96, gap = 8;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
      <Panel title="Floor plan" sub="Capacity fill · click a zone" right={
        <div className="flex items-center gap-2.5">
          {[["fast", t("wh.fast")], ["slow", t("wh.slow")], ["reserve", t("wh.reserve")]].map(([k, l]) => (
            <span key={k} className="inline-flex items-center gap-1 text-[10.5px] text-stone-500"><span className="w-2.5 h-2.5 rounded-sm" style={{ background: MOVE_COLOR[k] }} />{l}</span>
          ))}
        </div>
      } bodyClass="p-4 overflow-x-auto">
        <div className="relative mx-auto" style={{ width: M.cols * cell + (M.cols - 1) * gap, height: M.rows * cell + (M.rows - 1) * gap }}>
          {M.zones.map((z) => {
            const fill = z.units / z.cap;
            const col = MOVE_COLOR[z.move];
            const active = sel === z.id;
            return (
              <button key={z.id} onClick={() => setSel(z.id)}
                className={`absolute rounded-xl ring-1 p-2.5 text-start transition-all overflow-hidden ${active ? "ring-2 ring-stone-900 z-10" : "ring-stone-200 hover:ring-stone-400"}`}
                style={{ left: z.col * (cell + gap), top: z.row * (cell + gap), width: z.w * cell + (z.w - 1) * gap, height: z.h * cell + (z.h - 1) * gap, background: `color-mix(in oklab, ${col} ${Math.round(fill * 55 + 8)}%, white)` }}>
                <div className="flex items-center justify-between">
                  <span className="text-[12.5px] font-bold text-stone-900">{z.short}</span>
                  <span className="w-2 h-2 rounded-full" style={{ background: col }} />
                </div>
                <div className="text-[10.5px] text-stone-600 mt-0.5">{z.skus} {t("wh.skus")}</div>
                <div className="absolute bottom-2 start-2.5 end-2.5">
                  <div className="flex items-center justify-between text-[10px] text-stone-600 mb-0.5"><span className="tabular-nums">{Math.round(fill * 100)}%</span><span className="font-mono">{z.aisles.join(" ")}</span></div>
                  <div className="h-1.5 rounded-full bg-white/60 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${fill * 100}%`, background: col }} /></div>
                </div>
              </button>
            );
          })}
        </div>
      </Panel>

      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <KpiCard icon={I.Inventory} tone="stone" label={t("wh.skus")} value={totSku} />
          <KpiCard icon={I.Box} tone="violet" label={t("wh.units")} value={window.fmtMAD(totUnits)} />
        </div>
        {sel ? (() => {
          const z = M.zones.find((x) => x.id === sel); const fill = z.units / z.cap;
          return (
            <Panel title={z.short} sub={z.id} bodyClass="p-4 space-y-3">
              <div className="flex items-center gap-2"><Badge tone={MOVE_TONE[z.move]} dot>{t("wh." + z.move)} {t("wh.velocity").toLowerCase()}</Badge></div>
              <div className="grid grid-cols-2 gap-2">
                <WhStat label={t("wh.skus")} value={z.skus} />
                <WhStat label={t("wh.units")} value={z.units} />
                <WhStat label={t("wh.fill")} value={Math.round(fill * 100) + "%"} />
                <WhStat label={t("wh.picks7d")} value={z.picks7d} />
              </div>
              <div className="flex items-center gap-2 pt-1"><span className="text-[11px] text-stone-500">{t("wh.owner")}</span><Avatar name={D.byId(z.owner).name} size={22} /><span className="text-[12px] font-medium text-stone-800">{D.byId(z.owner).short}</span></div>
              <div className="text-[11px] text-stone-500">Aisles <span className="font-mono text-stone-700">{z.aisles.join(" · ")}</span></div>
            </Panel>
          );
        })() : (
          <Panel title={t("wh.density")} bodyClass="p-3 space-y-1.5">
            {M.zones.map((z) => { const fill = z.units / z.cap; return (
              <button key={z.id} onClick={() => setSel(z.id)} className="w-full flex items-center gap-2.5 px-1.5 py-1.5 rounded-lg hover:bg-stone-50 text-start">
                <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: MOVE_COLOR[z.move] }} />
                <span className="text-[12px] text-stone-700 flex-1 truncate">{z.short}</span>
                <div className="w-[70px] h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${fill * 100}%`, background: MOVE_COLOR[z.move] }} /></div>
                <span className="text-[11px] text-stone-500 tabular-nums w-[34px] text-end">{Math.round(fill * 100)}%</span>
              </button>
            ); })}
          </Panel>
        )}
      </div>
    </div>
  );
}
function WhStat({ label, value }) {
  return <div className="bg-stone-50 rounded-lg px-3 py-2"><div className="text-[16px] font-semibold text-stone-900 tabular-nums leading-none">{value}</div><div className="text-[10.5px] text-stone-500 mt-1">{label}</div></div>;
}

// ── Re-slotting (velocity-based moves) ───────────────────────────────
function Reslotting({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [rows, setRows] = useState(() => (window.LG_RESLOT || []).map((r) => ({ ...r })));
  const [moving, setMoving] = useState({});
  function startMove(sku) { setMoving((m) => ({ ...m, [sku]: 0 })); }
  function step(sku) { setMoving((m) => { const s = (m[sku] || 0) + 1; if (s >= 2) { setTimeout(() => { setRows((rs) => rs.filter((r) => r.sku !== sku)); onToast?.({ type: "success", text: "Re-slot complete · Material Transfer posted" }); }, 400); } return { ...m, [sku]: s }; }); }
  return (
    <div>
      <div className="rounded-xl bg-[var(--accent-50)]/50 ring-1 ring-[var(--accent-200)]/50 px-4 py-3 mb-4 flex items-center gap-3">
        <I.Zap width={18} height={18} className="text-[var(--accent-600)] flex-shrink-0" />
        <div className="text-[12.5px] text-stone-700 flex-1"><span className="font-semibold">{rows.length} {t("wh.suggested").toLowerCase()}</span> — fast movers in slow slots & dead stock in prime bins.</div>
        <Button variant="secondary" size="sm" icon={I.Zap} onClick={() => onToast?.({ type: "success", text: `${rows.length} moves sent to Pick Autopilot` })}>{t("wh.autopilotTie")}</Button>
      </div>
      <div className="space-y-2.5">
        {rows.map((r) => (
          <div key={r.sku} className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-stone-900">{r.name}</div>
                <div className="font-mono text-[10.5px] text-stone-400">{r.sku} · {r.picks7d} {t("wh.picks7d")}</div>
              </div>
              <div className="flex items-center gap-2"><Badge tone="amber">{r.gain}</Badge>{moving[r.sku] === undefined && <Button variant="brand" size="sm" icon={I.ArrowRight} onClick={() => startMove(r.sku)}>{t("wh.applyMove")}</Button>}</div>
            </div>
            {moving[r.sku] !== undefined ? (
              <div className="grid grid-cols-2 gap-2 mt-3">
                <button onClick={() => moving[r.sku] < 1 && step(r.sku)} className={`flex items-center gap-2 px-3 h-12 rounded-xl ring-2 transition-all ${moving[r.sku] >= 1 ? "ring-emerald-300 bg-emerald-50/50" : "ring-stone-300 bg-white hover:ring-stone-400"}`}><span className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${moving[r.sku] >= 1 ? "bg-emerald-500 text-white" : "bg-stone-900 text-white"}`}>{moving[r.sku] >= 1 ? <I.Check width={15} height={15} /> : <I.Search width={14} height={14} />}</span><div className="text-start"><div className="text-[11px] text-stone-500">{t("rl.scanSource")}</div><div className="font-mono text-[11px] font-medium text-stone-800">{r.fromBin}</div></div></button>
                <button onClick={() => moving[r.sku] >= 1 && step(r.sku)} disabled={moving[r.sku] < 1} className={`flex items-center gap-2 px-3 h-12 rounded-xl ring-2 transition-all ${moving[r.sku] >= 2 ? "ring-emerald-300 bg-emerald-50/50" : moving[r.sku] < 1 ? "ring-stone-200 bg-stone-50 opacity-50" : "ring-stone-300 bg-white hover:ring-stone-400"}`}><span className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${moving[r.sku] >= 2 ? "bg-emerald-500 text-white" : "bg-emerald-500/80 text-white"}`}><I.Pin width={14} height={14} /></span><div className="text-start"><div className="text-[11px] text-stone-500">{t("rl.scanDest")}</div><div className="font-mono text-[11px] font-medium text-stone-800">{r.toBin}</div></div></button>
              </div>
            ) : (
            <div className="flex items-center gap-3 mt-3">
              <div className="flex-1 rounded-lg bg-stone-50 ring-1 ring-stone-200/60 px-3 py-2"><div className="text-[10px] text-stone-400 uppercase tracking-wide">{t("wh.from")}</div><div className="text-[12px] font-medium text-stone-800">{r.from.replace(" - JM", "")}</div><div className="font-mono text-[10.5px] text-stone-500">{r.fromBin}</div></div>
              <I.ArrowRight width={16} height={16} className="text-stone-400 flex-shrink-0 rtl:rotate-180" />
              <div className="flex-1 rounded-lg bg-emerald-50 ring-1 ring-emerald-200/60 px-3 py-2"><div className="text-[10px] text-emerald-600 uppercase tracking-wide">{t("wh.to")}</div><div className="text-[12px] font-medium text-stone-800">{r.to.replace(" - JM", "")}</div><div className="font-mono text-[10.5px] text-stone-500">{r.toBin}</div></div>
            </div>
            )}
            <div className="text-[11px] text-stone-500 mt-2 flex items-center gap-1.5"><I.Info width={11} height={11} />{r.reason}</div>
          </div>
        ))}
        {rows.length === 0 && <div className="text-center text-[12.5px] text-emerald-600 py-12 flex items-center justify-center gap-1.5"><I.CheckCircle width={16} height={16} />All slots optimized</div>}
      </div>
    </div>
  );
}

// ── Cycle count (scan-based stock take) ──────────────────────────────
const SC_TONE = { scheduled: "neutral", counting: "blue", review: "amber", done: "green" };
function CycleCount({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const counts = window.LG_CYCLE_COUNTS || [];
  const variances = window.LG_CYCLE_VARIANCES || [];
  const P = window.LG_COUNT_PLAN || {};
  const [active, setActive] = useState(counts.find((c) => c.status === "review") || counts[0]);
  const [open, setOpen] = useState(null);
  const [creating, setCreating] = useState(false);
  const covPct = (P.coverage || 0) / 100;
  const r = 30, circ = 2 * Math.PI * r;

  if (open) return <CountDetail count={counts.find((c) => c.no === open)} onClose={() => setOpen(null)} onToast={onToast} />;

  return (
    <div className="space-y-4">
      {/* SMART COUNT PLANNER */}
      <div className="rounded-2xl ring-1 ring-[var(--accent-300)]/50 bg-gradient-to-br from-[var(--accent-50)]/50 to-white p-4">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
          <div className="flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-xl bg-gradient-to-br from-[var(--accent-500)] to-[var(--accent-700)] text-white flex items-center justify-center"><I.Zap width={18} height={18} /></span>
            <div><div className="text-[14.5px] font-semibold text-stone-900">{t("wh.planner")}</div><div className="text-[11.5px] text-stone-500">{t("wh.autoPlan")}</div></div>
          </div>
          <Button variant="brand" size="md" icon={I.Search} onClick={() => setCreating(true)}>{t("wh.startToday")}</Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-[180px_1fr] gap-4">
          {/* coverage ring */}
          <div className="flex items-center gap-3 bg-white rounded-xl ring-1 ring-stone-200/60 p-3">
            <svg width="74" height="74" className="-rotate-90 flex-shrink-0"><circle cx="37" cy="37" r={r} fill="none" stroke="#f0eeec" strokeWidth="7" /><circle cx="37" cy="37" r={r} fill="none" stroke="#10b981" strokeWidth="7" strokeDasharray={circ} strokeDashoffset={circ * (1 - covPct)} strokeLinecap="round" /></svg>
            <div><div className="text-[20px] font-bold text-stone-900 tabular-nums leading-none">{P.coverage}%</div><div className="text-[11px] text-stone-500 mt-1">{t("wh.coverage")}</div><div className="text-[10px] text-stone-400 mt-0.5">{P.countedSkus}/{P.totalSkus} · {P.period}</div></div>
          </div>
          {/* today + cadence */}
          <div className="space-y-3">
            <div className="flex items-center gap-3 rounded-xl bg-white ring-1 ring-stone-200/60 px-3 py-2.5">
              <I.Calendar width={16} height={16} className="text-[var(--accent-600)] flex-shrink-0" />
              <div className="flex-1 text-[12.5px] text-stone-700"><span className="font-semibold">{t("wh.todayCount")}:</span> {P.today.bins} bins · {P.today.skus} SKUs · ≈{P.today.mins} min</div>
              <span className="text-[11px] text-stone-400 hidden sm:block">{P.today.zones.map((z) => z.replace(" - JM", "")).join(", ")}</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {(P.cadence || []).map((c) => (
                <div key={c.cls} className="rounded-xl bg-white ring-1 ring-stone-200/60 p-2.5">
                  <div className="flex items-center gap-1.5"><span className="w-5 h-5 rounded text-[10px] font-bold text-white flex items-center justify-center" style={{ background: c.color }}>{c.cls}</span><span className="text-[11px] font-medium text-stone-700">{c.every}</span></div>
                  <div className="text-[11px] text-stone-500 mt-1.5">{c.skus} SKUs · <span className="text-amber-600 font-medium">{c.due} {t("wh.due")}</span></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-[13px] font-semibold text-stone-700">{t("wh.count")} · Stock Reconciliations</span>
        <Button variant="secondary" size="md" icon={I.Plus} onClick={() => setCreating(true)}>{t("wh.newCount")}</Button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <Panel bodyClass="p-0">
          <div className="divide-y divide-stone-100">
            {counts.map((c) => (
              <button key={c.no} onClick={() => setOpen(c.no)} className={`w-full grid grid-cols-[170px_1fr_auto_auto] items-center gap-3 px-4 py-3 text-start transition-colors hover:bg-stone-50`}>
                <span className="font-mono text-[11.5px] font-semibold text-stone-900">{c.no}</span>
                <div className="min-w-0"><div className="text-[12.5px] text-stone-800 truncate flex items-center gap-1.5"><span className={`text-[9px] font-bold w-4 h-4 rounded flex items-center justify-center ${c.cls === "A" ? "bg-emerald-100 text-emerald-700" : c.cls === "B" ? "bg-amber-100 text-amber-700" : "bg-stone-100 text-stone-500"}`}>{c.cls}</span>{c.zone.replace(" - JM", "")}</div><div className="text-[11px] text-stone-500">{c.counted}/{c.bins} bins{c.variances > 0 ? ` · ${c.variances} var` : ""}</div></div>
                <Avatar name={D.byId(c.owner).name} size={22} />
                <Badge tone={SC_TONE[c.status]} dot className="whitespace-nowrap">{c.status}</Badge>
              </button>
            ))}
          </div>
        </Panel>
      </div>
      {creating && <CreateCount onClose={() => setCreating(false)} onToast={onToast} />}
    </div>
  );
}

// ── Count detail — guided cycle flow (full page) ─────────────────────
function CountDetail({ count, onClose, onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const stages = ["scheduled", "counting", "review", "posted"];
  // build deterministic bins for the zone
  const aisle = (D.LG_WAREHOUSE_MAP || window.LG_WAREHOUSE_MAP).zones.find((z) => z.id === count.zone)?.aisles?.[0] || "J8";
  const bins = useMemo(() => Array.from({ length: count.bins }).map((_, i) => {
    const exp = 8 + (i * 13) % 40;
    const off = (count.no.charCodeAt(6) + i) % 11 === 0 ? -2 : (i % 17 === 0 ? 1 : 0);
    return { bin: `${aisle}${String.fromCharCode(65 + (i % 6))}${i % 9} - JM`, expected: exp, found: exp + off, off };
  }), [count.no]);
  const startStage = count.status === "done" ? 3 : count.status === "review" ? 2 : count.status === "counting" ? 1 : 0;
  const [stage, setStage] = useState(startStage);
  const [counted, setCounted] = useState(() => stage >= 2 ? bins.length : count.counted);
  const done = stage >= 2 ? bins.length : counted;
  const varList = bins.filter((b) => b.off !== 0);

  function scan() { const n = Math.min(bins.length, counted + 1); setCounted(n); if (n >= bins.length) setStage(2); }

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onClose} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"><I.Back width={15} height={15} className="rtl:rotate-180" />{t("wh.count")}</button>

      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="w-11 h-11 rounded-xl bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center"><I.Inventory width={22} height={22} /></span>
            <div><div className="flex items-center gap-2 flex-wrap"><h1 className="font-mono text-[17px] font-bold text-stone-900">{count.no}</h1><Badge tone={count.cls === "A" ? "green" : count.cls === "B" ? "amber" : "neutral"}>{count.cls} class</Badge></div>
            <div className="text-[12.5px] text-stone-600 mt-1 flex items-center gap-2"><Avatar name={D.byId(count.owner).name} size={20} />{D.byId(count.owner).short} · {count.zone.replace(" - JM", "")}</div></div>
          </div>
        </div>
        {/* stepper */}
        <div className="flex items-center mt-5">
          {stages.map((s, i) => { const dn = i <= stage; return (
            <React.Fragment key={s}>
              <div className="flex flex-col items-center gap-1.5 flex-shrink-0" style={{ width: 110 }}>
                <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold ${dn ? "bg-emerald-500 text-white" : "bg-stone-100 text-stone-400"}`}>{dn ? <I.Check width={14} height={14} /> : i + 1}</span>
                <span className={`text-[11px] font-medium ${dn ? "text-stone-900" : "text-stone-400"}`}>{t("cc." + s)}</span>
              </div>
              {i < stages.length - 1 && <div className={`flex-1 h-0.5 -mt-6 ${i < stage ? "bg-emerald-300" : "bg-stone-200"}`} />}
            </React.Fragment>
          ); })}
        </div>
        <div className="text-[11.5px] text-stone-500 mt-4 flex items-center gap-1.5 rounded-lg bg-stone-50 px-3 py-2"><I.Info width={13} height={13} className="text-stone-400 flex-shrink-0" />{t("cc.howto")}</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
        {/* bins checklist */}
        <Panel title={t("cc.bins")} sub={`${done}/${bins.length}`} right={<Badge tone={done >= bins.length ? "green" : "blue"} dot>{Math.round(done/bins.length*100)}%</Badge>} bodyClass="p-0">
          {stage < 2 && (
            <div className="p-4 border-b border-stone-100">
              <button onClick={scan} disabled={done >= bins.length} className={`w-full flex items-center gap-3 px-4 h-14 rounded-2xl ring-2 transition-all active:scale-[0.99] ${done >= bins.length ? "ring-emerald-300 bg-emerald-50/50" : "ring-stone-300 bg-white hover:ring-stone-400"}`}>
                <span className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${done >= bins.length ? "bg-emerald-500 text-white" : "bg-stone-900 text-white"}`}><I.Search width={18} height={18} /></span>
                <span className="text-[14px] font-medium text-stone-600 flex-1 text-start">{t("cc.scanNext")}</span>
              </button>
            </div>
          )}
          <div className="divide-y divide-stone-100 max-h-[420px] overflow-y-auto">
            {bins.map((b, i) => {
              const cd = i < done;
              return (
                <div key={i} className={`grid grid-cols-[24px_1fr_auto_auto] items-center gap-3 px-4 py-2.5 ${cd ? "" : "opacity-50"}`}>
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${cd ? (b.off !== 0 ? "bg-amber-500 text-white" : "bg-emerald-500 text-white") : "ring-1 ring-stone-300"}`}>{cd && (b.off !== 0 ? <I.AlertCircle width={11} height={11} /> : <I.Check width={11} height={11} />)}</span>
                  <span className="font-mono text-[11.5px] font-semibold text-stone-900">{b.bin}</span>
                  <span className="text-[11px] text-stone-400 tabular-nums">{t("cc.expected")} {b.expected}</span>
                  {cd ? (b.off !== 0 ? <Badge tone="amber" dot>{t("cc.off")} {b.off > 0 ? "+" : ""}{b.off}</Badge> : <Badge tone="green" dot>{t("cc.match")}</Badge>) : <span className="text-[11px] text-stone-300">—</span>}
                </div>
              );
            })}
          </div>
        </Panel>

        {/* right: variances + actions */}
        <div className="space-y-4">
          <Panel title={t("wh.variance")} right={varList.length > 0 && stage >= 1 && <Badge tone="amber" dot>{varList.length}</Badge>} bodyClass="p-0">
            {stage >= 1 && varList.length > 0 ? (
              <div className="divide-y divide-stone-100">
                {varList.map((b, i) => (
                  <div key={i} className="flex items-center gap-3 px-4 py-2.5">
                    <span className="font-mono text-[11.5px] text-stone-700 flex-1">{b.bin}</span>
                    <span className="text-[11px] text-stone-400">{t("cc.expected")} {b.expected}</span>
                    <span className="text-[11px] text-stone-600">{t("cc.found")} {b.found}</span>
                    <Badge tone="rose" dot>{b.off > 0 ? "+" : ""}{b.off}</Badge>
                  </div>
                ))}
                <div className="px-4 py-2.5"><Button variant="secondary" size="sm" icon={I.Clock} className="w-full">{t("cc.recountBin")}</Button></div>
              </div>
            ) : <div className="text-center text-[12px] text-stone-400 py-6">{stage < 1 ? "Start counting to see variances" : "No variances ✓"}</div>}
          </Panel>

          {/* primary action by stage */}
          <Panel bodyClass="p-4">
            {stage === 0 && <Button variant="brand" size="lg" icon={I.Search} className="w-full" onClick={() => setStage(1)}>{t("cc.startCount")}</Button>}
            {stage === 1 && <Button variant="secondary" size="lg" icon={I.CheckCircle} className="w-full" disabled={done < bins.length} onClick={() => setStage(2)}>{t("cc.toReview")}</Button>}
            {stage === 2 && <Button variant="success" size="lg" icon={I.CheckCircle} className="w-full" onClick={() => { setStage(3); onToast?.({ type: "success", text: `${count.no} posted as Stock Reconciliation` }); }}>{t("cc.confirmPost")}</Button>}
            {stage === 3 && <div className="text-center text-[12.5px] text-emerald-600 font-medium py-2 flex items-center justify-center gap-1.5"><I.CheckCircle width={16} height={16} />Posted as Stock Reconciliation</div>}
          </Panel>
        </div>
      </div>
    </div>
  );
}

// ── Create cycle count modal ─────────────────────────────────────────
function CreateCount({ onClose, onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const M = window.LG_WAREHOUSE_MAP;
  const pickers = D.TEAM.filter((p) => p.role === "picker" || p.role === "packer");
  const [method, setMethod] = useState("zone");
  const [zone, setZone] = useState(M.zones[0].id);
  const [owner, setOwner] = useState(pickers[0].id);
  const [when, setWhen] = useState("now");
  const [blind, setBlind] = useState(true);
  const z = M.zones.find((x) => x.id === zone);
  const estBins = method === "abc" ? 28 : Math.round((z.skus || 20) / 4);
  const estTime = Math.round(estBins * 1.2);
  function create() {
    onToast?.({ type: "success", text: `Cycle count created · ${z.short} · ${estBins} bins · ${D.byId(owner).short}` });
    onClose();
  }
  return (
    <window.LgModal title={t("nc.title")} sub="Stock Reconciliation" onClose={onClose}
      footer={<>
        <Button variant="ghost" size="md" onClick={onClose}>{t("c.cancel")}</Button>
        <Button variant="brand" size="md" icon={I.Check} onClick={create}>{t("nc.create")}</Button>
      </>}>
      <div className="space-y-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{t("nc.method")}</div>
          <div className="grid grid-cols-3 gap-1.5">
            {[["zone", t("nc.byZone"), I.Pin], ["abc", t("nc.byAbc"), I.TrendUp], ["bin", t("nc.byBin"), I.Box]].map(([k, l, Ic]) => (
              <button key={k} onClick={() => setMethod(k)} className={`flex flex-col items-center gap-1 px-2 py-2.5 rounded-lg ring-1 transition-all ${method === k ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40" : "ring-stone-200 hover:ring-stone-300"}`}><Ic width={15} height={15} className={method === k ? "text-[var(--accent-700)]" : "text-stone-400"} /><span className="text-[11.5px] font-medium text-stone-800">{l}</span></button>
            ))}
          </div>
        </div>
        {method === "abc" ? (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">ABC class</div>
            <div className="grid grid-cols-3 gap-1.5">{["A","B","C"].map((c) => <button key={c} className={`h-9 rounded-lg ring-1 text-[12px] font-semibold ${c==="A"?"ring-[var(--accent-400)] bg-[var(--accent-50)]/40":"ring-stone-200"}`}>{c} class</button>)}</div>
          </div>
        ) : (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{t("nc.pickZone")}</div>
            <div className="grid grid-cols-2 gap-1.5">
              {M.zones.filter((x) => x.move !== "reserve").map((x) => (
                <button key={x.id} onClick={() => setZone(x.id)} className={`flex items-center justify-between px-3 py-2 rounded-lg ring-1 text-start transition-all ${zone === x.id ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40" : "ring-stone-200 hover:ring-stone-300"}`}><span className="text-[12px] font-medium text-stone-800">{x.short}</span><span className="text-[10.5px] text-stone-400">{x.skus}</span></button>
              ))}
            </div>
          </div>
        )}
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{t("nc.assignTo")}</div>
          <div className="grid grid-cols-3 gap-1.5">{pickers.slice(0, 6).map((p) => <button key={p.id} onClick={() => setOwner(p.id)} className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg ring-1 transition-all ${owner === p.id ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40" : "ring-stone-200 hover:ring-stone-300"}`}><Avatar name={p.name} size={18} /><span className="text-[11px] font-medium text-stone-800 truncate">{p.short}</span></button>)}</div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{t("nc.scheduleFor")}</div><div className="inline-flex bg-stone-100/80 rounded-lg p-0.5 w-full">{[["now", t("nc.now")], ["tomorrow", t("nc.tomorrow")]].map(([k, l]) => <button key={k} onClick={() => setWhen(k)} className={`flex-1 h-8 text-[12px] font-medium rounded-md ${when === k ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-500"}`}>{l}</button>)}</div></div>
          <div className="rounded-lg bg-stone-50 ring-1 ring-stone-200/60 px-3 py-2"><div className="text-[14px] font-semibold text-stone-900 tabular-nums">{estBins} bins · ≈{estTime}m</div><div className="text-[10.5px] text-stone-500">{t("nc.estBins")} / {t("nc.estTime")}</div></div>
        </div>
        <button onClick={() => setBlind(!blind)} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg ring-1 ring-stone-200 hover:bg-stone-50">
          <span className={`w-9 h-5 rounded-full p-0.5 transition-colors flex-shrink-0 ${blind ? "bg-[var(--accent-600)]" : "bg-stone-200"}`}><span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform ${blind ? "translate-x-4" : ""}`} /></span>
          <span className="text-[12.5px] text-stone-700 text-start">{t("nc.blind")}</span>
        </button>
      </div>
    </window.LgModal>
  );
}

const IN_TONE = { scheduled: "neutral", checking: "blue", putaway: "amber", done: "green" };
function Receiving({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const rows = window.LG_INBOUND || [];
  const [open, setOpen] = useState(null);
  if (open) return <ReceivingDetail r={rows.find((x) => x.no === open)} onClose={() => setOpen(null)} onToast={onToast} />;
  return (
    <div>
      <div className="flex justify-end mb-3"><Button variant="brand" size="md" icon={I.Plus}>{t("wh.checkIn")}</Button></div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {rows.map((r) => (
          <div key={r.no} onClick={() => setOpen(r.no)} className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 cursor-pointer hover:ring-stone-300 hover:shadow-[0_8px_24px_-8px_rgba(0,0,0,0.1)] transition-all">
            <div className="flex items-center justify-between"><span className="font-mono text-[12px] font-semibold text-stone-900">{r.no}</span><Badge tone={IN_TONE[r.status]} dot className="whitespace-nowrap">{r.status}</Badge></div>
            <div className="text-[13px] font-medium text-stone-900 mt-2">{r.supplier}</div>
            <div className="flex items-center gap-3 mt-2 text-[11.5px] text-stone-500"><span className="tabular-nums">{r.items} {t("wh.skus")}</span><span className="text-stone-300">·</span><span className="tabular-nums">{r.units} {t("wh.units")}</span></div>
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-stone-100">
              <div className="flex items-center gap-1.5 text-[11.5px] text-stone-600"><I.Clock width={12} height={12} className="text-stone-400" />{r.eta} · {r.dock}</div>
              <div className="flex items-center gap-1.5"><Avatar name={D.byId(r.owner).name} size={20} /></div>
            </div>
            {r.status !== "done" && <Button variant="secondary" size="sm" icon={I.Inventory} className="w-full mt-3" onClick={(e) => { e.stopPropagation(); setOpen(r.no); }}>{t("wh.putaway")}</Button>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Zone owners (responsibility by zone) ─────────────────────────────
function ReceivingDetail({ r, onClose, onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const stages = ["checkin", "verify", "putaway", "done"];
  const lines = useMemo(() => Array.from({ length: Math.min(r.items, 6) }).map((_, i) => {
    const names = [["MCH100013", "Diffuseur huile MCH", "J8C - JM"], ["CSM44021", "Sérum éclat 30ml", "I4A - JM"], ["ACC11008", "Trousse maquillage", "H14A - JM"], ["MUZ22014", "Palette ombres MU", "H13B - JM"], ["TXT55012", "Foulard soie", "G13C - JM"], ["ACC11015", "Miroir LED", "H14C - JM"]];
    const [sku, nm, bin] = names[i % names.length]; const exp = 20 + (i * 17) % 60;
    return { sku, name: nm, bin, expected: exp, received: exp };
  }), [r.no]);
  const start = r.status === "putaway" ? 2 : r.status === "checking" ? 1 : 0;
  const [stage, setStage] = useState(start);
  const [done, setDone] = useState(stage >= 2 ? 0 : 0);
  function scan() { const n = Math.min(lines.length, done + 1); setDone(n); if (n >= lines.length) setStage(3); }

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onClose} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"><I.Back width={15} height={15} className="rtl:rotate-180" />{t("wh.receiving")}</button>

      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center"><I.Inventory width={22} height={22} /></span>
            <div><div className="flex items-center gap-2 flex-wrap"><h1 className="font-mono text-[17px] font-bold text-stone-900">{r.no}</h1><Badge tone="neutral">Material Receipt</Badge></div>
            <div className="text-[12.5px] text-stone-600 mt-1 flex items-center gap-2"><Avatar name={D.byId(r.owner).name} size={20} />{r.supplier} · {r.dock} · {r.eta}</div></div>
          </div>
        </div>
        <div className="flex items-center mt-5">
          {stages.map((s, i) => { const dn = i <= stage; return (
            <React.Fragment key={s}>
              <div className="flex flex-col items-center gap-1.5 flex-shrink-0" style={{ width: 110 }}>
                <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold ${dn ? "bg-emerald-500 text-white" : "bg-stone-100 text-stone-400"}`}>{dn ? <I.Check width={14} height={14} /> : i + 1}</span>
                <span className={`text-[11px] font-medium ${dn ? "text-stone-900" : "text-stone-400"}`}>{t("rc." + s)}</span>
              </div>
              {i < stages.length - 1 && <div className={`flex-1 h-0.5 -mt-6 ${i < stage ? "bg-emerald-300" : "bg-stone-200"}`} />}
            </React.Fragment>
          ); })}
        </div>
        <div className="text-[11.5px] text-stone-500 mt-4 flex items-center gap-1.5 rounded-lg bg-stone-50 px-3 py-2"><I.Info width={13} height={13} className="text-stone-400 flex-shrink-0" />{t("rc.verifyHow")}</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
        <Panel title={t("rc.verify")} sub={`${r.items} ${t("wh.skus")} · ${r.units} ${t("wh.units")}`} right={stage >= 2 && <Badge tone={done >= lines.length ? "green" : "blue"} dot>{done}/{lines.length}</Badge>} bodyClass="p-0">
          {stage >= 2 && stage < 3 && (
            <div className="p-4 border-b border-stone-100">
              <button onClick={scan} className="w-full flex items-center gap-3 px-4 h-14 rounded-2xl ring-2 ring-stone-300 bg-white hover:ring-stone-400 transition-all active:scale-[0.99]">
                <span className="w-10 h-10 rounded-xl bg-stone-900 text-white flex items-center justify-center flex-shrink-0"><I.Search width={18} height={18} /></span>
                <span className="text-[14px] font-medium text-stone-600 flex-1 text-start">{t("rc.scanItem")}</span>
              </button>
            </div>
          )}
          <div className="divide-y divide-stone-100">
            {lines.map((l, i) => { const putaway = stage >= 2 && i < done; return (
              <div key={i} className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-3 px-4 py-2.5">
                <div className="min-w-0"><div className="text-[12.5px] font-medium text-stone-900 truncate">{l.name}</div><div className="font-mono text-[10.5px] text-stone-400">{l.sku}</div></div>
                <span className="text-[11px] text-stone-500 tabular-nums">{t("rc.expected")} {l.expected}</span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stone-900 text-white text-[10.5px] font-bold font-mono"><I.Pin width={9} height={9} />{l.bin}</span>
                {stage >= 2 ? (putaway ? <Badge tone="green" dot>{t("rc.putaway")}</Badge> : <span className="text-[11px] text-stone-300">—</span>) : <Badge tone="blue" dot>{l.received}</Badge>}
              </div>
            ); })}
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel bodyClass="p-4">
            {stage === 0 && <Button variant="brand" size="lg" icon={I.CheckCircle} className="w-full" onClick={() => setStage(1)}>{t("rc.startCheck")}</Button>}
            {stage === 1 && <Button variant="secondary" size="lg" icon={I.Inventory} className="w-full" onClick={() => setStage(2)}>{t("rc.toPutaway")}</Button>}
            {stage === 2 && <Button variant="success" size="lg" icon={I.CheckCircle} className="w-full" disabled={done < lines.length} onClick={() => { setStage(3); onToast?.({ type: "success", text: `${r.no} · Material Receipt posted` }); }}>{t("rc.confirmReceipt")}</Button>}
            {stage === 3 && <div className="text-center text-[12.5px] text-emerald-600 font-medium py-2 flex items-center justify-center gap-1.5"><I.CheckCircle width={16} height={16} />Material Receipt posted</div>}
          </Panel>
        </div>
      </div>
    </div>
  );
}

// ── Zone owners (responsibility by zone) ─────────────────────────────
function ZoneOwners({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const M = window.LG_WAREHOUSE_MAP;
  return (
    <Panel bodyClass="p-0">
      <table className="w-full">
        <thead><tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
          <th className="text-start px-4 py-2.5">Zone</th><th className="text-start px-4 py-2.5">{t("wh.velocity")}</th><th className="text-start px-4 py-2.5">{t("wh.owner")}</th>
          <th className="text-end px-4 py-2.5 hidden sm:table-cell">{t("wh.skus")}</th><th className="text-end px-4 py-2.5">{t("wh.fill")}</th><th className="px-4 py-2.5"></th>
        </tr></thead>
        <tbody className="divide-y divide-stone-100">
          {M.zones.map((z) => { const fill = z.units / z.cap; return (
            <tr key={z.id} className="hover:bg-stone-50">
              <td className="px-4 py-2.5"><div className="text-[12.5px] font-medium text-stone-900">{z.short}</div><div className="font-mono text-[10.5px] text-stone-400">{z.aisles.join(" · ")}</div></td>
              <td className="px-4 py-2.5"><Badge tone={MOVE_TONE[z.move]} dot>{t("wh." + z.move)}</Badge></td>
              <td className="px-4 py-2.5"><div className="flex items-center gap-1.5"><Avatar name={D.byId(z.owner).name} size={22} /><span className="text-[12px] text-stone-700">{D.byId(z.owner).short}</span></div></td>
              <td className="px-4 py-2.5 text-end text-[12.5px] text-stone-700 tabular-nums hidden sm:table-cell">{z.skus}</td>
              <td className="px-4 py-2.5 text-end"><div className="flex items-center gap-2 justify-end"><div className="w-[60px] h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${fill*100}%`, background: MOVE_COLOR[z.move] }} /></div><span className="text-[11.5px] text-stone-500 tabular-nums w-[30px]">{Math.round(fill*100)}%</span></div></td>
              <td className="px-4 py-2.5 text-end"><Button variant="secondary" size="sm" icon={I.Users} onClick={() => onToast?.({ type: "info", text: `Reassign owner · ${z.short}` })}>{t("wh.assignOwner")}</Button></td>
            </tr>
          ); })}
        </tbody>
      </table>
    </Panel>
  );
}
