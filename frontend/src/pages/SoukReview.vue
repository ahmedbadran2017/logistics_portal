<template>
  <!-- Review & publish (1 day, never by the writer). The system checks what
       it can measure — a photo per colour, price above the cost with
       transport, weights, Shopify's quantity = what ee pushes from Next,
       vendor = house brand, French colour names; the reviewer ticks what only
       an eye sees. "Check again" reloads the system checks and KEEPS the
       ticks and the channels (they reset only on another product). Send back
       to the step that owns the problem (counted), drop it, or publish:
       channels → ACTIVE → studio samples back on the shelf → the next card
       in the queue opens. Backend: souk.review_boot / review_reject /
       review_drop / publish / qty_nudge. -->
  <div class="px-4 py-5 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <div v-if="d" class="text-[11.5px] font-semibold text-stone-500 flex flex-wrap items-center gap-x-1.5">
          <span>{{ t('souk.pub.reviewKicker').replace('{w}', d.writer || '—').replace('{r}', reviewerName) }}</span>
          <span v-if="!d.sameWriter" class="inline-flex items-center gap-1 text-emerald-700"><Icon name="check-circle" :size="13" />{{ t('souk.pub.oneEach') }}</span>
        </div>
        <h1 class="text-[20px] font-bold text-stone-900 truncate">{{ d ? (d.content.fr.title || d.title) : t('souk.reviewTitle') }}</h1>
        <p v-if="!d" class="text-[12.5px] text-stone-500 mt-0.5 max-w-[680px]">{{ t('souk.reviewIntro') }}</p>
        <div v-else-if="d.rejects" class="text-[11.5px] text-amber-700">{{ t('souk.returnedN').replace('{n}', d.rejects) }}</div>
      </div>
      <div v-if="d" class="flex gap-2 items-center flex-wrap">
        <span v-if="clock" class="text-[11.5px] font-bold rounded-md px-2 py-1 bg-white ring-1 tabular-nums"
              :class="clock.late ? 'ring-rose-200 text-rose-700' : 'ring-stone-200 text-stone-700'">{{ clock.text }}</span>
        <span v-if="dueText" class="text-[11.5px] text-stone-600 bg-white ring-1 ring-stone-200 rounded-md px-2 py-1 tabular-nums">{{ dueText }}</span>
        <a v-if="d.shopify && d.shopify.preview" :href="d.shopify.preview" target="_blank" rel="noopener"
           class="lp-tap h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center gap-1.5">
          <Icon name="external-link" :size="13" />{{ t('souk.previewSite') }}
        </a>
        <a v-if="d.shopifyAdmin" :href="d.shopifyAdmin" target="_blank" rel="noopener"
           class="lp-tap h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center gap-1.5">
          <Icon name="external-link" :size="13" />Shopify
        </a>
      </div>
    </header>

    <div v-if="loading && !data" class="h-[420px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <!-- nothing in the queue: the same card on the three screens -->
    <div v-else-if="data && !data.queue.length && !d" class="bg-white ring-1 ring-stone-200/70 rounded-2xl px-6 py-12 flex flex-col items-center text-center gap-3">
      <span class="w-12 h-12 rounded-full bg-stone-100 text-stone-500 inline-flex items-center justify-center"><Icon name="inbox" :size="22" /></span>
      <p class="text-[13.5px] font-semibold text-stone-700">{{ t('souk.reviewNone') }}</p>
      <router-link :to="{ name: 'SoukBoard' }" class="lp-tap h-10 px-4 rounded-xl bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center gap-1.5 hover:bg-stone-50">
        {{ t('souk.pub.toBoard') }}<Icon name="arrow-right" :size="14" class="rtl:rotate-180" />
      </router-link>
    </div>

    <div v-else-if="data" class="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4 items-start">
      <aside class="bg-white ring-1 ring-stone-200/70 rounded-2xl overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex justify-between text-[12px]">
          <b>{{ t('souk.nProducts').replace('{n}', data.queue.length) }}</b>
          <span class="text-stone-500">{{ t('souk.oldestFirst') }}</span>
        </div>
        <div v-if="!data.queue.length" class="p-6 text-center text-[12.5px] text-stone-500">{{ t('souk.reviewNone') }}</div>
        <router-link v-for="q in data.queue" :key="q.name" :to="{ name: 'SoukReview', params: { name: q.name } }"
                     class="flex items-center gap-2.5 px-3 py-2.5 border-b border-stone-100 last:border-0 min-h-[56px]"
                     :class="d && d.name === q.name ? 'bg-[var(--accent-50)]' : 'hover:bg-stone-50'">
          <img v-if="q.image" :src="q.image" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-10 h-10 rounded-lg bg-stone-100" />
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-semibold truncate">{{ q.title }}</div>
            <div class="text-[11px]" :class="q.mine ? 'text-amber-700' : 'text-stone-500'">{{ q.mine ? t('souk.youWroteIt') : t('souk.writtenBy').replace('{n}', q.writer || '—') }}</div>
          </div>
          <span class="text-[10.5px] font-bold rounded-full px-2 py-0.5 tabular-nums"
                :class="q.late ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-600'">{{ t('souk.ageDays').replace('{n}', q.age) }}</span>
        </router-link>
      </aside>

      <div v-if="!d" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-8 text-center text-[13px] text-stone-500">{{ t('souk.studioPick') }}</div>
      <div v-else class="space-y-4 min-w-0">
        <div v-if="d.sameWriter" class="bg-amber-50 ring-1 ring-amber-200 rounded-xl p-3 text-[12.5px] text-amber-900">{{ t('souk.sameWriter') }}</div>
        <div v-if="d.stage !== 'review'" class="bg-stone-50 ring-1 ring-stone-200 rounded-xl p-3 text-[12.5px] text-stone-700">{{ t('souk.reviewNotNow') }}</div>

        <div class="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-4 items-start">
          <!-- preview: the storefront page, in the language of the tab -->
          <section :aria-label="t('souk.pub.previewLbl')" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 sm:p-5 space-y-3 min-w-0">
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <div class="flex items-center gap-2">
                <span class="text-[12px] font-semibold text-stone-600">{{ t('souk.pub.previewLbl') }}</span>
                <div role="tablist" class="inline-flex gap-0.5 p-1 bg-stone-100 rounded-[10px]">
                  <button v-for="l in ['fr', 'ar']" :key="l" role="tab" :aria-selected="lang === l"
                          class="h-8 px-3 rounded-lg text-[12px] font-semibold"
                          :class="lang === l ? 'bg-white shadow-sm text-stone-900' : 'text-stone-600'" @click="lang = l">
                    {{ l === 'fr' ? t('souk.langFr') : t('souk.langAr') }}
                  </button>
                </div>
              </div>
              <span class="text-[10.5px] font-bold rounded-md px-2 py-0.5 bg-stone-100 text-stone-600">{{ (d.shopify && d.shopify.status) || 'DRAFT' }}</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5 rounded-[10px] p-4 sm:p-5 bg-[#faf8f4] text-[#16130f]"
                 :dir="lang === 'ar' ? 'rtl' : 'ltr'" :lang="lang">
              <div class="space-y-2 min-w-0">
                <img v-if="mainImg" :src="mainImg" class="w-full aspect-[4/5] object-cover rounded-[10px]" alt="" />
                <div v-else class="w-full aspect-[4/5] rounded-[10px] bg-stone-200" />
                <div class="grid grid-cols-5 gap-1.5">
                  <button v-for="f in d.finals" :key="f.url" class="aspect-square rounded-md overflow-hidden"
                          :class="mainImg === f.url ? 'ring-2 ring-[#16130f]' : 'ring-1 ring-stone-200'" @click="img = f.url">
                    <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                  </button>
                </div>
              </div>
              <div class="space-y-3 min-w-0">
                <h2 class="text-[20px] font-bold leading-snug">{{ d.content[lang].title || '—' }}</h2>
                <div class="text-[20px] font-extrabold tabular-nums text-[#c4301c]">
                  {{ priceLine.text }} <span v-if="priceLine.from" class="text-[13px] font-medium text-[#7a746b]">{{ shop('from') }}</span>
                </div>
                <div v-if="realColors.length > 1" class="space-y-1.5">
                  <div class="text-[12px] font-bold">{{ shop('color') }}</div>
                  <div class="flex gap-1.5 flex-wrap">
                    <span v-for="c in realColors" :key="c.code" class="h-8 px-3 rounded-full ring-1 ring-[#e3ddd3] text-[12px] font-semibold inline-flex items-center">{{ lang === 'ar' ? c.ar || c.fr : c.fr }}</span>
                  </div>
                </div>
                <div v-if="sizeRows.length > 1 || (sizeRows[0] && sizeRows[0].size)" class="space-y-1.5">
                  <div class="text-[12px] font-bold">{{ shop('size') }}</div>
                  <div class="flex gap-1.5 flex-wrap">
                    <span v-for="s in sizeRows" :key="s.size" class="h-[34px] px-3.5 rounded-full ring-1 ring-[#e3ddd3] text-[12.5px] font-bold inline-flex items-center tabular-nums">{{ s.size }} · {{ s.price }} MAD</span>
                  </div>
                </div>
                <div class="h-11 rounded-full bg-[#c4301c] text-white text-[14px] font-bold flex items-center justify-center text-center px-3">{{ shop('order') }}</div>
                <!-- Built server-side from plain text with every character escaped. -->
                <div class="souk-desc text-[13px] leading-relaxed text-[#46413a]" v-html="d.descHtml[lang]" />
              </div>
            </div>
            <div class="rounded-lg bg-stone-50 px-3.5 py-3 space-y-0.5" dir="ltr" lang="fr">
              <div class="text-[12px] text-stone-600 truncate">justyol.com › products › {{ d.content.handle }}</div>
              <div class="text-[16px] text-[#1a0dab] truncate">{{ d.content.metaTitle }}</div>
              <div class="text-[12.5px] text-stone-600 line-clamp-2">{{ d.content.metaDescription }}</div>
            </div>
          </section>

          <aside class="space-y-4 min-w-0">
            <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 space-y-2">
              <div class="flex items-center justify-between">
                <h3 class="text-[13px] font-bold">{{ t('souk.systemChecks') }}</h3>
                <button class="lp-tap h-8 px-2.5 rounded-lg text-[12px] font-semibold inline-flex items-center gap-1 hover:bg-stone-50 disabled:opacity-40"
                        :disabled="loading" @click="recheck">
                  <Icon name="refresh-cw" :size="13" :class="loading ? 'animate-spin' : ''" />{{ t('souk.recheck') }}
                </button>
              </div>
              <div v-for="k in d.checks" :key="k.key" class="flex items-start gap-2 text-[12.5px]">
                <span class="w-[18px] h-[18px] mt-px shrink-0 rounded-full text-[11px] font-bold inline-flex items-center justify-center text-white"
                      :class="k.ok ? 'bg-emerald-700' : k.hard ? 'bg-rose-600' : 'bg-amber-500'">{{ k.ok ? '✓' : k.hard ? '✗' : '!' }}</span>
                <div class="min-w-0 flex-1">
                  <div class="flex items-start justify-between gap-2">
                    <span :class="k.ok ? 'text-stone-800' : k.hard ? 'text-rose-800' : 'text-amber-900'">{{ t('souk.rk_' + k.key) }}</span>
                    <span v-if="k.detail && k.detail.length <= 24" class="text-[11.5px] text-stone-500 tabular-nums text-end shrink-0" dir="ltr">{{ k.detail }}</span>
                  </div>
                  <div v-if="k.detail && k.detail.length > 24" class="text-[11px] text-stone-500 break-words" dir="ltr">{{ k.detail }}</div>
                  <button v-if="k.key === 'qty' && !k.ok" class="lp-tap mt-1 h-8 text-[11.5px] font-semibold underline" :disabled="busy" @click="nudge">{{ t('souk.qtyNudge') }}</button>
                </div>
              </div>
            </section>

            <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 space-y-1">
              <h3 class="text-[13px] font-bold mb-1">{{ t('souk.eyeChecks') }}</h3>
              <label v-for="m in d.manual" :key="m" class="flex items-center gap-2.5 text-[12.5px] min-h-[36px] cursor-pointer">
                <input v-model="ticked" type="checkbox" :value="m" class="w-[18px] h-[18px] shrink-0 accent-[var(--accent-600)]" :disabled="!d.canPublish" />
                <span>{{ t('souk.mk_' + m) }}</span>
              </label>
            </section>

            <!-- something wrong -->
            <section v-if="d.stage === 'review' && !d.sameWriter" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 space-y-2">
              <h3 class="text-[13px] font-bold">{{ t('souk.somethingWrong') }}</h3>
              <div class="flex gap-2">
                <label for="rv-to" class="sr-only">{{ t('souk.pub.toLbl') }}</label>
                <select id="rv-to" v-model="back" class="flex-1 min-w-0 h-10 rounded-lg ring-1 ring-stone-300 px-2 text-[13px] bg-white">
                  <option value="content">{{ t('souk.backContent') }}</option>
                  <option value="studio">{{ t('souk.backStudio') }}</option>
                  <option value="photos">{{ t('souk.backPhotos') }}</option>
                  <option value="drop:return">{{ t('souk.dropReturn') }}</option>
                  <option value="drop:clearance">{{ t('souk.dropClearance') }}</option>
                </select>
                <button class="h-10 px-3 rounded-lg bg-white ring-1 ring-rose-200 text-rose-700 text-[12.5px] font-bold disabled:opacity-40 shrink-0"
                        :disabled="busy || !note.trim()" @click="sendBack">
                  {{ back.startsWith('drop') ? t('souk.dropIt') : t('souk.pub.returnBtn') }}
                </button>
              </div>
              <label for="rv-note" class="sr-only">{{ t('souk.pub.noteLbl') }}</label>
              <textarea id="rv-note" v-model="note" rows="2" class="w-full rounded-lg ring-1 ring-stone-300 px-2.5 py-2 text-[13px]" :placeholder="t('souk.noteRequired')" />
            </section>

            <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 space-y-1">
              <div class="flex items-baseline justify-between gap-2 mb-1">
                <h3 class="text-[13px] font-bold">{{ t('souk.channels') }}</h3>
                <span class="text-[11px] text-stone-500 text-end">{{ t('souk.channelsDefault') }}</span>
              </div>
              <div v-if="d.channelsError" class="text-[11.5px] text-rose-700 break-words">{{ d.channelsError }}</div>
              <label v-for="ch in d.channels" :key="ch.id" class="flex items-center gap-2.5 text-[12.5px] min-h-[36px] cursor-pointer">
                <input v-model="chosen" type="checkbox" :value="ch.id" class="w-[18px] h-[18px] shrink-0 accent-[var(--accent-600)]" :disabled="!d.canPublish" @change="chosenTouched = true" />
                <span class="flex-1 min-w-0 font-semibold truncate" dir="auto">{{ chLabel(ch) }}</span>
                <span v-if="chNote(ch)" class="text-[11px] text-stone-500 text-end shrink-0">{{ chNote(ch) }}</span>
              </label>
            </section>

            <div v-if="d.stage === 'review'" class="space-y-1.5">
              <p class="text-[12px] font-semibold text-stone-700 text-center">{{ summary }}</p>
              <button class="w-full h-[52px] rounded-xl bg-[var(--accent-600)] text-white text-[15px] font-bold disabled:bg-stone-200 disabled:text-stone-500"
                      :disabled="busy || !canPublish" @click="publish">
                {{ busy ? t('souk.sending') : t('souk.publish') }}
              </button>
              <p v-if="!canPublish" class="text-[11.5px] text-stone-500 text-center">{{ blockedWhy }}</p>
              <p v-else-if="d.samples.length" class="text-[11.5px] text-stone-500 text-center">{{ t('souk.samplesBack').replace('{n}', samplesN) }}</p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const { fullName } = useAuth();
const route = useRoute();
const router = useRouter();
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const lang = ref("fr");
const img = ref("");
const ticked = ref([]);
const chosen = ref([]);
const chosenTouched = ref(false);
const stateFor = ref(""); // the product the ticks and channels belong to
const back = ref("content");
const note = ref("");
const d = computed(() => data.value?.detail || null);

// The storefront's own words, in the preview's language (not the UI's).
const shop = (k) => t(`souk.pub.shop.${lang.value}.${k}`);
const reviewerName = computed(() => fullName.value || t("souk.pub.you"));
const mainImg = computed(() => img.value || d.value?.finals?.[0]?.url || d.value?.image || "");
const realColors = computed(() => (d.value?.colors || []).filter((c) => c.code));
const sizeRows = computed(() => {
  const out = {};
  for (const v of d.value?.variants || []) {
    const k = v.size || "";
    if (!(k in out)) out[k] = { size: k, price: d.value.content.prices[v.sku] };
  }
  return Object.values(out);
});
const priceLine = computed(() => {
  const ps = Object.values(d.value?.content?.prices || {}).map(Number).filter(Boolean);
  if (!ps.length) return { text: "—", from: false };
  const lo = Math.min(...ps);
  return { text: lo + " MAD", from: ps.some((p) => p !== lo) };
});
const samplesN = computed(() => (d.value?.samples || []).reduce((s, x) => s + (Number(x.qty) || 0), 0));
const summary = computed(() => t("souk.pub.summary").replace("{c}", chosen.value.length).replace("{s}", samplesN.value));

// Shopify names a channel after its catalog ("… for Online Store"); say
// what each one is, and never show a bare id as if it were a name.
const CH = [
  [/online store|boutique en ligne/i, "online"], [/headless|hydrogen/i, "headless"], [/google|youtube/i, "google"],
  [/facebook|instagram|meta/i, "meta"], [/tiktok/i, "tiktok"], [/point of sale|\bpos\b/i, "pos"],
  [/inbox/i, "inbox"], [/^shop$/i, "shop"],
];
const chLabel = (ch) => (/^\d+$/.test(String(ch.name || "")) ? t("souk.pub.channelN").replace("{n}", ch.name) : ch.name);
const chNote = (ch) => {
  const hit = CH.find(([re]) => re.test(String(ch.name || "")));
  const n = hit ? t("souk.pub.ch." + hit[1]) : "";
  return n && n.toLowerCase() !== String(ch.name || "").toLowerCase() ? n : "";
};

const dur = (h) => {
  const a = Math.abs(h);
  return a < 48 ? t("souk.pub.hours").replace("{n}", Math.round(a)) : t("souk.pub.days").replace("{n}", Math.round(a / 24));
};
const clock = computed(() => {
  const det = d.value;
  if (!det || det.hoursLeft == null) return null;
  const lim = Number(data.value?.limit) || 0;
  const late = det.hoursLeft < 0;
  const tail = late ? t("souk.pub.lateBy").replace("{n}", dur(det.hoursLeft)) : t("souk.pub.left").replace("{n}", dur(det.hoursLeft));
  if (!lim) return { late, text: tail };
  return { late, text: t("souk.pub.ofLimit").replace("{a}", dur(lim * 24 - det.hoursLeft)).replace("{l}", t("souk.pub.days").replace("{n}", lim)) + " · " + tail };
});
const dueText = computed(() => {
  const s = d.value?.deadline;
  if (!s) return "";
  const l = local(s); // site clock → the reader's clock
  return t("souk.pub.due").replace("{d}", l.slice(8, 10) + "/" + l.slice(5, 7) + " " + l.slice(11, 16));
});

const hardFail = computed(() => (d.value?.checks || []).filter((k) => k.hard && !k.ok));
const canPublish = computed(() => d.value && d.value.canPublish && !hardFail.value.length
  && ticked.value.length === d.value.manual.length && chosen.value.length > 0);
const blockedWhy = computed(() => {
  if (!d.value) return "";
  if (d.value.sameWriter) return t("souk.sameWriter");
  if (hardFail.value.length) return t("souk.blockedChecks").replace("{list}", hardFail.value.map((k) => t("souk.rk_" + k.key)).join(" · "));
  if (ticked.value.length < d.value.manual.length) return t("souk.blockedEye");
  if (!chosen.value.length) return t("souk.blockedChannels");
  return "";
});

async function load(keep = false) {
  loading.value = true;
  try {
    // A recheck asks for the product on screen, not "the first in the queue".
    const name = route.params.name || (keep ? d.value?.name : undefined);
    const next = await api("souk.review_boot", name ? { name } : {});
    const det = next.detail;
    data.value = next;
    if (det && det.name === stateFor.value) {
      // Same product: the reviewer's ticks and channels stay.
      ticked.value = ticked.value.filter((m) => det.manual.includes(m));
      const ids = new Set((det.channels || []).map((c) => c.id));
      chosen.value = chosen.value.filter((id) => ids.has(id));
      if (!chosen.value.length && !chosenTouched.value) chosen.value = [...(det.chosen || [])];
    } else {
      stateFor.value = det?.name || "";
      ticked.value = [];
      chosen.value = [...(det?.chosen || [])];
      chosenTouched.value = false;
      img.value = "";
      note.value = "";
      back.value = "content";
      lang.value = "fr";
    }
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

async function recheck() {
  await load(true);
  if (d.value && d.value.name === stateFor.value) success(t("souk.pub.rechecked"));
}

async function nudge() {
  busy.value = true;
  try {
    await apiPost("souk.qty_nudge", { name: d.value.name });
    success(t("souk.qtyNudged"));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

// After a publish / send back: the next card someone else wrote, in queue
// order after this one; none → the plain review route (the empty state, or
// whatever the server picks).
async function openNext(cur) {
  const q = data.value?.queue || [];
  const at = q.findIndex((x) => x.name === cur);
  const ring = [...q.slice(at + 1), ...q.slice(0, Math.max(at, 0))].filter((x) => x.name !== cur);
  const next = ring.find((x) => !x.mine);
  if (next) await router.push({ name: "SoukReview", params: { name: next.name } });
  else if (route.params.name) await router.push({ name: "SoukReview" });
  else await load();
  return !!next;
}

async function publish() {
  busy.value = true;
  const cur = d.value.name;
  try {
    const r = await apiPost("souk.publish", {
      name: cur, channels: JSON.stringify(chosen.value), manual: JSON.stringify(ticked.value),
    });
    const msg = t("souk.published").replace("{c}", r.channels).replace("{s}", r.samples);
    const more = await openNext(cur);
    success(msg + " " + (more ? t("souk.pub.nextOpened") : t("souk.pub.queueDone")));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load(true);
  } finally {
    busy.value = false;
  }
}

async function sendBack() {
  busy.value = true;
  const cur = d.value.name;
  try {
    if (back.value.startsWith("drop:")) {
      await apiPost("souk.review_drop", { name: cur, why: back.value.slice(5), note: note.value });
      success(t("souk.dropped"));
    } else {
      await apiPost("souk.review_reject", { name: cur, to: back.value, note: note.value });
      success(t("souk.sentBack"));
    }
    await openNext(cur);
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

watch(() => route.params.name, () => load());
onMounted(() => load());
</script>

<style scoped>
.souk-desc :deep(p) { margin: 0 0 0.5rem; }
.souk-desc :deep(ul) { list-style: disc; padding-inline-start: 1.25rem; margin: 0 0 0.5rem; }
</style>
