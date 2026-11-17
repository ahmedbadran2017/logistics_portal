<template>
  <!-- The launch board: every souk product from purchase to Live, one column
       per stage, oldest first. A card is late when it sits in its stage past
       the stage's days; past 21 days from purchase without Live it escalates.
       Backend: souk.board -->
  <div class="px-4 py-5 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900">{{ t('souk.boardTitle') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[680px]">{{ t('souk.boardIntro') }}</p>
      </div>
      <div class="flex gap-2">
        <router-link :to="{ name: 'SoukTrip' }" class="h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center gap-1.5">
          <Icon name="wallet" :size="14" />{{ t('souk.custody') }}
        </router-link>
        <router-link v-if="data?.canBuy" :to="{ name: 'SoukBuy' }" class="h-9 px-3 rounded-lg bg-[#c4301c] text-white text-[12.5px] font-bold inline-flex items-center">+ {{ t('souk.product') }}</router-link>
        <button class="h-9 px-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] font-semibold inline-flex items-center gap-1.5" :disabled="loading" @click="load">
          <Icon name="rotate-ccw" :size="14" />
        </button>
      </div>
    </header>

    <div v-if="data" class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4">
        <div class="text-[11px] font-semibold text-stone-500">{{ t('souk.kNotLive') }}</div>
        <div class="text-[22px] font-extrabold tabular-nums">{{ fmt(data.notLive) }} <small class="text-[12px] text-stone-400">MAD</small></div>
      </div>
      <div class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4">
        <div class="text-[11px] font-semibold text-stone-500">{{ t('souk.kInCycle') }}</div>
        <div class="text-[22px] font-extrabold tabular-nums">{{ data.cards.filter((c) => c.stage !== 'live').length }}</div>
      </div>
      <div class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4">
        <div class="text-[11px] font-semibold text-stone-500">{{ t('souk.kLate') }}</div>
        <div class="text-[22px] font-extrabold tabular-nums" :class="data.late ? 'text-rose-600' : ''">{{ data.late }}</div>
      </div>
      <div class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4">
        <div class="text-[11px] font-semibold text-stone-500">{{ t('souk.kDropped') }}</div>
        <div class="text-[22px] font-extrabold tabular-nums">{{ data.dropped }}</div>
      </div>
    </div>

    <div v-if="loading && !data" class="h-[360px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <div v-if="data" class="overflow-x-auto pb-2">
      <div class="flex gap-3 min-w-max">
        <section v-for="s in data.stages" :key="s" class="w-[230px] shrink-0 bg-stone-100/70 rounded-2xl p-2 space-y-2">
          <div class="px-1.5 pt-1 flex items-center justify-between">
            <span class="text-[12.5px] font-bold text-stone-800">{{ t('souk.st_' + s) }}</span>
            <span class="text-[11px] text-stone-500 tabular-nums">
              {{ col(s).length }}<span v-if="data.stageDays?.[s]"> · {{ t('souk.daysMax').replace('{n}', data.stageDays[s]) }}</span>
            </span>
          </div>
          <div v-for="c in col(s)" :key="c.name" class="space-y-1">
          <router-link :to="{ name: 'SoukProduct', params: { name: c.name } }"
                       class="block bg-white rounded-xl ring-1 p-2.5 space-y-1.5 hover:ring-stone-400"
                       :class="c.late || c.escalate ? 'ring-rose-300' : 'ring-stone-200'">
            <div class="flex gap-2">
              <img v-if="c.image" :src="c.image" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200" alt="" />
              <div v-else class="w-10 h-10 rounded-lg bg-stone-100" />
              <div class="min-w-0 flex-1">
                <div class="text-[12.5px] font-semibold text-stone-900 truncate">{{ c.title }}</div>
                <div class="text-[11px] font-mono text-stone-500">{{ c.name }} · {{ c.brand }}</div>
              </div>
            </div>
            <div class="flex items-center justify-between text-[11px] tabular-nums">
              <span class="text-stone-500">{{ c.units }} {{ t('souk.pcs') }} · {{ fmt(c.cost) }}</span>
              <span class="font-bold" :class="c.late ? 'text-rose-600' : 'text-stone-500'">{{ t('souk.ageDays').replace('{n}', c.age) }}</span>
            </div>
            <div v-if="c.error" class="text-[10.5px] text-rose-700 truncate">{{ c.error }}</div>
            <div v-else-if="c.escalate" class="text-[10.5px] font-bold text-rose-700">{{ t('souk.escalate') }}</div>
          </router-link>
          <router-link v-if="c.stage === 'bought' && c.po && data.canReceive" :to="{ name: 'SoukReceive', params: { po: c.po } }"
                       class="flex h-8 rounded-lg bg-emerald-600 text-white text-[11.5px] font-bold items-center justify-center">{{ t('souk.receiveBtn') }}</router-link>
          </div>
          <div v-if="!col(s).length" class="text-center text-[11px] text-stone-400 py-4">—</div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { warn } = useToast();
const data = ref(null);
const loading = ref(true);
const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const col = (s) => (data.value?.cards || []).filter((c) => c.stage === s);

async function load() {
  loading.value = true;
  try {
    data.value = await api("souk.board");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>
