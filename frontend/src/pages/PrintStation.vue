<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[760px] mx-auto">
    <header>
      <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('pstation.title') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-1">{{ t('pstation.intro') }}</p>
    </header>

    <!-- The big truth: is this laptop listening, and how deep is the queue. -->
    <div class="rounded-2xl ring-1 px-5 py-4 flex items-center gap-4 flex-wrap"
         :class="auto ? 'bg-emerald-50 ring-emerald-200' : 'bg-stone-50 ring-stone-200'">
      <span class="relative flex w-3 h-3 flex-shrink-0">
        <span v-if="auto" class="absolute inline-flex w-full h-full rounded-full bg-emerald-500 opacity-60 animate-ping" />
        <span class="relative inline-flex w-3 h-3 rounded-full" :class="auto ? 'bg-emerald-500' : 'bg-stone-300'" />
      </span>
      <div class="min-w-[160px]">
        <div class="text-[14px] font-bold" :class="auto ? 'text-emerald-900' : 'text-stone-700'">
          {{ auto ? t('pstation.listening') : t('pstation.paused') }}
        </div>
        <div class="text-[11px]" :class="auto ? 'text-emerald-700/80' : 'text-stone-400'">
          {{ t('pstation.printedN').replace('{n}', String(printedCount)) }}
        </div>
      </div>
      <div class="text-center">
        <div class="text-[22px] font-extrabold tabular-nums" :class="pending ? 'text-amber-600' : 'text-stone-800'">{{ pending }}</div>
        <div class="text-[9.5px] uppercase font-semibold text-stone-400">{{ t('pstation.pending') }}</div>
      </div>
      <div class="ms-auto flex items-center gap-2">
        <select v-model="sizeKey" class="h-9 px-2 rounded-lg text-[12px] bg-white ring-1 ring-stone-200">
          <option v-for="s in LABEL_SIZES" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>
        <button class="h-9 px-4 rounded-lg text-[12.5px] font-bold text-white"
                :class="auto ? 'bg-stone-900' : ''"
                :style="auto ? {} : { background: 'var(--accent-600)' }"
                @click="auto = !auto">
          {{ auto ? t('pstation.stop') : t('pstation.start') }}
        </button>
      </div>
    </div>

    <!-- Setup note: this only runs hands-free inside kiosk-print Chrome. -->
    <div class="flex items-start gap-2 text-[11.5px] text-stone-500 bg-stone-50 ring-1 ring-stone-200/60 rounded-xl px-3.5 py-2.5">
      <Icon name="info" :size="13" class="mt-0.5 flex-shrink-0 text-stone-400" />
      <span>{{ t('pstation.kioskHint') }} <code class="font-mono text-[10.5px] bg-white px-1 rounded ring-1 ring-stone-200">chrome --kiosk-printing</code></span>
    </div>

    <div class="flex items-center gap-2">
      <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
              @click="testPrint">
        <Icon name="printer" :size="13" class="inline -mt-px me-1" />{{ t('pstation.test') }}
      </button>
      <span v-if="lastErr" class="text-[11.5px] text-rose-600">{{ lastErr }}</span>
    </div>

    <!-- What just came off the printer — the operator's receipt. -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
        <Icon name="history" :size="14" class="text-stone-400" />
        <span class="text-[12px] font-semibold text-stone-900">{{ t('pstation.recent') }}</span>
      </div>
      <div class="divide-y divide-stone-100">
        <div v-for="r in recent" :key="r.item_code + (r.printed_at || '')" class="px-4 py-2 flex items-center gap-3">
          <span class="font-mono text-[12px] text-stone-700">{{ r.sku || r.item_code }}</span>
          <span class="text-[11.5px] text-stone-500 truncate flex-1" dir="auto">{{ r.item_name }}</span>
          <span v-if="r.qty > 1" class="text-[10.5px] font-bold text-stone-500 tabular-nums">×{{ r.qty }}</span>
          <span v-if="r.station" class="text-[10px] font-semibold rounded-full px-2 py-0.5 bg-stone-100 text-stone-500">{{ r.station }}</span>
          <span class="text-[10.5px] text-stone-400 tabular-nums">{{ (r.printed_at || '').slice(11, 16) }}</span>
        </div>
        <div v-if="!recent.length" class="px-4 py-6 text-center text-[12px] text-stone-400">{{ t('pstation.empty') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { LABEL_SIZES, printShelfLabels } from "@/lib/shelfLabelPrint.js";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const auto = ref(true);
const pending = ref(0);
const printedCount = ref(0);
const recent = ref([]);
const lastErr = ref("");
const sizeKey = ref(localStorage.getItem("lp_print_size") || LABEL_SIZES[0].key);
watch(sizeKey, (v) => { try { localStorage.setItem("lp_print_size", v); } catch {} });

function size() { return LABEL_SIZES.find((s) => s.key === sizeKey.value) || LABEL_SIZES[0]; }

function printJobs(jobs) {
  // One window per pull, all labels inside — the station Chrome runs with
  // --kiosk-printing, so this goes straight to the default printer.
  const ok = printShelfLabels({
    shelf: "",
    items: jobs.map((j) => ({
      sku: j.sku || j.barcode || j.item_code,
      barcode: j.barcode,
      name: j.item_name,
      qty: 1,
      copies: Math.max(1, Number(j.qty || 1)),
    })),
    copies: "sku",
    size: size(),
  });
  if (!ok) lastErr.value = t("pstation.popupBlocked");
  else { lastErr.value = ""; printedCount.value += jobs.length; }
  return ok;
}

let busy = false;
async function tick() {
  if (!auto.value || busy) return;
  busy = true;
  try {
    const r = await apiPost("labelprint.pull", { limit: 10 });
    pending.value = r.pending || 0;
    if ((r.jobs || []).length) {
      printJobs(r.jobs);
      const s = await api("labelprint.state");
      recent.value = s.recent || [];
      pending.value = s.pending || 0;
    }
  } catch (e) { lastErr.value = String(e.message || e); }
  busy = false;
}
async function loadState() {
  try {
    const s = await api("labelprint.state");
    recent.value = s.recent || [];
    pending.value = s.pending || 0;
  } catch {}
}
function testPrint() {
  printJobs([{ sku: "TEST-LABEL", barcode: "1234567890", item_name: "Print station test", qty: 1 }]);
}

// NB: no visibility gate — this tab IS the printer. Browsers throttle hidden
// tabs to ~1 poll/min, which still works, but the station should stay
// frontmost for instant labels.
const timer = setInterval(tick, 3000);
onMounted(() => { loadState(); tick(); });
onUnmounted(() => clearInterval(timer));
</script>
