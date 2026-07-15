<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1200px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cf.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cf.intro') }}</p>
      </div>
      <div v-if="data" class="flex items-center gap-1.5 flex-wrap">
        <span class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 me-1">{{ t('cf.myDay') }}</span>
        <span class="day-chip text-emerald-700 bg-emerald-50 ring-emerald-200">✓ {{ data.mine.confirm }}</span>
        <span class="day-chip text-amber-700 bg-amber-50 ring-amber-200">📵 {{ data.mine.dna }}</span>
        <span class="day-chip text-rose-700 bg-rose-50 ring-rose-200">✕ {{ data.mine.cancel }}</span>
      </div>
    </header>

    <!-- queue tabs -->
    <div class="flex items-center gap-1.5 flex-wrap">
      <button
        v-for="tb in TABS" :key="tb.key"
        class="px-3 h-9 text-[12.5px] font-semibold rounded-lg ring-1 whitespace-nowrap transition-colors"
        :class="tab === tb.key ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'"
        @click="tab = tb.key; page = 1; load()"
      >{{ t(tb.label) }} · {{ data?.counts?.[tb.key] ?? '…' }}</button>
      <div class="relative ms-auto">
        <Icon name="search" :size="13" class="absolute start-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
        <input v-model="q" :placeholder="t('cf.searchPh')" @input="debouncedLoad"
               class="h-9 w-[220px] ps-8 pe-3 text-[12.5px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none" />
      </div>
    </div>

    <!-- rows -->
    <div v-if="loading" class="space-y-2">
      <div v-for="n in 6" :key="n" class="h-[64px] rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="!rows.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="check-circle" :size="26" class="mx-auto mb-2 text-emerald-500" />
      <div class="text-[13px] text-stone-500">{{ t('cf.empty') }}</div>
    </div>
    <div v-else class="space-y-2">
      <div v-for="r in rows" :key="r.order"
           class="bg-white rounded-xl ring-1 p-3.5 space-y-2.5"
           :class="r.due ? 'ring-amber-300/70' : 'ring-stone-200/70'">
        <div class="flex items-center gap-3 flex-wrap">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono text-[12.5px] font-semibold text-stone-900">{{ r.order }}</span>
              <span class="text-[12.5px] text-stone-700 truncate max-w-[220px]">{{ r.customer }}</span>
              <span v-if="r.city" class="text-[11px] text-stone-500">📍 {{ r.city }}</span>
              <span v-if="r.attempts" class="text-[10.5px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded px-1.5 py-0.5 tabular-nums">
                {{ t('cf.attempts') }} {{ r.attempts }}
              </span>
              <span v-if="r.due" class="text-[10.5px] font-semibold text-white bg-amber-500 rounded px-1.5 py-0.5">{{ t('cf.due') }}</span>
            </div>
            <div class="text-[11px] text-stone-400 tabular-nums mt-0.5">
              {{ fmtMAD(r.total) }} MAD · {{ r.items }} {{ t('consol.items') }} · {{ ageLabel(r.ageH) }}
              <template v-if="r.agent"> · {{ r.agent }}</template>
              <template v-if="r.nextCall"> · {{ t('cf.nextCall') }} {{ r.nextCall.slice(5) }}</template>
            </div>
          </div>
          <!-- contact -->
          <div class="flex items-center gap-1.5">
            <a v-if="r.phone" :href="'tel:' + r.phone" :title="r.phone"
               class="contact-btn text-stone-600 hover:text-emerald-700 hover:ring-emerald-300">
              <Icon name="phone" :size="14" />
            </a>
            <a v-if="r.phone" :href="waLink(r.phone)" target="_blank" title="WhatsApp"
               class="contact-btn text-stone-600 hover:text-emerald-700 hover:ring-emerald-300">
              <Icon name="message-circle" :size="14" />
            </a>
            <button class="contact-btn text-stone-500 hover:text-stone-800"
                    :class="editFor === r.order ? 'bg-stone-100' : ''"
                    :title="t('cf.editContact')" @click="toggleEdit(r)">
              <Icon name="edit" :size="13" />
            </button>
          </div>
          <!-- decisions -->
          <div class="flex items-center gap-1.5 flex-wrap">
            <button class="act-btn text-white bg-emerald-600 hover:bg-emerald-700" :disabled="busy === r.order"
                    @click="act(r, 'confirm')">✓ {{ t('cf.actConfirm') }}</button>
            <button class="act-btn text-amber-700 bg-amber-50 ring-1 ring-amber-200 hover:bg-amber-100" :disabled="busy === r.order"
                    @click="act(r, 'dna')">📵 {{ t('cf.actDna') }}</button>
            <button class="act-btn text-sky-700 bg-sky-50 ring-1 ring-sky-200 hover:bg-sky-100" :disabled="busy === r.order"
                    @click="act(r, 'followup')">🕐 {{ t('cf.actFollowup') }}</button>
            <button class="act-btn text-stone-600 bg-stone-100 hover:bg-stone-200" :disabled="busy === r.order"
                    @click="act(r, 'onhold')">⏸ {{ t('cf.actOnhold') }}</button>
            <button class="act-btn text-rose-700 bg-rose-50 ring-1 ring-rose-200 hover:bg-rose-100" :disabled="busy === r.order"
                    @click="cancelFor = cancelFor === r.order ? '' : r.order">✕ {{ t('cf.actCancel') }}</button>
          </div>
        </div>

        <!-- cancel reason -->
        <div v-if="cancelFor === r.order" class="flex items-center gap-2 bg-rose-50/60 rounded-lg p-2">
          <input v-model="cancelReason" :placeholder="t('cf.cancelPh')" maxlength="120"
                 class="flex-1 h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-rose-200 text-[12.5px] focus:outline-none" />
          <button class="h-9 px-3 rounded-lg text-[12px] font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50"
                  :disabled="!cancelReason.trim() || busy === r.order"
                  @click="act(r, 'cancel', cancelReason)">{{ t('cf.cancelConfirm') }}</button>
        </div>

        <!-- contact edit -->
        <div v-if="editFor === r.order" class="flex items-center gap-2 flex-wrap bg-stone-50 rounded-lg p-2">
          <input v-model="editPhone" :placeholder="t('cf.phonePh')" maxlength="20"
                 class="h-9 w-[170px] ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] font-mono focus:outline-none" />
          <input v-model="editCity" :placeholder="t('cf.cityPh')" maxlength="60"
                 class="h-9 w-[170px] ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none" />
          <button class="h-9 px-3 rounded-lg text-[12px] font-semibold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50"
                  :disabled="savingContact" @click="saveContact(r)">{{ t('px.common.save') }}</button>
        </div>
      </div>

      <!-- pager -->
      <div v-if="total > pageSize" class="flex items-center justify-between px-1 pt-1">
        <span class="text-[11.5px] text-stone-500 tabular-nums">
          {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} / {{ total }}
        </span>
        <div class="flex items-center gap-1">
          <button class="pg-btn" :disabled="page <= 1" @click="page--; load()"><Icon name="chevron-left" :size="13" class="flip-rtl" /></button>
          <button class="pg-btn" :disabled="page * pageSize >= total" @click="page++; load()"><Icon name="chevron-right" :size="13" class="flip-rtl" /></button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const TABS = [
  { key: "pending", label: "cf.tabPending" },
  { key: "dna", label: "cf.tabDna" },
  { key: "followup", label: "cf.tabFollowup" },
  { key: "onhold", label: "cf.tabOnhold" },
];

const tab = ref("pending");
const q = ref("");
const page = ref(1);
const pageSize = 30;
const data = ref(null);
const rows = ref([]);
const total = ref(0);
const loading = ref(true);
const busy = ref("");
const cancelFor = ref("");
const cancelReason = ref("");
const editFor = ref("");
const editPhone = ref("");
const editCity = ref("");
const savingContact = ref(false);

let qTimer = null;
function debouncedLoad() {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { page.value = 1; load(); }, 350);
}

async function load() {
  loading.value = true;
  try {
    const res = await api("confirmation.board", {
      tab: tab.value, q: q.value, limit: pageSize,
      offset: (page.value - 1) * pageSize,
    });
    data.value = res;
    rows.value = res.rows || [];
    total.value = res.total || 0;
  } catch (e) {
    warn(t("cf.loadFail"), String(e.message || e));
    rows.value = [];
  } finally {
    loading.value = false;
  }
}
onMounted(load);

async function act(r, action, note) {
  busy.value = r.order;
  try {
    const res = await apiPost("confirmation.act", { order: r.order, action, note });
    rows.value = rows.value.filter((x) => x.order !== r.order);
    total.value = Math.max(0, total.value - 1);
    if (data.value?.counts) {
      data.value.counts[tab.value] = Math.max(0, (data.value.counts[tab.value] || 1) - 1);
      if (action === "dna") data.value.counts.dna += (tab.value === "dna" ? 1 : 1);
      if (action === "followup" && tab.value !== "followup") data.value.counts.followup++;
      if (action === "onhold" && tab.value !== "onhold") data.value.counts.onhold++;
      if (data.value.mine && action in data.value.mine) data.value.mine[action]++;
    }
    cancelFor.value = "";
    cancelReason.value = "";
    success(t(`cf.done_${action}`), r.order + (res.attempts ? ` · ${t('cf.attempts')} ${res.attempts}` : ""));
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

function toggleEdit(r) {
  if (editFor.value === r.order) { editFor.value = ""; return; }
  editFor.value = r.order;
  editPhone.value = r.phone || "";
  editCity.value = r.city || "";
}

async function saveContact(r) {
  savingContact.value = true;
  try {
    const res = await apiPost("confirmation.update_contact", {
      order: r.order, phone: editPhone.value, city: editCity.value,
    });
    if (!res.unchanged) {
      r.phone = editPhone.value.trim() || r.phone;
      r.city = editCity.value.trim() || r.city;
      success(t("cf.contactSaved"), (res.updated || []).join(" · "));
    }
    editFor.value = "";
  } catch (e) {
    warn(t("cf.contactFail"), String(e.message || e));
  } finally {
    savingContact.value = false;
  }
}

function waLink(phone) {
  const p = String(phone || "").replace(/[^0-9]/g, "");
  return "https://wa.me/" + (p.startsWith("212") ? p : "212" + p.replace(/^0/, ""));
}
function ageLabel(h) {
  return h < 48 ? `${h}${t('cf.hrs')}` : `${Math.round(h / 24)}${t('cf.days')}`;
}
function fmtMAD(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
</script>

<style scoped>
.day-chip {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums;
  border-radius: 8px; padding: 0 10px; height: 30px;
  box-shadow: inset 0 0 0 1px currentColor;
}
.day-chip.ring-emerald-200 { box-shadow: inset 0 0 0 1px rgb(167 243 208); }
.day-chip.ring-amber-200 { box-shadow: inset 0 0 0 1px rgb(253 230 138); }
.day-chip.ring-rose-200 { box-shadow: inset 0 0 0 1px rgb(254 205 211); }
.contact-btn {
  width: 34px; height: 34px; border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  box-shadow: inset 0 0 0 1px rgb(231 229 228); background: white;
  transition: all .15s;
}
.act-btn {
  height: 34px; padding: 0 12px; border-radius: 10px;
  font-size: 12px; font-weight: 600; white-space: nowrap;
  transition: background .15s;
}
.act-btn:disabled { opacity: .5; }
.pg-btn {
  width: 30px; height: 30px; border-radius: 8px; background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  display: inline-flex; align-items: center; justify-content: center;
}
.pg-btn:disabled { opacity: .4; }
</style>
