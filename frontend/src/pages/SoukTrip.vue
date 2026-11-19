<template>
  <!-- The custody (العهدة). The accountant hands the buyer the cash and opens
       the trip; every purchase is deducted; the buyer closes the day and the
       accountant counts what came back. A purchase without a receipt carries a
       substitute (photo of the goods + the stall's name and phone) the
       accountant approves before counting. The buyer's writes (receipt photo,
       substitute, taxi) go through the outbox (lib/soukOutbox) — the market's
       line drops. Backend: souk.trips_boot / open_trip / set_transport /
       set_voucher / approve_voucher / close_trip / count_trip.
       LOOK = design Trip.dc.html: white header, the dark custody card, the
       purchases, transport, the amber missing-receipt notice, the steps after
       the close and a fixed footer with the close button. The accounts moved
       to the souk settings (SoukSettings). -->
  <div>
    <header class="bg-white border-b border-stone-200">
      <div class="max-w-[600px] mx-auto px-4 py-3.5 flex flex-col gap-1.5">
        <template v-if="solo">
          <div class="flex items-center justify-between gap-2">
            <span class="min-w-0 truncate text-[12px] font-semibold text-stone-500">
              {{ tt('souk.buy.trip.custodyOf', { name: solo.buyerName }) }} · #{{ solo.name }}
            </span>
            <span class="shrink-0 text-[11px] font-bold rounded-md px-2 py-0.5" :class="pill(solo)">{{ stLabel(solo) }}</span>
          </div>
          <h1 class="text-[16px] font-bold text-stone-900">{{ solo.place }} · {{ day(solo.opened) }}</h1>
          <div v-if="solo.buyer === data.me" class="flex items-center gap-1.5 text-[12px] text-stone-600" aria-live="polite">
            <span class="w-[7px] h-[7px] rounded-full shrink-0" :class="waiting ? 'bg-amber-500' : 'bg-emerald-700'" />
            <span class="min-w-0">{{ waiting ? tt('souk.buy.trip.waitingLine', { n: waiting }) : t('souk.buy.trip.savedLine') }}</span>
          </div>
        </template>
        <template v-else>
          <h1 class="text-[16px] font-bold text-stone-900">{{ t('souk.custodyTitle') }}</h1>
          <p class="text-[12px] text-stone-600 leading-normal">{{ t('souk.custodyIntro') }}</p>
        </template>
      </div>
    </header>

    <div class="max-w-[600px] mx-auto px-4 pt-3.5 flex flex-col gap-3.5" :class="footTrip ? 'pb-44' : 'pb-6'">
      <div v-if="loading && !data" class="h-[260px] lp-card animate-pulse" />

      <!-- accountant: hand out a custody -->
      <section v-if="data?.isAccountant" class="lp-card p-3.5 space-y-3">
        <h2 class="text-[14px] font-bold text-stone-900">{{ t('souk.handOut') }}</h2>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <div class="space-y-1.5">
            <label for="st-buyer" class="block text-[13px] font-semibold text-stone-700">{{ t('souk.buy.trip.buyerLbl') }}</label>
            <select id="st-buyer" v-model="give.buyer" class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 px-2.5 text-[15px] bg-white">
              <option value="">{{ t('souk.buyer') }}</option>
              <option v-for="b in data.buyers" :key="b.user" :value="b.user">{{ b.name }}</option>
            </select>
          </div>
          <div class="space-y-1.5">
            <label for="st-cash" class="block text-[13px] font-semibold text-stone-700">{{ t('souk.buy.trip.cashLbl') }}</label>
            <input id="st-cash" v-model.number="give.cash" type="number" inputmode="decimal" min="0" placeholder="0"
                   class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 px-3 text-[16px] tabular-nums bg-white" />
          </div>
          <div class="space-y-1.5">
            <label for="st-place" class="block text-[13px] font-semibold text-stone-700">{{ t('souk.buy.trip.placeLbl') }}</label>
            <input id="st-place" v-model="give.place" placeholder="Derb Omar" class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 px-3 text-[16px] bg-white" />
          </div>
        </div>
        <button class="h-11 px-5 rounded-[10px] bg-[var(--accent-600)] text-white text-[14px] font-bold disabled:opacity-40"
                :disabled="busy || !give.buyer || !(give.cash > 0)" @click="openTrip">
          {{ t('souk.handOutBtn').replace('{n}', fmt(give.cash || 0)) }}
        </button>
      </section>

      <div v-if="data && !data.open.length" class="lp-card p-8 text-center text-[14px] text-stone-500">
        {{ data.isAccountant ? t('souk.noOpenTrips') : t('souk.noTrip') }}
      </div>

      <!-- one group per open / closed trip -->
      <template v-for="tr in data?.open || []" :key="tr.name">
        <!-- several trips (the accountant): each says whose it is -->
        <div v-if="!solo" class="pt-1.5 space-y-1">
          <div class="flex items-center justify-between gap-2">
            <span class="min-w-0 truncate text-[12px] font-semibold text-stone-500">
              {{ tt('souk.buy.trip.custodyOf', { name: tr.buyerName }) }} · #{{ tr.name }}
            </span>
            <span class="shrink-0 text-[11px] font-bold rounded-md px-2 py-0.5" :class="pill(tr)">{{ stLabel(tr) }}</span>
          </div>
          <h2 class="text-[15px] font-bold text-stone-900">{{ tr.place }} · {{ day(tr.opened) }}</h2>
          <div v-if="tr.openedBy" class="text-[12px] text-stone-500">{{ tt('souk.buy.trip.openedBy', { n: tr.openedBy }) }} · {{ when(tr.opened) }}</div>
        </div>

        <!-- the cash -->
        <section :aria-label="t('souk.custody')" class="rounded-[14px] bg-stone-900 text-white p-4 flex flex-col gap-3">
          <div class="flex flex-col gap-0.5">
            <span class="text-[12px] text-stone-300">{{ tr.status === 'Open' ? t('souk.shouldHave') : t('souk.toHandBack') }}</span>
            <span class="text-[28px] leading-tight font-extrabold tabular-nums">
              {{ fmt(tr.status === 'Open' ? tr.expected : tr.expectedBack) }} <small class="text-[14px] font-semibold text-stone-300">MAD</small>
            </span>
          </div>
          <div class="grid grid-cols-3 gap-2 tabular-nums">
            <div class="flex flex-col justify-between gap-0.5 min-w-0"><span class="text-[11px] leading-tight text-stone-300">{{ t('souk.fromAccountant') }}</span><span class="text-[15px] font-bold">{{ fmt(tr.cashGiven) }}</span></div>
            <div class="flex flex-col justify-between gap-0.5 min-w-0"><span class="text-[11px] leading-tight text-stone-300">{{ t('souk.goods') }}</span><span class="text-[15px] font-bold">{{ fmt(tr.goods) }}</span></div>
            <div class="flex flex-col justify-between gap-0.5 min-w-0"><span class="text-[11px] leading-tight text-stone-300">{{ t('souk.transport') }}</span><span class="text-[15px] font-bold">{{ fmt(tr.transport) }}</span></div>
          </div>
        </section>

        <!-- a product still being created on Shopify blocks the close -->
        <section v-if="tr.creating > 0" class="rounded-xl bg-amber-50 ring-1 ring-inset ring-amber-200 px-3.5 py-2.5 flex items-center gap-2.5">
          <Icon name="hourglass" :size="16" class="text-amber-700 shrink-0" />
          <span class="flex-1 text-[13px] text-amber-800 leading-normal">{{ tt('souk.buy.trip.creating', { n: tr.creating }) }}</span>
          <button class="shrink-0 h-11 px-3 rounded-lg bg-white ring-1 ring-inset ring-amber-200 text-amber-800 text-[13px] font-semibold disabled:opacity-40"
                  :disabled="loading" @click="load">{{ t('souk.buy.trip.refresh') }}</button>
        </section>

        <!-- purchases -->
        <section class="lp-card overflow-hidden">
          <div class="min-h-[44px] ps-3.5 pe-1.5 pt-1 flex items-center justify-between gap-2">
            <h2 class="text-[14px] font-bold text-stone-900">{{ t('souk.purchases') }} · {{ tr.buys.length }}</h2>
            <router-link v-if="tr.status === 'Open' && tr.buyer === data.me && data.canBuy" :to="{ name: 'SoukBuy' }"
                         class="min-h-[44px] px-2 inline-flex items-center text-[13px] font-semibold text-[var(--accent-700)] hover:text-[var(--accent-800)]">{{ t('souk.buy.trip.newBuy') }}</router-link>
          </div>
          <div v-for="b in tr.buys" :key="b.po" class="px-3.5 py-2.5 border-t border-stone-100 space-y-2">
            <div class="flex items-center gap-2.5">
              <img v-if="b.image" :src="b.image" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 shrink-0" alt="" loading="lazy" />
              <div v-else class="w-10 h-10 rounded-lg bg-stone-100 shrink-0 flex items-center justify-center"><Icon name="package" :size="16" class="text-stone-500" /></div>
              <div class="min-w-0 flex-1 flex flex-col">
                <span class="text-[13px] font-semibold text-stone-900 truncate">{{ b.title || b.po }}</span>
                <span class="text-[12px] text-stone-600 truncate">{{ b.supplier }} · {{ b.units }} {{ t('souk.pcs') }}</span>
                <span class="text-[12px] truncate">
                  <span v-if="b.received" class="text-emerald-700 font-semibold">{{ t('souk.receivedAs').replace('{pr}', b.received) }}</span>
                  <router-link v-else-if="data.canReceive" :to="{ name: 'SoukReceive', params: { po: b.po } }" class="font-semibold text-[var(--accent-700)] underline underline-offset-2">{{ t('souk.receiveBtn') }}</router-link>
                  <span v-else class="text-stone-500">{{ t('souk.notReceived') }}</span>
                  <span v-if="b.owed" class="ms-1.5 font-semibold text-amber-800">{{ t('souk.owesShort').replace('{n}', fmt(b.owed)) }}<span v-if="b.debitNote" class="mono"> · {{ b.debitNote }}</span></span>
                  <template v-if="b.title"> · <span class="mono text-stone-500" dir="ltr">{{ b.po }}</span></template>
                </span>
              </div>
              <div class="flex flex-col items-end gap-0.5 shrink-0">
                <span class="text-[13px] font-bold tabular-nums text-stone-900">{{ fmt(b.amount) }}</span>
                <span class="text-[11px] font-bold rounded-[5px] px-1.5 py-px" :class="rcls(b.receipt)">{{ t('souk.rc_' + b.receipt) }}</span>
              </div>
            </div>

            <!-- a write of this row waiting on the phone / refused -->
            <div v-if="slot(b.po)" class="text-[12px] font-semibold flex items-center gap-2"
                 :class="slot(b.po).s === 'failed' ? 'text-rose-700' : 'text-stone-600'">
              <Icon :name="slot(b.po).s === 'failed' ? 'alert-triangle' : slot(b.po).s === 'queued' ? 'upload-cloud' : 'refresh-cw'" :size="13" class="shrink-0" />
              <span class="flex-1 min-w-0 break-words" dir="auto">{{ slotText(slot(b.po)) }}</span>
              <button v-if="slot(b.po).s === 'failed'" class="shrink-0 h-11 px-3 rounded-lg ring-1 ring-inset ring-rose-300 text-rose-700 font-bold" @click="retrySlot(b.po)">{{ t('souk.buy.trip.retry') }}</button>
            </div>

            <!-- substitute receipt: what the accountant checks -->
            <div v-if="b.receipt === 'voucher_pending' || b.receipt === 'voucher_ok'"
                 class="rounded-lg p-2.5 flex items-center gap-3 ring-1 ring-inset"
                 :class="b.receipt === 'voucher_pending' ? 'bg-amber-50 ring-amber-200' : 'bg-stone-50 ring-stone-200'">
              <a v-if="b.voucherPhoto" :href="b.voucherPhoto" target="_blank" rel="noopener" :aria-label="t('souk.buy.trip.openPhoto')"
                 class="w-14 h-14 rounded-lg overflow-hidden ring-1 ring-stone-300 shrink-0">
                <img :src="b.voucherPhoto" class="w-full h-full object-cover" alt="" loading="lazy" />
              </a>
              <div class="flex-1 min-w-0 text-[13px] space-y-0.5">
                <div v-if="b.receipt === 'voucher_pending' && data.isAccountant" class="text-[12px] font-bold text-amber-800">{{ t('souk.buy.trip.vCheck') }}</div>
                <div class="font-semibold text-stone-900 truncate">{{ b.voucherStall || b.supplier }}</div>
                <a v-if="b.phone" :href="'tel:' + b.phone" class="inline-flex items-center gap-1 min-h-[28px] text-stone-700 tabular-nums" dir="ltr">
                  <Icon name="phone" :size="12" />{{ b.phone }}
                </a>
                <div v-if="b.receipt === 'voucher_ok' && b.voucherBy" class="text-[12px] text-emerald-700 font-semibold">{{ tt('souk.buy.trip.vApprovedBy', { n: b.voucherBy }) }}</div>
              </div>
              <div v-if="data.isAccountant && b.receipt === 'voucher_pending'" class="shrink-0 flex flex-col gap-1.5">
                <button class="h-11 px-4 rounded-lg bg-[var(--accent-600)] text-white text-[13px] font-bold disabled:opacity-40"
                        :disabled="busy" @click="approve(b)">{{ t('souk.approve') }}</button>
                <button class="h-11 px-4 rounded-lg bg-white ring-1 ring-inset ring-rose-200 text-rose-700 text-[13px] font-semibold disabled:opacity-40"
                        :disabled="busy" @click="refuse(b)">{{ t('souk.buy.trip.vRefuse') }}</button>
              </div>
            </div>
          </div>
        </section>

        <!-- transport -->
        <section v-if="tr.status === 'Open'" class="lp-card px-3.5 py-3 flex flex-col gap-2">
          <h2 class="text-[14px] font-bold text-stone-900">{{ t('souk.buy.trip.transportTitle') }}</h2>
          <div class="flex items-end gap-2">
            <div class="flex-1 min-w-0 flex flex-col gap-1.5">
              <label :for="'st-taxi-' + tr.name" class="text-[13px] font-semibold text-stone-700">{{ t('souk.taxi') }}</label>
              <div class="relative">
                <input :id="'st-taxi-' + tr.name" v-model.number="transport[tr.name]" type="number" inputmode="decimal" min="0" placeholder="0"
                       class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white ps-3 pe-12 text-[16px] tabular-nums" @change="saveTransport(tr)" />
                <span class="absolute inset-y-0 end-3 flex items-center text-[13px] text-stone-500 pointer-events-none">MAD</span>
              </div>
            </div>
            <label class="w-11 h-11 shrink-0 rounded-lg ring-1 ring-inset inline-flex items-center justify-center cursor-pointer"
                   :class="tr.transportReceipt ? 'ring-emerald-300 bg-emerald-50 text-emerald-700' : 'ring-stone-200 bg-stone-100 text-stone-700'"
                   :aria-label="t('souk.buy.trip.transportPhoto')" :title="t('souk.buy.trip.transportPhoto')">
              <Icon :name="tr.transportReceipt ? 'check' : 'camera'" :size="18" />
              <input type="file" accept="image/*" capture="environment" class="hidden" @change="(e) => transportReceipt(tr, e)" />
            </label>
          </div>
          <div v-if="slot('tr:' + tr.name)" class="text-[12px] font-semibold flex items-center gap-2"
               :class="slot('tr:' + tr.name).s === 'failed' ? 'text-rose-700' : 'text-stone-600'">
            <Icon :name="slot('tr:' + tr.name).s === 'failed' ? 'alert-triangle' : 'upload-cloud'" :size="13" class="shrink-0" />
            <span class="flex-1 min-w-0 break-words" dir="auto">{{ slotText(slot('tr:' + tr.name)) }}</span>
            <button v-if="slot('tr:' + tr.name).s === 'failed'" class="shrink-0 h-11 px-3 rounded-lg ring-1 ring-inset ring-rose-300 text-rose-700 font-bold" @click="retrySlot('tr:' + tr.name)">{{ t('souk.buy.trip.retry') }}</button>
          </div>
          <p class="text-[12px] text-stone-600 leading-normal">{{ t('souk.taxiHint') }}</p>
        </section>

        <!-- transport by weight (accountant), once everything is received -->
        <section v-if="data.isAccountant && tr.transport > 0" class="lp-card px-3.5 py-2 min-h-[56px] flex items-center gap-2 text-[13px]">
          <span v-if="tr.transportLcv" class="text-emerald-700 font-semibold">{{ t('souk.transportDone').replace('{v}', tr.transportLcv) }}</span>
          <template v-else>
            <span class="flex-1 text-stone-600">{{ tr.allReceived ? t('souk.transportReady') : t('souk.transportWait') }}</span>
            <button class="shrink-0 h-11 px-3 rounded-lg bg-stone-900 text-white text-[13px] font-bold disabled:opacity-40"
                    :disabled="busy || !tr.allReceived || !data.accounts?.custody" @click="allocate(tr)">{{ t('souk.transportBtn') }}</button>
          </template>
        </section>

        <!-- the buyer's purchases without a receipt: photo it, or a substitute -->
        <template v-for="b in missingMine(tr)" :key="'m-' + b.po">
          <section v-if="vForm.po !== b.po" class="rounded-xl bg-amber-50 ring-1 ring-inset ring-amber-200 px-3.5 py-3 flex gap-2 items-start">
            <Icon name="alert-triangle" :size="16" :stroke-width="2" class="text-amber-700 shrink-0 mt-0.5" />
            <div class="flex-1 min-w-0 flex flex-col gap-2">
              <p class="text-[13px] text-amber-800 leading-normal">{{ tt('souk.buy.trip.missingOne', { title: b.title || b.po }) }}</p>
              <div class="flex flex-wrap gap-2">
                <button class="h-11 px-3 rounded-lg bg-white ring-1 ring-inset ring-amber-200 text-[13px] font-semibold text-amber-800" @click="openVoucher(b)">{{ t('souk.buy.trip.substitute') }}</button>
                <label class="h-11 px-3 rounded-lg bg-white ring-1 ring-inset ring-amber-200 text-[13px] font-semibold text-amber-800 inline-flex items-center gap-1.5 cursor-pointer">
                  <Icon name="camera" :size="14" />{{ t('souk.addReceipt') }}
                  <input type="file" accept="image/*" capture="environment" class="hidden" @change="(e) => receipt(b, e)" />
                </label>
              </div>
            </div>
          </section>

          <!-- substitute receipt: goods photo + stall name + phone -->
          <section v-else class="lp-card p-3.5 space-y-3">
            <h2 class="text-[14px] font-bold text-stone-900">{{ t('souk.buy.trip.vTitle') }} · <span class="mono text-[12px] font-medium text-stone-500" dir="ltr">{{ b.po }}</span></h2>
            <div class="flex items-center gap-3">
              <div class="w-16 h-16 rounded-[10px] bg-stone-100 overflow-hidden flex items-center justify-center shrink-0">
                <img v-if="vForm.preview" :src="vForm.preview" class="w-full h-full object-cover" alt="" />
                <Icon v-else name="image" :size="20" class="text-stone-500" />
              </div>
              <label class="h-11 px-3 rounded-lg bg-stone-100 ring-1 ring-inset ring-stone-200 text-[13px] font-semibold text-stone-700 inline-flex items-center gap-1.5 cursor-pointer">
                <Icon name="camera" :size="14" />{{ t('souk.buy.trip.vPhoto') }}
                <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickVoucherPhoto" />
              </label>
            </div>
            <div class="space-y-1.5">
              <label :for="'st-vs-' + b.po" class="block text-[13px] font-semibold text-stone-700">{{ t('souk.buy.trip.vStall') }}</label>
              <input :id="'st-vs-' + b.po" v-model="vForm.stall" class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px]" />
            </div>
            <div class="space-y-1.5">
              <label :for="'st-vp-' + b.po" class="block text-[13px] font-semibold text-stone-700">{{ t('souk.buy.trip.vPhone') }}</label>
              <input :id="'st-vp-' + b.po" v-model="vForm.phone" type="tel" inputmode="tel" dir="ltr" placeholder="06…"
                     class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px] tabular-nums" />
            </div>
            <p v-if="vWhy" class="text-[12px] font-semibold text-amber-800">{{ vWhy }}</p>
            <div class="grid grid-cols-2 gap-2">
              <button class="h-11 rounded-lg bg-white ring-1 ring-inset ring-stone-300 text-[13px] font-semibold text-stone-700" @click="closeVoucher">{{ t('souk.buy.trip.cancel') }}</button>
              <button class="h-11 rounded-lg bg-[var(--accent-600)] text-white text-[13px] font-bold disabled:opacity-40" :disabled="!!vWhy" @click="sendVoucher(b)">{{ t('souk.buy.trip.vSend') }}</button>
            </div>
          </section>
        </template>

        <!-- what happens after the close -->
        <section class="lp-card px-3.5 py-3 flex flex-col gap-2">
          <h2 class="text-[14px] font-bold text-stone-900">{{ tr.status === 'Open' ? t('souk.buy.trip.afterTitle') : t('souk.buy.trip.nextTitle') }}</h2>
          <div v-if="tr.status !== 'Open' && tr.closedAt" class="text-[12px] text-stone-500">{{ tt('souk.buy.trip.closedAt', { when: when(tr.closedAt) }) }}</div>
          <ol class="flex flex-col gap-1.5 text-[13px] text-stone-700 leading-normal">
            <li v-for="s in steps(tr)" :key="s.n" class="flex items-start gap-1.5">
              <span class="shrink-0 min-w-[14px] tabular-nums" :class="s.state === 'done' ? 'text-emerald-700 pt-[2px]' : s.state === 'now' ? 'font-bold text-[var(--accent-700)]' : ''">
                <Icon v-if="s.state === 'done'" name="check" :size="13" :stroke-width="2.4" /><template v-else>{{ s.n }}.</template>
              </span>
              <span class="flex-1 min-w-0">
                <span :class="s.state === 'now' ? 'font-semibold text-stone-900' : ''">{{ s.text }}</span>
                <span v-if="s.sub" class="text-stone-500 tabular-nums"> · {{ s.sub }}</span>
              </span>
            </li>
          </ol>
        </section>

        <!-- close (buyer) — a second open trip of the same buyer closes here;
             the first one closes from the fixed footer -->
        <div v-if="tr.status === 'Open' && tr.buyer === data.me && tr !== footTrip" class="space-y-1.5">
          <p v-if="tr.missingReceipts" class="text-[12px] text-stone-600 text-center">{{ t('souk.missingN').replace('{n}', tr.missingReceipts) }}</p>
          <button class="w-full min-h-[50px] px-3 py-2 rounded-[10px] bg-[var(--accent-600)] text-white text-[15px] leading-snug font-bold disabled:bg-stone-200 disabled:text-stone-600"
                  :disabled="busy || !tr.canClose" @click="close(tr)">
            {{ t('souk.closeBtn').replace('{n}', fmt(tr.expected)) }}
          </button>
        </div>

        <!-- count (accountant) -->
        <section v-if="tr.status === 'Closed' && data.isAccountant" class="lp-card p-3.5 space-y-2.5">
          <h2 class="text-[14px] font-bold text-stone-900">{{ t('souk.countTitle').replace('{n}', fmt(tr.expectedBack)) }}</h2>
          <p v-if="tr.pendingVouchers" class="text-[12px] text-amber-800">{{ t('souk.approveFirst').replace('{n}', tr.pendingVouchers) }}</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div class="space-y-1.5">
              <label :for="'st-count-' + tr.name" class="block text-[13px] font-semibold text-stone-700">{{ t('souk.buy.trip.countedLbl') }}</label>
              <input :id="'st-count-' + tr.name" v-model.number="count[tr.name]" type="number" inputmode="decimal" min="0" placeholder="0"
                     class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px] tabular-nums" />
            </div>
            <div class="space-y-1.5">
              <label :for="'st-note-' + tr.name" class="block text-[13px] font-semibold text-stone-700">{{ t('souk.buy.trip.noteLbl') }}</label>
              <input :id="'st-note-' + tr.name" v-model="countNote[tr.name]" class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px]" />
            </div>
          </div>
          <p v-if="count[tr.name] !== undefined && count[tr.name] !== '' && diff(tr) !== 0" class="text-[13px] font-semibold" :class="diff(tr) < 0 ? 'text-rose-600' : 'text-emerald-700'">
            {{ t('souk.diff').replace('{n}', (diff(tr) > 0 ? '+' : '') + fmt(diff(tr))) }}
          </p>
          <button class="h-11 px-5 rounded-[10px] bg-[var(--accent-600)] text-white text-[14px] font-bold disabled:opacity-40"
                  :disabled="busy || tr.pendingVouchers || count[tr.name] === undefined || count[tr.name] === ''" @click="doCount(tr)">
            {{ t('souk.countBtn') }}
          </button>
        </section>
      </template>

      <!-- counted -->
      <section v-if="data?.counted?.length" class="lp-card overflow-hidden">
        <h2 class="px-3.5 pt-3 pb-2 text-[14px] font-bold text-stone-900">{{ t('souk.counted') }}</h2>
        <div v-for="tr in data.counted" :key="tr.name" class="px-3.5 py-2.5 border-t border-stone-100 flex items-center gap-3 text-[13px]">
          <div class="flex-1 min-w-0">
            <div class="truncate text-stone-900"><span class="text-stone-500 mono">#{{ tr.name }}</span> · {{ tr.buyerName }} · {{ tr.place }}</div>
            <div class="text-[12px] text-stone-500 truncate">{{ when(tr.countedAt) }}<span v-if="tr.countedBy"> · {{ tr.countedBy }}</span></div>
          </div>
          <span class="tabular-nums text-stone-600 shrink-0">{{ fmt(tr.counted) }} / {{ fmt(tr.expectedBack) }}</span>
          <span class="tabular-nums font-bold shrink-0" :class="tr.counted - tr.expectedBack < 0 ? 'text-rose-600' : 'text-stone-500'">
            {{ Math.round(tr.counted - tr.expectedBack) === 0 ? '✓' : fmt(tr.counted - tr.expectedBack) }}
          </span>
          <button v-if="data.isAccountant && tr.transport > 0 && !tr.transportLcv"
                  class="shrink-0 h-11 px-3 rounded-lg bg-stone-900 text-white text-[12px] font-bold disabled:opacity-40"
                  :disabled="busy || !tr.allReceived || !data.accounts?.custody"
                  :title="tr.allReceived ? '' : t('souk.transportWait')" @click="allocate(tr)">{{ t('souk.transportBtn') }}</button>
        </div>
      </section>

      <!-- elsewhere: the souk accounts (now in the settings) and the launch board -->
      <nav class="lp-card overflow-hidden">
        <router-link v-if="data?.accounts && hasSettings" :to="{ name: 'SoukSettings' }"
                     class="min-h-[52px] px-3.5 py-2 flex items-center gap-2.5 hover:bg-stone-50">
          <Icon name="settings" :size="16" class="text-stone-500 shrink-0" />
          <span class="flex-1 min-w-0 flex flex-col">
            <span class="text-[13px] font-semibold text-stone-900">{{ t('souk.accounts') }}</span>
            <span class="text-[12px] truncate" :class="data.accounts.custody ? 'text-stone-500' : 'font-semibold text-amber-700'">
              {{ data.accounts.custody ? t('souk.buy.trip.settingsSub') : t('souk.noBooks') }}
            </span>
          </span>
          <Icon name="chevron-right" :size="16" class="text-stone-500 shrink-0 rtl:rotate-180" />
        </router-link>
        <router-link :to="{ name: 'SoukBoard' }"
                     class="min-h-[48px] px-3.5 py-2 flex items-center gap-2.5 hover:bg-stone-50"
                     :class="data?.accounts && hasSettings ? 'border-t border-stone-100' : ''">
          <Icon name="layout-grid" :size="16" class="text-stone-500 shrink-0" />
          <span class="flex-1 min-w-0 text-[13px] font-semibold text-stone-900">{{ t('souk.board') }}</span>
          <Icon name="chevron-right" :size="16" class="text-stone-500 shrink-0 rtl:rotate-180" />
        </router-link>
      </nav>
    </div>

    <!-- close (buyer): fixed above the phone tab bar -->
    <footer v-if="footTrip" class="lp-footer px-4 pt-3 pb-4">
      <div class="max-w-[600px] mx-auto flex flex-col gap-1.5">
        <p v-if="footTrip.missingReceipts" class="text-[12px] text-stone-600 text-center">{{ t('souk.missingN').replace('{n}', footTrip.missingReceipts) }}</p>
        <button class="w-full min-h-[50px] px-3 py-2 rounded-[10px] bg-[var(--accent-600)] text-white text-[15px] leading-snug font-bold disabled:bg-stone-200 disabled:text-stone-600"
                :disabled="busy || !footTrip.canClose" @click="close(footTrip)">
          {{ t('souk.closeBtn').replace('{n}', fmt(footTrip.expected)) }}
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { shrink } from "@/lib/soukPhoto";
import { outbox, enqueue, onDone, retry as retryJob, newKey } from "@/lib/soukOutbox";
import { siteToDate } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t, locale } = useI18n();
const { success, warn } = useToast();
const router = useRouter();
const tt = (k, vars = {}) => {
  let s = String(t(k));
  for (const [a, b] of Object.entries(vars)) s = s.split("{" + a + "}").join(String(b ?? ""));
  return s;
};
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const give = reactive({ buyer: "", cash: null, place: "Derb Omar" });
const transport = reactive({});
const count = reactive({});
const countNote = reactive({});
const st = reactive({});   // slot (po | "tr:<trip>") → {s: sending|queued|failed, e, jobId}

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const diff = (tr) => Math.round((Number(count[tr.name]) || 0) - tr.expectedBack);
function rcls(r) {
  return { ok: "bg-emerald-50 text-emerald-700", voucher_ok: "bg-emerald-50 text-emerald-700",
           voucher_pending: "bg-amber-50 text-amber-800", missing: "bg-amber-50 text-amber-700" }[r];
}
const pill = (tr) => (tr.status === "Open" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800");
const stLabel = (tr) => (tr.status === "Open" ? t("souk.stOpen") : t("souk.stClosed"));

// One trip on the screen (the buyer's day): the header IS that trip, as in
// the design. The accountant sees several, each with its own heading.
const solo = computed(() => (data.value && !data.value.isAccountant && data.value.open.length === 1 ? data.value.open[0] : null));
// The buyer's open trip closes from the fixed footer.
const footTrip = computed(() => (data.value?.open || []).find((tr) => tr.status === "Open" && tr.buyer === data.value.me) || null);
// Writes still on the phone (the header's "saved" line says how many).
const waiting = computed(() => outbox.jobs.length);
// The souk accounts live in the settings page (route SoukSettings); the link
// only shows once that screen exists in this build.
const hasSettings = computed(() => router.hasRoute("SoukSettings"));
// The buyer's purchases without a receipt and nothing on its way for them.
function missingMine(tr) {
  if (tr.status !== "Open" || tr.buyer !== data.value?.me) return [];
  return tr.buys.filter((b) => b.receipt === "missing" && !(slot(b.po) && slot(b.po).s !== "failed"));
}

// "today 14:20", "yesterday 09:05", "Tuesday 17:40", "Tue 3 Nov 10:12" — on
// the reader's own clock (stored times are the site's, lib/clock).
const p2 = (n) => String(n).padStart(2, "0");
const dateLocale = computed(() => ({ ar: "ar-EG-u-nu-latn", fr: "fr-FR" }[locale.value] || "en-GB"));
function toDate(s) {
  if (!s) return null;
  const d = siteToDate(s);
  if (d) return d;
  const m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/.exec(String(s));
  return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) : null;
}
// The trip's day for its heading: "Tuesday 17 November".
function day(s) {
  const d = toDate(s);
  if (!d) return s ? String(s).slice(0, 10) : "";
  try {
    return d.toLocaleDateString(dateLocale.value, { weekday: "long" }) + " "
      + d.toLocaleDateString(dateLocale.value, { day: "numeric", month: "long" });
  } catch (_) {
    return String(s).slice(0, 10);
  }
}
function when(s) {
  if (!s) return "";
  const d = toDate(s);
  if (!d) return String(s);
  const hm = `${p2(d.getHours())}:${p2(d.getMinutes())}`;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const day = new Date(d);
  day.setHours(0, 0, 0, 0);
  const n = Math.round((today - day) / 86400000);
  if (n === 0) return tt("souk.buy.trip.today", { t: hm });
  if (n === 1) return tt("souk.buy.trip.yesterday", { t: hm });
  try {
    const opts = n > 1 && n < 7 ? { weekday: "long" } : { weekday: "short", day: "numeric", month: "short" };
    return d.toLocaleDateString(dateLocale.value, opts) + " " + hm;
  } catch (_) {
    return String(s).slice(0, 16);
  }
}

function steps(tr) {
  const n = tr.buys.length;
  const r = tr.buys.filter((b) => b.received).length;
  const open = tr.status === "Open";
  return [
    { n: 1, text: t("souk.buy.trip.step1"), state: open ? "todo" : "now" },
    { n: 2, text: t("souk.buy.trip.step2"), state: "todo" },
    { n: 3, text: t("souk.buy.trip.step3"), state: n && r === n ? "done" : "todo",
      sub: n ? tt("souk.buy.trip.receivedN", { r, n }) : "" },
  ];
}

async function run(fn, okMsg) {
  busy.value = true;
  try {
    await fn();
    if (okMsg) success(okMsg);
    await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

// ── the buyer's writes, through the outbox ───────────────────────────────────
// Which row a waiting job belongs to, from its id (receipt-<po>,
// voucher-<po>, transport-amount|photo-<trip>…): a reload still shows that a
// write is waiting on the phone, so it is not entered twice.
function jobSlot(id) {
  let m = /^(?:receipt|voucher)-(.+)$/.exec(id || "");
  if (m) return m[1];
  m = /^transport-(?:amount|photo)-([^-]+)/.exec(id || "");
  return m ? "tr:" + m[1] : "";
}
function slot(key) {
  if (st[key]) return st[key];
  const j = outbox.jobs.find((x) => jobSlot(x.id) === key);
  return j ? { s: j.failed ? "failed" : "queued", e: j.error, jobId: j.id } : null;
}
function slotText(x) {
  if (x.s === "failed") return tt("souk.buy.trip.photoFailed", { e: x.e || "" });
  if (x.s === "queued") return t("souk.buy.trip.queued");
  return t("souk.buy.trip.sending");
}
// While a write runs the row says "sending"; once it waits or is refused the
// outbox itself is the truth (slot() reads it), so a job retried or
// discarded from the shell's list never leaves a stale line here.
function settle(key, jobId, e) {
  const kept = outbox.jobs.some((x) => x.id === jobId);
  if (e && !kept) st[key] = { s: "failed", e: String((e && e.message) || e), jobId };
  else delete st[key];
}
async function send(key, job) {
  st[key] = { s: "sending", jobId: job.id };
  try {
    const r = await enqueue(job);
    settle(key, job.id);
    if (!(r && r.queued)) await load();
    return true;
  } catch (e) {
    settle(key, job.id, e);
    return false;
  }
}
async function retrySlot(key) {
  const x = slot(key);
  if (!x) return;
  st[key] = { s: "sending", jobId: x.jobId };
  try {
    const r = await retryJob(x.jobId);
    settle(key, x.jobId);
    if (!(r && r.queued)) await load();
  } catch (e) {
    settle(key, x.jobId, e);
  }
}

async function receipt(b, e) {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (!file) return;
  const blob = await shrink(file);
  send(b.po, { id: "receipt-" + b.po, kind: "photo", label: `${t("souk.receipt")} · ${b.title || b.po}`,
               photoKind: "receipt", target: b.po, blob });
}

const vForm = reactive({ po: "", stall: "", phone: "", photo: null, preview: "" });
function openVoucher(b) {
  closeVoucher();
  vForm.po = b.po;
  vForm.stall = b.voucherStall || b.supplier || "";
  vForm.phone = b.phone || "";
}
function closeVoucher() {
  if (vForm.preview) URL.revokeObjectURL(vForm.preview);
  Object.assign(vForm, { po: "", stall: "", phone: "", photo: null, preview: "" });
}
function pickVoucherPhoto(e) {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (!file) return;
  if (vForm.preview) URL.revokeObjectURL(vForm.preview);
  vForm.photo = file;
  vForm.preview = URL.createObjectURL(file);
}
const vWhy = computed(() => {
  if (!vForm.photo) return t("souk.buy.trip.vNeedPhoto");
  if ((vForm.phone || "").replace(/[^\d]/g, "").length < 9) return t("souk.buy.trip.vNeedPhone");
  return "";
});
async function sendVoucher(b) {
  if (vWhy.value) return;
  const photo = await shrink(vForm.photo);
  const job = { id: "voucher-" + b.po, kind: "voucher", label: `${t("souk.buy.trip.vTitle")} · ${b.title || b.po}`,
                po: b.po, phone: vForm.phone.trim(), stallName: vForm.stall.trim(), photo };
  closeVoucher();
  send(b.po, job);
}

function saveTransport(tr) {
  const amount = Math.max(0, Number(transport[tr.name]) || 0);
  send("tr:" + tr.name, { id: "transport-amount-" + tr.name, kind: "transport",
                          label: `${t("souk.transport")} · ${fmt(amount)} MAD`, trip: tr.name, amount, receipt: null });
}
async function transportReceipt(tr, e) {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (!file) return;
  const receipt = await shrink(file);
  const amount = Math.max(0, Number(transport[tr.name] ?? tr.transport) || 0);
  send("tr:" + tr.name, { id: "transport-photo-" + tr.name + "-" + newKey().slice(0, 8), kind: "transport",
                          label: `${t("souk.buy.trip.transportPhoto")} · ${fmt(amount)} MAD`, trip: tr.name, amount, receipt });
}

// ── accountant / online-only actions ─────────────────────────────────────────
const openTrip = () => run(async () => {
  await apiPost("souk.open_trip", { buyer: give.buyer, cash: give.cash, place: give.place });
  give.buyer = ""; give.cash = null;
}, t("souk.handedOut"));
const approve = (b) => run(() => apiPost("souk.approve_voucher", { po: b.po }));
// The substitute does not hold up: back to "receipt missing", with why.
function refuse(b) {
  const note = window.prompt(t("souk.buy.trip.vRefuseWhy"), "");
  if (note === null) return;
  return run(() => apiPost("souk.refuse_voucher", { po: b.po, note }));
}
const allocate = (tr) => run(() => apiPost("souk.allocate_transport", { trip: tr.name }), t("souk.transportOk"));
function close(tr) {
  if (!window.confirm(t("souk.closeConfirm").replace("{n}", fmt(tr.expected)))) return;
  run(() => apiPost("souk.close_trip", { trip: tr.name }), t("souk.closed"));
}
function doCount(tr) {
  run(() => apiPost("souk.count_trip", { trip: tr.name, counted: count[tr.name], note: countNote[tr.name] || "" }),
      t("souk.countedOk"));
}

async function load() {
  loading.value = true;
  try {
    data.value = await api("souk.trips_boot");
    for (const tr of data.value.open) if (transport[tr.name] === undefined) transport[tr.name] = tr.transport || null;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

// A write that waited on the phone went through: clear its row, re-read.
let reloadTimer = null;
const offDone = onDone((job) => {
  for (const [k, x] of Object.entries(st)) if (x.jobId === job.id) delete st[k];
  clearTimeout(reloadTimer);
  reloadTimer = setTimeout(load, 300);
});
onMounted(load);
onBeforeUnmount(() => {
  offDone();
  clearTimeout(reloadTimer);
  closeVoucher();
});
</script>
