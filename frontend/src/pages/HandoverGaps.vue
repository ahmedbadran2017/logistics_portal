<template>
  <div class="max-w-[1180px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('hgap.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('hgap.intro') }}</p>
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

    <!-- Four questions, in the order the parcel fails them. -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <button v-for="k in tabs" :key="k.id"
              class="text-start bg-white rounded-xl ring-1 p-4 transition-all"
              :class="tab === k.id ? 'ring-2 ring-[var(--accent-400)] shadow-[0_2px_12px_-4px_rgba(0,0,0,0.12)]'
                      : k.n ? 'ring-stone-200/70 hover:ring-stone-300' : 'ring-stone-200/70 opacity-70'"
              @click="tab = k.id">
        <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ k.label }}</div>
        <div class="text-[24px] font-extrabold tabular-nums mt-1"
             :class="k.n ? k.tone : 'text-stone-300'">{{ fmt(k.n) }}</div>
        <div class="text-[11px] text-stone-400 mt-0.5 leading-snug">{{ k.hint }}</div>
      </button>
    </div>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 6" :key="n" class="h-[46px] rounded-xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
    </div>

    <template v-else>
      <p class="text-[12.5px] text-stone-600 bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-2.5">
        {{ activeHint }}
      </p>

      <div v-if="!activeRows.length" class="bg-white rounded-xl ring-1 ring-emerald-200/70 p-10 text-center">
        <Icon name="check-circle" :size="22" class="mx-auto mb-2 text-emerald-500" />
        <div class="text-[13px] font-semibold text-stone-700">{{ t('hgap.clean') }}</div>
      </div>

      <div v-else class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="divide-y divide-stone-100 max-h-[62vh] overflow-y-auto">
          <button v-for="(r, i) in activeRows" :key="(r.order || r.dn) + i"
                  class="w-full text-start px-4 py-2.5 flex items-center gap-2.5 flex-wrap hover:bg-stone-50"
                  @click="r.order && $router.push({ name: 'OrderDetail', params: { name: r.order } })">
            <span class="font-mono text-[12px] font-semibold text-stone-900">{{ r.order || r.dn }}</span>
            <span v-if="r.noAwb" class="text-[10px] font-bold px-1.5 h-[17px] inline-flex items-center rounded bg-rose-600 text-white">
              {{ t('shp.offbookNoAwb') }}
            </span>
            <span v-else-if="r.awb" class="font-mono text-[11px] text-stone-400">{{ r.awb }}</span>
            <span class="text-[11.5px] text-stone-500 truncate max-w-[190px]" dir="auto">{{ r.customer }}</span>
            <span v-if="r.city" class="text-[11px] text-stone-400">{{ r.city }}</span>
            <span class="text-[11px] text-stone-500">{{ r.track || r.status || '—' }}</span>
            <span v-if="r.mad !== undefined" class="ms-auto text-[12px] font-semibold text-stone-900 tabular-nums whitespace-nowrap">
              {{ fmtMAD(r.mad) }} MAD
            </span>
            <span class="text-[11px] text-stone-400 tabular-nums w-14 text-end"
                  :class="!r.mad && r.mad !== 0 ? 'ms-auto' : ''">{{ r.ageH }}h</span>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { fmtMAD } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";
import { downloadCsv, stampName } from "@/lib/csvExport";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success } = useToast();

const offbook = ref(null);
const orphans = ref(null);
const loading = ref(true);
const tab = ref("live");

const fmt = (v) => (Number(v) || 0).toLocaleString("en-US");

const tabs = computed(() => [
  { id: "live", label: t("hgap.tabLive"), hint: t("hgap.tabLiveHint"),
    n: offbook.value?.live.length || 0, tone: "text-rose-600" },
  { id: "nodoc", label: t("hgap.tabNoDoc"), hint: t("hgap.tabNoDocHint"),
    n: offbook.value?.noDoc.length || 0, tone: "text-rose-600" },
  { id: "stuck", label: t("hgap.tabStuck"), hint: t("hgap.tabStuckHint"),
    n: orphans.value?.stuckN || 0, tone: "text-amber-600" },
  { id: "settled", label: t("hgap.tabSettled"), hint: t("hgap.tabSettledHint"),
    n: offbook.value?.settled.length || 0, tone: "text-stone-700" },
]);

const activeRows = computed(() => {
  if (tab.value === "live") return offbook.value?.live || [];
  if (tab.value === "nodoc") return offbook.value?.noDoc || [];
  if (tab.value === "settled") return offbook.value?.settled || [];
  return orphans.value?.stuck || [];
});

const activeHint = computed(() => t("hgap.hint_" + tab.value));

// The column set is the same for every bucket, so one export covers all four
// and a `bucket` column keeps them apart in the sheet. `noAwb` travels as a
// word rather than true/false: the person filtering this in Excel is looking
// for the ones with nothing to chase.
const columns = () => [
  { key: "bucket", label: t("hgap.colBucket") },
  { key: "order", label: t("hgap.colOrder") },
  { key: "dn", label: t("hgap.colDn") },
  { key: "awb", label: t("hgap.colAwb") },
  { key: "customer", label: t("hgap.colCustomer") },
  { key: "phone", label: t("hgap.colPhone") },
  { key: "city", label: t("hgap.colCity") },
  { key: "status", label: t("hgap.colStatus") },
  { key: "track", label: t("hgap.colTrack") },
  { key: "mad", label: t("hgap.colMad") },
  { key: "ageH", label: t("hgap.colAge") },
];

function shape(rows, bucketId) {
  return (rows || []).map((r) => ({
    bucket: t("hgap.tab" + bucketId),
    order: r.order || "",
    dn: r.dn || "",
    awb: r.awb || (r.noAwb ? t("hgap.noAwbWord") : ""),
    customer: r.customer || "",
    phone: r.phone || "",
    city: r.city || "",
    status: r.status || "",
    track: r.track || "",
    mad: r.mad === undefined ? "" : r.mad,
    ageH: r.ageH ?? "",
  }));
}

const BUCKETS = [
  ["live", "Live"], ["nodoc", "NoDoc"], ["stuck", "Stuck"], ["settled", "Settled"],
];
const rowsFor = (id) => (id === "live" ? offbook.value?.live
  : id === "nodoc" ? offbook.value?.noDoc
  : id === "settled" ? offbook.value?.settled
  : orphans.value?.stuck) || [];

const totalRows = computed(() =>
  BUCKETS.reduce((n, [id]) => n + rowsFor(id).length, 0));

function exportTab() {
  const id = BUCKETS.find(([b]) => b === tab.value);
  const n = downloadCsv(stampName("handover-gaps-" + tab.value), columns(),
                        shape(activeRows.value, id[1]));
  success(t("hgap.exported").replace("{n}", String(n)), "");
}

function exportAll() {
  const rows = BUCKETS.flatMap(([id, label]) => shape(rowsFor(id), label));
  const n = downloadCsv(stampName("handover-gaps-all"), columns(), rows);
  success(t("hgap.exported").replace("{n}", String(n)), "");
}

async function load() {
  loading.value = true;
  const [ob, or_] = await Promise.all([
    liveOr(null, () => api("shipping.offbook_parcels", { days: 30 })).catch(() => null),
    liveOr(null, () => api("shipping.label_orphans")).catch(() => null),
  ]);
  if (ob) offbook.value = ob;
  if (or_) orphans.value = or_;
  loading.value = false;
}

onMounted(load);
</script>
