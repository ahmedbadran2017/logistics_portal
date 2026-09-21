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

    <!-- Lang switcher. Hidden on a PDA-sized screen: the pills are 24px and a
         gloved thumb cannot hit them, the bar is only 52px tall so they cannot
         grow, and language is set once and never touched again. It moves into
         the menu drawer, where it has room to be a real target. -->
    <div class="hidden sm:inline-flex lp-lang items-center gap-0.5 p-0.5 bg-stone-100/80 rounded-lg">
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

    <!-- Hand to customer service. Parked beside the bell on purpose: the
         same icon, in the same corner, on every screen. Ahmed, 2026-09-21 —
         it has to be reachable without hunting for it. The two places it
         used to live were panels buried inside two of the eight surfaces,
         and in the four days they existed no human filed anything. -->
    <!-- When the page underneath is showing ONE order, this stops being a
         generic icon and says what it is about to do. It always knew the
         order — setCsContext publishes it from the workspace, the order page
         and rescue — it just never said so, and a speech bubble parked next
         to a bell reads as "notifications", not "hand this customer's
         problem to CS". That is the whole reason it went unused: the fix is
         to make the one control speak, not to add a second one beside it. -->
    <button
      v-if="canRaise"
      type="button"
      :title="csOrder ? t('cs.quickFor').replace('{o}', csOrder) : t('cs.quickTitle')"
      :aria-label="csOrder ? t('cs.quickFor').replace('{o}', csOrder) : t('cs.quickTitle')"
      class="h-8 rounded-md text-violet-600 flex items-center justify-center transition-all"
      :class="csOrder
        ? 'gap-1.5 px-2.5 bg-violet-50 ring-1 ring-violet-200 hover:bg-violet-100'
        : 'w-8 hover:bg-violet-50 hover:text-violet-800'"
      @click="$emit('open-cs')"
    >
      <Icon name="message-circle" :size="16" class="shrink-0" />
      <!-- Held back below md: the header is 52px and the label would push
           the clock and the language pills off a laptop at a narrow window.
           The tooltip carries the same sentence at every width. -->
      <!-- SAL-ORD-2026-03498 is eighteen characters; without a ceiling it
           pushes the clock and the language pills off a 13-inch screen. -->
      <span v-if="csOrder"
            class="hidden md:inline-flex items-baseline gap-1 text-[11.5px] font-semibold
                   max-w-[190px] overflow-hidden">
        <span class="shrink-0">{{ t('cs.quickShort') }}</span>
        <span class="font-mono opacity-70 truncate" dir="ltr">{{ csOrder }}</span>
      </span>
    </button>

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
      :title="theme === 'dark' ? t('common.themeLight') : t('common.themeDark')"
      :aria-label="theme === 'dark' ? t('common.themeLight') : t('common.themeDark')"
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
import { homeRouteFor, navItemsFor } from "@/lib/roles";
import { IS_CC, SURFACE } from "@/lib/portal";
import { useCsContext } from "@/composables/useCsContext";

defineProps({ unread: { type: Number, default: 0 } });
defineEmits(["toggle-menu", "open-notif", "open-cs"]);


const route = useRoute();
const { role, hiddenPages } = useAuth();
// Every lane may hand a customer's problem to CS — that is the whole point
// of the change. Only a session with no portal role at all is left out.
const canRaise = computed(() => !!role.value);
// What the page underneath is looking at. Cleared on every navigation by the
// app shell, so the label can never name a customer the agent has left.
const { csContext } = useCsContext();
const csOrder = computed(() => csContext.value?.order || "");
const { t, locale, setLocale } = useI18n();
const { theme, toggle } = useTheme();

const langs = [
  { v: "en", l: "EN" },
  { v: "fr", l: "FR" },
  { v: "ar", l: "ع" },
];

// Current page label: the sidebar's own label for this route, so the bar and
// the sidebar never disagree; a lowercase nav alias for pages outside the nav.
const pageLabel = computed(() => {
  const name = route.name || homeRouteFor(role.value, undefined, SURFACE);
  const item = navItemsFor(role.value, hiddenPages.value, SURFACE).find((i) => i.to === name);
  if (item) return t(item.label);
  return t(`nav.${String(name).toLowerCase()}`, String(name));
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
