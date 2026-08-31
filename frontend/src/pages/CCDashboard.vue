<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1200px] mx-auto">
    <header class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[19px] font-bold text-stone-900 tracking-tight">{{ t('ccd.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-1">{{ t('ccd.intro') }}</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <div class="flex items-center gap-0.5 bg-white ring-1 ring-stone-200/80 rounded-xl p-1">
          <button v-for="rk in RANGES" :key="rk"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold transition-colors"
                  :class="range === rk ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100'"
                  @click="range = rk; loadReport()">{{ t('ccd.r_' + rk) }}</button>
        </div>
        <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[12.5px] font-semibold text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"
                :disabled="loading" @click="load(); loadReport();">
          <Icon name="refresh-cw" :size="13" />{{ t('common.refresh') }}
        </button>
      </div>
    </header>

    <!-- RANGE KPIs: the numbers the section is judged on, over the picked window -->
    <div v-if="rLoading && !r" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <span v-for="n in 4" :key="n" class="h-[104px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <template v-else-if="r">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="ccd-kpi">
          <div class="ccd-kpi-l"><Icon name="shopping-bag" :size="12" class="inline -mt-px me-1" />{{ t('ccd.kOrders') }}</div>
          <div class="flex items-baseline gap-2 mt-1"><span class="text-[26px] font-extrabold tabular-nums text-stone-900">{{ fmtN(r.ordersIn?.n) }}</span><span v-if="deltas.orders" class="ccd-delta" :class="deltas.orders.up ? 'ccd-up' : 'ccd-down'">{{ deltas.orders.txt }}</span></div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ fmtN(r.ordersIn?.value) }} MAD</div>
        </div>
        <div class="ccd-kpi flex items-center gap-3">
          <div class="relative w-[64px] h-[64px] flex-shrink-0">
            <svg viewBox="0 0 64 64" class="w-full h-full -rotate-90">
              <circle cx="32" cy="32" r="26" fill="none" stroke="rgb(231 229 228)" stroke-width="7" />
              <circle cx="32" cy="32" r="26" fill="none" stroke-width="7" stroke-linecap="round"
                      :stroke="all.rate === null ? 'rgb(214 211 209)' : all.rate >= 50 ? 'rgb(16 185 129)' : 'rgb(244 63 94)'"
                      :stroke-dasharray="163.4" :stroke-dashoffset="163.4 - (163.4 * (all.rate || 0)) / 100"
                      style="transition: stroke-dashoffset .7s ease" />
            </svg>
            <span class="absolute inset-0 flex items-center justify-center text-[15px] font-extrabold tabular-nums"
                  :class="all.rate === null ? 'text-stone-300' : all.rate >= 50 ? 'text-emerald-600' : 'text-rose-600'">
              {{ all.rate === null ? '—' : all.rate + '%' }}</span>
          </div>
          <div class="min-w-0">
            <div class="ccd-kpi-l">{{ t('ccd.kRate') }}</div>
            <div class="text-[11.5px] tabular-nums mt-1 flex items-center gap-2">
              <span class="text-emerald-600 font-bold">{{ fmtN(all.confirm) }} <Icon name="check" :size="10" class="inline -mt-px" /></span>
              <span class="text-rose-500 font-bold">{{ fmtN(all.cancel) }} <Icon name="x" :size="10" class="inline -mt-px" /></span>
              <span class="text-stone-400">{{ t('ccd.ofDecided').replace('{n}', fmtN(all.confirm + all.cancel)) }}</span>
            </div>
            <div v-if="auto" class="text-[10px] text-stone-500 mt-0.5 tabular-nums">
              <Icon name="user" :size="9" class="inline -mt-px" /> {{ tot.rate === null ? '—' : tot.rate + '%' }}
              <span class="text-stone-300 mx-1">|</span>
              <Icon name="bot" :size="9" class="inline -mt-px" /> {{ auto.confirmRate === null ? '—' : auto.confirmRate + '%' }}
            </div>
            <div class="text-[10px] text-stone-400 mt-0.5">{{ t('ccd.kRateHint') }} <span v-if="deltas.rate" class="ccd-delta" :class="deltas.rate.up ? 'ccd-up' : 'ccd-down'">{{ deltas.rate.txt }}</span></div>
          </div>
        </div>
        <div class="ccd-kpi">
          <div class="ccd-kpi-l"><Icon name="activity" :size="12" class="inline -mt-px me-1" />{{ t('ccd.kDecisions') }}</div>
          <div class="flex items-baseline gap-2 mt-1"><span class="text-[26px] font-extrabold tabular-nums text-stone-900">{{ fmtN(all.total) }}</span><span v-if="deltas.total" class="ccd-delta" :class="deltas.total.up ? 'ccd-up' : 'ccd-down'">{{ deltas.total.txt }}</span></div>
          <div v-if="auto" class="text-[11px] tabular-nums flex items-center gap-2">
            <span class="text-stone-600 font-semibold"><Icon name="user" :size="10" class="inline -mt-px" /> {{ fmtN(tot.total) }}</span>
            <span class="text-sky-600 font-semibold"><Icon name="bot" :size="10" class="inline -mt-px" /> {{ fmtN(auto.total) }}</span>
            <span class="text-stone-400">{{ autoShare }}% {{ t('ccd.byAutomation') }}</span>
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ fmtN(tot.dna) }} {{ t('cf.actDna') }} · {{ fmtN(tot.followup) }} {{ t('cf.actFollowup') }}</div>
        </div>
        <div class="ccd-kpi">
          <div class="ccd-kpi-l"><Icon name="wallet" :size="12" class="inline -mt-px me-1" />{{ t('ccd.kValue') }}</div>
          <div class="flex items-baseline gap-2 mt-1"><span class="text-[26px] font-extrabold tabular-nums text-stone-900">{{ fmtN(tot.value) }}</span><span v-if="deltas.value" class="ccd-delta" :class="deltas.value.up ? 'ccd-up' : 'ccd-down'">{{ deltas.value.txt }}</span></div>
          <div class="text-[11px] tabular-nums" :class="collectedPct === null ? 'text-stone-400' : collectedPct >= 60 ? 'text-emerald-600' : 'text-amber-600'">
            {{ collectedPct === null ? '—' : t('ccd.kCollected').replace('{v}', fmtN(tot.collected)).replace('{p}', String(collectedPct)) }}
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-4 items-start">
        <!-- daily decisions, stacked -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center gap-2 mb-3">
            <Icon name="trending-up" :size="14" class="text-[var(--accent-600)]" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('ccd.dailyTitle') }}</span>
            <span class="ms-auto flex items-center gap-3 text-[10.5px] text-stone-500">
              <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-400 me-1" />{{ t('cf.actConfirm') }}</span>
              <span><span class="inline-block w-2 h-2 rounded-full bg-rose-400 me-1" />{{ t('cf.actCancel') }}</span>
              <span><span class="inline-block w-2 h-2 rounded-full bg-amber-300 me-1" />{{ t('cf.actDna') }}</span>
            </span>
          </div>
          <div v-if="(r.funnel || []).length" class="flex items-end gap-1 h-[110px]">
            <div v-for="f in r.funnel" :key="f.date" class="flex-1 flex flex-col items-center gap-0.5 min-w-0"
                 :title="`${f.date} · ${f.confirm}✓ ${f.cancel}✗ ${f.dna}·`">
              <div class="w-full max-w-[26px] flex flex-col justify-end rounded-t overflow-hidden" :style="{ height: '92px' }">
                <div class="w-full bg-amber-300" :style="{ height: fH(f.dna) }" />
                <div class="w-full bg-rose-400" :style="{ height: fH(f.cancel) }" />
                <div class="w-full bg-emerald-400" :style="{ height: fH(f.confirm) }" />
              </div>
              <span class="text-[8.5px] text-stone-400 tabular-nums">{{ f.date.slice(8) }}</span>
            </div>
          </div>
          <div v-else class="text-center text-[12px] text-stone-400 py-8">{{ t('ccd.noData') }}</div>
        </div>

        <div class="space-y-4">
          <!-- what the bot decided, on its own -->
          <div v-if="auto && auto.total" class="bg-white rounded-xl ring-1 ring-sky-200/70 p-4">
            <div class="text-[12px] font-semibold text-stone-900 flex items-center gap-2 mb-2.5">
              <Icon name="bot" :size="13" class="text-sky-600" />{{ t('ccd.autoTitle') }}
            </div>
            <div class="flex items-baseline gap-2">
              <span class="text-[24px] font-extrabold tabular-nums text-stone-900">{{ fmtN(auto.total) }}</span>
              <span class="text-[11px] text-stone-500">{{ t('ccd.autoOfAll').replace('{p}', String(autoShare)) }}</span>
            </div>
            <div class="h-2 rounded-full bg-stone-100 overflow-hidden mt-2 flex">
              <div class="h-full bg-emerald-400 transition-all duration-700"
                   :style="{ width: Math.round((auto.confirm * 100) / Math.max(1, auto.total)) + '%' }" />
              <div class="h-full bg-rose-400 transition-all duration-700"
                   :style="{ width: Math.round((auto.cancel * 100) / Math.max(1, auto.total)) + '%' }" />
              <div class="h-full bg-amber-300 transition-all duration-700"
                   :style="{ width: Math.round((auto.followup * 100) / Math.max(1, auto.total)) + '%' }" />
            </div>
            <div class="text-[11px] text-stone-500 tabular-nums mt-1.5 flex flex-wrap gap-x-2.5">
              <span class="text-emerald-600 font-semibold">{{ fmtN(auto.confirm) }} {{ t('cf.actConfirm') }}</span>
              <span class="text-rose-500 font-semibold">{{ fmtN(auto.cancel) }} {{ t('cf.actCancel') }}</span>
              <span class="text-amber-600 font-semibold">{{ fmtN(auto.followup) }} {{ t('cf.actFollowup') }}</span>
            </div>
            <div class="text-[11px] text-stone-400 tabular-nums mt-1.5 pt-1.5 border-t border-stone-100">
              {{ fmtN(auto.confirmedValue) }} MAD · {{ t('ccd.autoHint') }}
            </div>
          </div>
          <!-- automation share -->
          <div v-if="r.ladder" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div class="text-[12px] font-semibold text-stone-900 flex items-center gap-2 mb-2">
              <Icon name="send" :size="13" class="text-sky-600" />{{ t('ccd.chaseTitle') }}
            </div>
            <div class="h-2 rounded-full bg-stone-100 overflow-hidden">
              <div class="h-full rounded-full bg-sky-400 transition-all duration-700"
                   :style="{ width: Math.min(100, Math.round(((r.ladder.r1 || 0) * 100) / Math.max(1, r.ladder.n))) + '%' }" />
            </div>
            <div class="text-[11px] text-stone-500 tabular-nums mt-1.5">
              {{ fmtN(r.ladder.r1) }} + {{ fmtN(r.ladder.r2) }} / {{ fmtN(r.ladder.n) }} · {{ t('ccd.chaseHint') }}
            </div>
          </div>
          <!-- top cancel reasons -->
          <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
            <div class="text-[12px] font-semibold text-stone-900 flex items-center gap-2 mb-2.5">
              <Icon name="circle-x" :size="13" class="text-rose-500" />{{ t('ccd.reasonsTitle') }}
            </div>
            <div v-if="(r.reasons || []).length" class="space-y-2">
              <div v-for="rr in r.reasons.slice(0, 5)" :key="rr.reason" class="min-w-0">
                <div class="flex items-center justify-between gap-2 text-[11.5px]">
                  <span class="text-stone-700 truncate" dir="auto">{{ rr.reason }}</span>
                  <b class="tabular-nums text-stone-900 flex-shrink-0">{{ fmtN(rr.n) }}</b>
                </div>
                <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden mt-0.5">
                  <div class="h-full rounded-full bg-rose-300"
                       :style="{ width: Math.round((rr.n * 100) / Math.max(1, r.reasons[0]?.n || 1)) + '%' }" />
                </div>
              </div>
            </div>
            <div v-else class="text-[11.5px] text-stone-400 py-2 text-center">{{ t('ccd.noData') }}</div>
          </div>
          <RouterLink :to="{ name: 'ConfirmationReports' }"
                      class="block text-center text-[12px] font-semibold text-[var(--accent-600)] bg-white rounded-xl ring-1 ring-stone-200/70 py-2.5 hover:bg-stone-50">
            {{ t('ccd.fullReport') }}
          </RouterLink>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-4 items-start">
        <!-- did the confirms actually get taken? -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center gap-2 mb-3">
            <Icon name="package-check" :size="14" class="text-emerald-600" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('ccd.stickTitle') }}</span>
            <span class="text-[11px] text-stone-400 hidden sm:inline">{{ t('ccd.stickHint') }}</span>
            <span v-if="stickPct !== null" class="ms-auto text-[13px] font-extrabold tabular-nums"
                  :class="stickPct >= 60 ? 'text-emerald-600' : stickPct >= 40 ? 'text-amber-600' : 'text-rose-600'">{{ stickPct }}%</span>
          </div>
          <div v-if="(r.stick || []).length" class="flex items-end gap-1 h-[92px]">
            <div v-for="f2 in r.stick" :key="f2.d" class="flex-1 flex flex-col items-center gap-0.5 min-w-0"
                 :title="`${f2.d} · ${f2.delivered}/${f2.shipped}`">
              <div class="w-full max-w-[26px] h-[76px] bg-stone-100 rounded-t flex flex-col justify-end overflow-hidden">
                <div class="w-full bg-emerald-400 transition-all" :style="{ height: stickH(f2) }" />
              </div>
              <span class="text-[8.5px] text-stone-400 tabular-nums">{{ f2.d.slice(8) }}</span>
            </div>
          </div>
          <div v-else class="text-center text-[12px] text-stone-400 py-8">{{ t('ccd.noData') }}</div>
        </div>

        <!-- where parcels die -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[12px] font-semibold text-stone-900 flex items-center gap-2 mb-2.5">
            <Icon name="map-pin" :size="13" class="text-rose-500" />{{ t('ccd.citiesTitle') }}
          </div>
          <div v-if="(r.cities || []).length" class="space-y-2">
            <div v-for="c in r.cities" :key="c.city" class="min-w-0">
              <div class="flex items-center justify-between gap-2 text-[11.5px]">
                <span class="text-stone-700 truncate" dir="auto">{{ c.city }}</span>
                <span class="tabular-nums flex-shrink-0"><b class="text-rose-600">{{ c.failed }}</b><span class="text-stone-400"> / {{ c.parcels }}</span></span>
              </div>
              <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden mt-0.5">
                <div class="h-full rounded-full"
                     :class="(c.failed / Math.max(1, c.parcels)) > 0.3 ? 'bg-rose-400' : 'bg-amber-300'"
                     :style="{ width: Math.round((c.failed * 100) / Math.max(1, c.parcels)) + '%' }" />
              </div>
            </div>
          </div>
          <div v-else class="text-[11.5px] text-stone-400 py-2 text-center">{{ t('ccd.noData') }}</div>
        </div>
      </div>
    </template>

    <div v-if="loading && !d" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <span v-for="n in 4" :key="n" class="h-[92px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>
    <div v-else-if="loadError" class="rounded-2xl p-10 text-center bg-rose-50/60 ring-1 ring-rose-200/70">
      <div class="text-[14px] font-semibold text-rose-700">{{ t('cf.loadFail') }}</div>
      <div class="text-[12px] text-rose-600/80 font-mono mt-1 break-words">{{ loadError }}</div>
      <button class="mt-3 h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="load">{{ t('common.retry') }}</button>
    </div>

    <template v-if="d">
      <div class="flex items-center gap-2 pt-1">
        <Icon name="shield-alert" :size="15" class="text-[var(--accent-600)]" />
        <span class="text-[13px] font-bold text-stone-900">{{ t('ccd.slaSection') }}</span>
        <span class="text-[11px] text-stone-400">{{ t('ccd.slaSectionHint') }}</span>
      </div>
      <!-- SPEED hero -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="bg-white rounded-2xl ring-1 p-4" :class="todayH > 2 ? 'ring-rose-200' : 'ring-emerald-200'">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('ccd.firstTouchToday') }}</div>
          <div class="text-[26px] font-bold tabular-nums mt-1" :class="todayH > 2 ? 'text-rose-600' : 'text-emerald-600'">
            {{ d.speed.todayMin === null ? '—' : todayH + 'h' }}
          </div>
          <div class="text-[11px] text-stone-400 tabular-nums">{{ t('ccd.onN').replace('{n}', String(d.speed.todayN)) }}</div>
        </div>
        <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('ccd.firstTouch7d') }}</div>
          <div class="text-[26px] font-bold tabular-nums text-stone-900 mt-1">{{ d.speed.weekMin === null ? '—' : weekH + 'h' }}</div>
          <div class="text-[11px] tabular-nums" :class="deltaClass">{{ deltaLabel }}</div>
        </div>
        <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('ccd.decidedToday') }}</div>
          <div class="text-[26px] font-bold tabular-nums text-stone-900 mt-1">{{ teamToday }}</div>
          <div class="text-[11px] text-stone-400 tabular-nums">+ {{ d.automationToday }} {{ t('ccd.byAutomation') }}</div>
        </div>
        <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
          <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t('ccd.outcomesToday') }}</div>
          <div class="text-[18px] font-bold tabular-nums mt-1.5">
            <span class="text-emerald-600">{{ d.outcomes.confirmed }}</span>
            <span class="text-[12px] text-stone-400 font-medium mx-1">{{ t('ccd.vs') }}</span>
            <span class="text-rose-600">{{ d.outcomes.cancelled }}</span>
          </div>
          <div class="text-[11px] text-stone-400">{{ t('ccd.confVsCanc') }}</div>
        </div>
      </div>

      <!-- 14-day first-touch trend -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-3">
          <Icon name="trending-up" :size="14" class="text-[var(--accent-600)]" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('ccd.trendTitle') }}</span>
          <span class="text-[11px] text-stone-400 hidden sm:inline">{{ t('ccd.trendHint') }}</span>
        </div>
        <div class="flex items-end gap-1 h-[88px]">
          <div v-for="p in d.speed.trend" :key="p.d" class="flex-1 flex flex-col items-center gap-0.5 min-w-0"
               :title="`${p.d} · ${Math.round(p.min / 60 * 10) / 10}h · ${p.n}`">
            <div class="w-full rounded-t transition-all"
                 :class="p.min > 120 ? 'bg-rose-300' : 'bg-emerald-300'"
                 :style="{ height: trendH(p.min) }" />
            <span class="text-[8.5px] text-stone-400 tabular-nums">{{ p.d.slice(8) }}</span>
          </div>
        </div>
        <div class="flex items-center gap-4 mt-2 text-[11px] text-stone-500">
          <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-300 me-1" />&le;2h</span>
          <span><span class="inline-block w-2 h-2 rounded-full bg-rose-300 me-1" />&gt;2h</span>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-4 items-start">
        <!-- who is working NOW -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <Icon name="users" :size="14" class="text-[var(--accent-600)]" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('ccd.teamTitle') }}</span>
            <span class="text-[11px] text-stone-400">{{ t('ccd.teamHint') }}</span>
          </div>
          <div v-if="d.team.length" class="overflow-x-auto">
            <table class="w-full text-[12.5px]">
              <thead>
                <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                  <th class="text-start px-4 py-2">{{ t('ccd.thAgent') }}</th>
                  <th class="text-end px-3 py-2">{{ t('ccd.thToday') }}</th>
                  <th class="text-end px-3 py-2">{{ t('ccd.thPerHour') }}</th>
                  <th class="text-end px-4 py-2">{{ t('ccd.thLast') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-stone-50">
                <tr v-for="a in d.team" :key="a.user">
                  <td class="px-4 py-2">
                    <span class="inline-flex items-center gap-1.5">
                      <span class="w-2 h-2 rounded-full" :class="a.activeNow ? 'bg-emerald-500' : 'bg-stone-300'" />
                      <span class="font-medium text-stone-800">{{ a.agent }}</span>
                    </span>
                  </td>
                  <td class="px-3 py-2 text-end font-bold tabular-nums text-stone-900">{{ a.today }}</td>
                  <td class="px-3 py-2 text-end tabular-nums text-stone-600">{{ a.perHour }}</td>
                  <td class="px-4 py-2 text-end tabular-nums text-stone-500">{{ a.lastAt }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-center text-[12.5px] text-stone-400 py-8">{{ t('ccd.teamNone') }}</div>
        </div>

        <!-- the fire -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-2.5 lg:sticky lg:top-3">
          <div class="text-[12px] font-semibold text-stone-900 flex items-center gap-2">
            <Icon name="alert-triangle" :size="14" class="text-amber-600" />{{ t('ccd.fireTitle') }}
          </div>
          <RouterLink :to="{ name: 'Workspace' }" class="ccd-fire">
            <span>{{ t('ccd.fPending') }}</span>
            <b class="tabular-nums">{{ d.fire.pending }}</b>
          </RouterLink>
          <RouterLink :to="{ name: 'Confirmation' }" class="ccd-fire" :class="d.fire.pendingLate ? 'ccd-hot' : ''">
            <span>{{ t('ccd.fLate').replace('{h}', String(d.slaH)) }}</span>
            <b class="tabular-nums">{{ d.fire.pendingLate }}</b>
          </RouterLink>
          <RouterLink :to="{ name: 'Workspace' }" class="ccd-fire" :class="d.fire.dueRetries ? 'ccd-hot' : ''">
            <span>{{ t('ccd.fDue') }}</span>
            <b class="tabular-nums">{{ d.fire.dueRetries }}</b>
          </RouterLink>
          <RouterLink :to="{ name: 'Stranded' }" class="ccd-fire" :class="d.fire.stranded ? 'ccd-hot' : ''">
            <span>{{ t('ccd.fStranded') }}</span>
            <b class="tabular-nums">{{ d.fire.stranded ?? '—' }}</b>
          </RouterLink>
          <RouterLink :to="{ name: 'Rescue' }" class="ccd-fire">
            <span>{{ t('ccd.fRescue') }}</span>
            <b class="tabular-nums">{{ d.fire.rescueOpen }}</b>
          </RouterLink>
          <RouterLink :to="{ name: 'Tickets' }" class="ccd-fire" :class="d.fire.waUnhandled > 100 ? 'ccd-hot' : ''">
            <span>{{ t('ccd.fWa') }}</span>
            <b class="tabular-nums">{{ d.fire.waUnhandled }}</b>
          </RouterLink>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();
const d = ref(null);
const loading = ref(true);
const loadError = ref("");

// ── Range KPIs (confirmation.report over the picked window) ──
const RANGES = ["today", "yest", "7d", "month", "lastMonth"];
const range = ref("month");
const r = ref(null);
const rLoading = ref(false);
const localIso = (dt) =>
  `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
const day = 86400000;
function windowFor(key) {
  const now = new Date();
  if (key === "today") { const d0 = localIso(now); return [d0, d0]; }
  if (key === "yest") { const d0 = localIso(new Date(now.getTime() - day)); return [d0, d0]; }
  if (key === "7d") return [localIso(new Date(now.getTime() - 6 * day)), localIso(now)];
  if (key === "month") return [localIso(new Date(now.getFullYear(), now.getMonth(), 1)), localIso(now)];
  return [localIso(new Date(now.getFullYear(), now.getMonth() - 1, 1)),
          localIso(new Date(now.getFullYear(), now.getMonth(), 0))];
}
// The window right before the picked one, same length — the Δ chips' baseline.
function prevWindowFor(key) {
  const now = new Date();
  if (key === "month") return windowFor("lastMonth");
  if (key === "lastMonth") {
    return [localIso(new Date(now.getFullYear(), now.getMonth() - 2, 1)),
            localIso(new Date(now.getFullYear(), now.getMonth() - 1, 0))];
  }
  const [f, t2] = windowFor(key);
  const len = Math.round((new Date(t2) - new Date(f)) / day) + 1;
  return [localIso(new Date(new Date(f).getTime() - len * day)),
          localIso(new Date(new Date(f).getTime() - day))];
}
const rp = ref(null);   // previous-window report, for the Δ chips
let rSeq = 0;
async function loadReport() {
  const seq = ++rSeq;
  rLoading.value = true;
  try {
    const [f, t2] = windowFor(range.value);
    const [pf, pt] = prevWindowFor(range.value);
    const [cur, prev] = await Promise.all([
      api("confirmation.report", { frm: f, to: t2 }),
      api("confirmation.report", { frm: pf, to: pt }).catch(() => null),
    ]);
    if (seq === rSeq) { r.value = cur; rp.value = prev; }
  } catch (e) { /* the KPI strip keeps its last good state */ }
  if (seq === rSeq) rLoading.value = false;
}
function totalsOf(rep) {
  const ag = rep?.agents || [];
  const sum = (k) => ag.reduce((a, x) => a + (Number(x[k]) || 0), 0);
  const confirm = sum("confirm"), cancel = sum("cancel");
  return { confirm, cancel, total: sum("total"), value: sum("confirmedValue"),
    rate: confirm + cancel ? Math.round((confirm * 100) / (confirm + cancel)) : null };
}
// Δ vs the previous window. Rate compares in points, the rest in percent.
function deltaOf(cur, prev, isPts = false) {
  if (cur == null || prev == null || (!prev && !isPts)) return null;
  const d2 = isPts ? cur - prev : Math.round(((cur - prev) * 100) / prev);
  return { v: d2, up: d2 > 0, txt: (d2 > 0 ? "+" : "") + d2 + (isPts ? " pt" : "%") };
}
const deltas = computed(() => {
  if (!rp.value) return {};
  const c = tot.value, p2 = totalsOf(rp.value);
  return {
    orders: deltaOf(r.value?.ordersIn?.n, rp.value?.ordersIn?.n),
    rate: deltaOf(c.rate, p2.rate, true),
    total: deltaOf(c.total, p2.total),
    value: deltaOf(c.value, p2.value),
  };
})
const stickPct = computed(() => {
  const st = r.value?.stick || [];
  const sh = st.reduce((a, x) => a + x.shipped, 0);
  const dv = st.reduce((a, x) => a + x.delivered, 0);
  return sh ? Math.round((dv * 100) / sh) : null;
});
function stickH(f2) {
  return Math.max(4, Math.round(((f2.delivered || 0) * 72) / Math.max(1, f2.shipped || 0))) + "px";
}
const tot = computed(() => {
  const ag = r.value?.agents || [];
  const sum = (k) => ag.reduce((a, x) => a + (Number(x[k]) || 0), 0);
  return { ...totalsOf(r.value), dna: sum("dna"), followup: sum("followup"),
           collected: sum("collected") };
});
// The WhatsApp flow decides a large share of every window, so the headline
// counts it — but as a named half, never blended into the human numbers.
const auto = computed(() => r.value?.automation || null);
const all = computed(() => {
  const h = tot.value, a2 = auto.value;
  const confirm = h.confirm + (a2?.confirm || 0);
  const cancel = h.cancel + (a2?.cancel || 0);
  return { confirm, cancel, total: h.total + (a2?.total || 0),
           value: h.value + (a2?.confirmedValue || 0),
           rate: confirm + cancel ? Math.round((confirm * 100) / (confirm + cancel)) : null };
});
const autoShare = computed(() =>
  all.value.total ? Math.round(((auto.value?.total || 0) * 100) / all.value.total) : null);
const collectedPct = computed(() =>
  tot.value.value ? Math.round((tot.value.collected * 100) / tot.value.value) : null);
const fMax = computed(() =>
  Math.max(1, ...(r.value?.funnel || []).map((f) => (f.confirm || 0) + (f.cancel || 0) + (f.dna || 0))));
function fH(n) { return Math.round(((n || 0) * 92) / fMax.value) + "px"; }
function fmtN(v) { return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 }); }

const todayH = computed(() => Math.round(((d.value?.speed?.todayMin || 0) / 60) * 10) / 10);
const weekH = computed(() => Math.round(((d.value?.speed?.weekMin || 0) / 60) * 10) / 10);
const teamToday = computed(() => (d.value?.team || []).reduce((a, x) => a + x.today, 0));
const deltaClass = computed(() => {
  if (d.value?.speed?.todayMin == null || d.value?.speed?.weekMin == null) return "text-stone-400";
  return d.value.speed.todayMin <= d.value.speed.weekMin ? "text-emerald-600" : "text-rose-600";
});
const deltaLabel = computed(() => {
  const s = d.value?.speed;
  if (!s || s.todayMin == null || s.weekMin == null) return t("ccd.noData");
  const diff = Math.round(((s.weekMin - s.todayMin) / 60) * 10) / 10;
  return diff >= 0 ? t("ccd.faster").replace("{h}", String(Math.abs(diff)))
    : t("ccd.slower").replace("{h}", String(Math.abs(diff)));
});
const trendMax = computed(() =>
  Math.max(60, ...(d.value?.speed?.trend || []).map((p) => p.min)));
function trendH(min) { return Math.max(4, Math.round((min / trendMax.value) * 72)) + "px"; }

async function load() {
  loading.value = true;
  try {
    d.value = await api("contact_center.speed_dashboard");
    loadError.value = "";
  } catch (e) {
    // A failed silent poll must not replace a working dashboard with an
    // error panel — only a load with nothing on screen surfaces it.
    if (!d.value) loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}
onMounted(() => { load(); loadReport(); });
const timer = setInterval(() => {
  if (document.visibilityState === "visible" && !loading.value) { load(); loadReport(); }
}, 120000);
onUnmounted(() => clearInterval(timer));
</script>

<style scoped>
.ccd-kpi {
  background: white; border-radius: 16px; padding: 16px;
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / .7);
}
.ccd-delta {
  font-size: 10.5px; font-weight: 700; border-radius: 9999px;
  padding: 1px 7px; letter-spacing: 0;
}
.ccd-up { color: rgb(5 150 105); background: rgb(209 250 229 / .7); }
.ccd-down { color: rgb(190 18 60); background: rgb(255 228 230 / .8); }
.ccd-kpi-l {
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .05em; color: rgb(168 162 158);
}
.ccd-fire {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; border-radius: 10px; font-size: 12.5px;
  color: rgb(68 64 60); background: rgb(250 250 249);
  box-shadow: inset 0 0 0 1px rgb(231 229 228 / .7);
  transition: background-color .15s;
}
.ccd-fire:hover { background: rgb(245 245 244); }
.ccd-hot {
  color: rgb(190 18 60); background: rgb(255 241 242);
  box-shadow: inset 0 0 0 1px rgb(254 205 211 / .7);
}
</style>
