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
        class="w-full bg-transparent py-5 ps-14 pe-4 text-lg font-semibold text-content
               placeholder:text-content-4 focus:outline-none"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        @keydown.enter.prevent="submit"
      />
    </div>
    <div class="mt-2 min-h-[20px] text-sm font-medium flex items-center gap-1.5" :style="{ color: feedbackHex }">
      <Icon v-if="feedback" :name="feedbackIcon" :size="16" />
      <span>{{ feedback }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
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

onMounted(() => props.autofocus && refocus());
defineExpose({ showSuccess, showError, refocus });
</script>
