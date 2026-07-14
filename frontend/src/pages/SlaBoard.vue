<template>
  <div class="overflow-y-auto">
    <div class="p-5 sm:p-6 space-y-4 max-w-[1400px] mx-auto animate-fade-in">
      <!-- Title -->
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">SLA</h1>
          <p class="text-[13px] text-stone-500 mt-0.5">
            Carrier delivery promise · last {{ data?.days || 14 }} days · live
          </p>
        </div>
        <button
          class="inline-flex items-center justify-center h-9 w-9 rounded-lg text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          :class="loading ? 'opacity-60 pointer-events-none' : ''"
          title="Refresh" aria-label="Refresh"
          @click="load"
        >
          <Icon name="refresh-cw" :size="14" :class="loading ? 'animate-spin' : ''" />
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading && !data" class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div v-for="n in 8" :key="n" class="h-[92px] rounded-xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
      </div>

      <template v-else-if="data">
        <!-- Hero on-time ring + KPIs -->
        <div class="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-4">
          <div class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] p-5 flex items-center gap-4">
            <SlaRing :pct="data.onTimePct / 100" :size="84" :stroke="9" />
            <div>
              <div class="text-[28px] font-bold text-stone-900 tabular-nums leading-none">{{ data.onTimePct }}%</div>
              <div class="text-[12px] text-stone-500 mt-1">Delivered on time</div>
              <div class="text-[11px] text-stone-400 mt-2 tabular-nums">
                {{ data.counts.delivered }} on time · {{ data.counts.deliveredLate }} late
              </div>
            </div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div v-for="k in kpis" :key="k.label"
                 class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
              <div class="flex items-center gap-2">
                <span class="w-7 h-7 rounded-lg flex items-center justify-center" :class="k.tone">
                  <Icon :name="k.icon" :size="15" />
                </span>
                <span class="text-[12px] font-medium text-stone-500">{{ k.label }}</span>
              </div>
              <div class="mt-2.5 text-[24px] leading-none font-semibold tracking-[-0.01em] tabular-nums"
                   :class="k.valueClass || 'text-stone-900'">
                {{ k.value }}<span v-if="k.unit" class="text-[13px] font-medium text-stone-400 ms-0.5">{{ k.unit }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Days-remaining buckets (open parcels) -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden">
          <header class="flex items-center justify-between gap-3 px-4 py-3 border-b border-stone-100">
            <div>
              <h3 class="text-[13.5px] font-semibold text-stone-900">Open parcels · time to promise</h3>
              <p class="text-[11.5px] text-stone-500 mt-0.5">Where every undelivered parcel stands against its expected date</p>
            </div>
            <span class="text-[12px] text-stone-500 tabular-nums">{{ openTotal }} open</span>
          </header>
          <div class="p-4">
            <div class="flex items-end gap-2 h-[120px]">
              <div v-for="b in data.buckets" :key="b.key" class="flex-1 flex flex-col items-center gap-1.5">
                <span class="text-[12px] font-semibold tabular-nums" :class="bucketTxt(b.key)">{{ b.count }}</span>
                <div class="w-full flex items-end justify-center" style="height: 76px">
                  <div class="w-full max-w-[44px] rounded-t-md" :class="bucketTone(b.key)"
                       :style="{ height: Math.max(3, b.count / bucketMax * 100) + '%' }" />
                </div>
                <span class="text-[10.5px] text-stone-500 text-center leading-tight">{{ b.label }}</span>
              </div>
            </div>
          </div>
        </section>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <!-- Worst cities -->
          <section class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden">
            <header class="px-4 py-3 border-b border-stone-100">
              <h3 class="text-[13.5px] font-semibold text-stone-900">Open breaches by city</h3>
            </header>
            <div class="p-4 space-y-2.5">
              <div v-if="!data.cities.length" class="text-[12.5px] text-emerald-600 text-center py-6 flex items-center justify-center gap-1.5">
                <Icon name="check-circle" :size="15" /> No open breaches
              </div>
              <div v-for="c in data.cities" :key="c.city" class="flex items-center gap-3">
                <span class="text-[12.5px] font-medium text-stone-800 w-[110px] truncate capitalize">{{ c.city }}</span>
                <div class="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden">
                  <div class="h-full rounded-full bg-rose-500"
                       :style="{ width: (c.breached / cityMax * 100) + '%' }" />
                </div>
                <span class="text-[12.5px] font-semibold text-rose-600 tabular-nums w-8 text-end">{{ c.breached }}</span>
              </div>
            </div>
          </section>

          <!-- Open breach list -->
          <section class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden">
            <header class="flex items-center justify-between px-4 py-3 border-b border-stone-100">
              <h3 class="text-[13.5px] font-semibold text-stone-900">Oldest open breaches</h3>
              <span class="text-[11.5px] text-stone-400 tabular-nums">{{ data.counts.breached }} total</span>
            </header>
            <div class="divide-y divide-stone-50">
              <div v-if="!data.breaches.length" class="text-[12.5px] text-emerald-600 text-center py-6 flex items-center justify-center gap-1.5">
                <Icon name="check-circle" :size="15" /> All clear
              </div>
              <button v-for="b in data.breaches" :key="b.dn"
                      class="w-full text-start px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50 transition-colors"
                      @click="openOrder(b.order)">
                <span class="font-mono text-[12px] font-semibold text-stone-900">{{ b.order || b.dn }}</span>
                <span class="text-[11.5px] text-stone-500 truncate flex-1">{{ b.customer }} · {{ b.city }}</span>
                <span class="text-[11px] text-stone-400">{{ b.track || "—" }}</span>
                <span class="text-[11px] text-rose-600 tabular-nums whitespace-nowrap">{{ b.date }}</span>
              </button>
            </div>
          </section>
        </div>
      </template>

      <!-- Error -->
      <div v-else class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
        <div class="text-[14px] font-semibold text-stone-900">Couldn't load SLA data</div>
        <button class="mt-3 h-9 px-4 rounded-lg text-[13px] font-semibold text-white bg-stone-800" @click="load">Retry</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, h, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";

const router = useRouter();
const data = ref(null);
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const res = await api("sla.board");
    if (res && res.counts) data.value = res;
  } catch (_) {
    /* error card shows */
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const openTotal = computed(() =>
  (data.value?.buckets || []).reduce((a, b) => a + b.count, 0));
const bucketMax = computed(() =>
  Math.max(...(data.value?.buckets || []).map((b) => b.count), 1));
const cityMax = computed(() =>
  Math.max(...(data.value?.cities || []).map((c) => c.breached), 1));

const kpis = computed(() => {
  const c = data.value?.counts || {};
  return [
    { label: "On track", icon: "check-circle", tone: "text-emerald-600 bg-emerald-50", value: c.onTrack ?? 0 },
    { label: "At risk", icon: "clock", tone: "text-amber-600 bg-amber-50", value: c.atRisk ?? 0, valueClass: c.atRisk ? "text-amber-600" : "text-stone-900" },
    { label: "Breached (open)", icon: "alert-circle", tone: "text-rose-600 bg-rose-50", value: c.breached ?? 0, valueClass: c.breached ? "text-rose-600" : "text-stone-900" },
    { label: "Shipped same-day", icon: "zap", tone: "text-violet-600 bg-violet-50", value: data.value?.sameDayPct ?? 0, unit: "%" },
  ];
});

function bucketTone(k) {
  return { ok: "bg-emerald-500", soon: "bg-amber-400", today: "bg-amber-500",
           over1: "bg-rose-400", over3: "bg-rose-600" }[k] || "bg-stone-300";
}
function bucketTxt(k) {
  return { ok: "text-emerald-600", soon: "text-amber-600", today: "text-amber-700",
           over1: "text-rose-500", over3: "text-rose-700" }[k] || "text-stone-500";
}
function openOrder(no) {
  if (!no) return;
  router.push({ name: "OrderDetail", params: { name: String(no).replace("#", "") } });
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
</script>
