/* global React, I, Badge, Avatar, Button, IconButton, Panel, KpiCard, SlaBadge */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// RETURNS HANDLER — queue + process flow + mini analytics.
// ─────────────────────────────────────────────────────────────────────
const RET_STATE = {
  open:    { tone: "yellow", label: "rt.open" },
  inspect: { tone: "blue",   label: "rt.inspectS" },
  restock: { tone: "purple", label: "rt.restockS" },
  closed:  { tone: "green",  label: "rt.closed" },
};

function Returns({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [batches, setBatches] = useState(() => D.RETURN_BATCHES.map((b) => ({ ...b })));
  const [open, setOpen] = useState(null);
  const [tab, setTab] = useState("batches");

  if (open) {
    const b = batches.find((x) => x.no === open);
    return <ReturnReconcile b={b} onClose={() => setOpen(null)} onToast={onToast} setBatches={setBatches} />;
  }

  const toReconcile = batches.filter((b) => !b.reconciled).length;
  const missingTot = batches.reduce((a, b) => a + (b.missing || 0), 0);
  const reasonCounts = Object.entries(D.RETURNS.reduce((m, r) => { m[r.reason] = (m[r.reason] || 0) + 1; return m; }, {})).sort((a, b) => b[1] - a[1]);

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{t("rs.title")}</h1>
          <p className="text-[12.5px] text-stone-500 mt-0.5">{t("rs.sub")} · {D.CARRIER}</p>
        </div>
        <Avatar name="Nadia Berrada" size={34} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Return} tone="stone" label={t("rs.batches")} value={batches.length} />
        <KpiCard icon={I.Clock} tone="amber" label={t("rs.toReconcile")} value={toReconcile} />
        <KpiCard icon={I.AlertCircle} tone="rose" label={t("rs.missingTot")} value={missingTot} />
        <KpiCard icon={I.TrendDown} tone="violet" label={t("rs.returnRate")} value="2.4" unit="%" />
      </div>

      <div className="flex items-center gap-1 border-b border-stone-200/70 mb-4">
        {[["batches", t("rs.list")], ["analytics", t("rs.analytics")]].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} className={`px-3 h-9 text-[13px] font-medium border-b-2 -mb-px transition-colors ${tab === k ? "border-[var(--accent-600)] text-stone-900" : "border-transparent text-stone-500 hover:text-stone-800"}`}>{l}</button>
        ))}
      </div>

      {tab === "batches" ? (
        <Panel bodyClass="p-0">
          <div className="overflow-x-auto"><table className="w-full min-w-[720px]">
            <thead><tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th className="text-start px-4 py-2.5">{t("rs.batch")}</th><th className="text-start px-4 py-2.5">Date</th><th className="text-start px-4 py-2.5">Owner</th>
              <th className="text-end px-4 py-2.5">{t("rs.orders")}</th><th className="text-end px-4 py-2.5 hidden sm:table-cell">{t("rs.qty")}</th>
              <th className="text-end px-4 py-2.5">{t("rs.missing")}</th><th className="text-end px-4 py-2.5 hidden md:table-cell">{t("rs.returnPct")}</th><th className="text-start px-4 py-2.5">Status</th>
            </tr></thead>
            <tbody className="divide-y divide-stone-100">
              {batches.map((b) => (
                <tr key={b.no} onClick={() => setOpen(b.no)} className="cursor-pointer hover:bg-stone-50 transition-colors">
                  <td className="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900">{b.no}</td>
                  <td className="px-4 py-2.5 text-[12px] text-stone-600 whitespace-nowrap">{b.date}</td>
                  <td className="px-4 py-2.5"><div className="flex items-center gap-1.5"><Avatar name={D.byId(b.owner).name} size={20} /><span className="text-[12px] text-stone-600 hidden sm:inline">{D.byId(b.owner).short}</span></div></td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{b.orders}</td>
                  <td className="px-4 py-2.5 text-end text-[12px] text-stone-600 tabular-nums hidden sm:table-cell">{b.qty}</td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] tabular-nums"><span className={b.missing ? "text-rose-600 font-medium" : "text-stone-400"}>{b.missing || 0}</span></td>
                  <td className="px-4 py-2.5 text-end text-[12px] tabular-nums hidden md:table-cell"><span className={b.pct >= 100 ? "text-emerald-600" : "text-amber-600"}>{b.pct}%</span></td>
                  <td className="px-4 py-2.5"><Badge tone={RS_STATUS[b.status]} dot className="whitespace-nowrap">{b.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Panel>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Panel title="Return rate · 7d" bodyClass="p-4"><window.LineChart data={[2,2.1,2.2,2,2.3,2.4,2.4]} height={160} stroke="#ef4444" /></Panel>
          <Panel title="Top return reasons" bodyClass="p-4 space-y-2.5">
            {reasonCounts.map(([reason, n]) => { const pct = n / D.RETURNS.length; return (
              <div key={reason}>
                <div className="flex items-center justify-between text-[12px] mb-1"><span className="text-stone-700">{D.RETURN_REASONS[reason]}</span><span className="text-stone-400 tabular-nums">{n}</span></div>
                <div className="h-1.5 rounded-full bg-stone-100 overflow-hidden"><div className="h-full bg-[var(--accent-500)] rounded-full" style={{ width: `${pct*100}%` }} /></div>
              </div>
            ); })}
          </Panel>
        </div>
      )}
    </div>
  );
}
window.Returns = Returns;

const RS_STATUS = { Draft: "neutral", "AWB Scanning": "amber", "Item Scanning": "blue", "Ready for Return": "purple", Returned: "green", Cancelled: "red" };

// ── Return Shipment reconciliation (full page, 2-phase scan) ─────────
function ReturnReconcile({ b, onClose, onToast, setBatches }) {
  const { t, dir } = window.useLg();
  const D = window.LG_DATA;
  const items = D.RETURN_ITEMS;
  const phaseOrder = ["Draft", "AWB Scanning", "Item Scanning", "Ready for Return", "Returned"];
  const [phase, setPhase] = useState(b.status);
  const [awbDone, setAwbDone] = useState(() => phaseOrder.indexOf(b.status) > 1 ? b.orders : (b.awbScanned || 0));
  const [itemsDone, setItemsDone] = useState(() => phaseOrder.indexOf(b.status) > 2 ? b.qty : (b.itemsScanned || 0));
  const [fb, setFb] = useState("idle");
  const awbPct = b.orders ? awbDone / b.orders : 0;
  const itemPct = b.qty ? itemsDone / b.qty : 0;
  const cur = phaseOrder.indexOf(phase);
  const missing = b.qty - itemsDone > 0 && phase === "Ready for Return" ? b.qty - itemsDone : (b.missing || 0);

  function scanAwb() { const n = Math.min(b.orders, awbDone + Math.ceil(b.orders / 8)); setAwbDone(n); setFb("ok"); setTimeout(() => setFb("idle"), 500); if (n >= b.orders) setPhase("Item Scanning"); }
  function scanItem() { const n = Math.min(b.qty, itemsDone + Math.ceil(b.qty / 8)); setItemsDone(n); setFb("ok"); setTimeout(() => setFb("idle"), 500); if (n >= b.qty - (b.missing || 0)) setPhase("Ready for Return"); }
  function finalize() { setPhase("Returned"); setBatches((bs) => bs.map((x) => x.no === b.no ? { ...x, reconciled: true, status: "Returned" } : x)); onToast?.({ type: "success", text: `${b.no} · ${b.orders} Sales Returns created` }); onClose(); }

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onClose} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"><I.Back width={15} height={15} className="rtl:rotate-180" />{t("rs.title")}</button>

      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="w-11 h-11 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center"><I.Return width={22} height={22} /></span>
            <div><div className="flex items-center gap-2 flex-wrap"><h1 className="font-mono text-[18px] font-bold text-stone-900">{b.no}</h1><Badge tone={RS_STATUS[phase]} dot className="whitespace-nowrap">{phase}</Badge></div>
            <div className="text-[12.5px] text-stone-600 mt-1 flex items-center gap-2"><Avatar name={D.byId(b.owner).name} size={20} />{D.byId(b.owner).name} · {b.date} · {D.CARRIER}</div></div>
          </div>
          <div className="flex items-center gap-2">
            {phase === "Ready for Return" && <Button variant="success" size="md" icon={I.CheckCircle} onClick={finalize}>{t("rs.createReturns")}</Button>}
            <Button variant="secondary" size="md" iconRight={I.External}>{t("c.openInErp")}</Button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          {[[t("rs.orders"), b.orders], [t("rs.qty"), b.qty], [t("rs.missing"), missing, missing > 0 ? "rose" : null], [t("rs.returnPct"), b.pct + "%"]].map(([k, v, tone], i) => (
            <div key={i} className="bg-stone-50 rounded-xl px-3 py-2.5"><div className={`text-[20px] font-semibold tabular-nums leading-none ${tone === "rose" ? "text-rose-600" : "text-stone-900"}`}>{v}</div><div className="text-[11px] text-stone-500 mt-1">{k}</div></div>
          ))}
        </div>
        {/* phase stepper */}
        <div className="flex items-center mt-5">
          {phaseOrder.map((s, i) => { const done = i <= cur; return (
            <React.Fragment key={s}>
              <div className="flex flex-col items-center gap-1.5 flex-shrink-0" style={{ width: 96 }}>
                <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold ${done ? "bg-emerald-500 text-white" : "bg-stone-100 text-stone-400"}`}>{done ? <I.Check width={14} height={14} /> : i + 1}</span>
                <span className={`text-[10.5px] font-medium text-center leading-tight ${done ? "text-stone-900" : "text-stone-400"}`}>{s}</span>
              </div>
              {i < phaseOrder.length - 1 && <div className={`flex-1 h-0.5 -mt-6 ${i < cur ? "bg-emerald-300" : "bg-stone-200"}`} />}
            </React.Fragment>
          ); })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
        {/* scan phases */}
        <div className="space-y-4">
          <Panel title={t("rs.awbPhase")} right={<Badge tone={awbPct >= 1 ? "green" : "amber"} dot>{awbDone}/{b.orders}</Badge>} bodyClass="p-4">
            <button onClick={scanAwb} disabled={awbPct >= 1 || phase === "Returned"} className={`w-full flex items-center gap-3 px-4 h-14 rounded-2xl ring-2 transition-all active:scale-[0.99] ${fb === "ok" && phase === "AWB Scanning" ? "ring-emerald-400 bg-emerald-50" : awbPct >= 1 ? "ring-emerald-300 bg-emerald-50/50" : "ring-stone-300 bg-white hover:ring-stone-400"}`}>
              <span className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${awbPct >= 1 ? "bg-emerald-500 text-white" : "bg-stone-900 text-white"}`}>{awbPct >= 1 ? <I.Check width={20} height={20} /> : <I.Search width={18} height={18} />}</span>
              <span className="text-[14px] font-medium text-stone-600 text-start flex-1">{awbPct >= 1 ? "All AWBs scanned" : t("rs.scanAwb")}</span>
            </button>
            <div className="h-1.5 rounded-full bg-stone-100 overflow-hidden mt-3"><div className="h-full bg-emerald-500 rounded-full" style={{ width: `${awbPct*100}%`, transition: "width .4s ease" }} /></div>
          </Panel>

          <Panel title={t("rs.itemPhase")} right={<Badge tone={itemPct >= 1 ? "green" : cur >= 2 ? "blue" : "neutral"} dot>{itemsDone}/{b.qty}</Badge>} bodyClass="p-4">
            <button onClick={scanItem} disabled={cur < 2 || itemsDone >= b.qty - (b.missing || 0) || phase === "Returned"} className={`w-full flex items-center gap-3 px-4 h-14 rounded-2xl ring-2 transition-all active:scale-[0.99] ${cur < 2 ? "ring-stone-200 bg-stone-50 opacity-50 cursor-not-allowed" : fb === "ok" && phase === "Item Scanning" ? "ring-emerald-400 bg-emerald-50" : "ring-stone-300 bg-white hover:ring-stone-400"}`}>
              <span className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${itemsDone >= b.qty - (b.missing||0) && cur >= 2 ? "bg-emerald-500 text-white" : "bg-stone-900 text-white"}`}><I.Search width={18} height={18} /></span>
              <span className="text-[14px] font-medium text-stone-600 text-start flex-1">{cur < 2 ? "Finish AWB scanning first" : t("rs.scanItem")}</span>
            </button>
            <div className="h-1.5 rounded-full bg-stone-100 overflow-hidden mt-3"><div className="h-full bg-emerald-500 rounded-full" style={{ width: `${itemPct*100}%`, transition: "width .4s ease" }} /></div>
          </Panel>

          {/* return lines */}
          <Panel title={t("rs.lines")} bodyClass="p-0">
            <div className="divide-y divide-stone-100">
              {items.map((it, i) => (
                <div key={i} className="grid items-center gap-3 px-4 py-2.5 grid-cols-[1fr_auto_auto]">
                  <div className="min-w-0"><div className="text-[12.5px] font-medium text-stone-900 truncate">{it.name}</div><div className="font-mono text-[10.5px] text-stone-400">{it.sku} · {it.dn}</div></div>
                  <span className="text-[12px] tabular-nums text-stone-600">{it.actual}/{it.ordered}</span>
                  {it.complete ? <Badge tone="green" dot>{t("rs.complete")}</Badge> : <Badge tone="rose" dot className="whitespace-nowrap">{t("rs.short")} {it.ordered - it.actual}</Badge>}
                </div>
              ))}
            </div>
          </Panel>
        </div>

        {/* right: missing + activity */}
        <div className="space-y-4">
          <Panel title={t("rs.missingSkus")} right={missing > 0 && <Badge tone="red" dot>{missing}</Badge>} bodyClass="p-4">
            {missing > 0 || (b.missingSkus && b.missingSkus.length) ? (
              <div className="space-y-2">
                {(b.missingSkus || ["CSM44021"]).map((s) => (
                  <div key={s} className="flex items-center gap-2 rounded-lg bg-rose-50 ring-1 ring-rose-200/60 px-3 py-2"><I.AlertCircle width={14} height={14} className="text-rose-500 flex-shrink-0" /><span className="font-mono text-[12px] text-rose-800">{s}</span><span className="text-[11px] text-rose-600 ms-auto">not in batch</span></div>
                ))}
              </div>
            ) : <div className="text-center text-[12.5px] text-emerald-600 py-4 flex items-center justify-center gap-1.5"><I.CheckCircle width={15} height={15} />No missing items</div>}
          </Panel>
          <window.ActivityFeed events={[
            { who: D.byId(b.owner).short, act: "Return batch created · " + b.orders + " orders", at: "14:04", on: true },
            { who: D.byId(b.owner).short, act: "AWB scanning started", at: "14:10", on: cur >= 1 },
            { who: D.byId(b.owner).short, act: "Item scanning started", at: "16:22", on: cur >= 2 },
            { who: D.byId(b.owner).short, act: b.orders + " Sales Returns created", at: "17:27", on: cur >= 4 },
          ]} />
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// TRACKING — carrier tracking board (manager / dispatcher).
// ─────────────────────────────────────────────────────────────────────
function Tracking() {
  const { t, openOrder, askConfirm } = window.useLg();
  const D = window.LG_DATA;
  const [resolved, setResolved] = useState(() => new Set());
  const [toast, setToast] = useState(null);
  const [stateF, setStateF] = useState("all");
  const [q, setQ] = useState("");
  const [tlParcel, setTlParcel] = useState(null);
  const exc = D.PARCELS.filter((p) => (p.track === "exception" || p.track === "failed") && !resolved.has(p.dn));
  function resolve(p, label) { askConfirm?.({ title: label, body: `${p.dn} · ${p.customer} · AWB ${p.awb}`, confirmLabel: label, onConfirm: () => { setResolved((s) => new Set([...s, p.dn])); setToast({ type: "success", text: `${p.dn} · ${label} · synced to ${D.CARRIER}` }); setTimeout(() => setToast(null), 2600); } }); }
  const shown = D.PARCELS.filter((p) => (stateF === "all" || p.track === stateF) && (!q || `${p.dn} ${p.awb} ${p.trackNo} ${p.customer}`.toLowerCase().includes(q.toLowerCase())));

  if (tlParcel) return <ParcelTimeline p={D.PARCELS.find((x) => x.dn === tlParcel)} onClose={() => setTlParcel(null)} onOrder={openOrder} />;

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <div className="flex items-start justify-between gap-3 mb-5 flex-wrap">
        <div><h1 className="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{t("nav.tracking")}</h1>
        <p className="text-[12.5px] text-stone-500 mt-0.5">{D.CARRIER} · live parcel states</p></div>
        <div className="flex items-center gap-2"><span className="text-[11.5px] text-stone-400">{t("tr.lastSync")}</span><Button variant="secondary" size="md" icon={I.Globe}>{t("tr.sync")}</Button></div>
      </div>

      {exc.length > 0 && (
        <Panel title={t("tr.exceptions")} className="mb-5" right={<Badge tone="red" dot>{exc.length}</Badge>} bodyClass="p-0">
          <div className="divide-y divide-stone-100">
            {exc.map((p) => (
              <div key={p.dn} className="flex items-center gap-3 px-4 py-3 flex-wrap">
                <span className="font-mono text-[12px] font-semibold text-stone-900 w-[150px] flex-shrink-0">{p.dn}</span>
                <div className="flex-1 min-w-[140px]"><div className="text-[12.5px] text-stone-800 truncate">{p.customer}</div><div className="text-[11px] text-rose-600 truncate">{p.msg}</div></div>
                <window.TrackBadge state={p.track} />
                <div className="flex items-center gap-1.5">
                  <Button variant="secondary" size="sm" icon={I.Clock} onClick={() => resolve(p, t("tr.reschedule"))}>{t("tr.reschedule")}</Button>
                  <Button variant="secondary" size="sm" icon={I.Phone} onClick={() => resolve(p, t("tr.contact"))}>{t("tr.contact")}</Button>
                  <Button variant="danger" size="sm" icon={I.Return} onClick={() => resolve(p, t("tr.markReturned"))}>{t("tr.markReturned")}</Button>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {/* clickable state distribution */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 mb-4">
        {D.TRACK_STATES.map((s) => {
          const active = stateF === s;
          return (
            <button key={s} onClick={() => setStateF(active ? "all" : s)}
              className={`rounded-xl ring-1 p-3 text-center transition-all ${active ? "ring-[var(--accent-400)] bg-[var(--accent-50)]/50" : "ring-stone-200/70 bg-white hover:ring-stone-300"}`}>
              <div className="text-[20px] font-semibold text-stone-900 tabular-nums leading-none">{D.TRACK_COUNTS[s] ?? 0}</div>
              <div className="text-[10px] text-stone-500 mt-1.5 leading-tight">{t("t." + s)}</div>
            </button>
          );
        })}
      </div>

      {/* search */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]"><I.Search width={14} height={14} className="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("tr.searchParcel")} className="w-full h-9 ps-9 pe-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none" /></div>
        {stateF !== "all" && <button onClick={() => setStateF("all")} className="px-2.5 h-9 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-600 hover:ring-stone-300 inline-flex items-center gap-1.5"><window.TrackBadge state={stateF} /><I.X width={12} height={12} /></button>}
      </div>

      <Panel title="Parcels" sub={`${shown.length} ${stateF === "all" ? "active" : t("t." + stateF)}`} bodyClass="p-0">
        <div className="divide-y divide-stone-100">
          {shown.map((p) => (
            <button key={p.dn} onClick={() => setTlParcel(p.dn)} className="w-full grid items-center gap-3 px-4 py-3 hover:bg-stone-50 transition-colors text-start grid-cols-[150px_1fr_auto_auto] md:grid-cols-[150px_1fr_120px_70px_auto]">
              <span className="font-mono text-[12px] font-semibold text-stone-900">{p.dn}</span>
              <div className="min-w-0"><div className="text-[12.5px] text-stone-800 truncate">{p.customer}</div><div className="text-[11px] text-stone-500 truncate">{p.msg}</div></div>
              <span className="font-mono text-[11px] text-stone-400 hidden md:block">{p.trackNo}</span>
              <span className={`text-[11px] tabular-nums text-end hidden md:block ${p.days < 0 ? "text-rose-600 font-medium" : p.days === 0 ? "text-amber-600" : "text-stone-400"}`}>{p.days < 0 ? `${Math.abs(p.days)}d ${t("tr.overdue")}` : p.days === 0 ? t("tr.dueToday") : `${p.days}d`}</span>
              <window.TrackBadge state={p.track} />
            </button>
          ))}
          {shown.length === 0 && <div className="text-center text-[12.5px] text-stone-400 py-12">No parcels match.</div>}
        </div>
      </Panel>
      <window.Toast toast={toast} />
    </div>
  );
}
window.Tracking = Tracking;

// ── Parcel carrier timeline (full page) ──────────────────────────────
function ParcelTimeline({ p, onClose, onOrder }) {
  const { t, dir } = window.useLg();
  const D = window.LG_DATA;
  const order = D.STAGE_SEQ.indexOf;
  const steps = [
    { k: "pickedup", label: t("t.pickedup"), at: "Jun 19 · 14:22", done: true },
    { k: "intransit", label: t("t.intransit"), at: "Jun 19 · 18:40", done: ["intransit","outfordelivery","delivered","exception","failed"].includes(p.track) },
    { k: "outfordelivery", label: t("t.outfordelivery"), at: "Jun 20 · 08:10", done: ["outfordelivery","delivered","exception","failed"].includes(p.track) },
    { k: p.track === "delivered" ? "delivered" : "exception", label: p.track === "delivered" ? t("t.delivered") : p.track === "failed" ? t("t.failed") : t("t.exception"), at: "Jun 20 · 11:55", done: ["delivered","exception","failed"].includes(p.track), bad: p.track === "exception" || p.track === "failed" },
  ];
  return (
    <div className="max-w-[900px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onClose} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"><I.Back width={15} height={15} className="rtl:rotate-180" />{t("nav.tracking")}</button>
      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="w-11 h-11 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center"><I.Globe width={22} height={22} /></span>
            <div><div className="flex items-center gap-2 flex-wrap"><h1 className="font-mono text-[17px] font-bold text-stone-900">{p.dn}</h1><window.TrackBadge state={p.track} /><SlaBadge sla={p.sla} size="sm" /></div>
            <div className="text-[12.5px] text-stone-600 mt-1">{p.customer} · {p.carrier}</div></div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="md" icon={I.Orders} onClick={() => onOrder(p.order)}>{t("c.order")} {p.order}</Button>
            <Button variant="secondary" size="md" iconRight={I.External}>{t("c.openInErp")}</Button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          {[["AWB", p.awb], [t("tr.trackNo"), p.trackNo], [t("c.value"), window.fmtMAD(p.value) + " MAD"], [t("tr.daysLeft"), p.days < 0 ? Math.abs(p.days) + "d over" : p.days === 0 ? "today" : p.days + "d"]].map(([k, v], i) => (
            <div key={i} className="bg-stone-50 rounded-xl px-3 py-2.5"><div className="text-[14px] font-semibold text-stone-900 tabular-nums leading-tight truncate">{v}</div><div className="text-[11px] text-stone-500 mt-1">{k}</div></div>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
        <Panel title={t("tr.timeline")} sub={p.carrier} bodyClass="p-4">
          <ol className="relative">
            {steps.map((e, i) => { const last = i === steps.length - 1; return (
              <li key={i} className="relative flex gap-3.5 pb-4 last:pb-0">
                {!last && <span className={`absolute top-8 w-px ${e.done && !e.bad ? "bg-emerald-200" : "bg-stone-200"}`} style={dir === "rtl" ? { right: 13 } : { left: 13 }} />}
                <span className={`relative z-10 w-[27px] h-[27px] rounded-lg flex items-center justify-center flex-shrink-0 ${e.done ? (e.bad ? "bg-rose-500 text-white" : "bg-emerald-500 text-white") : "bg-white ring-1 ring-stone-300 text-stone-400"}`}>{e.done ? (e.bad ? <I.AlertCircle width={14} height={14} /> : <I.Check width={14} height={14} />) : i + 1}</span>
                <div className="min-w-0 flex-1"><div className={`text-[13px] font-medium ${e.bad ? "text-rose-700" : e.done ? "text-stone-900" : "text-stone-400"}`}>{e.label}</div>{e.done && <div className="text-[11px] text-stone-400 tabular-nums">{e.at}</div>}</div>
              </li>
            ); })}
          </ol>
        </Panel>
        <Panel title={t("tr.carrierMsg")} bodyClass="p-4">
          <div className={`rounded-xl p-3 ring-1 ${p.track === "exception" || p.track === "failed" ? "bg-rose-50 ring-rose-200/60" : "bg-stone-50 ring-stone-200/60"}`}>
            <div className="flex items-center gap-2 mb-1.5"><span className={`w-2 h-2 rounded-full ${p.track === "exception" || p.track === "failed" ? "bg-rose-500" : "bg-emerald-500"}`} /><span className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">{p.carrier}</span></div>
            <p className="text-[12.5px] text-stone-800 text-pretty">{p.msg}</p>
          </div>
          {(p.track === "exception" || p.track === "failed") && (
            <div className="grid grid-cols-1 gap-2 mt-3">
              <Button variant="secondary" size="md" icon={I.Clock}>{t("tr.reschedule")}</Button>
              <Button variant="secondary" size="md" icon={I.Phone}>{t("tr.contact")}</Button>
              <Button variant="danger" size="md" icon={I.Return}>{t("tr.markReturned")}</Button>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// ROUTES — last-mile delivery trips (ERPNext Delivery Trip)
// ─────────────────────────────────────────────────────────────────────
const RV_STATUS = { Loading: "yellow", "En route": "blue", Completed: "green", Cancelled: "red" };
function RoutesBoard({ onToast }) {
  const { t, dir } = window.useLg();
  const D = window.LG_DATA;
  const [open, setOpen] = useState(null);
  const R = D.ROUTES;
  const active = R.filter((r) => r.status === "En route" || r.status === "Loading").length;
  const out = R.reduce((a, r) => a + (r.parcels - r.delivered), 0);
  const delivered = R.reduce((a, r) => a + r.delivered, 0);
  const avgStops = Math.round(R.reduce((a, r) => a + r.stops, 0) / R.length);

  if (open) return <RouteDetail route={R.find((x) => x.no === open)} onClose={() => setOpen(null)} dir={dir} onToast={onToast} />;
  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("rv.title")} sub={`${t("rv.sub")} · ${D.CARRIER}`}>
        <Button variant="brand" size="md" icon={I.Plus}>Plan trip</Button>
      </PageHead>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <KpiCard icon={I.Globe} tone="cyan" label={t("rv.active")} value={active} />
        <KpiCard icon={I.Box} tone="amber" label={t("rv.out")} value={out} />
        <KpiCard icon={I.CheckCircle} tone="emerald" label={t("rv.deliveredToday")} value={delivered} />
        <KpiCard icon={I.Pin} tone="stone" label={t("rv.avgStops")} value={avgStops} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {R.map((r) => {
          const pct = r.parcels ? r.delivered / r.parcels : 0;
          const st = RV_STATUS[r.status];
          return (
            <div key={r.no} onClick={() => setOpen(r.no)} className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 cursor-pointer hover:ring-stone-300 hover:shadow-[0_8px_24px_-8px_rgba(0,0,0,0.12)] hover:-translate-y-0.5 transition-all">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="w-10 h-10 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center"><I.Globe width={20} height={20} /></span>
                  <div>
                    <div className="flex items-center gap-2"><span className="font-mono text-[13px] font-semibold text-stone-900">{r.no}</span><Badge tone={st} dot>{r.status}</Badge></div>
                    <div className="text-[11.5px] text-stone-500 mt-0.5 flex items-center gap-1.5"><I.Pin width={11} height={11} className="text-stone-400" />{r.zone}</div>
                  </div>
                </div>
                {r.exceptions > 0 && <Badge tone="red" dot>{r.exceptions} exc</Badge>}
              </div>
              <div className="flex items-center gap-2.5 mt-3">
                <Avatar name={r.driver} size={24} />
                <span className="text-[12px] text-stone-600 flex-1">{r.driver}</span>
                <span className="text-[11.5px] text-stone-500 tabular-nums">{r.stops} {t("rv.stops")}</span>
                {r.eta !== "—" && <span className="text-[11.5px] text-stone-500 tabular-nums">· {t("rv.eta")} {r.eta}</span>}
              </div>
              <div className="mt-3">
                <div className="flex items-center justify-between text-[11px] mb-1"><span className="text-stone-500 tabular-nums">{r.delivered}/{r.parcels} {t("c.parcels")}</span><span className="font-semibold tabular-nums" style={{ color: pct >= 1 ? "#10b981" : "#06b6d4" }}>{Math.round(pct * 100)}%</span></div>
                <div className="h-2 rounded-full bg-stone-100 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${Math.max(3, pct * 100)}%`, background: pct >= 1 ? "#10b981" : "#06b6d4" }} /></div>
              </div>
              <div className="mt-3 flex justify-end">
                <Button variant="secondary" size="sm" icon={I.Pin} onClick={(e) => { e.stopPropagation(); setOpen(r.no); }}>View stops</Button>
              </div>
            </div>
          );
        })}
      </div>
      {/* route detail now rendered as full page above */}
    </div>
  );
}
window.RoutesBoard = RoutesBoard;

function RouteDetail({ route, onClose, dir, onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const st = RV_STATUS[route.status];
  const customers = ["Khadija abhaoui", "Sara Razine", "Imane Tazi", "Najat Bennani", "Hind El Yazami", "Widad Widad", "Ghizlane Dargal", "Amal Mourid", "Rim Cherkaoui", "Loubna Saidi"];
  const stops = Array.from({ length: route.stops }).map((_, i) => {
    const done = i < route.delivered;
    const exception = !done && route.exceptions > 0 && i >= route.stops - route.exceptions;
    const h = 9 + Math.floor(i * 0.5), m = (i * 23) % 60;
    return { i, customer: customers[i % customers.length], addr: `${route.zone} · ${100 + i * 7}`, done, exception, eta: `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}` };
  });
  const pct = route.parcels ? route.delivered / route.parcels : 0;
  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onClose} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap">
        <I.Back width={15} height={15} className="rtl:rotate-180" />{t("rv.title")}
      </button>

      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <span className="w-11 h-11 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center"><I.Globe width={22} height={22} /></span>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="font-mono text-[19px] font-bold text-stone-900">{route.no}</h1>
                <Badge tone={st} dot>{route.status}</Badge>
                {route.exceptions > 0 && <Badge tone="red" dot className="whitespace-nowrap">{route.exceptions} exc</Badge>}
              </div>
              <div className="text-[12.5px] text-stone-600 mt-1 flex items-center gap-2"><Avatar name={route.driver} size={20} />{route.driver} · <I.Pin width={12} height={12} className="text-stone-400" />{route.zone}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="md" icon={I.Globe} onClick={() => onToast?.({ type: "info", text: `${route.no} · live tracking · ${route.driver}` })}>{t("rv.track")}</Button>
            <Button variant="secondary" size="md" iconRight={I.External}>{t("c.openInErp")}</Button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <PlStat2 label={t("rv.stops")} value={route.stops} />
          <PlStat2 label={t("rv.deliveredToday")} value={route.delivered} tone="emerald" />
          <PlStat2 label={t("rv.out")} value={route.parcels - route.delivered} />
          <PlStat2 label={t("rv.eta")} value={route.eta} />
        </div>
        <div className="mt-4">
          <div className="flex items-center justify-between text-[11px] mb-1"><span className="text-stone-500 tabular-nums">{route.delivered}/{route.parcels} {t("c.parcels")}</span><span className="font-semibold tabular-nums" style={{ color: pct >= 1 ? "#10b981" : "#06b6d4" }}>{Math.round(pct * 100)}%</span></div>
          <div className="h-2 rounded-full bg-stone-100 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${Math.max(3, pct * 100)}%`, background: pct >= 1 ? "#10b981" : "#06b6d4" }} /></div>
        </div>
      </div>

      <Panel title={t("rv.stops")} sub={route.zone} right={<Badge tone="cyan" dot>{route.stops} stops</Badge>} bodyClass="p-4">
        <ol className="relative max-w-[760px]">
          {stops.map((s, i) => {
            const last = i === stops.length - 1;
            return (
              <li key={i} className="relative flex gap-3.5 pb-3 last:pb-0">
                {!last && <span className={`absolute top-9 w-px ${s.done ? "bg-emerald-200" : "bg-stone-200"}`} style={dir === "rtl" ? { right: 15 } : { left: 15 }} />}
                <span className={`relative z-10 w-[31px] h-[31px] rounded-lg flex items-center justify-center text-[12px] font-bold flex-shrink-0 ${s.done ? "bg-emerald-500 text-white" : s.exception ? "bg-rose-500 text-white" : "bg-white ring-1 ring-stone-300 text-stone-500"}`}>{s.done ? <I.Check width={15} height={15} /> : s.exception ? <I.AlertCircle width={15} height={15} /> : s.i + 1}</span>
                <div className={`min-w-0 flex-1 rounded-xl ring-1 p-3 ${s.done ? "ring-emerald-200 bg-emerald-50/40" : s.exception ? "ring-rose-200 bg-rose-50/40" : "ring-stone-200 bg-white"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[13.5px] font-medium text-stone-900 truncate">{s.customer}</span>
                    <span className={`text-[11.5px] font-medium tabular-nums flex-shrink-0 ${s.done ? "text-emerald-600" : s.exception ? "text-rose-500" : "text-stone-400"}`}>{s.done ? "✓ Delivered" : s.exception ? "Failed" : s.eta}</span>
                  </div>
                  <div className="text-[11.5px] text-stone-500 flex items-center gap-1.5 mt-1"><I.Pin width={11} height={11} className="text-stone-400" />{s.addr}</div>
                </div>
              </li>
            );
          })}
        </ol>
      </Panel>
    </div>
  );
}
function PlStat2({ label, value, tone }) {
  return <div className="bg-stone-50 rounded-xl px-3 py-2.5"><div className={`text-[22px] font-semibold tabular-nums leading-none ${tone === "emerald" ? "text-emerald-600" : "text-stone-900"}`}>{typeof value === "number" ? <window.CountUp value={value} /> : value}</div><div className="text-[11px] text-stone-500 mt-1.5">{label}</div></div>;
}

// ─────────────────────────────────────────────────────────────────────
// TEAM / PERFORMANCE (shared desktop view)
// ─────────────────────────────────────────────────────────────────────
function TeamPerformance({ self }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const meId = self || "marouane";
  const me = D.LEADERBOARD.find((p) => p.id === meId) || D.LEADERBOARD[0];
  return (
    <div className="max-w-[1100px] mx-auto px-6 py-6 animate-fade-in space-y-5">
      <div>
        <h1 className="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{self ? t("pf.title") : t("ck.leaderboard")}</h1>
        <p className="text-[12.5px] text-stone-500 mt-0.5">{t("c.today")} · coaching view</p>
      </div>

      {self && (
        <div className="max-w-md"><window.PerfWidget person={me} /></div>
      )}

      <Panel title={t("ck.leaderboard")} bodyClass="p-0">
        <table className="w-full text-start">
          <thead>
            <tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th className="text-start px-4 py-2.5 font-semibold">{t("c.rank")}</th>
              <th className="text-start px-4 py-2.5 font-semibold">{t("nav.team")}</th>
              <th className="text-end px-4 py-2.5 font-semibold">{t("pf.completed")}</th>
              <th className="text-end px-4 py-2.5 font-semibold hidden sm:table-cell">{t("pf.avgTime")}</th>
              <th className="text-end px-4 py-2.5 font-semibold">{t("c.sla")}</th>
              <th className="text-end px-4 py-2.5 font-semibold hidden md:table-cell">{t("pf.trend")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {D.LEADERBOARD.map((p) => {
              const person = D.byId(p.id);
              return (
                <tr key={p.id} className={p.id === meId && self ? "bg-[var(--accent-50)]/40" : ""}>
                  <td className="px-4 py-2.5"><span className={`text-[13px] font-bold tabular-nums ${p.rank===1?"text-[var(--accent-700)]":"text-stone-400"}`}>{p.rank}</span></td>
                  <td className="px-4 py-2.5"><div className="flex items-center gap-2"><Avatar name={person.name} size={26} /><span className="text-[12.5px] font-medium text-stone-900">{person.short}{p.rank===1 && " ⭐"}</span></div></td>
                  <td className="px-4 py-2.5 text-end text-[13px] font-semibold text-stone-900 tabular-nums">{p.picks}</td>
                  <td className="px-4 py-2.5 text-end text-[12.5px] text-stone-600 tabular-nums hidden sm:table-cell">{p.avg}</td>
                  <td className="px-4 py-2.5 text-end"><span className={`text-[12.5px] font-semibold tabular-nums ${p.sla>=90?"text-emerald-600":p.sla>=85?"text-amber-600":"text-stone-600"}`}>{p.sla}%</span></td>
                  <td className="px-4 py-2.5 hidden md:table-cell"><div className="flex justify-end"><Sparkline data={p.trend} width={70} height={22} /></div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
window.TeamPerformance = TeamPerformance;
