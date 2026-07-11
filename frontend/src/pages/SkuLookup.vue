<template>
  <div class="max-w-3xl mx-auto px-4 py-6 space-y-4">
    <header>
      <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('sku.title') }}</h1>
      <p class="text-[13px] text-stone-500 mt-1">{{ t('sku.pageIntro') }}</p>
    </header>

    <!-- search -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
      <div class="flex items-center gap-2">
        <div class="relative flex-1">
          <Icon name="search" :size="15" class="absolute top-1/2 -translate-y-1/2 text-stone-400" style="inset-inline-start:.7rem" />
          <input
            ref="input" v-model="q" type="text" :placeholder="t('sku.placeholder')"
            class="w-full h-11 ps-9 pe-3 rounded-xl bg-stone-50 ring-1 ring-stone-200 text-[13.5px] focus:ring-2 focus:outline-none focus:bg-white"
            style="--tw-ring-color: var(--accent-400)"
            @keydown.enter="run"
          />
        </div>
        <button class="h-11 px-5 rounded-xl text-[13.5px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50" :disabled="loading || !q.trim()" @click="run">
          {{ loading ? t('sku.searching') : t('sku.search') }}
        </button>
      </div>
      <div v-if="lastQuery" class="mt-2.5 text-[11.5px] text-stone-400">
        {{ t('sku.resultsFor') }} <span class="font-mono text-stone-600">{{ lastQuery }}</span>
        <span v-if="groups.length"> · {{ groups.length }} {{ t('sku.skusFound') }}</span>
      </div>
    </div>

    <!-- results -->
    <div v-if="loading" class="text-center text-[13px] text-stone-400 py-12">{{ t('sku.searching') }}…</div>

    <div v-else-if="searched && !groups.length" class="text-center py-16">
      <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-stone-100 text-stone-400 mb-3"><Icon name="search" :size="22" /></span>
      <div class="text-[14.5px] font-semibold text-stone-800">{{ t('sku.none') }}</div>
      <div class="text-[12.5px] text-stone-500 mt-0.5">{{ t('sku.noneHint') }}</div>
    </div>

    <div v-else-if="!searched" class="text-center py-16">
      <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-[var(--accent-50)] text-[var(--accent-600)] mb-3"><Icon name="search" :size="22" /></span>
      <div class="text-[14.5px] font-semibold text-stone-800">{{ t('sku.emptyTitle') }}</div>
      <div class="text-[12.5px] text-stone-500 mt-0.5 max-w-md mx-auto">{{ t('sku.emptyHint') }}</div>
    </div>

    <div v-else class="space-y-3">
      <div v-for="g in groups" :key="g.sku" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="flex items-center gap-2 px-4 py-2.5 bg-stone-50 border-b border-stone-100">
          <span class="font-mono text-[13px] font-semibold text-stone-900 truncate">{{ g.sku }}</span>
          <span class="text-[10.5px] text-stone-400">{{ g.items.length }} {{ t('sku.codes') }}</span>
          <span v-if="g.anyStock" class="ms-auto inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200/70 rounded-md px-2 py-0.5">
            <Icon name="check-circle" :size="11" />{{ t('sku.inStock') }}
          </span>
          <span v-else class="ms-auto inline-flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 ring-1 ring-rose-200/70 rounded-md px-2 py-0.5">{{ t('sku.allOut') }}</span>
        </div>
        <div class="divide-y divide-stone-100">
          <div v-for="it in g.items" :key="it.code" class="px-4 py-3" :class="it.avail > 0 ? 'bg-emerald-50/30' : ''">
            <div class="flex items-center gap-2">
              <span class="font-mono text-[12px] text-stone-600">{{ it.code }}</span>
              <span v-if="it.ordered" class="inline-flex items-center gap-1 text-[10px] font-semibold text-violet-700 bg-violet-50 ring-1 ring-violet-200/60 rounded px-1.5 py-0.5">{{ t('sku.ordered') }}</span>
              <span class="ms-auto text-[15px] font-bold tabular-nums" :class="it.avail > 0 ? 'text-emerald-600' : 'text-stone-400'">{{ it.avail }} <span class="text-[11px] font-medium text-stone-400">{{ t('sku.avail') }}</span></span>
            </div>
            <div class="text-[12.5px] text-stone-700 mt-1 truncate">{{ it.name }}</div>
            <div v-if="it.bins.length" class="flex flex-wrap gap-1 mt-2">
              <span v-for="b in it.bins" :key="b.bin" class="inline-flex items-center gap-1 text-[11px] font-mono text-stone-600 bg-stone-100 rounded px-2 py-0.5">
                <Icon name="map-pin" :size="10" />{{ b.bin.replace(' - JM', '') }} · {{ b.net }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const route = useRoute();
const q = ref("");
const lastQuery = ref("");
const loading = ref(false);
const searched = ref(false);
const groups = ref([]);
const input = ref(null);

async function run() {
  if (!q.value.trim()) return;
  loading.value = true;
  searched.value = true;
  lastQuery.value = q.value.trim();
  try {
    const res = await liveOr(null, () => api("inventory.sku_lookup", { query: q.value.trim() }));
    groups.value = (res && Array.isArray(res.groups)) ? res.groups : [];
  } catch {
    groups.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  // Deep-link: /logistics/sku?q=<sku or order> runs the search immediately.
  const pre = String(route.query.q || "").trim();
  if (pre) { q.value = pre; run(); }
  nextTick(() => input.value?.focus());
});
</script>
