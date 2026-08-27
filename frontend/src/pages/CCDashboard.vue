<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1200px] mx-auto">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('ccd.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">{{ t('ccd.intro') }}</p>
      </div>
      <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
              :disabled="loading" @click="load">
        <Icon name="refresh-cw" :size="13" />{{ t('common.refresh') }}
      </button>
    </header>

    <div v-if="loading && !d" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <span v-for="n in 4" :key="n" class="h-[92px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="loadError" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('cf.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <template v-else-if="d">
      <!-- SPEED hero -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="bg-white rounded-2xl ring-1 p-4" :class="todayH > 2 ? 'ring-rose-200' : 'ring-emerald-200'">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('ccd.firstTouchToday') }}</div>
          <div class="text-[26px] font-bold tabular-nums mt-1" :class="todayH > 2 ? 'text-rose-600' : 'text-emerald-600'">
            {{ d.speed.todayMin === null ? '—' : todayH + 'h' }}
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ t('ccd.onN').replace('{n}', String(d.speed.todayN)) }}</div>
        </div>
        <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('ccd.firstTouch7d') }}</div>
          <div class="text-[26px] font-bold tabular-nums text-stone-900 mt-1">{{ d.speed.weekMin === null ? '—' : weekH + 'h' }}</div>
          <div class="text-[11px] tabular-nums" :class="deltaClass">{{ deltaLabel }}</div>
        </div>
        <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('ccd.decidedToday') }}</div>
          <div class="text-[26px] font-bold tabular-nums text-stone-900 mt-1">{{ teamToday }}</div>
          <div class="text-[11px] text-stone-400 tabular-nums">+ {{ d.automationToday }} {{ t('ccd.byAutomation') }}</div>
        </div>
        <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('ccd.outcomesToday') }}</div>
          <div class="text-[18px] font-bold tabular-nums mt-1.5">
            <span class="text-emerald-600">{{ d.outcomes.confirmed }}</span>
            <span class="text-[12px] text-stone-400 font-medium mx-1">{{ t('ccd.vs') }}</span>
            <span class="text-rose-600">{{ d.outcomes.cancelled }}</span>
          </div>
          <div class="text-[11px] text-stone-400">{{ t('ccd.confVsCanc') }}</div>
        </div>
      </div>

      <!-- 14-day first-touch trend -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-3">
          <Icon name="trending-up" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('ccd.trendTitle') }}</span>
          <span class="text-[11px] text-stone-400 hidden sm:inline">{{ t('ccd.trendHint') }}</span>
        </div>
        <div class="flex items-end gap-1 h-[88px]">
          <div v-for="p in d.speed.trend" :key="p.d" class="flex-1 flex flex-col items-center gap-0.5 min-w-0"
               :title="`${p.d} · ${Math.round(p.min / 60 * 10) / 10}h · ${p.n}`">
            <div class="w-full rounded-t transition-all"
                 :class="p.min > 120 ? 'bg-rose-300' : 'bg-emerald-300'"
                 :style="{ height: trendH(p.min) }" />
            <span class="text-[8.5px] text-stone-400 tabular-nums">{{ p.d.slice(8) }}</span>
          </div>
        </div>
        <div class="flex items-center gap-4 mt-2 text-[11px] text-stone-500">
          <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-300 me-1" />&le;2h</span>
          <span><span class="inline-block w-2 h-2 rounded-full bg-rose-300 me-1" />&gt;2h</span>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-4 items-start">
        <!-- who is working NOW -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <Icon name="users" :size="14" class="text-[var(--accent-600)]" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('ccd.teamTitle') }}</span>
            <span class="text-[11px] text-stone-400">{{ t('ccd.teamHint') }}</span>
          </div>
          <div v-if="d.team.length" class="overflow-x-auto">
            <table class="w-full text-[12.5px]">
              <thead>
                <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                  <th class="text-start px-4 py-2">{{ t('ccd.thAgent') }}</th>
                  <th class="text-end px-3 py-2">{{ t('ccd.thToday') }}</th>
                  <th class="text-end px-3 py-2">{{ t('ccd.thPerHour') }}</th>
                  <th class="text-end px-4 py-2">{{ t('ccd.thLast') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-stone-50">
                <tr v-for="a in d.team" :key="a.user">
                  <td class="px-4 py-2">
                    <span class="inline-flex items-center gap-1.5">
                      <span class="w-2 h-2 rounded-full" :class="a.activeNow ? 'bg-emerald-500' : 'bg-stone-300'" />
                      <span class="font-medium text-stone-800">{{ a.agent }}</span>
                    </span>
                  </td>
                  <td class="px-3 py-2 text-end font-bold tabular-nums text-stone-900">{{ a.today }}</td>
                  <td class="px-3 py-2 text-end tabular-nums text-stone-600">{{ a.perHour }}</td>
                  <td class="px-4 py-2 text-end tabular-nums text-stone-500">{{ a.lastAt }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-center text-[12.5px] text-stone-400 py-8">{{ t('ccd.teamNone') }}</div>
        </div>

        <!-- the fire -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-2.5 lg:sticky lg:top-3">
          <div class="text-[12px] font-semibold text-stone-900 flex items-center gap-2">
            <Icon name="alert-triangle" :size="14" class="text-amber-600" />{{ t('ccd.fireTitle') }}
          </div>
          <RouterLink :to="{ name: 'Workspace' }" class="ccd-fire">
            <span>{{ t('ccd.fPending') }}</span>
            <b class="tabular-nums">{{ d.fire.pending }}</b>
          </RouterLink>
          <RouterLink :to="{ name: 'Confirmation' }" class="ccd-fire" :class="d.fire.pendingLate ? 'ccd-hot' : ''">
            <span>{{ t('ccd.fLate').replace('{h}', String(d.slaH)) }}</span>
            <b class="tabular-nums">{{ d.fire.pendingLate }}</b>
          </RouterLink>
          <RouterLink :to="{ name: 'Workspace' }" class="ccd-fire" :class="d.fire.dueRetries ? 'ccd-hot' : ''">
            <span>{{ t('ccd.fDue') }}</span>
            <b class="tabular-nums">{{ d.fire.dueRetries }}</b>
          </RouterLink>
          <RouterLink :to="{ name: 'Rescue' }" class="ccd-fire">
            <span>{{ t('ccd.fRescue') }}</span>
            <b class="tabular-nums">{{ d.fire.rescueOpen }}</b>
          </RouterLink>
          <RouterLink :to="{ name: 'Tickets' }" class="ccd-fire" :class="d.fire.waUnhandled > 100 ? 'ccd-hot' : ''">
            <span>{{ t('ccd.fWa') }}</span>
            <b class="tabular-nums">{{ d.fire.waUnhandled }}</b>
          </RouterLink>
        </div>
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

const todayH = computed(() => Math.round(((d.value?.speed?.todayMin || 0) / 60) * 10) / 10);
const weekH = computed(() => Math.round(((d.value?.speed?.weekMin || 0) / 60) * 10) / 10);
const teamToday = computed(() => (d.value?.team || []).reduce((a, x) => a + x.today, 0));
const deltaClass = computed(() => {
  if (d.value?.speed?.todayMin == null || d.value?.speed?.weekMin == null) return "text-stone-400";
  return d.value.speed.todayMin <= d.value.speed.weekMin ? "text-emerald-600" : "text-rose-600";
});
const deltaLabel = computed(() => {
  const s = d.value?.speed;
  if (!s || s.todayMin == null || s.weekMin == null) return t("ccd.noData");
  const diff = Math.round(((s.weekMin - s.todayMin) / 60) * 10) / 10;
  return diff >= 0 ? t("ccd.faster").replace("{h}", String(Math.abs(diff)))
    : t("ccd.slower").replace("{h}", String(Math.abs(diff)));
});
const trendMax = computed(() =>
  Math.max(60, ...(d.value?.speed?.trend || []).map((p) => p.min)));
function trendH(min) { return Math.max(4, Math.round((min / trendMax.value) * 72)) + "px"; }

async function load() {
  loading.value = true;
  try {
    d.value = await api("contact_center.speed_dashboard");
    loadError.value = "";
  } catch (e) {
    loadError.value = String(e.message || e);
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

<style scoped>
.ccd-fire {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; border-radius: 10px; font-size: 12.5px;
  color: rgb(68 64 60); background: rgb(250 250 249);
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / .7);
  transition: background-color .15s;
}
.ccd-fire:hover { background: rgb(245 245 244); }
.ccd-hot {
  color: rgb(190 18 60); background: rgb(255 241 242);
  box-shadow: inset 0 0 0 1px rgb(254 205 211 / .7);
}
</style>
