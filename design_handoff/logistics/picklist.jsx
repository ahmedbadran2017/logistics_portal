/* global React, I, Badge, Avatar, Button, IconButton, Panel */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// PICK AUTOPILOT — AI agent control card (generate · assign · monitor · alert)
// ─────────────────────────────────────────────────────────────────────
function PickAutopilot({ onRun, onToast, onOpen }) {
  const { t } = window.useLg();
  const A = window.LG_AUTOPILOT;
  const [on, setOn] = useState(A.active);
  const [thinking, setThinking] = useState(false);
  const [recos, setRecos] = useState(A.recos);
  const kindStyle = {
    create: ["bg-[var(--accent-50)] text-[var(--accent-700)]", I.Zap],
    assign: ["bg-blue-50 text-blue-600", I.Layers],
    balance: ["bg-violet-50 text-violet-600", I.Users],
    alert: ["bg-rose-50 text-rose-600", I.AlertCircle],
    hold: ["bg-amber-50 text-amber-600", I.Clock],
  };
  function runNow() {
    setThinking(true);
    setTimeout(() => { setThinking(false); onRun?.(); onToast?.({ type: "success", text: "Autopilot generated 4 pick lists · auto-assigned · 41% less walking" }); }, 1400);
  }

  return (
    <div className={`rounded-2xl ring-1 mb-4 overflow-hidden ${on ? "ring-[var(--accent-300)]/60 bg-gradient-to-br from-[var(--accent-50)]/60 to-white" : "ring-stone-200 bg-white"}`}>
      <div className="p-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <div className={`relative w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${on ? "bg-gradient-to-br from-[var(--accent-500)] to-[var(--accent-700)] text-white" : "bg-stone-100 text-stone-400"}`}>
              <I.Zap width={22} height={22} />
              {on && <span className="absolute -top-0.5 -end-0.5 w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-white animate-pulse" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-[16px] font-semibold text-stone-900">{t("au.title")}</h2>
                <Badge tone={on ? "green" : "neutral"} dot>{on ? t("au.on") : t("au.off")}</Badge>
              </div>
              <div className="text-[12px] text-stone-500 mt-0.5">{t("au.sub")}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="md" icon={I.Zap} onClick={runNow} disabled={thinking || !on}>{thinking ? t("au.thinking") : t("au.runNow")}</Button>
            <Button variant="secondary" size="md" iconRight={I.ArrowRight} onClick={onOpen}>{t("au.open")}</Button>
            <Button variant={on ? "ghost" : "brand"} size="md" onClick={() => setOn((v) => !v)}>{on ? t("au.disable") : t("au.enable")}</Button>
          </div>
        </div>

        {on && (
          <>
            {/* live stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
              <ApStat icon={I.Clock} label={t("au.nextRun")} value={thinking ? "—" : `${A.nextRunMin}m`} sub={t("au.everyMin")} live />
              <ApStat icon={I.Box} label={t("au.todayCreated")} value={A.createdToday} />
              <ApStat icon={I.Users} label={t("au.todayAssigned")} value={A.assignedToday} />
              <ApStat icon={I.TrendUp} label={t("au.efficiency")} value={"+" + A.efficiency + "%"} tone="emerald" />
            </div>

            {/* suggestions */}
            {recos.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">{t("au.recos")}</div>
                {recos.map((r, i) => (
                  <div key={i} className="flex items-center gap-2.5 rounded-xl bg-white ring-1 ring-[var(--accent-200)]/50 px-3 py-2">
                    <I.Zap width={14} height={14} className="text-[var(--accent-600)] flex-shrink-0" />
                    <span className="text-[12px] text-stone-700 flex-1 text-pretty">{r.txt}</span>
                    <Button variant="brand" size="sm" onClick={() => { onRun?.(); setRecos((rs) => rs.filter((_, j) => j !== i)); onToast?.({ type: "success", text: "Suggestion applied · pick list created" }); }}>{t("au.apply")}</Button>
                    <button onClick={() => setRecos((rs) => rs.filter((_, j) => j !== i))} className="w-7 h-7 rounded-lg hover:bg-stone-100 flex items-center justify-center text-stone-400"><I.X width={13} height={13} /></button>
                  </div>
                ))}
              </div>
            )}

            {/* agent activity feed */}
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">{t("au.feed")}</span>
                <span className="text-[11px] text-stone-400">{t("au.watching").replace("{n}", A.watching)}</span>
              </div>
              <div className="space-y-1">
                {A.feed.map((e, i) => {
                  const [cls, Ic] = kindStyle[e.kind] || kindStyle.create;
                  return (
                    <div key={i} className="flex items-center gap-2.5 px-1 py-1">
                      <span className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${cls}`}><Ic width={12} height={12} /></span>
                      <span className="text-[12px] text-stone-700 flex-1 text-pretty">{e.act}</span>
                      <span className="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{e.t}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
window.PickAutopilot = PickAutopilot;
function ApStat({ icon: Icon, label, value, sub, tone, live }) {
  return (
    <div className="bg-white rounded-xl ring-1 ring-stone-200/60 p-3">
      <div className="flex items-center gap-1.5 text-stone-500"><Icon width={13} height={13} />{live && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />}<span className="text-[11px] font-medium">{label}</span></div>
      <div className={`text-[20px] font-semibold tabular-nums leading-none mt-1.5 ${tone === "emerald" ? "text-emerald-600" : "text-stone-900"}`}>{typeof value === "number" ? <window.CountUp value={value} /> : value}</div>
      {sub && <div className="text-[10px] text-stone-400 mt-1 truncate">{sub}</div>}
    </div>
  );
}

// ── Full Autopilot page (Overview · Rules · Decision log · Performance) ──
function AutopilotPage({ onBack, onToast }) {
  const { t } = window.useLg();
  const A = window.LG_AUTOPILOT;
  const [tab, setTab] = useState("overview");
  const tabs = [["overview", t("au.overview")], ["rules", t("au.rules")], ["history", t("au.history")], ["perf", t("au.perf")]];
  const kindStyle = {
    create: ["bg-[var(--accent-50)] text-[var(--accent-700)]", I.Zap], assign: ["bg-blue-50 text-blue-600", I.Layers],
    balance: ["bg-violet-50 text-violet-600", I.Users], alert: ["bg-rose-50 text-rose-600", I.AlertCircle], hold: ["bg-amber-50 text-amber-600", I.Clock],
  };
  const fullLog = [...A.feed, { t: "1h", act: "Created PL-51436 · single-item blitz (5 orders)", kind: "create" }, { t: "2h", act: "Auto-assigned 3 batches to morning shift", kind: "assign" }, { t: "2h", act: "SLA risk: 4 picked orders not labeled — pinged Reda", kind: "alert" }];

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap">
        <I.Back width={15} height={15} className="rtl:rotate-180" />{t("nav.picklists")}
      </button>

      {/* hero */}
      <div className="rounded-2xl ring-1 ring-[var(--accent-300)]/60 bg-gradient-to-br from-[var(--accent-50)]/60 to-white p-5 mb-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="relative w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--accent-500)] to-[var(--accent-700)] text-white flex items-center justify-center"><I.Zap width={24} height={24} /><span className="absolute -top-0.5 -end-0.5 w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-white animate-pulse" /></div>
            <div>
              <div className="flex items-center gap-2"><h1 className="text-[20px] font-semibold text-stone-900">{t("au.title")}</h1><Badge tone="green" dot>{t("au.on")}</Badge></div>
              <div className="text-[12.5px] text-stone-500 mt-0.5">{t("au.sub")}</div>
            </div>
          </div>
          <Button variant="brand" size="md" icon={I.Zap} onClick={() => onToast?.({ type: "success", text: "Autopilot run · 4 pick lists created & assigned" })}>{t("au.runNow")}</Button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <ApStat icon={I.Clock} label={t("au.nextRun")} value={`${A.nextRunMin}m`} sub={t("au.everyMin")} live />
          <ApStat icon={I.Box} label={t("au.todayCreated")} value={A.createdToday} />
          <ApStat icon={I.Users} label={t("au.todayAssigned")} value={A.assignedToday} />
          <ApStat icon={I.TrendUp} label={t("au.efficiency")} value={"+" + A.efficiency + "%"} tone="emerald" />
        </div>
      </div>

      {/* tabs */}
      <div className="flex items-center gap-1 border-b border-stone-200/70 mb-4">
        {tabs.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} className={`px-3 h-9 text-[13px] font-medium border-b-2 -mb-px transition-colors ${tab === k ? "border-[var(--accent-600)] text-stone-900" : "border-transparent text-stone-500 hover:text-stone-800"}`}>{l}</button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Panel title={t("au.recos")} bodyClass="p-3 space-y-2">
            {A.recos.map((r, i) => (
              <div key={i} className="flex items-center gap-2.5 rounded-xl bg-white ring-1 ring-[var(--accent-200)]/50 px-3 py-2">
                <I.Zap width={14} height={14} className="text-[var(--accent-600)] flex-shrink-0" />
                <span className="text-[12px] text-stone-700 flex-1 text-pretty">{r.txt}</span>
                <Button variant="brand" size="sm" onClick={() => onToast?.({ type: "success", text: "Suggestion applied" })}>{t("au.apply")}</Button>
              </div>
            ))}
          </Panel>
          <Panel title={t("au.feed")} right={<span className="text-[11px] text-stone-400">{t("au.watching").replace("{n}", A.watching)}</span>} bodyClass="p-3">
            <div className="space-y-1">
              {A.feed.map((e, i) => { const [cls, Ic] = kindStyle[e.kind] || kindStyle.create; return (
                <div key={i} className="flex items-center gap-2.5 px-1 py-1"><span className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${cls}`}><Ic width={12} height={12} /></span><span className="text-[12px] text-stone-700 flex-1 text-pretty">{e.act}</span><span className="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{e.t}</span></div>
              ); })}
            </div>
          </Panel>
        </div>
      )}

      {tab === "rules" && (
        <Panel title={t("au.config")} bodyClass="p-4 max-w-[560px]">
          <div className="space-y-4">
            <RuleRow label={t("au.strategy")} ctl={<Seg2 opts={[["zone","By zone"],["sku","By SKU"],["balanced","Balanced"]]} val="zone" />} />
            <RuleRow label={t("au.schedule")} ctl={<Seg2 opts={[["15m","15m"],["30m","30m"],["60m","60m"]]} val="30m" />} />
            <RuleRow label={t("au.batchThresh")} ctl={<Stepper val={4} />} />
            <RuleRow label={t("au.idleMin")} ctl={<Stepper val={6} />} />
            <RuleToggle label={t("au.autoAssign")} on />
            <RuleToggle label={t("au.idleReroute")} on />
            <RuleToggle label={t("au.slaWatch")} on />
            <div className="flex justify-end pt-2 border-t border-stone-100"><Button variant="brand" size="md" icon={I.Check} onClick={() => onToast?.({ type: "success", text: "Autopilot rules saved · synced to ERPNext scheduler" })}>{t("au.saveRules")}</Button></div>
          </div>
        </Panel>
      )}

      {tab === "history" && (
        <Panel title={t("au.allDecisions")} bodyClass="p-3">
          <div className="space-y-1">
            {fullLog.map((e, i) => { const [cls, Ic] = kindStyle[e.kind] || kindStyle.create; return (
              <div key={i} className="flex items-center gap-2.5 px-1.5 py-1.5 rounded-lg hover:bg-stone-50"><span className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${cls}`}><Ic width={13} height={13} /></span><span className="text-[12.5px] text-stone-700 flex-1 text-pretty">{e.act}</span><span className="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{e.t}</span></div>
            ); })}
          </div>
        </Panel>
      )}

      {tab === "perf" && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-4">
          <Panel title={t("au.efficiency")} sub="last 14 runs" bodyClass="p-4"><window.LineChart data={[22,28,25,31,34,30,36,38,35,40,39,42,41,41]} height={180} stroke="#10b981" /></Panel>
          <div className="space-y-3">
            <ApStat icon={I.Clock} label={t("au.walkSavedTotal")} value="3h 12m" tone="emerald" />
            <ApStat icon={I.Users} label={t("au.assignAcc")} value="96%" />
            <ApStat icon={I.Zap} label={t("au.runsToday")} value={18} />
          </div>
        </div>
      )}
    </div>
  );
}
window.AutopilotPage = AutopilotPage;
function RuleRow({ label, ctl }) { return <div className="flex items-center justify-between gap-3"><span className="text-[13px] text-stone-700">{label}</span>{ctl}</div>; }
function RuleToggle({ label, on }) { const [v, setV] = useState(on); return <div className="flex items-center justify-between gap-3"><span className="text-[13px] text-stone-700">{label}</span><button onClick={() => setV(!v)} className={`w-9 h-5 rounded-full p-0.5 transition-colors ${v ? "bg-[var(--accent-600)]" : "bg-stone-200"}`}><span className={`block w-4 h-4 rounded-full bg-white shadow transition-transform ${v ? "translate-x-4 rtl:-translate-x-4" : ""}`} /></button></div>; }
function Seg2({ opts, val }) { const [v, setV] = useState(val); return <div className="inline-flex bg-stone-100/80 rounded-lg p-0.5">{opts.map(([k, l]) => <button key={k} onClick={() => setV(k)} className={`px-2.5 h-7 text-[12px] font-medium rounded-md ${v === k ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-500"}`}>{l}</button>)}</div>; }
function Stepper({ val }) { const [v, setV] = useState(val); return <div className="inline-flex items-center gap-2"><button onClick={() => setV(Math.max(1, v - 1))} className="w-7 h-7 rounded-lg ring-1 ring-stone-200 text-stone-600 hover:bg-stone-50">−</button><span className="w-6 text-center text-[13px] font-semibold tabular-nums">{v}</span><button onClick={() => setV(v + 1)} className="w-7 h-7 rounded-lg ring-1 ring-stone-200 text-stone-600 hover:bg-stone-50">+</button></div>; }

// ─────────────────────────────────────────────────────────────────────
// SMART AUTO PICK LIST — groups pending orders to maximize pick efficiency
// ─────────────────────────────────────────────────────────────────────
function SmartPickModal({ onClose, onToast, dir, onGenerate }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [mode, setMode] = useState("smart");
  const [strategy, setStrategy] = useState("zone");
  const { groups, stats } = useMemo(() => window.autoPickGroups(strategy), [strategy]);
  const pickers = D.TEAM.filter((p) => p.role === "picker");
  const pool = window.LG_PICK_POOL || [];
  const poolOrders = [...new Set(pool.map((l) => l.so))];
  const [selOrders, setSelOrders] = useState(new Set());
  const [manPicker, setManPicker] = useState(pickers[0].id);
  function toggleOrder(o) { setSelOrders((s) => { const n = new Set(s); n.has(o) ? n.delete(o) : n.add(o); return n; }); }
  function createManual() {
    const chosen = pool.filter((l) => selOrders.has(l.so));
    const combined = selOrders.size > 1;
    onGenerate?.([{ no: "PL-" + (51450 + Math.floor(Math.random() * 40)), customer: combined ? `Manual · ${selOrders.size} orders` : pool.find((l) => selOrders.has(l.so))?.customer, item: "Manual", bin: "Multiple", qty: chosen.reduce((a, l) => a + l.qty, 0), items: chosen.length, status: "open", pct: 0, picker: manPicker, order: combined ? "combined" : [...selOrders][0] }]);
    onToast?.({ type: "success", text: `Manual pick list created · ${selOrders.size} orders · ${D.byId(manPicker).short}` });
    onClose();
  }

  const strategies = [
    ["zone", I.Pin, t("ap.zone"), t("ap.zoneSub")],
    ["sku", I.Layers, t("ap.sku"), t("ap.skuSub")],
    ["single", I.Zap, t("ap.single"), t("ap.singleSub")],
    ["balanced", I.Users, t("ap.balanced"), t("ap.balancedSub")],
  ];

  function generate() {
    onGenerate?.(groups.map((g, i) => ({
      no: g.no, customer: g.kind === "Batch SKU" ? g.label : `${g.kind} · ${g.label}`,
      item: g.kind, bin: g.aisles > 1 ? "Multiple" : g.lines[0].bin, qty: g.units, items: g.items,
      status: "open", pct: 0, picker: pickers[i % pickers.length].id, order: g.orders > 1 ? "combined" : g.lines[0].so,
    })));
    onToast?.({ type: "success", text: `${groups.length} smart pick lists created · ${stats.saved}% less walking` });
    onClose();
  }

  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-stone-900/30 backdrop-blur-[1px] animate-fade-in" onClick={onClose} />
      <div className="relative w-full max-w-[680px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] animate-scale-in overflow-hidden flex flex-col max-h-[88vh]" dir={dir}>
        <header className="flex items-center justify-between px-5 py-3.5 border-b border-stone-100">
          <div className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center"><I.Zap width={16} height={16} /></span>
            <div><div className="text-[14.5px] font-semibold text-stone-900">{t("nav.picklists")}</div>
            <div className="text-[11.5px] text-stone-500">{stats.orders} {t("ap.orders")} {t("c.of")} pending</div></div>
          </div>
          <IconButton icon={I.X} onClick={onClose} />
        </header>
        <div className="px-5 pt-3">
          <div className="inline-flex bg-stone-100/80 rounded-lg p-0.5 w-full">
            {[["smart", t("ap.smart")], ["manual", t("ap.manual")]].map(([k, l]) => (
              <button key={k} onClick={() => setMode(k)} className={`flex-1 h-8 text-[12.5px] font-medium rounded-md transition-all ${mode === k ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-500"}`}>{l}</button>
            ))}
          </div>
        </div>

        <div className="p-5 overflow-y-auto">
          {mode === "smart" ? <>
          {/* strategy picker */}
          <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">{t("ap.strategy")}</div>
          <div className="grid grid-cols-2 gap-2 mb-4">
            {strategies.map(([k, Icon, label, sub]) => (
              <button key={k} onClick={() => setStrategy(k)}
                className={`text-start rounded-xl ring-1 p-3 transition-all ${strategy === k ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40" : "ring-stone-200 hover:ring-stone-300"}`}>
                <div className="flex items-center gap-2"><Icon width={15} height={15} className={strategy === k ? "text-[var(--accent-700)]" : "text-stone-400"} /><span className="text-[12.5px] font-semibold text-stone-900">{label}</span></div>
                <div className="text-[11px] text-stone-500 mt-0.5">{sub}</div>
              </button>
            ))}
          </div>

          {/* efficiency banner */}
          <div className="flex items-center gap-3 rounded-xl bg-emerald-50 ring-1 ring-emerald-200/60 px-4 py-2.5 mb-4">
            <I.TrendUp width={18} height={18} className="text-emerald-600 flex-shrink-0" />
            <div className="text-[12.5px] text-emerald-800 flex-1"><span className="font-bold tabular-nums">{stats.saved}%</span> {t("ap.walkSaved")} · <span className="font-semibold">{stats.batches}</span> {t("ap.batches")} {t("c.of")} {stats.orders} {t("ap.orders")}</div>
          </div>

          {/* generated batches */}
          <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">{t("ap.preview")}</div>
          <div className="space-y-2">
            {groups.map((g, i) => (
              <div key={g.key} className="rounded-xl ring-1 ring-stone-200 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-[12px] font-semibold text-stone-900">{g.no}</span>
                    <Badge tone="purple" className="whitespace-nowrap">{g.kind}</Badge>
                    <span className="text-[12px] text-stone-600 truncate">{g.label}</span>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <Avatar name={D.byId(pickers[i % pickers.length].id).name} size={20} />
                    <span className="text-[11px] text-stone-500 hidden sm:inline">{D.byId(pickers[i % pickers.length].id).short}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-2 text-[11px] text-stone-500">
                  <span className="tabular-nums">{g.orders} {t("ap.orders")}</span><span className="text-stone-300">·</span>
                  <span className="tabular-nums">{g.items} {t("ap.lines")}</span><span className="text-stone-300">·</span>
                  <span className="tabular-nums">{g.units} {t("ap.units")}</span><span className="text-stone-300">·</span>
                  <span className="inline-flex items-center gap-1 tabular-nums"><I.Pin width={10} height={10} />{g.aisles} {t("ap.aisles")}</span>
                </div>
              </div>
            ))}
          </div>
          </> : <>
            <div className="rounded-lg bg-amber-50 ring-1 ring-amber-200/60 px-3 py-2 mb-3 flex items-start gap-2 text-[11.5px] text-amber-800"><I.AlertCircle width={13} height={13} className="text-amber-500 mt-0.5 flex-shrink-0" />{t("mp.manualHint")}</div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">{t("mp.assignTo")}</div>
            <div className="grid grid-cols-3 gap-1.5 mb-4">
              {pickers.map((p) => (
                <button key={p.id} onClick={() => setManPicker(p.id)} className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg ring-1 transition-all ${manPicker === p.id ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40" : "ring-stone-200 hover:ring-stone-300"}`}><Avatar name={p.name} size={20} /><span className="text-[11.5px] font-medium text-stone-800 truncate">{p.short}</span></button>
              ))}
            </div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">{t("mp.selectOrders")} · {selOrders.size} {t("mp.selected")}</div>
            <div className="space-y-1.5">
              {poolOrders.map((o) => {
                const ls = pool.filter((l) => l.so === o); const on = selOrders.has(o);
                return (
                  <button key={o} onClick={() => toggleOrder(o)} className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg ring-1 text-start transition-all ${on ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40" : "ring-stone-200 hover:ring-stone-300"}`}>
                    <span className={`w-4 h-4 rounded flex items-center justify-center ring-1 flex-shrink-0 ${on ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300"}`}>{on && <I.Check width={11} height={11} />}</span>
                    <span className="font-mono text-[12px] font-semibold text-stone-900">{o}</span>
                    <span className="text-[12px] text-stone-600 flex-1 truncate">{ls[0].customer}</span>
                    <span className="text-[11px] text-stone-400">{ls.length} {t("ap.lines")}</span>
                  </button>
                );
              })}
            </div>
          </>}
        </div>

        <footer className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-stone-100 bg-stone-50/60">
          <Button variant="ghost" size="md" onClick={onClose}>{t("c.cancel")}</Button>
          {mode === "smart"
            ? <Button variant="brand" size="md" icon={I.Check} onClick={generate}>{t("ap.generate").replace("{n}", groups.length)}</Button>
            : <Button variant="brand" size="md" icon={I.Check} disabled={selOrders.size === 0} onClick={createManual}>{t("mp.createManual")} ({selOrders.size})</Button>}
        </footer>
      </div>
    </div>
  );
}
window.SmartPickModal = SmartPickModal;

// ─────────────────────────────────────────────────────────────────────
// PICK LIST DETAIL — internal view: walk path ordered by bin, scan state
// ─────────────────────────────────────────────────────────────────────
function PickListDetail({ pl, onClose, dir }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const lines = useMemo(() => {
    const pool = window.LG_PICK_POOL || [];
    let ls = pool.slice(0, Math.max(1, pl.items || 1)).map((l) => ({ ...l }));
    return ls.sort((a, b) => (a.bin > b.bin ? 1 : -1)).map((l, i) => { const picked = pl.pct >= 100 || (pl.pct > 0 && i < Math.floor(ls.length * pl.pct / 100)); const partial = pl.errors && i === ls.length - 1 && l.qty > 1; return { ...l, picked: picked && !partial, pickedQty: partial ? l.qty - 1 : (picked ? l.qty : 0), partial }; });
  }, [pl]);
  const done = lines.filter((l) => l.picked).length;
  const aisles = new Set(lines.map((l) => window.lgAisle(l.bin))).size;
  const orders = new Set(lines.map((l) => l.so)).size;
  const units = lines.reduce((a, l) => a + l.qty, 0);
  const isErr = !!pl.errors;
  const [view, setView] = useState("walk");
  const estTime = Math.round(lines.length * 1.6 + aisles * 1.2);
  // by-SKU consolidation (batch pick)
  const bySku = useMemo(() => {
    const m = {};
    lines.forEach((l) => { (m[l.sku] = m[l.sku] || { ...l, qtyTot: 0, orders: [] }); m[l.sku].qtyTot += l.qty; m[l.sku].orders.push(l.so); });
    return Object.values(m).sort((a, b) => (a.bin > b.bin ? 1 : -1));
  }, [lines]);
  const byOrder = useMemo(() => {
    const m = {};
    lines.forEach((l) => { (m[l.so] = m[l.so] || { so: l.so, customer: l.customer, items: [] }); m[l.so].items.push(l); });
    return Object.values(m);
  }, [lines]);

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onClose} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap">
        <I.Back width={15} height={15} className="rtl:rotate-180" />{t("nav.picklists")}
      </button>

      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="w-11 h-11 rounded-xl bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center"><I.Box width={22} height={22} /></span>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="font-mono text-[19px] font-bold text-stone-900">{pl.no}</h1>
                {pl.order === "combined" ? <Badge tone="purple" className="whitespace-nowrap">{t("dp.combined")}</Badge> : <Badge tone="neutral">{pl.customer}</Badge>}
                {isErr ? <Badge tone="red" dot className="whitespace-nowrap">Short-pick</Badge> : <Badge tone={pl.pct >= 100 ? "green" : pl.pct > 0 ? "blue" : "yellow"} dot>{pl.pct >= 100 ? t("rt.closed") : pl.pct > 0 ? t("s.picking") : t("s.pending")}</Badge>}
              </div>
              <div className="text-[12.5px] text-stone-600 mt-1 flex items-center gap-2"><Avatar name={D.byId(pl.picker).name} size={20} />{D.byId(pl.picker).name} · {t("ap.optimized")}</div>
              <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                <Badge tone="neutral" className="whitespace-nowrap">{t("ap.purpose")}</Badge>
                <Badge tone="neutral" className="whitespace-nowrap">{t("ap.source")}: {D.WAREHOUSE}</Badge>
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200/60 rounded px-1.5 py-0.5"><I.Search width={10} height={10} />{t("ap.scanMode")}</span>
                {pl.order === "combined" && <span className="inline-flex items-center gap-1 text-[11px] font-medium text-violet-700 bg-violet-50 ring-1 ring-violet-200/60 rounded px-1.5 py-0.5"><I.Layers width={10} height={10} />{t("ap.grouped")}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {pl.pct < 100 && <Button variant="brand" size="md" icon={I.Box}>{pl.pct > 0 ? t("pc.continuePick") : t("pc.startPick")}</Button>}
            <Button variant="secondary" size="md" icon={I.Users}>{t("pc.reassign")}</Button>
            <Button variant="secondary" size="md" icon={I.Download}>{t("c.print")}</Button>
            <Button variant="secondary" size="md" iconRight={I.External}>{t("c.openInErp")}</Button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <PlStat label={t("ap.orders")} value={orders} />
          <PlStat label={t("ap.lines")} value={lines.length} />
          <PlStat label={t("ap.units")} value={units} />
          <PlStat label={t("pc.estTime")} value={estTime + "m"} tone="accent" />
        </div>
        <div className="mt-4">
          <div className="flex items-center justify-between text-[11px] mb-1"><span className="text-stone-500 tabular-nums">{done} / {lines.length} {t("pk.scanned").toLowerCase()}</span><span className="font-semibold tabular-nums text-emerald-600">{Math.round(done / lines.length * 100)}%</span></div>
          <div className="h-2 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${isErr ? "bg-rose-500" : "bg-emerald-500"}`} style={{ width: `${done / lines.length * 100}%` }} /></div>
        </div>
      </div>

      {/* lifecycle stepper */}
      <Panel title={t("pc.cycle")} className="mb-4" bodyClass="p-4">
        {(() => {
          const steps = [["pc.created", I.Plus], ["pc.assigned", I.Users], ["pc.picking", I.Box], ["pc.completed", I.CheckCircle], ["pc.toPack", I.Tag]];
          const cur = pl.pct >= 100 ? 3 : pl.pct > 0 ? 2 : (pl.status === "open" ? 1 : 0);
          const times = ["08:58", "09:01", "09:08", "09:25", "—"];
          return (
            <div className="flex items-center">
              {steps.map(([k, Ic], i) => {
                const done = i <= cur;
                return (
                  <React.Fragment key={k}>
                    <div className="flex flex-col items-center gap-1.5 flex-shrink-0" style={{ width: 92 }}>
                      <span className={`w-9 h-9 rounded-xl flex items-center justify-center ${done ? "bg-emerald-500 text-white" : "bg-stone-100 text-stone-400"}`}>{done ? <I.Check width={16} height={16} /> : <Ic width={15} height={15} />}</span>
                      <span className={`text-[11px] font-medium text-center leading-tight ${done ? "text-stone-900" : "text-stone-400"}`}>{t(k)}</span>
                      <span className="text-[10px] text-stone-400 tabular-nums">{i <= cur ? times[i] : ""}</span>
                    </div>
                    {i < steps.length - 1 && <div className={`flex-1 h-0.5 -mt-6 ${i < cur ? "bg-emerald-300" : "bg-stone-200"}`} />}
                  </React.Fragment>
                );
              })}
            </div>
          );
        })()}
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4">
        <Panel title={view === "walk" ? t("ap.walkPath") : view === "sku" ? t("pc.bySku") : t("pc.byOrder")} sub={view === "walk" ? t("ap.optimized") : null} right={
          <div className="inline-flex bg-stone-100/80 rounded-lg p-0.5">
            {[["walk", t("pc.walk")], ["sku", t("pc.bySku")], ["order", t("pc.byOrder")]].map(([k, l]) => (
              <button key={k} onClick={() => setView(k)} className={`px-2.5 h-7 text-[11.5px] font-medium rounded-md transition-all ${view === k ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-500 hover:text-stone-800"}`}>{l}</button>
            ))}
          </div>
        } bodyClass="p-4">
        {view === "walk" && <ol className="relative">
          {lines.map((l, i) => {
            const last = i === lines.length - 1;
            const newAisle = i === 0 || window.lgAisle(l.bin) !== window.lgAisle(lines[i - 1].bin);
            return (
              <li key={i} className="relative flex gap-3.5 pb-3 last:pb-0">
                {!last && <span className={`absolute top-9 w-px ${l.picked ? "bg-emerald-200" : "bg-stone-200"}`} style={dir === "rtl" ? { right: 15 } : { left: 15 }} />}
                <span className={`relative z-10 w-[31px] h-[31px] rounded-lg flex items-center justify-center text-[12px] font-bold flex-shrink-0 ${l.picked ? "bg-emerald-500 text-white" : l.partial ? "bg-amber-500 text-white" : "bg-white ring-1 ring-stone-300 text-stone-500"}`}>{l.picked ? <I.Check width={15} height={15} /> : l.partial ? <I.AlertCircle width={14} height={14} /> : i + 1}</span>
                <div className={`min-w-0 flex-1 rounded-xl ring-1 p-3 ${l.picked ? "ring-emerald-200 bg-emerald-50/40" : l.partial ? "ring-amber-200 bg-amber-50/40" : "ring-stone-200 bg-white"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-stone-900 text-white text-[12px] font-bold font-mono"><I.Pin width={11} height={11} />{l.bin}</span>
                      {newAisle && <span className="text-[10px] font-medium text-[var(--accent-700)] bg-[var(--accent-50)] rounded px-1.5 py-0.5">{window.lgBinZone(l.bin).replace(" - JM", "")}</span>}
                    </div>
                    <span className={`text-[13px] font-bold tabular-nums ${l.partial ? "text-amber-600" : "text-stone-900"}`}>{l.pickedQty}/{l.qty} {l.partial ? t("ap.picked") : "×"}</span>
                  </div>
                  <div className="text-[13.5px] font-medium text-stone-900 mt-2">{l.name}</div>
                  <div className="text-[11.5px] text-stone-500 flex items-center gap-2 mt-1 flex-wrap"><span className="font-mono">{l.sku}</span><span className="text-stone-300">·</span><span className="truncate">{l.so} · {l.customer}</span></div>
                  <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                    {l.code && <span className="font-mono text-[10px] text-stone-400 bg-stone-50 ring-1 ring-stone-200/70 rounded px-1.5 py-0.5">⌗ {l.code}</span>}
                    {l.grp && <span className="text-[10px] font-medium text-stone-500 bg-stone-100 rounded px-1.5 py-0.5">{l.grp}</span>}
                    {l.uom && l.uom !== "Nos" && <span className="text-[10px] font-medium text-stone-500 bg-stone-100 rounded px-1.5 py-0.5">{l.uom}</span>}
                    {(l.serial || l.batch) && <span className="inline-flex items-center gap-1 text-[10px] font-medium text-violet-700 bg-violet-50 ring-1 ring-violet-200/60 rounded px-1.5 py-0.5"><I.Tag width={9} height={9} />{l.serial ? "Serial" : "Batch"}</span>}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>}

        {view === "sku" && <div className="space-y-2">
          {bySku.map((l, i) => (
            <div key={i} className="rounded-xl ring-1 ring-stone-200 bg-white p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-stone-900 text-white text-[12px] font-bold font-mono"><I.Pin width={11} height={11} />{l.bin}</span>
                <span className="text-[15px] font-bold text-[var(--accent-700)] tabular-nums">{l.qtyTot}× {t("pc.batchPick")}</span>
              </div>
              <div className="text-[13.5px] font-medium text-stone-900 mt-2">{l.name}</div>
              <div className="text-[11.5px] text-stone-500 mt-1"><span className="font-mono">{l.sku}</span> · {t("pc.splits")} {l.orders.length} {t("ap.orders")}: <span className="text-stone-600">{l.orders.join(", ")}</span></div>
            </div>
          ))}
        </div>}

        {view === "order" && <div className="space-y-3">
          {byOrder.map((o, i) => (
            <div key={i} className="rounded-xl ring-1 ring-stone-200 overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2 bg-stone-50 border-b border-stone-100">
                <span className="font-mono text-[12px] font-semibold text-stone-900">{o.so}</span>
                <span className="text-[11.5px] text-stone-500 flex-1 truncate">{o.customer}</span>
                <Badge tone="neutral">{o.items.length} {t("ap.lines")}</Badge>
              </div>
              <div className="divide-y divide-stone-100">
                {o.items.map((l, j) => (
                  <div key={j} className="flex items-center gap-2.5 px-3 py-2">
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stone-900 text-white text-[10.5px] font-bold font-mono flex-shrink-0"><I.Pin width={9} height={9} />{l.bin}</span>
                    <span className="text-[12.5px] text-stone-800 flex-1 truncate">{l.name}</span>
                    <span className="text-[12px] font-semibold text-stone-900 tabular-nums">×{l.qty}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>}
        </Panel>

        <div className="space-y-4">
          <window.AttachPanel stageReady={pl.pct > 0} />
          <window.ActivityFeed events={[
            { who: "Anass", act: "Pick list created", at: "08:58", on: true },
            { who: D.byId(pl.picker).short, act: "Assigned to " + D.byId(pl.picker).short, at: "09:01", on: true },
            { who: D.byId(pl.picker).short, act: "Picking started", at: "09:08", on: pl.pct > 0 },
            { who: D.byId(pl.picker).short, act: isErr ? "Short-pick reported" : "All items scanned", at: "09:25", on: pl.pct >= 100 || isErr, bad: isErr },
          ]} />
        </div>
      </div>
    </div>
  );
}
window.PickListDetail = PickListDetail;
function PlStat({ label, value, tone }) {
  return <div className="bg-stone-50 rounded-xl px-3 py-2.5"><div className={`text-[22px] font-semibold tabular-nums leading-none ${tone === "accent" ? "text-[var(--accent-700)]" : "text-stone-900"}`}><window.CountUp value={value} /></div><div className="text-[11px] text-stone-500 mt-1.5">{label}</div></div>;
}
