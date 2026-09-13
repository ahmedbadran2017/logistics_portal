<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1240px] mx-auto">
    <header class="sh-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-start justify-between gap-5 flex-wrap">
        <div class="flex items-center gap-3.5 min-w-0">
          <span class="sh-hero-icon" style="background: linear-gradient(135deg, rgb(245 158 11), rgb(217 119 6)); box-shadow: 0 6px 16px -6px rgb(245 158 11 / .55)"><Icon name="package-x" :size="22" /></span>
          <div class="min-w-0">
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('oclk.blkTitle') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5 max-w-[620px]">{{ t('oclk.blkIntro') }}</p>
          </div>
        </div>
        <div v-if="d" class="flex items-stretch gap-2">
          <div class="sh-stat">
            <span class="sh-stat-n" :class="d.total ? 'text-rose-600' : 'text-emerald-600'">{{ d.total }}</span>
            <span class="sh-stat-l">{{ t('oclk.railAll') }}</span>
          </div>
          <div class="sh-stat">
            <span class="sh-stat-n text-stone-900">{{ d.inHouse }}</span>
            <span class="sh-stat-l">{{ t('oclk.v_wave') }}</span>
          </div>
          <div v-if="loadError" class="sh-stat" style="box-shadow: inset 0 0 0 1px rgb(244 63 94 / .5)">
            <span class="sh-stat-n text-rose-600"><Icon name="alert-triangle" :size="18" /></span>
            <span class="sh-stat-l text-rose-600">{{ t('oclk.staleWarn') }}</span>
          </div>
        </div>
      </div>
    </header>

    <div v-if="!d && loading" class="grid md:grid-cols-[260px_1fr] gap-4">
      <div class="h-[320px] rounded-2xl sh-shimmer" />
      <div class="space-y-2.5"><div v-for="n in 5" :key="n" class="h-[68px] rounded-2xl sh-shimmer" /></div>
    </div>

    <div v-else-if="loadError && !d" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('common.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-xl text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <div v-else-if="d" class="grid md:grid-cols-[260px_1fr] gap-4 items-start">
      <!-- the rail: every cause, its count, and the verb that clears it -->
      <aside class="sh-card rounded-2xl p-2 md:sticky md:top-3">
        <div class="px-2 pt-1.5 pb-2 text-[10.5px] font-bold uppercase tracking-wide text-stone-400">{{ t('oclk.railTitle') }}</div>
        <button class="w-full text-start rounded-xl px-3 py-2.5 flex items-center gap-3 transition-colors" :class="!why ? 'bg-stone-900 text-white ring-1 ring-stone-900' : 'hover:bg-stone-50'"
                :aria-pressed="!why" @click="why = ''">
          <span class="text-[12.5px] font-semibold flex-1">{{ t('oclk.railAll') }}</span>
          <span class="text-[12px] font-bold tabular-nums">{{ d.total }}</span>
        </button>
        <button v-for="k in causes" :key="k.key" class="w-full text-start rounded-xl px-3 py-2.5 flex items-center gap-3 transition-colors mt-0.5"
                :class="why === k.key ? 'bg-stone-900 text-white ring-1 ring-stone-900' : 'hover:bg-stone-50'" :aria-pressed="why === k.key"
                @click="why = why === k.key ? '' : k.key">
          <span class="w-8 h-8 rounded-lg inline-flex items-center justify-center flex-shrink-0" :class="why === k.key ? 'bg-white/15' : k.tint">
            <Icon :name="WHY_ICON[k.key]" :size="14" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block text-[12.5px] font-semibold truncate">{{ t('oclk.w_' + k.key) }}</span>
            <span class="block text-[10.5px] truncate" :class="why === k.key ? 'text-white/70' : 'text-stone-400'">{{ t('oclk.fx_' + k.key) }}</span>
          </span>
          <span class="text-[12px] font-bold tabular-nums" :class="why === k.key ? '' : k.n ? k.text : 'text-emerald-600'">{{ k.n }}</span>
        </button>
      </aside>

      <div class="space-y-2.5 min-w-0">
        <div class="flex items-center gap-2 px-1">
          <span class="text-[13px] font-bold text-stone-900">{{ why ? t('oclk.w_' + why) : t('oclk.railAll') }}</span>
          <span v-if="why" class="text-[11px] text-stone-400">— {{ t('oclk.fx_' + why) }}</span>
          <span class="ms-auto text-[11px] text-stone-400 tabular-nums" dir="ltr">
            <template v-if="truncated">{{ rows.length }} / {{ why ? d.groups[why] : d.total }}</template>
            <template v-else>{{ rows.length }}</template>
          </span>
        </div>

        <div v-for="r in paged" :key="r.order" class="sh-card rounded-2xl px-4 py-3 flex items-center gap-4">
          <span class="w-1 self-stretch rounded-full flex-shrink-0" :class="r.late ? 'bg-rose-500' : 'bg-stone-200'" />
          <RouterLink :to="{ name: 'OrderDetail', params: { name: r.order } }" class="lp-tap min-w-0 flex-1 basis-[140px] py-0.5">
            <div class="font-mono text-[12.5px] font-bold text-stone-900 truncate" dir="ltr">{{ r.order }}</div>
            <div class="text-[11px] text-stone-400 truncate" dir="auto">{{ r.customer }}<span v-if="r.city" class="text-stone-300"> · </span><span dir="auto">{{ r.city }}</span></div>
            <!-- the exact thing missing, in the row, so nobody opens the order to learn it -->
            <div class="text-[11px] mt-0.5 truncate" dir="auto">
              <span v-if="r.shortItems && r.shortItems.length" class="text-rose-700 font-mono">{{ t('oclk.shortItems') }}: {{ r.shortItems.join(', ') }}</span>
              <span v-else-if="r.why.includes('city')" class="text-sky-700">{{ r.city || '—' }}</span>
              <span v-else-if="r.shelfBin" class="text-amber-700 font-mono">{{ r.shelfBin }}</span>
              <span v-else-if="r.pickH" class="text-stone-600">{{ t('oclk.pickFor') }} {{ r.pickH }}{{ t('oclk.hShort') }}</span>
            </div>
          </RouterLink>
          <span class="text-[10px] font-bold rounded-full px-2 py-0.5 whitespace-nowrap flex-shrink-0 hidden sm:inline" :class="STAGE_CLS[r.stage]">{{ t('oclk.s_' + r.stage) }}</span>
          <div class="flex items-center gap-1 flex-wrap justify-end">
            <RouterLink v-for="w in r.why" :key="w" :to="fixLink(w, r)"
                        class="lp-tap text-[10.5px] font-semibold rounded-full px-2 py-0.5 ring-1 inline-flex items-center gap-1 hover:bg-white"
                        :class="WHY_CLS[w]" :title="t('oclk.fx_' + w)">
              <Icon :name="WHY_ICON[w]" :size="11" />{{ t('oclk.w_' + w) }}
            </RouterLink>
          </div>
          <RouterLink :to="fixLink(r.why[0], r)" class="lp-tap hidden lg:inline-flex h-9 px-3 rounded-xl text-[12px] font-bold text-white items-center gap-1.5 flex-shrink-0"
                      style="background: linear-gradient(135deg, rgb(20 184 166), rgb(13 148 136)); box-shadow: 0 4px 12px -4px rgb(20 184 166 / .45)">
            {{ t('oclk.openFix') }}<Icon name="arrow-right" :size="13" class="flip-rtl" />
          </RouterLink>
          <span class="text-[12px] font-bold tabular-nums w-[44px] text-end flex-shrink-0" dir="ltr" :class="r.late ? 'text-rose-600' : 'text-stone-400'" :title="t('oclk.ageHint')">{{ age(r) }}</span>
        </div>

        <Pager v-if="rows.length > pageSize || page > 1" v-model:page="page" v-model:pageSize="pageSize" :total="rows.length" />

        <div v-if="!rows.length" class="sh-empty rounded-2xl p-12 text-center">
          <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center mb-3" :class="loadError ? 'bg-rose-50 text-rose-500' : why ? 'bg-stone-100 text-stone-400' : 'bg-emerald-50 text-emerald-500'">
            <Icon :name="loadError ? 'alert-triangle' : why ? 'filter' : 'check-circle'" :size="26" />
          </span>
          <div class="text-[15px] font-semibold text-stone-800">{{ loadError ? t('oclk.staleWarn') : why ? t('oclk.blkNoneCause') : t('oclk.blkClear') }}</div>
          <button v-if="loadError" class="mt-3 h-9 px-4 rounded-xl text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import Pager from "@/components/ui/Pager.vue";
import { api } from "@/lib/resource";
import { readStale, writeStale } from "@/lib/swr";
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
  oos: "text-rose-700 bg-rose-50 ring-rose-200", shelf: "text-amber-700 bg-amber-50 ring-amber-200",
  city: "text-sky-700 bg-sky-50 ring-sky-200", no_awb: "text-violet-700 bg-violet-50 ring-violet-200",
  stuck_pick: "text-stone-700 bg-stone-100 ring-stone-200",
};
const WHY_ICON = { oos: "package-x", shelf: "alert-triangle", city: "map-pin", no_awb: "truck", stuck_pick: "clock" };
const TINT = { oos: "bg-rose-50 text-rose-600", shelf: "bg-amber-50 text-amber-600", city: "bg-sky-50 text-sky-600", no_awb: "bg-violet-50 text-violet-600", stuck_pick: "bg-stone-100 text-stone-600" };
const TEXT = { oos: "text-rose-600", shelf: "text-amber-600", city: "text-sky-600", no_awb: "text-violet-600", stuck_pick: "text-stone-700" };

const causes = computed(() => ORDER.map((k) => ({ key: k, n: d.value?.groups?.[k] || 0, tint: TINT[k], text: TEXT[k] })));
const rows = computed(() => {
  const all = d.value?.rows || [];
  return why.value ? all.filter((r) => r.why.includes(why.value)) : all;
});
const truncated = computed(() => !!d.value && (d.value.rows || []).length < d.value.total);
const paged = computed(() => rows.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value));
watch(why, () => { page.value = 1; });
watch(() => rows.value.length, (n) => { page.value = Math.min(page.value, Math.max(1, Math.ceil(n / pageSize.value))); });

// Each door lands on the row, not on the top of a long list.
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
  try { d.value = await api("shipments.blocked"); loadError.value = ""; writeStale("ship.blocked", d.value); }
  catch (e) { loadError.value = String(e?.message || e); }
  loading.value = false;
}
onMounted(() => {
  const stale = readStale("ship.blocked");
  if (stale) { d.value = stale; loading.value = false; }
  load();
});
const tick = setInterval(() => { if (document.visibilityState === "visible") load(); }, 180000);
onUnmounted(() => clearInterval(tick));
</script>
