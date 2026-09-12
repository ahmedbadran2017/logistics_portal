<template>
  <div class="max-w-[1000px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-end justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <RouterLink :to="{ name: 'VelocityBoard' }"
                    class="text-[11.5px] font-semibold text-stone-400 hover:text-stone-700 inline-flex items-center gap-1">
          <Icon name="chevron-left" :size="12" />{{ t('stuck.back') }}
        </RouterLink>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight mt-0.5">
          {{ t('vel.stuck_' + key) }}
        </h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('stuck.why_' + key) }}</p>
      </div>
      <div v-if="d" class="text-end">
        <div class="text-[30px] font-extrabold tabular-nums leading-none"
             :class="d.total ? 'text-rose-600' : 'text-stone-300'">{{ d.total }}</div>
        <div class="text-[10px] uppercase font-semibold text-stone-400 mt-0.5">{{ t('stuck.orders') }}</div>
      </div>
    </header>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 6" :key="n" class="h-[52px] rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <template v-else-if="d && d.total">
      <!-- How far each parcel actually got. A printed label with no delivery
           note is a different failure, and a different fix, from a parcel
           that has its note and was never handed over — so the pile splits
           before anyone starts working it. -->
      <div class="flex items-center gap-1.5 flex-wrap">
        <button class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors tabular-nums"
                :class="stage === '' ? 'text-white bg-stone-900 ring-stone-900' : 'text-stone-600 bg-white ring-stone-200 hover:ring-stone-300'"
                @click="stage = ''">{{ t('stuck.all') }} {{ d.total }}</button>
        <button v-for="(n, g) in d.groups" :key="g"
                class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors tabular-nums"
                :class="stage === g ? 'text-white bg-stone-900 ring-stone-900' : STAGE_CLS[g] || 'text-stone-600 bg-white ring-stone-200'"
                @click="stage = stage === g ? '' : g">{{ t('stuck.g_' + g) }} {{ n }}</button>
      </div>

      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="divide-y divide-stone-50">
          <RouterLink v-for="o in rows" :key="o.order"
                      :to="{ name: 'OrderDetail', params: { name: o.order } }"
                      class="px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50 transition-colors">
            <span class="font-mono text-[12px] font-semibold text-stone-900 w-[150px] truncate flex-shrink-0">{{ o.order }}</span>
            <span class="text-[12px] text-stone-600 truncate flex-1 min-w-0" dir="auto">{{ o.customer }}</span>
            <span class="text-[11px] text-stone-400 truncate w-[110px] hidden sm:block" dir="auto">{{ o.city }}</span>
            <span class="text-[10px] font-bold rounded-full px-2 py-0.5 flex-shrink-0" :class="STAGE_CLS[o.reason]">
              {{ t('stuck.g_' + o.reason) }}
            </span>
            <span class="text-[11.5px] text-stone-500 tabular-nums w-[72px] text-end hidden md:block">{{ fmt(o.value) }}</span>
            <span class="text-[12px] font-bold tabular-nums w-[44px] text-end flex-shrink-0"
                  :class="o.ageD >= 10 ? 'text-rose-600' : 'text-amber-600'">{{ o.ageD }}{{ t('vel.dayShort') }}</span>
          </RouterLink>
        </div>
      </div>
      <p class="text-[11px] text-stone-400 px-1">{{ t('stuck.tip') }}</p>
    </template>

    <div v-else class="rounded-2xl bg-white ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="check-circle" :size="24" class="mx-auto text-emerald-400" />
      <div class="text-[14px] font-semibold text-stone-700 mt-2">{{ t('vel.clear') }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const route = useRoute();
const d = ref(null);
const loading = ref(true);
const stage = ref("");
const key = computed(() => String(route.params.key || "labelledStale"));

const STAGE_CLS = {
  noDn: "text-rose-700 bg-rose-50 ring-1 ring-rose-200",
  noAwb: "text-amber-700 bg-amber-50 ring-1 ring-amber-200",
  noManifest: "text-sky-700 bg-sky-50 ring-1 ring-sky-200",
  handed: "text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200",
};

const rows = computed(() => {
  const all = d.value?.rows || [];
  return stage.value ? all.filter((r) => r.reason === stage.value) : all;
});
function fmt(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }

async function load() {
  loading.value = true;
  stage.value = "";
  try { d.value = await api("velocity.stuck_list", { key: key.value }); }
  catch { d.value = null; }
  loading.value = false;
}
watch(key, load);
onMounted(load);
</script>
