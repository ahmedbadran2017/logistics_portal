<template>
  <div class="py-16 px-8 text-center animate-fade-in-up">
    <div class="w-14 h-14 mx-auto rounded-2xl bg-stone-100 flex items-center justify-center text-stone-400 mb-4">
      <slot name="icon">
        <Icon :name="icon" :size="24" />
      </slot>
    </div>
    <p class="text-[14px] font-medium text-stone-900">{{ title }}</p>
    <p v-if="sub" class="text-[12.5px] text-stone-500 mt-1 max-w-md mx-auto">{{ sub }}</p>
    <slot name="action" />
  </div>
</template>

<script setup>
import Icon from "./Icon.vue";

defineProps({
  title: { type: String, default: "Nothing here yet" },
  sub:   { type: String, default: "" },
  icon:  { type: String, default: "search" },
});
</script>
