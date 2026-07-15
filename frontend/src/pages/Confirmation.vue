<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1200px] mx-auto">
    <!-- hero header -->
    <header class="cf-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3.5">
          <span class="cf-hero-icon"><Icon name="phone" :size="22" /></span>
          <div>
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('cf.title') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5">{{ t('cf.intro') }}</p>
          </div>
        </div>
        <div v-if="data" class="flex items-stretch gap-2">
          <div class="cf-stat">
            <span class="cf-stat-n text-emerald-600">{{ data.mine.confirm }}</span>
            <span class="cf-stat-l"><Icon name="check-circle" :size="10" class="inline -mt-px me-0.5" />{{ t('cf.actConfirm') }}</span>
          </div>
          <div class="cf-stat">
            <span class="cf-stat-n text-amber-600">{{ data.mine.dna }}</span>
            <span class="cf-stat-l"><Icon name="phone-off" :size="10" class="inline -mt-px me-0.5" />{{ t('cf.actDna') }}</span>
          </div>
          <div class="cf-stat">
            <span class="cf-stat-n text-rose-500">{{ data.mine.cancel }}</span>
            <span class="cf-stat-l"><Icon name="x" :size="10" class="inline -mt-px me-0.5" />{{ t('cf.actCancel') }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- segmented queues + search -->
    <div class="flex items-center gap-3 flex-wrap">
      <div class="cf-seg">
        <button
          v-for="tb in TABS" :key="tb.key"
          class="cf-seg-btn"
          :class="tab === tb.key ? 'cf-seg-on' : ''"
          @click="tab = tb.key; page = 1; load()"
        >
          <Icon :name="tb.icon" :size="14" />
          <span>{{ t(tb.label) }}</span>
          <span class="cf-seg-count" :class="tab === tb.key ? tb.onColor : 'bg-stone-200/70 text-stone-500'">
            {{ data?.counts?.[tb.key] ?? '–' }}
          </span>
        </button>
      </div>
      <div class="relative ms-auto">
        <Icon name="search" :size="13" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input v-model="q" :placeholder="t('cf.searchPh')" @input="debouncedLoad"
               class="h-10 w-[240px] ps-9 pe-3 text-[12.5px] bg-white rounded-xl ring-1 ring-stone-200/80 focus:ring-2 outline-none transition-shadow"
               style="--tw-ring-color: var(--accent-300)" />
      </div>
    </div>

    <!-- rows -->
    <div v-if="loading" class="space-y-2.5">
      <div v-for="n in 6" :key="n" class="h-[76px] rounded-2xl cf-shimmer" />
    </div>
    <div v-else-if="!rows.length" class="cf-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('cf.empty') }}</div>
      <div class="text-[12.5px] text-stone-400 mt-1">{{ t('cf.emptyHint') }}</div>
    </div>
    <TransitionGroup v-else name="cfrow" tag="div" class="space-y-2.5 relative">
      <div v-for="r in rows" :key="r.order"
           class="cf-card rounded-2xl p-4"
           :class="r.due ? 'cf-card-due' : ''">
        <div class="flex items-center gap-3.5 flex-wrap">
          <!-- customer identity -->
          <span class="cf-avatar" :class="r.due ? 'cf-avatar-due' : ''">{{ initial(r.customer) }}</span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[13.5px] font-bold text-stone-900 truncate max-w-[220px]">{{ r.customer || '—' }}</span>
              <span class="font-mono text-[11px] text-stone-400">{{ r.order }}</span>
              <span v-if="r.due" class="cf-due-badge">{{ t('cf.due') }}</span>
            </div>
            <div class="flex items-center gap-2.5 text-[11.5px] text-stone-500 tabular-nums mt-1 flex-wrap">
              <span class="font-semibold text-stone-800">{{ fmtMAD(r.total) }} <span class="text-stone-400 font-normal">MAD</span></span>
              <span v-if="r.city" class="inline-flex items-center gap-1"><Icon name="map-pin" :size="11" class="text-stone-300" />{{ r.city }}</span>
              <span>{{ r.items }} {{ t('consol.items') }}</span>
              <span class="inline-flex items-center gap-1" :class="ageColor(r.ageH)"><Icon name="clock" :size="11" />{{ ageLabel(r.ageH) }}</span>
              <span v-if="r.attempts" class="inline-flex items-center gap-1 text-amber-600 font-medium"><Icon name="phone-off" :size="11" />×{{ r.attempts }}</span>
              <span v-if="r.agent" class="text-stone-400">{{ r.agent }}</span>
              <span v-if="r.nextCall" class="text-stone-400">→ {{ r.nextCall.slice(5) }}</span>
            </div>
            <div v-if="r.itemsText" class="text-[11.5px] text-stone-500 truncate max-w-[560px] mt-1"
                 :title="r.itemsText" dir="auto">
              <Icon name="package" :size="11" class="inline -mt-px me-1 text-stone-300" />{{ r.itemsText }}
            </div>
          </div>
          <!-- contact -->
          <div class="flex items-center gap-1.5">
            <a v-if="r.phone" :href="'tel:' + r.phone" :title="r.phone" class="cf-contact cf-tel">
              <Icon name="phone" :size="15" />
            </a>
            <a v-if="r.phone" :href="waLink(r.phone)" target="_blank" title="WhatsApp" class="cf-contact cf-wa">
              <Icon name="message-circle" :size="15" />
            </a>
            <button class="cf-contact text-stone-400 hover:text-stone-700"
                    :class="editFor === r.order ? 'bg-stone-100' : ''"
                    :title="t('cf.editContact')" @click="toggleEdit(r)">
              <Icon name="edit" :size="13" />
            </button>
          </div>
          <!-- decisions -->
          <div class="flex items-center gap-1.5 flex-wrap">
            <button class="cf-act cf-act-confirm" :disabled="busy === r.order" @click="act(r, 'confirm')">
              <Icon name="check" :size="14" class="inline -mt-px me-1" />{{ t('cf.actConfirm') }}
            </button>
            <button class="cf-act cf-act-soft text-amber-700" :disabled="busy === r.order" :title="t('cf.actDna')" @click="act(r, 'dna')"><Icon name="phone-off" :size="15" /></button>
            <button class="cf-act cf-act-soft text-sky-700" :disabled="busy === r.order" :title="t('cf.actFollowup')" @click="act(r, 'followup')"><Icon name="clock" :size="15" /></button>
            <button class="cf-act cf-act-soft text-stone-500" :disabled="busy === r.order" :title="t('cf.actOnhold')" @click="act(r, 'onhold')"><Icon name="pause" :size="15" /></button>
            <button class="cf-act cf-act-soft text-violet-600" :disabled="busy === r.order" :title="t('cf.actDuplicate')" @click="act(r, 'duplicate')"><Icon name="copy" :size="15" /></button>
            <button class="cf-act cf-act-soft text-rose-600" :disabled="busy === r.order"
                    :class="cancelFor === r.order ? 'ring-2' : ''"
                    @click="cancelFor = cancelFor === r.order ? '' : r.order"><Icon name="x" :size="15" /></button>
          </div>
        </div>

        <!-- cancel reason -->
        <Transition name="cfslide">
          <div v-if="cancelFor === r.order" class="space-y-2 bg-rose-50/70 rounded-xl p-2.5 mt-3">
            <div v-if="data?.reasons?.length" class="flex flex-wrap gap-1.5">
              <button v-for="rs in data.reasons" :key="rs"
                      class="h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1 transition-all"
                      :class="cancelReason === rs ? 'text-white bg-rose-600 ring-rose-600 shadow-sm' : 'text-rose-700 bg-white ring-rose-200 hover:bg-rose-100'"
                      @click="cancelReason = rs">{{ rs }}</button>
            </div>
            <div class="flex items-center gap-2">
              <input v-model="cancelReason" :placeholder="t('cf.cancelPh')" maxlength="120"
                     class="flex-1 h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-rose-200 text-[12.5px] focus:outline-none" />
              <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 transition-colors"
                      :disabled="!cancelReason.trim() || busy === r.order"
                      @click="act(r, 'cancel', cancelReason)">{{ t('cf.cancelConfirm') }}</button>
            </div>
          </div>
        </Transition>

        <!-- contact edit -->
        <Transition name="cfslide">
          <div v-if="editFor === r.order" class="flex items-center gap-2 flex-wrap bg-stone-50 rounded-xl p-2.5 mt-3">
            <input v-model="editPhone" :placeholder="t('cf.phonePh')" maxlength="20"
                   class="h-9 w-[180px] ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] font-mono focus:outline-none" />
            <input v-model="editCity" :placeholder="t('cf.cityPh')" maxlength="60"
                   class="h-9 w-[180px] ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none" />
            <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50"
                    :disabled="savingContact" @click="saveContact(r)">{{ t('px.common.save') }}</button>
          </div>
        </Transition>
      </div>
    </TransitionGroup>

    <!-- pager -->
    <div v-if="!loading && total > pageSize" class="flex items-center justify-between px-1">
      <span class="text-[11.5px] text-stone-500 tabular-nums">
        {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} / {{ total }}
      </span>
      <div class="flex items-center gap-1">
        <button class="pg-btn" :disabled="page <= 1" @click="page--; load()"><Icon name="chevron-left" :size="13" class="flip-rtl" /></button>
        <button class="pg-btn" :disabled="page * pageSize >= total" @click="page++; load()"><Icon name="chevron-right" :size="13" class="flip-rtl" /></button>
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
  { key: "pending", label: "cf.tabPending", icon: "shopping-bag", onColor: "bg-[var(--accent-100)] text-[var(--accent-700)]" },
  { key: "dna", label: "cf.tabDna", icon: "phone-off", onColor: "bg-amber-100 text-amber-700" },
  { key: "followup", label: "cf.tabFollowup", icon: "clock", onColor: "bg-sky-100 text-sky-700" },
  { key: "onhold", label: "cf.tabOnhold", icon: "pause", onColor: "bg-stone-200 text-stone-600" },
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
      if (action === "dna") data.value.counts.dna++;
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
function initial(name) {
  const w = String(name || "").trim().split(/\s+/);
  return ((w[0]?.[0] || "؟") + (w[1]?.[0] || "")).toUpperCase();
}
function ageLabel(h) {
  return h < 48 ? `${h}${t('cf.hrs')}` : `${Math.round(h / 24)}${t('cf.days')}`;
}
function ageColor(h) {
  if (h < 12) return "text-emerald-600";
  if (h < 48) return "text-amber-600";
  return "text-rose-500 font-medium";
}
function fmtMAD(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
</script>

<style scoped>
/* ── hero ─────────────────────────────────────────────── */
.cf-hero {
  background: linear-gradient(135deg, var(--accent-50) 0%, #fff 45%, #fff 70%, var(--accent-50) 100%);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent-300) 45%, transparent),
              0 1px 2px rgb(0 0 0 / 0.03);
}
.cf-hero-icon {
  width: 52px; height: 52px; border-radius: 16px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: white;
  background: linear-gradient(135deg, var(--accent-500), var(--accent-700));
  box-shadow: 0 6px 16px -6px color-mix(in srgb, var(--accent-600) 55%, transparent);
}
.cf-stat {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-width: 78px; padding: 8px 14px; border-radius: 14px;
  background: rgb(255 255 255 / 0.75); backdrop-filter: blur(4px);
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.9), 0 1px 2px rgb(0 0 0 / 0.03);
}
.cf-stat-n { font-size: 21px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.cf-stat-l { font-size: 10px; font-weight: 600; color: rgb(168 162 158); margin-top: 4px; white-space: nowrap; }

/* ── segmented control ────────────────────────────────── */
.cf-seg {
  display: inline-flex; gap: 2px; padding: 4px;
  background: rgb(231 229 228 / 0.55); border-radius: 14px;
}
.cf-seg-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 12px; border-radius: 11px;
  font-size: 12.5px; font-weight: 600; color: rgb(120 113 108);
  transition: all .18s ease;
}
.cf-seg-btn:hover { color: rgb(41 37 36); }
.cf-seg-on {
  background: white; color: rgb(28 25 23);
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.08), 0 1px 2px rgb(0 0 0 / 0.04);
}
.cf-seg-count {
  font-size: 11px; font-weight: 700; font-variant-numeric: tabular-nums;
  padding: 1px 7px; border-radius: 999px;
}

/* ── row cards ────────────────────────────────────────── */
.cf-card {
  background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8), 0 1px 2px rgb(0 0 0 / 0.02);
  transition: box-shadow .18s ease, transform .18s ease;
}
.cf-card:hover {
  box-shadow: inset 0 0 0 1px rgb(214 211 209), 0 8px 24px -12px rgb(0 0 0 / 0.14);
  transform: translateY(-1px);
}
.cf-card-due {
  box-shadow: inset 0 0 0 1.5px rgb(252 211 77), 0 4px 16px -8px rgb(245 158 11 / 0.25);
}
.cf-avatar {
  width: 42px; height: 42px; border-radius: 999px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800; color: var(--accent-700);
  background: linear-gradient(135deg, var(--accent-50), var(--accent-100));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent-300) 50%, transparent);
}
.cf-avatar-due {
  color: rgb(180 83 9);
  background: linear-gradient(135deg, rgb(255 251 235), rgb(254 243 199));
  box-shadow: inset 0 0 0 1px rgb(252 211 77);
}
.cf-due-badge {
  font-size: 10px; font-weight: 800; letter-spacing: .02em;
  color: white; background: rgb(245 158 11);
  padding: 2px 8px; border-radius: 999px;
  animation: cf-pulse 2s ease-in-out infinite;
}
@keyframes cf-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .55; }
}

/* ── contact + action buttons ─────────────────────────── */
.cf-contact {
  width: 38px; height: 38px; border-radius: 12px;
  display: inline-flex; align-items: center; justify-content: center;
  background: white; box-shadow: inset 0 0 0 1px rgb(231 229 228);
  transition: all .15s ease;
}
.cf-contact:hover { transform: scale(1.06); }
.cf-tel { color: rgb(87 83 78); }
.cf-tel:hover { color: rgb(4 120 87); box-shadow: inset 0 0 0 1px rgb(110 231 183); }
.cf-wa { color: rgb(22 163 74); }
.cf-wa:hover { box-shadow: inset 0 0 0 1px rgb(134 239 172); background: rgb(240 253 244); }
.cf-act {
  height: 38px; border-radius: 12px; font-size: 12.5px; font-weight: 700;
  transition: all .15s ease; white-space: nowrap;
}
.cf-act:disabled { opacity: .5; }
.cf-act-confirm {
  padding: 0 16px; color: white;
  background: linear-gradient(135deg, rgb(16 185 129), rgb(5 150 105));
  box-shadow: 0 4px 12px -4px rgb(16 185 129 / 0.4);
}
.cf-act-confirm:hover { box-shadow: 0 6px 16px -4px rgb(16 185 129 / 0.55); transform: translateY(-1px); }
.cf-act-soft {
  width: 38px; background: rgb(250 250 249);
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  --tw-ring-color: currentColor;
}
.cf-act-soft:hover { background: white; transform: scale(1.06); box-shadow: inset 0 0 0 1px currentColor; }

/* ── empty / shimmer / pager ──────────────────────────── */
.cf-empty {
  background: linear-gradient(180deg, white, rgb(250 250 249));
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8);
}
.cf-shimmer {
  background: linear-gradient(90deg, rgb(245 245 244) 25%, rgb(231 229 228 / 0.6) 50%, rgb(245 245 244) 75%);
  background-size: 200% 100%;
  animation: cf-shimmer 1.4s ease-in-out infinite;
}
@keyframes cf-shimmer { to { background-position: -200% 0; } }
.pg-btn {
  width: 32px; height: 32px; border-radius: 10px; background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  display: inline-flex; align-items: center; justify-content: center;
}
.pg-btn:disabled { opacity: .4; }

/* ── list + panel animations ──────────────────────────── */
.cfrow-leave-active { transition: all .28s ease; position: relative; }
.cfrow-leave-to { opacity: 0; transform: translateX(24px) scale(.98); }
.cfrow-enter-active { transition: all .25s ease; }
.cfrow-enter-from { opacity: 0; transform: translateY(6px); }
.cfrow-move { transition: transform .28s ease; }
.cfslide-enter-active, .cfslide-leave-active { transition: all .2s ease; }
.cfslide-enter-from, .cfslide-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
