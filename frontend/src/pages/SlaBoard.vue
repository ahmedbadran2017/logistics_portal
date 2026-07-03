<template>
  <div class="overflow-y-auto">
    <div class="p-5 sm:p-6 space-y-4 max-w-[1400px] mx-auto animate-fade-in">
      <!-- Title -->
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">SLA</h1>
          <p class="text-[13px] text-stone-500 mt-0.5">Computed layer — wired to ship &amp; delivery dates</p>
        </div>
        <button
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          @click="info?.('SLA settings')"
        >
          <Icon name="settings" :size="15" /> SLA settings
        </button>
      </div>

      <!-- Hero target ring + KPIs -->
      <div class="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-4">
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] p-5 flex items-center gap-4">
          <SlaRing :pct="STATS.sameDay / 100" :size="84" :stroke="9" />
          <div>
            <div class="text-[28px] font-bold text-stone-900 tabular-nums leading-none">{{ STATS.sameDay }}%</div>
            <div class="text-[12px] text-stone-500 mt-1">Shipped same-day</div>
            <div class="text-[11px] text-stone-400 mt-2">Target {{ STATS.target }}% · avg ship {{ STATS.avgShipHrs }}h</div>
          </div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div
            v-for="k in kpis"
            :key="k.label"
            class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-7 h-7 rounded-lg flex items-center justify-center" :class="k.tone">
                  <Icon :name="k.icon" :size="15" />
                </span>
                <span class="text-[12px] font-medium text-stone-500">{{ k.label }}</span>
              </div>
              <span
                v-if="k.trend != null"
                class="inline-flex items-center gap-0.5 text-[11px] font-semibold tabular-nums text-emerald-600"
              >
                <Icon name="chevron-down" :size="12" /> {{ Math.abs(k.trend) }}%
              </span>
            </div>
            <div class="mt-2.5 flex items-end justify-between gap-2">
              <div class="text-[24px] leading-none font-semibold text-stone-900 tracking-[-0.01em] tabular-nums">
                {{ k.value }}<span v-if="k.unit" class="text-[13px] font-medium text-stone-400 ms-0.5">{{ k.unit }}</span>
              </div>
              <Sparkline :data="k.spark" :width="60" :height="24" :stroke="k.stroke" />
            </div>
          </div>
        </div>
      </div>

      <!-- Delivery SLA -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden">
        <header class="flex items-center justify-between gap-3 px-4 py-3 border-b border-stone-100">
          <div class="min-w-0">
            <h3 class="text-[13.5px] font-semibold text-stone-900 truncate">Delivery SLA</h3>
            <p class="text-[11.5px] text-stone-500 mt-0.5 truncate">Carrier on-time promise</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[12px] text-stone-500">On-time delivery</span>
            <span class="text-[15px] font-bold text-emerald-600 tabular-nums">{{ DELIVERY.onTime }}%</span>
          </div>
        </header>
        <div class="p-4">
          <div class="text-[11px] font-medium text-stone-400 uppercase tracking-wide mb-2">Days remaining · open parcels</div>
          <div class="flex items-end gap-2 h-[120px]">
            <button
              v-for="b in DELIVERY.buckets"
              :key="b.key"
              class="flex-1 flex flex-col items-center gap-1.5 group"
              @click="openBucket(b)"
            >
              <span class="text-[12px] font-semibold tabular-nums" :class="b.txt">
                <CountUp :value="b.count" />
              </span>
              <div class="w-full flex items-end justify-center" style="height: 76px">
                <div
                  class="w-full max-w-[44px] rounded-t-md group-hover:opacity-80 transition-opacity"
                  :class="b.tone"
                  :style="{ height: (b.count / bucketMax * 100) + '%' }"
                />
              </div>
              <span class="text-[10.5px] text-stone-500 text-center leading-tight">{{ b.label }}</span>
            </button>
          </div>
        </div>
      </section>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- SLA hit-rate by stage -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden">
          <header class="px-4 py-3 border-b border-stone-100">
            <h3 class="text-[13.5px] font-semibold text-stone-900">SLA hit-rate by stage</h3>
          </header>
          <div class="p-4 space-y-2.5">
            <div v-for="r in BY_STAGE" :key="r.key" class="flex items-center gap-3">
              <span class="w-[96px] text-[12px] text-stone-700 truncate">{{ STAGE_LABEL[r.key] || r.key }}</span>
              <div class="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full rounded-full" :class="hitColor(r.hit)" :style="{ width: r.hit + '%' }" />
              </div>
              <span class="w-[40px] text-end text-[12px] font-semibold text-stone-800 tabular-nums">{{ r.hit }}%</span>
            </div>
          </div>
        </section>

        <!-- SLA hit-rate by picker -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden">
          <header class="px-4 py-3 border-b border-stone-100">
            <h3 class="text-[13.5px] font-semibold text-stone-900">SLA hit-rate by picker</h3>
          </header>
          <div class="p-2">
            <div v-for="p in LEADERBOARD" :key="p.id" class="flex items-center gap-2.5 px-2 py-1.5">
              <div
                class="rounded-lg flex items-center justify-center font-semibold flex-shrink-0 ring-1 ring-black/[0.04]"
                :style="avatarStyle(byId(p.id).name, 26)"
              >{{ getInitial(byId(p.id).name) }}</div>
              <span class="text-[12.5px] text-stone-800 flex-1">{{ byId(p.id).short }}</span>
              <div class="w-[90px] h-1.5 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full rounded-full" :class="hitColor(p.sla, true)" :style="{ width: p.sla + '%' }" />
              </div>
              <span class="w-[36px] text-end text-[12px] font-semibold text-stone-800 tabular-nums">{{ p.sla }}%</span>
            </div>
          </div>
        </section>
      </div>

      <!-- Breach & at-risk board -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden">
        <header class="flex items-center justify-between gap-3 px-4 py-3 border-b border-stone-100">
          <h3 class="text-[13.5px] font-semibold text-stone-900">Breach &amp; at-risk board</h3>
          <span class="inline-flex items-center gap-1.5 px-2.5 h-6 rounded-full text-[11px] font-semibold text-rose-700 bg-rose-50 ring-1 ring-rose-200">
            <span class="w-1.5 h-1.5 rounded-full bg-rose-500" />
            {{ breaches.length + atRisk.length }} active
          </span>
        </header>
        <div class="divide-y divide-stone-100">
          <button
            v-for="o in board"
            :key="o.no"
            class="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-stone-50 text-start transition-colors"
            @click="openOrder(o)"
          >
            <span class="font-mono text-[12px] font-semibold text-stone-900 w-[88px] flex-shrink-0 truncate">{{ o.no }}</span>
            <span class="text-[12.5px] text-stone-800 flex-1 truncate">{{ o.customer }}</span>
            <span class="text-[11px] text-stone-400 hidden md:block w-[120px] truncate">{{ o.zone }}</span>
            <span
              class="inline-flex items-center px-2 h-5 rounded-md text-[10.5px] font-medium ring-1"
              :class="[STAGE[o.stage]?.txt, STAGE[o.stage]?.bg, STAGE[o.stage]?.ring]"
            >{{ STAGE_LABEL[o.stage] || o.stage }}</span>
            <span
              class="inline-flex items-center gap-1 px-2 h-5 rounded-md text-[10.5px] font-medium ring-1"
              :class="[SLA[o.sla]?.txt, SLA[o.sla]?.bg, SLA[o.sla]?.ring]"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="SLA[o.sla]?.dot" />
              {{ SLA_LABEL[o.sla] || o.sla }}
            </span>
            <span v-if="o.mins > 0" class="text-[11px] text-stone-400 tabular-nums w-[52px] text-end">{{ o.mins }}m</span>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, h, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import {
  ORDERS, LEADERBOARD, STAGE, SLA, STAGE_LABEL, SLA_LABEL,
  byId, getInitial,
} from "@/lib/handoffData";
import { useToast } from "@/composables/useToast";

const router = useRouter();
const { info } = useToast();

// ── Computed SLA layer (inlined from data.jsx — not in handoffData exports) ──
const STATS = { sameDay: 87, breached: 2, atRisk: 4, deliveredLate: 18, avgShipHrs: 5.4, target: 95 };
const DELIVERY = {
  onTime: 89,
  buckets: [
    { key: "overdue", label: "Overdue",   count: 14, tone: "bg-rose-500",    txt: "text-rose-600" },
    { key: "today",   label: "Due today", count: 38, tone: "bg-amber-500",   txt: "text-amber-600" },
    { key: "d1",      label: "1 day",     count: 91, tone: "bg-cyan-500",    txt: "text-cyan-600" },
    { key: "d2",      label: "2 days",    count: 64, tone: "bg-emerald-400", txt: "text-emerald-600" },
    { key: "d3",      label: "3+ days",   count: 47, tone: "bg-emerald-500", txt: "text-emerald-600" },
  ],
};
const BY_STAGE = [
  { key: "pending", hit: 88 }, { key: "picking", hit: 92 }, { key: "picked", hit: 95 },
  { key: "label", hit: 90 }, { key: "shipped", hit: 87 }, { key: "transit", hit: 84 }, { key: "delivered", hit: 91 },
];

const bucketMax = computed(() => Math.max(...DELIVERY.buckets.map((b) => b.count)));

const breaches = computed(() => ORDERS.filter((o) => o.sla === "breached"));
const atRisk = computed(() => ORDERS.filter((o) => o.sla === "atrisk"));
const late = computed(() => ORDERS.filter((o) => o.sla === "late"));
const board = computed(() => [...breaches.value, ...atRisk.value, ...late.value]);

const kpis = [
  { label: "Breached", icon: "alert-circle", tone: "text-rose-600 bg-rose-50", value: STATS.breached, trend: -2, spark: [3, 2, 4, 3, 2, 1, 2], stroke: "#ef4444" },
  { label: "At Risk", icon: "clock", tone: "text-amber-600 bg-amber-50", value: STATS.atRisk, spark: [1, 2, 2, 3, 2, 2, 4], stroke: "#f59e0b" },
  { label: "Delivered Late", icon: "trending-up", tone: "text-violet-600 bg-violet-50", value: STATS.deliveredLate, spark: [22, 20, 19, 18, 20, 19, 18], stroke: "#8b5cf6" },
  { label: "Avg ship time", icon: "zap", tone: "text-emerald-600 bg-emerald-50", value: STATS.avgShipHrs, unit: "h", trend: -6, spark: [7, 6.5, 6, 5.8, 5.5, 5.4, 5.4], stroke: "#10b981" },
];

function hitColor(v, picker = false) {
  if (picker) return v >= 90 ? "bg-emerald-500" : v >= 85 ? "bg-amber-500" : "bg-rose-500";
  return v >= 92 ? "bg-emerald-500" : v >= 86 ? "bg-amber-500" : "bg-rose-500";
}

function openOrder(o) {
  router.push({ name: "OrderDetail", params: { name: o.no.replace("#", "") } });
}
function openBucket() {
  info?.("Filtered orders by SLA bucket");
}

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

// ── Inline SlaRing (donut gauge) ────────────────────────────────────
const SlaRing = {
  props: {
    pct: { type: Number, default: 0 },
    size: { type: Number, default: 84 },
    stroke: { type: Number, default: 9 },
  },
  setup(props) {
    return () => {
      const { size, stroke, pct } = props;
      const r = (size - stroke) / 2;
      const c = 2 * Math.PI * r;
      const off = c * (1 - Math.max(0, Math.min(1, pct)));
      return h("svg", { width: size, height: size, viewBox: `0 0 ${size} ${size}` }, [
        h("circle", { cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#e7e5e4", "stroke-width": stroke }),
        h("circle", {
          cx: size / 2, cy: size / 2, r, fill: "none", stroke: "#10b981", "stroke-width": stroke,
          "stroke-linecap": "round", "stroke-dasharray": c, "stroke-dashoffset": off,
          transform: `rotate(-90 ${size / 2} ${size / 2})`,
          style: "transition: stroke-dashoffset .7s cubic-bezier(.16,1,.3,1)",
        }),
      ]);
    };
  },
};

// ── Inline CountUp ──────────────────────────────────────────────────
const CountUp = {
  props: { value: { type: Number, default: 0 }, duration: { type: Number, default: 700 } },
  setup(props) {
    const shown = ref(0);
    onMounted(() => {
      const start = performance.now();
      const tick = (now) => {
        const p = Math.min(1, (now - start) / props.duration);
        const eased = 1 - Math.pow(1 - p, 3);
        shown.value = Math.round(props.value * eased);
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    return () => h("span", { class: "tabular-nums" }, shown.value);
  },
};

// ── Inline Sparkline (ported from primitives.jsx) ───────────────────
const Sparkline = {
  props: {
    data: { type: Array, default: () => [] },
    width: { type: Number, default: 60 },
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
      return h("svg", { width, height }, [
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
