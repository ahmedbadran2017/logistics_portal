<template>
  <!-- Return Zone repair: supplier-bound returns that sit in Return Zone but
       not on the books. Paste the sheet (SKU, order, qty), check, then put
       each piece back — a count zeroed it, or its return was never booked.
       The hand-back itself stays on Supplier pickup. Backend: api/return_zone_repair. -->
  <div class="max-w-[1180px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('rzr.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[760px]">{{ t('rzr.intro') }}</p>
      </div>
      <router-link :to="{ name: 'SupplierPickup' }" class="h-9 px-3.5 rounded-lg text-[12.5px] font-semibold ring-1 ring-stone-200 bg-white text-stone-700 hover:bg-stone-50 flex items-center gap-1.5">
        <Icon name="rotate-ccw" :size="14" /> {{ t('nav.supplierPickup') }}
      </router-link>
    </header>

    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 space-y-2">
      <textarea v-model="text" rows="6" :placeholder="t('rzr.pastePh')"
        class="w-full rounded-xl ring-1 ring-stone-200 focus:ring-stone-400 outline-none p-3 font-mono text-[12px] text-stone-800 resize-y" />
      <div class="flex items-center gap-2 flex-wrap">
        <button class="h-9 px-4 rounded-lg text-[12.5px] font-semibold bg-stone-900 text-white hover:bg-stone-800 disabled:opacity-50 flex items-center gap-1.5"
          :disabled="!text.trim() || loading" @click="check">
          <Icon name="search" :size="14" /> {{ loading ? t('rzr.checking') : t('rzr.check') }}
        </button>
        <span class="text-[11px] text-stone-400">{{ t('rzr.pasteHint') }}</span>
      </div>
    </div>

    <!-- Tally: click a chip to filter -->
    <div v-if="rows.length" class="flex items-center gap-1.5 flex-wrap">
      <button class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1"
        :class="filter === '' ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200'"
        @click="filter = ''">{{ t('rzr.all') }} · {{ rows.length }}</button>
      <button v-for="s in statuses" :key="s" class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 tabular-nums"
        :class="filter === s ? 'bg-stone-900 text-white ring-stone-900' : tone(s)"
        @click="filter = filter === s ? '' : s">
        {{ t('rzr.s_' + s) }} · {{ counts[s] }}
      </button>
    </div>

    <div v-if="rows.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-x-auto">
      <table class="w-full text-[12.5px]">
        <thead>
          <tr class="text-[10.5px] uppercase tracking-wide text-stone-500 border-b border-stone-200">
            <th class="text-start px-3 py-2">{{ t('rzr.status') }}</th>
            <th class="text-start px-3 py-2">{{ t('rzr.order') }}</th>
            <th class="text-start px-3 py-2">{{ t('rzr.item') }}</th>
            <th class="text-center px-2 py-2">{{ t('rzr.qty') }}</th>
            <th class="text-start px-3 py-2">{{ t('rzr.zone') }}</th>
            <th class="text-end px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in shown" :key="r.key" class="border-b border-stone-100 align-top">
            <td class="px-3 py-2.5">
              <span class="inline-flex items-center h-6 px-2 rounded-md text-[11px] font-semibold ring-1 whitespace-nowrap" :class="tone(r.status)">{{ t('rzr.s_' + r.status) }}</span>
              <div class="text-[11px] text-stone-400 mt-1 max-w-[220px]">{{ t('rzr.h_' + r.status) }}</div>
            </td>
            <td class="px-3 py-2.5 whitespace-nowrap">
              <div class="font-semibold text-stone-800">{{ r.order || '—' }}</div>
              <div v-if="r.orderRaw && r.orderRaw !== r.order" class="text-[11px] text-stone-400">{{ r.orderRaw }}</div>
              <div v-if="r.line?.dn" class="text-[11px] text-stone-400 font-mono">{{ r.line.dn }}</div>
            </td>
            <td class="px-3 py-2.5 min-w-[220px]">
              <div class="text-stone-800">{{ r.name || r.sku }}</div>
              <div class="text-[11px] text-stone-400 font-mono">{{ r.sku }}<span v-if="r.item && r.item !== r.sku"> · {{ r.item }}</span></div>
              <div v-if="r.supplier" class="text-[11px] text-stone-500">{{ r.supplier }}<span v-if="r.crossdock" class="ms-1 text-violet-700 font-semibold">· Cross-dock</span></div>
            </td>
            <td class="px-2 py-2.5 text-center font-bold tabular-nums">{{ r.qty }}</td>
            <td class="px-3 py-2.5 text-[11.5px] text-stone-600 tabular-nums whitespace-nowrap">
              <template v-if="r.zone">
                <div>{{ t('rzr.holds') }} <b class="text-stone-800">{{ fmt(r.zone.current) }}</b> / {{ t('rzr.should') }} {{ fmt(r.zone.expected) }}</div>
                <div v-if="r.zone.zeroed">{{ t('rzr.zeroed') }} {{ fmt(r.zone.zeroed) }}<span v-if="r.zone.restored"> · {{ t('rzr.putBack') }} {{ fmt(r.zone.restored) }}</span></div>
                <div v-if="r.zone.count" class="text-stone-400 font-mono">{{ r.zone.count }}</div>
              </template>
            </td>
            <td class="px-3 py-2.5 text-end whitespace-nowrap">
              <div v-if="r.done" class="text-[11.5px] font-semibold text-emerald-700 flex items-center justify-end gap-1">
                <Icon name="check-circle" :size="14" /> {{ r.done }}
              </div>
              <button v-else-if="canRestore(r)"
                class="h-8 px-3 rounded-lg text-[12px] font-semibold disabled:opacity-50"
                :class="armed === r.key ? 'bg-amber-600 text-white' : 'bg-amber-50 text-amber-800 ring-1 ring-amber-200 hover:bg-amber-100'"
                :disabled="busy" @click="act(r, 'restore')">
                {{ armed === r.key ? t('rzr.sure') : `${t('rzr.restore')} ${restoreQty(r)}` }}
              </button>
              <button v-else-if="r.status === 'unregistered'"
                class="h-8 px-3 rounded-lg text-[12px] font-semibold disabled:opacity-50"
                :class="armed === r.key ? 'bg-sky-600 text-white' : 'bg-sky-50 text-sky-800 ring-1 ring-sky-200 hover:bg-sky-100'"
                :disabled="busy" @click="act(r, 'register')">
                {{ armed === r.key ? t('rzr.sure') : t('rzr.register') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const ORDER = ["zeroed", "zeroed_no_order", "unregistered", "missing", "in_zone", "collected", "never_shipped", "no_order", "unknown_sku"];

const text = ref("");
const rows = ref([]);
const loading = ref(false);
const busy = ref(false);
const armed = ref("");
const filter = ref("");

const counts = computed(() => rows.value.reduce((m, r) => ((m[r.status] = (m[r.status] || 0) + 1), m), {}));
const statuses = computed(() => ORDER.filter((s) => counts.value[s]));
const shown = computed(() => {
  const list = filter.value ? rows.value.filter((r) => r.status === filter.value) : rows.value;
  return [...list].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status));
});

const fmt = (n) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

function tone(s) {
  return {
    zeroed: "bg-amber-50 text-amber-800 ring-amber-200",
    zeroed_no_order: "bg-amber-50 text-amber-800 ring-amber-200",
    unregistered: "bg-sky-50 text-sky-800 ring-sky-200",
    missing: "bg-rose-50 text-rose-700 ring-rose-200",
    in_zone: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    collected: "bg-stone-50 text-stone-500 ring-stone-200",
  }[s] || "bg-stone-50 text-stone-600 ring-stone-200";
}

const restoreQty = (r) => Math.min(r.qty, r.zone?.restorable || 0);
const canRestore = (r) => (r.status === "zeroed" || r.status === "zeroed_no_order") && restoreQty(r) > 0;

async function check() {
  if (!text.value.trim() || loading.value) return;
  loading.value = true;
  try {
    const res = await apiPost("return_zone_repair.check", { lines: text.value });
    rows.value = (res.rows || []).map((r, i) => ({ ...r, key: `${i}|${r.sku}|${r.orderRaw}`, done: "" }));
    filter.value = "";
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

async function act(r, kind) {
  if (busy.value) return;
  if (armed.value !== r.key) {
    armed.value = r.key;
    setTimeout(() => { if (armed.value === r.key) armed.value = ""; }, 4000);
    return;
  }
  armed.value = "";
  busy.value = true;
  try {
    const res = kind === "restore"
      ? await apiPost("return_zone_repair.restore", { item_code: r.item, qty: restoreQty(r), order: r.order || "" })
      : await apiPost("return_zone_repair.register_return", { order: r.order, item_code: r.item, qty: r.qty });
    r.done = res.doc;
    success(kind === "restore" ? t("rzr.restored") : t("rzr.registered"), `${r.order || r.sku} · ${res.doc}`);
    // The same item can sit on several sheet lines: refresh the numbers so the
    // next button offers only what is still missing.
    const again = await apiPost("return_zone_repair.check", {
      lines: JSON.stringify(rows.value.filter((x) => !x.done).map((x) => ({ sku: x.sku, order: x.orderRaw, qty: x.qty, item: x.item }))),
    });
    const fresh = again.rows || [];
    let i = 0;
    rows.value.forEach((x) => {
      if (x.done) return;
      const f = fresh[i++];
      if (f) Object.assign(x, { status: f.status, zone: f.zone, line: f.line });
    });
  } catch (e) {
    warn(t("rzr.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}
</script>
