<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1200px] mx-auto">
    <!-- hero header -->
    <header class="cf-hero rounded-2xl p-5 sm:p-6">
      <div class="flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3.5">
          <span class="cf-hero-icon"><Icon name="phone" :size="22" /></span>
          <div>
            <h1 class="text-[21px] font-bold text-stone-900 tracking-tight leading-none">{{ t('cf.title') }}</h1>
            <p class="text-[12.5px] text-stone-500 mt-1.5">{{ t('cf.intro') }}</p>
          </div>
        </div>
        <div v-if="data" class="flex items-center gap-2 flex-wrap">
          <div class="cf-stat">
            <span class="cf-stat-n text-emerald-600">{{ data.mine.confirm }}</span>
            <span class="cf-stat-l"><Icon name="check-circle" :size="10" class="inline -mt-px me-0.5" />{{ t('cf.actConfirm') }}</span>
          </div>
          <div class="cf-stat">
            <span class="cf-stat-n text-amber-600">{{ data.mine.dna }}</span>
            <span class="cf-stat-l"><Icon name="phone-off" :size="10" class="inline -mt-px me-0.5" />{{ t('cf.actDna') }}</span>
          </div>
          <div class="cf-stat">
            <span class="cf-stat-n text-rose-500">{{ data.mine.cancel }}</span>
            <span class="cf-stat-l"><Icon name="circle-x" :size="10" class="inline -mt-px me-0.5" />{{ t('cf.actCancel') }}</span>
          </div>

          <!-- my day, on the same line: how far to the target, what it's worth -->
          <RouterLink v-if="data.myTarget" :to="{ name: 'Performance' }" class="cf-prog" :title="t('px.perf.dailyTarget')">
            <div class="flex items-baseline gap-1">
              <span class="text-[17px] font-extrabold tabular-nums leading-none"
                    :class="hitTarget ? 'text-emerald-600' : 'text-stone-900'">{{ data.myTotal }}</span>
              <span class="text-[10.5px] text-stone-400 tabular-nums">/ {{ data.myTarget }}</span>
              <Icon v-if="hitTarget" name="check-circle" :size="11" class="text-emerald-600" />
            </div>
            <div class="h-1.5 rounded-full bg-stone-200/70 overflow-hidden mt-1.5 w-[92px]">
              <div class="h-full rounded-full transition-all duration-700"
                   :class="hitTarget ? 'bg-emerald-500' : 'bg-[var(--accent-500)]'"
                   :style="{ width: dayPct + '%' }" />
            </div>
            <span class="cf-stat-l mt-1">{{ hitTarget ? t('cf.targetHit') : t('cf.targetGo', String(togo)).replace('{n}', togo) }}</span>
          </RouterLink>

          <RouterLink v-if="data.points" :to="{ name: 'Bonus' }" class="cf-stat cf-stat-link">
            <span class="cf-stat-n text-violet-600">{{ data.points.month }}</span>
            <span class="cf-stat-l"><Icon name="wallet" :size="10" class="inline -mt-px me-0.5" />{{ t('bn.pts') }} / {{ data.points.target }}</span>
          </RouterLink>
        </div>
      </div>
    </header>

    <!-- segmented queues + search -->
    <div class="flex items-center gap-3 flex-wrap">
      <div class="cf-seg">
        <template v-for="(tb, i) in TABS" :key="tb.key">
          <span v-if="tb.group && tb.group !== TABS[i - 1]?.group" class="cf-seg-div" />
          <button
            class="cf-seg-btn"
            :class="[tab === tb.key ? 'cf-seg-on' : '', tb.group ? 'cf-seg-alt' : '']"
            @click="tab = tb.key; page = 1; load()"
          >
            <Icon :name="tb.icon" :size="14" />
            <span>{{ t(tb.label) }}</span>
            <span class="cf-seg-count" :class="tab === tb.key ? tb.onColor : 'bg-stone-200/70 text-stone-500'">
              {{ data?.counts?.[tb.key] ?? '–' }}
            </span>
          </button>
        </template>
      </div>
      <div class="flex items-center gap-2 ms-auto flex-wrap">
        <DateRange v-model:days="days" v-model:frm="frm" v-model:to="to" @change="page = 1; load()" />
        <div class="relative">
          <Icon name="search" :size="13" class="absolute start-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <input v-model="q" :placeholder="t('cf.searchPh')" @input="debouncedLoad"
                 class="h-10 w-[240px] ps-9 pe-3 text-[12.5px] bg-white rounded-xl ring-1 ring-stone-200/80 focus:ring-2 outline-none transition-shadow"
                 style="--tw-ring-color: var(--accent-300)" />
        </div>
      </div>
    </div>

    <!-- bulk bar — on every tab, with the actions that tab honestly allows -->
    <div v-if="!loading && rows.length"
         class="flex items-center gap-2.5 flex-wrap bg-white rounded-2xl ring-1 ring-stone-200/80 px-4 py-3">
      <label class="inline-flex items-center gap-2 text-[12.5px] font-medium text-stone-700 cursor-pointer">
        <input type="checkbox" :checked="selected.size === rows.length && rows.length > 0" class="w-4 h-4"
               style="accent-color: var(--accent-600)" @change="toggleAll" />
        {{ t('rs.selectPage') }}
      </label>
      <span class="text-[12px] text-stone-400 tabular-nums">{{ selected.size }} {{ t('rs.selectedN') }}</span>
      <div class="flex items-center gap-2 ms-auto flex-wrap">
        <!-- done tabs: undo a batch of wrong decisions -->
        <button v-if="isDone"
                class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 hover:bg-amber-100 disabled:opacity-40 transition-colors"
                :disabled="!selected.size || bulkBusy" @click="bulkAct('reopen')">
          <Icon name="rotate-ccw" :size="13" class="inline -mt-px me-1" />{{ t('cf.bulkReopen') }}
        </button>
        <!-- working queues: kill or de-duplicate a batch -->
        <template v-else>
          <input v-model="bulkReason" :placeholder="t('cf.cancelPh')" maxlength="120"
                 class="h-9 w-[200px] ps-3 pe-3 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12px] focus:outline-none" />
          <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-violet-700 bg-violet-50 ring-1 ring-violet-200 hover:bg-violet-100 disabled:opacity-40 transition-colors"
                  :disabled="!selected.size || bulkBusy" @click="bulkAct('duplicate')">
            <Icon name="copy" :size="13" class="inline -mt-px me-1" />{{ t('cf.bulkDuplicate') }}
          </button>
          <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-rose-700 bg-rose-50 ring-1 ring-rose-200 hover:bg-rose-100 disabled:opacity-40 transition-colors"
                  :disabled="!selected.size || !bulkReason.trim() || bulkBusy" @click="bulkCancel">
            <Icon name="x" :size="13" class="inline -mt-px me-1" />{{ t('cf.bulkCancel') }}
          </button>
        </template>
      </div>
      <!-- Deliberately absent: bulk confirm. A confirmation means a customer
           said yes on a call; there is no honest way to do that to 50 rows. -->
    </div>

    <!-- rows -->
    <div v-if="loading" class="space-y-2.5">
      <div v-for="n in 6" :key="n" class="h-[76px] rounded-2xl cf-shimmer" />
    </div>
    <div v-else-if="!rows.length" class="cf-empty rounded-2xl p-12 text-center">
      <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-emerald-50 text-emerald-500 mb-3"><Icon name="check-circle" :size="26" /></span>
      <div class="text-[15px] font-semibold text-stone-800">{{ t('cf.empty') }}</div>
      <div class="text-[12.5px] text-stone-400 mt-1">{{ t('cf.emptyHint') }}</div>
    </div>
    <TransitionGroup v-else name="cfrow" tag="div" class="space-y-2.5 relative">
      <div v-for="r in rows" :key="r.order"
           class="cf-card rounded-2xl p-4"
           :class="r.due ? 'cf-card-due' : ''">
        <div class="flex items-center gap-3.5 flex-wrap">
          <!-- customer identity -->
          <input type="checkbox" class="w-4 h-4 shrink-0"
                 style="accent-color: var(--accent-600)"
                 :checked="selected.has(r.order)" @change="toggleOne(r.order)" />
          <span class="cf-avatar" :class="r.due ? 'cf-avatar-due' : ''">{{ initial(r.customer) }}</span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[13.5px] font-bold text-stone-900 truncate max-w-[220px]">{{ r.customer || '—' }}</span>
              <span class="font-mono text-[11px] text-stone-400">{{ r.order }}</span>
              <button v-if="r.cust && r.cust.seg !== 'new'" class="seg-chip" :class="'seg-' + r.cust.seg"
                      :title="t('seg.explain_' + r.cust.seg)" @click="toggleCust(r)">
                <Icon :name="segIcon(r.cust.seg)" :size="10" />
                {{ t('seg.' + r.cust.seg) }}
                <span v-if="r.cust.rate !== null" class="opacity-70 tabular-nums">{{ r.cust.rate }}%</span>
              </button>
              <span v-if="r.due" class="cf-due-badge">{{ t('cf.due') }}</span>
              <span v-else-if="r.slaBreached" class="cf-due-badge">{{ t('cf.slaLate') }}</span>
            </div>
            <div class="flex items-center gap-2.5 text-[11.5px] text-stone-500 tabular-nums mt-1 flex-wrap">
              <span class="font-semibold text-stone-800">{{ fmtMAD(r.total) }} <span class="text-stone-400 font-normal">MAD</span></span>
              <span v-if="r.city" class="inline-flex items-center gap-1"><Icon name="map-pin" :size="11" class="text-stone-300" />{{ r.city }}</span>
              <span>{{ r.items }} {{ t('consol.items') }}</span>
              <span class="inline-flex items-center gap-1" :class="ageColor(r.ageH)"><Icon name="clock" :size="11" />{{ ageLabel(r.ageH) }}</span>
              <span v-if="r.attempts" class="inline-flex items-center gap-1 text-amber-600 font-medium"><Icon name="phone-off" :size="11" />×{{ r.attempts }}</span>
              <span v-if="r.chased" class="inline-flex items-center gap-1 text-sky-600 font-medium"
                    :title="t('cf.chasedHint')">
                <Icon name="send" :size="11" />{{ t('cf.chased') }} ×{{ r.chased }}
              </span>
              <span v-if="r.agent" class="text-stone-400">{{ r.agent }}</span>
              <span v-if="r.nextCall" class="text-stone-400">→ {{ r.nextCall.slice(5) }}</span>
            </div>
            <!-- what's in the order: one line, click for the whole thing -->
            <button v-if="r.itemsText" class="flex items-center gap-1 text-[11.5px] text-stone-500 mt-1 max-w-[560px] group/it text-start"
                    @click="toggleDetail(r)">
              <Icon name="package" :size="11" class="shrink-0 text-stone-300" />
              <span class="truncate" dir="auto">{{ r.itemsText }}</span>
              <Icon :name="detailFor === r.order ? 'chevron-up' : 'chevron-down'" :size="11"
                    class="shrink-0 text-[var(--accent-500)] opacity-60 group-hover/it:opacity-100" />
            </button>
            <!-- the decision that closed it -->
            <div v-if="isDone && r.reason" class="text-[11.5px] text-stone-500 mt-1 truncate max-w-[560px]" dir="auto">
              <Icon name="corner-down-left" :size="11" class="inline -mt-px me-1 text-stone-300" />{{ r.reason }}
            </div>
          </div>
          <!-- contact -->
          <div class="flex items-center gap-1.5">
            <a v-if="r.phone" :href="'tel:' + r.phone" :title="r.phone" class="cf-contact cf-tel">
              <Icon name="phone" :size="15" />
            </a>
            <a v-if="r.phone" :href="waLink(r.phone)" target="_blank" title="WhatsApp" class="cf-contact cf-wa">
              <Icon name="message-circle" :size="15" />
            </a>
            <button class="cf-contact text-stone-400 hover:text-stone-700"
                    :class="editFor === r.order ? 'bg-stone-100' : ''"
                    :title="t('cf.editContact')" @click="toggleEdit(r)">
              <Icon name="edit" :size="13" />
            </button>
          </div>
          <!-- decisions -->
          <div v-if="!isDone" class="flex items-center gap-1.5 flex-wrap">
            <button class="cf-act cf-act-confirm" :disabled="busy === r.order" @click="act(r, 'confirm')">
              <Icon name="check" :size="14" class="inline -mt-px me-1" />{{ t('cf.actConfirm') }}
            </button>
            <button class="cf-act cf-act-soft text-amber-700" :disabled="busy === r.order" :title="t('cf.actDna')" @click="act(r, 'dna')"><Icon name="phone-off" :size="15" /></button>
            <button class="cf-act cf-act-soft text-sky-700" :disabled="busy === r.order" :title="t('cf.actFollowup')" @click="act(r, 'followup')"><Icon name="clock" :size="15" /></button>
            <button class="cf-act cf-act-soft text-stone-500" :disabled="busy === r.order" :title="t('cf.actOnhold')" @click="act(r, 'onhold')"><Icon name="circle-pause" :size="15" /></button>
            <button class="cf-act cf-act-soft text-violet-600" :disabled="busy === r.order" :title="t('cf.actDuplicate')" @click="act(r, 'duplicate')"><Icon name="copy" :size="15" /></button>
            <button :title="t('common.close')" class="cf-act cf-act-soft text-rose-600" :disabled="busy === r.order"
                    :class="cancelFor === r.order ? 'ring-2' : ''"
                    @click="cancelFor = cancelFor === r.order ? '' : r.order"><Icon name="circle-x" :size="15" /></button>
          </div>
          <!-- already decided: the outcome + an undo -->
          <div v-else class="flex items-center gap-2 flex-wrap">
            <span class="cf-done" :class="doneClass(r.status)">
              <Icon :name="doneIcon(r.status)" :size="12" />
              {{ t('cf.st' + tab) }}
              <span v-if="r.lastCall" class="font-mono opacity-70">{{ r.lastCall.slice(5) }}</span>
            </span>
            <button class="cf-act cf-act-soft text-amber-700" :disabled="busy === r.order"
                    :title="t('cf.actReopen')" @click="act(r, 'reopen')">
              <Icon name="rotate-ccw" :size="15" />
            </button>
          </div>
        </div>

        <!-- who this customer is: every order they ever made -->
        <Transition name="cfslide">
          <div v-if="custFor === r.order" class="mt-3 rounded-xl bg-stone-50 ring-1 ring-stone-200/70 p-3">
            <div v-if="custLoading" class="text-[12px] text-stone-400 text-center py-4">…</div>
            <template v-else-if="cust">
              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11.5px] tabular-nums pb-2.5 mb-2.5 border-b border-stone-200/70">
                <span class="text-stone-500">{{ t('seg.hOrders') }} <b class="text-stone-800">{{ cust.orders }}</b></span>
                <span class="text-stone-500">{{ t('seg.hDelivered') }} <b class="text-emerald-600">{{ cust.delivered }}</b></span>
                <span class="text-stone-500">{{ t('seg.hFailed') }} <b class="text-rose-600">{{ cust.failed }}</b></span>
                <span class="text-stone-500">{{ t('seg.hCancelled') }} <b class="text-stone-700">{{ cust.cancelled }}</b></span>
                <span v-if="cust.lifetime" class="text-stone-500">{{ t('seg.hLifetime') }} <b class="text-stone-900">{{ fmtMAD(cust.lifetime) }}</b> MAD</span>
              </div>
              <div class="space-y-1">
                <div v-for="o in cust.orders_list" :key="o.order"
                     class="flex items-center gap-2 text-[11.5px] bg-white rounded-lg px-2.5 py-1.5 ring-1 ring-stone-200/60">
                  <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="trackDot(o.track, o.status)" />
                  <span class="font-mono text-stone-700 shrink-0">{{ o.order }}</span>
                  <span class="text-stone-400 tabular-nums shrink-0">{{ o.at }}</span>
                  <span v-if="o.city" class="text-stone-400 truncate">{{ o.city }}</span>
                  <span class="ms-auto text-stone-500 shrink-0">{{ o.track || o.status }}</span>
                  <span class="font-semibold text-stone-800 tabular-nums shrink-0 w-[64px] text-end">{{ fmtMAD(o.total) }}</span>
                </div>
              </div>
            </template>
          </div>
        </Transition>

        <!-- the whole order, on demand -->
        <Transition name="cfslide">
          <div v-if="detailFor === r.order" class="mt-3 rounded-xl bg-stone-50 ring-1 ring-stone-200/70 p-3">
            <div v-if="detailLoading" class="text-[12px] text-stone-400 text-center py-4">…</div>
            <div v-else-if="detailError" class="text-[12px] text-rose-500 text-center py-3 font-mono">{{ detailError }}</div>
            <template v-else-if="detail">
              <!-- line items with their pictures — the agent describes them on the call -->
              <div class="space-y-1.5">
                <div v-for="(it, i) in detail.items" :key="i"
                     class="flex items-center gap-2.5 bg-white rounded-lg p-2 ring-1 ring-stone-200/60">
                  <img v-if="it.image" :src="it.image" alt="" loading="lazy"
                       class="w-10 h-10 rounded-md object-cover bg-stone-100 shrink-0" />
                  <span v-else class="w-10 h-10 rounded-md bg-stone-100 text-stone-300 grid place-items-center shrink-0">
                    <Icon name="package" :size="15" />
                  </span>
                  <div class="min-w-0 flex-1">
                    <div class="text-[12px] font-medium text-stone-900 truncate" dir="auto">{{ it.name }}</div>
                    <div class="text-[10.5px] text-stone-400 font-mono">{{ it.real_sku || it.sku }}</div>
                  </div>
                  <div class="text-[12px] text-stone-500 tabular-nums shrink-0">
                    <span class="font-bold text-stone-800">{{ it.qty }}×</span> {{ fmtMAD(it.price) }}
                  </div>
                  <div class="text-[12.5px] font-bold text-stone-900 tabular-nums w-[74px] text-end shrink-0">
                    {{ fmtMAD(it.line) }}
                  </div>
                </div>
              </div>
              <!-- money + destination, straight from the order -->
              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2.5 pt-2.5 border-t border-stone-200/70 text-[11.5px] tabular-nums">
                <span class="text-stone-500">{{ t('cf.dSubtotal') }} <b class="text-stone-800">{{ fmtMAD(detail.subtotal) }}</b></span>
                <span v-if="detail.discount" class="text-stone-500">{{ t('cf.dDiscount') }} <b class="text-rose-600">−{{ fmtMAD(detail.discount) }}</b></span>
                <span v-if="detail.taxes" class="text-stone-500">{{ t('cf.dShipping') }} <b class="text-stone-800">{{ fmtMAD(detail.taxes) }}</b></span>
                <span class="text-stone-500">{{ t('cf.dTotal') }} <b class="text-[13px] text-stone-900">{{ fmtMAD(detail.total) }}</b> MAD</span>
                <span v-if="detail.created" class="text-stone-400 ms-auto font-mono">{{ detail.created }}</span>
              </div>
              <div v-if="detail.address_line || detail.city" class="flex items-start gap-1.5 mt-2 text-[11.5px] text-stone-600" dir="auto">
                <Icon name="map-pin" :size="12" class="mt-0.5 shrink-0 text-stone-300" />
                <span>{{ [detail.address_line, detail.city, detail.governorate].filter(Boolean).join(' · ') }}</span>
              </div>
              <RouterLink :to="{ name: 'OrderDetail', params: { name: r.order } }"
                          class="inline-flex items-center gap-1 text-[11.5px] font-semibold text-[var(--accent-600)] hover:underline mt-2">
                {{ t('cf.dFull') }}<Icon name="chevron-right" :size="12" class="flip-rtl" />
              </RouterLink>
            </template>
          </div>
        </Transition>

        <!-- cancel reason -->
        <Transition name="cfslide">
          <div v-if="cancelFor === r.order" class="space-y-2 bg-rose-50/70 rounded-xl p-2.5 mt-3">
            <div v-if="data?.reasons?.length" class="flex flex-wrap gap-1.5">
              <button v-for="rs in data.reasons" :key="rs"
                      class="h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1 transition-all"
                      :class="cancelReason === rs ? 'text-white bg-rose-600 ring-rose-600 shadow-sm' : 'text-rose-700 bg-white ring-rose-200 hover:bg-rose-100'"
                      @click="cancelReason = rs">{{ rs }}</button>
            </div>
            <div class="flex items-center gap-2">
              <input v-model="cancelReason" :placeholder="t('cf.cancelPh')" maxlength="120"
                     class="flex-1 h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-rose-200 text-[12.5px] focus:outline-none" />
              <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 transition-colors"
                      :disabled="!cancelReason.trim() || busy === r.order"
                      @click="act(r, 'cancel', cancelReason)">{{ t('cf.cancelConfirm') }}</button>
            </div>
          </div>
        </Transition>

        <!-- contact edit -->
        <Transition name="cfslide">
          <div v-if="editFor === r.order" class="flex items-center gap-2 flex-wrap bg-stone-50 rounded-xl p-2.5 mt-3">
            <input v-model="editPhone" :placeholder="t('cf.phonePh')" maxlength="20"
                   class="h-9 w-[180px] ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] font-mono focus:outline-none" />
            <input v-model="editCity" :placeholder="t('cf.cityPh')" maxlength="60"
                   class="h-9 w-[180px] ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none" />
            <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50"
                    :disabled="savingContact" @click="saveContact(r)">{{ t('px.common.save') }}</button>
          </div>
        </Transition>
      </div>
    </TransitionGroup>

    <!-- pager -->
    <Pager v-if="!loading" v-model:page="page" v-model:pageSize="pageSize" :total="total" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import Pager from "@/components/ui/Pager.vue";
import DateRange from "@/components/ui/DateRange.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const TABS = [
  { key: "pending", label: "cf.tabPending", icon: "shopping-bag", onColor: "bg-[var(--accent-100)] text-[var(--accent-700)]" },
  { key: "dna", label: "cf.tabDna", icon: "phone-off", onColor: "bg-amber-100 text-amber-700" },
  { key: "followup", label: "cf.tabFollowup", icon: "clock", onColor: "bg-sky-100 text-sky-700" },
  { key: "onhold", label: "cf.tabOnhold", icon: "pause", onColor: "bg-stone-200 text-stone-600" },
  { key: "monitor", label: "cf.tabMonitor", icon: "shield-alert", onColor: "bg-rose-100 text-rose-700" },
  { key: "confirmed", label: "cf.tabConfirmed", icon: "check-circle", onColor: "bg-emerald-100 text-emerald-700", group: "done" },
  { key: "cancelled", label: "cf.tabCancelled", icon: "x", onColor: "bg-rose-100 text-rose-700", group: "done" },
  { key: "duplicated", label: "cf.tabDuplicated", icon: "copy", onColor: "bg-violet-100 text-violet-700", group: "done" },
];
// Tabs where the lane is done deciding — read-only rows with an undo.
const DONE = ["confirmed", "cancelled", "duplicated"];

const tab = ref("pending");
const q = ref("");
const page = ref(1);
const pageSize = ref(20);
const days = ref(30);
const frm = ref("");
const to = ref("");
// The pager owns page/pageSize; a change to either has to refetch.
watch([page, pageSize], () => load());
const data = ref(null);
const rows = ref([]);
const total = ref(0);
const loading = ref(true);
const busy = ref("");
const cancelFor = ref("");
const cancelReason = ref("");
const editFor = ref("");
const editPhone = ref("");
const editCity = ref("");
const savingContact = ref(false);

let qTimer = null;
function debouncedLoad() {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { page.value = 1; load(); }, 350);
}

async function load() {
  loading.value = true;
  selected.value = new Set();
  try {
    const res = await api("confirmation.board", {
      tab: tab.value, q: q.value, limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
      days: days.value, frm: frm.value || undefined, to: to.value || undefined,
    });
    data.value = res;
    rows.value = res.rows || [];
    total.value = res.total || 0;
  } catch (e) {
    warn(t("cf.loadFail"), String(e.message || e));
    rows.value = [];
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const isDone = computed(() => DONE.includes(tab.value));
const dayPct = computed(() => {
  const d = data.value;
  if (!d?.myTarget) return 0;
  return Math.min(100, Math.round((d.myTotal * 100) / d.myTarget));
});
const hitTarget = computed(() => (data.value?.myTotal || 0) >= (data.value?.myTarget || 1));
const togo = computed(() => Math.max(0, (data.value?.myTarget || 0) - (data.value?.myTotal || 0)));

// Who is this customer? The chip is on the card; the whole history is one
// click behind it. Nothing here blocks an order — the team decides.
const custFor = ref("");
const cust = ref(null);
const custLoading = ref(false);

async function toggleCust(r) {
  if (custFor.value === r.order) { custFor.value = ""; return; }
  custFor.value = r.order;
  cust.value = null;
  custLoading.value = true;
  try {
    const res = await api("customers.card", { phone: r.phone });
    if (custFor.value !== r.order) return;
    cust.value = { ...res, orders_list: res.recent || [] };
  } catch (e) {
    warn(t("cf.loadFail"), String(e.message || e));
    custFor.value = "";
  } finally {
    custLoading.value = false;
  }
}

function segIcon(seg) {
  return { vip: "sparkles", good: "check-circle", watch: "clock",
           risk: "alert-triangle", black: "shield-alert" }[seg] || "user";
}
function trackDot(track, status) {
  if (track === "Delivered") return "bg-emerald-500";
  if (track === "Delivery Exception" || track === "Failed Attempt") return "bg-rose-500";
  if (status === "Cancelled") return "bg-stone-300";
  return "bg-amber-400";
}

// The order itself, pulled on demand — the agent has the customer on the line
// and needs to say what's in the box, so it opens in place rather than
// navigating away from the queue.
const detailFor = ref("");
const detail = ref(null);
const detailLoading = ref(false);
const detailError = ref("");

async function toggleDetail(r) {
  if (detailFor.value === r.order) { detailFor.value = ""; return; }
  detailFor.value = r.order;
  detail.value = null;
  detailError.value = "";
  detailLoading.value = true;
  try {
    const res = await api("orders.detail", { name: r.order });
    if (detailFor.value !== r.order) return;   // they moved on
    if (!res || !res.items) { detailError.value = t("cf.dFail"); return; }
    detail.value = res;
  } catch (e) {
    detailError.value = String(e.message || e);
  } finally {
    detailLoading.value = false;
  }
}

function doneClass(status) {
  if (status === "Confirmed") return "text-emerald-700 bg-emerald-50 ring-emerald-200";
  if (status === "Cancelled") return "text-rose-700 bg-rose-50 ring-rose-200";
  return "text-violet-700 bg-violet-50 ring-violet-200";
}
function doneIcon(status) {
  if (status === "Confirmed") return "check-circle";
  if (status === "Cancelled") return "x";
  return "copy";
}

const selected = ref(new Set());
const bulkReason = ref("");
const bulkBusy = ref(false);

function toggleAll() {
  selected.value = selected.value.size === rows.value.length
    ? new Set() : new Set(rows.value.map((r) => r.order));
}
function toggleOne(order) {
  const s = new Set(selected.value);
  s.has(order) ? s.delete(order) : s.add(order);
  selected.value = s;
}

async function bulkAct(action) {
  bulkBusy.value = true;
  try {
    const res = await apiPost("confirmation.bulk_act", {
      orders: [...selected.value], action, reason: bulkReason.value,
    });
    success(t("cf.bulkDone"), `${res.done}`);
    selected.value = new Set();
    bulkReason.value = "";
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    bulkBusy.value = false;
  }
}

async function bulkCancel() {
  bulkBusy.value = true;
  try {
    const res = await apiPost("confirmation.bulk_cancel", {
      orders: [...selected.value], reason: bulkReason.value,
    });
    success(t("cf.bulkDone"), `${res.done}`);
    selected.value = new Set();
    bulkReason.value = "";
    load();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    bulkBusy.value = false;
  }
}

async function act(r, action, note) {
  busy.value = r.order;
  try {
    const res = await apiPost("confirmation.act", { order: r.order, action, note });
    rows.value = rows.value.filter((x) => x.order !== r.order);
    total.value = Math.max(0, total.value - 1);
    if (data.value?.counts) {
      data.value.counts[tab.value] = Math.max(0, (data.value.counts[tab.value] || 1) - 1);
      if (action === "dna") data.value.counts.dna++;
      if (action === "followup" && tab.value !== "followup") data.value.counts.followup++;
      if (action === "onhold" && tab.value !== "onhold") data.value.counts.onhold++;
      // The row moves to a terminal tab — or back to pending on an undo.
      if (action === "confirm") data.value.counts.confirmed++;
      if (action === "cancel") data.value.counts.cancelled++;
      if (action === "duplicate") data.value.counts.duplicated++;
      if (action === "reopen") data.value.counts.pending++;
      if (data.value.mine && action in data.value.mine) data.value.mine[action]++;
    }
    cancelFor.value = "";
    cancelReason.value = "";
    if (detailFor.value === r.order) detailFor.value = "";
    if (custFor.value === r.order) custFor.value = "";
    success(t(`cf.done_${action}`), r.order + (res.attempts ? ` · ${t('cf.attempts')} ${res.attempts}` : ""));
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}

function toggleEdit(r) {
  if (editFor.value === r.order) { editFor.value = ""; return; }
  editFor.value = r.order;
  editPhone.value = r.phone || "";
  editCity.value = r.city || "";
}

async function saveContact(r) {
  savingContact.value = true;
  try {
    const res = await apiPost("confirmation.update_contact", {
      order: r.order, phone: editPhone.value, city: editCity.value,
    });
    if (!res.unchanged) {
      r.phone = editPhone.value.trim() || r.phone;
      r.city = editCity.value.trim() || r.city;
      success(t("cf.contactSaved"), (res.updated || []).join(" · "));
    }
    editFor.value = "";
  } catch (e) {
    warn(t("cf.contactFail"), String(e.message || e));
  } finally {
    savingContact.value = false;
  }
}

function waLink(phone) {
  const p = String(phone || "").replace(/[^0-9]/g, "");
  return "https://wa.me/" + (p.startsWith("212") ? p : "212" + p.replace(/^0/, ""));
}
function initial(name) {
  const w = String(name || "").trim().split(/\s+/);
  return ((w[0]?.[0] || "؟") + (w[1]?.[0] || "")).toUpperCase();
}
function ageLabel(h) {
  return h < 48 ? `${h}${t('cf.hrs')}` : `${Math.round(h / 24)}${t('cf.days')}`;
}
function ageColor(h) {
  if (h < 12) return "text-emerald-600";
  if (h < 48) return "text-amber-600";
  return "text-rose-500 font-medium";
}
function fmtMAD(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }
</script>

<style scoped>
/* ── hero ─────────────────────────────────────────────── */
.cf-hero {
  background: linear-gradient(135deg, var(--accent-50) 0%, #fff 45%, #fff 70%, var(--accent-50) 100%);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent-300) 45%, transparent),
              0 1px 2px rgb(0 0 0 / 0.03);
}
.cf-hero-icon {
  width: 52px; height: 52px; border-radius: 16px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: white;
  background: linear-gradient(135deg, var(--accent-500), var(--accent-700));
  box-shadow: 0 6px 16px -6px color-mix(in srgb, var(--accent-600) 55%, transparent);
}
.cf-stat {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-width: 78px; padding: 8px 14px; border-radius: 14px;
  background: rgb(255 255 255 / 0.75); backdrop-filter: blur(4px);
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.9), 0 1px 2px rgb(0 0 0 / 0.03);
}
.cf-prog {
  display: flex; flex-direction: column; align-items: flex-start;
  padding: 8px 12px; border-radius: 14px;
  background: rgb(255 255 255 / 0.75);
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.9), 0 1px 2px rgb(0 0 0 / 0.03);
  transition: transform .15s ease, box-shadow .15s ease;
}
.cf-prog:hover, .cf-stat-link:hover { transform: translateY(-1px); box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.cf-stat-link { transition: transform .15s ease, box-shadow .15s ease; }
.cf-stat-n { font-size: 21px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.cf-stat-l { font-size: 10px; font-weight: 600; color: rgb(168 162 158); margin-top: 4px; white-space: nowrap; }

/* ── segmented control ────────────────────────────────── */
.cf-seg {
  display: inline-flex; gap: 2px; padding: 4px;
  background: rgb(231 229 228 / 0.55); border-radius: 14px;
}
.cf-seg-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 36px; padding: 0 12px; border-radius: 11px;
  font-size: 12.5px; font-weight: 600; color: rgb(120 113 108);
  transition: all .18s ease;
}
.cf-seg-btn:hover { color: rgb(41 37 36); }
.cf-seg-on {
  background: white; color: rgb(28 25 23);
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.08), 0 1px 2px rgb(0 0 0 / 0.04);
}
.cf-seg-div {
  width: 1px; align-self: stretch; margin: 5px 5px;
  background: rgb(214 211 209 / .9);
  flex-shrink: 0;
}
/* Cleanup + archive: reachable, but never competing with the work queues. */
.cf-seg-alt { color: rgb(168 162 158); }
.cf-seg-alt.cf-seg-on { color: rgb(28 25 23); }
.cf-seg-count {
  font-size: 11px; font-weight: 700; font-variant-numeric: tabular-nums;
  padding: 1px 7px; border-radius: 999px;
}

/* ── row cards ────────────────────────────────────────── */
.cf-card {
  background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8), 0 1px 2px rgb(0 0 0 / 0.02);
  transition: box-shadow .18s ease, transform .18s ease;
}
.cf-card:hover {
  box-shadow: inset 0 0 0 1px rgb(214 211 209), 0 8px 24px -12px rgb(0 0 0 / 0.14);
  transform: translateY(-1px);
}
.cf-card-due {
  box-shadow: inset 0 0 0 1.5px rgb(252 211 77), 0 4px 16px -8px rgb(245 158 11 / 0.25);
}
.cf-avatar {
  width: 42px; height: 42px; border-radius: 999px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800; color: var(--accent-700);
  background: linear-gradient(135deg, var(--accent-50), var(--accent-100));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent-300) 50%, transparent);
}
.cf-avatar-due {
  color: rgb(180 83 9);
  background: linear-gradient(135deg, rgb(255 251 235), rgb(254 243 199));
  box-shadow: inset 0 0 0 1px rgb(252 211 77);
}
.cf-done {
  display: inline-flex; align-items: center; gap: 5px;
  height: 38px; padding: 0 12px; border-radius: 12px;
  font-size: 12px; font-weight: 700; white-space: nowrap;
  background: white; box-shadow: inset 0 0 0 1px currentColor;
}
.cf-due-badge {
  font-size: 10px; font-weight: 800; letter-spacing: .02em;
  color: white; background: rgb(245 158 11);
  padding: 2px 8px; border-radius: 999px;
  animation: cf-pulse 2s ease-in-out infinite;
}
@keyframes cf-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .55; }
}

/* ── contact + action buttons ─────────────────────────── */
.cf-contact {
  width: 38px; height: 38px; border-radius: 12px;
  display: inline-flex; align-items: center; justify-content: center;
  background: white; box-shadow: inset 0 0 0 1px rgb(231 229 228);
  transition: all .15s ease;
}
.cf-contact:hover { transform: scale(1.06); }
.cf-tel { color: rgb(87 83 78); }
.cf-tel:hover { color: rgb(4 120 87); box-shadow: inset 0 0 0 1px rgb(110 231 183); }
.cf-wa { color: rgb(22 163 74); }
.cf-wa:hover { box-shadow: inset 0 0 0 1px rgb(134 239 172); background: rgb(240 253 244); }
.cf-act {
  height: 38px; border-radius: 12px; font-size: 12.5px; font-weight: 700;
  transition: all .15s ease; white-space: nowrap;
}
.cf-act:disabled { opacity: .5; }
.cf-act-confirm {
  padding: 0 16px; color: white;
  background: linear-gradient(135deg, rgb(16 185 129), rgb(5 150 105));
  box-shadow: 0 4px 12px -4px rgb(16 185 129 / 0.4);
}
.cf-act-confirm:hover { box-shadow: 0 6px 16px -4px rgb(16 185 129 / 0.55); transform: translateY(-1px); }
.cf-act-soft {
  width: 38px; background: rgb(250 250 249);
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  --tw-ring-color: currentColor;
  /* Without this the button stays display:block and Tailwind's preflight makes
     the svg display:block too — so text-align can't reach it and every icon
     pins to the left edge. Every other *-soft button in the app has it. */
  display: inline-flex; align-items: center; justify-content: center;
}
.cf-act-soft:hover { background: white; transform: scale(1.06); box-shadow: inset 0 0 0 1px currentColor; }

/* ── empty / shimmer / pager ──────────────────────────── */
.cf-empty {
  background: linear-gradient(180deg, white, rgb(250 250 249));
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / 0.8);
}
.cf-shimmer {
  background: linear-gradient(90deg, rgb(245 245 244) 25%, rgb(231 229 228 / 0.6) 50%, rgb(245 245 244) 75%);
  background-size: 200% 100%;
  animation: cf-shimmer 1.4s ease-in-out infinite;
}
@keyframes cf-shimmer { to { background-position: -200% 0; } }
.pg-btn {
  width: 32px; height: 32px; border-radius: 10px; background: white;
  box-shadow: inset 0 0 0 1px rgb(231 229 228);
  display: inline-flex; align-items: center; justify-content: center;
}
.pg-btn:disabled { opacity: .4; }

/* ── list + panel animations ──────────────────────────── */
.cfrow-leave-active { transition: all .28s ease; position: relative; }
.cfrow-leave-to { opacity: 0; transform: translateX(24px) scale(.98); }
.cfrow-enter-active { transition: all .25s ease; }
.cfrow-enter-from { opacity: 0; transform: translateY(6px); }
.cfrow-move { transition: transform .28s ease; }
.cfslide-enter-active, .cfslide-leave-active { transition: all .2s ease; }
.cfslide-enter-from, .cfslide-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
