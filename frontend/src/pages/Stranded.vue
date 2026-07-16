<template>
  <div class="p-5 sm:p-6 max-w-[1400px] mx-auto animate-fade-in">
    <!-- header -->
    <div class="flex items-start justify-between gap-4 flex-wrap mb-4">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t("st.title") }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t("st.subtitle") }}</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center rounded-lg ring-1 ring-stone-200 bg-white p-0.5">
          <button
            v-for="w in WINDOWS"
            :key="w.k"
            class="px-3 h-8 text-[12px] font-medium rounded-md transition-colors whitespace-nowrap"
            :class="win === w.k ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-800'"
            @click="setWin(w.k)"
          >{{ t("st.w_" + w.k) }}</button>
        </div>
        <button
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          @click="load()"
        >
          <Icon name="refresh-cw" :size="15" :class="loading ? 'animate-spin' : ''" />{{ t("common.refresh") }}
        </button>
      </div>
    </div>

    <!-- outage -->
    <div v-if="loadError" class="bg-white rounded-xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t("common.loadFail") }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[420px] mx-auto break-words">{{ loadError }}</div>
      <button
        class="mt-4 h-8 px-3 inline-flex items-center gap-1.5 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 hover:ring-stone-300 transition-all"
        @click="load()"
      ><Icon name="refresh-cw" :size="14" />{{ t("common.refresh") }}</button>
    </div>

    <template v-else>
      <!-- the three verdicts: each is a different person's job -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        <button
          v-for="b in BUCKETS"
          :key="b.k"
          class="st-card text-start"
          :class="[bucket === b.k ? 'st-card-on' : '', 'st-' + b.k]"
          @click="setBucket(b.k)"
        >
          <div class="flex items-start gap-3">
            <div class="st-ico" :class="'st-ico-' + b.k">
              <Icon :name="b.icon" :size="18" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-semibold text-stone-900">{{ t("st.b_" + b.k) }}</div>
              <div class="text-[11.5px] text-stone-500 mt-0.5 leading-snug">{{ t("st.d_" + b.k) }}</div>
            </div>
          </div>
          <div v-if="loading" class="mt-3 h-8 w-28 rounded bg-stone-100 animate-pulse" />
          <div v-else class="mt-3 flex items-baseline gap-2">
            <span class="text-[26px] font-semibold tabular-nums leading-none"
                  :class="(counts[b.k]?.orders || 0) > 0 ? 'text-stone-900' : 'text-stone-300'">
              {{ counts[b.k]?.orders || 0 }}
            </span>
            <span class="text-[12px] text-stone-500 tabular-nums">{{ fmtMAD(counts[b.k]?.value || 0) }}</span>
          </div>
          <div class="mt-2 text-[11px] font-medium" :class="'st-who-' + b.k">
            <Icon name="arrow-right" :size="11" class="inline flip-rtl me-0.5" />{{ t("st.who_" + b.k) }}
          </div>
        </button>
      </div>

      <!-- rows -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="px-4 py-3 border-b border-stone-100 flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div class="text-[13px] font-semibold text-stone-900">
              {{ bucket ? t("st.b_" + bucket) : t("st.allStuck") }}
            </div>
            <div class="text-[11px] text-stone-400 tabular-nums">
              {{ total }} {{ t("st.orders") }} · {{ fmtMAD(pageValue) }}
            </div>
          </div>
          <button
            v-if="bucket"
            class="text-[12px] font-medium text-stone-500 hover:text-stone-900 inline-flex items-center gap-1"
            @click="setBucket('')"
          ><Icon name="x" :size="13" />{{ t("st.clearFilter") }}</button>
        </div>

        <div v-if="loading" class="divide-y divide-stone-100">
          <div v-for="n in 6" :key="n" class="px-4 py-3.5 flex items-center gap-4">
            <div class="h-3.5 w-36 rounded bg-stone-100 animate-pulse" />
            <div class="h-3.5 w-44 rounded bg-stone-100 animate-pulse" />
            <div class="h-3.5 w-20 rounded bg-stone-100 animate-pulse ms-auto" />
          </div>
        </div>

        <div v-else-if="!rows.length" class="text-center py-14">
          <Icon name="check-circle" :size="26" class="mx-auto mb-2 text-emerald-500" />
          <div class="text-[13px] font-semibold text-stone-800">{{ t("st.emptyTitle") }}</div>
          <div class="text-[12px] text-stone-400 mt-1">{{ t("st.emptySub") }}</div>
        </div>

        <div v-else class="divide-y divide-stone-100">
          <div v-for="r in rows" :key="r.order" class="px-4 py-3 hover:bg-stone-50/70 transition-colors">
            <div class="flex items-start gap-3 flex-wrap">
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <button class="text-[13px] font-semibold text-stone-900 tabular-nums hover:underline"
                          @click="openOrder(r.order)">{{ r.order }}</button>
                  <span class="st-chip" :class="'st-chip-' + r.bucket">{{ t("st.b_" + r.bucket) }}</span>
                  <span class="st-age" :class="ageTone(r.ageDays)">{{ r.ageDays }}{{ t("st.dSuffix") }}</span>
                </div>
                <div class="text-[12px] text-stone-500 mt-0.5 truncate">
                  {{ r.customer }} · {{ r.city }}
                  <span v-if="r.agent !== '—'" class="text-stone-400"> · {{ r.agent }}</span>
                </div>
              </div>
              <div class="text-[13px] font-semibold text-stone-900 tabular-nums whitespace-nowrap">
                {{ fmtMAD(r.value) }}
              </div>
              <a
                v-if="r.phone"
                :href="'tel:' + r.phone"
                class="inline-flex items-center justify-center w-8 h-8 rounded-lg ring-1 ring-stone-200 text-stone-600 hover:bg-stone-100 transition-colors"
                :title="t('st.call')"
              ><Icon name="phone" :size="14" /></a>
            </div>

            <!-- what is actually missing, and where it is -->
            <div v-if="r.short.length" class="mt-2 space-y-1">
              <div v-for="(l, i) in r.short" :key="i"
                   class="flex items-center gap-2 flex-wrap text-[11.5px] rounded-lg px-2.5 py-1.5"
                   :class="l.why === 'zone' ? 'bg-amber-50/70 ring-1 ring-amber-200/60' : 'bg-rose-50/60 ring-1 ring-rose-200/50'">
                <span class="font-mono text-[11px] text-stone-700">{{ l.sku }}</span>
                <span class="text-stone-500 truncate flex-1 min-w-[100px]">{{ l.item }}</span>
                <span class="text-stone-600 tabular-nums whitespace-nowrap">
                  {{ t("st.need") }} {{ l.want }} · {{ t("st.onShelf") }} {{ l.pickable }}
                </span>
                <span v-if="l.why === 'zone'" class="text-amber-800 font-medium tabular-nums whitespace-nowrap">
                  {{ l.elsewhere }} {{ t("st.elsewhere") }}
                </span>
                <span v-else class="text-rose-700 font-medium whitespace-nowrap">{{ t("st.noneInMa") }}</span>
                <button
                  class="inline-flex items-center gap-1 h-6 px-2 rounded-md text-[11px] font-medium ring-1 ring-stone-200 bg-white text-stone-600 hover:bg-stone-50 whitespace-nowrap"
                  @click="findStock(l)"
                ><Icon name="search" :size="11" />{{ t("st.locate") }}</button>
              </div>
            </div>
            <div v-else class="mt-2 text-[11.5px] text-emerald-700 bg-emerald-50/70 ring-1 ring-emerald-200/60 rounded-lg px-2.5 py-1.5 inline-flex items-center gap-1.5">
              <Icon name="check-circle" :size="12" />{{ t("st.readyNote") }}
            </div>
          </div>
        </div>

        <div v-if="!loading && total > pageSize" class="px-4 py-2.5 border-t border-stone-100">
          <Pager v-model:page="page" v-model:pageSize="pageSize" :total="total" />
        </div>
      </div>

      <p class="text-[11.5px] text-stone-400 mt-3 leading-relaxed max-w-[760px]">{{ t("st.footnote") }}</p>
    </template>

    <!-- where is this stock -->
    <Teleport to="body">
      <div v-if="locate" class="fixed inset-0 z-50 flex justify-end">
        <div class="absolute inset-0 bg-stone-900/30" @click="locate = null" />
        <div class="relative w-full max-w-md h-full bg-white shadow-2xl flex flex-col animate-fade-in">
          <header class="px-5 py-4 border-b border-stone-100 flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h3 class="text-[14.5px] font-semibold text-stone-900 truncate">{{ locate.sku }}</h3>
              <p class="text-[12px] text-stone-500 mt-0.5 truncate">{{ locate.item }}</p>
            </div>
            <button :title="t('common.close')" class="w-8 h-8 rounded-lg hover:bg-stone-100 flex items-center justify-center flex-shrink-0"
                    @click="locate = null"><Icon name="x" :size="16" /></button>
          </header>
          <div class="flex-1 overflow-y-auto p-4">
            <div v-if="locBusy" class="space-y-2">
              <div v-for="n in 4" :key="n" class="h-11 rounded-lg bg-stone-100 animate-pulse" />
            </div>
            <div v-else-if="locError" class="text-center py-10">
              <Icon name="alert-triangle" :size="20" class="mx-auto mb-2 text-rose-500" />
              <div class="text-[13px] font-semibold text-stone-800">{{ t("common.loadFail") }}</div>
              <div class="text-[11.5px] text-stone-400 font-mono mt-1 break-words">{{ locError }}</div>
            </div>
            <div v-else-if="!locRows.length" class="text-center py-10 text-[12.5px] text-stone-400">
              {{ t("st.locNone") }}
            </div>
            <div v-else class="space-y-1.5">
              <div v-for="(b, i) in locRows" :key="i"
                   class="flex items-center gap-2 rounded-lg px-3 py-2.5 ring-1"
                   :class="b.pickable ? 'bg-emerald-50/60 ring-emerald-200/60' : 'bg-stone-50 ring-stone-200/70'">
                <Icon :name="b.pickable ? 'check-circle' : 'circle-pause'" :size="14"
                      :class="b.pickable ? 'text-emerald-600' : 'text-stone-400'" />
                <span class="text-[12.5px] text-stone-800 flex-1 truncate">{{ b.warehouse }}</span>
                <span class="text-[12.5px] font-semibold text-stone-900 tabular-nums">{{ b.qty }}</span>
              </div>
              <p class="text-[11px] text-stone-400 mt-3 leading-relaxed">{{ t("st.locNote") }}</p>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import Pager from "@/components/ui/Pager.vue";
import { fmtMAD } from "@/lib/handoffData";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const router = useRouter();
const { t } = useI18n();

// The three verdicts, in the order a manager should read them: what we could
// ship today, what one trip to the right shelf would fix, what we simply
// cannot ship.
const BUCKETS = [
  { k: "ready", icon: "package-check" },
  { k: "zone", icon: "route" },
  { k: "nostock", icon: "circle-x" },
];

// Under a month = the customer might still take it. Older is a different
// conversation, so it is a deliberate choice, not the default view.
const WINDOWS = [
  { k: "live", lo: 3, hi: 30 },
  { k: "all", lo: 3, hi: 3650 },
];

const rows = ref([]);
const counts = ref({});
const total = ref(0);
const pageValue = ref(0);
const loading = ref(false);
const loadError = ref("");
const bucket = ref("");
const win = ref("live");
const page = ref(1);
const pageSize = ref(20);

const winDef = computed(() => WINDOWS.find((w) => w.k === win.value) || WINDOWS[0]);

async function load() {
  loading.value = true;
  try {
    const r = await api("stranded.board", {
      bucket: bucket.value || undefined,
      min_age: winDef.value.lo,
      max_age: winDef.value.hi,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    });
    rows.value = r.rows || [];
    counts.value = r.counts || {};
    total.value = r.total || 0;
    pageValue.value = r.value || 0;
    loadError.value = "";
  } catch (e) {
    loadError.value = String(e.message || e);
    rows.value = [];
    counts.value = {};
    total.value = 0;
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch([page, pageSize], load);

function setBucket(k) {
  bucket.value = bucket.value === k ? "" : k;
  page.value = 1;
  load();
}
function setWin(k) {
  win.value = k;
  page.value = 1;
  load();
}
function openOrder(name) {
  router.push({ name: "OrderDetail", params: { name } });
}

function ageTone(d) {
  if (d >= 30) return "st-age-bad";
  if (d >= 7) return "st-age-warn";
  return "st-age-ok";
}

// ── where is this stock ────────────────────────────────────────────
const locate = ref(null);
const locRows = ref([]);
const locBusy = ref(false);
const locError = ref("");

async function findStock(line) {
  locate.value = line;
  locRows.value = [];
  locError.value = "";
  locBusy.value = true;
  try {
    locRows.value = (await api("stranded.where_is", { item_code: line.itemCode || line.sku })) || [];
  } catch (e) {
    locError.value = String(e.message || e);
  } finally {
    locBusy.value = false;
  }
}
</script>
