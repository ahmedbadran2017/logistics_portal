<template>
  <div class="max-w-5xl mx-auto px-4 py-6 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('brepair.title') }}</h1>
        <p class="text-[13px] text-stone-500 mt-1 max-w-2xl">{{ t('brepair.intro') }}</p>
      </div>
      <button class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg text-[13px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 disabled:opacity-50"
              :disabled="loading" @click="load">
        <Icon name="refresh-cw" :size="14" />{{ t('brepair.rescan') }}
      </button>
    </header>

    <div v-if="loading" class="text-center text-[13px] text-stone-400 py-16">{{ t('brepair.scanning') }}…</div>

    <template v-else-if="sc">
      <!-- scan cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="bg-white rounded-xl ring-1 ring-rose-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.staleBundles') }}</div>
          <div class="text-[22px] font-bold text-rose-600 tabular-nums mt-1">{{ fmt(sc.staleBundles) }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-rose-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.staleUnits') }}</div>
          <div class="text-[22px] font-bold text-rose-600 tabular-nums mt-1">{{ fmt(sc.staleUnits) }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.allBundles') }}</div>
          <div class="text-[22px] font-bold text-stone-900 tabular-nums mt-1">{{ fmt(sc.allHoldBundles) }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.allUnits') }}</div>
          <div class="text-[22px] font-bold text-stone-900 tabular-nums mt-1">{{ fmt(sc.allHoldUnits) }}</div>
        </div>
      </div>

      <!-- nothing to fix -->
      <div v-if="!sc.staleBundles" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-8 text-center">
        <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-600 mb-3"><Icon name="check-circle" :size="22" /></span>
        <div class="text-[15px] font-semibold text-stone-900">{{ t('brepair.cleanTitle') }}</div>
        <div class="text-[12.5px] text-stone-500 mt-1 max-w-md mx-auto">{{ t('brepair.cleanHint') }}</div>
      </div>

      <!-- release panel -->
      <div v-else class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="flex items-center gap-2">
          <Icon name="unlock" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[13px] font-semibold text-stone-900">{{ t('brepair.releaseTitle') }}</span>
        </div>
        <p class="text-[12px] text-stone-500">{{ t('brepair.releaseHint') }}</p>
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-[12px] text-stone-500">{{ t('brepair.limitLabel') }}</span>
          <button v-for="n in [1, 50, 500, 1000]" :key="n"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold tabular-nums ring-1 transition-colors"
                  :class="limit === n ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]' : 'text-stone-700 bg-white ring-stone-200 hover:bg-stone-50'"
                  @click="limit = n">{{ n }}</button>
          <button
            class="h-9 px-4 rounded-lg text-[13px] font-semibold transition-colors disabled:opacity-50 ms-auto"
            :class="armed ? 'text-white bg-rose-600' : 'text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]'"
            :disabled="busy" @click="doRelease">
            <span class="inline-flex items-center gap-1.5">
              <Icon name="unlock" :size="14" />
              {{ busy ? t('brepair.releasing') : armed ? t('brepair.releaseSure').replace('{n}', String(limit)) : t('brepair.releaseBtn').replace('{n}', String(limit)) }}
            </span>
          </button>
        </div>
      </div>

      <!-- last run result -->
      <div v-if="res" class="bg-white rounded-xl ring-1 ring-emerald-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="check-circle" :size="14" class="text-emerald-600" />
          <span class="text-[12px] font-semibold text-stone-900">
            {{ t('brepair.resultLine').replace('{b}', fmt(res.released)).replace('{u}', fmt(res.unitsFreed)) }}
          </span>
          <span v-if="res.failed" class="text-[11.5px] text-rose-600 font-medium">{{ t('brepair.resultFailed').replace('{n}', String(res.failed)) }}</span>
        </div>
        <div v-if="res.items && res.items.length" class="divide-y divide-stone-100">
          <div v-for="it in res.items" :key="it.itemCode" class="px-4 py-2.5 flex items-center gap-3 flex-wrap">
            <div class="font-mono text-[12px] text-stone-900 min-w-0 flex-1">{{ it.itemCode }}</div>
            <span class="text-[12px] tabular-nums text-stone-700 whitespace-nowrap"><b>{{ fmt(it.units) }}</b> u {{ t('brepair.freed') }}</span>
            <template v-if="probes[it.itemCode]">
              <span class="inline-flex items-center gap-1.5 text-[11.5px] font-medium rounded-md px-2 py-1 ring-1"
                    :class="probes[it.itemCode].eeAvailable > 0 ? 'text-emerald-700 bg-emerald-50 ring-emerald-200/70' : 'text-amber-700 bg-amber-50 ring-amber-200/70'">
                {{ t('brepair.probeShelf') }} <b class="tabular-nums">{{ probes[it.itemCode].shelfBin }}</b>
                · {{ t('brepair.probePickable') }} <b class="tabular-nums">{{ probes[it.itemCode].eeAvailable }}</b>
              </span>
            </template>
            <button v-else class="h-8 px-3 rounded-lg text-[12px] font-semibold text-stone-700 bg-stone-50 ring-1 ring-stone-200 hover:bg-stone-100 disabled:opacity-50"
                    :disabled="probing === it.itemCode" @click="doProbe(it.itemCode)">
              {{ probing === it.itemCode ? '…' : t('brepair.probeBtn') }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-8 text-center">
      <div class="text-[13px] text-stone-500">{{ t('brepair.loadFail') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const sc = ref(null);
const res = ref(null);
const probes = ref({});
const probing = ref("");
const limit = ref(1);
const armed = ref(false);
const busy = ref(false);
const loading = ref(true);

const fmt = (v) => (Number(v) || 0).toLocaleString("en-US");

async function load() {
  loading.value = true;
  sc.value = await liveOr(null, () => api("batch_repair.scan"));
  loading.value = false;
}

async function doRelease() {
  if (!armed.value) {
    armed.value = true;
    setTimeout(() => { armed.value = false; }, 4000);
    return;
  }
  armed.value = false;
  busy.value = true;
  try {
    const r = await apiPost("batch_repair.release", { limit: limit.value });
    res.value = r;
    probes.value = {};
    success(t("brepair.releaseDone"),
      t("brepair.resultLine").replace("{b}", fmt(r.released)).replace("{u}", fmt(r.unitsFreed)));
    await load();
  } catch (e) {
    warn(t("brepair.releaseFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

async function doProbe(itemCode) {
  probing.value = itemCode;
  try {
    const p = await api("batch_repair.probe", { item_code: itemCode });
    if (p) probes.value = { ...probes.value, [itemCode]: p };
  } catch (e) {
    warn(t("brepair.probeFail"), String(e.message || e));
  } finally {
    probing.value = "";
  }
}

onMounted(load);
</script>
