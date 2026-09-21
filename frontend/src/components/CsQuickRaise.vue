<template>
  <!-- The same sheet, from the same icon, on every screen. It knows which
       order the page underneath is showing; when the page is a list and
       there is nothing to know, the agent types the number or files the
       complaint against the customer's phone alone. Neither case is a dead
       end — before this, the only doors were two buried panels on two of
       eight surfaces, and in four days humans filed nothing through them. -->
  <Transition name="csq">
    <div v-if="open" class="fixed inset-0 z-[70]" @keydown.esc="$emit('close')">
      <div class="absolute inset-0 bg-stone-900/20" @click="$emit('close')" />
      <div class="absolute top-[58px] end-3 w-[min(420px,calc(100vw-24px))]
                  bg-white rounded-2xl shadow-floating ring-1 ring-stone-200/70 p-3.5 space-y-3">
        <div class="flex items-center gap-2">
          <span class="w-7 h-7 rounded-lg bg-violet-50 text-violet-700 flex items-center justify-center">
            <Icon name="message-circle" :size="14" />
          </span>
          <h3 class="text-[13px] font-bold text-stone-900">{{ t('cs.quickTitle') }}</h3>
          <button class="ms-auto w-7 h-7 rounded-lg hover:bg-stone-100 flex items-center justify-center"
                  :aria-label="t('common.close')" @click="$emit('close')">
            <Icon name="x" :size="14" />
          </button>
        </div>

        <!-- What this is about. Shown, not assumed. -->
        <div v-if="csContext.order" class="rounded-xl bg-stone-50 ring-1 ring-stone-200/70 px-3 py-2">
          <div class="flex items-center gap-2">
            <span class="font-mono text-[12px] font-semibold text-stone-800" dir="ltr">{{ csContext.order }}</span>
            <span v-if="csContext.customer" class="text-[11.5px] text-stone-500 truncate" dir="auto">{{ csContext.customer }}</span>
          </div>
        </div>
        <input v-else v-model="typed" :placeholder="t('cs.quickOrderPh')" dir="ltr"
               class="w-full h-9 px-3 rounded-lg bg-white ring-1 ring-stone-200 font-mono text-[12.5px] focus:outline-none" />

        <CsHandover :order="csContext.order || typed.trim()"
                    :phone="csContext.phone" :live="live"
                    @done="$emit('close')" />
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import CsHandover from "@/components/CsHandover.vue";
import { api } from "@/lib/resource";
import { useCsContext } from "@/composables/useCsContext";
import { useI18n } from "@/composables/useI18n";

const props = defineProps({ open: { type: Boolean, default: false } });
defineEmits(["close"]);
const { t } = useI18n();
const { csContext } = useCsContext();
const typed = ref("");
const live = ref(0);

// Only when it opens, and only when there is an order to ask about: the
// point is to warn "this is already reported" before a second ticket is
// filed, not to poll the desk from every screen in the portal.
watch(() => props.open, async (v) => {
  live.value = 0;
  if (!v || !csContext.value.order) return;
  try {
    const r = await api("cs.for_order", { order: csContext.value.order });
    live.value = r.live || 0;
  } catch (_) { /* the sheet still works without the count */ }
});
</script>

<style scoped>
.csq-enter-active, .csq-leave-active { transition: opacity .14s ease; }
.csq-enter-from, .csq-leave-to { opacity: 0; }
</style>
