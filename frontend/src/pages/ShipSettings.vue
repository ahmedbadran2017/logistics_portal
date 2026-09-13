<template>
  <div class="max-w-[880px] mx-auto px-4 py-6 space-y-4">
    <header>
      <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('oclk.setTitle') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[600px]">{{ t('oclk.setIntro') }}</p>
    </header>

    <div v-if="loading" class="h-[300px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />

    <template v-else-if="s">
      <!-- Waves: the promise the warehouse is held to -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="flex items-center gap-2">
          <Icon name="truck" :size="15" class="text-stone-400" />
          <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setWaves') }}</span>
        </div>
        <p class="text-[11.5px] text-stone-500">{{ t('oclk.setWavesHint') }}</p>
        <div v-for="(w, i) in s.waves" :key="i" class="flex items-center gap-3 flex-wrap">
          <span class="text-[12px] font-bold text-stone-700 w-[46px] uppercase">{{ w.id }}</span>
          <label class="text-[11.5px] text-stone-500">{{ t('oclk.cutoff') }}
            <input v-model="w.cutoff" type="time" :disabled="!s.isAdmin"
                   class="ms-1.5 h-8 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" />
          </label>
          <label class="text-[11.5px] text-stone-500">{{ t('oclk.leaves') }}
            <input v-model="w.out" type="time" :disabled="!s.isAdmin"
                   class="ms-1.5 h-8 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" />
          </label>
        </div>
      </section>

      <!-- Rest days -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-2.5">
        <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setRest') }}</span>
        <p class="text-[11.5px] text-stone-500">{{ t('oclk.setRestHint') }}</p>
        <div class="flex flex-wrap gap-1.5">
          <button v-for="(dn, i) in DAYS" :key="i" :disabled="!s.isAdmin"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                  :class="s.restDays.includes(i) ? 'text-white bg-stone-900 ring-stone-900' : 'text-stone-600 bg-white ring-stone-200'"
                  @click="toggleRest(i)">{{ t('oclk.d' + i) }}</button>
        </div>
      </section>

      <!-- Per-city promise -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-3 border-b border-stone-100">
          <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setCities') }}</span>
          <p class="text-[11.5px] text-stone-500 mt-0.5">{{ t('oclk.setCitiesHint') }}</p>
        </div>
        <div class="divide-y divide-stone-50 max-h-[300px] overflow-y-auto">
          <div v-for="c in cityList" :key="c" class="px-4 py-2 flex items-center gap-3">
            <span class="text-[12px] text-stone-700 flex-1 truncate">{{ c }}</span>
            <input v-model.number="s.cityDays[c]" type="number" min="1" max="20" :disabled="!s.isAdmin"
                   class="w-16 h-8 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
            <span class="text-[11px] text-stone-400 w-[40px]">{{ t('oclk.days') }}</span>
          </div>
          <div class="px-4 py-2 flex items-center gap-3 bg-stone-50/60">
            <span class="text-[12px] font-semibold text-stone-700 flex-1">{{ t('oclk.otherCities') }}</span>
            <input v-model.number="s.defaultCityDays" type="number" min="1" max="20" :disabled="!s.isAdmin"
                   class="w-16 h-8 px-2 rounded-lg bg-white ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
            <span class="text-[11px] text-stone-400 w-[40px]">{{ t('oclk.days') }}</span>
          </div>
        </div>
      </section>

      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 flex items-center gap-3 flex-wrap">
        <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setChase') }}</span>
        <input v-model.number="s.chaseDays" type="number" min="1" max="30" :disabled="!s.isAdmin"
               class="w-16 h-8 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
        <span class="text-[11.5px] text-stone-500 flex-1 min-w-[220px]">{{ t('oclk.setChaseHint') }}</span>
      </section>

      <div v-if="s.isAdmin" class="flex items-center gap-2">
        <button class="h-10 px-5 rounded-xl text-[13px] font-bold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50"
                :disabled="busy" @click="save">{{ busy ? t('oclk.saving') : t('common.save') }}</button>
        <span class="text-[11.5px] text-stone-400">{{ t('oclk.saveHint') }}</span>
      </div>
      <p v-else class="text-[11.5px] text-stone-400">{{ t('oclk.readOnly') }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const s = ref(null);
const loading = ref(true);
const busy = ref(false);
const DAYS = [0, 1, 2, 3, 4, 5, 6];

const cityList = computed(() => Object.keys(s.value?.cityDays || {}).sort());

function toggleRest(i) {
  if (!s.value?.isAdmin) return;
  const r = s.value.restDays;
  const at = r.indexOf(i);
  if (at >= 0) r.splice(at, 1); else r.push(i);
}

async function load() {
  loading.value = true;
  try { s.value = await api("shipments.settings"); }
  catch { s.value = null; }
  loading.value = false;
}
async function save() {
  busy.value = true;
  try {
    await apiPost("shipments.save_settings", {
      payload: {
        waves: s.value.waves, restDays: s.value.restDays,
        cityDays: s.value.cityDays, defaultCityDays: s.value.defaultCityDays,
        chaseDays: s.value.chaseDays,
      },
    });
    success(t("oclk.saved"), "");
  } catch (e) { warn(t("mv.loadFail"), String(e.message || e)); }
  busy.value = false;
}
onMounted(load);
</script>
