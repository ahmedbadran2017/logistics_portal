<template>
  <!-- ── Mobile-role stage: iPhone-style device frame ────────────── -->
  <div
    v-if="mobileRole"
    class="min-h-screen bg-gradient-to-br from-stone-100 to-stone-200 flex items-center justify-center p-4 relative"
  >
    <!-- Floating logo + role switcher, top-start -->
    <div class="absolute top-4 z-10 flex items-center gap-3" style="inset-inline-start:1rem">
      <img :src="logoSrc" alt="Justyol" class="h-4" />
      <button
        type="button"
        class="flex items-center gap-2 ps-1.5 pe-2.5 py-1.5 rounded-lg bg-white/90 backdrop-blur ring-1 ring-stone-200/70 shadow-sm hover:bg-white transition-colors"
        @click="roleMenu = !roleMenu"
      >
        <span class="w-6 h-6 rounded-md flex items-center justify-center text-[10px] font-semibold bg-[var(--accent-50)] text-[var(--accent-700)]">{{ initials }}</span>
        <div class="text-start leading-tight">
          <div class="text-[11.5px] font-semibold text-stone-900">{{ t(`roles.${role}`) }}</div>
          <div class="text-[9.5px] text-stone-500 truncate max-w-[110px]">{{ fullName }}</div>
        </div>
        <Icon name="chevron-down" :size="12" class="text-stone-400" />
      </button>

      <!-- role menu -->
      <div
        v-if="roleMenu"
        class="absolute top-full mt-1.5 min-w-[200px] bg-white rounded-xl shadow-floating ring-1 ring-stone-200/70 overflow-hidden py-1 animate-menu"
        style="inset-inline-start:0"
      >
        <div class="px-3 pt-2 pb-1.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">
          {{ t("nav.viewAs", "View as role") }}
        </div>
        <button
          v-for="r in roles"
          :key="r"
          type="button"
          class="w-full flex items-center gap-2.5 px-3 py-1.5 text-start"
          :class="r === role ? 'bg-stone-100' : 'hover:bg-stone-50'"
          @click="pickRole(r)"
        >
          <span class="text-[12.5px] font-medium text-stone-900 flex-1">{{ t(`roles.${r}`) }}</span>
          <Icon v-if="r === role" name="check" :size="14" class="text-[var(--accent-600)]" />
        </button>
      </div>
    </div>

    <!-- Phone frame -->
    <div class="relative" style="width:390px;height:800px;max-height:calc(100vh - 2rem)">
      <div class="absolute inset-0 rounded-[44px] bg-stone-900 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.45),0_0_0_2px_rgba(0,0,0,0.6)] p-[10px]">
        <div class="relative w-full h-full rounded-[36px] overflow-hidden bg-stone-50">
          <!-- status bar -->
          <div class="absolute top-0 inset-x-0 h-11 z-20 flex items-end justify-between px-6 pb-1.5 text-[12px] font-semibold text-stone-900 pointer-events-none">
            <span class="tabular-nums">9:41</span>
            <div class="absolute left-1/2 -translate-x-1/2 top-2 w-[110px] h-[26px] bg-stone-900 rounded-full" />
            <span class="flex items-center gap-1">
              <Icon name="globe" :size="13" /><span class="tabular-nums">100%</span>
            </span>
          </div>
          <!-- screen -->
          <div class="absolute inset-0 pt-11 pb-[68px] overflow-y-auto overscroll-contain" style="scrollbar-width:none">
            <router-view v-slot="{ Component }">
              <component :is="Component" :key="$route.fullPath" />
            </router-view>
          </div>
          <!-- bottom tab bar -->
          <div class="absolute bottom-0 inset-x-0 h-[60px] bg-white/95 backdrop-blur-sm border-t border-stone-200/70 flex items-stretch">
            <router-link
              v-for="item in mobileNav"
              :key="item.to"
              :to="{ name: item.to }"
              class="flex-1 flex flex-col items-center justify-center gap-1 transition-colors"
              :class="route.name === item.to ? 'text-[var(--accent-600)]' : 'text-stone-400'"
            >
              <Icon :name="item.icon" :size="21" />
              <span class="text-[10px] font-medium">{{ t(item.label) }}</span>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Desktop shell ───────────────────────────────────────────── -->
  <div v-else class="h-screen flex overflow-hidden bg-[#f5f5f4]">
    <!-- Desktop sidebar -->
    <Sidebar class="hidden lg:flex" @open-search="cmdOpen = true" />

    <!-- Mobile drawer sidebar -->
    <div v-if="drawer" class="fixed inset-0 bg-black/40 z-40 lg:hidden" @click="drawer = false" />
    <transition name="drawer">
      <Sidebar
        v-if="drawer"
        class="fixed inset-y-0 z-50 lg:hidden"
        style="inset-inline-start:0"
        @open-search="cmdOpen = true; drawer = false"
      />
    </transition>

    <div class="flex-1 flex flex-col min-w-0">
      <TopBar
        :unread="unread"
        @toggle-menu="drawer = !drawer"
        @open-notif="notifOpen = true"
      />
      <main class="flex-1 overflow-y-auto bg-[#f5f5f4]">
        <router-view v-slot="{ Component }">
          <component :is="Component" :key="$route.fullPath" />
        </router-view>
      </main>
    </div>
  </div>

  <!-- ── Global overlays ─────────────────────────────────────────── -->
  <CommandPalette :open="cmdOpen" @close="cmdOpen = false" />
  <NotifCenter :open="notifOpen" @close="notifOpen = false" />
  <OfflineBanner :show="offline" :queued="queued" />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import Sidebar from "./Sidebar.vue";
import TopBar from "./TopBar.vue";
import CommandPalette from "@/components/ui/CommandPalette.vue";
import NotifCenter from "@/components/ui/NotifCenter.vue";
import OfflineBanner from "@/components/ui/OfflineBanner.vue";
import Icon from "@/components/ui/Icon.vue";
import { useRoute } from "vue-router";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { isMobileRole, navItemsFor } from "@/lib/roles";

const route = useRoute();
const logoSrc = "/assets/logistics_portal/justyol-logo.png";
const { role, roles, fullName, setActiveRole } = useAuth();
const { t } = useI18n();

const mobileNav = computed(() => navItemsFor(role.value));

const drawer = ref(false);
const cmdOpen = ref(false);
const notifOpen = ref(false);
const roleMenu = ref(false);
const offline = ref(false); // wired false by default
const queued = ref(0);
const unread = ref(4);

const mobileRole = computed(() => isMobileRole(role.value));
const initials = computed(() =>
  (fullName.value || "?").split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase()
);

function pickRole(r) {
  setActiveRole(r);
  roleMenu.value = false;
}

// Global ⌘K / Ctrl+K to toggle the command palette.
function onKey(e) {
  if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
    e.preventDefault();
    cmdOpen.value = !cmdOpen.value;
  }
}
onMounted(() => window.addEventListener("keydown", onKey));
onUnmounted(() => window.removeEventListener("keydown", onKey));
</script>

<style scoped>
.drawer-enter-from, .drawer-leave-to { transform: translateX(-100%); }
[dir="rtl"] .drawer-enter-from, [dir="rtl"] .drawer-leave-to { transform: translateX(100%); }
.drawer-enter-active, .drawer-leave-active { transition: transform 0.2s ease; }
</style>
