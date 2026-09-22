<template>
  <div class="space-y-3">
    <!-- Confirmed customers who cannot be shipped yet. The pile was visible
         only on the dispatcher's board, which CS cannot open — so nobody
         whose job is talking to customers could see who was waiting. -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3 flex items-center gap-3 flex-wrap">
      <Icon name="package-x" :size="15" class="text-amber-600" />
      <span class="text-[13px] font-semibold text-stone-900">{{ t('sw.title') }}</span>
      <span class="text-[11.5px] text-stone-400">{{ t('sw.sub') }}</span>
      <div class="ms-auto flex items-center gap-1">
        <button v-for="s in SCOPES" :key="s.k" class="h-8 px-3 rounded-lg text-[12px] font-semibold transition-colors"
                :class="scope === s.k ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100'"
                @click="scope = s.k">{{ t(s.l) }}</button>
        <button class="w-8 h-8 rounded-lg text-stone-400 hover:bg-stone-100 flex items-center justify-center"
                :title="t('common.refresh')" @click="load">
          <Icon name="refresh-cw" :size="13" />
        </button>
      </div>
    </div>

    <div v-if="loading" class="space-y-2">
      <span v-for="n in 5" :key="n" class="block h-14 rounded-xl bg-stone-100 animate-pulse" />
    </div>

    <div v-else-if="denied" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-8 text-center text-[13px] text-stone-400">
      {{ t('sw.denied') }}
    </div>

    <template v-else>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div v-for="k in kpis" :key="k.l" class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5">
          <div class="text-[10.5px] font-semibold uppercase tracking-wide text-stone-400">{{ t(k.l) }}</div>
          <div class="text-[17px] font-extrabold tabular-nums" :class="k.cls || 'text-stone-900'">{{ k.v }}</div>
        </div>
      </div>

      <!-- Grouped by the thing ONE action fixes: a supplier is one phone call
           covering many orders, and an item is one buying decision covering
           many customers. A flat per-order list would make the same call
           twenty-seven times and read as twenty-seven problems. -->
      <div v-for="g in groups" :key="g.key" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <button class="w-full px-4 py-2.5 flex items-center gap-2.5 hover:bg-stone-50 text-start"
                @click="open = open === g.key ? '' : g.key">
          <Icon :name="open === g.key ? 'chevron-down' : 'chevron-right'" :size="13" class="text-stone-400 shrink-0" />
          <span class="text-[12.5px] font-semibold text-stone-900 truncate" dir="auto">{{ g.key }}</span>
          <span class="text-[11px] text-stone-400 tabular-nums whitespace-nowrap">
            {{ t('sw.nOrders').replace('{n}', String(g.orders.length)) }}
          </span>
          <span v-if="g.noPO" class="text-[10px] font-bold rounded-full px-2 py-0.5 bg-rose-50 text-rose-700 ring-1 ring-rose-200 whitespace-nowrap">
            {{ t('sw.sNoPO') }} {{ g.noPO }}
          </span>
          <span v-if="g.late" class="text-[10px] font-bold rounded-full px-2 py-0.5 bg-amber-50 text-amber-700 ring-1 ring-amber-200 whitespace-nowrap">
            {{ t('sw.sLate') }} {{ g.late }}
          </span>
          <span class="ms-auto text-[12px] font-bold tabular-nums text-stone-700 whitespace-nowrap">{{ fmtMAD(g.value) }}</span>
          <span class="text-[11px] tabular-nums text-stone-400 whitespace-nowrap">{{ g.oldest }}{{ t('sw.d') }}</span>
        </button>

        <div v-if="open === g.key" class="border-t border-stone-100 divide-y divide-stone-50">
          <div v-for="o in g.orders" :key="o.order" class="px-4 py-2 flex items-center gap-2.5 flex-wrap">
            <!-- What we can honestly tell this customer, before the call.
                 "late" carries no date on purpose: the promise is already
                 broken and offering another one is how it breaks twice. -->
            <span class="text-[9.5px] font-bold uppercase rounded px-1.5 py-0.5 whitespace-nowrap"
                  :class="STATE_CLS[o.state] || 'bg-stone-100 text-stone-500'"
                  :title="t('sw.h_' + o.state)">{{ t('sw.s_' + o.state) }}</span>
            <span v-if="o.state === 'late'" class="text-[11px] font-semibold text-rose-600 tabular-nums whitespace-nowrap">
              {{ t('sw.overdue').replace('{n}', String(o.overdueBy)) }}
            </span>
            <span v-else-if="o.state === 'ordered'" class="text-[11px] tabular-nums whitespace-nowrap"
                  :class="o.poAge > 60 ? 'text-rose-600 font-semibold' : 'text-stone-500'">
              {{ t('sw.poAge').replace('{n}', String(o.poAge)) }}
            </span>
            <span v-else-if="o.due" class="text-[11px] text-emerald-700 tabular-nums whitespace-nowrap">{{ o.due }}</span>

            <RouterLink :to="{ name: 'OrderDetail', params: { name: encodeURIComponent(o.order) } }"
                        class="text-[12px] font-semibold text-stone-800 hover:text-[var(--accent-700)] hover:underline truncate max-w-[150px]" dir="auto">
              {{ o.customer || o.order }}
            </RouterLink>
            <span class="text-[10.5px] font-mono text-stone-400 truncate">{{ o.order }}</span>
            <span class="text-[11px] text-stone-500 truncate flex-1 min-w-[110px]" dir="auto" :title="o.item">{{ o.item }}</span>
            <span class="text-[11.5px] font-bold tabular-nums text-stone-700 whitespace-nowrap">{{ fmtMAD(o.value) }}</span>
            <span class="text-[11px] tabular-nums text-stone-400 whitespace-nowrap">{{ o.age }}{{ t('sw.d') }}</span>
            <a v-if="o.phone" :href="'tel:' + o.phone"
               class="w-7 h-7 rounded-lg bg-sky-50 text-sky-700 ring-1 ring-sky-200 hover:bg-sky-100 flex items-center justify-center shrink-0"
               :title="o.phone"><Icon name="phone" :size="12" /></a>
          </div>
        </div>
      </div>

      <div v-if="!groups.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-10 text-center">
        <div class="text-[13px] text-emerald-600 font-semibold">{{ t('sw.empty') }}</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { RouterLink } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { fmtMAD } from "@/lib/handoffData";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const SCOPES = [{ k: "local", l: "sw.scLocal" }, { k: "import", l: "sw.scImport" }];
const STATE_CLS = {
  noPO: "bg-rose-100 text-rose-700",
  late: "bg-amber-100 text-amber-800",
  due: "bg-sky-100 text-sky-700",
  otw: "bg-emerald-100 text-emerald-700",
  // Import only: a purchase order exists, and that is ALL it says.
  ordered: "bg-stone-200 text-stone-600",
};
const scope = ref("local");
const d = ref(null);
const loading = ref(true);
const denied = ref(false);
const open = ref("");

// One shape for both tabs: a supplier group and an item group differ only in
// what the heading names, so the table does not need to know which it is.
const groups = computed(() => {
  const r = d.value;
  if (!r) return [];
  if (r.scope === "local") {
    return (r.suppliers || []).map((g) => ({
      key: g.supplier, orders: g.orders, value: g.value,
      oldest: g.oldest, noPO: g.noPO, late: g.late,
    }));
  }
  return (r.items || []).map((g) => ({
    key: g.item, orders: g.orders, value: g.value,
    oldest: g.oldest, noPO: g.noPO || 0, late: 0,
  }));
});

const kpis = computed(() => {
  const r = d.value || {};
  const out = [
    { l: "sw.kOrders", v: r.orders ?? 0 },
    { l: "sw.kValue", v: fmtMAD(r.value ?? 0) },
  ];
  if (r.scope === "local") {
    out.push({ l: "sw.kNoPO", v: r.noPO ?? 0, cls: (r.noPO ? "text-rose-600" : "text-stone-900") });
    out.push({ l: "sw.kLate", v: r.late ?? 0, cls: (r.late ? "text-amber-600" : "text-stone-900") });
  } else {
    out.push({ l: "sw.kItems", v: (r.items || []).length });
  }
  return out;
});

async function load() {
  loading.value = true;
  denied.value = false;
  try {
    d.value = await api("cs.stock_wait", { scope: scope.value });
    open.value = groups.value.length ? groups.value[0].key : "";
  } catch (e) {
    denied.value = true;
    d.value = null;
  } finally {
    loading.value = false;
  }
}
watch(scope, load);
onMounted(load);
</script>
