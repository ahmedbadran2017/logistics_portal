<template>
  <div class="max-w-[1240px] mx-auto px-6 py-6">
    <!-- Back -->
    <button
      class="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap"
      @click="goBack"
    >
      <Icon name="chevron-left" :size="15" class="flip-rtl" /> {{ t("ordersPg.title") }}
    </button>

    <!-- Header -->
    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div class="min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <h1 class="font-mono text-[20px] font-bold text-stone-900">{{ order.no }}</h1>
            <span
              class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1"
              :class="channelBadge.cls"
            >{{ channelBadge.label }}</span>
            <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 whitespace-nowrap" :class="salesBadge.cls">
              <span class="w-1.5 h-1.5 rounded-full bg-current opacity-60" /> {{ salesBadge.label }}
            </span>
            <span
              class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 whitespace-nowrap"
              :class="stageBadge.cls"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="stageBadge.dot" /> {{ stageBadge.label }}
            </span>
            <span
              class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 whitespace-nowrap"
              :class="slaBadge.cls"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="slaBadge.dot" /> {{ slaBadge.label }}
            </span>
          </div>
          <div class="text-[13px] text-stone-600 mt-1 flex items-center gap-2 flex-wrap">
            <span>{{ order.customer }} · {{ shipToLine }}</span>
            <span class="font-mono text-[12px] font-semibold text-stone-900 tabular-nums bg-stone-100 rounded-md px-2 py-0.5">{{ fmtMAD(grand) }} MAD</span>
            <span v-if="isLive && liveOrder.created" class="text-[11.5px] text-stone-400 tabular-nums">{{ t("od.placed") }} {{ local(liveOrder.created).slice(5) }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <a
            v-if="order.awb && isLive && liveOrder.label_url"
            :href="liveOrder.label_url" target="_blank"
            class="inline-flex items-center gap-1.5 h-9 px-3 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 hover:ring-stone-300"
          >
            <Icon name="file-text" :size="15" /> {{ t("od.printAwb") }}
          </a>
          <a
            :href="'/app/sales-order/' + encodeURIComponent(order.no)" target="_blank"
            class="inline-flex items-center gap-1.5 h-9 px-3 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 hover:ring-stone-300"
          >
            {{ t("od.openErp") }} <Icon name="arrow-right" :size="13" class="flip-rtl" />
          </a>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4">
      <!-- LEFT -->
      <div class="space-y-4">
        <!-- Line items -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-3 border-b border-stone-100">
            <div class="text-[13px] font-semibold text-stone-900">{{ t("od.lineItems") }}</div>
            <div class="text-[11.5px] text-stone-400 mt-0.5">{{ items.length }} {{ t(items.length === 1 ? "od.item" : "od.items", "items") }}</div>
          </div>
          <div class="overflow-x-auto"><table class="w-full min-w-[440px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t("od.product") }}</th>
                <th v-if="!isLive" class="text-start px-4 py-2.5 hidden sm:table-cell">{{ t("od.bin") }}</th>
                <th class="text-end px-4 py-2.5">{{ t("od.qty") }}</th>
                <th class="text-end px-4 py-2.5 hidden sm:table-cell">{{ t("od.unit") }}</th>
                <th class="text-end px-4 py-2.5">{{ t("od.total") }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="(it, i) in items" :key="i">
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2.5">
                    <img v-if="it.image" :src="it.image" loading="lazy"
                         class="w-9 h-9 rounded-lg object-cover ring-1 ring-stone-200/70 flex-shrink-0 bg-stone-100"
                         @error="it.image = ''" />
                    <span v-else class="w-9 h-9 rounded-lg bg-stone-100 ring-1 ring-stone-200/70 flex items-center justify-center flex-shrink-0 text-stone-400">
                      <Icon name="package" :size="15" />
                    </span>
                    <div class="min-w-0">
                      <div class="text-[12.5px] font-medium text-stone-900 truncate max-w-[200px]">{{ it.name }}</div>
                      <button class="font-mono text-[10.5px] text-[var(--accent-700)] hover:underline text-start" title="Open SKU lookup" @click="openSku(it.realSku || it.sku)">
                        SKU {{ it.realSku || it.sku }}
                      </button>
                    </div>
                  </div>
                </td>
                <td v-if="!isLive" class="px-4 py-2.5 font-mono text-[11.5px] text-stone-500 hidden sm:table-cell">{{ it.bin }}</td>
                <td class="px-4 py-2.5 text-end text-[12.5px] font-medium text-stone-900 tabular-nums">{{ it.qty }}</td>
                <td class="px-4 py-2.5 text-end text-[12px] text-stone-500 tabular-nums hidden sm:table-cell">{{ fmtMAD(it.price) }}</td>
                <td class="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{{ fmtMAD(it.line) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="border-t border-stone-100">
                <td class="px-4 pt-2.5 pb-0.5 text-[12px] text-stone-500" colspan="4">{{ t("od.subtotal") }}</td>
                <td class="px-4 pt-2.5 pb-0.5 text-end text-[12px] text-stone-700 tabular-nums">{{ fmtMAD(subtotal) }}</td>
              </tr>
              <tr>
                <td class="px-4 py-0.5 text-[12px] text-stone-500" colspan="4">{{ t("od.shipping") }}</td>
                <td class="px-4 py-0.5 text-end text-[12px] text-stone-700 tabular-nums">{{ shipping ? fmtMAD(shipping) : '—' }}</td>
              </tr>
              <tr v-if="discount > 0">
                <td class="px-4 py-0.5 text-[12px] text-stone-500" colspan="4">{{ t("od.discount") }}</td>
                <td class="px-4 py-0.5 text-end text-[12px] text-emerald-600 tabular-nums">−{{ fmtMAD(discount) }}</td>
              </tr>
              <tr>
                <td class="px-4 py-0.5 text-[12px] text-stone-500" colspan="4">{{ t("od.tax") }}</td>
                <td class="px-4 py-0.5 text-end text-[12px] text-stone-700 tabular-nums">{{ fmtMAD(tax) }}</td>
              </tr>
              <tr class="border-t border-stone-200 bg-stone-50/60">
                <td class="px-4 py-2.5 text-[12.5px] font-semibold text-stone-700" colspan="4">{{ t("od.grandTotal") }}</td>
                <td class="px-4 py-2.5 text-end text-[14px] font-bold text-stone-900 tabular-nums">
                  {{ fmtMAD(grand) }} <span class="text-[10px] font-normal text-stone-400">MAD</span>
                </td>
              </tr>
            </tfoot>
          </table></div>
        </div>

        <!-- Ship to + Payment -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div class="text-[13px] font-semibold text-stone-900 mb-2">{{ t("od.shipTo") }}</div>
            <div class="text-[13px] font-medium text-stone-900">{{ order.customer }}</div>
            <div class="space-y-1.5 mt-2 text-[12px]">
              <div class="flex items-center justify-between gap-2"><span class="text-stone-400">{{ t("od.phone") }}</span>
                <span class="flex items-center gap-1.5">
                  <span class="font-mono font-medium text-stone-800">{{ phone }}</span>
                  <template v-if="isLive && phone !== '—'">
                    <a :href="'tel:' + phone" class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-emerald-100 hover:text-emerald-700 flex items-center justify-center"><Icon name="phone" :size="11" /></a>
                    <a :href="'https://wa.me/212' + phone.replace(/\D/g,'').replace(/^0/,'')" target="_blank" class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-emerald-100 hover:text-emerald-700 flex items-center justify-center"><Icon name="message-circle" :size="11" /></a>
                    <!-- The order is one line of a longer story: 60% of
                         orders come from a number that has ordered before.
                         Only for the lanes that own the customer — the
                         backend gate would refuse a picker anyway. -->
                    <RouterLink v-if="canSeeCustomer" :to="{ name: 'CsLookup', query: { q: phone } }"
                                :title="t('od.customerHistory')"
                                class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-violet-100 hover:text-violet-700 flex items-center justify-center"><Icon name="user" :size="11" /></RouterLink>
                  </template>
                </span></div>
              <div class="flex items-center justify-between gap-2"><span class="text-stone-400">{{ t("od.destination") }}</span><span class="font-medium text-stone-800 text-end truncate">{{ shipToLine }}</span></div>
              <div class="flex items-center justify-between gap-2"><span class="text-stone-400">{{ t("od.governorate") }}</span><span class="font-medium text-stone-800">{{ govern }}</span></div>
              <div v-if="refNo && refNo !== order.no" class="flex items-center justify-between gap-2"><span class="text-stone-400">{{ t("od.reference") }}</span><span class="font-mono font-medium text-stone-800">{{ refNo }}</span></div>
            </div>
          </div>
          <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div class="text-[13px] font-semibold text-stone-900 mb-2">{{ t("od.payment") }}</div>
            <div class="flex items-center gap-1.5">
              <Icon name="dollar-sign" :size="14" class="text-emerald-500" />
              <span class="text-[12.5px] font-medium text-stone-800">{{ t("od.cod") }}</span>
            </div>
            <div class="text-[20px] font-bold text-stone-900 tabular-nums mt-1.5">
              {{ fmtMAD(grand) }} <span class="text-[11px] font-medium text-stone-400">MAD</span>
            </div>
            <div class="flex items-center gap-1.5 mt-2 flex-wrap">
              <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1" :class="channelBadge.cls">{{ channelBadge.label }}</span>
              <span
                class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 whitespace-nowrap"
                :class="codPending ? 'bg-amber-50 text-amber-700 ring-amber-200' : 'bg-emerald-50 text-emerald-700 ring-emerald-200'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="codPending ? 'bg-amber-500' : 'bg-emerald-500'" />
                {{ codPending ? t('od.codPending') : t('od.paid') }}
              </span>
            </div>
          </div>
        </div>

        <!-- Documents -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3">
          <div class="text-[13px] font-semibold text-stone-900 px-1 pt-1 pb-3">{{ t("od.documents") }}</div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <component
              v-for="(d, i) in documents"
              :key="i"
              :is="d.on && d.href ? 'a' : 'button'"
              v-bind="d.on && d.href ? { href: d.href, target: '_blank' } : { disabled: !d.on }"
              class="flex items-center gap-2 px-3 py-2.5 rounded-lg ring-1 transition-all"
              :class="d.on ? 'ring-stone-200 hover:ring-stone-300 text-stone-700' : 'ring-stone-100 text-stone-300 cursor-not-allowed'"
            >
              <Icon :name="d.icon" :size="15" :class="d.on ? 'text-stone-400' : ''" />
              <span class="text-[12px] font-medium flex-1 text-start">{{ d.label }}</span>
            </component>
          </div>
        </div>
      </div>

      <!-- RIGHT -->
      <div class="space-y-4">
        <!-- Fulfillment status timeline (fabricated · preview only) -->
        <div v-if="!isLive" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center justify-between mb-4">
            <div class="text-[13px] font-semibold text-stone-900">{{ t("od.fulfillStatus") }}</div>
            <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 bg-[var(--accent-50)] text-[var(--accent-700)] ring-[var(--accent-200,#c7d2fe)]">
              <span class="w-1.5 h-1.5 rounded-full bg-[var(--accent-500)]" /> {{ order.picker ? byId(order.picker).short : t('od.unassigned') }}
            </span>
          </div>

          <ol class="relative">
            <li v-for="(e, i) in timeline" :key="e.key" class="relative flex gap-3 pb-3.5 last:pb-0">
              <span
                v-if="i < timeline.length - 1"
                class="absolute top-5 w-px left-[9px]"
                :class="e.bad ? 'bg-rose-200' : 'bg-emerald-200'"
                style="bottom: 0"
              />
              <span
                class="relative z-10 w-[19px] h-[19px] rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-white"
                :class="e.bad ? 'bg-rose-500' : 'bg-emerald-500'"
              >
                <Icon :name="e.bad ? 'alert-triangle' : 'check'" :size="11" />
              </span>
              <div class="min-w-0 flex-1">
                <div class="flex items-center justify-between gap-2">
                  <span class="text-[12.5px] font-medium truncate" :class="e.bad ? 'text-rose-700' : 'text-stone-900'">{{ e.label }}</span>
                  <span class="text-[11px] text-stone-400 tabular-nums flex-shrink-0">{{ local(e.at) }}</span>
                </div>
                <div class="flex items-center gap-1.5 mt-0.5">
                  <span class="text-[11px] text-stone-500 truncate min-w-0">{{ e.actor }}</span>
                  <span v-if="e.doc" class="font-mono text-[10px] text-stone-400 bg-stone-50 ring-1 ring-stone-200/70 rounded px-1 flex-shrink-0">{{ e.doc }}</span>
                </div>
              </div>
            </li>
          </ol>
        </div>

        <!-- The parcel's clock: where it is, what it was promised, every hand it passed -->
        <div v-if="isLive && journey && journey.found" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center justify-between gap-2 mb-3 flex-wrap">
            <div class="text-[13px] font-semibold text-stone-900">{{ t("od.journey") }}</div>
            <div class="flex items-center gap-2">
              <button v-if="journey.row.stage === 'with_carrier' || journey.row.stage === 'failed' || journey.row.stage === 'delivered'"
                      class="h-7 px-2.5 rounded-lg text-[11px] font-semibold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50 inline-flex items-center gap-1"
                      :disabled="checking" @click="checkCarrier">
                <Icon name="refresh-cw" :size="11" :class="checking ? 'animate-spin' : ''" />{{ checking ? t('trk.checking') : t('trk.checkCarrier') }}
              </button>
              <span class="text-[10px] font-bold rounded-full px-2 py-0.5" :class="JSTAGE_CLS[journey.row.stage] || 'bg-stone-100 text-stone-600'">{{ t('oclk.s_' + journey.row.stage, journey.row.stage) }}</span>
            </div>
          </div>
          <div v-if="carrierCheck" class="mb-3 rounded-xl ring-1 overflow-hidden" :class="carrierCheck.ok ? 'ring-sky-200/70' : 'ring-amber-200/70'">
            <div class="px-3 py-2 flex items-center gap-2 text-[12px]" :class="carrierCheck.ok ? 'bg-sky-50/60' : 'bg-amber-50/60'">
              <span class="font-semibold text-stone-800">{{ t('trk.carrierSays') }}</span>
              <span v-if="carrierCheck.ok" class="font-bold text-sky-800">{{ carrierCheck.carrierStatus || carrierCheck.status || '—' }}</span>
              <span v-else class="text-amber-800">{{ t('trk.noTracking') }}</span>
              <span class="ms-auto text-[10.5px] text-stone-400 tabular-nums" dir="ltr">{{ local(carrierCheck.checkedAt) }}</span>
            </div>
            <div v-if="carrierCheck.events && carrierCheck.events.length" class="divide-y divide-stone-100 max-h-[200px] overflow-y-auto">
              <div v-for="(e, i) in carrierCheck.events" :key="i" class="px-3 py-1.5 flex items-start gap-2 text-[11.5px]">
                <span class="font-mono text-stone-400 tabular-nums flex-shrink-0" dir="ltr">{{ local(e.at).slice(5) }}</span>
                <span class="text-stone-800 flex-1 min-w-0" dir="auto">{{ e.text }}</span>
                <span class="text-stone-400 truncate max-w-[140px]">{{ e.who }}</span>
              </div>
            </div>
          </div>
          <ol class="flex items-start justify-between gap-1" dir="ltr">
            <li v-for="(st, i) in JSTEPS" :key="st.key" class="flex-1 min-w-0 text-center">
              <div class="flex items-center">
                <span class="h-px flex-1" :class="i && jReached >= i ? 'bg-teal-300' : i ? 'bg-stone-200' : ''" />
                <span class="w-3 h-3 rounded-full flex-shrink-0" :class="jReached >= i ? 'bg-teal-500' : (journey.row.late && jReached + 1 === i ? 'bg-rose-500' : 'bg-stone-200')" />
                <span class="h-px flex-1" :class="i < JSTEPS.length - 1 && jReached > i ? 'bg-teal-300' : i < JSTEPS.length - 1 ? 'bg-stone-200' : ''" />
              </div>
              <div class="text-[10px] font-semibold mt-1 truncate" :class="jReached >= i ? 'text-stone-800' : 'text-stone-400'">{{ t('oclk.' + st.label) }}</div>
              <div class="text-[10px] tabular-nums text-stone-400 truncate">{{ local(journey.row[st.at] || '').slice(5) || '—' }}</div>
            </li>
          </ol>
          <div v-if="journey.row.dueAt" class="mt-3 flex items-center gap-2 text-[11.5px] rounded-lg px-2.5 py-1.5" :class="journey.row.late ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700'">
            <Icon :name="journey.row.late ? 'alert-triangle' : 'clock'" :size="13" />
            <span>{{ t('od.journeyPromise') }} <b dir="ltr">{{ local(journey.row.dueAt).slice(5) }}</b></span>
            <span class="ms-auto font-bold tabular-nums" dir="ltr">{{ jRemain }}</span>
          </div>
          <!-- the whole story of this parcel, newest first -->
          <JourneyTimeline v-if="journey.timeline && journey.timeline.length" class="mt-4" :timeline="journey.timeline" />
          <div v-if="journey.docs" class="mt-3 flex flex-wrap gap-1.5 text-[10.5px] font-mono">
            <span v-for="p in journey.docs.pickLists" :key="p" class="rounded px-1.5 py-0.5 bg-amber-50 text-amber-700 ring-1 ring-amber-200">{{ p }}</span>
            <span v-for="d in journey.docs.deliveryNotes" :key="d.name" class="rounded px-1.5 py-0.5 bg-violet-50 text-violet-700 ring-1 ring-violet-200" :title="d.docstatus ? '' : 'draft'">{{ d.name }}<span v-if="!d.docstatus"> ·draft</span></span>
            <span v-for="sh in journey.docs.shipments" :key="sh" class="rounded px-1.5 py-0.5 bg-sky-50 text-sky-700 ring-1 ring-sky-200">{{ sh }}</span>
          </div>
        </div>

        <!-- Logistics activity (real audit trail) -->
        <div v-if="isLive" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center justify-between mb-4">
            <div class="text-[13px] font-semibold text-stone-900">{{ t("od.activity") }}</div>
            <button
              class="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-[11.5px] font-medium text-stone-600 bg-stone-50 ring-1 ring-stone-200 hover:bg-stone-100 transition-colors"
              @click="noteOpen = !noteOpen"
            ><Icon name="message-circle" :size="13" />{{ t("od.addNote") }}</button>
          </div>

          <!-- compose box -->
          <div v-if="noteOpen" class="mb-4">
            <textarea
              v-model="noteText"
              :placeholder="t('od.notePh')"
              rows="2" maxlength="1000" dir="auto"
              class="w-full px-3 py-2 rounded-lg bg-stone-50 ring-1 ring-stone-200 text-[12.5px] focus:outline-none focus:ring-stone-400 resize-y"
            />
            <div class="flex items-center justify-end gap-2 mt-1.5">
              <button class="h-8 px-3 rounded-lg text-[12px] font-medium text-stone-500 hover:text-stone-800"
                      @click="noteOpen = false; noteText = ''">{{ t('common.cancel') }}</button>
              <button class="h-8 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50"
                      :disabled="!noteText.trim() || savingNote" @click="saveNote">{{ t('od.postNote') }}</button>
            </div>
          </div>

          <div v-if="!activityEvents.length && !noteOpen" class="text-[12px] text-stone-400 py-2">{{ t("od.noActivity") }}</div>
          <ol v-else-if="activityEvents.length" class="relative">
            <li v-for="(e, i) in activityEvents" :key="i" class="relative flex gap-3 pb-3.5 last:pb-0">
              <span v-if="i < activityEvents.length - 1" class="absolute top-6 w-px left-[11px] bg-stone-200" style="bottom:0" />
              <span class="relative z-10 w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                    :style="{ background: actMeta(e.kind).hex + '18', color: actMeta(e.kind).hex }">
                <Icon :name="actMeta(e.kind).icon" :size="12" />
              </span>
              <div class="min-w-0 flex-1">
                <div class="flex items-center justify-between gap-2">
                  <span class="text-[12.5px] font-medium text-stone-900 truncate">{{ e.title }}</span>
                  <span class="text-[11px] text-stone-400 tabular-nums flex-shrink-0">{{ e.when }}</span>
                </div>
                <div class="flex items-start gap-1.5 mt-0.5 min-w-0">
                  <span class="text-[10.5px] font-semibold text-stone-500 bg-stone-100 rounded px-1.5 py-px flex-shrink-0">{{ actorShort(e.actor) }}</span>
                  <span v-if="e.detail" class="text-[11px] text-stone-500 leading-snug line-clamp-2 min-w-0">{{ e.detail }}</span>
                </div>
              </div>
            </li>
          </ol>
        </div>

        <!-- Carrier / tracking -->
        <div v-if="order.awb" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center justify-between mb-3">
            <div class="text-[13px] font-semibold text-stone-900">{{ CARRIER }}</div>
            <span
              v-if="order.track"
              class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 bg-stone-100 text-stone-600 ring-stone-200 whitespace-nowrap"
            >
              <span class="w-1.5 h-1.5 rounded-full bg-stone-400" /> {{ TRACK_LABEL[order.track] || order.track }}
            </span>
          </div>
          <div class="space-y-1.5 text-[12px]">
            <div class="flex items-center justify-between gap-2"><span class="text-stone-400">{{ t("od.trackingNo") }}</span><span class="font-mono font-medium text-stone-800">{{ (isLive && liveOrder.tracking_number) || order.awb }}</span></div>
            <div class="flex items-center justify-between gap-2"><span class="text-stone-400">{{ t("od.awb") }}</span><span class="font-mono font-medium text-stone-800">{{ order.awb }}</span></div>
            <div v-if="(isLive && liveOrder.dn) || order.dn" class="flex items-center justify-between gap-2"><span class="text-stone-400">{{ t("od.deliveryNote") }}</span><span class="font-mono font-medium text-stone-800">{{ (isLive && liveOrder.dn) || order.dn }}</span></div>
            <div v-if="!isLive" class="flex items-center justify-between gap-2"><span class="text-stone-400">{{ t("od.zone") }}</span><span class="font-mono font-medium text-stone-800">{{ order.zone }}</span></div>
          </div>
          <component
            :is="isLive && liveOrder.tracking_url ? 'a' : 'button'"
            v-bind="isLive && liveOrder.tracking_url ? { href: liveOrder.tracking_url, target: '_blank' } : { disabled: isLive }"
            class="w-full mt-2 flex items-center justify-center gap-1.5 h-8 rounded-lg ring-1 ring-stone-200 hover:ring-stone-300 text-[12px] font-medium text-stone-700 disabled:opacity-40"
          >
            <Icon name="truck" :size="13" /> {{ t("od.trackLive") }}
          </component>
        </div>

        <!-- Linked ERPNext documents -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-2">
          <div class="px-2 py-2">
            <div class="text-[13px] font-semibold text-stone-900">{{ t("od.linkedDocs") }}</div>
            <div class="text-[11.5px] text-stone-400 mt-0.5">{{ t("od.docChain") }}</div>
          </div>
          <component
            v-for="(c, i) in docChain"
            :key="i"
            :is="c.on && c.href ? 'a' : 'button'"
            v-bind="c.on && c.href ? { href: c.href, target: '_blank' } : { disabled: !c.on }"
            class="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-start"
            :class="c.on ? 'hover:bg-stone-50' : 'opacity-40 cursor-not-allowed'"
          >
            <span
              class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
              :class="c.on ? 'bg-[var(--accent-50)] text-[var(--accent-700)]' : 'bg-stone-100 text-stone-400'"
            >
              <Icon :name="c.icon" :size="13" />
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-[10px] text-stone-400 uppercase tracking-wide">{{ c.dt }}</div>
              <div class="font-mono text-[12px] font-medium text-stone-800 truncate">{{ c.id }}</div>
            </div>
            <Icon v-if="c.on" name="arrow-right" :size="12" class="text-stone-300 flex-shrink-0" />
          </component>
        </div>
      </div>

      <!-- ── Customer service ────────────────────────────────────────────
           The complaint history belongs ON the order, where all eight roles
           already look, not only inside a desk seven of them cannot open.
           It also answers "has anyone reported this already?", which is the
           question that stops the same problem being handed over twice. -->
      <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="flex items-center gap-2">
          <Icon name="message-circle" :size="14" class="text-violet-600" />
          <h3 class="text-[12.5px] font-bold text-stone-800">{{ t('od.csTitle') }}</h3>
          <span v-if="csRows.length" class="ms-auto text-[11px] text-stone-400 tabular-nums">{{ csRows.length }}</span>
        </div>

        <div v-if="csRows.length" class="space-y-2">
          <div v-for="r in csRows" :key="r.name"
               class="rounded-xl ring-1 p-2.5"
               :class="r.state === 'done' ? 'bg-stone-50 ring-stone-200/70' : 'bg-violet-50/60 ring-violet-200'">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[10px] font-bold rounded-full px-1.5 py-0.5 ring-1"
                    :class="r.state === 'done' ? 'text-stone-600 bg-white ring-stone-200' : 'text-violet-700 bg-white ring-violet-200'">
                {{ t('cs.k_' + r.kind) }}</span>
              <span class="text-[11px] font-semibold"
                    :class="r.state === 'done' ? 'text-stone-500' : 'text-violet-800'">
                {{ t('cs.tab_' + (r.state === 'done' ? 'done' : r.state === 'new' ? 'new' : 'waiting')) }}</span>
              <!-- Named, because "waiting on the team" told nobody which. -->
              <span v-if="r.waitTeam" class="text-[10.5px] text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-full px-1.5 py-0.5">
                {{ t('cs.team_' + r.waitTeam) }}</span>
              <span class="ms-auto text-[10.5px] text-stone-400 tabular-nums" dir="ltr">{{ local(r.at).slice(5, 16) }}</span>
            </div>
            <div v-if="r.note" class="text-[12px] text-stone-700 mt-1 whitespace-pre-line" dir="auto">{{ r.note }}</div>
            <div class="text-[10.5px] text-stone-400 mt-0.5">
              {{ t('od.csBy').replace('{who}', r.by).replace('{from}', r.from ? t('rl.' + r.from) : '—') }}
            </div>
            <div v-if="r.resolution" class="mt-1.5 pt-1.5 border-t border-stone-200/70">
              <div class="text-[12px] text-emerald-800" dir="auto">{{ r.resolution }}</div>
              <div class="text-[10.5px] text-stone-400">{{ r.closedBy }} · {{ local(r.closedAt).slice(5, 16) }}</div>
            </div>
          </div>
        </div>
        <div v-else class="text-[11.5px] text-stone-400">{{ t('od.csNone') }}</div>

        <CsHandover :order="props.name" :phone="phone" :live="csLive"
                    :source="myRole === 'tracking' ? 'tracking' : myRole === 'confirmation' ? 'confirmation' : ''"
                    @done="loadCs" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { RouterLink, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { local } from "@/lib/clock";
import JourneyTimeline from "@/components/JourneyTimeline.vue";
import CsHandover from "@/components/CsHandover.vue";
import {
  ORDERS, CHANNELS, STAGE, SLA, STAGE_LABEL, SLA_LABEL, TRACK_LABEL,
  byId, fmtMAD, CARRIER, CITY, WAREHOUSE, MANIFEST,
} from "@/lib/handoffData";
import { api, apiPost, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useAuth } from "@/composables/useAuth";
import { useToast } from "@/composables/useToast";
import { useSkuLink } from "@/composables/useSkuLink";

const { t } = useI18n();

// ── Real logistics activity feed (Version log + comments + doc events) ──
const activityEvents = ref([]);

// ── Add a note — the ERPNext comment box, from the portal ──
const { success, warn } = useToast();
const noteOpen = ref(false);
const noteText = ref("");
const savingNote = ref(false);
async function saveNote() {
  const text = noteText.value.trim();
  if (!text) return;
  savingNote.value = true;
  try {
    const res = await apiPost("orders.add_note", { name: props.name, text });
    // Show it immediately at the top of the feed — same shape the API returns.
    activityEvents.value = [
      { when: res.when, kind: "comment", title: "Comment", detail: text,
        actor: res.actor },
      ...activityEvents.value,
    ];
    noteText.value = "";
    noteOpen.value = false;
    success(t("od.noteSaved"));
  } catch (e) {
    warn(t("od.noteFail"), String(e.message || e));
  } finally {
    savingNote.value = false;
  }
}
const ACT_META = {
  submit: { icon: "check-circle", hex: "#10b981" },
  status: { icon: "git-branch", hex: "#7c3aed" },
  sales: { icon: "user", hex: "#d97706" },
  track: { icon: "truck", hex: "#0891b2" },
  awb: { icon: "tag", hex: "#4f46e5" },
  picker: { icon: "users", hex: "#0284c7" },
  comment: { icon: "message-circle", hex: "#78716c" },
  pl: { icon: "package", hex: "#7c3aed" },
  dn: { icon: "file-text", hex: "#78716c" },
  sh: { icon: "truck", hex: "#059669" },
  ret: { icon: "rotate-ccw", hex: "#e11d48" },
};
function actMeta(kind) { return ACT_META[kind] || { icon: "info", hex: "#78716c" }; }
function actorShort(actor) {
  const MAP = { marouaneelmessaoudi07: "Marouane", mouakkalanass: "Anass", asmaazirary7: "Asmaa",
    lamdanisaad12: "Saad", ossamanahila: "Oussama", saidnakri65: "Said", redazaari47: "Reda",
    Administrator: "System" };
  const k = (actor || "").split("@")[0];
  return MAP[k] || MAP[actor] || k;
}

const props = defineProps({
  name: { type: String, required: true },
});

const router = useRouter();
// Same set cs._gate() accepts; anyone else gets a link that only throws.
const { role: myRole } = useAuth();
const canSeeCustomer = computed(() =>
  ["cs", "confirmation", "tracking", "manager"].includes(myRole.value));
const openSku = useSkuLink();
function goBack() {
  // Return to the list the order was opened from (Orders / Consolidation /
  // Stranded …), remembered by the router guard. Fall back to browser history,
  // then to the Orders board — never the role's home.
  let ref = "";
  try { ref = sessionStorage.getItem("lp_order_ref") || ""; } catch (_) { /* private mode */ }
  const here = router.currentRoute.value.fullPath;
  if (ref && ref !== here) { router.push(ref); return; }
  if (window.history.length > 1) { router.back(); return; }
  router.push({ name: "Pipeline" });
}

const STAGE_SEQ = ["pending", "picking", "picked", "labelgen", "label", "shipped", "transit", "exception", "delivered", "returned"];

// Raw ERPNext status string → screen stage key.
const RAW_STAGE = {
  "Pending": "pending", "Picked": "picked", "In transit": "transit",
  "Received": "labelgen", "Label Generated": "labelgen", "Label Printed": "label",
  "Shipped": "shipped", "Delivered": "delivered", "Returned": "returned",
};

// Normalize a live tracking status to a TRACK_LABEL key when possible.
function normTrack(ts) {
  if (!ts) return null;
  const k = String(ts).toLowerCase().replace(/[\s_-]+/g, "");
  return TRACK_LABEL[k] ? k : String(ts);
}

// "2026-07-04 10:23:45" → "10:23"; anything else passes through.
function fmtTs(ts) {
  const m = String(ts || "").match(/(\d{1,2}):(\d{2})/);
  return m ? `${m[1].padStart(2, "0")}:${m[2]}` : String(ts || "—");
}

// The parcel's clock, as the tracking board reads it (shipments.journey).
const journey = ref(null);
const JSTEPS = [
  { key: "confirmed", label: "stConfirmed", at: "confirmedAt" }, { key: "picked", label: "stPicked", at: "pickedAt" },
  { key: "closed", label: "stClosed", at: "closedAt" }, { key: "carrier", label: "stCarrier", at: "handedAt" },
  { key: "door", label: "stDoor", at: "deliveredAt" },
];
const JREACHED = { to_pick: 0, picking: 1, to_hand_over: 2, with_carrier: 3, delivered: 4, failed: 3 };
const JSTAGE_CLS = {
  to_pick: "bg-rose-50 text-rose-700", picking: "bg-amber-50 text-amber-700", to_hand_over: "bg-violet-50 text-violet-700",
  with_carrier: "bg-sky-50 text-sky-700", delivered: "bg-emerald-50 text-emerald-700", failed: "bg-rose-100 text-rose-800",
};
const jReached = computed(() => JREACHED[journey.value?.row?.stage] ?? 0);
const jRemain = computed(() => {
  const r = journey.value?.row; if (!r) return "";
  const m = Math.abs(r.lateMin || 0), h = Math.floor(m / 60);
  const txt = h >= 48 ? Math.floor(h / 24) + t("oclk.dShort") : h + t("oclk.hShort");
  return (r.late ? "+" : "") + txt;
});

// Ask the carrier about this parcel now (same write path as the webhook).
const checking = ref(false);
const carrierCheck = ref(null);
async function checkCarrier() {
  checking.value = true;
  try {
    const res = await apiPost("carrier_sync.check_parcel", { order: props.name });
    carrierCheck.value = res;
    if (res.ok) {
      success(t("trk.carrierSays"), res.carrierStatus || res.status || "");
      api("shipments.journey", { order: props.name }).then((j) => { if (j && j.found) journey.value = j; }).catch(() => {});
    } else {
      warn(t("trk.noTracking"), props.name);
    }
  } catch (e) {
    warn(t("trk.checkFail"), String(e.message || e));
  } finally {
    checking.value = false;
  }
}

// Live order from `orders.detail`; demo/fabricated data stays as fallback.
const liveOrder = ref(null);
const csRows = ref([]);
const csLive = ref(0);
async function loadCs() {
  try {
    const r = await api("cs.for_order", { order: props.name });
    csRows.value = r.rows || [];
    csLive.value = r.live || 0;
  } catch (_) { /* the order screen must render without the desk */ }
}

onMounted(async () => {
  loadCs();
  api("shipments.journey", { order: props.name }).then((j) => { if (j && j.found) journey.value = j; }).catch(() => {});
  liveOr(null, () => api("orders.activity", { name: props.name })).then((ev) => {
    if (Array.isArray(ev) && ev.length) activityEvents.value = ev;
  });
  const live = await liveOr(null, () => api("orders.detail", { name: props.name }));
  if (live && live.name) {
    liveOrder.value = live;
    if (Array.isArray(live.items) && live.items.length) {
      liveItems.value = live.items.map((it) => ({
        sku: it.sku, realSku: it.real_sku || "", name: it.name || it.sku, bin: it.bin || "—",
        qty: it.qty || 1, price: it.price || 0, line: it.line || 0,
        image: it.image || "",
      }));
    }
  }
});

// Build the order by matching no (with/without '#'), fallback to a sensible object.
const order = computed(() => {
  const q = String(props.name || "");
  const found = ORDERS.find(
    (o) => o.no === q || o.no === "#" + q || o.no.replace(/^#/, "") === q.replace(/^#/, "")
  );
  const base = found || {
    no: q.startsWith("#") || /^\d+$/.test(q) ? q : q,
    channel: "shopify", customer: "Khadija abhaoui", total: 349, items: 1,
    stage: "label", sla: "ontrack", bin: "J7C - JM", zone: "FAST ZONE - JM",
    picker: "marouane", mins: 40, awb: "LD007706673", dn: "MAT-DN-2026-74477",
    track: "pending", city: "Casablanca",
  };
  const live = liveOrder.value;
  if (!live || !live.name) return base;
  return {
    ...base,
    no: live.name || base.no,
    customer: live.customer || base.customer || "—",
    channel: live.channel || base.channel,
    total: live.total != null ? live.total : base.total,
    stage: RAW_STAGE[live.stage] || base.stage,
    // live orders NEVER inherit demo docs — absence is real information
    awb: live.awb || "",
    dn: live.dn || "",
    track: normTrack(live.tracking_status) || "",
    city: live.city || "",
    picker: "",
  };
});

const channelBadge = computed(() => {
  const c = CHANNELS[order.value.channel] || CHANNELS.shopify;
  const toneMap = {
    emerald: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    violet: "bg-violet-50 text-violet-700 ring-violet-200",
    amber: "bg-amber-50 text-amber-700 ring-amber-200",
    slate: "bg-stone-100 text-stone-600 ring-stone-200",
    green: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  };
  return { label: c.label, cls: toneMap[c.tone] || toneMap.slate };
});

const stageBadge = computed(() => {
  const s = STAGE[order.value.stage] || STAGE.pending;
  return { label: t("od.stageL." + order.value.stage, STAGE_LABEL[order.value.stage] || order.value.stage), cls: `${s.bg} ${s.txt} ${s.ring}`, dot: s.dot };
});

const slaBadge = computed(() => {
  let key = order.value.sla;
  if (isLive.value) {
    const lv = liveOrder.value, st = order.value.stage;
    if (st === "delivered") key = "ontrack";
    else if (st === "returned") key = "returned";
    else if (["Delivery Exception", "Failed Attempt"].includes(lv.tracking_status)) key = "late";
    else if (["shipped", "transit"].includes(st)) key = "ontrack";
    else {
      // pre-carrier: same-day cutoff logic on the real creation time
      const created = new Date(String(lv.created || "").replace(" ", "T"));
      const cut = new Date(); cut.setHours(14, 0, 0, 0);
      const day0 = new Date(); day0.setHours(0, 0, 0, 0);
      key = (created < day0 || (created < cut && new Date() > cut)) ? "breached" : "ontrack";
    }
  }
  const s = SLA[key] || SLA.ontrack;
  return { label: t("sla." + ({ ontrack: "onTrack", atrisk: "atRisk", breached: "breached", late: "late", returned: "returned" }[key] || key), SLA_LABEL[key] || key), cls: `${s.bg} ${s.txt} ${s.ring}`, dot: s.dot };
});

// ── Line items (deterministic, mirrors genLineItems) ──────────────────
const liveItems = ref([]);
const isLive = computed(() => !!liveOrder.value);
const items = computed(() => {
  if (liveItems.value.length) return liveItems.value;
  const o = order.value;
  const names = [
    ["MCH100013", "Diffuseur huile MCH — box", o.bin],
    ["CSM44021", "Sérum éclat 30ml", "I4A - JM"],
    ["ACC11008", "Trousse maquillage zip", "H14A - JM"],
    ["MUZ22014", "Palette ombres MU", "H13B - JM"],
  ];
  const n = Math.max(1, Math.min(o.items, 4));
  const per = Math.round(o.total / n);
  return Array.from({ length: n }).map((_, i) => {
    const [sku, name, bin] = names[i % names.length];
    const qty = i === 0 && n < o.items ? o.items - (n - 1) : 1;
    const price = i === n - 1 ? o.total - per * (n - 1) : per;
    return { sku, name, bin, qty, price: Math.max(1, Math.round(price / qty)), line: Math.max(1, price) };
  });
});

const nseed = computed(() => parseInt((order.value.no.match(/\d+/) || [12])[0]));
// Money: authoritative ERPNext numbers when live; derived only in preview.
const subtotal = computed(() =>
  isLive.value ? (liveOrder.value.subtotal ?? 0) : items.value.reduce((a, it) => a + it.line, 0));
const shipping = computed(() => (isLive.value ? 0 : [0, 0, 25, 30][nseed.value % 4]));
const discount = computed(() =>
  isLive.value ? (liveOrder.value.discount || 0) : (nseed.value % 5 === 0 ? 20 : 0));
const tax = computed(() =>
  isLive.value ? (liveOrder.value.taxes || 0)
    : Math.round((subtotal.value + shipping.value - discount.value) * 0.05));
const grand = computed(() =>
  isLive.value ? (liveOrder.value.total ?? 0)
    : subtotal.value + shipping.value - discount.value + tax.value);
const phone = computed(() =>
  isLive.value ? (liveOrder.value.phone || "—")
    : `+212 6${String(nseed.value % 10)}${String((nseed.value * 7) % 90 + 10)} ${String((nseed.value * 13) % 900 + 100)}`);
const govern = computed(() =>
  isLive.value ? (liveOrder.value.governorate || "—")
    : ["Casablanca-Settat", "Rabat-Salé-Kénitra", "Tanger-Tétouan", "Marrakech-Safi"][nseed.value % 4]);
const refNo = computed(() =>
  isLive.value ? (liveOrder.value.ref || liveOrder.value.name)
    : `${order.value.channel === "shopify" ? "#" : order.value.channel === "youcan" ? "YC" : "REF"}${4400 + nseed.value % 600}`);
const codPending = computed(() =>
  isLive.value ? (liveOrder.value.payment_collection !== "Fully Received"
                  && order.value.stage !== "delivered")
    : order.value.stage !== "delivered");
// Ship-to destination line — real city/address when live (never the demo zone).
const shipToLine = computed(() => {
  if (!isLive.value) return (order.value.city || "Casablanca") + " · " + order.value.zone.replace(" - JM", "");
  const lv = liveOrder.value;
  return [lv.city || "—", lv.address_line].filter(Boolean).join(" · ");
});
// Header sales-status badge — real custom_sales_status.
const salesBadge = computed(() => {
  const s = isLive.value ? (liveOrder.value.sales_status || "—") : "Confirmed";
  const map = {
    Confirmed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    Cancelled: "bg-rose-50 text-rose-700 ring-rose-200",
    "On Hold": "bg-amber-50 text-amber-700 ring-amber-200",
  };
  return { label: t("od.salesStatus." + s, "Sales " + s.toLowerCase()), cls: map[s] || "bg-stone-100 text-stone-600 ring-stone-200" };
});

// ── Order lifecycle timeline (ported from orderTimeline) ──────────────
const timeline = computed(() => {
  const o = order.value;
  if (!o) return [];
  const idx = STAGE_SEQ.indexOf(o.stage);
  const pk = byId(o.picker)?.short;
  const fmt = (h, m) => `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  let h = 8, m = (parseInt((o.no.match(/\d+/) || [7])[0]) % 5) * 9 + 4;
  const step = () => { m += 17 + (idx % 6); if (m >= 60) { h += 1; m -= 60; } return fmt(h, m); };
  const all = [
    { key: "confirmed", label: "Order confirmed",     actor: "Sales · " + o.channel, doc: o.no, reached: 0 },
    { key: "picking",   label: "Pick list assigned",  actor: pk || "Dispatcher",    doc: "PL-51433", reached: 1 },
    { key: "picked",    label: "Picked & scanned",    actor: pk || "—",             doc: "PL-51433", reached: 2 },
    { key: "labelgen",  label: "Label generated",     actor: "Reda · Cathedis API", doc: o.awb || "AWB", reached: 3 },
    { key: "label",     label: "Label printed",       actor: "Reda",                doc: o.awb || "AWB", reached: 4 },
    { key: "shipped",   label: "On manifest",         actor: "Reda",                doc: MANIFEST.no, reached: 5 },
    { key: "transit",   label: "Picked up by carrier",actor: "Cathedis",            doc: o.awb || "AWB", reached: 6 },
    { key: "oos",       label: "Out of stock — blocked", actor: pk || "—",          doc: o.bin, reached: 2, bad: true },
    { key: "exception", label: o.track === "failed" ? "Failed attempt" : "Delivery exception", actor: "Cathedis", doc: o.awb || "AWB", reached: 7, bad: true },
    { key: "delivered", label: "Delivered",           actor: "Cathedis",            doc: o.awb || "AWB", reached: 8 },
    { key: "returned",  label: "Returned",            actor: "Cathedis",            doc: o.awb || "AWB", reached: 9, bad: true },
  ];
  const isException = o.stage === "exception";
  const isOos = o.stage === "oos";
  // Live timestamps (from orders.detail) win over the fabricated clock.
  const lv = liveOrder.value;
  const liveAt = lv ? {
    picked: lv.picked_at, labelgen: lv.labeled_at, label: lv.labeled_at,
    shipped: lv.shipped_at, delivered: lv.delivered_at,
  } : {};
  return all
    .filter((e) => {
      if (e.key === "oos") return isOos;
      if (isOos) return e.reached <= 1;
      if (e.key === "exception") return isException;
      if (e.key === "returned") return o.stage === "returned";
      if (e.key === "delivered") return idx >= 8 && o.stage !== "returned";
      return e.reached <= idx || (isException && e.reached <= 6);
    })
    .map((e) => {
      const fake = step();
      return { ...e, at: liveAt[e.key] ? fmtTs(liveAt[e.key]) : fake, done: true };
    });
});

// ── Documents ─────────────────────────────────────────────────────────
const documents = computed(() => {
  const o = order.value;
  const lv = liveOrder.value || {};
  return [
    { label: t("od.awbLabel"), icon: "tag", on: !!o.awb, href: lv.label_url || "" },
    { label: t("od.packingSlip"), icon: "file-text", on: !isLive.value },
    { label: t("od.invoice"), icon: "file-text", on: !isLive.value && o.stage !== "pending" },
  ];
});

// ── Linked ERPNext doc chain ──────────────────────────────────────────
function deskUrl(dt, id) {
  return `/app/${dt.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(id)}`;
}
const docChain = computed(() => {
  const o = order.value;
  if (isLive.value) {
    const lv = liveOrder.value;
    const row = (dt, id, icon) => ({ dt, id: id || "—", on: !!id, icon,
      href: id ? deskUrl(dt, id) : "" });
    return [
      row("Sales Order", lv.name, "shopping-bag"),
      row("Pick List", lv.pl, "package"),
      row("Delivery Note", lv.dn, "file-text"),
      row("Shipment", lv.sh, "send"),
      row("Return Shipment", lv.ret, "rotate-ccw"),
    ];
  }
  const idx = STAGE_SEQ.indexOf(o.stage);
  return [
    { dt: "Sales Order",   id: o.no, on: true, icon: "shopping-bag" },
    { dt: "Pick List",     id: "PL-51433", on: idx >= 1, icon: "package" },
    { dt: "Delivery Note", id: o.dn || "—", on: !!o.dn, icon: "file-text" },
    { dt: "Shipment",      id: idx >= 5 ? MANIFEST.no : "—", on: idx >= 5, icon: "send" },
  ];
});
</script>
