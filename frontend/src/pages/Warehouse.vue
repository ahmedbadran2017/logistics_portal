<template>
  <div class="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
    <!-- header -->
    <div class="flex items-start justify-between gap-3 flex-wrap mb-4">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Warehouse</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">The real floor — every JM zone and aisle holding stock · {{ WAREHOUSE }}</p>
      </div>
      <button
        class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
        @click="$router.push({ name: 'Settings' })"
      >
        <Icon name="settings" :size="14" /> Zone pick settings
      </button>
    </div>

    <!-- KPIs -->
    <div v-if="loading" class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <div v-for="n in 4" :key="n" class="h-[86px] bg-stone-50 rounded-xl ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="map" class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3.5">
        <div class="flex items-center gap-1.5 text-[11.5px] font-medium text-stone-500">
          <span class="w-6 h-6 rounded-lg flex items-center justify-center" :class="k.tone"><Icon :name="k.icon" :size="13" /></span>
          {{ k.label }}
        </div>
        <div class="text-[22px] font-semibold text-stone-900 tabular-nums mt-1.5 leading-none">
          {{ k.value }}<span v-if="k.unit" class="text-[11px] text-stone-400 ms-1 font-normal">{{ k.unit }}</span>
        </div>
      </div>
    </div>

    <!-- groups -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      <div v-for="n in 9" :key="n" class="h-[112px] bg-stone-50 rounded-xl ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="map && map.groups.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      <div
        v-for="g in map.groups" :key="g.key"
        class="bg-white rounded-xl ring-1 p-4"
        :class="g.offPick ? 'ring-amber-200/70' : 'ring-stone-200/70'"
      >
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                :class="g.aisleGroup ? 'bg-[var(--accent-50)] text-[var(--accent-700)]' : 'bg-stone-100 text-stone-500'">
            <Icon :name="g.aisleGroup ? 'layout-grid' : 'warehouse'" :size="15" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="text-[13.5px] font-semibold text-stone-900 truncate">{{ g.label }}</div>
            <div class="text-[11px] text-stone-400 tabular-nums">
              {{ g.bins }} {{ g.bins === 1 ? "bin" : "bins" }} · {{ num(g.skus) }} SKUs
            </div>
          </div>
          <span v-if="g.offPick"
                class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 whitespace-nowrap">
            off-pick
          </span>
        </div>
        <div class="flex items-end justify-between mt-3">
          <div>
            <div class="text-[18px] font-semibold text-stone-900 tabular-nums leading-none">{{ num(g.units) }}</div>
            <div class="text-[10.5px] text-stone-400 mt-0.5">units</div>
          </div>
          <div class="text-end">
            <div class="text-[13px] font-semibold text-stone-700 tabular-nums leading-none">{{ num(g.value) }}</div>
            <div class="text-[10.5px] text-stone-400 mt-0.5">MAD</div>
          </div>
        </div>
        <!-- share of total units — honest relative bar, no invented capacity -->
        <div class="mt-2.5 h-1.5 rounded-full bg-stone-100 overflow-hidden">
          <div class="h-full rounded-full"
               :class="g.offPick ? 'bg-amber-400' : g.aisleGroup ? 'bg-[var(--accent-500)]' : 'bg-stone-400'"
               :style="{ width: Math.max(2, Math.round((g.units / maxUnits) * 100)) + '%' }" />
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-10 text-center">
      <div class="text-[13.5px] font-semibold text-stone-900">Couldn't load the floor</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[13px] font-semibold text-white bg-stone-800" @click="load">Retry</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { WAREHOUSE } from "@/lib/handoffData.js";
import { api } from "@/lib/resource";

// Honest rebuild: the old page rendered a fabricated floor plan (zones that
// don't exist on this site, invented capacities/owners/pick counts) and four
// fiction tabs — re-slotting claimed "Material Transfer posted" without
// posting anything. Everything below is live Bin data, grouped by the real
// physical families, and nothing else.
const map = ref(null);
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const r = await api("warehouses.floor_map");
    if (r && Array.isArray(r.groups)) map.value = r;
  } catch (_) { /* error card shows */ } finally {
    loading.value = false;
  }
}
onMounted(load);

const maxUnits = computed(() =>
  Math.max(1, ...(map.value?.groups || []).map((g) => g.units)));

const kpis = computed(() => [
  { label: "SKUs in stock", icon: "package", tone: "bg-stone-100 text-stone-500", value: num(map.value?.skus) },
  { label: "Units on the floor", icon: "boxes", tone: "bg-[var(--accent-50)] text-[var(--accent-700)]", value: num(map.value?.units) },
  { label: "Stock value", icon: "wallet", tone: "bg-emerald-50 text-emerald-600", value: num(map.value?.value), unit: "MAD" },
  { label: "Zones off-pick", icon: "shield-alert", tone: (map.value?.offCount ? "bg-amber-50 text-amber-600" : "bg-stone-100 text-stone-400"), value: map.value?.offCount ?? 0 },
]);

function num(v) {
  return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
}
</script>
