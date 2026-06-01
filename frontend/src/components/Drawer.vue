<template>
  <Teleport to="body">
    <transition name="drawer">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex justify-end"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        @click.self="close"
        @keydown.esc.stop="close"
      >
        <div class="absolute inset-0 bg-stone-900/40 backdrop-blur-sm" />
        <div ref="panel" tabindex="-1" class="relative w-full max-w-[1000px] bg-stone-50 h-full overflow-y-auto shadow-2xl focus:outline-none">
          <div class="sticky top-0 bg-white border-b border-stone-200 px-6 py-3 flex items-center gap-3 z-10">
            <button ref="closeBtn" @click="close" class="btn-secondary" aria-label="Close drawer">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
              Back
            </button>
            <div class="flex-1 min-w-0">
              <h2 :id="titleId" class="text-[18px] font-semibold text-stone-900 truncate">{{ title || 'Detail' }}</h2>
              <div v-if="$slots.meta" class="mt-0.5"><slot name="meta" /></div>
            </div>
          </div>
          <div class="px-6 py-5">
            <slot />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from "vue";

const props = defineProps({
  modelValue: Boolean,
  title: String,
});
const emit = defineEmits(["update:modelValue"]);

const panel = ref(null);
const closeBtn = ref(null);
const titleId = `drawer-title-${Math.random().toString(36).slice(2, 8)}`;
let previouslyFocused = null;

function close() { emit("update:modelValue", false); }

function onKey(e) {
  if (e.key === "Escape") { close(); return; }
  if (e.key !== "Tab" || !panel.value) return;
  // Don't trap when the focused element is outside our panel (e.g., CommandPalette
  // mounted on top via Teleport-to-body) — let that modal handle its own tabbing.
  if (!panel.value.contains(document.activeElement)) return;
  const focusables = panel.value.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  );
  if (!focusables.length) return;
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}

watch(() => props.modelValue, async (open) => {
  if (open) {
    // Only capture on the FIRST open of a session — rapid toggles shouldn't lose the original focus.
    if (!previouslyFocused) previouslyFocused = document.activeElement;
    document.addEventListener("keydown", onKey, true);
    await nextTick();
    closeBtn.value?.focus();
  } else {
    document.removeEventListener("keydown", onKey, true);
    if (previouslyFocused && typeof previouslyFocused.focus === "function") {
      previouslyFocused.focus();
    }
    previouslyFocused = null;
  }
});

onBeforeUnmount(() => document.removeEventListener("keydown", onKey, true));
</script>

<style scoped>
.drawer-enter-active, .drawer-leave-active { transition: opacity 0.2s ease; }
.drawer-enter-active .relative,
.drawer-leave-active .relative { transition: transform 0.32s cubic-bezier(0.16, 1, 0.3, 1); }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-from .relative,
.drawer-leave-to .relative { transform: translateX(100%); }
</style>
