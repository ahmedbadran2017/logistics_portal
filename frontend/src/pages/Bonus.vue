<template>
  <!-- The logistics bonus scheme is not switched on yet (Ahmed 2026-09-11):
       the floor sees an honest 'coming soon' instead of a board of zeros
       that reads like they earned nothing. Managers still see everything. -->
  <div v-if="floorComingSoon" class="p-5 sm:p-6 max-w-[560px] mx-auto">
    <div class="mt-10 rounded-3xl bg-white ring-1 ring-stone-200/70 p-10 text-center">
      <div class="w-16 h-16 mx-auto rounded-2xl flex items-center justify-center"
           :style="{ background: 'var(--accent-50)' }">
        <Icon name="wallet" :size="28" class="text-[var(--accent-600)]" />
      </div>
      <h1 class="text-[19px] font-bold text-stone-900 mt-4">{{ t('bn.soonTitle') }}</h1>
      <p class="text-[13px] text-stone-500 mt-2 leading-relaxed">{{ t('bn.soonBody') }}</p>
      <span class="inline-flex items-center gap-1.5 mt-5 text-[11.5px] font-bold uppercase tracking-wide px-3 py-1.5 rounded-full"
            :style="{ background: 'var(--accent-50)', color: 'var(--accent-700)' }">
        <span class="w-2 h-2 rounded-full animate-pulse" :style="{ background: 'var(--accent-500)' }" />
        {{ t('bn.soonChip') }}
      </span>
      <div class="mt-5">
        <button class="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 ring-stone-200 bg-white text-stone-700 hover:bg-stone-50"
                @click="openRules()"><Icon name="list-checks" :size="14" />{{ t('an.rules') }}</button>
      </div>
    </div>
  </div>

  <div v-else class="p-5 sm:p-6 space-y-4 max-w-[1000px] mx-auto">
    <header class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-bold text-stone-900 tracking-tight">{{ t('bn.title') }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t('bn.intro') }}</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <button class="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 ring-stone-200 bg-white text-stone-700 hover:bg-stone-50"
                @click="openRules()"><Icon name="list-checks" :size="14" />{{ t('an.rules') }}</button>
        <!-- group switch (manager only — the server sends one group otherwise) -->
        <div v-if="(d?.groups || []).length > 1" class="flex items-center gap-1">
          <button v-for="g in d.groups" :key="g"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                  :class="group === g ? 'bg-violet-600 text-white ring-violet-600' : 'bg-white text-stone-600 ring-stone-200'"
                  @click="group = g; load()">{{ t('bn.grp_' + g) }}</button>
        </div>
        <div class="flex items-center gap-1">
          <button v-for="m in months" :key="m.key"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 transition-colors"
                  :class="month === m.key ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200'"
                  @click="month = m.key; load()">{{ m.label }}</button>
        </div>
      </div>
    </header>

    <!-- Who has read the launch notice. At the end of the month "nobody told
         me" is the objection a manager cannot answer without this. -->
    <div v-if="ackStat" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-4">
      <div class="flex items-center gap-3 flex-wrap">
        <span class="inline-flex w-9 h-9 rounded-xl items-center justify-center bg-emerald-50 text-emerald-600">
          <Icon name="check" :size="18" />
        </span>
        <div class="flex-1 min-w-[200px]">
          <div class="text-[13px] font-semibold text-stone-900">{{ t('an.ackTitle') }}</div>
          <div class="text-[12px] text-stone-500 tabular-nums">
            {{ ackStat.acked }} / {{ ackStat.total }} {{ t('an.ackRead') }}
          </div>
        </div>
        <div class="h-2 w-40 rounded-full bg-stone-100 overflow-hidden">
          <div class="h-full rounded-full bg-emerald-500 transition-all duration-700"
               :style="{ width: (ackStat.total ? 100 * ackStat.acked / ackStat.total : 0) + '%' }" />
        </div>
        <button v-if="ackPending.length" class="text-[12px] font-medium text-stone-500 hover:text-stone-900"
                @click="ackOpen = !ackOpen">{{ ackOpen ? t('an.ackHide') : t('an.ackShow') }}</button>
      </div>
      <div v-if="ackOpen && ackPending.length" class="mt-3 flex flex-wrap gap-1.5">
        <span v-for="r in ackPending" :key="r.user"
              class="text-[11.5px] rounded-md px-2 py-1 bg-amber-50 text-amber-800 ring-1 ring-amber-200/60">
          {{ r.name }}<span v-if="r.role" class="text-amber-600/80"> · {{ r.role }}</span>
        </span>
      </div>
    </div>

    <!-- The CC scheme isn't approved yet (Ahmed 2026-08-28): agents see a
         promise, not a leaderboard. Managers and section admins keep the full
         page to finish designing it; view-as renders the agent truth. -->
    <div v-if="comingSoon" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-12 text-center overflow-hidden">
      <!-- coins raining into the wallet — the money is on its way -->
      <div class="bn-scene mx-auto">
        <span class="bn-coin bn-c1"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="rgb(252 211 77)" stroke="rgb(217 119 6)" stroke-width="1.6"/><circle cx="12" cy="12" r="5.5" fill="none" stroke="rgb(217 119 6)" stroke-width="1.4"/></svg></span>
        <span class="bn-coin bn-c2"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="rgb(252 211 77)" stroke="rgb(217 119 6)" stroke-width="1.6"/><circle cx="12" cy="12" r="5.5" fill="none" stroke="rgb(217 119 6)" stroke-width="1.4"/></svg></span>
        <span class="bn-coin bn-c3"><svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="rgb(252 211 77)" stroke="rgb(217 119 6)" stroke-width="1.6"/><circle cx="12" cy="12" r="5.5" fill="none" stroke="rgb(217 119 6)" stroke-width="1.4"/></svg></span>
        <span class="bn-wallet inline-flex w-16 h-16 rounded-2xl items-center justify-center bg-amber-50 text-amber-500 ring-1 ring-amber-200/60">
          <Icon name="wallet" :size="30" />
        </span>
      </div>
      <div class="text-[17px] font-bold text-stone-900 mt-4">{{ t('bn.soonTitle') }}</div>
      <div class="text-[12.5px] text-stone-500 mt-1.5 max-w-[440px] mx-auto leading-relaxed">{{ t('bn.soonBody') }}</div>
      <!-- the "loading the money" shimmer -->
      <div class="h-2 w-[220px] mx-auto mt-5 rounded-full bg-stone-100 overflow-hidden">
        <div class="bn-shimmer h-full w-1/3 rounded-full" />
      </div>
      <div class="text-[11px] font-semibold text-amber-600 mt-2">{{ t('bn.soonFun') }}</div>
    </div>

    <div v-else-if="loading" class="space-y-2">
      <div class="h-[110px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
      <div class="h-[220px] rounded-2xl bg-stone-100 ring-1 ring-stone-200/60 animate-pulse" />
    </div>

    <div v-else-if="loadError" class="bg-white rounded-2xl ring-1 ring-rose-200/70 p-8 text-center">
      <Icon name="alert-triangle" :size="24" class="mx-auto mb-2 text-rose-500" />
      <div class="text-[13px] font-semibold text-stone-800">{{ t('cf.loadFail') }}</div>
      <div class="text-[11.5px] text-stone-400 font-mono mt-1 max-w-[420px] mx-auto break-words">{{ loadError }}</div>
    </div>

    <!-- The floor's month is under review (Ahmed 2026-11-02): until an
         approver publishes it the server sends no points and no amount, so
         this card is all there is to show. -->
    <div v-else-if="d && d.pending" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-10 text-center">
      <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-amber-50 text-amber-500 ring-1 ring-amber-200/60 mb-2.5">
        <Icon name="clock" :size="22" />
      </span>
      <div class="text-[14px] font-semibold text-stone-900">{{ t('bn.apPendingTitle') }}</div>
      <div class="text-[12.5px] text-stone-500 mt-1 max-w-[440px] mx-auto leading-relaxed">{{ t('bn.apPendingBody') }}</div>
    </div>

    <!-- roles whose work has no per-person source yet -->
    <div v-else-if="d && !d.available" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-10 text-center">
      <span class="inline-flex w-12 h-12 rounded-2xl items-center justify-center bg-stone-100 text-stone-400 mb-2.5">
        <Icon name="wallet" :size="22" />
      </span>
      <div class="text-[13.5px] font-semibold text-stone-800">{{ t('bn.noScheme') }}</div>
      <div class="text-[12px] text-stone-400 mt-0.5 max-w-[420px] mx-auto">{{ t('bn.noSchemeHint') }}</div>
    </div>

    <template v-else-if="d">
      <!-- The approver's desk: the computed amount beside the amount that will
           be paid. Nothing here reaches the team until "Approve". -->
      <div v-if="d.approval" class="bg-white rounded-2xl ring-1 overflow-hidden"
           :class="d.approved ? 'ring-emerald-200' : 'ring-amber-200'">
        <div class="px-4 py-3 flex items-center gap-3 flex-wrap"
             :class="d.approved ? 'bg-emerald-50' : 'bg-amber-50'">
          <Icon :name="d.approved ? 'check' : 'shield-alert'" :size="16"
                :class="d.approved ? 'text-emerald-600' : 'text-amber-600'" />
          <div class="flex-1 min-w-[220px]">
            <div class="text-[13px] font-bold text-stone-900">
              {{ d.approved ? t('bn.apApproved') : t('bn.apTitle') }}
              <span class="font-normal text-stone-500">· {{ d.month }} · {{ t('bn.grp_' + d.group) }}</span>
            </div>
            <div class="text-[11.5px] text-stone-600 mt-0.5">
              <template v-if="d.approval.by">{{ t('bn.apBy').replace('{u}', d.approval.by).replace('{at}', d.approval.at || '') }} · </template>
              {{ d.approved ? t('bn.apLive') : t('bn.apHidden') }}
            </div>
          </div>
          <span class="text-[12px] text-stone-600 tabular-nums">{{ t('bn.apTotal') }} <b class="text-stone-900">{{ apTotal }}</b> {{ d.money?.currency || 'MAD' }}</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[480px] text-[12.5px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2">{{ t('cfr.thAgent') }}</th>
                <th class="text-end px-3 py-2">{{ t('bn.thPoints') }}</th>
                <th class="text-end px-3 py-2">{{ t('bn.apSystem') }}</th>
                <th v-if="apHasSuggest" class="text-end px-3 py-2">{{ t('bn.apSuggest') }}</th>
                <th class="text-end px-4 py-2">{{ t('bn.apFinal') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="r in apRows" :key="r.user">
                <td class="px-4 py-2">
                  <div class="font-medium text-stone-900">{{ r.agent }}</div>
                  <div class="text-[10.5px] text-stone-400">{{ r.user }}</div>
                </td>
                <td class="px-3 py-2 text-end tabular-nums text-stone-500">{{ r.points ?? '—' }}</td>
                <td class="px-3 py-2 text-end tabular-nums text-stone-500">{{ r.system ?? '—' }}</td>
                <td v-if="apHasSuggest" class="px-3 py-2 text-end tabular-nums" :title="r.work">
                  <div class="font-semibold text-violet-700">{{ r.suggested ?? '—' }}</div>
                  <div v-if="r.hours != null" class="text-[10.5px] text-stone-400">{{ r.hours }} h</div>
                </td>
                <td class="px-4 py-2 text-end">
                  <input v-model.number="r.final" type="number" min="0" step="10" :disabled="d.approved"
                         class="w-[96px] h-8 px-2 rounded-lg ring-1 ring-stone-200 text-end tabular-nums font-bold text-stone-900 disabled:bg-stone-50 disabled:text-stone-500"
                         @input="apDirty = true" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!d.approved" class="px-4 py-3 border-t border-stone-100 space-y-2.5">
          <div v-if="apHasSuggest" class="flex items-center gap-2 flex-wrap text-[11.5px] text-stone-500">
            <span class="flex-1 min-w-[220px]">{{ t('bn.apSuggestHint').replace('{r}', String(d.approval.suggestion.rate)).replace('{h}', String(d.approval.suggestion.hours)) }}</span>
            <button class="h-7 px-2.5 rounded-lg font-semibold ring-1 ring-stone-200 bg-white text-stone-700 hover:bg-stone-50"
                    @click="fillAp('system')">{{ t('bn.apFillSystem') }}</button>
            <button class="h-7 px-2.5 rounded-lg font-semibold ring-1 ring-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-100"
                    @click="fillAp('suggested')">{{ t('bn.apFillSuggest') }}</button>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <input v-model.trim="apAdd" type="email" :placeholder="t('bn.apAddPh')"
                   class="flex-1 min-w-[200px] h-8 px-2.5 rounded-lg ring-1 ring-stone-200 text-[12px]"
                   @keyup.enter="addApRow" />
            <button class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 ring-stone-200 bg-white text-stone-700 hover:bg-stone-50"
                    :disabled="!apAdd" @click="addApRow">{{ t('bn.apAdd') }}</button>
          </div>
          <textarea v-model="apNote" rows="2" :placeholder="t('bn.apNotePh')"
                    class="w-full px-2.5 py-2 rounded-lg ring-1 ring-stone-200 text-[12px]" @input="apDirty = true" />
          <div class="flex items-center gap-2 justify-end flex-wrap">
            <button class="h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 ring-stone-200 bg-white text-stone-700 hover:bg-stone-50"
                    :disabled="apSaving" @click="saveApproval('draft')">{{ t('bn.apDraft') }}</button>
            <button class="h-8 px-3 rounded-lg text-[12px] font-semibold bg-emerald-600 text-white hover:bg-emerald-700"
                    :disabled="apSaving" @click="saveApproval('approved')">{{ t('bn.apApprove') }}</button>
          </div>
        </div>
        <div v-else class="px-4 py-3 border-t border-stone-100 flex items-center gap-2 flex-wrap">
          <div v-if="d.approval.note" class="flex-1 text-[12px] text-stone-600 whitespace-pre-line">{{ d.approval.note }}</div>
          <button class="ms-auto h-8 px-3 rounded-lg text-[12px] font-semibold ring-1 ring-stone-200 bg-white text-stone-700 hover:bg-stone-50"
                  :disabled="apSaving" @click="reopenApproval">{{ t('bn.apReopen') }}</button>
        </div>
      </div>

      <!-- September was the trial: points so people can see how the scheme
           reads their work, no money (Ahmed 2026-09-30). -->
      <div v-if="d.trial" class="rounded-2xl px-4 py-3 flex items-start gap-3 bg-amber-50 ring-1 ring-amber-200/70">
        <Icon name="info" :size="16" class="text-amber-600 mt-0.5 flex-shrink-0" />
        <div class="text-[12.5px] text-amber-900 leading-relaxed">{{ t('an.trialBanner') }}</div>
      </div>
      <!-- my card. Only for someone actually ON this board: a manager opens
           the page to read the team, and a permanent "0 pts / 250 · 0% of
           target" card about themselves is noise at best and, at 0%,
           reads like something is broken. -->
      <div v-if="d.me.actions || d.me.points || !isManager" class="bn-hero rounded-2xl p-5">
        <div class="flex items-center gap-4 flex-wrap">
          <span class="bn-ico"><Icon name="wallet" :size="20" /></span>
          <div class="flex-1 min-w-[220px]">
            <div class="flex items-baseline gap-2 flex-wrap">
              <template v-if="d.me.pay">
                <span class="text-[30px] font-extrabold text-stone-900 tabular-nums leading-none">{{ d.me.pay.total }}</span>
                <span class="text-[12px] font-semibold text-stone-500">{{ d.me.pay.currency }}</span>
                <span class="text-[11px] text-stone-400 tabular-nums">· {{ nPoints }} {{ t('bn.pts') }} / {{ d.target }}</span>
              </template>
              <template v-else>
                <span class="text-[30px] font-extrabold text-stone-900 tabular-nums leading-none">{{ nPoints }}</span>
                <span class="text-[12px] text-stone-500">{{ t('bn.pts') }} / {{ d.target }}</span>
              </template>
              <span v-if="d.me.rank" class="ms-1 text-[11px] font-bold rounded-full px-2.5 py-0.5"
                    :class="d.me.rank === 1 ? 'text-amber-700 bg-amber-50 ring-1 ring-amber-200' : 'text-stone-600 bg-stone-100 ring-1 ring-stone-200'">
                #{{ d.me.rank }}
              </span>
            </div>
            <!-- A lane whose weights have not been priced yet has no target,
                 and "0% of target" under a full month's work reads as failure
                 rather than as "we are still measuring". Say the true thing. -->
            <template v-if="d.target">
              <div class="h-2 rounded-full bg-stone-100 overflow-hidden mt-2.5 max-w-[420px]">
                <div class="h-full rounded-full transition-all duration-700"
                     :class="d.me.points >= d.target ? 'bg-emerald-500' : 'bg-amber-500'"
                     :style="{ width: pct + '%' }" />
              </div>
              <div class="text-[11px] text-stone-400 mt-1.5 tabular-nums">
                {{ d.me.actions }} {{ t('bn.actions') }} · {{ pct }}% {{ t('bn.ofTarget') }}
              </div>
            </template>
            <div v-else class="text-[11px] text-stone-400 mt-1.5 tabular-nums">
              {{ d.me.actions }} {{ t('bn.actions') }} · {{ t('bn.measuring') }}
            </div>
            <!-- how the payout was reached — never a black box -->
            <div v-if="d.me.pay" class="flex flex-wrap items-center gap-1.5 mt-2">
              <span class="bn-part">{{ t('bn.pBase') }} <b class="tabular-nums">{{ d.me.pay.base }}</b></span>
              <span v-if="d.me.pay.streakPct" class="bn-part bn-part-good">
                <Icon name="zap" :size="10" />{{ d.me.pay.streakDays }}{{ t('cf.days') }} +{{ d.me.pay.streakPct }}%
              </span>
              <span v-if="d.me.pay.kicker" class="bn-part bn-part-good">
                <Icon name="users" :size="10" />{{ t('bn.pKicker') }} +{{ d.me.pay.kicker }}
              </span>
              <span v-if="d.me.pay.gatePct !== null" class="bn-part"
                    :class="d.me.pay.gatePass ? 'bn-part-good' : 'bn-part-bad'">
                <Icon :name="d.me.pay.gatePass ? 'check-circle' : 'shield-alert'" :size="10" />
                {{ t('bn.pGate') }} {{ d.me.pay.gatePct }}%
              </span>
              <span v-if="d.me.pay.capped" class="bn-part bn-part-warn">
                <Icon name="alert-triangle" :size="10" />{{ t('bn.pCapped') }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- How the money happens — the recipe, told with the agent's own
           live numbers so it is a mirror, not a poster. Numbers come from
           the SAME endpoint as the receipt; prose never restates a figure
           that settings could change under it. -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <button type="button" class="w-full px-4 py-3 flex items-center gap-2.5 hover:bg-stone-50 transition-colors"
                @click="toggleHow">
          <span class="w-8 h-8 rounded-lg grid place-items-center bg-amber-100 text-amber-600 shrink-0">
            <Icon name="sparkles" :size="15" />
          </span>
          <span class="text-[13px] font-bold text-stone-900 flex-1 text-start">{{ t('bn.howTitle') }}</span>
          <span class="text-[11.5px] font-semibold text-[var(--accent-600)]">
            {{ howOpen ? t('bn.howClose') : t('bn.howOpen') }}
          </span>
          <Icon :name="howOpen ? 'chevron-up' : 'chevron-down'" :size="14" class="text-stone-400" />
        </button>

        <div v-if="howOpen" class="px-4 pb-4">
          <div v-if="howLoading" class="py-6 text-center text-[12px] text-stone-400">…</div>
          <template v-else>
            <div class="grid sm:grid-cols-2 gap-3">
              <div v-for="(st, si) in howSteps" :key="si"
                   class="bn-how rounded-xl p-3.5 ring-1 ring-stone-200/70"
                   :style="{ animationDelay: si * 90 + 'ms' }">
                <div class="flex items-center gap-2.5">
                  <span class="bn-how-n">{{ si + 1 }}</span>
                  <span class="w-8 h-8 rounded-lg grid place-items-center shrink-0" :class="st.tint">
                    <Icon :name="st.icon" :size="15" />
                  </span>
                  <span class="text-[12.5px] font-bold text-stone-900">{{ st.title }}</span>
                </div>
                <p class="text-[11.5px] text-stone-500 leading-relaxed mt-2">{{ st.body }}</p>
                <div v-if="st.live" class="mt-2.5 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1
                            text-[11px] font-bold tabular-nums" :class="st.liveTint">
                  <Icon :name="st.liveIcon" :size="10" />{{ st.live }}
                </div>
              </div>
            </div>
            <div class="mt-3 rounded-lg px-3.5 py-2.5 text-[11.5px] font-semibold flex items-center gap-2"
                 :class="howScheme?.moneyOn ? 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200/70'
                                            : 'bg-sky-50 text-sky-800 ring-1 ring-sky-200/70'">
              <Icon name="wallet" :size="13" class="shrink-0" />
              <span>{{ howScheme?.moneyOn
                  ? t('bn.howMoney').replace('{v}', String(howScheme.perPoint)).replace(/\{c\}/g, howScheme.currency).replace('{cap}', String(howScheme.cap))
                  : t('bn.howMoneyOff') }}</span>
            </div>
            <div class="mt-2 flex items-center gap-1.5 text-[10.5px] text-stone-400">
              <Icon name="info" :size="10" class="shrink-0" /><span>{{ t('bn.howFair') }}</span>
            </div>
          </template>
        </div>
      </div>

      <!-- team kicker: everyone gets it, or nobody does -->
      <div v-if="d.money?.kickerOn" class="rounded-2xl p-4 flex items-center gap-3.5 flex-wrap"
           :class="d.money.kickerHit ? 'bn-kick-on' : 'bn-kick-off'">
        <span class="w-10 h-10 rounded-xl grid place-items-center text-white shrink-0"
              :class="d.money.kickerHit ? 'bg-emerald-500' : 'bg-amber-500'">
          <Icon name="users" :size="19" />
        </span>
        <div class="flex-1 min-w-[200px]">
          <div class="text-[13.5px] font-bold text-stone-900">
            {{ t('bn.kickTitle') }} · +{{ d.money.kickerAmount }} {{ d.money.currency }}
          </div>
          <div class="text-[12px] text-stone-600 mt-0.5">
            {{ d.money.kickerHit ? t('bn.kickHit') : t('bn.kickMiss') }}
            <b class="tabular-nums">{{ d.money.sameday }}%</b> / {{ d.money.kickerTargetPct }}%
          </div>
        </div>
        <div class="w-[120px] shrink-0">
          <div class="h-2 rounded-full bg-white/70 overflow-hidden">
            <div class="h-full rounded-full transition-all duration-700"
                 :class="d.money.kickerHit ? 'bg-emerald-500' : 'bg-amber-500'"
                 :style="{ width: Math.min(100, (d.money.sameday / Math.max(1, d.money.kickerTargetPct)) * 100) + '%' }" />
          </div>
        </div>
      </div>

      <!-- leaderboard -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center gap-2">
          <Icon name="trending-up" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ d.scoped ? t('bn.myPoints') : t('cco.leaderboard') }}</span>
          <span class="text-[11px] text-stone-400 tabular-nums">{{ d.month }} · {{ t('bn.grp_' + d.group) }}</span>
          <span v-if="d.scoped && d.me?.rank" class="text-[11px] text-stone-400 tabular-nums">· {{ t('bn.rankOf').replace('{r}', String(d.me.rank)).replace('{n}', String(d.of || '')) }}</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[560px] text-[12.5px]">
            <thead>
              <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">{{ t('cfr.thAgent') }}</th>
                <th v-for="c in d.cols" :key="c" class="text-end px-3 py-2.5">{{ t(c) }}</th>
                <th class="text-end px-4 py-2.5">{{ t('bn.thPoints') }}</th>
                <th v-if="d.money?.on" class="text-end px-4 py-2.5">{{ t('bn.thPay') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-stone-100">
              <template v-for="(a, i) in d.agents" :key="a.user">
              <tr class="hover:bg-stone-50 cursor-pointer"
                  :class="a.user === d.meUser ? 'bg-amber-50/40' : ''"
                  @click="toggleBreakdown(a.user)">
                <td class="px-4 py-2.5">
                  <span class="inline-flex items-center gap-2">
                    <span class="w-5 h-5 rounded-full text-[10px] font-bold inline-flex items-center justify-center"
                          :class="(d.scoped ? (d.me?.rank || 1) === 1 : i === 0) ? 'bg-amber-100 text-amber-700' : 'bg-stone-100 text-stone-500'">{{ d.scoped ? (d.me?.rank || 1) : i + 1 }}</span>
                    <span class="font-medium text-stone-900">{{ a.agent }}</span>
                    <Icon :name="breakdownFor === a.user ? 'chevron-up' : 'chevron-down'" :size="11" class="text-stone-300" />
                  </span>
                </td>
                <td v-for="(v, ci) in a.cols" :key="ci" class="px-3 py-2.5 text-end tabular-nums text-stone-600">
                  {{ v || '—' }}
                </td>
                <td class="px-4 py-2.5 text-end">
                  <div class="inline-flex items-center gap-2">
                    <div class="w-[56px] h-1.5 rounded-full bg-stone-100 overflow-hidden">
                      <div class="h-full rounded-full transition-all duration-700"
                           :class="a.points >= d.target ? 'bg-emerald-500' : 'bg-amber-500'"
                           :style="{ width: Math.min(100, a.points * 100 / Math.max(1, d.target)) + '%' }" />
                    </div>
                    <span class="tabular-nums font-bold text-stone-900 w-[52px] text-end">{{ a.points }}</span>
                  </div>
                </td>
                <td v-if="d.money?.on" class="px-4 py-2.5 text-end">
                  <span class="tabular-nums font-bold text-stone-900">{{ a.pay?.total ?? '—' }}</span>
                  <span v-if="a.prize" class="ms-1.5 text-[10px] font-bold text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-full px-1.5 py-0.5">
                    +{{ a.prize }}
                  </span>
                  <Icon v-if="a.pay && !a.pay.gatePass" name="shield-alert" :size="11"
                        class="inline ms-1 text-rose-500" :title="t('bn.pGateFail')" />
                </td>
              </tr>
              <!-- the receipt: HOW those points happened -->
              <tr v-if="breakdownFor === a.user">
                <td :colspan="(d.cols?.length || 1) + 2 + (d.money?.on ? 1 : 0)" class="px-4 pb-3 pt-0 bg-stone-50/50">
                  <div v-if="breakdownLoading" class="text-[12px] text-stone-400 py-3 text-center">…</div>
                  <div v-else-if="breakdown" class="pt-2 space-y-1">
                    <div v-for="l in breakdown.lines" :key="l.key" class="flex items-center gap-2 text-[12px] tabular-nums">
                      <span class="text-stone-600 flex-1">{{ t('bn.k_' + l.key.replace('.', '_'), l.key) }}</span>
                      <span class="text-stone-400">{{ l.count }} × {{ l.each }}</span>
                      <span class="font-bold w-[60px] text-end"
                            :class="l.subtotal < 0 ? 'text-rose-600' : 'text-stone-800'">{{ l.subtotal }}</span>
                    </div>
                    <!-- the ship lane's outcomes are already lines above -->
                    <div v-if="breakdown.outcomes !== false" class="flex items-center gap-2 text-[12px] tabular-nums">
                      <span class="text-stone-600 flex-1">{{ t('bn.k_delivered') }}</span>
                      <span class="text-stone-400">{{ breakdown.delivered }} × {{ breakdown.deliveredEach }}</span>
                      <span class="font-bold text-emerald-600 w-[60px] text-end">{{ breakdown.deliveredPts }}</span>
                    </div>
                    <!-- the deduction: the one negative in the scheme, and the
                         receipt says so in red rather than hiding it in a net -->
                    <div v-if="breakdown.returned && breakdown.returnedEach"
                         class="flex items-center gap-2 text-[12px] tabular-nums">
                      <span class="text-rose-600 flex-1">{{ t('bn.k_failed') }}</span>
                      <span class="text-rose-400">{{ breakdown.returned }} × {{ breakdown.returnedEach }}</span>
                      <span class="font-bold text-rose-600 w-[60px] text-end">{{ breakdown.returnedPts }}</span>
                    </div>
                    <div class="flex items-center gap-2 text-[12px] tabular-nums pt-1 border-t border-stone-200/70">
                      <span class="text-stone-500 flex-1">{{ t('bn.kStreak').replace('{n}', String(breakdown.streakDays)) }}</span>
                      <span class="font-extrabold text-stone-900 w-[60px] text-end">{{ breakdown.total }}</span>
                    </div>
                    <div v-if="!breakdown.lines.length && !breakdown.delivered" class="text-[11.5px] text-stone-400 text-center py-1">{{ t('bn.kEmpty') }}</div>
                  </div>
                </td>
              </tr>
              </template>
            </tbody>
            <tfoot v-if="d.money?.on && d.money.pool !== null">
              <tr class="border-t border-stone-200 bg-stone-50/60 text-[12.5px] font-bold">
                <td class="px-4 py-2.5" :colspan="(d.cols?.length || 1) + 2">{{ t('bn.pool') }}</td>
                <td class="px-4 py-2.5 text-end text-stone-900 tabular-nums">
                  {{ d.money.pool }} <span class="text-[10px] font-normal text-stone-400">{{ d.money.currency }}</span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
        <div v-if="!d.agents.length" class="text-center text-[12.5px] text-stone-400 py-8">{{ t('cfr.noData') }}</div>
      </div>

      <!-- scheme editor (manager) -->
      <div v-if="scheme?.canEdit" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
        <div class="flex items-center gap-2">
          <Icon name="settings" :size="14" class="text-stone-400" />
          <span class="text-[12px] font-semibold text-stone-900">{{ t('bn.schemeTitle') }}</span>
          <span class="text-[11px] text-stone-400">{{ t('bn.schemeHint') }}</span>
        </div>
        <div class="flex items-center gap-4 flex-wrap">
          <label v-for="g in scheme.groups" :key="g" class="inline-flex items-center gap-2 text-[12px] text-stone-600">
            {{ t('bn.target') }} — {{ t('bn.grp_' + g) }}
            <input v-model.number="scheme.targets[g]" type="number" min="1"
                   class="w-24 h-9 ps-3 rounded-lg ring-1 ring-stone-200 text-[12.5px] tabular-nums focus:outline-none"
                   @input="dirty = true" />
          </label>
        </div>

        <!-- MONEY. Nothing here is a decision the code gets to make. -->
        <div v-if="scheme.money" class="rounded-xl bg-amber-50/40 ring-1 ring-amber-200/60 p-3.5 space-y-3">
          <label class="flex items-center gap-2.5 cursor-pointer">
            <button type="button" role="switch" :aria-checked="!!scheme.money.on"
                    class="relative w-11 h-6 rounded-full transition-colors shrink-0"
                    :class="scheme.money.on ? 'bg-amber-500' : 'bg-stone-300'"
                    @click="scheme.money.on = scheme.money.on ? 0 : 1; dirty = true">
              <span class="absolute top-0.5 start-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform"
                    :class="scheme.money.on ? 'ltr:translate-x-5 rtl:-translate-x-5' : 'translate-x-0'" />
            </button>
            <span>
              <span class="block text-[12.5px] font-bold text-stone-900">{{ t('bn.mTitle') }}</span>
              <span class="block text-[11px] text-stone-500">{{ t('bn.mHint') }}</span>
            </span>
          </label>

          <template v-if="scheme.money.on">
            <div class="grid sm:grid-cols-2 gap-x-4 gap-y-2.5 pt-1">
              <label v-for="g in scheme.groups" :key="'pp' + g" class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
                <span>{{ t('bn.mPerPoint') }} — {{ t('bn.grp_' + g) }}</span>
                <input v-model.number="scheme.money.perPoint[g]" type="number" min="0" step="0.5"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
              </label>
              <label v-for="g in scheme.groups" :key="'cap' + g" class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
                <span>{{ t('bn.mCap') }} — {{ t('bn.grp_' + g) }}</span>
                <input v-model.number="scheme.money.monthlyCap[g]" type="number" min="0" step="100"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
              </label>
              <label class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
                <span>{{ t('bn.mStreakStep') }}</span>
                <input v-model.number="scheme.money.streakStepPct" type="number" min="0" max="50"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
              </label>
              <label class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
                <span>{{ t('bn.mStreakCap') }}</span>
                <input v-model.number="scheme.money.streakCapPct" type="number" min="0" max="200"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
              </label>
            </div>

            <!-- quality gate, per group -->
            <div class="pt-2 border-t border-amber-200/60 space-y-2">
              <div class="text-[11.5px] font-bold text-stone-700">{{ t('bn.mGate') }}</div>
              <p class="text-[11px] text-stone-500">{{ t('bn.mGateHint') }}</p>
              <div class="flex flex-wrap gap-3">
                <label v-for="g in scheme.groups" :key="'gate' + g"
                       class="inline-flex items-center gap-2 text-[12px] text-stone-600">
                  <input type="checkbox" class="w-4 h-4" style="accent-color: #d97706"
                         :checked="!!scheme.money.gateOn[g]"
                         @change="scheme.money.gateOn[g] = scheme.money.gateOn[g] ? 0 : 1; dirty = true" />
                  {{ t('bn.grp_' + g) }}
                  <input v-model.number="scheme.money.gatePct[g]" type="number" min="0" max="100"
                         :disabled="!scheme.money.gateOn[g]"
                         class="w-16 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none disabled:bg-stone-100 disabled:text-stone-400"
                         @input="dirty = true" />%
                </label>
              </div>
              <p v-if="!scheme.money.gateOn.floor" class="text-[11px] text-stone-400">{{ t('bn.mGateFloorWhy') }}</p>
            </div>

            <!-- team kicker -->
            <div class="pt-2 border-t border-amber-200/60 space-y-2">
              <label class="inline-flex items-center gap-2 text-[12px] font-bold text-stone-700">
                <input type="checkbox" class="w-4 h-4" style="accent-color: #d97706"
                       :checked="!!scheme.money.kickerOn"
                       @change="scheme.money.kickerOn = scheme.money.kickerOn ? 0 : 1; dirty = true" />
                {{ t('bn.mKicker') }}
              </label>
              <p class="text-[11px] text-stone-500">{{ t('bn.mKickerHint') }}</p>
              <div v-if="scheme.money.kickerOn" class="flex flex-wrap gap-3">
                <label class="inline-flex items-center gap-2 text-[12px] text-stone-600">
                  {{ t('bn.mKickerAmount') }}
                  <input v-model.number="scheme.money.kickerAmount" type="number" min="0" step="10"
                         class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
                </label>
                <label class="inline-flex items-center gap-2 text-[12px] text-stone-600">
                  {{ t('bn.mKickerTarget') }}
                  <input v-model.number="scheme.money.kickerTargetPct" type="number" min="0" max="100"
                         class="w-16 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />%
                </label>
              </div>
            </div>

            <!-- weekly top 3 -->
            <div class="pt-2 border-t border-amber-200/60">
              <div class="text-[11.5px] font-bold text-stone-700 mb-1.5">{{ t('bn.mWeekly') }}</div>
              <div class="flex items-center gap-2">
                <input v-for="(v, i) in scheme.money.weeklyTop" :key="i"
                       v-model.number="scheme.money.weeklyTop[i]" type="number" min="0" step="10"
                       class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none" @input="dirty = true" />
                <span class="text-[11px] text-stone-400">{{ scheme.money.currency }} · {{ t('bn.prizeOrder') }}</span>
              </div>
            </div>
          </template>
        </div>
        <div class="grid sm:grid-cols-3 gap-x-4 gap-y-2 pt-1">
          <label v-for="(v, k) in scheme.points" :key="k"
                 class="flex items-center justify-between gap-2 text-[12px] text-stone-600">
            <span class="text-[11.5px]">{{ t('bn.k_' + k.replace('.', '_'), k) }}</span>
            <input v-model.number="scheme.points[k]" type="number" min="0" step="0.05"
                   class="w-20 h-8 ps-2.5 rounded-lg ring-1 ring-stone-200 text-[12px] tabular-nums focus:outline-none"
                   @input="dirty = true" />
          </label>
        </div>
        <div class="flex justify-end">
          <button class="h-9 px-4 rounded-lg text-[12px] font-bold text-white bg-stone-900 hover:bg-stone-800 disabled:opacity-50 transition-colors"
                  :disabled="!dirty || saving" @click="saveScheme">
            {{ saving ? '…' : t('px.common.save') }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";
import { useAuth } from "@/composables/useAuth";
import { IS_CC, IS_SHIP } from "@/lib/portal";
import { useBonusLaunch } from "@/composables/useBonusLaunch";

const { t } = useI18n();
const { role, ccAdmin, viewAs } = useAuth();
// Floor roles wait for the scheme to be switched on; CC lanes + managers
// see the live board.
// From October the floor is paid, but each month is reviewed by hand first:
// the poster stays up until a month comes back approved from the server.
const floorRole = computed(() =>
  ["picker", "packer", "dispatcher", "returns"].includes(role.value));
const floorApproved = ref(false);
const floorComingSoon = computed(() => floorRole.value && !floorApproved.value);
const isManager = computed(() => role.value === "manager");
const { openRules } = useBonusLaunch();

// The launch notice's read-receipt, manager only (and not while viewing as a
// member — the server would refuse, and the card is not theirs to see).
const ackStat = ref(null);
const ackOpen = ref(false);
const ackPending = computed(() => (ackStat.value?.rows || []).filter((r) => !r.ackedAt));
async function loadAcks() {
  if (!isManager.value || viewAs.value) return;
  try { ackStat.value = await api("announcements.status"); } catch { ackStat.value = null; }
}
// CC agents — and a manager viewing as one — get the coming-soon panel; only
// the manager/section admins see (and keep designing) the actual board.
const comingSoon = computed(() => {
  if (!IS_CC && !IS_SHIP) return false;
  // The tracking team waited behind the poster until its lane was priced
  // (2 MAD a point, 2026-11-02); an unpriced lane still gets the promise.
  if (IS_SHIP && !(Number(scheme.value?.money?.perPoint?.ship) > 0)) return true;
  // The moment the manager flips money.on, the promise page steps aside on
  // its own — no deploy between "activated" and "the team can see it".
  if (Number(scheme.value?.money?.on)) return false;
  // View-as used to render the promise poster too — faithful, and useless:
  // the manager already knows the poster exists; what they are impersonating
  // FOR is to check the agent's numbers before switching the money on. So
  // view-as previews the real page (the banner already says whose eyes these
  // are); the poster stays for the agents themselves until activation.
  if (viewAs.value) return false;
  const admin = ccAdmin.value?.cf || ccAdmin.value?.rs || ccAdmin.value?.cs;
  return role.value !== "manager" && !admin;
});
const { success, warn } = useToast();

const now = new Date();
const fmt = (dt) => `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}`;
const months = computed(() => {
  // History exists from September 2026 — the month the scheme went live.
  // Before that nobody was playing by these rules, so "Last month" only
  // appears once there is a played month to look back at. The server clamps
  // the same way, so a hand-typed URL cannot reach further either.
  const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const out = [{ key: fmt(now), label: t("bn.thisMonth") }];
  if (prev >= new Date(2026, 8, 1)) out.push({ key: fmt(prev), label: t("bn.lastMonth") });
  return out;
});

const month = ref(fmt(now));
// The logistics portal opens on the floor's board — its managers are floor
// staff, and the server's default for a manager is the CC board.
const group = ref(IS_CC || IS_SHIP ? "" : "floor");
const d = ref(null);
const breakdownFor = ref("");
const breakdown = ref(null);
const breakdownLoading = ref(false);
async function toggleBreakdown(user) {
  if (breakdownFor.value === user) { breakdownFor.value = ""; return; }
  breakdownFor.value = user;
  breakdown.value = null;
  breakdownLoading.value = true;
  try {
    breakdown.value = await api("contact_center.bonus_breakdown",
      { user, month: d.value?.month, group: d.value?.group });
  } catch (e) {
    breakdown.value = null;
  } finally {
    breakdownLoading.value = false;
  }
}
const loading = ref(true);
const loadError = ref("");

// The recipe. Opens with the agent's OWN month from bonus_breakdown — the
// same call the receipt uses, so the explainer can never disagree with the
// receipt below it.
const howOpen = ref(false);
const howLoading = ref(false);
const howData = ref(null);
const howScheme = computed(() => howData.value?.scheme || null);
async function toggleHow() {
  howOpen.value = !howOpen.value;
  if (!howOpen.value || howData.value) return;
  howLoading.value = true;
  try {
    howData.value = await api("contact_center.bonus_breakdown",
      { month: d.value?.month, group: d.value?.group });
  } catch { howData.value = null; }
  finally { howLoading.value = false; }
}
const howSteps = computed(() => {
  const b = howData.value;
  const sc = howScheme.value || {};
  const fill = (k, m) => Object.entries(m).reduce(
    (a, [kk, vv]) => a.replaceAll("{" + kk + "}", String(vv)), t(k));
  const actions = (b?.lines || []).reduce((a, l) => a + (l.count || 0), 0);
  const ratio = sc.confirmEach ? Math.round((sc.deliveredEach ?? b?.deliveredEach ?? 0) / sc.confirmEach) : 4;
  const steps = [
    { icon: "phone", tint: "bg-sky-100 text-sky-600",
      title: t("bn.how1Title"), body: t("bn.how1Body"),
      live: b ? fill("bn.how1Live", { n: actions }) : "",
      liveIcon: "activity", liveTint: "bg-sky-50 text-sky-700 ring-1 ring-sky-200/70" },
    { icon: "package-check", tint: "bg-emerald-100 text-emerald-600",
      title: t("bn.how2Title"), body: fill("bn.how2Body", { x: ratio }),
      live: b ? fill("bn.how2Live", { n: b.delivered, p: b.deliveredPts }) : "",
      liveIcon: "check", liveTint: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/70" },
  ];
  // The gate step only exists where the scheme actually gates.
  if (sc.gateOn) {
    const r = sc.deliveryRate;
    steps.push({ icon: "unlock", tint: "bg-amber-100 text-amber-600",
      title: t("bn.how3Title"), body: fill("bn.how3Body", { g: sc.gatePct }),
      live: r == null ? t("bn.how3LiveNone")
        : r >= sc.gatePct ? fill("bn.how3LivePass", { r })
        : fill("bn.how3LiveFail", { r, d: (sc.gatePct - r).toFixed(1) }),
      liveIcon: r != null && r >= sc.gatePct ? "check-circle" : "shield-alert",
      liveTint: r != null && r >= sc.gatePct
        ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/70"
        : "bg-amber-50 text-amber-700 ring-1 ring-amber-200/70" });
  }
  steps.push({ icon: "zap", tint: "bg-violet-100 text-violet-600",
    title: t("bn.how4Title"),
    body: fill("bn.how4Body", { s: 5, pct: sc.streakStepPct || 10, cap: sc.streakCapPct || 30 }),
    live: b ? fill("bn.how4Live", { n: b.streakDays || 0 }) : "",
    liveIcon: "zap", liveTint: "bg-violet-50 text-violet-700 ring-1 ring-violet-200/70" });
  return steps;
});
const scheme = ref(null);
const dirty = ref(false);
const saving = ref(false);

const pct = computed(() => {
  if (!d.value?.target) return 0;
  return Math.round(Math.min(100, (d.value.me.points * 100) / d.value.target));
});

// Count the points up — the number is the point of the page.
const nPoints = ref(0);
let rafId = 0;
watch(d, (v) => {
  if (!v?.available) return;
  cancelAnimationFrame(rafId);   // a reload mid-animation forked two loops
  const from = nPoints.value;
  const to = v.me.points;
  const t0 = performance.now();
  const step = (now2) => {
    const p = Math.min(1, (now2 - t0) / 900);
    const eased = 1 - Math.pow(1 - p, 3);
    nPoints.value = Math.round((from + (to - from) * eased) * 10) / 10;
    if (p < 1) rafId = requestAnimationFrame(step);
  };
  rafId = requestAnimationFrame(step);
});
onUnmounted(() => cancelAnimationFrame(rafId));

async function load() {
  if (comingSoon.value) return;   // the header's month buttons bypass mount
  loading.value = true;
  loadError.value = "";
  try {
    const res = await api("contact_center.bonus", {
      month: month.value, group: group.value || undefined,
    });
    d.value = res;
    if (res.group) group.value = res.group;
  } catch (e) {
    loadError.value = String(e.message || e);
  } finally {
    loading.value = false;
  }
}

async function loadScheme() {
  try {
    scheme.value = await api("contact_center.bonus_settings");
  } catch {
    scheme.value = null;
  }
}

async function saveScheme() {
  saving.value = true;
  try {
    const res = await apiPost("contact_center.save_bonus_settings", {
      settings: { targets: scheme.value.targets, points: scheme.value.points,
                  money: scheme.value.money },
    });
    Object.assign(scheme.value, res);
    dirty.value = false;
    success(t("cfs.saved"));
    load();
  } catch (e) {
    warn(t("cfs.saveFail"), String(e.message || e));
  } finally {
    saving.value = false;
  }
}

// The latest approved month, this one first. A floor member is never shown
// a month the approver has not published.
async function loadFloorApproved() {
  for (const m of months.value) {
    try {
      const res = await api("contact_center.bonus", { month: m.key });
      if (res?.approved) {
        month.value = m.key;
        d.value = res;
        if (res.group) group.value = res.group;
        floorApproved.value = true;
        loading.value = false;
        return;
      }
    } catch { /* stay on the poster */ }
  }
}

// ── approval (named approvers only — the server sends d.approval to them) ─
const apRows = ref([]);
const apNote = ref("");
const apAdd = ref("");
const apDirty = ref(false);
const apSaving = ref(false);
const apTotal = computed(() =>
  apRows.value.reduce((n, r) => n + Math.max(0, Number(r.final) || 0), 0));
watch(d, (v) => {
  const ap = v?.approval;
  if (!ap) { apRows.value = []; return; }
  const amounts = ap.amounts || {};
  const system = ap.system || {};
  const sug = ap.suggestion?.people || {};
  // A saved draft wins; otherwise the work-time suggestion pre-fills "to pay".
  const hasDraft = Object.keys(amounts).length > 0;
  const workOf = (u) => {
    const w = sug[u]?.work;
    return w ? Object.entries(w).filter(([, n]) => n).map(([k, n]) => `${k} ${n}`).join(" · ") : "";
  };
  const mk = (user, agent, points, sys) => ({
    user, agent, points, system: sys ?? null,
    suggested: sug[user]?.amount ?? null, hours: sug[user]?.hours ?? null, work: workOf(user),
    final: hasDraft ? (amounts[user] ?? 0) : (sug[user]?.amount ?? sys ?? 0),
  });
  // An approved board carries the approved amount in pay; the computed one
  // survives in the snapshot taken at approval.
  const rows = (v.agents || []).map((a) =>
    mk(a.user, a.agent, a.points, v.approved ? system[a.user] : a.pay?.total));
  for (const u of [...Object.keys(sug), ...Object.keys(amounts)]) {
    if (!rows.some((r) => r.user === u)) {
      rows.push(mk(u, sug[u]?.agent || u.split("@")[0], null, system[u]));
    }
  }
  rows.sort((a, b) => (Number(b.final) || 0) - (Number(a.final) || 0));
  apRows.value = rows;
  apNote.value = ap.note || "";
  apDirty.value = false;
});
const apHasSuggest = computed(() => !!d.value?.approval?.suggestion?.people);
function fillAp(which) {
  for (const r of apRows.value) r.final = (which === "suggested" ? r.suggested : r.system) ?? 0;
  apDirty.value = true;
}
function addApRow() {
  const u = (apAdd.value || "").toLowerCase();
  if (!u || apRows.value.some((r) => r.user === u)) { apAdd.value = ""; return; }
  apRows.value.push({ user: u, agent: u.split("@")[0], points: null, system: null,
                      suggested: null, hours: null, work: "", final: 0 });
  apAdd.value = "";
  apDirty.value = true;
}
async function saveApproval(state) {
  if (state === "approved" && !window.confirm(t("bn.apConfirm").replace("{n}", String(apTotal.value)))) return;
  apSaving.value = true;
  try {
    const amounts = Object.fromEntries(apRows.value.map((r) => [r.user, Math.max(0, Number(r.final) || 0)]));
    await apiPost("contact_center.set_bonus_approval", {
      group: d.value.group, month: d.value.month, amounts: JSON.stringify(amounts),
      note: apNote.value, state,
    });
    success(state === "approved" ? t("bn.apApprovedToast") : t("cfs.saved"));
    load();
  } catch (e) {
    warn(t("cfs.saveFail"), String(e.message || e));
  } finally {
    apSaving.value = false;
  }
}
async function reopenApproval() {
  if (!window.confirm(t("bn.apReopenConfirm"))) return;
  apSaving.value = true;
  try {
    await apiPost("contact_center.reopen_bonus_approval", { group: d.value.group, month: d.value.month });
    load();
  } catch (e) {
    warn(t("cfs.saveFail"), String(e.message || e));
  } finally {
    apSaving.value = false;
  }
}

onMounted(async () => {
  loadAcks();
  if (floorRole.value) { await loadFloorApproved(); return; }
  // Scheme first: comingSoon depends on money.on, so the promise page must
  // not be the thing that decides whether we ever find out it was switched on.
  await loadScheme();
  if (!comingSoon.value) load();
});
</script>

<style scoped>
.bn-how {
  opacity: 0;
  animation: bn-how-in .4s cubic-bezier(.2, .7, .3, 1) forwards;
}
@keyframes bn-how-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.bn-how-n {
  width: 20px; height: 20px; border-radius: 9999px; flex-shrink: 0;
  display: grid; place-items: center;
  font-size: 10.5px; font-weight: 800; color: white;
  background: var(--accent-500, #f97316);
}
@media (prefers-reduced-motion: reduce) {
  .bn-how { animation: none; opacity: 1; transform: none; }
}

.bn-scene { position: relative; width: 120px; height: 96px; }
.bn-wallet {
  position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  animation: bn-catch 2.4s ease-in-out infinite;
}
.bn-coin { position: absolute; width: 18px; height: 18px; top: -6px; opacity: 0; }
.bn-c1 { left: 26px; animation: bn-fall 2.4s ease-in infinite; }
.bn-c2 { left: 51px; animation: bn-fall 2.4s ease-in .5s infinite; }
.bn-c3 { left: 76px; animation: bn-fall 2.4s ease-in 1.1s infinite; }
@keyframes bn-fall {
  0%   { transform: translateY(0) rotate(0); opacity: 0; }
  12%  { opacity: 1; }
  62%  { transform: translateY(58px) rotate(160deg); opacity: 1; }
  74%  { transform: translateY(52px) rotate(180deg); }
  86%  { transform: translateY(60px) rotate(200deg); opacity: 0; }
  100% { opacity: 0; }
}
@keyframes bn-catch {
  0%, 55%, 100% { transform: translateX(-50%) translateY(0); }
  66% { transform: translateX(-50%) translateY(-4px) rotate(-3deg); }
  76% { transform: translateX(-50%) translateY(0) rotate(2deg); }
}
.bn-shimmer {
  background: linear-gradient(90deg, rgb(252 211 77), rgb(245 158 11));
  animation: bn-slide 1.6s ease-in-out infinite;
}
@keyframes bn-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(320%); }
}
[dir="rtl"] .bn-shimmer { animation-name: bn-slide-r; }
@keyframes bn-slide-r {
  0% { transform: translateX(100%); }
  100% { transform: translateX(-320%); }
}
.bn-hero {
  background: linear-gradient(135deg, rgb(255 251 235) 0%, #fff 50%, rgb(255 251 235) 100%);
  box-shadow: inset 0 0 0 1px rgb(253 230 138 / 0.6), 0 1px 2px rgb(0 0 0 / 0.03);
}
.bn-part {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10.5px; font-weight: 600; color: rgb(var(--text2));
  background: rgb(255 255 255 / .8); border-radius: 999px; padding: 3px 9px;
  box-shadow: inset 0 0 0 1px rgb(var(--border));
}
.bn-part-good { color: #047857; box-shadow: inset 0 0 0 1px #a7f3d0; }
.bn-part-bad { color: #be123c; box-shadow: inset 0 0 0 1px #fda4af; }
.bn-part-warn { color: #b45309; box-shadow: inset 0 0 0 1px #fcd34d; }
.bn-kick-on {
  background: linear-gradient(90deg, rgb(236 253 245), #fff);
  box-shadow: inset 0 0 0 1px rgb(167 243 208);
}
.bn-kick-off {
  background: linear-gradient(90deg, rgb(255 251 235), #fff);
  box-shadow: inset 0 0 0 1px rgb(253 230 138);
}
.bn-ico {
  width: 48px; height: 48px; border-radius: 14px; flex-shrink: 0;
  display: inline-flex; align-items: center; justify-content: center;
  color: white;
  background: linear-gradient(135deg, rgb(251 191 36), rgb(217 119 6));
  box-shadow: 0 6px 16px -6px rgb(217 119 6 / 0.5);
}
</style>
