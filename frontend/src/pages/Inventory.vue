<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <div class="mb-1">
      <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Stock levels</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5">Live on-hand by SKU · zone · bin · {{ WAREHOUSE }}</p>
    </div>

    <!-- KPI row -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <Kpi icon="boxes" tone="stone" label="SKUs tracked" :value="stats.skuCount" />
      <Kpi icon="package" tone="violet" label="Total units" :value="fmtMAD(stats.totalUnits)" />
      <Kpi icon="alert-circle" tone="amber" label="Low stock" :value="stats.lowSku" />
      <Kpi icon="alert-triangle" tone="rose" label="Out of stock" :value="stats.outSku" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1fr_1.6fr] gap-4">
      <!-- Zone filter / health -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 pt-4 pb-2">
          <div class="text-[13px] font-semibold text-stone-800">Zones</div>
          <div class="text-[11.5px] text-stone-500">Filter stock by zone</div>
        </div>
        <div class="p-2 space-y-0.5">
          <button
            @click="zone = null"
            class="w-full text-start rounded-lg px-3 py-2.5 transition-colors flex items-center justify-between"
            :class="zone === null ? 'bg-[var(--accent-50)]/50 ring-1 ring-[var(--accent-200)]' : 'hover:bg-stone-50'"
          >
            <span class="text-[12.5px] font-medium text-stone-900">All zones</span>
            <span class="text-[11px] text-stone-500 tabular-nums">{{ allItems.length }} SKU</span>
          </button>
          <button
            v-for="z in zonesList"
            :key="z.zone"
            @click="zone = zone === z.zone ? null : z.zone"
            class="w-full text-start rounded-lg px-3 py-2.5 transition-colors"
            :class="zone === z.zone ? 'bg-[var(--accent-50)]/50 ring-1 ring-[var(--accent-200)]' : 'hover:bg-stone-50'"
          >
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-[12.5px] font-medium text-stone-900">{{ z.zone.replace(' - JM', '') }}</span>
              <div class="flex items-center gap-1.5">
                <Badge v-if="z.out > 0" tone="rose" dot>{{ z.out }} out</Badge>
                <Badge v-if="z.low > 0" tone="amber" dot>{{ z.low }} low</Badge>
                <Badge v-if="z.out === 0 && z.low === 0" tone="emerald" dot>Healthy</Badge>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <div class="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden">
                <div
                  class="h-full rounded-full"
                  :class="z.fill >= 0.85 ? 'bg-emerald-500' : z.fill >= 0.7 ? 'bg-amber-500' : 'bg-rose-500'"
                  :style="{ width: (z.fill * 100) + '%' }"
                />
              </div>
              <span class="text-[11px] text-stone-500 tabular-nums w-[110px] text-end">{{ Math.round(z.fill * 100) }}% fill · {{ z.skus }} SKU</span>
            </div>
            <div class="text-[10.5px] text-stone-400 mt-1 font-mono">{{ z.bins.join(' · ') }}</div>
          </button>
        </div>
      </div>

      <!-- Stock levels table -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="flex items-center justify-between px-4 pt-4 pb-3">
          <div>
            <div class="text-[13px] font-semibold text-stone-800">Stock by SKU</div>
            <div class="text-[11.5px] text-stone-500">{{ zone ? zone.replace(' - JM', '') : 'All zones' }}</div>
          </div>
          <button
            @click="success('Restock task drafted', 'Material Transfer queued')"
            class="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-[var(--accent-600)] text-white text-[12px] font-medium hover:opacity-90 transition-opacity"
          >
            <Icon name="scan-barcode" :size="14" />Create restock task
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">SKU</th>
                <th class="text-start px-4 py-2.5 hidden sm:table-cell">Bin</th>
                <th class="text-end px-4 py-2.5">On hand</th>
                <th class="text-end px-4 py-2.5 hidden md:table-cell">Reserved</th>
                <th class="text-end px-4 py-2.5">Available</th>
                <th class="text-end px-4 py-2.5 hidden lg:table-cell">Value</th>
                <th class="text-end px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr
                v-for="it in items"
                :key="it.sku"
                :class="it.state === 'out' ? 'bg-rose-50/30' : ''"
              >
                <td class="px-4 py-2.5">
                  <div class="text-[12.5px] font-medium text-stone-900 truncate max-w-[180px]">{{ it.name }}</div>
                  <div class="font-mono text-[10.5px] text-stone-400">{{ it.sku }} · {{ it.zone.replace(' - JM', '') }}</div>
                </td>
                <td class="px-4 py-2.5 font-mono text-[11.5px] text-stone-500 hidden sm:table-cell">{{ it.bin }}</td>
                <td class="px-4 py-2.5 text-end">
                  <span
                    class="text-[13px] font-semibold tabular-nums font-mono"
                    :class="it.state === 'out' ? 'text-rose-600' : it.state === 'low' ? 'text-amber-600' : 'text-stone-800'"
                  >{{ it.onHand }}</span>
                  <div v-if="it.incoming" class="text-[10px] text-cyan-600 tabular-nums">+{{ it.incoming }} in</div>
                </td>
                <td class="px-4 py-2.5 text-end text-[12.5px] text-stone-500 tabular-nums font-mono hidden md:table-cell">{{ it.reserved }}</td>
                <td class="px-4 py-2.5 text-end text-[12.5px] text-stone-700 tabular-nums font-mono">{{ it.available }}</td>
                <td class="px-4 py-2.5 text-end text-[12.5px] text-stone-600 tabular-nums font-mono hidden lg:table-cell">{{ fmtMAD(it.value) }}</td>
                <td class="px-4 py-2.5 text-end">
                  <Badge :tone="it.state === 'out' ? 'rose' : it.state === 'low' ? 'amber' : 'emerald'" dot>
                    {{ it.state === 'ok' ? 'Healthy' : it.state === 'out' ? 'Out of stock' : 'Low stock' }}
                  </Badge>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, h, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import {
  STOCK_ITEMS as DEMO_STOCK_ITEMS,
  STOCK_STATS as DEMO_STOCK_STATS,
  RESTOCK,
  fmtMAD,
  WAREHOUSE,
} from "@/lib/handoffData.js";
import { api, liveOr } from "@/lib/resource";

const { success } = useToast();

const allItems = ref(DEMO_STOCK_ITEMS);
const stats = ref(DEMO_STOCK_STATS);

const zone = ref(null);
// Zone health panel: live from `inventory.zones` (same shape as the demo
// RESTOCK); demo seed only in dev builds so the panel never shows fake zones.
const zonesList = ref(import.meta.env.DEV ? RESTOCK : []);
const items = computed(() => (zone.value ? allItems.value.filter((i) => i.zone === zone.value) : allItems.value));

onMounted(async () => {
  api("inventory.zones").then((z) => {
    if (Array.isArray(z) && z.length) zonesList.value = z;
  }).catch(() => {});
  const live = await liveOr(null, () => api("inventory.stock", { limit: 60 }));
  if (live && live.length) allItems.value = live;
  const s = await liveOr(null, () => api("inventory.stats"));
  if (s && Object.keys(s).length) stats.value = s;
});

// ── Local presentational primitives (match handoff Tailwind) ────────────
const TONE = {
  stone: "bg-stone-100 text-stone-600", emerald: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-700", rose: "bg-rose-100 text-rose-700",
  violet: "bg-violet-100 text-violet-700", cyan: "bg-cyan-100 text-cyan-700",
};
const KPI_TONE = {
  stone: "#a8a29e", violet: "#8b5cf6", amber: "#f59e0b", rose: "#f43f5e", emerald: "#10b981",
};

const Badge = (props, { slots }) =>
  h("span", { class: `inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10.5px] font-medium whitespace-nowrap ${TONE[props.tone] || TONE.stone}` }, [
    props.dot ? h("span", { class: "w-1.5 h-1.5 rounded-full bg-current opacity-70" }) : null,
    slots.default?.(),
  ]);
Badge.props = ["tone", "dot"];

const Kpi = (props) =>
  h("div", { class: "bg-white rounded-xl ring-1 ring-stone-200/70 p-4 relative overflow-hidden" }, [
    h("span", { class: "absolute inset-x-0 top-0 h-1", style: { background: KPI_TONE[props.tone] || KPI_TONE.stone } }),
    h("div", { class: "flex items-center justify-between mb-2" }, [
      h("span", { class: "text-[11px] font-medium uppercase tracking-wide text-stone-400" }, props.label),
      h(Icon, { name: props.icon, size: 15, class: "text-stone-400" }),
    ]),
    h("div", { class: "text-[22px] font-bold text-stone-900 tabular-nums leading-none" }, String(props.value)),
  ]);
Kpi.props = ["icon", "tone", "label", "value"];
</script>
