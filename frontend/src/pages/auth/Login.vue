<template>
  <div class="min-h-screen bg-bg flex items-center justify-center p-4 relative overflow-hidden">
    <!-- portal-tinted glow: violet for the contact center, warm for the floor -->
    <div class="absolute -top-32 -end-32 w-[420px] h-[420px] rounded-full blur-3xl opacity-20 pointer-events-none"
         :class="IS_CC ? 'bg-violet-500' : 'bg-orange-500'" />
    <div class="absolute -bottom-40 -start-32 w-[380px] h-[380px] rounded-full blur-3xl opacity-10 pointer-events-none"
         :class="IS_CC ? 'bg-fuchsia-400' : 'bg-amber-400'" />

    <div class="w-full max-w-sm relative">
      <div class="text-center mb-8">
        <!-- the real logo, on a white chip so it survives dark mode -->
        <span class="inline-flex items-center justify-center h-14 px-6 rounded-2xl bg-white shadow-lg ring-1 ring-black/5 mb-4">
          <img :src="logoSrc" alt="Justyol" class="h-5" />
        </span>
        <h1 class="text-h1 text-content">{{ t('brand') }}</h1>
        <p class="text-sm text-content-3 mt-1">{{ IS_CC ? t('auth.ccSub') : t('auth.floorSub') }}</p>
        <span v-if="IS_CC"
              class="inline-flex items-center gap-1.5 mt-3 text-[11px] font-semibold text-violet-500 bg-violet-500/10 rounded-full px-3 py-1 ring-1 ring-violet-500/20">
          <Icon name="phone" :size="11" />Contact Center
        </span>
      </div>

      <form class="lp-card-pad space-y-4" @submit.prevent="submit">
        <div>
          <label class="label">{{ t('auth.email') }}</label>
          <input v-model="usr" type="email" class="input" autocomplete="username" required />
        </div>
        <div>
          <label class="label">{{ t('auth.password') }}</label>
          <input v-model="pwd" type="password" class="input" autocomplete="current-password" required />
        </div>
        <p v-if="error" class="text-sm text-danger flex items-center gap-1.5">
          <Icon name="alert-triangle" :size="15" /> {{ error }}
        </p>
        <button class="w-full h-11 rounded-xl font-semibold text-white transition-colors disabled:opacity-50"
                :class="IS_CC ? 'bg-violet-600 hover:bg-violet-700' : 'btn-primary !h-11'"
                :disabled="loading">
          {{ loading ? t("common.loading") : t('auth.signIn') }}
        </button>
      </form>

      <div class="flex items-center justify-center gap-3 mt-6 text-content-3">
        <button class="btn-ghost !p-2" @click="cycleLocale"><Icon name="globe" :size="18" /></button>
        <button class="btn-ghost !p-2" @click="toggle"><Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="18" /></button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { useTheme } from "@/composables/useTheme";
import { IS_CC } from "@/lib/portal";

const router = useRouter();
const route = useRoute();
const { login } = useAuth();
const { t, locale, setLocale } = useI18n();
const { theme, toggle } = useTheme();

// Served by Frappe from the app's public/ dir (same as the sidebar lockup).
const logoSrc = "/assets/logistics_portal/justyol-logo.png";

const usr = ref("");
const pwd = ref("");
const loading = ref(false);
const error = ref("");

async function submit() {
  loading.value = true;
  error.value = "";
  try {
    await login(usr.value, pwd.value);
    router.push(route.query.redirect || { name: "Home2" });
  } catch (e) {
    error.value = t("auth.badLogin");
  } finally {
    loading.value = false;
  }
}
const order = ["en", "fr", "ar"];
const cycleLocale = () => setLocale(order[(order.indexOf(locale.value) + 1) % order.length]);
</script>
