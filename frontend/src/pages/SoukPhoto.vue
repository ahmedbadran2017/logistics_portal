<template>
  <!-- In-house photos, on the phone, within 24 h of receiving. The first
       colour needs six angles, every other colour one front shot; a retake
       replaces the old photo. The photos land on the product card itself, so
       marketing never has to ask for them on WhatsApp. The sample pieces sit
       in Studio - JM. Backend: souk.photo_queue / photo_boot / photo_add /
       photo_remove / photos_send. -->
  <div class="max-w-[560px] mx-auto px-4 pt-4 pb-40 space-y-4">
    <header class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="text-[11.5px] font-semibold text-stone-500">{{ t('souk.photoKicker') }}</div>
        <h1 class="text-[18px] font-bold text-stone-900 truncate">{{ d ? d.title : t('souk.photoTitle') }}</h1>
        <div v-if="d" class="text-[11.5px] text-stone-500 font-mono" dir="ltr">{{ d.name }}</div>
      </div>
      <span v-if="d && d.hoursLeft != null" class="shrink-0 h-7 px-2.5 rounded-full text-[11.5px] font-bold inline-flex items-center tabular-nums"
            :class="d.hoursLeft < 0 ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-700'">
        {{ hoursText(d.hoursLeft) }}
      </span>
      <router-link v-else-if="name" :to="{ name: 'SoukPhoto' }" class="shrink-0 h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center">{{ t('souk.recvList') }}</router-link>
    </header>

    <div v-if="loading" class="h-[280px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <!-- queue -->
    <template v-else-if="!name">
      <div v-if="!queue.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-8 text-center text-[13px] text-stone-500">{{ t('souk.photoNone') }}</div>
      <router-link v-for="r in queue" :key="r.name" :to="{ name: 'SoukPhoto', params: { name: r.name } }"
                   class="flex items-center gap-3 bg-white ring-1 rounded-2xl p-3 hover:ring-stone-400"
                   :class="r.late ? 'ring-rose-300' : 'ring-stone-200/70'">
        <img v-if="r.image" :src="r.image" class="w-12 h-12 rounded-xl object-cover ring-1 ring-stone-200" alt="" />
        <div v-else class="w-12 h-12 rounded-xl bg-stone-100" />
        <div class="min-w-0 flex-1">
          <div class="text-[13px] font-semibold truncate">{{ r.title }}</div>
          <div class="text-[11.5px] text-stone-500 tabular-nums">
            {{ t('souk.photoProgress').replace('{d}', r.done).replace('{n}', r.required) }} · {{ t('souk.nColors').replace('{n}', r.colors) }}
          </div>
        </div>
        <span v-if="r.hoursLeft != null" class="text-[11px] font-bold tabular-nums" :class="r.late ? 'text-rose-600' : 'text-stone-500'">{{ hoursText(r.hoursLeft) }}</span>
      </router-link>
    </template>

    <template v-else-if="d">
      <div v-if="!d.canEdit" class="bg-stone-50 ring-1 ring-stone-200 rounded-2xl p-4 text-[13px] text-stone-700">
        {{ t('souk.photoNotNow') }}
        <router-link :to="{ name: 'SoukProduct', params: { name: d.name } }" class="font-bold underline">{{ t('souk.toProduct') }}</router-link>
      </div>

      <!-- progress -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
        <div class="flex items-center justify-between text-[12.5px]">
          <b>{{ t('souk.photoProgress').replace('{d}', doneCount).replace('{n}', requiredCount) }}</b>
          <span class="text-stone-500">{{ t('souk.photoRule') }}</span>
        </div>
        <div class="h-2 rounded-full bg-stone-100 overflow-hidden">
          <div class="h-full bg-emerald-600 transition-all" :style="{ width: (requiredCount ? (doneCount / requiredCount) * 100 : 0) + '%' }" />
        </div>
        <div v-if="d.samples.length" class="text-[11.5px] text-stone-500">
          {{ t('souk.samplesAt') }}
          <span v-for="s in d.samples" :key="s.sku" class="font-mono me-2" dir="ltr">{{ s.sku }}×{{ s.qty }}</span>
        </div>
      </section>

      <!-- colours -->
      <div v-if="d.colors.length > 1" class="flex gap-2 overflow-x-auto pb-1">
        <button v-for="(c, i) in d.colors" :key="c.code"
                class="shrink-0 h-10 px-3.5 rounded-xl text-[12.5px] font-bold ring-1 inline-flex items-center gap-1.5"
                :class="color === c.code ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white ring-stone-300 text-stone-800'"
                @click="color = c.code">
          {{ colorName(c) }}<span v-if="i === 0" class="text-[10.5px] opacity-70">· {{ t('souk.primary') }}</span>
          <span class="tabular-nums text-[11px]" :class="colorDone(c, i) ? 'text-emerald-400' : 'opacity-70'">{{ colorCount(c, i) }}</span>
        </button>
      </div>

      <!-- angles -->
      <section class="grid grid-cols-2 gap-2.5">
        <div v-for="s in slotsFor(color)" :key="s" class="bg-white ring-1 rounded-2xl overflow-hidden"
             :class="photoAt(color, s) ? 'ring-emerald-300' : 'ring-stone-200'">
          <button v-if="photoAt(color, s)" class="block w-full aspect-square bg-stone-100" @click="shoot(color, s)" :disabled="!d.canEdit || !!uploading">
            <img :src="photoAt(color, s).url" class="w-full h-full object-cover" alt="" />
          </button>
          <button v-else class="w-full aspect-square bg-stone-50 flex flex-col items-center justify-center gap-1.5 text-stone-500 disabled:opacity-50"
                  :disabled="!d.canEdit || !!uploading" @click="shoot(color, s)">
            <Icon v-if="uploading !== color + '|' + s" name="camera" :size="26" />
            <span v-else class="w-6 h-6 rounded-full border-2 border-stone-300 border-t-stone-700 animate-spin" />
            <span class="text-[11.5px] font-semibold">{{ t('souk.shoot') }}</span>
          </button>
          <div class="px-2.5 py-2">
            <div class="text-[12.5px] font-bold text-stone-900 flex items-center gap-1">
              <Icon v-if="photoAt(color, s)" name="check" :size="13" class="text-emerald-600" />{{ t('souk.slot_' + s) }}
            </div>
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
            <button v-if="d.canEdit" class="absolute top-1 end-1 w-6 h-6 rounded-full bg-white/90 text-rose-700 text-[13px] font-bold" @click="remove(p.url)">×</button>
          </div>
          <button v-if="d.canEdit" class="w-20 h-20 rounded-xl ring-1 ring-dashed ring-stone-300 bg-white text-stone-500 flex flex-col items-center justify-center text-[11px] font-semibold disabled:opacity-50"
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

    <footer v-if="d && d.canEdit" class="fixed inset-x-0 bottom-0 bg-white border-t border-stone-200 px-4 pt-3 pb-5 z-20">
      <div class="max-w-[560px] mx-auto space-y-2">
        <div v-if="d.missing.length" class="text-[12px] text-amber-800">{{ missingText }}</div>
        <button class="w-full h-12 rounded-xl bg-emerald-600 text-white text-[14px] font-bold disabled:opacity-40"
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

const { t, locale } = useI18n();
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
function hoursText(h) {
  if (h < 0) return t("souk.lateBy").replace("{n}", Math.ceil(-h));
  return t("souk.hoursLeft").replace("{n}", Math.floor(h));
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
