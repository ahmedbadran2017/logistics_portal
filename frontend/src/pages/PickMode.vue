<template>
  <div class="min-h-full bg-stone-50 flex flex-col">
    <!-- Header -->
    <div class="px-4 pt-3 pb-2.5 bg-white border-b border-stone-200/70 sticky top-0 z-10">
      <div class="flex items-center gap-2.5">
        <button class="w-8 h-8 rounded-lg bg-stone-100 flex items-center justify-center flex-shrink-0" @click="goBack">
          <Icon name="chevron-left" :size="16" class="rtl:rotate-180" />
        </button>
        <div class="min-w-0 flex-1">
          <div class="font-mono text-[14px] font-bold text-stone-900 truncate">{{ id }}</div>
          <div class="text-[11px] text-stone-500">{{ t("pickm.scanned") }} {{ done }}/{{ total }} · {{ pct }}%</div>
        </div>
        <span class="text-[12px] font-bold tabular-nums px-2 py-1 rounded-lg"
              :class="allDone ? 'bg-emerald-50 text-emerald-700' : 'bg-stone-100 text-stone-700'">
          {{ done }}/{{ total }}
        </span>
      </div>
      <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden mt-2">
        <div class="h-full rounded-full transition-all duration-300"
             :class="allDone ? 'bg-emerald-500' : 'bg-[var(--accent-500)]'"
             :style="{ width: pct + '%' }" />
      </div>
    </div>

    <!-- Scanner -->
    <div class="px-4 py-3 bg-white border-b border-stone-200/70 sticky top-[74px] z-10">
      <ScanInput ref="scanner" :placeholder="t('pickm.scanPh')" @scan="onScan" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="p-4 space-y-2.5">
      <div v-for="n in 4" :key="n" class="h-[72px] rounded-2xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
    </div>

    <!-- Walk stops: lines grouped by bin, in walk order -->
    <div v-else class="flex-1 px-4 py-3 space-y-3 pb-28">
      <div v-for="stop in stops" :key="stop.bin" class="space-y-1.5">
        <div class="flex items-center gap-2 px-1">
          <Icon name="map-pin" :size="12" class="text-stone-400" />
          <span class="text-[11px] font-bold uppercase tracking-[0.05em] text-stone-500">{{ stop.bin }}</span>
          <span class="text-[10.5px] text-stone-400 tabular-nums ms-auto">{{ stop.done }}/{{ stop.qty }}</span>
        </div>
        <div
          v-for="l in stop.lines"
          :key="l.sku + l.so"
          class="bg-white rounded-2xl ring-1 p-3 flex items-center gap-3 transition-all"
          :class="flash === l.sku ? 'ring-2 ring-[var(--accent-500)] shadow-md'
            : l.scannedQty >= l.qty ? 'ring-emerald-200 bg-emerald-50/40' : 'ring-stone-200/70'"
        >
          <img v-if="l.image" :src="l.image" alt="" loading="lazy" @error="hideImg"
               class="w-12 h-12 rounded-xl object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
          <span v-else class="w-12 h-12 rounded-xl bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400">
            <Icon name="package" :size="16" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-medium text-stone-900 truncate">{{ l.name }}</div>
            <div class="font-mono text-[11px] text-stone-500">{{ l.realSku || l.sku }}</div>
          </div>
          <div class="text-end flex-shrink-0">
            <span class="text-[16px] font-bold tabular-nums"
                  :class="l.scannedQty >= l.qty ? 'text-emerald-600' : 'text-stone-900'">
              {{ l.scannedQty }}/{{ l.qty }}
            </span>
            <Icon v-if="l.scannedQty >= l.qty" name="check-circle" :size="16" class="text-emerald-500 ms-1 inline" />
          </div>
        </div>
      </div>
    </div>

    <!-- Finish dock -->
    <div v-if="!loading" class="fixed bottom-[64px] inset-x-0 px-4 pb-2 z-10">
      <div class="max-w-[480px] mx-auto">
        <button
          class="w-full h-12 rounded-2xl text-[15px] font-semibold text-white flex items-center justify-center gap-2 shadow-lg transition-colors disabled:opacity-50"
          :class="allDone ? 'bg-emerald-600 active:bg-emerald-700' : 'bg-stone-300'"
          :disabled="!allDone || submitting"
          @click="finish"
        >
          <Icon name="check-circle" :size="18" />
          {{ submitting ? t("pickm.submitting") : t("pickm.finish") }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const { t } = useI18n();
const { success, warn } = useToast();

const scanner = ref(null);
const lines = ref([]);
const loading = ref(true);
const submitting = ref(false);
const flash = ref("");

onMounted(async () => {
  try {
    const d = await api("picking.pick_list_detail", { name: props.id });
    lines.value = d?.lines || [];
  } catch (e) {
    warn(t("pickm.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
  scanner.value?.refocus();
});

// Walk stops: group by bin, preserve backend walk order.
const stops = computed(() => {
  const by = new Map();
  for (const l of lines.value) {
    const bin = l.bin || "—";
    if (!by.has(bin)) by.set(bin, { bin, lines: [], qty: 0, done: 0 });
    const s = by.get(bin);
    s.lines.push(l);
    s.qty += l.qty;
    s.done += Math.min(l.scannedQty, l.qty);
  }
  return [...by.values()];
});
const total = computed(() => lines.value.reduce((a, l) => a + l.qty, 0));
const done = computed(() => lines.value.reduce((a, l) => a + Math.min(l.scannedQty, l.qty), 0));
const pct = computed(() => (total.value ? Math.round(done.value / total.value * 100) : 0));
const allDone = computed(() => total.value > 0 && done.value >= total.value);

async function onScan(code) {
  const c = String(code || "").trim();
  if (!c) return;
  let res;
  try {
    res = await apiPost("picking.scan_pick", { pick_list: props.id, code: c });
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
    return;
  }
  if (!res.ok) {
    scanner.value?.showError(
      res.reason === "done" ? t("pickm.lineDone")
        : res.reason === "not_on_list" ? t("pickm.notOnList")
          : t("pickm.unknown"));
    return;
  }
  // Reflect the backend truth locally.
  const l = lines.value.find((x) => x.sku === res.itemCode && x.scannedQty < x.qty)
    || lines.value.find((x) => x.sku === res.itemCode);
  if (l) {
    l.scannedQty = Math.min(l.scannedQty + 1, l.qty);
    flash.value = l.sku;
    setTimeout(() => { if (flash.value === l.sku) flash.value = ""; }, 800);
  }
  scanner.value?.showSuccess(`${res.name || res.itemCode} · ${res.totalScanned}/${res.totalQty}`);
  if (res.totalScanned >= res.totalQty) success(t("pickm.allScanned"), props.id);
}

async function finish() {
  submitting.value = true;
  try {
    const res = await apiPost("picking.submit_pick_list", { name: props.id });
    success(t("pickm.done"), res?.awb ? `AWB ${res.awb}` : props.id);
    router.push({ name: "Queue" });
  } catch (e) {
    warn(t("pickm.submitFail"), String(e.message || e));
  } finally {
    submitting.value = false;
  }
}

function goBack() { router.push({ name: "Queue" }); }
function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }
</script>
