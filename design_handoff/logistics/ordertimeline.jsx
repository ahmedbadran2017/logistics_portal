/* global React, I, Badge, IconButton, Button, StageBadge, SlaBadge, TrackBadge, ChannelBadge */
const { useMemo } = React;

// ─────────────────────────────────────────────────────────────────────
// ORDER FULL-CYCLE TIMELINE — the ERPNext doc trail behind one order.
// Sales Order → Pick List → Label → Manifest → Carrier → Delivered/Return.
// ─────────────────────────────────────────────────────────────────────
function OrderTimelineDrawer({ orderNo, onClose, dir }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const o = useMemo(() => D.ORDERS.find((x) => x.no === orderNo), [orderNo]);
  if (!o) return null;
  const events = D.orderTimeline(o);
  const side = dir === "rtl" ? "left-0" : "right-0";
  const anim = dir === "rtl" ? "animate-[drawerInL_.28s_cubic-bezier(.16,1,.3,1)]" : "animate-drawer-in";
  const c = D.CHANNELS[o.channel];

  return (
    <div className="fixed inset-0 z-[140]">
      <div className="absolute inset-0 bg-stone-900/25 backdrop-blur-[1px] animate-fade-in" onClick={onClose} />
      <div className={`absolute top-0 ${side} h-full w-full max-w-[480px] bg-stone-50 shadow-[0_0_60px_-10px_rgba(0,0,0,0.3)] flex flex-col ${anim}`} dir={dir}>
        {/* header */}
        <header className="bg-white border-b border-stone-200/70 px-4 py-3.5 flex-shrink-0">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[15px] font-bold text-stone-900">{o.no}</span>
                <ChannelBadge channel={o.channel} />
              </div>
              <div className="text-[12.5px] text-stone-600 mt-0.5">{o.customer}{o.city ? ` · ${o.city}` : ""} · <span className="font-semibold text-stone-900 tabular-nums">{window.fmtMAD(o.total)} MAD</span> · {o.items} {t("c.items")}</div>
            </div>
            <IconButton icon={I.X} onClick={onClose} />
          </div>
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <StageBadge stage={o.stage} />
            <SlaBadge sla={o.sla} />
            <Badge tone="neutral">{o.zone}</Badge>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* key facts */}
          <div className="grid grid-cols-2 gap-2">
            <Fact label={t("c.items")} value={o.items} />
            <Fact label={t("c.picker")} value={o.picker ? D.byId(o.picker).short : "—"} />
            <Fact label={t("c.bin")} value={o.bin} mono />
            <Fact label="AWB" value={o.awb || "—"} mono />
          </div>

          {/* timeline */}
          <div className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400 mb-3">{t("c.timeline")}</div>
            <ol className="relative">
              {events.map((e, i) => {
                const last = i === events.length - 1;
                return (
                  <li key={e.key} className="relative flex gap-3 pb-4 last:pb-0">
                    {!last && <span className={`absolute top-5 w-px ${e.bad ? "bg-rose-200" : "bg-emerald-200"}`} style={dir === "rtl" ? { right: 9 } : { left: 9 }} aria-hidden="true" />}
                    <span className={`relative z-10 w-[19px] h-[19px] rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${e.bad ? "bg-rose-500 text-white" : "bg-emerald-500 text-white"}`}>
                      {e.bad ? <I.AlertCircle width={11} height={11} /> : <I.Check width={11} height={11} />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className={`text-[13px] font-medium truncate ${e.bad ? "text-rose-700" : "text-stone-900"}`}>{e.label}</span>
                        <span className="text-[11px] text-stone-400 tabular-nums flex-shrink-0">{e.at}</span>
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[11.5px] text-stone-500 truncate min-w-0">{e.actor}</span>
                        {e.doc && <span className="font-mono text-[10.5px] text-stone-400 bg-stone-50 ring-1 ring-stone-200/70 rounded px-1 py-px flex-shrink-0">{e.doc}</span>}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>

          {/* carrier */}
          {o.awb && (
            <div className="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[12.5px] font-semibold text-stone-900">{o.carrier || D.CARRIER}</span>
                {o.track && <TrackBadge state={o.track} />}
              </div>
              <div className="flex items-center justify-between text-[12px]">
                <span className="text-stone-400">AWB</span>
                <span className="font-mono font-medium text-stone-800">{o.awb}</span>
              </div>
              {o.dn && <div className="flex items-center justify-between text-[12px] mt-1">
                <span className="text-stone-400">Delivery Note</span>
                <span className="font-mono font-medium text-stone-800">{o.dn}</span>
              </div>}
            </div>
          )}

          {/* actions */}
          <div className="flex items-center gap-2">
            {o.stage === "exception" && <Button variant="danger" size="md" icon={I.Phone} className="flex-1">Escalate to carrier</Button>}
            {o.stage === "oos" && <Button variant="danger" size="md" icon={I.Layers} className="flex-1">Reassign picker</Button>}
            <Button variant="secondary" size="md" iconRight={I.External} className="flex-1">{t("c.openInErp")}</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
window.OrderTimelineDrawer = OrderTimelineDrawer;

function Fact({ label, value, mono }) {
  return (
    <div className="bg-white rounded-lg ring-1 ring-stone-200/70 px-3 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">{label}</div>
      <div className={`text-[13px] font-medium text-stone-900 mt-0.5 truncate ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}
