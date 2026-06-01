<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[base, variantClass, sizeClass, fullWidth ? 'w-full' : '', loading ? 'cursor-wait' : '']"
    @click="$emit('click', $event)"
  >
    <span v-if="loading" class="animate-spin">
      <Icon name="loader" :size="size === 'sm' ? 12 : size === 'lg' ? 16 : 14" />
    </span>
    <Icon v-else-if="icon" :name="icon" :size="size === 'sm' ? 12 : size === 'lg' ? 16 : 14" />
    <slot />
  </button>
</template>

<script setup>
import { computed } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
  variant: { type: String, default: "secondary" }, // primary | secondary | brand | ghost | danger | success
  size: { type: String, default: "md" }, // sm | md | lg
  type: { type: String, default: "button" },
  icon: { type: String, default: "" },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  fullWidth: { type: Boolean, default: false },
});

defineEmits(["click"]);

const base = "inline-flex items-center justify-center gap-1.5 font-medium rounded-lg transition-all duration-150 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-1";

const variantClass = computed(() => ({
  primary:   "bg-stone-900 text-white hover:bg-stone-800 hover:shadow-md shadow-sm focus:ring-stone-700/30",
  secondary: "bg-white text-stone-700 border border-stone-200 hover:bg-stone-50 hover:border-stone-300 hover:shadow-sm focus:ring-stone-400/20",
  brand:     "bg-[var(--yol-v2-accent-600)] text-white hover:bg-[var(--yol-v2-accent-700)] hover:shadow-md shadow-sm focus:ring-[#c4492a]/30",
  ghost:     "bg-transparent text-stone-700 hover:bg-stone-100 focus:ring-stone-400/20",
  danger:    "bg-rose-600 text-white hover:bg-rose-700 hover:shadow-md shadow-sm focus:ring-rose-500/30",
  success:   "bg-emerald-600 text-white hover:bg-emerald-700 hover:shadow-md shadow-sm focus:ring-emerald-500/30",
}[props.variant] || ""));

const sizeClass = computed(() => ({
  sm: "h-7 px-2.5 text-[12px]",
  md: "h-8 px-3 text-[13px]",
  lg: "h-10 px-4 text-[14px]",
}[props.size] || ""));
</script>
