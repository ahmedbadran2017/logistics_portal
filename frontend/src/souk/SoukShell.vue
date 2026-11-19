<template>
  <div class="souk-root h-[100dvh] flex overflow-hidden bg-[rgb(var(--bg))]" :data-tabs="tabs.length ? 1 : 0">
    <!-- ── Sidebar (desktop) ─────────────────────────────────────────── -->
    <aside class="hidden lg:flex w-[244px] flex-shrink-0 flex-col bg-white border-e border-stone-200">
      <div class="px-5 pt-5 pb-4">
        <div class="flex items-center gap-2.5">
          <img :src="logoSrc" alt="Justyol" class="h-[15px]" />
          <span class="h-4 w-px bg-stone-200" />
          <span class="text-[13px] font-semibold text-[var(--accent-700)]">{{ t('nav.soukPortalShort') }}</span>
        </div>
      </div>

      <nav class="flex-1 overflow-y-auto px-3 pb-4 space-y-5">
        <div v-for="group in nav" :key="group.section">
          <div class="px-2 mb-1.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-500">{{ t(group.section) }}</div>
          <div class="space-y-px">
            <template v-for="item in group.items" :key="item.label">
              <a v-if="item.href" :href="item.href"
                 class="flex items-center gap-2.5 px-2 py-[7px] rounded-lg text-[14px] font-medium text-stone-600 hover:bg-stone-100 hover:text-stone-900 group">
                <Icon :name="item.icon" :size="16" class="text-stone-500 group-hover:text-stone-600" />
                <span class="flex-1 truncate">{{ t(item.label) }}</span>
                <Icon name="external-link" :size="13" class="text-stone-300" />
              </a>
              <router-link v-else :to="{ name: item.to }"
                           class="flex items-center gap-2.5 px-2 py-[7px] rounded-lg text-[14px] font-medium transition-colors group"
                           :class="isActive(item) ? 'bg-[var(--accent-50)] text-[var(--accent-700)]' : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900'">
                <Icon :name="item.icon" :size="16"
                      :class="isActive(item) ? 'text-[var(--accent-600)]' : 'text-stone-500 group-hover:text-stone-600'" />
                <span class="flex-1 truncate">{{ t(item.label) }}</span>
              </router-link>
            </template>
          </div>
        </div>
      </nav>

      <div class="p-3 border-t border-stone-100">
        <button type="button" class="w-full flex items-center gap-2.5 p-2 rounded-lg hover:bg-stone-50 text-start" @click="menu = !menu">
          <span class="w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] text-[12px] font-bold flex items-center justify-center flex-shrink-0">{{ initials }}</span>
          <span class="min-w-0 flex-1 leading-tight">
            <span class="block text-[13px] font-semibold text-stone-900 truncate">{{ fullName }}</span>
            <span class="block text-[11px] text-stone-500 truncate">{{ t(`roles.${role}`, role) }}</span>
          </span>
          <Icon name="chevron-down" :size="13" class="text-stone-500" />
        </button>
      </div>
    </aside>

    <!-- ── Main column ──────────────────────────────────────────────── -->
    <div class="flex-1 flex flex-col min-w-0">
      <div v-if="viewAs" class="flex items-center gap-2 px-4 py-1.5 bg-violet-600 text-white text-[13px] font-semibold">
        <Icon name="user" :size="13" />
        <span class="truncate">{{ t('nav.viewingAs', 'Viewing as') }} {{ viewAs.fullName }} · {{ t(`roles.${viewAs.role}`, viewAs.role) }}</span>
        <button class="ms-auto h-6 px-2.5 rounded-md bg-white/20 hover:bg-white/30 text-[12px] font-bold" @click="setViewAs(null)">
          {{ t('nav.exitViewAs', 'Exit') }}
        </button>
      </div>

      <!-- No line: what the buyer enters is kept on the phone and sent when
           it returns (lib/soukOutbox). Say so, or they will enter it twice. -->
      <div v-if="!outbox.online || waiting || failed"
           class="flex items-center gap-2 px-4 py-1.5 text-[13px] font-semibold"
           :class="failed ? 'bg-rose-600 text-white' : !outbox.online ? 'bg-stone-800 text-white' : 'bg-amber-100 text-amber-900'">
        <Icon :name="!outbox.online ? 'wifi-off' : failed ? 'alert-triangle' : 'upload-cloud'" :size="14" />
        <span class="truncate">
          <template v-if="!outbox.online">{{ t('souk.offline.banner') }}</template>
          <template v-else-if="failed">{{ t('souk.offline.failed').replace('{n}', failed) }}</template>
          <template v-else>{{ t('souk.offline.sending').replace('{n}', waiting) }}</template>
        </span>
        <span v-if="waiting && !outbox.online" class="ms-auto shrink-0 rounded-full bg-white/15 px-2 py-0.5 text-[12px]">
          {{ t('souk.offline.saved').replace('{n}', waiting) }}
        </span>
        <button v-if="failed" type="button" class="ms-auto shrink-0 h-6 px-2.5 rounded-md bg-white/20 text-[12px] font-bold"
                @click="queueOpen = true">{{ t('souk.offline.see') }}</button>
      </div>

      <!-- A deploy shipped a new version: one tap, never mid-purchase by force. -->
      <button v-if="pwa.updated" type="button"
              class="flex items-center justify-center gap-2 px-4 py-2 bg-[var(--accent-600)] text-white text-[13px] font-semibold"
              @click="reload">
        <Icon name="refresh-cw" :size="14" /> {{ t('souk.pwa.updated') }}
      </button>

      <header class="souk-glass souk-safe-top flex-shrink-0 border-b border-stone-200 relative z-10">
       <div class="h-14 flex items-center gap-3 px-4 sm:px-6">
        <!-- On a phone the brand rides the header; the sidebar has it on a desk. -->
        <div class="lg:hidden flex items-center gap-2 min-w-0">
          <img :src="logoSrc" alt="Justyol" class="h-[13px]" />
          <span class="text-[12px] font-semibold text-[var(--accent-700)] bg-[var(--accent-50)] rounded-full px-2 py-0.5">{{ t('nav.soukPortalShort') }}</span>
        </div>
        <h1 class="hidden lg:block text-[15px] font-semibold text-stone-900 truncate">{{ title }}</h1>

        <div class="ms-auto flex items-center gap-1">
          <div class="hidden sm:flex items-center rounded-lg ring-1 ring-stone-200 p-0.5">
            <button v-for="l in LOCALES" :key="l.k" type="button"
                    class="h-7 min-w-[30px] px-2 rounded-md text-[12px] font-semibold transition-colors"
                    :class="locale === l.k ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-900'"
                    @click="setLocale(l.k)">{{ l.label }}</button>
          </div>
          <button type="button" class="hidden sm:flex w-9 h-9 rounded-lg items-center justify-center text-stone-500 hover:bg-stone-100"
                  :title="theme === 'dark' ? 'Light' : 'Dark'" @click="toggle">
            <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="17" />
          </button>
          <button v-if="pwa.canInstall || pwa.ios" type="button"
                  class="h-9 ps-2.5 pe-3 rounded-full bg-[var(--accent-600)] text-white text-[13px] font-semibold flex items-center gap-1.5"
                  @click="askInstall">
            <Icon name="download" :size="14" /> {{ t('souk.pwa.install') }}
          </button>
          <button type="button" class="lg:hidden w-10 h-10 rounded-full bg-[var(--accent-50)] text-[var(--accent-700)] text-[13px] font-bold flex items-center justify-center ring-2 ring-white"
                  @click="menu = !menu">{{ initials }}</button>
        </div>
       </div>
      </header>

      <main class="flex-1 overflow-y-auto overscroll-contain" :class="tabs.length ? 'pb-[76px] lg:pb-0' : ''">
        <router-view v-slot="{ Component }">
          <transition name="souk-page" appear>
            <component :is="Component" :key="$route.name + JSON.stringify($route.params)" />
          </transition>
        </router-view>
      </main>

      <!-- ── Bottom tabs (phone / tablet) ─────────────────────────────── -->
      <nav v-if="tabs.length"
           class="souk-glass lg:hidden fixed bottom-0 inset-x-0 z-30 border-t border-stone-200 flex items-stretch"
           style="height: calc(64px + env(safe-area-inset-bottom)); padding-bottom: env(safe-area-inset-bottom)">
        <router-link v-for="item in tabs" :key="item.to" :to="{ name: item.to }"
                     class="flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors"
                     :class="isActive(item) ? 'text-[var(--accent-700)]' : 'text-stone-500'"
                     @click="more = false">
          <span class="h-8 w-14 rounded-full flex items-center justify-center transition-colors"
                :class="isActive(item) ? 'bg-[var(--accent-100)]' : ''">
            <Icon :name="item.icon" :size="20" :stroke-width="isActive(item) ? 2.1 : 1.75" />
          </span>
          <span class="text-[11px] truncate max-w-full px-1" :class="isActive(item) ? 'font-bold' : 'font-medium'">{{ t(item.label) }}</span>
        </router-link>
        <button v-if="moreItems.length" type="button"
                class="flex-1 flex flex-col items-center justify-center gap-0.5"
                :class="more || moreItems.some(isActive) ? 'text-[var(--accent-700)]' : 'text-stone-500'"
                @click="more = !more">
          <span class="h-8 w-14 rounded-full flex items-center justify-center" :class="more || moreItems.some(isActive) ? 'bg-[var(--accent-100)]' : ''">
            <Icon name="menu" :size="20" />
          </span>
          <span class="text-[11px] font-medium">{{ t('nav.more') }}</span>
        </button>
      </nav>
      <div v-if="more" class="lg:hidden fixed inset-0 z-20" @click="more = false">
        <div class="absolute inset-0 bg-stone-900/30" />
        <div class="absolute inset-x-0 bg-white rounded-t-2xl p-4 ring-1 ring-stone-200" style="bottom: calc(64px + env(safe-area-inset-bottom))" @click.stop>
          <div class="grid grid-cols-4 gap-3">
            <template v-for="item in moreItems" :key="item.to || item.href">
              <a v-if="item.href" :href="item.href" class="flex flex-col items-center gap-1.5 py-2 rounded-xl text-stone-600 active:bg-stone-100">
                <Icon :name="item.icon" :size="22" />
                <span class="text-[11px] font-semibold text-center leading-tight">{{ t(item.label) }}</span>
              </a>
              <router-link v-else :to="{ name: item.to }" class="flex flex-col items-center gap-1.5 py-2 rounded-xl"
                           :class="isActive(item) ? 'bg-[var(--accent-50)] text-[var(--accent-700)]' : 'text-stone-600 active:bg-stone-100'"
                           @click="more = false">
                <Icon :name="item.icon" :size="22" />
                <span class="text-[11px] font-semibold text-center leading-tight">{{ t(item.label) }}</span>
              </router-link>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- ── iPhone: no install prompt exists, so say where the button is ── -->
    <div v-if="iosHint" class="fixed inset-0 z-40 flex items-end justify-center" @click="iosHint = false">
      <div class="absolute inset-0 bg-stone-900/30" />
      <div class="relative w-full bg-white rounded-t-3xl p-5 shadow-2xl" style="padding-bottom: max(1.25rem, env(safe-area-inset-bottom))" @click.stop>
        <div class="flex items-center gap-3">
          <img :src="iconSrc" alt="" class="w-12 h-12 rounded-xl" />
          <div class="min-w-0">
            <div class="text-[15px] font-bold text-stone-900">{{ t('souk.pwa.iosTitle') }}</div>
            <div class="text-[13px] text-stone-500">{{ t('souk.pwa.iosWhy') }}</div>
          </div>
        </div>
        <ol class="mt-4 space-y-2 text-[14px] text-stone-700">
          <li class="flex items-center gap-2"><span class="w-6 h-6 rounded-full bg-[var(--accent-50)] text-[var(--accent-700)] text-[13px] font-bold flex items-center justify-center">1</span>{{ t('souk.pwa.iosStep1') }}</li>
          <li class="flex items-center gap-2"><span class="w-6 h-6 rounded-full bg-[var(--accent-50)] text-[var(--accent-700)] text-[13px] font-bold flex items-center justify-center">2</span>{{ t('souk.pwa.iosStep2') }}</li>
        </ol>
        <div class="mt-5 flex gap-2">
          <button type="button" class="flex-1 h-12 rounded-xl bg-[var(--accent-600)] text-white text-[15px] font-semibold" @click="iosHint = false">{{ t('souk.pwa.ok') }}</button>
          <button type="button" class="h-12 px-4 rounded-xl ring-1 ring-stone-200 text-stone-600 text-[14px] font-semibold" @click="notNow">{{ t('souk.pwa.notNow') }}</button>
        </div>
      </div>
    </div>

    <!-- ── What is waiting on the phone ─────────────────────────────── -->
    <div v-if="queueOpen" class="fixed inset-0 z-40 flex items-end sm:items-center justify-center" @click="queueOpen = false">
      <div class="absolute inset-0 bg-stone-900/30" />
      <div class="relative w-full sm:max-w-[420px] bg-white rounded-t-2xl sm:rounded-2xl p-4 shadow-2xl max-h-[80dvh] overflow-y-auto" @click.stop>
        <div class="flex items-center mb-3">
          <h3 class="text-[15px] font-bold text-stone-900">{{ t('souk.offline.title') }}</h3>
          <button type="button" class="ms-auto w-9 h-9 rounded-lg flex items-center justify-center text-stone-500 hover:bg-stone-100" @click="queueOpen = false">
            <Icon name="x" :size="17" />
          </button>
        </div>
        <p v-if="!outbox.jobs.length" class="text-[14px] text-stone-500">{{ t('souk.offline.empty') }}</p>
        <div v-for="j in outbox.jobs" :key="j.id" class="py-2.5 border-t border-stone-100 first:border-0">
          <div class="flex items-center gap-2">
            <Icon :name="j.failed ? 'alert-triangle' : 'clock'" :size="15" :class="j.failed ? 'text-rose-600' : 'text-amber-600'" />
            <span class="text-[14px] font-semibold text-stone-900 truncate">{{ j.label || t('souk.offline.kind.' + j.kind, j.kind) }}</span>
            <span class="ms-auto text-[12px] text-stone-500 shrink-0">{{ new Date(j.created).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}</span>
          </div>
          <p v-if="j.error" class="mt-1 text-[13px]" :class="j.failed ? 'text-rose-700' : 'text-stone-500'">{{ j.error }}</p>
          <div v-if="j.failed" class="mt-2 flex gap-2">
            <button type="button" class="h-11 px-4 rounded-xl bg-[var(--accent-600)] text-white text-[14px] font-semibold" @click="retryJob(j.id)">{{ t('souk.offline.retry') }}</button>
            <button type="button" class="h-11 px-4 rounded-xl ring-1 ring-stone-200 text-stone-600 text-[14px] font-semibold" @click="discardJob(j.id)">{{ t('souk.offline.discard') }}</button>
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
          <div class="text-[13px] font-semibold text-stone-900 truncate">{{ fullName }}</div>
          <div class="text-[11px] text-stone-500 truncate">{{ user }}</div>
        </div>
        <!-- Phones have no room for the language pills in the header. -->
        <div class="sm:hidden flex items-center gap-1 px-3 py-2 border-b border-stone-100">
          <Icon name="globe" :size="14" class="text-stone-500 me-1" />
          <button v-for="l in LOCALES" :key="l.k" type="button"
                  class="h-7 flex-1 rounded-md text-[12px] font-semibold"
                  :class="locale === l.k ? 'bg-stone-900 text-white' : 'text-stone-500 bg-stone-50'"
                  @click="setLocale(l.k)">{{ l.label }}</button>
        </div>
        <!-- …nor for the theme switch: a market phone rarely flips it. -->
        <button type="button" class="sm:hidden w-full flex items-center gap-2.5 px-3 py-2 text-start hover:bg-stone-50 border-b border-stone-100"
                @click="toggle">
          <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="14" class="text-stone-500" />
          <span class="text-[13px] text-stone-800">{{ theme === 'dark' ? t('common.themeLight') : t('common.themeDark') }}</span>
        </button>
        <template v-if="roles.length > 1">
          <button v-for="r in roles" :key="r" type="button"
                  class="w-full flex items-center gap-2 px-3 py-1.5 text-start hover:bg-stone-50"
                  @click="setActiveRole(r); menu = false">
            <span class="text-[13px] text-stone-800 flex-1">{{ t(`roles.${r}`, r) }}</span>
            <Icon v-if="r === role" name="check" :size="14" class="text-[var(--accent-600)]" />
          </button>
        </template>
        <button type="button" class="w-full flex items-center gap-2.5 px-3 py-2 text-start hover:bg-rose-50 text-rose-600 mt-0.5" @click="doLogout">
          <Icon name="log-out" :size="14" />
          <span class="text-[13px] font-semibold">{{ t('common.logout') }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { useTheme } from "@/composables/useTheme";
import { navFor } from "@/lib/roles";
import { outbox, startOutbox, retry, discard } from "@/lib/soukOutbox";
import { pwa, install, dismissInstall, forgetOffline } from "@/lib/soukPwa";
import { useToast } from "@/composables/useToast";

const route = useRoute();
const { user, fullName, role, roles, hiddenPages, logout, setActiveRole, viewAs, setViewAs } = useAuth();
const { t, locale, setLocale } = useI18n();
const { theme, toggle } = useTheme();

const logoSrc = "/assets/logistics_portal/justyol-logo.png";
const iconSrc = "/assets/logistics_portal/icon-192.png";
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
const queueOpen = ref(false);
const iosHint = ref(false);
async function askInstall() {
  if (pwa.canInstall) { await install(); return; }
  iosHint.value = true;
}
function notNow() { iosHint.value = false; dismissInstall(); }
function reload() { window.location.reload(); }
const waiting = computed(() => outbox.jobs.filter((j) => !j.failed).length);
const failed = computed(() => outbox.jobs.filter((j) => j.failed).length);
onMounted(startOutbox);
async function retryJob(id) {
  try { await retry(id); } catch (e) { useToast().warn(t("souk.failed"), String(e.message || e)); }
}
async function discardJob(id) {
  if (!window.confirm(t("souk.offline.discardConfirm"))) return;
  await discard(id);
}
watch(() => route.fullPath, () => { menu.value = false; more.value = false; });

async function doLogout() {
  menu.value = false;
  forgetOffline();
  try { await logout(); } catch (_) { /* clear locally regardless */ }
  window.location.href = "/souk/login";
}
</script>
