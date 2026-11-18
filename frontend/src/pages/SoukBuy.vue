<template>
  <!-- Souk buying, on the buyer's phone in the market. A NEW product is born
       as a Shopify Draft (vendor = our house brand by category), its Next
       items come from the sync, and a PO on the stall is paid from the
       custody. BUY AGAIN is a PO only. Backend: souk.create_buy / finish_buy /
       create_rebuy — always through the outbox (lib/soukOutbox): Derb Omar
       drops the line, so a purchase is a job kept on the phone with its
       photos and a clientKey, never lost and never made twice. The form
       itself is kept on the phone (localStorage) until it is sent. -->
  <div class="max-w-[520px] mx-auto px-4 pt-3 pb-48 space-y-4">
    <header class="flex items-center gap-2">
      <router-link :to="{ name: 'SoukTrip' }" :aria-label="t('souk.buy.back')"
                   class="shrink-0 w-11 h-11 -ms-2 rounded-lg inline-flex items-center justify-center text-stone-600 hover:bg-stone-100">
        <Icon name="chevron-left" :size="20" class="rtl:rotate-180" />
      </router-link>
      <div class="flex-1 min-w-0">
        <h1 class="text-[17px] font-bold text-stone-900 leading-tight">{{ t('souk.buyTitle') }}</h1>
        <div class="text-[11.5px] text-stone-500 truncate tabular-nums">
          {{ boot?.trip ? tt('souk.buy.sub', { place: boot.trip.place || 'Derb Omar', n: fmt(left) }) : t('souk.title') }}
        </div>
      </div>
      <span v-if="formMode && hasContent" class="shrink-0 text-[11px] font-semibold inline-flex items-center gap-1.5"
            :class="draftOk ? 'text-emerald-700' : 'text-amber-700'" aria-live="polite">
        <span class="w-[7px] h-[7px] rounded-full" :class="draftOk ? 'bg-emerald-600' : 'bg-amber-500'" />
        {{ draftOk ? t('souk.buy.saved') : t('souk.buy.notSaved') }}
      </span>
    </header>

    <div v-if="loading && !boot" class="h-[320px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <div v-else-if="boot && !boot.trip && !done && !sent"
         class="bg-amber-50 ring-1 ring-amber-200 rounded-2xl p-5 text-[13px] text-amber-900 leading-relaxed">
      {{ t('souk.noTrip') }}
    </div>

    <!-- ── done ─────────────────────────────────────────────────────────── -->
    <section v-else-if="done" class="space-y-3">
      <div class="text-center pt-3 pb-1 space-y-2">
        <div class="mx-auto w-14 h-14 rounded-full bg-emerald-50 ring-1 ring-emerald-200 text-emerald-700 flex items-center justify-center">
          <Icon name="check" :size="26" />
        </div>
        <h2 class="text-[17px] font-bold text-stone-900">
          {{ tt(done.again ? 'souk.buy.done.rebuyTitle' : 'souk.buy.done.title', { title: done.title || done.po }) }}
        </h2>
        <p class="text-[12.5px] text-stone-600">{{ t('souk.buy.done.goodsIn') }}</p>
      </div>

      <div class="bg-white ring-1 ring-stone-200/70 rounded-2xl divide-y divide-stone-100">
        <div v-if="!done.again" class="px-4 py-3 flex items-center gap-3">
          <span class="w-2 h-2 rounded-full bg-emerald-600 shrink-0" />
          <div class="flex-1 min-w-0">
            <div class="text-[13px] font-semibold text-stone-900">{{ t('souk.buy.done.draft') }}</div>
            <div class="text-[11.5px] text-stone-500">{{ tt('souk.buy.done.draftSub', { brand: done.brand || '—' }) }}</div>
          </div>
          <span class="text-[10.5px] font-bold rounded-md px-2 py-0.5 bg-stone-100 text-stone-700">DRAFT</span>
        </div>
        <div v-if="!done.again && done.variants.length" class="px-4 py-3 flex items-center gap-3">
          <span class="w-2 h-2 rounded-full bg-emerald-600 shrink-0" />
          <div class="flex-1 min-w-0">
            <div class="text-[13px] font-semibold text-stone-900">{{ tt('souk.buy.done.next', { n: done.variants.length }) }}</div>
            <div class="text-[11.5px] text-stone-500">{{ t('souk.buy.done.nextSub') }}</div>
          </div>
        </div>
        <div class="px-4 py-3 flex items-center gap-3">
          <span class="w-2 h-2 rounded-full bg-emerald-600 shrink-0" />
          <div class="flex-1 min-w-0">
            <div class="text-[13px] font-semibold text-stone-900">
              {{ tt(done.pi ? 'souk.buy.done.po' : 'souk.buy.done.poOnly', { stall: done.stall || '—' }) }}
            </div>
            <div v-if="done.po" class="text-[11.5px] text-stone-500"><span class="font-mono" dir="ltr">{{ done.po }}<span v-if="done.pi"> · {{ done.pi }}</span></span></div>
            <div class="text-[11.5px] text-stone-500 tabular-nums">{{ tt('souk.buy.done.amount', { n: fmt(done.amount), u: done.units }) }}</div>
          </div>
        </div>
      </div>

      <div v-if="done.variants.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl">
        <div class="px-4 pt-3 pb-1 text-[12px] font-semibold text-stone-600">{{ t('souk.skus') }}</div>
        <div class="divide-y divide-stone-100">
          <div v-for="v in done.variants" :key="v.sku" class="px-4 py-2 flex items-center justify-between gap-2 text-[12.5px]">
            <span class="font-mono font-bold text-stone-900" dir="ltr">{{ v.sku }}</span>
            <span class="text-stone-500 tabular-nums">{{ v.qty }} {{ t('souk.pcs') }}<span v-if="v.cost"> × {{ fmt(v.cost) }} MAD</span></span>
          </div>
        </div>
      </div>

      <div class="bg-stone-900 text-white rounded-2xl p-4 flex items-center justify-between">
        <span class="text-[12.5px] text-stone-300">{{ t('souk.leftWithYou') }}</span>
        <span class="text-[22px] font-extrabold tabular-nums">{{ fmt(done.left ?? left) }} <small class="text-[12px] text-stone-300">MAD</small></span>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <button class="h-12 rounded-xl bg-[var(--accent-600)] text-white text-[13px] font-bold px-2" @click="another">{{ t('souk.buy.done.another') }}</button>
        <router-link :to="{ name: 'SoukTrip' }" class="h-12 rounded-xl bg-white ring-1 ring-stone-300 text-stone-800 text-[13px] font-bold inline-flex items-center justify-center">{{ t('souk.buy.done.trip') }}</router-link>
      </div>
    </section>

    <!-- ── sent, not finished: saved on the phone / creating / stuck / photo ── -->
    <section v-else-if="sent" class="space-y-3">
      <div class="rounded-2xl p-4 space-y-2 ring-1"
           :class="sent.state === 'queued' || sent.state === 'creating' ? 'bg-white ring-stone-200/70' : 'bg-rose-50 ring-rose-200'">
        <div class="flex items-center gap-2">
          <Icon :name="sentIcon" :size="18" :class="sent.state === 'queued' || sent.state === 'creating' ? 'text-[var(--accent-600)]' : 'text-rose-600'" />
          <h2 class="text-[15px] font-bold text-stone-900">{{ sentTitle }}</h2>
        </div>
        <p class="text-[12.5px] text-stone-600 leading-relaxed">{{ sentBody }}</p>
        <p v-if="sent.error && sent.state !== 'queued' && sent.state !== 'creating'" class="text-[12px] text-rose-700 font-mono break-words" dir="auto">{{ sent.error }}</p>
      </div>

      <div class="bg-white ring-1 ring-stone-200/70 rounded-2xl px-4 py-3 space-y-1">
        <div class="text-[13.5px] font-bold text-stone-900 truncate">{{ sent.summary.title }}</div>
        <div class="text-[12px] text-stone-500 truncate">{{ sent.summary.stall }} · {{ sent.summary.units }} {{ t('souk.pcs') }}</div>
        <div class="text-[15px] font-extrabold tabular-nums text-stone-900">{{ fmt(sent.summary.total) }} MAD</div>
        <div v-if="sent.pending" class="font-mono text-[11.5px] text-stone-500" dir="ltr">{{ sent.pending }}</div>
      </div>

      <div v-if="boot?.trip" class="bg-stone-900 text-white rounded-2xl p-4 flex items-center justify-between">
        <span class="text-[12.5px] text-stone-300">{{ t('souk.leftWithYou') }}</span>
        <span class="text-[20px] font-extrabold tabular-nums">{{ fmt(left) }} <small class="text-[12px] text-stone-300">MAD</small></span>
      </div>

      <div class="space-y-2">
        <button v-if="sent.state === 'stuck'"
                class="w-full h-12 rounded-xl bg-stone-900 text-white text-[13.5px] font-bold disabled:opacity-40"
                :disabled="busy" @click="checkPending()">
          {{ busy ? t('souk.buy.trip.sending') : t('souk.retry') }}
        </button>
        <button v-if="sent.state === 'creating'"
                class="w-full h-12 rounded-xl bg-white ring-1 ring-stone-300 text-stone-800 text-[13.5px] font-bold disabled:opacity-40"
                :disabled="busy || outbox.flushing || !outbox.online" @click="checkNow">
          {{ outbox.flushing ? t('souk.buy.trip.sending') : t('souk.buy.sent.checkNow') }}
        </button>
        <template v-if="sent.state === 'photo'">
          <button class="w-full h-12 rounded-xl bg-stone-900 text-white text-[13.5px] font-bold disabled:opacity-40"
                  :disabled="busy" @click="retrySent">{{ busy ? t('souk.buy.trip.sending') : t('souk.buy.sent.retryPhoto') }}</button>
          <button class="w-full h-12 rounded-xl bg-white ring-1 ring-stone-300 text-stone-800 text-[13px] font-bold disabled:opacity-40"
                  :disabled="busy" @click="skipPhoto">{{ t('souk.buy.sent.skipPhoto') }}</button>
        </template>
        <template v-if="sent.state === 'refused'">
          <button class="w-full h-12 rounded-xl bg-stone-900 text-white text-[13.5px] font-bold disabled:opacity-40"
                  :disabled="busy" @click="retrySent">{{ t('souk.retry') }}</button>
          <button class="w-full h-12 rounded-xl bg-white ring-1 ring-rose-300 text-rose-700 text-[13px] font-bold disabled:opacity-40"
                  :disabled="busy" @click="discardSent">{{ t('souk.buy.sent.discard') }}</button>
        </template>
        <div class="grid grid-cols-2 gap-2">
          <button class="h-12 rounded-xl bg-white ring-1 ring-stone-300 text-stone-800 text-[13px] font-bold px-2" @click="another">{{ t('souk.buy.done.another') }}</button>
          <router-link :to="{ name: 'SoukTrip' }" class="h-12 rounded-xl bg-white ring-1 ring-stone-300 text-stone-800 text-[13px] font-bold inline-flex items-center justify-center">{{ t('souk.buy.done.trip') }}</router-link>
        </div>
      </div>
    </section>

    <!-- ── the form ─────────────────────────────────────────────────────── -->
    <template v-else-if="boot">
      <div role="tablist" class="grid grid-cols-2 bg-stone-100 rounded-xl p-1 text-[13px] font-bold">
        <button role="tab" :aria-selected="tab === 'new'" class="h-11 rounded-lg"
                :class="tab === 'new' ? 'bg-white shadow-sm text-stone-900' : 'text-stone-500'" @click="tab = 'new'">{{ t('souk.tabNew') }}</button>
        <button role="tab" :aria-selected="tab === 'again'" class="h-11 rounded-lg"
                :class="tab === 'again' ? 'bg-white shadow-sm text-stone-900' : 'text-stone-500'" @click="tab = 'again'">{{ t('souk.tabAgain') }}</button>
      </div>

      <!-- NEW PRODUCT -->
      <template v-if="tab === 'new'">
        <!-- reference photo -->
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 flex gap-3 items-center">
          <label class="w-[76px] h-[76px] shrink-0 rounded-xl ring-1 ring-stone-300 bg-stone-50 flex items-center justify-center overflow-hidden cursor-pointer">
            <img v-if="refPreview" :src="refPreview" class="w-full h-full object-cover" alt="" />
            <Icon v-else name="camera" :size="24" class="text-stone-400" />
            <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickRef" />
          </label>
          <div class="flex-1 min-w-0 space-y-1">
            <div class="text-[13px] font-semibold text-stone-900">{{ t('souk.buy.refTitle') }}</div>
            <div class="text-[11.5px] text-stone-500 leading-snug">{{ t('souk.buy.refNote') }}</div>
            <label class="inline-flex items-center gap-1.5 h-11 px-3 rounded-lg ring-1 ring-stone-300 text-[12.5px] font-semibold text-stone-700 cursor-pointer">
              <Icon name="camera" :size="14" />{{ refPreview ? t('souk.buy.retake') : t('souk.buy.takePhoto') }}
              <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickRef" />
            </label>
          </div>
        </section>

        <!-- name, category, brand -->
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
          <div class="space-y-1">
            <label for="sb-title" class="text-[12px] font-semibold text-stone-600">{{ t('souk.name') }}</label>
            <input id="sb-title" v-model="f.title" :placeholder="t('souk.namePh')" autocomplete="off"
                   class="w-full h-12 rounded-lg ring-1 ring-stone-300 px-3 text-[15px]" @input="lookSimilar" />
          </div>
          <div class="space-y-1">
            <div id="sb-cat" class="text-[12px] font-semibold text-stone-600">{{ t('souk.category') }}</div>
            <div class="flex flex-wrap gap-1.5" role="radiogroup" aria-labelledby="sb-cat">
              <button v-for="c in boot.categories" :key="c.key" role="radio" :aria-checked="f.category === c.key"
                      class="h-11 px-3.5 rounded-lg text-[13px] font-semibold ring-1 inline-flex items-center gap-1.5"
                      :class="f.category === c.key ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-700 ring-stone-300'"
                      @click="f.category = c.key">
                {{ isAr ? c.ar : c.fr }}
                <span v-if="c.key === lastCat && f.category !== c.key" class="text-[10px] font-semibold text-stone-400">· {{ t('souk.buy.lastPick') }}</span>
              </button>
            </div>
          </div>
          <div v-if="cat" class="flex items-center justify-between gap-2 bg-stone-50 rounded-lg px-3 py-2">
            <div class="min-w-0">
              <div class="text-[11.5px] font-semibold text-stone-700">{{ t('souk.brandOnSite') }}</div>
              <div class="text-[11px] text-stone-500">{{ t('souk.stallHint') }}</div>
            </div>
            <span class="text-[13px] font-bold text-stone-900 shrink-0">{{ cat.brand }}</span>
          </div>
        </section>
      </template>

      <!-- stall: both tabs -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
        <label for="sb-stall" class="text-[12px] font-semibold text-stone-600">{{ t('souk.stall') }}</label>
        <select id="sb-stall" v-model="f.stall" class="w-full h-12 rounded-lg ring-1 ring-stone-300 px-2 text-[14px] bg-white">
          <option value="">{{ t('souk.newStall') }}</option>
          <option v-for="s in boot.stalls" :key="s.name" :value="s.name">{{ s.label }}</option>
        </select>
        <div v-if="!f.stall" class="space-y-2 pt-1">
          <div class="space-y-1">
            <label for="sb-stall-name" class="text-[11.5px] font-semibold text-stone-600">{{ t('souk.buy.stallNameLbl') }}</label>
            <input id="sb-stall-name" v-model="f.newStall.name" dir="ltr" placeholder="AMINE DERB OMAR" autocomplete="off"
                   class="w-full h-12 rounded-lg ring-1 ring-stone-300 px-3 text-[14px] uppercase" />
          </div>
          <div class="space-y-1">
            <label for="sb-stall-phone" class="text-[11.5px] font-semibold text-stone-600">{{ t('souk.buy.stallPhoneLbl') }}</label>
            <input id="sb-stall-phone" v-model="f.newStall.phone" dir="ltr" inputmode="tel" type="tel" placeholder="06…"
                   class="w-full h-12 rounded-lg ring-1 ring-stone-300 px-3 text-[14px]" />
          </div>
        </div>
        <p v-if="tab === 'again'" class="text-[11px] text-stone-500">{{ t('souk.stallHint') }}</p>
      </section>

      <template v-if="tab === 'new'">
        <!-- do we already have it? -->
        <section v-if="similarShown.length" class="rounded-2xl bg-amber-50 ring-1 ring-amber-200 p-3 space-y-2" :aria-label="t('souk.similar')">
          <div class="flex items-center gap-2 px-1">
            <Icon name="alert-triangle" :size="15" class="text-amber-700" />
            <span class="text-[12.5px] font-bold text-amber-900">{{ tt('souk.buy.similarN', { n: similarShown.length }) }}</span>
          </div>
          <div class="space-y-1.5">
            <div v-for="r in similarShown" :key="r.kind + r.key" class="bg-white rounded-xl ring-1 ring-amber-100 p-2 flex items-center gap-2.5">
              <img v-if="r.image" :src="r.image" class="w-12 h-12 rounded-lg object-cover ring-1 ring-stone-200 shrink-0" alt="" loading="lazy" />
              <div v-else class="w-12 h-12 rounded-lg bg-stone-100 shrink-0 flex items-center justify-center"><Icon name="package" :size="18" class="text-stone-400" /></div>
              <div class="flex-1 min-w-0">
                <div class="text-[12.5px] font-semibold text-stone-900 truncate">{{ r.title }}</div>
                <div class="text-[11px] text-stone-500 truncate"><span class="font-mono" dir="ltr">{{ r.sku }}</span><span v-if="r.stall"> · {{ r.stall }}</span></div>
                <div class="text-[11px] truncate">
                  <span :class="r.stock > 0 ? 'text-emerald-700 font-semibold' : 'text-stone-500'">{{ r.stock > 0 ? tt('souk.buy.onShelf', { n: r.stock }) : t('souk.buy.noneOnShelf') }}</span>
                  <span class="text-stone-500"> · {{ r.lastSold ? tt('souk.buy.lastSold', { when: ago(r.lastSold) }) : t('souk.buy.neverSold') }}</span>
                  <span v-if="r.stage && r.stage !== 'live'" class="text-amber-800"> · {{ t('souk.st_' + r.stage) }}</span>
                </div>
              </div>
              <button class="shrink-0 h-11 px-3 rounded-lg ring-1 ring-[var(--accent-300)] text-[var(--accent-700)] text-[12px] font-bold" @click="startAgain(r)">{{ t('souk.buyAgain') }}</button>
            </div>
          </div>
          <button class="h-11 px-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] font-semibold text-amber-900" @click="dismissSimilar">{{ t('souk.buy.notIt') }}</button>
        </section>

        <!-- colours, sizes, quantities -->
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-4">
          <h2 class="text-[13.5px] font-bold text-stone-900">{{ t('souk.buy.colorsSizes') }}</h2>

          <div class="space-y-1.5">
            <div id="sb-colors" class="text-[12px] font-semibold text-stone-600">{{ t('souk.colors') }}</div>
            <div class="flex flex-wrap gap-1.5" role="group" aria-labelledby="sb-colors">
              <button v-for="c in boot.colors" :key="c.code" :aria-pressed="f.colors.includes(c.code)"
                      class="h-11 ps-2.5 pe-3 rounded-full text-[12.5px] font-semibold ring-1 inline-flex items-center gap-1.5"
                      :class="f.colors.includes(c.code) ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-700 ring-stone-300'"
                      @click="toggleColor(c.code)">
                <span class="w-3.5 h-3.5 rounded-full ring-1 ring-black/10 shrink-0" :style="{ background: swatch(c.code) }" />
                {{ colorName(c) }}
              </button>
            </div>
            <p class="text-[11px] text-stone-500">{{ t('souk.colorsHint') }}</p>
          </div>

          <div class="space-y-2">
            <div class="flex items-center justify-between gap-2">
              <span class="text-[12px] font-semibold text-stone-600">{{ t('souk.sizes') }}</span>
              <div class="flex items-center gap-1 flex-wrap justify-end">
                <span class="text-[10.5px] text-stone-400">{{ t('souk.buy.quick') }}</span>
                <button v-for="q in QUICK_SIZES" :key="q" class="h-9 min-w-[36px] px-2 rounded-md ring-1 ring-stone-300 text-[11.5px] font-bold font-mono text-stone-700 disabled:opacity-30"
                        :disabled="sizes.some((s) => effCode(s) === q)" @click="addSize(q)">{{ q }}</button>
              </div>
            </div>
            <div v-for="(s, i) in sizes" :key="s.id" class="grid grid-cols-[1fr_84px_44px] gap-2 items-end">
              <div class="space-y-1 min-w-0">
                <label :for="'sb-sz-' + s.id" class="text-[11px] font-semibold text-stone-500">{{ t('souk.buy.sizeDesc') }}</label>
                <input :id="'sb-sz-' + s.id" v-model="s.label" :placeholder="t('souk.buy.sizeDescPh')" autocomplete="off"
                       class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14px]" />
              </div>
              <div class="space-y-1">
                <label :for="'sb-sc-' + s.id" class="text-[11px] font-semibold text-stone-500 whitespace-nowrap">{{ t('souk.buy.sizeCode') }}</label>
                <input :id="'sb-sc-' + s.id" v-model="s.code" dir="ltr" maxlength="4" autocomplete="off"
                       :placeholder="sizeCode(s.label) || t('souk.buy.sizeCodePh')"
                       class="w-full h-11 rounded-lg ring-1 px-2 text-[14px] font-mono font-bold uppercase text-center"
                       :class="s.label.trim() && !effCode(s) ? 'ring-rose-400 bg-rose-50' : 'ring-stone-300'" />
              </div>
              <button class="h-11 w-11 rounded-lg ring-1 ring-stone-200 text-stone-500 inline-flex items-center justify-center"
                      :aria-label="t('souk.buy.removeSize')" @click="removeSize(i)"><Icon name="x" :size="16" /></button>
            </div>
            <button class="h-11 px-4 rounded-full ring-1 ring-stone-300 text-[12.5px] font-semibold text-stone-700" @click="addSize('')">{{ t('souk.buy.addSize') }}</button>
            <p class="text-[11px] text-stone-500 leading-snug">{{ t('souk.buy.sizesNote') }}</p>
          </div>

          <!-- quantities: one block per colour, one stepper per size -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[12px] font-semibold text-stone-600">{{ t('souk.qty') }}</span>
              <span class="text-[12px] font-bold tabular-nums text-stone-900">{{ units }} {{ t('souk.pcs') }}</span>
            </div>
            <div v-for="c in colorRows" :key="c" class="rounded-xl bg-stone-50 ring-1 ring-stone-200/70 p-2.5 space-y-1.5">
              <div class="flex items-center gap-1.5 text-[12.5px] font-semibold text-stone-800">
                <span v-if="c" class="w-3.5 h-3.5 rounded-full ring-1 ring-black/10" :style="{ background: swatch(c) }" />
                {{ c ? colorLabel(c) : t('souk.buy.noColor') }}
              </div>
              <div v-for="z in sizeCols" :key="z.id" class="flex items-center justify-between gap-2">
                <span class="min-w-0 text-[12.5px] text-stone-700 truncate">
                  <template v-if="z.label">{{ z.label.trim() }}<span v-if="effCode(z) !== z.label.trim()" class="ms-1.5 font-mono text-[10.5px] font-bold text-stone-500 bg-white ring-1 ring-stone-200 rounded px-1" dir="ltr">{{ effCode(z) || '?' }}</span></template>
                  <template v-else>{{ t('souk.buy.oneSize') }}</template>
                </span>
                <Stepper :model-value="qty[key(c, z.id)]" :id="'sb-q-' + c + '-' + z.id"
                         :label="tt('souk.buy.qtyOf', { v: [c ? colorLabel(c) : '', z.label].filter(Boolean).join(' · ') || t('souk.buy.oneSize') })"
                         :less="t('souk.buy.less')" :more="t('souk.buy.more')"
                         @update:model-value="(v) => (qty[key(c, z.id)] = v)" />
              </div>
            </div>
          </div>

          <div v-if="lines.length" class="space-y-1">
            <div class="text-[11.5px] font-semibold text-stone-600">{{ t('souk.skus') }}</div>
            <div class="flex flex-wrap gap-1.5" dir="ltr">
              <span v-for="l in lines" :key="l.sku" class="font-mono text-[11.5px] px-2 py-1 rounded-md"
                    :class="l.sku.length > boot.skuMax ? 'bg-rose-50 text-rose-700 ring-1 ring-rose-200' : 'bg-stone-100 text-stone-800'">{{ l.sku }}</span>
            </div>
            <p class="text-[11px] text-stone-500">{{ t('souk.skuHint') }}</p>
          </div>
        </section>

        <!-- prices per size -->
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
          <div class="flex items-center justify-between gap-2">
            <h2 class="text-[13.5px] font-bold text-stone-900">{{ t('souk.buy.priceTitle') }}</h2>
            <button v-if="sizeCols.length > 1" class="h-11 px-3 rounded-lg ring-1 ring-stone-300 text-[11.5px] font-semibold text-stone-700 disabled:opacity-40"
                    :disabled="!(Number(cost[sizeCols[0].id]) > 0)" @click="samePrices">{{ t('souk.buy.samePrices') }}</button>
          </div>
          <div v-for="z in sizeCols" :key="z.id" class="grid grid-cols-[1fr_1fr_52px] gap-2 items-end">
            <div class="space-y-1 min-w-0">
              <label :for="'sb-c-' + z.id" class="text-[11px] font-semibold text-stone-500 truncate block">{{ tt('souk.buy.costLbl', { z: zName(z) }) }}</label>
              <div class="relative">
                <input :id="'sb-c-' + z.id" v-model.number="cost[z.id]" type="number" inputmode="decimal" min="0" placeholder="0"
                       class="w-full h-12 rounded-lg ring-1 ring-stone-300 ps-3 pe-11 text-[15px] font-semibold tabular-nums" />
                <span class="absolute inset-y-0 end-3 flex items-center text-[11px] text-stone-400 pointer-events-none">MAD</span>
              </div>
            </div>
            <div class="space-y-1 min-w-0">
              <label :for="'sb-p-' + z.id" class="text-[11px] font-semibold text-stone-500 truncate block">{{ tt('souk.buy.sellLbl', { z: zName(z) }) }}</label>
              <div class="relative">
                <input :id="'sb-p-' + z.id" v-model.number="price[z.id]" type="number" inputmode="decimal" min="0" placeholder="0"
                       class="w-full h-12 rounded-lg ring-1 ps-3 pe-11 text-[15px] font-semibold tabular-nums"
                       :class="Number(price[z.id]) > 0 && Number(price[z.id]) <= Number(cost[z.id]) ? 'ring-rose-400 bg-rose-50' : 'ring-stone-300'" />
                <span class="absolute inset-y-0 end-3 flex items-center text-[11px] text-stone-400 pointer-events-none">MAD</span>
              </div>
            </div>
            <div class="h-12 flex flex-col items-end justify-center">
              <span class="text-[10px] text-stone-400">{{ t('souk.buy.margin') }}</span>
              <span class="text-[13px] font-bold tabular-nums" :class="margin(z.id) === null ? 'text-stone-300' : margin(z.id) < 40 ? 'text-rose-600' : 'text-emerald-700'">
                {{ margin(z.id) === null ? '—' : margin(z.id) + '%' }}
              </span>
            </div>
          </div>
          <p class="text-[11px] text-stone-500">{{ t('souk.marginHint') }}</p>
        </section>
      </template>

      <!-- BUY AGAIN -->
      <template v-else>
        <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-2">
          <label for="sb-find" class="text-[12px] font-semibold text-stone-600">{{ t('souk.findProduct') }}</label>
          <input id="sb-find" v-model="againQ" :placeholder="t('souk.findPh')" autocomplete="off"
                 class="w-full h-12 rounded-lg ring-1 ring-stone-300 px-3 text-[15px]" @input="lookAgain" />
          <div v-if="againRows.length && !again" class="space-y-1.5 pt-1">
            <button v-for="r in againRows" :key="r.kind + r.key"
                    class="w-full min-h-[56px] p-2 rounded-xl ring-1 ring-stone-200 flex items-center gap-2.5 text-start" @click="startAgain(r)">
              <img v-if="r.image" :src="r.image" class="w-12 h-12 rounded-lg object-cover ring-1 ring-stone-200 shrink-0" alt="" loading="lazy" />
              <div v-else class="w-12 h-12 rounded-lg bg-stone-100 shrink-0 flex items-center justify-center"><Icon name="package" :size="18" class="text-stone-400" /></div>
              <div class="flex-1 min-w-0">
                <div class="text-[12.5px] font-semibold text-stone-900 truncate">{{ r.title }}</div>
                <div class="text-[11px] text-stone-500 truncate"><span class="font-mono" dir="ltr">{{ r.sku }}</span><span v-if="r.stall"> · {{ r.stall }}</span></div>
                <div class="text-[11px] truncate">
                  <span :class="r.stock > 0 ? 'text-emerald-700 font-semibold' : 'text-stone-500'">{{ r.stock > 0 ? tt('souk.buy.onShelf', { n: r.stock }) : t('souk.buy.noneOnShelf') }}</span>
                  <span class="text-stone-500"> · {{ r.lastSold ? tt('souk.buy.lastSold', { when: ago(r.lastSold) }) : t('souk.buy.neverSold') }}</span>
                </div>
              </div>
              <Icon name="chevron-right" :size="16" class="text-stone-400 rtl:rotate-180 shrink-0" />
            </button>
          </div>
        </section>
        <section v-if="again" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
          <div class="flex items-center justify-between gap-2">
            <div class="text-[14px] font-bold text-stone-900 truncate">{{ again.title }}</div>
            <button class="h-11 px-3 rounded-lg text-[12.5px] font-semibold text-stone-500 hover:bg-stone-50" @click="again = null">{{ t('souk.change') }}</button>
          </div>
          <div v-for="r in again.rows" :key="r.itemCode" class="rounded-xl bg-stone-50 ring-1 ring-stone-200/70 p-2.5 space-y-2">
            <div class="min-w-0">
              <div class="font-mono text-[12.5px] font-bold text-stone-900" dir="ltr">{{ r.sku }}</div>
              <div class="text-[11px] text-stone-500 truncate">{{ r.label }}</div>
            </div>
            <div class="flex items-end justify-between gap-2">
              <div class="space-y-1">
                <span class="text-[11px] font-semibold text-stone-500">{{ t('souk.qtyShort') }}</span>
                <Stepper :model-value="r.qty" :id="'sb-aq-' + r.itemCode" :label="tt('souk.buy.qtyOf', { v: r.sku })"
                         :less="t('souk.buy.less')" :more="t('souk.buy.more')" @update:model-value="(v) => (r.qty = v)" />
              </div>
              <div class="space-y-1 w-[120px]">
                <label :for="'sb-ac-' + r.itemCode" class="text-[11px] font-semibold text-stone-500">{{ tt('souk.buy.costLbl', { z: '' }) }}</label>
                <div class="relative">
                  <input :id="'sb-ac-' + r.itemCode" v-model.number="r.cost" type="number" inputmode="decimal" min="0" placeholder="0"
                         class="w-full h-11 rounded-lg ring-1 ring-stone-300 bg-white ps-3 pe-10 text-[15px] font-semibold tabular-nums" />
                  <span class="absolute inset-y-0 end-2.5 flex items-center text-[10.5px] text-stone-400 pointer-events-none">MAD</span>
                </div>
              </div>
            </div>
          </div>
          <p v-if="again.lastStall" class="text-[11px] text-stone-500">{{ t('souk.lastStall').replace('{s}', again.lastStall) }}</p>
        </section>
      </template>

      <!-- receipt -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
        <div class="flex items-center gap-3">
          <div class="w-14 h-14 shrink-0 rounded-xl ring-1 ring-stone-300 bg-stone-50 flex items-center justify-center overflow-hidden">
            <img v-if="receiptPreview" :src="receiptPreview" class="w-full h-full object-cover" alt="" />
            <Icon v-else name="file-text" :size="20" class="text-stone-400" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-[12.5px] font-semibold text-stone-900">{{ t('souk.paidFromCustody') }}</div>
            <div class="text-[11px] text-stone-500 leading-snug">{{ t('souk.receiptHint') }}</div>
          </div>
        </div>
        <label class="w-full h-11 px-3 rounded-lg ring-1 ring-stone-300 text-[12.5px] font-semibold text-stone-700 inline-flex items-center justify-center gap-1.5 cursor-pointer">
          <Icon name="camera" :size="15" />{{ receiptPreview ? t('souk.buy.retake') : t('souk.buy.receiptTake') }}
          <input type="file" accept="image/*" capture="environment" class="hidden" @change="pickReceipt" />
        </label>
      </section>

      <div v-if="sendError" class="bg-rose-50 ring-1 ring-rose-200 rounded-2xl p-4 space-y-1" role="alert">
        <div class="text-[12.5px] font-bold text-rose-800">{{ t('souk.buy.refused') }}</div>
        <div class="text-[12.5px] text-rose-700 break-words" dir="auto">{{ sendError }}</div>
      </div>
    </template>

    <!-- footer -->
    <footer v-if="formMode" class="lp-footer bg-white border-t border-stone-200 shadow-[0_-8px_20px_rgba(0,0,0,0.05)] px-4 pt-3 pb-4">
      <div class="max-w-[520px] mx-auto space-y-2">
        <div class="flex items-center justify-between gap-2 text-[12.5px] tabular-nums">
          <span class="text-stone-600">{{ tt(tab === 'new' ? 'souk.buy.summary' : 'souk.buy.summaryAgain', { v: lineCount, n: units }) }}</span>
          <span class="font-extrabold text-[16px]" :class="total > left + 0.01 ? 'text-rose-600' : 'text-stone-900'">{{ fmt(total) }} MAD</span>
        </div>
        <p v-if="why" class="text-[11.5px] font-semibold text-amber-800 flex items-start gap-1.5" aria-live="polite">
          <Icon name="info" :size="13" class="mt-[2px] shrink-0" />{{ why }}
        </p>
        <button class="w-full h-12 rounded-xl bg-[var(--accent-600)] text-white text-[14.5px] font-bold disabled:opacity-40"
                :disabled="busy || !!why" @click="submit">
          {{ busy ? t('souk.sending') : tab === 'new' ? t('souk.confirmBuy') : t('souk.confirmRebuy') }}
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, defineComponent, h } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { shrink } from "@/lib/soukPhoto";
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
// holding the goods, needs targets, not a tiny number box.
const Stepper = defineComponent({
  props: { modelValue: { type: [Number, String, null], default: null }, id: String, label: String, less: String, more: String },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const val = () => Number(props.modelValue) || 0;
    const set = (n) => emit("update:modelValue", n > 0 ? Math.min(99999, Math.round(n)) : null);
    const btn = "w-11 h-11 rounded-lg bg-white ring-1 ring-stone-300 text-[20px] font-bold text-stone-700 inline-flex items-center justify-center active:bg-stone-100 disabled:opacity-30 select-none";
    return () => h("div", { class: "flex items-center gap-1 shrink-0" }, [
      h("button", { type: "button", class: btn, "aria-label": props.less, disabled: val() <= 0, onClick: () => set(val() - 1) }, "−"),
      h("input", {
        id: props.id, type: "number", inputmode: "numeric", min: 0, placeholder: "0", "aria-label": props.label,
        value: props.modelValue ?? "",
        class: "w-[60px] h-11 rounded-lg ring-1 ring-stone-300 bg-white text-center text-[16px] font-bold tabular-nums",
        onFocus: (e) => e.target.select(),
        onInput: (e) => { const v = e.target.value; set(v === "" ? 0 : parseInt(v, 10) || 0); },
      }),
      h("button", { type: "button", class: btn, "aria-label": props.more, onClick: () => set(val() + 1) }, "+"),
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

const blank = () => ({ stall: "", newStall: { name: "", phone: "" }, title: "", category: lastCat.value || "", colors: [] });
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
const formMode = computed(() => !!(boot.value?.trip && !done.value && !sent.value));

// ── colours ──────────────────────────────────────────────────────────────────
const SWATCH = {
  RED: "#b4412c", BLU: "#2b5fb4", GRN: "#2f7d4f", BLK: "#1c1917", WHT: "#ffffff", BEI: "#d9c7a7",
  BRN: "#7a4b2a", GRY: "#8a8784", PNK: "#e79bb4", YEL: "#e8c33a", ORG: "#e5792b", PUR: "#7b4fa8",
  NAV: "#1f2f57", GLD: "#c9a227", SLV: "#c4c4c4", NAT: "#cdb38b",
  MLT: "conic-gradient(#b4412c, #e8c33a, #2f7d4f, #2b5fb4, #7b4fa8, #b4412c)",
};
const swatch = (code) => SWATCH[code] || "#d6d3d1";
const colorName = (c) => (isAr.value ? `${c.ar} · ${c.fr}` : c.fr);
const colorLabel = (code) => {
  const x = boot.value?.colors.find((k) => k.code === code);
  return x ? colorName(x) : code;
};
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
const namedSizes = computed(() => sizes.value.filter((s) => (s.label || "").trim()));
const sizeCols = computed(() => (namedSizes.value.length ? namedSizes.value : [{ id: "", label: "", code: "" }]));
const zName = (z) => (z.label ? effCode(z) || z.label.trim() : "");
const colorRows = computed(() => (f.colors.length ? f.colors : [""]));
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
  if (!boot.value?.trip) return "";
  const W = (k, v) => tt("souk.buy.why." + k, v);
  if (tab.value === "again") {
    if (!again.value) return W("pick");
    if (!stallOk.value) return W("stall");
    if (!againLines.value.length) return W("qty");
    const r = againLines.value.find((x) => !(Number(x.cost) > 0));
    if (r) return W("cost", { z: r.sku });
  } else {
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
  if (total.value > left.value + 0.01) return W("over", { n: fmt(left.value) });
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
    try { similarRows.value = (await api("souk.similar", { q })).rows.slice(0, 4); } catch (_) { /* advisory only */ }
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
}
watch([f, sizes, qty, cost, price, tab, again, clientKey], saveDraft, { deep: true });
watch(() => f.category, (c) => { if (c) { lastCat.value = c; writeJSON(CAT_KEY, c); } });

function clearForm() {
  Object.assign(f, blank());
  f.newStall = { name: "", phone: "" };
  f.colors = [];
  sizes.value = [];
  for (const o of [qty, cost, price]) for (const k of Object.keys(o)) delete o[k];
  if (refPreview.value) URL.revokeObjectURL(refPreview.value);
  if (receiptPreview.value) URL.revokeObjectURL(receiptPreview.value);
  refFile.value = null; refPreview.value = "";
  receiptFile.value = null; receiptPreview.value = "";
  similarRows.value = []; similarHidden.value = [];
  again.value = null; againQ.value = ""; againRows.value = [];
  clientKey.value = "";
  sendError.value = "";
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
    po: r?.po || "", pi: r?.pi || "", left: r?.left ?? null,
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
    hasRef: isNew && !!refFile.value, hasReceipt: !!receiptFile.value,
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
          clientKey: clientKey.value,
        },
      };
    } else {
      job = {
        id: jobId, kind: "rebuy", label: summary.title, receipt,
        payload: {
          kind: again.value.kind, product: again.value.key, stall: f.stall, newStall: { ...f.newStall },
          lines: againLines.value.map((x) => ({ itemCode: x.itemCode, qty: Number(x.qty), cost: Number(x.cost) })),
          clientKey: clientKey.value,
        },
      };
    }
    setQueued(jobId, summary.total);
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
