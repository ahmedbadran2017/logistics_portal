<template>
  <div class="max-w-[980px] mx-auto px-4 py-6 space-y-4">
    <header>
      <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cc.title') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cc.intro') }}</p>
    </header>

    <!-- Bin picker -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 space-y-3">
      <div class="flex items-center gap-2 flex-wrap">
        <input
          v-model="binInput"
          list="lp-cc-bins"
          :placeholder="t('cc.binPh')"
          class="flex-1 min-w-[220px] h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] text-stone-800 focus:outline-none focus:ring-2"
          style="--tw-ring-color: var(--accent-400)"
          @keyup.enter="loadSheet"
        />
        <datalist id="lp-cc-bins">
          <option v-for="w in boot?.warehouses || []" :key="w" :value="w" />
        </datalist>
        <button
          class="h-10 px-4 rounded-lg text-[13px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50"
          :disabled="!binValid || loadingSheet"
          @click="loadSheet"
        >{{ loadingSheet ? t('cc.loading') : t('cc.loadBin') }}</button>
      </div>
      <ScanInput v-if="sheet" ref="scanner" :placeholder="t('cc.scanPh')" @scan="onScan" />
    </div>

    <!-- Counting sheet -->
    <div v-if="loadingSheet" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3 space-y-2">
      <div v-for="n in 6" :key="n" class="h-[52px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="sheet" class="bg-white rounded-2xl ring-1 ring-[var(--accent-300)] shadow-md overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center justify-between flex-wrap gap-2">
        <span class="text-[12px] font-semibold text-stone-900">{{ short(sheet.warehouse) }} — {{ sheet.rows.length }} {{ t('consol.items') }}</span>
        <div class="flex items-center gap-2">
          <span class="text-[11px] text-stone-500 tabular-nums">{{ countedCount }}/{{ sheet.rows.length }} {{ t('cc.counted') }}</span>
          <button class="text-[11.5px] font-semibold text-[var(--accent-700)]" @click="fillRest">{{ t('cc.fillBook') }}</button>
        </div>
      </div>
      <div class="divide-y divide-stone-50 max-h-[420px] overflow-y-auto">
        <div v-for="r in sheet.rows" :key="r.itemCode" class="px-4 py-2.5 flex items-center gap-3"
             :class="isDiff(r) ? 'bg-amber-50/60' : ''">
          <img v-if="r.image" :src="r.image" alt="" loading="lazy" @error="hideImg"
               class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
          <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400">
            <Icon name="package" :size="14" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ r.name }}</div>
            <div class="font-mono text-[10.5px] text-stone-400">{{ r.sku || r.itemCode }}</div>
          </div>
          <span class="text-[11px] text-stone-500 tabular-nums">{{ t('cc.book') }} <b class="text-stone-800">{{ r.book }}</b></span>
          <input
            v-model.number="r.counted" type="number" min="0" :placeholder="'—'"
            class="w-16 h-9 text-center text-[14px] font-bold tabular-nums rounded-lg ring-1 focus:outline-none focus:ring-2"
            :class="isDiff(r) ? 'ring-amber-300 text-amber-700' : 'ring-stone-200'"
            style="--tw-ring-color: var(--accent-400)"
          />
          <button class="text-[10.5px] font-semibold text-stone-400 hover:text-stone-700 w-9" @click="r.counted = r.book">= {{ r.book }}</button>
        </div>
      </div>
      <div class="p-3 border-t border-stone-100 space-y-2">
        <input
          v-model="note" :placeholder="t('cc.notePh')" maxlength="80"
          class="w-full h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] text-stone-800 focus:outline-none focus:ring-2"
          style="--tw-ring-color: var(--accent-400)"
        />
        <button
          class="w-full h-11 rounded-xl text-[13.5px] font-semibold flex items-center justify-center gap-2 disabled:opacity-50 transition-colors"
          :class="armed ? 'text-white bg-amber-600 hover:bg-amber-700' : 'text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]'"
          :disabled="submitting || countedCount === 0"
          @click="submitCount"
        >
          <Icon name="check-circle" :size="16" />
          <template v-if="submitting">{{ t('cc.submitting') }}</template>
          <template v-else-if="armed">{{ t('cc.confirmSubmit') }} — {{ diffCount }} {{ t('cc.diffs') }}<span v-if="uncounted"> · {{ uncounted }} {{ t('cc.skipped') }}</span></template>
          <template v-else>{{ t('cc.submitBtn') }}</template>
        </button>
      </div>
    </div>

    <!-- Pending approvals -->
    <div v-if="loadingBoot" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3 space-y-2">
      <div v-for="n in 2" :key="n" class="h-[64px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="pending.length" class="bg-white rounded-xl ring-1 ring-amber-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
        <Icon name="clock" :size="14" class="text-amber-600" />
        <span class="text-[12px] font-semibold text-stone-900">{{ t('cc.pendingTitle') }} ({{ pending.length }})</span>
      </div>
      <div class="divide-y divide-stone-100">
        <div v-for="p in pending" :key="p.name" class="px-4 py-3 space-y-2">
          <div class="flex items-center gap-3 flex-wrap">
            <span class="font-mono text-[11.5px] font-semibold text-stone-800">{{ p.name }}</span>
            <span class="text-[11.5px] text-stone-500">{{ short(p.warehouse) }} · {{ p.lines }} {{ t('cc.diffs') }}</span>
            <span class="text-[11.5px] font-semibold tabular-nums" :class="p.valueDelta < 0 ? 'text-rose-600' : 'text-emerald-600'">
              {{ p.valueDelta > 0 ? '+' : '' }}{{ fmt(p.valueDelta) }} MAD
            </span>
            <span class="text-[10.5px] text-stone-400 flex-1">{{ p.owner }} · {{ p.created }}</span>
            <template v-if="canApprove">
              <button
                class="h-8 px-3 rounded-lg text-[12px] font-semibold transition-colors"
                :class="armedApprove === p.name ? 'text-white bg-emerald-600' : 'text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 hover:bg-emerald-100'"
                :disabled="busyPending"
                @click="approve(p)"
              >{{ armedApprove === p.name ? t('cc.confirmApprove') : t('cc.approve') }}</button>
            </template>
            <button
              class="h-8 px-3 rounded-lg text-[12px] font-semibold transition-colors"
              :class="armedDiscard === p.name ? 'text-white bg-rose-600' : 'text-rose-700 bg-rose-50 ring-1 ring-rose-200 hover:bg-rose-100'"
              :disabled="busyPending"
              @click="discard(p)"
            >{{ armedDiscard === p.name ? t('cc.confirmDiscard') : t('cc.discard') }}</button>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="i in p.items" :key="i.itemCode"
                  class="text-[10.5px] font-mono px-1.5 py-0.5 rounded ring-1 tabular-nums"
                  :class="i.delta < 0 ? 'text-rose-700 bg-rose-50 ring-rose-200' : 'text-emerald-700 bg-emerald-50 ring-emerald-200'">
              {{ i.sku || i.itemCode }} {{ i.book }}→{{ i.counted }}
            </span>
            <span v-if="p.more" class="text-[10.5px] text-stone-400 px-1">+{{ p.more }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const scanner = ref(null);
const boot = ref(null);
const loadingBoot = ref(true);
const binInput = ref("");
const sheet = ref(null);
const loadingSheet = ref(false);
const note = ref("");
const submitting = ref(false);
const armed = ref(false);
const pending = ref([]);
const canApprove = ref(false);
const busyPending = ref(false);
const armedApprove = ref("");
const armedDiscard = ref("");

const binValid = computed(() => (boot.value?.warehouses || []).includes(binInput.value));
const countedCount = computed(() =>
  (sheet.value?.rows || []).filter((r) => r.counted !== "" && r.counted != null).length);
const uncounted = computed(() => (sheet.value?.rows.length || 0) - countedCount.value);
const diffCount = computed(() => (sheet.value?.rows || []).filter(isDiff).length);

function isDiff(r) {
  return r.counted !== "" && r.counted != null && Number(r.counted) !== r.book;
}

onMounted(async () => {
  try {
    boot.value = await api("cycle_count.count_boot");
    pending.value = boot.value.pending || [];
    canApprove.value = !!boot.value.canApprove;
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loadingBoot.value = false;
  }
});

async function loadSheet() {
  if (!binValid.value || loadingSheet.value) return;
  loadingSheet.value = true;
  sheet.value = null;
  armed.value = false;
  try {
    const res = await apiPost("cycle_count.bin_contents", { warehouse: binInput.value });
    sheet.value = { warehouse: res.warehouse,
                    rows: (res.rows || []).map((r) => ({ ...r, counted: "" })) };
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loadingSheet.value = false;
  }
}

async function onScan(raw) {
  const code = String(raw || "").trim();
  if (!code || !sheet.value) return;
  const hit = sheet.value.rows.find((r) => r.sku === code || r.itemCode === code);
  if (hit) {
    hit.counted = (Number(hit.counted) || 0) + 1;
    scanner.value?.showSuccess(`${hit.name} · ${hit.counted}`);
    return;
  }
  // A piece that isn't on the book for this bin — look it up and add a row.
  let res;
  try {
    res = await apiPost("stock_moves.receive_lookup", { code });
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
    return;
  }
  if (!res.ok) { scanner.value?.showError(t("pickm.unknown")); return; }
  const existing = sheet.value.rows.find((r) => r.itemCode === res.itemCode);
  if (existing) {
    existing.counted = (Number(existing.counted) || 0) + 1;
    scanner.value?.showSuccess(`${existing.name} · ${existing.counted}`);
  } else {
    sheet.value.rows.unshift({ ...res, book: 0, counted: 1 });
    scanner.value?.showSuccess(`${res.name} · ${t('cc.newInBin')}`);
  }
}

function fillRest() {
  for (const r of sheet.value?.rows || []) {
    if (r.counted === "" || r.counted == null) r.counted = r.book;
  }
}

async function submitCount() {
  if (!sheet.value || submitting.value || countedCount.value === 0) return;
  if (!armed.value) { armed.value = true; setTimeout(() => { armed.value = false; }, 4000); return; }
  armed.value = false;
  submitting.value = true;
  try {
    const counts = sheet.value.rows
      .filter((r) => r.counted !== "" && r.counted != null)
      .map((r) => ({ item_code: r.itemCode, qty: Number(r.counted) }));
    const res = await apiPost("cycle_count.submit_count", {
      warehouse: sheet.value.warehouse, counts, note: note.value,
    });
    if (res.clean) {
      success(t("cc.cleanTitle"), t("cc.cleanBody"));
    } else {
      success(t("cc.draftTitle"), `${res.draft} · ${res.diffs.length} ${t('cc.diffs')}`);
    }
    sheet.value = null;
    binInput.value = "";
    note.value = "";
    await refreshPending();
  } catch (e) {
    warn(t("cc.submitFail"), String(e.message || e));
  } finally {
    submitting.value = false;
  }
}

async function refreshPending() {
  try {
    const res = await api("cycle_count.pending_counts");
    pending.value = res.pending || [];
    canApprove.value = !!res.canApprove;
  } catch { /* boot already warned */ }
}

async function approve(p) {
  if (armedApprove.value !== p.name) {
    armedApprove.value = p.name;
    setTimeout(() => { if (armedApprove.value === p.name) armedApprove.value = ""; }, 4000);
    return;
  }
  armedApprove.value = "";
  busyPending.value = true;
  try {
    const res = await apiPost("cycle_count.approve_count", { name: p.name });
    success(t("cc.approvedTitle"), `${p.name} · ${fmt(res.differenceAmount)} MAD`);
    await refreshPending();
  } catch (e) {
    warn(t("cc.approveFail"), String(e.message || e));
  } finally {
    busyPending.value = false;
  }
}

async function discard(p) {
  if (armedDiscard.value !== p.name) {
    armedDiscard.value = p.name;
    setTimeout(() => { if (armedDiscard.value === p.name) armedDiscard.value = ""; }, 4000);
    return;
  }
  armedDiscard.value = "";
  busyPending.value = true;
  try {
    await apiPost("cycle_count.discard_count", { name: p.name });
    success(t("cc.discardedTitle"), p.name);
    await refreshPending();
  } catch (e) {
    warn(t("cc.discardFail"), String(e.message || e));
  } finally {
    busyPending.value = false;
  }
}

function short(w) { return String(w || "").replace(" - JM", ""); }
function fmt(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }
</script>
