<template>
  <div class="overflow-y-auto">
    <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
      <!-- Title -->
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">Floor board</h1>
          <p class="text-[13px] text-stone-500 mt-0.5">
            Live throughput across every station · {{ WAREHOUSE }}, {{ CITY }}
          </p>
        </div>
      </div>

      <!-- Hero throughput -->
      <div class="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-4">
        <div
          class="rounded-2xl ring-1 p-5"
          :class="pace >= 0.95
            ? 'ring-emerald-200 bg-gradient-to-br from-emerald-50/60 to-white'
            : 'ring-amber-200 bg-gradient-to-br from-amber-50/60 to-white'"
        >
          <div class="flex items-center justify-between">
            <span class="text-[12px] font-medium text-stone-500">Orders / hour</span>
            <span
              class="inline-flex items-center gap-1.5 px-2.5 h-6 rounded-full text-[11px] font-semibold ring-1"
              :class="pace >= 0.95
                ? 'text-emerald-700 bg-emerald-50 ring-emerald-200'
                : 'text-amber-700 bg-amber-50 ring-amber-200'"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="pace >= 0.95 ? 'bg-emerald-500' : 'bg-amber-500'" />
              {{ pace >= 0.95 ? 'On pace' : 'Behind pace' }}
            </span>
          </div>
          <div class="flex items-end gap-2 mt-2">
            <span class="text-[48px] font-bold text-stone-900 tabular-nums leading-none">
              <CountUp :value="ANDON.ordersPerHour" />
            </span>
            <span class="text-[14px] text-stone-400 mb-1.5">/ {{ ANDON.target }} target</span>
          </div>
          <!-- hourly sparkbars -->
          <div class="flex items-end gap-1.5 mt-4 h-16">
            <div
              v-for="(v, i) in ANDON.hourly"
              :key="i"
              class="flex-1 flex flex-col items-center gap-1"
            >
              <div
                class="w-full rounded-t bg-[var(--accent-400)]"
                :style="{ height: (v / hourlyMax * 100) + '%' }"
              />
              <span class="text-[9px] text-stone-400 tabular-nums">{{ v }}</span>
            </div>
          </div>
        </div>

        <!-- KPI cluster -->
        <div class="grid grid-cols-2 gap-3">
          <div
            v-for="k in kpis"
            :key="k.label"
            class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
          >
            <div class="flex items-center gap-2">
              <span class="w-7 h-7 rounded-lg flex items-center justify-center" :class="k.tone">
                <Icon :name="k.icon" :size="15" />
              </span>
              <span class="text-[12px] font-medium text-stone-500">{{ k.label }}</span>
            </div>
            <div class="mt-2.5 text-[24px] leading-none font-semibold text-stone-900 tracking-[-0.01em] tabular-nums">
              {{ k.value }}
            </div>
          </div>
        </div>
      </div>

      <!-- Station pipeline -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden">
        <header class="px-4 py-3 border-b border-stone-100">
          <h3 class="text-[13.5px] font-semibold text-stone-900">Stations</h3>
        </header>
        <div class="p-4">
          <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div
              v-for="s in ANDON.stations"
              :key="s.name"
              class="rounded-xl ring-1 p-4"
              :class="s.status === 'ok' ? 'ring-stone-200/70' : 'ring-amber-300 bg-amber-50/40'"
            >
              <div class="flex items-center justify-between">
                <span class="text-[12.5px] font-semibold text-stone-900">{{ s.name }}</span>
                <span
                  class="w-2 h-2 rounded-full"
                  :class="s.status === 'ok' ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'"
                />
              </div>
              <div class="text-[24px] font-bold text-stone-900 tabular-nums leading-none mt-2">
                <CountUp :value="s.rate" /><span class="text-[11px] text-stone-400 font-medium"> /hr</span>
              </div>
              <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden mt-2">
                <div
                  class="h-full rounded-full"
                  :class="s.status === 'ok' ? 'bg-emerald-500' : 'bg-amber-500'"
                  :style="{ width: Math.min(100, s.rate / s.target * 100) + '%' }"
                />
              </div>
              <div class="text-[10.5px] text-stone-400 mt-1 tabular-nums">Target {{ s.target }}/hr</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, h, ref, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { WAREHOUSE, CITY } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";

// ── Andon board snapshot (demo fallback — `performance.floor` overwrites) ──
const DEMO_ANDON = {
  ordersPerHour: 73, target: 80, packedToday: 412, shippedToday: 389, cutoffMin: 156,
  hourly: [38, 44, 52, 61, 58, 67, 73],
  stations: [
    { name: "Picking", rate: 78, target: 80, status: "ok" },
    { name: "Packing", rate: 61, target: 75, status: "warn" },
    { name: "Labeling", rate: 84, target: 80, status: "ok" },
    { name: "Shipping", rate: 70, target: 75, status: "ok" },
  ],
  laggingZone: "Cosmetic zone - JM",
};

const ANDON = ref({ ...DEMO_ANDON });

onMounted(async () => {
  const live = await liveOr(null, () => api("performance.floor"));
  if (live && Array.isArray(live.hours)) {
    ANDON.value = {
      ...ANDON.value, // stations / target / laggingZone stay demo
      ordersPerHour: live.perHour != null ? Number(live.perHour) : ANDON.value.ordersPerHour,
      packedToday: live.pickedToday != null ? Number(live.pickedToday) : ANDON.value.packedToday,
      shippedToday: live.shippedToday != null ? Number(live.shippedToday) : ANDON.value.shippedToday,
      ordersToday: live.ordersToday != null ? Number(live.ordersToday) : ANDON.value.ordersToday,
      hourly: live.hours.length ? live.hours.map((x) => Number(x.count) || 0) : ANDON.value.hourly,
    };
  }
});

const pace = computed(() => ANDON.value.ordersPerHour / (ANDON.value.target || 1));
const hourlyMax = computed(() => Math.max(...ANDON.value.hourly, 1));

const kpis = computed(() => [
  { label: "Packed today", icon: "tag", tone: "text-stone-500 bg-stone-100", value: ANDON.value.packedToday },
  { label: "Shipped today", icon: "send", tone: "text-cyan-600 bg-cyan-50", value: ANDON.value.shippedToday },
  { label: "Cutoff in", icon: "clock", tone: "text-violet-600 bg-violet-50", value: "2h 36m" },
  { label: "Lagging zone", icon: "alert-circle", tone: "text-amber-600 bg-amber-50", value: ANDON.value.laggingZone.replace(" zone - JM", "").replace(" - JM", "") },
]);

// ── Inline CountUp (ported from primitives.jsx) ─────────────────────
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
</script>
