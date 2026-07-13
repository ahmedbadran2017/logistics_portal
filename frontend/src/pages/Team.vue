<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1200px] mx-auto">
    <!-- Header -->
    <div class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em] flex items-center gap-2">
          <Icon name="users" :size="20" class="text-[var(--accent-600)]" /> Team
        </h1>
        <p class="text-[12.5px] text-stone-500 mt-1">Leaderboard, load and momentum across the floor.</p>
      </div>
    </div>

    <!-- KPI strip -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0"><Icon name="shield-alert" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Team same-day avg</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none">{{ teamSla }}<span class="text-[13px] font-medium text-stone-400">%</span></div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center flex-shrink-0"><Icon name="package" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Orders picked (30d)</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none">{{ totalPicks }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0"><Icon name="users" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Active members</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none">{{ ranked.length }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" :class="flaggedCount ? 'bg-rose-50 text-rose-600' : 'bg-stone-100 text-stone-400'"><Icon name="alert-triangle" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Flagged</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold tabular-nums leading-none" :class="flaggedCount ? 'text-rose-600' : 'text-stone-900'">{{ flaggedCount }}</div>
      </div>
    </div>

    <!-- Leaderboard table (desktop) -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden hidden md:block">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[820px]">
          <thead>
            <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th class="text-start px-4 py-2.5 w-12">#</th>
              <th class="text-start px-4 py-2.5">Member</th>
              <th class="text-start px-4 py-2.5">Role</th>
              <th class="text-end px-4 py-2.5">Orders</th>
              <th class="text-end px-4 py-2.5 hidden lg:table-cell">Pace</th>
              <th class="text-end px-4 py-2.5">Same-day</th>
              <th class="text-start px-4 py-2.5 hidden lg:table-cell">7-day</th>
              <th class="text-end px-4 py-2.5 hidden sm:table-cell">Target</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr v-for="row in ranked" :key="row.id"
                class="transition-colors" :class="row.rank === 1 ? 'bg-amber-50/40 hover:bg-amber-50/60' : 'hover:bg-stone-50'">
              <td class="px-4 py-3">
                <span class="inline-flex items-center gap-1 text-[13px] font-bold tabular-nums" :class="row.rank === 1 ? 'text-amber-500' : 'text-stone-400'">
                  <Icon v-if="row.rank === 1" name="zap" :size="13" class="text-amber-500" />{{ row.rank }}
                </span>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2.5">
                  <span class="w-8 h-8 rounded-full grid place-items-center text-white text-[11px] font-semibold flex-shrink-0"
                        :style="{ background: row.rank === 1 ? '#f59e0b' : '#6366f1' }">{{ initials(row.name) }}</span>
                  <span class="text-[12.5px] font-semibold truncate max-w-[180px]" :class="row.rank === 1 ? 'text-amber-700' : 'text-stone-900'">{{ row.name }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-[12px] text-stone-600 capitalize whitespace-nowrap">{{ row.role }}</td>
              <td class="px-4 py-3 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{{ row.picks }} <span class="text-[10px] font-normal text-stone-400">orders</span></td>
              <td class="px-4 py-3 text-end text-[12px] text-stone-600 font-mono tabular-nums hidden lg:table-cell">{{ row.avg }}</td>
              <td class="px-4 py-3 text-end">
                <span class="text-[12.5px] font-semibold tabular-nums" :class="slaColor(row.sla)">{{ row.sla }}%</span>
              </td>
              <td class="px-4 py-3 hidden lg:table-cell">
                <svg viewBox="0 0 100 28" class="w-[100px] h-7" preserveAspectRatio="none">
                  <polyline :points="sparkPoints(row.trend, 100, 28)" fill="none"
                            :stroke="trendUp(row.trend) ? '#10b981' : '#f43f5e'" stroke-width="1.75"
                            stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" />
                </svg>
              </td>
              <td class="px-4 py-3 text-end text-[12px] text-stone-500 tabular-nums hidden sm:table-cell">{{ row.target }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Leaderboard cards (mobile) -->
    <div class="space-y-3 md:hidden">
      <div v-for="row in ranked" :key="row.id"
           class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4" :class="row.rank === 1 ? 'ring-amber-200/70' : ''">
        <div class="flex items-center gap-3">
          <span class="inline-flex items-center gap-1 w-8 text-[14px] font-bold tabular-nums" :class="row.rank === 1 ? 'text-amber-500' : 'text-stone-400'">
            <Icon v-if="row.rank === 1" name="zap" :size="13" class="text-amber-500" />{{ row.rank }}
          </span>
          <span class="w-9 h-9 rounded-full grid place-items-center text-white text-[12px] font-semibold flex-shrink-0"
                :style="{ background: row.rank === 1 ? '#f59e0b' : '#6366f1' }">{{ initials(row.name) }}</span>
          <div class="flex-1 min-w-0">
            <div class="text-[13.5px] font-semibold truncate" :class="row.rank === 1 ? 'text-amber-700' : 'text-stone-900'">{{ row.name }}</div>
            <div class="text-[11.5px] text-stone-500 capitalize">{{ row.role }} · {{ row.picks }} orders · <span class="font-mono">{{ row.avg }}</span></div>
          </div>
          <span class="text-[13px] font-semibold tabular-nums" :class="slaColor(row.sla)">{{ row.sla }}%</span>
        </div>
        <div class="flex items-center justify-between mt-3 pt-3 border-t border-stone-100">
          <svg viewBox="0 0 120 28" class="w-[120px] h-7" preserveAspectRatio="none">
            <polyline :points="sparkPoints(row.trend, 120, 28)" fill="none"
                      :stroke="trendUp(row.trend) ? '#10b981' : '#f43f5e'" stroke-width="1.75"
                      stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" />
          </svg>
          <span class="text-[11px] text-stone-400 tabular-nums">Target {{ row.target }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { LEADERBOARD as DEMO_LEADERBOARD, byId } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";

const board = ref(DEMO_LEADERBOARD);

onMounted(async () => {
  const live = await liveOr(null, () => api("performance.team"));
  if (live && live.leaderboard && live.leaderboard.length) {
    // Real rows only — never borrow demo sparklines for live people.
    board.value = live.leaderboard;
  }
});

const ranked = computed(() =>
  [...board.value]
    .sort((a, b) => a.rank - b.rank)
    // Prefer the backend display name (User.full_name / prettified email);
    // the static byId map shows raw emails for anyone it doesn't know.
    .map((m) => ({ ...m, name: m.name || byId(m.id).name, role: byId(m.id).role || "picker" }))
);

const teamSla = computed(() =>
  ranked.value.length
    ? Math.round(ranked.value.reduce((s, m) => s + m.sla, 0) / ranked.value.length)
    : 0
);
const totalPicks = computed(() => ranked.value.reduce((s, m) => s + m.picks, 0));
const flaggedCount = computed(() => ranked.value.filter((m) => !trendUp(m.trend)).length);

function trendUp(trend) {
  if (!trend || trend.length < 2) return true;
  return trend[trend.length - 1] >= trend[0];
}
function slaColor(sla) {
  return sla >= 50 ? "text-emerald-600" : sla >= 30 ? "text-amber-600" : "text-rose-600";
}
function initials(name) {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
}
function sparkPoints(trend, w = 100, h = 28) {
  const vals = trend && trend.length ? trend : [0];
  const max = Math.max(...vals), min = Math.min(...vals);
  const range = max - min || 1;
  const pad = 3;
  return vals
    .map((v, i) => {
      const x = vals.length > 1 ? (i / (vals.length - 1)) * (w - pad * 2) + pad : w / 2;
      const y = h - pad - ((v - min) / range) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}
</script>
