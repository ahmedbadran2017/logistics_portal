<template>
  <!-- Two taps, from anywhere. An agent mid-call will not fill a form —
       that is exactly how the old Issue lane reached eight tickets in a
       year — so the order, the customer, the channel and who sent it are
       all taken from where the button was pressed. -->
  <div class="rounded-xl bg-violet-50/70 ring-1 ring-violet-200 p-2.5 space-y-2">
    <div class="text-[11px] font-semibold text-violet-800">{{ t('cs.handTitle') }}</div>
    <div class="flex flex-wrap gap-1.5">
      <button v-for="k in KINDS" :key="k"
              class="h-9 px-3 rounded-xl text-[12.5px] font-semibold ring-1 transition-all"
              :class="kind === k ? 'text-white bg-violet-600 ring-violet-600'
                                 : 'text-violet-700 bg-white ring-violet-200 hover:bg-violet-100'"
              @click="kind = k">{{ t('cs.k_' + k) }}</button>
    </div>
    <div class="flex items-center gap-2">
      <input v-model="note" :placeholder="t('cs.handPh')" maxlength="300"
             class="flex-1 h-9 px-3 rounded-lg bg-white ring-1 ring-violet-200 text-[12.5px] focus:outline-none"
             @keyup.enter="send" />
      <button class="h-9 px-4 rounded-lg text-[12px] font-bold text-white bg-violet-700 hover:bg-violet-800 disabled:opacity-40"
              :disabled="!kind || busy" @click="send">{{ busy ? '…' : t('cs.handSend') }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const props = defineProps({
  order: { type: String, default: "" },
  phone: { type: String, default: "" },
  source: { type: String, default: "" },
});
const emit = defineEmits(["done"]);
const { t } = useI18n();
const { success, warn } = useToast();

const KINDS = ["stock", "wrong_item", "exchange", "late", "damaged", "refund", "other"];
const kind = ref("");
const note = ref("");
const busy = ref(false);

async function send() {
  if (!kind.value) return;
  busy.value = true;
  try {
    const r = await apiPost("cs.raise_request", {
      kind: kind.value, note: note.value.trim(),
      order: props.order, phone: props.phone, source: props.source,
    });
    // Say when it merged rather than inventing a second request: two agents
    // noticing the same late parcel is one problem, not two.
    success(r.merged ? t("cs.handMerged") : t("cs.handOk"), r.request || "");
    kind.value = ""; note.value = "";
    emit("done", r);
  } catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
  finally { busy.value = false; }
}
</script>
