<template>
  <div class="max-w-[1100px] mx-auto px-6 py-6 animate-fade-in">
    <!-- header -->
    <div class="flex items-start justify-between gap-3 flex-wrap mb-4">
      <div>
        <h1 class="text-[19px] font-semibold text-stone-900 tracking-[-0.01em]">Wave picking</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">Scheduled batch releases · cutoff-aware</p>
      </div>
      <button
        class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] transition-colors"
        @click="autoPlan"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
        Auto-plan next wave
      </button>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-1.5 text-[11px] font-medium" :class="k.txt">
          <span v-html="k.icon" class="inline-flex" />
          <span class="text-stone-500">{{ k.label }}</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums leading-none mt-2">{{ k.value }}</div>
      </div>
    </div>

    <!-- wave rows -->
    <div class="space-y-3">
      <div
        v-for="w in rows"
        :key="w.no"
        class="bg-white rounded-xl ring-1 p-4"
        :class="w.status === 'active' ? 'ring-blue-200' : 'ring-stone-200/70'"
      >
        <div class="flex items-center justify-between gap-3 flex-wrap">
          <div class="flex items-center gap-3">
            <span
              class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
              :class="w.status === 'done' ? 'bg-emerald-50 text-emerald-600' : w.status === 'active' ? 'bg-blue-50 text-blue-600' : 'bg-amber-50 text-amber-600'"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="20" height="20"><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></svg>
            </span>
            <div>
              <div class="flex items-center gap-2">
                <span class="font-mono text-[14px] font-bold text-stone-900">{{ w.no }}</span>
                <span
                  class="inline-flex items-center gap-1 px-1.5 h-[18px] rounded text-[10.5px] font-medium ring-1"
                  :class="statusChip(w.status)"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="statusDot(w.status)" />{{ WV_LABEL[w.status] }}
                </span>
              </div>
              <div class="text-[11.5px] text-stone-500 mt-0.5">
                {{ w.releaseAt }} · {{ w.orders }} orders · {{ w.pickers }} pickers · {{ w.zones.join(" + ") }}
              </div>
            </div>
          </div>

          <button
            v-if="w.status === 'queued'"
            class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] transition-colors"
            @click="release(w.no)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
            Release wave
          </button>
          <span
            v-else-if="w.status === 'active'"
            class="inline-flex items-center gap-1 px-1.5 h-[18px] rounded text-[10.5px] font-medium text-blue-700 bg-blue-50 ring-1 ring-blue-200"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500" />{{ w.progress }}%
          </span>
          <span v-else class="inline-flex items-center gap-1 text-[12px] text-emerald-600 font-medium">
            <Icon name="check-circle" :size="14" />Completed
          </span>
        </div>

        <div v-if="w.status !== 'queued'" class="mt-3">
          <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden">
            <div
              class="h-full rounded-full transition-all"
              :class="w.status === 'done' ? 'bg-emerald-500' : 'bg-blue-500'"
              :style="{ width: w.progress + '%' }"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";

const { success } = useToast();

// ── Wave data (from data.jsx LG_WAVES) ─────────────────────────────────
const WAVES = [
  { no: "WAVE-08", window: "Cutoff 14:00", releaseAt: "11:30", orders: 42, pickers: 4, zones: ["FAST", "Cosmetic"], status: "active", progress: 64, cutoffMin: 156 },
  { no: "WAVE-09", window: "Cutoff 14:00", releaseAt: "12:30", orders: 38, pickers: 4, zones: ["SLOW", "Textile"], status: "queued", progress: 0, cutoffMin: 156 },
  { no: "WAVE-07", window: "Cutoff 14:00", releaseAt: "10:30", orders: 51, pickers: 5, zones: ["MU", "Accessory"], status: "done", progress: 100, cutoffMin: 0 },
];

const WV_LABEL = { active: "In progress", queued: "Queued", done: "Completed" };

const rows = ref(WAVES.map((w) => ({ ...w })));

const layersIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`;
const clockIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
const boxIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>`;
const alertIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

const kpis = computed(() => [
  { label: "In progress", value: rows.value.filter((w) => w.status === "active").length, icon: layersIcon, txt: "text-blue-600" },
  { label: "Queued", value: rows.value.filter((w) => w.status === "queued").length, icon: clockIcon, txt: "text-amber-600" },
  { label: "orders", value: rows.value.reduce((a, w) => a + w.orders, 0), icon: boxIcon, txt: "text-stone-500" },
  { label: "Cutoff in", value: "2h 36m", icon: alertIcon, txt: "text-violet-600" },
]);

function statusChip(s) {
  return {
    active: "text-blue-700 bg-blue-50 ring-blue-200",
    queued: "text-amber-700 bg-amber-50 ring-amber-200",
    done: "text-emerald-700 bg-emerald-50 ring-emerald-200",
  }[s];
}
function statusDot(s) {
  return { active: "bg-blue-500", queued: "bg-amber-500", done: "bg-emerald-500" }[s];
}

function release(no) {
  const w = rows.value.find((x) => x.no === no);
  const orders = w?.orders;
  rows.value = rows.value.map((x) => (x.no === no ? { ...x, status: "active", progress: 2 } : x));
  success(`${no} released · ${orders} pick lists assigned`);
}

function autoPlan() {
  success("Next wave auto-planned by zone + cutoff");
}
</script>
