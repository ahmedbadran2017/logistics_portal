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

      <!-- Labels that arrived AFTER their parcel was sorted (a City-check fix,
           a carrier retry). Nothing flips these to printed silently any more —
           they wait HERE until a human prints and sticks them. -->
      <div v-if="lateLabels.length" class="bg-white rounded-2xl ring-1 ring-rose-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-rose-100 bg-rose-50/50 flex items-center gap-2">
          <Icon name="printer" :size="14" class="text-rose-600" />
          <span class="text-[12.5px] font-bold text-stone-900">{{ t('sort.lateTitle') }}</span>
          <span class="text-[12px] font-bold text-rose-700 tabular-nums">{{ lateLabels.length }}</span>
          <span class="text-[11px] text-stone-500 hidden sm:inline">{{ t('sort.lateHint') }}</span>
        </div>
        <div class="divide-y divide-stone-100">
          <div v-for="r in lateLabels" :key="r.so" class="px-4 py-2.5 flex items-center gap-3">
            <div class="min-w-0 flex-1">
              <span class="font-mono text-[12.5px] font-semibold text-stone-900">{{ r.so }}</span>
              <span class="text-[11.5px] text-stone-500 ms-2 truncate" dir="auto">{{ r.customer }}</span>
              <div class="text-[10.5px] text-stone-400 tabular-nums">AWB {{ r.awb }} · {{ r.pickList }} · {{ Math.round(r.ageMin / 60) }}h</div>
            </div>
            <button class="h-10 px-4 rounded-xl text-[12.5px] font-bold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 flex-shrink-0"
                    :disabled="lateBusy === r.so" @click="printLate(r)">
              <Icon name="printer" :size="13" class="inline -mt-px me-1" />{{ t('sort.latePrint') }}
            </button>
          </div>
        </div>
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
            <span v-if="l.blocked" class="inline-flex items-center gap-1 mt-1 text-[11px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200/70 rounded-md px-1.5 py-0.5">
              <Icon name="alert-triangle" :size="11" />{{ l.blocked }} {{ t('sort.blockedChip') }}
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
          <button :title="t('common.back')" class="w-9 h-9 rounded-lg bg-white ring-1 ring-stone-200 hover:bg-stone-50 flex items-center justify-center flex-shrink-0" @click="closeWall">
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
            <div class="flex items-center gap-2 flex-shrink-0">
              <!-- Two stages: sorted (items scanned) vs printed (the label
                   actually spooled). Blue = sorted but label not confirmed out,
                   green = both done. -->
              <span v-if="o.shipped" class="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-1.5 h-5 rounded-full text-emerald-700 bg-emerald-100 ring-1 ring-emerald-300">
                <Icon name="truck" :size="10" />{{ t('sort.badgeShipped') }}
              </span>
              <span v-else-if="o.printed" class="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-1.5 h-5 rounded-full text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200">
                <Icon name="printer" :size="10" />{{ t('sort.badgePrinted') }}
              </span>
              <span v-else-if="o.done && o.labelUrl" class="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-1.5 h-5 rounded-full text-sky-700 bg-sky-50 ring-1 ring-sky-200">
                <Icon name="check" :size="10" />{{ t('sort.badgeSorted') }}
              </span>
              <span class="text-[14px] font-bold tabular-nums"
                    :class="o.printed ? 'text-emerald-600' : o.done ? 'text-sky-600' : 'text-stone-800'">
                {{ o.sorted }}/{{ o.qty }}
              </span>
            </div>
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
            v-if="o.done && o.labelUrl && !o.shipped"
            class="mt-2.5 w-full h-9 rounded-lg text-[12.5px] font-semibold flex items-center justify-center gap-1.5 transition-colors"
            :class="o.printed ? 'bg-white text-stone-600 ring-1 ring-stone-200 hover:bg-stone-50' : 'bg-sky-600 text-white hover:bg-sky-700'"
            @click="printAndMark(o)"
          >
            <Icon name="printer" :size="14" /> {{ o.printed ? t('sort.printAgain') : t('sort.printNow') }}
          </button>
          <div v-else-if="o.noLabel || showFix(o)" class="mt-2.5 space-y-1.5">
            <div class="flex items-start gap-2 rounded-lg bg-amber-50 ring-1 ring-amber-200/70 px-3 py-2 text-[11.5px] text-amber-800">
              <Icon name="alert-triangle" :size="14" class="text-amber-500 shrink-0 mt-0.5" />
              <span>{{ t('sort.noLabelHint') }}</span>
            </div>
            <!-- The AWB often lands MINUTES late — give the sorter a way to
                 claim it without rescanning (which says 'already sorted'). -->
            <button
              class="w-full h-9 rounded-lg text-[12.5px] font-semibold bg-amber-600 text-white hover:bg-amber-700 flex items-center justify-center gap-1.5 disabled:opacity-50"
              :disabled="o.rechecking"
              @click="recheckLabel(o)"
            >
              <Icon name="refresh-cw" :size="14" /> {{ o.rechecking ? t('sort.rechecking') : t('sort.recheck') }}
            </button>

            <!-- The hint above has always told the dispatcher to fix the city
                 and retry the AWB. Until now there was no way to do either from
                 here, so the parcel just stood in dispatch. -->
            <div v-if="canFix" class="rounded-lg ring-1 ring-stone-200 bg-stone-50/70 p-2 space-y-1.5">
              <div class="text-[11px] text-stone-500">
                {{ t('sort.cityNow') }}
                <span class="font-semibold text-stone-700">{{ o.city || t('sort.cityEmpty') }}</span>
              </div>
              <div v-if="o.citySuggests?.length" class="flex flex-wrap gap-1">
                <button
                  v-for="c in o.citySuggests" :key="c"
                  class="text-[11.5px] rounded-md px-2 h-7 ring-1 transition-colors"
                  :class="o.cityPick === c ? 'bg-sky-600 text-white ring-sky-600' : 'bg-white text-stone-700 ring-stone-200 hover:bg-stone-50'"
                  @click="o.cityPick = (o.cityPick === c ? '' : c)"
                >{{ c }}</button>
              </div>
              <div v-else-if="o.cityExact" class="text-[11px] text-emerald-700">{{ t('sort.cityOk') }}</div>
              <!-- The carrier's own words. Without these the panel offers a
                   city picker for a parcel whose real problem is a foreign
                   phone number or a missing address. -->
              <div v-if="o.why?.length" class="rounded-md bg-rose-50 ring-1 ring-rose-200/70 px-2 py-1.5 space-y-0.5">
                <div class="text-[10.5px] font-semibold text-rose-700">{{ t('sort.carrierSaid') }}</div>
                <div v-for="(w, i) in o.why" :key="i" class="text-[11px] text-rose-800 break-words">{{ w }}</div>
              </div>
              <input
                v-model="o.cityTyped" type="text" :placeholder="t('sort.cityOther')"
                class="w-full h-8 rounded-md ring-1 ring-stone-200 px-2 text-[12px] focus:outline-none focus:ring-[var(--accent-400)]"
              />
              <button
                class="w-full h-9 rounded-lg text-[12.5px] font-semibold bg-stone-900 text-white hover:bg-stone-800 flex items-center justify-center gap-1.5 disabled:opacity-50"
                :disabled="o.fixing"
                @click="fixAndLabel(o)"
              >
                <Icon name="send" :size="14" />
                {{ o.fixing ? t('sort.fixing') : ((o.cityPick || o.cityTyped) ? t('sort.fixCityAndLabel') : t('sort.makeLabel')) }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Multi-piece guard ──────────────────────────────────────────────
           A one-line toast under the scanner is the wrong weight for an order
           that is not finished: the sorter reads "2/3", takes it for a count of
           what they just did, tapes the box and moves on. A parcel that leaves
           short is worse than one that waits, so a multi-piece order stops the
           wall and says exactly which pieces are still owed. It clears itself
           on the next scan — no button to hunt for mid-flow. -->
      <div
        v-if="pending"
        class="fixed inset-0 z-40 flex items-end sm:items-center justify-center bg-stone-900/40 px-4 pb-4 sm:pb-0"
        @click.self="pending = null"
      >
        <div class="w-full max-w-sm bg-white rounded-2xl ring-1 ring-stone-200 shadow-xl p-4 space-y-3">
          <div class="flex items-center gap-2.5">
            <span class="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0">
              <Icon name="layers" :size="17" />
            </span>
            <div class="min-w-0">
              <div class="font-mono text-[13.5px] font-bold text-stone-900 truncate">{{ pending.order }}</div>
              <div class="text-[11.5px] text-stone-500">{{ t('sort.stillMissing') }}</div>
            </div>
            <span class="ms-auto text-[15px] font-bold tabular-nums text-amber-600">
              {{ pending.sorted }}/{{ pending.qty }}
            </span>
          </div>
          <div class="space-y-1.5">
            <div v-for="it in pending.items" :key="it.itemCode"
                 class="flex items-center gap-2.5 rounded-lg px-2 py-1.5"
                 :class="it.sorted >= it.qty ? 'bg-emerald-50/60' : 'bg-amber-50/60 ring-1 ring-amber-200/60'">
              <img v-if="it.image" :src="it.image" alt="" loading="lazy" @error="onImgError"
                   class="w-9 h-9 rounded-lg object-cover ring-1 ring-stone-200 bg-white flex-shrink-0" />
              <span v-else class="w-9 h-9 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="14" /></span>
              <div class="min-w-0 flex-1">
                <div class="text-[11.5px] font-medium text-stone-800 truncate">{{ it.name }}</div>
                <div class="font-mono text-[10.5px] text-stone-400">{{ it.sku || it.itemCode }}</div>
              </div>
              <span class="text-[12.5px] font-bold tabular-nums flex-shrink-0"
                    :class="it.sorted >= it.qty ? 'text-emerald-600' : 'text-amber-700'">
                {{ it.sorted }}/{{ it.qty }}
              </span>
            </div>
          </div>
          <div class="text-[11.5px] text-stone-500">{{ t('sort.scanToContinue') }}</div>
          <button class="w-full h-9 rounded-lg text-[12.5px] font-semibold bg-stone-100 text-stone-700 hover:bg-stone-200"
                  @click="pending = null">{{ t('common.close') }}</button>
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
import { useAuth } from "@/composables/useAuth";

const { t } = useI18n();
const { success, warn } = useToast();
const { role } = useAuth();

// The sorter holding the unlabelled parcel is the one who should be able to fix
// it. Restricting this to dispatch meant the person at the wall could see the
// carrier's refusal and do nothing about it. Matches relabel_order's gate.
const FIX_ROLES = ["packer", "dispatcher", "manager"];
const canFix = computed(() => FIX_ROLES.includes(role.value));

const scanner = ref(null);
const lists = ref([]);
const loadingLists = ref(true);
const wall = ref(null);          // {pickList, orders:[...]} — the open tote
const printedToday = ref(0);
const flash = ref("");           // order slot to pulse after a scan
const pending = ref(null);       // multi-piece order the sorter must finish

// Hold the repair panel back for a few minutes on a parcel that is merely
// waiting: the AWB normally lands within a minute or two of the pick list, and
// dressing a normal in-flight parcel up as a failure teaches the floor to
// ignore the flag. The ones that actually strand sit for hours.
const AWB_GRACE_MIN = 20;
function showFix(o) {
  return !!(o.awbMissing && !o.printed && (wall.value?.ageMin || 0) >= AWB_GRACE_MIN);
}

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
  loadLateLabels();
  await loadLists();
  scanner.value?.refocus();
});

// Orders that load already 'Label Printed' were printed in an earlier session —
// show them green, not blue. Fresh completions get `printed` from afterprint.
function normalizeWall(w) {
  if (w && w.orders) w.orders.forEach((o) => {
    // Anything at or past the label stage is printed — parcels can leave the
    // building (Shipped / Out For Delivery / Delivered) while this screen is
    // open, and they were rendering as merely-SORTED (PL-54797).
    o.shipped = ["Shipped", "Delivered"].includes(o.status);
    o.printed = o.status === "Label Printed" || o.shipped;
    o.cityPick = "";
    o.cityTyped = "";
    o.citySuggests = null;
    o.cityExact = "";
    o.why = null;
    o.fixing = false;
  });
  return w;
}

// Which carrier city could this address have meant? Asked only for the slots
// that actually need repairing, so a clean wall makes no extra calls.
async function loadSuggests(o) {
  if (o.citySuggests || !canFix.value) return;
  try {
    const res = await api("city.suggest_city", { order: o.order });
    o.citySuggests = res?.suggestions || [];
    o.cityExact = res?.exact || "";
    if (o.citySuggests.length === 1) o.cityPick = o.citySuggests[0];
  } catch (e) {
    o.citySuggests = [];
  }
}

function primeFixes() {
  (wall.value?.orders || []).forEach((o) => {
    if (o.noLabel || showFix(o)) loadSuggests(o);
  });
}

async function openWall(name) {
  try {
    wall.value = normalizeWall(await api("picking.sorting_detail", { pick_list: name }));
    primeFixes();
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
    wall.value = normalizeWall(await api("picking.sorting_detail", { pick_list: code }));
    primeFixes();
  } catch (e) {
    scanner.value?.showError(t("sort.unknownList"));
  }
}

// View-2 scan: allocate one unit to its order on THIS list.
async function onScanItem(raw) {
  const code = String(raw || "").trim();
  if (!code || !wall.value) return;
  // Any scan dismisses the guard — the sorter's hands are on the scanner, not
  // the screen, and a modal that swallows scans is worse than no modal.
  if (pending.value) pending.value = null;
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
    if (res.orderComplete && res.noLabel) {
      // Items all sorted but the parcel has no carrier label — don't print,
      // flag it so a dispatcher fixes the city / retries the AWB.
      o.done = true;
      o.noLabel = true;
      pending.value = null;
      loadSuggests(o);
      warn(t("sort.noLabel"), o.order);
    } else if (res.orderComplete) {
      // Stage 1: sorted (slot goes blue). Stage 2: printed — set only when the
      // browser confirms the label spooled (afterprint), turning it green.
      o.done = true;
      o.labelUrl = res.labelUrl || o.labelUrl;
      if (o.labelUrl) printLabel(o.order, () => { o.printed = true; printedToday.value += 1; });
      pending.value = null;
      success(t("sort.orderDone"), o.order);
    } else if (o.qty > 1) {
      // More pieces owed on this order. Show them — the toast alone is what
      // lets a short parcel get taped shut.
      pending.value = o;
      scanner.value?.refocus();
    } else {
      pending.value = null;
      scanner.value?.showSuccess(`${o.order} · ${o.sorted}/${o.qty}`);
    }
  }
  if (wall.value.orders.every((x) => x.done)) {
    success(t("sort.wallDone"), wall.value.pickList);
  }
}

// The manual print button must ALSO move the order to 'Label Printed': the
// scan-time flip only fires when the label already exists at sort completion,
// so late-label orders printed from this button were staying at 'Label
// Generated' forever (Anas, 2026-08-27). mark_packed is idempotent and only
// upgrades eligible statuses — safe to call on every print/reprint.
async function printAndMark(o) {
  printLabel(o.order, () => { o.printed = true; });
  try {
    const res = await apiPost("picking.mark_packed", { order: o.order });
    o.status = "Label Printed";
    if (res.labelUrl) o.labelUrl = res.labelUrl;
  } catch (e) {
    warn(t("sort.statusStuck"), String(e.message || e));
  }
}

// Correct the city if the dispatcher chose one, then actually create the AWB
// from the parcel's existing delivery note. Everything before this shipped a
// diagnosis and no cure: the hint told a dispatcher to fix the city and retry,
// while the only button re-read a label that was never going to arrive.
async function fixAndLabel(o) {
  const city = (o.cityTyped || "").trim() || o.cityPick || "";
  o.fixing = true;
  try {
    const res = await apiPost("picking.relabel_order", {
      pick_list: wall.value.pickList, order: o.order, city: city || undefined,
    });
    if (res.ok) {
      o.noLabel = false;
      o.awbMissing = false;
      o.awb = res.awb || o.awb;
      o.labelUrl = res.labelUrl || o.labelUrl;
      o.status = "Label Generated";
      if (res.cityChanged) o.city = res.cityChanged;
      if (o.labelUrl) printLabel(o.order, () => { o.printed = true; printedToday.value += 1; });
      success(t("sort.labelArrived"), o.order);
    } else {
      // Say what the carrier said. A generic failure here sends the parcel
      // back to the shelf it just came from.
      o.why = res.why || [];
      warn(t("sort.carrierRefused"), (res.why && res.why[0]) || res.error || o.order);
    }
  } catch (e) {
    warn(t("sort.stillNoLabel"), String(e.message || e));
  } finally {
    o.fixing = false;
    scanner.value?.refocus();
  }
}

// Late AWB recovery: re-read the order; if the label landed since the sort
// completed, flip it and print — no rescan (which would say "already sorted").
async function recheckLabel(o) {
  o.rechecking = true;
  try {
    const res = await apiPost("picking.recheck_label", {
      pick_list: wall.value.pickList, order: o.order,
    });
    if (res.ok) {
      o.noLabel = false;
      o.labelUrl = res.labelUrl || o.labelUrl;
      o.status = "Label Printed";
      if (o.labelUrl) printLabel(o.order, () => { o.printed = true; printedToday.value += 1; });
      success(t("sort.labelArrived"), o.order);
    } else {
      warn(t("sort.stillNoLabel"), o.order);
    }
  } catch (e) {
    warn(t("sort.stillNoLabel"), String(e.message || e));
  } finally {
    o.rechecking = false;
    scanner.value?.refocus();
  }
}

function slotClass(o) {
  if (flash.value === o.order) return "ring-2 ring-[var(--accent-500)] shadow-md";
  if (o.noLabel) return "ring-amber-300 bg-amber-50/40";
  if (o.printed) return "ring-emerald-300 bg-emerald-50/30";       // both stages done
  if (o.done) return "ring-sky-300 bg-sky-50/40";                  // sorted, label not confirmed out
  return "ring-stone-200/70";
}

function onImgError(e) { if (e && e.target) e.target.style.display = "none"; }

// Auto-print the parcel label. The carrier label is saved as a private File on
// the order; we stream it through picking.label_pdf, i.e. from the portal's OWN
// origin. That matters: the raw label URL is on the carrier (cross-origin), and
// a browser refuses to print a cross-origin iframe — the old code's print()
// threw and fell back to window.open, which a post-scan callback gets popup-
// blocked, so nothing printed. Same-origin, print() actually reaches the
// browser; whether a dialog shows is the station's own print setting.
// `onSpooled` fires when the browser's afterprint event confirms the job was
// sent to the printer — the automatic "label out" signal that turns the slot
// green. If print() throws (printer offline etc.) we fall back to a tab and
// never call it, so the slot stays blue and the failure is visible.
// ── late labels: the parcels whose label came after sorting ──────────────
const lateLabels = ref([]);
const lateBusy = ref("");
async function loadLateLabels() {
  try {
    const res = await api("picking.late_labels");
    lateLabels.value = res.rows || [];
  } catch { lateLabels.value = []; }
}
async function printLate(r) {
  lateBusy.value = r.so;
  try {
    const res = await apiPost("picking.recheck_label", {
      pick_list: r.pickList, order: r.so,
    });
    if (res.ok) {
      printLabel(r.so, () => { printedToday.value += 1; });
      lateLabels.value = lateLabels.value.filter((x) => x.so !== r.so);
      success(t("sort.labelArrived"), r.so);
    } else {
      warn(t("sort.stillNoLabel"), r.so);
    }
  } catch (e) {
    warn(t("sort.stillNoLabel"), String(e.message || e));
  } finally {
    lateBusy.value = "";
  }
}

function printLabel(order, onSpooled) {
  if (!order) return;
  const url = `/api/method/logistics_portal.api.picking.label_pdf?order=${encodeURIComponent(order)}`;
  try {
    let f = document.getElementById("lp-print-frame");
    if (!f) { f = document.createElement("iframe"); f.id = "lp-print-frame"; f.style.display = "none"; document.body.appendChild(f); }
    f.onload = () => {
      const w = f.contentWindow;
      try {
        if (onSpooled) {
          const done = () => { w.removeEventListener("afterprint", done); onSpooled(); };
          w.addEventListener("afterprint", done);
        }
        w.focus();
        w.print();
      } catch (e) { window.open(url, "_blank"); }
    };
    f.src = url;
  } catch (e) { window.open(url, "_blank"); }
}
</script>
