<template>
  <!-- Who this customer is: every order they ever made, under the same
       numbers the confirmation lane reads on its call (customers.card). The
       tracking lane asked for it in TKT-2611-4764565 -- it follows a parcel
       on the phone with the same person, and had no way to see the rest. -->
  <div class="rounded-xl bg-stone-50 ring-1 ring-stone-200/70 p-3" @click.stop>
    <div class="text-[11px] font-semibold text-stone-500 mb-2 flex items-center gap-1.5">
      <Icon name="users" :size="12" />{{ t("seg.historyTitle") }}
    </div>
    <div v-if="loading" class="text-[12px] text-stone-400 text-center py-4">…</div>
    <div v-else-if="error" class="text-[12px] text-rose-500 text-center py-3">{{ error }}</div>
    <template v-else-if="card">
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11.5px] tabular-nums pb-2.5 mb-2.5 border-b border-stone-200/70">
        <span class="text-stone-500">{{ t("seg.hOrders") }} <b class="text-stone-800">{{ card.orders || 0 }}</b></span>
        <span class="text-stone-500">{{ t("seg.hDelivered") }} <b class="text-emerald-600">{{ card.delivered || 0 }}</b></span>
        <span class="text-stone-500">{{ t("seg.hFailed") }} <b class="text-rose-600">{{ card.failed || 0 }}</b></span>
        <span class="text-stone-500">{{ t("seg.hCancelled") }} <b class="text-stone-700">{{ card.cancelled || 0 }}</b></span>
        <span v-if="card.lifetime" class="text-stone-500">{{ t("seg.hLifetime") }} <b class="text-stone-900">{{ fmt(card.lifetime) }}</b> MAD</span>
      </div>
      <div v-if="!(card.recent || []).length" class="text-[11.5px] text-stone-400 text-center py-1">{{ t("seg.historyEmpty") }}</div>
      <div v-else class="space-y-1">
        <RouterLink v-for="o in card.recent" :key="o.order"
                    :to="{ name: 'OrderDetail', params: { name: String(o.order).replace('#', '') } }"
                    class="flex items-center gap-2 text-[11.5px] bg-white rounded-lg px-2.5 py-1.5 ring-1 ring-stone-200/60 hover:ring-stone-300"
                    :class="o.order === current ? 'ring-2 ring-sky-300' : ''">
          <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="dot(o.track, o.status)" />
          <span class="font-mono text-stone-700 shrink-0" dir="ltr">{{ o.order }}</span>
          <span class="text-stone-400 tabular-nums shrink-0" dir="ltr">{{ o.at }}</span>
          <span v-if="o.city" class="text-stone-400 truncate">{{ o.city }}</span>
          <span class="ms-auto text-stone-500 shrink-0">{{ o.track || o.status }}</span>
          <span class="font-semibold text-stone-800 tabular-nums shrink-0 w-[64px] text-end">{{ fmt(o.total) }}</span>
        </RouterLink>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const props = defineProps({
  phone: { type: String, default: "" },
  // The order the agent is on, highlighted in the list.
  current: { type: String, default: "" },
});
const { t } = useI18n();
const card = ref(null);
const loading = ref(false);
const error = ref("");

function fmt(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
function dot(track, status) {
  if (track === "Delivered") return "bg-emerald-500";
  if (track === "Delivery Exception" || track === "Failed Attempt") return "bg-rose-500";
  if (status === "Cancelled") return "bg-stone-300";
  return "bg-amber-400";
}

let seq = 0;
watch(() => props.phone, async (phone) => {
  const mine = ++seq;
  card.value = null;
  error.value = "";
  if (!phone) return;
  loading.value = true;
  try {
    const res = await api("customers.card", { phone });
    if (mine === seq) card.value = res;
  } catch (e) {
    if (mine === seq) error.value = String(e.message || e);
  } finally {
    if (mine === seq) loading.value = false;
  }
}, { immediate: true });
</script>
