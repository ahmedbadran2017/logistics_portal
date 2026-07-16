<template>
  <div v-if="total > 0" class="flex items-center justify-between gap-3 flex-wrap px-1">
    <div class="flex items-center gap-2.5 flex-wrap">
      <span class="text-[11.5px] text-stone-500 tabular-nums">
        {{ from }}–{{ to }} <span class="text-stone-300">/</span> {{ total }}
      </span>
      <!-- rows per page -->
      <div class="pgz">
        <button v-for="s in SIZES" :key="s" class="pgz-btn" :class="pageSize === s ? 'pgz-on' : ''"
                @click="emit('update:pageSize', s); emit('update:page', 1)">{{ s }}</button>
      </div>
    </div>

    <div v-if="pages > 1" class="flex items-center gap-1">
      <button class="pg-btn" :disabled="page <= 1" :title="t('pg.prev')" @click="go(page - 1)">
        <Icon name="chevron-left" :size="13" class="flip-rtl" />
      </button>
      <button v-for="(p, i) in window" :key="i"
              class="pg-num" :class="p === page ? 'pg-num-on' : ''"
              :disabled="p === '…'" @click="p !== '…' && go(p)">{{ p }}</button>
      <button class="pg-btn" :disabled="page >= pages" :title="t('pg.next')" @click="go(page + 1)">
        <Icon name="chevron-right" :size="13" class="flip-rtl" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const SIZES = [20, 50, 100];

const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  total: { type: Number, required: true },
});
const emit = defineEmits(["update:page", "update:pageSize"]);

const pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)));
const from = computed(() => (props.page - 1) * props.pageSize + 1);
const to = computed(() => Math.min(props.page * props.pageSize, props.total));

// First, last, and a window around the current page — 3,014 backlog rows are
// 151 pages at 20/page; a full list of numbers is unusable.
const window = computed(() => {
  const n = pages.value;
  const p = props.page;
  if (n <= 7) return Array.from({ length: n }, (_, i) => i + 1);
  const out = [1];
  const lo = Math.max(2, p - 1);
  const hi = Math.min(n - 1, p + 1);
  if (lo > 2) out.push("…");
  for (let i = lo; i <= hi; i++) out.push(i);
  if (hi < n - 1) out.push("…");
  out.push(n);
  return out;
});

function go(p) {
  const next = Math.min(pages.value, Math.max(1, p));
  if (next !== props.page) emit("update:page", next);
}
</script>

<style scoped>
.pgz { display: inline-flex; gap: 1px; padding: 2px; background: rgb(231 229 228 / 0.6); border-radius: 9px; }
.pgz-btn {
  height: 24px; min-width: 30px; padding: 0 7px; border-radius: 7px;
  font-size: 11px; font-weight: 700; color: rgb(120 113 108);
  font-variant-numeric: tabular-nums; transition: all .15s ease;
}
.pgz-btn:hover { color: rgb(41 37 36); }
.pgz-on { background: white; color: rgb(28 25 23); box-shadow: 0 1px 2px rgb(0 0 0 / .08); }
.pg-btn {
  width: 32px; height: 32px; border-radius: 10px; background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  display: inline-flex; align-items: center; justify-content: center;
  transition: all .15s ease;
}
.pg-btn:hover:not(:disabled) { box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.pg-btn:disabled { opacity: .4; }
.pg-num {
  min-width: 32px; height: 32px; padding: 0 6px; border-radius: 10px;
  font-size: 12px; font-weight: 600; color: rgb(87 83 78);
  font-variant-numeric: tabular-nums; transition: all .15s ease;
}
.pg-num:hover:not(:disabled):not(.pg-num-on) { background: rgb(245 245 244); }
.pg-num:disabled { color: rgb(214 211 209); cursor: default; }
.pg-num-on {
  color: white; background: rgb(28 25 23);
  box-shadow: 0 2px 6px -2px rgb(0 0 0 / .3);
}
</style>
