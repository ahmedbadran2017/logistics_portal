<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <!-- Head -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Reports</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">Operational analytics · export-ready · {{ WAREHOUSE }}</p>
      </div>
      <button
        class="inline-flex items-center gap-1.5 h-9 px-3.5 text-[13px] font-medium rounded-lg bg-white text-stone-700 ring-1 ring-stone-200 hover:ring-stone-300 transition-colors whitespace-nowrap"
        @click="exp('All reports')">
        <Icon name="trending-up" :size="15" /> Export all
      </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Throughput -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="flex items-start justify-between gap-3 px-4 pt-4">
          <div>
            <div class="text-[13.5px] font-semibold text-stone-900">Throughput</div>
            <div class="text-[11.5px] text-stone-500 mt-0.5">Last 30 days</div>
          </div>
          <button class="inline-flex items-center gap-1 text-[11.5px] font-medium text-stone-500 hover:text-stone-900" @click="exp('Throughput')">
            <Icon name="file-text" :size="12" /> CSV
          </button>
        </div>
        <div class="p-4">
          <svg :viewBox="`0 0 ${cW} ${cH}`" class="w-full" :height="cH" preserveAspectRatio="none">
            <polyline :points="linePoints(tput)" fill="none" stroke="var(--accent-600)" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
          </svg>
        </div>
      </div>

      <!-- SLA trend -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="flex items-start justify-between gap-3 px-4 pt-4">
          <div>
            <div class="text-[13.5px] font-semibold text-stone-900">SLA trend</div>
            <div class="text-[11.5px] text-stone-500 mt-0.5">Last 30 days</div>
          </div>
          <button class="inline-flex items-center gap-1 text-[11.5px] font-medium text-stone-500 hover:text-stone-900" @click="exp('SLA trend')">
            <Icon name="file-text" :size="12" /> CSV
          </button>
        </div>
        <div class="p-4">
          <svg :viewBox="`0 0 ${cW} ${cH}`" class="w-full" :height="cH" preserveAspectRatio="none">
            <polyline :points="linePoints(sla30)" fill="none" stroke="#10b981" stroke-width="2"
                      stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
          </svg>
        </div>
      </div>

      <!-- Carrier performance -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="flex items-start justify-between gap-3 px-4 pt-4">
          <div>
            <div class="text-[13.5px] font-semibold text-stone-900">Carrier performance</div>
            <div class="text-[11.5px] text-stone-500 mt-0.5">{{ CARRIER }}</div>
          </div>
          <button class="inline-flex items-center gap-1 text-[11.5px] font-medium text-stone-500 hover:text-stone-900" @click="exp('Carrier performance')">
            <Icon name="file-text" :size="12" /> CSV
          </button>
        </div>
        <div class="p-4">
          <div class="space-y-2.5 pt-1">
            <div v-for="c in carrier" :key="c.label" class="flex items-center gap-3">
              <span class="w-[120px] text-[12px] text-stone-600 truncate">{{ c.label }}</span>
              <div class="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full rounded-full" :class="c.color" :style="{ width: c.value + '%' }" />
              </div>
              <span class="w-[38px] text-end text-[12px] font-semibold text-stone-800 tabular-nums">{{ c.value }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Zone heat -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="flex items-start justify-between gap-3 px-4 pt-4">
          <div>
            <div class="text-[13.5px] font-semibold text-stone-900">Zone activity heat</div>
            <div class="text-[11.5px] text-stone-500 mt-0.5">{{ RESTOCK.length }} zones</div>
          </div>
          <button class="inline-flex items-center gap-1 text-[11.5px] font-medium text-stone-500 hover:text-stone-900" @click="exp('Zone activity heat')">
            <Icon name="file-text" :size="12" /> CSV
          </button>
        </div>
        <div class="p-4">
          <div class="grid grid-cols-3 gap-2 pt-1">
            <div v-for="z in RESTOCK" :key="z.zone" class="rounded-lg p-2.5 text-center"
                 :style="{ background: `rgba(196,73,42,${0.08 + (z.skus / maxZone) * 0.32})` }">
              <div class="text-[15px] font-semibold text-stone-900 tabular-nums">{{ z.skus }}</div>
              <div class="text-[9.5px] text-stone-500 mt-0.5 truncate">{{ z.zone.replace(' - JM', '') }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Returns by reason -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="flex items-start justify-between gap-3 px-4 pt-4">
          <div>
            <div class="text-[13.5px] font-semibold text-stone-900">Returns by reason</div>
            <div class="text-[11.5px] text-stone-500 mt-0.5">Last 7 days</div>
          </div>
          <button class="inline-flex items-center gap-1 text-[11.5px] font-medium text-stone-500 hover:text-stone-900" @click="exp('Returns by reason')">
            <Icon name="file-text" :size="12" /> CSV
          </button>
        </div>
        <div class="p-4">
          <div class="space-y-2 pt-1">
            <div v-for="r in RETURN_BY_SKU" :key="r.sku" class="flex items-center gap-3">
              <span class="flex-1 text-[12px] text-stone-700 truncate">{{ r.reason }} · {{ r.name }}</span>
              <div class="w-[80px] h-1.5 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full bg-rose-500 rounded-full" :style="{ width: Math.min(100, r.rate * 8) + '%' }" />
              </div>
              <span class="text-[12px] font-semibold text-rose-600 tabular-nums w-[40px] text-end">{{ r.rate }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Channel performance -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="flex items-start justify-between gap-3 px-4 pt-4">
          <div>
            <div class="text-[13.5px] font-semibold text-stone-900">Channel performance</div>
            <div class="text-[11.5px] text-stone-500 mt-0.5">all orders</div>
          </div>
          <button class="inline-flex items-center gap-1 text-[11.5px] font-medium text-stone-500 hover:text-stone-900" @click="exp('Channel performance')">
            <Icon name="file-text" :size="12" /> CSV
          </button>
        </div>
        <div class="p-4">
          <div class="space-y-2.5 pt-1">
            <div v-for="ch in CHANNEL_MIX" :key="ch.key" class="flex items-center gap-3">
              <span class="w-[90px] text-[12px] text-stone-600">{{ CHANNELS[ch.key].label }}</span>
              <div class="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full rounded-full" :class="channelTone[CHANNELS[ch.key].tone]" :style="{ width: ch.pct + '%' }" />
              </div>
              <span class="w-[60px] text-end text-[11.5px] text-stone-500 tabular-nums">{{ ch.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import { WAREHOUSE, CARRIER, RESTOCK, RETURN_BY_SKU, CHANNEL_MIX, CHANNELS } from "@/lib/handoffData";

const { success, warn } = useToast();
const exp = () => warn("عرض تجريبي — لا يوجد ملف للتصدير");

// Fabricated 30-day series (matches prototype generators)
const sla30 = Array.from({ length: 30 }, (_, i) => Math.round(80 + 10 * Math.sin(i / 4) + i * 0.2));
const tput = Array.from({ length: 30 }, (_, i) => Math.round(180 + 40 * Math.sin(i / 3) + i));

const maxZone = Math.max(...RESTOCK.map((z) => z.skus));

const carrier = [
  { label: "Delivered", value: 91, color: "bg-emerald-500" },
  { label: "Out for delivery", value: 38, color: "bg-cyan-500" },
  { label: "Exceptions", value: 5, color: "bg-rose-500" },
  { label: "Failed attempts", value: 2, color: "bg-orange-500" },
];

const channelTone = { emerald: "bg-emerald-500", violet: "bg-violet-500", amber: "bg-amber-500", slate: "bg-stone-400", green: "bg-green-500" };

// Inline line chart geometry
const cW = 320;
const cH = 170;
function linePoints(data) {
  const vals = data && data.length ? data : [0];
  const max = Math.max(...vals);
  const min = Math.min(...vals);
  const range = max - min || 1;
  const step = vals.length > 1 ? cW / (vals.length - 1) : cW;
  const pad = 8;
  return vals
    .map((v, i) => `${i * step},${cH - pad - ((v - min) / range) * (cH - pad * 2)}`)
    .join(" ");
}
</script>
