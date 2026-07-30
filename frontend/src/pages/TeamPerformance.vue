<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1280px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('tp.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('tp.intro') }}</p>
      </div>
      <DateRange v-model:days="days" v-model:frm="frm" v-model:to="to" @change="load" />
    </header>

    <!-- loading / error -->
    <div v-if="loading" class="space-y-3">
      <div class="h-[92px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="h-[280px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[460px] mx-auto break-words">{{ loadError }}</div>
    </div>

    <template v-else-if="d">
      <!-- team KPI band -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div class="tp-kpi">
          <span class="tp-kpi-l">{{ t('tp.kBook') }}</span>
          <span class="tp-kpi-n">{{ num(d.kpis.book) }}</span>
          <span class="tp-kpi-s">{{ d.kpis.agents }} {{ t('tp.agents') }}</span>
        </div>
        <div class="tp-kpi">
          <span class="tp-kpi-l">{{ t('tp.kConfirmed') }}</span>
          <span class="tp-kpi-n text-emerald-600">{{ num(d.kpis.confirmed) }}</span>
          <span class="tp-kpi-s">{{ d.kpis.confirmRate }}% {{ t('tp.rate') }}</span>
        </div>
        <div class="tp-kpi">
          <span class="tp-kpi-l">{{ t('tp.kDelivered') }}</span>
          <span class="tp-kpi-n">{{ num(d.kpis.delivered) }}</span>
          <span class="tp-kpi-s">{{ d.kpis.deliveryRate }}% {{ t('tp.delivRate') }}</span>
        </div>
        <div class="tp-kpi">
          <span class="tp-kpi-l">{{ t('tp.kReturned') }}</span>
          <span class="tp-kpi-n" :class="d.kpis.returned ? 'text-rose-600' : 'text-stone-900'">{{ num(d.kpis.returned) }}</span>
          <span class="tp-kpi-s">{{ t('tp.ofDelivered') }}</span>
        </div>
        <div class="tp-kpi">
          <span class="tp-kpi-l">{{ t('tp.kCollected') }}</span>
          <span class="tp-kpi-n">{{ fmtMAD(d.kpis.collected) }}</span>
          <span class="tp-kpi-s">MAD {{ t('tp.landed') }}</span>
        </div>
        <div class="tp-kpi">
          <span class="tp-kpi-l">{{ t('tp.kPicks') }}</span>
          <span class="tp-kpi-n">{{ num(d.kpis.picks) }}</span>
          <span class="tp-kpi-s">{{ d.kpis.pickers }} {{ t('tp.pickers') }}</span>
        </div>
      </div>

      <p class="text-[11px] text-stone-400 -mt-1 max-w-[720px] leading-relaxed">{{ t('tp.basis') }}</p>

      <!-- Confirmation scorecard -->
      <section class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-3 border-b border-stone-100 flex items-center gap-2">
          <Icon name="phone" :size="15" class="text-stone-400" />
          <span class="text-[13px] font-bold text-stone-900">{{ t('tp.confTitle') }}</span>
          <span class="text-[11px] text-stone-400 ms-auto">{{ t('tp.confHint') }}</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[860px] text-[12.5px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100 select-none">
                <th class="text-start px-4 py-2.5 w-8">#</th>
                <th class="text-start px-2 py-2.5">{{ t('tp.cAgent') }}</th>
                <th v-for="c in confCols" :key="c.key"
                    class="text-end px-2 py-2.5 cursor-pointer hover:text-stone-700"
                    :class="c.last ? 'pe-4' : ''" @click="setSort(c.key)">
                  {{ t(c.label) }}<span v-if="sortBy === c.key" class="ms-0.5">{{ sortDir === 'desc' ? '▾' : '▴' }}</span>
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-50">
              <tr v-for="(r, i) in confSorted" :key="r.user" class="hover:bg-stone-50">
                <td class="px-4 py-2.5 text-stone-400 tabular-nums">{{ i + 1 }}</td>
                <td class="px-2 py-2.5">
                  <div class="font-semibold text-stone-900 truncate max-w-[160px]">{{ r.name }}</div>
                </td>
                <td class="px-2 py-2.5 text-end tabular-nums text-stone-700">{{ num(r.book) }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums">
                  <span :class="rateColor(r.confirmRate, 75, 60)">{{ r.confirmRate }}%</span>
                  <span class="text-stone-300 text-[10.5px]"> · {{ num(r.confirmed) }}</span>
                </td>
                <td class="px-2 py-2.5 text-end tabular-nums text-stone-700">{{ num(r.delivered) }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums">
                  <span :class="rateColor(r.deliveryRate, 90, 80)">{{ r.deliveryRate }}%</span>
                </td>
                <td class="px-2 py-2.5 text-end tabular-nums" :class="r.returned ? 'text-rose-500' : 'text-stone-300'">{{ num(r.returned) }}</td>
                <td class="px-2 py-2.5 text-end">
                  <div class="flex items-center justify-end gap-2">
                    <div class="h-1.5 rounded-full bg-emerald-500/80" :style="{ width: bar(r.collected, maxCollected) }" />
                    <span class="tabular-nums font-semibold text-stone-800 w-[70px] text-end">{{ fmtMAD(r.collected) }}</span>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-end tabular-nums text-stone-400">{{ num(r.edits) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!d.confirmation.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('cf.empty') }}</div>
      </section>

      <div class="grid lg:grid-cols-2 gap-3">
        <!-- Warehouse scorecard -->
        <section class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-3 border-b border-stone-100 flex items-center gap-2">
            <Icon name="package" :size="15" class="text-stone-400" />
            <span class="text-[13px] font-bold text-stone-900">{{ t('tp.whTitle') }}</span>
            <span class="text-[11px] text-stone-400 ms-auto">{{ t('tp.whHint') }}</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[420px] text-[12.5px]">
              <thead>
                <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                  <th class="text-start px-4 py-2.5">{{ t('tp.cPicker') }}</th>
                  <th class="text-end px-2 py-2.5">{{ t('tp.cPicks') }}</th>
                  <th class="text-end px-2 py-2.5">{{ t('tp.cPerDay') }}</th>
                  <th class="text-end px-4 py-2.5">{{ t('tp.cSameday') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-stone-50">
                <tr v-for="r in d.warehouse" :key="r.user" class="hover:bg-stone-50">
                  <td class="px-4 py-2.5 font-semibold text-stone-900 truncate max-w-[150px]">{{ r.name }}</td>
                  <td class="px-2 py-2.5 text-end tabular-nums text-stone-700">{{ num(r.picks) }}</td>
                  <td class="px-2 py-2.5 text-end tabular-nums text-stone-500">{{ r.perDay }}</td>
                  <td class="px-4 py-2.5 text-end tabular-nums">
                    <span :class="rateColor(r.samedayRate, 45, 30)">{{ r.samedayRate }}%</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!d.warehouse.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('cf.empty') }}</div>
        </section>

        <!-- Activity (desk workers not captured by book or picks) + tickets -->
        <div class="space-y-3">
          <section v-if="d.activity.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
            <div class="px-4 py-3 border-b border-stone-100 flex items-center gap-2">
              <Icon name="activity" :size="15" class="text-stone-400" />
              <span class="text-[13px] font-bold text-stone-900">{{ t('tp.actTitle') }}</span>
            </div>
            <ul class="p-2">
              <li v-for="r in d.activity" :key="r.user" class="flex items-center gap-2 px-2 py-1.5">
                <span class="text-[12.5px] font-semibold text-stone-800 truncate flex-1">{{ r.name }}</span>
                <span class="text-[12px] tabular-nums text-stone-500">{{ num(r.edits) }} {{ t('tp.edits') }}</span>
              </li>
            </ul>
            <p class="text-[10.5px] text-stone-400 px-4 pb-3">{{ t('tp.actHint') }}</p>
          </section>

          <section v-if="d.tickets.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
            <div class="px-4 py-3 border-b border-stone-100 flex items-center gap-2">
              <Icon name="message-circle" :size="15" class="text-stone-400" />
              <span class="text-[13px] font-bold text-stone-900">{{ t('tp.tkTitle') }}</span>
            </div>
            <ul class="p-2">
              <li v-for="r in d.tickets" :key="r.user" class="flex items-center gap-2 px-2 py-1.5">
                <span class="text-[12.5px] font-semibold text-stone-800 truncate flex-1">{{ r.name }}</span>
                <span class="text-[12px] tabular-nums text-stone-500">{{ r.resolved }}/{{ r.handled }} · {{ r.resolveRate }}%</span>
              </li>
            </ul>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import DateRange from "@/components/ui/DateRange.vue";
import { api, num } from "@/lib/resource";
import { fmtMAD } from "@/lib/handoffData";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();

const days = ref(30);
const frm = ref("");
const to = ref("");
const d = ref(null);
const loading = ref(true);
const loadError = ref("");

// Sortable confirmation columns. `key` matches a row field.
const confCols = [
  { key: "book", label: "tp.cBook" },
  { key: "confirmRate", label: "tp.cConfirm" },
  { key: "delivered", label: "tp.cDelivered" },
  { key: "deliveryRate", label: "tp.cDelivRate" },
  { key: "returned", label: "tp.cReturned" },
  { key: "collected", label: "tp.cCollected" },
  { key: "edits", label: "tp.cEdits", last: true },
];
const sortBy = ref("collected");
const sortDir = ref("desc");
function setSort(key) {
  if (sortBy.value === key) sortDir.value = sortDir.value === "desc" ? "asc" : "desc";
  else { sortBy.value = key; sortDir.value = "desc"; }
}
const confSorted = computed(() => {
  const rows = [...(d.value?.confirmation || [])];
  const k = sortBy.value, dir = sortDir.value === "desc" ? -1 : 1;
  return rows.sort((a, b) => ((a[k] || 0) - (b[k] || 0)) * dir);
});
const maxCollected = computed(() =>
  Math.max(1, ...(d.value?.confirmation || []).map((r) => r.collected || 0)));

function bar(v, max) { return Math.round((v / max) * 46) + "px"; }
function rateColor(v, good, ok) {
  if (v >= good) return "text-emerald-600 font-semibold";
  if (v >= ok) return "text-amber-600 font-semibold";
  return "text-rose-600 font-semibold";
}

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    d.value = await api("admin_performance.team_scorecard", {
      days: days.value, frm: frm.value || undefined, to: to.value || undefined,
    });
  } catch (e) {
    loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
.tp-kpi {
  display: flex; flex-direction: column; gap: 2px;
  background: #fff; border-radius: 14px; padding: 12px 14px;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8);
}
.tp-kpi-l { font-size: 10px; font-weight: 700; color: rgb(120 113 108); text-transform: uppercase; letter-spacing: .04em; }
.tp-kpi-n { font-size: 22px; font-weight: 800; color: rgb(28 25 23); font-variant-numeric: tabular-nums; line-height: 1.15; }
.tp-kpi-s { font-size: 10.5px; color: rgb(168 162 158); font-variant-numeric: tabular-nums; }
</style>
