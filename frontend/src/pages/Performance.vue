<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1000px] mx-auto">
    <!-- greeting -->
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[21px] font-bold text-stone-900 tracking-tight">
          {{ t('px.perf.hi') }} {{ firstName }}
        </h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('px.perf.sub') }}</p>
      </div>
      <div v-if="d?.streak > 1" class="pf-streak">
        <Icon name="zap" :size="13" />
        <span class="tabular-nums">{{ d.streak }}</span>
        <span>{{ t('px.perf.streak') }}</span>
      </div>
    </header>

    <div v-if="loading" class="space-y-3">
      <div class="h-[220px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="h-[140px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[420px] mx-auto break-words">{{ loadError }}</div>
    </div>

    <template v-else-if="d">
      <!-- the ring: today vs target -->
      <section class="pf-hero rounded-2xl p-5 sm:p-6" :class="hit ? 'pf-hero-hit' : ''">
        <div class="flex items-center gap-6 flex-wrap">
          <div class="relative shrink-0" style="width: 148px; height: 148px">
            <svg viewBox="0 0 120 120" class="w-full h-full -rotate-90">
              <circle cx="60" cy="60" r="52" fill="none" stroke="currentColor"
                      class="text-stone-200/70" stroke-width="9" />
              <circle cx="60" cy="60" r="52" fill="none" stroke-width="9" stroke-linecap="round"
                      :stroke="hit ? 'url(#pfHit)' : 'url(#pfRun)'"
                      :stroke-dasharray="C" :stroke-dashoffset="dash"
                      style="transition: stroke-dashoffset 1.1s cubic-bezier(.2,.8,.2,1)" />
              <defs>
                <linearGradient id="pfRun" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stop-color="var(--accent-400)" />
                  <stop offset="100%" stop-color="var(--accent-600)" />
                </linearGradient>
                <linearGradient id="pfHit" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stop-color="#34d399" />
                  <stop offset="100%" stop-color="#059669" />
                </linearGradient>
              </defs>
            </svg>
            <div class="absolute inset-0 flex flex-col items-center justify-center">
              <span class="text-[38px] font-extrabold text-stone-900 tabular-nums leading-none">{{ nToday }}</span>
              <span class="text-[11px] text-stone-400 mt-1">/ {{ d.target }} {{ t('px.perf.today') }}</span>
            </div>
          </div>

          <div class="flex-1 min-w-[240px] space-y-3">
            <div>
              <div class="text-[15px] font-bold" :class="hit ? 'text-emerald-600' : 'text-stone-800'">
                <Icon v-if="hit" name="check-circle" :size="16" class="inline -mt-0.5 me-1.5" />
                {{ hit ? t('px.perf.hitMsg', { n: d.today - d.target }).replace('{n}', d.today - d.target)
                       : t('px.perf.goMsg', { n: remaining }).replace('{n}', remaining) }}
              </div>
              <div class="text-[12px] text-stone-500 mt-1">
                <template v-if="d.kind === 'agent'">
                  <span class="font-bold text-emerald-600 tabular-nums">{{ nWins }}</span> {{ t('px.perf.wins') }}
                  <template v-if="d.rate !== null">
                    <span class="text-stone-300 mx-1.5">·</span>
                    <span class="font-bold text-stone-800 tabular-nums">{{ d.rate }}%</span> {{ t('cfr.thRate').toLowerCase() }}
                  </template>
                </template>
              </div>
            </div>

            <!-- quick stats -->
            <div class="flex flex-wrap gap-2">
              <div v-if="d.rank" class="pf-stat">
                <span class="pf-stat-n" :class="d.rank === 1 ? 'text-amber-600' : 'text-stone-900'">#{{ d.rank }}</span>
                <span class="pf-stat-l">{{ t('px.perf.onTeam') }} ({{ d.of }})</span>
              </div>
              <div v-if="d.best" class="pf-stat">
                <span class="pf-stat-n text-stone-900">{{ d.best.total }}</span>
                <span class="pf-stat-l">{{ t('px.perf.best') }} · {{ d.best.date.slice(5) }}</span>
              </div>
              <RouterLink v-if="d.points" :to="{ name: 'Bonus' }" class="pf-stat pf-stat-link">
                <span class="pf-stat-n text-violet-600">{{ d.points.month }}</span>
                <span class="pf-stat-l">{{ t('bn.pts') }} / {{ d.points.target }}</span>
              </RouterLink>
            </div>
          </div>
        </div>

        <!-- action breakdown -->
        <div v-if="actions.length" class="flex flex-wrap gap-1.5 mt-4 pt-4 border-t border-stone-200/60">
          <span v-for="a in actions" :key="a.key" class="pf-chip" :class="a.win ? 'pf-chip-win' : ''">
            <span class="tabular-nums font-bold">{{ a.n }}</span>
            {{ t('px.perf.a_' + a.key.replace('.', '_'), a.key.split('.')[1]) }}
          </span>
        </div>
      </section>

      <div class="grid gap-3" :class="d.hours.length ? 'md:grid-cols-2' : ''">
        <!-- today's pace — only where a timestamp really marks the work -->
        <section v-if="d.hours.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center gap-2 mb-3">
            <Icon name="activity" :size="14" class="text-stone-400" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('px.perf.pace') }}</span>
            <span v-if="peakHour !== null" class="text-[11px] text-stone-400 ms-auto tabular-nums">
              {{ t('px.perf.peak') }} {{ String(peakHour).padStart(2, '0') }}:00
            </span>
          </div>
          <div class="flex items-end gap-[3px] h-[86px]">
            <div v-for="h in d.hours" :key="h.h" class="flex-1 flex flex-col justify-end group relative">
              <div class="pf-bar rounded-t-[3px]" :class="h.n ? 'pf-bar-on' : 'pf-bar-off'"
                   :style="{ height: barH(h.n), transitionDelay: (h.h % 24) * 22 + 'ms' }" />
              <span v-if="h.n" class="pf-tip">{{ h.n }}</span>
            </div>
          </div>
          <div class="flex justify-between mt-1.5 text-[10px] text-stone-400 tabular-nums">
            <span>{{ String(d.hours[0]?.h ?? 8).padStart(2, '0') }}:00</span>
            <span>{{ String(d.hours[d.hours.length - 1]?.h ?? 20).padStart(2, '0') }}:00</span>
          </div>
        </section>

        <!-- 7-day trend -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center gap-2 mb-3">
            <Icon name="trending-up" :size="14" class="text-stone-400" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('px.perf.week') }}</span>
            <span class="text-[11px] text-stone-400 ms-auto tabular-nums">
              {{ weekTotal }} {{ t('px.perf.total') }}
            </span>
          </div>
          <div class="flex items-end gap-1.5 h-[86px]">
            <div v-for="(dd, i) in d.trend" :key="dd.date" class="flex-1 flex flex-col justify-end items-center gap-1">
              <span class="text-[10px] font-bold tabular-nums"
                    :class="i === d.trend.length - 1 ? 'text-stone-900' : 'text-stone-400'">{{ dd.total || '' }}</span>
              <div class="w-full rounded-t-[3px] pf-bar"
                   :class="i === d.trend.length - 1 ? 'pf-bar-today' : (dd.total >= d.target ? 'pf-bar-hit' : 'pf-bar-on')"
                   :style="{ height: trendH(dd.total), transitionDelay: i * 60 + 'ms' }" />
            </div>
          </div>
          <div class="flex justify-between mt-1.5 text-[10px] text-stone-400">
            <span v-for="dd in d.trend" :key="dd.date" class="flex-1 text-center">{{ dow(dd.date) }}</span>
          </div>
        </section>
      </div>

      <!-- today's activity -->
      <section v-if="d.recent.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
          <Icon name="list-checks" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('px.perf.recent') }}</span>
        </div>
        <TransitionGroup name="pfrow" tag="ul" class="divide-y divide-stone-50">
          <li v-for="(r, i) in d.recent" :key="r.ref + r.at + i"
              class="flex items-center justify-between px-4 py-2.5 gap-3 hover:bg-stone-50/70 transition-colors">
            <div class="flex items-center gap-3 min-w-0">
              <span class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                    :class="r.win ? 'bg-emerald-50 text-emerald-600' : 'bg-stone-100 text-stone-400'">
                <Icon :name="r.win ? 'check' : 'clock'" :size="13" />
              </span>
              <span class="font-mono text-[12px] text-stone-800 truncate">{{ r.ref }}</span>
              <span class="text-[11px] text-stone-400">{{ t('px.perf.a_' + r.lane + '_' + r.action, r.action) }}</span>
            </div>
            <span class="text-[11px] text-stone-400 tabular-nums font-mono">{{ r.at }}</span>
          </li>
        </TransitionGroup>
      </section>
      <div v-else class="bg-white rounded-xl ring-1 ring-stone-200/70 p-10 text-center">
        <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-stone-100 text-stone-400 mb-2.5">
          <Icon name="sparkles" :size="22" />
        </span>
        <div class="text-[13.5px] font-semibold text-stone-800">{{ t('px.perf.emptyDay') }}</div>
        <div class="text-[12px] text-stone-400 mt-0.5">{{ t('px.perf.emptyHint') }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useAuth } from "@/composables/useAuth";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const { fullName } = useAuth();

const d = ref(null);
const loading = ref(true);
const loadError = ref("");

const firstName = computed(() => (fullName.value || "").split(/\s+/)[0] || "");
const hit = computed(() => d.value && d.value.today >= d.value.target);
const remaining = computed(() => Math.max(0, (d.value?.target || 0) - (d.value?.today || 0)));
const weekTotal = computed(() =>
  (d.value?.trend || []).reduce((s, x) => s + x.total, 0));
const peakHour = computed(() => {
  const hs = (d.value?.hours || []).filter((h) => h.n);
  if (!hs.length) return null;
  return hs.reduce((a, b) => (b.n > a.n ? b : a)).h;
});
const actions = computed(() => {
  const wins = ["cf.confirm", "rs.redeliver", "rs.reship", "cs.resolve", "pick.picked"];
  return Object.entries(d.value?.byAction || {})
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([key, n]) => ({ key, n, win: wins.includes(key) }));
});

// The ring: 2πr with r=52.
const C = 2 * Math.PI * 52;
const dash = computed(() => {
  if (!d.value) return C;
  const p = Math.min(1, d.value.today / (d.value.target || 1));
  return C * (1 - p);
});

// Count-up so the numbers land rather than blink into place.
const nToday = ref(0);
const nWins = ref(0);
function countTo(refv, target, ms = 900) {
  const from = refv.value;
  const t0 = performance.now();
  const step = (now) => {
    const p = Math.min(1, (now - t0) / ms);
    const eased = 1 - Math.pow(1 - p, 3);
    refv.value = Math.round(from + (target - from) * eased);
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
watch(d, (v) => {
  if (!v) return;
  countTo(nToday, v.today);
  countTo(nWins, v.wins);
});

const maxHour = computed(() =>
  Math.max(1, ...(d.value?.hours || []).map((h) => h.n)));
function barH(n) {
  return n ? Math.max(6, Math.round((n / maxHour.value) * 86)) + "px" : "3px";
}
const maxTrend = computed(() =>
  Math.max(1, d.value?.target || 1, ...(d.value?.trend || []).map((x) => x.total)));
function trendH(n) {
  return Math.max(3, Math.round((n / maxTrend.value) * 70)) + "px";
}
function dow(date) {
  const dt = new Date(date + "T00:00:00");
  return t("px.perf.dow_" + dt.getDay(), String(dt.getDate()));
}

onMounted(async () => {
  try {
    const res = await api("performance.me");
    // A backend older than this page answers with the previous shape — say so
    // instead of rendering a broken half-page.
    if (!res || typeof res.today !== "number" || !Array.isArray(res.trend)) {
      loadError.value = t("px.set.deployHint");
      return;
    }
    d.value = res;
  } catch (e) {
    loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.pf-hero {
  background: linear-gradient(135deg, var(--accent-50) 0%, #fff 45%, #fff 70%, var(--accent-50) 100%);
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.9), 0 1px 2px rgb(0 0 0 / 0.03);
  transition: box-shadow .4s ease;
}
.pf-hero-hit {
  background: linear-gradient(135deg, rgb(236 253 245) 0%, #fff 45%, #fff 70%, rgb(236 253 245) 100%);
  box-shadow: inset 0 0 0 1px rgb(167 243 208 / 0.9), 0 8px 32px -16px rgb(16 185 129 / 0.35);
}
.pf-streak {
  display: inline-flex; align-items: center; gap: 5px;
  height: 30px; padding: 0 11px; border-radius: 999px;
  font-size: 11.5px; font-weight: 700; color: rgb(180 83 9);
  background: linear-gradient(135deg, rgb(254 243 199), rgb(253 230 138));
  box-shadow: inset 0 0 0 1px rgb(252 211 77);
  animation: pf-glow 2.4s ease-in-out infinite;
}
@keyframes pf-glow {
  0%, 100% { box-shadow: inset 0 0 0 1px rgb(252 211 77), 0 0 0 0 rgb(251 191 36 / .35); }
  50% { box-shadow: inset 0 0 0 1px rgb(252 211 77), 0 0 0 6px rgb(251 191 36 / 0); }
}
.pf-stat {
  display: flex; flex-direction: column; gap: 1px;
  padding: 7px 13px; border-radius: 12px;
  background: rgb(255 255 255 / 0.8);
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
}
.pf-stat-link { transition: transform .15s ease, box-shadow .15s ease; }
.pf-stat-link:hover { transform: translateY(-1px); box-shadow: inset 0 0 0 1px rgb(196 181 253); }
.pf-stat-n { font-size: 17px; font-weight: 800; line-height: 1.1; font-variant-numeric: tabular-nums; }
.pf-stat-l { font-size: 10px; font-weight: 600; color: rgb(168 162 158); white-space: nowrap; }
.pf-chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11.5px; font-weight: 600; color: rgb(87 83 78);
  background: rgb(255 255 255 / 0.75); border-radius: 999px; padding: 4px 11px;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
}
.pf-chip-win { color: rgb(4 120 87); box-shadow: inset 0 0 0 1px rgb(167 243 208); }

.pf-bar {
  width: 100%;
  transition: height .8s cubic-bezier(.2,.8,.2,1);
}
.pf-bar-off { background: rgb(231 229 228 / .8); }
.pf-bar-on { background: linear-gradient(180deg, var(--accent-300), var(--accent-500)); }
.pf-bar-hit { background: linear-gradient(180deg, #6ee7b7, #059669); }
.pf-bar-today { background: linear-gradient(180deg, var(--accent-400), var(--accent-700)); }
.pf-tip {
  position: absolute; top: -16px; left: 50%; transform: translateX(-50%);
  font-size: 9.5px; font-weight: 700; color: rgb(120 113 108);
  opacity: 0; transition: opacity .15s ease;
  font-variant-numeric: tabular-nums;
}
.group:hover .pf-tip { opacity: 1; }

.pfrow-enter-active { transition: all .3s ease; }
.pfrow-enter-from { opacity: 0; transform: translateX(-8px); }
</style>
