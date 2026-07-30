<template>
  <div class="max-w-[900px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('shelfLabels.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('shelfLabels.intro') }}</p>
      </div>
      <div v-if="loadingShelves" class="flex items-center gap-2">
        <span class="w-[120px] h-9 rounded-lg bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <div v-else-if="totals" class="flex items-center gap-2 flex-wrap">
        <span class="inline-flex items-baseline gap-1.5 text-white bg-stone-900 rounded-lg px-3 h-9 tabular-nums">
          <span class="text-[16px] font-bold">{{ totals.shelves }}</span>
          <span class="text-[11.5px] font-medium opacity-80">{{ t('shelfLabels.shelves') }}</span>
        </span>
      </div>
    </header>

    <!-- Step 1 — shelf picker: zone chips then shelf chips. -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 space-y-3">
      <div class="text-[12.5px] font-semibold text-stone-600">{{ t('shelfLabels.pickShelf') }}</div>

      <div v-if="loadingShelves" class="flex flex-wrap gap-1.5">
        <span v-for="n in 8" :key="n" class="w-10 h-8 rounded-lg bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <div v-else-if="errShelves" class="text-[13px] text-red-600 flex items-center gap-2">
        <Icon name="alert-triangle" :size="15" /> {{ t('common.loadFail') }}
      </div>
      <template v-else-if="zones.length">
        <!-- zones -->
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="z in zones" :key="z.zone"
            class="h-8 min-w-9 px-2.5 rounded-lg text-[13px] font-bold ring-1 transition-colors"
            :class="activeZone === z.zone
              ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]'
              : 'text-stone-700 bg-white ring-stone-200 hover:ring-stone-300'"
            @click="pickZone(z.zone)"
          >{{ z.zone }}</button>
        </div>
        <!-- shelves in the active zone -->
        <div v-if="activeZoneShelves.length" class="flex flex-wrap gap-1.5 pt-1">
          <button
            v-for="s in activeZoneShelves" :key="s.warehouse"
            class="h-9 px-2.5 rounded-lg text-[12.5px] font-semibold ring-1 transition-colors tabular-nums flex items-center gap-1.5"
            :class="selectedShelf === s.warehouse
              ? 'text-white bg-stone-900 ring-stone-900'
              : 'text-stone-700 bg-white ring-stone-200 hover:ring-stone-300'"
            @click="loadShelf(s)"
          >
            <span>{{ s.shelf }}</span>
            <span class="text-[10.5px] font-medium"
                  :class="selectedShelf === s.warehouse ? 'opacity-70' : 'text-stone-400'">
              {{ s.skus }}·{{ s.units }}
            </span>
          </button>
        </div>
      </template>
      <div v-else class="text-[13px] text-stone-400">{{ t('shelfLabels.noShelves') }}</div>
    </div>

    <!-- Step 2 — the shelf's items + print controls. -->
    <div v-if="loadingItems" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 space-y-3">
      <span v-for="n in 4" :key="n" class="block h-12 rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="shelf" class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
      <!-- controls bar -->
      <div class="p-4 border-b border-stone-100 flex items-center gap-3 flex-wrap">
        <div class="flex-1 min-w-0">
          <div class="text-[15px] font-bold text-stone-900">{{ shelf.shelf }}</div>
          <div class="text-[12px] text-stone-500 tabular-nums">
            {{ shelf.skus }} {{ t('shelfLabels.skus') }} · {{ shelf.units }} {{ t('recv.units') }}
            <span v-if="shelf.noSkuCount" class="text-amber-600 font-medium">
              · {{ shelf.noSkuCount }} {{ t('shelfLabels.needSku') }}
            </span>
          </div>
        </div>

        <!-- copies toggle -->
        <div class="inline-flex rounded-lg ring-1 ring-stone-200 overflow-hidden text-[12px] font-semibold">
          <button
            class="h-9 px-3 transition-colors"
            :class="copies === 'sku' ? 'bg-stone-900 text-white' : 'bg-white text-stone-600 hover:bg-stone-50'"
            @click="copies = 'sku'"
          >{{ t('shelfLabels.perSku') }}</button>
          <button
            class="h-9 px-3 transition-colors border-l border-stone-200"
            :class="copies === 'piece' ? 'bg-stone-900 text-white' : 'bg-white text-stone-600 hover:bg-stone-50'"
            @click="copies = 'piece'"
          >{{ t('shelfLabels.perPiece') }}</button>
        </div>

        <!-- label size -->
        <select v-model="sizeKey"
                class="h-9 rounded-lg ring-1 ring-stone-200 bg-white text-[12px] font-medium text-stone-700 px-2">
          <option v-for="s in sizes" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>

        <button
          class="h-9 px-4 rounded-lg bg-[var(--accent-600)] text-white text-[12.5px] font-semibold inline-flex items-center gap-1.5 disabled:opacity-40"
          :disabled="!printableCount"
          @click="print"
        >
          <Icon name="printer" :size="15" />
          {{ t('shelfLabels.print') }}
          <span class="tabular-nums opacity-80">({{ printableCount }})</span>
        </button>
      </div>

      <!-- item list -->
      <ul class="divide-y divide-stone-100">
        <li v-for="it in shelf.items" :key="it.itemCode"
            class="p-3 flex items-center gap-3"
            :class="it.noSku ? 'bg-amber-50/40' : ''">
          <img v-if="it.image" :src="it.image" alt="" @error="hideImg"
               class="w-11 h-11 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
          <span v-else class="w-11 h-11 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400">
            <Icon name="package" :size="18" />
          </span>

          <div class="min-w-0 flex-1">
            <div class="text-[13.5px] font-semibold text-stone-900 truncate">{{ it.name }}</div>
            <div v-if="it.noSku" class="text-[11.5px] text-amber-700 font-medium flex items-center gap-1">
              <Icon name="alert-triangle" :size="12" /> {{ t('shelfLabels.noSkuRow') }}
            </div>
            <div v-else class="font-mono text-[12px] text-stone-500 truncate">{{ it.sku }}</div>
          </div>

          <!-- live barcode preview -->
          <div v-if="!it.noSku" class="hidden sm:block flex-shrink-0" v-html="previewSvg(it.sku)" />

          <span class="text-[13px] font-bold text-stone-900 tabular-nums flex-shrink-0 w-10 text-right">
            {{ it.qty }}<span class="text-[10px] font-medium text-stone-400 ml-0.5">×</span>
          </span>

          <!-- per-item print -->
          <button
            v-if="!it.noSku"
            class="h-9 w-9 rounded-lg ring-1 ring-stone-200 text-stone-600 hover:bg-stone-50 flex items-center justify-center flex-shrink-0"
            :title="t('shelfLabels.printOne')"
            @click="printOne(it)"
          >
            <Icon name="printer" :size="15" />
          </button>
          <span v-else class="w-9 flex-shrink-0" />
        </li>
      </ul>
    </div>

    <div v-else-if="!loadingShelves && zones.length" class="text-center py-10 text-stone-400 text-[13px]">
      {{ t('shelfLabels.selectPrompt') }}
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { code128SVG } from "@/lib/code128.js";
import { LABEL_SIZES, printShelfLabels } from "@/lib/shelfLabelPrint.js";

const { t } = useI18n();
const toast = useToast();

const sizes = LABEL_SIZES;
const zones = ref([]);
const loadingShelves = ref(true);
const errShelves = ref(false);
const activeZone = ref("");
const selectedShelf = ref("");
const shelf = ref(null);
const loadingItems = ref(false);
const copies = ref("sku");
const sizeKey = ref(LABEL_SIZES[0].key);

const totals = computed(() => {
  if (!zones.value.length) return null;
  const shelves = zones.value.reduce((n, z) => n + z.shelves.length, 0);
  return { shelves };
});
const activeZoneShelves = computed(() => {
  const z = zones.value.find((x) => x.zone === activeZone.value);
  return z ? z.shelves : [];
});
const printableCount = computed(() => {
  if (!shelf.value) return 0;
  const items = shelf.value.items.filter((i) => !i.noSku && i.sku);
  return copies.value === "piece"
    ? items.reduce((n, i) => n + Math.max(1, i.qty || 1), 0)
    : items.length;
});

// Cache the tiny preview SVGs — the list re-renders on every toggle.
const previewCache = new Map();
function previewSvg(sku) {
  if (!previewCache.has(sku)) {
    previewCache.set(sku, code128SVG(sku, { height: 30, module: 1.1 }).svg);
  }
  return previewCache.get(sku);
}

function pickZone(zone) {
  activeZone.value = zone;
}

async function loadShelf(s) {
  selectedShelf.value = s.warehouse;
  shelf.value = null;
  loadingItems.value = true;
  try {
    shelf.value = await api("warehouses.shelf_items", { warehouse: s.warehouse });
  } catch (e) {
    toast.error(t("common.loadFail"));
  } finally {
    loadingItems.value = false;
  }
}

function sheet(items) {
  const size = sizes.find((s) => s.key === sizeKey.value) || sizes[0];
  const ok = printShelfLabels({ shelf: shelf.value.shelf, items, copies: copies.value, size });
  if (!ok) toast.error(t("shelfLabels.printBlocked"));
}

// Whole shelf, or a single item — both honour the copies toggle and size.
function print() {
  sheet(shelf.value.items);
}
function printOne(it) {
  sheet([it]);
}

function hideImg(e) {
  e.target.style.display = "none";
}

onMounted(async () => {
  try {
    const res = await api("warehouses.label_shelves");
    zones.value = res?.zones || [];
    if (zones.value.length) activeZone.value = zones.value[0].zone;
  } catch (e) {
    errShelves.value = true;
  } finally {
    loadingShelves.value = false;
  }
});
</script>
