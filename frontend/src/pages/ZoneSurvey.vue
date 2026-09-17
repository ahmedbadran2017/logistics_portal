<template>
  <!-- Walking a zone to find out which shelves are real. One thumb, one
       question per shelf, and nothing on the screen the walker does not need
       while standing in front of it. -->
  <div class="min-h-screen bg-stone-50 flex flex-col">
    <div class="sticky top-0 z-20 bg-white border-b border-stone-200 px-4 py-3">
      <div class="flex items-center gap-2">
        <button v-if="walk" class="w-9 h-9 rounded-xl bg-stone-100 text-stone-500 flex items-center justify-center"
                :aria-label="t('common.back')" @click="leave">
          <Icon name="chevron-left" :size="17" class="rtl:-scale-x-100" />
        </button>
        <h1 class="text-[15px] font-bold text-stone-900 flex items-center gap-1.5">
          <Icon name="map-pin" :size="17" />{{ walk ? walk.zone.replace(' - JM', '') : t("zs.title") }}
        </h1>
        <span v-if="walk" class="text-[11px] font-bold rounded-full px-2 py-0.5 bg-stone-900 text-white">
          {{ t('zs.pass') }} {{ walk.pass }}
        </span>
        <span v-if="walk" class="ms-auto text-[13px] font-bold tabular-nums text-stone-700">{{ doneN }}/{{ walk.bins.length }}</span>
      </div>
      <p v-if="walk && walk.pass === 2" class="text-[11.5px] text-amber-700 mt-2 leading-snug">{{ t("zs.blindHint") }}</p>
    </div>

    <!-- zone picker -->
    <div v-if="!walk" class="flex-1 px-3 py-3 space-y-2">
      <p class="px-1 text-[12px] text-stone-500 leading-snug">{{ t("zs.intro") }}</p>
      <div v-if="loading" class="space-y-2">
        <div v-for="n in 6" :key="n" class="h-[62px] rounded-2xl bg-white ring-1 ring-stone-200/60 animate-pulse" />
      </div>
      <button v-for="z in zones" :key="z.zone"
              class="w-full min-h-[62px] px-4 py-3 rounded-2xl bg-white ring-1 flex items-center gap-3 text-start active:bg-stone-50"
              :class="z.stage === 'confirmed' ? 'ring-emerald-200' : z.stage === 'disputed' ? 'ring-rose-200' : 'ring-stone-200/70'"
              @click="start(z)">
        <span class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 text-[13px] font-bold tabular-nums"
              :class="z.stage === 'confirmed' ? 'bg-emerald-50 text-emerald-700'
                : z.stage === 'disputed' ? 'bg-rose-50 text-rose-700'
                : z.stage === 'pass2' ? 'bg-amber-50 text-amber-700' : 'bg-stone-100 text-stone-500'">
          {{ z.bins }}
        </span>
        <span class="min-w-0 flex-1">
          <span class="block text-[13.5px] font-semibold text-stone-900 truncate">{{ z.zone.replace(' - JM', '') }}</span>
          <span class="block text-[11.5px] text-stone-400 mt-0.5">
            {{ z.withStock }} {{ t('zs.withStock') }}
            <template v-if="z.passes.length"> · {{ z.passes.map((p) => t('zs.pass') + p.pass + ' ' + p.by).join(' · ') }}</template>
          </span>
        </span>
        <span class="text-[11px] font-bold rounded-full px-2 py-0.5 flex-shrink-0"
              :class="z.stage === 'confirmed' ? 'text-emerald-700 bg-emerald-50'
                : z.stage === 'disputed' ? 'text-rose-700 bg-rose-50'
                : z.stage === 'pass2' ? 'text-amber-700 bg-amber-50'
                : z.stage === 'mine' ? 'text-stone-500 bg-stone-100' : 'text-stone-600 bg-stone-100'">
          {{ t('zs.st_' + z.stage) }}
        </span>
      </button>
    </div>

    <!-- the walk -->
    <div v-else class="flex-1 px-3 py-3 space-y-2 pb-32">
      <div v-for="b in walk.bins" :key="b.warehouse"
           class="bg-white rounded-2xl ring-1 p-3 flex items-center gap-3 transition-all"
           :class="b.mine === 'seen' ? 'ring-emerald-300 bg-emerald-50/50'
             : b.mine === 'missing' ? 'ring-stone-300 bg-stone-100/70 opacity-70' : 'ring-stone-200/70'">
        <span v-if="b.mine === 'seen'" class="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center text-[13px] font-bold tabular-nums flex-shrink-0">{{ b.pos }}</span>
        <span v-else class="w-9 h-9 rounded-xl bg-stone-100 text-stone-400 flex items-center justify-center flex-shrink-0"><Icon name="package" :size="16" /></span>
        <div class="min-w-0 flex-1">
          <div class="text-[15px] font-bold text-stone-900 font-mono">{{ b.short }}</div>
          <div class="text-[11px] text-stone-400 mt-0.5">
            <span v-if="b.book">{{ t('zs.book') }} {{ b.book }}</span>
            <span v-else>{{ t('zs.emptyBook') }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0">
          <button class="w-12 h-12 rounded-xl flex items-center justify-center transition-colors"
                  :class="b.mine === 'seen' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-600 ring-1 ring-emerald-200'"
                  :aria-label="t('zs.here')" @click="setMark(b, 'seen')">
            <Icon name="check" :size="20" />
          </button>
          <button class="w-12 h-12 rounded-xl flex items-center justify-center transition-colors"
                  :class="b.mine === 'missing' ? 'bg-stone-700 text-white' : 'bg-white text-stone-400 ring-1 ring-stone-200'"
                  :aria-label="t('zs.notHere')" @click="setMark(b, 'missing')">
            <Icon name="x" :size="20" />
          </button>
        </div>
      </div>

      <!-- a shelf with no record: written down, created by a manager later -->
      <div class="bg-white rounded-2xl ring-1 ring-dashed ring-stone-300 p-3">
        <div class="text-[12px] font-semibold text-stone-600 mb-2">{{ t("zs.foundTitle") }}</div>
        <div v-for="f in walk.found" :key="f.warehouse" class="text-[12.5px] font-mono text-amber-700 mb-1">+ {{ f.short }}</div>
        <div class="flex items-center gap-2">
          <input v-model="newLabel" :placeholder="t('zs.foundPh')" maxlength="60"
                 class="flex-1 h-11 px-3 rounded-xl bg-stone-50 ring-1 ring-stone-200 text-[14px] font-mono uppercase focus:outline-none" />
          <button class="h-11 px-4 rounded-xl text-[13px] font-semibold text-white bg-stone-900 disabled:opacity-40"
                  :disabled="!newLabel.trim()" @click="addFound">{{ t("zs.foundAdd") }}</button>
        </div>
      </div>
    </div>

    <!-- finish dock -->
    <div v-if="walk" class="fixed inset-x-0 bottom-0 z-20 bg-white border-t border-stone-200 px-4 py-3 flex items-center gap-3">
      <span class="text-[12px] text-stone-500">
        <b class="text-emerald-700 tabular-nums">{{ seenN }}</b> {{ t('zs.here') }} ·
        <b class="text-stone-700 tabular-nums">{{ missingN }}</b> {{ t('zs.notHere') }}
      </span>
      <button class="ms-auto h-11 px-5 rounded-xl text-[13.5px] font-bold text-white disabled:opacity-40"
              :class="armed ? 'bg-rose-600' : 'bg-stone-900'"
              :disabled="doneN === 0 || busy" @click="onFinish">
        {{ busy ? '…' : armed ? t('zs.finishSure') : t('zs.finish') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const zones = ref([]);
const loading = ref(true);
const walk = ref(null);
const newLabel = ref("");
const busy = ref(false);
const armed = ref(false);
let disarm = null;

const seenN = computed(() => (walk.value?.bins || []).filter((b) => b.mine === "seen").length);
const missingN = computed(() => (walk.value?.bins || []).filter((b) => b.mine === "missing").length);
const doneN = computed(() => seenN.value + missingN.value);

async function load() {
  loading.value = true;
  try {
    const r = await api("zone_survey.zones");
    zones.value = r.zones || [];
  } catch (e) { warn(t("mv.loadFail"), String(e.message || e)); } finally { loading.value = false; }
}

async function start(z) {
  try {
    const r = await apiPost("zone_survey.open_zone", { zone: z.zone });
    if (!r.ok) {
      warn(r.reason === "same_person" ? t("zs.needOther").replace("{who}", r.first || "")
        : t("zs.alreadyDone"), z.zone.replace(" - JM", ""));
      return;
    }
    walk.value = r;
    window.scrollTo(0, 0);
  } catch (e) { warn(t("mv.loadFail"), String(e.message || e)); }
}

// Optimistic: the tap must feel instant with a glove on, and a lost write is
// recoverable — the walk reopens exactly where it was left.
async function setMark(b, verdict) {
  const prev = b.mine;
  b.mine = verdict;
  try {
    const r = await apiPost("zone_survey.mark", {
      zone: walk.value.zone, warehouse: b.warehouse, verdict,
    });
    b.pos = r.pos;
  } catch (e) {
    b.mine = prev;
    warn(t("cf.actFail"), String(e.message || e));
  }
}

async function addFound() {
  const label = newLabel.value.trim().toUpperCase();
  if (!label) return;
  try {
    await apiPost("zone_survey.add_found", { zone: walk.value.zone, label });
    walk.value.found = [...(walk.value.found || []), { warehouse: label, short: label }];
    newLabel.value = "";
    success(t("zs.foundOk"), label);
  } catch (e) { warn(t("cf.actFail"), String(e.message || e)); }
}

async function onFinish() {
  if (!armed.value) {
    armed.value = true;
    clearTimeout(disarm);
    disarm = setTimeout(() => (armed.value = false), 4000);
    return;
  }
  armed.value = false;
  busy.value = true;
  try {
    const r = await apiPost("zone_survey.finish", { zone: walk.value.zone });
    if (r.ready) {
      const d = (r.differ || []).length;
      if (d) warn(t("zs.differ").replace("{n}", d), walk.value.zone.replace(" - JM", ""));
      else success(t("zs.agreed"), `${r.seen} ${t("zs.here")} · ${r.missing} ${t("zs.notHere")}`);
    } else {
      success(t("zs.passDone"), t("zs.awaitSecond"));
    }
    walk.value = null;
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally { busy.value = false; }
}

function leave() { walk.value = null; load(); }

onMounted(load);
</script>
