<template>
  <div class="fixed z-[200] bottom-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 w-[min(92vw,420px)] pointer-events-none">
    <transition-group name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="lp-card p-3.5 pointer-events-auto flex items-start gap-3 shadow-floating animate-toast-in"
        :style="{ borderInlineStartWidth: '4px', borderInlineStartColor: hex(t.severity) }"
      >
        <Icon :name="icon(t.severity)" :size="18" :style="{ color: hex(t.severity) }" class="mt-0.5 shrink-0" />
        <div class="min-w-0 flex-1">
          <div class="font-semibold text-sm text-content">{{ t.title }}</div>
          <div v-if="t.detail" class="text-xs text-content-3 mt-0.5">{{ t.detail }}</div>
          <button v-if="t.action" class="text-xs font-semibold mt-1.5" :style="{ color: hex(t.severity) }"
                  @click="t.action.fn && t.action.fn(); dismiss(t.id)">
            {{ t.action.label }}
          </button>
        </div>
        <button class="text-content-4 hover:text-content-2 shrink-0" @click="dismiss(t.id)">
          <Icon name="x" :size="16" />
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import Icon from "./Icon.vue";
import { useToast } from "@/composables/useToast";
const { toasts, dismiss } = useToast();

const HEX = { critical: "#ef4444", warn: "#f97316", info: "#f59e0b", success: "#10b981" };
const ICON = { critical: "alert-triangle", warn: "alert-triangle", info: "bell", success: "check-circle" };
const hex = (s) => HEX[s] || HEX.info;
const icon = (s) => ICON[s] || ICON.info;
</script>

<style scoped>
.toast-enter-from { opacity: 0; transform: translateY(12px); }
.toast-leave-to { opacity: 0; transform: translateY(8px); }
.toast-enter-active, .toast-leave-active { transition: all 0.2s ease; }
</style>
