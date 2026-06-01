<template>
  <Teleport to="body">
    <div class="fixed top-5 right-5 z-[100] flex flex-col gap-2 max-w-[400px] w-[calc(100vw-40px)] sm:w-auto pointer-events-none">
      <transition-group name="toast" tag="div" class="flex flex-col gap-2" appear>
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto rounded-xl border shadow-lg backdrop-blur-md flex items-start gap-2.5 p-3"
          :class="tone(t.type)"
          :role="t.type === 'error' ? 'alert' : 'status'"
          :aria-live="t.type === 'error' ? 'assertive' : 'polite'"
        >
          <div class="shrink-0 mt-0.5">
            <Icon :name="iconFor(t.type)" :size="16" />
          </div>
          <div class="flex-1 min-w-0">
            <div v-if="t.title" class="text-[12.5px] font-semibold leading-tight">{{ t.title }}</div>
            <!-- Plain text message — no v-html, no XSS surface (fixes audit M6). -->
            <div v-if="t.message" class="text-[12px] mt-0.5 leading-relaxed whitespace-pre-line break-words">{{ t.message }}</div>
            <!-- Optional structured links shown safely. -->
            <div v-if="t.links && t.links.length" class="flex flex-wrap gap-x-3 gap-y-1 mt-1.5">
              <a
                v-for="(l, i) in t.links"
                :key="i"
                :href="l.href"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[11.5px] font-mono underline underline-offset-2 hover:opacity-80 break-all"
              >{{ l.label }}</a>
            </div>
            <div v-if="t.actions && t.actions.length" class="flex gap-2 mt-2">
              <button
                v-for="(a, i) in t.actions"
                :key="i"
                @click="handleAction(t, a)"
                class="text-[11.5px] font-semibold underline underline-offset-2 hover:opacity-80"
              >{{ a.label }}</button>
            </div>
          </div>
          <button
            @click="dismiss(t.id)"
            class="shrink-0 opacity-50 hover:opacity-100 transition-opacity"
            aria-label="Dismiss"
          >
            <Icon name="x" :size="14" />
          </button>
        </div>
      </transition-group>
    </div>
  </Teleport>
</template>

<script setup>
import { toasts, useToast } from "@/composables/useToast";
import Icon from "./Icon.vue";

const { dismiss } = useToast();

function iconFor(type) {
  return {
    success: "check-circle",
    error: "alert-circle",
    warning: "alert-triangle",
    info: "info",
  }[type] || "info";
}
function tone(type) {
  return {
    success: "bg-emerald-50/95 text-emerald-900 border-emerald-200",
    error:   "bg-rose-50/95 text-rose-900 border-rose-200",
    warning: "bg-amber-50/95 text-amber-900 border-amber-200",
    info:    "bg-sky-50/95 text-sky-900 border-sky-200",
  }[type] || "bg-stone-50/95 text-stone-900 border-stone-200";
}
function handleAction(t, a) {
  if (a.onClick) a.onClick();
  if (a.dismissOnClick !== false) dismiss(t.id);
}
</script>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all 0.25s cubic-bezier(0.2, 0.9, 0.3, 1); }
.toast-enter-from { opacity: 0; transform: translateX(40px); }
.toast-leave-to { opacity: 0; transform: translateX(40px); }
.toast-move { transition: transform 0.2s ease; }
</style>
