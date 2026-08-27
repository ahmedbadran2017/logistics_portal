<template>
  <div class="p-4 sm:p-5 max-w-[1500px] mx-auto">
    <!-- top strip: the day as a scoreboard + the serve button -->
    <div class="flex items-center gap-3 flex-wrap mb-4">
      <h1 class="text-[18px] font-bold text-stone-900 tracking-tight me-1">{{ t('ws.title') }}</h1>

      <!-- target ring: the day, as one glance -->
      <div v-if="board?.myTarget" class="flex items-center gap-2.5 bg-white rounded-2xl ring-1 ring-stone-200/70 ps-2 pe-4 py-1.5 shadow-sm">
        <svg width="44" height="44" viewBox="0 0 44 44" class="-rotate-90">
          <circle cx="22" cy="22" r="18" fill="none" stroke="rgb(231 229 228)" stroke-width="5" />
          <circle cx="22" cy="22" r="18" fill="none" stroke-linecap="round" stroke-width="5"
                  :stroke="dayPct >= 100 ? 'rgb(16 185 129)' : 'var(--accent-500)'"
                  :stroke-dasharray="113"
                  :stroke-dashoffset="113 - Math.min(113, (dayPct / 100) * 113)"
                  style="transition: stroke-dashoffset .6s ease" />
        </svg>
        <div class="leading-tight">
          <div class="text-[17px] font-extrabold tabular-nums text-stone-900">
            {{ myTotal }}<span class="text-[11px] font-semibold text-stone-400">/{{ board.myTarget }}</span>
          </div>
          <div class="text-[9.5px] font-semibold uppercase tracking-wide" :class="dayPct >= 100 ? 'text-emerald-600' : 'text-stone-400'">
            {{ dayPct >= 100 ? t('ws.targetHit') : t('ws.today') }}
          </div>
        </div>
      </div>

      <!-- confirmed today -->
      <div class="flex items-center gap-2 bg-white rounded-2xl ring-1 ring-stone-200/70 px-3.5 py-1.5 shadow-sm">
        <span class="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center"><Icon name="check-circle" :size="15" /></span>
        <div class="leading-tight">
          <div class="text-[17px] font-extrabold tabular-nums text-emerald-600">{{ board?.mine?.confirm ?? 0 }}</div>
          <div class="text-[9.5px] font-semibold uppercase tracking-wide text-stone-400">{{ t('ws.confirmed') }}</div>
        </div>
      </div>

      <!-- SLA pulse: my queue against the first-call clock -->
      <div class="flex items-center gap-2 rounded-2xl ring-1 px-3.5 py-1.5 shadow-sm"
           :class="slaLate ? 'bg-rose-50 ring-rose-200' : 'bg-white ring-stone-200/70'">
        <span class="w-7 h-7 rounded-lg flex items-center justify-center"
              :class="slaLate ? 'bg-rose-100 text-rose-600' : 'bg-emerald-50 text-emerald-600'">
          <Icon name="shield-alert" :size="15" />
        </span>
        <div class="leading-tight">
          <div class="text-[17px] font-extrabold tabular-nums" :class="slaLate ? 'text-rose-600' : 'text-emerald-600'">
            {{ slaLate || '✓' }}
          </div>
          <div class="text-[9.5px] font-semibold uppercase tracking-wide" :class="slaLate ? 'text-rose-500' : 'text-stone-400'">
            SLA {{ board?.slaHours || 6 }}h
          </div>
        </div>
      </div>

      <!-- due call-backs -->
      <div v-if="dueCount" class="flex items-center gap-2 bg-amber-50 rounded-2xl ring-1 ring-amber-200 px-3.5 py-1.5 shadow-sm">
        <span class="w-7 h-7 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center"><Icon name="clock" :size="15" /></span>
        <div class="leading-tight">
          <div class="text-[17px] font-extrabold tabular-nums text-amber-600">{{ dueCount }}</div>
          <div class="text-[9.5px] font-semibold uppercase tracking-wide text-amber-500">{{ t('ws.dueShort') }}</div>
        </div>
      </div>

      <button class="ms-auto inline-flex items-center gap-2 h-12 px-6 rounded-2xl text-[14.5px] font-bold text-white shadow-md transition-all hover:shadow-lg disabled:opacity-50"
              :style="{ background: 'var(--accent-600)' }" :disabled="serving" @click="serveNext(true)">
        <Icon name="sparkles" :size="16" />{{ serving ? t('ws.serving') : t('ws.next') }}
        <kbd class="text-[10px] font-mono bg-white/20 rounded px-1.5 py-0.5">N</kbd>
      </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[300px_minmax(0,1fr)_300px] gap-4 items-start">
      <!-- LEFT: the queue, dense like the desk list they live in -->
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden lg:sticky lg:top-3">
        <div class="px-3 py-2 border-b border-stone-100 flex items-center gap-2">
          <span class="text-[11.5px] font-semibold text-stone-700">{{ t('ws.queue') }}</span>
          <span class="text-[10.5px] text-stone-400 tabular-nums">{{ board?.counts?.pending ?? '–' }}</span>
          <button class="ms-auto text-stone-400 hover:text-stone-700" :title="t('common.refresh')" @click="loadBoard">
            <Icon name="refresh-cw" :size="12" />
          </button>
        </div>
        <div v-if="boardLoading" class="p-3 space-y-1.5">
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
              </span>
              <span class="block text-[10px] text-stone-400 font-mono truncate">{{ r.order }} · {{ r.ageH }}h<template v-if="r.attempts"> · ×{{ r.attempts }}</template></span>
            </span>
            <span class="text-[11px] font-semibold tabular-nums text-stone-600 flex-shrink-0">{{ Math.round(r.total) }}</span>
          </button>
          <div v-if="!queueRows.length" class="text-center py-8">
            <div class="text-[12px] text-emerald-600">{{ t('cf.empty') }}</div>
            <!-- honest empty: work IS scheduled, just not due yet -->
            <div v-if="nextDueAt" class="text-[11px] text-amber-600 font-semibold mt-1">
              {{ t('ws.nextDueAt').replace('{t}', nextDueAt) }}
            </div>
          </div>
        </div>
      </div>

      <!-- CENTER: the active order card — every decision tool in one place -->
      <div>
        <div v-if="!active && !cardLoading" class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-12 text-center">
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
                <span v-if="activeRow?.attempts" class="text-amber-600">×{{ activeRow.attempts }} {{ t('ws.attempts') }}</span>
              </div>
            </div>
            <div class="flex items-center gap-1.5">
              <a :href="'tel:' + active.phone" class="ws-contact bg-sky-50 text-sky-700 ring-sky-200" :title="t('ws.call')"><Icon name="phone" :size="16" /></a>
              <a :href="waUrl" target="_blank" class="ws-contact bg-emerald-50 text-emerald-700 ring-emerald-200" title="WhatsApp"><Icon name="message-circle" :size="16" /></a>
              <button class="ws-contact bg-amber-50 text-amber-700 ring-amber-200" :title="t('cf.editContact')" @click="panel = panel === 'contact' ? '' : 'contact'"><Icon name="edit" :size="15" /></button>
            </div>
          </div>

          <!-- items -->
          <div class="rounded-xl ring-1 ring-stone-100 divide-y divide-stone-50">
            <div v-for="it in active.items" :key="it.sku" class="px-3 py-2 flex items-center gap-3">
              <img v-if="it.image" :src="it.image" alt="" class="w-10 h-10 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50" @error="hideImg" />
              <span v-else class="w-10 h-10 rounded-lg bg-stone-100 ring-1 ring-stone-200 flex items-center justify-center text-stone-400"><Icon name="package" :size="15" /></span>
              <div class="min-w-0 flex-1">
                <div class="text-[12.5px] text-stone-800 truncate">{{ it.name }}</div>
                <div class="text-[10.5px] text-stone-400 font-mono">{{ it.sku }}</div>
              </div>
              <span class="text-[12.5px] font-bold tabular-nums text-stone-700">{{ Math.round(it.qty) }}×</span>
              <span class="text-[12px] tabular-nums text-stone-500 w-[70px] text-end">{{ Math.round((it.price || 0) * it.qty) }} MAD</span>
            </div>
            <div class="px-3 py-2 flex items-center justify-between bg-stone-50/60">
              <button class="text-[11.5px] font-semibold text-[var(--accent-700)] hover:underline" @click="panel = panel === 'amend' ? '' : 'amend'">
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
                <div v-for="it in amendItems" :key="it.item_code" class="flex items-center gap-2">
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
                <span v-if="board?.discountCapPct !== undefined" class="text-[10.5px] text-stone-400">{{ t('ws.cap').replace('{p}', String(caps.pct)).replace('{a}', String(caps.amt)) }}</span>
                <button class="ms-auto h-8 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50"
                        :disabled="busy || !amendDirty" @click="applyAmend">{{ busy ? '…' : t('ws.applyAmend') }}</button>
              </div>
              <div class="text-[10.5px] text-stone-400">{{ t('ws.amendNote') }}</div>
            </div>
          </Transition>

          <!-- contact fix -->
          <Transition name="ws-slide">
            <div v-if="panel === 'contact'" class="rounded-xl bg-amber-50/60 ring-1 ring-amber-200/70 p-3 flex items-center gap-2 flex-wrap">
              <input v-model="editPhone" :placeholder="t('cf.phonePh')" inputmode="tel"
                     class="h-9 w-[150px] ps-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] font-mono focus:outline-none" />
              <input v-model="editCity" :placeholder="t('cf.cityPh')"
                     class="h-9 w-[130px] ps-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] focus:outline-none" />
              <input v-model="editAddress" :placeholder="t('cf.addressPh')"
                     class="h-9 flex-1 min-w-[150px] ps-3 rounded-lg bg-white ring-1 ring-amber-200 text-[12.5px] focus:outline-none" dir="auto" />
              <button class="h-9 px-3.5 rounded-lg text-[12px] font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50"
                      :disabled="busy" @click="saveContact">{{ t('cf.saveContact') }}</button>
            </div>
          </Transition>

          <!-- reason (cancel) -->
          <Transition name="ws-slide">
            <div v-if="panel === 'cancel'" class="rounded-xl bg-rose-50/60 ring-1 ring-rose-200/70 p-3 space-y-2">
              <div class="flex flex-wrap gap-1.5">
                <button v-for="rs in reasons" :key="rs"
                        class="h-7 px-2.5 rounded-full text-[11.5px] font-medium ring-1 transition-all"
                        :class="cancelReason === rs ? 'text-white bg-rose-600 ring-rose-600' : 'text-rose-700 bg-white ring-rose-200 hover:bg-rose-100'"
                        @click="cancelReason = rs">{{ rs }}</button>
              </div>
              <button class="h-9 px-4 rounded-lg text-[12.5px] font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50"
                      :disabled="!cancelReason || busy" @click="decide('cancel', cancelReason)">{{ t('cf.cancelConfirm') }}</button>
            </div>
          </Transition>

          <!-- Blocked customer: the warning IS the interface -->
          <div v-if="isBlocked" class="rounded-xl bg-rose-600 text-white px-4 py-2.5 flex items-center gap-2.5">
            <Icon name="shield-alert" :size="16" />
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] font-bold">{{ t('ws.blockedTitle') }}</div>
              <div class="text-[11px] opacity-90 truncate">{{ cust?.flag?.note || t('ws.blockedHint') }} · {{ cust?.flag?.by?.split('@')[0] }} · {{ cust?.flag?.at }}</div>
            </div>
          </div>

          <!-- THE decision row -->
          <div class="flex flex-wrap gap-2">
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
          </div>
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
                    <span class="text-stone-400 tabular-nums ms-1.5">{{ a.by }} · {{ a.at.slice(5) }}</span>
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
              {{ cust.flag.by.split('@')[0] }} · {{ cust.flag.at }}<template v-if="cust.flag.note"> · {{ cust.flag.note }}</template>
            </div>
          </template>
          <div v-else class="text-[11.5px] text-stone-400">—</div>
        </div>

        <div v-if="thread.length || threadLoading" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-3.5">
          <div class="text-[11.5px] font-semibold text-stone-700 mb-2 flex items-center gap-1.5">
            <Icon name="message-circle" :size="12" class="text-emerald-600" />{{ t('cs.thread') }}
          </div>
          <div v-if="threadLoading" class="h-20 rounded bg-stone-100 animate-pulse" />
          <div v-else class="max-h-[260px] overflow-y-auto space-y-1.5">
            <div v-for="(m, i) in thread" :key="i" class="flex" :class="m.in ? 'justify-start' : 'justify-end'">
              <div class="max-w-[85%] rounded-lg px-2.5 py-1.5 text-[11.5px]"
                   :class="m.in ? 'bg-stone-50 ring-1 ring-stone-200 text-stone-800' : 'bg-emerald-50 ring-1 ring-emerald-200 text-emerald-900'" dir="auto">
                <template v-if="m.text">{{ m.text }}</template>
                <span v-else class="text-stone-400">📷</span>
                <div class="text-[9px] text-stone-400 tabular-nums mt-0.5">{{ m.at.slice(5) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import Icon from "@/components/ui/Icon.vue";
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
const panel = ref("");
const reasons = ref([]);
const cancelReason = ref("");
const cust = ref(null);
const custLoading = ref(false);
const thread = ref([]);
const threadLoading = ref(false);
const amendItems = ref([]);
const discAmt = ref(null);
const discPct = ref(null);
const editPhone = ref("");
const editCity = ref("");
const editAddress = ref("");
const caps = ref({ pct: 15, amt: 50 });

// SLA against the first-call clock. Queue-level: how many of MY pending rows
// already blew it. Card-level: this order's countdown, flipping to "late by".
const slaLate = computed(() => {
  const h = board.value?.slaHours || 6;
  return queueRows.value.filter((r) => !r.attempts && r.ageH >= h).length;
});
const slaChip = computed(() => {
  const row = activeRow.value;
  const h = board.value?.slaHours || 6;
  if (!row || row.attempts) return null;   // the clock is about the FIRST touch
  const leftMin = h * 60 - (row.ageH || 0) * 60;
  if (leftMin <= 0) {
    const over = Math.round(((row.ageH || 0) - h) * 10) / 10;
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
const dayPct = computed(() => {
  const tgt = board.value?.myTarget || 0;
  return tgt ? Math.round((myTotal.value * 100) / tgt) : 0;
});

const myTotal = computed(() =>
  Object.values(board.value?.mine || {}).reduce((a, b) => a + (b || 0), 0));
// The queue pane mirrors the SERVE PLAN (due call-backs first, then fresh) —
// not just the pending slice; the agent sees exactly what N will hand out.
const plan = ref(null);
const queueRows = computed(() => plan.value?.rows || []);
const nextDueAt = computed(() => plan.value?.nextDueAt || "");
const dueCount = computed(() => plan.value?.dueCount || 0);
const KIND_CLS = {
  dna: "text-amber-700 bg-amber-100",
  followup: "text-sky-700 bg-sky-100",
  onhold: "text-stone-600 bg-stone-200",
};
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
    activity.value = [{ by: "me", text: noteText.value.trim(), at: new Date().toISOString().slice(0, 16).replace("T", " ") }, ...activity.value];
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
    if (b?.reasons?.length) reasons.value = b.reasons;
  } catch (e) { /* the queue pane is a helper; serve-next still works */ }
  boardLoading.value = false;
}

async function loadSettings() {
  try {
    const s = await api("confirmation.cf_settings");
    caps.value = { pct: s.discountCapPct ?? 15, amt: s.discountCapAmt ?? 50 };
  } catch (e) { /* caps keep their defaults */ }
}

async function openOrder(name) {
  panel.value = "";
  cancelReason.value = "";
  confirmArmed.value = false;
  noteText.value = "";
  showActivity.value = false;
  activity.value = [];
  cardSeconds.value = 0;
  clearInterval(cardTick);
  cardTick = setInterval(() => { cardSeconds.value += 1; }, 1000);
  cardLoading.value = true;
  try {
    active.value = await api("orders.detail", { name });
    activeRow.value = queueRows.value.find((r) => r.order === name) || null;
    amendItems.value = (active.value.items || []).map((i) => ({
      item_code: i.sku, name: i.name, qty: Math.round(i.qty), _orig: Math.round(i.qty),
    }));
    discAmt.value = null; discPct.value = null;
    editPhone.value = active.value.phone || "";
    editCity.value = active.value.city || "";
    editAddress.value = active.value.address_line || "";
    loadContext();
  } catch (e) {
    warn(t("cf.loadFail"), String(e.message || e));
    active.value = null;
  } finally {
    cardLoading.value = false;
  }
}

async function loadContext() {
  const phone = active.value?.phone;
  cust.value = null; thread.value = [];
  if (!phone) return;
  custLoading.value = true;
  threadLoading.value = true;
  api("customers.card", { phone }).then((c) => { cust.value = c; })
    .catch(() => {}).finally(() => { custLoading.value = false; });
  api("tickets.wa_thread", { phone, limit: 20 }).then((r) => { thread.value = r?.messages || []; })
    .catch(() => { thread.value = []; }).finally(() => { threadLoading.value = false; });
}

async function serveNext(skipCurrent = false) {
  serving.value = true;
  try {
    // Walking away UNDECIDED marks the order skipped for 10 minutes —
    // otherwise it comes straight back as the top priority. After a decision
    // the order left the queue on its own, so no marker.
    const skip = skipCurrent && active.value ? active.value.name : undefined;
    const r = await apiPost("confirmation.next_order", skip ? { skip } : {});
    if (r.order) await openOrder(r.order);
    else {
      active.value = null;
      clearInterval(cardTick);
      success(t("ws.allDone"));
    }
  } catch (e) {
    warn(t("cf.loadFail"), String(e.message || e));
  } finally {
    serving.value = false;
  }
}

async function decide(action, note) {
  if (!active.value) return;
  busy.value = true;
  try {
    const res = await apiPost("confirmation.act", { order: active.value.name, action, note });
    success(t(`cf.done_${action}`), active.value.name + (res.attempts ? ` · ×${res.attempts}` : ""));
    if (board.value?.mine && action in board.value.mine) board.value.mine[action]++;
    if (plan.value?.rows) plan.value.rows = plan.value.rows.filter((r) => r.order !== active.value.name);
    panel.value = ""; cancelReason.value = "";
    await serveNext(false);
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
      phone: editPhone.value.trim() || undefined,
      city: editCity.value.trim() || undefined,
      address_line: editAddress.value.trim() || undefined,
    });
    active.value.phone = editPhone.value.trim() || active.value.phone;
    active.value.city = editCity.value.trim() || active.value.city;
    panel.value = "";
    success(t("cf.contactSaved"), active.value.name);
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
  if (tag === "input" || tag === "textarea" || e.metaKey || e.ctrlKey) return;
  const k = e.key.toLowerCase();
  if (k === "n") { e.preventDefault(); serveNext(true); }
  else if (!active.value || busy.value) return;
  else if (k === "1") onConfirm();
  else if (k === "2") decide("dna");
  else if (k === "3") decide("followup");
  else if (k === "4") panel.value = panel.value === "cancel" ? "" : "cancel";
  else if (k === "d") panel.value = panel.value === "amend" ? "" : "amend";
  else if (k === "f") panel.value = panel.value === "contact" ? "" : "contact";
  else if (k === "m") panel.value = panel.value === "note" ? "" : "note";
}

onMounted(() => {
  loadBoard();
  loadSettings();
  window.addEventListener("keydown", onKey);
});
onUnmounted(() => {
  clearInterval(cardTick);
  window.removeEventListener("keydown", onKey);
  if (active.value) apiPost("confirmation.release_order", { order: active.value.name }).catch(() => {});
});
</script>

<style scoped>
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
</style>
