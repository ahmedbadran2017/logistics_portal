<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <!-- head -->
    <div>
      <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Carrier scorecard</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5">Performance by zone + smart routing</p>
    </div>

    <!-- routing suggestions -->
    <div v-if="routing.length > 0" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-3 border-b border-stone-100 flex items-center justify-between gap-2">
        <div class="text-[13px] font-semibold text-stone-900">Smart routing suggestions</div>
        <span
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 whitespace-nowrap"
          :style="{ color: 'var(--accent-600)', background: 'var(--accent-50)', '--tw-ring-color': 'var(--accent-200)' }"
        >
          <span class="w-1.5 h-1.5 rounded-full" :style="{ background: 'var(--accent-600)' }" />
          {{ routing.length }}
        </span>
      </div>
      <div class="p-3 space-y-2">
        <div
          v-for="(r, i) in routing"
          :key="i"
          class="flex items-center gap-2.5 rounded-xl ring-1 px-3 py-2"
          :style="{ background: 'color-mix(in srgb, var(--accent-50) 40%, transparent)', '--tw-ring-color': 'color-mix(in srgb, var(--accent-200) 50%, transparent)' }"
        >
          <Icon name="globe" :size="15" class="flex-shrink-0" :style="{ color: 'var(--accent-600)' }" />
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-medium text-stone-900">{{ r.zone }}: {{ r.from }} → {{ r.to }}</div>
            <div class="text-[11px] text-stone-500 truncate">{{ r.reason }}</div>
          </div>
          <span class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 text-emerald-700 bg-emerald-50 ring-emerald-200 whitespace-nowrap tabular-nums">{{ r.gain }}</span>
          <button
            class="inline-flex items-center gap-1 px-2.5 h-7 text-[12px] font-medium text-white rounded-lg whitespace-nowrap transition-colors"
            :style="{ background: 'var(--accent-600)' }"
            @click="success(`${r.zone} re-routed to ${r.to}`)"
          >
            <Icon name="arrow-right" :size="13" /> Re-route
          </button>
        </div>
      </div>
    </div>

    <!-- carrier comparison cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
      <button
        v-for="s in scores"
        :key="s.carrier"
        class="text-start bg-white rounded-xl ring-1 p-4 transition-all"
        :class="sel === s.carrier ? 'ring-2 ring-stone-900' : 'ring-stone-200/70 hover:ring-stone-300'"
        @click="sel = s.carrier"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="w-8 h-8 rounded-lg bg-cyan-50 text-cyan-700 flex items-center justify-center text-[11px] font-bold font-mono">{{ s.code }}</span>
            <span class="text-[13px] font-semibold text-stone-900">{{ s.carrier }}</span>
          </div>
          <span
            v-if="s.active"
            class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 text-emerald-700 bg-emerald-50 ring-emerald-200 whitespace-nowrap"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Active
          </span>
          <span
            v-else
            class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 text-stone-600 bg-stone-100 ring-stone-200 whitespace-nowrap"
          >
            Standby
          </span>
        </div>
        <div class="grid grid-cols-2 gap-2 mt-3">
          <div>
            <div class="text-[16px] font-semibold text-emerald-600 tabular-nums leading-none font-mono">{{ s.deliveryRate }}%</div>
            <div class="text-[10px] text-stone-500 mt-1">Delivery rate</div>
          </div>
          <div>
            <div class="text-[16px] font-semibold text-stone-900 tabular-nums leading-none font-mono">{{ s.costPerParcel }}<span class="text-[10px] text-stone-400"> MAD</span></div>
            <div class="text-[10px] text-stone-500 mt-1">Cost / parcel</div>
          </div>
          <div>
            <div class="text-[16px] font-semibold text-rose-500 tabular-nums leading-none font-mono">{{ s.exceptionRate }}%</div>
            <div class="text-[10px] text-stone-500 mt-1">Exception rate</div>
          </div>
          <div>
            <div class="text-[16px] font-semibold text-stone-900 tabular-nums leading-none font-mono">{{ s.avgTransit }}d</div>
            <div class="text-[10px] text-stone-500 mt-1">Avg transit</div>
          </div>
        </div>
      </button>
    </div>

    <!-- selected carrier · by zone -->
    <div v-if="c" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-3 border-b border-stone-100">
        <div class="text-[13px] font-semibold text-stone-900">{{ c.carrier }} · By zone</div>
      </div>
      <div class="divide-y divide-stone-100">
        <div v-for="z in c.zones" :key="z.zone" class="flex items-center gap-3 px-4 py-2.5">
          <span class="text-[12.5px] font-medium text-stone-900 w-[120px]">{{ z.zone }}</span>
          <div class="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden">
            <div
              class="h-full rounded-full"
              :class="z.rate >= 92 ? 'bg-emerald-500' : z.rate >= 87 ? 'bg-amber-500' : 'bg-rose-500'"
              :style="{ width: z.rate + '%' }"
            />
          </div>
          <span class="text-[12px] font-semibold text-stone-800 tabular-nums w-[40px] text-end font-mono">{{ z.rate }}%</span>
          <span class="text-[11px] text-stone-400 tabular-nums w-[44px] text-end font-mono">{{ z.transit }}d</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import { api, liveOr } from "@/lib/resource";

const { success } = useToast();

// Carrier scorecard data (from design_handoff/logistics/data.jsx)
const SCORES = [
  {
    carrier: "Cathedis", code: "CTH", deliveryRate: 91.2, exceptionRate: 4.8, avgTransit: 1.8, costPerParcel: 22, active: true,
    zones: [
      { zone: "Casablanca", rate: 95, transit: 1.2 },
      { zone: "Rabat", rate: 93, transit: 1.6 },
      { zone: "Tanger", rate: 84, transit: 2.6 },
      { zone: "Marrakech", rate: 88, transit: 2.1 },
    ],
  },
  {
    carrier: "Sendit", code: "SND", deliveryRate: 89, exceptionRate: 5.5, avgTransit: 1.9, costPerParcel: 24, active: false,
    zones: [
      { zone: "Casablanca", rate: 92, transit: 1.3 },
      { zone: "Rabat", rate: 90, transit: 1.5 },
    ],
  },
  {
    carrier: "Ozonexpress", code: "OZN", deliveryRate: 90, exceptionRate: 5.0, avgTransit: 2.2, costPerParcel: 20, active: false,
    zones: [
      { zone: "Marrakech", rate: 92, transit: 1.8 },
      { zone: "Agadir", rate: 91, transit: 2.0 },
    ],
  },
];

const routing = [
  { zone: "Tanger", from: "Cathedis", to: "Sendit", reason: "Cathedis 84% vs Sendit 92% in Tanger", gain: "+8% delivery" },
  { zone: "Marrakech", from: "Cathedis", to: "Ozonexpress", reason: "Ozon 92% & faster transit", gain: "+4% · −0.3d" },
];

// Live-or-demo data. `shipping.carriers` returns rows shaped
// { name, code, active, awbActive, deliveryRate, exceptionRate, avgTransit, zones, primary }.
// Map name→carrier; keep costPerParcel (demo-only) as fallback. In local preview
// api() fails and the demo SCORES remain.
const scores = ref(SCORES);
const sel = ref(SCORES[0].carrier);

onMounted(async () => {
  const live = await liveOr(null, () => api("shipping.carriers"));
  if (live && live.length) {
    scores.value = live.map((r) => {
      const demo = SCORES.find((d) => d.code === r.code || d.carrier === r.name) || {};
      return {
        carrier: r.name ?? demo.carrier ?? "—",
        code: r.code ?? demo.code ?? "—",
        active: r.active ?? demo.active ?? false,
        awbActive: r.awbActive ?? demo.awbActive,
        deliveryRate: r.deliveryRate ?? demo.deliveryRate ?? "—",
        exceptionRate: r.exceptionRate ?? demo.exceptionRate ?? "—",
        avgTransit: r.avgTransit ?? demo.avgTransit ?? "—",
        costPerParcel: r.costPerParcel ?? demo.costPerParcel ?? "—",
        zones: r.zones && r.zones.length ? r.zones : (demo.zones || []),
        primary: r.primary ?? demo.primary,
      };
    });
    if (!scores.value.some((x) => x.carrier === sel.value)) {
      sel.value = scores.value[0]?.carrier ?? sel.value;
    }
  }
});

const c = computed(() => scores.value.find((x) => x.carrier === sel.value));
</script>
