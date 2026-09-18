<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1000px] mx-auto">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('md.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">{{ t('mdt.intro') }}</p>
      </div>
      <div class="flex items-center gap-0.5 bg-white ring-1 ring-stone-200/80 rounded-xl p-1">
        <button v-for="rk in RANGES" :key="rk"
                class="h-8 px-3 rounded-lg text-[12px] font-semibold transition-colors"
                :class="range === rk ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100'"
                @click="range = rk; load()">{{ t('ccd.r_' + rk) }}</button>
      </div>
    </header>

    <div v-if="loading && !d" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <span v-for="n in 4" :key="n" class="h-[104px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="loadError" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('cf.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <template v-else-if="d">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="md-kpi md-in" style="animation-delay: 0ms">
          <div class="md-kpi-l"><Icon name="activity" :size="12" class="inline -mt-px me-1" />{{ t('ccd.kDecisions') }}</div>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-[26px] font-extrabold tabular-nums text-stone-900">{{ nTotal }}</span>
            <span v-if="deltas.total" class="md-delta" :class="deltas.total.up ? 'md-up' : 'md-down'">{{ deltas.total.txt }}</span>
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ d.acts.dna }} {{ t('cf.actDna') }}</div>
        </div>
        <div class="md-kpi md-in flex items-center gap-3" style="animation-delay: 70ms">
          <div class="relative w-[64px] h-[64px] flex-shrink-0">
            <svg viewBox="0 0 64 64" class="w-full h-full -rotate-90">
              <circle cx="32" cy="32" r="26" fill="none" stroke="rgb(231 229 228)" stroke-width="7" />
              <circle cx="32" cy="32" r="26" fill="none" stroke-width="7" stroke-linecap="round"
                      :stroke="d.saveRate === null ? 'rgb(214 211 209)' : d.saveRate >= 50 ? 'rgb(16 185 129)' : 'rgb(244 63 94)'"
                      :stroke-dasharray="163.4" :stroke-dashoffset="163.4 - (163.4 * (d.saveRate || 0)) / 100"
                      style="transition: stroke-dashoffset .7s ease" />
            </svg>
            <span class="absolute inset-0 flex items-center justify-center text-[15px] font-extrabold tabular-nums"
                  :class="d.saveRate === null ? 'text-stone-300' : d.saveRate >= 50 ? 'text-emerald-600' : 'text-rose-600'">
              {{ d.saveRate === null ? '—' : d.saveRate + '%' }}</span>
          </div>
          <div class="min-w-0">
            <div class="md-kpi-l">{{ t('mdt.kSaveRate') }}</div>
            <div class="text-[11.5px] tabular-nums mt-1"><span class="text-emerald-600 font-bold">{{ d.acts.redeliver + d.acts.reship }}</span> <span class="text-stone-400">/</span> <span class="text-rose-500 font-bold">{{ d.acts.returnreq + d.acts.cancel }}</span></div>
            <div class="text-[10px] text-stone-400 mt-0.5">{{ t('mdt.kSaveHint') }}<span v-if="deltas.save" class="md-delta ms-1" :class="deltas.save.up ? 'md-up' : 'md-down'">{{ deltas.save.txt }}</span></div>
          </div>
        </div>
        <!-- Measured against the SAVES, never against every order touched:
             the agent's own return requests can't be delivered, and with
             them in the denominator a real week read 3 of 113. -->
        <div class="md-kpi md-in" style="animation-delay: 140ms">
          <div class="md-kpi-l"><Icon name="package-check" :size="12" class="inline -mt-px me-1" />{{ t('mdt.kDelivered') }}</div>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-[26px] font-extrabold tabular-nums text-emerald-600">{{ nLanded }}</span>
            <span v-if="deltas.delivered" class="md-delta" :class="deltas.delivered.up ? 'md-up' : 'md-down'">{{ deltas.delivered.txt }}</span>
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ t('mdt.kDeliveredHint').replace('{n}', String(saved.n)) }}</div>
          <div v-if="saved.open || saved.failed" class="text-[10.5px] tabular-nums mt-1 flex flex-wrap gap-x-2">
            <span v-if="saved.open" class="text-sky-600">{{ t('mdt.kStillOut').replace('{n}', String(saved.open)) }}</span>
            <span v-if="saved.failed" class="text-rose-500">{{ t('mdt.kFellAgain').replace('{n}', String(saved.failed)) }}</span>
          </div>
        </div>
        <div class="md-kpi md-in" style="animation-delay: 210ms">
          <div class="md-kpi-l"><Icon name="rotate-ccw" :size="12" class="inline -mt-px me-1" />{{ t('mdt.kBack') }}</div>
          <div class="text-[26px] font-extrabold tabular-nums text-stone-900 mt-1">{{ d.acts.returnreq + d.acts.cancel }}</div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ d.acts.returnreq }} {{ t('rs.actReturn') }} · {{ d.acts.cancel }} {{ t('cf.actCancel') }}</div>
        </div>
      </div>

      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-3">
          <Icon name="trending-up" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('mdt.dailyTitle') }}</span>
          <span class="ms-auto flex items-center gap-3 text-[10.5px] text-stone-500">
            <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-400 me-1" />{{ t('mdt.lgSave') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-amber-300 me-1" />{{ t('cf.actDna') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-rose-400 me-1" />{{ t('mdt.lgBack') }}</span>
          </span>
        </div>
        <div v-if="(d.daily || []).length" class="flex items-end gap-1 h-[110px]">
          <div v-for="(f, fi) in d.daily" :key="f.date" class="flex-1 flex flex-col items-center gap-0.5 min-w-0"
               :title="`${f.date} · ${f.save} / ${f.dna} / ${f.back}`">
            <div class="w-full max-w-[26px] flex flex-col justify-end rounded-t overflow-hidden md-bar"
                 :style="{ height: '92px', animationDelay: Math.min(fi * 30, 600) + 'ms' }">
              <div class="w-full bg-rose-400" :style="{ height: fH(f.back) }" />
              <div class="w-full bg-amber-300" :style="{ height: fH(f.dna) }" />
              <div class="w-full bg-emerald-400" :style="{ height: fH(f.save) }" />
            </div>
            <span class="text-[8.5px] text-stone-400 tabular-nums">{{ f.date.slice(8) }}</span>
          </div>
        </div>
        <div v-else class="text-center text-[12px] text-stone-400 py-8">{{ t('ccd.noData') }}</div>
      </div>

      <!-- The work itself. The cards above count; this remembers — an agent
           who made 223 decisions in three days could not answer "what did I
           do on this customer, and did it work?" until this existed. -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 flex-wrap mb-1">
          <Icon name="notebook-pen" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('mdt.logTitle') }}</span>
          <span v-if="log.total" class="text-[11px] text-stone-400 tabular-nums">{{ log.total }}</span>
          <div class="ms-auto flex items-center gap-0.5 bg-stone-100/70 rounded-lg p-0.5">
            <button v-for="a in LOG_FILTERS" :key="a.k"
                    class="h-7 px-2.5 rounded-md text-[11px] font-semibold transition-colors"
                    :class="logAct === a.k ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500 hover:text-stone-800'"
                    @click="logAct = a.k; loadLog()">{{ t(a.label) }}</button>
          </div>
        </div>
        <p class="text-[11px] text-stone-400 mb-3">{{ t('mdt.logHint') }}</p>

        <div v-if="logLoading && !log.rows.length" class="space-y-1.5">
          <span v-for="n in 5" :key="n" class="block h-12 rounded-lg bg-stone-100 animate-pulse" />
        </div>
        <div v-else-if="!log.rows.length" class="text-center text-[12px] text-stone-400 py-8">{{ t('mdt.logEmpty') }}</div>
        <ul v-else class="divide-y divide-stone-100">
          <li v-for="(r, i) in log.rows" :key="r.at + r.order + i"
              class="py-2 flex items-center gap-2.5 flex-wrap">
            <span class="text-[10.5px] text-stone-400 tabular-nums w-[84px] shrink-0" dir="ltr">{{ local(r.at).slice(5, 16) }}</span>
            <span class="text-[10.5px] font-bold rounded-full px-2 py-0.5 shrink-0" :class="ACT_CLS[r.action] || 'text-stone-600 bg-stone-100'">{{ ACT_LBL[r.action] ? t(ACT_LBL[r.action]) : r.action }}</span>
            <!-- Shopify order names carry a leading '#'; unstripped it ends
                 the URL path and the link lands nowhere. -->
            <RouterLink :to="{ name: 'OrderDetail', params: { name: String(r.order).replace('#', '') } }"
                        class="text-[12px] font-semibold text-stone-800 hover:text-[var(--accent-600)] truncate max-w-[150px]" dir="ltr">{{ r.order }}</RouterLink>
            <span class="text-[11.5px] text-stone-500 truncate max-w-[150px]">{{ r.customer }}</span>
            <span v-if="r.city" class="text-[10.5px] text-stone-400 truncate max-w-[90px]">{{ r.city }}</span>
            <span v-if="r.note" class="text-[10.5px] text-stone-500 italic truncate max-w-[180px]">{{ r.note }}</span>
            <span class="ms-auto flex items-center gap-2 shrink-0">
              <span class="text-[11px] tabular-nums text-stone-400">{{ Math.round(r.total) }}</span>
              <span class="text-[10.5px] font-bold rounded-full px-2 py-0.5" :class="OUT_CLS[r.outcome]">{{ t(OUT_LBL[r.outcome]) }}</span>
            </span>
          </li>
        </ul>
        <button v-if="log.rows.length < log.total" :disabled="logLoading"
                class="mt-3 w-full h-9 rounded-lg text-[12px] font-semibold text-stone-700 bg-stone-100 hover:bg-stone-200 disabled:opacity-50"
                @click="loadLog(true)">{{ t('mdt.logMore') }}</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { RANGES, windowFor, prevWindowFor, deltaOf, useCountUp } from "@/composables/useRangeDash";

const { t } = useI18n();
const d = ref(null);
const dp = ref(null);
const loading = ref(true);
const loadError = ref("");
const range = ref("7d");

let seqN = 0;
async function load() {
  const seq = ++seqN;
  loading.value = true;
  try {
    const [f, t2] = windowFor(range.value);
    const [pf, pt] = prevWindowFor(range.value);
    const [cur, prev] = await Promise.all([
      api("rescue.my_report", { frm: f, to: t2 }),
      api("rescue.my_report", { frm: pf, to: pt }).catch(() => null),
    ]);
    if (seq !== seqN) return;
    d.value = cur; dp.value = prev;
    loadError.value = "";
  } catch (e) {
    if (seq === seqN && !d.value) loadError.value = String(e.message || e);
  } finally {
    if (seq === seqN) loading.value = false;
  }
  loadLog();
}
onMounted(load);

// ── the work log ──────────────────────────────────────────────────────────
const LOG_FILTERS = [
  { k: "", label: "mdt.logAll" },
  { k: "redeliver", label: "rs.actRedeliver" },
  { k: "dna", label: "cf.actDna" },
  { k: "returnreq", label: "rs.actReturn" },
  { k: "cancel", label: "cf.actCancel" },
];
const ACT_LBL = {
  redeliver: "rs.actRedeliver", reship: "rs.actReship",
  returnreq: "rs.actReturn", dna: "cf.actDna",
  cancel: "cf.actCancel", resolve: "rs.actResolved",
};
const ACT_CLS = {
  redeliver: "text-emerald-700 bg-emerald-50", reship: "text-violet-700 bg-violet-50",
  returnreq: "text-amber-700 bg-amber-50", dna: "text-sky-700 bg-sky-50",
  cancel: "text-rose-700 bg-rose-50", resolve: "text-stone-600 bg-stone-100",
};
const OUT_LBL = {
  landed: "mdt.oLanded", open: "mdt.oOpen", failed: "mdt.oFailed",
  closed: "mdt.oClosed", retry: "mdt.oRetry",
};
const OUT_CLS = {
  landed: "text-emerald-700 bg-emerald-50", open: "text-sky-700 bg-sky-50",
  failed: "text-rose-700 bg-rose-50", closed: "text-stone-500 bg-stone-100",
  retry: "text-amber-700 bg-amber-50",
};
const PAGE = 40;
const log = ref({ rows: [], total: 0 });
const logLoading = ref(false);
const logAct = ref("");

let logSeq = 0;
async function loadLog(more = false) {
  const seq = ++logSeq;
  logLoading.value = true;
  try {
    const [f, t2] = windowFor(range.value);
    const res = await api("rescue.my_log", {
      frm: f, to: t2, action: logAct.value,
      limit: PAGE, offset: more ? log.value.rows.length : 0,
    });
    if (seq !== logSeq) return;
    log.value = more
      ? { rows: [...log.value.rows, ...(res.rows || [])], total: res.total || 0 }
      : { rows: res.rows || [], total: res.total || 0 };
  } catch (_) {
    // The log is the detail behind the cards, never the reason the page
    // fails to render — the numbers above still stand on their own.
    if (seq === logSeq && !more) log.value = { rows: [], total: 0 };
  } finally {
    if (seq === logSeq) logLoading.value = false;
  }
}

const total = computed(() =>
  Object.values(d.value?.acts || {}).reduce((a, b) => a + (b || 0), 0));
const nTotal = useCountUp(total);
// A backend that predates the save-outcome split still answers the old
// shape; fall back to it rather than rendering zeros.
const saved = computed(() => d.value?.saved
  || { n: d.value?.acted || 0, landed: d.value?.deliveredAfter || 0, open: 0, failed: 0 });
const nLanded = useCountUp(computed(() => saved.value.landed || 0));
function totalOf(rep) {
  return Object.values(rep?.acts || {}).reduce((a, b) => a + (b || 0), 0);
}
const deltas = computed(() => {
  if (!dp.value) return {};
  return {
    total: deltaOf(total.value, totalOf(dp.value)),
    save: deltaOf(d.value?.saveRate, dp.value?.saveRate, true),
    delivered: deltaOf(saved.value.landed, dp.value?.saved?.landed ?? dp.value?.deliveredAfter),
  };
});
const fMax = computed(() =>
  Math.max(1, ...(d.value?.daily || []).map((f) => (f.save || 0) + (f.dna || 0) + (f.back || 0))));
function fH(n) { return Math.round(((n || 0) * 92) / fMax.value) + "px"; }
</script>

<style scoped>
.md-kpi { background: white; border-radius: 16px; padding: 16px; box-shadow: inset 0 0 0 1px rgb(231 229 228 / .7); }
.md-kpi-l { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; color: rgb(168 162 158); }
.md-delta { font-size: 10.5px; font-weight: 700; border-radius: 9999px; padding: 1px 7px; }
.md-up { color: rgb(5 150 105); background: rgb(209 250 229 / .7); }
.md-down { color: rgb(190 18 60); background: rgb(255 228 230 / .8); }
.md-in { opacity: 0; animation: md-rise .45s cubic-bezier(.2, .7, .3, 1) forwards; }
@keyframes md-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.md-bar { transform: scaleY(0); transform-origin: bottom; animation: md-grow .5s cubic-bezier(.2, .7, .3, 1) forwards; }
@keyframes md-grow { to { transform: scaleY(1); } }
</style>
