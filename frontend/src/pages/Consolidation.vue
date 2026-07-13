<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1100px] mx-auto animate-fade-in">
    <!-- Title row -->
    <div>
      <div class="flex items-center justify-between gap-3 flex-wrap">
        <div class="flex items-center gap-2.5 min-w-0">
          <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em] whitespace-nowrap">{{ t("consol.title") }}</h1>
          <span v-if="groups.length" class="inline-flex items-center gap-1 text-[11.5px] font-semibold text-violet-700 bg-violet-50 ring-1 ring-violet-200/60 rounded-md px-1.5 py-0.5 whitespace-nowrap tabular-nums">
            {{ groups.length }} · {{ extraParcels }} {{ t("ordersPg.consolParcels") }}
          </span>
        </div>
        <button
          class="inline-flex items-center justify-center h-9 w-9 rounded-lg text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          :class="loading ? 'opacity-60 pointer-events-none' : ''"
          :title="t('common.refresh')"
          :aria-label="t('common.refresh')"
          @click="load"
        >
          <Icon name="refresh-cw" :size="14" :class="loading ? 'animate-spin' : ''" />
        </button>
      </div>
      <p class="text-[13px] text-stone-500 mt-1">{{ t("consol.subtitle") }}</p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-3">
      <div v-for="n in 4" :key="n" class="h-[104px] rounded-xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
    </div>

    <!-- Empty -->
    <div v-else-if="!groups.length" class="rounded-2xl ring-1 ring-emerald-200/70 bg-gradient-to-r from-emerald-50 to-white p-6 flex items-center gap-4">
      <span class="w-11 h-11 rounded-2xl bg-emerald-500 text-white flex items-center justify-center flex-shrink-0">
        <Icon name="check-circle" :size="22" />
      </span>
      <div>
        <div class="text-[14.5px] font-semibold text-stone-900">{{ t("consol.emptyTitle") }}</div>
        <div class="text-[12.5px] text-stone-500 mt-0.5">{{ t("consol.emptyBody") }}</div>
      </div>
    </div>

    <!-- Groups -->
    <div v-else class="space-y-3">
      <div
        v-for="g in groups"
        :key="g.key"
        class="bg-white rounded-xl ring-1 overflow-hidden transition-shadow"
        :class="confirming === g.key ? 'ring-[var(--accent-400)] shadow-md' : 'ring-stone-200/70'"
      >
        <!-- Group head -->
        <div class="px-4 py-3 flex items-center gap-3 flex-wrap border-b border-stone-50">
          <div class="min-w-0 flex-1">
            <div class="text-[13.5px] font-semibold text-stone-900 truncate">
              {{ g.customer }}
              <span class="text-[11.5px] font-normal text-stone-400 ms-1" dir="ltr">{{ g.phone }}</span>
            </div>
            <div class="text-[11.5px] text-stone-400 flex items-center gap-1.5 mt-0.5">
              <span v-if="g.city" class="capitalize">{{ g.city }}</span>
              <span v-if="!g.sameAddress" class="text-amber-600 font-medium inline-flex items-center gap-0.5">
                <Icon name="alert-triangle" :size="10" /> {{ t("ordersPg.consolDiffAddr") }}
              </span>
              <span>· {{ fmtAge(g.ageMins) }}</span>
            </div>
          </div>
          <span class="text-[12px] font-bold text-violet-700 bg-violet-50 ring-1 ring-violet-200/50 rounded-md px-2 py-0.5 tabular-nums flex-shrink-0">
            {{ g.count }} {{ t("ordersPg.blOrders") }}
          </span>
          <span class="text-[13px] font-semibold text-stone-900 tabular-nums flex-shrink-0">{{ fmtMAD(g.mad) }} MAD</span>
        </div>

        <!-- Orders in the group -->
        <div class="divide-y divide-stone-50">
          <button
            v-for="o in g.orders"
            :key="o.no"
            class="w-full text-start px-4 py-2 flex items-center gap-3 hover:bg-stone-50 transition-colors"
            @click="openOrder(o.no)"
          >
            <span class="text-[12.5px] font-mono font-medium text-stone-800 tabular-nums">{{ o.no }}</span>
            <span class="text-[11px] text-stone-400">{{ o.items }} {{ t("consol.items") }}</span>
            <span class="text-[11px] text-stone-400 ms-auto">{{ fmtAge(o.ageMins) }}</span>
            <span class="text-[12px] text-stone-600 tabular-nums w-[86px] text-end">{{ fmtMAD(o.total) }} MAD</span>
            <Icon name="chevron-right" :size="13" class="text-stone-300 rtl:rotate-180" />
          </button>
        </div>

        <!-- Actions -->
        <div class="px-4 py-3 bg-stone-50/60 border-t border-stone-100">
          <!-- Confirm state: merge summary + final confirm -->
          <div v-if="confirming === g.key" class="flex items-center gap-3 flex-wrap">
            <Icon name="alert-circle" :size="15" class="text-[var(--accent-600)] flex-shrink-0" />
            <span class="text-[12.5px] text-stone-700 flex-1 min-w-[220px]">
              {{ t("consol.confirmBody").replace("{n}", g.count).replace("{mad}", fmtMAD(g.mad)) }}
            </span>
            <button
              class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg text-[13px] font-semibold text-white disabled:opacity-50"
              style="background: var(--accent-600)"
              :disabled="busy === g.key"
              @click="doMerge(g)"
            >
              <Icon name="check" :size="14" />
              {{ busy === g.key ? t("consol.merging") : t("consol.confirmYes") }}
            </button>
            <button
              class="h-9 px-3 rounded-lg text-[13px] font-medium text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
              :disabled="busy === g.key"
              @click="confirming = ''"
            >
              {{ t("common.cancel") }}
            </button>
          </div>
          <!-- Default actions -->
          <div v-else class="flex items-center gap-2 flex-wrap justify-end">
            <button
              class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 disabled:opacity-50"
              :disabled="busy === g.key"
              @click="shipTogether(g)"
            >
              <Icon name="layers" :size="13" />
              {{ busy === g.key ? t("ordersPg.creating") : t("ordersPg.consolShip") }}
            </button>
            <button
              class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg text-[13px] font-semibold text-white shadow-sm"
              style="background: var(--accent-600)"
              @click="confirming = g.key"
            >
              <Icon name="git-merge" :size="14" /> {{ t("consol.mergeBtn") }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Merged results (this session) -->
    <div v-if="merged.length" class="bg-white rounded-xl ring-1 ring-emerald-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
        <Icon name="check-circle" :size="14" class="text-emerald-600" />
        <span class="text-[12px] font-semibold text-stone-900">{{ t("consol.mergedTitle") }}</span>
      </div>
      <div class="divide-y divide-stone-50">
        <button
          v-for="m in merged" :key="m.order"
          class="w-full text-start px-4 py-2.5 flex items-center gap-3 hover:bg-stone-50 transition-colors"
          @click="openOrder(m.order)"
        >
          <span class="text-[12.5px] font-mono font-semibold text-emerald-700">{{ m.order }}</span>
          <span class="text-[11.5px] text-stone-500">{{ m.items }} {{ t("consol.items") }} · {{ t("consol.replacing") }} {{ m.cancelled.join(" · ") }}</span>
          <span class="text-[12.5px] font-semibold text-stone-900 tabular-nums ms-auto">{{ fmtMAD(m.total) }} MAD</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const router = useRouter();

const groups = ref([]);
const loading = ref(true);
const busy = ref("");
const confirming = ref("");
const merged = ref([]);

const extraParcels = computed(() =>
  groups.value.reduce((a, g) => a + Math.max(0, (g.count || 0) - 1), 0));

async function load() {
  loading.value = true;
  try {
    groups.value = (await api("orders.consolidation_groups", { limit: 60 })) || [];
  } catch (e) {
    warn(t("consol.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
onMounted(load);

async function doMerge(g) {
  busy.value = g.key;
  try {
    const res = await apiPost("orders.merge_orders", { orders: g.orders.map((o) => o.no) });
    merged.value.unshift(res);
    groups.value = groups.value.filter((x) => x.key !== g.key);
    confirming.value = "";
    success(t("consol.mergedToast").replace("{o}", res.order), `${res.items} ${t("consol.items")} · ${fmtMAD(res.total)} MAD`);
  } catch (e) {
    warn(t("consol.mergeFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

// The safe alternative: one pick list, separate parcels (kept from Orders).
async function shipTogether(g) {
  busy.value = g.key;
  try {
    const res = await apiPost("picking.create_pick_list_from_orders", {
      orders: g.orders.map((o) => o.no),
    });
    const nSkip = (res.skipped || []).length;
    success(
      t("ordersPg.consolDone").replace("{n}", res.orders).replace("{c}", g.customer),
      `${res.pl}` + (nSkip ? ` · ${nSkip} ${t("ordersPg.consolSkipped")}` : ""),
    );
    groups.value = groups.value.filter((x) => x.key !== g.key);
  } catch (e) {
    warn(t("ordersPg.consolFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

function openOrder(no) {
  router.push({ name: "OrderDetail", params: { name: String(no).replace("#", "") } });
}

function fmtMAD(v) {
  return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
}
function fmtAge(mins) {
  const m = Number(mins || 0);
  if (m < 60) return `${m}m`;
  if (m < 60 * 24) return `${Math.floor(m / 60)}h`;
  return `${Math.floor(m / 1440)}d`;
}
</script>
