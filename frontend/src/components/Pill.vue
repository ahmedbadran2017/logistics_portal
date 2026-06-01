<template>
  <span class="badge" :class="cls">
    <span v-if="dot" class="w-1.5 h-1.5 rounded-full" :class="dotCls" />
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  tone: { type: String, default: "gray" }, // gray | green | yellow | red | blue | violet | accent
  label: { type: String, default: "" },
  dot: { type: Boolean, default: false },
});

const cls = computed(() => ({
  gray: "badge-gray",
  green: "badge-green",
  yellow: "badge-yellow",
  red: "badge-red",
  blue: "badge-blue",
  violet: "badge-violet",
  accent: "bg-[var(--yol-v2-accent-50)] text-[var(--yol-v2-accent-700)] ring-1 ring-inset ring-[var(--yol-v2-accent-200)]",
}[props.tone] || "badge-gray"));

const dotCls = computed(() => ({
  gray: "bg-stone-400",
  green: "bg-emerald-500",
  yellow: "bg-amber-500",
  red: "bg-rose-500",
  blue: "bg-sky-500",
  violet: "bg-violet-500",
  accent: "bg-[var(--yol-v2-accent-500)]",
}[props.tone] || "bg-stone-400"));
</script>
