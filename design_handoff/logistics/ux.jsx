/* global React, I, Badge, Avatar, Button, IconButton, StageBadge, ChannelBadge */
const { useState, useEffect, useRef, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// COMMAND PALETTE (⌘K) — global jump-to search
// ─────────────────────────────────────────────────────────────────────
const CMD_PAGES = [
  ["cockpit", "Cockpit", I.Dashboard], ["sla", "SLA board", I.Shield], ["orders", "Orders", I.Orders],
  ["picklists", "Pick Lists", I.Box], ["shipments", "Shipments", I.File], ["tracking", "Tracking", I.Globe],
  ["returns", "Returns", I.Return], ["carriers", "Carriers", I.Send], ["stock", "Inventory", I.Inventory],
  ["restocking", "Restocking", I.Upload], ["analysis", "Stock Analysis", I.TrendUp], ["team", "Team", I.Users],
  ["bonus", "Bonus & incentives", I.Zap], ["settings", "Settings", I.Sliders],
];

function CommandPalette({ open, onClose, onGo, onOrder }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const inputRef = useRef(null);
  useEffect(() => { if (open) { setQ(""); setSel(0); setTimeout(() => inputRef.current?.focus(), 30); } }, [open]);

  const groups = useMemo(() => {
    const ql = q.trim().toLowerCase();
    const pages = CMD_PAGES.filter(([k, l]) => !ql || l.toLowerCase().includes(ql)).map(([k, l, Ic]) => ({ type: "page", k, label: l, icon: Ic, sub: t("cmd.pages") }));
    let orders = [], pls = [], shs = [], people = [];
    if (ql) {
      orders = D.ORDERS.filter((o) => `${o.no} ${o.customer} ${o.awb || ""}`.toLowerCase().includes(ql)).slice(0, 6)
        .map((o) => ({ type: "order", k: o.no, label: o.no, sub: o.customer, o }));
      pls = D.PICKLISTS.filter((p) => `${p.no} ${D.byId(p.picker).name}`.toLowerCase().includes(ql)).slice(0, 4)
        .map((p) => ({ type: "pl", k: p.no, label: p.no, sub: D.byId(p.picker).short, icon: I.Box }));
      shs = D.SHIPMENTS.filter((s) => s.no.toLowerCase().includes(ql)).slice(0, 3).map((s) => ({ type: "sh", k: s.no, label: s.no, sub: `${s.parcels} ${t("c.parcels")}`, icon: I.File }));
      people = D.TEAM_MEMBERS.filter((m) => D.byId(m.id).name.toLowerCase().includes(ql)).slice(0, 4)
        .map((m) => ({ type: "person", k: m.id, label: D.byId(m.id).name, sub: t("role." + m.role), m }));
    }
    return ql ? [...orders, ...people, ...pls, ...shs, ...pages.slice(0, 4)] : pages;
  }, [q]);

  useEffect(() => { setSel(0); }, [q]);
  if (!open) return null;

  function choose(item) {
    if (!item) return;
    if (item.type === "page") onGo(item.k);
    else if (item.type === "order") onOrder(item.k);
    else if (item.type === "pl") onGo("picklists");
    else if (item.type === "sh") onGo("shipments");
    else if (item.type === "person") onGo("team");
    onClose();
  }
  function onKey(e) {
    if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(groups.length - 1, s + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(0, s - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); choose(groups[sel]); }
    else if (e.key === "Escape") onClose();
  }

  const icons = { order: I.Orders, person: null };
  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[12vh] px-4" role="dialog" aria-modal="true" aria-label="Command palette">
      <div className="absolute inset-0 bg-stone-900/30 backdrop-blur-[2px] animate-fade-in" onClick={onClose} />
      <div className="relative w-full max-w-[560px] bg-white rounded-2xl shadow-[0_24px_80px_-12px_rgba(0,0,0,0.35)] overflow-hidden animate-[cmdkIn_.2s_cubic-bezier(.16,1,.3,1)]">
        <div className="flex items-center gap-2.5 px-4 border-b border-stone-100">
          <I.Search width={16} height={16} className="text-stone-400 flex-shrink-0" />
          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKey} placeholder={t("cmd.placeholder")}
            className="flex-1 h-12 text-[14px] text-stone-900 outline-none bg-transparent" />
          <kbd className="text-[10px] text-stone-400 bg-stone-50 ring-1 ring-stone-200 rounded px-1.5 py-0.5">Esc</kbd>
        </div>
        <div className="max-h-[50vh] overflow-y-auto py-2">
          {groups.length === 0 && <div className="px-4 py-8 text-center text-[12.5px] text-stone-400">{t("cmd.noResults")}</div>}
          {groups.map((item, i) => {
            const active = i === sel;
            const Icon = item.icon || icons[item.type] || I.ArrowRight;
            return (
              <button key={item.type + item.k} onMouseEnter={() => setSel(i)} onClick={() => choose(item)}
                className={`w-full flex items-center gap-3 px-4 py-2 text-start ${active ? "bg-[var(--accent-50)]/60" : ""}`}>
                {item.type === "person" ? <Avatar name={item.label} size={26} />
                  : <span className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${active ? "bg-white text-[var(--accent-700)] ring-1 ring-stone-200" : "bg-stone-100 text-stone-400"}`}><Icon width={14} height={14} /></span>}
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-medium text-stone-900 truncate">{item.label}</div>
                  <div className="text-[11px] text-stone-500 truncate">{item.sub}</div>
                </div>
                {item.type === "order" && <StageBadge stage={item.o.stage} size="sm" />}
                {active && <kbd className="text-[10px] text-stone-400 bg-white ring-1 ring-stone-200 rounded px-1 flex-shrink-0">↵</kbd>}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
window.CommandPalette = CommandPalette;

// ─────────────────────────────────────────────────────────────────────
// CONFIRM DIALOG
// ─────────────────────────────────────────────────────────────────────
function ConfirmDialog({ state, onClose }) {
  const { t } = window.useLg();
  useEffect(() => {
    if (!state) return;
    function k(e) { if (e.key === "Escape") onClose(); }
    document.addEventListener("keydown", k);
    return () => document.removeEventListener("keydown", k);
  }, [state]);
  if (!state) return null;
  const danger = state.danger;
  return (
    <div className="fixed inset-0 z-[210] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={state.title}>
      <div className="absolute inset-0 bg-stone-900/35 backdrop-blur-[2px] animate-fade-in" onClick={onClose} />
      <div className="relative w-full max-w-[400px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] p-5 animate-scale-in">
        <div className="flex items-start gap-3">
          <span className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${danger ? "bg-rose-50 text-rose-500" : "bg-amber-50 text-amber-500"}`}><I.AlertCircle width={20} height={20} /></span>
          <div className="min-w-0">
            <h3 className="text-[15px] font-semibold text-stone-900">{state.title}</h3>
            <p className="text-[12.5px] text-stone-600 mt-1 text-pretty">{state.body}</p>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 mt-5">
          <Button variant="ghost" size="md" onClick={onClose}>{t("c.cancel")}</Button>
          <Button variant={danger ? "danger" : "brand"} size="md" icon={I.Check} onClick={() => { state.onConfirm?.(); onClose(); }}>{state.confirmLabel || t("c.confirm")}</Button>
        </div>
      </div>
    </div>
  );
}
window.ConfirmDialog = ConfirmDialog;

// ─────────────────────────────────────────────────────────────────────
// OFFLINE BANNER (floor wifi) — shows when connection tweak = offline
// ─────────────────────────────────────────────────────────────────────
function OfflineBanner({ queued = 0 }) {
  const { t } = window.useLg();
  return (
    <div className="fixed top-0 inset-x-0 z-[180] flex items-center justify-center gap-2 h-8 bg-amber-500 text-white text-[12px] font-medium animate-[toastIn_.3s_ease]">
      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
      {t("c.offline")}{queued > 0 ? ` · ${queued} ${t("c.queued")}` : ""}
    </div>
  );
}
window.OfflineBanner = OfflineBanner;

// ─────────────────────────────────────────────────────────────────────
// NOTIFICATIONS PAGE — severity-grouped alert center
// ─────────────────────────────────────────────────────────────────────
const SEV_GROUP = { red: "critical", orange: "warning", yellow: "warning", insight: "info" };
function NotificationsPage({ onOpenOrder }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [filter, setFilter] = useState("all");
  const [read, setRead] = useState(() => new Set());
  const items = D.AUDIT.map((a, i) => ({ ...a, _id: i })).filter((a) => filter === "all" || SEV_GROUP[a.sev] === filter);
  const unread = D.AUDIT.length - read.size;
  const counts = {
    critical: D.AUDIT.filter((a) => SEV_GROUP[a.sev] === "critical").length,
    warning: D.AUDIT.filter((a) => SEV_GROUP[a.sev] === "warning").length,
    info: D.AUDIT.filter((a) => SEV_GROUP[a.sev] === "info").length,
  };

  return (
    <div className="max-w-[860px] mx-auto px-6 py-6 animate-fade-in">
      <window.PageHead title={t("al.title")} sub={t("al.sub")}>
        <Button variant="secondary" size="md" icon={I.CheckCircle} onClick={() => setRead(new Set(D.AUDIT.map((_, i) => i)))}>{t("al.markRead")}</Button>
      </window.PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <window.KpiCard icon={I.Bell} tone="stone" label={t("al.unread")} value={unread} />
        <window.KpiCard icon={I.AlertCircle} tone="rose" label={t("al.critical")} value={counts.critical} />
        <window.KpiCard icon={I.AlertCircle} tone="amber" label={t("al.warning")} value={counts.warning} />
        <window.KpiCard icon={I.Sparkles} tone="violet" label={t("al.info")} value={counts.info} />
      </div>

      <div className="flex items-center gap-1.5 mb-3">
        {[["all", t("al.all")], ["critical", t("al.critical")], ["warning", t("al.warning")], ["info", t("al.info")]].map(([k, l]) => (
          <button key={k} onClick={() => setFilter(k)} className={`px-3 h-8 text-[12.5px] font-medium rounded-lg ring-1 transition-colors ${filter === k ? "bg-stone-900 text-white ring-stone-900" : "bg-white text-stone-600 ring-stone-200 hover:ring-stone-300"}`}>{l}</button>
        ))}
      </div>

      {items.length === 0 ? (
        <window.EmptyState title={t("al.allRead")} />
      ) : (
        <div className="space-y-2.5">
          {items.map((a) => (
            <div key={a._id} className={`relative transition-opacity ${read.has(a._id) ? "opacity-55" : ""}`}>
              {!read.has(a._id) && <span className="absolute -start-2.5 top-4 w-1.5 h-1.5 rounded-full bg-[var(--accent-600)]" />}
              <AlertRow item={a} onAction={() => a.order && onOpenOrder?.(a.order)} onDismiss={() => setRead((s) => new Set([...s, a._id]))} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
window.NotificationsPage = NotificationsPage;

// ─────────────────────────────────────────────────────────────────────
// SHARED: ActivityFeed (audit trail + note composer) · AttachPanel
// ─────────────────────────────────────────────────────────────────────
function ActivityFeed({ events }) {
  const { t } = window.useLg();
  const [notes, setNotes] = useState([]);
  const [draft, setDraft] = useState("");
  const base = (events || []).filter((e) => e.on !== false);
  function post() {
    const txt = draft.trim(); if (!txt) return;
    const now = new Date();
    setNotes((n) => [{ who: t("od.you"), act: txt, at: `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}`, note: true }, ...n]);
    setDraft("");
  }
  const feed = [...notes, ...[...base].reverse()];
  return (
    <Panel title={t("od.activity")} sub={t("od.activitySub")} bodyClass="p-3">
      <div className="flex items-start gap-2 mb-3">
        <Avatar name="Supervisor" size={26} />
        <div className="flex-1 min-w-0">
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") post(); }}
            placeholder={t("od.addNote")} rows={2}
            className="w-full px-3 py-2 text-[12.5px] bg-stone-50 rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 focus:bg-white outline-none resize-none" />
          <div className="flex justify-end mt-1.5"><Button variant="brand" size="sm" icon={I.ArrowRight} disabled={!draft.trim()} onClick={post}>{t("od.post")}</Button></div>
        </div>
      </div>
      <div className="space-y-0.5 border-t border-stone-100 pt-2">
        {feed.map((e, i) => (
          <div key={i} className="flex items-start gap-2.5 px-1.5 py-1.5 rounded-lg hover:bg-stone-50">
            <Avatar name={e.who} size={22} />
            <div className="min-w-0 flex-1">
              {e.note
                ? <div className="text-[12.5px] text-stone-800 bg-amber-50 ring-1 ring-amber-200/60 rounded-lg px-2.5 py-1.5 text-pretty">{e.act}</div>
                : <div className={`text-[12px] ${e.bad ? "text-rose-700 font-medium" : "text-stone-800"}`}>{e.act}</div>}
              <div className="text-[10.5px] text-stone-400 mt-0.5">{e.who}</div>
            </div>
            <span className="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{e.at}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
window.ActivityFeed = ActivityFeed;

function AttachPanel({ stageReady = true, files }) {
  const { t } = window.useLg();
  const list = (files || ["scan_sheet.jpg", "pick_note.pdf"]).filter(() => stageReady);
  return (
    <Panel title={t("od.attachments")} sub={t("od.attachSub")} bodyClass="p-3">
      {list.length > 0 && (
        <div className="grid grid-cols-2 gap-2 mb-2">
          {list.map((name, i) => (
            <div key={i} className="rounded-lg ring-1 ring-stone-200 overflow-hidden">
              <div className="h-16 flex items-center justify-center" style={{ backgroundImage: "repeating-linear-gradient(45deg, #f5f5f4 0 6px, #ececeb 6px 12px)" }}>
                {name.endsWith(".pdf") ? <I.File width={18} height={18} className="text-stone-400" /> : <I.Box width={18} height={18} className="text-stone-400" />}
              </div>
              <div className="px-2 py-1.5 flex items-center gap-1"><span className="text-[10.5px] text-stone-600 truncate flex-1">{name}</span><I.Download width={11} height={11} className="text-stone-400 flex-shrink-0" /></div>
            </div>
          ))}
        </div>
      )}
      <button className="w-full flex items-center justify-center gap-2 h-16 rounded-lg ring-1 ring-dashed ring-stone-300 hover:ring-[var(--accent-400)] hover:bg-[var(--accent-50)]/30 text-[12px] font-medium text-stone-500 transition-all">
        <I.Upload width={15} height={15} />{t("od.dropFiles")}
      </button>
    </Panel>
  );
}
window.AttachPanel = AttachPanel;
