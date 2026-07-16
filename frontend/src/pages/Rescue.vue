<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1200px] mx-auto">
    <!-- hero -->
    <header class="rs-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3.5">
          <span class="rs-hero-icon"><Icon name="route" :size="22" /></span>
          <div>
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('rs.title') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5">{{ t('rs.intro') }}</p>
          </div>
        </div>
        <div v-if="data" class="flex items-stretch gap-2">
          <div class="rs-stat">
            <span class="rs-stat-n text-emerald-600">{{ data.mine.redeliver + data.mine.reship }}</span>
            <span class="rs-stat-l"><Icon name="refresh-cw" :size="10" class="inline -mt-px me-0.5" />{{ t('rs.statSaved') }}</span>
          </div>
          <div class="rs-stat">
            <span class="rs-stat-n text-amber-600">{{ data.mine.dna }}</span>
            <span class="rs-stat-l"><Icon name="phone-off" :size="10" class="inline -mt-px me-0.5" />{{ t('cf.actDna') }}</span>
          </div>
          <div class="rs-stat">
            <span class="rs-stat-n text-rose-500">{{ data.mine.returnreq + data.mine.cancel }}</span>
            <span class="rs-stat-l"><Icon name="rotate-ccw" :size="10" class="inline -mt-px me-0.5" />{{ t('rs.statLost') }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- queues + search -->
    <div class="flex items-center gap-3 flex-wrap">
      <div class="rs-seg">
        <button
          v-for="tb in TABS" :key="tb.key"
          class="rs-seg-btn"
          :class="tab === tb.key ? 'rs-seg-on' : ''"
          @click="tab = tb.key; page = 1; load()"
        >
          <Icon :name="tb.icon" :size="14" />
          <span>{{ t(tb.label) }}</span>
          <span class="rs-seg-count" :class="tab === tb.key ? tb.onColor : 'bg-stone-200/70 text-stone-500'">
            {{ data?.counts?.[tb.key] ?? '–' }}
          </span>
        </button>
      </div>
      <div class="relative ms-auto">
        <Icon name="search" :size="13" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input v-model="q" :placeholder="t('rs.searchPh')" @input="debouncedLoad"
               class="h-10 w-[240px] ps-9 pe-3 text-[12.5px] bg-white rounded-xl ring-1 ring-stone-200/80 focus:ring-2 outline-none transition-shadow"
               style="--tw-ring-color: rgb(125 211 252)" />
      </div>
    </div>

    <!-- backlog bulk bar -->
    <div v-if="tab === 'backlog' && !loading && rows.length"
         class="flex items-center gap-2.5 flex-wrap bg-white rounded-2xl ring-1 ring-stone-200/80 px-4 py-3">
      <label class="inline-flex items-center gap-2 text-[12.5px] font-medium text-stone-700 cursor-pointer">
        <input type="checkbox" :checked="selected.size === rows.length" class="accent-sky-600 w-4 h-4"
               @change="toggleAll" />
        {{ t('rs.selectPage') }}
      </label>
      <span class="text-[12px] text-stone-400 tabular-nums">{{ selected.size }} {{ t('rs.selectedN') }}</span>
      <div class="flex items-center gap-2 ms-auto flex-wrap">
        <input v-model="bulkNote" :placeholder="t('rs.bulkNotePh')" maxlength="120"
               class="h-9 w-[200px] ps-3 pe-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] focus:outline-none" />
        <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-rose-700 bg-rose-50 ring-1 ring-rose-200 hover:bg-rose-100 disabled:opacity-40 transition-colors"
                :disabled="!selected.size || bulkBusy" @click="bulkAct('returnreq')">
          <Icon name="rotate-ccw" :size="13" class="inline -mt-px me-1" />{{ t('rs.bulkReturn') }}
        </button>
        <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 hover:bg-emerald-100 disabled:opacity-40 transition-colors"
                :disabled="!selected.size || bulkBusy" @click="bulkAct('resolve')">
          <Icon name="check" :size="13" class="inline -mt-px me-1" />{{ t('rs.bulkResolve') }}
        </button>
      </div>
    </div>

    <!-- rows -->
    <div v-if="loading" class="space-y-2.5">
      <div v-for="n in 6" :key="n" class="h-[76px] rounded-2xl rs-shimmer" />
    </div>
    <div v-else-if="!rows.length" class="rs-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('rs.empty') }}</div>
      <div class="text-[12.5px] text-stone-400 mt-1">{{ t('rs.emptyHint') }}</div>
    </div>
    <TransitionGroup v-else name="rsrow" tag="div" class="space-y-2.5 relative">
      <div v-for="r in rows" :key="r.id"
           class="rs-card rounded-2xl p-4"
           :class="r.due ? 'rs-card-due' : ''">
        <div class="flex items-center gap-3.5 flex-wrap">
          <input v-if="tab === 'backlog'" type="checkbox" class="accent-sky-600 w-4 h-4 shrink-0"
                 :checked="selected.has(r.id)" @change="toggleOne(r.id)" />
          <span class="rs-avatar" :class="r.due ? 'rs-avatar-due' : ''">{{ initial(r.customer) }}</span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[13.5px] font-bold text-stone-900 truncate max-w-[220px]">{{ r.customer || '—' }}</span>
              <span class="font-mono text-[11px] text-stone-400">{{ r.order || r.dn }}</span>
              <span class="rs-track" :class="trackClass(r.track)">{{ t('track.' + trackKey(r.track), r.track) }}</span>
              <span v-if="r.due" class="rs-due-badge">{{ t('cf.due') }}</span>
              <span v-else-if="r.slaBreached && tab !== 'backlog'" class="rs-due-badge">{{ t('rs.slaLate') }}</span>
            </div>
            <div class="flex items-center gap-2.5 text-[11.5px] text-stone-500 tabular-nums mt-1 flex-wrap">
              <span class="font-semibold text-stone-800">{{ fmtMAD(r.total) }} <span class="text-stone-400 font-normal">MAD</span></span>
              <span v-if="r.awb" class="font-mono text-[10.5px]">{{ r.awb }}</span>
              <span v-if="r.city" class="inline-flex items-center gap-1"><Icon name="map-pin" :size="11" class="text-stone-300" />{{ r.city }}</span>
              <span class="inline-flex items-center gap-1" :class="ageColor(r.ageD)"><Icon name="clock" :size="11" />{{ r.ageD }}{{ t('cf.days') }}</span>
              <span v-if="r.attempts" class="inline-flex items-center gap-1 text-amber-600 font-medium"><Icon name="phone-off" :size="11" />×{{ r.attempts }}</span>
              <span v-if="r.nextCall" class="text-stone-400">→ {{ r.nextCall.slice(5) }}</span>
            </div>
          </div>
          <!-- contact -->
          <div class="flex items-center gap-1.5">
            <a v-if="r.phone" :href="'tel:' + r.phone" :title="r.phone" class="rs-contact rs-tel">
              <Icon name="phone" :size="15" />
            </a>
            <a v-if="r.phone" :href="waLink(r.phone)" target="_blank" title="WhatsApp" class="rs-contact rs-wa">
              <Icon name="message-circle" :size="15" />
            </a>
          </div>
          <!-- decisions -->
          <div class="flex items-center gap-1.5 flex-wrap">
            <button class="rs-act rs-act-save" :disabled="busy === r.id" :title="t('rs.actRedeliverHint')"
                    @click="act(r, 'redeliver')">
              <Icon name="refresh-cw" :size="14" class="inline -mt-px me-1" />{{ t('rs.actRedeliver') }}
            </button>
            <button class="rs-act rs-act-soft text-violet-700" :disabled="busy === r.id" :title="t('rs.actReshipHint')"
                    @click="act(r, 'reship')"><Icon name="send" :size="15" /></button>
            <button class="rs-act rs-act-soft text-amber-700" :disabled="busy === r.id" :title="t('cf.actDna')"
                    @click="act(r, 'dna')"><Icon name="phone-off" :size="15" /></button>
            <button class="rs-act rs-act-soft text-rose-600" :disabled="busy === r.id" :title="t('rs.actReturn')"
                    :class="reasonFor === r.id && reasonAction === 'returnreq' ? 'ring-2' : ''"
                    @click="openReason(r, 'returnreq')"><Icon name="rotate-ccw" :size="15" /></button>
            <button class="rs-act rs-act-soft text-stone-500" :disabled="busy === r.id" :title="t('rs.actCancel')"
                    :class="reasonFor === r.id && reasonAction === 'cancel' ? 'ring-2' : ''"
                    @click="openReason(r, 'cancel')"><Icon name="circle-x" :size="15" /></button>
          </div>
        </div>

        <!-- reason panel (return / cancel) -->
        <Transition name="rsslide">
          <div v-if="reasonFor === r.id" class="space-y-2 bg-rose-50/70 rounded-xl p-2.5 mt-3">
            <div class="text-[11px] font-semibold text-rose-700">
              {{ reasonAction === 'cancel' ? t('rs.actCancel') : t('rs.actReturn') }}
            </div>
            <div v-if="data?.reasons?.length" class="flex flex-wrap gap-1.5">
              <button v-for="rs in data.reasons" :key="rs"
                      class="h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1 transition-all"
                      :class="reason === rs ? 'text-white bg-rose-600 ring-rose-600 shadow-sm' : 'text-rose-700 bg-white ring-rose-200 hover:bg-rose-100'"
                      @click="reason = rs">{{ rs }}</button>
            </div>
            <div class="flex items-center gap-2">
              <input v-model="reason" :placeholder="t('cf.cancelPh')" maxlength="120"
                     class="flex-1 h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-rose-200 text-[12.5px] focus:outline-none" />
              <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 transition-colors"
                      :disabled="(reasonAction === 'cancel' && !reason.trim()) || busy === r.id"
                      @click="act(r, reasonAction, reason)">{{ t('rs.confirmDecision') }}</button>
            </div>
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
        <button :title="t('common.back')" class="pg-btn" :disabled="page <= 1" @click="page--; load()"><Icon name="chevron-left" :size="13" class="flip-rtl" /></button>
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
  { key: "exceptions", label: "rs.tabExceptions", icon: "alert-triangle", onColor: "bg-rose-100 text-rose-700" },
  { key: "failed", label: "rs.tabFailed", icon: "alert-circle", onColor: "bg-amber-100 text-amber-700" },
  { key: "notdelivered", label: "rs.tabNotDelivered", icon: "package", onColor: "bg-violet-100 text-violet-700" },
  { key: "stale", label: "rs.tabStale", icon: "clock", onColor: "bg-sky-100 text-sky-700" },
  { key: "backlog", label: "rs.tabBacklog", icon: "archive", onColor: "bg-stone-200 text-stone-700" },
];

const tab = ref("exceptions");
const q = ref("");
const page = ref(1);
const pageSize = 30;
const data = ref(null);
const rows = ref([]);
const total = ref(0);
const loading = ref(true);
const busy = ref("");
const reasonFor = ref("");
const reasonAction = ref("");
const reason = ref("");
const selected = ref(new Set());
const bulkNote = ref("");
const bulkBusy = ref(false);

function toggleAll() {
  selected.value = selected.value.size === rows.value.length
    ? new Set() : new Set(rows.value.map((r) => r.id));
}
function toggleOne(id) {
  const s = new Set(selected.value);
  s.has(id) ? s.delete(id) : s.add(id);
  selected.value = s;
}

async function bulkAct(action) {
  bulkBusy.value = true;
  try {
    const res = await apiPost("rescue.bulk_act", {
      ids: [...selected.value], action, note: bulkNote.value,
    });
    success(t("rs.bulkDone"), `${res.done}`);
    selected.value = new Set();
    bulkNote.value = "";
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    bulkBusy.value = false;
  }
}

let qTimer = null;
function debouncedLoad() {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { page.value = 1; load(); }, 350);
}

async function load() {
  loading.value = true;
  selected.value = new Set();
  try {
    const res = await api("rescue.board", {
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

function openReason(r, action) {
  if (reasonFor.value === r.id && reasonAction.value === action) {
    reasonFor.value = "";
    return;
  }
  reasonFor.value = r.id;
  reasonAction.value = action;
  reason.value = "";
}

async function act(r, action, note) {
  busy.value = r.id;
  try {
    const res = await apiPost("rescue.act", { id: r.id, action, note });
    // dna keeps the row in its queue (with a new timer); decisions remove it
    if (action !== "dna") {
      rows.value = rows.value.filter((x) => x.id !== r.id);
      total.value = Math.max(0, total.value - 1);
      if (data.value?.counts) {
        data.value.counts[tab.value] = Math.max(0, (data.value.counts[tab.value] || 1) - 1);
      }
    } else {
      const row = rows.value.find((x) => x.id === r.id);
      if (row) { row.attempts = res.attempts; row.due = false; }
    }
    if (data.value?.mine && action in data.value.mine) data.value.mine[action]++;
    reasonFor.value = "";
    reason.value = "";
    const label = action === "reship" && res.order
      ? `${r.order} → ${t('rs.done_reship')}` : t(`rs.done_${action}`);
    success(label, r.id + (res.attempts ? ` · ×${res.attempts}` : ""));
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

const TRACK_KEYS = {
  "Delivery Exception": "exception", "Failed Attempt": "failed",
  "Out For Delivery": "ofd", "In Transit": "intransit",
  "Pending": "pending", "Not Delivered": "notdelivered",
};
function trackKey(track) { return TRACK_KEYS[track] || "pending"; }
function trackClass(track) {
  if (track === "Delivery Exception") return "text-rose-700 bg-rose-50 ring-rose-200";
  if (track === "Failed Attempt") return "text-amber-700 bg-amber-50 ring-amber-200";
  if (track === "Not Delivered") return "text-violet-700 bg-violet-50 ring-violet-200";
  return "text-sky-700 bg-sky-50 ring-sky-200";
}
function waLink(phone) {
  const p = String(phone || "").replace(/[^0-9]/g, "");
  return "https://wa.me/" + (p.startsWith("212") ? p : "212" + p.replace(/^0/, ""));
}
function initial(name) {
  const w = String(name || "").trim().split(/\s+/);
  return ((w[0]?.[0] || "؟") + (w[1]?.[0] || "")).toUpperCase();
}
function ageColor(d) {
  if (d < 7) return "text-amber-600";
  if (d < 14) return "text-rose-500";
  return "text-rose-600 font-semibold";
}
function fmtMAD(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
</script>

<style scoped>
.rs-hero {
  background: linear-gradient(135deg, rgb(240 249 255) 0%, #fff 45%, #fff 70%, rgb(240 249 255) 100%);
  box-shadow: inset 0 0 0 1px rgb(186 230 253 / 0.6), 0 1px 2px rgb(0 0 0 / 0.03);
}
.rs-hero-icon {
  width: 52px; height: 52px; border-radius: 16px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: white;
  background: linear-gradient(135deg, rgb(14 165 233), rgb(2 132 199));
  box-shadow: 0 6px 16px -6px rgb(14 165 233 / 0.55);
}
.rs-stat {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-width: 78px; padding: 8px 14px; border-radius: 14px;
  background: rgb(255 255 255 / 0.75); backdrop-filter: blur(4px);
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.9), 0 1px 2px rgb(0 0 0 / 0.03);
}
.rs-stat-n { font-size: 21px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.rs-stat-l { font-size: 10px; font-weight: 600; color: rgb(168 162 158); margin-top: 4px; white-space: nowrap; }

.rs-seg { display: inline-flex; gap: 2px; padding: 4px; background: rgb(231 229 228 / 0.55); border-radius: 14px; }
.rs-seg-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 12px; border-radius: 11px;
  font-size: 12.5px; font-weight: 600; color: rgb(120 113 108);
  transition: all .18s ease;
}
.rs-seg-btn:hover { color: rgb(41 37 36); }
.rs-seg-on { background: white; color: rgb(28 25 23); box-shadow: 0 1px 3px rgb(0 0 0 / 0.08), 0 1px 2px rgb(0 0 0 / 0.04); }
.rs-seg-count { font-size: 11px; font-weight: 700; font-variant-numeric: tabular-nums; padding: 1px 7px; border-radius: 999px; }

.rs-card {
  background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8), 0 1px 2px rgb(0 0 0 / 0.02);
  transition: box-shadow .18s ease, transform .18s ease;
}
.rs-card:hover {
  box-shadow: inset 0 0 0 1px rgb(214 211 209), 0 8px 24px -12px rgb(0 0 0 / 0.14);
  transform: translateY(-1px);
}
.rs-card-due { box-shadow: inset 0 0 0 1.5px rgb(252 211 77), 0 4px 16px -8px rgb(245 158 11 / 0.25); }
.rs-avatar {
  width: 42px; height: 42px; border-radius: 999px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800; color: rgb(2 132 199);
  background: linear-gradient(135deg, rgb(240 249 255), rgb(224 242 254));
  box-shadow: inset 0 0 0 1px rgb(186 230 253);
}
.rs-avatar-due {
  color: rgb(180 83 9);
  background: linear-gradient(135deg, rgb(255 251 235), rgb(254 243 199));
  box-shadow: inset 0 0 0 1px rgb(252 211 77);
}
.rs-track {
  font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 999px;
  box-shadow: inset 0 0 0 1px currentColor;
}
.rs-due-badge {
  font-size: 10px; font-weight: 800; letter-spacing: .02em;
  color: white; background: rgb(245 158 11);
  padding: 2px 8px; border-radius: 999px;
  animation: rs-pulse 2s ease-in-out infinite;
}
@keyframes rs-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .55; } }

.rs-contact {
  width: 38px; height: 38px; border-radius: 12px;
  display: inline-flex; align-items: center; justify-content: center;
  background: white; box-shadow: inset 0 0 0 1px rgb(231 229 228);
  transition: all .15s ease;
}
.rs-contact:hover { transform: scale(1.06); }
.rs-tel { color: rgb(87 83 78); }
.rs-tel:hover { color: rgb(4 120 87); box-shadow: inset 0 0 0 1px rgb(110 231 183); }
.rs-wa { color: rgb(22 163 74); }
.rs-wa:hover { box-shadow: inset 0 0 0 1px rgb(134 239 172); background: rgb(240 253 244); }
.rs-act {
  height: 38px; border-radius: 12px; font-size: 12.5px; font-weight: 700;
  transition: all .15s ease; white-space: nowrap;
}
.rs-act:disabled { opacity: .5; }
.rs-act-save {
  padding: 0 16px; color: white;
  background: linear-gradient(135deg, rgb(16 185 129), rgb(5 150 105));
  box-shadow: 0 4px 12px -4px rgb(16 185 129 / 0.4);
}
.rs-act-save:hover { box-shadow: 0 6px 16px -4px rgb(16 185 129 / 0.55); transform: translateY(-1px); }
.rs-act-soft {
  width: 38px; background: rgb(250 250 249);
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  --tw-ring-color: currentColor;
  display: inline-flex; align-items: center; justify-content: center;
}
.rs-act-soft:hover { background: white; transform: scale(1.06); box-shadow: inset 0 0 0 1px currentColor; }

.rs-empty { background: linear-gradient(180deg, white, rgb(250 250 249)); box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8); }
.rs-shimmer {
  background: linear-gradient(90deg, rgb(245 245 244) 25%, rgb(231 229 228 / 0.6) 50%, rgb(245 245 244) 75%);
  background-size: 200% 100%;
  animation: rs-shimmer 1.4s ease-in-out infinite;
}
@keyframes rs-shimmer { to { background-position: -200% 0; } }
.pg-btn {
  width: 32px; height: 32px; border-radius: 10px; background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  display: inline-flex; align-items: center; justify-content: center;
}
.pg-btn:disabled { opacity: .4; }

.rsrow-leave-active { transition: all .28s ease; position: relative; }
.rsrow-leave-to { opacity: 0; transform: translateX(24px) scale(.98); }
.rsrow-enter-active { transition: all .25s ease; }
.rsrow-enter-from { opacity: 0; transform: translateY(6px); }
.rsrow-move { transition: transform .28s ease; }
.rsslide-enter-active, .rsslide-leave-active { transition: all .2s ease; }
.rsslide-enter-from, .rsslide-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
