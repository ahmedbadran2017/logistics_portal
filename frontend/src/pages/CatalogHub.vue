<template>
  <div class="max-w-5xl mx-auto px-4 py-6 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('catalog.title') }}</h1>
        <p class="text-[13px] text-stone-500 mt-1 max-w-2xl">{{ t('catalog.intro') }}</p>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        <span v-if="ov.lastSync" class="text-[11px] text-stone-400">{{ t('catalog.lastSync') }}: {{ ov.lastSync }}</span>
        <button class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg text-[13px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50"
                :disabled="syncing" @click="runSync">
          <Icon name="refresh-cw" :size="14" />{{ syncing ? t('catalog.syncing') : t('catalog.runSync') }}
        </button>
      </div>
    </header>

    <!-- loading -->
    <div v-if="loading" class="text-center text-[13px] text-stone-400 py-16">{{ t('catalog.syncing') }}…</div>

    <!-- not synced yet -->
    <div v-else-if="!ov.synced" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-8 text-center">
      <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-[var(--accent-50)] text-[var(--accent-600)] mb-3"><Icon name="refresh-cw" :size="22" /></span>
      <div class="text-[15px] font-semibold text-stone-900">{{ t('catalog.emptyTitle') }}</div>
      <div class="text-[12.5px] text-stone-500 mt-1 max-w-md mx-auto">{{ t('catalog.emptyHint') }}</div>
    </div>

    <template v-else>
      <!-- KPIs -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('catalog.strandedValue') }}</div>
          <div class="text-[22px] font-bold text-rose-600 tabular-nums mt-1">{{ fmtMAD(ov.strandedValue) }} <span class="text-[12px] text-stone-400 font-medium">MAD</span></div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('catalog.strandedItems') }}</div>
          <div class="text-[22px] font-bold text-stone-900 tabular-nums mt-1">{{ ov.strandedCount }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('catalog.strandedSkus') }}</div>
          <div class="text-[22px] font-bold text-stone-900 tabular-nums mt-1">{{ ov.strandedSkus }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('catalog.checked') }}</div>
          <div class="text-[22px] font-bold text-stone-900 tabular-nums mt-1">{{ ov.synced }}</div>
        </div>
      </div>

      <!-- status breakdown -->
      <div v-if="statusChips.length" class="flex items-center gap-1.5 flex-wrap">
        <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 me-1">{{ t('catalog.shopifyStatus') }}</span>
        <span v-for="c in statusChips" :key="c.k" class="inline-flex items-center gap-1.5 text-[11.5px] font-medium rounded-md px-2 py-1 ring-1"
              :class="statusClass(c.k)">
          {{ c.k }} <span class="font-bold tabular-nums">{{ c.n }}</span>
        </span>
      </div>

      <!-- stranded stock table -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
          <Icon name="alert-triangle" :size="14" class="text-rose-500" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('catalog.strandedTitle') }}</span>
          <span class="text-[11px] text-stone-400 hidden sm:inline">{{ t('catalog.strandedHint') }}</span>
        </div>
        <div v-if="rows.length" class="overflow-x-auto">
          <table class="w-full min-w-[640px] text-[13px]">
            <thead>
              <tr class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('catalog.thItem') }}</th>
                <th class="text-start px-3 py-2.5">{{ t('catalog.thStatus') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('catalog.thUnits') }}</th>
                <th class="text-end px-4 py-2.5">{{ t('catalog.thValue') }}</th>
                <th class="w-10"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="r in rows" :key="r.code" class="hover:bg-stone-50 cursor-pointer" @click="openSku(r.sku)">
                <td class="px-4 py-2.5">
                  <div class="font-mono text-[12px] text-stone-900">{{ r.sku || r.code }}</div>
                  <div class="text-[11.5px] text-stone-500 truncate max-w-[280px]">{{ r.name }}</div>
                </td>
                <td class="px-3 py-2.5">
                  <span class="inline-flex items-center gap-1 text-[11px] font-semibold rounded-md px-2 py-0.5 ring-1" :class="statusClass(r.status)">{{ r.status || '—' }}</span>
                  <span v-if="!r.variantLive" class="ms-1 text-[10px] text-amber-600 font-medium">{{ t('catalog.variantGone') }}</span>
                </td>
                <td class="px-3 py-2.5 text-end font-semibold tabular-nums text-stone-900">{{ r.units }}</td>
                <td class="px-4 py-2.5 text-end tabular-nums text-rose-600 font-semibold">{{ fmtMAD(r.value) }}</td>
                <td class="pe-3"><Icon name="chevron-right" :size="14" class="text-stone-300 flip-rtl" /></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="text-center text-[12.5px] text-emerald-600 py-10">{{ t('catalog.strandedNone') }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const router = useRouter();
const { success, warn } = useToast();

const ov = ref({ synced: 0, lastSync: "", byStatus: {}, strandedValue: 0, strandedCount: 0, strandedSkus: 0 });
const rows = ref([]);
const loading = ref(true);
const syncing = ref(false);

const fmtMAD = (v) => (Number(v) || 0).toLocaleString("en-US");

const statusChips = computed(() =>
  Object.entries(ov.value.byStatus || {}).map(([k, n]) => ({ k, n })).sort((a, b) => b.n - a.n));

function statusClass(s) {
  if (s === "ACTIVE") return "text-emerald-700 bg-emerald-50 ring-emerald-200/70";
  if (s === "ARCHIVED") return "text-rose-700 bg-rose-50 ring-rose-200/70";
  if (s === "DELETED") return "text-stone-700 bg-stone-100 ring-stone-200";
  if (s === "DRAFT") return "text-amber-700 bg-amber-50 ring-amber-200/70";
  return "text-stone-500 bg-stone-50 ring-stone-200";
}

function openSku(sku) {
  if (sku) router.push({ name: "SkuLookup", query: { q: sku } });
}

async function load() {
  loading.value = true;
  const [o, s] = await Promise.all([
    liveOr(null, () => api("catalog_hub.problems.overview")),
    liveOr(null, () => api("catalog_hub.problems.stranded_stock", { limit: 100 })),
  ]);
  if (o) ov.value = o;
  rows.value = Array.isArray(s) ? s : [];
  loading.value = false;
}

async function runSync() {
  syncing.value = true;
  try {
    await apiPost("catalog_hub.sync.enqueue_sync");
    success(t("catalog.syncQueued"), t("catalog.syncQueuedBody"));
  } catch (e) {
    warn(t("catalog.syncFail"), String(e.message || e));
  } finally {
    syncing.value = false;
  }
}

onMounted(load);
</script>
