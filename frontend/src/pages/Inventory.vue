<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1400px] mx-auto animate-fade-in">
    <div class="mb-1">
      <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t('px.inv.title') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5">Sellable network · per SKU · live from Bins · {{ WAREHOUSE }}</p>
    </div>

    <!-- KPI row -->
    <div v-if="statsLoading" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="n in 4" :key="n" class="h-[86px] bg-stone-50 rounded-xl ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <Kpi icon="boxes" tone="stone" label="SKUs in stock" :value="num(stats.skuCount)" />
      <Kpi icon="package" tone="violet" label="Sellable units" :value="num(stats.totalUnits)" />
      <Kpi icon="alert-circle" tone="amber" :label="`Low stock (≤10)`" :value="num(stats.lowSku)" />
      <Kpi icon="alert-triangle" tone="rose" label="Stranded SKUs" :value="num(stats.strandedSku)"
           sub="0 sellable · stock stuck in returns/receiving" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-4">
      <!-- Zone filter (real physical families, same grouping as the Warehouse map) -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden h-fit">
        <div class="px-4 pt-4 pb-2">
          <div class="text-[13px] font-semibold text-stone-800">Zones</div>
          <div class="text-[11.5px] text-stone-500">{{ t('px.inv.filterHint') }}</div>
        </div>
        <div v-if="zonesLoading" class="p-2 space-y-1">
          <div v-for="n in 6" :key="n" class="h-[44px] rounded-lg bg-stone-50 animate-pulse" />
        </div>
        <div v-else class="p-2 space-y-0.5 max-h-[560px] overflow-y-auto">
          <button
            class="w-full text-start rounded-lg px-3 py-2 transition-colors flex items-center justify-between"
            :class="group === '' ? 'bg-[var(--accent-50)]/50 ring-1 ring-[var(--accent-200)]' : 'hover:bg-stone-50'"
            @click="setGroup('')"
          >
            <span class="text-[12.5px] font-medium text-stone-900">All zones</span>
            <span class="text-[11px] text-stone-500 tabular-nums">{{ num(stats.skuCount) }} SKU</span>
          </button>
          <button
            v-for="g in pickGroups" :key="g.key"
            class="w-full text-start rounded-lg px-3 py-2 transition-colors"
            :class="group === g.key ? 'bg-[var(--accent-50)]/50 ring-1 ring-[var(--accent-200)]' : 'hover:bg-stone-50'"
            @click="setGroup(group === g.key ? '' : g.key)"
          >
            <div class="flex items-center justify-between">
              <span class="text-[12.5px] font-medium text-stone-900">{{ g.label }}</span>
              <span class="text-[11px] text-stone-500 tabular-nums">{{ num(g.skus) }} SKU</span>
            </div>
            <div class="text-[10.5px] text-stone-400 tabular-nums mt-0.5">
              {{ num(g.units) }} units · {{ g.bins }} {{ g.bins === 1 ? "bin" : "bins" }}
            </div>
          </button>
        </div>
      </div>

      <!-- Stock by SKU -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="flex items-center justify-between gap-2 px-4 pt-4 pb-3 flex-wrap">
          <div>
            <div class="text-[13px] font-semibold text-stone-800">{{ t('px.inv.bySku') }}</div>
            <div class="text-[11.5px] text-stone-500">{{ group || t('px.inv.allZones') }} · {{ num(total) }} SKUs</div>
          </div>
          <div class="flex items-center gap-2">
            <div class="relative">
              <Icon name="search" :size="13" class="absolute start-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
              <input
                v-model="q" :placeholder="t('px.inv.searchPh')" @input="onSearch"
                class="h-8 w-[190px] ps-8 pe-3 text-[12.5px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none"
              />
            </div>
            <button
              class="h-8 px-2.5 rounded-lg text-[11.5px] font-semibold ring-1 transition-colors whitespace-nowrap"
              :class="state === 'low' ? 'bg-amber-500 text-white ring-amber-500' : 'text-amber-700 bg-amber-50 ring-amber-200 hover:bg-amber-100'"
              @click="state = state === 'low' ? '' : 'low'; page = 1; load()"
            >Low ≤10</button>
          </div>
        </div>

        <div v-if="loading" class="p-3 space-y-2">
          <div v-for="n in 8" :key="n" class="h-[46px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full min-w-[680px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">SKU</th>
                <th class="text-start px-4 py-2.5 hidden sm:table-cell">{{ t('px.inv.topBin') }}</th>
                <th class="text-end px-4 py-2.5">{{ t('px.inv.onHand') }}</th>
                <th class="text-end px-4 py-2.5 hidden md:table-cell">Reserved</th>
                <th class="text-end px-4 py-2.5">Available</th>
                <th class="text-end px-4 py-2.5 hidden lg:table-cell">Value</th>
                <th class="text-end px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="it in rows" :key="it.itemCode">
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2.5">
                    <img v-if="it.image" :src="it.image" alt="" loading="lazy" @error="hideImg"
                         class="w-9 h-9 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
                    <div class="min-w-0">
                      <div class="text-[12.5px] font-medium text-stone-900 truncate max-w-[220px]">{{ it.name }}</div>
                      <button class="font-mono text-[10.5px] text-[var(--accent-700)] hover:underline"
                              @click="$router.push({ name: 'SkuLookup', query: { q: it.sku } })">{{ it.sku }}</button>
                    </div>
                  </div>
                </td>
                <td class="px-4 py-2.5 hidden sm:table-cell">
                  <span class="font-mono text-[11.5px] text-stone-600">{{ it.topBin }}</span>
                  <span v-if="it.bins > 1" class="text-[10.5px] text-stone-400"> +{{ it.bins - 1 }}</span>
                </td>
                <td class="px-4 py-2.5 text-end">
                  <span class="text-[13px] font-semibold tabular-nums font-mono"
                        :class="it.state === 'low' ? 'text-amber-600' : 'text-stone-800'">{{ num(it.onHand) }}</span>
                </td>
                <td class="px-4 py-2.5 text-end text-[12.5px] text-stone-500 tabular-nums font-mono hidden md:table-cell">{{ num(it.reserved) }}</td>
                <td class="px-4 py-2.5 text-end text-[12.5px] text-stone-700 tabular-nums font-mono">{{ num(it.available) }}</td>
                <td class="px-4 py-2.5 text-end text-[12.5px] text-stone-600 tabular-nums font-mono hidden lg:table-cell">{{ num(it.value) }}</td>
                <td class="px-4 py-2.5 text-end">
                  <Badge :tone="it.state === 'low' ? 'amber' : 'emerald'" dot>
                    {{ it.state === 'low' ? 'Low' : 'Healthy' }}
                  </Badge>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="loadError" class="text-center py-12">
            <Icon name="alert-triangle" :size="20" class="mx-auto mb-2 text-rose-500" />
            <div class="text-[13px] font-semibold text-stone-800">{{ t('common.loadFail') }}</div>
            <div class="text-[11.5px] text-stone-400 font-mono mt-1 break-words">{{ loadError }}</div>
          </div>
          <div v-else-if="!rows.length" class="text-center text-[12.5px] text-stone-400 py-12">{{ t('px.inv.noMatch') }}</div>
        </div>

        <div v-if="total > pageSize" class="flex items-center justify-between px-4 py-2.5 border-t border-stone-100 bg-stone-50/50">
          <span class="text-[11.5px] text-stone-500 tabular-nums">
            {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} of {{ num(total) }}
          </span>
          <div class="flex items-center gap-1">
            <button class="pager-btn" :disabled="page <= 1" @click="page--; load()"><Icon name="chevron-left" :size="13" class="flip-rtl" /></button>
            <span class="text-[11.5px] text-stone-600 tabular-nums px-1.5">{{ page }} / {{ Math.max(1, Math.ceil(total / pageSize)) }}</span>
            <button class="pager-btn" :disabled="page * pageSize >= total" @click="page++; load()"><Icon name="chevron-right" :size="13" class="flip-rtl" /></button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, h, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { WAREHOUSE } from "@/lib/handoffData.js";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
const { t } = useI18n();

// Honest rebuild: per-SKU sellable stock (pickable network — same scope as the
// Orders board), searchable + paginated. The old page listed the top-60 raw
// Bin rows over every warehouse ever created, with a zone list dominated by
// legacy Morocco/V-Turkey/ERPNext and a fake 'Create restock task' button.
const stats = ref({});
const statsLoading = ref(true);
const zones = ref([]);
const zonesLoading = ref(true);

const rows = ref([]);
const loadError = ref("");
const total = ref(0);
const loading = ref(true);
const pageSize = 30;
const page = ref(1);
const q = ref("");
const state = ref("");
const group = ref("");
let searchTimer = null;

async function load() {
  loading.value = true;
  try {
    const r = await api("inventory.stock", {
      limit: pageSize, offset: (page.value - 1) * pageSize,
      q: q.value, state: state.value, group: group.value,
    });
    rows.value = Array.isArray(r?.rows) ? r.rows : [];
    total.value = Number(r?.total || 0);
    loadError.value = "";
  } catch (e) {
    // Swallowing this rendered "No matching items" -- a dead stock API read
    // as an empty warehouse.
    rows.value = []; total.value = 0;
    loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { page.value = 1; load(); }, 350);
}
function setGroup(g) { group.value = g; page.value = 1; load(); }

// Zones panel = the same real families as the Warehouse floor map; off-pick
// groups are excluded here (this page is the SELLABLE view — stranded stock
// lives on the Restock/Warehouse screens).
const pickGroups = computed(() => zones.value.filter((g) => !g.offPick));

onMounted(async () => {
  load();
  api("inventory.stats").then((s) => {
    if (s && Object.keys(s).length) stats.value = s;
  }).catch(() => {}).finally(() => (statsLoading.value = false));
  api("warehouses.floor_map").then((m) => {
    if (m && Array.isArray(m.groups)) zones.value = m.groups;
  }).catch(() => {}).finally(() => (zonesLoading.value = false));
});

function num(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }

// ── Local presentational primitives ─────────────────────────────────────
const TONE = {
  stone: "bg-stone-100 text-stone-600", emerald: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-700", rose: "bg-rose-100 text-rose-700",
  violet: "bg-violet-100 text-violet-700",
};
const KPI_TONE = { stone: "#a8a29e", violet: "#8b5cf6", amber: "#f59e0b", rose: "#f43f5e", emerald: "#10b981" };

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
    props.sub ? h("div", { class: "text-[10.5px] text-stone-400 mt-1.5" }, props.sub) : null,
  ]);
Kpi.props = ["icon", "tone", "label", "value", "sub"];
</script>
