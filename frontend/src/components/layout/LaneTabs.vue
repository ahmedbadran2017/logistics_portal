<template>
  <!-- Sub-nav for a Contact-Center lane: renders nothing outside a lane route,
       so it's safe to mount globally above the router-view. Sticky so the tabs
       stay put while the lane's content scrolls. -->
  <div
    v-if="lane && tabs.length"
    class="sticky top-0 z-20 bg-white/95 backdrop-blur-sm border-b border-stone-200/70 px-3 lg:px-6"
  >
    <div class="flex items-center gap-0.5 overflow-x-auto" style="scrollbar-width:none">
      <router-link
        v-for="tab in tabs"
        :key="tab.to"
        :to="{ name: tab.to }"
        class="flex items-center gap-1.5 px-3 py-2.5 text-[13px] font-medium border-b-2 -mb-px whitespace-nowrap transition-colors"
        :class="route.name === tab.to
          ? 'border-[var(--accent-600)] text-[var(--accent-700)]'
          : 'border-transparent text-stone-500 hover:text-stone-800'"
      >
        <Icon :name="tab.icon" :size="15" :class="route.name === tab.to ? 'text-[var(--accent-600)]' : 'text-stone-400'" />
        <span>{{ t(tab.label) }}</span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { useI18n } from "@/composables/useI18n";
import { useAuth } from "@/composables/useAuth";
import { laneForRoute } from "@/lib/laneTabs";

const route = useRoute();
const { t } = useI18n();
const { hiddenPages } = useAuth();

const lane = computed(() => laneForRoute(route.name));
// A manager can still hide an individual sub-page for a user; honour that here
// too so the tab bar never links to something the sidebar wouldn't.
const tabs = computed(() => {
  if (!lane.value) return [];
  const h = new Set(hiddenPages.value || []);
  return lane.value.tabs.filter((tab) => !h.has(tab.to));
});
</script>
