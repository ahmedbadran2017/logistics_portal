<template>
  <!-- Marketing's queue: the final photos. The in-house photos and the specs
       come from the floor and the buy; marketing uploads the finals, puts
       them in order (the first is the main photo) and ties each to a colour.
       Handing to content puts them on the Shopify Draft; each colour's first
       final becomes its variants' image. The sample pieces are in
       Studio - JM. Backend: souk.studio_boot / final_add / final_set /
       photo_remove / studio_return / studio_send / raw_zip. -->
  <div class="px-4 py-5 space-y-4">
    <header>
      <h1 class="text-[20px] font-bold text-stone-900">{{ t('souk.studioTitle') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[680px]">{{ t('souk.studioIntro') }}</p>
    </header>

    <div v-if="loading && !data" class="h-[420px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <div v-else-if="data" class="grid grid-cols-1 lg:grid-cols-[290px_1fr] gap-4 items-start">
      <!-- queue -->
      <aside class="bg-white ring-1 ring-stone-200/70 rounded-2xl overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex justify-between text-[12px]">
          <b>{{ t('souk.nProducts').replace('{n}', data.queue.length) }}</b>
          <span class="text-stone-500">{{ t('souk.oldestFirst') }}</span>
        </div>
        <div v-if="!data.queue.length" class="p-6 text-center text-[12.5px] text-stone-500">{{ t('souk.studioNone') }}</div>
        <router-link v-for="q in data.queue" :key="q.name" :to="{ name: 'SoukStudio', params: { name: q.name } }"
                     class="flex items-center gap-2.5 px-3 py-2.5 border-b border-stone-100 last:border-0"
                     :class="d && d.name === q.name ? 'bg-[var(--accent-50)]' : 'hover:bg-stone-50'">
          <img v-if="q.image" :src="q.image" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-10 h-10 rounded-lg bg-stone-100" />
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-semibold truncate">{{ q.title }}</div>
            <div class="text-[11px] text-stone-500">{{ t('souk.nColors').replace('{n}', q.colors) }} · {{ t('souk.nRaw').replace('{n}', q.raw) }}</div>
          </div>
          <span class="text-[10.5px] font-bold rounded-full px-2 py-0.5 tabular-nums"
                :class="q.late ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-600'">{{ t('souk.ageDays').replace('{n}', q.age) }}</span>
        </router-link>
      </aside>

      <!-- product -->
      <div v-if="!d" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-8 text-center text-[13px] text-stone-500">{{ t('souk.studioPick') }}</div>
      <div v-else class="space-y-4">
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 flex items-start justify-between gap-3 flex-wrap">
          <div class="min-w-0">
            <h2 class="text-[17px] font-bold truncate">{{ d.title }}</h2>
            <div class="text-[11.5px] text-stone-500 font-mono" dir="ltr">{{ d.name }} · {{ d.brand }} · {{ d.colors.length }} × {{ sizes.length || 1 }}</div>
          </div>
          <div class="text-end space-y-1">
            <div v-if="d.hoursLeft != null" class="text-[11.5px] font-bold" :class="d.hoursLeft < 0 ? 'text-rose-600' : 'text-stone-600'">
              {{ d.hoursLeft < 0 ? t('souk.lateBy').replace('{n}', Math.ceil(-d.hoursLeft)) : t('souk.hoursLeft').replace('{n}', Math.floor(d.hoursLeft)) }}
            </div>
            <div v-if="d.samples.length" class="text-[11px] text-stone-500">
              {{ t('souk.samplesAt') }} <span v-for="s in d.samples" :key="s.sku" class="font-mono ms-1" dir="ltr">{{ s.sku }}×{{ s.qty }}</span>
            </div>
            <router-link :to="{ name: 'SoukProduct', params: { name: d.name } }" class="text-[11.5px] font-semibold underline">{{ t('souk.toProduct') }}</router-link>
          </div>
        </section>

        <div v-if="d.error" class="bg-rose-50 ring-1 ring-rose-200 rounded-xl p-3 text-[12px] text-rose-800 break-words">{{ d.error }}</div>
        <div v-if="!d.canEdit" class="bg-stone-50 ring-1 ring-stone-200 rounded-xl p-3 text-[12.5px] text-stone-700">{{ t('souk.studioNotNow') }}</div>

        <!-- raw -->
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="text-[12.5px] font-bold">{{ t('souk.rawPhotos') }} · {{ d.photos.length }}</h3>
            <a v-if="d.photos.length" :href="zipUrl" class="h-8 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12px] font-semibold inline-flex items-center gap-1.5">
              <Icon name="download" :size="14" />{{ t('souk.downloadAll') }}
            </a>
          </div>
          <div v-for="c in d.colors" :key="c.code" class="space-y-1.5">
            <div class="text-[11.5px] font-semibold text-stone-600">{{ colorName(c) }} · {{ rawOf(c.code).length }}</div>
            <div class="flex gap-2 flex-wrap">
              <a v-for="p in rawOf(c.code)" :key="p.url" :href="p.url" target="_blank" rel="noopener"
                 class="block w-[86px] h-[86px] rounded-lg overflow-hidden ring-1 ring-stone-200" :title="t('souk.slot_' + p.slot)">
                <img :src="p.url" class="w-full h-full object-cover" alt="" loading="lazy" />
              </a>
            </div>
          </div>
          <div class="text-[12px] text-stone-600 leading-relaxed border-t border-stone-100 pt-2.5 space-y-0.5">
            <div v-if="sizes.length"><b>{{ t('souk.sizesLbl') }}</b> {{ sizes.join(' · ') }}</div>
            <div v-if="d.specs"><b>{{ t('souk.specs') }}:</b> {{ d.specs }}</div>
            <div v-if="weights"><b>{{ t('souk.weightLbl') }}</b> <span dir="ltr">{{ weights }}</span></div>
          </div>
        </section>

        <!-- finals -->
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
          <div class="flex items-center justify-between gap-2 flex-wrap">
            <div>
              <h3 class="text-[12.5px] font-bold">{{ t('souk.finals') }}</h3>
              <div class="text-[11.5px] text-stone-500">{{ t('souk.finalsHint') }}</div>
            </div>
            <label v-if="d.canEdit" class="h-9 px-3 rounded-lg bg-stone-900 text-white text-[12.5px] font-bold inline-flex items-center gap-1.5 cursor-pointer"
                   :class="uploading ? 'opacity-50 pointer-events-none' : ''">
              <Icon name="plus" :size="14" />{{ uploading ? t('souk.uploadingN').replace('{n}', uploading) : t('souk.uploadFinals') }}
              <input type="file" accept="image/*" multiple class="hidden" @change="onFiles" />
            </label>
          </div>
          <div v-if="!d.finals.length" class="text-center text-[12px] text-stone-400 py-6">{{ t('souk.noFinals') }}</div>
          <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-3">
            <div v-for="(f, i) in d.finals" :key="f.url" class="ring-1 ring-stone-200 rounded-xl overflow-hidden">
              <div class="relative aspect-square bg-stone-100">
                <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                <span class="absolute top-1.5 start-1.5 text-[10.5px] font-bold rounded-full px-2 py-0.5"
                      :class="i === 0 ? 'bg-[var(--accent-600)] text-white' : 'bg-white/90 text-stone-700'">{{ i === 0 ? t('souk.mainPhoto') : i + 1 }}</span>
              </div>
              <div class="p-2 space-y-1.5">
                <select v-if="d.colors.length > 1" :value="f.color" :disabled="!d.canEdit || busy"
                        class="w-full h-8 rounded-lg ring-1 ring-stone-300 text-[12px] px-2 bg-white" @change="setColor(i, $event.target.value)">
                  <option value="">{{ t('souk.allColors') }}</option>
                  <option v-for="c in d.colors" :key="c.code" :value="c.code">{{ colorName(c) }}</option>
                </select>
                <div v-if="d.canEdit" class="flex items-center gap-1">
                  <button class="w-8 h-8 rounded-lg ring-1 ring-stone-200 inline-flex items-center justify-center disabled:opacity-30" :disabled="i === 0 || busy" @click="move(i, -1)" :title="t('souk.moveUp')"><Icon name="arrow-up" :size="14" /></button>
                  <button class="w-8 h-8 rounded-lg ring-1 ring-stone-200 inline-flex items-center justify-center disabled:opacity-30" :disabled="i === d.finals.length - 1 || busy" @click="move(i, 1)" :title="t('souk.moveDown')"><Icon name="arrow-down" :size="14" /></button>
                  <button class="ms-auto h-8 px-2 rounded-lg text-[11.5px] font-semibold text-rose-700 hover:bg-rose-50" :disabled="busy" @click="removeFinal(f.url)">{{ t('souk.remove') }}</button>
                </div>
              </div>
            </div>
          </div>
          <div v-if="d.colorsWithout.length && d.finals.length" class="bg-amber-50 ring-1 ring-amber-200 rounded-xl p-3 text-[12px] text-amber-900">
            {{ t('souk.colorNeedsFinal').replace('{list}', d.colorsWithout.map(colorOf).join(' · ')) }}
          </div>
        </section>

        <!-- actions -->
        <section v-if="d.canEdit" class="space-y-2">
          <div v-if="returning" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
            <label class="text-[12.5px] font-bold" for="souk-return">{{ t('souk.returnWhy') }}</label>
            <textarea id="souk-return" v-model="reason" rows="2" class="w-full rounded-xl ring-1 ring-stone-300 p-3 text-[13px]" :placeholder="t('souk.returnHint')" />
            <div class="flex gap-2">
              <button class="h-10 px-4 rounded-xl bg-amber-600 text-white text-[13px] font-bold disabled:opacity-40" :disabled="busy || !reason.trim()" @click="sendBack">{{ t('souk.returnConfirm') }}</button>
              <button class="h-10 px-4 rounded-xl bg-white ring-1 ring-stone-300 text-[13px] font-semibold" @click="returning = false">{{ t('souk.cancel') }}</button>
            </div>
          </div>
          <div class="flex gap-2 flex-wrap">
            <button class="h-11 px-5 rounded-xl bg-emerald-600 text-white text-[13.5px] font-bold disabled:opacity-40"
                    :disabled="busy || !!uploading || !d.finals.length || d.colorsWithout.length > 0" @click="send">
              {{ busy ? t('souk.sending') : t('souk.toContent') }}
            </button>
            <button v-if="!returning" class="h-11 px-4 rounded-xl bg-white ring-1 ring-stone-300 text-[13px] font-semibold" @click="returning = true">{{ t('souk.returnToFloor') }}</button>
          </div>
          <p class="text-[11.5px] text-stone-500">{{ t('souk.toContentNote') }}</p>
        </section>
      </div>
    </div>
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
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const uploading = ref(0);
const returning = ref(false);
const reason = ref("");
const d = computed(() => data.value?.detail || null);

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
const zipUrl = computed(() => "/api/method/logistics_portal.api.souk.raw_zip?name=" + encodeURIComponent(d.value?.name || ""));

async function load() {
  loading.value = true;
  returning.value = false;
  reason.value = "";
  try {
    data.value = await api("souk.studio_boot", route.params.name ? { name: route.params.name } : {});
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

function setDetail(det) {
  data.value = { ...data.value, detail: det };
}

async function onFiles(e) {
  const files = [...(e.target.files || [])];
  e.target.value = "";
  for (let i = 0; i < files.length; i++) {
    uploading.value = files.length - i;
    try {
      setDetail(await postPhoto("final_add", { name: d.value.name, color: "" }, files[i], { max: 2048, quality: 0.9 }));
    } catch (err) {
      warn(t("souk.failed"), String(err.message || err));
      break;
    }
  }
  uploading.value = 0;
}

async function save(list) {
  busy.value = true;
  try {
    setDetail(await apiPost("souk.final_set", {
      name: d.value.name, finals: JSON.stringify(list.map((f) => ({ url: f.url, color: f.color || "" }))),
    }));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load();
  } finally {
    busy.value = false;
  }
}
function setColor(i, code) {
  const list = d.value.finals.map((f, j) => (j === i ? { ...f, color: code } : f));
  save(list);
}
function move(i, step) {
  const list = [...d.value.finals];
  const [x] = list.splice(i, 1);
  list.splice(i + step, 0, x);
  save(list);
}
async function removeFinal(url) {
  busy.value = true;
  try {
    await apiPost("souk.photo_remove", { name: d.value.name, url, which: "final" });
    await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

async function send() {
  busy.value = true;
  try {
    const r = await apiPost("souk.studio_send", { name: d.value.name });
    success(t("souk.sentToContent").replace("{n}", r.media));
    router.push({ name: "SoukStudio" });
    await load();
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
    router.push({ name: "SoukStudio" });
    await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

watch(() => route.params.name, load);
onMounted(load);
</script>
