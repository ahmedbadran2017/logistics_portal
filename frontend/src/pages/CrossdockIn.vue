<template>
  <!-- Cross-dock in: a supplier who keeps stock at their place drops goods for
       orders already confirmed. Supplier-first; each scanned piece fills the
       oldest waiting order that still needs it; one Receive posts a Purchase
       Receipt per order into Cross-dock - JM and reserves the units for it.
       Backend: logistics_portal.api.crossdock_in. -->
  <div class="max-w-[1080px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cdi.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[720px]">{{ t('cdi.intro') }}</p>
      </div>
      <div v-if="supplier && countedUnits" class="flex items-center gap-2">
        <span class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded-lg px-2.5 h-8 tabular-nums">
          {{ touchedOrders }} {{ t('cdi.orders') }} · {{ countedUnits }} {{ t('cdi.units') }}
        </span>
      </div>
    </header>

    <div v-if="boot && !boot.ready" class="rounded-xl bg-amber-50 ring-1 ring-amber-200 px-4 py-3 text-[12.5px] text-amber-800">{{ t('cdi.notReady') }}</div>

    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 sticky top-2 z-10 shadow-sm">
      <ScanInput ref="scanner" :placeholder="t('cdi.scanPh')" @scan="onScan" />
      <div class="mt-1.5 text-[11px] text-stone-400">{{ t('cdi.scanHint') }}</div>
    </div>

    <!-- No supplier yet: who is at the door -->
    <div v-if="!supplier" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 space-y-3">
      <div class="text-[12.5px] font-semibold text-stone-800">{{ t('cdi.suppliers') }}</div>
      <div v-if="loading" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        <div v-for="n in 6" :key="n" class="h-[68px] rounded-xl bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <p v-else-if="!(boot?.suppliers || []).length" class="text-[12.5px] text-stone-400 py-4 text-center">{{ t('cdi.noneWaiting') }}</p>
      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        <button v-for="s in boot.suppliers" :key="s.supplier" @click="openSupplier(s.supplier)"
                class="text-start rounded-xl ring-1 ring-stone-200 bg-white hover:ring-[var(--accent-400)] px-3.5 py-3 transition-shadow hover:shadow-sm">
          <div class="flex items-center gap-2">
            <span class="w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-600)] flex items-center justify-center flex-shrink-0"><Icon name="truck" :size="15" /></span>
            <span class="text-[13.5px] font-semibold text-stone-900 truncate">{{ s.supplier }}</span>
          </div>
          <div class="mt-1.5 text-[11.5px] text-stone-500 tabular-nums">
            {{ s.orders }} {{ t('cdi.orders') }} · {{ s.units }} {{ t('cdi.units') }} ·
            <span :class="s.oldestH > 9 ? 'text-rose-600 font-semibold' : ''">{{ t('cdi.oldest') }} {{ age(s.oldestH) }}</span>
          </div>
        </button>
      </div>
    </div>

    <!-- Supplier open: their waiting orders -->
    <template v-else>
      <div class="bg-white rounded-2xl ring-1 ring-[var(--accent-300)] shadow-sm p-4 flex items-center gap-3 flex-wrap">
        <span class="w-9 h-9 rounded-xl bg-[var(--accent-50)] text-[var(--accent-600)] flex items-center justify-center"><Icon name="truck" :size="17" /></span>
        <div class="flex-1 min-w-0">
          <div class="text-[15px] font-bold text-stone-900 truncate">{{ supplier }}</div>
          <div class="text-[12px] text-stone-500 tabular-nums">{{ orders.length }} {{ t('cdi.orders') }} · {{ t('cdi.into') }} <span class="font-mono">{{ boot?.target }}</span></div>
        </div>
        <input v-model="note" :placeholder="t('cdi.refPh')" maxlength="80"
               class="w-[260px] max-w-full h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none focus:ring-2 focus:ring-[var(--accent-400)]" />
        <button class="h-9 px-3 rounded-lg text-[12px] font-semibold text-stone-600 bg-stone-100 hover:bg-stone-200" @click="closeSupplier">{{ t('cdi.change') }}</button>
      </div>

      <!-- A scanned handover sheet: only its orders, unless widened -->
      <div v-if="sheet" class="rounded-xl bg-[var(--accent-50)] ring-1 ring-[var(--accent-200)] px-4 py-2.5 flex items-center gap-3 flex-wrap">
        <Icon name="clipboard-check" :size="15" class="text-[var(--accent-600)]" />
        <span class="text-[12.5px] font-semibold text-stone-800">{{ t('cdi.sheet') }} <span class="font-mono">{{ sheet.name }}</span></span>
        <span class="text-[11.5px] text-stone-500 tabular-nums">{{ sheet.pos.length }}/{{ sheet.total }} {{ t('cdi.sheetWaiting') }}</span>
        <label class="ms-auto flex items-center gap-1.5 text-[12px] text-stone-600 cursor-pointer">
          <input type="checkbox" v-model="sheetOnly" /> {{ t('cdi.sheetOnly') }}
        </label>
        <button class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold text-emerald-700 bg-white ring-1 ring-emerald-200 hover:bg-emerald-50" @click="fillSheet">{{ t('cdi.fillSheet') }}</button>
      </div>

      <p v-if="!loading && !orders.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 py-10 text-center text-[12.5px] text-stone-400">{{ t('cdi.noneWaiting') }}</p>

      <div class="space-y-2.5">
        <div v-for="o in shownOrders" :key="o.po" :id="'cdi-' + o.po"
             class="bg-white rounded-2xl ring-1 shadow-sm overflow-hidden transition-all"
             :class="[o.problem ? 'ring-rose-300' : orderCount(o) >= o.pending ? 'ring-emerald-300' : orderCount(o) ? 'ring-amber-300' : 'ring-stone-200/70',
                      flash === o.po ? 'ring-2 ring-[var(--accent-500)]' : '']">
          <div class="px-4 py-2.5 flex items-center gap-2.5 flex-wrap border-b border-stone-100">
            <span class="font-mono text-[13px] font-bold text-stone-900">{{ o.so }}</span>
            <span class="text-[11px] text-stone-400 tabular-nums">{{ t('cdi.confirmed') }} {{ o.confirmedAt.slice(5) }} ·
              <span :class="o.ageH > 9 ? 'text-rose-600 font-semibold' : ''">{{ age(o.ageH) }}</span></span>
            <span class="text-[11px] font-semibold rounded px-1.5 py-0.5 tabular-nums"
                  :class="orderCount(o) >= o.pending ? 'bg-emerald-100 text-emerald-700' : 'bg-stone-100 text-stone-600'">
              {{ orderCount(o) }}/{{ o.pending }}
            </span>
            <div class="ms-auto flex items-center gap-1.5">
              <button class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 hover:bg-emerald-100" @click="fillOrder(o)">{{ t('cdi.fill') }}</button>
              <button v-if="orderCount(o)" class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold text-stone-600 bg-stone-100 hover:bg-stone-200" @click="clearOrder(o)">{{ t('cdi.clear') }}</button>
              <button class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold ring-1"
                      :class="o.problem ? 'text-rose-700 bg-rose-50 ring-rose-200' : 'text-stone-600 bg-white ring-stone-200 hover:bg-stone-50'"
                      @click="toggleProblem(o)">
                <Icon name="alert-triangle" :size="12" class="inline -mt-0.5" /> {{ t('cdi.problem') }}
              </button>
            </div>
          </div>

          <div v-if="o.problem" class="px-4 py-2 bg-rose-50/60 border-b border-rose-100 flex items-center gap-1.5 flex-wrap">
            <button v-for="k in PROBLEM_KINDS" :key="k" @click="o.problem.kind = k"
                    class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold ring-1"
                    :class="o.problem.kind === k ? 'bg-rose-600 text-white ring-rose-600' : 'bg-white text-rose-700 ring-rose-200'">{{ t('cdi.p_' + k) }}</button>
            <input v-model="o.problem.note" :placeholder="t('cdi.problemNotePh')" maxlength="200"
                   class="flex-1 min-w-[180px] h-7 ps-2.5 pe-2 rounded-lg ring-1 ring-rose-200 bg-white text-[12px] outline-none focus:ring-2 focus:ring-rose-300" />
          </div>

          <div class="divide-y divide-stone-50">
            <div v-for="l in o.lines" :key="l.poItem" class="px-4 py-2 flex items-center gap-3"
                 :class="l.qty > 0 ? (l.qty >= l.pending ? 'bg-emerald-50/40' : 'bg-amber-50/40') : ''">
              <img v-if="l.image" :src="l.image" alt="" loading="lazy" @error="hideImg"
                   class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
              <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="14" /></span>
              <div class="min-w-0 flex-1">
                <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ l.name }}</div>
                <div class="font-mono text-[10.5px] text-stone-400 truncate">{{ l.sku || l.itemCode }}</div>
              </div>
              <span class="text-[10.5px] font-semibold rounded px-1.5 py-0.5 tabular-nums bg-stone-100 text-stone-600 whitespace-nowrap">{{ l.pending }} {{ t('cdi.left') }}</span>
              <div class="flex items-center gap-1 flex-shrink-0">
                <button class="w-8 h-8 rounded-lg bg-stone-100 text-[14px] font-bold" @click="l.qty = Math.max(0, (l.qty || 0) - 1)">−</button>
                <input v-model.number="l.qty" type="number" min="0" :max="l.pending" inputmode="numeric" @change="clampLine(l)"
                       class="w-12 h-8 text-center text-[14px] font-bold tabular-nums rounded-lg ring-1 ring-stone-200 focus:outline-none focus:ring-2 focus:ring-[var(--accent-400)]" />
                <button class="w-8 h-8 rounded-lg bg-stone-100 text-[14px] font-bold disabled:opacity-40" :disabled="(l.qty || 0) >= l.pending" @click="l.qty = Math.min(l.pending, (l.qty || 0) + 1)">+</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="orders.length" class="sticky bottom-3 z-10">
        <button class="w-full h-12 rounded-xl text-[14px] font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg transition-colors"
                :class="armed ? 'bg-amber-600 hover:bg-amber-700' : 'bg-emerald-600 hover:bg-emerald-700'"
                :disabled="busy || !entries.length" @click="post">
          <Icon name="package-check" :size="17" />
          <template v-if="busy">{{ t('cdi.posting') }}</template>
          <template v-else-if="armed">{{ t('cdi.confirm') }} — {{ touchedOrders }} {{ t('cdi.orders') }} · {{ countedUnits }} {{ t('cdi.units') }}</template>
          <template v-else>{{ t('cdi.receiveBtn') }}<span v-if="entries.length" class="tabular-nums"> · {{ touchedOrders }} {{ t('cdi.orders') }} · {{ countedUnits }} {{ t('cdi.units') }}</span></template>
        </button>
      </div>
    </template>

    <!-- Recent -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100"><span class="text-[12px] font-semibold text-stone-900">{{ t('cdi.recentTitle') }}</span></div>
      <div class="divide-y divide-stone-50 max-h-[320px] overflow-y-auto">
        <p v-if="!recent.length" class="px-4 py-6 text-center text-[12.5px] text-stone-400">{{ t('cdi.recentEmpty') }}</p>
        <div v-for="r in recent" :key="r.receipt" class="px-4 py-2 flex items-center gap-3 text-[12px]">
          <span class="text-[10.5px] text-stone-400 tabular-nums w-[74px] flex-shrink-0">{{ r.time }}</span>
          <span class="font-mono font-semibold text-stone-800">{{ r.so }}</span>
          <span class="text-stone-600 truncate max-w-[160px]">{{ r.supplier }}</span>
          <span class="tabular-nums text-stone-600">{{ r.units }} {{ t('cdi.units') }}</span>
          <span class="font-mono text-[11px] text-stone-400 truncate flex-1">{{ r.receipt }}</span>
          <span class="text-[10.5px] text-stone-400">{{ r.by }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const PROBLEM_KINDS = ["missing", "damaged", "wrong_item", "other"];

const scanner = ref(null);
const boot = ref(null);
const loading = ref(true);
const supplier = ref("");
const orders = ref([]);
const recent = ref([]);
const note = ref("");
const busy = ref(false);
const armed = ref(false);
const flash = ref("");
const sheet = ref(null);        // { name, pos: [po], total } — a scanned handover sheet
const sheetOnly = ref(true);
const shownOrders = computed(() =>
  sheet.value && sheetOnly.value ? orders.value.filter((o) => sheet.value.pos.includes(o.po)) : orders.value);

const orderCount = (o) => o.lines.reduce((s, l) => s + (l.qty || 0), 0);
const entries = computed(() => orders.value
  .filter((o) => orderCount(o) > 0 || o.problem)
  .map((o) => ({
    po: o.po,
    items: o.lines.filter((l) => (l.qty || 0) > 0).map((l) => ({ po_item: l.poItem, qty: l.qty })),
    problem: o.problem ? { kind: o.problem.kind, note: o.problem.note } : null,
  })));
const countedUnits = computed(() => orders.value.reduce((s, o) => s + orderCount(o), 0));
const touchedOrders = computed(() => entries.value.length);

async function loadBoot() {
  try {
    boot.value = await api("crossdock_in.boot");
    recent.value = boot.value.recent || [];
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
onMounted(loadBoot);

async function openSupplier(name, keep = false) {
  if (supplier.value === name && keep) return;
  loading.value = true;
  try {
    const r = await api("crossdock_in.supplier_orders", { supplier: name });
    if (supplier.value !== name) sheet.value = null;
    supplier.value = name;
    orders.value = (r.orders || []).map((o) => ({ ...o, problem: null, lines: o.lines.map((l) => ({ ...l, qty: 0 })) }));
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
    setTimeout(() => scanner.value?.refocus(), 50);
  }
}

function closeSupplier() {
  supplier.value = ""; orders.value = []; note.value = ""; sheet.value = null;
  setTimeout(() => scanner.value?.refocus(), 50);
}

function fillSheet() { shownOrders.value.forEach(fillOrder); }
function fillOrder(o) { o.lines.forEach((l) => { l.qty = l.pending; }); }
function clearOrder(o) { o.lines.forEach((l) => { l.qty = 0; }); }
function clampLine(l) { l.qty = Math.max(0, Math.min(l.pending, Number(l.qty) || 0)); }
function toggleProblem(o) { o.problem = o.problem ? null : { kind: "missing", note: "" }; }

function highlight(po) {
  flash.value = po;
  nextTick(() => document.getElementById("cdi-" + po)?.scrollIntoView({ behavior: "smooth", block: "center" }));
  setTimeout(() => { if (flash.value === po) flash.value = ""; }, 1600);
}

async function onScan(raw) {
  const code = String(raw || "").trim();
  if (!code) return;
  let res;
  try { res = await apiPost("crossdock_in.resolve", { code, supplier: supplier.value || "" }); }
  catch (e) { scanner.value?.showError(String(e.message || e)); return; }
  if (!res.ok) {
    const msg = res.reason === "order_not_expected" ? `${res.so} — ${t("cdi.orderNotExpected")}`
      : res.reason === "not_expected" ? `${res.name} — ${t("cdi.notExpected")}` : t("cdi.unknown");
    scanner.value?.showError(msg);
    return;
  }
  if (res.supplier !== supplier.value) await openSupplier(res.supplier);
  if (res.kind === "handover") {
    sheet.value = { name: res.handover, pos: res.pos || [], total: res.total || 0 };
    sheetOnly.value = true;
    scanner.value?.showSuccess(`${res.handover} · ${(res.pos || []).length}/${res.total}`);
    return;
  }
  if (res.kind === "order") {
    scanner.value?.showSuccess(res.so);
    highlight(res.po);
    return;
  }
  // A piece: the oldest waiting order that still has room for it — the
  // scanned sheet's orders first.
  const onSheet = (p) => (sheet.value && sheet.value.pos.includes(p) ? 0 : 1);
  const targets = [...res.targets].sort((a, b) => onSheet(a.po) - onSheet(b.po));
  for (const tgt of targets) {
    const o = orders.value.find((x) => x.po === tgt.po);
    const l = o?.lines.find((x) => x.poItem === tgt.poItem);
    if (l && (l.qty || 0) < l.pending) {
      if (sheet.value && !sheet.value.pos.includes(o.po)) sheetOnly.value = false;
      l.qty = (l.qty || 0) + 1;
      scanner.value?.showSuccess(`${o.so} · ${res.name} · ${l.qty}/${l.pending}`);
      highlight(o.po);
      return;
    }
  }
  scanner.value?.showError(`${res.name} — ${t("cdi.allCounted")}`);
}

async function post() {
  if (!entries.value.length || busy.value) return;
  if (!armed.value) { armed.value = true; setTimeout(() => { armed.value = false; }, 4000); return; }
  armed.value = false;
  busy.value = true;
  try {
    const res = await apiPost("crossdock_in.receive", { entries: JSON.stringify(entries.value), note: note.value });
    if (res.done?.length) {
      success(t("cdi.posted"), `${res.done.length} ${t("cdi.orders")} · ${res.units} ${t("cdi.units")} · ${t("cdi.reserved")}`);
    }
    if (res.failed?.length) {
      warn(t("cdi.someFailed"), res.failed.map((f) => `${f.po}: ${f.error}`).join(" · "));
    }
    const current = supplier.value;
    const keepSheet = sheet.value;
    await loadBoot();
    await openSupplier(current);
    if (keepSheet) {
      const still = new Set(orders.value.map((o) => o.po));
      sheet.value = { ...keepSheet, pos: keepSheet.pos.filter((p) => still.has(p)) };
    }
  } catch (e) {
    warn(t("cdi.someFailed"), String(e.message || e));
  } finally {
    busy.value = false;
    scanner.value?.refocus();
  }
}

function age(h) {
  if (h == null) return "—";
  if (h < 1) return `${Math.max(1, Math.round(h * 60))}m`;
  if (h < 48) return `${Math.round(h)}h`;
  return `${Math.round(h / 24)}d`;
}
function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }
</script>
