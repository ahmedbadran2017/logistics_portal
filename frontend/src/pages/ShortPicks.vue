<template>
  <div class="p-5 sm:p-6 max-w-[1400px] mx-auto animate-fade-in">
    <!-- header -->
    <div class="flex items-start justify-between gap-4 flex-wrap mb-4">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t("sp.title") }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[640px]">{{ t("sp.subtitle") }}</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <div class="flex items-center rounded-lg ring-1 ring-stone-200 bg-white p-0.5">
          <button
            v-for="s in SHOWS" :key="s"
            class="px-3 h-8 text-[12px] font-medium rounded-md transition-colors whitespace-nowrap"
            :class="show === s ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-800'"
            @click="setShow(s)"
          >{{ t("sp.show_" + s) }}<span class="ms-1 tabular-nums opacity-70">{{ s === "open" ? meta.open : meta.checked }}</span></button>
        </div>
        <div class="flex items-center rounded-lg ring-1 ring-stone-200 bg-white p-0.5">
          <button
            v-for="d in DAYS" :key="d"
            class="px-2.5 h-8 text-[12px] font-medium rounded-md transition-colors tabular-nums"
            :class="days === d ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-800'"
            @click="setDays(d)"
          >{{ d }}{{ t("sp.dShort") }}</button>
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
      <!-- three verdicts, read top to bottom: likely wrong, needs a move, truly gone -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        <button
          v-for="b in BUCKETS" :key="b.k"
          class="st-card text-start"
          :class="[bucket === b.k ? 'st-card-on' : '', 'st-' + b.k]"
          @click="bucket = bucket === b.k ? '' : b.k"
        >
          <div class="flex items-start gap-3">
            <div class="st-ico" :class="'st-ico-' + b.k"><Icon :name="b.icon" :size="18" /></div>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-semibold text-stone-900">{{ t("sp.b_" + b.k) }}</div>
              <div class="text-[11.5px] text-stone-500 mt-0.5 leading-snug">{{ t("sp.d_" + b.k) }}</div>
            </div>
          </div>
          <div v-if="loading" class="mt-3 h-8 w-20 rounded bg-stone-100 animate-pulse" />
          <div v-else class="mt-3 text-[26px] font-semibold tabular-nums leading-none"
               :class="(counts[b.k] || 0) > 0 ? 'text-stone-900' : 'text-stone-300'">{{ counts[b.k] || 0 }}</div>
          <div class="mt-2 text-[11px] font-medium" :class="'st-who-' + b.k">
            <Icon name="arrow-right" :size="11" class="inline flip-rtl me-0.5" />{{ t("sp.who_" + b.k) }}
          </div>
        </button>
      </div>

      <!-- rows -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70">
        <div class="px-4 py-3 border-b border-stone-100 flex items-center justify-between gap-3 flex-wrap">
          <div class="text-[13px] font-semibold text-stone-900">
            {{ bucket ? t("sp.b_" + bucket) : t("sp.all") }}
            <span class="text-[11px] font-normal text-stone-400 tabular-nums ms-1">{{ visible.length }}</span>
          </div>
          <button v-if="bucket" class="text-[12px] font-medium text-stone-500 hover:text-stone-900 inline-flex items-center gap-1"
                  @click="bucket = ''"><Icon name="x" :size="13" />{{ t("st.clearFilter") }}</button>
        </div>

        <div v-if="loading" class="divide-y divide-stone-100">
          <div v-for="n in 6" :key="n" class="px-4 py-3.5 flex items-center gap-4">
            <div class="h-10 w-10 rounded-lg bg-stone-100 animate-pulse" />
            <div class="h-3.5 w-44 rounded bg-stone-100 animate-pulse" />
            <div class="h-3.5 w-24 rounded bg-stone-100 animate-pulse ms-auto" />
          </div>
        </div>

        <div v-else-if="!visible.length" class="text-center py-14">
          <Icon name="check-circle" :size="26" class="mx-auto mb-2 text-emerald-500" />
          <div class="text-[13px] font-semibold text-stone-800">{{ t(show === "open" ? "sp.emptyOpen" : "sp.emptyChecked") }}</div>
        </div>

        <div v-else class="divide-y divide-stone-100">
          <div v-for="r in visible" :key="r.order + r.item" class="px-4 py-3 hover:bg-stone-50/60 transition-colors">
            <div class="flex items-start gap-3 flex-wrap">
              <img v-if="r.image" :src="r.image" class="w-11 h-11 rounded-lg object-cover ring-1 ring-stone-200 flex-shrink-0" />
              <div v-else class="w-11 h-11 rounded-lg bg-stone-100 flex-shrink-0 flex items-center justify-center">
                <Icon name="package" :size="16" class="text-stone-400" />
              </div>

              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <button class="text-[13px] font-semibold text-stone-900 tabular-nums hover:underline"
                          @click="openOrder(r.order)">{{ r.order }}</button>
                  <span class="st-chip" :class="'st-chip-' + r.verdict">{{ t("sp.b_" + r.verdict) }}</span>
                  <!-- the repeat is the message: the same order sent back to
                       the same empty shelf again and again -->
                  <span class="st-age tabular-nums" :class="r.times >= 5 ? 'st-age-bad' : r.times >= 2 ? 'st-age-warn' : 'st-age-ok'">
                    ×{{ r.times }}
                  </span>
                  <span class="st-age st-age-ok tabular-nums">{{ ago(r.hours) }}</span>
                  <span v-if="r.onList" class="st-age st-age-ok">{{ t("sp.onList") }} {{ r.onList }}</span>
                </div>
                <div class="text-[12px] text-stone-800 mt-0.5 truncate">{{ r.name }}</div>
                <div class="text-[11px] text-stone-400 mt-0.5 truncate">
                  <span class="font-mono">{{ r.sku || r.item }}</span> · {{ r.customer }}
                  · {{ t("sp.by") }} {{ shortUser(r.picker) }} · {{ r.pickList }}
                </div>
                <div v-if="r.tote" class="mt-1 text-[11px] font-medium text-rose-700 inline-flex items-center gap-1">
                  <Icon name="alert-triangle" :size="11" />{{ t("sp.tote") }}
                </div>

                <!-- what the ledger says, bin by bin -->
                <div class="mt-2 flex flex-wrap gap-1.5">
                  <span v-if="!r.bins.length" class="text-[11px] text-rose-700 bg-rose-50/70 ring-1 ring-rose-200/60 rounded-md px-2 py-1">
                    {{ t("sp.noBins") }}
                  </span>
                  <span v-for="b in r.bins" :key="b.warehouse"
                        class="text-[11px] rounded-md px-2 py-1 ring-1 tabular-nums"
                        :class="b.cls === 'pick' ? 'bg-emerald-50/70 ring-emerald-200/60 text-emerald-800'
                              : 'bg-amber-50/70 ring-amber-200/60 text-amber-800'">
                    {{ short(b.warehouse) }} · {{ b.free }}
                    <span v-if="b.held" class="text-stone-500">({{ t("sp.held") }} {{ b.held }})</span>
                  </span>
                </div>

                <div v-if="r.ruling" class="mt-2 text-[11px] text-stone-500">
                  {{ t("sp.ruled_" + r.ruling.verdict) }} · {{ shortUser(r.ruling.by) }} · {{ r.ruling.at }}
                </div>
              </div>

              <!-- the double-check -->
              <div v-if="show === 'open'" class="flex items-center gap-1.5 flex-wrap self-center">
                <button
                  class="inline-flex items-center gap-1 h-8 px-2.5 rounded-lg text-[12px] font-semibold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
                  :disabled="busy === r.order + r.item" @click="doRule(r, 'present')"
                ><Icon name="check" :size="13" />{{ t("sp.present") }}</button>
                <button
                  class="inline-flex items-center gap-1 h-8 px-2.5 rounded-lg text-[12px] font-semibold text-rose-700 bg-white ring-1 ring-rose-200 hover:bg-rose-50 disabled:opacity-50"
                  :disabled="busy === r.order + r.item" @click="doRule(r, 'missing')"
                ><Icon name="x" :size="13" />{{ t("sp.missing") }}</button>
                <button v-if="r.verdict === 'zone'"
                  class="inline-flex items-center gap-1 h-8 px-2.5 rounded-lg text-[12px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
                  @click="goMove(r)"
                ><Icon name="route" :size="13" />{{ t("sp.move") }}</button>
                <button v-if="r.verdict === 'ready'"
                  class="inline-flex items-center gap-1 h-8 px-2.5 rounded-lg text-[12px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
                  @click="goCount(r)"
                ><Icon name="list-checks" :size="13" />{{ t("sp.count") }}</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <p class="text-[11.5px] text-stone-400 mt-3 leading-relaxed max-w-[760px]">{{ t("sp.footnote") }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const router = useRouter();
const { t } = useI18n();
const { success, warn } = useToast();

// Read in this order: the ledger says the picker is wrong, the piece is in a
// zone picking skips, the ledger agrees it is gone. Keys reuse the Stranded
// palette (green / amber / rose) so the two radars read the same way.
const BUCKETS = [
  { k: "ready", icon: "search" },
  { k: "zone", icon: "route" },
  { k: "nostock", icon: "circle-x" },
];
const SHOWS = ["open", "checked"];
const DAYS = [7, 14, 30];

const rows = ref([]);
const counts = ref({});
const meta = ref({ open: 0, checked: 0 });
const loading = ref(false);
const loadError = ref("");
const bucket = ref("");
const show = ref("open");
const days = ref(14);
const busy = ref("");

const visible = computed(() => (bucket.value ? rows.value.filter((r) => r.verdict === bucket.value) : rows.value));

async function load() {
  loading.value = true;
  try {
    const r = await api("short_shelf.radar", { days: days.value, show: show.value });
    rows.value = r.rows || [];
    counts.value = r.counts || {};
    meta.value = { open: r.open || 0, checked: r.checked || 0 };
    loadError.value = "";
  } catch (e) {
    loadError.value = String(e.message || e);
    rows.value = [];
  } finally {
    loading.value = false;
  }
}
onMounted(load);

function setShow(s) { show.value = s; bucket.value = ""; load(); }
function setDays(d) { days.value = d; load(); }

async function doRule(r, verdict) {
  busy.value = r.order + r.item;
  try {
    // The bin the manager most likely walked to: the first pickable one.
    const wh = (r.bins.find((b) => b.cls === "pick") || r.bins[0] || {}).warehouse;
    const res = await apiPost("short_shelf.rule", {
      order: r.order, item_code: r.item, verdict, warehouse: wh || undefined,
    });
    if (res.needsCount) {
      // Found on the shelf but the books have nothing to allocate: the order
      // cannot come back until the shelf is counted up.
      warn(t("sp.needsCount"), r.sku || r.item);
    } else {
      success(t(verdict === "present" ? "sp.donePresent" : "sp.doneMissing"), `${r.order} · ${r.sku || r.item}`);
    }
    await load();
  } catch (e) {
    warn(t("common.loadFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

function openOrder(name) { router.push({ name: "OrderDetail", params: { name } }); }
function goMove(r) { router.push({ name: "MoveStock", query: { item: r.sku || r.item } }); }
function goCount(r) {
  const b = r.bins.find((x) => x.cls === "pick");
  router.push({ name: "CycleCount", query: b ? { bin: b.warehouse } : {} });
}
function short(w) { return String(w || "").replace(/ - JM$/, ""); }
function shortUser(u) { return String(u || "").split("@")[0]; }
function ago(h) {
  if (h < 1) return t("sp.justNow");
  if (h < 48) return `${h}${t("sp.hShort")}`;
  return `${Math.floor(h / 24)}${t("sp.dShort")}`;
}
</script>
