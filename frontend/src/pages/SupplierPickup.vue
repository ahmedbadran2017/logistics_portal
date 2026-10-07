<template>
  <!-- Supplier pickup: a Cross-dock supplier collects the goods their
       customers sent back. Scan each piece as it is handed over, write who
       collects, one click books the Purchase Receipt returns and prints the
       hand-back slip for both signatures. Backend: api/crossdock_pickup. -->
  <div class="max-w-[1080px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('spk.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[720px]">{{ t('spk.intro') }}</p>
      </div>
      <span v-if="supplier && tickedUnits" class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded-lg px-2.5 h-8 tabular-nums">
        {{ tickedUnits }} {{ t('cdi.units') }}
      </span>
    </header>

    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 sticky top-2 z-10 shadow-sm">
      <ScanInput ref="scanner" :placeholder="t('spk.scanPh')" @scan="onScan" />
      <div class="mt-1.5 text-[11px] text-stone-400">{{ t('spk.scanHint') }}</div>
    </div>

    <!-- Result of the last hand-over -->
    <div v-if="result" class="rounded-2xl ring-1 ring-emerald-200 bg-emerald-50/70 p-4 flex items-center gap-3 flex-wrap">
      <span class="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center"><Icon name="check-circle" :size="17" /></span>
      <div class="flex-1 min-w-0">
        <div class="text-[13.5px] font-semibold text-emerald-900">{{ t('spk.done') }} — {{ result.done.length }} {{ t('spk.lines') }}</div>
        <div v-if="result.failed.length || result.skipped.length" class="text-[12px] text-amber-800">
          {{ result.failed.length + result.skipped.length }} {{ t('spk.notBooked') }}
        </div>
      </div>
      <button v-if="result.done.length" class="h-9 px-3.5 rounded-lg text-[12.5px] font-semibold bg-emerald-600 text-white hover:bg-emerald-700 flex items-center gap-1.5" @click="printSlip(result)">
        <Icon name="printer" :size="14" /> {{ t('spk.printSlip') }}
      </button>
    </div>

    <!-- Who is here -->
    <div v-if="!supplier" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 space-y-3">
      <div class="text-[12.5px] font-semibold text-stone-800">{{ t('spk.suppliers') }}</div>
      <div v-if="loading" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        <div v-for="n in 6" :key="n" class="h-[68px] rounded-xl bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <p v-else-if="!(boot?.suppliers || []).length" class="text-[12.5px] text-stone-400 py-4 text-center">{{ t('spk.none') }}</p>
      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        <button v-for="s in boot.suppliers" :key="s.supplier" @click="openSupplier(s.supplier)"
                class="text-start rounded-xl ring-1 ring-stone-200 bg-white hover:ring-[var(--accent-400)] px-3.5 py-3 transition-shadow hover:shadow-sm">
          <div class="flex items-center gap-2">
            <span class="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center flex-shrink-0"><Icon name="rotate-ccw" :size="15" /></span>
            <span class="text-[13.5px] font-semibold text-stone-900 truncate">{{ s.supplier }}</span>
          </div>
          <div class="mt-1.5 text-[11.5px] text-stone-500 tabular-nums">
            {{ s.units }} {{ t('cdi.units') }} · {{ t('spk.oldest') }} <span :class="s.oldestDays > 14 ? 'text-rose-600 font-semibold' : ''">{{ s.oldestDays }}{{ t('spk.d') }}</span>
          </div>
        </button>
      </div>
    </div>

    <template v-else>
      <div class="bg-white rounded-2xl ring-1 ring-[var(--accent-300)] shadow-sm p-4 space-y-3">
        <div class="flex items-center gap-3 flex-wrap">
          <span class="w-9 h-9 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center"><Icon name="rotate-ccw" :size="17" /></span>
          <div class="flex-1 min-w-0">
            <div class="text-[15px] font-bold text-stone-900 truncate">{{ supplierName }}</div>
            <div class="text-[12px] text-stone-500 tabular-nums">{{ lines.length }} {{ t('spk.lines') }}</div>
          </div>
          <button v-if="canClose" class="h-8 px-2.5 rounded-lg text-[11.5px] font-semibold ring-1"
                  :class="closeMode ? 'bg-stone-900 text-white ring-stone-900' : 'text-stone-700 bg-white ring-stone-200 hover:bg-stone-50'"
                  @click="toggleCloseMode">{{ t('spk.alreadyBack') }}</button>
          <button v-if="!closeMode" class="h-8 px-2.5 rounded-lg text-[11.5px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 hover:bg-emerald-100" @click="tickAll">{{ t('spk.tickAll') }}</button>
          <button class="h-8 px-3 rounded-lg text-[12px] font-semibold text-stone-600 bg-stone-100 hover:bg-stone-200" @click="closeSupplier">{{ t('cdi.change') }}</button>
        </div>
        <div v-if="closeMode" class="rounded-xl bg-stone-50 ring-1 ring-stone-200 p-3 space-y-2">
          <p class="text-[12px] text-stone-600">{{ t('spk.closeIntro') }}</p>
          <input v-model="closeNote" :placeholder="t('spk.closeNotePh')" maxlength="200"
                 class="w-full h-10 ps-3 pe-3 rounded-lg bg-white ring-1 text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--accent-400)]"
                 :class="closeNote.trim() ? 'ring-stone-200' : 'ring-amber-300'" />
        </div>
        <div v-else class="grid sm:grid-cols-3 gap-2">
          <input v-model="collector" :placeholder="t('spk.collectorPh')" maxlength="80"
                 class="h-10 ps-3 pe-3 rounded-lg bg-white ring-1 text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--accent-400)]"
                 :class="collector.trim() ? 'ring-stone-200' : 'ring-amber-300'" />
          <input v-model="collectorId" :placeholder="t('spk.idPh')" maxlength="40"
                 class="h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--accent-400)]" />
          <input v-model="note" :placeholder="t('spk.notePh')" maxlength="120"
                 class="h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--accent-400)]" />
        </div>
      </div>

      <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 shadow-sm overflow-hidden">
        <div class="divide-y divide-stone-50">
          <div v-for="l in lines" :key="l.key" :id="'spk-' + l.key" class="px-4 py-2.5 flex items-center gap-3"
               :class="[closeMode ? (l.closing ? 'bg-stone-100' : '') : !l.bookable ? 'bg-stone-50/80' : l.ticked ? 'bg-emerald-50/50' : '', flash === l.key ? 'ring-2 ring-inset ring-[var(--accent-400)]' : '']">
            <input v-if="closeMode" type="checkbox" class="w-4 h-4 rounded accent-stone-900" v-model="l.closing" />
            <input v-else type="checkbox" class="w-4 h-4 rounded" :disabled="!l.bookable" v-model="l.ticked" />
            <img v-if="l.image" :src="l.image" alt="" loading="lazy" @error="hideImg"
                 class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
            <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="14" /></span>
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ l.name }}</div>
              <div class="text-[10.5px] text-stone-400 truncate"><span class="font-mono">{{ l.sku || l.itemCode }}</span> · {{ l.so }} · {{ t('spk.back') }} {{ l.returnedOn }}</div>
            </div>
            <span v-if="!l.returnable" class="text-[10.5px] font-semibold rounded px-1.5 py-0.5 bg-stone-200 text-stone-600 whitespace-nowrap">{{ t('spk.noReceipt') }}</span>
            <span v-else-if="!l.source" class="text-[10.5px] font-semibold rounded px-1.5 py-0.5 bg-amber-100 text-amber-800 whitespace-nowrap"
                  :title="l.elsewhere ? t('spk.elsewhere') + ' ' + l.elsewhere : ''">{{ t('spk.noStock') }}<template v-if="l.elsewhere"> · {{ short(l.elsewhere) }}</template></span>
            <span v-else class="text-[10.5px] font-mono rounded px-1.5 py-0.5 bg-stone-100 text-stone-600 whitespace-nowrap">{{ short(l.source) }}</span>
            <span class="text-[13px] font-bold tabular-nums w-8 text-end">×{{ l.qty }}</span>
          </div>
          <p v-if="!lines.length" class="px-4 py-10 text-center text-[12.5px] text-stone-400">{{ t('spk.none') }}</p>
        </div>
      </div>

      <div v-if="lines.length && closeMode" class="sticky bottom-3 z-10">
        <button class="w-full h-12 rounded-xl text-[14px] font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg transition-colors"
                :class="closeArmed ? 'bg-amber-600 hover:bg-amber-700' : 'bg-stone-900 hover:bg-stone-800'"
                :disabled="busy || !closingUnits || !closeNote.trim()" @click="postClose">
          <Icon name="check-circle" :size="17" />
          <template v-if="busy">{{ t('cdi.posting') }}</template>
          <template v-else-if="!closeNote.trim()">{{ t('spk.closeNeedNote') }}</template>
          <template v-else-if="closeArmed">{{ t('cdi.confirm') }} — {{ closingUnits }} {{ t('cdi.units') }}</template>
          <template v-else>{{ t('spk.closeBtn') }} · {{ closingUnits }} {{ t('cdi.units') }}</template>
        </button>
      </div>
      <div v-else-if="lines.length" class="sticky bottom-3 z-10">
        <button class="w-full h-12 rounded-xl text-[14px] font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg transition-colors"
                :class="armed ? 'bg-amber-600 hover:bg-amber-700' : 'bg-emerald-600 hover:bg-emerald-700'"
                :disabled="busy || !tickedUnits || !collector.trim()" @click="post">
          <Icon name="hand" :size="17" />
          <template v-if="busy">{{ t('cdi.posting') }}</template>
          <template v-else-if="armed">{{ t('cdi.confirm') }} — {{ tickedUnits }} {{ t('cdi.units') }} → {{ collector }}</template>
          <template v-else-if="!collector.trim()">{{ t('spk.needCollector') }}</template>
          <template v-else>{{ t('spk.handOver') }} · {{ tickedUnits }} {{ t('cdi.units') }}</template>
        </button>
      </div>

      <!-- What this supplier already got back without this screen: a return
           booked on another order's receipt, or a manager's close. -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <button class="w-full px-4 py-2.5 flex items-center gap-2 text-start" @click="toggleBack">
          <span class="text-[12px] font-semibold text-stone-900 flex-1">{{ t('spk.backTitle') }}</span>
          <span v-if="back" class="text-[11px] text-stone-400 tabular-nums">{{ back.length }}</span>
          <Icon :name="showBack ? 'chevron-up' : 'chevron-down'" :size="14" class="text-stone-400" />
        </button>
        <div v-if="showBack" class="border-t border-stone-100 divide-y divide-stone-50 max-h-[360px] overflow-y-auto">
          <p v-if="!back" class="px-4 py-4 text-[12px] text-stone-400">{{ t('common.loading') }}</p>
          <p v-else-if="!back.length" class="px-4 py-4 text-[12px] text-stone-400">{{ t('spk.backEmpty') }}</p>
          <div v-for="b in back || []" :key="b.so + b.itemCode" class="px-4 py-2 flex items-start gap-3 text-[12px]">
            <div class="min-w-0 flex-1">
              <div class="text-stone-800 truncate">{{ b.name }} <span class="text-stone-400 tabular-nums">×{{ b.qty }}</span></div>
              <div class="text-[10.5px] text-stone-400"><span class="font-mono">{{ b.sku || b.itemCode }}</span> · {{ b.so }} · {{ t('spk.back') }} {{ b.returnedOn }}</div>
              <div v-for="x in b.by" :key="(x.manual || x.doc) + x.so" class="text-[11px] text-stone-500">
                <template v-if="x.manual">{{ t('spk.byHand') }} · {{ t('spk.act_' + x.action) }}<span v-if="x.doc && x.doc !== x.manual" class="font-mono"> {{ x.doc }}</span> · {{ x.note }} · {{ x.date }}</template>
                <template v-else><span class="font-mono">{{ x.doc }}</span> {{ x.date }}<span v-if="x.so !== b.so"> · {{ t('spk.onOther') }} {{ x.so }}</span></template>
              </div>
            </div>
            <button v-for="x in b.by.filter((y) => y.manual && !['returned', 'issued'].includes(y.action))" :key="'u' + x.manual" v-show="canClose"
                    class="h-7 px-2 rounded-lg text-[11px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50 disabled:opacity-50"
                    :disabled="busy" @click="doReopen(x.manual)">{{ t('spk.reopen') }}</button>
          </div>
        </div>
      </div>
    </template>

    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100"><span class="text-[12px] font-semibold text-stone-900">{{ t('spk.recent') }}</span></div>
      <div class="divide-y divide-stone-50 max-h-[300px] overflow-y-auto">
        <p v-if="!(boot?.recent || []).length" class="px-4 py-6 text-center text-[12.5px] text-stone-400">{{ t('spk.recentEmpty') }}</p>
        <div v-for="r in boot?.recent || []" :key="r.receipt" class="px-4 py-2 flex items-center gap-3 text-[12px]">
          <span class="text-[10.5px] text-stone-400 tabular-nums w-[74px] flex-shrink-0">{{ r.time }}</span>
          <span class="text-stone-800 font-medium truncate max-w-[160px]">{{ r.supplier }}</span>
          <span class="tabular-nums text-stone-600">{{ r.units }} {{ t('cdi.units') }}</span>
          <span class="text-stone-500 truncate flex-1">→ {{ r.to }}</span>
          <span class="font-mono text-[11px] text-stone-400">{{ r.receipt }}</span>
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

const scanner = ref(null);
const boot = ref(null);
const loading = ref(true);
const supplier = ref("");
const supplierName = ref("");
const lines = ref([]);
const collector = ref("");
const collectorId = ref("");
const note = ref("");
const busy = ref(false);
const armed = ref(false);
const flash = ref("");
const result = ref(null);

const tickedUnits = computed(() => lines.value.filter((l) => l.ticked).reduce((s, l) => s + l.qty, 0));

// Managers close lines that already went back with no document at all.
const canClose = ref(false);
const closeMode = ref(false);
const closeNote = ref("");
const closeArmed = ref(false);
const closingUnits = computed(() => lines.value.filter((l) => l.closing).reduce((s, l) => s + l.qty, 0));
const back = ref(null);
const showBack = ref(false);
function toggleCloseMode() {
  closeMode.value = !closeMode.value;
  closeArmed.value = false;
  lines.value.forEach((l) => { l.closing = false; });
}
async function loadBack() {
  try { back.value = (await api("crossdock_pickup.handed_back", { supplier: supplier.value })).lines || []; }
  catch (e) { back.value = []; warn(t("mv.loadFail"), String(e.message || e)); }
}
function toggleBack() {
  showBack.value = !showBack.value;
  if (showBack.value && back.value === null) loadBack();
}
async function postClose() {
  if (!closingUnits.value || !closeNote.value.trim() || busy.value) return;
  if (!closeArmed.value) { closeArmed.value = true; setTimeout(() => { closeArmed.value = false; }, 4000); return; }
  closeArmed.value = false;
  busy.value = true;
  try {
    const picked = lines.value.filter((l) => l.closing).map((l) => ({ so: l.so, item_code: l.itemCode, qty: l.qty }));
    const res = await apiPost("crossdock_pickup.close_lines", { supplier: supplier.value, lines: JSON.stringify(picked), note: closeNote.value });
    if (res.done?.length) success(t("spk.closedOk"), res.done.map((d) => `${d.so} · ${t("spk.act_" + d.action)}${d.doc ? " " + d.doc : ""}`).join(" · "));
    if (res.skipped?.length) warn(t("spk.notClosed"), res.skipped.map((s) => `${s.so}: ${t("spk.cr_" + s.reason)}${s.bin ? " " + short(s.bin) : ""}${s.error ? " — " + s.error : ""}`).join(" · "));
    const cur = supplier.value;
    closeNote.value = "";
    await loadBoot();
    await openSupplier(cur);
    back.value = null;
    if (showBack.value) loadBack();
  } catch (e) {
    warn(t("spk.notClosed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}
async function doReopen(name) {
  busy.value = true;
  try {
    await apiPost("crossdock_pickup.reopen", { name });
    const cur = supplier.value;
    await openSupplier(cur);
    await loadBack();
  } catch (e) { warn(t("spk.notClosed"), String(e.message || e)); }
  finally { busy.value = false; }
}

async function loadBoot() {
  try { boot.value = await api("crossdock_pickup.boot"); }
  catch (e) { warn(t("mv.loadFail"), String(e.message || e)); }
  finally { loading.value = false; }
}
onMounted(loadBoot);

async function openSupplier(name) {
  loading.value = true;
  try {
    const r = await api("crossdock_pickup.supplier_lines", { supplier: name });
    if (name !== supplier.value) { back.value = null; showBack.value = false; closeMode.value = false; }
    supplier.value = name;
    supplierName.value = r.supplierName || name;
    canClose.value = !!r.canClose;
    lines.value = (r.lines || []).map((l) => ({ ...l, key: `${l.so}|${l.itemCode}`,
      bookable: l.returnable && !!l.source, ticked: false, closing: false }));
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
    setTimeout(() => scanner.value?.refocus(), 50);
  }
}
function closeSupplier() {
  closeMode.value = false; back.value = null; showBack.value = false;
  supplier.value = ""; lines.value = []; collector.value = ""; collectorId.value = ""; note.value = "";
  setTimeout(() => scanner.value?.refocus(), 50);
}
function tickAll() { lines.value.forEach((l) => { if (l.bookable) l.ticked = true; }); }

async function onScan(raw) {
  const code = String(raw || "").trim();
  if (!code) return;
  let res;
  try { res = await apiPost("crossdock_pickup.resolve", { code, supplier: supplier.value || "" }); }
  catch (e) { scanner.value?.showError(String(e.message || e)); return; }
  if (!res.ok) {
    scanner.value?.showError(res.reason === "not_waiting" ? `${res.name} — ${t("spk.notWaiting")}` : t("cdi.unknown"));
    return;
  }
  if (res.supplier !== supplier.value) await openSupplier(res.supplier);
  const l = lines.value.find((x) => x.itemCode === res.itemCode && x.bookable && !x.ticked);
  if (!l) { scanner.value?.showError(`${res.name} — ${t("spk.allTicked")}`); return; }
  l.ticked = true;
  flash.value = l.key;
  nextTick(() => document.getElementById("spk-" + l.key)?.scrollIntoView({ behavior: "smooth", block: "center" }));
  setTimeout(() => { if (flash.value === l.key) flash.value = ""; }, 1500);
  scanner.value?.showSuccess(`${res.name} · ${l.so}`);
}

async function post() {
  if (!tickedUnits.value || !collector.value.trim() || busy.value) return;
  if (!armed.value) { armed.value = true; setTimeout(() => { armed.value = false; }, 4000); return; }
  armed.value = false;
  busy.value = true;
  try {
    const picked = lines.value.filter((l) => l.ticked).map((l) => ({ so: l.so, item_code: l.itemCode, qty: l.qty }));
    const res = await apiPost("crossdock_pickup.hand_over", {
      supplier: supplier.value, lines: JSON.stringify(picked),
      collector: collector.value, collector_id: collectorId.value, note: note.value,
    });
    result.value = res;
    if (res.done?.length) success(t("spk.done"), `${res.done.length} ${t("spk.lines")} → ${res.collector}`);
    if (res.failed?.length || res.skipped?.length) warn(t("spk.notBooked"), [...res.failed.map((f) => `${f.so}: ${f.error}`), ...res.skipped.map((s) => `${s.so}: ${t("spk.r_" + s.reason)}`)].join(" · "));
    const cur = supplier.value;
    await loadBoot();
    await openSupplier(cur);
  } catch (e) {
    warn(t("spk.notBooked"), String(e.message || e));
  } finally {
    busy.value = false;
    scanner.value?.refocus();
  }
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function printSlip(r) {
  const w = window.open("", "_blank");
  if (!w) return;
  const rows = r.done.map((d, i) => `<tr><td>${i + 1}</td><td>${esc(d.so)}</td><td>${esc(d.name)}<div class="sku">${esc(d.sku)}</div></td><td class="c">${d.qty}</td><td class="m">${esc(d.return)}</td></tr>`).join("");
  const units = r.done.reduce((s, d) => s + d.qty, 0);
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${esc(t("spk.slipTitle"))}</title>
<style>@page{size:A4;margin:14mm}body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1c1917}h1{font-size:20px;margin:0}
.muted{color:#78716c;font-size:12px}table{width:100%;border-collapse:collapse;margin-top:16px;font-size:12px}th{text-align:left;font-size:10px;text-transform:uppercase;color:#57534e;border-bottom:1px solid #d6d3d1;padding:6px}
td{border-bottom:1px solid #e7e5e4;padding:6px;vertical-align:top}.sku{font-family:monospace;color:#78716c;font-size:11px}.c{text-align:center;font-weight:700}.m{font-family:monospace;font-size:11px;color:#57534e}
.sign{display:flex;gap:24px;margin-top:36px}.sign div{flex:1;border-top:1px solid #1c1917;padding-top:6px;font-size:11px;color:#57534e}.tot{margin-top:10px;font-weight:600}</style></head><body>
<h1>${esc(t("spk.slipTitle"))}</h1>
<div class="muted">JUSTYOL · ${esc(r.supplierName)} · ${esc(r.at)}</div>
<div class="muted">${esc(t("spk.collectedBy"))}: <b>${esc(r.collector)}</b>${r.collectorId ? ` · ID ${esc(r.collectorId)}` : ""}${r.note ? ` · ${esc(r.note)}` : ""}</div>
<table><thead><tr><th>#</th><th>${esc(t("spk.colOrder"))}</th><th>${esc(t("spk.colProduct"))}</th><th>${esc(t("spk.colQty"))}</th><th>${esc(t("spk.colRef"))}</th></tr></thead><tbody>${rows}</tbody></table>
<div class="tot">${units} ${esc(t("cdi.units"))}</div>
<div class="sign"><div>${esc(t("spk.signSupplier"))}</div><div>${esc(t("spk.signWarehouse"))}</div></div>
<script>window.onload=function(){setTimeout(function(){window.print()},150)}<\/script></body></html>`);
  w.document.close();
}
function short(w) { return String(w || "").replace(" - JM", ""); }
function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }
</script>
