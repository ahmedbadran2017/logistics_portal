<template>
  <!-- Marketing's queue: the final photos. The in-house photos and the specs
       come from the floor and the buy; marketing uploads the finals per
       colour, puts them in order (drag, or the arrows on a phone — the first
       is the main photo) and the whole order is saved with ONE final_set.
       Handing to content puts them on the Shopify Draft; each colour's first
       final becomes its variants' image. The sample pieces are in
       Studio - JM. Backend: souk.studio_boot / final_add / final_set /
       photo_remove / studio_return / studio_send / raw_zip. -->
  <div class="px-4 sm:px-5 pt-6 pb-10 max-w-[1320px] mx-auto space-y-4">
    <header class="space-y-0.5">
      <h1 class="text-[20px] font-bold text-stone-900">{{ t('souk.studioTitle') }}</h1>
      <p class="text-[12.5px] text-stone-500 max-w-[680px]">{{ t('souk.studioIntro') }}</p>
    </header>

    <div v-if="loading && !data" class="lp-card h-[420px] animate-pulse" />

    <!-- nothing in the queue: the same card on the three screens -->
    <div v-else-if="data && !data.queue.length && !d" class="lp-card px-6 py-12 flex flex-col items-center text-center gap-3">
      <span class="w-12 h-12 rounded-full bg-stone-100 text-stone-500 inline-flex items-center justify-center"><Icon name="inbox" :size="22" /></span>
      <p class="text-[13.5px] font-semibold text-stone-700">{{ t('souk.studioNone') }}</p>
      <router-link :to="{ name: 'SoukBoard' }" class="lp-tap h-10 px-4 rounded-lg bg-white ring-1 ring-inset ring-stone-300 text-[12.5px] font-semibold inline-flex items-center gap-1.5 hover:bg-stone-50">
        {{ t('souk.pub.toBoard') }}<Icon name="arrow-right" :size="14" class="rtl:rotate-180" />
      </router-link>
    </div>

    <!-- Desktop: the queue beside the product. A phone: the queue is its own
         view (/souk/studio), the product another (/souk/studio/:name). -->
    <div v-else-if="data" class="grid grid-cols-1 lg:grid-cols-[300px_minmax(0,1fr)] gap-4 items-start">
      <aside :aria-label="t('souk.pub.queueLbl')" class="lp-card overflow-hidden" :class="listOnly ? '' : 'hidden lg:block'">
        <div class="px-3.5 py-3 flex justify-between gap-2 text-[12px] font-semibold text-stone-600 border-b border-stone-100">
          <span>{{ t('souk.nProducts').replace('{n}', data.queue.length) }}</span>
          <span>{{ t('souk.oldestFirst') }}</span>
        </div>
        <div v-if="!data.queue.length" class="p-6 text-center text-[12.5px] text-stone-500">{{ t('souk.studioNone') }}</div>
        <router-link v-for="q in data.queue" :key="q.name" :to="{ name: 'SoukStudio', params: { name: q.name } }"
                     class="flex items-center gap-2.5 px-3.5 py-2.5 border-b border-stone-100 last:border-0 min-h-[60px]"
                     :class="d && d.name === q.name ? 'bg-[var(--accent-50)]' : 'hover:bg-stone-50'">
          <img v-if="q.image" :src="q.image" class="w-10 h-10 shrink-0 rounded-lg object-cover bg-stone-100" alt="" />
          <div v-else class="w-10 h-10 shrink-0 rounded-lg bg-stone-100" />
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-semibold truncate ltr:text-left rtl:text-right" dir="auto">{{ q.title }}</div>
            <div class="text-[11px] text-stone-600 truncate">{{ t('souk.nColors').replace('{n}', q.colors) }} · {{ t('souk.nRaw').replace('{n}', q.raw) }}</div>
          </div>
          <span class="text-[10.5px] font-bold rounded-md px-[7px] py-0.5 whitespace-nowrap tabular-nums"
                :class="q.late ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-700'">{{ ageText(q.age) }}</span>
        </router-link>
      </aside>

      <!-- product -->
      <div class="min-w-0" :class="listOnly ? 'hidden lg:block' : ''">
        <router-link v-if="!listOnly" :to="{ name: 'SoukStudio' }"
                     class="lg:hidden lp-tap h-11 -ms-1 mb-1 px-1 inline-flex items-center gap-1 text-[13px] font-semibold text-stone-700">
          <Icon name="chevron-left" :size="18" class="rtl:rotate-180" />{{ t('souk.pub.backToQueue') }} · {{ data.queue.length }}
        </router-link>
        <div v-if="!d" class="lp-card p-8 text-center text-[13px] text-stone-500">{{ t('souk.studioPick') }}</div>
        <div v-else class="space-y-3.5">
          <section class="lp-card p-4 flex items-start justify-between gap-3 flex-wrap">
            <div class="min-w-0 flex flex-col gap-0.5">
              <h2 class="text-[17px] font-bold break-words">{{ d.title }}</h2>
              <div class="flex flex-wrap items-center gap-x-1.5 text-[11.5px] text-stone-600">
                <span class="mono" dir="ltr">{{ d.name }} · {{ d.brand }}</span>
                <span aria-hidden="true">·</span>
                <span>{{ t('souk.pub.colorsSizes').replace('{c}', realColorCount).replace('{s}', sizes.length || 1) }}</span>
              </div>
            </div>
            <div class="flex gap-2 items-center flex-wrap">
              <span v-if="clock" class="text-[11.5px] font-bold rounded-md px-2 py-[3px] tabular-nums"
                    :class="clock.late ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-700'">{{ clock.text }}</span>
              <span v-if="d.samples.length" class="text-[11.5px] text-stone-700 bg-stone-100 rounded-md px-2 py-[3px]">
                {{ t('souk.pub.sampleIn') }}<template v-for="s in d.samples" :key="s.sku"> · <span class="mono" dir="ltr">{{ s.sku }}×{{ s.qty }}</span></template>
              </span>
              <router-link :to="{ name: 'SoukProduct', params: { name: d.name } }" class="lp-tap h-8 px-1 inline-flex items-center text-[11.5px] font-semibold underline text-[var(--accent-700)]">{{ t('souk.toProduct') }}</router-link>
            </div>
          </section>

          <div v-if="d.error" class="bg-rose-50 rounded-lg px-3 py-2.5 text-[12px] text-rose-700 break-words">{{ d.error }}</div>
          <div v-if="!d.canEdit" class="bg-stone-100 rounded-lg px-3 py-2.5 text-[12.5px] text-stone-700">{{ t('souk.studioNotNow') }}</div>

          <!-- raw -->
          <section class="lp-card p-4 space-y-3">
            <div class="flex items-center justify-between gap-2">
              <h3 class="text-[13.5px] font-bold">{{ t('souk.rawPhotos') }} · {{ d.photos.length }}</h3>
              <a v-if="d.photos.length" :href="zipUrl" class="lp-tap h-[30px] px-2.5 rounded-lg bg-stone-100 ring-1 ring-inset ring-stone-200 text-[12px] font-semibold text-stone-700 inline-flex items-center gap-1.5 hover:bg-stone-200/60">
                <Icon name="download" :size="14" />{{ t('souk.downloadAll') }}
              </a>
            </div>
            <div v-for="c in d.colors" :key="c.code" class="flex gap-2.5 items-center">
              <span class="w-16 shrink-0 text-[12px] font-semibold text-stone-700 break-words">{{ colorName(c) }} · {{ rawOf(c.code).length }}</span>
              <div class="flex-1 min-w-0 grid grid-cols-4 sm:grid-cols-6 gap-1.5">
                <a v-for="p in rawOf(c.code)" :key="p.url" :href="p.url" target="_blank" rel="noopener"
                   class="block aspect-square rounded-md overflow-hidden bg-stone-100" :title="t('souk.slot_' + p.slot)">
                  <img :src="p.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                </a>
              </div>
            </div>
            <div v-if="sizes.length || d.specs || weights" class="flex flex-wrap gap-x-[18px] gap-y-1.5 text-[12px] text-stone-700 bg-stone-50 rounded-lg px-2.5 py-2">
              <span v-if="sizes.length">{{ t('souk.sizesLbl') }} {{ sizes.join(' · ') }}</span>
              <span v-if="d.specs">{{ t('souk.specs') }}: <bdi>{{ d.specs }}</bdi></span>
              <span v-if="weights">{{ t('souk.weightLbl') }} <span dir="ltr">{{ weights }}</span></span>
            </div>
          </section>

          <!-- finals (a file dropped anywhere here, off a colour zone, goes in
               untied rather than making the browser open it) -->
          <section class="lp-card p-4 space-y-3" @dragover="onSectionOver" @drop="onSectionDrop">
            <div class="flex items-baseline justify-between gap-2 flex-wrap">
              <h3 class="text-[13.5px] font-bold">{{ t('souk.finals') }}<template v-if="order.length"> · {{ order.length }}</template></h3>
              <span class="text-[11.5px] text-stone-600">
                <template v-if="orderSaving">{{ t('souk.pub.orderSaving') }}</template>
                <template v-else-if="d.canEdit">
                  <span class="souk-fine">{{ t('souk.pub.dragHint') }}</span><span class="souk-coarse">{{ t('souk.pub.dragHintTouch') }}</span>
                </template>
                <template v-else>{{ t('souk.finalsHint') }}</template>
              </span>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-2.5">
              <div v-for="(f, i) in order" :key="f.url"
                   class="flex flex-col gap-1.5 min-w-0 transition-opacity"
                   :class="[dragFrom === i ? 'opacity-40' : '', d.canEdit ? 'souk-grab' : '']"
                   :draggable="d.canEdit && !busy"
                   @dragstart="onDragStart($event, i)" @dragenter.prevent="onDragOver($event, i)" @dragover="onDragOver($event, i)"
                   @drop="onDropCard($event)" @dragend="onDragEnd">
                <div class="relative aspect-[4/5] rounded-lg overflow-hidden bg-stone-100"
                     :class="dragFrom === i ? 'ring-2 ring-[var(--accent-500)]' : ''">
                  <img :src="f.url" class="w-full h-full object-cover pointer-events-none select-none" alt="" loading="lazy" draggable="false" />
                  <span class="absolute top-1.5 start-1.5 text-[10px] font-bold text-white bg-stone-900 rounded-[5px] px-1.5 py-px">{{ i === 0 ? t('souk.mainPhoto') : i + 1 }}</span>
                  <button v-if="d.canEdit" class="absolute top-1 end-1 w-8 h-8 rounded-md bg-white/90 text-rose-700 hover:bg-white inline-flex items-center justify-center disabled:opacity-30"
                          :disabled="busy" :title="t('souk.remove')" :aria-label="t('souk.remove')" @click="removeFinal(f.url)">
                    <Icon name="trash-2" :size="15" />
                  </button>
                  <div v-if="d.canEdit && order.length > 1" class="absolute bottom-1 end-1 flex gap-1">
                    <button class="w-8 h-8 rounded-md bg-white/90 text-stone-700 hover:bg-white inline-flex items-center justify-center disabled:opacity-30"
                            :disabled="i === 0 || busy" :title="t('souk.pub.moveEarlier')" :aria-label="t('souk.pub.moveEarlier')" @click="nudge(i, -1)">
                      <Icon name="arrow-up" :size="15" />
                    </button>
                    <button class="w-8 h-8 rounded-md bg-white/90 text-stone-700 hover:bg-white inline-flex items-center justify-center disabled:opacity-30"
                            :disabled="i === order.length - 1 || busy" :title="t('souk.pub.moveLater')" :aria-label="t('souk.pub.moveLater')" @click="nudge(i, 1)">
                      <Icon name="arrow-down" :size="15" />
                    </button>
                  </div>
                </div>
                <label v-if="d.colors.length > 1" :for="'fc-' + i" class="sr-only">{{ t('souk.colorsLbl') }} {{ i + 1 }}</label>
                <select v-if="d.colors.length > 1" :id="'fc-' + i" :value="f.color" :disabled="!d.canEdit || busy"
                        class="w-full h-8 rounded-lg border border-stone-300 px-1.5 text-[12px] bg-white" @change="setColor(i, $event.target.value)">
                  <option value="">{{ t('souk.allColors') }}</option>
                  <option v-for="c in d.colors" :key="c.code" :value="c.code">{{ colorName(c) }}</option>
                </select>
              </div>

              <!-- one colour (or none): the upload tile closes the grid -->
              <label v-if="d.canEdit && zones.length === 1"
                     class="aspect-[4/5] rounded-lg bg-stone-50 outline-2 outline-dashed -outline-offset-2 flex flex-col items-center justify-center gap-1.5 text-[12px] font-semibold text-stone-600 cursor-pointer text-center px-2 hover:bg-stone-100"
                     :class="[hoverZone === '' ? 'outline-[var(--accent-500)] bg-[var(--accent-50)]' : 'outline-stone-300', uploading ? 'opacity-60 pointer-events-none' : '']"
                     @dragover="onZoneOver($event, '')" @dragleave="hoverZone = null" @drop="onZoneDrop($event, '')">
                <Icon name="upload-cloud" :size="22" />
                <span>{{ uploading ? t('souk.uploadingN').replace('{n}', uploading) : hoverZone === '' ? t('souk.pub.dropHere') : t('souk.uploadFinals') }}</span>
                <input type="file" accept="image/*" multiple class="hidden" @change="onFiles($event, '')" />
              </label>
            </div>
            <div v-if="!order.length && !d.canEdit" class="text-center text-[12px] text-stone-400 py-6">{{ t('souk.noFinals') }}</div>

            <!-- several colours: one drop zone per colour, tied to it -->
            <div v-if="d.canEdit && zones.length > 1" class="space-y-1.5">
              <div class="text-[12px] font-semibold text-stone-700">{{ t('souk.pub.addFor') }}</div>
              <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-2">
                <label v-for="z in zones" :key="z.code"
                       class="min-h-[72px] rounded-lg px-3 py-2 outline-2 outline-dashed -outline-offset-2 flex flex-col items-center justify-center gap-0.5 text-center cursor-pointer"
                       :class="[hoverZone === z.code ? 'outline-[var(--accent-500)] bg-[var(--accent-50)]'
                         : z.missing ? 'outline-amber-300 bg-amber-50' : 'outline-stone-300 bg-stone-50 hover:bg-stone-100',
                         uploading ? 'opacity-60 pointer-events-none' : '']"
                       @dragover="onZoneOver($event, z.code)" @dragleave="hoverZone = null" @drop="onZoneDrop($event, z.code)">
                  <span class="inline-flex items-center gap-1 text-[12.5px] font-bold text-stone-800"><Icon name="upload-cloud" :size="15" />{{ z.label }}</span>
                  <span class="text-[11px]" :class="z.missing ? 'text-amber-800 font-semibold' : 'text-stone-600'">
                    {{ uploadingCode === z.code && uploading ? t('souk.uploadingN').replace('{n}', uploading)
                      : hoverZone === z.code ? t('souk.pub.dropHere')
                      : z.count ? t('souk.pub.nFinals').replace('{n}', z.count) : t('souk.pub.noneYet') }}
                  </span>
                  <input type="file" accept="image/*" multiple class="hidden" @change="onFiles($event, z.code)" />
                </label>
              </div>
            </div>

            <div v-if="d.colorsWithout.length" class="flex items-center gap-2 bg-amber-50 rounded-lg px-2.5 py-2 text-[12px] text-amber-800">
              <Icon name="alert-triangle" :size="15" class="shrink-0 text-amber-700" />
              <span>{{ t('souk.colorNeedsFinal').replace('{list}', d.colorsWithout.map(colorOf).join(' · ')) }}</span>
            </div>
          </section>

          <!-- actions -->
          <section v-if="d.canEdit" class="space-y-2">
            <div v-if="returning" class="lp-card p-4 space-y-2">
              <label class="block text-[12.5px] font-bold" for="souk-return">{{ t('souk.returnWhy') }}</label>
              <textarea id="souk-return" v-model="reason" rows="2" class="w-full rounded-lg border border-stone-300 px-3 py-2 text-[13px]" :placeholder="t('souk.returnHint')" />
              <div class="flex gap-2 flex-wrap">
                <button class="h-[42px] px-4 rounded-lg bg-amber-600 text-white text-[13px] font-bold disabled:opacity-40" :disabled="busy || !reason.trim()" @click="sendBack">{{ t('souk.returnConfirm') }}</button>
                <button class="h-[42px] px-4 rounded-lg bg-white ring-1 ring-inset ring-stone-300 text-[13px] font-semibold text-stone-700" @click="returning = false">{{ t('souk.cancel') }}</button>
              </div>
            </div>
            <div class="flex gap-2 flex-wrap">
              <button class="w-full sm:w-auto h-[42px] px-[18px] rounded-lg bg-[var(--accent-600)] enabled:hover:bg-[var(--accent-700)] text-white text-[13.5px] font-bold disabled:bg-stone-200 disabled:text-stone-600"
                      :disabled="busy || !!uploading || orderSaving || !order.length || d.colorsWithout.length > 0" @click="send">
                {{ busy && !orderSaving ? t('souk.sending') : t('souk.toContent') }}
              </button>
              <button v-if="!returning" class="w-full sm:w-auto min-h-[42px] py-2 px-4 rounded-lg bg-white ring-1 ring-inset ring-stone-300 text-[13px] font-semibold text-stone-700 hover:bg-stone-50" @click="returning = true">{{ t('souk.returnToFloor') }}</button>
            </div>
            <p class="text-[11.5px] text-stone-500">{{ t('souk.toContentNote') }}</p>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { postPhoto } from "@/lib/soukPhoto";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t, locale } = useI18n();
const { success, warn } = useToast();
const route = useRoute();
const router = useRouter();
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const uploading = ref(0);
const uploadingCode = ref(null);
const returning = ref(false);
const reason = ref("");
const d = computed(() => data.value?.detail || null);

// The finals as shown: a local copy, so a drag re-orders live and the server
// hears ONE final_set when the drag ends (the arrows: one call after a short
// pause, however many taps).
const order = ref([]);
const dragFrom = ref(null);
const dragMoved = ref(false);
const hoverZone = ref(null);
const orderSaving = ref(false);
let nudgeTimer = null;

watch(() => d.value?.finals, (f) => {
  if (dragFrom.value == null) order.value = (f || []).map((x) => ({ ...x }));
}, { immediate: true });

const colorName = (c) => (c.code ? (locale.value === "ar" ? c.ar || c.fr : c.fr || c.code) : t("souk.theProduct"));
const colorOf = (code) => colorName(d.value.colors.find((c) => c.code === code) || { code, fr: code });
const rawOf = (code) => (d.value?.photos || []).filter((p) => (p.color || "") === code);
const sizes = computed(() => [...new Set((d.value?.variants || []).map((v) => v.size).filter(Boolean))]);
const weights = computed(() => {
  const seen = {};
  for (const v of d.value?.variants || []) if (v.grams) seen[v.size || "—"] = v.grams;
  const keys = Object.keys(seen);
  if (!keys.length) return "";
  return keys.map((k) => (k === "—" ? "" : k + " ") + (seen[k] >= 1000 ? (seen[k] / 1000).toFixed(2) + " kg" : seen[k] + " g")).join(" · ");
});
const realColorCount = computed(() => (d.value?.colors || []).filter((c) => c.code).length || 1);
// Days in the queue: whole days, "today" under one.
const ageText = (a) => (Number(a) < 1 ? t("souk.pub.today") : t("souk.ageDays").replace("{n}", Math.floor(Number(a))));
// A phone shows the queue OR the product; the route decides which.
const listOnly = computed(() => !route.params.name);
const zipUrl = computed(() => "/api/method/logistics_portal.api.souk.raw_zip?name=" + encodeURIComponent(d.value?.name || ""));

// Upload targets: one per real colour + "all colours"; a single-colour
// product has just the one tile.
const zones = computed(() => {
  const cols = (d.value?.colors || []).filter((c) => c.code);
  if (cols.length < 2) return [{ code: "", label: t("souk.uploadFinals"), count: order.value.length, missing: false }];
  const without = new Set(d.value.colorsWithout || []);
  return [
    ...cols.map((c) => ({ code: c.code, label: colorName(c), count: order.value.filter((f) => f.color === c.code).length,
      missing: without.has(c.code) })),
    { code: "", label: t("souk.pub.dropAllColors"), count: order.value.filter((f) => !f.color).length, missing: false },
  ];
});

// Time in the step against its limit (settings.stageDays.studio).
const dur = (h) => {
  const a = Math.abs(h);
  return a < 48 ? t("souk.pub.hours").replace("{n}", Math.round(a)) : t("souk.pub.days").replace("{n}", Math.round(a / 24));
};
const clock = computed(() => {
  const det = d.value;
  if (!det) return null;
  const lim = Number(data.value?.limit) || 0;
  if (det.hoursLeft == null || !lim) {
    return det.age != null ? { late: false, text: t("souk.pub.inStep").replace("{a}", t("souk.pub.days").replace("{n}", det.age)) } : null;
  }
  const late = det.hoursLeft < 0;
  return {
    late,
    text: t("souk.pub.ofLimit").replace("{a}", dur(lim * 24 - det.hoursLeft)).replace("{l}", t("souk.pub.days").replace("{n}", lim))
      + " · " + (late ? t("souk.pub.lateBy").replace("{n}", dur(det.hoursLeft)) : t("souk.pub.left").replace("{n}", dur(det.hoursLeft))),
  };
});

async function load() {
  loading.value = true;
  clearTimeout(nudgeTimer);
  try {
    const next = await api("souk.studio_boot", route.params.name ? { name: route.params.name } : {});
    if (next?.detail?.name !== d.value?.name) {
      returning.value = false;
      reason.value = "";
    }
    data.value = next;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

function setDetail(det) {
  data.value = { ...data.value, detail: det };
}

async function upload(files, code) {
  const imgs = files.filter((f) => /^image\//.test(f.type || ""));
  if (imgs.length < files.length) warn(t("souk.failed"), t("souk.pub.onlyImages"));
  if (!imgs.length) return;
  uploadingCode.value = code;
  for (let i = 0; i < imgs.length; i++) {
    uploading.value = imgs.length - i;
    try {
      setDetail(await postPhoto("final_add", { name: d.value.name, color: code }, imgs[i], { max: 2048, quality: 0.9 }));
    } catch (err) {
      warn(t("souk.failed"), String(err.message || err));
      break;
    }
  }
  uploading.value = 0;
  uploadingCode.value = null;
}
function onFiles(e, code) {
  const files = [...(e.target.files || [])];
  e.target.value = "";
  upload(files, code);
}
const isFileDrag = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
function onZoneOver(e, code) {
  if (!isFileDrag(e) || uploading.value) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = "copy";
  hoverZone.value = code;
}
function onZoneDrop(e, code) {
  hoverZone.value = null;
  if (!isFileDrag(e)) return;
  e.preventDefault();
  if (!d.value?.canEdit || uploading.value) return;
  upload([...(e.dataTransfer.files || [])], code);
}

function onSectionOver(e) {
  if (isFileDrag(e)) e.preventDefault();
}
function onSectionDrop(e) {
  if (!isFileDrag(e) || e.defaultPrevented) return;
  e.preventDefault();
  if (d.value?.canEdit && !uploading.value) upload([...(e.dataTransfer.files || [])], "");
}

// --- order -------------------------------------------------------------------
const sameOrder = () => {
  const a = (d.value?.finals || []).map((f) => f.url + "|" + (f.color || "")).join(",");
  const b = order.value.map((f) => f.url + "|" + (f.color || "")).join(",");
  return a === b;
};

async function save(list) {
  busy.value = true;
  orderSaving.value = true;
  try {
    setDetail(await apiPost("souk.final_set", {
      name: d.value.name, finals: JSON.stringify(list.map((f) => ({ url: f.url, color: f.color || "" }))),
    }));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load();
  } finally {
    busy.value = false;
    orderSaving.value = false;
  }
}
function setColor(i, code) {
  clearTimeout(nudgeTimer);
  order.value = order.value.map((f, j) => (j === i ? { ...f, color: code } : f));
  save(order.value);
}
function nudge(i, step) {
  const j = i + step;
  if (j < 0 || j >= order.value.length) return;
  const list = [...order.value];
  [list[i], list[j]] = [list[j], list[i]];
  order.value = list;
  clearTimeout(nudgeTimer);
  nudgeTimer = setTimeout(() => { if (!sameOrder()) save(order.value); }, 700);
}

function onDragStart(e, i) {
  if (!d.value?.canEdit || busy.value) return e.preventDefault();
  dragFrom.value = i;
  dragMoved.value = false;
  e.dataTransfer.effectAllowed = "move";
  // Firefox starts a drag only with some data on it.
  try { e.dataTransfer.setData("text/plain", order.value[i].url); } catch (_) { /* older engines */ }
}
function onDragOver(e, i) {
  if (dragFrom.value == null) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = "move";
  if (i === dragFrom.value) return;
  const list = [...order.value];
  const [x] = list.splice(dragFrom.value, 1);
  list.splice(i, 0, x);
  order.value = list;
  dragFrom.value = i;
  dragMoved.value = true;
}
function onDropCard(e) {
  if (dragFrom.value != null) e.preventDefault();
}
function onDragEnd() {
  const moved = dragMoved.value;
  dragFrom.value = null;
  dragMoved.value = false;
  if (moved && !sameOrder()) save(order.value);
  else order.value = (d.value?.finals || []).map((x) => ({ ...x }));
}

async function removeFinal(url) {
  if (!window.confirm(t("souk.pub.removeConfirm"))) return;
  clearTimeout(nudgeTimer);
  busy.value = true;
  try {
    // A pending arrow re-order goes first: final_set wants the same photos.
    if (!sameOrder()) {
      setDetail(await apiPost("souk.final_set", {
        name: d.value.name, finals: JSON.stringify(order.value.map((f) => ({ url: f.url, color: f.color || "" }))),
      }));
    }
    await apiPost("souk.photo_remove", { name: d.value.name, url, which: "final" });
    await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load();
  } finally {
    busy.value = false;
  }
}

async function go() {
  if (route.params.name) await router.push({ name: "SoukStudio" });
  else await load();
}

async function send() {
  clearTimeout(nudgeTimer);
  if (!sameOrder()) await save(order.value);
  busy.value = true;
  try {
    const r = await apiPost("souk.studio_send", { name: d.value.name });
    success(t("souk.sentToContent").replace("{n}", r.media));
    await go();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load();
  } finally {
    busy.value = false;
  }
}

async function sendBack() {
  busy.value = true;
  try {
    await apiPost("souk.studio_return", { name: d.value.name, reason: reason.value });
    success(t("souk.sentBack"));
    await go();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

watch(() => route.params.name, load);
onMounted(load);
onBeforeUnmount(() => clearTimeout(nudgeTimer));
</script>

<style scoped>
/* Drag is for a mouse; a finger gets the arrows (and the hint says so). */
.souk-grab { cursor: grab; }
.souk-coarse { display: none; }
.souk-fine { display: inline-flex; }
@media (pointer: coarse) {
  .souk-grab { cursor: default; }
  .souk-coarse { display: inline; }
  .souk-fine { display: none; }
}
</style>
