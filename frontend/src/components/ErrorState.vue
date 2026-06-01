<template>
  <div class="py-16 px-8 text-center animate-fade-in-up">
    <div class="w-14 h-14 mx-auto rounded-2xl bg-rose-50 flex items-center justify-center text-rose-600 mb-4">
      <Icon name="alert-triangle" :size="22" />
    </div>
    <p class="text-[14px] font-medium text-stone-900">{{ title }}</p>
    <p v-if="message" class="text-[12.5px] text-stone-500 mt-1 max-w-md mx-auto">{{ message }}</p>
    <Button v-if="onRetry" variant="secondary" icon="refresh-cw" class="mt-4" @click="onRetry">Retry</Button>
  </div>
</template>

<script setup>
import Icon from "./Icon.vue";
import Button from "./Button.vue";

defineProps({
  title: { type: String, default: "Something went wrong" },
  message: { type: String, default: "" },
  onRetry: { type: Function, default: null },
});
</script>
