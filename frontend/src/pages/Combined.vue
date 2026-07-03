<template>
  <div class="max-w-7xl mx-auto space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-h2 text-stone-900 flex items-center gap-2 tracking-[-0.01em]">
          <Icon name="layers" :size="22" class="text-[var(--accent-600)]" /> Combined Pick
        </h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">
          Batch orders that share the same SKUs into a single pick walk.
        </p>
      </div>
      <!-- threshold chips -->
      <div class="flex gap-2">
        <button v-for="t in thresholds" :key="t.value"
                class="px-3 py-1.5 rounded-full text-[12px] font-medium transition-colors"
                :class="threshold === t.value ? 'bg-[var(--accent-600)] text-white' : 'bg-stone-100 text-stone-600 hover:text-stone-900'"
                @click="threshold = t.value">
          {{ t.label }}
        </button>
      </div>
    </div>

    <!-- KPI strip -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <div class="rounded-xl ring-1 ring-stone-200/70 bg-white p-4">
        <div class="flex items-center gap-1.5 text-stone-500">
          <Icon name="layers" :size="14" class="text-violet-500" />
          <span class="text-[11px] font-medium">Candidate groups</span>
        </div>
        <div class="text-[24px] font-semibold tabular-nums text-stone-900 leading-none mt-1.5">{{ visibleGroups.length }}</div>
      </div>
      <div class="rounded-xl ring-1 ring-stone-200/70 bg-white p-4">
        <div class="flex items-center gap-1.5 text-stone-500">
          <Icon name="package" :size="14" class="text-cyan-500" />
          <span class="text-[11px] font-medium">Orders coverable</span>
        </div>
        <div class="text-[24px] font-semibold tabular-nums text-stone-900 leading-none mt-1.5">{{ ordersCoverable }}</div>
      </div>
      <div class="rounded-xl ring-1 ring-stone-200/70 bg-white p-4">
        <div class="flex items-center gap-1.5 text-stone-500">
          <Icon name="clock" :size="14" class="text-emerald-500" />
          <span class="text-[11px] font-medium">Est. time saved</span>
        </div>
        <div class="text-[24px] font-semibold tabular-nums text-emerald-600 leading-none mt-1.5">{{ timeSaved }}m</div>
      </div>
    </div>

    <!-- candidate groups -->
    <div v-if="!visibleGroups.length" class="rounded-xl ring-1 ring-stone-200/70 bg-white p-12 text-center">
      <Icon name="layers" :size="28" class="text-stone-300 mx-auto" />
      <div class="text-[14px] font-semibold text-stone-700 mt-3">No combinable groups</div>
      <div class="text-[12.5px] text-stone-500 mt-1">Lower the threshold to find more overlaps.</div>
    </div>

    <div v-else class="space-y-4">
      <div v-for="g in visibleGroups" :key="g.sku" class="rounded-xl ring-1 ring-stone-200/70 bg-white p-4">
        <div class="flex flex-col sm:flex-row sm:items-center gap-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11.5px] font-medium font-mono bg-violet-50 text-violet-700 ring-1 ring-violet-200">
                <Icon name="scan-barcode" :size="13" /> {{ g.sku }}
              </span>
              <span class="inline-flex items-center gap-1 text-[11px] text-stone-500">
                <Icon name="map-pin" :size="11" /> bin <span class="font-mono">{{ g.bin }}</span>
              </span>
            </div>
            <div class="text-h3 text-stone-900 mt-2">{{ g.itemName }}</div>
            <div class="text-[13px] text-stone-500 mt-1">
              {{ g.orders.length }} orders · <span class="tabular-nums">{{ g.totalQty }}</span> units total
            </div>
          </div>
          <div class="text-center px-4">
            <div class="text-[32px] font-semibold tabular-nums text-stone-900 leading-none">{{ g.totalQty }}</div>
            <div class="text-[11px] text-stone-400 mt-1">to pick</div>
          </div>
          <button class="inline-flex items-center gap-1.5 px-3 h-10 rounded-lg bg-[var(--accent-600)] text-white text-[13px] font-medium hover:bg-[var(--accent-700)] transition-colors shrink-0"
                  @click="createList(g)">
            <Icon name="list-checks" :size="16" /> Create Combined Pick List
          </button>
        </div>

        <!-- contributing orders -->
        <div class="mt-4 border-t border-stone-100 pt-3">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 mb-2">Contributing orders</div>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="o in g.orders" :key="o.no"
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[11px] bg-stone-100 text-stone-600">
              {{ o.no }} <span class="opacity-60">×{{ o.qty }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import { ORDERS, PICKLISTS } from "@/lib/handoffData.js";
import { api, liveOr } from "@/lib/resource";

const { success } = useToast();

const threshold = ref(2);
const thresholds = [
  { value: 2, label: "2+" },
  { value: 3, label: "3+" },
  { value: 5, label: "5+" },
];

// Removed groups (after a pick list is created)
const removed = ref(new Set());

// Live-or-demo pick-lists source. Seeded from the demo PICKLISTS; overwritten
// in onMounted with the live combined pick lists when the app is installed.
const pickLists = ref(PICKLISTS);
onMounted(async () => {
  const live = await liveOr(null, () => api("picking.pick_lists", { limit: 40 }));
  if (live && live.length) {
    const combined = live.filter((p) => p.order === "combined");
    if (combined.length) pickLists.value = combined;
  }
});

// ── Build combined-pick candidates ──────────────────────────────────────
// 1. Real combined pick lists (pickLists where order === "combined").
// 2. Synthesized SKU-overlap groups from ORDERS sharing a bin.
function buildGroups() {
  const groups = [];

  // (1) existing combined pick lists → candidate groups
  pickLists.value.filter((pl) => pl.order === "combined" && pl.status !== "completed").forEach((pl, i) => {
    const n = pl.items;
    // synthesize contributing order chips from the pool of pending orders
    const pool = ORDERS.slice(i * 2, i * 2 + n);
    const orders = pool.length
      ? pool.map((o) => ({ no: o.no, qty: Math.max(1, o.items) }))
      : Array.from({ length: n }, (_, k) => ({ no: `#2426${20 + k}`, qty: 1 }));
    groups.push({
      sku: pl.no,
      itemName: `${pl.item} · ${n} orders`,
      bin: pl.bin,
      totalQty: pl.qty,
      orders,
    });
  });

  // (2) synthesize SKU/bin-overlap groups from pending & active orders
  const byBin = {};
  ORDERS.filter((o) => ["pending", "picking", "picked"].includes(o.stage)).forEach((o) => {
    (byBin[o.bin] = byBin[o.bin] || []).push(o);
  });
  const skuFor = {
    "J8C - JM": ["MCH100013", "Diffuseur huile MCH — box"],
    "J8A - JM": ["MCH100013", "Diffuseur huile MCH — box"],
    "F14B - JM": ["CSM44021", "Sérum éclat 30ml"],
    "H14A - JM": ["ACC11008", "Trousse maquillage zip"],
    "H13B - JM": ["MUZ22014", "Palette ombres MU"],
    "J7B - JM": ["MCH100020", "Recharge huile lavande"],
  };
  Object.entries(byBin).forEach(([bin, list]) => {
    if (list.length < 2) return;
    const meta = skuFor[bin] || [bin.replace(" - JM", ""), "Batch pick"];
    groups.push({
      sku: meta[0],
      itemName: meta[1],
      bin,
      totalQty: list.reduce((a, o) => a + Math.max(1, o.items), 0),
      orders: list.map((o) => ({ no: o.no, qty: Math.max(1, o.items) })),
    });
  });

  return groups;
}

const allGroups = computed(() => buildGroups());

const visibleGroups = computed(() =>
  allGroups.value.filter((g) => g.orders.length >= threshold.value && !removed.value.has(g.sku))
);
const ordersCoverable = computed(() => {
  const set = new Set();
  visibleGroups.value.forEach((g) => g.orders.forEach((o) => set.add(o.no)));
  return set.size;
});
const timeSaved = computed(() =>
  visibleGroups.value.reduce((sum, g) => sum + Math.max(0, (g.orders.length - 1) * 2), 0)
);

function createList(g) {
  const id = "PL-514" + Math.floor(10 + Math.random() * 90);
  const s = new Set(removed.value);
  s.add(g.sku);
  removed.value = s;
  success(`${id} created`, `Combined pick for ${g.orders.length} orders · ${g.totalQty} units`);
}
</script>
