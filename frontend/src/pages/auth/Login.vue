<template>
  <div class="min-h-screen bg-bg flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="text-4xl mb-2">📦</div>
        <h1 class="text-h1 text-content">{{ t("brand") }}</h1>
        <p class="text-sm text-content-3 mt-1">Warehouse floor operations</p>
      </div>

      <form class="lp-card-pad space-y-4" @submit.prevent="submit">
        <div>
          <label class="label">Email</label>
          <input v-model="usr" type="email" class="input" autocomplete="username" required />
        </div>
        <div>
          <label class="label">Password</label>
          <input v-model="pwd" type="password" class="input" autocomplete="current-password" required />
        </div>
        <p v-if="error" class="text-sm text-danger flex items-center gap-1.5">
          <Icon name="alert-triangle" :size="15" /> {{ error }}
        </p>
        <button class="btn-primary w-full" :disabled="loading">
          {{ loading ? t("common.loading") : "Sign in" }}
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

const router = useRouter();
const route = useRoute();
const { login } = useAuth();
const { t, locale, setLocale } = useI18n();
const { theme, toggle } = useTheme();

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
    error.value = "Invalid email or password.";
  } finally {
    loading.value = false;
  }
}
const order = ["en", "fr", "ar"];
const cycleLocale = () => setLocale(order[(order.indexOf(locale.value) + 1) % order.length]);
</script>
