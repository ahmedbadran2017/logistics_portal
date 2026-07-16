<template>
  <header
    class="h-[52px] shrink-0 bg-white/80 backdrop-blur-sm border-b border-stone-200/70 flex items-center px-4 sm:px-5 gap-3"
  >
    <!-- Mobile hamburger -->
    <button
      type="button"
      :title="t('common.menu')"
      :aria-label="t('common.menu')"
      class="lg:hidden w-8 h-8 rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-900 flex items-center justify-center"
      @click="$emit('toggle-menu')"
    >
      <Icon name="menu" :size="18" />
    </button>

    <!-- Page label -->
    <div class="flex items-center gap-2 min-w-0">
      <span class="text-[13px] font-medium text-stone-900 truncate">{{ pageLabel }}</span>
    </div>

    <div class="flex-1" />

    <!-- Live clock -->
    <div class="hidden md:inline-flex items-center gap-1.5 text-[11.5px] font-medium text-stone-500 tabular-nums">
      <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
      {{ t("common.live", "Live") }} {{ clock }}
    </div>

    <!-- Lang switcher -->
    <div class="inline-flex items-center gap-0.5 p-0.5 bg-stone-100/80 rounded-lg">
      <button
        v-for="opt in langs"
        :key="opt.v"
        type="button"
        class="min-w-[26px] h-[24px] px-1.5 text-[11.5px] font-semibold rounded-md transition-all"
        :class="locale === opt.v
          ? 'bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]'
          : 'text-stone-500 hover:text-stone-800'"
        @click="setLocale(opt.v)"
      >
        {{ opt.l }}
      </button>
    </div>

    <!-- Notification bell -->
    <button
      type="button"
      :title="t('notif.title')"
      :aria-label="t('notif.title')"
      class="relative w-8 h-8 rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-900 flex items-center justify-center"
      @click="$emit('open-notif')"
    >
      <Icon name="bell" :size="16" />
      <span
        v-if="unread > 0"
        class="absolute top-1 end-1 min-w-[15px] h-[15px] px-1 rounded-full bg-[var(--accent-600)] text-white text-[9px] font-bold flex items-center justify-center ring-2 ring-white tabular-nums"
      >{{ unread }}</span>
    </button>

    <!-- Theme toggle -->
    <button
      type="button"
      class="w-8 h-8 rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-900 flex items-center justify-center"
      :title="theme === 'dark' ? 'Light' : 'Dark'"
      @click="toggle"
    >
      <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="16" />
    </button>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { useTheme } from "@/composables/useTheme";
import { homeRouteFor } from "@/lib/roles";

defineProps({ unread: { type: Number, default: 0 } });
defineEmits(["toggle-menu", "open-notif"]);

const route = useRoute();
const { role } = useAuth();
const { t, locale, setLocale } = useI18n();
const { theme, toggle } = useTheme();

const langs = [
  { v: "en", l: "EN" },
  { v: "fr", l: "FR" },
  { v: "ar", l: "ع" },
];

// Current page label from route meta/name, falling back to the role home.
const pageLabel = computed(() => {
  const name = route.name || homeRouteFor(role.value);
  const key = `nav.${String(name).toLowerCase()}`;
  return t(key, String(name));
});

// Live clock (HH:MM:SS)
const clock = ref(fmt(new Date()));
let timer = null;
function fmt(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
onMounted(() => {
  timer = setInterval(() => { clock.value = fmt(new Date()); }, 1000);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>
