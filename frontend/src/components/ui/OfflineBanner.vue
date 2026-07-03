<template>
  <transition name="offline">
    <div
      v-if="show"
      class="fixed top-3 left-1/2 -translate-x-1/2 z-[150] flex items-center gap-2 px-3.5 py-2 rounded-lg bg-stone-900 text-white text-[12.5px] font-medium shadow-floating"
    >
      <span class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
      {{ t("common.reconnecting", "Reconnecting…") }}
      <span v-if="queued > 0" class="text-white/70 tabular-nums">· {{ queued }} {{ t("common.queued", "queued") }}</span>
    </div>
  </transition>
</template>

<script setup>
import { useI18n } from "@/composables/useI18n";

defineProps({
  show: { type: Boolean, default: false },
  queued: { type: Number, default: 0 },
});

const { t } = useI18n();
</script>

<style scoped>
.offline-enter-from, .offline-leave-to { opacity: 0; transform: translate(-50%, -8px); }
.offline-enter-active, .offline-leave-active { transition: all 0.2s ease; }
</style>
