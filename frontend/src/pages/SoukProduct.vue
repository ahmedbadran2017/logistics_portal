<template>
  <!-- One souk product: where it is in the cycle and how long each stage
       took, what it cost per piece, where its pieces are, who has it now,
       and everything that happened to it. Backend: souk.product (+ claim,
       review_drop, finish_buy for a card still being created).
       Look = design Detail.dc.html (1280px). -->
  <div class="max-w-[1320px] mx-auto px-4 sm:px-5 pt-5 sm:pt-6 pb-10 flex flex-col gap-4">
    <div v-if="loading && !d" class="h-[300px] rounded-xl bg-white ring-1 ring-inset ring-stone-200 animate-pulse" />

    <template v-if="d">
      <!-- ── hero: what it is, where it is, the one next step ───────────── -->
      <header class="sk-hero flex flex-col gap-3.5" :class="stageClass(heroStage)">
        <div class="flex gap-3 items-start">
          <router-link :to="{ name: 'SoukBoard' }" :aria-label="t('souk.pd.back')" :title="t('souk.pd.back')"
                       class="w-10 h-10 shrink-0 rounded-xl bg-white/80 ring-1 ring-inset ring-stone-200 flex items-center justify-center text-stone-700 hover:bg-white">
            <Icon :name="isRTL ? 'chevron-right' : 'chevron-left'" :size="18" :stroke-width="2" />
          </router-link>
          <button v-if="d.image" type="button" class="w-[68px] h-[68px] sm:w-20 sm:h-20 shrink-0 rounded-2xl overflow-hidden ring-2 ring-white shadow-[0_6px_18px_-8px_rgba(28,25,23,.45)]"
                  :aria-label="t('souk.recv.refTitle')" @click="big = d.image">
            <img :src="d.image" class="w-full h-full object-cover" alt="" />
          </button>
          <div v-else class="w-[68px] h-[68px] sm:w-20 sm:h-20 shrink-0 rounded-2xl st-tint st-fg flex items-center justify-center">
            <Icon name="image" :size="24" />
          </div>
          <div class="min-w-0 flex-1 flex flex-col gap-1.5">
            <span class="self-start inline-flex items-center gap-1.5 h-7 ps-1 pe-2.5 rounded-full st-solid text-[12px] font-bold">
              <span class="w-5 h-5 rounded-full bg-white/25 flex items-center justify-center"><Icon :name="stageIcon(heroStage)" :size="12" :stroke-width="2.4" /></span>
              {{ d.stage === 'live' ? t('souk.lb.colLive') : t('souk.st_' + d.stage) }}
            </span>
            <h1 class="text-[19px] sm:text-[22px] font-extrabold text-stone-900 leading-tight line-clamp-2">{{ d.title }}</h1>
            <div class="flex flex-wrap gap-1.5 text-[12px]">
              <span class="chip-meta mono" dir="ltr"><Icon name="tag" :size="12" />{{ d.name }}</span>
              <span v-if="d.stall" class="chip-meta"><Icon name="building" :size="12" />{{ d.stall }}</span>
              <span v-if="d.brand" class="chip-meta"><Icon name="award" :size="12" />{{ d.brand }}</span>
              <span v-if="d.trip" class="chip-meta"><Icon name="wallet" :size="12" />{{ t('souk.tripNo').replace('{n}', d.trip) }}</span>
            </div>
          </div>
        </div>

        <!-- in-stage clock -->
        <div v-if="clock" class="flex items-center gap-2.5 bg-white/70 rounded-xl px-3 py-2 ring-1 ring-inset ring-[rgb(var(--st)/.18)]">
          <Icon :name="clock.late ? 'alert-triangle' : 'clock'" :size="15" :class="clock.late ? 'text-rose-600' : 'st-fg'" class="shrink-0" />
          <span class="text-[13px] font-semibold tabular-nums" :class="clock.late ? 'text-rose-700' : 'text-stone-800'">{{ clock.text }}</span>
          <div v-if="clock.limit" class="flex-1 h-1.5 rounded-full bg-stone-200/80 overflow-hidden min-w-[60px]">
            <div class="h-full rounded-full" :class="clock.late ? 'bg-rose-500' : 'st-solid'" :style="{ width: Math.min(100, clock.pct) + '%' }" />
          </div>
        </div>

        <!-- actions: the stage's own step first, the rest quiet -->
        <div class="flex flex-col sm:flex-row gap-2">
          <component :is="next.to ? 'router-link' : 'button'" v-if="next" :to="next.to" type="button"
                     class="h-11 px-4 rounded-xl st-solid text-[14px] font-bold inline-flex items-center justify-center gap-2 shadow-[0_6px_16px_-8px_rgb(var(--st))] disabled:opacity-40"
                     :disabled="busy" @click="next.click && next.click()">
            <Icon :name="next.icon" :size="16" :stroke-width="2.2" />{{ next.label }}
          </component>
          <div class="flex gap-2 overflow-x-auto -mx-1 px-1 sm:flex-wrap sm:overflow-visible">
            <template v-if="d.canClaim && d.stage !== 'buying'">
              <button v-if="!d.claimedBy || (d.claimedBy !== me && d.canDrop)" class="btn btn-line disabled:opacity-40" :disabled="busy" @click="claim(0)">
                <Icon name="hand" :size="14" />{{ t('souk.pd.claim') }}
              </button>
              <button v-if="d.claimedBy && (d.claimedBy === me || d.canDrop)" class="btn btn-line disabled:opacity-40" :disabled="busy" @click="claim(1)">
                <Icon name="unlock" :size="14" />{{ t('souk.pd.release') }}
              </button>
            </template>
            <router-link v-if="d.canBuy && d.stage !== 'buying'" :to="{ name: 'SoukBuy', query: { again: d.name, kind: 'souk' } }" class="btn btn-line">
              <Icon name="refresh-cw" :size="14" />{{ t('souk.buyAgain') }}
            </router-link>
            <a v-if="d.shopifyAdmin" :href="d.shopifyAdmin" target="_blank" rel="noopener" class="btn btn-line">
              <Icon name="shopping-bag" :size="14" />Shopify<Icon name="external-link" :size="12" class="opacity-60" />
            </a>
            <button v-if="canDropNow" class="btn bg-white ring-1 ring-inset ring-rose-200 text-rose-700 hover:bg-rose-50" @click="openDrop">
              <Icon name="ban" :size="14" />{{ t('souk.pd.drop') }}
            </button>
          </div>
        </div>
      </header>

      <div v-if="d.error" class="bg-rose-50 ring-1 ring-inset ring-rose-200 rounded-2xl px-4 py-3 text-[13px] text-rose-800 flex gap-2.5 items-start">
        <Icon name="alert-triangle" :size="16" class="shrink-0 mt-0.5" /><span class="mono break-words">{{ d.error }}</span>
      </div>

      <div v-if="d.stage === 'dropped'" class="sk-sec st-dropped px-4 py-3 text-[13px] text-stone-800 flex gap-2.5 items-start">
        <span class="sk-ico sk-ico-sm"><Icon name="ban" :size="14" /></span>
        <div class="min-w-0 flex flex-col gap-0.5">
          <div class="font-bold">
            {{ d.droppedFrom ? fill(t('souk.pd.droppedBanner'), { s: t('souk.st_' + d.droppedFrom) }) : t('souk.st_dropped') }}
            <span v-if="whyOf(d.reviewNote)" class="font-semibold text-stone-600"> · {{ t('souk.lb.why_' + whyOf(d.reviewNote)) }}</span>
          </div>
          <div v-if="noteText(d.reviewNote)" class="break-words">{{ noteText(d.reviewNote) }}</div>
        </div>
      </div>

      <!-- ── the cycle: one dot per stage, in its colour ───────────────── -->
      <nav ref="stepNav" :aria-label="t('souk.pd.stagesNav')" class="sk-sec px-3 py-3.5 overflow-x-auto">
        <ol class="flex min-w-[640px]">
          <li v-for="(st, i) in stepper" :key="st.s" class="flex-1 flex flex-col items-center gap-1.5 text-center relative" :class="stageClass(st.s)"
              :data-here="st.here ? 1 : undefined" :aria-current="st.here ? 'step' : undefined">
            <span v-if="i" class="absolute top-[17px] h-[3px] rounded-full -z-0"
                  :class="st.state === 'todo' ? 'bg-stone-200' : 'bg-[rgb(var(--st)/.45)]'"
                  :style="isRTL ? { right: '-50%', left: '50%', marginRight: '18px', marginLeft: '18px' } : { left: '-50%', right: '50%', marginLeft: '18px', marginRight: '18px' }" />
            <span class="relative z-[1] w-9 h-9 rounded-full flex items-center justify-center"
                  :class="{ done: 'st-tint st-ink', current: 'st-solid ring-4 ring-[rgb(var(--st)/.2)]', late: 'bg-rose-600 text-white ring-4 ring-rose-100', todo: 'bg-stone-100 text-stone-400' }[st.state]">
              <Icon :name="st.state === 'done' ? 'check' : stageIcon(st.s)" :size="16" :stroke-width="st.state === 'done' ? 2.6 : 2" />
            </span>
            <span class="text-[12px] font-bold leading-tight px-1"
                  :class="st.state === 'late' ? 'text-rose-700' : st.state === 'todo' ? 'text-stone-500' : 'text-stone-900'">{{ t('souk.st_' + st.s) }}</span>
            <span class="text-[11px] text-stone-500 tabular-nums leading-snug px-1">{{ st.sub }}</span>
          </li>
        </ol>
      </nav>

      <!-- ── the numbers that matter, at a glance ──────────────────────── -->
      <section class="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
        <div v-for="k in kpis" :key="k.k" class="kpi" :class="k.cls">
          <span class="flex items-center gap-2 text-[12px] font-semibold text-stone-600"><span class="sk-ico sk-ico-sm"><Icon :name="k.icon" :size="14" /></span>{{ k.k }}</span>
          <span class="text-[20px] font-extrabold tabular-nums text-stone-900 leading-tight"><bdi dir="ltr">{{ k.v }}</bdi> <small v-if="k.u" class="text-[12px] font-semibold text-stone-500">{{ k.u }}</small></span>
          <span v-if="k.s" class="text-[12px] text-stone-500 tabular-nums">{{ k.s }}</span>
        </div>
      </section>

      <div class="flex flex-wrap gap-4 items-start">
        <div class="flex-[999_1_560px] min-w-0 flex flex-col gap-4">
          <!-- variants, one block per colour -->
          <section class="sk-sec st-buying">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="layers" :size="16" /></span>
              <h2 class="sk-sec-t flex-1">{{ t('souk.variants') }}</h2>
              <span class="text-[12px] font-bold st-ink st-tint rounded-full px-2.5 py-1 tabular-nums">{{ d.variants.length }}</span>
            </div>
            <div class="divide-y divide-stone-100">
              <div v-for="g in colourGroups" :key="g.colour" class="px-3.5 py-3 flex flex-col gap-2">
                <div v-if="g.colour" class="flex items-center gap-2 text-[13px] font-bold text-stone-900">
                  <span class="w-3.5 h-3.5 rounded-full ring-1 ring-black/10" :style="{ background: g.swatch }" />{{ g.colour }}
                </div>
                <div v-for="v in g.rows" :key="v.sku" class="rounded-xl bg-stone-50 ring-1 ring-inset ring-stone-100 px-3 py-2.5 flex flex-col gap-2">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="mono text-[12px] font-semibold text-stone-900" dir="ltr">{{ v.sku }}</span>
                    <span v-if="v.sizeLabel" class="text-[12px] font-semibold text-stone-700 bg-white ring-1 ring-inset ring-stone-200 rounded-md px-1.5 py-px">{{ v.sizeLabel }}</span>
                    <span class="ms-auto text-[12px] text-stone-600 tabular-nums">{{ v.qty }} {{ t('souk.pcs') }}</span>
                  </div>
                  <div class="flex items-center gap-2 flex-wrap text-[12px] tabular-nums">
                    <span class="text-stone-600">{{ t('souk.cost') }} <b class="text-stone-900"><bdi dir="ltr">{{ v.cost }}</bdi></b></span>
                    <Icon name="arrow-right" :size="12" class="text-stone-400 rtl:rotate-180" />
                    <span class="text-stone-600">{{ t('souk.sell') }} <b class="text-stone-900"><bdi dir="ltr">{{ v.price || '—' }}</bdi></b></span>
                    <span v-if="marginOf(v) != null" class="rounded-full px-2 py-px font-bold"
                          :class="marginOf(v) < 40 ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700'">{{ marginOf(v) }}%</span>
                  </div>
                  <div v-if="v.stock.length" class="flex flex-wrap gap-1.5">
                    <span v-for="s in v.stock" :key="s.warehouse" class="inline-flex items-center gap-1 h-6 px-2 rounded-md text-[12px] font-semibold tabular-nums st-tint st-ink"
                          :class="whClass(s.warehouse)">
                      <Icon :name="whIcon(s.warehouse)" :size="12" />{{ shortWh(s.warehouse) }} · {{ fmt(s.qty) }}
                    </span>
                  </div>
                  <span v-else class="text-[12px] text-stone-400">{{ t('souk.whereNow') }}: —</span>
                </div>
              </div>
            </div>
          </section>

          <!-- photos -->
          <section v-if="d.finals.length || d.photos.length || d.specs" class="sk-sec st-studio">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="image" :size="16" /></span>
              <h2 class="sk-sec-t">{{ t('souk.pd.photosTitle') }}</h2>
            </div>
            <div class="sk-sec-b flex flex-col gap-3.5">
              <div v-if="d.finals.length" class="flex flex-col gap-2">
                <span class="text-[12px] font-bold st-ink inline-flex items-center gap-1.5"><Icon name="sparkles" :size="13" />{{ t('souk.finals') }} · {{ d.finals.length }}</span>
                <div class="grid grid-cols-4 sm:grid-cols-6 gap-2">
                  <button v-for="f in d.finals" :key="f.url" type="button" class="aspect-square rounded-xl overflow-hidden bg-stone-100 ring-1 ring-stone-200" @click="big = f.url">
                    <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                  </button>
                </div>
              </div>
              <div v-if="d.photos.length" class="flex flex-col gap-2 st-photos">
                <span class="text-[12px] font-bold st-ink inline-flex items-center gap-1.5"><Icon name="camera" :size="13" />{{ t('souk.rawPhotos') }} · {{ d.photos.length }}</span>
                <div class="grid grid-cols-5 sm:grid-cols-8 gap-1.5">
                  <button v-for="ph in d.photos" :key="ph.url" type="button" class="aspect-square rounded-lg overflow-hidden bg-stone-100" @click="big = ph.url">
                    <img :src="ph.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                  </button>
                </div>
              </div>
              <div v-if="d.specs" class="text-[13px] text-stone-700 bg-stone-50 rounded-xl px-3 py-2.5"><b class="text-stone-900">{{ t('souk.specs') }}:</b> {{ d.specs }}</div>
            </div>
          </section>

          <!-- what happened: a timeline, each event in its stage's colour -->
          <section class="sk-sec st-dropped">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="history" :size="16" /></span>
              <h2 class="sk-sec-t">{{ t('souk.pd.happened') }}</h2>
            </div>
            <ol class="sk-sec-b !py-2">
              <li v-for="(e, i) in events" :key="i" class="relative flex gap-3 py-2" :class="e.cls">
                <span v-if="i < events.length - 1" class="absolute top-10 bottom-0 w-px bg-stone-200" :style="isRTL ? { right: '13px' } : { left: '13px' }" />
                <span class="sk-ico sk-ico-sm relative z-[1]"><Icon :name="e.icon" :size="13" /></span>
                <div class="min-w-0 flex-1 flex flex-col gap-px">
                  <span class="text-[13px] font-semibold text-stone-900 break-words leading-snug">{{ e.text }}</span>
                  <span class="text-[12px] text-stone-500 tabular-nums">{{ stamp(e.at) }}<template v-if="e.by"> · {{ e.by }}</template></span>
                </div>
              </li>
              <li v-if="!events.length" class="text-[13px] text-stone-500 py-2">{{ t('souk.pd.noLog') }}</li>
            </ol>
          </section>
        </div>

        <aside class="flex-[1_1_300px] xl:max-w-[400px] min-w-0 flex flex-col gap-4">
          <!-- money: a receipt -->
          <section class="sk-sec st-bought">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="dollar-sign" :size="16" /></span>
              <h2 class="sk-sec-t">{{ t('souk.money') }}</h2>
            </div>
            <dl class="px-3.5 py-2">
              <div v-for="r in moneyRows" :key="r.k" class="row" :class="r.total ? 'row-total' : ''">
                <dt :class="r.total ? 'font-bold text-stone-900' : 'text-stone-600'">{{ r.k }}</dt>
                <dd class="tabular-nums text-end" :class="r.cls || 'font-semibold text-stone-900'"><bdi dir="ltr">{{ r.v }}</bdi></dd>
              </div>
            </dl>
          </section>

          <!-- stock: one bar, four places -->
          <section v-if="d.stockSplit" class="sk-sec st-live">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="warehouse" :size="16" /></span>
              <h2 class="sk-sec-t flex-1">{{ t('souk.pd.stock') }}</h2>
              <span class="text-[13px] font-extrabold st-ink tabular-nums">{{ fmt(stockTotal) }}</span>
            </div>
            <div class="sk-sec-b flex flex-col gap-2.5">
              <div v-if="stockTotal" class="flex h-2.5 rounded-full overflow-hidden gap-[2px] bg-stone-100">
                <div v-for="k in STOCK" :key="k.k" v-show="d.stockSplit[k.k]" :class="k.cls + ' st-solid'"
                     :style="{ width: (d.stockSplit[k.k] / stockTotal * 100) + '%' }" />
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div v-for="k in STOCK" :key="k.k" class="rounded-xl px-2.5 py-2 flex items-center gap-2" :class="[k.cls, d.stockSplit[k.k] ? 'st-soft' : 'bg-stone-50']">
                  <span class="st-dot" :class="d.stockSplit[k.k] ? '' : 'opacity-30'" />
                  <span class="text-[12px] text-stone-600 flex-1 min-w-0 truncate">{{ t('souk.pd.' + k.k) }}</span>
                  <span class="text-[14px] font-bold tabular-nums" :class="d.stockSplit[k.k] ? 'st-ink' : 'text-stone-400'">{{ fmt(d.stockSplit[k.k]) }}</span>
                </div>
              </div>
            </div>
          </section>

          <!-- people and the store -->
          <section class="sk-sec st-review">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="users" :size="16" /></span>
              <h2 class="sk-sec-t">{{ t('souk.pd.details') }}</h2>
            </div>
            <dl class="px-3.5 py-2">
              <div class="row"><dt class="text-stone-600">{{ t('souk.buyerLbl') }}</dt><dd class="text-end">{{ d.buyer || '—' }}</dd></div>
              <div v-if="d.canClaim || d.claimedBy" class="row">
                <dt class="text-stone-600">{{ t('souk.pd.whoHas') }}</dt>
                <dd class="text-end font-semibold" :class="d.claimedBy === me ? 'text-[var(--accent-700)]' : d.claimedBy ? 'text-stone-900' : 'text-stone-500 font-normal'">
                  {{ !d.claimedBy ? t('souk.pd.nobody') : d.claimedBy === me ? t('souk.pd.youHaveIt') : (d.claimedName || d.claimedBy) }}
                </dd>
              </div>
              <div class="row">
                <dt class="text-stone-600">Shopify</dt>
                <dd class="text-end">
                  <span v-if="d.shopifyId" class="inline-flex items-center gap-1.5 text-[12px] font-semibold rounded-full px-2 py-0.5"
                        :class="d.stage === 'live' ? 'bg-emerald-50 text-emerald-700' : 'bg-stone-100 text-stone-700'">
                    <span class="w-1.5 h-1.5 rounded-full" :class="d.stage === 'live' ? 'bg-emerald-500' : 'bg-stone-400'" />
                    {{ d.stage === 'live' ? t('souk.pd.shopActive') : t('souk.pd.shopDraft') }}
                    <span class="mono text-stone-500" dir="ltr">{{ d.shopifyId }}</span>
                  </span>
                  <span v-else>—</span>
                </dd>
              </div>
              <div v-if="d.contentBy" class="row"><dt class="text-stone-600">{{ t('souk.contentLbl') }}</dt><dd class="text-end">{{ d.contentBy }}</dd></div>
              <div v-if="d.publishedAt" class="row"><dt class="text-stone-600">{{ t('souk.publishedLbl') }}</dt><dd class="text-end tabular-nums">{{ d.publishedBy }} · {{ stamp(d.publishedAt) }}</dd></div>
              <div v-if="d.rejects" class="row"><dt class="text-stone-600">{{ t('souk.rejectsLbl') }}</dt><dd class="tabular-nums font-bold text-amber-700">{{ d.rejects }}</dd></div>
            </dl>
          </section>

          <!-- purchases -->
          <section class="sk-sec st-buying">
            <div class="sk-sec-h">
              <span class="sk-ico"><Icon name="file-text" :size="16" /></span>
              <h2 class="sk-sec-t">{{ t('souk.purchases') }}</h2>
            </div>
            <div class="sk-sec-b flex flex-col gap-2.5">
              <div v-for="p in d.purchases" :key="p.po" class="rounded-xl bg-stone-50 ring-1 ring-inset ring-stone-100 p-3 flex flex-col gap-2">
                <div class="flex items-center gap-2">
                  <span class="mono text-[12px] font-semibold text-stone-900" dir="ltr">{{ p.po }}</span>
                  <span class="ms-auto text-[14px] font-extrabold tabular-nums">{{ fmt(p.amount) }} <small class="text-[11px] font-semibold text-stone-500">MAD</small></span>
                </div>
                <div class="flex items-center gap-1.5 flex-wrap text-[12px]">
                  <span class="chip-meta"><Icon name="building" :size="12" />{{ p.stall }}</span>
                  <span v-if="p.pay" class="chip-meta" :class="PAY_CLS[p.pay]"><Icon :name="PAY_ICON[p.pay] || 'wallet'" :size="12" class="st-fg" />{{ t('souk.buy.pay.' + p.pay) }}<span v-if="p.payRef" class="mono" dir="ltr"> · {{ p.payRef }}</span><span v-if="p.payDue" dir="ltr"> · {{ p.payDue }}</span></span>
                </div>
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-1.5 rounded-full bg-stone-200 overflow-hidden"><div class="h-full rounded-full bg-emerald-500" :style="{ width: Math.min(100, p.received) + '%' }" /></div>
                  <span class="text-[12px] font-semibold text-stone-600 tabular-nums">{{ Math.round(p.received) }}%</span>
                </div>
                <div v-if="p.outcome" class="flex flex-wrap gap-1.5 text-[12px] font-semibold tabular-nums">
                  <span class="rounded-md px-1.5 py-0.5 bg-emerald-50 text-emerald-700">{{ t('souk.good') }} {{ sum(p.outcome.lines, 'good') }}</span>
                  <span v-if="sum(p.outcome.lines, 'studio')" class="rounded-md px-1.5 py-0.5 bg-violet-50 text-violet-700">{{ t('souk.pd.studio') }} {{ sum(p.outcome.lines, 'studio') }}</span>
                  <span v-if="brokenOf(p)" class="rounded-md px-1.5 py-0.5 bg-rose-50 text-rose-700">{{ t('souk.brokenShort') }} {{ brokenOf(p) }}</span>
                  <span v-if="sum(p.outcome.lines, 'short')" class="rounded-md px-1.5 py-0.5 bg-amber-50 text-amber-800">{{ t('souk.short') }} {{ sum(p.outcome.lines, 'short') }}</span>
                  <span v-if="p.pr" class="mono text-stone-500 px-1 py-0.5" dir="ltr">{{ p.pr }}</span>
                </div>
                <div v-if="p.owed" class="text-[12px] font-semibold text-amber-800 bg-amber-50 rounded-lg px-2.5 py-1.5 flex items-start gap-1.5">
                  <Icon name="alert-circle" :size="13" class="shrink-0 mt-0.5" />
                  <span>{{ t('souk.owesShort').replace('{n}', fmt(p.owed)) }}<span v-if="p.debitNote" class="mono"> · {{ p.debitNote }}</span><span v-else> · {{ t('souk.noDebitYet') }}</span></span>
                </div>
              </div>
              <div v-if="!d.purchases.length" class="text-stone-500 text-[13px]">—</div>
              <button v-if="d.receipt" type="button" class="rounded-xl overflow-hidden ring-1 ring-stone-200 flex items-center gap-2.5 p-2 text-start hover:bg-stone-50" @click="big = d.receipt">
                <img :src="d.receipt" class="w-12 h-12 rounded-lg object-cover" alt="" />
                <span class="text-[13px] font-semibold text-stone-800 flex items-center gap-1.5"><Icon name="ticket" :size="14" class="text-stone-500" />{{ t('souk.receipt') }}</span>
              </button>
            </div>
          </section>

          <!-- the exit rule -->
          <section class="rounded-2xl bg-stone-100/70 p-3.5 flex gap-2.5 items-start">
            <Icon name="info" :size="16" class="text-stone-500 shrink-0 mt-0.5" />
            <div class="flex flex-col gap-1">
              <h2 class="text-[13px] font-bold text-stone-800">{{ t('souk.pd.exitTitle') }}</h2>
              <p class="text-[12px] text-stone-600 leading-[1.6]">{{ exitBody }}</p>
            </div>
          </section>
        </aside>
      </div>
    </template>

    <!-- a photo, big -->
    <div v-if="big" class="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4" @click="big = ''">
      <img :src="big" class="max-w-full max-h-full rounded-xl object-contain" alt="" />
      <button type="button" class="absolute top-3 end-3 w-11 h-11 rounded-full bg-white/90 text-stone-900 flex items-center justify-center" :aria-label="t('souk.recv.close')">
        <Icon name="x" :size="18" />
      </button>
    </div>

    <!-- drop: won't be published -->
    <div v-if="dropOpen" class="fixed inset-0 z-50 bg-stone-900/40 flex items-end sm:items-center justify-center sm:p-4"
         role="dialog" aria-modal="true" :aria-label="t('souk.pd.dropTitle')" @click.self="dropOpen = false" @keydown.esc="dropOpen = false">
      <form class="bg-white w-full sm:max-w-md rounded-t-xl sm:rounded-xl p-4 pb-[max(1rem,env(safe-area-inset-bottom))] flex flex-col gap-3 max-h-[90vh] overflow-y-auto" @submit.prevent="drop">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-[15px] font-bold text-stone-900">{{ t('souk.pd.dropTitle') }}</h2>
            <p class="text-[13px] text-stone-600 mt-0.5">{{ t('souk.pd.dropIntro') }}</p>
          </div>
          <button type="button" class="w-11 h-11 -me-2 -mt-2 shrink-0 rounded-lg flex items-center justify-center text-stone-500" :aria-label="t('souk.cancel')" @click="dropOpen = false">
            <Icon name="x" :size="18" />
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2" role="radiogroup">
          <label v-for="w in ['return', 'clearance']" :key="w"
                 class="min-h-[56px] rounded-xl p-3 cursor-pointer ring-inset flex flex-col gap-0.5"
                 :class="why === w ? 'ring-[1.5px] ring-rose-600 bg-rose-50' : 'ring-1 ring-stone-200 bg-white'">
            <input v-model="why" type="radio" name="why" :value="w" class="sr-only" />
            <span class="text-[13px] font-bold text-stone-900">{{ w === 'return' ? t('souk.pd.whyReturn') : t('souk.pd.whyClearance') }}</span>
            <span class="text-[12px] text-stone-600">{{ w === 'return' ? t('souk.pd.whyReturnHint') : t('souk.pd.whyClearanceHint') }}</span>
          </label>
        </div>
        <textarea ref="noteEl" v-model="note" rows="3" required
                  class="w-full rounded-lg border border-stone-200 p-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-rose-400"
                  :placeholder="t('souk.pd.notePh')" />
        <div class="flex gap-2">
          <button type="button" class="btn btn-line flex-1 justify-center" @click="dropOpen = false">{{ t('souk.cancel') }}</button>
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
import { stageClass, stageIcon, swatch } from "@/souk/stages";
import { api, apiPost } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { eventText as souEvent } from "@/lib/soukEvents";
import { useToast } from "@/composables/useToast";
import { useAuth } from "@/composables/useAuth";

const STAGES = ["buying", "bought", "photos", "studio", "content", "review", "live"];
const { t, isRTL, locale } = useI18n();
const { warn, success } = useToast();
const { user } = useAuth();
const route = useRoute();
const d = ref(null);
const loading = ref(true);
const busy = ref(false);
const stepNav = ref(null);
const me = computed(() => user.value || "");

const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const PAY_ICON = { cash: "wallet", cheque: "notebook-pen", transfer: "send", credit: "clock" };
const PAY_CLS = { cash: "st-live", cheque: "st-photos", transfer: "st-studio", credit: "st-bought" };
const big = ref("");
const money = (n) => Number(n || 0).toLocaleString("fr-FR", { maximumFractionDigits: 2 }) + " MAD";
const round1 = (n) => Math.round(Number(n || 0) * 10) / 10;
const fill = (s, vars) => Object.entries(vars).reduce((o, [k, v]) => o.split("{" + k + "}").join(String(v)), String(s));
const shortWh = (w) => (w || "").replace(/ - JM$/, "");
const sum = (rows, k) => (rows || []).reduce((s, r) => s + (Number(r[k]) || 0), 0);
// Comments may come back wrapped in markup; show their text only.
const plain = (s) => String(s || "").replace(/<[^>]*>/g, "").replace(/&amp;/g, "&");
// Every souk comment starts "Souk: " so the desk can find them; the page doesn't need it.
const eventText = (s) => souEvent(plain(s), locale.value, (st) => t("souk.st_" + st, st));
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
// The exit rule's text opens with the card's own heading ("If it won't be
// published: …"); under that heading, show only the rest.
const exitBody = computed(() => {
  const r = String(t("souk.exitRule")), h = String(t("souk.pd.exitTitle"));
  if (!r.startsWith(h)) return r;
  const rest = r.slice(h.length).replace(/^\s*:\s*/, "");
  return rest.charAt(0).toUpperCase() + rest.slice(1);
});
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
    return { s, state, sub, here: i === reached };
  });
});

// ── the page's own reading of the card ──────────────────────────────────────
// A dropped card wears stone; every other one its stage's colour.
const heroStage = computed(() => (d.value?.stage === "dropped" ? "dropped" : d.value?.stage || "buying"));

// How long it has sat in this stage, against the stage's deadline.
const clock = computed(() => {
  const x = d.value;
  if (!x || ["live", "dropped"].includes(x.stage)) return null;
  const r = [...(x.stages || [])].reverse().find((s) => s.current);
  const days = r ? r.days : x.age;
  const limit = r ? r.limit : 0;
  const late = !!(r && r.late);
  let text = fill(t("souk.lb.inStage"), { d: dur(days) });
  if (limit) text += " · " + (late ? fill(t("souk.pd.lateBy"), { d: dur(days - limit) }) : fill(t("souk.lb.colDeadline"), { n: limit }));
  return { text, late, limit, pct: limit ? (days / limit) * 100 : 0 };
});

// The one next step this stage asks of the viewer, if they may do it.
const next = computed(() => {
  const x = d.value;
  if (!x) return null;
  if (x.stage === "buying") return { icon: "refresh-cw", label: t("souk.retry"), click: finish };
  if (x.stage === "bought" && x.canReceive && x.po) return { icon: "package-check", label: t("souk.receiveBtn"), to: { name: "SoukReceive", params: { po: x.po } } };
  if (x.stage === "photos" && x.canPhoto) return { icon: "camera", label: t("souk.shootBtn"), to: { name: "SoukPhoto", params: { name: x.name } } };
  if (x.stage === "studio" && x.canStudio) return { icon: "sparkles", label: t("souk.finalsBtn"), to: { name: "SoukStudio", params: { name: x.name } } };
  if (x.stage === "content" && x.canContent) return { icon: "notebook-pen", label: t("souk.contentBtn"), to: { name: "SoukContent", params: { name: x.name } } };
  if (x.stage === "review" && x.canReview) return { icon: "clipboard-check", label: t("souk.reviewBtn"), to: { name: "SoukReview", params: { name: x.name } } };
  return null;
});

// Four numbers: what it cost, how many, what one piece really costs, and
// how many are sellable now.
const kpis = computed(() => {
  const x = d.value, m = x?.money || {};
  const landed = m.landedPerPiece != null ? m.landedPerPiece : m.perPiece;
  return [
    { k: t("souk.pd.boughtFor"), icon: "wallet", cls: "st-buying", v: fmt(m.paid ?? x?.cost), u: "MAD" },
    { k: t("souk.units"), icon: "boxes", cls: "st-bought", v: fmt(m.units ?? x?.units), u: t("souk.pcs") },
    { k: t("souk.pd.landed"), icon: "tag", cls: "st-review", v: landed != null ? fmt(landed) : "—", u: landed != null ? "MAD" : "",
      s: m.landedPerPiece == null ? t("souk.pd.notAllocated") : "" },
    { k: t("souk.pd.shelf"), icon: "warehouse", cls: "st-live", v: fmt(x?.stockSplit?.shelf), u: t("souk.pcs") },
  ];
});

// Variants grouped by colour, so a size run reads as one block.
const colourGroups = computed(() => {
  const m = new Map();
  for (const v of d.value?.variants || []) {
    const k = v.colorFr || "";
    if (!m.has(k)) m.set(k, { colour: k, swatch: swatch(v.color), rows: [] });
    m.get(k).rows.push(v);
  }
  return [...m.values()];
});
const marginOf = (v) => (Number(v.price) > 0 ? Math.round(((v.price - v.cost) / v.price) * 100) : null);
// Where a piece sits, in the colour of what that place means.
const whClass = (w) => (/studio/i.test(w) ? "st-studio" : /defect/i.test(w) ? "st-late" : /receiv/i.test(w) ? "st-bought" : "st-live");
const whIcon = (w) => (/studio/i.test(w) ? "sparkles" : /defect/i.test(w) ? "package-x" : /receiv/i.test(w) ? "inbox" : "map-pin");

const STOCK = [
  { k: "shelf", cls: "st-live" }, { k: "studio", cls: "st-studio" },
  { k: "defective", cls: "st-late" }, { k: "receiving", cls: "st-bought" },
];
const stockTotal = computed(() => STOCK.reduce((a, k) => a + (Number(d.value?.stockSplit?.[k.k]) || 0), 0));
const brokenOf = (p) => sum(p.outcome?.lines, "brokenSupplier") + sum(p.outcome?.lines, "brokenTransport") + sum(p.outcome?.lines, "brokenWarehouse");

// The trail, newest first, each event marked by the stage it belongs to.
const EVENT_KIND = [
  [/bought again/i, "refresh-cw", "st-buying"], [/bought from/i, "shopping-bag", "st-buying"],
  [/received|nothing of ours/i, "package-check", "st-bought"], [/sent back to in-house|in-house photos/i, "camera", "st-photos"],
  [/final photos/i, "sparkles", "st-studio"], [/content on/i, "notebook-pen", "st-content"],
  [/review sent it back/i, "undo-2", "st-review"], [/will NOT be published/i, "ban", "st-dropped"],
  [/LIVE by/i, "zap", "st-live"], [/took it|released/i, "hand", "st-dropped"],
];
const events = computed(() => [...(d.value?.events || [])].reverse().map((e) => {
  const raw = plain(e.text);
  const k = EVENT_KIND.find(([re]) => re.test(raw));
  return { ...e, text: eventText(e.text), icon: k ? k[1] : "circle", cls: k ? k[2] : "st-dropped" };
}));

const moneyRows = computed(() => {
  const m = d.value?.money;
  if (!m) {
    return [
      { k: t("souk.pd.boughtFor"), v: money(d.value?.cost) },
      { k: t("souk.units"), v: fmt(d.value?.units) },
    ];
  }
  const na = t("souk.pd.notAllocated");
  // Design order: what we paid, the trip's transport share, what the stall
  // owes back (green, a credit), what broke on our side, then per piece.
  return [
    { k: t("souk.pd.boughtFor"), v: money(m.paid) },
    { k: t("souk.units"), v: fmt(m.units) },
    { k: t("souk.pd.transport"), v: m.transport == null ? na : money(m.transport), cls: m.transport == null ? "text-stone-500 italic" : "" },
    { k: t("souk.pd.owed"), v: (m.owed ? "\u2212" : "") + money(m.owed), cls: m.owed ? "font-semibold text-emerald-700" : "text-stone-500" },
    { k: fill(t("souk.pd.brokenOurs"), { n: m.brokenUnits || 0 }), v: money(m.brokenOurs),
      cls: m.brokenOurs ? "font-semibold text-rose-700" : "text-stone-500" },
    { k: t("souk.pd.perPiece"), v: money(m.perPiece), total: true },
    { k: t("souk.pd.landed"), v: m.landedPerPiece == null ? na : money(m.landedPerPiece), total: true,
      cls: m.landedPerPiece == null ? "text-stone-500 italic" : "font-extrabold text-stone-900" },
  ];
});

async function load() {
  loading.value = true;
  try {
    d.value = await api("souk.product", { name: route.params.name });
    // A phone shows ~3 of the 7 stages: bring the one it is in into view.
    nextTick(() => stepNav.value?.querySelector("[data-here]")?.scrollIntoView({ block: "nearest", inline: "center" }));
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
/* Header action — design: 36px, radius 8, 12.5px/600; 44px on touch. */
.btn {
  flex-shrink: 0;
  height: 2.75rem;
  padding-inline: 0.75rem;
  border-radius: 0.5rem;
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  white-space: nowrap;
}
@media (min-width: 1024px) { .btn { height: 2.25rem; } }
.btn-accent { background: var(--accent-600); color: #fff; }
.btn-accent:hover { background: var(--accent-700); }
.btn { border-radius: 0.75rem; }
.btn-line { background: rgb(255 255 255 / .85); color: rgb(28 25 23); box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.btn-line:hover { background: #fff; }
/* A fact about the card: a quiet pill with its icon. */
.chip-meta { display: inline-flex; align-items: center; gap: 4px; height: 24px; padding-inline: 8px; border-radius: 9999px;
  background: rgb(255 255 255 / .75); box-shadow: inset 0 0 0 1px rgb(231 229 228); color: rgb(68 64 60); font-weight: 600; white-space: nowrap; }
.kpi { display: flex; flex-direction: column; gap: 4px; padding: 12px 14px; border-radius: 16px;
  background: linear-gradient(160deg, rgb(var(--st) / .09), #fff 55%); box-shadow: inset 0 0 0 1px rgb(var(--st) / .18); }
.row-total { box-shadow: none !important; border-top: 1px dashed rgb(214 211 209); margin-top: 4px; padding-top: 8px; }
.row-total + .row-total { border-top: 0; margin-top: 0; padding-top: 3px; }
:global(html[data-theme="dark"] .chip-meta) { background: rgb(41 37 36); color: #d6d3d1; box-shadow: inset 0 0 0 1px rgb(68 64 60); }
:global(html[data-theme="dark"] .kpi) { background: linear-gradient(160deg, rgb(var(--st) / .14), #292524 60%); box-shadow: inset 0 0 0 1px rgb(var(--st) / .25); }
:global(html[data-theme="dark"] .btn-line) { background: #292524; color: #f5f5f4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }

/* Side card — design: white, radius 12, inset ring, 14px; rows 12.5px with
   a #f5f5f4 hairline under each. */
.side {
  display: flex; flex-direction: column; gap: 6px; padding: 14px; border-radius: 12px;
  background: #fff; box-shadow: inset 0 0 0 1px rgb(231 229 228); font-size: 13px;
}
.side-h { margin-bottom: 4px; font-size: 14px; font-weight: 700; color: rgb(28 25 23); }
.row { display: flex; justify-content: space-between; gap: 10px; padding-block: 3px; box-shadow: inset 0 -1px 0 rgb(245 245 244); }
.row:last-child { box-shadow: none; }
:global(html[data-theme="dark"] .side) { background: #292524; box-shadow: inset 0 0 0 1px rgb(68 64 60); }
:global(html[data-theme="dark"] .side-h) { color: #f5f5f4; }
:global(html[data-theme="dark"] .row) { box-shadow: inset 0 -1px 0 rgb(68 64 60); }
:global(html[data-theme="dark"] .row:last-child) { box-shadow: none; }
summary::-webkit-details-marker { display: none; }
</style>
