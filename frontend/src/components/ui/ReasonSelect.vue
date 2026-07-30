<template>
  <!-- A searchable single-select bound to a fixed vocabulary. No free text ever
       leaves it — the value is always one of `options`, so every cancel groups
       cleanly in the reports. Used for the cancellation reason on the
       confirmation board (per-row and bulk). -->
  <div ref="root" class="rsel" :class="open ? 'rsel-open' : ''">
    <button type="button" class="rsel-field" @click="toggle">
      <span class="truncate" :class="modelValue ? 'text-stone-800' : 'text-stone-400'">
        {{ modelValue || placeholder }}
      </span>
      <Icon name="chevron-down" :size="15" class="text-stone-400 shrink-0 rsel-chev" />
    </button>

    <div v-if="open" class="rsel-pop">
      <div class="rsel-search">
        <Icon name="search" :size="14" class="text-stone-400 shrink-0" />
        <input
          ref="searchEl" v-model="q" :placeholder="searchPlaceholder"
          class="rsel-search-input" dir="auto"
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="pickActive"
          @keydown.esc.prevent="close"
        />
      </div>
      <ul class="rsel-list">
        <li
          v-for="(o, i) in filtered" :key="o"
          class="rsel-opt"
          :class="[i === active ? 'rsel-opt-active' : '', o === modelValue ? 'rsel-opt-sel' : '']"
          @mouseenter="active = i" @click="pick(o)"
        >
          <span class="truncate" dir="auto">{{ o }}</span>
          <Icon v-if="o === modelValue" name="check" :size="14" class="shrink-0 text-[var(--accent-600)]" />
        </li>
        <li v-if="!filtered.length" class="rsel-empty">{{ noneText }}</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: "" },
  searchPlaceholder: { type: String, default: "" },
  noneText: { type: String, default: "—" },
});
const emit = defineEmits(["update:modelValue"]);

const root = ref(null);
const searchEl = ref(null);
const open = ref(false);
const q = ref("");
const active = ref(0);

const filtered = computed(() => {
  const s = q.value.trim().toLowerCase();
  const list = props.options || [];
  return s ? list.filter((o) => String(o).toLowerCase().includes(s)) : list;
});
watch(filtered, () => { active.value = 0; });

function toggle() { open.value ? close() : openMenu(); }
async function openMenu() {
  open.value = true;
  q.value = "";
  const i = (props.options || []).indexOf(props.modelValue);
  active.value = i >= 0 ? i : 0;
  await nextTick();
  searchEl.value?.focus();
}
function close() { open.value = false; }
function pick(o) { emit("update:modelValue", o); close(); }
function pickActive() { const o = filtered.value[active.value]; if (o) pick(o); }
function move(d) {
  if (!filtered.value.length) return;
  active.value = (active.value + d + filtered.value.length) % filtered.value.length;
}

function onDoc(e) { if (root.value && !root.value.contains(e.target)) close(); }
onMounted(() => document.addEventListener("mousedown", onDoc));
onBeforeUnmount(() => document.removeEventListener("mousedown", onDoc));
</script>

<style scoped>
.rsel { position: relative; }
.rsel-field {
  display: flex; align-items: center; gap: 8px; width: 100%;
  height: 36px; padding: 0 10px; border-radius: 8px;
  background: #fff; box-shadow: inset 0 0 0 1px rgb(231 229 228);
  font-size: 12.5px; text-align: start; transition: box-shadow .12s;
}
.rsel-field:hover { box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.rsel-open .rsel-field { box-shadow: inset 0 0 0 2px var(--accent-400); }
.rsel-chev { transition: transform .15s; }
.rsel-open .rsel-chev { transform: rotate(180deg); }

.rsel-pop {
  position: absolute; z-index: 40; top: calc(100% + 4px); left: 0; right: 0;
  background: #fff; border-radius: 12px; overflow: hidden;
  box-shadow: 0 1px 3px rgb(0 0 0 / .1), 0 8px 24px rgb(0 0 0 / .12),
              inset 0 0 0 1px rgb(231 229 228 / .8);
}
.rsel-search {
  display: flex; align-items: center; gap: 6px; padding: 8px 10px;
  border-bottom: 1px solid rgb(231 229 228 / .7);
}
.rsel-search-input {
  flex: 1; min-width: 0; border: 0; outline: 0; background: transparent;
  font-size: 12.5px; color: rgb(28 25 23);
}
.rsel-list { max-height: 240px; overflow-y: auto; padding: 4px; }
.rsel-opt {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  min-height: 34px; padding: 6px 8px; border-radius: 8px; cursor: pointer;
  font-size: 12.5px; color: rgb(41 37 36);
}
.rsel-opt-active { background: rgb(245 245 244); }
.rsel-opt-sel { font-weight: 600; color: rgb(28 25 23); }
.rsel-empty { padding: 10px 8px; font-size: 12px; color: rgb(168 162 158); text-align: center; }

/* Gloved-thumb targets on the PDAs. */
@media (pointer: coarse) {
  .rsel-field { height: 44px; }
  .rsel-opt { min-height: 44px; }
  .rsel-search-input { height: 32px; }
}
</style>
