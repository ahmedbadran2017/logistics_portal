<template>
  <div class="h-[100dvh] flex overflow-hidden bg-[rgb(var(--bg))]">
    <!-- ── Sidebar (desktop) ─────────────────────────────────────────── -->
    <aside class="hidden lg:flex w-[244px] flex-shrink-0 flex-col bg-white border-e border-stone-200/70">
      <div class="px-5 pt-5 pb-4">
        <div class="flex items-center gap-2.5">
          <img :src="logoSrc" alt="Justyol" class="h-[15px]" />
          <span class="h-4 w-px bg-stone-200" />
          <span class="text-[12.5px] font-semibold text-[var(--accent-700)]">{{ t('nav.soukPortalShort') }}</span>
        </div>
      </div>

      <nav class="flex-1 overflow-y-auto px-3 pb-4 space-y-5">
        <div v-for="group in nav" :key="group.section">
          <div class="px-2 mb-1.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">{{ t(group.section) }}</div>
          <div class="space-y-px">
            <template v-for="item in group.items" :key="item.label">
              <a v-if="item.href" :href="item.href"
                 class="flex items-center gap-2.5 px-2 py-[7px] rounded-lg text-[13px] font-medium text-stone-600 hover:bg-stone-100 hover:text-stone-900 group">
                <Icon :name="item.icon" :size="16" class="text-stone-400 group-hover:text-stone-600" />
                <span class="flex-1 truncate">{{ t(item.label) }}</span>
                <Icon name="external-link" :size="13" class="text-stone-300" />
              </a>
              <router-link v-else :to="{ name: item.to }"
                           class="flex items-center gap-2.5 px-2 py-[7px] rounded-lg text-[13px] font-medium transition-colors group"
                           :class="isActive(item) ? 'bg-[var(--accent-50)] text-[var(--accent-700)]' : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900'">
                <Icon :name="item.icon" :size="16"
                      :class="isActive(item) ? 'text-[var(--accent-600)]' : 'text-stone-400 group-hover:text-stone-600'" />
                <span class="flex-1 truncate">{{ t(item.label) }}</span>
              </router-link>
            </template>
          </div>
        </div>
      </nav>

      <div class="p-3 border-t border-stone-100">
        <button type="button" class="w-full flex items-center gap-2.5 p-2 rounded-lg hover:bg-stone-50 text-start" @click="menu = !menu">
          <span class="w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] text-[11px] font-bold flex items-center justify-center flex-shrink-0">{{ initials }}</span>
          <span class="min-w-0 flex-1 leading-tight">
            <span class="block text-[12.5px] font-semibold text-stone-900 truncate">{{ fullName }}</span>
            <span class="block text-[10.5px] text-stone-500 truncate">{{ t(`roles.${role}`, role) }}</span>
          </span>
          <Icon name="chevron-down" :size="13" class="text-stone-400" />
        </button>
      </div>
    </aside>

    <!-- ── Main column ──────────────────────────────────────────────── -->
    <div class="flex-1 flex flex-col min-w-0">
      <div v-if="viewAs" class="flex items-center gap-2 px-4 py-1.5 bg-violet-600 text-white text-[12px] font-semibold">
        <Icon name="user" :size="13" />
        <span class="truncate">{{ t('nav.viewingAs', 'Viewing as') }} {{ viewAs.fullName }} · {{ t(`roles.${viewAs.role}`, viewAs.role) }}</span>
        <button class="ms-auto h-6 px-2.5 rounded-md bg-white/20 hover:bg-white/30 text-[11px] font-bold" @click="setViewAs(null)">
          {{ t('nav.exitViewAs', 'Exit') }}
        </button>
      </div>

      <header class="h-14 flex-shrink-0 flex items-center gap-3 px-4 sm:px-6 bg-white/90 backdrop-blur border-b border-stone-200/70">
        <!-- On a phone the brand rides the header; the sidebar has it on a desk. -->
        <div class="lg:hidden flex items-center gap-2 min-w-0">
          <img :src="logoSrc" alt="Justyol" class="h-[13px]" />
          <span class="text-[11.5px] font-semibold text-[var(--accent-700)] bg-[var(--accent-50)] rounded-full px-2 py-0.5">{{ t('nav.soukPortalShort') }}</span>
        </div>
        <h1 class="hidden lg:block text-[15px] font-semibold text-stone-900 truncate">{{ title }}</h1>

        <div class="ms-auto flex items-center gap-1">
          <div class="hidden sm:flex items-center rounded-lg ring-1 ring-stone-200 p-0.5">
            <button v-for="l in LOCALES" :key="l.k" type="button"
                    class="h-7 min-w-[30px] px-2 rounded-md text-[11.5px] font-semibold transition-colors"
                    :class="locale === l.k ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-900'"
                    @click="setLocale(l.k)">{{ l.label }}</button>
          </div>
          <button type="button" class="w-9 h-9 rounded-lg flex items-center justify-center text-stone-500 hover:bg-stone-100"
                  :title="theme === 'dark' ? 'Light' : 'Dark'" @click="toggle">
            <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="17" />
          </button>
          <button type="button" class="lg:hidden w-9 h-9 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] text-[11px] font-bold flex items-center justify-center"
                  @click="menu = !menu">{{ initials }}</button>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto overscroll-contain" :class="tabs.length ? 'pb-[76px] lg:pb-0' : ''">
        <router-view v-slot="{ Component }">
          <component :is="Component" :key="$route.name + JSON.stringify($route.params)" />
        </router-view>
      </main>

      <!-- ── Bottom tabs (phone / tablet) ─────────────────────────────── -->
      <nav v-if="tabs.length"
           class="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-white/95 backdrop-blur border-t border-stone-200/70 flex items-stretch h-[64px]"
           style="padding-bottom: env(safe-area-inset-bottom)">
        <router-link v-for="item in tabs" :key="item.to" :to="{ name: item.to }"
                     class="flex-1 flex flex-col items-center justify-center gap-1 transition-colors"
                     :class="isActive(item) ? 'text-[var(--accent-600)]' : 'text-stone-400'"
                     @click="more = false">
          <Icon :name="item.icon" :size="21" />
          <span class="text-[10px] font-medium truncate max-w-full px-1">{{ t(item.label) }}</span>
        </router-link>
        <button v-if="moreItems.length" type="button"
                class="flex-1 flex flex-col items-center justify-center gap-1"
                :class="more || moreItems.some(isActive) ? 'text-[var(--accent-600)]' : 'text-stone-400'"
                @click="more = !more">
          <Icon name="layout-grid" :size="21" />
          <span class="text-[10px] font-medium">{{ t('nav.more') }}</span>
        </button>
      </nav>
      <div v-if="more" class="lg:hidden fixed inset-0 z-20" @click="more = false">
        <div class="absolute inset-0 bg-stone-900/30" />
        <div class="absolute bottom-[64px] inset-x-0 bg-white rounded-t-2xl p-4 shadow-2xl" @click.stop>
          <div class="grid grid-cols-4 gap-3">
            <template v-for="item in moreItems" :key="item.to || item.href">
              <a v-if="item.href" :href="item.href" class="flex flex-col items-center gap-1.5 py-2 rounded-xl text-stone-600 active:bg-stone-100">
                <Icon :name="item.icon" :size="22" />
                <span class="text-[10px] font-semibold text-center leading-tight">{{ t(item.label) }}</span>
              </a>
              <router-link v-else :to="{ name: item.to }" class="flex flex-col items-center gap-1.5 py-2 rounded-xl"
                           :class="isActive(item) ? 'bg-[var(--accent-50)] text-[var(--accent-700)]' : 'text-stone-600 active:bg-stone-100'"
                           @click="more = false">
                <Icon :name="item.icon" :size="22" />
                <span class="text-[10px] font-semibold text-center leading-tight">{{ t(item.label) }}</span>
              </router-link>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Account menu (both layouts) ──────────────────────────────── -->
    <div v-if="menu" class="fixed inset-0 z-40" @click="menu = false">
      <div class="absolute w-[240px] bg-white rounded-xl shadow-floating ring-1 ring-stone-200/70 py-1.5 animate-menu
                  top-14 end-3 lg:top-auto lg:end-auto lg:bottom-[68px] lg:start-3"
           @click.stop>
        <div class="px-3 pt-1.5 pb-2 border-b border-stone-100">
          <div class="text-[12.5px] font-semibold text-stone-900 truncate">{{ fullName }}</div>
          <div class="text-[10.5px] text-stone-500 truncate">{{ user }}</div>
        </div>
        <!-- Phones have no room for the language pills in the header. -->
        <div class="sm:hidden flex items-center gap-1 px-3 py-2 border-b border-stone-100">
          <Icon name="globe" :size="14" class="text-stone-400 me-1" />
          <button v-for="l in LOCALES" :key="l.k" type="button"
                  class="h-7 flex-1 rounded-md text-[11.5px] font-semibold"
                  :class="locale === l.k ? 'bg-stone-900 text-white' : 'text-stone-500 bg-stone-50'"
                  @click="setLocale(l.k)">{{ l.label }}</button>
        </div>
        <template v-if="roles.length > 1">
          <button v-for="r in roles" :key="r" type="button"
                  class="w-full flex items-center gap-2 px-3 py-1.5 text-start hover:bg-stone-50"
                  @click="setActiveRole(r); menu = false">
            <span class="text-[12.5px] text-stone-800 flex-1">{{ t(`roles.${r}`, r) }}</span>
            <Icon v-if="r === role" name="check" :size="14" class="text-[var(--accent-600)]" />
          </button>
        </template>
        <button type="button" class="w-full flex items-center gap-2.5 px-3 py-2 text-start hover:bg-rose-50 text-rose-600 mt-0.5" @click="doLogout">
          <Icon name="log-out" :size="14" />
          <span class="text-[12.5px] font-semibold">{{ t('common.logout') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { useTheme } from "@/composables/useTheme";
import { navFor } from "@/lib/roles";

const route = useRoute();
const { user, fullName, role, roles, hiddenPages, logout, setActiveRole, viewAs, setViewAs } = useAuth();
const { t, locale, setLocale } = useI18n();
const { theme, toggle } = useTheme();

const logoSrc = "/assets/logistics_portal/justyol-logo.png";
const LOCALES = [{ k: "en", label: "EN" }, { k: "fr", label: "FR" }, { k: "ar", label: "ع" }];

const nav = computed(() => navFor(role.value, hiddenPages.value, "souk"));
const items = computed(() => nav.value.flatMap((g) => g.items));

// A product card is opened from the board, so the board stays lit behind it.
const PARENT = { SoukProduct: "SoukBoard" };
function isActive(item) {
  return !!item.to && (route.name === item.to || PARENT[route.name] === item.to);
}

// The phone bar fits five thumbs: four + More when a role has more pages.
const inApp = computed(() => items.value.filter((i) => i.to));
const tabs = computed(() => (inApp.value.length > 5 ? inApp.value.slice(0, 4) : inApp.value));
const moreItems = computed(() => (inApp.value.length > 5
  ? items.value.filter((i) => !tabs.value.includes(i))
  : items.value.filter((i) => i.href)));

const title = computed(() => {
  const want = PARENT[route.name] || route.name;
  const it = items.value.find((i) => i.to === want);
  return it ? t(it.label) : t("nav.soukPortalShort");
});

const initials = computed(() =>
  (fullName.value || "?").split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase());

const menu = ref(false);
const more = ref(false);
watch(() => route.fullPath, () => { menu.value = false; more.value = false; });

async function doLogout() {
  menu.value = false;
  try { await logout(); } catch (_) { /* clear locally regardless */ }
  window.location.href = "/souk/login";
}
</script>
