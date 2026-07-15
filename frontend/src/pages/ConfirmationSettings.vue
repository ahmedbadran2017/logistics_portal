<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[820px] mx-auto">
    <header>
      <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cfs.title') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cfs.intro') }}</p>
    </header>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 3" :key="n" class="h-[90px] rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <template v-else-if="s">
      <p v-if="!s.canEdit" class="flex items-center gap-2 text-[12px] text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-lg px-3 py-2">
        <Icon name="shield-alert" :size="14" /> {{ t('cfs.readOnly') }}
      </p>

      <!-- retry timers -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="text-[12px] font-semibold text-stone-900">{{ t('cfs.timersTitle') }}</div>
        <div class="grid sm:grid-cols-3 gap-3">
          <label v-for="f in TIMERS" :key="f.key" class="block">
            <span class="text-[11.5px] font-medium text-stone-600">{{ t(f.label) }}</span>
            <div class="flex items-center gap-2 mt-1">
              <input v-model.number="s[f.key]" type="number" min="1" max="168" :disabled="!s.canEdit"
                     class="w-full h-10 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] tabular-nums focus:outline-none focus:ring-2 disabled:bg-stone-50"
                     style="--tw-ring-color: var(--accent-400)" @input="dirty = true" />
              <span class="text-[11.5px] text-stone-400">{{ t('cfs.hours') }}</span>
            </div>
          </label>
        </div>
      </div>

      <!-- cancel reasons -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="text-[12px] font-semibold text-stone-900">{{ t('cfs.reasonsTitle') }}</div>
        <p class="text-[11.5px] text-stone-500">{{ t('cfs.reasonsHint') }}</p>
        <div class="flex flex-wrap gap-1.5">
          <span v-for="(r, i) in s.reasons" :key="i"
                class="inline-flex items-center gap-1.5 h-8 ps-3 pe-1.5 rounded-lg text-[12px] font-medium text-stone-700 bg-stone-50 ring-1 ring-stone-200">
            {{ r }}
            <button v-if="s.canEdit" class="w-5 h-5 rounded hover:bg-rose-100 text-stone-400 hover:text-rose-600 flex items-center justify-center"
                    @click="s.reasons.splice(i, 1); dirty = true"><Icon name="x" :size="11" /></button>
          </span>
        </div>
        <div v-if="s.canEdit" class="flex items-center gap-2">
          <input v-model="newReason" :placeholder="t('cfs.reasonPh')" maxlength="60"
                 class="flex-1 h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none"
                 @keyup.enter="addReason" />
          <button class="h-9 px-3 rounded-lg text-[12px] font-semibold text-stone-700 bg-stone-100 hover:bg-stone-200"
                  @click="addReason">+ {{ t('cfs.addReason') }}</button>
        </div>
      </div>

      <!-- section admins (portal manager only) -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="text-[12px] font-semibold text-stone-900">{{ t('cfs.adminsTitle') }}</div>
        <p class="text-[11.5px] text-stone-500">{{ t('cfs.adminsHint') }}</p>
        <div class="flex flex-wrap gap-1.5">
          <span v-for="(a, i) in s.admins" :key="a"
                class="inline-flex items-center gap-1.5 h-8 ps-3 pe-1.5 rounded-lg text-[12px] font-mono text-violet-700 bg-violet-50 ring-1 ring-violet-200">
            {{ a }}
            <button v-if="isManager" class="w-5 h-5 rounded hover:bg-rose-100 text-violet-400 hover:text-rose-600 flex items-center justify-center"
                    @click="s.admins.splice(i, 1); dirty = true"><Icon name="x" :size="11" /></button>
          </span>
          <span v-if="!s.admins.length" class="text-[12px] text-stone-400">{{ t('cfs.noAdmins') }}</span>
        </div>
        <div v-if="isManager" class="flex items-center gap-2">
          <input v-model="newAdmin" :placeholder="t('cfs.adminPh')" type="email"
                 class="flex-1 h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] font-mono focus:outline-none"
                 @keyup.enter="addAdmin" />
          <button class="h-9 px-3 rounded-lg text-[12px] font-semibold text-stone-700 bg-stone-100 hover:bg-stone-200"
                  @click="addAdmin">+ {{ t('cfs.addAdmin') }}</button>
        </div>
      </div>

      <button v-if="s.canEdit && dirty"
              class="w-full h-11 rounded-xl text-[13.5px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-50"
              :disabled="saving" @click="save">
        {{ saving ? "…" : t('px.common.save') }}
      </button>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const { role } = useAuth();
const isManager = computed(() => role.value === "manager");

const TIMERS = [
  { key: "retryDna", label: "cfs.tDna" },
  { key: "retryFollowup", label: "cfs.tFollowup" },
  { key: "retryOnhold", label: "cfs.tOnhold" },
];

const s = ref(null);
const loading = ref(true);
const dirty = ref(false);
const saving = ref(false);
const newReason = ref("");
const newAdmin = ref("");

onMounted(async () => {
  try {
    s.value = await api("confirmation.cf_settings");
  } catch (e) {
    warn(t("cf.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
});

function addReason() {
  const v = newReason.value.trim();
  if (!v || s.value.reasons.includes(v)) return;
  s.value.reasons.push(v);
  newReason.value = "";
  dirty.value = true;
}
function addAdmin() {
  const v = newAdmin.value.trim().toLowerCase();
  if (!v || !/^\S+@\S+\.\S+$/.test(v) || s.value.admins.includes(v)) return;
  s.value.admins.push(v);
  newAdmin.value = "";
  dirty.value = true;
}

async function save() {
  saving.value = true;
  try {
    const payload = {
      retryDna: s.value.retryDna, retryFollowup: s.value.retryFollowup,
      retryOnhold: s.value.retryOnhold, reasons: s.value.reasons,
    };
    if (isManager.value) payload.admins = s.value.admins;
    const res = await apiPost("confirmation.save_cf_settings", { settings: payload });
    Object.assign(s.value, res);
    dirty.value = false;
    success(t("cfs.saved"));
  } catch (e) {
    warn(t("cfs.saveFail"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}
</script>
