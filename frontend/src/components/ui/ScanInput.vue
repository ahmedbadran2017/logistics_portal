<template>
  <div>
    <div
      class="relative rounded-card border-2 transition-colors duration-150 bg-card"
      :class="stateBorder"
      :style="flashStyle"
    >
      <Icon name="scan-barcode" :size="26" class="absolute inset-inline-start-4 top-1/2 -translate-y-1/2 text-content-3" style="inset-inline-start:1rem" />
      <input
        ref="field"
        v-model="value"
        :placeholder="placeholder"
        :inputmode="softKeyboard ? 'text' : 'none'"
        class="w-full bg-transparent py-5 ps-14 pe-4 text-lg font-semibold text-content
               placeholder:text-content-4 focus:outline-none"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        @keydown.enter.prevent="submit"
      />
      <button
        type="button"
        class="absolute top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg flex items-center justify-center text-content-3 hover:text-content"
        style="inset-inline-end:.6rem"
        :title="softKeyboard ? 'Scanner mode' : 'Keyboard'"
        tabindex="-1"
        @click.prevent="softKeyboard = !softKeyboard; refocus()"
      >
        <Icon name="edit" :size="15" />
      </button>
    </div>
    <div class="mt-2 min-h-[20px] text-sm font-medium flex items-center gap-1.5" :style="{ color: feedbackHex }">
      <Icon v-if="feedback" :name="feedbackIcon" :size="16" />
      <span>{{ feedback }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({
  placeholder: { type: String, default: "Scan SKU / parcel" },
  autofocus: { type: Boolean, default: true },
});
const emit = defineEmits(["scan"]);

const field = ref(null);
const value = ref("");
const state = ref("idle"); // idle | success | error | duplicate
const feedback = ref("");
// PDA default: hardware wedge types the code, so suppress the soft keyboard
// (inputmode="none"); the pencil button re-enables it for manual entry.
const softKeyboard = ref(false);

// Warehouse-standard focus recovery: an incidental tap anywhere kills focus
// silently and the next wedge scan types into the void. Any printable key
// pressed while no editable element has focus is routed back to this input.
function captureKeys(e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const el = document.activeElement;
  if (el === field.value) return;
  const editable = el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA"
    || el.tagName === "SELECT" || el.isContentEditable);
  if (editable) return;
  if (e.key === "Enter") {
    // A scan finished while we were unfocused — submit whatever buffered.
    if (value.value.trim()) { e.preventDefault(); submit(); }
    return;
  }
  if (e.key.length === 1) {
    value.value += e.key;
    e.preventDefault();
    refocus();
  }
}

const stateBorder = computed(() => ({
  "border-border": state.value === "idle",
  "border-success animate-success-pulse": state.value === "success",
  "border-danger animate-error-shake": state.value === "error" || state.value === "duplicate",
}));
const flashStyle = computed(() => {
  if (state.value === "success") return { boxShadow: "0 0 20px rgb(16 185 129 / .25)" };
  if (state.value === "error" || state.value === "duplicate") return { boxShadow: "0 0 20px rgb(239 68 68 / .25)" };
  return {};
});
const feedbackHex = computed(() =>
  state.value === "success" ? "#10b981" : state.value === "idle" ? "#64748b" : "#ef4444"
);
const feedbackIcon = computed(() => (state.value === "success" ? "check" : "x"));

function submit() {
  const code = value.value.trim();
  if (!code) return;
  emit("scan", code);
  value.value = "";
  refocus();
}

/** Parent calls these via template ref to drive multi-sensory feedback. */
function showSuccess(msg) {
  state.value = "success";
  feedback.value = msg;
  beep(880);
  vibrate(30);
  setTimeout(() => (state.value = "idle"), 700);
}
function showError(msg) {
  state.value = "error";
  feedback.value = msg;
  beep(220);
  vibrate([40, 40, 40]);
  setTimeout(() => (state.value = "idle"), 900);
}
function refocus() {
  requestAnimationFrame(() => field.value && field.value.focus());
}
function beep(freq) {
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = new AC();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = freq;
    gain.gain.value = 0.05;
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.08);
  } catch (_) { /* audio not available */ }
}
function vibrate(p) {
  if (navigator.vibrate) navigator.vibrate(p);
}

onMounted(() => {
  if (props.autofocus) refocus();
  document.addEventListener("keydown", captureKeys, true);
});
onBeforeUnmount(() => document.removeEventListener("keydown", captureKeys, true));
defineExpose({ showSuccess, showError, refocus });
</script>
