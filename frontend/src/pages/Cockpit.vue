<template>
  <div class="overflow-y-auto">
    <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
      <!-- Title + actions -->
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">Floor cockpit</h1>
          <p class="text-[13px] text-stone-500 mt-0.5">
            Live across the whole floor · {{ WAREHOUSE }}, {{ CITY }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          >
            <Icon name="calendar" :size="15" /> Today
          </button>
          <button
            class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
            @click="onExport"
          >
            <Icon name="file-text" :size="15" /> Export
          </button>
        </div>
      </div>

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
        >
          Breached orders <Icon name="chevron-right" :size="16" />
        </button>
      </div>

      <!-- Today's flow -->
      <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div class="flex items-center justify-between gap-4 flex-wrap">
          <div class="flex items-center gap-1.5">
            <span class="text-[13px] font-semibold text-stone-900">Today's flow</span>
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl ring-1 bg-rose-50 ring-rose-200">
            <Icon name="clock" :size="14" class="text-rose-500" />
            <span class="text-[11.5px] text-stone-500">Past cutoff</span>
            <span class="text-[14px] font-bold tabular-nums text-rose-600">{{ cockpit.pastCutoff }}</span>
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
                {{ pipelineTotal }} orders · 9 stages
              </p>
            </div>
          </header>
          <div class="p-4">
            <div class="space-y-1.5">
              <div
                v-for="p in pipeline"
                :key="p.key"
                class="w-full flex items-center gap-3 group"
              >
                <div class="w-[110px] flex items-center gap-2 flex-shrink-0">
                  <span class="w-2 h-2 rounded-full" :class="STAGE[p.key].dot" />
                  <span class="text-[12px] font-medium text-stone-700 truncate">{{ STAGE_LABEL[p.key] }}</span>
                </div>
                <div class="flex-1 h-7 rounded-lg bg-stone-50 overflow-hidden relative">
                  <div
                    class="h-full ring-1 ring-inset rounded-lg flex items-center px-2.5 transition-all group-hover:brightness-95"
                    :class="[STAGE[p.key].bg, STAGE[p.key].ring]"
                    :style="{ width: barWidth(p.count) + '%' }"
                  >
                    <span class="text-[11.5px] font-semibold tabular-nums" :class="STAGE[p.key].txt">{{ p.count }}</span>
                  </div>
                </div>
                <div class="w-[92px] text-end text-[11.5px] text-stone-500 tabular-nums flex-shrink-0">
                  {{ fmtMAD(p.value) }} <span class="text-[10px] text-stone-400">MAD</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Team leaderboard -->
        <section
          class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden"
        >
          <header class="flex items-center justify-between gap-3 px-4 py-3 border-b border-stone-100">
            <h3 class="text-[13.5px] font-semibold text-stone-900 truncate">Team leaderboard</h3>
            <button class="text-[11.5px] font-semibold text-[var(--accent-700)]">View all</button>
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
                :style="avatarStyle(person(p.id).name, 30)"
              >{{ getInitial(person(p.id).name) }}</div>
              <div class="min-w-0 flex-1 leading-tight">
                <div class="text-[12.5px] font-medium text-stone-900 truncate flex items-center gap-1">
                  {{ person(p.id).short }}<span v-if="i === 0" class="text-[10px]">⭐</span>
                </div>
                <div class="text-[10.5px] text-stone-500 tabular-nums">{{ p.picks }} orders · {{ p.avg }}</div>
              </div>
              <Sparkline :data="p.trend" :width="48" :height="18" stroke="#ef4444" />
              <div class="text-end w-[40px]">
                <div class="text-[12.5px] font-semibold text-stone-900 tabular-nums">{{ p.sla }}%</div>
                <div class="text-[9.5px] text-stone-400 uppercase tracking-wide">SLA</div>
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
  STAGE, STAGE_LABEL, PIPELINE as DEMO_PIPELINE, LEADERBOARD as DEMO_LEADERBOARD, COCKPIT as DEMO_COCKPIT,
  byId, fmtMAD, getInitial, WAREHOUSE, CITY,
} from "@/lib/handoffData.js";
import { api, liveOr } from "@/lib/resource";
import { useToast } from "@/composables/useToast";

const { success } = useToast();

// Live-or-demo data. `performance.cockpit` fills these once the app is installed;
// missing fields (e.g. sparkline trends) keep their demo values so nothing breaks.
const cockpit = ref(DEMO_COCKPIT);
const pipeline = ref(DEMO_PIPELINE);
const leaderboard = ref(DEMO_LEADERBOARD);

// Live time-vs-cutoff, computed client-side so it's always current.
function cutoffDelta(cutoff = "14:00") {
  const [h, m] = cutoff.split(":").map(Number);
  const now = new Date();
  const cut = new Date(now); cut.setHours(h, m, 0, 0);
  const diff = Math.abs(now - cut) / 1000;
  const hh = String(Math.floor(diff / 3600)).padStart(2, "0");
  const mm = String(Math.floor((diff % 3600) / 60)).padStart(2, "0");
  const ss = String(Math.floor(diff % 60)).padStart(2, "0");
  return (now > cut ? "+" : "−") + `${hh}:${mm}:${ss}`;
}

onMounted(async () => {
  const live = await liveOr(null, () => api("performance.cockpit"));
  if (live && live.summary) {
    cockpit.value = {
      ...DEMO_COCKPIT,
      ...live.summary,
      pastCutoff: cutoffDelta(live.summary.cutoff || "14:00"),
    };
    if (live.pipeline && live.pipeline.length) pipeline.value = live.pipeline;
    if (live.leaderboard && live.leaderboard.length) {
      leaderboard.value = live.leaderboard.map((r) => ({
        ...r,
        trend: r.trend && r.trend.length ? r.trend : (DEMO_LEADERBOARD.find((d) => d.id === r.id)?.trend || []),
      }));
    }
  }
});

const needsAttention = computed(() => cockpit.value.breaches > 0);
const pipelineTotal = computed(() => pipeline.value.reduce((a, p) => a + p.count, 0));
const pipelineMax = computed(() => Math.max(...pipeline.value.map((p) => p.count), 1));

const person = (id) => byId(id);

function barWidth(count) {
  return Math.max(6, (count / pipelineMax.value) * 100);
}

function onExport() {
  success?.("Export queued");
}

const flowCells = computed(() => [
  { label: "Orders in", value: cockpit.value.ordersIn, tone: "text-stone-900" },
  { label: "Shipped", value: cockpit.value.shipped, tone: "text-emerald-600" },
  { label: "Printed", value: cockpit.value.printed, tone: "text-violet-600" },
  { label: "To ship", value: cockpit.value.toShip, tone: "text-amber-600" },
]);

const kpis = computed(() => [
  { label: "Shipped same-day", icon: "zap", toneClass: "text-emerald-600 bg-emerald-50", value: cockpit.value.sameDayPct, unit: "%", trend: 4, good: true, spark: cockpit.value.sameDayTrend },
  { label: "SLA breaches", icon: "alert-circle", toneClass: "text-rose-600 bg-rose-50", value: cockpit.value.breaches, unit: "", trend: -2, good: true, spark: cockpit.value.breachTrend },
  { label: "At risk now", icon: "clock", toneClass: "text-amber-600 bg-amber-50", value: cockpit.value.atRisk, unit: "", trend: 1, good: false, spark: cockpit.value.atRiskTrend },
  { label: "In Transit", icon: "globe", toneClass: "text-cyan-600 bg-cyan-50", value: cockpit.value.inTransit, unit: "", trend: 6, good: true, spark: cockpit.value.transitTrend },
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
