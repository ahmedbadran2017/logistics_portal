<template>
  <div class="relative">
    <button class="dr-btn" :class="isCustom ? 'dr-btn-on' : ''" @click="open = !open">
      <Icon name="calendar" :size="13" />
      <span>{{ label }}</span>
      <Icon :name="open ? 'chevron-up' : 'chevron-down'" :size="12" class="opacity-50" />
    </button>

    <Transition name="drpop">
      <div v-if="open" class="dr-pop">
        <button v-for="p in PRESETS" :key="p.d" class="dr-opt"
                :class="!isCustom && days === p.d ? 'dr-opt-on' : ''"
                @click="pick(p.d)">
          {{ t(p.label) }}
        </button>
        <div class="border-t border-stone-100 mt-1 pt-2 space-y-1.5">
          <div class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 px-1">
            {{ t('dr.custom') }}
          </div>
          <div class="flex items-center gap-1.5">
            <input v-model="f1" type="date" :max="f2 || today" class="dr-date" />
            <span class="text-stone-300 text-[11px]">→</span>
            <input v-model="f2" type="date" :min="f1" :max="today" class="dr-date" />
          </div>
          <button class="dr-apply" :disabled="!f1 && !f2" @click="apply">{{ t('dr.apply') }}</button>
        </div>
      </div>
    </Transition>
    <div v-if="open" class="fixed inset-0 z-[5]" @click="open = false" />
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const PRESETS = [
  { d: 1, label: "dr.d1" },
  { d: 7, label: "dr.d7" },
  { d: 30, label: "dr.d30" },
  { d: 90, label: "dr.d90" },
];

const props = defineProps({
  days: { type: Number, default: 30 },
  frm: { type: String, default: "" },
  to: { type: String, default: "" },
});
const emit = defineEmits(["update:days", "update:frm", "update:to", "change"]);

const open = ref(false);
const f1 = ref(props.frm);
const f2 = ref(props.to);
const today = new Date().toISOString().slice(0, 10);

const isCustom = computed(() => !!(props.frm || props.to));
const label = computed(() => {
  if (props.frm && props.to) return `${props.frm.slice(5)} → ${props.to.slice(5)}`;
  if (props.frm) return `${t("dr.since")} ${props.frm.slice(5)}`;
  if (props.to) return `${t("dr.until")} ${props.to.slice(5)}`;
  const p = PRESETS.find((x) => x.d === props.days);
  return p ? t(p.label) : `${props.days}${t("cf.days")}`;
});

function pick(d) {
  emit("update:frm", "");
  emit("update:to", "");
  emit("update:days", d);
  f1.value = "";
  f2.value = "";
  open.value = false;
  emit("change");
}

function apply() {
  emit("update:frm", f1.value || "");
  emit("update:to", f2.value || "");
  open.value = false;
  emit("change");
}
</script>

<style scoped>
.dr-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 40px; padding: 0 12px; border-radius: 12px;
  font-size: 12.5px; font-weight: 600; color: rgb(87 83 78);
  background: white; box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8);
  transition: all .15s ease; white-space: nowrap;
}
.dr-btn:hover { box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.dr-btn-on { color: var(--accent-700); box-shadow: inset 0 0 0 1px var(--accent-300); }
.dr-pop {
  position: absolute; top: calc(100% + 6px); inset-inline-end: 0; z-index: 10;
  width: 230px; padding: 6px; border-radius: 14px; background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228), 0 12px 32px -8px rgb(0 0 0 / .18);
}
.dr-opt {
  display: block; width: 100%; text-align: start;
  height: 32px; padding: 0 9px; border-radius: 9px;
  font-size: 12.5px; font-weight: 500; color: rgb(68 64 60);
  transition: background .12s ease;
}
.dr-opt:hover { background: rgb(245 245 244); }
.dr-opt-on { background: var(--accent-50); color: var(--accent-700); font-weight: 700; }
.dr-date {
  flex: 1; min-width: 0; height: 32px; padding: 0 7px; border-radius: 9px;
  font-size: 11.5px; color: rgb(41 37 36);
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  font-variant-numeric: tabular-nums;
}
.dr-date:focus { outline: none; box-shadow: inset 0 0 0 2px var(--accent-300); }
.dr-apply {
  width: 100%; height: 32px; border-radius: 9px;
  font-size: 12px; font-weight: 700; color: white;
  background: var(--accent-600); transition: opacity .15s ease;
}
.dr-apply:disabled { opacity: .4; }
.drpop-enter-active, .drpop-leave-active { transition: all .15s ease; }
.drpop-enter-from, .drpop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
