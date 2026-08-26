<template>
  <div class="max-w-[1000px] mx-auto px-4 py-6 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cityfix.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cityfix.intro') }}</p>
      </div>
      <div v-if="data" class="flex items-center gap-2">
        <span class="inline-flex items-baseline gap-1.5 text-white bg-rose-600 rounded-lg px-3 h-9 tabular-nums">
          <span class="text-[16px] font-bold">{{ data.blocked }}</span>
          <span class="text-[11px] font-medium opacity-80">{{ t('cityfix.held') }}</span>
        </span>
        <span class="inline-flex items-baseline gap-1.5 text-amber-800 bg-amber-100 rounded-lg px-3 h-9 tabular-nums">
          <span class="text-[16px] font-bold">{{ data.warn }}</span>
          <span class="text-[11px] font-medium opacity-80">{{ t('cityfix.warn') }}</span>
        </span>
      </div>
    </header>

    <div v-if="loading" class="space-y-2.5">
      <div v-for="n in 6" :key="n" class="h-[72px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
    </div>
    <div v-else-if="!rows.length" class="cf-empty rounded-2xl p-12 text-center bg-white ring-1 ring-stone-200/70">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('cityfix.empty') }}</div>
      <div class="text-[12.5px] text-stone-400 mt-1">{{ t('cityfix.emptyHint') }}</div>
    </div>

    <TransitionGroup v-else name="cfrow" tag="div" class="space-y-2.5">
      <div v-for="r in rows" :key="r.order"
           class="bg-white rounded-2xl ring-1 p-4"
           :class="r.blocked ? 'ring-rose-200' : 'ring-amber-200/70'">
        <div class="flex items-center gap-3 flex-wrap">
          <span class="inline-flex items-center gap-1 text-[10.5px] font-bold uppercase tracking-wide px-2 h-6 rounded-full flex-shrink-0"
                :class="r.blocked ? 'text-rose-700 bg-rose-50 ring-1 ring-rose-200' : 'text-amber-700 bg-amber-50 ring-1 ring-amber-200'">
            <Icon :name="r.blocked ? 'ban' : 'alert-triangle'" :size="11" />
            {{ r.blocked ? t('cityfix.blocked') : t('cityfix.unmatched') }}
          </span>
          <!-- Already picked, waiting at the sort wall with no carrier label -->
          <span v-if="r.inFlow"
                class="inline-flex items-center gap-1 text-[10.5px] font-bold uppercase tracking-wide px-2 h-6 rounded-full flex-shrink-0 text-violet-700 bg-violet-50 ring-1 ring-violet-200">
            <Icon name="package" :size="11" /> {{ t('cityfix.inFlow') }}
          </span>
          <div class="min-w-0">
            <RouterLink :to="{ name: 'OrderDetail', params: { name: r.order } }"
                        class="font-mono text-[13px] font-bold text-stone-900 hover:text-[var(--accent-700)] hover:underline">{{ r.order }}</RouterLink>
            <span class="block text-[11.5px] text-stone-500 truncate">{{ r.customer }}<span v-if="r.phone" class="font-mono"> · {{ r.phone }}</span></span>
          </div>
          <div class="ms-auto text-end flex-shrink-0">
            <div class="text-[10.5px] uppercase tracking-wide text-stone-400">{{ t('cityfix.current') }}</div>
            <div class="text-[12.5px] font-semibold" dir="auto"
                 :class="r.blocked ? 'text-rose-600' : 'text-amber-700'">{{ r.city || '—' }}</div>
          </div>
        </div>

        <div class="flex items-center gap-2 mt-3">
          <div class="flex-1 min-w-0">
            <ReasonSelect v-model="pick[r.order]" :options="cities" allow-custom
                          :placeholder="t('cityfix.pickCity')"
                          :search-placeholder="t('cityfix.searchCity')"
                          :custom-label="t('cityfix.useTyped')"
                          :none-text="t('cityfix.noCity')" />
          </div>
          <button class="h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-40 shrink-0"
                  :disabled="!pick[r.order] || busy === r.order" @click="save(r)">
            {{ t('px.common.save') }}
          </button>
          <!-- In-flow parcels also need the AWB regenerated after the fix;
               saves the picked city first when one is chosen. -->
          <button v-if="r.inFlow"
                  class="h-9 px-3.5 rounded-lg text-[12.5px] font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-40 shrink-0 inline-flex items-center gap-1.5"
                  :disabled="busy === r.order" @click="fixAndRetry(r)">
            <Icon name="refresh-cw" :size="13" /> {{ t('cityfix.retryAwb') }}
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import ReasonSelect from "@/components/ui/ReasonSelect.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const data = ref(null);
const rows = ref([]);
const cities = ref([]);
const pick = ref({});
const loading = ref(true);
const loadError = ref("");
const busy = ref("");

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const [q, c] = await Promise.all([
      api("city.city_check_queue"),
      api("city.cathedis_cities"),
    ]);
    data.value = q;
    rows.value = q.rows || [];
    cities.value = c?.cities || [];
  } catch (e) {
    loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}

async function save(r) {
  busy.value = r.order;
  try {
    await apiPost("city.set_shipping_city", { order: r.order, city: pick.value[r.order] });
    rows.value = rows.value.filter((x) => x.order !== r.order);
    if (data.value) {
      if (r.blocked) data.value.blocked = Math.max(0, data.value.blocked - 1);
      else data.value.warn = Math.max(0, data.value.warn - 1);
    }
    success(t("cityfix.fixed"), `${r.order} → ${pick.value[r.order]}`);
    delete pick.value[r.order];
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

// In-flow recovery: save the corrected city (if one was picked), then re-run
// the carrier automation. The row leaves the queue once the AWB is enqueued —
// if the city was left bad, Cathedis will fail again and the row returns.
async function fixAndRetry(r) {
  busy.value = r.order;
  try {
    if (pick.value[r.order]) {
      await apiPost("city.set_shipping_city", { order: r.order, city: pick.value[r.order] });
    }
    const res = await apiPost("shipping.retry_awb", { order: r.order });
    rows.value = rows.value.filter((x) => x.order !== r.order);
    if (data.value) data.value.inFlow = Math.max(0, (data.value.inFlow || 0) - 1);
    success(t("cityfix.retried"), res && res.awb ? `${r.order} · AWB ${res.awb}` : r.order);
    delete pick.value[r.order];
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

onMounted(load);
</script>
