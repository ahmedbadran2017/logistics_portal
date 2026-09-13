<template>
  <div class="max-w-[1200px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('dfb.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[720px]">{{ t('dfb.intro') }}</p>
      </div>
      <div class="flex items-center gap-1 rounded-lg bg-stone-100 p-0.5">
        <button v-for="n in [7, 14, 30]" :key="n" class="h-7 px-2.5 rounded-md text-[11.5px] font-semibold"
                :class="days === n ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500'" @click="setDays(n)">{{ n }}{{ t('oclk.dShort') }}</button>
      </div>
    </header>

    <!-- State banner: this engine ships off, and says so instead of showing zeros. -->
    <div v-if="d && !d.ready" class="rounded-xl bg-amber-50 ring-1 ring-amber-200 px-4 py-3 text-[12.5px] text-amber-800 flex items-center gap-2">
      <Icon name="alert-triangle" :size="15" />{{ t('dfb.notReady') }}
    </div>
    <div v-else-if="d && !d.enabled" class="rounded-xl bg-stone-100 ring-1 ring-stone-200 px-4 py-3 text-[12.5px] text-stone-600 flex items-center gap-2">
      <Icon name="circle-pause" :size="15" class="text-stone-400" />{{ t('dfb.disabled') }}
    </div>

    <section v-if="d && d.ready" class="grid grid-cols-2 md:grid-cols-4 gap-2.5">
      <div class="rounded-xl bg-white ring-1 ring-stone-200/70 p-3.5">
        <div class="text-[24px] font-extrabold tabular-nums leading-none text-stone-900">{{ d.sent }}</div>
        <div class="text-[11px] font-semibold text-stone-600 mt-1">{{ t('dfb.kSent') }}</div>
        <div class="text-[10.5px] text-stone-400">{{ t('dfb.kSentSub').replace('{n}', days) }}</div>
      </div>
      <div class="rounded-xl bg-white ring-1 ring-stone-200/70 p-3.5">
        <div class="text-[24px] font-extrabold tabular-nums leading-none text-stone-900">{{ pct(d.responseRate) }}</div>
        <div class="text-[11px] font-semibold text-stone-600 mt-1">{{ t('dfb.kResp') }}</div>
        <div class="text-[10.5px] text-stone-400">{{ t('dfb.kRespSub') }}</div>
      </div>
      <div class="rounded-xl bg-white ring-1 ring-stone-200/70 p-3.5">
        <div class="text-[24px] font-extrabold tabular-nums leading-none" :class="satCls">{{ pct(d.satisfaction) }}</div>
        <div class="text-[11px] font-semibold text-stone-600 mt-1">{{ t('dfb.kSat') }}</div>
        <div class="text-[10.5px] text-stone-400">{{ t('dfb.kSatSub') }}</div>
      </div>
      <div class="rounded-xl bg-white ring-1 ring-stone-200/70 p-3.5">
        <div class="text-[24px] font-extrabold tabular-nums leading-none" :class="d.openNegatives ? 'text-rose-600' : 'text-emerald-600'">{{ d.openNegatives }}</div>
        <div class="text-[11px] font-semibold text-stone-600 mt-1">{{ t('dfb.kOpen') }}</div>
        <div class="text-[10.5px] text-stone-400">{{ t('dfb.kOpenSub') }}</div>
      </div>
    </section>

    <!-- Daily bars: how many were asked, and how the answers split. -->
    <section v-if="d && d.series && d.series.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
      <div class="text-[12px] font-semibold text-stone-900 mb-3">{{ t('dfb.daily') }}</div>
      <div class="flex items-end gap-1 h-[90px]">
        <div v-for="s in d.series" :key="s.d" class="flex-1 flex flex-col justify-end items-stretch gap-px min-w-[6px]" :title="s.d + ' · ' + s.sent">
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

    <div class="grid md:grid-cols-[1fr_340px] gap-4 items-start">
      <!-- The queue for a human: every unhappy reply, unhandled first. -->
      <section v-if="d && d.ready" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
          <Icon name="thumbs-down" :size="14" class="text-rose-500" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('dfb.negTitle') }}</span>
          <span class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ d.negatives.length }}</span>
        </div>
        <div v-if="d.negatives.length" class="divide-y divide-stone-50 max-h-[520px] overflow-y-auto">
          <div v-for="r in d.negatives" :key="r.name" class="px-4 py-2.5 flex items-start gap-3" :class="r.handled ? 'opacity-60' : ''">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap">
                <RouterLink :to="{ name: 'OrderDetail', params: { name: r.sales_order } }" class="font-mono text-[12px] font-semibold text-stone-900 hover:underline">{{ r.sales_order }}</RouterLink>
                <span class="text-[11px] text-stone-500 truncate" dir="auto">{{ r.customer_name }}</span>
                <span class="text-[10.5px] text-stone-400" dir="auto">{{ r.city }}</span>
                <span class="text-[10.5px] text-stone-400 tabular-nums ms-auto">{{ r.replied_at }}</span>
              </div>
              <div class="text-[12px] text-stone-700 mt-1" dir="auto">"{{ r.reply }}"</div>
              <div class="flex items-center gap-2 mt-1.5 flex-wrap">
                <a :href="'tel:+' + r.phone" class="text-[10.5px] font-semibold text-stone-600 inline-flex items-center gap-1 rounded-md ring-1 ring-stone-200 px-1.5 py-0.5 hover:bg-stone-50"><Icon name="phone" :size="11" />+{{ r.phone }}</a>
                <RouterLink v-if="r.ticket" :to="{ name: 'Tickets', query: { q: r.ticket } }" class="text-[10.5px] font-semibold text-violet-700 inline-flex items-center gap-1 rounded-md ring-1 ring-violet-200 bg-violet-50 px-1.5 py-0.5"><Icon name="ticket" :size="11" />{{ r.ticket }}</RouterLink>
                <span v-if="r.handled" class="text-[10.5px] text-stone-400">{{ t('dfb.handledBy') }} {{ r.handled_by }}</span>
                <button v-else class="ms-auto h-7 px-2.5 rounded-md text-[11px] font-semibold text-white bg-stone-900 hover:bg-stone-800" @click="handled(r)">{{ t('dfb.markHandled') }}</button>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="p-8 text-center">
          <Icon name="check-circle" :size="22" class="mx-auto text-emerald-400" />
          <div class="text-[13px] font-semibold text-stone-700 mt-2">{{ t('dfb.negEmpty') }}</div>
        </div>
      </section>

      <div class="space-y-4">
        <!-- Cities where the door goes wrong most: a carrier conversation, not a warehouse one. -->
        <section v-if="d && d.cities && d.cities.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-900">{{ t('dfb.cities') }}</div>
          <div class="divide-y divide-stone-50">
            <div v-for="c in d.cities" :key="c.city" class="px-4 py-2 flex items-center gap-2 text-[11.5px]">
              <span class="flex-1 truncate text-stone-700" dir="auto">{{ c.city }}</span>
              <span class="tabular-nums text-stone-400 w-[34px] text-end">{{ c.n }}</span>
              <span class="tabular-nums font-bold w-[46px] text-end" :class="c.neg / c.n > 0.3 ? 'text-rose-600' : 'text-emerald-600'">{{ Math.round(100 * c.pos / c.n) }}%</span>
            </div>
          </div>
        </section>

        <section v-if="d && d.recent && d.recent.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-900">{{ t('dfb.recent') }}</div>
          <div class="divide-y divide-stone-50 max-h-[320px] overflow-y-auto">
            <div v-for="(r, i) in d.recent" :key="i" class="px-4 py-2 flex items-center gap-2 text-[11.5px]">
              <Icon :name="r.status === 'positive' ? 'thumbs-up' : 'thumbs-down'" :size="12" :class="r.status === 'positive' ? 'text-emerald-500' : 'text-rose-500'" class="flex-shrink-0" />
              <span class="font-mono text-stone-700 flex-shrink-0">{{ r.sales_order }}</span>
              <span class="text-stone-500 truncate flex-1" dir="auto">{{ r.reply }}</span>
              <span class="text-stone-400 tabular-nums flex-shrink-0">{{ r.replied_at.slice(5) }}</span>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- Settings: the lead configures the question, the answers and the follow-ups. -->
    <section v-if="s" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <button class="w-full px-4 py-3 flex items-center gap-2 text-start" @click="showSet = !showSet">
        <Icon name="settings" :size="14" class="text-stone-400" />
        <span class="text-[12.5px] font-semibold text-stone-900">{{ t('dfb.setTitle') }}</span>
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
            <span v-if="tplBody" class="block text-[10.5px] text-stone-400 whitespace-pre-line" dir="auto">{{ tplBody }}</span>
          </label>
          <div class="grid grid-cols-2 gap-2">
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.delayH') }}</span>
              <input v-model.number="s.delayHours" type="number" min="1" max="72" :disabled="!s.isAdmin" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.maxAge') }}</span>
              <input v-model.number="s.maxAgeDays" type="number" min="1" max="14" :disabled="!s.isAdmin" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.winStart') }}</span>
              <input v-model="s.windowStart" type="time" :disabled="!s.isAdmin" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.winEnd') }}</span>
              <input v-model="s.windowEnd" type="time" :disabled="!s.isAdmin" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.cap') }}</span>
              <input v-model.number="s.dailyCap" type="number" min="1" max="5000" :disabled="!s.isAdmin" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
            <label class="text-[11.5px] text-stone-600"><span class="font-semibold block mb-1">{{ t('dfb.cooldown') }}</span>
              <input v-model.number="s.phoneCooldownDays" type="number" min="1" max="180" :disabled="!s.isAdmin" class="w-full h-9 px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" /></label>
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

        <div v-if="s.isAdmin" class="flex items-center gap-3 flex-wrap">
          <label class="inline-flex items-center gap-2 text-[12px] font-semibold text-stone-800">
            <input v-model="s.enabled" type="checkbox" :disabled="!s.template" class="w-4 h-4" />{{ t('dfb.enable') }}
          </label>
          <button class="h-9 px-4 rounded-lg text-[12.5px] font-bold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50" :disabled="busy" @click="save">{{ busy ? t('oclk.saving') : t('common.save') }}</button>
          <span class="ms-auto inline-flex items-center gap-1.5">
            <input v-model="testPhone" :placeholder="t('dfb.testPh')" class="h-9 w-[160px] px-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] tabular-nums" />
            <button class="h-9 px-3 rounded-lg text-[12px] font-semibold text-stone-800 ring-1 ring-stone-300 hover:bg-stone-50 disabled:opacity-50" :disabled="!s.template || !testPhone || busy" @click="testSend">{{ t('dfb.testSend') }}</button>
          </span>
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
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const d = ref(null);
const s = ref(null);
const days = ref(14);
const busy = ref(false);
const showSet = ref(false);
const testPhone = ref("");
const posWords = ref("");
const negWords = ref("");

const satCls = computed(() => {
  const v = d.value?.satisfaction;
  if (v == null) return "text-stone-900";
  return v >= 80 ? "text-emerald-600" : v >= 60 ? "text-amber-600" : "text-rose-600";
});
const tplBody = computed(() => (s.value?.templates || []).find((x) => x.name === s.value?.template)?.body || "");
const maxDay = computed(() => Math.max(1, ...(d.value?.series || []).map((x) => x.sent)));

function pct(v) { return v == null ? "—" : v + "%"; }
function barH(n) { return Math.max(0, (90 * (n || 0)) / maxDay.value) + "px"; }

async function load() {
  try { d.value = await api("feedback.board", { days: days.value }); } catch { d.value = null; }
}
async function loadSettings() {
  try {
    s.value = await api("feedback.settings");
    posWords.value = (s.value.positiveWords || []).join(", ");
    negWords.value = (s.value.negativeWords || []).join(", ");
  } catch { s.value = null; }
}
function setDays(n) { days.value = n; load(); }
async function handled(r) {
  try { await apiPost("feedback.mark_handled", { name: r.name }); r.handled = 1; load(); }
  catch (e) { warn(t("mv.loadFail"), String(e.message || e)); }
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
  } catch (e) { warn(t("mv.loadFail"), String(e.message || e)); }
  busy.value = false;
}
async function testSend() {
  busy.value = true;
  try { await apiPost("feedback.test_send", { phone: testPhone.value }); success(t("dfb.testSent"), ""); }
  catch (e) { warn(t("dfb.testFail"), String(e.message || e)); }
  busy.value = false;
}
onMounted(() => { load(); loadSettings(); });
const tick = setInterval(() => { if (document.visibilityState === "visible") load(); }, 180000);
onUnmounted(() => clearInterval(tick));
</script>
