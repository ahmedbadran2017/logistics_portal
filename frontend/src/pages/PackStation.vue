<template>
  <div class="max-w-[1000px] mx-auto px-4 py-6 space-y-4">
    <!-- ══════════════ View 1: pick a tote (pick list) ══════════════ -->
    <template v-if="!wall">
      <header class="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('sort.title') }}</h1>
          <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('sort.intro') }}</p>
        </div>
        <span class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200/70 rounded-lg px-2.5 h-8 tabular-nums">
          <Icon name="check-circle" :size="14" />{{ printedToday }} {{ t('sort.printedToday') }}
        </span>
      </header>

      <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
        <ScanInput ref="scanner" :placeholder="t('sort.scanList')" @scan="onScanList" />
      </div>

      <div v-if="loadingLists" class="space-y-2.5">
        <div v-for="n in 3" :key="n" class="h-[76px] rounded-2xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
      </div>
      <div v-else-if="!lists.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-10 text-center">
        <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-600 mb-3"><Icon name="check-circle" :size="22" /></span>
        <div class="text-[15px] font-semibold text-stone-900">{{ t('sort.noLists') }}</div>
        <div class="text-[12.5px] text-stone-500 mt-1">{{ t('sort.noListsHint') }}</div>
      </div>
      <div v-else class="space-y-2.5">
        <button
          v-for="l in lists" :key="l.name"
          class="w-full bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 flex items-center gap-4 text-start hover:ring-[var(--accent-400)] hover:shadow-sm transition-all"
          @click="openWall(l.name)"
        >
          <span class="w-10 h-10 rounded-xl bg-[var(--accent-50)] text-[var(--accent-600)] flex items-center justify-center flex-shrink-0">
            <Icon name="package" :size="18" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block font-mono text-[14px] font-bold text-stone-900">{{ l.name }}</span>
            <span class="block text-[12px] text-stone-500 mt-0.5">
              {{ l.picker }} · {{ l.orders }} {{ t('ordersPg.blOrders') }} · {{ l.qty }} {{ t('consol.items') }}
            </span>
          </span>
          <span class="flex flex-col items-end gap-1 flex-shrink-0">
            <span class="text-[12.5px] font-bold tabular-nums" :class="l.printed ? 'text-emerald-600' : 'text-stone-400'">
              {{ l.printed }}/{{ l.orders }}
            </span>
            <span class="w-24 h-1.5 rounded-full bg-stone-100 overflow-hidden">
              <span class="block h-full rounded-full bg-emerald-500" :style="{ width: (l.orders ? l.printed / l.orders * 100 : 0) + '%' }" />
            </span>
          </span>
          <Icon name="chevron-right" :size="15" class="text-stone-300 rtl:rotate-180 flex-shrink-0" />
        </button>
      </div>
    </template>

    <!-- ══════════════ View 2: the sort wall ══════════════ -->
    <template v-else>
      <header class="flex items-center justify-between gap-3 flex-wrap">
        <div class="flex items-center gap-3 min-w-0">
          <button class="w-9 h-9 rounded-lg bg-white ring-1 ring-stone-200 hover:bg-stone-50 flex items-center justify-center flex-shrink-0" @click="closeWall">
            <Icon name="chevron-left" :size="16" class="rtl:rotate-180" />
          </button>
          <div class="min-w-0">
            <h1 class="font-mono text-[17px] font-bold text-stone-900 truncate">{{ wall.pickList }}</h1>
            <p class="text-[12px] text-stone-500">{{ t('sort.wallHint') }}</p>
          </div>
        </div>
        <span class="inline-flex items-center gap-1.5 text-[12.5px] font-bold tabular-nums px-3 h-9 rounded-lg ring-1"
              :class="doneCount === wall.orders.length ? 'text-emerald-700 bg-emerald-50 ring-emerald-200' : 'text-stone-700 bg-white ring-stone-200'">
          {{ doneCount }}/{{ wall.orders.length }} {{ t('sort.ordersDone') }}
        </span>
      </header>

      <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 sticky top-2 z-10 shadow-sm">
        <ScanInput ref="scanner" :placeholder="t('sort.scanItem')" @scan="onScanItem" />
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div
          v-for="o in wall.orders" :key="o.order"
          class="bg-white rounded-2xl ring-1 p-3.5 transition-all"
          :class="slotClass(o)"
        >
          <div class="flex items-center justify-between gap-2 pb-2.5 mb-2.5 border-b border-stone-100">
            <div class="min-w-0">
              <span class="font-mono text-[13.5px] font-bold text-stone-900">{{ o.order }}</span>
              <span class="block text-[11.5px] text-stone-500 truncate">{{ o.customer }}<span v-if="o.city" class="capitalize"> · {{ o.city }}</span></span>
            </div>
            <span class="text-[14px] font-bold tabular-nums flex-shrink-0" :class="o.done ? 'text-emerald-600' : 'text-stone-800'">
              {{ o.sorted }}/{{ o.qty }}
            </span>
          </div>
          <div class="space-y-1.5">
            <div v-for="it in o.items" :key="it.itemCode" class="flex items-center gap-2.5">
              <img v-if="it.image" :src="it.image" alt="" loading="lazy" @error="onImgError"
                   class="w-9 h-9 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
              <span v-else class="w-9 h-9 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="14" /></span>
              <div class="min-w-0 flex-1">
                <div class="text-[11.5px] font-medium text-stone-800 truncate">{{ it.name }}</div>
                <div class="font-mono text-[10.5px] text-stone-400">{{ it.sku || it.itemCode }}</div>
              </div>
              <span class="text-[12px] font-bold tabular-nums" :class="it.sorted >= it.qty ? 'text-emerald-600' : 'text-stone-600'">{{ it.sorted }}/{{ it.qty }}</span>
            </div>
          </div>
          <button
            v-if="o.done && o.labelUrl"
            class="mt-2.5 w-full h-9 rounded-lg text-[12.5px] font-semibold flex items-center justify-center gap-1.5 bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
            @click="printLabel(o.labelUrl)"
          >
            <Icon name="printer" :size="14" /> {{ t('sort.printAgain') }}
          </button>
        </div>
      </div>
    </template>
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
const lists = ref([]);
const loadingLists = ref(true);
const wall = ref(null);          // {pickList, orders:[...]} — the open tote
const printedToday = ref(0);
const flash = ref("");           // order slot to pulse after a scan

const doneCount = computed(() => (wall.value?.orders || []).filter((o) => o.done).length);

async function loadLists() {
  loadingLists.value = true;
  try {
    lists.value = (await api("picking.sorting_lists")) || [];
  } catch (e) {
    warn(t("sort.loadFail"), String(e.message || e));
  } finally {
    loadingLists.value = false;
  }
}
onMounted(async () => {
  await loadLists();
  scanner.value?.refocus();
});

async function openWall(name) {
  try {
    wall.value = await api("picking.sorting_detail", { pick_list: name });
    scanner.value?.refocus();
  } catch (e) {
    warn(t("sort.loadFail"), String(e.message || e));
  }
}
function closeWall() {
  wall.value = null;
  loadLists();
}

// View-1 scan: a pick-list id opens its wall directly.
async function onScanList(raw) {
  const code = String(raw || "").trim();
  if (!code) return;
  const hit = lists.value.find((l) => l.name.toLowerCase() === code.toLowerCase());
  if (hit) return openWall(hit.name);
  // Maybe an older list not in the window — try it anyway.
  try {
    wall.value = await api("picking.sorting_detail", { pick_list: code });
  } catch (e) {
    scanner.value?.showError(t("sort.unknownList"));
  }
}

// View-2 scan: allocate one unit to its order on THIS list.
async function onScanItem(raw) {
  const code = String(raw || "").trim();
  if (!code || !wall.value) return;
  let res;
  try {
    res = await apiPost("picking.sort_scan", { pick_list: wall.value.pickList, code });
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
    return;
  }
  if (!res.ok) {
    scanner.value?.showError(
      res.reason === "not_on_list" ? t("sort.notOnList")
        : res.reason === "done" ? t("sort.itemDone")
          : t("pack.unknown"));
    return;
  }
  // Update the slot locally.
  const o = wall.value.orders.find((x) => x.order === res.order);
  if (o) {
    const it = o.items.find((x) => x.itemCode === res.itemCode && x.sorted < x.qty)
      || o.items.find((x) => x.itemCode === res.itemCode);
    if (it) it.sorted = Math.min(it.sorted + 1, it.qty);
    o.sorted = o.items.reduce((a, x) => a + x.sorted, 0);
    flash.value = o.order;
    setTimeout(() => { if (flash.value === o.order) flash.value = ""; }, 900);
    if (res.orderComplete) {
      o.done = true;
      o.labelUrl = res.labelUrl || o.labelUrl;
      printedToday.value += 1;
      printLabel(o.labelUrl);
      success(t("sort.orderDone"), o.order);
    } else {
      scanner.value?.showSuccess(`${o.order} · ${o.sorted}/${o.qty}`);
    }
  }
  if (wall.value.orders.every((x) => x.done)) {
    success(t("sort.wallDone"), wall.value.pickList);
  }
}

function slotClass(o) {
  if (flash.value === o.order) return "ring-2 ring-[var(--accent-500)] shadow-md";
  if (o.done) return "ring-emerald-300 bg-emerald-50/30";
  return "ring-stone-200/70";
}

function onImgError(e) { if (e && e.target) e.target.style.display = "none"; }

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
</script>
