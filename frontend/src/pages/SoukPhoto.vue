<template>
  <!-- In-house photos, on the phone, within 24 h of receiving. The first
       colour needs six angles, every other colour one front shot; a retake
       replaces the old photo. The photos land on the product card itself, so
       marketing never has to ask for them on WhatsApp. The sample pieces sit
       in Studio - JM. Layout = the Photo artboard: white header with the
       clock and the progress bar, colour tabs, a 2-up slot grid, fixed send.
       Backend: souk.photo_queue / photo_boot / photo_add / photo_remove /
       photos_send. -->
  <div class="pb-40 text-stone-900 st-photos">
    <header class="ph-head border-b border-stone-200">
      <div class="max-w-[560px] mx-auto px-4 py-3.5 flex flex-col gap-2.5">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex items-start gap-1">
            <!-- back to the queue: always there on a product, whatever its clock -->
            <router-link v-if="name" :to="{ name: 'SoukPhoto' }" :aria-label="t('souk.ph.back')" :title="t('souk.ph.back')"
                         class="shrink-0 w-11 h-11 -ms-3 -my-1.5 rounded-lg inline-flex items-center justify-center text-stone-600 hover:bg-stone-100">
              <Icon :name="isRTL ? 'chevron-right' : 'chevron-left'" :size="18" />
            </router-link>
            <span v-if="!name" class="sk-ico sk-ico-solid shrink-0 me-1.5"><Icon name="camera" :size="17" /></span>
            <img v-else-if="d && d.image" :src="d.image" class="w-10 h-10 rounded-xl object-cover shrink-0 me-1 ring-1 ring-black/5" alt="" />
            <div class="min-w-0 flex flex-col gap-px">
              <span class="text-[12px] font-semibold st-ink truncate">{{ t('souk.photoKicker') }}</span>
              <h1 class="m-0 text-[16px] font-bold leading-snug truncate">{{ d ? d.title : t('souk.photoTitle') }}</h1>
            </div>
          </div>
          <span v-if="d && d.hoursLeft != null" class="shrink-0 rounded-md px-2 py-[3px] text-[12px] font-bold tabular-nums"
                :class="clockClass(d.hoursLeft, 'chip')">
            {{ hoursText(d.hoursLeft) }}
          </span>
        </div>
        <div v-if="d" class="flex flex-col gap-1">
          <div class="flex justify-between gap-3 text-[12px] text-stone-600 tabular-nums">
            <span class="shrink-0">{{ t('souk.photoProgress').replace('{d}', doneCount).replace('{n}', requiredCount) }}</span>
            <span class="text-end leading-snug">{{ t('souk.photoRule') }}</span>
          </div>
          <div class="h-2 rounded-full bg-white/80 ring-1 ring-inset ring-black/5 overflow-hidden" role="progressbar" :aria-valuenow="doneCount" aria-valuemin="0" :aria-valuemax="requiredCount">
            <div class="h-full rounded-full transition-all" :class="doneCount >= requiredCount ? 'bg-emerald-500' : 'st-solid'" :style="{ width: (requiredCount ? (doneCount / requiredCount) * 100 : 0) + '%' }" />
          </div>
        </div>
      </div>
    </header>

    <div class="max-w-[560px] mx-auto px-4 pt-3 flex flex-col gap-3">
      <div v-if="loading" class="h-[280px] rounded-xl bg-white ring-1 ring-inset ring-stone-200 animate-pulse" />

      <!-- queue -->
      <template v-else-if="!name">
        <div v-if="!queue.length" class="lp-card p-8 flex flex-col items-center gap-2.5 text-center text-[14px] text-stone-500">
          <span class="sk-ico sk-ico-lg"><Icon name="inbox" :size="20" /></span>{{ t('souk.photoNone') }}
        </div>
        <div v-else class="sk-sec">
          <div class="sk-sec-h">
            <span class="sk-ico sk-ico-sm"><Icon name="layers" :size="14" /></span>
            <div class="min-w-0 flex-1"><div class="sk-sec-t">{{ t('souk.nProducts').replace('{n}', queue.length) }}</div><div class="sk-sec-s">{{ t('souk.oldestFirst') }}</div></div>
          </div>
          <router-link v-for="(r, i) in queue" :key="r.name" :to="{ name: 'SoukPhoto', params: { name: r.name } }"
                       class="flex items-center gap-3 px-3.5 py-3 min-h-[72px] hover:bg-stone-50 border-t border-stone-100"
                       :class="r.late ? 'bg-rose-50/50' : ''">
            <img v-if="r.image" :src="r.image" class="w-12 h-12 shrink-0 rounded-xl object-cover" alt="" />
            <span v-else class="w-12 h-12 shrink-0 rounded-xl bg-stone-100 text-stone-400 inline-flex items-center justify-center"><Icon name="image" :size="16" /></span>
            <div class="min-w-0 flex-1 flex flex-col gap-1">
              <span class="text-[14px] font-semibold truncate">{{ r.title }}</span>
              <span class="text-[12px] text-stone-600 tabular-nums truncate">
                {{ t('souk.photoProgress').replace('{d}', r.done).replace('{n}', r.required) }} · {{ t('souk.nColors').replace('{n}', r.colors) }}
              </span>
              <span class="h-1.5 rounded-full bg-stone-100 overflow-hidden" aria-hidden="true">
                <span class="block h-full rounded-full" :class="r.done >= r.required ? 'bg-emerald-500' : 'st-solid'" :style="{ width: (r.required ? (r.done / r.required) * 100 : 0) + '%' }" />
              </span>
            </div>
            <span v-if="r.samples" class="shrink-0 hidden min-[380px]:inline-flex items-center gap-0.5 text-[11px] font-semibold text-stone-500"><Icon name="package" :size="11" />{{ r.samples }}</span>
            <span v-if="r.hoursLeft != null" class="shrink-0 rounded-full px-2 py-[3px] text-[12px] font-bold tabular-nums inline-flex items-center gap-1" :class="clockClass(r.hoursLeft, 'chip')"><Icon name="clock" :size="11" />{{ hoursText(r.hoursLeft) }}</span>
          </router-link>
        </div>
      </template>

      <template v-else-if="d">
        <div v-if="!d.canEdit" class="bg-white ring-1 ring-inset ring-stone-200 rounded-xl p-4 text-[14px] text-stone-600">
          {{ t('souk.photoNotNow') }}
          <router-link :to="{ name: 'SoukProduct', params: { name: d.name } }" class="font-bold text-[var(--accent-700)] underline">{{ t('souk.toProduct') }}</router-link>
        </div>

        <!-- sent back here: why -->
        <div v-if="d.backNote" class="rounded-xl bg-amber-50 ring-1 ring-inset ring-amber-200 px-3.5 py-3 text-[13px] text-amber-900 flex gap-2.5 items-start">
          <Icon name="undo-2" :size="16" class="shrink-0 mt-0.5 text-amber-700" />
          <span class="min-w-0 break-words"><b>{{ t('souk.bk.said').replace('{by}', d.backNote.by) }}</b> {{ d.backNote.note }}</span>
        </div>
        <!-- marketing has the card: a retake reaches them, nothing is sent -->
        <div v-if="d.canEdit && d.stage === 'studio'" class="st-studio rounded-xl st-soft px-3.5 py-3 text-[13px] text-stone-800 flex gap-2.5 items-start">
          <Icon name="sparkles" :size="16" class="shrink-0 mt-0.5 st-fg" />
          <span class="min-w-0">{{ t('souk.bk.rawInStudio') }}
            <router-link :to="{ name: 'SoukProduct', params: { name: d.name } }" class="font-bold underline">{{ t('souk.toProduct') }}</router-link>
          </span>
        </div>

        <!-- colours -->
        <nav v-if="d.colors.length > 1" class="flex gap-1.5 overflow-x-auto" :aria-label="t('souk.nColors').replace('{n}', d.colors.length)">
          <button v-for="(c, i) in d.colors" :key="c.code" type="button" :aria-current="color === c.code ? 'true' : undefined"
                  class="min-w-max h-11 px-3 rounded-xl text-[13px] font-semibold inline-flex items-center justify-center gap-1.5 tabular-nums"
                  :class="[color === c.code ? 'st-solid' : 'bg-white ring-1 ring-inset ring-stone-200 text-stone-700', i === 0 ? 'flex-[1.4_1_0%]' : 'flex-[1_1_0%]']"
                  @click="color = c.code">
            <span v-if="c.code" class="w-3.5 h-3.5 rounded-full ring-1 ring-black/15 shrink-0" :style="{ background: swatch(c.code) }" />
            {{ colorName(c) }}<template v-if="i === 0"> · {{ t('souk.primary') }}</template>
            <span>{{ colorCount(c, i) }}</span>
            <Icon v-if="colorDone(c, i)" name="check" :size="13" :stroke-width="2.5" :class="color === c.code ? 'text-white' : 'text-emerald-700'" />
          </button>
        </nav>

        <!-- angles -->
        <section class="grid grid-cols-2 gap-2.5">
          <div v-for="s in slotsFor(color)" :key="s" class="flex flex-col gap-1.5">
            <button v-if="photoAt(color, s)" type="button" class="relative block w-full aspect-square rounded-2xl overflow-hidden bg-stone-200 ring-2 ring-emerald-400/70 disabled:cursor-default"
                    :aria-label="t('souk.ph.retake') + ' · ' + t('souk.slot_' + s)"
                    :disabled="!d.canEdit || !!uploading" @click="shoot(color, s)">
              <img :src="photoAt(color, s).url" class="w-full h-full object-cover" alt="" />
              <span class="absolute top-2 end-2 w-6 h-6 rounded-full bg-emerald-700 text-white flex items-center justify-center"><Icon name="check" :size="13" :stroke-width="3" /></span>
              <span v-if="d.canEdit && uploading !== color + '|' + s" class="absolute bottom-2 start-2 h-7 px-2 rounded-md bg-white/90 text-stone-800 text-[12px] font-bold inline-flex items-center gap-1">
                <Icon name="camera" :size="12" />{{ t('souk.ph.retake') }}
              </span>
              <span v-if="uploading === color + '|' + s" class="absolute inset-0 bg-white/70 flex items-center justify-center">
                <span class="w-7 h-7 rounded-full border-2 border-stone-300 border-t-stone-700 animate-spin" />
              </span>
            </button>
            <button v-else type="button" class="w-full aspect-square rounded-2xl st-soft outline-dashed outline-2 [outline-offset:-8px] ph-empty flex flex-col items-center justify-center gap-1.5 st-ink disabled:opacity-50"
                    :aria-label="t('souk.shoot') + ' · ' + t('souk.slot_' + s)"
                    :disabled="!d.canEdit || !!uploading" @click="shoot(color, s)">
              <Icon v-if="uploading !== color + '|' + s" name="camera" :size="26" :stroke-width="1.8" />
              <span v-else class="w-6 h-6 rounded-full border-2 border-stone-300 border-t-stone-700 animate-spin" />
              <span class="text-[13px] font-semibold">{{ t('souk.shoot') }}</span>
            </button>
            <div class="flex flex-col">
              <span class="text-[13px] font-semibold">{{ t('souk.slot_' + s) }}</span>
              <span class="text-[12px] text-stone-600 leading-snug">{{ t('souk.slotHint_' + s) }}</span>
            </div>
          </div>
        </section>
        <span v-if="d.colors.length > 1" class="text-[12px] text-stone-600 leading-normal">{{ t('souk.otherColorRule') }}</span>
        <!-- the website photos are cut from these: a clean shot = a clean result -->
        <div v-if="d.canEdit" class="flex items-start gap-2.5 rounded-xl st-soft px-3 py-2.5 text-[12.5px] text-stone-700 leading-relaxed">
          <span class="sk-ico sk-ico-sm shrink-0"><Icon name="sparkles" :size="13" /></span>
          <span>{{ t('souk.st.shootTip') }}</span>
        </div>
        <span v-if="d.samples.length" class="text-[12px] text-stone-500 leading-normal">
          {{ t('souk.samplesAt') }}
          <span v-for="s in d.samples" :key="s.sku" class="font-mono me-2 inline-block" dir="ltr">{{ s.sku }}×{{ s.qty }}</span>
        </span>

        <!-- extras -->
        <section class="sk-sec">
          <div class="sk-sec-h">
            <span class="sk-ico sk-ico-sm"><Icon name="image" :size="14" /></span>
            <div class="min-w-0 flex-1"><h2 class="sk-sec-t m-0">{{ t('souk.extras') }}<template v-if="extras.length"> · {{ extras.length }}</template></h2><div class="sk-sec-s">{{ t('souk.optional') }}</div></div>
          </div>
          <div class="sk-sec-b flex gap-2 flex-wrap">
            <div v-for="p in extras" :key="p.url" class="relative w-20 h-20 rounded-[10px] overflow-hidden bg-stone-200">
              <img :src="p.url" class="w-full h-full object-cover" alt="" />
              <button v-if="d.canEdit" type="button" class="absolute top-0 end-0 w-11 h-11 flex items-start justify-end p-1" :aria-label="t('souk.ph.remove')" @click="remove(p.url)">
                <span class="w-7 h-7 rounded-full bg-white/90 text-rose-700 flex items-center justify-center"><Icon name="x" :size="14" /></span>
              </button>
            </div>
            <button v-if="d.canEdit" type="button" class="w-20 h-20 rounded-[10px] bg-white ring-2 ring-inset ring-stone-200 outline-dashed outline-2 outline-stone-300 [outline-offset:-6px] text-stone-600 flex flex-col items-center justify-center gap-0.5 text-[12px] font-semibold disabled:opacity-50"
                    :disabled="!!uploading" @click="shoot(color, 'extra')">
              <Icon name="plus" :size="18" />{{ t('souk.addPhoto') }}
            </button>
          </div>
        </section>

        <!-- specs -->
        <section class="sk-sec">
          <div class="sk-sec-h">
            <span class="sk-ico sk-ico-sm"><Icon name="scale" :size="14" /></span>
            <div class="min-w-0 flex-1"><label class="sk-sec-t block" for="souk-specs">{{ t('souk.specs') }}</label>
              <div v-if="d.sizes.length" class="sk-sec-s">{{ t('souk.specsSizes').replace('{s}', d.sizes.join(' · ')) }}</div></div>
          </div>
          <div class="sk-sec-b">
          <textarea id="souk-specs" v-model="specs" rows="3" :disabled="!d.canSend"
                    class="w-full rounded-xl border border-stone-300 p-3 text-[16px] bg-white outline-none focus:ring-2 focus:ring-sky-500/30" :placeholder="t('souk.specsHint')" />
          </div>
        </section>

        <input ref="fileInput" type="file" accept="image/*" capture="environment" class="hidden" @change="onFile" />
      </template>
    </div>

    <footer v-if="d && d.canSend && name" class="lp-footer bg-white px-4 pt-3 pb-4">
      <div class="max-w-[560px] mx-auto flex flex-col gap-1.5">
        <span v-if="d.missing.length" class="text-[12px] text-stone-600 text-center leading-snug">{{ missingText }}</span>
        <button type="button" class="st-studio w-full h-[52px] rounded-xl st-solid text-[15px] font-bold inline-flex items-center justify-center gap-2 disabled:!bg-stone-200 disabled:!text-stone-500 disabled:shadow-none"
                :disabled="busy || d.missing.length > 0 || !!uploading" @click="send">
          <Icon name="sparkles" :size="17" />{{ busy ? t('souk.sending') : t('souk.toMarketing') }}
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { postPhoto } from "@/lib/soukPhoto";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { swatch } from "@/souk/stages";

const { t, locale, isRTL } = useI18n();
const { success, warn } = useToast();
const route = useRoute();
const router = useRouter();
const name = computed(() => route.params.name || "");
const loading = ref(true);
const busy = ref(false);
const queue = ref([]);
const d = ref(null);
const color = ref("");
const specs = ref("");
const uploading = ref("");
const fileInput = ref(null);
let aim = null;

const colorName = (c) => (c.code ? (locale.value === "ar" ? c.ar || c.fr : c.fr || c.code) : t("souk.theProduct"));
const slotsFor = (code) => (d.value && d.value.colors.length && code === d.value.colors[0].code ? d.value.slots : ["front"]);
const photoAt = (code, slot) => (d.value?.photos || []).find((p) => (p.color || "") === code && p.slot === slot);
const extras = computed(() => (d.value?.photos || []).filter((p) => p.slot === "extra" && (p.color || "") === color.value));
const requiredCount = computed(() => (d.value ? d.value.slots.length + d.value.colors.length - 1 : 0));
const doneCount = computed(() => requiredCount.value - (d.value?.missing.length || 0));
const colorCount = (c, i) => {
  const need = i === 0 ? d.value.slots.length : 1;
  const miss = d.value.missing.filter((m) => m.color === c.code).length;
  return `${need - miss}/${need}`;
};
const colorDone = (c) => !d.value.missing.some((m) => m.color === c.code);
const missingText = computed(() => {
  const by = {};
  for (const m of d.value?.missing || []) by[m.color] = (by[m.color] || 0) + 1;
  // A product without colours: "Still missing: 6 photos", not "The product 6".
  if (d.value.colors.length === 1 && !d.value.colors[0].code) {
    return t("souk.photoMissingN").replace("{n}", by[""] || 0);
  }
  const parts = d.value.colors.filter((c) => by[c.code]).map((c) => `${colorName(c)} ${by[c.code]}`);
  return t("souk.photoMissing").replace("{list}", parts.join(" · "));
});
// The clock never reads "0 h" or "-0 h": under an hour it counts minutes,
// past due it says how late (at least 1 h).
function hoursText(h) {
  if (h == null) return "";
  const x = Number(h);
  if (x < 0) return t("souk.ph.lateBy").replace("{n}", Math.max(1, Math.floor(-x)));
  if (x < 1) {
    const m = Math.floor(x * 60);
    return m >= 1 ? t("souk.ph.minLeft").replace("{n}", m) : t("souk.ph.underHour");
  }
  return t("souk.ph.hoursLeft").replace("{n}", Math.floor(x));
}
// The artboard's clock chip is amber while it runs; late turns rose, the
// last hours a shade darker.
function clockClass(h, kind) {
  const x = Number(h);
  if (x < 0) return kind === "chip" ? "bg-rose-50 text-rose-700" : "text-rose-700";
  if (x < 6) return kind === "chip" ? "bg-amber-100 text-amber-800" : "text-amber-800";
  return kind === "chip" ? "bg-amber-50 text-amber-700" : "text-amber-700";
}

async function load() {
  loading.value = true;
  d.value = null;
  try {
    if (!name.value) {
      queue.value = (await api("souk.photo_queue")).queue || [];
    } else {
      d.value = await api("souk.photo_boot", { name: name.value });
      specs.value = d.value.specs || "";
      // Open on the first colour that still misses a photo.
      const first = d.value.missing[0];
      color.value = first ? first.color : d.value.colors[0].code;
    }
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

function shoot(code, slot) {
  aim = { color: code, slot };
  if (fileInput.value) {
    fileInput.value.value = "";
    fileInput.value.click();
  }
}

async function onFile(e) {
  const file = e.target.files && e.target.files[0];
  if (!file || !aim) return;
  const { color: c, slot } = aim;
  uploading.value = c + "|" + slot;
  try {
    const r = await postPhoto("photo_add", { name: d.value.name, color: c, slot }, file);
    d.value.photos = r.photos;
    d.value.missing = r.missing;
    // A colour finished: move on to the next one still missing a photo.
    if (!r.missing.some((m) => m.color === c) && r.missing.length) color.value = r.missing[0].color;
  } catch (err) {
    warn(t("souk.failed"), String(err.message || err));
  } finally {
    uploading.value = "";
  }
}

async function remove(url) {
  if (!window.confirm(t("souk.ph.removeConfirm"))) return;
  try {
    const r = await apiPost("souk.photo_remove", { name: d.value.name, url });
    d.value.photos = r.photos;
    d.value.missing = r.missing;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  }
}

async function send() {
  busy.value = true;
  try {
    await apiPost("souk.photos_send", { name: d.value.name, specs: specs.value });
    success(t("souk.sentToMarketing"));
    router.push({ name: "SoukPhoto" });
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

watch(name, load);
onMounted(load);
</script>

<style scoped>
/* The phone header carries the stage tint (sky) like the other stage screens. */
.ph-head { background: linear-gradient(180deg, rgb(var(--st) / 0.10), rgb(var(--st) / 0.03)), #fff; }
.ph-empty { outline-color: rgb(var(--st) / 0.45); }
:global(html[data-theme="dark"] .ph-head) { background: linear-gradient(180deg, rgb(var(--st) / 0.16), rgb(var(--st) / 0.05)), rgb(28 25 23); }
</style>
