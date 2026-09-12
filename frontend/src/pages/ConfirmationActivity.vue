<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1200px] mx-auto">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('cfa.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">{{ t('cfa.intro') }}</p>
      </div>
      <div class="flex items-center gap-1.5">
        <!-- The picker alone made every other day a hunt: it looks like a
             label, and it answers one day at a time. Arrows walk the days. -->
        <button class="w-9 h-9 rounded-lg text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50 flex items-center justify-center"
                :title="t('common.prevDay')" @click="stepDay(-1)">
          <Icon name="chevron-left" :size="15" />
        </button>
        <label class="relative inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 cursor-pointer">
          <Icon name="calendar" :size="14" /> {{ day }}
          <input type="date" class="absolute inset-0 opacity-0 cursor-pointer" :value="day" :max="today" @change="onDay" />
        </label>
        <button class="w-9 h-9 rounded-lg text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50 flex items-center justify-center disabled:opacity-40"
                :disabled="day >= today" :title="t('common.nextDay')" @click="stepDay(1)">
          <Icon name="chevron-right" :size="15" />
        </button>
        <button v-if="day !== today"
                class="h-9 px-3 rounded-lg text-[12.5px] font-semibold text-white bg-stone-900 hover:bg-stone-800"
                @click="goToday">{{ t('common.today') }}</button>
      </div>
    </header>

    <!-- The honesty box comes BEFORE the data: an action here is a decision
         or an order edit, on either trail (portal or Desk). A gap can be a
         long call, a WhatsApp queue, a break — a question, never a verdict. -->
    <div class="flex items-start gap-2 text-[11.5px] text-stone-500 bg-stone-50 ring-1 ring-stone-200/60 rounded-xl px-3.5 py-2.5">
      <Icon name="info" :size="13" class="mt-0.5 flex-shrink-0 text-stone-400" />
      <span>{{ t('cfa.honesty') }}</span>
    </div>

    <!-- History: the run of days, so a dip is visible before anyone clicks
         into one. Each bar is a day; the open day is outlined, and clicking
         a bar loads it above. -->
    <section v-if="hist && hist.totals.length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
      <div class="flex items-baseline gap-2 flex-wrap mb-3">
        <span class="text-[12.5px] font-semibold text-stone-900">{{ t('common.histTitle') }}</span>
        <span class="text-[11px] text-stone-400 tabular-nums">{{ t('common.histDays').replace('{n}', String(hist.days.length)) }}</span>
        <div class="ms-auto flex items-center gap-1.5">
          <button v-for="n in [7, 14, 30]" :key="n"
                  class="h-7 px-2.5 rounded-md text-[11.5px] font-semibold ring-1 transition-colors tabular-nums"
                  :class="histDays === n ? 'text-white bg-stone-900 ring-stone-900' : 'text-stone-600 bg-white ring-stone-200 hover:ring-stone-300'"
                  @click="setHistDays(n)">{{ n }}{{ t('cc.dayShort') }}</button>
        </div>
      </div>
      <div class="flex items-end gap-1 h-[84px]">
        <button v-for="r in hist.totals" :key="r.day"
                class="flex-1 min-w-[6px] flex flex-col justify-end h-full group"
                :title="r.day + ' · ' + r.actions + ' · ' + r.people"
                @click="pickDay(r.day)">
          <span class="text-[9px] text-stone-400 tabular-nums text-center mb-0.5 opacity-0 group-hover:opacity-100">{{ r.actions }}</span>
          <span class="w-full rounded-t transition-colors"
                :class="r.day === day
                  ? 'bg-[var(--accent-600)] ring-2 ring-[var(--accent-300)]'
                  : (r.actions ? 'bg-[var(--accent-400)] group-hover:bg-[var(--accent-500)]' : 'bg-stone-100')"
                :style="{ height: barH(r.actions) }" />
        </button>
      </div>
      <div class="flex gap-1 mt-1">
        <span v-for="r in hist.totals" :key="'lbl-' + r.day"
              class="flex-1 min-w-[6px] text-[9px] text-center tabular-nums"
              :class="r.day === day ? 'text-stone-900 font-bold' : 'text-stone-400'">
          {{ r.day.slice(8) }}
        </span>
      </div>
      <!-- Per agent across the same days: who is steady, who comes and goes. -->
      <div v-if="hist.people.length" class="mt-3 pt-3 border-t border-stone-100 space-y-1.5">
        <div v-for="hp in hist.people" :key="'h-' + hp.user" class="flex items-center gap-2.5">
          <span class="text-[11.5px] text-stone-700 truncate w-[130px] flex-shrink-0" dir="auto">{{ hp.name }}</span>
          <span class="flex-1 flex items-end gap-[2px] h-[22px]">
            <span v-for="dd in hist.days" :key="hp.user + dd"
                  class="flex-1 rounded-sm"
                  :class="(hp.byDay[dd] || 0) ? 'bg-emerald-400' : 'bg-stone-100'"
                  :style="{ height: sparkH(hp.byDay[dd] || 0) }"
                  :title="dd + ' · ' + (hp.byDay[dd] || 0)" />
          </span>
          <span class="text-[11px] font-bold text-stone-800 tabular-nums w-[46px] text-end flex-shrink-0">{{ hp.total }}</span>
          <span class="text-[10px] text-stone-400 tabular-nums w-[44px] text-end flex-shrink-0">{{ hp.activeDays }}{{ t('common.histD') }}</span>
        </div>
      </div>
    </section>

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
        <!-- the day as a real heatmap: one cell per 30 minutes, intensity
             relative to the board's busiest half-hour, the count printed on
             any cell strong enough to carry it, an hour ruler underneath,
             and a pulse on the CURRENT half-hour. Same axis for everyone,
             so silence lines up vertically. -->
        <div class="mt-3">
          <div class="flex gap-[3px]">
            <div v-for="(slot, si) in axis" :key="slot"
                 class="flex-1 h-6 rounded-[5px] flex items-center justify-center transition-colors duration-300"
                 :class="[cellCls(p.slots[slot] || 0),
                          isToday && si === axis.length - 1 ? 'hm-now' : '']"
                 :title="slot + ' — ' + (p.slots[slot] || 0)">
              <span v-if="(p.slots[slot] || 0) > 0 && cellStrong(p.slots[slot])"
                    class="text-[9px] font-bold tabular-nums text-white/95">{{ p.slots[slot] }}</span>
              <span v-else-if="(p.slots[slot] || 0) > 0"
                    class="text-[9px] font-bold tabular-nums text-emerald-900/60">{{ p.slots[slot] }}</span>
            </div>
          </div>
          <div class="flex gap-[3px] mt-1">
            <div v-for="slot in axis" :key="'r' + slot"
                 class="flex-1 text-center text-[8.5px] tabular-nums leading-none"
                 :class="slot.endsWith(':00') ? 'text-stone-400 font-medium' : 'text-stone-200'">
              {{ slot.endsWith(':00') ? slot.slice(0, 2) : '·' }}
            </div>
          </div>
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

// ── History: the run of days behind the one on screen ──────────────────────
const hist = ref(null);
const histDays = ref(14);
async function loadHist() {
  try { hist.value = await api("contact_center.team_history", { days: histDays.value }); }
  catch { hist.value = null; }
}
function setHistDays(n) { histDays.value = n; loadHist(); }
function pickDay(dd) { if (dd === day.value) return; day.value = dd; load(); }
function stepDay(delta) {
  const t = new Date(day.value + "T12:00:00");
  t.setDate(t.getDate() + delta);
  const next = t.toISOString().slice(0, 10);
  if (next > today) return;
  day.value = next;
  load();
}
function goToday() { day.value = today; load(); }

// Bars are scaled to the busiest day in the window, so a quiet fortnight
// still shows its own shape instead of a flat line.
const histMax = computed(() => Math.max(1, ...(hist.value?.totals || []).map((r) => r.actions)));
function barH(n) { return n ? Math.max(4, Math.round((n / histMax.value) * 76)) + "px" : "3px"; }
const sparkMax = computed(() => {
  const all = [];
  for (const p of hist.value?.people || []) all.push(...Object.values(p.byDay || {}));
  return Math.max(1, ...all);
});
function sparkH(n) { return n ? Math.max(3, Math.round((n / sparkMax.value) * 22)) + "px" : "2px"; }

onMounted(() => { load(); loadHist(); });
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
// Intensity is RELATIVE to the board's busiest half-hour, not a fixed
// scale: a slow day still shows its own rhythm instead of a wash of the
// palest green.
const boardMax = computed(() => {
  let m = 1;
  for (const p of d.value?.people || [])
    for (const k in p.slots) m = Math.max(m, p.slots[k]);
  return m;
});
function cellCls(n) {
  if (!n) return "bg-stone-100";
  const r = n / boardMax.value;
  if (r >= 0.85) return "bg-emerald-600";
  if (r >= 0.6) return "bg-emerald-500";
  if (r >= 0.35) return "bg-emerald-400";
  if (r >= 0.15) return "bg-emerald-300";
  return "bg-emerald-200";
}
function cellStrong(n) { return n / boardMax.value >= 0.35; }
const isToday = computed(() => day.value === today);
function pace(p) {
  if (!p.first || !p.last || p.first === p.last) return p.actions;
  const [h0, m0] = p.first.split(":").map(Number);
  const [h1, m1] = p.last.split(":").map(Number);
  const hrs = Math.max(0.5, (h1 * 60 + m1 - h0 * 60 - m0) / 60);
  return Math.round(p.actions / hrs);
}
</script>
<style scoped>
.hm-now { box-shadow: 0 0 0 2px var(--accent-400); animation: hmPulse 2s ease-in-out infinite; }
@keyframes hmPulse { 0%, 100% { box-shadow: 0 0 0 2px var(--accent-400); } 50% { box-shadow: 0 0 0 2px transparent; } }
</style>
