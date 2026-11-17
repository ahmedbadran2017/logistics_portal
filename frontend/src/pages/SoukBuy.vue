<template>
  <!-- Souk buying, on the buyer's phone in the market. A NEW product is born
       as a Shopify Draft (vendor = our house brand by category), its Next
       items come from the sync, and a PO on the stall is paid from the
       custody. BUY AGAIN is a PO only. Backend: souk.create_buy / finish_buy /
       create_rebuy. The form is kept on the phone until it is sent. -->
  <div class="max-w-[520px] mx-auto px-4 pt-4 pb-40 space-y-4">
    <header class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="text-[11.5px] font-semibold text-stone-500">
          {{ boot?.trip ? t('souk.tripOf').replace('{place}', boot.trip.place) : t('souk.title') }}
        </div>
        <h1 class="text-[18px] font-bold text-stone-900">{{ t('souk.buyTitle') }}</h1>
      </div>
      <router-link :to="{ name: 'SoukTrip' }"
                   class="shrink-0 h-9 px-3 rounded-lg bg-stone-900 text-white text-[12.5px] font-bold inline-flex items-center gap-1.5 tabular-nums">
        <Icon name="wallet" :size="14" />{{ boot?.trip ? fmt(boot.trip.expected) + ' MAD' : t('souk.custody') }}
      </router-link>
    </header>

    <div v-if="loading" class="h-[320px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <div v-else-if="boot && !boot.trip" class="bg-amber-50 ring-1 ring-amber-200 rounded-2xl p-5 text-[13px] text-amber-900 leading-relaxed">
      {{ t('souk.noTrip') }}
    </div>

    <!-- done -->
    <section v-else-if="done" class="space-y-3">
      <div class="bg-emerald-50 ring-1 ring-emerald-200 rounded-2xl p-4 space-y-1">
        <div class="text-[15px] font-bold text-emerald-900">{{ done.again ? t('souk.rebuyDone') : t('souk.buyDone') }}</div>
        <div v-if="!done.again" class="text-[12.5px] text-emerald-800">{{ t('souk.draftOn').replace('{brand}', done.brand) }}</div>
        <div class="text-[12.5px] text-emerald-800 font-mono">{{ done.po }}<span v-if="done.pi"> · {{ done.pi }}</span></div>
      </div>
      <div v-if="done.variants?.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl divide-y divide-stone-100">
        <div v-for="v in done.variants" :key="v.sku" class="px-4 py-2 flex items-center justify-between text-[12.5px]">
          <span class="font-mono font-bold text-stone-900">{{ v.sku }}</span>
          <span class="text-stone-500 tabular-nums">{{ v.qty }} × {{ v.cost }} MAD</span>
        </div>
      </div>
      <div class="bg-stone-900 text-white rounded-2xl p-4 flex items-center justify-between">
        <span class="text-[12.5px] text-stone-300">{{ t('souk.leftWithYou') }}</span>
        <span class="text-[20px] font-extrabold tabular-nums">{{ fmt(done.left) }} MAD</span>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <button class="h-12 rounded-xl bg-white ring-1 ring-stone-300 text-[13px] font-bold" @click="reset">{{ t('souk.another') }}</button>
        <router-link :to="{ name: 'SoukTrip' }" class="h-12 rounded-xl bg-stone-900 text-white text-[13px] font-bold inline-flex items-center justify-center">{{ t('souk.toTrip') }}</router-link>
      </div>
    </section>

    <!-- waiting for Shopify / Next -->
    <section v-else-if="pendingName" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-5 space-y-3 text-center">
      <div class="text-[14px] font-bold text-stone-900">{{ pendingName }}</div>
      <p class="text-[12.5px] text-stone-600">{{ pendingError ? t('souk.stuck') : t('souk.creating') }}</p>
      <p v-if="pendingError" class="text-[12px] text-rose-700 font-mono break-words">{{ pendingError }}</p>
      <button class="h-11 px-5 rounded-xl bg-stone-900 text-white text-[13px] font-bold disabled:opacity-40" :disabled="busy" @click="poll(true)">
        {{ t('souk.retry') }}
      </button>
    </section>

    <template v-else-if="boot">
      <!-- tabs -->
      <div class="grid grid-cols-2 bg-stone-100 rounded-xl p-1 text-[13px] font-bold">
        <button class="h-10 rounded-lg" :class="tab === 'new' ? 'bg-white shadow-sm text-stone-900' : 'text-stone-500'" @click="tab = 'new'">{{ t('souk.tabNew') }}</button>
        <button class="h-10 rounded-lg" :class="tab === 'again' ? 'bg-white shadow-sm text-stone-900' : 'text-stone-500'" @click="tab = 'again'">{{ t('souk.tabAgain') }}</button>
      </div>

      <!-- stall: both tabs -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
        <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.stall') }}</label>
        <select v-model="f.stall" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-2 text-[14px] bg-white">
          <option value="">{{ t('souk.newStall') }}</option>
          <option v-for="s in boot.stalls" :key="s.name" :value="s.name">{{ s.label }}</option>
        </select>
        <div v-if="!f.stall" class="grid grid-cols-2 gap-2">
          <input v-model="f.newStall.name" dir="ltr" :placeholder="t('souk.stallName')" class="h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14px] uppercase col-span-2" />
          <input v-model="f.newStall.phone" dir="ltr" inputmode="tel" :placeholder="t('souk.stallPhone')" class="h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14px] col-span-2" />
        </div>
        <p class="text-[11px] text-stone-500">{{ t('souk.stallHint') }}</p>
      </section>

      <!-- NEW PRODUCT -->
      <template v-if="tab === 'new'">
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
          <div class="flex gap-3 items-center">
            <label class="w-20 h-20 shrink-0 rounded-xl ring-1 ring-dashed ring-stone-300 bg-stone-50 flex items-center justify-center overflow-hidden cursor-pointer">
              <img v-if="refPreview" :src="refPreview" class="w-full h-full object-cover" alt="" />
              <Icon v-else name="image" :size="22" class="text-stone-400" />
              <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickRef" />
            </label>
            <div class="flex-1 min-w-0 space-y-1">
              <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.name') }}</label>
              <input v-model="f.title" :placeholder="t('souk.namePh')" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14px]" @input="lookSimilar" />
            </div>
          </div>
          <p class="text-[11px] text-stone-500">{{ t('souk.refHint') }}</p>

          <div v-if="similarRows.length" class="rounded-xl bg-amber-50 ring-1 ring-amber-200 p-3 space-y-2">
            <div class="text-[12px] font-bold text-amber-900">{{ t('souk.similar') }}</div>
            <div v-for="r in similarRows" :key="r.kind + r.key" class="flex items-center gap-2 text-[12px]">
              <span class="font-mono text-stone-700">{{ r.sku }}</span>
              <span class="flex-1 truncate text-stone-600">{{ r.title }}</span>
              <button class="font-bold text-[#a33a22]" @click="startAgain(r)">{{ t('souk.buyAgain') }}</button>
            </div>
          </div>

          <div class="space-y-1">
            <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.category') }}</label>
            <div class="flex flex-wrap gap-1.5">
              <button v-for="c in boot.categories" :key="c.key"
                      class="h-9 px-3 rounded-lg text-[12.5px] font-semibold ring-1"
                      :class="f.category === c.key ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-700 ring-stone-300'"
                      @click="f.category = c.key">{{ isAr ? c.ar : c.fr }}</button>
            </div>
            <div v-if="cat" class="flex items-center justify-between bg-stone-50 rounded-lg px-3 py-2 mt-1">
              <span class="text-[11.5px] text-stone-600">{{ t('souk.brandOnSite') }}</span>
              <span class="text-[12.5px] font-bold">{{ cat.brand }}</span>
            </div>
          </div>
        </section>

        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
          <div class="space-y-1">
            <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.colors') }}</label>
            <div class="flex flex-wrap gap-1.5">
              <button v-for="c in boot.colors" :key="c.code"
                      class="h-9 px-2.5 rounded-lg text-[12px] font-semibold ring-1"
                      :class="f.colors.includes(c.code) ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-700 ring-stone-300'"
                      @click="toggleColor(c.code)">{{ c.ar }} · {{ c.fr }}</button>
            </div>
            <p class="text-[11px] text-stone-500">{{ t('souk.colorsHint') }}</p>
          </div>
          <div class="space-y-1">
            <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.sizes') }}</label>
            <input v-model="sizesText" dir="ltr" placeholder="S, M, L" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14px] uppercase" />
            <p class="text-[11px] text-stone-500">{{ t('souk.sizesHint') }}</p>
          </div>
        </section>

        <!-- quantities -->
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.qty') }}</label>
            <span class="text-[12px] font-bold tabular-nums text-stone-900">{{ units }} {{ t('souk.pcs') }}</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-[12.5px]">
              <thead>
                <tr class="text-stone-500">
                  <th class="text-start font-semibold py-1"></th>
                  <th v-for="z in sizeCols" :key="z" class="font-semibold py-1 px-1 font-mono">{{ z || '—' }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in colorRows" :key="c">
                  <td class="py-1 pe-2 whitespace-nowrap text-stone-700">{{ colorLabel(c) }}</td>
                  <td v-for="z in sizeCols" :key="z" class="py-1 px-1">
                    <input v-model.number="qty[key(c, z)]" type="number" inputmode="numeric" min="0"
                           class="w-full min-w-[56px] h-10 rounded-lg ring-1 ring-stone-300 text-center text-[15px] font-bold tabular-nums" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- prices per size -->
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
          <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.prices') }}</label>
          <div v-for="z in sizeCols" :key="z" class="grid grid-cols-[48px_1fr_1fr_56px] gap-2 items-center">
            <span class="font-mono text-[12.5px] font-bold text-stone-700">{{ z || '—' }}</span>
            <input v-model.number="cost[z]" type="number" inputmode="decimal" :placeholder="t('souk.cost')" class="h-10 rounded-lg ring-1 ring-stone-300 px-2 text-[14px] tabular-nums" />
            <input v-model.number="price[z]" type="number" inputmode="decimal" :placeholder="t('souk.sell')" class="h-10 rounded-lg ring-1 ring-stone-300 px-2 text-[14px] tabular-nums" />
            <span class="text-[12px] font-bold tabular-nums text-end" :class="margin(z) !== null && margin(z) < 40 ? 'text-rose-600' : 'text-emerald-700'">
              {{ margin(z) === null ? '' : margin(z) + '%' }}
            </span>
          </div>
          <p class="text-[11px] text-stone-500">{{ t('souk.marginHint') }}</p>
        </section>

        <!-- SKUs preview -->
        <section v-if="lines.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-1">
          <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.skus') }}</label>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="l in lines" :key="l.sku" class="font-mono text-[11.5px] px-2 py-1 rounded-md"
                  :class="l.sku.length > boot.skuMax ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-800'">{{ l.sku }}</span>
          </div>
          <p class="text-[11px] text-stone-500">{{ t('souk.skuHint') }}</p>
        </section>
      </template>

      <!-- BUY AGAIN -->
      <template v-else>
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
          <label class="text-[12px] font-semibold text-stone-600">{{ t('souk.findProduct') }}</label>
          <input v-model="againQ" :placeholder="t('souk.findPh')" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14px]" @input="lookAgain" />
          <div v-if="againRows.length && !again" class="divide-y divide-stone-100">
            <button v-for="r in againRows" :key="r.kind + r.key" class="w-full py-2 flex items-center gap-2 text-start" @click="startAgain(r)">
              <span class="font-mono text-[12px] text-stone-700">{{ r.sku }}</span>
              <span class="flex-1 truncate text-[12.5px] text-stone-600">{{ r.title }}</span>
              <Icon name="chevron-left" :size="14" class="text-stone-400" />
            </button>
          </div>
        </section>
        <section v-if="again" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
          <div class="flex items-center justify-between gap-2">
            <div class="text-[13.5px] font-bold text-stone-900 truncate">{{ again.title }}</div>
            <button class="text-[12px] text-stone-500" @click="again = null">{{ t('souk.change') }}</button>
          </div>
          <div v-for="r in again.rows" :key="r.itemCode" class="grid grid-cols-[1fr_64px_80px] gap-2 items-center">
            <div class="min-w-0">
              <div class="font-mono text-[12px] font-bold">{{ r.sku }}</div>
              <div class="text-[11px] text-stone-500 truncate">{{ r.label }}</div>
            </div>
            <input v-model.number="r.qty" type="number" inputmode="numeric" min="0" :placeholder="t('souk.qtyShort')" class="h-10 rounded-lg ring-1 ring-stone-300 text-center text-[14px] font-bold tabular-nums" />
            <input v-model.number="r.cost" type="number" inputmode="decimal" :placeholder="t('souk.cost')" class="h-10 rounded-lg ring-1 ring-stone-300 px-2 text-[14px] tabular-nums" />
          </div>
          <p v-if="again.lastStall" class="text-[11px] text-stone-500">{{ t('souk.lastStall').replace('{s}', again.lastStall) }}</p>
        </section>
      </template>

      <!-- receipt -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 flex items-center gap-3">
        <label class="w-14 h-14 shrink-0 rounded-xl ring-1 ring-stone-300 bg-stone-50 flex items-center justify-center overflow-hidden cursor-pointer">
          <img v-if="receiptPreview" :src="receiptPreview" class="w-full h-full object-cover" alt="" />
          <Icon v-else name="file-text" :size="20" class="text-stone-400" />
          <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickReceipt" />
        </label>
        <div class="flex-1">
          <div class="text-[12.5px] font-semibold">{{ t('souk.paidFromCustody') }}</div>
          <div class="text-[11px] text-stone-500">{{ t('souk.receiptHint') }}</div>
        </div>
      </section>
    </template>

    <!-- footer -->
    <footer v-if="boot?.trip && !done && !pendingName" class="fixed inset-x-0 bottom-0 bg-white border-t border-stone-200 px-4 pt-3 pb-5 z-20">
      <div class="max-w-[520px] mx-auto space-y-2">
        <div class="flex items-center justify-between text-[12.5px]">
          <span class="text-stone-500">{{ t('souk.total') }}</span>
          <span class="font-extrabold text-[16px] tabular-nums" :class="total > boot.trip.expected ? 'text-rose-600' : 'text-stone-900'">{{ fmt(total) }} MAD</span>
        </div>
        <button class="w-full h-12 rounded-xl bg-[#c4301c] text-white text-[14px] font-bold disabled:opacity-40"
                :disabled="busy || !canSubmit" @click="submit">
          {{ busy ? t('souk.sending') : tab === 'new' ? t('souk.confirmBuy') : t('souk.confirmRebuy') }}
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { uploadPhoto } from "@/lib/soukPhoto";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t, locale } = useI18n();
const { warn } = useToast();
const route = useRoute();
const isAr = computed(() => (locale?.value || "ar") === "ar");

const DRAFT_KEY = "lp_souk_buy_draft";
const boot = ref(null);
const loading = ref(true);
const busy = ref(false);
const tab = ref("new");
const done = ref(null);
const pendingName = ref("");
const pendingError = ref("");

const blank = () => ({ stall: "", newStall: { name: "", phone: "" }, title: "", category: "", colors: [] });
const f = reactive(blank());
const sizesText = ref("");
const qty = reactive({});
const cost = reactive({});
const price = reactive({});
const refFile = ref(null);
const refPreview = ref("");
const receiptFile = ref(null);
const receiptPreview = ref("");
const similarRows = ref([]);
const againQ = ref("");
const againRows = ref([]);
const again = ref(null);

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const cat = computed(() => boot.value?.categories.find((c) => c.key === f.category));
const sizeCols = computed(() => {
  const z = sizesText.value.split(/[,\s،]+/).map((s) => s.trim().toUpperCase()).filter(Boolean);
  return z.length ? [...new Set(z)] : [""];
});
const colorRows = computed(() => (f.colors.length ? f.colors : [""]));
const key = (c, z) => `${c}|${z}`;
const colorLabel = (c) => {
  if (!c) return "—";
  const x = boot.value.colors.find((k) => k.code === c);
  return x ? `${x.ar} · ${x.fr}` : c;
};
const sizeCode = (z) => (z || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4);
const lines = computed(() => {
  if (!boot.value) return [];
  const out = [];
  for (const c of colorRows.value) {
    for (const z of sizeCols.value) {
      const q = Number(qty[key(c, z)]) || 0;
      if (q <= 0) continue;
      const sku = [boot.value.nextSku, c, sizeCode(z)].filter(Boolean).join("-");
      out.push({ color: c, size: z, qty: q, cost: Number(cost[z]) || 0, price: Number(price[z]) || 0, sku });
    }
  }
  return out;
});
const units = computed(() => lines.value.reduce((s, l) => s + l.qty, 0));
const total = computed(() => {
  if (tab.value === "again") {
    return (again.value?.rows || []).reduce((s, r) => s + (Number(r.qty) || 0) * (Number(r.cost) || 0), 0);
  }
  return lines.value.reduce((s, l) => s + l.qty * l.cost, 0);
});
function margin(z) {
  const c = Number(cost[z]) || 0;
  const p = Number(price[z]) || 0;
  if (!c || !p) return null;
  return Math.round(((p - c) / p) * 100);
}
const stallOk = computed(() => !!f.stall || (f.newStall.name || "").trim().length >= 3);
const canSubmit = computed(() => {
  if (!boot.value?.trip || !stallOk.value || total.value <= 0 || total.value > boot.value.trip.expected + 0.01) return false;
  if (tab.value === "again") return !!again.value;
  return f.title.trim().length >= 3 && !!f.category && lines.value.length > 0
    && lines.value.every((l) => l.cost > 0 && l.price > l.cost && l.sku.length <= boot.value.skuMax);
});

function toggleColor(c) {
  const i = f.colors.indexOf(c);
  if (i >= 0) f.colors.splice(i, 1);
  else f.colors.push(c);
}
function pickRef(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  refFile.value = file;
  refPreview.value = URL.createObjectURL(file);
}
function pickReceipt(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  receiptFile.value = file;
  receiptPreview.value = URL.createObjectURL(file);
}

let simTimer = null;
function lookSimilar() {
  clearTimeout(simTimer);
  simTimer = setTimeout(async () => {
    const q = f.title.trim();
    if (q.length < 3) { similarRows.value = []; return; }
    try { similarRows.value = (await api("souk.similar", { q })).rows.slice(0, 4); } catch (_) { /* advisory only */ }
  }, 450);
}
let agTimer = null;
function lookAgain() {
  clearTimeout(agTimer);
  agTimer = setTimeout(async () => {
    const q = againQ.value.trim();
    if (q.length < 3) { againRows.value = []; return; }
    try { againRows.value = (await api("souk.similar", { q })).rows; } catch (_) { /* advisory only */ }
  }, 400);
}
async function startAgain(r) {
  tab.value = "again";
  try {
    const d = await api("souk.rebuy_lookup", { key: r.key, kind: r.kind });
    again.value = { ...d, key: r.key, kind: r.kind, rows: d.rows.map((x) => ({ ...x, qty: null })) };
    if (d.lastStall && boot.value.stalls.some((s) => s.name === d.lastStall)) f.stall = d.lastStall;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  }
}

// --- keep the form on the phone --------------------------------------------
function saveDraft() {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({
      f: { ...f, newStall: { ...f.newStall }, colors: [...f.colors] }, sizesText: sizesText.value,
      qty: { ...qty }, cost: { ...cost }, price: { ...price }, pendingName: pendingName.value,
    }));
  } catch (_) { /* private mode */ }
}
function loadDraft() {
  try {
    const d = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null");
    if (!d) return;
    Object.assign(f, blank(), d.f || {});
    sizesText.value = d.sizesText || "";
    Object.assign(qty, d.qty || {});
    Object.assign(cost, d.cost || {});
    Object.assign(price, d.price || {});
    pendingName.value = d.pendingName || "";
  } catch (_) { /* ignore */ }
}
function clearDraft() {
  try { localStorage.removeItem(DRAFT_KEY); } catch (_) { /* ignore */ }
}
watch([f, sizesText, qty, cost, price, pendingName], saveDraft, { deep: true });

function reset() {
  Object.assign(f, blank());
  sizesText.value = "";
  for (const o of [qty, cost, price]) for (const k of Object.keys(o)) delete o[k];
  refFile.value = null; refPreview.value = "";
  receiptFile.value = null; receiptPreview.value = "";
  similarRows.value = []; again.value = null; againQ.value = ""; againRows.value = [];
  done.value = null; pendingName.value = ""; pendingError.value = "";
  tab.value = "new";
  clearDraft();
  load();
}

async function uploadAfter(target, isProduct) {
  // Photos are secondary: a failed upload never undoes a purchase; the trip
  // screen shows the receipt as missing and lets the buyer add it.
  try { if (isProduct && refFile.value) await uploadPhoto("ref", target, refFile.value); } catch (_) { /* shown later */ }
  try { if (receiptFile.value) await uploadPhoto("receipt", target, receiptFile.value); } catch (_) { /* shown later */ }
}

async function poll(manual = false) {
  if (!pendingName.value) return;
  busy.value = true;
  try {
    for (let i = 0; i < (manual ? 1 : 15); i++) {
      const r = await apiPost("souk.finish_buy", { name: pendingName.value });
      if (!r.pending) {
        finishDone(r);
        return;
      }
      pendingError.value = r.error || "";
      if (r.error) return;
      await new Promise((ok) => setTimeout(ok, 4000));
    }
  } catch (e) {
    pendingError.value = String(e.message || e);
  } finally {
    busy.value = false;
  }
}
function finishDone(r) {
  done.value = { po: r.po, pi: r.pi, variants: r.variants || [], left: r.left, brand: cat.value?.brand || "", again: false };
  pendingName.value = "";
  clearDraft();
}

async function submit() {
  busy.value = true;
  try {
    if (tab.value === "again") {
      const r = await apiPost("souk.create_rebuy", { payload: JSON.stringify({
        kind: again.value.kind, product: again.value.key, stall: f.stall, newStall: f.newStall,
        lines: again.value.rows.map((x) => ({ itemCode: x.itemCode, qty: x.qty, cost: x.cost })),
      }) });
      await uploadAfter(r.po, false);
      done.value = { po: r.po, pi: r.pi, variants: [], left: r.left, again: true };
      clearDraft();
      return;
    }
    const r = await apiPost("souk.create_buy", { payload: JSON.stringify({
      title: f.title, category: f.category, colors: f.colors, sizes: sizeCols.value.filter(Boolean),
      stall: f.stall, newStall: f.newStall,
      lines: lines.value.map((l) => ({ color: l.color, size: l.size, qty: l.qty, cost: l.cost, price: l.price })),
    }) });
    await uploadAfter(r.name, true);
    if (!r.pending) { finishDone(r); return; }
    pendingName.value = r.name;
    pendingError.value = r.error || "";
    busy.value = false;
    if (!r.error) await poll();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

async function load() {
  loading.value = true;
  try {
    boot.value = await api("souk.buy_boot");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  loadDraft();
  await load();
  if (route.query.again) await startAgain({ key: route.query.again, kind: route.query.kind || "souk" });
  if (pendingName.value) poll();
});
</script>
