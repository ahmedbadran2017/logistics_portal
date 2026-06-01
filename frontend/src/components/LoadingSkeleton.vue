<template>
  <div class="p-5 space-y-3">
    <div v-for="i in rows" :key="i" class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-md skeleton-shimmer" />
      <div class="flex-1 space-y-1.5">
        <div class="h-3 skeleton-shimmer rounded" :style="{ width: 40 + ((i * 13) % 40) + '%' }" />
        <div class="h-2.5 skeleton-shimmer rounded w-1/4" />
      </div>
      <div class="h-4 w-16 skeleton-shimmer rounded" />
      <div class="h-5 w-12 skeleton-shimmer rounded" />
    </div>
  </div>
</template>

<script setup>
defineProps({ rows: { type: Number, default: 8 } });
</script>
