<template>
  <!-- Content queue (2 days): French first (the storefront's main language),
       Arabic as the shop's translation, product type, collections, tags, the
       final price per size and SEO. The buy's and the floor's specs come
       ready. "Send to review" writes it onto the Shopify Draft. Backend:
       souk.content_boot / content_save / content_send. -->
  <div class="px-4 py-5 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900">{{ t('souk.contentTitle') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5 max-w-[680px]">{{ t('souk.contentIntro') }}</p>
      </div>
    </header>

    <div v-if="loading && !data" class="h-[420px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <div v-else-if="data" class="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4 items-start">
      <aside class="bg-white ring-1 ring-stone-200/70 rounded-2xl overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex justify-between text-[12px]">
          <b>{{ t('souk.nProducts').replace('{n}', data.queue.length) }}</b>
          <span class="text-stone-500">{{ t('souk.oldestFirst') }}</span>
        </div>
        <div v-if="!data.queue.length" class="p-6 text-center text-[12.5px] text-stone-500">{{ t('souk.contentNone') }}</div>
        <router-link v-for="q in data.queue" :key="q.name" :to="{ name: 'SoukContent', params: { name: q.name } }"
                     class="flex items-center gap-2.5 px-3 py-2.5 border-b border-stone-100 last:border-0"
                     :class="d && d.name === q.name ? 'bg-[#fdf5f3]' : 'hover:bg-stone-50'">
          <img v-if="q.image" :src="q.image" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-10 h-10 rounded-lg bg-stone-100" />
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-semibold truncate">{{ q.title }}</div>
            <div v-if="q.rejects" class="text-[11px] text-amber-700">{{ t('souk.returnedN').replace('{n}', q.rejects) }}</div>
          </div>
          <span class="text-[10.5px] font-bold rounded-full px-2 py-0.5 tabular-nums"
                :class="q.late ? 'bg-rose-50 text-rose-700' : 'bg-stone-100 text-stone-600'">{{ t('souk.ageDays').replace('{n}', q.age) }}</span>
        </router-link>
      </aside>

      <div v-if="!d" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-8 text-center text-[13px] text-stone-500">{{ t('souk.studioPick') }}</div>
      <div v-else class="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-4 items-start">
        <div class="space-y-4">
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 flex items-start justify-between gap-3 flex-wrap">
            <div class="min-w-0">
              <h2 class="text-[17px] font-bold truncate">{{ c.fr.title || d.title }}</h2>
              <div class="text-[11.5px] text-stone-500 font-mono" dir="ltr">{{ d.name }} · {{ d.brand }}</div>
            </div>
            <div class="flex gap-2 items-center">
              <span v-if="d.hoursLeft != null" class="text-[11.5px] font-bold" :class="d.hoursLeft < 0 ? 'text-rose-600' : 'text-stone-600'">
                {{ d.hoursLeft < 0 ? t('souk.lateBy').replace('{n}', Math.ceil(-d.hoursLeft)) : t('souk.hoursLeft').replace('{n}', Math.floor(d.hoursLeft)) }}
              </span>
              <button v-if="d.canEdit" class="h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold" @click="draft">{{ t('souk.draftFromSpecs') }}</button>
            </div>
          </section>

          <div v-if="d.reviewNote" class="bg-amber-50 ring-1 ring-amber-200 rounded-xl p-3 text-[12.5px] text-amber-900">
            <b>{{ t('souk.reviewSaid').replace('{n}', d.rejects) }}</b> {{ d.reviewNote }}
          </div>
          <div v-if="!d.canEdit" class="bg-stone-50 ring-1 ring-stone-200 rounded-xl p-3 text-[12.5px] text-stone-700">{{ t('souk.contentNotNow') }}</div>

          <!-- texts -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
            <div class="flex gap-1.5">
              <button v-for="l in ['fr', 'ar']" :key="l" class="h-8 px-3 rounded-lg text-[12px] font-bold"
                      :class="lang === l ? 'bg-stone-900 text-white' : 'bg-stone-100 text-stone-700'" @click="lang = l">
                {{ l === 'fr' ? t('souk.langFr') : t('souk.langAr') }}
              </button>
            </div>
            <div :dir="lang === 'ar' ? 'rtl' : 'ltr'" class="space-y-3">
              <div class="space-y-1">
                <div class="flex justify-between text-[12px]"><label class="font-semibold" for="c-title">Titre</label>
                  <span class="tabular-nums" :class="c[lang].title.length > 70 ? 'text-rose-600' : 'text-stone-400'">{{ c[lang].title.length }} / 70</span></div>
                <input id="c-title" v-model="c[lang].title" :disabled="!d.canEdit" class="w-full h-10 rounded-xl ring-1 ring-stone-300 px-3 text-[13.5px]" @input="dirty = true" />
              </div>
              <div class="space-y-1">
                <label class="text-[12px] font-semibold" for="c-desc">Description</label>
                <textarea id="c-desc" v-model="c[lang].description" :disabled="!d.canEdit" rows="9"
                          class="w-full rounded-xl ring-1 ring-stone-300 p-3 text-[13px] leading-relaxed" @input="dirty = true" />
                <div class="text-[11px] text-stone-400">{{ t('souk.descHint') }}</div>
              </div>
            </div>
          </section>

          <!-- catalogue -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="space-y-1">
              <label class="text-[12px] font-semibold" for="c-type">{{ t('souk.productType') }}</label>
              <input id="c-type" v-model="c.productType" :disabled="!d.canEdit" class="w-full h-10 rounded-xl ring-1 ring-stone-300 px-3 text-[13px]" @input="dirty = true" />
            </div>
            <div class="space-y-1">
              <label class="text-[12px] font-semibold" for="c-tags">Tags</label>
              <input id="c-tags" v-model="tagsText" :disabled="!d.canEdit" class="w-full h-10 rounded-xl ring-1 ring-stone-300 px-3 text-[13px]" :placeholder="t('souk.tagsHint')" @input="dirty = true" />
            </div>
            <div class="md:col-span-2 space-y-1.5">
              <div class="text-[12px] font-semibold">{{ t('souk.collections') }}</div>
              <div v-if="d.collectionsError" class="text-[11.5px] text-rose-700">{{ d.collectionsError }}</div>
              <div class="flex gap-1.5 flex-wrap">
                <span v-for="id in c.collections" :key="id" class="h-7 ps-2.5 pe-1 rounded-full bg-stone-100 text-[12px] inline-flex items-center gap-1">
                  {{ colTitle(id) }}
                  <button v-if="d.canEdit" class="w-5 h-5 rounded-full hover:bg-stone-200 text-[12px]" @click="dropCol(id)">×</button>
                </span>
              </div>
              <div v-if="d.canEdit" class="relative">
                <input v-model="colQuery" class="w-full h-9 rounded-xl ring-1 ring-stone-300 px-3 text-[12.5px]" :placeholder="t('souk.collectionSearch')" />
                <div v-if="colQuery.trim()" class="absolute z-10 mt-1 w-full max-h-[240px] overflow-auto bg-white ring-1 ring-stone-200 rounded-xl shadow-lg">
                  <button v-for="x in colHits" :key="x.id" class="block w-full text-start px-3 py-2 text-[12.5px] hover:bg-stone-50" @click="addCol(x.id)">{{ x.title }}</button>
                  <div v-if="!colHits.length" class="px-3 py-2 text-[12px] text-stone-400">—</div>
                </div>
              </div>
            </div>
          </section>

          <!-- prices -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
            <div class="text-[12.5px] font-bold">{{ t('souk.finalPrice') }}</div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div v-for="g in groups" :key="g.key" class="ring-1 ring-stone-200 rounded-xl p-3 space-y-1.5">
                <div class="flex justify-between text-[12px]">
                  <b>{{ g.key || t('souk.theProduct') }}</b>
                  <span class="text-stone-500 tabular-nums">{{ t('souk.landedCost') }} {{ fmt2(g.landed) }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <input type="number" inputmode="decimal" :value="priceOf(g)" :disabled="!d.canEdit"
                         class="w-[120px] h-10 rounded-xl ring-1 ring-stone-300 px-3 text-[15px] font-bold tabular-nums" @input="setPrice(g, $event.target.value)" />
                  <span class="text-[12px] text-stone-500">MAD</span>
                  <span class="ms-auto text-[12px] font-bold tabular-nums" :class="marginOf(g) <= 0 ? 'text-rose-600' : 'text-emerald-700'">{{ t('souk.marginPct').replace('{n}', marginOf(g)) }}</span>
                </div>
                <div v-if="!g.allocated" class="text-[11px] text-amber-700">{{ t('souk.transportNotYet') }}</div>
              </div>
            </div>
          </section>

          <!-- SEO -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
            <div class="text-[12.5px] font-bold">{{ t('souk.seoTitle') }}</div>
            <div class="rounded-xl ring-1 ring-stone-200 p-3 space-y-0.5" dir="ltr">
              <div class="text-[12px] text-stone-500 truncate">justyol.com › products › {{ c.handle || '…' }}</div>
              <div class="text-[16px] text-[#1a0dab] truncate">{{ c.metaTitle || c.fr.title || '—' }}</div>
              <div class="text-[12.5px] text-stone-600 line-clamp-2">{{ c.metaDescription || '—' }}</div>
            </div>
            <div class="space-y-1" dir="ltr">
              <div class="flex justify-between text-[12px]"><label class="font-semibold" for="c-handle">{{ t('souk.handle') }}</label>
                <button v-if="d.canEdit" class="text-[11.5px] font-semibold underline" @click="c.handle = slug(c.fr.title); dirty = true">{{ t('souk.fromTitle') }}</button></div>
              <input id="c-handle" v-model="c.handle" :disabled="!d.canEdit" class="w-full h-10 rounded-xl ring-1 ring-stone-300 px-3 text-[13px] font-mono" @input="dirty = true" />
            </div>
            <div class="space-y-1" dir="ltr">
              <div class="flex justify-between text-[12px]"><label class="font-semibold" for="c-mt">Meta title</label>
                <span class="tabular-nums" :class="c.metaTitle.length > 60 ? 'text-rose-600' : 'text-stone-400'">{{ c.metaTitle.length }} / 60</span></div>
              <input id="c-mt" v-model="c.metaTitle" :disabled="!d.canEdit" class="w-full h-10 rounded-xl ring-1 ring-stone-300 px-3 text-[13px]" @input="dirty = true" />
            </div>
            <div class="space-y-1" dir="ltr">
              <div class="flex justify-between text-[12px]"><label class="font-semibold" for="c-md">Meta description</label>
                <span class="tabular-nums" :class="c.metaDescription.length > 160 ? 'text-rose-600' : 'text-stone-400'">{{ c.metaDescription.length }} / 160</span></div>
              <textarea id="c-md" v-model="c.metaDescription" :disabled="!d.canEdit" rows="2" class="w-full rounded-xl ring-1 ring-stone-300 p-3 text-[13px]" @input="dirty = true" />
            </div>
          </section>
        </div>

        <!-- side -->
        <aside class="space-y-4 xl:sticky xl:top-4">
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-1.5 text-[12px]">
            <h3 class="text-[12.5px] font-bold mb-1">{{ t('souk.fromBuy') }}</h3>
            <div class="flex justify-between gap-2"><span class="text-stone-500">{{ t('souk.stallShort') }}</span><span class="text-end">{{ d.stall }}</span></div>
            <div class="flex justify-between gap-2"><span class="text-stone-500">{{ t('souk.siteShort') }}</span><span>{{ d.brand }}</span></div>
            <div v-if="sizes.length" class="flex justify-between gap-2"><span class="text-stone-500">{{ t('souk.sizesLbl') }}</span><span class="text-end">{{ sizes.join(' · ') }}</span></div>
            <div v-if="d.colors.length > 1 || d.colors[0].code" class="flex justify-between gap-2"><span class="text-stone-500">{{ t('souk.colorsLbl') }}</span><span class="text-end" dir="ltr">{{ d.colors.map((x) => x.fr).join(' · ') }}</span></div>
            <div v-if="weights" class="flex justify-between gap-2"><span class="text-stone-500">{{ t('souk.weightLbl') }}</span><span class="text-end" dir="ltr">{{ weights }}</span></div>
            <div class="flex justify-between gap-2"><span class="text-stone-500">{{ t('souk.stockLbl') }}</span><span class="tabular-nums">{{ t('souk.stockLine').replace('{s}', d.stock.shelf).replace('{t}', d.stock.studio) }}</span></div>
            <div v-if="d.specs" class="pt-1 text-stone-700"><b>{{ t('souk.specs') }}:</b> {{ d.specs }}</div>
          </section>
          <section v-if="d.finals.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
            <h3 class="text-[12.5px] font-bold">{{ t('souk.finals') }} · {{ d.finals.length }}</h3>
            <div class="grid grid-cols-4 gap-1.5">
              <a v-for="f in d.finals" :key="f.url" :href="f.url" target="_blank" rel="noopener" class="block aspect-square rounded-lg overflow-hidden ring-1 ring-stone-200">
                <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
              </a>
            </div>
          </section>
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-1.5">
            <h3 class="text-[12.5px] font-bold">{{ t('souk.beforeSend') }}</h3>
            <div v-for="k in checks" :key="k.key" class="flex items-start gap-2 text-[12.5px]">
              <span class="w-5 h-5 shrink-0 rounded-full text-[11px] font-bold inline-flex items-center justify-center"
                    :class="k.ok ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'">{{ k.ok ? '✓' : '!' }}</span>
              <span :class="k.ok ? 'text-stone-800' : 'text-amber-900'">{{ t('souk.ck_' + k.key) }}</span>
            </div>
          </section>
          <div v-if="d.canEdit" class="space-y-2">
            <button class="w-full h-11 rounded-xl bg-white ring-1 ring-stone-300 text-[13px] font-semibold disabled:opacity-40" :disabled="busy || !dirty" @click="save()">
              {{ dirty ? t('souk.save') : t('souk.saved') }}
            </button>
            <button class="w-full h-11 rounded-xl bg-emerald-600 text-white text-[13.5px] font-bold disabled:opacity-40"
                    :disabled="busy || checks.some((k) => !k.ok)" @click="send">
              {{ busy ? t('souk.sending') : t('souk.toReview') }}
            </button>
            <p class="text-[11.5px] text-stone-500">{{ t('souk.toReviewNote') }}</p>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
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
const dirty = ref(false);
const lang = ref("fr");
const colQuery = ref("");
const c = ref(blank());
const tagsText = ref("");
const d = computed(() => data.value?.detail || null);

function blank() {
  return { fr: { title: "", description: "" }, ar: { title: "", description: "" }, productType: "", collections: [],
    tags: [], handle: "", metaTitle: "", metaDescription: "", prices: {} };
}
const fmt2 = (n) => Number(n || 0).toLocaleString("fr-FR", { maximumFractionDigits: 2 });
const sizes = computed(() => [...new Set((d.value?.variants || []).map((v) => v.size).filter(Boolean))]);
const weights = computed(() => {
  const seen = {};
  for (const v of d.value?.variants || []) if (v.grams) seen[v.size || "—"] = v.grams;
  return Object.keys(seen).map((k) => (k === "—" ? "" : k + " ") + (seen[k] >= 1000 ? (seen[k] / 1000).toFixed(2) + " kg" : seen[k] + " g")).join(" · ");
});
// One price per size (the colours of a size sell at the same price).
const groups = computed(() => {
  const out = {};
  for (const v of d.value?.variants || []) {
    const k = v.size || "";
    const g = out[k] || (out[k] = { key: k, skus: [], landed: 0, allocated: true });
    g.skus.push(v.sku);
    g.landed = Math.max(g.landed, Number(v.landed) || 0);
    g.allocated = g.allocated && !!v.allocated;
  }
  return Object.values(out);
});
const priceOf = (g) => c.value.prices[g.skus[0]] ?? "";
function setPrice(g, val) {
  for (const s of g.skus) c.value.prices[s] = Number(val) || 0;
  dirty.value = true;
}
const marginOf = (g) => {
  const p = Number(priceOf(g)) || 0;
  return p ? Math.round(((p - g.landed) / p) * 100) : 0;
};
const colTitle = (id) => (d.value?.collections || []).find((x) => x.id === id)?.title || id.split("/").pop();
const colHits = computed(() => {
  const q = colQuery.value.trim().toLowerCase();
  return (d.value?.collections || []).filter((x) => !c.value.collections.includes(x.id) && x.title.toLowerCase().includes(q)).slice(0, 30);
});
function addCol(id) {
  c.value.collections.push(id);
  colQuery.value = "";
  dirty.value = true;
}
function dropCol(id) {
  c.value.collections = c.value.collections.filter((x) => x !== id);
  dirty.value = true;
}
function slug(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120);
}
// Same rules as the server's checklist, live while typing.
const checks = computed(() => {
  const x = c.value;
  const landed = {};
  for (const v of d.value?.variants || []) landed[v.sku] = Number(v.landed) || 0;
  return [
    { key: "frTitle", ok: !!x.fr.title.trim() && x.fr.title.length <= 70 },
    { key: "frDesc", ok: x.fr.description.trim().length >= 40 },
    { key: "arText", ok: !!x.ar.title.trim() && !!x.ar.description.trim() },
    { key: "prices", ok: Object.keys(landed).every((s) => (Number(x.prices[s]) || 0) > landed[s]) },
    { key: "collection", ok: x.collections.length >= 1 },
    { key: "seo", ok: !!x.metaTitle.trim() && x.metaTitle.length <= 60 && !!x.metaDescription.trim()
        && x.metaDescription.length <= 160 && /^[a-z0-9]+(-[a-z0-9]+)*$/.test(x.handle || "") },
  ];
});

function draft() {
  const x = c.value;
  const colors = (d.value.colors || []).map((k) => k.fr).filter(Boolean);
  if (!x.fr.description.trim()) {
    const lines = [x.fr.title || d.value.title, ""];
    if (sizes.value.length) lines.push("• Tailles : " + sizes.value.join(", "));
    if (colors.length > 1) lines.push("• Couleurs : " + colors.join(", "));
    else if (colors.length === 1) lines.push("• Couleur : " + colors[0]);
    if (d.value.specs) lines.push("• " + d.value.specs);
    lines.push("• Paiement à la livraison partout au Maroc");
    x.fr.description = lines.join("\n");
  }
  if (!x.metaTitle) x.metaTitle = ((x.fr.title || d.value.title) + " | Justyol").slice(0, 60);
  if (!x.metaDescription) {
    const bits = [x.fr.title || d.value.title];
    if (sizes.value.length) bits.push(sizes.value.join(" / "));
    if (colors.length) bits.push(colors.join(", "));
    x.metaDescription = (bits.join(" · ") + ". Paiement à la livraison partout au Maroc.").slice(0, 160);
  }
  if (!x.handle) x.handle = slug(x.fr.title || d.value.title);
  dirty.value = true;
}

function payload() {
  return { ...c.value, tags: tagsText.value.split(",").map((s) => s.trim()).filter(Boolean) };
}
function take(det) {
  data.value = { ...data.value, detail: { ...det, collections: det.collections?.length ? det.collections : d.value?.collections || [] } };
}

async function load() {
  loading.value = true;
  try {
    data.value = await api("souk.content_boot", route.params.name ? { name: route.params.name } : {});
    const det = data.value.detail;
    c.value = det ? JSON.parse(JSON.stringify(det.content)) : blank();
    tagsText.value = (c.value.tags || []).join(", ");
    dirty.value = false;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

async function save(quiet = false) {
  busy.value = true;
  try {
    take(await apiPost("souk.content_save", { name: d.value.name, content: JSON.stringify(payload()) }));
    dirty.value = false;
    if (!quiet) success(t("souk.saved"));
    return true;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    return false;
  } finally {
    busy.value = false;
  }
}

async function send() {
  if (!(await save(true))) return;
  busy.value = true;
  try {
    const r = await apiPost("souk.content_send", { name: d.value.name });
    success(r.arabic && !r.arabic.ok ? t("souk.sentNoArabic") : t("souk.sentToReview"));
    router.push({ name: "SoukContent" });
    await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

function guard(e) {
  if (dirty.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}
window.addEventListener("beforeunload", guard);
onBeforeUnmount(() => window.removeEventListener("beforeunload", guard));
watch(() => route.params.name, load);
onMounted(load);
</script>
