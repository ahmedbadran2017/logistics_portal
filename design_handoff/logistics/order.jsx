/* global React, I, Badge, Button, IconButton, Panel, StageBadge, SlaBadge, TrackBadge, ChannelBadge, SlaRing, Avatar */
const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// ORDER DETAIL — full page (line items · address · payment · docs · cycle)
// ─────────────────────────────────────────────────────────────────────
function genLineItems(o) {
  const D = window.LG_DATA;
  const names = [
    ["MCH100013", "Diffuseur huile MCH — box", o.bin],
    ["CSM44021", "Sérum éclat 30ml", "I4A - JM"],
    ["ACC11008", "Trousse maquillage zip", "H14A - JM"],
    ["MUZ22014", "Palette ombres MU", "H13B - JM"],
  ];
  const n = Math.max(1, Math.min(o.items, 4));
  const per = Math.round(o.total / n);
  return Array.from({ length: n }).map((_, i) => {
    const [sku, name, bin] = names[i % names.length];
    const qty = i === 0 && n < o.items ? o.items - (n - 1) : 1;
    const price = i === n - 1 ? o.total - per * (n - 1) : per;
    return { sku, name, bin, qty, price: Math.max(1, Math.round(price / qty)), line: Math.max(1, price) };
  });
}

function OrderDetail({ no, onBack }) {
  const { t, dir } = window.useLg();
  const D = window.LG_DATA;
  const o = useMemo(() => D.ORDERS.find((x) => x.no === no), [no]);
  if (!o) return <div className="p-10 text-center text-stone-400">Order not found.</div>;
  const items = useMemo(() => genLineItems(o), [no]);
  const tl = D.orderTimeline(o);
  const slaPct = o.sla === "breached" ? 0.1 : o.sla === "atrisk" ? 0.35 : o.sla === "late" ? 0.25 : 0.8;
  // financial breakdown (mirrors Sales Order: net + shipping + tax − discount)
  const nseed = parseInt((o.no.match(/\d+/) || [12])[0]);
  const subtotal = items.reduce((a, it) => a + it.line, 0);
  const shipping = [0, 0, 25, 30][nseed % 4];
  const discount = nseed % 5 === 0 ? 20 : 0;
  const tax = Math.round((subtotal + shipping - discount) * 0.05);
  const grand = subtotal + shipping - discount + tax;
  const phone = `+212 6${String(nseed % 10)}${String(nseed * 7 % 90 + 10)} ${String(nseed * 13 % 900 + 100)}`;
  const govern = ["Casablanca-Settat", "Rabat-Salé-Kénitra", "Tanger-Tétouan", "Marrakech-Safi"][nseed % 4];
  const ref = `${o.channel === "shopify" ? "#" : o.channel === "youcan" ? "YC" : "REF"}${4400 + nseed % 600}`;
  const codPending = o.stage !== "delivered";

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap">
        <I.Back width={15} height={15} className="rtl:rotate-180" />{t("nav.orders")}
      </button>

      {/* header */}
      <div className="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-mono text-[20px] font-bold text-stone-900">{o.no}</h1>
              <ChannelBadge channel={o.channel} size="md" />
              <Badge tone="green" dot className="whitespace-nowrap">{t("od.salesConfirmed")}</Badge>
              <StageBadge stage={o.stage} /><SlaBadge sla={o.sla} />
            </div>
            <div className="text-[13px] text-stone-600 mt-1">{o.customer}{o.city ? ` · ${o.city}` : ""} · {o.zone}</div>
          </div>
          <div className="flex items-center gap-2">
            {o.stage === "oos" && <Button variant="danger" size="md" icon={I.Layers}>Reassign</Button>}
            {o.stage === "exception" && <Button variant="danger" size="md" icon={I.Phone}>Escalate</Button>}
            {o.awb && <Button variant="secondary" size="md" icon={I.Download} onClick={() => window.print()}>{t("c.print")} {t("od.label")}</Button>}
            <Button variant="secondary" size="md" iconRight={I.External}>{t("c.openInErp")}</Button>
          </div>
        </div>
      </div>

      {/* print-only AWB label */}
      {o.awb && (
        <div className="print-label" style={{ fontFamily: "monospace" }}>
          <div style={{ maxWidth: 360, border: "2px solid #000", borderRadius: 8, padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "2px dashed #000", paddingBottom: 8 }}>
              <strong style={{ fontSize: 18 }}>{o.carrier || D.CARRIER}</strong><span>AWB</span>
            </div>
            <div style={{ textAlign: "center", fontSize: 20, fontWeight: 700, letterSpacing: 2, margin: "14px 0" }}>{o.awb}</div>
            <div style={{ display: "flex", justifyContent: "center", gap: 2, height: 44, marginBottom: 12 }}>
              {Array.from({ length: 48 }).map((_, i) => <span key={i} style={{ width: i % 3 ? 2 : 3, height: "100%", background: i % 2 ? "#000" : "#fff" }} />)}
            </div>
            <div style={{ borderTop: "2px dashed #000", paddingTop: 8, fontSize: 12, lineHeight: 1.6 }}>
              <div><strong>Order:</strong> {o.no}</div>
              <div><strong>To:</strong> {o.customer} · {o.city || D.CITY}</div>
              <div><strong>From:</strong> {D.WAREHOUSE}</div>
              <div><strong>COD:</strong> {window.fmtMAD(o.total)} MAD · {o.items} {t("c.items")}</div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4">
        {/* LEFT */}
        <div className="space-y-4">
          <Panel title={t("od.items")} sub={`${o.items} ${t("c.items")}`} bodyClass="p-0">
            <table className="w-full">
              <thead><tr className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th className="text-start px-4 py-2.5">Product</th>
                <th className="text-start px-4 py-2.5 hidden sm:table-cell">{t("c.bin")}</th>
                <th className="text-end px-4 py-2.5">{t("c.qty")}</th>
                <th className="text-end px-4 py-2.5 hidden sm:table-cell">{t("od.unit")}</th>
                <th className="text-end px-4 py-2.5">{t("od.lineTotal")}</th>
              </tr></thead>
              <tbody className="divide-y divide-stone-100">
                {items.map((it, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5"><div className="flex items-center gap-2.5">
                      <span className="w-9 h-9 rounded-lg bg-stone-100 ring-1 ring-stone-200/70 flex items-center justify-center flex-shrink-0 overflow-hidden" style={{ backgroundImage: "repeating-linear-gradient(45deg, #f5f5f4 0 6px, #ececeb 6px 12px)" }}><I.Box width={15} height={15} className="text-stone-400" /></span>
                      <div className="min-w-0"><div className="text-[12.5px] font-medium text-stone-900 truncate max-w-[180px]">{it.name}</div><div className="font-mono text-[10.5px] text-stone-400">{it.sku}</div></div>
                    </div></td>
                    <td className="px-4 py-2.5 font-mono text-[11.5px] text-stone-500 hidden sm:table-cell">{it.bin}</td>
                    <td className="px-4 py-2.5 text-end text-[12.5px] font-medium text-stone-900 tabular-nums">{it.qty}</td>
                    <td className="px-4 py-2.5 text-end text-[12px] text-stone-500 tabular-nums hidden sm:table-cell">{window.fmtMAD(it.price)}</td>
                    <td className="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{window.fmtMAD(it.line)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot><tr className="border-t border-stone-100"><td className="px-4 pt-2.5 pb-0.5 text-[12px] text-stone-500" colSpan="4">{t("od.subtotal")}</td><td className="px-4 pt-2.5 pb-0.5 text-end text-[12px] text-stone-700 tabular-nums">{window.fmtMAD(subtotal)}</td></tr>
                <tr><td className="px-4 py-0.5 text-[12px] text-stone-500" colSpan="4">{t("od.shipping")}</td><td className="px-4 py-0.5 text-end text-[12px] text-stone-700 tabular-nums">{shipping ? window.fmtMAD(shipping) : "—"}</td></tr>
                {discount > 0 && <tr><td className="px-4 py-0.5 text-[12px] text-stone-500" colSpan="4">{t("od.discount")}</td><td className="px-4 py-0.5 text-end text-[12px] text-emerald-600 tabular-nums">−{window.fmtMAD(discount)}</td></tr>}
                <tr><td className="px-4 py-0.5 text-[12px] text-stone-500" colSpan="4">{t("od.tax")}</td><td className="px-4 py-0.5 text-end text-[12px] text-stone-700 tabular-nums">{window.fmtMAD(tax)}</td></tr>
                <tr className="border-t border-stone-200 bg-stone-50/60">
                <td className="px-4 py-2.5 text-[12.5px] font-semibold text-stone-700" colSpan="4">{t("od.grand")}</td>
                <td className="px-4 py-2.5 text-end text-[14px] font-bold text-stone-900 tabular-nums">{window.fmtMAD(grand)} <span className="text-[10px] font-normal text-stone-400">MAD</span></td>
              </tr></tfoot>
            </table>
          </Panel>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Panel title={t("od.shipTo")} bodyClass="p-4">
              <div className="text-[13px] font-medium text-stone-900">{o.customer}</div>
              <div className="space-y-1.5 mt-2 text-[12px]">
                <Row2 k={t("od.phone")} v={phone} />
                <Row2 k={t("c.zone")} v={(o.city || D.CITY) + " · " + o.zone.replace(" - JM", "")} />
                <Row2 k={t("od.govern")} v={govern} />
                <Row2 k={t("od.ref")} v={ref} />
              </div>
            </Panel>
            <Panel title={t("od.payment")} bodyClass="p-4">
              <div className="flex items-center gap-1.5"><I.Cash width={14} height={14} className="text-emerald-500" /><span className="text-[12.5px] font-medium text-stone-800">{t("od.cod")}</span></div>
              <div className="text-[20px] font-bold text-stone-900 tabular-nums mt-1.5">{window.fmtMAD(grand)} <span className="text-[11px] font-medium text-stone-400">MAD</span></div>
              <div className="flex items-center gap-1.5 mt-2">
                <ChannelBadge channel={o.channel} />
                <Badge tone={codPending ? "amber" : "green"} dot>{codPending ? t("od.codPending") : t("od.paid")}</Badge>
              </div>
            </Panel>
          </div>

          <Panel title={t("od.documents")} bodyClass="p-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {[[t("od.label"), I.Tag, !!o.awb], [t("od.packingSlip"), I.File, true], [t("od.invoice"), I.File, o.stage !== "pending"]].map(([label, Ic, on], i) => (
                <button key={i} disabled={!on} className={`flex items-center gap-2 px-3 py-2.5 rounded-lg ring-1 transition-all ${on ? "ring-stone-200 hover:ring-stone-300 text-stone-700" : "ring-stone-100 text-stone-300 cursor-not-allowed"}`}>
                  <Ic width={15} height={15} className={on ? "text-stone-400" : ""} /><span className="text-[12px] font-medium flex-1 text-start">{label}</span>{on && <I.Download width={13} height={13} className="text-stone-400" />}
                </button>
              ))}
            </div>
          </Panel>

          <Panel title={t("od.attachments")} sub={t("od.attachSub")} bodyClass="p-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-2">
              {[["POD_LD0077.jpg", "delivered"], ["invoice.pdf", null], ["parcel_photo.jpg", null]].filter((a) => o.stage !== "pending").map(([name, tag], i) => (
                <div key={i} className="rounded-lg ring-1 ring-stone-200 overflow-hidden">
                  <div className="h-16 flex items-center justify-center" style={{ backgroundImage: "repeating-linear-gradient(45deg, #f5f5f4 0 6px, #ececeb 6px 12px)" }}>
                    {name.endsWith(".pdf") ? <I.File width={18} height={18} className="text-stone-400" /> : <I.Box width={18} height={18} className="text-stone-400" />}
                  </div>
                  <div className="px-2 py-1.5 flex items-center gap-1"><span className="text-[10.5px] text-stone-600 truncate flex-1">{name}</span><I.Download width={11} height={11} className="text-stone-400 flex-shrink-0" /></div>
                </div>
              ))}
            </div>
            <button className="w-full flex items-center justify-center gap-2 h-16 rounded-lg ring-1 ring-dashed ring-stone-300 hover:ring-[var(--accent-400)] hover:bg-[var(--accent-50)]/30 text-[12px] font-medium text-stone-500 transition-all">
              <I.Upload width={15} height={15} />{t("od.dropFiles")}
            </button>
          </Panel>

          <window.OrderActivity o={o} />
        </div>

        {/* RIGHT */}
        <div className="space-y-4">          <Panel title={t("od.status")} right={<Badge tone="brand" dot>{o.picker ? D.byId(o.picker).short : t("c.unassigned")}</Badge>} bodyClass="p-4">
            {o.awb && <div className="mb-3"><SlaRing pct={slaPct} size={44} label={t("sla." + o.sla)} sub={o.mins ? `${o.mins} ${t("c.min")} ${t("c.left")}` : D.CARRIER} /></div>}
            <ol className="relative">
              {tl.map((e, i) => {
                const last = i === tl.length - 1;
                return (
                  <li key={e.key} className="relative flex gap-3 pb-3.5 last:pb-0">
                    {!last && <span className={`absolute top-5 w-px ${e.bad ? "bg-rose-200" : "bg-emerald-200"}`} style={dir === "rtl" ? { right: 9 } : { left: 9 }} />}
                    <span className={`relative z-10 w-[19px] h-[19px] rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${e.bad ? "bg-rose-500 text-white" : "bg-emerald-500 text-white"}`}>{e.bad ? <I.AlertCircle width={11} height={11} /> : <I.Check width={11} height={11} />}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2"><span className={`text-[12.5px] font-medium truncate ${e.bad ? "text-rose-700" : "text-stone-900"}`}>{e.label}</span><span className="text-[11px] text-stone-400 tabular-nums flex-shrink-0">{e.at}</span></div>
                      <div className="flex items-center gap-1.5 mt-0.5"><span className="text-[11px] text-stone-500 truncate min-w-0">{e.actor}</span>{e.doc && <span className="font-mono text-[10px] text-stone-400 bg-stone-50 ring-1 ring-stone-200/70 rounded px-1 flex-shrink-0">{e.doc}</span>}</div>
                    </div>
                  </li>
                );
              })}
            </ol>
          </Panel>

          {o.awb && (
            <Panel title={D.CARRIER} right={o.track && <TrackBadge state={o.track} />} bodyClass="p-4 space-y-1.5 text-[12px]">
              <Row2 k={t("od.trackNo")} v={o.awb} />
              <Row2 k="AWB" v={o.awb} />
              {o.dn && <Row2 k="Delivery Note" v={o.dn} />}
              <Row2 k={t("c.zone")} v={o.zone} />
              <button className="w-full mt-1 flex items-center justify-center gap-1.5 h-8 rounded-lg ring-1 ring-stone-200 hover:ring-stone-300 text-[12px] font-medium text-stone-700"><I.Globe width={13} height={13} />{t("rv.track")}</button>
            </Panel>
          )}

          {/* linked ERPNext documents — the real doc chain */}
          <Panel title={t("od.linked")} sub={t("od.docChain")} bodyClass="p-2">
            {(() => {
              const idx = D.STAGE_SEQ.indexOf(o.stage);
              const chain = [
                { dt: "Sales Order", id: o.no, on: true, ic: I.Orders },
                { dt: "Pick List", id: "PL-51433", on: idx >= 1, ic: I.Box },
                { dt: "Delivery Note", id: o.dn || "—", on: !!o.dn, ic: I.File },
                { dt: "Sales Invoice", id: o.dn ? "ACC-SINV-" + o.no.replace(/\D/g, "").slice(-4) : "—", on: idx >= 5, ic: I.Cash },
                { dt: "Shipment", id: idx >= 5 ? D.MANIFEST.no : "—", on: idx >= 5, ic: I.Send },
                { dt: "Payment Entry", id: o.stage === "delivered" ? "ACC-PAY-" + o.no.replace(/\D/g, "").slice(-4) : "—", on: o.stage === "delivered", ic: I.Wallet },
              ];
              return chain.map((c, i) => {
                const Ic = c.ic;
                return (
                  <button key={i} disabled={!c.on} className={`w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-start ${c.on ? "hover:bg-stone-50" : "opacity-40 cursor-not-allowed"}`}>
                    <span className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${c.on ? "bg-[var(--accent-50)] text-[var(--accent-700)]" : "bg-stone-100 text-stone-400"}`}><Ic width={13} height={13} /></span>
                    <div className="min-w-0 flex-1"><div className="text-[10px] text-stone-400 uppercase tracking-wide">{c.dt}</div><div className="font-mono text-[12px] font-medium text-stone-800 truncate">{c.id}</div></div>
                    {c.on && <I.External width={12} height={12} className="text-stone-300 flex-shrink-0" />}
                  </button>
                );
              });
            })()}
          </Panel>
        </div>
      </div>
    </div>
  );
}
window.OrderDetail = OrderDetail;
function Row2({ k, v }) { return <div className="flex items-center justify-between gap-2"><span className="text-stone-400">{k}</span><span className="font-mono font-medium text-stone-800 truncate">{v}</span></div>; }

// Activity log + add-note (ERPNext comment/version trail)
function OrderActivity({ o }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const idx = D.STAGE_SEQ.indexOf(o.stage);
  const pk = o.picker ? D.byId(o.picker).short : "Dispatcher";
  const base = [
    { who: "Sales · " + o.channel, act: "Order confirmed", at: "08:42", on: true },
    { who: "Anass", act: "Assigned to " + pk, at: "09:01", on: idx >= 1 },
    { who: pk, act: "Picking started", at: "09:08", on: idx >= 1 },
    { who: pk, act: "All items scanned", at: "09:25", on: idx >= 2 },
    { who: "Reda", act: "AWB generated · " + (o.awb || "—"), at: "09:46", on: idx >= 3 },
    { who: "Reda", act: "Added to manifest", at: "10:19", on: idx >= 5 },
    { who: "Cathedis", act: o.stage === "exception" ? "Delivery exception" : "Picked up", at: "10:37", on: idx >= 6, bad: o.stage === "exception" },
  ].filter((e) => e.on);
  const [notes, setNotes] = React.useState([]);
  const [draft, setDraft] = React.useState("");
  function post() {
    const txt = draft.trim(); if (!txt) return;
    const now = new Date();
    setNotes((n) => [{ who: t("od.you"), act: txt, at: `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}`, note: true }, ...n]);
    setDraft("");
  }
  const feed = [...notes, ...[...base].reverse()];
  return (
    <Panel title={t("od.activity")} sub={t("od.activitySub")} bodyClass="p-3">
      {/* note composer */}
      <div className="flex items-start gap-2 mb-3">
        <Avatar name="Supervisor" size={26} />
        <div className="flex-1 min-w-0">
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") post(); }}
            placeholder={t("od.addNote")} rows={2}
            className="w-full px-3 py-2 text-[12.5px] bg-stone-50 rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 focus:bg-white outline-none resize-none" />
          <div className="flex justify-end mt-1.5">
            <Button variant="brand" size="sm" icon={I.ArrowRight} disabled={!draft.trim()} onClick={post}>{t("od.post")}</Button>
          </div>
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
window.OrderActivity = OrderActivity;
