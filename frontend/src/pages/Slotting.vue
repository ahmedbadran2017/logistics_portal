<template>
  <div class="max-w-5xl mx-auto px-4 py-6 space-y-4">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('slotting.title') }}</h1>
        <p class="text-[13px] text-stone-500 mt-1 max-w-2xl">{{ t('slotting.intro') }}</p>
      </div>
      <select v-model.number="days" @change="load"
              class="h-9 rounded-lg ring-1 ring-stone-200 bg-white text-[12.5px] font-medium text-stone-700 px-2">
        <option :value="30">30 {{ t('slotting.days') }}</option>
        <option :value="90">90 {{ t('slotting.days') }}</option>
        <option :value="180">180 {{ t('slotting.days') }}</option>
      </select>
    </header>

    <div v-if="loading" class="text-center text-[13px] text-stone-400 py-16">{{ t('common.loading') }}…</div>

    <template v-else-if="ov">
      <!-- scorecard -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('slotting.aMovers') }}</div>
          <div class="text-[22px] font-bold text-emerald-600 tabular-nums mt-1">{{ ov.scorecard.aMovers }}</div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ t('slotting.aMoversSub').replace('{p}', aShare) }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-rose-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('slotting.scatter') }}</div>
          <div class="text-[22px] font-bold text-rose-600 tabular-nums mt-1">{{ ov.scorecard.aZones }} <span class="text-[13px] text-stone-400 font-medium">/ {{ ov.zonesTotal }}</span></div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ t('slotting.scatterSub') }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-amber-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('slotting.cold') }}</div>
          <div class="text-[22px] font-bold text-amber-600 tabular-nums mt-1">{{ ov.scorecard.coldItems }}</div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ t('slotting.coldSub').replace('{s}', ov.scorecard.coldShelves).replace('{u}', ov.scorecard.coldUnits) }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('slotting.pickPath') }}</div>
          <div class="text-[22px] font-bold text-stone-900 tabular-nums mt-1">{{ ov.scorecard.pickPathZones }}</div>
          <div class="text-[11.5px] text-stone-500 mt-0.5">{{ t('slotting.pickPathSub') }}</div>
        </div>
      </div>

      <!-- class summary -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="text-[12px] font-semibold text-stone-700 mb-3">{{ t('slotting.classTitle') }}</div>
        <div class="space-y-2.5">
          <div v-for="c in ov.classes" :key="c.cls" class="flex items-center gap-3">
            <span class="w-6 h-6 rounded-md flex items-center justify-center text-[12px] font-bold text-white flex-shrink-0"
                  :class="clsColor(c.cls)">{{ c.cls }}</span>
            <div class="flex-1 min-w-0">
              <div class="h-2.5 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full transition-all" :class="clsColor(c.cls)" :style="{ width: c.pickShare + '%' }" />
              </div>
            </div>
            <div class="text-[12px] tabular-nums text-stone-600 w-[150px] text-right flex-shrink-0">
              <b class="text-stone-900">{{ c.skus }}</b> {{ t('slotting.skus') }} · <b class="text-stone-900">{{ c.pickShare }}%</b> {{ t('slotting.ofPicks') }}
            </div>
          </div>
        </div>
      </div>

      <!-- zone heat table -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-700">{{ t('slotting.zoneTitle') }}</div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[640px] text-[13px]">
            <thead>
              <tr class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('slotting.zone') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('slotting.shelves') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('slotting.skus') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('slotting.picks') }}</th>
                <th class="text-start px-4 py-2.5 w-[34%]">{{ t('slotting.mix') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="z in ov.zones" :key="z.zone" class="hover:bg-stone-50">
                <td class="px-4 py-2.5 font-bold text-stone-900">{{ z.zone }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-stone-600">{{ z.shelves }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-stone-600">{{ z.skus }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums font-semibold text-stone-900">{{ z.picks }}</td>
                <td class="px-4 py-2.5">
                  <div class="flex h-3 rounded-full overflow-hidden ring-1 ring-stone-200/60 bg-stone-50" :title="`A ${z.A} · B ${z.B} · C ${z.C} · cold ${z.cold}`">
                    <div class="bg-emerald-500" :style="{ width: pctOf(z.A, z) + '%' }" />
                    <div class="bg-sky-400" :style="{ width: pctOf(z.B, z) + '%' }" />
                    <div class="bg-stone-400" :style="{ width: pctOf(z.C, z) + '%' }" />
                    <div class="bg-amber-300" :style="{ width: pctOf(z.cold, z) + '%' }" />
                  </div>
                  <div class="text-[10.5px] text-stone-400 mt-1 tabular-nums">A {{ z.A }} · B {{ z.B }} · C {{ z.C }} · <span class="text-amber-600">{{ t('slotting.coldShort') }} {{ z.cold }}</span></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Phase 2: the target layout the floor re-arranges to match -->
      <div v-if="plan" class="bg-white rounded-xl ring-1 ring-[var(--accent-200,#f5d0b0)] overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
          <Icon name="layout-grid" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('slotting.planTitle') }}</span>
          <span class="text-[11px] text-stone-400 hidden sm:inline">{{ t('slotting.planHint') }}</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4">
          <div v-for="z in plan.zones" :key="z.cls" class="rounded-xl ring-1 ring-stone-200/70 p-3">
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-md text-white text-[12px] font-bold flex items-center justify-center" :class="clsColor(z.cls)">{{ z.cls }}</span>
              <span class="text-[15px] font-bold text-stone-900 tracking-wide">{{ z.letters.join(' + ') }}</span>
              <span class="text-[11px] text-stone-400 ms-auto tabular-nums">{{ z.bins }} {{ t('slotting.shelves') }}</span>
            </div>
            <div class="text-[11.5px] text-stone-500 mt-1.5">{{ t('slotting.role' + z.cls) }}</div>
            <template v-if="compOf(z.cls)">
              <div class="mt-2 h-1.5 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full rounded-full" :class="clsColor(z.cls)"
                     :style="{ width: compPct(z.cls) + '%' }" />
              </div>
              <div class="text-[11px] text-stone-500 mt-1 tabular-nums">
                {{ t('slotting.inPlace').replace('{a}', compOf(z.cls).inPlace).replace('{b}', compOf(z.cls).inPlace + compOf(z.cls).toMove).replace('{p}', compPct(z.cls)) }}
              </div>
            </template>
          </div>
        </div>
        <div class="px-4 pb-3 text-[11.5px] text-stone-400">{{ t('slotting.planReserved') }}</div>
      </div>

      <!-- Phase 2: the move worklist -->
      <div v-if="plan" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="route" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('slotting.moveTitle') }}</span>
          <div class="inline-flex rounded-lg ring-1 ring-stone-200 overflow-hidden text-[12px] font-semibold">
            <button v-for="c in ['A','B','C']" :key="c"
                    class="h-8 px-3 transition-colors" :class="moveCls === c ? 'bg-stone-900 text-white' : 'bg-white text-stone-600 hover:bg-stone-50'"
                    @click="setMoveCls(c)">{{ c }}</button>
          </div>
          <span class="text-[11.5px] text-stone-400 tabular-nums">{{ moveTotal }} {{ t('slotting.toMoveN') }}</span>
        </div>
        <div v-if="moveLoading" class="p-4 space-y-2">
          <span v-for="n in 4" :key="n" class="block h-11 rounded-lg bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
        </div>
        <ul v-else-if="moveRows.length" class="divide-y divide-stone-100 max-h-[440px] overflow-y-auto">
          <li v-for="it in moveRows" :key="it.itemCode" class="p-3 flex items-center gap-3">
            <img v-if="it.image" :src="it.image" alt="" @error="hideImg"
                 class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
            <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="16" /></span>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-semibold text-stone-900 truncate">{{ it.name }}</div>
              <div class="font-mono text-[11.5px] text-stone-500 truncate">{{ it.sku || it.itemCode }} · {{ it.qty }}u · {{ it.picks }} {{ t('slotting.picksShort') }}</div>
            </div>
            <span class="text-[12px] font-semibold text-stone-700 tabular-nums whitespace-nowrap">
              {{ it.from }} <Icon name="chevron-right" :size="12" class="inline flip-rtl text-stone-400" />
              <b class="text-[var(--accent-700)]">{{ it.target }}</b>
            </span>
            <button class="h-8 px-3 rounded-lg text-[12px] font-semibold text-[var(--accent-700)] bg-[var(--accent-50)] ring-1 ring-[var(--accent-200,#f5d0b0)] hover:bg-[var(--accent-100,#fde8d7)] flex-shrink-0"
                    @click="goMove(it)">{{ t('slotting.moveBtn') }}</button>
          </li>
        </ul>
        <div v-else class="text-center text-[12.5px] text-emerald-600 py-8">{{ t('slotting.moveDone') }}</div>
      </div>

      <!-- The fastest SKUs with no picking face at all -->
      <div v-if="noFace" class="bg-white rounded-xl ring-1 ring-rose-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="alert-triangle" :size="14" class="text-rose-600" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('slotting.nfTitle') }}</span>
          <span class="text-[11.5px] text-stone-400 tabular-nums">{{ noFace.total }} SKU</span>
          <div class="ms-auto flex items-center gap-1">
            <button v-for="c in ['A', 'B', 'C']" :key="c" @click="setNfCls(c)"
                    class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold transition-colors"
                    :class="nfCls === c ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100'">{{ c }}</button>
          </div>
        </div>
        <div class="px-4 py-2 bg-rose-50/50 text-[11.5px] text-stone-600 flex flex-wrap gap-x-3 gap-y-1 tabular-nums">
          <span class="text-emerald-700 font-semibold">{{ noFace.sourced }} {{ t('slotting.nfReady') }}</span>
          <span class="text-amber-700 font-semibold">{{ noFace.elsewhere }} {{ t('slotting.nfElsewhere') }}</span>
          <span class="text-rose-700 font-semibold">{{ noFace.noStock }} {{ t('slotting.nfNoStock') }}</span>
        </div>
        <ul v-if="noFace.rows.length" class="divide-y divide-stone-100 max-h-[440px] overflow-y-auto">
          <li v-for="it in noFace.rows" :key="it.itemCode" class="p-3 flex items-center gap-3">
            <img v-if="it.image" :src="it.image" alt="" @error="hideImg"
                 class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
            <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="16" /></span>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-semibold text-stone-900 truncate">{{ it.name }}</div>
              <div class="font-mono text-[11.5px] text-stone-500 truncate">{{ it.sku || it.itemCode }} · {{ it.picks }} {{ t('slotting.picksShort') }}</div>
            </div>
            <span v-if="it.state === 'ready'" class="text-[12px] font-semibold text-stone-700 tabular-nums whitespace-nowrap">
              {{ it.source }} ({{ it.available }}u) <Icon name="chevron-right" :size="12" class="inline flip-rtl text-stone-400" />
              <b class="text-[var(--accent-700)]">{{ it.target }}</b>
            </span>
            <span v-else class="text-[11.5px] font-semibold whitespace-nowrap"
                  :class="it.state === 'elsewhere' ? 'text-amber-600' : 'text-rose-600'">
              {{ it.state === 'elsewhere' ? t('slotting.nfElsewhere') : t('slotting.nfNoStock') }}
            </span>
            <button v-if="it.state === 'ready'"
                    class="h-8 px-3 rounded-lg text-[12px] font-semibold text-[var(--accent-700)] bg-[var(--accent-50)] ring-1 ring-[var(--accent-200,#f5d0b0)] hover:bg-[var(--accent-100,#fde8d7)] flex-shrink-0"
                    @click="goFace(it)">{{ t('slotting.moveBtn') }}</button>
          </li>
        </ul>
        <div v-else class="text-center text-[12.5px] text-emerald-600 py-8">{{ t('slotting.nfDone') }}</div>
      </div>

      <!-- Clear the zone before filling it -->
      <div v-if="evac" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="arrow-right" :size="14" class="text-amber-600" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('slotting.evTitle').replace('{z}', (evac.letters || []).join('+')) }}</span>
          <span class="text-[11.5px] text-stone-400 tabular-nums">{{ evac.total }} SKU · {{ evac.unitsToClear.toLocaleString() }}u</span>
          <div class="ms-auto flex items-center gap-1">
            <button v-for="c in ['A', 'B', 'C']" :key="c" @click="setEvCls(c)"
                    class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold transition-colors"
                    :class="evCls === c ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100'">{{ c }}</button>
          </div>
        </div>
        <div class="px-4 py-2 text-[11.5px] text-stone-500">{{ t('slotting.evHint').replace('{n}', String(evac.coldRows)) }}</div>
        <ul v-if="evac.rows.length" class="divide-y divide-stone-100 max-h-[440px] overflow-y-auto">
          <li v-for="it in evac.rows" :key="it.itemCode" class="p-3 flex items-center gap-3">
            <img v-if="it.image" :src="it.image" alt="" @error="hideImg"
                 class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
            <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="16" /></span>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-semibold text-stone-900 truncate">{{ it.name }}</div>
              <div class="font-mono text-[11.5px] text-stone-500 truncate">
                {{ it.sku || it.itemCode }} · {{ it.qty }}u
                <span v-if="it.cold" class="text-amber-600 font-semibold">· {{ t('slotting.evCold') }}</span>
                <span v-else>· {{ t('slotting.cls') }} {{ it.cls }}</span>
              </div>
            </div>
            <span class="text-[12px] font-semibold text-stone-700 tabular-nums whitespace-nowrap">
              {{ it.from }} <Icon name="chevron-right" :size="12" class="inline flip-rtl text-stone-400" />
              <b class="text-[var(--accent-700)]">{{ it.target }}</b>
            </span>
            <button class="h-8 px-3 rounded-lg text-[12px] font-semibold text-[var(--accent-700)] bg-[var(--accent-50)] ring-1 ring-[var(--accent-200,#f5d0b0)] hover:bg-[var(--accent-100,#fde8d7)] flex-shrink-0"
                    @click="goEvac(it)">{{ t('slotting.moveBtn') }}</button>
          </li>
        </ul>
        <div v-else class="text-center text-[12.5px] text-emerald-600 py-8">{{ t('slotting.evDone') }}</div>
      </div>

      <!-- Phase 2: excess on the fast faces -> SLOW ZONE -->
      <div v-if="over" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="boxes" :size="14" class="text-amber-600" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('slotting.overTitle') }}</span>
          <span class="text-[11.5px] text-stone-400 tabular-nums">{{ over.total }} SKU · {{ over.unitsExcess.toLocaleString() }} {{ t('slotting.overUnits') }}</span>
          <span class="text-[11px] text-stone-400 hidden sm:inline ms-auto">{{ t('slotting.overHint') }}</span>
        </div>
        <ul v-if="over.rows.length" class="divide-y divide-stone-100 max-h-[440px] overflow-y-auto">
          <li v-for="it in over.rows" :key="it.itemCode" class="p-3 flex items-center gap-3">
            <img v-if="it.image" :src="it.image" alt="" @error="hideImg"
                 class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
            <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="16" /></span>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-semibold text-stone-900 truncate">{{ it.name }}</div>
              <div class="font-mono text-[11.5px] text-stone-500 truncate">
                {{ it.sku || it.itemCode }} · {{ it.from }} · {{ t('slotting.overKeep').replace('{k}', it.keep).replace('{q}', it.qty) }}
                <span v-if="it.cold" class="text-amber-600 font-sans font-semibold">· {{ t('slotting.coldShort') }}</span>
              </div>
            </div>
            <span class="text-[13px] font-bold text-amber-700 tabular-nums whitespace-nowrap">{{ it.excess }}u <Icon name="chevron-right" :size="12" class="inline flip-rtl text-stone-400" /> SLOW</span>
            <button class="h-8 px-3 rounded-lg text-[12px] font-semibold text-amber-700 bg-amber-50 ring-1 ring-amber-200 hover:bg-amber-100 flex-shrink-0"
                    @click="goSlow(it)">{{ t('slotting.moveBtn') }}</button>
          </li>
        </ul>
        <div v-else class="text-center text-[12.5px] text-emerald-600 py-8">{{ t('slotting.overDone') }}</div>
      </div>

      <!-- movers drill-down -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <div class="inline-flex rounded-lg ring-1 ring-stone-200 overflow-hidden text-[12px] font-semibold">
            <button v-for="c in ['A','B','C']" :key="c"
                    class="h-8 px-3 transition-colors" :class="cls === c ? 'bg-stone-900 text-white' : 'bg-white text-stone-600 hover:bg-stone-50'"
                    @click="setCls(c)">{{ c }}</button>
          </div>
          <span class="text-[11.5px] text-stone-400 tabular-nums">{{ moversTotal }} {{ t('slotting.skus') }}</span>
          <div class="relative ms-auto">
            <span class="absolute inset-y-0 left-2.5 flex items-center text-stone-400"><Icon name="search" :size="14" /></span>
            <input v-model="q" @input="runSearch" :placeholder="t('slotting.searchPh')"
                   class="h-9 w-[200px] max-w-full ps-8 pe-3 rounded-lg ring-1 ring-stone-200 bg-white text-[12.5px] outline-none focus:ring-2 focus:ring-[var(--accent-400)]" />
          </div>
        </div>
        <div v-if="moversLoading" class="p-4 space-y-2">
          <span v-for="n in 5" :key="n" class="block h-11 rounded-lg bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
        </div>
        <ul v-else class="divide-y divide-stone-100 max-h-[520px] overflow-y-auto">
          <li v-for="it in movers" :key="it.itemCode"
              class="p-3 flex items-center gap-3 hover:bg-stone-50 cursor-pointer" @click="openSku(it.sku)">
            <img v-if="it.image" :src="it.image" alt="" @error="hideImg"
                 class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
            <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center flex-shrink-0 text-stone-400"><Icon name="package" :size="16" /></span>
            <div class="min-w-0 flex-1">
              <div class="text-[13px] font-semibold text-stone-900 truncate">{{ it.name }}</div>
              <div class="font-mono text-[11.5px] text-stone-500 truncate">{{ it.sku || it.itemCode }}</div>
            </div>
            <span class="text-[11.5px] font-semibold rounded-md px-2 py-0.5 ring-1 flex-shrink-0"
                  :class="it.placed ? 'text-stone-700 bg-stone-50 ring-stone-200' : 'text-rose-700 bg-rose-50 ring-rose-200/70'">
              {{ it.placed ? it.shelf : t('slotting.noStock') }}
            </span>
            <span class="text-[12px] font-bold text-stone-900 tabular-nums flex-shrink-0 w-14 text-right">{{ it.picks }} <span class="text-[10px] text-stone-400 font-medium">{{ t('slotting.picksShort') }}</span></span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const router = useRouter();

const days = ref(90);
const ov = ref(null);
const loading = ref(true);

const plan = ref(null);
const over = ref(null);
const moveCls = ref("A");
const noFace = ref(null);
const nfCls = ref("A");
const evac = ref(null);
const evCls = ref("A");
const moveRows = ref([]);
const moveTotal = ref(0);
const moveLoading = ref(false);

const cls = ref("A");
const movers = ref([]);
const moversTotal = ref(0);
const moversLoading = ref(false);
const q = ref("");
let searchTimer = null;

const aShare = computed(() => {
  const a = (ov.value?.classes || []).find((c) => c.cls === "A");
  return a ? a.pickShare : 0;
});

function clsColor(c) {
  return c === "A" ? "bg-emerald-500" : c === "B" ? "bg-sky-400" : "bg-stone-400";
}
function pctOf(n, z) {
  const tot = (z.A + z.B + z.C + z.cold) || 1;
  return (100 * n / tot).toFixed(1);
}

async function load() {
  loading.value = true;
  try {
    ov.value = await api("slotting.overview", { days: days.value });
  } catch (e) {
    ov.value = null;
  } finally {
    loading.value = false;
  }
  loadMovers();
  loadPlan();
  loadOver();
  loadNoFace();
  loadEvac();
}

// The two halves the plan was missing: what has no face at all, and what has
// to leave a zone before its own class can move in.
async function loadNoFace() {
  try {
    noFace.value = await api("slotting.no_face_list", { cls: nfCls.value, days: days.value });
  } catch (e) {
    noFace.value = null;
  }
}
function setNfCls(c) { nfCls.value = c; loadNoFace(); }

async function loadEvac() {
  try {
    evac.value = await api("slotting.evacuate_list", { cls: evCls.value, days: days.value });
  } catch (e) {
    evac.value = null;
  }
}
function setEvCls(c) { evCls.value = c; loadEvac(); }

function compOf(c) {
  return (plan.value?.compliance || []).find((x) => x.cls === c) || null;
}
function compPct(c) {
  const m = compOf(c);
  const tot = m ? m.inPlace + m.toMove : 0;
  return tot ? Math.round((100 * m.inPlace) / tot) : 0;
}

async function loadPlan() {
  try {
    plan.value = await api("slotting.target_plan", { days: days.value });
  } catch (e) {
    plan.value = null;
  }
  loadMoves();
}

async function loadOver() {
  try {
    over.value = await api("slotting.overstock_list", { days: days.value });
  } catch (e) {
    over.value = null;
  }
}

async function loadMoves() {
  moveLoading.value = true;
  try {
    const res = await api("slotting.move_list", { cls: moveCls.value, days: days.value });
    moveRows.value = res?.rows || [];
    moveTotal.value = res?.total || 0;
  } catch (e) {
    moveRows.value = [];
    moveTotal.value = 0;
  } finally {
    moveLoading.value = false;
  }
}

function setMoveCls(c) { moveCls.value = c; loadMoves(); }
function goMove(it) {
  router.push({ name: "MoveStock", query: { item: it.itemCode, target: it.target } });
}
function goFace(it) {
  // Pull from where the stock actually is, into the class's own letters.
  router.push({ name: "MoveStock",
                query: { item: it.itemCode, from: it.source, target: it.target } });
}
function goEvac(it) {
  router.push({ name: "MoveStock",
                query: { item: it.itemCode, from: it.from, target: it.target, qty: it.qty } });
}
function goSlow(it) {
  router.push({ name: "MoveStock", query: { item: it.itemCode, target: "SLOW ZONE - JM", qty: it.excess } });
}

async function loadMovers() {
  moversLoading.value = true;
  try {
    const res = await api("slotting.movers", { cls: cls.value, q: q.value.trim(), days: days.value });
    movers.value = res?.rows || [];
    moversTotal.value = res?.total || 0;
  } catch (e) {
    movers.value = [];
    moversTotal.value = 0;
  } finally {
    moversLoading.value = false;
  }
}

function setCls(c) { cls.value = c; loadMovers(); }
function runSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(loadMovers, 250); }
function openSku(sku) { if (sku) router.push({ name: "SkuLookup", query: { q: sku } }); }
function hideImg(e) { e.target.style.display = "none"; }

onMounted(load);
</script>
