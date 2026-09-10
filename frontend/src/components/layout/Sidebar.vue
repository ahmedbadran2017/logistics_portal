<template>
  <aside class="w-[236px] shrink-0 bg-white border-e border-stone-200/70 flex flex-col h-full">
    <!-- Logo lockup -->
    <div class="px-4 pt-4 pb-2">
      <div class="flex items-center gap-2 min-w-0">
        <img :src="logoSrc" alt="Justyol" class="block h-3.5 flex-shrink-0" />
        <span class="h-3.5 w-px bg-stone-200 flex-shrink-0" />
        <span class="text-[9.5px] font-semibold text-stone-400 tracking-[0.14em] uppercase">
          {{ IS_CC ? t("nav.ccPortal", "Contact Center") : t("nav.logistics", "Logistics") }}
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
      <!-- Every section is a first-class top-level group — the Contact-Center
           lanes (Confirmation / Rescue / CS) each stand on their own route,
           no umbrella switcher. Cross-lane navigation lives in the admin hub. -->
      <template v-for="(group, gi) in nav" :key="group.section">
        <div :class="gi > 0 ? 'mt-3' : ''">
          <!-- Section headers fold. Six groups is the honest size of this
               portal, but nobody works all six at once — the fold lets each
               role keep only their morning on screen, and the choice is
               remembered per browser. The group holding the CURRENT page can
               be folded visually but never silently: its header keeps the
               accent dot so "where am I" always has an answer. -->
          <button type="button"
                  class="w-full flex items-center gap-1.5 px-3 mb-1 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400 hover:text-stone-600 transition-colors group/sec"
                  @click="toggleSection(group.section)">
            <span class="truncate">{{ t(group.section) }}</span>
            <span v-if="isFolded(group.section) && sectionHasActive(group)"
                  class="w-1.5 h-1.5 rounded-full bg-[var(--accent-500)] flex-shrink-0" />
            <Icon :name="isFolded(group.section) ? 'chevron-down' : 'chevron-up'" :size="11"
                  class="ms-auto text-stone-300 group-hover/sec:text-stone-500 flex-shrink-0" />
          </button>
          <div v-show="!isFolded(group.section)" class="space-y-px">
            <!-- One loop, so the order in roles.js is the order on screen. An
                 item can point OUT of the SPA (item.href): attendance lives in
                 Frappe HR's own app, and standing up a second writer to
                 Employee Checkin — the doctype payroll reads — to save one hop
                 would be a poor trade. Those render as a plain link. -->
            <template v-for="item in group.items" :key="item.label">
            <a
              v-if="item.href"
              :href="item.href"
              class="flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium cursor-pointer group transition-colors text-stone-600 hover:bg-stone-100 hover:text-stone-900"
            >
              <Icon :name="item.icon" :size="16" class="text-stone-400 group-hover:text-stone-600" />
              <span class="flex-1 truncate">{{ t(item.label) }}</span>
              <Icon name="external-link" :size="13" class="text-stone-300" />
            </a>
            <router-link v-else :to="{ name: item.to }" custom v-slot="{ navigate }">
              <a
                class="flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] font-medium cursor-pointer group transition-colors"
                :class="isActive(item) ? 'bg-[var(--accent-50)] text-[var(--accent-700)]' : 'text-stone-600 hover:bg-stone-100 hover:text-stone-900'"
                @click="navigate"
              >
                <Icon :name="item.icon" :size="16" :class="isActive(item) ? 'text-[var(--accent-600)]' : 'text-stone-400 group-hover:text-stone-600'" />
                <span class="flex-1 truncate">{{ t(item.label) }}</span>
                <!-- live pull: same-customer clusters waiting on THIS agent -->
                <span v-if="item.to === 'Consolidation' && consolCount"
                      class="text-[10px] font-bold tabular-nums text-violet-700 bg-violet-100 ring-1 ring-violet-200/70 rounded-full px-1.5 py-px animate-pulse">
                  {{ consolCount }}
                </span>
              </a>
            </router-link>
            </template>
          </div>
        </div>
      </template>
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

    <!-- On the clock? Read-only, from Frappe HR's own logs. The floor punches
         in the HR app; this only saves them opening it to remember whether
         they did. Tapping it goes there. -->
    <a
      v-if="att && att.state !== 'no_employee'"
      :href="att.hrApp || '/hrms'"
      class="mx-2 mb-1 flex items-center gap-2 px-2 py-1.5 rounded-lg ring-1 transition-colors"
      :class="attOn ? 'bg-emerald-50 ring-emerald-200/70 hover:bg-emerald-100'
                    : attOut ? 'bg-stone-50 ring-stone-200 hover:bg-stone-100'
                             : 'bg-amber-50 ring-amber-200/70 hover:bg-amber-100'"
    >
      <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
            :class="attOn ? 'bg-emerald-500' : attOut ? 'bg-stone-400' : 'bg-amber-500'" />
      <span class="min-w-0 flex-1 leading-tight">
        <span class="block text-[11.5px] font-semibold truncate"
              :class="attOn ? 'text-emerald-800' : attOut ? 'text-stone-700' : 'text-amber-800'">
          {{ attLabel }}
        </span>
        <span v-if="attDetail" class="block text-[10px] tabular-nums truncate"
              :class="attOn ? 'text-emerald-700/80' : attOut ? 'text-stone-500' : 'text-amber-700/90'">
          {{ attDetail }}
        </span>
      </span>
      <Icon name="external-link" :size="12" class="flex-shrink-0"
            :class="attOn ? 'text-emerald-400' : 'text-stone-300'" />
    </a>

    <!-- Role switcher card -->
    <div class="p-2 border-t border-stone-100 relative">
      <button
        type="button"
        class="w-full flex items-center gap-2 ps-1.5 pe-2 py-1.5 rounded-lg hover:bg-stone-100 transition-colors"
        @click="menuOpen = !menuOpen; if (menuOpen) loadMembers();"
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
        <!-- View-as: the manager renders the portal through a member's role
             and queue (read-fidelity; actions stay the manager's own). -->
        <template v-if="realRole === 'manager'">
          <div class="px-3 pt-2 pb-1.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400 border-t border-stone-100 mt-1">
            {{ t("nav.viewAsMember", "View as member") }}
          </div>
          <div class="max-h-[180px] overflow-y-auto">
            <button v-for="m in members" :key="m.user" type="button"
                    class="w-full flex items-center gap-2 px-3 py-1.5 text-start hover:bg-stone-50"
                    @click="pickMember(m)">
              <span class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 text-[9px] font-bold flex items-center justify-center flex-shrink-0">{{ (m.fullName || m.user)[0].toUpperCase() }}</span>
              <span class="min-w-0 flex-1 leading-tight">
                <span class="block text-[12px] text-stone-800 truncate">{{ m.fullName }}</span>
                <span class="block text-[9.5px] text-stone-400">{{ t(`roles.${m.role}`, m.role) }}</span>
              </span>
            </button>
            <div v-if="!members.length" class="px-3 py-2 text-[11px] text-stone-400">…</div>
          </div>
        </template>

        <!-- Log out — the Desk is blocked for the floor team, so the portal must
             carry its own way out of the session. -->
        <div class="border-t border-stone-100 mt-1 pt-1">
          <button
            type="button"
            class="w-full flex items-center gap-2.5 px-3 py-2 text-start hover:bg-rose-50 text-rose-600"
            @click="doLogout"
          >
            <Icon name="log-out" :size="14" />
            <span class="text-[12.5px] font-semibold">{{ t('common.logout') }}</span>
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import InstallApp from "@/components/ui/InstallApp.vue";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { api } from "@/lib/resource";
import { navFor } from "@/lib/roles";
import { IS_CC, PORTAL_BASE } from "@/lib/portal";

defineEmits(["open-search"]);

// Served by Frappe from the app's public/ dir; bound (not a static src) so vite
// doesn't try to resolve it at build time.
const logoSrc = "/assets/logistics_portal/justyol-logo.png";
const { t, locale, setLocale } = useI18n();
const langs = [{ v: "en", l: "EN" }, { v: "fr", l: "FR" }, { v: "ar", l: "ع" }];
const { user, role, roles, fullName, hiddenPages, setActiveRole, logout, viewAs, setViewAs } = useAuth();
// The REAL role (session), not the viewed one — the picker must stay visible
// while viewing as someone else.
const realRole = computed(() => (viewAs.value ? "manager" : role.value));
const members = ref([]);
async function loadMembers() {
  if (realRole.value !== "manager" || members.value.length) return;
  try {
    const r = await api("auth.team_members");
    members.value = (r?.members || []).filter((m) => m.role && m.user !== user.value)
      .map((m) => ({ user: m.user, fullName: m.name, role: m.role }));
  } catch (_) { members.value = []; }
}
function pickMember(m) { menuOpen.value = false; setViewAs(m); }
const route = useRoute();
const menuOpen = ref(false);

const nav = computed(() => navFor(role.value, hiddenPages.value, IS_CC));

// Folded sections, remembered per browser. localStorage on purpose (not
// session): which parts of the menu a person keeps open is a workstation
// habit, not a login-scoped state.
const FOLD_KEY = "lp_nav_folded";
const folded = ref(new Set());
try {
  folded.value = new Set(JSON.parse(localStorage.getItem(FOLD_KEY) || "[]"));
} catch { /* a fresh browser simply starts fully open */ }
function isFolded(sec) { return folded.value.has(sec); }
function toggleSection(sec) {
  const next = new Set(folded.value);
  if (next.has(sec)) next.delete(sec);
  else next.add(sec);
  folded.value = next;
  try { localStorage.setItem(FOLD_KEY, JSON.stringify([...next])); } catch {}
}
function sectionHasActive(group) {
  return (group.items || []).some((it) => it.to && isActive(it));
}

// Consolidation badge — the agent must SEE that a cluster of their own
// customers appeared without having to visit the page.
const consolCount = ref(0);
async function loadConsolCount() {
  if (!IS_CC) return;
  const has = nav.value.some((g) => g.items.some((i) => i.to === "Consolidation"));
  if (!has) { consolCount.value = 0; return; }
  try {
    const r = await api("orders.consolidation_count");
    consolCount.value = Number(r?.n) || 0;
  } catch (_) { /* the badge is a bonus, never an error */ }
}
onMounted(loadConsolCount);
const consolTimer = setInterval(() => {
  if (document.visibilityState === "visible") loadConsolCount();
}, 120000);
onUnmounted(() => clearInterval(consolTimer));

// ── On the clock ────────────────────────────────────────────────────────────
// The punch happens in Frappe HR's app; this is a read of what it recorded, so
// the state can go stale between polls. Refresh on focus as well as on a timer:
// coming back from the HR app is exactly when the answer has just changed.
const att = ref(null);
async function loadAtt() {
  try {
    att.value = await api("attendance.my_status");
  } catch (e) {
    att.value = null;   // never let a status chip break the nav
  }
}
onMounted(loadAtt);
const attTimer = setInterval(() => {
  if (document.visibilityState === "visible") loadAtt();
}, 300000);
function onVis() { if (document.visibilityState === "visible") loadAtt(); }
document.addEventListener("visibilitychange", onVis);
onUnmounted(() => {
  clearInterval(attTimer);
  document.removeEventListener("visibilitychange", onVis);
});

// A shift left open overnight is the ANOMALY this chip exists to surface, so
// it must not wear the same green as a healthy morning punch — read at a
// glance, "still clocked in from yesterday" in emerald says "all good".
// `attOn` is therefore today's clock-in only; a stale one falls through to
// the amber that every other needs-a-human state already uses.
const attOn = computed(() => att.value?.state === "in" && !att.value?.stale);
// A checkout from a previous day is not "you left at 14:48" — it is "you have
// not punched today". Saying the former for a log from February would be
// precise and useless.
const attOut = computed(() => att.value?.state === "out" && !att.value?.stale);
// Two lines, state then detail. One line could not hold either: the sidebar is
// ~150px of text and "Still clocked in from an earlier day" arrived as
// "Still clocked in from an earli…" — the half that got cut is the half that
// says something. The state alone fits in every locale; the clock goes below.
const attLabel = computed(() => {
  const a = att.value;
  if (!a) return "";
  if (a.state === "in") return a.stale ? t("nav.attSinceYesterday") : t("nav.attIn");
  if (a.state === "out" && !a.stale) return t("nav.attOut");
  return t("nav.attNone");
});
const attDetail = computed(() => {
  const a = att.value;
  if (!a) return "";
  if (a.state === "in") {
    if (a.stale) return t("nav.attEarlierDay");
    const parts = [];
    if (a.since) parts.push(`${t("nav.attSince")} ${a.since}`);
    if (a.workedMin) parts.push(hhmm(a.workedMin));
    return parts.join(" · ");
  }
  if (a.state === "out" && !a.stale) {
    const at = (a.lastAt || "").slice(11, 16);
    return at ? `${t("nav.attAt")} ${at}` : "";
  }
  return "";
});
function hhmm(mins) {
  const h = Math.floor((mins || 0) / 60), m = (mins || 0) % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}

const initials = computed(() =>
  (fullName.value || "?").split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase()
);

const ROLE_ICON = {
  manager: "gauge",
  dispatcher: "layers",
  picker: "package",
  packer: "tag",
  returns: "rotate-ccw",
  confirmation: "phone",
  cs: "message-circle",
  tracking: "map-pin",
};
function roleIcon(r) {
  return ROLE_ICON[r] || "user";
}

function isActive(item) {
  // Active when the current route matches; the first nav item pointing at a
  // shared fallback route wins visually via route-name match.
  return route.name === item.to;
}

async function doLogout() {
  menuOpen.value = false;
  try { await logout(); } catch (_) { /* clear locally regardless */ }
  window.location.href = `${PORTAL_BASE}/login`;
}

function pickRole(r) {
  // Picking one of MY roles while viewing as a member is an exit first —
  // otherwise the banner says "viewing as X" while the nav shows role Y and
  // as_user still rides every call.
  if (viewAs.value) { setViewAs(null); return; }
  setActiveRole(r);
  menuOpen.value = false;
}
</script>
