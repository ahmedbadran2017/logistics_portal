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
      <button class="mt-3 h-9 px-4 rounded-xl text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
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
        <div class="px-4 py-3 border-b border-stone-100 flex items-start gap-3 flex-wrap">
          <div class="min-w-0 flex-1">
            <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setCities') }}</span>
            <p class="text-[11.5px] text-stone-500 mt-0.5">{{ t('oclk.setCitiesHint') }}</p>
            <p v-if="tuner" class="text-[11px] text-teal-700 mt-1">{{ t('oclk.tunerHint') }} · {{ tuner.weeks }}{{ t('oclk.wShort') }}</p>
          </div>
          <button v-if="s.isAdmin && tuner && suggestions.length" class="h-9 px-3 rounded-xl text-[12px] font-bold text-white"
                  style="background: linear-gradient(135deg, rgb(20 184 166), rgb(13 148 136)); box-shadow: 0 4px 12px -4px rgb(20 184 166 / .45)" @click="acceptAll">
            {{ t('oclk.acceptAll') }} ({{ suggestions.length }})
          </button>
        </div>
        <div class="divide-y divide-stone-50 max-h-[300px] overflow-y-auto">
          <div v-for="c in cityList" :key="c" class="px-4 py-1.5 flex items-center gap-3">
            <span class="text-[12px] text-stone-700 flex-1 truncate" dir="auto">{{ c }}</span>
            <!-- what the carrier actually did here lately, next to what we promise -->
            <span v-if="measured[c]" class="text-[10.5px] tabular-nums text-stone-400 hidden sm:inline-flex items-center gap-1" dir="ltr" :title="t('oclk.measuredHint')">
              p75 <b :class="measured[c].suggested !== (s.cityDays[c] || 0) ? 'text-amber-600' : 'text-stone-600'">{{ measured[c].p75 }}{{ t('oclk.dShort') }}</b>
              · n {{ measured[c].n }} · <span :class="measured[c].keptPct >= 75 ? 'text-emerald-600' : 'text-rose-600'">{{ measured[c].keptPct }}% {{ t('oclk.keptShort') }}</span>
            </span>
            <button v-if="s.isAdmin && measured[c] && measured[c].suggested !== s.cityDays[c]" class="lp-tap h-8 px-2 rounded-lg text-[11px] font-bold text-amber-700 bg-amber-50 ring-1 ring-amber-200 hover:bg-amber-100 inline-flex items-center gap-1"
                    :title="t('oclk.accept') + ' — p75 ' + measured[c].p75 + t('oclk.dShort') + ' · n ' + measured[c].n" @click="s.cityDays[c] = measured[c].suggested"><Icon name="arrow-right" :size="11" class="flip-rtl" />{{ measured[c].suggested }}</button>
            <input v-model.number="s.cityDays[c]" type="number" min="1" max="20" :disabled="!s.isAdmin" dir="ltr" :aria-label="c"
                   class="w-16 h-8 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
            <span class="text-[11px] text-stone-400 w-[40px]">{{ t('oclk.days') }}</span>
            <button v-if="s.isAdmin" class="lp-tap text-stone-300 hover:text-rose-600" :title="t('oclk.removeCity')" :aria-label="t('oclk.removeCity') + ' ' + c" @click="delete s.cityDays[c]">
              <Icon name="x" :size="14" />
            </button>
          </div>
        </div>
        <!-- the default sits outside the scroller: it must never scroll out of sight -->
        <div class="px-4 py-2 flex items-center gap-3 bg-stone-50/60 border-t border-stone-100">
          <span class="text-[12px] font-semibold text-stone-700 flex-1">{{ t('oclk.otherCities') }}</span>
          <input v-model.number="s.defaultCityDays" type="number" min="1" max="20" :disabled="!s.isAdmin" dir="ltr" :aria-label="t('oclk.otherCities')"
                 class="w-16 h-8 px-2 rounded-lg bg-white ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
          <span class="text-[11px] text-stone-400 w-[40px]">{{ t('oclk.days') }}</span>
          <span v-if="s.isAdmin" class="w-[14px]" />
        </div>
        <!-- Busy cities the promise list has never heard of — measured, one click to add. -->
        <div v-if="s.isAdmin && unlisted.length" class="px-4 py-2.5 border-t border-stone-100">
          <div class="text-[10.5px] font-bold uppercase tracking-wide text-stone-400 mb-1.5">{{ t('oclk.suggestAdd') }}</div>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="m in unlisted" :key="m.city" class="lp-tap h-8 px-2.5 rounded-lg text-[11px] font-semibold text-stone-700 bg-stone-50 ring-1 ring-stone-200 hover:bg-white inline-flex items-center gap-1.5"
                    @click="s.cityDays[m.city] = m.suggested" dir="auto">
              {{ m.city }} <span class="tabular-nums text-stone-400" dir="ltr">n {{ m.n }} · p75 {{ m.p75 }}{{ t('oclk.dShort') }}</span> <b class="text-teal-700 inline-flex items-center gap-0.5" dir="ltr"><Icon name="arrow-right" :size="10" class="flip-rtl" />{{ m.suggested }}</b>
            </button>
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

      <section class="sh-card rounded-2xl p-4 flex items-center gap-3 flex-wrap">
        <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.setSnooze') }}</span>
        <input v-model.number="s.chaseSnoozeH" type="number" min="1" max="168" :disabled="!s.isAdmin" dir="ltr"
               class="w-16 h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums text-center" />
        <span class="text-[11.5px] text-stone-500 flex-1 min-w-[220px]">{{ t('oclk.setSnoozeHint') }}</span>
      </section>

      <!-- Carrier status sync: the hand-run Desk resync, on a clock. Without
           it half of each day's parcels stay 'Pending' in our book while the
           carrier delivers them (measured 2026-09-16), and the tracking board
           blames the carrier for a gap that is ours. -->
      <section v-if="s.isAdmin" class="sh-card rounded-2xl p-4 space-y-2.5">
        <div class="flex items-center gap-2 flex-wrap">
          <Icon name="refresh-cw" :size="15" class="text-stone-400" />
          <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.csTitle') }}</span>
          <button class="ms-auto inline-flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-[11.5px] font-semibold ring-1 transition-colors"
                  :class="cs.on ? 'text-emerald-700 bg-emerald-50 ring-emerald-200' : 'text-stone-600 bg-white ring-stone-200'"
                  :disabled="csBusy" @click="toggleCs">
            <Icon :name="cs.on ? 'check-circle' : 'circle'" :size="12" />{{ cs.on ? t('oclk.on', 'on') : t('oclk.off', 'off') }}
          </button>
          <button class="h-8 px-3 rounded-lg text-[11.5px] font-semibold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50"
                  :disabled="csBusy" @click="runCs">{{ t('oclk.csRun') }}</button>
        </div>
        <p class="text-[11.5px] text-stone-500">{{ t('oclk.csHint').replace('{d}', cs.days || 21) }}</p>
        <div class="flex items-center gap-4 flex-wrap text-[12px] tabular-nums">
          <span class="font-bold" :class="cs.pending ? 'text-amber-700' : 'text-emerald-700'">{{ cs.pending }} <span class="font-normal text-stone-500">{{ t('oclk.csPending') }}</span></span>
          <span v-if="cs.last" class="text-stone-600">
            {{ t('oclk.csLast') }} {{ cs.last.startedAt }} ·
            <template v-if="cs.last.ok">{{ cs.last.processed }} {{ t('oclk.csProcessed') }} · {{ cs.last.inserted }} {{ t('oclk.csInserted') }} · {{ cs.last.errors }} {{ t('oclk.csErrors') }} · {{ cs.last.seconds }}s</template>
            <span v-else class="text-rose-600 font-mono">{{ cs.last.error || cs.last.reason }}</span>
          </span>
          <span v-else class="text-stone-400">{{ t('oclk.csNever') }}</span>
        </div>
      </section>

      <!-- Who may change all of this: managers always, plus the leads named here. -->
      <section v-if="s.isOpsAdmin" class="sh-card rounded-2xl p-4 space-y-2">
        <span class="text-[13px] font-semibold text-stone-900">{{ t('oclk.admins') }}</span>
        <p class="text-[11.5px] text-stone-500">{{ t('oclk.adminsHint') }}</p>
        <textarea v-model="admins" rows="2" dir="ltr" placeholder="lead@justyol.com, other@justyol.com"
                  class="w-full px-2 py-1.5 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] font-mono" />
      </section>

      <div v-if="s.isAdmin" class="flex items-center gap-2 flex-wrap">
        <button class="h-9 px-5 rounded-xl text-[13px] font-bold text-white disabled:opacity-50" style="background: linear-gradient(135deg, rgb(20 184 166), rgb(13 148 136)); box-shadow: 0 4px 12px -4px rgb(20 184 166 / .45)"
                :disabled="busy || !dirty" @click="save">{{ busy ? t('oclk.saving') : t('common.save') }}</button>
        <span v-if="dirty" class="text-[11px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-full px-2 py-0.5">{{ t('oclk.unsaved') }}</span>
        <span class="text-[11.5px] text-stone-400">{{ t('oclk.saveHint') }}</span>
      </div>
      <p v-else class="text-[11.5px] text-stone-400">{{ t('oclk.readOnly') }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { onBeforeRouteLeave } from "vue-router";
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
const tuner = ref(null);
const measured = computed(() => Object.fromEntries((tuner.value?.cities || []).map((m) => [m.city, m])));
// Cities whose configured promise differs from what the carrier has been keeping.
const suggestions = computed(() => (tuner.value?.cities || []).filter((m) => (m.city in (s.value?.cityDays || {})) && m.suggested !== s.value.cityDays[m.city]));
const unlisted = computed(() => (tuner.value?.cities || []).filter((m) => !(m.city in (s.value?.cityDays || {})) && m.n >= 30).slice(0, 12));
function acceptAll() { for (const m of suggestions.value) s.value.cityDays[m.city] = m.suggested; }
async function loadTuner() {
  try { tuner.value = await api("shipments.city_promises", { weeks: 4 }); } catch (_) { tuner.value = null; }
}

// ── carrier status sync ──────────────────────────────────────────────────
const cs = ref({ on: true, last: null, pending: 0, days: 21 });
const csBusy = ref(false);
async function loadCs() {
  try { cs.value = await api("carrier_sync.status"); } catch (_) { /* not an admin: the section is hidden anyway */ }
}
async function toggleCs() {
  csBusy.value = true;
  try { cs.value = await apiPost("carrier_sync.set_enabled", { on: cs.value.on ? 0 : 1 }); }
  catch (e) { warn(t("oclk.saveFail"), String(e.message || e)); }
  csBusy.value = false;
}
async function runCs() {
  csBusy.value = true;
  try {
    await apiPost("carrier_sync.run_now");
    success(t("oclk.csQueued"), "");
    setTimeout(loadCs, 90000);
  } catch (e) { warn(t("oclk.saveFail"), String(e.message || e)); }
  csBusy.value = false;
}

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

// What would be sent on Save, as a string — the snapshot taken after load/save
// is compared to it so the button knows when there is nothing to save, and a
// sidebar click cannot silently throw away an accepted suggestion.
function payload() {
  return JSON.stringify({
    waves: s.value.waves, restDays: [...(s.value.restDays || [])].sort(),
    cityDays: cleanDays(s.value.cityDays),
    defaultCityDays: parseInt(s.value.defaultCityDays, 10) || 5,
    chaseDays: parseInt(s.value.chaseDays, 10) || 5,
    chaseSnoozeH: parseInt(s.value.chaseSnoozeH, 10) || 24,
    admins: admins.value,
  });
}
const snap = ref("");
const dirty = computed(() => !!s.value && !!s.value.isAdmin && payload() !== snap.value);
onBeforeRouteLeave(() => !dirty.value || window.confirm(t("oclk.leaveUnsaved")));
function beforeUnload(e) { if (dirty.value) { e.preventDefault(); e.returnValue = ""; } }
onUnmounted(() => window.removeEventListener("beforeunload", beforeUnload));

async function load() {
  loading.value = true;
  try { s.value = await api("shipments.settings"); admins.value = (s.value.admins || []).join(", "); snap.value = payload(); loadError.value = ""; loadTuner(); if (s.value.isAdmin) loadCs(); }
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
        chaseSnoozeH: parseInt(s.value.chaseSnoozeH, 10) || 24,
        ...(s.value.isOpsAdmin ? { admins: admins.value.split(/[,\s]+/).map((x) => x.trim()).filter(Boolean) } : {}),
      },
    });
    Object.assign(s.value, r.settings);
    admins.value = (r.settings.admins || []).join(", ");
    snap.value = payload();
    success(t("oclk.saved"), "");
  } catch (e) { warn(t("oclk.saveFail"), String(e.message || e)); }
  busy.value = false;
}
onMounted(() => { load(); window.addEventListener("beforeunload", beforeUnload); });
</script>
