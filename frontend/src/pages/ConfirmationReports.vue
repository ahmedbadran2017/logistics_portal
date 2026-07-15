<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1100px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cfr.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cfr.intro') }}</p>
      </div>
      <div class="flex items-center gap-1">
        <button v-for="d in [7, 14, 30]" :key="d"
                class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                :class="days === d ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200'"
                @click="days = d; load()">{{ d }}{{ t('cf.days') }}</button>
      </div>
    </header>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 4" :key="n" class="h-[56px] rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="denied" class="bg-white rounded-2xl ring-1 ring-amber-200/70 p-8 text-center">
      <Icon name="shield-alert" :size="24" class="mx-auto mb-2 text-amber-500" />
      <div class="text-[13px] text-stone-600">{{ t('cfr.denied') }}</div>
    </div>

    <template v-else-if="data">
      <!-- per-agent table -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-900">{{ t('cfr.agentsTitle') }}</div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[720px] text-[12.5px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('cfr.thAgent') }}</th>
                <th class="text-end px-3 py-2.5">✓ {{ t('cf.actConfirm') }}</th>
                <th class="text-end px-3 py-2.5">✕ {{ t('cf.actCancel') }}</th>
                <th class="text-end px-3 py-2.5">📵 {{ t('cf.actDna') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('cfr.thTotal') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('cfr.thRate') }}</th>
                <th class="text-end px-4 py-2.5">{{ t('cfr.thAttempts') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="a in data.agents" :key="a.user" class="hover:bg-stone-50">
                <td class="px-4 py-2.5 font-medium text-stone-900">{{ a.agent }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums font-semibold text-emerald-600">{{ a.confirm }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-rose-600">{{ a.cancel }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-amber-600">{{ a.dna }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums font-semibold text-stone-900">{{ a.total }}</td>
                <td class="px-3 py-2.5 text-end">
                  <div class="flex items-center justify-end gap-2">
                    <div class="w-[64px] h-1.5 rounded-full bg-stone-100 overflow-hidden">
                      <div class="h-full rounded-full transition-all"
                           :class="a.confirmRate >= 70 ? 'bg-emerald-500' : a.confirmRate >= 50 ? 'bg-amber-500' : 'bg-rose-500'"
                           :style="{ width: a.confirmRate + '%' }" />
                    </div>
                    <span class="tabular-nums font-semibold w-[44px]"
                          :class="a.confirmRate >= 70 ? 'text-emerald-600' : a.confirmRate >= 50 ? 'text-amber-600' : 'text-rose-600'">
                      {{ a.confirmRate }}%
                    </span>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-end tabular-nums text-stone-600">{{ a.avgAttempts }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!data.agents.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('cfr.noData') }}</div>
      </div>

      <div class="grid md:grid-cols-2 gap-3">
        <!-- cancel reasons -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-900">{{ t('cfr.reasonsTitle') }}</div>
          <div class="divide-y divide-stone-50">
            <div v-for="r in data.reasons" :key="r.reason" class="px-4 py-2 flex items-center gap-2 text-[12.5px]">
              <span class="flex-1 text-stone-700 truncate">{{ r.reason }}</span>
              <span class="font-bold tabular-nums text-stone-900">{{ r.n }}</span>
            </div>
            <div v-if="!data.reasons.length" class="text-center text-[12px] text-stone-400 py-6">—</div>
          </div>
        </div>
        <!-- daily funnel -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-900">{{ t('cfr.funnelTitle') }}</div>
          <div class="divide-y divide-stone-50">
            <div v-for="f in [...data.funnel].reverse()" :key="f.date" class="px-4 py-2 space-y-1">
              <div class="flex items-center gap-3 text-[12px] tabular-nums">
                <span class="text-stone-500 w-[64px]">{{ f.date.slice(5) }}</span>
                <span class="text-emerald-600 font-semibold">✓ {{ f.confirm }}</span>
                <span class="text-rose-600">✕ {{ f.cancel }}</span>
                <span class="text-amber-600">📵 {{ f.dna }}</span>
              </div>
              <div class="flex h-1.5 rounded-full overflow-hidden bg-stone-100 ms-[76px]">
                <div class="bg-emerald-500" :style="{ width: barW(f.confirm) }" />
                <div class="bg-rose-400" :style="{ width: barW(f.cancel) }" />
                <div class="bg-amber-400" :style="{ width: barW(f.dna) }" />
              </div>
            </div>
            <div v-if="!data.funnel.length" class="text-center text-[12px] text-stone-400 py-6">—</div>
          </div>
        </div>
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

const days = ref(7);
const data = ref(null);
const loading = ref(true);
const denied = ref(false);

function barW(n) {
  const max = Math.max(1, ...(data.value?.funnel || []).map((f) => f.confirm + f.cancel + f.dna));
  return Math.round((n / max) * 100) + "%";
}

async function load() {
  loading.value = true;
  denied.value = false;
  try {
    data.value = await api("confirmation.report", { days: days.value });
  } catch (e) {
    const msg = String(e.message || e);
    if (/section admin|PermissionError|403/i.test(msg)) denied.value = true;
    else warn(t("cf.loadFail"), msg);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>
