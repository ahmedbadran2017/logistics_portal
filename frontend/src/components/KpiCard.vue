<template>
  <div
    class="bg-white rounded-xl border border-stone-200/70 p-4 shadow-[0_1px_3px_rgba(0,0,0,0.02)] transition-all duration-200 relative overflow-hidden group"
    :class="clickable ? 'cursor-pointer hover:border-stone-300 hover:shadow-[0_4px_20px_-6px_rgba(0,0,0,0.06)] hover:-translate-y-0.5' : ''"
  >
    <!-- Tone strip -->
    <div class="absolute top-0 left-0 right-0 h-[3px]" :class="stripClass" />

    <div class="flex items-start justify-between gap-2">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-500">
          <span>{{ label }}</span>
          <span v-if="pulse" class="w-1.5 h-1.5 rounded-full animate-pulse" :class="pulseClass" />
        </div>
        <div class="text-[24px] font-semibold tabular-nums tracking-[-0.02em] mt-1 leading-none" :class="valueClass">
          <CountUp v-if="useCountUp" :value="numericValue" :decimals="decimals" :prefix="prefix" :suffix="suffix" />
          <template v-else>{{ value }}</template>
        </div>
        <div v-if="sub" class="text-[11px] text-stone-400 mt-1.5">{{ sub }}</div>
      </div>
      <div v-if="icon" class="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center" :class="iconBg">
        <Icon :name="icon" :size="18" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "./Icon.vue";
import CountUp from "./CountUp.vue";

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: "—" },
  sub: { type: String, default: "" },
  icon: { type: String, default: "" },
  tone: { type: String, default: "neutral" }, // neutral | emerald | amber | rose | sky | violet | accent
  pulse: { type: Boolean, default: false },
  clickable: { type: Boolean, default: false },
  animated: { type: Boolean, default: true },
  // For animated value with formatting
  numericValue: { type: Number, default: 0 },
  decimals: { type: Number, default: 0 },
  prefix: { type: String, default: "" },
  suffix: { type: String, default: "" },
});

// Use CountUp whenever a numeric value is provided via :numeric-value (even 0),
// or when :value itself is a parseable number.
const useCountUp = computed(() => {
  if (!props.animated) return false;
  if (typeof props.numericValue === "number" && !isNaN(props.numericValue)) return true;
  if (typeof props.value === "number" && !isNaN(props.value)) return true;
  if (typeof props.value === "string" && !isNaN(Number(props.value.replace(/[,_\s]/g, "")))) return true;
  return false;
});

const valueClass = computed(() => ({
  neutral: "text-stone-900",
  emerald: "text-emerald-700",
  amber:   "text-amber-700",
  rose:    "text-rose-700",
  sky:     "text-sky-700",
  violet:  "text-violet-700",
  accent:  "text-[var(--yol-v2-accent-700)]",
}[props.tone] || "text-stone-900"));

const stripClass = computed(() => ({
  neutral: "bg-stone-300",
  emerald: "bg-emerald-500",
  amber:   "bg-amber-500",
  rose:    "bg-rose-500",
  sky:     "bg-sky-500",
  violet:  "bg-violet-500",
  accent:  "bg-[var(--yol-v2-accent-500)]",
}[props.tone] || "bg-stone-300"));

const pulseClass = computed(() => ({
  neutral: "bg-stone-500",
  emerald: "bg-emerald-500",
  amber:   "bg-amber-500",
  rose:    "bg-rose-500",
  sky:     "bg-sky-500",
  violet:  "bg-violet-500",
  accent:  "bg-[var(--yol-v2-accent-500)]",
}[props.tone] || "bg-amber-500"));

const iconBg = computed(() => ({
  neutral: "bg-stone-100 text-stone-600",
  emerald: "bg-emerald-50 text-emerald-700",
  amber:   "bg-amber-50 text-amber-700",
  rose:    "bg-rose-50 text-rose-700",
  sky:     "bg-sky-50 text-sky-700",
  violet:  "bg-violet-50 text-violet-700",
  accent:  "bg-[var(--yol-v2-accent-50)] text-[var(--yol-v2-accent-700)]",
}[props.tone] || "bg-stone-100 text-stone-600"));
</script>
