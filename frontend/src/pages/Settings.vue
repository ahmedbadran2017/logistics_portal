<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[900px] mx-auto">
    <div>
      <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em] flex items-center gap-2">
        <Icon name="settings" :size="20" class="text-[var(--accent-600)]" /> Settings
      </h1>
      <p class="text-[12.5px] text-stone-500 mt-1">Manage your profile and preferences.</p>
    </div>

    <!-- Profile -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5">
      <div class="flex items-center gap-2 mb-4 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
        <Icon name="user" :size="15" /> Profile
      </div>
      <dl class="divide-y divide-stone-100">
        <div class="flex items-center justify-between py-2.5">
          <dt class="text-[12.5px] text-stone-500">Name</dt>
          <dd class="text-[12.5px] font-medium text-stone-900">{{ fullName || '—' }}</dd>
        </div>
        <div class="flex items-center justify-between py-2.5">
          <dt class="text-[12.5px] text-stone-500">Role</dt>
          <dd class="text-[12.5px] font-medium text-stone-900 capitalize">{{ role || '—' }}</dd>
        </div>
        <div class="flex items-center justify-between py-2.5">
          <dt class="text-[12.5px] text-stone-500">Zone</dt>
          <dd class="text-[12.5px] font-medium text-stone-900">{{ zone || '—' }}</dd>
        </div>
        <div class="flex items-center justify-between py-2.5">
          <dt class="text-[12.5px] text-stone-500">Email</dt>
          <dd class="text-[12.5px] font-medium text-stone-900 font-mono tabular-nums">{{ user || '—' }}</dd>
        </div>
      </dl>
    </div>

    <!-- Appearance -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5">
      <div class="flex items-center gap-2 mb-4 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
        <Icon name="sun" :size="15" /> Appearance
      </div>
      <div class="grid grid-cols-2 gap-3">
        <button
          type="button"
          class="rounded-lg ring-1 px-4 py-3 flex items-center justify-center gap-2 text-[13px] font-medium transition-all"
          :class="theme === 'light' ? 'ring-[var(--accent-400)] bg-[var(--accent-50)]/50 text-stone-900' : 'ring-stone-200 text-stone-600 hover:ring-stone-300'"
          @click="set('light')"
        ><Icon name="sun" :size="16" /> Light</button>
        <button
          type="button"
          class="rounded-lg ring-1 px-4 py-3 flex items-center justify-center gap-2 text-[13px] font-medium transition-all"
          :class="theme === 'dark' ? 'ring-[var(--accent-400)] bg-[var(--accent-50)]/50 text-stone-900' : 'ring-stone-200 text-stone-600 hover:ring-stone-300'"
          @click="set('dark')"
        ><Icon name="moon" :size="16" /> Dark</button>
      </div>
    </div>

    <!-- Language -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5">
      <div class="flex items-center gap-2 mb-4 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
        <Icon name="globe" :size="15" /> Language
      </div>
      <div class="grid grid-cols-3 gap-3">
        <button
          v-for="l in langs" :key="l.code"
          type="button"
          class="rounded-lg ring-1 px-4 py-3 text-[13px] font-medium transition-all"
          :class="locale === l.code ? 'ring-[var(--accent-400)] bg-[var(--accent-50)]/50 text-stone-900' : 'ring-stone-200 text-stone-600 hover:ring-stone-300'"
          @click="setLocale(l.code)"
        >{{ l.label }}</button>
      </div>
    </div>

    <!-- Notifications -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5">
      <div class="flex items-center gap-2 mb-4 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
        <Icon name="bell" :size="15" /> Notifications
      </div>
      <ul class="divide-y divide-stone-100">
        <li v-for="n in notifs" :key="n.key" class="flex items-center justify-between py-3 gap-3">
          <div class="min-w-0">
            <div class="text-[12.5px] font-medium text-stone-900">{{ n.label }}</div>
            <div class="text-[11px] text-stone-500">{{ n.hint }}</div>
          </div>
          <button
            type="button"
            role="switch"
            :aria-checked="n.on"
            class="relative w-11 h-6 rounded-full transition-colors flex-shrink-0"
            :class="n.on ? 'bg-[var(--accent-600)]' : 'bg-stone-200'"
            @click="toggle(n)"
          >
            <span
              class="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform"
              :class="n.on ? 'translate-x-5' : 'translate-x-0'"
            />
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useAuth } from "@/composables/useAuth";
import { useTheme } from "@/composables/useTheme";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { fullName, role, user, zone } = useAuth();
const { theme, set } = useTheme();
const { locale, setLocale } = useI18n();
const { success } = useToast();

const langs = [
  { code: "en", label: "EN" },
  { code: "fr", label: "FR" },
  { code: "ar", label: "AR" },
];

const notifs = ref([
  { key: "sla", label: "SLA breach alerts", hint: "When an order is about to miss its SLA", on: true },
  { key: "cutoff", label: "Manifest cutoff reminders", hint: "Before the daily carrier cutoff", on: true },
  { key: "returns", label: "Returns spike", hint: "When returns for a SKU jump unexpectedly", on: false },
]);

function toggle(n) {
  n.on = !n.on;
  success("Preference saved", `${n.label} ${n.on ? "on" : "off"}`);
}
</script>
