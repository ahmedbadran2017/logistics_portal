<template>
  <!-- Self-contained shell for a Contact-Center lane: the lane's tab bar plus
       its own nested router-view. Each lane route group mounts this, so a lane
       owns its sub-pages (queue / dashboard / reports / settings) as a proper
       nested tree instead of sharing a global tab layer. -->
  <div>
    <LaneTabs />
    <router-view v-slot="{ Component }">
      <component :is="Component" :key="$route.name + JSON.stringify($route.params)" />
    </router-view>
  </div>
</template>

<script setup>
import LaneTabs from "./LaneTabs.vue";
</script>
