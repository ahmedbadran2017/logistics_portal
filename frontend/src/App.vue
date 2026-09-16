<template>
  <router-view />
  <ToastLayer />
  <!-- Not on the PDA. The floor works this app on a Zebra, one hand on the
       device and one on a parcel, and a floating pill parked over the scan
       screen is a mis-tap waiting to happen. The people holding those
       devices scan; they do not file tickets (Ahmed, 2026-09-17). Desks and
       the wall screens keep it. Held back until the role is known, so it
       never flashes on a PDA during boot. -->
  <TaskHubWidget v-if="showTasks" portal="Logistics" />
</template>

<script setup>
import { computed, ref } from "vue";
import ToastLayer from "@/components/ui/ToastLayer.vue";
import TaskHubWidget from "@/components/TaskHubWidget.vue";
import { useAuth } from "@/composables/useAuth";
import { isMobileRole } from "@/lib/roles";

const { role } = useAuth();

// Same test the app shell uses to decide it is on a handheld: a small screen
// AND a coarse pointer. A laptop at a narrow window keeps the widget.
const pda = ref(false);
try {
  const mq = window.matchMedia("(max-width: 640px) and (pointer: coarse)");
  pda.value = mq.matches;
  mq.addEventListener?.("change", (e) => { pda.value = e.matches; });
} catch { /* odd browsers: the role flag below still decides */ }

const showTasks = computed(() =>
  !pda.value && !!role.value && !isMobileRole(role.value));
</script>
