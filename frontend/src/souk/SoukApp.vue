<template>
  <router-view />
  <ToastLayer />
  <ErrorPopup />
</template>

<script setup>
import ToastLayer from "@/components/ui/ToastLayer.vue";
import ErrorPopup from "@/components/ui/ErrorPopup.vue";
</script>
