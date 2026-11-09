<template>
  <!-- Every call to this customer about this order, from both lanes, the
       Desk, the automation and the carrier (rescue.calls). It used to be a
       "x3" counter, which said how many but not who, when or what came of
       it -- and the tracking lane could not see confirmation's half at all
       (TKT-2611-4764565). -->
  <div class="rounded-xl bg-white ring-1 ring-stone-200/70 p-3" @click.stop>
    <div class="text-[11px] font-semibold text-stone-500 mb-2 flex items-center gap-1.5">
      <Icon name="phone" :size="12" />{{ t("calls.title") }}
      <span v-if="data?.calls?.length" class="text-stone-400 font-normal tabular-nums">· {{ data.calls.length }}</span>
    </div>
    <div v-if="loading" class="text-[12px] text-stone-400 text-center py-3">…</div>
    <div v-else-if="error" class="text-[12px] text-rose-500 text-center py-2">{{ error }}</div>
    <div v-else-if="!data?.calls?.length" class="text-[11.5px] text-stone-400 text-center py-1">{{ t("calls.empty") }}</div>
    <div v-else class="space-y-1 max-h-56 overflow-y-auto">
      <div v-for="(c, i) in data.calls" :key="i" class="flex items-center gap-2 text-[11.5px]">
        <span class="text-[10px] font-bold rounded px-1.5 py-0.5 shrink-0" :class="LANE_CLS[c.lane] || LANE_CLS.desk">
          {{ t("calls.lane_" + c.lane, c.lane) }}
        </span>
        <span class="font-semibold shrink-0" :class="c.action === 'dna' || c.action === 'unreachable' ? 'text-amber-700' : 'text-stone-800'">
          {{ t("calls.a_" + c.action, c.action) }}<span v-if="c.attempt" class="font-normal text-stone-400 tabular-nums"> #{{ c.attempt }}</span>
        </span>
        <span v-if="c.note" class="text-stone-500 truncate min-w-0" dir="auto">{{ c.note }}</span>
        <span class="ms-auto text-[10.5px] text-stone-400 tabular-nums shrink-0" dir="ltr">{{ c.who }} · {{ local(c.at).slice(5, 16) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";

const props = defineProps({ order: { type: String, default: "" } });
const { t } = useI18n();
const data = ref(null);
const loading = ref(false);
const error = ref("");
const LANE_CLS = {
  cf: "text-violet-700 bg-violet-50", rs: "text-teal-700 bg-teal-50",
  desk: "text-stone-600 bg-stone-100", bot: "text-sky-700 bg-sky-50",
  carrier: "text-amber-700 bg-amber-50",
};

let seq = 0;
async function load() {
  const mine = ++seq;
  data.value = null;
  error.value = "";
  if (!props.order) return;
  loading.value = true;
  try {
    const res = await api("rescue.calls", { order: props.order });
    if (mine === seq) data.value = res;
  } catch (e) {
    if (mine === seq) error.value = String(e.message || e);
  } finally {
    if (mine === seq) loading.value = false;
  }
}
watch(() => props.order, load, { immediate: true });
defineExpose({ reload: load });
</script>
