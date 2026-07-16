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
        @keydown="onKeydown"
        @input="onInput"
        @compositionend="onInput"
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

    <!-- ?scandebug=1 — what the device is actually sending. There is no
         console to open on a PDA. -->
    <div v-if="debug" class="mt-2 rounded-lg bg-stone-900 text-stone-100 p-2.5 font-mono text-[10.5px] leading-relaxed">
      <div class="flex items-center justify-between mb-1.5 text-stone-400">
        <span>scan debug · {{ log.length }} events</span>
        <button type="button" class="underline" tabindex="-1" @click.prevent="log = []">clear</button>
      </div>
      <div v-if="!log.length" class="text-stone-500">Scan once — every raw event lands here.</div>
      <div v-for="(l, i) in log" :key="i" class="whitespace-pre-wrap break-all">{{ l }}</div>
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

// Scanner diagnostics: open any scanning screen with ?scandebug=1 and every
// raw event the device produces is listed under the field. On a PDA there is
// no console to open, and what the wedge actually sends is the whole question.
const debug = ref(false);
const log = ref([]);
function logEvent(type, detail) {
  if (!debug.value) return;
  const t = new Date().toISOString().slice(14, 23);
  log.value.unshift(`${t}  ${type.padEnd(15)} ${detail}`);
  if (log.value.length > 14) log.value.pop();
}

// Warehouse-standard focus recovery: an incidental tap anywhere kills focus
// silently and the next wedge scan types into the void. Any printable key
// pressed while no editable element has focus is routed back to this input.
// NB: this can only ever help the key-event path. A PDA that commits text
// through the InputConnection needs the field focused to receive anything at
// all, which is what refocus() is for.
function captureKeys(e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.isComposing || e.keyCode === 229) return;
  const el = document.activeElement;
  if (el === field.value) return;
  const editable = el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA"
    || el.tagName === "SELECT" || el.isContentEditable);
  if (editable) return;
  if (e.key === "Enter" || e.keyCode === 13) {
    // A scan finished while we were unfocused — submit whatever buffered.
    if (value.value.trim()) { e.preventDefault(); submit(); }
    return;
  }
  if (e.key && e.key.length === 1) {
    sawRealKeys = true;
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

// ── Wedge input, without assuming key events ─────────────────────────────
// The Zebra PDAs deliver a scan through DataWedge's Keystroke output, and its
// default is NOT what this component used to assume:
//
//   "Send Characters as Events"  — OFF by default. The barcode's printable
//     characters (ASCII 32-126) are committed as a STRING through Android's
//     InputConnection, not injected as key events. The field fills; no keydown
//     ever fires.
//   "Action key character"       — None / Tab / Line feed / Carriage return.
//     On None, no terminator is sent at all, so nothing ever says "scan over".
//
// On top of that, anything routed through an Android IME reports keydown as
// key="Unidentified", keyCode=229 — so `@keydown.enter` cannot match, and
// Vue's v-model suppresses model updates while a composition is open, leaving
// the ref empty while the field visibly holds the scan.
//
// Reproduced in the browser against this component: real key events submit;
// keyCode-229 keys and composition-committed text both leave the SKU sitting
// in the field doing nothing — exactly what the floor reported. So: read the
// DOM at submit time (not the composition-guarded ref), accept a terminator in
// any form it may arrive, and fall back to a settle timer when none arrives.
const SETTLE_MS = 140;
let settleTimer = null;
// Did THIS entry come from trusted, printable key events (a person typing, or
// a USB wedge on the laptop)? If so it keeps the old contract: Enter submits,
// nothing auto-fires. The settle fallback is only for input that arrived with
// no usable key events — i.e. the PDA path.
let sawRealKeys = false;

function armSettle() {
  clearTimeout(settleTimer);
  settleTimer = setTimeout(() => {
    if (!sawRealKeys) submit();
  }, SETTLE_MS);
}

function onKeydown(e) {
  logEvent("keydown", `key=${e.key} code=${e.keyCode} composing=${e.isComposing}`);
  // IME noise: no information about which key this was.
  if (e.isComposing || e.keyCode === 229) return;
  if (e.key && e.key.length === 1) sawRealKeys = true;
  if (e.key === "Enter" || e.keyCode === 13 || e.key === "Tab" || e.keyCode === 9) {
    e.preventDefault();
    submit();
  }
}

function onInput(e) {
  logEvent(e.type, `type=${e.inputType || "-"} data=${JSON.stringify(e.data ?? null)}`);
  const el = e.target;
  // An empty field is a new entry: forget how the last one was typed. Without
  // this, someone typing by hand once and NOT pressing Enter leaves sawRealKeys
  // true forever, and every PDA scan after that silently stops auto-firing.
  if (el && !el.value) {
    sawRealKeys = false;
    clearTimeout(settleTimer);
    return;
  }
  // A wedge may send the terminator as a CR/LF character instead of a key.
  if (el && /[\r\n]/.test(el.value)) { submit(); return; }
  if (e.inputType === "insertLineBreak") { submit(); return; }
  armSettle();
}

function submit() {
  clearTimeout(settleTimer);
  // The DOM, never the ref: Vue's v-model skips model updates while an IME
  // composition is open, so `value` can be empty while the field shows the
  // scan. That read is why the SKU appeared and the pick never happened.
  const el = field.value;
  const raw = el ? el.value : value.value;
  const code = String(raw || "").replace(/[\r\n\t]+/g, "").trim();
  sawRealKeys = false;
  if (!code) return;
  emit("scan", code);
  value.value = "";
  if (el) el.value = "";
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
  try {
    debug.value = new URLSearchParams(window.location.search).get("scandebug") === "1";
  } catch (_) { /* no URL access, no debug */ }
  if (props.autofocus) refocus();
  document.addEventListener("keydown", captureKeys, true);
});
onBeforeUnmount(() => {
  clearTimeout(settleTimer);
  document.removeEventListener("keydown", captureKeys, true);
});
defineExpose({ showSuccess, showError, refocus });
</script>
