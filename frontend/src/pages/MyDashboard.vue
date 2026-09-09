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

    <div v-if="loading && !d" class="space-y-3">
      <span class="block h-[132px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <span v-for="n in 4" :key="n" class="h-[104px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
    </div>
    <div v-else-if="loadError" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('cf.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <template v-else-if="d">
      <!-- HERO. The one thing worth looking at first: how far through the day
           this person is, and the streak they are protecting. -->
      <section class="md-hero md-in" :class="{ 'md-hero-hit': hit }">
        <div class="md-hero-glow" aria-hidden="true" />
        <div class="relative flex items-center gap-5 flex-wrap sm:flex-nowrap">
          <div class="relative w-[104px] h-[104px] flex-shrink-0">
            <svg viewBox="0 0 104 104" class="w-full h-full -rotate-90">
              <defs>
                <linearGradient id="mdRing" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" :stop-color="hit ? '#34d399' : 'var(--accent-400, #fb923c)'" />
                  <stop offset="100%" :stop-color="hit ? '#059669' : 'var(--accent-600, #ea580c)'" />
                </linearGradient>
              </defs>
              <circle cx="52" cy="52" r="44" fill="none" stroke="rgb(255 255 255 / .14)" stroke-width="9" />
              <circle cx="52" cy="52" r="44" fill="none" stroke="url(#mdRing)" stroke-width="9"
                      stroke-linecap="round" :stroke-dasharray="RING"
                      :stroke-dashoffset="RING - RING * Math.min(1, goalPct / 100)"
                      class="md-ring" />
            </svg>
            <span class="absolute inset-0 flex flex-col items-center justify-center">
              <span class="text-[27px] font-extrabold tabular-nums text-white leading-none">{{ nHero }}</span>
              <span v-if="showTarget" class="text-[10.5px] font-semibold text-white/55 tabular-nums mt-0.5">/ {{ goal }}</span>
            </span>
          </div>

          <div class="min-w-0 flex-1">
            <div class="text-[15px] font-bold text-white leading-snug">{{ heroLine }}</div>
            <div class="text-[12px] text-white/60 mt-0.5">
              {{ range === 'today' ? t('md.heroDone') : t('md.heroPeriod') }}
            </div>
            <div class="flex items-center gap-2 flex-wrap mt-2.5">
              <span v-if="streak >= 1" class="md-chip md-chip-live">
                <Icon name="zap" :size="11" />
                {{ streak > 1 ? t('md.streak').replace('{n}', String(streak)) : t('md.streakOne') }}
              </span>
              <span v-if="best" class="md-chip">
                <Icon name="award" :size="11" />
                {{ t('md.best').replace('{n}', String(best.n)).replace('{d}', best.date.slice(5)) }}
              </span>
              <span v-if="d.autoClosed" class="md-chip">
                <Icon name="bot" :size="11" />
                {{ t('md.autoClosed').replace('{n}', String(d.autoClosed)) }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <div class="flex items-center gap-1.5 text-[11px] text-stone-400 -mt-2">
        <Icon name="info" :size="11" /><span>{{ t('md.autoNote') }}</span>
      </div>

      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="md-kpi md-in" style="animation-delay: 60ms">
          <div class="md-kpi-l"><Icon name="activity" :size="12" class="inline -mt-px me-1" />{{ t('ccd.kDecisions') }}</div>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-[28px] font-extrabold tabular-nums text-stone-900">{{ nTotal }}</span>
            <span v-if="deltas.total" class="md-delta" :class="deltas.total.up ? 'md-up' : 'md-down'">{{ deltas.total.txt }}</span>
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ d.acts.dna }} {{ t('cf.actDna') }} · {{ d.acts.followup }} {{ t('cf.actFollowup') }}</div>
        </div>

        <div class="md-kpi md-in flex items-center gap-3" style="animation-delay: 120ms">
          <div class="relative w-[66px] h-[66px] flex-shrink-0">
            <svg viewBox="0 0 66 66" class="w-full h-full -rotate-90">
              <circle cx="33" cy="33" r="27" fill="none" stroke="rgb(231 229 228)" stroke-width="7" />
              <circle cx="33" cy="33" r="27" fill="none" stroke-width="7" stroke-linecap="round"
                      :stroke="rate === null ? 'rgb(214 211 209)' : rate >= 50 ? 'rgb(16 185 129)' : 'rgb(244 63 94)'"
                      :stroke-dasharray="169.6" :stroke-dashoffset="169.6 - (169.6 * (rate || 0)) / 100"
                      class="md-ring" />
            </svg>
            <span class="absolute inset-0 flex items-center justify-center text-[15px] font-extrabold tabular-nums"
                  :class="rate === null ? 'text-stone-300' : rate >= 50 ? 'text-emerald-600' : 'text-rose-600'">
              {{ rate === null ? '—' : nRate + '%' }}</span>
          </div>
          <div class="min-w-0">
            <div class="md-kpi-l">{{ t('ccd.kRate') }}</div>
            <div class="text-[11.5px] tabular-nums mt-1 flex items-center gap-2">
              <span class="text-emerald-600 font-bold">{{ d.acts.confirm }} <Icon name="check" :size="10" class="inline -mt-px" /></span>
              <span class="text-rose-500 font-bold">{{ d.acts.cancel }} <Icon name="x" :size="10" class="inline -mt-px" /></span>
            </div>
            <div class="text-[10px] mt-0.5"><span v-if="deltas.rate" class="md-delta" :class="deltas.rate.up ? 'md-up' : 'md-down'">{{ deltas.rate.txt }}</span></div>
          </div>
        </div>

        <div class="md-kpi md-in" style="animation-delay: 180ms">
          <div class="md-kpi-l"><Icon name="wallet" :size="12" class="inline -mt-px me-1" />{{ t('ccd.kValue') }}</div>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-[28px] font-extrabold tabular-nums text-stone-900">{{ fmtN(nValue) }}</span>
            <span v-if="deltas.value" class="md-delta" :class="deltas.value.up ? 'md-up' : 'md-down'">{{ deltas.value.txt }}</span>
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ fmtN(d.cohort.n) }} {{ t('md.myOrders') }}</div>
        </div>

        <div class="md-kpi md-in" style="animation-delay: 240ms">
          <div class="md-kpi-l"><Icon name="package-check" :size="12" class="inline -mt-px me-1" />{{ t('ccd.stickTitle') }}</div>
          <div class="text-[28px] font-extrabold tabular-nums mt-1"
               :class="stickPct === null ? 'text-stone-300' : stickPct >= 60 ? 'text-emerald-600' : stickPct >= 40 ? 'text-amber-600' : 'text-rose-600'">
            {{ stickPct === null ? '—' : stickPct + '%' }}
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ d.stick.delivered }} / {{ d.stick.shipped }} {{ t('md.deliveredOfShipped') }}</div>
        </div>
      </div>

      <!-- Time to first touch. Deliberately its own quiet row and not a
           fifth KPI tile: it is a number to look at, not one that pays. -->
      <div v-if="d.touch && d.touch.n" class="md-in flex items-center gap-3 flex-wrap
                  bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3"
           style="animation-delay: 270ms">
        <Icon name="clock" :size="14" class="text-stone-400 flex-shrink-0" />
        <span class="text-[12px] font-semibold text-stone-800">{{ t('md.touchTitle') }}</span>
        <span class="text-[18px] font-extrabold tabular-nums"
              :class="d.touch.median <= d.touch.slaH ? 'text-emerald-600' : 'text-stone-800'">
          {{ d.touch.median }}<span class="text-[11px] font-bold ms-0.5">{{ t('md.hoursShort') }}</span>
        </span>
        <div class="flex-1 min-w-[120px] h-1.5 rounded-full bg-stone-100 overflow-hidden">
          <div class="h-full rounded-full transition-all duration-700"
               :class="d.touch.withinPct >= 60 ? 'bg-emerald-500'
                       : d.touch.withinPct >= 35 ? 'bg-amber-400' : 'bg-rose-400'"
               :style="{ width: d.touch.withinPct + '%' }" />
        </div>
        <span class="text-[11.5px] text-stone-500 tabular-nums">
          {{ t('md.touchWithin').replace('{p}', String(d.touch.withinPct)).replace('{h}', String(d.touch.slaH)) }}
        </span>
      </div>

      <!-- my daily decisions -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 md-in" style="animation-delay: 300ms">
        <div class="flex items-center gap-2 mb-3">
          <Icon name="trending-up" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('ccd.dailyTitle') }}</span>
          <span class="ms-auto flex items-center gap-3 text-[10.5px] text-stone-500">
            <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-400 me-1" />{{ t('cf.actConfirm') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-rose-400 me-1" />{{ t('cf.actCancel') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-amber-300 me-1" />{{ t('cf.actDna') }}</span>
          </span>
        </div>
        <!-- Columns are FIXED width and centered, never flex-stretched: a
             single-day range used to hand one 28px bar an entire panel of
             emptiness. Gridlines give the heights something to be read
             against; the baseline grounds the bars. -->
        <div v-if="(d.daily || []).length" class="relative">
          <div class="absolute inset-x-0 top-[18px] bottom-[22px] pointer-events-none">
            <div v-for="g in [0, 1, 2, 3]" :key="g"
                 class="absolute inset-x-0 border-t border-dashed border-stone-100"
                 :style="{ top: g * 33.33 + '%' }" />
            <div class="absolute inset-x-0 bottom-0 border-t border-stone-200" />
          </div>
          <div class="relative flex items-end justify-center gap-2 sm:gap-3 overflow-x-auto pb-0.5"
               style="scrollbar-width: none">
            <div v-for="(f, fi) in d.daily" :key="f.date"
                 class="group flex-none w-11 sm:w-12 flex flex-col items-center gap-1"
                 :title="`${f.date} · ${f.confirm} ${t('cf.actConfirm')} · ${f.cancel} ${t('cf.actCancel')} · ${f.dna} ${t('cf.actDna')}`">
              <span class="text-[10px] font-bold tabular-nums transition-colors"
                    :class="best && f.date === best.date ? 'text-[var(--accent-600)]' : 'text-stone-500 group-hover:text-stone-800'">
                {{ dayTotal(f) || '' }}</span>
              <div class="w-8 flex flex-col justify-end rounded-md overflow-hidden md-bar
                          transition-transform group-hover:scale-y-[1.03] origin-bottom bg-stone-50"
                   :class="best && f.date === best.date ? 'ring-2 ring-[var(--accent-400)] ring-offset-1' : ''"
                   :style="{ height: '112px', animationDelay: Math.min(fi * 35, 700) + 'ms' }">
                <div class="w-full bg-amber-300" :style="{ height: fH(f.dna) }" />
                <div class="w-full bg-rose-400" :style="{ height: fH(f.cancel) }" />
                <div class="w-full bg-emerald-400" :style="{ height: fH(f.confirm) }" />
              </div>
              <span class="text-[9.5px] tabular-nums font-medium"
                    :class="best && f.date === best.date ? 'text-[var(--accent-600)]' : 'text-stone-400'">
                {{ f.date.slice(8) }}/{{ f.date.slice(5, 7) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="text-center text-[12px] text-stone-400 py-8">{{ t('ccd.noData') }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const d = ref(null);
const dp = ref(null);   // previous window, for the Δ chips
const loading = ref(true);
const loadError = ref("");
// "Last month" only once a month AFTER September 2026 exists to look back
// at — the scheme started then, and August's numbers were never played by
// these rules. From October onward the chip appears and history accumulates.
const EPOCH = new Date(2026, 8, 1);
const _now0 = new Date();
const RANGES = ["today", "yest", "7d", "month",
  ...(new Date(_now0.getFullYear(), _now0.getMonth() - 1, 1) >= EPOCH ? ["lastMonth"] : [])];
// Remember the chip across visits — an agent who lives on "today" should not
// re-click it every time they glance at their numbers.
let _r0 = "7d";
try { _r0 = sessionStorage.getItem("lp_md_range") || "7d"; } catch {}
const range = ref(RANGES.includes(_r0) ? _r0 : "7d");
watch(range, (v) => { try { sessionStorage.setItem("lp_md_range", v); } catch {} });
const RING = 2 * Math.PI * 44;

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
function dayTotal(f) { return (f.confirm || 0) + (f.cancel || 0) + (f.dna || 0); }

// Count-up: the numbers roll to their value — the page feels alive without
// a single external library. One RAF loop per target, cancellable.
function useCountUp(target) {
  const shown = ref(0);
  let raf = 0;
  watch(target, (to) => {
    cancelAnimationFrame(raf);
    const from = shown.value;
    const t0 = performance.now();
    const step = (now2) => {
      const p2 = Math.min(1, (now2 - t0) / 800);
      const eased = 1 - Math.pow(1 - p2, 3);
      shown.value = Math.round(from + (to - from) * eased);
      if (p2 < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
  }, { immediate: true });
  onUnmounted(() => cancelAnimationFrame(raf));
  return shown;
}
const nTotal = useCountUp(total);
const nValue = useCountUp(computed(() => d.value?.cohort?.value || 0));
const rate = computed(() => {
  const a = d.value?.acts;
  if (!a) return null;
  const dec = (a.confirm || 0) + (a.cancel || 0);
  return dec ? Math.round((a.confirm * 100) / dec) : null;
});
const nRate = useCountUp(computed(() => rate.value || 0));
const stickPct = computed(() => {
  const st = d.value?.stick;
  return st?.shipped ? Math.round((st.delivered * 100) / st.shipped) : null;
});

// --- the hero ---
// One rule for every range: the goal is the daily target multiplied by the
// days in the window. The ring and the number then measure the same thing —
// a ring filling against the best day while the number showed the period
// total would be two different claims in one graphic.
const winDays = computed(() => {
  const [f, t2] = windowFor(range.value);
  return Math.max(1, Math.round((new Date(t2) - new Date(f)) / day) + 1);
});
const goal = computed(() => (d.value?.target || 0) * winDays.value);
const showTarget = computed(() => goal.value > 0);
const nHero = useCountUp(total);
const goalPct = computed(() =>
  goal.value ? Math.round((total.value * 100) / goal.value) : 0);
const hit = computed(() => showTarget.value && total.value >= goal.value);
const heroLine = computed(() => {
  if (!d.value) return "";
  if (!showTarget.value) return t("md.heroPeriod");
  if (hit.value) return t("md.heroHit");
  if (!total.value) return t("md.heroNone");
  return t("md.heroToGo").replace("{n}", String(goal.value - total.value));
});
// Best day and streak come straight out of the daily series — nothing is
// stored, so they can never drift from the bars right below them.
const best = computed(() => {
  const rows = (d.value?.daily || []).filter((f) => dayTotal(f) > 0);
  if (!rows.length) return null;
  return rows.reduce((a, b) => (dayTotal(b) > dayTotal(a) ? b : a), rows[0]);
});
// Days ON TARGET, counted back from the newest day that has any work. A day
// with nothing on it breaks the run; a weekend with no orders simply is not
// in the series, so it cannot silently claim a streak either.
const streak = computed(() => {
  const tgt = d.value?.target || 0;
  const rows = d.value?.daily || [];
  if (!tgt || !rows.length) return 0;
  let n = 0;
  for (let i = rows.length - 1; i >= 0; i--) {
    if (dayTotal(rows[i]) >= tgt) n++;
    else break;
  }
  return n;
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
  Math.max(1, ...(d.value?.daily || []).map(dayTotal)));
function fH(n) { return Math.round(((n || 0) * 112) / fMax.value) + "px"; }
function fmtN(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
</script>

<style scoped>
.md-hero {
  position: relative; overflow: hidden;
  border-radius: 20px; padding: 20px 22px;
  background: linear-gradient(135deg, #1c1917 0%, #292524 55%, #1c1917 100%);
  box-shadow: 0 10px 30px -18px rgb(28 25 23 / .8);
}
/* A slow drifting wash so the card is not a flat rectangle. Purely
   decorative, and it stops entirely for anyone who asked for less motion. */
.md-hero-glow {
  position: absolute; inset: -40%;
  background: radial-gradient(closest-side, var(--accent-500, #f97316) 0%, transparent 70%);
  opacity: .20; filter: blur(10px);
  animation: md-drift 14s ease-in-out infinite alternate;
}
.md-hero-hit .md-hero-glow {
  background: radial-gradient(closest-side, #10b981 0%, transparent 70%);
  opacity: .28;
}
@keyframes md-drift {
  from { transform: translate3d(-8%, -6%, 0) scale(1); }
  to   { transform: translate3d(10%, 8%, 0) scale(1.15); }
}
.md-chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 10.5px; font-weight: 700; color: rgb(255 255 255 / .82);
  background: rgb(255 255 255 / .10); border: 1px solid rgb(255 255 255 / .14);
  border-radius: 9999px; padding: 3px 9px;
}
.md-chip-live { color: #fde68a; border-color: rgb(253 230 138 / .35); background: rgb(253 230 138 / .12); }
.md-ring { transition: stroke-dashoffset .9s cubic-bezier(.2, .7, .3, 1); }

.md-kpi {
  background: white; border-radius: 16px; padding: 16px;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / .7);
  transition: transform .18s ease, box-shadow .18s ease;
}
.md-kpi:hover {
  transform: translateY(-2px);
  box-shadow: inset 0 0 0 1px rgb(214 211 209 / .9), 0 8px 20px -14px rgb(28 25 23 / .5);
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
.md-in {
  opacity: 0;
  animation: md-rise .45s cubic-bezier(.2, .7, .3, 1) forwards;
}
@keyframes md-rise {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.md-bar {
  transform: scaleY(0); transform-origin: bottom;
  animation: md-grow .5s cubic-bezier(.2, .7, .3, 1) forwards;
}
@keyframes md-grow {
  to { transform: scaleY(1); }
}
/* Motion is decoration here, never information: everything below still
   reads correctly standing still. */
@media (prefers-reduced-motion: reduce) {
  .md-in, .md-bar, .md-hero-glow { animation: none; opacity: 1; transform: none; }
  .md-ring { transition: none; }
}
</style>
