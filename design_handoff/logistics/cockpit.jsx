/* global React, I, Badge, Avatar, Sparkline, LineChart, Button, IconButton, KpiCard, Panel, StageBadge, SlaBadge, PerfWidget, AlertRow, SlaRing, SlaBar */
const { useState, useMemo, useEffect } = React;

// ─────────────────────────────────────────────────────────────────────
// MANAGER COCKPIT — desktop-dense. Pipeline · SLA board · leaderboard · audit.
// ─────────────────────────────────────────────────────────────────────
function Cockpit({ onAlertAction }) {
  const { t, dir, openOrder, go } = window.useLg();
  const D = window.LG_DATA;
  const [drill, setDrill] = useState(null); // null | "breach"
  const breaches = D.ORDERS.filter((o) => o.sla === "breached");
  const atRisk = D.ORDERS.filter((o) => o.sla === "atrisk");
  const exceptions = D.ORDERS.filter((o) => o.stage === "exception");
  const inTransit = D.PIPELINE.find((p) => p.key === "transit").count;
  const needsAttention = breaches.length > 0;

  return (
    <div className="max-w-[1320px] mx-auto px-6 py-6 animate-fade-in">
      {/* Title + hero status */}
      <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
        <div>
          <h1 className="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">{t("ck.title")}</h1>
          <p className="text-[13px] text-stone-500 mt-0.5">{t("ck.sub")} · {D.WAREHOUSE}, {D.CITY}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="md" icon={I.Calendar}>{t("c.today")}</Button>
          <Button variant="secondary" size="md" icon={I.Download}>Export</Button>
        </div>
      </div>

      {/* Hero banner */}
      <div className={`rounded-2xl p-5 mb-5 ring-1 flex items-center gap-4 ${needsAttention ? "bg-gradient-to-r from-rose-50 to-white ring-rose-200/70" : "bg-gradient-to-r from-emerald-50 to-white ring-emerald-200/70"}`}>
        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 ${needsAttention ? "bg-rose-500 text-white" : "bg-emerald-500 text-white"}`}>
          {needsAttention ? <I.AlertCircle width={24} height={24} /> : <I.CheckCircle width={24} height={24} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[15px] font-semibold text-stone-900">{needsAttention ? t("ck.needsAttention") : t("ck.allgreen")}</div>
          <div className="text-[12.5px] text-stone-600 mt-0.5">
            {needsAttention
              ? <>{breaches.length} {t("sla.breached").toLowerCase()} · {atRisk.length} {t("ck.atrisk").toLowerCase()}</>
              : t("ck.allgreenSub")}
          </div>
        </div>
        {needsAttention && (
          <Button variant="danger" size="md" iconRight={I.ArrowRight} onClick={() => setDrill("breach")}>{t("ck.drillBreach")}</Button>
        )}
      </div>

      {/* Today's flow + cutoff countdown */}
      <TodayFlow go={go} />

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <KpiCard icon={I.Zap} tone="emerald" label={t("ck.sameday")} value="87" unit="%" trend={+4} spark={[78,80,79,83,85,84,87]} />
        <KpiCard icon={I.AlertCircle} tone="rose" label={t("ck.breaches")} value={breaches.length} trend={-2} trendGood="down" spark={[3,2,4,3,2,1,1]} onClick={() => setDrill("breach")} />
        <KpiCard icon={I.Clock} tone="amber" label={t("ck.atrisk")} value={atRisk.length} trend={+1} trendGood="down" spark={[1,2,2,3,2,2,2]} onClick={() => { window.__ordersInit = { sla: "atrisk" }; go("orders"); }} />
        <KpiCard icon={I.Globe} tone="cyan" label={t("t.intransit")} value={inTransit} trend={+6} spark={[420,440,460,480,500,510,514]} />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Pipeline — spans 2 */}
        <div className="xl:col-span-2 space-y-4">
          <Panel title={t("ck.pipeline")} sub={`${D.PIPELINE.reduce((a,p)=>a+p.count,0)} ${t("c.orders")} · 9 stages`} bodyClass="p-4">
            <PipelineFunnel onStage={(key) => { window.__ordersInit = { stage: key }; go("orders"); }} />
          </Panel>

          <Panel title={t("ck.slaboard")} right={<Badge tone="amber" dot>{atRisk.length} {t("ck.atrisk").toLowerCase()}</Badge>} bodyClass="p-0">
            <div className="divide-y divide-stone-100">
              {[...breaches, ...atRisk].map((o) => (
                <BreachRow key={o.no} o={o} onOpen={() => openOrder(o.no)} />
              ))}
            </div>
          </Panel>

          {/* Channel mix + Carrier exceptions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Panel title={t("ck.channelMix")} bodyClass="p-4 space-y-2.5">
              {D.CHANNEL_MIX.map((ch) => {
                const c = D.CHANNELS[ch.key];
                const tones = { emerald: "bg-emerald-500", violet: "bg-violet-500", amber: "bg-amber-500", slate: "bg-stone-400", green: "bg-green-500" };
                return (
                  <div key={ch.key}>
                    <div className="flex items-center justify-between text-[12px] mb-1">
                      <span className="text-stone-700">{c.label}</span>
                      <span className="text-stone-400 tabular-nums">{ch.count} · {ch.pct}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${tones[c.tone]}`} style={{ width: `${ch.pct}%` }} /></div>
                  </div>
                );
              })}
            </Panel>
            <Panel title={t("ck.exceptions")} right={<Badge tone="red" dot>{exceptions.length}</Badge>} bodyClass="p-0">
              <div className="divide-y divide-stone-100">
                {exceptions.map((o) => (
                  <button key={o.no} onClick={() => openOrder(o.no)} className="w-full flex items-center gap-2.5 px-4 py-2.5 hover:bg-stone-50 text-start">
                    <span className="font-mono text-[11.5px] text-stone-500 w-[64px] flex-shrink-0">{o.no}</span>
                    <span className="text-[12px] text-stone-800 flex-1 truncate">{o.customer}</span>
                    <window.TrackBadge state={o.track} />
                  </button>
                ))}
              </div>
            </Panel>
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          <Panel title={t("ck.leaderboard")} right={<button className="text-[11.5px] font-semibold text-[var(--accent-700)]">{t("c.viewAll")}</button>} bodyClass="p-2">
            {D.LEADERBOARD.map((p, i) => (
              <LeaderRow key={p.id} p={p} top={i === 0} />
            ))}
          </Panel>

          <Panel title={t("ck.audit")} right={<Badge tone="red" dot>3 new</Badge>} bodyClass="p-3 space-y-2.5">
            {D.AUDIT.map((a, i) => (
              <AlertRow key={i} item={a} onAction={() => onAlertAction?.(a)} />
            ))}
          </Panel>
        </div>
      </div>

      {/* Breach drill-in */}
      {drill === "breach" && <BreachDrawer breaches={breaches} atRisk={atRisk} onClose={() => setDrill(null)} dir={dir} />}
    </div>
  );
}
window.Cockpit = Cockpit;

// Today's flow strip — orders in vs shipped vs to-ship, with live cutoff countdown
function TodayFlow({ go }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const F = D.TODAY_FLOW;
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const id = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(id); }, []);
  const [ch, cm] = F.cutoff.split(":").map(Number);
  const cutoff = new Date(now); cutoff.setHours(ch, cm, 0, 0);
  const diff = Math.floor((cutoff - now) / 1000);
  const past = diff < 0;
  const hh = Math.floor(Math.abs(diff) / 3600), mm = Math.floor((Math.abs(diff) % 3600) / 60), ss = Math.abs(diff) % 60;
  const shippedPct = F.intake ? (F.shipped + F.labeled) / F.intake : 0;
  const cells = [
    { label: t("ck.intake"), value: F.intake, tone: "text-stone-900" },
    { label: t("ck.shippedToday"), value: F.shipped, tone: "text-emerald-600" },
    { label: t("c.printed"), value: F.labeled, tone: "text-violet-600" },
    { label: t("ck.toShip"), value: F.pending, tone: "text-amber-600", onClick: () => { window.__ordersInit = { stage: "pending" }; go("orders"); } },
  ];
  return (
    <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 mb-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-1.5"><span className="text-[13px] font-semibold text-stone-900">{t("ck.today")}</span><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /></div>
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl ring-1 ${past ? "bg-rose-50 ring-rose-200" : diff < 3600 ? "bg-amber-50 ring-amber-200" : "bg-stone-50 ring-stone-200"}`}>
          <I.Clock width={14} height={14} className={past ? "text-rose-500" : diff < 3600 ? "text-amber-500" : "text-stone-400"} />
          <span className="text-[11.5px] text-stone-500">{past ? t("ck.afterCutoff") : t("ck.cutoffIn")}</span>
          <span className={`text-[14px] font-bold tabular-nums ${past ? "text-rose-600" : diff < 3600 ? "text-amber-600" : "text-stone-900"}`}>{past ? "+" : ""}{String(hh).padStart(2,"0")}:{String(mm).padStart(2,"0")}:{String(ss).padStart(2,"0")}</span>
          <span className="text-[11px] text-stone-400">· {F.cutoff}</span>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-3 mt-3.5">
        {cells.map((c) => (
          <button key={c.label} onClick={c.onClick} disabled={!c.onClick} className={`text-start rounded-xl p-3 ring-1 ring-stone-200/60 ${c.onClick ? "hover:ring-stone-300 hover:bg-stone-50 transition-all cursor-pointer" : ""}`}>
            <div className={`text-[24px] font-semibold tabular-nums leading-none ${c.tone}`}><window.CountUp value={c.value} /></div>
            <div className="text-[11px] text-stone-500 mt-1.5">{c.label}</div>
          </button>
        ))}
      </div>
      <div className="mt-3">
        <div className="flex items-center justify-between text-[11px] mb-1">
          <span className="text-stone-500">{F.shipped + F.labeled} / {F.intake} {window.LG_STRINGS[window.useLg().lang]?.["ck.burndown"]?.replace("{c}", F.cutoff) || `before ${F.cutoff} cutoff`}</span>
          <span className="font-semibold text-emerald-600 tabular-nums">{Math.round(shippedPct * 100)}%</span>
        </div>
        <div className="h-2 rounded-full bg-stone-100 overflow-hidden"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${shippedPct * 100}%`, transition: "width .5s cubic-bezier(.16,1,.3,1)" }} /></div>
      </div>
    </div>
  );
}

function PipelineFunnel({ onStage }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const max = Math.max(...D.PIPELINE.map((p) => p.count));
  return (
    <div className="space-y-1.5">
      {D.PIPELINE.map((p) => {
        const s = D.STAGE[p.key];
        const w = Math.max(6, (p.count / max) * 100);
        return (
          <button key={p.key} onClick={() => onStage(p.key)}
            className="w-full flex items-center gap-3 group">
            <div className="w-[110px] flex items-center gap-2 flex-shrink-0">
              <span className={`w-2 h-2 rounded-full ${s.dot}`} />
              <span className="text-[12px] font-medium text-stone-700 truncate">{t("s." + p.key)}</span>
            </div>
            <div className="flex-1 h-7 rounded-lg bg-stone-50 overflow-hidden relative">
              <div className={`h-full ${s.bg} ${s.ring} ring-1 ring-inset rounded-lg flex items-center px-2.5 transition-all group-hover:brightness-95`} style={{ width: `${w}%` }}>
                <span className={`text-[11.5px] font-semibold tabular-nums ${s.txt}`}>{p.count}</span>
              </div>
            </div>
            <div className="w-[92px] text-end text-[11.5px] text-stone-500 tabular-nums flex-shrink-0">{window.fmtMAD(p.value)} <span className="text-[10px] text-stone-400">MAD</span></div>
          </button>
        );
      })}
    </div>
  );
}

function BreachRow({ o, onOpen }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  return (
    <button onClick={onOpen} className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-stone-50 transition-colors text-start">
      <span className="font-mono text-[11.5px] text-stone-500 tabular-nums w-[88px] flex-shrink-0 truncate">{o.no}</span>
      <span className="text-[12.5px] font-medium text-stone-900 flex-1 truncate">{o.customer}</span>
      <span className="text-[11.5px] text-stone-400 hidden md:block w-[120px] truncate">{o.zone}</span>
      {o.picker && <Avatar name={D.byId(o.picker)?.name} size={22} className="hidden sm:flex" />}
      <StageBadge stage={o.stage} size="sm" />
      <SlaBadge sla={o.sla} size="sm" />
      <span className="text-[11px] text-stone-400 tabular-nums w-[52px] text-end">{o.mins}{t("c.min")}</span>
    </button>
  );
}

function LeaderRow({ p, top }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const person = D.byId(p.id);
  return (
    <div className={`flex items-center gap-2.5 px-2 py-2 rounded-lg ${top ? "bg-[var(--accent-50)]/60" : "hover:bg-stone-50"}`}>
      <span className={`w-5 text-center text-[12px] font-bold tabular-nums ${top ? "text-[var(--accent-700)]" : "text-stone-400"}`}>{p.rank}</span>
      <Avatar name={person?.name} size={30} />
      <div className="min-w-0 flex-1 leading-tight">
        <div className="text-[12.5px] font-medium text-stone-900 truncate flex items-center gap-1">{person?.short}{top && <span className="text-[10px]">⭐</span>}</div>
        <div className="text-[10.5px] text-stone-500 tabular-nums">{p.picks} {t("c.orders")} · {p.avg}</div>
      </div>
      <Sparkline data={p.trend} width={48} height={18} />
      <div className="text-end w-[40px]">
        <div className="text-[12.5px] font-semibold text-stone-900 tabular-nums">{p.sla}%</div>
        <div className="text-[9.5px] text-stone-400 uppercase tracking-wide">{t("c.sla")}</div>
      </div>
    </div>
  );
}

// ── Breach drill-in slide-over ───────────────────────────────────────
function BreachDrawer({ breaches, atRisk, onClose, dir }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const o = breaches[0];
  const side = dir === "rtl" ? "left-0" : "right-0";
  const anim = dir === "rtl" ? "animate-[drawerInL_.26s_cubic-bezier(.16,1,.3,1)]" : "animate-drawer-in";
  return (
    <div className="fixed inset-0 z-[120]">
      <div className="absolute inset-0 bg-stone-900/20 backdrop-blur-[1px] animate-fade-in" onClick={onClose} />
      <div className={`absolute top-0 ${side} h-full w-full max-w-[460px] bg-stone-50 shadow-[0_0_60px_-10px_rgba(0,0,0,0.3)] flex flex-col ${anim}`} dir={dir}>
        <header className="h-[56px] bg-white border-b border-stone-200/70 flex items-center px-4 gap-3 flex-shrink-0">
          <span className="w-8 h-8 rounded-lg bg-rose-50 text-rose-500 flex items-center justify-center"><I.AlertCircle width={17} height={17} /></span>
          <div className="flex-1">
            <div className="text-[14px] font-semibold text-stone-900">{t("ck.drillBreach")}</div>
            <div className="text-[11.5px] text-stone-500">{breaches.length} {t("sla.breached").toLowerCase()} · {atRisk.length} {t("ck.atrisk").toLowerCase()}</div>
          </div>
          <IconButton icon={I.X} onClick={onClose} />
        </header>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Focus order */}
          <div className="bg-white rounded-xl ring-1 ring-rose-200/70 overflow-hidden">
            <div className="px-4 py-3 bg-gradient-to-r from-rose-50 to-white flex items-center justify-between">
              <div>
                <div className="font-mono text-[13px] font-semibold text-stone-900">{o.no}</div>
                <div className="text-[12px] text-stone-600">{o.customer}</div>
              </div>
              <div className="text-end">
                <div className="text-[18px] font-semibold text-stone-900 tabular-nums">{window.fmtMAD(o.total)} <span className="text-[11px] text-stone-400">MAD</span></div>
                <div className="text-[11px] text-stone-500">{o.items} {t("c.items")}</div>
              </div>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <StageBadge stage={o.stage} /><SlaBadge sla={o.sla} />
                <Badge tone="neutral">{o.zone}</Badge>
              </div>
              {/* timeline */}
              <div className="space-y-2 pt-1">
                {[["s.pending","✓","ok"],["s.picking","✓","ok"],["s.picked","✓","ok"],["s.oos","!","bad"]].map(([k,m,st],i) => (
                  <div key={i} className="flex items-center gap-2.5">
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${st==="ok"?"bg-emerald-100 text-emerald-600":"bg-rose-500 text-white"}`}>{m}</span>
                    <span className={`text-[12.5px] ${st==="bad"?"font-semibold text-rose-700":"text-stone-600"}`}>{t(k)}</span>
                    {st==="bad" && <span className="text-[11px] text-rose-500 ms-auto tabular-nums">{o.mins}{t("c.min")} · past {D.CUTOFF}</span>}
                  </div>
                ))}
              </div>
              <div className="rounded-lg bg-rose-50 ring-1 ring-rose-200/60 p-3 flex items-start gap-2">
                <I.AlertCircle width={15} height={15} className="text-rose-500 mt-0.5 flex-shrink-0" />
                <p className="text-[12px] text-rose-800 text-pretty">Items are out of stock in {o.zone}. Re-route to a substitute SKU or split-ship the in-stock items to recover SLA.</p>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="danger" size="md" icon={I.Layers} className="flex-1">Reassign picker</Button>
                <Button variant="secondary" size="md" icon={I.Box} className="flex-1">Split-ship</Button>
              </div>
            </div>
          </div>

          {/* Other breaches / at-risk */}
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400 mb-2 px-1">{t("ck.atrisk")}</div>
            <div className="bg-white rounded-xl ring-1 ring-stone-200/70 divide-y divide-stone-100 overflow-hidden">
              {atRisk.map((a) => (
                <div key={a.no} className="flex items-center gap-3 px-4 py-2.5">
                  <span className="font-mono text-[12px] text-stone-500 w-[84px] flex-shrink-0 truncate">{a.no}</span>
                  <span className="text-[12.5px] text-stone-900 flex-1 truncate">{a.customer}</span>
                  <SlaBadge sla={a.sla} size="sm" />
                  <span className="text-[11px] text-stone-400 tabular-nums">{a.mins}{t("c.min")}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
