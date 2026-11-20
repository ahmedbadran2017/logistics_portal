<template>
  <!-- Where the good pieces go (souk receiving, 2026-11-20). Up to three
       suggestions from the server, each with its reason (the item's own
       stock first, then its siblings', then the emptiest bins of the
       new-product zone), and a search over every sellable shelf. -->
  <div class="flex flex-col gap-2">
    <div v-if="modelValue && !editing" class="flex items-center gap-2 rounded-xl st-soft ring-1 ring-inset ring-[rgb(var(--st)/.3)] ps-3 pe-1.5 py-1.5">
      <Icon name="map-pin" :size="16" class="st-fg shrink-0" />
      <div class="flex-1 min-w-0 flex flex-col">
        <span class="text-[16px] font-extrabold st-ink font-mono" dir="ltr" :class="isRTL ? 'text-right' : ''">{{ short(modelValue) }}</span>
        <span v-if="whyOf(modelValue)" class="text-[12px] text-stone-600 truncate">{{ whyOf(modelValue) }}</span>
      </div>
      <button type="button" class="shrink-0 h-11 px-3 rounded-lg bg-white ring-1 ring-inset ring-stone-300 text-[13px] font-semibold" @click="startEdit">{{ t('souk.recv.shelfChange') }}</button>
    </div>

    <template v-else>
      <div v-if="suggest.length" class="flex flex-col gap-1.5">
        <span class="text-[12px] font-bold text-stone-600">{{ t('souk.recv.shelfSuggest') }}</span>
        <button v-for="s in suggest" :key="s.shelf" type="button"
                class="w-full min-h-[52px] rounded-xl bg-white ring-1 ring-inset ring-stone-300 hover:ring-[rgb(var(--st)/.5)] px-3 py-2 flex items-center gap-3 text-start"
                @click="choose(s.shelf)">
          <span class="shrink-0 min-w-[64px] h-9 px-2 rounded-lg st-tint st-ink font-mono font-extrabold text-[15px] inline-flex items-center justify-center" dir="ltr">{{ short(s.shelf) }}</span>
          <span class="flex-1 min-w-0 text-[13px] text-stone-700 leading-snug">{{ reason(s) }}</span>
        </button>
      </div>

      <div class="relative">
        <label class="sr-only" for="sp-q">{{ t('souk.recv.shelfSearchPh') }}</label>
        <Icon name="search" :size="16" class="absolute top-1/2 -translate-y-1/2 start-3 text-stone-400 pointer-events-none" />
        <input id="sp-q" ref="qEl" v-model="q" dir="ltr" autocomplete="off" autocapitalize="characters" :placeholder="t('souk.recv.shelfSearchPh')"
               class="w-full h-11 rounded-lg ring-1 ring-inset bg-white ps-9 pe-3 text-[16px] font-mono uppercase placeholder:normal-case placeholder:font-sans"
               :class="[invalid ? 'ring-amber-400' : 'ring-stone-300', isRTL ? 'text-right' : '']" />
      </div>
      <div v-if="q" class="flex flex-wrap gap-1.5">
        <button v-for="w in hits" :key="w" type="button"
                class="h-11 ps-3 pe-2.5 rounded-lg bg-white ring-1 ring-inset ring-stone-300 inline-flex items-center gap-2"
                @click="choose(w)">
          <span class="font-mono font-bold text-[14px]" dir="ltr">{{ short(w) }}</span>
          <span class="text-[11px] text-stone-500">{{ fill[w] ? tt('souk.recv.shelfSkus', { n: fill[w] }) : t('souk.recv.shelfEmpty') }}</span>
        </button>
        <span v-if="!hits.length" class="text-[13px] text-stone-600">{{ tt('souk.recv.shelfNone', { q }) }}</span>
      </div>
      <button v-if="editing && modelValue" type="button" class="self-start h-9 text-[13px] font-semibold text-stone-600 underline underline-offset-2" @click="editing = false">{{ t('souk.recv.shelfKeep') }}</button>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useI18n } from "@/composables/useI18n";

const props = defineProps({
  modelValue: { type: String, default: "" },
  shelves: { type: Array, default: () => [] },
  suggest: { type: Array, default: () => [] },
  fill: { type: Object, default: () => ({}) },
  zone: { type: String, default: "B" },
  invalid: Boolean,
});
const emit = defineEmits(["update:modelValue"]);
const { t, isRTL } = useI18n();
const tt = (k, o) => Object.entries(o || {}).reduce((s, [a, b]) => s.split(`{${a}}`).join(String(b)), t(k));

const q = ref("");
const qEl = ref(null);
const editing = ref(false);

const short = (w) => String(w || "").replace(/ - JM$/, "");
// "h3b", "H3B.", "h 3 b" all find "H3B - JM"
const key = (s) => String(s || "").toUpperCase().replace(/ - JM$/, "").replace(/[\s.]/g, "");
const hits = computed(() => {
  const k = key(q.value);
  if (!k) return [];
  const starts = [], inside = [];
  for (const w of props.shelves) {
    const n = key(w);
    if (n.startsWith(k)) starts.push(w);
    else if (n.includes(k)) inside.push(w);
  }
  return [...starts, ...inside].slice(0, 12);
});

function reason(s) {
  return tt("souk.recv.why_" + s.why, { n: s.n, z: props.zone });
}
function whyOf(w) {
  const s = props.suggest.find((x) => x.shelf === w);
  return s ? reason(s) : props.fill[w] ? tt("souk.recv.shelfSkus", { n: props.fill[w] }) : t("souk.recv.shelfEmpty");
}
function choose(w) {
  emit("update:modelValue", w);
  q.value = "";
  editing.value = false;
}
async function startEdit() {
  editing.value = true;
  await nextTick();
  qEl.value && qEl.value.focus();
}
</script>
