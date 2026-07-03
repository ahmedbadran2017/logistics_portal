<template>
  <div v-if="open" class="fixed inset-0 z-[120]">
    <!-- backdrop -->
    <div class="absolute inset-0 bg-stone-900/20 animate-fade-in" @click="$emit('close')" />

    <!-- slide-over: right in LTR, left in RTL -->
    <aside
      class="absolute inset-y-0 w-[min(92vw,384px)] bg-white shadow-drawer flex flex-col"
      :class="isRTL ? 'start-0 animate-drawer-inL' : 'end-0 animate-drawer-in'"
      :style="isRTL ? 'left:0' : 'right:0'"
    >
      <!-- header -->
      <header class="h-[52px] shrink-0 border-b border-stone-200/70 flex items-center gap-2.5 px-4">
        <Icon name="bell" :size="16" class="text-stone-500" />
        <span class="text-[13.5px] font-semibold text-stone-900 flex-1">
          {{ t("notif.title", "Notifications") }}
        </span>
        <button
          type="button"
          class="text-[11.5px] font-medium text-[var(--accent-700)] hover:text-[var(--accent-800)]"
          @click="markRead"
        >{{ t("notif.markRead", "Mark read") }}</button>
        <button
          type="button"
          class="w-7 h-7 rounded-md text-stone-400 hover:bg-stone-100 hover:text-stone-700 flex items-center justify-center"
          @click="$emit('close')"
        >
          <Icon name="x" :size="16" />
        </button>
      </header>

      <!-- list -->
      <div class="flex-1 overflow-y-auto py-1">
        <div
          v-for="(a, i) in items"
          :key="i"
          class="flex items-start gap-3 px-4 py-3 border-b border-stone-100 hover:bg-stone-50/70 transition-colors"
        >
          <span
            class="mt-1 w-2 h-2 rounded-full flex-shrink-0"
            :class="dotClass(a.sev)"
          />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="text-[13px] font-semibold text-stone-900 truncate">{{ a.title }}</span>
              <span class="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0 ms-auto">{{ a.t }}</span>
            </div>
            <p class="text-[12px] text-stone-600 mt-0.5 leading-snug">{{ a.body }}</p>
            <button
              v-if="a.action"
              type="button"
              class="mt-1.5 text-[11.5px] font-semibold text-[var(--accent-700)] hover:text-[var(--accent-800)]"
            >{{ a.action }}</button>
          </div>
        </div>

        <div v-if="!items.length" class="flex flex-col items-center justify-center py-16 text-center">
          <div class="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-500 flex items-center justify-center mb-3">
            <Icon name="check-circle" :size="22" />
          </div>
          <p class="text-[13px] font-medium text-stone-700">{{ t("common.allCaught", "All caught up") }}</p>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useI18n } from "@/composables/useI18n";

defineProps({ open: { type: Boolean, default: false } });
defineEmits(["close"]);

const { t, isRTL } = useI18n();

// Seeded from the handoff AUDIT array.
const items = ref([
  { sev: "red", t: "4m", title: "SLA breached", body: "Order #242638 · Mohmad Mohmad has been Out of Stock 2h38m in Cosmetic zone — past the 14:00 cutoff.", action: "Reassign" },
  { sev: "orange", t: "12m", title: "Failed delivery", body: "AWB LD007744422 (#240682 · Edghir hanane) — Cathedis logged a Failed Attempt. 2nd in 24h.", action: "Open order" },
  { sev: "orange", t: "26m", title: "Carrier exception", body: "AWB LD007748688 (#242128 · Fatima Fatima) flagged Delivery Exception by Cathedis.", action: "Open order" },
  { sev: "yellow", t: "38m", title: "Manifest cutoff risk", body: "3 picked orders not yet labeled — SH-000179 cutoff in 1h 40m.", action: "View queue" },
  { sev: "insight", t: "1h", title: "Daily insight", body: "Said's pick time rose ~22% after 16:00 three days running — likely fatigue on the SLOW zone.", action: null },
  { sev: "insight", t: "1h", title: "Daily insight", body: "Returns for SKU CSM44021 are +40% this week, all flagged 'defective' — worth a supplier quality check.", action: null },
]);

const DOT = {
  red: "bg-rose-500",
  orange: "bg-orange-500",
  yellow: "bg-amber-500",
  insight: "bg-[var(--accent-500)]",
};
function dotClass(sev) {
  return DOT[sev] || "bg-stone-400";
}

function markRead() {
  items.value = [];
}
</script>

<style scoped>
.animate-drawer-inL { animation: drawerInL 280ms cubic-bezier(0.16, 1, 0.3, 1); }
</style>
