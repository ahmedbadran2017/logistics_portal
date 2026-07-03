<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <!-- head -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">COD reconciliation</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">Cash collected by carrier → remitted</p>
      </div>
      <button
        class="inline-flex items-center gap-1.5 px-3 h-9 text-[13px] font-medium text-stone-700 bg-white rounded-lg ring-1 ring-stone-200 hover:ring-stone-300 transition-colors whitespace-nowrap"
        @click="info('Export queued')"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" x2="12" y1="15" y2="3" />
        </svg>
        Export
      </button>
    </div>

    <!-- KPI strip -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3.5">
        <div class="flex items-center gap-1.5 text-[11.5px] font-medium text-stone-500">
          <span class="w-6 h-6 rounded-lg flex items-center justify-center" :class="k.tone">
            <Icon :name="k.icon" :size="13" />
          </span>
          {{ k.label }}
        </div>
        <div class="text-[22px] font-semibold text-stone-900 tabular-nums mt-1.5 leading-none font-mono">
          {{ k.value }}<span v-if="k.unit" class="text-[11px] text-stone-400 ms-1 font-normal font-sans">{{ k.unit }}</span>
        </div>
      </div>
    </div>

    <!-- remitted / collected progress -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
      <div class="flex items-center justify-between text-[12px] mb-1.5">
        <span class="text-stone-600 font-medium">Remitted / Collected</span>
        <span class="font-semibold text-emerald-600 tabular-nums">{{ Math.round(remitPct * 100) }}%</span>
      </div>
      <div class="h-2.5 rounded-full bg-stone-100 overflow-hidden">
        <div class="h-full bg-emerald-500 rounded-full" :style="{ width: remitPct * 100 + '%' }" />
      </div>
      <div class="flex items-center gap-4 mt-2 text-[11px] text-stone-400">
        <span>COD success rate {{ COD.codRate }}%</span>
      </div>
    </div>

    <!-- remittances table -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-3 border-b border-stone-100">
        <div class="text-[13px] font-semibold text-stone-900">Carrier remittances</div>
        <div class="text-[11.5px] text-stone-500 mt-0.5">{{ CARRIER }}</div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[720px]">
          <thead>
            <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th class="text-start px-4 py-2.5">Remittance</th>
              <th class="text-start px-4 py-2.5">Date</th>
              <th class="text-end px-4 py-2.5">Parcels</th>
              <th class="text-end px-4 py-2.5">Expected</th>
              <th class="text-end px-4 py-2.5">Received</th>
              <th class="text-end px-4 py-2.5">Diff</th>
              <th class="text-start px-4 py-2.5">Status</th>
              <th class="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr v-for="r in rows" :key="r.no" :class="r.status === 'discrepancy' ? 'bg-rose-50/30' : 'hover:bg-stone-50'">
              <td class="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900">{{ r.no }}</td>
              <td class="px-4 py-2.5 text-[12px] text-stone-600 whitespace-nowrap">{{ r.date }}</td>
              <td class="px-4 py-2.5 text-end text-[12px] text-stone-600 tabular-nums">{{ r.parcels }}</td>
              <td class="px-4 py-2.5 text-end text-[12.5px] text-stone-700 tabular-nums font-mono">{{ fmtMAD(r.expected) }}</td>
              <td class="px-4 py-2.5 text-end text-[12.5px] font-medium text-stone-900 tabular-nums font-mono">{{ r.received ? fmtMAD(r.received) : "—" }}</td>
              <td class="px-4 py-2.5 text-end text-[12.5px] tabular-nums font-mono">
                <span :class="r.diff < 0 ? 'text-rose-600 font-semibold' : 'text-stone-400'">{{ r.diff ? fmtMAD(r.diff) : "0" }}</span>
              </td>
              <td class="px-4 py-2.5">
                <span
                  class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 whitespace-nowrap capitalize"
                  :class="statusPill(r.status)"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="statusDot(r.status)" />
                  {{ r.status }}
                </span>
              </td>
              <td class="px-4 py-2.5 text-end">
                <button
                  v-if="r.status === 'pending'"
                  class="inline-flex items-center gap-1 px-2.5 h-7 text-[12px] font-medium text-white rounded-lg whitespace-nowrap transition-colors"
                  :style="{ background: 'var(--accent-600)' }"
                  @click="reconcile(r.no)"
                >
                  <Icon name="check" :size="13" /> Reconcile
                </button>
                <button
                  v-else-if="r.status === 'discrepancy'"
                  class="inline-flex items-center gap-1 px-2.5 h-7 text-[12px] font-medium text-white bg-rose-600 rounded-lg hover:bg-rose-500 whitespace-nowrap transition-colors"
                >
                  <Icon name="alert-circle" :size="13" /> Flag discrepancy
                </button>
                <span v-else class="inline-flex items-center gap-1 text-[11.5px] text-emerald-600">
                  <Icon name="check-circle" :size="13" /> Reconciled
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { CARRIER, fmtMAD } from "@/lib/handoffData";
import { useToast } from "@/composables/useToast";

const { success, info } = useToast();

// COD reconciliation data (from design_handoff/logistics/data.jsx)
const COD = {
  collected: 141368, remitted: 98200, pending: 43168, discrepancy: 1240, codRate: 96,
  remittances: [
    { no: "CR-2026-0142", date: "2026-06-19", carrier: "Cathedis", parcels: 198, expected: 31420, received: 31420, diff: 0, status: "reconciled" },
    { no: "CR-2026-0141", date: "2026-06-18", carrier: "Cathedis", parcels: 241, expected: 38950, received: 37710, diff: -1240, status: "discrepancy" },
    { no: "CR-2026-0140", date: "2026-06-17", carrier: "Cathedis", parcels: 263, expected: 39950, received: 39950, diff: 0, status: "reconciled" },
    { no: "CR-2026-0139", date: "2026-06-20", carrier: "Cathedis", parcels: 124, expected: 43168, received: 0, diff: 0, status: "pending" },
  ],
};

const rows = ref(COD.remittances.map((r) => ({ ...r })));

const remitPct = computed(() => (COD.collected ? COD.remitted / COD.collected : 0));

function reconcile(no) {
  rows.value = rows.value.map((r) =>
    r.no === no ? { ...r, status: "reconciled", received: r.expected, diff: 0 } : r
  );
  success(`${no} reconciled · posted to ERPNext`);
}

const kpis = computed(() => [
  { label: "Collected", icon: "wallet", tone: "bg-stone-100 text-stone-500", value: fmtMAD(COD.collected), unit: "MAD" },
  { label: "Remitted", icon: "check-circle", tone: "bg-emerald-50 text-emerald-600", value: fmtMAD(COD.remitted), unit: "MAD" },
  { label: "Pending remittance", icon: "clock", tone: "bg-amber-50 text-amber-600", value: fmtMAD(COD.pending), unit: "MAD" },
  { label: "Discrepancy", icon: "alert-circle", tone: "bg-rose-50 text-rose-600", value: fmtMAD(COD.discrepancy), unit: "MAD" },
]);

const STATUS_PILL = {
  reconciled: "text-emerald-700 bg-emerald-50 ring-emerald-200",
  discrepancy: "text-rose-700 bg-rose-50 ring-rose-200",
  pending: "text-amber-700 bg-amber-50 ring-amber-200",
};
const STATUS_DOT = {
  reconciled: "bg-emerald-500",
  discrepancy: "bg-rose-500",
  pending: "bg-amber-500",
};
function statusPill(s) { return STATUS_PILL[s] || STATUS_PILL.pending; }
function statusDot(s) { return STATUS_DOT[s] || STATUS_DOT.pending; }
</script>
