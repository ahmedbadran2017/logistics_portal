<template>
  <div v-if="suggest" class="fixed inset-0 z-[150] flex items-center justify-center p-4" role="dialog" aria-modal="true">
    <div class="absolute inset-0 bg-stone-900/30 backdrop-blur-[1px] animate-fade-in" @click="suggest = null" />
    <div class="relative w-full max-w-[760px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] animate-scale-in overflow-hidden flex flex-col max-h-[88vh]">
      <header class="flex items-center justify-between px-5 py-3.5 border-b border-stone-100">
        <div class="flex items-center gap-2.5">
          <span class="w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center" v-html="zapIcon(16)" />
          <div>
            <div class="text-[14.5px] font-semibold text-stone-900">{{ t("pl.sbTitle") }}</div>
            <div v-if="suggest.data" class="text-[11.5px] text-stone-500">
              {{ t("pl.sbSub").replace("{n}", suggest.data.poolTotal).replace("{b}", suggest.data.batched).replace("{o}", suggest.data.oos.length) }}
            </div>
          </div>
        </div>
        <button class="w-8 h-8 rounded-lg hover:bg-stone-100 flex items-center justify-center text-stone-400" @click="suggest = null">
          <Icon name="x" :size="16" />
        </button>
      </header>

      <div class="p-4 overflow-y-auto space-y-2.5">
        <div v-if="suggest.loading" class="space-y-2.5">
          <div v-for="n in 4" :key="n" class="h-20 rounded-xl bg-stone-100 animate-pulse" />
        </div>
        <template v-else-if="suggest.data">
          <div v-if="!suggest.data.batches.length" class="text-center text-[13px] text-emerald-600 py-10">{{ t("pl.sbEmpty") }}</div>

          <div class="flex items-center justify-between gap-2 px-0.5 flex-wrap">
            <div class="flex items-center gap-1.5">
              <button class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold ring-1 ring-stone-200 bg-white text-stone-600 hover:ring-stone-300" @click="selectTop">{{ t("pl.sbSelTop") }}</button>
              <button class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold ring-1 ring-stone-200 bg-white text-stone-600 hover:ring-stone-300" @click="picked = new Set()">{{ t("pl.sbSelNone") }}</button>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="text-[11px] text-stone-400">{{ t("pl.sbSize") }}</span>
              <div class="flex items-center rounded-lg ring-1 ring-stone-200 bg-white p-0.5">
                <button v-for="c in [15, 20, 25]" :key="c"
                        class="px-2 h-6 text-[11.5px] font-semibold rounded-md transition-colors"
                        :class="capSel === c ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-800'"
                        @click="capSel = c; openSuggest()">{{ c }}</button>
              </div>
            </div>
            <span class="text-[11px] text-stone-400">{{ t("pl.sbPickHint") }}</span>
          </div>

          <div v-for="b in suggest.data.batches" :key="b.key"
               class="rounded-xl ring-1 p-3 transition-all cursor-pointer select-none"
               :class="picked.has(b.key) ? 'ring-[var(--accent-300)] bg-[var(--accent-50)]/30' : 'ring-stone-200 opacity-60 hover:opacity-90'"
               @click="toggleBatch(b.key)">
            <div class="flex items-center gap-2.5 flex-wrap">
              <button class="w-4.5 h-4.5 w-[18px] h-[18px] rounded flex items-center justify-center ring-1 flex-shrink-0 transition-colors"
                      :class="picked.has(b.key) ? 'bg-[var(--accent-600)] ring-[var(--accent-600)] text-white' : 'ring-stone-300 bg-white'"
                      @click.stop="toggleBatch(b.key)">
                <Icon v-if="picked.has(b.key)" name="check" :size="12" />
              </button>
              <span class="font-mono text-[11px] font-bold text-stone-400">{{ b.key }}</span>
              <span class="inline-flex items-center px-1.5 h-[18px] rounded text-[10.5px] font-semibold ring-1 whitespace-nowrap" :class="sbKindCls(b.kind)">
                {{ sbKindLabel(b.kind) }}
              </span>
              <span class="text-[12.5px] font-medium text-stone-900 truncate max-w-[220px]" :title="b.label">
                {{ b.kind === 'mono' ? b.label : b.kind === 'mixed' ? '—' : (b.label === 'STG' ? 'Staging' : b.label) }}
              </span>
              <span v-if="b.late" class="inline-flex items-center px-1.5 h-[18px] rounded text-[10px] font-bold text-rose-600 bg-rose-50 ring-1 ring-rose-200/60 tabular-nums whitespace-nowrap">
                ⏰ {{ b.late }} {{ t("pl.sbLate") }}
              </span>
              <div class="ms-auto flex items-center gap-1.5">
                <span class="text-[10.5px] text-stone-400">{{ t("pl.sbPicker") }}</span>
                <select v-model="pickerFor[b.key]"
                        class="h-8 ps-2.5 pe-6 rounded-lg bg-white ring-1 ring-stone-200 text-[12px] text-stone-700 appearance-none cursor-pointer focus:outline-none"
                        @click.stop>
                  <option value="">{{ t("pl.sbUnassigned") }}</option>
                  <option v-for="p in sbPickers" :key="p.email" :value="p.email">{{ p.name }} ({{ p.load }})</option>
                </select>
              </div>
            </div>
            <div class="flex items-center gap-3 mt-2 text-[11px] text-stone-500 tabular-nums flex-wrap">
              <span>{{ b.orders.length }} {{ t("pl.sbOrders") }}</span><span class="text-stone-300">·</span>
              <span>{{ b.lines.length }} {{ t("pl.sbLines") }}</span><span class="text-stone-300">·</span>
              <span>{{ b.units }} {{ t("pl.sbUnits") }}</span><span class="text-stone-300">·</span>
              <span class="inline-flex items-center gap-1"><Icon name="map-pin" :size="10" />{{ b.aisles.join(", ") }}</span><span class="text-stone-300">·</span>
              <span class="font-semibold text-[var(--accent-700)]">~{{ b.est }}m</span>
            </div>
            <div class="mt-2 space-y-1">
              <div v-for="(l, i) in b.lines.slice(0, 2)" :key="i" class="flex items-center gap-2 text-[11.5px]">
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stone-900 text-white text-[10px] font-bold font-mono flex-shrink-0"><Icon name="map-pin" :size="9" />{{ l.bin.replace(" - JM", "") }}</span>
                <span class="text-stone-700 truncate flex-1">{{ l.name }}</span>
                <span class="font-semibold text-stone-900 tabular-nums flex-shrink-0">×{{ l.qty }}</span>
              </div>
              <div v-if="b.lines.length > 2" class="text-[10.5px] text-stone-400 ps-1">{{ t("pl.sbMore").replace("{n}", b.lines.length - 2) }}</div>
            </div>
          </div>

          <div v-if="suggest.data.moreBatches" class="rounded-xl bg-stone-50 ring-1 ring-stone-200/70 p-3 text-center text-[12px] text-stone-500">
            {{ t("pl.sbMoreBatches").replace("{b}", suggest.data.moreBatches).replace("{o}", suggest.data.moreOrders) }}
          </div>

          <div v-if="suggest.data.oos.length" class="rounded-xl bg-rose-50 ring-1 ring-rose-200/60 p-3">
            <div class="text-[12px] font-semibold text-rose-700 mb-0.5">{{ t("pl.sbOos") }} · {{ suggest.data.oos.length }}</div>
            <div class="text-[11px] text-rose-600 mb-1.5">{{ t("pl.sbOosHint") }}</div>
            <div class="flex flex-wrap gap-1.5">
              <span v-for="o in suggest.data.oos.slice(0, 12)" :key="o.so"
                    class="font-mono text-[10.5px] text-rose-700 bg-white ring-1 ring-rose-200/70 rounded px-1.5 py-0.5" :title="o.missing.join(', ')">{{ o.so }}</span>
              <span v-if="suggest.data.oos.length > 12" class="text-[10.5px] text-rose-500">{{ t("pl.sbMore").replace("{n}", suggest.data.oos.length - 12) }}</span>
            </div>
          </div>
        </template>
      </div>

      <footer class="flex items-center justify-between gap-2 px-5 py-3.5 border-t border-stone-100 bg-stone-50/60">
        <span v-if="suggest.data" class="text-[11.5px] tabular-nums" :class="overCap ? 'text-rose-600 font-semibold' : 'text-stone-500'">
          {{ pickedOrders }} {{ t("pl.sbOrders") }} · {{ picked.size }}/20<span v-if="overCap"> — {{ t("pl.sbCap") }}</span>
        </span>
        <div class="flex items-center gap-2">
          <button class="inline-flex items-center h-9 px-3 rounded-lg text-[13px] font-medium text-stone-600 hover:bg-stone-100" @click="suggest = null">✕</button>
          <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-40"
                  :disabled="!picked.size || sbCreating || overCap"
                  @click="createSuggested">
            <Icon name="check-circle" :size="15" />
            {{ sbCreating ? t("pl.sbCreating") : t("pl.sbCreate").replace("{n}", picked.size) }}
          </button>
        </div>
      </footer>
    </div>
  </div>

</template>

<script setup>
import { ref, shallowRef, computed } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost, liveOr } from "@/lib/resource";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";

const emit = defineEmits(["created"]);
const { t } = useI18n();
const { success, warn } = useToast();

const zapIcon = (s) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="${s}" height="${s}"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;

const suggest = shallowRef(null);     // null | { loading, data } (shallow: big payload)
const picked = ref(new Set());        // selected batch keys
const pickerFor = ref({});            // batch key -> picker email
const sbPickers = ref([]);
const sbCreating = ref(false);
const capSel = ref(20);

const pickedOrders = computed(() => {
  if (!suggest.value?.data) return 0;
  return suggest.value.data.batches
    .filter((b) => picked.value.has(b.key))
    .reduce((a, b) => a + b.orders.length, 0);
});
// server accepts at most 20 batches / 200 orders per run
const overCap = computed(() => picked.value.size > 20 || pickedOrders.value > 200);
function sbKindLabel(k) {
  return t({ mono: "pl.sbMono", aisle: "pl.sbAisle", zone: "pl.sbZone", mixed: "pl.sbMixed" }[k] || k);
}
function sbKindCls(k) {
  return {
    mono: "text-violet-700 bg-violet-50 ring-violet-200",
    aisle: "text-cyan-700 bg-cyan-50 ring-cyan-200",
    zone: "text-amber-700 bg-amber-50 ring-amber-200",
    mixed: "text-stone-600 bg-stone-100 ring-stone-200",
  }[k] || "text-stone-600 bg-stone-100 ring-stone-200";
}
function selectTop() {
  const sel = new Set();
  let ords = 0;
  for (const b of suggest.value.data.batches) {
    if (sel.size >= 20 || ords + b.orders.length > 200) break;
    sel.add(b.key);
    ords += b.orders.length;
  }
  picked.value = sel;
}
function toggleBatch(key) {
  const s = new Set(picked.value);
  s.has(key) ? s.delete(key) : s.add(key);
  picked.value = s;
}
async function openSuggest() {
  suggest.value = { loading: true, data: null };
  picked.value = new Set();
  pickerFor.value = {};
  const [res, pk] = await Promise.all([
    liveOr(null, () => api("picking.suggest_batches", { cap_orders: capSel.value })),
    liveOr(null, () => api("picking.pickers")),
  ]);
  if (Array.isArray(pk)) sbPickers.value = pk.filter((p) => p.email);
  if (res && Array.isArray(res.batches)) {
    suggest.value = { loading: false, data: res };
    // Pre-select only what one run may create (server caps: 20 batches / 200
    // orders) — the tail stays visible but unchecked.
    selectTop();
    for (const b of res.batches) pickerFor.value[b.key] = "";
  } else {
    suggest.value = null;
    warn("Couldn't load suggestions", "Backend unreachable or engine not deployed yet.");
  }
}
async function createSuggested() {
  const payload = suggest.value.data.batches
    .filter((b) => picked.value.has(b.key))
    .map((b) => ({ orders: b.orders.map((o) => o.so), picker: pickerFor.value[b.key] || null }));
  sbCreating.value = true;
  try {
    const res = await apiPost("picking.create_batches", { batches: payload });
    let msg = t("pl.sbCreated").replace("{n}", res.created);
    if (res.failed) msg += " · " + t("pl.sbFailed").replace("{n}", res.failed);
    success(msg);
    suggest.value = null;
    emit("created", res);
  } catch (e) {
    warn("Couldn't create batches", String(e.message || e));
  } finally {
    sbCreating.value = false;
  }
}

// ── live autopilot card ──────────────────────────────────────────────────
const ap = ref({ enabled: false, runs: [] });
const apBusy = ref(false);
async function apRefresh() {
  const st = await liveOr(null, () => api("picking.autopilot_status"));
  if (st && typeof st.enabled === "boolean") ap.value = { enabled: st.enabled, runs: st.runs || [] };
}
async function apToggle() {
  apBusy.value = true;
  try {
    const res = await apiPost("picking.autopilot_toggle", { enabled: !ap.value.enabled ? 1 : 0 });
    ap.value.enabled = !!res.enabled;
    await apRefresh();
  } catch (e) {
    warn("Autopilot", String(e.message || e));
  } finally {
    apBusy.value = false;
  }
}
async function apRunNow() {
  apBusy.value = true;
  try {
    const res = await apiPost("picking.autopilot_run", {});
    success(t("pl.apCreatedN").replace("{c}", res.created || 0).replace("{o}", res.orders || 0));
    await apRefresh();
    load(true);
  } catch (e) {
    warn("Autopilot", String(e.message || e));
  } finally {
    apBusy.value = false;
  }
}


defineExpose({ open: openSuggest });
</script>
