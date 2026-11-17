<template>
  <!-- Review & publish (1 day, never by the writer). The system checks what
       it can measure — a photo per colour, price above the cost with
       transport, weights, Shopify's quantity = what ee pushes from Next,
       vendor = house brand, French colour names; the reviewer ticks what only
       an eye sees. Send back to the step that owns the problem (counted), drop
       it, or publish: channels → ACTIVE → studio samples back on the shelf.
       Backend: souk.review_boot / review_reject / review_drop / publish /
       qty_nudge. -->
  <div class="px-4 py-5 space-y-4">
    <header>
      <h1 class="text-[20px] font-bold text-stone-900">{{ t('souk.reviewTitle') }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[680px]">{{ t('souk.reviewIntro') }}</p>
    </header>

    <div v-if="loading && !data" class="h-[420px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <div v-else-if="data" class="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4 items-start">
      <aside class="bg-white ring-1 ring-stone-200/70 rounded-2xl overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex justify-between text-[12px]">
          <b>{{ t('souk.nProducts').replace('{n}', data.queue.length) }}</b>
          <span class="text-stone-500">{{ t('souk.oldestFirst') }}</span>
        </div>
        <div v-if="!data.queue.length" class="p-6 text-center text-[12.5px] text-stone-500">{{ t('souk.reviewNone') }}</div>
        <router-link v-for="q in data.queue" :key="q.name" :to="{ name: 'SoukReview', params: { name: q.name } }"
                     class="flex items-center gap-2.5 px-3 py-2.5 border-b border-stone-100 last:border-0"
                     :class="d && d.name === q.name ? 'bg-[#fdf5f3]' : 'hover:bg-stone-50'">
          <img v-if="q.image" :src="q.image" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-10 h-10 rounded-lg bg-stone-100" />
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-semibold truncate">{{ q.title }}</div>
            <div class="text-[11px]" :class="q.mine ? 'text-amber-700' : 'text-stone-500'">{{ q.mine ? t('souk.youWroteIt') : t('souk.writtenBy').replace('{n}', q.writer) }}</div>
          </div>
          <span class="text-[10.5px] font-bold rounded-full px-2 py-0.5 tabular-nums"
                :class="q.late ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-600'">{{ t('souk.ageDays').replace('{n}', q.age) }}</span>
        </router-link>
      </aside>

      <div v-if="!d" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-8 text-center text-[13px] text-stone-500">{{ t('souk.studioPick') }}</div>
      <div v-else class="space-y-4">
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 flex items-start justify-between gap-3 flex-wrap">
          <div class="min-w-0">
            <h2 class="text-[17px] font-bold truncate">{{ d.content.fr.title || d.title }}</h2>
            <div class="text-[11.5px] text-stone-500">
              {{ t('souk.writtenBy').replace('{n}', d.writer || '—') }}<span v-if="d.rejects"> · {{ t('souk.returnedN').replace('{n}', d.rejects) }}</span>
            </div>
          </div>
          <div class="flex gap-2 flex-wrap">
            <a v-if="d.shopify.preview" :href="d.shopify.preview" target="_blank" rel="noopener" class="h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center">{{ t('souk.previewSite') }}</a>
            <a v-if="d.shopifyAdmin" :href="d.shopifyAdmin" target="_blank" rel="noopener" class="h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center">Shopify</a>
          </div>
        </section>

        <div v-if="d.sameWriter" class="bg-amber-50 ring-1 ring-amber-200 rounded-xl p-3 text-[12.5px] text-amber-900">{{ t('souk.sameWriter') }}</div>
        <div v-if="d.stage !== 'review'" class="bg-stone-50 ring-1 ring-stone-200 rounded-xl p-3 text-[12.5px] text-stone-700">{{ t('souk.reviewNotNow') }}</div>

        <div class="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-4 items-start">
          <!-- preview -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex gap-1.5">
                <button v-for="l in ['fr', 'ar']" :key="l" class="h-8 px-3 rounded-lg text-[12px] font-bold"
                        :class="lang === l ? 'bg-stone-900 text-white' : 'bg-stone-100 text-stone-700'" @click="lang = l">
                  {{ l === 'fr' ? t('souk.langFr') : t('souk.langAr') }}
                </button>
              </div>
              <span class="text-[10.5px] font-bold rounded-full px-2 py-0.5 bg-stone-900 text-white">{{ d.shopify.status || 'DRAFT' }}</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4" :dir="lang === 'ar' ? 'rtl' : 'ltr'">
              <div class="space-y-2">
                <img v-if="mainImg" :src="mainImg" class="w-full aspect-square object-cover rounded-xl ring-1 ring-stone-200" alt="" />
                <div class="flex gap-1.5 flex-wrap">
                  <button v-for="f in d.finals" :key="f.url" class="w-12 h-12 rounded-lg overflow-hidden ring-1"
                          :class="mainImg === f.url ? 'ring-stone-900' : 'ring-stone-200'" @click="img = f.url">
                    <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                  </button>
                </div>
              </div>
              <div class="space-y-3">
                <h3 class="text-[18px] font-bold leading-snug">{{ d.content[lang].title || '—' }}</h3>
                <div class="text-[16px] font-extrabold tabular-nums">{{ priceLine }}</div>
                <div v-if="d.colors.length > 1" class="flex gap-1.5 flex-wrap">
                  <span v-for="c in d.colors" :key="c.code" class="h-8 px-3 rounded-lg ring-1 ring-stone-300 text-[12px] inline-flex items-center">{{ c.fr }}</span>
                </div>
                <div v-if="sizeRows.length > 1" class="flex gap-1.5 flex-wrap">
                  <span v-for="s in sizeRows" :key="s.size" class="h-8 px-3 rounded-lg ring-1 ring-stone-300 text-[12px] inline-flex items-center tabular-nums">{{ s.size }} · {{ s.price }} MAD</span>
                </div>
                <!-- Built server-side from plain text with every character escaped. -->
                <div class="souk-desc text-[13px] leading-relaxed text-stone-700" v-html="d.descHtml[lang]" />
              </div>
            </div>
            <div class="border-t border-stone-100 pt-3 text-[12px] text-stone-600 space-y-0.5" dir="ltr">
              <div class="text-[12px] text-stone-500 truncate">justyol.com › products › {{ d.content.handle }}</div>
              <div class="text-[15px] text-[#1a0dab] truncate">{{ d.content.metaTitle }}</div>
              <div class="line-clamp-2">{{ d.content.metaDescription }}</div>
            </div>
          </section>

          <aside class="space-y-4">
            <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-1.5">
              <div class="flex items-center justify-between">
                <h3 class="text-[12.5px] font-bold">{{ t('souk.systemChecks') }}</h3>
                <button class="text-[11.5px] font-semibold underline" :disabled="loading" @click="load">{{ t('souk.recheck') }}</button>
              </div>
              <div v-for="k in d.checks" :key="k.key" class="flex items-start gap-2 text-[12.5px]">
                <span class="w-5 h-5 shrink-0 rounded-full text-[11px] font-bold inline-flex items-center justify-center"
                      :class="k.ok ? 'bg-emerald-100 text-emerald-700' : k.hard ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-800'">{{ k.ok ? '✓' : k.hard ? '✗' : '!' }}</span>
                <div class="min-w-0 flex-1">
                  <div :class="k.ok ? 'text-stone-800' : k.hard ? 'text-rose-800' : 'text-amber-900'">{{ t('souk.rk_' + k.key) }}</div>
                  <div v-if="k.detail" class="text-[11px] text-stone-500 break-words" dir="ltr">{{ k.detail }}</div>
                  <button v-if="k.key === 'qty' && !k.ok" class="mt-1 text-[11.5px] font-semibold underline" :disabled="busy" @click="nudge">{{ t('souk.qtyNudge') }}</button>
                </div>
              </div>
            </section>

            <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
              <h3 class="text-[12.5px] font-bold">{{ t('souk.eyeChecks') }}</h3>
              <label v-for="m in d.manual" :key="m" class="flex items-start gap-2 text-[12.5px] cursor-pointer">
                <input v-model="ticked" type="checkbox" :value="m" class="mt-0.5 w-4 h-4" :disabled="!d.canPublish" />
                <span>{{ t('souk.mk_' + m) }}</span>
              </label>
            </section>

            <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
              <div class="flex items-center justify-between">
                <h3 class="text-[12.5px] font-bold">{{ t('souk.channels') }}</h3>
                <span class="text-[11px] text-stone-500">{{ t('souk.channelsDefault') }}</span>
              </div>
              <div v-if="d.channelsError" class="text-[11.5px] text-rose-700 break-words">{{ d.channelsError }}</div>
              <label v-for="ch in d.channels" :key="ch.id" class="flex items-center gap-2 text-[12.5px] cursor-pointer">
                <input v-model="chosen" type="checkbox" :value="ch.id" class="w-4 h-4" :disabled="!d.canPublish" />
                <span>{{ ch.name }}</span>
              </label>
            </section>

            <div v-if="d.samples.length" class="bg-stone-50 ring-1 ring-stone-200 rounded-xl p-3 text-[12px] text-stone-700">
              {{ t('souk.samplesBack').replace('{n}', d.samples.reduce((s, x) => s + x.qty, 0)) }}
            </div>

            <button v-if="d.stage === 'review'" class="w-full h-12 rounded-xl bg-[#c4301c] text-white text-[14px] font-bold disabled:opacity-40"
                    :disabled="busy || !canPublish" @click="publish">
              {{ busy ? t('souk.sending') : t('souk.publish') }}
            </button>
            <p v-if="d.stage === 'review' && !canPublish" class="text-[11.5px] text-stone-500">{{ blockedWhy }}</p>

            <!-- something wrong -->
            <section v-if="d.stage === 'review' && !d.sameWriter" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
              <h3 class="text-[12.5px] font-bold">{{ t('souk.somethingWrong') }}</h3>
              <select v-model="back" class="w-full h-10 rounded-xl ring-1 ring-stone-300 px-2 text-[12.5px] bg-white">
                <option value="content">{{ t('souk.backContent') }}</option>
                <option value="studio">{{ t('souk.backStudio') }}</option>
                <option value="photos">{{ t('souk.backPhotos') }}</option>
                <option value="drop:return">{{ t('souk.dropReturn') }}</option>
                <option value="drop:clearance">{{ t('souk.dropClearance') }}</option>
              </select>
              <textarea v-model="note" rows="2" class="w-full rounded-xl ring-1 ring-stone-300 p-3 text-[12.5px]" :placeholder="t('souk.noteRequired')" />
              <button class="w-full h-10 rounded-xl bg-amber-600 text-white text-[13px] font-bold disabled:opacity-40" :disabled="busy || !note.trim()" @click="sendBack">
                {{ back.startsWith('drop') ? t('souk.dropIt') : t('souk.returnConfirm') }}
              </button>
            </section>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const route = useRoute();
const router = useRouter();
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const lang = ref("fr");
const img = ref("");
const ticked = ref([]);
const chosen = ref([]);
const back = ref("content");
const note = ref("");
const d = computed(() => data.value?.detail || null);

const mainImg = computed(() => img.value || d.value?.finals?.[0]?.url || d.value?.image || "");
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
  if (!ps.length) return "—";
  const lo = Math.min(...ps);
  return (ps.some((p) => p !== lo) ? "à partir de " : "") + lo + " MAD";
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

async function load() {
  loading.value = true;
  try {
    data.value = await api("souk.review_boot", route.params.name ? { name: route.params.name } : {});
    ticked.value = [];
    img.value = "";
    note.value = "";
    back.value = "content";
    chosen.value = [...(data.value.detail?.chosen || [])];
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
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

async function publish() {
  busy.value = true;
  try {
    const r = await apiPost("souk.publish", {
      name: d.value.name, channels: JSON.stringify(chosen.value), manual: JSON.stringify(ticked.value),
    });
    success(t("souk.published").replace("{c}", r.channels).replace("{s}", r.samples));
    router.push({ name: "SoukProduct", params: { name: d.value.name } });
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
    if (back.value.startsWith("drop:")) {
      await apiPost("souk.review_drop", { name: d.value.name, why: back.value.slice(5), note: note.value });
      success(t("souk.dropped"));
    } else {
      await apiPost("souk.review_reject", { name: d.value.name, to: back.value, note: note.value });
      success(t("souk.sentBack"));
    }
    router.push({ name: "SoukReview" });
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

<style scoped>
.souk-desc :deep(p) { margin: 0 0 0.5rem; }
.souk-desc :deep(ul) { list-style: disc; padding-inline-start: 1.25rem; margin: 0 0 0.5rem; }
</style>
