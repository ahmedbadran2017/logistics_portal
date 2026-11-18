<template>
  <!-- One souk product: where it is in the cycle and how long each stage
       took, what it cost per piece, where its pieces are, who has it now,
       and everything that happened to it. Backend: souk.product (+ claim,
       review_drop, finish_buy for a card still being created). -->
  <div class="max-w-[1180px] mx-auto px-4 py-5 space-y-4">
    <div v-if="loading && !d" class="h-[300px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <template v-if="d">
      <header class="flex items-start justify-between gap-3 flex-wrap">
        <div class="flex gap-3 items-center min-w-0">
          <router-link :to="{ name: 'SoukBoard' }" :aria-label="t('souk.pd.back')"
                       class="w-11 h-11 shrink-0 rounded-lg bg-white ring-1 ring-stone-200 flex items-center justify-center text-stone-600">
            <Icon :name="isRTL ? 'chevron-right' : 'chevron-left'" :size="18" />
          </router-link>
          <img v-if="d.image" :src="d.image" class="w-14 h-14 shrink-0 rounded-xl object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-14 h-14 shrink-0 rounded-xl bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center text-stone-300">
            <Icon name="image" :size="20" />
          </div>
          <div class="min-w-0">
            <h1 class="text-[19px] font-bold text-stone-900 leading-tight line-clamp-2">{{ d.title }}</h1>
            <div class="text-[11.5px] text-stone-500 mt-0.5 break-words">
              <span class="font-mono" dir="ltr">{{ d.name }}</span>
              <span v-if="d.stall"> · {{ t('souk.stallShort') }} {{ d.stall }}</span>
              <span v-if="d.brand"> · {{ t('souk.siteShort') }} {{ d.brand }}</span>
              <span v-if="d.trip"> · {{ t('souk.tripNo').replace('{n}', d.trip) }}</span>
            </div>
          </div>
        </div>
        <div class="flex gap-2 flex-wrap">
          <button v-if="d.stage === 'buying'" class="btn bg-stone-900 text-white font-bold disabled:opacity-40" :disabled="busy" @click="finish">{{ t('souk.retry') }}</button>
          <router-link v-if="d.canReceive && d.stage === 'bought' && d.po" :to="{ name: 'SoukReceive', params: { po: d.po } }"
                       class="btn bg-[var(--accent-600)] text-white font-bold">{{ t('souk.receiveBtn') }}</router-link>
          <router-link v-if="d.canPhoto && d.stage === 'photos'" :to="{ name: 'SoukPhoto', params: { name: d.name } }"
                       class="btn bg-stone-900 text-white font-bold">{{ t('souk.shootBtn') }}</router-link>
          <router-link v-if="d.canStudio && d.stage === 'studio'" :to="{ name: 'SoukStudio', params: { name: d.name } }"
                       class="btn bg-stone-900 text-white font-bold">{{ t('souk.finalsBtn') }}</router-link>
          <router-link v-if="d.canContent && d.stage === 'content'" :to="{ name: 'SoukContent', params: { name: d.name } }"
                       class="btn bg-stone-900 text-white font-bold">{{ t('souk.contentBtn') }}</router-link>
          <router-link v-if="d.canReview && d.stage === 'review'" :to="{ name: 'SoukReview', params: { name: d.name } }"
                       class="btn bg-[var(--accent-600)] text-white font-bold">{{ t('souk.reviewBtn') }}</router-link>
          <!-- claim / release -->
          <template v-if="d.canClaim && d.stage !== 'buying'">
            <button v-if="!d.claimedBy || (d.claimedBy !== me && d.canDrop)" class="btn font-semibold bg-white ring-1 ring-stone-300 disabled:opacity-40" :disabled="busy" @click="claim(0)">
              <Icon name="hand" :size="14" />{{ t('souk.pd.claim') }}
            </button>
            <button v-if="d.claimedBy && (d.claimedBy === me || d.canDrop)" class="btn font-semibold bg-white ring-1 ring-stone-300 disabled:opacity-40" :disabled="busy" @click="claim(1)">
              <Icon name="unlock" :size="14" />{{ t('souk.pd.release') }}
            </button>
          </template>
          <a v-if="d.shopifyAdmin" :href="d.shopifyAdmin" target="_blank" rel="noopener" class="btn font-semibold bg-white ring-1 ring-stone-300">
            Shopify<Icon name="external-link" :size="13" />
          </a>
          <router-link v-if="d.canBuy && d.stage !== 'buying'" :to="{ name: 'SoukBuy', query: { again: d.name, kind: 'souk' } }"
                       class="btn font-semibold bg-white ring-1 ring-stone-300">{{ t('souk.buyAgain') }}</router-link>
          <button v-if="canDropNow" class="btn font-semibold bg-white ring-1 ring-rose-200 text-rose-700" @click="openDrop">{{ t('souk.pd.drop') }}</button>
        </div>
      </header>

      <div v-if="d.error" class="bg-rose-50 ring-1 ring-rose-200 rounded-xl p-3 text-[12px] text-rose-800 font-mono break-words">{{ d.error }}</div>

      <div v-if="d.stage === 'dropped'" class="bg-stone-100 ring-1 ring-stone-200 rounded-xl p-3 text-[12.5px] text-stone-800 space-y-0.5">
        <div class="font-bold">
          {{ d.droppedFrom ? fill(t('souk.pd.droppedBanner'), { s: t('souk.st_' + d.droppedFrom) }) : t('souk.st_dropped') }}
          <span v-if="whyOf(d.reviewNote)" class="font-semibold text-stone-600"> · {{ t('souk.lb.why_' + whyOf(d.reviewNote)) }}</span>
        </div>
        <div v-if="noteText(d.reviewNote)" class="break-words">{{ noteText(d.reviewNote) }}</div>
      </div>

      <!-- stages -->
      <nav class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 overflow-x-auto">
        <ol class="flex gap-1.5 min-w-[680px]">
          <li v-for="st in stepper" :key="st.s" class="flex-1 space-y-1.5">
            <div class="h-1.5 rounded-full"
                 :class="{ done: 'bg-[var(--accent-600)]', current: 'bg-stone-900', late: 'bg-rose-500', todo: 'bg-stone-200' }[st.state]" />
            <div class="text-[11.5px] font-bold"
                 :class="st.state === 'late' ? 'text-rose-700' : st.state === 'todo' ? 'text-stone-400' : 'text-stone-900'">{{ t('souk.st_' + st.s) }}</div>
            <div class="text-[10.5px] tabular-nums" :class="st.state === 'late' ? 'text-rose-700' : 'text-stone-500'">{{ st.sub }}</div>
          </li>
        </ol>
      </nav>

      <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] gap-4 items-start">
        <div class="space-y-4 min-w-0">
          <!-- stage by stage -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4">
            <h2 class="text-[13px] font-bold mb-2">{{ t('souk.pd.timeline') }}</h2>
            <ol class="space-y-1">
              <li v-for="(r, i) in d.stages || []" :key="i"
                  class="grid grid-cols-[12px_minmax(0,1fr)_auto] gap-x-3 items-start rounded-xl px-2.5 py-2"
                  :class="r.current && !['live', 'dropped'].includes(r.stage) ? (r.late ? 'bg-rose-50 ring-1 ring-rose-200' : 'bg-[var(--accent-50)] ring-1 ring-[var(--accent-200)]') : ''">
                <span class="w-2.5 h-2.5 rounded-full mt-1"
                      :class="r.late ? 'bg-rose-500' : r.current ? 'bg-stone-900' : 'bg-[var(--accent-600)]'" />
                <div class="min-w-0">
                  <div class="text-[12.5px] font-semibold" :class="r.late ? 'text-rose-800' : 'text-stone-900'">
                    {{ t('souk.st_' + r.stage) }}
                    <span v-if="r.current && !['live', 'dropped'].includes(r.stage)" class="ms-1 text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-stone-900 text-white">{{ t('souk.pd.now') }}</span>
                  </div>
                  <div class="text-[11px] text-stone-500 tabular-nums">
                    {{ stamp(r.at) }}<span v-if="r.by"> · {{ fill(t('souk.pd.byWho'), { n: r.by }) }}</span>
                  </div>
                </div>
                <div v-if="!['live', 'dropped'].includes(r.stage)" class="text-[11.5px] font-semibold tabular-nums text-end whitespace-nowrap"
                     :class="r.late ? 'text-rose-700' : 'text-stone-600'">
                  <div>{{ r.limit ? fill(t('souk.pd.daysOf'), { d: dur(r.days), l: dur(r.limit) }) : dur(r.days) }}</div>
                  <div v-if="r.late" class="text-[10.5px]">{{ fill(t('souk.pd.lateBy'), { d: dur(r.days - r.limit) }) }}</div>
                </div>
              </li>
            </ol>
          </section>

          <!-- variants -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl overflow-hidden">
            <div class="px-4 py-2.5 border-b border-stone-100 text-[13px] font-bold">{{ t('souk.variants') }} · {{ d.variants.length }}</div>
            <div class="overflow-x-auto">
              <table class="w-full min-w-[520px] text-[12px]">
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
                    <td class="px-4 py-2 font-mono font-bold" dir="ltr">{{ v.sku }}</td>
                    <td class="px-2 text-stone-600">{{ [v.colorFr, v.sizeLabel].filter(Boolean).join(' · ') || '—' }}</td>
                    <td class="px-2 text-center tabular-nums">{{ v.qty }}</td>
                    <td class="px-2 text-center tabular-nums">{{ v.cost }}</td>
                    <td class="px-2 text-center tabular-nums">{{ v.price }}</td>
                    <td class="px-4 text-stone-600">
                      <span v-if="!v.stock.length" class="text-stone-400">—</span>
                      <span v-for="s in v.stock" :key="s.warehouse" class="me-2 tabular-nums whitespace-nowrap">{{ shortWh(s.warehouse) }} {{ s.qty }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <!-- photos -->
          <section v-if="d.finals.length || d.photos.length || d.specs" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
            <div v-if="d.finals.length" class="space-y-1.5">
              <h2 class="text-[13px] font-bold">{{ t('souk.finals') }} · {{ d.finals.length }}</h2>
              <div class="flex gap-2 flex-wrap">
                <a v-for="f in d.finals" :key="f.url" :href="f.url" target="_blank" rel="noopener" class="block w-[86px] h-[86px] rounded-lg overflow-hidden ring-1 ring-stone-200">
                  <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                </a>
              </div>
            </div>
            <div v-if="d.photos.length" class="space-y-1.5">
              <h2 class="text-[13px] font-bold">{{ t('souk.rawPhotos') }} · {{ d.photos.length }}</h2>
              <div class="flex gap-2 flex-wrap">
                <a v-for="p in d.photos" :key="p.url" :href="p.url" target="_blank" rel="noopener" class="block w-[64px] h-[64px] rounded-lg overflow-hidden ring-1 ring-stone-200">
                  <img :src="p.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                </a>
              </div>
            </div>
            <div v-if="d.specs" class="text-[12px] text-stone-600"><b>{{ t('souk.specs') }}:</b> {{ d.specs }}</div>
          </section>

          <!-- the raw log, secondary -->
          <details class="bg-white ring-1 ring-stone-200/70 rounded-2xl group">
            <summary class="min-h-[44px] px-4 flex items-center justify-between gap-2 cursor-pointer select-none text-[13px] font-bold list-none">
              <span>{{ fill(t('souk.pd.log'), { n: d.events.length }) }}</span>
              <Icon name="chevron-down" :size="16" class="text-stone-400 transition-transform group-open:rotate-180" />
            </summary>
            <div class="px-4 pb-3 space-y-0.5">
              <div v-for="(e, i) in d.events" :key="i" class="grid grid-cols-[92px_minmax(0,1fr)] gap-3 py-1.5 border-t border-stone-100 first:border-0">
                <span class="text-[11px] text-stone-500 tabular-nums">{{ stamp(e.at) }}</span>
                <div class="min-w-0">
                  <div class="text-[12.5px] text-stone-900 break-words">{{ plain(e.text) }}</div>
                  <div class="text-[11px] text-stone-500">{{ e.by }}</div>
                </div>
              </div>
              <div v-if="!d.events.length" class="text-[12px] text-stone-400 py-2">{{ t('souk.pd.noLog') }}</div>
            </div>
          </details>
        </div>

        <aside class="space-y-4 min-w-0">
          <!-- money -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 text-[12.5px]">
            <h2 class="font-bold text-[13px] mb-1.5">{{ t('souk.money') }}</h2>
            <dl class="divide-y divide-stone-100">
              <div v-for="r in moneyRows" :key="r.k" class="flex justify-between gap-3 py-1.5">
                <dt class="text-stone-500">{{ r.k }}</dt>
                <dd class="tabular-nums text-end" :class="r.cls || 'font-semibold text-stone-900'">{{ r.v }}</dd>
              </div>
            </dl>
          </section>

          <!-- stock -->
          <section v-if="d.stockSplit" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 text-[12.5px]">
            <h2 class="font-bold text-[13px] mb-1.5">{{ t('souk.pd.stock') }}</h2>
            <dl class="divide-y divide-stone-100">
              <div v-for="k in ['shelf', 'studio', 'defective', 'receiving']" :key="k" class="flex justify-between gap-3 py-1.5">
                <dt class="text-stone-500">{{ t('souk.pd.' + k) }}</dt>
                <dd class="tabular-nums font-semibold" :class="!d.stockSplit[k] ? 'text-stone-300' : k === 'defective' ? 'text-rose-700' : 'text-stone-900'">{{ fmt(d.stockSplit[k]) }}</dd>
              </div>
            </dl>
          </section>

          <!-- details -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 text-[12.5px]">
            <h2 class="font-bold text-[13px] mb-1.5">{{ t('souk.pd.details') }}</h2>
            <dl class="divide-y divide-stone-100">
              <div class="flex justify-between gap-3 py-1.5"><dt class="text-stone-500">{{ t('souk.buyerLbl') }}</dt><dd class="text-end">{{ d.buyer || '—' }}</dd></div>
              <div v-if="d.canClaim || d.claimedBy" class="flex justify-between gap-3 py-1.5">
                <dt class="text-stone-500">{{ t('souk.pd.whoHas') }}</dt>
                <dd class="text-end font-semibold" :class="d.claimedBy === me ? 'text-[var(--accent-700)]' : d.claimedBy ? 'text-stone-900' : 'text-stone-400 font-normal'">
                  {{ !d.claimedBy ? t('souk.pd.nobody') : d.claimedBy === me ? t('souk.pd.youHaveIt') : (d.claimedName || d.claimedBy) }}
                </dd>
              </div>
              <div class="flex justify-between gap-3 py-1.5"><dt class="text-stone-500">Shopify</dt><dd class="font-mono text-end break-all">{{ d.shopifyId ? (d.stage === 'live' ? 'Active' : 'Draft') + ' · ' + d.shopifyId : '—' }}</dd></div>
              <div v-if="d.contentBy" class="flex justify-between gap-3 py-1.5"><dt class="text-stone-500">{{ t('souk.contentLbl') }}</dt><dd class="text-end">{{ d.contentBy }}</dd></div>
              <div v-if="d.publishedAt" class="flex justify-between gap-3 py-1.5"><dt class="text-stone-500">{{ t('souk.publishedLbl') }}</dt><dd class="text-end tabular-nums">{{ d.publishedBy }} · {{ stamp(d.publishedAt) }}</dd></div>
              <div v-if="d.rejects" class="flex justify-between gap-3 py-1.5"><dt class="text-stone-500">{{ t('souk.rejectsLbl') }}</dt><dd class="tabular-nums font-bold text-amber-800">{{ d.rejects }}</dd></div>
            </dl>
          </section>

          <!-- purchases -->
          <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2 text-[12px]">
            <h2 class="font-bold text-[13px]">{{ t('souk.purchases') }}</h2>
            <div v-for="p in d.purchases" :key="p.po" class="space-y-1 pb-2 border-b border-stone-100 last:border-0">
              <div class="flex justify-between gap-2">
                <span class="font-mono" dir="ltr">{{ p.po }}</span>
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

    <!-- drop: won't be published -->
    <div v-if="dropOpen" class="fixed inset-0 z-50 bg-stone-900/40 flex items-end sm:items-center justify-center sm:p-4"
         role="dialog" aria-modal="true" :aria-label="t('souk.pd.dropTitle')" @click.self="dropOpen = false" @keydown.esc="dropOpen = false">
      <form class="bg-white w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl p-4 pb-[max(1rem,env(safe-area-inset-bottom))] space-y-3 max-h-[90vh] overflow-y-auto" @submit.prevent="drop">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-[15px] font-bold text-stone-900">{{ t('souk.pd.dropTitle') }}</h2>
            <p class="text-[12px] text-stone-500 mt-0.5">{{ t('souk.pd.dropIntro') }}</p>
          </div>
          <button type="button" class="w-11 h-11 -me-2 -mt-2 shrink-0 rounded-lg flex items-center justify-center text-stone-500" :aria-label="t('souk.cancel')" @click="dropOpen = false">
            <Icon name="x" :size="18" />
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2" role="radiogroup">
          <label v-for="w in ['return', 'clearance']" :key="w"
                 class="min-h-[56px] rounded-xl p-3 cursor-pointer ring-1 flex flex-col gap-0.5"
                 :class="why === w ? 'ring-2 ring-rose-500 bg-rose-50' : 'ring-stone-200 bg-white'">
            <input v-model="why" type="radio" name="why" :value="w" class="sr-only" />
            <span class="text-[12.5px] font-bold text-stone-900">{{ w === 'return' ? t('souk.pd.whyReturn') : t('souk.pd.whyClearance') }}</span>
            <span class="text-[11px] text-stone-500">{{ w === 'return' ? t('souk.pd.whyReturnHint') : t('souk.pd.whyClearanceHint') }}</span>
          </label>
        </div>
        <textarea ref="noteEl" v-model="note" rows="3" required
                  class="w-full rounded-xl ring-1 ring-stone-300 p-3 text-[13px] focus:outline-none focus:ring-2 focus:ring-rose-400"
                  :placeholder="t('souk.pd.notePh')" />
        <div class="flex gap-2">
          <button type="button" class="btn font-semibold flex-1 justify-center bg-white ring-1 ring-stone-300" @click="dropOpen = false">{{ t('souk.cancel') }}</button>
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
import { useToast } from "@/composables/useToast";
import { useAuth } from "@/composables/useAuth";

const STAGES = ["buying", "bought", "photos", "studio", "content", "review", "live"];
const { t, isRTL } = useI18n();
const { warn, success } = useToast();
const { user } = useAuth();
const route = useRoute();
const d = ref(null);
const loading = ref(true);
const busy = ref(false);
const me = computed(() => user.value || "");

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const money = (n) => Number(n || 0).toLocaleString("fr-FR", { maximumFractionDigits: 2 }) + " MAD";
const round1 = (n) => Math.round(Number(n || 0) * 10) / 10;
const fill = (s, vars) => Object.entries(vars).reduce((o, [k, v]) => o.split("{" + k + "}").join(String(v)), String(s));
const shortWh = (w) => (w || "").replace(/ - JM$/, "");
const sum = (rows, k) => (rows || []).reduce((s, r) => s + (Number(r[k]) || 0), 0);
// Comments may come back wrapped in markup; show their text only.
const plain = (s) => String(s || "").replace(/<[^>]*>/g, "").replace(/&amp;/g, "&");
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
    return { s, state, sub };
  });
});

const moneyRows = computed(() => {
  const m = d.value?.money;
  if (!m) {
    return [
      { k: t("souk.paid"), v: money(d.value?.cost) },
      { k: t("souk.units"), v: fmt(d.value?.units) },
    ];
  }
  const na = t("souk.pd.notAllocated");
  return [
    { k: t("souk.paid"), v: money(m.paid) },
    { k: t("souk.units"), v: fmt(m.units) },
    { k: t("souk.pd.perPiece"), v: money(m.perPiece) },
    { k: t("souk.pd.transport"), v: m.transport == null ? na : money(m.transport), cls: m.transport == null ? "text-stone-400 italic" : "" },
    { k: t("souk.pd.landed"), v: m.landedPerPiece == null ? na : money(m.landedPerPiece), cls: m.landedPerPiece == null ? "text-stone-400 italic" : "" },
    { k: fill(t("souk.pd.brokenOurs"), { n: m.brokenUnits || 0 }), v: money(m.brokenOurs),
      cls: m.brokenOurs ? "font-semibold text-rose-700" : "text-stone-400" },
    { k: t("souk.pd.owed"), v: money(m.owed), cls: m.owed ? "font-semibold text-[var(--accent-700)]" : "text-stone-400" },
  ];
});

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
.btn {
  height: 2.75rem;
  padding-inline: 0.875rem;
  border-radius: 0.5rem;
  font-size: 12.5px;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  white-space: nowrap;
}
summary::-webkit-details-marker { display: none; }
</style>
