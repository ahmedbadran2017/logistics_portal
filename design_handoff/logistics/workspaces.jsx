/* global React, I, Badge, Avatar, Sparkline, Button, IconButton, Panel, KpiCard, StageBadge, SlaBadge, ChannelBadge, TrackBadge, SlaRing */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// Shared: page header + lightweight modal
// ─────────────────────────────────────────────────────────────────────
function PageHead({ title, sub, children }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
      <div>
        <h1 className="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{title}</h1>
        {sub && <p className="text-[12.5px] text-stone-500 mt-0.5">{sub}</p>}
      </div>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  );
}
window.PageHead = PageHead;

function Modal({ title, sub, onClose, children, footer, dir }) {
  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-stone-900/30 backdrop-blur-[1px] animate-fade-in" onClick={onClose} />
      <div className="relative w-full max-w-[480px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] animate-scale-in overflow-hidden" dir={dir}>
        <header className="flex items-center justify-between px-5 py-3.5 border-b border-stone-100">
          <div>
            <div className="text-[14.5px] font-semibold text-stone-900">{title}</div>
            {sub && <div className="text-[12px] text-stone-500 mt-0.5">{sub}</div>}
          </div>
          <IconButton icon={I.X} onClick={onClose} />
        </header>
        <div className="p-5 max-h-[60vh] overflow-y-auto">{children}</div>
        {footer && <footer className="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-stone-100 bg-stone-50/60">{footer}</footer>}
      </div>
    </div>
  );
}
window.LgModal = Modal;

const FilterChip = ({ active, onClick, children, tone }) => (
  <button onClick={onClick}
    className={`px-2.5 h-7 text-[12px] font-medium rounded-lg ring-1 transition-colors whitespace-nowrap ${active ? "bg-stone-900 text-white ring-stone-900" : "bg-white text-stone-600 ring-stone-200 hover:ring-stone-300"}`}>
    {children}
  </button>
);

function SortTh({ k, sort, onSort, children, end }) {
  const active = sort.key === k;
  return (
    <button onClick={() => onSort(k)} className={`inline-flex items-center gap-1 hover:text-stone-700 ${end ? "flex-row-reverse" : ""} ${active ? "text-stone-700" : ""}`}>
      {children}
      <span className={`text-[8px] ${active ? "text-stone-500" : "text-stone-300"}`}>{active ? (sort.dir === "asc" ? "▲" : "▼") : "▲"}</span>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────
// ORDERS — full workspace table with search + filters
// ─────────────────────────────────────────────────────────────────────
function OrdersList() {
  const { t, openOrderPage } = window.useLg();
  const D = window.LG_DATA;
  const [q, setQ] = useState("");
  const [stage, setStage] = useState(() => (window.__ordersInit && window.__ordersInit.stage) || "all");
  const [sla, setSla] = useState(() => (window.__ordersInit && window.__ordersInit.sla) || "all");
  const [sel, setSel] = useState(() => new Set());
  const [sort, setSort] = useState({ key: "age", dir: "asc" });
  if (window.__ordersInit) window.__ordersInit = null;
  function toggleSel(no, e) { e.stopPropagation(); setSel((s) => { const n = new Set(s); n.has(no) ? n.delete(no) : n.add(no); return n; }); }
  // deterministic placed-time per order (today, by hash) + age in minutes
  function placed(o) { const n = parseInt((o.no.match(/\d+/) || [10])[0]); const ageMin = (n * 37) % 540 + (o.stage === "pending" ? 4 : 30); const d = new Date(); d.setHours(7, 0, 0, 0); d.setMinutes(d.getMinutes() + ((n * 53) % 600)); return { hhmm: `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`, ageMin }; }
  function setSortKey(k) { setSort((s) => ({ key: k, dir: s.key === k && s.dir === "asc" ? "desc" : "asc" })); }

  const rows = useMemo(() => {
    const filtered = D.ORDERS.filter((o) => {
      if (stage !== "all" && o.stage !== stage) return false;
      if (sla !== "all" && o.sla !== sla) return false;
      if (q && !(`${o.no} ${o.customer} ${o.awb || ""}`.toLowerCase().includes(q.toLowerCase()))) return false;
      return true;
    }).map((o) => ({ ...o, _p: placed(o) }));
    const dir = sort.dir === "asc" ? 1 : -1;
    const val = { age: (o) => o._p.ageMin, value: (o) => o.total, customer: (o) => o.customer, order: (o) => o.no };
    const f = val[sort.key] || val.age;
    return filtered.sort((a, b) => (f(a) > f(b) ? 1 : f(a) < f(b) ? -1 : 0) * dir);
  }, [q, stage, sla, sort]);

  const stages = ["all", "pending", "picking", "picked", "label", "shipped", "transit", "exception", "delivered", "returned"];
  const total = rows.reduce((a, o) => a + o.total, 0);

  return (
    <div className="max-w-[1320px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("nav.orders")} sub={`${t("od.confirmedOnly")} · ${D.ORDERS.length} ${t("c.orders")} · ${D.WAREHOUSE}`}>
        <Button variant="secondary" size="md" icon={I.Download}>Export</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Orders} tone="stone" label={t("c.orders")} value={D.ORDERS.length} />
        <KpiCard icon={I.Clock} tone="amber" label={t("ck.atrisk")} value={D.ORDERS.filter(o=>o.sla==="atrisk").length} />
        <KpiCard icon={I.AlertCircle} tone="rose" label={t("ck.breaches")} value={D.ORDERS.filter(o=>o.sla==="breached").length} />
        <KpiCard icon={I.Cash} tone="emerald" label="Open value" value={window.fmtMAD(total)} unit="MAD" />
      </div>

      {/* search + filters */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <I.Search width={14} height={14} className="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("c.search")}
            className="w-full h-9 ps-9 pe-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none" />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {["all", "ontrack", "atrisk", "breached"].map((s) => (
            <FilterChip key={s} active={sla === s} onClick={() => setSla(s)}>{s === "all" ? t("c.sla") + ": All" : t("sla." + s)}</FilterChip>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-1.5 mb-3 overflow-x-auto pb-1">
        {stages.map((s) => (
          <FilterChip key={s} active={stage === s} onClick={() => setStage(s)}>{s === "all" ? "All stages" : t("s." + s)}</FilterChip>
        ))}
      </div>

      <Panel bodyClass="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px]">
            <thead>
              <tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th className="ps-4 pe-1 py-2.5 w-8"><span className={`w-4 h-4 rounded ring-1 inline-flex items-center justify-center cursor-pointer ${sel.size === rows.length && rows.length ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300"}`} onClick={() => setSel(sel.size === rows.length ? new Set() : new Set(rows.map(r=>r.no)))}>{sel.size === rows.length && rows.length > 0 && <I.Check width={11} height={11} />}</span></th>
                <th className="text-start px-4 py-2.5"><SortTh k="order" sort={sort} onSort={setSortKey}>{t("c.order")}</SortTh></th>
                <th className="text-start px-4 py-2.5"><SortTh k="customer" sort={sort} onSort={setSortKey}>{t("c.customer")}</SortTh></th>
                <th className="text-start px-4 py-2.5 hidden md:table-cell">{t("c.channel")}</th>
                <th className="text-start px-4 py-2.5 hidden lg:table-cell">{t("c.zone")}</th>
                <th className="text-start px-4 py-2.5">{t("c.picker")}</th>
                <th className="text-start px-4 py-2.5">{t("c.stage")}</th>
                <th className="text-start px-4 py-2.5">{t("c.sla")}</th>
                <th className="text-start px-4 py-2.5 hidden sm:table-cell"><SortTh k="age" sort={sort} onSort={setSortKey}>{t("od.placed")}</SortTh></th>
                <th className="text-end px-4 py-2.5"><SortTh k="value" sort={sort} onSort={setSortKey} end>{t("c.value")}</SortTh></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {rows.map((o) => (
                <tr key={o.no} onClick={() => openOrderPage(o.no)} className={`cursor-pointer transition-colors ${sel.has(o.no) ? "bg-[var(--accent-50)]/50" : "hover:bg-stone-50"}`}>
                  <td className="ps-4 pe-1 py-2.5"><span onClick={(e) => toggleSel(o.no, e)} className={`w-4 h-4 rounded ring-1 inline-flex items-center justify-center ${sel.has(o.no) ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300 hover:ring-stone-400"}`}>{sel.has(o.no) && <I.Check width={11} height={11} />}</span></td>
                  <td className="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900 whitespace-nowrap">{o.no}</td>
                  <td className="px-4 py-2.5 text-[12.5px] text-stone-800 truncate max-w-[150px]">{o.customer}</td>
                  <td className="px-4 py-2.5 hidden md:table-cell"><ChannelBadge channel={o.channel} /></td>
                  <td className="px-4 py-2.5 text-[11.5px] text-stone-500 hidden lg:table-cell whitespace-nowrap">{o.zone}</td>
                  <td className="px-4 py-2.5">{o.picker ? <div className="flex items-center gap-1.5"><Avatar name={D.byId(o.picker).name} size={20} /><span className="text-[11.5px] text-stone-600 hidden xl:inline">{D.byId(o.picker).short}</span></div> : <span className="text-[11.5px] text-stone-300">—</span>}</td>
                  <td className="px-4 py-2.5"><StageBadge stage={o.stage} size="sm" /></td>
                  <td className="px-4 py-2.5"><SlaBadge sla={o.sla} size="sm" /></td>
                  <td className="px-4 py-2.5 hidden sm:table-cell whitespace-nowrap"><span className="text-[12px] text-stone-600 tabular-nums">{o._p.hhmm}</span> <span className="text-[10.5px] text-stone-400">· {o._p.ageMin >= 60 ? `${Math.floor(o._p.ageMin/60)}h` : `${o._p.ageMin}m`}</span></td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums whitespace-nowrap">{window.fmtMAD(o.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length === 0 && <div className="text-center text-[12.5px] text-stone-400 py-12">No orders match these filters.</div>}
      </Panel>

      {sel.size > 0 && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-[120] flex items-center gap-2 bg-stone-900 text-white rounded-xl shadow-[0_12px_40px_-8px_rgba(0,0,0,0.4)] px-3 py-2 animate-[toastIn_.25s_ease]">
          <span className="text-[12.5px] font-medium ps-1">{sel.size} selected</span>
          <span className="w-px h-5 bg-white/20 mx-0.5" />
          <button className="flex items-center gap-1.5 px-2.5 h-8 text-[12.5px] font-medium rounded-lg hover:bg-white/10"><I.Layers width={14} height={14} />Assign</button>
          <button className="flex items-center gap-1.5 px-2.5 h-8 text-[12.5px] font-medium rounded-lg hover:bg-white/10"><I.Tag width={14} height={14} />Generate labels</button>
          <button className="flex items-center gap-1.5 px-2.5 h-8 text-[12.5px] font-medium rounded-lg hover:bg-white/10"><I.Download width={14} height={14} />Export</button>
          <button onClick={() => setSel(new Set())} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center"><I.X width={14} height={14} /></button>
        </div>
      )}
    </div>
  );
}
window.OrdersList = OrdersList;

// ─────────────────────────────────────────────────────────────────────
// PICK LISTS — list + Create Pick List
// ─────────────────────────────────────────────────────────────────────
const PL_STATUS = { draft: "neutral", open: "yellow", completed: "green", cancelled: "red" };
function PickLists({ onToast, dir }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [rows, setRows] = useState(() => D.PICKLISTS.map((p) => ({ ...p })));
  const [create, setCreate] = useState(false);
  const [detail, setDetail] = useState(null);
  const [autopilot, setAutopilot] = useState(false);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState({ key: "no", dir: "desc" });
  const [sel, setSel] = useState(() => new Set());
  function plSel(no, e) { e.stopPropagation(); setSel((s) => { const n = new Set(s); n.has(no) ? n.delete(no) : n.add(no); return n; }); }
  const plOrigin = (p) => p.origin || (["Zone cluster","Balanced","Batch SKU","Single-item blitz","Multi-line"].includes(p.item) ? "auto" : p.item === "Manual" ? "manual" : "auto");

  const open = rows.filter((p) => p.status === "open" || p.status === "draft").length;
  const completed = rows.filter((p) => p.status === "completed").length;
  const withErrors = rows.filter((p) => p.errors).length;
  const totalQty = rows.reduce((a, p) => a + p.qty, 0);
  const shown = rows.filter((p) => filter === "all" || p.status === filter || (filter === "errors" && p.errors))
    .slice().sort((a, b) => {
      const v = { no: (x) => x.no, qty: (x) => x.qty, items: (x) => x.items || 0, pct: (x) => x.pct }[sort.key] || ((x) => x.no);
      return (v(a) > v(b) ? 1 : v(a) < v(b) ? -1 : 0) * (sort.dir === "asc" ? 1 : -1);
    });
  function plSortKey(k) { setSort((s) => ({ key: k, dir: s.key === k && s.dir === "asc" ? "desc" : "asc" })); }

  if (detail) return <window.PickListDetail pl={detail} onClose={() => setDetail(null)} dir={dir} />;
  if (autopilot) return <window.AutopilotPage onBack={() => setAutopilot(false)} onToast={onToast} />;

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("nav.picklists")} sub={`${rows.length} pick lists today · ${D.WAREHOUSE}`}>
        <Button variant="brand" size="md" icon={I.Zap} onClick={() => setCreate(true)}>{t("ap.smart")} pick list</Button>
      </PageHead>

      <window.PickAutopilot onRun={() => { const gs = window.autoPickGroups("zone").groups.map((g, i) => ({ no: g.no, customer: g.kind === "Batch SKU" ? g.label : `${g.kind} · ${g.label}`, item: g.kind, bin: g.aisles > 1 ? "Multiple" : g.lines[0].bin, qty: g.units, items: g.items, status: "open", pct: 0, picker: D.TEAM.filter(p=>p.role==="picker")[i % 5].id, order: g.orders > 1 ? "combined" : g.lines[0].so })); setRows((rs) => [...gs, ...rs]); }} onToast={onToast} onOpen={() => setAutopilot(true)} />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Box} tone="amber" label="Open / draft" value={open} />
        <KpiCard icon={I.CheckCircle} tone="emerald" label="Completed" value={completed} />
        <KpiCard icon={I.Layers} tone="violet" label="Combined picks" value={rows.filter(p=>p.order==="combined").length} />
        <KpiCard icon={I.AlertCircle} tone={withErrors ? "rose" : "stone"} label="Pick errors" value={withErrors} />
      </div>

      <div className="flex items-center gap-1.5 mb-3 overflow-x-auto pb-1">
        {[["all","All"],["draft","Draft"],["open","Open"],["completed","Completed"],["cancelled","Cancelled"],["errors",`Errors·${withErrors}`]].map(([k,l]) => (
          <FilterChip key={k} active={filter === k} onClick={() => setFilter(k)}>{l}</FilterChip>
        ))}
      </div>

      <Panel bodyClass="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead>
              <tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th className="ps-4 pe-1 py-2.5 w-8"><span className={`w-4 h-4 rounded ring-1 inline-flex items-center justify-center cursor-pointer ${sel.size === shown.length && shown.length ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300"}`} onClick={() => setSel(sel.size === shown.length ? new Set() : new Set(shown.map(r=>r.no)))}>{sel.size === shown.length && shown.length > 0 && <I.Check width={11} height={11} />}</span></th>
                <th className="text-start px-4 py-2.5"><SortTh k="no" sort={sort} onSort={plSortKey}>Pick List</SortTh></th>
                <th className="text-start px-4 py-2.5">{t("c.picker")}</th>
                <th className="text-start px-4 py-2.5">Origin</th>
                <th className="text-start px-4 py-2.5">Type</th>
                <th className="text-end px-4 py-2.5 hidden sm:table-cell"><SortTh k="items" sort={sort} onSort={plSortKey} end>Items</SortTh></th>
                <th className="text-end px-4 py-2.5"><SortTh k="qty" sort={sort} onSort={plSortKey} end>{t("c.qty")}</SortTh></th>
                <th className="text-start px-4 py-2.5 w-[150px]"><SortTh k="pct" sort={sort} onSort={plSortKey}>Progress</SortTh></th>
                <th className="text-start px-4 py-2.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {shown.map((p) => (
                <tr key={p.no} onClick={() => setDetail(p)} className={`transition-colors cursor-pointer ${sel.has(p.no) ? "bg-[var(--accent-50)]/50" : "hover:bg-stone-50"}`}>
                  <td className="ps-4 pe-1 py-2.5"><span onClick={(e) => plSel(p.no, e)} className={`w-4 h-4 rounded ring-1 inline-flex items-center justify-center ${sel.has(p.no) ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300 hover:ring-stone-400"}`}>{sel.has(p.no) && <I.Check width={11} height={11} />}</span></td>
                  <td className="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900 whitespace-nowrap">{p.no}{p.errors && <I.AlertCircle width={12} height={12} className="text-rose-500 inline ms-1.5 -mt-0.5" />}</td>
                  <td className="px-4 py-2.5"><div className="flex items-center gap-1.5"><Avatar name={D.byId(p.picker).name} size={20} /><span className="text-[12px] text-stone-700">{D.byId(p.picker).short}</span></div></td>
                  <td className="px-4 py-2.5">{plOrigin(p) === "manual" ? <span className="inline-flex items-center gap-1 text-[10.5px] font-medium text-stone-500 bg-stone-100 rounded px-1.5 py-0.5 whitespace-nowrap"><I.Users width={9} height={9} />Manual</span> : <span className="inline-flex items-center gap-1 text-[10.5px] font-medium text-[var(--accent-700)] bg-[var(--accent-50)] rounded px-1.5 py-0.5 whitespace-nowrap"><I.Zap width={9} height={9} />Autopilot</span>}</td>
                  <td className="px-4 py-2.5 text-[12px] text-stone-600">{p.order === "combined" ? <Badge tone="purple" className="whitespace-nowrap">{t("dp.combined")}</Badge> : <span className="truncate">{p.customer}</span>}</td>
                  <td className="px-4 py-2.5 text-end text-[12px] text-stone-500 tabular-nums hidden sm:table-cell">{p.items ?? "—"}</td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{p.qty}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2"><div className="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className={`h-full rounded-full ${p.errors ? "bg-rose-500" : "bg-emerald-500"}`} style={{ width: `${p.pct}%` }} /></div><span className="text-[10.5px] text-stone-400 tabular-nums w-[28px]">{p.pct}%</span></div>
                  </td>
                  <td className="px-4 py-2.5">{p.errors ? <Badge tone="red" dot className="whitespace-nowrap">Short-pick</Badge> : <Badge tone={PL_STATUS[p.status]} dot>{p.status[0].toUpperCase()+p.status.slice(1)}</Badge>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {create && <window.SmartPickModal onClose={() => setCreate(false)} onToast={onToast} dir={dir} onGenerate={(gs) => setRows((rs) => [...gs, ...rs])} />}

      {sel.size > 0 && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-[120] flex items-center gap-2 bg-stone-900 text-white rounded-xl shadow-[0_12px_40px_-8px_rgba(0,0,0,0.4)] px-3 py-2 animate-[toastIn_.25s_ease]">
          <span className="text-[12.5px] font-medium ps-1">{sel.size} selected</span>
          <span className="w-px h-5 bg-white/20 mx-0.5" />
          <button onClick={() => { onToast?.({ type: "success", text: `${sel.size} pick lists re-assigned` }); setSel(new Set()); }} className="flex items-center gap-1.5 px-2.5 h-8 text-[12.5px] font-medium rounded-lg hover:bg-white/10"><I.Users width={14} height={14} />Assign</button>
          <button onClick={() => { onToast?.({ type: "success", text: `${sel.size} pick sheets printed` }); setSel(new Set()); }} className="flex items-center gap-1.5 px-2.5 h-8 text-[12.5px] font-medium rounded-lg hover:bg-white/10"><I.Download width={14} height={14} />Print</button>
          <button onClick={() => setSel(new Set())} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center"><I.X width={14} height={14} /></button>
        </div>
      )}
    </div>
  );
}
window.PickLists = PickLists;

function CreatePickList({ onClose, onToast, dir, addRow }) {
  const D = window.LG_DATA;
  const pickers = D.TEAM.filter((p) => p.role === "picker");
  const ready = D.ORDERS.filter((o) => o.stage === "pending");
  const [picker, setPicker] = useState(pickers[0].id);
  const [sel, setSel] = useState(new Set());

  function toggle(no) { setSel((s) => { const n = new Set(s); n.has(no) ? n.delete(no) : n.add(no); return n; }); }
  function submit() {
    const no = "PL-" + (51434 + Math.floor(Math.random() * 40));
    const combined = sel.size > 1;
    addRow({ no, customer: combined ? `Combined · ${sel.size} orders` : D.ORDERS.find(o=>sel.has(o.no))?.customer || "—", item: "—", bin: "Multiple", qty: sel.size, status: "open", pct: 0, picker, order: combined ? "combined" : [...sel][0] });
    onToast?.({ type: "success", text: `${no} created · ${D.byId(picker).short} · ${sel.size} order${sel.size>1?"s":""}` });
    onClose();
  }

  return (
    <Modal title="Create pick list" sub="Assign ready orders to a picker" onClose={onClose} dir={dir}
      footer={<>
        <Button variant="ghost" size="md" onClick={onClose}>Cancel</Button>
        <Button variant="brand" size="md" icon={I.Check} disabled={sel.size === 0} onClick={submit}>Create {sel.size > 1 ? `combined (${sel.size})` : sel.size === 1 ? "(1)" : ""}</Button>
      </>}>
      <div className="space-y-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">Picker</div>
          <div className="grid grid-cols-2 gap-1.5">
            {pickers.map((p) => (
              <button key={p.id} onClick={() => setPicker(p.id)}
                className={`flex items-center gap-2 px-2 py-1.5 rounded-lg ring-1 transition-all ${picker === p.id ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40" : "ring-stone-200 hover:ring-stone-300"}`}>
                <Avatar name={p.name} size={22} /><span className="text-[12px] font-medium text-stone-800 truncate">{p.short}</span>
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">Ready orders · {ready.length}</span>
            {sel.size > 1 && <Badge tone="purple">Combined pick · {sel.size}</Badge>}
          </div>
          <div className="space-y-1.5 max-h-[220px] overflow-y-auto">
            {ready.map((o) => {
              const on = sel.has(o.no);
              return (
                <button key={o.no} onClick={() => toggle(o.no)}
                  className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg ring-1 text-start transition-all ${on ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40" : "ring-stone-200 hover:ring-stone-300"}`}>
                  <span className={`w-4 h-4 rounded flex items-center justify-center ring-1 ${on ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300"}`}>{on && <I.Check width={11} height={11} />}</span>
                  <span className="font-mono text-[12px] font-semibold text-stone-900">{o.no}</span>
                  <span className="text-[12px] text-stone-600 flex-1 truncate">{o.customer}</span>
                  <span className="text-[11px] text-stone-400">{o.zone}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </Modal>
  );
}

// ─────────────────────────────────────────────────────────────────────
// SHIPMENTS — management + tracking + Create Shipment
// ─────────────────────────────────────────────────────────────────────
const SH_STATUS = { Draft: "neutral", Submitted: "blue", Booked: "purple", Completed: "green", Cancelled: "red" };
function Shipments({ onToast, dir }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [rows, setRows] = useState(() => D.SHIPMENTS.map((s) => ({ ...s })));
  const [create, setCreate] = useState(false);
  const [open, setOpen] = useState(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState({ key: "no", dir: "desc" });
  const [sel, setSel] = useState(() => new Set());
  function shSel(no, e) { e.stopPropagation(); setSel((s) => { const n = new Set(s); n.has(no) ? n.delete(no) : n.add(no); return n; }); }

  const todayP = rows[0].parcels;
  const inTransit = D.TRACK_COUNTS.intransit + D.TRACK_COUNTS.outfordelivery;

  if (open) {
    const sh = rows.find((s) => s.no === open);
    return <ShipmentDetail sh={sh} onClose={() => setOpen(null)} onToast={onToast} setRows={setRows} dir={dir} />;
  }

  const shown = rows.filter((s) => (filter === "all" || s.status === filter) && (!q || s.no.toLowerCase().includes(q.toLowerCase())))
    .slice().sort((a, b) => { const v = { no: (x) => x.no, parcels: (x) => x.parcels, value: (x) => x.value }[sort.key] || ((x) => x.no); return (v(a) > v(b) ? 1 : -1) * (sort.dir === "asc" ? 1 : -1); });
  const sk = (k) => setSort((s) => ({ key: k, dir: s.key === k && s.dir === "asc" ? "desc" : "asc" }));

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("nav.shipments")} sub={`${D.CARRIER} · ${D.WAREHOUSE}`}>
        <Button variant="secondary" size="md" icon={I.Globe}>{t("sh.trackAll")}</Button>
        <Button variant="brand" size="md" icon={I.Plus} onClick={() => setCreate(true)}>Create shipment</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.File} tone="stone" label="Today's parcels" value={todayP} />
        <KpiCard icon={I.Globe} tone="cyan" label={t("t.intransit")} value={inTransit} />
        <KpiCard icon={I.CheckCircle} tone="emerald" label="Delivered (yest.)" value={rows[1]?.delivered ?? 0} />
        <KpiCard icon={I.AlertCircle} tone="rose" label={t("ck.exceptions")} value={D.TRACK_COUNTS.exception + D.TRACK_COUNTS.failed} />
      </div>

      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="relative flex-1 min-w-[180px]">
          <I.Search width={14} height={14} className="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search shipment…" className="w-full h-9 ps-9 pe-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none" />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {[["all","All"],["Draft","Draft"],["Submitted","Submitted"],["Booked","Booked"],["Completed","Completed"]].map(([k,l]) => (
            <FilterChip key={k} active={filter === k} onClick={() => setFilter(k)}>{l}</FilterChip>
          ))}
        </div>
      </div>

      <Panel bodyClass="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead>
              <tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th className="ps-4 pe-1 py-2.5 w-8"><span className={`w-4 h-4 rounded ring-1 inline-flex items-center justify-center cursor-pointer ${sel.size === shown.length && shown.length ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300"}`} onClick={() => setSel(sel.size === shown.length ? new Set() : new Set(shown.map(r=>r.no)))}>{sel.size === shown.length && shown.length > 0 && <I.Check width={11} height={11} />}</span></th>
                <th className="text-start px-4 py-2.5"><SortTh k="no" sort={sort} onSort={sk}>Shipment</SortTh></th>
                <th className="text-start px-4 py-2.5">Date</th>
                <th className="text-start px-4 py-2.5 hidden lg:table-cell">{t("sh.masterAwb")}</th>
                <th className="text-end px-4 py-2.5"><SortTh k="parcels" sort={sort} onSort={sk} end>{t("c.parcels")}</SortTh></th>
                <th className="text-end px-4 py-2.5 hidden sm:table-cell"><SortTh k="value" sort={sort} onSort={sk} end>{t("c.value")}</SortTh></th>
                <th className="text-end px-4 py-2.5 hidden md:table-cell">Delivered</th>
                <th className="text-start px-4 py-2.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {shown.map((s) => (
                <tr key={s.no} onClick={() => setOpen(s.no)} className={`cursor-pointer transition-colors ${sel.has(s.no) ? "bg-[var(--accent-50)]/50" : "hover:bg-stone-50"}`}>
                  <td className="ps-4 pe-1 py-2.5"><span onClick={(e) => shSel(s.no, e)} className={`w-4 h-4 rounded ring-1 inline-flex items-center justify-center ${sel.has(s.no) ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300 hover:ring-stone-400"}`}>{sel.has(s.no) && <I.Check width={11} height={11} />}</span></td>
                  <td className="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900">{s.no}</td>
                  <td className="px-4 py-2.5 text-[12px] text-stone-600 whitespace-nowrap">{s.date}</td>
                  <td className="px-4 py-2.5 font-mono text-[11.5px] text-stone-500 hidden lg:table-cell">{s.awb}</td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{s.parcels}</td>
                  <td className="px-4 py-2.5 text-end text-[12px] text-stone-600 tabular-nums hidden sm:table-cell">{window.fmtMAD(s.value)}</td>
                  <td className="px-4 py-2.5 text-end text-[12px] tabular-nums hidden md:table-cell">{s.delivered ? <span className="text-emerald-600">{s.delivered}/{s.parcels}</span> : <span className="text-stone-300">—</span>}</td>
                  <td className="px-4 py-2.5"><Badge tone={SH_STATUS[s.status]} dot>{s.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {create && <CreateShipment onClose={() => setCreate(false)} onToast={onToast} dir={dir} addRow={(r) => setRows((rs) => [r, ...rs])} />}

      {sel.size > 0 && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-[120] flex items-center gap-2 bg-stone-900 text-white rounded-xl shadow-[0_12px_40px_-8px_rgba(0,0,0,0.4)] px-3 py-2 animate-[toastIn_.25s_ease]">
          <span className="text-[12.5px] font-medium ps-1">{sel.size} selected</span>
          <span className="w-px h-5 bg-white/20 mx-0.5" />
          <button onClick={() => { onToast?.({ type: "success", text: `${sel.size} manifests printed` }); setSel(new Set()); }} className="flex items-center gap-1.5 px-2.5 h-8 text-[12.5px] font-medium rounded-lg hover:bg-white/10"><I.Download width={14} height={14} />{t("sh.bulkPrint")}</button>
          <button onClick={() => setSel(new Set())} className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center"><I.X width={14} height={14} /></button>
        </div>
      )}
    </div>
  );
}
window.Shipments = Shipments;

// ── Full shipment page ───────────────────────────────────────────────
function ShipmentDetail({ sh, onClose, onToast, setRows, dir }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const pct = sh.parcels ? sh.delivered / sh.parcels : 0;
  const isDraft = sh.status === "Draft";
  const manifest = D.PARCELS.slice(0, 6);
  const [loaded, setLoaded] = useState(() => new Set(isDraft ? [] : manifest.map((p) => p.dn)));
  const [feedback, setFeedback] = useState("idle");
  const [mq, setMq] = useState("");
  const [excOnly, setExcOnly] = useState(false);
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const id = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(id); }, []);
  const cutoff = new Date(now); cutoff.setHours(14, 0, 0, 0);
  const diff = Math.floor((cutoff - now) / 1000); const past = diff < 0;
  const ch = Math.floor(Math.abs(diff) / 3600), cm = Math.floor((Math.abs(diff) % 3600) / 60), cs = Math.abs(diff) % 60;
  const shownManifest = manifest.filter((p) => (!excOnly || p.track === "exception" || p.track === "failed") && (!mq || `${p.dn} ${p.awb} ${p.customer}`.toLowerCase().includes(mq.toLowerCase())));
  const loadedCount = isDraft ? loaded.size + 0 : sh.parcels;
  const totalToLoad = manifest.length;
  const allLoaded = loaded.size >= totalToLoad;
  function scan() {
    const next = manifest.find((p) => !loaded.has(p.dn));
    if (!next) return;
    setLoaded((s) => new Set([...s, next.dn]));
    setFeedback("ok"); setTimeout(() => setFeedback("idle"), 600);
  }
  function closeHand() {
    setRows((rs) => rs.map((r) => r.no === sh.no ? { ...r, status: "Submitted" } : r));
    onToast?.({ type: "success", text: `${sh.no} closed · ${loaded.size} parcels handed to ${sh.carrier}` });
    onClose();
  }
  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onClose} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"><I.Back width={15} height={15} className="rtl:rotate-180" />{t("nav.shipments")}</button>

      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center"><I.File width={22} height={22} /></span>
            <div>
              <div className="flex items-center gap-2 flex-wrap"><h1 className="font-mono text-[19px] font-bold text-stone-900">{sh.no}</h1><Badge tone={SH_STATUS[sh.status]} dot>{sh.status}</Badge>{sh.exceptions > 0 && <Badge tone="red" dot className="whitespace-nowrap">{sh.exceptions} exc</Badge>}</div>
              <div className="text-[12.5px] text-stone-600 mt-1">{sh.carrier} · {sh.service} · {sh.date} · {sh.window}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {sh.status === "Draft"
              ? <Button variant="success" size="md" icon={I.CheckCircle} disabled={!allLoaded} onClick={closeHand}>{t("sh.closeHand")}</Button>
              : <Button variant="secondary" size="md" icon={I.Globe}>{t("sh.trackAll")}</Button>}
            <Button variant="secondary" size="md" icon={I.Download}>{t("c.print")}</Button>
            <Button variant="secondary" size="md" iconRight={I.External}>{t("c.openInErp")}</Button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
          <DetailStat label={t("c.parcels")} value={sh.parcels} />
          <DetailStat label={t("c.value")} value={window.fmtMAD(sh.value)} unit="MAD" />
          <DetailStat label={t("sh.weight")} value={sh.weight} unit="kg" />
          <DetailStat label={t("sh.pallets")} value={sh.pallets} />
          <DetailStat label={t("sh.incoterm")} value={sh.incoterm} />
        </div>
        {sh.delivered > 0 && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-[11px] mb-1"><span className="text-stone-500 tabular-nums">{sh.delivered}/{sh.parcels} delivered</span><span className="text-emerald-600 font-semibold tabular-nums">{Math.round(pct*100)}%</span></div>
            <div className="h-2 rounded-full bg-stone-100 overflow-hidden"><div className="h-full bg-emerald-500 rounded-full" style={{ width: `${pct*100}%` }} /></div>
          </div>
        )}
        {isDraft && (
          <div className={`mt-4 flex items-center gap-2 rounded-xl px-3 py-2 ring-1 ${past ? "bg-rose-50 ring-rose-200" : diff < 3600 ? "bg-amber-50 ring-amber-200" : "bg-stone-50 ring-stone-200"}`}>
            <I.Clock width={15} height={15} className={past ? "text-rose-500" : diff < 3600 ? "text-amber-500" : "text-stone-400"} />
            <span className="text-[12px] text-stone-600">{past ? t("sh.pastCutoff") : t("sh.cutoffIn")}</span>
            <span className={`text-[14px] font-bold tabular-nums ${past ? "text-rose-600" : diff < 3600 ? "text-amber-600" : "text-stone-900"}`}>{past ? "+" : ""}{String(ch).padStart(2,"0")}:{String(cm).padStart(2,"0")}:{String(cs).padStart(2,"0")}</span>
            <span className="text-[11px] text-stone-400 ms-auto">14:00 · {sh.carrier}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4">
        <Panel title={t("sh.manifest")} sub={`${sh.parcels} ${t("c.parcels")}`} right={isDraft ? <Badge tone={allLoaded ? "green" : "amber"} dot>{loaded.size}/{totalToLoad} {t("sh.loadedN")}</Badge> : <Badge tone="neutral">{D.CARRIER}</Badge>} bodyClass="p-0">
          {isDraft && (
            <div className="p-4 border-b border-stone-100">
              <button onClick={scan} disabled={allLoaded} className={`w-full flex items-center gap-3 px-4 h-14 rounded-2xl ring-2 transition-all active:scale-[0.99] ${feedback === "ok" ? "ring-emerald-400 bg-emerald-50" : allLoaded ? "ring-emerald-300 bg-emerald-50/50" : "ring-stone-300 bg-white hover:ring-stone-400"}`}>
                <span className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${feedback === "ok" || allLoaded ? "bg-emerald-500 text-white" : "bg-stone-900 text-white"}`}>{feedback === "ok" || allLoaded ? <I.Check width={20} height={20} /> : <I.Search width={18} height={18} />}</span>
                <span className="text-[14px] font-medium text-stone-600 text-start flex-1">{allLoaded ? t("sh.allLoaded") : t("sh.scanDn")}</span>
                <span className="text-[10px] font-mono text-stone-400 uppercase tracking-wide">{allLoaded ? "✓" : "scan"}</span>
              </button>
              {feedback === "ok" && <div className="text-center text-[12px] font-semibold text-emerald-600 mt-2 animate-fade-in">{t("sh.scanned")}</div>}
            </div>
          )}
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-stone-100">
            <div className="relative flex-1"><I.Search width={13} height={13} className="absolute start-2.5 top-1/2 -translate-y-1/2 text-stone-400" /><input value={mq} onChange={(e) => setMq(e.target.value)} placeholder={t("sh.searchParcel")} className="w-full h-8 ps-8 pe-3 text-[12px] bg-stone-50 rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none" /></div>
            <button onClick={() => setExcOnly(!excOnly)} className={`px-2.5 h-8 text-[11.5px] font-medium rounded-lg ring-1 whitespace-nowrap ${excOnly ? "bg-rose-500 text-white ring-rose-500" : "bg-white text-stone-600 ring-stone-200 hover:ring-stone-300"}`}>{t("sh.excOnly")}</button>
          </div>
          <div className="divide-y divide-stone-100 max-h-[420px] overflow-y-auto">
            {shownManifest.map((p) => {
              const isLoaded = loaded.has(p.dn);
              return (
              <div key={p.dn} className={`grid items-center gap-3 px-4 py-2.5 transition-colors ${isDraft ? "grid-cols-[20px_148px_1fr_96px_100px]" : "grid-cols-[148px_1fr_96px_100px]"} ${isDraft && !isLoaded ? "opacity-50" : ""} ${isLoaded && isDraft ? "bg-emerald-50/40" : ""}`}>
                {isDraft && <span className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${isLoaded ? "bg-emerald-500 text-white" : "ring-1 ring-stone-300"}`}>{isLoaded && <I.Check width={11} height={11} />}</span>}
                <span className="font-mono text-[11.5px] font-semibold text-stone-900">{p.dn}</span>
                <span className="text-[12px] text-stone-700 truncate">{p.customer}</span>
                <span className="font-mono text-[10.5px] text-stone-400 hidden sm:block text-end">{p.awb}</span>
                <div className="flex justify-end">{isDraft ? (isLoaded ? <Badge tone="green" dot>{t("sh.loaded")}</Badge> : <span className="text-[11px] text-stone-400 whitespace-nowrap">{t("sh.notLoaded")}</span>) : <window.TrackBadge state={p.track} />}</div>
              </div>
            ); })}
            <div className="px-4 py-2.5 text-center text-[11.5px] text-stone-400">+ {sh.parcels - manifest.length} more parcels</div>
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel title={t("sh.pickup") + " → " + t("sh.deliveryTo")} bodyClass="p-4 space-y-3">
            <div className="flex items-start gap-2.5"><span className="w-7 h-7 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center flex-shrink-0 mt-0.5"><I.Pin width={14} height={14} /></span><div><div className="text-[12.5px] font-medium text-stone-900">{sh.pickup}</div><div className="text-[11px] text-stone-500">{sh.pickupContact}</div></div></div>
            <div className="ms-3.5 h-4 w-px bg-stone-200" />
            <div className="flex items-start gap-2.5"><span className="w-7 h-7 rounded-lg bg-cyan-50 text-cyan-600 flex items-center justify-center flex-shrink-0 mt-0.5"><I.Globe width={14} height={14} /></span><div><div className="text-[12.5px] font-medium text-stone-900">{sh.deliveryTo}</div><div className="text-[11px] text-stone-500">{sh.window}</div></div></div>
          </Panel>
          <Panel title={t("sh.tracking")} bodyClass="p-4 space-y-1.5 text-[12px]">
            <Row3 k={t("sh.masterAwb")} v={sh.awb} />
            <Row3 k={t("sh.service")} v={sh.service} />
            <Row3 k={t("sh.shipType")} v={sh.shipType} />
          </Panel>
          {!isDraft && (
            <Panel title={t("sh.handoverProof")} bodyClass="p-3">
              <div className="flex items-center gap-2.5 rounded-lg bg-emerald-50/60 ring-1 ring-emerald-200/60 px-3 py-2 mb-2">
                <I.CheckCircle width={15} height={15} className="text-emerald-600 flex-shrink-0" />
                <span className="text-[12px] text-emerald-800 flex-1">{t("sh.proofDone")} · {sh.date} 14:05</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg ring-1 ring-stone-200 overflow-hidden"><div className="h-14 flex items-center justify-center" style={{ backgroundImage: "repeating-linear-gradient(45deg, #f5f5f4 0 6px, #ececeb 6px 12px)" }}><I.Edit width={16} height={16} className="text-stone-400" /></div><div className="px-2 py-1 text-[10px] text-stone-500">signature.png</div></div>
                <div className="rounded-lg ring-1 ring-stone-200 overflow-hidden"><div className="h-14 flex items-center justify-center" style={{ backgroundImage: "repeating-linear-gradient(45deg, #f5f5f4 0 6px, #ececeb 6px 12px)" }}><I.Box width={16} height={16} className="text-stone-400" /></div><div className="px-2 py-1 text-[10px] text-stone-500">truck_load.jpg</div></div>
              </div>
            </Panel>
          )}
          <window.ActivityFeed events={[
            { who: "Reda", act: "Shipment created · " + sh.parcels + " parcels", at: "13:40", on: true },
            { who: "Reda", act: "Closed & handed to " + sh.carrier, at: "14:05", on: sh.status !== "Draft" },
            { who: sh.carrier, act: "Booked · " + sh.awb, at: "14:20", on: sh.status === "Booked" || sh.status === "Completed" },
          ]} />
        </div>
      </div>
    </div>
  );
}
function Row3({ k, v }) { return <div className="flex items-center justify-between gap-2"><span className="text-stone-400">{k}</span><span className="font-mono font-medium text-stone-800 truncate">{v}</span></div>; }

function DetailStat({ label, value, unit }) {
  return (
    <div className="bg-stone-50 rounded-lg px-3 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">{label}</div>
      <div className="text-[15px] font-semibold text-stone-900 tabular-nums mt-0.5">{value}{unit && <span className="text-[10px] text-stone-400 ms-1">{unit}</span>}</div>
    </div>
  );
}

function CreateShipment({ onClose, onToast, dir, addRow }) {
  const D = window.LG_DATA;
  const ready = D.PARCELS.filter((p) => p.track === "pickedup" || p.track === "pending");
  const [carrier, setCarrier] = useState("Cathedis");
  const [sel, setSel] = useState(new Set(ready.map((p) => p.dn)));
  function toggle(dn) { setSel((s) => { const n = new Set(s); n.has(dn) ? n.delete(dn) : n.add(dn); return n; }); }
  function submit() {
    const no = "SH-000" + (180 + Math.floor(Math.random() * 9));
    const value = D.PARCELS.filter((p) => sel.has(p.dn)).reduce((a, p) => a + p.value, 0);
    addRow({ no, date: D.TODAY, parcels: sel.size, value, carrier, status: "Draft", window: "09:00 – 17:00", delivered: 0, exceptions: 0 });
    onToast?.({ type: "success", text: `${no} created · ${sel.size} parcels · ${carrier}` });
    onClose();
  }
  return (
    <Modal title="Create shipment" sub="Build a carrier handover from ready parcels" onClose={onClose} dir={dir}
      footer={<>
        <Button variant="ghost" size="md" onClick={onClose}>Cancel</Button>
        <Button variant="brand" size="md" icon={I.Check} disabled={sel.size === 0} onClick={submit}>Create ({sel.size})</Button>
      </>}>
      <div className="space-y-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{t_carrierLabel()}</div>
          <div className="flex gap-1.5">
            {D.CARRIERS.map((c) => (
              <button key={c.name} disabled={!c.active} onClick={() => setCarrier(c.name)}
                className={`px-3 h-8 text-[12.5px] font-medium rounded-lg ring-1 transition-all ${carrier === c.name ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40 text-stone-900" : c.active ? "ring-stone-200 text-stone-600 hover:ring-stone-300" : "ring-stone-100 text-stone-300 cursor-not-allowed"}`}>
                {c.name}{!c.active && " ·"}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">Ready parcels · {ready.length}</div>
          <div className="space-y-1.5 max-h-[240px] overflow-y-auto">
            {ready.map((p) => {
              const on = sel.has(p.dn);
              return (
                <button key={p.dn} onClick={() => toggle(p.dn)}
                  className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg ring-1 text-start transition-all ${on ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/40" : "ring-stone-200 hover:ring-stone-300"}`}>
                  <span className={`w-4 h-4 rounded flex items-center justify-center ring-1 ${on ? "bg-[var(--accent-600)] ring-[var(--accent-600)] text-white" : "ring-stone-300"}`}>{on && <I.Check width={11} height={11} />}</span>
                  <span className="font-mono text-[11.5px] font-semibold text-stone-900">{p.dn}</span>
                  <span className="text-[12px] text-stone-600 flex-1 truncate">{p.customer}</span>
                  <span className="font-mono text-[10.5px] text-stone-400">{p.awb}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </Modal>
  );
}
function t_carrierLabel() { return "Carrier"; }

// ─────────────────────────────────────────────────────────────────────
// CARRIERS — Cathedis live + others to configure
// ─────────────────────────────────────────────────────────────────────
function Carriers() {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const main = D.CARRIERS.find((c) => c.primary);
  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("nav.carriers")} sub="Shipping partners & live performance">
        <Button variant="secondary" size="md" icon={I.Plus}>Add carrier</Button>
      </PageHead>

      {/* primary carrier */}
      <Panel className="mb-4" bodyClass="p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-700 flex items-center justify-center text-white text-[15px] font-bold">{main.code}</div>
            <div>
              <div className="flex items-center gap-2 flex-wrap"><span className="text-[16px] font-semibold text-stone-900">{main.name}</span><Badge tone="green" dot className="whitespace-nowrap">Active · primary</Badge></div>
              <div className="text-[12px] text-stone-500 mt-0.5">{main.zones} · {main.awbActive} active AWBs</div>
            </div>
          </div>
          <div className="flex items-center gap-5">
            <SlaRing pct={main.deliveryRate/100} size={52} label={main.deliveryRate + "%"} sub="Delivery rate" />
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">
          <DetailStat label="Active AWBs" value={main.awbActive} />
          <DetailStat label="Delivery rate" value={main.deliveryRate} unit="%" />
          <DetailStat label="Exception rate" value={main.exceptionRate} unit="%" />
          <DetailStat label="Avg transit" value={main.avgTransit} />
        </div>
        {/* state breakdown */}
        <div className="mt-5">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">Live AWB states</div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
            {D.TRACK_STATES.map((s) => (
              <div key={s} className="bg-stone-50 rounded-lg p-2.5 text-center">
                <div className="text-[16px] font-semibold text-stone-900 tabular-nums leading-none">{D.TRACK_COUNTS[s] ?? 0}</div>
                <div className="text-[9.5px] text-stone-500 mt-1 leading-tight">{t("t." + s)}</div>
              </div>
            ))}
          </div>
        </div>
      </Panel>

      {/* others */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {D.CARRIERS.filter((c) => !c.primary).map((c) => (
          <div key={c.name} className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center text-stone-400 text-[12px] font-bold">{c.code}</div>
              <div>
                <div className="text-[13.5px] font-semibold text-stone-900">{c.name}</div>
                <div className="text-[11.5px] text-stone-500">{c.zones}</div>
              </div>
            </div>
            <Button variant="secondary" size="sm">Configure</Button>
          </div>
        ))}
      </div>
    </div>
  );
}
window.Carriers = Carriers;
