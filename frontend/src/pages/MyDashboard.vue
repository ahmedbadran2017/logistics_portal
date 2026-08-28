<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1000px] mx-auto">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('md.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">{{ t('md.intro') }}</p>
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
        <div class="md-kpi">
          <div class="md-kpi-l"><Icon name="activity" :size="12" class="inline -mt-px me-1" />{{ t('ccd.kDecisions') }}</div>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-[26px] font-extrabold tabular-nums text-stone-900">{{ total }}</span>
            <span v-if="deltas.total" class="md-delta" :class="deltas.total.up ? 'md-up' : 'md-down'">{{ deltas.total.txt }}</span>
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ d.acts.dna }} {{ t('cf.actDna') }} · {{ d.acts.followup }} {{ t('cf.actFollowup') }}</div>
        </div>
        <div class="md-kpi flex items-center gap-3">
          <div class="relative w-[64px] h-[64px] flex-shrink-0">
            <svg viewBox="0 0 64 64" class="w-full h-full -rotate-90">
              <circle cx="32" cy="32" r="26" fill="none" stroke="rgb(231 229 228)" stroke-width="7" />
              <circle cx="32" cy="32" r="26" fill="none" stroke-width="7" stroke-linecap="round"
                      :stroke="rate === null ? 'rgb(214 211 209)' : rate >= 50 ? 'rgb(16 185 129)' : 'rgb(244 63 94)'"
                      :stroke-dasharray="163.4" :stroke-dashoffset="163.4 - (163.4 * (rate || 0)) / 100"
                      style="transition: stroke-dashoffset .7s ease" />
            </svg>
            <span class="absolute inset-0 flex items-center justify-center text-[15px] font-extrabold tabular-nums"
                  :class="rate === null ? 'text-stone-300' : rate >= 50 ? 'text-emerald-600' : 'text-rose-600'">
              {{ rate === null ? '—' : rate + '%' }}</span>
          </div>
          <div class="min-w-0">
            <div class="md-kpi-l">{{ t('ccd.kRate') }}</div>
            <div class="text-[11.5px] tabular-nums mt-1"><span class="text-emerald-600 font-bold">{{ d.acts.confirm }}</span> <span class="text-stone-400">/</span> <span class="text-rose-500 font-bold">{{ d.acts.cancel }}</span></div>
            <div class="text-[10px] text-stone-400 mt-0.5"><span v-if="deltas.rate" class="md-delta" :class="deltas.rate.up ? 'md-up' : 'md-down'">{{ deltas.rate.txt }}</span></div>
          </div>
        </div>
        <div class="md-kpi">
          <div class="md-kpi-l"><Icon name="wallet" :size="12" class="inline -mt-px me-1" />{{ t('ccd.kValue') }}</div>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-[26px] font-extrabold tabular-nums text-stone-900">{{ fmtN(d.cohort.value) }}</span>
            <span v-if="deltas.value" class="md-delta" :class="deltas.value.up ? 'md-up' : 'md-down'">{{ deltas.value.txt }}</span>
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ fmtN(d.cohort.n) }} {{ t('md.myOrders') }}</div>
        </div>
        <div class="md-kpi">
          <div class="md-kpi-l"><Icon name="package-check" :size="12" class="inline -mt-px me-1" />{{ t('ccd.stickTitle') }}</div>
          <div class="text-[26px] font-extrabold tabular-nums mt-1"
               :class="stickPct === null ? 'text-stone-300' : stickPct >= 60 ? 'text-emerald-600' : stickPct >= 40 ? 'text-amber-600' : 'text-rose-600'">
            {{ stickPct === null ? '—' : stickPct + '%' }}
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ d.stick.delivered }} / {{ d.stick.shipped }} {{ t('md.deliveredOfShipped') }}</div>
        </div>
      </div>

      <!-- my daily decisions -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-3">
          <Icon name="trending-up" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('ccd.dailyTitle') }}</span>
          <span class="ms-auto flex items-center gap-3 text-[10.5px] text-stone-500">
            <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-400 me-1" />{{ t('cf.actConfirm') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-rose-400 me-1" />{{ t('cf.actCancel') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-amber-300 me-1" />{{ t('cf.actDna') }}</span>
          </span>
        </div>
        <div v-if="(d.daily || []).length" class="flex items-end gap-1 h-[110px]">
          <div v-for="f in d.daily" :key="f.date" class="flex-1 flex flex-col items-center gap-0.5 min-w-0"
               :title="`${f.date} · ${f.confirm}✓ ${f.cancel}✗ ${f.dna}·`">
            <div class="w-full max-w-[26px] flex flex-col justify-end rounded-t overflow-hidden" :style="{ height: '92px' }">
              <div class="w-full bg-amber-300" :style="{ height: fH(f.dna) }" />
              <div class="w-full bg-rose-400" :style="{ height: fH(f.cancel) }" />
              <div class="w-full bg-emerald-400" :style="{ height: fH(f.confirm) }" />
            </div>
            <span class="text-[8.5px] text-stone-400 tabular-nums">{{ f.date.slice(8) }}</span>
          </div>
        </div>
        <div v-else class="text-center text-[12px] text-stone-400 py-8">{{ t('ccd.noData') }}</div>
      </div>

      <!-- today's target, mirrored from the workspace ring -->
      <div v-if="range === 'today' && d.target" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 flex items-center gap-3">
        <Icon name="gauge" :size="15" class="text-[var(--accent-600)]" />
        <span class="text-[12.5px] font-semibold text-stone-800">{{ t('md.targetToday') }}</span>
        <div class="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden">
          <div class="h-full rounded-full transition-all duration-700"
               :class="total >= d.target ? 'bg-emerald-500' : 'bg-[var(--accent-500)]'"
               :style="{ width: Math.min(100, Math.round((total * 100) / d.target)) + '%' }" />
        </div>
        <span class="text-[13px] font-bold tabular-nums" :class="total >= d.target ? 'text-emerald-600' : 'text-stone-700'">{{ total }}/{{ d.target }}</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const d = ref(null);
const dp = ref(null);   // previous window, for the Δ chips
const loading = ref(true);
const loadError = ref("");
const RANGES = ["today", "yest", "7d", "month", "lastMonth"];
const range = ref("7d");

const day = 86400000;
const localIso = (dt) =>
  `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
function windowFor(key) {
  const now = new Date();
  if (key === "today") { const d0 = localIso(now); return [d0, d0]; }
  if (key === "yest") { const d0 = localIso(new Date(now.getTime() - day)); return [d0, d0]; }
  if (key === "7d") return [localIso(new Date(now.getTime() - 6 * day)), localIso(now)];
  if (key === "month") return [localIso(new Date(now.getFullYear(), now.getMonth(), 1)), localIso(now)];
  return [localIso(new Date(now.getFullYear(), now.getMonth() - 1, 1)),
          localIso(new Date(now.getFullYear(), now.getMonth(), 0))];
}
function prevWindowFor(key) {
  const now = new Date();
  if (key === "month") return windowFor("lastMonth");
  if (key === "lastMonth") {
    return [localIso(new Date(now.getFullYear(), now.getMonth() - 2, 1)),
            localIso(new Date(now.getFullYear(), now.getMonth() - 1, 0))];
  }
  const [f, t2] = windowFor(key);
  const len = Math.round((new Date(t2) - new Date(f)) / day) + 1;
  return [localIso(new Date(new Date(f).getTime() - len * day)),
          localIso(new Date(new Date(f).getTime() - day))];
}

let seqN = 0;
async function load() {
  const seq = ++seqN;
  loading.value = true;
  try {
    const [f, t2] = windowFor(range.value);
    const [pf, pt] = prevWindowFor(range.value);
    const [cur, prev] = await Promise.all([
      api("confirmation.my_report", { frm: f, to: t2 }),
      api("confirmation.my_report", { frm: pf, to: pt }).catch(() => null),
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

const total = computed(() =>
  Object.values(d.value?.acts || {}).reduce((a, b) => a + (b || 0), 0));
const rate = computed(() => {
  const a = d.value?.acts;
  if (!a) return null;
  const dec = (a.confirm || 0) + (a.cancel || 0);
  return dec ? Math.round((a.confirm * 100) / dec) : null;
});
const stickPct = computed(() => {
  const st = d.value?.stick;
  return st?.shipped ? Math.round((st.delivered * 100) / st.shipped) : null;
});
function rateOf(rep) {
  const a = rep?.acts;
  const dec = (a?.confirm || 0) + (a?.cancel || 0);
  return dec ? Math.round((a.confirm * 100) / dec) : null;
}
function deltaOf(cur, prev, isPts = false) {
  if (cur == null || prev == null || (!prev && !isPts)) return null;
  const d2 = isPts ? cur - prev : Math.round(((cur - prev) * 100) / prev);
  return { v: d2, up: d2 > 0, txt: (d2 > 0 ? "+" : "") + d2 + (isPts ? " pt" : "%") };
}
const deltas = computed(() => {
  if (!dp.value) return {};
  const pTotal = Object.values(dp.value.acts || {}).reduce((a, b) => a + (b || 0), 0);
  return {
    total: deltaOf(total.value, pTotal),
    rate: deltaOf(rate.value, rateOf(dp.value), true),
    value: deltaOf(d.value?.cohort?.value, dp.value?.cohort?.value),
  };
});
const fMax = computed(() =>
  Math.max(1, ...(d.value?.daily || []).map((f) => (f.confirm || 0) + (f.cancel || 0) + (f.dna || 0))));
function fH(n) { return Math.round(((n || 0) * 92) / fMax.value) + "px"; }
function fmtN(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
</script>

<style scoped>
.md-kpi {
  background: white; border-radius: 16px; padding: 16px;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / .7);
}
.md-kpi-l {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .05em; color: rgb(168 162 158);
}
.md-delta {
  font-size: 10.5px; font-weight: 700; border-radius: 9999px; padding: 1px 7px;
}
.md-up { color: rgb(5 150 105); background: rgb(209 250 229 / .7); }
.md-down { color: rgb(190 18 60); background: rgb(255 228 230 / .8); }
</style>
