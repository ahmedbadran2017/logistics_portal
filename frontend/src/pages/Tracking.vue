<template>
  <!-- Parcel timeline (full page) -->
  <div v-if="tlParcel" class="p-5 sm:p-6 max-w-[900px] mx-auto animate-fade-in">
    <button
      class="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"
      @click="tlParcel = null"
    >
      <Icon name="chevron-left" :size="15" class="flip-rtl" />{{ t("trk.title") }}
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
            <div class="text-[12.5px] text-stone-600 mt-1">
              {{ tlParcel.customer }} · {{ tlParcel.carrier }}<span v-if="tlParcel.city"> · {{ tlParcel.city }}</span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <button
            v-if="tlParcel.order"
            class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
            @click="openOrder(tlParcel.order)"
          >
            <Icon name="package" :size="15" />{{ tlParcel.order }}
          </button>
          <a
            :href="'/app/delivery-note/' + encodeURIComponent(tlParcel.dn)" target="_blank"
            class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
          >
            {{ t("trk.openErp") }} <Icon name="chevron-right" :size="15" class="flip-rtl" />
          </a>
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
          <div><div class="text-[13px] font-semibold text-stone-900">{{ t("trk.timeline") }}</div><div class="text-[11px] text-stone-400">{{ tlParcel.carrier }} · {{ t("trk.lastUpdate") }} {{ tlParcel.updated || "—" }}</div></div>
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
                <div v-if="e.at" class="text-[11px] text-stone-400 tabular-nums">{{ e.at }}</div>
              </div>
            </li>
          </ol>
        </div>
      </div>

      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="px-4 py-3 border-b border-stone-100"><div class="text-[13px] font-semibold text-stone-900">{{ t("trk.carrierStatus") }}</div></div>
        <div class="p-4">
          <div
            class="rounded-xl p-3 ring-1"
            :class="isBad(tlParcel.track) ? 'bg-rose-50 ring-rose-200/60' : 'bg-stone-50 ring-stone-200/60'"
          >
            <div class="flex items-center gap-2 mb-1.5">
              <span class="w-2 h-2 rounded-full" :class="isBad(tlParcel.track) ? 'bg-rose-500' : 'bg-emerald-500'" />
              <span class="text-[11px] font-semibold uppercase tracking-wide text-stone-500">{{ tlParcel.carrier }}</span>
            </div>
            <p class="text-[12.5px] text-stone-800 text-pretty">
              {{ trackLabel(tlParcel.track) }} — {{ t("trk.sinceShipped").replace("{n}", tlParcel.days) }}
            </p>
          </div>
          <div class="grid grid-cols-1 gap-2 mt-3">
            <a
              v-if="tlParcel.awb"
              :href="'https://cathedis.ma/shipment/?track_number=' + tlParcel.awb" target="_blank"
              class="inline-flex items-center justify-center gap-1.5 px-3 h-10 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
            ><Icon name="globe" :size="15" />{{ t("trk.trackOn") }}</a>
            <a
              v-if="tlParcel.phone"
              :href="'tel:' + tlParcel.phone"
              class="inline-flex items-center justify-center gap-1.5 px-3 h-10 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
            ><Icon name="phone" :size="15" />{{ t("trk.call") }} {{ tlParcel.customer.split(" ")[0] }} · {{ tlParcel.phone }}</a>
            <a
              v-if="tlParcel.phone"
              :href="waLink(tlParcel.phone)" target="_blank"
              class="inline-flex items-center justify-center gap-1.5 px-3 h-10 text-[12.5px] font-medium rounded-lg ring-1 ring-emerald-200 text-emerald-700 bg-white hover:ring-emerald-300"
            ><Icon name="message-circle" :size="15" />{{ t("trk.whatsapp") }}</a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Tracking board -->
  <div v-else class="p-5 sm:p-6 max-w-[1400px] mx-auto animate-fade-in">
    <div class="flex items-start justify-between gap-3 mb-5 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t("trk.title") }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ CARRIER }} · {{ t("trk.subtitle").replace("{n}", daysF) }}</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center rounded-lg ring-1 ring-stone-200 bg-white p-0.5">
          <button
            v-for="d in [7, 14, 30]" :key="d"
            class="px-2.5 h-7 text-[12px] font-medium rounded-md transition-colors"
            :class="daysF === d ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-800'"
            @click="daysF = d; page = 1; load()"
          >{{ d }}d</button>
        </div>
        <span class="text-[11.5px] text-stone-400">{{ updatedAgo }}</span>
        <button
          class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
          :class="loading ? 'opacity-60 pointer-events-none' : ''"
          @click="load()"
        >
          <Icon name="refresh-cw" :size="15" :class="loading ? 'animate-spin' : ''" />{{ t("common.refresh") }}
        </button>
      </div>
    </div>

    <!-- clickable state distribution -->
    <div v-if="mode === 'loading'" class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 mb-4">
      <div v-for="n in 8" :key="n" class="rounded-xl ring-1 ring-stone-200/60 bg-white/70 p-3 animate-pulse">
        <div class="h-5 w-10 rounded bg-stone-100 mx-auto" />
        <div class="h-2 w-14 rounded bg-stone-100 mx-auto mt-2" />
      </div>
    </div>
    <div v-else class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 mb-4">
      <button
        v-for="s in TRACK_STATES"
        :key="s"
        class="rounded-xl ring-1 p-3 text-center transition-all"
        :class="stateF === s ? 'ring-[var(--accent-400)] bg-[var(--accent-50)]/50' : 'ring-stone-200/70 bg-white hover:ring-stone-300'"
        @click="setState(stateF === s ? '' : s)"
      >
        <div class="text-[20px] font-semibold tabular-nums leading-none"
             :class="(counts[s] ?? 0) > 0 ? 'text-stone-900' : 'text-stone-300'">{{ counts[s] ?? 0 }}</div>
        <div class="text-[10px] text-stone-500 mt-1.5 leading-tight">{{ trackLabel(s) }}</div>
      </button>
    </div>

    <!-- search -->
    <div class="flex items-center gap-2 mb-3 flex-wrap">
      <div class="relative flex-1 min-w-[200px]">
        <Icon name="search" :size="14" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input
          v-model="q"
          :placeholder="t('trk.searchPh')"
          class="w-full h-9 ps-9 pe-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none"
          @input="onSearch"
        />
      </div>
      <button
        v-if="stateF"
        class="px-2.5 h-9 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-600 hover:ring-stone-300 inline-flex items-center gap-1.5"
        @click="setState('')"
      >
        <TrackBadge :state="stateF" /><Icon name="x" :size="12" />
      </button>
    </div>

    <div v-if="mode === 'error'" class="bg-white rounded-xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t("trk.loadFail") }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[420px] mx-auto break-words">{{ loadError }}</div>
      <button
        class="mt-4 h-8 px-3 inline-flex items-center gap-1.5 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 hover:ring-stone-300 transition-all"
        @click="load()"
      >
        <Icon name="refresh-cw" :size="14" />{{ t("common.refresh") }}
      </button>
    </div>

    <div v-else class="bg-white rounded-xl ring-1 ring-stone-200/70">
      <div class="px-4 py-3 border-b border-stone-100">
        <div class="text-[13px] font-semibold text-stone-900">{{ t("trk.parcels") }}</div>
        <div class="text-[11px] text-stone-400 tabular-nums">
          {{ total }} {{ stateF ? trackLabel(stateF) : t("trk.active") }} · {{ t("trk.lastDays").replace("{n}", daysF) }}
        </div>
      </div>
      <div v-if="loading" class="divide-y divide-stone-100">
        <div v-for="n in 6" :key="n" class="px-4 py-3.5 flex items-center gap-4">
          <div class="h-3.5 w-32 rounded bg-stone-100 animate-pulse" />
          <div class="h-3.5 w-44 rounded bg-stone-100 animate-pulse" />
          <div class="h-3.5 w-20 rounded bg-stone-100 animate-pulse ms-auto" />
        </div>
      </div>
      <div v-else class="divide-y divide-stone-100">
        <div
          v-for="p in parcels"
          :key="p.dn"
          class="w-full grid items-center gap-3 px-4 py-3 hover:bg-stone-50 transition-colors text-start cursor-pointer grid-cols-[1fr_auto] md:grid-cols-[170px_1fr_110px_120px_70px_auto]"
          @click="tlParcel = p"
        >
          <div class="min-w-0">
            <div class="font-mono text-[12px] font-semibold text-stone-900 truncate">{{ p.dn }}</div>
            <div class="font-mono text-[10.5px] text-stone-400 truncate">{{ p.awb || "—" }}</div>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-1.5">
              <span class="text-[12.5px] text-stone-800 truncate">{{ p.customer }}</span>
              <template v-if="p.phone">
                <a :href="'tel:' + p.phone" @click.stop
                   class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-emerald-100 hover:text-emerald-700 flex items-center justify-center flex-shrink-0" :title="p.phone">
                  <Icon name="phone" :size="11" />
                </a>
                <a :href="waLink(p.phone)" target="_blank" @click.stop
                   class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-emerald-100 hover:text-emerald-700 flex items-center justify-center flex-shrink-0" title="WhatsApp">
                  <Icon name="message-circle" :size="11" />
                </a>
              </template>
            </div>
            <div class="text-[11px] text-stone-500 truncate">
              <span v-if="p.city">{{ p.city }} · </span>{{ fmtMAD(p.value) }} MAD
            </div>
          </div>
          <button
            v-if="p.order" @click.stop="openOrder(p.order)"
            class="font-mono text-[11px] text-stone-500 hover:text-stone-900 text-start truncate hidden md:block"
          >{{ p.order }}</button>
          <span v-else class="hidden md:block" />
          <span class="font-mono text-[11px] text-stone-400 hidden md:block truncate">{{ p.trackNo || "—" }}</span>
          <span
            class="text-[11px] tabular-nums text-end hidden md:block"
            :class="p.days > 7 ? 'text-rose-600 font-medium' : p.days > 3 ? 'text-amber-600' : 'text-stone-400'"
          >{{ p.days }}d</span>
          <TrackBadge :state="p.track" />
        </div>
        <div v-if="parcels.length === 0" class="text-center text-[12.5px] text-stone-400 py-12">{{ t("trk.noMatch") }}</div>
        <div v-if="total > pageSize" class="flex items-center justify-between px-4 py-2.5 bg-stone-50/50">
          <span class="text-[11.5px] text-stone-500 tabular-nums">
            {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} {{ t("trk.of") }} {{ total }}
          </span>
          <div class="flex items-center gap-1">
            <button class="pager-btn" :disabled="page <= 1" @click="page--; load(true)">
              <Icon name="chevron-left" :size="13" class="flip-rtl" />
            </button>
            <span class="text-[11.5px] text-stone-600 tabular-nums px-1.5">{{ page }} / {{ Math.max(1, Math.ceil(total / pageSize)) }}</span>
            <button class="pager-btn" :disabled="page * pageSize >= total" @click="page++; load(true)">
              <Icon name="chevron-right" :size="13" class="flip-rtl" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="text-[11px] text-stone-400 text-center mt-4">
      {{ t("trk.footnote") }}
    </div>
  </div>
</template>

<script setup>
import { computed, ref, h, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import {
  TRACK_STATES, TRACK_LABEL, SLA, SLA_LABEL, CARRIER, fmtMAD,
} from "@/lib/handoffData";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const router = useRouter();
const { t } = useI18n();
const t2 = t;
function trackLabel(k) { return t("track." + k, TRACK_LABEL[k] || k); }

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
    trackLabel(props.state),
  ]);
};
const SlaBadge = (props) => {
  const t = SLA[props.sla] || SLA.ontrack;
  return h("span", {
    class: ["inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap", t.txt, t.bg, t.ring],
  }, [
    h("span", { class: ["w-1.5 h-1.5 rounded-full", t.dot] }),
    t2("sla." + ({ ontrack: "onTrack", atrisk: "atRisk" }[props.sla] || props.sla), SLA_LABEL[props.sla] || props.sla),
  ]);
};

// ── server-driven board state ──────────────────────────────────────
const mode = ref("loading"); // loading → skeleton · live · error
const loadError = ref("");
const loading = ref(false);
const parcels = ref([]);
const counts = ref({});
const total = ref(0);
const stateF = ref("");
const daysF = ref(14);
const q = ref("");
const page = ref(1);
const pageSize = 30;
const tlParcel = ref(null);
const updatedAt = ref(Date.now());
let searchTimer = null;

async function load(keepPage = false) {
  if (!keepPage) page.value = 1;
  loading.value = true;
  // No fallback data. This screen answers "where is this customer's parcel"
  // and an agent reads it out loud on the phone. Inventing a row here means
  // telling a real person their parcel was delivered because the API blinked.
  // An error the agent can see is the only honest failure mode.
  try {
    const live = await api("shipping.tracking", {
      days: daysF.value, state: stateF.value || undefined,
      q: q.value.trim() || undefined,
      limit: pageSize, offset: (page.value - 1) * pageSize,
    });
    mode.value = "live";
    loadError.value = "";
    parcels.value = live.parcels || [];
    counts.value = live.counts || {};
    total.value = live.total ?? (live.parcels || []).length;
    updatedAt.value = Date.now();
  } catch (e) {
    mode.value = "error";
    loadError.value = String(e.message || e);
    parcels.value = [];
    counts.value = {};
    total.value = 0;
  }
  loading.value = false;
}
onMounted(load);

function setState(s) {
  stateF.value = s;
  load();
}
function onSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => load(), 350);
}
const updatedAgo = computed(() => {
  const s = Math.round((Date.now() - updatedAt.value) / 1000);
  if (s < 5) return t("ordersPg.justNow");
  if (s < 60) return t("ordersPg.agoS").replace("{n}", s);
  return t("ordersPg.agoM").replace("{n}", Math.round(s / 60));
});

const isBad = (track) => track === "exception" || track === "failed";

// Moroccan mobile → wa.me international format (0612… → 212612…).
function waLink(phone) {
  let d = (phone || "").replace(/\D/g, "");
  if (d.startsWith("00")) d = d.slice(2);
  if (d.startsWith("0")) d = "212" + d.slice(1);
  else if (!d.startsWith("212")) d = "212" + d;
  return `https://wa.me/${d}`;
}
function openOrder(no) {
  router.push({ name: "OrderDetail", params: { name: String(no).replace("#", "") } });
}

// ── parcel timeline (honest: only shipped + last-update are known) ──
const timelineStats = computed(() => {
  const p = tlParcel.value;
  if (!p) return [];
  return [
    [t("trk.awb"), p.awb || "—"],
    [t("trk.trackingNo"), p.trackNo || "—"],
    [t("trk.value"), fmtMAD(p.value) + " MAD"],
    [t("trk.age"), t("trk.sinceShipped").replace("{n}", p.days)],
  ];
});
const timelineSteps = computed(() => {
  const p = tlParcel.value;
  if (!p) return [];
  const reached = { pending: 0, pickedup: 1, intransit: 1, outfordelivery: 2, delivered: 3, exception: 3, failed: 3, return: 3 }[p.track] ?? 0;
  const final = p.track === "delivered"
    ? { label: trackLabel("delivered") }
    : isBad(p.track)
      ? { label: trackLabel(p.track), bad: true }
      : { label: trackLabel("delivered") };
  return [
    { label: t("trk.shippedHanded").replace("{carrier}", p.carrier), at: p.posted, done: true },
    { label: trackLabel("intransit"), at: reached === 1 ? p.updated : "", done: reached >= 1 },
    { label: trackLabel("outfordelivery"), at: reached === 2 ? p.updated : "", done: reached >= 2 },
    { ...final, at: reached >= 3 ? p.updated : "", done: reached >= 3 },
  ];
});
</script>
