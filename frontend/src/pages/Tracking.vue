<template>
  <!-- Parcel timeline (full page) -->
  <div v-if="tlParcel" class="p-5 sm:p-6 max-w-[900px] mx-auto animate-fade-in">
    <button
      class="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"
      @click="tlParcel = null"
    >
      <Icon name="chevron-left" :size="15" />Tracking
    </button>

    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3">
          <span class="w-11 h-11 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center">
            <Icon name="globe" :size="22" />
          </span>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h1 class="font-mono text-[17px] font-bold text-stone-900">{{ tlParcel.dn }}</h1>
              <TrackBadge :state="tlParcel.track" />
              <SlaBadge :sla="tlParcel.sla" />
            </div>
            <div class="text-[12.5px] text-stone-600 mt-1">{{ tlParcel.customer }} · {{ tlParcel.carrier }}</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
            @click="openOrder(tlParcel.order)"
          >
            <Icon name="package" :size="15" />Order {{ tlParcel.order }}
          </button>
          <button class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300">
            Open in ERP <Icon name="chevron-right" :size="15" />
          </button>
        </div>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        <div v-for="(kv, i) in timelineStats" :key="i" class="bg-stone-50 rounded-xl px-3 py-2.5">
          <div class="text-[14px] font-semibold text-stone-900 tabular-nums leading-tight truncate">{{ kv[1] }}</div>
          <div class="text-[11px] text-stone-500 mt-1">{{ kv[0] }}</div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
          <div><div class="text-[13px] font-semibold text-stone-900">Timeline</div><div class="text-[11px] text-stone-400">{{ tlParcel.carrier }}</div></div>
        </div>
        <div class="p-4">
          <ol class="relative">
            <li v-for="(e, i) in timelineSteps" :key="i" class="relative flex gap-3.5 pb-4 last:pb-0">
              <span
                v-if="i !== timelineSteps.length - 1"
                class="absolute top-8 w-px"
                :class="e.done && !e.bad ? 'bg-emerald-200' : 'bg-stone-200'"
                :style="{ insetInlineStart: '13px' }"
              />
              <span
                class="relative z-10 w-[27px] h-[27px] rounded-lg flex items-center justify-center flex-shrink-0"
                :class="e.done ? (e.bad ? 'bg-rose-500 text-white' : 'bg-emerald-500 text-white') : 'bg-white ring-1 ring-stone-300 text-stone-400'"
              >
                <Icon v-if="e.done && e.bad" name="alert-circle" :size="14" />
                <Icon v-else-if="e.done" name="check" :size="14" />
                <template v-else>{{ i + 1 }}</template>
              </span>
              <div class="min-w-0 flex-1">
                <div class="text-[13px] font-medium" :class="e.bad ? 'text-rose-700' : e.done ? 'text-stone-900' : 'text-stone-400'">{{ e.label }}</div>
                <div v-if="e.done" class="text-[11px] text-stone-400 tabular-nums">{{ e.at }}</div>
              </div>
            </li>
          </ol>
        </div>
      </div>

      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="px-4 py-3 border-b border-stone-100"><div class="text-[13px] font-semibold text-stone-900">Carrier message</div></div>
        <div class="p-4">
          <div
            class="rounded-xl p-3 ring-1"
            :class="isBad(tlParcel.track) ? 'bg-rose-50 ring-rose-200/60' : 'bg-stone-50 ring-stone-200/60'"
          >
            <div class="flex items-center gap-2 mb-1.5">
              <span class="w-2 h-2 rounded-full" :class="isBad(tlParcel.track) ? 'bg-rose-500' : 'bg-emerald-500'" />
              <span class="text-[11px] font-semibold uppercase tracking-wide text-stone-500">{{ tlParcel.carrier }}</span>
            </div>
            <p class="text-[12.5px] text-stone-800 text-pretty">{{ tlParcel.msg }}</p>
          </div>
          <div v-if="isBad(tlParcel.track)" class="grid grid-cols-1 gap-2 mt-3">
            <button class="inline-flex items-center justify-center gap-1.5 px-3 h-10 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"><Icon name="clock" :size="15" />Reschedule</button>
            <button class="inline-flex items-center justify-center gap-1.5 px-3 h-10 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"><Icon name="activity" :size="15" />Contact</button>
            <button class="inline-flex items-center justify-center gap-1.5 px-3 h-10 text-[12.5px] font-medium rounded-lg ring-1 ring-rose-200 text-rose-700 bg-white hover:ring-rose-300"><Icon name="rotate-ccw" :size="15" />Mark returned</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Tracking board -->
  <div v-else class="p-5 sm:p-6 max-w-[1400px] mx-auto animate-fade-in">
    <div class="flex items-start justify-between gap-3 mb-5 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Tracking</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ CARRIER }} · live parcel states</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-[11.5px] text-stone-400">Last sync just now</span>
        <button
          class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
          @click="info(`Synced with ${CARRIER}`)"
        >
          <Icon name="globe" :size="15" />Sync
        </button>
      </div>
    </div>

    <!-- exceptions panel -->
    <div v-if="exc.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 mb-5">
      <div class="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
        <div class="text-[13px] font-semibold text-stone-900">Delivery exceptions</div>
        <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 text-rose-700 bg-rose-50 ring-rose-200">
          <span class="w-1.5 h-1.5 rounded-full bg-rose-500" />{{ exc.length }}
        </span>
      </div>
      <div class="divide-y divide-stone-100">
        <div v-for="p in exc" :key="p.dn" class="flex items-center gap-3 px-4 py-3 flex-wrap">
          <span class="font-mono text-[12px] font-semibold text-stone-900 w-[150px] flex-shrink-0">{{ p.dn }}</span>
          <div class="flex-1 min-w-[140px]">
            <div class="text-[12.5px] text-stone-800 truncate">{{ p.customer }}</div>
            <div class="text-[11px] text-rose-600 truncate">{{ p.msg }}</div>
          </div>
          <TrackBadge :state="p.track" />
          <div class="flex items-center gap-1.5">
            <button class="inline-flex items-center gap-1.5 px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300" @click="resolve(p, 'Rescheduled')"><Icon name="clock" :size="13" />Reschedule</button>
            <button class="inline-flex items-center gap-1.5 px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300" @click="resolve(p, 'Contacted')"><Icon name="activity" :size="13" />Contact</button>
            <button class="inline-flex items-center gap-1.5 px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 ring-rose-200 text-rose-700 bg-white hover:ring-rose-300" @click="resolve(p, 'Marked returned')"><Icon name="rotate-ccw" :size="13" />Mark returned</button>
          </div>
        </div>
      </div>
    </div>

    <!-- clickable state distribution -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 mb-4">
      <button
        v-for="s in TRACK_STATES"
        :key="s"
        class="rounded-xl ring-1 p-3 text-center transition-all"
        :class="stateF === s ? 'ring-[var(--accent-400)] bg-[var(--accent-50)]/50' : 'ring-stone-200/70 bg-white hover:ring-stone-300'"
        @click="stateF = stateF === s ? 'all' : s"
      >
        <div class="text-[20px] font-semibold text-stone-900 tabular-nums leading-none">{{ counts[s] ?? 0 }}</div>
        <div class="text-[10px] text-stone-500 mt-1.5 leading-tight">{{ TRACK_LABEL[s] }}</div>
      </button>
    </div>

    <!-- search -->
    <div class="flex items-center gap-2 mb-3 flex-wrap">
      <div class="relative flex-1 min-w-[200px]">
        <Icon name="search" :size="14" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input
          v-model="q"
          placeholder="Search DN, AWB, tracking no, customer…"
          class="w-full h-9 ps-9 pe-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none"
        />
      </div>
      <button
        v-if="stateF !== 'all'"
        class="px-2.5 h-9 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-600 hover:ring-stone-300 inline-flex items-center gap-1.5"
        @click="stateF = 'all'"
      >
        <TrackBadge :state="stateF" /><Icon name="x" :size="12" />
      </button>
    </div>

    <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
      <div class="px-4 py-3 border-b border-stone-100">
        <div class="text-[13px] font-semibold text-stone-900">Parcels</div>
        <div class="text-[11px] text-stone-400">{{ shown.length }} {{ stateF === "all" ? "active" : TRACK_LABEL[stateF] }}</div>
      </div>
      <div class="divide-y divide-stone-100">
        <button
          v-for="p in shown"
          :key="p.dn"
          class="w-full grid items-center gap-3 px-4 py-3 hover:bg-stone-50 transition-colors text-start grid-cols-[150px_1fr_auto_auto] md:grid-cols-[150px_1fr_120px_70px_auto]"
          @click="tlParcel = p"
        >
          <span class="font-mono text-[12px] font-semibold text-stone-900">{{ p.dn }}</span>
          <div class="min-w-0">
            <div class="text-[12.5px] text-stone-800 truncate">{{ p.customer }}</div>
            <div class="text-[11px] text-stone-500 truncate">{{ p.msg }}</div>
          </div>
          <span class="font-mono text-[11px] text-stone-400 hidden md:block">{{ p.trackNo }}</span>
          <span
            class="text-[11px] tabular-nums text-end hidden md:block"
            :class="p.days < 0 ? 'text-rose-600 font-medium' : p.days === 0 ? 'text-amber-600' : 'text-stone-400'"
          >{{ p.days < 0 ? `${Math.abs(p.days)}d overdue` : p.days === 0 ? "due today" : `${p.days}d` }}</span>
          <TrackBadge :state="p.track" />
        </button>
        <div v-if="shown.length === 0" class="text-center text-[12.5px] text-stone-400 py-12">No parcels match.</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, h, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import {
  PARCELS, TRACK_STATES, TRACK_LABEL, TRACK_COUNTS, SLA, SLA_LABEL, CARRIER, fmtMAD,
} from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";

const router = useRouter();
const { success, info } = useToast();

// ── inline badge primitives ────────────────────────────────────────
const TRACK_TONE = {
  pending: SLA.returned, pickedup: SLA.ontrack, intransit: SLA.ontrack,
  outfordelivery: SLA.atrisk, delivered: SLA.ontrack, exception: SLA.breached,
  failed: SLA.late, return: SLA.returned,
};
const TrackBadge = (props) => {
  const t = TRACK_TONE[props.state] || SLA.returned;
  return h("span", {
    class: ["inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap", t.txt, t.bg, t.ring],
  }, [
    h("span", { class: ["w-1.5 h-1.5 rounded-full", t.dot] }),
    TRACK_LABEL[props.state] || props.state,
  ]);
};
const SlaBadge = (props) => {
  const t = SLA[props.sla] || SLA.ontrack;
  return h("span", {
    class: ["inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap", t.txt, t.bg, t.ring],
  }, [
    h("span", { class: ["w-1.5 h-1.5 rounded-full", t.dot] }),
    SLA_LABEL[props.sla] || props.sla,
  ]);
};

const resolved = ref(new Set());
const stateF = ref("all");
const q = ref("");
const tlParcel = ref(null);

// Live-or-demo data. `shipping.tracking` fills these once the app is installed;
// in local preview api() fails and the demo PARCELS/TRACK_COUNTS remain.
const parcels = ref(PARCELS);
const counts = ref(TRACK_COUNTS);

onMounted(async () => {
  const live = await liveOr(null, () => api("shipping.tracking"));
  if (live) {
    if (live.parcels && live.parcels.length) parcels.value = live.parcels;
    if (live.counts) counts.value = { ...TRACK_COUNTS, ...live.counts };
  }
});

const isBad = (track) => track === "exception" || track === "failed";

const exc = computed(() =>
  parcels.value.filter((p) => isBad(p.track) && !resolved.value.has(p.dn))
);
const shown = computed(() =>
  parcels.value.filter(
    (p) =>
      (stateF.value === "all" || p.track === stateF.value) &&
      (!q.value || `${p.dn} ${p.awb} ${p.trackNo} ${p.customer}`.toLowerCase().includes(q.value.toLowerCase()))
  )
);

function resolve(p, label) {
  resolved.value = new Set([...resolved.value, p.dn]);
  success(`${p.dn} · ${label} · synced to ${CARRIER}`);
}
function openOrder(no) {
  router.push({ name: "OrderDetail", params: { name: String(no).replace("#", "") } });
}

// ── parcel timeline derived state ──────────────────────────────────
const timelineStats = computed(() => {
  const p = tlParcel.value;
  if (!p) return [];
  return [
    ["AWB", p.awb],
    ["Tracking no", p.trackNo],
    ["Value", fmtMAD(p.value) + " MAD"],
    ["Days left", p.days < 0 ? Math.abs(p.days) + "d over" : p.days === 0 ? "today" : p.days + "d"],
  ];
});
const timelineSteps = computed(() => {
  const p = tlParcel.value;
  if (!p) return [];
  return [
    { k: "pickedup", label: TRACK_LABEL.pickedup, at: "Jun 19 · 14:22", done: true },
    { k: "intransit", label: TRACK_LABEL.intransit, at: "Jun 19 · 18:40", done: ["intransit", "outfordelivery", "delivered", "exception", "failed"].includes(p.track) },
    { k: "outfordelivery", label: TRACK_LABEL.outfordelivery, at: "Jun 20 · 08:10", done: ["outfordelivery", "delivered", "exception", "failed"].includes(p.track) },
    {
      k: p.track === "delivered" ? "delivered" : "exception",
      label: p.track === "delivered" ? TRACK_LABEL.delivered : p.track === "failed" ? TRACK_LABEL.failed : TRACK_LABEL.exception,
      at: "Jun 20 · 11:55",
      done: ["delivered", "exception", "failed"].includes(p.track),
      bad: isBad(p.track),
    },
  ];
});
</script>
