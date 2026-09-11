<template>
  <div class="max-w-[980px] mx-auto px-4 py-6 space-y-4">
    <header>
      <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cc.title') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cc.intro') }}</p>
    </header>

    <!-- Shelves a picker found empty that the ledger still calls stocked. This
         is the backlog the old order-level cool-down was hiding: the order was
         punished for 24h and the lying Bin was never corrected. Ranked by the
         orders each shelf is holding up, so the first row is the most
         expensive count in the building. -->
    <div v-if="empties && empties.rows.length" class="bg-white rounded-2xl ring-1 ring-amber-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-amber-100 flex items-center gap-2 flex-wrap bg-amber-50/50">
        <Icon name="alert-triangle" :size="14" class="text-amber-600" />
        <span class="text-[12px] font-semibold text-stone-900">{{ t('cc.emptyTitle') }}</span>
        <span class="text-[11px] text-stone-500">
          {{ t('cc.emptySub').replace('{n}', empties.items).replace('{o}', empties.orders) }}
        </span>
      </div>
      <div class="divide-y divide-stone-100">
        <button
          v-for="r in empties.rows" :key="r.item + r.warehouse"
          class="w-full px-4 py-2 flex items-center gap-3 text-start hover:bg-stone-50 transition-colors"
          @click="binInput = r.warehouse; loadSheet()"
        >
          <span class="min-w-0 flex-1">
            <span class="block text-[12.5px] font-medium text-stone-800 truncate">{{ r.name }}</span>
            <span class="block font-mono text-[10.5px] text-stone-400">{{ r.sku || r.item }} · {{ r.warehouse }}</span>
          </span>
          <span class="text-[11px] text-amber-700 bg-amber-50 ring-1 ring-amber-200/70 rounded-md px-1.5 py-px flex-shrink-0">
            {{ t('cc.emptyLedger').replace('{n}', r.ledger) }}
          </span>
          <span v-if="r.orders" class="text-[11.5px] font-bold tabular-nums text-stone-700 flex-shrink-0">
            {{ r.orders }} {{ t('ordersPg.blOrders') }}
          </span>
        </button>
      </div>
    </div>

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

    <!-- Counting sheet — PDA-first: thumb-size steppers, loud states,
         and the relocation flow (a short count whose pieces sit on another
         shelf is a MOVE, never a write-off). -->
    <div v-if="loadingSheet" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3 space-y-2">
      <div v-for="n in 6" :key="n" class="h-[64px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="sheet" class="bg-white rounded-2xl ring-1 ring-[var(--accent-300)] shadow-md overflow-hidden">
      <div class="px-4 pt-3 pb-2 border-b border-stone-100 sticky top-0 bg-white/95 backdrop-blur-sm z-10 space-y-2">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <span class="text-[14px] font-bold text-stone-900">{{ short(sheet.warehouse) }}</span>
          <span class="text-[12px] text-stone-500 tabular-nums font-semibold">{{ countedCount }}/{{ sheet.rows.length }} {{ t('cc.counted') }}</span>
        </div>
        <div class="h-2 rounded-full bg-stone-100 overflow-hidden">
          <div class="h-full rounded-full transition-all duration-300"
               :style="{ width: (sheet.rows.length ? Math.round(countedCount * 100 / sheet.rows.length) : 0) + '%',
                         background: 'var(--accent-500)' }" />
        </div>
        <div class="flex items-center gap-1.5">
          <button v-for="f in [['all', t('cc.fAll')], ['rest', t('cc.fRest')], ['diff', t('cc.fDiff')]]" :key="f[0]"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold transition-colors"
                  :class="filter === f[0] ? 'bg-stone-900 text-white' : 'bg-stone-100 text-stone-500'"
                  @click="filter = f[0]">{{ f[1] }}</button>
          <button class="ms-auto text-[11.5px] font-semibold text-[var(--accent-700)]" @click="fillRest">{{ t('cc.fillBook') }}</button>
        </div>
      </div>
      <div class="divide-y divide-stone-50 max-h-[52vh] overflow-y-auto">
        <div v-for="r in visibleRows" :key="r.itemCode" class="px-3 py-3"
             :class="rowDone(r) ? 'bg-emerald-50/50' : isDiff(r) ? 'bg-amber-50/60' : ''">
          <div class="flex items-center gap-2.5">
            <img v-if="r.image" :src="r.image" alt="" loading="lazy" @error="hideImg"
                 class="w-12 h-12 rounded-xl object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
            <span v-else class="w-12 h-12 rounded-xl bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400">
              <Icon name="package" :size="16" />
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-semibold text-stone-900 leading-tight line-clamp-2">{{ r.name }}</div>
              <div class="font-mono text-[10.5px] text-stone-400 mt-0.5">{{ r.sku || r.itemCode }}
                <span class="ms-1 text-stone-500">{{ t('cc.book') }} <b class="text-stone-800">{{ r.book }}</b></span>
              </div>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <button class="w-11 h-11 rounded-xl bg-stone-100 text-stone-700 text-[20px] font-bold active:bg-stone-200 disabled:opacity-30"
                      :disabled="!Number(r.counted)" @click="bump(r, -1)">−</button>
              <input v-model.number="r.counted" type="number" min="0" inputmode="numeric" :placeholder="'—'"
                     class="w-14 h-11 text-center text-[18px] font-extrabold tabular-nums rounded-xl ring-1 focus:outline-none focus:ring-2"
                     :class="rowDone(r) ? 'ring-emerald-300 text-emerald-700' : isDiff(r) ? 'ring-amber-300 text-amber-700' : 'ring-stone-200'"
                     style="--tw-ring-color: var(--accent-400)" />
              <button class="w-11 h-11 rounded-xl text-white text-[20px] font-bold active:opacity-80"
                      :style="{ background: 'var(--accent-600)' }" @click="bump(r, 1)">+</button>
            </div>
          </div>
          <!-- The verdict line: matched, short, or extra — and the honest way out -->
          <div v-if="isDiff(r) || rowMoves(r).length" class="mt-2 ms-[58px] space-y-1.5">
            <div class="flex items-center gap-2 flex-wrap">
              <span v-if="effDelta(r) === 0" class="text-[11px] font-bold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded-md px-2 py-0.5">
                ✓ {{ t('cc.afterMoveOk') }}</span>
              <span v-else-if="effDelta(r) < 0" class="text-[11px] font-bold text-amber-800 bg-amber-100/70 ring-1 ring-amber-200 rounded-md px-2 py-0.5 tabular-nums">
                {{ t('cc.missingN').replace('{n}', String(-effDelta(r))) }}</span>
              <span v-else class="text-[11px] font-bold text-sky-800 bg-sky-50 ring-1 ring-sky-200 rounded-md px-2 py-0.5 tabular-nums">
                {{ t('cc.extraN').replace('{n}', String(effDelta(r))) }}</span>
              <button v-if="effDelta(r) !== 0" class="h-8 px-2.5 rounded-lg text-[11.5px] font-bold text-white bg-stone-800 active:bg-stone-900"
                      @click="openMove(r)">
                <Icon name="move" :size="11" class="inline -mt-px me-1" />
                {{ effDelta(r) < 0 ? t('cc.moveShortBtn') : t('cc.moveSurplusBtn') }}
              </button>
            </div>
            <div v-for="(m, mi) in rowMoves(r)" :key="mi" class="flex items-center gap-1.5">
              <span class="text-[11px] font-semibold text-violet-800 bg-violet-50 ring-1 ring-violet-200 rounded-md px-2 py-0.5 tabular-nums">
                {{ m.dir === 'out' ? '→' : '←' }} {{ m.qty }} · {{ short(m.other) }}
              </span>
              <button class="w-7 h-7 rounded-md text-stone-400 hover:text-rose-600 text-[13px]" @click="removeMove(m)">✕</button>
            </div>
            <!-- the shelf picker: where the pieces actually are / came from -->
            <div v-if="moveFor === r.itemCode" class="rounded-xl bg-stone-50 ring-1 ring-stone-200 p-2.5 space-y-2" @click.stop>
              <div class="text-[11.5px] font-bold text-stone-700">
                {{ effDelta(r) < 0 ? t('cc.moveTitleShort') : t('cc.moveTitleIn') }}
              </div>
              <div v-if="locsLoading" class="text-[11px] text-stone-400">…</div>
              <div v-else-if="locs.length" class="flex flex-wrap gap-1.5">
                <button v-for="l in locs.filter((x) => x.warehouse !== sheet.warehouse)" :key="l.warehouse"
                        class="h-9 px-3 rounded-lg text-[12px] font-bold ring-1 transition-colors"
                        :class="moveOther === l.warehouse ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-700 ring-stone-200'"
                        @click="moveOther = l.warehouse">
                  {{ short(l.warehouse) }} <span class="opacity-60 tabular-nums">· {{ l.qty }}</span>
                </button>
              </div>
              <input v-model="moveOther" list="lp-cc-bins" :placeholder="t('cc.moveOtherPh')"
                     class="w-full h-10 ps-3 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] focus:outline-none focus:ring-2"
                     style="--tw-ring-color: var(--accent-400)" />
              <div class="flex items-center gap-2">
                <button class="w-10 h-10 rounded-lg bg-stone-200 text-stone-700 text-[18px] font-bold" @click="moveQty = Math.max(1, moveQty - 1)">−</button>
                <span class="w-10 text-center text-[17px] font-extrabold tabular-nums">{{ moveQty }}</span>
                <button class="w-10 h-10 rounded-lg bg-stone-200 text-stone-700 text-[18px] font-bold" @click="moveQty = Math.min(Math.abs(effDelta(r)), moveQty + 1)">+</button>
                <button class="ms-auto h-10 px-4 rounded-lg text-[12.5px] font-bold text-white disabled:opacity-40"
                        :style="{ background: 'var(--accent-600)' }"
                        :disabled="!moveOther || !moveQty" @click="confirmMove(r)">{{ t('cc.moveConfirm') }}</button>
                <button class="h-10 px-2 text-[12px] text-stone-400" @click="moveFor = ''">✕</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="p-3 border-t border-stone-100 space-y-2 sticky bottom-0 bg-white">
        <input
          v-model="note" :placeholder="t('cc.notePh')" maxlength="80"
          class="w-full h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] text-stone-800 focus:outline-none focus:ring-2"
          style="--tw-ring-color: var(--accent-400)"
        />
        <button
          class="w-full h-12 rounded-xl text-[14px] font-bold flex items-center justify-center gap-2 disabled:opacity-50 transition-colors"
          :class="armed ? 'text-white bg-amber-600 hover:bg-amber-700' : 'text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]'"
          :disabled="submitting || countedCount === 0"
          @click="submitCount"
        >
          <Icon name="check-circle" :size="17" />
          <template v-if="submitting">{{ t('cc.submitting') }}</template>
          <template v-else-if="armed">{{ t('cc.confirmSubmit') }} — {{ diffCount }} {{ t('cc.diffs') }}<span v-if="moves.length"> · {{ moves.length }} {{ t('cc.movesN') }}</span><span v-if="uncounted"> · {{ uncounted }} {{ t('cc.skipped') }}</span></template>
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
import { useRoute } from "vue-router";
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
const filter = ref("all");
const visibleRows = computed(() => {
  const rows = sheet.value?.rows || [];
  if (filter.value === "rest") return rows.filter((r) => r.counted === "" || r.counted == null);
  if (filter.value === "diff") return rows.filter((r) => isDiff(r) || rowMoves(r).length);
  return rows;
});
function bump(r, d) {
  const v = Math.max(0, (Number(r.counted) || 0) + d);
  r.counted = v;
}
function rowDone(r) {
  return r.counted !== "" && r.counted != null && effDelta(r) === 0;
}

// ── relocations: the honest record when the pieces exist on ANOTHER shelf.
// A move changes what this shelf SHOULD hold, so the residual difference is
// computed against the post-move book — a fully-relocated shortage reconciles
// to nothing.
const moves = ref([]);            // {item_code, qty, dir: out|in, other}
const moveFor = ref("");
const moveOther = ref("");
const moveQty = ref(1);
const locs = ref([]);
const locsLoading = ref(false);
function rowMoves(r) { return moves.value.filter((m) => m.item_code === r.itemCode); }
function effDelta(r) {
  if (r.counted === "" || r.counted == null) return 0;
  let book = r.book;
  for (const m of rowMoves(r)) book += m.dir === "in" ? m.qty : -m.qty;
  return Number(r.counted) - book;
}
async function openMove(r) {
  moveFor.value = r.itemCode;
  moveOther.value = "";
  moveQty.value = Math.max(1, Math.abs(effDelta(r)));
  locs.value = [];
  locsLoading.value = true;
  try {
    const res = await apiPost("cycle_count.item_locations", { item_code: r.itemCode });
    locs.value = res.locations || [];
  } catch { locs.value = []; }
  locsLoading.value = false;
}
function confirmMove(r) {
  const other = (moveOther.value || "").trim();
  if (!other || !moveQty.value) return;
  moves.value.push({
    item_code: r.itemCode, qty: Number(moveQty.value),
    dir: effDelta(r) < 0 ? "out" : "in", other,
  });
  moveFor.value = "";
}
function removeMove(m) {
  const i = moves.value.indexOf(m);
  if (i >= 0) moves.value.splice(i, 1);
}
const countedCount = computed(() =>
  (sheet.value?.rows || []).filter((r) => r.counted !== "" && r.counted != null).length);
const uncounted = computed(() => (sheet.value?.rows.length || 0) - countedCount.value);
const diffCount = computed(() =>
  (sheet.value?.rows || []).filter((r) => r.counted !== "" && r.counted != null
    && effDelta(r) !== 0).length);

function isDiff(r) {
  return r.counted !== "" && r.counted != null && Number(r.counted) !== r.book;
}

// Shelves a picker reported empty while the ledger still claims stock. A
// failed load hides the panel rather than breaking the page — counting a bin
// by hand must keep working whether or not this list can be built.
const empties = ref(null);
async function loadEmpties() {
  try { empties.value = await api("short_shelf.count_worklist"); }
  catch (e) { empties.value = null; }
}

// Arriving from the out-of-stock worklist with a bin already named: the row
// said which shelf a picker found empty, so open that count instead of making
// someone retype it.
const route = useRoute();

onMounted(async () => {
  loadEmpties();
  const q = (route.query.bin || "").toString().trim();
  if (q) {
    binInput.value = q.endsWith(" - JM") ? q : `${q} - JM`;
  }
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
  moves.value = [];
  moveFor.value = "";
  filter.value = "all";
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
      moves: moves.value,
    });
    if (res.clean) {
      success(t("cc.cleanTitle"), t("cc.cleanBody"));
    } else {
      success(t("cc.draftTitle"), `${res.draft} · ${res.diffs.length} ${t('cc.diffs')}`);
    }
    if (res.moved) success(t("cc.movedTitle"), res.moved);
    sheet.value = null;
    binInput.value = "";
    note.value = "";
    moves.value = [];
    moveFor.value = "";
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
