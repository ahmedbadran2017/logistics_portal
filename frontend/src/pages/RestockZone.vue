<template>
  <div class="max-w-[900px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('restock.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('restock.intro') }}</p>
      </div>
      <div v-if="loadingSummary" class="flex items-center gap-2">
        <span class="w-[90px] h-8 rounded-lg bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
        <span class="w-[150px] h-8 rounded-lg bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <div v-else-if="summary" class="flex items-center gap-2 flex-wrap">
        <span class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 rounded-lg px-2.5 h-8 tabular-nums">
          {{ summary.qty }} {{ t('recv.units') }}
        </span>
        <span class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-lg px-2.5 h-8 tabular-nums">
          {{ fmt(summary.value) }} MAD {{ t('restock.stuck') }}
        </span>
      </div>
    </header>

    <!-- Scanner -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
      <ScanInput ref="scanner" :placeholder="t('restock.scanPh')" @scan="onScan" />
    </div>

    <!-- Scanned item card -->
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
          <div class="text-[12px] text-stone-500 mt-0.5">
            <b class="text-stone-900 tabular-nums">{{ current.inZone }}</b> {{ t('restock.inZone') }}
          </div>
        </div>
        <button :title="t('common.close')" class="w-8 h-8 rounded-lg hover:bg-stone-100 flex items-center justify-center flex-shrink-0" @click="clearCurrent">
          <Icon name="x" :size="16" />
        </button>
      </div>

      <!-- qty stepper -->
      <div class="flex items-center gap-3">
        <span class="text-[12.5px] font-medium text-stone-600 w-16">{{ t('restock.qty') }}</span>
        <div class="flex items-center gap-1">
          <button class="w-9 h-9 rounded-lg bg-stone-100 text-[16px] font-bold" @click="qty = Math.max(1, qty - 1)">−</button>
          <span class="w-12 text-center text-[16px] font-bold tabular-nums">{{ qty }}</span>
          <button class="w-9 h-9 rounded-lg bg-stone-100 text-[16px] font-bold" @click="qty = Math.min(current.inZone, qty + 1)">+</button>
        </div>
        <button class="text-[11.5px] font-semibold text-[var(--accent-700)]" @click="qty = current.inZone">
          {{ t('restock.all') }} ({{ current.inZone }})
        </button>
      </div>

      <!-- target shelf: sibling-stock suggestions as one-tap chips, plus a
           searchable field for any other valid shelf (the old <select> had
           650+ options — unusable on the PDA). -->
      <div class="flex items-start gap-3 flex-wrap">
        <span class="text-[12.5px] font-medium text-stone-600 w-16 mt-2">{{ t('restock.target') }}</span>
        <div class="flex-1 min-w-[200px] space-y-2">
          <div v-if="current.suggestions?.length" class="flex flex-wrap gap-1.5">
            <button
              v-for="s in current.suggestions" :key="s.warehouse"
              class="h-8 px-2.5 rounded-lg text-[12px] font-semibold ring-1 transition-colors tabular-nums"
              :class="target === s.warehouse
                ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]'
                : 'text-stone-700 bg-white ring-stone-200 hover:ring-stone-300'"
              @click="target = s.warehouse"
            >{{ s.warehouse.replace(' - JM', '') }} · {{ s.qty }} {{ t('restock.already') }}</button>
          </div>
          <input
            v-model="target"
            list="lp-restock-targets"
            :placeholder="t('restock.otherShelf')"
            class="w-full h-10 ps-3 pe-3 rounded-lg bg-white ring-1 text-[13px] text-stone-800 focus:outline-none focus:ring-2"
            :class="target && !targetValid ? 'ring-rose-300' : 'ring-stone-200'"
            style="--tw-ring-color: var(--accent-400)"
          />
          <datalist id="lp-restock-targets">
            <option v-for="w in summary?.targets || []" :key="w" :value="w" />
          </datalist>
          <p v-if="target && !targetValid" class="text-[11px] text-rose-600">{{ t('restock.invalidShelf') }}</p>
        </div>
      </div>

      <!-- actions -->
      <div class="grid grid-cols-2 gap-2.5">
        <button
          class="h-11 rounded-xl text-[13.5px] font-semibold text-white bg-emerald-600 hover:bg-emerald-700 flex items-center justify-center gap-2 disabled:opacity-50"
          :disabled="busy || !targetValid"
          @click="move('restock')"
        >
          <Icon name="check-circle" :size="16" /> {{ busy === 'restock' ? t('restock.moving') : t('restock.toShelf') }}
        </button>
        <button
          class="h-11 rounded-xl text-[13.5px] font-semibold text-rose-700 bg-rose-50 ring-1 ring-rose-200 hover:bg-rose-100 flex items-center justify-center gap-2 disabled:opacity-50"
          :disabled="busy"
          @click="move('defective')"
        >
          <Icon name="alert-triangle" :size="16" /> {{ busy === 'defective' ? t('restock.moving') : t('restock.defective') }}
        </button>
      </div>
    </div>

    <!-- Zone contents (skeleton while the live call is in flight) -->
    <div v-if="loadingSummary" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3 space-y-2">
      <div v-for="n in 6" :key="n" class="h-[56px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="summary" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center justify-between">
        <span class="text-[12px] font-semibold text-stone-900">{{ t('restock.zoneTitle') }}</span>
        <span class="text-[11px] text-stone-400 tabular-nums">{{ summary.items }} {{ t('consol.items') }}</span>
      </div>
      <div class="divide-y divide-stone-50 max-h-[420px] overflow-y-auto">
        <button
          v-for="r in summary.rows" :key="r.itemCode"
          class="w-full text-start px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50 transition-colors"
          @click="onScan(r.sku || r.itemCode)"
        >
          <img v-if="r.image" :src="r.image" alt="" loading="lazy" @error="hideImg"
               class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
          <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="14" /></span>
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ r.name }}</div>
            <div class="font-mono text-[10.5px] text-stone-400">{{ r.sku || r.itemCode }}</div>
          </div>
          <span class="text-[12px] font-bold tabular-nums text-stone-800">{{ r.qty }}</span>
          <span class="text-[11.5px] text-stone-500 tabular-nums w-[80px] text-end">{{ fmt(r.value) }} MAD</span>
        </button>
      </div>
    </div>

    <!-- Session log -->
    <div v-if="moved.length" class="bg-white rounded-xl ring-1 ring-emerald-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
        <Icon name="check-circle" :size="14" class="text-emerald-600" />
        <span class="text-[12px] font-semibold text-stone-900">{{ t('restock.movedTitle') }}</span>
      </div>
      <div class="divide-y divide-stone-50">
        <div v-for="m in moved" :key="m.entry" class="px-4 py-2 flex items-center gap-3 text-[12px]">
          <span class="font-mono font-medium text-stone-800">{{ m.itemCode }}</span>
          <span class="tabular-nums font-bold" :class="m.disposition === 'defective' ? 'text-rose-600' : 'text-emerald-600'">×{{ m.qty }}</span>
          <span class="text-stone-500 truncate flex-1">→ {{ m.target }}</span>
          <span class="font-mono text-[10.5px] text-stone-400">{{ m.entry }}</span>
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
const summary = ref(null);
const loadingSummary = ref(true);
const current = ref(null);
const qty = ref(1);
const target = ref("");
const busy = ref("");
const moved = ref([]);

// The move button unlocks only for a shelf the server will accept — the
// backend re-validates anyway, this just keeps the UI honest while typing.
const targetValid = computed(() => {
  if (!target.value) return false;
  if ((current.value?.suggestions || []).some((s) => s.warehouse === target.value)) return true;
  return (summary.value?.targets || []).includes(target.value);
});

async function load() {
  try {
    summary.value = await api("returns.restock_summary");
  } catch (e) {
    warn(t("restock.loadFail"), String(e.message || e));
  } finally {
    loadingSummary.value = false;
  }
}
onMounted(async () => {
  await load();
  scanner.value?.refocus();
});

async function onScan(raw) {
  const code = String(raw || "").trim();
  if (!code) return;
  let res;
  try {
    res = await apiPost("returns.restock_scan", { code });
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
    return;
  }
  if (!res.ok) {
    scanner.value?.showError(
      res.reason === "not_in_zone" ? t("restock.notInZone") : t("pickm.unknown"));
    return;
  }
  current.value = res;
  qty.value = res.inZone;
  target.value = res.suggestions?.[0]?.warehouse || summary.value?.targets?.[0] || "";
  scanner.value?.showSuccess(`${res.name} · ${res.inZone}`);
}

async function move(disposition) {
  if (!current.value || busy.value) return;
  busy.value = disposition;
  try {
    const res = await apiPost("returns.restock_move", {
      item_code: current.value.itemCode,
      qty: qty.value,
      target: disposition === "restock" ? target.value : undefined,
      disposition,
    });
    moved.value.unshift(res);
    success(
      disposition === "defective" ? t("restock.markedDefective") : t("restock.restocked"),
      `${res.itemCode} ×${res.qty} → ${res.target}`,
    );
    current.value = res.remaining > 0
      ? { ...current.value, inZone: res.remaining }
      : null;
    if (current.value) qty.value = current.value.inZone;
    await load();
  } catch (e) {
    warn(t("restock.moveFail"), String(e.message || e));
  } finally {
    busy.value = "";
    scanner.value?.refocus();
  }
}

function clearCurrent() { current.value = null; scanner.value?.refocus(); }
function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }
function fmt(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
</script>
