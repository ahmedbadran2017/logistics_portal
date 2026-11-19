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
       Layout = the Receive artboard: one quantity table (good stepper, broken
       box that opens "where did it break"), its amber footer for what the
       stall owes and the broken, then weight, studio + shelf, labels.
       Backend: souk.receive_queue / receive_boot / receive. -->
  <div class="pb-40 text-stone-900">
    <header class="bg-white border-b border-stone-200">
      <div class="max-w-[560px] mx-auto px-4 py-3.5 flex items-start justify-between gap-3">
        <div class="min-w-0 flex flex-col gap-0.5">
          <span class="text-[12px] font-semibold text-stone-500">{{ b && b.isNew ? t('souk.recv.kickerNew') : t('souk.recv.kicker') }}</span>
          <h1 class="m-0 text-[16px] font-bold leading-snug truncate">{{ b ? (b.title || b.po) : t('souk.recvTitle') }}</h1>
          <span v-if="b" class="text-[12px] text-stone-600 truncate">
            <span class="font-mono" dir="ltr">{{ b.po }} · {{ b.stall }}</span><template v-if="b.trip"> · {{ t('souk.tripNo').replace('{n}', b.trip) }}</template>
          </span>
        </div>
        <router-link v-if="po" :to="{ name: 'SoukReceive' }"
                     class="shrink-0 h-11 -me-1 px-2.5 rounded-lg text-[13px] font-semibold text-stone-700 inline-flex items-center gap-1 hover:bg-stone-100">
          <Icon :name="isRTL ? 'chevron-right' : 'chevron-left'" :size="15" />{{ t('souk.recvList') }}
        </router-link>
      </div>
    </header>

    <div class="max-w-[560px] mx-auto px-4 pt-3.5 flex flex-col gap-3.5">
      <div v-if="loading" class="h-[280px] rounded-xl bg-white ring-1 ring-inset ring-stone-200 animate-pulse" />

      <!-- queue -->
      <template v-else-if="!po">
        <div v-if="!queue.length" class="bg-white ring-1 ring-inset ring-stone-200 rounded-xl p-8 text-center text-[14px] text-stone-500">{{ t('souk.recvNone') }}</div>
        <div v-else class="bg-white ring-1 ring-inset ring-stone-200 rounded-xl overflow-hidden">
          <router-link v-for="(r, i) in queue" :key="r.po" :to="{ name: 'SoukReceive', params: { po: r.po } }"
                       class="flex items-center gap-3 px-3.5 py-3 min-h-[72px] hover:bg-stone-50"
                       :class="i ? 'border-t border-stone-100' : ''">
            <img v-if="r.image" :src="r.image" class="w-12 h-12 shrink-0 rounded-[10px] object-cover" alt="" />
            <div v-else class="w-12 h-12 shrink-0 rounded-[10px] bg-stone-100" />
            <div class="min-w-0 flex-1">
              <div class="text-[14px] font-semibold truncate">{{ r.title || r.po }}</div>
              <div class="text-[12px] text-stone-600 truncate">{{ r.stall }} · {{ r.units }} {{ t('souk.pcs') }} · <span class="tabular-nums">{{ r.date }}</span></div>
              <div class="font-mono text-[11px] text-stone-500 truncate self-start" dir="ltr" :class="isRTL ? 'text-right' : ''">{{ r.po }}</div>
            </div>
            <span v-if="r.draft" class="shrink-0 h-6 px-2 rounded-md bg-amber-50 text-amber-800 text-[12px] font-bold inline-flex items-center">{{ t('souk.recv.draftChip') }}</span>
            <Icon :name="isRTL ? 'chevron-left' : 'chevron-right'" :size="16" class="shrink-0 text-stone-500" />
          </router-link>
        </div>
      </template>

      <!-- done -->
      <section v-else-if="result" class="flex flex-col gap-3">
        <div class="bg-emerald-50 ring-1 ring-inset ring-emerald-200 rounded-xl p-4 flex flex-col gap-1">
          <div class="text-[15px] font-bold text-emerald-800">{{ t('souk.recvDone').replace('{n}', result.good) }}</div>
          <div class="text-[13px] text-emerald-800 font-mono self-start" dir="ltr">{{ result.receipt }}<span v-if="result.debitNote"> · {{ result.debitNote }}</span></div>
          <div v-if="result.labels" class="text-[13px] text-emerald-800">{{ t('souk.labelsQueued').replace('{n}', result.labels) }}</div>
        </div>
        <div v-if="result.owed" class="bg-amber-50 ring-1 ring-inset ring-amber-200 rounded-xl p-4 text-[13px] font-semibold text-amber-800">
          {{ t('souk.owedLine').replace('{n}', fmt(result.owed)).replace('{s}', b.stall) }}
        </div>
        <div v-for="(n, i) in result.notes" :key="i" class="bg-white ring-1 ring-inset ring-stone-200 rounded-xl p-3 text-[13px] text-stone-600">{{ n }}</div>
        <div class="grid grid-cols-2 gap-2">
          <router-link :to="{ name: 'SoukReceive' }" class="h-12 rounded-[10px] bg-white ring-1 ring-inset ring-stone-300 text-[14px] font-bold inline-flex items-center justify-center">{{ t('souk.recvNext') }}</router-link>
          <router-link v-if="result.product" :to="{ name: 'SoukProduct', params: { name: result.product } }"
                       class="h-12 rounded-[10px] bg-[var(--accent-600)] hover:bg-[var(--accent-700)] text-white text-[14px] font-bold inline-flex items-center justify-center">{{ t('souk.toProduct') }}</router-link>
        </div>
      </section>

      <div v-else-if="b && b.done" class="bg-white ring-1 ring-inset ring-stone-200 rounded-xl p-5 text-[14px] text-stone-600">
        {{ t('souk.recvAlready').replace('{pr}', b.done) }}
      </div>

      <template v-else-if="b">
        <!-- the count was kept on this phone -->
        <div v-if="draftAt" class="flex items-center justify-between gap-3 bg-amber-50 ring-1 ring-inset ring-amber-200 rounded-xl ps-3 pe-1.5 py-1.5">
          <span class="text-[13px] text-amber-800 leading-snug">{{ t('souk.recv.draftRestored').replace('{t}', draftAt) }}</span>
          <button type="button" class="shrink-0 h-11 px-3 rounded-lg bg-white ring-1 ring-inset ring-amber-200 text-[13px] font-bold text-amber-800" @click="resetDraft">{{ t('souk.recv.draftReset') }}</button>
        </div>

        <!-- the buyer's reference photo -->
        <section class="flex gap-3 items-center bg-white ring-1 ring-inset ring-stone-200 rounded-xl p-3">
          <button v-if="b.image" type="button" class="w-16 h-16 shrink-0 rounded-[10px] overflow-hidden" @click="refBig = true" :aria-label="t('souk.recv.refTitle')">
            <img :src="b.image" class="w-full h-full object-cover" alt="" />
          </button>
          <div v-else class="w-16 h-16 shrink-0 rounded-[10px] bg-[repeating-linear-gradient(45deg,#f5f5f4_0_7px,#e7e5e4_7px_8px)] flex items-center justify-center">
            <Icon name="image" :size="20" class="text-stone-500" />
          </div>
          <div class="min-w-0 flex flex-col gap-0.5">
            <span class="text-[13px] font-semibold">{{ t('souk.recv.refTitle') }}</span>
            <span class="text-[12px] text-stone-600 leading-normal">{{ t('souk.recv.refHint') }}</span>
          </div>
        </section>

        <!-- quantity: good / broken per variant, short is the rest -->
        <section class="bg-white ring-1 ring-inset ring-stone-200 rounded-xl flex flex-col">
          <div class="grid grid-cols-[minmax(0,1fr)_132px_64px] gap-2 px-3.5 pt-3 pb-2 items-end">
            <h2 class="m-0 text-[14px] font-bold">{{ t('souk.recv.qtyTitle') }}</h2>
            <span class="text-[12px] font-semibold text-stone-600 text-center">{{ t('souk.good') }}</span>
            <span class="text-[12px] font-semibold text-stone-600 text-center">{{ t('souk.brokenShort') }}</span>
          </div>

          <div v-for="(l, i) in b.lines" :key="l.itemCode"
               class="grid grid-cols-[minmax(0,1fr)_132px_64px] gap-x-2 gap-y-2 items-center px-3.5 py-2 border-t border-stone-100"
               :class="[rowBg(l), i === b.lines.length - 1 && !footerOn ? 'rounded-b-xl' : '']">
            <div class="min-w-0 flex flex-col">
              <span class="font-mono text-[12px] font-medium truncate self-start max-w-full" dir="ltr">{{ l.sku }}</span>
              <span v-if="l.label" class="text-[12px] text-stone-500 truncate">{{ l.label }}</span>
              <span class="text-[12px] leading-snug" :class="noteTone(l)">{{ noteOf(l) }}</span>
            </div>
            <Stepper :model-value="c[l.itemCode].good" :max="Math.max(0, pending(l) - brokenOf(l))" :bad="over(l)"
                     :label="t('souk.good') + ' ' + l.sku"
                     @update:model-value="(v) => setCount(l, 'good', v)" />
            <button type="button" class="h-11 rounded-lg ring-1 ring-inset text-[16px] font-bold tabular-nums inline-flex items-center justify-center gap-0.5"
                    :class="brokenOf(l) ? 'bg-rose-50 ring-rose-200 text-rose-700' : 'bg-white ring-stone-300 text-stone-800 hover:bg-stone-50'"
                    :aria-expanded="!!open[l.itemCode]" :aria-label="t('souk.recv.brokenBtn') + ' ' + l.sku"
                    @click="open[l.itemCode] = !open[l.itemCode]">
              {{ brokenOf(l) }}<Icon :name="open[l.itemCode] ? 'chevron-up' : 'chevron-down'" :size="12" class="opacity-60" />
            </button>

            <!-- not counted yet: the two one-tap answers -->
            <div v-if="!touched[l.itemCode] && !open[l.itemCode]" class="col-span-3 grid grid-cols-[1fr_auto] gap-2">
              <button type="button" class="h-11 rounded-lg bg-emerald-50 ring-1 ring-inset ring-emerald-200 text-emerald-800 text-[13px] font-bold inline-flex items-center justify-center gap-1.5"
                      @click="allArrived(l)">
                <Icon name="check" :size="15" />{{ t('souk.recv.allArrived').replace('{n}', Math.max(0, pending(l) - brokenOf(l))) }}
              </button>
              <button type="button" class="h-11 px-3 rounded-lg bg-white ring-1 ring-inset ring-stone-300 text-stone-600 text-[13px] font-semibold"
                      @click="noneCame(l)">{{ t('souk.recv.noneCame') }}</button>
            </div>

            <!-- opened from the broken box: where it broke, and the quick answers -->
            <div v-if="open[l.itemCode]" class="col-span-3 rounded-lg bg-white ring-1 ring-inset ring-stone-200 p-2.5 flex flex-col gap-2.5 mb-1">
              <div class="grid grid-cols-[1fr_auto] gap-2">
                <button type="button" class="h-11 rounded-lg ring-1 ring-inset text-[13px] font-bold inline-flex items-center justify-center gap-1.5"
                        :class="allIn(l) ? 'bg-emerald-700 text-white ring-emerald-700' : 'bg-emerald-50 text-emerald-800 ring-emerald-200'"
                        @click="allArrived(l)">
                  <Icon name="check" :size="15" />{{ t('souk.recv.allArrived').replace('{n}', Math.max(0, pending(l) - brokenOf(l))) }}
                </button>
                <button type="button" class="h-11 px-3 rounded-lg ring-1 ring-inset text-[13px] font-semibold"
                        :class="touched[l.itemCode] && !arrived(l) ? 'bg-amber-50 text-amber-800 ring-amber-200' : 'bg-white text-stone-600 ring-stone-300'"
                        @click="noneCame(l)">{{ t('souk.recv.noneCame') }}</button>
              </div>
              <div class="text-[12px] font-bold text-rose-700">{{ t('souk.recv.whereQ') }}</div>
              <div v-for="w in WHERE" :key="w" class="grid grid-cols-[minmax(0,1fr)_132px] gap-2 items-center">
                <div class="min-w-0">
                  <div class="text-[13px] font-semibold text-stone-800 leading-snug">{{ t('souk.br_' + w) }}</div>
                  <div class="text-[12px] text-stone-500 leading-snug">{{ t('souk.brh_' + w) }}</div>
                </div>
                <Stepper :model-value="c[l.itemCode][w]" :max="pending(l)" tone="bad" :label="t('souk.br_' + w) + ' ' + l.sku"
                         @update:model-value="(v) => setCount(l, w, v)" />
              </div>
            </div>
          </div>

          <!-- what the stall owes, the broken, their photo -->
          <div v-if="footerOn" class="px-3.5 py-2.5 flex flex-col gap-2 bg-amber-50 rounded-b-xl border-t border-amber-200">
            <div v-if="owed > 0" class="flex gap-2 items-start">
              <Icon name="alert-triangle" :size="15" :stroke-width="2" class="shrink-0 mt-0.5 text-amber-700" />
              <div class="min-w-0 flex flex-col gap-0.5 text-[12px] text-amber-800 leading-normal">
                <span><b>{{ t('souk.owedLine').replace('{n}', fmt(owed)).replace('{s}', b.stall) }}.</b> {{ b.hasInvoice ? t('souk.owedDebit') : t('souk.owedNoBooks') }}</span>
                <span v-for="o in owedLines" :key="o.itemCode" class="tabular-nums font-mono text-[12px] self-start" dir="ltr">
                  {{ t('souk.recv.owedBy').replace('{sku}', o.sku).replace('{n}', o.qty).replace('{r}', fmt(o.rate)).replace('{m}', fmt(o.qty * o.rate)) }}
                </span>
              </div>
            </div>
            <div v-if="anyBroken" class="flex gap-2 items-start">
              <Icon name="alert-triangle" :size="15" :stroke-width="2" class="shrink-0 mt-0.5 text-amber-700" />
              <span class="text-[12px] text-amber-800 leading-normal"><b>{{ t('souk.recv.brokenBold').replace('{n}', totalBroken) }}</b> {{ t('souk.recv.brokenRest') }}</span>
            </div>
            <span v-if="anyBroken" class="text-[12px] text-amber-800 leading-normal">{{ t('souk.recv.whereRule') }}</span>
            <span v-if="lossWaitsOn" class="text-[12px] text-amber-800 leading-normal">{{ t('souk.lossWaits') }}</span>

            <!-- broken photo: uploads at once, its failure shows and can be retried -->
            <div v-if="anyBroken || brokenState" class="flex items-center gap-2 flex-wrap">
              <label class="h-11 ps-1 pe-3 rounded-lg bg-white ring-1 ring-inset ring-amber-200 text-[13px] font-semibold text-amber-800 inline-flex items-center gap-2 cursor-pointer"
                     :class="brokenState === 'up' ? 'opacity-70 cursor-wait' : ''">
                <span class="w-9 h-9 shrink-0 rounded-md overflow-hidden bg-amber-50 flex items-center justify-center relative">
                  <img v-if="brokenPreview || brokenUrl" :src="brokenPreview || brokenUrl" class="w-full h-full object-cover" alt="" />
                  <Icon v-else name="camera" :size="16" />
                  <span v-if="brokenState === 'up'" class="absolute inset-0 bg-white/70 flex items-center justify-center">
                    <span class="w-4 h-4 rounded-full border-2 border-amber-200 border-t-amber-800 animate-spin" />
                  </span>
                </span>
                {{ brokenState ? t('souk.recv.photoRetake') : t('souk.recv.photoTake') }}
                <input type="file" accept="image/*" capture="environment" class="hidden" :disabled="brokenState === 'up'" @change="pickBroken" />
              </label>
              <span v-if="brokenState === 'up'" class="text-[12px] text-amber-800">{{ t('souk.recv.photoUploading') }}</span>
              <span v-else-if="brokenState === 'ok'" class="text-[12px] font-semibold text-emerald-700 inline-flex items-center gap-1"><Icon name="check" :size="13" />{{ t('souk.recv.photoSaved') }}</span>
            </div>
            <div v-if="brokenState === 'err'" class="flex items-center justify-between gap-2 rounded-lg bg-rose-50 ring-1 ring-inset ring-rose-200 ps-3 pe-1.5 py-1.5">
              <span class="text-[12px] text-rose-700 min-w-0 break-words">{{ t('souk.recv.photoFailed').replace('{e}', brokenErr) }}</span>
              <button type="button" class="shrink-0 h-11 px-3 rounded-lg bg-white ring-1 ring-inset ring-rose-200 text-[13px] font-bold text-rose-700 inline-flex items-center gap-1.5" @click="sendBroken">
                <Icon name="refresh-cw" :size="14" />{{ t('souk.recv.photoRetry') }}
              </button>
            </div>
          </div>
        </section>

        <!-- weight: one piece of each size, required for good pieces -->
        <section class="bg-white ring-1 ring-inset ring-stone-200 rounded-xl px-3.5 py-3 flex flex-col gap-2.5">
          <div class="flex items-baseline justify-between gap-2">
            <h2 class="m-0 text-[14px] font-bold">{{ t('souk.recv.weightTitle') }}</h2>
            <span v-if="groups.some((g) => !g.allKnown)" class="text-[12px] font-bold text-rose-700">{{ t('souk.recv.required') }}</span>
          </div>
          <div class="grid grid-cols-2 gap-2.5">
            <div v-for="g in groups" :key="g.key" class="min-w-0 flex flex-col gap-[5px]">
              <label :for="'w-' + g.key" class="text-[13px] font-semibold text-stone-700 truncate">
                {{ g.size ? t('souk.recv.sizeOf').replace('{s}', g.size) : g.label }}
              </label>
              <div class="relative">
                <input :id="'w-' + g.key" v-model="weights[g.key]" type="number" inputmode="decimal" min="1" max="100000"
                       :placeholder="g.allKnown ? knownText(g) : ''"
                       class="w-full h-11 rounded-lg border ps-3 pe-8 text-[16px] tabular-nums bg-white outline-none focus:ring-2 focus:ring-[var(--accent-600)]/30 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                       :class="weightMissing(g) || weightBadOf(g) ? 'border-rose-300 bg-rose-50' : 'border-stone-300'" />
                <span class="absolute inset-y-0 end-3 flex items-center text-[14px] text-stone-500 pointer-events-none">g</span>
              </div>
              <span v-if="g.allKnown" class="text-[12px] text-emerald-700 truncate">{{ t('souk.recv.weightKnown') }}</span>
            </div>
          </div>
          <span class="text-[12px] text-stone-600 leading-normal">{{ groups.some((g) => g.size && g.lines.length > 1) ? t('souk.recv.weightFoot') : t('souk.recv.weightFootOne') }}</span>
        </section>

        <!-- studio sample + shelf -->
        <section class="bg-white ring-1 ring-inset ring-stone-200 rounded-xl px-3.5 py-3 flex flex-col gap-2.5">
          <template v-if="b.studioSamples">
            <h2 class="m-0 text-[14px] font-bold">{{ t('souk.recv.studioTitle') }}</h2>
            <label class="flex gap-2.5 items-center min-h-[44px] cursor-pointer">
              <input v-model="studioOn" type="checkbox" class="peer sr-only" />
              <span aria-hidden="true" class="w-[22px] h-[22px] shrink-0 rounded-md flex items-center justify-center peer-focus-visible:ring-2 peer-focus-visible:ring-[var(--accent-600)]/40"
                    :class="studioOn ? 'bg-[var(--accent-600)] text-white' : 'bg-white ring-1 ring-inset ring-stone-300'">
                <Icon v-if="studioOn" name="check" :size="13" :stroke-width="3" />
              </span>
              <span class="text-[13px] leading-normal">
                <template v-for="(part, k) in studioText" :key="k"><b v-if="part.b">{{ part.s }}</b><template v-else>{{ part.s }}</template></template>
              </span>
            </label>
            <span class="text-[12px] text-stone-600 leading-normal">{{ t('souk.recv.studioHint') }}</span>
            <template v-if="studioOn">
              <div v-if="!totalGood" class="text-[12px] text-amber-800">{{ t('souk.recv.studioWaits') }}</div>
              <div v-else-if="!studioEdit" class="flex items-center justify-between gap-2">
                <div class="flex flex-wrap gap-1.5 min-w-0">
                  <span v-for="(n, code) in effStudio" :key="code" class="h-6 px-2 rounded-md bg-stone-100 text-[12px] font-mono inline-flex items-center" dir="ltr">{{ skuOf(code) }} ×{{ n }}</span>
                </div>
                <button type="button" class="shrink-0 h-11 px-3 rounded-lg ring-1 ring-inset ring-stone-300 text-[13px] font-semibold" @click="studioEdit = true">{{ t('souk.recv.studioChange') }}</button>
              </div>
              <div v-else class="rounded-lg bg-stone-50 ring-1 ring-inset ring-stone-200 p-2.5 flex flex-col gap-2">
                <div v-for="l in b.lines" :key="l.itemCode" class="grid grid-cols-[minmax(0,1fr)_132px] gap-2 items-center"
                     :class="good(l) || effStudio[l.itemCode] ? '' : 'opacity-50'">
                  <div class="min-w-0 flex flex-col">
                    <span class="font-mono text-[12px] font-medium truncate self-start max-w-full" dir="ltr">{{ l.sku }}</span>
                    <span class="text-[12px] text-stone-500 truncate">{{ t('souk.good') }} {{ good(l) }}</span>
                  </div>
                  <Stepper :model-value="effStudio[l.itemCode] || 0" :max="good(l)" :label="t('souk.toStudio') + ' ' + l.sku"
                           @update:model-value="(v) => setStudio(l, v)" />
                </div>
                <div class="flex items-center justify-between gap-2 pt-0.5">
                  <button v-if="studioManual" type="button" class="h-11 px-1 text-[13px] font-semibold text-stone-600 underline" @click="studioManual = null">{{ t('souk.recv.studioReset') }}</button>
                  <span v-else />
                  <button type="button" class="h-11 px-4 rounded-lg bg-stone-900 text-white text-[13px] font-bold" @click="studioEdit = false">{{ t('souk.recv.studioDone') }}</button>
                </div>
              </div>
            </template>
          </template>

          <div class="flex flex-col gap-[5px]">
            <label for="souk-shelf" class="text-[13px] font-semibold text-stone-700">{{ t('souk.shelf') }}</label>
            <select id="souk-shelf" v-model="target" class="w-full h-11 rounded-lg border px-2.5 text-[15px] bg-white outline-none focus:ring-2 focus:ring-[var(--accent-600)]/30"
                    :class="needsShelf && !target ? 'border-amber-400' : 'border-stone-300'">
              <option value="">—</option>
              <option v-for="w in b.shelves" :key="w" :value="w">{{ shortWh(w) }}</option>
            </select>
            <span class="text-[12px] text-stone-600 leading-normal">{{ t('souk.shelfHint') }}</span>
          </div>
          <input v-model="note" :placeholder="t('souk.note')" class="w-full h-11 rounded-lg border border-stone-300 px-3 text-[16px] bg-white outline-none focus:ring-2 focus:ring-[var(--accent-600)]/30" />
        </section>

        <!-- labels -->
        <section class="bg-white ring-1 ring-inset ring-stone-200 rounded-xl">
          <label class="flex gap-3 items-center px-3.5 py-3 min-h-[44px] cursor-pointer">
            <div aria-hidden="true" class="w-[74px] h-11 shrink-0 rounded-md ring-1 ring-inset ring-stone-300 bg-white flex flex-col items-center justify-center gap-0.5">
              <div class="w-[58px] h-[18px] bg-[repeating-linear-gradient(90deg,#1c1917_0_1px,#fff_1px_3px,#1c1917_3px_5px,#fff_5px_6px)]" />
              <span class="font-mono text-[6.5px] text-stone-900 max-w-[66px] truncate" dir="ltr">{{ b.lines[0] && b.lines[0].sku }}</span>
            </div>
            <div class="min-w-0 flex-1 flex flex-col">
              <span class="text-[13px] font-semibold">{{ t('souk.recv.labelsTitle').replace('{n}', totalGood) }}</span>
              <span class="text-[12px] text-stone-600">{{ t('souk.recv.labelsStation') }}</span>
            </div>
            <input v-model="labels" type="checkbox" class="peer sr-only" />
            <span aria-hidden="true" class="w-[22px] h-[22px] shrink-0 rounded-md flex items-center justify-center peer-focus-visible:ring-2 peer-focus-visible:ring-[var(--accent-600)]/40"
                  :class="labels ? 'bg-[var(--accent-600)] text-white' : 'bg-white ring-1 ring-inset ring-stone-300'">
              <Icon v-if="labels" name="check" :size="13" :stroke-width="3" />
            </span>
          </label>
        </section>
      </template>
    </div>

    <footer v-if="b && !b.done && !result && !loading && po" class="lp-footer bg-white px-4 pt-3 pb-4">
      <div class="max-w-[560px] mx-auto flex flex-col gap-2">
        <div v-if="blocker && blocker.trim() && !busy" class="text-[12px] font-semibold text-amber-800 text-center leading-snug">{{ blocker }}</div>
        <button type="button" class="w-full h-[52px] rounded-[10px] bg-[var(--accent-600)] hover:bg-[var(--accent-700)] text-white text-[15px] font-bold inline-flex items-center justify-center gap-2 disabled:bg-stone-200 disabled:text-stone-600"
                :disabled="busy || !!blocker" @click="post">
          <Icon v-if="!busy && !nothingCame && labels && totalGood" name="printer" :size="18" :stroke-width="2" />
          {{ busy ? t('souk.sending') : nothingCame ? t('souk.allShort')
            : labels && totalGood ? t('souk.recv.confirmPrint').replace('{n}', totalGood) : t('souk.recv.confirm') }}
        </button>
      </div>
    </footer>

    <!-- the reference photo, big -->
    <div v-if="refBig && b && b.image" class="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4" @click="refBig = false">
      <img :src="b.image" class="max-w-full max-h-full rounded-xl object-contain" alt="" />
      <button type="button" class="absolute top-3 end-3 w-11 h-11 rounded-full bg-white/90 text-stone-900 flex items-center justify-center" :aria-label="t('souk.recv.close')">
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

// − n + in one 44px box (the artboard's stepper), each half a 44px target:
// counted with a thumb, often with gloves on. The number stays typeable.
const Stepper = defineComponent({
  props: { modelValue: { type: Number, default: 0 }, max: { type: Number, default: 9999 }, tone: String, label: String, bad: Boolean },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const clamp = (v) => Math.max(0, Math.min(props.max, Math.round(Number(v) || 0)));
    const set = (v) => emit("update:modelValue", clamp(v));
    const btn = "w-11 h-11 shrink-0 text-[18px] leading-none text-stone-500 hover:text-stone-900";
    return () => h("div", {
      class: "flex items-center h-11 w-full rounded-lg bg-white ring-1 ring-inset "
        + (props.bad ? "ring-rose-300 bg-rose-50" : "ring-stone-300"),
    }, [
      h("button", { type: "button", class: btn, "aria-label": "−",
        onClick: () => set((props.modelValue || 0) - 1) }, "−"),
      h("input", {
        type: "number", inputmode: "numeric", value: props.modelValue, "aria-label": props.label,
        class: "min-w-0 flex-1 h-full bg-transparent text-center text-[16px] font-bold tabular-nums outline-none "
          + "[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none "
          + (props.tone === "bad" && props.modelValue > 0 ? "text-rose-700" : "text-stone-900"),
        // DataWedge / a keypad commits text: react to the value, never to Enter.
        onInput: (e) => {
          const v = clamp(e.target.value);
          set(v);
          if (e.target.value !== "" && String(v) !== e.target.value) e.target.value = String(v);
        },
      }),
      h("button", { type: "button", class: btn, "aria-label": "+",
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

// --- the quantity table (artboard): one row per variant ---------------------
const issue = (l) => touched[l.itemCode] && (shortOf(l) > 0 || brokenOf(l) > 0);
const rowBg = (l) => (over(l) ? "bg-rose-50" : issue(l) ? "bg-amber-50" : "bg-white");
const noteTone = (l) => (over(l) ? "text-rose-700 font-semibold" : issue(l) ? "text-amber-700" : "text-stone-600");
function noteOf(l) {
  if (over(l)) return t("souk.tooMany");
  const parts = [t("souk.recv.want").replace("{n}", pending(l))];
  if (!touched[l.itemCode]) parts.push(t("souk.recv.notCounted"));
  else {
    if (shortOf(l)) parts.push(t("souk.recv.shortN").replace("{n}", shortOf(l)));
    if (brokenOf(l)) parts.push(t("souk.recv.brokenN").replace("{n}", brokenOf(l)));
  }
  return parts.join(" · ");
}
const lossWaitsOn = computed(() => !!b.value && ((ourBroken.value.transport && !b.value.lossAccounts?.transport)
  || (ourBroken.value.warehouse && !b.value.lossAccounts?.warehouse)));
// The table's amber footer: what the stall owes, the broken and their photo.
const footerOn = computed(() => owed.value > 0 || anyBroken.value || !!brokenState.value || lossWaitsOn.value);
// "Studio - JM" in bold inside the sentence, as on the artboard.
const studioText = computed(() => {
  const n = studioOn.value ? (totalStudio.value || plannedStudio.value) : 0;
  const s = !studioManual.value && plannedStudio.value === perColor.value.length
    ? t("souk.recv.studioPerColor").replace("{n}", n)
    : t("souk.recv.studioOn").replace("{n}", n);
  const out = [];
  s.split("Studio - JM").forEach((x, i) => {
    if (i) out.push({ s: "Studio - JM", b: true });
    if (x) out.push({ s: x });
  });
  return out;
});

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
