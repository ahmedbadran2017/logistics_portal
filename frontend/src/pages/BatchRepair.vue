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

    <!-- ═══ Returns marked received but never credited to stock ═══ -->
    <div v-if="rr" class="space-y-4 pt-2">
      <div class="flex items-center gap-2">
        <Icon name="package-check" :size="15" class="text-amber-600" />
        <h2 class="text-[15px] font-bold text-stone-900">{{ t('brepair.rrTitle') }}</h2>
      </div>
      <p class="text-[12.5px] text-stone-500 -mt-2">{{ t('brepair.rrHint') }}</p>

      <div v-if="!rr.docs.length" class="bg-white rounded-xl ring-1 ring-emerald-200/70 p-6 text-center">
        <Icon name="check-circle" :size="20" class="mx-auto mb-1.5 text-emerald-500" />
        <div class="text-[13px] font-semibold text-stone-800">{{ t('brepair.rrClean') }}</div>
      </div>
      <template v-else>
        <div class="grid grid-cols-3 gap-3">
          <div class="bg-white rounded-xl ring-1 ring-amber-200/70 p-4">
            <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.rrDocs') }}</div>
            <div class="text-[24px] font-extrabold tabular-nums text-amber-600 mt-1">{{ fmt(rr.totalDocs) }}</div>
          </div>
          <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.rrUnits') }}</div>
            <div class="text-[24px] font-extrabold tabular-nums text-stone-900 mt-1">{{ fmt(rr.totalUnits) }}</div>
          </div>
          <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.rrValue') }}</div>
            <div class="text-[24px] font-extrabold tabular-nums text-stone-900 mt-1">{{ fmt(rr.totalValue) }}</div>
          </div>
        </div>

        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 divide-y divide-stone-100">
          <div v-for="doc in rr.docs" :key="doc.ret" class="px-4 py-3">
            <div class="flex items-center gap-3 flex-wrap">
              <span class="font-mono text-[12.5px] font-semibold text-stone-900">{{ doc.ret }}</span>
              <span class="text-[11.5px] text-stone-400 tabular-nums">{{ doc.date }}</span>
              <span class="text-[11.5px] text-stone-500 tabular-nums">
                {{ t('brepair.rrLine').replace('{r}', String(doc.received)).replace('{c}', String(doc.credited)) }}
              </span>
              <span class="text-[11.5px] font-bold text-amber-700 bg-amber-50 ring-1 ring-amber-200/70 rounded-full px-2 py-0.5 tabular-nums">
                {{ t('brepair.rrMissing').replace('{n}', String(doc.units)) }}
              </span>
              <div class="ms-auto flex items-center gap-2">
                <button v-for="n in [1, 20, 200]" :key="n"
                        class="h-8 px-2.5 rounded-lg text-[11.5px] font-semibold tabular-nums ring-1 transition-colors"
                        :class="rrLimit === n ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]' : 'text-stone-700 bg-white ring-stone-200 hover:bg-stone-50'"
                        @click="rrLimit = n">{{ n }}</button>
                <button class="h-8 px-3.5 rounded-lg text-[12px] font-semibold transition-colors disabled:opacity-50"
                        :class="rrArmed === doc.ret ? 'text-white bg-rose-600' : 'text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]'"
                        :disabled="rrBusy" @click="doCredit(doc)">
                  {{ rrBusy === doc.ret ? t('brepair.releasing') : rrArmed === doc.ret ? t('brepair.rrSure').replace('{n}', String(rrLimit)) : t('brepair.rrBtn') }}
                </button>
              </div>
            </div>
            <div v-if="(doc.sample || []).length" class="flex flex-wrap gap-1.5 mt-2">
              <span v-for="sm in doc.sample" :key="sm.idx" class="text-[10.5px] font-mono text-stone-500 bg-stone-50 ring-1 ring-stone-200/70 rounded px-1.5 py-0.5">
                #{{ sm.idx }} · {{ sm.item }} · {{ sm.qty }}u
              </span>
              <span v-if="doc.missing > doc.sample.length" class="text-[10.5px] text-stone-400">+{{ doc.missing - doc.sample.length }}</span>
            </div>
            <div v-if="rrRes[doc.ret]" class="mt-2 text-[11.5px] font-semibold text-emerald-700">
              {{ t('brepair.rrDone').replace('{n}', String(rrRes[doc.ret].created)).replace('{u}', String(rrRes[doc.ret].units)).replace('{m}', String(rrRes[doc.ret].remaining)) }}
              <span v-if="rrRes[doc.ret].failed" class="text-rose-600 ms-1">{{ t('brepair.resultFailed').replace('{n}', String(rrRes[doc.ret].failed)) }}</span>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ═══ The SRE sibling: reservations still held by sales-cancelled orders ═══ -->
    <div v-if="sre" class="space-y-4 pt-2">
      <div class="flex items-center gap-2">
        <Icon name="shield-alert" :size="15" class="text-rose-500" />
        <h2 class="text-[15px] font-bold text-stone-900">{{ t('brepair.sreTitle') }}</h2>
      </div>
      <p class="text-[12.5px] text-stone-500 -mt-2">{{ t('brepair.sreHint') }}</p>

      <div v-if="!sre.staleRes" class="bg-white rounded-xl ring-1 ring-emerald-200/70 p-6 text-center">
        <Icon name="check-circle" :size="20" class="mx-auto mb-1.5 text-emerald-500" />
        <div class="text-[13px] font-semibold text-stone-800">{{ t('brepair.sreClean') }}</div>
      </div>
      <template v-else>
        <div class="grid grid-cols-3 gap-3">
          <div class="bg-white rounded-xl ring-1 ring-rose-200/70 p-4">
            <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.sreCount') }}</div>
            <div class="text-[24px] font-extrabold tabular-nums text-rose-600 mt-1">{{ fmt(sre.staleRes) }}</div>
          </div>
          <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.sreUnits') }}</div>
            <div class="text-[24px] font-extrabold tabular-nums text-stone-900 mt-1">{{ fmt(sre.staleResUnits) }}</div>
          </div>
          <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('brepair.sreItems') }}</div>
            <div class="text-[24px] font-extrabold tabular-nums text-stone-900 mt-1">{{ fmt(sre.staleResItems) }}</div>
          </div>
        </div>
        <div v-if="(sre.sample || []).length" class="bg-white rounded-xl ring-1 ring-stone-200/70 divide-y divide-stone-100">
          <div v-for="r in sre.sample" :key="r.order + r.item" class="px-4 py-2 flex items-center gap-3 text-[12px] tabular-nums">
            <span class="font-mono text-stone-800 truncate">{{ r.item }}</span>
            <span class="font-mono text-stone-400">{{ r.order }}</span>
            <span class="ms-auto text-stone-700"><b>{{ r.qty }}</b> u</span>
            <span class="text-stone-400">{{ r.since }}</span>
          </div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 flex items-center gap-2 flex-wrap">
          <span class="text-[12px] text-stone-500">{{ t('brepair.limitLabel') }}</span>
          <button v-for="n in [1, 50, 500]" :key="n"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold tabular-nums ring-1 transition-colors"
                  :class="sreLimit === n ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]' : 'text-stone-700 bg-white ring-stone-200 hover:bg-stone-50'"
                  @click="sreLimit = n">{{ n }}</button>
          <button
            class="h-9 px-4 rounded-lg text-[13px] font-semibold transition-colors disabled:opacity-50 ms-auto"
            :class="sreArmed ? 'text-white bg-rose-600' : 'text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]'"
            :disabled="sreBusy" @click="doSreRelease">
            <span class="inline-flex items-center gap-1.5">
              <Icon name="unlock" :size="14" />
              {{ sreBusy ? t('brepair.releasing') : sreArmed ? t('brepair.releaseSure').replace('{n}', String(sreLimit)) : t('brepair.releaseBtn').replace('{n}', String(sreLimit)) }}
            </span>
          </button>
        </div>
        <div v-if="sreRes" class="bg-white rounded-xl ring-1 ring-emerald-200/70 px-4 py-2.5 flex items-center gap-2 flex-wrap">
          <Icon name="check-circle" :size="14" class="text-emerald-600" />
          <span class="text-[12px] font-semibold text-stone-900">
            {{ t('brepair.resultLine').replace('{b}', fmt(sreRes.released)).replace('{u}', fmt(sreRes.unitsFreed)) }}
          </span>
          <span v-if="sreRes.failed" class="text-[11.5px] text-rose-600 font-medium">{{ t('brepair.resultFailed').replace('{n}', String(sreRes.failed)) }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost, liveOr } from "@/lib/resource";
// eslint-disable-next-line no-unused-vars — SRE repair state

import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const sc = ref(null);
const res = ref(null);
const sre = ref(null);
const rr = ref(null);
const rrLimit = ref(1);
const rrArmed = ref("");
const rrBusy = ref("");
const rrRes = ref({});
let rrArmT = null;
async function doCredit(doc) {
  if (rrArmed.value !== doc.ret) {
    rrArmed.value = doc.ret;
    clearTimeout(rrArmT);
    rrArmT = setTimeout(() => { rrArmed.value = ""; }, 4000);
    return;
  }
  rrArmed.value = "";
  rrBusy.value = doc.ret;
  try {
    const r = await apiPost("returns_repair.complete", { ret: doc.ret, limit: rrLimit.value });
    rrRes.value = { ...rrRes.value, [doc.ret]: r };
    success(t("brepair.rrDoneToast"),
      t("brepair.rrDone").replace("{n}", String(r.created)).replace("{u}", String(r.units)).replace("{m}", String(r.remaining)));
    rr.value = await api("returns_repair.scan");
  } catch (e) {
    warn(t("brepair.releaseFail"), String(e.message || e));
  } finally {
    rrBusy.value = "";
  }
}
const sreLimit = ref(1);
const sreArmed = ref(false);
const sreBusy = ref(false);
const sreRes = ref(null);
let sreArmT = null;
async function doSreRelease() {
  if (!sreArmed.value) {
    sreArmed.value = true;
    clearTimeout(sreArmT);
    sreArmT = setTimeout(() => { sreArmed.value = false; }, 4000);
    return;
  }
  sreArmed.value = false;
  sreBusy.value = true;
  try {
    const r = await apiPost("batch_repair.sre_release", { limit: sreLimit.value });
    sreRes.value = r;
    success(t("brepair.releaseDone"),
      t("brepair.resultLine").replace("{b}", fmt(r.released)).replace("{u}", fmt(r.unitsFreed)));
    sre.value = await api("batch_repair.sre_scan");
  } catch (e) {
    warn(t("brepair.releaseFail"), String(e.message || e));
  } finally {
    sreBusy.value = false;
  }
}
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
  sre.value = await liveOr(null, () => api("batch_repair.sre_scan"));
  rr.value = await liveOr(null, () => api("returns_repair.scan"));
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
