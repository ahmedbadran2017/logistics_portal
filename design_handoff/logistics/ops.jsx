/* global React, I, Badge, Avatar, Button, Panel, KpiCard, PageHead, SlaRing */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// COD RECONCILIATION — cash collected by carrier → remitted
// ─────────────────────────────────────────────────────────────────────
const CR_TONE = { reconciled: "green", discrepancy: "rose", pending: "amber" };
function CODReconcile({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const C = window.LG_COD;
  const [rows, setRows] = useState(() => C.remittances.map((r) => ({ ...r })));
  function reconcile(no) { setRows((rs) => rs.map((r) => r.no === no ? { ...r, status: "reconciled", received: r.expected, diff: 0 } : r)); onToast?.({ type: "success", text: `${no} reconciled · posted to ERPNext` }); }
  const remitPct = C.collected ? C.remitted / C.collected : 0;

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("cod.title")} sub={t("cod.sub")}>
        <Button variant="secondary" size="md" icon={I.Download}>Export</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Cash} tone="stone" label={t("cod.collected")} value={window.fmtMAD(C.collected)} unit="MAD" />
        <KpiCard icon={I.CheckCircle} tone="emerald" label={t("cod.remitted")} value={window.fmtMAD(C.remitted)} unit="MAD" />
        <KpiCard icon={I.Clock} tone="amber" label={t("cod.pending")} value={window.fmtMAD(C.pending)} unit="MAD" />
        <KpiCard icon={I.AlertCircle} tone="rose" label={t("cod.discrepancy")} value={window.fmtMAD(C.discrepancy)} unit="MAD" />
      </div>

      <Panel className="mb-4" bodyClass="p-4">
        <div className="flex items-center justify-between text-[12px] mb-1.5"><span className="text-stone-600 font-medium">{t("cod.remitted")} / {t("cod.collected")}</span><span className="font-semibold text-emerald-600 tabular-nums">{Math.round(remitPct * 100)}%</span></div>
        <div className="h-2.5 rounded-full bg-stone-100 overflow-hidden"><div className="h-full bg-emerald-500 rounded-full" style={{ width: `${remitPct * 100}%` }} /></div>
        <div className="flex items-center gap-4 mt-2 text-[11px] text-stone-400"><span>COD success rate {C.codRate}%</span></div>
      </Panel>

      <Panel title={t("cod.remittances")} sub={D.CARRIER} bodyClass="p-0">
        <div className="overflow-x-auto"><table className="w-full min-w-[720px]">
          <thead><tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
            <th className="text-start px-4 py-2.5">Remittance</th><th className="text-start px-4 py-2.5">Date</th><th className="text-end px-4 py-2.5">{t("c.parcels")}</th>
            <th className="text-end px-4 py-2.5">{t("cod.expected")}</th><th className="text-end px-4 py-2.5">{t("cod.received")}</th><th className="text-end px-4 py-2.5">{t("cod.diff")}</th><th className="text-start px-4 py-2.5">Status</th><th className="px-4 py-2.5"></th>
          </tr></thead>
          <tbody className="divide-y divide-stone-100">
            {rows.map((r) => (
              <tr key={r.no} className={r.status === "discrepancy" ? "bg-rose-50/30" : "hover:bg-stone-50"}>
                <td className="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900">{r.no}</td>
                <td className="px-4 py-2.5 text-[12px] text-stone-600 whitespace-nowrap">{r.date}</td>
                <td className="px-4 py-2.5 text-end text-[12px] text-stone-600 tabular-nums">{r.parcels}</td>
                <td className="px-4 py-2.5 text-end text-[12.5px] text-stone-700 tabular-nums">{window.fmtMAD(r.expected)}</td>
                <td className="px-4 py-2.5 text-end text-[12.5px] font-medium text-stone-900 tabular-nums">{r.received ? window.fmtMAD(r.received) : "—"}</td>
                <td className="px-4 py-2.5 text-end text-[12.5px] tabular-nums"><span className={r.diff < 0 ? "text-rose-600 font-semibold" : "text-stone-400"}>{r.diff ? window.fmtMAD(r.diff) : "0"}</span></td>
                <td className="px-4 py-2.5"><Badge tone={CR_TONE[r.status]} dot className="whitespace-nowrap">{r.status}</Badge></td>
                <td className="px-4 py-2.5 text-end">{r.status === "pending" ? <Button variant="brand" size="sm" icon={I.Check} onClick={() => reconcile(r.no)}>{t("cod.reconcile")}</Button> : r.status === "discrepancy" ? <Button variant="danger" size="sm" icon={I.AlertCircle}>{t("cod.flagDisc")}</Button> : <span className="inline-flex items-center gap-1 text-[11.5px] text-emerald-600"><I.CheckCircle width={13} height={13} />{t("cod.reconciled")}</span>}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </Panel>
    </div>
  );
}
window.CODReconcile = CODReconcile;

// ─────────────────────────────────────────────────────────────────────
// EXCEPTION COMMAND CENTER — one queue for every blocker
// ─────────────────────────────────────────────────────────────────────
function ExceptionCenter({ onToast }) {
  const { t, openOrder } = window.useLg();
  const D = window.LG_DATA;
  const K = window.LG_EXC_KIND;
  const [rows, setRows] = useState(() => (window.LG_EXCEPTIONS || []).map((e) => ({ ...e })));
  const [filter, setFilter] = useState("all");
  function resolve(id) { setRows((rs) => rs.filter((e) => e.id !== id)); onToast?.({ type: "success", text: `${id} resolved` }); }
  const kinds = ["all", "oos", "carrier", "shortpick", "return", "cod"];
  const shown = rows.filter((e) => filter === "all" || e.kind === filter);
  const critical = rows.filter((e) => e.sev === "red").length;
  const overdue = rows.filter((e) => e.age > e.sla).length;

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("ex.title")} sub={t("ex.sub")} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.AlertCircle} tone="stone" label={t("ex.open")} value={rows.length} />
        <KpiCard icon={I.AlertCircle} tone="rose" label={t("ex.critical")} value={critical} />
        <KpiCard icon={I.Clock} tone="amber" label={t("ex.overdue")} value={overdue} />
        <KpiCard icon={I.Zap} tone="violet" label="Avg age" value={Math.round(rows.reduce((a, e) => a + e.age, 0) / (rows.length || 1))} unit="m" />
      </div>

      <div className="flex items-center gap-1.5 mb-3 overflow-x-auto pb-1">
        {kinds.map((k) => (
          <button key={k} onClick={() => setFilter(k)} className={`px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 whitespace-nowrap ${filter === k ? "bg-stone-900 text-white ring-stone-900" : "bg-white text-stone-600 ring-stone-200 hover:ring-stone-300"}`}>{k === "all" ? t("ex.allKinds") : k === "oos" ? "Out of stock" : k === "carrier" ? "Carrier" : k === "shortpick" ? "Short-pick" : k === "return" ? "Returns" : "COD"}</button>
        ))}
      </div>

      <div className="space-y-2">
        {shown.map((e) => {
          const k = K[e.kind] || K.oos; const Icon = I[k.icon] || I.AlertCircle; const isOverdue = e.age > e.sla;
          const sevColor = e.sev === "red" ? "bg-rose-500" : e.sev === "orange" ? "bg-orange-500" : "bg-amber-500";
          return (
            <div key={e.id} className="relative bg-white rounded-xl ring-1 ring-stone-200/70 p-3.5 ps-4 overflow-hidden flex items-center gap-3 flex-wrap">
              <span className={`absolute inset-y-0 start-0 w-1 ${sevColor}`} />
              <span className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-${k.tone}-50 text-${k.tone}-600`} style={{ background: `var(--x)` }}><Icon width={15} height={15} className={`text-${k.tone}-600`} /></span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap"><span className="font-mono text-[12px] font-semibold text-stone-900">{e.id}</span><Badge tone={K[e.kind].tone === "orange" ? "amber" : K[e.kind].tone} dot>{e.label}</Badge>{isOverdue && <Badge tone="red" className="whitespace-nowrap">{t("ex.overdue")}</Badge>}</div>
                <div className="text-[12px] text-stone-600 mt-0.5 truncate">{e.detail}</div>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-stone-400"><Avatar name={D.byId(e.owner).name} size={20} /><span className={`tabular-nums ${isOverdue ? "text-rose-600 font-medium" : ""}`}>{e.age}m {t("ex.age")}</span></div>
              <div className="flex items-center gap-1.5">
                <Button variant="secondary" size="sm" icon={I.ArrowRight} onClick={() => e.id.startsWith("#") && openOrder(e.id)}>Open</Button>
                <Button variant="brand" size="sm" icon={I.Check} onClick={() => resolve(e.id)}>{t("ex.resolve")}</Button>
              </div>
            </div>
          );
        })}
        {shown.length === 0 && <div className="text-center text-[12.5px] text-emerald-600 py-12 flex items-center justify-center gap-1.5"><I.CheckCircle width={16} height={16} />All clear — no open exceptions</div>}
      </div>
    </div>
  );
}
window.ExceptionCenter = ExceptionCenter;

// ─────────────────────────────────────────────────────────────────────
// CARRIER SCORECARD — performance + smart routing
// ─────────────────────────────────────────────────────────────────────
function CarrierScorecard({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const scores = window.LG_CARRIER_SCORES || [];
  const routing = window.LG_ROUTING || [];
  const [sel, setSel] = useState(scores[0].carrier);
  const c = scores.find((x) => x.carrier === sel);

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("cs.title")} sub={t("cs.sub")} />

      {/* routing suggestions */}
      {routing.length > 0 && (
        <Panel title={t("cs.routing")} className="mb-4" right={<Badge tone="brand" dot>{routing.length}</Badge>} bodyClass="p-3 space-y-2">
          {routing.map((r, i) => (
            <div key={i} className="flex items-center gap-2.5 rounded-xl bg-[var(--accent-50)]/40 ring-1 ring-[var(--accent-200)]/50 px-3 py-2">
              <I.Globe width={15} height={15} className="text-[var(--accent-600)] flex-shrink-0" />
              <div className="min-w-0 flex-1"><div className="text-[12.5px] font-medium text-stone-900">{r.zone}: {r.from} → {r.to}</div><div className="text-[11px] text-stone-500 truncate">{r.reason}</div></div>
              <Badge tone="green">{r.gain}</Badge>
              <Button variant="brand" size="sm" icon={I.ArrowRight} onClick={() => onToast?.({ type: "success", text: `${r.zone} re-routed to ${r.to}` })}>{t("cs.reroute")}</Button>
            </div>
          ))}
        </Panel>
      )}

      {/* carrier comparison */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        {scores.map((s) => (
          <button key={s.carrier} onClick={() => setSel(s.carrier)} className={`text-start bg-white rounded-xl ring-1 p-4 transition-all ${sel === s.carrier ? "ring-2 ring-stone-900" : "ring-stone-200/70 hover:ring-stone-300"}`}>
            <div className="flex items-center justify-between"><div className="flex items-center gap-2"><span className="w-8 h-8 rounded-lg bg-cyan-50 text-cyan-700 flex items-center justify-center text-[11px] font-bold">{s.code}</span><span className="text-[13px] font-semibold text-stone-900">{s.carrier}</span></div>{s.active ? <Badge tone="green" dot>Active</Badge> : <Badge tone="neutral">Standby</Badge>}</div>
            <div className="grid grid-cols-2 gap-2 mt-3">
              <div><div className="text-[16px] font-semibold text-emerald-600 tabular-nums leading-none">{s.deliveryRate}%</div><div className="text-[10px] text-stone-500 mt-1">{t("cs.deliveryRate")}</div></div>
              <div><div className="text-[16px] font-semibold text-stone-900 tabular-nums leading-none">{s.costPerParcel}<span className="text-[10px] text-stone-400"> MAD</span></div><div className="text-[10px] text-stone-500 mt-1">{t("cs.cost")}</div></div>
              <div><div className="text-[16px] font-semibold text-rose-500 tabular-nums leading-none">{s.exceptionRate}%</div><div className="text-[10px] text-stone-500 mt-1">{t("cs.exceptionRate")}</div></div>
              <div><div className="text-[16px] font-semibold text-stone-900 tabular-nums leading-none">{s.avgTransit}d</div><div className="text-[10px] text-stone-500 mt-1">{t("cs.transit")}</div></div>
            </div>
          </button>
        ))}
      </div>

      <Panel title={`${c.carrier} · ${t("cs.byZone")}`} bodyClass="p-0">
        <div className="divide-y divide-stone-100">
          {c.zones.map((z) => (
            <div key={z.zone} className="flex items-center gap-3 px-4 py-2.5">
              <span className="text-[12.5px] font-medium text-stone-900 w-[120px]">{z.zone}</span>
              <div className="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${z.rate >= 92 ? "bg-emerald-500" : z.rate >= 87 ? "bg-amber-500" : "bg-rose-500"}`} style={{ width: `${z.rate}%` }} /></div>
              <span className="text-[12px] font-semibold text-stone-800 tabular-nums w-[40px] text-end">{z.rate}%</span>
              <span className="text-[11px] text-stone-400 tabular-nums w-[44px] text-end">{z.transit}d</span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
window.CarrierScorecard = CarrierScorecard;
