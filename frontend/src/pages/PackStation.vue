<template>
  <div class="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
    <!-- header -->
    <div class="flex items-start justify-between gap-3 flex-wrap mb-4">
      <div>
        <h1 class="text-[19px] font-semibold text-stone-900 tracking-[-0.01em]">Pack station</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">Scan-verify packing · auto box &amp; label</p>
      </div>
      <span class="inline-flex items-center gap-1 px-2 h-[24px] rounded-md text-[11.5px] font-medium text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Mispack guard on
      </span>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-1.5 text-[11px] font-medium text-stone-500">
          <span v-html="k.icon" class="inline-flex" :class="k.txt" />
          <span>{{ k.label }}</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums leading-none mt-2">{{ k.value }}</div>
      </div>
    </div>

    <!-- fast lane banner -->
    <div class="rounded-2xl ring-1 ring-[var(--accent-300)]/50 bg-gradient-to-r from-[var(--accent-50)]/60 to-white p-4 mb-4 flex items-center gap-3">
      <span class="w-10 h-10 rounded-xl bg-[var(--accent-600)] text-white flex items-center justify-center flex-shrink-0">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>
      </span>
      <div class="flex-1 min-w-0">
        <div class="text-[13.5px] font-semibold text-stone-900">Single-item fast lane</div>
        <div class="text-[12px] text-stone-500">1-item orders · pick→pack→label in one step</div>
      </div>
      <span class="inline-flex items-center gap-1 px-1.5 h-[18px] rounded text-[10.5px] font-medium text-[var(--accent-700)] bg-[var(--accent-50)] ring-1 ring-[var(--accent-200)]">
        <span class="w-1.5 h-1.5 rounded-full bg-[var(--accent-600)]" />{{ fastReady }} ready
      </span>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-4">
      <!-- queue -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">Pack queue</div>
        <div class="p-2">
          <button
            v-for="o in queue"
            :key="o.order"
            class="w-full text-start rounded-xl px-3 py-2.5 flex items-center gap-2.5 transition-colors"
            :class="active?.order === o.order ? 'bg-[var(--accent-50)]/60 ring-1 ring-[var(--accent-200)]' : 'hover:bg-stone-50'"
            @click="openOrder(o)"
          >
            <span
              class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-[11px] font-bold"
              :class="o.items === 1 ? 'bg-[var(--accent-100)] text-[var(--accent-700)]' : 'bg-stone-100 text-stone-500'"
            >{{ o.items }}</span>
            <div class="min-w-0 flex-1">
              <div class="font-mono text-[12px] font-semibold text-stone-900">{{ o.order }}</div>
              <div class="text-[11px] text-stone-500 truncate">{{ o.customer }}</div>
            </div>
            <span
              v-if="o.items === 1"
              class="inline-flex items-center px-1.5 h-[17px] rounded text-[10px] font-medium text-[var(--accent-700)] bg-[var(--accent-50)] ring-1 ring-[var(--accent-200)]"
            >fast</span>
            <span
              class="inline-flex items-center gap-1 px-1.5 h-[17px] rounded text-[10px] font-medium ring-1"
              :class="[SLA[o.sla]?.txt, SLA[o.sla]?.bg, SLA[o.sla]?.ring]"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="SLA[o.sla]?.dot" />{{ SLA_LABEL[o.sla] }}
            </span>
          </button>
        </div>
      </div>

      <!-- pack workspace -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <!-- empty -->
        <div v-if="!active" class="flex flex-col items-center justify-center text-center py-20 px-6">
          <div class="w-14 h-14 rounded-2xl bg-stone-100 text-stone-400 flex items-center justify-center mb-3">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="26" height="26"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z" /><circle cx="7" cy="7" r="1" /></svg>
          </div>
          <div class="text-[14px] font-medium text-stone-700">Scan order or AWB</div>
          <div class="text-[12px] text-stone-400 mt-1">Pick an order from the queue or scan its barcode</div>
        </div>

        <!-- active -->
        <div v-else class="p-5">
          <div class="flex items-center justify-between mb-4">
            <div>
              <div class="font-mono text-[16px] font-bold text-stone-900">{{ active.order }}</div>
              <div class="text-[12px] text-stone-500">{{ active.customer }} · {{ active.zone.replace(" - JM", "") }}</div>
            </div>
            <span
              class="inline-flex items-center gap-1 px-2 h-[22px] rounded text-[11px] font-medium ring-1"
              :class="[SLA[active.sla]?.txt, SLA[active.sla]?.bg, SLA[active.sla]?.ring]"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="SLA[active.sla]?.dot" />{{ SLA_LABEL[active.sla] }}
            </span>
          </div>

          <!-- suggested box -->
          <div class="rounded-xl bg-stone-50 ring-1 ring-stone-200/60 p-3 mb-4 flex items-center gap-3">
            <span class="w-10 h-10 rounded-lg bg-white ring-1 ring-stone-200 flex items-center justify-center text-[12px] font-bold text-stone-700">{{ box.id }}</span>
            <div class="flex-1">
              <div class="text-[11px] text-stone-400 uppercase tracking-wide">Suggested box</div>
              <div class="text-[12.5px] font-medium text-stone-800">{{ box.dim }} cm · ≤{{ box.max }}kg</div>
            </div>
            <div class="text-end">
              <div class="text-[11px] text-stone-400">Weight</div>
              <div class="text-[13px] font-semibold text-stone-900 tabular-nums">{{ active.weight }} kg</div>
            </div>
          </div>

          <!-- scan progress -->
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-[12px] font-medium text-stone-600">Scan each item to verify</span>
            <span class="text-[12px] font-semibold text-emerald-600 tabular-nums">{{ scanned }}/{{ active.items }} verified</span>
          </div>
          <div class="h-2 rounded-full bg-stone-100 overflow-hidden mb-3">
            <div class="h-full bg-emerald-500 rounded-full transition-all" :style="{ width: (scanned / active.items * 100) + '%' }" />
          </div>

          <div class="space-y-2 mb-4">
            <div
              v-for="(_, i) in active.items"
              :key="i"
              class="flex items-center gap-3 rounded-xl ring-1 p-2.5"
              :class="i < scanned ? 'ring-emerald-200 bg-emerald-50/40' : 'ring-stone-200'"
            >
              <span
                class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                :class="i < scanned ? 'bg-emerald-500 text-white' : 'bg-stone-100 text-stone-400'"
              >
                <Icon v-if="i < scanned" name="check-circle" :size="15" />
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" /><path d="m3.3 7 8.7 5 8.7-5" /><path d="M12 22V12" /></svg>
              </span>
              <div class="min-w-0 flex-1">
                <div class="text-[12.5px] font-medium text-stone-900">Item {{ i + 1 }}</div>
                <div class="font-mono text-[10.5px] text-stone-400">{{ SKUS[i % 3] }}</div>
              </div>
              <span v-if="i < scanned" class="text-[11px] text-emerald-600 font-medium">✓ verified</span>
            </div>
          </div>

          <button
            v-if="!allScanned"
            class="w-full flex items-center gap-3 px-4 h-14 rounded-2xl ring-2 ring-stone-300 bg-white hover:ring-stone-400 transition-all active:scale-[0.99]"
            @click="scan"
          >
            <span class="w-10 h-10 rounded-xl bg-stone-900 text-white flex items-center justify-center flex-shrink-0">
              <Icon name="scan-barcode" :size="18" />
            </span>
            <span class="text-[14px] font-medium text-stone-600 flex-1 text-start">Scan each item to verify</span>
          </button>
          <button
            v-else
            class="w-full inline-flex items-center justify-center gap-2 h-12 rounded-2xl text-[14px] font-semibold text-white bg-emerald-600 hover:bg-emerald-700 transition-colors"
            @click="finish"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z" /><circle cx="7" cy="7" r="1" /></svg>
            Pack, weigh &amp; print AWB
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { SLA, SLA_LABEL, CARRIER } from "@/lib/handoffData.js";
import { useToast } from "@/composables/useToast";
import { api, liveOr } from "@/lib/resource";

const { success } = useToast();

// ── Pack station data (from data.jsx LG_PACK_QUEUE / LG_BOXES) ──────────
const PACK_QUEUE = [
  { order: "#242611", customer: "Khadija abhaoui", items: 2, weight: 0.6, box: "S", zone: "FAST ZONE - JM", sla: "ontrack" },
  { order: "#242605", customer: "Soukaina Idrissi", items: 1, weight: 0.3, box: "XS", zone: "FAST ZONE - JM", sla: "ontrack" },
  { order: "#242598", customer: "Rim Cherkaoui", items: 3, weight: 1.2, box: "M", zone: "Cosmetic zone - JM", sla: "atrisk" },
  { order: "#242590", customer: "Loubna Saidi", items: 1, weight: 0.4, box: "XS", zone: "Accessory Zone - JM", sla: "ontrack" },
];
const BOXES = [
  { id: "XS", dim: "15×10×5", max: 0.5 },
  { id: "S", dim: "25×18×8", max: 1.5 },
  { id: "M", dim: "35×25×12", max: 4 },
  { id: "L", dim: "45×35×20", max: 10 },
];
const SKUS = ["MCH100013", "CSM44021", "ACC11008"];

const queue = ref(PACK_QUEUE.map((o) => ({ ...o })));
const active = ref(null);
const scanned = ref(0);
const packed = ref(412);

// Live-or-demo: overwrite the pack queue with the real label queue once the
// app is installed. Map label-queue fields → the row/workspace shape, keeping
// demo defaults (box/weight/zone) so the workspace still renders. Preview →
// api() fails → keep demo.
onMounted(async () => {
  const live = await liveOr(null, () => api("shipping.label_queue", { limit: 50 }));
  if (live && live.length) {
    queue.value = live.map((o, i) => {
      const seed = PACK_QUEUE[i % PACK_QUEUE.length];
      return {
        order: o.order,
        customer: o.customer,
        items: o.parcels ?? seed.items,
        value: o.value,
        channel: o.channel,
        weight: seed.weight,
        box: seed.box,
        zone: seed.zone,
        sla: o.sla ?? seed.sla,
      };
    });
  }
});

const fastReady = computed(() => queue.value.filter((o) => o.items === 1).length);
const box = computed(() => (active.value ? BOXES.find((b) => b.id === active.value.box) || BOXES[0] : null));
const allScanned = computed(() => active.value && scanned.value >= active.value.items);

const tagIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/></svg>`;
const boxIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>`;
const zapIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;
const clockIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;

const kpis = computed(() => [
  { label: "Packed today", value: packed.value, icon: tagIcon, txt: "text-stone-500" },
  { label: "Pack queue", value: queue.value.length, icon: boxIcon, txt: "text-amber-600" },
  { label: "Orders / hour", value: 73, icon: zapIcon, txt: "text-emerald-600" },
  { label: "To cutoff", value: "2h 36m", icon: clockIcon, txt: "text-violet-600" },
]);

function openOrder(o) {
  active.value = o;
  scanned.value = 0;
}
function scan() {
  if (!active.value) return;
  scanned.value = Math.min(active.value.items, scanned.value + 1);
}
function finish() {
  packed.value += 1;
  success(`${active.value.order} packed · AWB printed · ${CARRIER}`);
  active.value = null;
  scanned.value = 0;
}
</script>
