<template>
  <div class="p-4 sm:p-6 max-w-[1180px] mx-auto">
    <!-- ── the window ─────────────────────────────────────────────── -->
    <div class="flex items-center gap-3 flex-wrap mb-5">
      <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('cfp.title') }}</h1>
      <div class="flex items-center gap-1 p-0.5 bg-stone-100/80 rounded-lg">
        <button v-for="r in RANGES" :key="r.d"
                class="h-7 px-3 text-[12px] font-semibold rounded-md transition-all"
                :class="days === r.d
                  ? 'bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]'
                  : 'text-stone-500 hover:text-stone-800'"
                @click="pick(r.d)">{{ t(r.l) }}</button>
      </div>
      <button class="ms-auto h-8 px-3 rounded-lg text-[12px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
              :disabled="loading" @click="load()">
        <Icon name="refresh-cw" :size="13" class="inline -mt-px me-1" />{{ t('common.refresh') }}
      </button>
    </div>

    <div v-if="loading" class="space-y-4">
      <div class="h-[190px] rounded-2xl bg-white ring-1 ring-stone-200/60 animate-pulse" />
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div v-for="n in 3" :key="n" class="h-[104px] rounded-2xl bg-white ring-1 ring-stone-200/60 animate-pulse" />
      </div>
    </div>

    <template v-else-if="d">
      <!-- ── THE FUNNEL ───────────────────────────────────────────────
           One picture of the whole lane: what came in, what survived each
           step, and what fell out where. Everything else on this page is a
           detail of one of these five numbers. -->
      <section class="cfp-hero rounded-2xl p-5 mb-4">
        <div class="flex items-baseline gap-2.5 mb-4">
          <span class="text-[12px] font-semibold uppercase tracking-wide text-stone-400">{{ t('cfp.funnel') }}</span>
          <span class="text-[11.5px] text-stone-400">{{ t('cfp.cohort') }}</span>
        </div>

        <div class="flex items-stretch gap-2 flex-wrap sm:flex-nowrap">
          <div v-for="(st, i) in stages" :key="st.k" class="flex items-stretch gap-2 min-w-0 flex-1">
            <div class="min-w-0 flex-1">
              <div class="text-[11.5px] font-semibold text-stone-500 truncate">{{ t(st.l) }}</div>
              <div class="text-[26px] leading-tight font-bold tabular-nums" :class="st.tone">{{ fmt(st.n) }}</div>
              <div class="h-1.5 rounded-full mt-1.5 overflow-hidden bg-stone-100">
                <div class="h-full rounded-full transition-all" :class="st.bar"
                     :style="{ width: pctOf(st.n) + '%' }" />
              </div>
              <div v-if="st.rate !== null && st.rate !== undefined"
                   class="text-[11px] mt-1 tabular-nums" :class="st.tone">
                {{ st.rate }}%<span class="text-stone-400 font-normal"> {{ t(st.rateL) }}</span>
              </div>
              <div v-else class="text-[11px] mt-1 text-stone-400 tabular-nums">{{ fmtMAD(st.mad) }} MAD</div>
            </div>
            <Icon v-if="i < stages.length - 1" name="chevron-right" :size="15"
                  class="text-stone-300 self-center shrink-0 rtl-flip" />
          </div>
        </div>

        <!-- Where the rest went. Two leaks, and they are not the same kind
             of loss: a cancel is a sale that never happened, a door failure
             cost a round trip as well. -->
        <div class="flex gap-2.5 flex-wrap mt-4 pt-4 border-t border-stone-200/70">
          <div class="cfp-leak cfp-leak-rose">
            <Icon name="x" :size="13" />
            <span class="font-semibold">{{ fmt(d.funnel.cancelled) }}</span>
            <span class="opacity-75">{{ t('cfp.leakCancel') }}</span>
            <b class="tabular-nums ms-auto" dir="ltr">−{{ fmtMAD(d.funnel.lostCancel) }}</b>
          </div>
          <div class="cfp-leak cfp-leak-amber">
            <Icon name="alert-triangle" :size="13" />
            <span class="font-semibold">{{ fmt(d.funnel.failed) }}</span>
            <span class="opacity-75">{{ t('cfp.leakDoor') }}</span>
            <b class="tabular-nums ms-auto" dir="ltr">−{{ fmtMAD(d.funnel.lostDoor) }}</b>
          </div>
          <!-- A cohort measured today is not finished. Saying so on the face
               of the number is the difference between a dashboard and a
               rumour: without it the newest month always looks worst. -->
          <div v-if="d.funnel.inFlight" class="cfp-leak cfp-leak-sky">
            <Icon name="truck" :size="13" />
            <span class="font-semibold">{{ fmt(d.funnel.inFlight) }}</span>
            <span class="opacity-75">{{ t('cfp.inFlight') }}</span>
          </div>
        </div>
      </section>

      <!-- ── three numbers, each with its own direction ───────────── -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <div v-for="k in kpis" :key="k.k" class="cfp-kpi">
          <div class="flex items-center gap-1.5">
            <Icon :name="k.icon" :size="12" :class="k.icon_cls" />
            <span class="text-[11.5px] font-semibold text-stone-500">{{ t(k.l) }}</span>
          </div>
          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-[25px] font-bold tabular-nums text-stone-900">{{ k.v }}</span>
            <span v-if="k.delta !== null" class="text-[12px] font-bold tabular-nums"
                  :class="k.good ? 'text-emerald-600' : 'text-rose-500'" dir="ltr">
              {{ k.delta > 0 ? '+' : '' }}{{ k.delta }}{{ k.unit }}
            </span>
          </div>
          <div class="text-[11px] text-stone-400 mt-0.5">{{ k.sub }}</div>
        </div>
      </div>

      <!-- ── the shape of the days ────────────────────────────────── -->
      <section class="cfp-card p-5 mb-4">
        <div class="flex items-baseline gap-2.5 mb-3">
          <span class="text-[12px] font-semibold uppercase tracking-wide text-stone-400">{{ t('cfp.byDay') }}</span>
          <span class="flex items-center gap-3 ms-auto text-[11px] text-stone-500">
            <span class="inline-flex items-center gap-1"><i class="w-2 h-2 rounded-sm bg-stone-300" />{{ t('cfp.sArrived') }}</span>
            <span class="inline-flex items-center gap-1"><i class="w-2 h-2 rounded-sm bg-violet-400" />{{ t('cfp.sConfirmed') }}</span>
            <span class="inline-flex items-center gap-1"><i class="w-2 h-2 rounded-sm bg-emerald-500" />{{ t('cfp.sDelivered') }}</span>
          </span>
        </div>
        <div v-if="!d.daily.length" class="text-[12px] text-stone-400 py-6 text-center">{{ t('cfp.noDays') }}</div>
        <div v-else class="flex items-end gap-[3px] h-[132px]" dir="ltr">
          <div v-for="row in d.daily" :key="row.d"
               class="flex-1 min-w-0 flex items-end justify-center gap-[2px] group relative"
               :title="`${row.d} · ${row.arrived} → ${row.confirmed} → ${row.delivered}`">
            <span class="w-1/3 rounded-t-[2px] bg-stone-200 group-hover:bg-stone-300 transition-colors"
                  :style="{ height: barH(row.arrived) }" />
            <span class="w-1/3 rounded-t-[2px] bg-violet-300 group-hover:bg-violet-400 transition-colors"
                  :style="{ height: barH(row.confirmed) }" />
            <span class="w-1/3 rounded-t-[2px] bg-emerald-400 group-hover:bg-emerald-500 transition-colors"
                  :style="{ height: barH(row.delivered) }" />
          </div>
        </div>
      </section>

      <!-- ── where the money leaves ───────────────────────────────── -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <section class="cfp-card p-5">
          <div class="text-[12px] font-semibold uppercase tracking-wide text-stone-400 mb-1">{{ t('cfp.whyCancel') }}</div>
          <!-- Ranked by VALUE, not by count. Ten cheap cancels are not the
               problem one expensive one is. -->
          <div class="text-[11px] text-stone-400 mb-3">{{ t('cfp.byValue') }}</div>
          <div v-if="!d.reasons.length" class="text-[12px] text-stone-400 py-4 text-center">{{ t('cfp.none') }}</div>
          <ul v-else class="space-y-1.5">
            <li v-for="r in d.reasons" :key="r.reason" class="flex items-center gap-2.5 text-[12.5px]">
              <span class="truncate text-stone-700 min-w-0 flex-1" dir="auto">{{ r.reason }}</span>
              <span class="w-16 h-1.5 rounded-full bg-stone-100 overflow-hidden shrink-0">
                <span class="block h-full rounded-full bg-rose-400" :style="{ width: share(r.value, d.reasons) + '%' }" />
              </span>
              <span class="tabular-nums text-stone-400 w-9 text-end shrink-0">{{ r.n }}</span>
              <b class="tabular-nums text-stone-800 w-[74px] text-end shrink-0" dir="ltr">{{ fmtMAD(r.value) }}</b>
            </li>
          </ul>
        </section>

        <section class="cfp-card p-5">
          <div class="text-[12px] font-semibold uppercase tracking-wide text-stone-400 mb-1">{{ t('cfp.whereFail') }}</div>
          <div class="text-[11px] text-stone-400 mb-3">{{ t('cfp.byCount') }}</div>
          <div v-if="!d.cities.length" class="text-[12px] text-stone-400 py-4 text-center">{{ t('cfp.none') }}</div>
          <ul v-else class="space-y-1.5">
            <li v-for="c in d.cities" :key="c.city" class="flex items-center gap-2.5 text-[12.5px]">
              <span class="truncate text-stone-700 min-w-0 flex-1" dir="auto">{{ c.city }}</span>
              <span class="w-16 h-1.5 rounded-full bg-stone-100 overflow-hidden shrink-0">
                <span class="block h-full rounded-full bg-amber-400" :style="{ width: share(c.n, d.cities, 'n') + '%' }" />
              </span>
              <span class="tabular-nums text-stone-400 w-9 text-end shrink-0">{{ c.n }}</span>
              <b class="tabular-nums text-stone-800 w-[74px] text-end shrink-0" dir="ltr">{{ fmtMAD(c.value) }}</b>
            </li>
          </ul>
        </section>
      </div>

      <p class="text-[11px] text-stone-400 mt-4 leading-relaxed">{{ t('cfp.foot') }}</p>
    </template>

    <div v-else class="rounded-2xl p-12 text-center bg-white ring-1 ring-stone-200/70">
      <div class="text-[14px] text-stone-500">{{ t('cfp.none') }}</div>
    </div>
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

const RANGES = [
  { d: 1, l: "cfp.rToday" },
  { d: 7, l: "cfp.r7" },
  { d: 30, l: "cfp.r30" },
  { d: 90, l: "cfp.r90" },
];

const d = ref(null);
const days = ref(30);
const loading = ref(true);

function fmt(n) { return Number(n || 0).toLocaleString(); }
function fmtMAD(n) {
  const v = Math.round(Number(n || 0));
  return v >= 1000 ? (v / 1000).toFixed(v >= 10000 ? 0 : 1) + "k" : String(v);
}

// Every bar in the funnel is a share of what ARRIVED — the one denominator
// that makes the five numbers readable as a single shape.
function pctOf(n) {
  const a = d.value?.funnel?.arrived || 0;
  return a ? Math.max(2, Math.round((Number(n || 0) / a) * 100)) : 0;
}
function share(v, list, key = "value") {
  const top = Math.max(...list.map((x) => Number(x[key] || 0)), 1);
  return Math.max(4, Math.round((Number(v || 0) / top) * 100));
}
const dayMax = computed(() =>
  Math.max(...(d.value?.daily || []).map((r) => r.arrived || 0), 1));
function barH(n) {
  return Math.max(2, Math.round((Number(n || 0) / dayMax.value) * 120)) + "px";
}

const stages = computed(() => {
  const f = d.value?.funnel || {};
  return [
    { k: "arrived", l: "cfp.sArrived", n: f.arrived, mad: f.value,
      tone: "text-stone-900", bar: "bg-stone-300", rate: null },
    { k: "confirmed", l: "cfp.sConfirmed", n: f.confirmed, mad: f.confirmedValue,
      tone: "text-violet-700", bar: "bg-violet-400",
      rate: f.confirmRate, rateL: "cfp.ofArrived" },
    { k: "delivered", l: "cfp.sDelivered", n: f.delivered, mad: f.collected,
      tone: "text-emerald-700", bar: "bg-emerald-500",
      rate: f.stickRate, rateL: "cfp.ofSettled" },
  ];
});

// A delta only means something against the same length of time. The backend
// measures the window immediately before this one for exactly that reason.
function delta(key, digits = 1) {
  const a = d.value?.funnel?.[key];
  const b = d.value?.prev?.[key];
  if (a === null || a === undefined || b === null || b === undefined) return null;
  return Number((a - b).toFixed(digits));
}

const kpis = computed(() => {
  const f = d.value?.funnel || {};
  const s = d.value?.speed || {};
  const dc = delta("confirmRate");
  const ds = delta("stickRate");
  const collected = f.collected || 0;
  const pc = d.value?.prev?.collected;
  const dm = pc ? Number((((collected - pc) / pc) * 100).toFixed(1)) : null;
  return [
    { k: "confirm", l: "cfp.kConfirm", icon: "check-circle", icon_cls: "text-violet-500",
      v: f.confirmRate === null || f.confirmRate === undefined ? "—" : f.confirmRate + "%",
      delta: dc, unit: "pt", good: (dc ?? 0) >= 0,
      sub: t("cfp.kConfirmSub").replace("{n}", fmt(f.confirmed)) },
    { k: "stick", l: "cfp.kStick", icon: "truck", icon_cls: "text-emerald-500",
      v: f.stickRate === null || f.stickRate === undefined ? "—" : f.stickRate + "%",
      delta: ds, unit: "pt", good: (ds ?? 0) >= 0,
      sub: t("cfp.kStickSub").replace("{n}", fmt(f.settled)) },
    { k: "speed", l: "cfp.kSpeed", icon: "clock", icon_cls: "text-amber-500",
      v: s.median === null || s.median === undefined ? "—" : s.median + t("cf.hrs"),
      delta: null, unit: "",
      sub: s.slaPct === null || s.slaPct === undefined
        ? t("cfp.kSpeedNone")
        : t("cfp.kSpeedSub").replace("{p}", s.slaPct).replace("{h}", s.slaH) },
  ];
});

function pick(n) { if (days.value === n) return; days.value = n; load(); }

async function load() {
  loading.value = true;
  try {
    d.value = await api("confirmation.pulse_board", { days: days.value });
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
    d.value = null;
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>
