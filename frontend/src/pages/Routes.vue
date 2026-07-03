<template>
  <!-- Route detail (full page) -->
  <div v-if="open" class="p-5 sm:p-6 max-w-[1400px] mx-auto animate-fade-in">
    <button
      class="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"
      @click="open = null"
    >
      <Icon name="chevron-left" :size="15" />Delivery routes
    </button>

    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3">
          <span class="w-11 h-11 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center"><Icon name="globe" :size="22" /></span>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h1 class="font-mono text-[19px] font-bold text-stone-900">{{ open.no }}</h1>
              <StatusBadge :status="open.status" />
              <span
                v-if="open.exceptions > 0"
                class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap text-rose-700 bg-rose-50 ring-rose-200"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-rose-500" />{{ open.exceptions }} exc
              </span>
            </div>
            <div class="text-[12.5px] text-stone-600 mt-1 flex items-center gap-2">
              <span class="w-5 h-5 rounded-full bg-stone-200 text-stone-600 flex items-center justify-center text-[9px] font-semibold">{{ initials(open.driver) }}</span>
              {{ open.driver }} · <Icon name="map-pin" :size="12" class="text-stone-400" />{{ open.zone }}
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
            @click="info(`${open.no} · live tracking · ${open.driver}`)"
          >
            <Icon name="globe" :size="15" />Track live
          </button>
          <button class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300">
            Open in ERP <Icon name="chevron-right" :size="15" />
          </button>
        </div>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        <div class="bg-stone-50 rounded-xl px-3 py-2.5"><div class="text-[22px] font-semibold tabular-nums leading-none text-stone-900">{{ open.stops }}</div><div class="text-[11px] text-stone-500 mt-1.5">Stops</div></div>
        <div class="bg-stone-50 rounded-xl px-3 py-2.5"><div class="text-[22px] font-semibold tabular-nums leading-none text-emerald-600">{{ open.delivered }}</div><div class="text-[11px] text-stone-500 mt-1.5">Delivered today</div></div>
        <div class="bg-stone-50 rounded-xl px-3 py-2.5"><div class="text-[22px] font-semibold tabular-nums leading-none text-stone-900">{{ open.parcels - open.delivered }}</div><div class="text-[11px] text-stone-500 mt-1.5">Parcels out</div></div>
        <div class="bg-stone-50 rounded-xl px-3 py-2.5"><div class="text-[22px] font-semibold tabular-nums leading-none text-stone-900">{{ open.eta }}</div><div class="text-[11px] text-stone-500 mt-1.5">ETA</div></div>
      </div>
      <div class="mt-4">
        <div class="flex items-center justify-between text-[11px] mb-1">
          <span class="text-stone-500 tabular-nums">{{ open.delivered }}/{{ open.parcels }} parcels</span>
          <span class="font-semibold tabular-nums" :style="{ color: pctOf(open) >= 1 ? '#10b981' : '#06b6d4' }">{{ Math.round(pctOf(open) * 100) }}%</span>
        </div>
        <div class="h-2 rounded-full bg-stone-100 overflow-hidden">
          <div class="h-full rounded-full" :style="{ width: `${Math.max(3, pctOf(open) * 100)}%`, background: pctOf(open) >= 1 ? '#10b981' : '#06b6d4' }" />
        </div>
      </div>
    </div>

    <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
      <div class="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
        <div><div class="text-[13px] font-semibold text-stone-900">Stops</div><div class="text-[11px] text-stone-400">{{ open.zone }}</div></div>
        <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 text-cyan-700 bg-cyan-50 ring-cyan-200"><span class="w-1.5 h-1.5 rounded-full bg-cyan-500" />{{ open.stops }} stops</span>
      </div>
      <div class="p-4">
        <ol class="relative max-w-[760px]">
          <li v-for="(s, i) in detailStops" :key="i" class="relative flex gap-3.5 pb-3 last:pb-0">
            <span
              v-if="i !== detailStops.length - 1"
              class="absolute top-9 w-px"
              :class="s.done ? 'bg-emerald-200' : 'bg-stone-200'"
              :style="{ insetInlineStart: '15px' }"
            />
            <span
              class="relative z-10 w-[31px] h-[31px] rounded-lg flex items-center justify-center text-[12px] font-bold flex-shrink-0"
              :class="s.done ? 'bg-emerald-500 text-white' : s.exception ? 'bg-rose-500 text-white' : 'bg-white ring-1 ring-stone-300 text-stone-500'"
            >
              <Icon v-if="s.done" name="check" :size="15" />
              <Icon v-else-if="s.exception" name="alert-circle" :size="15" />
              <template v-else>{{ s.i + 1 }}</template>
            </span>
            <div
              class="min-w-0 flex-1 rounded-xl ring-1 p-3"
              :class="s.done ? 'ring-emerald-200 bg-emerald-50/40' : s.exception ? 'ring-rose-200 bg-rose-50/40' : 'ring-stone-200 bg-white'"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-[13.5px] font-medium text-stone-900 truncate">{{ s.customer }}</span>
                <span class="text-[11.5px] font-medium tabular-nums flex-shrink-0" :class="s.done ? 'text-emerald-600' : s.exception ? 'text-rose-500' : 'text-stone-400'">{{ s.done ? "✓ Delivered" : s.exception ? "Failed" : s.eta }}</span>
              </div>
              <div class="text-[11.5px] text-stone-500 flex items-center gap-1.5 mt-1"><Icon name="map-pin" :size="11" class="text-stone-400" />{{ s.addr }}</div>
            </div>
          </li>
        </ol>
      </div>
    </div>
  </div>

  <!-- Routes board -->
  <div v-else class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <div class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Delivery routes</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">Last-mile trips · {{ CARRIER }}</p>
      </div>
      <button
        class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg text-white"
        :style="{ background: 'var(--accent-600)' }"
        @click="info('Plan a new delivery trip')"
      >
        <Icon name="plus" :size="15" />Plan trip
      </button>
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-2">
          <span class="w-7 h-7 rounded-lg flex items-center justify-center" :class="[k.bg, k.fg]"><Icon :name="k.icon" :size="15" /></span>
          <span class="text-[11px] font-medium text-stone-500">{{ k.label }}</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums leading-none">{{ k.value }}</div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div
        v-for="r in ROUTES"
        :key="r.no"
        class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 cursor-pointer hover:ring-stone-300 hover:shadow-[0_8px_24px_-8px_rgba(0,0,0,0.12)] hover:-translate-y-0.5 transition-all"
        @click="open = r"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-2.5">
            <span class="w-10 h-10 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center"><Icon name="globe" :size="20" /></span>
            <div>
              <div class="flex items-center gap-2">
                <span class="font-mono text-[13px] font-semibold text-stone-900">{{ r.no }}</span>
                <StatusBadge :status="r.status" />
              </div>
              <div class="text-[11.5px] text-stone-500 mt-0.5 flex items-center gap-1.5"><Icon name="map-pin" :size="11" class="text-stone-400" />{{ r.zone }}</div>
            </div>
          </div>
          <span
            v-if="r.exceptions > 0"
            class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap text-rose-700 bg-rose-50 ring-rose-200"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500" />{{ r.exceptions }} exc
          </span>
        </div>
        <div class="flex items-center gap-2.5 mt-3">
          <span class="w-6 h-6 rounded-full bg-stone-200 text-stone-600 flex items-center justify-center text-[9px] font-semibold">{{ initials(r.driver) }}</span>
          <span class="text-[12px] text-stone-600 flex-1">{{ r.driver }}</span>
          <span class="text-[11.5px] text-stone-500 tabular-nums">{{ r.stops }} stops</span>
          <span v-if="r.eta !== '—'" class="text-[11.5px] text-stone-500 tabular-nums">· ETA {{ r.eta }}</span>
        </div>
        <div class="mt-3">
          <div class="flex items-center justify-between text-[11px] mb-1">
            <span class="text-stone-500 tabular-nums">{{ r.delivered }}/{{ r.parcels }} parcels</span>
            <span class="font-semibold tabular-nums" :style="{ color: pctOf(r) >= 1 ? '#10b981' : '#06b6d4' }">{{ Math.round(pctOf(r) * 100) }}%</span>
          </div>
          <div class="h-2 rounded-full bg-stone-100 overflow-hidden">
            <div class="h-full rounded-full" :style="{ width: `${Math.max(3, pctOf(r) * 100)}%`, background: pctOf(r) >= 1 ? '#10b981' : '#06b6d4' }" />
          </div>
        </div>
        <div class="mt-3 flex justify-end">
          <button
            class="inline-flex items-center gap-1.5 px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
            @click.stop="open = r"
          >
            <Icon name="map-pin" :size="13" />View stops
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, h } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import { CARRIER } from "@/lib/handoffData";

const { info } = useToast();

// ── local data (not exported from handoffData) ─────────────────────
const ROUTES = [
  { no: "TRIP-0043", driver: "Karim Tahiri",   zone: "Mohammedia",              stops: 14, parcels: 19, delivered: 0,  status: "Loading",   eta: "17:20", exceptions: 0 },
  { no: "TRIP-0042", driver: "Younes Bennani",  zone: "Casablanca Centre",       stops: 18, parcels: 24, delivered: 11, status: "En route",  eta: "16:40", exceptions: 0 },
  { no: "TRIP-0040", driver: "Said Mernissi",   zone: "Maârif / Gauthier",       stops: 16, parcels: 21, delivered: 14, status: "En route",  eta: "16:05", exceptions: 2 },
  { no: "TRIP-0041", driver: "Hamid Raji",      zone: "Aïn Sebaâ / Sidi Moumen", stops: 22, parcels: 31, delivered: 31, status: "Completed", eta: "—",     exceptions: 0 },
];

const RV_STATUS = {
  Loading: { txt: "text-amber-700", bg: "bg-amber-50", ring: "ring-amber-200", dot: "bg-amber-500" },
  "En route": { txt: "text-cyan-700", bg: "bg-cyan-50", ring: "ring-cyan-200", dot: "bg-cyan-500" },
  Completed: { txt: "text-emerald-700", bg: "bg-emerald-50", ring: "ring-emerald-200", dot: "bg-emerald-500" },
  Cancelled: { txt: "text-rose-700", bg: "bg-rose-50", ring: "ring-rose-200", dot: "bg-rose-500" },
};
const StatusBadge = (props) => {
  const t = RV_STATUS[props.status] || RV_STATUS.Loading;
  return h("span", {
    class: ["inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap", t.txt, t.bg, t.ring],
  }, [
    h("span", { class: ["w-1.5 h-1.5 rounded-full", t.dot] }),
    props.status,
  ]);
};

const open = ref(null);

const pctOf = (r) => (r.parcels ? r.delivered / r.parcels : 0);

const kpis = computed(() => {
  const active = ROUTES.filter((r) => r.status === "En route" || r.status === "Loading").length;
  const out = ROUTES.reduce((a, r) => a + (r.parcels - r.delivered), 0);
  const delivered = ROUTES.reduce((a, r) => a + r.delivered, 0);
  const avgStops = Math.round(ROUTES.reduce((a, r) => a + r.stops, 0) / ROUTES.length);
  return [
    { label: "Active trips", value: active, icon: "globe", bg: "bg-cyan-50", fg: "text-cyan-600" },
    { label: "Parcels out", value: out, icon: "package", bg: "bg-amber-50", fg: "text-amber-600" },
    { label: "Delivered today", value: delivered, icon: "check-circle", bg: "bg-emerald-50", fg: "text-emerald-600" },
    { label: "Avg stops", value: avgStops, icon: "map-pin", bg: "bg-stone-100", fg: "text-stone-600" },
  ];
});

const detailStops = computed(() => {
  const route = open.value;
  if (!route) return [];
  const customers = ["Khadija abhaoui", "Sara Razine", "Imane Tazi", "Najat Bennani", "Hind El Yazami", "Widad Widad", "Ghizlane Dargal", "Amal Mourid", "Rim Cherkaoui", "Loubna Saidi"];
  return Array.from({ length: route.stops }).map((_, i) => {
    const done = i < route.delivered;
    const exception = !done && route.exceptions > 0 && i >= route.stops - route.exceptions;
    const hh = 9 + Math.floor(i * 0.5), mm = (i * 23) % 60;
    return {
      i,
      customer: customers[i % customers.length],
      addr: `${route.zone} · ${100 + i * 7}`,
      done,
      exception,
      eta: `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`,
    };
  });
});

function initials(name) {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
}
</script>
