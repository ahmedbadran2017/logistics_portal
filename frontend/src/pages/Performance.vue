<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[900px] mx-auto">
    <!-- Greeting -->
    <div>
      <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Hi {{ firstName }} 👋</h1>
      <p class="text-[12.5px] text-stone-500 mt-1">{{ t('px.perf.sub') }}</p>
    </div>

    <!-- Metric tiles -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0"><Icon name="package-check" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Today</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none">{{ me.picks }}</div>
        <div class="text-[10.5px] text-stone-400 mt-1">picks</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center flex-shrink-0"><Icon name="clock" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('px.perf.avgTime') }}</span>
        </div>
        <div class="mt-2 text-[22px] font-semibold text-stone-900 font-mono tabular-nums leading-none">{{ me.avg }}</div>
        <div class="text-[10.5px] text-stone-400 mt-1">{{ t('px.perf.perPick') }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0"><Icon name="check-circle" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('px.perf.slaRate') }}</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-emerald-600 tabular-nums leading-none">{{ me.sla }}<span class="text-[13px] font-medium text-stone-400">%</span></div>
        <div class="text-[10.5px] text-stone-400 mt-1">{{ t('px.perf.onTime') }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0"><Icon name="trending-up" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Rank</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none">#{{ me.rank }}</div>
        <div class="text-[10.5px] text-stone-400 mt-1">{{ t('px.perf.onTeam') }}</div>
      </div>
    </div>

    <!-- Progress to target -->
    <div class="bg-gradient-to-br from-[var(--accent-50)] to-white rounded-xl ring-1 ring-[var(--accent-200)]/50 p-5">
      <div class="flex items-center justify-between mb-2">
        <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('px.perf.dailyTarget') }}</span>
        <span class="text-[12.5px] tabular-nums text-stone-600">{{ me.picks }} / {{ me.target }}</span>
      </div>
      <div class="h-3 rounded-full bg-white ring-1 ring-stone-200/70 overflow-hidden">
        <div class="h-full rounded-full transition-all duration-500"
             :style="{ width: pct + '%', background: hitTarget ? '#10b981' : 'var(--accent-500)' }" />
      </div>
      <p class="mt-3 text-[13px] font-medium" :class="hitTarget ? 'text-emerald-600' : 'text-stone-700'">
        <template v-if="hitTarget">🎉 Target smashed — {{ me.picks - me.target }} over. Amazing work!</template>
        <template v-else>{{ remaining }} to hit {{ me.target }}! Keep it up — you're almost there.</template>
      </p>
    </div>

    <!-- 7-day trend sparkline -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5">
      <div class="flex items-center gap-2 mb-4 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
        <Icon name="trending-up" :size="15" class="text-emerald-500" /> Last 7 days
      </div>
      <svg :viewBox="`0 0 ${spW} ${spH}`" class="w-full" :height="spH" preserveAspectRatio="none">
        <polyline :points="sparkPoints" fill="none" stroke="#10b981" stroke-width="2.5"
                  stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
        <circle v-for="(p, i) in sparkCoords" :key="i" :cx="p.x" :cy="p.y" r="2.5"
                :fill="i === sparkCoords.length - 1 ? '#10b981' : '#10b98180'" />
      </svg>
      <div class="flex justify-between mt-2 text-[11px] text-stone-400 tabular-nums">
        <span v-for="(v, i) in me.trend" :key="i">{{ v }}</span>
      </div>
    </div>

    <!-- Personal bests -->
    <div v-if="bests.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5">
      <div class="flex items-center gap-2 mb-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
        <Icon name="sparkles" :size="15" class="text-amber-500" /> Personal bests
      </div>
      <div class="flex flex-wrap gap-2">
        <div v-for="b in bests" :key="b.label" class="rounded-lg bg-stone-50 ring-1 ring-stone-200/60 px-3 py-2">
          <div class="text-[10.5px] text-stone-400">{{ b.label }}</div>
          <div class="text-[13.5px] font-semibold text-stone-900 tabular-nums font-mono">{{ b.value }}</div>
        </div>
      </div>
    </div>

    <!-- Recent activity -->
    <div v-if="recent.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5">
      <div class="flex items-center gap-2 mb-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
        <Icon name="list-checks" :size="15" /> Recent picks
      </div>
      <ul class="divide-y divide-stone-100">
        <li v-for="(r, i) in recent" :key="i" class="flex items-center justify-between py-2.5">
          <div class="flex items-center gap-3">
            <span class="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0">
              <Icon name="check" :size="14" />
            </span>
            <div class="min-w-0">
              <div class="text-[12.5px] font-medium text-stone-800 tabular-nums font-mono">{{ r.order }}</div>
              <div class="text-[11px] text-stone-500 truncate">{{ r.customer }}</div>
            </div>
          </div>
          <span class="text-[11px] text-stone-400 tabular-nums font-mono">{{ r.time }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useAuth } from "@/composables/useAuth";
import { api, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
const { t } = useI18n();

// Real identity: the logged-in user, matched against the live leaderboard by
// email-derived id or raw email (the old hardcoded "marouane" showed everyone
// the same person's stats).
const { user, fullName } = useAuth();
const board = ref([]);
const myStats = ref(null);

onMounted(async () => {
  const [live, mine] = await Promise.all([
    liveOr(null, () => api("performance.team")),
    api("performance.me").catch(() => null),
  ]);
  if (live && live.leaderboard && live.leaderboard.length) board.value = live.leaderboard;
  myStats.value = mine;
});

const me = computed(() => {
  const email = user.value || "";
  const localPart = email.split("@")[0].toLowerCase();
  return board.value.find((m) =>
    m.id === email || String(m.id).toLowerCase() === localPart
    || (m.name || "").toLowerCase() === (fullName.value || "").toLowerCase())
    || { picks: myStats.value?.todayCount || 0, avg: "—", sla: 0, rank: 0, trend: [0], target: 40 };
});

const firstName = computed(() => (fullName.value || "").split(/\s+/)[0] || "");

const pct = computed(() => Math.min(100, Math.round((me.value.picks / (me.value.target || 1)) * 100)));
const hitTarget = computed(() => me.value.picks >= me.value.target);
const remaining = computed(() => Math.max(0, me.value.target - me.value.picks));

// Sparkline geometry
const spW = 320;
const spH = 60;
const sparkCoords = computed(() => {
  const vals = me.value.trend && me.value.trend.length ? me.value.trend : [0];
  const max = Math.max(...vals, 1);
  const min = Math.min(...vals, 0);
  const range = max - min || 1;
  const step = vals.length > 1 ? spW / (vals.length - 1) : spW;
  const pad = 6;
  return vals.map((v, i) => ({
    x: vals.length > 1 ? i * step : spW / 2,
    y: spH - pad - ((v - min) / range) * (spH - pad * 2),
  }));
});
const sparkPoints = computed(() => sparkCoords.value.map((p) => `${p.x},${p.y}`).join(" "));

// Personal bests / recent picks: no real history endpoint yet — show nothing
// rather than fabricated numbers. (Backed by performance.me once it grows.)
const bests = [];
const recent = [];
</script>
