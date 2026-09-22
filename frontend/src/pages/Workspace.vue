<template>
  <div class="p-4 sm:p-5 max-w-[1500px] mx-auto">
    <!-- ONE thing to press, and a scoreboard that knows it is a scoreboard.
         This strip had grown to eight elements competing at the same weight:
         an animated target ring with confetti, three stat cards, a pulsing
         red alarm, a pool chip with a popover, and the serve button. When
         everything shouts, nothing does — and the number that mattered (a
         customer waiting with nobody on them) was one shout among eight. -->
    <div class="flex items-center gap-3 mb-2">
      <h1 class="text-[18px] font-bold text-stone-900 tracking-tight">{{ t('ws.title') }}</h1>

      <!-- The alarm IS the button. Two separate things to press, one of them
           red, made the agent choose; there is only ever one right answer, so
           there is now only one control. It carries its own reason. -->
      <button class="ms-auto inline-flex items-center gap-2.5 h-12 px-6 rounded-2xl text-[14.5px] font-bold text-white shadow-md transition-all hover:shadow-lg disabled:opacity-50"
              :class="freshAlarm ? 'bg-rose-600 hover:bg-rose-700' : ''"
              :style="freshAlarm ? {} : { background: 'var(--accent-600)' }"
              :disabled="serving" @click="serveNext(true)">
        <Icon :name="freshAlarm ? 'zap' : 'sparkles'" :size="17" />
        <span v-if="serving">{{ t('ws.serving') }}</span>
        <template v-else-if="freshAlarm">
          {{ t('ws.nextFresh').replace('{n}', freshN) }}
          <span class="text-[11.5px] font-semibold text-white/80 tabular-nums" dir="ltr">{{ freshOldest }}m</span>
        </template>
        <span v-else>{{ t('ws.next') }}</span>
        <kbd class="text-[10px] font-mono bg-white/20 rounded px-1.5 py-0.5">N</kbd>
      </button>
    </div>

    <!-- the day, quietly: one line, one weight, nothing animated competing
         with the control above it -->
    <div class="flex items-center gap-x-4 gap-y-1.5 flex-wrap mb-4 text-[12px] text-stone-500">
      <span v-if="board?.myTarget" class="relative inline-flex items-center gap-1.5" :class="celebrating ? 'ws-ring-hit' : ''">
        <span v-for="pop in pops" :key="pop.id" class="ws-pop" :class="pop.cls">+1</span>
        <span v-if="celebrating" class="ws-burst" aria-hidden="true"><i v-for="n in 14" :key="n" :style="burstStyle(n)" /></span>
        <span class="inline-block w-16 h-1.5 rounded-full bg-stone-200 overflow-hidden align-middle">
          <span class="block h-full rounded-full transition-all duration-500"
                :class="dayPct >= 100 ? 'bg-emerald-500' : 'bg-[var(--accent-500)]'"
                :style="{ width: Math.min(100, dayPct) + '%' }" />
        </span>
        <b class="tabular-nums" :class="dayPct >= 100 ? 'text-emerald-600' : 'text-stone-800'">{{ myTotal }}</b>
        <span class="text-stone-400">/{{ board.myTarget }}</span>
      </span>

      <span class="inline-flex items-center gap-1.5">
        <Icon name="check-circle" :size="13" class="text-emerald-500" />
        <b class="tabular-nums text-stone-800">{{ board?.mine?.confirm ?? 0 }}</b> {{ t('ws.confirmed') }}
      </span>

      <span v-if="slaLate" class="inline-flex items-center gap-1.5 text-rose-600 font-semibold">
        <Icon name="shield-alert" :size="13" />
        <b class="tabular-nums">{{ slaLate }}</b> {{ t('ws.slaLateShort').replace('{h}', board?.slaHours || 6) }}
      </span>

      <span v-if="dueCount" class="inline-flex items-center gap-1.5 text-amber-600">
        <Icon name="clock" :size="13" />
        <b class="tabular-nums">{{ dueCount }}</b> {{ t('ws.dueShort') }}
      </span>

      <!-- the pool is a lead's number: present, never shouting -->
      <button v-if="poolN" class="inline-flex items-center gap-1.5 hover:text-stone-800 transition-colors"
              :class="poolBlock ? 'text-stone-400' : 'text-teal-600'"
              :title="poolBlock ? t('ws.poolBlk_' + poolBlock) : t('ws.poolLeft').replace('{n}', poolN)"
              @click="toggleTeam">
        <Icon name="users" :size="13" />
        <b class="tabular-nums">{{ poolN }}</b> {{ t('ws.poolShort') }}
      </button>

      <div v-if="teamOpen && team.length"
           class="absolute z-30 mt-8 w-[290px] bg-white rounded-2xl ring-1 ring-stone-200 shadow-xl p-2.5 space-y-1">
        <div v-for="m in team" :key="m.user" class="flex items-center gap-2 text-[12px] px-1.5 py-1 rounded-lg"
             :class="m.onShift ? '' : 'opacity-45'">
          <span class="w-1.5 h-1.5 rounded-full shrink-0"
                :class="!m.onShift ? 'bg-stone-300' : m.punched ? 'bg-emerald-500' : 'ring-1 ring-emerald-400'"
                :title="m.punched ? '' : t('ws.noPunch')" />
          <span class="min-w-0 flex-1 truncate" :class="m.onDuty ? 'text-stone-800' : 'text-stone-400 italic'">{{ m.name }}</span>
          <span v-if="!m.onDuty" class="text-[9.5px] font-semibold text-stone-400 shrink-0">{{ t('ws.offDuty') }}</span>
          <span class="tabular-nums text-stone-400" :title="t('ws.poolShort')">{{ m.holding }}</span>
          <span class="tabular-nums font-semibold text-emerald-600" :title="t('ws.doneToday')">{{ m.doneToday }}</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[300px_minmax(0,1fr)_300px] gap-4 items-start">
      <!-- LEFT: the queue, dense like the desk list they live in -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden lg:sticky lg:top-3">
        <div class="px-3 py-2 border-b border-stone-100 flex items-center gap-2">
          <span class="text-[11.5px] font-semibold" :class="tabMode ? 'text-[var(--accent-700)]' : 'text-stone-700'">{{ tabMode ? t(WORK_TAB_LABEL[tabMode]) : t(plan?.scope === 'team' ? 'ws.queueTeam' : 'ws.queue') }}</span>
          <span class="text-[10.5px] text-stone-400 tabular-nums">{{ tabMode ? tabRows.length : (board?.counts?.pending ?? '–') }}</span>
          <button v-if="tabMode" class="ms-auto text-[10px] font-semibold text-stone-500 hover:text-stone-800 bg-stone-100 rounded-md px-1.5 py-0.5" @click="exitTabMode()">{{ t('ws.exitList') }}</button>
          <button :class="tabMode ? '' : 'ms-auto'" class="text-stone-400 hover:text-stone-700" :title="t('common.refresh')" @click="tabMode ? loadTabQueue(tabMode) : loadBoard()">
            <Icon name="refresh-cw" :size="12" />
          </button>
        </div>
        <div v-if="boardLoading || tabLoading" class="p-3 space-y-1.5">
          <span v-for="n in 8" :key="n" class="block h-8 rounded bg-stone-100 animate-pulse" />
        </div>
        <div v-else class="max-h-[70vh] overflow-y-auto divide-y divide-stone-50">
          <button v-for="r in queueRows" :key="r.order"
                  class="w-full text-start px-3 py-2 flex items-center gap-2 hover:bg-stone-50 transition-colors"
                  :class="active?.name === r.order ? 'bg-[var(--accent-50)]' : ''"
                  @click="openOrder(r.order)">
            <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
                  :class="r.due ? 'bg-amber-500' : r.ageH > (board?.slaHours || 6) ? 'bg-rose-500' : 'bg-stone-300'" />
            <span class="min-w-0 flex-1">
              <span class="flex items-center gap-1.5 min-w-0">
                <span class="text-[12px] font-semibold text-stone-800 truncate">{{ r.customer || r.order }}</span>
                <span v-if="r.kind !== 'pending'" class="text-[8.5px] font-bold uppercase rounded px-1 py-px flex-shrink-0"
                      :class="KIND_CLS[r.kind]">{{ t('ws.k_' + r.kind) }}</span>
                <!-- Never handed out by Next; here so the row explains why
                     it is sitting there and who to ask. -->
                <span v-if="r.phoneSale" class="text-[8.5px] font-bold uppercase rounded px-1 py-px flex-shrink-0 text-violet-700 bg-violet-100"
                      :title="r.soldBy ? t('ws.phoneSaleBy').replace('{name}', r.soldBy) : t('ws.phoneSale')">{{ t('ws.kPhone') }}</span>
              </span>
              <span class="block text-[10px] text-stone-400 font-mono truncate">{{ r.order }} · {{ r.ageH }}h<template v-if="r.attempts"> · ×{{ r.attempts }}</template></span>
            </span>
            <span class="text-[11px] font-semibold tabular-nums text-stone-600 flex-shrink-0">{{ Math.round(r.total) }}</span>
          </button>
          <div v-if="!queueRows.length" class="text-center py-8">
            <div class="text-[12px] text-emerald-600">{{ t('cf.empty') }}</div>
            <!-- honest empty: work IS scheduled, just not due yet -->
            <div v-if="nextDueAt" class="text-[11px] text-amber-600 font-semibold mt-1">
              {{ t('ws.nextDueAt').replace('{t}', local(nextDueAt)) }}
            </div>
          </div>
        </div>
      </div>

      <!-- CENTER: the active order card — every decision tool in one place -->
      <div>
        <!-- Somebody else is on this customer. Named, timed, and it moves
             the agent on by itself — a refusal with nowhere to go is how a
             portal teaches people to click twice. -->
        <div v-if="busyBy" class="bg-amber-50 rounded-2xl ring-1 ring-amber-300 p-10 text-center">
          <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-amber-100 text-amber-600 mb-3">
            <Icon name="user" :size="26" /></span>
          <div class="text-[15px] font-bold text-stone-900">{{ t('ws.busyTitle').replace('{who}', busyBy) }}</div>
          <div v-if="busySince" class="text-[12.5px] text-stone-500 mt-1" dir="ltr">{{ local(busySince).slice(11) }}</div>
          <div class="text-[12px] text-amber-700 mt-3">{{ t('ws.busyNext') }}</div>
        </div>

        <div v-else-if="!active && !cardLoading" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-12 text-center">
          <span class="inline-flex w-14 h-14 rounded-2xl items-center justify-center bg-[var(--accent-50)] text-[var(--accent-600)] mb-3"><Icon name="sparkles" :size="26" /></span>
          <div class="text-[15px] font-semibold text-stone-900">{{ t('ws.emptyTitle') }}</div>
          <div class="text-[12.5px] text-stone-500 mt-1 max-w-sm mx-auto">{{ t('ws.emptyHint') }}</div>
          <div class="mt-3 text-[11px] text-stone-400">{{ t('ws.keys') }}</div>
        </div>
        <div v-else-if="cardLoading" class="bg-white rounded-2xl ring-1 ring-stone-200/70 h-[420px] animate-pulse" />
        <Transition v-else name="ws-card" mode="out-in">
        <div :key="active.name" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 space-y-4">
          <!-- header -->
          <div class="flex items-start gap-3 flex-wrap">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[16px] font-bold text-stone-900">{{ active.customer }}</span>
                <span v-if="grade" class="text-[10.5px] font-bold rounded-full px-2 py-0.5 ring-1" :class="grade.cls" :title="grade.hint">{{ grade.label }}</span>
                <span class="font-mono text-[11.5px] text-stone-400">{{ active.name }}</span>
                <span v-if="stChip" class="text-[10px] font-bold uppercase rounded-full px-2 py-0.5" :class="stChip.cls">{{ stChip.label }}</span>
                <span v-if="activeRow?.due" class="text-[10px] font-bold text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-full px-2 py-0.5">{{ t('cf.due') }}</span>
                <span class="text-[10.5px] font-mono tabular-nums rounded-full px-2 py-0.5 ring-1"
                      :class="cardSeconds > 240 ? 'text-rose-700 bg-rose-50 ring-rose-200' : 'text-stone-500 bg-stone-50 ring-stone-200'">
                  <Icon name="clock" :size="9" class="inline -mt-px" /> {{ cardTimer }}
                </span>
                <!-- the first-call clock on THIS order: green while there's
                     time, counts down, flips to "late by Xh" past the SLA -->
                <span v-if="slaChip" class="text-[10px] font-bold rounded-full px-2 py-0.5 ring-1 tabular-nums" :class="slaChip.cls">
                  {{ slaChip.text }}
                </span>
              </div>
              <div class="flex items-center gap-2.5 text-[12px] text-stone-500 mt-1 flex-wrap tabular-nums">
                <a :href="'tel:' + active.phone" class="font-mono text-sky-700 font-semibold">{{ active.phone }}</a>
                <span v-if="active.city" class="inline-flex items-center gap-1"><Icon name="map-pin" :size="11" />{{ active.city }}</span>
                <span v-if="cardAge" class="inline-flex items-center gap-1"><Icon name="clock" :size="11" />{{ cardAge }}</span>
                <span v-if="cardAttempts" class="text-amber-600 font-medium">×{{ cardAttempts }} {{ t('ws.attempts') }}</span>
                <span v-if="active.next_call" class="text-stone-400">→ {{ local(active.next_call).slice(5) }}</span>
              </div>
              <!-- "Where is my order?" answered before the customer finishes
                   asking: the warehouse journey, with the live carrier status. -->
              <div v-if="journey.show" class="flex items-center gap-1.5 mt-2 flex-wrap">
                <span v-for="(st, i) in journey.steps" :key="st.key"
                      class="text-[10px] font-bold rounded-full px-2 py-0.5 ring-1 whitespace-nowrap"
                      :class="i < journey.at ? 'text-emerald-700 bg-emerald-50 ring-emerald-200'
                        : i === journey.at ? 'text-white bg-[var(--accent-600)] ring-[var(--accent-600)]'
                        : 'text-stone-400 bg-stone-50 ring-stone-200'">{{ t(st.label) }}</span>
                <span v-if="journey.returned" class="text-[10px] font-bold rounded-full px-2 py-0.5 ring-1 text-rose-700 bg-rose-50 ring-rose-200 whitespace-nowrap">
                  {{ t('ws.jReturned') }}
                </span>
                <span v-if="active.tracking_status" class="text-[10.5px] font-semibold rounded-full px-2 py-0.5 ring-1"
                      :class="trackBad ? 'text-rose-700 bg-rose-50 ring-rose-200' : 'text-sky-700 bg-sky-50 ring-sky-200'">
                  {{ active.tracking_status }}
                </span>
                <a v-if="active.awb" :href="active.tracking_url || '#'" target="_blank"
                   class="text-[10.5px] font-mono text-stone-500 hover:text-[var(--accent-700)] hover:underline">
                  AWB {{ active.awb }}
                </a>
              </div>
            </div>
            <div class="flex items-center gap-1.5">
              <a :href="'tel:' + active.phone" class="ws-contact bg-sky-50 text-sky-700 ring-sky-200" :title="t('ws.call')"><Icon name="phone" :size="16" /></a>
              <a :href="waUrl" target="_blank" class="ws-contact bg-emerald-50 text-emerald-700 ring-emerald-200" title="WhatsApp"><Icon name="message-circle" :size="16" /></a>
              <button class="ws-contact bg-amber-50 text-amber-700 ring-amber-200" :title="t('cf.editContact')" @click="panel = panel === 'contact' ? '' : 'contact'"><Icon name="edit" :size="15" /></button>
            </div>
          </div>

          <!-- Somebody here already had this conversation. This sits above
               everything else on the card because it changes what the agent
               does next: not "call and ask", but "confirm what a colleague
               already sold". It is why the order never comes out of the
               queue on its own. -->
          <div v-if="active.phoneSale"
               class="rounded-xl px-3.5 py-3 flex items-start gap-2.5 bg-violet-50 ring-1 ring-violet-300">
            <span class="w-7 h-7 rounded-lg bg-violet-600 text-white flex items-center justify-center flex-shrink-0">
              <Icon name="phone" :size="15" />
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-bold text-violet-900" dir="auto">
                {{ active.soldBy ? t('ws.phoneSaleBy').replace('{name}', active.soldBy) : t('ws.phoneSale') }}
              </div>
              <div class="text-[11px] text-violet-700 mt-0.5">{{ t('ws.phoneSaleHint') }}</div>
            </div>
          </div>

          <!-- the order's story so far — auto-loaded for anything not fresh,
               so the agent knows the history BEFORE dialing -->
          <div v-if="miniActivity.length && !showActivity" class="rounded-xl bg-stone-50 ring-1 ring-stone-200/60 px-3 py-2 space-y-1">
            <div v-for="(a, i) in miniActivity" :key="i" class="flex items-center gap-2 text-[11px] text-stone-600 min-w-0">
              <span class="w-1 h-1 rounded-full bg-stone-300 flex-shrink-0" />
              <span class="truncate" dir="auto">{{ a.text }}</span>
              <span class="ms-auto flex-shrink-0 text-stone-400 font-mono text-[10px]">{{ a.by }} · {{ local(a.at).slice(5) }}</span>
            </div>
            <button class="text-[10.5px] font-semibold text-[var(--accent-600)] hover:underline" @click="toggleActivity">{{ t('ws.moreActivity') }}</button>
          </div>

          <!-- Stock reality, while the customer is still on the line: finding
               out days later that a line can't be picked is a dead order. -->
          <div v-if="(active.stockShort || []).length"
               class="ws-oos rounded-xl px-3.5 py-3 flex items-start gap-2.5">
            <span class="w-7 h-7 rounded-lg bg-rose-600 text-white flex items-center justify-center flex-shrink-0">
              <Icon name="alert-triangle" :size="15" />
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-bold text-rose-800">
                {{ active.stockShort.length === 1 ? t('ws.oosOne') : t('ws.oosN').replace('{n}', String(active.stockShort.length)) }}
              </div>
              <!-- Each short line opens the shelf lookup: "out of stock" is a
                   claim the agent can now check while the customer waits,
                   instead of a verdict they have to take on trust. -->
              <div class="flex flex-wrap gap-1.5 mt-1">
                <button v-for="(sh, si) in active.stockShort" :key="si"
                        class="inline-flex items-center gap-1 max-w-full text-[11px] font-semibold text-rose-800 bg-white/70 ring-1 ring-rose-200 rounded-md px-1.5 py-0.5 hover:bg-white hover:ring-rose-300"
                        :title="t('ws.oosCheck')" dir="auto"
                        @click="skuModal?.openWith(sh.code || sh.name)">
                  <Icon name="search" :size="10" class="flex-shrink-0" />
                  <span class="truncate">{{ sh.name }}</span>
                </button>
              </div>
              <div class="text-[11px] text-rose-600/80 mt-0.5">{{ t('ws.oosHint') }}</div>
            </div>
            <button class="h-8 px-3 rounded-lg text-[11.5px] font-bold text-white bg-rose-600 hover:bg-rose-700 flex-shrink-0"
                    @click="panel = panel === 'amend' ? '' : 'amend'">{{ t('ws.oosFix') }}</button>
          </div>

          <!-- Sellable, just not on a pick face. This is NOT the red panel
               and must never look like it: the agent should confirm. Saying
               "out of stock" here is what made them cancel live sales —
               J-008094 was refused with 1,986 units of its item in the
               building, 694 of them in SLOW ZONE. -->
          <div v-else-if="(active.stockOffFace || []).length"
               class="rounded-xl px-3.5 py-3 flex items-start gap-2.5 bg-amber-50 ring-1 ring-amber-300">
            <span class="w-7 h-7 rounded-lg bg-amber-500 text-white flex items-center justify-center flex-shrink-0">
              <Icon name="package-check" :size="15" />
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-bold text-amber-900">{{ t('ws.offFaceTitle') }}</div>
              <div class="flex flex-wrap gap-1.5 mt-1">
                <button v-for="(of, oi) in active.stockOffFace" :key="oi"
                        class="inline-flex items-center gap-1 max-w-full text-[11px] font-semibold text-amber-900 bg-white/70 ring-1 ring-amber-200 rounded-md px-1.5 py-0.5 hover:bg-white"
                        :title="t('ws.oosCheck')" dir="auto"
                        @click="skuModal?.openWith(of.code || of.name)">
                  <Icon name="search" :size="10" class="flex-shrink-0" />
                  <span class="truncate">{{ of.name }}</span>
                  <span v-if="of.qty" class="tabular-nums opacity-80" dir="ltr">· {{ of.qty }} {{ of.where }}</span>
                </button>
              </div>
              <div class="text-[11px] text-amber-700 mt-0.5">{{ t('ws.offFaceHint') }}</div>
            </div>
          </div>

          <!-- items -->
          <div class="rounded-xl ring-1 ring-stone-100 divide-y divide-stone-50">
            <div v-for="it in active.items" :key="it.idx || it.sku" class="px-3 py-2 flex items-center gap-3">
              <img v-if="it.image" :src="it.image" alt="" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50" @error="hideImg" />
              <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center text-stone-400"><Icon name="package-check" :size="15" /></span>
              <div class="min-w-0 flex-1">
                <div class="text-[12.5px] text-stone-800 truncate">{{ it.name }}</div>
              <!-- The REAL SKU, not the Shopify variant id.
                   item_code is the variant number the channel generated
                   (9219745579262); custom_sku is what the warehouse, the
                   shelf label and the supplier all call this thing (NP-001).
                   The agent on the phone needs the second one, and it is
                   present on 98.3% of order lines — the variant id stays as
                   the fallback for the rest so a line never loses its code.
                   Clicking it asks the shelf, which is the question that
                   follows "is it available?" every time. -->
              <button class="text-[10.5px] text-stone-400 font-mono hover:text-[var(--accent-700)] hover:underline"
                      :title="t('ws.oosCheck')" @click.stop="skuModal?.openWith(it.real_sku || it.sku)">
                {{ it.real_sku || it.sku }}
              </button>
              </div>
              <span v-if="it.local" class="text-[10px] font-bold rounded-full px-2 py-0.5 bg-sky-50 text-sky-700 ring-1 ring-sky-200 whitespace-nowrap flex-shrink-0"
                    :title="t('ws.localHint')">
                {{ t('ws.localItem') }}
              </span>
              <span v-else-if="it.short" class="text-[10px] font-bold rounded-full px-2 py-0.5 bg-rose-50 text-rose-700 ring-1 ring-rose-200 whitespace-nowrap flex-shrink-0"
                    :title="t('ws.availHint')">
                {{ it.avail ? t('ws.availN').replace('{n}', String(it.avail)) : t('ws.availZero') }}
              </span>
              <span class="text-[12.5px] font-bold tabular-nums text-stone-700">{{ Math.round(it.qty) }}×</span>
              <span class="text-[12px] tabular-nums text-stone-500 w-[70px] text-end">{{ Math.round((it.price || 0) * it.qty) }} MAD</span>
            </div>
            <div class="px-3 py-2 flex items-center justify-between bg-stone-50/60">
              <button v-if="inLane" class="text-[11.5px] font-semibold text-[var(--accent-700)] hover:underline" @click="panel = panel === 'amend' ? '' : 'amend'">
                {{ t('ws.amendBtn') }} <kbd class="text-[9px] font-mono text-stone-400">D</kbd>
              </button>
              <div class="text-[13px] tabular-nums">
                <span v-if="active.discount" class="text-emerald-600 me-2">−{{ Math.round(active.discount) }}</span>
                <b class="text-stone-900">{{ Math.round(active.total) }} MAD</b>
              </div>
            </div>
          </div>

          <!-- amend panel: discount + quantities, ONE atomic amend -->
          <Transition name="ws-slide">
            <div v-if="panel === 'amend'" class="rounded-xl bg-violet-50/60 ring-1 ring-violet-200/70 p-3 space-y-2.5">
              <div class="text-[11.5px] font-semibold text-violet-700">{{ t('ws.amendTitle') }}</div>
              <div class="space-y-1.5">
                <div v-for="it in amendItems" :key="it.idx || it.item_code" class="flex items-center gap-2">
                  <span class="text-[12px] text-stone-700 truncate flex-1">{{ it.name }}</span>
                  <div class="inline-flex items-center rounded-lg ring-1 ring-violet-200 bg-white overflow-hidden">
                    <button class="w-8 h-8 text-stone-500 hover:bg-stone-50" @click="it.qty = Math.max(0, it.qty - 1)">−</button>
                    <span class="w-8 text-center text-[12.5px] font-bold tabular-nums" :class="it.qty === 0 ? 'text-rose-600 line-through' : ''">{{ it.qty }}</span>
                    <button class="w-8 h-8 text-stone-500 hover:bg-stone-50" @click="it.qty += 1">+</button>
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-wrap pt-1">
                <span class="text-[11.5px] text-stone-500">{{ t('ws.discount') }}</span>
                <input v-model.number="discAmt" type="number" min="0" :placeholder="'MAD'"
                       class="h-8 w-[84px] ps-2 rounded-lg bg-white ring-1 ring-violet-200 text-[12.5px] tabular-nums focus:outline-none" />
                <span class="text-[11px] text-stone-400">{{ t('ws.or') }}</span>
                <input v-model.number="discPct" type="number" min="0" max="100" placeholder="%"
                       class="h-8 w-[64px] ps-2 rounded-lg bg-white ring-1 ring-violet-200 text-[12.5px] tabular-nums focus:outline-none" />
                <span class="text-[10.5px] text-stone-400">{{ t('ws.cap').replace('{p}', String(caps.pct)).replace('{a}', String(caps.amt)) }}</span>
                <button class="ms-auto h-8 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50"
                        :disabled="busy || !amendDirty" @click="applyAmend">{{ busy ? '…' : t('ws.applyAmend') }}</button>
              </div>
              <div class="text-[10.5px] text-stone-400">{{ t('ws.amendNote') }}</div>
            </div>
          </Transition>

          <!-- contact fix -->
          <Transition name="ws-slide">
            <div v-if="panel === 'contact'" class="rounded-xl bg-amber-50/60 ring-1 ring-amber-200/70 p-3 space-y-2">
            <div class="flex items-center gap-2 flex-wrap">
              <input v-model="editName" :placeholder="t('cf.namePh')" dir="auto" maxlength="140"
                     class="h-9 w-[160px] ps-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] focus:outline-none" />
              <input v-model="editPhone" :placeholder="t('cf.phonePh')" inputmode="tel"
                     class="h-9 w-[150px] ps-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] font-mono focus:outline-none" />
              <input v-model="editCity" :placeholder="t('cf.cityPh')"
                     class="h-9 w-[130px] ps-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] focus:outline-none" />
              <input v-model="editAddress" :placeholder="t('cf.addressPh')"
                     class="h-9 flex-1 min-w-[150px] ps-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] focus:outline-none" dir="auto" />
              <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50"
                      :disabled="busy" @click="saveContact">{{ t('cf.saveContact') }}</button>
            </div>
            <!-- One sentence, and only when it is true.
                 The carrier's payload was built when the parcel was made, so
                 a correction after that fixes our records and nothing the
                 driver is holding. Saying so is the difference between a
                 tool and a tool that lies. -->
            <div v-if="active.dn" class="flex items-start gap-1.5 text-[11px] text-amber-800/90 leading-snug">
              <Icon name="alert-triangle" :size="12" class="mt-[2px] shrink-0" />
              <span>{{ t('cf.contactLate') }}</span>
            </div>
            </div>
          </Transition>

          <!-- The order is already moving. This is NOT an error panel: the
               customer's decision stands either way, and all that changes is
               what we can still do about it. So the sentence names where the
               goods are and the button says what will actually happen. -->
          <Transition name="ws-slide">
            <div v-if="stopAsk" class="rounded-xl bg-rose-50 ring-1 ring-rose-300 p-3 space-y-2.5">
              <div class="flex items-start gap-2">
                <Icon name="package-x" :size="16" class="text-rose-600 mt-0.5 shrink-0" />
                <div class="text-[12.5px] text-rose-900 leading-snug">
                  {{ t('stop.at_' + stopAsk.stage) }}
                  <span class="block font-semibold mt-0.5">{{ t('stop.can_' + stopAsk.mode) }}</span>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <button class="h-9 px-4 rounded-lg text-[12.5px] font-bold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50"
                        :disabled="busy" @click="submitStop">{{ t('stop.do_' + stopAsk.mode) }}</button>
                <button class="h-9 px-3 rounded-lg text-[12.5px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200"
                        :disabled="busy" @click="stopAsk = null">{{ t('common.cancel') }}</button>
              </div>
            </div>
          </Transition>

          <!-- reason (cancel) -->
          <Transition name="ws-slide">
            <div v-if="panel === 'cancel' && !stopAsk" class="rounded-xl bg-rose-50/60 ring-1 ring-rose-200/70 p-3 space-y-2">
              <div class="flex flex-wrap gap-1.5">
                <button v-for="rs in reasons" :key="rs"
                        class="h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1 transition-all"
                        :class="cancelReason === rs ? 'text-white bg-rose-600 ring-rose-600' : 'text-rose-700 bg-white ring-rose-200 hover:bg-rose-100'"
                        @click="cancelReason = rs">{{ rs }}</button>
              </div>
              <button class="h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50"
                      :disabled="!cancelReason || busy" @click="submitCancel">{{ t('cf.cancelConfirm') }}</button>
            </div>
          </Transition>

          <!-- The hand-over used to be a panel behind a violet icon in the
               contact row here, and another inside an expanded row on the
               rescue board — two doors, in two places, on two of the eight
               surfaces, and in four days no human filed anything through
               either. It is one icon in the header now, on every screen,
               and it already knows which card is open (useCsContext). -->

          <!-- A lead may read a card somebody is working; the decision row
               below is hidden for them, because acting on it would take the
               customer out from under the person on the phone. -->
          <div v-if="readOnly" class="rounded-xl bg-amber-50 ring-1 ring-amber-200 px-3.5 py-2 text-[12px] text-amber-800 flex items-center gap-2">
            <Icon name="eye" :size="14" />{{ t('ws.readOnly') }}
          </div>

          <!-- Blocked customer: the warning IS the interface -->
          <div v-if="isBlocked" class="rounded-xl bg-rose-600 text-white px-4 py-2.5 flex items-center gap-2.5">
            <Icon name="shield-alert" :size="16" />
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-bold">{{ t('ws.blockedTitle') }}</div>
              <div class="text-[11px] opacity-90 truncate">{{ cust?.flag?.note || t('ws.blockedHint') }} · {{ cust?.flag?.by?.split('@')[0] }} · {{ local(cust?.flag?.at) }}</div>
            </div>
          </div>

          <!-- THE decision row — only while the order is still ours. The
               clickable history lands the agent on delivered / returned /
               cancelled orders, where every one of these posts is rejected
               by the backend; offering them was a guaranteed error toast. -->
          <div v-if="inLane && !readOnly" class="flex flex-wrap gap-2">
            <button class="ws-decide flex-[2] min-w-[160px] text-white"
                    :class="isBlocked ? (confirmArmed ? 'bg-rose-600 hover:bg-rose-700' : 'bg-stone-400 hover:bg-stone-500') : 'bg-emerald-600 hover:bg-emerald-700'"
                    :disabled="busy" @click="onConfirm">
              <Icon name="check" :size="16" />
              <span>{{ isBlocked && confirmArmed ? t('ws.confirmAnyway') : t('cf.actConfirm') }}</span>
              <kbd>1</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[120px] bg-amber-50 text-amber-700 ring-1 ring-amber-200 hover:bg-amber-100" :disabled="busy" @click="decide('dna')">
              <Icon name="phone-off" :size="14" /><span>{{ t('cf.actDna') }}</span> <kbd>2</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[120px] bg-sky-50 text-sky-700 ring-1 ring-sky-200 hover:bg-sky-100" :disabled="busy" @click="decide('followup')">
              <Icon name="clock" :size="14" /><span>{{ t('cf.actFollowup') }}</span> <kbd>3</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[120px] bg-white text-rose-600 ring-1 ring-rose-200 hover:bg-rose-50" :disabled="busy"
                    :class="panel === 'cancel' ? 'ring-2' : ''"
                    @click="panel = panel === 'cancel' ? '' : 'cancel'">
              <Icon name="x" :size="14" /><span>{{ t('rs.actCancel') }}</span> <kbd>4</kbd>
            </button>
          </div>

          <!-- Not-Delivered decisions: Rescue's action set, run through
               rescue.act so the transitions live in one place — same engine
               the tab's inline buttons use. -->
          <div v-if="isNdCard" class="flex flex-wrap gap-2">
            <button class="ws-decide flex-[2] min-w-[160px] text-white bg-emerald-600 hover:bg-emerald-700"
                    :disabled="busy" @click="decideNd('redeliver')">
              <Icon name="refresh-cw" :size="15" /><span>{{ t('rs.actRedeliver') }}</span> <kbd>1</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[120px] bg-violet-50 text-violet-700 ring-1 ring-violet-200 hover:bg-violet-100"
                    :disabled="busy" @click="decideNd('reship')">
              <Icon name="send" :size="14" /><span>{{ t('rs.actReship') }}</span> <kbd>2</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[120px] bg-amber-50 text-amber-700 ring-1 ring-amber-200 hover:bg-amber-100"
                    :disabled="busy" @click="decideNd('dna')">
              <Icon name="phone-off" :size="14" /><span>{{ t('cf.actDna') }}</span> <kbd>3</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[120px] bg-white text-rose-600 ring-1 ring-rose-200 hover:bg-rose-50"
                    :disabled="busy" :class="panel === 'cancel' ? 'ring-2' : ''"
                    @click="panel = panel === 'cancel' ? '' : 'cancel'">
              <Icon name="x" :size="14" /><span>{{ t('rs.actCancel') }}</span> <kbd>4</kbd>
            </button>
          </div>

          <!-- Duplicated: the agent reached the customer — decide here, no
               reopen detour. Same four decisions, plus "back in the queue"
               for when the call is not for now. -->
          <div v-else-if="isDupCard" class="flex flex-wrap gap-2">
            <button class="ws-decide flex-[2] min-w-[160px] text-white"
                    :class="isBlocked ? (confirmArmed ? 'bg-rose-600 hover:bg-rose-700' : 'bg-stone-400 hover:bg-stone-500') : 'bg-emerald-600 hover:bg-emerald-700'"
                    :disabled="busy" @click="onConfirm">
              <Icon name="check" :size="16" />
              <span>{{ isBlocked && confirmArmed ? t('ws.confirmAnyway') : t('cf.actConfirm') }}</span>
              <kbd>1</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[120px] bg-amber-50 text-amber-700 ring-1 ring-amber-200 hover:bg-amber-100" :disabled="busy" @click="decide('dna')">
              <Icon name="phone-off" :size="14" /><span>{{ t('cf.actDna') }}</span> <kbd>2</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[120px] bg-sky-50 text-sky-700 ring-1 ring-sky-200 hover:bg-sky-100" :disabled="busy" @click="decide('followup')">
              <Icon name="clock" :size="14" /><span>{{ t('cf.actFollowup') }}</span> <kbd>3</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[120px] bg-white text-rose-600 ring-1 ring-rose-200 hover:bg-rose-50" :disabled="busy"
                    :class="panel === 'cancel' ? 'ring-2' : ''"
                    @click="panel = panel === 'cancel' ? '' : 'cancel'">
              <Icon name="x" :size="14" /><span>{{ t('rs.actCancel') }}</span> <kbd>4</kbd>
            </button>
            <button class="ws-decide flex-1 min-w-[150px] bg-stone-50 text-stone-600 ring-1 ring-stone-200 hover:bg-stone-100"
                    :disabled="busy" @click="decide('reopen')">
              <Icon name="rotate-ccw" :size="14" /><span>{{ t('cf.bulkReopen') }}</span> <kbd>5</kbd>
            </button>
          </div>

          <div v-if="!inLane && !isNdCard && !isDupCard" class="rounded-xl bg-stone-50 ring-1 ring-stone-200/70 px-3.5 py-2.5 text-[12px] text-stone-500">
            {{ t('ws.outOfLane') }}
          </div>

          <!-- note + activity -->
          <div class="flex items-center gap-2 flex-wrap">
            <button class="text-[11.5px] font-semibold text-stone-500 hover:text-stone-800 inline-flex items-center gap-1"
                    @click="panel = panel === 'note' ? '' : 'note'">
              <Icon name="edit" :size="12" />{{ t('ws.addNote') }} <kbd class="text-[9px] font-mono text-stone-400 border border-stone-200 rounded px-1">M</kbd>
            </button>
            <button class="text-[11.5px] font-semibold text-stone-500 hover:text-stone-800 inline-flex items-center gap-1"
                    @click="toggleActivity">
              <Icon name="activity" :size="12" />{{ t('ws.activity') }}
              <span v-if="activity.length" class="text-[10px] tabular-nums text-stone-400">{{ activity.length }}</span>
            </button>
            <!-- The one in the top bar follows the card; this one is where
                 the agent's hand already is when the customer says something
                 that is not a confirmation decision. Same component, same
                 request — a second door, not a second feature. -->
            <button class="text-[11.5px] font-semibold text-violet-600 hover:text-violet-800 inline-flex items-center gap-1"
                    @click="panel = panel === 'cs' ? '' : 'cs'">
              <Icon name="message-circle" :size="12" />{{ t('cs.handTitle') }}
            </button>
          </div>
          <Transition name="ws-slide">
            <CsHandover v-if="panel === 'cs'" :order="active.name" :phone="active.phone || ''"
                        source="confirmation" @done="panel = ''" />
          </Transition>
          <Transition name="ws-slide">
            <div v-if="panel === 'note'" class="flex items-center gap-2 bg-stone-50 rounded-xl p-2.5">
              <input v-model="noteText" :placeholder="t('ws.notePh')" maxlength="400" dir="auto"
                     class="flex-1 h-9 ps-3 pe-3 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] focus:outline-none"
                     @keydown.enter="saveNote" />
              <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-stone-700 hover:bg-stone-800 disabled:opacity-50"
                      :disabled="!noteText.trim() || busy" @click="saveNote">{{ t('cf.saveContact') }}</button>
            </div>
          </Transition>
          <Transition name="ws-slide">
            <div v-if="showActivity" class="bg-stone-50 rounded-xl p-3 max-h-[220px] overflow-y-auto space-y-2">
              <div v-if="activityLoading" class="text-[12px] text-stone-400 text-center py-2">…</div>
              <template v-else>
                <div v-for="(a, i) in activity" :key="i" class="flex items-start gap-2 text-[11.5px]">
                  <span class="w-1.5 h-1.5 rounded-full bg-stone-300 mt-1.5 flex-shrink-0" />
                  <div class="min-w-0 flex-1">
                    <span class="text-stone-800" dir="auto">{{ a.text }}</span>
                    <span class="text-stone-400 tabular-nums ms-1.5">{{ a.by }} · {{ local(a.at).slice(5) }}</span>
                  </div>
                </div>
                <div v-if="!activity.length" class="text-[12px] text-stone-400 text-center py-2">{{ t('ws.noActivity') }}</div>
              </template>
            </div>
          </Transition>
        </div>
        </Transition>
      </div>

      <!-- RIGHT: who is this customer -->
      <div class="space-y-3 lg:sticky lg:top-3">
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3.5">
          <div class="text-[11.5px] font-semibold text-stone-700 mb-2">{{ t('ws.custTitle') }}</div>
          <div v-if="custLoading" class="h-16 rounded bg-stone-100 animate-pulse" />
          <template v-else-if="cust">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-[11px] font-bold rounded-md px-2 py-0.5 ring-1"
                    :class="custClass">{{ t('seg.' + (cust.seg || 'new'), cust.seg || '—') }}</span>
              <span v-if="cust.rate !== null && cust.rate !== undefined" class="text-[10.5px] text-stone-400 tabular-nums">{{ cust.rate }}% {{ t('ws.took') }}</span>
            </div>
            <div class="grid grid-cols-3 gap-2 text-center">
              <div><div class="text-[16px] font-bold tabular-nums text-stone-900">{{ cust.orders ?? '—' }}</div><div class="text-[9.5px] text-stone-400 uppercase">{{ t('ws.parcels') }}</div></div>
              <div><div class="text-[16px] font-bold tabular-nums text-emerald-600">{{ cust.delivered ?? '—' }}</div><div class="text-[9.5px] text-stone-400 uppercase">{{ t('ws.took') }}</div></div>
              <div><div class="text-[16px] font-bold tabular-nums text-rose-600">{{ cust.failed ?? '—' }}</div><div class="text-[9.5px] text-stone-400 uppercase">{{ t('ws.refused') }}</div></div>
            </div>
            <!-- Their past orders: the customer asks "and my last one?" and the
                 agent should not have to leave the call to find out. -->
            <div v-if="(cust.recent || []).length" class="mt-2.5 pt-2.5 border-t border-stone-100 space-y-1">
              <div class="text-[10px] font-semibold uppercase tracking-wide text-stone-400 mb-1">{{ t('ws.histTitle') }}</div>
              <!-- Each past order opens in the card: the customer asks about an
                   older parcel and the agent lands on it without leaving the call. -->
              <button v-for="o in cust.recent.slice(0, histOpen ? 12 : 4)" :key="o.order"
                      type="button"
                      class="w-full text-start flex items-center gap-2 text-[11px] tabular-nums rounded-md px-1 py-0.5 -mx-1 transition-colors group/hist"
                      :class="o.order === active?.name ? 'bg-[var(--accent-50)] ring-1 ring-[var(--accent-200)]' : 'hover:bg-stone-50'"
                      :title="o.order"
                      @click="openHistory(o)">
                <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :class="histDot(o)" />
                <span class="text-stone-400 flex-shrink-0">{{ local(o.at).slice(5) }}</span>
                <span class="text-stone-600 truncate flex-1" :title="o.track || o.status">{{ o.track || o.status }}</span>
                <span class="font-semibold text-stone-800 flex-shrink-0">{{ Math.round(o.total) }}</span>
                <Icon name="chevron-right" :size="11"
                      class="flex-shrink-0 text-stone-300 opacity-0 group-hover/hist:opacity-100 transition-opacity rtl:-scale-x-100"
                      :class="o.order === active?.name ? 'opacity-100 text-[var(--accent-600)]' : ''" />
              </button>
              <button v-if="cust.recent.length > 4" class="text-[10.5px] font-semibold text-[var(--accent-600)] hover:underline"
                      @click="histOpen = !histOpen">
                {{ histOpen ? t('common.less') : t('ws.histMore').replace('{n}', String(cust.recent.length - 4)) }}
              </button>
            </div>

            <!-- the decision about this customer, not just the data -->
            <div class="flex items-center gap-1.5 mt-2.5 pt-2.5 border-t border-stone-100">
              <button class="flex-1 h-8 rounded-lg text-[11px] font-bold ring-1 transition-colors disabled:opacity-50"
                      :class="cust.flag?.flag === 'blocked' ? 'text-white bg-rose-600 ring-rose-600' : 'text-rose-700 bg-rose-50 ring-rose-200 hover:bg-rose-100'"
                      :disabled="flagBusy" @click="setFlag(cust.flag?.flag === 'blocked' ? '' : 'blocked')">
                {{ cust.flag?.flag === 'blocked' ? t('ws.unblock') : t('ws.block') }}
              </button>
              <button class="flex-1 h-8 rounded-lg text-[11px] font-bold ring-1 transition-colors disabled:opacity-50"
                      :class="cust.flag?.flag === 'vip' ? 'text-white bg-emerald-600 ring-emerald-600' : 'text-emerald-700 bg-emerald-50 ring-emerald-200 hover:bg-emerald-100'"
                      :disabled="flagBusy" @click="setFlag(cust.flag?.flag === 'vip' ? '' : 'vip')">
                {{ cust.flag?.flag === 'vip' ? 'VIP ✓' : 'VIP' }}
              </button>
            </div>
            <div v-if="cust.flag" class="text-[10px] text-stone-400 mt-1.5 truncate">
              {{ cust.flag.by.split('@')[0] }} · {{ local(cust.flag.at) }}<template v-if="cust.flag.note"> · {{ cust.flag.note }}</template>
            </div>
          </template>
          <div v-else class="text-[11.5px] text-stone-400">—</div>
        </div>

        <div v-if="thread.length || threadLoading" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3.5">
          <div class="text-[11.5px] font-semibold text-stone-700 mb-2 flex items-center gap-1.5">
            <Icon name="message-circle" :size="12" class="text-emerald-600" />{{ t('cs.thread') }}
          </div>
          <div v-if="threadLoading" class="h-20 rounded bg-stone-100 animate-pulse" />
          <div v-else ref="threadBox" class="max-h-[300px] overflow-y-auto space-y-1.5">
            <template v-for="(m, i) in thread" :key="i">
              <!-- day separator whenever the calendar flips -->
              <div v-if="!i || local(m.at).slice(0, 10) !== local(thread[i - 1].at).slice(0, 10)" class="text-center pt-1">
                <span class="text-[9.5px] font-semibold text-stone-400 bg-stone-100 rounded-full px-2 py-0.5 tabular-nums">{{ local(m.at).slice(5, 10) }}</span>
              </div>
              <div class="flex" :class="m.in ? 'justify-start' : 'justify-end'">
                <div class="max-w-[85%] rounded-lg px-2.5 py-1.5 text-[11.5px]"
                     :class="m.in ? 'bg-stone-50 ring-1 ring-stone-200 text-stone-800' : 'bg-emerald-50 ring-1 ring-emerald-200 text-emerald-900'" dir="auto">
                  <div v-if="m.kind && m.kind !== 'text' && m.kind !== 'button'"
                       class="flex items-center gap-1.5 text-stone-500" :class="m.text ? 'mb-0.5' : ''">
                    <Icon :name="WA_KIND_ICON[m.kind] || 'file-text'" :size="12" />
                    <span class="text-[10.5px] font-medium">{{ t('wa.' + m.kind, m.kind) }}</span>
                  </div>
                  <template v-if="m.text">{{ m.text }}</template>
                  <div class="text-[9px] tabular-nums mt-0.5" :class="m.in ? 'text-stone-400' : 'text-emerald-700/70'">
                    {{ local(m.at).slice(11) }}<template v-if="!m.in"> · Justyol</template>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <SkuLookupModal ref="skuModal" />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { local, nowSite } from "@/lib/clock";
import { setCsContext } from "@/composables/useCsContext";
import SkuLookupModal from "@/components/SkuLookupModal.vue";
import CsHandover from "@/components/CsHandover.vue";
import { api, apiPost } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useToast } from "@/composables/useToast";

const { t } = useI18n();
const { success, warn } = useToast();

const board = ref(null);
const boardLoading = ref(true);
const active = ref(null);          // orders.detail payload
const activeRow = ref(null);       // the queue row (age/attempts/due)
const cardLoading = ref(false);
const serving = ref(false);
const busy = ref(false);
const skuModal = ref(null);
const panel = ref("");
const reasons = ref([]);
const cancelReason = ref("");
// Set when the backend hands the cancel over to api.stop: {stage, mode}.
const stopAsk = ref(null);
const cust = ref(null);
const custLoading = ref(false);
const histOpen = ref(false);
function openHistory(o) {
  // Same door as the queue: drive it through the URL so back/refresh land
  // on the order the agent was looking at.
  if (!o?.order || o.order === active.value?.name) return;
  gotoOrder(o.order);
}
function histDot(o) {
  const t2 = o.track || "";
  if (t2 === "Delivered") return "bg-emerald-500";
  if (t2 === "Delivery Exception" || t2 === "Failed Attempt") return "bg-rose-500";
  if (o.status === "Cancelled") return "bg-stone-300";
  return "bg-amber-400";
}
// The warehouse journey of THIS order — shown only once it has left the
// confirmation lane, because before that every step is still ahead of it.
const JOURNEY = [
  { key: "Pending", label: "ws.jPending" },
  { key: "Picked", label: "ws.jPicked" },
  { key: "Label Printed", label: "ws.jLabel" },
  { key: "Shipped", label: "ws.jShipped" },
  { key: "Delivered", label: "ws.jDelivered" },
];
const journey = computed(() => {
  const stage = active.value?.stage || "";
  const alias = { "Label Generated": "Label Printed", "Out For Delivery": "Shipped" };
  // Returned is a real terminal stage on 1,303 orders — it is NOT step zero,
  // and showing "in the queue" for a parcel that came back would be a lie.
  const returned = stage === "Returned";
  // Past the end: every step reads as done and NONE is highlighted as the
  // live one — the parcel came back, it never sat at "delivered".
  const at = returned ? JOURNEY.length
    : JOURNEY.findIndex((s2) => s2.key === (alias[stage] || stage));
  return { steps: JOURNEY, at: at < 0 ? 0 : at, returned,
           show: !!(active.value && (at > 0 || returned || active.value.awb)) };
});
// The carrier's own word. A failure must not wear the calm blue chip.
const trackBad = computed(() =>
  ["Delivery Exception", "Failed Attempt"].includes(active.value?.tracking_status));
const thread = ref([]);
const threadLoading = ref(false);
const threadBox = ref(null);
const WA_KIND_ICON = { image: "image", audio: "mic", video: "video",
  document: "file-text", location: "map-pin", reaction: "thumbs-up",
  flow: "file-text" };
// The latest message is the one that matters — land scrolled to the bottom.
watch(thread, async () => {
  await nextTick();
  if (threadBox.value) threadBox.value.scrollTop = threadBox.value.scrollHeight;
});
const amendItems = ref([]);
const discAmt = ref(null);
const discPct = ref(null);
const editName = ref("");
const editPhone = ref("");
const editCity = ref("");
const editAddress = ref("");
const caps = ref({ pct: 15, amt: 50 });

// SLA against the first-call clock. Queue-level: how many of MY pending rows
// already blew it. Card-level: this order's countdown, flipping to "late by".
const slaLate = computed(() => {
  const h = board.value?.slaHours || 6;
  // Always the SERVE PLAN, never the browsed list: on a retry list every row
  // has attempts, so the tile flashed a green "✓" while the real pending
  // queue was blowing its first-call SLA.
  return (plan.value?.rows || []).filter((r) => !r.attempts && r.ageH >= h).length;
});
const slaChip = computed(() => {
  const h = board.value?.slaHours || 6;
  // Order-first: the plan row is absent for deep-linked opens.
  const ageH = activeRow.value?.ageH ?? cardAgeH.value;
  if (ageH == null || cardAttempts.value) return null;   // first-touch clock only
  const leftMin = h * 60 - (ageH || 0) * 60;
  if (leftMin <= 0) {
    const over = Math.round(((ageH || 0) - h) * 10) / 10;
    return { text: t("ws.slaOver").replace("{h}", String(over)),
             cls: "text-white bg-rose-600 ring-rose-600" };
  }
  const hh = Math.floor(leftMin / 60);
  const mm = Math.round(leftMin % 60);
  return { text: t("ws.slaLeft").replace("{t}", hh ? `${hh}h${String(mm).padStart(2, "0")}` : `${mm}m`),
           cls: leftMin < 60 ? "text-amber-700 bg-amber-50 ring-amber-300"
                            : "text-emerald-700 bg-emerald-50 ring-emerald-200" };
});

const cardSeconds = ref(0);
let cardTick = null;
const cardTimer = computed(() => {
  const m = Math.floor(cardSeconds.value / 60);
  const sec = cardSeconds.value % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
});
// ── the game layer ──────────────────────────────────────────────────────
// Feedback, not information: every number here is already true elsewhere on
// the page, so reduced-motion can drop all of it without losing anything.
const pops = ref([]);
let _popId = 0;
function popCoin(action) {
  const cls = action === "confirm" ? "ws-pop-good"
    : action === "cancel" ? "ws-pop-bad" : "ws-pop-mid";
  const id = ++_popId;
  pops.value.push({ id, cls });
  setTimeout(() => { pops.value = pops.value.filter((x) => x.id !== id); }, 950);
}
// Once per day, the moment the ring closes — not on every load after it.
const celebrating = ref(false);
function maybeCelebrate() {
  if (dayPct.value < 100) return;
  const k = "lp_ws_hit_" + new Date().toISOString().slice(0, 10);
  try {
    if (sessionStorage.getItem(k)) return;
    sessionStorage.setItem(k, "1");
  } catch { return; }
  celebrating.value = true;
  setTimeout(() => { celebrating.value = false; }, 1800);
}
const _BURST = ["#34d399", "#fbbf24", "#f97316", "#a78bfa", "#38bdf8"];
function burstStyle(n) {
  const a = (n / 14) * 2 * Math.PI;
  return {
    "--dx": Math.cos(a) * (34 + (n % 3) * 14) + "px",
    "--dy": Math.sin(a) * (34 + (n % 3) * 14) + "px",
    background: _BURST[n % _BURST.length],
    animationDelay: (n % 4) * 40 + "ms",
  };
}

const dayPct = computed(() => {
  const tgt = board.value?.myTarget || 0;
  return tgt ? Math.round((myTotal.value * 100) / tgt) : 0;
});

const myTotal = computed(() =>
  Object.values(board.value?.mine || {}).reduce((a, b) => a + (b || 0), 0));
// The queue pane mirrors the SERVE PLAN (due call-backs first, then fresh) —
// not just the pending slice; the agent sees exactly what N will hand out.
const plan = ref(null);
const queueRows = computed(() =>
  tabMode.value ? tabRows.value : (plan.value?.rows || []));
const nextDueAt = computed(() => plan.value?.nextDueAt || "");
const dueCount = computed(() => plan.value?.dueCount || 0);
const KIND_CLS = {
  dna: "text-amber-700 bg-amber-100",
  followup: "text-sky-700 bg-sky-100",
  nd: "text-orange-700 bg-orange-100",
  duplicated: "text-violet-700 bg-violet-100",
};

// The card tells the ORDER's truth from the order itself (orders.detail) —
// never from the plan row, which deep-linked opens aren't part of.
// LIVE statuses only — inLane hangs off this map, so Not Delivered and
// Duplicated must NOT be in it: their cards carry their own action rows
// (rescue's set, and Reopen) below, never the confirm row.
const ST_KIND = { "Did not Answer": "dna", "Follow Up": "followup" };
const ROW_KIND = { ...ST_KIND, "Not Delivered": "nd", "Duplicated": "duplicated" };
// Is this order still ours to decide? The clickable history can land the
// agent on a delivered, returned or cancelled order — the backend rejects a
// decision there, so the buttons must not be offered in the first place.
// A Not Delivered order splits by what the WAREHOUSE holds, not by the status
// alone. With no parcel out there — which is the normal case, the status being
// a verdict on the customer rather than a failed shipment — the question is the
// ordinary confirmation one and it gets the ordinary buttons, ending in the
// same Confirmed / Cancelled as any other order. Only a live parcel makes it
// Rescue's problem, and only then does Redeliver / Reship mean anything.
const ndHasParcel = computed(() => {
  const st = active.value?.stage || "";
  return !!st && st !== "Pending";
});
const isNd = computed(() => active.value?.sales_status === "Not Delivered");
const inLane = computed(() => {
  const st = active.value?.sales_status;
  if (st === "Not Delivered") return !ndHasParcel.value;
  return !!st && (st === "Pending" || !!ST_KIND[st]);
});
// Two more cards the workspace knows how to work — the reason the pin
// button and the two tab buttons exist on Not Delivered and Duplicated.
const isNdCard = computed(() => isNd.value && ndHasParcel.value);
const isDupCard = computed(() => active.value?.sales_status === "Duplicated");
const stChip = computed(() => {
  const st = active.value?.sales_status;
  if (!st) return null;
  const kind = ST_KIND[st];
  if (kind) return { label: t("ws.k_" + kind), cls: KIND_CLS[kind] };
  if (st === "Pending") return { label: t("cf.tabPending"), cls: "text-[var(--accent-700)] bg-[var(--accent-100)]" };
  if (st === "Not Delivered")
    return { label: t("cf.tabNotDelivered"), cls: "text-orange-700 bg-orange-100" };
  const done = { Confirmed: "confirmed", Cancelled: "cancelled",
                 Duplicated: "duplicated" }[st];
  return { label: done ? t("cf.st" + done) : st, cls: "text-stone-600 bg-stone-200" };
});
const cardAgeH = computed(() => {
  const c = active.value?.created;
  if (!c) return null;
  return Math.max(0, Math.round((Date.now() - new Date(c.replace(" ", "T")).getTime()) / 3600000));
});
const cardAge = computed(() => {
  const h = cardAgeH.value;
  return h == null ? "" : (h < 48 ? h + "h" : Math.round(h / 24) + "d");
});
const cardAttempts = computed(() =>
  active.value?.attempts ?? activeRow.value?.attempts ?? 0);
const miniActivity = ref([]);

// Board-tab list mode: the agent picked a queue on the Confirmation board and
// works it here start to finish — no bouncing back after every decision.
const WORK_TAB_LABEL = { pending: "cf.tabPending", dna: "cf.tabDna",
  followup: "cf.tabFollowup", monitor: "cf.tabMonitor",
  notdelivered: "cf.tabNotDelivered", duplicated: "cf.tabDuplicated" };
const tabMode = ref("");
const tabRows = ref([]);
const tabLoading = ref(false);
let tabSeq = 0;
async function loadTabQueue(tb) {
  const seq = ++tabSeq;   // Back/Forward between two tabs: newest reply wins
  tabLoading.value = true;
  try {
    const r = await api("confirmation.board", { tab: tb, limit: 50 });
    if (seq !== tabSeq) return;
    tabRows.value = (r?.rows || []).map((x) => ({
      order: x.order, customer: x.customer, total: x.total, ageH: x.ageH,
      attempts: x.attempts, due: !!x.due, kind: ROW_KIND[x.status] || (KIND_CLS[tb] ? tb : "pending"),
    }));
  } catch (e) { if (seq === tabSeq) tabRows.value = []; }
  if (seq === tabSeq) tabLoading.value = false;
}
function exitTabMode() {
  tabMode.value = "";
  tabRows.value = [];
  router.replace({ query: {} });
}
function gotoOrder(name) {
  // Drive navigation through the URL — the query watcher opens the card, and
  // refresh/back land exactly where the agent was.
  router.replace({ query: { ...(tabMode.value ? { tab: tabMode.value } : {}), order: name } });
}
async function advanceTab(decided) {
  const idx = tabRows.value.findIndex((r) => r.order === decided);
  tabRows.value = tabRows.value.filter((r) => r.order !== decided);
  const next = tabRows.value[Math.min(Math.max(idx, 0), tabRows.value.length - 1)];
  if (next) gotoOrder(next.order);
  else {
    success(t("ws.listDone"));
    exitTabMode();
    await _serve(false);
  }
}
const waUrl = computed(() =>
  "https://wa.me/" + String(active.value?.phone || "").replace(/\D/g, ""));
const isBlocked = computed(() => cust.value?.flag?.flag === "blocked");
const confirmArmed = ref(false);
const noteText = ref("");
const showActivity = ref(false);
const activity = ref([]);
const activityLoading = ref(false);
const flagBusy = ref(false);

// One glance = one verdict. Manual flag wins; otherwise the measured segment.
const grade = computed(() => {
  const c = cust.value;
  if (!c) return null;
  if (c.flag?.flag === "blocked")
    return { label: t("ws.gBlocked"), cls: "text-white bg-rose-600 ring-rose-600", hint: c.flag.note || "" };
  if (c.flag?.flag === "vip")
    return { label: "VIP ★", cls: "text-white bg-emerald-600 ring-emerald-600", hint: "" };
  const map = {
    vip:   { label: "A ★", cls: "text-emerald-700 bg-emerald-50 ring-emerald-200" },
    good:  { label: "B",   cls: "text-emerald-700 bg-emerald-50 ring-emerald-200" },
    new:   { label: t("ws.gNew"), cls: "text-stone-600 bg-stone-50 ring-stone-200" },
    watch: { label: "C",   cls: "text-amber-700 bg-amber-50 ring-amber-200" },
    risk:  { label: "D",   cls: "text-amber-700 bg-amber-50 ring-amber-200" },
    black: { label: "E ⚠", cls: "text-rose-700 bg-rose-50 ring-rose-200" },
  };
  const g = map[c.seg] || map.new;
  return { ...g, hint: c.rate !== null && c.rate !== undefined ? `${c.rate}%` : "" };
});

function onConfirm() {
  // A blocked customer needs a SECOND press — the agent can still confirm
  // (the block is a warning we own, not a law), but never by reflex.
  if (isBlocked.value && !confirmArmed.value) {
    confirmArmed.value = true;
    setTimeout(() => { confirmArmed.value = false; }, 4000);
    return;
  }
  confirmArmed.value = false;
  decide("confirm");
}

async function saveNote() {
  if (!active.value || !noteText.value.trim()) return;
  busy.value = true;
  try {
    await apiPost("confirmation.add_note", { order: active.value.name, note: noteText.value.trim() });
    activity.value = [{ by: "me", text: noteText.value.trim(), at: nowSite().slice(0, 16) }, ...activity.value];
    noteText.value = "";
    panel.value = "";
    success(t("ws.noteSaved"));
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

async function toggleActivity() {
  showActivity.value = !showActivity.value;
  if (!showActivity.value || !active.value) return;
  activityLoading.value = true;
  try {
    const r = await api("confirmation.order_activity", { order: active.value.name });
    activity.value = r?.rows || [];
  } catch (e) {
    activity.value = [];
  } finally {
    activityLoading.value = false;
  }
}

async function setFlag(flag) {
  if (!active.value?.phone) return;
  flagBusy.value = true;
  try {
    const r = await apiPost("customers.flag_customer", { phone: active.value.phone, flag });
    if (cust.value) cust.value = { ...cust.value, flag: r.flag || null };
    success(flag === "blocked" ? t("ws.blockedSet") : flag === "vip" ? "VIP ✓" : t("ws.flagCleared"));
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    flagBusy.value = false;
  }
}

const custClass = computed(() => {
  const s = cust.value?.seg || "";
  if (s === "black") return "text-rose-700 bg-rose-50 ring-rose-200";
  if (s === "vip" || s === "good") return "text-emerald-700 bg-emerald-50 ring-emerald-200";
  return "text-stone-600 bg-stone-50 ring-stone-200";
});
const amendDirty = computed(() =>
  (discAmt.value || 0) > 0 || (discPct.value || 0) > 0
  || amendItems.value.some((i) => i.qty !== i._orig));

async function loadBoard() {
  boardLoading.value = true;
  try {
    const [b, p2] = await Promise.all([
      api("confirmation.board", { tab: "pending", limit: 1 }),
      api("confirmation.next_up", { limit: 25 }),
    ]);
    board.value = b;
    plan.value = p2;
    syncFromBoard(b);
    if (b?.reasons?.length) reasons.value = b.reasons;
    // A deep-linked open usually beats this load — re-resolve the plan row
    // so the due badge / attempts / SLA chip appear once the plan lands.
    if (active.value && !activeRow.value) {
      activeRow.value = queueRows.value.find((r) => r.order === active.value.name) || null;
    }
  } catch (e) {
    // The queue pane is a helper — but reasons/caps ride this payload and a
    // cancel is impossible without them, so one quiet retry beats waiting
    // for the 120s poll.
    if (!board.value && !retryTimer) {
      retryTimer = setTimeout(() => { retryTimer = null; if (!board.value) loadBoard(); }, 15000);
    }
  }
  boardLoading.value = false;
}

function syncFromBoard(b) {
  if (!b) return;
  caps.value = { pct: b.discountCapPct ?? 15, amt: b.discountCapAmt ?? 50 };
}

let openSeq = 0;
async function openOrder(name) {
  panel.value = "";
  cancelReason.value = "";
  stopAsk.value = null;
  confirmArmed.value = false;
  noteText.value = "";
  showActivity.value = false;
  activity.value = [];
  cardSeconds.value = 0;
  clearInterval(cardTick);
  cardTick = setInterval(() => { cardSeconds.value += 1; }, 1000);
  // Hold it for as long as the call lasts, not for a flat five minutes —
  // and let go on its own if the laptop closes.
  clearInterval(holdTimer);
  holdTimer = setInterval(() => {
    if (active.value?.name) apiPost("confirmation.hold_open", { order: active.value.name }).catch(() => {});
  }, 60000);
  cardLoading.value = true;
  const seq = ++openSeq;    // rapid clicks: only the LATEST response paints
  try {
    // Take the card BEFORE loading it. The block has to be at open, not at
    // the decision: the old guard refused the button press, which is after
    // the agent has already phoned a customer their colleague was phoning.
    const lock = await apiPost("confirmation.open_order", { order: name });
    if (seq !== openSeq) return;
    if (lock && lock.ok === false) {
      busyBy.value = (lock.by || "").split("@")[0];
      busySince.value = lock.since || "";
      active.value = null;
      activeRow.value = null;
      cardLoading.value = false;
      // Two seconds, then move them on. Jumping instantly reads as a broken
      // screen; leaving them on a dead card reads as a broken portal.
      clearTimeout(busyTimer);
      busyTimer = setTimeout(() => { busyBy.value = ""; serveNext(false); }, 2000);
      return;
    }
    readOnly.value = !!(lock && lock.readOnly);
    busyBy.value = "";
    const det = await api("orders.detail", { name });
    if (seq !== openSeq) return;
    if (!det || !det.name) {
      // orders.detail returns {} for an unknown/renamed order — never render
      // a blank card with live decision buttons posting order: undefined.
      warn(t("cf.loadFail"), name);
      active.value = null;
      activeRow.value = null;
      return;
    }
    active.value = det;
    // The header's CS button follows the card the agent is actually on.
    setCsContext(det.name, det.phone || "", det.customer || "");
    activeRow.value = queueRows.value.find((r) => r.order === name) || null;
    amendItems.value = (active.value.items || []).map((i) => ({
      idx: i.idx, item_code: i.sku, name: i.name,
      qty: Math.round(i.qty), _orig: Math.round(i.qty),
    }));
    discAmt.value = null; discPct.value = null;
    editName.value = active.value.customer || "";
    editPhone.value = active.value.phone || "";
    editCity.value = active.value.city || "";
    editAddress.value = active.value.address_line || "";
    miniActivity.value = [];
    if (det.sales_status !== "Pending" || (det.attempts || 0) > 0) {
      api("confirmation.order_activity", { order: name, limit: 3 })
        .then((r) => { if (seq === openSeq) miniActivity.value = r?.rows || []; })
        .catch(() => {});
    }
    loadContext();
  } catch (e) {
    if (seq !== openSeq) return;
    warn(t("cf.loadFail"), String(e.message || e));
    active.value = null;
    activeRow.value = null;
  } finally {
    if (seq === openSeq) cardLoading.value = false;
  }
}

let ctxSeq = 0;
async function loadContext() {
  const phone = active.value?.phone;
  cust.value = null; thread.value = [];
  if (!phone) return;
  const seq = ++ctxSeq;
  custLoading.value = true;
  threadLoading.value = true;
  api("customers.card", { phone }).then((c) => { if (seq === ctxSeq) cust.value = c; })
    .catch(() => {}).finally(() => { if (seq === ctxSeq) custLoading.value = false; });
  api("tickets.wa_thread", { phone, limit: 20 }).then((r) => { if (seq === ctxSeq) thread.value = r?.messages || []; })
    .catch(() => { if (seq === ctxSeq) thread.value = []; })
    .finally(() => { if (seq === ctxSeq) threadLoading.value = false; });
}

async function serveNext(skipCurrent = false) {
  // Guarded entry for N / the button only. decide() chains _serve() directly:
  // its own busy flag is still up here, and this guard silently ate the
  // auto-advance (decision recorded, next order never served).
  if (serving.value || busy.value) return;
  if (tabMode.value) {
    // List mode: N walks the picked queue instead of asking serve-next.
    const rows = tabRows.value;
    if (rows.length) {
      const idx = rows.findIndex((r) => r.order === active.value?.name);
      const next = rows[(idx + 1) % rows.length];
      if (next && next.order !== active.value?.name) return gotoOrder(next.order);
    }
    success(t("ws.listDone"));
    exitTabMode();
  }
  return _serve(skipCurrent);
}

// The shared pool's depth. Cheap (one indexed count, 12 ms on production),
// refreshed with the board rather than on its own timer.
// Somebody else has this customer's card open.
const busyBy = ref("");
const busySince = ref("");
const readOnly = ref(false);
let busyTimer = null;
let holdTimer = null;

const freshN = ref(0);
// The button turns into the alarm only when this agent can actually act on
// it — a red button that serves somebody else's work is a lie.
const freshAlarm = computed(() => freshN.value > 0 && freshCanTake.value);
const freshOldest = ref(0);
const freshCanTake = ref(true);
async function loadFresh() {
  try {
    const r = await api("confirmation.fresh_waiting");
    freshN.value = r.n || 0;
    freshOldest.value = r.oldestMin || 0;
    freshCanTake.value = r.canTake !== false;
  } catch { freshN.value = 0; }
}

const poolN = ref(0);
const poolBlock = ref("");
const team = ref([]);
const teamOpen = ref(false);
async function loadPool() {
  try {
    const r = await api("confirmation.pool_depth");
    poolN.value = r.enabled ? (r.n || 0) : 0;
    poolBlock.value = r.block || "";
  } catch { poolN.value = 0; poolBlock.value = ""; }
}
// Leads only — the endpoint refuses everyone else, so a quiet failure here
// simply means the popover stays empty for an agent.
async function toggleTeam() {
  teamOpen.value = !teamOpen.value;
  if (!teamOpen.value || team.value.length) return;
  try { team.value = (await api("confirmation.pool_team")).team || []; }
  catch { team.value = []; }
}

async function _serve(skipCurrent = false) {
  serving.value = true;
  try {
    // Walking away UNDECIDED marks the order skipped for 10 minutes —
    // otherwise it comes straight back as the top priority. After a decision
    // the order left the queue on its own, so no marker.
    const skip = skipCurrent && active.value ? active.value.name : undefined;
    const r = await apiPost("confirmation.next_order", skip ? { skip } : {});
    if (r.order) {
      await openOrder(r.order);
      // Say where it came from. An order arriving out of a colleague's slice
      // without a word is the kind of thing a team notices and resents; said
      // out loud it reads as covering for each other, which is what it is.
      if (r.fromPool) {
        success(t("ws.fromPool"), r.tookFrom ? String(r.tookFrom).split("@")[0] : "");
      }
    }
    else {
      active.value = null;
      activeRow.value = null;
      cust.value = null;
      thread.value = [];
      activity.value = [];
      clearInterval(cardTick);
      success(t("ws.allDone"));
    }
    // The deep-link marker went stale the moment we moved on — a refresh
    // must not resurrect a decided order's card.
    if (route.query.order) router.replace({ query: {} });
  } catch (e) {
    warn(t("cf.loadFail"), String(e.message || e));
  } finally {
    serving.value = false;
    loadPool();
    loadFresh();
  }
}

// A cancel from the panel posts to whichever engine owns this card.
function submitCancel() {
  if (isNdCard.value) decideNd("cancel", cancelReason.value);
  else decide("cancel", cancelReason.value);
}

// Rescue decisions for a Not-Delivered card — mirrors decide(), but through
// rescue.act, because a shipped-then-failed parcel's transitions belong to
// the rescue engine (confirmation.act rightly refuses them).
async function decideNd(action, note) {
  if (!active.value) return;
  busy.value = true;
  try {
    await apiPost("rescue.act", { id: active.value.name, action, note });
    success(t(`rs.done_${action}`), active.value.name);
    popCoin(action === "cancel" ? "cancel" : action === "dna" ? "dna" : "confirm");
    panel.value = ""; cancelReason.value = "";
    // dna re-queues with a retry timer; every other decision removes it.
    if (action !== "dna") {
      if (plan.value?.rows) plan.value.rows = plan.value.rows.filter((r) => r.order !== active.value.name);
      if (tabMode.value) { await advanceTab(active.value?.name); busy.value = false; return; }
    } else if (tabMode.value) { await advanceTab(active.value?.name); busy.value = false; return; }
    await _serve(false);
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

async function decide(action, note) {
  if (!active.value) return;
  busy.value = true;
  try {
    const res = await apiPost("confirmation.act", { order: active.value.name, action, note });
    success(t(`cf.done_${action}`), active.value.name + (res.attempts ? ` · ×${res.attempts}` : ""));
    if (board.value?.mine && action in board.value.mine) board.value.mine[action]++;
    popCoin(action);
    maybeCelebrate();
    if (plan.value?.rows) plan.value.rows = plan.value.rows.filter((r) => r.order !== active.value.name);
    panel.value = ""; cancelReason.value = "";
    if (tabMode.value) await advanceTab(active.value?.name);
    else await _serve(false);
  } catch (e) {
    // The warehouse already has it. That is an answer, not a failure — ask
    // the server what can still be done and offer exactly that.
    if (e.key === "stopNeeded") {
      try {
        const p = await api("stop.preview", { order: active.value.name });
        stopAsk.value = { stage: p.stage, mode: p.mode };
      } catch (_) {
        stopAsk.value = { stage: e.arg || "picking", mode: "stop" };
      }
      return;
    }
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

async function submitStop() {
  if (!active.value || !stopAsk.value) return;
  const mode = stopAsk.value.mode;
  busy.value = true;
  try {
    await apiPost("stop.request_stop", {
      order: active.value.name, reason: cancelReason.value });
    success(t("stop.done_" + mode), active.value.name);
    stopAsk.value = null; panel.value = ""; cancelReason.value = "";
    // A recall leaves the order live on purpose — the parcel is still out
    // there and somebody has to chase it — so only a real stop takes the
    // card off this queue.
    if (mode === "cancel_now" || mode === "stop") {
      popCoin("cancel");
      if (plan.value?.rows) plan.value.rows = plan.value.rows.filter((r) => r.order !== active.value.name);
      if (tabMode.value) await advanceTab(active.value?.name);
      else await _serve(false);
    }
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

async function applyAmend() {
  if (!active.value) return;
  busy.value = true;
  try {
    // Send the ROW, not the code — the same SKU can appear on several lines.
    const items = amendItems.value.filter((i) => i.qty !== i._orig)
      .map((i) => ({ item_code: i.item_code, qty: i.qty }));
    const res = await apiPost("confirmation.amend_order", {
      order: active.value.name,
      discount_amount: discAmt.value || undefined,
      discount_percent: discPct.value || undefined,
      items: items.length ? items : undefined,
    });
    success(t("ws.amended"), `${res.order} · ${Math.round(res.total)} MAD`);
    panel.value = "";
    if (plan.value?.rows) {
      plan.value.rows = plan.value.rows.filter((r) => r.order !== res.amendedFrom);
    }
    await openOrder(res.order);
    loadBoard();
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

async function saveContact() {
  if (!active.value) return;
  busy.value = true;
  try {
    await apiPost("confirmation.update_contact", {
      order: active.value.name,
      name: editName.value.trim() || undefined,
      phone: editPhone.value.trim() || undefined,
      city: editCity.value.trim() || undefined,
      address_line: editAddress.value.trim() || undefined,
    });
    active.value.customer = editName.value.trim() || active.value.customer;
    active.value.phone = editPhone.value.trim() || active.value.phone;
    active.value.city = editCity.value.trim() || active.value.city;
    panel.value = "";
    success(t("cf.contactSaved"), active.value.name);
    loadContext();   // history + thread must follow the corrected number
  } catch (e) {
    warn(t("cf.actFail"), String(e.message || e));
  } finally {
    busy.value = false;
  }
}

function hideImg(e) { if (e && e.target) e.target.style.display = "none"; }

// Keyboard: n = next, 1..4 decisions, d = amend, f = fix contact. Silent when
// the focus is in an input.
function onKey(e) {
  const tag = (e.target?.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select"
      || e.target?.isContentEditable || e.metaKey || e.ctrlKey || e.altKey) return;
  // Physical key codes, not characters — on the Arabic layout e.key is
  // ن/د/م and every advertised shortcut was silently dead.
  const c = e.code;
  if (c === "KeyN") {
    // Never nuke a half-built cancel with a stray N.
    if (panel.value === "cancel" && cancelReason.value) return;
    e.preventDefault();
    serveNext(true);
  }
  // While a new card is loading, `active` still holds the old order — a
  // keystroke here decided (or skipped) the wrong one.
  else if (!active.value || busy.value || cardLoading.value) return;
  // Each card kind answers its own digits — the live map used to fire on ANY
  // card, posting a confirm at an order the backend was guaranteed to refuse.
  else if (isNdCard.value) {
    if (c === "Digit1" || c === "Numpad1") decideNd("redeliver");
    else if (c === "Digit2" || c === "Numpad2") decideNd("reship");
    else if (c === "Digit3" || c === "Numpad3") decideNd("dna");
    else if (c === "Digit4" || c === "Numpad4") panel.value = panel.value === "cancel" ? "" : "cancel";
    else if (c === "KeyM") panel.value = panel.value === "note" ? "" : "note";
    return;
  }
  else if (isDupCard.value) {
    if (c === "Digit1" || c === "Numpad1") onConfirm();
    else if (c === "Digit2" || c === "Numpad2") decide("dna");
    else if (c === "Digit3" || c === "Numpad3") decide("followup");
    else if (c === "Digit4" || c === "Numpad4") panel.value = panel.value === "cancel" ? "" : "cancel";
    else if (c === "Digit5" || c === "Numpad5") decide("reopen");
    else if (c === "KeyM") panel.value = panel.value === "note" ? "" : "note";
    return;
  }
  else if (!inLane.value) return;
  else if (c === "Digit1" || c === "Numpad1") onConfirm();
  else if (c === "Digit2" || c === "Numpad2") decide("dna");
  else if (c === "Digit3" || c === "Numpad3") decide("followup");
  else if (c === "Digit4" || c === "Numpad4") panel.value = panel.value === "cancel" ? "" : "cancel";
  else if (c === "KeyD") panel.value = panel.value === "amend" ? "" : "amend";
  else if (c === "KeyF") panel.value = panel.value === "contact" ? "" : "contact";
  else if (c === "KeyM") panel.value = panel.value === "note" ? "" : "note";
}

const route = useRoute();
const router = useRouter();
onMounted(() => {
  loadBoard();
  loadPool();
  loadFresh();
  // Deep link from the Confirmation board: open THIS order (and, in list
  // mode, THIS queue) instead of whatever serve-next would pick.
  const tb = String(route.query.tab || "");
  const o = String(route.query.order || "");
  if (WORK_TAB_LABEL[tb]) {
    tabMode.value = tb;
    loadTabQueue(tb).then(() => {
      if (!o && tabRows.value.length) gotoOrder(tabRows.value[0].order);
    });
  }
  if (o) openOrder(o);
  window.addEventListener("keydown", onKey);
});
// Query changes don't remount (router-view keys on name+params) — Back/
// Forward between ?order= entries and repeat board clicks land here.
watch(() => route.query.order, (o) => {
  const name = String(o || "");
  if (name && name !== active.value?.name) openOrder(name);
});
watch(() => route.query.tab, (tb2) => {
  const tb = String(tb2 || "");
  if (tb === tabMode.value) return;
  if (WORK_TAB_LABEL[tb]) {
    tabMode.value = tb;
    loadTabQueue(tb);
  } else {
    tabMode.value = "";
    tabRows.value = [];
  }
});
// The plan pane goes stale over a shift — silent refresh like every queue.
let retryTimer = null;
const planTimer = setInterval(() => {
  if (document.visibilityState === "visible" && !serving.value && !busy.value
      && !cardLoading.value) loadBoard();
}, 120000);
// Separate and far more often than the board: a new order's whole value is
// how fast somebody calls it, and the board reload costs too much to run at
// this rate. Safe while the agent is on a call — it only lights a button,
// it never moves the card under them.
const freshTimer = setInterval(() => {
  if (document.visibilityState === "visible") { loadFresh(); loadPool(); }
}, 30000);
onUnmounted(() => {
  clearTimeout(retryTimer);
  clearInterval(planTimer);
  clearInterval(freshTimer);
  clearInterval(cardTick);
  clearInterval(holdTimer);
  clearTimeout(busyTimer);
  window.removeEventListener("keydown", onKey);
  if (active.value) apiPost("confirmation.release_order", { order: active.value.name }).catch(() => {});
});
</script>

<style scoped>
.ws-oos {
  background: linear-gradient(135deg, rgb(255 241 242), rgb(255 228 230));
  box-shadow: inset 0 0 0 1px rgb(253 164 175 / .7);
  animation: ws-oos-in .35s cubic-bezier(.2,.7,.3,1);
}
@keyframes ws-oos-in {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}
.ws-contact {
  display: inline-flex; align-items: center; justify-content: center;
  width: 38px; height: 38px; border-radius: 10px;
  box-shadow: inset 0 0 0 1px var(--tw-ring-color, rgb(231 229 228));
}
.ws-decide {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  height: 46px; border-radius: 12px; font-size: 13px; font-weight: 700;
  transition: background-color .15s;
}
.ws-decide kbd {
  font-size: 9px; font-family: ui-monospace, monospace; opacity: .55;
  border: 1px solid currentColor; border-radius: 4px; padding: 0 4px;
}
.ws-card-enter-active { transition: all .22s ease; }
.ws-card-leave-active { transition: all .15s ease; }
.ws-card-enter-from { opacity: 0; transform: translateY(10px) scale(.99); }
.ws-card-leave-to { opacity: 0; transform: translateY(-8px) scale(.995); }
.ws-slide-enter-active, .ws-slide-leave-active { transition: all .18s ease; }
.ws-slide-enter-from, .ws-slide-leave-to { opacity: 0; transform: translateY(-4px); }
@media (pointer: coarse) {
  .ws-contact { min-width: 44px; min-height: 44px; }
}

/* ── the game layer ── */
.ws-pop {
  position: absolute; top: -4px; inset-inline-start: 26px; z-index: 20;
  font-size: 12px; font-weight: 800; pointer-events: none;
  animation: ws-pop-fly .95s cubic-bezier(.2, .7, .3, 1) forwards;
}
.ws-pop-good { color: rgb(5 150 105); }
.ws-pop-bad  { color: rgb(190 18 60); }
.ws-pop-mid  { color: rgb(217 119 6); }
@keyframes ws-pop-fly {
  0%   { opacity: 0; transform: translateY(4px) scale(.7); }
  20%  { opacity: 1; transform: translateY(-4px) scale(1.15); }
  100% { opacity: 0; transform: translateY(-26px) scale(1); }
}
.ws-ring-hit { animation: ws-hit-glow 1.8s ease; }
@keyframes ws-hit-glow {
  0%, 100% { box-shadow: 0 1px 2px rgb(0 0 0 / .05); }
  25% { box-shadow: 0 0 0 4px rgb(16 185 129 / .25), 0 8px 24px -8px rgb(16 185 129 / .5); }
}
.ws-burst { position: absolute; top: 22px; inset-inline-start: 24px; z-index: 20; pointer-events: none; }
.ws-burst i {
  position: absolute; width: 7px; height: 7px; border-radius: 2px;
  animation: ws-burst-fly 1.4s cubic-bezier(.15, .6, .3, 1) forwards;
}
@keyframes ws-burst-fly {
  0%   { opacity: 1; transform: translate(0, 0) rotate(0deg) scale(1); }
  100% { opacity: 0; transform: translate(var(--dx), var(--dy)) rotate(300deg) scale(.4); }
}
@media (prefers-reduced-motion: reduce) {
  .ws-pop, .ws-burst i { animation: none; display: none; }
  .ws-ring-hit { animation: none; }
}
</style>
