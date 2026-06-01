<template>
  <router-link
    :to="to"
    class="relative flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 group"
    :class="[
      isActive
        ? 'bg-[var(--yol-v2-accent-50)] text-[var(--yol-v2-accent-700)] shadow-sm'
        : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900',
    ]"
    :title="collapsed ? label : ''"
  >
    <!-- Active indicator pill on the left edge -->
    <span
      v-if="isActive"
      class="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-[var(--yol-v2-accent-600)]"
    />
    <Icon :name="icon" :size="16" class="shrink-0 transition-transform group-hover:scale-110" />
    <span v-if="!collapsed" class="flex-1 truncate">{{ label }}</span>

    <!-- Live count badge -->
    <span
      v-if="!collapsed && count > 0"
      class="text-[10px] font-bold px-1.5 py-0.5 rounded-md tabular-nums"
      :class="countCls"
    >{{ count }}</span>

    <!-- Static tag badge (e.g., PLAN) -->
    <span
      v-if="!collapsed && badge && count <= 0"
      class="text-[9.5px] font-bold px-1.5 py-0.5 rounded bg-[var(--yol-v2-accent-100)] text-[var(--yol-v2-accent-700)] uppercase tracking-wider"
    >{{ badge }}</span>

    <!-- Mini dot indicator when collapsed -->
    <span
      v-if="collapsed && count > 0"
      class="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full"
      :class="dotCls"
    />
  </router-link>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/Icon.vue";

const props = defineProps({
  to: { type: String, required: true },
  label: { type: String, required: true },
  icon: { type: String, default: "circle" },
  badge: { type: String, default: "" },
  badgeTone: { type: String, default: "amber" },
  count: { type: Number, default: 0 },
  collapsed: Boolean,
});

const route = useRoute();
const isActive = computed(() => {
  if (props.to === "/logistics") return route.path === "/logistics" || route.path === "/logistics/";
  // Light up "/stock" also for "/stock/anything-deeper" so child routes don't dim the parent.
  return route.path === props.to || route.path.startsWith(props.to + "/");
});

const countCls = computed(() => ({
  rose:   "bg-rose-100 text-rose-700",
  amber:  "bg-amber-100 text-amber-800",
  sky:    "bg-sky-100 text-sky-700",
  emerald:"bg-emerald-100 text-emerald-700",
  violet: "bg-violet-100 text-violet-700",
}[props.badgeTone] || "bg-stone-100 text-stone-700"));

const dotCls = computed(() => ({
  rose:   "bg-rose-500",
  amber:  "bg-amber-500",
  sky:    "bg-sky-500",
  emerald:"bg-emerald-500",
  violet: "bg-violet-500",
}[props.badgeTone] || "bg-stone-500"));
</script>
