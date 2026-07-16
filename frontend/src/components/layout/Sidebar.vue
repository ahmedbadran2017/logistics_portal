<template>
  <aside class="w-[236px] shrink-0 bg-white border-e border-stone-200/70 flex flex-col h-full">
    <!-- Logo lockup -->
    <div class="px-4 pt-4 pb-2">
      <div class="flex items-center gap-2 min-w-0">
        <img :src="logoSrc" alt="Justyol" class="block h-3.5 flex-shrink-0" />
        <span class="h-3.5 w-px bg-stone-200 flex-shrink-0" />
        <span class="text-[9.5px] font-semibold text-stone-400 tracking-[0.14em] uppercase">
          {{ t("nav.logistics", "Logistics") }}
        </span>
      </div>
    </div>

    <!-- ⌘K search launcher -->
    <div class="px-3 pb-3">
      <button
        type="button"
        class="w-full flex items-center gap-2 px-2.5 py-1.5 text-[12.5px] text-stone-500 bg-stone-50/80 hover:bg-stone-100 rounded-lg transition-colors"
        @click="$emit('open-search')"
      >
        <Icon name="search" :size="13" />
        <span class="flex-1 text-start truncate">{{ t("common.search") }}</span>
        <kbd class="inline-flex items-center justify-center min-w-[20px] h-[20px] px-1.5 text-[10.5px] font-medium text-stone-500 bg-white border border-stone-200/80 rounded-md">⌘K</kbd>
      </button>
    </div>

    <!-- Grouped nav -->
    <nav class="flex-1 px-2 overflow-y-auto pb-3">
      <div v-for="(group, gi) in nav" :key="group.section" :class="gi > 0 ? 'mt-4' : ''">
        <div class="px-3 mb-1 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">
          {{ t(group.section) }}
        </div>
        <div class="space-y-px">
          <router-link
            v-for="item in group.items"
            :key="item.label"
            :to="{ name: item.to }"
            custom
            v-slot="{ navigate }"
          >
            <a
              class="flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium cursor-pointer group transition-colors"
              :class="isActive(item)
                ? 'bg-[var(--accent-50)] text-[var(--accent-700)]'
                : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900'"
              @click="navigate"
            >
              <Icon
                :name="item.icon"
                :size="16"
                :class="isActive(item) ? 'text-[var(--accent-600)]' : 'text-stone-400 group-hover:text-stone-600'"
              />
              <span class="flex-1 truncate">{{ t(item.label) }}</span>
            </a>
          </router-link>
        </div>
      </div>
    </nav>

    <InstallApp />

    <!-- Language, for the screens too small to carry it in the top bar. The
         PDAs live here: full-size targets, set once, done. -->
    <div class="sm:hidden p-2 border-t border-stone-100">
      <div class="flex items-center gap-1.5">
        <button
          v-for="opt in langs"
          :key="opt.v"
          type="button"
          class="flex-1 h-11 rounded-lg text-[13px] font-semibold transition-all"
          :class="locale === opt.v
            ? 'bg-[var(--accent-600)] text-white'
            : 'bg-stone-100 text-stone-600 hover:bg-stone-200'"
          @click="setLocale(opt.v)"
        >{{ opt.l }}</button>
      </div>
    </div>

    <!-- Role switcher card -->
    <div class="p-2 border-t border-stone-100 relative">
      <button
        type="button"
        class="w-full flex items-center gap-2 ps-1.5 pe-2 py-1.5 rounded-lg hover:bg-stone-100 transition-colors"
        @click="menuOpen = !menuOpen"
      >
        <span
          class="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-semibold flex-shrink-0 bg-[var(--accent-50)] text-[var(--accent-700)] ring-1 ring-[var(--accent-200)]/60"
        >{{ initials }}</span>
        <div class="text-start leading-tight min-w-0 flex-1">
          <div class="text-[12px] font-semibold text-stone-900 truncate">{{ fullName }}</div>
          <div class="text-[10px] text-stone-500 truncate">{{ t(`roles.${role}`) }}</div>
        </div>
        <Icon name="chevron-up" :size="13" class="text-stone-400 flex-shrink-0" />
      </button>

      <!-- Role menu -->
      <div
        v-if="menuOpen"
        class="absolute bottom-full mb-1.5 inset-x-2 bg-white rounded-xl shadow-floating ring-1 ring-stone-200/70 overflow-hidden py-1 animate-menu z-40"
      >
        <div class="px-3 pt-2 pb-1.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">
          {{ t("nav.viewAs", "View as role") }}
        </div>
        <button
          v-for="r in roles"
          :key="r"
          type="button"
          class="w-full flex items-center gap-2.5 px-2.5 py-1.5 mx-1 rounded-md text-start"
          :class="r === role ? 'bg-stone-100' : 'hover:bg-stone-50'"
          style="width: calc(100% - 0.5rem)"
          @click="pickRole(r)"
        >
          <span
            class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            :class="r === role ? 'bg-white text-[var(--accent-700)] ring-1 ring-stone-200' : 'bg-stone-100 text-stone-500'"
          >
            <Icon :name="roleIcon(r)" :size="14" />
          </span>
          <div class="min-w-0 flex-1 leading-tight">
            <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ t(`roles.${r}`) }}</div>
          </div>
          <Icon v-if="r === role" name="check" :size="14" class="text-[var(--accent-600)] flex-shrink-0" />
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import InstallApp from "@/components/ui/InstallApp.vue";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { navFor } from "@/lib/roles";

defineEmits(["open-search"]);

// Served by Frappe from the app's public/ dir; bound (not a static src) so vite
// doesn't try to resolve it at build time.
const logoSrc = "/assets/logistics_portal/justyol-logo.png";
const { t, locale, setLocale } = useI18n();
const langs = [{ v: "en", l: "EN" }, { v: "fr", l: "FR" }, { v: "ar", l: "ع" }];
const { role, roles, fullName, hiddenPages, setActiveRole } = useAuth();
const route = useRoute();
const menuOpen = ref(false);

const nav = computed(() => navFor(role.value, hiddenPages.value));
const initials = computed(() =>
  (fullName.value || "?").split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase()
);

const ROLE_ICON = {
  manager: "gauge",
  dispatcher: "layers",
  picker: "package",
  packer: "tag",
  returns: "rotate-ccw",
};
function roleIcon(r) {
  return ROLE_ICON[r] || "user";
}

function isActive(item) {
  // Active when the current route matches; the first nav item pointing at a
  // shared fallback route wins visually via route-name match.
  return route.name === item.to;
}

function pickRole(r) {
  setActiveRole(r);
  menuOpen.value = false;
}
</script>
