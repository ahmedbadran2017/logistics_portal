<template>
  <div v-if="open" class="fixed inset-0 z-[150] flex items-center justify-center p-4" role="dialog" aria-modal="true">
    <div class="absolute inset-0 bg-stone-900/30 backdrop-blur-[1px] animate-fade-in" @click="close" />
    <div class="relative w-full max-w-[720px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] animate-scale-in overflow-hidden flex flex-col max-h-[88vh]">
      <header class="flex items-center justify-between px-5 py-3.5 border-b border-stone-100">
        <div class="flex items-center gap-2.5">
          <span class="w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center">
            <Icon name="package" :size="16" />
          </span>
          <div>
            <div class="text-[14.5px] font-semibold text-stone-900">{{ t("cpl.title") }}</div>
            <div class="text-[11.5px] text-stone-500">{{ t("cpl.sub") }}</div>
          </div>
        </div>
        <button :title="t('common.close')" class="w-8 h-8 rounded-lg hover:bg-stone-100 flex items-center justify-center text-stone-400" @click="close">
          <Icon name="x" :size="16" />
        </button>
      </header>

      <div class="p-4 overflow-y-auto space-y-4">
        <!-- filters -->
        <div class="space-y-3">
          <!-- items: single / multi / any -->
          <div>
            <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{{ t("cpl.itemsLabel") }}</div>
            <div class="inline-flex rounded-lg ring-1 ring-stone-200 bg-stone-50 p-0.5">
              <button
                v-for="opt in ITEM_OPTS" :key="opt"
                class="h-8 px-3.5 text-[12.5px] font-medium rounded-md transition-colors"
                :class="items === opt ? 'bg-white text-stone-900 shadow-sm ring-1 ring-stone-200' : 'text-stone-500 hover:text-stone-800'"
                @click="items = opt; reload()"
              >{{ t("cpl.items_" + opt) }}</button>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <!-- supplier -->
            <div>
              <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{{ t("cpl.supplierLabel") }}</div>
              <select v-model="supplier" class="w-full h-9 ps-3 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none focus:ring-stone-400" @change="reload">
                <option value="">{{ t("cpl.anySupplier") }}</option>
                <option v-for="s in facets.suppliers" :key="s.name" :value="s.name">{{ s.name }} ({{ s.orders }})</option>
              </select>
            </div>
            <!-- city -->
            <div>
              <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{{ t("cpl.cityLabel") }}</div>
              <select v-model="city" class="w-full h-9 ps-3 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none focus:ring-stone-400" @change="reload">
                <option value="">{{ t("cpl.anyCity") }}</option>
                <option v-for="c in facets.cities" :key="c.name" :value="c.name">{{ c.name }} ({{ c.orders }})</option>
              </select>
            </div>
            <!-- SKU -->
            <div>
              <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{{ t("cpl.skuLabel") }}</div>
              <div class="relative">
                <input v-model="sku" :placeholder="t('cpl.skuPh')" @input="reload"
                       class="w-full h-9 ps-3 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] font-mono focus:outline-none focus:ring-stone-400" />
                <button v-if="sku" :title="t('common.close')" class="absolute end-2 top-1/2 -translate-y-1/2 text-stone-300 hover:text-stone-600" @click="sku = ''; reload()">
                  <Icon name="x" :size="13" />
                </button>
              </div>
            </div>
            <!-- zone -->
            <div>
              <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{{ t("cpl.zoneLabel") }}</div>
              <select v-model="zone" class="w-full h-9 ps-3 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none focus:ring-stone-400" @change="reload">
                <option value="">{{ t("cpl.anyZone") }}</option>
                <option v-for="z in facets.zones" :key="z.zone" :value="z.zone">{{ t("cpl.zone") }} {{ z.zone }} ({{ z.orders }})</option>
              </select>
            </div>
          </div>

          <!-- cap -->
          <div>
            <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{{ t("cpl.capLabel") }}</div>
            <div class="flex items-center gap-2">
              <button
                v-for="n in CAP_PRESETS" :key="n"
                class="h-8 px-3 text-[12.5px] font-medium rounded-lg ring-1 transition-colors"
                :class="cap === n ? 'bg-stone-900 text-white ring-stone-900' : 'text-stone-600 bg-white ring-stone-200 hover:ring-stone-300'"
                @click="cap = n"
              >{{ n }}</button>
              <input
                v-model.number="cap" type="number" min="1" max="120"
                class="h-8 w-20 ps-2.5 pe-2 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] tabular-nums focus:outline-none focus:ring-stone-400"
              />
              <span class="text-[11.5px] text-stone-400">{{ t("cpl.capHint") }}</span>
            </div>
          </div>
        </div>

        <!-- preview -->
        <div class="rounded-xl ring-1 ring-stone-200/70 bg-stone-50/60 p-3">
          <div v-if="loading" class="flex items-center gap-2 text-[12.5px] text-stone-400">
            <Icon name="refresh-cw" :size="14" class="animate-spin" />{{ t("cpl.loading") }}
          </div>
          <div v-else-if="loadError" class="text-[12px] text-rose-600 font-mono break-words">{{ loadError }}</div>
          <template v-else>
            <div class="flex items-baseline gap-2 flex-wrap">
              <span class="text-[22px] font-semibold tabular-nums text-stone-900">{{ Math.min(cap, matched) }}</span>
              <span class="text-[12.5px] text-stone-500">{{ t("cpl.willCreate") }}</span>
              <span v-if="matched > cap" class="text-[11.5px] text-amber-700 bg-amber-50 ring-1 ring-amber-200/70 rounded-full px-2 py-0.5">
                {{ t("cpl.ofMatch").replace("{n}", matched) }}
              </span>
            </div>
            <div class="text-[11.5px] text-stone-400 mt-1 tabular-nums">
              {{ matched }} {{ t("cpl.ordersMatch") }} · {{ matchedUnits }} {{ t("cpl.units") }}
              <span v-if="matched === 0"> · {{ t("cpl.noneMatch") }}</span>
            </div>
            <!-- a peek at the first few orders -->
            <div v-if="rows.length" class="mt-2.5 space-y-1 max-h-[180px] overflow-y-auto">
              <div v-for="(r, i) in rows.slice(0, cap)" :key="r.order"
                   class="flex items-center gap-2 text-[11.5px] rounded-lg bg-white ring-1 ring-stone-200/60 px-2.5 py-1.5">
                <span class="text-stone-300 tabular-nums w-5 text-end">{{ i + 1 }}</span>
                <span class="font-semibold text-stone-800 tabular-nums">{{ r.order }}</span>
                <span class="text-stone-500 truncate flex-1 min-w-0">{{ r.customer }} · {{ r.city }}</span>
                <span class="text-stone-400 whitespace-nowrap">{{ r.lines }} {{ r.lines === 1 ? t("cpl.item1") : t("cpl.itemN") }}</span>
              </div>
            </div>
          </template>
        </div>

        <!-- picker (optional) -->
        <div>
          <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">{{ t("cpl.pickerLabel") }}</div>
          <select v-model="picker" class="w-full h-9 ps-3 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none focus:ring-stone-400">
            <option value="">{{ t("cpl.pickerLater") }}</option>
            <option v-for="p in pickers" :key="p.email" :value="p.email">{{ p.name }}<span v-if="p.load"> ({{ p.load }})</span></option>
          </select>
        </div>
      </div>

      <footer class="px-5 py-3.5 border-t border-stone-100 flex items-center justify-end gap-2">
        <button class="h-9 px-3.5 rounded-lg text-[12.5px] font-medium text-stone-500 hover:text-stone-800" @click="close">{{ t("common.cancel") }}</button>
        <button
          class="h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-40 transition-colors inline-flex items-center gap-1.5"
          :disabled="creating || matched === 0"
          @click="create"
        >
          <Icon name="package" :size="14" />{{ t("cpl.create") }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const emit = defineEmits(["created"]);

const ITEM_OPTS = ["any", "single", "multi"];
const CAP_PRESETS = [10, 20, 40];

const open = ref(false);
const items = ref("any");
const supplier = ref("");
const city = ref("");
const sku = ref("");
const zone = ref("");
const cap = ref(20);
const picker = ref("");

const rows = ref([]);
const matched = ref(0);
const matchedUnits = ref(0);
const facets = reactive({ suppliers: [], cities: [], zones: [] });
const pickers = ref([]);
const loading = ref(false);
const loadError = ref("");
const creating = ref(false);

let reloadTimer = null;
function reload() {
  clearTimeout(reloadTimer);
  reloadTimer = setTimeout(load, 150);
}

async function load() {
  loading.value = true;
  try {
    const r = await api("picking.pick_candidates", {
      items: items.value, supplier: supplier.value || undefined,
      city: city.value || undefined, sku: sku.value || undefined,
      zone: zone.value || undefined,
    });
    rows.value = r.rows || [];
    matched.value = r.matched || 0;
    matchedUnits.value = r.matchedUnits || 0;
    // Facets are only refreshed when nothing is filtered, so the dropdowns
    // don't collapse to the current selection.
    if (!supplier.value && !city.value && !sku.value && !zone.value && items.value === "any") {
      facets.suppliers = r.suppliers || [];
      facets.cities = r.cities || [];
      facets.zones = r.zones || [];
    }
    loadError.value = "";
  } catch (e) {
    loadError.value = String(e.message || e);
    rows.value = []; matched.value = 0; matchedUnits.value = 0;
  } finally {
    loading.value = false;
  }
}

async function openModal() {
  open.value = true;
  items.value = "any"; supplier.value = ""; city.value = ""; sku.value = ""; zone.value = ""; cap.value = 20; picker.value = "";
  await load();
  try {
    const pk = await api("picking.pickers");
    pickers.value = Array.isArray(pk) ? pk : (pk?.pickers || []);
  } catch (_) { pickers.value = []; }
}
function close() { open.value = false; }

async function create() {
  if (!matched.value) return;
  creating.value = true;
  try {
    const chosen = rows.value.slice(0, cap.value).map((r) => r.order);
    const res = await apiPost("picking.create_pick_list_from_orders", {
      orders: chosen, picker: picker.value || undefined,
    });
    const made = (res.pls || (res.pl ? [res.pl] : [])).length || 1;
    const skipped = res.skipped || [];
    // Name the skipped orders and why — "3 skipped" alone leaves the
    // dispatcher guessing which orders never made the list.
    const detail = skipped.length
      ? t("cpl.skipped").replace("{n}", skipped.length) + " — "
        + skipped.slice(0, 3).map((s) => `${s.order}: ${s.reason}`).join(" · ")
        + (skipped.length > 3 ? " …" : "")
      : (res.pl || "");
    success(t("cpl.done").replace("{n}", res.orders ?? chosen.length), detail);
    open.value = false;
    emit("created");
  } catch (e) {
    warn(t("cpl.failed"), String(e.message || e));
  } finally {
    creating.value = false;
  }
}

defineExpose({ open: openModal });
</script>
