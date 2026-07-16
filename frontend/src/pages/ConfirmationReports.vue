<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1280px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cfr.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cfr.intro') }}</p>
      </div>
      <DateRange v-model:days="days" v-model:frm="frm" v-model:to="to" @change="load" />
    </header>

    <div v-if="loading" class="space-y-3">
      <div class="h-[92px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="h-[280px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="denied" class="bg-white rounded-2xl ring-1 ring-amber-200/70 p-8 text-center">
      <Icon name="shield-alert" :size="24" class="mx-auto mb-2 text-amber-500" />
      <div class="text-[13px] text-stone-600">{{ t('cfr.denied') }}</div>
    </div>

    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[460px] mx-auto break-words">{{ loadError }}</div>
    </div>

    <template v-else-if="d">
      <!-- The money. Confirmed is a promise; collected is the fact. Measured on
           the live data, ~42% of confirmed value never arrives. -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="rp-kpi">
          <span class="rp-kpi-l"><Icon name="check-circle" :size="11" class="inline -mt-px me-1 text-emerald-500" />{{ t('cfr.kConfirmed') }}</span>
          <span class="rp-kpi-n">{{ fmtMAD(tot.confirmedValue) }}</span>
          <span class="rp-kpi-s">{{ tot.confirm }} {{ t('cfr.kOrders') }}</span>
        </div>
        <div class="rp-kpi rp-kpi-hero">
          <span class="rp-kpi-l"><Icon name="wallet" :size="11" class="inline -mt-px me-1" />{{ t('cfr.kCollected') }}</span>
          <span class="rp-kpi-n">{{ fmtMAD(tot.collected) }}</span>
          <span class="rp-kpi-s">{{ collectedPct }}% {{ t('cfr.kOf') }}</span>
        </div>
        <div class="rp-kpi">
          <span class="rp-kpi-l"><Icon name="alert-triangle" :size="11" class="inline -mt-px me-1 text-rose-500" />{{ t('cfr.kLeak') }}</span>
          <span class="rp-kpi-n text-rose-600">{{ fmtMAD(tot.confirmedValue - tot.collected) }}</span>
          <span class="rp-kpi-s">{{ t('cfr.kLeakHint') }}</span>
        </div>
        <div class="rp-kpi">
          <span class="rp-kpi-l"><Icon name="package-check" :size="11" class="inline -mt-px me-1 text-sky-500" />{{ t('cfr.kStick') }}</span>
          <span class="rp-kpi-n">{{ tot.stick }}<span class="text-[14px] text-stone-400">%</span></span>
          <span class="rp-kpi-s">{{ tot.delivered }} / {{ tot.shipped }} {{ t('cfr.kParcels') }}</span>
        </div>
      </div>

      <!-- What the automation already did before a human ever dialled. -->
      <div v-if="d.ladder && d.ladder.n" class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3 flex items-center gap-4 flex-wrap">
        <span class="text-[12px] font-semibold text-stone-900 whitespace-nowrap">
          <Icon name="send" :size="13" class="inline -mt-px me-1.5 text-sky-500" />{{ t('cfr.ladder') }}
        </span>
        <div class="flex-1 min-w-[220px] flex items-center gap-1">
          <div class="rp-bar bg-stone-200" :style="{ flex: Math.max(1, d.ladder.n - d.ladder.r1) }" :title="t('cfr.ladderNone')" />
          <div class="rp-bar bg-sky-300" :style="{ flex: Math.max(1, d.ladder.r1 - d.ladder.r2) }" :title="t('cfr.ladder1')" />
          <div class="rp-bar bg-sky-600" :style="{ flex: Math.max(1, d.ladder.r2) }" :title="t('cfr.ladder2')" />
        </div>
        <span class="text-[11.5px] text-stone-500 tabular-nums whitespace-nowrap">
          {{ d.ladder.r1 }} · {{ d.ladder.r2 }} / {{ d.ladder.n }}
        </span>
      </div>

      <!-- The leaderboard -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="users" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('cfr.agentsTitle') }}</span>
          <span class="text-[11px] text-stone-400">{{ t('cfr.cohortHint') }}</span>
          <div class="ms-auto flex items-center gap-1">
            <button v-for="so in SORTS" :key="so.k" class="rp-sort" :class="sort === so.k ? 'rp-sort-on' : ''"
                    @click="sort = so.k">{{ t(so.l) }}</button>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[980px] text-[12.5px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('cfr.thAgent') }}</th>
                <th class="text-end px-2 py-2.5">{{ t('cfr.thTotal') }}</th>
                <th class="text-end px-2 py-2.5 text-emerald-600">{{ t('cf.actConfirm') }}</th>
                <th class="text-end px-2 py-2.5 text-rose-500">{{ t('cf.actCancel') }}</th>
                <th class="text-end px-2 py-2.5">{{ t('cf.tabDna') }}</th>
                <th class="text-end px-2 py-2.5">{{ t('cf.tabFollowup') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('cfr.thRate') }}</th>
                <th class="text-end px-2 py-2.5">{{ t('cfr.thResp') }}</th>
                <th class="text-end px-2 py-2.5">{{ t('cfr.thAttempts') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('cfr.thConfirmedValue') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('cfr.kCollected') }}</th>
                <th class="text-end px-4 py-2.5">{{ t('cfr.thStick') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="(a, i) in sorted" :key="a.user" class="hover:bg-stone-50">
                <td class="px-4 py-2.5">
                  <span class="inline-flex items-center gap-2">
                    <span class="w-5 h-5 rounded-full text-[10px] font-bold inline-flex items-center justify-center"
                          :class="i === 0 ? 'bg-amber-100 text-amber-700' : 'bg-stone-100 text-stone-500'">{{ i + 1 }}</span>
                    <span class="font-medium text-stone-900">{{ a.agent }}</span>
                    <Icon v-if="a.bulk" name="layers" :size="11" class="text-stone-300" :title="t('cfr.thBulk')" />
                  </span>
                </td>
                <td class="px-2 py-2.5 text-end tabular-nums font-semibold text-stone-900">{{ a.total }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums text-emerald-600 font-semibold">{{ a.confirm || '—' }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums text-rose-500">{{ a.cancel || '—' }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums text-stone-500">{{ a.dna || '—' }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums text-stone-500">{{ a.followup || '—' }}</td>
                <td class="px-3 py-2.5 text-end">
                  <span v-if="a.confirmRate !== null" class="inline-flex items-center justify-end gap-1.5">
                    <span class="w-[42px] h-1.5 rounded-full bg-stone-100 overflow-hidden">
                      <span class="block h-full rounded-full"
                            :class="rateColor(a.confirmRate, 80, 60, 'bg')"
                            :style="{ width: a.confirmRate + '%' }" />
                    </span>
                    <b class="tabular-nums w-[38px] text-end" :class="rateColor(a.confirmRate, 80, 60, 'text')">{{ a.confirmRate }}%</b>
                  </span>
                  <span v-else class="text-stone-300">—</span>
                </td>
                <td class="px-2 py-2.5 text-end tabular-nums text-stone-600">{{ a.respH !== null ? a.respH + t('cf.hrs') : '—' }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums text-stone-600">{{ a.avgAttempts || '—' }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-stone-500">{{ fmtMAD(a.confirmedValue) }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums font-bold text-stone-900">{{ fmtMAD(a.collected) }}</td>
                <td class="px-4 py-2.5 text-end">
                  <b v-if="a.stickRate !== null" class="tabular-nums" :class="rateColor(a.stickRate, 75, 65, 'text')">{{ a.stickRate }}%</b>
                  <span v-else class="text-stone-300">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!d.agents.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('cfr.noData') }}</div>
        <div v-else class="px-4 py-2 border-t border-stone-100 text-[10.5px] text-stone-400">{{ t('cfr.stickHint') }}</div>
      </div>

      <div class="grid lg:grid-cols-2 gap-3">
        <!-- Why orders die — the company's own vocabulary, off the Select field -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <Icon name="circle-x" :size="14" class="text-stone-400" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cfr.reasonsTitle') }}</span>
            <span class="text-[11px] text-stone-400 ms-auto tabular-nums">{{ reasonTotal }}</span>
          </div>
          <div class="p-3 space-y-1.5 max-h-[340px] overflow-y-auto">
            <div v-for="r in d.reasons" :key="r.reason" class="flex items-center gap-2.5">
              <span class="text-[11.5px] text-stone-600 w-[150px] shrink-0 truncate" :title="r.reason">{{ r.reason }}</span>
              <div class="flex-1 h-4 rounded-md bg-stone-50 overflow-hidden">
                <div class="h-full rounded-md bg-gradient-to-r from-rose-300 to-rose-500 transition-all duration-700"
                     :style="{ width: reasonPct(r.n) + '%' }" />
              </div>
              <span class="text-[11.5px] font-bold text-stone-800 tabular-nums w-[46px] text-end">{{ r.n }}</span>
            </div>
            <div v-if="!d.reasons.length" class="text-center text-[12px] text-stone-400 py-6">—</div>
          </div>
        </section>

        <!-- Day by day, and the hour the work actually happens -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <Icon name="trending-up" :size="14" class="text-stone-400" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cfr.funnelTitle') }}</span>
          </div>
          <div class="p-3">
            <div class="flex items-end gap-1 h-[120px]">
              <div v-for="f in d.funnel" :key="f.date" class="flex-1 flex flex-col justify-end gap-[2px]"
                   :title="`${f.date}: ${f.confirm} / ${f.cancel} / ${f.dna}`">
                <div class="rounded-t-[2px] bg-emerald-500 transition-all duration-500" :style="{ height: fh(f.confirm) }" />
                <div class="bg-rose-400 transition-all duration-500" :style="{ height: fh(f.cancel) }" />
                <div class="rounded-b-[2px] bg-amber-300 transition-all duration-500" :style="{ height: fh(f.dna) }" />
              </div>
              <div v-if="!d.funnel.length" class="w-full text-center text-[12px] text-stone-400 py-10">—</div>
            </div>
            <div v-if="d.funnel.length" class="flex justify-between mt-1.5 text-[10px] text-stone-400 tabular-nums">
              <span>{{ d.funnel[0].date.slice(5) }}</span>
              <span>{{ d.funnel[d.funnel.length - 1].date.slice(5) }}</span>
            </div>
            <div class="flex items-center gap-3 mt-2 text-[10.5px] text-stone-500">
              <span class="inline-flex items-center gap-1"><i class="w-2 h-2 rounded-full bg-emerald-500" />{{ t('cf.actConfirm') }}</span>
              <span class="inline-flex items-center gap-1"><i class="w-2 h-2 rounded-full bg-rose-400" />{{ t('cf.actCancel') }}</span>
              <span class="inline-flex items-center gap-1"><i class="w-2 h-2 rounded-full bg-amber-300" />{{ t('cf.tabDna') }}</span>
            </div>

            <div v-if="d.hours && d.hours.length" class="mt-4 pt-3 border-t border-stone-100">
              <div class="text-[11px] font-semibold text-stone-500 mb-2">{{ t('cfr.hoursTitle') }}</div>
              <div class="flex items-end gap-[2px] h-[52px]">
                <div v-for="h in d.hours" :key="h.h" class="flex-1 rounded-t-[2px] transition-all duration-500"
                     :class="h.n ? 'bg-[var(--accent-400)]' : 'bg-stone-100'"
                     :style="{ height: hh(h.n) }" :title="`${h.h}:00 — ${h.n}`" />
              </div>
              <div class="flex justify-between mt-1 text-[10px] text-stone-400 tabular-nums">
                <span>{{ String(d.hours[0].h).padStart(2, '0') }}:00</span>
                <span>{{ String(d.hours[d.hours.length - 1].h).padStart(2, '0') }}:00</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import DateRange from "@/components/ui/DateRange.vue";
import { api } from "@/lib/resource";
import { fmtMAD } from "@/lib/handoffData";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();

const SORTS = [
  { k: "total", l: "cfr.thTotal" },
  { k: "collected", l: "cfr.kCollected" },
  { k: "stickRate", l: "cfr.thStick" },
  { k: "confirmRate", l: "cfr.thRate" },
];

const days = ref(30);
const frm = ref("");
const to = ref("");
const sort = ref("total");
const d = ref(null);
const loading = ref(true);
const denied = ref(false);
const loadError = ref("");

const sorted = computed(() => {
  const rows = [...(d.value?.agents || [])];
  return rows.sort((a, b) => (b[sort.value] ?? -1) - (a[sort.value] ?? -1));
});

// Section totals — the headline the manager reads first.
const tot = computed(() => {
  const a = d.value?.agents || [];
  const s = (k) => a.reduce((x, r) => x + (r[k] || 0), 0);
  const delivered = s("delivered");
  const shipped = delivered + s("failedParcels");
  return {
    confirm: s("confirm"), confirmedValue: s("confirmedValue"),
    collected: s("collected"), delivered, shipped,
    stick: shipped ? Math.round((delivered * 100) / shipped) : 0,
  };
});
const collectedPct = computed(() =>
  tot.value.confirmedValue ? Math.round((tot.value.collected * 100) / tot.value.confirmedValue) : 0);

// Written out in full on purpose: Tailwind's JIT scans source text, so a
// class built by interpolation (`bg-${c}`) is never generated and renders
// colourless.
function rateColor(v, good, ok, kind) {
  if (kind === "bg") {
    return v >= good ? "bg-emerald-500" : v >= ok ? "bg-amber-500" : "bg-rose-500";
  }
  return v >= good ? "text-emerald-600" : v >= ok ? "text-amber-600" : "text-rose-600";
}

const reasonTotal = computed(() => (d.value?.reasons || []).reduce((s, r) => s + r.n, 0));
function reasonPct(n) {
  const max = Math.max(1, ...(d.value?.reasons || []).map((r) => r.n));
  return Math.round((n / max) * 100);
}
const funnelMax = computed(() =>
  Math.max(1, ...(d.value?.funnel || []).map((f) => f.confirm + f.cancel + f.dna)));
function fh(n) { return n ? Math.max(2, Math.round((n / funnelMax.value) * 120)) + "px" : "0px"; }
const hourMax = computed(() => Math.max(1, ...(d.value?.hours || []).map((h) => h.n)));
function hh(n) { return n ? Math.max(3, Math.round((n / hourMax.value) * 52)) + "px" : "2px"; }

async function load() {
  loading.value = true;
  denied.value = false;
  loadError.value = "";
  try {
    const res = await api("confirmation.report", {
      days: days.value, frm: frm.value || undefined, to: to.value || undefined,
    });
    // An older backend answers with the previous shape — say so rather than
    // rendering a half-empty page.
    if (!res || !Array.isArray(res.agents)) {
      loadError.value = t("px.set.deployHint");
      return;
    }
    d.value = res;
  } catch (e) {
    const msg = String(e.message || e);
    if (/section admin|PermissionError|403/i.test(msg)) denied.value = true;
    else loadError.value = msg;
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
.rp-kpi {
  display: flex; flex-direction: column; gap: 3px;
  background: white; border-radius: 14px; padding: 13px 15px;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8);
}
.rp-kpi-hero {
  background: linear-gradient(135deg, var(--accent-50), #fff);
  box-shadow: inset 0 0 0 1px var(--accent-200);
}
.rp-kpi-l { font-size: 10.5px; font-weight: 700; color: rgb(120 113 108); text-transform: uppercase; letter-spacing: .04em; }
.rp-kpi-n { font-size: 21px; font-weight: 800; color: rgb(28 25 23); font-variant-numeric: tabular-nums; line-height: 1.1; }
.rp-kpi-s { font-size: 10.5px; color: rgb(168 162 158); font-variant-numeric: tabular-nums; }
.rp-bar { height: 8px; border-radius: 3px; transition: flex .6s ease; }
.rp-sort {
  height: 24px; padding: 0 8px; border-radius: 7px;
  font-size: 10.5px; font-weight: 700; color: rgb(120 113 108);
  transition: all .12s ease;
}
.rp-sort:hover { background: rgb(245 245 244); }
.rp-sort-on { background: rgb(28 25 23); color: white; }
</style>
