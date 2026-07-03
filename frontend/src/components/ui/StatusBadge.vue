<template>
  <span class="badge" :style="style">
    <span class="w-1.5 h-1.5 rounded-full" :style="{ background: hex }" />
    {{ display }}
    <span v-if="count" class="opacity-70">{{ count }}</span>
  </span>
</template>

<script setup>
import { computed } from "vue";
import { STAGE_COLOR, SLA_COLOR, TRACK_COLOR, colorHex } from "@/lib/status";
import { useI18n } from "@/composables/useI18n";

const props = defineProps({
  value: { type: String, required: true },
  kind: { type: String, default: "stage" }, // stage | sla | track | plain
  count: { type: String, default: "" },
});

const { t } = useI18n();
const maps = { stage: STAGE_COLOR, sla: SLA_COLOR, track: TRACK_COLOR };

const hex = computed(() => colorHex((maps[props.kind] || {})[props.value] || "slate"));
const style = computed(() => ({
  background: `${hex.value}26`, // ~15% alpha
  color: hex.value,
}));
const display = computed(() => {
  if (props.kind === "stage") return t(`stage.${props.value}`, props.value);
  return props.value;
});
</script>
