<template>
  <div class="max-w-[980px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('gi.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('gi.intro') }}</p>
      </div>
      <div v-if="session.length" class="flex items-center gap-2">
        <span class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded-lg px-2.5 h-8 tabular-nums">
          {{ session.length }} {{ t('consol.items') }} · {{ totalUnits }} {{ t('recv.units') }}
        </span>
        <span v-if="extraUnits" class="inline-flex items-center gap-1.5 text-[12px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-lg px-2.5 h-8 tabular-nums">
          {{ extraUnits }} {{ t('gi.noPoShort') }}
        </span>
      </div>
    </header>

    <!-- Supplier picker -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 space-y-3">
      <div class="flex items-start gap-3 flex-wrap">
        <span class="text-[12.5px] font-medium text-stone-600 w-20 mt-2">{{ t('gi.supplier') }}</span>
        <div class="flex-1 min-w-[240px] space-y-2">
          <div v-if="loadingBoot" class="flex gap-1.5">
            <span v-for="n in 4" :key="n" class="w-[120px] h-8 rounded-lg bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
          </div>
          <div v-else-if="boot" class="flex flex-wrap gap-1.5">
            <button
              v-for="s in (boot.suppliers || []).slice(0, 6)" :key="s.name"
              class="h-8 px-2.5 rounded-lg text-[12px] font-semibold ring-1 transition-colors tabular-nums"
              :class="supplier === s.name
                ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]'
                : 'text-stone-700 bg-white ring-stone-200 hover:ring-stone-300'"
              @click="pickSupplier(s.name)"
            >{{ s.name }} · {{ s.pending }}</button>
          </div>
          <input
            v-model="supplierInput"
            list="lp-gi-suppliers"
            :placeholder="t('gi.supplierPh')"
            class="w-full h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] text-stone-800 focus:outline-none focus:ring-2"
            style="--tw-ring-color: var(--accent-400)"
            @change="onSupplierInput"
          />
          <datalist id="lp-gi-suppliers">
            <option v-for="s in boot?.suppliers || []" :key="s.name" :value="s.name" />
          </datalist>
          <p v-if="boot && !boot.suppliers.length" class="text-[11.5px] text-stone-400">{{ t('gi.noOpenPos') }}</p>
        </div>
      </div>

      <template v-if="supplier">
        <div class="flex items-start gap-3 flex-wrap">
          <span class="text-[12.5px] font-medium text-stone-600 w-20 mt-2">{{ t('gi.into') }}</span>
          <div class="flex-1 min-w-[200px]">
            <input
              v-model="target"
              list="lp-gi-targets"
              class="w-full h-10 ps-3 pe-3 rounded-lg bg-white ring-1 text-[13px] text-stone-800 focus:outline-none focus:ring-2"
              :class="target && !targetValid ? 'ring-rose-300' : 'ring-stone-200'"
              style="--tw-ring-color: var(--accent-400)"
            />
            <datalist id="lp-gi-targets">
              <option v-for="w in boot?.warehouses || []" :key="w" :value="w" />
            </datalist>
          </div>
          <span class="text-[12.5px] font-medium text-stone-600 w-20 mt-2">{{ t('gi.ref') }}</span>
          <input
            v-model="note" :placeholder="t('gi.refPh')" maxlength="80"
            class="flex-1 min-w-[180px] h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] text-stone-800 focus:outline-none focus:ring-2"
            style="--tw-ring-color: var(--accent-400)"
          />
        </div>
        <ScanInput ref="scanner" :placeholder="t('gi.scanPh')" @scan="onScan" />
      </template>
    </div>

    <!-- Session lines -->
    <div v-if="session.length" class="bg-white rounded-2xl ring-1 ring-[var(--accent-300)] shadow-md overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center justify-between">
        <span class="text-[12px] font-semibold text-stone-900">{{ t('gi.sessionTitle') }} — {{ supplier }}</span>
        <button class="text-[11.5px] font-semibold text-rose-600 hover:text-rose-700" @click="session = []">
          {{ t('gi.clearAll') }}
        </button>
      </div>
      <div class="divide-y divide-stone-50 max-h-[380px] overflow-y-auto">
        <div v-for="(l, i) in session" :key="l.itemCode" class="px-4 py-2.5 flex items-center gap-3"
             :class="isExtra(l) ? 'bg-amber-50/60' : ''">
          <img v-if="l.image" :src="l.image" alt="" loading="lazy" @error="hideImg"
               class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
          <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400">
            <Icon name="package" :size="14" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ l.name }}</div>
            <div class="font-mono text-[10.5px] text-stone-400">{{ l.sku || l.itemCode }}</div>
          </div>
          <span v-if="!isExtra(l)" class="text-[10.5px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded px-1.5 py-0.5 tabular-nums whitespace-nowrap">
            PO · {{ l.pending }}
          </span>
          <span v-else class="text-[10.5px] font-semibold text-amber-700 bg-amber-100 ring-1 ring-amber-200 rounded px-1.5 py-0.5 whitespace-nowrap"
                :title="t('gi.noPoHint')">
            {{ l.pending ? `PO ${l.pending} + ${l.qty - l.pending}` : t('gi.noPo') }}
          </span>
          <div class="flex items-center gap-1">
            <button class="w-8 h-8 rounded-lg bg-stone-100 text-[14px] font-bold" @click="l.qty = Math.max(1, l.qty - 1)">−</button>
            <input v-model.number="l.qty" type="number" min="1"
                   class="w-14 h-8 text-center text-[14px] font-bold tabular-nums rounded-lg ring-1 ring-stone-200 focus:outline-none" />
            <button class="w-8 h-8 rounded-lg bg-stone-100 text-[14px] font-bold" @click="l.qty += 1">+</button>
          </div>
          <button class="w-8 h-8 rounded-lg hover:bg-rose-50 text-stone-400 hover:text-rose-600 flex items-center justify-center" @click="session.splice(i, 1)">
            <Icon name="x" :size="14" />
          </button>
        </div>
      </div>
      <div class="p-3 border-t border-stone-100 space-y-2">
        <p v-if="extraUnits && !isManager" class="text-[11.5px] text-amber-700 flex items-center gap-1.5">
          <Icon name="alert-triangle" :size="13" /> {{ t('gi.managerNeeded') }}
        </p>
        <button
          class="w-full h-11 rounded-xl text-[13.5px] font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50 transition-colors"
          :class="armed ? 'bg-amber-600 hover:bg-amber-700' : 'bg-emerald-600 hover:bg-emerald-700'"
          :disabled="busy || !targetValid || (extraUnits > 0 && !isManager)"
          @click="post"
        >
          <Icon name="package-check" :size="16" />
          <template v-if="busy">{{ t('gi.posting') }}</template>
          <template v-else-if="armed">{{ t('gi.confirmPost') }} — {{ totalUnits }} {{ t('recv.units') }}<span v-if="extraUnits"> · {{ extraUnits }} {{ t('gi.noPoShort') }}</span></template>
          <template v-else>{{ t('gi.postBtn') }}</template>
        </button>
      </div>
    </div>

    <!-- Recent receipts -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100">
        <span class="text-[12px] font-semibold text-stone-900">{{ t('gi.recentTitle') }}</span>
      </div>
      <div v-if="loadingBoot" class="p-3 space-y-2">
        <div v-for="n in 4" :key="n" class="h-[44px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <div v-else class="divide-y divide-stone-50 max-h-[380px] overflow-y-auto">
        <p v-if="!recent.length" class="px-4 py-6 text-center text-[12.5px] text-stone-400">{{ t('gi.recentEmpty') }}</p>
        <div v-for="r in recent" :key="r.receipt" class="px-4 py-2 flex items-center gap-3 text-[12px]">
          <span class="text-[10.5px] text-stone-400 tabular-nums w-[74px] flex-shrink-0">{{ r.time }}</span>
          <span class="font-mono font-medium text-stone-800 truncate max-w-[150px]">{{ r.receipt }}</span>
          <span class="text-stone-600 truncate max-w-[140px]">{{ r.supplier }}</span>
          <span class="tabular-nums text-stone-600">{{ r.lines }} × {{ r.units }} {{ t('recv.units') }}</span>
          <span class="text-stone-500 truncate flex-1">→ {{ short(r.target) }}</span>
          <span v-if="r.viaPortal" class="text-[10px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200 rounded px-1.5 py-0.5">{{ t('mv.viaPortal') }}</span>
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
const boot = ref(null);
const loadingBoot = ref(true);
const supplier = ref("");
const supplierInput = ref("");
const target = ref("Receiving Zone - JM");
const note = ref("");
const session = ref([]);
const busy = ref(false);
const armed = ref(false);
const recent = ref([]);

const isManager = computed(() => !!boot.value?.isManager);
const totalUnits = computed(() => session.value.reduce((s, l) => s + (l.qty || 0), 0));
const extraUnits = computed(() =>
  session.value.reduce((s, l) => s + Math.max(0, (l.qty || 0) - (l.pending || 0)), 0));
const targetValid = computed(() =>
  !!target.value && (boot.value?.warehouses || []).includes(target.value));

function isExtra(l) { return (l.qty || 0) > (l.pending || 0); }

onMounted(async () => {
  try {
    boot.value = await api("purchasing.receive_boot");
    recent.value = boot.value.recent || [];
    if (boot.value.defaultTarget) target.value = boot.value.defaultTarget;
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loadingBoot.value = false;
  }
});

function pickSupplier(name) {
  if (supplier.value === name) return;
  supplier.value = name;
  supplierInput.value = name;
  session.value = [];
  setTimeout(() => scanner.value?.refocus(), 50);
}
function onSupplierInput() {
  const v = supplierInput.value.trim();
  if ((boot.value?.suppliers || []).some((s) => s.name === v)) pickSupplier(v);
}

async function onScan(raw) {
  const code = String(raw || "").trim();
  if (!code || !supplier.value) return;
  const hit = session.value.find((l) => l.sku === code || l.itemCode === code);
  if (hit) {
    hit.qty += 1;
    scanner.value?.showSuccess(`${hit.name} · ×${hit.qty}`);
    return;
  }
  let res;
  try {
    res = await apiPost("purchasing.receive_scan", { supplier: supplier.value, code });
  } catch (e) {
    scanner.value?.showError(String(e.message || e));
    return;
  }
  if (!res.ok) {
    scanner.value?.showError(t("pickm.unknown"));
    return;
  }
  const existing = session.value.find((l) => l.itemCode === res.itemCode);
  if (existing) {
    existing.qty += 1;
    scanner.value?.showSuccess(`${existing.name} · ×${existing.qty}`);
  } else {
    session.value.unshift({ ...res, qty: 1 });
    if (res.hasPo) scanner.value?.showSuccess(`${res.name} · PO ${res.pending}`);
    else scanner.value?.showError(`${res.name} — ${t('gi.noPo')}`);
  }
}

async function post() {
  if (!session.value.length || busy.value || !targetValid.value) return;
  if (!armed.value) { armed.value = true; setTimeout(() => { armed.value = false; }, 4000); return; }
  armed.value = false;
  busy.value = true;
  try {
    const res = await apiPost("purchasing.post_purchase_receipt", {
      supplier: supplier.value,
      items: session.value.map((l) => ({ item_code: l.itemCode, qty: l.qty })),
      target: target.value,
      note: note.value,
    });
    let detail = `${res.receipts.join(" + ")} · ${res.units} ${t('recv.units')} → ${short(res.target)}`;
    if (res.extras) detail += ` · ${res.extras} ${t('gi.noPoShort')}`;
    success(t("gi.posted"), detail);
    session.value = [];
    note.value = "";
    const r = await api("purchasing.recent_purchase_receipts");
    recent.value = r.rows || [];
  } catch (e) {
    warn(t("gi.postFail"), String(e.message || e));
  } finally {
    busy.value = false;
    scanner.value?.refocus();
  }
}

function short(w) { return String(w || "").replace(" - JM", ""); }
function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }
</script>
