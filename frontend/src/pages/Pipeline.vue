<template>
  <div class="max-w-[1320px] mx-auto px-6 py-6">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4 mb-5 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Orders</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">
          Confirmed orders — logistics queue · {{ orders.length }} orders · {{ WAREHOUSE }}
        </p>
      </div>
      <button
        class="inline-flex items-center gap-1.5 px-3 h-9 text-[13px] font-medium text-stone-700 bg-white rounded-lg ring-1 ring-stone-200 hover:ring-stone-300 transition-colors whitespace-nowrap"
      >
        <Icon name="file-text" :size="15" /> Export
      </button>
    </div>

    <!-- KPI strip -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <div
        v-for="k in kpis"
        :key="k.label"
        class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3.5"
      >
        <div class="flex items-center gap-1.5 text-[11.5px] font-medium text-stone-500">
          <span
            class="w-6 h-6 rounded-lg flex items-center justify-center"
            :class="k.tone"
          >
            <Icon :name="k.icon" :size="13" />
          </span>
          {{ k.label }}
        </div>
        <div class="text-[22px] font-semibold text-stone-900 tabular-nums mt-1.5 leading-none">
          {{ k.value }}<span v-if="k.unit" class="text-[11px] text-stone-400 ms-1 font-normal">{{ k.unit }}</span>
        </div>
      </div>
    </div>

    <!-- search + SLA filters -->
    <div class="flex items-center gap-2 mb-3 flex-wrap">
      <div class="relative flex-1 min-w-[200px]">
        <Icon name="search" :size="14" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input
          v-model="q"
          placeholder="Search order, AWB, pick list…"
          class="w-full h-9 ps-9 pe-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none"
        />
      </div>
      <div class="flex items-center gap-1.5 overflow-x-auto">
        <button
          v-for="s in slaFilters"
          :key="s.key"
          class="px-2.5 h-7 text-[12px] font-medium rounded-lg ring-1 transition-colors whitespace-nowrap"
          :class="sla === s.key ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'"
          @click="sla = s.key"
        >
          {{ s.label }}
        </button>
      </div>
    </div>

    <!-- stage filters -->
    <div class="flex items-center gap-1.5 mb-3 overflow-x-auto pb-1">
      <button
        v-for="s in stageFilters"
        :key="s.key"
        class="px-2.5 h-7 text-[12px] font-medium rounded-lg ring-1 transition-colors whitespace-nowrap"
        :class="stage === s.key ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'"
        @click="stage = s.key"
      >
        {{ s.label }}
      </button>
    </div>

    <!-- table -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[820px]">
          <thead>
            <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th class="text-start px-4 py-2.5">Order</th>
              <th class="text-start px-4 py-2.5">Customer</th>
              <th class="text-start px-4 py-2.5 hidden md:table-cell">Channel</th>
              <th class="text-start px-4 py-2.5 hidden lg:table-cell">Zone</th>
              <th class="text-start px-4 py-2.5">Picker</th>
              <th class="text-start px-4 py-2.5">Stage</th>
              <th class="text-start px-4 py-2.5">SLA</th>
              <th class="text-start px-4 py-2.5 hidden sm:table-cell">Placed</th>
              <th class="text-end px-4 py-2.5">Value</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr
              v-for="o in rows"
              :key="o.no"
              class="cursor-pointer transition-colors hover:bg-stone-50"
              @click="openOrder(o)"
            >
              <td class="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900 whitespace-nowrap">{{ o.no }}</td>
              <td class="px-4 py-2.5 text-[12.5px] text-stone-800 truncate max-w-[150px]">{{ o.customer }}</td>
              <td class="px-4 py-2.5 hidden md:table-cell">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 whitespace-nowrap"
                  :class="channelChip(o.channel)"
                >
                  {{ CHANNELS[o.channel]?.label || o.channel }}
                </span>
              </td>
              <td class="px-4 py-2.5 text-[11.5px] text-stone-500 hidden lg:table-cell whitespace-nowrap">{{ o.zone }}</td>
              <td class="px-4 py-2.5">
                <div v-if="o.picker" class="flex items-center gap-1.5">
                  <span class="w-5 h-5 rounded-full bg-stone-200 text-stone-600 text-[9px] font-bold flex items-center justify-center flex-shrink-0">{{ initials(byId(o.picker).name) }}</span>
                  <span class="text-[11.5px] text-stone-600 hidden xl:inline">{{ byId(o.picker).short }}</span>
                </div>
                <span v-else class="text-[11.5px] text-stone-300">—</span>
              </td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 whitespace-nowrap"
                  :class="[STAGE[o.stage].txt, STAGE[o.stage].bg, STAGE[o.stage].ring]"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="STAGE[o.stage].dot" />
                  {{ STAGE_LABEL[o.stage] }}
                </span>
              </td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 whitespace-nowrap"
                  :class="[SLA[o.sla].txt, SLA[o.sla].bg, SLA[o.sla].ring]"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="SLA[o.sla].dot" />
                  {{ SLA_LABEL[o.sla] }}
                </span>
              </td>
              <td class="px-4 py-2.5 hidden sm:table-cell whitespace-nowrap">
                <span class="text-[12px] text-stone-600 tabular-nums">{{ o._p.hhmm }}</span>
                <span class="text-[10.5px] text-stone-400"> · {{ o._p.age }}</span>
              </td>
              <td class="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums whitespace-nowrap">{{ fmtMAD(o.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="rows.length === 0" class="text-center text-[12.5px] text-stone-400 py-12">
        No orders match these filters.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import {
  ORDERS as DEMO_ORDERS, STAGE, STAGE_LABEL, SLA, SLA_LABEL,
  CHANNELS, byId, fmtMAD, WAREHOUSE,
} from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";

const router = useRouter();

const q = ref("");
const stage = ref("all");
const sla = ref("all");

// Live-or-demo orders. `orders.list` (floor scope) fills this once installed;
// falls back to the demo seed in local preview / on error.
const orders = ref(DEMO_ORDERS);

onMounted(async () => {
  const live = await liveOr(null, () => api("orders.list", { scope: "floor", limit: 60 }));
  if (live && live.length) orders.value = live;
});

const kpis = computed(() => [
  { label: "orders", icon: "package", tone: "bg-stone-100 text-stone-500", value: orders.value.length },
  { label: "At risk now", icon: "clock", tone: "bg-amber-50 text-amber-600", value: orders.value.filter((o) => o.sla === "atrisk").length },
  { label: "SLA breaches", icon: "alert-circle", tone: "bg-rose-50 text-rose-600", value: orders.value.filter((o) => o.sla === "breached").length },
  { label: "Open value", icon: "dollar-sign", tone: "bg-emerald-50 text-emerald-600", value: fmtMAD(rows.value.reduce((a, o) => a + o.total, 0)), unit: "MAD" },
]);

const slaFilters = [
  { key: "all", label: "SLA: All" },
  { key: "ontrack", label: "On Track" },
  { key: "atrisk", label: "At Risk" },
  { key: "breached", label: "Breached" },
];

const stageFilters = [
  { key: "all", label: "All stages" },
  { key: "pending", label: "Pending" },
  { key: "picking", label: "Picking" },
  { key: "picked", label: "Picked" },
  { key: "label", label: "Label Printed" },
  { key: "shipped", label: "Shipped" },
  { key: "transit", label: "In Transit" },
  { key: "exception", label: "Exception" },
  { key: "delivered", label: "Delivered" },
  { key: "returned", label: "Returned" },
];

// Channel chip tone → Tailwind classes (label + tone)
const CHANNEL_TONES = {
  emerald: "text-emerald-700 bg-emerald-50 ring-emerald-200",
  violet: "text-violet-700 bg-violet-50 ring-violet-200",
  amber: "text-amber-700 bg-amber-50 ring-amber-200",
  slate: "text-slate-700 bg-slate-50 ring-slate-200",
  green: "text-green-700 bg-green-50 ring-green-200",
};
function channelChip(key) {
  return CHANNEL_TONES[CHANNELS[key]?.tone] || "text-stone-600 bg-stone-100 ring-stone-200";
}

function initials(name) {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
}

// deterministic placed-time + age per order
function placed(o) {
  const n = parseInt((o.no.match(/\d+/) || [10])[0]);
  const ageMin = (n * 37) % 540 + (o.stage === "pending" ? 4 : 30);
  const d = new Date();
  d.setHours(7, 0, 0, 0);
  d.setMinutes(d.getMinutes() + ((n * 53) % 600));
  const hhmm = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  const age = ageMin >= 60 ? `${Math.floor(ageMin / 60)}h` : `${ageMin}m`;
  return { hhmm, ageMin, age };
}

const rows = computed(() => {
  const filtered = orders.value.filter((o) => {
    if (stage.value !== "all" && o.stage !== stage.value) return false;
    if (sla.value !== "all" && o.sla !== sla.value) return false;
    if (q.value && !(`${o.no} ${o.customer} ${o.awb || ""}`.toLowerCase().includes(q.value.toLowerCase()))) return false;
    return true;
  }).map((o) => ({ ...o, _p: placed(o) }));
  return filtered.sort((a, b) => a._p.ageMin - b._p.ageMin);
});

function openOrder(o) {
  router.push({ name: "OrderDetail", params: { name: o.no.replace("#", "") } });
}
</script>
