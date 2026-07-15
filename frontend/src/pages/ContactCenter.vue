<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1200px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cco.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cco.intro') }}</p>
      </div>
      <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
              :disabled="loading" @click="load">
        <Icon name="refresh-cw" :size="13" class="inline -mt-px me-1.5" />{{ t('common.refresh') }}
      </button>
    </header>

    <div v-if="loading" class="grid md:grid-cols-3 gap-3">
      <div v-for="n in 3" :key="n" class="h-[190px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="denied" class="bg-white rounded-2xl ring-1 ring-amber-200/70 p-8 text-center">
      <Icon name="shield-alert" :size="24" class="mx-auto mb-2 text-amber-500" />
      <div class="text-[13px] text-stone-600">{{ t('cfr.denied') }}</div>
    </div>

    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[420px] mx-auto break-words">{{ loadError }}</div>
    </div>

    <template v-else-if="d">
      <div class="grid md:grid-cols-3 gap-3">
        <!-- Lane 1: confirmation -->
        <RouterLink :to="{ name: 'Confirmation' }" class="cco-card group">
          <div class="flex items-center gap-2.5">
            <span class="cco-ico" style="background: linear-gradient(135deg, var(--accent-400), var(--accent-600))"><Icon name="phone" :size="16" /></span>
            <span class="text-[13.5px] font-bold text-stone-900">{{ t('nav.confirmSection') }}</span>
            <span v-if="d.cf.breached" class="cco-breach">{{ d.cf.breached }} {{ t('cco.late') }}</span>
          </div>
          <div class="flex flex-wrap gap-1.5 mt-3">
            <span class="cco-chip"><b>{{ d.cf.counts.pending }}</b> {{ t('cf.tabPending') }}</span>
            <span class="cco-chip"><b>{{ d.cf.counts.dna }}</b> {{ t('cf.tabDna') }}</span>
            <span class="cco-chip"><b>{{ d.cf.counts.followup }}</b> {{ t('cf.tabFollowup') }}</span>
            <span class="cco-chip"><b>{{ d.cf.counts.onhold }}</b> {{ t('cf.tabOnhold') }}</span>
          </div>
          <div class="cco-today">
            <span class="text-emerald-600 font-bold tabular-nums">{{ d.cf.today.confirm || 0 }}</span> {{ t('cco.confirmedToday') }}
            <span class="text-stone-300 mx-1">·</span>
            <span class="text-rose-600 font-bold tabular-nums">{{ d.cf.today.cancel || 0 }}</span> {{ t('cco.cancelledToday') }}
          </div>
        </RouterLink>

        <!-- Lane 2: rescue -->
        <RouterLink :to="{ name: 'Rescue' }" class="cco-card group">
          <div class="flex items-center gap-2.5">
            <span class="cco-ico" style="background: linear-gradient(135deg, rgb(56 189 248), rgb(2 132 199))"><Icon name="route" :size="16" /></span>
            <span class="text-[13.5px] font-bold text-stone-900">{{ t('nav.rescueSection') }}</span>
            <span v-if="d.rs.breached" class="cco-breach">{{ d.rs.breached }} {{ t('cco.late') }}</span>
          </div>
          <div class="flex flex-wrap gap-1.5 mt-3">
            <span class="cco-chip"><b>{{ d.rs.counts.exceptions }}</b> {{ t('rs.tabExceptions') }}</span>
            <span class="cco-chip"><b>{{ d.rs.counts.failed }}</b> {{ t('rs.tabFailed') }}</span>
            <span class="cco-chip"><b>{{ d.rs.counts.backlog }}</b> {{ t('rs.tabBacklog') }}</span>
          </div>
          <div class="cco-today">
            <span class="text-emerald-600 font-bold tabular-nums">{{ (d.rs.today.redeliver || 0) + (d.rs.today.reship || 0) }}</span> {{ t('cco.savedToday') }}
            <span class="text-stone-300 mx-1">·</span>
            <span class="text-rose-600 font-bold tabular-nums">{{ (d.rs.today.returnreq || 0) + (d.rs.today.cancel || 0) }}</span> {{ t('cco.lostToday') }}
          </div>
        </RouterLink>

        <!-- Lane 3: tickets -->
        <RouterLink :to="{ name: 'Tickets' }" class="cco-card group">
          <div class="flex items-center gap-2.5">
            <span class="cco-ico" style="background: linear-gradient(135deg, rgb(139 92 246), rgb(109 40 217))"><Icon name="message-circle" :size="16" /></span>
            <span class="text-[13.5px] font-bold text-stone-900">{{ t('nav.ticketsSection') }}</span>
            <span v-if="d.cs.breached" class="cco-breach">{{ d.cs.breached }} {{ t('cco.late') }}</span>
          </div>
          <div class="flex flex-wrap gap-1.5 mt-3">
            <span class="cco-chip"><b>{{ d.cs.inbox }}</b> {{ t('cs.tabInbox') }}</span>
            <span class="cco-chip"><b>{{ d.cs.open }}</b> {{ t('cs.tabOpen') }}</span>
            <span class="cco-chip"><b>{{ d.cs.resolved7 }}</b> {{ t('cco.resolved7') }}</span>
          </div>
          <div class="cco-today">
            <span class="text-emerald-600 font-bold tabular-nums">{{ d.cs.today.resolve || 0 }}</span> {{ t('cco.resolvedToday') }}
            <span class="text-stone-300 mx-1">·</span>
            <span class="text-violet-600 font-bold tabular-nums">{{ d.cs.today.create || 0 }}</span> {{ t('cco.openedToday') }}
          </div>
        </RouterLink>
      </div>

      <!-- leaderboard -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
          <Icon name="trending-up" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('cco.leaderboard') }}</span>
          <span class="text-[11px] text-stone-400">7{{ t('cf.days') }}</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[640px] text-[12.5px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('cfr.thAgent') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('nav.confirmation') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('nav.rescue') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('nav.tickets') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('cfr.thTotal') }}</th>
                <th class="text-end px-4 py-2.5">{{ t('cco.thWins') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="(a, i) in d.leaderboard" :key="a.user" class="hover:bg-stone-50">
                <td class="px-4 py-2.5">
                  <span class="inline-flex items-center gap-2">
                    <span class="w-5 h-5 rounded-full text-[10px] font-bold inline-flex items-center justify-center"
                          :class="i === 0 ? 'bg-amber-100 text-amber-700' : 'bg-stone-100 text-stone-500'">{{ i + 1 }}</span>
                    <span class="font-medium text-stone-900">{{ a.agent }}</span>
                  </span>
                </td>
                <td class="px-3 py-2.5 text-end tabular-nums text-stone-600">{{ a.cf || '—' }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-stone-600">{{ a.rs || '—' }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-stone-600">{{ a.cs || '—' }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums font-semibold text-stone-900">{{ a.total }}</td>
                <td class="px-4 py-2.5 text-end tabular-nums font-bold text-emerald-600">{{ a.wins }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!d.leaderboard.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('cfr.noData') }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { warn } = useToast();

const d = ref(null);
const loading = ref(true);
const denied = ref(false);
const loadError = ref("");

async function load() {
  loading.value = true;
  denied.value = false;
  loadError.value = "";
  try {
    d.value = await api("contact_center.overview");
  } catch (e) {
    const msg = String(e.message || e);
    if (/section admin|PermissionError|403/i.test(msg)) denied.value = true;
    else { loadError.value = msg; warn(t("cf.loadFail"), msg); }
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
.cco-card {
  display: block; background: white; border-radius: 16px; padding: 16px;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8), 0 1px 2px rgb(0 0 0 / 0.02);
  transition: box-shadow .18s ease, transform .18s ease;
}
.cco-card:hover {
  box-shadow: inset 0 0 0 1px rgb(214 211 209), 0 8px 24px -12px rgb(0 0 0 / 0.14);
  transform: translateY(-1px);
}
.cco-ico {
  width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center; color: white;
}
.cco-chip {
  font-size: 11.5px; color: rgb(87 83 78); background: rgb(250 250 249);
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  border-radius: 999px; padding: 3px 10px;
  font-variant-numeric: tabular-nums;
}
.cco-chip b { color: rgb(28 25 23); font-weight: 700; }
.cco-breach {
  margin-inline-start: auto;
  font-size: 10px; font-weight: 800; color: white; background: rgb(244 63 94);
  padding: 2px 8px; border-radius: 999px; white-space: nowrap;
  animation: cco-pulse 2s ease-in-out infinite;
}
@keyframes cco-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .55; } }
.cco-today {
  margin-top: 12px; padding-top: 10px;
  border-top: 1px solid rgb(245 245 244);
  font-size: 11.5px; color: rgb(120 113 108);
}
</style>
