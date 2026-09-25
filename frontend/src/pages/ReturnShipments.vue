<template>
  <div class="max-w-[1180px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('retsh.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('retsh.intro') }}</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <button
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]"
          @click="$router.push({ name: 'ReturnReceiving' })">
          <Icon name="package" :size="14" />{{ t('retsh.goReceive') }}
        </button>
      </div>
    </header>

    <!-- KPIs. Shortage leads: it is the only number here that is an argument
         with somebody, and it used to be buried inside a tab. -->
    <div v-if="kpis" class="grid grid-cols-2 md:grid-cols-5 gap-3">
      <div class="bg-white rounded-xl ring-1 p-4"
           :class="kpis.missing ? 'ring-rose-200/70' : 'ring-stone-200/70'">
        <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('retsh.kMissing') }}</div>
        <div class="text-[24px] font-extrabold tabular-nums mt-1"
             :class="kpis.missing ? 'text-rose-600' : 'text-stone-900'">{{ fmt(kpis.missing) }}</div>
        <div class="text-[11px] text-stone-400 mt-0.5">{{ t('retsh.kMissingSub').replace('{n}', String(kpis.shortBatches)) }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('retsh.kBatches') }}</div>
        <div class="text-[24px] font-extrabold tabular-nums text-stone-900 mt-1">{{ fmt(kpis.batches) }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('retsh.kOrders') }}</div>
        <div class="text-[24px] font-extrabold tabular-nums text-stone-900 mt-1">{{ fmt(kpis.orders) }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('retsh.kUnits') }}</div>
        <div class="text-[24px] font-extrabold tabular-nums text-stone-900 mt-1">{{ fmt(kpis.units) }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 p-4"
           :class="kpis.openDrafts ? 'ring-amber-200/70' : 'ring-stone-200/70'">
        <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('retsh.kOpen') }}</div>
        <div class="text-[24px] font-extrabold tabular-nums mt-1"
             :class="kpis.openDrafts ? 'text-amber-600' : 'text-stone-900'">{{ fmt(kpis.openDrafts) }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex items-center gap-2 flex-wrap">
      <div class="relative flex-1 min-w-[200px]">
        <Icon name="search" :size="14" class="absolute start-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
        <input v-model="q" :placeholder="t('retsh.searchPh')" @keyup.enter="reload"
               class="w-full h-9 ps-8 pe-3 rounded-lg text-[12.5px] bg-white ring-1 ring-stone-200 focus:ring-[var(--accent-400)] outline-none" />
      </div>
      <button v-for="d in [7, 30, 90, 365]" :key="d"
              class="h-9 px-3 rounded-lg text-[12px] font-semibold tabular-nums ring-1 transition-colors"
              :class="days === d ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]' : 'text-stone-700 bg-white ring-stone-200 hover:bg-stone-50'"
              @click="days = d; reload()">{{ d }}{{ t('retsh.dayUnit') }}</button>
      <button
        class="h-9 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors inline-flex items-center gap-1.5"
        :class="onlyShort ? 'text-white bg-rose-600 ring-rose-600' : 'text-stone-700 bg-white ring-stone-200 hover:bg-stone-50'"
        @click="onlyShort = !onlyShort; reload()">
        <Icon name="alert-triangle" :size="13" />{{ t('retsh.onlyShort') }}
      </button>
    </div>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 5" :key="n" class="h-[58px] rounded-xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
    </div>

    <div v-else-if="!rows.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="package" :size="22" class="mx-auto mb-2 text-stone-300" />
      <div class="text-[13px] font-semibold text-stone-700">{{ t('retsh.empty') }}</div>
    </div>

    <div v-else class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-[12.5px]">
          <thead class="bg-stone-50/80 text-[11px] uppercase tracking-[0.04em] text-stone-400">
            <tr>
              <th class="px-4 py-2.5 text-start font-semibold">{{ t('retsh.thBatch') }}</th>
              <th class="px-3 py-2.5 text-start font-semibold">{{ t('retsh.thDate') }}</th>
              <th class="px-3 py-2.5 text-start font-semibold">{{ t('retsh.thBy') }}</th>
              <th class="px-3 py-2.5 text-end font-semibold">{{ t('retsh.thParcels') }}</th>
              <th class="px-3 py-2.5 text-end font-semibold">{{ t('retsh.thUnits') }}</th>
              <th class="px-3 py-2.5 text-end font-semibold">{{ t('retsh.thMissing') }}</th>
              <th class="px-3 py-2.5 text-start font-semibold">{{ t('retsh.thStatus') }}</th>
              <th class="px-3 py-2.5"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr v-for="r in rows" :key="r.no"
                class="transition-colors cursor-pointer hover:bg-stone-50"
                :class="r.missing ? 'bg-rose-50/40' : ''" @click="open(r)">
              <td class="px-4 py-2.5 font-mono font-semibold text-stone-900 whitespace-nowrap">{{ r.no }}</td>
              <td class="px-3 py-2.5 text-stone-600 tabular-nums whitespace-nowrap">{{ r.date }}</td>
              <td class="px-3 py-2.5 text-stone-600 truncate max-w-[130px]">{{ r.owner }}</td>
              <td class="px-3 py-2.5 text-end tabular-nums text-stone-800">{{ fmt(r.parcels) }}</td>
              <td class="px-3 py-2.5 text-end tabular-nums text-stone-800">{{ fmt(r.actual) }}<span class="text-stone-400">/{{ fmt(r.ordered) }}</span></td>
              <td class="px-3 py-2.5 text-end tabular-nums font-bold"
                  :class="r.missing ? 'text-rose-600' : 'text-stone-300'">{{ r.missing || '—' }}</td>
              <td class="px-3 py-2.5">
                <span class="inline-flex items-center px-2 h-[21px] rounded-md text-[11px] font-semibold ring-1"
                      :class="r.draft ? 'text-amber-700 bg-amber-50 ring-amber-200'
                              : 'text-emerald-700 bg-emerald-50 ring-emerald-200'">
                  {{ r.draft ? t('retsh.draft') : t('retsh.posted') }}
                </span>
              </td>
              <td class="px-3 py-2.5 text-end">
                <button class="h-7 px-2 rounded-lg text-[11.5px] font-semibold text-stone-600 bg-stone-100 hover:bg-stone-200 inline-flex items-center gap-1"
                        :disabled="printing === r.no" @click.stop="doPrint(r.no)">
                  <Icon name="printer" :size="12" />{{ printing === r.no ? '…' : t('retsh.print') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="total > rows.length" class="px-4 py-2.5 border-t border-stone-100 flex items-center gap-2">
        <span class="text-[11.5px] text-stone-400 tabular-nums">{{ rows.length }} / {{ total }}</span>
        <button class="ms-auto h-8 px-3 rounded-lg text-[12px] font-semibold text-stone-700 bg-stone-100 hover:bg-stone-200"
                :disabled="loading" @click="more">{{ t('retsh.more') }}</button>
      </div>
    </div>

    <!-- Detail drawer: the parcels of one batch, shortages first -->
    <div v-if="detail" class="fixed inset-0 z-[160] flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div class="absolute inset-0 bg-stone-900/40" @click="detail = null" />
      <div class="relative w-full max-w-[720px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] overflow-hidden flex flex-col max-h-[84vh]">
        <header class="flex items-start justify-between gap-3 px-5 py-3.5 border-b border-stone-100">
          <div class="min-w-0">
            <div class="font-mono text-[14px] font-bold text-stone-900">{{ detail.batch }}</div>
            <div class="text-[11.5px] text-stone-500 tabular-nums">
              {{ detail.date }} · {{ detail.parcels }} {{ t('retsh.parcelsWord') }} ·
              {{ detail.actual }}/{{ detail.ordered }} {{ t('retsh.unitsWord') }}
              <span v-if="detail.missing" class="text-rose-600 font-semibold"> · {{ detail.missing }} {{ t('retsh.missingWord') }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <button class="h-8 px-2.5 rounded-lg text-[12px] font-semibold text-stone-700 bg-stone-100 hover:bg-stone-200 inline-flex items-center gap-1.5"
                    @click="doPrint(detail.batch)">
              <Icon name="printer" :size="13" />{{ t('retsh.print') }}
            </button>
            <button :title="t('common.close')" class="text-stone-400 hover:text-stone-700" @click="detail = null">
              <Icon name="x" :size="18" />
            </button>
          </div>
        </header>
        <div class="overflow-y-auto divide-y divide-stone-100">
          <div v-for="p in detailRows" :key="p.awb + p.dn" class="px-5 py-2.5"
               :class="p.missing ? 'bg-rose-50/50' : ''">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono text-[12px] font-semibold text-stone-900">{{ p.awb || p.dn || '—' }}</span>
              <span class="text-[11.5px] text-stone-500 truncate" dir="auto">{{ p.customer }}<span v-if="p.city"> · {{ p.city }}</span></span>
              <span class="ms-auto text-[12px] tabular-nums" :class="p.missing ? 'text-rose-600 font-bold' : 'text-stone-500'">
                {{ p.actual }}/{{ p.ordered }}
              </span>
            </div>
            <div v-for="(l, i) in p.lines" :key="i" class="text-[11px] mt-0.5 truncate"
                 :class="l.missing ? 'text-rose-600 font-semibold' : 'text-stone-400'">
              <span class="font-mono">{{ l.sku }}</span> {{ l.name }} — {{ l.actual }}/{{ l.ordered }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { printReturnSheet } from "@/lib/returnSheetPrint";

const { t } = useI18n();
const { warn } = useToast();

const rows = ref([]);
const total = ref(0);
const kpis = ref(null);
const loading = ref(true);
const q = ref("");
const days = ref(30);
const onlyShort = ref(false);
const detail = ref(null);
const printing = ref("");

const fmt = (v) => (Number(v) || 0).toLocaleString("en-US");

// Shortages first inside a batch — the reason anyone opens one.
const detailRows = computed(() => {
  const r = [...(detail.value?.rows || [])];
  r.sort((a, b) => Number(b.missing || 0) - Number(a.missing || 0));
  return r;
});

async function load(offset = 0) {
  loading.value = true;
  try {
    const live = await api("returns.shipments", {
      days: days.value, q: q.value.trim(), limit: 30, offset,
      only_short: onlyShort.value ? 1 : 0,
    });
    rows.value = offset ? [...rows.value, ...(live.rows || [])] : (live.rows || []);
    total.value = live.total || 0;
    kpis.value = live.kpis || null;
  } catch (e) {
    warn(t("retsh.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
const reload = () => load(0);
const more = () => load(rows.value.length);

async function open(r) {
  try {
    detail.value = await api("returns.return_sheet", { name: r.no });
  } catch (e) {
    warn(t("retsh.loadFail"), String(e.message || e));
  }
}

async function doPrint(name) {
  printing.value = name;
  try {
    const sheet = await api("returns.return_sheet", { name });
    if (!printReturnSheet(sheet)) warn(t("retsh.printBlocked"), "");
  } catch (e) {
    warn(t("retsh.printFail"), String(e.message || e));
  } finally {
    printing.value = "";
  }
}

onMounted(reload);
</script>
