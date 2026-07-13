<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <!-- Head -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Bonus &amp; incentives</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">Monthly payout · coaching incentives</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="inline-flex items-center gap-1.5 h-9 px-3.5 text-[13px] font-medium rounded-lg bg-white text-stone-700 ring-1 ring-stone-200 hover:ring-stone-300 transition-colors whitespace-nowrap">
          <Icon name="file-text" :size="15" /> Export
        </button>
        <button class="inline-flex items-center gap-1.5 h-9 px-3.5 text-[13px] font-medium rounded-lg text-white ring-1 transition-colors whitespace-nowrap"
                style="background: var(--accent-600); border-color: var(--accent-600);"
                @click="runPayout">
          <Icon name="wallet" :size="15" /> Run payout
        </button>
      </div>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0"><Icon name="wallet" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Total pool</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none font-mono">{{ fmtMAD(pool) }}<span class="text-[13px] font-medium text-stone-400 ms-1">MAD</span></div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-stone-100 text-stone-600 flex items-center justify-center flex-shrink-0"><Icon name="dollar-sign" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Avg / member</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none font-mono">{{ fmtMAD(avg) }}<span class="text-[13px] font-medium text-stone-400 ms-1">MAD</span></div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0"><Icon name="check-circle" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Unlocked</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none font-mono">{{ unlocked }}/{{ rows.length }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center flex-shrink-0"><Icon name="zap" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Same-day</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none font-mono">{{ B.currentSameDay }}<span class="text-[13px] font-medium text-stone-400">%</span></div>
      </div>
    </div>

    <!-- Team kicker banner -->
    <div class="rounded-2xl p-4 ring-1 flex items-center gap-4"
         :class="kickerOn ? 'bg-gradient-to-r from-emerald-50 to-white ring-emerald-200/70' : 'bg-gradient-to-r from-amber-50 to-white ring-amber-200/70'">
      <div class="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 text-white"
           :class="kickerOn ? 'bg-emerald-500' : 'bg-amber-500'"><Icon name="users" :size="22" /></div>
      <div class="flex-1 min-w-0">
        <div class="text-[14px] font-semibold text-stone-900">Team kicker · +{{ fmtMAD(B.teamKicker) }} MAD for every member</div>
        <div class="text-[12px] text-stone-600 mt-0.5">
          <template v-if="kickerOn">Floor hit {{ B.currentSameDay }}% same-day ship — kicker unlocked.</template>
          <template v-else>Floor at {{ B.currentSameDay }}% · {{ toGo }}% to unlock team kicker (target {{ B.teamSameDayTarget }}%).</template>
        </div>
      </div>
      <div class="w-[120px] flex-shrink-0 hidden sm:block">
        <div class="h-2 rounded-full bg-white ring-1 ring-stone-200 overflow-hidden">
          <div class="h-full rounded-full" :class="kickerOn ? 'bg-emerald-500' : 'bg-amber-500'" :style="{ width: B.currentSameDay + '%' }" />
        </div>
        <div class="text-[10px] text-stone-400 mt-1 text-end">{{ B.currentSameDay }}% / {{ B.teamSameDayTarget }}%</div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
      <!-- payout table -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 pt-4">
          <div class="text-[13.5px] font-semibold text-stone-900">Projected payout</div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">This month · {{ B.workedDays }}/{{ B.monthDays }} days</div>
        </div>
        <div class="overflow-x-auto mt-2">
          <table class="w-full min-w-[720px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5 w-10">#</th>
                <th class="text-start px-4 py-2.5">Members</th>
                <th class="text-end px-4 py-2.5 hidden md:table-cell">Output</th>
                <th class="text-end px-4 py-2.5">SLA</th>
                <th class="text-start px-4 py-2.5">Quality gate</th>
                <th class="text-end px-4 py-2.5 hidden sm:table-cell">Streak</th>
                <th class="text-end px-4 py-2.5">Payout</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="(r, i) in rows" :key="r.m.id" class="hover:bg-stone-50 transition-colors">
                <td class="px-4 py-2.5">
                  <span class="text-[12px] font-bold tabular-nums" :class="i === 0 ? 'text-amber-500' : 'text-stone-400'">{{ i + 1 }}</span>
                </td>
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2.5">
                    <span class="w-[26px] h-[26px] rounded-full grid place-items-center text-white text-[10px] font-semibold flex-shrink-0"
                          :style="{ background: i === 0 ? '#f59e0b' : '#6366f1' }">{{ initials(byId(r.m.id).name) }}</span>
                    <div class="min-w-0">
                      <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ byId(r.m.id).short }}</div>
                      <div class="text-[10.5px] text-stone-400">{{ roleLabel(r.m.role) }}</div>
                    </div>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-end text-[12.5px] text-stone-700 tabular-nums hidden md:table-cell">{{ r.m.perf.count }} <span class="text-[10px] text-stone-400">{{ r.m.perf.unit }}</span></td>
                <td class="px-4 py-2.5 text-end">
                  <span class="text-[12.5px] font-semibold tabular-nums" :class="r.m.perf.sla >= 90 ? 'text-emerald-600' : 'text-amber-600'">{{ r.m.perf.sla }}%</span>
                </td>
                <td class="px-4 py-2.5">
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium whitespace-nowrap ring-1"
                        :class="r.b.gatePass ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-rose-50 text-rose-700 ring-rose-200'">
                    <span class="w-1.5 h-1.5 rounded-full" :class="r.b.gatePass ? 'bg-emerald-500' : 'bg-rose-500'" />{{ r.b.gatePass ? 'Unlocked' : 'Locked' }}
                  </span>
                </td>
                <td class="px-4 py-2.5 text-end hidden sm:table-cell">
                  <span class="inline-flex items-center gap-0.5 text-[11.5px] text-amber-600 font-medium tabular-nums"><Icon name="zap" :size="11" />{{ r.b.streakDays }}d</span>
                </td>
                <td class="px-4 py-2.5 text-end">
                  <span class="text-[13px] font-semibold text-stone-900 tabular-nums font-mono">{{ fmtMAD(r.b.projected) }}</span> <span class="text-[10px] text-stone-400">MAD</span>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="border-t border-stone-200 bg-stone-50/60 text-[12.5px] font-semibold">
                <td class="px-4 py-2.5" colspan="6">Total pool</td>
                <td class="px-4 py-2.5 text-end text-stone-900 tabular-nums font-mono">{{ fmtMAD(pool) }} <span class="text-[10px] font-normal text-stone-400">MAD</span></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <!-- weekly rewards + rules -->
      <div class="space-y-4">
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
          <div class="px-4 pt-4 text-[13.5px] font-semibold text-stone-900">Weekly top 3</div>
          <div class="p-3 space-y-2">
            <div v-for="(r, i) in rows.slice(0, 3)" :key="r.m.id" class="flex items-center gap-2.5 px-2 py-1.5 rounded-lg bg-stone-50/60">
              <span class="text-[15px]">{{ ['🥇', '🥈', '🥉'][i] }}</span>
              <span class="w-[26px] h-[26px] rounded-full grid place-items-center text-white text-[10px] font-semibold flex-shrink-0"
                    :style="{ background: '#6366f1' }">{{ initials(byId(r.m.id).name) }}</span>
              <span class="text-[12.5px] font-medium text-stone-900 flex-1 truncate">{{ byId(r.m.id).short }}</span>
              <span class="text-[12.5px] font-semibold text-emerald-600 tabular-nums font-mono">+{{ B.weeklyTop[i] }} <span class="text-[10px] text-stone-400">MAD</span></span>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
          <div class="px-4 pt-4 text-[13.5px] font-semibold text-stone-900">How it works</div>
          <div class="p-4">
            <ul class="space-y-2.5 text-[12px] text-stone-600">
              <li v-for="(rule, i) in rules" :key="i" class="flex items-start gap-2">
                <Icon :name="rule.icon" :size="14" class="mt-0.5 flex-shrink-0" style="color: var(--accent-600);" />
                <span class="text-pretty">{{ rule.text }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import { fmtMAD, byId } from "@/lib/handoffData";

const { success, warn } = useToast();

// TEAM_MEMBERS (with perf) and the bonus engine are not exported from
// handoffData.js — inlined from design_handoff/logistics/data.jsx.
const TEAM_MEMBERS = [
  { id: "marouane", role: "picker",     tier: "top",      perf: { count: 34,  unit: "picks",   sla: 94 } },
  { id: "anass",    role: "dispatcher", tier: "top",      perf: { count: 27,  unit: "picks",   sla: 91 } },
  { id: "asmaa",    role: "picker",     tier: "steady",   perf: { count: 22,  unit: "picks",   sla: 89 } },
  { id: "saad",     role: "picker",     tier: "coaching", perf: { count: 18,  unit: "picks",   sla: 86 } },
  { id: "oussama",  role: "picker",     tier: "steady",   perf: { count: 15,  unit: "picks",   sla: 83 } },
  { id: "said",     role: "picker",     tier: "coaching", perf: { count: 12,  unit: "picks",   sla: 80 } },
  { id: "reda",     role: "packer",     tier: "top",      perf: { count: 242, unit: "parcels", sla: 92 } },
  { id: "nadia",    role: "returns",    tier: "steady",   perf: { count: 31,  unit: "returns", sla: 88 } },
  { id: "sara",     role: "manager",    tier: "top",      perf: { count: 0,   unit: "—",       sla: 0 } },
];

const B = {
  perPick: 2, onTime: 1, zeroErrorDay: 15, dailyTargetBonus: 30,
  slaGate: 90, errorGate: 2, monthlyCap: 1500, streakStepPct: 10, streakCapPct: 30,
  tierMult: { top: 1.15, steady: 1.0, coaching: 1.05 },
  weeklyTop: [200, 100, 50], teamKicker: 120, teamSameDayTarget: 90, currentSameDay: 87,
  workedDays: 18, monthDays: 22,
};

function computeBonus(m) {
  const p = m.perf;
  if (!p || !p.sla) return null;
  const daily = p.count || 0;
  const monthlyOut = daily * B.workedDays;
  const tierMult = B.tierMult[m.tier] || 1;
  const targetHitDays = Math.round(B.workedDays * Math.min(1, p.sla / 95));
  const zeroErrDays = Math.max(0, Math.round(B.workedDays * (p.sla / 100) - 2));
  const streakDays = m.tier === "top" ? 7 : m.tier === "steady" ? 4 : 2;
  const streakPct = Math.min(B.streakCapPct, Math.floor(streakDays / 5) * B.streakStepPct);
  const breaches = p.sla >= 90 ? 0 : p.sla >= 85 ? 1 : 3;
  const base = Math.round(monthlyOut * B.perPick);
  const onTime = Math.round(monthlyOut * (p.sla / 100) * B.onTime);
  const zeroError = zeroErrDays * B.zeroErrorDay;
  const targetBonus = targetHitDays * B.dailyTargetBonus;
  const penalty = breaches * 25;
  const gatePass = p.sla >= B.slaGate;
  let gross = base + onTime + zeroError + targetBonus - penalty;
  gross = Math.round(gross * tierMult * (1 + streakPct / 100));
  const projected = gatePass ? Math.min(B.monthlyCap, gross) : base;
  const teamKicker = B.currentSameDay >= B.teamSameDayTarget ? B.teamKicker : 0;
  return { projected, gatePass, breaches, streakDays, streakPct, tierMult, teamKicker };
}

const rows = computed(() =>
  TEAM_MEMBERS.map((m) => ({ m, b: computeBonus(m) }))
    .filter((x) => x.b)
    .sort((a, c) => c.b.projected - a.b.projected)
);

const pool = computed(() => rows.value.reduce((a, x) => a + x.b.projected, 0));
const unlocked = computed(() => rows.value.filter((x) => x.b.gatePass).length);
const avg = computed(() => (rows.value.length ? Math.round(pool.value / rows.value.length) : 0));
const kickerOn = computed(() => B.currentSameDay >= B.teamSameDayTarget);
const toGo = computed(() => (B.teamSameDayTarget - B.currentSameDay).toFixed(1));

const rules = [
  { icon: "boxes", text: `Base ${B.perPick} MAD per pick/parcel` },
  { icon: "shield-alert", text: `Quality gate: bonus unlocks at ${B.slaGate}% SLA` },
  { icon: "zap", text: `Streak: +${B.streakStepPct}% per 5-day target streak (cap ${B.streakCapPct}%)` },
  { icon: "trending-up", text: "Tier multiplier rewards improvement, not just output" },
  { icon: "users", text: `Team kicker: +${B.teamKicker} MAD each at ${B.teamSameDayTarget}% same-day` },
  { icon: "wallet", text: `Monthly cap ${fmtMAD(B.monthlyCap)} MAD · paid end of month` },
];

function runPayout() {
  warn("عرض تجريبي — لم يتم ترحيل أي رواتب", "الصفحة غير مربوطة بالسيستم بعد");
}
function roleLabel(role) {
  return role.charAt(0).toUpperCase() + role.slice(1);
}
function initials(name) {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
}
</script>
