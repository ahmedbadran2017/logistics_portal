<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1200px] mx-auto">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('cfa.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">{{ t('cfa.intro') }}</p>
      </div>
      <label class="relative inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 cursor-pointer">
        <Icon name="calendar" :size="14" /> {{ day }}
        <input type="date" class="absolute inset-0 opacity-0 cursor-pointer" :value="day" :max="today" @change="onDay" />
      </label>
    </header>

    <!-- The honesty box comes BEFORE the data: an action here is a decision
         or an order edit, on either trail (portal or Desk). A gap can be a
         long call, a WhatsApp queue, a break — a question, never a verdict. -->
    <div class="flex items-start gap-2 text-[11.5px] text-stone-500 bg-stone-50 ring-1 ring-stone-200/60 rounded-xl px-3.5 py-2.5">
      <Icon name="info" :size="13" class="mt-0.5 flex-shrink-0 text-stone-400" />
      <span>{{ t('cfa.honesty') }}</span>
    </div>

    <!-- NOW: one pulsing card per agent. Calls run longer than scans, so the
         pulse is slower than the floor's: green within 10, rose past 30. -->
    <div v-if="!loading && d && day === today && d.people.length"
         class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
      <div v-for="p in d.people" :key="'live-' + p.user"
           class="rounded-xl ring-1 px-3 py-2.5" :class="liveTone(p).box">
        <div class="flex items-center gap-2">
          <span class="relative flex w-2.5 h-2.5 flex-shrink-0">
            <span v-if="liveTone(p).pulse" class="absolute inline-flex w-full h-full rounded-full opacity-60 animate-ping" :class="liveTone(p).dot" />
            <span class="relative inline-flex w-2.5 h-2.5 rounded-full" :class="liveTone(p).dot" />
          </span>
          <span class="text-[12px] font-bold truncate" :class="liveTone(p).name" dir="auto">{{ p.name }}</span>
          <span v-if="roleTag(p)" class="text-[9px] font-semibold text-stone-400 flex-shrink-0">{{ roleTag(p) }}</span>
        </div>
        <div class="text-[10.5px] mt-1 tabular-nums" :class="liveTone(p).sub">
          <template v-if="p.lastAgoMin === null">{{ t('cfa.noActionsYet') }}</template>
          <template v-else-if="p.lastAgoMin <= 10">{{ t('cfa.liveNow') }} · {{ mainStation(p) }}</template>
          <template v-else>{{ t('cfa.silentFor').replace('{m}', String(p.lastAgoMin)) }} · {{ mainStation(p) }}</template>
        </div>
        <div v-if="p.notes.length" class="text-[10px] mt-0.5 truncate" :class="liveTone(p).sub">
          <Icon name="edit" :size="9" class="inline -mt-px" /> {{ p.notes[p.notes.length - 1].text }}
        </div>
      </div>
    </div>

    <div v-if="loading" class="space-y-2">
      <div v-for="n in 4" :key="n" class="h-[76px] rounded-xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="d && d.people.length" class="space-y-2">
      <div v-for="p in d.people" :key="p.user"
           class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3 hover:shadow-sm transition-shadow">
        <div class="flex items-center gap-3 flex-wrap">
          <div class="min-w-[150px]">
            <div class="text-[13.5px] font-bold text-stone-900" dir="auto">{{ p.name }}
              <span v-if="roleTag(p)" class="text-[10px] font-semibold text-stone-400">· {{ roleTag(p) }}</span>
            </div>
            <div class="text-[10.5px] text-stone-400 tabular-nums">
              <template v-if="p.punchIn">{{ t('cfa.punched') }} {{ p.punchIn }} · </template>
              {{ t('cfa.firstAction') }} {{ p.first || '—' }}
            </div>
          </div>
          <div class="flex items-center gap-1.5 flex-wrap">
            <span v-for="(n, st) in p.stations" :key="st"
                  class="text-[10px] font-bold rounded-full px-2 py-0.5" :class="ST_CLS[st] || 'bg-stone-100 text-stone-600'">
              {{ t('cfa.st_' + st) }} {{ n }}
            </span>
          </div>
          <div class="ms-auto flex items-center gap-4 text-end">
            <div>
              <div class="text-[17px] font-extrabold tabular-nums text-stone-900">{{ p.actions }}</div>
              <div class="text-[9.5px] uppercase font-semibold text-stone-400">{{ t('cfa.actions') }}</div>
            </div>
            <div>
              <div class="text-[17px] font-extrabold tabular-nums text-stone-800">{{ p.orders }}</div>
              <div class="text-[9.5px] uppercase font-semibold text-stone-400">{{ t('cfa.orders') }}</div>
            </div>
            <div>
              <div class="text-[17px] font-extrabold tabular-nums text-stone-800">{{ pace(p) }}</div>
              <div class="text-[9.5px] uppercase font-semibold text-stone-400">{{ t('cfa.perHour') }}</div>
            </div>
            <div>
              <div class="text-[17px] font-extrabold tabular-nums"
                   :class="p.maxGapMin >= 90 ? 'text-rose-600' : p.maxGapMin >= 45 ? 'text-amber-600' : 'text-stone-800'">
                {{ p.maxGapMin }}<span class="text-[10px] font-semibold">{{ t('cfa.minShort') }}</span>
              </div>
              <div class="text-[9.5px] uppercase font-semibold text-stone-400">{{ t('cfa.maxGap') }}</div>
            </div>
          </div>
        </div>
        <!-- the admin's margin: what the silences meant, in their words. -->
        <div v-if="p.notes.length || noteFor === p.user" class="mt-2 space-y-1">
          <div v-for="(n, ni) in p.notes" :key="ni" class="text-[11px] text-stone-500 flex items-start gap-1.5">
            <Icon name="edit" :size="10" class="mt-0.5 flex-shrink-0 text-stone-300" />
            <span dir="auto">{{ n.text }} <span class="text-stone-300">· {{ n.by }} {{ n.at }}</span></span>
          </div>
        </div>
        <div class="mt-1.5 flex items-center gap-1.5">
          <template v-if="noteFor === p.user">
            <input v-model="noteText" :placeholder="t('cfa.notePh')" dir="auto"
                   class="h-8 flex-1 max-w-[380px] ps-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] focus:outline-none focus:ring-2"
                   style="--tw-ring-color: var(--accent-300)"
                   @keyup.enter="saveNote(p)" />
            <button class="h-8 px-3 rounded-lg text-[11.5px] font-semibold text-white bg-stone-900 disabled:opacity-40"
                    :disabled="!noteText.trim() || noteBusy" @click="saveNote(p)">{{ t('cfa.noteSave') }}</button>
            <button class="h-8 px-2 text-[11.5px] text-stone-400" @click="noteFor = ''">✕</button>
          </template>
          <button v-else class="text-[10.5px] font-semibold text-stone-400 hover:text-stone-700"
                  @click="noteFor = p.user; noteText = ''">
            + {{ t('cfa.noteAdd') }}
          </button>
        </div>
        <!-- the day as a strip: one cell per 30 minutes, darker = busier. -->
        <div class="flex items-center gap-px mt-2.5">
          <span class="text-[9px] text-stone-400 tabular-nums me-1">{{ axis[0] }}</span>
          <div v-for="slot in axis" :key="slot" class="flex-1 h-4 rounded-[3px]"
               :class="cellCls(p.slots[slot] || 0)"
               :title="slot + ' · ' + (p.slots[slot] || 0)" />
          <span class="text-[9px] text-stone-400 tabular-nums ms-1">{{ axis[axis.length - 1] }}</span>
        </div>
      </div>
      <div class="text-[11px] text-stone-400 text-center pt-1">{{ d.totalActions }} {{ t('cfa.totalActions') }}</div>
    </div>

    <div v-else class="rounded-2xl bg-white ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="activity" :size="24" class="mx-auto text-stone-300" />
      <div class="text-[14px] font-semibold text-stone-700 mt-2">{{ t('cfa.emptyTitle') }}</div>
      <p class="text-[12px] text-stone-500 mt-1 max-w-[420px] mx-auto">{{ t('cfa.emptyBody') }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const d = ref(null);
const loading = ref(true);
const today = new Date().toISOString().slice(0, 10);
const day = ref(today);

const ST_CLS = {
  confirm: "bg-emerald-50 text-emerald-700",
  cancel: "bg-rose-50 text-rose-700",
  dna: "bg-amber-50 text-amber-700",
  followup: "bg-sky-50 text-sky-700",
  other: "bg-stone-100 text-stone-600",
  rescue: "bg-violet-50 text-violet-700",
  cs: "bg-indigo-50 text-indigo-700",
  desk: "bg-teal-50 text-teal-700",
  edit: "bg-stone-100 text-stone-500",
};

async function load() {
  loading.value = true;
  try { d.value = await api("contact_center.team_activity", { day: day.value }); }
  catch { d.value = { people: [], totalActions: 0 }; }
  loading.value = false;
}
function onDay(e) { day.value = e.target.value || today; load(); }
onMounted(load);
// Live board: today refreshes itself every 60s — same wall-dashboard habit
// as the floor's screen. Quiet: no skeleton flash on the refresh.
const tick = setInterval(async () => {
  if (day.value !== today || document.visibilityState !== "visible") return;
  try { d.value = await api("contact_center.team_activity", { day: day.value }); } catch {}
}, 60000);
onUnmounted(() => clearInterval(tick));

// The pulse, tuned for phones: a call runs longer than a scan, so green is
// an action within 10 minutes, amber 10-30, rose past 30 while punched in;
// stone = punched in and not one action yet.
function liveTone(p) {
  const level = p.lastAgoMin === null ? "off"
    : p.lastAgoMin <= 10 ? "on" : p.lastAgoMin <= 30 ? "cooling" : "silent";
  return {
    on:      { box: "bg-emerald-50 ring-emerald-200", dot: "bg-emerald-500", pulse: true,
               name: "text-emerald-900", sub: "text-emerald-700/80" },
    cooling: { box: "bg-amber-50 ring-amber-200", dot: "bg-amber-500", pulse: false,
               name: "text-amber-900", sub: "text-amber-700/80" },
    silent:  { box: "bg-rose-50 ring-rose-200", dot: "bg-rose-500", pulse: false,
               name: "text-rose-900", sub: "text-rose-700/90" },
    off:     { box: "bg-white ring-stone-200", dot: "bg-stone-300", pulse: false,
               name: "text-stone-700", sub: "text-stone-400" },
  }[level];
}
function roleTag(p) {
  if (!p.role || p.role === "none") return "";
  return t("cfa.role_" + p.role, p.role);
}
function mainStation(p) {
  let best = "", n = -1;
  for (const [st, c] of Object.entries(p.stations || {})) if (c > n) { best = st; n = c; }
  return best ? t("cfa.st_" + best) : "";
}

// Section-admin margin notes.
const noteFor = ref("");
const noteText = ref("");
const noteBusy = ref(false);
async function saveNote(p) {
  if (!noteText.value.trim()) return;
  noteBusy.value = true;
  try {
    await apiPost("contact_center.team_note", { user: p.user, day: day.value, text: noteText.value.trim() });
    noteFor.value = ""; noteText.value = "";
    d.value = await api("contact_center.team_activity", { day: day.value });
  } catch (e) { /* keep the input so nothing is lost */ }
  noteBusy.value = false;
}

// Server axis: the WHOLE working day, so a silent morning is a visible hole.
const axis = computed(() => d.value?.axis || []);
function cellCls(n) {
  if (!n) return "bg-stone-100";
  if (n >= 12) return "bg-emerald-600";
  if (n >= 6) return "bg-emerald-500";
  if (n >= 3) return "bg-emerald-300";
  return "bg-emerald-200";
}
function pace(p) {
  if (!p.first || !p.last || p.first === p.last) return p.actions;
  const [h0, m0] = p.first.split(":").map(Number);
  const [h1, m1] = p.last.split(":").map(Number);
  const hrs = Math.max(0.5, (h1 * 60 + m1 - h0 * 60 - m0) / 60);
  return Math.round(p.actions / hrs);
}
</script>
