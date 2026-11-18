<template>
  <!-- The launch board: every souk product from purchase to Live, one column
       per stage, oldest first. A card is late when it sits in its stage past
       the stage's days; past 21 days from purchase without Live it escalates.
       On a phone the columns snap one by one; the filters narrow every column
       at once. Backend: souk.board -->
  <div class="px-4 py-5 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <h1 class="text-[20px] font-bold text-stone-900">{{ t('souk.boardTitle') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[680px]">{{ t('souk.boardIntro') }}</p>
      </div>
      <div class="flex gap-2 flex-wrap w-full sm:w-auto">
        <label class="relative basis-full sm:basis-auto sm:flex-none">
          <span class="sr-only">{{ t('souk.lb.searchLbl') }}</span>
          <Icon name="search" :size="15" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none" />
          <input v-model="q" type="search" :placeholder="t('souk.lb.search')"
                 class="h-11 w-full sm:w-[240px] rounded-lg bg-white ring-1 ring-stone-200 ps-9 pe-3 text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--accent-500)]" />
        </label>
        <router-link :to="{ name: 'SoukTrip' }" class="h-11 px-3 flex-1 sm:flex-none justify-center rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center gap-1.5 whitespace-nowrap">
          <Icon name="wallet" :size="14" />
          <span v-if="data">{{ fill(t('souk.lb.custodyOpen'), { n: data.openTrips || 0 }) }}</span>
          <span v-else>{{ t('souk.custody') }}</span>
        </router-link>
        <router-link v-if="data?.canBuy" :to="{ name: 'SoukBuy' }" class="h-11 px-3.5 flex-1 sm:flex-none justify-center rounded-lg bg-[var(--accent-600)] text-white text-[12.5px] font-bold inline-flex items-center gap-1.5 whitespace-nowrap">
          <Icon name="plus" :size="14" />{{ t('souk.lb.newProduct') }}
        </router-link>
        <button class="h-11 w-11 rounded-lg bg-white ring-1 ring-stone-200 inline-flex items-center justify-center disabled:opacity-50"
                :disabled="loading" :aria-label="t('souk.lb.refresh')" :title="t('souk.lb.refresh')" @click="load">
          <Icon name="rotate-ccw" :size="15" :class="loading ? 'animate-spin' : ''" />
        </button>
      </div>
    </header>

    <!-- KPIs -->
    <section v-if="data" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 sm:p-4 flex flex-col gap-0.5 min-w-0">
        <span class="text-[11.5px] font-semibold text-stone-500">{{ t('souk.kNotLive') }}</span>
        <span class="text-[22px] font-extrabold tabular-nums leading-tight">{{ fmt(data.notLive) }} <small class="text-[12px] font-semibold text-stone-400">MAD</small></span>
        <span class="text-[11.5px] text-stone-600 tabular-nums">{{ fill(t('souk.lb.kNotLiveSub'), { n: kpi.inCycle ?? 0, u: fmt(kpi.units) }) }}</span>
      </div>
      <div class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 sm:p-4 flex flex-col gap-0.5 min-w-0">
        <span class="text-[11.5px] font-semibold text-stone-500">{{ t('souk.lb.kR2L') }}</span>
        <span v-if="kpi.receiptToLive != null" class="text-[22px] font-extrabold tabular-nums leading-tight"
              :class="kpi.receiptToLive > target ? 'text-rose-700' : ''">
          {{ kpi.receiptToLive }} <small class="text-[12px] font-semibold text-stone-400">{{ t('souk.lb.days').replace('{n}', '').trim() }}</small>
        </span>
        <span v-else class="text-[15px] font-bold text-stone-400 leading-[30px]">{{ t('souk.lb.noData') }}</span>
        <span class="text-[11.5px] text-stone-600 tabular-nums">
          {{ kpi.receiptToLive != null
            ? fill(t('souk.lb.kR2LSub'), { t: target, n: kpi.receiptToLiveN || 0 })
            : fill(t('souk.lb.kR2LNone'), { t: target }) }}
        </span>
      </div>
      <div class="rounded-2xl p-3.5 sm:p-4 flex flex-col gap-0.5 min-w-0 ring-1"
           :class="data.late ? 'bg-rose-50 ring-rose-200' : 'bg-white ring-stone-200/70'">
        <span class="text-[11.5px] font-semibold" :class="data.late ? 'text-rose-700' : 'text-stone-500'">{{ t('souk.lb.kLate') }}</span>
        <span class="text-[22px] font-extrabold tabular-nums leading-tight" :class="data.late ? 'text-rose-800' : ''">{{ data.late }}</span>
        <span class="text-[11.5px]" :class="data.late ? 'text-rose-800' : 'text-stone-600'">
          {{ lateTop ? fill(t('souk.lb.kLateSub'), { s: t('souk.st_' + lateTop.s), n: lateTop.n }) : t('souk.lb.kLateNone') }}
        </span>
      </div>
      <div class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 sm:p-4 flex flex-col gap-0.5 min-w-0">
        <span class="text-[11.5px] font-semibold text-stone-500">{{ t('souk.lb.kSell') }}</span>
        <span v-if="kpi.sellThrough != null" class="text-[22px] font-extrabold tabular-nums leading-tight">{{ kpi.sellThrough }}%</span>
        <span v-else class="text-[15px] font-bold text-stone-400 leading-[30px]">{{ t('souk.lb.noData') }}</span>
        <span class="text-[11.5px] text-stone-600 tabular-nums">
          {{ fill(t('souk.lb.kSellSub'), { s: fmt(kpi.soldMonth), b: fmt(kpi.boughtMonth), n: kpi.launchedMonth || 0 }) }}
        </span>
      </div>
    </section>

    <!-- where the time goes -->
    <section v-if="data" class="bg-white ring-1 ring-stone-200/70 rounded-2xl px-4 py-3 space-y-2">
      <div class="flex justify-between gap-3 text-[12px] flex-wrap">
        <span class="font-semibold text-stone-700">{{ t('souk.lb.timeTitle') }}</span>
        <span v-if="timeSegs.length" class="text-stone-500 tabular-nums">{{ fill(t('souk.lb.timeTotal'), { n: round1(timeTotal) }) }}</span>
      </div>
      <template v-if="timeSegs.length">
        <div class="flex h-7 rounded-md overflow-hidden text-[11.5px] font-semibold text-white">
          <div v-for="(g, i) in timeSegs" :key="g.s"
               class="flex items-center justify-center min-w-[6px] overflow-hidden whitespace-nowrap px-1"
               :class="g.over ? 'bg-rose-500' : i % 2 ? 'bg-[var(--accent-500)]' : 'bg-[var(--accent-700)]'"
               :style="{ width: (g.avg / timeTotal * 100) + '%' }" :title="t('souk.st_' + g.s) + ' · ' + g.avg">
            <span v-if="g.avg / timeTotal >= 0.12" class="truncate">{{ g.avg }}</span>
          </div>
        </div>
        <div class="flex gap-x-4 gap-y-1 text-[11.5px] flex-wrap">
          <span v-for="(g, i) in timeSegs" :key="g.s" class="inline-flex items-center gap-1.5 tabular-nums"
                :class="g.over ? 'text-rose-700 font-semibold' : 'text-stone-600'" :title="fill(t('souk.lb.timeN'), { n: g.n })">
            <span class="w-2 h-2 rounded-full" :class="g.over ? 'bg-rose-500' : i % 2 ? 'bg-[var(--accent-500)]' : 'bg-[var(--accent-700)]'" />
            {{ t('souk.st_' + g.s) }} {{ g.limit ? fill(t('souk.lb.timeOf'), { a: g.avg, l: g.limit }) : g.avg }}
          </span>
        </div>
      </template>
      <div v-else class="text-[12px] text-stone-400">{{ t('souk.lb.noData') }}</div>
    </section>

    <!-- filters -->
    <div v-if="data" class="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 sm:flex-wrap">
      <button v-for="m in modes" :key="m.k" type="button"
              class="h-11 px-3.5 rounded-full text-[12.5px] font-semibold whitespace-nowrap shrink-0 tabular-nums"
              :class="mode === m.k ? 'bg-stone-900 text-white' : ['bg-white ring-1 ring-stone-200', m.k === 'late' && m.n ? 'text-rose-700' : 'text-stone-700']"
              :aria-pressed="mode === m.k" @click="mode = m.k">
        {{ t('souk.lb.f_' + m.k) }} · {{ m.n }}
      </button>
      <select v-model="trip" class="chip-select" :class="trip ? 'ring-stone-900 text-stone-900' : ''" :aria-label="t('souk.lb.tripAll')">
        <option value="">{{ t('souk.lb.tripAll') }}</option>
        <option v-for="o in trips" :key="o" :value="o">{{ o }}</option>
      </select>
      <select v-model="stall" class="chip-select" :class="stall ? 'ring-stone-900 text-stone-900' : ''" :aria-label="t('souk.lb.stallAll')">
        <option value="">{{ t('souk.lb.stallAll') }}</option>
        <option v-for="o in stalls" :key="o" :value="o">{{ o }}</option>
      </select>
      <select v-model="buyer" class="chip-select" :class="buyer ? 'ring-stone-900 text-stone-900' : ''" :aria-label="t('souk.lb.buyerAll')">
        <option value="">{{ t('souk.lb.buyerAll') }}</option>
        <option v-for="o in buyers" :key="o.v" :value="o.v">{{ o.l }}</option>
      </select>
      <button v-if="filtered" type="button" class="h-11 px-3 rounded-full text-[12.5px] font-semibold text-stone-500 whitespace-nowrap shrink-0 inline-flex items-center gap-1" @click="clear">
        <Icon name="x" :size="13" />{{ t('souk.lb.clear') }}
      </button>
    </div>

    <div v-if="loading && !data" class="h-[360px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <!-- dropped: one list, why and from where -->
    <section v-if="data && mode === 'dropped'" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
      <router-link v-for="c in shown" :key="c.name" :to="{ name: 'SoukProduct', params: { name: c.name } }"
                   class="bg-white rounded-xl ring-1 ring-stone-200 p-3 space-y-2 hover:ring-stone-400 block">
        <div class="flex gap-2.5">
          <Thumb :src="c.image" />
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-semibold text-stone-900 line-clamp-2">{{ c.title }}</div>
            <div class="text-[11px] font-mono text-stone-500" dir="ltr">{{ c.name }}</div>
          </div>
          <span class="text-[10.5px] font-bold px-2 py-0.5 h-fit rounded-md bg-stone-100 text-stone-700 whitespace-nowrap">{{ whyLabel(c.note) }}</span>
        </div>
        <div class="text-[11.5px] text-stone-600 flex justify-between gap-2 tabular-nums">
          <span>{{ c.droppedFrom ? fill(t('souk.lb.leftAt'), { s: t('souk.st_' + c.droppedFrom) }) : t('souk.st_dropped') }}</span>
          <span>{{ c.units }} {{ t('souk.pcs') }} · {{ fmt(c.cost) }} MAD</span>
        </div>
        <div v-if="noteText(c.note)" class="text-[12px] text-stone-800 bg-stone-50 rounded-lg px-2.5 py-1.5 break-words">{{ noteText(c.note) }}</div>
        <div class="text-[11px] text-stone-500 truncate">{{ [c.stall, c.buyerName].filter(Boolean).join(' · ') }}</div>
      </router-link>
      <div v-if="!shown.length" class="col-span-full text-center text-[12.5px] text-stone-400 py-10">
        {{ data.droppedCards?.length ? t('souk.lb.none') : t('souk.lb.noneDropped') }}
      </div>
    </section>

    <!-- the columns -->
    <div v-else-if="data">
     <!-- Phone: one column at a time, so a stage bar says where you are and
          jumps to any stage (with its count, and a red dot when late). -->
     <div class="sm:hidden sticky top-0 z-10 -mx-4 px-4 py-2 mb-1 souk-glass flex gap-1.5 overflow-x-auto" ref="stageBar">
       <button v-for="(s, i) in data.stages" :key="s" type="button"
               class="h-9 ps-3 pe-2.5 rounded-full text-[12.5px] font-semibold whitespace-nowrap flex items-center gap-1.5 shrink-0 transition-colors"
               :class="activeCol === i ? 'bg-stone-900 text-white' : 'bg-white ring-1 ring-stone-200 text-stone-600'"
               @click="goCol(i)">
         {{ s === 'live' ? t('souk.lb.colLive') : t('souk.st_' + s) }}
         <span class="min-w-[20px] h-5 px-1 rounded-full text-[11px] tabular-nums flex items-center justify-center"
               :class="activeCol === i ? 'bg-white/20' : 'bg-stone-100'">{{ col(s).length }}</span>
         <span v-if="col(s).some((c) => c.late || c.error)" class="w-1.5 h-1.5 rounded-full bg-rose-500" />
       </button>
     </div>
     <div ref="strip" class="overflow-x-auto pb-2 -mx-4 px-4 snap-x snap-mandatory sm:snap-none scroll-px-4" @scroll.passive="onStrip">
      <div class="flex gap-3 min-w-max items-start">
        <section v-for="s in data.stages" :key="s" class="w-[80vw] max-w-[300px] sm:w-[240px] shrink-0 snap-start bg-stone-100/80 rounded-2xl p-2 space-y-2">
          <div class="px-1.5 pt-1 pb-0.5">
            <div class="flex items-baseline justify-between gap-2">
              <span class="text-[12.5px] font-bold text-stone-800 truncate">{{ s === 'live' ? t('souk.lb.colLive') : t('souk.st_' + s) }}</span>
              <span class="text-[11.5px] font-semibold text-stone-600 tabular-nums">{{ col(s).length }}</span>
            </div>
            <div class="text-[11px] text-stone-500 tabular-nums flex gap-1.5 flex-wrap">
              <span v-if="s === 'live'">{{ fill(t('souk.lb.colSold'), { n: fmt(colSold(s)) }) }}</span>
              <span v-else>{{ fmt(colSum(s)) }} MAD</span>
              <span v-if="data.stageDays?.[s]">· {{ fill(t('souk.lb.colDeadline'), { n: data.stageDays[s] }) }}</span>
            </div>
          </div>
          <div v-for="c in col(s)" :key="c.name" class="space-y-1">
            <router-link :to="{ name: 'SoukProduct', params: { name: c.name } }"
                         class="block bg-white rounded-xl p-2.5 space-y-1.5 hover:ring-stone-400"
                         :class="c.late || c.error || c.escalate ? 'ring-[1.5px] ring-rose-400' : 'ring-1 ring-stone-200'">
              <div class="flex gap-2">
                <Thumb :src="c.image" />
                <div class="min-w-0 flex-1">
                  <div class="text-[12.5px] font-semibold text-stone-900 leading-snug line-clamp-2">{{ c.title }}</div>
                  <div class="text-[10.5px] font-mono text-stone-500 truncate" dir="ltr">{{ c.name }}<span v-if="c.brand"> · {{ c.brand }}</span></div>
                </div>
              </div>
              <div class="flex items-center justify-between gap-2 text-[11px] text-stone-600 tabular-nums">
                <span class="truncate">{{ c.stage === 'live' ? fill(t('souk.lb.soldOf'), { s: c.sold ?? 0, u: c.units }) : variantLine(c) }}</span>
                <span class="whitespace-nowrap">{{ fmt(c.cost) }} MAD</span>
              </div>
              <div v-if="c.stall || c.buyerName" class="text-[10.5px] text-stone-500 truncate">
                <span v-if="c.stall">{{ t('souk.stallShort') }} {{ c.stall }}</span>
                <span v-if="c.stall && c.buyerName"> · </span>
                <span v-if="c.buyerName">{{ c.buyerName }}</span>
              </div>
              <div class="flex items-center justify-between gap-2">
                <span class="text-[10.5px] font-bold px-1.5 py-0.5 rounded-md tabular-nums whitespace-nowrap"
                      :class="c.error || c.late ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-700'">{{ agePill(c) }}</span>
                <span v-if="c.claimedBy" class="inline-flex items-center gap-1 min-w-0 text-[10.5px] font-semibold"
                      :class="c.claimedBy === data.me ? 'text-[var(--accent-700)]' : 'text-stone-600'"
                      :title="c.claimedBy === data.me ? t('souk.lb.youHaveIt') : fill(t('souk.lb.hasIt'), { n: c.claimedName || c.claimedBy })">
                  <span class="w-[22px] h-[22px] shrink-0 rounded-full text-[10px] font-bold flex items-center justify-center"
                        :class="c.claimedBy === data.me ? 'bg-[var(--accent-50)] ring-1 ring-[var(--accent-300)]' : 'bg-stone-100 ring-1 ring-stone-300'">{{ initial(c.claimedName || c.claimedBy) }}</span>
                  <span class="truncate max-w-[90px]">{{ c.claimedBy === data.me ? t('souk.lb.youHaveIt') : firstName(c.claimedName || c.claimedBy) }}</span>
                </span>
              </div>
              <div v-if="c.error" class="text-[10.5px] text-rose-700 line-clamp-2 break-words">{{ c.error }}</div>
              <div v-if="c.escalate" class="text-[10.5px] font-bold text-rose-700 inline-flex items-center gap-1">
                <Icon name="alert-triangle" :size="12" />{{ fill(t('souk.lb.escalated'), { n: Math.floor(c.sinceBuy) }) }}
              </div>
            </router-link>
            <router-link v-if="c.stage === 'bought' && c.po && data.canReceive" :to="{ name: 'SoukReceive', params: { po: c.po } }"
                         class="flex h-11 rounded-lg bg-[var(--accent-600)] text-white text-[12px] font-bold items-center justify-center">{{ t('souk.receiveBtn') }}</router-link>
            <router-link v-if="c.stage === 'photos' && data.canPhoto" :to="{ name: 'SoukPhoto', params: { name: c.name } }"
                         class="flex h-11 rounded-lg bg-stone-900 text-white text-[12px] font-bold items-center justify-center">{{ t('souk.shootBtn') }}</router-link>
            <router-link v-if="c.stage === 'studio' && data.canStudio" :to="{ name: 'SoukStudio', params: { name: c.name } }"
                         class="flex h-11 rounded-lg bg-stone-900 text-white text-[12px] font-bold items-center justify-center">{{ t('souk.finalsBtn') }}</router-link>
            <router-link v-if="c.stage === 'content' && data.canContent" :to="{ name: 'SoukContent', params: { name: c.name } }"
                         class="flex h-11 rounded-lg bg-stone-900 text-white text-[12px] font-bold items-center justify-center">{{ t('souk.contentBtn') }}</router-link>
            <router-link v-if="c.stage === 'review' && data.canReview" :to="{ name: 'SoukReview', params: { name: c.name } }"
                         class="flex h-11 rounded-lg bg-[var(--accent-600)] text-white text-[12px] font-bold items-center justify-center">{{ t('souk.reviewBtn') }}</router-link>
          </div>
          <div v-if="!col(s).length" class="text-center text-[11px] text-stone-400 py-4">—</div>
        </section>
      </div>
      <p v-if="filtered && !shown.length" class="text-center text-[12.5px] text-stone-400 py-3">{{ t('souk.lb.none') }}</p>
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
  ? h("img", { src: props.src, alt: "", loading: "lazy", class: "w-10 h-10 shrink-0 rounded-lg object-cover ring-1 ring-stone-200" })
  : h("div", { class: "w-10 h-10 shrink-0 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center text-stone-300" },
      [h(Icon, { name: "image", size: 16 })]);
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
  return order.filter((s) => st[s] && st[s].avg > 0 && !seen.has(s) && seen.add(s))
    .map((s) => ({ s, avg: st[s].avg, n: st[s].n, limit: Number(days[s]) || 0, over: !!days[s] && st[s].avg > days[s] }));
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
.chip-select {
  height: 2.75rem;
  flex-shrink: 0;
  max-width: 220px;
  border-radius: 9999px;
  background-color: #fff;
  padding-inline: 0.875rem 2rem;
  font-size: 12.5px;
  font-weight: 600;
  color: rgb(68 64 60);
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  border: 0;
}
.chip-select.ring-stone-900 { box-shadow: inset 0 0 0 1.5px rgb(28 25 23); color: rgb(28 25 23); }
</style>
