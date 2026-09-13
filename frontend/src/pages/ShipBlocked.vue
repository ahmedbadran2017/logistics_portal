<template>
  <div class="max-w-[1200px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('oclk.blkTitle') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[720px]">{{ t('oclk.blkIntro') }}</p>
      </div>
      <div v-if="d" class="text-[11.5px] text-stone-400 tabular-nums">
        {{ d.total }} / {{ d.inHouse }} {{ t('oclk.blkOf') }}
      </div>
    </header>

    <!-- One card per cause. Each is a filter, and each names its own repair. -->
    <section v-if="d" class="grid grid-cols-2 md:grid-cols-5 gap-2.5">
      <button v-for="k in causes" :key="k.key"
              class="rounded-xl bg-white ring-1 p-3.5 text-start transition-shadow hover:shadow-sm"
              :class="why === k.key ? 'ring-stone-900' : 'ring-stone-200/70'"
              @click="why = why === k.key ? '' : k.key">
        <div class="text-[24px] font-extrabold tabular-nums leading-none"
             :class="k.n ? k.cls : 'text-emerald-600'">{{ k.n }}</div>
        <div class="text-[11px] font-semibold text-stone-600 mt-1">{{ t('oclk.w_' + k.key) }}</div>
        <div class="text-[10.5px] text-stone-400">{{ t('oclk.wh_' + k.key) }}</div>
      </button>
    </section>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 6" :key="n" class="h-[52px] rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <section v-else-if="rows.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
        <span class="text-[12px] font-semibold text-stone-900">{{ why ? t('oclk.w_' + why) : t('oclk.blkAll') }}</span>
        <span class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ rows.length }}</span>
      </div>
      <div class="divide-y divide-stone-50 max-h-[620px] overflow-y-auto">
        <div v-for="r in rows" :key="r.order" class="px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50 transition-colors">
          <span class="w-1 h-8 rounded-full flex-shrink-0" :class="r.late ? 'bg-rose-500' : 'bg-stone-200'" />
          <RouterLink :to="{ name: 'OrderDetail', params: { name: r.order } }" class="min-w-0 w-[168px] flex-shrink-0">
            <div class="font-mono text-[12px] font-semibold text-stone-900 truncate">{{ r.order }}</div>
            <div class="text-[10.5px] text-stone-400 truncate" dir="auto">{{ r.customer }}</div>
          </RouterLink>
          <span class="text-[10px] font-bold rounded-full px-2 py-0.5 flex-shrink-0" :class="STAGE_CLS[r.stage]">
            {{ t('oclk.s_' + r.stage) }}
          </span>
          <span class="text-[11px] text-stone-400 truncate flex-1 hidden sm:block" dir="auto">{{ r.city || '—' }}</span>
          <!-- The blockers, each one a door to the screen that clears it. -->
          <div class="flex items-center gap-1 flex-wrap justify-end">
            <RouterLink v-for="w in r.why" :key="w" :to="fixLink(w, r)"
                        class="text-[10.5px] font-semibold rounded-md px-1.5 py-0.5 ring-1 inline-flex items-center gap-1 hover:bg-white"
                        :class="WHY_CLS[w]">
              <Icon :name="WHY_ICON[w]" :size="11" />{{ t('oclk.w_' + w) }}
            </RouterLink>
          </div>
          <span class="text-[12px] font-bold tabular-nums w-[64px] text-end flex-shrink-0"
                :class="r.late ? 'text-rose-600' : 'text-stone-400'">{{ age(r) }}</span>
        </div>
      </div>
    </section>

    <div v-else-if="d" class="rounded-2xl bg-white ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="check-circle" :size="24" class="mx-auto text-emerald-400" />
      <div class="text-[14px] font-semibold text-stone-700 mt-2">{{ t('oclk.blkClear') }}</div>
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
const loading = ref(true);
const why = ref("");

const ORDER = ["oos", "shelf", "city", "no_awb", "stuck_pick"];
const STAGE_CLS = {
  to_pick: "text-rose-700 bg-rose-50 ring-1 ring-rose-200",
  picking: "text-amber-700 bg-amber-50 ring-1 ring-amber-200",
  to_hand_over: "text-violet-700 bg-violet-50 ring-1 ring-violet-200",
};
const WHY_CLS = {
  oos: "text-rose-700 bg-rose-50 ring-rose-200",
  shelf: "text-amber-700 bg-amber-50 ring-amber-200",
  city: "text-sky-700 bg-sky-50 ring-sky-200",
  no_awb: "text-violet-700 bg-violet-50 ring-violet-200",
  stuck_pick: "text-stone-700 bg-stone-100 ring-stone-200",
};
const WHY_ICON = { oos: "package-x", shelf: "alert-triangle", city: "map-pin", no_awb: "truck", stuck_pick: "clock" };
const CARD_CLS = { oos: "text-rose-600", shelf: "text-amber-600", city: "text-sky-600", no_awb: "text-violet-600", stuck_pick: "text-stone-700" };

const causes = computed(() => ORDER.map((k) => ({ key: k, n: d.value?.groups?.[k] || 0, cls: CARD_CLS[k] })));
const rows = computed(() => {
  const all = d.value?.rows || [];
  return why.value ? all.filter((r) => r.why.includes(why.value)) : all;
});

// The city screen and the pipeline both accept a search; hand them the order
// so the person lands on the row, not on the top of a long list.
function fixLink(w, r) {
  const name = d.value?.fix?.[w] || "ShipBoard";
  if (w === "city") return { name, query: { q: r.city || r.order } };
  if (w === "oos" || w === "stuck_pick") return { name, query: { q: r.order } };
  return { name };
}
function age(r) {
  const h = r.ageH || 0;
  return h >= 48 ? Math.floor(h / 24) + t("oclk.dShort") : h + t("oclk.hShort");
}

async function load() {
  loading.value = true;
  try { d.value = await api("shipments.blocked"); } catch { d.value = null; }
  loading.value = false;
}
onMounted(load);
const tick = setInterval(() => { if (document.visibilityState === "visible") load(); }, 180000);
onUnmounted(() => clearInterval(tick));
</script>
