<template>
  <div class="p-5 sm:p-6 space-y-4 max-w-[1280px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('cfr.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('cfr.intro') }}</p>
      </div>
      <DateRange v-model:days="days" v-model:frm="frm" v-model:to="to" @change="load" />
    </header>

    <div v-if="loading" class="space-y-3">
      <div class="h-[92px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="h-[280px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="denied" class="bg-white rounded-2xl ring-1 ring-amber-200/70 p-8 text-center">
      <Icon name="shield-alert" :size="24" class="mx-auto mb-2 text-amber-500" />
      <div class="text-[13px] text-stone-600">{{ t('cfr.denied') }}</div>
    </div>

    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[460px] mx-auto break-words">{{ loadError }}</div>
    </div>

    <template v-else-if="d">
      <!-- The money. Confirmed is a promise; collected is the fact. Measured on
           the live data, ~42% of confirmed value never arrives. -->
      <div class="grid grid-cols-2 lg:grid-cols-6 gap-3">
        <!-- How long a customer waits before a human reaches them. A MEDIAN
             over the orders somebody actually touched — the ones the bot
             closed untouched are named underneath, never averaged in. -->
        <div class="rp-kpi">
          <span class="rp-kpi-l"><Icon name="clock" :size="11" class="inline -mt-px me-1 text-amber-500" />{{ t('cfr.kTouch') }}</span>
          <span class="rp-kpi-n" :class="ft && ft.slaPct !== null ? rateColor(ft.slaPct, 70, 45, 'text') : ''">
            {{ ft && ft.median !== null ? ft.median + t('cf.hrs') : '—' }}
          </span>
          <span class="rp-kpi-s">{{ ft && ft.slaPct !== null
            ? t('cfr.kTouchSub').replace('{p}', ft.slaPct).replace('{h}', ft.slaH)
            : '' }}</span>
        </div>
        <div class="rp-kpi">
          <span class="rp-kpi-l"><Icon name="inbox" :size="11" class="inline -mt-px me-1 text-stone-400" />{{ t('cfr.kIn') }}</span>
          <span class="rp-kpi-n">{{ d.ordersIn ? d.ordersIn.n : '—' }}</span>
          <span class="rp-kpi-s">{{ d.ordersIn ? fmtMAD(d.ordersIn.value) + ' MAD' : '' }}</span>
        </div>
        <div class="rp-kpi">
          <span class="rp-kpi-l"><Icon name="check-circle" :size="11" class="inline -mt-px me-1 text-emerald-500" />{{ t('cfr.kConfirmed') }}</span>
          <span class="rp-kpi-n">{{ fmtMAD(tot.confirmedValue) }}</span>
          <span class="rp-kpi-s">{{ tot.confirm }} {{ t('cfr.kOrders') }}</span>
        </div>
        <div class="rp-kpi rp-kpi-hero">
          <span class="rp-kpi-l"><Icon name="wallet" :size="11" class="inline -mt-px me-1" />{{ t('cfr.kCollected') }}</span>
          <span class="rp-kpi-n">{{ fmtMAD(tot.collected) }}</span>
          <span class="rp-kpi-s">{{ collectedPct }}% {{ t('cfr.kOf') }}</span>
        </div>
        <div class="rp-kpi">
          <span class="rp-kpi-l"><Icon name="alert-triangle" :size="11" class="inline -mt-px me-1 text-rose-500" />{{ t('cfr.kLeak') }}</span>
          <span class="rp-kpi-n text-rose-600">{{ fmtMAD(tot.confirmedValue - tot.collected) }}</span>
          <span class="rp-kpi-s">{{ t('cfr.kLeakHint') }}</span>
        </div>
        <div class="rp-kpi">
          <span class="rp-kpi-l"><Icon name="package-check" :size="11" class="inline -mt-px me-1 text-sky-500" />{{ t('cfr.kStick') }}</span>
          <span class="rp-kpi-n">{{ tot.stick }}<span class="text-[14px] text-stone-400">%</span></span>
          <span class="rp-kpi-s">{{ tot.delivered }} / {{ tot.shipped }} {{ t('cfr.kParcels') }}</span>
        </div>
      </div>

      <!-- The automation as its own worker — separate from every human
           average, exactly like the backend keeps it. -->
      <div v-if="d.automation && d.automation.total"
           class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3 flex items-center gap-4 flex-wrap">
        <span class="text-[12px] font-semibold text-stone-900 whitespace-nowrap">
          <Icon name="bot" :size="13" class="inline -mt-px me-1.5 text-sky-500" />{{ t('cfr.autoTitle') }}
        </span>
        <span class="text-[13px] font-extrabold tabular-nums text-stone-900">{{ d.automation.total }}</span>
        <div class="flex-1 min-w-[200px] h-2 rounded-full overflow-hidden flex">
          <div class="bg-emerald-400" :style="{ width: autoPct('confirm') }" />
          <div class="bg-rose-400" :style="{ width: autoPct('cancel') }" />
          <div class="bg-amber-300" :style="{ width: autoPct('dna') }" />
          <div class="bg-stone-200 flex-1" />
        </div>
        <span class="text-[11.5px] tabular-nums text-stone-500 whitespace-nowrap">
          <b class="text-emerald-600">{{ d.automation.confirm }}</b> {{ t('cf.actConfirm') }} ·
          <b class="text-rose-500">{{ d.automation.cancel }}</b> {{ t('cf.actCancel') }} ·
          <b class="text-stone-700">{{ d.automation.dna }}</b> {{ t('cf.tabDna') }}
        </span>
        <span v-if="d.automation.confirmRate !== null"
              class="text-[11px] font-bold tabular-nums px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 ring-1 ring-sky-200/70 whitespace-nowrap">
          {{ d.automation.confirmRate }}%
        </span>
        <span class="text-[11.5px] text-stone-400 tabular-nums whitespace-nowrap">{{ fmtMAD(d.automation.confirmedValue) }} MAD</span>
      </div>

      <!-- What the automation already did before a human ever dialled. -->
      <div v-if="d.ladder && d.ladder.n" class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3 flex items-center gap-4 flex-wrap">
        <span class="text-[12px] font-semibold text-stone-900 whitespace-nowrap">
          <Icon name="send" :size="13" class="inline -mt-px me-1.5 text-sky-500" />{{ t('cfr.ladder') }}
        </span>
        <div class="flex-1 min-w-[220px] flex items-center gap-1">
          <div class="rp-bar bg-stone-200" :style="{ flex: Math.max(1, d.ladder.n - d.ladder.r1) }" :title="t('cfr.ladderNone')" />
          <div class="rp-bar bg-sky-300" :style="{ flex: Math.max(1, d.ladder.r1 - d.ladder.r2) }" :title="t('cfr.ladder1')" />
          <div class="rp-bar bg-sky-600" :style="{ flex: Math.max(1, d.ladder.r2) }" :title="t('cfr.ladder2')" />
        </div>
        <span class="text-[11.5px] text-stone-500 tabular-nums whitespace-nowrap">
          {{ d.ladder.r1 }} · {{ d.ladder.r2 }} / {{ d.ladder.n }}
        </span>
      </div>

      <!-- The three paths an order can take to Confirmed.
           Without this the leaderboard under it is unreadable, and it was
           being read as the company's confirm rate. It is not: 63% of orders
           never reach a person, and what does is the residue the other two
           paths could not settle. -->
      <div v-if="cov" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="git-branch" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('cfr.covTitle') }}</span>
          <span class="ms-auto inline-flex items-baseline gap-1.5">
            <b class="text-[18px] font-extrabold tabular-nums text-stone-900">{{ cov.all.rate }}%</b>
            <span class="text-[11px] text-stone-400 tabular-nums">
              {{ fmtN(cov.all.c) }} / {{ fmtN(cov.all.n) }}<template v-if="cov.all.valueRate"> · {{ cov.all.valueRate }}% {{ t('cfr.covByValue') }}</template>
            </span>
          </span>
        </div>
        <div class="px-4 py-3 space-y-2">
          <div v-for="p in covRows" :key="p.k" class="flex items-center gap-3">
            <span class="w-[150px] flex-shrink-0 text-[11.5px]"
                  :class="p.k === 'team' ? 'font-semibold text-stone-900' : 'text-stone-500'">{{ t(p.l) }}</span>
            <span class="flex-1 min-w-[120px] h-2 rounded-full bg-stone-100 overflow-hidden flex">
              <span class="h-full" :class="p.cls" :style="{ width: p.share + '%' }" />
            </span>
            <span class="w-[86px] text-end text-[11px] text-stone-400 tabular-nums">{{ fmtN(p.n) }} · {{ p.share }}%</span>
            <b class="w-[54px] text-end text-[12.5px] tabular-nums"
               :class="rateColor(p.rate, 85, 65, 'text')">{{ p.rate === null ? '—' : p.rate + '%' }}</b>
          </div>
          <div class="text-[10.5px] text-stone-400 pt-1">{{ t('cfr.covHint') }}</div>
        </div>
      </div>

      <!-- The leaderboard -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2 flex-wrap">
          <Icon name="users" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('cfr.agentsTitle') }}</span>
          <span class="text-[11px] text-amber-600 font-medium">{{ t('cfr.agentsScope') }}</span>
          <div class="ms-auto flex items-center gap-1">
            <button v-for="so in SORTS" :key="so.k" class="rp-sort" :class="sort === so.k ? 'rp-sort-on' : ''"
                    @click="sort = so.k">{{ t(so.l) }}</button>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[1080px] text-[12.5px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('cfr.thAgent') }}</th>
                <th class="text-end px-2 py-2.5" :title="t('cfr.thHandledHint')">{{ t('cfr.thHandled') }}</th>
                <th class="text-end px-2 py-2.5 text-emerald-600">{{ t('cf.actConfirm') }}</th>
                <th class="text-end px-2 py-2.5 text-rose-500">{{ t('cf.actCancel') }}</th>
                <th class="text-end px-2 py-2.5 text-amber-600" :title="t('cfr.thOpenHint')">{{ t('cfr.thOpen') }}</th>
                <th class="text-end px-2 py-2.5" :title="t('cfr.thOursHint')">{{ t('cfr.thOurs') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('cfr.thRate') }}</th>
                <th class="text-end px-2 py-2.5">{{ t('cfr.thResp') }}</th>
                <th class="text-end px-2 py-2.5" :title="t('cfr.thCallsHint')">{{ t('cfr.thCalls') }}</th>
                <th class="text-end px-2 py-2.5">{{ t('cfr.thAttempts') }}</th>
                <th class="text-end px-3 py-2.5 border-s border-stone-200">{{ t('cfr.thConfirmedValue') }}</th>
                <th class="text-end px-3 py-2.5">{{ t('cfr.kCollected') }}</th>
                <th class="text-end px-4 py-2.5" :title="t('cfr.thStickHint')">{{ t('cfr.thStick') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="(a, i) in sorted" :key="a.user" class="hover:bg-stone-50">
                <td class="px-4 py-2.5">
                  <span class="inline-flex items-center gap-2">
                    <span class="w-5 h-5 rounded-full text-[10px] font-bold inline-flex items-center justify-center"
                          :class="i === 0 ? 'bg-amber-100 text-amber-700 ring-1 ring-amber-300'
                                  : i === 1 ? 'bg-stone-200 text-stone-600'
                                  : i === 2 ? 'bg-orange-100 text-orange-700' : 'bg-stone-100 text-stone-500'">{{ i + 1 }}</span>
                    <span class="font-medium text-stone-900">{{ a.agent }}</span>
                    <Icon v-if="a.bulk" name="layers" :size="11" class="text-stone-300" :title="t('cfr.thBulk')" />
                    <!-- Not on this team. The row stays — the work was real
                         — but it is out of the lane's own averages, and a
                         manager's cleanup must not read as a bad agent. -->
                    <span v-if="a.inTeam === false"
                          class="text-[9.5px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full
                                 bg-stone-100 text-stone-500 ring-1 ring-stone-200"
                          :title="t('cfr.offTeamHint')">{{ a.role || t('cfr.offTeam') }}</span>
                    <!-- A cleanup day, named and dated, instead of a number
                         nobody can explain. -->
                    <span v-if="a.batchN"
                          class="text-[9.5px] font-semibold px-1.5 py-0.5 rounded-full
                                 bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                          :title="(a.batchDays || []).map((b) => b.d + ': ' + b.n).join(' · ')">
                      {{ t('cfr.batch').replace('{n}', a.batchN) }}</span>
                  </span>
                  <!-- Is this person getting better? The team chart answers
                       that for the team; without this a manager cannot tell
                       somebody improving from somebody who was always good.
                       Buckets under the server's floor draw hollow: quiet
                       reads as quiet, not as a collapse. -->
                  <span v-if="spark(a).pts.length > 1" class="flex items-center gap-1 mt-1">
                    <svg :width="spark(a).pts.length * 9" height="16" class="overflow-visible">
                      <polyline :points="spark(a).line" fill="none" stroke-width="1.5"
                                :stroke="spark(a).up ? '#059669' : spark(a).down ? '#e11d48' : '#a8a29e'"
                                stroke-linejoin="round" stroke-linecap="round" />
                      <circle v-for="(p2, pi) in spark(a).pts" :key="pi" :cx="p2.x" :cy="p2.y" r="1.6"
                              :fill="p2.solid ? (spark(a).up ? '#059669' : spark(a).down ? '#e11d48' : '#a8a29e') : '#fff'"
                              :stroke="p2.solid ? 'none' : '#d6d3d1'" stroke-width="1" />
                    </svg>
                    <span v-if="spark(a).delta !== null" class="text-[9.5px] font-bold tabular-nums"
                          :class="spark(a).up ? 'text-emerald-600' : spark(a).down ? 'text-rose-500' : 'text-stone-400'"
                          :title="t('cfr.trendHint')">
                      {{ spark(a).delta > 0 ? '+' : '' }}{{ spark(a).delta }} pt
                    </span>
                  </span>
                </td>
                <td class="px-2 py-2.5 text-end tabular-nums font-semibold text-stone-900">{{ a.handled }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums text-emerald-600 font-semibold">{{ a.confirmed || '—' }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums text-rose-500">{{ a.cancelled || '—' }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums" :class="a.open ? 'text-amber-600 font-semibold' : 'text-stone-300'">
                  {{ a.open || '—' }}<!--
                  A status none of the buckets claims. Always zero today; if
                  it ever is not, the row would stop adding up and this is
                  what says so instead of letting the rate drift silently.
               --><span v-if="a.other" class="ms-1 text-[10px] font-bold text-rose-600" :title="t('cfr.thOtherHint')">+{{ a.other }}</span>
                </td>
                <!-- Not this person's to answer for. The money rides along
                     in the tooltip because 264 of these are an item we could
                     not ship, and that is a purchasing number, not a
                     coaching one. -->
                <td class="px-2 py-2.5 text-end tabular-nums"
                    :title="a.cancelOursValue ? fmtMAD(a.cancelOursValue) : ''">
                  <span :class="a.cancelOurs ? 'text-sky-700 font-semibold' : 'text-stone-300'">{{ a.cancelOurs || '—' }}</span>
                  <!-- A cancel nobody explained: the hole in the number to
                       its left, named next to the person who can close it. -->
                  <span v-if="a.noReason" class="ms-1 text-[10px] font-bold text-amber-600"
                        :title="t('cfr.thNoReasonHint')">?{{ a.noReason }}</span>
                </td>
                <td class="px-3 py-2.5 text-end">
                  <span v-if="a.confirmRate !== null" class="inline-flex items-center justify-end gap-1.5">
                    <span class="w-[42px] h-1.5 rounded-full bg-stone-100 overflow-hidden">
                      <span class="block h-full rounded-full"
                            :class="rateColor(a.confirmRate, 80, 60, 'bg')"
                            :style="{ width: a.confirmRate + '%' }" />
                    </span>
                    <b class="tabular-nums w-[38px] text-end" :class="rateColor(a.confirmRate, 80, 60, 'text')">{{ a.confirmRate }}%</b>
                    <b v-if="a.adjRate !== null && a.adjRate !== a.confirmRate"
                       class="tabular-nums w-[44px] text-end text-[11px] text-sky-700"
                       :title="t('cfr.thAdjHint')">→{{ a.adjRate }}%</b>
                    <span v-else class="w-[44px]" />
                  </span>
                  <span v-else class="text-stone-300">—</span>
                </td>
                <!-- median, coloured by how much of it landed inside the
                     SLA — the hours alone never said whether that was good -->
                <td class="px-2 py-2.5 text-end tabular-nums"
                    :title="a.slaPct !== null && a.slaPct !== undefined
                            ? t('cfr.thRespHint').replace('{p}', a.slaPct).replace('{n}', a.touched) : ''">
                  <span v-if="a.respH !== null && a.respH !== undefined"
                        :class="a.slaPct !== null && a.slaPct !== undefined ? rateColor(a.slaPct, 70, 45, 'text') : 'text-stone-600'">
                    {{ a.respH }}{{ t('cf.hrs') }}
                  </span>
                  <span v-else class="text-stone-300">—</span>
                </td>
                <td class="px-2 py-2.5 text-end tabular-nums text-stone-600">{{ a.callsPerOrder === null ? '—' : a.callsPerOrder.toFixed(1) }}</td>
                <td class="px-2 py-2.5 text-end tabular-nums text-stone-600">{{ a.avgAttempts || '—' }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums text-stone-500 border-s border-stone-200">{{ fmtMAD(a.confirmedValue) }}</td>
                <td class="px-3 py-2.5 text-end tabular-nums font-bold text-stone-900">{{ fmtMAD(a.collected) }}</td>
                <td class="px-4 py-2.5 text-end">
                  <b v-if="a.stickRate !== null" class="tabular-nums" :class="rateColor(a.stickRate, 75, 65, 'text')">{{ a.stickRate }}%</b>
                  <span v-else class="text-stone-300">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!d.agents.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('cfr.noData') }}</div>
        <div v-else class="px-4 py-2 border-t border-stone-100 text-[10.5px] text-stone-400">{{ t('cfr.stickHint') }}</div>
      </div>

      <!-- Day by day — BOTH trails (portal comments + Desk versions), on the
           floor's clock. Fixed-width centered columns with gridlines, same
           language as the agent's own dashboard. -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-4 py-3.5">
        <div class="flex items-center gap-2 mb-2">
          <Icon name="trending-up" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('cfr.funnelTitle') }}</span>
          <span class="ms-auto flex items-center gap-3 text-[10.5px] text-stone-500">
            <span><span class="inline-block w-2 h-2 rounded-full bg-emerald-400 me-1" />{{ t('cf.actConfirm') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-rose-400 me-1" />{{ t('cf.actCancel') }}</span>
            <span><span class="inline-block w-2 h-2 rounded-full bg-amber-300 me-1" />{{ t('cf.tabDna') }}</span>
          </span>
        </div>
        <div v-if="(d.funnel || []).length" class="relative">
          <div class="absolute inset-x-0 top-[18px] bottom-[22px] pointer-events-none">
            <div v-for="g in [0, 1, 2, 3]" :key="g"
                 class="absolute inset-x-0 border-t border-dashed border-stone-100"
                 :style="{ top: g * 33.33 + '%' }" />
            <div class="absolute inset-x-0 bottom-0 border-t border-stone-200" />
          </div>
          <div class="relative flex items-end justify-center gap-2 sm:gap-3 overflow-x-auto pb-0.5"
               style="scrollbar-width: none">
            <div v-for="(f, fi) in d.funnel" :key="f.date"
                 class="group flex-none w-10 sm:w-11 flex flex-col items-center gap-1"
                 :title="`${f.date} · ${f.confirm} ${t('cf.actConfirm')} · ${f.cancel} ${t('cf.actCancel')} · ${f.dna} ${t('cf.tabDna')}`">
              <span class="text-[10px] font-bold tabular-nums transition-colors"
                    :class="bestDay && f.date === bestDay ? 'text-[var(--accent-600)]' : 'text-stone-500 group-hover:text-stone-800'">
                {{ (f.confirm + f.cancel + f.dna) || '' }}</span>
              <div class="w-7 flex flex-col justify-end rounded-md overflow-hidden rp-grow
                          transition-transform group-hover:scale-y-[1.03] origin-bottom bg-stone-50"
                   :class="bestDay && f.date === bestDay ? 'ring-2 ring-[var(--accent-400)] ring-offset-1' : ''"
                   :style="{ height: '112px', animationDelay: Math.min(fi * 30, 650) + 'ms' }">
                <div class="w-full bg-amber-300" :style="{ height: fh(f.dna) }" />
                <div class="w-full bg-rose-400" :style="{ height: fh(f.cancel) }" />
                <div class="w-full bg-emerald-400" :style="{ height: fh(f.confirm) }" />
              </div>
              <span class="text-[9.5px] tabular-nums font-medium"
                    :class="bestDay && f.date === bestDay ? 'text-[var(--accent-600)]' : 'text-stone-400'">
                {{ f.date.slice(8) }}/{{ f.date.slice(5, 7) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="text-center text-[12px] text-stone-400 py-8">{{ t('cfr.noData') }}</div>

        <div v-if="d.hours && d.hours.length" class="mt-4 pt-3 border-t border-stone-100">
          <div class="flex items-baseline gap-2 mb-2 flex-wrap">
            <span class="text-[11px] font-semibold text-stone-500">{{ t('cfr.hoursTitle') }}</span>
            <span v-if="bestHour" class="text-[10.5px] text-stone-400">{{ t('cfr.hoursHint') }}</span>
          </div>
          <!-- The bar is WHEN the team works; the line across it is whether
               the customer picked up. They are not the same hour, and the
               gap is the whole reason this strip exists. -->
          <div class="relative flex items-end gap-[2px] h-[52px]">
            <div v-for="h in d.hours" :key="h.h" class="relative flex-1 h-full flex items-end"
                 :title="`${h.h}:00 — ${h.n}` + (h.reached === null ? '' : ` · ${h.reached}% ${t('cfr.hoursReached')}`)">
              <div class="w-full rounded-t-[2px] transition-all duration-500"
                   :class="h.h === bestHour ? 'bg-emerald-400' : h.h === worstHour ? 'bg-rose-300' : h.n ? 'bg-[var(--accent-400)]' : 'bg-stone-100'"
                   :style="{ height: hh(h.n) }" />
              <span v-if="h.reached !== null"
                    class="absolute inset-x-0 h-[2px] rounded-full bg-stone-700/70"
                    :style="{ bottom: (h.reached * 0.5) + 'px' }" />
            </div>
          </div>
          <div class="flex justify-between mt-1 text-[10px] text-stone-400 tabular-nums">
            <span>{{ String(d.hours[0].h).padStart(2, '0') }}:00</span>
            <span v-if="bestHour !== null" class="text-[10px]">
              <b class="text-emerald-600">{{ String(bestHour).padStart(2, '0') }}:00 · {{ hourOf(bestHour)?.reached }}%</b>
              <span class="mx-1 text-stone-300">vs</span>
              <b class="text-rose-500">{{ String(worstHour).padStart(2, '0') }}:00 · {{ hourOf(worstHour)?.reached }}%</b>
            </span>
            <span>{{ String(d.hours[d.hours.length - 1].h).padStart(2, '0') }}:00</span>
          </div>
        </div>
      </div>

      <div class="grid lg:grid-cols-2 gap-3">
        <!-- Why orders die — the company's own vocabulary, off the Select field -->
        <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
            <Icon name="circle-x" :size="14" class="text-stone-400" />
            <span class="text-[12px] font-semibold text-stone-900">{{ t('cfr.reasonsTitle') }}</span>
            <span class="text-[11px] text-stone-400 ms-auto tabular-nums">{{ reasonTotal }}</span>
          </div>
          <div class="p-3 space-y-1.5 max-h-[340px] overflow-y-auto">
            <div v-for="r in d.reasons" :key="r.reason" class="flex items-center gap-2.5">
              <span class="text-[11.5px] text-stone-600 w-[150px] shrink-0 truncate" :title="r.reason">{{ r.reason }}</span>
              <div class="flex-1 h-4 rounded-md bg-stone-50 overflow-hidden">
                <div class="h-full rounded-md bg-gradient-to-r from-rose-300 to-rose-500 transition-all duration-700"
                     :style="{ width: reasonPct(r.n) + '%' }" />
              </div>
              <span class="text-[11.5px] font-bold text-stone-800 tabular-nums w-[46px] text-end">{{ r.n }}</span>
            </div>
            <div v-if="!d.reasons.length" class="text-center text-[12px] text-stone-400 py-6">—</div>
          </div>
        </section>

        <!-- Did what we confirmed actually arrive — and where do parcels die -->
        <div class="space-y-3">
          <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
            <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
              <Icon name="package-check" :size="14" class="text-stone-400" />
              <span class="text-[12px] font-semibold text-stone-900">{{ t('cfr.stickTrend') }}</span>
            </div>
            <div class="p-3">
              <div class="flex items-end gap-[3px] h-[64px]">
                <div v-for="sd in d.stick" :key="sd.d" class="flex-1 flex flex-col justify-end"
                     :title="`${sd.d} · ${sd.delivered}/${sd.shipped}`">
                  <div class="rounded-t-[2px] bg-stone-200 relative overflow-hidden transition-all duration-500"
                       :style="{ height: sh(sd.shipped) }">
                    <div class="absolute bottom-0 inset-x-0 bg-emerald-400"
                         :style="{ height: sd.shipped ? Math.round(sd.delivered * 100 / sd.shipped) + '%' : '0%' }" />
                  </div>
                </div>
                <div v-if="!(d.stick || []).length" class="w-full text-center text-[12px] text-stone-400 py-6">—</div>
              </div>
              <div v-if="(d.stick || []).length" class="flex justify-between mt-1 text-[10px] text-stone-400 tabular-nums">
                <span>{{ d.stick[0].d.slice(5) }}</span>
                <span>{{ d.stick[d.stick.length - 1].d.slice(5) }}</span>
              </div>
            </div>
          </section>
          <section class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
            <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
              <Icon name="map-pin" :size="14" class="text-stone-400" />
              <span class="text-[12px] font-semibold text-stone-900">{{ t('cfr.citiesTitle') }}</span>
            </div>
            <div class="p-3 space-y-1.5">
              <div v-for="c in d.cities" :key="c.city" class="flex items-center gap-2.5">
                <span class="text-[11.5px] text-stone-600 w-[120px] shrink-0 truncate" dir="auto">{{ c.city }}</span>
                <div class="flex-1 h-3.5 rounded-md bg-stone-50 overflow-hidden">
                  <div class="h-full rounded-md bg-gradient-to-r from-amber-300 to-rose-400 transition-all duration-700"
                       :style="{ width: cityPct(c) + '%' }" />
                </div>
                <span class="text-[11px] font-bold text-stone-800 tabular-nums w-[62px] text-end">{{ c.failed }} / {{ c.parcels }}</span>
              </div>
              <div v-if="!(d.cities || []).length" class="text-center text-[12px] text-stone-400 py-6">—</div>
            </div>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
import DateRange from "@/components/ui/DateRange.vue";
import { api } from "@/lib/resource";
import { fmtMAD } from "@/lib/handoffData";

// Plain counts, grouped — MAD has its own formatter and these are orders.
const fmtN = (n) => new Intl.NumberFormat().format(Math.round(n || 0));
import { useI18n } from "@/composables/useI18n";

const { t } = useI18n();

const SORTS = [
  { k: "handled", l: "cfr.thHandled" },
  { k: "collected", l: "cfr.kCollected" },
  { k: "stickRate", l: "cfr.thStick" },
  { k: "confirmRate", l: "cfr.thRate" },
  { k: "adjRate", l: "cfr.thAdj" },
];

const days = ref(30);
const frm = ref("");
const to = ref("");
const sort = ref("handled");
const d = ref(null);
// The lane's own time-to-first-human-touch. Absent on an older backend, so
// every reader checks before it prints.
const ft = computed(() => d.value?.firstTouch || null);
const loading = ref(true);
const denied = ref(false);
const loadError = ref("");

const sorted = computed(() => {
  const rows = [...(d.value?.agents || [])];
  return rows.sort((a, b) => (b[sort.value] ?? -1) - (a[sort.value] ?? -1));
});

// A rate sparkline per agent, over the server's buckets. Points below the
// server's volume floor come back with rate null: they are drawn hollow at
// the neighbouring level rather than dropped, so a gap in the line means a
// quiet week and not a missing one.
function spark(a) {
  const b = a.trend || [];
  const real = b.filter((x) => x.rate !== null && x.rate !== undefined);
  if (real.length < 2) return { pts: [], line: "", delta: null, up: false, down: false };
  const lo = Math.min(...real.map((x) => x.rate));
  const hi = Math.max(...real.map((x) => x.rate));
  const span = Math.max(1, hi - lo);
  let last = real[0].rate;
  const pts = b.map((x, i) => {
    const solid = x.rate !== null && x.rate !== undefined;
    if (solid) last = x.rate;
    return { x: i * 9, y: 14 - ((last - lo) / span) * 12, solid };
  });
  // Halves, not endpoints. The window cuts the first and last bucket mid-week,
  // so a single edge point can carry the whole delta: measured on production
  // one agent read +38.4 pt off a two-day opening bucket, against +21.5 when
  // the halves are compared. Same direction, an honest size.
  const mid = Math.floor(real.length / 2);
  const avg = (xs) => xs.reduce((x, y) => x + y.rate, 0) / xs.length;
  const delta = Math.round((avg(real.slice(mid)) - avg(real.slice(0, mid))) * 10) / 10;
  return {
    pts, line: pts.map((p2) => `${p2.x},${p2.y}`).join(" "),
    delta, up: delta >= 3, down: delta <= -3,
  };
}

// Best and worst hour to dial, over the hours that carry enough calls to
// mean anything (the server sends `reached: null` below its floor).
const hourOf = (h) => (d.value?.hours || []).find((x) => x.h === h) || null;
const ranked = computed(() =>
  (d.value?.hours || []).filter((h) => h.reached !== null && h.reached !== undefined)
    .sort((a, b) => b.reached - a.reached));
const bestHour = computed(() => (ranked.value.length ? ranked.value[0].h : null));
const worstHour = computed(() =>
  (ranked.value.length ? ranked.value[ranked.value.length - 1].h : null));

// The three paths to Confirmed. `team` is what the leaderboard below is a
// slice of — naming that on screen is the whole point of this block.
const cov = computed(() => d.value?.coverage || null);
const COV_ROWS = [
  { k: "born", l: "cfr.covBorn", cls: "bg-stone-400" },
  { k: "bot", l: "cfr.covBot", cls: "bg-sky-500" },
  { k: "team", l: "cfr.covTeam", cls: "bg-[var(--accent-600)]" },
];
const covRows = computed(() => {
  const c = cov.value;
  if (!c) return [];
  return COV_ROWS.map((r) => ({ ...r, ...(c[r.k] || { n: 0, share: 0, rate: null }) }));
});

// Section totals — the headline the manager reads first.
const tot = computed(() => {
  const a = d.value?.agents || [];
  const s = (k) => a.reduce((x, r) => x + (r[k] || 0), 0);
  const delivered = s("delivered");
  const shipped = delivered + s("failedParcels");
  return {
    confirm: s("confirmed"), confirmedValue: s("confirmedValue"),
    collected: s("collected"), delivered, shipped,
    stick: shipped ? Math.round((delivered * 100) / shipped) : 0,
  };
});
const collectedPct = computed(() =>
  tot.value.confirmedValue ? Math.round((tot.value.collected * 100) / tot.value.confirmedValue) : 0);

// Written out in full on purpose: Tailwind's JIT scans source text, so a
// class built by interpolation (`bg-${c}`) is never generated and renders
// colourless.
function rateColor(v, good, ok, kind) {
  if (kind === "bg") {
    return v >= good ? "bg-emerald-500" : v >= ok ? "bg-amber-500" : "bg-rose-500";
  }
  return v >= good ? "text-emerald-600" : v >= ok ? "text-amber-600" : "text-rose-600";
}

const reasonTotal = computed(() => (d.value?.reasons || []).reduce((s, r) => s + r.n, 0));
function reasonPct(n) {
  const max = Math.max(1, ...(d.value?.reasons || []).map((r) => r.n));
  return Math.round((n / max) * 100);
}
const funnelMax = computed(() =>
  Math.max(1, ...(d.value?.funnel || []).map((f) => f.confirm + f.cancel + f.dna)));
function fh(n) { return n ? Math.max(2, Math.round((n / funnelMax.value) * 112)) + "px" : "0px"; }
const bestDay = computed(() => {
  let best = "", n = 0;
  for (const f of d.value?.funnel || []) {
    const tot = f.confirm + f.cancel + f.dna;
    if (tot > n) { n = tot; best = f.date; }
  }
  return best;
});
function autoPct(k) {
  const a = d.value?.automation;
  if (!a || !a.total) return "0%";
  return Math.round(((a[k] || 0) * 100) / a.total) + "%";
}
const stickMax = computed(() => Math.max(1, ...(d.value?.stick || []).map((r) => r.shipped)));
function sh(n) { return n ? Math.max(4, Math.round((n / stickMax.value) * 64)) + "px" : "2px"; }
function cityPct(c) {
  const max = Math.max(1, ...(d.value?.cities || []).map((x) => x.failed));
  return Math.round((c.failed / max) * 100);
}
const hourMax = computed(() => Math.max(1, ...(d.value?.hours || []).map((h) => h.n)));
function hh(n) { return n ? Math.max(3, Math.round((n / hourMax.value) * 52)) + "px" : "2px"; }

async function load() {
  loading.value = true;
  denied.value = false;
  loadError.value = "";
  try {
    const res = await api("confirmation.report", {
      days: days.value, frm: frm.value || undefined, to: to.value || undefined,
    });
    // An older backend answers with the previous shape — say so rather than
    // rendering a half-empty page.
    if (!res || !Array.isArray(res.agents)) {
      loadError.value = t("px.set.deployHint");
      return;
    }
    d.value = res;
  } catch (e) {
    const msg = String(e.message || e);
    if (/section admin|PermissionError|403/i.test(msg)) denied.value = true;
    else loadError.value = msg;
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
.rp-kpi {
  display: flex; flex-direction: column; gap: 3px;
  background: rgb(var(--card)); border-radius: 14px; padding: 13px 15px;
  box-shadow: inset 0 0 0 1px rgb(var(--border) / 0.8);
}
.rp-kpi-hero {
  background: linear-gradient(135deg, var(--accent-50), #fff);
  box-shadow: inset 0 0 0 1px var(--accent-200);
}
.rp-kpi-l { font-size: 10.5px; font-weight: 700; color: rgb(var(--text3)); text-transform: uppercase; letter-spacing: .04em; }
.rp-kpi-n { font-size: 21px; font-weight: 800; color: rgb(var(--text)); font-variant-numeric: tabular-nums; line-height: 1.1; }
.rp-kpi-s { font-size: 10.5px; color: rgb(var(--text4)); font-variant-numeric: tabular-nums; }
.rp-bar { height: 8px; border-radius: 3px; transition: flex .6s ease; }
.rp-sort {
  height: 24px; padding: 0 8px; border-radius: 7px;
  font-size: 10.5px; font-weight: 700; color: rgb(var(--text3));
  transition: all .12s ease;
}
.rp-sort:hover { background: rgb(var(--bg)); }
.rp-sort-on { background: rgb(28 25 23); color: white; }
.rp-grow { animation: rpGrow .45s cubic-bezier(.2, .7, .3, 1) backwards; }
@keyframes rpGrow { from { transform: scaleY(0); } to { transform: scaleY(1); } }
</style>
