<template>
  <div class="max-w-[980px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('mv.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('mv.intro') }}</p>
      </div>
      <div v-if="loadingBoot" class="flex items-center gap-2">
        <span v-for="n in 3" :key="n" class="w-[110px] h-8 rounded-lg bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <div v-else-if="boot" class="flex items-center gap-2 flex-wrap">
        <span class="kpi-chip text-stone-700 bg-white ring-stone-200">
          {{ boot.kpis.todayMoves }} {{ t('mv.movesToday') }} · {{ boot.kpis.todayUnits }} {{ t('recv.units') }}
        </span>
        <span class="kpi-chip text-amber-700 bg-amber-50 ring-amber-200">
          {{ t('mv.inReceiving') }} {{ boot.kpis.receivingUnits }}
        </span>
        <span class="kpi-chip text-sky-700 bg-sky-50 ring-sky-200">
          SLOW {{ boot.kpis.slowUnits }}
        </span>
      </div>
    </header>

    <!-- Scanner -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
      <ScanInput ref="scanner" :placeholder="t('mv.scanPh')" @scan="onScan" />
    </div>

    <!-- Move card -->
    <div v-if="current" class="bg-white rounded-2xl ring-1 ring-[var(--accent-300)] shadow-md p-4 space-y-4">
      <div class="flex items-center gap-3">
        <img v-if="current.image" :src="current.image" alt="" @error="hideImg"
             class="w-16 h-16 rounded-xl object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
        <span v-else class="w-16 h-16 rounded-xl bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400">
          <Icon name="package" :size="22" />
        </span>
        <div class="min-w-0 flex-1">
          <div class="text-[14.5px] font-semibold text-stone-900 truncate">{{ current.name }}</div>
          <div class="font-mono text-[12px] text-stone-500">{{ current.sku || current.itemCode }}</div>
        </div>
        <button class="w-8 h-8 rounded-lg hover:bg-stone-100 flex items-center justify-center flex-shrink-0" @click="clearCurrent">
          <Icon name="x" :size="16" />
        </button>
      </div>

      <!-- source bin -->
      <div class="flex items-start gap-3 flex-wrap">
        <span class="text-[12.5px] font-medium text-stone-600 w-16 mt-2">{{ t('mv.from') }}</span>
        <div class="flex-1 min-w-[200px] flex flex-wrap gap-1.5">
          <button
            v-for="b in current.bins.slice(0, 8)" :key="b.warehouse"
            class="h-8 px-2.5 rounded-lg text-[12px] font-semibold ring-1 transition-colors tabular-nums"
            :class="source === b.warehouse
              ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]'
              : 'text-stone-700 bg-white ring-stone-200 hover:ring-stone-300'"
            @click="pickSource(b)"
          >{{ short(b.warehouse) }} · {{ b.qty }}</button>
        </div>
      </div>

      <!-- qty stepper -->
      <div class="flex items-center gap-3">
        <span class="text-[12.5px] font-medium text-stone-600 w-16">{{ t('restock.qty') }}</span>
        <div class="flex items-center gap-1">
          <button class="w-9 h-9 rounded-lg bg-stone-100 text-[16px] font-bold" @click="qty = Math.max(1, qty - 1)">−</button>
          <input v-model.number="qty" type="number" min="1" :max="sourceQty"
                 class="w-16 h-9 text-center text-[16px] font-bold tabular-nums rounded-lg ring-1 ring-stone-200 focus:outline-none" />
          <button class="w-9 h-9 rounded-lg bg-stone-100 text-[16px] font-bold" @click="qty = Math.min(sourceQty, qty + 1)">+</button>
        </div>
        <button class="text-[11.5px] font-semibold text-[var(--accent-700)]" @click="qty = sourceQty">
          {{ t('restock.all') }} ({{ sourceQty }})
        </button>
      </div>

      <!-- target bin -->
      <div class="flex items-start gap-3 flex-wrap">
        <span class="text-[12.5px] font-medium text-stone-600 w-16 mt-2">{{ t('mv.to') }}</span>
        <div class="flex-1 min-w-[200px] space-y-2">
          <div v-if="targetChips.length" class="flex flex-wrap gap-1.5">
            <button
              v-for="b in targetChips" :key="b.warehouse"
              class="h-8 px-2.5 rounded-lg text-[12px] font-semibold ring-1 transition-colors tabular-nums"
              :class="target === b.warehouse
                ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]'
                : 'text-stone-700 bg-white ring-stone-200 hover:ring-stone-300'"
              @click="target = b.warehouse"
            >{{ short(b.warehouse) }} · {{ b.qty }} {{ t('restock.already') }}</button>
          </div>
          <input
            v-model="target"
            list="lp-move-targets"
            :placeholder="t('mv.anyBin')"
            class="w-full h-10 ps-3 pe-3 rounded-lg bg-white ring-1 text-[13px] text-stone-800 focus:outline-none focus:ring-2"
            :class="target && !targetValid ? 'ring-rose-300' : 'ring-stone-200'"
            style="--tw-ring-color: var(--accent-400)"
          />
          <datalist id="lp-move-targets">
            <option v-for="w in boot?.warehouses || []" :key="w" :value="w" />
          </datalist>
          <p v-if="target && !targetValid" class="text-[11px] text-rose-600">{{ t('mv.invalidBin') }}</p>
          <p v-else-if="target && target === source" class="text-[11px] text-rose-600">{{ t('mv.sameBin') }}</p>
        </div>
      </div>

      <button
        class="w-full h-11 rounded-xl text-[13.5px] font-semibold text-white bg-emerald-600 hover:bg-emerald-700 flex items-center justify-center gap-2 disabled:opacity-50"
        :disabled="busy || !canMove"
        @click="doMove"
      >
        <Icon name="route" :size="16" /> {{ busy ? t('restock.moving') : t('mv.moveBtn') }}
      </button>
    </div>

    <!-- Queues -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-3 pt-2.5 flex items-center gap-1.5 border-b border-stone-100">
        <button
          v-for="tb in TABS" :key="tb.key"
          class="h-8 px-3 rounded-t-lg text-[12px] font-semibold transition-colors"
          :class="tab === tb.key ? 'text-[var(--accent-700)] bg-[var(--accent-50)]' : 'text-stone-500 hover:text-stone-700'"
          @click="tab = tb.key"
        >{{ t(tb.label) }}<span v-if="tb.key !== 'recent' && counts[tb.key] != null" class="ms-1 tabular-nums">({{ counts[tb.key] }})</span></button>
      </div>

      <!-- skeleton -->
      <div v-if="loadingTab" class="p-3 space-y-2">
        <div v-for="n in 5" :key="n" class="h-[52px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
      </div>

      <!-- putaway -->
      <div v-else-if="tab === 'putaway'" class="divide-y divide-stone-50 max-h-[440px] overflow-y-auto">
        <p v-if="!putaway.length" class="px-4 py-6 text-center text-[12.5px] text-stone-400">{{ t('mv.putawayEmpty') }}</p>
        <button
          v-for="r in putaway" :key="r.itemCode + r.source"
          class="w-full text-start px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50 transition-colors"
          @click="prefill(r, r.source, r.suggest, r.qty)"
        >
          <RowImg :src="r.image" />
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ r.name }}</div>
            <div class="font-mono text-[10.5px] text-stone-400">{{ r.sku || r.itemCode }} · {{ short(r.source) }}</div>
          </div>
          <span class="text-[12px] font-bold tabular-nums text-stone-800">{{ r.qty }}</span>
          <span class="text-[11.5px] tabular-nums w-[110px] text-end" :class="r.suggest ? 'text-emerald-600 font-semibold' : 'text-stone-400'">
            {{ r.suggest ? '→ ' + short(r.suggest) : t('mv.noShelfYet') }}
          </span>
        </button>
      </div>

      <!-- replenish -->
      <div v-else-if="tab === 'replenish'" class="divide-y divide-stone-50 max-h-[440px] overflow-y-auto">
        <p v-if="!replenish.length" class="px-4 py-6 text-center text-[12.5px] text-stone-400">{{ t('mv.replenishEmpty') }}</p>
        <button
          v-for="r in replenish" :key="r.itemCode"
          class="w-full text-start px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50 transition-colors"
          @click="prefill(r, boot?.slowWh, r.suggest, r.suggested)"
        >
          <RowImg :src="r.image" />
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ r.name }}</div>
            <div class="font-mono text-[10.5px] text-stone-400">{{ r.sku || r.itemCode }}</div>
          </div>
          <div class="text-end">
            <div class="text-[11px] text-stone-500 tabular-nums">{{ t('mv.shelfQty') }} <b :class="r.shelfQty === 0 ? 'text-rose-600' : 'text-stone-800'">{{ r.shelfQty }}</b> · {{ t('mv.sold14') }} {{ r.sold14 }}</div>
            <div class="text-[11.5px] font-semibold text-emerald-600 tabular-nums">{{ t('mv.moveN') }} {{ r.suggested }}</div>
          </div>
        </button>
      </div>

      <!-- recent -->
      <div v-else class="divide-y divide-stone-50 max-h-[440px] overflow-y-auto">
        <p v-if="!recent.length" class="px-4 py-6 text-center text-[12.5px] text-stone-400">{{ t('mv.recentEmpty') }}</p>
        <div v-for="m in recent" :key="m.entry" class="px-4 py-2 flex items-center gap-3 text-[12px]">
          <span class="text-[10.5px] text-stone-400 tabular-nums w-[74px] flex-shrink-0">{{ m.time }}</span>
          <span class="font-mono font-medium text-stone-800 truncate max-w-[130px]">{{ m.itemCode }}</span>
          <span class="tabular-nums font-bold text-stone-700">×{{ m.qty }}</span>
          <span class="text-stone-500 truncate flex-1">{{ short(m.source) }} → {{ short(m.target) }}</span>
          <span v-if="m.viaPortal" class="text-[10px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded px-1.5 py-0.5">{{ t('mv.viaPortal') }}</span>
          <span class="font-mono text-[10.5px] text-stone-400">{{ m.entry }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, h, onMounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const TABS = [
  { key: "putaway", label: "mv.tabPutaway" },
  { key: "replenish", label: "mv.tabReplenish" },
  { key: "recent", label: "mv.tabRecent" },
];

const RowImg = (props) => props.src
  ? h("img", { src: props.src, alt: "", loading: "lazy", class: "w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0", onError: hideImg })
  : h("span", { class: "w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400" }, [h(Icon, { name: "package", size: 14 })]);
RowImg.props = ["src"];

const scanner = ref(null);
const boot = ref(null);
const loadingBoot = ref(true);
const current = ref(null);
const source = ref("");
const target = ref("");
const qty = ref(1);
const busy = ref(false);

const tab = ref("putaway");
const loadingTab = ref(true);
const putaway = ref([]);
const replenish = ref([]);
const recent = ref([]);
const counts = computed(() => ({ putaway: putaway.value.length, replenish: replenish.value.length }));

const sourceQty = computed(() => {
  const b = (current.value?.bins || []).find((x) => x.warehouse === source.value);
  return b ? b.qty : 0;
});
const targetChips = computed(() =>
  (current.value?.bins || []).filter((b) => b.warehouse !== source.value).slice(0, 3));
const targetValid = computed(() =>
  !!target.value && (boot.value?.warehouses || []).includes(target.value));
const canMove = computed(() =>
  !!current.value && !!source.value && targetValid.value &&
  target.value !== source.value && qty.value >= 1 && qty.value <= sourceQty.value);

async function loadBoot() {
  try {
    boot.value = await api("stock_moves.move_boot");
    recent.value = boot.value.recent || [];
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loadingBoot.value = false;
  }
}
async function loadTab(which) {
  loadingTab.value = true;
  try {
    if (which === "putaway") putaway.value = (await api("stock_moves.putaway_queue")).rows || [];
    else if (which === "replenish") replenish.value = (await api("stock_moves.replenish_queue")).rows || [];
    else recent.value = (await api("stock_moves.recent_moves")).rows || [];
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loadingTab.value = false;
  }
}
watch(tab, (v) => loadTab(v));
onMounted(async () => {
  await Promise.all([loadBoot(), loadTab(tab.value)]);
  scanner.value?.refocus();
});

async function onScan(raw) {
  const code = String(raw || "").trim();
  if (!code) return;
  let res;
  try {
    res = await apiPost("stock_moves.move_lookup", { code });
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
    return;
  }
  if (!res.ok) {
    scanner.value?.showError(res.reason === "no_stock" ? t("mv.noStock") : t("pickm.unknown"));
    return;
  }
  current.value = res;
  source.value = res.bins[0]?.warehouse || "";
  qty.value = res.bins[0]?.qty || 1;
  target.value = "";
  scanner.value?.showSuccess(`${res.name} · ${res.bins.length} ${t('mv.bins')}`);
}

function pickSource(b) {
  source.value = b.warehouse;
  qty.value = Math.min(qty.value, b.qty) || b.qty;
  if (target.value === b.warehouse) target.value = "";
}

/** A queue row was tapped: load the item and pre-fill the whole move. */
async function prefill(r, src, tgt, n) {
  let res;
  try {
    res = await apiPost("stock_moves.move_lookup", { code: r.sku || r.itemCode });
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
    return;
  }
  if (!res.ok) { warn(t("mv.noStock"), r.itemCode); return; }
  current.value = res;
  source.value = src && res.bins.some((b) => b.warehouse === src) ? src : (res.bins[0]?.warehouse || "");
  const cap = (res.bins.find((b) => b.warehouse === source.value) || {}).qty || 1;
  qty.value = Math.min(Math.max(1, n || cap), cap);
  target.value = tgt || "";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function doMove() {
  if (!canMove.value || busy.value) return;
  busy.value = true;
  try {
    const res = await apiPost("stock_moves.move_stock", {
      item_code: current.value.itemCode, qty: qty.value,
      source: source.value, target: target.value,
    });
    success(t("mv.moved"), `${res.itemCode} ×${res.qty} · ${short(res.source)} → ${short(res.target)}`);
    // refresh the card from live bins + active queue
    await Promise.all([onScan(current.value.sku || current.value.itemCode), loadTab(tab.value), loadBoot()]);
  } catch (e) {
    warn(t("restock.moveFail"), String(e.message || e));
  } finally {
    busy.value = false;
    scanner.value?.refocus();
  }
}

function clearCurrent() { current.value = null; scanner.value?.refocus(); }
function short(w) { return String(w || "").replace(" - JM", ""); }
function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }
</script>

<style scoped>
.kpi-chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600;
  border-radius: 8px; padding: 0 10px; height: 32px;
  box-shadow: inset 0 0 0 1px var(--tw-ring-color, transparent);
  font-variant-numeric: tabular-nums;
  --tw-ring-shadow: none;
}
.kpi-chip.ring-stone-200 { box-shadow: inset 0 0 0 1px rgb(231 229 228); }
.kpi-chip.ring-amber-200 { box-shadow: inset 0 0 0 1px rgb(253 230 138); }
.kpi-chip.ring-sky-200 { box-shadow: inset 0 0 0 1px rgb(186 230 253); }
</style>
