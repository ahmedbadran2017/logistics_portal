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
          <!-- An exchange names both sides; say which one this row is and
               who owes whom, because that is what the caller asks. -->
          <span v-if="r.exchange"
                class="inline-flex items-center gap-1 text-[10px] font-bold rounded-full px-2 py-0.5
                       text-violet-700 bg-violet-50 ring-1 ring-violet-200"
                :title="exTitle(r.exchange)">
            <Icon name="refresh-cw" :size="10" />{{ t('csl.x_' + r.exchange.side) }}
          </span>
          <span class="ms-auto flex items-center gap-2 shrink-0">
            <span class="text-[11.5px] tabular-nums text-stone-500">{{ Math.round(r.total) }}</span>
            <span v-if="r.outcome" class="text-[10.5px] font-bold rounded-full px-2 py-0.5"
                  :class="OUT_CLS[r.outcome]">{{ t('csl.o_' + r.outcome) }}</span>
            <span v-else-if="r.logistics" class="text-[10.5px] text-stone-500 rounded-full px-2 py-0.5 bg-stone-100">
              {{ r.logistics }}</span>
            <button class="h-7 px-2 rounded-lg text-[11px] font-semibold text-stone-600
                           bg-stone-100 hover:bg-stone-200"
                    :title="t('csl.raiseHint')" @click="openRaise(r)">
              <Icon name="message-circle" :size="11" class="inline -mt-px me-0.5" />{{ t('csl.raise') }}
            </button>
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

    <!-- Somewhere to start when the screen opens cold. The way in is the
         search box — an agent always arrives holding a name or a number —
         so these are short lists of PEOPLE, not a browsable table of
         175,711 customer records nobody would page through. -->
    <section v-if="!searched && !loading" class="bg-white rounded-2xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="flex items-center gap-1 px-3 py-2 border-b border-stone-100">
        <button v-for="tb in TABS" :key="tb.k"
                class="h-8 px-3 rounded-lg text-[12px] font-semibold transition-colors"
                :class="tab === tb.k ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100'"
                @click="tab = tb.k; loadList()">{{ t(tb.label) }}</button>
        <span v-if="list.length" class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ list.length }}</span>
      </div>
      <div v-if="listLoading" class="p-4 space-y-1.5">
        <span v-for="n in 6" :key="n" class="block h-10 rounded-lg bg-stone-100 animate-pulse" />
      </div>
      <div v-else-if="!list.length" class="p-10 text-center text-[12px] text-stone-400">
        {{ t('csl.listEmpty') }}
      </div>
      <ul v-else class="divide-y divide-stone-100">
        <li v-for="p in list" :key="p.key"
            class="px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50/70 cursor-pointer"
            @click="pick(p)">
          <span class="text-[12.5px] font-semibold text-stone-800 truncate max-w-[180px]">
            {{ p.name || t('csl.noName') }}</span>
          <span class="font-mono text-[11px] text-stone-400 tabular-nums" dir="ltr">{{ p.phone }}</span>
          <span v-if="p.via" class="text-[10px] font-semibold rounded-full px-2 py-0.5 bg-sky-50 text-sky-700">
            {{ p.via }}</span>
          <span v-if="p.unread" class="w-1.5 h-1.5 rounded-full bg-rose-500" />
          <span class="ms-auto flex items-center gap-2.5 text-[11px] text-stone-400 tabular-nums shrink-0" dir="ltr">
            <template v-if="p.orders">{{ p.orders }} · {{ Math.round(p.spend) }}</template>
            <span>{{ p.at ? local(p.at).slice(5, 16) : p.lastAt }}</span>
          </span>
        </li>
      </ul>
    </section>

    <!-- Raising a request: the kind and one line. Everything else is taken
         from the order the agent pressed it on. An agent mid-call does not
         fill a form — that is how the old Issue lane reached eight tickets
         in a year. -->
    <div v-if="raise" class="fixed inset-0 z-40 flex items-end sm:items-center justify-center bg-stone-900/40 px-4 pb-4 sm:pb-0"
         @click.self="raise = null">
      <div class="w-full max-w-sm bg-white rounded-2xl ring-1 ring-stone-200 shadow-xl p-4 space-y-3">
        <div class="text-[13px] font-bold text-stone-900">{{ t('csl.raiseTitle') }}</div>
        <div class="font-mono text-[11.5px] text-stone-500" dir="ltr">{{ raise.order }}</div>
        <div class="flex flex-wrap gap-1.5">
          <button v-for="k in KINDS" :key="k"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold transition-colors"
                  :class="raiseKind === k ? 'bg-[var(--accent-600)] text-white' : 'bg-stone-100 text-stone-700 hover:bg-stone-200'"
                  @click="raiseKind = k">{{ t('cs.k_' + k, k) }}</button>
        </div>
        <textarea v-model="raiseNote" rows="2" :placeholder="t('csl.raiseNote')"
                  class="w-full rounded-xl bg-stone-50 ring-1 ring-stone-200 px-3 py-2 text-[12.5px]
                         focus:outline-none focus:ring-2 focus:ring-[var(--accent-500)]" />
        <div v-if="raiseErr" class="text-[11.5px] text-rose-600">{{ raiseErr }}</div>
        <div class="flex gap-2">
          <button class="flex-1 h-9 rounded-lg text-[12.5px] font-semibold bg-stone-100 text-stone-700 hover:bg-stone-200"
                  @click="raise = null">{{ t('common.cancel') }}</button>
          <button :disabled="!raiseKind || raiseBusy"
                  class="flex-1 h-9 rounded-lg text-[12.5px] font-semibold text-white
                         bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-40"
                  @click="sendRaise()">{{ raiseBusy ? '…' : t('csl.raiseSend') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success } = useToast();
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

// ── the two lists ─────────────────────────────────────────────────────────
const TABS = [
  { k: "today", label: "csl.tabToday" },
  { k: "repeat", label: "csl.tabRepeat" },
];
const tab = ref("today");
const list = ref([]);
const listLoading = ref(false);

async function loadList() {
  listLoading.value = true;
  try {
    const res = await api("cs.lists", { kind: tab.value, limit: 40 });
    list.value = res.rows || [];
  } catch (_) {
    // A starting point, never the reason the screen fails: the search box
    // above still works.
    list.value = [];
  } finally {
    listLoading.value = false;
  }
}

function pick(p) {
  q.value = p.phone || p.key;
  run();
}

// ── raising a request from an order ───────────────────────────────────────
const KINDS = ["stock", "wrong_item", "exchange", "late", "damaged", "refund", "other"];
const raise = ref(null);
const raiseKind = ref("");
const raiseNote = ref("");
const raiseBusy = ref(false);
const raiseErr = ref("");

function openRaise(row) {
  raise.value = row;
  raiseKind.value = row.exchange ? "exchange" : "";
  raiseNote.value = "";
  raiseErr.value = "";
}

async function sendRaise() {
  if (!raiseKind.value || raiseBusy.value) return;
  raiseBusy.value = true;
  raiseErr.value = "";
  try {
    const res = await apiPost("cs.raise_request", {
      kind: raiseKind.value, note: raiseNote.value.trim(),
      order: raise.value.order, phone: raise.value.phone || "",
    });
    // The server merges a repeat into the open one rather than making the
    // desk reconcile two tickets for one problem — say which happened.
    success(res.merged ? t("csl.raiseMerged") : t("csl.raiseDone"), res.request || "");
    const on = raise.value.order;
    raise.value = null;
    // Refresh the card so the new request shows in the customer's list —
    // reading raise.value after nulling it was the bug here.
    if (cust.value?.found) loadCustomer({ phone: cust.value.phone, order: on });
  } catch (e) {
    raiseErr.value = String(e.message || e);
  } finally {
    raiseBusy.value = false;
  }
}

function exTitle(x) {
  const dir = x.direction ? ` · ${x.direction}` : "";
  const diff = x.diff ? ` ${Math.round(Math.abs(x.diff))}` : "";
  return `${x.other || ""} · ${x.status}${dir}${diff}`;
}

onMounted(async () => {
  await nextTick();
  box.value?.focus();
  if (q.value.trim().length >= 3) run();
  else loadList();
});
</script>
