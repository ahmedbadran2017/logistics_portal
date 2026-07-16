<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1200px] mx-auto">
    <!-- hero -->
    <header class="ex-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3.5">
          <span class="ex-hero-icon"><Icon name="refresh-cw" :size="22" /></span>
          <div>
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('ex.title') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5">{{ t('ex.intro') }}</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <input v-model="newOrder" :placeholder="t('ex.orderPh')" maxlength="30"
                 class="h-10 w-[180px] ps-3 pe-3 rounded-xl bg-white ring-1 ring-stone-200/80 text-[12.5px] font-mono focus:ring-2 focus:ring-amber-300 outline-none"
                 @keyup.enter="start" />
          <button class="ex-new" :disabled="!newOrder.trim() || starting" @click="start">
            <Icon name="plus" :size="15" class="inline -mt-px me-1" />{{ starting ? '…' : t('ex.start') }}
          </button>
        </div>
      </div>
    </header>

    <!-- tabs + search -->
    <div class="flex items-center gap-3 flex-wrap">
      <div class="ex-seg">
        <button v-for="tb in TABS" :key="tb.key" class="ex-seg-btn" :class="tab === tb.key ? 'ex-seg-on' : ''"
                @click="tab = tb.key; page = 1; load()">
          <Icon :name="tb.icon" :size="14" />
          <span>{{ t(tb.label) }}</span>
          <span class="ex-seg-count" :class="tab === tb.key ? tb.onColor : 'bg-stone-200/70 text-stone-500'">
            {{ data?.counts?.[tb.key] ?? '–' }}
          </span>
        </button>
      </div>
      <div class="relative ms-auto">
        <Icon name="search" :size="13" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input v-model="q" :placeholder="t('ex.searchPh')" @input="debouncedLoad"
               class="h-10 w-[240px] ps-9 pe-3 text-[12.5px] bg-white rounded-xl ring-1 ring-stone-200/80 focus:ring-2 focus:ring-amber-300 outline-none" />
      </div>
    </div>

    <!-- rows -->
    <div v-if="loading" class="space-y-2.5">
      <div v-for="n in 5" :key="n" class="h-[80px] rounded-2xl ex-shimmer" />
    </div>
    <div v-else-if="loadError" class="ex-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-rose-50 text-rose-500 mb-3"><Icon name="alert-triangle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[12px] text-stone-400 mt-1 font-mono max-w-[420px] mx-auto break-words">{{ loadError }}</div>
    </div>
    <div v-else-if="!rows.length" class="ex-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('ex.empty') }}</div>
      <div class="text-[12.5px] text-stone-400 mt-1">{{ t('ex.emptyHint') }}</div>
    </div>

    <TransitionGroup v-else name="exrow" tag="div" class="space-y-2.5 relative">
      <div v-for="r in rows" :key="r.name" class="ex-card rounded-2xl p-4">
        <div class="flex items-center gap-3.5 flex-wrap">
          <span class="ex-avatar"><Icon name="refresh-cw" :size="16" /></span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[13.5px] font-bold text-stone-900 truncate max-w-[220px]">{{ r.customer || '—' }}</span>
              <span class="font-mono text-[11px] text-stone-400">{{ r.order }}</span>
              <span v-if="r.exOrder" class="font-mono text-[11px] text-amber-600">→ {{ r.exOrder }}</span>
              <span class="ex-chip" :class="statusClass(r.status)">{{ t('ex.st' + r.status.replace(/ /g, ''), r.status) }}</span>
              <span v-if="r.status === 'Label Generated' && r.settlement === 'Pending' && r.difference"
                    class="ex-chip" :class="r.difference > 0 ? 'text-emerald-700 bg-emerald-50' : 'text-rose-700 bg-rose-50'">
                {{ r.difference > 0 ? t('ex.collect') : t('ex.refund') }} {{ Math.abs(r.difference) }} MAD
              </span>
            </div>
            <div class="flex items-center gap-2.5 text-[11.5px] text-stone-500 tabular-nums mt-1 flex-wrap">
              <span v-if="r.phone" class="font-mono">{{ r.phone }}</span>
              <span v-if="r.city" class="inline-flex items-center gap-1"><Icon name="map-pin" :size="11" class="text-stone-300" />{{ r.city }}</span>
              <span v-if="r.awb" class="font-mono text-[10.5px] text-amber-700">{{ r.awb }}</span>
              <span class="inline-flex items-center gap-1 text-stone-400"><Icon name="clock" :size="11" />{{ ageLabel(r.ageH) }}</span>
            </div>
            <div v-if="r.itemsText" class="text-[11.5px] text-stone-500 truncate max-w-[560px] mt-1" :title="r.itemsText" dir="auto">
              <Icon name="package" :size="11" class="inline -mt-px me-1 text-stone-300" />{{ r.itemsText }}
            </div>
          </div>
          <div class="flex items-center gap-1.5 flex-wrap">
            <a v-if="r.labelUrl" :href="r.labelUrl" target="_blank" class="ex-act ex-act-soft text-stone-600" :title="t('ex.label')">
              <Icon name="printer" :size="15" />
            </a>
            <template v-if="tab === 'waiting'">
              <button class="ex-act ex-act-soft text-amber-700" :title="t('ex.editItems')"
                      :class="editFor === r.name ? 'ring-2' : ''" @click="toggleEdit(r)">
                <Icon name="edit" :size="15" />
              </button>
              <button class="ex-act ex-act-main" :disabled="busy === r.name || !r.itemsText" @click="generate(r)">
                <Icon name="zap" :size="14" class="inline -mt-px me-1" />{{ busy === r.name ? '…' : t('ex.generate') }}
              </button>
            </template>
            <button v-else-if="tab === 'labeled'" class="ex-act ex-act-main" :disabled="busy === r.name" @click="settle(r)">
              <Icon name="check" :size="14" class="inline -mt-px me-1" />{{ t('ex.settle') }}
            </button>
          </div>
        </div>

        <!-- items editor -->
        <Transition name="exslide">
          <div v-if="editFor === r.name" class="bg-amber-50/50 rounded-xl p-3 mt-3 space-y-2">
            <div v-for="(it, i) in editItems" :key="i" class="flex items-center gap-2 flex-wrap">
              <input v-model="it.item_code" :placeholder="t('ex.itemPh')" maxlength="140"
                     class="flex-1 min-w-[220px] h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] font-mono focus:outline-none" />
              <input v-model.number="it.qty" type="number" min="1" :placeholder="t('ex.qtyPh')"
                     class="w-[80px] h-9 ps-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] tabular-nums focus:outline-none" />
              <input v-model.number="it.rate" type="number" min="0" :placeholder="t('ex.ratePh')"
                     class="w-[110px] h-9 ps-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] tabular-nums focus:outline-none" />
              <button :title="t('common.close')" class="w-8 h-8 rounded-lg text-stone-400 hover:text-rose-600 hover:bg-rose-50 inline-flex items-center justify-center"
                      @click="editItems.splice(i, 1)"><Icon name="x" :size="13" /></button>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
              <button class="h-8 px-3 rounded-lg text-[11.5px] font-semibold text-amber-700 bg-white ring-1 ring-amber-200 hover:bg-amber-100 transition-colors"
                      @click="editItems.push({ item_code: '', qty: 1, rate: 0 })">
                <Icon name="plus" :size="12" class="inline -mt-px me-1" />{{ t('ex.addItem') }}
              </button>
              <span class="ms-auto" />
              <button class="h-9 px-4 rounded-lg text-[12px] font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 transition-colors"
                      :disabled="savingItems || !editItems.some(x => x.item_code.trim())" @click="saveItems(r)">
                {{ savingItems ? '…' : t('px.common.save') }}
              </button>
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
  { key: "waiting", label: "ex.tabWaiting", icon: "edit", onColor: "bg-amber-100 text-amber-700" },
  { key: "labeled", label: "ex.tabLabeled", icon: "tag", onColor: "bg-sky-100 text-sky-700" },
  { key: "settled", label: "ex.tabSettled", icon: "check-circle", onColor: "bg-emerald-100 text-emerald-700" },
];

const tab = ref("waiting");
const q = ref("");
const page = ref(1);
const pageSize = 30;
const data = ref(null);
const rows = ref([]);
const total = ref(0);
const loading = ref(true);
const loadError = ref("");
const busy = ref("");
const newOrder = ref("");
const starting = ref(false);
const editFor = ref("");
const editItems = ref([]);
const savingItems = ref(false);

let qTimer = null;
function debouncedLoad() {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { page.value = 1; load(); }, 350);
}

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const res = await api("exchange.board", {
      tab: tab.value, q: q.value, limit: pageSize,
      offset: (page.value - 1) * pageSize,
    });
    data.value = res;
    rows.value = res.rows || [];
    total.value = res.total || 0;
  } catch (e) {
    loadError.value = String(e.message || e);
    rows.value = [];
  } finally {
    loading.value = false;
  }
}
onMounted(load);

async function start() {
  starting.value = true;
  try {
    const res = await apiPost("exchange.start", { order: newOrder.value.trim() });
    success(t("ex.started"), res.name);
    newOrder.value = "";
    tab.value = "waiting";
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    starting.value = false;
  }
}

function toggleEdit(r) {
  if (editFor.value === r.name) { editFor.value = ""; return; }
  editFor.value = r.name;
  editItems.value = [{ item_code: "", qty: 1, rate: 0 }];
}

async function saveItems(r) {
  savingItems.value = true;
  try {
    const items = editItems.value.filter((x) => x.item_code.trim());
    const res = await apiPost("exchange.set_items", { name: r.name, items });
    success(t("ex.itemsSaved"),
            `${res.direction || ""} ${Math.abs(res.difference || 0)} MAD`);
    editFor.value = "";
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    savingItems.value = false;
  }
}

async function generate(r) {
  busy.value = r.name;
  try {
    const res = await apiPost("exchange.generate", { name: r.name });
    success(t("ex.generated"), `${res.awb} → ${res.exOrder}`);
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

async function settle(r) {
  busy.value = r.name;
  try {
    await apiPost("exchange.settle", { name: r.name });
    success(t("ex.settled"), r.name);
    rows.value = rows.value.filter((x) => x.name !== r.name);
    if (data.value?.counts) { data.value.counts.labeled--; data.value.counts.settled++; }
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

function statusClass(s) {
  if (s === "Label Generated") return "text-sky-700 bg-sky-50";
  if (s === "Settled") return "text-emerald-700 bg-emerald-50";
  if (s === "Cancelled") return "text-stone-500 bg-stone-100";
  return "text-amber-700 bg-amber-50";
}
function ageLabel(h) {
  return h < 48 ? `${h}${t('cf.hrs')}` : `${Math.round(h / 24)}${t('cf.days')}`;
}
</script>

<style scoped>
.ex-hero {
  background: linear-gradient(135deg, rgb(255 251 235) 0%, #fff 45%, #fff 70%, rgb(255 251 235) 100%);
  box-shadow: inset 0 0 0 1px rgb(253 230 138 / 0.6), 0 1px 2px rgb(0 0 0 / 0.03);
}
.ex-hero-icon {
  width: 52px; height: 52px; border-radius: 16px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: white;
  background: linear-gradient(135deg, rgb(251 191 36), rgb(217 119 6));
  box-shadow: 0 6px 16px -6px rgb(217 119 6 / 0.5);
}
.ex-new {
  height: 40px; padding: 0 16px; border-radius: 12px;
  font-size: 12.5px; font-weight: 700; color: white;
  background: linear-gradient(135deg, rgb(251 191 36), rgb(217 119 6));
  box-shadow: 0 4px 12px -4px rgb(217 119 6 / 0.4);
  transition: all .15s ease;
}
.ex-new:hover { transform: translateY(-1px); }
.ex-new:disabled { opacity: .5; }
.ex-seg { display: inline-flex; gap: 2px; padding: 4px; background: rgb(231 229 228 / 0.55); border-radius: 14px; }
.ex-seg-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 12px; border-radius: 11px;
  font-size: 12.5px; font-weight: 600; color: rgb(120 113 108);
  transition: all .18s ease;
}
.ex-seg-btn:hover { color: rgb(41 37 36); }
.ex-seg-on { background: white; color: rgb(28 25 23); box-shadow: 0 1px 3px rgb(0 0 0 / 0.08); }
.ex-seg-count { font-size: 11px; font-weight: 700; font-variant-numeric: tabular-nums; padding: 1px 7px; border-radius: 999px; }
.ex-card {
  background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8), 0 1px 2px rgb(0 0 0 / 0.02);
  transition: box-shadow .18s ease, transform .18s ease;
}
.ex-card:hover {
  box-shadow: inset 0 0 0 1px rgb(214 211 209), 0 8px 24px -12px rgb(0 0 0 / 0.14);
  transform: translateY(-1px);
}
.ex-avatar {
  width: 42px; height: 42px; border-radius: 999px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: rgb(180 83 9);
  background: linear-gradient(135deg, rgb(255 251 235), rgb(254 243 199));
  box-shadow: inset 0 0 0 1px rgb(253 230 138);
}
.ex-chip { font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 999px; }
.ex-act {
  height: 38px; border-radius: 12px; font-size: 12.5px; font-weight: 700;
  transition: all .15s ease; white-space: nowrap;
}
.ex-act:disabled { opacity: .5; }
.ex-act-main {
  padding: 0 16px; color: white;
  background: linear-gradient(135deg, rgb(251 191 36), rgb(217 119 6));
  box-shadow: 0 4px 12px -4px rgb(217 119 6 / 0.4);
}
.ex-act-main:hover:not(:disabled) { transform: translateY(-1px); }
.ex-act-soft {
  width: 38px; background: rgb(250 250 249);
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  display: inline-flex; align-items: center; justify-content: center;
}
.ex-act-soft:hover { background: white; transform: scale(1.06); }
.ex-empty { background: linear-gradient(180deg, white, rgb(250 250 249)); box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8); }
.ex-shimmer {
  background: linear-gradient(90deg, rgb(245 245 244) 25%, rgb(231 229 228 / 0.6) 50%, rgb(245 245 244) 75%);
  background-size: 200% 100%;
  animation: ex-shimmer 1.4s ease-in-out infinite;
}
@keyframes ex-shimmer { to { background-position: -200% 0; } }
.pg-btn {
  width: 32px; height: 32px; border-radius: 10px; background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  display: inline-flex; align-items: center; justify-content: center;
}
.pg-btn:disabled { opacity: .4; }
.exrow-leave-active { transition: all .28s ease; position: relative; }
.exrow-leave-to { opacity: 0; transform: translateX(24px) scale(.98); }
.exrow-enter-active { transition: all .25s ease; }
.exrow-enter-from { opacity: 0; transform: translateY(6px); }
.exrow-move { transition: transform .28s ease; }
.exslide-enter-active, .exslide-leave-active { transition: all .2s ease; }
.exslide-enter-from, .exslide-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
