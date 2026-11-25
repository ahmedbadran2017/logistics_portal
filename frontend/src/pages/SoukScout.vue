<template>
  <!-- The market round (جولة السوق): the person walking the wholesale
       markets registers each shop in four steps — storefront (+ the GPS fix
       taken at the same moment), business card (read by a model, checked by
       the person), Telegram (checked against its public page while still at
       the shop), market / place / what it sells. Saved through the outbox:
       a shop entered with no signal is kept on the phone and sent later.
       Backend: souk_scout.scout_boot / read_card / check_telegram / similar /
       save_visit / visit_photo. -->
  <div class="st-buying px-4 pt-4 pb-12 max-w-[560px] mx-auto flex flex-col gap-4">
    <div v-if="loading && !data" class="h-[220px] sk-sec animate-pulse" />

    <!-- ── home: today's round ─────────────────────────────────────────── -->
    <template v-else-if="step === 0 && data">
      <header class="sk-hero flex flex-col gap-3">
        <div class="flex items-start gap-3">
          <span class="sk-ico sk-ico-lg sk-ico-solid"><Icon name="map-pin" :size="20" :stroke-width="2" /></span>
          <div class="min-w-0 flex-1">
            <h1 class="text-[19px] font-extrabold text-stone-900 leading-tight">{{ t('souk.scout.title') }}</h1>
            <p class="text-[12px] text-stone-600 leading-normal">{{ t('souk.scout.sub') }}</p>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button type="button" class="cat inline-flex items-center gap-1" aria-pressed="true" @click="pickMarket(0)">
            <Icon name="map-pin" :size="13" />{{ draft.market || t('souk.scout.pickMarket') }}
          </button>
          <div v-if="data.seesAll" class="ms-auto inline-flex rounded-full ring-1 ring-inset ring-stone-200 bg-white p-0.5" role="group">
            <button v-for="w in ['me', 'all']" :key="w" type="button" class="seg" :aria-pressed="who === w" @click="setWho(w)">
              {{ t('souk.scout.who.' + w) }}
            </button>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-2">
          <div class="stat"><span>{{ t('souk.scout.stat.shops') }}</span><b>{{ data.stats.shops + waitingJobs.length }}</b></div>
          <div class="stat"><span>{{ t('souk.scout.stat.channels') }}</span><b>{{ data.stats.channels }}</b></div>
          <div class="stat" :class="waitingJobs.length ? 'stat-amber' : ''"><span>{{ t('souk.scout.stat.waiting') }}</span><b>{{ waitingJobs.length }}</b></div>
        </div>
      </header>

      <p v-if="!data.ready" class="rounded-xl bg-amber-50 text-amber-900 text-[13px] px-3 py-2.5 flex gap-2">
        <Icon name="info" :size="16" class="shrink-0 mt-0.5" />{{ t('souk.scout.notReady') }}
      </p>
      <p v-else-if="!outbox.online" class="rounded-xl bg-amber-50 text-amber-900 text-[13px] px-3 py-2.5 flex gap-2">
        <Icon name="upload-cloud" :size="16" class="shrink-0 mt-0.5" />{{ t('souk.scout.offline') }}
      </p>

      <button type="button" class="btn btn-st btn-big w-full" :disabled="!data.ready" @click="startShop">
        <Icon name="plus" :size="18" :stroke-width="2.4" />{{ hasDraft ? t('souk.scout.resume') : t('souk.scout.newShop') }}
      </button>
      <button v-if="hasDraft" type="button" class="text-[13px] text-stone-500 underline self-center -mt-2" @click="dropDraft">
        {{ t('souk.scout.dropDraft') }}
      </button>

      <section class="sk-sec">
        <div class="sk-sec-h"><span class="sk-ico sk-ico-sm"><Icon name="store" :size="14" /></span>
          <span class="sk-sec-t">{{ who === 'all' ? t('souk.scout.listAll') : t('souk.scout.list') }}</span>
        </div>
        <div v-if="!data.rows.length && !waitingJobs.length" class="px-5 py-8 text-center text-[14px] text-stone-600">
          {{ t('souk.scout.empty') }}
        </div>
        <ul v-else class="divide-y divide-stone-100">
          <li v-for="j in waitingJobs" :key="j.id" class="row">
            <span class="thumb"><Icon name="upload-cloud" :size="18" /></span>
            <div class="min-w-0 flex-1">
              <p class="nm" dir="ltr">{{ j.label }}</p>
              <p class="sub">{{ j.failed ? j.error : t('souk.scout.waitingRow') }}</p>
            </div>
            <span class="tag" :class="j.failed ? 'tag-rose' : 'tag-amber'">{{ j.failed ? t('souk.scout.failed') : t('souk.scout.queued') }}</span>
          </li>
          <li v-for="r in data.rows" :key="r.name" class="row">
            <img v-if="r.photo" :src="r.photo" alt="" class="thumb object-cover" loading="lazy" />
            <span v-else class="thumb"><Icon name="store" :size="18" /></span>
            <div class="min-w-0 flex-1">
              <p class="nm" dir="ltr">{{ r.label }}</p>
              <p class="sub">{{ [r.market, r.place].filter(Boolean).join(' · ') }}<template v-if="who === 'all'"> · {{ r.by }}</template> · <span dir="ltr">{{ local(r.at).slice(11, 16) }}</span></p>
              <p v-if="r.outcome !== 'new'" class="sub st-ink">{{ t('souk.scout.joined') }}</p>
              <p v-else-if="r.dup" class="sub text-amber-800">{{ tt('souk.scout.looksLike', { n: r.dup }) }}</p>
            </div>
            <span class="tag" :class="tgClass(r.tg)"><Icon :name="r.tg === 'public' ? 'send' : r.tg === 'private' ? 'unlock' : 'minus'" :size="11" />{{ t('souk.scout.tg.' + r.tg) }}</span>
          </li>
        </ul>
      </section>
    </template>

    <!-- ── steps 1–4 ──────────────────────────────────────────────────────── -->
    <template v-else-if="step >= 1 && step <= 4">
      <div class="flex items-center gap-2">
        <button type="button" class="w-10 h-10 -ms-2 rounded-full inline-flex items-center justify-center text-stone-600"
                :aria-label="t('souk.scout.back')" @click="back">
          <Icon :name="locale === 'ar' ? 'arrow-right' : 'chevron-left'" :size="20" />
        </button>
        <h1 class="flex-1 text-[17px] font-extrabold text-stone-900">{{ pickingMarket ? t('souk.scout.f.market') : t('souk.scout.step.' + step) }}</h1>
        <span v-if="!pickingMarket" class="text-[12px] text-stone-500 tabular-nums">{{ tt('souk.scout.stepOf', { n: step }) }}</span>
      </div>
      <div v-if="!pickingMarket" class="flex gap-1" aria-hidden="true">
        <div v-for="i in 4" :key="i" class="h-1 flex-1 rounded-full" :class="i <= step ? 'st-solid' : 'bg-stone-200'" />
      </div>

      <!-- 1. storefront + GPS -->
      <template v-if="step === 1">
        <label v-if="!shopUrl" for="sc-shop" class="shot">
          <Icon name="camera" :size="36" />
          <span class="text-[15px] font-bold">{{ t('souk.scout.shopShoot') }}</span>
          <span class="text-[12px] opacity-80">{{ t('souk.scout.shopHint') }}</span>
        </label>
        <img v-else :src="shopUrl" alt="" class="w-full max-h-[320px] object-cover rounded-2xl" />
        <input id="sc-shop" ref="shopInput" type="file" accept="image/*" capture="environment" class="sr-only" @change="onShop" />

        <div class="gps" :class="fixState">
          <span class="sk-ico"><Icon :name="fixState === 'ok' ? 'map-pin' : fixState === 'bad' ? 'alert-triangle' : 'hourglass'" :size="18" /></span>
          <div class="min-w-0 flex-1">
            <p class="text-[14px] font-bold text-stone-900">{{ t('souk.scout.gps.' + fixState) }}</p>
            <p v-if="fix" class="text-[12px] text-stone-600 tabular-nums">{{ tt('souk.scout.gps.acc', { n: Math.round(fix.acc) }) }}</p>
            <p v-else-if="fixState === 'bad'" class="text-[12px] text-stone-600">{{ t('souk.scout.gps.badHint') }}</p>
          </div>
          <a v-if="fix" :href="`https://maps.google.com/?q=${fix.lat},${fix.lng}`" target="_blank" rel="noopener"
             class="text-[12px] font-semibold st-ink underline">{{ t('souk.scout.gps.map') }}</a>
        </div>

        <div class="flex flex-col gap-2 mt-2">
          <button type="button" class="btn btn-st btn-big w-full" :disabled="!shopUrl" @click="step = 2">{{ t('souk.scout.next.card') }}</button>
          <label v-if="shopUrl" for="sc-shop" class="btn btn-line w-full">{{ t('souk.scout.retake') }}</label>
          <button v-else type="button" class="text-[13px] text-stone-500 underline self-center" @click="step = 2">{{ t('souk.scout.noPhoto') }}</button>
        </div>
      </template>

      <!-- 2. business card -->
      <template v-if="step === 2">
        <label v-if="!cardUrl && !manual" for="sc-card" class="shot shot-dash">
          <Icon name="file-text" :size="34" />
          <span class="text-[15px] font-bold">{{ t('souk.scout.cardShoot') }}</span>
          <span class="text-[12px] opacity-80">{{ t('souk.scout.cardHint') }}</span>
        </label>
        <input id="sc-card" type="file" accept="image/*" capture="environment" class="sr-only" @change="onCard" />

        <div v-if="reading" class="rounded-2xl st-tint px-4 py-8 text-center st-ink flex flex-col items-center gap-2">
          <Icon name="sparkles" :size="28" class="animate-pulse" />
          <span class="text-[14px] font-semibold">{{ t('souk.scout.reading') }}</span>
        </div>

        <template v-if="(cardUrl || manual) && !reading">
          <div v-if="cardUrl" class="flex items-center gap-3">
            <img :src="cardUrl" alt="" class="w-20 h-14 object-cover rounded-lg ring-1 ring-stone-200" />
            <p class="flex-1 text-[13px] leading-snug" :class="cardNoteClass">{{ cardNote }}</p>
            <label for="sc-card" class="text-[12px] font-semibold st-ink underline shrink-0">{{ t('souk.scout.retake') }}</label>
          </div>

          <div class="flex flex-col gap-3">
            <Field id="sc-name" :label="t('souk.scout.f.name')" :from="fromCard('name')">
              <input id="sc-name" v-model="draft.name" dir="ltr" autocomplete="off" autocapitalize="characters"
                     class="inp uppercase" :placeholder="t('souk.scout.f.namePh')" @blur="draft.name = cleanName(draft.name)" />
              <p v-if="arabicName" class="text-[12px] text-amber-800 mt-1">{{ t('souk.scout.f.latinOnly') }}</p>
            </Field>
            <Field id="sc-phone" :label="t('souk.scout.f.phone')" :from="fromCard('phone')">
              <input id="sc-phone" v-model="draft.phone" dir="ltr" inputmode="tel" autocomplete="off" class="inp" placeholder="06 61 23 45 67" />
            </Field>
            <Field id="sc-phone2" :label="t('souk.scout.f.phone2')" :from="fromCard('phone2')">
              <input id="sc-phone2" v-model="draft.phone2" dir="ltr" inputmode="tel" autocomplete="off" class="inp" placeholder="07 70 11 22 33" />
            </Field>
            <Field id="sc-ig" :label="t('souk.scout.f.instagram')" :from="fromCard('instagram')">
              <input id="sc-ig" v-model="draft.instagram" dir="ltr" autocomplete="off" class="inp" placeholder="@amine.deco" />
            </Field>
          </div>
        </template>

        <div class="flex flex-col gap-2 mt-2">
          <button v-if="cardUrl || manual" type="button" class="btn btn-st btn-big w-full" :disabled="reading" @click="toTelegram">
            {{ t('souk.scout.next.tg') }}
          </button>
          <button v-else type="button" class="btn btn-line w-full" @click="manual = true">{{ t('souk.scout.noCard') }}</button>
        </div>
      </template>

      <!-- 3. Telegram -->
      <template v-if="step === 3">
        <div class="flex gap-1.5" role="group">
          <button type="button" class="cat" :aria-pressed="!draft.noChannel" @click="draft.noChannel = false">{{ t('souk.scout.hasChannel') }}</button>
          <button type="button" class="cat" :aria-pressed="draft.noChannel" @click="draft.noChannel = true">{{ t('souk.scout.noChannel') }}</button>
        </div>

        <p v-if="draft.noChannel" class="text-[14px] text-stone-600 text-center py-6 leading-relaxed">{{ t('souk.scout.noChannelNote') }}</p>
        <template v-else>
          <Field id="sc-tg" :label="t('souk.scout.f.telegram')" :from="fromCard('telegram')">
            <input id="sc-tg" v-model="draft.telegram" dir="ltr" autocomplete="off" inputmode="url" class="inp" placeholder="t.me/channel" />
          </Field>
          <div class="grid grid-cols-2 gap-2">
            <button type="button" class="btn btn-line" @click="qrOpen = true"><Icon name="scan-line" :size="16" />{{ t('souk.scout.scanQr') }}</button>
            <button type="button" class="btn btn-line" @click="paste"><Icon name="copy" :size="16" />{{ t('souk.scout.paste') }}</button>
          </div>

          <div v-if="tgBusy" class="rounded-2xl ring-1 ring-stone-200 bg-white px-4 py-5 text-[13px] text-stone-600 flex items-center gap-2">
            <Icon name="hourglass" :size="16" class="animate-pulse" />{{ t('souk.scout.tgChecking') }}
          </div>
          <div v-else-if="tg && tg.preview" class="rounded-2xl ring-1 ring-stone-200 bg-white p-3 flex flex-col gap-2.5">
            <div class="flex items-center gap-3">
              <span class="sk-ico sk-ico-lg st-photos"><Icon name="send" :size="20" /></span>
              <div class="min-w-0 flex-1">
                <p class="text-[15px] font-bold text-stone-900 truncate" dir="auto">{{ tg.preview.title }}</p>
                <p class="text-[12px] text-stone-600">
                  {{ tt('souk.scout.subs', { n: fmtSubs(tg.preview.subscribers) }) }}<template v-if="tg.preview.last"> · {{ tt('souk.scout.lastPost', { d: '' }).trim() }} <span dir="ltr">{{ local(tg.preview.last).slice(5, 16) }}</span></template>
                </p>
              </div>
            </div>
            <div v-if="tg.preview.photos.length" class="grid grid-cols-4 gap-1">
              <img v-for="(u, i) in tg.preview.photos" :key="i" :src="u" alt="" referrerpolicy="no-referrer" class="aspect-square w-full object-cover rounded-lg bg-stone-100" />
            </div>
            <p class="text-[12px] font-semibold text-emerald-700 flex items-center gap-1"><Icon name="check" :size="14" />{{ t('souk.scout.tgPublic') }}</p>
            <p v-if="tg.known" class="text-[12px] text-amber-800">{{ tt('souk.scout.tgKnown', { n: tg.known.label }) }}</p>
          </div>
          <p v-else-if="tg && tg.state === 'public' && tg.unreachable" class="note-amber">{{ t('souk.scout.tgUnreachable') }}</p>
          <p v-else-if="tg && tg.state === 'public' && !outbox.online" class="note-amber">{{ t('souk.scout.tgOffline') }}</p>
          <p v-else-if="tg && (tg.state === 'private' || tg.state === 'nopreview')" class="note-amber">
            <Icon name="unlock" :size="15" class="shrink-0 mt-0.5" />{{ t('souk.scout.tgPrivate') }}
          </p>
          <p v-else-if="tg && tg.state === 'none' && draft.telegram.trim()" class="note-rose">{{ t('souk.scout.tgBad') }}</p>
        </template>

        <button type="button" class="btn btn-st btn-big w-full mt-2" @click="step = 4">{{ t('souk.scout.next.details') }}</button>
      </template>

      <!-- 4. details -->
      <template v-if="step === 4">
        <div>
          <p class="lbl">{{ t('souk.scout.f.market') }}</p>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="m in markets" :key="m" type="button" class="cat" :aria-pressed="draft.market === m" @click="setMarket(m)">{{ m }}</button>
            <button type="button" class="cat" :aria-pressed="otherMarket" @click="otherMarket = true">{{ t('souk.scout.otherMarket') }}</button>
          </div>
          <input v-if="otherMarket" v-model="draft.market" class="inp mt-2" :placeholder="t('souk.scout.otherMarketPh')" @change="rememberMarket" />
        </div>
        <template v-if="!pickingMarket">
          <Field id="sc-place" :label="t('souk.scout.f.place')">
            <input id="sc-place" v-model="draft.place" autocomplete="off" class="inp" :placeholder="t('souk.scout.f.placePh')" />
          </Field>
          <div>
            <p class="lbl">{{ t('souk.scout.f.sells') }}</p>
            <div class="flex flex-wrap gap-1.5">
              <button v-for="c in data?.categories || []" :key="c.key" type="button" class="cat"
                      :aria-pressed="draft.sells.includes(c.key)" @click="toggleSell(c.key)">{{ catName(c) }}</button>
            </div>
          </div>
          <Field id="sc-note" :label="t('souk.scout.f.note')">
            <textarea id="sc-note" v-model="draft.note" rows="2" class="inp h-auto py-2" :placeholder="t('souk.scout.f.notePh')" />
          </Field>
          <button type="button" class="btn btn-st btn-big w-full mt-1" :disabled="saving" @click="save">
            <Icon name="check" :size="18" :stroke-width="2.4" />{{ saving ? t('souk.scout.saving') : t('souk.scout.save') }}
          </button>
        </template>
        <button v-else type="button" class="btn btn-st btn-big w-full" :disabled="!draft.market.trim()" @click="marketPicked">
          {{ t('souk.scout.done') }}
        </button>
      </template>
    </template>

    <!-- ── the same shop? ──────────────────────────────────────────────────── -->
    <template v-else-if="step === 5">
      <div class="text-center pt-6 flex flex-col items-center gap-2">
        <span class="sk-ico sk-ico-lg st-bought"><Icon name="alert-triangle" :size="22" /></span>
        <h1 class="text-[18px] font-extrabold text-stone-900">{{ t('souk.scout.dupTitle') }}</h1>
        <p class="text-[13px] text-stone-600">{{ t('souk.scout.dupSub') }}</p>
      </div>
      <div class="flex flex-col gap-2">
        <button v-for="m in dups" :key="m.name" type="button" class="dup" :disabled="saving" @click="submit(m.name)">
          <img v-if="m.photo" :src="m.photo" alt="" class="w-14 h-14 rounded-xl object-cover shrink-0" />
          <span v-else class="w-14 h-14 rounded-xl st-tint st-ink inline-flex items-center justify-center shrink-0"><Icon name="store" :size="20" /></span>
          <span class="min-w-0 flex-1 text-start">
            <span class="block text-[15px] font-bold text-stone-900 truncate" dir="ltr">{{ m.label }}</span>
            <span class="block text-[12px] text-stone-600">{{ m.place || '—' }} · {{ tt('souk.scout.dupBy', { n: m.by, d: m.at }) }}</span>
            <span class="flex flex-wrap gap-1 mt-1">
              <span v-for="w in m.why" :key="w" class="tag tag-amber">{{ w === 'near' && m.metres != null ? tt('souk.scout.why.nearN', { n: m.metres }) : t('souk.scout.why.' + w) }}</span>
            </span>
          </span>
          <span class="text-[12px] font-bold st-ink shrink-0">{{ t('souk.scout.isSame') }}</span>
        </button>
      </div>
      <button type="button" class="btn btn-line btn-big w-full" :disabled="saving" @click="submit('new')">{{ t('souk.scout.isOther') }}</button>
      <button type="button" class="text-[13px] text-stone-500 underline self-center" @click="step = 4">{{ t('souk.scout.back') }}</button>
    </template>

    <!-- ── saved ───────────────────────────────────────────────────────────── -->
    <template v-else-if="step === 6">
      <div class="text-center pt-10 flex flex-col items-center gap-2">
        <span class="w-16 h-16 rounded-full inline-flex items-center justify-center" :class="done?.queued ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-700'">
          <Icon :name="done?.queued ? 'upload-cloud' : 'check'" :size="30" :stroke-width="2.4" />
        </span>
        <h1 class="text-[19px] font-extrabold text-stone-900">{{ done?.queued ? t('souk.scout.queuedTitle') : t('souk.scout.savedTitle') }}</h1>
        <p class="text-[14px] text-stone-700" dir="ltr">{{ done?.label }}</p>
        <p class="text-[13px] text-stone-600 leading-relaxed max-w-[360px]">{{ doneNote }}</p>
        <p class="mt-3 rounded-xl st-tint st-ink px-4 py-2 text-[14px] font-semibold">{{ tt('souk.scout.nthToday', { n: todayCount }) }}</p>
      </div>
      <button type="button" class="btn btn-st btn-big w-full" @click="startShop">{{ t('souk.scout.nextShop') }}</button>
      <button type="button" class="btn btn-line w-full" @click="step = 0">{{ t('souk.scout.endRound') }}</button>
    </template>

    <BarcodeScan v-model:open="qrOpen" qr @code="onQr" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, defineComponent, h } from "vue";
import Icon from "@/components/ui/Icon.vue";
import BarcodeScan from "@/souk/BarcodeScan.vue";
import { api } from "@/lib/resource";
import { postPhoto, shrink } from "@/lib/soukPhoto";
import { outbox, enqueue, onDone, newKey, isTransient } from "@/lib/soukOutbox";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t, locale } = useI18n();
const toast = useToast();
const tt = (k, o) => Object.entries(o || {}).reduce((s, [a, b]) => s.split(`{${a}}`).join(String(b ?? "")), t(k));

// A labelled field with the "from the card" mark.
const Field = defineComponent({
  props: { id: String, label: String, from: Boolean },
  setup(p, { slots }) {
    return () => h("div", { class: "flex flex-col gap-1" }, [
      h("div", { class: "flex items-center justify-between gap-2" }, [
        // Tailwind here, not the scoped classes: a render function in the same
        // file does not get the component's scope attribute.
        h("label", { for: p.id, class: "text-[12px] font-semibold text-stone-600" }, p.label),
        p.from ? h("span", { class: "inline-flex rounded-full px-2 py-0.5 text-[11px] font-bold bg-sky-50 text-sky-800" },
                   t("souk.scout.fromCard")) : null,
      ]),
      slots.default && slots.default(),
    ]);
  },
});

const data = ref(null);
const loading = ref(false);
const who = ref("me");
const step = ref(0);
const saving = ref(false);
const pickingMarket = ref(false);
const otherMarket = ref(false);

// ── the shop being entered (kept on the phone: Android kills the app) ─────────
const DRAFT_KEY = "lp_scout_draft";
const MARKET_KEY = "lp_scout_market";
const blank = () => ({ name: "", phone: "", phone2: "", instagram: "", telegram: "", noChannel: false,
                       place: "", sells: [], note: "", market: readMarket() });
function readMarket() { try { return localStorage.getItem(MARKET_KEY) || ""; } catch (_) { return ""; } }
const draft = reactive(blank());
const card = ref(null);          // what the reader said
const cardWhy = ref("");         // "" | off | failed | offline
const cardUrl = ref("");         // shown: server URL or a local data URL
const cardServer = ref("");      // the uploaded card's URL (read at the shop)
const shopUrl = ref("");
let shopBlob = null;
let cardBlob = null;
const manual = ref(false);
const reading = ref(false);
const fix = ref(null);           // {lat, lng, acc}
const fixState = ref("wait");    // wait | ok | bad
const hasDraft = ref(false);

function saveDraft() {
  if (step.value < 1 || step.value > 4 || pickingMarket.value) return;
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({
      d: { ...draft }, card: card.value, cardWhy: cardWhy.value, cardServer: cardServer.value,
      shop: shopUrl.value.startsWith("data:") ? shopUrl.value : "", cardImg: cardUrl.value.startsWith("data:") ? cardUrl.value : "",
      fix: fix.value, manual: manual.value, step: step.value, at: Date.now(),
    }));
  } catch (_) {
    // A full quota: keep the fields at least.
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify({ d: { ...draft }, step: step.value, at: Date.now() })); } catch (__) { /* private */ }
  }
}
function loadDraft() {
  try {
    const raw = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null");
    if (!raw || Date.now() - (raw.at || 0) > 12 * 3600 * 1000) return null;
    return raw;
  } catch (_) { return null; }
}
function clearDraft() {
  try { localStorage.removeItem(DRAFT_KEY); } catch (_) { /* private */ }
  hasDraft.value = false;
}
function dataUrlBlob(u) {
  const [head, b64] = u.split(",");
  const bin = atob(b64);
  const a = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i);
  return new File([a], "photo.jpg", { type: (head.match(/data:([^;]+)/) || [])[1] || "image/jpeg" });
}
const toDataUrl = (blob) => new Promise((ok) => {
  const r = new FileReader();
  r.onload = () => ok(String(r.result || ""));
  r.onerror = () => ok("");
  r.readAsDataURL(blob);
});

function reset() {
  Object.assign(draft, blank());
  card.value = null; cardWhy.value = ""; cardUrl.value = ""; cardServer.value = "";
  shopUrl.value = ""; shopBlob = null; cardBlob = null; manual.value = false;
  fix.value = null; fixState.value = "wait"; tg.value = null; tgKey = "";
}

function startShop() {
  const d = loadDraft();
  reset();
  if (d) {
    Object.assign(draft, d.d || {});
    card.value = d.card || null; cardWhy.value = d.cardWhy || ""; cardServer.value = d.cardServer || "";
    manual.value = !!d.manual; fix.value = d.fix || null; fixState.value = d.fix ? "ok" : "wait";
    if (d.shop) { shopUrl.value = d.shop; shopBlob = dataUrlBlob(d.shop); }
    if (d.cardImg) { cardUrl.value = d.cardImg; cardBlob = dataUrlBlob(d.cardImg); } else if (d.cardServer) cardUrl.value = d.cardServer;
    step.value = Math.max(1, Math.min(4, d.step || 1));
  } else {
    if (!draft.market) { pickMarket(1); return; }
    step.value = 1;
  }
}
function dropDraft() { clearDraft(); reset(); }
// The market is chosen once for the round (and changed from the home chip).
let afterMarket = 0;
function pickMarket(next) { afterMarket = next; pickingMarket.value = true; step.value = 4; }
function marketPicked() { rememberMarket(); pickingMarket.value = false; step.value = afterMarket; }
function back() {
  if (pickingMarket.value) { pickingMarket.value = false; step.value = 0; return; }
  step.value = step.value <= 1 ? 0 : step.value - 1;
}

watch(draft, saveDraft, { deep: true });
watch(step, (s) => { saveDraft(); if (s === 1) startGps(); else if (fix.value || s === 0) stopGps(); window.scrollTo(0, 0); });

// ── GPS: watched while the storefront is being shot; the best fix is kept ────
let watchId = null;
let shotAt = 0;
function startGps() {
  if (watchId != null || !navigator.geolocation) { if (!navigator.geolocation) fixState.value = "bad"; return; }
  watchId = navigator.geolocation.watchPosition((pos) => {
    const f = { lat: pos.coords.latitude, lng: pos.coords.longitude, acc: pos.coords.accuracy || 0 };
    // Before the photo: keep the most precise reading. After it the fix
    // belongs to the shot — only a first one is still taken.
    if (shotAt ? !fix.value : (!fix.value || f.acc <= fix.value.acc)) fix.value = f;
    fixState.value = "ok";
  }, () => { if (!fix.value) fixState.value = "bad"; }, { enableHighAccuracy: true, maximumAge: 15000, timeout: 20000 });
}
function stopGps() {
  if (watchId != null && navigator.geolocation) navigator.geolocation.clearWatch(watchId);
  watchId = null;
}

async function onShop(e) {
  const f = e.target.files && e.target.files[0];
  e.target.value = "";
  if (!f) return;
  shotAt = Date.now();
  const small = await shrink(f, 1280, 0.78);
  shopBlob = small;
  shopUrl.value = await toDataUrl(small);
  saveDraft();
}

// ── the card ───────────────────────────────────────────────────────────────────
async function onCard(e) {
  const f = e.target.files && e.target.files[0];
  e.target.value = "";
  if (!f) return;
  const small = await shrink(f, 1600, 0.85);
  cardBlob = small;
  cardUrl.value = await toDataUrl(small);
  cardServer.value = "";
  card.value = null;
  if (!outbox.online) { cardWhy.value = "offline"; manual.value = true; return; }
  reading.value = true;
  try {
    const r = await postPhoto("souk_scout.read_card", {}, small, { max: 1600, quality: 0.85 });
    cardServer.value = r.url || "";
    cardWhy.value = r.why || "";
    if (r.card) applyCard(r.card);
    cardBlob = null;                       // on the server already
  } catch (err) {
    cardWhy.value = isTransient(err) ? "offline" : "failed";
  } finally {
    reading.value = false;
    manual.value = true;
  }
}
function applyCard(c) {
  card.value = c;
  if (c.isCard === false) { cardWhy.value = "notCard"; return; }
  const ph = c.phones || [];
  if (!draft.name && c.name) draft.name = c.name;
  if (!draft.phone && ph[0]) draft.phone = ph[0];
  if (!draft.phone2 && ph[1]) draft.phone2 = ph[1];
  if (!draft.telegram && c.telegram) draft.telegram = c.telegram;
  if (!draft.instagram && c.instagram) draft.instagram = c.instagram;
  if (!draft.place && c.place) draft.place = c.place;
}
function fromCard(k) {
  const c = card.value;
  if (!c) return false;
  const v = { name: c.name, phone: (c.phones || [])[0], phone2: (c.phones || [])[1], telegram: c.telegram, instagram: c.instagram }[k];
  return !!v && String(v).replace(/\s/g, "") === String(draft[k] || "").replace(/\s/g, "");
}
const cardNote = computed(() => {
  if (cardWhy.value === "offline") return t("souk.scout.card.offline");
  if (cardWhy.value === "off") return t("souk.scout.card.off");
  if (cardWhy.value === "failed") return t("souk.scout.card.failed");
  if (cardWhy.value === "notCard") return t("souk.scout.card.notCard");
  return card.value ? t("souk.scout.card.read") : t("souk.scout.card.manual");
});
const cardNoteClass = computed(() => (card.value && !cardWhy.value ? "text-sky-800" : "text-amber-800"));

const cleanName = (s) => String(s || "").replace(/[^A-Za-z0-9 &'.-]/g, "").replace(/\s+/g, " ").trim().toUpperCase();
const arabicName = computed(() => /[؀-ۿ]/.test(draft.name || ""));

function toTelegram() {
  draft.name = cleanName(draft.name);
  if (draft.name.length < 3) { toast.warn(t("souk.scout.f.nameNeeded"), ""); return; }
  step.value = 3;
}

// ── Telegram ───────────────────────────────────────────────────────────────────
const tg = ref(null);
const tgBusy = ref(false);
const qrOpen = ref(false);
let tgKey = "";
let tgTimer = null;
async function checkTg() {
  const link = draft.telegram.trim();
  if (!link || draft.noChannel) { tg.value = null; return; }
  if (link === tgKey && tg.value) return;
  tgKey = link;
  if (!outbox.online) { tg.value = { state: /t\.me\/\+|joinchat/i.test(link) ? "private" : "public" }; return; }
  tgBusy.value = true;
  try {
    const r = await api("souk_scout.check_telegram", { link });
    if (tgKey === link) tg.value = r;
  } catch (_) {
    if (tgKey === link) tg.value = { state: "public", unreachable: true };
  } finally {
    tgBusy.value = false;
  }
}
watch(() => draft.telegram, () => { clearTimeout(tgTimer); tgTimer = setTimeout(checkTg, 600); });
watch(step, (s) => { if (s === 3) checkTg(); });
function onQr(code) { draft.telegram = String(code || "").trim(); draft.noChannel = false; }
async function paste() {
  try {
    const s = await navigator.clipboard.readText();
    if (s) draft.telegram = s.trim();
  } catch (_) {
    toast.info(t("souk.scout.pasteNo"), "");
  }
}
const fmtSubs = (n) => (n >= 1000 ? (Math.round(n / 100) / 10).toLocaleString(locale.value) + (locale.value === "ar" ? " ألف" : "k") : String(n || 0));

// ── details ────────────────────────────────────────────────────────────────────
const markets = computed(() => {
  const list = [...(data.value?.markets || [])];
  if (draft.market && !list.includes(draft.market) && !otherMarket.value) list.unshift(draft.market);
  return list;
});
function setMarket(m) { draft.market = m; otherMarket.value = false; rememberMarket(); }
function rememberMarket() { try { localStorage.setItem(MARKET_KEY, draft.market.trim()); } catch (_) { /* private */ } }
function toggleSell(k) {
  const i = draft.sells.indexOf(k);
  if (i < 0) draft.sells.push(k); else draft.sells.splice(i, 1);
}
const catName = (c) => (locale.value === "ar" ? c.ar : locale.value === "fr" ? c.fr : c.fr || c.key);

// ── save ───────────────────────────────────────────────────────────────────────
const dups = ref([]);
const done = ref(null);
// Plain data: the job goes into IndexedDB, which cannot store Vue's proxies.
function payload(target) {
  return JSON.parse(JSON.stringify({
    clientKey: draftKey(), target, name: cleanName(draft.name), phone: draft.phone, phone2: draft.phone2,
    telegram: draft.noChannel ? "" : draft.telegram.trim(), instagram: draft.instagram, market: draft.market.trim(),
    place: draft.place, sells: draft.sells, note: draft.note,
    lat: fix.value?.lat ?? null, lng: fix.value?.lng ?? null, accuracy: fix.value ? Math.round(fix.value.acc) : 0,
    cardUrl: cardServer.value, card: card.value,
  }));
}
// One key per shop being entered: a retry never makes the shop twice.
let key = "";
function draftKey() {
  if (!key) key = newKey();
  return key;
}
async function save() {
  draft.name = cleanName(draft.name);
  if (draft.name.length < 3) { step.value = 2; toast.warn(t("souk.scout.f.nameNeeded"), ""); return; }
  if (!draft.market.trim()) { toast.warn(t("souk.scout.f.marketNeeded"), ""); return; }
  saving.value = true;
  try {
    if (outbox.online) {
      try {
        const r = await api("souk_scout.similar", {
          name: draft.name, phone: draft.phone, phone2: draft.phone2,
          telegram: draft.noChannel ? "" : draft.telegram, lat: fix.value?.lat ?? "", lng: fix.value?.lng ?? "" });
        if ((r.rows || []).length) {
          dups.value = r.rows;
          step.value = 5;
          return;
        }
      } catch (_) { /* no answer: the server joins on a phone / channel match */ }
    }
    await submit("");
  } finally {
    saving.value = false;
  }
}
async function submit(target) {
  saving.value = true;
  try {
    const job = { kind: "scout", label: cleanName(draft.name), payload: payload(target),
                  shop: shopBlob || null, card: cardServer.value ? null : (cardBlob || null) };
    const r = await enqueue(job);
    done.value = r && r.queued ? { queued: true, label: job.label, tg: job.payload.telegram ? "public" : "none" } : r;
    clearDraft();
    key = "";
    step.value = 6;
    load();
  } catch (e) {
    toast.warn(t("souk.scout.saveFailed"), String((e && e.message) || e));
    step.value = 4;
  } finally {
    saving.value = false;
  }
}
const todayCount = computed(() => (data.value?.stats.shops || 0) + waitingJobs.value.length);
const doneNote = computed(() => {
  const d = done.value || {};
  if (d.queued) return t("souk.scout.queuedNote");
  const parts = [];
  if (d.outcome === "same" || d.outcome === "auto") parts.push(t("souk.scout.doneJoined"));
  if (d.tg === "public") parts.push(t("souk.scout.doneChannel"));
  else if (d.tg === "private") parts.push(t("souk.scout.donePrivate"));
  if (d.dup) parts.push(tt("souk.scout.looksLike", { n: d.dup }));
  return parts.join(" ") || t("souk.scout.doneLead");
});

// ── the list ───────────────────────────────────────────────────────────────────
const waitingJobs = computed(() => outbox.jobs.filter((j) => j.kind === "scout"));
const tgClass = (s) => (s === "public" ? "tag-sky" : s === "private" ? "tag-amber" : "tag-stone");
function setWho(w) { who.value = w; load(); }
async function load() {
  loading.value = true;
  try {
    data.value = await api("souk_scout.scout_boot", { who: who.value });
  } catch (e) {
    toast.warn(t("souk.scout.loadFailed"), String((e && e.message) || e));
  } finally {
    loading.value = false;
  }
}

let offDone = null;
onMounted(() => {
  hasDraft.value = !!loadDraft();
  load();
  offDone = onDone((j) => { if (j.kind === "scout") load(); });
});
onBeforeUnmount(() => { stopGps(); offDone && offDone(); clearTimeout(tgTimer); });
watch(step, (s) => { if (s === 0) hasDraft.value = !!loadDraft(); });
</script>

<style scoped>
.btn { flex-shrink: 0; height: 2.75rem; padding-block: 0; padding-inline: 0.875rem; border-radius: 0.75rem; font-size: 14px; font-weight: 600;
  gap: 0.375rem; white-space: nowrap; }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.btn-big { height: 3.25rem; font-size: 15px; border-radius: 14px; }
.btn-st { background: rgb(var(--st)); color: #fff; font-weight: 700; box-shadow: 0 6px 16px -8px rgb(var(--st)); }
.btn-st:not(:disabled):hover { background: rgb(var(--st-ink)); }
.btn-st:disabled { background: rgb(231 229 228); color: rgb(87 83 78); box-shadow: none; opacity: 1; }
.btn-line { background: rgb(255 255 255 / .85); color: rgb(28 25 23); box-shadow: inset 0 0 0 1px rgb(214 211 209); }
:global(html[data-theme="dark"] .st-buying .btn-st) { color: rgb(28 25 23); }
:global(html[data-theme="dark"] .st-buying .btn-line) { background: #292524; color: #f5f5f4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }

.cat { flex-shrink: 0; min-height: 36px; padding: 0 12px; border-radius: 9999px; font-size: 13px; font-weight: 600;
  background: #fff; color: rgb(68 64 60); box-shadow: inset 0 0 0 1px rgb(214 211 209); white-space: nowrap; }
.cat[aria-pressed="true"] { background: rgb(var(--st) / .10); color: rgb(var(--st-ink)); box-shadow: inset 0 0 0 2px rgb(var(--st)); }
:global(html[data-theme="dark"] .st-buying .cat:not([aria-pressed="true"])) { background: #292524; color: #e7e5e4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }
.seg { min-height: 30px; padding: 0 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; color: rgb(87 83 78); }
.seg[aria-pressed="true"] { background: rgb(var(--st)); color: #fff; }

.stat { display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; border-radius: 12px; background: rgb(var(--st) / .05);
  box-shadow: inset 0 0 0 1px rgb(var(--st) / .14); }
.stat span { font-size: 12px; color: rgb(87 83 78); }
.stat b { font-size: 20px; font-weight: 800; color: rgb(28 25 23); font-variant-numeric: tabular-nums; }
.stat-amber { background: rgb(217 119 6 / .08); box-shadow: inset 0 0 0 1px rgb(217 119 6 / .25); }
:global(html[data-theme="dark"] .st-buying .stat b) { color: #f5f5f4; }
:global(html[data-theme="dark"] .st-buying .stat span) { color: rgb(168 162 158); }

.row { display: flex; align-items: center; gap: 12px; padding: 10px 16px; }
.thumb { width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center;
  background: rgb(245 245 244); color: rgb(120 113 108); }
.nm { font-size: 14px; font-weight: 700; color: rgb(28 25 23); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: start; }
.sub { font-size: 12px; color: rgb(87 83 78); line-height: 1.5; }
.tag { display: inline-flex; align-items: center; gap: 3px; flex-shrink: 0; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 700; }
.tag-sky { background: rgb(2 132 199 / .1); color: rgb(7 89 133); }
.tag-amber { background: rgb(217 119 6 / .12); color: rgb(146 64 14); }
.tag-rose { background: rgb(225 29 72 / .1); color: rgb(159 18 57); }
.tag-stone { background: rgb(120 113 108 / .1); color: rgb(87 83 78); }
:global(html[data-theme="dark"] .st-buying .nm) { color: #f5f5f4; }
:global(html[data-theme="dark"] .st-buying .thumb) { background: #292524; }

.shot { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; min-height: 300px; border-radius: 18px;
  background: rgb(28 25 23); color: #fff; text-align: center; padding: 16px; cursor: pointer; }
.shot-dash { min-height: 190px; background: transparent; color: rgb(87 83 78); box-shadow: inset 0 0 0 2px rgb(var(--st) / .35); border-radius: 18px; }
.gps { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 14px; box-shadow: inset 0 0 0 1px rgb(214 211 209); background: #fff; }
.gps.ok .sk-ico { background: rgb(5 150 105 / .12); color: rgb(6 95 70); }
.gps.bad .sk-ico { background: rgb(217 119 6 / .14); color: rgb(146 64 14); }
:global(html[data-theme="dark"] .st-buying .gps) { background: #1c1917; box-shadow: inset 0 0 0 1px rgb(68 64 60); }

.lbl { font-size: 12px; font-weight: 600; color: rgb(87 83 78); margin-bottom: 4px; }
.inp { width: 100%; height: 2.875rem; border-radius: 12px; padding: 0 12px; font-size: 15px; background: #fff;
  box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.inp:focus { outline: none; box-shadow: inset 0 0 0 2px rgb(var(--st)); }
:global(html[data-theme="dark"] .st-buying .inp) { background: #1c1917; color: #f5f5f4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }
.note-amber, .note-rose { display: flex; gap: 8px; font-size: 13px; line-height: 1.6; border-radius: 12px; padding: 10px 12px; }
.note-amber { background: rgb(217 119 6 / .1); color: rgb(146 64 14); }
.note-rose { background: rgb(225 29 72 / .08); color: rgb(159 18 57); }
.dup { display: flex; align-items: center; gap: 12px; padding: 12px; border-radius: 16px; background: #fff; box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.dup:not(:disabled):active { box-shadow: inset 0 0 0 2px rgb(var(--st)); }
:global(html[data-theme="dark"] .st-buying .dup) { background: #1c1917; box-shadow: inset 0 0 0 1px rgb(87 83 78); }
</style>
