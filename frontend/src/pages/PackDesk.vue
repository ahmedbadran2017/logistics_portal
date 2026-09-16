<template>
  <!-- Packing desk — a PDA screen, not a dashboard. One question at a time:
       scan the label, then scan the pieces. Everything is thumb-sized and
       readable at arm's length over a table. -->
  <div class="min-h-screen bg-stone-50 flex flex-col">
    <!-- scan bar: always at the top, always focused -->
    <div class="sticky top-0 z-20 bg-white border-b border-stone-200 px-4 pt-3 pb-2">
      <div class="flex items-center gap-2 mb-2">
        <h1 class="text-[15px] font-bold text-stone-900 flex items-center gap-1.5">
          <Icon name="package-check" :size="17" />{{ t("pk.title") }}
        </h1>
        <span v-if="board" class="ms-auto text-[12px] font-semibold text-stone-500 tabular-nums">
          {{ board.mine.parcels }} {{ t("pk.today") }}
        </span>
        <button class="w-9 h-9 rounded-xl bg-stone-100 text-stone-500 flex items-center justify-center"
                :aria-label="t('pk.waiting')" @click="showQueue = !showQueue">
          <Icon name="list-checks" :size="16" />
          <span v-if="board?.waitingN" class="absolute translate-x-3 -translate-y-3 min-w-[18px] h-[18px] px-1 rounded-full bg-amber-500 text-white text-[10px] font-bold flex items-center justify-center tabular-nums">{{ board.waitingN }}</span>
        </button>
      </div>
      <ScanInput ref="scanner" :placeholder="parcel ? t('pk.scanPiece') : t('pk.scanAwb')" @scan="onScan" />
    </div>

    <!-- waiting list (tap the badge) -->
    <div v-if="showQueue" class="px-4 py-3 bg-white border-b border-stone-200">
      <div class="text-[12px] font-semibold text-stone-500 mb-2">{{ t("pk.waiting") }} · {{ board?.waitingN || 0 }}</div>
      <div v-if="!board?.waiting?.length" class="text-[13px] text-emerald-700 py-2">{{ t("pk.queueEmpty") }}</div>
      <div v-else class="space-y-1.5 max-h-[40vh] overflow-y-auto">
        <button v-for="w in board.waiting" :key="w.order"
                class="w-full min-h-[52px] px-3 rounded-xl bg-stone-50 ring-1 ring-stone-200 flex items-center gap-3 text-start active:bg-stone-100"
                @click="openOrder(w.order)">
          <span class="w-9 h-9 rounded-lg bg-white ring-1 ring-stone-200 flex items-center justify-center text-stone-500 flex-shrink-0 text-[13px] font-bold tabular-nums">{{ w.pieces }}</span>
          <span class="min-w-0 flex-1">
            <span class="block text-[13px] font-semibold text-stone-900 truncate" dir="auto">{{ w.customer }}</span>
            <span class="block font-mono text-[11px] text-stone-400">{{ w.awb || w.order }}</span>
          </span>
          <Icon name="chevron-right" :size="16" class="text-stone-300 rtl:-scale-x-100" />
        </button>
      </div>
    </div>

    <!-- nothing open: the desk is idle -->
    <div v-if="!parcel && !showQueue" class="flex-1 flex flex-col items-center justify-center px-8 text-center">
      <span class="w-16 h-16 rounded-2xl bg-white ring-1 ring-stone-200 flex items-center justify-center text-stone-300 mb-3">
        <Icon name="scan-line" :size="28" />
      </span>
      <div class="text-[14px] font-semibold text-stone-700">{{ t("pk.idleTitle") }}</div>
      <div class="text-[12.5px] text-stone-400 mt-1">{{ t("pk.idleHint") }}</div>
      <div v-if="board" class="mt-6 flex items-center gap-6">
        <div class="text-center">
          <div class="text-[26px] font-bold text-stone-900 tabular-nums leading-none">{{ board.mine.parcels }}</div>
          <div class="text-[11px] text-stone-400 mt-1">{{ t("pk.myParcels") }}</div>
        </div>
        <div class="text-center">
          <div class="text-[26px] font-bold text-stone-900 tabular-nums leading-none">{{ board.mine.pieces }}</div>
          <div class="text-[11px] text-stone-400 mt-1">{{ t("pk.myPieces") }}</div>
        </div>
      </div>
    </div>

    <!-- the open parcel -->
    <div v-else-if="parcel" class="flex-1 pb-32">
      <!-- who it is for -->
      <div class="px-4 py-3 bg-white border-b border-stone-200">
        <div class="flex items-start gap-3">
          <div class="min-w-0 flex-1">
            <div class="text-[15px] font-bold text-stone-900 truncate" dir="auto">{{ parcel.customer }}</div>
            <div class="text-[12px] text-stone-500 flex items-center gap-1.5 mt-0.5">
              <Icon name="map-pin" :size="12" />{{ parcel.city }}
            </div>
            <div class="font-mono text-[11.5px] text-stone-400 mt-0.5">{{ parcel.awb || parcel.order }}</div>
          </div>
          <button class="w-10 h-10 rounded-xl bg-stone-100 text-stone-500 flex items-center justify-center flex-shrink-0"
                  :aria-label="t('common.close')" @click="closeParcel">
            <Icon name="x" :size="18" />
          </button>
        </div>
        <!-- progress: the only number that matters while packing -->
        <div class="mt-3 flex items-center gap-3">
          <div class="flex-1 h-2.5 rounded-full bg-stone-100 overflow-hidden">
            <div class="h-full rounded-full transition-all duration-300"
                 :class="parcel.packed >= parcel.pieces ? 'bg-emerald-500' : 'bg-[var(--accent-500)]'"
                 :style="{ width: Math.round(100 * parcel.packed / Math.max(1, parcel.pieces)) + '%' }" />
          </div>
          <span class="text-[19px] font-bold tabular-nums flex-shrink-0"
                :class="parcel.packed >= parcel.pieces ? 'text-emerald-600' : 'text-stone-900'">
            {{ parcel.packed }}/{{ parcel.pieces }}
          </span>
        </div>
      </div>

      <!-- the pieces -->
      <div class="px-3 py-3 space-y-2.5">
        <div v-for="it in parcel.items" :key="it.sku"
             class="bg-white rounded-2xl ring-1 p-3 flex items-center gap-3 transition-all"
             :class="flash === it.sku ? 'ring-2 ring-[var(--accent-500)] shadow-md scale-[1.01]'
               : it.packed >= it.qty ? 'ring-emerald-200 bg-emerald-50/50' : 'ring-stone-200/70'">
          <img v-if="it.image" :src="it.image" alt="" loading="lazy" @error="hideImg"
               class="w-14 h-14 rounded-xl object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
          <span v-else class="w-14 h-14 rounded-xl bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400">
            <Icon name="package" :size="18" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="text-[13.5px] font-medium text-stone-900 line-clamp-2" dir="auto">{{ it.name }}</div>
            <div class="font-mono text-[11px] text-stone-500 mt-1">{{ it.realSku || it.sku }}</div>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-[20px] font-bold tabular-nums"
                  :class="it.packed >= it.qty ? 'text-emerald-600' : 'text-stone-900'">
              {{ it.packed }}/{{ it.qty }}
            </span>
            <Icon v-if="it.packed >= it.qty" name="check-circle" :size="20" class="text-emerald-500" />
            <!-- the piece is not in the slot: stop the parcel here -->
            <button v-else class="w-11 h-11 rounded-xl flex items-center justify-center transition-colors"
                    :class="shortFor === it.sku ? 'bg-rose-600 text-white' : 'bg-stone-100 text-stone-400'"
                    :aria-label="t('pk.missing')" @click="onShort(it)">
              <Icon name="alert-triangle" :size="17" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- sealed: a full-width green bar the packer cannot miss -->
    <Transition name="pk-seal">
      <div v-if="sealed" class="fixed inset-x-0 bottom-0 z-30 bg-emerald-500 text-white px-5 py-4 flex items-center gap-3 shadow-2xl">
        <Icon name="check-circle" :size="26" />
        <div class="min-w-0 flex-1">
          <div class="text-[15px] font-bold">{{ t("pk.sealed") }}</div>
          <div class="text-[12px] opacity-90 truncate">{{ sealed.customer }} · {{ sealed.pieces }} {{ t("pk.pieces") }}</div>
        </div>
        <button class="h-11 px-4 rounded-xl bg-white/20 text-[13px] font-semibold" @click="sealed = null">
          {{ t("pk.next") }}
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { warn, success } = useToast();

const scanner = ref(null);
const parcel = ref(null);
const board = ref(null);
const showQueue = ref(false);
const sealed = ref(null);
const flash = ref("");
const shortFor = ref("");
let flashTimer = null;
let shortTimer = null;

function hideImg(e) { e.target.style.display = "none"; }

async function loadBoard() {
  try { board.value = await api("packing.pack_board"); } catch (_) { /* the desk still works */ }
}

function beat(sku) {
  flash.value = sku;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => { flash.value = ""; }, 700);
}

// One scan handler for both modes: with no parcel open the code is a label,
// with one open it is a piece. The packer never chooses a mode.
async function onScan(code) {
  if (!parcel.value) return openByCode(code);
  return scanPiece(code);
}

async function openByCode(code) {
  try {
    const res = await apiPost("packing.pack_open", { code });
    if (res.ok) {
      parcel.value = res;
      showQueue.value = false;
      sealed.value = null;
      if (res.done) {
        scanner.value?.showError(t("pk.alreadyPacked").replace("{who}", res.packedBy));
      } else {
        scanner.value?.showSuccess(`${res.customer} · ${res.pieces} ${t("pk.pieces")}`);
      }
      return;
    }
    if (res.reason === "single") {
      // 80% of the day. Say it once, clearly, and let it go through.
      scanner.value?.showSuccess(t("pk.singlePass"));
    } else if (res.reason === "not_sorted") {
      scanner.value?.showError(t("pk.notSorted"));
    } else if (res.reason === "gone") {
      scanner.value?.showError(t("pk.gone"));
    } else {
      scanner.value?.showError(t("pk.unknownAwb").replace("{code}", res.code || ""));
    }
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
  }
}

async function openOrder(order) {
  showQueue.value = false;
  await openByCode(order);
}

async function scanPiece(code) {
  const o = parcel.value.order;
  try {
    const res = await apiPost("packing.pack_item", { order: o, code });
    if (res.ok === false) {
      if (res.reason === "not_on_order") {
        const b = res.belongsTo;
        scanner.value?.showError(
          b ? t("pk.otherParcel").replace("{who}", b.customer || b.order)
            : t("pk.notOnOrder"));
      } else if (res.reason === "line_done") {
        parcel.value = { ...parcel.value, ...res };
        scanner.value?.showError(t("pk.lineDone"));
      } else if (res.reason === "already_sealed") {
        parcel.value = { ...parcel.value, ...res };
        scanner.value?.showError(t("pk.alreadyPacked").replace("{who}", res.packedBy || ""));
      } else {
        scanner.value?.showError(t("pk.unknownPiece"));
      }
      return;
    }
    parcel.value = res;
    beat(res.scanned);
    if (res.sealed) {
      sealed.value = { customer: res.customer, pieces: res.pieces };
      scanner.value?.showSuccess(t("pk.sealed"));
      setTimeout(() => { parcel.value = null; }, 500);
      loadBoard();
    } else {
      scanner.value?.showSuccess(`${res.packed}/${res.pieces}`);
    }
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
  }
}

// Two taps: the first arms, the second reports. A mis-tap must not stop a
// parcel, and a real missing piece must not need a keyboard.
async function onShort(it) {
  if (shortFor.value !== it.sku) {
    shortFor.value = it.sku;
    clearTimeout(shortTimer);
    shortTimer = setTimeout(() => { shortFor.value = ""; }, 4000);
    warn(t("pk.missingArm"), it.realSku || it.sku);
    return;
  }
  shortFor.value = "";
  try {
    await apiPost("packing.pack_short", { order: parcel.value.order, item_code: it.sku });
    success(t("pk.missingSent"), it.realSku || it.sku);
    parcel.value = null;
    loadBoard();
  } catch (e) {
    warn(t("pk.missingFail"), String(e.message || e));
  }
}

function closeParcel() {
  parcel.value = null;
  scanner.value?.refocus();
}

onMounted(loadBoard);
</script>

<style scoped>
.pk-seal-enter-active, .pk-seal-leave-active { transition: transform .22s ease, opacity .22s ease; }
.pk-seal-enter-from, .pk-seal-leave-to { transform: translateY(100%); opacity: 0; }
.line-clamp-2 {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
</style>
