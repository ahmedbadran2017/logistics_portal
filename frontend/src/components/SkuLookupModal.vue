<template>
  <div v-if="open" class="fixed inset-0 z-[160] flex items-start justify-center p-4 pt-[8vh]" role="dialog" aria-modal="true">
    <div class="absolute inset-0 bg-stone-900/30 backdrop-blur-[1px] animate-fade-in" @click="close" />
    <div class="relative w-full max-w-[640px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] animate-scale-in overflow-hidden flex flex-col max-h-[80vh]">
      <header class="flex items-center gap-2.5 px-5 py-3.5 border-b border-stone-100">
        <span class="inline-flex w-8 h-8 rounded-lg items-center justify-center bg-[var(--accent-50)] text-[var(--accent-700)]"><Icon name="search" :size="16" /></span>
        <div class="min-w-0">
          <div class="text-[14.5px] font-semibold text-stone-900">{{ t('sku.title') }}</div>
          <div class="text-[11.5px] text-stone-400">{{ t('sku.subtitle') }}</div>
        </div>
        <button class="ms-auto text-stone-400 hover:text-stone-700" @click="close"><Icon name="x" :size="18" /></button>
      </header>

      <div class="px-5 py-3 border-b border-stone-100">
        <div class="flex items-center gap-2">
          <div class="relative flex-1">
            <Icon name="search" :size="14" class="absolute top-1/2 -translate-y-1/2 text-stone-400" style="inset-inline-start:.6rem" />
            <input
              ref="input" v-model="q" type="text" :placeholder="t('sku.placeholder')"
              class="w-full h-10 ps-8 pe-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[13px] focus:ring-2 focus:outline-none focus:bg-white"
              style="--tw-ring-color: var(--accent-400)"
              @keydown.enter="run"
            />
          </div>
          <button class="h-10 px-4 rounded-lg text-[13px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50" :disabled="loading || !q.trim()" @click="run">
            {{ loading ? t('sku.searching') : t('sku.search') }}
          </button>
        </div>
      </div>

      <div class="overflow-y-auto p-4 space-y-3">
        <div v-if="loading" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('sku.searching') }}…</div>

        <div v-else-if="searched && !groups.length" class="text-center py-10">
          <span class="inline-flex w-11 h-11 rounded-xl items-center justify-center bg-stone-100 text-stone-400 mb-2"><Icon name="search" :size="20" /></span>
          <div class="text-[13.5px] font-semibold text-stone-800">{{ t('sku.none') }}</div>
          <div class="text-[12px] text-stone-500 mt-0.5">{{ t('sku.noneHint') }}</div>
        </div>

        <div v-for="g in groups" :key="g.sku" class="rounded-xl ring-1 ring-stone-200 overflow-hidden">
          <div class="flex items-center gap-2 px-3 py-2 bg-stone-50 border-b border-stone-100">
            <span class="font-mono text-[12px] font-semibold text-stone-900 truncate">{{ g.sku }}</span>
            <span v-if="g.anyStock" class="ms-auto inline-flex items-center gap-1 text-[10.5px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200/70 rounded px-1.5 py-0.5">
              <Icon name="check-circle" :size="10" />{{ t('sku.inStock') }}
            </span>
            <span v-else class="ms-auto inline-flex items-center gap-1 text-[10.5px] font-semibold text-rose-700 bg-rose-50 ring-1 ring-rose-200/70 rounded px-1.5 py-0.5">
              {{ t('sku.allOut') }}
            </span>
          </div>
          <div class="divide-y divide-stone-100">
            <div v-for="it in g.items" :key="it.code" class="px-3 py-2.5" :class="it.avail > 0 ? 'bg-emerald-50/30' : ''">
              <div class="flex items-center gap-2">
                <span class="font-mono text-[11.5px] text-stone-600">{{ it.code }}</span>
                <span v-if="it.ordered" class="inline-flex items-center gap-1 text-[10px] font-semibold text-violet-700 bg-violet-50 ring-1 ring-violet-200/60 rounded px-1.5 py-0.5">{{ t('sku.ordered') }}</span>
                <span class="ms-auto text-[13px] font-bold tabular-nums" :class="it.avail > 0 ? 'text-emerald-600' : 'text-stone-400'">{{ it.avail }}</span>
              </div>
              <div class="text-[12px] text-stone-700 mt-1 truncate">{{ it.name }}</div>
              <div v-if="it.bins.length" class="flex flex-wrap gap-1 mt-1.5">
                <span v-for="b in it.bins" :key="b.bin" class="inline-flex items-center gap-1 text-[10.5px] font-mono text-stone-600 bg-stone-100 rounded px-1.5 py-0.5">
                  <Icon name="map-pin" :size="9" />{{ b.bin.replace(' - JM', '') }} · {{ b.net }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const open = ref(false);
const q = ref("");
const loading = ref(false);
const searched = ref(false);
const groups = ref([]);
const input = ref(null);

async function run() {
  if (!q.value.trim()) return;
  loading.value = true;
  searched.value = true;
  try {
    const res = await liveOr(null, () => api("inventory.sku_lookup", { query: q.value.trim() }));
    groups.value = (res && Array.isArray(res.groups)) ? res.groups : [];
  } catch {
    groups.value = [];
  } finally {
    loading.value = false;
  }
}
function openWith(query = "") {
  open.value = true;
  q.value = query || "";
  groups.value = [];
  searched.value = false;
  nextTick(() => {
    input.value?.focus();
    if (query) run();
  });
}
function close() { open.value = false; }
defineExpose({ openWith });
</script>
