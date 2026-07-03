<template>
  <div class="flex flex-col items-center justify-center text-center py-14 px-6">
    <div
      class="w-14 h-14 rounded-full flex items-center justify-center mb-4"
      :style="{ background: `${hex}1f`, color: hex }"
    >
      <Icon :name="icon" :size="26" />
    </div>
    <h3 class="text-h3 text-content mb-1">{{ title }}</h3>
    <p v-if="hint" class="text-sm text-content-3 max-w-xs">{{ hint }}</p>
    <button v-if="cta" class="btn-primary mt-5" @click="$emit('cta')">{{ cta }}</button>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "./Icon.vue";
import { colorHex } from "@/lib/status";

const props = defineProps({
  icon: { type: String, default: "check-circle" },
  title: { type: String, default: "All caught up" },
  hint: String,
  cta: String,
  tone: { type: String, default: "green" },
});
defineEmits(["cta"]);
const hex = computed(() => colorHex(props.tone));
</script>
