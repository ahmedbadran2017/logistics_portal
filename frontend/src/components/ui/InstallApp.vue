<template>
  <!-- Already installed, or a desktop with a mouse: nothing to offer. -->
  <div v-if="show" class="p-2 border-t border-stone-100">
    <button
      v-if="prompt"
      type="button"
      class="w-full h-11 rounded-lg text-[13px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] transition-colors inline-flex items-center justify-center gap-1.5"
      @click="install"
    >
      <Icon name="download" :size="15" />{{ t("install.btn") }}
    </button>

    <!-- No prompt on offer. Chrome only fires beforeinstallprompt when a
         service worker with a fetch handler is present, and this app has none
         — so say how to do it by hand rather than show a button that lies. -->
    <div v-else class="rounded-lg bg-stone-50 ring-1 ring-stone-200/70 p-2.5">
      <div class="flex items-start gap-2">
        <Icon name="download" :size="14" class="text-stone-400 mt-0.5 flex-shrink-0" />
        <div class="min-w-0">
          <div class="text-[12px] font-semibold text-stone-800">{{ t("install.title") }}</div>
          <div class="text-[11px] text-stone-500 leading-snug mt-0.5">{{ t("install.how") }}</div>
        </div>
      </div>
      <button
        type="button"
        class="mt-1.5 text-[11px] font-medium text-stone-400 hover:text-stone-700"
        @click="dismiss"
      >{{ t("install.dismiss") }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import Icon from "./Icon.vue";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const KEY = "lp.installHidden";

const prompt = ref(null);      // the deferred beforeinstallprompt event, if it comes
const dismissed = ref(false);
const installed = ref(false);
const touch = ref(false);

// Only worth showing on the devices this is for: a touch screen, not already
// running as an installed app, not dismissed.
const show = computed(() => touch.value && !installed.value && !dismissed.value);

function onPrompt(e) {
  e.preventDefault();          // keep it; fire it from our own button
  prompt.value = e;
}
function onInstalled() {
  installed.value = true;
  prompt.value = null;
}
async function install() {
  const e = prompt.value;
  if (!e) return;
  prompt.value = null;
  e.prompt();
  await e.userChoice;
}
function dismiss() {
  dismissed.value = true;
  try { localStorage.setItem(KEY, "1"); } catch (_) { /* private mode */ }
}

onMounted(() => {
  try {
    touch.value = window.matchMedia("(pointer: coarse)").matches;
    installed.value = window.matchMedia("(display-mode: standalone)").matches
      || window.navigator.standalone === true;
    dismissed.value = localStorage.getItem(KEY) === "1";
  } catch (_) { /* no matchMedia / no storage */ }
  window.addEventListener("beforeinstallprompt", onPrompt);
  window.addEventListener("appinstalled", onInstalled);
});
onBeforeUnmount(() => {
  window.removeEventListener("beforeinstallprompt", onPrompt);
  window.removeEventListener("appinstalled", onInstalled);
});
</script>
