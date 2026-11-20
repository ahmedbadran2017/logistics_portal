<template>
  <!-- Souk buying, on the buyer's phone in the market. A NEW product is born
       as a Shopify Draft (vendor = our house brand by category), its Next
       items come from the sync, and a PO on the stall is paid from the
       custody. BUY AGAIN is a PO only. Backend: souk.create_buy / finish_buy /
       create_rebuy — always through the outbox (lib/soukOutbox): Derb Omar
       drops the line, so a purchase is a job kept on the phone with its
       photos and a clientKey, never lost and never made twice. The form
       itself is kept on the phone (localStorage) until it is sent.
       LOOK = design Buy.dc.html (the form) and BuyDone.dc.html (done). -->
  <div>
    <header v-if="!done" class="st-buying bg-white/85 backdrop-blur border-b border-stone-200">
      <div class="max-w-[520px] mx-auto px-4 py-3 flex flex-col gap-2.5">
        <div class="flex items-center gap-2.5">
          <router-link :to="{ name: 'SoukTrip' }" :aria-label="t('souk.buy.back')"
                       class="shrink-0 w-11 h-11 -ms-2 rounded-lg inline-flex items-center justify-center text-stone-700 hover:bg-stone-100">
            <Icon name="chevron-left" :size="18" :stroke-width="2" class="rtl:rotate-180" />
          </router-link>
          <span class="sk-ico sk-ico-solid"><Icon name="shopping-bag" :size="17" :stroke-width="2" /></span>
          <div class="flex-1 min-w-0 flex flex-col">
            <h1 class="text-[17px] font-extrabold text-stone-900 leading-snug">{{ t('souk.buyTitle') }}</h1>
            <span class="text-[12px] text-stone-600 truncate tabular-nums">
              {{ boot?.trip ? tt('souk.buy.sub', { place: boot.trip.place || 'Derb Omar', n: fmt(left) }) : t('souk.title') }}
            </span>
          </div>
          <span v-if="formMode && hasContent" class="shrink-0 text-[11px] font-semibold inline-flex items-center gap-1"
                :class="draftOk ? 'text-emerald-700' : 'text-amber-700'" aria-live="polite">
            <span class="w-[7px] h-[7px] rounded-full" :class="draftOk ? 'bg-emerald-700' : 'bg-amber-500'" />
            {{ draftOk ? t('souk.buy.saved') : t('souk.buy.notSaved') }}
          </span>
        </div>
        <div v-if="formMode" role="tablist" class="flex gap-1 p-1 bg-[var(--accent-50)] ring-1 ring-inset ring-[var(--accent-100)] rounded-xl">
          <button role="tab" :aria-selected="tab === 'new'" class="flex-1 min-w-0 h-11 px-2 rounded-[9px] text-[13px] font-semibold truncate inline-flex items-center justify-center gap-1.5 transition-colors"
                  :class="tab === 'new' ? 'bg-white shadow-[0_2px_6px_-2px_rgba(163,58,34,.25)] text-[var(--accent-700)]' : 'text-stone-600'" @click="tab = 'new'">
            <Icon name="sparkles" :size="15" />{{ t('souk.tabNew') }}</button>
          <button role="tab" :aria-selected="tab === 'again'" class="flex-1 min-w-0 h-11 px-2 rounded-[9px] text-[13px] font-semibold truncate inline-flex items-center justify-center gap-1.5 transition-colors"
                  :class="tab === 'again' ? 'bg-white shadow-[0_2px_6px_-2px_rgba(163,58,34,.25)] text-[var(--accent-700)]' : 'text-stone-600'" @click="tab = 'again'">
            <Icon name="refresh-cw" :size="15" />{{ t('souk.tabAgain') }}</button>
        </div>
      </div>
    </header>

    <div class="max-w-[520px] mx-auto px-4 flex flex-col gap-3.5" :class="done ? 'pt-7 pb-6' : formMode ? 'pt-3.5 pb-48' : 'pt-3.5 pb-6'">
      <div v-if="loading && !boot" class="h-[320px] lp-card animate-pulse" />

      <!-- ── done (BuyDone) ───────────────────────────────────────────────── -->
      <template v-else-if="done">
        <div class="flex flex-col items-center gap-2 text-center pt-2 pb-1">
          <div class="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 text-white flex items-center justify-center shadow-[0_8px_24px_-8px_rgba(5,150,105,.7)] ring-4 ring-emerald-100">
            <Icon name="check" :size="30" :stroke-width="2.8" />
          </div>
          <h1 class="text-[18px] font-bold text-stone-900">
            {{ tt(done.again ? 'souk.buy.done.rebuyTitle' : 'souk.buy.done.title', { title: done.title || done.po }) }}
          </h1>
          <p class="text-[13px] text-stone-600">{{ t('souk.buy.done.goodsIn') }}</p>
        </div>

        <section class="sk-sec">
          <div v-if="!done.again" class="px-3.5 py-3 flex items-center gap-2.5 st-live">
            <span class="sk-ico sk-ico-sm"><Icon name="shopping-bag" :size="14" /></span>
            <div class="flex-1 min-w-0 flex flex-col">
              <span class="text-[14px] font-semibold text-stone-900">{{ t('souk.buy.done.draft') }}</span>
              <span class="text-[12px] text-stone-600">{{ tt('souk.buy.done.draftSub', { brand: done.brand || '—' }) }}</span>
            </div>
            <span class="shrink-0 text-[11px] font-bold rounded-md px-[7px] py-0.5 bg-stone-100 text-stone-600">DRAFT</span>
          </div>
          <div v-if="!done.again && done.variants.length" class="px-3.5 py-3 border-t border-stone-100 flex items-center gap-2.5 st-live">
            <span class="sk-ico sk-ico-sm"><Icon name="layers" :size="14" /></span>
            <div class="flex-1 min-w-0 flex flex-col">
              <span class="text-[14px] font-semibold text-stone-900">{{ tt('souk.buy.done.next', { n: done.variants.length }) }}</span>
              <span class="text-[12px] text-stone-600">{{ t('souk.buy.done.nextSub') }}</span>
            </div>
          </div>
          <div class="px-3.5 py-3 flex items-center gap-2.5 st-live" :class="done.again ? '' : 'border-t border-stone-100'">
            <span class="sk-ico sk-ico-sm"><Icon name="file-text" :size="14" /></span>
            <div class="flex-1 min-w-0 flex flex-col">
              <span class="text-[14px] font-semibold text-stone-900">
                {{ tt('souk.buy.done.poPay', { stall: done.stall || '—', pay: payLabel(done.pay) }) }}
              </span>
              <span class="text-start text-[12px] text-stone-600 tabular-nums break-words">
                <span class="mono" dir="ltr"><template v-if="done.po">{{ done.po }}<template v-if="done.pi"> · {{ done.pi }}</template> · </template>{{ fmt(done.amount) }} MAD</span>
                <span> · {{ done.units }} {{ t('souk.pcs') }}</span>
              </span>
            </div>
          </div>
        </section>

        <section v-if="done.variants.length" class="lp-card px-3.5 py-3 flex flex-col gap-1.5">
          <span class="text-[13px] font-bold text-stone-800 inline-flex items-center gap-2"><Icon name="tag" :size="14" class="text-stone-500" />{{ t('souk.skus') }}</span>
          <div v-for="v in done.variants" :key="v.sku" class="flex items-center justify-between gap-2 text-[13px] py-[3px]">
            <span class="mono text-[12px] text-stone-900" dir="ltr">{{ v.sku }}</span>
            <span class="text-stone-600 tabular-nums">{{ v.qty }} {{ t('souk.pcs') }}</span>
          </div>
        </section>

        <div v-if="done.left != null" class="sk-wallet rounded-2xl text-white px-4 py-3.5 flex items-center justify-between gap-2">
          <span class="text-[13px] text-white/80 inline-flex items-center gap-2"><Icon name="wallet" :size="16" />{{ t('souk.leftWithYou') }}</span>
          <span class="text-[16px] font-extrabold tabular-nums">{{ fmt(done.left) }} MAD</span>
        </div>

        <div class="flex flex-col gap-2 pt-2">
          <button class="h-12 rounded-xl bg-[var(--accent-600)] text-white text-[15px] font-bold px-3 inline-flex items-center justify-center gap-2 shadow-[0_6px_16px_-6px_rgba(196,73,42,.7)]" @click="another"><Icon name="plus" :size="17" :stroke-width="2.4" />{{ t('souk.buy.done.another') }}</button>
          <router-link :to="{ name: 'SoukTrip' }" class="h-12 rounded-[10px] bg-white ring-1 ring-inset ring-stone-300 text-stone-900 text-[15px] font-semibold inline-flex items-center justify-center">{{ t('souk.buy.done.trip') }}</router-link>
        </div>
      </template>

      <!-- ── sent, not finished: saved on the phone / creating / stuck / photo ── -->
      <template v-else-if="sent">
        <section class="rounded-xl p-3.5 space-y-2 ring-1 ring-inset"
                 :class="sent.state === 'queued' || sent.state === 'creating' ? 'bg-white ring-stone-200' : 'bg-rose-50 ring-rose-200'">
          <div class="flex items-center gap-2">
            <Icon :name="sentIcon" :size="18" :class="sent.state === 'queued' || sent.state === 'creating' ? 'text-[var(--accent-600)]' : 'text-rose-600'" />
            <h2 class="text-[15px] font-bold text-stone-900">{{ sentTitle }}</h2>
          </div>
          <p class="text-[13px] text-stone-600 leading-relaxed">{{ sentBody }}</p>
          <p v-if="sent.error && sent.state !== 'queued' && sent.state !== 'creating'" class="text-[13px] text-rose-700 mono break-words" dir="auto">{{ sent.error }}</p>
        </section>

        <section class="lp-card px-3.5 py-3 space-y-1">
          <div class="text-[14px] font-bold text-stone-900 truncate">{{ sent.summary.title }}</div>
          <div class="text-[13px] text-stone-600 truncate">{{ sent.summary.stall }} · {{ sent.summary.units }} {{ t('souk.pcs') }}</div>
          <div class="text-[15px] font-extrabold tabular-nums text-stone-900">{{ fmt(sent.summary.total) }} MAD</div>
          <div v-if="sent.pending" class="mono text-[12px] text-stone-500" dir="ltr">{{ sent.pending }}</div>
        </section>

        <div v-if="boot?.trip && sent.summary.pay === 'cash'" class="sk-wallet rounded-2xl text-white px-4 py-3.5 flex items-center justify-between gap-2">
          <span class="text-[13px] text-white/80 inline-flex items-center gap-2"><Icon name="wallet" :size="16" />{{ t('souk.leftWithYou') }}</span>
          <span class="text-[16px] font-extrabold tabular-nums">{{ fmt(left) }} MAD</span>
        </div>

        <div class="flex flex-col gap-2">
          <button v-if="sent.state === 'stuck'"
                  class="w-full h-12 rounded-[10px] bg-[var(--accent-600)] text-white text-[15px] font-bold disabled:opacity-40"
                  :disabled="busy" @click="checkPending()">
            {{ busy ? t('souk.buy.trip.sending') : t('souk.retry') }}
          </button>
          <button v-if="sent.state === 'creating'"
                  class="w-full h-12 rounded-[10px] bg-white ring-1 ring-inset ring-stone-300 text-stone-900 text-[15px] font-semibold disabled:opacity-40"
                  :disabled="busy || outbox.flushing || !outbox.online" @click="checkNow">
            {{ outbox.flushing ? t('souk.buy.trip.sending') : t('souk.buy.sent.checkNow') }}
          </button>
          <template v-if="sent.state === 'photo'">
            <button class="w-full h-12 rounded-[10px] bg-[var(--accent-600)] text-white text-[15px] font-bold disabled:opacity-40"
                    :disabled="busy" @click="retrySent">{{ busy ? t('souk.buy.trip.sending') : t('souk.buy.sent.retryPhoto') }}</button>
            <button class="w-full h-12 rounded-[10px] bg-white ring-1 ring-inset ring-stone-300 text-stone-900 text-[15px] font-semibold disabled:opacity-40"
                    :disabled="busy" @click="skipPhoto">{{ t('souk.buy.sent.skipPhoto') }}</button>
          </template>
          <template v-if="sent.state === 'refused'">
            <button class="w-full h-12 rounded-[10px] bg-[var(--accent-600)] text-white text-[15px] font-bold disabled:opacity-40"
                    :disabled="busy" @click="retrySent">{{ t('souk.retry') }}</button>
            <button class="w-full h-12 rounded-[10px] bg-white ring-1 ring-inset ring-rose-300 text-rose-700 text-[15px] font-semibold disabled:opacity-40"
                    :disabled="busy" @click="discardSent">{{ t('souk.buy.sent.discard') }}</button>
          </template>
          <button class="h-12 rounded-[10px] bg-white ring-1 ring-inset ring-stone-300 text-stone-900 text-[15px] font-semibold px-3" @click="another">{{ t('souk.buy.done.another') }}</button>
          <router-link :to="{ name: 'SoukTrip' }" class="h-12 rounded-[10px] bg-white ring-1 ring-inset ring-stone-300 text-stone-900 text-[15px] font-semibold inline-flex items-center justify-center">{{ t('souk.buy.done.trip') }}</router-link>
        </div>
      </template>

      <!-- ── the form ─────────────────────────────────────────────────────── -->
      <template v-else-if="boot">
        <!-- NEW PRODUCT: reference photo -->
        <section v-if="tab === 'new'" class="sk-sec st-buying p-3.5 flex gap-3 items-center">
          <label class="w-[84px] h-[84px] shrink-0 rounded-2xl flex items-center justify-center overflow-hidden cursor-pointer"
                 :class="refPreview ? 'ring-1 ring-stone-200' : 'st-soft border-2 border-dashed border-[rgb(var(--st)/.35)] st-fg'"
                 :aria-label="refPreview ? t('souk.buy.retake') : t('souk.buy.takePhoto')">
            <img v-if="refPreview" :src="refPreview" class="w-full h-full object-cover" alt="" />
            <Icon v-else name="camera" :size="28" />
            <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickRef" />
          </label>
          <div class="flex-1 min-w-0 flex flex-col gap-1 items-start">
            <span class="text-[14px] font-bold text-stone-900">{{ t('souk.buy.refTitle') }}</span>
            <span class="text-[12px] text-stone-600 leading-normal">{{ t('souk.buy.refNote') }}</span>
            <label class="h-11 px-3.5 rounded-xl st-tint st-ink text-[13px] font-bold inline-flex items-center gap-1.5 cursor-pointer">
              <Icon name="camera" :size="15" />{{ refPreview ? t('souk.buy.retake') : t('souk.buy.takePhoto') }}
              <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickRef" />
            </label>
          </div>
        </section>

        <!-- name, category, stall, brand (the stall card only, to buy again) -->
        <section class="sk-sec st-buying">
          <div class="sk-sec-h">
            <span class="sk-ico"><Icon :name="tab === 'new' ? 'tag' : 'building'" :size="16" /></span>
            <div class="min-w-0 flex flex-col">
              <h2 class="sk-sec-t">{{ tab === 'new' ? t('souk.buy.secProduct') : t('souk.stall') }}</h2>
              <span v-if="tab === 'new'" class="sk-sec-s">{{ t('souk.buy.secProductSub') }}</span>
            </div>
          </div>
          <div class="sk-sec-b flex flex-col gap-3">
          <template v-if="tab === 'new'">
            <div class="flex flex-col gap-1.5">
              <label for="sb-title" class="text-[13px] font-semibold text-stone-700">{{ t('souk.name') }}</label>
              <div class="flex gap-1.5">
                <input id="sb-title" v-model="f.title" :placeholder="t('souk.namePh')" autocomplete="off"
                       class="flex-1 min-w-0 h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px]" @input="lookSimilar" />
                <button type="button" class="shrink-0 w-11 h-11 rounded-xl st-tint st-ink inline-flex items-center justify-center"
                        :aria-label="t('souk.scan.btn')" :title="t('souk.scan.btn')" @click="openScan('new')">
                  <Icon name="scan-barcode" :size="18" :stroke-width="2" />
                </button>
              </div>
            </div>
            <!-- the box's barcode: known = buy it again; unknown = kept on the new product -->
            <div v-if="f.barcode" class="flex flex-col gap-2">
              <div class="flex items-center gap-2 text-[12px]">
                <span class="inline-flex items-center gap-1 rounded-full bg-stone-100 text-stone-800 font-semibold px-2.5 h-7">
                  <Icon name="scan-barcode" :size="13" />{{ t('souk.scan.label') }} <span class="mono" dir="ltr">{{ f.barcode }}</span>
                </span>
                <button type="button" class="h-9 px-2 rounded-lg text-stone-600 underline underline-offset-2" @click="clearBarcode">{{ t('souk.scan.remove') }}</button>
              </div>
              <p v-if="bcBusy" class="text-[12px] text-stone-600">{{ t('souk.scan.checking') }}</p>
              <div v-else-if="bcHits.length && !f.barcodeSure" role="alert" class="rounded-xl bg-rose-50 ring-1 ring-inset ring-rose-200 p-3 flex flex-col gap-2">
                <span class="text-[14px] font-bold text-rose-800 inline-flex items-center gap-1.5"><Icon name="alert-triangle" :size="15" />{{ t('souk.scan.knownTitle') }}</span>
                <span class="text-[12px] text-rose-900/80">{{ tt('souk.scan.knownSub', { code: f.barcode }) }}</span>
                <div v-for="r in bcHits" :key="r.kind + r.key" class="bg-white rounded-lg ps-2 pe-1 py-1 flex items-center gap-2">
                  <img v-if="r.image" :src="r.image" class="w-10 h-10 rounded-md object-cover shrink-0" alt="" loading="lazy" />
                  <div v-else class="w-10 h-10 rounded-md bg-stone-100 shrink-0 flex items-center justify-center"><Icon name="package" :size="14" class="text-stone-500" /></div>
                  <div class="flex-1 min-w-0 flex flex-col">
                    <span class="text-[13px] font-semibold text-stone-900 truncate" dir="auto">{{ r.title }}</span>
                    <span class="text-[12px] text-stone-600 truncate"><span class="mono" dir="ltr">{{ r.sku }}</span> ·
                      <span :class="r.stock > 0 ? 'text-emerald-700 font-semibold' : ''">{{ r.stock > 0 ? tt('souk.buy.onShelf', { n: r.stock }) : t('souk.buy.noneOnShelf') }}</span></span>
                  </div>
                  <button class="shrink-0 h-11 px-3 rounded-lg st-solid text-[13px] font-bold" @click="startAgain(r)">{{ t('souk.buyAgain') }}</button>
                </div>
                <button type="button" class="self-start min-h-9 text-[13px] font-semibold text-stone-700 underline underline-offset-2" @click="f.barcodeSure = true">{{ t('souk.scan.different') }}</button>
              </div>
              <p v-else-if="bcHits.length" class="text-[12px] text-amber-800">{{ t('souk.scan.differentNote') }}</p>
              <p v-else class="text-[12px] text-emerald-800">{{ tt('souk.scan.isNew', { code: f.barcode }) }}</p>
            </div>
            <div class="flex flex-col gap-1.5">
              <label for="sb-cat" class="text-[13px] font-semibold text-stone-700">{{ t('souk.category') }}</label>
              <select id="sb-cat" v-model="f.category" class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-2.5 text-[15px]"
                      :class="f.category ? 'text-stone-900' : 'text-stone-500'">
                <option value="" disabled>{{ t('souk.buy.chooseCategory') }}</option>
                <option v-for="c in boot.categories" :key="c.key" :value="c.key">
                  {{ isAr ? c.ar : c.fr }}{{ c.key === lastCat ? ' (' + t('souk.buy.lastPick') + ')' : '' }}
                </option>
              </select>
            </div>
          </template>

          <div class="flex flex-col gap-1.5">
            <label for="sb-stall" class="text-[13px] font-semibold text-stone-700">{{ t('souk.stall') }}</label>
            <div class="flex gap-1.5">
              <select id="sb-stall" v-model="f.stall" class="flex-1 min-w-0 h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-2.5 text-[15px]">
                <option value="">{{ t('souk.newStall') }}</option>
                <option v-for="s in boot.stalls" :key="s.name" :value="s.name">{{ s.label }}</option>
              </select>
              <button type="button" class="shrink-0 w-11 h-11 rounded-xl st-tint st-ink inline-flex items-center justify-center"
                      :aria-label="t('souk.buy.newStallBtn')" :title="t('souk.buy.newStallBtn')" @click="newStall">
                <Icon name="plus" :size="16" :stroke-width="2.2" />
              </button>
            </div>
          </div>
          <div v-if="!f.stall" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div class="flex flex-col gap-1.5">
              <label for="sb-stall-name" class="text-[13px] font-semibold text-stone-700">{{ t('souk.buy.stallNameLbl') }}</label>
              <input id="sb-stall-name" v-model="f.newStall.name" dir="ltr" placeholder="AMINE DERB OMAR" autocomplete="off"
                     class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px] uppercase" />
            </div>
            <div class="flex flex-col gap-1.5">
              <label for="sb-stall-phone" class="text-[13px] font-semibold text-stone-700">{{ t('souk.buy.stallPhoneLbl') }}</label>
              <input id="sb-stall-phone" v-model="f.newStall.phone" dir="ltr" inputmode="tel" type="tel" placeholder="06…"
                     class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px]" />
            </div>
          </div>

          <!-- the same stall twice? the phone or a name that reads the same -->
          <div v-if="!f.stall && stMatch.length && !f.newStall.sure" role="status"
               class="rounded-xl bg-amber-50 ring-1 ring-inset ring-amber-200 p-3 flex flex-col gap-2">
            <span class="text-[13px] font-bold text-amber-900 inline-flex items-center gap-1.5">
              <Icon name="alert-triangle" :size="14" />{{ t('souk.stl.didYouMean') }}
            </span>
            <button v-for="m in stMatch" :key="m.name" type="button" @click="useMatch(m)"
                    class="lp-tap min-h-11 flex items-center gap-2.5 rounded-lg bg-white ring-1 ring-inset ring-amber-200 px-2.5 py-1.5 text-start">
              <img v-if="m.photo" :src="m.photo" alt="" class="w-9 h-9 rounded-md object-cover shrink-0" />
              <span v-else class="sk-ico sk-ico-sm"><Icon name="store" :size="14" /></span>
              <span class="min-w-0 flex-1 flex flex-col">
                <span class="text-[14px] font-semibold text-stone-900 truncate" dir="ltr">{{ m.label }}</span>
                <span class="text-[12px] text-stone-600 truncate">
                  {{ m.why === 'phone' ? t('souk.stl.samePhone') : t('souk.stl.sameName') }}<template v-if="m.place"> · {{ m.place }}</template><template v-if="m.phone"> · <span dir="ltr">{{ m.phone }}</span></template>
                </span>
              </span>
              <span class="shrink-0 text-[12px] font-bold st-ink">{{ t('souk.stl.useIt') }}</span>
            </button>
            <button type="button" class="self-start text-[13px] font-semibold text-stone-700 underline underline-offset-2 min-h-9"
                    @click="f.newStall.sure = true">{{ t('souk.stl.another') }}</button>
          </div>

          <div v-if="tab === 'new' && cat" class="flex items-center justify-between gap-2.5 st-soft rounded-xl px-3 py-2.5">
            <div class="min-w-0 flex flex-col">
              <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.brandOnSite') }}</span>
              <span class="text-[12px] text-stone-600">{{ t('souk.buy.brandSub') }}</span>
            </div>
            <span class="shrink-0 text-[13px] font-bold st-ink bg-white ring-1 ring-inset ring-[rgb(var(--st)/.3)] rounded-lg px-2.5 py-[3px] inline-flex items-center gap-1"><Icon name="award" :size="13" />{{ cat.brand }}</span>
          </div>
          <p v-if="tab === 'again'" class="text-[12px] text-stone-600">{{ t('souk.stallHint') }}</p>
          </div>
        </section>

        <template v-if="tab === 'new'">
          <!-- do we already have it? -->
          <section v-if="similarShown.length" class="st-bought rounded-2xl bg-gradient-to-br from-amber-50 to-amber-100/60 ring-1 ring-inset ring-amber-200 px-3.5 py-3 flex flex-col gap-2" :aria-label="t('souk.similar')">
            <div class="flex items-center gap-2">
              <span class="sk-ico sk-ico-sm"><Icon name="alert-triangle" :size="14" :stroke-width="2" /></span>
              <span class="text-[13px] font-bold text-amber-800">{{ tt('souk.buy.similarN', { n: similarShown.length }) }}</span>
            </div>
            <div class="flex flex-col gap-1.5">
              <div v-for="r in similarShown" :key="r.kind + r.key" class="bg-white rounded-lg ps-2 pe-1 py-1 flex items-center gap-2">
                <img v-if="r.image" :src="r.image" class="w-8 h-8 rounded-md object-cover shrink-0" alt="" loading="lazy" />
                <div v-else class="w-8 h-8 rounded-md bg-stone-100 shrink-0 flex items-center justify-center"><Icon name="package" :size="14" class="text-stone-500" /></div>
                <div class="flex-1 min-w-0 flex flex-col">
                  <span class="text-[13px] font-semibold text-stone-900 truncate">{{ r.title }}</span>
                  <span class="text-[12px] text-stone-600 truncate">
                    <template v-if="r.stall">{{ r.stall }} · </template>
                    <span :class="r.stock > 0 ? 'text-emerald-700 font-semibold' : ''">{{ r.stock > 0 ? tt('souk.buy.onShelf', { n: r.stock }) : t('souk.buy.noneOnShelf') }}</span>
                    · {{ r.lastSold ? tt('souk.buy.lastSold', { when: ago(r.lastSold) }) : t('souk.buy.neverSold') }}
                    <span v-if="r.stage && r.stage !== 'live'" class="text-amber-800"> · {{ t('souk.st_' + r.stage) }}</span>
                  </span>
                </div>
                <button class="shrink-0 h-11 px-2 rounded-lg text-[12px] font-semibold text-[var(--accent-700)] hover:bg-[var(--accent-50)]" @click="startAgain(r)">{{ t('souk.buyAgain') }}</button>
              </div>
            </div>
            <button class="self-start h-11 px-3 rounded-lg bg-white ring-1 ring-inset ring-amber-200 text-[13px] font-semibold text-amber-800" @click="dismissSimilar">{{ t('souk.buy.notIt') }}</button>
          </section>

          <!-- colours, sizes, quantities -->
          <section class="sk-sec st-buying">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="layers" :size="16" /></span>
              <div class="min-w-0 flex flex-col">
                <h2 class="sk-sec-t">{{ t('souk.buy.colorsSizes') }}</h2>
                <span class="sk-sec-s">{{ t('souk.buy.secVariantsSub') }}</span>
              </div>
              <span v-if="units" class="ms-auto shrink-0 text-[12px] font-bold st-ink st-tint rounded-full px-2.5 py-1 tabular-nums">{{ units }} {{ t('souk.pcs') }}</span>
            </div>
            <div class="sk-sec-b flex flex-col gap-3">

            <div class="flex flex-col gap-1.5">
              <span id="sb-colors" class="text-[12px] font-semibold text-stone-600">{{ t('souk.buy.colorsLbl') }}</span>
              <div class="flex flex-wrap gap-1.5" role="group" aria-labelledby="sb-colors">
                <button v-for="c in shownColors" :key="c.code" type="button" :aria-pressed="f.colors.includes(c.code)"
                        class="h-11 ps-2.5 pe-3 rounded-full text-[13px] font-semibold inline-flex items-center gap-1.5"
                        :class="f.colors.includes(c.code) ? 'bg-[var(--accent-600)] text-white shadow-[0_3px_10px_-4px_rgba(196,73,42,.7)]' : 'bg-white text-stone-700 ring-1 ring-inset ring-stone-300'"
                        @click="toggleColor(c.code)">
                  <span class="w-3.5 h-3.5 rounded-full shrink-0" :class="f.colors.includes(c.code) ? 'ring-2 ring-white' : 'ring-1 ring-black/10'" :style="{ background: swatch(c.code) }" />
                  {{ colorName(c) }}
                </button>
                <button type="button" :aria-expanded="colorsOpen"
                        class="h-11 px-3 rounded-full text-[13px] font-semibold inline-flex items-center"
                        :class="colorsOpen ? 'bg-stone-100 text-stone-700' : 'bg-white text-stone-700 ring-1 ring-inset ring-stone-300'"
                        @click="colorsOpen = !colorsOpen">{{ colorsOpen ? t('souk.buy.sizeDone') : t('souk.buy.addColor') }}</button>
              </div>
              <p class="text-[12px] text-stone-600 leading-normal">{{ tt('souk.buy.colorsNote', { code: f.colors[0] || 'RED' }) }}</p>
            </div>

            <div class="flex flex-col gap-1.5">
              <span id="sb-sizes" class="text-[12px] font-semibold text-stone-600">{{ t('souk.sizes') }}</span>
              <div class="flex flex-wrap gap-1.5" role="group" aria-labelledby="sb-sizes">
                <button v-for="s in sizes" :key="s.id" type="button" :aria-expanded="editSize === s.id"
                        :aria-label="tt('souk.buy.editSize', { z: sizeChip(s) })"
                        class="h-11 px-3 rounded-full text-[13px] font-semibold inline-flex items-center max-w-full"
                        :class="editSize === s.id ? 'bg-white text-stone-900 ring-2 ring-inset ring-stone-900'
                          : sizeBad(s) ? 'bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-300' : 'bg-[var(--accent-600)] text-white'"
                        @click="toggleEdit(s)">
                  <span class="truncate"><bdi>{{ (s.label || '').trim() || '…' }}</bdi><template v-if="effCode(s) && effCode(s) !== (s.label || '').trim()"> · <bdi class="mono">{{ effCode(s) }}</bdi></template></span>
                </button>
                <button type="button" class="h-11 px-3 rounded-full bg-white ring-1 ring-inset ring-stone-300 text-[13px] font-semibold text-stone-700" @click="newSize('')">{{ t('souk.buy.addSize') }}</button>
                <button v-for="q in quickLeft" :key="q" type="button" class="h-11 min-w-[44px] px-2.5 rounded-full bg-white ring-1 ring-inset ring-stone-200 text-[13px] font-semibold mono text-stone-500"
                        :aria-label="t('souk.buy.addSize') + ' ' + q" @click="addSize(q)"><span dir="ltr">+{{ q }}</span></button>
              </div>
              <!-- the size being edited: what the customer reads + the code in the SKU -->
              <div v-if="editing" class="rounded-xl st-soft ring-1 ring-inset ring-[rgb(var(--st)/.2)] p-2.5 flex flex-col gap-2.5">
                <div class="grid grid-cols-[minmax(0,1fr)_84px] gap-2">
                  <div class="flex flex-col gap-1 min-w-0">
                    <label :for="'sb-sz-' + editing.id" class="text-[12px] font-semibold text-stone-600 truncate">{{ t('souk.buy.sizeDesc') }}</label>
                    <input :id="'sb-sz-' + editing.id" v-model="editing.label" :placeholder="t('souk.buy.sizeDescPh')" autocomplete="off"
                           class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px]" @keydown.enter.prevent="closeEdit" />
                  </div>
                  <div class="flex flex-col gap-1">
                    <label :for="'sb-sc-' + editing.id" class="text-[12px] font-semibold text-stone-600 truncate">{{ t('souk.buy.sizeCode') }}</label>
                    <input :id="'sb-sc-' + editing.id" v-model="editing.code" dir="ltr" maxlength="4" autocomplete="off"
                           :placeholder="sizeCode(editing.label) || t('souk.buy.sizeCodePh')"
                           class="w-full h-11 rounded-lg ring-1 ring-inset px-2 text-[16px] mono font-semibold uppercase text-center"
                           :class="sizeBad(editing) ? 'ring-rose-400 bg-rose-50' : 'ring-stone-300 bg-white'" @keydown.enter.prevent="closeEdit" />
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <button type="button" class="h-11 px-3 rounded-lg bg-white ring-1 ring-inset ring-rose-200 text-rose-700 text-[13px] font-semibold inline-flex items-center gap-1.5"
                          @click="removeEditing"><Icon name="x" :size="14" />{{ t('souk.buy.removeSize') }}</button>
                  <button type="button" class="ms-auto h-11 px-4 rounded-lg st-solid text-[13px] font-bold inline-flex items-center gap-1.5" @click="closeEdit"><Icon name="check" :size="14" :stroke-width="2.4" />{{ t('souk.buy.sizeDone') }}</button>
                </div>
              </div>
              <p class="text-[12px] text-stone-600 leading-normal">{{ t('souk.buy.sizesNote') }}</p>
            </div>

            <!-- quantities: a row per colour, a −/+ cell per size -->
            <div class="rounded-xl ring-1 ring-inset ring-stone-200 overflow-x-auto">
              <div class="w-max min-w-full">
                <div class="grid gap-1.5 px-2.5 py-2 st-soft text-[12px] font-bold st-ink" :style="qtyCols">
                  <span>{{ t('souk.qtyShort') }}</span>
                  <span v-for="z in sizeCols" :key="z.id" class="text-center truncate">{{ z.label ? zName(z) : t('souk.buy.oneSize') }}</span>
                </div>
                <div v-for="c in colorRows" :key="c" class="grid gap-1.5 items-center px-2.5 py-1.5 border-t border-stone-100" :style="qtyCols">
                  <span class="min-w-0 inline-flex items-center gap-1.5 text-[13px] font-semibold text-stone-900">
                    <span v-if="c" class="w-3 h-3 rounded-full ring-1 ring-black/10 shrink-0" :style="{ background: swatch(c) }" />
                    <span class="truncate">{{ c ? colorShort(c) : t('souk.buy.noColor') }}</span>
                  </span>
                  <Stepper v-for="z in sizeCols" :key="z.id" compact :model-value="qty[key(c, z.id)]" :id="'sb-q-' + c + '-' + z.id"
                           :label="tt('souk.buy.qtyOf', { v: [c ? colorLabel(c) : '', z.label].filter(Boolean).join(' · ') || t('souk.buy.oneSize') })"
                           :less="t('souk.buy.less')" :more="t('souk.buy.more')"
                           @update:model-value="(v) => (qty[key(c, z.id)] = v)" />
                </div>
              </div>
            </div>

            <div v-if="lines.length" class="bg-stone-50 rounded-xl px-3 py-2.5 flex flex-col gap-1">
              <span class="text-[12px] font-semibold text-stone-600 inline-flex items-center gap-1.5"><Icon name="tag" :size="13" />{{ t('souk.buy.skusLbl') }}</span>
              <div class="text-start text-[12px] leading-[1.7] text-stone-800 mono break-words">
                <span dir="ltr"><template v-for="(l, i) in lines" :key="l.sku"><template v-if="i"> · </template><span :class="l.sku.length > boot.skuMax ? 'text-rose-700 font-bold' : ''">{{ l.sku }}</span></template></span>
              </div>
            </div>
            </div>
          </section>

          <!-- price -->
          <section class="sk-sec st-buying">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="dollar-sign" :size="16" /></span>
              <div class="min-w-0 flex-1 flex flex-col">
                <h2 class="sk-sec-t">{{ t('souk.buy.priceTitle') }}</h2>
                <span class="sk-sec-s">{{ t('souk.buy.secPriceSub') }}</span>
              </div>
              <button v-if="sizeCols.length > 1" class="shrink-0 h-11 -my-2.5 px-2 rounded-lg text-[13px] font-semibold text-[var(--accent-700)] hover:bg-[var(--accent-50)] disabled:opacity-40"
                      :disabled="!(Number(cost[sizeCols[0].id]) > 0)" @click="samePrices">{{ t('souk.buy.samePrices') }}</button>
            </div>
            <div class="sk-sec-b flex flex-col gap-3">
            <div class="grid grid-cols-2 gap-2.5">
              <template v-for="z in sizeCols" :key="z.id">
                <div class="flex flex-col gap-1.5 min-w-0">
                  <label :for="'sb-c-' + z.id" class="text-[13px] font-semibold text-stone-700 truncate">{{ tt('souk.buy.costLbl', { z: zName(z) }) }}</label>
                  <div class="relative">
                    <input :id="'sb-c-' + z.id" v-model.number="cost[z.id]" type="number" inputmode="decimal" min="0" placeholder="0"
                           class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white ps-3 pe-11 text-[16px] tabular-nums" />
                    <span class="absolute inset-y-0 end-3 flex items-center text-[13px] text-stone-500 pointer-events-none">MAD</span>
                  </div>
                </div>
                <div class="flex flex-col gap-1.5 min-w-0">
                  <label :for="'sb-p-' + z.id" class="text-[13px] font-semibold text-stone-700 truncate">{{ tt('souk.buy.sellLbl', { z: zName(z) }) }}</label>
                  <div class="relative">
                    <input :id="'sb-p-' + z.id" v-model.number="price[z.id]" type="number" inputmode="decimal" min="0" placeholder="0"
                           class="w-full h-11 rounded-lg ring-1 ring-inset ps-3 pe-11 text-[16px] tabular-nums"
                           :class="Number(price[z.id]) > 0 && Number(price[z.id]) <= Number(cost[z.id]) ? 'ring-rose-400 bg-rose-50' : 'ring-stone-300 bg-white'" />
                    <span class="absolute inset-y-0 end-3 flex items-center text-[13px] text-stone-500 pointer-events-none">MAD</span>
                  </div>
                </div>
              </template>
            </div>
            <!-- margin before shipping, per size. (The design's "after delivery
                 and returns" row needs a per-category delivery-cost + return-rate
                 number the backend does not send yet — not shown.) -->
            <div class="rounded-xl ring-1 ring-inset ring-stone-200 overflow-x-auto text-[13px] tabular-nums">
              <div class="w-max min-w-full">
                <div class="grid gap-1.5 px-2.5 py-[7px] bg-stone-50 font-semibold text-stone-600" :style="marginCols">
                  <span>{{ t('souk.buy.margin') }}</span>
                  <span v-for="z in sizeCols" :key="z.id" class="text-center truncate">{{ z.label ? zName(z) : t('souk.buy.oneSize') }}</span>
                </div>
                <div class="grid gap-1.5 px-2.5 py-[7px]" :style="marginCols">
                  <span class="text-stone-700">{{ t('souk.buy.marginBefore') }}</span>
                  <span v-for="z in sizeCols" :key="z.id" class="text-center font-semibold"
                        :class="margin(z.id) === null ? 'text-stone-300' : margin(z.id) < 40 ? 'text-rose-600' : 'text-emerald-700'">
                    <span v-if="margin(z.id) !== null" class="inline-flex items-center justify-center min-w-[52px] rounded-full px-2 py-0.5"
                          :class="margin(z.id) < 40 ? 'bg-rose-50' : 'bg-emerald-50'">{{ margin(z.id) }}%</span>
                    <template v-else>—</template>
                  </span>
                </div>
              </div>
            </div>
            <p class="text-[12px] text-stone-600 leading-normal">{{ t('souk.marginHint') }}</p>
            </div>
          </section>
        </template>

        <!-- BUY AGAIN -->
        <template v-else>
          <section class="sk-sec st-buying p-3.5 flex flex-col gap-1.5">
            <label for="sb-find" class="text-[13px] font-bold text-stone-800 inline-flex items-center gap-2"><span class="sk-ico sk-ico-sm"><Icon name="search" :size="14" /></span>{{ t('souk.findProduct') }}</label>
            <div class="flex gap-1.5">
              <input id="sb-find" v-model="againQ" :placeholder="t('souk.findPh')" autocomplete="off"
                     class="flex-1 min-w-0 h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px]" @input="lookAgain" />
              <button type="button" class="shrink-0 w-11 h-11 rounded-xl st-tint st-ink inline-flex items-center justify-center"
                      :aria-label="t('souk.scan.btn')" :title="t('souk.scan.btn')" @click="openScan('again')">
                <Icon name="scan-barcode" :size="18" :stroke-width="2" />
              </button>
            </div>
            <p v-if="againBarcode && againNone && !again" class="text-[12px] text-amber-800">{{ tt('souk.scan.againNone', { code: againBarcode }) }}</p>
            <div v-if="againRows.length && !again" class="flex flex-col gap-1.5 pt-1">
              <button v-for="r in againRows" :key="r.kind + r.key"
                      class="w-full min-h-[56px] p-2 rounded-lg ring-1 ring-inset ring-stone-200 flex items-center gap-2.5 text-start hover:bg-stone-50" @click="startAgain(r)">
                <img v-if="r.image" :src="r.image" class="w-10 h-10 rounded-lg object-cover shrink-0" alt="" loading="lazy" />
                <div v-else class="w-10 h-10 rounded-lg bg-stone-100 shrink-0 flex items-center justify-center"><Icon name="package" :size="16" class="text-stone-500" /></div>
                <div class="flex-1 min-w-0 flex flex-col">
                  <span class="text-[13px] font-semibold text-stone-900 truncate">{{ r.title }}</span>
                  <span class="text-[12px] text-stone-600 truncate"><span class="mono" dir="ltr">{{ r.sku }}</span><template v-if="r.stall"> · {{ r.stall }}</template></span>
                  <span class="text-[12px] truncate">
                    <span :class="r.stock > 0 ? 'text-emerald-700 font-semibold' : 'text-stone-600'">{{ r.stock > 0 ? tt('souk.buy.onShelf', { n: r.stock }) : t('souk.buy.noneOnShelf') }}</span>
                    <span class="text-stone-600"> · {{ r.lastSold ? tt('souk.buy.lastSold', { when: ago(r.lastSold) }) : t('souk.buy.neverSold') }}</span>
                  </span>
                </div>
                <Icon name="chevron-right" :size="16" class="text-stone-500 rtl:rotate-180 shrink-0" />
              </button>
            </div>
          </section>
          <section v-if="again" class="sk-sec st-buying">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="refresh-cw" :size="16" /></span>
              <h2 class="sk-sec-t flex-1 min-w-0 truncate">{{ again.title }}</h2>
              <button class="shrink-0 h-11 -my-2.5 px-2 rounded-lg text-[13px] font-semibold text-[var(--accent-700)] hover:bg-[var(--accent-50)]" @click="again = null">{{ t('souk.change') }}</button>
            </div>
            <div class="sk-sec-b flex flex-col gap-3">
            <div v-for="r in again.rows" :key="r.itemCode" class="rounded-xl bg-stone-50 ring-1 ring-inset ring-stone-100 p-2.5 flex flex-col gap-2">
              <div class="min-w-0">
                <div class="mono text-[13px] font-semibold text-stone-900" dir="ltr">{{ r.sku }}</div>
                <div class="text-[12px] text-stone-600 truncate">{{ r.label }}</div>
              </div>
              <div class="flex items-end justify-between gap-2">
                <div class="flex flex-col gap-1">
                  <span class="text-[12px] font-semibold text-stone-600">{{ t('souk.qtyShort') }}</span>
                  <Stepper :model-value="r.qty" :id="'sb-aq-' + r.itemCode" :label="tt('souk.buy.qtyOf', { v: r.sku })"
                           :less="t('souk.buy.less')" :more="t('souk.buy.more')" @update:model-value="(v) => (r.qty = v)" />
                </div>
                <div class="flex flex-col gap-1 w-[120px]">
                  <label :for="'sb-ac-' + r.itemCode" class="text-[12px] font-semibold text-stone-600">{{ tt('souk.buy.costLbl', { z: '' }) }}</label>
                  <div class="relative">
                    <input :id="'sb-ac-' + r.itemCode" v-model.number="r.cost" type="number" inputmode="decimal" min="0" placeholder="0"
                           class="w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white ps-3 pe-10 text-[16px] tabular-nums" />
                    <span class="absolute inset-y-0 end-2.5 flex items-center text-[12px] text-stone-500 pointer-events-none">MAD</span>
                  </div>
                </div>
              </div>
            </div>
            <p v-if="again.lastStall" class="text-[12px] text-stone-600">{{ t('souk.lastStall').replace('{s}', again.lastStall) }}</p>
            </div>
          </section>
        </template>

        <!-- PAYMENT: how the stall is paid. The purchase is a PO; receiving
             makes the PR and the accountant the PI and the payment — this
             only tells him how (cash on the custody, cheque, transfer,
             credit). Not tied to a custody (Ahmed, 2026-11-19). -->
        <section class="sk-sec st-buying" aria-labelledby="sb-pay-h">
          <div class="sk-sec-h">
            <span class="sk-ico"><Icon name="wallet" :size="16" /></span>
            <div class="min-w-0 flex flex-col">
              <h2 id="sb-pay-h" class="sk-sec-t">{{ t('souk.buy.pay.title') }}</h2>
              <span class="sk-sec-s">{{ t('souk.buy.secPaySub') }}</span>
            </div>
          </div>
          <div class="sk-sec-b flex flex-col gap-3">
          <div role="radiogroup" :aria-labelledby="'sb-pay-h'" class="grid grid-cols-2 gap-2">
            <button v-for="m in PAY" :key="m.k" type="button" role="radio" :aria-checked="pay.method === m.k"
                    class="min-h-[60px] rounded-xl px-3 py-2 flex items-center gap-2.5 text-start ring-inset transition-colors"
                    :class="[m.cls, pay.method === m.k ? 'ring-2 ring-[rgb(var(--st))] bg-[rgb(var(--st)/.08)] st-ink' : 'ring-1 ring-stone-200 bg-white text-stone-800 hover:bg-stone-50']"
                    @click="choosePay(m.k)">
              <span class="sk-ico sk-ico-sm" :class="pay.method === m.k ? 'sk-ico-solid' : ''"><Icon :name="m.icon" :size="15" /></span>
              <span class="flex flex-col min-w-0">
                <span class="text-[14px] font-semibold leading-tight">{{ t('souk.buy.pay.' + m.k) }}</span>
                <span v-if="m.k === 'cash'" class="text-[11px] leading-snug mt-0.5"
                      :class="pay.method === 'cash' ? 'st-ink opacity-90' : 'text-stone-500'">
                  {{ boot.trip ? tt('souk.buy.pay.cashTrip', { n: fmt(left) }) : t('souk.buy.pay.cashNoTrip') }}
                </span>
              </span>
            </button>
          </div>

          <div v-if="pay.method === 'cheque' || pay.method === 'transfer' || pay.method === 'credit'" class="grid grid-cols-2 gap-2.5">
            <div v-if="pay.method !== 'credit'" class="flex flex-col gap-1" :class="pay.method === 'transfer' ? 'col-span-2' : ''">
              <label for="sb-pay-ref" class="text-[12px] font-semibold text-stone-700">
                {{ t(pay.method === 'cheque' ? 'souk.buy.pay.chequeNo' : 'souk.buy.pay.transferRef') }}
                <span class="font-normal text-stone-500">· {{ t('souk.buy.pay.optional') }}</span>
              </label>
              <input id="sb-pay-ref" v-model="pay.ref" dir="ltr" inputmode="text" autocomplete="off" maxlength="60"
                     class="h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px] tabular-nums" />
            </div>
            <div v-if="pay.method !== 'transfer'" class="flex flex-col gap-1" :class="pay.method === 'credit' ? 'col-span-2' : ''">
              <label for="sb-pay-due" class="text-[12px] font-semibold text-stone-700">
                {{ t(pay.method === 'cheque' ? 'souk.buy.pay.chequeDue' : 'souk.buy.pay.creditDue') }}
                <span class="font-normal text-stone-500">· {{ t('souk.buy.pay.optional') }}</span>
              </label>
              <input id="sb-pay-due" v-model="pay.due" type="date" dir="ltr"
                     class="h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px]" />
            </div>
          </div>

          <p v-if="pay.method === 'cash' && boot.trip && total > left + 0.01"
             class="text-[12px] text-amber-800 bg-amber-50 rounded-lg px-3 py-2 flex items-start gap-1.5">
            <Icon name="info" :size="13" class="mt-[2px] shrink-0" />{{ tt('souk.buy.pay.over', { n: fmt(total - left) }) }}
          </p>
          <p v-else class="text-[12px] text-stone-600 leading-normal">{{ t('souk.buy.pay.books') }}</p>

          <!-- the stall's paper: the accountant's proof, whatever the payment -->
          <div class="flex items-center gap-2.5 pt-3 border-t border-dashed border-stone-200">
            <span class="sk-ico sk-ico-sm st-dropped"><Icon name="ticket" :size="14" /></span>
            <span class="flex-1 min-w-0 text-[13px] font-semibold text-stone-900">{{ t('souk.buy.pay.receipt') }}</span>
            <img v-if="receiptPreview" :src="receiptPreview" class="w-11 h-11 rounded-lg object-cover ring-1 ring-stone-200 shrink-0" alt="" />
            <label class="shrink-0 h-11 px-3 rounded-xl bg-stone-100 text-[13px] font-semibold text-stone-700 inline-flex items-center gap-1.5 cursor-pointer"><Icon name="camera" :size="14" />
              {{ receiptPreview ? t('souk.buy.retake') : t('souk.buy.receiptTake') }}
              <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickReceipt" />
            </label>
          </div>
          </div>
        </section>

        <div v-if="sendError" class="rounded-xl bg-rose-50 ring-1 ring-inset ring-rose-200 p-3.5 space-y-1" role="alert">
          <div class="text-[13px] font-bold text-rose-800">{{ t('souk.buy.refused') }}</div>
          <div class="text-[13px] text-rose-700 break-words" dir="auto">{{ sendError }}</div>
        </div>
      </template>
    </div>

    <!-- footer: totals + the one button, above the phone tab bar -->
    <footer v-if="formMode" class="lp-footer px-4 pt-3 pb-4">
      <div class="max-w-[520px] mx-auto flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2 text-[13px] text-stone-700 tabular-nums">
          <span class="min-w-0 truncate inline-flex items-center gap-1.5"><Icon name="shopping-bag" :size="14" class="text-[var(--accent-600)] shrink-0" />{{ tt(tab === 'new' ? 'souk.buy.summary' : 'souk.buy.summaryAgain', { v: lineCount, n: units }) }}</span>
          <span class="shrink-0 text-[17px] font-extrabold text-stone-900">{{ fmt(total) }} <small class="text-[12px] font-semibold text-stone-500">MAD</small></span>
        </div>
        <p v-if="why" class="text-[12px] font-semibold text-amber-800 flex items-start gap-1.5" aria-live="polite">
          <Icon name="info" :size="13" class="mt-[2px] shrink-0" />{{ why }}
        </p>
        <button class="w-full h-12 rounded-xl bg-gradient-to-b from-[var(--accent-500)] to-[var(--accent-700)] text-white text-[15px] font-bold disabled:opacity-40 disabled:from-stone-400 disabled:to-stone-500 shadow-[0_6px_16px_-6px_rgba(196,73,42,.7)] disabled:shadow-none"
                :disabled="busy || !!why" @click="submit">
          {{ busy ? t('souk.sending') : tab === 'new' ? t('souk.buy.createBtn') : t('souk.confirmRebuy') }}
        </button>
      </div>
    </footer>
    <BarcodeScan v-model:open="scanOpen" @code="onCode" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick, defineComponent, h } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { swatch } from "@/souk/stages";
import { api, apiPost } from "@/lib/resource";
import { shrink } from "@/lib/soukPhoto";
import BarcodeScan from "@/souk/BarcodeScan.vue";
import { outbox, enqueue, onDone, newKey, flush, retry as retryJob, discard as discardJob } from "@/lib/soukOutbox";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t, locale } = useI18n();
const { warn } = useToast();
const route = useRoute();
const isAr = computed(() => (locale?.value || "ar") === "ar");
const tt = (k, vars = {}) => {
  let s = String(t(k));
  for (const [a, b] of Object.entries(vars)) s = s.split("{" + a + "}").join(String(b ?? ""));
  return s;
};

// A −/+ stepper with a typed field between: a thumb in the market, one hand
// holding the goods, needs targets, not a tiny number box. `compact` is the
// design's grid cell: one 44px-tall box, − and + inside it.
const Stepper = defineComponent({
  props: { modelValue: { type: [Number, String, null], default: null }, id: String, label: String, less: String, more: String,
           compact: Boolean },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const val = () => Number(props.modelValue) || 0;
    const set = (n) => emit("update:modelValue", n > 0 ? Math.min(99999, Math.round(n)) : null);
    const c = () => props.compact;
    const btn = () => (c()
      ? "w-9 h-11 shrink-0 text-[18px] text-stone-500 inline-flex items-center justify-center active:bg-stone-100 disabled:opacity-30 select-none"
      : "w-11 h-11 rounded-lg bg-white ring-1 ring-inset ring-stone-300 text-[20px] font-bold text-stone-700 inline-flex items-center justify-center active:bg-stone-100 disabled:opacity-30 select-none");
    return () => h("div", { class: c()
      ? "flex items-center w-[104px] h-11 shrink-0 rounded-lg ring-1 ring-inset ring-stone-300 bg-white overflow-hidden"
      : "flex items-center gap-1 shrink-0" }, [
      h("button", { type: "button", class: btn(), "aria-label": props.less, disabled: val() <= 0, onClick: () => set(val() - 1) }, "−"),
      h("input", {
        id: props.id, type: "number", inputmode: "numeric", min: 0, placeholder: "0", "aria-label": props.label,
        value: props.modelValue ?? "",
        class: c()
          ? "flex-1 min-w-0 w-full h-11 bg-transparent text-center text-[15px] font-semibold text-stone-900 tabular-nums"
          : "w-[60px] h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white text-center text-[16px] font-bold tabular-nums",
        onFocus: (e) => e.target.select(),
        onInput: (e) => { const v = e.target.value; set(v === "" ? 0 : parseInt(v, 10) || 0); },
      }),
      h("button", { type: "button", class: btn(), "aria-label": props.more, onClick: () => set(val() + 1) }, "+"),
    ]);
  },
});

const DRAFT_KEY = "lp_souk_buy_draft";
const CAT_KEY = "lp_souk_last_category";
const SENT_KEY = "lp_souk_buy_sent";
const QUEUED_KEY = "lp_souk_buy_queued";
const QUICK_SIZES = ["S", "M", "L", "XL", "XXL"];

function readJSON(k, dflt) {
  try { return JSON.parse(localStorage.getItem(k) || "null") ?? dflt; } catch (_) { return dflt; }
}
function writeJSON(k, v) {
  try {
    if (v == null) localStorage.removeItem(k);
    else localStorage.setItem(k, JSON.stringify(v));
    return true;
  } catch (_) { return false; }
}

const boot = ref(null);
const loading = ref(true);
const busy = ref(false);
const tab = ref("new");
const done = ref(null);
const sent = ref(null);        // {jobId, kind, summary, state: queued|creating|stuck|photo|refused, pending, error}
const sendError = ref("");
const draftOk = ref(true);
const lastCat = ref(readJSON(CAT_KEY, "") || "");

const blank = () => ({ stall: "", newStall: { name: "", phone: "", sure: false }, title: "", category: lastCat.value || "", colors: [],
                       barcode: "", barcodeSure: false });
const f = reactive(blank());
const sizes = ref([]);           // [{id, label, code}] — label is what the customer reads, code goes into the SKU
const qty = reactive({});
const cost = reactive({});
const price = reactive({});
const clientKey = ref("");
const refFile = ref(null);
const refPreview = ref("");
const receiptFile = ref(null);
const receiptPreview = ref("");
const similarRows = ref([]);
const similarHidden = ref([]);
const againQ = ref("");
const againRows = ref([]);
const again = ref(null);
const queued = ref(readJSON(QUEUED_KEY, {}) || {});

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const cat = computed(() => boot.value?.categories.find((c) => c.key === f.category));
const formMode = computed(() => !!(boot.value && !done.value && !sent.value));

// ── payment ──────────────────────────────────────────────────────────────────
const PAY = [
  // each way to pay wears its own soft colour (icon chip + ring when picked)
  { k: "cash", icon: "wallet", cls: "st-live" }, { k: "cheque", icon: "notebook-pen", cls: "st-photos" },
  { k: "transfer", icon: "send", cls: "st-studio" }, { k: "credit", icon: "clock", cls: "st-bought" },
];
const pay = reactive({ method: "", ref: "", due: "", picked: false });
const payLabel = (m) => (m ? t("souk.buy.pay." + m) : "—");
function choosePay(m) {
  pay.method = m;
  pay.picked = true;
  if (m === "cash") { pay.ref = ""; pay.due = ""; }
  if (m === "transfer") pay.due = "";
  if (m === "credit") pay.ref = "";
}
// Until the buyer picks: the way this stall was paid last time, else cash
// when a custody is open.
function defaultPay() {
  if (pay.picked) return;
  const last = (boot.value?.lastPay || {})[f.stall];
  pay.method = last || (boot.value?.trip ? "cash" : "");
}

// ── colours ──────────────────────────────────────────────────────────────────
const colorName = (c) => (isAr.value ? `${c.ar} · ${c.fr}` : c.fr);
const colorLabel = (code) => {
  const x = boot.value?.colors.find((k) => k.code === code);
  return x ? colorName(x) : code;
};
// The quantity grid's row name: just the colour, in the reader's language.
const colorShort = (code) => {
  const x = boot.value?.colors.find((k) => k.code === code);
  return x ? (isAr.value ? x.ar : x.fr) : code;
};
// The design shows the chosen colours + "+ Colour", which opens the list.
const colorsOpen = ref(false);
const shownColors = computed(() => (boot.value?.colors || []).filter((c) => colorsOpen.value || f.colors.includes(c.code)));
function toggleColor(c) {
  const i = f.colors.indexOf(c);
  if (i >= 0) f.colors.splice(i, 1);
  else f.colors.push(c);
}

// ── sizes ────────────────────────────────────────────────────────────────────
// Same rule as the server's _size_code: capitals and digits, 4 at most.
const sizeCode = (z) => String(z || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4);
const effCode = (s) => sizeCode((s.code || "").trim() || s.label);
const sid = () => "z" + Math.random().toString(36).slice(2, 8);
function addSize(label) {
  sizes.value.push({ id: sid(), label: label || "", code: "" });
}
function removeSize(i) {
  const [s] = sizes.value.splice(i, 1);
  if (!s) return;
  for (const k of Object.keys(qty)) if (k.endsWith("|" + s.id)) delete qty[k];
  delete cost[s.id];
  delete price[s.id];
}
// Sizes are chips ("Small · 24 cm · S"); tapping one opens its editor.
const editSize = ref(null);
const editing = computed(() => sizes.value.find((s) => s.id === editSize.value) || null);
const sizeBad = (s) => !!(s.label || "").trim() && !effCode(s);
function sizeChip(s) {
  const label = (s.label || "").trim();
  if (!label) return "…";
  const code = effCode(s);
  return code && code !== label ? `${label} · ${code}` : label;
}
const quickLeft = computed(() => QUICK_SIZES.filter((q) => !sizes.value.some((s) => effCode(s) === q)));
function focusId(id) {
  nextTick(() => document.getElementById(id)?.focus());
}
function newSize(label) {
  addSize(label);
  editSize.value = sizes.value[sizes.value.length - 1].id;
  focusId("sb-sz-" + editSize.value);
}
function toggleEdit(s) {
  if (editSize.value === s.id) { closeEdit(); return; }
  closeEdit();
  editSize.value = s.id;
}
// A size left without a description is no size: drop it on close.
function closeEdit() {
  const s = editing.value;
  editSize.value = null;
  if (s && !(s.label || "").trim()) {
    const i = sizes.value.indexOf(s);
    if (i >= 0) removeSize(i);
  }
}
function removeEditing() {
  const i = sizes.value.findIndex((s) => s.id === editSize.value);
  editSize.value = null;
  if (i >= 0) removeSize(i);
}
// A new stall that may already be one: asked while the buyer types.
const stMatch = ref([]);
let stTimer = null;
watch(() => [f.stall, f.newStall.name, f.newStall.phone], ([stall, name, phone], old) => {
  clearTimeout(stTimer);
  if (old && (old[1] !== name || old[2] !== phone)) f.newStall.sure = false;
  const n = (name || "").replace(/[^A-Za-z0-9]/g, "");
  const p = (phone || "").replace(/\D/g, "");
  if (stall || (n.length < 3 && p.length < 9)) { stMatch.value = []; return; }
  stTimer = setTimeout(async () => {
    try {
      const r = await api("souk_stalls.similar_stalls", { name, phone });
      if (f.newStall.name === name && f.newStall.phone === phone) stMatch.value = (r && r.rows) || [];
    } catch (_) { stMatch.value = []; }
  }, 450);
});
function useMatch(m) {
  if (boot.value && !boot.value.stalls.some((s) => s.name === m.name)) boot.value.stalls.unshift({ name: m.name, label: m.label });
  f.stall = m.name;
  f.newStall = { name: "", phone: "", sure: false };
  stMatch.value = [];
}

// "+" beside the stall list: a new stall, typed below.
function newStall() {
  f.stall = "";
  focusId("sb-stall-name");
}
const namedSizes = computed(() => sizes.value.filter((s) => (s.label || "").trim()));
const sizeCols = computed(() => (namedSizes.value.length ? namedSizes.value : [{ id: "", label: "", code: "" }]));
const zName = (z) => (z.label ? effCode(z) || z.label.trim() : "");
const colorRows = computed(() => (f.colors.length ? f.colors : [""]));
// Grid tracks: the name column, then one per size (the box scrolls sideways
// past what a phone can hold — never the page).
const qtyCols = computed(() => ({ gridTemplateColumns: `minmax(64px, 1fr) repeat(${sizeCols.value.length}, 104px)` }));
const marginCols = computed(() => ({ gridTemplateColumns: `minmax(96px, 1fr) repeat(${sizeCols.value.length}, minmax(56px, max-content))` }));
const key = (c, z) => `${c}|${z}`;
function samePrices() {
  const first = sizeCols.value[0];
  for (const z of sizeCols.value.slice(1)) {
    cost[z.id] = cost[first.id];
    price[z.id] = price[first.id];
  }
}

const lines = computed(() => {
  if (!boot.value) return [];
  const out = [];
  for (const c of colorRows.value) {
    for (const z of sizeCols.value) {
      const q = Number(qty[key(c, z.id)]) || 0;
      if (q <= 0) continue;
      const label = (z.label || "").trim();
      const code = label ? effCode(z) : "";
      const sku = [boot.value.nextSku, c, code].filter(Boolean).join("-");
      out.push({ color: c, size: label, sizeCode: label ? (z.code || "").trim() : "", code, zid: z.id,
                 qty: q, cost: Number(cost[z.id]) || 0, price: Number(price[z.id]) || 0, sku });
    }
  }
  return out;
});
function margin(zid) {
  const c = Number(cost[zid]) || 0;
  const p = Number(price[zid]) || 0;
  if (!c || !p) return null;
  return Math.round(((p - c) / p) * 100);
}

const againLines = computed(() => (again.value?.rows || []).filter((r) => (Number(r.qty) || 0) > 0));
const units = computed(() => (tab.value === "again"
  ? againLines.value.reduce((s, r) => s + (Number(r.qty) || 0), 0)
  : lines.value.reduce((s, l) => s + l.qty, 0)));
const lineCount = computed(() => (tab.value === "again" ? againLines.value.length : lines.value.length));
const total = computed(() => (tab.value === "again"
  ? againLines.value.reduce((s, r) => s + (Number(r.qty) || 0) * (Number(r.cost) || 0), 0)
  : lines.value.reduce((s, l) => s + l.qty * l.cost, 0)));

// Custody left: the server's number, minus what is waiting on this phone and
// has not reached the server yet (a purchase made offline is money spent).
const offlineSpent = computed(() => {
  let s = 0;
  for (const j of outbox.jobs) {
    const a = queued.value[j.id];
    if (a == null || j.failed) continue;
    if (j.state && (j.state.name || j.state.po)) continue;   // the server already counts it
    s += Number(a) || 0;
  }
  return s;
});
const left = computed(() => (boot.value?.trip ? boot.value.trip.expected - offlineSpent.value : 0));
function setQueued(id, amount) {
  const m = { ...queued.value };
  if (amount == null) delete m[id];
  else m[id] = amount;
  queued.value = m;
  writeJSON(QUEUED_KEY, m);
}

const stallOk = computed(() => !!f.stall || (f.newStall.name || "").replace(/[^A-Za-z0-9]/g, "").length >= 3);

// Why the button is grey — the first thing to fix, in words.
const why = computed(() => {
  if (!boot.value) return "";
  const W = (k, v) => tt("souk.buy.why." + k, v);
  if (tab.value === "again") {
    if (!again.value) return W("pick");
    if (!stallOk.value) return W("stall");
    if (!againLines.value.length) return W("qty");
    const r = againLines.value.find((x) => !(Number(x.cost) > 0));
    if (r) return W("cost", { z: r.sku });
  } else {
    // A known barcode first: the answer is "buy it again", not "fill the form".
    if (f.barcode && bcHits.value.length && !f.barcodeSure) return t("souk.scan.why");
    if (f.title.trim().length < 3) return W("title");
    if (!f.category) return W("category");
    if (!stallOk.value) return W("stall");
    const bad = namedSizes.value.find((s) => !effCode(s));
    if (bad) return W("sizeCode", { z: bad.label.trim() });
    const labels = namedSizes.value.map((s) => s.label.trim().toLowerCase());
    const codes = namedSizes.value.map(effCode);
    if (new Set(labels).size !== labels.length || new Set(codes).size !== codes.length) return W("sizeDup");
    if (!lines.value.length) return W("qty");
    for (const l of lines.value) {
      const z = l.code || l.size || t("souk.buy.oneSize");
      if (!(l.cost > 0)) return W("cost", { z });
      if (!(l.price > 0)) return W("price", { z });
      if (l.price <= l.cost) return W("priceLow", { z });
    }
    const long = lines.value.find((l) => l.sku.length > boot.value.skuMax);
    if (long) return W("skuLong", { sku: long.sku, n: boot.value.skuMax });
  }
  if (total.value <= 0) return W("qty");
  if (!pay.method) return W("pay");
  return "";
});

// ── photos ───────────────────────────────────────────────────────────────────
function pickRef(e) {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (!file) return;
  if (refPreview.value) URL.revokeObjectURL(refPreview.value);
  refFile.value = file;
  refPreview.value = URL.createObjectURL(file);
}
function pickReceipt(e) {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (!file) return;
  if (receiptPreview.value) URL.revokeObjectURL(receiptPreview.value);
  receiptFile.value = file;
  receiptPreview.value = URL.createObjectURL(file);
}

// ── do we already have it? ───────────────────────────────────────────────────
function ago(d) {
  const day = new Date(String(d).slice(0, 10) + "T00:00:00");
  if (isNaN(day.getTime())) return String(d);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const n = Math.round((today - day) / 86400000);
  if (n <= 0) return t("souk.buy.today");
  if (n === 1) return t("souk.buy.yesterday");
  if (n < 60) return tt("souk.buy.daysAgo", { n });
  try {
    return day.toLocaleDateString(isAr.value ? "ar-u-nu-latn" : locale.value || "fr",
                                  { day: "numeric", month: "short", year: "numeric" });
  } catch (_) { return String(d).slice(0, 10); }
}
const similarShown = computed(() => similarRows.value.filter((r) => !similarHidden.value.includes(r.kind + r.key)));
function dismissSimilar() {
  similarHidden.value = [...similarHidden.value, ...similarRows.value.map((r) => r.kind + r.key)];
}
let simTimer = null;
function lookSimilar() {
  clearTimeout(simTimer);
  simTimer = setTimeout(async () => {
    const q = f.title.trim();
    if (q.length < 3) { similarRows.value = []; return; }
    try { similarRows.value = (await api("souk.similar", { q, category: f.category || "" })).rows.slice(0, 4); } catch (_) { /* advisory only */ }
  }, 450);
}
let agTimer = null;
function lookAgain() {
  clearTimeout(agTimer);
  agTimer = setTimeout(async () => {
    const q = againQ.value.trim();
    if (q.length < 3) { againRows.value = []; return; }
    try { againRows.value = (await api("souk.similar", { q })).rows; } catch (_) { /* advisory only */ }
  }, 400);
}
// ── the box's barcode ────────────────────────────────────────────────────────
// Scanned on "new": known = the buyer is shown the product to buy again (the
// server refuses a new one unless they say it is different); unknown = kept
// on the new product. Scanned on "again": one match opens it straight away.
const scanOpen = ref(false);
const scanFor = ref("new");
const bcHits = ref([]);
const bcBusy = ref(false);
const againBarcode = ref("");
const againNone = ref(false);
function openScan(where) {
  scanFor.value = where;
  scanOpen.value = true;
}
async function onCode(code) {
  if (scanFor.value === "again") {
    againBarcode.value = code;
    againNone.value = false;
    again.value = null;
    try {
      const rows = (await api("souk.similar", { barcode: code })).rows || [];
      if (rows.length === 1) startAgain(rows[0]);
      else { againRows.value = rows; againNone.value = !rows.length; }
    } catch (e) {
      warn(t("souk.failed"), String(e.message || e));
    }
    return;
  }
  f.barcodeSure = false;
  f.barcode = code;
}
function clearBarcode() {
  f.barcode = "";
  f.barcodeSure = false;
  bcHits.value = [];
}
// Also after a draft comes back with a barcode in it.
watch(() => f.barcode, async (code) => {
  bcHits.value = [];
  if (!code) return;
  bcBusy.value = true;
  try {
    const rows = (await api("souk.similar", { barcode: code })).rows || [];
    if (f.barcode === code) bcHits.value = rows;
  } catch (_) { /* the server checks again at submit */ } finally {
    bcBusy.value = false;
  }
}, { immediate: true });

async function startAgain(r) {
  tab.value = "again";
  try {
    const d = await api("souk.rebuy_lookup", { key: r.key, kind: r.kind });
    again.value = { ...d, key: r.key, kind: r.kind, rows: d.rows.map((x) => ({ ...x, qty: null })) };
    if (d.lastStall && boot.value?.stalls.some((s) => s.name === d.lastStall)) f.stall = d.lastStall;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  }
}

// ── keep the form on the phone ───────────────────────────────────────────────
const hasContent = computed(() => !!(f.title.trim() || f.colors.length || sizes.value.length || f.newStall.name
  || Object.values(qty).some((v) => Number(v) > 0) || again.value));
function saveDraft() {
  draftOk.value = writeJSON(DRAFT_KEY, {
    v: 2, tab: tab.value,
    f: { ...f, newStall: { ...f.newStall }, colors: [...f.colors] },
    sizes: sizes.value.map((s) => ({ ...s })),
    qty: { ...qty }, cost: { ...cost }, price: { ...price },
    clientKey: clientKey.value, again: again.value,
    pay: { ...pay },
  });
}
function loadDraft() {
  const d = readJSON(DRAFT_KEY, null);
  if (!d) return;
  Object.assign(f, blank(), d.f || {});
  f.newStall = { name: "", phone: "", ...((d.f || {}).newStall || {}) };
  if (Array.isArray(d.sizes)) {
    sizes.value = d.sizes.map((s) => ({ id: s.id || sid(), label: s.label || "", code: s.code || "" }));
    Object.assign(qty, d.qty || {});
    Object.assign(cost, d.cost || {});
    Object.assign(price, d.price || {});
  } else if (d.sizesText) {
    // The first bundle kept sizes as "S, M, L" keyed by the label itself.
    const old = [...new Set(String(d.sizesText).split(/[,\s،]+/).map((s) => s.trim().toUpperCase()).filter(Boolean))];
    sizes.value = old.map((label) => ({ id: sid(), label, code: "" }));
    for (const s of sizes.value) {
      if ((d.cost || {})[s.label] != null) cost[s.id] = d.cost[s.label];
      if ((d.price || {})[s.label] != null) price[s.id] = d.price[s.label];
    }
    for (const [k, v] of Object.entries(d.qty || {})) {
      const [c, z] = k.split("|");
      const s = sizes.value.find((x) => x.label === z);
      qty[key(c, s ? s.id : "")] = v;
    }
  }
  clientKey.value = d.clientKey || "";
  if (d.tab === "again" || d.tab === "new") tab.value = d.tab;
  if (d.again && Array.isArray(d.again.rows)) again.value = d.again;
  if (d.pay && PAY.some((m) => m.k === d.pay.method)) Object.assign(pay, { ref: "", due: "", ...d.pay });
}
watch([f, sizes, qty, cost, price, tab, again, clientKey, pay], saveDraft, { deep: true });
watch([() => f.stall, boot], defaultPay);
watch(() => f.category, (c) => { if (c) { lastCat.value = c; writeJSON(CAT_KEY, c); } });

function clearForm() {
  Object.assign(f, blank());
  f.newStall = { name: "", phone: "" };
  f.colors = [];
  sizes.value = [];
  editSize.value = null;
  colorsOpen.value = false;
  for (const o of [qty, cost, price]) for (const k of Object.keys(o)) delete o[k];
  if (refPreview.value) URL.revokeObjectURL(refPreview.value);
  if (receiptPreview.value) URL.revokeObjectURL(receiptPreview.value);
  refFile.value = null; refPreview.value = "";
  receiptFile.value = null; receiptPreview.value = "";
  similarRows.value = []; similarHidden.value = [];
  bcHits.value = []; againBarcode.value = ""; againNone.value = false;
  again.value = null; againQ.value = ""; againRows.value = [];
  clientKey.value = "";
  sendError.value = "";
  Object.assign(pay, { method: "", ref: "", due: "", picked: false });
  defaultPay();
  tab.value = "new";
  writeJSON(DRAFT_KEY, null);
}
function setSent(s) {
  sent.value = s;
  writeJSON(SENT_KEY, s);
}
function another() {
  done.value = null;
  setSent(null);
  clearForm();
  load();
  window.scrollTo?.({ top: 0 });
}

// ── send, through the outbox ─────────────────────────────────────────────────
const stallLabel = () => (f.stall ? (boot.value?.stalls.find((s) => s.name === f.stall)?.label || f.stall)
  : (f.newStall.name || "").trim().toUpperCase());

function finish(summary, r) {
  done.value = {
    again: summary.again, title: summary.title, stall: summary.stall, brand: summary.brand,
    amount: summary.total, units: summary.units,
    po: r?.po || "", pi: r?.pi || "", left: summary.pay === "cash" ? (r?.left ?? null) : null, pay: summary.pay,
    variants: (r?.variants?.length ? r.variants : summary.lines || []).map((v) => ({ sku: v.sku, qty: v.qty, cost: v.cost })),
  };
  if (summary.again) done.value.variants = summary.lines || [];
  setSent(null);
  load();
}

// What a refused job means for the buyer: nothing made (refused), the
// purchase made but a photo stuck (photo), or the product made and its last
// step (Shopify / Next) erroring (stuck — finish_buy by hand).
function classify(kind, summary, jst, epending) {
  const made = jst.name || jst.po || epending;
  if (!made) return "refused";
  if (epending) return "stuck";
  if (kind === "rebuy") return "photo";
  if ((summary.hasRef && !jst.ref) || (summary.hasReceipt && !jst.receipt)) return "photo";
  return "stuck";
}

async function submit() {
  if (busy.value || why.value) return;
  // The key is made ONCE, when the button is first pressed, and kept in the
  // draft: a reload or a second press re-sends the same purchase.
  if (!clientKey.value) clientKey.value = newKey();
  saveDraft();
  busy.value = true;
  sendError.value = "";
  const isNew = tab.value === "new";
  const jobId = (isNew ? "buy-" : "rebuy-") + clientKey.value;
  const summary = {
    again: !isNew, title: isNew ? f.title.trim() : again.value.title, stall: stallLabel(),
    brand: isNew ? cat.value?.brand || "" : "", total: total.value, units: units.value,
    hasRef: isNew && !!refFile.value, hasReceipt: !!receiptFile.value, pay: pay.method,
    lines: isNew ? lines.value.map((l) => ({ sku: l.sku, qty: l.qty, cost: l.cost }))
      : againLines.value.map((r) => ({ sku: r.sku, qty: Number(r.qty), cost: Number(r.cost) })),
  };
  try {
    const receipt = receiptFile.value ? await shrink(receiptFile.value) : null;
    let job;
    if (isNew) {
      const ref = refFile.value ? await shrink(refFile.value) : null;
      job = {
        id: jobId, kind: "buy", label: summary.title, ref, receipt,
        payload: {
          title: f.title.trim(), category: f.category, colors: [...f.colors],
          sizes: namedSizes.value.map((s) => s.label.trim()),
          stall: f.stall, newStall: { ...f.newStall },
          lines: lines.value.map((l) => ({ color: l.color, size: l.size, ...(l.sizeCode ? { sizeCode: l.sizeCode } : {}),
                                           qty: l.qty, cost: l.cost, price: l.price })),
          payment: { method: pay.method, ref: pay.ref.trim(), due: pay.due },
          clientKey: clientKey.value,
          ...(f.barcode ? { barcode: f.barcode, barcodeSure: !!f.barcodeSure } : {}),
        },
      };
    } else {
      job = {
        id: jobId, kind: "rebuy", label: summary.title, receipt,
        payload: {
          kind: again.value.kind, product: again.value.key, stall: f.stall, newStall: { ...f.newStall },
          lines: againLines.value.map((x) => ({ itemCode: x.itemCode, qty: Number(x.qty), cost: Number(x.cost) })),
          payment: { method: pay.method, ref: pay.ref.trim(), due: pay.due },
          clientKey: clientKey.value,
          // Scanned but unknown, then found by name: the catalogue learns it.
          ...(againBarcode.value && againNone.value ? { barcode: againBarcode.value } : {}),
        },
      };
    }
    setQueued(jobId, pay.method === "cash" ? summary.total : 0);
    const r = await enqueue(job);
    clearForm();
    if (r && r.queued) {
      const name = r.pending || outbox.jobs.find((x) => x.id === jobId)?.state?.name || "";
      setSent({ jobId, kind: job.kind, summary, state: name ? "creating" : "queued", pending: name, error: "" });
    } else {
      setQueued(jobId, null);
      finish(summary, r);
    }
  } catch (e) {
    const msg = String((e && e.message) || e);
    const j = outbox.jobs.find((x) => x.id === jobId);
    const state = classify(isNew ? "buy" : "rebuy", summary, j?.state || {}, e?.pending);
    if (state !== "refused") {
      // The server has the purchase; what failed is a photo or the last step.
      clearForm();
      setSent({ jobId, kind: isNew ? "buy" : "rebuy", summary, pending: j?.state?.name || e?.pending || "",
                po: j?.state?.po || "", state, error: msg });
    } else {
      // Refused (custody left, unknown stall…): nothing was made. The form is
      // still here, so the job goes — pressing again sends the same key.
      setQueued(jobId, null);
      if (j) await discardJob(jobId).catch(() => {});
      sendError.value = msg;
    }
  } finally {
    busy.value = false;
  }
}

// Stuck product (an error on Shopify / Next): drive finish_buy by hand.
async function checkPending(rounds = 1) {
  const s = sent.value;
  if (!s || !s.pending) return;
  busy.value = true;
  try {
    for (let i = 0; i < rounds; i++) {
      const r = await apiPost("souk.finish_buy", { name: s.pending });
      if (!r.pending) {
        await discardJob(s.jobId).catch(() => {});
        setQueued(s.jobId, null);
        finish(s.summary, r);
        return;
      }
      setSent({ ...s, state: r.error ? "stuck" : "creating", error: r.error || "" });
      if (r.error) return;
      if (i < rounds - 1) await new Promise((ok) => setTimeout(ok, 4000));
    }
  } catch (e) {
    setSent({ ...s, state: "stuck", error: String((e && e.message) || e) });
  } finally {
    busy.value = false;
  }
}
async function retrySent() {
  const s = sent.value;
  if (!s) return;
  busy.value = true;
  try {
    const r = await retryJob(s.jobId);
    if (r == null) { setSent(null); return; }          // gone from the phone (discarded elsewhere)
    if (r.queued) setSent({ ...s, state: r.pending ? "creating" : "queued", pending: r.pending || s.pending, error: "" });
    else { setQueued(s.jobId, null); finish(s.summary, r); }
  } catch (e) {
    setSent({ ...s, state: e?.pending ? "stuck" : s.state, pending: e?.pending || s.pending, error: String((e && e.message) || e) });
  } finally {
    busy.value = false;
  }
}
async function skipPhoto() {
  const s = sent.value;
  if (!s) return;
  if (s.kind === "rebuy") {
    // The PO exists; the receipt can be added from the trip.
    await discardJob(s.jobId).catch(() => {});
    setQueued(s.jobId, null);
    finish(s.summary, { po: s.po });
    return;
  }
  await checkPending(4);
}
async function discardSent() {
  const s = sent.value;
  if (!s) return;
  if (!window.confirm(t("souk.offline.discardConfirm"))) return;
  await discardJob(s.jobId).catch(() => {});
  setQueued(s.jobId, null);
  setSent(null);
}
// "Check now": a job still waiting goes through the outbox (never two
// finish_buy at once); one the outbox gave up on is driven by hand.
function checkNow() {
  const s = sent.value;
  const j = s && outbox.jobs.find((x) => x.id === s.jobId);
  if (j && !j.failed) flush();
  else checkPending(3);
}

const sentIcon = computed(() => ({ queued: "upload-cloud", creating: "hourglass", stuck: "alert-triangle",
                                    photo: "camera", refused: "alert-circle" }[sent.value?.state] || "info"));
const sentTitle = computed(() => {
  const s = sent.value;
  if (!s) return "";
  if (s.state === "queued") return t("souk.buy.sent.queuedTitle");
  if (s.state === "creating") return t("souk.buy.sent.creatingTitle");
  if (s.state === "photo") return t("souk.buy.sent.photoTitle");
  if (s.state === "refused") return t("souk.buy.sent.refusedTitle");
  return s.pending || t("souk.buy.sent.refusedTitle");
});
const sentBody = computed(() => {
  const s = sent.value;
  if (!s) return "";
  if (s.state === "queued") return t("souk.buy.sent.queuedBody");
  if (s.state === "creating") return tt("souk.buy.sent.creatingBody", { sku: s.pending || s.summary.title });
  if (s.state === "photo") return t("souk.buy.sent.photoBody");
  if (s.state === "refused") return t("souk.buy.refused");
  return t("souk.stuck");
});

// A job that was waiting finished (or was refused) while this screen is open.
const offDone = onDone((job, res) => {
  if (job.kind !== "buy" && job.kind !== "rebuy") return;
  if (sent.value && job.id === sent.value.jobId) {
    setQueued(job.id, null);
    finish(sent.value.summary, res);
  } else {
    setQueued(job.id, null);
    load();
  }
});
watch(() => outbox.jobs, (jobs) => {
  const s = sent.value;
  if (!s || (s.state !== "queued" && s.state !== "creating")) return;
  const j = jobs.find((x) => x.id === s.jobId);
  if (!j) return;                                    // finished: onDone handles it
  if (j.failed) {
    setSent({ ...s, state: classify(s.kind, s.summary, j.state || {}), pending: j.state?.name || s.pending,
              po: j.state?.po || s.po, error: j.error });
  } else if (j.state?.name && s.state === "queued") {
    setSent({ ...s, state: "creating", pending: j.state.name });
  }
});

// After a reload: is what we sent still waiting, stuck, or done?
let reconciled = false;
function reconcile() {
  if (reconciled || !outbox.ready) return;
  reconciled = true;
  const m = { ...queued.value };
  let pruned = false;
  for (const id of Object.keys(m)) if (!outbox.jobs.some((j) => j.id === id)) { delete m[id]; pruned = true; }
  if (pruned) { queued.value = m; writeJSON(QUEUED_KEY, m); }
  const s = sent.value;
  if (!s) return;
  const j = outbox.jobs.find((x) => x.id === s.jobId);
  if (j) {
    if (j.failed && (s.state === "queued" || s.state === "creating")) {
      setSent({ ...s, state: classify(s.kind, s.summary, j.state || {}), pending: j.state?.name || s.pending,
                po: j.state?.po || s.po, error: j.error });
    }
    return;
  }
  // Not on the phone any more: it went through (or was discarded).
  if (s.pending) checkPending(1);
  else setSent(null);
}
watch(() => outbox.ready, reconcile);

async function load() {
  loading.value = true;
  try {
    boot.value = await api("souk.buy_boot");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  sent.value = readJSON(SENT_KEY, null);
  if (sent.value && !sent.value.summary) sent.value = null;
  loadDraft();
  await load();
  reconcile();
  if (route.query.again && !sent.value) await startAgain({ key: route.query.again, kind: route.query.kind || "souk" });
});
onBeforeUnmount(() => {
  offDone();
  clearTimeout(simTimer);
  clearTimeout(agTimer);
});
</script>
