<template>
  <div class="max-w-[1200px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cmx.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[640px]">{{ t('cmx.intro') }}</p>
      </div>
      <div class="flex items-center gap-1.5">
        <button v-for="b in ['overall', 'confirm', 'deliver']" :key="b"
                class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                :class="basis === b ? 'text-white bg-stone-900 ring-stone-900' : 'text-stone-600 bg-white ring-stone-200 hover:ring-stone-300'"
                @click="setBasis(b)">{{ t('cmx.b_' + b) }}</button>
      </div>
    </header>

    <div v-if="loading" class="h-[420px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />

    <template v-else-if="d && d.cities.length">
      <!-- The two rates that must be read together, for the whole network. -->
      <section class="flex items-center gap-3 flex-wrap">
        <div v-for="k in headline" :key="k.label"
             class="rounded-xl bg-white ring-1 ring-stone-200/70 px-4 py-2.5">
          <div class="text-[19px] font-extrabold tabular-nums" :class="k.cls">{{ k.value }}</div>
          <div class="text-[10px] uppercase font-semibold text-stone-400 mt-0.5">{{ k.label }}</div>
        </div>
        <p class="text-[11px] text-stone-400 max-w-[380px] leading-relaxed">{{ t('cmx.resolvedNote') }}</p>
      </section>

      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-x-auto">
        <div class="p-3 min-w-[880px]">
          <!-- header: weeks -->
          <div class="grid items-center gap-1 mb-1" :style="cols">
            <div />
            <div v-for="w in d.weeks" :key="w" class="text-center text-[10.5px] text-stone-400 tabular-nums">
              {{ wkLabel(w) }}
            </div>
            <div class="text-center text-[10px] uppercase font-semibold text-stone-400">{{ t('cmx.avg') }}</div>
          </div>

          <div v-for="c in d.cities" :key="c.city" class="grid items-center gap-1 mb-1" :style="cols">
            <button class="text-start flex items-center gap-2 pe-2 min-w-0" @click="open(c.city)">
              <Icon name="map-pin" :size="12" class="text-stone-400 flex-shrink-0" />
              <span class="text-[12.5px] font-semibold text-stone-900 truncate">{{ c.city }}</span>
              <span class="text-[10px] text-stone-400 tabular-nums flex-shrink-0">{{ c.orders }}</span>
            </button>
            <button v-for="(cell, i) in c.cells" :key="i"
                    class="h-9 rounded-md grid place-items-center relative"
                    :class="cell.covered ? '' : 'bg-stone-100'"
                    :style="cell.covered ? { background: heat(cell.score), opacity: cell.conf === 'low' ? 0.45 : 1 } : {}"
                    :title="cell.covered ? `${cell.n} · ${cell.conf === 'low' ? t('cmx.lowConf') : t('cmx.highConf')}` : t('cmx.noData')"
                    @click="cell.covered && open(c.city)">
              <span v-if="cell.covered" class="text-[12px] font-bold tabular-nums text-stone-900">{{ Math.round(cell.score) }}</span>
              <Icon v-else name="minus" :size="11" class="text-stone-300" />
              <span v-if="cell.covered && cell.conf === 'low'"
                    class="absolute bottom-1 end-1 w-[5px] h-[5px] rounded-full border-[1.5px] border-stone-900/70" />
            </button>
            <div class="h-9 rounded-md grid place-items-center bg-stone-50 text-[12.5px] font-bold tabular-nums"
                 :class="bandText(c.score)">{{ Math.round(c.score) }}</div>
          </div>

          <div class="flex items-center gap-4 mt-3 px-1 text-[10.5px] text-stone-400 flex-wrap">
            <span class="flex items-center gap-1.5">
              <span v-for="s in [60, 70, 80, 90]" :key="s" class="w-[18px] h-2 rounded-sm" :style="{ background: heat(s) }" />
              60 → 90
            </span>
            <span class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full border-[1.5px] border-stone-400" />{{ t('cmx.legendLow') }}
            </span>
            <span class="flex items-center gap-1.5">
              <span class="w-3 h-2 rounded-sm bg-stone-100 ring-1 ring-stone-200" />{{ t('cmx.noData') }}
            </span>
          </div>
        </div>
      </section>
    </template>

    <div v-else class="rounded-2xl bg-white ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="map-pin" :size="24" class="mx-auto text-stone-300" />
      <div class="text-[14px] font-semibold text-stone-700 mt-2">{{ t('cmx.empty') }}</div>
    </div>

    <!-- One city's funnel and the reasons behind its two rates -->
    <div v-if="card" class="fixed inset-0 z-[160] flex justify-end" role="dialog" aria-modal="true">
      <div class="absolute inset-0 bg-stone-900/30 backdrop-blur-[1px]" @click="card = null" />
      <div class="relative w-full max-w-[460px] bg-white h-full overflow-y-auto shadow-2xl">
        <header class="sticky top-0 bg-white border-b border-stone-100 px-5 py-3.5 flex items-center gap-2.5">
          <span class="w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] grid place-items-center">
            <Icon name="map-pin" :size="16" />
          </span>
          <div class="min-w-0">
            <div class="text-[14.5px] font-bold text-stone-900 truncate">{{ card.city }}</div>
            <div class="text-[11.5px] text-stone-400">{{ t('cmx.cardSub').replace('{w}', String(card.weeks)) }}</div>
          </div>
          <button class="ms-auto text-stone-400 hover:text-stone-700" @click="card = null"><Icon name="x" :size="18" /></button>
        </header>
        <div class="p-5 space-y-4">
          <div class="grid grid-cols-2 gap-2">
            <div class="rounded-xl ring-1 ring-stone-200/70 p-3">
              <div class="text-[9.5px] uppercase font-semibold text-stone-400 tracking-wide">{{ t('cmx.b_confirm') }}</div>
              <div class="text-[22px] font-extrabold tabular-nums" :class="bandText(card.confirmPct)">{{ card.confirmPct ?? '—' }}%</div>
            </div>
            <div class="rounded-xl ring-1 ring-stone-200/70 p-3">
              <div class="text-[9.5px] uppercase font-semibold text-stone-400 tracking-wide">{{ t('cmx.b_deliver') }}</div>
              <div class="text-[22px] font-extrabold tabular-nums" :class="bandText(card.deliveredPct)">{{ card.deliveredPct ?? '—' }}%</div>
            </div>
          </div>

          <div class="rounded-xl ring-1 ring-stone-200/70 divide-y divide-stone-50">
            <div v-for="f in funnel" :key="f.label" class="px-3.5 py-2 flex items-center gap-3 text-[12px]">
              <span class="text-stone-600 flex-1">{{ f.label }}</span>
              <span class="font-bold tabular-nums text-stone-900">{{ f.n }}</span>
            </div>
          </div>

          <!-- What the money did, which is the reason any of this matters -->
          <div class="rounded-xl ring-1 ring-rose-200 bg-rose-50/50 px-3.5 py-3">
            <div class="text-[9.5px] uppercase font-semibold text-rose-700 tracking-wide">{{ t('cmx.lostValue') }}</div>
            <div class="text-[20px] font-extrabold tabular-nums text-rose-700">{{ fmt(card.lostValue) }} MAD</div>
            <div class="text-[11px] text-rose-600/80 mt-0.5">{{ t('cmx.lostHint') }}</div>
          </div>

          <div v-for="grp in [{ k: 'cancelReasons', t: t('cmx.whyCancel') }, { k: 'failReasons', t: t('cmx.whyFail') }]"
               :key="grp.k">
            <div v-if="card[grp.k].length">
              <div class="text-[11.5px] font-semibold text-stone-700 mb-1.5">{{ grp.t }}</div>
              <div class="space-y-1">
                <div v-for="r in card[grp.k]" :key="r.label" class="flex items-center gap-2 text-[11.5px]">
                  <span class="text-stone-600 truncate flex-1" dir="auto">{{ r.label }}</span>
                  <span class="tabular-nums font-semibold text-stone-800">{{ r.n }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const d = ref(null);
const card = ref(null);
const loading = ref(true);
const basis = ref("overall");

const cols = computed(() => ({
  gridTemplateColumns: `150px repeat(${(d.value?.weeks || []).length}, minmax(0,1fr)) 56px`,
}));

// Continuous rose → amber → emerald, in the portal's own palette rather than
// the reference's lime: a score reads as a colour before it reads as a number,
// and it must mean the same red and green as every other screen here.
const STOPS = [[58, [225, 29, 72]], [76, [245, 158, 11]], [90, [16, 185, 129]]];
function heat(s) {
  const v = Math.max(STOPS[0][0], Math.min(STOPS[2][0], Number(s) || 0));
  let a = STOPS[0], b = STOPS[STOPS.length - 1];
  for (let i = 0; i < STOPS.length - 1; i++) {
    if (v >= STOPS[i][0] && v <= STOPS[i + 1][0]) { a = STOPS[i]; b = STOPS[i + 1]; break; }
  }
  const k = b[0] === a[0] ? 0 : (v - a[0]) / (b[0] - a[0]);
  const c = a[1].map((x, i) => Math.round(x + (b[1][i] - x) * k));
  return `rgba(${c[0]},${c[1]},${c[2]},0.55)`;
}
function bandText(s) {
  if (s == null) return "text-stone-400";
  return s >= 80 ? "text-emerald-600" : s >= 70 ? "text-amber-600" : "text-rose-600";
}
function wkLabel(w) {
  const s = String(w);
  return "W" + s.slice(4);
}
function fmt(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }

const headline = computed(() => {
  const x = d.value;
  if (!x) return [];
  return [
    { label: t("cmx.netScore"), value: x.netScore, cls: bandText(x.netScore) },
    { label: t("cmx.b_confirm"), value: (x.netConfirm ?? "—") + "%", cls: bandText(x.netConfirm) },
    { label: t("cmx.b_deliver"), value: (x.netDeliver ?? "—") + "%", cls: bandText(x.netDeliver) },
  ];
});
const funnel = computed(() => {
  const f = card.value?.funnel;
  if (!f) return [];
  return [
    { label: t("cmx.fOrders"), n: f.orders },
    { label: t("cmx.fConfirmed"), n: f.confirmed },
    { label: t("cmx.fCancelled"), n: f.cancelled },
    { label: t("cmx.fShipped"), n: f.shipped },
    { label: t("cmx.fDelivered"), n: f.delivered },
    { label: t("cmx.fFailed"), n: f.failed },
  ];
});

async function load() {
  loading.value = true;
  try { d.value = await api("city.matrix", { basis: basis.value, weeks: 8 }); }
  catch { d.value = null; }
  loading.value = false;
}
function setBasis(b) { basis.value = b; load(); }
async function open(city) {
  try { card.value = await api("city.city_card", { city, weeks: 8 }); }
  catch { card.value = null; }
}
onMounted(load);
</script>
