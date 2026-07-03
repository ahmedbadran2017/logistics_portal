<template>
  <button
    type="button"
    class="lp-card p-5 text-left w-full relative overflow-hidden transition-all duration-150
           hover:shadow-glow hover:-translate-y-0.5"
    :class="clickable ? 'cursor-pointer' : 'cursor-default'"
    :disabled="!clickable"
  >
    <span class="absolute inset-x-0 top-0 h-1" :style="{ background: accentHex }" />
    <div class="flex items-center justify-between mb-3">
      <span class="caption">{{ title }}</span>
      <Icon v-if="icon" :name="icon" :size="16" class="text-content-3" />
    </div>
    <template v-if="loading">
      <div class="skeleton h-9 w-24 mb-2" />
      <div class="skeleton h-4 w-16" />
    </template>
    <template v-else>
      <div class="text-h1 tabular text-content leading-none">{{ value }}</div>
      <div class="flex items-center gap-2 mt-2">
        <span v-if="sub" class="text-sm text-content-3 tabular">{{ sub }}</span>
        <span
          v-if="trend != null"
          class="badge text-[11px] py-0.5"
          :style="trendStyle"
        >{{ trend > 0 ? "▲" : trend < 0 ? "▼" : "•" }} {{ Math.abs(trend) }}%</span>
      </div>
    </template>
  </button>
</template>

<script setup>
import { computed } from "vue";
import Icon from "./Icon.vue";
import { colorHex } from "@/lib/status";

const props = defineProps({
  title: String,
  value: [String, Number],
  sub: String,
  icon: String,
  accent: { type: String, default: "blue" }, // color key
  trend: { type: Number, default: null },
  clickable: { type: Boolean, default: false },
  loading: Boolean,
});

const accentHex = computed(() => colorHex(props.accent));
const trendStyle = computed(() => {
  const hex = props.trend >= 0 ? "#10b981" : "#ef4444";
  return { background: `${hex}26`, color: hex };
});
</script>
