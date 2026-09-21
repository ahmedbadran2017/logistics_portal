<template>
  <!-- ONE line, from anywhere. The order, the customer, the lane and who
       sent it are all taken from where the button was pressed.

       The six type buttons above this box were mandatory until 2026-09-21,
       and in the four days the button existed humans raised ZERO requests
       while the AI raised 640. Six buttons standing between an agent on a
       live call and one sentence about a customer's problem is not a form,
       it is a wall. The server guesses the type from the words; the desk
       retypes it in one tap with a button it already has. -->
  <div class="rounded-xl bg-violet-50/70 ring-1 ring-violet-200 p-2.5 space-y-2">
    <div class="flex items-center gap-2">
      <Icon name="message-circle" :size="13" class="text-violet-600 shrink-0" />
      <span class="text-[11px] font-semibold text-violet-800">{{ t('cs.handTitle') }}</span>
      <span v-if="live" class="ms-auto text-[10.5px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-full px-2 py-0.5">
        {{ t('cs.handAlready').replace('{n}', String(live)) }}
      </span>
    </div>
    <div class="flex items-center gap-2">
      <input v-model="note" :placeholder="t('cs.handPh')" maxlength="300"
             class="flex-1 h-9 px-3 rounded-lg bg-white ring-1 ring-violet-200 text-[12.5px] focus:outline-none"
             @keyup.enter="send" />
      <button class="h-9 px-4 rounded-lg text-[12px] font-bold text-white bg-violet-700 hover:bg-violet-800 disabled:opacity-40"
              :disabled="!note.trim() || busy" @click="send">{{ busy ? '…' : t('cs.handSend') }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const props = defineProps({
  order: { type: String, default: "" },
  phone: { type: String, default: "" },
  source: { type: String, default: "" },
  // How many requests are already open on this order. Shown so the second
  // person to notice the same late parcel knows it is already reported,
  // rather than raising it again and splitting the thread.
  live: { type: Number, default: 0 },
});
const emit = defineEmits(["done"]);
const { t } = useI18n();
const { success, warn } = useToast();

const note = ref("");
const busy = ref(false);

async function send() {
  const text = note.value.trim();
  if (!text) return;
  busy.value = true;
  try {
    const r = await apiPost("cs.raise_request", {
      note: text, order: props.order, phone: props.phone, source: props.source,
    });
    // Say when it merged rather than inventing a second request: two agents
    // noticing the same late parcel is one problem, not two.
    success(r.merged ? t("cs.handMerged") : t("cs.handOk"), r.request || "");
    note.value = "";
    emit("done", r);
  } catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
  finally { busy.value = false; }
}
</script>
