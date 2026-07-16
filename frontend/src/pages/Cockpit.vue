<template>
  <div class="overflow-y-auto">
    <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
      <!-- Title + actions -->
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t('px.ckp.title') }}</h1>
          <p class="text-[13px] text-stone-500 mt-0.5">
            Live across the whole floor · {{ WAREHOUSE }}, {{ CITY }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <label
            class="relative inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors cursor-pointer"
          >
            <Icon name="calendar" :size="15" /> {{ dateLabel }}
            <input
              type="date"
              class="absolute inset-0 opacity-0 cursor-pointer"
              :max="todayStr"
              :value="selectedDate"
              @change="onDateChange"
            />
          </label>
          <button
            class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors disabled:opacity-50"
            :disabled="exporting"
            @click="onExport"
          >
            <Icon name="file-text" :size="15" /> {{ exporting ? "…" : "Export" }}
          </button>
        </div>
      </div>

      <!-- Skeleton until the live snapshot arrives — never demo numbers -->
      <template v-if="loading && !isLive">
        <div class="h-[88px] rounded-2xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
        <div class="h-[180px] rounded-2xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div v-for="n in 4" :key="n" class="h-[110px] rounded-xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-4">
          <div class="h-[360px] rounded-xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
          <div class="h-[360px] rounded-xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
        </div>
      </template>

      <!-- Outage. Zeros are not an all-clear: nothing was measured. -->
      <div v-else-if="loadError" class="rounded-2xl bg-white ring-1 ring-rose-200/70 p-8 text-center">
        <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
        <div class="text-[13px] font-semibold text-stone-800">{{ t("common.loadFail") }}</div>
        <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[420px] mx-auto break-words">{{ loadError }}</div>
        <button
          class="mt-4 h-8 px-3 inline-flex items-center gap-1.5 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 hover:ring-stone-300 transition-all"
          @click="load()"
        >
          <Icon name="refresh-cw" :size="14" />{{ t('common.refresh') }}
        </button>
      </div>

      <template v-else>
      <!-- Needs attention band -->
      <div
        class="rounded-2xl p-5 ring-1 flex items-center gap-4"
        :class="needsAttention
          ? 'bg-gradient-to-r from-rose-50 to-white ring-rose-200/70'
          : 'bg-gradient-to-r from-emerald-50 to-white ring-emerald-200/70'"
      >
        <div
          class="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 text-white"
          :class="needsAttention ? 'bg-rose-500' : 'bg-emerald-500'"
        >
          <Icon :name="needsAttention ? 'alert-circle' : 'check-circle'" :size="24" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-[15px] font-semibold text-stone-900">
            {{ needsAttention ? 'Needs attention' : 'All green' }}
          </div>
          <div class="text-[12.5px] text-stone-600 mt-0.5">
            <template v-if="needsAttention">
              {{ cockpit.breaches }} breached · {{ cockpit.atRisk }} at risk now
            </template>
            <template v-else>Everything is on track across the floor.</template>
          </div>
        </div>
        <button
          v-if="needsAttention"
          class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg text-[13px] font-semibold text-white bg-rose-600 hover:bg-rose-700 transition-colors"
          @click="openBreached"
        >
          Breached orders <Icon name="chevron-right" :size="16" />
        </button>
      </div>

      </template>

      <!-- Breached orders panel -->
      <Teleport to="body">
        <div v-if="breachedOpen" class="fixed inset-0 z-50 flex justify-end">
          <div class="absolute inset-0 bg-stone-900/30" @click="breachedOpen = false" />
          <div class="relative w-full max-w-lg h-full bg-white shadow-2xl flex flex-col animate-fade-in">
            <header class="px-5 py-4 border-b border-stone-100 flex items-center justify-between">
              <div>
                <h3 class="text-[15px] font-semibold text-stone-900">Open SLA problems</h3>
                <p class="text-[12px] text-stone-500 mt-0.5">
                  Breached & at-risk parcels not yet delivered · last 14 days
                </p>
              </div>
              <button class="w-8 h-8 rounded-lg hover:bg-stone-100 flex items-center justify-center" @click="breachedOpen = false">
                <Icon name="x" :size="16" />
              </button>
            </header>
            <div class="flex-1 overflow-y-auto">
              <div v-if="breachedLoading" class="p-8 text-center text-[13px] text-stone-400">Loading…</div>
              <div v-else-if="breachedError" class="p-8 text-center">
                <Icon name="alert-triangle" :size="20" class="mx-auto mb-2 text-rose-500" />
                <div class="text-[13px] font-semibold text-stone-800">{{ t("common.loadFail") }}</div>
                <div class="text-[11.5px] text-stone-400 font-mono mt-1 break-words">{{ breachedError }}</div>
              </div>
              <div v-else-if="!breachedRows.length" class="p-8 text-center text-[13px] text-stone-400">Nothing open. All clear.</div>
              <button
                v-for="r in breachedRows"
                :key="r.dn"
                class="w-full text-start px-5 py-3 border-b border-stone-50 hover:bg-stone-50 transition-colors"
                @click="openBreachedOrder(r)"
              >
                <div class="flex items-center justify-between gap-3">
                  <span class="text-[13px] font-semibold text-stone-900 tabular-nums">{{ r.order || r.dn }}</span>
                  <span
                    class="px-2 h-5 inline-flex items-center rounded-full text-[10.5px] font-semibold"
                    :class="r.sla === 'Breached' ? 'bg-rose-50 text-rose-700 ring-1 ring-rose-200' : 'bg-amber-50 text-amber-700 ring-1 ring-amber-200'"
                  >{{ r.sla }}</span>
                </div>
                <div class="flex items-center justify-between gap-3 mt-1">
                  <span class="text-[12px] text-stone-500 truncate">{{ r.customer }} · {{ r.city }}</span>
                  <span class="text-[11px] text-stone-400 whitespace-nowrap">{{ r.track || "—" }} · {{ r.date }}</span>
                </div>
              </button>
            </div>
            <footer class="px-5 py-3 border-t border-stone-100 flex items-center justify-between">
              <span class="text-[12px] text-stone-500 tabular-nums">{{ breachedRows.length }} parcels</span>
              <button
                class="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-[12.5px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
                @click="onExport"
              >
                <Icon name="file-text" :size="14" /> Export CSV
              </button>
            </footer>
          </div>
        </div>
      </Teleport>

      <!-- Today's flow -->
      <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div class="flex items-center justify-between gap-4 flex-wrap">
          <div class="flex items-center gap-1.5">
            <span class="text-[13px] font-semibold text-stone-900">Today's flow</span>
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl ring-1"
               :class="cockpit.cutoffLate ? 'bg-rose-50 ring-rose-200' : 'bg-emerald-50 ring-emerald-200'">
            <Icon name="clock" :size="14" :class="cockpit.cutoffLate ? 'text-rose-500' : 'text-emerald-600'" />
            <span class="text-[11.5px] text-stone-500">{{ cockpit.cutoffLate ? 'Past cutoff' : 'To cutoff' }}</span>
            <span class="text-[14px] font-bold tabular-nums"
                  :class="cockpit.cutoffLate ? 'text-rose-600' : 'text-emerald-700'">{{ cockpit.pastCutoff }}</span>
            <span class="text-[11px] text-stone-400">· {{ cockpit.cutoff }}</span>
          </div>
        </div>

        <div class="grid grid-cols-4 gap-3 mt-3.5">
          <div
            v-for="c in flowCells"
            :key="c.label"
            class="text-start rounded-xl p-3 ring-1 ring-stone-200/60"
          >
            <div class="text-[24px] font-semibold tabular-nums leading-none" :class="c.tone">
              {{ c.value }}
            </div>
            <div class="text-[11px] text-stone-500 mt-1.5">{{ c.label }}</div>
          </div>
        </div>

        <div class="mt-3">
          <div class="flex items-center justify-between text-[11px] mb-1">
            <span class="text-stone-500">
              {{ cockpit.beforeCutoff }} / {{ cockpit.ordersIn }} before {{ cockpit.cutoff }} cutoff
            </span>
            <span class="font-semibold text-emerald-600 tabular-nums">{{ cockpit.cutoffPct }}%</span>
          </div>
          <div class="h-2 rounded-full bg-stone-100 overflow-hidden">
            <div
              class="h-full rounded-full bg-emerald-500"
              :style="{ width: cockpit.cutoffPct + '%', transition: 'width .5s cubic-bezier(.16,1,.3,1)' }"
            />
          </div>
        </div>
      </div>

      <!-- KPI row -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div
          v-for="k in kpis"
          :key="k.label"
          class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition-all"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-lg flex items-center justify-center" :class="k.toneClass">
                <Icon :name="k.icon" :size="15" />
              </span>
              <span class="text-[12px] font-medium text-stone-500">{{ k.label }}</span>
            </div>
            <span
              v-if="k.trend != null"
              class="inline-flex items-center gap-0.5 text-[11px] font-semibold tabular-nums"
              :class="k.good ? 'text-emerald-600' : 'text-rose-600'"
            >
              <Icon :name="k.trend > 0 ? 'chevron-up' : 'chevron-down'" :size="12" />
              {{ Math.abs(k.trend) }}%
            </span>
          </div>
          <div class="mt-2.5 flex items-end justify-between gap-2">
            <div class="text-[26px] leading-none font-semibold text-stone-900 tracking-[-0.01em] tabular-nums">
              {{ k.value }}<span v-if="k.unit" class="text-[13px] font-medium text-stone-400 ms-1">{{ k.unit }}</span>
            </div>
            <Sparkline :data="k.spark" :width="64" :height="26" stroke="#ef4444" />
          </div>
        </div>
      </div>

      <!-- Pipeline + Leaderboard -->
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <!-- Pipeline (spans 2) -->
        <section
          class="xl:col-span-2 bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden"
        >
          <header class="flex items-center justify-between gap-3 px-4 py-3 border-b border-stone-100">
            <div class="min-w-0">
              <h3 class="text-[13.5px] font-semibold text-stone-900 truncate">Pipeline</h3>
              <p class="text-[11.5px] text-stone-500 mt-0.5 truncate">
                {{ pipelineTotal }} orders · {{ pipeline.length }} stages
              </p>
            </div>
          </header>
          <div class="p-4">
            <div class="space-y-1.5">
              <component
                :is="isBoardKey(p.key) ? 'button' : 'div'"
                v-for="p in pipeline"
                :key="p.key"
                class="w-full flex items-center gap-3 group text-start"
                @click="goStage(p.key)"
              >
                <div class="w-[110px] flex items-center gap-2 flex-shrink-0">
                  <span class="w-2 h-2 rounded-full" :style="{ background: stageHex(p.key) }" />
                  <span class="text-[12px] font-medium text-stone-700 truncate group-hover:text-stone-900">{{ stageLabelOf(p.key) }}</span>
                </div>
                <div class="flex-1 h-7 rounded-lg bg-stone-50 overflow-hidden relative">
                  <div
                    class="h-full rounded-lg flex items-center px-2.5 transition-all group-hover:brightness-95 ring-1 ring-inset"
                    :style="{ width: barWidth(p.count) + '%', background: stageHex(p.key) + '1c', '--tw-ring-color': stageHex(p.key) + '3a' }"
                  >
                    <span class="text-[11.5px] font-semibold tabular-nums" :style="{ color: stageHex(p.key) }">{{ p.count }}</span>
                  </div>
                </div>
                <div class="w-[92px] text-end text-[11.5px] text-stone-500 tabular-nums flex-shrink-0">
                  {{ fmtMAD(p.value) }} <span class="text-[10px] text-stone-400">MAD</span>
                </div>
              </component>
            </div>
          </div>
        </section>

        <!-- Team leaderboard -->
        <section
          class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden"
        >
          <header class="flex items-center justify-between gap-3 px-4 py-3 border-b border-stone-100">
            <h3 class="text-[13.5px] font-semibold text-stone-900 truncate">Team leaderboard</h3>
            <button
              class="text-[11.5px] font-semibold text-[var(--accent-700)] hover:underline"
              @click="_router.push({ name: 'Team' })"
            >View all</button>
          </header>
          <div class="p-2">
            <div
              v-for="(p, i) in leaderboard"
              :key="p.id"
              class="flex items-center gap-2.5 px-2 py-2 rounded-lg"
              :class="i === 0 ? 'bg-[var(--accent-50)]/60' : 'hover:bg-stone-50'"
            >
              <span
                class="w-5 text-center text-[12px] font-bold tabular-nums"
                :class="i === 0 ? 'text-[var(--accent-700)]' : 'text-stone-400'"
              >{{ p.rank }}</span>
              <div
                class="rounded-lg flex items-center justify-center font-semibold flex-shrink-0 ring-1 ring-black/[0.04]"
                :style="avatarStyle(pickerName(p), 30)"
              >{{ getInitial(pickerName(p)) }}</div>
              <div class="min-w-0 flex-1 leading-tight">
                <div class="text-[12.5px] font-medium text-stone-900 truncate flex items-center gap-1">
                  {{ pickerShort(p) }}<span v-if="i === 0" class="text-[10px]">⭐</span>
                </div>
                <div class="text-[10.5px] text-stone-500 tabular-nums">{{ p.picks }} orders · {{ p.avg }}</div>
              </div>
              <Sparkline :data="p.trend" :width="48" :height="18" stroke="#ef4444" />
              <div class="text-end w-[52px]">
                <div class="text-[12.5px] font-semibold text-stone-900 tabular-nums">{{ p.sla }}%</div>
                <div class="text-[9.5px] text-stone-400 uppercase tracking-wide">Same-day</div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, h, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import {
  STAGE, STAGE_LABEL, byId, fmtMAD, getInitial, WAREHOUSE, CITY,
} from "@/lib/handoffData.js";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useRouter } from "vue-router";
import { useToast } from "@/composables/useToast";

const { success } = useToast();

// NO demo data: skeletons render until `performance.cockpit` resolves, then
// real numbers (or honest zeros) — never plausible fake ones.
const EMPTY_COCKPIT = {
  ordersIn: 0, shipped: 0, printed: 0, toShip: 0, inTransit: 0, breaches: 0,
  atRisk: 0, returns: 0, attention: 0, totalOrders: 0, sameDayPct: 0,
  cutoff: "17:00", beforeCutoff: 0, cutoffPct: 0, pastCutoff: "—",
  sameDayTrend: [], breachTrend: [], atRiskTrend: [], transitTrend: [],
};
const cockpit = ref({ ...EMPTY_COCKPIT });
const { t } = useI18n();
const pipeline = ref([]);
const leaderboard = ref([]);
const loading = ref(true);

// Live time-vs-cutoff, computed client-side so it's always current.
function cutoffDelta(cutoff = "14:00") {
  const [h, m] = cutoff.split(":").map(Number);
  const now = new Date();
  const cut = new Date(now); cut.setHours(h, m, 0, 0);
  const diff = Math.abs(now - cut) / 1000;
  const hh = String(Math.floor(diff / 3600)).padStart(2, "0");
  const mm = String(Math.floor((diff % 3600) / 60)).padStart(2, "0");
  const ss = String(Math.floor(diff % 60)).padStart(2, "0");
  return { late: now > cut, text: `${hh}:${mm}:${ss}` };
}

const isLive = ref(false);
const loadError = ref("");

// ── Date scope ──────────────────────────────────────────────────────
const todayStr = new Date().toISOString().slice(0, 10);
const selectedDate = ref(todayStr);
const dateLabel = computed(() => {
  if (selectedDate.value === todayStr) return "Today";
  const d = new Date(selectedDate.value + "T00:00:00");
  const yest = new Date(); yest.setDate(yest.getDate() - 1);
  if (selectedDate.value === yest.toISOString().slice(0, 10)) return "Yesterday";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
});

async function load() {
  loading.value = true;
  // A failed load must never read as "All green". EMPTY_COCKPIT is all zeros,
  // so breaches=0 -> needsAttention=false -> the manager sees a green card
  // saying everything is on track, when in fact nothing was measured.
  try {
    const live = await api("performance.cockpit", { date: selectedDate.value });
    if (!live || !live.summary) throw new Error("Empty response");
    isLive.value = true;
    loadError.value = "";
    const delta = live.summary.isToday
      ? cutoffDelta(live.summary.cutoff || "17:00") : null;
    cockpit.value = {
      ...EMPTY_COCKPIT,
      ...live.summary,
      pastCutoff: delta ? delta.text : "—",
      cutoffLate: !!(delta && delta.late),
      sameDayTrend: [], breachTrend: [], atRiskTrend: [], transitTrend: [],
    };
    pipeline.value = live.pipeline || [];
    leaderboard.value = live.leaderboard || [];
  } catch (e) {
    isLive.value = false;
    loadError.value = String(e.message || e);
  }
  loading.value = false;
}

function onDateChange(e) {
  const v = e.target.value;
  if (!v || v === selectedDate.value) return;
  selectedDate.value = v;
  load();
}

onMounted(load);

// ── Breached orders panel ───────────────────────────────────────────
const breachedOpen = ref(false);
const breachedLoading = ref(false);
const breachedRows = ref([]);
const breachedError = ref("");

async function openBreached() {
  breachedOpen.value = true;
  if (breachedRows.value.length) return;
  breachedLoading.value = true;
  breachedError.value = "";
  try {
    breachedRows.value = (await api("performance.breached_list")) || [];
  } catch (e) {
    // Without this the empty array falls through to "Nothing open. All clear."
    breachedError.value = String(e.message || e);
  } finally {
    breachedLoading.value = false;
  }
}

function openBreachedOrder(r) {
  if (!r.order) return;
  breachedOpen.value = false;
  _router.push({ name: "OrderDetail", params: { name: r.order.replace("#", "") } });
}

const needsAttention = computed(() => cockpit.value.breaches > 0);
// Board stage keys (live funnel) — hex-toned + i18n'd + clickable → the board.
const BOARD_HEX = {
  to_pick: "#d97706", picking: "#0891b2", prepared: "#7c3aed", ready: "#4f46e5",
  shipped: "#059669", delivered: "#10b981", to_return: "#ea580c", returned: "#78716c",
};
// Demo design keys keep their original tones.
const DEMO_HEX = {
  pending: "#d97706", picked: "#ea580c", labelgen: "#7c3aed", label: "#4f46e5",
  transit: "#0891b2", shipped: "#059669", delivered: "#10b981", returned: "#78716c", picking: "#0891b2",
};
const isBoardKey = (k) => k in BOARD_HEX && pipeline.value.some((p) => p.key === "to_pick");
function stageHex(k) { return BOARD_HEX[k] && isBoardKey(k) ? BOARD_HEX[k] : (DEMO_HEX[k] || "#a8a29e"); }
const _router = useRouter();
function goStage(k) {
  if (isBoardKey(k)) _router.push({ name: "Pipeline", query: { stage: k } });
}
function stageLabelOf(k) {
  if (isBoardKey(k)) return t("ordersPg.stages." + k + ".label");
  return STAGE_LABEL[k] || k;
}

const pipelineTotal = computed(() => pipeline.value.reduce((a, p) => a + p.count, 0));
const pipelineMax = computed(() => Math.max(...pipeline.value.map((p) => p.count), 1));

const person = (id) => byId(id);
// Prefer the backend-provided display name (real User.full_name or a
// prettified email) over the static demo TEAM map, which shows raw emails
// for anyone it doesn't know.
const pickerName = (p) => p.name || person(p.id).name;
const pickerShort = (p) => p.short || person(p.id).short;

function barWidth(count) {
  return Math.max(6, (count / pipelineMax.value) * 100);
}

const exporting = ref(false);

async function onExport() {
  // Real export: the open breached/at-risk parcels as a CSV download.
  exporting.value = true;
  try {
    const rows = breachedRows.value.length
      ? breachedRows.value
      : ((await api("performance.breached_list")) || []);
    if (!breachedRows.value.length) breachedRows.value = rows;
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [
      ["order", "delivery_note", "awb", "customer", "city", "sla", "carrier_status", "date"].join(","),
      ...rows.map((r) => [r.order, r.dn, r.awb, r.customer, r.city, r.sla, r.track, r.date].map(esc).join(",")),
    ].join("\n");
    const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `sla-problems-${todayStr}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    success?.(`Exported ${rows.length} parcels`);
  } finally {
    exporting.value = false;
  }
}

const flowCells = computed(() => [
  { label: "Orders in", value: cockpit.value.ordersIn, tone: "text-stone-900" },
  { label: "Shipped", value: cockpit.value.shipped, tone: "text-emerald-600" },
  { label: "Printed", value: cockpit.value.printed, tone: "text-violet-600" },
  { label: "To ship", value: cockpit.value.toShip, tone: "text-amber-600" },
]);

// Trend %s are demo-only; on live data they're hidden until real history exists.
const kpis = computed(() => [
  { label: "Shipped same-day", icon: "zap", toneClass: "text-emerald-600 bg-emerald-50", value: cockpit.value.sameDayPct, unit: "%", trend: isLive.value ? null : 4, good: true, spark: cockpit.value.sameDayTrend },
  { label: "SLA breaches", icon: "alert-circle", toneClass: "text-rose-600 bg-rose-50", value: cockpit.value.breaches, unit: "", trend: isLive.value ? null : -2, good: true, spark: cockpit.value.breachTrend },
  { label: "At risk now", icon: "clock", toneClass: "text-amber-600 bg-amber-50", value: cockpit.value.atRisk, unit: "", trend: isLive.value ? null : 1, good: false, spark: cockpit.value.atRiskTrend },
  { label: "In Transit", icon: "globe", toneClass: "text-cyan-600 bg-cyan-50", value: cockpit.value.inTransit, unit: "", trend: isLive.value ? null : 6, good: true, spark: cockpit.value.transitTrend },
]);

// ── Avatar helpers (gradient-seeded, warm palette) ──────────────────
function avatarHue(name) {
  let hh = 0;
  for (let i = 0; i < (name || "").length; i++) hh = (hh * 31 + name.charCodeAt(i)) & 0xffff;
  return hh % 360;
}
function avatarStyle(name, size) {
  const hue = avatarHue(name);
  return {
    width: size + "px",
    height: size + "px",
    fontSize: size * 0.4 + "px",
    background: `linear-gradient(135deg, hsl(${hue} 60% 88%) 0%, hsl(${(hue + 40) % 360} 55% 78%) 100%)`,
    color: `hsl(${hue} 40% 28%)`,
  };
}

// ── Inline Sparkline (ported from primitives.jsx) ───────────────────
const Sparkline = {
  props: {
    data: { type: Array, default: () => [] },
    width: { type: Number, default: 72 },
    height: { type: Number, default: 24 },
    stroke: { type: String, default: "var(--accent-600)" },
  },
  setup(props) {
    return () => {
      const { data, width, height, stroke } = props;
      if (!data?.length || data.every((v) => v === 0)) {
        return h("svg", { width, height }, [
          h("line", {
            x1: 0, y1: height / 2, x2: width, y2: height / 2,
            stroke: "#e7e5e4", "stroke-width": "1.25", "stroke-dasharray": "2 2",
          }),
        ]);
      }
      const max = Math.max(...data), min = Math.min(...data);
      const range = Math.max(1, max - min);
      const step = width / (data.length - 1);
      const pts = data.map((v, i) => [i * step, height - ((v - min) / range) * (height - 4) - 2]);
      const d = pts.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
      const area = d + ` L ${width} ${height} L 0 ${height} Z`;
      const gid = "sg-" + Math.random().toString(36).slice(2, 8);
      return h("svg", { width, height }, [
        h("defs", [
          h("linearGradient", { id: gid, x1: "0", y1: "0", x2: "0", y2: "1" }, [
            h("stop", { offset: "0%", "stop-color": stroke, "stop-opacity": "0.22" }),
            h("stop", { offset: "100%", "stop-color": stroke, "stop-opacity": "0" }),
          ]),
        ]),
        h("path", { d: area, fill: `url(#${gid})` }),
        h("path", {
          d, fill: "none", stroke, "stroke-width": "1.5",
          "stroke-linecap": "round", "stroke-linejoin": "round",
        }),
        h("circle", { cx: pts[pts.length - 1][0], cy: pts[pts.length - 1][1], r: "2", fill: stroke }),
      ]);
    };
  },
};
</script>
