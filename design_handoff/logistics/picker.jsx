/* global React, I, Badge, Avatar, Button, StageBadge, SlaBadge, ScanInput, EmptyState, LangSwitcher, Sparkline */
const { useState, useEffect, useMemo, useRef } = React;

// ─────────────────────────────────────────────────────────────────────
// PICKER — mobile-first My Queue + scan-to-complete. Runs in PhoneFrame.
// ─────────────────────────────────────────────────────────────────────
function PickerApp() {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const me = D.byId("marouane");

  const initialQueue = useMemo(() => {
    const order = { breached: 0, atrisk: 1, ontrack: 2, late: 2, returned: 3 };
    return D.ORDERS
      .filter((o) => ["pending", "picking", "picked"].includes(o.stage))
      .filter((o) => !o.picker || o.picker === "marouane")
      .sort((a, b) => order[a.sla] - order[b.sla] || a.mins - b.mins)
      .slice(0, 5);
  }, []);

  const [view, setView] = useState("queue"); // queue | pick | done | perf
  const [queue, setQueue] = useState(initialQueue);
  const [active, setActive] = useState(null);
  const [completedToday, setCompletedToday] = useState(38);

  function openPick(o) { setActive(o); setView("pick"); }
  function completePick() {
    setQueue((q) => q.filter((o) => o.no !== active.no));
    setCompletedToday((c) => c + 1);
    setView("done");
  }
  function next() { setActive(null); setView("queue"); }

  return (
    <div className="min-h-full bg-stone-50 flex flex-col" style={{ minHeight: 779 }}>
      {view !== "pick" && view !== "done" && <PickerTop me={me} />}
      <div className="flex-1">
        {view === "queue" && <QueueView queue={queue} onOpen={openPick} completed={completedToday} />}
        {view === "pick" && <PickView order={active} onBack={() => setView("queue")} onComplete={completePick} />}
        {view === "done" && <DoneView order={active} onNext={next} remaining={queue.length} />}
        {view === "perf" && <MobilePerf completed={completedToday} />}
      </div>
      {view !== "pick" && view !== "done" && <BottomNav view={view} setView={setView} />}
    </div>
  );
}
window.PickerApp = PickerApp;

function PickerTop({ me }) {
  const { t } = window.useLg();
  return (
    <div className="bg-white border-b border-stone-200/70 px-4 pt-3 pb-3 sticky top-0 z-10">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Avatar name={me.name} size={36} />
          <div className="leading-tight">
            <div className="text-[11px] text-stone-500">{t("pk.hi")},</div>
            <div className="text-[14px] font-semibold text-stone-900">{me.short}</div>
          </div>
        </div>
        <LangSwitcher compact />
      </div>
    </div>
  );
}

function QueueView({ queue, onOpen, completed }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const me = D.LEADERBOARD.find((p) => p.id === "marouane");
  const nextDue = queue[0]?.mins ?? 0;
  return (
    <div className="px-4 py-3.5 space-y-3.5">
      {/* stat strip */}
      <div className="grid grid-cols-3 gap-2">
        <MiniStat value={completed} label={t("pk.todays")} tone="stone" />
        <MiniStat value={me.sla + "%"} label={t("pk.hitrate")} tone="emerald" />
        <MiniStat value={nextDue + t("c.min")} label={t("pk.nextdue")} tone={nextDue < 20 ? "rose" : "amber"} />
      </div>

      <div className="flex items-center justify-between pt-1">
        <h2 className="text-[15px] font-semibold text-stone-900">{t("pk.queue")}</h2>
        <span className="text-[11px] text-stone-500">{t("pk.urgent")}</span>
      </div>

      {queue.length === 0 && <EmptyState title={t("pk.empty")} sub={t("pk.emptySub")} />}

      <div className="space-y-2.5">
        {queue.map((o) => <OrderCard key={o.no} o={o} onOpen={() => onOpen(o)} />)}
      </div>
    </div>
  );
}

function MiniStat({ value, label, tone }) {
  const tones = { stone: "text-stone-900", emerald: "text-emerald-600", amber: "text-amber-600", rose: "text-rose-600" };
  return (
    <div className="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
      <div className={`text-[19px] font-semibold tabular-nums leading-none ${tones[tone]}`}>{value}</div>
      <div className="text-[10px] text-stone-500 mt-1 leading-tight">{label}</div>
    </div>
  );
}

function OrderCard({ o, onOpen }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const urgent = o.sla === "breached" || o.sla === "atrisk";
  return (
    <button onClick={onOpen}
      className={`w-full text-start bg-white rounded-2xl ring-1 p-3.5 transition-all active:scale-[0.99] ${urgent ? "ring-rose-200" : "ring-stone-200/70"}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[13px] font-bold text-stone-900">{o.no}</span>
          <SlaBadge sla={o.sla} size="sm" />
        </div>
        <span className="text-[13px] font-semibold text-stone-900 tabular-nums">{window.fmtMAD(o.total)} <span className="text-[10px] text-stone-400">MAD</span></span>
      </div>
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <div className="text-[13.5px] font-medium text-stone-800 truncate">{o.customer}</div>
          <div className="text-[11.5px] text-stone-500 mt-0.5 flex items-center gap-1.5">
            <I.Pin width={11} height={11} className="text-stone-400" />{o.zone}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ps-2">
          <div className="text-end">
            <div className="text-[15px] font-bold text-stone-900 tabular-nums leading-none">{o.items}</div>
            <div className="text-[9.5px] text-stone-400 uppercase">{t("c.items")}</div>
          </div>
          <span className="w-9 h-9 rounded-full bg-stone-900 text-white flex items-center justify-center"><I.ArrowRight width={16} height={16} className="rtl:rotate-180" /></span>
        </div>
      </div>
    </button>
  );
}

// ── Pick mode (scan) ─────────────────────────────────────────────────
function PickView({ order, onBack, onComplete }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [items, setItems] = useState(() => D.PICK_ITEMS.map((it) => ({ ...it, scanned: false })).slice(0, Math.min(order.items, 3) || 1));
  const [feedback, setFeedback] = useState("idle"); // idle | ok | err
  const allScanned = items.every((i) => i.scanned);
  const nextIdx = items.findIndex((i) => !i.scanned);

  function scan() {
    if (nextIdx === -1) return;
    setFeedback("ok");
    setItems((arr) => arr.map((it, i) => (i === nextIdx ? { ...it, scanned: true } : it)));
    setTimeout(() => setFeedback("idle"), 700);
  }

  return (
    <div className="min-h-full bg-white flex flex-col" style={{ minHeight: 779 }}>
      {/* header */}
      <div className="px-4 pt-3 pb-3 border-b border-stone-100 flex items-center gap-3 sticky top-0 bg-white z-10">
        <button onClick={onBack} className="w-9 h-9 rounded-full hover:bg-stone-100 flex items-center justify-center text-stone-600"><I.Back width={18} height={18} className="rtl:rotate-180" /></button>
        <div className="flex-1">
          <div className="font-mono text-[14px] font-bold text-stone-900">{order.no}</div>
          <div className="text-[11.5px] text-stone-500">{order.customer}</div>
        </div>
        <SlaBadge sla={order.sla} size="sm" />
      </div>

      {/* progress */}
      <div className="px-4 py-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[12px] font-medium text-stone-500 whitespace-nowrap">{items.filter(i=>i.scanned).length} / {items.length} {t("c.scan").toLowerCase()}</span>
          <span className="text-[12px] font-semibold text-emerald-600">{Math.round(items.filter(i=>i.scanned).length/items.length*100)}%</span>
        </div>
        <div className="h-2 rounded-full bg-stone-100 overflow-hidden">
          <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${items.filter(i=>i.scanned).length/items.length*100}%`, transition: "width .4s cubic-bezier(.16,1,.3,1)" }} />
        </div>
      </div>

      {/* item list */}
      <div className="px-4 space-y-2.5 flex-1">
        {items.map((it, i) => {
          const isNext = i === nextIdx;
          return (
            <div key={it.sku}
              className={`rounded-2xl ring-1 p-3.5 transition-all ${it.scanned ? "ring-emerald-200 bg-emerald-50/50" : isNext ? "ring-stone-900 bg-white shadow-[0_4px_16px_-6px_rgba(0,0,0,0.12)]" : "ring-stone-200 bg-white opacity-60"}`}>
              <div className="flex items-center gap-3">
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${it.scanned ? "bg-emerald-500 text-white" : "bg-stone-100 text-stone-400"}`}>
                  {it.scanned ? <I.Check width={22} height={22} /> : <I.Box width={20} height={20} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[13.5px] font-medium text-stone-900 truncate">{it.name}</div>
                  <div className="text-[11.5px] text-stone-500 mt-0.5 flex items-center gap-2">
                    <span className="font-mono">{it.sku}</span>
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stone-100 text-stone-600 font-medium whitespace-nowrap"><I.Pin width={10} height={10} />{it.bin}</span>
                  </div>
                  {it.scanned && <div className="text-[10.5px] text-emerald-600 mt-1 font-mono flex items-center gap-1"><I.Check width={10} height={10} />Batch B{it.sku.replace(/\D/g,"").slice(0,4)} · serial captured</div>}
                </div>
                <div className="text-end">
                  <div className="text-[15px] font-bold text-stone-900 tabular-nums leading-none">×{it.qty}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* scan dock */}
      <div className="sticky bottom-0 bg-white border-t border-stone-100 p-4 pt-3 space-y-2.5">
        {!allScanned ? (
          <>
            <ScanInput placeholder={t("pk.scanItem")} onScan={scan} state={feedback} />
            {feedback === "ok" && <div className="text-center text-[12px] font-semibold text-emerald-600 animate-fade-in">✓ {t("pk.scanned")}</div>}
          </>
        ) : (
          <div className="space-y-2.5 animate-fade-in">
            <div className="flex items-center justify-center gap-2 text-[13px] font-semibold text-emerald-600"><I.CheckCircle width={18} height={18} />{t("pk.allScanned")}</div>
            <Button variant="success" size="lg" icon={I.Check} className="w-full !h-14 !text-[15px] !rounded-2xl" onClick={onComplete}>{t("pk.completePick")}</Button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Done / success ───────────────────────────────────────────────────
function DoneView({ order, onNext, remaining }) {
  const { t } = window.useLg();
  useEffect(() => { const id = setTimeout(onNext, 2400); return () => clearTimeout(id); }, []);
  return (
    <div className="min-h-full bg-gradient-to-b from-emerald-50 to-white flex flex-col items-center justify-center text-center px-8" style={{ minHeight: 779 }}>
      <div className="w-24 h-24 rounded-full bg-emerald-500 text-white flex items-center justify-center mb-5 animate-scale-in shadow-[0_12px_40px_-8px_rgba(16,185,129,0.5)]">
        <I.Check width={48} height={48} />
      </div>
      <div className="text-[22px] font-bold text-stone-900">{t("pk.nicework")} 🎉</div>
      <div className="text-[14px] text-stone-600 mt-1">{order.no} · {order.customer}</div>
      <div className="mt-6 text-[12.5px] text-stone-500">{t("pk.advancing")}</div>
      <div className="mt-2 flex items-center gap-1">
        {[0,1,2].map((i) => <span key={i} className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" style={{ animationDelay: `${i*0.15}s` }} />)}
      </div>
    </div>
  );
}

// ── Mobile performance (coaching) ────────────────────────────────────
function MobilePerf({ completed }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const me = D.LEADERBOARD.find((p) => p.id === "marouane");
  const target = me.target, remaining = Math.max(0, target - completed);
  const pct = Math.min(1, completed / target);
  return (
    <div className="px-4 py-4 space-y-4">
      <h2 className="text-[16px] font-semibold text-stone-900">{t("pf.title")}</h2>

      <div className="bg-gradient-to-br from-[var(--accent-50)] to-white rounded-2xl ring-1 ring-[var(--accent-200)]/50 p-5 text-center">
        <div className="text-[12px] font-medium text-[var(--accent-700)]">{t("pf.coaching")}</div>
        <div className="mt-3 text-[44px] font-bold text-stone-900 tabular-nums leading-none">{completed}<span className="text-[20px] text-stone-400">/{target}</span></div>
        <div className="mt-3 h-3 rounded-full bg-white ring-1 ring-[var(--accent-200)]/60 overflow-hidden">
          <div className="h-full rounded-full bg-[var(--accent-500)]" style={{ width: `${pct*100}%`, transition: "width .6s cubic-bezier(.16,1,.3,1)" }} />
        </div>
        <div className="mt-2.5 text-[13px] font-semibold text-emerald-600">{remaining > 0 ? `${remaining} ${t("pf.toGo")} 💪` : `🎯 ${t("c.target")} ✓`}</div>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <BigMobileStat value={me.avg} label={t("pf.avgTime")} />
        <BigMobileStat value={me.sla + "%"} label={t("pk.hitrate")} />
        <BigMobileStat value={"#" + me.rank} label={`${t("c.rank")} ${t("c.of")} 6`} />
        <BigMobileStat value={"+" + (me.picks - 31)} label={t("pf.vsTeam")} good />
      </div>

      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
        <div className="text-[12px] font-medium text-stone-500 mb-2">{t("pf.trend")}</div>
        <Sparkline data={me.trend} width={310} height={56} />
      </div>
    </div>
  );
}

function BigMobileStat({ value, label, good }) {
  return (
    <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 px-4 py-3.5">
      <div className={`text-[22px] font-bold tabular-nums leading-none ${good ? "text-emerald-600" : "text-stone-900"}`}>{value}</div>
      <div className="text-[11px] text-stone-500 mt-1.5">{label}</div>
    </div>
  );
}

// ── Bottom nav ───────────────────────────────────────────────────────
function BottomNav({ view, setView }) {
  const { t } = window.useLg();
  const items = [["queue", t("nav.queue"), I.Box], ["perf", t("nav.performance"), I.TrendUp]];
  return (
    <div className="sticky bottom-0 bg-white/95 backdrop-blur border-t border-stone-200/70 px-6 pt-2 pb-5 flex items-center justify-around">
      {items.map(([key, label, Icon]) => {
        const active = view === key;
        return (
          <button key={key} onClick={() => setView(key)} className="flex flex-col items-center gap-0.5 px-6 py-1">
            <Icon width={22} height={22} className={active ? "text-[var(--accent-700)]" : "text-stone-400"} />
            <span className={`text-[10px] font-medium ${active ? "text-[var(--accent-700)]" : "text-stone-400"}`}>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
