/* global React, I, Badge, Button, Panel, KpiCard, PageHead, Avatar */
const { useState } = React;

// ─────────────────────────────────────────────────────────────────────
// SLA & BONUS SETTINGS — edits the live engine; writes back to ERPNext
// (Logistics SLA Settings + Logistics Bonus Settings — Single doctypes)
// ─────────────────────────────────────────────────────────────────────
function LogisticsSettings({ onToast }) {
  const { t } = window.useLg();
  const D = window.LG_DATA;
  const B = window.LG_BONUS;
  const SLA = window.LG_SLA_SETTINGS;

  const initial = () => ({
    cutoff: SLA.cutoff, sameDayTarget: SLA.sameDayTarget, deliveryDays: SLA.deliveryDays,
    maxPick: SLA.maxPick, maxLabel: SLA.maxLabel, maxShip: SLA.maxShip,
    perPick: B.perPick, onTime: B.onTime, zeroErrorDay: B.zeroErrorDay, dailyTargetBonus: B.dailyTargetBonus,
    slaGate: B.slaGate, streakStepPct: B.streakStepPct, streakCapPct: B.streakCapPct,
    monthlyCap: B.monthlyCap, teamKicker: B.teamKicker, teamSameDayTarget: B.teamSameDayTarget,
  });
  const [s, setS] = useState(initial);
  const [synced, setSynced] = useState(true);
  const set = (k, v) => { setS((o) => ({ ...o, [k]: v })); setSynced(false); };

  function apply() {
    // write into the live engine so every screen recomputes
    Object.assign(B, {
      perPick: +s.perPick, onTime: +s.onTime, zeroErrorDay: +s.zeroErrorDay, dailyTargetBonus: +s.dailyTargetBonus,
      slaGate: +s.slaGate, streakStepPct: +s.streakStepPct, streakCapPct: +s.streakCapPct,
      monthlyCap: +s.monthlyCap, teamKicker: +s.teamKicker, teamSameDayTarget: +s.teamSameDayTarget,
    });
    Object.assign(SLA, { cutoff: s.cutoff, sameDayTarget: +s.sameDayTarget, deliveryDays: +s.deliveryDays, maxPick: +s.maxPick, maxLabel: +s.maxLabel, maxShip: +s.maxShip });
  }
  function save() {
    apply(); setSynced(true);
    onToast?.({ type: "success", text: `${t("set.synced")} · Logistics SLA Settings + Bonus Settings` });
  }
  function reset() { setS(initial()); apply(); setSynced(true); }

  // live preview — recompute a couple of pickers
  const preview = ["marouane", "asmaa", "said"].map((id) => {
    const m = D.TEAM_MEMBERS.find((x) => x.id === id);
    // temp-apply current form for preview
    const snapB = { ...window.LG_BONUS };
    Object.assign(window.LG_BONUS, { perPick: +s.perPick, onTime: +s.onTime, zeroErrorDay: +s.zeroErrorDay, dailyTargetBonus: +s.dailyTargetBonus, slaGate: +s.slaGate, streakStepPct: +s.streakStepPct, streakCapPct: +s.streakCapPct, monthlyCap: +s.monthlyCap });
    const b = window.computeBonus(m);
    Object.assign(window.LG_BONUS, snapB);
    return { m, b };
  });

  return (
    <div className="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
      <PageHead title={t("set.title")} sub={t("set.sub")}>
        <span className={`inline-flex items-center gap-1.5 text-[11.5px] font-medium px-2.5 h-8 rounded-lg ring-1 whitespace-nowrap ${synced ? "text-emerald-700 bg-emerald-50 ring-emerald-200" : "text-amber-700 bg-amber-50 ring-amber-200"}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${synced ? "bg-emerald-500" : "bg-amber-500"}`} />{synced ? `${t("set.synced")}` : "Unsaved changes"}
        </span>
        <Button variant="secondary" size="md" icon={I.Back} onClick={reset}>{t("set.reset")}</Button>
        <Button variant="brand" size="md" icon={I.Check} onClick={save} disabled={synced}>{t("set.save")}</Button>
      </PageHead>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        <div className="space-y-4">
          {/* SLA */}
          <Panel title={t("set.sla")} sub="Single doctype · Logistics SLA Settings" bodyClass="p-4">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <FieldNum label={t("set.cutoff")} value={s.cutoff} onChange={(v) => set("cutoff", v)} type="text" />
              <FieldNum label={t("set.sameDayTarget")} value={s.sameDayTarget} onChange={(v) => set("sameDayTarget", v)} unit="%" />
              <FieldNum label={t("set.deliveryDays")} value={s.deliveryDays} onChange={(v) => set("deliveryDays", v)} unit={t("set.days")} />
              <FieldNum label={t("set.maxPick")} value={s.maxPick} onChange={(v) => set("maxPick", v)} unit={t("set.hrs")} />
              <FieldNum label={t("set.maxLabel")} value={s.maxLabel} onChange={(v) => set("maxLabel", v)} unit={t("set.hrs")} />
              <FieldNum label={t("set.maxShip")} value={s.maxShip} onChange={(v) => set("maxShip", v)} unit={t("set.hrs")} />
            </div>
          </Panel>

          {/* Bonus */}
          <Panel title={t("set.bonus")} sub="Single doctype · Logistics Bonus Settings" bodyClass="p-4">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <FieldNum label={t("set.perPick")} value={s.perPick} onChange={(v) => set("perPick", v)} unit="MAD" />
              <FieldNum label={t("set.onTime")} value={s.onTime} onChange={(v) => set("onTime", v)} unit="MAD" />
              <FieldNum label={t("set.zeroError")} value={s.zeroErrorDay} onChange={(v) => set("zeroErrorDay", v)} unit="MAD" />
              <FieldNum label={t("set.targetBonus")} value={s.dailyTargetBonus} onChange={(v) => set("dailyTargetBonus", v)} unit="MAD" />
              <FieldNum label={t("set.slaGate")} value={s.slaGate} onChange={(v) => set("slaGate", v)} unit="%" />
              <FieldNum label={t("set.cap")} value={s.monthlyCap} onChange={(v) => set("monthlyCap", v)} unit="MAD" />
              <FieldNum label={t("set.streakStep")} value={s.streakStepPct} onChange={(v) => set("streakStepPct", v)} unit="%" />
              <FieldNum label={t("set.streakCap")} value={s.streakCapPct} onChange={(v) => set("streakCapPct", v)} unit="%" />
              <FieldNum label={t("set.kicker")} value={s.teamKicker} onChange={(v) => set("teamKicker", v)} unit="MAD" />
              <FieldNum label={t("set.kickerTarget")} value={s.teamSameDayTarget} onChange={(v) => set("teamSameDayTarget", v)} unit="%" />
            </div>
          </Panel>
        </div>

        {/* live preview */}
        <div className="space-y-4">
          <Panel title="Live preview" sub={t("set.preview")} bodyClass="p-3 space-y-2">
            {preview.map(({ m, b }) => (
              <div key={m.id} className="flex items-center gap-2.5 px-2 py-2 rounded-lg bg-stone-50/60">
                <Avatar name={D.byId(m.id).name} size={28} />
                <div className="min-w-0 flex-1">
                  <div className="text-[12.5px] font-medium text-stone-900 truncate">{D.byId(m.id).short}</div>
                  <div className="text-[10.5px] text-stone-500">{m.perf.sla}% SLA · {b && b.gatePass ? t("bn.unlocked") : t("bn.locked")}</div>
                </div>
                <div className="text-end"><div className="text-[13px] font-semibold text-stone-900 tabular-nums">{b ? window.fmtMAD(b.projected) : "—"}</div><div className="text-[9.5px] text-stone-400">MAD</div></div>
              </div>
            ))}
          </Panel>

          <div className="rounded-xl bg-white ring-1 ring-stone-200/70 p-4">
            <div className="flex items-center gap-2 mb-1.5"><I.Shield width={14} height={14} className="text-stone-400 flex-shrink-0" /><span className="text-[12px] font-semibold text-stone-900 whitespace-nowrap">Write-back</span></div>
            <p className="text-[11.5px] text-stone-500 leading-snug text-pretty">Saving syncs these thresholds to the <span className="font-medium text-stone-700">Logistics SLA Settings</span> and <span className="font-medium text-stone-700">Bonus Settings</span> single doctypes in ERPNext. The SLA scheduler and bonus job pick them up on the next run.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
window.LogisticsSettings = LogisticsSettings;

function FieldNum({ label, value, onChange, unit, type = "number" }) {
  return (
    <div>
      <div className="text-[11px] font-medium text-stone-500 mb-1">{label}</div>
      <div className="relative">
        <input type={type} value={value} onChange={(e) => onChange(e.target.value)}
          className="w-full h-9 px-3 pe-12 text-[13px] font-medium text-stone-900 bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none tabular-nums" />
        {unit && <span className="absolute end-3 top-1/2 -translate-y-1/2 text-[11px] text-stone-400 pointer-events-none">{unit}</span>}
      </div>
    </div>
  );
}
