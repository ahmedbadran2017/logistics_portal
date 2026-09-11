<template>
  <!-- The pick list's life story, one glance: picked → sorted → printed →
       shipped. Floor stages count PIECES, paper stages count PARCELS. A
       stage is solid when complete, tinted while in progress, grey before
       it starts — so "stuck between printed and shipped" reads instantly. -->
  <div v-if="life && (life.units || life.orders)" class="flex items-center flex-wrap"
       :class="compact ? 'gap-1' : 'gap-1.5'">
    <template v-for="(st, i) in stages" :key="st.k">
      <span class="inline-flex items-center gap-1 rounded-full ring-1 tabular-nums whitespace-nowrap"
            :class="[compact ? 'text-[9.5px] font-bold px-1.5 py-px' : 'text-[11px] font-bold px-2 py-0.5',
                     chip(st)]"
            :title="t('plife.' + st.k) + ' ' + st.done + '/' + st.total">
        <span class="rounded-full" :class="[compact ? 'w-1.5 h-1.5' : 'w-2 h-2', dot(st)]" />
        <span v-if="!compact">{{ t('plife.' + st.k) }}</span>
        {{ st.done }}/{{ st.total }}
      </span>
      <span v-if="i < stages.length - 1" class="text-stone-300"
            :class="compact ? 'text-[8px]' : 'text-[10px]'">·</span>
    </template>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const props = defineProps({
  life: { type: Object, default: null },
  compact: { type: Boolean, default: false },
});

const PALETTE = {
  picked:  { on: "text-emerald-800 bg-emerald-50 ring-emerald-200", dotOn: "bg-emerald-500" },
  sorted:  { on: "text-violet-800 bg-violet-50 ring-violet-200",    dotOn: "bg-violet-500" },
  printed: { on: "text-sky-800 bg-sky-50 ring-sky-200",             dotOn: "bg-sky-500" },
  shipped: { on: "text-teal-800 bg-teal-50 ring-teal-300",          dotOn: "bg-teal-600" },
};

const stages = computed(() => {
  const l = props.life || {};
  return [
    { k: "picked",  done: l.picked || 0,  total: l.units || 0 },
    { k: "sorted",  done: l.sorted || 0,  total: l.units || 0 },
    { k: "printed", done: l.printed || 0, total: l.orders || 0 },
    { k: "shipped", done: l.shipped || 0, total: l.orders || 0 },
  ];
});

function chip(st) {
  if (!st.total || !st.done) return "text-stone-400 bg-stone-50 ring-stone-200";
  return PALETTE[st.k].on + (st.done >= st.total ? "" : " opacity-80");
}
function dot(st) {
  if (!st.total || !st.done) return "bg-stone-300";
  return PALETTE[st.k].dotOn + (st.done >= st.total ? "" : " opacity-60");
}
</script>
