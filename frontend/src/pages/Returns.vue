<template>
  <div class="max-w-[1240px] mx-auto px-6 py-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-5">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Returns</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">Inspect &amp; process returned parcels · {{ CARRIER }}</p>
      </div>
    </div>

    <!-- KPI strip -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
            <Icon name="rotate-ccw" :size="16" />
          </span>
          <span class="text-[11px] font-medium text-stone-500 uppercase tracking-wide">Open returns</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums mt-2 leading-none">{{ openReturns }}</div>
        <div class="text-[11px] text-stone-400 mt-1">to process</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Icon name="check-circle" :size="16" />
          </span>
          <span class="text-[11px] font-medium text-stone-500 uppercase tracking-wide">Today processed</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums mt-2 leading-none">{{ processedToday }}</div>
        <div class="text-[11px] text-stone-400 mt-1">closed</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center">
            <Icon name="trending-up" :size="16" />
          </span>
          <span class="text-[11px] font-medium text-stone-500 uppercase tracking-wide">Return rate</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums mt-2 leading-none">{{ returnRate }}%</div>
        <div class="text-[11px] text-stone-400 mt-1">of shipped</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
            <Icon name="alert-triangle" :size="16" />
          </span>
          <span class="text-[11px] font-medium text-stone-500 uppercase tracking-wide">Top reason</span>
        </div>
        <div class="text-[16px] font-semibold text-stone-900 mt-2 leading-tight truncate">{{ topReason }}</div>
        <div class="text-[11px] text-stone-400 mt-1">most common</div>
      </div>
    </div>

    <!-- Returns table -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden mb-5">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[820px]">
          <thead>
            <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th class="text-start px-4 py-2.5">Return</th>
              <th class="text-start px-4 py-2.5">Order</th>
              <th class="text-start px-4 py-2.5">Customer</th>
              <th class="text-start px-4 py-2.5">Reason</th>
              <th class="text-start px-4 py-2.5 hidden sm:table-cell">SKU</th>
              <th class="text-end px-4 py-2.5">Value</th>
              <th class="text-start px-4 py-2.5">Status</th>
              <th class="text-start px-4 py-2.5 hidden md:table-cell">AWB</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr
              v-for="r in rows"
              :key="r.no"
              class="cursor-pointer hover:bg-stone-50 transition-colors"
              @click="openDrawer(r)"
            >
              <td class="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900 whitespace-nowrap">{{ r.no }}</td>
              <td class="px-4 py-2.5 font-mono text-[12px] text-stone-600">{{ r.order }}</td>
              <td class="px-4 py-2.5 text-[12.5px] text-stone-800">{{ r.customer }}</td>
              <td class="px-4 py-2.5 text-[12px] text-stone-600">{{ RETURN_REASONS[r.reason] || r.reason }}</td>
              <td class="px-4 py-2.5 font-mono text-[11.5px] text-stone-500 hidden sm:table-cell">{{ r.sku }}</td>
              <td class="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{{ fmtMAD(r.value) }}</td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ring-1"
                  :class="stateBadge[r.state].cls"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="stateBadge[r.state].dot" />
                  {{ stateBadge[r.state].label }}
                </span>
              </td>
              <td class="px-4 py-2.5 font-mono text-[11.5px] text-stone-500 hidden md:table-cell">{{ r.awb || '—' }}</td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="8" class="text-center text-[12.5px] text-stone-400 py-12">
                No returns waiting — every returned parcel has been processed.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Mini analytics -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-4 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
          <Icon name="alert-triangle" :size="15" /> Return reasons
        </div>
        <div class="space-y-3">
          <div v-for="rb in reasonBars" :key="rb.label">
            <div class="flex items-center justify-between text-[12px] mb-1">
              <span class="text-stone-700">{{ rb.label }}</span>
              <span class="text-stone-400 tabular-nums">{{ rb.count }}</span>
            </div>
            <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden">
              <div class="h-full rounded-full bg-[var(--accent-500)]" :style="{ width: (rb.count / reasonMax * 100) + '%' }" />
            </div>
          </div>
          <div v-if="reasonBars.length === 0" class="text-center text-[12px] text-stone-400 py-6">No data.</div>
        </div>
      </div>

      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-4 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
          <Icon name="package" :size="15" /> Returns by SKU
        </div>
        <div class="space-y-3">
          <div v-for="sb in skuBars" :key="sb.sku">
            <div class="flex items-center justify-between text-[12px] mb-1">
              <span class="font-mono text-stone-700">{{ sb.sku }}</span>
              <span class="tabular-nums" :style="{ color: sb.count >= 2 ? '#e11d48' : '#78716c' }">{{ sb.count }}</span>
            </div>
            <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden">
              <div class="h-full rounded-full" :style="{ width: (sb.count / skuMax * 100) + '%', background: sb.count >= 2 ? '#f43f5e' : '#f59e0b' }" />
            </div>
          </div>
          <div v-if="skuBars.length === 0" class="text-center text-[12px] text-stone-400 py-6">No data.</div>
        </div>
      </div>
    </div>

    <!-- Process slide-over -->
    <transition name="lp-drawer">
      <div v-if="active" class="fixed inset-0 z-40" @keydown.esc="closeDrawer">
        <div class="absolute inset-0 bg-stone-900/30" @click="closeDrawer" />
        <aside class="absolute right-0 top-0 h-full w-full max-w-md bg-white ring-1 ring-stone-200 shadow-2xl overflow-y-auto">
          <div class="p-5 border-b border-stone-200/70 flex items-center justify-between sticky top-0 bg-white z-10">
            <div>
              <div class="font-mono text-[16px] font-bold text-stone-900">{{ active.no }}</div>
              <div class="text-[12.5px] text-stone-500">Process return</div>
            </div>
            <button class="w-8 h-8 rounded-lg flex items-center justify-center text-stone-500 hover:bg-stone-100" @click="closeDrawer">
              <Icon name="x" :size="18" />
            </button>
          </div>

          <div class="p-5 space-y-5">
            <!-- Inspect summary -->
            <div class="rounded-xl ring-1 ring-stone-200/70 bg-stone-50 p-4 space-y-2">
              <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 mb-1">Inspect</div>
              <div class="flex justify-between text-[12.5px]"><span class="text-stone-500">Order</span><span class="font-mono text-stone-800">{{ active.order }}</span></div>
              <div class="flex justify-between text-[12.5px]"><span class="text-stone-500">Customer</span><span class="text-stone-800">{{ active.customer }}</span></div>
              <div class="flex justify-between text-[12.5px]"><span class="text-stone-500">SKU</span><span class="font-mono text-stone-800">{{ active.sku }}</span></div>
              <div class="flex justify-between text-[12.5px]"><span class="text-stone-500">Value</span><span class="tabular-nums text-stone-800">{{ fmtMAD(active.value) }} MAD</span></div>
              <div class="flex justify-between text-[12.5px]"><span class="text-stone-500">AWB</span><span class="font-mono text-stone-800">{{ active.awb || '—' }}</span></div>
              <div class="flex justify-between text-[12.5px]"><span class="text-stone-500">Stated reason</span><span class="text-stone-800">{{ RETURN_REASONS[active.reason] || active.reason }}</span></div>
            </div>

            <!-- Outcome -->
            <div>
              <div class="text-[12px] font-medium text-stone-700 mb-2">Outcome</div>
              <div class="grid grid-cols-3 gap-2">
                <button
                  v-for="o in outcomes"
                  :key="o"
                  type="button"
                  class="rounded-lg ring-1 px-3 py-2 text-[13px] font-medium transition-colors"
                  :class="form.outcome === o ? 'ring-[var(--accent-600)] text-[var(--accent-700)] bg-[var(--accent-50)]' : 'ring-stone-200 text-stone-600 hover:bg-stone-50'"
                  @click="form.outcome = o"
                >{{ o }}</button>
              </div>
            </div>

            <!-- Reason -->
            <div>
              <label class="text-[12px] font-medium text-stone-700 mb-1 block">Confirmed reason</label>
              <select v-model="form.reason" class="w-full h-9 px-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none">
                <option v-for="r in reasonOptions" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>

            <!-- Notes -->
            <div>
              <label class="text-[12px] font-medium text-stone-700 mb-1 block">Notes</label>
              <textarea
                v-model="form.notes"
                rows="3"
                placeholder="Condition of item, packaging, next steps…"
                class="w-full px-3 py-2 text-[12.5px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none resize-none"
              />
            </div>

            <button
              class="w-full h-11 flex items-center justify-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white text-[14px] font-medium transition-colors"
              @click="confirm"
            >
              <Icon name="check-circle" :size="16" /> Confirm &amp; close return
            </button>
          </div>
        </aside>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import { RETURNS as DEMO_RETURNS, RETURN_REASONS, CARRIER, fmtMAD } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";

const { success } = useToast();

const rows = ref(DEMO_RETURNS.map((r) => ({ ...r })));
const active = ref(null);
const processedToday = ref(0);

onMounted(async () => {
  const live = await liveOr(null, () => api("returns.queue", { limit: 50 }));
  if (live && live.length) rows.value = live;
});

const stateBadge = {
  open:    { label: "Open",    cls: "bg-amber-50 text-amber-700 ring-amber-200",     dot: "bg-amber-500" },
  inspect: { label: "Inspect", cls: "bg-cyan-50 text-cyan-700 ring-cyan-200",        dot: "bg-cyan-500" },
  restock: { label: "Restock", cls: "bg-violet-50 text-violet-700 ring-violet-200",  dot: "bg-violet-500" },
  closed:  { label: "Closed",  cls: "bg-emerald-50 text-emerald-700 ring-emerald-200",dot: "bg-emerald-500" },
};

const outcomes = ["Restock", "Defective", "Re-ship"];
const reasonOptions = Object.values(RETURN_REASONS);

const form = reactive({ outcome: "Restock", reason: reasonOptions[0], notes: "" });

const openReturns = computed(() => rows.value.filter((r) => r.state !== "closed").length);
const returnRate = computed(() => "2.4");

const reasonBars = computed(() => {
  const counts = {};
  rows.value.forEach((r) => { counts[r.reason] = (counts[r.reason] || 0) + 1; });
  return Object.entries(counts)
    .map(([key, count]) => ({ label: RETURN_REASONS[key] || key, count }))
    .sort((a, b) => b.count - a.count);
});
const reasonMax = computed(() => Math.max(1, ...reasonBars.value.map((r) => r.count)));
const topReason = computed(() => (reasonBars.value[0] && reasonBars.value[0].label) || "—");

const skuBars = computed(() => {
  const counts = {};
  rows.value.forEach((r) => { counts[r.sku] = (counts[r.sku] || 0) + 1; });
  return Object.entries(counts)
    .map(([sku, count]) => ({ sku, count }))
    .sort((a, b) => b.count - a.count);
});
const skuMax = computed(() => Math.max(1, ...skuBars.value.map((s) => s.count)));

function openDrawer(row) {
  active.value = row;
  form.outcome = "Restock";
  const label = RETURN_REASONS[row.reason];
  form.reason = reasonOptions.includes(label) ? label : reasonOptions[0];
  form.notes = "";
}
function closeDrawer() {
  active.value = null;
}
function confirm() {
  const no = active.value.no;
  rows.value = rows.value.filter((r) => r.no !== no);
  processedToday.value += 1;
  success(`${no} processed`, `${form.outcome} · ${form.reason}`);
  active.value = null;
}
</script>

<style scoped>
.lp-drawer-enter-active,
.lp-drawer-leave-active { transition: opacity 0.2s ease; }
.lp-drawer-enter-from,
.lp-drawer-leave-to { opacity: 0; }
</style>
