<template>
  <!-- The souk's settings, from the app instead of code/Desk. Backend:
       souk.settings_boot (GET) / souk.save_settings (POST, only the keys that
       changed — a publish that remembered its channels meanwhile is not
       overwritten). The manager edits everything; the accountant only the
       accounts. The server validates every rule again; the checks here only
       say it before the round trip. -->
  <div class="max-w-[760px] mx-auto px-4 pt-3 lg:pt-6 space-y-4" :class="dirty ? 'pb-44 lg:pb-32' : 'pb-10'">
    <header>
      <h1 class="text-[17px] lg:text-[20px] font-bold text-stone-900 leading-tight">{{ t('souk.set.title') }}</h1>
      <p class="text-[11.5px] lg:text-[12.5px] text-stone-500 mt-0.5">
        {{ boot && !boot.isManager ? t('souk.set.subAcct') : t('souk.set.sub') }}
      </p>
    </header>

    <div v-if="loading && !boot" class="space-y-3" aria-busy="true">
      <div class="souk-skel h-[150px] rounded-xl" />
      <div class="souk-skel h-[240px] rounded-xl" />
    </div>

    <div v-else-if="loadErr && !boot" class="lp-card p-5 text-center space-y-3" role="alert">
      <Icon name="alert-circle" :size="22" class="mx-auto text-rose-500" />
      <p class="text-[13px] font-semibold text-stone-900">{{ t('souk.set.loadFail') }}</p>
      <p class="text-[11.5px] text-stone-500 break-words">{{ loadErr }}</p>
      <button type="button" class="h-11 px-5 rounded-lg ring-1 ring-stone-300 bg-white text-[13px] font-semibold text-stone-700"
              @click="load">{{ t('souk.set.retry') }}</button>
    </div>

    <template v-else-if="boot">
      <p v-if="!boot.isManager"
         class="rounded-xl bg-stone-100 px-3.5 py-2.5 text-[12px] text-stone-700 flex items-start gap-2">
        <Icon name="info" :size="14" class="mt-[2px] shrink-0 text-stone-500" />{{ t('souk.set.acctOnly') }}
      </p>

      <!-- jump row: the page is long on a phone -->
      <nav v-if="boot.isManager" class="-mx-4 px-4 flex gap-1.5 overflow-x-auto" :aria-label="t('souk.set.title')">
        <button v-for="j in JUMPS" :key="j" type="button"
                class="shrink-0 h-9 px-3 rounded-full bg-white ring-1 ring-stone-200 text-[12px] font-semibold text-stone-600 hover:text-stone-900 inline-flex items-center gap-1.5"
                @click="jump(j)">
          {{ t('souk.set.jump.' + j) }}
          <span v-if="sectionDirty(j)" class="w-1.5 h-1.5 rounded-full bg-[var(--accent-600)]" />
        </button>
      </nav>

      <!-- ── SKU ─────────────────────────────────────────────────────── -->
      <section v-if="boot.isManager" id="set-sku" class="lp-card p-4 space-y-3 scroll-mt-3">
        <SecHead icon="tag" :title="t('souk.set.sku.title')" :hint="t('souk.set.sku.hint')" />
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="ss-prefix" class="block text-[12px] font-semibold text-stone-700 mb-1">{{ t('souk.set.sku.prefix') }}</label>
            <input id="ss-prefix" :value="form.skuPrefix" dir="ltr" autocomplete="off" autocapitalize="characters" spellcheck="false"
                   maxlength="4" :class="[inp, 'mono uppercase tracking-wide', errs.prefix ? bad : '']"
                   @input="onPrefix" />
            <p class="text-[11px] text-stone-500 mt-1">{{ t('souk.set.sku.prefixHint') }}</p>
          </div>
          <div>
            <label for="ss-start" class="block text-[12px] font-semibold text-stone-700 mb-1">{{ t('souk.set.sku.start') }}</label>
            <input id="ss-start" v-model.number="form.skuStart" type="number" inputmode="numeric" min="1" dir="ltr"
                   :class="[inp, 'tabular-nums', errs.start ? bad : '']" />
            <p class="text-[11px] text-stone-500 mt-1">{{ t('souk.set.sku.startHint') }}</p>
          </div>
        </div>
        <div class="rounded-lg bg-stone-50 ring-1 ring-stone-200/70 p-3 space-y-2">
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-[11.5px] text-stone-500">{{ t('souk.set.sku.next') }}</span>
            <span class="mono text-[15px] font-bold text-stone-900 whitespace-nowrap" dir="ltr">{{ preview.sku }}</span>
          </div>
          <div class="flex items-baseline justify-between gap-3">
            <span class="text-[11.5px] text-stone-500 min-w-0">
              {{ t('souk.set.sku.longest') }}
              <span class="block text-[10.5px] text-stone-400">{{ t('souk.set.sku.longestHint') }}</span>
            </span>
            <span class="mono text-[13px] font-semibold whitespace-nowrap shrink-0" :class="preview.over ? 'text-rose-700' : 'text-stone-800'" dir="ltr">{{ preview.longest }}</span>
          </div>
          <div class="h-1.5 rounded-full bg-stone-200 overflow-hidden" role="meter" :aria-valuenow="preview.len" aria-valuemin="0" :aria-valuemax="boot.skuMax">
            <div class="h-full rounded-full" :class="preview.over ? 'bg-rose-600' : 'bg-emerald-600'"
                 :style="{ width: Math.min(100, (preview.len / boot.skuMax) * 100) + '%' }" />
          </div>
          <div class="flex items-center justify-between gap-2 text-[11px] tabular-nums">
            <span :class="preview.over ? 'text-rose-700 font-semibold' : 'text-stone-500'">{{ tt('souk.set.sku.len', { n: preview.len, max: boot.skuMax }) }}</span>
          </div>
          <p v-if="preview.over" class="text-[11.5px] font-semibold text-rose-700">{{ t('souk.set.sku.tooLong') }}</p>
          <p v-else-if="form.skuPrefix !== orig.skuPrefix && !errs.prefix" class="text-[11px] text-stone-500">{{ t('souk.set.sku.newPrefix') }}</p>
        </div>
      </section>

      <!-- ── categories ─────────────────────────────────────────────── -->
      <section v-if="boot.isManager" id="set-cats" class="lp-card p-4 space-y-3 scroll-mt-3">
        <SecHead icon="layers" :title="t('souk.set.cats.title')" :hint="t('souk.set.cats.hint')" />
        <datalist id="ss-brands"><option v-for="b in brandNames" :key="b" :value="b" /></datalist>
        <datalist id="ss-types"><option v-for="p in productTypes" :key="p" :value="p" /></datalist>
        <div v-for="(c, i) in form.categories" :key="c._id"
             class="rounded-xl ring-1 p-3 space-y-2.5"
             :class="pending === c._id ? 'ring-amber-300 bg-amber-50/50' : errs.cats[i] ? 'ring-rose-300' : 'ring-stone-200'">
          <div class="flex items-center gap-2 min-h-[44px]">
            <template v-if="c._new">
              <label :for="'ss-ck-' + c._id" class="sr-only">{{ t('souk.set.cats.key') }}</label>
              <input :id="'ss-ck-' + c._id" :value="c.key" dir="ltr" autocomplete="off" autocapitalize="none" spellcheck="false"
                     maxlength="30" :placeholder="t('souk.set.cats.key')"
                     :class="[inp, 'mono !w-40 lowercase', errs.cats[i] === 'key' ? bad : '']" @input="onKey(c, $event)" />
              <span class="text-[10.5px] text-stone-400 leading-tight hidden sm:block">{{ t('souk.set.cats.keyHint') }}</span>
            </template>
            <span v-else class="mono text-[12px] font-semibold text-stone-700 bg-stone-100 rounded-md px-2 py-1" dir="ltr">{{ c.key }}</span>
            <span v-if="usedCat(c)" class="text-[11px] text-stone-500 tabular-nums">· {{ tt('souk.set.used', { n: usedCat(c) }) }}</span>
            <button type="button" class="ms-auto shrink-0 w-11 h-11 -me-1.5 rounded-lg inline-flex items-center justify-center text-stone-400 hover:text-rose-600 hover:bg-rose-50"
                    :aria-label="t('souk.set.remove') + ' ' + (c.fr || c.key)" @click="askRemove('categories', c, usedCat(c))">
              <Icon name="trash-2" :size="17" />
            </button>
          </div>
          <div class="grid grid-cols-2 lg:grid-cols-4 gap-2">
            <div>
              <label :for="'ss-car-' + c._id" class="block text-[11.5px] font-semibold text-stone-700 mb-1">{{ t('souk.set.cats.ar') }}</label>
              <input :id="'ss-car-' + c._id" v-model="c.ar" dir="rtl" lang="ar" autocomplete="off" :class="[inp, !c.ar.trim() && errs.cats[i] === 'fields' ? bad : '']" />
            </div>
            <div>
              <label :for="'ss-cfr-' + c._id" class="block text-[11.5px] font-semibold text-stone-700 mb-1">{{ t('souk.set.cats.fr') }}</label>
              <input :id="'ss-cfr-' + c._id" :value="c.fr" dir="ltr" lang="fr" autocomplete="off" :class="[inp, !c.fr.trim() && errs.cats[i] === 'fields' ? bad : '']"
                     @input="onCatFr(c, $event)" />
            </div>
            <div>
              <label :for="'ss-cty-' + c._id" class="block text-[11.5px] font-semibold text-stone-700 mb-1">{{ t('souk.set.cats.type') }}</label>
              <input :id="'ss-cty-' + c._id" v-model="c.productType" dir="ltr" list="ss-types" autocomplete="off"
                     :class="[inp, !c.productType.trim() && errs.cats[i] === 'fields' ? bad : '']" />
            </div>
            <div>
              <label :for="'ss-cbr-' + c._id" class="block text-[11.5px] font-semibold text-stone-700 mb-1">{{ t('souk.set.cats.brand') }}</label>
              <input :id="'ss-cbr-' + c._id" v-model="c.brand" dir="ltr" list="ss-brands" autocomplete="off"
                     :class="[inp, !c.brand.trim() && errs.cats[i] === 'fields' ? bad : '']" />
            </div>
          </div>
          <p v-if="c.brand.trim() && !brandKnown(c.brand)" class="text-[11px] font-medium text-amber-800 flex items-start gap-1.5">
            <Icon name="alert-triangle" :size="12" class="mt-[2px] shrink-0" />{{ t('souk.set.cats.newBrand') }}
          </p>
          <RemoveWarn v-if="pending === c._id" :n="usedCat(c)" :name="c.fr || c.key"
                      @yes="remove('categories', c)" @no="pending = null" />
        </div>
        <button type="button" class="w-full h-11 rounded-lg border border-dashed border-stone-300 text-[13px] font-semibold text-[var(--accent-700)] inline-flex items-center justify-center gap-1.5 hover:bg-stone-50"
                @click="addCat">
          <Icon name="plus" :size="15" />{{ t('souk.set.cats.add') }}
        </button>
      </section>

      <!-- ── colours ────────────────────────────────────────────────── -->
      <section v-if="boot.isManager" id="set-colors" class="lp-card p-4 space-y-3 scroll-mt-3">
        <SecHead icon="sparkles" :title="t('souk.set.colors.title')" :hint="t('souk.set.colors.hint')" />
        <div class="space-y-1.5">
          <div class="grid grid-cols-[60px_1fr_1fr_40px] gap-1.5 text-[11px] font-semibold text-stone-500 px-0.5" aria-hidden="true">
            <span>{{ t('souk.set.colors.code') }}</span><span>{{ t('souk.set.colors.fr') }}</span><span>{{ t('souk.set.colors.ar') }}</span><span />
          </div>
          <template v-for="(c, i) in form.colors" :key="c._id">
            <div class="grid grid-cols-[60px_1fr_1fr_40px] gap-1.5 items-start rounded-lg"
                 :class="pending === c._id ? 'bg-amber-50 ring-1 ring-amber-300 p-1 -m-1' : ''">
              <div>
                <input v-if="c._new" :value="c.code" dir="ltr" maxlength="3" autocapitalize="characters" autocomplete="off" spellcheck="false"
                       :aria-label="t('souk.set.colors.code')"
                       :class="[inp, 'mono uppercase !px-2 text-center', errs.colors[i] === 'code' ? bad : '']" @input="onCode(c, $event)" />
                <div v-else class="h-11 rounded-lg bg-stone-100 mono text-[13px] font-bold text-stone-800 flex items-center justify-center" dir="ltr">{{ c.code }}</div>
                <div v-if="usedColor(c)" class="text-[10px] text-stone-500 text-center mt-0.5 tabular-nums">{{ tt('souk.set.used', { n: usedColor(c) }) }}</div>
              </div>
              <input v-model="c.fr" dir="ltr" lang="fr" autocomplete="off" :aria-label="t('souk.set.colors.fr') + ' ' + c.code"
                     :class="[inp, '!px-2', !c.fr.trim() && errs.colors[i] === 'names' ? bad : '']" />
              <input v-model="c.ar" dir="rtl" lang="ar" autocomplete="off" :aria-label="t('souk.set.colors.ar') + ' ' + c.code"
                     :class="[inp, '!px-2', !c.ar.trim() && errs.colors[i] === 'names' ? bad : '']" />
              <button type="button" class="w-10 h-11 rounded-lg inline-flex items-center justify-center text-stone-400 hover:text-rose-600 hover:bg-rose-50"
                      :aria-label="t('souk.set.remove') + ' ' + (c.code || c.fr)" @click="askRemove('colors', c, usedColor(c))">
                <Icon name="trash-2" :size="16" />
              </button>
            </div>
            <RemoveWarn v-if="pending === c._id" :n="usedColor(c)" :name="c.fr || c.code"
                        @yes="remove('colors', c)" @no="pending = null" />
          </template>
        </div>
        <button type="button" class="w-full h-11 rounded-lg ring-1 ring-stone-300 text-[13px] font-semibold text-[var(--accent-700)] inline-flex items-center justify-center gap-1.5 hover:bg-stone-50"
                @click="addColor">
          <Icon name="plus" :size="15" />{{ t('souk.set.colors.add') }}
        </button>
      </section>

      <!-- ── deadlines ──────────────────────────────────────────────── -->
      <section v-if="boot.isManager" id="set-days" class="lp-card p-4 space-y-1 scroll-mt-3">
        <SecHead icon="clock" :title="t('souk.set.days.title')" :hint="t('souk.set.days.hint')" class="mb-2" />
        <div class="divide-y divide-stone-100">
          <NumRow v-for="k in stages" :key="k" v-model="form.stageDays[k]" :id="'ss-d-' + k"
                  :label="t('souk.set.days.' + k)" :unit="t('souk.set.days.unit')" :min="1" :max="30" :bad="!!errs.days[k]" />
        </div>
        <div class="border-t border-stone-200 pt-1 divide-y divide-stone-100">
          <NumRow v-model="form.escalateDays" id="ss-esc" :label="t('souk.set.days.escalate')" :hint="t('souk.set.days.escalateHint')"
                  :unit="t('souk.set.days.unit')" :min="1" :max="90" :bad="!!errs.days.escalate" />
          <NumRow v-model="form.launchDays" id="ss-launch" :label="t('souk.set.days.launch')" :hint="t('souk.set.days.launchHint')"
                  :unit="t('souk.set.days.unit')" :min="1" :max="60" :bad="!!errs.days.launch" />
        </div>
      </section>

      <!-- ── receiving ──────────────────────────────────────────────── -->
      <section v-if="boot.isManager" id="set-receiving" class="lp-card p-4 space-y-1 scroll-mt-3">
        <SecHead icon="package-check" :title="t('souk.set.receiving.title')" />
        <NumRow v-model="form.studioSamples" id="ss-samples" :label="t('souk.set.receiving.samples')"
                :hint="t('souk.set.receiving.samplesHint')" :unit="t('souk.set.receiving.unit')" :min="0" :max="10"
                :bad="!!errs.days.samples" />
      </section>

      <!-- ── publishing ─────────────────────────────────────────────── -->
      <section v-if="boot.isManager" id="set-publish" class="lp-card p-4 space-y-3 scroll-mt-3">
        <SecHead icon="send" :title="t('souk.set.publish.title')" :hint="t('souk.set.publish.hint')" />
        <div v-if="boot.channelsError" class="rounded-lg bg-amber-50 ring-1 ring-amber-200 p-3 space-y-1">
          <p class="text-[12px] font-semibold text-amber-900 flex items-start gap-1.5">
            <Icon name="alert-triangle" :size="13" class="mt-[2px] shrink-0" />{{ t('souk.set.publish.unreachable') }}
          </p>
          <p class="text-[11px] text-amber-800 break-words" dir="ltr">{{ boot.channelsError }}</p>
          <p class="text-[11.5px] text-amber-900 tabular-nums">{{ tt('souk.set.publish.current', { n: form.publishChannels.length }) }}</p>
        </div>
        <div v-else class="space-y-1.5">
          <label v-for="ch in channelRows" :key="ch.id"
                 class="flex items-center gap-3 min-h-[48px] px-3 rounded-lg ring-1 cursor-pointer"
                 :class="form.publishChannels.includes(ch.id) ? 'ring-[var(--accent-600)] bg-[var(--accent-50)]' : 'ring-stone-200 bg-white'">
            <input type="checkbox" class="w-5 h-5 shrink-0" style="accent-color: var(--accent-600)"
                   :checked="form.publishChannels.includes(ch.id)" @change="toggleChannel(ch.id)" />
            <span class="flex-1 min-w-0">
              <span class="block text-[13.5px] font-semibold text-stone-900 truncate">{{ ch.name }}</span>
              <span v-if="ch.unknown" class="block text-[11px] text-amber-800">{{ t('souk.set.publish.unknown') }}</span>
            </span>
          </label>
          <p v-if="!form.publishChannels.length" class="text-[11.5px] text-stone-500 flex items-start gap-1.5 pt-1">
            <Icon name="info" :size="13" class="mt-[2px] shrink-0" />{{ t('souk.set.publish.none') }}
          </p>
        </div>
      </section>

      <!-- ── accounts ───────────────────────────────────────────────── -->
      <section id="set-accounts" class="lp-card p-4 space-y-4 scroll-mt-3">
        <SecHead icon="wallet" :title="t('souk.set.acct.title')" :hint="t('souk.set.acct.hint')" />
        <div v-for="a in ACCTS" :key="a.key">
          <div :id="'ss-al-' + a.key" class="block text-[12px] font-semibold text-stone-700 mb-1">{{ t(a.label) }}</div>
          <button type="button" :aria-expanded="openAcct === a.key" :aria-labelledby="'ss-al-' + a.key + ' ss-av-' + a.key"
                  class="w-full h-11 rounded-lg bg-white ring-1 px-3 flex items-center gap-2 text-start"
                  :class="openAcct === a.key ? 'ring-2 ring-[var(--accent-500)]' : 'ring-stone-300'"
                  @click="toggleAcct(a.key)">
            <span :id="'ss-av-' + a.key" class="flex-1 min-w-0 truncate text-[14px]" :class="form[a.key] ? 'text-stone-900' : 'text-stone-400'"
                  dir="auto">{{ form[a.key] || t('souk.set.acct.none') }}</span>
            <Icon name="chevron-down" :size="16" class="shrink-0 text-stone-400 transition-transform" :class="openAcct === a.key ? 'rotate-180' : ''" />
          </button>
          <div v-if="openAcct === a.key" class="mt-1.5 rounded-lg ring-1 ring-stone-200 bg-white overflow-hidden">
            <div class="p-2 border-b border-stone-100">
              <!-- account names are Latin: the box reads left to right in every language -->
              <div class="relative" dir="ltr">
                <input ref="acctSearch" v-model="acctQ" type="search" autocomplete="off" :placeholder="t('souk.set.acct.search')"
                       :class="[inp, '!ps-9']" @keydown.esc="openAcct = null" />
                <Icon name="search" :size="15" class="absolute top-1/2 -translate-y-1/2 start-3 text-stone-400 pointer-events-none" />
              </div>
            </div>
            <ul class="max-h-[264px] overflow-y-auto overscroll-contain py-1" role="listbox" :aria-labelledby="'ss-al-' + a.key">
              <li role="option" :aria-selected="!form[a.key]">
                <button type="button" class="w-full min-h-[44px] px-3 text-start text-[13px] text-stone-500 hover:bg-stone-50 flex items-center gap-2"
                        @click="pickAcct(a.key, '')">
                  <span class="flex-1">{{ t('souk.set.acct.none') }}</span>
                  <Icon v-if="!form[a.key]" name="check" :size="15" class="text-[var(--accent-600)]" />
                </button>
              </li>
              <li v-for="name in acctMatches(a.list).rows" :key="name" role="option" :aria-selected="form[a.key] === name">
                <button type="button" class="w-full min-h-[44px] px-3 text-start text-[13px] hover:bg-stone-50 flex items-center gap-2"
                        :class="form[a.key] === name ? 'text-[var(--accent-700)] font-semibold' : 'text-stone-800'"
                        @click="pickAcct(a.key, name)">
                  <span class="flex-1 min-w-0 break-words" dir="ltr">{{ name }}</span>
                  <Icon v-if="form[a.key] === name" name="check" :size="15" class="shrink-0 text-[var(--accent-600)]" />
                </button>
              </li>
              <li v-if="!acctMatches(a.list).rows.length" class="px-3 py-3 text-[12px] text-stone-500">{{ t('souk.set.acct.noMatch') }}</li>
              <li v-else-if="acctMatches(a.list).more" class="px-3 py-2 text-[11px] text-stone-400">{{ tt('souk.set.acct.more', { n: acctMatches(a.list).more }) }}</li>
            </ul>
          </div>
          <p v-if="form[a.key] && !(boot.accounts[a.list] || []).includes(form[a.key])" class="text-[11px] font-medium text-amber-800 mt-1">
            {{ t('souk.set.acct.notListed') }}
          </p>
          <p class="text-[11px] text-stone-500 mt-1">{{ t(a.hint) }}</p>
        </div>
      </section>

      <!-- ── last changes ───────────────────────────────────────────── -->
      <section id="set-log" class="lp-card p-4 scroll-mt-3">
        <SecHead icon="history" :title="t('souk.set.log.title')" />
        <p v-if="!boot.log?.length" class="text-[12px] text-stone-500 mt-2">{{ t('souk.set.log.empty') }}</p>
        <ul v-else class="mt-1 divide-y divide-stone-100">
          <li v-for="(e, i) in boot.log" :key="i" class="py-2.5 flex items-start gap-3">
            <span class="mt-1.5 w-1.5 h-1.5 rounded-full bg-stone-300 shrink-0" />
            <div class="min-w-0">
              <div class="text-[12.5px] text-stone-800">
                <span class="font-semibold">{{ e.byName || e.by }}</span> {{ tt('souk.set.log.changed', { what: keysText(e.keys) }) }}
              </div>
              <div class="text-[11px] text-stone-500 tabular-nums" dir="ltr">{{ when(e.at) }}</div>
            </div>
          </li>
        </ul>
      </section>
    </template>

    <!-- ── sticky save bar ─────────────────────────────────────────── -->
    <footer v-if="dirty" class="lp-footer px-4 pt-3 pb-3">
      <div class="max-w-[760px] mx-auto space-y-2">
        <p v-if="saveErr" class="text-[12px] font-semibold text-rose-700 flex items-start gap-1.5" role="alert">
          <Icon name="alert-circle" :size="14" class="mt-[1px] shrink-0" /><span class="break-words min-w-0">{{ saveErr }}</span>
        </p>
        <p v-else-if="problem" class="text-[11.5px] font-semibold text-amber-800 flex items-start gap-1.5" aria-live="polite">
          <Icon name="info" :size="13" class="mt-[2px] shrink-0" />{{ problem }}
        </p>
        <div class="flex items-center gap-2">
          <span class="flex-1 min-w-0 text-[12px] text-stone-600 leading-tight">{{ tt('souk.set.bar.n', { n: changed.length }) }}</span>
          <button type="button" class="shrink-0 h-11 px-4 rounded-xl ring-1 ring-stone-300 bg-white text-[13.5px] font-semibold text-stone-700 disabled:opacity-40"
                  :disabled="saving" @click="discard">{{ t('souk.set.bar.discard') }}</button>
          <button type="button" class="shrink-0 h-11 px-5 rounded-xl bg-[var(--accent-600)] hover:bg-[var(--accent-700)] text-white text-[14px] font-bold disabled:opacity-40"
                  :disabled="saving || !!problem" @click="save">
            {{ saving ? t('souk.set.bar.saving') : t('souk.set.bar.save') }}
          </button>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, defineComponent, h, watch } from "vue";
import { onBeforeRouteLeave } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { local } from "@/lib/clock";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t, locale } = useI18n();
const toast = useToast();
const tt = (k, vars = {}) => {
  let s = String(t(k));
  for (const [a, b] of Object.entries(vars)) s = s.split("{" + a + "}").join(String(b ?? ""));
  return s;
};

const inp = "w-full h-11 rounded-lg bg-white ring-1 ring-stone-300 px-3 text-[14px] text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-[var(--accent-500)]";
const bad = "!ring-rose-400 !ring-2";

const JUMPS = ["sku", "cats", "colors", "days", "receiving", "publish", "accounts", "log"];
const ACCOUNT_KEYS = ["custodyAccount", "transportLossAccount", "warehouseLossAccount"];
const ACCTS = [
  { key: "custodyAccount", list: "cash", label: "souk.set.acct.custody", hint: "souk.set.acct.custodyHint" },
  { key: "transportLossAccount", list: "expense", label: "souk.set.acct.transport", hint: "souk.set.acct.transportHint" },
  { key: "warehouseLossAccount", list: "expense", label: "souk.set.acct.warehouse", hint: "souk.set.acct.warehouseHint" },
];
const SECTION_KEYS = {
  sku: ["skuPrefix", "skuStart"], cats: ["categories"], colors: ["colors"],
  days: ["stageDays", "escalateDays", "launchDays"], receiving: ["studioSamples"],
  publish: ["publishChannels"], accounts: ACCOUNT_KEYS, log: [],
};

// ── small pieces ────────────────────────────────────────────────────────
const SecHead = defineComponent({
  props: { icon: String, title: String, hint: String },
  setup(p) {
    return () => h("div", [
      h("h2", { class: "text-[13.5px] font-bold text-stone-900 flex items-center gap-2" }, [
        h(Icon, { name: p.icon, size: 15, class: "text-stone-400" }), p.title,
      ]),
      p.hint ? h("p", { class: "text-[11.5px] text-stone-500 mt-1 leading-relaxed" }, p.hint) : null,
    ]);
  },
});

// A label on one side, a −/+ stepper on the other: a thumb, not a tiny box.
const NumRow = defineComponent({
  props: { modelValue: [Number, String], id: String, label: String, hint: String, unit: String,
    min: Number, max: Number, bad: Boolean },
  emits: ["update:modelValue"],
  setup(p, { emit }) {
    const val = () => (p.modelValue === "" || p.modelValue == null ? null : Number(p.modelValue));
    const set = (n) => emit("update:modelValue", Math.max(p.min, Math.min(p.max, n)));
    const btn = "w-11 h-11 rounded-lg bg-white ring-1 ring-stone-300 text-[20px] font-bold text-stone-700 inline-flex items-center justify-center active:bg-stone-100 disabled:opacity-30";
    return () => h("div", { class: "flex items-center gap-3 py-2.5" }, [
      h("div", { class: "flex-1 min-w-0" }, [
        h("label", { for: p.id, class: "block text-[13px] font-semibold text-stone-800" }, p.label),
        p.hint ? h("p", { class: "text-[11px] text-stone-500 mt-0.5 leading-snug" }, p.hint) : null,
      ]),
      h("div", { class: "flex items-center gap-1 shrink-0", dir: "ltr" }, [
        h("button", { type: "button", class: btn, "aria-label": "−", tabindex: -1,
          disabled: val() != null && val() <= p.min, onClick: () => set((val() ?? p.min + 1) - 1) }, "−"),
        h("input", {
          id: p.id, type: "number", inputmode: "numeric", min: p.min, max: p.max, value: p.modelValue ?? "",
          class: "w-14 h-11 rounded-lg bg-white ring-1 text-center text-[15px] font-bold tabular-nums focus:outline-none focus:ring-2 "
            + (p.bad ? "ring-rose-400 ring-2" : "ring-stone-300"),
          onInput: (e) => {
            const raw = e.target.value;
            emit("update:modelValue", raw === "" ? "" : Number(raw));
          },
        }),
        h("button", { type: "button", class: btn, "aria-label": "+", tabindex: -1,
          disabled: val() != null && val() >= p.max, onClick: () => set((val() ?? p.min - 1) + 1) }, "+"),
      ]),
      h("span", { class: "w-9 text-[11px] text-stone-500 shrink-0" }, p.unit),
    ]);
  },
});

const RemoveWarn = defineComponent({
  props: { n: Number, name: String },
  emits: ["yes", "no"],
  setup(p, { emit }) {
    return () => h("div", { class: "rounded-lg bg-amber-50 ring-1 ring-amber-200 p-3 space-y-2", role: "alert" }, [
      h("p", { class: "text-[12px] text-amber-900 leading-relaxed" }, tt("souk.set.removeWarn", { n: p.n, name: p.name })),
      h("div", { class: "flex gap-2" }, [
        h("button", { type: "button", class: "h-10 px-3.5 rounded-lg bg-rose-600 text-white text-[12.5px] font-bold", onClick: () => emit("yes") },
          t("souk.set.removeAnyway")),
        h("button", { type: "button", class: "h-10 px-3.5 rounded-lg ring-1 ring-stone-300 bg-white text-[12.5px] font-semibold text-stone-700", onClick: () => emit("no") },
          t("souk.set.keep")),
      ]),
    ]);
  },
});

// ── state ───────────────────────────────────────────────────────────────
const boot = ref(null);
const loading = ref(false);
const loadErr = ref("");
const saving = ref(false);
const saveErr = ref("");
const orig = ref({});
const form = reactive({});
const pending = ref(null);      // the row whose removal waits for "remove anyway"
let uid = 0;

function toForm(s) {
  const out = JSON.parse(JSON.stringify(s || {}));
  if (Array.isArray(out.categories)) {
    out.categories = out.categories.map((c) => ({
      key: c.key || "", ar: c.ar || "", fr: c.fr || "", productType: c.productType || "", brand: c.brand || "", _id: ++uid,
    }));
  }
  if (Array.isArray(out.colors)) out.colors = out.colors.map((c) => ({ code: c.code || "", fr: c.fr || "", ar: c.ar || "", _id: ++uid }));
  if (out.stageDays && typeof out.stageDays === "object") out.stageDays = { ...out.stageDays };
  if ("publishChannels" in out && !Array.isArray(out.publishChannels)) out.publishChannels = [];
  for (const k of ACCOUNT_KEYS) if (k in out) out[k] = out[k] || "";
  return out;
}

function reset() {
  const f = toForm(boot.value.settings);
  for (const k of Object.keys(form)) delete form[k];
  Object.assign(form, f);
  orig.value = toForm(boot.value.settings);
  pending.value = null;
  saveErr.value = "";
}

async function load() {
  loading.value = true;
  loadErr.value = "";
  try {
    boot.value = await api("souk.settings_boot");
    reset();
  } catch (e) {
    loadErr.value = e.message || String(e);
  } finally {
    loading.value = false;
  }
}

// ── comparison: only keys that really changed are sent ──────────────────
function norm(k, v) {
  if (k === "categories") return (v || []).map(({ key, ar, fr, productType, brand }) => ({ key, ar, fr, productType, brand }));
  if (k === "colors") return (v || []).map(({ code, fr, ar }) => ({ code, fr, ar }));
  if (k === "publishChannels") return [...(v || [])].sort();
  if (k === "stageDays") return Object.fromEntries(Object.keys(v || {}).sort().map((s) => [s, v[s]]));
  return v;
}
const changed = computed(() => Object.keys(form).filter(
  (k) => JSON.stringify(norm(k, form[k])) !== JSON.stringify(norm(k, orig.value[k]))));
const dirty = computed(() => changed.value.length > 0);
const sectionDirty = (j) => (SECTION_KEYS[j] || []).some((k) => changed.value.includes(k));

watch(() => JSON.stringify(form), () => { saveErr.value = ""; });

// ── SKU ─────────────────────────────────────────────────────────────────
function onPrefix(e) {
  const v = String(e.target.value || "").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 4);
  form.skuPrefix = v;
  if (e.target.value !== v) e.target.value = v;
}
function skuFor(prefix, start, used) {
  const n = Math.max(used, (Number(start) || 1) - 1) + 1;
  const sku = `${prefix}${n}`;
  const longest = `${sku}-RED-2XL`;
  return { sku, longest, len: longest.length };
}
const preview = computed(() => {
  if (!boot.value?.isManager) return { sku: "", longest: "", len: 0, over: false };
  const same = form.skuPrefix === orig.value.skuPrefix;
  const p = skuFor(form.skuPrefix || "", form.skuStart, same ? Number(boot.value.skuUsed) || 0 : 0);
  const now = skuFor(orig.value.skuPrefix || "", orig.value.skuStart, Number(boot.value.skuUsed) || 0);
  const touched = form.skuPrefix !== orig.value.skuPrefix || Number(form.skuStart) !== Number(orig.value.skuStart);
  const over = p.len > boot.value.skuMax;
  // Same rule as the server: refuse only a change that makes it longer still.
  return { ...p, over, blocks: touched && over && p.len > now.len };
});

// ── categories & colours ────────────────────────────────────────────────
const usage = computed(() => boot.value?.usage || { colors: {}, categories: {} });
const usedCat = (c) => (c._new ? 0 : Number(usage.value.categories?.[c.key]) || 0);
const usedColor = (c) => (c._new ? 0 : Number(usage.value.colors?.[c.code]) || 0);
const brandNames = computed(() => {
  const set = new Set((boot.value?.brands || []).map((b) => b.name));
  for (const c of orig.value.categories || []) if (c.brand) set.add(c.brand);
  return [...set].sort((a, b) => a.localeCompare(b));
});
const brandKnown = (b) => brandNames.value.some((x) => x.toLowerCase() === String(b).trim().toLowerCase());
const productTypes = computed(() => [...new Set((form.categories || []).map((c) => c.productType.trim()).filter(Boolean))]);

const slug = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
  .replace(/&/g, " ").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 30);

function onKey(c, e) {
  c.key = String(e.target.value || "").toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 30);
  if (e.target.value !== c.key) e.target.value = c.key;
  c._autoKey = false;
}
function onCatFr(c, e) {
  c.fr = e.target.value;
  if (c._new && c._autoKey !== false) c.key = slug(c.fr);
}
function onCode(c, e) {
  c.code = String(e.target.value || "").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 3);
  if (e.target.value !== c.code) e.target.value = c.code;
}

async function focusLast(prefix) {
  await nextTick();
  const rows = document.querySelectorAll(`[id^="${prefix}"]`);
  const el = rows[rows.length - 1];
  if (el) { el.focus(); el.scrollIntoView({ block: "center", behavior: "smooth" }); }
}
function addCat() {
  form.categories.push({ key: "", ar: "", fr: "", productType: "", brand: "", _id: ++uid, _new: true });
  focusLast("ss-car-");
}
function addColor() {
  form.colors.push({ code: "", fr: "", ar: "", _id: ++uid, _new: true });
  nextTick(() => {
    const ins = document.querySelectorAll('#set-colors input[maxlength="3"]');
    const el = ins[ins.length - 1];
    if (el) { el.focus(); el.scrollIntoView({ block: "center", behavior: "smooth" }); }
  });
}
function askRemove(list, row, n) {
  if (n > 0) { pending.value = row._id; return; }
  remove(list, row);
}
function remove(list, row) {
  form[list] = form[list].filter((r) => r._id !== row._id);
  pending.value = null;
}

// ── publishing ──────────────────────────────────────────────────────────
const channelRows = computed(() => {
  const known = boot.value?.channels || [];
  const ids = new Set(known.map((c) => c.id));
  const extra = (form.publishChannels || []).filter((id) => !ids.has(id))
    .map((id) => ({ id, name: id.split("/").pop(), unknown: true }));
  return [...known, ...extra];
});
function toggleChannel(id) {
  const on = new Set(form.publishChannels);
  if (on.has(id)) on.delete(id); else on.add(id);
  form.publishChannels = channelRows.value.map((c) => c.id).filter((x) => on.has(x));
}

// ── accounts ────────────────────────────────────────────────────────────
const openAcct = ref(null);
const acctQ = ref("");
const acctSearch = ref(null);
const ACCT_SHOW = 120;
function toggleAcct(key) {
  openAcct.value = openAcct.value === key ? null : key;
  acctQ.value = "";
  // A phone opens the keyboard on focus and hides the list: focus on desktop only.
  if (openAcct.value && window.matchMedia("(pointer: fine)").matches) {
    nextTick(() => { const el = [].concat(acctSearch.value || [])[0]; if (el) el.focus(); });
  }
}
function acctMatches(list) {
  const all = boot.value?.accounts?.[list] || [];
  const words = acctQ.value.toLowerCase().split(/\s+/).filter(Boolean);
  const hit = words.length ? all.filter((n) => { const l = n.toLowerCase(); return words.every((w) => l.includes(w)); }) : all;
  return { rows: hit.slice(0, ACCT_SHOW), more: Math.max(0, hit.length - ACCT_SHOW) };
}
function pickAcct(key, name) {
  form[key] = name;
  openAcct.value = null;
}

// ── checks (the server repeats every one) ───────────────────────────────
const stages = computed(() => boot.value?.stages || ["bought", "photos", "studio", "content", "review"]);
const isInt = (v, lo, hi) => v !== "" && v != null && Number.isInteger(Number(v)) && Number(v) >= lo && Number(v) <= hi;
// Per field (to paint it) and per settings key (the first message of each).
const errs = computed(() => {
  const out = { prefix: false, start: false, cats: {}, colors: {}, days: {}, byKey: {} };
  if (!boot.value?.isManager) return out;
  const say = (key, m) => { if (!out.byKey[key]) out.byKey[key] = m; };
  if (!/^[A-Z]{1,4}$/.test(form.skuPrefix || "")) { out.prefix = true; say("skuPrefix", t("souk.set.err.prefix")); }
  if (!isInt(form.skuStart, 1, 999999)) { out.start = true; say("skuStart", t("souk.set.err.start")); }
  const colors = form.colors || [];
  if (!colors.length) say("colors", t("souk.set.err.oneColor"));
  const seenC = new Set();
  colors.forEach((c, i) => {
    if (!/^[A-Z]{3}$/.test(c.code)) { out.colors[i] = "code"; say("colors", t("souk.set.err.code")); return; }
    if (seenC.has(c.code)) { out.colors[i] = "code"; say("colors", tt("souk.set.err.codeDup", { c: c.code })); return; }
    seenC.add(c.code);
    if (!c.fr.trim() || !c.ar.trim()) { out.colors[i] = "names"; say("colors", t("souk.set.err.colorNames")); }
  });
  const cats = form.categories || [];
  if (!cats.length) say("categories", t("souk.set.err.oneCat"));
  const seenK = new Set();
  cats.forEach((c, i) => {
    if (!/^[a-z0-9_-]{1,30}$/.test(c.key)) { out.cats[i] = "key"; say("categories", t("souk.set.err.key")); return; }
    if (seenK.has(c.key)) { out.cats[i] = "key"; say("categories", tt("souk.set.err.keyDup", { c: c.key })); return; }
    seenK.add(c.key);
    if (![c.ar, c.fr, c.productType, c.brand].every((x) => String(x).trim())) {
      out.cats[i] = "fields"; say("categories", t("souk.set.err.catFields"));
    }
  });
  const range = (key, field, label, v, lo, hi) => {
    if (!isInt(v, lo, hi)) { out.days[field] = true; say(key, tt("souk.set.err.range", { what: label, lo, hi })); }
  };
  for (const k of stages.value) range("stageDays", k, t("souk.set.days." + k), form.stageDays?.[k], 1, 30);
  range("escalateDays", "escalate", t("souk.set.days.escalate"), form.escalateDays, 1, 90);
  range("launchDays", "launch", t("souk.set.days.launch"), form.launchDays, 1, 60);
  range("studioSamples", "samples", t("souk.set.receiving.samples"), form.studioSamples, 0, 10);
  return out;
});
// Only a problem in something being changed blocks the save.
const problem = computed(() => {
  if (preview.value.blocks) return t("souk.set.err.tooLong");
  for (const k of changed.value) if (errs.value.byKey[k]) return errs.value.byKey[k];
  return "";
});

// ── save ────────────────────────────────────────────────────────────────
function payload() {
  const out = {};
  for (const k of changed.value) {
    const v = form[k];
    if (k === "categories") out[k] = v.map(({ key, ar, fr, productType, brand }) => ({
      key: key.trim(), ar: ar.trim(), fr: fr.trim(), productType: productType.trim(), brand: brand.trim() }));
    else if (k === "colors") out[k] = v.map(({ code, fr, ar }) => ({ code, fr: fr.trim(), ar: ar.trim() }));
    else if (k === "skuStart" || k === "escalateDays" || k === "launchDays" || k === "studioSamples") out[k] = Number(v);
    else if (k === "stageDays") out[k] = Object.fromEntries(Object.entries(v).map(([a, b]) => [a, Number(b)]));
    else out[k] = v;
  }
  return out;
}
async function save() {
  if (saving.value || problem.value) return;
  saving.value = true;
  saveErr.value = "";
  try {
    await apiPost("souk.save_settings", { settings_json: JSON.stringify(payload()) });
    toast.success(t("souk.set.bar.saved"), "");
    boot.value = await api("souk.settings_boot");
    reset();
  } catch (e) {
    saveErr.value = e.message || String(e);
  } finally {
    saving.value = false;
  }
}
function discard() { reset(); }

// ── misc ────────────────────────────────────────────────────────────────
function jump(j) {
  const el = document.getElementById("set-" + j);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}
function keysText(keys) {
  const sep = locale.value === "ar" ? "، " : ", ";
  return (keys || []).map((k) => t("souk.set.keys." + k, k)).join(sep);
}
const when = (at) => String(local(at) || "").slice(0, 16);

onBeforeRouteLeave(() => !dirty.value || window.confirm(t("souk.set.bar.leave")));
function beforeUnload(e) { if (dirty.value) { e.preventDefault(); e.returnValue = ""; } }
onMounted(() => { window.addEventListener("beforeunload", beforeUnload); load(); });
onBeforeUnmount(() => window.removeEventListener("beforeunload", beforeUnload));
</script>
