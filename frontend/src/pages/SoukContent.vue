<template>
  <!-- Content queue (2 days): French first (the storefront's main language),
       Arabic as the shop's translation (a warning, never a blocker), product
       type, collections, tags, the final price per size and SEO. The buy's
       and the floor's specs come ready; "Draft for me" fills only the empty
       fields from them (souk.content_draft — no AI). Edits save themselves
       3 s after the last change and are never lost on a product switch or a
       closed tab. "Send to review" writes it onto the Shopify Draft.
       Backend: souk.content_boot / content_draft / content_save / content_send. -->
  <div class="px-4 py-5 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <div v-if="d && data" class="text-[11.5px] font-semibold text-stone-500">
          {{ t('souk.pub.kicker').replace('{n}', data.queue.length) }}
        </div>
        <h1 class="text-[20px] font-bold text-stone-900 truncate">{{ d ? (c.fr.title || d.title) : t('souk.contentTitle') }}</h1>
        <p v-if="!d" class="text-[12.5px] text-stone-500 mt-0.5 max-w-[680px]">{{ t('souk.contentIntro') }}</p>
      </div>
      <div v-if="d" class="flex gap-2 items-center flex-wrap">
        <span v-if="clock" class="text-[11.5px] font-bold rounded-md px-2 py-1 bg-white ring-1 tabular-nums"
              :class="clock.late ? 'ring-rose-200 text-rose-700' : 'ring-stone-200 text-stone-700'">{{ clock.text }}</span>
        <span v-if="dueText" class="text-[11.5px] text-stone-600 bg-white ring-1 ring-stone-200 rounded-md px-2 py-1 tabular-nums" dir="auto">{{ dueText }}</span>
        <span class="text-[11.5px] text-stone-600 bg-white ring-1 ring-stone-200 rounded-md px-2 py-1">{{ writerText }}</span>
        <button v-if="d.canEdit" class="h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold text-stone-700 inline-flex items-center gap-1.5 disabled:opacity-40"
                :disabled="drafting" :title="t('souk.pub.draftHint')" @click="draftForMe">
          <Icon name="sparkles" :size="14" />{{ drafting ? t('souk.pub.drafting') : t('souk.pub.draftForMe') }}
        </button>
        <button v-if="d.canEdit" class="h-9 px-4 rounded-lg bg-[var(--accent-600)] text-white text-[13px] font-bold disabled:bg-stone-200 disabled:text-stone-500"
                :disabled="busy || blockers.length > 0" @click="send">
          {{ busy ? t('souk.sending') : t('souk.toReview') }}
        </button>
      </div>
    </header>

    <div v-if="loading && !data" class="h-[420px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <!-- nothing in the queue: the same card on the three screens -->
    <div v-else-if="data && !data.queue.length && !d" class="bg-white ring-1 ring-stone-200/70 rounded-2xl px-6 py-12 flex flex-col items-center text-center gap-3">
      <span class="w-12 h-12 rounded-full bg-stone-100 text-stone-500 inline-flex items-center justify-center"><Icon name="inbox" :size="22" /></span>
      <p class="text-[13.5px] font-semibold text-stone-700">{{ t('souk.contentNone') }}</p>
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
        <div v-if="!data.queue.length" class="p-6 text-center text-[12.5px] text-stone-500">{{ t('souk.contentNone') }}</div>
        <router-link v-for="q in data.queue" :key="q.name" :to="{ name: 'SoukContent', params: { name: q.name } }"
                     class="flex items-center gap-2.5 px-3 py-2.5 border-b border-stone-100 last:border-0 min-h-[56px]"
                     :class="d && d.name === q.name ? 'bg-[var(--accent-50)]' : 'hover:bg-stone-50'">
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
      <div v-else class="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-4 items-start min-w-0">
        <div class="space-y-4 min-w-0">
          <div class="text-[11.5px] text-stone-500 font-mono px-1" dir="ltr">{{ d.name }} · {{ d.brand }}</div>

          <div v-if="d.reviewNote" class="bg-amber-50 ring-1 ring-amber-200 rounded-xl p-3 text-[12.5px] text-amber-900">
            <b>{{ t('souk.reviewSaid').replace('{n}', d.rejects) }}</b> {{ d.reviewNote }}
          </div>
          <div v-if="!d.canEdit" class="bg-stone-50 ring-1 ring-stone-200 rounded-xl p-3 text-[12.5px] text-stone-700">{{ t('souk.contentNotNow') }}</div>

          <!-- texts -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3.5">
            <div role="tablist" class="inline-flex gap-0.5 p-1 bg-stone-100 rounded-[10px]">
              <button v-for="l in ['fr', 'ar']" :key="l" role="tab" :aria-selected="lang === l"
                      class="h-8 px-3.5 rounded-lg text-[12.5px] font-semibold"
                      :class="lang === l ? 'bg-white shadow-sm text-stone-900' : 'text-stone-600'" @click="lang = l">
                {{ l === 'fr' ? t('souk.langFr') : t('souk.langAr') }}
                <span v-if="l === 'ar' && !arDone" class="ms-1 inline-block w-1.5 h-1.5 rounded-full bg-amber-500 align-middle" />
              </button>
            </div>
            <div class="space-y-1">
              <label class="text-[12px] font-semibold text-stone-700" for="c-title">{{ t('souk.pub.fTitle') }}</label>
              <input id="c-title" v-model="c[lang].title" :dir="lang === 'ar' ? 'rtl' : 'ltr'" :disabled="!d.canEdit"
                     class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14.5px]" />
              <div class="text-[11px] tabular-nums" :class="c[lang].title.length > 70 ? 'text-rose-600 font-semibold' : 'text-stone-500'">
                {{ t('souk.pub.chars').replace('{n}', c[lang].title.length).replace('{m}', 70) }}
              </div>
            </div>
            <div class="space-y-1">
              <label class="text-[12px] font-semibold text-stone-700" for="c-desc">{{ t('souk.pub.fDesc') }}</label>
              <textarea id="c-desc" v-model="c[lang].description" :dir="lang === 'ar' ? 'rtl' : 'ltr'" :disabled="!d.canEdit" rows="9"
                        class="w-full rounded-lg ring-1 ring-stone-300 px-3 py-2.5 text-[14px] leading-relaxed" />
              <div class="text-[11px] text-stone-500">{{ t('souk.descHint') }}</div>
            </div>
          </section>

          <!-- catalogue + prices -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 grid grid-cols-1 md:grid-cols-2 gap-3.5">
            <div class="space-y-1">
              <label class="text-[12px] font-semibold text-stone-700" for="c-type">{{ t('souk.productType') }}</label>
              <select id="c-type" v-model="c.productType" :disabled="!d.canEdit" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-2.5 text-[14px] bg-white">
                <option value="">{{ t('souk.pub.pickType') }}</option>
                <option v-for="pt in typeOptions" :key="pt" :value="pt">{{ pt }}</option>
              </select>
            </div>
            <div class="space-y-1.5">
              <div class="text-[12px] font-semibold text-stone-700">{{ t('souk.collections') }}</div>
              <div v-if="d.collectionsError" class="text-[11.5px] text-rose-700 break-words">{{ d.collectionsError }}</div>
              <div class="flex gap-1.5 flex-wrap items-center min-h-[44px]">
                <span v-for="id in c.collections" :key="id" class="h-8 ps-2.5 pe-1 rounded-full bg-stone-100 ring-1 ring-stone-200 text-[12px] font-semibold inline-flex items-center gap-1">
                  {{ colTitle(id) }}
                  <button v-if="d.canEdit" class="w-6 h-6 rounded-full hover:bg-stone-200 inline-flex items-center justify-center" :aria-label="t('souk.remove')" @click="dropCol(id)"><Icon name="x" :size="12" /></button>
                </span>
                <button v-if="d.canEdit && !addingCol" class="h-8 px-2.5 rounded-full bg-white ring-1 ring-stone-300 text-[12px] font-semibold text-stone-600" @click="addingCol = true">
                  {{ t('souk.pub.addCollection') }}
                </button>
              </div>
              <div v-if="d.canEdit && (addingCol || !c.collections.length)" class="relative">
                <input v-model="colQuery" class="w-full h-10 rounded-lg ring-1 ring-stone-300 px-3 text-[13px]" :placeholder="t('souk.collectionSearch')"
                       @keydown.esc="colQuery = ''; addingCol = false" />
                <div v-if="colQuery.trim()" class="absolute z-10 mt-1 w-full max-h-[240px] overflow-auto bg-white ring-1 ring-stone-200 rounded-xl shadow-lg">
                  <button v-for="x in colHits" :key="x.id" class="block w-full text-start px-3 py-2.5 text-[12.5px] hover:bg-stone-50" @click="addCol(x.id)">{{ x.title }}</button>
                  <div v-if="!colHits.length" class="px-3 py-2 text-[12px] text-stone-400">—</div>
                </div>
              </div>
            </div>

            <div v-for="g in groups" :key="g.key" class="space-y-1">
              <label class="text-[12px] font-semibold text-stone-700" :for="'c-price-' + g.key">{{ t('souk.finalPrice') }} {{ g.key }}</label>
              <div class="flex items-center gap-2">
                <input :id="'c-price-' + g.key" type="number" inputmode="decimal" :value="priceOf(g)" :disabled="!d.canEdit"
                       class="w-full max-w-[160px] h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[15px] font-bold tabular-nums" @input="setPrice(g, $event.target.value)" />
                <span class="text-[12px] text-stone-500">MAD</span>
              </div>
              <div class="text-[11px] text-stone-500 tabular-nums">
                {{ t('souk.landedCost') }} {{ fmt2(g.landed) }} ·
                <span class="font-bold" :class="marginOf(g) <= 0 ? 'text-rose-600' : 'text-emerald-700'">{{ t('souk.marginPct').replace('{n}', marginOf(g)) }}</span>
              </div>
              <div v-if="!g.allocated" class="text-[11px] text-amber-700">{{ t('souk.transportNotYet') }}</div>
            </div>

            <div class="space-y-1 md:col-span-2">
              <label class="text-[12px] font-semibold text-stone-700" for="c-tags">{{ t('souk.pub.tags') }}</label>
              <input id="c-tags" v-model="tagsText" dir="auto" :disabled="!d.canEdit" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14px]" :placeholder="t('souk.tagsHint')" />
            </div>
          </section>

          <!-- SEO -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3.5">
            <h2 class="text-[13.5px] font-bold">{{ t('souk.seoTitle') }}</h2>
            <div class="rounded-lg bg-stone-50 px-3.5 py-3 space-y-0.5" dir="ltr" lang="fr">
              <div class="text-[12px] text-stone-600 truncate">justyol.com › products › {{ c.handle || '…' }}</div>
              <div class="text-[17px] text-[#1a0dab] truncate">{{ c.metaTitle || c.fr.title || '—' }}</div>
              <div class="text-[13px] text-stone-600 line-clamp-2 leading-normal">{{ c.metaDescription || '—' }}</div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              <div class="space-y-1">
                <div class="flex justify-between items-center text-[12px]">
                  <label class="font-semibold text-stone-700" for="c-handle">{{ t('souk.handle') }}</label>
                  <button v-if="d.canEdit" class="lp-tap h-7 px-1 text-[11.5px] font-semibold underline" @click="c.handle = slug(c.fr.title)">{{ t('souk.fromTitle') }}</button>
                </div>
                <input id="c-handle" v-model="c.handle" dir="ltr" :disabled="!d.canEdit" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[13.5px] font-mono" />
              </div>
              <div class="space-y-1">
                <label class="text-[12px] font-semibold text-stone-700" for="c-mt">{{ t('souk.pub.metaTitle') }}</label>
                <input id="c-mt" v-model="c.metaTitle" dir="ltr" :disabled="!d.canEdit" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14px]" />
                <div class="text-[11px] tabular-nums" :class="c.metaTitle.length > 60 ? 'text-rose-600 font-semibold' : 'text-stone-500'">
                  {{ t('souk.pub.chars').replace('{n}', c.metaTitle.length).replace('{m}', 60) }}
                </div>
              </div>
              <div class="space-y-1 md:col-span-2">
                <label class="text-[12px] font-semibold text-stone-700" for="c-md">{{ t('souk.pub.metaDesc') }}</label>
                <textarea id="c-md" v-model="c.metaDescription" dir="ltr" :disabled="!d.canEdit" rows="2" class="w-full rounded-lg ring-1 ring-stone-300 px-3 py-2.5 text-[14px] leading-normal" />
                <div class="text-[11px] tabular-nums" :class="c.metaDescription.length > 160 ? 'text-rose-600 font-semibold' : 'text-stone-500'">
                  {{ t('souk.pub.chars').replace('{n}', c.metaDescription.length).replace('{m}', 160) }}
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- side -->
        <aside class="space-y-4 xl:sticky xl:top-4 min-w-0">
          <section v-if="d.finals.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 space-y-2.5">
            <h3 class="text-[13px] font-bold">{{ t('souk.finals') }} · {{ d.finals.length }}</h3>
            <div class="grid grid-cols-5 gap-1.5">
              <a v-for="f in d.finals" :key="f.url" :href="f.url" target="_blank" rel="noopener" class="block aspect-[4/5] rounded-md overflow-hidden ring-1 ring-stone-200">
                <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
              </a>
            </div>
          </section>
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 text-[12.5px]">
            <h3 class="text-[13px] font-bold mb-1.5">{{ t('souk.fromBuy') }}</h3>
            <div v-for="row in facts" :key="row.k" class="flex justify-between gap-2.5 py-1 border-b border-stone-100 last:border-0">
              <span class="text-stone-500 shrink-0">{{ row.k }}</span><span class="font-semibold text-end min-w-0 break-words" :dir="row.ltr ? 'ltr' : null">{{ row.v }}</span>
            </div>
            <div v-if="d.specs" class="pt-1.5 text-stone-700"><b>{{ t('souk.specs') }}:</b> {{ d.specs }}</div>
          </section>
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3.5 space-y-2">
            <h3 class="text-[13px] font-bold">{{ t('souk.beforeSend') }}</h3>
            <div v-for="k in checks" :key="k.key" class="flex items-start gap-2 text-[12.5px]">
              <span class="w-[18px] h-[18px] mt-px shrink-0 rounded-full text-[11px] font-bold inline-flex items-center justify-center text-white"
                    :class="k.ok ? 'bg-emerald-700' : k.soft ? 'bg-amber-500' : 'bg-rose-600'">{{ k.ok ? '✓' : '!' }}</span>
              <div class="min-w-0">
                <div :class="k.ok ? 'text-stone-800' : k.soft ? 'text-amber-900' : 'text-rose-800'">{{ t('souk.ck_' + k.key) }}</div>
                <div v-if="!k.ok && k.soft" class="text-[11px] text-amber-700">{{ t('souk.pub.softWarn') }}</div>
              </div>
            </div>
          </section>
          <div v-if="d.canEdit" class="space-y-2">
            <div class="flex items-center justify-between gap-2 min-h-[36px] text-[12px]">
              <span class="font-semibold inline-flex items-center gap-1.5"
                    :class="saveState === 'error' ? 'text-rose-700' : dirty || saving ? 'text-amber-800' : 'text-emerald-700'">
                <span class="w-2 h-2 rounded-full" :class="saveState === 'error' ? 'bg-rose-500' : dirty || saving ? 'bg-amber-500' : 'bg-emerald-500'" />
                {{ saving ? t('souk.pub.saving') : saveState === 'error' ? t('souk.pub.saveFailed').replace('{e}', saveError) : dirty ? t('souk.pub.unsaved') : t('souk.pub.saved') }}
              </span>
              <button v-if="dirty || saveState === 'error'" class="h-8 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12px] font-semibold disabled:opacity-40" :disabled="saving" @click="save({ quiet: false })">
                {{ t('souk.pub.saveNow') }}
              </button>
            </div>
            <p class="text-[11px] text-stone-400">{{ t('souk.pub.autoNote') }}</p>
            <button class="w-full h-11 rounded-xl bg-[var(--accent-600)] text-white text-[13.5px] font-bold disabled:bg-stone-200 disabled:text-stone-500"
                    :disabled="busy || blockers.length > 0" @click="send">
              {{ busy ? t('souk.sending') : t('souk.toReview') }}
            </button>
            <p v-if="blockers.length" class="text-[11.5px] text-rose-700">{{ t('souk.pub.blocksSend').replace('{list}', blockers.map((k) => t('souk.ck_' + k.key)).join(' · ')) }}</p>
            <p class="text-[11.5px] text-stone-500">{{ t('souk.toReviewNote') }}</p>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter, onBeforeRouteUpdate, onBeforeRouteLeave } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t, locale } = useI18n();
const { success, warn } = useToast();
const route = useRoute();
const router = useRouter();
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const drafting = ref(false);
const lang = ref("fr");
const colQuery = ref("");
const addingCol = ref(false);
const c = ref(blank());
const tagsText = ref("");
const d = computed(() => data.value?.detail || null);

function blank() {
  return { fr: { title: "", description: "" }, ar: { title: "", description: "" }, productType: "", collections: [],
    tags: [], handle: "", metaTitle: "", metaDescription: "", prices: {} };
}
const fmt2 = (n) => Number(n || 0).toLocaleString("fr-FR", { maximumFractionDigits: 2 });
const colorName = (x) => (locale.value === "ar" ? x.ar || x.fr : x.fr || x.code);
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
const facts = computed(() => {
  const x = d.value;
  if (!x) return [];
  const rows = [
    { k: t("souk.stallShort"), v: x.stall },
    { k: t("souk.siteShort"), v: x.brand },
  ];
  if (sizes.value.length) rows.push({ k: t("souk.sizesLbl").replace(/\s*:$/, ""), v: sizes.value.join(" · ") });
  const cols = (x.colors || []).filter((k) => k.code);
  if (cols.length) rows.push({ k: t("souk.colorsLbl").replace(/\s*:$/, ""), v: cols.map(colorName).join(" · ") });
  if (weights.value) rows.push({ k: t("souk.weightLbl").replace(/\s*:$/, ""), v: weights.value, ltr: true });
  rows.push({ k: t("souk.stockLbl").replace(/\s*:$/, ""), v: t("souk.stockLine").replace("{s}", x.stock.shelf).replace("{t}", x.stock.studio) });
  const cost = groups.value.filter((g) => g.landed).map((g) => (g.key ? g.key + " " : "") + fmt2(g.landed)).join(" · ");
  if (cost) rows.push({ k: t("souk.pub.costLbl"), v: cost + " MAD", ltr: true });
  return rows;
});
const typeOptions = computed(() => [...new Set([...(d.value?.productTypes || []), c.value.productType].filter(Boolean))]);
const priceOf = (g) => c.value.prices[g.skus[0]] ?? "";
function setPrice(g, val) {
  for (const s of g.skus) c.value.prices[s] = Number(val) || 0;
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
  addingCol.value = false;
}
function dropCol(id) {
  c.value.collections = c.value.collections.filter((x) => x !== id);
}
function slug(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120);
}
const arDone = computed(() => !!c.value.ar.title.trim() && !!c.value.ar.description.trim());
// Same rules as the server's checklist (_content_checks), live while typing.
// soft = a warning: send goes ahead (the server's own flag wins).
const checks = computed(() => {
  const x = c.value;
  const landed = {};
  for (const v of d.value?.variants || []) landed[v.sku] = Number(v.landed) || 0;
  const soft = new Set(["arText", ...(d.value?.checks || []).filter((k) => k.soft).map((k) => k.key)]);
  return [
    { key: "frTitle", ok: !!x.fr.title.trim() && x.fr.title.length <= 70 },
    { key: "frDesc", ok: x.fr.description.trim().length >= 40 },
    { key: "arText", ok: arDone.value },
    { key: "prices", ok: Object.keys(landed).every((s) => (Number(x.prices[s]) || 0) > landed[s]) },
    { key: "collection", ok: x.collections.length >= 1 },
    { key: "seo", ok: !!x.metaTitle.trim() && x.metaTitle.length <= 60 && !!x.metaDescription.trim()
        && x.metaDescription.length <= 160 && /^[a-z0-9]+(-[a-z0-9]+)*$/.test(x.handle || "") },
  ].map((k) => ({ ...k, soft: soft.has(k.key) }));
});
const blockers = computed(() => checks.value.filter((k) => !k.ok && !k.soft));

// Stage clock, deadline and writer.
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
const writerText = computed(() => (d.value?.writer ? t("souk.pub.writer").replace("{n}", d.value.writer) : t("souk.pub.writerYou")));

// --- saving: autosave 3 s after the last change; never lose an edit ---------
function payload() {
  return { ...c.value, tags: tagsText.value.split(",").map((s) => s.trim()).filter(Boolean) };
}
const snap = () => JSON.stringify(payload());
const baseline = ref("");
const current = computed(() => snap());
const dirty = computed(() => !!d.value?.canEdit && current.value !== baseline.value);
const saving = ref(false);
const saveState = ref("idle"); // idle | saved | error
const saveError = ref("");
let timer = null;
let inflight = null;

watch(current, () => {
  clearTimeout(timer);
  if (!dirty.value) return;
  if (saveState.value === "saved") saveState.value = "idle";
  timer = setTimeout(() => save(), 3000);
});

function take(det) {
  data.value = { ...data.value, detail: { ...det, collections: det.collections?.length ? det.collections : d.value?.collections || [] } };
}

async function save({ quiet = true } = {}) {
  clearTimeout(timer);
  if (inflight) await inflight;
  if (!d.value?.canEdit) return true;
  if (!dirty.value) return true;
  const body = current.value;
  const name = d.value.name;
  saving.value = true;
  inflight = (async () => {
    try {
      const det = await apiPost("souk.content_save", { name, content: body });
      if (d.value?.name === name) {
        take(det);
        baseline.value = body;
      }
      saveState.value = "saved";
      saveError.value = "";
      if (!quiet) success(t("souk.saved"));
      return true;
    } catch (e) {
      saveState.value = "error";
      saveError.value = String(e.message || e);
      if (!quiet) warn(t("souk.failed"), saveError.value);
      return false;
    } finally {
      saving.value = false;
      inflight = null;
    }
  })();
  const ok = await inflight;
  // Typed on while it was saving: the next round goes by itself.
  if (ok && dirty.value) timer = setTimeout(() => save(), 3000);
  return ok;
}

async function load() {
  clearTimeout(timer);
  loading.value = true;
  try {
    const next = await api("souk.content_boot", route.params.name ? { name: route.params.name } : {});
    const same = next?.detail?.name && next.detail.name === d.value?.name;
    data.value = next;
    const det = next.detail;
    c.value = det ? JSON.parse(JSON.stringify(det.content)) : blank();
    tagsText.value = (c.value.tags || []).join(", ");
    baseline.value = snap();
    saveState.value = "idle";
    saveError.value = "";
    if (!same) {
      lang.value = "fr";
      colQuery.value = "";
      addingCol.value = false;
    }
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

async function draftForMe() {
  drafting.value = true;
  try {
    const g = await api("souk.content_draft", { name: d.value.name });
    let n = 0;
    const fill = (obj, key, val) => {
      if (val && !String(obj[key] || "").trim()) {
        obj[key] = val;
        n++;
      }
    };
    fill(c.value.fr, "title", g.fr?.title);
    fill(c.value.fr, "description", g.fr?.description);
    fill(c.value.ar, "title", g.ar?.title);
    fill(c.value.ar, "description", g.ar?.description);
    fill(c.value, "productType", g.productType);
    fill(c.value, "handle", g.handle);
    fill(c.value, "metaTitle", g.metaTitle);
    fill(c.value, "metaDescription", g.metaDescription);
    if (!tagsText.value.trim() && g.tags?.length) {
      tagsText.value = g.tags.join(", ");
      n++;
    }
    if (n) success(t("souk.pub.draftFilled").replace("{n}", n));
    else success(t("souk.pub.draftNothing"));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    drafting.value = false;
  }
}

async function send() {
  if (!(await save())) {
    warn(t("souk.failed"), saveError.value);
    return;
  }
  busy.value = true;
  try {
    const r = await apiPost("souk.content_send", { name: d.value.name });
    // No longer ours to edit: nothing left to guard on the way out.
    data.value = { ...data.value, detail: { ...d.value, canEdit: false } };
    success(r.arabic && !r.arabic.ok ? t("souk.sentNoArabic") : t("souk.sentToReview"));
    if (route.params.name) await router.push({ name: "SoukContent" });
    else await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

// Leaving the product (another one in the queue, another screen): save
// first; only if that fails, ask.
async function guardLeave() {
  if (!dirty.value && !inflight) return true;
  if ((await save()) && !dirty.value) return true;
  return window.confirm(t("souk.pub.leaveUnsaved"));
}
onBeforeRouteUpdate((to, from) => (to.params.name === from.params.name ? true : guardLeave()));
onBeforeRouteLeave(() => guardLeave());

function guard(e) {
  if (dirty.value || saving.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}
window.addEventListener("beforeunload", guard);
onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", guard);
  clearTimeout(timer);
});
watch(() => route.params.name, load);
onMounted(load);
</script>
