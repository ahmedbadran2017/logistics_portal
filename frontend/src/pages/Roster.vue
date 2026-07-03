<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <!-- Head -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Shifts &amp; roster</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">Who's on the floor today · {{ WAREHOUSE }}</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="inline-flex items-center gap-1.5 h-9 px-3.5 text-[13px] font-medium rounded-lg bg-white text-stone-700 ring-1 ring-stone-200 hover:ring-stone-300 transition-colors whitespace-nowrap">
          <Icon name="calendar" :size="15" /> Today
        </button>
        <button class="inline-flex items-center gap-1.5 h-9 px-3.5 text-[13px] font-medium rounded-lg text-white ring-1 transition-colors whitespace-nowrap"
                style="background: var(--accent-600); border-color: var(--accent-600);">
          <Icon name="plus" :size="15" /> Add shift
        </button>
      </div>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-stone-100 text-stone-600 flex items-center justify-center flex-shrink-0"><Icon name="users" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Members</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none font-mono">{{ TEAM_MEMBERS.length }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0"><Icon name="activity" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">On floor now</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-emerald-600 tabular-nums leading-none font-mono">{{ onFloor }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center flex-shrink-0"><Icon name="clock" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Scheduled</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none font-mono">{{ scheduled }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0"><Icon name="alert-circle" :size="15" /></span>
          <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Understaffed</span>
        </div>
        <div class="mt-2 text-[24px] font-semibold text-stone-900 tabular-nums leading-none font-mono">1</div>
      </div>
    </div>

    <!-- Shift columns -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div v-for="s in shiftBoards" :key="s.name" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-3 border-b border-stone-100" :class="s.gap ? 'bg-amber-50/40' : ''">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-[13.5px] font-semibold text-stone-900">{{ s.name }}</div>
              <div class="text-[11px] text-stone-500">{{ s.time }}</div>
            </div>
            <span v-if="s.gap" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-50 text-amber-700 ring-1 ring-amber-200">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-500" />Understaffed
            </span>
            <span v-else class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500" />{{ s.active }} on floor now
            </span>
          </div>
          <div class="flex items-center gap-2 mt-2.5">
            <div class="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden">
              <div class="h-full rounded-full" :class="s.gap ? 'bg-amber-500' : 'bg-emerald-500'" :style="{ width: s.pct * 100 + '%' }" />
            </div>
            <span class="text-[11px] text-stone-500 tabular-nums">{{ s.members.length }}/{{ s.cap }} capacity</span>
          </div>
        </div>
        <div class="p-2 space-y-0.5 min-h-[140px]">
          <div v-for="m in s.members" :key="m.id" class="flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-stone-50">
            <div class="relative flex-shrink-0">
              <span class="w-[26px] h-[26px] rounded-full grid place-items-center text-white text-[10px] font-semibold"
                    :style="{ background: '#6366f1' }">{{ initials(byId(m.id).name) }}</span>
              <span class="absolute -bottom-0.5 -end-0.5 w-2.5 h-2.5 rounded-full ring-2 ring-white"
                    :class="m.status === 'active' ? 'bg-emerald-500' : m.status === 'idle' ? 'bg-amber-500' : 'bg-stone-300'" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ byId(m.id).short }}</div>
              <div class="text-[10.5px] text-stone-500 flex items-center gap-1">
                <template v-if="m.status === 'offline'">{{ roleLabel(m.role) }}</template>
                <template v-else>
                  <Icon name="clock" :size="9" class="text-emerald-500" />{{ startTime(s.name) }}:{{ pad(m.id) }} · {{ roleLabel(m.role) }}
                </template>
              </div>
            </div>
            <span v-if="m.suspended" class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-rose-50 text-rose-700 ring-1 ring-rose-200">Suspended</span>
          </div>
          <div v-if="s.members.length === 0" class="text-center text-[11.5px] text-stone-300 py-8">No one scheduled</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { WAREHOUSE, byId } from "@/lib/handoffData";

// TEAM_MEMBERS is not exported from handoffData.js — inlined from
// design_handoff/logistics/data.jsx (LG_DATA_TEAM.TEAM_MEMBERS).
const TEAM_MEMBERS = [
  { id: "marouane", role: "picker",     tier: "top",      shift: "Morning",  status: "active",  suspended: false },
  { id: "anass",    role: "dispatcher", tier: "top",      shift: "Full day", status: "active",  suspended: false },
  { id: "asmaa",    role: "picker",     tier: "steady",   shift: "Morning",  status: "active",  suspended: false },
  { id: "saad",     role: "picker",     tier: "coaching", shift: "Evening",  status: "idle",    suspended: false },
  { id: "oussama",  role: "picker",     tier: "steady",   shift: "Evening",  status: "active",  suspended: false },
  { id: "said",     role: "picker",     tier: "coaching", shift: "Evening",  status: "offline", suspended: false },
  { id: "reda",     role: "packer",     tier: "top",      shift: "Full day", status: "active",  suspended: false },
  { id: "nadia",    role: "returns",    tier: "steady",   shift: "Morning",  status: "active",  suspended: false },
  { id: "sara",     role: "manager",    tier: "top",      shift: "Full day", status: "active",  suspended: false },
];

const shifts = [
  { name: "Morning", time: "06:00 – 14:00", cap: 6 },
  { name: "Evening", time: "14:00 – 22:00", cap: 5 },
  { name: "Full day", time: "08:00 – 18:00", cap: 3 },
];

const onFloor = computed(() => TEAM_MEMBERS.filter((m) => m.status === "active").length);
const scheduled = computed(() => TEAM_MEMBERS.filter((m) => m.status !== "offline").length);

const shiftBoards = computed(() =>
  shifts.map((s) => {
    const members = TEAM_MEMBERS.filter((m) => m.shift === s.name);
    const active = members.filter((m) => m.status === "active").length;
    return {
      ...s,
      members,
      active,
      pct: Math.min(1, members.length / s.cap),
      gap: members.length < s.cap,
    };
  })
);

function roleLabel(role) {
  return role.charAt(0).toUpperCase() + role.slice(1);
}
function startTime(name) {
  return name === "Morning" ? "06" : name === "Evening" ? "14" : "08";
}
function pad(id) {
  return String(((id.charCodeAt(0) * 7) % 55) + 2).padStart(2, "0");
}
function initials(name) {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
}
</script>
