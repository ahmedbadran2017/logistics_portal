<template>
  <aside
    class="bg-white border-r border-stone-200 flex flex-col transition-all duration-200 shrink-0 relative"
    :class="collapsed ? 'w-[64px]' : 'w-[224px]'"
    aria-label="Primary navigation"
  >
    <!-- Brand -->
    <div class="h-[60px] flex items-center px-4 border-b border-stone-200 shrink-0">
      <img
        v-if="!collapsed"
        :src="logoUrl"
        alt="Justyol"
        class="h-7 w-auto select-none"
        draggable="false"
      />
      <img
        v-else
        :src="logoUrl"
        alt="Justyol"
        class="h-7 w-7 object-contain select-none"
        draggable="false"
      />
      <button
        @click="$emit('toggle')"
        class="ml-auto text-stone-400 hover:text-stone-700 hover:bg-stone-100 rounded-md p-1 transition-colors"
        :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :aria-expanded="!collapsed"
      >
        <Icon :name="collapsed ? 'chevron-right' : 'chevron-left'" :size="14" />
      </button>
    </div>

    <!-- Nav -->
    <nav class="flex-1 p-2 overflow-y-auto">
      <div v-if="!collapsed" class="px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-[0.08em] text-stone-400">
        Overview
      </div>
      <div class="space-y-0.5">
        <NavItem v-for="item in navOverview" :key="item.to" v-bind="item" :collapsed="collapsed" />
      </div>

      <!--
        Add sections here as modules land. Suggested groupings:
          • Warehouse   (Receiving, Picking, Counts, Transfers, Bins)
          • Logistics   (Inbound, Customs, Carriers, Documents)
          • Returns     (RMA, Damage, Restocking)
      -->
    </nav>

    <!-- Footer -->
    <div class="border-t border-stone-200 p-3 shrink-0 space-y-2">
      <a
        href="/app"
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center gap-2 text-[12px] text-stone-600 hover:text-[var(--yol-v2-accent-700)] transition-colors group"
        :title="collapsed ? 'Open ERPNext' : ''"
      >
        <Icon name="external-link" :size="14" class="transition-transform group-hover:translate-x-0.5" />
        <span v-if="!collapsed">Open ERPNext</span>
      </a>
      <a
        href="/purchasing"
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center gap-2 text-[12px] text-stone-600 hover:text-[var(--yol-v2-accent-700)] transition-colors group"
        :title="collapsed ? 'Open Purchasing Portal' : ''"
      >
        <Icon name="shopping-cart" :size="14" />
        <span v-if="!collapsed">Purchasing Portal</span>
      </a>
    </div>
  </aside>
</template>

<script setup>
import NavItem from "./NavItem.vue";
import Icon from "@/components/Icon.vue";

defineProps({ collapsed: Boolean });
defineEmits(["toggle"]);

const logoUrl = "/assets/ecommerce_integrations/icons/logo.svg";

const navOverview = [
  { to: "/logistics", label: "Dashboard", icon: "home" },
];
</script>
