<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1240px] mx-auto">
    <!-- hero: what the team is, and the one number the whole room runs on -->
    <header class="sh-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-start justify-between gap-5 flex-wrap">
        <div class="flex items-center gap-3.5 min-w-0">
          <span class="sh-hero-icon"><Icon name="gauge" :size="22" /></span>
          <div class="min-w-0">
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('oclk.title') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5 max-w-[560px]">{{ t('oclk.intro') }}</p>
            <div class="mt-2 flex items-center gap-2 text-[11px] tabular-nums" :class="loadError ? 'text-rose-600' : 'text-stone-400'" dir="ltr">
              <span class="w-1.5 h-1.5 rounded-full" :class="loadError ? 'bg-rose-500' : refreshing ? 'bg-amber-400 animate-pulse' : 'bg-emerald-500'" />
              <span>{{ d?.now }}</span>
              <span v-if="loadError && d" dir="auto">{{ t('oclk.staleWarn') }}</span>
            </div>
          </div>
        </div>

        <div v-if="nw" class="flex items-center gap-3 flex-wrap">
          <!-- the countdown: the next van, and how much of its load is ready -->
          <div class="flex items-center gap-4 rounded-2xl px-4 py-3 bg-white/75 ring-1 ring-teal-200/70" style="backdrop-filter: blur(4px)">
            <svg width="64" height="64" viewBox="0 0 64 64" class="flex-shrink-0 -rotate-90" role="img" :aria-label="nw.ready + ' / ' + nw.n + ' ' + t('oclk.readyOf')">
              <circle cx="32" cy="32" r="26" fill="none" stroke="rgb(20 184 166 / 0.18)" stroke-width="7" />
              <circle cx="32" cy="32" r="26" fill="none" :stroke="nwLate ? 'rgb(244 63 94)' : 'rgb(20 184 166)'" stroke-width="7" stroke-linecap="round"
                      :stroke-dasharray="dash(nw.n ? nw.ready / nw.n : 1)" />
            </svg>
            <div>
              <div class="text-[10px] uppercase font-bold tracking-wide" :class="nwLate ? 'text-rose-600' : 'text-teal-700'">
                {{ t('oclk.nextWave') }} · {{ dayLabel(nw.dueAt) }} {{ nw.dueAt.slice(11) }}
              </div>
              <div class="sh-countdown mt-1" :class="nwLate ? 'text-rose-600' : 'text-stone-900'" dir="ltr">{{ countdown }}</div>
              <div class="text-[11px] text-stone-500 mt-1 tabular-nums">
                <b class="text-stone-800">{{ nw.n }}</b> · <span class="text-emerald-600 font-semibold">{{ nw.ready }} {{ t('oclk.readyLbl') }}</span>
                · <span class="text-amber-600 font-semibold">{{ nw.picking }} {{ t('oclk.picking') }}</span>
                · <span class="text-rose-600 font-semibold">{{ nw.toPick }} {{ t('oclk.noList') }}</span>
              </div>
            </div>
          </div>
          <div class="sh-stat" :title="t('oclk.keptSub')">
            <span class="sh-stat-n" :class="keptCls">{{ keptPct }}</span>
            <span class="sh-stat-l">{{ t('oclk.keptRate') }}</span>
          </div>
          <div class="sh-stat">
            <span class="sh-stat-n text-stone-900">{{ d.counts.live }}</span>
            <span class="sh-stat-l">{{ t('oclk.kLive') }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- my day: what I did, what the team did — from the trail the actions leave -->
    <section v-if="day" class="sh-card rounded-2xl px-4 py-3 flex items-center gap-3 flex-wrap">
      <span class="text-[11px] font-bold uppercase tracking-wide text-teal-700">{{ t('oclk.myDay') }}</span>
      <span v-for="k in DAY_KINDS" :key="k.key" class="inline-flex items-center gap-1.5 text-[12px]" :title="t('oclk.day_' + k.key)">
        <Icon :name="k.icon" :size="13" class="text-stone-400" />
        <b class="tabular-nums" :class="day.me[k.key] ? 'text-stone-900' : 'text-stone-300'">{{ day.me[k.key] }}</b>
        <span class="text-stone-500 hidden sm:inline">{{ t('oclk.day_' + k.key) }}</span>
      </span>
      <button class="ms-auto lp-tap inline-flex items-center gap-1.5 text-[11.5px] font-semibold text-stone-600 hover:text-stone-900" :aria-expanded="showTeam" @click="showTeam = !showTeam">
        {{ t('oclk.teamToday') }} <b class="tabular-nums text-stone-900">{{ day.totals.total }}</b>
        <Icon :name="showTeam ? 'chevron-up' : 'chevron-down'" :size="13" />
      </button>
      <div v-if="showTeam" class="basis-full grid sm:grid-cols-2 lg:grid-cols-3 gap-1.5 pt-1">
        <div v-for="m in day.team" :key="m.user" class="flex items-center gap-2 rounded-xl px-3 py-2 bg-stone-50 text-[11.5px]" :class="m.user === day.me.user ? 'ring-1 ring-teal-200' : ''">
          <span class="font-semibold text-stone-800 truncate flex-1" dir="auto">{{ m.name }}</span>
          <span v-for="k in DAY_KINDS" :key="k.key" class="inline-flex items-center gap-0.5 tabular-nums" :class="m[k.key] ? 'text-stone-700' : 'text-stone-300'" :title="t('oclk.day_' + k.key)">
            <Icon :name="k.icon" :size="11" />{{ m[k.key] }}
          </span>
        </div>
        <div v-if="!day.team.length" class="text-[11.5px] text-stone-400 px-1">{{ t('oclk.teamQuiet') }}</div>
      </div>
    </section>

    <!-- lenses: each one IS the list behind its number -->
    <div v-if="d" class="sticky top-[41px] z-10 -mx-2 px-2 py-1.5 rounded-xl flex items-center gap-3 flex-wrap"
         style="background: rgb(var(--bg) / 0.92); backdrop-filter: blur(6px)">
      <div class="sh-seg overflow-x-auto flex-shrink min-w-0" style="scrollbar-width: none">
        <button v-for="l in lenses" :key="l.view" class="sh-seg-btn" :class="view === l.view ? 'sh-seg-on' : ''"
                :aria-pressed="view === l.view" @click="setView(l.view)">
          <Icon :name="l.icon" :size="14" />
          <span>{{ l.label }}</span>
          <span class="sh-seg-count" :class="view === l.view ? l.on : 'bg-stone-200/70 text-stone-500'">{{ l.n }}</span>
        </button>
      </div>
      <RouterLink v-if="d.counts.failed" :to="{ name: 'Rescue' }" class="lp-tap inline-flex items-center gap-1.5 h-9 px-3 rounded-xl text-[12px] font-semibold text-rose-700 bg-rose-50 ring-1 ring-rose-200 hover:bg-rose-100" :title="t('oclk.toRescue')">
        <Icon name="route" :size="13" /><span>{{ t('oclk.failedLens') }}</span><span class="tabular-nums font-bold">{{ d.counts.failed }}</span><Icon name="arrow-right" :size="12" class="flip-rtl" />
      </RouterLink>
      <span class="text-[11px] text-stone-400 hidden lg:inline ms-auto">{{ t('oclk.lensHint') }}</span>
    </div>

    <!-- waves: the vans, in order. Missed ones fold into one red card. -->
    <section v-if="waves" class="flex gap-3 overflow-x-auto pb-1" style="scrollbar-width: thin">
      <div v-if="missed.n" class="sh-card sh-card-hot rounded-2xl p-4 min-w-[220px] flex-shrink-0 cursor-pointer" @click="showMissed = !showMissed">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 inline-flex items-center justify-center"><Icon name="alert-triangle" :size="15" /></span>
          <div>
            <div class="text-[11px] font-bold text-rose-600 uppercase tracking-wide">{{ t('oclk.missedWaves') }}</div>
            <div class="text-[10.5px] text-stone-400">{{ t('oclk.missedHint') }}</div>
          </div>
        </div>
        <div class="mt-3 flex items-end gap-2">
          <span class="text-[30px] font-extrabold tabular-nums leading-none text-rose-600">{{ missed.n }}</span>
          <span class="text-[11px] text-stone-500 mb-1">/ {{ missed.waves }} <Icon :name="showMissed ? 'chevron-up' : 'chevron-down'" :size="12" class="inline" /></span>
        </div>
        <div v-if="showMissed" class="mt-2 space-y-1 text-[11px] tabular-nums" dir="ltr">
          <div v-for="w in missed.list" :key="w.dueAt" class="flex justify-between text-stone-600">
            <span>{{ w.dueAt.slice(5) }}</span><span class="font-semibold text-rose-600">{{ w.n }}</span>
          </div>
        </div>
      </div>

      <button v-for="w in upcoming" :key="w.dueAt" class="sh-card rounded-2xl p-4 min-w-[230px] flex-shrink-0 text-start"
              :class="[nw && w.dueAt === nw.dueAt ? 'sh-card-next' : '', waveFilter === w.dueAt ? 'ring-2 ring-stone-900' : '']"
              :aria-pressed="waveFilter === w.dueAt" :title="t('oclk.waveFilter')" @click="toggleWave(w.dueAt)">
        <div class="flex items-center justify-between gap-2">
          <div>
            <div class="text-[11px] font-bold uppercase tracking-wide" :class="nw && w.dueAt === nw.dueAt ? 'text-teal-700' : 'text-stone-500'">{{ dayLabel(w.dueAt) }}</div>
            <div class="text-[20px] font-extrabold tabular-nums leading-none text-stone-900 mt-0.5" dir="ltr">{{ w.dueAt.slice(11) }}</div>
          </div>
          <svg width="44" height="44" viewBox="0 0 44 44" class="-rotate-90 flex-shrink-0" role="img" :aria-label="w.ready + ' / ' + w.n + ' ' + t('oclk.readyOf')">
            <circle cx="22" cy="22" r="17" fill="none" stroke="rgb(20 184 166 / 0.18)" stroke-width="5" />
            <circle cx="22" cy="22" r="17" fill="none" stroke="rgb(20 184 166)" stroke-width="5" stroke-linecap="round" :stroke-dasharray="dash(w.n ? w.ready / w.n : 1, 17)" />
          </svg>
        </div>
        <div class="mt-3 flex h-1.5 rounded-full overflow-hidden bg-stone-100">
          <span class="bg-emerald-400" :style="{ width: pct(w.ready, w.n) }" />
          <span class="bg-amber-400" :style="{ width: pct(w.picking, w.n) }" />
          <span class="bg-rose-400" :style="{ width: pct(w.toPick, w.n) }" />
        </div>
        <div class="mt-2 flex items-center justify-between text-[11px] tabular-nums">
          <span class="font-bold text-stone-900">{{ w.n }}</span>
          <span class="text-emerald-600 font-semibold">{{ w.ready }} {{ t('oclk.readyLbl') }}</span>
          <span class="text-amber-600 font-semibold">{{ w.picking }}</span>
          <span class="text-rose-600 font-semibold">{{ w.toPick }} {{ t('oclk.noList') }}</span>
        </div>
      </button>
    </section>

    <!-- the list -->
    <div v-if="!d && loading" class="space-y-2.5">
      <div v-for="n in 6" :key="n" class="h-[60px] rounded-2xl sh-shimmer" />
    </div>
    <div v-else-if="loadError && !d" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('common.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <section v-else-if="d && d.rows.length" class="space-y-4">
      <div class="flex items-center gap-2 px-1 flex-wrap">
        <span class="text-[13px] font-bold text-stone-900">{{ t('oclk.v_' + (d.view || view)) }}</span>
        <button v-if="waveFilter" class="lp-tap text-[11px] font-semibold text-teal-700 bg-teal-50 ring-1 ring-teal-200 rounded-full px-2 py-0.5 inline-flex items-center gap-1" @click="waveFilter = ''">
          {{ t('oclk.waveFilter') }} {{ waveFilter.slice(5) }}<Icon name="x" :size="11" />
        </button>
        <span class="text-[10.5px] text-stone-400 hidden md:inline">{{ t('oclk.keysHint') }}</span>
        <span class="text-[11px] text-stone-400 tabular-nums ms-auto" dir="ltr">
          <template v-if="d.rows.length < d.total">{{ d.rows.length }} / {{ d.total }}</template>
          <template v-else>{{ d.total }}</template>
        </span>
      </div>
      <div v-for="g in groups" :key="g.key" class="space-y-1.5">
        <div class="flex items-center gap-2 px-1">
          <span class="text-[10.5px] font-bold uppercase tracking-wide" :class="g.late ? 'text-rose-600' : 'text-stone-500'">{{ t('oclk.dueGroup') }} · {{ dayLabel(g.key) }} {{ g.key.slice(5, 10) }}</span>
          <span class="text-[10.5px] text-stone-400 tabular-nums">{{ g.rows.length }}</span>
          <span class="flex-1 h-px bg-stone-200/70" />
        </div>
        <div v-for="r in g.rows" :key="r.order" class="sh-card rounded-2xl px-4 py-3 flex items-center gap-4">
          <RouterLink :to="{ name: 'OrderDetail', params: { name: r.order } }" class="lp-tap contents">
          <div class="min-w-0 flex-1 basis-[150px]">
            <div class="font-mono text-[12.5px] font-bold text-stone-900 truncate" dir="ltr">{{ r.order }}</div>
            <div class="text-[11px] text-stone-400 truncate" dir="auto">{{ r.customer }}<span v-if="r.city" class="text-stone-300"> · </span><span dir="auto">{{ r.city }}</span></div>
          </div>
          <!-- the clock as a path: which doors this order has passed -->
          <div class="hidden sm:flex items-center" :title="stepTitle(r)">
            <template v-for="(s, i) in STEPS" :key="s">
              <span v-if="i" class="sh-step-line" :class="reached(r) >= i ? 'sh-step-line-on' : ''" />
              <span class="sh-step" :class="reached(r) >= i ? 'sh-step-on' : (r.late && reached(r) + 1 === i ? 'sh-step-late' : '')" />
            </template>
          </div>
          <span class="text-[10px] font-bold rounded-full px-2 py-0.5 whitespace-nowrap flex-shrink-0" :class="STAGE_CLS[r.stage]">{{ t('oclk.s_' + r.stage) }}</span>
          <span class="text-[11px] text-stone-400 tabular-nums w-[46px] text-end hidden lg:block" dir="ltr">{{ r.dueAt.slice(11) }}</span>
          <span class="text-[13px] font-extrabold tabular-nums w-[64px] text-end flex-shrink-0" dir="ltr"
                :class="r.late ? 'text-rose-600' : 'text-emerald-600'" :title="r.late ? t('oclk.pastPromise') : t('oclk.timeLeft')">{{ remain(r) }}</span>
          </RouterLink>
          <button v-if="view === 'chase'" class="lp-tap h-9 px-3 rounded-xl text-[12px] font-bold text-white flex-shrink-0 disabled:opacity-50"
                  style="background: linear-gradient(135deg, rgb(249 115 22), rgb(234 88 12)); box-shadow: 0 4px 12px -4px rgb(249 115 22 / .45)"
                  :disabled="chasing.has(r.order)" :title="t('oclk.chasedHint')" @click.stop="markChased(r)">
            <Icon name="phone" :size="13" class="inline -mt-px me-1" />{{ t('oclk.chased') }}
          </button>
        </div>
      </div>
    </section>

    <div v-else-if="d" class="sh-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center mb-3" :class="loadError ? 'bg-rose-50 text-rose-500' : 'bg-emerald-50 text-emerald-500'">
        <Icon :name="loadError ? 'alert-triangle' : 'check-circle'" :size="26" />
      </span>
      <div class="text-[15px] font-semibold text-stone-800">{{ loadError ? t('oclk.staleWarn') : t('oclk.clear') }}</div>
      <button v-if="loadError" class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { readStale, writeStale } from "@/lib/swr";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const waveFilter = ref("");
const chasing = ref(new Set());
const day = ref(null);
const showTeam = ref(false);
const DAY_KINDS = [
  { key: "chases", icon: "phone" }, { key: "rescues", icon: "route" }, { key: "cities", icon: "map-pin" },
  { key: "feedback", icon: "message-circle" }, { key: "notes", icon: "clipboard-check" },
];
async function loadDay() {
  try { day.value = await api("shipments.my_day"); } catch (_) { /* the strip is a bonus, never an error */ }
}
const d = ref(null);
const waves = ref(null);
const loading = ref(true);
const refreshing = ref(false);
const loadError = ref("");
const view = ref("late");
const showMissed = ref(false);
const nowTick = ref(Date.now());
let seq = 0;
let offsetMs = 0; // server floor clock minus this device's clock

const STEPS = ["stConfirmed", "stPicked", "stClosed", "stCarrier", "stDoor"];
const REACHED = { to_pick: 0, picking: 1, to_hand_over: 2, with_carrier: 3, delivered: 4, failed: 3 };
const STAGE_CLS = {
  to_pick: "text-rose-700 bg-rose-50 ring-1 ring-rose-200",
  picking: "text-amber-700 bg-amber-50 ring-1 ring-amber-200",
  to_hand_over: "text-violet-700 bg-violet-50 ring-1 ring-violet-200",
  with_carrier: "text-sky-700 bg-sky-50 ring-1 ring-sky-200",
};

const lenses = computed(() => {
  const c = d.value?.counts;
  if (!c) return [];
  return [
    { view: "late", icon: "alert-triangle", label: t("oclk.kLate"), n: c.lateInHouse, on: "bg-rose-100 text-rose-700" },
    { view: "to_pick", icon: "clipboard-check", label: t("oclk.kToPick"), n: c.toPick, on: "bg-amber-100 text-amber-700" },
    { view: "late_carrier", icon: "truck", label: t("oclk.kCarrier"), n: c.lateCarrier, on: "bg-rose-100 text-rose-700" },
    { view: "chase", icon: "phone", label: t("oclk.kChase"), n: c.chase, on: "bg-orange-100 text-orange-700" },
    { view: "live", icon: "package", label: t("oclk.kLive"), n: c.live, on: "bg-teal-100 text-teal-700" },
  ];
});

const nw = computed(() => d.value?.nextWave || null);
const nwLate = computed(() => nw.value && nw.value.minutes <= 0);
const keptPct = computed(() => {
  const k = d.value?.counts?.kept7d;
  return k && k.n ? Math.round(100 * k.ok / k.n) + "%" : "—";
});
const keptCls = computed(() => {
  const k = d.value?.counts?.kept7d;
  if (!k || !k.n) return "text-stone-400";
  const p = k.ok / k.n;
  return p >= 0.85 ? "text-emerald-600" : p >= 0.7 ? "text-amber-600" : "text-rose-600";
});

// Live countdown to the next van, on the server's floor clock, not the phone's.
const countdown = computed(() => {
  if (!nw.value) return "";
  const due = parse(nw.value.dueAt);
  let m = Math.round((due - (nowTick.value + offsetMs)) / 60000);
  const late = m < 0;
  m = Math.abs(m);
  const h = Math.floor(m / 60), mm = m % 60;
  const txt = h ? `${h}h ${String(mm).padStart(2, "0")}m` : `${mm}m`;
  return late ? "+" + txt : txt;
});

const missed = computed(() => {
  const now = d.value?.now || "";
  const list = (waves.value?.waves || []).filter((w) => w.dueAt < now);
  return { n: list.reduce((a, w) => a + w.n, 0), waves: list.length, list };
});
const upcoming = computed(() => {
  const now = d.value?.now || "";
  return (waves.value?.waves || []).filter((w) => w.dueAt >= now).slice(0, 5);
});

// Rows grouped by the day they are due; the oldest promise first.
const groups = computed(() => {
  const by = new Map();
  for (const r of d.value?.rows || []) {
    if (waveFilter.value && r.dueAt !== waveFilter.value) continue;
    const key = r.dueAt || "—";
    if (!by.has(key.slice(0, 10))) by.set(key.slice(0, 10), { key: key.slice(0, 10), rows: [], late: false });
    const g = by.get(key.slice(0, 10));
    g.rows.push(r);
    if (r.late) g.late = true;
  }
  return [...by.values()].sort((a, b) => (a.key < b.key ? -1 : 1))
    .map((g) => ({ ...g, rows: g.rows.sort((a, b) => b.lateMin - a.lateMin) }));
});

function parse(s) { return new Date(String(s).replace(" ", "T")).getTime(); }
function dash(frac, r = 26) {
  const c = 2 * Math.PI * r;
  return `${Math.max(0, Math.min(1, frac)) * c} ${c}`;
}
function pct(part, total) { return total ? (100 * part / total) + "%" : "0%"; }
function dayLabel(s) {
  const now = d.value?.now || "";
  const day = String(s).slice(0, 10);
  if (day === now.slice(0, 10)) return t("oclk.today");
  const tmr = new Date(parse(now.slice(0, 10) + " 12:00") + 86400000).toISOString().slice(0, 10);
  if (day === tmr) return t("oclk.tomorrow");
  return day.slice(5);
}
function reached(r) { return REACHED[r.stage] ?? 0; }
function stepTitle(r) {
  return [r.confirmedAt && `${t("oclk.stConfirmed")} ${r.confirmedAt.slice(5)}`, r.pickedAt && `${t("oclk.stPicked")} ${r.pickedAt.slice(5)}`,
    r.closedAt && `${t("oclk.stClosed")} ${r.closedAt.slice(5)}`, r.handedAt && `${t("oclk.stCarrier")} ${r.handedAt.slice(5)}`].filter(Boolean).join(" · ");
}
// Overdue carries a plus sign; time still in hand carries none.
function remain(r) {
  const m = Math.abs(r.lateMin || 0);
  const h = Math.floor(m / 60);
  const txt = h >= 48 ? Math.floor(h / 24) + t("oclk.dShort") : h + t("oclk.hShort");
  return (r.late ? "+" : "") + txt;
}

function accept(b) {
  d.value = b;
  waves.value = { waves: b.waveBuckets || [], now: b.now };
  if (b?.now) offsetMs = parse(b.now) - Date.now();
}
async function load() {
  const my = ++seq;
  if (!d.value) loading.value = true; else refreshing.value = true;
  try {
    const b = await api("shipments.board", { view: view.value });
    if (my !== seq) return;
    accept(b); loadError.value = "";
    writeStale("ship.board." + view.value, b);
  } catch (e) {
    if (my !== seq) return;
    loadError.value = String(e?.message || e);
  }
  loading.value = false; refreshing.value = false;
}
function setView(v) {
  view.value = v;
  const stale = readStale("ship.board." + v);
  if (stale) accept(stale);
  load();
}
// A wave card narrows the list to that van's load (the in-house lens).
function toggleWave(dueAt) {
  if (waveFilter.value === dueAt) { waveFilter.value = ""; return; }
  waveFilter.value = dueAt;
  if (view.value !== "wave") setView("wave");
}
// Mark a parcel as chased: it leaves the list for the snooze window.
async function markChased(r) {
  if (chasing.value.has(r.order)) return;
  chasing.value.add(r.order);
  try {
    await apiPost("shipments.chase", { order: r.order });
    if (d.value) { d.value.rows = d.value.rows.filter((x) => x.order !== r.order); d.value.total -= 1; d.value.counts.chase = Math.max(0, d.value.counts.chase - 1); }
    success(t("oclk.chasedDone"), r.order); loadDay();
  } catch (e) { warn(t("oclk.saveFail"), String(e?.message || e)); }
  chasing.value.delete(r.order);
}
// 1-5 jump between lenses; Escape clears the wave filter.
function onKey(e) {
  if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
  const i = parseInt(e.key, 10);
  if (i >= 1 && i <= lenses.value.length) { waveFilter.value = ""; setView(lenses.value[i - 1].view); }
  if (e.key === "Escape") waveFilter.value = "";
}
onMounted(() => {
  const stale = readStale("ship.board." + view.value);
  if (stale) { accept(stale); loading.value = false; }
  load(); loadDay();
  window.addEventListener("keydown", onKey);
});
const tick = setInterval(() => { if (document.visibilityState === "visible") { load(); loadDay(); } }, 120000);
const clockTick = setInterval(() => { nowTick.value = Date.now(); }, 30000);
onUnmounted(() => { clearInterval(tick); clearInterval(clockTick); window.removeEventListener("keydown", onKey); });
</script>
