<template>
  <div class="max-w-[820px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('pack.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('pack.intro') }}</p>
      </div>
      <span class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200/70 rounded-lg px-2.5 h-8 tabular-nums">
        <Icon name="check-circle" :size="14" />{{ packedToday }} {{ t('pack.packedToday') }}
      </span>
    </header>

    <!-- scanner -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
      <ScanInput ref="scanner" :placeholder="current ? t('pack.scanNext') : t('pack.scanStart')" @scan="onScan" />
      <div v-if="current" class="mt-1.5 text-[11.5px] text-stone-500 tabular-nums">{{ totalPacked }}/{{ totalNeeded }} {{ t('pack.itemsPacked') }}</div>
    </div>

    <!-- no order open -->
    <div v-if="!current" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-10 text-center">
      <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-[var(--accent-50)] text-[var(--accent-600)] mb-3"><Icon name="tag" :size="22" /></span>
      <div class="text-[15px] font-semibold text-stone-900">{{ t('pack.emptyTitle') }}</div>
      <div class="text-[12.5px] text-stone-500 mt-1 max-w-sm mx-auto">{{ t('pack.emptyHint') }}</div>
    </div>

    <!-- open order -->
    <div v-else class="bg-white rounded-2xl ring-1 p-4" :class="orderComplete ? 'ring-emerald-300' : 'ring-stone-200/70'">
      <div class="flex items-start justify-between gap-3 border-b border-stone-100 pb-3 mb-3">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-mono text-[15px] font-bold text-stone-900">{{ current.order }}</span>
            <span v-if="current.single" class="inline-flex items-center gap-1 text-[10.5px] font-semibold text-[var(--accent-700)] bg-[var(--accent-50)] ring-1 ring-[var(--accent-200)]/60 rounded px-1.5 py-0.5">{{ t('pack.single') }}</span>
            <span v-else class="inline-flex items-center gap-1 text-[10.5px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200/60 rounded px-1.5 py-0.5">{{ current.items.length }} {{ t('pack.itemsWord') }}</span>
          </div>
          <div class="text-[12px] text-stone-500 truncate mt-0.5">{{ current.customer }}<span v-if="current.city" class="capitalize"> · {{ current.city }}</span> · <span class="font-mono">{{ current.awb || '—' }}</span></div>
        </div>
        <button class="text-stone-400 hover:text-stone-700 flex-shrink-0" :title="t('pack.skip')" @click="clearOrder"><Icon name="x" :size="18" /></button>
      </div>

      <div class="space-y-2">
        <div v-for="it in current.items" :key="it.sku" class="flex items-center gap-3 rounded-xl ring-1 p-2.5"
             :class="itemPacked(it) >= it.qty ? 'ring-emerald-200 bg-emerald-50/40' : 'ring-stone-200'">
          <img v-if="it.image" :src="it.image" alt="" loading="lazy" @error="onImgError"
               class="w-12 h-12 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
          <span v-else class="w-12 h-12 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="16" /></span>
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ it.name }}</div>
            <div class="font-mono text-[11px] text-stone-500">SKU {{ it.realSku || it.sku }}</div>
          </div>
          <span class="text-[14px] font-bold tabular-nums flex-shrink-0" :class="itemPacked(it) >= it.qty ? 'text-emerald-600' : 'text-stone-800'">{{ itemPacked(it) }}/{{ it.qty }}</span>
          <Icon v-if="itemPacked(it) >= it.qty" name="check-circle" :size="18" class="text-emerald-500 flex-shrink-0" />
        </div>
      </div>

      <button class="mt-3 w-full h-11 rounded-xl text-[14px] font-semibold text-white flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              :class="orderComplete ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-stone-300 cursor-not-allowed'"
              :disabled="!orderComplete || busy" @click="finishOrder">
        <Icon name="printer" :size="16" />{{ busy ? t('pack.finishing') : t('pack.printFinish') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { apiPost, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const scanner = ref(null);
const current = ref(null);        // the order open at the station
const packed = ref({});           // item_code -> units packed for the current order
const packedToday = ref(0);
const busy = ref(false);

const itemPacked = (it) => packed.value[it.sku] || 0;
const totalPacked = computed(() => (current.value?.items || []).reduce((a, it) => a + Math.min(itemPacked(it), it.qty), 0));
const totalNeeded = computed(() => (current.value?.items || []).reduce((a, it) => a + it.qty, 0));
const orderComplete = computed(() => !!current.value && current.value.items.every((it) => itemPacked(it) >= it.qty));

function onImgError(e) { if (e && e.target) e.target.style.display = "none"; }
function matchItem(lc) {
  return (current.value?.items || []).find((it) => itemPacked(it) < it.qty &&
    [it.realSku, it.sku].some((v) => v && String(v).toLowerCase() === lc));
}

async function onScan(raw) {
  const code = String(raw || "").trim();
  if (!code || busy.value) return;
  // An order is open and still needs items → this scan completes it.
  if (current.value && !orderComplete.value) {
    const it = matchItem(code.toLowerCase());
    if (it) {
      packed.value = { ...packed.value, [it.sku]: Math.min(itemPacked(it) + 1, it.qty) };
      scanner.value?.showSuccess(`✓ ${totalPacked.value}/${totalNeeded.value}`);
      if (orderComplete.value) await finishOrder();
    } else {
      scanner.value?.showError(t("pack.finishFirst"));
    }
    return;
  }
  // Otherwise, open the order this item belongs to.
  busy.value = true;
  const res = await liveOr(null, () => apiPost("picking.pack_scan", { code }));
  busy.value = false;
  if (!res || !res.ok) {
    scanner.value?.showError(res && res.reason === "no_order" ? t("pack.noOrder") : t("pack.unknown"));
    return;
  }
  current.value = res;
  const first = res.items.find((x) => x.sku === res.scannedItem);
  packed.value = first ? { [first.sku]: 1 } : {};
  if (res.single || orderComplete.value) await finishOrder();
  else scanner.value?.showSuccess(`${res.order} · ${res.items.length} ${t("pack.itemsWord")}`);
}

async function finishOrder() {
  const ord = current.value?.order;
  const fallbackUrl = current.value?.labelUrl;
  if (!ord) return;
  busy.value = true;
  try {
    const r = await apiPost("picking.mark_packed", { order: ord });
    printLabel(r?.labelUrl || fallbackUrl);
    packedToday.value += 1;
    success(t("pack.packed"), `${ord}`);
  } catch (e) {
    warn(t("pack.finishFail"), String(e.message || e));
  } finally {
    busy.value = false;
    current.value = null;
    packed.value = {};
    scanner.value?.refocus();
  }
}
function clearOrder() { current.value = null; packed.value = {}; scanner.value?.refocus(); }

// Thermal label prints from the browser dialog: load it in a hidden iframe and
// pop the print dialog; if the label is cross-origin, fall back to a new tab.
function printLabel(url) {
  if (!url) return;
  try {
    let f = document.getElementById("lp-print-frame");
    if (!f) { f = document.createElement("iframe"); f.id = "lp-print-frame"; f.style.display = "none"; document.body.appendChild(f); }
    f.onload = () => { try { f.contentWindow.focus(); f.contentWindow.print(); } catch (e) { window.open(url, "_blank"); } };
    f.src = url;
  } catch (e) { window.open(url, "_blank"); }
}

onMounted(() => scanner.value?.refocus());
</script>
