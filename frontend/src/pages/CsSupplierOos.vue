<template>
  <div class="p-4 sm:p-5 max-w-[1100px] mx-auto">
    <div class="flex items-center gap-3 mb-1">
      <h1 class="text-[18px] font-bold text-stone-900 tracking-tight">{{ t('soos.title') }}</h1>
      <span v-if="rows.length" class="text-[12px] font-semibold tabular-nums text-rose-700 bg-rose-50 ring-1 ring-rose-200 rounded-full px-2 py-0.5">
        {{ total }}
      </span>
      <button class="ms-auto h-9 px-4 rounded-xl text-[13px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
              :disabled="loading" @click="load()">
        <Icon name="refresh-cw" :size="14" class="inline -mt-px me-1" />{{ t('common.refresh') }}
      </button>
    </div>
    <p class="text-[13px] text-stone-500 mb-4">{{ t('soos.intro') }}</p>

    <div v-if="loading" class="space-y-2.5">
      <div v-for="n in 4" :key="n" class="h-[104px] rounded-2xl bg-white ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="!rows.length" class="rounded-2xl p-12 text-center bg-white ring-1 ring-stone-200/70">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3">
        <Icon name="check-circle" :size="26" />
      </span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('soos.empty') }}</div>
    </div>

    <div v-else class="space-y-2.5">
      <div v-for="r in rows" :key="r.order" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-start gap-3 flex-wrap">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[14px] font-bold text-stone-900 truncate max-w-[200px]" dir="auto">{{ r.customer || '—' }}</span>
              <RouterLink :to="{ name: 'OrderDetail', params: { name: String(r.order).replace('#','') } }"
                          class="font-mono text-[11.5px] font-semibold text-stone-500 hover:underline" dir="ltr">{{ r.order }}</RouterLink>
              <span class="text-[12px] font-semibold text-stone-700 tabular-nums" dir="ltr">{{ Math.round(r.total) }} MAD</span>
              <span v-if="r.city" class="text-[11.5px] text-stone-400">{{ r.city }}</span>
              <span v-if="r.attempts" class="text-[10.5px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-full px-2 py-0.5">
                ×{{ r.attempts }}
              </span>
            </div>

            <!-- Which product, who said no, how long ago. The whole point of
                 the call: the agent must name the item, not the order. -->
            <div v-if="r.oos && r.oos.length" class="mt-2 space-y-1">
              <div v-for="(l, i) in r.oos" :key="i"
                   class="inline-flex items-center gap-1.5 text-[11.5px] rounded-lg px-2 py-1 bg-rose-50 ring-1 ring-rose-200/70 text-rose-800 max-w-full">
                <Icon name="package-x" :size="12" class="shrink-0" />
                <span class="font-semibold truncate" dir="auto">{{ l.qty }}× {{ l.item }}</span>
                <span class="text-rose-500 shrink-0">· {{ l.supplier }}</span>
                <span class="text-rose-400 tabular-nums shrink-0">· {{ ageLabel(l.ageH) }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-1.5 shrink-0">
            <a v-if="r.phone" :href="'tel:' + r.phone"
               class="h-9 w-9 inline-flex items-center justify-center rounded-lg text-sky-700 bg-sky-50 ring-1 ring-sky-200">
              <Icon name="phone-off" :size="14" /></a>
            <a v-if="r.phone" :href="waLink(r.phone)" target="_blank" rel="noopener"
               class="h-9 w-9 inline-flex items-center justify-center rounded-lg text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200">
              <Icon name="message-circle" :size="14" /></a>
            <button class="h-9 px-3.5 rounded-lg text-[12px] font-bold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40"
                    :title="t('soos.keepHint')" :disabled="busy === r.order" @click="act(r, 'keep')">
              {{ t('soos.keep') }}
            </button>
            <button class="h-9 px-3 rounded-lg text-[12px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 disabled:opacity-40"
                    :title="t('soos.retryHint')" :disabled="busy === r.order" @click="act(r, 'retry')">
              {{ t('soos.retry') }}
            </button>
            <button class="h-9 px-3 rounded-lg text-[12px] font-semibold text-rose-700 bg-rose-50 ring-1 ring-rose-200 disabled:opacity-40"
                    :disabled="busy === r.order" @click="cancelFor = cancelFor === r.order ? '' : r.order">
              {{ t('soos.cancel') }}
            </button>
          </div>
        </div>

        <!-- Cancelling goes through api.stop, which knows what a cancel means
             from wherever the goods already are — this order is Confirmed and
             may be on a pick list. -->
        <div v-if="cancelFor === r.order" class="mt-3 rounded-xl bg-rose-50 ring-1 ring-rose-200 p-3">
          <div class="text-[12px] text-rose-900 mb-2">{{ t('soos.cancelHint') }}</div>
          <div class="flex items-center gap-2">
            <button class="h-9 px-4 rounded-lg text-[12.5px] font-bold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-40"
                    :disabled="busy === r.order" @click="act(r, 'cancel')">{{ t('soos.cancelDo') }}</button>
            <button class="h-9 px-3 rounded-lg text-[12.5px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200"
                    @click="cancelFor = ''">{{ t('common.cancel') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Supplier out of stock — customer service's lane.
 *
 * A cross-dock supplier answered "don't have it" on a line of an order the
 * customer already confirmed. The product is not coming and the customer
 * does not know. Somebody has to ring them and agree what happens instead.
 *
 * It was built as a tab on the confirmation board on 2026-10-08, because
 * that is where the blindness was found. It is not a confirmation decision
 * though — the order is already confirmed and the customer already said yes
 * — so the lane moved here (Ahmed, 2026-10-15). The SQL and the three
 * actions stayed in api.confirmation: one definition of "the supplier said
 * no", reached through a door this team is allowed to open.
 */
import { onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const rows = ref([]);
const total = ref(0);
const loading = ref(true);
const busy = ref("");
const cancelFor = ref("");

function waLink(p) {
  p = String(p || "").replace(/\D/g, "");
  return "https://wa.me/" + (p.startsWith("212") ? p : "212" + p.replace(/^0/, ""));
}

function ageLabel(h) {
  const n = Number(h) || 0;
  return n >= 48 ? `${Math.round(n / 24)}${t("common.histD")}` : `${Math.round(n)}h`;
}

async function load() {
  loading.value = true;
  try {
    const r = await api("confirmation.board", { tab: "supplieroos", limit: 100, days: 120 });
    rows.value = r.rows || [];
    total.value = r.counts?.supplieroos ?? rows.value.length;
  } catch (e) {
    warn(t("mv.loadFail"), String(e.message || e));
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

async function act(r, action) {
  busy.value = r.order;
  try {
    const res = await apiPost("confirmation.supplier_oos_act", { order: r.order, action });
    if (action === "retry") {
      // The customer was not reached; the row stays, with the attempt on it.
      r.attempts = res.attempts || (r.attempts || 0) + 1;
    } else {
      rows.value = rows.value.filter((x) => x.order !== r.order);
      total.value = Math.max(0, total.value - 1);
    }
    cancelFor.value = "";
    success(t("soos.done_" + action), r.order);
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

onMounted(load);
</script>
