<template>
  <div class="p-4 sm:p-6 space-y-4 max-w-[1100px] mx-auto">
    <header>
      <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('csl.title') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-1">{{ t('csl.intro') }}</p>
    </header>

    <!-- One box. Submit, never per keystroke: the phone branch reads the
         whole order table (~300ms) and there is no index that makes it
         faster without making it quietly wrong. -->
    <form class="flex items-center gap-2" @submit.prevent="run()">
      <div class="relative flex-1">
        <Icon name="search" :size="15"
              class="absolute inset-y-0 my-auto start-3 text-stone-400 pointer-events-none" />
        <input ref="box" v-model="q" type="search" inputmode="search"
               :placeholder="t('csl.placeholder')"
               class="w-full h-11 ps-9 pe-3 rounded-xl bg-white ring-1 ring-stone-200 text-[13.5px]
                      focus:outline-none focus:ring-2 focus:ring-[var(--accent-500)]" />
      </div>
      <button type="submit" :disabled="loading || q.trim().length < 3"
              class="h-11 px-5 rounded-xl text-[13px] font-semibold text-white
                     bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-40">
        {{ loading ? t('csl.searching') : t('csl.search') }}
      </button>
    </form>

    <div v-if="err" class="rounded-xl p-4 bg-rose-50/70 ring-1 ring-rose-200 text-[12.5px] text-rose-700">
      {{ err }}
    </div>

    <!-- The person, before the orders: who they are and how we have treated
         each other. 60% of orders come from a number that ordered before. -->
    <section v-if="cust && cust.found" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 space-y-3">
      <div class="flex items-start gap-3 flex-wrap">
        <span class="w-10 h-10 rounded-xl bg-[var(--accent-50)] text-[var(--accent-600)]
                     flex items-center justify-center shrink-0">
          <Icon name="user" :size="18" />
        </span>
        <div class="min-w-0">
          <div class="text-[15px] font-bold text-stone-900 truncate">{{ cust.name || t('csl.noName') }}</div>
          <div class="text-[11.5px] text-stone-500 tabular-nums" dir="ltr">
            {{ cust.phone }}<template v-if="cust.city"> · {{ cust.city }}</template>
          </div>
          <div v-if="cust.names && cust.names.length > 1" class="text-[10.5px] text-stone-400 mt-0.5">
            {{ t('csl.alsoKnown') }} {{ cust.names.slice(1).join(' · ') }}
          </div>
        </div>
        <span v-if="cust.risky"
              class="ms-auto inline-flex items-center gap-1.5 text-[11px] font-bold rounded-full px-2.5 py-1
                     text-amber-800 bg-amber-50 ring-1 ring-amber-300"
              :title="t('csl.riskyHint')">
          <Icon name="alert-circle" :size="12" />{{ t('csl.risky') }}
        </span>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
        <div v-for="k in KPIS" :key="k.k" class="rounded-xl bg-stone-50 ring-1 ring-stone-200/70 px-3 py-2">
          <div class="text-[10px] font-semibold uppercase tracking-wide text-stone-400">{{ t(k.label) }}</div>
          <div class="text-[17px] font-extrabold tabular-nums mt-0.5" :class="k.cls">{{ kpi(k.k) }}</div>
        </div>
      </div>

      <div class="text-[11px] text-stone-400 tabular-nums" dir="ltr">
        {{ t('csl.since') }} {{ local(cust.firstOrder) }} → {{ local(cust.lastOrder) }}
      </div>

      <div v-if="cust.conversations && cust.conversations.length"
           class="flex flex-wrap gap-1.5 pt-1">
        <span v-for="c in cust.conversations" :key="c.name"
              class="inline-flex items-center gap-1.5 text-[10.5px] rounded-full px-2 py-1
                     bg-sky-50 text-sky-700 ring-1 ring-sky-200" :title="c.summary">
          <Icon name="message-circle" :size="11" />{{ c.channel || 'chat' }}
          <span class="tabular-nums text-sky-500" dir="ltr">{{ local(c.at).slice(5, 16) }}</span>
          <span v-if="c.unread" class="w-1.5 h-1.5 rounded-full bg-rose-500" />
        </span>
      </div>

      <div v-if="cust.requests && cust.requests.length" class="space-y-1 pt-1">
        <div v-for="r in cust.requests.slice(0, 4)" :key="r.name"
             class="flex items-center gap-2 text-[11.5px] rounded-lg px-2 py-1.5 bg-stone-50">
          <span class="font-semibold text-stone-700">{{ t('cs.k_' + r.kind, r.kind) }}</span>
          <span class="text-stone-400">{{ r.state }}</span>
          <span class="text-stone-500 truncate">{{ r.note }}</span>
          <span class="ms-auto text-stone-400 tabular-nums shrink-0" dir="ltr">{{ local(r.at).slice(5, 16) }}</span>
        </div>
      </div>
    </section>

    <!-- The orders. Same row shape whichever way the agent got here. -->
    <section v-if="rows.length" class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="flex items-center gap-2 px-4 py-2.5 border-b border-stone-100">
        <span class="text-[12px] font-semibold text-stone-900">{{ t('csl.orders') }}</span>
        <span class="text-[11px] text-stone-400 tabular-nums">{{ total }}</span>
        <span v-if="mode" class="text-[10px] font-semibold uppercase tracking-wide rounded-full px-2 py-0.5
                                 bg-stone-100 text-stone-500">{{ t('csl.by_' + mode, mode) }}</span>
      </div>
      <ul class="divide-y divide-stone-100">
        <li v-for="r in rows" :key="r.order"
            class="px-4 py-2.5 flex items-center gap-3 flex-wrap hover:bg-stone-50/70">
          <RouterLink :to="{ name: 'OrderDetail', params: { name: String(r.order).replace('#', '') } }"
                      class="font-mono text-[12.5px] font-semibold text-stone-800
                             hover:text-[var(--accent-600)]" dir="ltr">{{ r.order }}</RouterLink>
          <span class="text-[10.5px] text-stone-400 tabular-nums" dir="ltr">{{ local(r.date) }}</span>
          <button v-if="!cust || !cust.found" class="text-[12px] text-stone-600 hover:text-[var(--accent-600)] truncate max-w-[160px]"
                  :title="t('csl.openCustomer')" @click="openCustomer(r)">{{ r.customer }}</button>
          <span v-else class="text-[12px] text-stone-600 truncate max-w-[160px]">{{ r.customer }}</span>
          <span v-if="r.city" class="text-[10.5px] text-stone-400 truncate max-w-[100px]">{{ r.city }}</span>
          <span class="ms-auto flex items-center gap-2 shrink-0">
            <span class="text-[11.5px] tabular-nums text-stone-500">{{ Math.round(r.total) }}</span>
            <span v-if="r.outcome" class="text-[10.5px] font-bold rounded-full px-2 py-0.5"
                  :class="OUT_CLS[r.outcome]">{{ t('csl.o_' + r.outcome) }}</span>
            <span v-else-if="r.logistics" class="text-[10.5px] text-stone-500 rounded-full px-2 py-0.5 bg-stone-100">
              {{ r.logistics }}</span>
          </span>
        </li>
      </ul>
      <button v-if="hasMore" :disabled="loading"
              class="w-full h-10 text-[12px] font-semibold text-stone-700 bg-stone-50 hover:bg-stone-100
                     border-t border-stone-100 disabled:opacity-50"
              @click="run(true)">{{ t('mdt.logMore') }}</button>
    </section>

    <div v-else-if="searched && !loading && !err"
         class="rounded-2xl p-10 text-center bg-stone-50 ring-1 ring-stone-200/60">
      <div class="text-[13px] font-semibold text-stone-600">{{ t('csl.none') }}</div>
      <div class="text-[11.5px] text-stone-400 mt-1">{{ t('csl.noneHint') }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const q = ref(String(route.query.q || ""));
const rows = ref([]);
const total = ref(0);
const mode = ref("");
const hasMore = ref(false);
const cust = ref(null);
const loading = ref(false);
const searched = ref(false);
const err = ref("");
const box = ref(null);

const KPIS = [
  { k: "orders", label: "csl.kOrders", cls: "text-stone-900" },
  { k: "delivered", label: "csl.kDelivered", cls: "text-emerald-600" },
  { k: "failed", label: "csl.kFailed", cls: "text-rose-600" },
  { k: "cancelled", label: "csl.kCancelled", cls: "text-amber-600" },
  { k: "open", label: "csl.kOpen", cls: "text-sky-600" },
  { k: "spend", label: "csl.kSpend", cls: "text-stone-900" },
];
const OUT_CLS = {
  delivered: "text-emerald-700 bg-emerald-50",
  failed: "text-rose-700 bg-rose-50",
  cancelled: "text-amber-700 bg-amber-50",
  open: "text-sky-700 bg-sky-50",
  unknown: "text-stone-500 bg-stone-100",
};
function kpi(k) {
  return cust.value?.totals?.[k] ?? 0;
}

let seq = 0;
async function run(more = false) {
  const term = q.value.trim();
  if (term.length < 3) return;
  const mine = ++seq;
  loading.value = true;
  err.value = "";
  try {
    const res = await api("cs.search", {
      q: term, limit: 25, offset: more ? rows.value.length : 0,
    });
    if (mine !== seq) return;
    rows.value = more ? [...rows.value, ...(res.rows || [])] : (res.rows || []);
    total.value = res.total || 0;
    mode.value = res.mode || "";
    hasMore.value = !!res.hasMore;
    searched.value = true;
    if (!more) {
      router.replace({ query: term ? { q: term } : {} });
      // A phone search IS a customer: show who they are without a second
      // click. Anything else waits for the agent to pick a row.
      cust.value = null;
      if (res.mode === "phone" && res.rows?.length) loadCustomer(res.rows[0]);
    }
  } catch (e) {
    if (mine === seq) err.value = String(e.message || e);
  } finally {
    if (mine === seq) loading.value = false;
  }
}

async function loadCustomer(row) {
  try {
    const c = await api("cs.customer", row.phone ? { phone: row.phone } : { order: row.order });
    if (c && c.found) {
      cust.value = c;
      // The customer view owns the list from here: it is the whole history,
      // not the page of matches.
      rows.value = c.orders || rows.value;
      total.value = (c.orders || []).length;
      hasMore.value = false;
    }
  } catch (_) { /* the header is a bonus; the rows already answered */ }
}

function openCustomer(row) {
  loadCustomer(row);
}

onMounted(async () => {
  await nextTick();
  box.value?.focus();
  if (q.value.trim().length >= 3) run();
});
</script>
