<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1200px] mx-auto">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('fa.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">{{ t('fa.intro') }}</p>
      </div>
      <label class="relative inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 cursor-pointer">
        <Icon name="calendar" :size="14" /> {{ day }}
        <input type="date" class="absolute inset-0 opacity-0 cursor-pointer" :value="day" :max="today" @change="onDay" />
      </label>
    </header>

    <!-- The honesty box comes BEFORE the data: what this screen can and
         cannot say, so a gap is a question, never an automatic verdict. -->
    <div class="flex items-start gap-2 text-[11.5px] text-stone-500 bg-stone-50 ring-1 ring-stone-200/60 rounded-xl px-3.5 py-2.5">
      <Icon name="info" :size="13" class="mt-0.5 flex-shrink-0 text-stone-400" />
      <span>{{ t('fa.honesty') }}</span>
    </div>

    <!-- NOW: one pulsing card per person. Station discipline is the rule
         here — someone on sort stays on sort — so silence is a real signal,
         and the manager's note is the recorded exception. -->
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
        </div>
        <div class="text-[10.5px] mt-1 tabular-nums" :class="liveTone(p).sub">
          <template v-if="p.lastAgoMin === null">{{ t('fa.noScansYet') }}</template>
          <template v-else-if="p.lastAgoMin <= 5">{{ t('fa.liveNow') }} · {{ mainStation(p) }}</template>
          <template v-else>{{ t('fa.silentFor').replace('{m}', String(p.lastAgoMin)) }} · {{ mainStation(p) }}</template>
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
            <div class="text-[13.5px] font-bold text-stone-900" dir="auto">{{ p.name }}</div>
            <div class="text-[10.5px] text-stone-400 tabular-nums">
              <template v-if="p.punchIn">{{ t('fa.punched') }} {{ p.punchIn }} · </template>
              {{ t('fa.firstScan') }} {{ p.first }}
            </div>
          </div>
          <div class="flex items-center gap-1.5">
            <span v-for="(n, st) in p.stations" :key="st"
                  class="text-[10px] font-bold rounded-full px-2 py-0.5" :class="ST_CLS[st]">
              {{ t('fa.st_' + st) }} {{ n }}
            </span>
          </div>
          <div class="ms-auto flex items-center gap-4 text-end">
            <div>
              <div class="text-[17px] font-extrabold tabular-nums text-stone-900">{{ p.scans }}</div>
              <div class="text-[9.5px] uppercase font-semibold text-stone-400">{{ t('fa.scans') }}</div>
            </div>
            <div>
              <div class="text-[17px] font-extrabold tabular-nums text-stone-800">{{ pace(p) }}</div>
              <div class="text-[9.5px] uppercase font-semibold text-stone-400">{{ t('fa.perHour') }}</div>
            </div>
            <div>
              <div class="text-[17px] font-extrabold tabular-nums"
                   :class="p.maxGapMin >= 60 ? 'text-rose-600' : p.maxGapMin >= 30 ? 'text-amber-600' : 'text-stone-800'">
                {{ p.maxGapMin }}<span class="text-[10px] font-semibold">{{ t('fa.minShort') }}</span>
              </div>
              <div class="text-[9.5px] uppercase font-semibold text-stone-400">{{ t('fa.maxGap') }}</div>
            </div>
          </div>
        </div>
        <!-- the manager's margin: what the silences meant, in their words,
             with their name on it — and the box to add the next one. -->
        <div v-if="p.notes.length || noteFor === p.user" class="mt-2 space-y-1">
          <div v-for="(n, ni) in p.notes" :key="ni" class="text-[11px] text-stone-500 flex items-start gap-1.5">
            <Icon name="edit" :size="10" class="mt-0.5 flex-shrink-0 text-stone-300" />
            <span dir="auto">{{ n.text }} <span class="text-stone-300">· {{ n.by }} {{ n.at }}</span></span>
          </div>
        </div>
        <div class="mt-1.5 flex items-center gap-1.5">
          <template v-if="noteFor === p.user">
            <input v-model="noteText" :placeholder="t('fa.notePh')" dir="auto"
                   class="h-8 flex-1 max-w-[380px] ps-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] focus:outline-none focus:ring-2"
                   style="--tw-ring-color: var(--accent-300)"
                   @keyup.enter="saveNote(p)" />
            <button class="h-8 px-3 rounded-lg text-[11.5px] font-semibold text-white bg-stone-900 disabled:opacity-40"
                    :disabled="!noteText.trim() || noteBusy" @click="saveNote(p)">{{ t('fa.noteSave') }}</button>
            <button class="h-8 px-2 text-[11.5px] text-stone-400" @click="noteFor = ''">✕</button>
          </template>
          <button v-else class="text-[10.5px] font-semibold text-stone-400 hover:text-stone-700"
                  @click="noteFor = p.user; noteText = ''">
            + {{ t('fa.noteAdd') }}
          </button>
        </div>
        <!-- the day as a strip: one cell per 30 minutes, darker = busier.
             Same hour axis for everyone, so silence lines up vertically. -->
        <div class="flex items-center gap-px mt-2.5">
          <span class="text-[9px] text-stone-400 tabular-nums me-1">{{ axis[0] }}</span>
          <div v-for="slot in axis" :key="slot" class="flex-1 h-4 rounded-[3px]"
               :class="cellCls(p.slots[slot] || 0)"
               :title="slot + ' · ' + (p.slots[slot] || 0)" />
          <span class="text-[9px] text-stone-400 tabular-nums ms-1">{{ axis[axis.length - 1] }}</span>
        </div>
      </div>
      <div class="text-[11px] text-stone-400 text-center pt-1">{{ d.totalScans }} {{ t('fa.totalScans') }}</div>
    </div>

    <div v-else class="rounded-2xl bg-white ring-1 ring-stone-200/70 p-10 text-center">
      <Icon name="activity" :size="24" class="mx-auto text-stone-300" />
      <div class="text-[14px] font-semibold text-stone-700 mt-2">{{ t('fa.emptyTitle') }}</div>
      <p class="text-[12px] text-stone-500 mt-1 max-w-[420px] mx-auto">{{ t('fa.emptyBody') }}</p>
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
  pick: "bg-emerald-50 text-emerald-700",
  sort: "bg-violet-50 text-violet-700",
  manifest: "bg-sky-50 text-sky-700",
};

async function load() {
  loading.value = true;
  try { d.value = await api("scanlog.floor_activity", { day: day.value }); }
  catch { d.value = { people: [], totalScans: 0 }; }
  loading.value = false;
}
function onDay(e) { day.value = e.target.value || today; load(); }
onMounted(load);
// Live board: today refreshes itself every 60s, so this can sit on an office
// screen as a wall dashboard. Quiet — no skeleton flash on the refresh.
const tick = setInterval(async () => {
  if (day.value !== today || document.visibilityState !== "visible") return;
  try { d.value = await api("scanlog.floor_activity", { day: day.value }); } catch {}
}, 60000);
onUnmounted(() => clearInterval(tick));

// The pulse: station discipline means silence is signal here. Green = scanned
// within 5 minutes; amber = 5-20; rose = 20+ while punched in — the same 20
// the alert engine fires on, so the card never turns red without the bell
// agreeing; stone = punched in and not one scan yet. The manager's note
// rides the card so the recorded exception travels with the red it excuses.
function liveTone(p) {
  const level = p.lastAgoMin === null ? "off"
    : p.lastAgoMin <= 5 ? "on" : p.lastAgoMin <= 20 ? "cooling" : "silent";
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
function mainStation(p) {
  let best = "", n = -1;
  for (const [st, c] of Object.entries(p.stations || {})) if (c > n) { best = st; n = c; }
  return best ? t("fa.st_" + best) : "";
}

// Manager margin notes.
const noteFor = ref("");
const noteText = ref("");
const noteBusy = ref(false);
async function saveNote(p) {
  if (!noteText.value.trim()) return;
  noteBusy.value = true;
  try {
    await apiPost("scanlog.floor_note", { user: p.user, day: day.value, text: noteText.value.trim() });
    noteFor.value = ""; noteText.value = "";
    d.value = await api("scanlog.floor_activity", { day: day.value });
  } catch (e) { /* the toast layer isn't wired here; keep the input so nothing is lost */ }
  noteBusy.value = false;
}

// One shared axis from the earliest to the latest slot anyone touched, so a
// silent half-hour shows as a hole that lines up across all the rows.
const axis = computed(() => {
  const slots = new Set();
  for (const p of d.value?.people || []) Object.keys(p.slots).forEach((s) => slots.add(s));
  if (!slots.size) return [];
  const all = [...slots].sort();
  const [h0, m0] = all[0].split(":").map(Number);
  const [h1, m1] = all[all.length - 1].split(":").map(Number);
  const out = [];
  for (let x = h0 * 2 + (m0 >= 30 ? 1 : 0); x <= h1 * 2 + (m1 >= 30 ? 1 : 0); x++) {
    out.push(`${String(Math.floor(x / 2)).padStart(2, "0")}:${x % 2 ? "30" : "00"}`);
  }
  return out;
});
function cellCls(n) {
  if (!n) return "bg-stone-100";
  if (n >= 20) return "bg-emerald-600";
  if (n >= 10) return "bg-emerald-500";
  if (n >= 4) return "bg-emerald-300";
  return "bg-emerald-200";
}
function pace(p) {
  if (!p.first || !p.last || p.first === p.last) return p.scans;
  const [h0, m0] = p.first.split(":").map(Number);
  const [h1, m1] = p.last.split(":").map(Number);
  const hrs = Math.max(0.5, (h1 * 60 + m1 - h0 * 60 - m0) / 60);
  return Math.round(p.scans / hrs);
}
</script>
