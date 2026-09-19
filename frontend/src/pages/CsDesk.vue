<template>
  <div class="p-4 sm:p-5 max-w-[1100px] mx-auto">
    <!-- One control, one quiet line — the same shape the confirmation
         workspace settled on after eight competing chips proved unreadable. -->
    <div class="flex items-center gap-3 mb-2">
      <h1 class="text-[18px] font-bold text-stone-900 tracking-tight">{{ t('cs.title') }}</h1>
      <button v-if="freshN" class="ms-auto inline-flex items-center gap-2.5 h-11 px-5 rounded-2xl text-[13.5px] font-bold text-white bg-rose-600 hover:bg-rose-700 shadow-md"
              @click="applyFresh">
        <Icon name="zap" :size="16" />{{ t('cs.freshN').replace('{n}', freshN) }}
      </button>
      <button v-else class="ms-auto h-11 px-4 rounded-2xl text-[13px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
              :disabled="loading" @click="load()">
        <Icon name="refresh-cw" :size="14" class="inline -mt-px me-1" />{{ t('common.refresh') }}
      </button>
    </div>

    <!-- tabs -->
    <div class="flex items-center gap-1.5 flex-wrap mb-3">
      <button v-for="tb in TABS" :key="tb"
              class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-xl text-[12.5px] font-semibold transition-colors"
              :class="tab === tb ? 'text-white bg-violet-600' : 'text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50'"
              @click="goTab(tb)">
        {{ t('cs.tab_' + tb) }}
        <span class="tabular-nums text-[11px]" :class="tab === tb ? 'text-white/75' : 'text-stone-400'">{{
          tb === 'watch' ? (watchN ?? '–') : (data?.counts?.[tb] ?? '–') }}</span>
      </button>
      <input v-if="tab !== 'watch'" v-model="q" :placeholder="t('cs.searchPh')"
             class="ms-auto h-9 w-52 px-3 rounded-xl bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none"
             @input="debouncedLoad" />
    </div>

    <!-- kind filter: six types, a filter row rather than six more tabs -->
    <div v-if="tab !== 'watch'" class="flex items-center gap-1.5 flex-wrap mb-3">
      <button class="h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1"
              :class="!kindF ? 'text-white bg-stone-800 ring-stone-800' : 'text-stone-600 bg-white ring-stone-200'"
              @click="kindF = ''; load()">{{ t('cs.allKinds') }}</button>
      <button v-for="k in (data?.kinds || [])" :key="k"
              class="h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1 transition-all"
              :class="kindF === k ? 'text-white bg-violet-600 ring-violet-600' : KIND_CLS[k] || KIND_CLS.other"
              @click="kindF = kindF === k ? '' : k; load()">
        {{ t('cs.k_' + k) }}
        <span v-if="data?.counts?.byKind?.[k]" class="tabular-nums ms-1 opacity-70">{{ data.counts.byKind[k] }}</span>
      </button>
    </div>

    <!-- ── the watchlist ────────────────────────────────────────────────
         Not tickets. Exchanges that went wrong, computed fresh on every
         load, with the reason on each row. A row becomes a real request
         the moment someone takes it — which is also the moment it leaves
         this list. -->
    <template v-if="tab === 'watch'">
      <div class="flex items-center gap-1.5 flex-wrap mb-3">
        <button class="h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1"
                :class="!whyF ? 'text-white bg-stone-800 ring-stone-800' : 'text-stone-600 bg-white ring-stone-200'"
                @click="whyF = ''">{{ t('cs.allKinds') }}</button>
        <button v-for="w in WHY_ORDER" :key="w"
                class="h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1 transition-all"
                :class="whyF === w ? 'text-white bg-violet-600 ring-violet-600' : WHY_CLS[w]"
                @click="whyF = whyF === w ? '' : w">
          {{ t('cs.w_' + w) }}
          <span v-if="watch?.counts?.[w]" class="tabular-nums ms-1 opacity-70">{{ watch.counts[w] }}</span>
        </button>
        <span v-if="watch?.money" class="ms-auto text-[12px] font-semibold text-stone-500 tabular-nums" dir="ltr">
          {{ watch.money.toLocaleString() }} MAD</span>
      </div>

      <div v-if="loading" class="space-y-2.5">
        <div v-for="n in 5" :key="n" class="h-[72px] rounded-2xl bg-white ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <div v-else-if="!watchRows.length" class="rounded-2xl p-12 text-center bg-white ring-1 ring-stone-200/70">
        <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
        <div class="text-[15px] font-semibold text-stone-800">{{ t('cs.empty') }}</div>
      </div>
      <div v-else class="space-y-2">
        <div v-for="r in watchRows" :key="r.ref" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-3.5">
          <div class="flex items-start gap-3 flex-wrap">
            <span class="text-[10px] font-bold rounded-full px-2 py-0.5 ring-1 shrink-0 mt-0.5"
                  :class="WHY_CLS[r.why]">{{ t('cs.w_' + r.why) }}</span>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[14px] font-bold text-stone-900 truncate max-w-[200px]" dir="auto">{{ r.customer || '—' }}</span>
                <RouterLink v-if="r.order" :to="{ name: 'OrderDetail', params: { name: String(r.order).replace('#','') } }"
                            class="font-mono text-[11.5px] font-semibold text-stone-500 hover:underline" dir="ltr">{{ r.order }}</RouterLink>
                <!-- the replacement is a different parcel with a different
                     fate; showing only the original hides which one failed -->
                <RouterLink v-if="r.replacement" :to="{ name: 'OrderDetail', params: { name: String(r.replacement).replace('#','') } }"
                            class="font-mono text-[11px] text-violet-600 hover:underline" dir="ltr">→ {{ r.replacement }}</RouterLink>
                <span v-if="r.trackKey" class="text-[10.5px] rounded-full px-2 py-0.5 bg-stone-100 text-stone-600">{{ t('track.' + r.trackKey) }}</span>
              </div>
              <div class="flex items-center gap-2.5 mt-1 text-[11.5px] text-stone-500 flex-wrap">
                <span v-if="r.city">{{ r.city }}</span>
                <span v-if="r.phone" class="font-mono" dir="ltr">{{ r.phone }}</span>
                <span class="tabular-nums" :class="r.waitD >= 30 ? 'text-rose-600 font-semibold' : ''" dir="ltr">
                  {{ t('cs.waitedD').replace('{n}', r.waitD) }}</span>
                <span v-if="r.amount && r.weOwe" class="font-semibold text-amber-700 tabular-nums" dir="ltr">
                  {{ r.amount }} MAD</span>
              </div>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              <a v-if="r.phone" :href="waLink(r.phone)" target="_blank" rel="noopener"
                 class="h-9 w-9 inline-flex items-center justify-center rounded-lg text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200">
                <Icon name="message-circle" :size="14" /></a>
              <button class="h-9 px-3.5 rounded-lg text-[12px] font-bold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-40"
                      :disabled="busy === r.ref" @click="takeWatch(r)">{{ t('cs.takeIt') }}</button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else-if="loading" class="space-y-2.5">
      <div v-for="n in 5" :key="n" class="h-[92px] rounded-2xl bg-white ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="!rows.length" class="rounded-2xl p-12 text-center bg-white ring-1 ring-stone-200/70">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('cs.empty') }}</div>
    </div>

    <div v-else class="space-y-2.5">
      <div v-for="r in rows" :key="r.name" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-start gap-3 flex-wrap">
          <!-- The intake guesses the type from thin evidence and says so;
               retyping it is one tap, not an edit screen. -->
          <button class="text-[10px] font-bold rounded-full px-2 py-0.5 ring-1 shrink-0 mt-0.5"
                  :class="KIND_CLS[r.kind] || KIND_CLS.other"
                  :title="t('cs.retype')" @click="kindFor = kindFor === r.name ? '' : r.name">
            {{ t('cs.k_' + r.kind) }}</button>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[14px] font-bold text-stone-900 truncate max-w-[220px]" dir="auto">{{ r.customer || '—' }}</span>
              <RouterLink v-if="r.order" :to="{ name: 'OrderDetail', params: { name: String(r.order).replace('#','') } }"
                          class="font-mono text-[11.5px] font-semibold text-stone-500 hover:underline" dir="ltr">{{ r.order }}</RouterLink>
              <!-- 505 of 626 requests arrive with a phone and no order, and
                   on 53% of them the order is already in the table. Asking
                   the customer for a number we hold is the thing to stop. -->
              <button v-else class="text-[10.5px] font-semibold rounded-full px-2 py-0.5
                                    text-violet-700 bg-violet-50 ring-1 ring-violet-200 hover:bg-violet-100"
                      :disabled="candBusy === r.name" @click="findOrder(r)">
                <Icon name="search" :size="10" class="inline -mt-px me-0.5" />{{
                  candBusy === r.name ? '…' : t('cs.whichOrder') }}
              </button>
              <!-- where the parcel actually is, so "where is my order" never
                   costs the agent a second screen -->
              <span v-if="r.parcel?.track" class="text-[10px] font-semibold rounded-full px-2 py-0.5 bg-sky-50 text-sky-700 ring-1 ring-sky-200">{{ r.parcel.track }}</span>
              <span v-if="r.heldBy" class="text-[10px] font-bold rounded-full px-2 py-0.5 ring-1"
                    :class="r.heldMine ? 'text-teal-700 bg-teal-50 ring-teal-200' : 'text-stone-600 bg-stone-100 ring-stone-200'">
                {{ r.heldMine ? t('rs.heldMine') : r.heldBy }}</span>
              <span v-if="r.waitUntil" class="text-[10px] font-semibold rounded-full px-2 py-0.5 bg-amber-50 text-amber-700 ring-1 ring-amber-200" dir="ltr">
                <Icon name="hourglass" :size="10" class="inline -mt-px" /> {{ local(r.waitUntil).slice(5,10) }}</span>
              <span class="ms-auto text-[11px] text-stone-400 tabular-nums" dir="ltr">{{ age(r.ageMin) }}</span>
            </div>
            <div class="text-[12.5px] text-stone-700 mt-1 line-clamp-2" dir="auto">{{ r.note || '—' }}</div>
            <div class="text-[10.5px] text-stone-400 mt-1">
              {{ t('cs.src_' + r.source, r.source) }}<template v-if="r.raisedBy"> · {{ r.raisedBy }}</template>
            </div>
          </div>
        </div>

        <Transition name="rsslide">
          <div v-if="cand[r.name]" class="mt-2.5 rounded-xl bg-stone-50 ring-1 ring-stone-200/70 p-2.5">
            <!-- A Messenger page id is not a number: nobody can dial it and
                 there is nothing to look up. Say that instead of an empty
                 list, so the agent answers in the thread. -->
            <div v-if="cand[r.name].psid" class="text-[11.5px] text-stone-500">
              <Icon name="message-circle" :size="12" class="inline -mt-px me-1" />{{ t('cs.psidOnly') }}
            </div>
            <div v-else-if="!cand[r.name].rows.length" class="text-[11.5px] text-stone-500">
              {{ t('cs.noOrderFound') }}
            </div>
            <template v-else>
              <div class="text-[10.5px] font-semibold uppercase tracking-wide text-stone-400 mb-1.5">
                {{ t('cs.pickOrder') }} · {{ cand[r.name].total }}
              </div>
              <ul class="space-y-1">
                <li v-for="o in cand[r.name].rows" :key="o.order"
                    class="flex items-center gap-2 text-[11.5px] rounded-lg bg-white ring-1 ring-stone-200/70 px-2 py-1.5">
                  <span class="font-mono font-semibold text-stone-800" dir="ltr">{{ o.order }}</span>
                  <span class="text-stone-400 tabular-nums" dir="ltr">{{ local(o.date) }}</span>
                  <span v-if="o.city" class="text-stone-400 truncate max-w-[90px]">{{ o.city }}</span>
                  <span v-if="o.logistics" class="text-[10px] rounded-full px-1.5 py-0.5 bg-stone-100 text-stone-600">{{ o.logistics }}</span>
                  <span class="ms-auto tabular-nums text-stone-500">{{ Math.round(o.total) }}</span>
                  <button class="h-7 px-2 rounded-lg text-[11px] font-semibold text-white
                                 bg-violet-600 hover:bg-violet-700 disabled:opacity-40"
                          :disabled="busy === r.name" @click="attach(r, o.order)">{{ t('cs.attach') }}</button>
                </li>
              </ul>
            </template>
          </div>
        </Transition>

        <Transition name="rsslide">
          <div v-if="kindFor === r.name" class="mt-2.5 flex flex-wrap gap-1.5">
            <button v-for="k in (data?.kinds || [])" :key="k"
                    class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1"
                    :class="r.kind === k ? 'text-white bg-violet-600 ring-violet-600' : KIND_CLS[k] || KIND_CLS.other"
                    @click="setKind(r, k)">{{ t('cs.k_' + k) }}</button>
          </div>
        </Transition>

        <div class="mt-3 flex items-center gap-1.5 flex-wrap">
          <button v-if="!r.heldMine && r.state !== 'done'" class="cs-act text-teal-700" :disabled="busy === r.name" @click="take(r)">
            <Icon name="hand" :size="14" /> {{ t('rs.take') }}
          </button>
          <button v-if="r.heldMine" class="cs-act text-stone-500" :disabled="busy === r.name" @click="drop(r)">
            <Icon name="undo-2" :size="14" /> {{ t('rs.drop') }}
          </button>
          <button v-if="r.state !== 'done'" class="cs-act text-amber-700" :disabled="busy === r.name" @click="park(r)">
            <Icon name="hourglass" :size="14" /> {{ t('cs.wait') }}
          </button>
          <button v-if="r.state !== 'done'" class="cs-act text-emerald-700"
                  :class="doneFor === r.name ? 'ring-2' : ''" :disabled="busy === r.name"
                  @click="doneFor = doneFor === r.name ? '' : r.name">
            <Icon name="check" :size="14" /> {{ t('cs.resolve') }}
          </button>
          <a v-if="r.phone" :href="'tel:' + r.phone" class="cs-act text-stone-600"><Icon name="phone" :size="14" /></a>
          <a v-if="r.phone" :href="waLink(r.phone)" target="_blank" rel="noopener" class="cs-act text-emerald-600"><Icon name="message-circle" :size="14" /></a>
          <button class="cs-act text-sky-700 ms-auto" @click="openDesk(r)">
            <Icon name="notebook-pen" :size="14" /> {{ t('rs.desk') }}
          </button>
        </div>

        <Transition name="rsslide">
          <div v-if="doneFor === r.name" class="mt-2.5 flex items-center gap-2">
            <input v-model="resolution" :placeholder="t('cs.resolvePh')" maxlength="300"
                   class="flex-1 h-9 px-3 rounded-lg bg-emerald-50/60 ring-1 ring-emerald-200 text-[12.5px] focus:outline-none"
                   @keyup.enter="resolve(r)" />
            <button class="h-9 px-4 rounded-lg text-[12px] font-bold text-white bg-emerald-600 disabled:opacity-40"
                    :disabled="!resolution.trim() || busy === r.name" @click="resolve(r)">{{ t('cs.resolve') }}</button>
          </div>
        </Transition>

        <Transition name="rsslide">
          <div v-if="deskFor === r.name" class="mt-3 rounded-xl bg-stone-50 p-3 space-y-3">
            <div v-if="deskLoading" class="text-[12px] text-stone-400 text-center py-2">…</div>
            <template v-else>
              <!-- the customer's own words, when there is a thread -->
              <div v-if="desk?.thread?.length" class="space-y-1 max-h-44 overflow-y-auto">
                <div v-for="(m, i) in desk.thread" :key="i" class="flex" :class="m.from === 'customer' ? '' : 'justify-end'">
                  <span class="text-[12px] rounded-xl px-2.5 py-1.5 max-w-[80%] whitespace-pre-line" dir="auto"
                        :class="m.from === 'customer' ? 'bg-white ring-1 ring-stone-200 text-stone-800' : 'bg-violet-100 text-violet-900'">{{ m.text }}</span>
                </div>
              </div>
              <div v-for="(e, i) in (desk?.events || [])" :key="'e' + i" class="flex items-start gap-2 text-[12px]">
                <span class="text-stone-700 min-w-0 flex-1" dir="auto">{{ e.text }}</span>
                <span class="text-[10.5px] text-stone-400 tabular-nums shrink-0" dir="ltr">{{ e.by }} · {{ local(e.at).slice(5) }}</span>
              </div>
              <div class="flex items-center gap-2">
                <input v-model="noteText" :placeholder="t('rs.notePh')" maxlength="400"
                       class="flex-1 h-9 px-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none"
                       @keyup.enter="saveNote(r)" />
                <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-stone-800 disabled:opacity-40"
                        :disabled="!noteText.trim()" @click="saveNote(r)">{{ t('rs.noteSave') }}</button>
              </div>
            </template>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { local } from "@/lib/clock";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const route = useRoute();
const router = useRouter();

// `watch` is not a state of a request — it is work that has no request
// yet. It sits with the tabs because that is where the team already looks,
// not because it is the same kind of thing.
const TABS = ["new", "mine", "waiting", "done", "watch"];
const WHY_ORDER = ["never_started", "came_back", "never_moved", "refund_unpaid"];
const WHY_CLS = {
  never_started: "text-rose-700 bg-rose-50 ring-rose-200",
  came_back: "text-orange-700 bg-orange-50 ring-orange-200",
  never_moved: "text-amber-700 bg-amber-50 ring-amber-200",
  refund_unpaid: "text-sky-700 bg-sky-50 ring-sky-200",
};
const KIND_CLS = {
  stock: "text-rose-700 bg-rose-50 ring-rose-200",
  wrong_item: "text-orange-700 bg-orange-50 ring-orange-200",
  exchange: "text-violet-700 bg-violet-50 ring-violet-200",
  late: "text-amber-700 bg-amber-50 ring-amber-200",
  damaged: "text-red-700 bg-red-50 ring-red-200",
  refund: "text-sky-700 bg-sky-50 ring-sky-200",
  other: "text-stone-600 bg-stone-100 ring-stone-200",
};

const tab = ref(String(route.query.tab || "new"));
const kindF = ref(String(route.query.kind || ""));
const q = ref("");
const data = ref(null);
const rows = ref([]);
const loading = ref(true);
const busy = ref("");
const doneFor = ref("");
const resolution = ref("");
// Candidate orders for a request that arrived without one. Loaded per
// ticket on demand: one lookup reads the whole order table (~310ms) and
// thirty of them on the board would make the desk unusable.
const cand = ref({});
const candBusy = ref("");
const watch = ref(null);
const whyF = ref("");
// The tab badge must survive leaving the tab, so the count is kept apart
// from the payload and refreshed whenever the watchlist is read.
const watchN = ref(null);

const watchRows = computed(() => {
  const all = watch.value?.rows || [];
  return whyF.value ? all.filter((r) => r.why === whyF.value) : all;
});

async function findOrder(r) {
  if (cand.value[r.name]) { delete cand.value[r.name]; cand.value = { ...cand.value }; return; }
  candBusy.value = r.name;
  try {
    const res = await api("cs.candidates", { name: r.name });
    cand.value = { ...cand.value, [r.name]: res };
  } catch (e) {
    warn(String(e.message || e));
  } finally {
    candBusy.value = "";
  }
}

async function attach(r, order) {
  busy.value = r.name;
  try {
    await apiPost("cs.attach_order", { name: r.name, order });
    r.order = order;
    delete cand.value[r.name];
    cand.value = { ...cand.value };
    success(t("cs.attached"), order);
  } catch (e) {
    warn(String(e.message || e));
  } finally {
    busy.value = "";
  }
}
const kindFor = ref("");
const deskFor = ref("");
const desk = ref(null);
const deskLoading = ref(false);
const noteText = ref("");
const freshN = ref(0);
let since = "";
let qTimer = null;

function age(m) {
  if (m < 60) return m + "m";
  if (m < 1440) return Math.round(m / 60) + "h";
  return Math.round(m / 1440) + "d";
}
function waLink(p) {
  p = String(p || "").replace(/\D/g, "");
  return "https://wa.me/" + (p.startsWith("212") ? p : "212" + p.replace(/^0/, ""));
}
function syncUrl() {
  const query = {};
  if (tab.value !== "new") query.tab = tab.value;
  if (kindF.value) query.kind = kindF.value;
  if (JSON.stringify(query) !== JSON.stringify(route.query)) router.replace({ query }).catch(() => {});
}
function goTab(k) { if (tab.value === k) return; tab.value = k; load(); }
function debouncedLoad() { clearTimeout(qTimer); qTimer = setTimeout(load, 350); }

async function load() {
  syncUrl();
  loading.value = true;
  try {
    if (tab.value === "watch") {
      // limit 100 is the endpoint's own ceiling; the pile is 533 and the
      // top of it is the only part anyone will work today.
      const w = await api("cs.watchlist", { kind: "exchange", limit: 100 });
      watch.value = w;
      watchN.value = w.total ?? 0;
      return;
    }
    const r = await api("cs.board", { tab: tab.value, kind: kindF.value, q: q.value.trim() });
    data.value = r;
    rows.value = r.rows || [];
    freshN.value = 0;
  } catch (e) { warn(t("mv.loadFail"), String(e.message || e)); rows.value = []; }
  finally { loading.value = false; }
}
function applyFresh() { freshN.value = 0; load(); }

async function takeWatch(r) {
  busy.value = r.ref;
  try {
    const res = await apiPost("cs.take_watch", { kind: "exchange", ref: r.ref });
    // It is a ticket now, so it no longer belongs on a list of things with
    // no ticket. Drop it here rather than reloading the whole pile.
    watch.value = { ...watch.value, rows: (watch.value?.rows || []).filter((x) => x.ref !== r.ref) };
    watchN.value = Math.max(0, (watchN.value || 1) - 1);
    success(res.merged ? t("cs.mergedInto") : t("rs.tookIt"), r.customer || r.ref);
  } catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
  finally { busy.value = ""; }
}

async function take(r) {
  busy.value = r.name;
  try {
    const res = await apiPost("cs.claim", { name: r.name });
    if (!res.ok) { warn(t("rs.takenBy").replace("{who}", (res.by || "").split("@")[0]), r.name); return; }
    r.heldMine = true; r.heldBy = t("rs.heldMine");
    success(t("rs.tookIt"), r.customer || r.name);
  } catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
  finally { busy.value = ""; }
}
async function drop(r) {
  busy.value = r.name;
  try { await apiPost("cs.release", { name: r.name }); r.heldMine = false; r.heldBy = ""; }
  catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
  finally { busy.value = ""; }
}
async function park(r) {
  busy.value = r.name;
  try {
    const res = await apiPost("cs.wait", { name: r.name, days: 1, who: "customer" });
    r.waitUntil = res.until || "";
    success(t("rs.carrierParked"), local(res.until || "").slice(5, 10));
    load();
  } catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
  finally { busy.value = ""; }
}
async function resolve(r) {
  if (!resolution.value.trim()) return;
  busy.value = r.name;
  try {
    await apiPost("cs.resolve", { name: r.name, resolution: resolution.value.trim() });
    resolution.value = ""; doneFor.value = "";
    rows.value = rows.value.filter((x) => x.name !== r.name);
    success(t("cs.resolved"), r.customer || r.name);
  } catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
  finally { busy.value = ""; }
}
async function setKind(r, k) {
  try {
    await apiPost("cs.set_kind", { name: r.name, kind: k });
    r.kind = k;
    kindFor.value = "";
  } catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
}

async function openDesk(r) {
  if (deskFor.value === r.name) { deskFor.value = ""; return; }
  deskFor.value = r.name; desk.value = null; noteText.value = ""; deskLoading.value = true;
  try { desk.value = await api("cs.timeline", { name: r.name }); }
  catch (e) { warn(t("mv.loadFail"), String(e.message || e)); }
  finally { deskLoading.value = false; }
}
async function saveNote(r) {
  const text = noteText.value.trim();
  if (!text) return;
  try {
    await apiPost("cs.note", { name: r.name, text });
    noteText.value = "";
    desk.value = await api("cs.timeline", { name: r.name });
  } catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
}

// Same heartbeat as the other two desks: cheap, and it lights a button
// rather than moving the list under someone who is reading it.
const beat = setInterval(async () => {
  if (document.visibilityState !== "visible" || loading.value) return;
  try {
    const r = await api("cs.pulse", { since });
    since = r.now || since;
    if (r.n) freshN.value += r.n;
  } catch { /* a heartbeat must never break the screen */ }
}, 30000);

onMounted(load);
onUnmounted(() => { clearInterval(beat); clearTimeout(qTimer); });
</script>

<style scoped>
.cs-act {
  display: inline-flex; align-items: center; gap: .35rem;
  height: 2rem; padding: 0 .7rem; border-radius: .6rem;
  font-size: 12px; font-weight: 600; background: #fff;
  box-shadow: inset 0 0 0 1px rgb(231 229 228); transition: background .15s;
}
.cs-act:hover { background: rgb(250 250 249); }
.cs-act:disabled { opacity: .4; }
</style>
