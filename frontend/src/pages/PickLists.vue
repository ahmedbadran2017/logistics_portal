<template>
  <!-- ══════════════ AUTOPILOT FULL PAGE ══════════════ -->
  <div v-if="autopilot" class="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
    <button class="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap" @click="autopilot = false">
      <Icon name="chevron-left" :size="15" />Pick lists
    </button>

    <!-- hero -->
    <div class="rounded-2xl ring-1 ring-[var(--accent-300)]/60 bg-gradient-to-br from-[var(--accent-50)]/60 to-white p-5 mb-4">
      <div class="flex items-start justify-between gap-3 flex-wrap">
        <div class="flex items-center gap-3">
          <div class="relative w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--accent-500)] to-[var(--accent-700)] text-white flex items-center justify-center">
            <span v-html="zapIcon(24)" />
            <span class="absolute -top-0.5 -end-0.5 w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-white animate-pulse" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-[20px] font-semibold text-stone-900">Pick Autopilot</h1>
              <span class="inline-flex items-center gap-1 px-2 h-[20px] rounded-md text-[11px] font-medium text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500" />Active</span>
            </div>
            <div class="text-[12.5px] text-stone-500 mt-0.5">AI agent · generates, assigns &amp; monitors picks</div>
          </div>
        </div>
        <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] transition-colors" @click="success('Autopilot run · 4 pick lists created & assigned')">
          <span v-html="zapIcon(15)" />Run now
        </button>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        <div v-for="s in apStats" :key="s.label" class="bg-white rounded-xl ring-1 ring-stone-200/60 p-3">
          <div class="flex items-center gap-1.5 text-stone-500"><span v-html="s.icon" /><span v-if="s.live" class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /><span class="text-[11px] font-medium">{{ s.label }}</span></div>
          <div class="text-[20px] font-semibold tabular-nums leading-none mt-1.5" :class="s.tone === 'emerald' ? 'text-emerald-600' : 'text-stone-900'">{{ s.value }}</div>
          <div v-if="s.sub" class="text-[10px] text-stone-400 mt-1 truncate">{{ s.sub }}</div>
        </div>
      </div>
    </div>

    <!-- tabs -->
    <div class="flex items-center gap-1 border-b border-stone-200/70 mb-4">
      <button v-for="tb in apTabs" :key="tb[0]" class="px-3 h-9 text-[13px] font-medium border-b-2 -mb-px transition-colors" :class="apTab === tb[0] ? 'border-[var(--accent-600)] text-stone-900' : 'border-transparent text-stone-500 hover:text-stone-800'" @click="apTab = tb[0]">{{ tb[1] }}</button>
    </div>

    <!-- overview -->
    <div v-if="apTab === 'overview'" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">Suggestions</div>
        <div class="p-3 space-y-2">
          <div v-for="(r, i) in AUTOPILOT.recos" :key="i" class="flex items-center gap-2.5 rounded-xl bg-white ring-1 ring-[var(--accent-200)]/50 px-3 py-2">
            <span v-html="zapIcon(14)" class="text-[var(--accent-600)] flex-shrink-0" />
            <span class="text-[12px] text-stone-700 flex-1">{{ r.txt }}</span>
            <button class="inline-flex items-center h-7 px-2.5 rounded-md text-[11.5px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]" @click="success('Suggestion applied')">Apply</button>
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center justify-between">
          <span class="text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">Agent activity</span>
          <span class="text-[11px] text-stone-400">Watching {{ AUTOPILOT.watching }} active picks</span>
        </div>
        <div class="p-3 space-y-1">
          <div v-for="(e, i) in AUTOPILOT.feed" :key="i" class="flex items-center gap-2.5 px-1 py-1">
            <span class="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0" :class="feedStyle(e.kind).cls" v-html="feedStyle(e.kind).icon" />
            <span class="text-[12px] text-stone-700 flex-1">{{ e.act }}</span>
            <span class="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{{ e.t }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- rules -->
    <div v-else-if="apTab === 'rules'" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden max-w-[560px]">
      <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">Autopilot rules</div>
      <div class="p-4 space-y-4">
        <div class="flex items-center justify-between gap-3"><span class="text-[13px] text-stone-700">Default strategy</span>
          <div class="inline-flex bg-stone-100/80 rounded-lg p-0.5">
            <button v-for="o in [['zone','By zone'],['sku','By SKU'],['balanced','Balanced']]" :key="o[0]" class="px-2.5 h-7 text-[12px] font-medium rounded-md" :class="ruleStrategy === o[0] ? 'bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]' : 'text-stone-500'" @click="ruleStrategy = o[0]">{{ o[1] }}</button>
          </div>
        </div>
        <div class="flex items-center justify-between gap-3"><span class="text-[13px] text-stone-700">Run schedule</span>
          <div class="inline-flex bg-stone-100/80 rounded-lg p-0.5">
            <button v-for="o in [['15m','15m'],['30m','30m'],['60m','60m']]" :key="o[0]" class="px-2.5 h-7 text-[12px] font-medium rounded-md" :class="ruleSchedule === o[0] ? 'bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]' : 'text-stone-500'" @click="ruleSchedule = o[0]">{{ o[1] }}</button>
          </div>
        </div>
        <div class="flex items-center justify-between gap-3"><span class="text-[13px] text-stone-700">Min orders per batch</span>
          <div class="inline-flex items-center gap-2"><button class="w-7 h-7 rounded-lg ring-1 ring-stone-200 text-stone-600 hover:bg-stone-50" @click="batchThresh = Math.max(1, batchThresh - 1)">−</button><span class="w-6 text-center text-[13px] font-semibold tabular-nums">{{ batchThresh }}</span><button class="w-7 h-7 rounded-lg ring-1 ring-stone-200 text-stone-600 hover:bg-stone-50" @click="batchThresh++">+</button></div>
        </div>
        <div class="flex items-center justify-between gap-3"><span class="text-[13px] text-stone-700">Idle threshold (min)</span>
          <div class="inline-flex items-center gap-2"><button class="w-7 h-7 rounded-lg ring-1 ring-stone-200 text-stone-600 hover:bg-stone-50" @click="idleMin = Math.max(1, idleMin - 1)">−</button><span class="w-6 text-center text-[13px] font-semibold tabular-nums">{{ idleMin }}</span><button class="w-7 h-7 rounded-lg ring-1 ring-stone-200 text-stone-600 hover:bg-stone-50" @click="idleMin++">+</button></div>
        </div>
        <div v-for="tg in toggles" :key="tg.key" class="flex items-center justify-between gap-3">
          <span class="text-[13px] text-stone-700">{{ tg.label }}</span>
          <button class="w-9 h-5 rounded-full p-0.5 transition-colors" :class="tg.on ? 'bg-[var(--accent-600)]' : 'bg-stone-200'" @click="tg.on = !tg.on"><span class="block w-4 h-4 rounded-full bg-white shadow transition-transform" :class="tg.on ? 'translate-x-4' : ''" /></button>
        </div>
        <div class="flex justify-end pt-2 border-t border-stone-100">
          <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]" @click="success('Autopilot rules saved · synced to ERPNext scheduler')"><Icon name="check-circle" :size="15" />Save rules</button>
        </div>
      </div>
    </div>

    <!-- history -->
    <div v-else-if="apTab === 'history'" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">All agent decisions today</div>
      <div class="p-3 space-y-1">
        <div v-for="(e, i) in fullLog" :key="i" class="flex items-center gap-2.5 px-1.5 py-1.5 rounded-lg hover:bg-stone-50">
          <span class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" :class="feedStyle(e.kind).cls" v-html="feedStyle(e.kind).icon" />
          <span class="text-[12.5px] text-stone-700 flex-1">{{ e.act }}</span>
          <span class="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{{ e.t }}</span>
        </div>
      </div>
    </div>

    <!-- perf -->
    <div v-else class="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-4">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100"><span class="text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">Efficiency gain</span> <span class="text-[11px] text-stone-400">last 14 runs</span></div>
        <div class="p-4">
          <svg viewBox="0 0 300 120" class="w-full" preserveAspectRatio="none" style="height:120px">
            <polyline :points="sparkPoints" fill="none" stroke="#10b981" stroke-width="2" />
          </svg>
        </div>
      </div>
      <div class="space-y-3">
        <div v-for="s in perfStats" :key="s.label" class="bg-white rounded-xl ring-1 ring-stone-200/60 p-3">
          <div class="flex items-center gap-1.5 text-stone-500"><span v-html="s.icon" /><span class="text-[11px] font-medium">{{ s.label }}</span></div>
          <div class="text-[20px] font-semibold tabular-nums leading-none mt-1.5" :class="s.tone === 'emerald' ? 'text-emerald-600' : 'text-stone-900'">{{ s.value }}</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ══════════════ PICK LIST DETAIL ══════════════ -->
  <div v-else-if="detail" class="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
    <button class="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap" @click="detail = null">
      <Icon name="chevron-left" :size="15" class="flip-rtl" />{{ t("pl.back") }}
    </button>

    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3">
          <span class="w-11 h-11 rounded-xl bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center" v-html="boxIcon(22)" />
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h1 class="font-mono text-[19px] font-bold text-stone-900">{{ detail.no }}</h1>
              <span v-if="detail.order === 'combined'" class="inline-flex items-center px-2 h-[20px] rounded-md text-[11px] font-medium text-violet-700 bg-violet-50 ring-1 ring-violet-200 whitespace-nowrap">{{ t("pl.combined") }}</span>
              <span v-else class="inline-flex items-center px-2 h-[20px] rounded-md text-[11px] font-medium text-stone-600 bg-stone-100 ring-1 ring-stone-200 font-mono">{{ detail.customer || detail.order }}</span>
              <span v-if="detail.errors" class="inline-flex items-center gap-1 px-2 h-[20px] rounded-md text-[11px] font-medium text-rose-700 bg-rose-50 ring-1 ring-rose-200 whitespace-nowrap"><span class="w-1.5 h-1.5 rounded-full bg-rose-500" />Short-pick</span>
              <span v-else class="inline-flex items-center gap-1 px-2 h-[20px] rounded-md text-[11px] font-medium ring-1" :class="statusPill(detail)"><span class="w-1.5 h-1.5 rounded-full" :class="statusPillDot(detail)" />{{ statusPillLabel(detail) }}</span>
            </div>
            <div class="text-[12.5px] text-stone-600 mt-1 flex items-center gap-2">
              <span class="w-5 h-5 rounded-full bg-stone-200 text-stone-600 flex items-center justify-center text-[9px] font-bold">{{ pickerInitials(detail.picker) }}</span>
              {{ pickerName(detail.picker) }} · {{ t("pl.optimized") }}<span v-if="liveDetail" class="text-stone-400"> · {{ liveDetail.created }}</span>
            </div>
            <div class="flex items-center gap-1.5 mt-2 flex-wrap">
              <span class="inline-flex items-center px-2 h-[20px] rounded-md text-[11px] font-medium text-stone-600 bg-stone-100 ring-1 ring-stone-200 whitespace-nowrap">Delivery</span>
              <span class="inline-flex items-center px-2 h-[20px] rounded-md text-[11px] font-medium text-stone-600 bg-stone-100 ring-1 ring-stone-200 whitespace-nowrap">Source: {{ WAREHOUSE }}</span>
              <span class="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200/60 rounded px-1.5 py-0.5"><Icon name="scan-barcode" :size="10" />Scan mode</span>
              <span v-if="detail.order === 'combined'" class="inline-flex items-center gap-1 text-[11px] font-medium text-violet-700 bg-violet-50 ring-1 ring-violet-200/60 rounded px-1.5 py-0.5" v-html="layersIcon(10) + ' Grouped SKUs'" />
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <template v-if="isLiveData">
            <!-- DRAFT: assign · cancel · submit (the action that finishes it on the portal) -->
            <template v-if="liveDetail && liveDetail.status === 'draft'">
              <div class="relative">
                <select :value="liveDetail.picker"
                        class="h-9 ps-3 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[12.5px] text-stone-700 appearance-none cursor-pointer focus:outline-none hover:ring-stone-300"
                        :disabled="assigning" @change="doAssign($event.target.value)">
                  <option value="">{{ t("pl.assignPicker") }}</option>
                  <option v-for="p in sbPickers" :key="p.email" :value="p.email">{{ p.name }} ({{ p.load }})</option>
                </select>
                <Icon name="chevron-down" :size="13" class="absolute top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none" style="inset-inline-end:.6rem" />
              </div>
              <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-rose-600 bg-white ring-1 ring-rose-200 hover:bg-rose-50" @click="confirmCancel = true">
                <Icon name="x" :size="15" />{{ t("pl.cancelPl") }}
              </button>
              <button class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg text-[13px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] shadow-[0_4px_14px_-4px_rgba(196,73,42,0.5)] transition-all hover:-translate-y-px disabled:opacity-50"
                      :disabled="submitting" @click="confirmSubmit = true">
                <Icon name="check-circle" :size="15" />{{ submitting ? t("pl.submitting") : t("pl.submit") }}
              </button>
            </template>
            <!-- SUBMITTED: AWB ready -> print label -->
            <template v-else>
              <a v-if="liveAwbUrl" :href="liveAwbUrl" target="_blank" class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg text-[13px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]"><Icon name="printer" :size="15" />{{ t("pl.printAwb") }}</a>
              <a :href="'/app/pick-list/' + encodeURIComponent(detail.no)" target="_blank" class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50">{{ t("pl.openErp") }} <Icon name="arrow-right" :size="13" class="flip-rtl" /></a>
            </template>
          </template>
          <template v-else>
            <button v-if="detail.pct < 100" class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]"><span v-html="boxIcon(15)" />{{ detail.pct > 0 ? "Continue pick" : "Start pick" }}</button>
            <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"><span v-html="usersIcon(15)" />Reassign</button>
            <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50"><Icon name="printer" :size="15" />Print</button>
          </template>
        </div>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        <div class="bg-stone-50 rounded-xl px-3 py-2.5"><div class="text-[22px] font-semibold tabular-nums leading-none text-stone-900">{{ detailOrders }}</div><div class="text-[11px] text-stone-500 mt-1.5">{{ t("pl.dOrders") }}</div></div>
        <div class="bg-stone-50 rounded-xl px-3 py-2.5"><div class="text-[22px] font-semibold tabular-nums leading-none text-stone-900">{{ lines.length }}</div><div class="text-[11px] text-stone-500 mt-1.5">{{ t("pl.dLines") }}</div></div>
        <div class="bg-stone-50 rounded-xl px-3 py-2.5"><div class="text-[22px] font-semibold tabular-nums leading-none text-stone-900">{{ detailUnits }}</div><div class="text-[11px] text-stone-500 mt-1.5">{{ t("pl.dUnits") }}</div></div>
        <div class="bg-stone-50 rounded-xl px-3 py-2.5"><div class="text-[22px] font-semibold tabular-nums leading-none text-[var(--accent-700)]">{{ estTime }}m</div><div class="text-[11px] text-stone-500 mt-1.5">Est. time</div></div>
      </div>
      <div class="mt-4">
        <div class="flex items-center justify-between text-[11px] mb-1"><span class="text-stone-500 tabular-nums">{{ doneCount }} / {{ lines.length }} {{ t("pl.scanned") }}</span><span class="font-semibold tabular-nums text-emerald-600">{{ Math.round(doneCount / lines.length * 100) }}%</span></div>
        <div class="h-2 rounded-full bg-stone-100 overflow-hidden"><div class="h-full rounded-full" :class="detail.errors ? 'bg-rose-500' : 'bg-emerald-500'" :style="{ width: (doneCount / lines.length * 100) + '%' }" /></div>
      </div>
    </div>

    <!-- lifecycle stepper -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden mb-4">
      <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t("pl.lifecycle") }}</div>
      <div class="p-4">
        <div class="flex items-center">
          <template v-for="(st, i) in lifecycleShown" :key="st.label">
            <div class="flex flex-col items-center gap-1.5 flex-shrink-0" style="width:92px">
              <span class="w-9 h-9 rounded-xl flex items-center justify-center" :class="i <= lifecycleCur ? 'bg-emerald-500 text-white' : 'bg-stone-100 text-stone-400'">
                <Icon v-if="i <= lifecycleCur" name="check-circle" :size="16" />
                <span v-else v-html="st.icon" />
              </span>
              <span class="text-[11px] font-medium text-center leading-tight" :class="i <= lifecycleCur ? 'text-stone-900' : 'text-stone-400'">{{ st.label }}</span>
              <span class="text-[10px] text-stone-400 tabular-nums">{{ i <= lifecycleCur ? lifecycleTimes[i] : "" }}</span>
            </div>
            <div v-if="i < lifecycleShown.length - 1" class="flex-1 h-0.5 -mt-6" :class="i < lifecycleCur ? 'bg-emerald-300' : 'bg-stone-200'" />
          </template>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-4">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 flex items-center justify-between">
          <div>
            <span class="text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ view === "walk" ? t("pl.walk") : view === "sku" ? t("pl.bySku") : t("pl.byOrder") }}</span>
            <span v-if="view === 'walk'" class="text-[11px] text-stone-400"> · {{ t('pl.stopsCount').replace('{s}', walkStops.length).replace('{u}', detailUnits) }}</span>
          </div>
          <div class="inline-flex bg-stone-100/80 rounded-lg p-0.5">
            <button v-for="v in [['walk', t('pl.walk')],['sku', t('pl.bySku')],['order', t('pl.byOrder')]]" :key="v[0]" class="px-2.5 h-7 text-[11.5px] font-medium rounded-md transition-all" :class="view === v[0] ? 'bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]' : 'text-stone-500 hover:text-stone-800'" @click="view = v[0]">{{ v[1] }}</button>
          </div>
        </div>
        <div class="p-4">
          <!-- walk — one stop per (bin, product), whatever the order count -->
          <ol v-if="view === 'walk'" class="relative">
            <li v-for="(s, i) in walkStops" :key="s.key" class="relative flex gap-3.5 pb-3 last:pb-0">
              <span v-if="i !== walkStops.length - 1" class="absolute top-9 w-px" :class="s.picked ? 'bg-emerald-200' : 'bg-stone-200'" style="left:15px" />
              <span class="relative z-10 w-[31px] h-[31px] rounded-lg flex items-center justify-center text-[12px] font-bold flex-shrink-0" :class="s.picked ? 'bg-emerald-500 text-white' : s.partial ? 'bg-amber-500 text-white' : 'bg-white ring-1 ring-stone-300 text-stone-500'">
                <Icon v-if="s.picked" name="check-circle" :size="15" />
                <svg v-else-if="s.partial" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
                <template v-else>{{ i + 1 }}</template>
              </span>
              <div class="min-w-0 flex-1 rounded-xl ring-1 p-3" :class="s.picked ? 'ring-emerald-200 bg-emerald-50/40' : s.partial ? 'ring-amber-200 bg-amber-50/40' : 'ring-stone-200 bg-white'">
                <div class="flex items-center justify-between gap-2">
                  <div class="flex items-center gap-2">
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-stone-900 text-white text-[12px] font-bold font-mono"><Icon name="map-pin" :size="11" />{{ s.bin }}</span>
                    <span v-if="isNewAisleStop(i)" class="text-[10px] font-medium text-[var(--accent-700)] bg-[var(--accent-50)] rounded px-1.5 py-0.5">{{ binZone(s.bin).replace(" - JM", "") }}</span>
                  </div>
                  <span class="text-[15px] font-bold tabular-nums" :class="s.partial ? 'text-amber-600' : 'text-stone-900'">{{ s.pickedQty }}/{{ s.qty }} <span class="text-[12px] font-semibold text-stone-400">{{ t('pl.grab') }}</span></span>
                </div>
                <div class="flex gap-3 mt-2">
                  <img v-if="s.image" :src="s.image" alt="" loading="lazy" @error="onImgError"
                       class="w-14 h-14 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
                  <div class="min-w-0 flex-1">
                    <div class="text-[13.5px] font-medium text-stone-900">{{ s.name }}</div>
                    <div class="flex items-center gap-2 mt-1 flex-wrap">
                      <span class="inline-flex items-center gap-1 text-[12px] font-bold font-mono text-stone-800 bg-stone-100 rounded px-1.5 py-0.5">SKU {{ s.realSku || s.sku }}</span>
                      <span v-if="s.orders.length === 1" class="text-[11.5px] text-stone-500 truncate">{{ s.orders[0].so }} · {{ s.orders[0].customer }}</span>
                      <span v-else class="text-[11.5px] font-semibold text-[var(--accent-700)]">{{ t('pl.splitsTo').replace('{n}', s.orders.length) }}</span>
                    </div>
                    <div v-if="s.realSku && s.sku !== s.realSku" class="font-mono text-[10px] text-stone-400 mt-0.5">⌗ {{ s.sku }}</div>
                  </div>
                </div>
                <div class="flex items-center gap-1.5 mt-1.5 flex-wrap">
                  <span v-if="grpClean(s.grp)" class="text-[10px] font-medium text-stone-500 bg-stone-100 rounded px-1.5 py-0.5">{{ s.grp }}</span>
                  <span v-if="s.uom && s.uom !== 'Nos'" class="text-[10px] font-medium text-stone-500 bg-stone-100 rounded px-1.5 py-0.5">{{ s.uom }}</span>
                  <span v-if="s.serial || s.batch" class="inline-flex items-center gap-1 text-[10px] font-medium text-violet-700 bg-violet-50 ring-1 ring-violet-200/60 rounded px-1.5 py-0.5"><span v-html="tagIcon(9)" />{{ s.serial ? "Serial" : "Batch" }}</span>
                </div>
                <!-- packing map: which orders this grab splits into -->
                <div v-if="s.orders.length > 1" class="mt-2 pt-2 border-t border-stone-100 flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                  <span v-for="o in s.orders" :key="o.so" class="inline-flex items-center gap-1 text-[10.5px] font-mono text-stone-600 bg-stone-50 ring-1 ring-stone-200/70 rounded px-1.5 py-0.5" :title="o.customer">
                    {{ o.so }}<span v-if="o.qty > 1" class="font-bold text-stone-400">×{{ o.qty }}</span>
                  </span>
                </div>
              </div>
            </li>
          </ol>

          <!-- by SKU -->
          <div v-else-if="view === 'sku'" class="space-y-2">
            <div v-for="(l, i) in bySku" :key="i" class="rounded-xl ring-1 ring-stone-200 bg-white p-3">
              <div class="flex items-center justify-between gap-2">
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-stone-900 text-white text-[12px] font-bold font-mono"><Icon name="map-pin" :size="11" />{{ l.bin }}</span>
                <span class="text-[15px] font-bold text-[var(--accent-700)] tabular-nums">{{ l.qtyTot }}× batch-pick</span>
              </div>
              <div class="flex gap-3 mt-2">
                <img v-if="l.image" :src="l.image" alt="" loading="lazy" @error="onImgError"
                     class="w-14 h-14 rounded-lg object-cover ring-1 ring-stone-200 bg-stone-50 flex-shrink-0" />
                <div class="min-w-0 flex-1">
                  <div class="text-[13.5px] font-medium text-stone-900">{{ l.name }}</div>
                  <div class="flex items-center gap-2 mt-1 flex-wrap">
                    <span class="inline-flex items-center gap-1 text-[12px] font-bold font-mono text-stone-800 bg-stone-100 rounded px-1.5 py-0.5">SKU {{ l.realSku || l.sku }}</span>
                    <span class="text-[11.5px] text-stone-500">{{ t('pl.splitsTo').replace('{n}', l.orders.length) }}</span>
                  </div>
                  <div v-if="l.realSku && l.sku !== l.realSku" class="font-mono text-[10px] text-stone-400 mt-0.5">⌗ {{ l.sku }}</div>
                </div>
              </div>
              <div v-if="l.orders.length > 1" class="mt-2 pt-2 border-t border-stone-100 flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                <span v-for="(so, j) in l.orders" :key="j" class="text-[10.5px] font-mono text-stone-600 bg-stone-50 ring-1 ring-stone-200/70 rounded px-1.5 py-0.5">{{ so }}</span>
              </div>
            </div>
          </div>

          <!-- by order -->
          <div v-else class="space-y-3">
            <div v-for="(o, i) in byOrder" :key="i" class="rounded-xl ring-1 ring-stone-200 overflow-hidden">
              <div class="flex items-center gap-2 px-3 py-2 bg-stone-50 border-b border-stone-100">
                <span class="font-mono text-[12px] font-semibold text-stone-900">{{ o.so }}</span>
                <span class="text-[11.5px] text-stone-500 flex-1 truncate">{{ o.customer }}</span>
                <span class="inline-flex items-center px-2 h-[20px] rounded-md text-[11px] font-medium text-stone-600 bg-stone-100 ring-1 ring-stone-200">{{ o.items.length }} lines</span>
              </div>
              <div class="divide-y divide-stone-100">
                <div v-for="(l, j) in o.items" :key="j" class="flex items-center gap-2.5 px-3 py-2">
                  <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stone-900 text-white text-[10.5px] font-bold font-mono flex-shrink-0"><Icon name="map-pin" :size="9" />{{ l.bin }}</span>
                  <span class="text-[12.5px] text-stone-800 flex-1 truncate">{{ l.name }}</span>
                  <span class="text-[12px] font-semibold text-stone-900 tabular-nums">×{{ l.qty }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- orders on this PL (live) / activity (demo) -->
      <div v-if="liveDetail" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden h-fit">
        <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">{{ t("pl.ordersOn") }}</div>
        <div class="divide-y divide-stone-100">
          <div v-for="o in liveDetail.orders" :key="o.so" class="flex items-center gap-2.5 px-4 py-2.5">
            <button class="font-mono text-[12px] font-semibold text-stone-900 hover:text-[var(--accent-700)]" @click="$router.push({ name: 'OrderDetail', params: { name: o.so.replace('#','') } })">{{ o.so }}</button>
            <span class="text-[12px] text-stone-600 flex-1 truncate">{{ o.customer }}</span>
            <span v-if="o.awb" class="font-mono text-[10.5px] text-stone-500 bg-stone-100 ring-1 ring-stone-200/70 rounded px-1.5 py-0.5">{{ o.awb }}</span>
          </div>
          <div v-if="!liveDetail.orders.length" class="text-center text-[12px] text-stone-400 py-8">—</div>
        </div>
      </div>
      <div v-else class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400">Activity</div>
        <div class="p-4 space-y-3">
          <div v-for="(ev, i) in detailActivity" :key="i" class="flex items-start gap-2.5" :class="!ev.on && 'opacity-40'">
            <span class="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5" :class="ev.bad ? 'bg-rose-100 text-rose-600' : ev.on ? 'bg-emerald-100 text-emerald-600' : 'bg-stone-100 text-stone-400'">
              <Icon :name="ev.bad ? 'alert-circle' : 'check-circle'" :size="13" />
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] text-stone-800">{{ ev.act }}</div>
              <div class="text-[11px] text-stone-400">{{ ev.who }} · {{ ev.at }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Submit confirm (creates the DN + Cathedis AWB — irreversible) -->
    <div v-if="confirmSubmit" class="fixed inset-0 z-[160] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-stone-900/30 backdrop-blur-[1px]" @click="confirmSubmit = false" />
      <div class="relative w-full max-w-[420px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] p-5 animate-scale-in">
        <div class="flex items-center gap-2.5 mb-2">
          <span class="w-9 h-9 rounded-xl bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center"><Icon name="check-circle" :size="18" /></span>
          <div class="text-[15px] font-semibold text-stone-900">{{ t("pl.submitTitle") }}</div>
        </div>
        <p class="text-[12.5px] text-stone-500 leading-relaxed mb-4">{{ t("pl.submitBody") }}</p>
        <div class="flex items-center justify-end gap-2">
          <button class="h-9 px-3 rounded-lg text-[13px] font-medium text-stone-600 hover:bg-stone-100" @click="confirmSubmit = false">{{ t("pl.keep") }}</button>
          <button class="inline-flex items-center gap-1.5 h-9 px-4 rounded-lg text-[13px] font-semibold text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]" @click="doSubmit">
            <Icon name="check-circle" :size="15" />{{ t("pl.confirm") }}
          </button>
        </div>
      </div>
    </div>

    <!-- Cancel confirm (deletes a draft — orders return to To Pick) -->
    <div v-if="confirmCancel" class="fixed inset-0 z-[160] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-stone-900/30 backdrop-blur-[1px]" @click="confirmCancel = false" />
      <div class="relative w-full max-w-[420px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] p-5 animate-scale-in">
        <div class="flex items-center gap-2.5 mb-2">
          <span class="w-9 h-9 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center"><Icon name="alert-triangle" :size="18" /></span>
          <div class="text-[15px] font-semibold text-stone-900">{{ t("pl.cancelTitle") }}</div>
        </div>
        <p class="text-[12.5px] text-stone-500 leading-relaxed mb-4">{{ t("pl.cancelBody") }}</p>
        <div class="flex items-center justify-end gap-2">
          <button class="h-9 px-3 rounded-lg text-[13px] font-medium text-stone-600 hover:bg-stone-100" @click="confirmCancel = false">{{ t("pl.keep") }}</button>
          <button class="inline-flex items-center gap-1.5 h-9 px-4 rounded-lg text-[13px] font-semibold text-white bg-rose-600 hover:bg-rose-700" @click="doCancel">
            <Icon name="x" :size="15" />{{ t("pl.confirm") }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- ══════════════ PICK LISTS TABLE ══════════════ -->
  <div v-else class="max-w-[1240px] mx-auto px-6 py-6 animate-fade-in">
    <div class="flex items-start justify-between gap-3 flex-wrap mb-4">
      <div>
        <h1 class="text-[19px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t("pl.title") }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ isLiveData ? t("pl.subtitle").replace("{n}", total).replace("{d}", daysF) : rows.length + " pick lists today" }} · {{ WAREHOUSE }}</p>
      </div>
      <div class="flex items-center gap-2">
        <div v-if="isLiveData" class="flex items-center rounded-lg ring-1 ring-stone-200 bg-white p-0.5">
          <button v-for="d in [7, 14, 30]" :key="d"
                  class="px-3 h-8 text-[12px] font-medium rounded-md transition-colors"
                  :class="daysF === d ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-800'"
                  @click="daysF = d; load()">{{ d }}d</button>
        </div>
        <button v-if="isLiveData" class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors" @click="$router.push({ name: 'Pipeline' })">
          <span v-html="boxIcon(15)" />{{ t("pl.fromBoard") }}
        </button>
        <button v-if="isLiveData" class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] transition-colors" @click="sbModal && sbModal.open()">
          <span v-html="zapIcon(15)" />{{ t("pl.sbBtn") }}
        </button>
        <button v-else class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] transition-colors" @click="create = true">
          <span v-html="zapIcon(15)" />Smart auto pick list
        </button>
      </div>
    </div>

    <!-- autopilot card (LIVE — real engine, real log) -->
    <div v-if="isLiveData" class="rounded-2xl ring-1 mb-4 overflow-hidden"
         :class="ap.enabled ? 'ring-[var(--accent-300)]/60 bg-gradient-to-br from-[var(--accent-50)]/60 to-white' : 'ring-stone-200 bg-white'">
      <div class="p-4">
        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div class="flex items-center gap-3">
            <div class="relative w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
                 :class="ap.enabled ? 'bg-gradient-to-br from-[var(--accent-500)] to-[var(--accent-700)] text-white' : 'bg-stone-100 text-stone-400'">
              <span v-html="zapIcon(22)" />
              <span v-if="ap.enabled" class="absolute -top-0.5 -end-0.5 w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-white animate-pulse" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-[16px] font-semibold text-stone-900">{{ t("pl.apTitle") }}</h2>
                <span class="inline-flex items-center gap-1 px-2 h-[20px] rounded-md text-[11px] font-medium ring-1"
                      :class="ap.enabled ? 'text-emerald-700 bg-emerald-50 ring-emerald-200' : 'text-stone-600 bg-stone-100 ring-stone-200'">
                  <span class="w-1.5 h-1.5 rounded-full" :class="ap.enabled ? 'bg-emerald-500' : 'bg-stone-400'" />
                  {{ ap.enabled ? t("pl.apActive") : t("pl.apPaused") }}
                </span>
              </div>
              <div class="text-[12px] text-stone-500 mt-0.5">{{ t("pl.apSub") }}</div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 disabled:opacity-40"
                    :disabled="apBusy || !ap.enabled" @click="apRunNow">
              <span v-html="zapIcon(15)" />{{ apBusy ? t("pl.apRunning") : t("pl.apRun") }}
            </button>
            <button class="inline-flex items-center h-9 px-3 rounded-lg text-[13px] font-medium transition-colors"
                    :class="ap.enabled ? 'text-stone-600 hover:bg-stone-100 ring-1 ring-stone-200 bg-white' : 'text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]'"
                    :disabled="apBusy" @click="apToggle">
              {{ ap.enabled ? t("pl.apPause") : t("pl.apEnable") }}
            </button>
          </div>
        </div>
        <div v-if="ap.runs.length" class="mt-4">
          <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">{{ t("pl.apLog") }}</div>
          <div class="space-y-1">
            <div v-for="(r, i) in ap.runs.slice(0, 5)" :key="i" class="flex items-center gap-2.5 px-1 py-1 text-[12px]">
              <span class="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0"
                    :class="r.note ? 'bg-stone-100 text-stone-400' : 'bg-emerald-50 text-emerald-600'">
                <span v-html="zapIcon(12)" />
              </span>
              <span class="text-stone-700 flex-1 truncate">
                <template v-if="r.trigger === 'toggle'">{{ r.note === 'enabled' ? t("pl.apToggleOn") : t("pl.apToggleOff") }} · {{ (r.by || '').split('@')[0] }}</template>
                <template v-else-if="r.note">{{ t("pl.apSkip") }}</template>
                <template v-else>{{ t("pl.apCreatedN").replace("{c}", r.created).replace("{o}", r.orders) }}<span v-if="r.failed" class="text-rose-600"> · {{ r.failed }}✗</span></template>
                <span class="text-stone-400"> · {{ r.trigger === 'manual' ? t("pl.apManual") : r.trigger === 'auto' ? t("pl.apAuto") : '' }}</span>
              </span>
              <span class="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{{ (r.at || '').slice(5, 16) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- autopilot card (concept preview — demo mode only) -->
    <div v-if="!isLiveData" class="rounded-2xl ring-1 mb-4 overflow-hidden" :class="apOn ? 'ring-[var(--accent-300)]/60 bg-gradient-to-br from-[var(--accent-50)]/60 to-white' : 'ring-stone-200 bg-white'">
      <div class="p-4">
        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div class="flex items-center gap-3">
            <div class="relative w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0" :class="apOn ? 'bg-gradient-to-br from-[var(--accent-500)] to-[var(--accent-700)] text-white' : 'bg-stone-100 text-stone-400'">
              <span v-html="zapIcon(22)" />
              <span v-if="apOn" class="absolute -top-0.5 -end-0.5 w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-white animate-pulse" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-[16px] font-semibold text-stone-900">Pick Autopilot</h2>
                <span class="inline-flex items-center gap-1 px-2 h-[20px] rounded-md text-[11px] font-medium ring-1" :class="apOn ? 'text-emerald-700 bg-emerald-50 ring-emerald-200' : 'text-stone-600 bg-stone-100 ring-stone-200'"><span class="w-1.5 h-1.5 rounded-full" :class="apOn ? 'bg-emerald-500' : 'bg-stone-400'" />{{ apOn ? "Active" : "Paused" }}</span>
              </div>
              <div class="text-[12px] text-stone-500 mt-0.5">AI agent · generates, assigns &amp; monitors picks</div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 disabled:opacity-40" :disabled="thinking || !apOn" @click="runNow"><span v-html="zapIcon(15)" />{{ thinking ? "Analyzing pending orders…" : "Run now" }}</button>
            <button class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50" @click="autopilot = true">Open Autopilot<Icon name="arrow-right" :size="15" /></button>
            <button class="inline-flex items-center h-9 px-3 rounded-lg text-[13px] font-medium transition-colors" :class="apOn ? 'text-stone-600 hover:bg-stone-100' : 'text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]'" @click="apOn = !apOn">{{ apOn ? "Pause Autopilot" : "Enable Autopilot" }}</button>
          </div>
        </div>

        <template v-if="apOn">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <div v-for="s in apStats" :key="s.label" class="bg-white rounded-xl ring-1 ring-stone-200/60 p-3">
              <div class="flex items-center gap-1.5 text-stone-500"><span v-html="s.icon" /><span v-if="s.live" class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /><span class="text-[11px] font-medium">{{ s.label }}</span></div>
              <div class="text-[20px] font-semibold tabular-nums leading-none mt-1.5" :class="s.tone === 'emerald' ? 'text-emerald-600' : 'text-stone-900'">{{ s.cardValue !== undefined ? s.cardValue : s.value }}</div>
              <div v-if="s.sub" class="text-[10px] text-stone-400 mt-1 truncate">{{ s.sub }}</div>
            </div>
          </div>

          <div v-if="recos.length" class="mt-4 space-y-2">
            <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400">Suggestions</div>
            <div v-for="(r, i) in recos" :key="i" class="flex items-center gap-2.5 rounded-xl bg-white ring-1 ring-[var(--accent-200)]/50 px-3 py-2">
              <span v-html="zapIcon(14)" class="text-[var(--accent-600)] flex-shrink-0" />
              <span class="text-[12px] text-stone-700 flex-1">{{ r.txt }}</span>
              <button class="inline-flex items-center h-7 px-2.5 rounded-md text-[11.5px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]" @click="applyReco(i)">Apply</button>
              <button class="w-7 h-7 rounded-lg hover:bg-stone-100 flex items-center justify-center text-stone-400" @click="recos.splice(i, 1)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg></button>
            </div>
          </div>

          <div class="mt-4">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[11px] font-semibold uppercase tracking-wide text-stone-400">Agent activity</span>
              <span class="text-[11px] text-stone-400">Watching {{ AUTOPILOT.watching }} active picks</span>
            </div>
            <div class="space-y-1">
              <div v-for="(e, i) in AUTOPILOT.feed" :key="i" class="flex items-center gap-2.5 px-1 py-1">
                <span class="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0" :class="feedStyle(e.kind).cls" v-html="feedStyle(e.kind).icon" />
                <span class="text-[12px] text-stone-700 flex-1">{{ e.act }}</span>
                <span class="text-[10.5px] text-stone-400 tabular-nums flex-shrink-0">{{ e.t }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-1.5 text-[11px] font-medium text-stone-500"><span v-html="k.icon" /><span>{{ k.label }}</span></div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums leading-none mt-2">{{ k.value }}</div>
      </div>
    </div>

    <!-- filters -->
    <div class="flex items-center gap-1.5 mb-3 overflow-x-auto pb-1">
      <div v-if="isLiveData" class="relative flex-shrink-0">
        <Icon name="search" :size="13" class="absolute start-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
        <input v-model="q" :placeholder="t('pl.searchPh')" @input="onSearch"
               class="h-9 w-[210px] ps-8 pe-3 text-[13px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none" />
      </div>
      <button v-for="f in filters" :key="f[0]" class="px-3 h-8 text-[12px] font-medium rounded-lg ring-1 transition-colors whitespace-nowrap" :class="filter === f[0] ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'" @click="setFilter(f[0])">{{ f[1] }}</button>
    </div>

    <!-- table -->
    <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[760px]">
          <thead>
            <tr class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th class="text-start px-4 py-2.5">{{ t("pl.thPl") }}</th>
              <th class="text-start px-4 py-2.5">{{ t("pl.thPicker") }}</th>
              <th v-if="!isLiveData" class="text-start px-4 py-2.5">{{ t("pl.thOrigin") }}</th>
              <th class="text-start px-4 py-2.5">{{ t("pl.thOrders") }}</th>
              <th class="text-end px-4 py-2.5 hidden sm:table-cell">{{ t("pl.thItems") }}</th>
              <th class="text-end px-4 py-2.5">{{ t("pl.thQty") }}</th>
              <th v-if="isLiveData" class="text-start px-4 py-2.5 hidden md:table-cell">{{ t("pl.thCreated") }}</th>
              <th class="text-start px-4 py-2.5 w-[150px]">{{ t("pl.thProgress") }}</th>
              <th class="text-start px-4 py-2.5">{{ t("pl.thStatus") }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr v-for="p in shown" :key="p.no" class="transition-colors cursor-pointer hover:bg-stone-50" @click="openDetail(p)">
              <td class="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900 whitespace-nowrap">{{ p.no }}<svg v-if="p.errors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="12" height="12" class="text-rose-500 inline ms-1.5 -mt-0.5"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg></td>
              <td class="px-4 py-2.5"><div class="flex items-center gap-1.5"><span class="w-5 h-5 rounded-full bg-stone-200 text-stone-600 flex items-center justify-center text-[9px] font-bold">{{ pickerInitials(p.picker) }}</span><span class="text-[12px] text-stone-700">{{ pickerName(p.picker) }}</span></div></td>
              <td v-if="!isLiveData" class="px-4 py-2.5"><span v-if="plOrigin(p) === 'manual'" class="inline-flex items-center gap-1 text-[10.5px] font-medium text-stone-500 bg-stone-100 rounded px-1.5 py-0.5 whitespace-nowrap"><span v-html="usersIcon(9)" />Manual</span><span v-else class="inline-flex items-center gap-1 text-[10.5px] font-medium text-[var(--accent-700)] bg-[var(--accent-50)] rounded px-1.5 py-0.5 whitespace-nowrap"><span v-html="zapIcon(9)" />Autopilot</span></td>
              <td class="px-4 py-2.5 text-[12px] text-stone-600">
                <div class="flex items-center gap-1.5">
                  <span v-if="p.order === 'combined'" class="inline-flex items-center px-2 h-[20px] rounded-md text-[11px] font-medium text-violet-700 bg-violet-50 ring-1 ring-violet-200 whitespace-nowrap">{{ t("pl.combined") }}<template v-if="p.orders"> · {{ p.orders }}</template></span>
                  <span v-else class="font-mono text-[11.5px] truncate">{{ p.customer || p.order }}</span>
                  <span v-if="p.mono" class="inline-flex items-center gap-1 px-1.5 h-[20px] rounded-md text-[10.5px] font-semibold text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200/70 whitespace-nowrap" :title="t('pl.monoHint')"><Icon name="layers" :size="10" />{{ t('pl.mono') }}</span>
                </div>
              </td>
              <td class="px-4 py-2.5 text-end text-[12px] text-stone-500 tabular-nums hidden sm:table-cell">{{ p.items ?? "—" }}</td>
              <td class="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{{ p.qty }}</td>
              <td v-if="isLiveData" class="px-4 py-2.5 text-[11.5px] text-stone-500 tabular-nums whitespace-nowrap hidden md:table-cell">{{ (p.created || "").slice(5) }}</td>
              <td class="px-4 py-2.5"><div v-if="p.pct > 0" class="flex items-center gap-2"><div class="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden"><div class="h-full rounded-full" :class="p.errors ? 'bg-rose-500' : 'bg-emerald-500'" :style="{ width: p.pct + '%' }" /></div><span class="text-[10.5px] text-stone-400 tabular-nums w-[28px]">{{ p.pct }}%</span></div><span v-else class="text-[11px] text-stone-300">—</span></td>
              <td class="px-4 py-2.5"><span v-if="p.errors" class="inline-flex items-center gap-1 px-2 h-[20px] rounded-md text-[11px] font-medium text-rose-700 bg-rose-50 ring-1 ring-rose-200 whitespace-nowrap"><span class="w-1.5 h-1.5 rounded-full bg-rose-500" />Short-pick</span><span v-else class="inline-flex items-center gap-1 px-2 h-[20px] rounded-md text-[11px] font-medium ring-1" :class="plStatusChip(p.status)"><span class="w-1.5 h-1.5 rounded-full" :class="plStatusDot(p.status)" />{{ plStatusLabel(p.status) }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-if="!shown.length && !loading" class="text-center text-[12.5px] text-stone-400 py-12">{{ t("pl.noRows") }}</div>
      </div>
      <div v-if="isLiveData && total > pageSize" class="flex items-center justify-between px-4 py-2.5 border-t border-stone-100 bg-stone-50/50">
        <span class="text-[11.5px] text-stone-500 tabular-nums">
          {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} {{ t("pl.of") }} {{ total }}
        </span>
        <div class="flex items-center gap-1">
          <button class="pager-btn" :disabled="page <= 1" @click="page--; load(true)"><Icon name="chevron-left" :size="13" class="flip-rtl" /></button>
          <span class="text-[11.5px] text-stone-600 tabular-nums px-1.5">{{ page }} / {{ Math.max(1, Math.ceil(total / pageSize)) }}</span>
          <button class="pager-btn" :disabled="page * pageSize >= total" @click="page++; load(true)"><Icon name="chevron-right" :size="13" class="flip-rtl" /></button>
        </div>
      </div>
    </div>

    <SuggestBatchesModal ref="sbModal" @created="load()" />

    <!-- ══════════ SMART PICK MODAL ══════════ -->
    <div v-if="create" class="fixed inset-0 z-[150] flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div class="absolute inset-0 bg-stone-900/30 backdrop-blur-[1px] animate-fade-in" @click="create = false" />
      <div class="relative w-full max-w-[680px] bg-white rounded-2xl shadow-[0_24px_64px_-16px_rgba(0,0,0,0.3)] animate-scale-in overflow-hidden flex flex-col max-h-[88vh]">
        <header class="flex items-center justify-between px-5 py-3.5 border-b border-stone-100">
          <div class="flex items-center gap-2.5">
            <span class="w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-700)] flex items-center justify-center" v-html="zapIcon(16)" />
            <div><div class="text-[14.5px] font-semibold text-stone-900">Pick lists</div><div class="text-[11.5px] text-stone-500">{{ smart.stats.orders }} orders of pending</div></div>
          </div>
          <button class="w-8 h-8 rounded-lg hover:bg-stone-100 flex items-center justify-center text-stone-400" @click="create = false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg></button>
        </header>
        <div class="px-5 pt-3">
          <div class="inline-flex bg-stone-100/80 rounded-lg p-0.5 w-full">
            <button v-for="m in [['smart','Smart auto'],['manual','Manual']]" :key="m[0]" class="flex-1 h-8 text-[12.5px] font-medium rounded-md transition-all" :class="mode === m[0] ? 'bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]' : 'text-stone-500'" @click="mode = m[0]">{{ m[1] }}</button>
          </div>
        </div>

        <div class="p-5 overflow-y-auto">
          <template v-if="mode === 'smart'">
            <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">Grouping strategy</div>
            <div class="grid grid-cols-2 gap-2 mb-4">
              <button v-for="s in strategies" :key="s.k" class="text-start rounded-xl ring-1 p-3 transition-all" :class="strategy === s.k ? 'ring-[var(--accent-400)] bg-[var(--accent-50)]/40' : 'ring-stone-200 hover:ring-stone-300'" @click="strategy = s.k">
                <div class="flex items-center gap-2"><span :class="strategy === s.k ? 'text-[var(--accent-700)]' : 'text-stone-400'" v-html="s.icon" /><span class="text-[12.5px] font-semibold text-stone-900">{{ s.label }}</span></div>
                <div class="text-[11px] text-stone-500 mt-0.5">{{ s.sub }}</div>
              </button>
            </div>

            <div class="flex items-center gap-3 rounded-xl bg-emerald-50 ring-1 ring-emerald-200/60 px-4 py-2.5 mb-4">
              <span v-html="trendIcon(18)" class="text-emerald-600 flex-shrink-0" />
              <div class="text-[12.5px] text-emerald-800 flex-1"><span class="font-bold tabular-nums">{{ smart.stats.saved }}%</span> walk saved · <span class="font-semibold">{{ smart.stats.batches }}</span> batches of {{ smart.stats.orders }} orders</div>
            </div>

            <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">Generated batches</div>
            <div class="space-y-2">
              <div v-for="(g, i) in smart.groups" :key="g.key" class="rounded-xl ring-1 ring-stone-200 p-3">
                <div class="flex items-center justify-between gap-2">
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="font-mono text-[12px] font-semibold text-stone-900">{{ g.no }}</span>
                    <span class="inline-flex items-center px-2 h-[20px] rounded-md text-[11px] font-medium text-violet-700 bg-violet-50 ring-1 ring-violet-200 whitespace-nowrap">{{ g.kind }}</span>
                    <span class="text-[12px] text-stone-600 truncate">{{ g.label }}</span>
                  </div>
                  <div class="flex items-center gap-1.5 flex-shrink-0">
                    <span class="w-5 h-5 rounded-full bg-stone-200 text-stone-600 flex items-center justify-center text-[9px] font-bold">{{ initials(byId(pickers[i % pickers.length].id).name) }}</span>
                    <span class="text-[11px] text-stone-500 hidden sm:inline">{{ byId(pickers[i % pickers.length].id).short }}</span>
                  </div>
                </div>
                <div class="flex items-center gap-3 mt-2 text-[11px] text-stone-500">
                  <span class="tabular-nums">{{ g.orders }} orders</span><span class="text-stone-300">·</span>
                  <span class="tabular-nums">{{ g.items }} lines</span><span class="text-stone-300">·</span>
                  <span class="tabular-nums">{{ g.units }} units</span><span class="text-stone-300">·</span>
                  <span class="inline-flex items-center gap-1 tabular-nums"><Icon name="map-pin" :size="10" />{{ g.aisles }} aisles</span>
                </div>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="rounded-lg bg-amber-50 ring-1 ring-amber-200/60 px-3 py-2 mb-3 flex items-start gap-2 text-[11.5px] text-amber-800"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="13" height="13" class="text-amber-500 mt-0.5 flex-shrink-0"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>Use when Autopilot needs an override — hand-pick orders &amp; picker.</div>
            <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">Assign to picker</div>
            <div class="grid grid-cols-3 gap-1.5 mb-4">
              <button v-for="p in pickers" :key="p.id" class="flex items-center gap-1.5 px-2 py-1.5 rounded-lg ring-1 transition-all" :class="manPicker === p.id ? 'ring-[var(--accent-400)] bg-[var(--accent-50)]/40' : 'ring-stone-200 hover:ring-stone-300'" @click="manPicker = p.id"><span class="w-5 h-5 rounded-full bg-stone-200 text-stone-600 flex items-center justify-center text-[9px] font-bold">{{ initials(p.name) }}</span><span class="text-[11.5px] font-medium text-stone-800 truncate">{{ p.short }}</span></button>
            </div>
            <div class="text-[11px] font-semibold uppercase tracking-wide text-stone-400 mb-2">Select orders to pick · {{ selOrders.size }} selected</div>
            <div class="space-y-1.5">
              <button v-for="o in poolOrders" :key="o" class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg ring-1 text-start transition-all" :class="selOrders.has(o) ? 'ring-[var(--accent-400)] bg-[var(--accent-50)]/40' : 'ring-stone-200 hover:ring-stone-300'" @click="toggleOrder(o)">
                <span class="w-4 h-4 rounded flex items-center justify-center ring-1 flex-shrink-0" :class="selOrders.has(o) ? 'bg-[var(--accent-600)] ring-[var(--accent-600)] text-white' : 'ring-stone-300'"><Icon v-if="selOrders.has(o)" name="check-circle" :size="11" /></span>
                <span class="font-mono text-[12px] font-semibold text-stone-900">{{ o }}</span>
                <span class="text-[12px] text-stone-600 flex-1 truncate">{{ poolLines(o)[0].customer }}</span>
                <span class="text-[11px] text-stone-400">{{ poolLines(o).length }} lines</span>
              </button>
            </div>
          </template>
        </div>

        <footer class="flex items-center justify-end gap-2 px-5 py-3.5 border-t border-stone-100 bg-stone-50/60">
          <button class="inline-flex items-center h-9 px-3 rounded-lg text-[13px] font-medium text-stone-600 hover:bg-stone-100" @click="create = false">Cancel</button>
          <button v-if="mode === 'smart'" class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)]" @click="generate"><Icon name="check-circle" :size="15" />Generate {{ smart.groups.length }} pick lists</button>
          <button v-else class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] disabled:opacity-40" :disabled="selOrders.size === 0" @click="createManual"><Icon name="check-circle" :size="15" />Create pick list ({{ selOrders.size }})</button>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import SuggestBatchesModal from "@/components/SuggestBatchesModal.vue";
import { PICKLISTS as DEMO_PICKLISTS, TEAM, WAREHOUSE, byId } from "@/lib/handoffData.js";
import { api, apiPost, liveOr } from "@/lib/resource";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";

const { success, warn } = useToast();
const { t } = useI18n();

// ── local data (from data.jsx) ─────────────────────────────────────────
const BIN_ZONE = { J: "FAST ZONE - JM", F: "SLOW ZONE - JM", I: "Cosmetic zone - JM", H: "MU Zone - JM", E: "Accessory Zone - JM", G: "Textile Zone - JM" };
const PICK_POOL = [
  { so: "#242646", sku: "MCH100013", code: "46029739950334", grp: "Home Fragrance", uom: "Nos", name: "Diffuseur huile MCH — box", bin: "J8C - JM", qty: 1, customer: "oualid elmouden" },
  { so: "#242644", sku: "ACC11008", code: "47594099441918", grp: "Accessories", uom: "Nos", name: "Trousse maquillage zip", bin: "H14A - JM", qty: 1, customer: "Chada Rami" },
  { so: "#242644", sku: "ACC11015", code: "47594099442011", grp: "Accessories", uom: "Nos", name: "Miroir LED pliable", bin: "H14C - JM", qty: 1, customer: "Chada Rami" },
  { so: "#242641", sku: "TXT55012", code: "46881234500021", grp: "Textile", uom: "Nos", name: "Foulard soie imprimé", bin: "G13C - JM", qty: 1, customer: "Hamid Hamid" },
  { so: "#242638", sku: "CSM44021", code: "46029811200334", grp: "Cosmetics", uom: "box", name: "Sérum éclat 30ml", bin: "I4A - JM", qty: 2, customer: "Mohmad Mohmad", serial: true },
  { so: "#242620", sku: "MCH100013", code: "46029739950334", grp: "Home Fragrance", uom: "Nos", name: "Diffuseur huile MCH — box", bin: "J8C - JM", qty: 1, customer: "Najat Bennani" },
  { so: "#242620", sku: "MCH100020", code: "46029739950571", grp: "Home Fragrance", uom: "Nos", name: "Recharge huile lavande", bin: "J7B - JM", qty: 1, customer: "Najat Bennani" },
  { so: "#242618", sku: "MUZ22014", code: "46772200140088", grp: "Makeup", uom: "Nos", name: "Palette ombres MU", bin: "H13B - JM", qty: 1, customer: "Imane Tazi", batch: true },
  { so: "#242615", sku: "CSM44021", code: "46029811200334", grp: "Cosmetics", uom: "box", name: "Sérum éclat 30ml", bin: "I4A - JM", qty: 1, customer: "Fouzia Fouzia", serial: true },
  { so: "#242612", sku: "MCH100013", code: "46029739950334", grp: "Home Fragrance", uom: "Nos", name: "Diffuseur huile MCH — box", bin: "J8C - JM", qty: 1, customer: "Sanae R." },
  { so: "#242609", sku: "ACC11015", code: "47594099442011", grp: "Accessories", uom: "Nos", name: "Miroir LED pliable", bin: "H14C - JM", qty: 1, customer: "Loubna T." },
  { so: "#242607", sku: "TXT55012", code: "46881234500021", grp: "Textile", uom: "Nos", name: "Foulard soie imprimé", bin: "G13C - JM", qty: 1, customer: "Nawal B." },
  { so: "#242605", sku: "MCH100020", code: "46029739950571", grp: "Home Fragrance", uom: "Nos", name: "Recharge huile lavande", bin: "J7B - JM", qty: 1, customer: "Soukaina Idrissi" },
  { so: "#242601", sku: "CSM44021", code: "46029811200334", grp: "Cosmetics", uom: "box", name: "Sérum éclat 30ml", bin: "I4A - JM", qty: 1, customer: "Yasmine Alaoui", serial: true },
];
const AUTOPILOT = {
  active: true, nextRunMin: 12, createdToday: 14, assignedToday: 14, efficiency: 41, watching: 6,
  feed: [
    { t: "2m", act: "Created PL-51440 → PL-51443 · 4 zone batches", kind: "create" },
    { t: "2m", act: "Auto-assigned to Marouane, Asmaa, Saad, Oussama by load + zone", kind: "assign" },
    { t: "14m", act: "Marouane idle 6 min — re-routed 1 batch to Asmaa", kind: "balance" },
    { t: "31m", act: "Flagged PL-51388 stalled (Short-pick) — alerted dispatcher", kind: "alert" },
    { t: "1h", act: "Held 8 SLOW-zone orders for next batch (below threshold)", kind: "hold" },
  ],
  recos: [
    { txt: "Batch 6 Cosmetic-zone orders now — saves ~22 min walking before cutoff", strat: "zone" },
    { txt: "Marouane is fastest on FAST zone — assign next FAST batch to him", strat: "sku" },
  ],
};

// ── inline lucide-style icons (missing from Icon.vue set) ───────────────
const zapIcon = (s) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="${s}" height="${s}"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;
const boxIcon = (s) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="${s}" height="${s}"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>`;
const usersIcon = (s) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="${s}" height="${s}"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`;
const layersIcon = (s) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="${s}" height="${s}" style="display:inline"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`;
const clockIcon = (s) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="${s}" height="${s}"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
const trendIcon = (s) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="${s}" height="${s}"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>`;
const alertIcon = (s) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="${s}" height="${s}"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

// ── helpers ─────────────────────────────────────────────────────────────
function initials(name) {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
}
const cap = (s) => s[0].toUpperCase() + s.slice(1);
const binZone = (bin) => ((bin || "").includes(" - ") && (bin || "").length > 8) ? bin : (BIN_ZONE[(bin || "?")[0]] || "Other");
const aisle = (bin) => (bin || "?").match(/^[A-Z]\d*/)?.[0] || "?";

const feedStyle = (kind) => {
  const map = {
    create: { cls: "bg-[var(--accent-50)] text-[var(--accent-700)]", icon: zapIcon(12) },
    assign: { cls: "bg-blue-50 text-blue-600", icon: layersIcon(12) },
    balance: { cls: "bg-violet-50 text-violet-600", icon: usersIcon(12) },
    alert: { cls: "bg-rose-50 text-rose-600", icon: alertIcon(12) },
    hold: { cls: "bg-amber-50 text-amber-600", icon: clockIcon(12) },
  };
  return map[kind] || map.create;
};

// ── autoPickGroups engine (from data.jsx) ───────────────────────────────
function autoPickGroups(strategy, cap2 = 12) {
  const pool = PICK_POOL;
  const totalLines = pool.length;
  let groups = [];
  if (strategy === "sku") {
    const m = {};
    pool.forEach((l) => { (m[l.sku] = m[l.sku] || []).push(l); });
    groups = Object.entries(m).map(([sku, ls]) => ({ key: sku, kind: "Batch SKU", label: ls[0].name, lines: ls }));
  } else if (strategy === "single") {
    const orders = {};
    pool.forEach((l) => { (orders[l.so] = orders[l.so] || []).push(l); });
    const singles = Object.values(orders).filter((ls) => ls.length === 1).flat();
    const multi = Object.entries(orders).filter(([, ls]) => ls.length > 1);
    groups = [{ key: "blitz", kind: "Single-item blitz", label: `${singles.length} one-line orders`, lines: singles }];
    multi.forEach(([so, ls]) => groups.push({ key: so, kind: "Multi-line", label: so, lines: ls }));
  } else if (strategy === "zone") {
    const m = {};
    pool.forEach((l) => { const z = binZone(l.bin); (m[z] = m[z] || []).push(l); });
    groups = Object.entries(m).map(([z, ls]) => ({ key: z, kind: "Zone cluster", label: z.replace(" - JM", ""), lines: ls }));
  } else {
    const m = {};
    pool.forEach((l) => { const z = binZone(l.bin); (m[z] = m[z] || []).push(l); });
    Object.entries(m).forEach(([z, ls]) => {
      for (let i = 0; i < ls.length; i += cap2) groups.push({ key: z + i, kind: "Balanced", label: z.replace(" - JM", ""), lines: ls.slice(i, i + cap2) });
    });
  }
  groups = groups.filter((g) => g.lines.length).map((g, i) => {
    const orders = new Set(g.lines.map((l) => l.so)).size;
    const aisles = new Set(g.lines.map((l) => aisle(l.bin))).size;
    const units = g.lines.reduce((a, l) => a + l.qty, 0);
    return { ...g, no: `PL-${51440 + i}`, orders, aisles, units, items: g.lines.length };
  });
  const baselineAisles = pool.length;
  const newAisles = groups.reduce((a, g) => a + g.aisles, 0);
  const saved = Math.max(0, Math.round((1 - newAisles / baselineAisles) * 100));
  return { groups, stats: { lines: totalLines, units: pool.reduce((a, l) => a + l.qty, 0), orders: new Set(pool.map((l) => l.so)).size, batches: groups.length, saved } };
}

// ── list state (server-driven when live · demo seed as fallback) ────────
const rows = ref(DEMO_PICKLISTS.map((p) => ({ ...p })));
const sbModal = ref(null);
const sbPickers = ref([]);

// ── Live autopilot card state (was lost in a refactor — restored + wired) ──
const ap = ref({ enabled: false, runs: [] });
const apBusy = ref(false);
async function apRefresh() {
  const s = await liveOr(null, () => api("picking.autopilot_status"));
  if (s) ap.value = { enabled: !!s.enabled, runs: Array.isArray(s.runs) ? s.runs : [] };
}
async function apToggle() {
  apBusy.value = true;
  try {
    await apiPost("picking.autopilot_toggle", { enabled: !ap.value.enabled });
    await apRefresh();
  } catch (e) { warn("Autopilot", String(e.message || e)); }
  finally { apBusy.value = false; }
}
async function apRunNow() {
  apBusy.value = true;
  try {
    const r = await apiPost("picking.autopilot_run");
    success(t("pl.apRun"), r && r.created != null ? `${r.created} pick lists` : "");
    await apRefresh();
    load();
  } catch (e) { warn("Autopilot", String(e.message || e)); }
  finally { apBusy.value = false; }
}
const dataMode = ref("loading");
const counts = ref({});
const total = ref(0);
const page = ref(1);
const pageSize = 30;
const daysF = ref(7);
const statusF = ref("");
const q = ref("");
const loading = ref(false);
let searchTimer = null;
const isLiveData = computed(() => dataMode.value === "live");

async function load(keepPage = false) {
  if (!keepPage) page.value = 1;
  loading.value = true;
  const live = await liveOr(null, () => api("picking.pick_lists", {
    days: daysF.value, status: statusF.value || undefined,
    q: q.value.trim() || undefined,
    limit: pageSize, offset: (page.value - 1) * pageSize,
  }));
  if (live && Array.isArray(live.rows)) {
    dataMode.value = "live";
    rows.value = live.rows.map((p) => ({ ...p }));
    counts.value = live.counts || {};
    total.value = live.total || 0;
    if (!ap.value.runs.length && !ap.value.enabled) apRefresh();
  } else if (dataMode.value !== "live") {
    dataMode.value = "demo";
  }
  loading.value = false;
}
onMounted(load);
function onSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(() => load(), 350); }
function setFilter(k) {
  filter.value = k;
  if (isLiveData.value) { statusF.value = k === "all" ? "" : k; load(); }
}

// Live rows carry picker EMAILS (assigned picker, falling back to the PL
// owner — on production pickers create their own PLs); demo rows carry ids.
const PICKER_SHORT = {
  marouaneelmessaoudi07: "Marouane", mouakkalanass: "Anass", anaskarrassi: "Anas K.",
  asmaazirary7: "Asmaa", lamdanisaad12: "Saad", ossamanahila: "Oussama",
  saidnakri65: "Said", redazaari47: "Reda", elabdouny99: "Abdouny",
};
function pickerName(p) {
  if (!p) return "—";
  if (String(p).includes("@")) {
    const k = String(p).split("@")[0];
    return PICKER_SHORT[k] || k;
  }
  return byId(p)?.short || byId(p)?.name || p;
}
function pickerInitials(p) {
  const s = pickerName(p);
  return ((s[0] || "?") + (s[1] || "")).toUpperCase();
}
const create = ref(false);
const detail = ref(null);
const autopilot = ref(false);
const filter = ref("all");

const apOn = ref(AUTOPILOT.active);
const thinking = ref(false);
const recos = reactive([...AUTOPILOT.recos]);
const apTab = ref("overview");
const apTabs = [["overview", "Overview"], ["rules", "Rules"], ["history", "Decision log"], ["perf", "Performance"]];
const ruleStrategy = ref("zone");
const ruleSchedule = ref("30m");
const batchThresh = ref(4);
const idleMin = ref(6);
const toggles = reactive([
  { key: "autoAssign", label: "Auto-assign to pickers", on: true },
  { key: "idleReroute", label: "Re-route idle pickers", on: true },
  { key: "slaWatch", label: "SLA risk alerts", on: true },
]);

const withErrors = computed(() => rows.value.filter((p) => p.errors).length);
const kpis = computed(() => isLiveData.value ? [
  { label: t("pl.kOpen"), value: counts.value.open || 0, icon: boxIcon(13) },
  { label: t("pl.kShipped"), value: counts.value.shipped || 0, icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>` },
  { label: t("pl.kDraft"), value: counts.value.draft || 0, icon: layersIcon(13) },
  { label: t("pl.kCancelled"), value: counts.value.cancelled || 0, icon: alertIcon(13) },
] : [
  { label: "Open / draft", value: rows.value.filter((p) => p.status === "open" || p.status === "draft").length, icon: boxIcon(13) },
  { label: "Completed", value: rows.value.filter((p) => p.status === "completed").length, icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>` },
  { label: "Combined picks", value: rows.value.filter((p) => p.order === "combined").length, icon: layersIcon(13) },
  { label: "Pick errors", value: withErrors.value, icon: alertIcon(13) },
]);

const filters = computed(() => isLiveData.value ? [
  ["all", `${t("pl.fAll")} · ${(counts.value.draft || 0) + (counts.value.open || 0) + (counts.value.shipped || 0) + (counts.value.partial || 0) + (counts.value.cancelled || 0)}`],
  ["draft", `${t("pl.fDraft")} · ${counts.value.draft || 0}`],
  ["open", `${t("pl.fOpen")} · ${counts.value.open || 0}`],
  ["shipped", `${t("pl.fShipped")} · ${counts.value.shipped || 0}`],
  ["cancelled", `${t("pl.fCancelled")} · ${counts.value.cancelled || 0}`],
] : [
  ["all", "All"], ["draft", "Draft"], ["open", "Open"], ["completed", "Completed"], ["cancelled", "Cancelled"], ["errors", `Errors·${withErrors.value}`],
]);

const shown = computed(() => isLiveData.value
  ? rows.value
  : rows.value.filter((p) => filter.value === "all" || p.status === filter.value || (filter.value === "errors" && p.errors)).slice()
);

const plOrigin = (p) => p.origin || (["Zone cluster", "Balanced", "Batch SKU", "Single-item blitz", "Multi-line"].includes(p.item) ? "auto" : p.item === "Manual" ? "manual" : "auto");

const plStatusChip = (s) => ({ draft: "text-stone-600 bg-stone-100 ring-stone-200", open: "text-amber-700 bg-amber-50 ring-amber-200", completed: "text-emerald-700 bg-emerald-50 ring-emerald-200", shipped: "text-emerald-700 bg-emerald-50 ring-emerald-200", partial: "text-orange-700 bg-orange-50 ring-orange-200", cancelled: "text-rose-700 bg-rose-50 ring-rose-200" }[s] || "text-stone-600 bg-stone-100 ring-stone-200");
const plStatusDot = (s) => ({ draft: "bg-stone-400", open: "bg-amber-500", completed: "bg-emerald-500", shipped: "bg-emerald-500", partial: "bg-orange-500", cancelled: "bg-rose-500" }[s] || "bg-stone-400");
const plStatusLabel = (s) => isLiveData.value
  ? ({ draft: t("pl.fDraft"), open: t("pl.fOpen"), shipped: t("pl.fShipped"), partial: t("pl.fPartial"), cancelled: t("pl.fCancelled") }[s] || s)
  : cap(s);

// ── autopilot card ──────────────────────────────────────────────────────
const apStats = computed(() => [
  { label: "Next run", value: `${AUTOPILOT.nextRunMin}m`, cardValue: thinking.value ? "—" : `${AUTOPILOT.nextRunMin}m`, sub: "every 30 min · cutoff-aware", live: true, icon: clockIcon(13) },
  { label: "Created today", value: AUTOPILOT.createdToday, icon: boxIcon(13) },
  { label: "Auto-assigned", value: AUTOPILOT.assignedToday, icon: usersIcon(13) },
  { label: "Efficiency gain", value: "+" + AUTOPILOT.efficiency + "%", tone: "emerald", icon: trendIcon(13) },
]);
const perfStats = [
  { label: "Walk time saved today", value: "3h 12m", tone: "emerald", icon: clockIcon(13) },
  { label: "Assign accuracy", value: "96%", icon: usersIcon(13) },
  { label: "Runs today", value: 18, icon: zapIcon(13) },
];
const fullLog = [
  ...AUTOPILOT.feed,
  { t: "1h", act: "Created PL-51436 · single-item blitz (5 orders)", kind: "create" },
  { t: "2h", act: "Auto-assigned 3 batches to morning shift", kind: "assign" },
  { t: "2h", act: "SLA risk: 4 picked orders not labeled — pinged Reda", kind: "alert" },
];
const sparkData = [22, 28, 25, 31, 34, 30, 36, 38, 35, 40, 39, 42, 41, 41];
const sparkPoints = computed(() => {
  const max = Math.max(...sparkData), min = Math.min(...sparkData);
  return sparkData.map((v, i) => {
    const x = (i / (sparkData.length - 1)) * 300;
    const y = 110 - ((v - min) / (max - min || 1)) * 100;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
});

function runNow() {
  thinking.value = true;
  setTimeout(() => {
    thinking.value = false;
    const gs = autoPickGroups("zone").groups.map((g, i) => ({
      no: g.no, customer: g.kind === "Batch SKU" ? g.label : `${g.kind} · ${g.label}`, item: g.kind,
      bin: g.aisles > 1 ? "Multiple" : g.lines[0].bin, qty: g.units, items: g.items, status: "open", pct: 0,
      picker: TEAM.filter((p) => p.role === "picker")[i % 5].id, order: g.orders > 1 ? "combined" : g.lines[0].so,
    }));
    rows.value = [...gs, ...rows.value];
    success("Autopilot generated 4 pick lists · auto-assigned · 41% less walking");
  }, 1400);
}
function applyReco(i) {
  const gs = autoPickGroups("zone").groups.map((g, j) => ({
    no: g.no, customer: g.kind === "Batch SKU" ? g.label : `${g.kind} · ${g.label}`, item: g.kind,
    bin: g.aisles > 1 ? "Multiple" : g.lines[0].bin, qty: g.units, items: g.items, status: "open", pct: 0,
    picker: TEAM.filter((p) => p.role === "picker")[j % 5].id, order: g.orders > 1 ? "combined" : g.lines[0].so,
  }));
  rows.value = [...gs, ...rows.value];
  recos.splice(i, 1);
  success("Suggestion applied · pick list created");
}

// ── smart pick modal ────────────────────────────────────────────────────
const mode = ref("smart");
const strategy = ref("zone");
const pickers = TEAM.filter((p) => p.role === "picker");
const manPicker = ref(pickers[0].id);
const selOrders = reactive(new Set());
const poolOrders = [...new Set(PICK_POOL.map((l) => l.so))];
const poolLines = (o) => PICK_POOL.filter((l) => l.so === o);
const smart = computed(() => autoPickGroups(strategy.value));
const strategies = [
  { k: "zone", icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>`, label: "By zone", sub: "Cluster by aisle — least walking" },
  { k: "sku", icon: layersIcon(15), label: "By SKU", sub: "Batch-pick same product" },
  { k: "single", icon: zapIcon(15), label: "Single-item blitz", sub: "All 1-line orders in one sweep" },
  { k: "balanced", icon: usersIcon(15), label: "Balanced", sub: "Zone clusters, capped per picker" },
];

function toggleOrder(o) { selOrders.has(o) ? selOrders.delete(o) : selOrders.add(o); }

function generate() {
  const { groups, stats } = smart.value;
  rows.value = [
    ...groups.map((g, i) => ({
      no: g.no, customer: g.kind === "Batch SKU" ? g.label : `${g.kind} · ${g.label}`, item: g.kind,
      bin: g.aisles > 1 ? "Multiple" : g.lines[0].bin, qty: g.units, items: g.items, status: "open", pct: 0,
      picker: pickers[i % pickers.length].id, order: g.orders > 1 ? "combined" : g.lines[0].so,
    })),
    ...rows.value,
  ];
  success(`${groups.length} smart pick lists created · ${stats.saved}% less walking`);
  create.value = false;
}
function createManual() {
  const chosen = PICK_POOL.filter((l) => selOrders.has(l.so));
  const combined = selOrders.size > 1;
  rows.value = [
    { no: "PL-" + (51450 + Math.floor(Math.random() * 40)), customer: combined ? `Manual · ${selOrders.size} orders` : PICK_POOL.find((l) => selOrders.has(l.so))?.customer, item: "Manual", bin: "Multiple", qty: chosen.reduce((a, l) => a + l.qty, 0), items: chosen.length, status: "open", pct: 0, picker: manPicker.value, order: combined ? "combined" : [...selOrders][0] },
    ...rows.value,
  ];
  success(`Manual pick list created · ${selOrders.size} orders · ${byId(manPicker.value).short}`);
  create.value = false;
}

// ── detail view ─────────────────────────────────────────────────────────
const view = ref("walk");
const liveDetail = ref(null);
const submitting = ref(false);
const assigning = ref(false);
const confirmSubmit = ref(false);
const confirmCancel = ref(false);
const liveAwbUrl = ref("");
async function openDetail(p) {
  detail.value = p;
  liveDetail.value = null;
  liveAwbUrl.value = "";
  confirmSubmit.value = confirmCancel.value = false;
  if (isLiveData.value) {
    const [d] = await Promise.all([
      liveOr(null, () => api("picking.pick_list_detail", { name: p.no })),
      sbPickers.value.length ? Promise.resolve() : loadPickers(),
    ]);
    if (d && d.no) {
      liveDetail.value = d;
      const awbOrder = (d.orders || []).find((o) => o.awb);
      if (awbOrder && awbOrder.dn) liveAwbUrl.value = "/app/delivery-note/" + encodeURIComponent(awbOrder.dn);
    }
  }
}
async function loadPickers() {
  const pk = await liveOr(null, () => api("picking.pickers"));
  if (Array.isArray(pk)) sbPickers.value = pk.filter((p) => p.email);
}
async function doAssign(email) {
  assigning.value = true;
  try {
    await apiPost("picking.assign_picker", { name: detail.value.no, picker: email });
    if (liveDetail.value) liveDetail.value = { ...liveDetail.value, picker: email };
    if (email) success(t("pl.assignedOk").replace("{n}", pickerName(email)));
    await loadPickers();
  } catch (e) { warn("Couldn't assign", String(e.message || e)); }
  finally { assigning.value = false; }
}
async function doSubmit() {
  confirmSubmit.value = false;
  submitting.value = true;
  try {
    const res = await apiPost("picking.submit_pick_list", { name: detail.value.no });
    success(t("pl.submitOk").replace("{awb}", res.awb || "—"));
    detail.value = null;      // back to the list; it's off to shipping now
    load();
  } catch (e) { warn("Couldn't submit the pick list", String(e.message || e)); }
  finally { submitting.value = false; }
}
async function doCancel() {
  confirmCancel.value = false;
  try {
    await apiPost("picking.cancel_pick_list", { name: detail.value.no });
    success(t("pl.cancelledOk"));
    detail.value = null;
    load();
  } catch (e) { warn("Couldn't cancel", String(e.message || e)); }
}
const lines = computed(() => {
  const pl = detail.value;
  if (!pl) return [];
  if (liveDetail.value) {
    const done = liveDetail.value.status !== "draft";
    return (liveDetail.value.lines || []).map((l) => ({
      ...l, code: "", serial: false, batch: false,
      picked: done && l.pickedQty >= l.qty,
      partial: l.pickedQty > 0 && l.pickedQty < l.qty,
      pickedQty: l.pickedQty,
    }));
  }
  let ls = PICK_POOL.slice(0, Math.max(1, pl.items || 1)).map((l) => ({ ...l }));
  ls = ls.sort((a, b) => (a.bin > b.bin ? 1 : -1));
  return ls.map((l, i) => {
    const picked = pl.pct >= 100 || (pl.pct > 0 && i < Math.floor(ls.length * pl.pct / 100));
    const partial = pl.errors && i === ls.length - 1 && l.qty > 1;
    return { ...l, picked: picked && !partial, pickedQty: partial ? l.qty - 1 : (picked ? l.qty : 0), partial };
  });
});
const doneCount = computed(() => lines.value.filter((l) => l.picked).length);
const detailOrders = computed(() => new Set(lines.value.map((l) => l.so)).size);
const detailUnits = computed(() => lines.value.reduce((a, l) => a + l.qty, 0));
const detailAisles = computed(() => new Set(lines.value.map((l) => aisle(l.bin))).size);
// Time is driven by physical stops (walking) + units grabbed, not raw lines —
// a 146-line mono list is one stop, not 146 walks.
const estTime = computed(() => Math.round(walkStops.value.length * 1.6 + detailUnits.value * 0.12 + detailAisles.value * 1.2));

const isNewAisle = (i) => i === 0 || aisle(lines.value[i].bin) !== aisle(lines.value[i - 1].bin);

const bySku = computed(() => {
  const m = {};
  lines.value.forEach((l) => { (m[l.sku] = m[l.sku] || { ...l, qtyTot: 0, orders: [] }); m[l.sku].qtyTot += l.qty; m[l.sku].orders.push(l.so); });
  return Object.values(m).sort((a, b) => (a.bin > b.bin ? 1 : -1));
});
const byOrder = computed(() => {
  const m = {};
  lines.value.forEach((l) => { (m[l.so] = m[l.so] || { so: l.so, customer: l.customer, items: [] }); m[l.so].items.push(l); });
  return Object.values(m);
});

// A walk STOP is one physical grab: same product at the same bin, however many
// orders it serves. Collapsing lines this way turns a 30-order mono pick list
// (30 identical rows) into a single "grab 30× here → 30 orders" stop — which is
// how the picker actually works it. Mixed lists degrade to one stop per line.
const walkStops = computed(() => {
  const m = new Map();
  lines.value.forEach((l) => {
    const key = `${l.bin}|||${l.sku}`;
    let s = m.get(key);
    if (!s) {
      s = { key, bin: l.bin, sku: l.sku, realSku: l.realSku, name: l.name,
            grp: l.grp, uom: l.uom, serial: l.serial, batch: l.batch, image: l.image,
            qty: 0, pickedQty: 0, orders: [] };
      m.set(key, s);
    }
    s.qty += l.qty || 0;
    s.pickedQty += l.pickedQty || 0;
    if (l.so) s.orders.push({ so: l.so, customer: l.customer, qty: l.qty || 1 });
  });
  return [...m.values()].map((s) => ({
    ...s,
    picked: s.qty > 0 && s.pickedQty >= s.qty,
    partial: s.pickedQty > 0 && s.pickedQty < s.qty,
  }));
});
const isNewAisleStop = (i) =>
  i === 0 || aisle(walkStops.value[i].bin) !== aisle(walkStops.value[i - 1].bin);
// ERPNext's root item group ("All Item Groups") means the item is simply
// uncategorised — showing it as a chip is noise, so drop it (and blanks).
const grpClean = (g) => (g && g !== "All Item Groups" ? g : "");
// Hide a broken product image (dead Shopify CDN url) instead of a broken icon.
function onImgError(e) { if (e && e.target) e.target.style.display = "none"; }

const lifecycleSteps = [
  { label: "Created", icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>` },
  { label: "Assigned", icon: usersIcon(15) },
  { label: "Picking", icon: boxIcon(15) },
  { label: "Completed", icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>` },
  { label: "To packing", icon: tagIcon(15) },
];
const lifecycleTimes = computed(() => {
  const lv = liveDetail.value;
  if (lv) {
    const c = (lv.created || "").slice(5) || "—";
    const shipped = lv.status === "shipped" || lv.status === "partial";
    return [c, c, shipped ? (lv.updated || "").slice(5) || "—" : "—"];
  }
  return ["08:58", "09:01", "09:08", "09:25", "—"];
});
const lifecycleCur = computed(() => {
  const lv = liveDetail.value;
  if (lv) return lv.status === "shipped" || lv.status === "partial" ? 2 : lv.status === "draft" ? 0 : 1;
  const pl = detail.value;
  if (!pl) return 0;
  return pl.pct >= 100 ? 3 : pl.pct > 0 ? 2 : (pl.status === "open" ? 1 : 0);
});
const lifecycleShown = computed(() => liveDetail.value
  ? [{ label: t("pl.lcCreated"), icon: usersIcon(15) }, { label: t("pl.lcPicked"), icon: boxIcon(15) }, { label: t("pl.lcShipped"), icon: tagIcon(15) }]
  : lifecycleSteps);

function tagIcon(s) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" width="${s}" height="${s}"><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/></svg>`;
}

const statusPill = (pl) => (pl.pct >= 100 ? "text-emerald-700 bg-emerald-50 ring-emerald-200" : pl.pct > 0 ? "text-blue-700 bg-blue-50 ring-blue-200" : "text-amber-700 bg-amber-50 ring-amber-200");
const statusPillDot = (pl) => (pl.pct >= 100 ? "bg-emerald-500" : pl.pct > 0 ? "bg-blue-500" : "bg-amber-500");
const statusPillLabel = (pl) => liveDetail.value ? plStatusLabel(liveDetail.value.status) : (pl.pct >= 100 ? "Closed" : pl.pct > 0 ? "Picking" : "Pending");

const detailActivity = computed(() => {
  const pl = detail.value;
  if (!pl) return [];
  const isErr = !!pl.errors;
  return [
    { who: "Anass", act: "Pick list created", at: "08:58", on: true },
    { who: byId(pl.picker).short, act: "Assigned to " + byId(pl.picker).short, at: "09:01", on: true },
    { who: byId(pl.picker).short, act: "Picking started", at: "09:08", on: pl.pct > 0 },
    { who: byId(pl.picker).short, act: isErr ? "Short-pick reported" : "All items scanned", at: "09:25", on: pl.pct >= 100 || isErr, bad: isErr },
  ];
});
</script>
