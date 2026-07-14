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
          v-if="items.some((a) => !a.read)"
          type="button"
          class="text-[11.5px] font-medium text-[var(--accent-700)] hover:text-[var(--accent-800)]"
          @click="markAllRead"
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
        <div v-if="loading" class="p-4 space-y-2">
          <div v-for="n in 4" :key="n" class="h-[64px] rounded-xl ring-1 ring-stone-200/60 bg-stone-50 animate-pulse" />
        </div>

        <template v-else>
          <div
            v-for="a in items"
            :key="a.id"
            class="flex items-start gap-3 px-4 py-3 border-b border-stone-100 hover:bg-stone-50/70 transition-colors"
            :class="a.read ? 'opacity-60' : ''"
          >
            <span class="mt-1 w-2 h-2 rounded-full flex-shrink-0" :class="a.read ? 'bg-stone-300' : dotClass(a.sev)" />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="text-[13px] font-semibold text-stone-900 truncate">{{ a.title }}</span>
                <span class="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0 ms-auto">{{ a.t }}</span>
              </div>
              <p class="text-[12px] text-stone-600 mt-0.5 leading-snug">{{ a.body }}</p>
              <button
                v-if="a.order"
                type="button"
                class="mt-1.5 text-[11.5px] font-semibold text-[var(--accent-700)] hover:text-[var(--accent-800)]"
                @click="openOrder(a)"
              >{{ t("notif.openOrder", "Open order") }}</button>
            </div>
          </div>

          <div v-if="!items.length" class="flex flex-col items-center justify-center py-16 text-center">
            <div class="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-500 flex items-center justify-center mb-3">
              <Icon name="check-circle" :size="22" />
            </div>
            <p class="text-[13px] font-medium text-stone-700">{{ t("common.allCaught", "All caught up") }}</p>
          </div>
        </template>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const props = defineProps({ open: { type: Boolean, default: false } });
const emit = defineEmits(["close", "read"]);

const { t, isRTL } = useI18n();
const router = useRouter();

const items = ref([]);
const loading = ref(false);

watch(() => props.open, async (v) => {
  if (!v) return;
  loading.value = true;
  try {
    items.value = (await api("audit.recent_alerts")) || [];
  } catch (_) {
    items.value = [];
  } finally {
    loading.value = false;
  }
});

const DOT = {
  red: "bg-rose-500",
  orange: "bg-orange-500",
  yellow: "bg-amber-500",
  insight: "bg-[var(--accent-500)]",
};
function dotClass(sev) {
  return DOT[sev] || "bg-stone-400";
}

async function markAllRead() {
  try {
    await apiPost("audit.mark_read");
    items.value = items.value.map((a) => ({ ...a, read: true }));
    emit("read");
  } catch (_) { /* badge poll self-corrects */ }
}

function openOrder(a) {
  if (!a.order) return;
  apiPost("audit.mark_read", { names: [a.id] }).catch(() => {});
  a.read = true;
  emit("read");
  emit("close");
  router.push({ name: "OrderDetail", params: { name: String(a.order).replace("#", "") } });
}
</script>

<style scoped>
.animate-drawer-inL { animation: drawerInL 280ms cubic-bezier(0.16, 1, 0.3, 1); }
</style>
