<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1200px] mx-auto">
    <!-- hero -->
    <header class="ex-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3.5">
          <span class="ex-hero-icon"><Icon name="refresh-cw" :size="22" /></span>
          <div>
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('ex.title') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5">{{ t('ex.intro') }}</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <input ref="orderInput" v-model="newOrder" :placeholder="t('ex.orderPh')" maxlength="30"
                 class="h-10 w-[180px] ps-3 pe-3 rounded-xl bg-white ring-1 ring-stone-200/80 text-[12.5px] font-mono focus:ring-2 focus:ring-amber-300 outline-none"
                 @keyup.enter="start" />
          <!-- Not disabled when empty. Greyed out on arrival, it read as
               decoration and the question "where do I start an exchange?"
               has a button sitting right there. Empty now focuses the box. -->
          <button class="ex-new" :disabled="starting" @click="start">
            <Icon name="plus" :size="15" class="inline -mt-px me-1" />{{ starting ? '…' : t('ex.start') }}
          </button>
        </div>
      </div>
    </header>

    <!-- tabs + search -->
    <div class="flex items-center gap-3 flex-wrap">
      <div class="ex-seg">
        <button v-for="tb in TABS" :key="tb.key" class="ex-seg-btn" :class="tab === tb.key ? 'ex-seg-on' : ''"
                @click="tab = tb.key; page = 1; load()">
          <Icon :name="tb.icon" :size="14" />
          <span>{{ t(tb.label) }}</span>
          <span class="ex-seg-count" :class="tab === tb.key ? tb.onColor : 'bg-stone-200/70 text-stone-500'">
            {{ data?.counts?.[tb.key] ?? '–' }}
          </span>
        </button>
      </div>
      <div class="relative ms-auto">
        <Icon name="search" :size="13" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input v-model="q" :placeholder="t('ex.searchPh')" @input="debouncedLoad"
               class="h-10 w-[240px] ps-9 pe-3 text-[12.5px] bg-white rounded-xl ring-1 ring-stone-200/80 focus:ring-2 focus:ring-amber-300 outline-none" />
      </div>
    </div>

    <!-- rows -->
    <div v-if="loading" class="space-y-2.5">
      <div v-for="n in 5" :key="n" class="h-[80px] rounded-2xl ex-shimmer" />
    </div>
    <div v-else-if="loadError" class="ex-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-rose-50 text-rose-500 mb-3"><Icon name="alert-triangle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[12px] text-stone-400 mt-1 font-mono max-w-[420px] mx-auto break-words">{{ loadError }}</div>
    </div>
    <div v-else-if="!rows.length" class="ex-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('ex.empty') }}</div>
      <div class="text-[12.5px] text-stone-400 mt-1">{{ t('ex.emptyHint') }}</div>
    </div>

    <TransitionGroup v-else name="exrow" tag="div" class="space-y-2.5 relative">
      <div v-for="r in rows" :key="r.name" class="ex-card rounded-2xl p-4">
        <div class="flex items-center gap-3.5 flex-wrap">
          <span class="ex-avatar"><Icon name="refresh-cw" :size="16" /></span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[13.5px] font-bold text-stone-900 truncate max-w-[220px]">{{ r.customer || '—' }}</span>
              <span class="font-mono text-[11px] text-stone-400">{{ r.order }}</span>
              <span v-if="r.exOrder" class="font-mono text-[11px] text-amber-600">→ {{ r.exOrder }}</span>
              <span class="ex-chip" :class="statusClass(r.status)">{{ t('ex.st' + r.status.replace(/ /g, ''), r.status) }}</span>
              <span v-if="r.status === 'Label Generated' && r.settlement === 'Pending' && r.difference"
                    class="ex-chip" :class="r.difference > 0 ? 'text-emerald-700 bg-emerald-50' : 'text-rose-700 bg-rose-50'">
                {{ r.difference > 0 ? t('ex.collect') : t('ex.refund') }} {{ Math.abs(r.difference) }} MAD
              </span>
            </div>
            <div class="flex items-center gap-2.5 text-[11.5px] text-stone-500 tabular-nums mt-1 flex-wrap">
              <span v-if="r.phone" class="font-mono">{{ r.phone }}</span>
              <span v-if="r.city" class="inline-flex items-center gap-1"><Icon name="map-pin" :size="11" class="text-stone-300" />{{ r.city }}</span>
              <span v-if="r.awb" class="font-mono text-[10.5px] text-amber-700">{{ r.awb }}</span>
              <!-- The reason IS the money: it decides the 25 MAD and whether
                   the difference is zero. The board never showed it, so the
                   edit panel reopened blank on a required field and the agent
                   re-picked from memory. -->
              <span class="inline-flex items-center gap-1"
                    :class="r.reason ? 'text-stone-500' : 'text-stone-300'">
                <Icon name="help-circle" :size="11" class="text-stone-300" />
                {{ r.reason ? t('ex.r_' + r.reason, r.reason) : t('ex.noneYet') }}
              </span>
              <span class="inline-flex items-center gap-1 text-stone-400"><Icon name="clock" :size="11" />{{ ageLabel(r.ageH) }}</span>
            </div>
            <div v-if="r.itemsText" class="text-[11.5px] text-stone-500 truncate max-w-[560px] mt-1" :title="r.itemsText" dir="auto">
              <Icon name="package" :size="11" class="inline -mt-px me-1 text-stone-300" />{{ r.itemsText }}
            </div>
          </div>
          <div class="flex items-center gap-1.5 flex-wrap">
            <a v-if="r.labelUrl" :href="r.labelUrl" target="_blank" class="ex-act ex-act-soft text-stone-600" :title="t('ex.label')">
              <Icon name="printer" :size="15" />
            </a>
            <!-- On every tab, not just the editable one: a settled exchange is
                 exactly when somebody asks what was sent and who decided it. -->
            <button class="ex-act ex-act-soft text-stone-600" :title="t('ex.details')"
                    :class="detailFor === r.name ? 'ring-2' : ''" @click="toggleDetail(r)">
              <Icon name="list" :size="15" />
            </button>
            <template v-if="tab === 'waiting'">
              <button class="ex-act ex-act-soft text-amber-700" :title="t('ex.editItems')"
                      :class="editFor === r.name ? 'ring-2' : ''" @click="toggleEdit(r)">
                <Icon name="edit" :size="15" />
              </button>
              <button class="ex-act ex-act-main" :disabled="busy === r.name || !r.itemsText" @click="generate(r)">
                <Icon name="zap" :size="14" class="inline -mt-px me-1" />{{ busy === r.name ? '…' : t('ex.generate') }}
              </button>
            </template>
            <button v-else-if="tab === 'labeled'" class="ex-act ex-act-main" :disabled="busy === r.name" @click="settle(r)">
              <Icon name="check" :size="14" class="inline -mt-px me-1" />{{ t('ex.settle') }}
            </button>
          </div>
        </div>

        <!-- details + history -->
        <Transition name="exslide">
          <div v-if="detailFor === r.name" class="bg-stone-50 rounded-xl p-3.5 mt-3">
            <div v-if="loadingDetail" class="h-16 rounded-lg ex-shimmer" />
            <div v-else-if="detailErr" class="text-[12px] text-rose-600">{{ detailErr }}</div>
            <div v-else-if="detail" class="grid gap-4 md:grid-cols-3">
              <!-- what they have vs what goes out: the comparison the agent is
                   actually making, and the board never showed the left half. -->
              <div class="space-y-1.5">
                <h4 class="ex-dh">{{ t('ex.dHas') }}</h4>
                <p v-for="(x, i) in detail.has" :key="'h' + i" class="text-[11.5px] text-stone-600" dir="auto">
                  <span class="tabular-nums text-stone-400">{{ x.qty }}×</span>
                  {{ x.name }}
                  <span class="tabular-nums text-stone-400">· {{ x.rate }} MAD</span>
                </p>
                <p v-if="!detail.has.length" class="text-[11.5px] text-stone-400">{{ t('ex.dNone') }}</p>
              </div>
              <div class="space-y-1.5">
                <h4 class="ex-dh">{{ t('ex.dSending') }}</h4>
                <p v-for="(x, i) in detail.sending" :key="'s' + i" class="text-[11.5px] text-stone-600" dir="auto">
                  <span class="tabular-nums text-stone-400">{{ x.qty }}×</span>
                  {{ x.name }}
                  <span class="tabular-nums text-stone-400">· {{ x.rate }} MAD</span>
                </p>
                <p v-if="!detail.sending.length" class="text-[11.5px] text-stone-400">{{ t('ex.dPureReturn') }}</p>
              </div>
              <!-- The money, itemised. The row shows one number; this says how
                   it was reached, including the pickup fee by name. -->
              <div class="space-y-1.5">
                <h4 class="ex-dh">{{ t('ex.dMoney') }}</h4>
                <p class="text-[11.5px] text-stone-600 flex justify-between gap-3">
                  <span>{{ t('ex.dPaid') }}</span><span class="tabular-nums">{{ detail.originalTotal }}</span>
                </p>
                <p v-for="(c, i) in detail.charges" :key="'c' + i"
                   class="text-[11.5px] text-stone-600 flex justify-between gap-3">
                  <span dir="auto">{{ c.label }}</span><span class="tabular-nums">{{ c.amount }}</span>
                </p>
                <p class="text-[11.5px] text-stone-600 flex justify-between gap-3">
                  <span>{{ t('ex.dGoingOut') }}</span><span class="tabular-nums">{{ detail.exchangeTotal }}</span>
                </p>
                <p class="text-[12px] font-semibold flex justify-between gap-3 pt-1 border-t border-stone-200"
                   :class="Math.round(detail.difference) === 0 ? 'text-emerald-700'
                           : (detail.difference > 0 ? 'text-amber-700' : 'text-rose-700')">
                  <span>{{ Math.round(detail.difference) === 0 ? t('ex.settleNone')
                          : (detail.difference > 0 ? t('ex.collect') : t('ex.refund')) }}</span>
                  <span v-if="Math.round(detail.difference) !== 0" class="tabular-nums">
                    {{ Math.abs(Math.round(detail.difference)) }} MAD
                  </span>
                </p>
              </div>
              <!-- both parcels: the one that went out and the one coming back -->
              <div class="md:col-span-3 flex items-center gap-4 flex-wrap text-[11.5px] pt-1 border-t border-stone-200">
                <span class="text-stone-400">{{ t('ex.dOldParcel') }}</span>
                <a v-if="detail.old.url" :href="detail.old.url" target="_blank"
                   class="font-mono text-stone-600 hover:text-amber-700">{{ detail.old.awb }}</a>
                <span v-else class="font-mono text-stone-400">{{ detail.old.awb || '—' }}</span>
                <span class="text-stone-400">{{ t('ex.dNewParcel') }}</span>
                <a v-if="detail.new.url" :href="detail.new.url" target="_blank"
                   class="font-mono text-amber-700 hover:underline">{{ detail.new.awb }}</a>
                <span v-else class="font-mono text-stone-400">{{ detail.new.awb || '—' }}</span>
                <span v-if="detail.address" class="text-stone-500 ms-auto" dir="auto">
                  <Icon name="map-pin" :size="11" class="inline -mt-px me-1 text-stone-300" />{{ detail.address }}
                </span>
              </div>
              <!-- History. 2,996 Version rows exist across the site and none of
                   them were readable anywhere in the portal until now. -->
              <div class="md:col-span-3 pt-1 border-t border-stone-200">
                <h4 class="ex-dh mb-1.5">{{ t('ex.dHistory') }}</h4>
                <ol class="space-y-1">
                  <li v-for="(e, i) in detail.events" :key="'e' + i"
                      class="text-[11.5px] flex items-start gap-2.5 flex-wrap">
                    <span class="tabular-nums text-stone-400 w-[112px] shrink-0">{{ e.at }}</span>
                    <span class="font-semibold text-stone-600 w-[92px] shrink-0 truncate">{{ e.who }}</span>
                    <span class="ex-ev">{{ t('ex.ev_' + e.what, e.what) }}</span>
                    <span class="text-stone-500 break-all" dir="auto">{{ e.detail }}</span>
                  </li>
                </ol>
              </div>
            </div>
          </div>
        </Transition>

        <!-- items editor -->
        <Transition name="exslide">
          <div v-if="editFor === r.name" class="bg-amber-50/50 rounded-xl p-3 mt-3 space-y-2">
            <!-- Why it is coming back. This is the only question about money
                 the agent answers: the wording carries whose fault it was,
                 and the 25 MAD pickup follows from it. -->
            <div class="flex items-center gap-2 flex-wrap">
              <select v-model="editReason"
                      class="h-9 px-2.5 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] focus:outline-none">
                <option value="">{{ t('ex.whyPh') }}</option>
                <option v-for="rs in REASONS" :key="rs" :value="rs">{{ t('ex.r_' + rs) }}</option>
              </select>
              <span v-if="editReason" class="text-[11.5px] font-semibold"
                    :class="feeApplies ? 'text-amber-700' : 'text-emerald-700'">
                {{ feeApplies ? t('ex.feeYes').replace('{n}', String(fee)) : t('ex.feeNo') }}
              </span>
              <span class="ms-auto" />
            </div>

            <div v-if="loadingLines" class="h-20 rounded-lg ex-shimmer" />
            <div v-else class="grid gap-4 md:grid-cols-2">
              <!-- COMING BACK — picked off the order, never typed.
                   Shopify's returnLineItems are a quantity against a line of
                   the order; you cannot name a product that was never bought.
                   Typing a code from memory is how you get "Unknown item". -->
              <div class="space-y-1.5">
                <h4 class="ex-dh">{{ t('ex.backTitle') }}</h4>
                <label v-for="(ln, i) in backLines" :key="'b' + i"
                       class="flex items-center gap-2.5 p-1.5 rounded-lg cursor-pointer transition-colors"
                       :class="ln.take ? 'bg-white ring-1 ring-amber-200' : 'hover:bg-white/60'">
                  <input v-model="ln.take" type="checkbox" class="accent-amber-600 w-4 h-4 shrink-0"
                         @change="onTakeChanged" />
                  <img v-if="ln.image" :src="ln.image" alt="" loading="lazy"
                       class="w-9 h-9 rounded-md object-cover bg-stone-100 shrink-0" />
                  <span v-else class="w-9 h-9 rounded-md bg-stone-100 shrink-0 inline-flex items-center justify-center text-stone-300">
                    <Icon name="package" :size="14" />
                  </span>
                  <span class="min-w-0 flex-1">
                    <span class="block text-[11.5px] text-stone-700 truncate" dir="auto">{{ ln.name }}</span>
                    <span class="block text-[10.5px] text-stone-400 tabular-nums">
                      {{ ln.ordered }}× · {{ ln.rate }} MAD
                    </span>
                  </span>
                  <input v-if="ln.take" v-model.number="ln.qty" type="number" min="1" :max="ln.ordered"
                         class="w-[60px] h-8 ps-2 rounded-lg bg-white ring-1 ring-amber-200 text-[12px] tabular-nums focus:outline-none"
                         @click.prevent.stop @change="quoteSoon(0)" />
                </label>
                <p v-if="!backLines.length" class="text-[11.5px] text-stone-400">{{ t('ex.dNone') }}</p>
                <p class="text-[10.5px] text-stone-400">{{ t('ex.backHint') }}</p>
              </div>

              <!-- GOING OUT — three answers, because there are only three.
                   Shopify keeps exchangeLineItems as a separate list from the
                   returned ones, and most of ours are the same item again. -->
              <div class="space-y-1.5">
                <h4 class="ex-dh">{{ t('ex.outTitle') }}</h4>
                <label v-for="m in OUT_MODES" :key="m"
                       class="flex items-start gap-2.5 p-1.5 rounded-lg cursor-pointer transition-colors"
                       :class="outMode === m ? 'bg-white ring-1 ring-amber-200' : 'hover:bg-white/60'">
                  <input v-model="outMode" :value="m" type="radio" class="accent-amber-600 w-4 h-4 mt-0.5 shrink-0"
                         @change="onModeChanged" />
                  <span class="min-w-0">
                    <span class="block text-[12px] font-semibold text-stone-700">{{ t('ex.out_' + m) }}</span>
                    <span class="block text-[10.5px] text-stone-400">{{ t('ex.outHint_' + m) }}</span>
                  </span>
                </label>

                <!-- the only case that needs a product we do not already know -->
                <div v-if="outMode === 'other'" class="pt-1 space-y-1.5">
                  <div class="relative">
                    <Icon name="search" :size="13" class="absolute start-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
                    <input v-model="pickQ" :placeholder="t('ex.searchItemPh')" maxlength="80"
                           @input="searchSoon"
                           class="w-full h-9 ps-8 pe-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] focus:outline-none" />
                  </div>
                  <div v-if="searching" class="h-8 rounded-lg ex-shimmer" />
                  <ul v-else-if="hits.length" class="max-h-[168px] overflow-auto space-y-0.5">
                    <li v-for="h in hits" :key="h.code">
                      <button class="w-full flex items-center gap-2 p-1.5 rounded-lg text-start hover:bg-white transition-colors"
                              @click="addPicked(h)">
                        <span class="min-w-0 flex-1">
                          <span class="block text-[11.5px] text-stone-700 truncate" dir="auto">{{ h.name }}</span>
                          <span class="block text-[10.5px] text-stone-400 font-mono">{{ h.code }}</span>
                        </span>
                        <span class="text-[10.5px] tabular-nums shrink-0"
                              :class="h.avail > 0 ? 'text-emerald-600' : 'text-rose-500'">
                          {{ h.avail > 0 ? t('ex.onShelf').replace('{n}', String(h.avail)) : t('ex.noneOnShelf') }}
                        </span>
                      </button>
                    </li>
                  </ul>
                  <p v-else-if="pickQ.trim() && searched" class="text-[11px] text-stone-400">{{ t('ex.noHits') }}</p>
                </div>

                <!-- whatever ends up going out, priced, whichever way it got here -->
                <div v-if="editItems.length" class="pt-1 space-y-1">
                  <div v-for="(it, i) in editItems" :key="'o' + i"
                       class="flex items-center gap-2 p-1.5 rounded-lg bg-white ring-1 ring-amber-200">
                    <span class="min-w-0 flex-1">
                      <span class="block text-[11.5px] text-stone-700 truncate" dir="auto">
                        {{ priced(i) ? priced(i).name : it.item_code }}
                      </span>
                      <span v-if="priced(i)" class="block text-[10.5px] text-stone-400 tabular-nums">
                        {{ priced(i).rate }} MAD<template v-if="priced(i).auto"> · {{ t('ex.fromLastSold') }}</template>
                        <template v-if="priced(i).avail <= 0"> · <span class="text-rose-500">{{ t('ex.noneOnShelf') }}</span></template>
                      </span>
                      <span v-else-if="quoteErr" class="block text-[10.5px] text-rose-600">{{ quoteErr }}</span>
                    </span>
                    <input v-model.number="it.qty" type="number" min="1"
                           class="w-[56px] h-8 ps-2 rounded-lg bg-stone-50 ring-1 ring-amber-200 text-[12px] tabular-nums focus:outline-none"
                           @change="quoteSoon(0)" />
                    <!-- the rare correction; blank stays blank -->
                    <input v-model.number="it.rate" type="number" min="0"
                           :placeholder="priced(i) ? String(priced(i).rate) : t('ex.ratePh')"
                           class="w-[86px] h-8 ps-2 rounded-lg bg-stone-50 ring-1 ring-amber-200 text-[12px] tabular-nums focus:outline-none"
                           :class="it.rate > 0 ? 'text-stone-800' : 'text-stone-400'"
                           @change="quoteSoon(0)" />
                    <button :title="t('common.close')" class="w-7 h-7 rounded-lg text-stone-400 hover:text-rose-600 hover:bg-rose-50 inline-flex items-center justify-center shrink-0"
                            @click="editItems.splice(i, 1); quoteSoon(0)"><Icon name="x" :size="12" /></button>
                  </div>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2 flex-wrap pt-1">
              <!-- The sentence the agent says out loud. It was only knowable
                   AFTER saving, which is the wrong order: the number is what
                   the customer is being told while the panel is still open.
                   Same server code as the save, so it cannot disagree. -->
              <span v-if="editReason" class="ms-auto text-[12px] font-semibold tabular-nums"
                    :class="settleTone">
                <Icon :name="settleIcon" :size="13" class="inline -mt-px me-1" />{{ settleText }}
              </span>
              <span v-else class="ms-auto" />
              <button class="h-9 px-4 rounded-lg text-[12px] font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 transition-colors"
                      :disabled="savingItems || !editReason" @click="saveItems(r)">
                {{ savingItems ? '…' : t('px.common.save') }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </TransitionGroup>

    <!-- pager -->
    <div v-if="!loading && total > pageSize" class="flex items-center justify-between px-1">
      <span class="text-[11.5px] text-stone-500 tabular-nums">
        {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} / {{ total }}
      </span>
      <div class="flex items-center gap-1">
        <button :title="t('common.back')" class="pg-btn" :disabled="page <= 1" @click="page--; load()"><Icon name="chevron-left" :size="13" class="flip-rtl" /></button>
        <button class="pg-btn" :disabled="page * pageSize >= total" @click="page++; load()"><Icon name="chevron-right" :size="13" class="flip-rtl" /></button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const TABS = [
  { key: "waiting", label: "ex.tabWaiting", icon: "edit", onColor: "bg-amber-100 text-amber-700" },
  { key: "labeled", label: "ex.tabLabeled", icon: "tag", onColor: "bg-sky-100 text-sky-700" },
  { key: "settled", label: "ex.tabSettled", icon: "check-circle", onColor: "bg-emerald-100 text-emerald-700" },
];

const tab = ref("waiting");
// Opened from an order screen: ?q=<order> lands here already searched, the
// same contract Find-a-customer has had for months. An agent on a call should
// not have to copy an order number, leave the page and type it again.
const route = useRoute();
const q = ref(String(route.query.q || ""));
const page = ref(1);
const pageSize = 30;
const data = ref(null);
const rows = ref([]);
const total = ref(0);
const loading = ref(true);
const loadError = ref("");
const busy = ref("");
const newOrder = ref("");
const orderInput = ref(null);
const starting = ref(false);
const editFor = ref("");
const editItems = ref([]);
// The reason list and the fee map both live on the server; the page reads
// them rather than keeping a second copy that could drift from the policy.
const REASONS = ["Damaged on arrival", "Missing piece", "We sent the wrong item",
  "We sent the wrong size", "Customer ordered the wrong size", "Changed mind",
  "Wants a different product"];
const editReason = ref("");
const feeMap = ref({});
const fee = ref(25);
const feeApplies = computed(() => !!feeMap.value[editReason.value]);
async function loadFeePolicy() {
  try {
    const cfg = await api("tickets.cs_settings");
    feeMap.value = cfg?.reasonFee || {};
    fee.value = cfg?.pickupFee ?? 25;
  } catch (e) { /* the server still decides; this is only the preview */ }
}
const savingItems = ref(false);

// ---- details + history ----------------------------------------------------
const detailFor = ref("");
const detail = ref(null);
const detailErr = ref("");
const loadingDetail = ref(false);
async function toggleDetail(r) {
  if (detailFor.value === r.name) { detailFor.value = ""; return; }
  detailFor.value = r.name;
  detail.value = null;
  detailErr.value = "";
  loadingDetail.value = true;
  try {
    detail.value = await api("exchange.details", { name: r.name });
  } catch (e) {
    detailErr.value = String(e?.message || e || "");
  } finally {
    loadingDetail.value = false;
  }
}

// ---- live quote -----------------------------------------------------------
// The panel used to be write-only: the agent typed a code, a quantity and a
// price, pressed Save, and only then learned which item the code meant, what
// price we would use and what the customer owed. All three are decisions made
// with the customer on the line, so they are answered here instead — by the
// SAME server call the save runs, minus the save.
const quoted = ref(null);
const quoteErr = ref("");
let quoteTimer = null;
function priced(i) {
  const q = quoted.value;
  if (!q || !Array.isArray(q.items)) return null;
  const typed = (editItems.value[i]?.item_code || "").trim();
  if (!typed) return null;
  return q.items.find((x) => x.typed === typed) || null;
}
async function runQuote() {
  const name = editFor.value;
  if (!name) return;
  const items = editItems.value
    .filter((x) => (x.item_code || "").trim())
    .map((x) => ({ item_code: x.item_code.trim(), qty: x.qty || 1, rate: x.rate || 0 }));
  try {
    quoted.value = await api("exchange.quote",
      { name, items, reason: editReason.value, returning: returningPayload() });
    quoteErr.value = "";
  } catch (e) {
    // An unknown code is the common case while still typing — say so on the
    // row rather than clearing the money line to a silent blank.
    quoted.value = null;
    quoteErr.value = String(e?.message || e || "");
  }
}
function quoteSoon(delay = 400) {
  clearTimeout(quoteTimer);
  quoteTimer = setTimeout(runQuote, typeof delay === "number" ? delay : 400);
}
watch(editReason, () => quoteSoon(0));
const settleText = computed(() => {
  const q = quoted.value;
  if (!q) return t("ex.settleWorking");
  const d = Math.round(q.difference || 0);
  if (!d) return t("ex.settleNone");
  return (d > 0 ? t("ex.settleCollect") : t("ex.settleRefund"))
    .replace("{n}", String(Math.abs(d)));
});
const settleTone = computed(() => {
  const d = Math.round(quoted.value?.difference || 0);
  if (!quoted.value) return "text-stone-400";
  if (!d) return "text-emerald-700";
  return d > 0 ? "text-amber-700" : "text-rose-700";
});
const settleIcon = computed(() => {
  const d = Math.round(quoted.value?.difference || 0);
  if (!quoted.value) return "clock";
  if (!d) return "check-circle";
  return d > 0 ? "arrow-down-left" : "arrow-up-right";
});

let qTimer = null;
function debouncedLoad() {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { page.value = 1; load(); }, 350);
}

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const res = await api("exchange.board", {
      tab: tab.value, q: q.value, limit: pageSize,
      offset: (page.value - 1) * pageSize,
    });
    data.value = res;
    rows.value = res.rows || [];
    total.value = res.total || 0;
  } catch (e) {
    loadError.value = String(e.message || e);
    rows.value = [];
  } finally {
    loading.value = false;
  }
}
loadFeePolicy();
onMounted(load);

async function start() {
  if (!newOrder.value.trim()) { orderInput.value?.focus(); return; }
  starting.value = true;
  try {
    const res = await apiPost("exchange.start", { order: newOrder.value.trim() });
    success(t("ex.started"), res.name);
    newOrder.value = "";
    tab.value = "waiting";
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    starting.value = false;
  }
}

// The three answers to "what goes out", because there are only three.
// Shopify keeps exchangeLineItems separate from the returned lines; ours are
// the same item again in most cases, a different product occasionally, and
// nothing at all on the 680-of-1,000 that are plain returns.
const OUT_MODES = ["same", "other", "none"];
const outMode = ref("same");
const backLines = ref([]);
const loadingLines = ref(false);

async function toggleEdit(r) {
  if (editFor.value === r.name) { editFor.value = ""; return; }
  editFor.value = r.name;
  editItems.value = [];
  editReason.value = r.reason || "";
  quoted.value = null;
  quoteErr.value = "";
  pickQ.value = "";
  hits.value = [];
  searched.value = false;
  backLines.value = [];
  loadingLines.value = true;
  try {
    // The order's own lines ARE the picker. Typing a code from memory is what
    // produced "Unknown item: MCH00013" on a product that was never ordered.
    const d = await api("exchange.details", { name: r.name });
    const already = new Map((d.coming || []).map((x) => [x.code, x.qty]));
    backLines.value = (d.has || []).map((x) => ({
      code: x.code, name: x.name, image: x.image, rate: x.rate,
      ordered: x.qty,
      take: already.size ? already.has(x.code) : false,
      qty: already.get(x.code) || x.qty,
    }));
    // Reopening shows the decision that was made, not a blank form.
    const sending = d.sending || [];
    if (sending.length) {
      const sameAsOrder = sending.every((sd) =>
        (d.has || []).some((h) => h.code === sd.code));
      outMode.value = sameAsOrder ? "same" : "other";
      editItems.value = sending.map((x) => ({ item_code: x.code, qty: x.qty, rate: null }));
    } else {
      outMode.value = already.size ? "none" : "same";
    }
  } catch (e) {
    quoteErr.value = String(e?.message || e || "");
  } finally {
    loadingLines.value = false;
  }
  quoteSoon(0);
}

// "Send the same thing back out" is a mirror of what is coming back, so it
// stays in step instead of being a second list somebody has to maintain.
function mirrorBack() {
  editItems.value = backLines.value
    .filter((l) => l.take)
    .map((l) => ({ item_code: l.code, qty: l.qty || 1, rate: null }));
}
function onTakeChanged() {
  if (outMode.value === "same") mirrorBack();
  quoteSoon(0);
}
function onModeChanged() {
  if (outMode.value === "same") mirrorBack();
  else if (outMode.value === "none") editItems.value = [];
  quoteSoon(0);
}

// ---- product search, for the one case that needs a product we do not know --
const pickQ = ref("");
const hits = ref([]);
const searching = ref(false);
const searched = ref(false);
let searchTimer = null;
async function runSearch() {
  const query = pickQ.value.trim();
  if (!query) { hits.value = []; searched.value = false; return; }
  searching.value = true;
  try {
    const res = await api("inventory.sku_lookup", { query });
    const out = [];
    for (const g of (res?.groups || [])) {
      for (const it of (g.items || [])) {
        out.push({ code: it.code, name: it.name || it.code, avail: it.avail || 0 });
      }
    }
    hits.value = out.slice(0, 20);
  } catch {
    hits.value = [];
  } finally {
    searching.value = false;
    searched.value = true;
  }
}
function searchSoon() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(runSearch, 350);
}
function addPicked(h) {
  if (!editItems.value.some((x) => x.item_code === h.code)) {
    editItems.value.push({ item_code: h.code, qty: 1, rate: null });
  }
  pickQ.value = "";
  hits.value = [];
  searched.value = false;
  quoteSoon(0);
}

// What the van is collecting, sent alongside what goes out.
function returningPayload() {
  return backLines.value.filter((l) => l.take)
    .map((l) => ({ item_code: l.code, qty: l.qty || 1 }));
}

async function saveItems(r) {
  savingItems.value = true;
  try {
    const items = editItems.value.filter((x) => (x.item_code || "").trim());
    const res = await apiPost("exchange.set_items", {
      name: r.name, items, reason: editReason.value,
      returning: returningPayload(),
    });
    success(t("ex.itemsSaved"),
            `${res.direction || ""} ${Math.abs(res.difference || 0)} MAD`
            + (res.fee ? ` (+${res.fee} ${t("ex.feeWord")})` : ""));
    editFor.value = "";
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    savingItems.value = false;
  }
}

async function generate(r) {
  busy.value = r.name;
  try {
    const res = await apiPost("exchange.generate", { name: r.name });
    success(t("ex.generated"), `${res.awb} → ${res.exOrder}`);
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

async function settle(r) {
  busy.value = r.name;
  try {
    await apiPost("exchange.settle", { name: r.name });
    success(t("ex.settled"), r.name);
    rows.value = rows.value.filter((x) => x.name !== r.name);
    if (data.value?.counts) { data.value.counts.labeled--; data.value.counts.settled++; }
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

function statusClass(s) {
  if (s === "Label Generated") return "text-sky-700 bg-sky-50";
  if (s === "Settled") return "text-emerald-700 bg-emerald-50";
  if (s === "Cancelled") return "text-stone-500 bg-stone-100";
  return "text-amber-700 bg-amber-50";
}
function ageLabel(h) {
  return h < 48 ? `${h}${t('cf.hrs')}` : `${Math.round(h / 24)}${t('cf.days')}`;
}
</script>

<style scoped>
.ex-hero {
  background: linear-gradient(135deg, rgb(255 251 235) 0%, #fff 45%, #fff 70%, rgb(255 251 235) 100%);
  box-shadow: inset 0 0 0 1px rgb(253 230 138 / 0.6), 0 1px 2px rgb(0 0 0 / 0.03);
}
.ex-hero-icon {
  width: 52px; height: 52px; border-radius: 16px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: white;
  background: linear-gradient(135deg, rgb(251 191 36), rgb(217 119 6));
  box-shadow: 0 6px 16px -6px rgb(217 119 6 / 0.5);
}
.ex-new {
  height: 40px; padding: 0 16px; border-radius: 12px;
  font-size: 12.5px; font-weight: 700; color: white;
  background: linear-gradient(135deg, rgb(251 191 36), rgb(217 119 6));
  box-shadow: 0 4px 12px -4px rgb(217 119 6 / 0.4);
  transition: all .15s ease;
}
.ex-new:hover { transform: translateY(-1px); }
.ex-new:disabled { opacity: .5; }
.ex-dh {
  font-size: 10.5px; font-weight: 700; letter-spacing: .04em;
  text-transform: uppercase; color: rgb(var(--text3));
}
.ex-ev {
  display: inline-flex; align-items: center; height: 18px; padding: 0 7px;
  border-radius: 6px; font-size: 10.5px; font-weight: 700;
  background: rgb(var(--border) / 0.6); color: rgb(var(--text2));
}
.ex-seg { display: inline-flex; gap: 2px; padding: 4px; background: rgb(var(--border) / 0.55); border-radius: 14px; }
.ex-seg-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 12px; border-radius: 11px;
  font-size: 12.5px; font-weight: 600; color: rgb(var(--text3));
  transition: all .18s ease;
}
.ex-seg-btn:hover { color: rgb(var(--text)); }
.ex-seg-on { background: rgb(var(--card)); color: rgb(var(--text)); box-shadow: 0 1px 3px rgb(0 0 0 / 0.08); }
.ex-seg-count { font-size: 11px; font-weight: 700; font-variant-numeric: tabular-nums; padding: 1px 7px; border-radius: 999px; }
.ex-card {
  background: rgb(var(--card));
  box-shadow: inset 0 0 0 1px rgb(var(--border) / 0.8), 0 1px 2px rgb(0 0 0 / 0.02);
  transition: box-shadow .18s ease, transform .18s ease;
}
.ex-card:hover {
  box-shadow: inset 0 0 0 1px rgb(var(--border)), 0 8px 24px -12px rgb(0 0 0 / 0.14);
  transform: translateY(-1px);
}
.ex-avatar {
  width: 42px; height: 42px; border-radius: 999px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: rgb(180 83 9);
  background: linear-gradient(135deg, rgb(255 251 235), rgb(254 243 199));
  box-shadow: inset 0 0 0 1px rgb(253 230 138);
}
.ex-chip { font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 999px; }
.ex-act {
  height: 38px; border-radius: 12px; font-size: 12.5px; font-weight: 700;
  transition: all .15s ease; white-space: nowrap;
}
.ex-act:disabled { opacity: .5; }
.ex-act-main {
  padding: 0 16px; color: white;
  background: linear-gradient(135deg, rgb(251 191 36), rgb(217 119 6));
  box-shadow: 0 4px 12px -4px rgb(217 119 6 / 0.4);
}
.ex-act-main:hover:not(:disabled) { transform: translateY(-1px); }
.ex-act-soft {
  width: 38px; background: rgb(250 250 249);
  box-shadow: inset 0 0 0 1px rgb(var(--border));
  display: inline-flex; align-items: center; justify-content: center;
}
.ex-act-soft:hover { background: rgb(var(--card)); transform: scale(1.06); }
.ex-empty { background: linear-gradient(180deg, white, rgb(250 250 249)); box-shadow: inset 0 0 0 1px rgb(var(--border) / 0.8); }
.ex-shimmer {
  background: linear-gradient(90deg, rgb(var(--bg)) 25%, rgb(var(--border) / 0.6) 50%, rgb(var(--bg)) 75%);
  background-size: 200% 100%;
  animation: ex-shimmer 1.4s ease-in-out infinite;
}
@keyframes ex-shimmer { to { background-position: -200% 0; } }
.pg-btn {
  width: 32px; height: 32px; border-radius: 10px; background: rgb(var(--card));
  box-shadow: inset 0 0 0 1px rgb(var(--border));
  display: inline-flex; align-items: center; justify-content: center;
}
.pg-btn:disabled { opacity: .4; }
.exrow-leave-active { transition: all .28s ease; position: relative; }
.exrow-leave-to { opacity: 0; transform: translateX(24px) scale(.98); }
.exrow-enter-active { transition: all .25s ease; }
.exrow-enter-from { opacity: 0; transform: translateY(6px); }
.exrow-move { transition: transform .28s ease; }
.exslide-enter-active, .exslide-leave-active { transition: all .2s ease; }
.exslide-enter-from, .exslide-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
