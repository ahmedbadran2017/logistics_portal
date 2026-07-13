<template>
  <div class="max-w-[900px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('recv.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">
          {{ t('recv.intro') }}<span v-if="state" class="font-mono font-semibold text-stone-700"> · {{ state.batch }}</span>
        </p>
      </div>
      <div v-if="state" class="flex items-center gap-2 flex-wrap">
        <span class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 rounded-lg px-2.5 h-8 tabular-nums">
          <Icon name="truck" :size="14" class="text-stone-400" />{{ state.orders }} {{ t('recv.parcels') }}
        </span>
        <span class="inline-flex items-center gap-1.5 text-[12px] font-semibold rounded-lg px-2.5 h-8 tabular-nums ring-1"
              :class="state.missing > 0 ? 'text-amber-700 bg-amber-50 ring-amber-200' : 'text-emerald-700 bg-emerald-50 ring-emerald-200'">
          {{ state.actual }}/{{ state.ordered }} {{ t('recv.units') }}
        </span>
      </div>
    </header>

    <!-- Scanner -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 sticky top-2 z-10 shadow-sm">
      <ScanInput ref="scanner" :placeholder="t('recv.scanPh')" @scan="onScan" />
      <div class="mt-1.5 text-[11px] text-stone-400">{{ t('recv.scanHint') }}</div>
    </div>

    <!-- Load failed -->
    <div v-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-rose-50 text-rose-600 mb-3"><Icon name="alert-circle" :size="22" /></span>
      <div class="text-[14.5px] font-semibold text-stone-900">{{ t('recv.loadFail') }}</div>
      <div class="text-[12px] text-stone-500 mt-1 font-mono">{{ loadError }}</div>
      <button class="mt-4 h-9 px-4 rounded-lg text-[13px] font-semibold text-white bg-stone-800 hover:bg-stone-700" @click="boot">
        {{ t('common.refresh') }}
      </button>
    </div>

    <!-- Loading -->
    <div v-else-if="!state" class="space-y-2.5">
      <div v-for="n in 3" :key="n" class="h-[70px] rounded-2xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
    </div>

    <template v-else>
      <!-- Empty -->
      <div v-if="!state.parcels.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-10 text-center">
        <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-[var(--accent-50)] text-[var(--accent-600)] mb-3"><Icon name="rotate-ccw" :size="22" /></span>
        <div class="text-[15px] font-semibold text-stone-900">{{ t('recv.emptyTitle') }}</div>
        <div class="text-[12.5px] text-stone-500 mt-1 max-w-sm mx-auto">{{ t('recv.emptyHint') }}</div>
      </div>

      <!-- Parcels -->
      <div v-else class="space-y-2">
        <div
          v-for="p in state.parcels" :key="p.awb || p.dn"
          class="bg-white rounded-xl ring-1 px-4 py-3 transition-all"
          :class="flash === (p.awb || p.dn) ? 'ring-2 ring-[var(--accent-500)] shadow-md'
            : p.done ? 'ring-emerald-200 bg-emerald-50/30' : 'ring-stone-200/70'"
        >
          <div class="flex items-center gap-3">
            <Icon :name="p.done ? 'check-circle' : 'package'" :size="16"
                  :class="p.done ? 'text-emerald-500' : 'text-stone-400'" class="flex-shrink-0" />
            <div class="min-w-0 flex-1">
              <span class="font-mono text-[13px] font-bold text-stone-900">{{ p.awb || p.dn }}</span>
              <span class="text-[11px] text-stone-400 ms-2">{{ p.dn }}</span>
            </div>
            <span class="text-[13px] font-bold tabular-nums flex-shrink-0"
                  :class="p.done ? 'text-emerald-600' : 'text-stone-800'">{{ p.actual }}/{{ p.ordered }}</span>
          </div>
          <div v-if="!p.done" class="flex flex-wrap gap-1.5 mt-2 ps-7">
            <span v-for="it in p.items" :key="it.sku"
                  class="inline-flex items-center gap-1 text-[10.5px] font-medium rounded-md px-1.5 py-0.5 ring-1 font-mono"
                  :class="it.complete ? 'text-emerald-700 bg-emerald-50 ring-emerald-200/60' : 'text-stone-600 bg-stone-50 ring-stone-200'">
              {{ it.sku }} <span class="font-bold tabular-nums">{{ it.actual }}/{{ it.ordered }}</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Close batch -->
      <div v-if="state.parcels.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
        <div v-if="state.missing > 0" class="flex items-center gap-2 text-[12.5px] text-amber-700 bg-amber-50 ring-1 ring-amber-200/70 rounded-lg px-3 py-2 mb-3">
          <Icon name="alert-triangle" :size="14" class="flex-shrink-0" />
          {{ t('recv.missingWarn').replace('{n}', state.missing) }}
        </div>
        <button
          class="w-full h-11 rounded-xl text-[14px] font-semibold text-white flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          :class="confirmClose ? 'bg-rose-600 hover:bg-rose-700' : 'bg-emerald-600 hover:bg-emerald-700'"
          :disabled="closing"
          @click="onClose"
        >
          <Icon name="check-circle" :size="16" />
          {{ closing ? t('recv.closing') : confirmClose ? t('recv.closeConfirm') : t('recv.closeBtn') }}
        </button>
        <div class="text-[11px] text-stone-400 text-center mt-2">{{ t('recv.closeHint') }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const scanner = ref(null);
const state = ref(null);
const flash = ref("");
const closing = ref(false);
const confirmClose = ref(false);

const loadError = ref("");

async function boot() {
  loadError.value = "";
  try {
    state.value = await api("returns.open_batch");
  } catch (e) {
    loadError.value = String(e.message || e);
  }
  scanner.value?.refocus();
}
onMounted(boot);

async function onScan(raw) {
  const code = String(raw || "").trim();
  if (!code || !state.value || closing.value) return;
  confirmClose.value = false;
  let res;
  try {
    res = await apiPost("returns.receive_scan", { batch: state.value.batch, code });
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
    return;
  }
  if (!res.ok) {
    scanner.value?.showError(
      res.reason === "in_other_batch" ? t("recv.inOtherBatch").replace("{b}", res.batch)
        : res.message || t("recv.unknown"));
    return;
  }
  state.value = res.state;
  if (res.kind === "awb") {
    flash.value = code;
    scanner.value?.showSuccess(res.single ? t("recv.parcelSingle") : `${res.dn}`);
  } else {
    scanner.value?.showSuccess(`${res.sku} · ${res.actual}/${res.ordered}`);
    if (res.allComplete) success(t("recv.allComplete"), state.value.batch);
  }
  setTimeout(() => { flash.value = ""; }, 900);
}

async function onClose() {
  if (!confirmClose.value) {
    confirmClose.value = true;
    setTimeout(() => { confirmClose.value = false; }, 5000);
    return;
  }
  closing.value = true;
  try {
    const res = await apiPost("returns.close_batch", { batch: state.value.batch });
    success(t("recv.closed"), `${res.batch} · ${res.salesReturns} ${t("recv.salesReturns")}`);
    state.value = null;
    confirmClose.value = false;
    state.value = await api("returns.open_batch");
  } catch (e) {
    warn(t("recv.closeFail"), String(e.message || e));
  } finally {
    closing.value = false;
    scanner.value?.refocus();
  }
}
</script>
