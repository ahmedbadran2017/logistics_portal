<template>
  <div class="flex h-screen bg-stone-50 overflow-hidden">
    <Sidebar :collapsed="collapsed" @toggle="collapsed = !collapsed" />
    <!-- main landmark for assistive tech -->

    <div class="flex-1 min-w-0 flex flex-col">
      <Header />
      <main class="flex-1 overflow-auto">
        <router-view v-slot="{ Component, route }">
          <transition name="page" mode="out-in">
            <!-- Keyed on route.name so query-string changes don't remount the page
                 and trigger full refetches (fixes audit H10). -->
            <div :key="route.name || route.path">
              <component :is="Component" />
            </div>
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import Sidebar from "./Sidebar.vue";
import Header from "./Header.vue";
import { usePersist } from "@/composables/usePersist";

const collapsed = usePersist("pp_sidebar_collapsed", false);
</script>

<style scoped>
.page-enter-active { transition: opacity 0.2s ease, transform 0.25s cubic-bezier(0.2, 0.9, 0.3, 1); }
.page-leave-active { transition: opacity 0.12s ease; }
.page-enter-from { opacity: 0; transform: translateY(8px); }
.page-leave-to { opacity: 0; }
</style>
