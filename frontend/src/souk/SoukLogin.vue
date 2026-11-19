<template>
  <div class="min-h-[100dvh] flex bg-[rgb(var(--bg))]">
    <!-- The story panel (desktop): what this app is for, in one look. -->
    <div class="hidden lg:flex w-[46%] max-w-[620px] flex-col justify-between p-10 text-white relative overflow-hidden"
         style="background: #1c1917">
      <div class="absolute -bottom-24 -end-24 w-[360px] h-[360px] rounded-full blur-3xl opacity-20 bg-[#c4492a] pointer-events-none" />
      <span class="inline-flex items-center self-start h-11 px-4 rounded-xl bg-white">
        <img :src="logoSrc" alt="Justyol" class="h-4" />
      </span>
      <div class="relative">
        <span class="inline-flex items-center gap-1.5 text-[11.5px] font-semibold text-[#f6ccbf] bg-white/10 ring-1 ring-white/15 rounded-full px-3 py-1">
          <span class="w-1.5 h-1.5 rounded-full bg-[#e17f62]" />{{ t('nav.soukPortalShort') }}
        </span>
        <h2 class="mt-5 text-[30px] font-bold leading-tight tracking-[-0.01em]">{{ t('auth.soukHero') }}</h2>
        <ol class="mt-7 space-y-3.5">
          <li v-for="(s, i) in STEPS" :key="s.k" class="flex items-center gap-3">
            <span class="w-8 h-8 rounded-lg bg-white/10 ring-1 ring-white/15 flex items-center justify-center flex-shrink-0">
              <Icon :name="s.icon" :size="15" class="text-[#eea894]" />
            </span>
            <span class="text-[13.5px] text-white/85"><span class="text-white/40 me-1.5 tabular-nums">{{ i + 1 }}</span>{{ t(s.k) }}</span>
          </li>
        </ol>
      </div>
      <div class="text-[11.5px] text-white/40">© {{ year }} Justyol</div>
    </div>

    <!-- The form -->
    <div class="flex-1 flex flex-col">
      <div class="flex justify-end p-4">
        <div class="flex items-center rounded-lg ring-1 ring-stone-200 bg-white p-0.5">
          <button v-for="l in LOCALES" :key="l.k" type="button"
                  class="h-7 min-w-[34px] px-2 rounded-md text-[11.5px] font-semibold"
                  :class="locale === l.k ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-900'"
                  @click="setLocale(l.k)">{{ l.label }}</button>
        </div>
        <button type="button" class="ms-1 w-9 h-9 rounded-lg flex items-center justify-center text-stone-500 hover:bg-stone-100" @click="toggle">
          <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="17" />
        </button>
      </div>

      <div class="flex-1 flex items-center justify-center px-5 pb-16">
        <div class="w-full max-w-[360px]">
          <div class="lg:hidden mb-8 flex items-center gap-2">
            <img :src="logoSrc" alt="Justyol" class="h-4" />
            <span class="text-[11.5px] font-semibold text-[var(--accent-700)] bg-[var(--accent-50)] rounded-full px-2 py-0.5">{{ t('nav.soukPortalShort') }}</span>
          </div>
          <h1 class="text-[24px] font-bold text-stone-900 tracking-[-0.01em]">{{ t('auth.soukWelcome') }}</h1>
          <p class="text-[13px] text-stone-500 mt-1">{{ t('auth.soukSub') }}</p>

          <form class="mt-7 space-y-4" @submit.prevent="submit">
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
            <button class="btn-primary w-full !h-11 !rounded-xl" :disabled="loading">
              {{ loading ? t("common.loading") : t('auth.signIn') }}
            </button>
          </form>
        </div>
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

const router = useRouter();
const route = useRoute();
const { login } = useAuth();
const { t, locale, setLocale } = useI18n();
const { theme, toggle } = useTheme();

const logoSrc = "/assets/logistics_portal/justyol-logo.png";
const LOCALES = [{ k: "en", label: "EN" }, { k: "fr", label: "FR" }, { k: "ar", label: "ع" }];
const year = new Date().getFullYear();
// The cycle the app runs, the way the team says it.
const STEPS = [
  { k: "nav.soukBuy", icon: "shopping-bag" },
  { k: "nav.soukReceive", icon: "package-check" },
  { k: "nav.soukStudio", icon: "image" },
  { k: "nav.soukContent", icon: "notebook-pen" },
  { k: "nav.soukReview", icon: "clipboard-check" },
];

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
</script>
