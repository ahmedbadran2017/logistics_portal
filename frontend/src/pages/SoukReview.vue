<template>
  <!-- Review & publish (1 day, never by the writer). The system checks what
       it can measure — a photo per colour, price above the cost with
       transport, weights, Shopify's quantity = what ee pushes from Next,
       vendor = house brand, French colour names; the reviewer ticks what only
       an eye sees. "Check again" reloads the system checks and KEEPS the
       ticks and the channels (they reset only on another product). Send back
       to the step that owns the problem (counted), drop it, or publish:
       channels → ACTIVE → studio samples back on the shelf → the next card
       in the queue opens. Look = the souk stage system: an indigo hero (clock
       bar + Publish), the storefront preview, then system checks, eye
       checks, channels + publish, and the send-back flow as sk-sec cards.
       Backend: souk.review_boot / review_reject / review_drop / publish /
       qty_nudge. -->
  <div class="st-review px-4 sm:px-5 pt-5 sm:pt-6 max-w-[1320px] mx-auto flex flex-col gap-4" :class="hasFooter ? 'pb-28 lg:pb-10' : 'pb-10'">
    <!-- ── hero: the product, its clock, the one next step ──────────────── -->
    <header v-if="d" class="sk-hero flex-col gap-3.5" :class="listOnly ? 'hidden lg:flex' : 'flex'">
      <router-link v-if="data && !listOnly" :to="{ name: 'SoukReview' }"
                   class="lg:hidden self-start lp-tap h-9 -mt-1 ps-1.5 pe-3 rounded-full bg-white/80 ring-1 ring-inset ring-stone-200 inline-flex items-center gap-1 text-[13px] font-semibold text-stone-700">
        <Icon name="chevron-left" :size="16" class="rtl:rotate-180" />{{ t('souk.pub.backToQueue') }} · {{ data.queue.length }}
      </router-link>
      <div class="flex gap-3 items-start">
        <span class="sk-ico sk-ico-lg sk-ico-solid"><Icon name="clipboard-check" :size="20" :stroke-width="2" /></span>
        <div class="min-w-0 flex-1 flex flex-col gap-1">
          <span class="text-[12px] font-semibold st-ink">
            {{ t('souk.pub.reviewKicker').replace('{w}', d.writer || '—').replace('{r}', reviewerName) }}<template v-if="!d.sameWriter"> · <span class="font-normal text-stone-600">{{ t('souk.pub.oneEach') }}</span></template>
          </span>
          <h1 class="text-[19px] sm:text-[22px] font-extrabold text-stone-900 leading-tight break-words">{{ d.content.fr.title || d.title }}</h1>
          <span v-if="d.rejects" class="self-start inline-flex items-center gap-1 h-6 px-2 rounded-full bg-amber-50 text-amber-800 text-[12px] font-bold">
            <Icon name="undo-2" :size="12" />{{ t('souk.returnedN').replace('{n}', d.rejects) }}
          </span>
        </div>
      </div>

      <!-- time in this step against the limit; rose once late -->
      <div v-if="clock" class="flex flex-wrap items-center gap-x-2.5 gap-y-1.5 bg-white/80 rounded-xl px-3 py-2 ring-1 ring-inset ring-[rgb(var(--st)/.18)]">
        <Icon :name="clock.late ? 'alert-triangle' : 'clock'" :size="15" :class="clock.late ? 'text-rose-600' : 'st-fg'" class="shrink-0" />
        <span class="text-[13px] font-semibold tabular-nums" :class="clock.late ? 'text-rose-700' : 'text-stone-800'">{{ clock.text }}</span>
        <div v-if="clock.limit" class="flex-1 h-1.5 rounded-full bg-stone-200 overflow-hidden min-w-[80px]">
          <div class="h-full rounded-full" :class="clock.late ? 'bg-rose-500' : 'st-solid'" :style="{ width: Math.min(100, clock.pct) + '%' }" />
        </div>
        <span v-if="dueText" class="text-[12px] text-stone-600 tabular-nums" dir="auto">{{ dueText }}</span>
      </div>

      <!-- the one next step (a phone keeps it in the footer), the rest quiet -->
      <div class="flex flex-wrap items-center gap-2">
        <button v-if="d.stage === 'review'" class="hidden lg:inline-flex btn btn-st" :disabled="busy || !canPublish" :title="canPublish ? publishSub : blockedWhy" @click="publish">
          <Icon name="zap" :size="15" :stroke-width="2.2" />{{ busy ? t('souk.sending') : t('souk.publish') }}
        </button>
        <a v-if="d.shopify && d.shopify.preview" :href="d.shopify.preview" target="_blank" rel="noopener" class="btn btn-line">
          <Icon name="eye" :size="14" />{{ t('souk.previewSite') }}<Icon name="external-link" :size="12" class="opacity-60" />
        </a>
        <a v-if="d.shopifyAdmin" :href="d.shopifyAdmin" target="_blank" rel="noopener" class="btn btn-line">
          <Icon name="shopping-bag" :size="14" />Shopify<Icon name="external-link" :size="12" class="opacity-60" />
        </a>
      </div>
    </header>
    <header v-if="!d || listOnly" class="sk-hero flex gap-3 items-start" :class="d ? 'lg:hidden' : ''">
      <span class="sk-ico sk-ico-lg sk-ico-solid"><Icon name="clipboard-check" :size="20" :stroke-width="2" /></span>
      <div class="min-w-0 flex flex-col gap-0.5">
        <h1 class="text-[19px] sm:text-[22px] font-extrabold text-stone-900 leading-tight">{{ t('souk.reviewTitle') }}</h1>
        <p class="text-[13px] text-stone-600 max-w-[680px]">{{ t('souk.reviewIntro') }}</p>
      </div>
    </header>

    <div v-if="loading && !data" class="h-[420px] rounded-2xl souk-skel" />

    <!-- nothing in the queue: the same card on the three screens -->
    <div v-else-if="data && !data.queue.length && !d" class="sk-sec px-6 py-12 flex flex-col items-center text-center gap-3">
      <span class="sk-ico sk-ico-lg"><Icon name="inbox" :size="22" /></span>
      <p class="text-[14px] font-semibold text-stone-700">{{ t('souk.reviewNone') }}</p>
      <router-link :to="{ name: 'SoukBoard' }" class="btn btn-line">
        {{ t('souk.pub.toBoard') }}<Icon name="arrow-right" :size="14" class="rtl:rotate-180" />
      </router-link>
    </div>

    <template v-else-if="data">
      <!-- the queue: a phone's list view; a strip above the product on a desk -->
      <section v-if="listOnly && data.queue.length" :aria-label="t('souk.pub.queueLbl')" class="lg:hidden sk-sec">
        <div class="sk-sec-h">
          <span class="sk-ico"><Icon name="inbox" :size="16" /></span>
          <div class="min-w-0 flex-1 flex flex-col">
            <h2 class="sk-sec-t">{{ t('souk.pub.queueLbl') }}</h2>
            <span class="sk-sec-s">{{ t('souk.oldestFirst') }}</span>
          </div>
          <span class="shrink-0 min-w-[26px] h-[26px] px-2 rounded-full st-solid text-[13px] font-bold tabular-nums inline-flex items-center justify-center"
                :aria-label="t('souk.nProducts').replace('{n}', data.queue.length)">{{ data.queue.length }}</span>
        </div>
        <router-link v-for="(q, i) in data.queue" :key="q.name" :to="{ name: 'SoukReview', params: { name: q.name } }"
                     class="flex items-center gap-3 px-3.5 py-3 min-h-[72px] hover:bg-stone-50" :class="i ? 'border-t border-stone-100' : ''">
          <img v-if="q.image" :src="q.image" class="w-12 h-12 shrink-0 rounded-xl object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-12 h-12 shrink-0 rounded-xl st-tint st-fg flex items-center justify-center"><Icon name="image" :size="18" /></div>
          <div class="min-w-0 flex-1 flex flex-col gap-0.5">
            <div class="text-[14px] font-semibold truncate ltr:text-left rtl:text-right" dir="auto">{{ q.title }}</div>
            <div class="text-[12px] truncate inline-flex items-center gap-1" :class="q.mine ? 'text-amber-800' : 'text-stone-600'">
              <Icon :name="q.mine ? 'alert-triangle' : 'user'" :size="12" class="shrink-0" />{{ q.mine ? t('souk.youWroteIt') : t('souk.writtenBy').replace('{n}', q.writer || '—') }}
            </div>
          </div>
          <span class="sp-age" :class="q.late ? 'sp-age-late' : 'st-tint st-ink'"><Icon :name="q.late ? 'alert-triangle' : 'clock'" :size="11" />{{ ageText(q.age) }}</span>
          <Icon name="chevron-right" :size="16" class="shrink-0 text-stone-400 rtl:rotate-180" />
        </router-link>
      </section>
      <nav v-if="showStrip" :aria-label="t('souk.pub.queueLbl')" class="hidden lg:flex gap-2 overflow-x-auto pb-0.5">
        <router-link v-for="q in data.queue" :key="q.name" :to="{ name: 'SoukReview', params: { name: q.name } }"
                     class="sp-q" :class="d && d.name === q.name ? 'sp-q-on' : ''" :aria-current="d && d.name === q.name ? 'page' : undefined">
          <img v-if="q.image" :src="q.image" class="w-10 h-10 shrink-0 rounded-lg object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-10 h-10 shrink-0 rounded-lg st-tint st-fg flex items-center justify-center"><Icon name="image" :size="16" /></div>
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-semibold truncate ltr:text-left rtl:text-right" dir="auto">{{ q.title }}</div>
            <div class="text-[12px] truncate" :class="q.mine ? 'text-amber-800' : 'text-stone-600'">{{ q.mine ? t('souk.youWroteIt') : t('souk.writtenBy').replace('{n}', q.writer || '—') }}</div>
          </div>
          <span class="sp-age" :class="q.late ? 'sp-age-late' : 'st-tint st-ink'">{{ ageText(q.age) }}</span>
        </router-link>
      </nav>

      <div v-if="!d" class="hidden lg:flex sk-sec p-8 flex-col items-center gap-3 text-center text-[14px] text-stone-500">
        <span class="sk-ico sk-ico-lg"><Icon name="arrow-up" :size="20" /></span>{{ t('souk.studioPick') }}
      </div>
      <div v-else class="flex flex-col gap-4" :class="listOnly ? 'hidden lg:flex' : ''">
        <div v-if="d.sameWriter" class="bg-amber-50 ring-1 ring-inset ring-amber-200 rounded-2xl px-3.5 py-3 text-[13px] text-amber-800 flex gap-2.5 items-start">
          <Icon name="alert-triangle" :size="16" class="shrink-0 mt-0.5" />{{ t('souk.sameWriter') }}
        </div>
        <div v-if="d.stage !== 'review'" class="bg-stone-100 rounded-2xl px-3.5 py-3 text-[13px] text-stone-700 flex gap-2.5 items-start">
          <Icon name="info" :size="16" class="shrink-0 mt-0.5" />{{ t('souk.reviewNotNow') }}
        </div>

        <div class="flex flex-wrap gap-4 items-start">
          <!-- preview: the storefront page, in the language of the tab -->
          <section :aria-label="t('souk.pub.previewLbl')" class="flex-[999_1_520px] min-w-0 sk-sec">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="eye" :size="16" /></span>
              <div class="min-w-0 flex-1 flex flex-col">
                <h2 class="sk-sec-t">{{ t('souk.pub.previewLbl') }}</h2>
                <span class="sk-sec-s">{{ t('souk.pub.secPreviewSub') }}</span>
              </div>
              <span class="shrink-0 text-[11px] font-bold rounded-full px-2 py-1 bg-white/80 ring-1 ring-inset ring-stone-200 text-stone-600 mono" dir="ltr">{{ (d.shopify && d.shopify.status) || 'DRAFT' }}</span>
            </div>
            <div class="sk-sec-b flex flex-col gap-3">
              <div role="tablist" :aria-label="t('souk.pub.langLbl')" class="self-start inline-flex gap-0.5 p-1 bg-stone-100 rounded-[10px]">
                <button v-for="l in ['fr', 'ar']" :key="l" role="tab" :aria-selected="lang === l"
                        class="h-9 px-3.5 rounded-lg text-[13px] font-semibold inline-flex items-center"
                        :class="lang === l ? 'bg-white shadow-[0_1px_3px_rgba(0,0,0,0.08)] text-stone-900' : 'text-stone-600'" @click="lang = l">
                  {{ l === 'fr' ? t('souk.langFr') : t('souk.langAr') }}
                </button>
              </div>
              <div class="sp-shop flex flex-wrap gap-5 rounded-xl p-4 sm:p-5"
                   :dir="lang === 'ar' ? 'rtl' : 'ltr'" :lang="lang">
                <div class="flex-[1_1_240px] min-w-0 flex flex-col gap-2">
                  <img v-if="mainImg" :src="mainImg" class="w-full aspect-[4/5] object-cover rounded-[10px] bg-[#ece8e1]" alt="" />
                  <div v-else class="w-full aspect-[4/5] rounded-[10px] bg-[#ece8e1]" />
                  <div v-if="d.finals.length > 1" class="grid grid-cols-5 gap-1.5">
                    <button v-for="(f, i) in d.finals" :key="f.url" type="button" class="aspect-square rounded-md overflow-hidden bg-[#ece8e1]"
                            :class="mainImg === f.url ? 'ring-2 ring-[#16130f]' : ''" :aria-label="t('souk.pub.photoN').replace('{n}', i + 1)"
                            :aria-pressed="mainImg === f.url" @click="img = f.url">
                      <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                    </button>
                  </div>
                </div>
                <div class="flex-[1_1_240px] min-w-0 flex flex-col gap-3">
                  <h2 class="text-[20px] font-bold leading-[1.3] break-words">{{ d.content[lang].title || '—' }}</h2>
                  <div class="text-[20px] font-extrabold tabular-nums text-[#c4301c]">
                    {{ priceLine.text }} <span v-if="priceLine.from" class="text-[14px] font-medium text-[#7a746b]">{{ shop('from') }}</span>
                  </div>
                  <div v-if="realColors.length > 1" class="flex flex-col gap-1.5">
                    <span class="text-[13px] font-bold">{{ shop('color') }}{{ lang === 'fr' ? ' : ' : ': ' }}{{ shopColor(realColors[0]) }}</span>
                    <div class="flex gap-2 flex-wrap">
                      <span v-for="(c, i) in realColors" :key="c.code" class="h-8 px-3 rounded-full text-[13px] font-semibold inline-flex items-center"
                            :class="i === 0 ? 'sp-shop-on' : 'ring-1 ring-inset ring-[#e3ddd3]'">{{ shopColor(c) }}</span>
                    </div>
                  </div>
                  <div v-if="sizeRows.length > 1 || (sizeRows[0] && sizeRows[0].size)" class="flex flex-col gap-1.5">
                    <span class="text-[13px] font-bold">{{ shop('size') }}</span>
                    <div class="flex gap-2 flex-wrap">
                      <span v-for="(s, i) in sizeRows" :key="s.size" class="h-[34px] px-3.5 rounded-full text-[13px] font-bold inline-flex items-center tabular-nums"
                            :class="i === 0 ? 'sp-shop-on' : 'ring-1 ring-inset ring-[#e3ddd3]'">{{ s.size }}<template v-if="s.price && Number(s.price) !== priceLine.low"> · {{ s.price }} MAD</template></span>
                    </div>
                  </div>
                  <div class="h-11 rounded-full bg-[#c4301c] text-white text-[15px] font-bold flex items-center justify-center text-center px-3">{{ shop('order') }}</div>
                  <!-- Built server-side from plain text with every character escaped. -->
                  <div class="souk-desc text-[14px] leading-[1.6] text-[#46413a]" v-html="d.descHtml[lang]" />
                </div>
              </div>
              <div v-if="d.content.handle || d.content.metaTitle" class="sp-serp rounded-xl px-3.5 py-3 flex flex-col gap-[3px] min-w-0" dir="ltr" lang="fr" style="font-family: Arial, sans-serif">
                <span class="text-[13px] text-[#3c4043] truncate">justyol.com › products › {{ d.content.handle }}</span>
                <span class="text-[16px] text-[#1a0dab] truncate">{{ d.content.metaTitle }}</span>
                <span class="text-[13px] text-[#4d5156] line-clamp-2">{{ d.content.metaDescription }}</span>
              </div>
            </div>
          </section>

          <aside class="flex-[1_1_320px] lg:max-w-[420px] min-w-0 flex flex-col gap-4">
            <!-- what the system measured -->
            <section class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="list-checks" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.systemChecks') }}</h2>
                  <span class="sk-sec-s tabular-nums" :class="hardFail.length ? '!text-rose-700 font-semibold' : ''">{{ t('souk.pub.passedN').replace('{n}', checksPassed).replace('{m}', d.checks.length) }}</span>
                </div>
                <button class="btn btn-line btn-sm" :disabled="loading" @click="recheck">
                  <Icon name="refresh-cw" :size="13" :class="loading ? 'animate-spin' : ''" />{{ t('souk.recheck') }}
                </button>
              </div>
              <ul class="px-3.5 py-2">
                <li v-for="k in d.checks" :key="k.key" class="flex items-start gap-2.5 py-1.5 text-[13px]">
                  <span class="sp-tick" :class="k.ok ? 'sp-tick-ok' : k.hard ? 'sp-tick-bad' : 'sp-tick-warn'">
                    <Icon :name="k.ok ? 'check' : k.hard ? 'x' : 'alert-triangle'" :size="13" :stroke-width="2.4" />
                  </span>
                  <div class="min-w-0 flex-1 pt-0.5">
                    <div class="flex items-start justify-between gap-2">
                      <span :class="k.ok ? 'text-stone-900' : k.hard ? 'text-rose-700 font-semibold' : 'text-amber-800 font-semibold'">{{ t('souk.rk_' + k.key) }}</span>
                      <span v-if="k.detail && k.detail.length <= 24" class="text-stone-600 tabular-nums text-end shrink-0" dir="ltr">{{ k.detail }}</span>
                    </div>
                    <div v-if="k.detail && k.detail.length > 24" class="text-[12px] text-stone-600 break-words" dir="ltr">{{ k.detail }}</div>
                    <button v-if="k.key === 'qty' && !k.ok" class="lp-tap mt-1 h-8 text-[12px] font-semibold underline st-ink inline-flex items-center gap-1" :disabled="busy" @click="nudge">
                      <Icon name="refresh-cw" :size="12" />{{ t('souk.qtyNudge') }}
                    </button>
                  </div>
                </li>
              </ul>
            </section>

            <!-- what only an eye sees -->
            <section class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="eye" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.eyeChecks') }}</h2>
                  <span class="sk-sec-s tabular-nums">{{ t('souk.pub.tickedN').replace('{n}', ticked.length).replace('{m}', d.manual.length) }}</span>
                </div>
              </div>
              <div class="p-2 flex flex-col gap-1">
                <label v-for="m in d.manual" :key="m" class="sp-eye" :class="ticked.includes(m) ? 'sp-eye-on' : ''">
                  <input v-model="ticked" type="checkbox" :value="m" class="w-5 h-5 shrink-0 accent-[rgb(var(--st))]" :disabled="!d.canPublish" />
                  <span class="min-w-0">{{ t('souk.mk_' + m) }}</span>
                </label>
              </div>
            </section>

            <!-- channels and the publish itself -->
            <section class="sk-sec st-live">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="zap" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.channels') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.channelsDefault') }}</span>
                </div>
                <span class="text-[12px] font-bold st-ink st-tint rounded-full px-2.5 py-1 tabular-nums">{{ chosen.length }}</span>
              </div>
              <div class="p-2 flex flex-col gap-1">
                <div v-if="d.channelsError" class="mx-1.5 my-1 text-[12px] text-rose-700 break-words">{{ d.channelsError }}</div>
                <label v-for="ch in d.channels" :key="ch.id" class="sp-eye" :class="chosen.includes(ch.id) ? 'sp-eye-on' : ''">
                  <input v-model="chosen" type="checkbox" :value="ch.id" class="w-5 h-5 shrink-0 accent-[rgb(var(--st))]" :disabled="!d.canPublish" @change="chosenTouched = true" />
                  <span class="flex-1 min-w-0 break-words" dir="auto">{{ chLabel(ch) }}</span>
                  <span v-if="chNote(ch)" class="max-w-[48%] text-[12px] leading-tight text-stone-600 text-end">{{ chNote(ch) }}</span>
                </label>
              </div>
              <div v-if="d.stage === 'review'" class="px-3.5 pb-3.5 pt-1 flex flex-col gap-2">
                <div class="rounded-xl px-3 py-2.5 text-[12px] flex gap-2 items-start"
                     :class="canPublish ? 'bg-emerald-50 text-emerald-800' : 'bg-stone-100 text-stone-700'">
                  <Icon :name="canPublish ? 'check-circle' : 'info'" :size="14" class="shrink-0 mt-px" />
                  <span class="min-w-0">
                    <template v-if="!canPublish">{{ blockedWhy }}</template>
                    <template v-else><b>{{ t('souk.pub.ready') }}</b> · {{ publishSub }}<template v-if="d.samples.length"> · {{ t('souk.samplesBack').replace('{n}', samplesN) }}</template></template>
                  </span>
                </div>
                <button class="sp-pub hidden lg:flex w-full min-h-[52px] py-1.5 rounded-xl text-[15px] font-bold flex-col items-center justify-center gap-px"
                        :disabled="busy || !canPublish" @click="publish">
                  <span class="inline-flex items-center gap-1.5"><Icon name="zap" :size="15" :stroke-width="2.2" />{{ busy ? t('souk.sending') : t('souk.publish') }}</span>
                  <span class="text-[12px] font-medium opacity-90 tabular-nums">{{ publishSub }}</span>
                </button>
              </div>
            </section>

            <!-- something wrong: back to the step that owns it, or drop it -->
            <section v-if="d.stage === 'review' && !d.sameWriter" class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="undo-2" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.somethingWrong') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.pub.secRejectSub') }}</span>
                </div>
              </div>
              <div class="sk-sec-b flex flex-col gap-3">
                <div role="group" :aria-label="t('souk.pub.toLbl')" class="flex flex-col gap-2">
                  <span class="text-[12px] font-bold text-stone-600">{{ t('souk.pub.toLbl') }}</span>
                  <div class="grid grid-cols-3 gap-2">
                    <button v-for="o in BACK" :key="o.v" type="button" class="sk-pick !min-h-[76px] !text-[12px] leading-tight" :class="'st-' + o.st"
                            :aria-pressed="back === o.v" @click="back = o.v">
                      <span class="sk-ico sk-ico-sm"><Icon :name="o.icon" :size="14" /></span>{{ t('souk.' + o.k) }}
                    </button>
                  </div>
                  <span class="text-[12px] font-bold text-stone-600 mt-1">{{ t('souk.pub.orDrop') }}</span>
                  <div class="grid grid-cols-2 gap-2">
                    <button v-for="o in DROP" :key="o.v" type="button" class="sk-pick st-dropped !min-h-[64px] !text-[12px] leading-tight"
                            :aria-pressed="back === o.v" @click="back = o.v">
                      <span class="sk-ico sk-ico-sm"><Icon :name="o.icon" :size="14" /></span>{{ t('souk.' + o.k) }}
                    </button>
                  </div>
                </div>
                <div class="flex flex-col gap-[5px]">
                  <label for="rv-note" class="text-[13px] font-semibold text-stone-700">{{ t('souk.pub.noteLbl') }}</label>
                  <textarea id="rv-note" v-model="note" rows="3" class="w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-[14px] resize-y" :placeholder="t('souk.noteRequired')" />
                </div>
                <button class="btn w-full bg-white ring-1 ring-inset ring-rose-200 text-rose-700 font-bold enabled:hover:bg-rose-50"
                        :disabled="busy || !note.trim()" @click="sendBack">
                  <Icon :name="back.startsWith('drop') ? 'ban' : 'undo-2'" :size="15" />{{ back.startsWith('drop') ? t('souk.dropIt') : t('souk.pub.returnBtn') }}
                </button>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </template>

    <!-- a phone: the publish stays under the thumb -->
    <div v-if="hasFooter" class="lp-footer lg:hidden px-4 py-3 flex items-center gap-3">
      <span class="flex-1 min-w-0 text-[12px] leading-snug line-clamp-2" :class="canPublish ? 'text-emerald-700 font-semibold' : 'text-stone-600'">
        {{ canPublish ? publishSub : blockedWhy }}
      </span>
      <button class="btn btn-st h-11 px-5" :disabled="busy || !canPublish" @click="publish">
        <Icon name="zap" :size="15" :stroke-width="2.2" />{{ busy ? t('souk.sending') : t('souk.publish') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();
const { fullName } = useAuth();
const route = useRoute();
const router = useRouter();
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const lang = ref("fr");
const img = ref("");
const ticked = ref([]);
const chosen = ref([]);
const chosenTouched = ref(false);
const stateFor = ref(""); // the product the ticks and channels belong to
const back = ref("content");
const note = ref("");
const d = computed(() => data.value?.detail || null);

// The storefront's own words, in the preview's language (not the UI's).
const shop = (k) => t(`souk.pub.shop.${lang.value}.${k}`);
const reviewerName = computed(() => fullName.value || t("souk.pub.you"));
const mainImg = computed(() => img.value || d.value?.finals?.[0]?.url || d.value?.image || "");
const realColors = computed(() => (d.value?.colors || []).filter((c) => c.code));
const sizeRows = computed(() => {
  const out = {};
  for (const v of d.value?.variants || []) {
    const k = v.size || "";
    if (!(k in out)) out[k] = { size: k, price: d.value.content.prices[v.sku] };
  }
  return Object.values(out);
});
const priceLine = computed(() => {
  const ps = Object.values(d.value?.content?.prices || {}).map(Number).filter(Boolean);
  if (!ps.length) return { text: "—", from: false, low: null };
  const lo = Math.min(...ps);
  return { text: lo + " MAD", from: ps.some((p) => p !== lo), low: lo };
});
const samplesN = computed(() => (d.value?.samples || []).reduce((s, x) => s + (Number(x.qty) || 0), 0));
// Under the publish button: where it goes Live, and Shopify's quantity when
// the system check has measured it.
const publishSub = computed(() => {
  const qty = (d.value?.checks || []).find((k) => k.key === "qty" && k.ok && k.detail);
  const head = t("souk.pub.publishSub").replace("{c}", chosen.value.length);
  return qty ? head + " · " + t("souk.pub.qtyOnShopify").replace("{q}", qty.detail) : head;
});
const shopColor = (c) => (lang.value === "ar" ? c.ar || c.fr : c.fr || c.code);
// A phone shows the queue OR the product; the route decides which.
const listOnly = computed(() => !route.params.name);
const showStrip = computed(() => {
  const q = data.value?.queue || [];
  return q.length > 1 || (q.length === 1 && q[0].name !== d.value?.name);
});
// A phone keeps the publish under the thumb on the product view.
const hasFooter = computed(() => !!d.value && !listOnly.value && d.value.stage === "review");
const checksPassed = computed(() => (d.value?.checks || []).filter((k) => k.ok).length);
// Where a send-back goes, each in its stage's colour; or out of the cycle.
const BACK = [
  { v: "content", k: "backContent", icon: "notebook-pen", st: "content" },
  { v: "studio", k: "backStudio", icon: "sparkles", st: "studio" },
  { v: "photos", k: "backPhotos", icon: "camera", st: "photos" },
];
const DROP = [
  { v: "drop:return", k: "dropReturn", icon: "undo-2" },
  { v: "drop:clearance", k: "dropClearance", icon: "tag" },
];
const ageText = (a) => (Number(a) < 1 ? t("souk.pub.today") : t("souk.ageDays").replace("{n}", Math.floor(Number(a))));

// Shopify names a channel after its catalog ("… for Online Store"); say
// what each one is, and never show a bare id as if it were a name.
const CH = [
  [/online store|boutique en ligne/i, "online"], [/headless|hydrogen/i, "headless"], [/google|youtube/i, "google"],
  [/facebook|instagram|meta/i, "meta"], [/tiktok/i, "tiktok"], [/point of sale|\bpos\b/i, "pos"],
  [/inbox/i, "inbox"], [/^shop$/i, "shop"],
];
const chLabel = (ch) => (/^\d+$/.test(String(ch.name || "")) ? t("souk.pub.channelN").replace("{n}", ch.name) : ch.name);
const chNote = (ch) => {
  const hit = CH.find(([re]) => re.test(String(ch.name || "")));
  const n = hit ? t("souk.pub.ch." + hit[1]) : "";
  return n && n.toLowerCase() !== String(ch.name || "").toLowerCase() ? n : "";
};

const dur = (h) => {
  const a = Math.abs(h);
  return a < 48 ? t("souk.pub.hours").replace("{n}", Math.round(a)) : t("souk.pub.days").replace("{n}", Math.round(a / 24));
};
const clock = computed(() => {
  const det = d.value;
  if (!det || det.hoursLeft == null) return null;
  const lim = Number(data.value?.limit) || 0;
  const late = det.hoursLeft < 0;
  const tail = late ? t("souk.pub.lateBy").replace("{n}", dur(det.hoursLeft)) : t("souk.pub.left").replace("{n}", dur(det.hoursLeft));
  if (!lim) return { late, text: tail, limit: 0, pct: 0 };
  const spent = lim * 24 - det.hoursLeft; // hours in this step so far
  return { late, limit: lim, pct: Math.max(0, (spent / (lim * 24)) * 100),
    text: t("souk.pub.ofLimit").replace("{a}", dur(spent)).replace("{l}", t("souk.pub.days").replace("{n}", lim)) + " · " + tail };
});
const dueText = computed(() => {
  const s = d.value?.deadline;
  if (!s) return "";
  const l = local(s); // site clock → the reader's clock
  return t("souk.pub.due").replace("{d}", l.slice(8, 10) + "/" + l.slice(5, 7) + " " + l.slice(11, 16));
});

const hardFail = computed(() => (d.value?.checks || []).filter((k) => k.hard && !k.ok));
const canPublish = computed(() => d.value && d.value.canPublish && !hardFail.value.length
  && ticked.value.length === d.value.manual.length && chosen.value.length > 0);
const blockedWhy = computed(() => {
  if (!d.value) return "";
  if (d.value.sameWriter) return t("souk.sameWriter");
  if (hardFail.value.length) return t("souk.blockedChecks").replace("{list}", hardFail.value.map((k) => t("souk.rk_" + k.key)).join(" · "));
  if (ticked.value.length < d.value.manual.length) return t("souk.blockedEye");
  if (!chosen.value.length) return t("souk.blockedChannels");
  return "";
});

async function load(keep = false) {
  loading.value = true;
  try {
    // A recheck asks for the product on screen, not "the first in the queue".
    const name = route.params.name || (keep ? d.value?.name : undefined);
    const next = await api("souk.review_boot", name ? { name } : {});
    const det = next.detail;
    data.value = next;
    if (det && det.name === stateFor.value) {
      // Same product: the reviewer's ticks and channels stay.
      ticked.value = ticked.value.filter((m) => det.manual.includes(m));
      const ids = new Set((det.channels || []).map((c) => c.id));
      chosen.value = chosen.value.filter((id) => ids.has(id));
      if (!chosen.value.length && !chosenTouched.value) chosen.value = [...(det.chosen || [])];
    } else {
      stateFor.value = det?.name || "";
      ticked.value = [];
      chosen.value = [...(det?.chosen || [])];
      chosenTouched.value = false;
      img.value = "";
      note.value = "";
      back.value = "content";
      lang.value = "fr";
    }
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

async function recheck() {
  await load(true);
  if (d.value && d.value.name === stateFor.value) success(t("souk.pub.rechecked"));
}

async function nudge() {
  busy.value = true;
  try {
    await apiPost("souk.qty_nudge", { name: d.value.name });
    success(t("souk.qtyNudged"));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

// After a publish / send back: the next card someone else wrote, in queue
// order after this one; none → the plain review route (the empty state, or
// whatever the server picks).
async function openNext(cur) {
  const q = data.value?.queue || [];
  const at = q.findIndex((x) => x.name === cur);
  const ring = [...q.slice(at + 1), ...q.slice(0, Math.max(at, 0))].filter((x) => x.name !== cur);
  const next = ring.find((x) => !x.mine);
  if (next) await router.push({ name: "SoukReview", params: { name: next.name } });
  else if (route.params.name) await router.push({ name: "SoukReview" });
  else await load();
  return !!next;
}

async function publish() {
  busy.value = true;
  const cur = d.value.name;
  try {
    const r = await apiPost("souk.publish", {
      name: cur, channels: JSON.stringify(chosen.value), manual: JSON.stringify(ticked.value),
    });
    const msg = t("souk.published").replace("{c}", r.channels).replace("{s}", r.samples);
    const more = await openNext(cur);
    success(msg + " " + (more ? t("souk.pub.nextOpened") : t("souk.pub.queueDone")));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load(true);
  } finally {
    busy.value = false;
  }
}

async function sendBack() {
  busy.value = true;
  const cur = d.value.name;
  try {
    if (back.value.startsWith("drop:")) {
      await apiPost("souk.review_drop", { name: cur, why: back.value.slice(5), note: note.value });
      success(t("souk.dropped"));
    } else {
      await apiPost("souk.review_reject", { name: cur, to: back.value, note: note.value });
      success(t("souk.sentBack"));
    }
    await openNext(cur);
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

watch(() => route.params.name, () => load());
onMounted(() => load());
</script>

<style scoped>
.souk-desc :deep(p) { margin: 0 0 0.5rem; }
.souk-desc :deep(ul) { list-style: disc; padding-inline-start: 1.25rem; margin: 0 0 0.5rem; }

/* Buttons: one solid in the stage colour (the next step), the rest outline.
   44px under a thumb, 36px on a desk. Display comes from the global .btn,
   so `hidden` still wins. */
.btn { flex-shrink: 0; height: 2.75rem; padding-block: 0; padding-inline: 0.875rem; border-radius: 0.75rem; font-size: 13px; font-weight: 600;
  gap: 0.375rem; white-space: nowrap; }
@media (min-width: 1024px) { .btn { height: 2.375rem; } }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.btn-sm { height: 2.25rem; padding-inline: 0.625rem; font-size: 12px; }
@media (min-width: 1024px) { .btn-sm { height: 2rem; } }
.btn-st { background: rgb(var(--st)); color: #fff; font-size: 14px; font-weight: 700; box-shadow: 0 6px 16px -8px rgb(var(--st)); }
.btn-st:not(:disabled):hover { background: rgb(var(--st-ink)); }
.btn-st:disabled { background: rgb(231 229 228); color: rgb(87 83 78); box-shadow: none; opacity: 1; }
.btn-line { background: rgb(255 255 255 / .85); color: rgb(28 25 23); box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.btn-line:not(:disabled):hover { background: #fff; }
:global(html[data-theme="dark"] .btn-st) { color: rgb(28 25 23); }
:global(html[data-theme="dark"] .btn-st:disabled) { background: rgb(68 64 60); color: rgb(168 162 158); }
:global(html[data-theme="dark"] .btn-line) { background: #292524; color: #f5f5f4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }

/* The big publish button at the foot of the channels card. */
.sp-pub { background: rgb(var(--st)); color: #fff; box-shadow: 0 6px 16px -8px rgb(var(--st)); }
.sp-pub:not(:disabled):hover { background: rgb(var(--st-ink)); }
.sp-pub:disabled { background: rgb(231 229 228); color: rgb(87 83 78); box-shadow: none; cursor: not-allowed; }
:global(html[data-theme="dark"] .sp-pub) { color: rgb(28 25 23); }
:global(html[data-theme="dark"] .sp-pub:disabled) { background: rgb(68 64 60); color: rgb(168 162 158); }

/* Queue card (desk strip): picked = the stage tint + ring. */
.sp-q { flex-shrink: 0; width: 248px; display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 14px;
  background: #fff; box-shadow: inset 0 0 0 1px rgb(231 229 228); }
.sp-q:hover { background: rgb(250 250 249); }
.sp-q-on, .sp-q-on:hover { background: rgb(var(--st) / .10); box-shadow: inset 0 0 0 2px rgb(var(--st)); }
:global(html[data-theme="dark"] .sp-q) { background: #292524; box-shadow: inset 0 0 0 1px rgb(68 64 60); }
:global(html[data-theme="dark"] .sp-q-on) { background: rgb(var(--st) / .16); box-shadow: inset 0 0 0 2px rgb(var(--st)); }

/* Age pill: the stage tint; rose once the step is late. */
.sp-age { flex-shrink: 0; display: inline-flex; align-items: center; gap: 3px; height: 22px; padding-inline: 7px; border-radius: 9999px;
  font-size: 11px; font-weight: 700; white-space: nowrap; font-variant-numeric: tabular-nums; }
.sp-age-late { background: rgb(255 228 230); color: rgb(190 18 60); }
:global(html[data-theme="dark"] .sp-age-late) { background: rgb(76 5 25 / .6); color: rgb(253 164 175); }

/* Pass / warn / fail mark in the checks list. */
.sp-tick { flex-shrink: 0; width: 22px; height: 22px; border-radius: 9999px; display: inline-flex; align-items: center; justify-content: center; }
.sp-tick-ok { background: rgb(209 250 229); color: rgb(4 120 87); }
.sp-tick-warn { background: rgb(254 243 199); color: rgb(180 83 9); }
.sp-tick-bad { background: rgb(255 228 230); color: rgb(190 18 60); }
:global(html[data-theme="dark"] .sp-tick-ok) { background: rgb(6 78 59 / .55); color: rgb(110 231 183); }
:global(html[data-theme="dark"] .sp-tick-warn) { background: rgb(120 53 15 / .5); color: rgb(252 211 77); }
:global(html[data-theme="dark"] .sp-tick-bad) { background: rgb(76 5 25 / .6); color: rgb(253 164 175); }

/* A tick row (eye check, channel): a 44px target; ticked = soft green. */
.sp-eye { display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 6px 10px; border-radius: 12px; font-size: 13px; cursor: pointer; }
.sp-eye:hover { background: rgb(250 250 249); }
.sp-eye-on, .sp-eye-on:hover { background: rgb(16 185 129 / .09); }
:global(html[data-theme="dark"] .sp-eye:hover) { background: rgb(255 255 255 / .04); }
:global(html[data-theme="dark"] .sp-eye-on) { background: rgb(52 211 153 / .12); }

/* The storefront preview keeps the shop's own light look in both themes. */
.sp-shop { background: #faf8f4; color: #16130f; box-shadow: inset 0 0 0 1px #ece8e1; }
.sp-shop-on { background: #16130f; color: #fff; }
.sp-serp { background: rgb(250 250 249); box-shadow: inset 0 0 0 1px rgb(231 229 228); }
:global(html[data-theme="dark"] .sp-serp) { background: #fff; }
</style>
