<template>
  <!-- Souk receiving, at the door when the taxi arrives. Per variant: good,
       broken by WHERE it broke (at the stall → the stall owes it; in transport
       or in our warehouse → our loss, each in its own account), and the rest
       is short (the stall owes it). Good pieces go onto a real shelf (sellable,
       on Shopify) minus the studio samples; ours broken go to Defective Items.
       Counting is a deliberate act: "good" starts at 0 and every variant must
       be counted (a tap on a stepper, "All arrived" or "None came"). The count
       is kept on the phone (localStorage, per PO) until it posts. One piece of
       each size must be weighed — the server refuses good pieces of an
       unweighed item. One receiving per purchase, then the PO closes.
       Backend: souk.receive_queue / receive_boot / receive. -->
  <div class="max-w-[560px] mx-auto px-4 pt-4 pb-56 space-y-4">
    <header class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="text-[11.5px] font-semibold text-stone-500">{{ t('souk.recvKicker') }}</div>
        <h1 class="text-[18px] font-bold text-stone-900 truncate">{{ b ? (b.title || b.po) : t('souk.recvTitle') }}</h1>
        <div v-if="b" class="text-[11.5px] text-stone-500 font-mono truncate" dir="ltr">{{ b.po }} · {{ b.stall }} · {{ t('souk.tripNo').replace('{n}', b.trip) }}</div>
      </div>
      <router-link v-if="po" :to="{ name: 'SoukReceive' }"
                   class="shrink-0 h-11 px-3 rounded-xl bg-white ring-1 ring-stone-300 text-[13px] font-semibold inline-flex items-center gap-1">
        <Icon :name="isRTL ? 'chevron-right' : 'chevron-left'" :size="15" />{{ t('souk.recvList') }}
      </router-link>
    </header>

    <div v-if="loading" class="h-[280px] rounded-2xl bg-white ring-1 ring-stone-200/70 animate-pulse" />

    <!-- queue -->
    <template v-else-if="!po">
      <div v-if="!queue.length" class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-8 text-center text-[13px] text-stone-500">{{ t('souk.recvNone') }}</div>
      <router-link v-for="r in queue" :key="r.po" :to="{ name: 'SoukReceive', params: { po: r.po } }"
                   class="flex items-center gap-3 bg-white ring-1 ring-stone-200/70 rounded-2xl p-3 min-h-[72px] hover:ring-stone-400">
        <img v-if="r.image" :src="r.image" class="w-12 h-12 rounded-xl object-cover ring-1 ring-stone-200" alt="" />
        <div v-else class="w-12 h-12 rounded-xl bg-stone-100" />
        <div class="min-w-0 flex-1">
          <div class="text-[13px] font-semibold truncate">{{ r.title || r.po }}</div>
          <div class="text-[11.5px] text-stone-500 truncate">{{ r.stall }} · {{ r.units }} {{ t('souk.pcs') }} · {{ r.date }}</div>
          <span v-if="r.draft" class="mt-1 inline-flex h-5 px-1.5 rounded-md bg-amber-50 text-amber-800 text-[10.5px] font-bold items-center">{{ t('souk.recv.draftChip') }}</span>
        </div>
        <Icon :name="isRTL ? 'chevron-left' : 'chevron-right'" :size="16" class="text-stone-400" />
      </router-link>
    </template>

    <!-- done -->
    <section v-else-if="result" class="space-y-3">
      <div class="bg-emerald-50 ring-1 ring-emerald-200 rounded-2xl p-4 space-y-1">
        <div class="text-[15px] font-bold text-emerald-900">{{ t('souk.recvDone').replace('{n}', result.good) }}</div>
        <div class="text-[12.5px] text-emerald-800 font-mono" dir="ltr">{{ result.receipt }}<span v-if="result.debitNote"> · {{ result.debitNote }}</span></div>
        <div v-if="result.labels" class="text-[12.5px] text-emerald-800">{{ t('souk.labelsQueued').replace('{n}', result.labels) }}</div>
      </div>
      <div v-if="result.owed" class="bg-amber-50 ring-1 ring-amber-200 rounded-2xl p-4 text-[13px] text-amber-900">
        {{ t('souk.owedLine').replace('{n}', fmt(result.owed)).replace('{s}', b.stall) }}
      </div>
      <div v-for="(n, i) in result.notes" :key="i" class="bg-stone-50 ring-1 ring-stone-200 rounded-xl p-3 text-[12px] text-stone-700">{{ n }}</div>
      <div class="grid grid-cols-2 gap-2">
        <router-link :to="{ name: 'SoukReceive' }" class="h-12 rounded-xl bg-white ring-1 ring-stone-300 text-[13px] font-bold inline-flex items-center justify-center">{{ t('souk.recvNext') }}</router-link>
        <router-link v-if="result.product" :to="{ name: 'SoukProduct', params: { name: result.product } }"
                     class="h-12 rounded-xl bg-[var(--accent-600)] text-white text-[13px] font-bold inline-flex items-center justify-center">{{ t('souk.toProduct') }}</router-link>
      </div>
    </section>

    <div v-else-if="b && b.done" class="bg-stone-50 ring-1 ring-stone-200 rounded-2xl p-5 text-[13px] text-stone-700">
      {{ t('souk.recvAlready').replace('{pr}', b.done) }}
    </div>

    <template v-else-if="b">
      <!-- the count was kept on this phone -->
      <div v-if="draftAt" class="flex items-center justify-between gap-3 bg-amber-50 ring-1 ring-amber-200 rounded-2xl px-3 py-2">
        <span class="text-[12px] text-amber-900">{{ t('souk.recv.draftRestored').replace('{t}', draftAt) }}</span>
        <button class="shrink-0 h-11 px-3 rounded-xl bg-white ring-1 ring-amber-300 text-[12.5px] font-bold text-amber-900" @click="resetDraft">{{ t('souk.recv.draftReset') }}</button>
      </div>

      <!-- the buyer's reference photo -->
      <section class="flex gap-3 items-center bg-white ring-1 ring-stone-200/70 rounded-2xl p-3">
        <button v-if="b.image" class="w-16 h-16 shrink-0 rounded-xl overflow-hidden ring-1 ring-stone-200" @click="refBig = true" :aria-label="t('souk.recv.refTitle')">
          <img :src="b.image" class="w-full h-full object-cover" alt="" />
        </button>
        <div v-else class="w-16 h-16 shrink-0 rounded-xl bg-stone-100 flex items-center justify-center"><Icon name="image" :size="20" class="text-stone-400" /></div>
        <div class="min-w-0">
          <div class="text-[12.5px] font-semibold text-stone-900">{{ t('souk.recv.refTitle') }}</div>
          <div class="text-[11.5px] text-stone-600 leading-snug">{{ t('souk.recv.refHint') }}</div>
        </div>
      </section>

      <!-- good / broken / short, and who pays -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-3 space-y-2">
        <div class="text-[12.5px] font-bold text-stone-900">{{ t('souk.recv.howTitle') }}</div>
        <div class="grid grid-cols-[auto_1fr] gap-x-2.5 gap-y-1.5 text-[11.5px] leading-snug text-stone-600">
          <span class="h-5 px-1.5 rounded-md bg-emerald-50 text-emerald-800 font-bold inline-flex items-center">{{ t('souk.good') }}</span>
          <span>{{ t('souk.recv.howGood') }}</span>
          <span class="h-5 px-1.5 rounded-md bg-rose-50 text-rose-700 font-bold inline-flex items-center">{{ t('souk.brokenShort') }}</span>
          <span>{{ t('souk.recv.howBroken') }}</span>
          <span class="h-5 px-1.5 rounded-md bg-amber-50 text-amber-800 font-bold inline-flex items-center">{{ t('souk.short') }}</span>
          <span>{{ t('souk.recv.howShort') }}</span>
        </div>
      </section>

      <!-- per variant -->
      <section v-for="l in b.lines" :key="l.itemCode" class="bg-white ring-1 rounded-2xl p-4 space-y-3"
               :class="over(l) ? 'ring-rose-300' : touched[l.itemCode] && (shortOf(l) || brokenOf(l)) ? 'ring-amber-300' : 'ring-stone-200/70'">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <div class="font-mono text-[14px] font-bold truncate" dir="ltr">{{ l.sku }}</div>
            <div class="text-[11.5px] text-stone-500 truncate">{{ l.label }}</div>
          </div>
          <div class="text-end shrink-0">
            <div class="text-[11px] text-stone-500">{{ t('souk.bought') }}</div>
            <div class="text-[18px] font-extrabold tabular-nums leading-none">{{ pending(l) }}</div>
          </div>
        </div>
        <div v-if="!touched[l.itemCode]" class="text-[11px] font-semibold text-stone-500">{{ t('souk.recv.notCounted') }}</div>

        <div class="grid grid-cols-[1fr_auto] gap-2 items-center">
          <label class="text-[12.5px] font-semibold text-emerald-800">{{ t('souk.good') }}</label>
          <Stepper :model-value="c[l.itemCode].good" :max="Math.max(0, pending(l) - brokenOf(l))" tone="good" :label="t('souk.good') + ' ' + l.sku"
                   @update:model-value="(v) => setCount(l, 'good', v)" />
        </div>
        <div class="grid grid-cols-[1fr_auto] gap-2">
          <button class="h-11 rounded-xl text-[12.5px] font-bold ring-1 inline-flex items-center justify-center gap-1.5"
                  :class="allIn(l) ? 'bg-emerald-600 text-white ring-emerald-600' : 'bg-emerald-50 text-emerald-800 ring-emerald-200'"
                  @click="allArrived(l)">
            <Icon name="check" :size="15" />{{ t('souk.recv.allArrived').replace('{n}', Math.max(0, pending(l) - brokenOf(l))) }}
          </button>
          <button class="h-11 px-3 rounded-xl text-[12.5px] font-semibold ring-1"
                  :class="touched[l.itemCode] && !arrived(l) ? 'bg-amber-100 text-amber-900 ring-amber-300' : 'bg-white text-stone-600 ring-stone-300'"
                  @click="noneCame(l)">{{ t('souk.recv.noneCame') }}</button>
        </div>

        <button class="w-full h-11 px-3 rounded-xl ring-1 text-[12.5px] font-semibold inline-flex items-center justify-between gap-2"
                :class="brokenOf(l) ? 'bg-rose-50 ring-rose-200 text-rose-700' : 'bg-white ring-stone-300 text-stone-600'"
                :aria-expanded="!!(open[l.itemCode] || brokenOf(l))"
                @click="open[l.itemCode] = !open[l.itemCode]">
          <span class="inline-flex items-center gap-1.5"><Icon name="alert-triangle" :size="15" />{{ t('souk.recv.brokenBtn') }}</span>
          <span class="inline-flex items-center gap-1.5">
            <b v-if="brokenOf(l)" class="tabular-nums">{{ brokenOf(l) }}</b>
            <Icon :name="open[l.itemCode] || brokenOf(l) ? 'chevron-up' : 'chevron-down'" :size="15" />
          </span>
        </button>
        <div v-if="open[l.itemCode] || brokenOf(l)" class="rounded-xl bg-rose-50/60 ring-1 ring-rose-100 p-3 space-y-2.5">
          <div class="text-[11.5px] font-bold text-rose-800">{{ t('souk.recv.whereQ') }}</div>
          <div v-for="w in WHERE" :key="w" class="grid grid-cols-[1fr_auto] gap-2 items-center">
            <div class="min-w-0">
              <div class="text-[12.5px] font-semibold text-stone-800">{{ t('souk.br_' + w) }}</div>
              <div class="text-[10.5px] text-stone-500 leading-snug">{{ t('souk.brh_' + w) }}</div>
            </div>
            <Stepper :model-value="c[l.itemCode][w]" :max="pending(l)" tone="bad" :label="t('souk.br_' + w) + ' ' + l.sku"
                     @update:model-value="(v) => setCount(l, w, v)" />
          </div>
        </div>

        <div v-if="touched[l.itemCode] || over(l)" class="flex items-center justify-between gap-2 text-[12px] rounded-lg px-3 py-2"
             :class="over(l) ? 'bg-rose-100 text-rose-800' : shortOf(l) ? 'bg-amber-50 text-amber-900' : 'bg-stone-50 text-stone-600'">
          <span v-if="over(l)">{{ t('souk.tooMany') }}</span>
          <span v-else-if="shortOf(l)" class="font-semibold tabular-nums">{{ t('souk.recv.shortValue').replace('{n}', shortOf(l)).replace('{m}', fmt(shortOf(l) * l.rate)) }}</span>
          <span v-else>{{ t('souk.recv.shortNone') }}</span>
          <span v-if="!over(l) && Number(c[l.itemCode].supplier)" class="text-[11px] tabular-nums">+ {{ c[l.itemCode].supplier }} {{ t('souk.br_supplier') }}</span>
        </div>
      </section>

      <!-- broken photo: uploads at once, its failure shows and can be retried -->
      <section v-if="anyBroken || brokenState" class="bg-white ring-1 rounded-2xl p-4 space-y-2"
               :class="brokenState === 'err' ? 'ring-rose-300' : 'ring-stone-200/70'">
        <div class="flex items-center gap-3">
          <label class="w-16 h-16 shrink-0 rounded-xl ring-1 ring-stone-300 bg-stone-50 flex items-center justify-center overflow-hidden cursor-pointer relative">
            <img v-if="brokenPreview || brokenUrl" :src="brokenPreview || brokenUrl" class="w-full h-full object-cover" alt="" />
            <Icon v-else name="camera" :size="22" class="text-stone-400" />
            <span v-if="brokenState === 'up'" class="absolute inset-0 bg-white/70 flex items-center justify-center">
              <span class="w-6 h-6 rounded-full border-2 border-stone-300 border-t-stone-700 animate-spin" />
            </span>
            <input type="file" accept="image/*" capture="environment" class="hidden" :disabled="brokenState === 'up'" @change="pickBroken" />
          </label>
          <div class="min-w-0 flex-1 space-y-0.5">
            <div class="text-[12.5px] font-semibold text-stone-900">{{ brokenState ? t('souk.recv.photoRetake') : t('souk.recv.photoTake') }}</div>
            <div class="text-[11.5px] text-stone-600 leading-snug">{{ t('souk.brokenPhoto') }}</div>
            <div v-if="brokenState === 'up'" class="text-[11.5px] text-stone-500">{{ t('souk.recv.photoUploading') }}</div>
            <div v-else-if="brokenState === 'ok'" class="text-[11.5px] font-semibold text-emerald-700 inline-flex items-center gap-1"><Icon name="check" :size="13" />{{ t('souk.recv.photoSaved') }}</div>
          </div>
        </div>
        <div v-if="brokenState === 'err'" class="flex items-center justify-between gap-2 rounded-xl bg-rose-50 ring-1 ring-rose-200 px-3 py-2">
          <span class="text-[12px] text-rose-800 min-w-0 break-words">{{ t('souk.recv.photoFailed').replace('{e}', brokenErr) }}</span>
          <button class="shrink-0 h-11 px-3 rounded-xl bg-white ring-1 ring-rose-300 text-[12.5px] font-bold text-rose-700 inline-flex items-center gap-1.5" @click="sendBroken">
            <Icon name="refresh-cw" :size="14" />{{ t('souk.recv.photoRetry') }}
          </button>
        </div>
      </section>

      <!-- weight: one piece of each size, required for good pieces -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
        <div class="flex items-baseline justify-between gap-2">
          <h2 class="text-[13.5px] font-bold text-stone-900">{{ t('souk.recv.weightTitle') }}</h2>
          <span v-if="groups.some((g) => !g.allKnown)" class="text-[11px] font-bold text-rose-700">{{ t('souk.recv.required') }}</span>
        </div>
        <p class="text-[11.5px] text-stone-600 leading-snug">{{ t('souk.recv.weightWhy') }}</p>
        <div class="grid grid-cols-2 gap-2.5">
          <div v-for="g in groups" :key="g.key" class="min-w-0 space-y-1">
            <label :for="'w-' + g.key" class="block text-[12px] font-semibold text-stone-700 truncate">
              {{ g.size ? t('souk.recv.sizeOf').replace('{s}', g.size) : g.label }}
            </label>
            <div class="relative">
              <input :id="'w-' + g.key" v-model="weights[g.key]" type="number" inputmode="decimal" min="1" max="100000"
                     :placeholder="g.allKnown ? knownText(g) : 'g'"
                     class="w-full h-11 rounded-lg ring-1 ps-3 pe-8 text-[16px] tabular-nums bg-white"
                     :class="weightMissing(g) || weightBadOf(g) ? 'ring-rose-400 bg-rose-50/40' : 'ring-stone-300'" />
              <span class="absolute inset-y-0 end-3 flex items-center text-[12px] text-stone-400 pointer-events-none">g</span>
            </div>
            <div class="text-[10.5px] truncate" :class="g.allKnown ? 'text-emerald-700' : 'text-stone-500'" dir="auto">
              <template v-if="g.allKnown">{{ t('souk.recv.weightKnown') }} · </template><span dir="ltr" class="font-mono">{{ g.lines.map((x) => x.sku).join(' · ') }}</span>
            </div>
          </div>
        </div>
        <p v-if="groups.some((g) => g.size && g.lines.length > 1)" class="text-[11px] text-stone-500">{{ t('souk.recv.weightSame') }}</p>
      </section>

      <!-- studio sample + shelf -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4 space-y-3">
        <template v-if="b.studioSamples">
          <h2 class="text-[13.5px] font-bold text-stone-900">{{ t('souk.recv.studioTitle') }}</h2>
          <label class="flex items-start gap-3 min-h-[44px] cursor-pointer">
            <input v-model="studioOn" type="checkbox" class="mt-1 w-5 h-5 shrink-0 rounded accent-[var(--accent-600)]" />
            <span class="text-[12.5px] text-stone-800 leading-snug">
              {{ (!studioManual && plannedStudio === perColor.length ? t('souk.recv.studioPlan') + ' ' : '')
                + t('souk.recv.studioOn').replace('{n}', studioOn ? (totalStudio || plannedStudio) : 0) }}
            </span>
          </label>
          <p class="text-[11px] text-stone-500 leading-snug">{{ t('souk.recv.studioHint') }}</p>
          <template v-if="studioOn">
            <div v-if="!totalGood" class="text-[11.5px] text-amber-800">{{ t('souk.recv.studioWaits') }}</div>
            <div v-else-if="!studioEdit" class="flex items-center justify-between gap-2">
              <div class="flex flex-wrap gap-1.5 min-w-0">
                <span v-for="(n, code) in effStudio" :key="code" class="h-6 px-2 rounded-md bg-stone-100 text-[11.5px] font-mono inline-flex items-center" dir="ltr">{{ skuOf(code) }} ×{{ n }}</span>
              </div>
              <button class="shrink-0 h-11 px-3 rounded-xl ring-1 ring-stone-300 text-[12.5px] font-semibold" @click="studioEdit = true">{{ t('souk.recv.studioChange') }}</button>
            </div>
            <div v-else class="rounded-xl bg-stone-50 ring-1 ring-stone-200 p-3 space-y-2">
              <div v-for="l in b.lines" :key="l.itemCode" class="grid grid-cols-[1fr_auto] gap-2 items-center"
                   :class="good(l) || effStudio[l.itemCode] ? '' : 'opacity-50'">
                <div class="min-w-0">
                  <div class="font-mono text-[12.5px] font-bold truncate" dir="ltr">{{ l.sku }}</div>
                  <div class="text-[10.5px] text-stone-500 truncate">{{ t('souk.good') }} {{ good(l) }}</div>
                </div>
                <Stepper :model-value="effStudio[l.itemCode] || 0" :max="good(l)" tone="good" :label="t('souk.toStudio') + ' ' + l.sku"
                         @update:model-value="(v) => setStudio(l, v)" />
              </div>
              <div class="flex items-center justify-between gap-2 pt-1">
                <button v-if="studioManual" class="h-11 px-2 text-[12px] font-semibold text-stone-600 underline" @click="studioManual = null">{{ t('souk.recv.studioReset') }}</button>
                <span v-else />
                <button class="h-11 px-4 rounded-xl bg-stone-900 text-white text-[12.5px] font-bold" @click="studioEdit = false">{{ t('souk.recv.studioDone') }}</button>
              </div>
            </div>
          </template>
          <div class="border-t border-stone-100" />
        </template>

        <div class="space-y-1.5">
          <label for="souk-shelf" class="text-[12px] font-semibold text-stone-700">{{ t('souk.shelf') }}</label>
          <select id="souk-shelf" v-model="target" class="w-full h-11 rounded-lg ring-1 px-2 text-[15px] bg-white"
                  :class="needsShelf && !target ? 'ring-amber-400' : 'ring-stone-300'">
            <option value="">—</option>
            <option v-for="w in b.shelves" :key="w" :value="w">{{ shortWh(w) }}</option>
          </select>
          <p class="text-[11px] text-stone-500 leading-snug">{{ t('souk.shelfHint') }}</p>
        </div>
        <input v-model="note" :placeholder="t('souk.note')" class="w-full h-11 rounded-lg ring-1 ring-stone-300 px-3 text-[14px]" />
      </section>

      <!-- labels -->
      <section class="bg-white ring-1 ring-stone-200/70 rounded-2xl p-4">
        <label class="flex items-center gap-3 min-h-[44px] cursor-pointer">
          <div aria-hidden="true" class="w-[74px] h-11 shrink-0 rounded-md ring-1 ring-stone-300 bg-white flex flex-col items-center justify-center gap-0.5">
            <div class="w-[58px] h-[18px] bg-[repeating-linear-gradient(90deg,#1c1917_0_1px,#fff_1px_3px,#1c1917_3px_5px,#fff_5px_6px)]" />
            <span class="font-mono text-[6.5px] text-stone-800" dir="ltr">{{ b.lines[0] && b.lines[0].sku }}</span>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-[12.5px] font-semibold text-stone-900">{{ t('souk.recv.labelsTitle').replace('{n}', totalGood) }}</div>
            <div class="text-[11.5px] text-stone-500">{{ t('souk.recv.labelsStation') }}</div>
          </div>
          <input v-model="labels" type="checkbox" class="w-6 h-6 shrink-0 rounded accent-[var(--accent-600)]" />
        </label>
      </section>

      <!-- money summary -->
      <section v-if="owed > 0" class="bg-amber-50 ring-1 ring-amber-200 rounded-2xl p-4 text-[12.5px] text-amber-900 space-y-1.5">
        <div class="font-bold flex items-center gap-1.5"><Icon name="alert-triangle" :size="15" />{{ t('souk.owedLine').replace('{n}', fmt(owed)).replace('{s}', b.stall) }}</div>
        <div v-for="o in owedLines" :key="o.itemCode" class="text-[11.5px] tabular-nums" dir="ltr" :class="isRTL ? 'text-end' : ''">
          {{ t('souk.recv.owedBy').replace('{sku}', o.sku).replace('{n}', o.qty).replace('{r}', fmt(o.rate)).replace('{m}', fmt(o.qty * o.rate)) }}
        </div>
        <div class="text-[11.5px]">{{ b.hasInvoice ? t('souk.owedDebit') : t('souk.owedNoBooks') }}</div>
      </section>
      <section v-if="ourBroken.transport && !b.lossAccounts.transport || ourBroken.warehouse && !b.lossAccounts.warehouse"
               class="bg-stone-50 ring-1 ring-stone-200 rounded-2xl p-3 text-[12px] text-stone-600">
        {{ t('souk.lossWaits') }}
      </section>
    </template>

    <footer v-if="b && !b.done && !result && !loading && po" class="lp-footer bg-white border-t border-stone-200 px-4 pt-3 pb-4 shadow-[0_-8px_20px_rgba(0,0,0,0.05)]">
      <div class="max-w-[560px] mx-auto space-y-2">
        <div class="flex items-center justify-between gap-2 text-[12px] text-stone-600 tabular-nums">
          <span>{{ t('souk.good') }} <b class="text-stone-900">{{ totalGood }}</b></span>
          <span>{{ t('souk.brokenShort') }} <b class="text-rose-700">{{ totalBroken }}</b></span>
          <span>{{ t('souk.short') }} <b class="text-amber-800">{{ totalShort }}</b></span>
          <span v-if="owed > 0"><b class="text-amber-800">{{ fmt(owed) }}</b> MAD</span>
        </div>
        <div v-if="blocker && !busy" class="text-[11.5px] font-semibold text-amber-800 text-center leading-snug">{{ blocker }}</div>
        <button class="w-full h-[52px] rounded-xl bg-[var(--accent-600)] text-white text-[15px] font-bold inline-flex items-center justify-center gap-2 disabled:bg-stone-200 disabled:text-stone-500"
                :disabled="busy || !!blocker" @click="post">
          <Icon v-if="!busy && !nothingCame && labels && totalGood" name="printer" :size="18" />
          {{ busy ? t('souk.sending') : nothingCame ? t('souk.allShort')
            : labels && totalGood ? t('souk.recv.confirmPrint').replace('{n}', totalGood) : t('souk.recv.confirm') }}
        </button>
      </div>
    </footer>

    <!-- the reference photo, big -->
    <div v-if="refBig && b && b.image" class="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4" @click="refBig = false">
      <img :src="b.image" class="max-w-full max-h-full rounded-xl object-contain" alt="" />
      <button class="absolute top-3 end-3 w-11 h-11 rounded-full bg-white/90 text-stone-900 flex items-center justify-center" :aria-label="t('souk.recv.close')">
        <Icon name="x" :size="18" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, defineComponent, h } from "vue";
import { useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { uploadPhoto } from "@/lib/soukPhoto";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

// − n + with big targets: counted with a thumb, often with gloves on.
const Stepper = defineComponent({
  props: { modelValue: { type: Number, default: 0 }, max: { type: Number, default: 9999 }, tone: String, label: String },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const clamp = (v) => Math.max(0, Math.min(props.max, Math.round(Number(v) || 0)));
    const set = (v) => emit("update:modelValue", clamp(v));
    return () => h("div", { class: "flex items-center gap-1.5" }, [
      h("button", { type: "button", class: "w-11 h-11 rounded-xl ring-1 ring-stone-300 bg-white text-[18px] font-bold", "aria-label": "−",
        onClick: () => set((props.modelValue || 0) - 1) }, "−"),
      h("input", {
        type: "number", inputmode: "numeric", value: props.modelValue, "aria-label": props.label,
        class: "w-[68px] h-11 rounded-xl ring-1 ring-stone-300 bg-white text-center text-[17px] font-extrabold tabular-nums "
          + (props.tone === "good" ? "text-emerald-800" : "text-rose-700"),
        // DataWedge / a keypad commits text: react to the value, never to Enter.
        onInput: (e) => {
          const v = clamp(e.target.value);
          set(v);
          if (e.target.value !== "" && String(v) !== e.target.value) e.target.value = String(v);
        },
      }),
      h("button", { type: "button", class: "w-11 h-11 rounded-xl ring-1 ring-stone-300 bg-white text-[18px] font-bold", "aria-label": "+",
        onClick: () => set((props.modelValue || 0) + 1) }, "+"),
    ]);
  },
});

const WHERE = ["supplier", "transport", "warehouse"];
const DRAFT_PREFIX = "lp.souk.recv.";
const { t, isRTL, locale } = useI18n();
const { warn } = useToast();
const route = useRoute();
const po = computed(() => route.params.po || "");
const loading = ref(true);
const busy = ref(false);
const queue = ref([]);
const b = ref(null);
const c = reactive({});
const touched = reactive({});
const open = reactive({});
const weights = reactive({});
const studioOn = ref(true);
const studioManual = ref(null);
const studioEdit = ref(false);
const target = ref("");
const labels = ref(true);
const note = ref("");
const result = ref(null);
const brokenFile = ref(null);
const brokenPreview = ref("");
const brokenUrl = ref("");
const brokenState = ref(""); // "" | up | ok | err
const brokenErr = ref("");
const draftAt = ref("");
const refBig = ref(false);
let ready = false;
let lastSaved = "";

// --- drafts: the count lives on the phone until it posts ------------------
function readDraft(name) {
  try {
    const raw = localStorage.getItem(DRAFT_PREFIX + name);
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}
function writeDraft(name, data) {
  try { localStorage.setItem(DRAFT_PREFIX + name, JSON.stringify(data)); } catch (_) { /* private mode / full */ }
}
function clearDraft(name) {
  try { localStorage.removeItem(DRAFT_PREFIX + name); } catch (_) { /* nothing kept */ }
}

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const shortWh = (w) => (w || "").replace(/ - JM$/, "");
const pending = (l) => Math.max(0, Math.round(l.ordered - l.already));
const good = (l) => Number(c[l.itemCode]?.good) || 0;
const brokenOf = (l) => WHERE.reduce((s, w) => s + (Number(c[l.itemCode]?.[w]) || 0), 0);
const arrived = (l) => good(l) + brokenOf(l);
const over = (l) => arrived(l) > pending(l);
const shortOf = (l) => Math.max(0, pending(l) - arrived(l));
const allIn = (l) => touched[l.itemCode] && pending(l) > 0 && good(l) === pending(l) - brokenOf(l);
const lines = computed(() => b.value?.lines || []);
const lineBy = computed(() => Object.fromEntries(lines.value.map((l) => [l.itemCode, l])));
const skuOf = (code) => lineBy.value[code]?.sku || code;
const totalGood = computed(() => lines.value.reduce((s, l) => s + good(l), 0));
const totalBroken = computed(() => lines.value.reduce((s, l) => s + brokenOf(l), 0));
// Short and owed only count what has been counted: an untouched variant is
// not "short", it is not counted yet.
const totalShort = computed(() => lines.value.reduce((s, l) => s + (touched[l.itemCode] ? shortOf(l) : 0), 0));
const anyBroken = computed(() => totalBroken.value > 0);
const ourBroken = computed(() => ({
  transport: lines.value.some((l) => Number(c[l.itemCode]?.transport) > 0),
  warehouse: lines.value.some((l) => Number(c[l.itemCode]?.warehouse) > 0),
}));
// The stall owes what never came and what was broken at its stall.
const owedLines = computed(() => lines.value
  .map((l) => ({ itemCode: l.itemCode, sku: l.sku, rate: l.rate, qty: shortOf(l) + (Number(c[l.itemCode]?.supplier) || 0) }))
  .filter((o) => o.qty > 0 && touched[o.itemCode] && !over(lineBy.value[o.itemCode])));
const owed = computed(() => owedLines.value.reduce((s, o) => s + o.qty * o.rate, 0));
const allCounted = computed(() => lines.value.every((l) => touched[l.itemCode]));
const nothingCame = computed(() => lines.value.length > 0 && allCounted.value && totalGood.value + totalBroken.value === 0);
const needsShelf = computed(() => lines.value.some((l) => {
  const x = c[l.itemCode] || {};
  return (Number(x.good) || 0) + (Number(x.transport) || 0) + (Number(x.warehouse) || 0) > 0;
}));

function setCount(l, key, v) {
  c[l.itemCode][key] = v;
  touched[l.itemCode] = true;
  // Broken pieces come out of the good count, never on top of it.
  if (key !== "good" && arrived(l) > pending(l)) c[l.itemCode].good = Math.max(0, pending(l) - brokenOf(l));
}
function allArrived(l) {
  c[l.itemCode].good = Math.max(0, pending(l) - brokenOf(l));
  touched[l.itemCode] = true;
}
function noneCame(l) {
  for (const k of ["good", ...WHERE]) c[l.itemCode][k] = 0;
  touched[l.itemCode] = true;
}

// --- weight: one piece per size (the artboard), sent on every line of it ---
// The size is the label after the colour ("Rouge · L"); without a colour, or
// when the label cannot be split, each line is its own group.
const sizeOf = (l) => {
  if (l.size) return l.size;           // receive_boot sends the size itself
  if (!l.color) return "";
  const p = (l.label || "").split(" · ");
  return p.length >= 2 ? p.slice(1).join(" · ") : "";
};
const groups = computed(() => {
  const out = [];
  const by = {};
  for (const l of lines.value) {
    const s = sizeOf(l);
    const key = s ? "s:" + s : "i:" + l.itemCode;
    if (!by[key]) {
      by[key] = { key, size: s, label: l.label || l.sku, lines: [] };
      out.push(by[key]);
    }
    by[key].lines.push(l);
  }
  for (const g of out) {
    const known = g.lines.map((l) => l.grams).filter(Boolean);
    g.allKnown = known.length === g.lines.length;
    g.initial = g.allKnown && new Set(known).size === 1 ? known[0] : null;
  }
  return out;
});
const groupOf = (l) => groups.value.find((g) => g.lines.includes(l));
const gramsOk = (v) => v !== "" && v != null && Number(v) >= 1 && Number(v) <= 100000;
const entered = (g) => weights[g.key] !== "" && weights[g.key] != null;
const weightBadOf = (g) => entered(g) && !gramsOk(weights[g.key]);
const weightMissing = (g) => !gramsOk(weights[g.key]) && g.lines.some((l) => good(l) > 0 && !l.grams);
const knownText = (g) => [...new Set(g.lines.map((l) => l.grams))].join(" / ");
const gramsFor = (l) => {
  const g = groupOf(l);
  return g && gramsOk(weights[g.key]) ? Number(weights[g.key]) : (l.grams || null);
};

// --- studio: one sample of each colour (the first size of it, from the
// server), the rest of studioSamples on the first colour. Until changed by
// hand it follows the count: a size with no good piece hands its sample to
// another size of the same colour.
const perColor = computed(() => {
  const x = b.value?.studioPerColor;
  if (x && x.length) return x;
  return b.value?.studioDefault ? [b.value.studioDefault] : [];
});
const plan = computed(() => {
  const p = {};
  const n = Number(b.value?.studioSamples) || 0;
  if (!n || !perColor.value.length) return p;
  // One per colour (Ahmed's design) — the studio shoots every colour once.
  for (const code of perColor.value) p[code] = 1;
  return p;
});
const plannedStudio = computed(() => Object.values(plan.value).reduce((s, n) => s + n, 0));
const autoStudio = computed(() => {
  const out = {};
  for (const [code, n] of Object.entries(plan.value)) {
    const l0 = lineBy.value[code];
    if (!l0) continue;
    let left = n;
    for (const l of [l0, ...lines.value.filter((x) => x.color === l0.color && x.itemCode !== code)]) {
      const take = Math.min(left, Math.max(0, good(l) - (out[l.itemCode] || 0)));
      if (take > 0) {
        out[l.itemCode] = (out[l.itemCode] || 0) + take;
        left -= take;
      }
      if (!left) break;
    }
  }
  return out;
});
const effStudio = computed(() => {
  if (!studioOn.value || !b.value?.studioSamples) return {};
  const src = studioManual.value || autoStudio.value;
  return Object.fromEntries(Object.entries(src).filter(([, n]) => Number(n) > 0));
});
const totalStudio = computed(() => Object.values(effStudio.value).reduce((s, n) => s + Number(n), 0));
const studioBad = computed(() => lines.value.some((l) => (Number(effStudio.value[l.itemCode]) || 0) > good(l)));
function setStudio(l, v) {
  if (!studioManual.value) studioManual.value = { ...autoStudio.value };
  studioManual.value[l.itemCode] = v;
}

// --- what still blocks the post (one reason, the first) -------------------
const blocker = computed(() => {
  if (!lines.value.length) return " ";
  const left = lines.value.filter((l) => !touched[l.itemCode]).length;
  if (left) return t("souk.recv.whyCount").replace("{n}", left);
  if (lines.value.some(over)) return t("souk.recv.whyOver");
  const miss = groups.value.filter(weightMissing);
  if (miss.length) {
    return t("souk.recv.whyWeight").replace("{list}", miss.map((g) => (g.size || g.lines[0].sku)).join(", "));
  }
  if (groups.value.some(weightBadOf)) return t("souk.recv.whyWeightBad");
  if (studioBad.value) return t("souk.recv.whyStudio");
  if (needsShelf.value && !target.value) return t("souk.recv.whyShelf");
  if (brokenState.value === "up") return t("souk.recv.whyPhoto");
  return "";
});

// --- broken photo ------------------------------------------------------------
function pickBroken(e) {
  const f = e.target.files?.[0];
  e.target.value = "";
  if (!f) return;
  brokenFile.value = f;
  if (brokenPreview.value) URL.revokeObjectURL(brokenPreview.value);
  brokenPreview.value = URL.createObjectURL(f);
  sendBroken();
}
async function sendBroken() {
  if (!brokenFile.value || !b.value) return;
  brokenState.value = "up";
  brokenErr.value = "";
  try {
    const r = await uploadPhoto("broken", b.value.po, brokenFile.value);
    brokenUrl.value = (r && r.url) || "";
    brokenState.value = "ok";
  } catch (err) {
    brokenState.value = "err";
    brokenErr.value = String(err?.message || err);
  }
}

// --- form -----------------------------------------------------------------
function resetForm() {
  for (const k of Object.keys(c)) delete c[k];
  for (const k of Object.keys(touched)) delete touched[k];
  for (const k of Object.keys(open)) delete open[k];
  for (const k of Object.keys(weights)) delete weights[k];
  studioOn.value = true;
  studioManual.value = null;
  studioEdit.value = false;
  target.value = "";
  labels.value = true;
  note.value = "";
  brokenFile.value = null;
  if (brokenPreview.value) URL.revokeObjectURL(brokenPreview.value);
  brokenPreview.value = "";
  brokenUrl.value = "";
  brokenState.value = "";
  brokenErr.value = "";
  draftAt.value = "";
}

function initForm() {
  ready = false;
  resetForm();
  for (const l of b.value.lines) {
    // Counting is deliberate: nothing is "good" until somebody says so.
    c[l.itemCode] = { good: 0, supplier: 0, transport: 0, warehouse: 0 };
    touched[l.itemCode] = pending(l) === 0;
  }
  for (const g of groups.value) weights[g.key] = g.initial || "";
  const d = readDraft(b.value.po);
  const codes = b.value.lines.map((l) => l.itemCode).sort().join("|");
  if (d && d.codes === codes) {
    for (const l of b.value.lines) {
      const x = d.c?.[l.itemCode];
      if (x) for (const k of ["good", ...WHERE]) c[l.itemCode][k] = Math.max(0, Math.min(pending(l), Number(x[k]) || 0));
      if (d.touched?.[l.itemCode]) touched[l.itemCode] = true;
      if (d.open?.[l.itemCode]) open[l.itemCode] = true;
    }
    for (const [k, v] of Object.entries(d.weights || {})) if (k in weights && v !== "" && v != null) weights[k] = v;
    studioOn.value = d.studioOn !== false;
    studioManual.value = d.studioManual || null;
    if (d.target && b.value.shelves.includes(d.target)) target.value = d.target;
    labels.value = d.labels !== false;
    note.value = d.note || "";
    if (d.brokenUrl) {
      brokenUrl.value = d.brokenUrl;
      brokenState.value = "ok";
    }
    draftAt.value = new Date(d.at || Date.now()).toLocaleString(locale.value === "ar" ? "ar-EG" : locale.value === "fr" ? "fr-FR" : "en-GB",
      { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  } else if (d) {
    clearDraft(b.value.po);
  }
  // A restored draft is not a new change: keep its time.
  lastSaved = draftState.value || "";
  ready = true;
}

function resetDraft() {
  if (!window.confirm(t("souk.recv.draftResetConfirm"))) return;
  clearDraft(b.value.po);
  initForm();
  draftAt.value = "";
}

const draftState = computed(() => {
  if (!b.value || b.value.done || result.value) return null;
  const dirty = lines.value.some((l) => touched[l.itemCode] && pending(l) > 0)
    || groups.value.some((g) => entered(g) && weights[g.key] !== (g.initial || ""))
    || !!target.value || !!note.value.trim() || !!brokenUrl.value || !!studioManual.value || !studioOn.value;
  if (!dirty) return "";
  return JSON.stringify({
    codes: lines.value.map((l) => l.itemCode).sort().join("|"),
    c, touched, open, weights, studioOn: studioOn.value, studioManual: studioManual.value,
    target: target.value, labels: labels.value, note: note.value, brokenUrl: brokenUrl.value,
  });
});
watch(draftState, (s) => {
  if (!ready || s === null || !b.value || s === lastSaved) return;
  lastSaved = s;
  if (s === "") { clearDraft(b.value.po); return; }
  writeDraft(b.value.po, { ...JSON.parse(s), at: Date.now() });
});

// Good can drop under a hand-set sample: keep the sample inside it.
watch(() => lines.value.map((l) => good(l)).join("|"), () => {
  if (!studioManual.value) return;
  for (const l of lines.value) {
    const n = Number(studioManual.value[l.itemCode]) || 0;
    if (n > good(l)) studioManual.value[l.itemCode] = good(l);
  }
});

const hasDraft = (name) => {
  try { return !!localStorage.getItem(DRAFT_PREFIX + name); } catch (_) { return false; }
};

async function load() {
  loading.value = true;
  result.value = null;
  refBig.value = false;
  try {
    if (!po.value) {
      queue.value = ((await api("souk.receive_queue")).rows || []).map((r) => ({ ...r, draft: hasDraft(r.po) }));
      b.value = null;
    } else {
      b.value = await api("souk.receive_boot", { po: po.value });
      if (b.value.done) clearDraft(b.value.po);
      else initForm();
    }
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

async function post() {
  if (blocker.value) return;
  if (brokenState.value === "err" && !window.confirm(t("souk.recv.photoMissingConfirm"))) return;
  const msg = nothingCame.value
    ? t("souk.allShortConfirm").replace("{n}", fmt(owed.value))
    : t("souk.recvConfirm").replace("{g}", totalGood.value).replace("{b}", totalBroken.value)
      .replace("{s}", totalShort.value).replace("{w}", shortWh(target.value) || "—");
  if (!window.confirm(msg)) return;
  busy.value = true;
  try {
    const res = await apiPost("souk.receive", { po: b.value.po, payload: JSON.stringify({
      target: target.value, labels: labels.value ? 1 : 0, note: note.value, nothingCame: nothingCame.value ? 1 : 0,
      studio: { ...effStudio.value },
      lines: b.value.lines.map((l) => ({
        itemCode: l.itemCode, good: good(l), grams: gramsFor(l),
        broken: { supplier: c[l.itemCode].supplier, transport: c[l.itemCode].transport, warehouse: c[l.itemCode].warehouse },
      })),
    }) });
    clearDraft(b.value.po);
    result.value = res;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

watch(po, load);
onMounted(load);
</script>
