<template>
  <header class="h-[60px] bg-white border-b border-stone-200 flex items-center justify-between px-6 shrink-0">
    <div class="flex items-center gap-3 min-w-0">
      <div>
        <h1 class="text-[17px] font-semibold text-stone-900 tracking-tight">{{ title }}</h1>
        <p v-if="subtitle" class="text-[11.5px] text-stone-500 mt-px">{{ subtitle }}</p>
      </div>
    </div>
    <div class="flex items-center gap-3">
      <!-- Cmd+K hint -->
      <button
        @click="openCmd"
        class="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-stone-50 hover:bg-stone-100 text-stone-500 text-[11.5px] transition-colors group"
        title="Quick search (⌘K)"
        aria-haspopup="dialog"
        aria-keyshortcuts="Meta+K"
        aria-label="Open quick search palette"
      >
        <Icon name="search" :size="13" class="group-hover:text-stone-700 transition-colors" />
        <span>Quick search</span>
        <kbd class="ml-2 text-[10px] font-mono text-stone-400 px-1.5 py-0.5 bg-white border border-stone-200 rounded">⌘K</kbd>
      </button>
      <div class="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-stone-50 text-stone-500 text-[11px]" role="status" aria-label="Live data connection">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" aria-hidden="true" />
        Live
      </div>
      <div class="h-6 w-px bg-stone-200" aria-hidden="true"></div>
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-full overflow-hidden bg-gradient-to-br from-[var(--yol-v2-accent-400)] to-[var(--yol-v2-accent-700)] flex items-center justify-center text-[11px] font-semibold text-white shadow-sm shrink-0">
          <img v-if="userImage" :src="userImage" :alt="userName" class="w-full h-full object-cover" @error="userImage = ''" />
          <span v-else aria-hidden="true">{{ initials }}</span>
        </div>
        <div class="hidden md:block leading-tight">
          <div class="text-[12.5px] font-medium text-stone-900 truncate max-w-[160px]">{{ userName }}</div>
          <div class="text-[10.5px] text-stone-400 truncate max-w-[160px]">{{ userId }}</div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, inject, ref, onMounted, onBeforeUnmount } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/Icon.vue";
import { COMPANY } from "@/composables/useApi";

const route = useRoute();

const openCommandPalette = inject("openCommandPalette", () => {});
function openCmd() { openCommandPalette(); }

const title = computed(() => route.meta?.title || "Logistics");
const subtitle = computed(() => COMPANY);

// User state populated from server-injected globals or, in dev, fetched from Frappe.
const userId = ref(window.user_id || "");
const fullName = ref(window.full_name || "");
const userImage = ref(window.user_image || "");

let cancelled = false;
onBeforeUnmount(() => { cancelled = true; });

onMounted(async () => {
  if (userId.value && userId.value !== "Guest") {
    if (!userImage.value || !fullName.value) await fetchUser(userId.value);
    return;
  }
  try {
    const r = await fetch("/api/method/frappe.auth.get_logged_user", {
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (cancelled) return;
    // Session expired: Frappe returns 403 or redirects to login HTML.
    if (r.status === 403 || r.redirected) {
      const here = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?redirect-to=${here}`;
      return;
    }
    const j = await r.json();
    if (cancelled) return;
    if (j.message && j.message !== "Guest") {
      userId.value = j.message;
      await fetchUser(j.message);
    } else {
      const here = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/login?redirect-to=${here}`;
    }
  } catch (e) {
    if (cancelled) return;
    console.error("[Header] couldn't load user", e);
    userId.value = userId.value || "Guest";
  }
});

async function fetchUser(email) {
  try {
    const url = "/api/method/frappe.client.get_value?doctype=User"
      + "&filters=" + encodeURIComponent(JSON.stringify({ name: email }))
      + "&fieldname=" + encodeURIComponent(JSON.stringify(["full_name", "user_image"]));
    const r = await fetch(url, { credentials: "include", headers: { Accept: "application/json" } });
    if (cancelled) return;
    const j = await r.json();
    if (cancelled) return;
    const m = j.message || {};
    if (m.full_name) fullName.value = m.full_name;
    if (m.user_image) userImage.value = m.user_image;
  } catch (e) { /* non-fatal */ }
}

const userName = computed(() => {
  if (fullName.value) return fullName.value;
  const u = userId.value;
  if (!u) return "…";
  if (u === "Guest") return "Guest";
  return u.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
});

const initials = computed(() => {
  const n = userName.value;
  if (!n || n === "…") return "?";
  if (n === "Guest") return "G";
  return n.split(/\s+/).map((p) => p[0]).filter(Boolean).slice(0, 2).join("").toUpperCase() || "?";
});
</script>
