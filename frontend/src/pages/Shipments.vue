<template>
  <div class="max-w-[1240px] mx-auto px-6 py-6">
    <!-- ── Detail view ─────────────────────────────────────────── -->
    <template v-if="openSh">
      <button
        class="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"
        @click="open = null"
      >
        <Icon name="chevron-left" :size="15" class="flip-rtl" /> {{ t("shp.back") }}
      </button>

      <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div class="flex items-center gap-3">
            <span class="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Icon name="file-text" :size="22" />
            </span>
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <h1 class="font-mono text-[19px] font-bold text-stone-900">{{ openSh.no }}</h1>
                <span
                  class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 whitespace-nowrap"
                  :class="statusPill(openSh.status)"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="statusDot(openSh.status)" />
                  {{ openSh.status }}
                </span>
              </div>
              <div class="text-[12.5px] text-stone-600 mt-1">
                {{ openSh.carrier }} · {{ openSh.service ?? '—' }} · {{ openSh.date }} · {{ openSh.window ?? '—' }}
              </div>
            </div>
          </div>
          <a :href="'/app/shipment/' + encodeURIComponent(openSh.no)" target="_blank"
             class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300">
            {{ t("shp.openErpNext") }} <Icon name="arrow-right" :size="13" class="flip-rtl" />
          </a>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
          <div v-for="st in detailStats" :key="st.label" class="bg-stone-50 rounded-lg px-3 py-2">
            <div class="text-[10px] font-semibold uppercase tracking-wide text-stone-400">{{ st.label }}</div>
            <div class="text-[15px] font-semibold text-stone-900 tabular-nums mt-0.5">
              {{ st.value }}<span v-if="st.unit" class="text-[10px] text-stone-400 ms-1">{{ st.unit }}</span>
            </div>
          </div>
        </div>

        <div v-if="openSh.delivered > 0" class="mt-4">
          <div class="flex items-center justify-between text-[11px] mb-1">
            <span class="text-stone-500 tabular-nums">{{ openSh.delivered }}/{{ openSh.parcels }} {{ t("shp.delivered") }}</span>
            <span class="text-emerald-600 font-semibold tabular-nums">{{ Math.round((openSh.delivered / openSh.parcels) * 100) }}%</span>
          </div>
          <div class="h-2 rounded-full bg-stone-100 overflow-hidden">
            <div class="h-full bg-emerald-500 rounded-full" :style="{ width: (openSh.delivered / openSh.parcels) * 100 + '%' }" />
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4">
        <!-- pickup → delivery -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden h-fit">
          <div class="px-4 py-3 border-b border-stone-100">
            <div class="text-[13px] font-semibold text-stone-900">{{ t("shp.pickupTo") }}</div>
          </div>
          <div class="p-4 space-y-3">
            <div class="flex items-start gap-2.5">
              <span class="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Icon name="map-pin" :size="14" />
              </span>
              <div>
                <div class="text-[12.5px] font-medium text-stone-900">{{ openSh.pickup ?? '—' }}</div>
                <div class="text-[11px] text-stone-500">{{ openSh.pickupContact ?? '' }}</div>
              </div>
            </div>
            <div class="ms-3.5 h-4 w-px bg-stone-200" />
            <div class="flex items-start gap-2.5">
              <span class="w-7 h-7 rounded-lg bg-cyan-50 text-cyan-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Icon name="globe" :size="14" />
              </span>
              <div>
                <div class="text-[12.5px] font-medium text-stone-900">{{ openSh.deliveryTo ?? '—' }}</div>
                <div class="text-[11px] text-stone-500">{{ openSh.window ?? '—' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- tracking / meta -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden h-fit">
          <div class="px-4 py-3 border-b border-stone-100">
            <div class="text-[13px] font-semibold text-stone-900">{{ t("shp.tracking") }}</div>
          </div>
          <div class="p-4 space-y-1.5 text-[12px]">
            <div v-for="r in trackingRows" :key="r.k" class="flex items-center justify-between gap-2">
              <span class="text-stone-400">{{ r.k }}</span>
              <span class="font-mono font-medium text-stone-800 truncate">{{ r.v }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── List view ───────────────────────────────────────────── -->
    <template v-else>
      <div class="flex items-start justify-between gap-4 mb-5 flex-wrap">
        <div>
          <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t("shp.title") }}</h1>
          <p class="text-[12.5px] text-stone-500 mt-0.5">{{ CARRIER }} · {{ WAREHOUSE }}</p>
        </div>
        <div class="flex items-center gap-2">
          <a href="/app/shipment" target="_blank" class="inline-flex items-center gap-1.5 px-3 h-9 text-[13px] font-medium text-stone-700 bg-white rounded-lg ring-1 ring-stone-200 hover:ring-stone-300 transition-colors whitespace-nowrap">
            <Icon name="globe" :size="15" /> {{ t("shp.openErp") }}
          </a>
          <button class="inline-flex items-center gap-1.5 px-3 h-9 text-[13px] font-medium text-white bg-stone-900 rounded-lg hover:bg-stone-800 transition-colors whitespace-nowrap"
                  @click="$router.push({ name: 'Manifest' })">
            <Icon name="plus" :size="15" /> {{ t("shp.todaysManifest") }}
          </button>
        </div>
      </div>

      <!-- KPI strip -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3.5">
          <div class="flex items-center gap-1.5 text-[11.5px] font-medium text-stone-500">
            <span class="w-6 h-6 rounded-lg flex items-center justify-center" :class="k.tone">
              <Icon :name="k.icon" :size="13" />
            </span>
            {{ k.label }}
          </div>
          <div class="text-[22px] font-semibold text-stone-900 tabular-nums mt-1.5 leading-none">
            {{ k.value }}<span v-if="k.unit" class="text-[11px] text-stone-400 ms-1 font-normal">{{ k.unit }}</span>
          </div>
        </div>
      </div>

      <!-- search + filters -->
      <div class="flex items-center gap-2 mb-3 flex-wrap">
        <div class="relative flex-1 min-w-[180px]">
          <Icon name="search" :size="14" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <input
            v-model="q"
            :placeholder="t('shp.searchPh')"
            class="w-full h-9 ps-9 pe-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none"
          />
        </div>
        <div class="flex items-center gap-1.5 overflow-x-auto">
          <button
            v-for="f in statusFilters"
            :key="f.key"
            class="px-2.5 h-7 text-[12px] font-medium rounded-lg ring-1 transition-colors whitespace-nowrap"
            :class="filter === f.key ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'"
            @click="filter = f.key"
          >
            {{ f.label }}
          </button>
        </div>
      </div>

      <!-- table -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full min-w-[720px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t("shp.thShipment") }}</th>
                <th class="text-start px-4 py-2.5">{{ t("shp.thDate") }}</th>
                <th class="text-start px-4 py-2.5 hidden lg:table-cell">{{ t("shp.thAwb") }}</th>
                <th class="text-end px-4 py-2.5">{{ t("shp.thParcels") }}</th>
                <th class="text-end px-4 py-2.5 hidden sm:table-cell">{{ t("shp.thValue") }}</th>
                <th class="text-end px-4 py-2.5 hidden md:table-cell">{{ t("shp.thDelivered") }}</th>
                <th class="text-start px-4 py-2.5">{{ t("shp.thStatus") }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr
                v-for="s in shown"
                :key="s.no"
                class="cursor-pointer transition-colors hover:bg-stone-50"
                @click="open = s.no"
              >
                <td class="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900">{{ s.no }}</td>
                <td class="px-4 py-2.5 text-[12px] text-stone-600 whitespace-nowrap">{{ s.date }}</td>
                <td class="px-4 py-2.5 font-mono text-[11.5px] text-stone-500 hidden lg:table-cell">{{ s.awb }}</td>
                <td class="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{{ s.parcels }}</td>
                <td class="px-4 py-2.5 text-end text-[12px] text-stone-600 tabular-nums hidden sm:table-cell">{{ fmtMAD(s.value) }}</td>
                <td class="px-4 py-2.5 text-end text-[12px] tabular-nums hidden md:table-cell whitespace-nowrap">
                  <span v-if="s.delivered" class="text-emerald-600">{{ s.delivered }}/{{ s.parcels }}</span>
                  <span v-else class="text-stone-300">—</span>
                  <span v-if="s.exceptions" class="text-rose-600 ms-1.5">· {{ s.exceptions }} {{ t("shp.excShort") }}</span>
                </td>
                <td class="px-4 py-2.5">
                  <span
                    class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 whitespace-nowrap"
                    :class="statusPill(s.status)"
                  >
                    <span class="w-1.5 h-1.5 rounded-full" :class="statusDot(s.status)" />
                    {{ s.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="shown.length === 0" class="text-center text-[12.5px] text-stone-400 py-12">
          {{ t("shp.noMatch") }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { SHIPMENTS as DEMO_SHIPMENTS, CARRIER, WAREHOUSE, fmtMAD } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();

const q = ref("");
const filter = ref("all");
const open = ref(null);

// Live-or-demo shipments. `shipping.shipments` fills this once installed;
// falls back to the demo seed in local preview / on error.
const shipments = ref([]);

onMounted(async () => {
  const live = await liveOr(null, () => api("shipping.shipments", { limit: 30 }));
  if (live && live.length) shipments.value = live;
});

const statusFilters = computed(() => [
  { key: "all", label: t("shp.fAll") },
  { key: "Draft", label: t("shp.fDraft") },
  { key: "Submitted", label: t("shp.fSubmitted") },
  { key: "Booked", label: t("shp.fBooked") },
  { key: "Completed", label: t("shp.fCompleted") },
]);

// status → pill color by status
const STATUS_PILL = {
  Draft: "text-stone-600 bg-stone-100 ring-stone-200",
  Submitted: "text-emerald-700 bg-emerald-50 ring-emerald-200",
  Booked: "text-amber-700 bg-amber-50 ring-amber-200",
  Completed: "text-stone-600 bg-stone-100 ring-stone-200",
  Cancelled: "text-rose-700 bg-rose-50 ring-rose-200",
};
const STATUS_DOT = {
  Draft: "bg-stone-400",
  Submitted: "bg-emerald-500",
  Booked: "bg-amber-500",
  Completed: "bg-emerald-500",
  Cancelled: "bg-rose-500",
};
function statusPill(s) { return STATUS_PILL[s] || STATUS_PILL.Draft; }
function statusDot(s) { return STATUS_DOT[s] || STATUS_DOT.Draft; }

const shown = computed(() =>
  shipments.value.filter(
    (s) =>
      (filter.value === "all" || s.status === filter.value) &&
      (!q.value || s.no.toLowerCase().includes(q.value.toLowerCase()))
  )
);

// KPI strip: this-week shipments, parcels today, avg value
const weekCount = computed(() => {
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 7);
  return shipments.value.filter((s) => new Date(s.date) >= cutoff).length;
});
const parcelsToday = computed(() => shipments.value[0]?.parcels ?? 0);
const avgValue = computed(() => {
  if (!shipments.value.length) return 0;
  return Math.round(shipments.value.reduce((a, s) => a + s.value, 0) / shipments.value.length);
});

const kpis = computed(() => [
  { label: t("shp.weekCount"), icon: "truck", tone: "bg-stone-100 text-stone-500", value: weekCount.value },
  { label: t("shp.parcelsToday"), icon: "package", tone: "bg-cyan-50 text-cyan-600", value: parcelsToday.value },
  { label: t("shp.avgValue"), icon: "trending-up", tone: "bg-emerald-50 text-emerald-600", value: fmtMAD(avgValue.value), unit: "MAD" },
  { label: t("shp.carrier"), icon: "send", tone: "bg-amber-50 text-amber-600", value: CARRIER },
]);

// selected shipment
const openSh = computed(() => shipments.value.find((s) => s.no === open.value) || null);

const detailStats = computed(() => {
  const s = openSh.value;
  if (!s) return [];
  if (s.weight == null && s.pallets == null) {
    return [
      { label: t("shp.stParcels"), value: s.parcels },
      { label: t("shp.stDelivered"), value: s.delivered ?? 0 },
      { label: t("shp.stExceptions"), value: s.exceptions ?? 0 },
      { label: t("shp.stValue"), value: fmtMAD(s.value), unit: "MAD" },
      { label: t("shp.stStatus"), value: s.status },
    ];
  }
  return [
    { label: "Parcels", value: s.parcels },
    { label: "Value", value: fmtMAD(s.value), unit: "MAD" },
    { label: "Weight", value: s.weight ?? "—", unit: s.weight != null ? "kg" : "" },
    { label: "Pallets", value: s.pallets ?? "—" },
    { label: "Incoterm", value: s.incoterm ?? "—" },
  ];
});

const trackingRows = computed(() => {
  const s = openSh.value;
  if (!s) return [];
  return [
    { k: t("shp.thAwb"), v: s.awb ?? "—" },
    { k: t("shp.rService"), v: s.service ?? "—" },
    { k: t("shp.rWindow"), v: s.window ?? "—" },
    { k: t("shp.rPickup"), v: s.pickup ?? "—" },
    { k: t("shp.rDeliveryTo"), v: s.deliveryTo ?? "—" },
  ];
});
</script>
