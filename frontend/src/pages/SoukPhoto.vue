<template>
  <!-- In-house photos, on the phone, within 24 h of receiving. The first
       colour needs six angles, every other colour one front shot; a retake
       replaces the old photo. The photos land on the product card itself, so
       marketing never has to ask for them on WhatsApp. The sample pieces sit
       in Studio - JM. Backend: souk.photo_queue / photo_boot / photo_add /
       photo_remove / photos_send. -->
  <div class="max-w-[560px] mx-auto px-4 pt-3 pb-48 space-y-4">
    <!-- back to the queue: always there on a product, whatever its clock -->
    <div v-if="name" class="flex items-center justify-between gap-2 -mb-1">
      <router-link :to="{ name: 'SoukPhoto' }"
                   class="h-11 -ms-2 px-2 rounded-xl inline-flex items-center gap-1 text-[13px] font-semibold text-stone-700 hover:bg-stone-100">
        <Icon :name="isRTL ? 'chevron-right' : 'chevron-left'" :size="16" />{{ t('souk.ph.back') }}
      </router-link>
      <span v-if="d && d.hoursLeft != null" class="shrink-0 h-7 px-2.5 rounded-lg text-[11.5px] font-bold inline-flex items-center tabular-nums"
            :class="clockClass(d.hoursLeft, 'chip')">
        {{ hoursText(d.hoursLeft) }}
      </span>
    </div>
    <header class="flex items-center gap-3">
      <img v-if="d && d.image" :src="d.image" class="w-12 h-12 shrink-0 rounded-xl object-cover ring-1 ring-stone-200" alt="" />
      <div class="min-w-0">
        <div class="text-[11.5px] font-semibold text-stone-500">{{ t('souk.photoKicker') }}</div>
        <h1 class="text-[18px] font-bold text-stone-900 truncate">{{ d ? d.title : t('souk.photoTitle') }}</h1>
        <div v-if="d" class="text-[11.5px] text-stone-500 font-mono truncate" dir="ltr">{{ d.name }}</div>
      </div>
    </header>

    <div v-if="loading" class="h-[280px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <!-- queue -->
    <template v-else-if="!name">
      <div v-if="!queue.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-8 text-center text-[13px] text-stone-500">{{ t('souk.photoNone') }}</div>
      <router-link v-for="r in queue" :key="r.name" :to="{ name: 'SoukPhoto', params: { name: r.name } }"
                   class="flex items-center gap-3 bg-white ring-1 rounded-2xl p-3 min-h-[72px] hover:ring-stone-400"
                   :class="r.late ? 'ring-rose-300' : 'ring-stone-200/70'">
        <img v-if="r.image" :src="r.image" class="w-12 h-12 rounded-xl object-cover ring-1 ring-stone-200" alt="" />
        <div v-else class="w-12 h-12 rounded-xl bg-stone-100" />
        <div class="min-w-0 flex-1">
          <div class="text-[13px] font-semibold truncate">{{ r.title }}</div>
          <div class="text-[11.5px] text-stone-500 tabular-nums">
            {{ t('souk.photoProgress').replace('{d}', r.done).replace('{n}', r.required) }} · {{ t('souk.nColors').replace('{n}', r.colors) }}
          </div>
        </div>
        <span v-if="r.hoursLeft != null" class="shrink-0 text-[11px] font-bold tabular-nums" :class="clockClass(r.hoursLeft, 'text')">{{ hoursText(r.hoursLeft) }}</span>
      </router-link>
    </template>

    <template v-else-if="d">
      <div v-if="!d.canEdit" class="bg-stone-50 ring-1 ring-stone-200 rounded-2xl p-4 text-[13px] text-stone-700">
        {{ t('souk.photoNotNow') }}
        <router-link :to="{ name: 'SoukProduct', params: { name: d.name } }" class="font-bold underline">{{ t('souk.toProduct') }}</router-link>
      </div>

      <!-- progress -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
        <div class="flex items-baseline justify-between gap-3 text-[12px] tabular-nums">
          <b class="shrink-0 text-stone-900">{{ t('souk.photoProgress').replace('{d}', doneCount).replace('{n}', requiredCount) }}</b>
          <span class="text-stone-500 text-end leading-snug">{{ t('souk.photoRule') }}</span>
        </div>
        <div class="h-1.5 rounded-full bg-stone-200 overflow-hidden" role="progressbar" :aria-valuenow="doneCount" aria-valuemin="0" :aria-valuemax="requiredCount">
          <div class="h-full rounded-full bg-[var(--accent-600)] transition-all" :style="{ width: (requiredCount ? (doneCount / requiredCount) * 100 : 0) + '%' }" />
        </div>
        <div v-if="d.samples.length" class="text-[11.5px] text-stone-500">
          {{ t('souk.samplesAt') }}
          <span v-for="s in d.samples" :key="s.sku" class="font-mono me-2" dir="ltr">{{ s.sku }}×{{ s.qty }}</span>
        </div>
      </section>

      <!-- colours -->
      <nav v-if="d.colors.length > 1" class="flex gap-1.5 overflow-x-auto pb-1" :aria-label="t('souk.nColors').replace('{n}', d.colors.length)">
        <button v-for="(c, i) in d.colors" :key="c.code" :aria-current="color === c.code ? 'true' : undefined"
                class="shrink-0 h-11 px-3.5 rounded-xl text-[12.5px] font-semibold ring-1 inline-flex items-center justify-center gap-1.5"
                :class="[color === c.code ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white ring-stone-200 text-stone-700', i === 0 ? 'flex-[1.4_1_auto]' : 'flex-[1_1_auto]']"
                @click="color = c.code">
          {{ colorName(c) }}<span v-if="i === 0" class="text-[10.5px] opacity-70">· {{ t('souk.primary') }}</span>
          <span class="tabular-nums text-[11px]" :class="colorDone(c, i) ? (color === c.code ? 'text-emerald-300' : 'text-emerald-700') : 'opacity-70'">{{ colorCount(c, i) }}</span>
        </button>
      </nav>

      <!-- angles -->
      <section class="grid grid-cols-2 gap-2.5">
        <div v-for="s in slotsFor(color)" :key="s" class="space-y-1.5">
          <button v-if="photoAt(color, s)" class="relative block w-full aspect-square rounded-2xl overflow-hidden bg-stone-100 ring-1 ring-emerald-300 disabled:cursor-default"
                  :aria-label="t('souk.ph.retake') + ' · ' + t('souk.slot_' + s)"
                  :disabled="!d.canEdit || !!uploading" @click="shoot(color, s)">
            <img :src="photoAt(color, s).url" class="w-full h-full object-cover" alt="" />
            <span class="absolute top-2 start-2 w-6 h-6 rounded-full bg-emerald-700 text-white flex items-center justify-center"><Icon name="check" :size="13" /></span>
            <span v-if="d.canEdit && uploading !== color + '|' + s" class="absolute bottom-2 end-2 h-7 px-2 rounded-lg bg-white/90 text-stone-800 text-[11px] font-bold inline-flex items-center gap-1">
              <Icon name="camera" :size="12" />{{ t('souk.ph.retake') }}
            </span>
            <span v-if="uploading === color + '|' + s" class="absolute inset-0 bg-white/70 flex items-center justify-center">
              <span class="w-7 h-7 rounded-full border-2 border-stone-300 border-t-stone-700 animate-spin" />
            </span>
          </button>
          <button v-else class="relative w-full aspect-square rounded-2xl bg-white ring-2 ring-stone-200 flex flex-col items-center justify-center gap-1.5 text-stone-600 disabled:opacity-50"
                  :aria-label="t('souk.shoot') + ' · ' + t('souk.slot_' + s)"
                  :disabled="!d.canEdit || !!uploading" @click="shoot(color, s)">
            <span class="absolute inset-2 rounded-xl border-2 border-dashed border-stone-300 pointer-events-none" />
            <Icon v-if="uploading !== color + '|' + s" name="camera" :size="26" />
            <span v-else class="w-6 h-6 rounded-full border-2 border-stone-300 border-t-stone-700 animate-spin" />
            <span class="text-[12px] font-semibold">{{ t('souk.shoot') }}</span>
          </button>
          <div class="px-0.5">
            <div class="text-[12.5px] font-semibold text-stone-900">{{ t('souk.slot_' + s) }}</div>
            <div class="text-[11px] text-stone-500 leading-snug">{{ t('souk.slotHint_' + s) }}</div>
          </div>
        </div>
      </section>
      <p v-if="d.colors.length > 1 && color !== d.colors[0].code" class="text-[11.5px] text-stone-500">{{ t('souk.otherColorRule') }}</p>

      <!-- extras -->
      <section class="space-y-2">
        <div class="text-[12.5px] font-bold">{{ t('souk.extras') }} <span class="font-normal text-stone-500">· {{ t('souk.optional') }}</span></div>
        <div class="flex gap-2 flex-wrap">
          <div v-for="p in extras" :key="p.url" class="relative w-20 h-20 rounded-xl overflow-hidden ring-1 ring-stone-200">
            <img :src="p.url" class="w-full h-full object-cover" alt="" />
            <button v-if="d.canEdit" class="absolute top-0 end-0 w-11 h-11 flex items-start justify-end p-1" :aria-label="t('souk.ph.remove')" @click="remove(p.url)">
              <span class="w-7 h-7 rounded-full bg-white/90 text-rose-700 flex items-center justify-center shadow-sm"><Icon name="x" :size="14" /></span>
            </button>
          </div>
          <button v-if="d.canEdit" class="w-20 h-20 rounded-xl border-2 border-dashed border-stone-300 bg-white text-stone-500 flex flex-col items-center justify-center text-[11px] font-semibold disabled:opacity-50"
                  :disabled="!!uploading" @click="shoot(color, 'extra')">
            <Icon name="plus" :size="18" />{{ t('souk.addPhoto') }}
          </button>
        </div>
      </section>

      <!-- specs -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
        <label class="text-[12.5px] font-bold" for="souk-specs">{{ t('souk.specs') }}</label>
        <div v-if="d.sizes.length" class="text-[11.5px] text-stone-500">{{ t('souk.specsSizes').replace('{s}', d.sizes.join(' · ')) }}</div>
        <textarea id="souk-specs" v-model="specs" rows="3" :disabled="!d.canEdit"
                  class="w-full rounded-xl ring-1 ring-stone-300 p-3 text-[13px]" :placeholder="t('souk.specsHint')" />
      </section>

      <input ref="fileInput" type="file" accept="image/*" capture="environment" class="hidden" @change="onFile" />
    </template>

    <footer v-if="d && d.canEdit && name" class="lp-footer bg-white border-t border-stone-200 px-4 pt-3 pb-4 shadow-[0_-8px_20px_rgba(0,0,0,0.05)]">
      <div class="max-w-[560px] mx-auto space-y-1.5">
        <div v-if="d.missing.length" class="text-[11.5px] text-stone-600 text-center leading-snug">{{ missingText }}</div>
        <button class="w-full h-[50px] rounded-xl bg-[var(--accent-600)] text-white text-[15px] font-bold disabled:bg-stone-200 disabled:text-stone-500"
                :disabled="busy || d.missing.length > 0 || !!uploading" @click="send">
          {{ busy ? t('souk.sending') : t('souk.toMarketing') }}
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
function clockClass(h, kind) {
  const x = Number(h);
  if (x < 0) return kind === "chip" ? "bg-rose-50 text-rose-700 ring-1 ring-rose-200" : "text-rose-600";
  if (x < 6) return kind === "chip" ? "bg-amber-50 text-amber-800" : "text-amber-700";
  return kind === "chip" ? "bg-stone-100 text-stone-700" : "text-stone-500";
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
