<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1240px] mx-auto">
    <header class="sh-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-start justify-between gap-5 flex-wrap">
        <div class="flex items-center gap-3.5 min-w-0">
          <span class="sh-hero-icon"><Icon name="award" :size="22" /></span>
          <div class="min-w-0">
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('oclk.trTitle') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5 max-w-[620px]">{{ t('oclk.trIntro') }}</p>
          </div>
        </div>
        <div v-if="d" class="flex items-stretch gap-2 flex-wrap">
          <div class="sh-stat"><span class="sh-stat-n text-stone-900">{{ d.totals.total }}</span><span class="sh-stat-l">{{ t('oclk.trActions') }}</span></div>
          <div class="sh-stat" :title="t('oclk.trSavedHint')">
            <span class="sh-stat-n" :class="pctCls(d.outcomes.savedOk, d.outcomes.saved)">{{ pct(d.outcomes.savedOk, d.outcomes.saved) }}</span>
            <span class="sh-stat-l">{{ t('oclk.trSavedRate') }}</span>
          </div>
          <div class="sh-stat" :title="t('oclk.trChasedHint')">
            <span class="sh-stat-n" :class="pctCls(d.outcomes.chasedOk, d.outcomes.chased)">{{ pct(d.outcomes.chasedOk, d.outcomes.chased) }}</span>
            <span class="sh-stat-l">{{ t('oclk.trChasedRate') }}</span>
          </div>
          <div class="sh-stat"><span class="sh-stat-n text-stone-900">{{ d.members.length }}</span><span class="sh-stat-l">{{ t('oclk.trActive') }}</span></div>
        </div>
      </div>
    </header>

    <!-- the window -->
    <div class="flex items-center gap-2 flex-wrap">
      <div class="sh-seg">
        <button v-for="n in [1, 7, 14, 30]" :key="n" class="sh-seg-btn" :class="days === n ? 'sh-seg-on' : ''" :aria-pressed="days === n" @click="setDays(n)">
          {{ n === 1 ? t('oclk.today') : n + t('oclk.dShort') }}
        </button>
      </div>
      <span v-if="d" class="text-[11px] text-stone-400 tabular-nums" dir="ltr">{{ d.since }} → {{ d.until }}</span>
    </div>

    <div v-if="loading && !d" class="space-y-2.5"><div v-for="n in 4" :key="n" class="h-[56px] rounded-2xl sh-shimmer" /></div>
    <div v-else-if="loadError && !d" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ loadError === 'lp:leadsOnly' ? t('srv.leadsOnly') : t('common.loadFail') }}</div>
      <div v-if="loadError !== 'lp:leadsOnly'" class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button v-if="loadError !== 'lp:leadsOnly'" class="mt-3 h-9 px-4 rounded-xl text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <template v-else-if="d">
      <!-- day by day: the team's rhythm -->
      <section v-if="d.daily.length > 1" class="sh-card rounded-2xl p-4">
        <div class="flex items-center justify-between mb-3">
          <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.trDaily') }}</span>
          <span class="flex items-center gap-3 text-[10.5px] text-stone-500">
            <span v-for="k in KINDS" :key="k.key" class="inline-flex items-center gap-1"><span class="w-2 h-2 rounded-sm" :class="k.bar" />{{ t('oclk.day_' + k.key) }}</span>
          </span>
        </div>
        <div class="flex items-end gap-1.5 h-[120px]" role="img" :aria-label="t('oclk.trDaily')">
          <div v-for="day in d.daily" :key="day.d" class="flex-1 min-w-0 flex flex-col items-center justify-end h-full" :title="day.d + ' · ' + day.total">
            <div class="w-full max-w-[38px] flex flex-col-reverse rounded-md overflow-hidden" :style="{ height: barH(day.total) }">
              <span v-for="k in KINDS" :key="k.key" :class="k.bar" :style="{ height: (day.total ? 100 * day[k.key] / day.total : 0) + '%' }" />
            </div>
            <span class="text-[9.5px] text-stone-400 tabular-nums mt-1 truncate w-full text-center" dir="ltr">{{ day.d.slice(5) }}</span>
          </div>
        </div>
      </section>

      <!-- every member: what they did, and what came of it -->
      <section class="sh-card rounded-2xl overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full min-w-[720px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('px.team.thMember') }}</th>
                <th v-for="k in KINDS" :key="k.key" class="text-end px-3 py-2.5 whitespace-nowrap">{{ t('oclk.day_' + k.key) }}</th>
                <th class="text-end px-3 py-2.5">{{ t('px.team.thTotal') }}</th>
                <th class="text-end px-3 py-2.5 whitespace-nowrap" :title="t('oclk.trSavedHint')">{{ t('oclk.trSavedRate') }}</th>
                <th class="text-end px-4 py-2.5 whitespace-nowrap" :title="t('oclk.trChasedHint')">{{ t('oclk.trChasedRate') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="(m, i) in d.members" :key="m.user" class="hover:bg-stone-50" :class="i === 0 ? 'bg-teal-50/40' : ''">
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2.5">
                    <span class="w-8 h-8 rounded-full grid place-items-center text-white text-[11px] font-semibold flex-shrink-0" :class="i === 0 ? 'bg-teal-600' : 'bg-stone-400'">{{ initials(m.name) }}</span>
                    <span class="text-[12.5px] font-semibold text-stone-900 truncate max-w-[220px]" dir="auto">{{ m.name }}</span>
                  </div>
                </td>
                <td v-for="k in KINDS" :key="k.key" class="px-3 py-2.5 text-end text-[12.5px] tabular-nums" :class="m[k.key] ? 'font-semibold text-stone-900' : 'text-stone-300'">{{ m[k.key] }}</td>
                <td class="px-3 py-2.5 text-end text-[12.5px] font-bold text-stone-900 tabular-nums">{{ m.total }}</td>
                <td class="px-3 py-2.5 text-end text-[12.5px] tabular-nums" :class="pctCls(m.savedOk, m.saved)">
                  <span v-if="m.saved">{{ pct(m.savedOk, m.saved) }} <span class="text-[10.5px] text-stone-400">{{ m.savedOk }}/{{ m.saved }}</span></span><span v-else class="text-stone-300">—</span>
                </td>
                <td class="px-4 py-2.5 text-end text-[12.5px] tabular-nums" :class="pctCls(m.chasedOk, m.chased)">
                  <span v-if="m.chased">{{ pct(m.chasedOk, m.chased) }} <span class="text-[10.5px] text-stone-400">{{ m.chasedOk }}/{{ m.chased }}</span></span><span v-else class="text-stone-300">—</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!d.members.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('oclk.teamQuiet') }}</div>
        </div>
      </section>
      <p class="text-[11px] text-stone-400">{{ t('oclk.trFoot') }}</p>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const KINDS = [
  { key: "chases", bar: "bg-orange-400" }, { key: "rescues", bar: "bg-teal-500" }, { key: "cities", bar: "bg-sky-400" },
  { key: "feedback", bar: "bg-violet-400" }, { key: "notes", bar: "bg-stone-300" },
];
const d = ref(null);
const days = ref(7);
const loading = ref(true);
const loadError = ref("");
async function load() {
  loading.value = true;
  try { d.value = await api("shipments.team_report", { days: days.value }); loadError.value = ""; }
  catch (e) { loadError.value = String(e?.message || e); }
  loading.value = false;
}
function setDays(n) { days.value = n; load(); }
function pct(ok, n) { return n ? Math.round(100 * ok / n) + "%" : "—"; }
function pctCls(ok, n) {
  if (!n) return "text-stone-400";
  const p = ok / n;
  return p >= 0.6 ? "text-emerald-600" : p >= 0.35 ? "text-amber-600" : "text-rose-600";
}
function barH(total) {
  const max = Math.max(1, ...(d.value?.daily || []).map((x) => x.total));
  return Math.max(4, Math.round(100 * total / max)) + "%";
}
function initials(name) {
  const p = String(name || "?").trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
}
onMounted(load);
</script>
