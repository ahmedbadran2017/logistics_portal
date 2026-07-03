<template>
  <div class="flex items-center gap-2">
    <div class="flex-1 h-2 rounded-full bg-card2 overflow-hidden min-w-[48px]">
      <div
        class="h-full rounded-full transition-all duration-500"
        :class="{ 'animate-pulse': status === 'At Risk' }"
        :style="{ width: pct + '%', background: hex }"
      />
    </div>
    <span class="text-xs font-semibold tabular whitespace-nowrap" :style="{ color: hex }">
      {{ label }}
    </span>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { slaHex } from "@/lib/status";

/**
 * status: On Track | At Risk | Breached | Delivered | Delivered Late | Returned
 * remaining: human string ("2h 10m" or "3d") shown as the label
 * ratio: 0..1 fill (1 = full time left, 0 = deadline). Breached shows overdue.
 */
const props = defineProps({
  status: { type: String, default: "On Track" },
  remaining: { type: String, default: "" },
  ratio: { type: Number, default: 1 },
});

const hex = computed(() => slaHex(props.status));
const pct = computed(() => {
  if (props.status === "Breached") return 100;
  return Math.max(4, Math.min(100, Math.round(props.ratio * 100)));
});
const label = computed(() => {
  if (props.status === "Breached") return props.remaining ? `Overdue ${props.remaining}` : "Overdue";
  if (props.status === "Delivered") return "Delivered";
  return props.remaining || props.status;
});
</script>
