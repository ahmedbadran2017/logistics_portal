<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <!-- Title -->
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">Audit &amp; Insights</h1>
        <p class="text-[13px] text-stone-500 mt-0.5">
          Problem radar — every known failure mode, scanned live · {{ WAREHOUSE }}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="radar" class="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-stone-500">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Last scan {{ (radar.scannedAt || "").slice(11, 16) }} · every 10 min
        </span>
        <button
          class="inline-flex items-center justify-center h-9 w-9 rounded-lg text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          :class="loading ? 'opacity-60 pointer-events-none' : ''"
          title="Rescan" aria-label="Rescan"
          @click="load"
        >
          <Icon name="refresh-cw" :size="14" :class="loading ? 'animate-spin' : ''" />
        </button>
      </div>
    </div>

    <!-- Severity totals (from the radar) -->
    <div class="grid grid-cols-3 gap-3">
      <div v-for="s in severities" :key="s.key" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 flex items-center gap-3">
        <span class="w-9 h-9 rounded-lg flex items-center justify-center" :style="{ background: s.tint, color: s.hex }">
          <Icon :name="s.icon" :size="18" />
        </span>
        <div>
          <div class="text-[20px] font-semibold tabular-nums leading-none" :style="s.count ? { color: s.hex } : {}">{{ s.count }}</div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <!-- The radar: every open problem, click-through to the fixing screen -->
      <section class="xl:col-span-2 bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <header class="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
          <h3 class="text-[13.5px] font-semibold text-stone-900">Problem radar</h3>
          <span class="text-[11px] text-stone-400">deterministic · windowed · cached 2 min</span>
        </header>

        <div v-if="loading && !radar" class="p-4 space-y-2.5">
          <div v-for="n in 5" :key="n" class="h-[72px] rounded-xl ring-1 ring-stone-200/60 bg-stone-50 animate-pulse" />
        </div>

        <div v-else-if="radar && !radar.findings.length" class="p-10 text-center">
          <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3">
            <Icon name="check-circle" :size="22" />
          </span>
          <div class="text-[14.5px] font-semibold text-stone-900">Floor is clean</div>
          <div class="text-[12.5px] text-stone-500 mt-1">No open problems in any category.</div>
        </div>

        <div v-else-if="radar" class="divide-y divide-stone-100">
          <button
            v-for="f in radar.findings"
            :key="f.key"
            class="w-full text-start flex items-start gap-3 p-4 hover:bg-stone-50 transition-colors"
            :style="{ borderInlineStartWidth: '3px', borderInlineStartColor: sevHex(f.sev) }"
            @click="go(f.route)"
          >
            <span class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 text-[13px] font-bold tabular-nums"
                  :style="{ background: sevTint(f.sev), color: sevHex(f.sev) }">
              {{ f.count > 999 ? "1k+" : f.count }}
            </span>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[13.5px] font-semibold text-stone-900">{{ f.title }}</span>
                <span v-if="f.value" class="text-[11px] font-semibold text-stone-500 tabular-nums">{{ fmt(f.value) }} MAD</span>
              </div>
              <p class="text-[12.5px] text-stone-600 mt-0.5 leading-relaxed">{{ f.detail }}</p>
            </div>
            <Icon name="chevron-right" :size="15" class="text-stone-300 rtl:rotate-180 flex-shrink-0 mt-2" />
          </button>
        </div>

        <div v-else class="p-8 text-center">
          <div class="text-[13.5px] font-semibold text-stone-900">Couldn't scan</div>
          <button class="mt-3 h-9 px-4 rounded-lg text-[13px] font-semibold text-white bg-stone-800" @click="load">Retry</button>
        </div>
      </section>

      <!-- Alert history (what the engine notified about) -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <header class="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
          <h3 class="text-[13.5px] font-semibold text-stone-900">Alert history</h3>
          <span class="text-[11px] text-stone-400">sent to managers</span>
        </header>
        <div class="divide-y divide-stone-100 max-h-[560px] overflow-y-auto">
          <div v-for="(a, i) in alerts" :key="i" class="flex items-start gap-3 p-3.5">
            <span class="mt-1 w-2 h-2 rounded-full flex-shrink-0" :style="{ background: sevHex(a.sev) }" />
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-semibold text-stone-900 leading-snug">{{ a.title }}</div>
              <p class="text-[11.5px] text-stone-500 mt-0.5">{{ a.body }} · {{ a.t }}</p>
            </div>
          </div>
          <div v-if="!alerts.length" class="p-8 text-center text-[12.5px] text-stone-400">
            No alerts fired yet.
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { WAREHOUSE } from "@/lib/handoffData";
import { api } from "@/lib/resource";

const router = useRouter();

const radar = ref(null);
const alerts = ref([]);
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const [r, a] = await Promise.all([
      api("audit.problem_radar"),
      api("audit.recent_alerts").catch(() => []),
    ]);
    if (r && Array.isArray(r.findings)) radar.value = r;
    alerts.value = Array.isArray(a) ? a.filter((x) => x.kind === "alert") : [];
  } catch (_) {
    /* error card shows */
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const SEV = {
  critical: { hex: "#e11d48", tint: "#ffe4e6", icon: "alert-triangle" },
  warning:  { hex: "#d97706", tint: "#fef3c7", icon: "alert-circle" },
  info:     { hex: "#7c3aed", tint: "#ede9fe", icon: "sparkles" },
  red:      { hex: "#e11d48", tint: "#ffe4e6", icon: "alert-triangle" },
  orange:   { hex: "#ea580c", tint: "#ffedd5", icon: "alert-circle" },
  yellow:   { hex: "#d97706", tint: "#fef3c7", icon: "bell" },
};
const sevHex = (s) => (SEV[s] || SEV.yellow).hex;
const sevTint = (s) => (SEV[s] || SEV.yellow).tint;

const severities = computed(() => [
  { key: "critical", label: "Critical", icon: "alert-triangle", hex: "#e11d48", tint: "#ffe4e6", count: radar.value?.critical ?? 0 },
  { key: "warning", label: "Warning", icon: "alert-circle", hex: "#d97706", tint: "#fef3c7", count: radar.value?.warning ?? 0 },
  { key: "info", label: "Opportunities", icon: "sparkles", hex: "#7c3aed", tint: "#ede9fe", count: radar.value?.info ?? 0 },
]);

function go(route) {
  if (route) router.push(route);
}
function fmt(v) {
  return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
}
</script>
