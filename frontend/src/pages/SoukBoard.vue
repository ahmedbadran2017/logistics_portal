<template>
  <!-- The launch board: every souk product from purchase to Live, one column
       per stage, oldest first. A card is late when it sits in its stage past
       the stage's days; past 21 days from purchase without Live it escalates.
       On a phone the columns snap one by one; the filters narrow every column
       at once. Backend: souk.board. Look = design Main.dc.html (1280px). -->
  <div class="max-w-[1400px] mx-auto px-4 sm:px-5 pt-5 sm:pt-6 pb-10 flex flex-col gap-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div class="min-w-0 flex flex-col gap-0.5">
        <h1 class="text-[20px] font-bold tracking-[-0.01em] text-stone-900">{{ t('souk.boardTitle') }}</h1>
        <p class="text-[13px] text-stone-500 max-w-[680px]">{{ t('souk.boardIntro') }}</p>
      </div>
      <div class="flex gap-2 items-center flex-wrap w-full sm:w-auto">
        <label class="basis-full sm:basis-auto sm:flex-none">
          <span class="sr-only">{{ t('souk.lb.searchLbl') }}</span>
          <input v-model="q" type="search" :placeholder="t('souk.lb.search')"
                 class="h-11 lg:h-9 w-full sm:w-[220px] rounded-lg bg-white border border-stone-200 px-3 text-[14px] text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-[var(--accent-500)]" />
        </label>
        <router-link :to="{ name: 'SoukTrip' }"
                     class="h-11 lg:h-9 px-3 flex-1 sm:flex-none justify-center rounded-lg bg-white ring-1 ring-inset ring-stone-300 text-stone-900 text-[14px] font-semibold inline-flex items-center gap-1.5 whitespace-nowrap hover:bg-stone-50">
          <span v-if="data">{{ fill(t('souk.lb.tripsOpen'), { n: data.openTrips || 0 }) }}</span>
          <span v-else>{{ t('souk.lb.trips') }}</span>
        </router-link>
        <router-link v-if="data?.canBuy" :to="{ name: 'SoukBuy' }"
                     class="h-11 lg:h-9 px-3.5 flex-1 sm:flex-none justify-center rounded-lg bg-[var(--accent-600)] hover:bg-[var(--accent-700)] text-white text-[14px] font-semibold inline-flex items-center gap-1.5 whitespace-nowrap">
          <Icon name="plus" :size="14" :stroke-width="2.5" />{{ t('souk.lb.newProduct') }}
        </router-link>
        <button type="button" class="h-11 w-11 lg:h-9 lg:w-9 shrink-0 rounded-lg bg-white ring-1 ring-inset ring-stone-200 text-stone-600 inline-flex items-center justify-center hover:bg-stone-50 disabled:opacity-50"
                :disabled="loading" :aria-label="t('souk.lb.refresh')" :title="t('souk.lb.refresh')" @click="load">
          <Icon name="rotate-ccw" :size="15" :class="loading ? 'animate-spin' : ''" />
        </button>
      </div>
    </header>

    <!-- KPIs -->
    <section v-if="data" :aria-label="t('souk.lb.kpis')" class="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
      <div class="tile">
        <span class="tile-k">{{ t('souk.kNotLive') }}</span>
        <span class="tile-v">{{ fmt(data.notLive) }} <small class="tile-u">MAD</small></span>
        <span class="tile-s">{{ fill(t('souk.lb.kNotLiveSub'), { n: kpi.inCycle ?? 0, u: fmt(kpi.units) }) }}</span>
      </div>
      <div class="tile">
        <span class="tile-k">{{ t('souk.lb.kR2L') }}</span>
        <span v-if="kpi.receiptToLive != null" class="tile-v" :class="kpi.receiptToLive > target ? 'text-rose-800' : ''">
          {{ kpi.receiptToLive }} <small class="tile-u">{{ t('souk.lb.days').replace('{n}', '').trim() }}</small>
        </span>
        <span v-else class="text-[15px] font-bold text-stone-500 leading-8">{{ t('souk.lb.noData') }}</span>
        <span class="tile-s">
          {{ kpi.receiptToLive != null
            ? fill(t('souk.lb.kR2LSub'), { t: target, n: kpi.receiptToLiveN || 0 })
            : fill(t('souk.lb.kR2LNone'), { t: target }) }}
        </span>
      </div>
      <div class="tile" :class="data.late ? 'tile-late' : ''">
        <!-- A problem carries a mark, not only a colour: the late rose sits too
             close to the terracotta of the actions to be read by hue alone. -->
        <span class="tile-k inline-flex items-center gap-1" :class="data.late ? 'text-rose-700' : ''">
          <Icon v-if="data.late" name="alert-triangle" :size="13" />{{ t('souk.lb.kLate') }}
        </span>
        <span class="tile-v" :class="data.late ? 'text-rose-800' : ''">{{ data.late }}</span>
        <span class="tile-s" :class="data.late ? 'text-rose-800' : ''">
          {{ lateTop ? fill(t('souk.lb.kLateSub'), { s: t('souk.st_' + lateTop.s), n: lateTop.n }) : t('souk.lb.kLateNone') }}
        </span>
      </div>
      <div class="tile">
        <span class="tile-k">{{ t('souk.lb.kSell') }}</span>
        <span v-if="kpi.sellThrough != null" class="tile-v">{{ kpi.sellThrough }}%</span>
        <span v-else class="text-[15px] font-bold text-stone-500 leading-8">{{ t('souk.lb.noData') }}</span>
        <span class="tile-s">
          {{ fill(t('souk.lb.kSellSub'), { s: fmt(kpi.soldMonth), b: fmt(kpi.boughtMonth), n: kpi.launchedMonth || 0 }) }}
        </span>
      </div>
    </section>

    <!-- where the time goes -->
    <section v-if="data" :aria-label="t('souk.lb.timeTitle')" class="bg-white rounded-xl ring-1 ring-inset ring-stone-200 px-4 py-3 flex flex-col gap-2">
      <div class="flex justify-between gap-x-3 gap-y-0.5 text-[13px] flex-wrap">
        <span class="font-semibold text-stone-700">{{ t('souk.lb.timeTitle') }}</span>
        <span v-if="timeSegs.length" class="text-stone-500 tabular-nums">{{ fill(t('souk.lb.timeTotal'), { n: round1(timeTotal) }) }}</span>
      </div>
      <template v-if="timeSegs.length">
        <div class="flex h-[26px] rounded-md overflow-hidden text-[12px] font-semibold">
          <div v-for="g in timeSegs" :key="g.s"
               class="flex items-center justify-center min-w-[4px] overflow-hidden whitespace-nowrap px-1 tabular-nums"
               :class="g.cls" :style="{ width: (g.avg / timeTotal * 100) + '%' }"
               :title="t('souk.st_' + g.s) + ' · ' + g.avg + (g.limit ? ' / ' + g.limit : '') + ' · ' + fill(t('souk.lb.timeN'), { n: g.n })">
            <span v-if="g.avg / timeTotal >= 0.3" class="truncate">{{ t('souk.st_' + g.s) }} {{ g.avg }}</span>
            <span v-else-if="g.avg / timeTotal >= 0.07">{{ g.avg }}</span>
          </div>
        </div>
        <div class="flex gap-x-4 gap-y-1 text-[12px] flex-wrap">
          <span v-for="g in timeSegs" :key="g.s" class="tabular-nums"
                :class="g.over ? 'text-rose-700 font-semibold' : 'text-stone-600'" :title="fill(t('souk.lb.timeN'), { n: g.n })">
            {{ t('souk.st_' + g.s) }} {{ g.over ? fill(t('souk.lb.timeOf'), { a: g.avg, l: g.limit }) : g.avg }}
          </span>
        </div>
      </template>
      <div v-else class="text-[13px] text-stone-500">{{ t('souk.lb.noData') }}</div>
    </section>

    <!-- filters: design order — all, late, trip, buyer, stall, mine, left the cycle -->
    <div v-if="data" class="flex gap-1.5 items-center overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 sm:pb-0 sm:flex-wrap">
      <button v-for="m in modes.slice(0, 2)" :key="m.k" type="button" class="chip"
              :class="mode === m.k ? 'chip-on' : m.k === 'late' && m.n ? 'text-rose-700' : ''"
              :aria-pressed="mode === m.k" @click="mode = m.k">
        {{ t('souk.lb.f_' + m.k) }} · {{ m.n }}
      </button>
      <select v-model="trip" class="chip chip-select" :class="trip ? 'chip-set' : ''" :aria-label="t('souk.lb.tripAll')">
        <option value="">{{ t('souk.lb.tripAll') }}</option>
        <option v-for="o in trips" :key="o" :value="o">{{ o }}</option>
      </select>
      <select v-model="buyer" class="chip chip-select" :class="buyer ? 'chip-set' : ''" :aria-label="t('souk.lb.buyerAll')">
        <option value="">{{ t('souk.lb.buyerAll') }}</option>
        <option v-for="o in buyers" :key="o.v" :value="o.v">{{ o.l }}</option>
      </select>
      <select v-model="stall" class="chip chip-select" :class="stall ? 'chip-set' : ''" :aria-label="t('souk.lb.stallAll')">
        <option value="">{{ t('souk.lb.stallAll') }}</option>
        <option v-for="o in stalls" :key="o" :value="o">{{ o }}</option>
      </select>
      <button v-for="m in modes.slice(2)" :key="m.k" type="button" class="chip"
              :class="mode === m.k ? 'chip-on' : ''" :aria-pressed="mode === m.k" @click="mode = m.k">
        {{ t('souk.lb.f_' + m.k) }}<template v-if="m.k !== 'mine' || m.n"> · {{ m.n }}</template>
      </button>
      <button v-if="filtered" type="button" class="chip !shadow-none !bg-transparent text-stone-500 inline-flex items-center gap-1" @click="clear">
        <Icon name="x" :size="13" />{{ t('souk.lb.clear') }}
      </button>
    </div>

    <div v-if="loading && !data" class="h-[360px] rounded-xl bg-white ring-1 ring-inset ring-stone-200 animate-pulse" />

    <!-- dropped: one list, why and from where -->
    <section v-if="data && mode === 'dropped'" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2.5">
      <router-link v-for="c in shown" :key="c.name" :to="{ name: 'SoukProduct', params: { name: c.name } }"
                   class="bg-white rounded-xl ring-1 ring-inset ring-stone-200 hover:ring-stone-400 p-3 flex flex-col gap-2">
        <div class="flex gap-2 items-start">
          <Thumb :src="c.image" />
          <div class="min-w-0 flex-1 flex flex-col gap-px">
            <span class="text-[13px] font-semibold text-stone-900 leading-[1.35] line-clamp-2">{{ c.title }}</span>
            <span class="mono text-[11px] text-stone-600 truncate"><bdi dir="ltr">{{ c.name }}</bdi></span>
          </div>
          <span class="text-[11px] font-bold px-[7px] py-0.5 h-fit rounded-md bg-stone-100 text-stone-700 whitespace-nowrap">{{ whyLabel(c.note) }}</span>
        </div>
        <div class="text-[12px] text-stone-600 flex justify-between gap-2 tabular-nums">
          <span class="truncate">{{ c.droppedFrom ? fill(t('souk.lb.leftAt'), { s: t('souk.st_' + c.droppedFrom) }) : t('souk.st_dropped') }}</span>
          <span class="whitespace-nowrap">{{ c.units }} {{ t('souk.pcs') }} · {{ fmt(c.cost) }} MAD</span>
        </div>
        <div v-if="noteText(c.note)" class="text-[13px] text-stone-800 bg-stone-50 rounded-lg px-2.5 py-1.5 break-words">{{ noteText(c.note) }}</div>
        <div class="text-[12px] text-stone-500 truncate">{{ [c.stall, c.buyerName].filter(Boolean).join(' · ') }}</div>
      </router-link>
      <div v-if="!shown.length" class="col-span-full text-center text-[13px] text-stone-500 py-10">
        {{ data.droppedCards?.length ? t('souk.lb.none') : t('souk.lb.noneDropped') }}
      </div>
    </section>

    <!-- the columns -->
    <div v-else-if="data">
     <!-- Phone: one column at a time, so a stage bar says where you are and
          jumps to any stage (with its count, and a red dot when late). -->
     <div ref="stageBar" class="sm:hidden sticky top-0 z-10 -mx-4 px-4 py-2 mb-2 souk-glass border-b border-stone-200 flex gap-1.5 overflow-x-auto">
       <button v-for="(s, i) in data.stages" :key="s" type="button"
               class="h-10 ps-3 pe-2 rounded-full text-[13px] font-semibold whitespace-nowrap flex items-center gap-1.5 shrink-0 transition-colors"
               :class="activeCol === i ? 'bg-stone-900 text-white' : 'bg-white ring-1 ring-inset ring-stone-200 text-stone-700'"
               :aria-current="activeCol === i ? 'true' : undefined" @click="goCol(i)">
         {{ s === 'live' ? t('souk.lb.colLive') : t('souk.st_' + s) }}
         <span class="min-w-[20px] h-5 px-1 rounded-full text-[12px] tabular-nums flex items-center justify-center"
               :class="activeCol === i ? 'bg-white/20' : 'bg-stone-100 text-stone-600'">{{ col(s).length }}</span>
         <span v-if="col(s).some((c) => c.late || c.error)" class="w-1.5 h-1.5 -ms-0.5 rounded-full bg-rose-600" />
       </button>
     </div>
     <div ref="strip" class="overflow-x-auto pb-1.5 -mx-4 px-4 sm:mx-0 sm:px-0 snap-x snap-mandatory sm:snap-none scroll-px-4" @scroll.passive="onStrip">
      <div class="flex gap-2.5 min-w-max items-start sm:grid sm:min-w-[1240px] sm:[grid-template-columns:repeat(var(--cols),minmax(172px,1fr))]"
           :style="{ '--cols': data.stages.length }">
        <section v-for="s in data.stages" :key="s" :aria-label="s === 'live' ? t('souk.lb.colLive') : t('souk.st_' + s)"
                 class="w-[80vw] max-w-[300px] sm:w-auto sm:max-w-none shrink-0 snap-start bg-stone-200 rounded-xl p-2 flex flex-col gap-2">
          <div class="px-1.5 pt-1 pb-0.5 flex flex-col gap-px">
            <div class="flex items-baseline justify-between gap-2">
              <span class="text-[13px] font-bold text-stone-900 truncate">{{ s === 'live' ? t('souk.lb.colLive') : t('souk.st_' + s) }}</span>
              <span class="text-[12px] font-semibold text-stone-600 tabular-nums">{{ col(s).length }}</span>
            </div>
            <span class="text-[12px] text-stone-600 tabular-nums">
              <template v-if="s === 'live'">{{ fill(t('souk.lb.colSold'), { n: fmt(colSold(s)) }) }}</template>
              <template v-else>{{ fmt(colSum(s)) }} MAD</template>
              <template v-if="data.stageDays?.[s]"> · {{ fill(t('souk.lb.colDeadline'), { n: data.stageDays[s] }) }}</template>
            </span>
          </div>
          <div v-for="c in col(s)" :key="c.name" class="flex flex-col gap-1">
            <router-link :to="{ name: 'SoukProduct', params: { name: c.name } }"
                         class="bg-white rounded-[10px] p-[9px] flex flex-col gap-[7px] ring-inset text-stone-900"
                         :class="hot(c) ? 'ring-[1.5px] ring-rose-600' : 'ring-1 ring-stone-200 hover:ring-stone-400'">
              <div class="flex gap-2 items-start">
                <Thumb :src="c.image" />
                <div class="min-w-0 flex-1 flex flex-col gap-px">
                  <span class="text-[13px] font-semibold leading-[1.35] line-clamp-2">{{ c.title }}</span>
                  <span class="mono text-[11px] text-stone-600 truncate"><bdi dir="ltr">{{ c.name }}</bdi></span>
                </div>
              </div>
              <div class="flex justify-between gap-2 text-[12px] text-stone-600 tabular-nums">
                <span class="min-w-0">{{ c.stage === 'live' ? fill(t('souk.lb.soldOf'), { s: c.sold ?? 0, u: c.units }) : variantLine(c) }}</span>
                <span class="whitespace-nowrap">{{ fmt(c.cost) }} MAD</span>
              </div>
              <div class="flex items-center justify-between gap-2">
                <span class="text-[11px] font-bold px-[7px] py-0.5 rounded-md tabular-nums whitespace-nowrap truncate"
                      :class="c.error || c.late ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-700'">{{ agePill(c) }}</span>
                <span v-if="c.claimedBy" role="img"
                      class="w-[22px] h-[22px] shrink-0 rounded-full ring-1 ring-inset text-[11px] font-bold flex items-center justify-center"
                      :class="c.claimedBy === data.me ? 'bg-[var(--accent-50)] ring-[var(--accent-300)] text-[var(--accent-700)]' : 'bg-stone-100 ring-stone-300 text-stone-700'"
                      :title="c.claimedBy === data.me ? t('souk.lb.youHaveIt') : fill(t('souk.lb.hasIt'), { n: c.claimedName || c.claimedBy })"
                      :aria-label="c.claimedBy === data.me ? t('souk.lb.youHaveIt') : fill(t('souk.lb.hasIt'), { n: c.claimedName || c.claimedBy })">{{ initial(c.claimedName || c.claimedBy) }}</span>
              </div>
              <div v-if="c.error" class="text-[11px] text-rose-700 line-clamp-2 break-words">{{ c.error }}</div>
              <div v-if="c.escalate" class="text-[11px] font-bold text-rose-700 inline-flex items-center gap-1">
                <Icon name="alert-triangle" :size="12" />{{ fill(t('souk.lb.escalated'), { n: Math.floor(c.sinceBuy) }) }}
              </div>
            </router-link>
            <router-link v-if="c.stage === 'bought' && c.po && data.canReceive" :to="{ name: 'SoukReceive', params: { po: c.po } }"
                         class="act bg-[var(--accent-600)] hover:bg-[var(--accent-700)]">{{ t('souk.receiveBtn') }}</router-link>
            <router-link v-if="c.stage === 'photos' && data.canPhoto" :to="{ name: 'SoukPhoto', params: { name: c.name } }"
                         class="act bg-stone-900">{{ t('souk.shootBtn') }}</router-link>
            <router-link v-if="c.stage === 'studio' && data.canStudio" :to="{ name: 'SoukStudio', params: { name: c.name } }"
                         class="act bg-stone-900">{{ t('souk.finalsBtn') }}</router-link>
            <router-link v-if="c.stage === 'content' && data.canContent" :to="{ name: 'SoukContent', params: { name: c.name } }"
                         class="act bg-stone-900">{{ t('souk.contentBtn') }}</router-link>
            <router-link v-if="c.stage === 'review' && data.canReview" :to="{ name: 'SoukReview', params: { name: c.name } }"
                         class="act bg-[var(--accent-600)] hover:bg-[var(--accent-700)]">{{ t('souk.reviewBtn') }}</router-link>
          </div>
          <div v-if="!col(s).length" class="text-center text-[12px] text-stone-500 py-4">—</div>
        </section>
      </div>
      <p v-if="filtered && !shown.length" class="text-center text-[13px] text-stone-500 py-3">{{ t('souk.lb.none') }}</p>
     </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { warn } = useToast();
const data = ref(null);
const loading = ref(true);
const q = ref("");
const mode = ref("all"); // all | late | mine | dropped
const trip = ref("");
const stall = ref("");
const buyer = ref("");

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const round1 = (n) => Math.round(Number(n || 0) * 10) / 10;
const fill = (s, vars) => Object.entries(vars).reduce((o, [k, v]) => o.split("{" + k + "}").join(String(v)), String(s));
const initial = (n) => String(n || "?").trim().charAt(0).toUpperCase();
const firstName = (n) => String(n || "").split(/[\s@]/)[0];

// A card's thumbnail, or a quiet placeholder when there is none yet.
const Thumb = (props) => props.src
  ? h("img", { src: props.src, alt: "", loading: "lazy", class: "w-[38px] h-[38px] shrink-0 rounded-lg object-cover bg-stone-100" })
  : h("div", { class: "w-[38px] h-[38px] shrink-0 rounded-lg bg-stone-100 flex items-center justify-center text-stone-500" },
      [h(Icon, { name: "image", size: 15 })]);
Thumb.props = ["src"];

const kpi = computed(() => data.value?.kpi || {});
const target = computed(() => kpi.value.launchDays || 5);

/** Days → "6 h" under a day, "2.5 d" under ten, "12 d" after. */
function dur(days) {
  const d = Math.max(0, Number(days) || 0);
  if (d < 1) return t("souk.lb.hours").replace("{n}", Math.max(1, Math.round(d * 24)));
  return t("souk.lb.days").replace("{n}", d < 10 ? round1(d) : Math.round(d));
}
function agePill(c) {
  if (c.stage === "live") return fill(t("souk.lb.liveFor"), { d: dur(c.age) });
  if (c.error) return t("souk.lb.error");
  if (c.late && c.limit) return fill(t("souk.lb.lateBy"), { d: dur(c.age - c.limit) });
  return fill(t("souk.lb.inStage"), { d: dur(c.age) });
}
function variantLine(c) {
  const parts = [];
  if (c.colors) parts.push(c.colors === 1 ? t("souk.lb.colour1") : t("souk.lb.colours").replace("{n}", c.colors));
  if (c.sizes) parts.push(c.sizes === 1 ? t("souk.lb.size1") : t("souk.lb.sizes").replace("{n}", c.sizes));
  if (!parts.length && c.variants > 1) parts.push(t("souk.lb.variantsN").replace("{n}", c.variants));
  parts.push(c.units + " " + t("souk.pcs"));
  return parts.join(" · ");
}
// review_drop stores the note as "<why>: <text>".
const whyOf = (note) => (/^(return|clearance):/.exec(note || "") || [])[1] || "";
const whyLabel = (note) => (whyOf(note) ? t("souk.lb.why_" + whyOf(note)) : t("souk.st_dropped"));
const noteText = (note) => String(note || "").replace(/^(return|clearance):\s*/, "");

// --- filters -----------------------------------------------------------------
const everyCard = computed(() => [...(data.value?.cards || []), ...(data.value?.droppedCards || [])]);
const uniq = (xs) => [...new Set(xs.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b)));
const trips = computed(() => uniq(everyCard.value.map((c) => c.trip)).reverse());
const stalls = computed(() => uniq(everyCard.value.map((c) => c.stall)));
const buyers = computed(() => {
  const m = new Map();
  for (const c of everyCard.value) if (c.buyer) m.set(c.buyer, c.buyerName || c.buyer);
  return [...m].map(([v, l]) => ({ v, l })).sort((a, b) => a.l.localeCompare(b.l));
});
const modes = computed(() => {
  const cards = data.value?.cards || [];
  return [
    { k: "all", n: cards.length },
    { k: "late", n: data.value?.late ?? cards.filter((c) => c.late).length },
    { k: "mine", n: cards.filter((c) => c.mine).length },
    { k: "dropped", n: data.value?.dropped ?? (data.value?.droppedCards || []).length },
  ];
});
const filtered = computed(() => !!(q.value.trim() || trip.value || stall.value || buyer.value || mode.value === "late" || mode.value === "mine"));
function clear() {
  q.value = ""; trip.value = ""; stall.value = ""; buyer.value = "";
  if (mode.value !== "dropped") mode.value = "all";
}
const shown = computed(() => {
  const pool = mode.value === "dropped" ? data.value?.droppedCards || [] : data.value?.cards || [];
  const needle = q.value.trim().toLowerCase();
  return pool.filter((c) => {
    if (mode.value === "late" && !c.late) return false;
    if (mode.value === "mine" && !c.mine) return false;
    if (trip.value && c.trip !== trip.value) return false;
    if (stall.value && c.stall !== stall.value) return false;
    if (buyer.value && c.buyer !== buyer.value) return false;
    if (needle && ![c.title, c.name, c.stall, c.buyerName, c.buyer, c.brand]
      .some((x) => String(x || "").toLowerCase().includes(needle))) return false;
    return true;
  });
});
const col = (s) => shown.value.filter((c) => c.stage === s);

// Phone stage bar ⇄ the snapping column strip.
const strip = ref(null);
const stageBar = ref(null);
const activeCol = ref(0);
function goCol(i) {
  const sec = strip.value?.querySelectorAll(":scope > div > section")[i];
  if (sec) sec.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });
  activeCol.value = i;
}
let stripRaf = 0;
function onStrip() {
  cancelAnimationFrame(stripRaf);
  stripRaf = requestAnimationFrame(() => {
    const box = strip.value?.getBoundingClientRect();
    if (!box) return;
    const mid = box.left + box.width / 2;
    let best = 0, gap = Infinity;
    strip.value.querySelectorAll(":scope > div > section").forEach((sec, i) => {
      const r = sec.getBoundingClientRect();
      const d = Math.abs(r.left + r.width / 2 - mid);
      if (d < gap) { gap = d; best = i; }
    });
    if (best !== activeCol.value) {
      activeCol.value = best;
      stageBar.value?.children[best]?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
    }
  });
}
// Late, failed or escalated: the card gets the design's 1.5px rose ring.
const hot = (c) => !!(c.late || c.error || c.escalate);
const colSum = (s) => col(s).reduce((a, c) => a + (Number(c.cost) || 0), 0);
const colSold = (s) => col(s).reduce((a, c) => a + (Number(c.sold) || 0), 0);

// --- KPI helpers -------------------------------------------------------------
const lateTop = computed(() => {
  const by = {};
  for (const c of data.value?.cards || []) if (c.late) by[c.stage] = (by[c.stage] || 0) + 1;
  const best = Object.entries(by).sort((a, b) => b[1] - a[1])[0];
  return best ? { s: best[0], n: best[1] } : null;
});
// Stage-time segments in cycle order — the same reading order as the columns.
const timeSegs = computed(() => {
  const st = kpi.value.stageTime || {};
  const days = data.value?.stageDays || {};
  const order = [...(data.value?.stages || []), ...Object.keys(st)];
  const seen = new Set();
  const segs = order.filter((s) => st[s] && st[s].avg > 0 && !seen.has(s) && seen.add(s))
    .map((s) => ({ s, avg: st[s].avg, n: st[s].n, limit: Number(days[s]) || 0, over: !!days[s] && st[s].avg > days[s] }));
  // Design: the stage that eats the most time is terracotta, the rest step
  // through the stone greys (dark text on the lightest one).
  const top = segs.reduce((b, g) => (!b || g.avg > b.avg ? g : b), null);
  const greys = ["bg-stone-600 text-white", "bg-stone-500 text-white", "bg-stone-400 text-stone-900"];
  let k = 0;
  return segs.map((g) => ({ ...g, cls: g === top ? "bg-[var(--accent-600)] text-white" : greys[k++ % greys.length] }));
});
const timeTotal = computed(() => timeSegs.value.reduce((a, g) => a + g.avg, 0) || 1);

async function load() {
  loading.value = true;
  try {
    data.value = await api("souk.board");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
/* KPI tile — design: white, radius 12, 1px inset #e7e5e4, 14px 16px. */
.tile {
  display: flex; flex-direction: column; gap: 2px; min-width: 0;
  padding: 14px 16px; border-radius: 12px; background: #fff;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
}
.tile-late { background: rgb(255 241 242); box-shadow: inset 0 0 0 1px rgb(254 205 211); }
.tile-k { font-size: 12px; font-weight: 600; color: rgb(120 113 108); }
.tile-v { font-size: 24px; font-weight: 800; line-height: 1.33; font-variant-numeric: tabular-nums; }
.tile-u { font-size: 14px; font-weight: 600; color: rgb(120 113 108); }
.tile-s { font-size: 12px; color: rgb(87 83 78); font-variant-numeric: tabular-nums; }
@media (max-width: 639px) {
  .tile { padding: 12px 14px; }
  .tile-v { font-size: 21px; }
}
:global(html[data-theme="dark"]) .tile { background: #292524; box-shadow: inset 0 0 0 1px rgb(68 64 60); }
:global(html[data-theme="dark"]) .tile-late { background: rgba(136, 19, 55, .3); box-shadow: inset 0 0 0 1px #9f1239; }
:global(html[data-theme="dark"]) .tile-k, :global(html[data-theme="dark"]) .tile-u { color: #a8a29e; }
:global(html[data-theme="dark"]) .tile-s { color: #c0bbb5; }

/* Filter chip — design: 30px pill, 12px/600, white + 1px inset ring;
   touch screens keep a 44px target. */
.chip {
  height: 2.75rem; flex-shrink: 0; padding-inline: 12px; border-radius: 9999px; border: 0;
  white-space: nowrap; font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums;
  background: #fff; color: rgb(68 64 60); box-shadow: inset 0 0 0 1px rgb(231 229 228);
}
.chip-on { background: rgb(28 25 23); color: #fff; box-shadow: none; }
.chip-set { box-shadow: inset 0 0 0 1.5px rgb(28 25 23); color: rgb(28 25 23); }
.chip-select { max-width: 220px; padding-inline-end: 2rem; }
@media (min-width: 1024px) { .chip { height: 30px; } }
:global(html[data-theme="dark"]) .chip:not(.chip-on) { background: #292524; color: #d6d3d1; box-shadow: inset 0 0 0 1px rgb(68 64 60); }
:global(html[data-theme="dark"]) .chip-on { background: #f5f5f4; color: #1c1917; }

/* The next-step button under a card. */
.act {
  display: flex; align-items: center; justify-content: center; height: 2.75rem;
  border-radius: 8px; color: #fff; font-size: 13px; font-weight: 700;
}
@media (min-width: 1024px) { .act { height: 2rem; } }
</style>
