<template>
  <!-- One souk product: where it is in the cycle, what was bought from whom,
       where its pieces are, and everything that happened to it. Backend:
       souk.product (+ finish_buy for a card still being created). -->
  <div class="max-w-[1100px] mx-auto px-4 py-5 space-y-4">
    <div v-if="loading && !d" class="h-[300px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <template v-if="d">
      <header class="flex items-start justify-between gap-3 flex-wrap">
        <div class="flex gap-3 items-center min-w-0">
          <router-link :to="{ name: 'SoukBoard' }" class="w-9 h-9 rounded-lg bg-white ring-1 ring-stone-200 flex items-center justify-center text-stone-600">
            <Icon :name="isRTL ? 'chevron-right' : 'chevron-left'" :size="16" />
          </router-link>
          <img v-if="d.image" :src="d.image" class="w-14 h-14 rounded-xl object-cover ring-1 ring-stone-200" alt="" />
          <div class="min-w-0">
            <h1 class="text-[19px] font-bold text-stone-900 truncate">{{ d.title }}</h1>
            <div class="text-[11.5px] text-stone-500 font-mono" dir="ltr">
              {{ d.name }} · {{ t('souk.stallShort') }} {{ d.stall }} · {{ t('souk.siteShort') }} {{ d.brand }} · {{ t('souk.tripNo').replace('{n}', d.trip) }}
            </div>
          </div>
        </div>
        <div class="flex gap-2">
          <button v-if="d.stage === 'buying'" class="h-9 px-3 rounded-lg bg-stone-900 text-white text-[12.5px] font-bold disabled:opacity-40" :disabled="busy" @click="finish">{{ t('souk.retry') }}</button>
          <router-link v-if="d.canReceive && d.stage === 'bought' && d.po" :to="{ name: 'SoukReceive', params: { po: d.po } }"
                       class="h-9 px-3 rounded-lg bg-emerald-600 text-white text-[12.5px] font-bold inline-flex items-center">{{ t('souk.receiveBtn') }}</router-link>
          <router-link v-if="d.canPhoto && d.stage === 'photos'" :to="{ name: 'SoukPhoto', params: { name: d.name } }"
                       class="h-9 px-3 rounded-lg bg-stone-900 text-white text-[12.5px] font-bold inline-flex items-center">{{ t('souk.shootBtn') }}</router-link>
          <router-link v-if="d.canStudio && d.stage === 'studio'" :to="{ name: 'SoukStudio', params: { name: d.name } }"
                       class="h-9 px-3 rounded-lg bg-stone-900 text-white text-[12.5px] font-bold inline-flex items-center">{{ t('souk.finalsBtn') }}</router-link>
          <router-link v-if="d.canContent && d.stage === 'content'" :to="{ name: 'SoukContent', params: { name: d.name } }"
                       class="h-9 px-3 rounded-lg bg-stone-900 text-white text-[12.5px] font-bold inline-flex items-center">{{ t('souk.contentBtn') }}</router-link>
          <router-link v-if="d.canReview && d.stage === 'review'" :to="{ name: 'SoukReview', params: { name: d.name } }"
                       class="h-9 px-3 rounded-lg bg-[#c4301c] text-white text-[12.5px] font-bold inline-flex items-center">{{ t('souk.reviewBtn') }}</router-link>
          <a v-if="d.shopifyAdmin" :href="d.shopifyAdmin" target="_blank" rel="noopener"
             class="h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center">Shopify</a>
          <router-link v-if="d.canBuy && d.stage !== 'buying'" :to="{ name: 'SoukBuy', query: { again: d.name, kind: 'souk' } }"
                       class="h-9 px-3 rounded-lg bg-white ring-1 ring-stone-300 text-[12.5px] font-semibold inline-flex items-center">{{ t('souk.buyAgain') }}</router-link>
        </div>
      </header>

      <div v-if="d.error" class="bg-rose-50 ring-1 ring-rose-200 rounded-xl p-3 text-[12px] text-rose-800 font-mono break-words">{{ d.error }}</div>

      <!-- stages -->
      <nav class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 overflow-x-auto">
        <ol class="flex gap-1.5 min-w-[640px]">
          <li v-for="(s, i) in STAGES" :key="s" class="flex-1 space-y-1.5">
            <div class="h-1.5 rounded-full" :class="i < stageIdx ? 'bg-emerald-600' : i === stageIdx ? 'bg-stone-900' : 'bg-stone-200'" />
            <div class="text-[11.5px] font-bold" :class="i === stageIdx ? 'text-stone-900' : 'text-stone-500'">{{ t('souk.st_' + s) }}</div>
            <div v-if="i === stageIdx" class="text-[10.5px] text-stone-500 tabular-nums">{{ t('souk.ageDays').replace('{n}', d.age) }}</div>
          </li>
        </ol>
      </nav>

      <div class="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4 items-start">
        <div class="space-y-4">
          <!-- variants -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-stone-100 text-[12.5px] font-bold">{{ t('souk.variants') }}</div>
            <table class="w-full text-[12px]">
              <thead class="text-stone-500">
                <tr>
                  <th class="text-start font-semibold px-4 py-1.5">SKU</th>
                  <th class="text-start font-semibold px-2">{{ t('souk.variant') }}</th>
                  <th class="font-semibold px-2">{{ t('souk.qtyShort') }}</th>
                  <th class="font-semibold px-2">{{ t('souk.cost') }}</th>
                  <th class="font-semibold px-2">{{ t('souk.sell') }}</th>
                  <th class="text-start font-semibold px-4">{{ t('souk.whereNow') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-stone-100">
                <tr v-for="v in d.variants" :key="v.sku">
                  <td class="px-4 py-1.5 font-mono font-bold">{{ v.sku }}</td>
                  <td class="px-2 text-stone-600">{{ [v.colorFr, v.sizeLabel].filter(Boolean).join(' · ') || '—' }}</td>
                  <td class="px-2 text-center tabular-nums">{{ v.qty }}</td>
                  <td class="px-2 text-center tabular-nums">{{ v.cost }}</td>
                  <td class="px-2 text-center tabular-nums">{{ v.price }}</td>
                  <td class="px-4 text-stone-600">
                    <span v-if="!v.stock.length" class="text-stone-400">—</span>
                    <span v-for="s in v.stock" :key="s.warehouse" class="me-2 tabular-nums">{{ shortWh(s.warehouse) }} {{ s.qty }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </section>

          <!-- photos -->
          <section v-if="d.finals.length || d.photos.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
            <div v-if="d.finals.length" class="space-y-1.5">
              <h2 class="text-[12.5px] font-bold">{{ t('souk.finals') }} · {{ d.finals.length }}</h2>
              <div class="flex gap-2 flex-wrap">
                <a v-for="f in d.finals" :key="f.url" :href="f.url" target="_blank" rel="noopener" class="block w-[86px] h-[86px] rounded-lg overflow-hidden ring-1 ring-stone-200">
                  <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                </a>
              </div>
            </div>
            <div v-if="d.photos.length" class="space-y-1.5">
              <h2 class="text-[12.5px] font-bold">{{ t('souk.rawPhotos') }} · {{ d.photos.length }}</h2>
              <div class="flex gap-2 flex-wrap">
                <a v-for="p in d.photos" :key="p.url" :href="p.url" target="_blank" rel="noopener" class="block w-[64px] h-[64px] rounded-lg overflow-hidden ring-1 ring-stone-200">
                  <img :src="p.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                </a>
              </div>
            </div>
            <div v-if="d.specs" class="text-[12px] text-stone-600"><b>{{ t('souk.specs') }}:</b> {{ d.specs }}</div>
          </section>

          <!-- timeline -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-1">
            <h2 class="text-[12.5px] font-bold mb-2">{{ t('souk.history') }}</h2>
            <div v-for="(e, i) in d.events" :key="i" class="grid grid-cols-[110px_1fr] gap-3 py-1.5">
              <span class="text-[11px] text-stone-500 tabular-nums">{{ e.at }}</span>
              <div>
                <div class="text-[12.5px] text-stone-900">{{ plain(e.text) }}</div>
                <div class="text-[11px] text-stone-500">{{ e.by }}</div>
              </div>
            </div>
          </section>
        </div>

        <aside class="space-y-4">
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-1.5 text-[12.5px]">
            <h2 class="font-bold mb-1">{{ t('souk.money') }}</h2>
            <div class="flex justify-between"><span class="text-stone-500">{{ t('souk.paid') }}</span><b class="tabular-nums">{{ fmt(d.cost) }} MAD</b></div>
            <div class="flex justify-between"><span class="text-stone-500">{{ t('souk.units') }}</span><b class="tabular-nums">{{ d.units }}</b></div>
            <div class="flex justify-between"><span class="text-stone-500">{{ t('souk.buyerLbl') }}</span><span>{{ d.buyer }}</span></div>
            <div class="flex justify-between"><span class="text-stone-500">Shopify</span><span class="font-mono">{{ d.shopifyId ? (d.stage === 'live' ? 'Active' : 'Draft') + ' · ' + d.shopifyId : '—' }}</span></div>
            <div v-if="d.contentBy" class="flex justify-between"><span class="text-stone-500">{{ t('souk.contentLbl') }}</span><span>{{ d.contentBy }}</span></div>
            <div v-if="d.publishedAt" class="flex justify-between"><span class="text-stone-500">{{ t('souk.publishedLbl') }}</span><span class="text-end">{{ d.publishedBy }} · {{ d.publishedAt }}</span></div>
            <div v-if="d.rejects" class="flex justify-between"><span class="text-stone-500">{{ t('souk.rejectsLbl') }}</span><b class="tabular-nums text-amber-800">{{ d.rejects }}</b></div>
          </section>
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2 text-[12px]">
            <h2 class="font-bold text-[12.5px]">{{ t('souk.purchases') }}</h2>
            <div v-for="p in d.purchases" :key="p.po" class="space-y-1 pb-2 border-b border-stone-100 last:border-0">
              <div class="flex justify-between gap-2">
                <span class="font-mono">{{ p.po }}</span>
                <span class="text-stone-500 truncate">{{ p.stall }}</span>
                <span class="tabular-nums font-semibold">{{ fmt(p.amount) }}</span>
                <span class="tabular-nums text-stone-500">{{ Math.round(p.received) }}%</span>
              </div>
              <div v-if="p.outcome" class="text-[11px] text-stone-600 tabular-nums">
                {{ t('souk.outcomeLine')
                  .replace('{g}', sum(p.outcome.lines, 'good'))
                  .replace('{st}', sum(p.outcome.lines, 'studio'))
                  .replace('{b}', sum(p.outcome.lines, 'brokenSupplier') + sum(p.outcome.lines, 'brokenTransport') + sum(p.outcome.lines, 'brokenWarehouse'))
                  .replace('{s}', sum(p.outcome.lines, 'short')) }}
                · <span class="font-mono">{{ p.pr }}</span>
              </div>
              <div v-if="p.owed" class="text-[11px] font-semibold text-amber-800">
                {{ t('souk.owesShort').replace('{n}', fmt(p.owed)) }}<span v-if="p.debitNote" class="font-mono"> · {{ p.debitNote }}</span>
                <span v-else> · {{ t('souk.noDebitYet') }}</span>
              </div>
            </div>
            <div v-if="!d.purchases.length" class="text-stone-400">—</div>
          </section>
          <section v-if="d.receipt" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3">
            <a :href="d.receipt" target="_blank" rel="noopener"><img :src="d.receipt" class="w-full rounded-lg" :alt="t('souk.receipt')" /></a>
          </section>
          <section class="bg-stone-50 ring-1 ring-stone-200/70 rounded-2xl p-4 text-[12px] text-stone-600 leading-relaxed">
            {{ t('souk.exitRule') }}
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const STAGES = ["buying", "bought", "photos", "studio", "content", "review", "live"];
const { t, isRTL } = useI18n();
const { warn } = useToast();
const route = useRoute();
const d = ref(null);
const loading = ref(true);
const busy = ref(false);
const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const shortWh = (w) => (w || "").replace(/ - JM$/, "");
const sum = (rows, k) => (rows || []).reduce((s, r) => s + (Number(r[k]) || 0), 0);
const stageIdx = computed(() => STAGES.indexOf(d.value?.stage));
// Comments may come back wrapped in markup; show their text only.
const plain = (s) => String(s || "").replace(/<[^>]*>/g, "").replace(/&amp;/g, "&");

async function load() {
  loading.value = true;
  try {
    d.value = await api("souk.product", { name: route.params.name });
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
async function finish() {
  busy.value = true;
  try {
    await apiPost("souk.finish_buy", { name: d.value.name });
    await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}
onMounted(load);
</script>
