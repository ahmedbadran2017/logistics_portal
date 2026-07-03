/* global React, I, Avatar, Dropdown, MenuItem, IconButton, Badge, Button, Kbd */
const { useState, useEffect } = React;

// ─────────────────────────────────────────────────────────────────────
// PORTAL SHELL — role-aware. Desktop roles get the sidebar; the Picker
// runs mobile-first inside a device frame.
// ─────────────────────────────────────────────────────────────────────

const ROLES = [
  { id: "manager",    person: "Sara Benali",        device: "desktop", icon: I.Dashboard, home: "cockpit" },
  { id: "dispatcher", person: "Anass Mouakkal",      device: "desktop", icon: I.Layers,    home: "assign" },
  { id: "picker",     person: "Marouane El Messaoudi", device: "mobile", icon: I.Box,     home: "queue" },
  { id: "packer",     person: "Reda ZAARI",         device: "desktop", icon: I.Tag,       home: "label" },
  { id: "returns",    person: "Nadia Berrada",      device: "desktop", icon: I.Return,    home: "returns" },
];
window.LG_ROLES = ROLES;

const ROLE_NAV = {
  manager: [
    { sec: "nav.overview", items: [["cockpit","nav.cockpit",I.Dashboard],["andon","nav.andon",I.TrendUp],["sla","nav.sla",I.Shield],["alerts","nav.alerts",I.Bell]] },
    { sec: "nav.fulfillment", items: [["orders","nav.orders",I.Orders],["waves","nav.waves",I.Layers],["picklists","nav.picklists",I.Box],["pack","nav.pack",I.Tag],["shipments","nav.shipments",I.File],["routes","nav.routes",I.Globe],["tracking","nav.tracking",I.Globe],["exceptions","nav.exceptions",I.AlertCircle],["returns","nav.returns",I.Return],["cod","nav.cod",I.Cash],["carriers","nav.carriers",I.Send]] },
    { sec: "nav.inventoryGrp", items: [["warehouse","wh.title",I.Building],["stock","nav.stock",I.Inventory],["reports","nav.reports",I.File]] },
    { sec: "nav.team", items: [["team","nav.team",I.Users],["roster","nav.roster",I.Calendar],["bonus","bn.nav",I.Zap],["settings","nav.settings",I.Sliders]] },
  ],
  dispatcher: [
    { sec: "nav.operations", items: [["assign","nav.assign",I.Layers],["orders","nav.orders",I.Orders],["picklists","nav.picklists",I.Box]] },
    { sec: "nav.inventoryGrp", items: [["warehouse","wh.title",I.Building],["stock","nav.stock",I.Inventory]] },
    { sec: "nav.me", items: [["tracking","nav.tracking",I.Globe],["performance","nav.performance",I.TrendUp]] },
  ],
  packer: [
    { sec: "nav.operations", items: [["label","nav.label",I.Tag],["manifest","nav.manifest",I.File],["shipments","nav.shipments",I.Send],["carriers","nav.carriers",I.Globe]] },
    { sec: "nav.me", items: [["performance","nav.performance",I.TrendUp]] },
  ],
  returns: [
    { sec: "nav.operations", items: [["returns","nav.returns",I.Return],["tracking","nav.tracking",I.Globe]] },
    { sec: "nav.me", items: [["performance","nav.performance",I.TrendUp]] },
  ],
  picker: [
    { sec: "nav.operations", items: [["queue","nav.queue",I.Box],["performance","nav.performance",I.TrendUp]] },
  ],
};
window.LG_ROLE_NAV = ROLE_NAV;

// ── Language switcher (EN / FR / AR — AR flips to RTL) ────────────────
function LangSwitcher({ compact = false }) {
  const { lang, setLang } = window.useLg();
  const opts = [["en", "EN"], ["fr", "FR"], ["ar", "ع"]];
  return (
    <div className={`inline-flex items-center ${compact ? "gap-0.5 p-0.5" : "gap-0.5 p-0.5"} bg-stone-100/80 rounded-lg`}>
      {opts.map(([v, l]) => (
        <button key={v} onClick={() => setLang(v)}
          className={`min-w-[26px] h-[24px] px-1.5 text-[11.5px] font-semibold rounded-md transition-all ${lang === v ? "bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]" : "text-stone-500 hover:text-stone-800"}`}>
          {l}
        </button>
      ))}
    </div>
  );
}
window.LangSwitcher = LangSwitcher;

// ── Live clock (real-time feel) ──────────────────────────────────────
function LiveClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const id = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(id); }, []);
  const hh = String(now.getHours()).padStart(2, "0"), mm = String(now.getMinutes()).padStart(2, "0"), ss = String(now.getSeconds()).padStart(2, "0");
  return (
    <div className="hidden md:inline-flex items-center gap-1.5 text-[11.5px] font-medium text-stone-500 tabular-nums">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />Live {hh}:{mm}:{ss}
    </div>
  );
}
window.LiveClock = LiveClock;

// ── Justyol logo lockup (official wordmark) ──────────────────────────
function JustyolLogo({ tag = true }) {
  return (
    <div className="flex items-center gap-2 min-w-0">
      <img src="logistics/justyol-logo.png" alt="Justyol" className="block flex-shrink-0" style={{ height: 16 }} />
      {tag && <>
        <span className="h-3.5 w-px bg-stone-200 flex-shrink-0" />
        <span className="text-[9.5px] font-semibold text-stone-400 tracking-[0.14em] uppercase">Logistics</span>
      </>}
    </div>
  );
}
window.JustyolLogo = JustyolLogo;

// ── Role switcher (the prototype "view as" affordance) ───────────────
function RoleSwitcher({ role, onRole }) {
  const { t } = window.useLg();
  const cur = ROLES.find((r) => r.id === role);
  return (
    <Dropdown align="left" trigger={
      <button className="flex items-center gap-2 ps-1.5 pe-2 py-1.5 rounded-lg hover:bg-stone-100 transition-colors">
        <Avatar name={cur.person} size={24} />
        <div className="text-start leading-tight">
          <div className="text-[12px] font-semibold text-stone-900">{t("role." + role)}</div>
          <div className="text-[10px] text-stone-500 truncate max-w-[120px]">{cur.person}</div>
        </div>
        <I.ChevronDown width={13} height={13} className="text-stone-400" />
      </button>
    }>
      {(close) => (
        <div className="w-[232px]">
          <div className="px-3 pt-2 pb-1.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">View as role</div>
          {ROLES.map((r) => {
            const Icon = r.icon;
            return (
              <button key={r.id} onClick={() => { onRole(r.id); close(); }}
                className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 mx-1 rounded-md text-start ${r.id === role ? "bg-stone-100" : "hover:bg-stone-50"}`}>
                <span className={`w-7 h-7 rounded-lg flex items-center justify-center ${r.id === role ? "bg-white text-[var(--accent-700)] ring-1 ring-stone-200" : "bg-stone-100 text-stone-500"}`}>
                  <Icon width={14} height={14} />
                </span>
                <div className="min-w-0 flex-1 leading-tight">
                  <div className="text-[12.5px] font-medium text-stone-900">{t("role." + r.id)}</div>
                  <div className="text-[10.5px] text-stone-500 truncate">{r.person}</div>
                </div>
                <span className="text-[9.5px] font-mono uppercase text-stone-400">{r.device === "mobile" ? "📱" : "🖥"}</span>
              </button>
            );
          })}
        </div>
      )}
    </Dropdown>
  );
}
window.RoleSwitcher = RoleSwitcher;

// ── Desktop shell ────────────────────────────────────────────────────
function DesktopShell({ role, page, onNav, onRole, onBell, unread, onOpenCmd, children }) {
  const { t } = window.useLg();
  const nav = ROLE_NAV[role] || [];
  const cur = ROLES.find((r) => r.id === role);
  return (
    <div className="h-screen flex overflow-hidden bg-stone-50/60">
      {/* Sidebar */}
      <aside className="w-[236px] bg-white border-e border-stone-200/70 flex flex-col flex-shrink-0">
        <div className="px-3 pt-3 pb-2">
          <div className="w-full flex items-center px-2 py-1.5 rounded-lg">
            <JustyolLogo sub={window.LG_DATA.WAREHOUSE} />
          </div>
        </div>
        <div className="px-3 pb-3">
          <button onClick={onOpenCmd} className="w-full flex items-center gap-2 px-2.5 py-1.5 text-[12.5px] text-stone-500 bg-stone-50/80 hover:bg-stone-100 rounded-lg transition-colors">
            <I.Search width={13} height={13} />
            <span className="flex-1 text-start">{t("c.search")}</span>
            <Kbd>⌘K</Kbd>
          </button>
        </div>
        <nav className="flex-1 px-2 overflow-y-auto pb-3">
          {nav.map((group, gi) => (
            <div key={gi} className={gi > 0 ? "mt-4" : ""}>
              <div className="px-3 mb-1 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">{t(group.sec)}</div>
              <div className="space-y-px">
                {group.items.map(([key, label, Icon]) => {
                  const active = page === key;
                  return (
                    <a key={key} onClick={() => onNav(key)}
                      className={`flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium cursor-pointer group transition-colors ${active ? "bg-stone-100 text-stone-900" : "text-stone-600 hover:bg-stone-100/70 hover:text-stone-900"}`}>
                      <Icon width={16} height={16} className={active ? "text-stone-700" : "text-stone-400 group-hover:text-stone-600"} />
                      <span className="flex-1">{t(label)}</span>
                    </a>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
        {/* role card */}
        <div className="p-2 border-t border-stone-100">
          <RoleSwitcher role={role} onRole={onRole} />
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-[52px] bg-white/80 backdrop-blur-sm border-b border-stone-200/70 flex items-center px-5 gap-3 flex-shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <Badge tone="brand" dot>{t("role." + role)}</Badge>
            <span className="text-[13px] font-medium text-stone-900 truncate">{t("role." + role + ".home")}</span>
          </div>
          <div className="flex-1" />
          <LiveClock />
          <LangSwitcher />
          <button onClick={onBell} className="relative w-8 h-8 rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-900 flex items-center justify-center">
            <I.Bell width={16} height={16} />
            {unread > 0 && <span className="absolute top-1 end-1 min-w-[15px] h-[15px] px-1 rounded-full bg-[var(--accent-600)] text-white text-[9px] font-bold flex items-center justify-center ring-2 ring-white tabular-nums">{unread}</span>}
          </button>
        </header>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
window.DesktopShell = DesktopShell;
