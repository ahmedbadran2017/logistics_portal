<template>
  <div class="max-w-[1200px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('tmx.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[660px]">
          {{ lane === 'cc' ? t('tmx.introCc') : t('tmx.introFloor') }}
        </p>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <div v-if="lane === 'cc'" class="flex items-center gap-1.5">
          <button v-for="b in ['deliver', 'confirm', 'overall']" :key="b"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                  :class="basis === b ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]' : 'text-stone-600 bg-white ring-stone-200 hover:ring-stone-300'"
                  @click="setBasis(b)">{{ t('cmx.b_' + b) }}</button>
        </div>
        <div class="flex items-center gap-1.5">
          <button v-for="l in ['cc', 'floor']" :key="l"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                  :class="lane === l ? 'text-white bg-stone-900 ring-stone-900' : 'text-stone-600 bg-white ring-stone-200 hover:ring-stone-300'"
                  @click="setLane(l)">{{ t('tmx.lane_' + l) }}</button>
        </div>
      </div>
    </header>

    <div v-if="loading" class="h-[380px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />

    <!-- ── Confirmation: agent × city ─────────────────────────────────── -->
    <template v-else-if="lane === 'cc' && cc && cc.rows.length">
      <section class="flex items-center gap-3 flex-wrap">
        <div v-for="k in ccHeadline" :key="k.label" class="rounded-xl bg-white ring-1 ring-stone-200/70 px-4 py-2.5">
          <div class="text-[19px] font-extrabold tabular-nums" :class="band(k.raw)">{{ k.value }}</div>
          <div class="text-[10px] uppercase font-semibold text-stone-400 mt-0.5">{{ k.label }}</div>
        </div>
        <p class="text-[11px] text-stone-400 max-w-[400px] leading-relaxed">{{ t('tmx.ccNote') }}</p>
      </section>

      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-x-auto">
        <div class="p-3 min-w-[860px]">
          <div class="grid items-center gap-1 mb-1" :style="ccCols">
            <div />
            <div v-for="c in cc.columns" :key="c" class="text-center text-[10px] text-stone-400 truncate px-0.5">{{ c }}</div>
            <div class="text-center text-[10px] uppercase font-semibold text-stone-400">{{ t('cmx.avg') }}</div>
          </div>
          <div v-for="r in cc.rows" :key="r.user" class="grid items-center gap-1 mb-1" :style="ccCols">
            <div class="min-w-0 pe-2">
              <div class="text-[12.5px] font-semibold text-stone-900 truncate" dir="auto">{{ r.name }}</div>
              <div class="text-[10px] text-stone-400 tabular-nums">{{ r.orders }} · {{ r.confirmPct }}% → {{ r.deliveredPct }}%</div>
            </div>
            <div v-for="(cell, i) in r.cells" :key="i"
                 class="h-9 rounded-md grid place-items-center relative"
                 :class="cell.covered ? '' : 'bg-stone-100'"
                 :style="cell.covered ? { background: heat(cell.score), opacity: cell.conf === 'low' ? 0.45 : 1 } : {}"
                 :title="cell.covered ? `${cell.n} · ${cell.raw}%` : t('cmx.noData')">
              <span v-if="cell.covered" class="text-[12px] font-bold tabular-nums text-stone-900">{{ Math.round(cell.score) }}</span>
              <Icon v-else name="minus" :size="11" class="text-stone-300" />
              <span v-if="cell.covered && cell.conf === 'low'"
                    class="absolute bottom-1 end-1 w-[5px] h-[5px] rounded-full border-[1.5px] border-stone-900/70" />
            </div>
            <div class="h-9 rounded-md grid place-items-center bg-stone-50 text-[12.5px] font-bold tabular-nums"
                 :class="band(r.score)">{{ Math.round(r.score) }}</div>
          </div>
          <div class="flex items-center gap-4 mt-3 px-1 text-[10.5px] text-stone-400 flex-wrap">
            <span class="flex items-center gap-1.5">
              <span v-for="s in [60, 70, 80, 90]" :key="s" class="w-[18px] h-2 rounded-sm" :style="{ background: heat(s) }" />60 → 90
            </span>
            <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full border-[1.5px] border-stone-400" />{{ t('cmx.legendLow') }}</span>
          </div>
        </div>
      </section>
    </template>

    <!-- ── Floor: person × station ────────────────────────────────────── -->
    <template v-else-if="lane === 'floor' && fl && fl.rows.length">
      <p class="text-[11px] text-stone-500 bg-stone-50 ring-1 ring-stone-200/60 rounded-xl px-3.5 py-2.5 leading-relaxed">
        <Icon name="info" :size="12" class="inline -mt-px text-stone-400" /> {{ t('tmx.floorNote') }}
      </p>
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-x-auto">
        <div class="p-3 min-w-[820px]">
          <div class="grid items-center gap-1 mb-1" :style="flCols">
            <div />
            <div v-for="s in fl.columns" :key="s" class="text-center">
              <div class="text-[10.5px] text-stone-500 font-semibold">{{ t('fa.st_' + s, s) }}</div>
              <div class="text-[9px] text-stone-300 tabular-nums">{{ fl.median[s] }}/h</div>
            </div>
          </div>
          <div v-for="r in fl.rows" :key="r.user" class="grid items-center gap-1 mb-1" :style="flCols">
            <div class="min-w-0 pe-2">
              <div class="text-[12.5px] font-semibold text-stone-900 truncate" dir="auto">{{ r.name }}</div>
              <div class="text-[10px] text-stone-400 tabular-nums">{{ r.actions }} · {{ r.hours }}h</div>
            </div>
            <div v-for="s in fl.columns" :key="s"
                 class="h-10 rounded-md grid place-items-center leading-none"
                 :class="r.stations[s] ? '' : 'bg-stone-100'"
                 :style="r.stations[s] ? { background: relHeat(r.stations[s].rel) } : {}"
                 :title="r.stations[s] ? `${r.stations[s].actions} · ${r.stations[s].hours}h · ${r.stations[s].rel}×` : t('tmx.never')">
              <template v-if="r.stations[s]">
                <span class="text-[12px] font-bold tabular-nums text-stone-900">{{ r.stations[s].actions }}</span>
                <span class="text-[9px] tabular-nums text-stone-600/80">{{ r.stations[s].pace }}/h</span>
              </template>
              <Icon v-else name="minus" :size="11" class="text-stone-300" />
            </div>
          </div>
          <div class="flex items-center gap-4 mt-3 px-1 text-[10.5px] text-stone-400 flex-wrap">
            <span class="flex items-center gap-1.5">
              <span v-for="v in [0.4, 0.8, 1.2, 2]" :key="v" class="w-[18px] h-2 rounded-sm" :style="{ background: relHeat(v) }" />
              {{ t('tmx.vsMedian') }}
            </span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-2 rounded-sm bg-stone-100 ring-1 ring-stone-200" />{{ t('tmx.never') }}</span>
          </div>
        </div>
      </section>
    </template>

    <div v-else class="rounded-2xl bg-white ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="users" :size="24" class="mx-auto text-stone-300" />
      <div class="text-[14px] font-semibold text-stone-700 mt-2">{{ t('cmx.empty') }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const lane = ref("cc");
const basis = ref("deliver");
const cc = ref(null);
const fl = ref(null);
const loading = ref(true);

const ccCols = computed(() => ({
  gridTemplateColumns: `170px repeat(${(cc.value?.columns || []).length}, minmax(0,1fr)) 56px`,
}));
const flCols = computed(() => ({
  gridTemplateColumns: `170px repeat(${(fl.value?.columns || []).length}, minmax(0,1fr))`,
}));

// Same scale as the city matrix, so a colour means one thing across the portal.
const STOPS = [[58, [225, 29, 72]], [76, [245, 158, 11]], [90, [16, 185, 129]]];
function mix(v, stops) {
  const x = Math.max(stops[0][0], Math.min(stops[stops.length - 1][0], Number(v) || 0));
  let a = stops[0], b = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (x >= stops[i][0] && x <= stops[i + 1][0]) { a = stops[i]; b = stops[i + 1]; break; }
  }
  const k = b[0] === a[0] ? 0 : (x - a[0]) / (b[0] - a[0]);
  const c = a[1].map((y, i) => Math.round(y + (b[1][i] - y) * k));
  return `rgba(${c[0]},${c[1]},${c[2]},0.55)`;
}
const heat = (s) => mix(s, STOPS);
// The floor cell is a ratio to the station's median worker, not a 0–100 score,
// so it gets its own anchors: 1.0 is the middle of the team, and the ends are
// clamped well before the outliers a burst station produces.
const REL_STOPS = [[0.4, [225, 29, 72]], [1.0, [245, 158, 11]], [1.6, [16, 185, 129]]];
const relHeat = (r) => mix(r, REL_STOPS);
function band(s) {
  if (s == null) return "text-stone-400";
  return s >= 80 ? "text-emerald-600" : s >= 70 ? "text-amber-600" : "text-rose-600";
}

const ccHeadline = computed(() => {
  const x = cc.value;
  if (!x) return [];
  return [
    { label: t("cmx.netScore"), value: x.netScore, raw: x.netScore },
    { label: t("cmx.b_confirm"), value: (x.netConfirm ?? "—") + "%", raw: x.netConfirm },
    { label: t("cmx.b_deliver"), value: (x.netDeliver ?? "—") + "%", raw: x.netDeliver },
  ];
});

async function load() {
  loading.value = true;
  try {
    if (lane.value === "cc") {
      cc.value = await api("contact_center.agent_matrix", { basis: basis.value, weeks: 12 });
    } else {
      fl.value = await api("scanlog.floor_matrix", { days: 30 });
    }
  } catch { if (lane.value === "cc") cc.value = null; else fl.value = null; }
  loading.value = false;
}
function setLane(l) { lane.value = l; load(); }
function setBasis(b) { basis.value = b; load(); }
onMounted(load);
</script>
