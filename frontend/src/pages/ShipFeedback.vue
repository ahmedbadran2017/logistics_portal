<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1240px] mx-auto">
    <header class="sh-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-start justify-between gap-5 flex-wrap">
        <div class="flex items-center gap-3.5 min-w-0">
          <span class="sh-hero-icon"><Icon name="message-circle" :size="22" /></span>
          <div class="min-w-0">
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('dfb.title') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5 max-w-[620px]">{{ t('dfb.intro') }}</p>
            <div class="mt-2.5 flex items-center gap-1 rounded-lg bg-stone-100/80 p-0.5 w-max">
              <button v-for="n in [7, 14, 30]" :key="n" class="h-7 px-2.5 rounded-md text-[11.5px] font-semibold" :aria-pressed="days === n"
                      :class="days === n ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500'" @click="setDays(n)">{{ n }}{{ t('oclk.dShort') }}</button>
            </div>
          </div>
        </div>

        <div v-if="d && d.ready" class="flex items-center gap-3 flex-wrap">
          <!-- the ring: of those who answered, how many were happy -->
          <div class="flex items-center gap-4 rounded-2xl px-4 py-3 bg-white/75 ring-1 ring-teal-200/70" style="backdrop-filter: blur(4px)">
            <div class="relative flex-shrink-0">
              <svg width="72" height="72" viewBox="0 0 72 72" class="-rotate-90" role="img" :aria-label="pct(d.satisfaction) + ' ' + t('oclk.satRing')">
                <circle cx="36" cy="36" r="30" fill="none" stroke="rgb(20 184 166 / 0.18)" stroke-width="8" />
                <circle cx="36" cy="36" r="30" fill="none" :stroke="ringColor" stroke-width="8" stroke-linecap="round" :stroke-dasharray="dash((d.satisfaction || 0) / 100, 30)" />
              </svg>
              <span class="absolute inset-0 grid place-items-center text-[15px] font-extrabold tabular-nums" :class="satCls">{{ pct(d.satisfaction) }}</span>
            </div>
            <div>
              <div class="text-[10px] uppercase font-bold tracking-wide text-teal-700">{{ t('oclk.fbHero') }}</div>
              <div class="text-[12px] text-stone-600 mt-1 tabular-nums">
                <b class="text-stone-900">{{ d.sent }}</b> {{ t('oclk.asked') }} · <b class="text-stone-900">{{ pct(d.responseRate) }}</b> {{ t('oclk.answered') }}
              </div>
              <div class="text-[11px] text-stone-400 mt-0.5">{{ t('dfb.kSatSub') }}</div>
            </div>
          </div>
          <div class="sh-stat">
            <span class="sh-stat-n" :class="d.openNegatives ? 'text-rose-600' : 'text-emerald-600'">{{ d.openNegatives }}</span>
            <span class="sh-stat-l">{{ t('dfb.kOpen') }}</span>
          </div>
          <div v-if="loadError" class="sh-stat" style="box-shadow: inset 0 0 0 1px rgb(254 205 211)">
            <span class="sh-stat-n text-rose-600"><Icon name="alert-triangle" :size="18" /></span>
            <span class="sh-stat-l text-rose-600">{{ t('oclk.staleWarn') }}</span>
          </div>
        </div>
      </div>
    </header>

    <div v-if="!d && loading" class="space-y-2.5">
      <div class="h-[52px] rounded-2xl sh-shimmer" />
      <div class="grid md:grid-cols-[1fr_360px] gap-4"><div class="h-[300px] rounded-2xl sh-shimmer" /><div class="h-[300px] rounded-2xl sh-shimmer" /></div>
    </div>

    <div v-else-if="loadError && !d" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('common.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <template v-else-if="d">
      <!-- State banners: this engine ships off, and says so instead of showing zeros. -->
      <div v-if="!d.ready" class="rounded-2xl bg-amber-50 ring-1 ring-amber-200 px-4 py-3 text-[12.5px] text-amber-800 flex items-center gap-2">
        <Icon name="alert-triangle" :size="15" />{{ t('dfb.notReady') }}
      </div>
      <div v-else-if="!d.enabled" class="rounded-2xl bg-stone-100 ring-1 ring-stone-200 px-4 py-3 text-[12.5px] text-stone-600 flex items-center gap-2">
        <Icon name="circle-pause" :size="15" class="text-stone-400" />{{ t('dfb.disabled') }}
      </div>
      <div v-if="d.failedRecent && d.failedRecent.length" class="rounded-2xl bg-rose-50 ring-1 ring-rose-200 px-4 py-3 text-[12px] text-rose-800 space-y-1">
        <div class="font-semibold flex items-center gap-2"><Icon name="alert-triangle" :size="14" />{{ t('dfb.failedTitle') }}</div>
        <div v-for="f in d.failedRecent" :key="f.sales_order" class="flex items-start gap-2 font-mono text-[11px]" dir="ltr">
          <span class="flex-shrink-0">{{ f.sales_order }}</span><span class="text-rose-700/80 break-words">{{ f.error }}</span>
        </div>
      </div>

      <div v-if="d.ready" class="grid md:grid-cols-[1fr_360px] gap-4 items-start">
        <!-- the queue for a human: every unhappy reply as the customer wrote it -->
        <section class="space-y-2.5 min-w-0">
          <div class="flex items-center gap-2 px-1">
            <Icon name="thumbs-down" :size="14" class="text-rose-500" />
            <span class="text-[13px] font-bold text-stone-900">{{ t('oclk.unhappyQueue') }}</span>
            <span class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ d.negatives.length }}</span>
          </div>
          <div v-for="r in d.negatives" :key="r.name" class="sh-card rounded-2xl p-4" :class="r.handled ? 'opacity-60' : ''">
            <div class="flex items-center gap-2 flex-wrap">
              <RouterLink :to="{ name: 'OrderDetail', params: { name: r.sales_order } }" class="font-mono text-[12.5px] font-bold text-stone-900 hover:underline" dir="ltr">{{ r.sales_order }}</RouterLink>
              <span class="text-[12px] text-stone-600 truncate" dir="auto">{{ r.customer_name }}</span>
              <span class="text-[11px] text-stone-400" dir="auto">{{ r.city }}</span>
              <span class="text-[10.5px] text-stone-400 tabular-nums ms-auto" dir="ltr">{{ r.replied_at }}</span>
            </div>
            <div class="sh-bubble sh-bubble-neg mt-2.5 text-[13px] text-stone-800 max-w-[560px]" dir="auto">{{ r.reply }}</div>
            <div class="flex items-center gap-2 mt-3 flex-wrap">
              <a :href="'tel:+' + r.phone" dir="ltr" class="lp-tap h-9 px-3 rounded-xl text-[12px] font-semibold text-stone-700 inline-flex items-center gap-1.5 bg-white ring-1 ring-stone-200 hover:ring-emerald-300 hover:text-emerald-700 transition-colors"><Icon name="phone" :size="13" />+{{ r.phone }}</a>
              <span v-if="r.ticket" class="h-9 px-3 rounded-xl text-[12px] font-semibold text-violet-700 inline-flex items-center gap-1.5 bg-violet-50 ring-1 ring-violet-200" dir="ltr" :title="t('dfb.ticketHint')"><Icon name="ticket" :size="13" />{{ r.ticket }}</span>
              <span v-if="r.handled" class="text-[11px] text-stone-400 inline-flex items-center gap-1"><Icon name="check" :size="12" />{{ t('dfb.handledBy') }} {{ r.handled_by }}</span>
              <button v-else class="ms-auto h-9 px-3.5 rounded-xl text-[12px] font-bold text-white" style="background: linear-gradient(135deg, rgb(16 185 129), rgb(5 150 105)); box-shadow: 0 4px 12px -4px rgb(16 185 129 / .4)" @click="handled(r)">
                <Icon name="check" :size="13" class="inline -mt-px me-1" />{{ t('dfb.markHandled') }}
              </button>
            </div>
          </div>
          <div v-if="!d.negatives.length" class="sh-empty rounded-2xl p-12 text-center">
            <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
            <div class="text-[15px] font-semibold text-stone-800">{{ t('dfb.negEmpty') }}</div>
          </div>
        </section>

        <div class="space-y-4">
          <!-- the pulse: every day's questions and how the answers split -->
          <section v-if="d.series && d.series.length" class="sh-card rounded-2xl p-4">
            <div class="text-[12px] font-bold text-stone-900 mb-3">{{ t('dfb.daily') }}</div>
            <div class="flex items-end gap-1 h-[84px]" dir="ltr">
              <div v-for="s in d.series" :key="s.d" class="flex-1 flex flex-col justify-end items-stretch gap-px min-w-[6px]" role="img"
                   :title="s.d + ' · ' + s.sent" :aria-label="s.d + ': ' + s.pos + ' ' + t('dfb.pos') + ', ' + s.neg + ' ' + t('dfb.neg') + ', ' + (s.sent - s.pos - s.neg) + ' ' + t('dfb.silent')">
                <div class="bg-rose-400 rounded-t-sm" :style="{ height: barH(s.neg) }" />
                <div class="bg-emerald-400" :style="{ height: barH(s.pos) }" />
                <div class="bg-stone-200 rounded-b-sm" :style="{ height: barH(s.sent - s.pos - s.neg) }" />
              </div>
            </div>
            <div class="flex items-center gap-3 mt-2 text-[10.5px] text-stone-400">
              <span class="inline-flex items-center gap-1"><i class="w-2 h-2 rounded-sm bg-emerald-400 inline-block" />{{ t('dfb.pos') }}</span>
              <span class="inline-flex items-center gap-1"><i class="w-2 h-2 rounded-sm bg-rose-400 inline-block" />{{ t('dfb.neg') }}</span>
              <span class="inline-flex items-center gap-1"><i class="w-2 h-2 rounded-sm bg-stone-200 inline-block" />{{ t('dfb.silent') }}</span>
            </div>
          </section>

          <section v-if="d.cities && d.cities.length" class="sh-card rounded-2xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-bold text-stone-900">{{ t('dfb.cities') }}</div>
            <div class="divide-y divide-stone-50">
              <div v-for="c in d.cities" :key="c.city" class="px-4 py-2 flex items-center gap-2 text-[11.5px]">
                <span class="flex-1 truncate text-stone-700" dir="auto">{{ c.city }}</span>
                <span class="w-[72px] h-1.5 rounded-full bg-rose-100 overflow-hidden"><span class="block h-full bg-emerald-400" :style="{ width: Math.round(100 * c.pos / c.n) + '%' }" /></span>
                <span class="tabular-nums font-bold w-[40px] text-end" dir="ltr" :class="c.neg / c.n > 0.3 ? 'text-rose-600' : 'text-emerald-600'">{{ Math.round(100 * c.pos / c.n) }}%</span>
              </div>
            </div>
          </section>

          <section v-if="d.recent && d.recent.length" class="sh-card rounded-2xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-bold text-stone-900">{{ t('dfb.recent') }}</div>
            <div class="divide-y divide-stone-50 max-h-[320px] overflow-y-auto">
              <div v-for="(r, i) in d.recent" :key="i" class="px-4 py-2 flex items-center gap-2 text-[11.5px]">
                <Icon :name="r.status === 'positive' ? 'thumbs-up' : 'thumbs-down'" :size="12" :class="r.status === 'positive' ? 'text-emerald-500' : 'text-rose-500'" class="flex-shrink-0" />
                <span class="sr-only">{{ r.status === 'positive' ? t('dfb.pos') : t('dfb.neg') }}</span>
                <span class="font-mono text-stone-700 flex-shrink-0" dir="ltr">{{ r.sales_order }}</span>
                <span class="text-stone-500 truncate flex-1" dir="auto">{{ r.reply }}</span>
                <span class="text-stone-400 tabular-nums flex-shrink-0" dir="ltr">{{ r.replied_at.slice(5) }}</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </template>

    <!-- Settings: the lead configures the question, the answers and the follow-ups. -->
    <div v-if="settingsError" class="rounded-2xl bg-rose-50 ring-1 ring-rose-200 px-4 py-3 text-[12px] text-rose-800 flex items-center gap-3 flex-wrap">
      <span class="font-semibold">{{ t('dfb.settingsFail') }}</span>
      <span class="font-mono text-[11px] text-rose-700/80 break-words">{{ settingsError }}</span>
      <button class="ms-auto h-8 px-3 rounded-md text-[11.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="loadSettings">{{ t('common.retry') }}</button>
    </div>
    <section v-if="s" class="sh-card rounded-2xl overflow-hidden">
      <button class="w-full px-4 py-3.5 flex items-center gap-2 text-start" :aria-expanded="showSet" @click="showSet = !showSet">
        <span class="w-8 h-8 rounded-lg bg-stone-100 text-stone-500 inline-flex items-center justify-center"><Icon name="settings" :size="14" /></span>
        <span class="text-[13px] font-bold text-stone-900">{{ t('dfb.setTitle') }}</span>
        <span class="text-[10.5px] font-bold rounded-full px-2 py-0.5 ms-1" :class="s.enabled ? 'text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200' : 'text-stone-500 bg-stone-100'">{{ s.enabled ? t('dfb.on') : t('dfb.off') }}</span>
        <Icon :name="showSet ? 'chevron-up' : 'chevron-down'" :size="14" class="ms-auto text-stone-400" />
      </button>
      <div v-if="showSet" class="px-4 pb-4 space-y-4 border-t border-stone-100 pt-4">
        <p class="text-[11.5px] text-stone-500">{{ t('dfb.setIntro') }}</p>

        <div class="grid sm:grid-cols-2 gap-3">
          <label class="text-[11.5px] text-stone-600 space-y-1">
            <span class="font-semibold">{{ t('dfb.template') }}</span>
            <select v-model="s.template" :disabled="!s.isAdmin" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px]">
              <option value="">{{ t('dfb.pickTemplate') }}</option>
              <option v-for="tp in s.templates" :key="tp.name" :value="tp.name">{{ tp.template_name }} ({{ tp.language_code }})</option>
            </select>
            <span v-if="tplBody" class="sh-bubble block text-[11px] text-stone-600 whitespace-pre-line mt-2" dir="auto">{{ tplBody }}</span>
          </label>
          <div class="grid grid-cols-2 gap-2">
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.delayH') }}</span>
              <input v-model.number="s.delayHours" type="number" min="1" max="72" :disabled="!s.isAdmin" dir="ltr" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.maxAge') }}</span>
              <input v-model.number="s.maxAgeDays" type="number" min="1" max="14" :disabled="!s.isAdmin" dir="ltr" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.winStart') }}</span>
              <input v-model="s.windowStart" type="time" :disabled="!s.isAdmin" dir="ltr" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.winEnd') }}</span>
              <input v-model="s.windowEnd" type="time" :disabled="!s.isAdmin" dir="ltr" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.cap') }}</span>
              <input v-model.number="s.dailyCap" type="number" min="1" max="5000" :disabled="!s.isAdmin" dir="ltr" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.cooldown') }}</span>
              <input v-model.number="s.phoneCooldownDays" type="number" min="1" max="180" :disabled="!s.isAdmin" dir="ltr" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
          </div>
        </div>

        <div class="grid sm:grid-cols-2 gap-3">
          <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.posWords') }}</span>
            <input v-model="posWords" :disabled="!s.isAdmin" dir="auto" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px]" /></label>
          <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.negWords') }}</span>
            <input v-model="negWords" :disabled="!s.isAdmin" dir="auto" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px]" /></label>
          <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.thanks') }}</span>
            <textarea v-model="s.thanksText" rows="3" :disabled="!s.isAdmin" dir="auto" class="w-full px-2 py-1.5 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px]" /></label>
          <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.sorry') }}</span>
            <textarea v-model="s.sorryText" rows="3" :disabled="!s.isAdmin" dir="auto" class="w-full px-2 py-1.5 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px]" /></label>
        </div>

        <div v-if="s.isAdmin" class="space-y-2">
          <div class="flex items-center gap-3 flex-wrap">
            <label class="inline-flex items-center gap-2 text-[12px] font-semibold text-stone-800" :class="!s.template ? 'opacity-60' : ''">
              <input v-model="s.enabled" type="checkbox" :disabled="!s.template" class="w-4 h-4 accent-teal-600" />{{ t('dfb.enable') }}
            </label>
            <button class="h-9 px-4 rounded-xl text-[12.5px] font-bold text-white disabled:opacity-50" style="background: linear-gradient(135deg, rgb(20 184 166), rgb(13 148 136)); box-shadow: 0 4px 12px -4px rgb(20 184 166 / .45)" :disabled="busy" @click="save">{{ busy ? t('oclk.saving') : t('common.save') }}</button>
            <span class="ms-auto inline-flex items-center gap-1.5">
              <input v-model="testPhone" :placeholder="t('dfb.testPh')" dir="ltr" inputmode="tel" class="h-9 w-[160px] px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" />
              <button class="h-9 px-3 rounded-xl text-[12px] font-semibold text-stone-800 ring-1 ring-stone-300 hover:bg-stone-50 disabled:opacity-50" :disabled="!s.template || !testPhone || busy" @click="testSend">{{ t('dfb.testSend') }}</button>
            </span>
          </div>
          <p v-if="!s.template" class="text-[11px] text-amber-700">{{ t('dfb.needTemplate') }}</p>
        </div>
        <p v-else class="text-[11.5px] text-stone-400">{{ t('oclk.readOnly') }}</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { readStale, writeStale } from "@/lib/swr";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { useAuth } from "@/composables/useAuth";

const { t } = useI18n();
const { success, warn } = useToast();
const { user, fullName } = useAuth();
let seq = 0;
const d = ref(null);
const s = ref(null);
const days = ref(14);
const loading = ref(true);
const loadError = ref("");
const settingsError = ref("");
const busy = ref(false);
const showSet = ref(false);
const testPhone = ref("");
const posWords = ref("");
const negWords = ref("");

const satCls = computed(() => {
  const v = d.value?.satisfaction;
  if (v == null) return "text-stone-400";
  return v >= 80 ? "text-emerald-600" : v >= 60 ? "text-amber-600" : "text-rose-600";
});
const ringColor = computed(() => {
  const v = d.value?.satisfaction;
  if (v == null) return "rgb(168 162 158)";
  return v >= 80 ? "rgb(16 185 129)" : v >= 60 ? "rgb(245 158 11)" : "rgb(244 63 94)";
});
const tplBody = computed(() => (s.value?.templates || []).find((x) => x.name === s.value?.template)?.body || "");
const maxDay = computed(() => Math.max(1, ...(d.value?.series || []).map((x) => x.sent)));

function pct(v) { return v == null ? "—" : v + "%"; }
function barH(n) { return Math.max(0, (84 * (n || 0)) / maxDay.value) + "px"; }
function dash(frac, r) { const c = 2 * Math.PI * r; return `${Math.max(0, Math.min(1, frac)) * c} ${c}`; }

async function load() {
  const my = ++seq;
  if (!d.value) loading.value = true;
  try {
    const r = await api("feedback.board", { days: days.value });
    if (my !== seq) return;
    d.value = r; loadError.value = "";
    writeStale("ship.feedback." + days.value, r);
  } catch (e) {
    if (my !== seq) return;
    loadError.value = String(e?.message || e);
  }
  loading.value = false;
}
async function loadSettings() {
  try {
    s.value = await api("feedback.settings");
    posWords.value = (s.value.positiveWords || []).join(", ");
    negWords.value = (s.value.negativeWords || []).join(", ");
    settingsError.value = "";
  } catch (e) { s.value = null; settingsError.value = String(e?.message || e); }
}
function setDays(n) { days.value = n; load(); }
async function handled(r) {
  try {
    await apiPost("feedback.mark_handled", { name: r.name });
    r.handled = 1; r.handled_by = fullName.value || user.value || "";
    load();
  } catch (e) { warn(t("dfb.saveFail"), String(e.message || e)); }
}
async function save() {
  busy.value = true;
  try {
    const split = (v) => v.split(/[,،\n]/).map((x) => x.trim()).filter(Boolean);
    const payload = { ...s.value, positiveWords: split(posWords.value), negativeWords: split(negWords.value) };
    delete payload.templates; delete payload.isAdmin; delete payload.hasWa;
    const r = await apiPost("feedback.save_settings", { payload });
    Object.assign(s.value, r.settings);
    success(t("oclk.saved"), "");
    load();
  } catch (e) { warn(t("dfb.saveFail"), String(e.message || e)); }
  busy.value = false;
}
async function testSend() {
  busy.value = true;
  try { await apiPost("feedback.test_send", { phone: testPhone.value }); success(t("dfb.testSent"), ""); }
  catch (e) { warn(t("dfb.testFail"), String(e.message || e)); }
  busy.value = false;
}
onMounted(() => {
  const stale = readStale("ship.feedback." + days.value);
  if (stale) { d.value = stale; loading.value = false; }
  load(); loadSettings();
});
const tick = setInterval(() => { if (document.visibilityState === "visible") load(); }, 180000);
onUnmounted(() => clearInterval(tick));
</script>
