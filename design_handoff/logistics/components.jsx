/* global React, I, Badge, Avatar, Sparkline, Button, IconButton */
const { useState, useEffect, useRef } = React;

// ─────────────────────────────────────────────────────────────────────
// LOGISTICS COMPONENT KIT — built on the Yol Admin v2 primitives.
// ─────────────────────────────────────────────────────────────────────
const D = () => window.LG_DATA;
function useLg() { return React.useContext(window.LgContext); }
window.useLg = useLg;

// ── CountUp — animated numeric value (foreground only; safe fallback) ─
function CountUp({ value }) {
  const str = String(value);
  const numeric = typeof value === "number" || /^[\d,]+(\.\d+)?$/.test(str);
  const target = numeric ? parseFloat(str.replace(/,/g, "")) : null;
  const dec = numeric && str.includes(".") ? (str.split(".")[1] || "").length : 0;
  const fmt = (n) => n.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const [disp, setDisp] = useState(numeric ? fmt(target) : value);
  useEffect(() => {
    if (!numeric) { setDisp(value); return; }
    let reduce = false;
    try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}
    if (document.visibilityState === "hidden" || reduce) { setDisp(fmt(target)); return; }
    let raf, start; const dur = 750;
    setDisp(fmt(0));
    function tick(ts) { if (!start) start = ts; const p = Math.min(1, (ts - start) / dur); const e = 1 - Math.pow(1 - p, 3); setDisp(fmt(target * e)); if (p < 1) raf = requestAnimationFrame(tick); else setDisp(fmt(target)); }
    raf = requestAnimationFrame(tick);
    const guard = setTimeout(() => setDisp(fmt(target)), dur + 120);
    return () => { cancelAnimationFrame(raf); clearTimeout(guard); };
  }, [value]);
  return disp;
}
window.CountUp = CountUp;

// ── Stage badge ──────────────────────────────────────────────────────
function StageBadge({ stage, size = "md" }) {
  const { t } = useLg();
  const s = D().STAGE[stage] || D().STAGE.pending;
  const pad = size === "sm" ? "text-[10.5px] px-1.5 py-0.5" : "text-[11.5px] px-2 py-0.5";
  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-md ring-1 ring-inset whitespace-nowrap ${pad} ${s.txt} ${s.bg} ${s.ring}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {t("s." + stage)}
    </span>
  );
}
window.StageBadge = StageBadge;

// ── SLA badge ────────────────────────────────────────────────────────
function SlaBadge({ sla, size = "md" }) {
  const { t } = useLg();
  const s = D().SLA[sla] || D().SLA.ontrack;
  const pad = size === "sm" ? "text-[10.5px] px-1.5 py-0.5" : "text-[11.5px] px-2 py-0.5";
  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-md ring-1 ring-inset whitespace-nowrap ${pad} ${s.txt} ${s.bg} ${s.ring}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {t("sla." + sla)}
    </span>
  );
}
window.SlaBadge = SlaBadge;

// ── Tracking badge ───────────────────────────────────────────────────
function TrackBadge({ state }) {
  const { t } = useLg();
  const map = {
    pending: "neutral", pickedup: "blue", intransit: "blue", outfordelivery: "purple",
    delivered: "green", exception: "red", failed: "red", return: "yellow",
  };
  return <Badge tone={map[state] || "neutral"} dot className="whitespace-nowrap">{t("t." + state)}</Badge>;
}
window.TrackBadge = TrackBadge;

// ── Channel badge (Shopify / YouCan / Landing / Manual) ──────────────
function ChannelBadge({ channel, size = "sm" }) {
  const c = D().CHANNELS[channel];
  if (!c) return null;
  const tones = {
    emerald: "text-emerald-700 bg-emerald-50 ring-emerald-200",
    violet: "text-violet-700 bg-violet-50 ring-violet-200",
    amber: "text-amber-700 bg-amber-50 ring-amber-200",
    slate: "text-stone-600 bg-stone-100 ring-stone-200",
    green: "text-green-700 bg-green-50 ring-green-200",
  };
  const pad = size === "sm" ? "text-[10px] px-1.5 py-0.5" : "text-[11px] px-2 py-0.5";
  return <span className={`inline-flex items-center font-medium rounded ring-1 ring-inset whitespace-nowrap ${pad} ${tones[c.tone]}`}>{c.label}</span>;
}
window.ChannelBadge = ChannelBadge;

// ── SLA meter — ring or bar, green→amber→red ─────────────────────────
function slaColor(pct) { return pct >= 0.66 ? "#10b981" : pct >= 0.33 ? "#f59e0b" : "#ef4444"; }

function SlaRing({ pct = 0.7, size = 44, stroke = 5, label, sub }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const col = slaColor(pct);
  return (
    <div className="inline-flex items-center gap-2.5">
      <svg width={size} height={size} className="-rotate-90 flex-shrink-0">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f0eeec" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={col} strokeWidth={stroke}
          strokeDasharray={c} strokeDashoffset={c * (1 - pct)} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset .5s cubic-bezier(.16,1,.3,1)" }} />
      </svg>
      {(label || sub) && (
        <div className="leading-tight">
          {label && <div className="text-[13px] font-semibold tabular-nums" style={{ color: col }}>{label}</div>}
          {sub && <div className="text-[11px] text-stone-500">{sub}</div>}
        </div>
      )}
    </div>
  );
}
window.SlaRing = SlaRing;

function SlaBar({ pct = 0.7, label, className = "" }) {
  const col = slaColor(pct);
  return (
    <div className={className}>
      <div className="h-1.5 rounded-full bg-stone-100 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${Math.max(4, pct * 100)}%`, background: col, transition: "width .5s cubic-bezier(.16,1,.3,1)" }} />
      </div>
      {label && <div className="mt-1 text-[11px] font-medium tabular-nums" style={{ color: col }}>{label}</div>}
    </div>
  );
}
window.SlaBar = SlaBar;

// SLA meter that adapts to the tweak (ring | bar)
function SlaMeter(props) {
  const variant = (window.__lgMeter || "ring");
  return variant === "bar"
    ? <SlaBar pct={props.pct} label={props.label} className="w-[120px]" />
    : <SlaRing {...props} />;
}
window.SlaMeter = SlaMeter;

// ── KPI card ─────────────────────────────────────────────────────────
function KpiCard({ icon: Icon, label, value, unit, trend, trendGood = "up", spark, tone = "stone", onClick }) {
  const trendUp = trend > 0;
  const good = trendGood === "up" ? trendUp : !trendUp;
  const tones = {
    stone: "text-stone-500 bg-stone-100", emerald: "text-emerald-600 bg-emerald-50",
    amber: "text-amber-600 bg-amber-50", rose: "text-rose-600 bg-rose-50",
    violet: "text-violet-600 bg-violet-50", cyan: "text-cyan-600 bg-cyan-50", brand: "text-[var(--accent-700)] bg-[var(--accent-50)]",
  };
  return (
    <div onClick={onClick}
      className={`bg-white rounded-xl ring-1 ring-stone-200/70 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] ${onClick ? "cursor-pointer hover:ring-stone-300 hover:shadow-[0_8px_24px_-8px_rgba(0,0,0,0.14)] hover:-translate-y-0.5 transition-all" : "transition-all"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {Icon && <span className={`w-7 h-7 rounded-lg flex items-center justify-center ${tones[tone]}`}><Icon width={15} height={15} /></span>}
          <span className="text-[12px] font-medium text-stone-500">{label}</span>
        </div>
        {trend != null && (
          <span className={`inline-flex items-center gap-0.5 text-[11px] font-semibold tabular-nums ${good ? "text-emerald-600" : "text-rose-600"}`}>
            {trendUp ? <I.ArrowUp width={11} height={11} /> : <I.ArrowDown width={11} height={11} />}
            {Math.abs(trend)}%
          </span>
        )}
      </div>
      <div className="mt-2.5 flex items-end justify-between gap-2">
        <div className="text-[26px] leading-none font-semibold text-stone-900 tracking-[-0.01em] tabular-nums">
          <CountUp value={value} />{unit && <span className="text-[13px] font-medium text-stone-400 ms-1">{unit}</span>}
        </div>
        {spark && <Sparkline data={spark} width={64} height={26} />}
      </div>
    </div>
  );
}
window.KpiCard = KpiCard;

// ── Section card ─────────────────────────────────────────────────────
function Panel({ title, sub, right, children, className = "", bodyClass = "p-4" }) {
  return (
    <section className={`bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden ${className}`}>
      {(title || right) && (
        <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-stone-100">
          <div className="min-w-0">
            {title && <h3 className="text-[13.5px] font-semibold text-stone-900 truncate">{title}</h3>}
            {sub && <p className="text-[11.5px] text-stone-500 mt-0.5 truncate">{sub}</p>}
          </div>
          {right && <div className="flex-shrink-0 whitespace-nowrap">{right}</div>}
        </header>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  );
}
window.Panel = Panel;

// ── Performance widget (coaching tone) ───────────────────────────────
function PerfWidget({ person, compact = false }) {
  const { t } = useLg();
  const tone = (window.__lgPerfTone || "coaching"); // coaching | neutral
  const remaining = person.target - person.picks;
  const pct = Math.min(1, person.picks / person.target);
  const median = 31;
  const aboveMedian = person.picks - median;
  return (
    <div className={`bg-gradient-to-br from-[var(--accent-50)] to-white rounded-xl ring-1 ring-[var(--accent-200)]/50 p-4 ${compact ? "" : "p-5"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <Avatar name={D().byId(person.id)?.name} size={compact ? 32 : 38} />
          <div className="leading-tight">
            <div className="text-[13px] font-semibold text-stone-900">{D().byId(person.id)?.short}</div>
            <div className="text-[11px] text-stone-500">{t("c.rank")} #{person.rank} {t("c.of")} 6</div>
          </div>
        </div>
        {tone === "coaching" && (
          <Badge tone="brand" dot>{remaining > 0 ? `${remaining} ${t("pf.toGo")}` : "🎯 " + t("c.target")}</Badge>
        )}
      </div>
      <div className="grid grid-cols-3 gap-3 mb-3">
        <Stat label={t("pf.completed")} value={person.picks} />
        <Stat label={t("pf.avgTime")} value={person.avg} />
        <Stat label={t("pk.hitrate")} value={person.sla + "%"} />
      </div>
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[11px] font-medium text-stone-500 tabular-nums">{person.picks} / {person.target}</span>
          {tone === "coaching"
            ? <span className="text-[11px] font-semibold text-emerald-600">{aboveMedian > 0 ? `+${aboveMedian} ${t("pf.vsTeam")}` : t("pf.almostThere")}</span>
            : <span className="text-[11px] text-stone-400 tabular-nums">{Math.round(pct * 100)}%</span>}
        </div>
        <div className="h-2 rounded-full bg-white ring-1 ring-[var(--accent-200)]/50 overflow-hidden">
          <div className="h-full rounded-full bg-[var(--accent-500)]" style={{ width: `${pct * 100}%`, transition: "width .6s cubic-bezier(.16,1,.3,1)" }} />
        </div>
      </div>
    </div>
  );
}
window.PerfWidget = PerfWidget;

function Stat({ label, value }) {
  return (
    <div>
      <div className="text-[16px] font-semibold text-stone-900 tabular-nums leading-none">{value}</div>
      <div className="text-[10.5px] text-stone-500 mt-1 leading-tight">{label}</div>
    </div>
  );
}
window.LgStat = Stat;

// ── Alert toast (severity colored) ───────────────────────────────────
const SEV = {
  red:     { ring: "ring-rose-200",    bar: "bg-rose-500",    ic: "text-rose-500",    icon: I.AlertCircle },
  orange:  { ring: "ring-orange-200",  bar: "bg-orange-500",  ic: "text-orange-500",  icon: I.AlertCircle },
  yellow:  { ring: "ring-amber-200",   bar: "bg-amber-500",   ic: "text-amber-500",   icon: I.Info },
  insight: { ring: "ring-violet-200",  bar: "bg-violet-500",  ic: "text-violet-500",  icon: I.Sparkles },
};
function AlertRow({ item, onAction, onDismiss }) {
  const s = SEV[item.sev] || SEV.yellow;
  const Icon = s.icon;
  return (
    <div className={`relative bg-white rounded-lg ring-1 ${s.ring} p-3 ps-3.5 overflow-hidden`}>
      <span className={`absolute inset-y-0 start-0 w-1 ${s.bar}`} />
      <div className="flex items-start gap-2.5">
        <Icon width={16} height={16} className={`mt-0.5 flex-shrink-0 ${s.ic}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[12.5px] font-semibold text-stone-900 truncate flex-1 min-w-0">{item.title}</span>
            <span className="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{item.t}</span>
          </div>
          <p className="text-[12px] text-stone-600 mt-0.5 leading-snug text-pretty">{item.body}</p>
          {item.action && (
            <button onClick={onAction} className="mt-2 inline-flex items-center gap-1 text-[11.5px] font-semibold text-[var(--accent-700)] hover:text-[var(--accent-800)]">
              {item.action} <I.ArrowRight width={11} height={11} />
            </button>
          )}
        </div>
        {onDismiss && <IconButton icon={I.X} size={22} onClick={onDismiss} />}
      </div>
    </div>
  );
}
window.AlertRow = AlertRow;

// ── Phone frame (handheld scanner look) ──────────────────────────────
function PhoneFrame({ children, label }) {
  const { dir } = useLg();
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: 390, height: 800 }}>
        {/* device */}
        <div className="absolute inset-0 rounded-[44px] bg-stone-900 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.45),0_0_0_2px_rgba(0,0,0,0.6)] p-[10px]">
          <div className="relative w-full h-full rounded-[36px] overflow-hidden bg-stone-50" dir={dir}>
            {/* status bar */}
            <div className="absolute top-0 inset-x-0 h-11 z-20 flex items-end justify-between px-6 pb-1.5 text-[12px] font-semibold text-stone-900 pointer-events-none">
              <span className="tabular-nums">9:41</span>
              <div className="absolute left-1/2 -translate-x-1/2 top-2 w-[110px] h-[26px] bg-stone-900 rounded-full" />
              <span className="flex items-center gap-1">
                <I.Globe width={13} height={13} /><span className="tabular-nums">100%</span>
              </span>
            </div>
            <div className="absolute inset-0 pt-11 overflow-y-auto overscroll-contain" style={{ scrollbarWidth: "none" }}>
              {children}
            </div>
          </div>
        </div>
      </div>
      {label && <div className="text-[11px] font-medium text-stone-400">{label}</div>}
    </div>
  );
}
window.PhoneFrame = PhoneFrame;

// ── Scan input (big barcode field, success/error states) ─────────────
function ScanInput({ placeholder, onScan, state = "idle" }) {
  const ring = state === "ok" ? "ring-emerald-400 bg-emerald-50" : state === "err" ? "ring-rose-400 bg-rose-50" : "ring-stone-300 bg-white";
  return (
    <button onClick={onScan}
      className={`w-full flex items-center gap-3 px-4 h-16 rounded-2xl ring-2 ${ring} transition-all active:scale-[0.99]`}>
      <span className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${state === "ok" ? "bg-emerald-500 text-white" : state === "err" ? "bg-rose-500 text-white" : "bg-stone-900 text-white"}`}>
        {state === "ok" ? <I.Check width={20} height={20} /> : state === "err" ? <I.X width={20} height={20} /> : <I.Search width={18} height={18} />}
      </span>
      <span className="text-[15px] font-medium text-stone-500 text-start flex-1">{placeholder}</span>
      <span className="text-[10px] font-mono text-stone-400 uppercase tracking-wide">tap</span>
    </button>
  );
}
window.ScanInput = ScanInput;

// ── Empty state ──────────────────────────────────────────────────────
function EmptyState({ icon: Icon = I.CheckCircle, title, sub }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      <div className="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-500 flex items-center justify-center mb-3">
        <Icon width={26} height={26} />
      </div>
      <h3 className="text-[15px] font-semibold text-stone-900">{title}</h3>
      {sub && <p className="text-[12.5px] text-stone-500 mt-1 max-w-[260px]">{sub}</p>}
    </div>
  );
}
window.EmptyState = EmptyState;

// ── Mini bar (load capacity) ─────────────────────────────────────────
function CapacityBar({ load, capacity }) {
  const pct = Math.min(1, load / capacity);
  const col = pct >= 0.9 ? "bg-rose-500" : pct >= 0.66 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div className="h-1.5 rounded-full bg-stone-100 overflow-hidden">
      <div className={`h-full rounded-full ${col}`} style={{ width: `${pct * 100}%`, transition: "width .4s ease" }} />
    </div>
  );
}
window.CapacityBar = CapacityBar;
