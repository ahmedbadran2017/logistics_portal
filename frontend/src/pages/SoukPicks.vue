<template>
  <!-- Selection (الاختيار, 2026-11-20): what the Derb Omar wholesalers post on
       their public Telegram channels, read every 3 hours. The same photo
       posted by several channels is ONE pick. Anyone in the souk marks what
       they would sell; the decider (settings: Manal) says buy — how many, at
       what max cost, from whom — or no, with a reason. "Buy" picks make the
       shopping list, grouped by source; the buyer opens SoukBuy from it.
       Backend: souk_picks.picks_boot / pick / pick_interest / pick_decide /
       create_source / import_sources / disable_source / scrape_now /
       save_deciders. -->
  <div class="st-buying px-4 sm:px-5 pt-5 sm:pt-6 pb-10 max-w-[1240px] mx-auto flex flex-col gap-4">
    <header class="sk-hero flex flex-col gap-3">
      <div class="flex items-start gap-3">
        <span class="sk-ico sk-ico-lg sk-ico-solid"><Icon name="sparkles" :size="20" :stroke-width="2" /></span>
        <div class="min-w-0 flex-1">
          <h1 class="text-[19px] font-extrabold text-stone-900 leading-tight">{{ t('souk.pk.title') }}</h1>
          <p class="text-[12px] text-stone-600 leading-normal">{{ tt('souk.pk.sub', { who: deciderNames || '—' }) }}</p>
        </div>
      </div>
      <nav class="flex gap-1.5 overflow-x-auto -mx-1 px-1 pb-0.5" :aria-label="t('souk.pk.title')">
        <button v-for="x in TABS" :key="x" type="button" class="cat inline-flex items-center gap-1.5" :aria-pressed="tab === x" @click="go(x)">
          {{ t('souk.pk.tab_' + x) }}
          <span v-if="tabCount(x)" class="min-w-5 h-5 px-1.5 rounded-full text-[11px] font-bold inline-flex items-center justify-center"
                :class="tab === x ? 'bg-[rgb(var(--st))] text-white' : 'bg-stone-100 text-stone-700'">{{ tabCount(x) }}</span>
        </button>
      </nav>
    </header>

    <div v-if="data && !data.ready" class="sk-sec px-5 py-8 text-center text-[14px] text-stone-600">{{ t('souk.pk.notReady') }}</div>

    <!-- ── feed / waiting / done: the photo grid ───────────────────────── -->
    <template v-else-if="tab === 'feed' || tab === 'interest' || tab === 'done'">
      <div v-if="tab === 'feed'" class="flex flex-col gap-2">
        <label class="relative block">
          <span class="sr-only">{{ t('souk.pk.searchPh') }}</span>
          <Icon name="search" :size="16" class="absolute top-1/2 -translate-y-1/2 start-3 text-stone-400 pointer-events-none" />
          <input v-model="q" type="search" :placeholder="t('souk.pk.searchPh')" autocomplete="off"
                 class="w-full h-11 rounded-xl ring-1 ring-inset ring-stone-300 bg-white ps-9 pe-3 text-[15px]" @keydown.enter="reload" />
        </label>
        <div class="flex gap-1.5 overflow-x-auto -mx-1 px-1" role="group" :aria-label="t('souk.pk.filter')">
          <button type="button" class="cat" :aria-pressed="!only" @click="setOnly('')">{{ t('souk.pk.all') }}</button>
          <button type="button" class="cat inline-flex items-center gap-1" :aria-pressed="only === 'trending'" @click="setOnly('trending')">
            <Icon name="trending-up" :size="14" />{{ t('souk.pk.trending') }}
          </button>
          <button type="button" class="cat" :aria-pressed="only === 'saturated'" @click="setOnly('saturated')">{{ t('souk.pk.saturated') }}</button>
          <button v-if="onlySource" type="button" class="cat" aria-pressed="true" @click="setOnly('')">{{ onlySource }} ✕</button>
        </div>
        <!-- What each pick is (Claude Haiku reads the photo and caption after every read). -->
        <div v-if="kindChips.length" class="flex gap-1.5 overflow-x-auto -mx-1 px-1" role="group" :aria-label="t('souk.pk.kindFilter')">
          <button type="button" class="cat" :aria-pressed="!kind" @click="setKind('')">{{ t('souk.pk.allKinds') }}</button>
          <button v-for="k in kindChips" :key="k.k" type="button" class="cat inline-flex items-center gap-1" :aria-pressed="kind === k.k" @click="setKind(k.k)">
            {{ t('souk.pk.k_' + k.k) }}<span class="text-[11px] tabular-nums opacity-70">{{ k.n }}</span>
          </button>
          <button v-if="data?.kinds?.noise" type="button" class="cat inline-flex items-center gap-1 text-stone-500" :aria-pressed="kind === 'noise'" @click="setKind('noise')">
            <Icon name="eye-off" :size="13" />{{ t('souk.pk.k_noise') }}<span class="text-[11px] tabular-nums opacity-70">{{ data.kinds.noise }}</span>
          </button>
        </div>
        <p v-if="data?.untagged" class="text-[12px] text-stone-600 flex flex-wrap items-center gap-x-2 gap-y-1">
          <span>{{ tt(data.tagOn ? 'souk.pk.untagged' : 'souk.pk.untaggedOff', { n: data.untagged }) }}</span>
          <button v-if="data.tagOn && data.isManager" type="button" class="font-bold st-ink underline underline-offset-2" :disabled="saving" @click="tagNow">{{ t('souk.pk.tagNow') }}</button>
        </p>
        <p v-if="kind === 'noise'" class="text-[12px] text-stone-600 leading-normal">{{ t('souk.pk.noiseHint') }}</p>
      </div>
      <p v-if="tab === 'interest'" class="text-[13px] text-stone-600 leading-normal">
        {{ data?.canDecide ? t('souk.pk.interestYou') : tt('souk.pk.interestWait', { who: deciderNames || '—' }) }}
      </p>

      <div v-if="loading && !rows.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div v-for="i in 10" :key="i" class="aspect-[3/4] sk-sec animate-pulse" />
      </div>
      <div v-else-if="!rows.length" class="sk-sec px-5 py-10 text-center text-[14px] text-stone-600">{{ t('souk.pk.empty_' + tab) }}</div>
      <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <article v-for="p in rows" :key="p.name" class="sk-sec flex flex-col">
          <button type="button" class="relative block aspect-square bg-stone-100" :aria-label="tt('souk.pk.open', { t: p.title })" @click="open(p.name)">
            <img v-if="p.photo" :src="p.photo" alt="" loading="lazy" class="absolute inset-0 w-full h-full object-cover" />
            <span class="absolute top-1.5 start-1.5 flex flex-wrap gap-1">
              <span v-if="p.trending" class="badge bg-rose-600 text-white"><Icon name="trending-up" :size="11" />{{ tt('souk.pk.nSources', { n: p.trendN }) }}</span>
              <span v-else-if="p.sourcesN > 1" class="badge bg-white/90 text-stone-800"><Icon name="layers" :size="11" />{{ tt('souk.pk.nSources', { n: p.sourcesN }) }}</span>
              <span v-if="p.saturated" class="badge bg-stone-800/85 text-white">{{ t('souk.pk.saturated') }}</span>
            </span>
            <span v-if="p.status !== 'new' && p.status !== 'interested'" class="absolute bottom-1.5 start-1.5 badge" :class="statusCls(p.status)">{{ t('souk.pk.st_' + p.status) }}</span>
            <span v-if="p.priceSeen" class="absolute bottom-1.5 end-1.5 badge bg-white/95 text-stone-900 tabular-nums" dir="ltr">{{ fmt(p.priceSeen) }} MAD</span>
            <span v-if="p.packN" class="absolute top-1.5 end-1.5 badge bg-white/95 text-stone-800 tabular-nums">{{ tt('souk.pk.packN', { n: p.packN }) }}</span>
          </button>
          <div class="p-2.5 flex flex-col gap-1 flex-1">
            <span class="text-[13px] font-semibold text-stone-900 leading-snug line-clamp-2" dir="auto">{{ p.title || '—' }}</span>
            <button v-if="p.kind && p.kind !== 'noise' && tab === 'feed'" type="button" class="self-start text-[11px] font-semibold px-1.5 py-0.5 rounded-md bg-stone-100 text-stone-700 hover:bg-stone-200"
                    :aria-label="tt('souk.pk.showKind', { k: t('souk.pk.k_' + p.kind) })" @click="setKind(p.kind)">{{ t('souk.pk.k_' + p.kind) }}</button>
            <span class="text-[11px] text-stone-500 truncate" dir="auto">
              {{ p.sources[0]?.label || '—' }}<template v-if="p.sources.length > 1"> +{{ p.sources.length - 1 }}</template> · {{ ago(p.lastSeen) }}
            </span>
            <span v-if="p.status === 'rejected'" class="text-[11px] text-stone-600">{{ t('souk.pk.why_' + p.reason) }}</span>
            <div v-if="p.status === 'new' || p.status === 'interested'" class="mt-auto pt-1 flex items-center gap-1.5">
              <button type="button" class="flex-1 h-10 rounded-lg text-[13px] font-bold inline-flex items-center justify-center gap-1.5"
                      :class="p.mine ? 'bg-[rgb(var(--st))] text-white' : 'bg-white ring-1 ring-inset ring-stone-300 text-stone-800'"
                      :aria-pressed="p.mine" :disabled="busy === p.name" @click="toggle(p)">
                <Icon name="thumbs-up" :size="14" />{{ t('souk.pk.interested') }}<template v-if="p.interested.length"> · {{ p.interested.length }}</template>
              </button>
              <button v-if="data?.canDecide" type="button" class="shrink-0 h-10 px-2.5 rounded-lg st-tint st-ink text-[13px] font-bold" @click="open(p.name)">{{ t('souk.pk.decide') }}</button>
            </div>
          </div>
        </article>
      </div>
      <button v-if="data?.more" type="button" class="self-center btn btn-line" :disabled="loading" @click="more">{{ t('souk.pk.more') }}</button>
    </template>

    <!-- ── the shopping list, one block per source ─────────────────────── -->
    <template v-else-if="tab === 'list'">
      <div v-if="loading && !data?.groups" class="h-[220px] sk-sec animate-pulse" />
      <div v-else-if="!(data?.groups || []).length" class="sk-sec px-5 py-10 text-center text-[14px] text-stone-600">{{ t('souk.pk.empty_list') }}</div>
      <section v-for="g in data?.groups || []" :key="g.source" class="sk-sec">
        <div class="sk-sec-h flex-wrap">
          <span class="sk-ico"><Icon name="store" :size="16" /></span>
          <div class="min-w-0 flex-1">
            <h2 class="sk-sec-t truncate" dir="ltr">{{ g.label || t('souk.pk.noSource') }}</h2>
            <p class="sk-sec-s">{{ tt('souk.pk.groupSum', { n: g.picks.length, q: g.pieces, b: fmt(g.budget) }) }}<template v-if="!g.stall && g.source"> · {{ t('souk.pk.leadTag') }}</template></p>
          </div>
          <a v-if="g.wa" :href="g.wa" target="_blank" rel="noopener" class="btn btn-line btn-sm inline-flex items-center"><Icon name="message-circle" :size="14" />WhatsApp</a>
          <a v-if="g.handle" :href="'https://t.me/' + g.handle" target="_blank" rel="noopener" class="btn btn-line btn-sm inline-flex items-center"><Icon name="send" :size="14" />Telegram</a>
        </div>
        <ul>
          <li v-for="(n, i) in g.picks" :key="n" class="flex items-center gap-3 px-3.5 py-2.5" :class="i ? 'border-t border-stone-100' : ''">
            <button type="button" class="w-14 h-14 shrink-0 rounded-xl overflow-hidden bg-stone-100 ring-1 ring-stone-200" :aria-label="tt('souk.pk.open', { t: byName[n]?.title })" @click="open(n)">
              <img v-if="byName[n]?.photo" :src="byName[n].photo" alt="" class="w-full h-full object-cover" />
            </button>
            <div class="min-w-0 flex-1 flex flex-col">
              <span class="text-[14px] font-semibold text-stone-900 truncate" dir="auto">{{ byName[n]?.title || '—' }}</span>
              <span class="text-[12px] text-stone-600 tabular-nums">{{ tt('souk.pk.targets', { q: byName[n]?.targetQty, p: fmt(byName[n]?.maxPrice) }) }}</span>
              <span v-if="byName[n]?.decidedBy" class="text-[11px] text-stone-500">{{ tt('souk.pk.decidedBy', { who: byName[n].decidedBy, d: ago(byName[n].decidedAt) }) }}</span>
            </div>
            <router-link v-if="data.canBuy" :to="{ name: 'SoukBuy', query: { pick: n } }" class="btn btn-st btn-sm inline-flex items-center">
              <Icon name="shopping-bag" :size="14" />{{ t('souk.pk.buyNow') }}
            </router-link>
          </li>
        </ul>
      </section>
    </template>

    <!-- ── sources ─────────────────────────────────────────────────────── -->
    <template v-else-if="tab === 'sources'">
      <div class="grid gap-4 lg:grid-cols-[380px_minmax(0,1fr)] items-start">
        <div class="flex flex-col gap-4">
          <section class="sk-sec">
            <div class="sk-sec-h"><span class="sk-ico"><Icon name="plus" :size="16" /></span><h2 class="sk-sec-t">{{ t('souk.pk.addTitle') }}</h2></div>
            <form class="sk-sec-b flex flex-col gap-3" @submit.prevent="addSource">
              <label class="flex flex-col gap-1">
                <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.pk.linkLbl') }}</span>
                <input v-model="nf.link" dir="ltr" autocomplete="off" placeholder="t.me/…" class="fld" />
              </label>
              <label class="flex flex-col gap-1">
                <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.pk.nameLbl') }}</span>
                <input v-model="nf.name" dir="ltr" autocomplete="off" placeholder="CASA GROS" class="fld" />
              </label>
              <label class="flex flex-col gap-1">
                <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.pk.phoneLbl') }}</span>
                <input v-model="nf.phone" dir="ltr" inputmode="tel" type="tel" autocomplete="off" placeholder="06…" class="fld" />
              </label>
              <p class="text-[12px] text-stone-600 leading-normal">{{ t('souk.pk.addNote') }}</p>
              <button type="submit" class="btn btn-st self-start inline-flex items-center" :disabled="saving || nf.link.trim().length < 5">
                <Icon name="check" :size="15" :stroke-width="2.4" />{{ t('souk.pk.addBtn') }}
              </button>
            </form>
          </section>

          <section v-if="data?.isManager" class="sk-sec">
            <div class="sk-sec-h"><span class="sk-ico"><Icon name="list-checks" :size="16" /></span><h2 class="sk-sec-t">{{ t('souk.pk.importTitle') }}</h2></div>
            <div class="sk-sec-b flex flex-col gap-3">
              <label class="flex flex-col gap-1">
                <span class="text-[12px] text-stone-600 leading-normal">{{ t('souk.pk.importNote') }}</span>
                <textarea v-model="importText" rows="6" dir="ltr" class="w-full rounded-lg ring-1 ring-inset ring-stone-300 bg-white p-2.5 text-[13px] font-mono" placeholder="CASA GROS	https://t.me/casa11gros"></textarea>
              </label>
              <button type="button" class="btn btn-st self-start" :disabled="saving || !importText.trim()" @click="doImport">{{ t('souk.pk.importBtn') }}</button>
              <p v-if="importResult" class="text-[13px] text-stone-700" role="status">{{ tt('souk.pk.importDone', importResult) }}</p>
              <ul v-if="importResult?.badList?.length" class="text-[12px] text-rose-800 list-disc ps-5">
                <li v-for="b in importResult.badList" :key="b" dir="auto">{{ b }}</li>
              </ul>
            </div>
          </section>

          <section v-if="data?.isManager" class="sk-sec">
            <div class="sk-sec-h"><span class="sk-ico"><Icon name="users" :size="16" /></span><h2 class="sk-sec-t">{{ t('souk.pk.decidersTitle') }}</h2></div>
            <div class="sk-sec-b flex flex-col gap-3">
              <label class="flex flex-col gap-1">
                <span class="text-[12px] text-stone-600 leading-normal">{{ t('souk.pk.decidersNote') }}</span>
                <input v-model="decidersText" dir="ltr" autocomplete="off" class="fld" />
              </label>
              <button type="button" class="btn btn-line self-start" :disabled="saving" @click="saveDeciders">{{ t('souk.pk.save') }}</button>
            </div>
          </section>
        </div>

        <section class="sk-sec">
          <div class="sk-sec-h">
            <span class="sk-ico"><Icon name="send" :size="16" /></span>
            <div class="min-w-0 flex-1">
              <h2 class="sk-sec-t">{{ tt('souk.pk.sourcesTitle', { n: (data?.sources || []).filter((s) => !s.disabled).length }) }}</h2>
              <p class="sk-sec-s">{{ t('souk.pk.sourcesSub') }}</p>
            </div>
            <button v-if="data?.isManager" type="button" class="btn btn-line btn-sm inline-flex items-center" :disabled="saving" @click="scrapeNow">
              <Icon name="refresh-cw" :size="14" />{{ t('souk.pk.readNow') }}
            </button>
          </div>
          <div v-if="!(data?.sources || []).length" class="px-5 py-8 text-center text-[14px] text-stone-600">{{ t('souk.pk.noSources') }}</div>
          <ul>
            <li v-for="(s, i) in data?.sources || []" :key="s.name" class="flex items-center gap-3 px-3.5 py-2.5 min-h-[64px]"
                :class="[i ? 'border-t border-stone-100' : '', s.disabled ? 'opacity-55' : '']">
              <div class="min-w-0 flex-1 flex flex-col gap-0.5">
                <div class="flex items-center gap-1.5 min-w-0">
                  <span class="text-[14px] font-semibold text-stone-900 truncate" dir="ltr">{{ s.label }}</span>
                  <span class="shrink-0 text-[11px] font-bold rounded px-1.5" :class="s.stall ? 'bg-emerald-50 text-emerald-800' : 'bg-stone-100 text-stone-600'">{{ s.stall ? t('souk.pk.stallTag') : t('souk.pk.leadTag') }}</span>
                  <span v-if="s.error" class="shrink-0 text-[11px] font-bold rounded px-1.5 bg-rose-50 text-rose-700">{{ s.error === 'private' ? t('souk.pk.errPrivate') : t('souk.pk.errRead') }}</span>
                </div>
                <span class="text-[12px] text-stone-600 truncate">
                  <a :href="s.link" target="_blank" rel="noopener" class="underline underline-offset-2" dir="ltr">@{{ s.handle }}</a>
                  · {{ tt('souk.pk.weekPosts', { n: s.week }) }}<template v-if="s.lastPost"> · {{ tt('souk.pk.lastPost', { d: ago(s.lastPost) }) }}</template>
                </span>
              </div>
              <button v-if="s.week" type="button" class="shrink-0 h-9 px-2.5 rounded-lg text-[12px] font-semibold st-ink st-tint" @click="showSource(s)">{{ t('souk.pk.seePosts') }}</button>
              <button v-if="data?.isManager" type="button" class="shrink-0 h-9 px-2.5 rounded-lg text-[12px] font-semibold text-stone-600 ring-1 ring-inset ring-stone-300"
                      :disabled="saving" @click="toggleSource(s)">{{ s.disabled ? t('souk.pk.enable') : t('souk.pk.disable') }}</button>
            </li>
          </ul>
        </section>
      </div>
    </template>

    <!-- ── one pick ────────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="name" class="fixed inset-0 z-[70] bg-stone-950/50 flex items-end sm:items-center justify-center st-buying" @click.self="close">
        <div class="w-full sm:max-w-[760px] max-h-[92vh] overflow-y-auto bg-[#faf9f7] rounded-t-3xl sm:rounded-3xl p-4 sm:p-5 space-y-4 pk-sheet"
             role="dialog" aria-modal="true" :aria-label="d?.title || t('souk.pk.title')">
          <div class="flex items-center gap-2">
            <h2 class="flex-1 min-w-0 text-[17px] font-extrabold text-stone-900 leading-snug" dir="auto">{{ d?.title || '…' }}</h2>
            <button type="button" class="w-11 h-11 rounded-full bg-white ring-1 ring-inset ring-stone-200 inline-flex items-center justify-center" :aria-label="t('souk.pk.close')" @click="close">
              <Icon name="x" :size="18" />
            </button>
          </div>
          <div v-if="!d" class="h-[300px] sk-sec animate-pulse" />
          <template v-else>
            <div class="grid gap-4 sm:grid-cols-[260px_minmax(0,1fr)]">
              <img v-if="d.photo" :src="d.photo" alt="" class="w-full h-[34vh] sm:h-auto sm:aspect-square object-cover rounded-2xl ring-1 ring-stone-200 bg-stone-100" />
              <div class="flex flex-col gap-2.5">
                <div class="flex flex-wrap gap-1.5">
                  <span class="chip" :class="statusCls(d.status)">{{ t('souk.pk.st_' + d.status) }}</span>
                  <span v-if="d.trending" class="chip bg-rose-50 text-rose-800"><Icon name="trending-up" :size="12" />{{ tt('souk.pk.trendSum', { n: d.trendN }) }}</span>
                  <span v-if="d.saturated" class="chip bg-stone-200 text-stone-800">{{ t('souk.pk.saturatedLong') }}</span>
                  <span v-if="d.priceSeen" class="chip bg-white ring-1 ring-inset ring-stone-200 text-stone-900">{{ tt('souk.pk.priceSeen', { p: fmt(d.priceSeen) }) }}</span>
                  <span class="chip bg-white ring-1 ring-inset ring-stone-200 text-stone-700">{{ tt('souk.pk.seenSum', { n: d.sourcesN, p: d.postsN, d: ago(d.firstSeen) }) }}</span>
                </div>
                <div v-if="d.interested.length" class="text-[13px] text-stone-700">
                  <Icon name="thumbs-up" :size="13" class="inline -mt-0.5" /> {{ d.interested.map((x) => x.name).join('، ') }}
                </div>
                <p v-if="d.note" class="text-[13px] text-stone-700 whitespace-pre-line leading-normal" dir="auto">{{ d.note }}</p>
                <div v-if="d.status === 'approved' || d.status === 'bought'" class="rounded-xl bg-sky-50 ring-1 ring-inset ring-sky-200 p-3 text-[13px] text-stone-800 flex flex-col gap-1">
                  <b>{{ tt('souk.pk.targets', { q: d.targetQty, p: fmt(d.maxPrice) }) }}</b>
                  <span>{{ tt('souk.pk.fromSrc', { s: srcLabel(d.source) }) }}</span>
                  <span class="text-stone-600">{{ tt('souk.pk.decidedBy', { who: d.decidedBy, d: ago(d.decidedAt) }) }}</span>
                  <router-link v-if="d.card" :to="{ name: 'SoukProduct', params: { name: d.card.name } }" class="font-semibold underline underline-offset-2">{{ d.card.sku_base }} · {{ d.card.title }}</router-link>
                </div>
                <div v-if="d.status === 'rejected'" class="rounded-xl bg-stone-100 p-3 text-[13px] text-stone-800">
                  {{ t('souk.pk.why_' + d.reason) }} · {{ tt('souk.pk.decidedBy', { who: d.decidedBy, d: ago(d.decidedAt) }) }}
                </div>
                <div class="flex flex-wrap gap-2">
                  <button v-if="d.status === 'new' || d.status === 'interested'" type="button" class="btn inline-flex items-center"
                          :class="d.mine ? 'btn-st' : 'btn-line'" :aria-pressed="d.mine" :disabled="busy === d.name" @click="toggle(d)">
                    <Icon name="thumbs-up" :size="15" />{{ d.mine ? t('souk.pk.interestedMine') : t('souk.pk.interested') }}
                  </button>
                  <button v-if="data?.canDecide && (d.status === 'approved' || d.status === 'rejected')" type="button" class="btn btn-line inline-flex items-center" :disabled="saving" @click="decide('undo')">
                    <Icon name="rotate-ccw" :size="15" />{{ t('souk.pk.undo') }}
                  </button>
                  <router-link v-if="d.status === 'approved' && data?.canBuy" :to="{ name: 'SoukBuy', query: { pick: d.name } }" class="btn btn-st inline-flex items-center">
                    <Icon name="shopping-bag" :size="15" />{{ t('souk.pk.buyNow') }}
                  </router-link>
                </div>
              </div>
            </div>

            <!-- the decision -->
            <section v-if="data?.canDecide && (d.status === 'new' || d.status === 'interested')" class="sk-sec">
              <div class="sk-sec-h"><span class="sk-ico"><Icon name="clipboard-check" :size="16" /></span><h3 class="sk-sec-t">{{ t('souk.pk.decision') }}</h3></div>
              <div class="sk-sec-b flex flex-col gap-3">
                <div class="grid grid-cols-2 gap-3">
                  <label class="flex flex-col gap-1">
                    <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.pk.qtyLbl') }}</span>
                    <input v-model.number="dec.qty" type="number" min="1" inputmode="numeric" dir="ltr" class="fld" />
                  </label>
                  <label class="flex flex-col gap-1">
                    <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.pk.maxLbl') }}</span>
                    <input v-model.number="dec.max" type="number" min="0" step="0.5" inputmode="decimal" dir="ltr" class="fld" />
                  </label>
                  <label class="flex flex-col gap-1">
                    <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.pk.srcLbl') }}</span>
                    <select v-model="dec.source" class="fld">
                      <option v-for="s in d.sources" :key="s.name" :value="s.name">{{ s.label }}</option>
                    </select>
                  </label>
                  <label class="flex flex-col gap-1">
                    <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.pk.catLbl') }}</span>
                    <select v-model="dec.category" class="fld">
                      <option value="">—</option>
                      <option v-for="c in data.categories" :key="c.key" :value="c.key">{{ locale === 'fr' ? c.fr : c.ar }}</option>
                    </select>
                  </label>
                </div>
                <label class="flex flex-col gap-1">
                  <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.pk.noteLbl') }}</span>
                  <input v-model="dec.note" dir="auto" autocomplete="off" class="fld" />
                </label>
                <button type="button" class="btn btn-st self-start inline-flex items-center" :disabled="saving || !(dec.qty > 0) || !(dec.max > 0) || !dec.source" @click="decide('buy')">
                  <Icon name="check" :size="15" :stroke-width="2.4" />{{ t('souk.pk.yesBtn') }}
                </button>
                <div class="border-t border-stone-100 pt-3 flex flex-col gap-2">
                  <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.pk.noLbl') }}</span>
                  <div class="flex flex-wrap gap-1.5" role="group" :aria-label="t('souk.pk.noLbl')">
                    <button v-for="r in data.reasons" :key="r" type="button" class="cat" :aria-pressed="dec.reason === r" @click="dec.reason = r">{{ t('souk.pk.why_' + r) }}</button>
                  </div>
                  <button type="button" class="btn btn-line self-start inline-flex items-center" :disabled="saving || !dec.reason" @click="decide('no')">
                    <Icon name="x" :size="15" />{{ t('souk.pk.noBtn') }}
                  </button>
                </div>
              </div>
            </section>

            <!-- who posted it -->
            <section class="sk-sec">
              <div class="sk-sec-h"><span class="sk-ico"><Icon name="send" :size="16" /></span><h3 class="sk-sec-t">{{ tt('souk.pk.postsTitle', { n: d.postsN }) }}</h3></div>
              <ul>
                <li v-for="(s, i) in d.sources" :key="s.name" class="flex items-center gap-2 px-3.5 py-2" :class="i ? 'border-t border-stone-100' : ''">
                  <span class="flex-1 min-w-0 text-[13px] font-semibold text-stone-900 truncate" dir="ltr">{{ s.label }}<span class="font-normal text-stone-500"> · {{ ago(s.last) }}</span></span>
                  <a v-if="s.wa" :href="s.wa" target="_blank" rel="noopener" class="shrink-0 h-9 px-2.5 rounded-lg ring-1 ring-inset ring-stone-300 text-[12px] font-semibold inline-flex items-center gap-1"><Icon name="message-circle" :size="13" />WhatsApp</a>
                  <a v-if="s.handle" :href="'https://t.me/' + s.handle" target="_blank" rel="noopener" class="shrink-0 h-9 px-2.5 rounded-lg ring-1 ring-inset ring-stone-300 text-[12px] font-semibold inline-flex items-center gap-1"><Icon name="send" :size="13" />@{{ s.handle }}</a>
                </li>
              </ul>
              <div class="border-t border-stone-100 p-3 grid grid-cols-2 sm:grid-cols-3 gap-3">
                <a v-for="p in d.posts" :key="p.name" :href="p.url" target="_blank" rel="noopener" class="flex flex-col gap-1 rounded-xl bg-white ring-1 ring-inset ring-stone-200 overflow-hidden">
                  <img v-if="p.thumb" :src="p.thumb" alt="" loading="lazy" class="w-full aspect-square object-cover bg-stone-100" />
                  <span class="px-2 text-[11px] font-semibold text-stone-800 truncate" dir="ltr">{{ p.label }} · {{ ago(p.at) }}</span>
                  <span v-if="p.caption" class="px-2 pb-2 text-[11px] text-stone-600 line-clamp-3 whitespace-pre-line" dir="auto">{{ p.caption }}</span>
                </a>
              </div>
            </section>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { siteToDate } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t, locale } = useI18n();
const { warn, success } = useToast();
const route = useRoute();
const router = useRouter();
const tt = (k, o) => Object.entries(o || {}).reduce((s, [a, b]) => s.split(`{${a}}`).join(String(b ?? "")), t(k));
const fmt = (n) => Number(n || 0).toLocaleString("fr-FR", { maximumFractionDigits: 2 });

const TABS = ["feed", "interest", "list", "done", "sources"];
const tab = computed(() => (TABS.includes(route.query.tab) ? route.query.tab : "feed"));
const name = computed(() => route.params.name || "");
const data = ref(null);
const rows = ref([]);
const loading = ref(false);
const busy = ref("");
const saving = ref(false);
const q = ref("");
const only = ref("");
const onlySource = ref("");
const kind = ref("");
// Largest first; "noise" (banners, price lists) has its own chip at the end.
const kindChips = computed(() => Object.entries(data.value?.kinds || {})
  .filter(([k, n]) => k !== "noise" && n > 0).sort((a, b) => b[1] - a[1]).map(([k, n]) => ({ k, n })));
const d = ref(null);
const dec = reactive({ qty: null, max: null, source: "", category: "", note: "", reason: "" });
const nf = reactive({ link: "", name: "", phone: "" });
const importText = ref("");
const importResult = ref(null);
const decidersText = ref("");

const deciderNames = computed(() => (data.value?.deciders || []).map((x) => x.name).join("، "));
const byName = computed(() => Object.fromEntries((data.value?.picks || []).map((p) => [p.name, p])));
function tabCount(x) {
  const c = data.value?.counts || {};
  return { interest: c.interested, list: c.approved }[x] || 0;
}
function statusCls(s) {
  return { approved: "bg-sky-600 text-white", bought: "bg-emerald-600 text-white", rejected: "bg-stone-700 text-white",
           interested: "bg-amber-100 text-amber-900", new: "bg-white ring-1 ring-inset ring-stone-200 text-stone-700" }[s] || "";
}
function srcLabel(n) {
  return (d.value?.sources || []).find((s) => s.name === n)?.label || n || "—";
}
function ago(s) {
  if (!s) return "";
  const dt = siteToDate(s) || new Date(String(s).replace(" ", "T"));
  const m = Math.max(0, Math.round((Date.now() - dt.getTime()) / 60000));
  // Arabic counts 3–10 take the plural (3 أيام, 11 يومًا): the *p keys.
  const say = (k, n) => tt(`souk.pk.${k}${n >= 3 && n <= 10 ? "p" : ""}`, { n });
  if (m < 60) return say("agoM", Math.max(1, m));
  if (m < 48 * 60) return say("agoH", Math.round(m / 60));
  return say("agoD", Math.round(m / 1440));
}

async function load(start = 0) {
  loading.value = true;
  try {
    const r = await api("souk_picks.picks_boot", { tab: tab.value, q: q.value, only: only.value, kind: kind.value, start });
    data.value = r;
    rows.value = start ? [...rows.value, ...r.picks] : r.picks;
    if (r.isManager && !decidersText.value) decidersText.value = r.deciders.map((x) => x.user).join(", ");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}
const reload = () => load(0);
const more = () => load(rows.value.length);
function go(x) {
  only.value = "";
  onlySource.value = "";
  kind.value = "";
  router.replace({ query: { ...route.query, tab: x } });
}
function setOnly(v) {
  only.value = v;
  if (v === "" || v === "trending" || v === "saturated") onlySource.value = "";
  reload();
}
function setKind(v) {
  kind.value = kind.value === v ? "" : v;
  reload();
}
function showSource(s) {
  router.replace({ query: { tab: "feed" } });
  setTimeout(() => { only.value = s.name; onlySource.value = s.label; reload(); }, 0);
}

function patch(card) {
  const i = rows.value.findIndex((x) => x.name === card.name);
  if (i >= 0) rows.value[i] = card;
  if (d.value && d.value.name === card.name) d.value = { ...d.value, ...card, posts: d.value.posts, postsN: d.value.postsN };
}
async function toggle(p) {
  busy.value = p.name;
  try {
    patch(await apiPost("souk_picks.pick_interest", { name: p.name, on: p.mine ? 0 : 1 }));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = "";
  }
}
async function decide(verdict) {
  saving.value = true;
  try {
    const card = await apiPost("souk_picks.pick_decide", {
      name: d.value.name, verdict, reason: dec.reason, note: dec.note,
      target_qty: dec.qty || 0, max_price: dec.max || 0, source: dec.source, category: dec.category,
    });
    patch(card);
    success(t("souk.pk.saved_" + verdict), "");
    if (verdict !== "undo") { close(); reload(); }
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}

function open(n) {
  router.push({ name: "SoukPicks", params: { name: n }, query: route.query });
}
function close() {
  router.push({ name: "SoukPicks", query: route.query });
}
// The classifier's kind → the shop category, when that category exists in Settings.
function shopCat(p) {
  const c = p?.shopCat || "";
  const cats = data.value?.categories;
  // The pick can arrive before the board: keep it, the server drops unknown keys.
  return !cats || cats.some((x) => x.key === c) ? c : "";
}
async function loadOne(n) {
  d.value = null;
  if (!n) return;
  try {
    d.value = await api("souk_picks.pick", { name: n });
    Object.assign(dec, { qty: d.value.targetQty || null, max: d.value.maxPrice || d.value.priceSeen || null,
                         source: d.value.source || d.value.sources[0]?.name || "", category: d.value.category || shopCat(d.value),
                         note: "", reason: "" });
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  }
}

async function addSource() {
  saving.value = true;
  try {
    const r = await apiPost("souk_picks.create_source", { ...nf });
    data.value = { ...data.value, sources: r.sources };
    success(r.created ? t("souk.pk.added") : t("souk.pk.known"), r.name);
    Object.assign(nf, { link: "", name: "", phone: "" });
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}
async function doImport() {
  saving.value = true;
  try {
    const r = await apiPost("souk_picks.import_sources", { text: importText.value });
    data.value = { ...data.value, sources: r.sources };
    importResult.value = { a: r.added, k: r.known, b: r.bad.length, badList: r.bad };
    if (!r.bad.length) importText.value = "";
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}
async function toggleSource(s) {
  saving.value = true;
  try {
    const r = await apiPost("souk_picks.disable_source", { name: s.name, off: s.disabled ? 0 : 1 });
    data.value = { ...data.value, sources: r.sources };
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}
async function scrapeNow() {
  saving.value = true;
  try {
    await apiPost("souk_picks.scrape_now", {});
    success(t("souk.pk.readQueued"), "");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}
async function tagNow() {
  saving.value = true;
  try {
    await apiPost("souk_picks.tag_now", {});
    success(t("souk.pk.tagQueued"), "");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}
async function saveDeciders() {
  saving.value = true;
  try {
    const users = decidersText.value.split(/[\s,،;]+/).map((x) => x.trim()).filter(Boolean);
    const r = await apiPost("souk_picks.save_deciders", { users: JSON.stringify(users) });
    data.value = { ...data.value, deciders: r };
    decidersText.value = r.map((x) => x.user).join(", ");
    success(t("souk.pk.savedDeciders"), "");
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}

watch(tab, () => { rows.value = []; reload(); });
watch(name, loadOne);
onMounted(() => { reload(); loadOne(name.value); });
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
.chip { display: inline-flex; align-items: center; gap: 4px; min-height: 28px; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; }
.badge { display: inline-flex; align-items: center; gap: 3px; height: 20px; padding: 0 6px; border-radius: 6px; font-size: 11px; font-weight: 700; }
.fld { width: 100%; height: 2.75rem; border-radius: 0.5rem; box-shadow: inset 0 0 0 1px rgb(214 211 209); background: #fff; padding: 0 0.625rem; font-size: 15px; }
.cat { flex-shrink: 0; min-height: 36px; padding: 0 12px; border-radius: 9999px; font-size: 13px; font-weight: 600;
  background: #fff; color: rgb(68 64 60); box-shadow: inset 0 0 0 1px rgb(214 211 209); white-space: nowrap; }
.cat[aria-pressed="true"] { background: rgb(var(--st) / .10); color: rgb(var(--st-ink)); box-shadow: inset 0 0 0 2px rgb(var(--st)); }
:global(html[data-theme="dark"] .st-buying .btn-st) { color: rgb(28 25 23); }
:global(html[data-theme="dark"] .st-buying .btn-line),
:global(html[data-theme="dark"] .st-buying .cat),
:global(html[data-theme="dark"] .st-buying .fld) { background: #292524; color: #f5f5f4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }
:global(html[data-theme="dark"] .pk-sheet) { background: #1c1917; }
</style>
