<template>
  <!-- Labelled, never left: parcels with a label and a Delivery Note that the
       carrier never scanned. Backend: shipping.never_left. -->
  <div class="max-w-[1180px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('nl.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[760px]">{{ t('nl.intro') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 disabled:opacity-50"
                :disabled="loading || !activeRows.length" @click="exportTab">
          <Icon name="file-text" :size="14" />{{ t('hgap.excel') }}
        </button>
        <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50 disabled:opacity-50"
                :disabled="loading || !totalRows" @click="exportAll">
          {{ t('hgap.excelAll') }}<span class="tabular-nums text-stone-400">{{ totalRows }}</span>
        </button>
        <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
                :disabled="loading" @click="load">
          <Icon name="rotate-ccw" :size="14" />{{ t('hgap.refresh') }}
        </button>
      </div>
    </header>

    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <button v-for="k in tabs" :key="k.id"
              class="text-start bg-white rounded-xl ring-1 p-4 transition-all"
              :class="tab === k.id ? 'ring-2 ring-[var(--accent-400)] shadow-[0_2px_12px_-4px_rgba(0,0,0,0.12)]'
                      : k.n ? 'ring-stone-200/70 hover:ring-stone-300' : 'ring-stone-200/70 opacity-70'"
              @click="tab = k.id">
        <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ k.label }}</div>
        <div class="flex items-baseline gap-2 mt-1">
          <span class="text-[24px] font-extrabold tabular-nums" :class="k.n ? k.tone : 'text-stone-300'">{{ fmt(k.n) }}</span>
          <span v-if="k.mad" class="text-[12px] font-semibold text-stone-500 tabular-nums">{{ fmtMAD(k.mad) }} MAD</span>
        </div>
        <div class="text-[11px] text-stone-400 mt-0.5 leading-snug">{{ k.hint }}</div>
      </button>
    </div>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 6" :key="n" class="h-[46px] rounded-xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
    </div>

    <template v-else>
      <p class="text-[12.5px] text-stone-600 bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-2.5">
        {{ t('nl.hint_' + tab) }}
      </p>

      <!-- Many parcels on one manifest = a pickup that did not happen. -->
      <div v-if="tab === 'noPickup' && (data?.manifests || []).length" class="flex flex-wrap gap-1.5">
        <button v-for="m in data.manifests" :key="m.manifest"
                class="h-8 px-3 rounded-lg text-[11.5px] font-semibold ring-1 transition-colors tabular-nums"
                :class="manifest === m.manifest ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-700 ring-stone-200 hover:ring-stone-300'"
                @click="manifest = manifest === m.manifest ? '' : m.manifest">
          <span class="font-mono">{{ m.manifest }}</span> · {{ m.n }} · {{ fmtMAD(m.mad) }} MAD
        </button>
      </div>

      <div v-if="!activeRows.length" class="bg-white rounded-xl ring-1 ring-emerald-200/70 p-10 text-center">
        <Icon name="check-circle" :size="22" class="mx-auto mb-2 text-emerald-500" />
        <div class="text-[13px] font-semibold text-stone-700">{{ t('hgap.clean') }}</div>
      </div>

      <div v-else class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="divide-y divide-stone-100 max-h-[62vh] overflow-y-auto">
          <button v-for="r in activeRows" :key="r.order + r.dn"
                  class="w-full text-start px-4 py-2.5 flex items-center gap-2.5 flex-wrap hover:bg-stone-50"
                  @click="$router.push({ name: 'OrderDetail', params: { name: r.order } })">
            <span class="font-mono text-[12px] font-semibold text-stone-900">{{ r.order }}</span>
            <span class="font-mono text-[11px] text-stone-400">{{ r.awb }}</span>
            <span class="text-[11.5px] text-stone-500 truncate max-w-[180px]" dir="auto">{{ r.customer }}</span>
            <span v-if="r.city" class="text-[11px] text-stone-400">{{ r.city }}</span>
            <span class="text-[10.5px] font-semibold rounded px-1.5 py-0.5 bg-stone-100 text-stone-600">{{ r.status || '—' }}</span>
            <span v-if="r.manifest" class="font-mono text-[10.5px] rounded px-1.5 py-0.5"
                  :class="r.draft ? 'bg-amber-50 text-amber-700' : 'bg-sky-50 text-sky-700'">
              {{ r.manifest }}<template v-if="r.draft"> · {{ t('nl.draft') }}</template>
            </span>
            <span v-if="r.pickList" class="font-mono text-[10.5px] text-stone-400">{{ r.pickList }}</span>
            <span class="ms-auto text-[12px] font-semibold text-stone-900 tabular-nums whitespace-nowrap">{{ fmtMAD(r.mad) }} MAD</span>
            <span class="text-[11px] font-semibold tabular-nums w-12 text-end"
                  :class="r.ageD >= 7 ? 'text-rose-600' : r.ageD >= 3 ? 'text-amber-600' : 'text-stone-500'">
              {{ r.ageD ? r.ageD + t('nl.d') : r.ageH + 'h' }}
            </span>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { fmtMAD } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";
import { downloadCsv, stampName } from "@/lib/csvExport";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success } = useToast();

const data = ref(null);
const loading = ref(true);
const tab = ref("unmanifested");
const manifest = ref("");
watch(tab, () => { manifest.value = ""; });

const fmt = (v) => (Number(v) || 0).toLocaleString("en-US");
const BUCKETS = ["unmanifested", "noPickup", "cancelled"];
const TONE = { unmanifested: "text-rose-600", noPickup: "text-rose-600", cancelled: "text-amber-600" };

const tabs = computed(() => BUCKETS.map((id) => ({
  id, label: t("nl.tab_" + id), hint: t("nl.tabHint_" + id), tone: TONE[id],
  n: data.value?.totals?.[id]?.n || 0, mad: data.value?.totals?.[id]?.mad || 0,
})));

const activeRows = computed(() => {
  const rows = data.value?.[tab.value] || [];
  return manifest.value ? rows.filter((r) => r.manifest === manifest.value) : rows;
});
const totalRows = computed(() => BUCKETS.reduce((n, id) => n + (data.value?.[id] || []).length, 0));

const columns = () => [
  { key: "bucket", label: t("hgap.colBucket") },
  { key: "order", label: t("hgap.colOrder") },
  { key: "dn", label: t("hgap.colDn") },
  { key: "awb", label: t("hgap.colAwb") },
  { key: "customer", label: t("hgap.colCustomer") },
  { key: "phone", label: t("hgap.colPhone") },
  { key: "city", label: t("hgap.colCity") },
  { key: "status", label: t("hgap.colStatus") },
  { key: "manifest", label: t("nl.colManifest") },
  { key: "pickList", label: t("nl.colPickList") },
  { key: "mad", label: t("hgap.colMad") },
  { key: "ageD", label: t("nl.colAgeD") },
];
const shape = (rows, id) => (rows || []).map((r) => ({ ...r, bucket: t("nl.tab_" + id) }));

function exportTab() {
  const n = downloadCsv(stampName("never-left-" + tab.value), columns(), shape(activeRows.value, tab.value));
  success(t("hgap.exported").replace("{n}", String(n)), "");
}
function exportAll() {
  const rows = BUCKETS.flatMap((id) => shape(data.value?.[id], id));
  const n = downloadCsv(stampName("never-left-all"), columns(), rows);
  success(t("hgap.exported").replace("{n}", String(n)), "");
}

async function load() {
  loading.value = true;
  const r = await liveOr(null, () => api("shipping.never_left", { days: 60 })).catch(() => null);
  if (r) data.value = r;
  if (r && !(r[tab.value] || []).length) {
    const first = BUCKETS.find((id) => (r[id] || []).length);
    if (first) tab.value = first;
  }
  loading.value = false;
}

onMounted(load);
</script>
