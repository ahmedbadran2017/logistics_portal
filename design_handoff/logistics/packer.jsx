/* global React, I, Badge, Avatar, Button, IconButton, StageBadge, SlaBadge, TrackBadge, Panel, ScanInput, EmptyState */
const { useState, useMemo, useEffect } = React;

// ─────────────────────────────────────────────────────────────────────
// PACKER / SHIPPER — Label & Print queue + Today's Manifest builder.
// ─────────────────────────────────────────────────────────────────────
function Packer({ onToast, initialTab = "label" }) {
  const { t } = window.useLg();
  const [tab, setTab] = useState(initialTab);
  useEffect(() => { setTab(initialTab); }, [initialTab]);
  return (
    <div className="h-full flex flex-col animate-fade-in">
      <div className="px-6 pt-4 border-b border-stone-200/60 bg-white/40">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <h1 className="text-[19px] font-semibold text-stone-900 tracking-[-0.01em]">{t("role.packer.home")}</h1>
            <p className="text-[12.5px] text-stone-500 mt-0.5">{window.LG_DATA.CARRIER} · {window.LG_DATA.WAREHOUSE}</p>
          </div>
          <Avatar name="Reda ZAARI" size={34} />
        </div>
        <div className="flex items-center gap-1">
          {[["label", t("pc.labelQueue"), I.Tag], ["manifest", t("pc.manifestTab"), I.File]].map(([k, l, Ic]) => (
            <button key={k} onClick={() => setTab(k)}
              className={`flex items-center gap-1.5 px-3 h-9 text-[13px] font-medium border-b-2 -mb-px transition-colors ${tab === k ? "border-[var(--accent-600)] text-stone-900" : "border-transparent text-stone-500 hover:text-stone-800"}`}>
              <Ic width={15} height={15} />{l}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {tab === "label" ? <LabelQueue onToast={onToast} /> : <ManifestBuilder onToast={onToast} />}
      </div>
    </div>
  );
}
window.Packer = Packer;

// ── Tab 1: Label & print ─────────────────────────────────────────────
function LabelQueue({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const [rows, setRows] = useState(() => D.LABEL_QUEUE.map((r) => ({ ...r })));
  const [preview, setPreview] = useState(D.LABEL_QUEUE[0].order);

  function print(order) {
    setRows((rs) => rs.map((r) => (r.order === order ? { ...r, printed: true } : r)));
    onToast?.({ type: "success", text: `AWB generated · #${order}` });
  }
  const sel = rows.find((r) => r.order === preview);
  const pending = rows.filter((r) => !r.printed).length;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4 p-6">
      {/* queue */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-[13px] font-semibold text-stone-700">{rows.length} {t("c.orders")} · {pending} {t("c.print").toLowerCase()}</span>
          <Button variant="brand" size="md" icon={I.Tag} onClick={() => { rows.filter(r=>!r.printed).forEach(r=>print(r.order)); }}>{t("pc.generateLabel")} · all</Button>
        </div>
        <div className="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div className="divide-y divide-stone-100">
            {rows.map((r) => (
              <div key={r.order} onClick={() => setPreview(r.order)}
                className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors ${preview === r.order ? "bg-[var(--accent-50)]/40" : "hover:bg-stone-50"}`}>
                <span className="font-mono text-[12px] font-semibold text-stone-900 w-[80px] flex-shrink-0 truncate">{r.order}</span>
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] text-stone-800 truncate">{r.customer}</div>
                  <div className="text-[11px] text-stone-500 tabular-nums">{r.parcels} {t("c.parcels")} · {window.fmtMAD(r.value)} MAD</div>
                </div>
                <SlaBadge sla={r.sla} size="sm" />
                {r.printed
                  ? <Badge tone="green" dot>{t("c.printed")}</Badge>
                  : <Button variant="secondary" size="sm" icon={I.Tag} onClick={(e) => { e.stopPropagation(); print(r.order); }}>{t("c.print")}</Button>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* label preview */}
      <div>
        <div className="text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400 mb-2">Label preview</div>
        <div className="bg-white rounded-xl ring-1 ring-stone-200/70 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
          <div className="flex items-center justify-between pb-3 border-b border-dashed border-stone-300">
            <div className="font-bold text-[15px] text-stone-900">{D.CARRIER}</div>
            <Badge tone="neutral">AWB</Badge>
          </div>
          <div className="py-4 text-center">
            <div className="font-mono text-[15px] font-semibold text-stone-900 tracking-wider">{"LD007758" + String(300 + ((parseInt((sel?.order||"").replace(/\D/g,"")) || 0) % 600)).padStart(3,"0")}</div>
            {/* faux barcode */}
            <div className="mt-3 flex items-end justify-center gap-[2px] h-12">
              {Array.from({ length: 42 }).map((_, i) => (
                <span key={i} className="bg-stone-900" style={{ width: (i % 4 === 0 ? 3 : i % 3 === 0 ? 1 : 2), height: `${60 + (i * 37 % 40)}%` }} />
              ))}
            </div>
          </div>
          <div className="pt-3 border-t border-dashed border-stone-300 space-y-1.5 text-[12px]">
            <Row k={t("c.order")} v={sel?.order} />
            <Row k={t("c.customer")} v={sel?.customer} />
            <Row k="From" v={D.WAREHOUSE} />
            <Row k={t("c.parcels")} v={sel?.parcels} />
            <Row k={t("c.value")} v={`${window.fmtMAD(sel?.value)} MAD`} />
          </div>
          <Button variant="primary" size="md" icon={I.Download} className="w-full mt-4" onClick={() => print(sel.order)}>{t("c.print")} label</Button>
        </div>
      </div>
    </div>
  );
}

function Row({ k, v }) {
  return <div className="flex items-center justify-between"><span className="text-stone-400">{k}</span><span className="font-medium text-stone-800">{v}</span></div>;
}

// ── Tab 2: Manifest builder ──────────────────────────────────────────
function ManifestBuilder({ onToast }) {
  const { t, askConfirm } = window.useLg();
  const D = window.LG_DATA;
  const M = D.MANIFEST;
  const [added, setAdded] = useState(() => D.PARCELS.slice(0, 2).map((p) => ({ ...p })));
  const pool = D.PARCELS.filter((p) => !added.find((a) => a.dn === p.dn));
  const [poolState, setPoolState] = useState(pool);

  // running totals — base = manifest minus the two parcels we preload as "just added"
  const baseParcels = M.parcels - 2, baseValue = M.value - 303;
  const parcels = baseParcels + added.length;
  const value = baseValue + added.reduce((a, p) => a + p.value, 0);
  const atRisk = added.filter((p) => p.sla === "late" || p.sla === "atrisk").length;

  function add() {
    if (poolState.length === 0) return;
    const [first, ...rest] = poolState;
    setAdded((a) => [...a, first]);
    setPoolState(rest);
    onToast?.({ type: "success", text: `${first.dn} → ${M.no}` });
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4 p-6">
      {/* builder */}
      <div className="space-y-4">
        {/* manifest header */}
        <div className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center"><I.File width={20} height={20} /></span>
              <div>
                <div className="font-mono text-[15px] font-semibold text-stone-900">{M.no}</div>
                <div className="text-[11.5px] text-stone-500">{D.CARRIER} · {t("c.today")} {M.pickupDate} · {M.window}</div>
              </div>
            </div>
            <div className="flex items-center gap-5">
              <div className="text-end">
                <div className="text-[24px] font-semibold text-stone-900 tabular-nums leading-none">{parcels}</div>
                <div className="text-[10.5px] text-stone-500 uppercase tracking-wide">{t("c.parcels")}</div>
              </div>
              <div className="text-end">
                <div className="text-[24px] font-semibold text-stone-900 tabular-nums leading-none">{window.fmtMAD(value)}</div>
                <div className="text-[10.5px] text-stone-500 uppercase tracking-wide">MAD</div>
              </div>
            </div>
          </div>
        </div>

        {/* scan to add */}
        <div onClick={add} className="cursor-pointer">
          <ScanInput placeholder={t("pc.addParcel")} onScan={add} />
        </div>

        {/* added parcels */}
        <div className="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div className="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-700 flex items-center justify-between">
            <span>On manifest · last added</span>
            <span className="text-stone-400 tabular-nums">{added.length} new</span>
          </div>
          <div className="divide-y divide-stone-100 max-h-[340px] overflow-y-auto">
            {added.map((p) => (
              <div key={p.dn} className="flex items-center gap-3 px-4 py-2.5 animate-scale-in">
                <I.CheckCircle width={16} height={16} className="text-emerald-500 flex-shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="font-mono text-[12px] font-medium text-stone-900">{p.dn}</div>
                  <div className="text-[11px] text-stone-500">{p.customer} · {p.awb}</div>
                </div>
                {(p.sla === "late" || p.sla === "atrisk") && <SlaBadge sla={p.sla} size="sm" />}
                <span className="text-[12px] font-semibold text-stone-800 tabular-nums">{window.fmtMAD(p.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* cutoff + close */}
      <div className="space-y-3">
        <div className="bg-gradient-to-br from-amber-50 to-white rounded-xl ring-1 ring-amber-200/70 p-4">
          <div className="flex items-center gap-2 text-amber-700"><I.Clock width={16} height={16} /><span className="text-[12px] font-semibold uppercase tracking-wide">{t("pc.cutoffIn")}</span></div>
          <div className="text-[34px] font-bold text-stone-900 tabular-nums mt-1.5 leading-none">1h 40m</div>
          <div className="text-[11.5px] text-stone-500 mt-1">{t("c.cutoff")} {M.cutoff} · pickup {M.window}</div>
          {atRisk > 0 && (
            <div className="mt-3 rounded-lg bg-white ring-1 ring-amber-200/60 px-3 py-2 flex items-center gap-2 text-[12px] text-amber-800">
              <I.AlertCircle width={14} height={14} className="text-amber-500" />{atRisk} parcel{atRisk>1?"s":""} at risk of missing cutoff
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
          <div className="space-y-1.5 text-[12.5px]">
            <Row k={t("c.parcels")} v={parcels} />
            <Row k={t("c.value")} v={`${window.fmtMAD(value)} MAD`} />
            <Row k={t("c.carrier")} v={D.CARRIER} />
          </div>
          <Button variant="success" size="lg" icon={I.CheckCircle} className="w-full" onClick={() => askConfirm?.({ title: t("c.handToCarrier") + "?", body: `${M.no} · ${parcels} ${t("c.parcels")} · ${window.fmtMAD(value)} MAD will be submitted as a Shipment to ${D.CARRIER}.`, confirmLabel: t("c.handToCarrier"), onConfirm: () => onToast?.({ type: "success", text: `${M.no} closed · Shipment submitted to ${D.CARRIER}` }) })}>{t("c.handToCarrier")}</Button>
        </div>
      </div>
    </div>
  );
}
