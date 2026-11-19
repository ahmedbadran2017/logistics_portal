<template>
  <!-- One souk product: where it is in the cycle and how long each stage
       took, what it cost per piece, where its pieces are, who has it now,
       and everything that happened to it. Backend: souk.product (+ claim,
       review_drop, finish_buy for a card still being created).
       Look = design Detail.dc.html (1280px). -->
  <div class="max-w-[1320px] mx-auto px-4 sm:px-5 pt-5 sm:pt-6 pb-10 flex flex-col gap-4">
    <div v-if="loading && !d" class="h-[300px] rounded-xl bg-white ring-1 ring-inset ring-stone-200 animate-pulse" />

    <template v-if="d">
      <header class="flex items-start justify-between gap-3 flex-wrap">
        <div class="flex gap-3 items-center min-w-0">
          <router-link :to="{ name: 'SoukBoard' }" :aria-label="t('souk.pd.back')" :title="t('souk.pd.back')"
                       class="w-11 h-11 lg:w-9 lg:h-9 shrink-0 rounded-lg bg-white ring-1 ring-inset ring-stone-200 flex items-center justify-center text-stone-700 hover:bg-stone-50">
            <Icon :name="isRTL ? 'chevron-right' : 'chevron-left'" :size="18" :stroke-width="2" />
          </router-link>
          <img v-if="d.image" :src="d.image" class="w-[52px] h-[52px] shrink-0 rounded-[10px] object-cover bg-stone-100" alt="" />
          <div v-else class="w-[52px] h-[52px] shrink-0 rounded-[10px] bg-stone-100 ring-1 ring-inset ring-stone-200 flex items-center justify-center text-stone-500">
            <Icon name="image" :size="20" />
          </div>
          <div class="min-w-0 flex flex-col gap-0.5">
            <h1 class="text-[20px] font-bold text-stone-900 leading-tight line-clamp-2">{{ d.title }}</h1>
            <div class="text-[12px] text-stone-600 break-words">
              <bdi class="mono" dir="ltr">{{ d.name }}</bdi>
              <span v-if="d.stall"> · {{ t('souk.stallShort') }} {{ d.stall }}</span>
              <span v-if="d.brand"> · {{ t('souk.siteShort') }} {{ d.brand }}</span>
              <span v-if="d.trip"> · {{ t('souk.tripNo').replace('{n}', d.trip) }}</span>
            </div>
          </div>
        </div>
        <!-- Phone: one swipeable row under the title (wrapping left a lone
             button on a second line); desk: wraps beside the title. -->
        <div class="w-full sm:w-auto -mx-4 px-4 sm:mx-0 sm:px-0 flex gap-2 overflow-x-auto sm:overflow-visible sm:flex-wrap">
          <button v-if="d.stage === 'buying'" class="btn bg-stone-900 text-white disabled:opacity-40" :disabled="busy" @click="finish">{{ t('souk.retry') }}</button>
          <router-link v-if="d.canReceive && d.stage === 'bought' && d.po" :to="{ name: 'SoukReceive', params: { po: d.po } }"
                       class="btn btn-accent">{{ t('souk.receiveBtn') }}</router-link>
          <router-link v-if="d.canPhoto && d.stage === 'photos'" :to="{ name: 'SoukPhoto', params: { name: d.name } }"
                       class="btn bg-stone-900 text-white">{{ t('souk.shootBtn') }}</router-link>
          <router-link v-if="d.canStudio && d.stage === 'studio'" :to="{ name: 'SoukStudio', params: { name: d.name } }"
                       class="btn bg-stone-900 text-white">{{ t('souk.finalsBtn') }}</router-link>
          <router-link v-if="d.canContent && d.stage === 'content'" :to="{ name: 'SoukContent', params: { name: d.name } }"
                       class="btn bg-stone-900 text-white">{{ t('souk.contentBtn') }}</router-link>
          <router-link v-if="d.canReview && d.stage === 'review'" :to="{ name: 'SoukReview', params: { name: d.name } }"
                       class="btn btn-accent">{{ t('souk.reviewBtn') }}</router-link>
          <!-- claim / release -->
          <template v-if="d.canClaim && d.stage !== 'buying'">
            <button v-if="!d.claimedBy || (d.claimedBy !== me && d.canDrop)" class="btn btn-line disabled:opacity-40" :disabled="busy" @click="claim(0)">
              <Icon name="hand" :size="14" />{{ t('souk.pd.claim') }}
            </button>
            <button v-if="d.claimedBy && (d.claimedBy === me || d.canDrop)" class="btn btn-line disabled:opacity-40" :disabled="busy" @click="claim(1)">
              <Icon name="unlock" :size="14" />{{ t('souk.pd.release') }}
            </button>
          </template>
          <a v-if="d.shopifyAdmin" :href="d.shopifyAdmin" target="_blank" rel="noopener" class="btn btn-line">
            Shopify<Icon name="external-link" :size="13" />
          </a>
          <router-link v-if="d.canBuy && d.stage !== 'buying'" :to="{ name: 'SoukBuy', query: { again: d.name, kind: 'souk' } }"
                       class="btn btn-line">{{ t('souk.buyAgain') }}</router-link>
          <button v-if="canDropNow" class="btn bg-white ring-1 ring-inset ring-rose-200 text-rose-700 hover:bg-rose-50" @click="openDrop">{{ t('souk.pd.drop') }}</button>
        </div>
      </header>

      <div v-if="d.error" class="bg-rose-50 ring-1 ring-inset ring-rose-200 rounded-xl px-4 py-3 text-[13px] text-rose-800 mono break-words">{{ d.error }}</div>

      <div v-if="d.stage === 'dropped'" class="bg-stone-50 ring-1 ring-inset ring-stone-200 rounded-xl px-4 py-3 text-[13px] text-stone-800 flex flex-col gap-0.5">
        <div class="font-bold">
          {{ d.droppedFrom ? fill(t('souk.pd.droppedBanner'), { s: t('souk.st_' + d.droppedFrom) }) : t('souk.st_dropped') }}
          <span v-if="whyOf(d.reviewNote)" class="font-semibold text-stone-600"> · {{ t('souk.lb.why_' + whyOf(d.reviewNote)) }}</span>
        </div>
        <div v-if="noteText(d.reviewNote)" class="break-words">{{ noteText(d.reviewNote) }}</div>
      </div>

      <!-- stages -->
      <nav ref="stepNav" :aria-label="t('souk.pd.stagesNav')" class="bg-white rounded-xl ring-1 ring-inset ring-stone-200 px-4 py-3.5 overflow-x-auto">
        <ol class="flex gap-1.5 min-w-[760px]">
          <li v-for="st in stepper" :key="st.s" class="flex-1 flex flex-col gap-1.5" :data-here="st.here ? 1 : undefined" :aria-current="st.here ? 'step' : undefined">
            <div class="h-1.5 rounded-full"
                 :class="{ done: 'bg-emerald-700', current: 'bg-stone-900', late: 'bg-rose-600', todo: 'bg-stone-200' }[st.state]" />
            <span class="text-[13px] font-bold"
                  :class="st.state === 'late' ? 'text-rose-700' : st.state === 'todo' ? 'text-stone-600' : 'text-stone-900'">{{ t('souk.st_' + st.s) }}</span>
            <span class="text-[12px] text-stone-600 tabular-nums">{{ st.sub }}</span>
          </li>
        </ol>
      </nav>

      <div class="flex flex-wrap gap-4 items-start">
        <div class="flex-[999_1_560px] min-w-0 flex flex-col gap-4">
          <!-- what happened -->
          <section class="bg-white rounded-xl ring-1 ring-inset ring-stone-200 p-4 flex flex-col gap-1">
            <h2 class="text-[14px] font-bold text-stone-900 mb-2">{{ t('souk.pd.happened') }}</h2>
            <div v-for="(e, i) in d.events" :key="i"
                 class="grid grid-cols-[76px_10px_minmax(0,1fr)] sm:grid-cols-[96px_14px_minmax(0,1fr)] gap-2.5 items-start py-1.5">
              <span class="text-[12px] text-stone-600 tabular-nums pt-px">{{ stamp(e.at) }}</span>
              <span class="w-2.5 h-2.5 rounded-full mt-1 bg-stone-400" />
              <div class="min-w-0 flex flex-col gap-px">
                <span class="text-[13px] font-semibold text-stone-900 break-words">{{ eventText(e.text) }}</span>
                <span v-if="e.by" class="text-[12px] text-stone-600">{{ e.by }}</span>
              </div>
            </div>
            <div v-if="!d.events.length" class="text-[13px] text-stone-500 py-1">{{ t('souk.pd.noLog') }}</div>
          </section>

          <!-- variants -->
          <section class="bg-white rounded-xl ring-1 ring-inset ring-stone-200 overflow-hidden">
            <h2 class="px-4 pt-3.5 pb-2 text-[14px] font-bold text-stone-900">{{ t('souk.variants') }} · {{ d.variants.length }}</h2>
            <div class="overflow-x-auto">
              <table class="w-full min-w-[520px] text-[13px]">
                <thead class="text-stone-500 text-[12px]">
                  <tr class="border-b border-stone-100">
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
                    <td class="px-4 py-2 mono text-[12px] font-medium text-stone-900 whitespace-nowrap" dir="ltr">{{ v.sku }}</td>
                    <td class="px-2 text-stone-600">{{ [v.colorFr, v.sizeLabel].filter(Boolean).join(' · ') || '—' }}</td>
                    <td class="px-2 text-center tabular-nums">{{ v.qty }}</td>
                    <td class="px-2 text-center tabular-nums">{{ v.cost }}</td>
                    <td class="px-2 text-center tabular-nums">{{ v.price }}</td>
                    <td class="px-4 text-stone-600">
                      <span v-if="!v.stock.length" class="text-stone-500">—</span>
                      <span v-for="s in v.stock" :key="s.warehouse" class="me-2 tabular-nums whitespace-nowrap">{{ shortWh(s.warehouse) }} {{ s.qty }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- photos -->
          <section v-if="d.finals.length || d.photos.length || d.specs" class="bg-white rounded-xl ring-1 ring-inset ring-stone-200 p-4 flex flex-col gap-3">
            <div v-if="d.finals.length" class="flex flex-col gap-1.5">
              <h2 class="text-[14px] font-bold text-stone-900">{{ t('souk.finals') }} · {{ d.finals.length }}</h2>
              <div class="flex gap-2 flex-wrap">
                <a v-for="f in d.finals" :key="f.url" :href="f.url" target="_blank" rel="noopener" class="block w-[86px] h-[86px] rounded-lg overflow-hidden bg-stone-100">
                  <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                </a>
              </div>
            </div>
            <div v-if="d.photos.length" class="flex flex-col gap-1.5">
              <h2 class="text-[14px] font-bold text-stone-900">{{ t('souk.rawPhotos') }} · {{ d.photos.length }}</h2>
              <div class="flex gap-2 flex-wrap">
                <a v-for="p in d.photos" :key="p.url" :href="p.url" target="_blank" rel="noopener" class="block w-16 h-16 rounded-lg overflow-hidden bg-stone-100">
                  <img :src="p.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                </a>
              </div>
            </div>
            <div v-if="d.specs" class="text-[13px] text-stone-700"><b class="text-stone-900">{{ t('souk.specs') }}:</b> {{ d.specs }}</div>
          </section>

          <!-- stage by stage: who moved it and how long each stage took -->
          <details class="bg-white rounded-xl ring-1 ring-inset ring-stone-200 group">
            <summary class="min-h-[44px] px-4 flex items-center justify-between gap-2 cursor-pointer select-none text-[14px] font-bold text-stone-900 list-none">
              <span>{{ t('souk.pd.timeline') }}</span>
              <Icon name="chevron-down" :size="16" class="text-stone-500 transition-transform group-open:rotate-180" />
            </summary>
            <ol class="px-2 pb-3 flex flex-col gap-1">
              <li v-for="(r, i) in d.stages || []" :key="i"
                  class="grid grid-cols-[10px_minmax(0,1fr)_auto] gap-x-3 items-start rounded-lg px-2.5 py-2"
                  :class="r.current && !['live', 'dropped'].includes(r.stage) ? (r.late ? 'bg-rose-50' : 'bg-stone-50') : ''">
                <span class="w-2.5 h-2.5 rounded-full mt-1"
                      :class="r.late ? 'bg-rose-600' : r.current ? 'bg-stone-900' : 'bg-emerald-700'" />
                <div class="min-w-0">
                  <div class="text-[13px] font-semibold" :class="r.late ? 'text-rose-700' : 'text-stone-900'">
                    {{ t('souk.st_' + r.stage) }}
                    <span v-if="r.current && !['live', 'dropped'].includes(r.stage)" class="ms-1 text-[11px] font-bold uppercase px-1.5 py-0.5 rounded bg-stone-900 text-white">{{ t('souk.pd.now') }}</span>
                  </div>
                  <div class="text-[12px] text-stone-600 tabular-nums">
                    {{ stamp(r.at) }}<span v-if="r.by"> · {{ fill(t('souk.pd.byWho'), { n: r.by }) }}</span>
                  </div>
                </div>
                <div v-if="!['live', 'dropped'].includes(r.stage)" class="text-[12px] font-semibold tabular-nums text-end whitespace-nowrap"
                     :class="r.late ? 'text-rose-700' : 'text-stone-600'">
                  <div>{{ r.limit ? fill(t('souk.pd.daysOf'), { d: dur(r.days), l: dur(r.limit) }) : dur(r.days) }}</div>
                  <div v-if="r.late" class="text-[11px]">{{ fill(t('souk.pd.lateBy'), { d: dur(r.days - r.limit) }) }}</div>
                </div>
              </li>
            </ol>
          </details>
        </div>

        <aside class="flex-[1_1_300px] xl:max-w-[400px] min-w-0 flex flex-col gap-3.5">
          <!-- money -->
          <section class="side">
            <h2 class="side-h">{{ t('souk.money') }}</h2>
            <dl>
              <div v-for="r in moneyRows" :key="r.k" class="row">
                <dt class="text-stone-600">{{ r.k }}</dt>
                <dd class="tabular-nums text-end" :class="r.cls || 'font-semibold text-stone-900'"><bdi dir="ltr">{{ r.v }}</bdi></dd>
              </div>
            </dl>
          </section>

          <!-- stock -->
          <section v-if="d.stockSplit" class="side">
            <h2 class="side-h">{{ t('souk.pd.stock') }}</h2>
            <dl>
              <div v-for="k in ['shelf', 'studio', 'defective', 'receiving']" :key="k" class="row">
                <dt class="text-stone-600">{{ t('souk.pd.' + k) }}</dt>
                <dd class="tabular-nums font-semibold" :class="!d.stockSplit[k] ? 'text-stone-500' : k === 'defective' ? 'text-rose-700' : 'text-stone-900'">{{ fmt(d.stockSplit[k]) }}</dd>
              </div>
            </dl>
          </section>

          <!-- details -->
          <section class="side">
            <h2 class="side-h">{{ t('souk.pd.details') }}</h2>
            <dl>
              <div class="row"><dt class="text-stone-600">{{ t('souk.buyerLbl') }}</dt><dd class="text-end">{{ d.buyer || '—' }}</dd></div>
              <div v-if="d.canClaim || d.claimedBy" class="row">
                <dt class="text-stone-600">{{ t('souk.pd.whoHas') }}</dt>
                <dd class="text-end font-semibold" :class="d.claimedBy === me ? 'text-[var(--accent-700)]' : d.claimedBy ? 'text-stone-900' : 'text-stone-500 font-normal'">
                  {{ !d.claimedBy ? t('souk.pd.nobody') : d.claimedBy === me ? t('souk.pd.youHaveIt') : (d.claimedName || d.claimedBy) }}
                </dd>
              </div>
              <div class="row"><dt class="text-stone-600">Shopify</dt><dd class="mono text-[12px] text-end break-all">{{ d.shopifyId ? (d.stage === 'live' ? t('souk.pd.shopActive') : t('souk.pd.shopDraft')) + ' · ' + d.shopifyId : '—' }}</dd></div>
              <div v-if="d.contentBy" class="row"><dt class="text-stone-600">{{ t('souk.contentLbl') }}</dt><dd class="text-end">{{ d.contentBy }}</dd></div>
              <div v-if="d.publishedAt" class="row"><dt class="text-stone-600">{{ t('souk.publishedLbl') }}</dt><dd class="text-end tabular-nums">{{ d.publishedBy }} · {{ stamp(d.publishedAt) }}</dd></div>
              <div v-if="d.rejects" class="row"><dt class="text-stone-600">{{ t('souk.rejectsLbl') }}</dt><dd class="tabular-nums font-bold text-amber-700">{{ d.rejects }}</dd></div>
            </dl>
          </section>

          <!-- purchases -->
          <section class="side text-[13px]">
            <h2 class="side-h">{{ t('souk.purchases') }}</h2>
            <div v-for="p in d.purchases" :key="p.po" class="flex flex-col gap-1 py-1.5 border-b border-stone-100 last:border-0">
              <div class="flex justify-between gap-2">
                <span class="mono text-[12px]" dir="ltr">{{ p.po }}</span>
                <span class="text-stone-600 truncate">{{ p.stall }}</span>
                <span class="tabular-nums font-semibold">{{ fmt(p.amount) }}</span>
                <span class="tabular-nums text-stone-600">{{ Math.round(p.received) }}%</span>
              </div>
              <div v-if="p.pay" class="text-[12px] text-stone-600 flex items-center gap-1.5">
                <Icon :name="PAY_ICON[p.pay] || 'wallet'" :size="13" class="shrink-0 text-stone-500" />
                <span>{{ t('souk.buy.pay.' + p.pay) }}<span v-if="p.payRef" class="mono" dir="ltr"> · {{ p.payRef }}</span><span v-if="p.payDue" dir="ltr"> · {{ p.payDue }}</span></span>
              </div>
              <div v-if="p.outcome" class="text-[12px] text-stone-600 tabular-nums">
                {{ t('souk.outcomeLine')
                  .replace('{g}', sum(p.outcome.lines, 'good'))
                  .replace('{st}', sum(p.outcome.lines, 'studio'))
                  .replace('{b}', sum(p.outcome.lines, 'brokenSupplier') + sum(p.outcome.lines, 'brokenTransport') + sum(p.outcome.lines, 'brokenWarehouse'))
                  .replace('{s}', sum(p.outcome.lines, 'short')) }}
                · <span class="mono">{{ p.pr }}</span>
              </div>
              <div v-if="p.owed" class="text-[12px] font-semibold text-amber-700">
                {{ t('souk.owesShort').replace('{n}', fmt(p.owed)) }}<span v-if="p.debitNote" class="mono"> · {{ p.debitNote }}</span>
                <span v-else> · {{ t('souk.noDebitYet') }}</span>
              </div>
            </div>
            <div v-if="!d.purchases.length" class="text-stone-500">—</div>
          </section>
          <section v-if="d.receipt" class="side !p-3">
            <a :href="d.receipt" target="_blank" rel="noopener"><img :src="d.receipt" class="w-full rounded-lg" :alt="t('souk.receipt')" /></a>
          </section>

          <!-- the exit rule -->
          <section class="bg-stone-50 rounded-xl ring-1 ring-inset ring-stone-200 p-3.5 flex flex-col gap-1.5">
            <h2 class="text-[14px] font-bold text-stone-900">{{ t('souk.pd.exitTitle') }}</h2>
            <p class="text-[13px] text-stone-700 leading-[1.6]">{{ exitBody }}</p>
          </section>
        </aside>
      </div>
    </template>

    <!-- drop: won't be published -->
    <div v-if="dropOpen" class="fixed inset-0 z-50 bg-stone-900/40 flex items-end sm:items-center justify-center sm:p-4"
         role="dialog" aria-modal="true" :aria-label="t('souk.pd.dropTitle')" @click.self="dropOpen = false" @keydown.esc="dropOpen = false">
      <form class="bg-white w-full sm:max-w-md rounded-t-xl sm:rounded-xl p-4 pb-[max(1rem,env(safe-area-inset-bottom))] flex flex-col gap-3 max-h-[90vh] overflow-y-auto" @submit.prevent="drop">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-[15px] font-bold text-stone-900">{{ t('souk.pd.dropTitle') }}</h2>
            <p class="text-[13px] text-stone-600 mt-0.5">{{ t('souk.pd.dropIntro') }}</p>
          </div>
          <button type="button" class="w-11 h-11 -me-2 -mt-2 shrink-0 rounded-lg flex items-center justify-center text-stone-500" :aria-label="t('souk.cancel')" @click="dropOpen = false">
            <Icon name="x" :size="18" />
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2" role="radiogroup">
          <label v-for="w in ['return', 'clearance']" :key="w"
                 class="min-h-[56px] rounded-xl p-3 cursor-pointer ring-inset flex flex-col gap-0.5"
                 :class="why === w ? 'ring-[1.5px] ring-rose-600 bg-rose-50' : 'ring-1 ring-stone-200 bg-white'">
            <input v-model="why" type="radio" name="why" :value="w" class="sr-only" />
            <span class="text-[13px] font-bold text-stone-900">{{ w === 'return' ? t('souk.pd.whyReturn') : t('souk.pd.whyClearance') }}</span>
            <span class="text-[12px] text-stone-600">{{ w === 'return' ? t('souk.pd.whyReturnHint') : t('souk.pd.whyClearanceHint') }}</span>
          </label>
        </div>
        <textarea ref="noteEl" v-model="note" rows="3" required
                  class="w-full rounded-lg border border-stone-200 p-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-rose-400"
                  :placeholder="t('souk.pd.notePh')" />
        <div class="flex gap-2">
          <button type="button" class="btn btn-line flex-1 justify-center" @click="dropOpen = false">{{ t('souk.cancel') }}</button>
          <button type="submit" class="btn flex-1 justify-center bg-rose-600 text-white font-bold disabled:opacity-40" :disabled="busy || !why || !note.trim()">{{ t('souk.pd.confirm') }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { eventText as souEvent } from "@/lib/soukEvents";
import { useToast } from "@/composables/useToast";
import { useAuth } from "@/composables/useAuth";

const STAGES = ["buying", "bought", "photos", "studio", "content", "review", "live"];
const { t, isRTL, locale } = useI18n();
const { warn, success } = useToast();
const { user } = useAuth();
const route = useRoute();
const d = ref(null);
const loading = ref(true);
const busy = ref(false);
const stepNav = ref(null);
const me = computed(() => user.value || "");

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const PAY_ICON = { cash: "wallet", cheque: "notebook-pen", transfer: "send", credit: "clock" };
const money = (n) => Number(n || 0).toLocaleString("fr-FR", { maximumFractionDigits: 2 }) + " MAD";
const round1 = (n) => Math.round(Number(n || 0) * 10) / 10;
const fill = (s, vars) => Object.entries(vars).reduce((o, [k, v]) => o.split("{" + k + "}").join(String(v)), String(s));
const shortWh = (w) => (w || "").replace(/ - JM$/, "");
const sum = (rows, k) => (rows || []).reduce((s, r) => s + (Number(r[k]) || 0), 0);
// Comments may come back wrapped in markup; show their text only.
const plain = (s) => String(s || "").replace(/<[^>]*>/g, "").replace(/&amp;/g, "&");
// Every souk comment starts "Souk: " so the desk can find them; the page doesn't need it.
const eventText = (s) => souEvent(plain(s), locale.value, (st) => t("souk.st_" + st, st));
/** A stored site-clock stamp on the reader's clock, as "17/11 16:05". */
function stamp(s) {
  const v = local(s);
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2}))?/.exec(v || "");
  return m ? `${m[3]}/${m[2]}${m[4] ? " " + m[4] : ""}` : v || "";
}
/** Days → "6 h" under a day, "2.5 d" under ten, "12 d" after. */
function dur(days) {
  const x = Math.max(0, Number(days) || 0);
  if (x < 1) return t("souk.lb.hours").replace("{n}", Math.max(1, Math.round(x * 24)));
  return t("souk.lb.days").replace("{n}", x < 10 ? round1(x) : Math.round(x));
}
// The exit rule's text opens with the card's own heading ("If it won't be
// published: …"); under that heading, show only the rest.
const exitBody = computed(() => {
  const r = String(t("souk.exitRule")), h = String(t("souk.pd.exitTitle"));
  if (!r.startsWith(h)) return r;
  const rest = r.slice(h.length).replace(/^\s*:\s*/, "");
  return rest.charAt(0).toUpperCase() + rest.slice(1);
});
// review_drop stores the note as "<why>: <text>".
const whyOf = (note) => (/^(return|clearance):/.exec(note || "") || [])[1] || "";
const noteText = (note) => String(note || "").replace(/^(return|clearance):\s*/, "");

// The stepper: each stage of the cycle, from the card's own history.
const stepper = computed(() => {
  const rows = d.value?.stages || [];
  const stage = d.value?.stage;
  const reached = stage === "dropped" ? STAGES.indexOf(d.value?.droppedFrom) : STAGES.indexOf(stage);
  return STAGES.map((s, i) => {
    const r = [...rows].reverse().find((x) => x.stage === s);
    let state = i < reached ? "done" : i === reached ? (stage === "dropped" ? "late" : "current") : "todo";
    if (s === "live" && stage === "live") state = "done";
    if (r && r.late) state = "late";
    let sub = "";
    if (state === "current" || (r && r.current && s !== "live")) {
      sub = fill(t("souk.lb.inStage"), { d: dur(r ? r.days : d.value.age) })
        + (r && r.limit ? " · " + fill(t("souk.lb.colDeadline"), { n: r.limit }) : "");
    } else if (r) {
      sub = stamp(r.at).slice(0, 5) + (s !== "live" && r.days ? " · " + dur(r.days) : "");
    }
    return { s, state, sub, here: i === reached };
  });
});

const moneyRows = computed(() => {
  const m = d.value?.money;
  if (!m) {
    return [
      { k: t("souk.pd.boughtFor"), v: money(d.value?.cost) },
      { k: t("souk.units"), v: fmt(d.value?.units) },
    ];
  }
  const na = t("souk.pd.notAllocated");
  // Design order: what we paid, the trip's transport share, what the stall
  // owes back (green, a credit), what broke on our side, then per piece.
  return [
    { k: t("souk.pd.boughtFor"), v: money(m.paid) },
    { k: t("souk.units"), v: fmt(m.units) },
    { k: t("souk.pd.transport"), v: m.transport == null ? na : money(m.transport), cls: m.transport == null ? "text-stone-500 italic" : "" },
    { k: t("souk.pd.owed"), v: (m.owed ? "\u2212" : "") + money(m.owed), cls: m.owed ? "font-semibold text-emerald-700" : "text-stone-500" },
    { k: fill(t("souk.pd.brokenOurs"), { n: m.brokenUnits || 0 }), v: money(m.brokenOurs),
      cls: m.brokenOurs ? "font-semibold text-rose-700" : "text-stone-500" },
    { k: t("souk.pd.perPiece"), v: money(m.perPiece) },
    { k: t("souk.pd.landed"), v: m.landedPerPiece == null ? na : money(m.landedPerPiece), cls: m.landedPerPiece == null ? "text-stone-500 italic" : "" },
  ];
});

async function load() {
  loading.value = true;
  try {
    d.value = await api("souk.product", { name: route.params.name });
    // A phone shows ~3 of the 7 stages: bring the one it is in into view.
    nextTick(() => stepNav.value?.querySelector("[data-here]")?.scrollIntoView({ block: "nearest", inline: "center" }));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
watch(() => route.params.name, (n, o) => { if (n && n !== o) load(); });

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

async function claim(release) {
  busy.value = true;
  try {
    const r = await apiPost("souk.claim", { name: d.value.name, release });
    d.value.claimedBy = r?.claimedBy || "";
    d.value.claimedName = r?.claimedName || "";
    success(release ? t("souk.pd.released") : t("souk.pd.taken"));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load();
  } finally {
    busy.value = false;
  }
}

// --- drop ---------------------------------------------------------------------
// The server refuses a card still being created, so the button waits for it.
const canDropNow = computed(() => d.value?.canDrop && !["buying", "live", "dropped"].includes(d.value?.stage));
const dropOpen = ref(false);
const why = ref("");
const note = ref("");
const noteEl = ref(null);
function openDrop() {
  why.value = "";
  note.value = "";
  dropOpen.value = true;
  nextTick(() => noteEl.value?.closest("form")?.querySelector("input")?.focus());
}
async function drop() {
  if (!why.value || !note.value.trim()) return;
  busy.value = true;
  try {
    await apiPost("souk.review_drop", { name: d.value.name, why: why.value, note: note.value.trim() });
    success(t("souk.dropped"));
    dropOpen.value = false;
    await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
/* Header action — design: 36px, radius 8, 12.5px/600; 44px on touch. */
.btn {
  flex-shrink: 0;
  height: 2.75rem;
  padding-inline: 0.75rem;
  border-radius: 0.5rem;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  white-space: nowrap;
}
@media (min-width: 1024px) { .btn { height: 2.25rem; } }
.btn-accent { background: var(--accent-600); color: #fff; }
.btn-accent:hover { background: var(--accent-700); }
.btn-line { background: #fff; color: rgb(28 25 23); box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.btn-line:hover { background: rgb(250 250 249); }
:global(html[data-theme="dark"]) .btn-line { background: #292524; color: #f5f5f4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }

/* Side card — design: white, radius 12, inset ring, 14px; rows 12.5px with
   a #f5f5f4 hairline under each. */
.side {
  display: flex; flex-direction: column; gap: 6px; padding: 14px; border-radius: 12px;
  background: #fff; box-shadow: inset 0 0 0 1px rgb(231 229 228); font-size: 13px;
}
.side-h { margin-bottom: 4px; font-size: 14px; font-weight: 700; color: rgb(28 25 23); }
.row { display: flex; justify-content: space-between; gap: 10px; padding-block: 3px; box-shadow: inset 0 -1px 0 rgb(245 245 244); }
.row:last-child { box-shadow: none; }
:global(html[data-theme="dark"]) .side { background: #292524; box-shadow: inset 0 0 0 1px rgb(68 64 60); }
:global(html[data-theme="dark"]) .side-h { color: #f5f5f4; }
:global(html[data-theme="dark"]) .row { box-shadow: inset 0 -1px 0 rgb(68 64 60); }
:global(html[data-theme="dark"]) .row:last-child { box-shadow: none; }
summary::-webkit-details-marker { display: none; }
</style>
