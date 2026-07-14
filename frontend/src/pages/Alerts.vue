<template>
  <div class="overflow-y-auto">
    <div class="p-5 sm:p-6 space-y-4 max-w-[860px] mx-auto animate-fade-in">
      <!-- Title + action -->
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">Alerts</h1>
          <p class="text-[13px] text-stone-500 mt-0.5">Rule-based alerts &amp; daily insights across the floor</p>
        </div>
        <button
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          @click="markAll"
        >
          <Icon name="check-circle" :size="15" /> Mark all read
        </button>
      </div>

      <!-- KPI row -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
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

      <!-- Filter tabs -->
      <div class="flex items-center gap-1.5">
        <button
          v-for="f in filters"
          :key="f.key"
          class="px-3 h-8 text-[12.5px] font-medium rounded-lg ring-1 transition-colors"
          :class="filter === f.key
            ? 'bg-stone-900 text-white ring-stone-900'
            : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'"
          @click="filter = f.key"
        >{{ f.label }}</button>
      </div>

      <!-- Empty -->
      <div
        v-if="items.length === 0"
        class="bg-white rounded-xl ring-1 ring-stone-200/70 p-10 text-center"
      >
        <div class="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-500 flex items-center justify-center mx-auto mb-3">
          <Icon name="check-circle" :size="24" />
        </div>
        <div class="text-[14px] font-medium text-stone-700">You're all caught up</div>
      </div>

      <!-- Alert list -->
      <div v-else class="space-y-2.5">
        <div
          v-for="a in items"
          :key="a._id"
          class="relative transition-opacity"
          :class="read.has(a._id) ? 'opacity-55' : ''"
        >
          <span
            v-if="!read.has(a._id)"
            class="absolute -start-2.5 top-4 w-1.5 h-1.5 rounded-full bg-[var(--accent-600)]"
          />
          <!-- AlertRow (severity-colored) -->
          <div class="relative bg-white rounded-lg ring-1 p-3 ps-3.5 overflow-hidden" :class="sev(a).ring">
            <span class="absolute inset-y-0 start-0 w-1" :class="sev(a).bar" />
            <div class="flex items-start gap-2.5">
              <Icon :name="sev(a).icon" :size="16" class="mt-0.5 flex-shrink-0" :class="sev(a).ic" />
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="text-[12.5px] font-semibold text-stone-900 truncate flex-1 min-w-0">{{ a.title }}</span>
                  <span class="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{{ a.t }}</span>
                </div>
                <p class="text-[12px] text-stone-600 mt-0.5 leading-snug text-pretty">{{ a.body }}</p>
                <button
                  v-if="a.action"
                  class="mt-2 inline-flex items-center gap-1 text-[11.5px] font-semibold text-[var(--accent-700)] hover:text-[var(--accent-800)]"
                  @click="onAction(a)"
                >
                  {{ a.action }} <Icon name="arrow-right" :size="11" />
                </button>
              </div>
              <button
                class="w-[22px] h-[22px] rounded-md flex items-center justify-center text-stone-400 hover:text-stone-600 hover:bg-stone-100 flex-shrink-0 transition-colors"
                @click="dismiss(a)"
              >
                <Icon name="x" :size="14" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";

import { api, liveOr } from "@/lib/resource";

const router = useRouter();

// Live-or-demo alert feed: `audit.recent_alerts` returns the same shape as AUDIT.
const AUDIT = ref([]);
onMounted(async () => {
  const live = await liveOr(null, () => api("audit.recent_alerts"));
  if (Array.isArray(live) && live.length) AUDIT.value = live;
});

// severity → group (for filters + counts)
const SEV_GROUP = { red: "critical", orange: "warning", yellow: "warning", insight: "info" };

// severity → visual style (ported from components.jsx AlertRow SEV map)
const SEV = {
  red:     { ring: "ring-rose-200",   bar: "bg-rose-500",   ic: "text-rose-500",   icon: "alert-circle" },
  orange:  { ring: "ring-orange-200", bar: "bg-orange-500", ic: "text-orange-500", icon: "alert-circle" },
  yellow:  { ring: "ring-amber-200",  bar: "bg-amber-500",  ic: "text-amber-500",  icon: "info" },
  insight: { ring: "ring-violet-200", bar: "bg-violet-500", ic: "text-violet-500", icon: "sparkles" },
};
const sev = (a) => SEV[a.sev] || SEV.yellow;

const filter = ref("all");
const read = ref(new Set());

const filters = [
  { key: "all", label: "All" },
  { key: "critical", label: "Critical" },
  { key: "warning", label: "Warning" },
  { key: "info", label: "Info" },
];

const items = computed(() =>
  AUDIT.value.map((a, i) => ({ ...a, _id: i }))
    .filter((a) => filter.value === "all" || SEV_GROUP[a.sev] === filter.value)
);

const counts = computed(() => ({
  critical: AUDIT.value.filter((a) => SEV_GROUP[a.sev] === "critical").length,
  warning: AUDIT.value.filter((a) => SEV_GROUP[a.sev] === "warning").length,
  info: AUDIT.value.filter((a) => SEV_GROUP[a.sev] === "info").length,
}));
const unread = computed(() => AUDIT.value.length - read.value.size);

const kpis = computed(() => [
  { label: "Unread", icon: "bell", tone: "text-stone-500 bg-stone-100", value: unread.value },
  { label: "Critical", icon: "alert-circle", tone: "text-rose-600 bg-rose-50", value: counts.value.critical },
  { label: "Warning", icon: "alert-circle", tone: "text-amber-600 bg-amber-50", value: counts.value.warning },
  { label: "Info", icon: "sparkles", tone: "text-violet-600 bg-violet-50", value: counts.value.info },
]);

function markAll() {
  read.value = new Set(AUDIT.value.map((_, i) => i));
}
function dismiss(a) {
  read.value = new Set([...read.value, a._id]);
}
function onAction(a) {
  if (a.order) router.push({ name: "OrderDetail", params: { name: a.order.replace("#", "") } });
}
</script>
