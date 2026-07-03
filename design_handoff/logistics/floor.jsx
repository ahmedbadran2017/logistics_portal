/* global React, I, Badge, Avatar, Button, Panel, KpiCard, PageHead, ScanInput */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// PACK STATION — scan-verify packing, auto box + AWB
// ─────────────────────────────────────────────────────────────────────
function PackStation({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const queue = window.LG_PACK_QUEUE || [];
  const boxes = window.LG_BOXES || [];
  const [active, setActive] = useState(null);
  const [scanned, setScanned] = useState(0);
  const [packed, setPacked] = useState(412);

  function open(o) { setActive(o); setScanned(0); }
  function scan() { setScanned((s) => Math.min(active.items, s + 1)); }
  function finish() {
    setPacked((p) => p + 1);
    onToast?.({ type: "success", text: `${active.order} packed · AWB printed · ${D.CARRIER}` });
    setActive(null); setScanned(0);
  }
  const box = active ? (boxes.find((b) => b.id === active.box) || boxes[0]) : null;
  const allScanned = active && scanned >= active.items;

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("ps.title")} sub={t("ps.sub")}>
        <Badge tone="green" dot>{t("ps.mispackGuard")}</Badge>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Tag} tone="stone" label={t("ps.packed")} value={packed} />
        <KpiCard icon={I.Box} tone="amber" label={t("ps.queue")} value={queue.length} />
        <KpiCard icon={I.Zap} tone="emerald" label={t("an.oph")} value={73} />
        <KpiCard icon={I.Clock} tone="violet" label={t("an.cutoff")} value={"2h 36m"} />
      </div>

      {/* fast lane banner */}
      <div className="rounded-2xl ring-1 ring-[var(--accent-300)]/50 bg-gradient-to-r from-[var(--accent-50)]/60 to-white p-4 mb-4 flex items-center gap-3">
        <span className="w-10 h-10 rounded-xl bg-[var(--accent-600)] text-white flex items-center justify-center flex-shrink-0"><I.Zap width={20} height={20} /></span>
        <div className="flex-1 min-w-0"><div className="text-[13.5px] font-semibold text-stone-900">{t("ps.fastLane")}</div><div className="text-[12px] text-stone-500">{t("ps.fastLaneSub")}</div></div>
        <Badge tone="brand" dot>{queue.filter((o) => o.items === 1).length} ready</Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-4">
        {/* queue */}
        <Panel title={t("ps.queue")} bodyClass="p-2">
          {queue.map((o) => (
            <button key={o.order} onClick={() => open(o)} className={`w-full text-start rounded-xl px-3 py-2.5 flex items-center gap-2.5 transition-colors ${active?.order === o.order ? "bg-[var(--accent-50)]/60 ring-1 ring-[var(--accent-200)]" : "hover:bg-stone-50"}`}>
              <span className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-[11px] font-bold ${o.items === 1 ? "bg-[var(--accent-100)] text-[var(--accent-700)]" : "bg-stone-100 text-stone-500"}`}>{o.items}</span>
              <div className="min-w-0 flex-1"><div className="font-mono text-[12px] font-semibold text-stone-900">{o.order}</div><div className="text-[11px] text-stone-500 truncate">{o.customer}</div></div>
              {o.items === 1 && <Badge tone="brand">fast</Badge>}
              <window.SlaBadge sla={o.sla} size="sm" />
            </button>
          ))}
        </Panel>

        {/* pack workspace */}
        <Panel bodyClass="p-0">
          {!active ? (
            <div className="flex flex-col items-center justify-center text-center py-20 px-6">
              <div className="w-14 h-14 rounded-2xl bg-stone-100 text-stone-400 flex items-center justify-center mb-3"><I.Tag width={26} height={26} /></div>
              <div className="text-[14px] font-medium text-stone-700">{t("ps.scanOrder")}</div>
              <div className="text-[12px] text-stone-400 mt-1">Pick an order from the queue or scan its barcode</div>
            </div>
          ) : (
            <div className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div><div className="font-mono text-[16px] font-bold text-stone-900">{active.order}</div><div className="text-[12px] text-stone-500">{active.customer} · {active.zone.replace(" - JM", "")}</div></div>
                <window.SlaBadge sla={active.sla} />
              </div>

              {/* suggested box */}
              <div className="rounded-xl bg-stone-50 ring-1 ring-stone-200/60 p-3 mb-4 flex items-center gap-3">
                <span className="w-10 h-10 rounded-lg bg-white ring-1 ring-stone-200 flex items-center justify-center text-[12px] font-bold text-stone-700">{box.id}</span>
                <div className="flex-1"><div className="text-[11px] text-stone-400 uppercase tracking-wide">{t("ps.suggestedBox")}</div><div className="text-[12.5px] font-medium text-stone-800">{box.dim} cm · ≤{box.max}kg</div></div>
                <div className="text-end"><div className="text-[11px] text-stone-400">{t("ps.weight")}</div><div className="text-[13px] font-semibold text-stone-900 tabular-nums">{active.weight} kg</div></div>
              </div>

              {/* scan progress */}
              <div className="flex items-center justify-between mb-1.5"><span className="text-[12px] font-medium text-stone-600">{t("ps.scanItems")}</span><span className="text-[12px] font-semibold text-emerald-600 tabular-nums">{scanned}/{active.items} {t("ps.verified")}</span></div>
              <div className="h-2 rounded-full bg-stone-100 overflow-hidden mb-3"><div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${scanned / active.items * 100}%` }} /></div>

              <div className="space-y-2 mb-4">
                {Array.from({ length: active.items }).map((_, i) => {
                  const done = i < scanned;
                  return (
                    <div key={i} className={`flex items-center gap-3 rounded-xl ring-1 p-2.5 ${done ? "ring-emerald-200 bg-emerald-50/40" : "ring-stone-200"}`}>
                      <span className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${done ? "bg-emerald-500 text-white" : "bg-stone-100 text-stone-400"}`}>{done ? <I.Check width={15} height={15} /> : <I.Box width={15} height={15} />}</span>
                      <div className="min-w-0 flex-1"><div className="text-[12.5px] font-medium text-stone-900">Item {i + 1}</div><div className="font-mono text-[10.5px] text-stone-400">{["MCH100013", "CSM44021", "ACC11008"][i % 3]}</div></div>
                      {done && <span className="text-[11px] text-emerald-600 font-medium">✓ verified</span>}
                    </div>
                  );
                })}
              </div>

              {!allScanned ? (
                <button onClick={scan} className="w-full flex items-center gap-3 px-4 h-14 rounded-2xl ring-2 ring-stone-300 bg-white hover:ring-stone-400 transition-all active:scale-[0.99]">
                  <span className="w-10 h-10 rounded-xl bg-stone-900 text-white flex items-center justify-center flex-shrink-0"><I.Search width={18} height={18} /></span>
                  <span className="text-[14px] font-medium text-stone-600 flex-1 text-start">{t("ps.scanItems")}</span>
                </button>
              ) : (
                <Button variant="success" size="lg" icon={I.Tag} className="w-full" onClick={finish}>{t("ps.printSeal")}</Button>
              )}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
window.PackStation = PackStation;

// ─────────────────────────────────────────────────────────────────────
// WAVE PICKING — scheduled batch releases
// ─────────────────────────────────────────────────────────────────────
const WV_TONE = { active: "blue", queued: "amber", done: "green" };
function WavePicking({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [rows, setRows] = useState(() => (window.LG_WAVES || []).map((w) => ({ ...w })));
  function release(no) { setRows((rs) => rs.map((w) => w.no === no ? { ...w, status: "active", progress: 2 } : w)); onToast?.({ type: "success", text: `${no} released · ${rows.find(w=>w.no===no).orders} pick lists assigned` }); }

  return (
    <div className="max-w-[1100px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("wv.title")} sub={t("wv.sub")}>
        <Button variant="brand" size="md" icon={I.Zap} onClick={() => onToast?.({ type: "success", text: "Next wave auto-planned by zone + cutoff" })}>{t("wv.autoPlan")}</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Layers} tone="blue" label={t("wv.active")} value={rows.filter(w=>w.status==="active").length} />
        <KpiCard icon={I.Clock} tone="amber" label={t("wv.queued")} value={rows.filter(w=>w.status==="queued").length} />
        <KpiCard icon={I.Box} tone="stone" label={t("wv.orders")} value={rows.reduce((a,w)=>a+w.orders,0)} />
        <KpiCard icon={I.AlertCircle} tone="violet" label={t("wv.cutoffIn")} value={"2h 36m"} />
      </div>

      <div className="space-y-3">
        {rows.map((w) => (
          <div key={w.no} className={`bg-white rounded-xl ring-1 p-4 ${w.status === "active" ? "ring-blue-200" : "ring-stone-200/70"}`}>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3">
                <span className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${w.status === "done" ? "bg-emerald-50 text-emerald-600" : w.status === "active" ? "bg-blue-50 text-blue-600" : "bg-amber-50 text-amber-600"}`}><I.Layers width={20} height={20} /></span>
                <div>
                  <div className="flex items-center gap-2"><span className="font-mono text-[14px] font-bold text-stone-900">{w.no}</span><Badge tone={WV_TONE[w.status]} dot>{t("wv." + w.status)}</Badge></div>
                  <div className="text-[11.5px] text-stone-500 mt-0.5">{w.releaseAt} · {w.orders} {t("wv.orders")} · {w.pickers} {t("wv.pickers")} · {w.zones.join(" + ")}</div>
                </div>
              </div>
              {w.status === "queued"
                ? <Button variant="brand" size="md" icon={I.Zap} onClick={() => release(w.no)}>{t("wv.release")}</Button>
                : w.status === "active" ? <Badge tone="blue" dot>{w.progress}%</Badge> : <span className="inline-flex items-center gap-1 text-[12px] text-emerald-600 font-medium"><I.CheckCircle width={14} height={14} />{t("wv.done")}</span>}
            </div>
            {w.status !== "queued" && (
              <div className="mt-3"><div className="h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${w.status === "done" ? "bg-emerald-500" : "bg-blue-500"}`} style={{ width: `${w.progress}%` }} /></div></div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
window.WavePicking = WavePicking;

// ─────────────────────────────────────────────────────────────────────
// FLOOR BOARD (Andon) — live throughput
// ─────────────────────────────────────────────────────────────────────
function FloorBoard() {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const A = window.LG_ANDON;
  const pace = A.ordersPerHour / A.target;

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("an.title")} sub={t("an.sub")} />

      {/* hero throughput */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-4 mb-4">
        <div className={`rounded-2xl ring-1 p-5 ${pace >= 0.95 ? "ring-emerald-200 bg-gradient-to-br from-emerald-50/60 to-white" : "ring-amber-200 bg-gradient-to-br from-amber-50/60 to-white"}`}>
          <div className="flex items-center justify-between">
            <span className="text-[12px] font-medium text-stone-500">{t("an.oph")}</span>
            <Badge tone={pace >= 0.95 ? "green" : "amber"} dot>{pace >= 0.95 ? t("an.onPace") : t("an.behind")}</Badge>
          </div>
          <div className="flex items-end gap-2 mt-2"><span className="text-[48px] font-bold text-stone-900 tabular-nums leading-none"><window.CountUp value={A.ordersPerHour} /></span><span className="text-[14px] text-stone-400 mb-1.5">/ {A.target} {t("an.target")}</span></div>
          {/* hourly sparkbars */}
          <div className="flex items-end gap-1.5 mt-4 h-16">
            {A.hourly.map((v, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full rounded-t bg-[var(--accent-400)]" style={{ height: `${v / Math.max(...A.hourly) * 100}%` }} />
                <span className="text-[9px] text-stone-400 tabular-nums">{v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <KpiCard icon={I.Tag} tone="stone" label={t("an.packed")} value={A.packedToday} />
          <KpiCard icon={I.Send} tone="cyan" label={t("an.shipped")} value={A.shippedToday} />
          <KpiCard icon={I.Clock} tone="violet" label={t("an.cutoff")} value={"2h 36m"} />
          <KpiCard icon={I.AlertCircle} tone="amber" label={t("an.lagging")} value={A.laggingZone.replace(" zone - JM", "").replace(" - JM", "")} />
        </div>
      </div>

      {/* station pipeline */}
      <Panel title={t("an.stations")} bodyClass="p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {A.stations.map((s, i) => {
            const ok = s.status === "ok";
            return (
              <div key={s.name} className={`rounded-xl ring-1 p-4 ${ok ? "ring-stone-200/70" : "ring-amber-300 bg-amber-50/40"}`}>
                <div className="flex items-center justify-between"><span className="text-[12.5px] font-semibold text-stone-900">{s.name}</span><span className={`w-2 h-2 rounded-full ${ok ? "bg-emerald-500" : "bg-amber-500 animate-pulse"}`} /></div>
                <div className="text-[24px] font-bold text-stone-900 tabular-nums leading-none mt-2"><window.CountUp value={s.rate} /><span className="text-[11px] text-stone-400 font-medium"> /hr</span></div>
                <div className="h-1.5 rounded-full bg-stone-100 overflow-hidden mt-2"><div className={`h-full rounded-full ${ok ? "bg-emerald-500" : "bg-amber-500"}`} style={{ width: `${Math.min(100, s.rate / s.target * 100)}%` }} /></div>
                <div className="text-[10.5px] text-stone-400 mt-1 tabular-nums">{t("an.target")} {s.target}/hr</div>
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}
window.FloorBoard = FloorBoard;
