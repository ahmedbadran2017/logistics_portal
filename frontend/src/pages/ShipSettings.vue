<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[920px] mx-auto">
    <header class="sh-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-center gap-3.5 min-w-0">
        <span class="sh-hero-icon" style="background: linear-gradient(135deg, rgb(120 113 108), rgb(87 83 78)); box-shadow: 0 6px 16px -6px rgb(87 83 78 / .5)"><Icon name="settings" :size="22" /></span>
        <div class="min-w-0">
          <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('oclk.setTitle') }}</h1>
          <p class="text-[12.5px] text-stone-500 mt-1.5 max-w-[620px]">{{ t('oclk.setIntro') }}</p>
        </div>
      </div>
    </header>

    <div v-if="loading" class="h-[300px] rounded-2xl sh-shimmer" />

    <div v-else-if="loadError" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('common.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <template v-else-if="s">
      <!-- Waves: the promise the warehouse is held to -->
      <section class="sh-card rounded-2xl p-4 space-y-3">
        <div class="flex items-center gap-2">
          <Icon name="truck" :size="15" class="text-stone-400" />
          <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setWaves') }}</span>
        </div>
        <p class="text-[11.5px] text-stone-500">{{ t('oclk.setWavesHint') }}</p>
        <div v-for="(w, i) in s.waves" :key="i" class="flex items-center gap-3 flex-wrap">
          <span class="text-[12px] font-bold text-stone-700 w-[46px] uppercase" dir="ltr">{{ w.id }}</span>
          <label class="text-[11.5px] text-stone-500">{{ t('oclk.cutoff') }}
            <input v-model="w.cutoff" type="time" :disabled="!s.isAdmin" dir="ltr"
                   class="ms-1.5 h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" />
          </label>
          <label class="text-[11.5px] text-stone-500">{{ t('oclk.leaves') }}
            <input v-model="w.out" type="time" :disabled="!s.isAdmin" dir="ltr"
                   class="ms-1.5 h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" />
          </label>
        </div>
      </section>

      <!-- Rest days -->
      <section class="sh-card rounded-2xl p-4 space-y-2.5">
        <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setRest') }}</span>
        <p class="text-[11.5px] text-stone-500">{{ t('oclk.setRestHint') }}</p>
        <div class="flex flex-wrap gap-1.5">
          <button v-for="(dn, i) in DAYS" :key="i" :disabled="!s.isAdmin" :aria-pressed="s.restDays.includes(i)"
                  class="h-9 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                  :class="s.restDays.includes(i) ? 'text-white bg-stone-900 ring-stone-900' : 'text-stone-600 bg-white ring-stone-200'"
                  @click="toggleRest(i)">{{ t('oclk.d' + i) }}</button>
        </div>
      </section>

      <!-- Per-city promise -->
      <section class="sh-card rounded-2xl overflow-hidden">
        <div class="px-4 py-3 border-b border-stone-100">
          <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setCities') }}</span>
          <p class="text-[11.5px] text-stone-500 mt-0.5">{{ t('oclk.setCitiesHint') }}</p>
        </div>
        <div class="divide-y divide-stone-50 max-h-[300px] overflow-y-auto">
          <div v-for="c in cityList" :key="c" class="px-4 py-2 flex items-center gap-3">
            <span class="text-[12px] text-stone-700 flex-1 truncate" dir="auto">{{ c }}</span>
            <input v-model.number="s.cityDays[c]" type="number" min="1" max="20" :disabled="!s.isAdmin" dir="ltr"
                   class="w-16 h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
            <span class="text-[11px] text-stone-400 w-[40px]">{{ t('oclk.days') }}</span>
            <button v-if="s.isAdmin" class="lp-tap text-stone-300 hover:text-rose-600" :title="t('oclk.removeCity')" @click="delete s.cityDays[c]">
              <Icon name="x" :size="14" />
            </button>
          </div>
          <div class="px-4 py-2 flex items-center gap-3 bg-stone-50/60">
            <span class="text-[12px] font-semibold text-stone-700 flex-1">{{ t('oclk.otherCities') }}</span>
            <input v-model.number="s.defaultCityDays" type="number" min="1" max="20" :disabled="!s.isAdmin" dir="ltr"
                   class="w-16 h-9 px-2 rounded-lg bg-white ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
            <span class="text-[11px] text-stone-400 w-[40px]">{{ t('oclk.days') }}</span>
            <span v-if="s.isAdmin" class="w-[14px]" />
          </div>
        </div>
        <!-- A carrier city the list does not know yet gets its own promise here. -->
        <div v-if="s.isAdmin" class="px-4 py-2.5 border-t border-stone-100 flex items-center gap-2">
          <input v-model="newCity" :placeholder="t('oclk.addCityPh')" dir="auto"
                 class="flex-1 h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px]" @keyup.enter="addCity" />
          <button class="h-9 px-3 rounded-lg text-[12px] font-semibold text-stone-800 ring-1 ring-stone-300 hover:bg-stone-50 disabled:opacity-50"
                  :disabled="!newCity.trim()" @click="addCity">{{ t('oclk.addCity') }}</button>
        </div>
      </section>

      <section class="sh-card rounded-2xl p-4 flex items-center gap-3 flex-wrap">
        <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setChase') }}</span>
        <input v-model.number="s.chaseDays" type="number" min="1" max="30" :disabled="!s.isAdmin" dir="ltr"
               class="w-16 h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
        <span class="text-[11.5px] text-stone-500 flex-1 min-w-[220px]">{{ t('oclk.setChaseHint') }}</span>
      </section>

      <!-- Who may change all of this: managers always, plus the leads named here. -->
      <section v-if="s.isOpsAdmin" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-2">
        <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.admins') }}</span>
        <p class="text-[11.5px] text-stone-500">{{ t('oclk.adminsHint') }}</p>
        <textarea v-model="admins" rows="2" dir="ltr" placeholder="lead@justyol.com, other@justyol.com"
                  class="w-full px-2 py-1.5 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] font-mono" />
      </section>

      <div v-if="s.isAdmin" class="flex items-center gap-2">
        <button class="h-10 px-5 rounded-xl text-[13px] font-bold text-white disabled:opacity-50" style="background: linear-gradient(135deg, rgb(20 184 166), rgb(13 148 136)); box-shadow: 0 4px 12px -4px rgb(20 184 166 / .45)"
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
const loadError = ref("");
const busy = ref(false);
const newCity = ref("");
const admins = ref("");
const DAYS = [0, 1, 2, 3, 4, 5, 6];

const cityList = computed(() => Object.keys(s.value?.cityDays || {}).sort());

function toggleRest(i) {
  if (!s.value?.isAdmin) return;
  const r = s.value.restDays;
  const at = r.indexOf(i);
  if (at >= 0) r.splice(at, 1); else r.push(i);
}
// Same canonical form the board uses to look a city up: accents folded,
// upper-case, single spaces — so "Béni Mellal" and "BENI MELLAL" are one key.
function addCity() {
  const key = newCity.value.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ").toUpperCase().trim();
  if (!key) return;
  if (!(key in s.value.cityDays)) s.value.cityDays[key] = s.value.defaultCityDays || 5;
  newCity.value = "";
}
// An emptied number input is "" under v-model.number; the server would
// choke on it, so it is dropped here and clamped there.
function cleanDays(map) {
  const out = {};
  for (const [k, v] of Object.entries(map || {})) {
    const n = parseInt(v, 10);
    if (Number.isFinite(n) && n >= 1) out[k] = Math.min(n, 20);
  }
  return out;
}

async function load() {
  loading.value = true;
  try { s.value = await api("shipments.settings"); admins.value = (s.value.admins || []).join(", "); loadError.value = ""; }
  catch (e) { s.value = null; loadError.value = String(e?.message || e); }
  loading.value = false;
}
async function save() {
  busy.value = true;
  try {
    const r = await apiPost("shipments.save_settings", {
      payload: {
        waves: s.value.waves, restDays: s.value.restDays,
        cityDays: cleanDays(s.value.cityDays),
        defaultCityDays: parseInt(s.value.defaultCityDays, 10) || 5,
        chaseDays: parseInt(s.value.chaseDays, 10) || 5,
        ...(s.value.isOpsAdmin ? { admins: admins.value.split(/[,\s]+/).map((x) => x.trim()).filter(Boolean) } : {}),
      },
    });
    Object.assign(s.value, r.settings);
    admins.value = (r.settings.admins || []).join(", ");
    success(t("oclk.saved"), "");
  } catch (e) { warn(t("oclk.saveFail"), String(e.message || e)); }
  busy.value = false;
}
onMounted(load);
</script>
