<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1280px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cfd.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cfd.intro') }}</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <!-- the same screen answers "how is the section" and "how am I" -->
        <div v-if="d?.canSeeAll" class="cfd-seg">
          <button class="cfd-seg-b" :class="!mine ? 'cfd-seg-on' : ''" @click="mine = 0; load()">{{ t('cfd.all') }}</button>
          <button class="cfd-seg-b" :class="mine ? 'cfd-seg-on' : ''" @click="mine = 1; load()">{{ t('cfd.mine') }}</button>
        </div>
        <DateRange v-model:days="days" v-model:frm="frm" v-model:to="to" @change="load" />
      </div>
      <!-- The range only reaches Intake. Queue / aging / segments / cities /
           oldest all read the CURRENT state -- there is no snapshot history to
           replay them from -- so the picker must not appear to control them. -->
      <p class="text-[11px] text-stone-400 mt-1.5 max-w-[640px] leading-relaxed">{{ t('cfd.rangeNote') }}</p>
    </header>

    <div v-if="loading" class="space-y-3">
      <div class="h-[96px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="h-[240px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[460px] mx-auto break-words">{{ loadError }}</div>
    </div>

    <template v-else-if="d">
      <!-- the queue right now -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <RouterLink :to="{ name: 'Confirmation' }" class="cfd-kpi">
          <span class="cfd-kpi-l">{{ t('cfd.kWaiting') }}</span>
          <span class="cfd-kpi-n">{{ d.queueTotal }}</span>
          <span class="cfd-kpi-s">{{ fmtMAD(d.queueValue) }} MAD</span>
        </RouterLink>
        <div class="cfd-kpi" :class="d.sla.late ? 'cfd-kpi-bad' : ''">
          <span class="cfd-kpi-l">{{ t('cfd.kLate') }}</span>
          <span class="cfd-kpi-n" :class="d.sla.late ? 'text-rose-600' : 'text-emerald-600'">{{ d.sla.late }}</span>
          <span class="cfd-kpi-s">{{ t('cfd.kLateHint', String(d.slaHours)).replace('{h}', d.slaHours) }}</span>
        </div>
        <div class="cfd-kpi">
          <span class="cfd-kpi-l">{{ t('cfd.kOld') }}</span>
          <span class="cfd-kpi-n" :class="oldPct > 50 ? 'text-amber-600' : 'text-stone-900'">{{ oldPct }}<span class="text-[14px] text-stone-400">%</span></span>
          <span class="cfd-kpi-s">{{ t('cfd.kOldHint') }}</span>
        </div>
        <RouterLink :to="{ name: 'Confirmation', query: { tab: 'monitor' } }" class="cfd-kpi"
                    :class="riskN ? 'cfd-kpi-bad' : ''">
          <span class="cfd-kpi-l">{{ t('cfd.kRisk') }}</span>
          <span class="cfd-kpi-n" :class="riskN ? 'text-rose-600' : 'text-stone-900'">{{ riskN }}</span>
          <span class="cfd-kpi-s">{{ fmtMAD(riskValue) }} MAD {{ t('cfd.kRiskHint') }}</span>
        </RouterLink>
      </div>

      <!-- Rows the sums refused. Never a silent drop. -->
      <div v-if="d.absurd" class="flex items-start gap-2.5 bg-amber-50 ring-1 ring-amber-200/70 rounded-xl px-4 py-2.5">
        <Icon name="alert-triangle" :size="15" class="text-amber-500 shrink-0 mt-0.5" />
        <span class="text-[11.5px] text-amber-800">
          {{ t('cfd.absurd', String(d.absurd)).replace('{n}', d.absurd).replace('{max}', fmtMAD(d.saneMax)) }}
        </span>
      </div>

      <div class="grid lg:grid-cols-2 gap-3">
        <!-- WHO is waiting. Nothing else in the company can answer this. -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <Icon name="users" :size="14" class="text-stone-400" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cfd.segTitle') }}</span>
            <span class="cfd-now">{{ t('cfd.liveNow') }}</span>
            <span class="text-[11px] text-stone-400 ms-auto">{{ t('cfd.segSample', String(d.segSampled)).replace('{n}', d.segSampled) }}</span>
          </div>
          <div class="p-3.5 space-y-2">
            <RouterLink v-for="sg in segRows" :key="sg.k" :to="{ name: 'Confirmation' }"
                        class="flex items-center gap-2.5 group">
              <span class="seg-chip shrink-0 w-[138px] justify-center whitespace-nowrap overflow-hidden"
                    :class="'seg-' + sg.k" :title="t('seg.explain_' + sg.k)">{{ t('seg.' + sg.k) }}</span>
              <div class="flex-1 h-5 rounded-md bg-stone-50 overflow-hidden">
                <div class="h-full rounded-md transition-all duration-700" :class="segBar(sg.k)"
                     :style="{ width: segPct(sg.n) + '%' }" />
              </div>
              <span class="text-[12px] font-bold text-stone-900 tabular-nums w-[42px] text-end">{{ sg.n }}</span>
              <span class="text-[11px] text-stone-400 tabular-nums w-[74px] text-end">{{ fmtMAD(sg.value) }}</span>
            </RouterLink>
            <p class="text-[10.5px] text-stone-400 pt-1.5">{{ t('cfd.segHint') }}</p>
          </div>
        </section>

        <!-- how old the pile is -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <Icon name="clock" :size="14" class="text-stone-400" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cfd.agingTitle') }}</span>
            <span class="cfd-now">{{ t('cfd.liveNow') }}</span>
          </div>
          <div class="p-3.5">
            <div class="flex items-end gap-2 h-[130px]">
              <div v-for="a in d.aging" :key="a.bucket" class="flex-1 flex flex-col justify-end items-center gap-1">
                <span class="text-[11px] font-bold text-stone-800 tabular-nums">{{ a.n || '' }}</span>
                <div class="w-full rounded-t-md transition-all duration-700"
                     :class="agingColor(a.bucket)" :style="{ height: agingH(a.n) }" />
                <span class="text-[10px] text-stone-400 tabular-nums">{{ a.bucket }}</span>
              </div>
            </div>
            <div class="flex flex-wrap gap-x-4 gap-y-1 mt-3 pt-2.5 border-t border-stone-100 text-[11px] text-stone-500 tabular-nums">
              <span v-for="a in d.aging" :key="a.bucket">
                {{ a.bucket }} · <b class="text-stone-700">{{ fmtMAD(a.value) }}</b>
              </span>
            </div>
          </div>
        </section>
      </div>

      <div class="grid lg:grid-cols-[1fr_300px] gap-3">
        <!-- the oldest orders still waiting -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <Icon name="alert-circle" :size="14" class="text-stone-400" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cfd.oldestTitle') }}</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[620px] text-[12.5px]">
              <thead>
                <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                  <th class="text-start px-4 py-2">{{ t('cfd.thOrder') }}</th>
                  <th class="text-start px-2 py-2">{{ t('cfd.thCustomer') }}</th>
                  <th class="text-start px-2 py-2">{{ t('cfd.thCity') }}</th>
                  <th class="text-start px-2 py-2">{{ t('cfd.thStatus') }}</th>
                  <th class="text-end px-2 py-2">{{ t('cfd.thAge') }}</th>
                  <th class="text-end px-4 py-2">{{ t('cfd.thValue') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-stone-50">
                <tr v-for="o in d.topPending" :key="o.order" class="hover:bg-stone-50">
                  <td class="px-4 py-2 font-mono text-[11.5px] text-stone-700">{{ o.order }}</td>
                  <td class="px-2 py-2 text-stone-800 truncate max-w-[150px]">{{ o.customer || '—' }}</td>
                  <td class="px-2 py-2 text-stone-500 truncate max-w-[110px]">{{ o.city || '—' }}</td>
                  <td class="px-2 py-2"><span class="cfd-st">{{ o.status }}</span></td>
                  <td class="px-2 py-2 text-end tabular-nums font-semibold"
                      :class="o.ageH > 168 ? 'text-rose-600' : o.ageH > 24 ? 'text-amber-600' : 'text-stone-600'">
                    {{ o.ageH < 48 ? o.ageH + t('cf.hrs') : Math.round(o.ageH / 24) + t('cf.days') }}
                  </td>
                  <td class="px-4 py-2 text-end tabular-nums text-stone-700">{{ fmtMAD(o.total) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!d.topPending.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('cf.empty') }}</div>
        </section>

        <div class="space-y-3">
          <!-- where the queue is -->
          <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
            <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
              <Icon name="map-pin" :size="14" class="text-stone-400" />
              <span class="text-[12px] font-semibold text-stone-900">{{ t('cfd.citiesTitle') }}</span>
            <span class="cfd-now">{{ t('cfd.liveNow') }}</span>
            </div>
            <div class="p-3 space-y-1.5">
              <div v-for="c in d.cities" :key="c.city" class="flex items-center gap-2 text-[11.5px]">
                <span class="text-stone-600 w-[86px] truncate" :title="c.city">{{ c.city }}</span>
                <div class="flex-1 h-3 rounded bg-stone-50 overflow-hidden">
                  <div class="h-full rounded bg-sky-400 transition-all duration-700" :style="{ width: cityPct(c.n) + '%' }" />
                </div>
                <span class="font-bold text-stone-800 tabular-nums w-[36px] text-end">{{ c.n }}</span>
              </div>
              <div v-if="!d.cities.length" class="text-center text-[12px] text-stone-400 py-4">—</div>
            </div>
          </section>

          <!-- what happened to the window's intake -->
          <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
            <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
              <Icon name="layers" :size="14" class="text-stone-400" />
              <span class="text-[12px] font-semibold text-stone-900">{{ t('cfd.intakeTitle') }}</span>
            </div>
            <div class="p-3 space-y-1.5">
              <div v-for="i in d.intake" :key="i.status" class="flex items-center gap-2 text-[11.5px]">
                <span class="text-stone-600 flex-1 truncate">{{ i.status }}</span>
                <span class="font-bold text-stone-800 tabular-nums">{{ i.n }}</span>
                <span class="text-stone-400 tabular-nums w-[38px] text-end">{{ intakePct(i.n) }}%</span>
              </div>
              <div v-if="!d.intake.length" class="text-center text-[12px] text-stone-400 py-4">—</div>
            </div>
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
import { api } from "@/lib/resource";
import { fmtMAD } from "@/lib/handoffData";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();

const SEG_ORDER = ["black", "risk", "watch", "new", "good", "vip"];
const days = ref(30);
const frm = ref("");
const to = ref("");
const mine = ref(0);
const d = ref(null);
const loading = ref(true);
const loadError = ref("");

const segRows = computed(() =>
  SEG_ORDER.filter((k) => d.value?.segMix?.[k])
    .map((k) => ({ k, ...d.value.segMix[k] })));
const segTotal = computed(() => segRows.value.reduce((s, r) => s + r.n, 0));
function segPct(n) {
  const max = Math.max(1, ...segRows.value.map((r) => r.n));
  return Math.round((n / max) * 100);
}
// Written out, not interpolated — Tailwind's JIT only sees literal classes.
function segBar(k) {
  return { black: "bg-rose-500", risk: "bg-orange-400", watch: "bg-amber-400",
           new: "bg-stone-300", good: "bg-emerald-400", vip: "bg-amber-500" }[k]
         || "bg-stone-300";
}
const riskN = computed(() =>
  (d.value?.segMix?.black?.n || 0) + (d.value?.segMix?.risk?.n || 0));
const riskValue = computed(() =>
  (d.value?.segMix?.black?.value || 0) + (d.value?.segMix?.risk?.value || 0));

const oldPct = computed(() => {
  const a = d.value?.aging || [];
  const tot = a.reduce((s, x) => s + x.n, 0);
  if (!tot) return 0;
  const old = a.filter((x) => x.bucket === "3-7d" || x.bucket === "7d+")
               .reduce((s, x) => s + x.n, 0);
  return Math.round((old * 100) / tot);
});
const agingMax = computed(() => Math.max(1, ...(d.value?.aging || []).map((a) => a.n)));
function agingH(n) { return n ? Math.max(4, Math.round((n / agingMax.value) * 100)) + "px" : "2px"; }
function agingColor(b) {
  return { "0-6h": "bg-emerald-400", "6-24h": "bg-emerald-300",
           "1-3d": "bg-amber-300", "3-7d": "bg-orange-400", "7d+": "bg-rose-500" }[b]
         || "bg-stone-300";
}
function cityPct(n) {
  const max = Math.max(1, ...(d.value?.cities || []).map((c) => c.n));
  return Math.round((n / max) * 100);
}
function intakePct(n) {
  const tot = (d.value?.intake || []).reduce((s, i) => s + i.n, 0);
  return tot ? Math.round((n * 100) / tot) : 0;
}

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const res = await api("confirmation.dashboard", {
      days: days.value, frm: frm.value || undefined, to: to.value || undefined,
      mine: mine.value,
    });
    if (!res || !res.queue) { loadError.value = t("px.set.deployHint"); return; }
    d.value = res;
  } catch (e) {
    loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
.cfd-kpi {
  display: flex; flex-direction: column; gap: 3px;
  background: white; border-radius: 14px; padding: 13px 15px;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8);
  transition: transform .15s ease, box-shadow .15s ease;
}
a.cfd-kpi:hover { transform: translateY(-1px); box-shadow: inset 0 0 0 1px rgb(214 211 209), 0 8px 20px -12px rgb(0 0 0 / .15); }
.cfd-kpi-bad { box-shadow: inset 0 0 0 1px rgb(253 164 175); }
.cfd-kpi-l { font-size: 10.5px; font-weight: 700; color: rgb(120 113 108); text-transform: uppercase; letter-spacing: .04em; }
.cfd-kpi-n { font-size: 24px; font-weight: 800; color: rgb(28 25 23); font-variant-numeric: tabular-nums; line-height: 1.1; }
.cfd-kpi-s { font-size: 10.5px; color: rgb(168 162 158); font-variant-numeric: tabular-nums; }
.cfd-seg { display: inline-flex; gap: 2px; padding: 3px; background: rgb(231 229 228 / .55); border-radius: 11px; }
.cfd-seg-b { height: 32px; padding: 0 11px; border-radius: 8px; font-size: 12px; font-weight: 700; color: rgb(120 113 108); transition: all .15s ease; }
.cfd-seg-on { background: white; color: rgb(28 25 23); box-shadow: 0 1px 3px rgb(0 0 0 / .08); }
.cfd-st { font-size: 10.5px; font-weight: 600; color: rgb(87 83 78); background: rgb(245 245 244); border-radius: 999px; padding: 2px 7px; white-space: nowrap; }
</style>
