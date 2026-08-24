<template>
  <div class="max-w-[900px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('weights.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('weights.intro') }}</p>
      </div>
      <div v-if="cov" class="flex items-center gap-2 flex-wrap">
        <span class="inline-flex items-baseline gap-1.5 text-white bg-stone-900 rounded-lg px-3 h-9 tabular-nums">
          <span class="text-[16px] font-bold">{{ cov.done }}</span>
          <span class="text-[11.5px] font-medium opacity-70">/ {{ cov.stocked }}</span>
        </span>
        <span class="text-[12px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded-lg px-2.5 h-9 inline-flex items-center tabular-nums">
          {{ cov.pct }}%
        </span>
      </div>
    </header>

    <!-- progress -->
    <div v-if="cov" class="h-2 rounded-full bg-stone-100 overflow-hidden">
      <div class="h-full bg-emerald-500 transition-all" :style="{ width: cov.pct + '%' }" />
    </div>

    <!-- Scanner -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 sticky top-2 z-10 shadow-sm">
      <ScanInput ref="scanner" :placeholder="t('weights.scanPh')" @scan="onScan" />
      <div class="mt-1.5 text-[11px] text-stone-400">{{ t('weights.scanHint') }}</div>
    </div>

    <!-- Active item — enter its weight -->
    <div v-if="active" class="bg-white rounded-2xl ring-1 ring-[var(--accent-300)] shadow-sm p-4">
      <div class="flex items-center gap-3">
        <img v-if="active.image" :src="active.image" alt="" @error="hideImg"
             class="w-14 h-14 rounded-xl object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
        <span v-else class="w-14 h-14 rounded-xl bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="22" /></span>
        <div class="min-w-0 flex-1">
          <div class="text-[14.5px] font-semibold text-stone-900 truncate">{{ active.name }}</div>
          <div class="font-mono text-[12px] text-stone-500 truncate">{{ active.sku || active.itemCode }}</div>
          <div class="text-[11.5px] text-stone-400 tabular-nums mt-0.5">
            {{ active.qty }} {{ t('recv.units') }}<span v-if="active.hasWeight" class="text-amber-600 font-medium"> · {{ t('weights.current') }}: {{ active.grams }} g</span>
          </div>
        </div>
      </div>

      <div class="flex items-end gap-2 mt-3">
        <div class="flex-1">
          <label class="block text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 mb-1">{{ t('weights.grams') }}</label>
          <input ref="gramsInput" v-model.number="grams" type="number" min="1" max="50000" inputmode="numeric"
                 :placeholder="t('weights.gramsPh')" @keyup.enter="save"
                 class="w-full h-12 rounded-xl ring-1 ring-stone-200 bg-white text-[18px] font-bold text-stone-900 tabular-nums px-3 outline-none focus:ring-2 focus:ring-[var(--accent-400)]" />
        </div>
        <button
          class="h-12 px-5 rounded-xl bg-[var(--accent-600)] text-white text-[14px] font-semibold inline-flex items-center gap-1.5 disabled:opacity-40"
          :disabled="saving || !(grams > 0)" @click="save">
          <Icon name="check" :size="16" />{{ saving ? t('weights.saving') : t('weights.save') }}
        </button>
      </div>

      <label class="flex items-center gap-2 mt-3 text-[12px] text-stone-600 cursor-pointer select-none">
        <input v-model="applySiblings" type="checkbox" class="w-4 h-4 rounded accent-[var(--accent-600)]" />
        {{ t('weights.applySiblings') }}
      </label>
    </div>

    <!-- Worklist -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="p-3.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
        <span class="text-[12.5px] font-semibold text-stone-700">{{ t('weights.worklist') }}</span>
        <span v-if="cov" class="text-[11.5px] text-stone-400 tabular-nums">{{ cov.missing }} {{ t('weights.remaining') }}</span>
        <div class="relative ms-auto">
          <span class="absolute inset-y-0 left-2.5 flex items-center text-stone-400"><Icon name="search" :size="14" /></span>
          <input v-model="searchQ" @input="runSearch" :placeholder="t('weights.searchPh')"
                 class="h-9 w-[200px] max-w-full ps-8 pe-3 rounded-lg ring-1 ring-stone-200 bg-white text-[12.5px] outline-none focus:ring-2 focus:ring-[var(--accent-400)]" />
        </div>
      </div>

      <div v-if="loading" class="p-4 space-y-2">
        <span v-for="n in 5" :key="n" class="block h-12 rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <div v-else-if="!rows.length" class="p-10 text-center text-[13px] text-emerald-600">
        <Icon name="check-circle" :size="26" class="mx-auto mb-2" />{{ searchQ ? t('weights.noResults') : t('weights.allDone') }}
      </div>
      <ul v-else class="divide-y divide-stone-100 max-h-[520px] overflow-y-auto">
        <li v-for="it in rows" :key="it.itemCode"
            class="p-3 flex items-center gap-3 hover:bg-stone-50 cursor-pointer"
            :class="active && active.itemCode === it.itemCode ? 'bg-[var(--accent-50)]' : ''"
            @click="pick(it)">
          <img v-if="it.image" :src="it.image" alt="" @error="hideImg"
               class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
          <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="16" /></span>
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-semibold text-stone-900 truncate">{{ it.name }}</div>
            <div class="font-mono text-[11.5px] text-stone-500 truncate">{{ it.sku || it.itemCode }}</div>
          </div>
          <span v-if="it.hasWeight" class="text-[12px] font-semibold text-stone-500 tabular-nums flex-shrink-0">{{ it.grams }} g</span>
          <span v-else class="text-[11px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200/70 rounded-md px-2 py-0.5 flex-shrink-0">{{ t('weights.missing') }}</span>
          <Icon name="chevron-right" :size="14" class="text-stone-300 flip-rtl flex-shrink-0" />
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, nextTick } from "vue";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const scanner = ref(null);
const gramsInput = ref(null);
const cov = ref(null);
const rows = ref([]);
const loading = ref(true);
const active = ref(null);
const grams = ref(null);
const applySiblings = ref(false);
const saving = ref(false);
const searchQ = ref("");
let searchTimer = null;

async function loadCoverage() {
  try { cov.value = await api("weights.coverage"); } catch (e) { /* header only */ }
}
async function loadQueue() {
  loading.value = true;
  try {
    const res = await api("weights.queue", { q: searchQ.value.trim() });
    rows.value = res?.rows || [];
  } catch (e) {
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

function focusGrams() {
  nextTick(() => gramsInput.value?.focus());
}

function setActive(item) {
  active.value = item;
  grams.value = item.hasWeight ? item.grams : null;
  applySiblings.value = false;
  focusGrams();
}

async function onScan(raw) {
  const code = String(raw || "").trim();
  if (!code) return;
  let res;
  try {
    res = await apiPost("weights.lookup", { code });
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
    return;
  }
  if (!res.ok) {
    scanner.value?.showError(t("weights.unknown"));
    return;
  }
  scanner.value?.showSuccess(res.item.sku || res.item.itemCode);
  setActive(res.item);
}

function pick(it) {
  setActive(it);
}

async function save() {
  if (!active.value || !(grams.value > 0) || saving.value) return;
  saving.value = true;
  try {
    const res = await apiPost("weights.set_weight", {
      item_code: active.value.itemCode,
      grams: grams.value,
      apply_siblings: applySiblings.value ? 1 : 0,
    });
    success(t("weights.saved"),
      res.applied > 1 ? t("weights.savedSiblings").replace("{n}", res.applied) : `${res.grams} g`);
    active.value = null;
    grams.value = null;
    await Promise.all([loadCoverage(), loadQueue()]);
    scanner.value?.refocus();
  } catch (e) {
    warn(t("weights.saveFail"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}

function runSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadQueue, 250);
}

function hideImg(e) { e.target.style.display = "none"; }

onMounted(async () => {
  await Promise.all([loadCoverage(), loadQueue()]);
  scanner.value?.refocus();
});
</script>
