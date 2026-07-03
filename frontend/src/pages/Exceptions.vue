<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <div>
      <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Exception center</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5">One queue for every blocker across the cycle</p>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-2">
          <span class="w-7 h-7 rounded-lg flex items-center justify-center" :class="[k.bg, k.fg]">
            <Icon :name="k.icon" :size="15" />
          </span>
          <span class="text-[11px] font-medium text-stone-500">{{ k.label }}</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums leading-none">
          {{ k.value }}<span v-if="k.unit" class="text-[12px] text-stone-400 ms-0.5">{{ k.unit }}</span>
        </div>
      </div>
    </div>

    <!-- kind filter -->
    <div class="flex items-center gap-1.5 overflow-x-auto pb-1">
      <button
        v-for="k in kinds"
        :key="k"
        class="px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 whitespace-nowrap"
        :class="filter === k ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'"
        @click="filter = k"
      >
        {{ kindLabel(k) }}
      </button>
    </div>

    <!-- rows -->
    <div class="space-y-2">
      <div
        v-for="e in shown"
        :key="e.id"
        class="relative bg-white rounded-xl ring-1 ring-stone-200/70 p-3.5 ps-4 overflow-hidden flex items-center gap-3 flex-wrap"
      >
        <span class="absolute inset-y-0 start-0 w-1" :class="sevColor(e.sev)" />
        <span
          class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          :class="[toneBg(EXC_KIND[e.kind].tone), toneFg(EXC_KIND[e.kind].tone)]"
        >
          <Icon :name="kindIcon(e.kind)" :size="15" />
        </span>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="font-mono text-[12px] font-semibold text-stone-900">{{ e.id }}</span>
            <span
              class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap"
              :class="[toneFg(badgeTone(e.kind)), toneBg(badgeTone(e.kind)), toneRing(badgeTone(e.kind))]"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="toneDot(badgeTone(e.kind))" />{{ e.label }}
            </span>
            <span
              v-if="e.age > e.sla"
              class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap text-rose-700 bg-rose-50 ring-rose-200"
            >Overdue</span>
          </div>
          <div class="text-[12px] text-stone-600 mt-0.5 truncate">{{ e.detail }}</div>
        </div>
        <div class="flex items-center gap-1.5 text-[11px] text-stone-400">
          <span class="w-5 h-5 rounded-full bg-stone-200 text-stone-600 flex items-center justify-center text-[9px] font-semibold">{{ initials(byId(e.owner).name) }}</span>
          <span class="tabular-nums" :class="e.age > e.sla ? 'text-rose-600 font-medium' : ''">{{ e.age }}m old</span>
        </div>
        <div class="flex items-center gap-1.5">
          <button
            class="inline-flex items-center gap-1.5 px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
            @click="openOrder(e.id)"
          >
            <Icon name="arrow-right" :size="13" />Open
          </button>
          <button
            class="inline-flex items-center gap-1.5 px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 whitespace-nowrap text-white"
            :style="{ background: 'var(--accent-600)', borderColor: 'var(--accent-600)' }"
            @click="resolveExc(e.id)"
          >
            <Icon name="check" :size="13" />Resolve
          </button>
        </div>
      </div>
      <div v-if="shown.length === 0" class="text-center text-[12.5px] text-emerald-600 py-12 flex items-center justify-center gap-1.5">
        <Icon name="check-circle" :size="16" />All clear — no open exceptions
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import { byId } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";

const router = useRouter();
const { success } = useToast();

// ── local data (not exported from handoffData) ─────────────────────
const EXCEPTIONS = [
  { id: "#242638", kind: "oos", label: "Out of stock", detail: "Mohmad Mohmad · Cosmetic zone · 2 items OOS", owner: "asmaa", age: 158, sev: "red", sla: 30 },
  { id: "#240682", kind: "carrier", label: "Failed delivery", detail: "Edghir hanane · 2nd failed attempt · LD007744422", owner: "nadia", age: 142, sev: "red", sla: 60 },
  { id: "#242128", kind: "carrier", label: "Carrier exception", detail: "Fatima Fatima · address not found", owner: "nadia", age: 86, sev: "orange", sla: 60 },
  { id: "PL-51388", kind: "shortpick", label: "Short-pick", detail: "Nezili kaoutar · MUZ22014 missing 1", owner: "asmaa", age: 47, sev: "orange", sla: 45 },
  { id: "RET-26-3137317", kind: "return", label: "Missing on return", detail: "3 SKUs not in carrier return batch", owner: "nadia", age: 220, sev: "yellow", sla: 120 },
  { id: "CR-2026-0141", kind: "cod", label: "COD discrepancy", detail: "Cathedis · −1,240 MAD short on remittance", owner: "sara", age: 300, sev: "red", sla: 240 },
];
const EXC_KIND = {
  oos: { tone: "rose", icon: "package" },
  carrier: { tone: "orange", icon: "globe" },
  shortpick: { tone: "amber", icon: "alert-circle" },
  return: { tone: "violet", icon: "rotate-ccw" },
  cod: { tone: "rose", icon: "dollar-sign" },
};

const rows = ref(EXCEPTIONS.map((e) => ({ ...e })));
const filter = ref("all");
const kinds = ["all", "oos", "carrier", "shortpick", "return", "cod"];

// Live-or-demo data. `shipping.exceptions` returns rows shaped
// { id, awb, customer, kind:'exception'|'failed', detail, value }; map them into
// the screen's row shape. In local preview api() fails and EXCEPTIONS remain.
onMounted(async () => {
  const live = await liveOr(null, () => api("shipping.exceptions"));
  if (live && live.length) {
    rows.value = live.map((r) => ({
      id: r.id ?? r.awb ?? "—",
      awb: r.awb ?? "—",
      customer: r.customer ?? "—",
      // live kind is exception|failed → screen's "carrier" bucket (has both icon + tone)
      kind: EXC_KIND[r.kind] ? r.kind : "carrier",
      label: r.kind === "failed" ? "Failed delivery" : "Carrier exception",
      detail: r.detail ?? r.reason ?? ([r.customer, r.awb].filter(Boolean).join(" · ") || "—"),
      value: r.value ?? null,
      owner: r.owner ?? "nadia",
      age: r.age ?? 0,
      sev: r.sev ?? (r.kind === "failed" ? "red" : "orange"),
      sla: r.sla ?? 60,
    }));
  }
});

const shown = computed(() => rows.value.filter((e) => filter.value === "all" || e.kind === filter.value));
const critical = computed(() => rows.value.filter((e) => e.sev === "red").length);
const overdue = computed(() => rows.value.filter((e) => e.age > e.sla).length);
const avgAge = computed(() =>
  Math.round(rows.value.reduce((a, e) => a + e.age, 0) / (rows.value.length || 1))
);

const kpis = computed(() => [
  { label: "Open", value: rows.value.length, icon: "alert-circle", bg: "bg-stone-100", fg: "text-stone-600" },
  { label: "Critical", value: critical.value, icon: "alert-circle", bg: "bg-rose-50", fg: "text-rose-600" },
  { label: "Overdue", value: overdue.value, icon: "clock", bg: "bg-amber-50", fg: "text-amber-600" },
  { label: "Avg age", value: avgAge.value, unit: "m", icon: "activity", bg: "bg-violet-50", fg: "text-violet-600" },
]);

function kindLabel(k) {
  return k === "all" ? "All kinds"
    : k === "oos" ? "Out of stock"
    : k === "carrier" ? "Carrier"
    : k === "shortpick" ? "Short-pick"
    : k === "return" ? "Returns"
    : "COD";
}
function kindIcon(k) {
  return (EXC_KIND[k] || EXC_KIND.oos).icon;
}
function badgeTone(k) {
  const t = EXC_KIND[k].tone;
  return t === "orange" ? "amber" : t;
}
function sevColor(sev) {
  return sev === "red" ? "bg-rose-500" : sev === "orange" ? "bg-orange-500" : "bg-amber-500";
}
const toneBg = (t) => ({ rose: "bg-rose-50", orange: "bg-orange-50", amber: "bg-amber-50", violet: "bg-violet-50" }[t] || "bg-stone-50");
const toneFg = (t) => ({ rose: "text-rose-600", orange: "text-orange-600", amber: "text-amber-600", violet: "text-violet-600" }[t] || "text-stone-600");
const toneRing = (t) => ({ rose: "ring-rose-200", orange: "ring-orange-200", amber: "ring-amber-200", violet: "ring-violet-200" }[t] || "ring-stone-200");
const toneDot = (t) => ({ rose: "bg-rose-500", orange: "bg-orange-500", amber: "bg-amber-500", violet: "bg-violet-500" }[t] || "bg-stone-400");

function initials(name) {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
}
function resolveExc(id) {
  rows.value = rows.value.filter((e) => e.id !== id);
  success(`${id} resolved`);
}
function openOrder(id) {
  if (String(id).startsWith("#")) {
    router.push({ name: "OrderDetail", params: { name: String(id).replace("#", "") } });
  }
}
</script>
