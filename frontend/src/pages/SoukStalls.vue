<template>
  <!-- The stalls (المحلات): the Derb Omar directory and each stall's account.
       A phone shows the list, then one stall; a desk shows both side by side.
       The balance = what we owe the stall less what it owes us (souk_stalls.py
       explains the three parts). The buyer sees the balance only; the
       statement (every purchase, payment and debit note) is the manager's and
       the accountant's — the server sends it to nobody else.
       Backend: souk_stalls.stalls_boot / stall / save_stall / create_stall /
       similar_stalls; the storefront photo is souk.upload_photo kind=stall. -->
  <div class="st-buying px-4 sm:px-5 pt-5 sm:pt-6 pb-10 max-w-[1240px] mx-auto flex flex-col gap-4">
    <div v-if="loading && !data" class="h-[220px] sk-sec animate-pulse" />

    <template v-else-if="data">
      <div class="grid gap-4 lg:grid-cols-[400px_minmax(0,1fr)] items-start">
        <!-- ── the list ─────────────────────────────────────────────────── -->
        <div class="flex flex-col gap-3" :class="name || creating ? 'hidden lg:flex' : 'flex'">
          <header class="sk-hero flex flex-col gap-3">
            <div class="flex items-start gap-3">
              <span class="sk-ico sk-ico-lg sk-ico-solid"><Icon name="store" :size="20" :stroke-width="2" /></span>
              <div class="min-w-0 flex-1">
                <h1 class="text-[19px] font-extrabold text-stone-900 leading-tight">{{ t('souk.stl.title') }}</h1>
                <p class="text-[12px] text-stone-600 leading-normal">{{ t('souk.stl.sub') }}</p>
              </div>
              <button v-if="data.canEdit" class="btn btn-st btn-sm inline-flex items-center" @click="openCreate">
                <Icon name="plus" :size="14" :stroke-width="2.4" />{{ t('souk.stl.add') }}
              </button>
            </div>
            <div class="flex flex-wrap gap-2">
              <span class="chip bg-white/85 ring-1 ring-inset ring-stone-200 text-stone-800">
                {{ t('souk.stl.totalOwed') }} · <b class="tabular-nums" dir="ltr">{{ fmt(Math.max(0, owedSum)) }} MAD</b>
              </span>
              <span v-if="creditSum > 0" class="chip bg-emerald-50 text-emerald-800">
                {{ t('souk.stl.totalCredit') }} · <b class="tabular-nums" dir="ltr">{{ fmt(creditSum) }} MAD</b>
              </span>
              <span v-if="data.totals.overdue > 0" class="chip bg-rose-50 text-rose-800">
                <Icon name="alert-triangle" :size="12" />{{ tt('souk.stl.overdueTotal', { n: data.totals.overdueStalls }) }} ·
                <b class="tabular-nums" dir="ltr">{{ fmt(data.totals.overdue) }} MAD</b>
              </span>
              <span v-if="data.full && data.totals.notBilled" class="chip bg-amber-50 text-amber-900">
                <Icon name="file-text" :size="12" />{{ tt('souk.stl.notBilled', { n: data.totals.notBilled }) }}
              </span>
            </div>
          </header>

          <div class="flex flex-col gap-2">
            <label class="relative block">
              <span class="sr-only">{{ t('souk.stl.searchPh') }}</span>
              <Icon name="search" :size="16" class="absolute top-1/2 -translate-y-1/2 start-3 text-stone-400 pointer-events-none" />
              <input v-model="q" type="search" :placeholder="t('souk.stl.searchPh')" autocomplete="off"
                     class="w-full h-11 rounded-xl ring-1 ring-inset ring-stone-300 bg-white ps-9 pe-3 text-[15px]" />
            </label>
            <div v-if="usedCats.length" class="flex gap-1.5 overflow-x-auto -mx-1 px-1 pb-0.5" role="group" :aria-label="t('souk.stl.sellsLbl')">
              <button type="button" class="cat" :aria-pressed="!cat" @click="cat = ''">{{ t('souk.stl.all') }}</button>
              <button v-for="c in usedCats" :key="c.key" type="button" class="cat" :aria-pressed="cat === c.key"
                      @click="cat = cat === c.key ? '' : c.key">{{ catName(c.key) }}</button>
            </div>
          </div>

          <section class="sk-sec">
            <div v-if="!data.stalls.length" class="px-5 py-10 text-center text-[14px] text-stone-600">{{ t('souk.stl.empty') }}</div>
            <div v-else-if="!shown.length" class="px-5 py-8 text-center text-[14px] text-stone-600">{{ t('souk.stl.noResults') }}</div>
            <router-link v-for="(s, i) in shown" :key="s.name" :to="{ name: 'SoukStalls', params: { name: s.name } }"
                         class="flex items-center gap-3 px-3.5 py-3 min-h-[72px] hover:bg-stone-50"
                         :class="[i ? 'border-t border-stone-100' : '', s.name === name ? 'st-soft' : '', s.disabled ? 'opacity-60' : '']">
              <img v-if="s.photo" :src="s.photo" alt="" class="w-12 h-12 shrink-0 rounded-xl object-cover ring-1 ring-stone-200" />
              <span v-else class="w-12 h-12 shrink-0 rounded-xl st-tint st-fg flex items-center justify-center"><Icon name="store" :size="18" /></span>
              <div class="min-w-0 flex-1 flex flex-col gap-0.5">
                <div class="flex items-center gap-1.5 min-w-0">
                  <span class="text-[14px] font-semibold text-stone-900 truncate ltr:text-left rtl:text-right" dir="ltr">{{ s.label }}</span>
                  <span v-if="s.disabled" class="shrink-0 text-[11px] font-bold rounded px-1.5 bg-stone-100 text-stone-600">{{ t('souk.stl.disabledTag') }}</span>
                </div>
                <div class="text-[12px] text-stone-600 truncate">
                  <template v-if="s.place">{{ s.place }}</template><template v-if="s.place && s.phone"> · </template><span v-if="s.phone" dir="ltr">{{ s.phone }}</span>
                  <template v-if="!s.place && !s.phone">{{ s.last ? tt('souk.stl.lastBuy', { d: day(s.last) }) : t('souk.stl.never') }}</template>
                </div>
                <div v-if="s.place || s.phone" class="text-[12px] text-stone-500 truncate">
                  {{ s.last ? tt('souk.stl.lastBuy', { d: day(s.last) }) : t('souk.stl.never') }}<template v-if="s.buys"> · {{ tt('souk.stl.buysN', { n: s.buys }) }}</template>
                  <template v-if="s.issueRate"> · <span class="text-amber-800">{{ tt('souk.stl.issueRate', { n: s.issueRate }) }}</span></template>
                </div>
              </div>
              <div class="shrink-0 flex flex-col items-end gap-1">
                <span class="text-[14px] font-bold tabular-nums" :class="balCls(s.balance)" dir="ltr">{{ balText(s.balance) }}</span>
                <span v-if="s.overdue" class="text-[11px] font-bold rounded-full px-2 py-0.5 bg-rose-50 text-rose-700">{{ t('souk.stl.st_overdue') }}</span>
                <span v-else-if="s.balance < -0.5" class="text-[11px] font-bold rounded-full px-2 py-0.5 bg-emerald-50 text-emerald-700">{{ t('souk.stl.creditTag') }}</span>
              </div>
            </router-link>
          </section>
        </div>

        <!-- ── a new stall ──────────────────────────────────────────────── -->
        <section v-if="creating" class="sk-sec">
          <div class="sk-sec-h">
            <button class="lg:hidden lp-tap w-9 h-9 -ms-1 rounded-full inline-flex items-center justify-center" :aria-label="t('souk.stl.back')" @click="closeCreate">
              <Icon name="chevron-left" :size="18" class="rtl:rotate-180" />
            </button>
            <span class="sk-ico"><Icon name="plus" :size="16" /></span>
            <h2 class="sk-sec-t flex-1">{{ t('souk.stl.newTitle') }}</h2>
          </div>
          <div class="sk-sec-b flex flex-col gap-3">
            <StallFields :f="nf" :cats="data.categories" :cat-name="catName" with-name />
            <div v-if="nfMatch.length && !nf.sure" role="status" class="rounded-xl bg-amber-50 ring-1 ring-inset ring-amber-200 p-3 flex flex-col gap-2">
              <span class="text-[13px] font-bold text-amber-900 inline-flex items-center gap-1.5"><Icon name="alert-triangle" :size="14" />{{ t('souk.stl.didYouMean') }}</span>
              <router-link v-for="m in nfMatch" :key="m.name" :to="{ name: 'SoukStalls', params: { name: m.name } }"
                           class="lp-tap min-h-11 flex items-center gap-2.5 rounded-lg bg-white ring-1 ring-inset ring-amber-200 px-2.5 py-1.5">
                <span class="min-w-0 flex-1 flex flex-col">
                  <span class="text-[14px] font-semibold text-stone-900 truncate" dir="ltr">{{ m.label }}</span>
                  <span class="text-[12px] text-stone-600 truncate">{{ m.why === 'phone' ? t('souk.stl.samePhone') : t('souk.stl.sameName') }}<template v-if="m.place"> · {{ m.place }}</template></span>
                </span>
                <Icon name="chevron-right" :size="16" class="rtl:rotate-180 text-stone-400" />
              </router-link>
              <button type="button" class="self-start text-[13px] font-semibold text-stone-700 underline underline-offset-2 min-h-9" @click="nf.sure = true">{{ t('souk.stl.another') }}</button>
            </div>
            <div class="flex gap-2">
              <button class="btn btn-st inline-flex items-center" :disabled="busy || nameShort(nf.label) || (nfMatch.length && !nf.sure)" @click="create">
                <Icon name="check" :size="15" :stroke-width="2.4" />{{ t('souk.stl.createBtn') }}
              </button>
              <button class="btn btn-line inline-flex items-center" @click="closeCreate">{{ t('souk.stl.cancel') }}</button>
            </div>
          </div>
        </section>

        <!-- ── one stall ────────────────────────────────────────────────── -->
        <div v-else-if="name" class="flex flex-col gap-4">
          <div v-if="!d" class="h-[320px] sk-sec animate-pulse" />
          <template v-else>
            <router-link :to="{ name: 'SoukStalls' }"
                         class="lg:hidden self-start lp-tap h-9 ps-1.5 pe-3 rounded-full bg-white ring-1 ring-inset ring-stone-200 inline-flex items-center gap-1 text-[13px] font-semibold text-stone-700">
              <Icon name="chevron-left" :size="16" class="rtl:rotate-180" />{{ t('souk.stl.back') }} · {{ data.stalls.length }}
            </router-link>

            <!-- profile -->
            <header class="sk-hero flex flex-col gap-3">
              <div class="flex gap-3.5 items-start">
                <button type="button" class="relative shrink-0 w-[84px] h-[84px] rounded-2xl overflow-hidden bg-white ring-1 ring-inset ring-stone-200 group"
                        :disabled="!data.canEdit || uploading" :aria-label="d.photo ? t('souk.stl.photoChange') : t('souk.stl.photoAdd')" @click="pickPhoto">
                  <img v-if="d.photo" :src="d.photo" alt="" class="w-full h-full object-cover" />
                  <span v-else class="w-full h-full st-tint st-fg flex flex-col items-center justify-center gap-1 text-[11px] font-semibold">
                    <Icon name="camera" :size="20" /><template v-if="data.canEdit">{{ t('souk.stl.photoAdd') }}</template>
                  </span>
                  <span v-if="uploading" class="absolute inset-0 bg-white/70 flex items-center justify-center"><Icon name="refresh-cw" :size="18" class="animate-spin" /></span>
                </button>
                <input ref="fileEl" type="file" accept="image/*" capture="environment" class="hidden" @change="onPhoto" />
                <div class="min-w-0 flex-1 flex flex-col gap-1">
                  <h1 class="text-[19px] sm:text-[22px] font-extrabold text-stone-900 leading-tight break-words ltr:text-left rtl:text-right" dir="ltr">{{ d.label }}</h1>
                  <div class="text-[13px] text-stone-700 inline-flex items-center gap-1"><Icon name="map-pin" :size="13" class="shrink-0 st-fg" />{{ d.place || t('souk.stl.noPlace') }}</div>
                  <div class="text-[12px] text-stone-500">{{ tt('souk.stl.since', { d: day(d.since) }) }}<template v-if="d.disabled"> · {{ t('souk.stl.disabledTag') }}</template></div>
                  <div v-if="d.cats.length" class="flex flex-wrap gap-1 pt-0.5">
                    <span v-for="c in d.cats" :key="c" class="text-[11px] font-semibold rounded-full px-2 py-0.5 bg-white/85 ring-1 ring-inset ring-stone-200 text-stone-700">{{ catName(c) }}</span>
                  </div>
                </div>
              </div>
              <div class="flex flex-wrap gap-2">
                <a v-if="d.phone" :href="'tel:' + d.phone" class="btn btn-st inline-flex items-center"><Icon name="phone" :size="15" />{{ t('souk.stl.call') }}<span class="font-normal opacity-90" dir="ltr">{{ d.phone }}</span></a>
                <a v-if="d.wa" :href="'https://wa.me/' + d.wa" target="_blank" rel="noopener" class="btn btn-line inline-flex items-center"><Icon name="whatsapp" :size="15" />{{ t('souk.stl.whatsapp') }}</a>
                <span v-if="!d.phone" class="text-[13px] text-stone-600 self-center">{{ t('souk.stl.noPhone') }}</span>
                <button v-if="data.canEdit && !editing" class="btn btn-line inline-flex items-center ms-auto" @click="startEdit"><Icon name="pen-line" :size="14" />{{ t('souk.stl.edit') }}</button>
              </div>
              <p v-if="d.note && !editing" class="text-[13px] text-stone-700 bg-white/80 rounded-xl px-3 py-2 ring-1 ring-inset ring-stone-200 whitespace-pre-line" dir="auto">{{ d.note }}</p>
            </header>

            <!-- edit -->
            <section v-if="editing" class="sk-sec">
              <div class="sk-sec-h"><span class="sk-ico"><Icon name="pen-line" :size="16" /></span><h2 class="sk-sec-t flex-1">{{ t('souk.stl.edit') }}</h2></div>
              <div class="sk-sec-b flex flex-col gap-3">
                <StallFields :f="ed" :cats="data.categories" :cat-name="catName" with-name />
                <div class="flex flex-wrap gap-2">
                  <button class="btn btn-st inline-flex items-center" :disabled="busy || nameShort(ed.label)" @click="saveEdit"><Icon name="check" :size="15" :stroke-width="2.4" />{{ t('souk.stl.save') }}</button>
                  <button class="btn btn-line inline-flex items-center" @click="editing = false">{{ t('souk.stl.cancel') }}</button>
                  <button v-if="d.full" class="btn btn-line inline-flex items-center ms-auto" :disabled="busy" @click="toggleDisabled">
                    <Icon :name="d.disabled ? 'unlock' : 'ban'" :size="14" />{{ d.disabled ? t('souk.stl.enable') : t('souk.stl.disable') }}
                  </button>
                </div>
              </div>
            </section>

            <!-- balance -->
            <section class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="wallet" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col"><h2 class="sk-sec-t">{{ t('souk.stl.balanceTitle') }}</h2><span class="sk-sec-s">{{ t('souk.stl.balanceSub') }}</span></div>
              </div>
              <div class="sk-sec-b flex flex-col gap-3">
                <div class="flex items-end justify-between gap-3 flex-wrap">
                  <div class="flex flex-col">
                    <span class="text-[12px] font-semibold text-stone-600">{{ balLabel(d.account.balance) }}</span>
                    <span class="text-[28px] font-extrabold tabular-nums leading-tight" :class="balCls(d.account.balance)" dir="ltr">{{ fmt(Math.abs(d.account.balance)) }} MAD</span>
                  </div>
                  <div class="flex flex-col items-end gap-1">
                    <span v-if="d.account.overdue" class="chip bg-rose-50 text-rose-800"><Icon name="alert-triangle" :size="12" />{{ tt('souk.stl.overdue', { n: fmt(d.account.overdue) }) }}</span>
                    <span v-if="d.account.nextDue" class="text-[12px] text-stone-600">{{ tt('souk.stl.nextDue', { d: day(d.account.nextDue.date), n: fmt(d.account.nextDue.amount) }) }}</span>
                  </div>
                </div>
                <dl v-if="d.full" class="flex flex-col divide-y divide-stone-100 rounded-xl ring-1 ring-inset ring-stone-200 text-[13px]">
                  <div class="flex justify-between gap-3 px-3 py-2"><dt class="text-stone-600">{{ t('souk.stl.books') }}</dt><dd class="font-semibold tabular-nums" dir="ltr">{{ fmt(d.account.books) }}</dd></div>
                  <div class="flex justify-between gap-3 px-3 py-2"><dt class="text-stone-600">+ {{ t('souk.stl.unbilled') }}</dt><dd class="font-semibold tabular-nums" dir="ltr">{{ fmt(d.account.unbilled) }}</dd></div>
                  <div class="flex justify-between gap-3 px-3 py-2"><dt class="text-stone-600">− {{ t('souk.stl.owedBack') }}</dt><dd class="font-semibold tabular-nums" dir="ltr">{{ fmt(d.account.owedBack) }}</dd></div>
                </dl>
                <p v-else class="text-[12px] text-stone-500 inline-flex items-start gap-1.5"><Icon name="info" :size="13" class="shrink-0 mt-0.5" />{{ t('souk.stl.buyerNote') }}</p>
              </div>
            </section>

            <!-- track record -->
            <section class="sk-sec">
              <div class="sk-sec-h"><span class="sk-ico"><Icon name="activity" :size="16" /></span><h2 class="sk-sec-t flex-1">{{ t('souk.stl.statsTitle') }}</h2></div>
              <div class="sk-sec-b grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                <div class="stat"><span>{{ t('souk.stl.stBuys') }}</span><b>{{ d.stats.buys }}</b></div>
                <div v-if="d.full" class="stat"><span>{{ t('souk.stl.stBought') }}</span><b dir="ltr">{{ fmt(d.stats.bought) }} MAD</b></div>
                <div class="stat"><span>{{ t('souk.stl.stIssues') }}</span>
                  <b :class="d.stats.issueRate >= 20 ? 'text-amber-800' : ''">{{ d.stats.issues }}<template v-if="d.stats.issueRate != null"> · {{ d.stats.issueRate }}%</template></b></div>
              </div>
              <div v-if="d.products.length" class="px-3.5 pb-3.5 flex flex-col gap-2">
                <span class="text-[12px] font-semibold text-stone-600">{{ t('souk.stl.products') }}</span>
                <div class="flex gap-2 overflow-x-auto pb-1">
                  <router-link v-for="p in d.products" :key="p.name" :to="{ name: 'SoukProduct', params: { name: p.name } }" class="shrink-0 w-[92px] flex flex-col gap-1">
                    <img v-if="p.image" :src="p.image" alt="" class="w-[92px] h-[92px] rounded-xl object-cover ring-1 ring-stone-200" />
                    <span v-else class="w-[92px] h-[92px] rounded-xl st-tint st-fg flex items-center justify-center"><Icon name="image" :size="18" /></span>
                    <span class="text-[11px] text-stone-700 leading-snug line-clamp-2" dir="auto">{{ p.title }}</span>
                  </router-link>
                </div>
              </div>
            </section>

            <!-- statement: the manager and the accountant only (the server sends it to nobody else) -->
            <section v-if="d.statement" class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="file-text" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col"><h2 class="sk-sec-t">{{ t('souk.stl.statement') }}</h2><span class="sk-sec-s">{{ t('souk.stl.statementSub') }}</span></div>
              </div>
              <div class="flex flex-col">
                <div class="px-3.5 pt-3 pb-1 text-[12px] font-bold text-stone-600">{{ t('souk.stl.purchases') }} · {{ d.statement.lines.length }}</div>
                <div v-for="l in d.statement.lines" :key="l.po" class="px-3.5 py-2.5 border-t border-stone-100 flex flex-col gap-1">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-[12px] text-stone-500 tabular-nums">{{ day(l.date) }}</span>
                    <a :href="'/app/purchase-order/' + l.po" target="_blank" rel="noopener" class="mono text-[12px] text-stone-700 underline-offset-2 hover:underline" dir="ltr" :title="t('souk.stl.openDesk')">{{ l.po }}</a>
                    <span class="text-[11px] font-bold rounded-full px-2 py-0.5" :class="stateCls(l.state)">{{ t('souk.stl.st_' + l.state) }}</span>
                    <span class="ms-auto text-[14px] font-bold tabular-nums text-stone-900" dir="ltr">{{ fmt(l.total) }} MAD</span>
                  </div>
                  <div class="text-[12px] text-stone-600 flex flex-wrap gap-x-2 gap-y-0.5">
                    <span v-if="l.method">{{ t('souk.stl.m_' + l.method) }}<template v-if="l.ref">{{ " " }}<span dir="ltr">{{ l.ref }}</span></template><template v-if="l.due"> · {{ tt('souk.stl.dueOn', { d: day(l.due) }) }}</template></span>
                    <span v-if="l.unpaid && l.state !== 'paid'" class="font-semibold" :class="l.overdue ? 'text-rose-700' : 'text-stone-800'">{{ tt('souk.stl.unpaid', { n: fmt(l.unpaid) }) }}</span>
                    <span v-if="l.owed" class="text-amber-800">{{ tt('souk.stl.owedLine', { n: fmt(l.owed) }) }}<template v-if="l.debitNote"> · <span class="mono" dir="ltr">{{ l.debitNote }}</span></template></span>
                    <span v-if="l.nothingArrived" class="text-rose-700">{{ t('souk.stl.nothingArrived') }}</span>
                    <span v-else-if="!l.received" class="text-stone-500">{{ t('souk.stl.notReceived') }}</span>
                    <a v-if="l.receipt" :href="l.receipt" target="_blank" rel="noopener" class="st-ink font-semibold underline-offset-2 hover:underline">{{ t('souk.stl.receipt') }}</a>
                    <router-link v-if="l.product" :to="{ name: 'SoukProduct', params: { name: l.product } }" class="mono st-ink" dir="ltr">{{ l.product }}</router-link>
                  </div>
                </div>

                <div class="px-3.5 pt-3 pb-1 border-t border-stone-200 text-[12px] font-bold text-stone-600">{{ t('souk.stl.payments') }}</div>
                <div v-if="!d.statement.payments.length" class="px-3.5 pb-3 text-[13px] text-stone-500">{{ t('souk.stl.noPayments') }}</div>
                <div v-for="p in d.statement.payments" :key="p.voucher" class="px-3.5 py-2 border-t border-stone-100 flex items-center gap-2">
                  <span class="text-[12px] text-stone-500 tabular-nums">{{ day(p.date) }}</span>
                  <a :href="'/app/' + slug(p.type) + '/' + p.voucher" target="_blank" rel="noopener" class="mono text-[12px] text-stone-700 hover:underline" dir="ltr">{{ p.voucher }}</a>
                  <span class="ms-auto text-[13px] font-bold tabular-nums" :class="p.amount >= 0 ? 'text-emerald-700' : 'text-stone-800'" dir="ltr">{{ fmt(p.amount) }} MAD</span>
                </div>

                <template v-if="d.statement.returns.length">
                  <div class="px-3.5 pt-3 pb-1 border-t border-stone-200 text-[12px] font-bold text-stone-600">{{ t('souk.stl.returns') }}</div>
                  <div v-for="r in d.statement.returns" :key="r.name" class="px-3.5 py-2 border-t border-stone-100 flex items-center gap-2">
                    <span class="text-[12px] text-stone-500 tabular-nums">{{ day(r.date) }}</span>
                    <a :href="'/app/purchase-invoice/' + r.name" target="_blank" rel="noopener" class="mono text-[12px] text-stone-700 hover:underline" dir="ltr">{{ r.name }}</a>
                    <span class="ms-auto text-[13px] font-bold tabular-nums text-emerald-700" dir="ltr">{{ fmt(r.amount) }} MAD</span>
                  </div>
                </template>
              </div>
            </section>
          </template>
        </div>

        <!-- a desk with no stall picked: a quiet hint -->
        <div v-else class="hidden lg:flex sk-sec px-6 py-16 flex-col items-center text-center gap-3">
          <span class="sk-ico sk-ico-lg"><Icon name="store" :size="22" /></span>
          <p class="text-[14px] text-stone-600 max-w-[360px]">{{ t('souk.stl.sub') }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, defineComponent, h } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { uploadPhoto } from "@/lib/soukPhoto";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t, locale } = useI18n();
const { success, warn } = useToast();
const route = useRoute();
const router = useRouter();

const tt = (k, vars = {}) => {
  let s = String(t(k));
  for (const [a, b] of Object.entries(vars)) s = s.split("{" + a + "}").join(String(b ?? ""));
  return s;
};
const fmt = (n) => Math.round(Number(n || 0)).toLocaleString("fr-FR");
const isAr = computed(() => locale.value === "ar");
const day = (s) => {
  if (!s) return "";
  const d = new Date(String(s).slice(0, 10) + "T12:00:00");
  if (isNaN(d)) return String(s);
  return d.toLocaleDateString(isAr.value ? "ar-MA" : locale.value === "fr" ? "fr-FR" : "en-GB",
    { day: "numeric", month: "short", year: d.getFullYear() === new Date().getFullYear() ? undefined : "numeric" });
};
const slug = (dt) => String(dt || "").toLowerCase().replace(/\s+/g, "-");
const nameShort = (s) => String(s || "").replace(/[^A-Za-z0-9]/g, "").length < 3;

// ── the list ──────────────────────────────────────────────────────────────
const data = ref(null);
const loading = ref(true);
const q = ref("");
const cat = ref("");
const name = computed(() => String(route.params.name || ""));

async function load() {
  loading.value = true;
  try {
    data.value = await api("souk_stalls.stalls_boot");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

const catName = (k) => {
  const c = (data.value?.categories || []).find((x) => x.key === k);
  return c ? (isAr.value ? c.ar : c.fr) : k;
};
const usedCats = computed(() => {
  const used = new Set((data.value?.stalls || []).flatMap((s) => s.cats || []));
  return (data.value?.categories || []).filter((c) => used.has(c.key));
});
const norm = (s) => String(s || "").toLowerCase().replace(/[\s.'&-]/g, "");
const shown = computed(() => {
  const n = norm(q.value), digits = q.value.replace(/\D/g, "");
  return (data.value?.stalls || []).filter((s) => {
    if (cat.value && !(s.cats || []).includes(cat.value)) return false;
    if (!n) return true;
    return norm(s.label).includes(n) || norm(s.place).includes(n) || (digits.length >= 3 && String(s.phone).replace(/\D/g, "").includes(digits));
  });
});
const owedSum = computed(() => (data.value?.stalls || []).reduce((a, s) => a + Math.max(0, s.balance), 0));
const creditSum = computed(() => (data.value?.stalls || []).reduce((a, s) => a + Math.max(0, -s.balance), 0));

// Positive: we owe the stall. Negative: the stall owes us.
const balCls = (b) => (b > 0.5 ? "text-stone-900" : b < -0.5 ? "text-emerald-700" : "text-stone-400");
const balText = (b) => (Math.abs(b) < 0.5 ? "0" : fmt(Math.abs(b)) + " MAD");
const balLabel = (b) => (b > 0.5 ? t("souk.stl.owedTo") : b < -0.5 ? t("souk.stl.owedBy") : t("souk.stl.settled"));
const stateCls = (s) => ({
  paidAtStall: "bg-stone-100 text-stone-700", paid: "bg-emerald-50 text-emerald-700",
  invoiced: "bg-sky-50 text-sky-800", notInvoiced: "bg-amber-50 text-amber-900", overdue: "bg-rose-50 text-rose-700",
}[s] || "bg-stone-100 text-stone-700");

// ── one stall ─────────────────────────────────────────────────────────────
const d = ref(null);
async function loadOne(n) {
  d.value = null;
  editing.value = false;
  if (!n) return;
  try {
    const r = await api("souk_stalls.stall", { name: n });
    if (name.value === n) d.value = r;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    router.replace({ name: "SoukStalls" });
  }
}
watch(name, (n) => loadOne(n));

// A stall's row in the list follows its edits without a reload.
function syncRow(r) {
  const s = (data.value?.stalls || []).find((x) => x.name === r.name);
  if (s) Object.assign(s, { label: r.label, phone: r.phone, place: r.place, photo: r.photo, cats: r.cats, disabled: r.disabled });
}

const editing = ref(false);
const busy = ref(false);
const ed = reactive({ label: "", phone: "", place: "", sells: [], note: "", sure: false });
function startEdit() {
  Object.assign(ed, { label: d.value.label, phone: d.value.phone, place: d.value.place, sells: [...d.value.sells], note: d.value.note, sure: false });
  editing.value = true;
}
async function saveEdit() {
  busy.value = true;
  try {
    const r = await apiPost("souk_stalls.save_stall", { name: d.value.name, payload: JSON.stringify(ed) });
    d.value = r;
    syncRow(r);
    editing.value = false;
    success(t("souk.stl.saved"), "");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}
async function toggleDisabled() {
  busy.value = true;
  try {
    const r = await apiPost("souk_stalls.save_stall", { name: d.value.name, payload: JSON.stringify({ disabled: d.value.disabled ? 0 : 1 }) });
    d.value = r;
    syncRow(r);
    editing.value = false;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

const fileEl = ref(null);
const uploading = ref(false);
function pickPhoto() { fileEl.value?.click(); }
async function onPhoto(ev) {
  const file = ev.target.files && ev.target.files[0];
  ev.target.value = "";
  if (!file || !d.value) return;
  uploading.value = true;
  try {
    const r = await uploadPhoto("stall", d.value.name, file);
    d.value.photo = r.url;
    syncRow(d.value);
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    uploading.value = false;
  }
}

// ── a new stall ───────────────────────────────────────────────────────────
// In the URL (?new=1): the shell remounts the page on every route change.
const creating = computed(() => route.query.new === "1");
const nf = reactive({ label: "", phone: "", place: "", sells: [], note: "", sure: false });
const nfMatch = ref([]);
let nfTimer = null;
function openCreate() {
  Object.assign(nf, { label: "", phone: "", place: "", sells: [], note: "", sure: false });
  nfMatch.value = [];
  router.push({ name: "SoukStalls", query: { new: "1" } });
}
const closeCreate = () => router.push({ name: "SoukStalls" });
watch(() => [nf.label, nf.phone], ([label, phone]) => {
  clearTimeout(nfTimer);
  nf.sure = false;
  if (nameShort(label) && String(phone).replace(/\D/g, "").length < 9) { nfMatch.value = []; return; }
  nfTimer = setTimeout(async () => {
    try {
      const r = await api("souk_stalls.similar_stalls", { name: label, phone });
      if (nf.label === label && nf.phone === phone) nfMatch.value = (r && r.rows) || [];
    } catch (_) { nfMatch.value = []; }
  }, 450);
});
async function create() {
  busy.value = true;
  try {
    const r = await apiPost("souk_stalls.create_stall", { payload: JSON.stringify({ ...nf, name: nf.label }) });
    success(t("souk.stl.created"), r.label);
    await load();
    router.push({ name: "SoukStalls", params: { name: r.name } });
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

// The fields of a stall, shared by "new" and "edit".
const StallFields = defineComponent({
  props: { f: Object, cats: Array, catName: Function, withName: Boolean },
  setup(p) {
    const field = (id, label, input) => h("div", { class: "flex flex-col gap-1.5" }, [
      h("label", { for: id, class: "text-[13px] font-semibold text-stone-700" }, label), input]);
    const cls = "w-full h-11 rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 text-[16px]";
    return () => h("div", { class: "flex flex-col gap-3" }, [
      h("div", { class: "grid grid-cols-1 sm:grid-cols-2 gap-3" }, [
        p.withName ? field("stl-name", t("souk.stl.nameLbl"), h("input", {
          id: "stl-name", value: p.f.label, dir: "ltr", placeholder: "AMINE DERB OMAR", autocomplete: "off", class: cls + " uppercase",
          onInput: (e) => { p.f.label = e.target.value; } })) : null,
        field("stl-phone", t("souk.stl.phoneLbl"), h("input", {
          id: "stl-phone", value: p.f.phone, dir: "ltr", type: "tel", inputmode: "tel", placeholder: "06…", class: cls,
          onInput: (e) => { p.f.phone = e.target.value; } })),
      ]),
      field("stl-place", t("souk.stl.placeLbl"), h("input", {
        id: "stl-place", value: p.f.place, placeholder: t("souk.stl.placePh"), class: cls,
        onInput: (e) => { p.f.place = e.target.value; } })),
      h("div", { class: "flex flex-col gap-1.5" }, [
        h("span", { class: "text-[13px] font-semibold text-stone-700" }, t("souk.stl.sellsLbl")),
        h("div", { class: "flex flex-wrap gap-1.5", role: "group" }, (p.cats || []).map((c) => h("button", {
          type: "button", class: "cat", "aria-pressed": String(p.f.sells.includes(c.key)),
          onClick: () => { const i = p.f.sells.indexOf(c.key); if (i >= 0) p.f.sells.splice(i, 1); else p.f.sells.push(c.key); },
        }, p.catName(c.key)))),
      ]),
      field("stl-note", t("souk.stl.noteLbl"), h("textarea", {
        id: "stl-note", value: p.f.note, rows: 2, placeholder: t("souk.stl.notePh"), dir: "auto",
        class: "w-full rounded-lg ring-1 ring-inset ring-stone-300 bg-white px-3 py-2 text-[16px]",
        onInput: (e) => { p.f.note = e.target.value; } })),
    ]);
  },
});

onMounted(async () => {
  await load();
  if (name.value) loadOne(name.value);
});
</script>

<style scoped>
.btn { flex-shrink: 0; height: 2.75rem; padding-block: 0; padding-inline: 0.875rem; border-radius: 0.75rem; font-size: 13px; font-weight: 600;
  gap: 0.375rem; white-space: nowrap; }
@media (min-width: 1024px) { .btn { height: 2.375rem; } }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.btn-sm { height: 2.25rem; padding-inline: 0.625rem; font-size: 12px; }
.btn-st { background: rgb(var(--st)); color: #fff; font-weight: 700; box-shadow: 0 6px 16px -8px rgb(var(--st)); }
.btn-st:not(:disabled):hover { background: rgb(var(--st-ink)); }
.btn-st:disabled { background: rgb(231 229 228); color: rgb(87 83 78); box-shadow: none; opacity: 1; }
.btn-line { background: rgb(255 255 255 / .85); color: rgb(28 25 23); box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.btn-line:not(:disabled):hover { background: #fff; }
:global(html[data-theme="dark"] .st-buying .btn-st) { color: rgb(28 25 23); }
:global(html[data-theme="dark"] .st-buying .btn-line) { background: #292524; color: #f5f5f4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }

.chip { display: inline-flex; align-items: center; gap: 4px; min-height: 28px; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; }
.chip b { font-weight: 800; }

/* category chips: picked = the stage tint + ring */
:deep(.cat) { flex-shrink: 0; min-height: 36px; padding: 0 12px; border-radius: 9999px; font-size: 13px; font-weight: 600;
  background: #fff; color: rgb(68 64 60); box-shadow: inset 0 0 0 1px rgb(214 211 209); white-space: nowrap; }
:deep(.cat[aria-pressed="true"]) { background: rgb(var(--st) / .10); color: rgb(var(--st-ink)); box-shadow: inset 0 0 0 2px rgb(var(--st)); }
:global(html[data-theme="dark"] .st-buying .cat) { background: #292524; color: #e7e5e4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }

.stat { display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; border-radius: 12px; background: rgb(var(--st) / .05);
  box-shadow: inset 0 0 0 1px rgb(var(--st) / .14); }
.stat span { font-size: 12px; color: rgb(87 83 78); }
.stat b { font-size: 17px; font-weight: 800; color: rgb(28 25 23); font-variant-numeric: tabular-nums; }
:global(html[data-theme="dark"] .st-buying .stat b) { color: #f5f5f4; }
:global(html[data-theme="dark"] .st-buying .stat span) { color: rgb(168 162 158); }
</style>
