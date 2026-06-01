<template>
  <span
    class="relative inline-flex"
    @mouseenter="show = true"
    @mouseleave="show = false"
    @focusin="show = true"
    @focusout="show = false"
  >
    <slot />
    <transition name="tip">
      <span
        v-if="show && text"
        :id="tipId"
        role="tooltip"
        class="absolute z-50 px-2 py-1 rounded-md bg-stone-900 text-white text-[11px] font-medium whitespace-nowrap pointer-events-none shadow-lg"
        :class="positionClass"
      >
        {{ text }}
        <span class="absolute w-2 h-2 bg-stone-900 rotate-45" :class="arrowClass" />
      </span>
    </transition>
  </span>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  text: { type: String, default: "" },
  position: { type: String, default: "top" }, // top | bottom | left | right
});

const show = ref(false);
const tipId = `tip-${Math.random().toString(36).slice(2, 8)}`;

const positionClass = computed(() => ({
  top:    "bottom-full mb-1.5 left-1/2 -translate-x-1/2",
  bottom: "top-full mt-1.5 left-1/2 -translate-x-1/2",
  left:   "right-full mr-1.5 top-1/2 -translate-y-1/2",
  right:  "left-full ml-1.5 top-1/2 -translate-y-1/2",
}[props.position]));

const arrowClass = computed(() => ({
  top:    "bottom-[-3px] left-1/2 -translate-x-1/2",
  bottom: "top-[-3px] left-1/2 -translate-x-1/2",
  left:   "right-[-3px] top-1/2 -translate-y-1/2",
  right:  "left-[-3px] top-1/2 -translate-y-1/2",
}[props.position]));
</script>

<style scoped>
.tip-enter-active, .tip-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.tip-enter-from { opacity: 0; transform: translateY(2px) translateX(var(--tw-translate-x, 0)); }
.tip-leave-to { opacity: 0; }
</style>
