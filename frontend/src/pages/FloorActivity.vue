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
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
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
