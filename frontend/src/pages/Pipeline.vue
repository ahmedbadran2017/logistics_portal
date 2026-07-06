<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1500px] mx-auto animate-fade-in">
    <!-- Title -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t("ordersPg.title") }}</h1>
        <p class="text-[13px] text-stone-500 mt-0.5 flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          {{ t("ordersPg.subtitle") }} · {{ WAREHOUSE }}
        </p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <div class="relative">
          <Icon name="search" :size="14" class="absolute top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none" style="inset-inline-start:.65rem" />
          <input
            v-model="q"
            :placeholder="t('ordersPg.searchPh')"
            class="h-9 w-[230px] max-w-full max-sm:w-[170px] ps-8 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] text-stone-900 placeholder:text-stone-400 focus:ring-2 focus:outline-none transition"
            style="--tw-ring-color: var(--accent-400)"
            @input="onSearch"
          />
          <button v-if="q" class="absolute top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600" style="inset-inline-end:.5rem"
                  @click="q=''; onSearch()">
            <Icon name="x" :size="13" />
          </button>
        </div>
        <div class="relative">
          <select
            v-model="dateRange"
            class="h-9 ps-3 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] text-stone-600 appearance-none cursor-pointer focus:outline-none"
            @change="load(activeStage, activeTrack)"
          >
            <option value="">{{ t("ordersPg.allDates") }}</option>
            <option value="today">{{ t("ordersPg.today") }}</option>
            <option value="yesterday">{{ t("ordersPg.yesterday") }}</option>
            <option value="7d">{{ t("ordersPg.last7") }}</option>
            <option value="30d">{{ t("ordersPg.last30") }}</option>
          </select>
          <Icon name="chevron-down" :size="13" class="absolute top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none" style="inset-inline-end:.6rem" />
        </div>
        <button
          v-if="activeStage === 'to_pick' && mode === 'live'"
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white transition-colors hover:brightness-110"
          style="background: var(--accent-600)"
          @click="sbModal && sbModal.open()"
        >
          <Icon name="package" :size="14" /> {{ t("pl.sbBtn") }}
        </button>
        <button
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          :class="exporting ? 'opacity-60 pointer-events-none' : ''"
          @click="exportCsv"
        >
          <Icon name="file-text" :size="14" /> {{ exporting ? t("ordersPg.exporting") : t("ordersPg.csv") }}
        </button>
        <button
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          :class="loading ? 'opacity-60 pointer-events-none' : ''"
          @click="load(activeStage, activeTrack)"
        >
          <Icon name="refresh-cw" :size="14" :class="loading ? 'animate-spin' : ''" /> {{ t("common.refresh") }}
        </button>
      </div>
    </div>

    <!-- Attention bar -->
    <div
      v-if="attentionTotal > 0"
      class="rounded-2xl ring-1 ring-rose-200/70 bg-gradient-to-r from-rose-50 via-amber-50/60 to-white p-3.5 flex items-center gap-3 flex-wrap"
    >
      <span class="w-9 h-9 rounded-xl bg-rose-500 text-white flex items-center justify-center flex-shrink-0">
        <Icon name="alert-triangle" :size="18" />
      </span>
      <div class="me-1">
        <div class="text-[13.5px] font-semibold text-stone-900 leading-tight">{{ t("ordersPg.needsHuman") }}</div>
        <div class="text-[11.5px] text-stone-500">{{ t("ordersPg.faultsNotStages") }}</div>
      </div>
      <button
        v-for="a in attentionChips" :key="a.key"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-semibold ring-1 transition-all hover:-translate-y-px"
        :class="activeStage === 'attention' ? 'bg-rose-600 text-white ring-rose-600' : 'bg-white text-stone-700 ring-stone-200 hover:ring-rose-300'"
        @click="load('attention')"
      >
        <span class="w-1.5 h-1.5 rounded-full" :style="{ background: a.hex }" />
        {{ a.label }}
        <span class="font-mono tabular-nums" :style="activeStage === 'attention' ? {} : { color: a.hex }">{{ a.count }}</span>
      </button>
    </div>

    <!-- Flow strip (skeleton on first load — never dummy numbers) -->
    <div v-if="mode === 'loading'" class="overflow-x-auto py-1 -mx-1 px-1">
      <div class="flex items-stretch gap-2 min-w-[920px]">
        <div v-for="n in 8" :key="n" class="flex-1 rounded-xl ring-1 ring-stone-200/60 bg-white/70 p-3 animate-pulse">
          <div class="flex items-center gap-2">
            <div class="w-7 h-7 rounded-lg bg-stone-100" />
            <div class="h-2.5 w-14 rounded bg-stone-100" />
          </div>
          <div class="mt-3 h-6 w-12 rounded bg-stone-100" />
          <div class="mt-2 h-2 w-20 rounded bg-stone-100" />
        </div>
      </div>
    </div>
    <div v-else class="overflow-x-auto py-1 -mx-1 px-1">
      <div class="flex items-stretch gap-1.5 min-w-[920px]">
        <template v-for="(s, i) in stages" :key="s.key">
          <button
            class="relative flex-1 min-w-[106px] text-start rounded-xl p-3 ring-1 transition-all duration-200 group overflow-hidden flex flex-col"
            :class="activeStage === s.key
              ? 'bg-white shadow-[0_8px_24px_-8px_rgba(0,0,0,0.14)] ring-2'
              : 'bg-white/60 ring-stone-200/70 hover:bg-white hover:shadow-[0_4px_16px_-6px_rgba(0,0,0,0.1)] hover:-translate-y-px'"
            :style="activeStage === s.key ? { '--tw-ring-color': s.hex } : {}"
            @click="load(s.key)"
          >
            <span class="absolute top-0 inset-x-0 h-[3px] transition-opacity"
                  :style="{ background: s.hex, opacity: activeStage === s.key ? 1 : 0 }" />
            <div class="flex items-center gap-1.5 min-w-0">
              <span class="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0"
                    :style="{ background: s.hex + '1c', color: s.hex }">
                <Icon :name="s.icon" :size="13" />
              </span>
              <span class="text-[10.5px] font-semibold uppercase tracking-[0.03em] truncate"
                    :class="activeStage === s.key ? 'text-stone-900' : 'text-stone-500'">{{ t('ordersPg.stages.' + s.key + '.label') }}</span>
            </div>
            <div class="mt-2.5 flex items-baseline gap-1.5 min-w-0 flex-wrap">
              <span class="text-[23px] leading-none font-semibold tabular-nums flex-shrink-0"
                    :class="(counts[s.key] ?? 0) > 0 ? 'text-stone-900' : 'text-stone-300'">
                {{ counts[s.key] ?? "—" }}
              </span>
              <span v-if="values[s.key]" class="text-[10.5px] font-mono font-medium text-stone-400 tabular-nums truncate">
                {{ fmtK(values[s.key]) }}
              </span>
              <span v-if="s.key === 'to_pick' && counts.to_pick_late > 0"
                    class="ms-auto flex-shrink-0 text-[10.5px] font-bold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded-md tabular-nums"
                    :title="counts.to_pick_late + ' ' + t('ordersPg.late')">
                ⏰{{ fmtK(counts.to_pick_late) }}
              </span>
            </div>
            <div class="mt-1 text-[11px] text-stone-400 leading-tight truncate"
                 :title="t('ordersPg.stages.' + s.key + '.hint')">{{ t('ordersPg.stages.' + s.key + '.hint') }}</div>
            <div class="mt-auto pt-2">
              <div class="h-[3px] rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full rounded-full transition-all duration-500"
                     :style="{ width: stageShare(s.key) + '%', background: s.hex, opacity: 0.7 }" />
              </div>
            </div>
          </button>
          <div v-if="i < stages.length - 1" class="hidden 2xl:flex items-center px-0.5 text-stone-300 flex-shrink-0">
            <Icon name="chevron-right" :size="14" class="flip-rtl" />
          </div>
        </template>
      </div>
    </div>

    <!-- City filter -->
    <div v-if="cities.length" class="flex items-center gap-2 flex-wrap">
      <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t("ordersPg.city") }}</span>
      <div class="relative">
        <select
          v-model="cityFilter"
          class="h-9 ps-3 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] text-stone-700 appearance-none cursor-pointer capitalize focus:ring-2 focus:outline-none"
          style="--tw-ring-color: var(--accent-400)"
          @change="load(activeStage, activeTrack)"
        >
          <option value="">{{ t("ordersPg.allCities") }}</option>
          <option v-for="c in cities" :key="c.city" :value="c.city">{{ c.city }} ({{ c.count }})</option>
        </select>
        <Icon name="chevron-down" :size="13" class="absolute top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none" style="inset-inline-end:.6rem" />
      </div>
      <button v-if="cityFilter" class="text-[11.5px] font-medium text-stone-400 hover:text-stone-600"
              @click="cityFilter=''; load(activeStage, activeTrack)">
        {{ t("ordersPg.clear") }}
      </button>
    </div>

    <!-- Shipped sub-segmentation -->
    <div v-if="activeStage === 'shipped'" class="flex items-center gap-2 flex-wrap">
      <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t("ordersPg.carrierStatus") }}</span>
      <button
        v-for="tchip in trackChips" :key="tchip.key"
        class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[12px] font-medium ring-1 transition-colors"
        :class="activeTrack === tchip.key
          ? 'text-white ring-transparent'
          : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'"
        :style="activeTrack === tchip.key ? { background: tchip.hex } : {}"
        @click="setTrack(tchip.key)"
      >
        {{ tchip.label }}
        <span class="font-mono tabular-nums" :style="activeTrack === tchip.key ? {} : { color: tchip.hex }">{{ tchip.count }}</span>
      </button>
    </div>

    <!-- Rows -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 shadow-[0_1px_2px_rgba(0,0,0,0.03)] overflow-hidden">
      <div v-if="loading" class="divide-y divide-stone-100">
        <div v-for="n in 6" :key="n" class="px-4 py-3.5 flex items-center gap-4">
          <div class="h-3.5 w-20 rounded bg-stone-100 animate-pulse" />
          <div class="h-3.5 w-40 rounded bg-stone-100 animate-pulse" />
          <div class="h-3.5 w-24 rounded bg-stone-100 animate-pulse ms-auto" />
        </div>
      </div>

      <div v-else-if="!rows.length" class="py-16 text-center">
        <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center mb-3"
              :style="{ background: activeMeta.hex + '1c', color: activeMeta.hex }">
          <Icon :name="activeMeta.icon" :size="22" />
        </span>
        <div class="text-[14.5px] font-semibold text-stone-900">{{ q ? t('ordersPg.noMatches') : t('ordersPg.stages.' + activeMeta.key + '.emptyTitle') }}</div>
        <div class="text-[12.5px] text-stone-500 mt-0.5">
          {{ q ? t('ordersPg.noMatchesIn').replace('{stage}', t('ordersPg.stages.' + activeMeta.key + '.label')).replace('{q}', q) : t('ordersPg.stages.' + activeMeta.key + '.emptyHint') }}
        </div>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-[13px]">
          <thead class="sticky top-0 z-10">
            <tr class="text-start border-b border-stone-100 bg-white/95 backdrop-blur-sm">
              <th v-if="selectableStage" class="w-10 px-3 py-2.5 text-center">
                <input type="checkbox" class="board-cb" :checked="allSelected" @change="toggleAll" />
              </th>
              <th class="text-start px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400">{{ t("ordersPg.thOrder") }}</th>
              <th class="text-start px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400">{{ t("ordersPg.thCustomer") }}</th>
              <th class="text-start px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400 hidden md:table-cell">{{ t("ordersPg.thChannel") }}</th>
              <th class="text-start px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400">{{ t("ordersPg.thStage") }}</th>
              <th class="text-start px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400">{{ t("ordersPg.thSla") }}</th>
              <th v-if="activeStage !== 'to_pick'" class="text-start px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400 hidden xl:table-cell">{{ t("ordersPg.thDocs") }}</th>
              <th v-if="activeStage === 'attention'" class="text-start px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400">{{ t("ordersPg.thFault") }}</th>
              <th class="text-start px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400">{{ t("ordersPg.thCity") }}</th>
              <th class="text-start px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400 hidden xl:table-cell">{{ t("ordersPg.thPicker") }}</th>
              <th class="text-start px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400 cursor-pointer select-none hover:text-stone-600" @click="toggleSort('placed')" :class="'hidden lg:table-cell'">{{ t('ordersPg.thPlaced') }} <span v-if="sortKey==='placed'">{{ sortDir==='asc' ? '↑' : '↓' }}</span></th>
              <th class="text-end px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400 cursor-pointer select-none hover:text-stone-600" @click="toggleSort('value')">{{ t('ordersPg.thValue') }} <span v-if="sortKey==='value'">{{ sortDir==='asc' ? '↑' : '↓' }}</span></th>
              <th class="text-end px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-stone-400"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr v-for="r in rows" :key="r.no" class="hover:bg-stone-50/70 transition-colors cursor-pointer group"
                :class="selected.has(r.no) ? 'bg-amber-50/50' : ''"
                :style="activeStage === 'to_pick' && missedCutoff(r)
                  ? { boxShadow: 'inset 3px 0 0 #f43f5e' } : {}"
                @click="openDrawer(r)">
              <td v-if="selectableStage" class="px-3 py-3 text-center" @click.stop>
                <input type="checkbox" class="board-cb" :checked="selected.has(r.no)" @change="toggleRow(r.no)" />
              </td>
              <td class="px-4 py-3">
                <div class="font-mono font-bold text-stone-900 flex items-center gap-1.5">
                  {{ r.no }}
                  <span v-if="activeStage === 'to_pick' && missedCutoff(r)"
                        class="text-[10.5px] font-sans font-semibold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded-md ring-1 ring-rose-200/70 whitespace-nowrap">
                    {{ t("ordersPg.missedCutoff") }}
                  </span>
                </div>

              </td>
              <td class="px-3 py-3">
                <div class="font-medium text-stone-800 truncate max-w-[200px]">{{ r.customer }}</div>
                <div v-if="r.itemsDesc" class="text-[11px] text-stone-400 truncate max-w-[200px] mt-0.5" :title="r.itemsDesc">
                  {{ r.itemsDesc }}
                </div>
                <div class="flex items-center gap-1.5 mt-0.5">
                  <span class="text-[11px] text-stone-400 tabular-nums">{{ r.items }} {{ itemsWord(r.items) }}</span>
                  <template v-if="r.phone">
                    <a :href="'tel:' + r.phone" @click.stop
                       class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-emerald-100 hover:text-emerald-700 flex items-center justify-center transition-colors"
                       :title="r.phone">
                      <Icon name="phone" :size="11" />
                    </a>
                    <a :href="waLink(r.phone)" target="_blank" @click.stop
                       class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-emerald-100 hover:text-emerald-700 flex items-center justify-center transition-colors"
                       title="WhatsApp">
                      <Icon name="message-circle" :size="11" />
                    </a>
                  </template>
                </div>
              </td>
              <td class="px-3 py-3 hidden md:table-cell">
                <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11.5px] font-medium text-stone-600 whitespace-nowrap">
                  <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :style="{ background: channelHex(channelOf(r)) }" />
                  {{ channelLabel(channelOf(r)) }}
                </span>
              </td>
              <td class="px-3 py-3">
                <span v-if="r.status" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold ring-1 ring-inset whitespace-nowrap bg-white"
                      :style="{ color: statusHex(r.status), '--tw-ring-color': statusHex(r.status) + '55' }">
                  <span class="w-1.5 h-1.5 rounded-full" :style="{ background: statusHex(r.status) }" />
                  {{ statusLabel(r.status) }}
                </span>
                <span v-else class="text-[11px] text-stone-300">—</span>
              </td>
              <td class="px-3 py-3">
                <span v-if="slaOf(r).calm"
                      class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11.5px] font-medium text-stone-500 whitespace-nowrap">
                  <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :style="{ background: slaOf(r).hex }" />
                  {{ slaOf(r).label }}
                </span>
                <span v-else class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold ring-1 ring-inset whitespace-nowrap"
                      :style="{ color: slaOf(r).hex, background: slaOf(r).hex + '10', '--tw-ring-color': slaOf(r).hex + '45' }">
                  <span class="w-1.5 h-1.5 rounded-full" :style="{ background: slaOf(r).hex }" />
                  {{ slaOf(r).label }}
                </span>
              </td>
              <td v-if="activeStage !== 'to_pick'" class="px-3 py-3 hidden xl:table-cell">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <a v-if="r.pl" :href="desk('pick-list', r.pl)" target="_blank" @click.stop
                     class="doc-chip text-violet-700 bg-violet-50 hover:bg-violet-100" style="--chip-ring:#ddd6fe">
                    <Icon name="package" :size="11" />{{ r.pl }}
                  </a>
                  <a v-if="r.awb" :href="r.labelUrl || desk('sales-order', r.no)" target="_blank" @click.stop
                     class="doc-chip text-stone-600 bg-stone-100 hover:bg-stone-200" style="--chip-ring:#e7e5e4">
                    <Icon name="tag" :size="11" />{{ r.awb }}
                  </a>
                  <a v-if="r.sh" :href="desk('shipment', r.sh)" target="_blank" @click.stop
                     class="doc-chip text-emerald-700 bg-emerald-50 hover:bg-emerald-100" style="--chip-ring:#a7f3d0">
                    <Icon name="truck" :size="11" />{{ r.sh }}
                  </a>
                  <a v-if="r.ret" :href="desk('return-shipment', r.ret)" target="_blank" @click.stop
                     class="doc-chip text-rose-700 bg-rose-50 hover:bg-rose-100" style="--chip-ring:#fecdd3">
                    <Icon name="rotate-ccw" :size="11" />{{ r.ret }}
                  </a>
                  <span v-if="activeStage === 'shipped' && r.track" class="doc-chip"
                        :style="{ color: trackHexOf(r.track), background: trackHexOf(r.track) + '14', '--chip-ring': trackHexOf(r.track) + '40' }">
                    {{ trackLabelOf(r.track) }}
                  </span>
                  <span v-if="!r.pl && !r.awb && !r.sh && !r.ret" class="text-[11px] text-stone-300">—</span>
                </div>
              </td>
              <td v-if="activeStage === 'attention'" class="px-3 py-3">
                <span class="doc-chip" :style="{ color: faultHex(r.kind), background: faultHex(r.kind) + '14', '--chip-ring': faultHex(r.kind) + '40' }">
                  {{ faultLabel(r.kind) }}
                </span>
              </td>
              <td class="px-3 py-3">
                <span v-if="r.city" class="text-[12px] text-stone-600 capitalize block truncate max-w-[150px]" :title="r.city">{{ r.city }}</span>
                <span v-else class="text-[11px] text-stone-300">—</span>
              </td>
              <td class="px-3 py-3 hidden xl:table-cell">
                <div v-if="r.picker" class="flex items-center gap-1.5">
                  <span class="w-6 h-6 rounded-full bg-stone-200/80 text-stone-600 text-[9.5px] font-bold flex items-center justify-center uppercase">
                    {{ initials(r.picker) }}
                  </span>
                  <span class="text-[12px] text-stone-600 truncate max-w-[90px]">{{ pickerShort(r.picker) }}</span>
                </div>
                <span v-else class="text-[11px] text-stone-300">—</span>
              </td>
              <td class="px-3 py-3 whitespace-nowrap hidden lg:table-cell">
                <span v-if="r.created" class="text-[12.5px] font-medium text-stone-700 tabular-nums">{{ createdFmt(r.created) }}</span>
                <span class="text-[11.5px] tabular-nums ms-1.5 font-semibold" :style="{ color: ageHex(r.ageMins) }">· {{ ageFmt(r.ageMins) }}</span>
              </td>
              <td class="px-3 py-3 text-end">
                <span class="font-semibold text-stone-900 tabular-nums">{{ fmtMAD(r.total) }}</span>
                <span class="text-[10px] text-stone-400"> MAD</span>
              </td>
              <td class="px-4 py-3 text-end">
                <component
                  :is="actionFor(r) && actionFor(r).href ? 'a' : 'button'"
                  v-if="actionFor(r)"
                  v-bind="actionFor(r).href ? { href: actionFor(r).href, target: '_blank' } : {}"
                  class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11.5px] font-semibold text-white opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity"
                  :style="{ background: activeMeta.hex }"
                  @click.stop="actionFor(r).go && actionFor(r).go(r)"
                >
                  {{ actionFor(r).label }} <Icon name="chevron-right" :size="12" class="flip-rtl" />
                </component>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="flex items-center justify-between gap-3 px-4 py-2.5 border-t border-stone-100 bg-stone-50/50 flex-wrap">
          <span class="text-[11.5px] text-stone-500 tabular-nums whitespace-nowrap">
            {{ rangeStart }}–{{ rangeEnd }} {{ t("ordersPg.of") }} {{ total }}
            <span class="text-stone-400 ms-2 tabular-nums">{{ fmtMAD(rowsTotal) }} MAD</span>
          </span>
          <div class="flex items-center gap-2">
            <select
              :value="pageSize"
              class="h-8 ps-2.5 pe-6 rounded-lg bg-white ring-1 ring-stone-200 text-[12px] text-stone-600 appearance-none cursor-pointer focus:outline-none"
              @change="setPageSize"
            >
              <option :value="20">20 {{ t("ordersPg.perPage") }}</option>
              <option :value="25">25 {{ t("ordersPg.perPage") }}</option>
              <option :value="50">50 {{ t("ordersPg.perPage") }}</option>
              <option :value="100">100 {{ t("ordersPg.perPage") }}</option>
            </select>
            <div class="flex items-center gap-0.5">
              <button class="pager-btn" :disabled="page <= 1" @click="goPage(page - 1)">
                <Icon name="chevron-left" :size="13" class="flip-rtl" />
              </button>
              <button
                v-for="p in pageWindow" :key="p"
                class="pager-btn min-w-[28px] tabular-nums"
                :class="p === page ? 'pager-active' : ''"
                :disabled="typeof p !== 'number'"
                @click="goPage(p)"
              >{{ typeof p === 'number' ? p : '…' }}</button>
              <button class="pager-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">
                <Icon name="chevron-right" :size="13" class="flip-rtl" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="text-[11px] text-stone-400 text-center">
      {{ t("ordersPg.footnote") }} {{ updatedAgo }}
    </div>

    <SuggestBatchesModal ref="sbModal" @created="load('to_pick')" />

    <!-- Quick-view drawer -->
    <transition name="qv">
      <div v-if="drawerRow" class="fixed inset-0 z-[90]">
        <div class="absolute inset-0 bg-stone-900/25 backdrop-blur-[1px]" @click="drawerRow = null" />
        <div class="absolute top-0 bottom-0 w-full max-w-[440px] bg-stone-50 shadow-[0_0_60px_-10px_rgba(0,0,0,0.35)] flex flex-col qv-panel"
             style="inset-inline-end:0">
          <!-- header -->
          <div class="bg-white border-b border-stone-200/70 px-4 py-3 flex items-center gap-3">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="font-mono text-[15px] font-bold text-stone-900">{{ drawerRow.no }}</span>
                <span v-if="drawerRow.status" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10.5px] font-semibold ring-1 ring-inset bg-white whitespace-nowrap"
                      :style="{ color: statusHex(drawerRow.status), '--tw-ring-color': statusHex(drawerRow.status) + '55' }">
                  {{ drawerRow.status }}
                </span>
              </div>
              <div class="text-[12px] text-stone-500 truncate">{{ drawerRow.customer }}<span v-if="drawerRow.city" class="capitalize"> · {{ drawerRow.city }}</span></div>
            </div>
            <button class="text-[11.5px] font-semibold whitespace-nowrap" style="color: var(--accent-700)" @click="openOrder(drawerRow)">
              {{ t("ordersPg.qvFullPage") }} →
            </button>
            <button class="w-7 h-7 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-100 flex items-center justify-center" @click="drawerRow = null">
              <Icon name="x" :size="15" />
            </button>
          </div>

          <div class="flex-1 overflow-y-auto p-4 space-y-4">
            <!-- items -->
            <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3">
              <div class="text-[12px] font-semibold text-stone-900 mb-2">{{ t("ordersPg.qvItems") }}</div>
              <div v-if="drawerLoading" class="space-y-2">
                <div v-for="n in 2" :key="n" class="h-10 rounded-lg bg-stone-100 animate-pulse" />
              </div>
              <div v-else-if="drawerDetail && drawerDetail.items && drawerDetail.items.length" class="space-y-2">
                <div v-for="(it, i) in drawerDetail.items" :key="i" class="flex items-center gap-2.5">
                  <img v-if="it.image" :src="it.image" loading="lazy"
                       class="w-9 h-9 rounded-lg object-cover ring-1 ring-stone-200/70 flex-shrink-0 bg-stone-100" @error="it.image = ''" />
                  <span v-else class="w-9 h-9 rounded-lg bg-stone-100 ring-1 ring-stone-200/70 flex items-center justify-center flex-shrink-0 text-stone-400">
                    <Icon name="package" :size="14" />
                  </span>
                  <div class="min-w-0 flex-1">
                    <div class="text-[12px] font-medium text-stone-900 truncate">{{ it.name }}</div>
                    <div class="font-mono text-[10px] text-stone-400">{{ it.sku }} · ×{{ it.qty }}</div>
                  </div>
                  <span class="font-mono text-[12px] font-semibold text-stone-800 tabular-nums">{{ fmtMAD(it.line) }}</span>
                </div>
                <div class="flex items-center justify-between pt-2 border-t border-stone-100">
                  <span class="text-[11.5px] text-stone-500">{{ t("ordersPg.qvGrand") }}</span>
                  <span class="font-mono text-[13px] font-bold text-stone-900 tabular-nums">{{ fmtMAD(drawerDetail.total ?? drawerRow.total) }} <span class="text-[9px] font-sans text-stone-400">MAD</span></span>
                </div>
              </div>
              <div v-else class="text-[11.5px] text-stone-400">{{ drawerRow.itemsDesc || "—" }}</div>
            </div>

            <!-- contact / docs -->
            <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3 space-y-1.5 text-[12px]">
              <div class="flex items-center justify-between gap-2">
                <span class="text-stone-400">{{ t("ordersPg.qvPhone") }}</span>
                <span class="flex items-center gap-1.5">
                  <span class="font-mono font-medium text-stone-800">{{ (drawerDetail && drawerDetail.phone) || drawerRow.phone || "—" }}</span>
                  <a v-if="drawerRow.phone" :href="waLink(drawerRow.phone)" target="_blank"
                     class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-emerald-100 hover:text-emerald-700 flex items-center justify-center">
                    <Icon name="message-circle" :size="11" />
                  </a>
                </span>
              </div>
              <div class="flex items-center justify-between gap-2">
                <span class="text-stone-400">{{ t("ordersPg.thDocs") }}</span>
                <span class="flex items-center gap-1.5 flex-wrap justify-end">
                  <a v-if="drawerDetail && drawerDetail.pl" :href="desk('pick-list', drawerDetail.pl)" target="_blank" class="doc-chip text-violet-700 bg-violet-50" style="--chip-ring:#ddd6fe">{{ drawerDetail.pl }}</a>
                  <a v-if="(drawerDetail && drawerDetail.awb) || drawerRow.awb" :href="(drawerDetail && drawerDetail.label_url) || drawerRow.labelUrl || '#'" target="_blank" class="doc-chip text-stone-600 bg-stone-100" style="--chip-ring:#e7e5e4">{{ (drawerDetail && drawerDetail.awb) || drawerRow.awb }}</a>
                  <a v-if="drawerDetail && drawerDetail.sh" :href="desk('shipment', drawerDetail.sh)" target="_blank" class="doc-chip text-emerald-700 bg-emerald-50" style="--chip-ring:#a7f3d0">{{ drawerDetail.sh }}</a>
                  <a v-if="drawerDetail && drawerDetail.ret" :href="desk('return-shipment', drawerDetail.ret)" target="_blank" class="doc-chip text-rose-700 bg-rose-50" style="--chip-ring:#fecdd3">{{ drawerDetail.ret }}</a>
                  <span v-if="!(drawerDetail && (drawerDetail.pl || drawerDetail.awb || drawerRow.awb))" class="text-stone-300">—</span>
                </span>
              </div>
              <div v-if="drawerDetail && drawerDetail.tracking_url" class="flex items-center justify-between gap-2">
                <span class="text-stone-400">{{ t("ordersPg.qvTracking") }}</span>
                <a :href="drawerDetail.tracking_url" target="_blank" class="text-[11.5px] font-semibold" style="color: var(--accent-700)">{{ t("ordersPg.qvTrackLive") }} →</a>
              </div>
            </div>

            <!-- activity -->
            <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3">
              <div class="text-[12px] font-semibold text-stone-900 mb-2">{{ t("ordersPg.qvActivity") }}</div>
              <div v-if="drawerLoading" class="space-y-2">
                <div v-for="n in 3" :key="n" class="h-8 rounded-lg bg-stone-100 animate-pulse" />
              </div>
              <ol v-else-if="drawerActivity.length" class="relative">
                <li v-for="(e, i) in drawerActivity.slice(0, 12)" :key="i" class="relative flex gap-2.5 pb-3 last:pb-0">
                  <span v-if="i < Math.min(drawerActivity.length, 12) - 1" class="absolute top-5 w-px left-[9px] bg-stone-200" style="bottom:0" />
                  <span class="relative z-10 w-[19px] h-[19px] rounded-md flex items-center justify-center flex-shrink-0 mt-0.5"
                        :style="{ background: qvMeta(e.kind).hex + '18', color: qvMeta(e.kind).hex }">
                    <Icon :name="qvMeta(e.kind).icon" :size="10" />
                  </span>
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center justify-between gap-2">
                      <span class="text-[11.5px] font-medium text-stone-900 truncate">{{ e.title }}</span>
                      <span class="text-[10px] text-stone-400 tabular-nums flex-shrink-0">{{ e.when.slice(5) }}</span>
                    </div>
                    <div class="text-[11px] text-stone-500 truncate">{{ qvActor(e.actor) }}<span v-if="e.detail" class="font-mono"> · {{ e.detail }}</span></div>
                  </div>
                </li>
              </ol>
              <div v-else class="text-[11.5px] text-stone-400">{{ t("ordersPg.qvNoActivity") }}</div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- Floating selection bar -->
    <transition name="selbar">
      <div v-if="selected.size" class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
        <div class="flex items-center gap-3 bg-stone-900 text-white rounded-2xl ps-4 pe-2 py-2 shadow-[0_16px_48px_-12px_rgba(0,0,0,0.45)]">
          <span class="text-[13px] font-semibold tabular-nums whitespace-nowrap">{{ selected.size }} {{ t("ordersPg.selected") }}</span>
          <span class="text-[12px] font-mono text-stone-300 tabular-nums whitespace-nowrap">{{ fmtMAD(selectedTotal) }} MAD</span>
          <template v-if="activeStage === 'to_pick'">
            <button
              class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-[12.5px] font-semibold text-white transition-all"
              :class="creating ? 'opacity-60 pointer-events-none' : 'hover:brightness-110'"
              style="background: var(--accent-600)"
              @click="createPL"
            >
              <Icon name="package" :size="14" :class="creating ? 'animate-pulse' : ''" />
              {{ creating ? t("ordersPg.creating") : t("ordersPg.createPL") }}
            </button>
            <button
              class="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12.5px] font-semibold text-stone-200 ring-1 ring-white/20 hover:bg-white/10 transition-colors"
              @click="assignSelected"
            >
              <Icon name="layout-grid" :size="13" /> {{ t("ordersPg.assign") }}
            </button>
          </template>
          <template v-else-if="activeStage === 'prepared'">
            <button
              class="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12.5px] font-semibold text-stone-200 ring-1 ring-white/20 hover:bg-white/10 transition-colors"
              @click="openLabels"
            >
              <Icon name="tag" :size="13" /> {{ t("ordersPg.openLabels") }}
            </button>
            <button
              class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-[12.5px] font-semibold text-white transition-all"
              :class="creating ? 'opacity-60 pointer-events-none' : 'hover:brightness-110'"
              style="background: var(--accent-600)"
              @click="markPrinted"
            >
              <Icon name="printer" :size="14" :class="creating ? 'animate-pulse' : ''" />
              {{ creating ? t("ordersPg.marking") : t("ordersPg.markPrinted") }}
            </button>
          </template>
          <button class="w-7 h-7 rounded-lg text-stone-400 hover:text-white hover:bg-white/10 flex items-center justify-center"
                  @click="selected = new Set()">
            <Icon name="x" :size="14" />
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import SuggestBatchesModal from "@/components/SuggestBatchesModal.vue";
import { WAREHOUSE, fmtMAD } from "@/lib/handoffData";
import { api, apiPost, liveOr } from "@/lib/resource";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";

const router = useRouter();
const route = useRoute();
const sbModal = ref(null);
const { success, warn } = useToast();
const { t, locale } = useI18n();

// ── Stage model (production-verified signals) ────────────────────────
const stages = [
  { key: "to_pick",   label: "To Pick",       icon: "list-checks",  hex: "#d97706", hint: "Confirmed · no pick list",    emptyTitle: "Nothing to pick 🎉",    emptyHint: "Every confirmed order has a pick list." },
  { key: "picking",   label: "Picking",       icon: "package",      hex: "#0891b2", hint: "Pick list in progress",       emptyTitle: "No picks running",      emptyHint: "Create pick lists from To Pick." },
  { key: "prepared",  label: "Prepared",      icon: "tag",          hex: "#7c3aed", hint: "AWB created · to print",      emptyTitle: "Nothing to print",      emptyHint: "Submitting a pick list creates the AWB." },
  { key: "ready",     label: "Ready",         icon: "printer",      hex: "#4f46e5", hint: "Printed · awaiting manifest", emptyTitle: "Nothing staged",        emptyHint: "Printed orders wait here for the manifest." },
  { key: "shipped",   label: "Shipped",       icon: "truck",        hex: "#059669", hint: "With Cathedis",               emptyTitle: "Nothing with carrier",  emptyHint: "Close a manifest to hand parcels over." },
  { key: "delivered", label: "Delivered",     icon: "check-circle", hex: "#10b981", hint: "Last 30 days",                emptyTitle: "No deliveries yet",     emptyHint: "Delivered orders land here." },
  { key: "to_return", label: "To Return",     icon: "rotate-ccw",   hex: "#ea580c", hint: "Coming back · with carrier",  emptyTitle: "No returns in transit", emptyHint: "Carrier-flagged returns appear here." },
  { key: "returned",  label: "Returned",      icon: "archive",      hex: "#78716c", hint: "Received in RET batch",       emptyTitle: "No returns received",   emptyHint: "Scanned return batches land here." },
];
const ATTENTION_META = { key: "attention", label: "Attention", icon: "alert-triangle", hex: "#e11d48", emptyTitle: "All clear", emptyHint: "No operational faults right now." };

const TRACK_ORDER = [
  { key: "In Transit",         lk: "intransit", hex: "#0891b2" },
  { key: "Out For Delivery",   lk: "ofd",       hex: "#4f46e5" },
  { key: "Delivery Exception", lk: "exception", hex: "#e11d48" },
  { key: "Failed Attempt",     lk: "failed",    hex: "#ea580c" },
  { key: "Pending",            lk: "pending",   hex: "#a8a29e" },
  { key: "Delivered",          lk: "awaiting",  hex: "#10b981" },
  { key: "none",               lk: "none",      hex: "#78716c" },
];

// ── Demo fallback (preview without a backend) ────────────────────────
const DEMO_BOARD = {
  counts: { to_pick: 12, picking: 4, prepared: 6, ready: 5, shipped: 42, delivered: 210, to_return: 9, returned: 6 },
  shippedTracks: { "In Transit": 12, "Out For Delivery": 9, "Delivery Exception": 11, "Failed Attempt": 5, Pending: 3, none: 2 },
  attention: { cancelled_midflow: 2, no_awb: 1, sync_lag: 3 },
  rows: [
    { no: "#242646", customer: "oualid elmouden", total: 149, channel: "shopify", items: 1, city: "Casablanca", status: "Pending", awb: "", track: "", ageMins: 41 },
    { no: "#242644", customer: "Chada Rami", total: 198, channel: "shopify", items: 2, city: "Rabat", status: "Pending", awb: "", track: "", ageMins: 12 },
    { no: "SAL-ORD-2026-00299", customer: "Salma", total: 149, channel: "joyagent", items: 1, city: "Tangier", status: "Pending", awb: "", track: "", ageMins: 8 },
  ],
};

// ── State ────────────────────────────────────────────────────────────
const mode = ref("loading"); // loading → skeleton · live → real · demo → preview fallback
const counts = ref({});
const values = ref({});
const shippedTracks = ref({});
const attention = ref({});
const rows = ref([]);
const activeStage = ref("to_pick");
const activeTrack = ref("");
const q = ref("");
const loading = ref(false);
const updatedAt = ref(Date.now());
const tick = ref(0);
let timer = null;
let searchTimer = null;

const activeMeta = computed(() =>
  activeStage.value === "attention" ? ATTENTION_META : stages.find((s) => s.key === activeStage.value) || stages[0]
);
const attentionTotal = computed(() =>
  (attention.value.cancelled_midflow || 0) + (attention.value.no_awb || 0) + (attention.value.sync_lag || 0)
);
const attentionChips = computed(() => [
  { key: "cancelled_midflow", label: t("ordersPg.faults.cancelled_midflow"), count: attention.value.cancelled_midflow || 0, hex: "#e11d48" },
  { key: "no_awb", label: t("ordersPg.faults.no_awb"), count: attention.value.no_awb || 0, hex: "#ea580c" },
  { key: "sync_lag", label: t("ordersPg.faults.sync_lag"), count: attention.value.sync_lag || 0, hex: "#d97706" },
].filter((c) => c.count > 0));

const trackChips = computed(() => {
  const chips = [{ key: "", label: t("ordersPg.all"), count: counts.value.shipped || 0, hex: "#059669" }];
  for (const tr of TRACK_ORDER) {
    const c = shippedTracks.value[tr.key] || 0;
    if (c > 0) chips.push({ ...tr, label: t("ordersPg.tracks." + tr.lk), count: c });
  }
  return chips;
});

const selected = ref(new Set());
const creating = ref(false);
const cities = ref([]);
const serverNow = ref(null); // server clock anchor — no browser-timezone drift
const dateRange = ref("");
const sortKey = ref("");
const sortDir = ref("desc");
const exporting = ref(false);
const drawerRow = ref(null);
const drawerDetail = ref(null);
const drawerActivity = ref([]);
const drawerLoading = ref(false);
const cityFilter = ref("");
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

async function load(stage, track = "", keepPage = false) {
  if (stage !== activeStage.value) cityFilter.value = "";
  if (!keepPage) page.value = 1;
  activeStage.value = stage;
  activeTrack.value = stage === "shipped" ? track : "";
  loading.value = true;
  selected.value = new Set();
  const live = await liveOr(null, () =>
    api("orders.board", {
      stage, track: track || undefined,
      limit: pageSize.value, offset: (page.value - 1) * pageSize.value,
      q: q.value.trim() || undefined, city: cityFilter.value || undefined,
      sort: sortKey.value ? `${sortKey.value}_${sortDir.value}` : undefined,
      dates: dateRange.value || undefined,
    })
  );
  if (live && live.counts) {
    mode.value = "live";
    counts.value = live.counts;
    values.value = live.values || {};
    shippedTracks.value = live.shippedTracks || {};
    attention.value = live.attention || {};
    rows.value = live.rows || [];
    cities.value = live.cities || [];
    total.value = live.total ?? (live.rows || []).length;
    if (live.serverNow) serverNow.value = live.serverNow;
    updatedAt.value = Date.now();
  } else if (mode.value !== "live") {
    // Backend truly unreachable (local preview) — demo, clearly a fallback.
    mode.value = "demo";
    counts.value = DEMO_BOARD.counts;
    values.value = { to_pick: 5900, picking: 2100, prepared: 3400, ready: 2800, shipped: 21400 };
    shippedTracks.value = DEMO_BOARD.shippedTracks;
    attention.value = DEMO_BOARD.attention;
    rows.value = stage === "to_pick" ? DEMO_BOARD.rows : [];
    total.value = rows.value.length;
  } else {
    rows.value = [];
    total.value = 0;
  }
  loading.value = false;
}

const selectableStage = computed(() => ["to_pick", "prepared"].includes(activeStage.value));

function toggleSort(key) {
  if (sortKey.value === key) sortDir.value = sortDir.value === "desc" ? "asc" : "desc";
  else { sortKey.value = key; sortDir.value = "desc"; }
  load(activeStage.value, activeTrack.value, true);
}

// ── Quick-view drawer ────────────────────────────────────────────────
const QV_META = {
  submit: { icon: "check-circle", hex: "#10b981" }, status: { icon: "git-branch", hex: "#7c3aed" },
  sales: { icon: "user", hex: "#d97706" }, track: { icon: "truck", hex: "#0891b2" },
  awb: { icon: "tag", hex: "#4f46e5" }, picker: { icon: "users", hex: "#0284c7" },
  comment: { icon: "message-circle", hex: "#78716c" }, pl: { icon: "package", hex: "#7c3aed" },
  dn: { icon: "file-text", hex: "#78716c" }, sh: { icon: "truck", hex: "#059669" },
  ret: { icon: "rotate-ccw", hex: "#e11d48" },
};
function qvMeta(kind) { return QV_META[kind] || { icon: "info", hex: "#78716c" }; }
function qvActor(actor) { return pickerShort(actor); }
async function openDrawer(r) {
  drawerRow.value = r;
  drawerDetail.value = null;
  drawerActivity.value = [];
  drawerLoading.value = true;
  const nameArg = r.no.replace("#", "");
  const [detail, activity] = await Promise.all([
    liveOr(null, () => api("orders.detail", { name: nameArg })),
    liveOr(null, () => api("orders.activity", { name: nameArg })),
  ]);
  if (detail && detail.name) drawerDetail.value = detail;
  if (Array.isArray(activity)) drawerActivity.value = activity;
  drawerLoading.value = false;
}

// ── Bulk: assign / open labels / mark printed ────────────────────────
function assignSelected() {
  const ids = Array.from(selected.value).join(",");
  router.push({ name: "Assign", query: ids ? { orders: ids } : {} });
}
function openLabels() {
  const picked = rows.value.filter((r) => selected.value.has(r.no) && r.labelUrl);
  if (!picked.length) { warn("No labels", "Selected orders have no label files."); return; }
  picked.forEach((r, i) => setTimeout(() => window.open(r.labelUrl, "_blank"), i * 250));
}
async function markPrinted() {
  creating.value = true;
  try {
    const res = await apiPost("shipping.mark_labels_printed", { orders: Array.from(selected.value) });
    success(`${res.printed} labels marked printed`, "Moved to Ready to Ship");
    selected.value = new Set();
    load("prepared");
  } catch (e) {
    warn("Couldn't mark printed", String(e.message || e));
  } finally {
    creating.value = false;
  }
}

// ── CSV export of the current filtered stage (up to 500 rows) ────────
async function exportCsv() {
  exporting.value = true;
  try {
    const all = [];
    for (let off = 0; off < 500; off += 100) {
      const res = await liveOr(null, () => api("orders.board", {
        stage: activeStage.value, track: activeTrack.value || undefined,
        limit: 100, offset: off, q: q.value.trim() || undefined,
        city: cityFilter.value || undefined, dates: dateRange.value || undefined,
        sort: sortKey.value ? `${sortKey.value}_${sortDir.value}` : undefined,
      }));
      const batch = (res && res.rows) || [];
      all.push(...batch);
      if (batch.length < 100) break;
    }
    const source = all.length ? all : rows.value;
    const cols = ["no", "customer", "phone", "status", "city", "picker", "awb", "pl", "sh", "ret", "created", "total"];
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [cols.join(",")]
      .concat(source.map((r) => cols.map((c) => esc(r[c])).join(",")))
      .join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `orders-${activeStage.value}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    success(`Exported ${source.length} orders`);
  } finally {
    exporting.value = false;
  }
}

// ── Pagination (numbered, like Next) ─────────────────────────────────
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));
const pageWindow = computed(() => {
  const tp = totalPages.value, c = page.value, out = [];
  const push = (v) => { if (!out.includes(v)) out.push(v); };
  push(1);
  if (c - 1 > 2) push("…");
  for (let p = Math.max(2, c - 1); p <= Math.min(tp - 1, c + 1); p++) push(p);
  if (c + 1 < tp - 1) push("…2");
  if (tp > 1) push(tp);
  return out;
});
const rangeStart = computed(() => total.value === 0 ? 0 : (page.value - 1) * pageSize.value + 1);
const rangeEnd = computed(() => Math.min(page.value * pageSize.value, total.value));
function goPage(p) {
  if (p === "…" || p === "…2" || p === page.value || p < 1 || p > totalPages.value) return;
  page.value = p;
  load(activeStage.value, activeTrack.value, true);
}
function setPageSize(e) {
  pageSize.value = Number(e.target.value);
  page.value = 1;
  load(activeStage.value, activeTrack.value, true);
}
function setTrack(t) { load("shipped", t); }

// ── Selection → create a combined Pick List (dispatcher action) ──────
const allSelected = computed(() => rows.value.length > 0 && rows.value.every((r) => selected.value.has(r.no)));
const selectedTotal = computed(() =>
  rows.value.filter((r) => selected.value.has(r.no)).reduce((a, r) => a + (r.total || 0), 0)
);
function toggleRow(no) {
  const s = new Set(selected.value);
  s.has(no) ? s.delete(no) : s.add(no);
  selected.value = s;
}
function toggleAll() {
  selected.value = allSelected.value ? new Set() : new Set(rows.value.map((r) => r.no));
}
async function createPL() {
  creating.value = true;
  try {
    const res = await apiPost("picking.create_pick_list_from_orders", {
      orders: Array.from(selected.value),
    });
    success(`Pick List ${res.pl} created`, `${res.orders} orders · ${res.items} items — draft, ready to assign`);
    selected.value = new Set();
    load("to_pick");
  } catch (e) {
    warn("Couldn't create the pick list", String(e.message || e));
  } finally {
    creating.value = false;
  }
}

// Same-day cutoff (14:00): flag To Pick orders that already missed it.
function srvNow() {
  return serverNow.value ? new Date(serverNow.value.replace(" ", "T")) : new Date();
}
function missedCutoff(r) {
  if (!r.created) return false;
  const created = new Date(r.created.replace(" ", "T"));
  const now = srvNow();
  const cut = new Date(now); cut.setHours(14, 0, 0, 0);
  const day0 = new Date(now); day0.setHours(0, 0, 0, 0);
  if (created < day0) return true;                   // from a previous day
  return created < cut && now > cut;                 // placed before today's cutoff, cutoff passed
}
function onSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => load(activeStage.value, activeTrack.value), 350);
}
const rowsTotal = computed(() => rows.value.reduce((a, r) => a + (r.total || 0), 0));
function fmtK(v) {
  return v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : `${v}`;
}

const updatedAgo = computed(() => {
  tick.value; // reactive tick
  const s = Math.max(0, Math.round((Date.now() - updatedAt.value) / 1000));
  if (s < 5) return t("ordersPg.justNow");
  if (s < 60) return t("ordersPg.agoS").replace("{n}", s);
  return t("ordersPg.agoM").replace("{n}", Math.round(s / 60));
});

let refreshTimer = null;
onMounted(() => {
  const qStage = String(route.query.stage || "");
  const valid = qStage === "attention" || stages.some((s) => s.key === qStage);
  load(valid ? qStage : "to_pick");
  timer = setInterval(() => { tick.value++; }, 5000);
  // Silent refresh — skipped while the dispatcher has a selection in hand.
  refreshTimer = setInterval(() => {
    if (!selected.value.size && !loading.value && document.visibilityState === "visible") {
      load(activeStage.value, activeTrack.value, true);
    }
  }, 120000);
});
onUnmounted(() => { timer && clearInterval(timer); refreshTimer && clearInterval(refreshTimer); });

// Visual weight of each stage relative to the busiest one.
function stageShare(key) {
  const max = Math.max(...stages.map((s) => counts.value[s.key] || 0), 1);
  const c = counts.value[key] || 0;
  return c ? Math.max(4, Math.round((c / max) * 100)) : 0;
}
// "2026-07-03 10:23" → "10:23" today, else "Jul 3 · 10:23".
function createdFmt(created) {
  const [d, tm] = created.split(" ");
  const today = (serverNow.value || new Date().toISOString()).slice(0, 10);
  if (d === today) return tm;
  const dt = new Date(d + "T00:00:00");
  return dt.toLocaleDateString(locale.value === "ar" ? "ar-MA" : locale.value === "fr" ? "fr-FR" : "en-US", { month: "short", day: "numeric" }) + " · " + tm;
}

// ── Row helpers ──────────────────────────────────────────────────────
function desk(doctype, name) {
  return `/app/${doctype}/${encodeURIComponent(name)}`;
}
function openOrder(r) {
  router.push({ name: "OrderDetail", params: { name: r.no.replace("#", "") } });
}
const PICKER_SHORT = {
  marouaneelmessaoudi07: "Marouane", mouakkalanass: "Anass", asmaazirary7: "Asmaa",
  lamdanisaad12: "Saad", ossamanahila: "Oussama", saidnakri65: "Said", redazaari47: "Reda",
};
function pickerShort(email) {
  const k = (email || "").split("@")[0];
  return PICKER_SHORT[k] || k;
}
function initials(email) {
  const s = pickerShort(email);
  return (s[0] || "?").toUpperCase() + (s[1] || "").toLowerCase();
}
function ageFmt(mins) {
  if (mins < 60) return `${mins}m`;
  if (mins < 1440) return `${Math.floor(mins / 60)}h ${mins % 60}m`;
  return `${Math.floor(mins / 1440)}d ${Math.floor((mins % 1440) / 60)}h`;
}
function ageHex(mins) {
  return mins < 120 ? "#10b981" : mins < 360 ? "#d97706" : "#e11d48";
}
function channelHex(ch) {
  return { shopify: "#10b981", youcan: "#7c3aed", landing: "#d97706", joyagent: "#0284c7", manual: "#78716c", whatsapp: "#16a34a" }[ch] || "#a8a29e";
}
// 77% of orders have no custom_channel — derive it from the naming series.
function channelOf(r) {
  if (r.channel) return r.channel;
  const no = r.no || "";
  if (no.startsWith("#")) return "shopify";
  if (no.startsWith("YC-")) return "youcan";
  if (no.startsWith("J-")) return "landing";
  if (no.startsWith("WA-")) return "whatsapp";
  if (no.startsWith("SAL-ORD")) return "joyagent";
  return "manual";
}
// Moroccan mobile → wa.me international format (0612… → 212612…).
function waLink(phone) {
  let d = (phone || "").replace(/\D/g, "");
  if (d.startsWith("00")) d = d.slice(2);
  if (d.startsWith("0")) d = "212" + d.slice(1);
  else if (!d.startsWith("212")) d = "212" + d;
  return `https://wa.me/${d}`;
}
function trackHexOf(t) {
  return TRACK_ORDER.find((x) => x.key === t)?.hex || "#a8a29e";
}
const CHANNEL_LABEL = { shopify: "Shopify", youcan: "YouCan", landing: "Landing Page", joyagent: "JoyAgent", manual: "Manual", whatsapp: "WhatsApp" };
function channelLabel(ch) { return CHANNEL_LABEL[ch] || ch; }
function stageLabelOf() {
  // Raw status "Pending" is ambiguous — show the derived stage instead.
  return activeStage.value === "picking" ? "Picking" : "Pending";
}
// Honest SLA until the DN SLA engine has history: same-day cutoff before the
// carrier has it; carrier exceptions after.
function slaOf(r) {
  const st = activeStage.value;
  if (st === "delivered") return { label: t("sla.delivered"), hex: "#10b981", calm: true };
  if (st === "to_return" || st === "returned") return { label: t("sla.returned"), hex: "#78716c", calm: true };
  if (st === "shipped") {
    if (r.track === "Delivery Exception" || r.track === "Failed Attempt") return { label: t("sla.late"), hex: "#ea580c" };
    return { label: t("sla.onTrack"), hex: "#10b981", calm: true };
  }
  if (missedCutoff(r)) return { label: t("sla.breached"), hex: "#e11d48" };
  if (r.created) {
    const created = new Date(r.created.replace(" ", "T"));
    const now = srvNow();
    const cut = new Date(now); cut.setHours(14, 0, 0, 0);
    const today = new Date(now); today.setHours(0, 0, 0, 0);
    if (created >= today && now < cut && (cut - now) < 90 * 60000) return { label: t("sla.atRisk"), hex: "#d97706" };
  }
  return { label: t("sla.onTrack"), hex: "#10b981", calm: true };
}
function statusHex(s) {
  return {
    Pending: "#d97706", Picked: "#ea580c", "In transit": "#0891b2", Received: "#0891b2",
    "Label Generated": "#7c3aed", "Label Printed": "#4f46e5",
    Shipped: "#059669", Delivered: "#10b981", Returned: "#e11d48",
  }[s] || "#78716c";
}
function faultHex(kind) {
  return { cancelled_midflow: "#e11d48", no_awb: "#ea580c", sync_lag: "#d97706" }[kind] || "#78716c";
}
function faultLabel(kind) {
  return t("ordersPg.faultsLong." + kind, kind);
}
function itemsWord(n) {
  return t(n === 1 ? "ordersPg.item" : "ordersPg.items");
}
function statusLabel(s) {
  const eff = s === "Pending" ? stageLabelOf() : s;
  if (eff === "Picking") return t("ordersPg.stages.picking.label");
  return t("stage." + eff, eff);
}
function trackLabelOf(track) {
  const tr = TRACK_ORDER.find((x) => x.key === track);
  return tr ? t("ordersPg.tracks." + tr.lk) : track;
}
function actionFor(r) {
  switch (activeStage.value) {
    case "to_pick":   return { label: t("ordersPg.actions.assign"), go: () => router.push({ name: "Assign" }) };
    case "picking":   return r.pl ? { label: t("ordersPg.actions.openPl"), href: desk("pick-list", r.pl) } : null;
    case "prepared":  return r.labelUrl ? { label: t("ordersPg.actions.print"), href: r.labelUrl } : { label: t("ordersPg.actions.open"), href: desk("sales-order", r.no) };
    case "ready":     return { label: t("ordersPg.actions.manifest"), go: () => router.push({ name: "Manifest" }) };
    case "shipped":   return { label: t("ordersPg.actions.track"), href: desk("sales-order", r.no) };
    case "to_return": return { label: t("ordersPg.actions.track"), href: desk("sales-order", r.no) };
    case "returned":  return r.ret ? { label: t("ordersPg.actions.openRet"), href: desk("return-shipment", r.ret) } : null;
    case "attention": return r.pl ? { label: t("ordersPg.actions.fix"), href: desk("pick-list", r.pl) } : { label: t("ordersPg.actions.open"), href: desk("sales-order", r.no) };
    default: return null;
  }
}
</script>

<style scoped>
.doc-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 9px; border-radius: 7px;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 11.5px; font-weight: 500;
  box-shadow: inset 0 0 0 1px var(--chip-ring, transparent);
  transition: background-color .15s;
}
.board-cb {
  width: 15px; height: 15px; cursor: pointer;
  accent-color: var(--accent-600);
}
.pager-btn {
  display: inline-flex; align-items: center; justify-content: center;
  height: 32px; padding: 0 9px; border-radius: 8px;
  font-size: 12.5px; font-weight: 600; color: #57534e;
  background: #fff; box-shadow: inset 0 0 0 1px #e7e5e4;
  transition: background-color .12s;
}
.pager-btn:hover:not(:disabled):not(.pager-active) { background: #fafaf9; }
.pager-btn:disabled { opacity: .4; cursor: default; box-shadow: none; background: transparent; }
.pager-active { color: #fff; background: var(--accent-600); box-shadow: none; }
.qv-enter-from .qv-panel, .qv-leave-to .qv-panel { transform: translateX(100%); }
[dir="rtl"] .qv-enter-from .qv-panel, [dir="rtl"] .qv-leave-to .qv-panel { transform: translateX(-100%); }
.qv-enter-active .qv-panel, .qv-leave-active .qv-panel { transition: transform .26s cubic-bezier(.16,1,.3,1); }
.qv-enter-from, .qv-leave-to { opacity: 0; }
.qv-enter-active, .qv-leave-active { transition: opacity .2s ease; }
.selbar-enter-from, .selbar-leave-to { opacity: 0; transform: translate(-50%, 12px); }
.selbar-enter-active, .selbar-leave-active { transition: all .22s cubic-bezier(.16,1,.3,1); }
</style>
