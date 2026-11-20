<template>
  <!-- Marketing's queue: the final photos. The in-house photos and the specs
       come from the floor and the buy; marketing uploads the finals per
       colour, puts them in order (drag, or the arrows on a phone — the first
       is the main photo) and the whole order is saved with ONE final_set.
       Handing to content puts them on the Shopify Draft; each colour's first
       final becomes its variants' image. The sample pieces are in
       Studio - JM. Backend: souk.studio_boot / final_add / final_set /
       photo_remove / studio_return / studio_send / raw_zip. -->
  <div class="px-4 sm:px-5 pt-5 pb-10 max-w-[1320px] mx-auto space-y-4">
    <header class="sk-hero st-studio px-4 py-3.5 flex items-center gap-3">
      <span class="sk-ico sk-ico-lg sk-ico-solid"><Icon name="sparkles" :size="20" /></span>
      <div class="min-w-0">
        <h1 class="text-[19px] font-bold text-stone-900 leading-tight">{{ t('souk.studioTitle') }}</h1>
        <p class="text-[13px] text-stone-600 max-w-[680px]">{{ t('souk.studioIntro') }}</p>
      </div>
    </header>

    <div v-if="loading && !data" class="lp-card h-[420px] animate-pulse" />

    <!-- nothing in the queue: the same card on the three screens -->
    <div v-else-if="data && !data.queue.length && !d" class="lp-card px-6 py-12 flex flex-col items-center text-center gap-3 st-studio">
      <span class="sk-ico sk-ico-lg"><Icon name="inbox" :size="22" /></span>
      <p class="text-[14px] font-semibold text-stone-700">{{ t('souk.studioNone') }}</p>
      <router-link :to="{ name: 'SoukBoard' }" class="lp-tap h-10 px-4 rounded-xl bg-white ring-1 ring-inset ring-stone-300 text-[13px] font-semibold inline-flex items-center gap-1.5 hover:bg-stone-50">
        {{ t('souk.pub.toBoard') }}<Icon name="arrow-right" :size="14" class="rtl:rotate-180" />
      </router-link>
    </div>

    <!-- Desktop: the queue beside the product. A phone: the queue is its own
         view (/souk/studio), the product another (/souk/studio/:name). -->
    <div v-else-if="data" class="grid grid-cols-1 lg:grid-cols-[300px_minmax(0,1fr)] gap-4 items-start">
      <aside :aria-label="t('souk.pub.queueLbl')" class="sk-sec st-studio" :class="listOnly ? '' : 'hidden lg:block'">
        <div class="sk-sec-h">
          <span class="sk-ico sk-ico-sm"><Icon name="layers" :size="14" /></span>
          <div class="min-w-0 flex-1">
            <div class="sk-sec-t">{{ t('souk.nProducts').replace('{n}', data.queue.length) }}</div>
            <div class="sk-sec-s">{{ t('souk.oldestFirst') }}</div>
          </div>
        </div>
        <div v-if="!data.queue.length" class="p-6 text-center text-[13px] text-stone-500">{{ t('souk.studioNone') }}</div>
        <router-link v-for="q in data.queue" :key="q.name" :to="{ name: 'SoukStudio', params: { name: q.name } }"
                     class="flex items-center gap-2.5 px-3.5 py-2.5 border-t border-stone-100 min-h-[64px] transition-colors"
                     :class="d && d.name === q.name ? 'st-soft qsel' : 'hover:bg-stone-50'">
          <img v-if="q.image" :src="q.image" class="w-11 h-11 shrink-0 rounded-xl object-cover bg-stone-100" alt="" />
          <span v-else class="w-11 h-11 shrink-0 rounded-xl bg-stone-100 text-stone-400 inline-flex items-center justify-center"><Icon name="image" :size="16" /></span>
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-semibold truncate ltr:text-left rtl:text-right" dir="auto">{{ q.title }}</div>
            <div class="text-[12px] text-stone-600 truncate">{{ t('souk.nColors').replace('{n}', q.colors) }} · {{ t('souk.nRaw').replace('{n}', q.raw) }}</div>
          </div>
          <span class="text-[11px] font-bold rounded-full px-2 py-0.5 whitespace-nowrap tabular-nums inline-flex items-center gap-1"
                :class="q.late ? 'bg-rose-50 text-rose-700' : 'st-tint st-ink'"><Icon name="clock" :size="11" />{{ ageText(q.age) }}</span>
        </router-link>
      </aside>

      <!-- product -->
      <div class="min-w-0" :class="listOnly ? 'hidden lg:block' : ''">
        <router-link v-if="!listOnly" :to="{ name: 'SoukStudio' }"
                     class="lg:hidden lp-tap h-11 -ms-1 mb-1 px-1 inline-flex items-center gap-1 text-[14px] font-semibold text-stone-700">
          <Icon name="chevron-left" :size="18" class="rtl:rotate-180" />{{ t('souk.pub.backToQueue') }} · {{ data.queue.length }}
        </router-link>
        <div v-if="!d" class="lp-card p-8 text-center text-[14px] text-stone-500">{{ t('souk.studioPick') }}</div>
        <div v-else class="space-y-3.5">
          <!-- the card: who it is, how long it has waited, what is left -->
          <section class="sk-hero st-studio p-4 space-y-3">
            <div class="flex items-start gap-3">
              <img v-if="d.image" :src="d.image" class="w-14 h-14 rounded-xl object-cover bg-white shrink-0 ring-1 ring-black/5" alt="" />
              <div class="min-w-0 flex-1 space-y-1.5">
                <h2 class="text-[17px] font-bold break-words leading-snug" dir="auto">{{ d.title }}</h2>
                <div class="flex flex-wrap gap-1.5">
                  <span class="chip-meta mono" dir="ltr">{{ d.name }}</span>
                  <span v-if="d.brand" class="chip-meta">{{ d.brand }}</span>
                  <span class="chip-meta">{{ t('souk.pub.colorsSizes').replace('{c}', realColorCount).replace('{s}', sizes.length || 1) }}</span>
                  <span v-if="d.samples.length" class="chip-meta" :title="d.samples.map((s) => s.sku + '×' + s.qty).join(' · ')"><Icon name="package" :size="12" />{{ t('souk.pub.sampleIn') }} · {{ d.samples.reduce((n, s) => n + Number(s.qty || 0), 0) }}</span>
                </div>
              </div>
              <router-link :to="{ name: 'SoukProduct', params: { name: d.name } }" class="lp-tap shrink-0 h-9 px-3 rounded-xl bg-white/80 ring-1 ring-inset ring-stone-200 text-[12px] font-semibold text-stone-700 inline-flex items-center gap-1 hover:bg-white">
                {{ t('souk.toProduct') }}<Icon name="arrow-right" :size="13" class="rtl:rotate-180" />
              </router-link>
            </div>
            <div v-if="clock" class="space-y-1">
              <div class="flex justify-between gap-2 text-[12px] font-semibold" :class="clock.late ? 'text-rose-700' : 'text-stone-700'">
                <span class="inline-flex items-center gap-1"><Icon name="clock" :size="12" />{{ clock.text }}</span>
              </div>
              <div v-if="clock.pct != null" class="h-1.5 rounded-full bg-white/70 overflow-hidden">
                <div class="h-full rounded-full" :class="clock.late ? 'bg-rose-500' : 'st-solid'" :style="{ width: clock.pct + '%' }" />
              </div>
            </div>
            <!-- what is left before content: one line per colour -->
            <div class="flex flex-wrap gap-1.5">
              <span v-for="z in coverage" :key="z.code" class="text-[12px] font-semibold rounded-full ps-1.5 pe-2.5 py-0.5 inline-flex items-center gap-1"
                    :class="z.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'">
                <span v-if="z.code" class="w-3 h-3 rounded-full ring-1 ring-black/10" :style="{ background: swatch(z.code) }" />
                <Icon :name="z.ok ? 'check' : 'circle'" :size="12" />{{ z.label }} · {{ z.n }}
              </span>
            </div>
          </section>

          <div v-if="d.error" class="bg-rose-50 rounded-xl px-3 py-2.5 text-[13px] text-rose-700 break-words flex gap-2"><Icon name="alert-circle" :size="15" class="shrink-0 mt-0.5" />{{ d.error }}</div>
          <div v-if="!d.canEdit" class="bg-stone-100 rounded-xl px-3 py-2.5 text-[13px] text-stone-700">{{ t('souk.studioNotNow') }}</div>

          <!-- the photo set (souk_set): drawn shots checked against the floor
               photos, the words drawn by code, a person accepts -->
          <section v-if="ps && d.canEdit && (ps.ready || ps.items.length || ps.why === 'setoff' && isManager)" class="sk-sec st-studio">
            <div class="sk-sec-h">
              <span class="sk-ico sk-ico-sm sk-ico-solid"><Icon name="layout-grid" :size="14" /></span>
              <div class="min-w-0 flex-1">
                <div class="sk-sec-t">{{ t('souk.ss.title') }}<template v-if="ps.items.length"> · {{ ps.items.length }}</template></div>
                <div class="sk-sec-s">{{ t('souk.ss.sub') }}</div>
              </div>
              <button v-if="psOk.length" class="lp-tap shrink-0 h-9 px-3 rounded-xl st-solid text-[13px] font-bold inline-flex items-center gap-1.5 disabled:opacity-40"
                      :disabled="busy || aiBusy" @click="setAccept(psOk.map((i) => i.url))">
                <Icon name="check-circle" :size="14" />{{ t('souk.ss.acceptOk').replace('{n}', psOk.length) }}
              </button>
            </div>
            <div class="sk-sec-b space-y-3">
              <div v-if="!ps.ready" class="flex items-start gap-2.5 rounded-xl bg-stone-50 px-3 py-2.5 text-[13px] text-stone-700">
                <Icon name="info" :size="15" class="shrink-0 mt-0.5 text-stone-500" />
                <div class="space-y-1">
                  <div>{{ whyText(ps.why) }}</div>
                  <router-link v-if="isManager && ps.why !== 'migrate'" :to="{ name: 'SoukSettings', hash: '#set-ai' }" class="font-semibold underline st-ink">{{ t('souk.st.openSettings') }}</router-link>
                </div>
              </div>

              <div v-if="psWorking" class="flex items-center gap-2.5 rounded-xl st-soft px-3 py-2.5 text-[13px] font-semibold st-ink">
                <Icon name="refresh-cw" :size="15" class="animate-spin" />
                {{ ps.step === 'draw' ? t('souk.ss.step_draw').replace('{n}', ps.todo.length) : ps.step === 'brief' ? t('souk.ss.step_brief') : t('souk.ss.queued') }}
              </div>
              <div v-if="ps.state === 'error' && ps.error" class="flex items-start gap-2 rounded-xl bg-rose-50 px-3 py-2.5 text-[13px] text-rose-800 break-words">
                <Icon name="alert-circle" :size="15" class="shrink-0 mt-0.5" />{{ ps.error }}
              </div>

              <!-- what the brief could not settle: checked on the goods -->
              <div v-if="ps.brief && ps.brief.verify && ps.brief.verify.length && ps.items.length" class="rounded-xl bg-amber-50 px-3 py-2.5 space-y-1">
                <div class="text-[13px] font-bold text-amber-900 flex items-center gap-1.5"><Icon name="alert-triangle" :size="14" />{{ t('souk.ss.verifyTitle') }}</div>
                <ul class="text-[13px] text-amber-900 space-y-0.5 list-disc ps-5">
                  <li v-for="(v, k) in ps.brief.verify" :key="k" dir="auto">{{ v }}</li>
                </ul>
              </div>

              <div v-if="ps.items.length || psTodo.length" class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-2.5">
                <div v-for="it in ps.items" :key="it.url" class="rounded-xl ring-1 overflow-hidden bg-white flex flex-col"
                     :class="it.ok === false ? 'ring-rose-300' : 'ring-stone-200'">
                  <button class="relative aspect-square bg-white" :aria-label="t('souk.st.compare')" @click="openSet(it)">
                    <img :src="it.url" class="w-full h-full object-contain" alt="" loading="lazy" />
                    <span class="absolute top-1.5 start-1.5 text-[11px] font-bold rounded-full px-2 py-0.5 bg-white/90 text-stone-700 inline-flex items-center gap-1">
                      <span v-if="it.color" class="w-2.5 h-2.5 rounded-full ring-1 ring-black/10" :style="{ background: swatch(it.color) }" />{{ t('souk.ss.shot_' + it.shot) }}
                    </span>
                  </button>
                  <div class="px-2 py-1.5 border-t border-stone-100 space-y-1 text-[12px]">
                    <div v-if="['detail', 'real', 'colours'].includes(it.shot)" class="font-semibold text-stone-600 flex items-center gap-1"><Icon name="camera" :size="12" />{{ it.shot === 'colours' ? t('souk.ss.shot_colours') : t('souk.ss.fromFloor') }}</div>
                    <div v-else class="font-semibold flex flex-wrap items-center gap-x-1"
                         :class="it.ok === true ? 'text-emerald-700' : it.ok === false ? 'text-rose-700' : 'text-stone-500'">
                      <Icon :name="it.ok === true ? 'check-circle' : it.ok === false ? 'alert-triangle' : 'help-circle'" :size="12" />
                      {{ it.ok === true ? t('souk.ss.qcOk') : it.ok === false ? t('souk.ss.qcBad') : t('souk.ss.qcNone') }}
                      <span v-if="it.tries > 1" class="basis-full text-stone-500 font-normal">{{ t('souk.ss.tries').replace('{n}', it.tries) }}</span>
                    </div>
                    <ul v-if="it.notes && it.notes.length" class="text-rose-800 space-y-0.5">
                      <li v-for="(n, k) in it.notes" :key="k" dir="auto">• {{ n }}</li>
                    </ul>
                    <div v-if="it.shot === 'box' && it.numbered === 0" class="text-amber-800">{{ t('souk.ss.noNumbers') }}</div>
                    <div v-if="it.edited" class="text-stone-500">{{ t('souk.ss.edited') }}</div>
                  </div>
                  <div class="grid grid-cols-[1fr_auto_auto] border-t border-stone-100 mt-auto">
                    <button class="h-10 text-[13px] font-bold text-emerald-700 hover:bg-emerald-50 inline-flex items-center justify-center gap-1 disabled:opacity-40"
                            :disabled="busy || aiBusy" @click="setAccept([it.url])"><Icon name="check" :size="15" />{{ t('souk.st.accept') }}</button>
                    <button class="h-10 w-10 border-s border-stone-100 text-stone-600 hover:bg-stone-50 inline-flex items-center justify-center disabled:opacity-40"
                            :disabled="busy || aiBusy || !ps.ready || psWorking" :title="t('souk.st.redo')" :aria-label="t('souk.st.redo')" @click="setStart([it.id])"><Icon name="refresh-cw" :size="14" /></button>
                    <button class="h-10 w-10 border-s border-stone-100 text-rose-600 hover:bg-rose-50 inline-flex items-center justify-center disabled:opacity-40"
                            :disabled="busy || aiBusy" :title="t('souk.st.reject')" :aria-label="t('souk.st.reject')" @click="setReject(it.url)"><Icon name="x" :size="15" /></button>
                  </div>
                </div>
                <div v-for="id in psTodo" :key="'todo-' + id" class="rounded-xl ring-1 ring-stone-200 overflow-hidden bg-white">
                  <div class="relative aspect-square bg-stone-50 flex items-center justify-center">
                    <span class="sk-ico st-studio"><Icon name="sparkles" :size="16" class="animate-pulse" /></span>
                  </div>
                  <div class="h-10 border-t border-stone-100 text-[12px] font-semibold text-stone-500 flex items-center justify-center">{{ t('souk.ss.shot_' + id.split(':')[0]) }}</div>
                </div>
              </div>

              <div v-for="f in ps.failed" :key="'sf-' + f.id" class="flex items-center gap-2.5 rounded-xl bg-rose-50 px-2.5 py-2 text-[12px] text-rose-800">
                <Icon name="alert-circle" :size="15" class="shrink-0" />
                <span class="flex-1 min-w-0 break-words"><b>{{ t('souk.ss.shot_' + f.shot) }}</b> · {{ t('souk.ss.failedOne') }} <span class="opacity-75" dir="ltr">{{ f.error }}</span></span>
                <button v-if="ps.ready && !psWorking" class="lp-tap shrink-0 h-8 px-2.5 rounded-lg bg-white ring-1 ring-inset ring-rose-200 font-semibold inline-flex items-center gap-1 disabled:opacity-40"
                        :disabled="aiBusy" @click="setStart([f.id])"><Icon name="refresh-cw" :size="12" />{{ t('souk.st.retry') }}</button>
              </div>

              <!-- the words on the photos: edited here, redrawn by code for free -->
              <details v-if="ps.brief && ps.items.some((i) => i.editable)" class="rounded-xl ring-1 ring-stone-200 bg-white group" @toggle="onTextsToggle">
                <summary class="px-3 min-h-[44px] flex items-center gap-2 cursor-pointer text-[13px] font-bold text-stone-800 list-none">
                  <Icon name="pen-line" :size="14" />{{ t('souk.ss.textsTitle') }}
                  <span class="text-[12px] font-normal text-stone-500 hidden sm:inline">· {{ t('souk.ss.textsHint') }}</span>
                  <Icon name="chevron-down" :size="14" class="ms-auto transition-transform group-open:rotate-180" />
                </summary>
                <div v-if="tx" class="px-3 pb-3 grid gap-2.5 sm:grid-cols-2 text-[13px]" dir="ltr">
                  <label class="sm:col-span-2 space-y-1"><span class="block font-semibold text-stone-700" dir="auto">{{ t('souk.ss.headline') }}</span>
                    <input v-model="tx.headlineFr" maxlength="48" class="w-full h-10 rounded-lg border border-stone-300 px-2.5" /></label>
                  <label class="sm:col-span-2 space-y-1"><span class="block font-semibold text-stone-700" dir="auto">{{ t('souk.ss.benefits') }}</span>
                    <textarea v-model="tx.benefits" rows="5" class="w-full rounded-lg border border-stone-300 px-2.5 py-2" /></label>
                  <label class="space-y-1"><span class="block font-semibold text-stone-700" dir="auto">{{ t('souk.ss.scaleValue') }}</span>
                    <input v-model="tx.scaleValue" maxlength="12" class="w-full h-10 rounded-lg border border-stone-300 px-2.5" /></label>
                  <label class="space-y-1"><span class="block font-semibold text-stone-700" dir="auto">{{ t('souk.ss.scaleLine1') }}</span>
                    <input v-model="tx.scaleLine1Fr" maxlength="44" class="w-full h-10 rounded-lg border border-stone-300 px-2.5" /></label>
                  <label class="sm:col-span-2 space-y-1"><span class="block font-semibold text-stone-700" dir="auto">{{ t('souk.ss.scaleLine2') }}</span>
                    <input v-model="tx.scaleLine2Fr" maxlength="52" class="w-full h-10 rounded-lg border border-stone-300 px-2.5" /></label>
                  <template v-if="ps.items.some((i) => i.shot === 'box')">
                    <label class="space-y-1"><span class="block font-semibold text-stone-700" dir="auto">{{ t('souk.ss.packCount') }}</span>
                      <input v-model.number="tx.packCount" type="number" min="2" max="24" class="w-full h-10 rounded-lg border border-stone-300 px-2.5" /></label>
                    <label class="space-y-1"><span class="block font-semibold text-stone-700" dir="auto">{{ t('souk.ss.pieces') }}</span>
                      <input v-model="tx.piecesFr" maxlength="24" class="w-full h-10 rounded-lg border border-stone-300 px-2.5" /></label>
                    <label class="sm:col-span-2 space-y-1"><span class="block font-semibold text-stone-700" dir="auto">{{ t('souk.ss.boxSub') }}</span>
                      <input v-model="tx.boxSubFr" maxlength="48" class="w-full h-10 rounded-lg border border-stone-300 px-2.5" /></label>
                  </template>
                  <label class="sm:col-span-2 flex items-center gap-2.5 min-h-[40px] cursor-pointer" dir="auto">
                    <input v-model="tx.trust" type="checkbox" class="w-5 h-5 shrink-0" style="accent-color: rgb(var(--st))" />
                    <span class="font-semibold text-stone-700">{{ t('souk.ss.trust') }}</span>
                  </label>
                  <div class="sm:col-span-2" dir="auto">
                    <button class="lp-tap h-10 px-4 rounded-xl st-solid text-[13px] font-bold inline-flex items-center gap-1.5 disabled:opacity-40"
                            :disabled="aiBusy || psWorking" @click="setRetext"><Icon name="pen-line" :size="14" />{{ t('souk.ss.redraw') }}</button>
                  </div>
                </div>
              </details>

              <!-- start / remake -->
              <div v-if="ps.ready && !psWorking" class="flex flex-wrap items-center gap-3">
                <button class="lp-tap h-11 px-4 rounded-xl text-[14px] font-bold inline-flex items-center gap-2 disabled:opacity-40"
                        :class="ps.items.length ? 'bg-white ring-1 ring-inset ring-stone-300 text-stone-700' : 'st-solid'"
                        :disabled="aiBusy || !d.photos.length" @click="setStart([])">
                  <Icon :name="ps.items.length ? 'refresh-cw' : 'sparkles'" :size="16" />{{ ps.items.length ? t('souk.ss.remake') : t('souk.ss.make') }}
                </button>
                <button v-if="ps.brief" class="lp-tap h-11 px-3 rounded-xl text-[13px] font-semibold text-stone-700 hover:bg-stone-50 inline-flex items-center gap-1.5 disabled:opacity-40"
                        :disabled="aiBusy" :title="t('souk.ss.newBriefHint')" @click="setStart([], true)"><Icon name="eye" :size="15" />{{ t('souk.ss.newBrief') }}</button>
                <span class="text-[12px] text-stone-600">{{ t('souk.ss.cost').replace('{usd}', ps.usd.toFixed(2)).replace('{model}', ps.model) }}<template v-if="ps.spent"> · {{ t('souk.ss.spent').replace('{usd}', ps.spent.toFixed(2)) }}</template></span>
              </div>
              <p v-if="ps.items.length" class="text-[12px] text-stone-500 flex items-start gap-1.5"><Icon name="info" :size="12" class="mt-[2px] shrink-0" />{{ t('souk.ss.rule') }}</p>
            </div>
          </section>

          <!-- web pack: the AI's suggestions, each accepted by a person -->
          <section v-if="ai && d.canEdit" class="sk-sec st-studio">
            <div class="sk-sec-h">
              <span class="sk-ico sk-ico-sm sk-ico-solid"><Icon name="sparkles" :size="14" /></span>
              <div class="min-w-0 flex-1">
                <div class="sk-sec-t">{{ t('souk.st.aiTitle') }}<template v-if="ai.items.length"> · {{ ai.items.length }}</template></div>
                <div class="sk-sec-s">{{ t('souk.st.aiSub') }}</div>
              </div>
              <button v-if="ai.items.length > 1" class="lp-tap shrink-0 h-9 px-3 rounded-xl st-solid text-[13px] font-bold inline-flex items-center gap-1.5 disabled:opacity-40"
                      :disabled="busy || aiBusy" @click="aiAccept(ai.items.map((i) => i.url))">
                <Icon name="check" :size="14" />{{ t('souk.st.acceptAll') }}
              </button>
            </div>
            <div class="sk-sec-b space-y-3">
              <!-- cannot run: say why, and where it is switched on -->
              <div v-if="!ai.ready && !ai.items.length" class="flex items-start gap-2.5 rounded-xl bg-stone-50 px-3 py-2.5 text-[13px] text-stone-700">
                <Icon name="info" :size="15" class="shrink-0 mt-0.5 text-stone-500" />
                <div class="space-y-1">
                  <div>{{ t('souk.st.why_' + ai.why) }}</div>
                  <router-link v-if="isManager && ai.why !== 'migrate'" :to="{ name: 'SoukSettings', hash: '#set-ai' }" class="font-semibold underline st-ink">{{ t('souk.st.openSettings') }}</router-link>
                </div>
              </div>

              <!-- working -->
              <div v-if="cutWorking" class="flex items-center gap-2.5 rounded-xl st-soft px-3 py-2.5 text-[13px] font-semibold st-ink">
                <Icon name="refresh-cw" :size="15" class="animate-spin" />
                {{ t('souk.st.working').replace('{n}', ai.todo.length) }}
              </div>

              <div v-if="ai.items.length || ai.todo.length" class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-2.5">
                <div v-for="it in ai.items" :key="it.url" class="rounded-xl ring-1 ring-stone-200 overflow-hidden bg-white flex flex-col">
                  <button class="relative aspect-square bg-white" :aria-label="t('souk.st.compare')" @click="big = it">
                    <img :src="it.url" class="w-full h-full object-contain" alt="" loading="lazy" />
                    <img :src="it.src" class="absolute bottom-1.5 start-1.5 w-11 h-11 rounded-lg object-cover ring-2 ring-white shadow" alt="" loading="lazy" :title="t('souk.st.before')" />
                    <span class="absolute top-1.5 start-1.5 text-[11px] font-bold rounded-full px-2 py-0.5 bg-white/90 text-stone-700 inline-flex items-center gap-1">
                      <span v-if="it.color" class="w-2.5 h-2.5 rounded-full ring-1 ring-black/10" :style="{ background: swatch(it.color) }" />{{ slotName(it.slot) }}
                    </span>
                  </button>
                  <div class="grid grid-cols-[1fr_auto_auto] border-t border-stone-100">
                    <button class="h-10 text-[13px] font-bold text-emerald-700 hover:bg-emerald-50 inline-flex items-center justify-center gap-1 disabled:opacity-40"
                            :disabled="busy || aiBusy" @click="aiAccept([it.url])"><Icon name="check" :size="15" />{{ t('souk.st.accept') }}</button>
                    <button class="h-10 w-10 border-s border-stone-100 text-stone-600 hover:bg-stone-50 inline-flex items-center justify-center disabled:opacity-40"
                            :disabled="busy || aiBusy || !ai.ready" :title="t('souk.st.redo')" :aria-label="t('souk.st.redo')" @click="aiStart([it.src])"><Icon name="refresh-cw" :size="14" /></button>
                    <button class="h-10 w-10 border-s border-stone-100 text-rose-600 hover:bg-rose-50 inline-flex items-center justify-center disabled:opacity-40"
                            :disabled="busy || aiBusy" :title="t('souk.st.reject')" :aria-label="t('souk.st.reject')" @click="aiReject(it.url)"><Icon name="x" :size="15" /></button>
                  </div>
                </div>
                <!-- still being made -->
                <div v-for="u in ai.todo" :key="'todo-' + u" class="rounded-xl ring-1 ring-stone-200 overflow-hidden bg-white">
                  <div class="relative aspect-square">
                    <img :src="u" class="w-full h-full object-cover opacity-40 blur-[1px]" alt="" loading="lazy" />
                    <span class="absolute inset-0 flex items-center justify-center"><span class="sk-ico st-studio"><Icon name="sparkles" :size="16" class="animate-pulse" /></span></span>
                  </div>
                  <div class="h-10 border-t border-stone-100 text-[12px] font-semibold text-stone-500 flex items-center justify-center">{{ t('souk.st.queued') }}</div>
                </div>
              </div>

              <div v-for="f in ai.failed" :key="'f-' + f.src" class="flex items-center gap-2.5 rounded-xl bg-rose-50 px-2.5 py-2 text-[12px] text-rose-800">
                <img :src="f.src" class="w-9 h-9 rounded-lg object-cover shrink-0" alt="" />
                <span class="flex-1 min-w-0 break-words">{{ t('souk.st.failedOne') }} <span class="opacity-75">{{ f.error }}</span></span>
                <button v-if="ai.ready" class="lp-tap shrink-0 h-8 px-2.5 rounded-lg bg-white ring-1 ring-inset ring-rose-200 font-semibold inline-flex items-center gap-1 disabled:opacity-40"
                        :disabled="aiBusy" @click="aiStart([f.src])"><Icon name="refresh-cw" :size="12" />{{ t('souk.st.retry') }}</button>
              </div>

              <!-- nothing yet: one button for the website angles -->
              <div v-if="ai.ready && !ai.items.length && !ai.todo.length" class="flex flex-wrap items-center gap-3">
                <button class="lp-tap h-11 px-4 rounded-xl st-solid text-[14px] font-bold inline-flex items-center gap-2 disabled:opacity-40"
                        :disabled="aiBusy || !autoSrcs.length" @click="aiStart([])">
                  <Icon name="sparkles" :size="16" />{{ t('souk.st.make').replace('{n}', autoSrcs.length) }}
                </button>
                <span class="text-[12px] text-stone-600">{{ t('souk.st.cost').replace('{usd}', (ai.usd * autoSrcs.length).toFixed(2)) }}</span>
              </div>
              <p v-if="ai.items.length || ai.todo.length" class="text-[12px] text-stone-500 flex items-center gap-1.5"><Icon name="info" :size="12" />{{ t('souk.st.rule') }}</p>
            </div>
          </section>

          <!-- in-house photos -->
          <section class="sk-sec st-photos">
            <div class="sk-sec-h">
              <span class="sk-ico sk-ico-sm"><Icon name="camera" :size="14" /></span>
              <div class="min-w-0 flex-1">
                <div class="sk-sec-t">{{ t('souk.rawPhotos') }} · {{ d.photos.length }}</div>
                <div class="sk-sec-s">{{ ai && ai.ready && d.canEdit ? t('souk.st.rawSubAi') : t('souk.st.rawSub') }}</div>
              </div>
              <a v-if="d.photos.length" :href="zipUrl" class="lp-tap shrink-0 h-9 px-3 rounded-xl bg-white/80 ring-1 ring-inset ring-stone-200 text-[13px] font-semibold text-stone-700 inline-flex items-center gap-1.5 hover:bg-white">
                <Icon name="download" :size="14" />{{ t('souk.downloadAll') }}
              </a>
            </div>
            <div class="sk-sec-b space-y-3">
              <div v-for="c in d.colors" :key="c.code" class="space-y-1.5">
                <div class="flex items-center gap-1.5 text-[13px] font-semibold text-stone-700">
                  <span v-if="c.code" class="w-3.5 h-3.5 rounded-full ring-1 ring-black/10" :style="{ background: swatch(c.code) }" />
                  {{ colorName(c) }} <span class="text-stone-400 font-normal">· {{ rawOf(c.code).length }}</span>
                </div>
                <div class="grid grid-cols-4 sm:grid-cols-6 xl:grid-cols-8 gap-1.5">
                  <div v-for="p in rawOf(c.code)" :key="p.url" class="relative">
                    <a :href="p.url" target="_blank" rel="noopener" class="block aspect-square rounded-lg overflow-hidden bg-stone-100" :title="slotName(p.slot)">
                      <img :src="p.url" class="w-full h-full object-cover" alt="" loading="lazy" />
                    </a>
                    <span class="absolute bottom-1 start-1 text-[10px] font-semibold rounded px-1 bg-black/55 text-white max-w-[calc(100%-2.5rem)] truncate">{{ slotName(p.slot) }}</span>
                    <button v-if="ai && ai.ready && d.canEdit && !hasAi(p.url)" class="absolute top-1 end-1 w-7 h-7 rounded-lg bg-white/90 st-studio st-ink hover:bg-white inline-flex items-center justify-center disabled:opacity-40"
                            :disabled="aiBusy" :title="t('souk.st.makeOne')" :aria-label="t('souk.st.makeOne')" @click="aiStart([p.url])"><Icon name="sparkles" :size="13" /></button>
                  </div>
                </div>
              </div>
              <div v-if="sizes.length || d.specs || weights" class="grid gap-1.5 sm:grid-cols-3 text-[13px]">
                <div v-if="sizes.length" class="rounded-xl bg-stone-50 px-3 py-2"><div class="text-[11px] font-semibold text-stone-500">{{ t('souk.sizesLbl') }}</div><div class="font-semibold text-stone-800">{{ sizes.join(' · ') }}</div></div>
                <div v-if="d.specs" class="rounded-xl bg-stone-50 px-3 py-2 sm:col-span-1"><div class="text-[11px] font-semibold text-stone-500">{{ t('souk.specs') }}</div><bdi class="font-semibold text-stone-800">{{ d.specs }}</bdi></div>
                <div v-if="weights" class="rounded-xl bg-stone-50 px-3 py-2"><div class="text-[11px] font-semibold text-stone-500">{{ t('souk.weightLbl') }}</div><div class="font-semibold text-stone-800" dir="ltr">{{ weights }}</div></div>
              </div>
            </div>
          </section>

          <!-- finals (a file dropped anywhere here, off a colour zone, goes in
               untied rather than making the browser open it) -->
          <section class="sk-sec st-studio" @dragover="onSectionOver" @drop="onSectionDrop">
            <div class="sk-sec-h">
              <span class="sk-ico sk-ico-sm"><Icon name="image" :size="14" /></span>
              <div class="min-w-0 flex-1">
                <div class="sk-sec-t">{{ t('souk.finals') }}<template v-if="order.length"> · {{ order.length }}</template></div>
                <div class="sk-sec-s">
                  <template v-if="orderSaving">{{ t('souk.pub.orderSaving') }}</template>
                  <template v-else-if="d.canEdit">
                    <span class="souk-fine">{{ t('souk.pub.dragHint') }}</span><span class="souk-coarse">{{ t('souk.pub.dragHintTouch') }}</span>
                  </template>
                  <template v-else>{{ t('souk.finalsHint') }}</template>
                </div>
              </div>
            </div>
            <div class="sk-sec-b space-y-3">
              <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-2.5">
                <div v-for="(f, i) in order" :key="f.url"
                     class="flex flex-col gap-1.5 min-w-0 transition-opacity"
                     :class="[dragFrom === i ? 'opacity-40' : '', d.canEdit ? 'souk-grab' : '']"
                     :draggable="d.canEdit && !busy"
                     @dragstart="onDragStart($event, i)" @dragenter.prevent="onDragOver($event, i)" @dragover="onDragOver($event, i)"
                     @drop="onDropCard($event)" @dragend="onDragEnd">
                  <div class="relative aspect-[4/5] rounded-xl overflow-hidden bg-stone-100"
                       :class="dragFrom === i ? 'ring-2 ring-[var(--accent-500)]' : i === 0 ? 'ring-2 st-ring' : ''">
                    <img :src="f.url" class="w-full h-full object-cover pointer-events-none select-none" alt="" loading="lazy" draggable="false" />
                    <span class="absolute top-1.5 start-1.5 text-[11px] font-bold rounded-full px-2 py-px"
                          :class="i === 0 ? 'st-solid' : 'bg-stone-900/80 text-white'">{{ i === 0 ? t('souk.mainPhoto') : i + 1 }}</span>
                    <span v-if="f.ai" class="absolute top-8 start-1.5 text-[10px] font-bold rounded-full px-1.5 py-px bg-white/90 st-ink inline-flex items-center gap-0.5"><Icon name="sparkles" :size="10" />{{ t('souk.st.aiBadge') }}</span>
                    <button v-if="d.canEdit" class="absolute top-1 end-1 w-8 h-8 rounded-lg bg-white/90 text-rose-700 hover:bg-white inline-flex items-center justify-center disabled:opacity-30"
                            :disabled="busy" :title="t('souk.remove')" :aria-label="t('souk.remove')" @click="removeFinal(f.url)">
                      <Icon name="trash-2" :size="15" />
                    </button>
                    <div v-if="d.canEdit && order.length > 1" class="absolute bottom-1 end-1 flex gap-1">
                      <button class="w-8 h-8 rounded-lg bg-white/90 text-stone-700 hover:bg-white inline-flex items-center justify-center disabled:opacity-30"
                              :disabled="i === 0 || busy" :title="t('souk.pub.moveEarlier')" :aria-label="t('souk.pub.moveEarlier')" @click="nudge(i, -1)">
                        <Icon name="arrow-up" :size="15" />
                      </button>
                      <button class="w-8 h-8 rounded-lg bg-white/90 text-stone-700 hover:bg-white inline-flex items-center justify-center disabled:opacity-30"
                              :disabled="i === order.length - 1 || busy" :title="t('souk.pub.moveLater')" :aria-label="t('souk.pub.moveLater')" @click="nudge(i, 1)">
                        <Icon name="arrow-down" :size="15" />
                      </button>
                    </div>
                  </div>
                  <label v-if="d.colors.length > 1" :for="'fc-' + i" class="sr-only">{{ t('souk.colorsLbl') }} {{ i + 1 }}</label>
                  <select v-if="d.colors.length > 1" :id="'fc-' + i" :value="f.color" :disabled="!d.canEdit || busy"
                          class="w-full h-8 rounded-lg border border-stone-300 px-1.5 text-[13px] bg-white" @change="setColor(i, $event.target.value)">
                    <option value="">{{ t('souk.allColors') }}</option>
                    <option v-for="c in d.colors" :key="c.code" :value="c.code">{{ colorName(c) }}</option>
                  </select>
                </div>

                <!-- one colour (or none): the upload tile closes the grid -->
                <label v-if="d.canEdit && zones.length === 1"
                       class="aspect-[4/5] rounded-xl bg-stone-50 outline-2 outline-dashed -outline-offset-2 flex flex-col items-center justify-center gap-1.5 text-[13px] font-semibold text-stone-600 cursor-pointer text-center px-2 hover:bg-stone-100"
                       :class="[hoverZone === '' ? 'outline-[var(--accent-500)] bg-[var(--accent-50)]' : 'outline-stone-300', uploading ? 'opacity-60 pointer-events-none' : '']"
                       @dragover="onZoneOver($event, '')" @dragleave="hoverZone = null" @drop="onZoneDrop($event, '')">
                  <Icon name="upload-cloud" :size="22" />
                  <span>{{ uploading ? t('souk.uploadingN').replace('{n}', uploading) : hoverZone === '' ? t('souk.pub.dropHere') : t('souk.uploadFinals') }}</span>
                  <input type="file" accept="image/*" multiple class="hidden" @change="onFiles($event, '')" />
                </label>
              </div>
              <div v-if="!order.length && !d.canEdit" class="text-center text-[13px] text-stone-500 py-6">{{ t('souk.noFinals') }}</div>

              <!-- several colours: one drop zone per colour, tied to it -->
              <div v-if="d.canEdit && zones.length > 1" class="space-y-1.5">
                <div class="text-[13px] font-semibold text-stone-700">{{ t('souk.pub.addFor') }}</div>
                <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-2">
                  <label v-for="z in zones" :key="z.code"
                         class="min-h-[72px] rounded-xl px-3 py-2 outline-2 outline-dashed -outline-offset-2 flex flex-col items-center justify-center gap-0.5 text-center cursor-pointer"
                         :class="[hoverZone === z.code ? 'outline-[var(--accent-500)] bg-[var(--accent-50)]'
                           : z.missing ? 'outline-amber-300 bg-amber-50' : 'outline-stone-300 bg-stone-50 hover:bg-stone-100',
                           uploading ? 'opacity-60 pointer-events-none' : '']"
                         @dragover="onZoneOver($event, z.code)" @dragleave="hoverZone = null" @drop="onZoneDrop($event, z.code)">
                    <span class="inline-flex items-center gap-1 text-[13px] font-bold text-stone-800">
                      <span v-if="z.code" class="w-3 h-3 rounded-full ring-1 ring-black/10" :style="{ background: swatch(z.code) }" /><Icon v-else name="upload-cloud" :size="15" />{{ z.label }}
                    </span>
                    <span class="text-[12px]" :class="z.missing ? 'text-amber-800 font-semibold' : 'text-stone-600'">
                      {{ uploadingCode === z.code && uploading ? t('souk.uploadingN').replace('{n}', uploading)
                        : hoverZone === z.code ? t('souk.pub.dropHere')
                        : z.count ? t('souk.pub.nFinals').replace('{n}', z.count) : t('souk.pub.noneYet') }}
                    </span>
                    <input type="file" accept="image/*" multiple class="hidden" @change="onFiles($event, z.code)" />
                  </label>
                </div>
              </div>

              <div v-if="d.colorsWithout.length" class="flex items-center gap-2 bg-amber-50 rounded-xl px-2.5 py-2 text-[13px] text-amber-800">
                <Icon name="alert-triangle" :size="15" class="shrink-0 text-amber-700" />
                <span>{{ t('souk.colorNeedsFinal').replace('{list}', d.colorsWithout.map(colorOf).join(' · ')) }}</span>
              </div>
            </div>
          </section>

          <!-- actions -->
          <section v-if="d.canEdit" class="lp-card p-4 space-y-3">
            <div v-if="returning" class="space-y-2 rounded-xl bg-amber-50/70 p-3">
              <label class="block text-[13px] font-bold" for="souk-return">{{ t('souk.returnWhy') }}</label>
              <textarea id="souk-return" v-model="reason" rows="2" class="w-full rounded-xl border border-stone-300 px-3 py-2 text-[14px] bg-white" :placeholder="t('souk.returnHint')" />
              <div class="flex gap-2 flex-wrap">
                <button class="h-[42px] px-4 rounded-xl bg-amber-600 text-white text-[14px] font-bold disabled:opacity-40" :disabled="busy || !reason.trim()" @click="sendBack">{{ t('souk.returnConfirm') }}</button>
                <button class="h-[42px] px-4 rounded-xl bg-white ring-1 ring-inset ring-stone-300 text-[14px] font-semibold text-stone-700" @click="returning = false">{{ t('souk.cancel') }}</button>
              </div>
            </div>
            <div class="flex gap-2 flex-wrap items-center">
              <button class="st-content w-full sm:w-auto h-12 px-5 rounded-xl st-solid text-[15px] font-bold inline-flex items-center justify-center gap-2 disabled:!bg-stone-200 disabled:!text-stone-500 disabled:shadow-none"
                      :disabled="busy || !!uploading || orderSaving || !order.length || d.colorsWithout.length > 0" @click="send">
                <Icon name="notebook-pen" :size="17" />{{ busy && !orderSaving ? t('souk.sending') : t('souk.toContent') }}
              </button>
              <button v-if="!returning" class="w-full sm:w-auto min-h-[44px] py-2 px-4 rounded-xl bg-white ring-1 ring-inset ring-stone-300 text-[14px] font-semibold text-stone-700 hover:bg-stone-50 inline-flex items-center justify-center gap-1.5" @click="returning = true">
                <Icon name="undo-2" :size="15" />{{ t('souk.returnToFloor') }}
              </button>
            </div>
            <p class="text-[12px] text-stone-500">{{ t('souk.toContentNote') }}</p>
          </section>
        </div>
      </div>
    </div>

    <!-- before / after -->
    <div v-if="big" class="fixed inset-0 z-50 bg-black/80 p-4 flex items-center justify-center" @click.self="big = null">
      <div class="bg-white rounded-2xl p-3 w-full max-w-[920px] space-y-2">
        <div class="flex items-center justify-between gap-2">
          <span class="text-[14px] font-bold">{{ big.label || slotName(big.slot) }}</span>
          <button class="w-9 h-9 rounded-lg hover:bg-stone-100 inline-flex items-center justify-center" :aria-label="t('souk.cancel')" @click="big = null"><Icon name="x" :size="18" /></button>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <figure class="space-y-1"><img :src="big.src" class="w-full aspect-square object-contain bg-stone-100 rounded-xl" alt="" /><figcaption class="text-[12px] text-center text-stone-600">{{ big.kind === 'set' ? t('souk.ss.compareRef') : t('souk.st.before') }}</figcaption></figure>
          <figure class="space-y-1"><img :src="big.url" class="w-full aspect-square object-contain bg-white ring-1 ring-stone-200 rounded-xl" alt="" /><figcaption class="text-[12px] text-center text-stone-600">{{ t('souk.st.after') }}</figcaption></figure>
        </div>
        <div class="flex gap-2 justify-end">
          <button class="h-10 px-3 rounded-xl text-rose-700 hover:bg-rose-50 text-[13px] font-semibold inline-flex items-center gap-1" :disabled="aiBusy" @click="(big.kind === 'set' ? setReject : aiReject)(big.url); big = null"><Icon name="x" :size="14" />{{ t('souk.st.reject') }}</button>
          <button class="h-10 px-4 rounded-xl bg-emerald-600 text-white text-[13px] font-bold inline-flex items-center gap-1" :disabled="aiBusy" @click="(big.kind === 'set' ? setAccept : aiAccept)([big.url]); big = null"><Icon name="check" :size="14" />{{ t('souk.st.accept') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { postPhoto } from "@/lib/soukPhoto";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { useAuth } from "@/composables/useAuth";
import { swatch } from "@/souk/stages";

const { t, locale } = useI18n();
const { success, warn } = useToast();
const route = useRoute();
const router = useRouter();
const data = ref(null);
const loading = ref(true);
const busy = ref(false);
const uploading = ref(0);
const uploadingCode = ref(null);
const returning = ref(false);
const reason = ref("");
const d = computed(() => data.value?.detail || null);
const auth = useAuth();
const isManager = computed(() => auth.role?.value === "manager");

// --- web pack (souk_ai): suggestions a person accepts --------------------------
const ai = computed(() => d.value?.ai || null);
const aiBusy = ref(false);
const big = ref(null);
const cutWorking = computed(() => !!ai.value && ["queued", "running"].includes(ai.value.state) && ai.value.todo.length > 0);
// the photo set (souk_set)
const ps = computed(() => d.value?.aiSet || null);
const psWorking = computed(() => !!ps.value && ["queued", "running"].includes(ps.value.state) && ps.value.todo.length > 0);
const psTodo = computed(() => (ps.value?.todo || []).filter((id) => id !== "*" && !ps.value.items.some((i) => i.id === id)));
const psOk = computed(() => (ps.value?.items || []).filter((i) => i.ok !== false));
const working = computed(() => cutWorking.value || psWorking.value);
const autoSrcs = computed(() => (d.value?.photos || []).filter((p) => (ai.value?.autoSlots || []).includes(p.slot)).map((p) => p.url));
const hasAi = (url) => !!ai.value && (ai.value.items.some((i) => i.src === url) || ai.value.todo.includes(url));
const slotName = (s) => (s ? t("souk.slot_" + s) : "");
let pollTimer = null;
function schedulePoll() {
  clearTimeout(pollTimer);
  if (!working.value || !d.value) return;
  const name = d.value.name;
  pollTimer = setTimeout(async () => {
    try {
      const det = await api(psWorking.value ? "souk_set.poll" : "souk_ai.poll", { name });
      if (d.value?.name === name) setDetail(det);
    } catch (_) { /* the next tick tries again */ }
    schedulePoll();
  }, 4000);
}
watch(working, schedulePoll);
async function aiCall(method, args) {
  aiBusy.value = true;
  try {
    setDetail(await apiPost("souk_ai." + method, { name: d.value.name, ...args }));
    schedulePoll();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    aiBusy.value = false;
  }
}
const aiStart = (srcs) => aiCall("start", { srcs: JSON.stringify(srcs) });
const aiReject = (url) => aiCall("reject", { url });
async function aiAccept(urls) {
  // A pending arrow re-order goes first: accept appends to the saved list.
  clearTimeout(nudgeTimer);
  if (!sameOrder()) await save(order.value);
  await aiCall("accept", { urls: JSON.stringify(urls) });
}
async function setCall(method, args) {
  aiBusy.value = true;
  try {
    setDetail(await apiPost("souk_set." + method, { name: d.value.name, ...args }));
    schedulePoll();
    return true;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    return false;
  } finally {
    aiBusy.value = false;
  }
}
const setStart = (ids, fresh = false) => setCall("start", { ids: JSON.stringify(ids), fresh: fresh ? 1 : 0 });
const setReject = (url) => setCall("reject", { url });
async function setAccept(urls) {
  clearTimeout(nudgeTimer);
  if (!sameOrder()) await save(order.value);
  await setCall("accept", { urls: JSON.stringify(urls) });
}
const whyText = (w) => {
  const v = t("souk.ss.why_" + w);
  return v === "souk.ss.why_" + w ? t("souk.st.why_" + w) : v;
};
// The words on the photos: a local copy, filled when the panel opens.
const tx = ref(null);
function fillTexts() {
  const b = ps.value?.brief;
  tx.value = b ? {
    headlineFr: b.headlineFr || "", benefits: (b.benefitsFr || []).join("\n"),
    scaleValue: b.scaleValue || "", scaleLine1Fr: b.scaleLine1Fr || "", scaleLine2Fr: b.scaleLine2Fr || "",
    piecesFr: b.piecesFr || "", packCount: Number(b.packCount || 0), boxSubFr: b.boxSubFr || "", trust: b.trust !== false,
  } : null;
}
const onTextsToggle = (e) => { if (e.target.open) fillTexts(); };
watch(() => d.value?.name, () => { tx.value = null; });
async function setRetext() {
  const x = tx.value;
  if (!x) return;
  const texts = { ...x, benefitsFr: x.benefits.split("\n").map((l) => l.trim()).filter(Boolean).slice(0, 5) };
  delete texts.benefits;
  if (await setCall("retext", { texts: JSON.stringify(texts) })) success(t("souk.ss.redrawn"));
}
// The floor photo a set shot is judged against: its colour's front.
function refFor(it) {
  const ph = d.value?.photos || [];
  const main = d.value?.colors?.[0]?.code || "";
  const col = it.color || main;
  const pick = ph.find((p) => (p.color || "") === col && p.slot === "front") || ph.find((p) => p.slot === "front") || ph[0];
  return pick ? pick.url : "";
}
const openSet = (it) => { big.value = { url: it.url, src: refFor(it), label: t("souk.ss.shot_" + it.shot), kind: "set" }; };

// The finals as shown: a local copy, so a drag re-orders live and the server
// hears ONE final_set when the drag ends (the arrows: one call after a short
// pause, however many taps).
const order = ref([]);
const dragFrom = ref(null);
const dragMoved = ref(false);
const hoverZone = ref(null);
const orderSaving = ref(false);
let nudgeTimer = null;

watch(() => d.value?.finals, (f) => {
  if (dragFrom.value == null) order.value = (f || []).map((x) => ({ ...x }));
}, { immediate: true });

const colorName = (c) => (c.code ? (locale.value === "ar" ? c.ar || c.fr : c.fr || c.code) : t("souk.theProduct"));
const colorOf = (code) => colorName(d.value.colors.find((c) => c.code === code) || { code, fr: code });
const rawOf = (code) => (d.value?.photos || []).filter((p) => (p.color || "") === code);
const sizes = computed(() => [...new Set((d.value?.variants || []).map((v) => v.size).filter(Boolean))]);
const weights = computed(() => {
  const seen = {};
  for (const v of d.value?.variants || []) if (v.grams) seen[v.size || "—"] = v.grams;
  const keys = Object.keys(seen);
  if (!keys.length) return "";
  return keys.map((k) => (k === "—" ? "" : k + " ") + (seen[k] >= 1000 ? (seen[k] / 1000).toFixed(2) + " kg" : seen[k] + " g")).join(" · ");
});
// Per colour: has it a final yet? (the send button waits for every one)
const coverage = computed(() => {
  const cols = (d.value?.colors || []).filter((c) => c.code);
  if (cols.length < 2) return [{ code: "", label: t("souk.finals"), n: order.value.length, ok: order.value.length > 0 }];
  return cols.map((c) => {
    const n = order.value.filter((f) => f.color === c.code).length;
    return { code: c.code, label: colorName(c), n, ok: n > 0 };
  });
});
const realColorCount = computed(() => (d.value?.colors || []).filter((c) => c.code).length || 1);
// Days in the queue: whole days, "today" under one.
const ageText = (a) => (Number(a) < 1 ? t("souk.pub.today") : t("souk.ageDays").replace("{n}", Math.floor(Number(a))));
// A phone shows the queue OR the product; the route decides which.
const listOnly = computed(() => !route.params.name);
const zipUrl = computed(() => "/api/method/logistics_portal.api.souk.raw_zip?name=" + encodeURIComponent(d.value?.name || ""));

// Upload targets: one per real colour + "all colours"; a single-colour
// product has just the one tile.
const zones = computed(() => {
  const cols = (d.value?.colors || []).filter((c) => c.code);
  if (cols.length < 2) return [{ code: "", label: t("souk.uploadFinals"), count: order.value.length, missing: false }];
  const without = new Set(d.value.colorsWithout || []);
  return [
    ...cols.map((c) => ({ code: c.code, label: colorName(c), count: order.value.filter((f) => f.color === c.code).length,
      missing: without.has(c.code) })),
    { code: "", label: t("souk.pub.dropAllColors"), count: order.value.filter((f) => !f.color).length, missing: false },
  ];
});

// Time in the step against its limit (settings.stageDays.studio).
const dur = (h) => {
  const a = Math.abs(h);
  return a < 48 ? t("souk.pub.hours").replace("{n}", Math.round(a)) : t("souk.pub.days").replace("{n}", Math.round(a / 24));
};
const clock = computed(() => {
  const det = d.value;
  if (!det) return null;
  const lim = Number(data.value?.limit) || 0;
  if (det.hoursLeft == null || !lim) {
    return det.age != null ? { late: false, text: t("souk.pub.inStep").replace("{a}", t("souk.pub.days").replace("{n}", det.age)) } : null;
  }
  const late = det.hoursLeft < 0;
  return {
    late,
    pct: Math.max(4, Math.min(100, Math.round(((lim * 24 - det.hoursLeft) / (lim * 24)) * 100))),
    text: t("souk.pub.ofLimit").replace("{a}", dur(lim * 24 - det.hoursLeft)).replace("{l}", t("souk.pub.days").replace("{n}", lim))
      + " · " + (late ? t("souk.pub.lateBy").replace("{n}", dur(det.hoursLeft)) : t("souk.pub.left").replace("{n}", dur(det.hoursLeft))),
  };
});

async function load() {
  loading.value = true;
  clearTimeout(nudgeTimer);
  try {
    const next = await api("souk.studio_boot", route.params.name ? { name: route.params.name } : {});
    if (next?.detail?.name !== d.value?.name) {
      returning.value = false;
      reason.value = "";
    }
    data.value = next;
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    loading.value = false;
  }
}

function setDetail(det) {
  data.value = { ...data.value, detail: det };
}

async function upload(files, code) {
  const imgs = files.filter((f) => /^image\//.test(f.type || ""));
  if (imgs.length < files.length) warn(t("souk.failed"), t("souk.pub.onlyImages"));
  if (!imgs.length) return;
  uploadingCode.value = code;
  for (let i = 0; i < imgs.length; i++) {
    uploading.value = imgs.length - i;
    try {
      setDetail(await postPhoto("final_add", { name: d.value.name, color: code }, imgs[i], { max: 2048, quality: 0.9 }));
    } catch (err) {
      warn(t("souk.failed"), String(err.message || err));
      break;
    }
  }
  uploading.value = 0;
  uploadingCode.value = null;
}
function onFiles(e, code) {
  const files = [...(e.target.files || [])];
  e.target.value = "";
  upload(files, code);
}
const isFileDrag = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
function onZoneOver(e, code) {
  if (!isFileDrag(e) || uploading.value) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = "copy";
  hoverZone.value = code;
}
function onZoneDrop(e, code) {
  hoverZone.value = null;
  if (!isFileDrag(e)) return;
  e.preventDefault();
  if (!d.value?.canEdit || uploading.value) return;
  upload([...(e.dataTransfer.files || [])], code);
}

function onSectionOver(e) {
  if (isFileDrag(e)) e.preventDefault();
}
function onSectionDrop(e) {
  if (!isFileDrag(e) || e.defaultPrevented) return;
  e.preventDefault();
  if (d.value?.canEdit && !uploading.value) upload([...(e.dataTransfer.files || [])], "");
}

// --- order -------------------------------------------------------------------
const sameOrder = () => {
  const a = (d.value?.finals || []).map((f) => f.url + "|" + (f.color || "")).join(",");
  const b = order.value.map((f) => f.url + "|" + (f.color || "")).join(",");
  return a === b;
};

async function save(list) {
  busy.value = true;
  orderSaving.value = true;
  try {
    setDetail(await apiPost("souk.final_set", {
      name: d.value.name, finals: JSON.stringify(list.map((f) => ({ url: f.url, color: f.color || "" }))),
    }));
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load();
  } finally {
    busy.value = false;
    orderSaving.value = false;
  }
}
function setColor(i, code) {
  clearTimeout(nudgeTimer);
  order.value = order.value.map((f, j) => (j === i ? { ...f, color: code } : f));
  save(order.value);
}
function nudge(i, step) {
  const j = i + step;
  if (j < 0 || j >= order.value.length) return;
  const list = [...order.value];
  [list[i], list[j]] = [list[j], list[i]];
  order.value = list;
  clearTimeout(nudgeTimer);
  nudgeTimer = setTimeout(() => { if (!sameOrder()) save(order.value); }, 700);
}

function onDragStart(e, i) {
  if (!d.value?.canEdit || busy.value) return e.preventDefault();
  dragFrom.value = i;
  dragMoved.value = false;
  e.dataTransfer.effectAllowed = "move";
  // Firefox starts a drag only with some data on it.
  try { e.dataTransfer.setData("text/plain", order.value[i].url); } catch (_) { /* older engines */ }
}
function onDragOver(e, i) {
  if (dragFrom.value == null) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = "move";
  if (i === dragFrom.value) return;
  const list = [...order.value];
  const [x] = list.splice(dragFrom.value, 1);
  list.splice(i, 0, x);
  order.value = list;
  dragFrom.value = i;
  dragMoved.value = true;
}
function onDropCard(e) {
  if (dragFrom.value != null) e.preventDefault();
}
function onDragEnd() {
  const moved = dragMoved.value;
  dragFrom.value = null;
  dragMoved.value = false;
  if (moved && !sameOrder()) save(order.value);
  else order.value = (d.value?.finals || []).map((x) => ({ ...x }));
}

async function removeFinal(url) {
  if (!window.confirm(t("souk.pub.removeConfirm"))) return;
  clearTimeout(nudgeTimer);
  busy.value = true;
  try {
    // A pending arrow re-order goes first: final_set wants the same photos.
    if (!sameOrder()) {
      setDetail(await apiPost("souk.final_set", {
        name: d.value.name, finals: JSON.stringify(order.value.map((f) => ({ url: f.url, color: f.color || "" }))),
      }));
    }
    await apiPost("souk.photo_remove", { name: d.value.name, url, which: "final" });
    await load();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load();
  } finally {
    busy.value = false;
  }
}

async function go() {
  if (route.params.name) await router.push({ name: "SoukStudio" });
  else await load();
}

async function send() {
  clearTimeout(nudgeTimer);
  if (!sameOrder()) await save(order.value);
  busy.value = true;
  try {
    const r = await apiPost("souk.studio_send", { name: d.value.name });
    success(t("souk.sentToContent").replace("{n}", r.media));
    await go();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
    await load();
  } finally {
    busy.value = false;
  }
}

async function sendBack() {
  busy.value = true;
  try {
    await apiPost("souk.studio_return", { name: d.value.name, reason: reason.value });
    success(t("souk.sentBack"));
    await go();
  } catch (e) {
    warn(t("souk.failed"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

watch(() => route.params.name, load);
const onKey = (e) => { if (e.key === "Escape") big.value = null; };
onMounted(() => { load(); window.addEventListener("keydown", onKey); });
onBeforeUnmount(() => { clearTimeout(nudgeTimer); clearTimeout(pollTimer); window.removeEventListener("keydown", onKey); });
</script>

<style scoped>
.chip-meta {
  display: inline-flex; align-items: center; gap: 0.25rem;
  font-size: 12px; font-weight: 600; color: rgb(68 64 60);
  background: rgb(255 255 255 / 0.75); border-radius: 999px; padding: 2px 9px;
  box-shadow: inset 0 0 0 1px rgb(0 0 0 / 0.06);
}
.qsel { box-shadow: inset 3px 0 0 rgb(var(--st)); }
[dir="rtl"] .qsel { box-shadow: inset -3px 0 0 rgb(var(--st)); }
:global(html[data-theme="dark"] .chip-meta) { background: rgb(41 37 36 / 0.8); color: rgb(231 229 228); }
/* Drag is for a mouse; a finger gets the arrows (and the hint says so). */
.souk-grab { cursor: grab; }
.souk-coarse { display: none; }
.souk-fine { display: inline-flex; }
@media (pointer: coarse) {
  .souk-grab { cursor: default; }
  .souk-coarse { display: inline; }
  .souk-fine { display: none; }
}
</style>
