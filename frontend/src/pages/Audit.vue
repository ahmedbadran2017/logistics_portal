<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <!-- Title -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">Audit &amp; Insights</h1>
        <p class="text-[13px] text-stone-500 mt-0.5">Rule engine (real-time) + the daily LLM review · {{ WAREHOUSE }}</p>
      </div>
      <div class="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-stone-500">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Rule engine · alerts land below as they fire
      </div>
    </div>

    <!-- Severity legend -->
    <div class="grid grid-cols-3 gap-3">
      <div v-for="s in severities" :key="s.key" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 flex items-center gap-3">
        <span class="w-9 h-9 rounded-lg flex items-center justify-center" :style="{ background: s.tint, color: s.hex }">
          <Icon :name="s.icon" :size="18" />
        </span>
        <div>
          <div class="text-[20px] font-semibold tabular-nums leading-none text-stone-900">{{ s.count }}</div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <!-- Live alerts (rule engine) -->
      <section class="xl:col-span-2 bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <header class="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
          <h3 class="text-[13.5px] font-semibold text-stone-900">Live alerts</h3>
          <span class="text-[11px] text-stone-400">Layer A · deterministic</span>
        </header>
        <div class="divide-y divide-stone-100">
          <div v-for="(a, i) in alerts" :key="i" class="flex items-start gap-3 p-4"
               :style="{ borderInlineStartWidth: '3px', borderInlineStartColor: sevHex(a.sev) }">
            <span class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                  :style="{ background: sevTint(a.sev), color: sevHex(a.sev) }">
              <Icon :name="sevIcon(a.sev)" :size="16" />
            </span>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="text-[13.5px] font-semibold text-stone-900">{{ a.title }}</span>
                <span class="text-[11px] text-stone-400">· {{ a.t }} ago</span>
              </div>
              <p class="text-[12.5px] text-stone-600 mt-0.5 leading-relaxed">{{ a.body }}</p>
              <button v-if="a.action" class="mt-1.5 text-[12px] font-semibold" style="color: var(--accent-700)"
                      @click="a.order && openOrder(a.order)">
                {{ a.action }} <Icon name="chevron-right" :size="13" class="inline -mt-px" />
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Daily insights (LLM) — hidden in production until the digest is wired -->
      <section v-if="insights.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <header class="px-4 py-3 border-b border-stone-100 flex items-center gap-2">
          <Icon name="sparkles" :size="16" class="text-violet-500" />
          <h3 class="text-[13.5px] font-semibold text-stone-900">Daily insights</h3>
          <span class="ms-auto text-[11px] text-stone-400">Layer B · LLM</span>
        </header>
        <div class="p-4 space-y-3">
          <div v-for="(n, i) in insights" :key="i" class="rounded-xl bg-violet-50/60 ring-1 ring-violet-100 p-3.5">
            <div class="text-[12.5px] font-semibold text-stone-900 leading-snug">{{ n.title }}</div>
            <p class="text-[12px] text-stone-600 mt-1.5 leading-relaxed">{{ n.body }}</p>
          </div>
          <div class="text-[11px] text-stone-400 pt-1">Generated end-of-shift · analytical, not accusatory.</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { AUDIT, WAREHOUSE } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";

const router = useRouter();

// Live-or-demo alerts (Layer A). Insights stay demo — LLM layer not live yet.
const alerts = ref(AUDIT.filter((a) => a.kind === "alert"));
const insights = computed(() => (import.meta.env.DEV ? AUDIT.filter((a) => a.kind === "note") : []));

onMounted(async () => {
  const live = await liveOr(null, () => api("audit.recent_alerts"));
  if (Array.isArray(live) && live.length) {
    const liveAlerts = live.filter((a) => a.kind === "alert");
    if (liveAlerts.length) alerts.value = liveAlerts;
  }
});

const SEV = {
  red:     { hex: "#e11d48", tint: "#ffe4e6", icon: "alert-triangle" },
  orange:  { hex: "#ea580c", tint: "#ffedd5", icon: "alert-circle" },
  yellow:  { hex: "#d97706", tint: "#fef3c7", icon: "bell" },
  insight: { hex: "#7c3aed", tint: "#ede9fe", icon: "sparkles" },
};
const sevHex = (s) => (SEV[s] || SEV.yellow).hex;
const sevTint = (s) => (SEV[s] || SEV.yellow).tint;
const sevIcon = (s) => (SEV[s] || SEV.yellow).icon;

const severities = computed(() => [
  { key: "red", label: "Critical", icon: "alert-triangle", hex: "#e11d48", tint: "#ffe4e6", count: alerts.value.filter((a) => a.sev === "red").length },
  { key: "orange", label: "Warning", icon: "alert-circle", hex: "#ea580c", tint: "#ffedd5", count: alerts.value.filter((a) => a.sev === "orange").length },
  { key: "yellow", label: "Info", icon: "bell", hex: "#d97706", tint: "#fef3c7", count: alerts.value.filter((a) => a.sev === "yellow").length },
]);

function openOrder(no) {
  router.push({ name: "OrderDetail", params: { name: no.replace("#", "") } });
}
</script>
