<template>
  <div class="max-w-[1200px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('oclk.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('oclk.intro') }}</p>
      </div>
      <div class="flex items-center gap-2 text-[11.5px] text-stone-400 tabular-nums">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />{{ d?.now }}
      </div>
    </header>

    <!-- The four numbers the team lives by. Each is a filter, not a decoration. -->
    <section v-if="d" class="grid grid-cols-2 md:grid-cols-4 gap-2.5">
      <button v-for="k in kpis" :key="k.view"
              class="rounded-xl bg-white ring-1 p-3.5 text-start transition-shadow hover:shadow-sm"
              :class="view === k.view ? 'ring-stone-900' : 'ring-stone-200/70'"
              @click="setView(k.view)">
        <div class="text-[24px] font-extrabold tabular-nums leading-none" :class="k.cls">{{ k.n }}</div>
        <div class="text-[11px] font-semibold text-stone-600 mt-1">{{ k.label }}</div>
        <div class="text-[10.5px] text-stone-400">{{ k.sub }}</div>
      </button>
    </section>

    <!-- Today's waves: what each van has to carry, and what will miss it. -->
    <section v-if="waves && waves.waves.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
        <Icon name="truck" :size="14" class="text-stone-400" />
        <span class="text-[12px] font-semibold text-stone-900">{{ t('oclk.waves') }}</span>
        <span class="text-[11px] text-stone-400">{{ t('oclk.wavesHint') }}</span>
      </div>
      <div class="divide-y divide-stone-50 max-h-[230px] overflow-y-auto">
        <div v-for="w in waves.waves" :key="w.dueAt" class="px-4 py-2.5 flex items-center gap-3 text-[12px]">
          <span class="font-semibold tabular-nums w-[110px] flex-shrink-0"
                :class="w.late ? 'text-rose-600' : 'text-stone-800'">{{ w.dueAt.slice(5) }}</span>
          <span class="flex-1 h-2 rounded-full bg-stone-100 overflow-hidden flex">
            <span class="block h-full bg-rose-400" :style="{ width: pctOf(w.late, w.n) }" />
            <span class="block h-full bg-emerald-400" :style="{ width: pctOf(w.n - w.late, w.n) }" />
          </span>
          <span class="tabular-nums text-stone-500 w-[54px] text-end">{{ w.toPick }} {{ t('oclk.noPl') }}</span>
          <span class="tabular-nums font-bold text-stone-900 w-[40px] text-end">{{ w.n }}</span>
          <span class="tabular-nums font-bold w-[46px] text-end" :class="w.late ? 'text-rose-600' : 'text-stone-300'">
            {{ w.late ? '−' + w.late : '✓' }}
          </span>
        </div>
      </div>
    </section>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 6" :key="n" class="h-[52px] rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <section v-else-if="d && d.rows.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
        <span class="text-[12px] font-semibold text-stone-900">{{ t('oclk.v_' + view) }}</span>
        <span class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ d.total }}</span>
      </div>
      <div class="divide-y divide-stone-50 max-h-[560px] overflow-y-auto">
        <RouterLink v-for="r in d.rows" :key="r.order"
                    :to="{ name: 'OrderDetail', params: { name: r.order } }"
                    class="px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50 transition-colors">
          <span class="w-1 h-8 rounded-full flex-shrink-0" :class="r.late ? 'bg-rose-500' : 'bg-stone-200'" />
          <div class="min-w-0 w-[168px] flex-shrink-0">
            <div class="font-mono text-[12px] font-semibold text-stone-900 truncate">{{ r.order }}</div>
            <div class="text-[10.5px] text-stone-400 truncate" dir="auto">{{ r.customer }}</div>
          </div>
          <span class="text-[10px] font-bold rounded-full px-2 py-0.5 flex-shrink-0" :class="STAGE_CLS[r.stage]">
            {{ t('oclk.s_' + r.stage) }}
          </span>
          <span class="text-[11px] text-stone-400 truncate flex-1 hidden sm:block" dir="auto">{{ r.city }}</span>
          <span class="text-[11px] text-stone-400 tabular-nums w-[96px] text-end hidden md:block">{{ r.dueAt.slice(5) }}</span>
          <span class="text-[12px] font-bold tabular-nums w-[86px] text-end flex-shrink-0"
                :class="r.late ? 'text-rose-600' : 'text-emerald-600'">{{ remain(r) }}</span>
        </RouterLink>
      </div>
    </section>

    <div v-else-if="d" class="rounded-2xl bg-white ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="check-circle" :size="24" class="mx-auto text-emerald-400" />
      <div class="text-[14px] font-semibold text-stone-700 mt-2">{{ t('oclk.clear') }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const d = ref(null);
const waves = ref(null);
const loading = ref(true);
const view = ref("late");

const STAGE_CLS = {
  to_pick: "text-rose-700 bg-rose-50 ring-1 ring-rose-200",
  picking: "text-amber-700 bg-amber-50 ring-1 ring-amber-200",
  to_hand_over: "text-violet-700 bg-violet-50 ring-1 ring-violet-200",
  with_carrier: "text-sky-700 bg-sky-50 ring-1 ring-sky-200",
};

const kpis = computed(() => {
  const c = d.value?.counts;
  if (!c) return [];
  return [
    { view: "late", n: c.lateInHouse, label: t("oclk.kLate"), sub: t("oclk.kLateSub"),
      cls: c.lateInHouse ? "text-rose-600" : "text-emerald-600" },
    { view: "wave", n: c.toPick, label: t("oclk.kToPick"), sub: t("oclk.kToPickSub"),
      cls: c.toPick ? "text-amber-600" : "text-emerald-600" },
    { view: "carrier", n: c.lateCarrier, label: t("oclk.kCarrier"), sub: t("oclk.kCarrierSub"),
      cls: c.lateCarrier ? "text-rose-600" : "text-emerald-600" },
    { view: "live", n: c.live, label: t("oclk.kLive"), sub: t("oclk.kLiveSub"), cls: "text-stone-900" },
  ];
});

function pctOf(part, total) { return total ? (100 * part / total) + "%" : "0%"; }
// Hours are what a person can act on; a due timestamp alone makes them do the
// arithmetic while the van is loading.
function remain(r) {
  const m = Math.abs(r.lateMin || 0);
  const h = Math.floor(m / 60);
  const txt = h >= 48 ? Math.floor(h / 24) + t("oclk.dShort") : h + t("oclk.hShort");
  return (r.late ? "+" : "−") + txt;
}

async function load() {
  loading.value = true;
  try {
    const [b, w] = await Promise.all([
      api("shipments.board", { view: view.value }),
      api("shipments.wave_board"),
    ]);
    d.value = b; waves.value = w;
  } catch { d.value = null; }
  loading.value = false;
}
function setView(v) { view.value = v; load(); }
onMounted(load);
// A tracking board that needs refreshing by hand is a board nobody trusts.
const tick = setInterval(() => {
  if (document.visibilityState === "visible") load();
}, 120000);
onUnmounted(() => clearInterval(tick));
</script>
