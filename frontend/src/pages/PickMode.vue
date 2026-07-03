<template>
  <div class="min-h-full bg-white flex flex-col">
    <!-- Success state -->
    <div
      v-if="complete"
      class="flex-1 flex flex-col items-center justify-center text-center px-8 py-16 bg-gradient-to-b from-emerald-50 to-white"
    >
      <div class="w-24 h-24 rounded-full bg-emerald-500 text-white flex items-center justify-center mb-5 shadow-[0_12px_40px_-8px_rgba(16,185,129,0.5)]">
        <Icon name="check" :size="48" />
      </div>
      <div class="text-[22px] font-bold text-stone-900">Nice work 🎉</div>
      <div class="text-[14px] text-stone-600 mt-1">{{ orderNo }} · {{ order?.customer }}</div>
      <button
        class="mt-8 h-13 px-6 py-3.5 rounded-2xl bg-stone-900 text-white text-[15px] font-semibold active:scale-[0.98] transition-transform"
        @click="nextOrder"
      >
        Next order
      </button>
    </div>

    <template v-else>
      <!-- header -->
      <div class="px-4 pt-3 pb-3 border-b border-stone-100 flex items-center gap-3 sticky top-0 bg-white z-10">
        <button
          class="w-9 h-9 rounded-full hover:bg-stone-100 flex items-center justify-center text-stone-600"
          @click="$router.back()"
        >
          <Icon name="chevron-left" :size="18" />
        </button>
        <div class="flex-1 min-w-0">
          <div class="font-mono text-[14px] font-bold text-stone-900 truncate">{{ orderNo }}</div>
          <div class="text-[11.5px] text-stone-500 truncate">{{ order?.customer || "Order" }}</div>
        </div>
        <span
          v-if="order"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap"
          :class="[SLA[order.sla].txt, SLA[order.sla].bg, SLA[order.sla].ring]"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="SLA[order.sla].dot" />
          {{ SLA_LABEL[order.sla] }}
        </span>
      </div>

      <!-- progress -->
      <div class="px-4 py-3">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-[12px] font-medium text-stone-500 whitespace-nowrap">{{ scannedCount }} / {{ items.length }} scanned</span>
          <span class="text-[12px] font-semibold text-emerald-600">{{ progress }}%</span>
        </div>
        <div class="h-2 rounded-full bg-stone-100 overflow-hidden">
          <div class="h-full bg-emerald-500 rounded-full transition-all duration-300" :style="{ width: progress + '%' }" />
        </div>
      </div>

      <!-- current item hero -->
      <div v-if="current" class="px-4 pb-1">
        <div class="rounded-2xl ring-1 ring-stone-900 bg-white p-4 shadow-[0_4px_16px_-6px_rgba(0,0,0,0.12)]">
          <div class="text-[10px] font-semibold text-stone-400 uppercase tracking-wide mb-1">Current item</div>
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="text-[15px] font-semibold text-stone-900 truncate">{{ current.name }}</div>
              <div class="text-[12px] text-stone-500 mt-1 flex items-center gap-2 flex-wrap">
                <span class="font-mono">{{ current.sku }}</span>
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stone-100 text-stone-600 font-mono font-medium whitespace-nowrap">
                  <Icon name="map-pin" :size="10" />{{ current.bin }}
                </span>
              </div>
            </div>
            <div class="text-[18px] font-bold text-stone-900 tabular-nums leading-none flex-shrink-0">×{{ current.qty }}</div>
          </div>
        </div>
      </div>

      <!-- scan input -->
      <div class="px-4 pt-3">
        <ScanInput ref="scanner" placeholder="Scan item barcode" @scan="onScan" />
      </div>

      <!-- remaining checklist -->
      <div class="px-4 space-y-2.5 flex-1">
        <div
          v-for="it in items"
          :key="it.sku"
          class="rounded-2xl ring-1 p-3.5 transition-all"
          :class="it.scanned ? 'ring-emerald-200 bg-emerald-50/50' : it === current ? 'ring-stone-300 bg-white' : 'ring-stone-200 bg-white opacity-60'"
        >
          <div class="flex items-center gap-3">
            <div
              class="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
              :class="it.scanned ? 'bg-emerald-500 text-white' : 'bg-stone-100 text-stone-400'"
            >
              <Icon :name="it.scanned ? 'check' : 'package'" :size="it.scanned ? 22 : 20" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-[13.5px] font-medium text-stone-900 truncate">{{ it.name }}</div>
              <div class="text-[11.5px] text-stone-500 mt-0.5 flex items-center gap-2">
                <span class="font-mono">{{ it.sku }}</span>
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stone-100 text-stone-600 font-mono font-medium whitespace-nowrap">
                  <Icon name="map-pin" :size="10" />{{ it.bin }}
                </span>
              </div>
            </div>
            <div class="text-[15px] font-bold text-stone-900 tabular-nums leading-none flex-shrink-0">×{{ it.qty }}</div>
          </div>
        </div>
      </div>

      <!-- action dock -->
      <div class="sticky bottom-0 bg-white border-t border-stone-100 p-4 pt-3 space-y-2.5">
        <div v-if="allScanned" class="flex items-center justify-center gap-2 text-[13px] font-semibold text-emerald-600">
          <Icon name="check-circle" :size="18" /> All items scanned
        </div>
        <div class="flex gap-2.5">
          <button
            class="flex-1 h-12 rounded-2xl ring-1 ring-stone-200 text-stone-700 text-[13.5px] font-semibold flex items-center justify-center gap-1.5 active:scale-[0.98] transition-transform"
            @click="reportIssue"
          >
            <Icon name="alert-triangle" :size="16" /> Report issue
          </button>
          <button
            class="flex-1 h-12 rounded-2xl text-white text-[13.5px] font-semibold flex items-center justify-center gap-1.5 transition-all active:scale-[0.98]"
            :class="allScanned ? 'bg-emerald-500' : 'bg-stone-300 cursor-not-allowed'"
            :disabled="!allScanned"
            @click="completePick"
          >
            <Icon name="check" :size="16" /> Complete Pick
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { ORDERS, PICK_ITEMS, SLA, SLA_LABEL, byId } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";

const props = defineProps({ id: String });
const router = useRouter();

const orderNo = computed(() => (props.id?.startsWith("SAL-ORD") ? props.id : "#" + props.id));
const order = computed(
  () => ORDERS.find((o) => o.no === orderNo.value || o.no.replace("#", "") === props.id) || null
);

// Build the line-item list for this order from PICK_ITEMS.
const count = Math.min(order.value?.items || 1, PICK_ITEMS.length) || 1;
const items = ref(PICK_ITEMS.slice(0, count).map((it) => ({ ...it, scanned: false })));

const complete = ref(false);
const scanner = ref(null);

// Live-or-demo: overwrite the demo line items with the real pick items for
// this order once the app is installed. In preview api() fails → keep demo.
onMounted(async () => {
  const orderId = order.value?.no || props.id;
  const live = await liveOr(null, () => api("picking.pick_items", { order: orderId }));
  if (live && live.length) {
    items.value = live.map((it) => ({ ...it, scanned: false }));
  }
});

const current = computed(() => items.value.find((i) => !i.scanned) || null);
const scannedCount = computed(() => items.value.filter((i) => i.scanned).length);
const allScanned = computed(() => items.value.length > 0 && items.value.every((i) => i.scanned));
const progress = computed(() =>
  items.value.length ? Math.round((scannedCount.value / items.value.length) * 100) : 0
);

function onScan(code) {
  const c = code.toLowerCase();
  const exact = items.value.find((i) => !i.scanned && i.sku.toLowerCase() === c);
  const target = exact || current.value;
  if (!target) return scanner.value.showError("✗ Nothing left to scan");
  if (target.scanned) return scanner.value.showError("Already scanned");
  target.scanned = true;
  scanner.value.showSuccess(`✓ Scanned (${scannedCount.value}/${items.value.length})`);
}
function reportIssue() {
  scanner.value?.showError("Issue reported — dispatcher notified");
}
function completePick() {
  complete.value = true;
}
function nextOrder() {
  router.push({ name: "Queue" });
}
</script>
