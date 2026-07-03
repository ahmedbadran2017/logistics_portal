/* global React */
const { useState, useEffect, useRef, useMemo, useCallback } = React;

// ─────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM — v2
// Notion-warm neutrals, Stripe-level polish, one accent.
// Everything here is shared across the module.
// ─────────────────────────────────────────────────────────────────────

// ── Icons: Lucide-style, stroke 1.75 for a softer Notion-ish feel ────
const mkIcon = (d) => (p) => (
  <svg {...p} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">{d}</svg>
);

const I = {
  Search: mkIcon(<><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></>),
  X: mkIcon(<><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>),
  Check: mkIcon(<polyline points="20 6 9 17 4 12"/>),
  Chevron: mkIcon(<polyline points="9 18 15 12 9 6"/>),
  ChevronDown: mkIcon(<polyline points="6 9 12 15 18 9"/>),
  ChevronUp: mkIcon(<polyline points="18 15 12 9 6 15"/>),
  Back: mkIcon(<polyline points="15 18 9 12 15 6"/>),
  Plus: mkIcon(<><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></>),
  Filter: mkIcon(<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>),
  Dashboard: mkIcon(<><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/></>),
  Users: mkIcon(<><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></>),
  Orders: mkIcon(<><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></>),
  Cash: mkIcon(<><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></>),
  Box: mkIcon(<><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></>),
  Inventory: mkIcon(<><path d="M20 12V22H4V12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/></>),
  Return: mkIcon(<><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></>),
  Star: mkIcon(<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>),
  UserPlus: mkIcon(<><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></>),
  Chat: mkIcon(<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>),
  Bell: mkIcon(<><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></>),
  External: mkIcon(<><path d="M10 6H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"/><polyline points="14 4 20 4 20 10"/><line x1="10" y1="14" x2="20" y2="4"/></>),
  Upload: mkIcon(<><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></>),
  Sort: mkIcon(<path d="M3 6h18M6 12h12M10 18h4"/>),
  More: mkIcon(<><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></>),
  Download: mkIcon(<><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></>),
  Phone: mkIcon(<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>),
  Mail: mkIcon(<><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></>),
  Globe: mkIcon(<><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></>),
  Pin: mkIcon(<><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></>),
  File: mkIcon(<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></>),
  Shield: mkIcon(<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>),
  Sliders: mkIcon(<><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></>),
  Edit: mkIcon(<><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></>),
  Trash: mkIcon(<><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></>),
  Copy: mkIcon(<><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></>),
  Eye: mkIcon(<><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></>),
  ArrowRight: mkIcon(<><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></>),
  ArrowUp: mkIcon(<><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></>),
  ArrowDown: mkIcon(<><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></>),
  Clock: mkIcon(<><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></>),
  CheckCircle: mkIcon(<><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></>),
  AlertCircle: mkIcon(<><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></>),
  Info: mkIcon(<><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></>),
  Zap: mkIcon(<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>),
  Command: mkIcon(<path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"/>),
  Keyboard: mkIcon(<><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10"/></>),
  Enter: mkIcon(<><polyline points="9 10 4 15 9 20"/><path d="M20 4v7a4 4 0 0 1-4 4H4"/></>),
  SidebarLeft: mkIcon(<><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></>),
  Bookmark: mkIcon(<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>),
  Calendar: mkIcon(<><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></>),
  Tag: mkIcon(<><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></>),
  Layers: mkIcon(<><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></>),
  TrendUp: mkIcon(<><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></>),
  TrendDown: mkIcon(<><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></>),
  Dot: mkIcon(<circle cx="12" cy="12" r="4"/>),
  Send: mkIcon(<><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></>),
  Pause: mkIcon(<><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></>),
  Sparkles: mkIcon(<><path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6z"/><path d="M19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8z"/><path d="M5 15l.5 1.5L7 17l-1.5.5L5 19l-.5-1.5L3 17l1.5-.5z"/></>),
  Building: mkIcon(<><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h.01M9 12h.01M9 15h.01M15 9h.01M15 12h.01M15 15h.01M12 21v-4"/></>),
  Wallet: mkIcon(<><path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4z"/></>),
};
window.I = I;

// ── Keyboard key glyph (⌘K style) ────────────────────────────────────
function Kbd({ children, className = "" }) {
  return (
    <kbd className={`inline-flex items-center justify-center min-w-[20px] h-[20px] px-1.5 text-[10.5px] font-medium text-stone-500 bg-stone-50 border border-stone-200/80 rounded-md shadow-[0_1px_0_rgba(0,0,0,0.04)] font-sans ${className}`}>
      {children}
    </kbd>
  );
}
window.Kbd = Kbd;

// ── Badge ────────────────────────────────────────────────────────────
function Badge({ tone = "neutral", dot = false, soft = true, children, className = "" }) {
  const tones = {
    neutral: "text-stone-700 bg-stone-100/80 ring-stone-200",
    green:   "text-emerald-700 bg-emerald-50 ring-emerald-200/70",
    yellow:  "text-amber-700 bg-amber-50 ring-amber-200/80",
    red:     "text-rose-700 bg-rose-50 ring-rose-200/70",
    blue:    "text-sky-700 bg-sky-50 ring-sky-200/70",
    purple:  "text-violet-700 bg-violet-50 ring-violet-200/70",
    brand:   "text-[var(--accent-700)] bg-[var(--accent-50)] ring-[var(--accent-200)]/60",
  };
  const dots = {
    neutral: "bg-stone-400", green: "bg-emerald-500", yellow: "bg-amber-500",
    red: "bg-rose-500", blue: "bg-sky-500", purple: "bg-violet-500", brand: "bg-[var(--accent-600)]",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 text-[11.5px] font-medium px-2 py-0.5 rounded-md ring-1 ring-inset ${tones[tone]} ${className}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dots[tone]}`} />}
      {children}
    </span>
  );
}
window.Badge = Badge;

function StatusBadge({ status }) {
  const map = { "Active": "green", "Pending Approval": "yellow", "Suspended": "red" };
  return <Badge tone={map[status] || "neutral"} dot>{status}</Badge>;
}
window.StatusBadge = StatusBadge;

// ── Avatar (gradient-seeded, Notion-warm palette) ────────────────────
function Avatar({ name, size = 32, className = "" }) {
  // Deterministic hue from name — warm palette bias.
  const hue = useMemo(() => {
    let h = 0;
    for (let i = 0; i < (name || "").length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffff;
    return h % 360;
  }, [name]);
  const bg = `linear-gradient(135deg, hsl(${hue} 60% 88%) 0%, hsl(${(hue + 40) % 360} 55% 78%) 100%)`;
  const fg = `hsl(${hue} 40% 28%)`;
  return (
    <div className={`rounded-lg flex items-center justify-center font-semibold flex-shrink-0 ring-1 ring-black/[0.04] ${className}`}
      style={{ width: size, height: size, fontSize: size * 0.4, background: bg, color: fg }}>
      {window.getInitial(name)}
    </div>
  );
}
window.Avatar = Avatar;

// ── Sparkline ────────────────────────────────────────────────────────
function Sparkline({ data, width = 72, height = 24, stroke = "var(--accent-600)" }) {
  if (!data?.length || data.every((v) => v === 0)) {
    return <svg width={width} height={height}><line x1="0" y1={height/2} x2={width} y2={height/2} stroke="#e7e5e4" strokeWidth="1.25" strokeDasharray="2 2" /></svg>;
  }
  const max = Math.max(...data), min = Math.min(...data);
  const range = Math.max(1, max - min);
  const step = width / (data.length - 1);
  const pts = data.map((v, i) => [i * step, height - ((v - min) / range) * (height - 4) - 2]);
  const d = pts.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = d + ` L ${width} ${height} L 0 ${height} Z`;
  const gid = "sg-" + Math.random().toString(36).slice(2, 8);
  return (
    <svg width={width} height={height}>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.22" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path d={d} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length-1][0]} cy={pts[pts.length-1][1]} r="2" fill={stroke} />
    </svg>
  );
}
window.Sparkline = Sparkline;

// ── LineChart (detail pages) ─────────────────────────────────────────
function LineChart({ data, labels, height = 180, stroke = "var(--accent-600)" }) {
  const ref = useRef(null);
  const [w, setW] = useState(600);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((entries) => setW(entries[0].contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  const max = Math.max(...data, 1);
  const step = w / Math.max(1, data.length - 1);
  const pts = data.map((v, i) => [i * step, height - (v / max) * (height - 30) - 15]);
  const d = pts.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = d + ` L ${w} ${height - 10} L 0 ${height - 10} Z`;
  return (
    <div ref={ref} className="w-full">
      <svg width={w} height={height}>
        {[0, 0.25, 0.5, 0.75, 1].map((f, i) => (
          <line key={i} x1="0" x2={w} y1={10 + f * (height - 30)} y2={10 + f * (height - 30)} stroke="#f5f5f4" strokeWidth="1" strokeDasharray={i === 4 ? "" : "2 4"} />
        ))}
        <defs>
          <linearGradient id="lc-grad-v2" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.14" />
            <stop offset="100%" stopColor={stroke} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#lc-grad-v2)" />
        <path d={d} fill="none" stroke={stroke} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
        {pts.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={i === pts.length - 1 ? 3.5 : 0} fill="#fff" stroke={stroke} strokeWidth="1.75" />
        ))}
        {labels?.map((lbl, i) => (
          <text key={i} x={i * step} y={height - 2} fontSize="10.5" fill="#a8a29e" fontWeight="500" textAnchor={i === 0 ? "start" : i === labels.length - 1 ? "end" : "middle"}>{lbl}</text>
        ))}
      </svg>
    </div>
  );
}
window.LineChart = LineChart;

// ── Dropdown ─────────────────────────────────────────────────────────
function Dropdown({ trigger, children, align = "right", className = "" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    function onClick(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    function onEsc(e) { if (e.key === "Escape") setOpen(false); }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onEsc);
    return () => { document.removeEventListener("mousedown", onClick); document.removeEventListener("keydown", onEsc); };
  }, []);
  return (
    <div ref={ref} className={`relative ${className}`}>
      <div onClick={() => setOpen(!open)}>{trigger}</div>
      {open && (
        <div className={`absolute z-40 mt-1.5 min-w-[200px] bg-white rounded-xl shadow-[0_4px_32px_-8px_rgba(0,0,0,0.16),0_0_0_1px_rgba(0,0,0,0.05)] overflow-hidden py-1 animate-menu ${align === "right" ? "right-0" : "left-0"}`}>
          {typeof children === "function" ? children(() => setOpen(false)) : children}
        </div>
      )}
    </div>
  );
}
window.Dropdown = Dropdown;

function MenuItem({ icon: Icon, label, kbd, onClick, tone = "default", className = "" }) {
  const tones = { default: "text-stone-700 hover:bg-stone-50", danger: "text-rose-600 hover:bg-rose-50" };
  return (
    <button onClick={onClick} className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 text-[13px] font-medium rounded-md mx-1 ${tones[tone]} ${className}`}>
      {Icon && <Icon width={14} height={14} className="text-stone-400 flex-shrink-0" />}
      <span className="flex-1 text-left">{label}</span>
      {kbd && <Kbd className="!bg-transparent !border-transparent !text-stone-400">{kbd}</Kbd>}
    </button>
  );
}
window.MenuItem = MenuItem;

// ── Toast ────────────────────────────────────────────────────────────
function Toast({ toast }) {
  if (!toast) return null;
  const tones = {
    success: { cls: "bg-white text-stone-800", icon: <I.CheckCircle width={16} height={16} className="text-emerald-500" /> },
    error:   { cls: "bg-white text-stone-800", icon: <I.AlertCircle width={16} height={16} className="text-rose-500" /> },
    info:    { cls: "bg-white text-stone-800", icon: <I.Info width={16} height={16} className="text-sky-500" /> },
  };
  const t = tones[toast.type] || tones.info;
  return (
    <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl shadow-[0_8px_40px_-8px_rgba(0,0,0,0.24),0_0_0_1px_rgba(0,0,0,0.05)] text-sm font-medium max-w-md animate-toast-in ${t.cls}`}>
      {t.icon}
      {toast.text}
      {toast.action && (
        <button onClick={toast.action.onClick} className="ml-2 text-[var(--accent-700)] hover:text-[var(--accent-800)] font-semibold">
          {toast.action.label}
        </button>
      )}
    </div>
  );
}
window.Toast = Toast;

// ── IconButton (ghost square button, 32px) ───────────────────────────
function IconButton({ icon: Icon, onClick, title, className = "", active = false, size = 32 }) {
  return (
    <button onClick={onClick} title={title}
      className={`rounded-md flex items-center justify-center transition-colors flex-shrink-0 ${active ? "bg-stone-100 text-stone-900" : "text-stone-500 hover:bg-stone-100 hover:text-stone-900"} ${className}`}
      style={{ width: size, height: size }}>
      <Icon width={Math.round(size * 0.5)} height={Math.round(size * 0.5)} />
    </button>
  );
}
window.IconButton = IconButton;

// ── Button ───────────────────────────────────────────────────────────
function Button({ variant = "secondary", size = "md", icon: Icon, iconRight: IconRight, kbd, children, className = "", ...rest }) {
  const sizes = {
    sm: "h-7 px-2.5 text-[12.5px] gap-1.5",
    md: "h-8 px-3 text-[13px] gap-1.5",
    lg: "h-9 px-3.5 text-sm gap-2",
  };
  const variants = {
    primary:   "bg-stone-900 text-white hover:bg-stone-800 shadow-[0_1px_2px_rgba(0,0,0,0.08),inset_0_1px_0_rgba(255,255,255,0.12)]",
    secondary: "bg-white text-stone-700 border border-stone-200 hover:bg-stone-50 hover:border-stone-300 shadow-[0_1px_2px_rgba(0,0,0,0.03)]",
    ghost:     "text-stone-600 hover:bg-stone-100 hover:text-stone-900",
    brand:     "bg-[var(--accent-600)] text-white hover:bg-[var(--accent-700)] shadow-[0_1px_2px_rgba(0,0,0,0.08),inset_0_1px_0_rgba(255,255,255,0.15)]",
    danger:    "bg-rose-600 text-white hover:bg-rose-700",
    success:   "bg-emerald-600 text-white hover:bg-emerald-700",
  };
  return (
    <button className={`inline-flex items-center justify-center font-medium rounded-lg transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none ${sizes[size]} ${variants[variant]} ${className}`} {...rest}>
      {Icon && <Icon width={14} height={14} />}
      {children}
      {IconRight && <IconRight width={14} height={14} />}
      {kbd && <Kbd className="ml-1 !bg-white/10 !border-white/20 !text-white/80">{kbd}</Kbd>}
    </button>
  );
}
window.Button = Button;

// ── useHotkeys — global keyboard shortcut registry ───────────────────
const hotkeyRegistry = new Set();
let hotkeysAttached = false;
function attachHotkeys() {
  if (hotkeysAttached) return;
  hotkeysAttached = true;
  document.addEventListener("keydown", (e) => {
    // Skip when typing — unless the shortcut uses a modifier.
    const inField = ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) || e.target.isContentEditable;
    const hasMod = e.metaKey || e.ctrlKey;
    for (const fn of hotkeyRegistry) {
      try { fn(e, { inField, hasMod }); } catch {}
    }
  });
}
function useHotkeys(handler, deps = []) {
  useEffect(() => {
    attachHotkeys();
    hotkeyRegistry.add(handler);
    return () => hotkeyRegistry.delete(handler);
    // eslint-disable-next-line
  }, deps);
}
window.useHotkeys = useHotkeys;

// ── Tooltip (super lightweight) ──────────────────────────────────────
function Tip({ label, kbd, children, side = "bottom" }) {
  const [show, setShow] = useState(false);
  const t = useRef(null);
  return (
    <div className="relative inline-flex"
      onMouseEnter={() => { t.current = setTimeout(() => setShow(true), 400); }}
      onMouseLeave={() => { clearTimeout(t.current); setShow(false); }}>
      {children}
      {show && (
        <div className={`absolute z-50 pointer-events-none flex items-center gap-1.5 px-2 py-1 text-[11.5px] font-medium text-white bg-stone-900 rounded-md whitespace-nowrap animate-tip ${side === "bottom" ? "top-full mt-1.5 left-1/2 -translate-x-1/2" : "bottom-full mb-1.5 left-1/2 -translate-x-1/2"}`}>
          {label}
          {kbd && <Kbd className="!bg-white/10 !border-white/10 !text-white/80">{kbd}</Kbd>}
        </div>
      )}
    </div>
  );
}
window.Tip = Tip;

Object.assign(window, { I, Badge, StatusBadge, Sparkline, LineChart, Avatar, Dropdown, MenuItem, Toast, IconButton, Button, Kbd, Tip, useHotkeys });
