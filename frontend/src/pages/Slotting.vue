<template>
  <div class="max-w-5xl mx-auto px-4 py-6 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('slotting.title') }}</h1>
        <p class="text-[13px] text-stone-500 mt-1 max-w-2xl">{{ t('slotting.intro') }}</p>
      </div>
      <select v-model.number="days" @change="load"
              class="h-9 rounded-lg ring-1 ring-stone-200 bg-white text-[12.5px] font-medium text-stone-700 px-2">
        <option :value="30">30 {{ t('slotting.days') }}</option>
        <option :value="90">90 {{ t('slotting.days') }}</option>
        <option :value="180">180 {{ t('slotting.days') }}</option>
      </select>
    </header>

    <div v-if="loading" class="text-center text-[13px] text-stone-400 py-16">{{ t('common.loading') }}…</div>

    <template v-else-if="ov">
      <!-- scorecard -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('slotting.aMovers') }}</div>
          <div class="text-[22px] font-bold text-emerald-600 tabular-nums mt-1">{{ ov.scorecard.aMovers }}</div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ t('slotting.aMoversSub').replace('{p}', aShare) }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-rose-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('slotting.scatter') }}</div>
          <div class="text-[22px] font-bold text-rose-600 tabular-nums mt-1">{{ ov.scorecard.aZones }} <span class="text-[13px] text-stone-400 font-medium">/ {{ ov.zonesTotal }}</span></div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ t('slotting.scatterSub') }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-amber-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('slotting.cold') }}</div>
          <div class="text-[22px] font-bold text-amber-600 tabular-nums mt-1">{{ ov.scorecard.coldItems }}</div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ t('slotting.coldSub').replace('{s}', ov.scorecard.coldShelves).replace('{u}', ov.scorecard.coldUnits) }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('slotting.pickPath') }}</div>
          <div class="text-[22px] font-bold text-stone-900 tabular-nums mt-1">{{ ov.scorecard.pickPathZones }}</div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ t('slotting.pickPathSub') }}</div>
        </div>
      </div>

      <!-- class summary -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="text-[12px] font-semibold text-stone-700 mb-3">{{ t('slotting.classTitle') }}</div>
        <div class="space-y-2.5">
          <div v-for="c in ov.classes" :key="c.cls" class="flex items-center gap-3">
            <span class="w-6 h-6 rounded-md flex items-center justify-center text-[12px] font-bold text-white flex-shrink-0"
                  :class="clsColor(c.cls)">{{ c.cls }}</span>
            <div class="flex-1 min-w-0">
              <div class="h-2.5 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full transition-all" :class="clsColor(c.cls)" :style="{ width: c.pickShare + '%' }" />
              </div>
            </div>
            <div class="text-[12px] tabular-nums text-stone-600 w-[150px] text-right flex-shrink-0">
              <b class="text-stone-900">{{ c.skus }}</b> {{ t('slotting.skus') }} · <b class="text-stone-900">{{ c.pickShare }}%</b> {{ t('slotting.ofPicks') }}
            </div>
          </div>
        </div>
      </div>

      <!-- zone heat table -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-700">{{ t('slotting.zoneTitle') }}</div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[640px] text-[13px]">
            <thead>
              <tr class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('slotting.zone') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('slotting.shelves') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('slotting.skus') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('slotting.picks') }}</th>
                <th class="text-start px-4 py-2.5 w-[34%]">{{ t('slotting.mix') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="z in ov.zones" :key="z.zone" class="hover:bg-stone-50">
                <td class="px-4 py-2.5 font-bold text-stone-900">{{ z.zone }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-stone-600">{{ z.shelves }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-stone-600">{{ z.skus }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums font-semibold text-stone-900">{{ z.picks }}</td>
                <td class="px-4 py-2.5">
                  <div class="flex h-3 rounded-full overflow-hidden ring-1 ring-stone-200/60 bg-stone-50" :title="`A ${z.A} · B ${z.B} · C ${z.C} · cold ${z.cold}`">
                    <div class="bg-emerald-500" :style="{ width: pctOf(z.A, z) + '%' }" />
                    <div class="bg-sky-400" :style="{ width: pctOf(z.B, z) + '%' }" />
                    <div class="bg-stone-400" :style="{ width: pctOf(z.C, z) + '%' }" />
                    <div class="bg-amber-300" :style="{ width: pctOf(z.cold, z) + '%' }" />
                  </div>
                  <div class="text-[10.5px] text-stone-400 mt-1 tabular-nums">A {{ z.A }} · B {{ z.B }} · C {{ z.C }} · <span class="text-amber-600">{{ t('slotting.coldShort') }} {{ z.cold }}</span></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- movers drill-down -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <div class="inline-flex rounded-lg ring-1 ring-stone-200 overflow-hidden text-[12px] font-semibold">
            <button v-for="c in ['A','B','C']" :key="c"
                    class="h-8 px-3 transition-colors" :class="cls === c ? 'bg-stone-900 text-white' : 'bg-white text-stone-600 hover:bg-stone-50'"
                    @click="setCls(c)">{{ c }}</button>
          </div>
          <span class="text-[11.5px] text-stone-400 tabular-nums">{{ moversTotal }} {{ t('slotting.skus') }}</span>
          <div class="relative ms-auto">
            <span class="absolute inset-y-0 left-2.5 flex items-center text-stone-400"><Icon name="search" :size="14" /></span>
            <input v-model="q" @input="runSearch" :placeholder="t('slotting.searchPh')"
                   class="h-9 w-[200px] max-w-full ps-8 pe-3 rounded-lg ring-1 ring-stone-200 bg-white text-[12.5px] outline-none focus:ring-2 focus:ring-[var(--accent-400)]" />
          </div>
        </div>
        <div v-if="moversLoading" class="p-4 space-y-2">
          <span v-for="n in 5" :key="n" class="block h-11 rounded-lg bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
        </div>
        <ul v-else class="divide-y divide-stone-100 max-h-[520px] overflow-y-auto">
          <li v-for="it in movers" :key="it.itemCode"
              class="p-3 flex items-center gap-3 hover:bg-stone-50 cursor-pointer" @click="openSku(it.sku)">
            <img v-if="it.image" :src="it.image" alt="" @error="hideImg"
                 class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
            <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="16" /></span>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-semibold text-stone-900 truncate">{{ it.name }}</div>
              <div class="font-mono text-[11.5px] text-stone-500 truncate">{{ it.sku || it.itemCode }}</div>
            </div>
            <span class="text-[11.5px] font-semibold rounded-md px-2 py-0.5 ring-1 flex-shrink-0"
                  :class="it.placed ? 'text-stone-700 bg-stone-50 ring-stone-200' : 'text-rose-700 bg-rose-50 ring-rose-200/70'">
              {{ it.placed ? it.shelf : t('slotting.noStock') }}
            </span>
            <span class="text-[12px] font-bold text-stone-900 tabular-nums flex-shrink-0 w-14 text-right">{{ it.picks }} <span class="text-[10px] text-stone-400 font-medium">{{ t('slotting.picksShort') }}</span></span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const router = useRouter();

const days = ref(90);
const ov = ref(null);
const loading = ref(true);

const cls = ref("A");
const movers = ref([]);
const moversTotal = ref(0);
const moversLoading = ref(false);
const q = ref("");
let searchTimer = null;

const aShare = computed(() => {
  const a = (ov.value?.classes || []).find((c) => c.cls === "A");
  return a ? a.pickShare : 0;
});

function clsColor(c) {
  return c === "A" ? "bg-emerald-500" : c === "B" ? "bg-sky-400" : "bg-stone-400";
}
function pctOf(n, z) {
  const tot = (z.A + z.B + z.C + z.cold) || 1;
  return (100 * n / tot).toFixed(1);
}

async function load() {
  loading.value = true;
  try {
    ov.value = await api("slotting.overview", { days: days.value });
  } catch (e) {
    ov.value = null;
  } finally {
    loading.value = false;
  }
  loadMovers();
}

async function loadMovers() {
  moversLoading.value = true;
  try {
    const res = await api("slotting.movers", { cls: cls.value, q: q.value.trim(), days: days.value });
    movers.value = res?.rows || [];
    moversTotal.value = res?.total || 0;
  } catch (e) {
    movers.value = [];
    moversTotal.value = 0;
  } finally {
    moversLoading.value = false;
  }
}

function setCls(c) { cls.value = c; loadMovers(); }
function runSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(loadMovers, 250); }
function openSku(sku) { if (sku) router.push({ name: "SkuLookup", query: { q: sku } }); }
function hideImg(e) { e.target.style.display = "none"; }

onMounted(load);
</script>
