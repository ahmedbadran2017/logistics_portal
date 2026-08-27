<template>
  <!-- Sub-nav for a Contact-Center lane: renders nothing outside a lane route,
       so it's safe to mount globally above the router-view. Sticky so the tabs
       stay put while the lane's content scrolls. The first tab (the lane's
       working queue) carries a live depth badge — from Reports or Settings the
       agent had no idea the queue was growing behind them. -->
  <div
    v-if="lane && tabs.length"
    class="sticky top-0 z-20 bg-white/95 backdrop-blur-sm border-b border-stone-200/70 px-3 lg:px-6"
  >
    <div class="flex items-center gap-0.5 overflow-x-auto" style="scrollbar-width:none">
      <router-link
        v-for="(tab, i) in tabs"
        :key="tab.to"
        :to="{ name: tab.to }"
        class="flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium border-b-2 -mb-px whitespace-nowrap transition-colors"
        :class="route.name === tab.to
          ? 'border-[var(--accent-600)] text-[var(--accent-700)]'
          : 'border-transparent text-stone-500 hover:text-stone-800'"
      >
        <Icon :name="tab.icon" :size="15" :class="route.name === tab.to ? 'text-[var(--accent-600)]' : 'text-stone-400'" />
        <span>{{ t(tab.label) }}</span>
        <span v-if="i === 0 && badge !== null"
              class="text-[10px] font-bold tabular-nums rounded-full px-1.5 py-px ring-1"
              :class="badge ? 'text-rose-700 bg-rose-50 ring-rose-200/70' : 'text-stone-400 bg-stone-100 ring-stone-200'">
          {{ badge }}
        </span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useAuth } from "@/composables/useAuth";
import { laneForRoute, LANE_ADMIN_KEY } from "@/lib/laneTabs";

const route = useRoute();
const { t } = useI18n();
const { hiddenPages, role, ccAdmin } = useAuth();

const lane = computed(() => laneForRoute(route.name));
// A manager can still hide an individual sub-page for a user; honour that here
// too so the tab bar never links to something the sidebar wouldn't.
const tabs = computed(() => {
  if (!lane.value) return [];
  const h = new Set(hiddenPages.value || []);
  // Section dashboard/reports/settings carry TEAM-level data — managers and
  // the lane's own section admins only; a plain agent gets just the queue.
  const adminKey = LANE_ADMIN_KEY[lane.value.key];
  const isAdmin = role.value === "manager" || !!ccAdmin.value?.[adminKey];
  return lane.value.tabs.filter((tab) =>
    !h.has(tab.to) && (!tab.admin || isAdmin));
});

// Live queue depth for the current lane (server-cached 60s, polled 90s).
const counts = ref(null);
const badge = computed(() => {
  if (!lane.value || !counts.value) return null;
  const n = counts.value[lane.value.key];
  return typeof n === "number" ? n : null;
});
async function loadCounts() {
  if (!lane.value) return;
  try {
    counts.value = await api("contact_center.lane_counts");
  } catch (e) { /* the badge is a bonus, never an error */ }
}
onMounted(loadCounts);
const timer = setInterval(() => {
  if (document.visibilityState === "visible") loadCounts();
}, 90000);
onUnmounted(() => clearInterval(timer));
</script>
