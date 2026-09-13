<template>
  <div class="max-w-[1200px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('oclk.blkTitle') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[720px]">{{ t('oclk.blkIntro') }}</p>
      </div>
      <div v-if="d" class="text-[11.5px] text-stone-400 tabular-nums" dir="ltr">
        {{ d.total }} / {{ d.inHouse }} <span dir="auto">{{ t('oclk.blkOf') }}</span>
      </div>
    </header>

    <!-- One card per cause. Each is a filter, and each names its own repair. -->
    <section v-if="d" class="grid grid-cols-2 md:grid-cols-5 gap-2.5">
      <button v-for="k in causes" :key="k.key"
              class="rounded-xl bg-white ring-1 p-3.5 text-start transition-shadow hover:shadow-sm"
              :class="why === k.key ? 'ring-2 ring-[var(--accent-600)]' : 'ring-stone-200/70'"
              :aria-pressed="why === k.key"
              @click="why = why === k.key ? '' : k.key">
        <div class="text-[24px] font-extrabold tabular-nums leading-none"
             :class="k.n ? k.cls : 'text-emerald-600'">{{ k.n }}</div>
        <div class="text-[11px] font-semibold text-stone-600 mt-1">{{ t('oclk.w_' + k.key) }}</div>
        <div class="text-[10.5px] text-stone-400">{{ t('oclk.wh_' + k.key) }}</div>
      </button>
    </section>

    <div v-if="!d && loading" class="space-y-2">
      <div v-for="n in 6" :key="n" class="h-[52px] rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="loadError && !d" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('common.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <section v-else-if="rows.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
        <span class="text-[12px] font-semibold text-stone-900">{{ why ? t('oclk.w_' + why) : t('oclk.blkAll') }}</span>
        <span v-if="loadError" class="text-[10.5px] text-rose-600">{{ t('oclk.staleWarn') }}</span>
        <span class="ms-auto text-[11px] text-stone-400 tabular-nums" dir="ltr">
          <template v-if="truncated">{{ rows.length }} / {{ why ? d.groups[why] : d.total }}</template>
          <template v-else>{{ rows.length }}</template>
        </span>
      </div>
      <div class="divide-y divide-stone-50">
        <div v-for="r in paged" :key="r.order" class="px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50 transition-colors">
          <span class="w-1 h-8 rounded-full flex-shrink-0" :class="r.late ? 'bg-rose-500' : 'bg-stone-200'" />
          <RouterLink :to="{ name: 'OrderDetail', params: { name: r.order } }" class="lp-tap min-w-0 flex-1 basis-[120px] py-1">
            <div class="font-mono text-[12px] font-semibold text-stone-900 truncate" dir="ltr">{{ r.order }}</div>
            <div class="text-[10.5px] text-stone-400 truncate" dir="auto">{{ r.customer }}</div>
          </RouterLink>
          <span class="text-[10px] font-bold rounded-full px-2 py-0.5 flex-shrink-0 whitespace-nowrap hidden sm:inline" :class="STAGE_CLS[r.stage]">
            {{ t('oclk.s_' + r.stage) }}
          </span>
          <span class="text-[11px] text-stone-400 truncate flex-1 hidden md:block" dir="auto">{{ r.city || '—' }}</span>
          <!-- The blockers, each one a door to the screen that clears it. -->
          <div class="flex items-center gap-1 flex-wrap justify-end">
            <RouterLink v-for="w in r.why" :key="w" :to="fixLink(w, r)"
                        class="lp-tap text-[10.5px] font-semibold rounded-md px-1.5 py-1 ring-1 inline-flex items-center gap-1 hover:bg-white"
                        :class="WHY_CLS[w]" :title="t('oclk.wh_' + w)">
              <Icon :name="WHY_ICON[w]" :size="11" />{{ t('oclk.w_' + w) }}
            </RouterLink>
          </div>
          <span class="text-[12px] font-bold tabular-nums w-[48px] text-end flex-shrink-0" dir="ltr"
                :class="r.late ? 'text-rose-600' : 'text-stone-400'" :title="t('oclk.ageHint')">{{ age(r) }}</span>
        </div>
      </div>
    </section>

    <Pager v-if="rows.length > pageSize || page > 1" v-model:page="page" v-model:pageSize="pageSize" :total="rows.length" />

    <div v-if="d && !rows.length && !(loadError && !d)" class="rounded-2xl bg-white ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="check-circle" :size="24" class="mx-auto text-emerald-400" />
      <div class="text-[14px] font-semibold text-stone-700 mt-2">{{ t('oclk.blkClear') }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import Pager from "@/components/ui/Pager.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const d = ref(null);
const loading = ref(true);
const loadError = ref("");
const why = ref("");
const page = ref(1);
const pageSize = ref(50);

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
// The cards count every hit; the list is capped server-side far above
// anything the floor has produced (2,000) and paged here.
const truncated = computed(() => !!d.value && (d.value.rows || []).length < d.value.total);
const paged = computed(() => rows.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value));
watch(why, () => { page.value = 1; });

// Each door lands on the row, not on the top of a long list: the pipeline
// and the pick lists seed their search from `q`, the manifest screen has an
// orphans view, and the count screen opens straight on the short bin.
function fixLink(w, r) {
  const name = d.value?.fix?.[w] || "ShipBoard";
  if (w === "oos" || w === "stuck_pick") return { name, query: { q: r.order } };
  if (w === "no_awb") return { name, query: { orphans: 1 } };
  if (w === "shelf" && r.shelfBin) return { name, query: { bin: r.shelfBin } };
  return { name };
}
function age(r) {
  const h = r.ageH || 0;
  return h >= 48 ? Math.floor(h / 24) + t("oclk.dShort") : h + t("oclk.hShort");
}

async function load() {
  if (!d.value) loading.value = true;
  try { d.value = await api("shipments.blocked"); loadError.value = ""; }
  catch (e) { loadError.value = String(e?.message || e); }
  loading.value = false;
}
onMounted(load);
const tick = setInterval(() => { if (document.visibilityState === "visible") load(); }, 180000);
onUnmounted(() => clearInterval(tick));
</script>
