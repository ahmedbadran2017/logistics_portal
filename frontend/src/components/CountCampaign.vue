<template>
  <section v-if="d" class="space-y-4">
    <!-- No campaign yet: the only thing to do is start one. -->
    <div v-if="!c" class="rounded-2xl bg-white ring-1 ring-stone-200/70 p-6 text-center">
      <div class="text-[15px] font-bold text-stone-900">{{ t('camp.noneTitle') }}</div>
      <p class="text-[12.5px] text-stone-500 mt-1 max-w-[460px] mx-auto">
        {{ t('camp.noneBody').replace('{n}', String(d.candidateBins || 0)) }}
      </p>
      <button class="mt-3 h-10 px-5 rounded-xl text-[13px] font-bold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50"
              :disabled="busy" @click="start">{{ busy ? t('camp.starting') : t('camp.start') }}</button>
    </div>

    <template v-else>
      <!-- The campaign itself: number, window, and the one number that matters -->
      <div class="rounded-2xl p-5 md:p-6"
           :class="c.status === 'Closed' ? 'bg-emerald-900 text-white' : 'bg-stone-900 text-white'">
        <div class="flex items-center gap-2 flex-wrap mb-3">
          <span class="text-[13px] font-bold">{{ t('camp.title') }} #{{ c.no }}</span>
          <span class="text-[11px] px-2 py-0.5 rounded-full font-semibold"
                :class="c.status === 'Closed' ? 'bg-emerald-400 text-emerald-950' : 'bg-white/15'">
            {{ c.status === 'Closed' ? t('camp.closed') : t('camp.open') }}
          </span>
          <span class="text-[11px] opacity-70 tabular-nums">
            {{ c.startedOn }}<template v-if="c.closedOn"> → {{ c.closedOn }}</template>
          </span>
          <span v-if="c.blocked" class="ms-auto inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-[12px] font-bold text-amber-900 bg-amber-300">
            <Icon name="clock" :size="12" />{{ c.blocked }} {{ t('camp.blocked') }}
          </span>
        </div>
        <div class="flex items-center gap-6 flex-wrap">
          <div class="flex items-end gap-2">
            <span class="text-[46px] leading-none font-bold tabular-nums">{{ c.pct }}</span>
            <span class="text-[20px] font-bold opacity-60 mb-1">%</span>
          </div>
          <div class="min-w-0 flex-1">
            <div class="h-2.5 rounded-full bg-white/15 overflow-hidden flex">
              <div class="h-full bg-emerald-400 transition-[width] duration-500" :style="{ width: c.pct + '%' }" />
              <div class="h-full bg-amber-400 transition-[width] duration-500"
                   :style="{ width: (c.scope ? (c.blocked / c.scope) * 100 : 0) + '%' }" />
            </div>
            <div class="text-[11.5px] opacity-75 mt-1.5 tabular-nums">
              {{ c.done }} / {{ c.scope }} {{ t('camp.bins') }} ·
              {{ c.left }} {{ t('camp.leftLabel') }}
              <template v-if="c.blocked"> · {{ c.blocked }} {{ t('camp.blocked') }}</template>
            </div>
          </div>
        </div>
        <p class="text-[11px] opacity-55 mt-3 leading-relaxed">
          <Icon name="info" :size="11" class="inline -mt-px" /> {{ t('camp.scopeNote') }}
        </p>
      </div>

      <!-- The countdown, day by day: what got done and what was still left -->
      <div v-if="c.days.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-900">
          {{ t('camp.daily') }}
        </div>
        <div class="divide-y divide-stone-50">
          <div v-for="r in c.days" :key="r.day" class="px-4 py-2.5 flex items-center gap-3 text-[12px]">
            <span class="font-semibold text-stone-800 tabular-nums w-[74px] flex-shrink-0">{{ r.day.slice(5) }}</span>
            <span class="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden">
              <span class="block h-full bg-[var(--accent-500)]"
                    :style="{ width: (c.scope ? (r.bins / c.scope) * 100 : 0) + '%' }" />
            </span>
            <span class="tabular-nums font-bold text-stone-900 w-[58px] text-end">+{{ r.bins }}</span>
            <span class="tabular-nums text-stone-400 w-[66px] text-end">{{ r.people }} {{ t('camp.ppl') }}</span>
            <span class="tabular-nums text-stone-500 w-[78px] text-end">{{ r.left }} {{ t('camp.leftLabel') }}</span>
          </div>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-4">
        <!-- Aisles inside the campaign -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-900">{{ t('camp.aisles') }}</div>
          <div class="divide-y divide-stone-50 max-h-[340px] overflow-y-auto">
            <div v-for="z in c.zones" :key="z.zone" class="px-4 py-2 flex items-center gap-3 text-[12px]">
              <span class="font-bold text-stone-900 w-[70px] truncate flex-shrink-0">{{ z.zone }}</span>
              <span class="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden">
                <span class="block h-full" :class="z.done >= z.bins ? 'bg-emerald-500' : 'bg-[var(--accent-400)]'"
                      :style="{ width: (z.bins ? (z.done / z.bins) * 100 : 0) + '%' }" />
              </span>
              <span class="tabular-nums text-stone-500 w-[60px] text-end">{{ z.done }}/{{ z.bins }}</span>
            </div>
          </div>
        </div>

        <!-- Who counted what -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-900">{{ t('camp.people') }}</div>
          <div v-if="!c.people.length" class="px-4 py-6 text-center text-[12px] text-stone-400">{{ t('cc.noPeople') }}</div>
          <div v-else class="divide-y divide-stone-50 max-h-[340px] overflow-y-auto">
            <div v-for="p in c.people" :key="p.user" class="px-4 py-2.5 flex items-center gap-3">
              <span class="text-[12.5px] text-stone-900 truncate flex-1" dir="auto">{{ p.name }}</span>
              <span v-if="p.blocked" class="text-[10px] font-bold text-amber-700 bg-amber-50 rounded px-1.5 py-0.5">{{ p.blocked }}</span>
              <span class="text-[10.5px] text-stone-400 tabular-nums">{{ p.last.slice(5, 10) }}</span>
              <span class="text-[14px] font-bold text-stone-900 tabular-nums w-[42px] text-end">{{ p.bins }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- What is left to walk — the worklist, straight into the count screen -->
      <div v-if="c.leftBins.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
          <span class="text-[12px] font-semibold text-stone-900">{{ t('camp.remaining') }}</span>
          <span class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ c.left }}</span>
        </div>
        <div class="p-3 flex flex-wrap gap-1.5 max-h-[220px] overflow-y-auto">
          <button v-for="b in c.leftBins" :key="b.warehouse"
                  class="h-7 px-2.5 rounded-lg font-mono text-[11px] font-semibold text-stone-700 bg-stone-50 ring-1 ring-stone-200 hover:ring-[var(--accent-400)] hover:text-[var(--accent-700)]"
                  @click="$router.push({ name: 'CycleCount', query: { bin: b.warehouse } })">
            {{ b.bin }}
          </button>
        </div>
      </div>

      <!-- The frozen report: what the campaign corrected, kept as the record -->
      <div v-if="c.report" class="bg-white rounded-xl ring-1 ring-emerald-200 overflow-hidden">
        <div class="px-4 py-3 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="check-circle" :size="15" class="text-emerald-600" />
          <span class="text-[13px] font-bold text-stone-900">{{ t('camp.reportTitle') }} #{{ c.report.no }}</span>
          <span class="text-[11px] text-stone-400 tabular-nums">{{ c.report.startedOn }} → {{ c.report.closedOn }}</span>
          <button class="ms-auto h-8 px-3 rounded-lg text-[11.5px] font-semibold text-stone-700 bg-stone-100 hover:bg-stone-200"
                  @click="csv">{{ t('camp.export') }}</button>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-px bg-stone-100">
          <div v-for="k in reportKpis" :key="k.label" class="bg-white px-4 py-3">
            <div class="text-[18px] font-extrabold tabular-nums" :class="k.cls">{{ k.value }}</div>
            <div class="text-[10px] uppercase font-semibold text-stone-400 mt-0.5">{{ k.label }}</div>
          </div>
        </div>
        <div v-if="c.report.lines.length" class="divide-y divide-stone-50 max-h-[320px] overflow-y-auto">
          <div v-for="(l, i) in c.report.lines" :key="i" class="px-4 py-2 flex items-center gap-3 text-[11.5px]">
            <span class="font-mono font-semibold text-stone-800 w-[64px] flex-shrink-0">{{ l.bin }}</span>
            <span class="font-mono text-stone-400 truncate flex-1">{{ l.item }}</span>
            <span class="tabular-nums text-stone-400 w-[46px] text-end">{{ l.book }}</span>
            <span class="tabular-nums text-stone-700 w-[46px] text-end">{{ l.counted }}</span>
            <span class="tabular-nums font-bold w-[52px] text-end"
                  :class="l.delta > 0 ? 'text-emerald-600' : 'text-rose-600'">
              {{ l.delta > 0 ? '+' + l.delta : l.delta }}
            </span>
          </div>
        </div>
        <p v-if="c.report.newBinsCount" class="px-4 py-2.5 text-[11px] text-stone-500 border-t border-stone-100">
          {{ t('camp.newBins').replace('{n}', String(c.report.newBinsCount)) }}
        </p>
      </div>

      <div v-if="c.status === 'Closed'" class="text-center">
        <button class="h-10 px-5 rounded-xl text-[13px] font-bold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50"
                :disabled="busy" @click="start">
          {{ busy ? t('camp.starting') : t('camp.startNext').replace('{n}', String(c.no + 1)) }}
        </button>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const d = ref(null);
const busy = ref(false);
const c = computed(() => d.value?.campaign || null);

const reportKpis = computed(() => {
  const r = c.value?.report;
  if (!r) return [];
  return [
    { label: t("camp.kBins"), value: r.bins, cls: "text-stone-900" },
    { label: t("camp.kDiffBins"), value: r.binsWithDifference, cls: "text-amber-600" },
    { label: t("camp.kNet"), value: (r.netPieces > 0 ? "+" : "") + r.netPieces, cls: r.netPieces < 0 ? "text-rose-600" : "text-emerald-600" },
    { label: t("camp.kValue"), value: fmt(r.valueDelta) + " MAD", cls: r.valueDelta < 0 ? "text-rose-600" : "text-emerald-600" },
  ];
});
function fmt(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }

async function load() {
  try { d.value = await api("campaign.state"); }
  catch (e) { d.value = null; }
}
async function start() {
  busy.value = true;
  try {
    const r = await apiPost("campaign.open_campaign");
    success(t("camp.started").replace("{n}", String(r.no)), String(r.bins));
    await load();
  } catch (e) {
    warn(t("cc.ctlTitle"), String(e.message || e));
  } finally { busy.value = false; }
}

// The manager's copy. A frozen report that can only be read on screen is not
// a record anybody can file, so it leaves as a spreadsheet too.
function csv() {
  const r = c.value?.report;
  if (!r) return;
  const head = ["bin", "item", "book", "counted", "delta", "by", "at"];
  const rows = r.lines.map((l) => head.map((k) => `"${String(l[k] ?? "").replace(/"/g, '""')}"`).join(","));
  const blob = new Blob(["﻿" + head.join(",") + "\n" + rows.join("\n")],
                        { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `count-campaign-${r.no}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

defineExpose({ load });
onMounted(load);
</script>
