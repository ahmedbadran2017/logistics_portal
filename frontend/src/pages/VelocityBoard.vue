<template>
  <div class="max-w-[1100px] mx-auto px-4 py-6 space-y-5">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('vel.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('vel.intro') }}</p>
      </div>
      <div class="inline-flex rounded-lg ring-1 ring-stone-200 overflow-hidden text-[12px] font-semibold">
        <button v-for="d in [14, 30]" :key="d" class="h-9 px-3 transition-colors"
                :class="days === d ? 'bg-stone-900 text-white' : 'bg-white text-stone-600 hover:bg-stone-50'"
                @click="days = d; load()">{{ d }}{{ t('vel.dayShort') }}</button>
      </div>
    </header>

    <div v-if="loading" class="space-y-3">
      <div class="h-[92px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="h-[240px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
    </div>

    <template v-else-if="d">
      <!-- KPI band -->
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
        <div class="vb-kpi" :class="paceClass.ring">
          <span class="vb-l">{{ t('vel.pace') }}</span>
          <span class="vb-n" :class="paceClass.text">{{ d.kpis.pacePct }}<span class="text-[14px] text-stone-400">%</span></span>
          <span class="vb-s">{{ t('vel.paceHint') }}</span>
        </div>
        <div class="vb-kpi">
          <span class="vb-l">{{ t('vel.in7') }}</span>
          <span class="vb-n">{{ num(d.kpis.in7) }}</span>
          <span class="vb-s">{{ t('vel.demand') }}</span>
        </div>
        <div class="vb-kpi">
          <span class="vb-l">{{ t('vel.out7') }}</span>
          <span class="vb-n text-emerald-600">{{ num(d.kpis.out7) }}</span>
          <span class="vb-s">{{ t('vel.labeled') }}</span>
        </div>
        <div class="vb-kpi" :class="d.kpis.backlog > 400 ? 'ring-2 ring-amber-300' : ''">
          <span class="vb-l">{{ t('vel.backlog') }}</span>
          <span class="vb-n" :class="d.kpis.backlog > 400 ? 'text-amber-600' : 'text-stone-900'">{{ num(d.kpis.backlog) }}</span>
          <span class="vb-s">{{ t('vel.avgAge') }} {{ Math.round(d.kpis.backlogAgeH / 24) }}{{ t('vel.dayShort') }}</span>
        </div>
        <div class="vb-kpi">
          <span class="vb-l">{{ t('vel.cycle') }}</span>
          <span class="vb-n">{{ d.kpis.cycleH }}<span class="text-[14px] text-stone-400">h</span></span>
          <span class="vb-s">{{ t('vel.cycleHint') }}</span>
        </div>
      </div>

      <!-- In vs Out per day -->
      <section class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-3 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="trending-up" :size="15" class="text-stone-400" />
          <span class="text-[13px] font-bold text-stone-900">{{ t('vel.chartTitle') }}</span>
          <div class="ms-auto flex items-center gap-3 text-[11px]">
            <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-stone-300" />{{ t('vel.in') }}</span>
            <span class="inline-flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-sm bg-emerald-500" />{{ t('vel.out') }}</span>
          </div>
        </div>
        <div class="p-4">
          <div class="flex items-end gap-[3px] h-[180px]">
            <div v-for="row in d.daily" :key="row.date"
                 class="flex-1 flex items-end justify-center gap-[2px] group relative h-full"
                 :title="`${row.date} · in ${row.in} · out ${row.out}`">
              <div class="w-1/2 max-w-[10px] rounded-t-sm bg-stone-300" :style="{ height: barH(row.in) }" />
              <div class="w-1/2 max-w-[10px] rounded-t-sm bg-emerald-500" :style="{ height: barH(row.out) }" />
            </div>
          </div>
          <div class="flex justify-between text-[10px] text-stone-400 mt-1.5 tabular-nums">
            <span>{{ shortDate(d.daily[0]?.date) }}</span>
            <span>{{ shortDate(d.daily[d.daily.length - 1]?.date) }}</span>
          </div>
          <p class="text-[11px] text-stone-400 mt-2 leading-relaxed">{{ t('vel.chartNote') }}</p>
        </div>
      </section>

      <!-- Stuck tails -->
      <section>
        <div class="flex items-center gap-2 mb-2 px-1">
          <Icon name="alert-circle" :size="15" class="text-stone-400" />
          <span class="text-[13px] font-bold text-stone-900">{{ t('vel.stuckTitle') }}</span>
        </div>
        <div class="grid md:grid-cols-3 gap-3">
          <div v-for="b in d.stuck" :key="b.key"
               class="bg-white rounded-2xl ring-1 p-4"
               :class="b.n ? 'ring-rose-200' : 'ring-stone-200/70'">
            <div class="flex items-center justify-between gap-2">
              <span class="text-[12px] font-semibold text-stone-800">{{ t('vel.stuck_' + b.key) }}</span>
              <RouterLink v-if="b.route" :to="{ name: b.route }"
                          class="text-[11px] font-semibold text-[var(--accent-700)] hover:underline">{{ t('vel.open') }}</RouterLink>
            </div>
            <div class="flex items-baseline gap-2 mt-1">
              <span class="text-[24px] font-extrabold tabular-nums" :class="b.n ? 'text-rose-600' : 'text-stone-300'">{{ b.n }}</span>
              <span v-if="b.n" class="text-[11px] text-stone-500">{{ t('vel.oldest') }} {{ b.oldestD }}{{ t('vel.dayShort') }}</span>
            </div>
            <div v-if="b.rows.length" class="mt-2.5 space-y-1 border-t border-stone-100 pt-2.5">
              <RouterLink v-for="o in b.rows" :key="o.order"
                          :to="{ name: 'OrderDetail', params: { name: o.order } }"
                          class="flex items-center gap-2 text-[11.5px] hover:bg-stone-50 rounded px-1 py-0.5 -mx-1">
                <span class="font-mono text-stone-700">{{ o.order }}</span>
                <span class="text-stone-400 truncate flex-1">{{ o.customer }}</span>
                <span class="tabular-nums text-rose-500 shrink-0">{{ o.ageD }}{{ t('vel.dayShort') }}</span>
              </RouterLink>
            </div>
            <div v-else class="text-[11.5px] text-stone-400 mt-2">{{ t('vel.clear') }}</div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, num } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();

const days = ref(14);
const d = ref(null);
const loading = ref(true);
const loadError = ref("");

const chartMax = computed(() =>
  Math.max(1, ...(d.value?.daily || []).flatMap((r) => [r.in, r.out])));
function barH(v) { return Math.round((v / chartMax.value) * 100) + "%"; }
function shortDate(s) { return s ? s.slice(5) : ""; }

const paceClass = computed(() => {
  const p = d.value?.kpis?.pacePct || 0;
  if (p >= 95) return { text: "text-emerald-600", ring: "" };
  if (p >= 80) return { text: "text-amber-600", ring: "ring-2 ring-amber-300" };
  return { text: "text-rose-600", ring: "ring-2 ring-rose-300" };
});

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    d.value = await api("velocity.board", { days: days.value });
  } catch (e) {
    loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
.vb-kpi { display: flex; flex-direction: column; gap: 2px; background: #fff; border-radius: 14px; padding: 12px 14px; box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8); }
.vb-l { font-size: 10px; font-weight: 700; color: rgb(120 113 108); text-transform: uppercase; letter-spacing: .04em; }
.vb-n { font-size: 22px; font-weight: 800; color: rgb(28 25 23); font-variant-numeric: tabular-nums; line-height: 1.15; }
.vb-s { font-size: 10.5px; color: rgb(168 162 158); font-variant-numeric: tabular-nums; }
</style>
