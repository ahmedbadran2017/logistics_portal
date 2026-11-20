<template>
  <!-- Content queue (2 days): French first (the storefront's main language),
       Arabic as the shop's translation (a warning, never a blocker), product
       type, collections, tags, the final price per size and SEO. The buy's
       and the floor's specs come ready; "Draft for me" fills only the empty
       fields from them (souk.content_draft — no AI). Edits save themselves
       3 s after the last change and are never lost on a product switch or a
       closed tab. "Send to review" writes it onto the Shopify Draft.
       Look = the souk stage system: a teal hero (clock bar + the one next
       step), then one sk-sec card per job: French, Arabic, catalogue, prices,
       SEO; the side holds the checks, the finals and the buy's facts.
       Backend: souk.content_boot / content_draft / content_save / content_send. -->
  <div class="st-content px-4 sm:px-5 pt-5 sm:pt-6 max-w-[1320px] mx-auto flex flex-col gap-4" :class="hasFooter ? 'pb-28 lg:pb-10' : 'pb-10'">
    <!-- ── hero: the product, its clock, the one next step ──────────────── -->
    <header v-if="d" class="sk-hero flex-col gap-3.5" :class="listOnly ? 'hidden lg:flex' : 'flex'">
      <router-link v-if="data && !listOnly" :to="{ name: 'SoukContent' }"
                   class="lg:hidden self-start lp-tap h-9 -mt-1 ps-1.5 pe-3 rounded-full bg-white/80 ring-1 ring-inset ring-stone-200 inline-flex items-center gap-1 text-[13px] font-semibold text-stone-700">
        <Icon name="chevron-left" :size="16" class="rtl:rotate-180" />{{ t('souk.pub.backToQueue') }} · {{ data.queue.length }}
      </router-link>
      <div class="flex gap-3 items-start">
        <span class="sk-ico sk-ico-lg sk-ico-solid"><Icon name="notebook-pen" :size="20" :stroke-width="2" /></span>
        <div class="min-w-0 flex-1 flex flex-col gap-1">
          <div class="text-[12px] font-semibold st-ink flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
            <span>{{ t('souk.pub.kicker').replace('{n}', data.queue.length) }}</span>
            <span aria-hidden="true">·</span><span class="mono" dir="ltr">{{ d.name }}</span>
            <span aria-hidden="true">·</span><span>{{ writerText }}</span>
          </div>
          <h1 class="text-[19px] sm:text-[22px] font-extrabold text-stone-900 leading-tight break-words">{{ c.fr.title || d.title }}</h1>
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
      <div v-if="d.canEdit" class="flex flex-wrap items-center gap-2">
        <button class="hidden lg:inline-flex btn btn-st" :disabled="busy || blockers.length > 0" :title="blockers.length ? blockText : null" @click="send">
          <Icon name="send" :size="15" :stroke-width="2.2" />{{ busy ? t('souk.sending') : t('souk.toReview') }}
        </button>
        <button class="btn btn-line" :disabled="drafting" :title="t('souk.pub.draftHint')" @click="draftForMe">
          <Icon name="list-checks" :size="14" />{{ drafting ? t('souk.pub.drafting') : t('souk.wr.template') }}
        </button>
        <button v-if="dirty || saveState === 'error'" class="hidden lg:inline-flex btn btn-line" :disabled="saving" @click="save({ quiet: false })">
          <Icon name="check" :size="14" />{{ t('souk.pub.saveNow') }}
        </button>
        <span class="hidden lg:inline-flex items-center gap-1.5 text-[12px] font-semibold ms-auto" :title="t('souk.pub.autoNote')"
              :class="saveState === 'error' ? 'text-rose-700' : dirty || saving ? 'text-amber-800' : 'text-emerald-700'">
          <span class="w-2 h-2 rounded-full" :class="saveState === 'error' ? 'bg-rose-500' : dirty || saving ? 'bg-amber-500' : 'bg-emerald-500'" />
          {{ saveText }}
        </span>
      </div>
    </header>
    <header v-if="!d || listOnly" class="sk-hero flex gap-3 items-start" :class="d ? 'lg:hidden' : ''">
      <span class="sk-ico sk-ico-lg sk-ico-solid"><Icon name="notebook-pen" :size="20" :stroke-width="2" /></span>
      <div class="min-w-0 flex flex-col gap-0.5">
        <h1 class="text-[19px] sm:text-[22px] font-extrabold text-stone-900 leading-tight">{{ t('souk.contentTitle') }}</h1>
        <p class="text-[13px] text-stone-600 max-w-[680px]">{{ t('souk.contentIntro') }}</p>
      </div>
    </header>

    <div v-if="loading && !data" class="h-[420px] rounded-2xl souk-skel" />

    <!-- nothing in the queue: the same card on the three screens -->
    <div v-else-if="data && !data.queue.length && !d" class="sk-sec px-6 py-12 flex flex-col items-center text-center gap-3">
      <span class="sk-ico sk-ico-lg"><Icon name="inbox" :size="22" /></span>
      <p class="text-[14px] font-semibold text-stone-700">{{ t('souk.contentNone') }}</p>
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
        <router-link v-for="(q, i) in data.queue" :key="q.name" :to="{ name: 'SoukContent', params: { name: q.name } }"
                     class="flex items-center gap-3 px-3.5 py-3 min-h-[72px] hover:bg-stone-50" :class="i ? 'border-t border-stone-100' : ''">
          <img v-if="q.image" :src="q.image" class="w-12 h-12 shrink-0 rounded-xl object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-12 h-12 shrink-0 rounded-xl st-tint st-fg flex items-center justify-center"><Icon name="image" :size="18" /></div>
          <div class="min-w-0 flex-1 flex flex-col gap-0.5">
            <div class="text-[14px] font-semibold truncate ltr:text-left rtl:text-right" dir="auto">{{ q.title }}</div>
            <div v-if="q.rejects" class="text-[12px] text-amber-800 inline-flex items-center gap-1"><Icon name="undo-2" :size="12" />{{ t('souk.returnedN').replace('{n}', q.rejects) }}</div>
          </div>
          <span class="sp-age" :class="q.late ? 'sp-age-late' : 'st-tint st-ink'"><Icon :name="q.late ? 'alert-triangle' : 'clock'" :size="11" />{{ ageText(q.age) }}</span>
          <Icon name="chevron-right" :size="16" class="shrink-0 text-stone-400 rtl:rotate-180" />
        </router-link>
      </section>
      <nav v-if="showStrip" :aria-label="t('souk.pub.queueLbl')" class="hidden lg:flex gap-2 overflow-x-auto pb-0.5">
        <router-link v-for="q in data.queue" :key="q.name" :to="{ name: 'SoukContent', params: { name: q.name } }"
                     class="sp-q" :class="d && d.name === q.name ? 'sp-q-on' : ''" :aria-current="d && d.name === q.name ? 'page' : undefined">
          <img v-if="q.image" :src="q.image" class="w-10 h-10 shrink-0 rounded-lg object-cover ring-1 ring-stone-200" alt="" />
          <div v-else class="w-10 h-10 shrink-0 rounded-lg st-tint st-fg flex items-center justify-center"><Icon name="image" :size="16" /></div>
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-semibold truncate ltr:text-left rtl:text-right" dir="auto">{{ q.title }}</div>
            <div v-if="q.rejects" class="text-[12px] text-amber-800 truncate">{{ t('souk.returnedN').replace('{n}', q.rejects) }}</div>
          </div>
          <span class="sp-age" :class="q.late ? 'sp-age-late' : 'st-tint st-ink'">{{ ageText(q.age) }}</span>
        </router-link>
      </nav>

      <div v-if="!d" class="hidden lg:flex sk-sec p-8 flex-col items-center gap-3 text-center text-[14px] text-stone-500">
        <span class="sk-ico sk-ico-lg"><Icon name="arrow-up" :size="20" /></span>{{ t('souk.studioPick') }}
      </div>
      <div v-else :class="listOnly ? 'hidden lg:block' : ''">
        <div class="flex flex-wrap gap-4 items-start">
          <div class="flex-[999_1_560px] min-w-0 flex flex-col gap-4">
            <div v-if="d.reviewNote" class="bg-amber-50 ring-1 ring-inset ring-amber-200 rounded-2xl px-3.5 py-3 text-[13px] text-amber-800 flex gap-2.5 items-start">
              <Icon name="undo-2" :size="16" class="shrink-0 mt-0.5" />
              <span class="min-w-0 break-words"><b>{{ t('souk.reviewSaid').replace('{n}', d.rejects) }}</b> {{ d.reviewNote }}</span>
            </div>
            <div v-if="!d.canEdit" class="bg-stone-100 rounded-2xl px-3.5 py-3 text-[13px] text-stone-700 flex gap-2.5 items-start">
              <Icon name="info" :size="16" class="shrink-0 mt-0.5" />{{ t('souk.contentNotNow') }}
            </div>

            <!-- AI writer (souk_write): one call reads the finals + facts; the
                 result waits as a suggestion until the writer applies it -->
            <section v-if="wr && d.canEdit" class="sk-sec" aria-live="polite">
              <div class="sk-sec-h">
                <span class="sk-ico sk-ico-solid"><Icon name="pen-line" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.wr.title') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.wr.sub') }}</span>
                </div>
              </div>
              <div class="sk-sec-b flex flex-col gap-3">
                <div v-if="wr.why" class="rounded-xl bg-stone-100 px-3 py-2.5 text-[13px] text-stone-700 flex flex-wrap items-center gap-x-2 gap-y-1">
                  <Icon name="info" :size="15" class="shrink-0" />{{ t('souk.wr.why_' + wr.why) }}
                  <router-link v-if="isManager" :to="{ name: 'SoukSettings', hash: '#set-write' }" class="font-semibold underline st-ink">{{ t('souk.wr.openSettings') }}</router-link>
                </div>
                <div v-else-if="!d.finals.length" class="rounded-xl bg-stone-100 px-3 py-2.5 text-[13px] text-stone-700 flex items-center gap-2">
                  <Icon name="info" :size="15" class="shrink-0" />{{ t('souk.wr.noFinals') }}
                </div>
                <template v-else>
                  <div v-if="writing" class="flex items-center gap-2.5 rounded-xl st-soft px-3 py-2.5 text-[13px] font-semibold st-ink">
                    <Icon name="refresh-cw" :size="15" class="animate-spin" />{{ t('souk.wr.writing') }}
                  </div>
                  <div v-else-if="wr.state === 'error'" class="rounded-xl bg-rose-50 ring-1 ring-inset ring-rose-200 px-3 py-2.5 text-[13px] text-rose-800 flex gap-2 items-start">
                    <Icon name="alert-triangle" :size="15" class="shrink-0 mt-0.5" /><span class="min-w-0 break-words">{{ t('souk.wr.failed').replace('{e}', wr.error) }}</span>
                  </div>

                  <!-- the suggestion: a short preview, apply, and what to check -->
                  <div v-if="wr.result && !writing" class="rounded-xl ring-1 ring-inset ring-[rgb(var(--st)/.25)] bg-white overflow-hidden">
                    <div class="px-3 py-2 st-soft flex flex-wrap items-center gap-2">
                      <Icon name="check" :size="14" class="st-fg" />
                      <span class="text-[13px] font-bold st-ink">{{ t('souk.wr.ready') }}</span>
                      <span class="text-[12px] text-stone-500 tabular-nums" dir="ltr">{{ wr.at }}</span>
                    </div>
                    <div class="px-3 py-2.5 flex flex-col gap-1.5">
                      <div class="text-[14px] font-semibold text-stone-900 break-words" dir="ltr" lang="fr">{{ wr.result.fr.title }}</div>
                      <div class="text-[14px] font-semibold text-stone-900 break-words" dir="rtl" lang="ar">{{ wr.result.ar.title }}</div>
                      <p class="text-[13px] text-stone-600 line-clamp-3 whitespace-pre-line" dir="ltr" lang="fr">{{ wr.result.fr.description }}</p>
                    </div>
                    <div v-if="wr.result.verify" class="px-3 py-2.5 border-t border-stone-100">
                      <div class="text-[12px] font-bold text-amber-800 flex items-center gap-1.5 mb-1"><Icon name="list-checks" :size="14" />{{ t('souk.wr.verify') }}</div>
                      <ul v-if="wr.result.verify.length" class="text-[13px] text-stone-700 list-disc ps-5 space-y-0.5" dir="rtl" lang="ar">
                        <li v-for="(v, i) in wr.result.verify" :key="i">{{ v }}</li>
                      </ul>
                      <p v-else class="text-[13px] text-stone-500">{{ t('souk.wr.none') }}</p>
                    </div>
                    <div class="px-3 py-2.5 border-t border-stone-100 flex flex-wrap items-center gap-2">
                      <button class="btn btn-st" @click="applyWr"><Icon name="check" :size="14" :stroke-width="2.2" />{{ t('souk.wr.apply') }}</button>
                      <button v-if="undoWr" class="btn btn-line" @click="undoApply"><Icon name="undo-2" :size="14" />{{ t('souk.wr.undo') }}</button>
                      <span class="text-[12px] text-stone-500 min-w-0 basis-full sm:basis-auto sm:flex-1">{{ t('souk.wr.replaces') }}</span>
                    </div>
                  </div>

                  <div v-if="!writing" class="flex flex-wrap items-center gap-2">
                    <input v-model="wrNote" type="text" maxlength="300" :placeholder="t('souk.wr.notePh')" dir="auto"
                           class="flex-[1_1_240px] min-w-0 h-11 rounded-xl ring-1 ring-stone-300 bg-white px-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--st))]" />
                    <button class="btn" :class="wr.result ? 'btn-line' : 'btn-st'" :disabled="wrBusy" @click="startWr">
                      <Icon name="sparkles" :size="14" />{{ wr.result ? t('souk.wr.again') : t('souk.wr.write') }}
                    </button>
                  </div>
                  <p v-if="!writing" class="text-[12px] text-stone-500">{{ t('souk.wr.cost').replace('{usd}', wr.usd).replace('{m}', wr.model) }}</p>
                </template>
              </div>
            </section>

            <!-- French: the storefront's own language -->
            <section class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="file-text" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.pub.secFr') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.pub.secFrSub') }}</span>
                </div>
                <span class="sp-tick" :class="frDone ? 'sp-tick-ok' : 'sp-tick-bad'"><Icon :name="frDone ? 'check' : 'alert-circle'" :size="13" :stroke-width="2.4" /></span>
              </div>
              <div class="sk-sec-b flex flex-col gap-3.5">
                <div class="flex flex-col gap-[5px]">
                  <div class="flex justify-between items-center gap-2">
                    <label class="text-[13px] font-semibold text-stone-700" for="c-title-fr">{{ t('souk.pub.fTitle') }}</label>
                    <span class="sp-count" :class="c.fr.title.length > 70 ? 'sp-count-over' : ''">{{ t('souk.pub.chars').replace('{n}', c.fr.title.length).replace('{m}', 70) }}</span>
                  </div>
                  <input id="c-title-fr" v-model="c.fr.title" dir="ltr" lang="fr" :disabled="!d.canEdit"
                         class="w-full h-[44px] rounded-lg border border-stone-300 bg-white px-3 text-[15px] disabled:bg-stone-50" />
                </div>
                <div class="flex flex-col gap-[5px]">
                  <label class="text-[13px] font-semibold text-stone-700" for="c-desc-fr">{{ t('souk.pub.fDesc') }}</label>
                  <textarea id="c-desc-fr" v-model="c.fr.description" dir="ltr" lang="fr" :disabled="!d.canEdit" rows="7"
                            class="w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-[15px] leading-[1.6] resize-y disabled:bg-stone-50" />
                  <span class="text-[12px] text-stone-500">{{ t('souk.descHint') }}</span>
                </div>
              </div>
            </section>

            <!-- Arabic: the shop's translation, always typed right-to-left -->
            <section class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="globe" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.pub.secAr') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.pub.secArSub') }}</span>
                </div>
                <span v-if="arDone" class="sp-tick sp-tick-ok"><Icon name="check" :size="13" :stroke-width="2.4" /></span>
                <span v-else class="shrink-0 h-6 px-2 rounded-full bg-amber-50 text-amber-800 text-[12px] font-bold inline-flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-500" />{{ t('souk.pub.arTodo') }}
                </span>
              </div>
              <div class="sk-sec-b flex flex-col gap-3.5">
                <div class="flex flex-col gap-[5px]">
                  <div class="flex justify-between items-center gap-2">
                    <label class="text-[13px] font-semibold text-stone-700" for="c-title-ar">{{ t('souk.pub.fTitle') }}</label>
                    <span class="sp-count" :class="c.ar.title.length > 70 ? 'sp-count-over' : ''">{{ t('souk.pub.chars').replace('{n}', c.ar.title.length).replace('{m}', 70) }}</span>
                  </div>
                  <input id="c-title-ar" v-model="c.ar.title" dir="rtl" lang="ar" :disabled="!d.canEdit"
                         class="w-full h-[44px] rounded-lg border border-stone-300 bg-white px-3 text-[15px] disabled:bg-stone-50" />
                </div>
                <div class="flex flex-col gap-[5px]">
                  <label class="text-[13px] font-semibold text-stone-700" for="c-desc-ar">{{ t('souk.pub.fDesc') }}</label>
                  <textarea id="c-desc-ar" v-model="c.ar.description" dir="rtl" lang="ar" :disabled="!d.canEdit" rows="6"
                            class="w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-[15px] leading-[1.7] resize-y disabled:bg-stone-50" />
                  <span class="text-[12px] text-stone-500">{{ t('souk.descHint') }}</span>
                </div>
              </div>
            </section>

            <!-- catalogue: type, collections, tags -->
            <section class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="layers" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.pub.secCat') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.pub.secCatSub') }}</span>
                </div>
              </div>
              <div class="sk-sec-b grid grid-cols-1 md:grid-cols-2 gap-3.5">
                <div class="flex flex-col gap-[5px] min-w-0">
                  <label class="text-[13px] font-semibold text-stone-700" for="c-type">{{ t('souk.productType') }}</label>
                  <select id="c-type" v-model="c.productType" :disabled="!d.canEdit" class="w-full h-[44px] rounded-lg border border-stone-300 px-2.5 text-[15px] bg-white disabled:bg-stone-50">
                    <option value="">{{ t('souk.pub.pickType') }}</option>
                    <option v-for="pt in typeOptions" :key="pt" :value="pt">{{ pt }}</option>
                  </select>
                </div>
                <div class="flex flex-col gap-[5px] min-w-0">
                  <label class="text-[13px] font-semibold text-stone-700" for="c-tags">{{ t('souk.pub.tags') }}</label>
                  <input id="c-tags" v-model="tagsText" dir="auto" :disabled="!d.canEdit" class="w-full h-[44px] rounded-lg border border-stone-300 bg-white px-3 text-[15px] disabled:bg-stone-50" :placeholder="t('souk.tagsHint')" />
                </div>
                <div class="flex flex-col gap-[5px] min-w-0 md:col-span-2">
                  <span class="text-[13px] font-semibold text-stone-700">{{ t('souk.collections') }}</span>
                  <div v-if="d.collectionsError" class="text-[12px] text-rose-700 break-words">{{ d.collectionsError }}</div>
                  <div v-if="c.collections.length" class="flex gap-1.5 flex-wrap items-center min-h-[36px]">
                    <span v-for="id in c.collections" :key="id" class="h-8 ps-3 pe-1 rounded-full st-tint st-ink text-[13px] font-semibold inline-flex items-center gap-1 max-w-full">
                      <span class="truncate">{{ colTitle(id) }}</span>
                      <button v-if="d.canEdit" class="w-6 h-6 shrink-0 rounded-full hover:bg-white/60 inline-flex items-center justify-center" :aria-label="t('souk.remove')" @click="dropCol(id)"><Icon name="x" :size="12" /></button>
                    </span>
                    <button v-if="d.canEdit && !addingCol && c.collections.length" class="h-8 px-3 rounded-full bg-white ring-1 ring-inset ring-stone-300 text-[13px] font-semibold text-stone-600 hover:bg-stone-50" @click="addingCol = true">
                      {{ t('souk.pub.addCollection') }}
                    </button>
                  </div>
                  <div v-if="d.canEdit && (addingCol || !c.collections.length)" class="relative">
                    <Icon name="search" :size="15" class="absolute top-1/2 -translate-y-1/2 start-3 text-stone-400 pointer-events-none" />
                    <input v-model="colQuery" class="w-full h-11 rounded-lg border border-stone-300 bg-white ps-9 pe-3 text-[14px]" :placeholder="t('souk.collectionSearch')"
                           :aria-label="t('souk.collectionSearch')" @keydown.esc="colQuery = ''; addingCol = false" />
                    <div v-if="colQuery.trim()" class="absolute z-10 mt-1 w-full max-h-[240px] overflow-auto bg-white ring-1 ring-stone-200 rounded-lg shadow-lg">
                      <button v-for="x in colHits" :key="x.id" class="block w-full text-start px-3 py-2.5 text-[13px] hover:bg-stone-50" @click="addCol(x.id)">{{ x.title }}</button>
                      <div v-if="!colHits.length" class="px-3 py-2 text-[13px] text-stone-500">—</div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- prices: one per size, the margin as a badge -->
            <section class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="dollar-sign" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.pub.secPrices') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.pub.secPricesSub') }}</span>
                </div>
              </div>
              <div class="divide-y divide-stone-100">
                <div v-for="g in groups" :key="g.key" class="px-3.5 py-3 flex flex-col gap-2">
                  <div class="flex flex-wrap items-end gap-x-3 gap-y-2">
                    <div class="flex-[1_1_180px] min-w-0 flex flex-col gap-[5px]">
                      <label class="text-[13px] font-semibold text-stone-700" :for="'c-price-' + g.key">
                        {{ t('souk.finalPrice') }}<span v-if="g.key" class="ms-1.5 text-[12px] font-bold text-stone-700 bg-stone-100 rounded-md px-1.5 py-px">{{ g.key }}</span>
                      </label>
                      <div class="relative">
                        <input :id="'c-price-' + g.key" type="number" inputmode="decimal" :value="priceOf(g)" :disabled="!d.canEdit"
                               class="w-full h-[44px] rounded-lg border border-stone-300 bg-white ps-3 pe-14 text-[15px] font-semibold tabular-nums disabled:bg-stone-50" @input="setPrice(g, $event.target.value)" />
                        <span class="absolute inset-y-0 end-3 flex items-center text-[13px] text-stone-500 pointer-events-none">MAD</span>
                      </div>
                    </div>
                    <div class="flex-[1_1_160px] min-w-0 flex items-center justify-between gap-2 h-[44px] rounded-lg bg-stone-50 px-3">
                      <span class="flex-1 text-[12px] text-stone-600 min-w-0 truncate">{{ t('souk.landedCost') }}</span>
                      <span class="text-[13px] font-semibold text-stone-900 tabular-nums"><bdi dir="ltr">{{ fmt2(g.landed) }}</bdi></span>
                      <span class="shrink-0 h-6 px-2 rounded-full text-[12px] font-bold tabular-nums inline-flex items-center"
                            :class="marginOf(g) <= 0 ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700'">{{ t('souk.marginPct').replace('{n}', marginOf(g)) }}</span>
                    </div>
                  </div>
                  <span v-if="!g.allocated" class="text-[12px] text-amber-800 inline-flex items-start gap-1"><Icon name="truck" :size="13" class="shrink-0 mt-px" />{{ t('souk.transportNotYet') }}</span>
                </div>
              </div>
            </section>

            <!-- SEO -->
            <section class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="search" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.seoTitle') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.pub.secSeoSub') }}</span>
                </div>
              </div>
              <div class="sk-sec-b flex flex-col gap-3.5">
                <div class="sp-serp rounded-xl px-3.5 py-3 flex flex-col gap-[3px] min-w-0" dir="ltr" lang="fr" style="font-family: Arial, sans-serif">
                  <span class="text-[13px] text-[#3c4043] truncate">justyol.com › products › {{ c.handle || '…' }}</span>
                  <span class="text-[17px] text-[#1a0dab] truncate">{{ c.metaTitle || c.fr.title || '—' }}</span>
                  <span class="text-[14px] text-[#4d5156] line-clamp-2 leading-normal">{{ c.metaDescription || '—' }}</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  <div class="flex flex-col gap-[5px] min-w-0">
                    <!-- fixed height: the link button must not push this input below its neighbour -->
                    <div class="flex justify-between items-center gap-2 h-[22px] text-[13px]">
                      <label class="font-semibold text-stone-700" for="c-handle">{{ t('souk.handle') }}</label>
                      <button v-if="d.canEdit" class="lp-tap h-7 px-1 shrink-0 text-[12px] font-semibold underline st-ink" @click="c.handle = slug(c.fr.title)">{{ t('souk.fromTitle') }}</button>
                    </div>
                    <input id="c-handle" v-model="c.handle" dir="ltr" :disabled="!d.canEdit" class="w-full h-[44px] rounded-lg border border-stone-300 bg-white px-3 text-[15px] mono disabled:bg-stone-50" />
                  </div>
                  <div class="flex flex-col gap-[5px] min-w-0">
                    <div class="flex justify-between items-center gap-2 h-[22px]">
                      <label class="text-[13px] font-semibold text-stone-700" for="c-mt">{{ t('souk.pub.metaTitle') }}</label>
                      <span class="sp-count" :class="c.metaTitle.length > 60 ? 'sp-count-over' : ''">{{ t('souk.pub.chars').replace('{n}', c.metaTitle.length).replace('{m}', 60) }}</span>
                    </div>
                    <input id="c-mt" v-model="c.metaTitle" dir="ltr" lang="fr" :disabled="!d.canEdit" class="w-full h-[44px] rounded-lg border border-stone-300 bg-white px-3 text-[15px] disabled:bg-stone-50" />
                    <div class="sp-meter"><div :class="c.metaTitle.length > 60 ? 'bg-rose-500' : 'st-solid'" :style="{ width: Math.min(100, c.metaTitle.length / 60 * 100) + '%' }" /></div>
                  </div>
                  <div class="flex flex-col gap-[5px] md:col-span-2">
                    <div class="flex justify-between items-center gap-2">
                      <label class="text-[13px] font-semibold text-stone-700" for="c-md">{{ t('souk.pub.metaDesc') }}</label>
                      <span class="sp-count" :class="c.metaDescription.length > 160 ? 'sp-count-over' : ''">{{ t('souk.pub.chars').replace('{n}', c.metaDescription.length).replace('{m}', 160) }}</span>
                    </div>
                    <textarea id="c-md" v-model="c.metaDescription" dir="ltr" lang="fr" :disabled="!d.canEdit" rows="2" class="w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-[15px] leading-normal resize-y disabled:bg-stone-50" />
                    <div class="sp-meter"><div :class="c.metaDescription.length > 160 ? 'bg-rose-500' : 'st-solid'" :style="{ width: Math.min(100, c.metaDescription.length / 160 * 100) + '%' }" /></div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <!-- side: what is left before sending, then what the floor gave -->
          <aside class="flex-[1_1_300px] lg:max-w-[380px] min-w-0 flex flex-col gap-4 xl:sticky xl:top-4">
            <section class="sk-sec">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="list-checks" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.beforeSend') }}</h2>
                  <span class="sk-sec-s tabular-nums">{{ t('souk.pub.readyN').replace('{n}', checksOk).replace('{m}', checks.length) }}</span>
                </div>
              </div>
              <ul class="px-3.5 py-2">
                <li v-for="k in checks" :key="k.key" class="flex items-start gap-2.5 py-1.5 text-[13px]">
                  <span class="sp-tick" :class="k.ok ? 'sp-tick-ok' : k.soft ? 'sp-tick-warn' : 'sp-tick-bad'">
                    <Icon :name="k.ok ? 'check' : k.soft ? 'alert-triangle' : 'alert-circle'" :size="13" :stroke-width="2.4" />
                  </span>
                  <div class="min-w-0 pt-0.5">
                    <div :class="k.ok ? 'text-stone-900' : k.soft ? 'text-amber-800 font-semibold' : 'text-rose-700 font-semibold'">{{ t('souk.ck_' + k.key) }}</div>
                    <div v-if="!k.ok && k.soft" class="text-[12px] text-amber-700">{{ t('souk.pub.softWarn') }}</div>
                  </div>
                </li>
              </ul>
              <div v-if="d.canEdit" class="px-3.5 pb-3.5 flex flex-col gap-2">
                <p v-if="blockers.length" class="text-[12px] text-rose-700 bg-rose-50 rounded-lg px-2.5 py-2">{{ blockText }}</p>
                <p class="text-[12px] text-stone-500 leading-normal">{{ t('souk.toReviewNote') }}</p>
              </div>
            </section>

            <section v-if="d.finals.length" class="sk-sec st-studio">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="sparkles" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.finals') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.pub.secFinalsSub') }}</span>
                </div>
                <span class="text-[12px] font-bold st-ink st-tint rounded-full px-2.5 py-1 tabular-nums">{{ d.finals.length }}</span>
              </div>
              <div class="sk-sec-b grid grid-cols-5 gap-1.5">
                <a v-for="f in d.finals" :key="f.url" :href="f.url" target="_blank" rel="noopener" class="block aspect-[4/5] rounded-lg overflow-hidden bg-stone-100 ring-1 ring-stone-200">
                  <img :src="f.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                </a>
              </div>
            </section>

            <section class="sk-sec st-buying">
              <div class="sk-sec-h">
                <span class="sk-ico"><Icon name="shopping-bag" :size="16" /></span>
                <div class="min-w-0 flex-1 flex flex-col">
                  <h2 class="sk-sec-t">{{ t('souk.fromBuy') }}</h2>
                  <span class="sk-sec-s">{{ t('souk.pub.secBuySub') }}</span>
                </div>
              </div>
              <dl class="px-3.5 py-2">
                <div v-for="row in facts" :key="row.k" class="row">
                  <dt class="text-stone-600 shrink-0">{{ row.k }}</dt>
                  <dd class="font-semibold text-stone-900 text-end min-w-0 break-words" :dir="row.ltr ? 'ltr' : null">{{ row.v }}</dd>
                </div>
              </dl>
              <div v-if="d.specs" class="mx-3.5 mb-3.5 text-[13px] text-stone-700 bg-stone-50 rounded-xl px-3 py-2.5"><b class="text-stone-900">{{ t('souk.specs') }}:</b> <bdi>{{ d.specs }}</bdi></div>
            </section>
          </aside>
        </div>
      </div>
    </template>

    <!-- a phone: the save state and the send stay under the thumb -->
    <div v-if="hasFooter" class="lp-footer lg:hidden px-4 py-3 flex items-center gap-2">
      <button type="button" class="flex-1 min-w-0 h-11 inline-flex items-center gap-1.5 text-[13px] font-semibold text-start"
              :class="saveState === 'error' ? 'text-rose-700' : dirty || saving ? 'text-amber-800' : 'text-emerald-700'"
              :disabled="saving || !(dirty || saveState === 'error')" @click="save({ quiet: false })">
        <span class="w-2 h-2 shrink-0 rounded-full" :class="saveState === 'error' ? 'bg-rose-500' : dirty || saving ? 'bg-amber-500' : 'bg-emerald-500'" />
        <span class="truncate">{{ saveText }}</span>
        <span v-if="!saving && (dirty || saveState === 'error')" class="shrink-0 underline">{{ t('souk.pub.saveNow') }}</span>
      </button>
      <button class="btn btn-st h-11 px-5" :disabled="busy || blockers.length > 0" @click="send">
        <Icon name="send" :size="15" :stroke-width="2.2" />{{ busy ? t('souk.sending') : t('souk.toReview') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter, onBeforeRouteUpdate, onBeforeRouteLeave } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { useAuth } from "@/composables/useAuth";

const { t, locale } = useI18n();
const { success, warn } = useToast();
const route = useRoute();
const router = useRouter();
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const drafting = ref(false);
const colQuery = ref("");
const addingCol = ref(false);
const c = ref(blank());
const tagsText = ref("");
const d = computed(() => data.value?.detail || null);
const auth = useAuth();
const isManager = computed(() => auth.role?.value === "manager");

function blank() {
  return { fr: { title: "", description: "" }, ar: { title: "", description: "" }, productType: "", collections: [],
    tags: [], handle: "", metaTitle: "", metaDescription: "", prices: {} };
}
const fmt2 = (n) => Number(n || 0).toLocaleString("fr-FR", { maximumFractionDigits: 2 });
const colorName = (x) => (locale.value === "ar" ? x.ar || x.fr : x.fr || x.code);
const sizes = computed(() => [...new Set((d.value?.variants || []).map((v) => v.size).filter(Boolean))]);
const weights = computed(() => {
  const seen = {};
  for (const v of d.value?.variants || []) if (v.grams) seen[v.size || "—"] = v.grams;
  return Object.keys(seen).map((k) => (k === "—" ? "" : k + " ") + (seen[k] >= 1000 ? (seen[k] / 1000).toFixed(2) + " kg" : seen[k] + " g")).join(" · ");
});
// One price per size (the colours of a size sell at the same price).
const groups = computed(() => {
  const out = {};
  for (const v of d.value?.variants || []) {
    const k = v.size || "";
    const g = out[k] || (out[k] = { key: k, skus: [], landed: 0, allocated: true });
    g.skus.push(v.sku);
    g.landed = Math.max(g.landed, Number(v.landed) || 0);
    g.allocated = g.allocated && !!v.allocated;
  }
  return Object.values(out);
});
const facts = computed(() => {
  const x = d.value;
  if (!x) return [];
  const rows = [
    { k: t("souk.stallShort"), v: x.stall },
    { k: t("souk.siteShort"), v: x.brand },
  ];
  if (sizes.value.length) rows.push({ k: t("souk.sizesLbl").replace(/\s*:$/, ""), v: sizes.value.join(" · ") });
  const cols = (x.colors || []).filter((k) => k.code);
  if (cols.length) rows.push({ k: t("souk.colorsLbl").replace(/\s*:$/, ""), v: cols.map(colorName).join(" · ") });
  if (weights.value) rows.push({ k: t("souk.weightLbl").replace(/\s*:$/, ""), v: weights.value, ltr: true });
  rows.push({ k: t("souk.stockLbl").replace(/\s*:$/, ""), v: t("souk.stockLine").replace("{s}", x.stock.shelf).replace("{t}", x.stock.studio) });
  const cost = groups.value.filter((g) => g.landed).map((g) => (g.key ? g.key + " " : "") + fmt2(g.landed)).join(" · ");
  if (cost) rows.push({ k: t("souk.pub.costLbl"), v: cost + " MAD", ltr: true });
  return rows;
});
const typeOptions = computed(() => [...new Set([...(d.value?.productTypes || []), c.value.productType].filter(Boolean))]);
const priceOf = (g) => c.value.prices[g.skus[0]] ?? "";
function setPrice(g, val) {
  for (const s of g.skus) c.value.prices[s] = Number(val) || 0;
}
const marginOf = (g) => {
  const p = Number(priceOf(g)) || 0;
  return p ? Math.round(((p - g.landed) / p) * 100) : 0;
};
const colTitle = (id) => (d.value?.collections || []).find((x) => x.id === id)?.title || id.split("/").pop();
const colHits = computed(() => {
  const q = colQuery.value.trim().toLowerCase();
  return (d.value?.collections || []).filter((x) => !c.value.collections.includes(x.id) && x.title.toLowerCase().includes(q)).slice(0, 30);
});
function addCol(id) {
  c.value.collections.push(id);
  colQuery.value = "";
  addingCol.value = false;
}
function dropCol(id) {
  c.value.collections = c.value.collections.filter((x) => x !== id);
}
function slug(s) {
  return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120);
}
const arDone = computed(() => !!c.value.ar.title.trim() && !!c.value.ar.description.trim());
// The French card's own tick: its two checks pass.
const frDone = computed(() => !!c.value.fr.title.trim() && c.value.fr.title.length <= 70 && c.value.fr.description.trim().length >= 40);
// Same rules as the server's checklist (_content_checks), live while typing.
// soft = a warning: send goes ahead (the server's own flag wins).
const checks = computed(() => {
  const x = c.value;
  const landed = {};
  for (const v of d.value?.variants || []) landed[v.sku] = Number(v.landed) || 0;
  const soft = new Set(["arText", ...(d.value?.checks || []).filter((k) => k.soft).map((k) => k.key)]);
  return [
    { key: "frTitle", ok: !!x.fr.title.trim() && x.fr.title.length <= 70 },
    { key: "frDesc", ok: x.fr.description.trim().length >= 40 },
    { key: "arText", ok: arDone.value },
    { key: "prices", ok: Object.keys(landed).every((s) => (Number(x.prices[s]) || 0) > landed[s]) },
    { key: "collection", ok: x.collections.length >= 1 },
    { key: "seo", ok: !!x.metaTitle.trim() && x.metaTitle.length <= 60 && !!x.metaDescription.trim()
        && x.metaDescription.length <= 160 && /^[a-z0-9]+(-[a-z0-9]+)*$/.test(x.handle || "") },
  ].map((k) => ({ ...k, soft: soft.has(k.key) }));
});
const blockers = computed(() => checks.value.filter((k) => !k.ok && !k.soft));
const checksOk = computed(() => checks.value.filter((k) => k.ok).length);
const blockText = computed(() => t("souk.pub.blocksSend").replace("{list}", blockers.value.map((k) => t("souk.ck_" + k.key)).join(" · ")));

// A phone shows the queue OR the product; the route decides which.
const listOnly = computed(() => !route.params.name);
const showStrip = computed(() => {
  const q = data.value?.queue || [];
  return q.length > 1 || (q.length === 1 && q[0].name !== d.value?.name);
});
const hasFooter = computed(() => !!d.value?.canEdit && !listOnly.value);
const ageText = (a) => (Number(a) < 1 ? t("souk.pub.today") : t("souk.ageDays").replace("{n}", Math.floor(Number(a))));

// Stage clock, deadline and writer.
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
const writerText = computed(() => (d.value?.writer ? t("souk.pub.writer").replace("{n}", d.value.writer) : t("souk.pub.writerYou")));

// --- saving: autosave 3 s after the last change; never lose an edit ---------
function payload() {
  return { ...c.value, tags: tagsText.value.split(",").map((s) => s.trim()).filter(Boolean) };
}
const snap = () => JSON.stringify(payload());
const baseline = ref("");
const current = computed(() => snap());
const dirty = computed(() => !!d.value?.canEdit && current.value !== baseline.value);
const saving = ref(false);
const saveState = ref("idle"); // idle | saved | error
const saveError = ref("");
const saveText = computed(() => (saving.value ? t("souk.pub.saving") : saveState.value === "error"
  ? t("souk.pub.saveFailed").replace("{e}", saveError.value) : dirty.value ? t("souk.pub.unsaved") : t("souk.pub.saved")));
let timer = null;
let inflight = null;

watch(current, () => {
  clearTimeout(timer);
  if (!dirty.value) return;
  if (saveState.value === "saved") saveState.value = "idle";
  timer = setTimeout(() => save(), 3000);
});

function take(det) {
  data.value = { ...data.value, detail: { ...det, collections: det.collections?.length ? det.collections : d.value?.collections || [] } };
}

async function save({ quiet = true } = {}) {
  clearTimeout(timer);
  if (inflight) await inflight;
  if (!d.value?.canEdit) return true;
  if (!dirty.value) return true;
  const body = current.value;
  const name = d.value.name;
  saving.value = true;
  inflight = (async () => {
    try {
      const det = await apiPost("souk.content_save", { name, content: body });
      if (d.value?.name === name) {
        take(det);
        baseline.value = body;
      }
      saveState.value = "saved";
      saveError.value = "";
      if (!quiet) success(t("souk.saved"));
      return true;
    } catch (e) {
      saveState.value = "error";
      saveError.value = String(e.message || e);
      if (!quiet) warn(t("souk.failed"), saveError.value);
      return false;
    } finally {
      saving.value = false;
      inflight = null;
    }
  })();
  const ok = await inflight;
  // Typed on while it was saving: the next round goes by itself.
  if (ok && dirty.value) timer = setTimeout(() => save(), 3000);
  return ok;
}

async function load() {
  clearTimeout(timer);
  loading.value = true;
  try {
    const next = await api("souk.content_boot", route.params.name ? { name: route.params.name } : {});
    const same = next?.detail?.name && next.detail.name === d.value?.name;
    data.value = next;
    const det = next.detail;
    c.value = det ? JSON.parse(JSON.stringify(det.content)) : blank();
    tagsText.value = (c.value.tags || []).join(", ");
    baseline.value = snap();
    saveState.value = "idle";
    saveError.value = "";
    if (!same) {
      colQuery.value = "";
      addingCol.value = false;
    }
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

async function draftForMe() {
  drafting.value = true;
  try {
    const g = await api("souk.content_draft", { name: d.value.name });
    let n = 0;
    const fill = (obj, key, val) => {
      if (val && !String(obj[key] || "").trim()) {
        obj[key] = val;
        n++;
      }
    };
    fill(c.value.fr, "title", g.fr?.title);
    fill(c.value.fr, "description", g.fr?.description);
    fill(c.value.ar, "title", g.ar?.title);
    fill(c.value.ar, "description", g.ar?.description);
    fill(c.value, "productType", g.productType);
    fill(c.value, "handle", g.handle);
    fill(c.value, "metaTitle", g.metaTitle);
    fill(c.value, "metaDescription", g.metaDescription);
    if (!tagsText.value.trim() && g.tags?.length) {
      tagsText.value = g.tags.join(", ");
      n++;
    }
    if (n) success(t("souk.pub.draftFilled").replace("{n}", n));
    else success(t("souk.pub.draftNothing"));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    drafting.value = false;
  }
}

// --- AI writer (souk_write) --------------------------------------------------
const wr = computed(() => d.value?.write || null);
const writing = computed(() => !!wr.value && ["queued", "running"].includes(wr.value.state));
const wrBusy = ref(false);
const wrNote = ref("");
const undoWr = ref(null);
let wrTimer = null;
function setWr(w) {
  if (d.value) data.value = { ...data.value, detail: { ...d.value, write: w } };
}
function pollWr() {
  clearTimeout(wrTimer);
  if (!writing.value || !d.value) return;
  const name = d.value.name;
  wrTimer = setTimeout(async () => {
    try {
      const w = await api("souk_write.poll", { name });
      if (d.value?.name !== name) return;
      setWr(w);
      if (w.state === "done") success(t("souk.wr.ready"));
    } catch (e) {
      /* a missed poll: try again on the next tick */
    }
    pollWr();
  }, 4000);
}
async function startWr() {
  wrBusy.value = true;
  try {
    setWr(await apiPost("souk_write.start", { name: d.value.name, note: wrNote.value.trim() }));
    pollWr();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    wrBusy.value = false;
  }
}
function applyWr() {
  const r = wr.value?.result;
  if (!r) return;
  undoWr.value = { c: JSON.parse(JSON.stringify(c.value)), tags: tagsText.value };
  c.value.fr = { title: r.fr.title, description: r.fr.description };
  c.value.ar = { title: r.ar.title, description: r.ar.description };
  c.value.metaTitle = r.metaTitle;
  c.value.metaDescription = r.metaDescription;
  if (r.handle && !String(c.value.handle || "").trim()) c.value.handle = r.handle;
  // The shop's own tags (souk, brand, colours) stay; the writer's are added.
  const have = tagsText.value.split(",").map((x) => x.trim()).filter(Boolean);
  for (const x of r.tags || []) if (!have.some((h) => h.toLowerCase() === x.toLowerCase())) have.push(x);
  tagsText.value = have.join(", ");
  success(t("souk.wr.applied"));
}
function undoApply() {
  if (!undoWr.value) return;
  c.value = undoWr.value.c;
  tagsText.value = undoWr.value.tags;
  undoWr.value = null;
}
watch(() => d.value?.name, () => {
  undoWr.value = null;
  wrNote.value = "";
  pollWr();
});

async function send() {
  if (!(await save())) {
    warn(t("souk.failed"), saveError.value);
    return;
  }
  busy.value = true;
  try {
    const r = await apiPost("souk.content_send", { name: d.value.name });
    // No longer ours to edit: nothing left to guard on the way out.
    data.value = { ...data.value, detail: { ...d.value, canEdit: false } };
    success(r.arabic && !r.arabic.ok ? t("souk.sentNoArabic") : t("souk.sentToReview"));
    if (route.params.name) await router.push({ name: "SoukContent" });
    else await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

// Leaving the product (another one in the queue, another screen): save
// first; only if that fails, ask.
async function guardLeave() {
  if (!dirty.value && !inflight) return true;
  if ((await save()) && !dirty.value) return true;
  return window.confirm(t("souk.pub.leaveUnsaved"));
}
onBeforeRouteUpdate((to, from) => (to.params.name === from.params.name ? true : guardLeave()));
onBeforeRouteLeave(() => guardLeave());

function guard(e) {
  if (dirty.value || saving.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}
window.addEventListener("beforeunload", guard);
onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", guard);
  clearTimeout(timer);
  clearTimeout(wrTimer);
});
watch(() => route.params.name, load);
onMounted(load);
</script>

<style scoped>
/* Buttons: one solid in the stage colour (the next step), the rest outline.
   44px under a thumb, 36px on a desk. */
.btn { flex-shrink: 0; height: 2.75rem; padding-block: 0; padding-inline: 0.875rem; border-radius: 0.75rem; font-size: 13px; font-weight: 600;
  gap: 0.375rem; white-space: nowrap; } /* display comes from the global .btn, so `hidden` still wins */
@media (min-width: 1024px) { .btn { height: 2.375rem; } }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.btn-st { background: rgb(var(--st)); color: #fff; font-size: 14px; font-weight: 700; box-shadow: 0 6px 16px -8px rgb(var(--st)); }
.btn-st:not(:disabled):hover { background: rgb(var(--st-ink)); }
.btn-st:disabled { background: rgb(231 229 228); color: rgb(87 83 78); box-shadow: none; opacity: 1; }
.btn-line { background: rgb(255 255 255 / .85); color: rgb(28 25 23); box-shadow: inset 0 0 0 1px rgb(214 211 209); }
.btn-line:not(:disabled):hover { background: #fff; }
:global(html[data-theme="dark"] .btn-st) { color: rgb(28 25 23); }
:global(html[data-theme="dark"] .btn-st:disabled) { background: rgb(68 64 60); color: rgb(168 162 158); }
:global(html[data-theme="dark"] .btn-line) { background: #292524; color: #f5f5f4; box-shadow: inset 0 0 0 1px rgb(87 83 78); }

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

/* Character counter + its thin sp-meter. */
.sp-count { font-size: 12px; font-variant-numeric: tabular-nums; color: rgb(87 83 78); white-space: nowrap; }
.sp-count-over { color: rgb(190 18 60); font-weight: 700; }
.sp-meter { height: 4px; border-radius: 9999px; background: rgb(231 229 228); overflow: hidden; }
.sp-meter > div { height: 100%; border-radius: 9999px; transition: width .15s; }
:global(html[data-theme="dark"] .sp-count) { color: rgb(168 162 158); }
:global(html[data-theme="dark"] .sp-count-over) { color: rgb(253 164 175); }
:global(html[data-theme="dark"] .sp-meter) { background: rgb(68 64 60); }

/* The Google result keeps Google's own light look in both themes. */
.sp-serp { background: rgb(250 250 249); box-shadow: inset 0 0 0 1px rgb(231 229 228); }
:global(html[data-theme="dark"] .sp-serp) { background: #fff; }

/* Receipt-style fact rows. */
.row { display: flex; justify-content: space-between; gap: 10px; padding-block: 5px; font-size: 13px; box-shadow: inset 0 -1px 0 rgb(245 245 244); }
.row:last-child { box-shadow: none; }
:global(html[data-theme="dark"] .row) { box-shadow: inset 0 -1px 0 rgb(68 64 60); }
:global(html[data-theme="dark"] .row:last-child) { box-shadow: none; }
</style>
