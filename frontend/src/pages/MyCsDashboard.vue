<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1000px] mx-auto">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('md.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">{{ t('mdc.intro') }}</p>
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
          <div class="md-kpi-l"><Icon name="check-circle" :size="12" class="inline -mt-px me-1" />{{ t('mdc.kResolved') }}</div>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-[26px] font-extrabold tabular-nums text-stone-900">{{ nResolved }}</span>
            <span v-if="deltas.resolved" class="md-delta" :class="deltas.resolved.up ? 'md-up' : 'md-down'">{{ deltas.resolved.txt }}</span>
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ d.acts.reply }} {{ t('mdc.replies') }}</div>
        </div>
        <div class="md-kpi md-in flex items-center gap-3" style="animation-delay: 70ms">
          <div class="relative w-[64px] h-[64px] flex-shrink-0">
            <svg viewBox="0 0 64 64" class="w-full h-full -rotate-90">
              <circle cx="32" cy="32" r="26" fill="none" stroke="rgb(231 229 228)" stroke-width="7" />
              <circle cx="32" cy="32" r="26" fill="none" stroke-width="7" stroke-linecap="round"
                      :stroke="d.res24Pct === null ? 'rgb(214 211 209)' : d.res24Pct >= 70 ? 'rgb(16 185 129)' : 'rgb(244 63 94)'"
                      :stroke-dasharray="163.4" :stroke-dashoffset="163.4 - (163.4 * (d.res24Pct || 0)) / 100"
                      style="transition: stroke-dashoffset .7s ease" />
            </svg>
            <span class="absolute inset-0 flex items-center justify-center text-[15px] font-extrabold tabular-nums"
                  :class="d.res24Pct === null ? 'text-stone-300' : d.res24Pct >= 70 ? 'text-emerald-600' : 'text-rose-600'">
              {{ d.res24Pct === null ? '—' : d.res24Pct + '%' }}</span>
          </div>
          <div class="min-w-0">
            <div class="md-kpi-l">{{ t('mdc.k24h') }}</div>
            <div class="text-[10px] text-stone-400 mt-0.5">{{ t('mdc.k24hHint') }}<span v-if="deltas.res24" class="md-delta ms-1" :class="deltas.res24.up ? 'md-up' : 'md-down'">{{ deltas.res24.txt }}</span></div>
          </div>
        </div>
        <div class="md-kpi md-in" style="animation-delay: 140ms">
          <div class="md-kpi-l"><Icon name="clock" :size="12" class="inline -mt-px me-1" />{{ t('mdc.kAvgRes') }}</div>
          <div class="text-[26px] font-extrabold tabular-nums mt-1"
               :class="d.avgResH === null ? 'text-stone-300' : d.avgResH <= 24 ? 'text-emerald-600' : 'text-amber-600'">
            {{ d.avgResH === null ? '—' : d.avgResH + 'h' }}
          </div>
          <div class="text-[11px] text-stone-400">{{ t('mdc.kAvgResHint') }}</div>
        </div>
        <div class="md-kpi md-in" style="animation-delay: 210ms">
          <div class="md-kpi-l"><Icon name="message-circle" :size="12" class="inline -mt-px me-1" />{{ t('mdc.kOpen') }}</div>
          <div class="text-[26px] font-extrabold tabular-nums mt-1"
               :class="d.openNow ? 'text-amber-600' : 'text-emerald-600'">{{ d.openNow }}</div>
          <div class="text-[11px] text-stone-400">{{ t('mdc.kOpenHint') }}</div>
        </div>
      </div>

      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-3">
          <Icon name="trending-up" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('mdc.dailyTitle') }}</span>
          <span class="ms-auto flex items-center gap-3 text-[10.5px] text-stone-500">
            <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-400 me-1" />{{ t('mdc.lgResolve') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-sky-400 me-1" />{{ t('mdc.lgReply') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-stone-300 me-1" />{{ t('mdc.lgOther') }}</span>
          </span>
        </div>
        <div v-if="(d.daily || []).length" class="flex items-end gap-1 h-[110px]">
          <div v-for="(f, fi) in d.daily" :key="f.date" class="flex-1 flex flex-col items-center gap-0.5 min-w-0"
               :title="`${f.date} · ${f.resolve} / ${f.reply} / ${f.other}`">
            <div class="w-full max-w-[26px] flex flex-col justify-end rounded-t overflow-hidden md-bar"
                 :style="{ height: '92px', animationDelay: Math.min(fi * 30, 600) + 'ms' }">
              <div class="w-full bg-stone-300" :style="{ height: fH(f.other) }" />
              <div class="w-full bg-sky-400" :style="{ height: fH(f.reply) }" />
              <div class="w-full bg-emerald-400" :style="{ height: fH(f.resolve) }" />
            </div>
            <span class="text-[8.5px] text-stone-400 tabular-nums">{{ f.date.slice(8) }}</span>
          </div>
        </div>
        <div v-else class="text-center text-[12px] text-stone-400 py-8">{{ t('ccd.noData') }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
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
      api("tickets.my_report", { frm: f, to: t2 }),
      api("tickets.my_report", { frm: pf, to: pt }).catch(() => null),
    ]);
    if (seq !== seqN) return;
    d.value = cur; dp.value = prev;
    loadError.value = "";
  } catch (e) {
    if (seq === seqN && !d.value) loadError.value = String(e.message || e);
  } finally {
    if (seq === seqN) loading.value = false;
  }
}
onMounted(load);

const nResolved = useCountUp(computed(() => d.value?.resolved || 0));
const deltas = computed(() => {
  if (!dp.value) return {};
  return {
    resolved: deltaOf(d.value?.resolved, dp.value?.resolved),
    res24: deltaOf(d.value?.res24Pct, dp.value?.res24Pct, true),
  };
});
const fMax = computed(() =>
  Math.max(1, ...(d.value?.daily || []).map((f) => (f.resolve || 0) + (f.reply || 0) + (f.other || 0))));
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
