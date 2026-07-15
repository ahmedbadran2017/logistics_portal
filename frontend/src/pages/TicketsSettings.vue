<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[760px] mx-auto">
    <header>
      <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('css.title') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('css.intro') }}</p>
    </header>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 3" :key="n" class="h-[88px] rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <template v-else-if="s">
      <div v-if="!s.canEdit" class="flex items-center gap-2.5 bg-amber-50 ring-1 ring-amber-200/70 rounded-xl px-4 py-3">
        <Icon name="shield-alert" :size="16" class="text-amber-500 shrink-0" />
        <span class="text-[12.5px] text-amber-800">{{ t('cfs.readOnly') }}</span>
      </div>

      <!-- SLA targets -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 inline-flex items-center justify-center"><Icon name="clock" :size="15" /></span>
          <div>
            <div class="text-[13px] font-semibold text-stone-900">{{ t('css.slaTitle') }}</div>
            <div class="text-[11.5px] text-stone-400">{{ t('css.slaHint') }}</div>
          </div>
        </div>
        <div class="grid sm:grid-cols-2 gap-3">
          <label class="block">
            <span class="text-[11.5px] font-medium text-stone-500">{{ t('css.firstResp') }}</span>
            <div class="flex items-center gap-2 mt-1">
              <input v-model.number="s.firstResponseH" type="number" min="1" max="720" :disabled="!s.canEdit"
                     class="w-24 h-9 ps-3 rounded-lg ring-1 ring-stone-200 text-[13px] tabular-nums focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:bg-stone-50 disabled:text-stone-400"
                     @input="dirty = true" />
              <span class="text-[12px] text-stone-400">{{ t('cfs.hours') }}</span>
            </div>
          </label>
          <label class="block">
            <span class="text-[11.5px] font-medium text-stone-500">{{ t('css.resolution') }}</span>
            <div class="flex items-center gap-2 mt-1">
              <input v-model.number="s.resolutionH" type="number" min="1" max="720" :disabled="!s.canEdit"
                     class="w-24 h-9 ps-3 rounded-lg ring-1 ring-stone-200 text-[13px] tabular-nums focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:bg-stone-50 disabled:text-stone-400"
                     @input="dirty = true" />
              <span class="text-[12px] text-stone-400">{{ t('cfs.hours') }}</span>
            </div>
          </label>
        </div>
      </section>

      <!-- categories -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 inline-flex items-center justify-center"><Icon name="tag" :size="15" /></span>
          <div>
            <div class="text-[13px] font-semibold text-stone-900">{{ t('css.catsTitle') }}</div>
            <div class="text-[11.5px] text-stone-400">{{ t('css.catsHint') }}</div>
          </div>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <span v-for="(c, i) in s.categories" :key="c"
                class="inline-flex items-center gap-1.5 h-8 ps-3 rounded-full text-[12px] font-medium text-violet-700 bg-violet-50 ring-1 ring-violet-200"
                :class="s.canEdit ? 'pe-1.5' : 'pe-3'">
            {{ c }}
            <button v-if="s.canEdit" class="w-5 h-5 rounded-full inline-flex items-center justify-center hover:bg-violet-100 text-violet-400 hover:text-violet-700"
                    @click="s.categories.splice(i, 1); dirty = true"><Icon name="x" :size="11" /></button>
          </span>
        </div>
        <div v-if="s.canEdit" class="flex items-center gap-2">
          <input v-model="newCat" :placeholder="t('css.addCatPh')" maxlength="60" dir="auto"
                 class="flex-1 h-9 ps-3 pe-3 rounded-lg ring-1 ring-stone-200 text-[12.5px] focus:outline-none focus:ring-2 focus:ring-violet-300"
                 @keyup.enter="addCat" />
          <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-violet-700 bg-violet-50 ring-1 ring-violet-200 hover:bg-violet-100 disabled:opacity-50 transition-colors"
                  :disabled="!newCat.trim() || s.categories.length >= 20" @click="addCat">
            <Icon name="plus" :size="13" class="inline -mt-px me-1" />{{ t('cfs.addReason') }}
          </button>
        </div>
      </section>

      <!-- section admins -->
      <section class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 inline-flex items-center justify-center"><Icon name="shield-alert" :size="15" /></span>
          <div>
            <div class="text-[13px] font-semibold text-stone-900">{{ t('cfs.adminsTitle') }}</div>
            <div class="text-[11.5px] text-stone-400">{{ t('cfs.adminsHint') }}</div>
          </div>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <span v-for="(a, i) in s.admins" :key="a"
                class="inline-flex items-center gap-1.5 h-8 ps-3 rounded-full text-[12px] font-medium text-stone-700 bg-stone-100 ring-1 ring-stone-200 font-mono"
                :class="isManager ? 'pe-1.5' : 'pe-3'">
            {{ a }}
            <button v-if="isManager" class="w-5 h-5 rounded-full inline-flex items-center justify-center hover:bg-stone-200 text-stone-400 hover:text-stone-700"
                    @click="s.admins.splice(i, 1); dirty = true"><Icon name="x" :size="11" /></button>
          </span>
          <span v-if="!s.admins.length" class="text-[12px] text-stone-400">{{ t('cfs.noAdmins') }}</span>
        </div>
        <div v-if="isManager" class="flex items-center gap-2">
          <input v-model="newAdmin" :placeholder="t('cfs.adminPh')" maxlength="140"
                 class="flex-1 h-9 ps-3 pe-3 rounded-lg ring-1 ring-stone-200 text-[12.5px] font-mono focus:outline-none focus:ring-2 focus:ring-violet-300"
                 @keyup.enter="addAdmin" />
          <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-stone-700 bg-stone-100 ring-1 ring-stone-200 hover:bg-stone-200 disabled:opacity-50 transition-colors"
                  :disabled="!newAdmin.trim()" @click="addAdmin">
            <Icon name="plus" :size="13" class="inline -mt-px me-1" />{{ t('cfs.addAdmin') }}
          </button>
        </div>
      </section>

      <div v-if="s.canEdit" class="flex items-center justify-end gap-2">
        <button class="h-10 px-5 rounded-xl text-[13px] font-bold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50 shadow-sm transition-colors"
                :disabled="saving || !dirty" @click="save">
          <Icon name="check" :size="14" class="inline -mt-px me-1.5" />{{ saving ? '…' : t('px.common.save') }}
        </button>
      </div>
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

const s = ref(null);
const loading = ref(true);
const dirty = ref(false);
const saving = ref(false);
const newCat = ref("");
const newAdmin = ref("");

onMounted(async () => {
  try {
    s.value = await api("tickets.cs_settings");
  } catch (e) {
    warn(t("cf.loadFail"), String(e.message || e));
  } finally {
    loading.value = false;
  }
});

function addCat() {
  const v = newCat.value.trim();
  if (!v || s.value.categories.includes(v) || s.value.categories.length >= 20) return;
  s.value.categories.push(v);
  newCat.value = "";
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
      firstResponseH: s.value.firstResponseH,
      resolutionH: s.value.resolutionH,
      categories: s.value.categories,
    };
    if (isManager.value) payload.admins = s.value.admins;
    const res = await apiPost("tickets.save_cs_settings", { settings: payload });
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
