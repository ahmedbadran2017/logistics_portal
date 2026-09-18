<template>
  <div class="max-w-[1100px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cc.ctlTitle') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cc.ctlIntro') }}</p>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <!-- Where the count came from. "Portal" answers how far the team has
             got with the tool, which is a different question from how much of
             the warehouse is trustworthy. -->
        <div class="flex items-center gap-1.5">
          <button v-for="sc in ['portal', 'all']" :key="sc"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                  :class="source === sc ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]' : 'text-stone-600 bg-white ring-stone-200 hover:ring-stone-300'"
                  @click="setSource(sc)">{{ t('cc.src_' + sc) }}</button>
        </div>
        <div class="flex items-center gap-1.5">
          <button v-for="d in [7, 30, 90]" :key="d"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors tabular-nums"
                  :class="days === d ? 'text-white bg-stone-900 ring-stone-900' : 'text-stone-600 bg-white ring-stone-200 hover:ring-stone-300'"
                  @click="setDays(d)">{{ d }}{{ t('cc.dayShort') }}</button>
        </div>
      </div>
    </header>

    <!-- The campaign comes first: it is the question being asked now. The
         coverage board underneath still answers the wider one — how much of
         the warehouse is trustworthy, whoever counted it. -->
    <CountCampaign />

    <h2 class="text-[13px] font-semibold text-stone-900 pt-1">{{ t('cc.coverage') }}</h2>

    <div v-if="loading" class="space-y-3">
      <div class="h-[132px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        <div v-for="n in 8" :key="n" class="h-[96px] rounded-xl bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
      </div>
    </div>

    <template v-else-if="data">
      <!-- The one number: how much of the stocked warehouse has been walked. -->
      <section class="rounded-2xl bg-stone-900 text-white p-5 md:p-6">
        <div class="flex items-center gap-6 flex-wrap">
          <div class="flex items-end gap-2">
            <span class="text-[46px] leading-none font-bold tabular-nums">{{ h.pct }}</span>
            <span class="text-[20px] font-bold opacity-60 mb-1">%</span>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-semibold">{{ t('cc.heroLabel') }}</div>
            <div class="h-2.5 rounded-full bg-white/15 mt-2 overflow-hidden">
              <div class="h-full rounded-full bg-emerald-400 transition-[width] duration-500"
                   :style="{ width: h.pct + '%' }" />
            </div>
            <div class="text-[11.5px] opacity-70 mt-1.5 tabular-nums">
              {{ h.countedStocked }} / {{ h.stocked }} {{ t('cc.binsWithStock') }} ·
              {{ h.left }} {{ t('cc.left') }} ·
              {{ fmt(h.unitsCounted) }} / {{ fmt(h.units) }} {{ t('recv.units') }}
            </div>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <router-link v-if="h.pending" :to="{ name: 'CycleCount' }"
                         class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12px] font-bold text-amber-900 bg-amber-300 hover:bg-amber-200">
              <Icon name="clock" :size="13" />{{ h.pending }} {{ t('cc.pending') }}
            </router-link>
            <span class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12px] font-semibold bg-white/10 tabular-nums">
              {{ h.pctAll }}% {{ t('cc.ofAllBins') }}
            </span>
          </div>
        </div>
        <!-- Honesty line: a clean count used to leave no trace, so anything
             counted before the witness shipped can only be seen through the
             reconciliation it happened to produce. -->
        <p class="text-[11px] opacity-55 mt-3 leading-relaxed">
          <Icon name="info" :size="11" class="inline -mt-px" />
          {{ t('cc.srcSplit').replace('{s}', String(h.bySession || 0))
               .replace('{p}', String(h.byPortal || 0)).replace('{d}', String(h.byDesk || 0)) }}
          <template v-if="!h.bySession"> {{ t('cc.floorNote') }}</template>
        </p>
      </section>

      <!-- Zones — where the campaign stands, aisle by aisle -->
      <section>
        <h2 class="text-[13px] font-semibold text-stone-900 mb-2">{{ t('cc.zones') }}</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-2.5">
          <div v-for="z in liveZones" :key="z.zone"
               class="rounded-xl bg-white ring-1 p-3"
               :class="z.pct >= 100 ? 'ring-emerald-300' : 'ring-stone-200/70'">
            <div class="flex items-baseline gap-2">
              <span class="text-[14px] font-bold text-stone-900 truncate">{{ z.zone }}</span>
              <span class="ms-auto text-[15px] font-bold tabular-nums" :class="barText(z.pct)">{{ z.pct }}%</span>
            </div>
            <div class="h-1.5 rounded-full bg-stone-100 mt-2 overflow-hidden">
              <div class="h-full rounded-full transition-[width] duration-500"
                   :class="barBg(z.pct)" :style="{ width: z.pct + '%' }" />
            </div>
            <div class="text-[11px] text-stone-500 mt-1.5 tabular-nums">
              {{ z.countedStocked }}/{{ z.stocked }} {{ t('cc.bins') }} · {{ fmt(z.units) }} {{ t('recv.units') }}
            </div>
            <div v-if="z.lastBy" class="text-[10.5px] text-stone-400 mt-0.5 truncate">
              {{ local(z.lastAt).slice(5, 10) }} · {{ z.lastBy.split('@')[0] }}
            </div>
            <div v-else class="text-[10.5px] text-stone-300 mt-0.5">{{ t('cc.never') }}</div>
          </div>
        </div>
        <p v-if="emptyZones.length" class="text-[11px] text-stone-400 mt-2">
          {{ t('cc.emptyZones').replace('{n}', String(emptyZones.length)) }}: {{ emptyZones.map(z => z.zone).join(', ') }}
        </p>
      </section>

      <div class="grid md:grid-cols-2 gap-4">
        <!-- Who is counting -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cc.people') }}</span>
            <span class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ data.people.length }}</span>
          </div>
          <div v-if="!data.people.length" class="px-4 py-6 text-center text-[12px] text-stone-400">{{ t('cc.noPeople') }}</div>
          <div v-else class="divide-y divide-stone-50 max-h-[380px] overflow-y-auto">
            <div v-for="p in data.people" :key="p.user" class="px-4 py-2.5 flex items-center gap-3">
              <span class="w-7 h-7 rounded-lg bg-stone-100 text-stone-600 flex items-center justify-center text-[10.5px] font-bold flex-shrink-0">
                {{ initials(p.name) }}
              </span>
              <div class="min-w-0 flex-1">
                <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ p.name }}</div>
                <div class="text-[10.5px] text-stone-400 tabular-nums">
                  {{ local(p.last).slice(5, 16) }}
                  <span v-if="p.src === 'reco'" class="ms-1 text-amber-600">· {{ t('cc.viaDesk') }}</span>
                </div>
              </div>
              <div class="text-end flex-shrink-0">
                <div class="text-[13px] font-bold text-stone-900 tabular-nums">{{ p.binCount }}</div>
                <div class="text-[10px] text-stone-400">{{ t('cc.bins') }}</div>
              </div>
              <div class="text-end flex-shrink-0 w-[52px]">
                <div class="text-[13px] font-bold text-violet-700 tabular-nums">{{ p.lines }}</div>
                <div class="text-[10px] text-stone-400">{{ t('cc.lines') }}</div>
              </div>
            </div>
          </div>
        </section>

        <!-- What is still untouched — the worklist, biggest first -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cc.notCounted') }}</span>
            <span class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ data.uncountedTotal }}</span>
          </div>
          <div v-if="!data.uncounted.length" class="px-4 py-6 text-center text-[12px] text-emerald-700">{{ t('cc.allDone') }}</div>
          <div v-else class="divide-y divide-stone-50 max-h-[380px] overflow-y-auto">
            <button v-for="u in data.uncounted" :key="u.warehouse"
                    class="w-full text-start px-4 py-2 flex items-center gap-3 hover:bg-stone-50 transition-colors"
                    @click="$router.push({ name: 'CycleCount', query: { bin: u.warehouse } })">
              <span class="font-mono text-[12px] font-semibold text-stone-800 w-[70px] flex-shrink-0">{{ u.bin }}</span>
              <span class="text-[11px] text-stone-400 tabular-nums flex-1">{{ u.lines }} {{ t('cc.lines') }}</span>
              <span class="text-[12.5px] font-bold text-stone-700 tabular-nums">{{ fmt(u.units) }}</span>
              <Icon name="chevron-right" :size="13" class="text-stone-300 flex-shrink-0" />
            </button>
          </div>
        </section>
      </div>

      <!-- Ghost twins: found units this campaign already posted as gains
           whose book twin still sits in a closed warehouse or a parking
           zone. The rule that pulls instead of posting runs at every count
           from now on; this panel is the retroactive half. -->
      <section class="bg-white rounded-xl ring-1 overflow-hidden" :class="ghost && ghost.units ? 'ring-amber-200/70' : 'ring-stone-200/70'">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <span class="text-[12px] font-semibold text-stone-900">{{ t('cc.ghostTitle') }}</span>
          <span v-if="ghost" class="text-[11px] tabular-nums font-bold" :class="ghost.units ? 'text-amber-700' : 'text-stone-400'">{{ fmt(ghost.units) }} {{ t('recv.units') }}</span>
          <label class="ms-auto inline-flex items-center gap-1.5 text-[11.5px] text-stone-600 cursor-pointer">
            <input type="checkbox" v-model="ghostShelves" class="accent-[var(--accent-600)]" @change="loadGhost" />
            {{ t('cc.ghostShelves') }}
          </label>
          <button class="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-[11.5px] font-semibold ring-1 transition-colors"
                  :class="pullOn ? 'text-emerald-700 bg-emerald-50 ring-emerald-200' : 'text-stone-600 bg-white ring-stone-200'"
                  :disabled="pullBusy" @click="togglePull">
            <Icon :name="pullOn ? 'check-circle' : 'circle'" :size="12" />{{ pullOn ? t('cc.pullOn') : t('cc.pullOff') }}
          </button>
        </div>
        <p class="px-4 py-2 text-[11.5px] text-stone-500 border-b border-stone-50">{{ t('cc.ghostHint') }}</p>
        <div v-if="ghostLoading" class="p-3 space-y-2">
          <div v-for="n in 3" :key="n" class="h-[34px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
        </div>
        <div v-else-if="!ghost || !ghost.rows.length" class="px-4 py-6 text-center text-[12px] text-emerald-700">{{ t('cc.ghostNone') }}</div>
        <template v-else>
          <div class="px-4 py-2 flex flex-wrap gap-1.5 border-b border-stone-50">
            <span v-for="s in ghost.sources" :key="s.source"
                  class="inline-flex items-center gap-1 text-[11px] rounded-md px-1.5 py-0.5 ring-1 tabular-nums"
                  :class="s.tier === 1 ? 'text-rose-700 bg-rose-50 ring-rose-200/70' : s.tier === 2 ? 'text-amber-700 bg-amber-50 ring-amber-200/70' : 'text-stone-600 bg-stone-50 ring-stone-200'">
              <span class="font-semibold">{{ s.source.replace(' - JM', '') }}</span> · {{ s.units }}u · {{ s.lines }} {{ t('cc.lines') }}
            </span>
          </div>
          <div class="max-h-[320px] overflow-y-auto divide-y divide-stone-50">
            <div v-for="(r, i) in ghost.rows" :key="r.source + r.itemCode + i" class="px-4 py-1.5 flex items-center gap-3 text-[11.5px]">
              <span class="font-mono font-semibold text-stone-800 w-[120px] truncate flex-shrink-0">{{ r.source.replace(' - JM', '') }}</span>
              <span class="font-mono text-stone-700 flex-1 truncate" :title="r.name">{{ r.sku || r.itemCode }}</span>
              <span class="text-stone-400 tabular-nums flex-shrink-0">{{ t('cc.ghostFoundOn') }} <span class="font-mono text-stone-600">{{ r.shelf.replace(' - JM', '') }}</span></span>
              <span class="font-bold text-stone-800 tabular-nums w-[52px] text-end flex-shrink-0">−{{ r.clear }} / {{ r.book }}</span>
            </div>
          </div>
          <div class="px-4 py-2.5 border-t border-stone-100 flex items-center gap-3 flex-wrap">
            <span class="text-[11.5px] text-stone-500 tabular-nums">{{ ghost.rows.length }} {{ t('cc.lines') }} · {{ fmt(ghost.units) }} {{ t('recv.units') }} · {{ fmt(ghost.value) }} MAD</span>
            <button class="ms-auto h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white transition-colors disabled:opacity-50"
                    :class="ghostArmed ? 'bg-rose-600 hover:bg-rose-700' : 'bg-stone-900 hover:bg-stone-800'"
                    :disabled="ghostBusy" @click="clearGhosts">
              {{ ghostBusy ? t('cc.ghostBusy') : ghostArmed ? t('cc.ghostSure') : t('cc.ghostClear').replace('{n}', fmt(ghost.units)) }}
            </button>
          </div>
        </template>
      </section>

      <!-- Double counts: units a posted count added on top of its own pull.
           The source is fixed at the count; this clears what already landed. -->
      <section v-if="dbl === null || dbl.total" class="bg-white rounded-xl ring-1 overflow-hidden"
               :class="dbl && dbl.units ? 'ring-rose-200/70' : 'ring-stone-200/70'">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <span class="text-[12px] font-semibold text-stone-900">{{ t('cc.dblTitle') }}</span>
          <span v-if="dbl" class="text-[11px] tabular-nums font-bold" :class="dbl.units ? 'text-rose-700' : 'text-stone-400'">{{ fmt(dbl.units) }} {{ t('recv.units') }}</span>
        </div>
        <p class="px-4 py-2 text-[11.5px] text-stone-500 border-b border-stone-50">{{ t('cc.dblHint') }}</p>
        <div v-if="dblLoading" class="p-3 space-y-2">
          <div v-for="n in 3" :key="n" class="h-[34px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
        </div>
        <template v-else-if="dbl && dbl.rows.length">
          <div class="max-h-[320px] overflow-y-auto divide-y divide-stone-50">
            <div v-for="(r, i) in dbl.rows" :key="r.reco + r.itemCode + i" class="px-4 py-1.5 flex items-center gap-3 text-[11.5px]">
              <span class="font-mono font-semibold text-stone-800 w-[76px] truncate flex-shrink-0">{{ r.warehouse.replace(' - JM', '') }}</span>
              <span class="font-mono text-stone-700 flex-1 truncate" :title="r.name">{{ r.sku || r.itemCode }}</span>
              <span class="text-stone-400 tabular-nums flex-shrink-0">{{ t('cc.dblCounted') }} {{ r.counted }} · {{ t('cc.dblBook') }} {{ r.bookNow }}</span>
              <span class="font-bold tabular-nums w-[64px] text-end flex-shrink-0"
                    :class="r.target === null ? 'text-amber-700' : 'text-rose-700'">
                {{ r.target === null ? t('cc.dblWalk') : '−' + r.phantom + ' → ' + r.target }}
              </span>
            </div>
          </div>
          <div class="px-4 py-2.5 border-t border-stone-100 flex items-center gap-3 flex-wrap">
            <span class="text-[11.5px] text-stone-500 tabular-nums">{{ dbl.total }} {{ t('cc.lines') }} · {{ fmt(dbl.units) }} {{ t('recv.units') }} · {{ fmt(dbl.value) }} MAD</span>
            <button v-if="dbl.fixable" class="ms-auto h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white transition-colors disabled:opacity-50"
                    :class="dblArmed ? 'bg-rose-600 hover:bg-rose-700' : 'bg-stone-900 hover:bg-stone-800'"
                    :disabled="dblBusy" @click="fixDouble">
              {{ dblBusy ? t('cc.ghostBusy') : dblArmed ? t('cc.ghostSure') : t('cc.dblFix').replace('{n}', fmt(dbl.fixableUnits)) }}
            </button>
          </div>
        </template>
        <div v-else class="px-4 py-6 text-center text-[12px] text-emerald-700">{{ t('cc.dblNone') }}</div>
      </section>

      <!-- Daily rhythm: only real once sessions exist, so it hides until then -->
      <section v-if="data.daily.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="text-[12px] font-semibold text-stone-900 mb-2.5">{{ t('cc.daily') }}</div>
        <div class="flex items-end gap-1 h-[64px]">
          <div v-for="d in data.daily" :key="d.day" class="flex-1 min-w-[4px] rounded-t bg-[var(--accent-500)] hover:bg-[var(--accent-600)] transition-colors"
               :style="{ height: Math.max(4, (d.bins / dailyMax) * 64) + 'px' }"
               :title="d.day + ' · ' + d.bins + ' ' + t('cc.bins')" />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { local } from "@/lib/clock";
import CountCampaign from "@/components/CountCampaign.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { warn, success } = useToast();

// ── Ghost twins (retroactive pull) ───────────────────────────────────────
const ghost = ref(null);
const ghostLoading = ref(true);
const ghostShelves = ref(false);
const ghostArmed = ref(false);
const ghostBusy = ref(false);
const pullOn = ref(true);
const pullBusy = ref(false);
let disarm = null;
async function loadGhost() {
  ghostLoading.value = true;
  try {
    ghost.value = await api("cycle_count.ghost_twins", { shelves: ghostShelves.value ? 1 : 0 });
    if (ghost.value && ghost.value.pullEnabled != null) pullOn.value = !!ghost.value.pullEnabled;
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    ghostLoading.value = false;
  }
}
async function togglePull() {
  pullBusy.value = true;
  try {
    const res = await apiPost("cycle_count.set_pull", { on: pullOn.value ? 0 : 1 });
    pullOn.value = !!res.on;
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    pullBusy.value = false;
  }
}
async function clearGhosts() {
  if (!ghostArmed.value) {
    ghostArmed.value = true;
    clearTimeout(disarm);
    disarm = setTimeout(() => (ghostArmed.value = false), 5000);
    return;
  }
  ghostArmed.value = false;
  ghostBusy.value = true;
  try {
    const res = await apiPost("cycle_count.clear_ghosts", { shelves: ghostShelves.value ? 1 : 0 });
    success(t("cc.ghostDone").replace("{n}", fmt(res.units)).replace("{r}", (res.recos || []).length),
            (res.recos || []).map((r) => `${r.source.replace(" - JM", "")} · ${r.name}`).join(" · "));
    if (res.failed && res.failed.length) {
      warn(t("cc.ghostFail"), res.failed.map((f) => `${f.source}: ${f.reason}`).join(" · "));
    }
    await Promise.all([loadGhost(), load()]);
  } catch (e) {
    warn(t("cc.ghostFail"), String(e.message || e));
  } finally {
    ghostBusy.value = false;
  }
}

// ── Double counts (a count that posted on top of its own pull) ───────────
const dbl = ref(null);
const dblLoading = ref(true);
const dblArmed = ref(false);
const dblBusy = ref(false);
let dblDisarm = null;
async function loadDbl() {
  dblLoading.value = true;
  try {
    dbl.value = await api("cycle_count.double_counts", { days: 30 });
  } catch (_) {
    dbl.value = { rows: [], total: 0, units: 0, value: 0, fixable: 0, fixableUnits: 0 };
  } finally {
    dblLoading.value = false;
  }
}
async function fixDouble() {
  if (!dblArmed.value) {
    dblArmed.value = true;
    clearTimeout(dblDisarm);
    dblDisarm = setTimeout(() => (dblArmed.value = false), 5000);
    return;
  }
  dblArmed.value = false;
  dblBusy.value = true;
  try {
    const res = await apiPost("cycle_count.fix_double_counts", { days: 30 });
    success(t("cc.dblDone").replace("{n}", fmt(res.units)).replace("{r}", (res.recos || []).length),
            (res.recos || []).map((r) => `${r.shelf.replace(" - JM", "")} · ${r.name}`).join(" · "));
    if (res.failed && res.failed.length) {
      warn(t("cc.ghostFail"), res.failed.map((f) => `${f.shelf}: ${f.reason}`).join(" · "));
    }
    await Promise.all([loadDbl(), load()]);
  } catch (e) {
    warn(t("cc.ghostFail"), String(e.message || e));
  } finally {
    dblBusy.value = false;
  }
}

const data = ref(null);
const loading = ref(true);
const days = ref(30);
// Portal by default: the Desk is closed to the floor team, so its counts are
// a diagnostic, not the picture anyone is asking for.
const source = ref("portal");

const h = computed(() => data.value?.headline || {});
// A zone with nothing on its shelves has no counting work in it; listing the
// reserve racking (270 empty bins) alongside the live aisles would bury them.
const liveZones = computed(() => (data.value?.zones || []).filter((z) => z.stocked > 0));
const emptyZones = computed(() => (data.value?.zones || []).filter((z) => !z.stocked));
const dailyMax = computed(() => Math.max(1, ...(data.value?.daily || []).map((d) => d.bins)));

function barBg(p) {
  if (p >= 100) return "bg-emerald-500";
  if (p >= 60) return "bg-emerald-400";
  if (p >= 25) return "bg-amber-400";
  return "bg-rose-400";
}
function barText(p) {
  if (p >= 60) return "text-emerald-600";
  if (p >= 25) return "text-amber-600";
  return "text-rose-600";
}
function initials(n) {
  return String(n || "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0] || "").join("").toUpperCase();
}
function fmt(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }

async function load() {
  loading.value = true;
  try {
    data.value = await api("cycle_count.progress",
                          { days: days.value, source: source.value });
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
function setDays(d) { days.value = d; load(); }
function setSource(sc) { source.value = sc; load(); }
onMounted(() => { load(); loadGhost(); loadDbl(); });
</script>
