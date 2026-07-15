<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[900px] mx-auto">
    <div>
      <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em] flex items-center gap-2">
        <Icon name="settings" :size="20" class="text-[var(--accent-600)]" /> Settings
      </h1>
      <p class="text-[12.5px] text-stone-500 mt-1">{{ t('px.set.sub') }}</p>
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

    <!-- Operations (manager): every tunable the portal used to hardcode -->
    <div v-if="role === 'manager'" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5">
      <div class="flex items-center justify-between gap-2 mb-1 flex-wrap">
        <div class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
          <Icon name="gauge" :size="15" /> Operations
        </div>
        <button
          v-if="opsDirty"
          class="h-8 px-3 rounded-lg text-[12px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50"
          :disabled="opsSaving" @click="saveOps"
        >{{ opsSaving ? "Saving…" : "Save changes" }}</button>
      </div>
      <p class="text-[11.5px] text-stone-500 mb-3">{{ t('px.set.opsSub') }}</p>

      <div v-if="opsLoading" class="space-y-2">
        <div v-for="n in 3" :key="n" class="h-[52px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
      </div>

      <ul v-else-if="ops" class="divide-y divide-stone-100">
        <li v-for="f in opsFields" :key="f.key" class="flex items-center justify-between py-3 gap-3">
          <div class="min-w-0">
            <div class="text-[12.5px] font-medium text-stone-900">{{ f.label }}</div>
            <div class="text-[11px] text-stone-500">{{ f.hint }}</div>
          </div>
          <input
            v-if="f.type === 'time'" v-model="ops[f.key]" type="time"
            class="h-9 px-2.5 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] font-semibold text-stone-900 tabular-nums outline-none focus:ring-stone-400 flex-shrink-0"
          />
          <div v-else class="flex items-center gap-1.5 flex-shrink-0">
            <input
              v-model.number="ops[f.key]" type="number" :min="f.min" :max="f.max"
              class="w-[76px] h-9 px-2 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] font-semibold text-stone-900 tabular-nums text-center outline-none focus:ring-stone-400"
            />
            <span class="text-[11px] text-stone-400 w-[42px]">{{ f.unit }}</span>
          </div>
        </li>
      </ul>
      <div v-else class="text-[12px] text-stone-400 py-4">{{ t('px.set.deployHint') }}</div>
    </div>

    <!-- Pickable warehouses (manager) -->
    <div v-if="role === 'manager'" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5">
      <div class="flex items-center gap-2 mb-1 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
        <Icon name="warehouse" :size="15" /> {{ t('px.set.whTitle') }}
      </div>
      <p class="text-[11.5px] text-stone-500 mb-3">{{ t('px.set.whSub') }}</p>
      <div v-if="whLoading" class="text-[12px] text-stone-400 py-4">{{ t('px.set.whLoading') }}</div>
      <ul v-else-if="zones.length" class="divide-y divide-stone-100">
        <li v-for="z in zones" :key="z.name" class="flex items-center justify-between py-3 gap-3">
          <div class="min-w-0">
            <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ z.short }}</div>
            <div class="text-[11px] text-stone-500 tabular-nums">
              {{ z.qty }} units · {{ z.items }} items<span v-if="z.locked" class="text-stone-400"> · always excluded</span>
            </div>
          </div>
          <button
            type="button" role="switch" :aria-checked="z.pickable" :disabled="z.locked || whSaving"
            class="relative w-11 h-6 rounded-full transition-colors flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
            :class="z.pickable ? 'bg-[var(--accent-600)]' : 'bg-stone-200'"
            @click="toggleZone(z)"
          >
            <span class="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform"
                  :class="z.pickable ? 'translate-x-5' : 'translate-x-0'" />
          </button>
        </li>
      </ul>
      <div v-else class="text-[12px] text-stone-400 py-4">{{ t('px.set.whEmpty') }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useAuth } from "@/composables/useAuth";
import { useTheme } from "@/composables/useTheme";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { api, apiPost, liveOr } from "@/lib/resource";

const { fullName, role, user, zone } = useAuth();
const { theme, set } = useTheme();
const { locale, setLocale, t } = useI18n();
const { success, warn } = useToast();

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

// ── Operations settings (manager) ────────────────────────────────────
const ops = ref(null);
const opsSaved = ref(null);
const opsLoading = ref(true);
const opsSaving = ref(false);

const opsFields = [
  { key: "cutoff", type: "time", label: "Manifest cutoff",
    hint: "Carrier hand-off deadline — countdowns, today's cycle boundary, cutoff %" },
  { key: "dayTarget", type: "num", min: 1, max: 500, unit: "orders",
    label: "Daily target / person", hint: "Floor board pace + leaderboard target" },
  { key: "floorStart", type: "num", min: 0, max: 23, unit: "h",
    label: "Floor day starts", hint: "Hourly-rate denominators and the intake chart" },
  { key: "floorEnd", type: "num", min: 1, max: 23, unit: "h",
    label: "Floor day ends", hint: "Last hour on the intake chart" },
  { key: "lowThreshold", type: "num", min: 0, max: 1000, unit: "units",
    label: "Low-stock threshold", hint: "A SKU at or below this counts as low" },
  { key: "slaDays", type: "num", min: 1, max: 30, unit: "days",
    label: "Delivery promise", hint: "SLA engine — expected delivery = ship date + this" },
  { key: "shortPickCooldownH", type: "num", min: 0, max: 168, unit: "hours",
    label: "Short-pick cooldown", hint: "How long an order stays off the pick pool after a shelf-empty report" },
];

const opsDirty = computed(() =>
  !!ops.value && !!opsSaved.value &&
  JSON.stringify(ops.value) !== JSON.stringify(opsSaved.value));

async function loadOps() {
  if (role.value !== "manager") { opsLoading.value = false; return; }
  try {
    const r = await api("settings.ops_settings");
    if (r && typeof r === "object" && r.cutoff) {
      ops.value = { ...r };
      opsSaved.value = { ...r };
    }
  } catch (_) { /* hint card shows */ } finally {
    opsLoading.value = false;
  }
}

async function saveOps() {
  opsSaving.value = true;
  try {
    const r = await apiPost("settings.save_ops_settings", { settings: ops.value });
    ops.value = { ...r };
    opsSaved.value = { ...r };
    success("Operations settings saved", "Applied portal-wide immediately");
  } catch (e) {
    warn("Couldn't save", String(e.message || e));
  } finally {
    opsSaving.value = false;
  }
}

// ── Pickable warehouses (manager) ────────────────────────────────────
const zones = ref([]);
const whLoading = ref(false);
const whSaving = ref(false);

async function loadWarehouses() {
  if (role.value !== "manager") return;
  whLoading.value = true;
  const res = await liveOr(null, () => api("warehouses.warehouse_settings"));
  zones.value = res && Array.isArray(res.zones) ? res.zones : [];
  whLoading.value = false;
}
async function toggleZone(z) {
  if (z.locked || whSaving.value) return;
  z.pickable = !z.pickable;
  const excluded = zones.value.filter((x) => !x.locked && !x.pickable).map((x) => x.name);
  whSaving.value = true;
  try {
    await apiPost("warehouses.save_warehouse_settings", { excluded });
    success("Pickable zones saved", `${z.short} ${z.pickable ? "included" : "excluded"}`);
  } catch (e) {
    z.pickable = !z.pickable; // revert on failure
    warn("Couldn't save", String(e.message || e));
  } finally {
    whSaving.value = false;
  }
}
onMounted(() => { loadWarehouses(); loadOps(); });
</script>
