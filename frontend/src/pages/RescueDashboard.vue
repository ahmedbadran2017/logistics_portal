<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1100px] mx-auto">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('rsd.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">{{ t('rsd.intro') }}</p>
      </div>
      <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
              :disabled="loading" @click="load">
        <Icon name="refresh-cw" :size="13" />{{ t('common.refresh', 'Refresh') }}
      </button>
    </header>

    <div v-if="loading && !d" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <span v-for="n in 4" :key="n" class="h-[84px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="loadError" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('cf.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <template v-else-if="d">
      <!-- queue depth cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <RouterLink v-for="c in cardDefs" :key="c.key" :to="{ name: 'Rescue' }"
                    class="bg-white rounded-2xl ring-1 p-4 hover:shadow-sm transition-shadow"
                    :class="c.hot && d.cards[c.key].n ? 'ring-rose-200' : 'ring-stone-200/70'">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t(c.label) }}</div>
          <div class="text-[22px] font-bold tabular-nums mt-1" :class="c.hot && d.cards[c.key].n ? 'text-rose-600' : 'text-stone-900'">
            {{ d.cards[c.key].n.toLocaleString() }}
          </div>
          <div class="text-[11.5px] text-stone-500 mt-0.5 tabular-nums">{{ d.cards[c.key].value.toLocaleString() }} MAD</div>
        </RouterLink>
      </div>

      <!-- age spread + breach -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-3">
          <Icon name="clock" :size="14" class="text-amber-600" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('rsd.agesTitle') }}</span>
          <span class="ms-auto text-[11.5px] font-bold rounded-md px-2 py-0.5 ring-1"
                :class="d.ages.breached ? 'text-rose-700 bg-rose-50 ring-rose-200/70' : 'text-emerald-700 bg-emerald-50 ring-emerald-200/70'">
            {{ t('rsd.breached').replace('{n}', String(d.ages.breached)).replace('{h}', String(d.slaH)) }}
          </span>
        </div>
        <div class="flex h-3 rounded-full overflow-hidden bg-stone-100">
          <div class="bg-emerald-400" :style="{ width: agePct(d.ages.d1) }" />
          <div class="bg-amber-400" :style="{ width: agePct(d.ages.d3) }" />
          <div class="bg-rose-500" :style="{ width: agePct(d.ages.older) }" />
        </div>
        <div class="flex items-center gap-4 mt-2 text-[11.5px] text-stone-500 tabular-nums flex-wrap">
          <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-400 me-1" />&le;24h · {{ d.ages.d1 }}</span>
          <span><span class="inline-block w-2 h-2 rounded-full bg-amber-400 me-1" />1–3d · {{ d.ages.d3 }}</span>
          <span><span class="inline-block w-2 h-2 rounded-full bg-rose-500 me-1" />&gt;3d · {{ d.ages.older }}</span>
        </div>
      </div>

      <!-- inflow vs decided, 14d -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-3">
          <Icon name="trending-up" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('rsd.dailyTitle') }}</span>
          <span class="text-[11px] text-stone-400 hidden sm:inline">{{ t('rsd.dailyHint') }}</span>
        </div>
        <div class="flex items-end gap-1 h-[96px]">
          <div v-for="p in d.daily" :key="p.d" class="flex-1 flex flex-col items-center gap-0.5 min-w-0" :title="`${p.d} · ${p.inflow} / ${p.decided}`">
            <div class="w-full flex items-end gap-px h-[76px]">
              <div class="flex-1 bg-rose-300 rounded-t" :style="{ height: barH(p.inflow) }" />
              <div class="flex-1 bg-emerald-400 rounded-t" :style="{ height: barH(p.decided) }" />
            </div>
            <span class="text-[8.5px] text-stone-400 tabular-nums">{{ p.d.slice(8) }}</span>
          </div>
        </div>
        <div class="flex items-center gap-4 mt-2 text-[11px] text-stone-500">
          <span><span class="inline-block w-2 h-2 rounded-full bg-rose-300 me-1" />{{ t('rsd.inflow') }}</span>
          <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-400 me-1" />{{ t('rsd.decided') }}</span>
        </div>
      </div>

      <!-- the call list: oldest untouched failures -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
          <Icon name="alert-triangle" :size="14" class="text-rose-500" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('rsd.oldestTitle') }}</span>
        </div>
        <div v-if="d.oldest.length" class="divide-y divide-stone-100">
          <div v-for="r in d.oldest" :key="r.dn" class="px-4 py-2.5 flex items-center gap-3 flex-wrap">
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-semibold text-stone-900 truncate">{{ r.customer || r.order || r.dn }}</div>
              <div class="text-[11px] text-stone-400 font-mono truncate">{{ r.order || r.dn }} · {{ r.track }}</div>
            </div>
            <a v-if="r.phone" :href="'tel:' + r.phone" class="text-[11.5px] font-mono text-sky-700">{{ r.phone }}</a>
            <span class="text-[11.5px] tabular-nums text-stone-500">{{ r.value.toLocaleString() }} MAD</span>
            <span class="text-[11.5px] font-bold tabular-nums" :class="r.ageD > 3 ? 'text-rose-600' : 'text-amber-600'">{{ r.ageD }}d</span>
            <span class="text-[10.5px] text-stone-400 tabular-nums">×{{ r.attempts }}</span>
          </div>
        </div>
        <div v-else class="text-center text-[12.5px] text-emerald-600 py-8">{{ t('rsd.oldestNone') }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const d = ref(null);
const loading = ref(true);
const loadError = ref("");

const cardDefs = [
  { key: "exceptions", label: "rs.tabExceptions", hot: true },
  { key: "failed", label: "rs.tabFailed", hot: true },
  { key: "stale", label: "rs.tabStale", hot: false },
  { key: "backlog", label: "rs.tabBacklog", hot: false },
];

const ageTotal = computed(() => {
  const a = d.value?.ages;
  return a ? Math.max(1, a.d1 + a.d3 + a.older) : 1;
});
function agePct(n) { return Math.round((n / ageTotal.value) * 100) + "%"; }
const dailyMax = computed(() =>
  Math.max(1, ...(d.value?.daily || []).flatMap((p) => [p.inflow, p.decided])));
function barH(n) { return Math.max(n ? 6 : 2, Math.round((n / dailyMax.value) * 76)) + "px"; }

async function load() {
  loading.value = true;
  try {
    d.value = await api("rescue.dashboard");
    loadError.value = "";
  } catch (e) {
    if (!d.value) loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
const timer = setInterval(() => {
  if (document.visibilityState === "visible" && !loading.value) load();
}, 120000);
onUnmounted(() => clearInterval(timer));
</script>
