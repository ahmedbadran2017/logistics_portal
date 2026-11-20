<template>
  <!-- Scan the barcode printed on the box (souk buy, 2026-11-20). The phone's
       own BarcodeDetector (Chrome on Android) reads the camera; where it is
       missing (iPhone Safari) or the camera is refused, the buyer types the
       digits printed under the bars — always offered at the foot. Emits
       `code` once and closes. -->
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[80] bg-stone-950 flex flex-col text-white" role="dialog" aria-modal="true" :aria-label="t('souk.scan.title')">
      <div class="flex items-center gap-2 px-4 pt-[max(12px,env(safe-area-inset-top))] pb-3">
        <h2 class="flex-1 text-[16px] font-bold">{{ t('souk.scan.title') }}</h2>
        <button type="button" class="w-11 h-11 rounded-full bg-white/10 inline-flex items-center justify-center" :aria-label="t('souk.scan.close')" @click="close">
          <Icon name="x" :size="20" />
        </button>
      </div>

      <div class="flex-1 min-h-0 flex flex-col items-center justify-center px-4 gap-3">
        <div v-if="live" class="relative w-full max-w-[520px] aspect-[3/4] sm:aspect-video rounded-2xl overflow-hidden bg-black">
          <video ref="videoEl" class="absolute inset-0 w-full h-full object-cover" playsinline muted autoplay />
          <!-- the aiming frame: a wide band, as barcodes are -->
          <div class="absolute inset-x-[8%] top-1/2 -translate-y-1/2 h-[30%] rounded-xl ring-2 ring-white/90 shadow-[0_0_0_9999px_rgba(0,0,0,.35)]" />
          <div class="absolute inset-x-[10%] top-1/2 h-0.5 bg-rose-500/80 animate-pulse" />
        </div>
        <p class="text-[14px] text-white/85 text-center max-w-[420px] leading-normal">
          {{ live ? t('souk.scan.aim') : problem === 'denied' ? t('souk.scan.denied') : t('souk.scan.noCamera') }}
        </p>
      </div>

      <form class="px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-3 flex gap-2 max-w-[560px] w-full mx-auto" @submit.prevent="typed">
        <label class="sr-only" for="bs-digits">{{ t('souk.scan.typePh') }}</label>
        <input id="bs-digits" ref="inputEl" v-model="digits" dir="ltr" inputmode="numeric" autocomplete="off" :placeholder="t('souk.scan.typePh')"
               class="flex-1 min-w-0 h-12 rounded-xl bg-white text-stone-900 px-3 text-[17px] tracking-wider" />
        <button type="submit" class="shrink-0 h-12 px-5 rounded-xl bg-white text-stone-900 text-[15px] font-bold disabled:opacity-40"
                :disabled="clean(digits).length < 6">{{ t('souk.scan.find') }}</button>
      </form>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useI18n } from "@/composables/useI18n";

const props = defineProps({ open: Boolean });
const emit = defineEmits(["update:open", "code"]);
const { t } = useI18n();

const videoEl = ref(null);
const inputEl = ref(null);
const live = ref(false);
const problem = ref("");
const digits = ref("");
let stream = null;
let timer = null;
let busy = false;

const WANT = ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39", "itf"];
const clean = (s) => String(s || "").replace(/\s+/g, "");

function stop() {
  clearInterval(timer);
  timer = null;
  if (stream) for (const tr of stream.getTracks()) tr.stop();
  stream = null;
  live.value = false;
}
function close() {
  stop();
  emit("update:open", false);
}
function done(code) {
  try { navigator.vibrate && navigator.vibrate(60); } catch (_) { /* no vibration */ }
  emit("code", code);
  close();
}
function typed() {
  const c = clean(digits.value);
  if (c.length >= 6) done(c);
}

async function start() {
  digits.value = "";
  problem.value = "";
  const BD = window.BarcodeDetector;
  if (!BD || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    problem.value = "unsupported";
    await nextTick();
    inputEl.value && inputEl.value.focus();
    return;
  }
  let formats = WANT;
  try {
    const have = await BD.getSupportedFormats();
    formats = WANT.filter((f) => have.includes(f));
  } catch (_) { /* keep the list */ }
  if (!formats.length) { problem.value = "unsupported"; return; }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false,
    });
  } catch (e) {
    problem.value = e && e.name === "NotAllowedError" ? "denied" : "unsupported";
    return;
  }
  if (!props.open) { stop(); return; }
  live.value = true;
  await nextTick();
  const v = videoEl.value;
  if (!v) { stop(); return; }
  v.srcObject = stream;
  try { await v.play(); } catch (_) { /* autoplay muted plays anyway */ }
  const det = new BD({ formats });
  timer = setInterval(async () => {
    if (busy || !v.videoWidth) return;
    busy = true;
    try {
      const found = await det.detect(v);
      const c = found && found[0] && clean(found[0].rawValue);
      if (c && c.length >= 6) done(c);
    } catch (_) { /* a frame it could not read */ } finally {
      busy = false;
    }
  }, 200);
}

watch(() => props.open, (o) => { if (o) start(); else stop(); }, { immediate: true });
onBeforeUnmount(stop);
</script>
