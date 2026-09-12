<template>
  <div class="max-w-[1100px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cc.ctlTitle') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cc.ctlIntro') }}</p>
      </div>
      <div class="flex items-center gap-1.5">
        <button v-for="d in [7, 30, 90]" :key="d"
                class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors tabular-nums"
                :class="days === d ? 'text-white bg-stone-900 ring-stone-900' : 'text-stone-600 bg-white ring-stone-200 hover:ring-stone-300'"
                @click="setDays(d)">{{ d }}{{ t('cc.dayShort') }}</button>
      </div>
    </header>

    <div v-if="loading" class="space-y-3">
      <div class="h-[132px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        <div v-for="n in 8" :key="n" class="h-[96px] rounded-xl bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
    </div>

    <template v-else-if="data">
      <!-- The one number: how much of the stocked warehouse has been walked. -->
      <section class="rounded-2xl bg-stone-900 text-white p-5 md:p-6">
        <div class="flex items-center gap-6 flex-wrap">
          <div class="flex items-end gap-2">
            <span class="text-[46px] leading-none font-bold tabular-nums">{{ h.pct }}</span>
            <span class="text-[20px] font-bold opacity-60 mb-1">%</span>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-semibold">{{ t('cc.heroLabel') }}</div>
            <div class="h-2.5 rounded-full bg-white/15 mt-2 overflow-hidden">
              <div class="h-full rounded-full bg-emerald-400 transition-[width] duration-500"
                   :style="{ width: h.pct + '%' }" />
            </div>
            <div class="text-[11.5px] opacity-70 mt-1.5 tabular-nums">
              {{ h.countedStocked }} / {{ h.stocked }} {{ t('cc.binsWithStock') }} ·
              {{ h.left }} {{ t('cc.left') }} ·
              {{ fmt(h.unitsCounted) }} / {{ fmt(h.units) }} {{ t('recv.units') }}
            </div>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <router-link v-if="h.pending" :to="{ name: 'CycleCount' }"
                         class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12px] font-bold text-amber-900 bg-amber-300 hover:bg-amber-200">
              <Icon name="clock" :size="13" />{{ h.pending }} {{ t('cc.pending') }}
            </router-link>
            <span class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12px] font-semibold bg-white/10 tabular-nums">
              {{ h.pctAll }}% {{ t('cc.ofAllBins') }}
            </span>
          </div>
        </div>
        <!-- Honesty line: a clean count used to leave no trace, so anything
             counted before the witness shipped can only be seen through the
             reconciliation it happened to produce. -->
        <p v-if="h.byReco" class="text-[11px] opacity-55 mt-3 leading-relaxed">
          <Icon name="info" :size="11" class="inline -mt-px" />
          {{ t('cc.floorNote').replace('{s}', String(h.bySession)).replace('{r}', String(h.byReco)) }}
        </p>
      </section>

      <!-- Zones — where the campaign stands, aisle by aisle -->
      <section>
        <h2 class="text-[13px] font-semibold text-stone-900 mb-2">{{ t('cc.zones') }}</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-2.5">
          <div v-for="z in liveZones" :key="z.zone"
               class="rounded-xl bg-white ring-1 p-3"
               :class="z.pct >= 100 ? 'ring-emerald-300' : 'ring-stone-200/70'">
            <div class="flex items-baseline gap-2">
              <span class="text-[14px] font-bold text-stone-900 truncate">{{ z.zone }}</span>
              <span class="ms-auto text-[15px] font-bold tabular-nums" :class="barText(z.pct)">{{ z.pct }}%</span>
            </div>
            <div class="h-1.5 rounded-full bg-stone-100 mt-2 overflow-hidden">
              <div class="h-full rounded-full transition-[width] duration-500"
                   :class="barBg(z.pct)" :style="{ width: z.pct + '%' }" />
            </div>
            <div class="text-[11px] text-stone-500 mt-1.5 tabular-nums">
              {{ z.countedStocked }}/{{ z.stocked }} {{ t('cc.bins') }} · {{ fmt(z.units) }} {{ t('recv.units') }}
            </div>
            <div v-if="z.lastBy" class="text-[10.5px] text-stone-400 mt-0.5 truncate">
              {{ z.lastAt.slice(5, 10) }} · {{ z.lastBy.split('@')[0] }}
            </div>
            <div v-else class="text-[10.5px] text-stone-300 mt-0.5">{{ t('cc.never') }}</div>
          </div>
        </div>
        <p v-if="emptyZones.length" class="text-[11px] text-stone-400 mt-2">
          {{ t('cc.emptyZones').replace('{n}', String(emptyZones.length)) }}: {{ emptyZones.map(z => z.zone).join(', ') }}
        </p>
      </section>

      <div class="grid md:grid-cols-2 gap-4">
        <!-- Who is counting -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cc.people') }}</span>
            <span class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ data.people.length }}</span>
          </div>
          <div v-if="!data.people.length" class="px-4 py-6 text-center text-[12px] text-stone-400">{{ t('cc.noPeople') }}</div>
          <div v-else class="divide-y divide-stone-50 max-h-[380px] overflow-y-auto">
            <div v-for="p in data.people" :key="p.user" class="px-4 py-2.5 flex items-center gap-3">
              <span class="w-7 h-7 rounded-lg bg-stone-100 text-stone-600 flex items-center justify-center text-[10.5px] font-bold flex-shrink-0">
                {{ initials(p.name) }}
              </span>
              <div class="min-w-0 flex-1">
                <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ p.name }}</div>
                <div class="text-[10.5px] text-stone-400 tabular-nums">
                  {{ p.last.slice(5, 16) }}
                  <span v-if="p.src === 'reco'" class="ms-1 text-amber-600">· {{ t('cc.viaDesk') }}</span>
                </div>
              </div>
              <div class="text-end flex-shrink-0">
                <div class="text-[13px] font-bold text-stone-900 tabular-nums">{{ p.binCount }}</div>
                <div class="text-[10px] text-stone-400">{{ t('cc.bins') }}</div>
              </div>
              <div class="text-end flex-shrink-0 w-[52px]">
                <div class="text-[13px] font-bold text-violet-700 tabular-nums">{{ p.lines }}</div>
                <div class="text-[10px] text-stone-400">{{ t('cc.lines') }}</div>
              </div>
            </div>
          </div>
        </section>

        <!-- What is still untouched — the worklist, biggest first -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cc.notCounted') }}</span>
            <span class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ data.uncountedTotal }}</span>
          </div>
          <div v-if="!data.uncounted.length" class="px-4 py-6 text-center text-[12px] text-emerald-700">{{ t('cc.allDone') }}</div>
          <div v-else class="divide-y divide-stone-50 max-h-[380px] overflow-y-auto">
            <button v-for="u in data.uncounted" :key="u.warehouse"
                    class="w-full text-start px-4 py-2 flex items-center gap-3 hover:bg-stone-50 transition-colors"
                    @click="$router.push({ name: 'CycleCount', query: { bin: u.warehouse } })">
              <span class="font-mono text-[12px] font-semibold text-stone-800 w-[70px] flex-shrink-0">{{ u.bin }}</span>
              <span class="text-[11px] text-stone-400 tabular-nums flex-1">{{ u.lines }} {{ t('cc.lines') }}</span>
              <span class="text-[12.5px] font-bold text-stone-700 tabular-nums">{{ fmt(u.units) }}</span>
              <Icon name="chevron-right" :size="13" class="text-stone-300 flex-shrink-0" />
            </button>
          </div>
        </section>
      </div>

      <!-- Daily rhythm: only real once sessions exist, so it hides until then -->
      <section v-if="data.daily.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="text-[12px] font-semibold text-stone-900 mb-2.5">{{ t('cc.daily') }}</div>
        <div class="flex items-end gap-1 h-[64px]">
          <div v-for="d in data.daily" :key="d.day" class="flex-1 min-w-[4px] rounded-t bg-[var(--accent-500)] hover:bg-[var(--accent-600)] transition-colors"
               :style="{ height: Math.max(4, (d.bins / dailyMax) * 64) + 'px' }"
               :title="d.day + ' · ' + d.bins + ' ' + t('cc.bins')" />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { warn } = useToast();

const data = ref(null);
const loading = ref(true);
const days = ref(30);

const h = computed(() => data.value?.headline || {});
// A zone with nothing on its shelves has no counting work in it; listing the
// reserve racking (270 empty bins) alongside the live aisles would bury them.
const liveZones = computed(() => (data.value?.zones || []).filter((z) => z.stocked > 0));
const emptyZones = computed(() => (data.value?.zones || []).filter((z) => !z.stocked));
const dailyMax = computed(() => Math.max(1, ...(data.value?.daily || []).map((d) => d.bins)));

function barBg(p) {
  if (p >= 100) return "bg-emerald-500";
  if (p >= 60) return "bg-emerald-400";
  if (p >= 25) return "bg-amber-400";
  return "bg-rose-400";
}
function barText(p) {
  if (p >= 60) return "text-emerald-600";
  if (p >= 25) return "text-amber-600";
  return "text-rose-600";
}
function initials(n) {
  return String(n || "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0] || "").join("").toUpperCase();
}
function fmt(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }

async function load() {
  loading.value = true;
  try {
    data.value = await api("cycle_count.progress", { days: days.value });
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
function setDays(d) { days.value = d; load(); }
onMounted(load);
</script>
