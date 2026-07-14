<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <!-- Title -->
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t('px.aud.title') }}</h1>
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
          <h3 class="text-[13.5px] font-semibold text-stone-900">{{ t('px.aud.radar') }}</h3>
          <span class="text-[11px] text-stone-400">deterministic · windowed · cached 2 min</span>
        </header>

        <div v-if="loading && !radar" class="p-4 space-y-2.5">
          <div v-for="n in 5" :key="n" class="h-[72px] rounded-xl ring-1 ring-stone-200/60 bg-stone-50 animate-pulse" />
        </div>

        <div v-else-if="radar && !radar.findings.length" class="p-10 text-center">
          <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3">
            <Icon name="check-circle" :size="22" />
          </span>
          <div class="text-[14.5px] font-semibold text-stone-900">{{ t('px.aud.clean') }}</div>
          <div class="text-[12.5px] text-stone-500 mt-1">{{ t('px.aud.cleanSub') }}</div>
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
          <div class="text-[13.5px] font-semibold text-stone-900">{{ t('px.aud.scanFail') }}</div>
          <button class="mt-3 h-9 px-4 rounded-lg text-[13px] font-semibold text-white bg-stone-800" @click="load">Retry</button>
        </div>
      </section>

      <!-- Right column: AI digest + alert history -->
      <div class="space-y-4">
      <!-- Layer B: LLM daily digest -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <header class="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
          <h3 class="text-[13.5px] font-semibold text-stone-900 flex items-center gap-1.5">
            <Icon name="sparkles" :size="14" class="text-violet-500" /> {{ t('px.aud.aiTitle') }}
          </h3>
          <button
            v-if="ai.configured"
            class="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-[11.5px] font-semibold text-violet-700 bg-violet-50 hover:bg-violet-100 transition-colors"
            :class="aiBusy ? 'opacity-60 pointer-events-none' : ''"
            @click="genDigest"
          >
            <Icon name="refresh-cw" :size="11" :class="aiBusy ? 'animate-spin' : ''" />
            {{ aiBusy ? "Thinking…" : "Generate now" }}
          </button>
        </header>

        <div v-if="aiLoading" class="p-4 space-y-2">
          <div v-for="n in 3" :key="n" class="h-[56px] rounded-xl ring-1 ring-stone-200/60 bg-stone-50 animate-pulse" />
        </div>

        <div v-else-if="!ai.configured" class="p-5 text-[12.5px] text-stone-500 leading-relaxed">
          <template v-if="ai.reason === 'sdk_missing'">
            Key found on the server — install the SDK to activate:
            <code class="block mt-2 px-2.5 py-1.5 rounded-lg bg-stone-100 text-stone-700 text-[11.5px] font-mono" dir="ltr">bench pip install anthropic &amp;&amp; bench restart</code>
          </template>
          <template v-else>
            Add <code class="px-1 rounded bg-stone-100 text-[11.5px] font-mono">anthropic_api_key</code> to site_config to activate the daily digest.
          </template>
        </div>

        <div v-else-if="!ai.digest" class="p-5 text-center">
          <p class="text-[12.5px] text-stone-500">No digest yet — it generates automatically at end of day.</p>
          <button class="mt-3 h-8 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-violet-600 hover:bg-violet-700"
                  :class="aiBusy ? 'opacity-60 pointer-events-none' : ''" @click="genDigest">
            {{ aiBusy ? "Thinking…" : "Generate the first one" }}
          </button>
        </div>

        <div v-else>
          <p class="px-4 pt-3.5 pb-1 text-[12.5px] text-stone-700 leading-relaxed" dir="auto">{{ ai.digest.summary }}</p>
          <div class="divide-y divide-stone-100">
            <div v-for="(it, i) in ai.digest.items" :key="i" class="flex items-start gap-2.5 px-4 py-3">
              <span class="mt-1.5 w-2 h-2 rounded-full flex-shrink-0" :style="{ background: aiSevHex(it.sev) }" />
              <div class="min-w-0" dir="auto">
                <div class="text-[12.5px] font-semibold text-stone-900 leading-snug">{{ it.title }}</div>
                <p class="text-[11.5px] text-stone-500 mt-0.5 leading-relaxed">{{ it.detail }}</p>
              </div>
            </div>
          </div>
          <div class="px-4 py-2.5 border-t border-stone-100 text-[10.5px] text-stone-400" dir="ltr">
            {{ ai.digest.generatedAt }} · {{ ai.digest.model }}
          </div>
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
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { WAREHOUSE } from "@/lib/handoffData";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
const { t } = useI18n();

const router = useRouter();

const radar = ref(null);
const alerts = ref([]);
const loading = ref(true);

// ── Layer B: LLM daily digest ────────────────────────────────────────
const ai = ref({ configured: false, reason: null, digest: null });
const aiLoading = ref(true);
const aiBusy = ref(false);

async function loadAI() {
  try {
    const r = await api("audit.daily_insights");
    if (r && typeof r === "object") ai.value = r;
  } catch (_) { /* panel shows setup hint */ } finally {
    aiLoading.value = false;
  }
}
onMounted(loadAI);

async function genDigest() {
  if (aiBusy.value) return;
  aiBusy.value = true;
  try {
    const r = await apiPost("audit.run_daily_digest");
    if (r && typeof r === "object") ai.value = r;
  } catch (_) { /* server logged it */ } finally {
    aiBusy.value = false;
  }
}

const AI_SEV = { act: "#e11d48", watch: "#d97706", good: "#059669" };
const aiSevHex = (s) => AI_SEV[s] || "#a8a29e";

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
