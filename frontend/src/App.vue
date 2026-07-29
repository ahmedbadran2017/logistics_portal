<template>
  <router-view />
  <ToastLayer />
  <TaskHubWidget portal="Logistics" />
</template>

<script setup>
import ToastLayer from "@/components/ui/ToastLayer.vue";
import TaskHubWidget from "@/components/TaskHubWidget.vue";
</script>
