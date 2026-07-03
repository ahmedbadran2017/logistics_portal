<template>
  <!-- Count detail full-page view -->
  <div v-if="openCount" class="p-5 sm:p-6 max-w-[1400px] mx-auto animate-fade-in">
    <button @click="openCount = null" class="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap">
      <Icon name="chevron-left" :size="15" />Cycle counting
    </button>

    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3">
          <span class="w-11 h-11 rounded-xl bg-[var(--accent-50)] text-[var(--accent-600)] flex items-center justify-center"><Icon name="boxes" :size="22" /></span>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h1 class="font-mono text-[17px] font-bold text-stone-900">{{ openCount.no }}</h1>
              <Badge :tone="openCount.cls === 'A' ? 'emerald' : openCount.cls === 'B' ? 'amber' : 'stone'">{{ openCount.cls }} class</Badge>
            </div>
            <div class="text-[12.5px] text-stone-600 mt-1 flex items-center gap-2">
              <Avatar :name="byId(openCount.owner).name" :size="20" />{{ byId(openCount.owner).short }} · {{ openCount.zone.replace(' - JM', '') }}
            </div>
          </div>
        </div>
      </div>
      <!-- stepper -->
      <div class="flex items-center mt-5">
        <template v-for="(s, i) in countStages" :key="s.k">
          <div class="flex flex-col items-center gap-1.5 flex-shrink-0" style="width: 110px">
            <span class="w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold" :class="i <= cStage ? 'bg-emerald-500 text-white' : 'bg-stone-100 text-stone-400'">
              <Icon v-if="i <= cStage" name="check" :size="14" /><template v-else>{{ i + 1 }}</template>
            </span>
            <span class="text-[11px] font-medium" :class="i <= cStage ? 'text-stone-900' : 'text-stone-400'">{{ s.l }}</span>
          </div>
          <div v-if="i < countStages.length - 1" class="flex-1 h-0.5 -mt-6" :class="i < cStage ? 'bg-emerald-300' : 'bg-stone-200'" />
        </template>
      </div>
      <div class="text-[11.5px] text-stone-500 mt-4 flex items-center gap-1.5 rounded-lg bg-stone-50 px-3 py-2">
        <Icon name="info" :size="13" class="text-stone-400 flex-shrink-0" />Scan each bin to compare counted qty against the system total; variances post as a Stock Reconciliation.
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
      <!-- bins checklist -->
      <Panel title="Bins" :sub="`${cDone}/${countBins.length}`">
        <template #right><Badge :tone="cDone >= countBins.length ? 'emerald' : 'cyan'" dot>{{ Math.round(cDone / countBins.length * 100) }}%</Badge></template>
        <div v-if="cStage < 2" class="p-4 border-b border-stone-100">
          <button @click="scanBin" :disabled="cDone >= countBins.length" class="w-full flex items-center gap-3 px-4 h-14 rounded-2xl ring-2 transition-all active:scale-[0.99]" :class="cDone >= countBins.length ? 'ring-emerald-300 bg-emerald-50/50' : 'ring-stone-300 bg-white hover:ring-stone-400'">
            <span class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" :class="cDone >= countBins.length ? 'bg-emerald-500 text-white' : 'bg-stone-900 text-white'"><Icon name="scan-barcode" :size="18" /></span>
            <span class="text-[14px] font-medium text-stone-600 flex-1 text-start">Scan next bin</span>
          </button>
        </div>
        <div class="divide-y divide-stone-100 max-h-[420px] overflow-y-auto">
          <div v-for="(b, i) in countBins" :key="i" class="grid grid-cols-[24px_1fr_auto_auto] items-center gap-3 px-4 py-2.5" :class="i < cDone ? '' : 'opacity-50'">
            <span class="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0" :class="i < cDone ? (b.off !== 0 ? 'bg-amber-500 text-white' : 'bg-emerald-500 text-white') : 'ring-1 ring-stone-300'">
              <Icon v-if="i < cDone && b.off !== 0" name="alert-circle" :size="11" /><Icon v-else-if="i < cDone" name="check" :size="11" />
            </span>
            <span class="font-mono text-[11.5px] font-semibold text-stone-900">{{ b.bin }}</span>
            <span class="text-[11px] text-stone-400 tabular-nums font-mono">Expected {{ b.expected }}</span>
            <template v-if="i < cDone">
              <Badge v-if="b.off !== 0" tone="amber" dot>Off {{ b.off > 0 ? '+' : '' }}{{ b.off }}</Badge>
              <Badge v-else tone="emerald" dot>Match</Badge>
            </template>
            <span v-else class="text-[11px] text-stone-300">—</span>
          </div>
        </div>
      </Panel>

      <!-- variances + actions -->
      <div class="space-y-4">
        <Panel title="Variances">
          <template #right><Badge v-if="cVarList.length > 0 && cStage >= 1" tone="amber" dot>{{ cVarList.length }}</Badge></template>
          <div v-if="cStage >= 1 && cVarList.length > 0" class="divide-y divide-stone-100">
            <div v-for="(b, i) in cVarList" :key="i" class="flex items-center gap-3 px-4 py-2.5">
              <span class="font-mono text-[11.5px] text-stone-700 flex-1">{{ b.bin }}</span>
              <span class="text-[11px] text-stone-400 font-mono">Exp {{ b.expected }}</span>
              <span class="text-[11px] text-stone-600 font-mono">Found {{ b.found }}</span>
              <Badge tone="rose" dot>{{ b.off > 0 ? '+' : '' }}{{ b.off }}</Badge>
            </div>
            <div class="px-4 py-2.5">
              <button @click="info('Recount queued', 'Bin flagged for second count')" class="w-full inline-flex items-center justify-center gap-1.5 h-8 px-3 rounded-lg ring-1 ring-stone-200 text-[12px] font-medium text-stone-700 hover:bg-stone-50"><Icon name="clock" :size="13" />Recount bin</button>
            </div>
          </div>
          <div v-else class="text-center text-[12px] text-stone-400 py-6">{{ cStage < 1 ? 'Start counting to see variances' : 'No variances ✓' }}</div>
        </Panel>

        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <button v-if="cStage === 0" @click="cStage = 1" class="w-full inline-flex items-center justify-center gap-2 h-11 rounded-xl bg-[var(--accent-600)] text-white text-[14px] font-semibold hover:opacity-90"><Icon name="scan-barcode" :size="18" />Start count</button>
          <button v-else-if="cStage === 1" @click="cStage = 2" :disabled="cDone < countBins.length" class="w-full inline-flex items-center justify-center gap-2 h-11 rounded-xl ring-1 ring-stone-200 text-stone-800 text-[14px] font-semibold hover:bg-stone-50 disabled:opacity-50"><Icon name="check-circle" :size="18" />To review</button>
          <button v-else-if="cStage === 2" @click="postCount" class="w-full inline-flex items-center justify-center gap-2 h-11 rounded-xl bg-emerald-500 text-white text-[14px] font-semibold hover:opacity-90"><Icon name="check-circle" :size="18" />Confirm &amp; post</button>
          <div v-else class="text-center text-[12.5px] text-emerald-600 font-medium py-2 flex items-center justify-center gap-1.5"><Icon name="check-circle" :size="16" />Posted as Stock Reconciliation</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Receiving detail full-page view -->
  <div v-else-if="openInbound" class="p-5 sm:p-6 max-w-[1400px] mx-auto animate-fade-in">
    <button @click="openInbound = null" class="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-stone-500 hover:text-stone-900 mb-4 whitespace-nowrap">
      <Icon name="chevron-left" :size="15" />Receiving
    </button>

    <div class="bg-white rounded-2xl ring-1 ring-stone-200/70 p-5 mb-4">
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3">
          <span class="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center"><Icon name="boxes" :size="22" /></span>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h1 class="font-mono text-[17px] font-bold text-stone-900">{{ openInbound.no }}</h1>
              <Badge tone="stone">Material Receipt</Badge>
            </div>
            <div class="text-[12.5px] text-stone-600 mt-1 flex items-center gap-2">
              <Avatar :name="byId(openInbound.owner).name" :size="20" />{{ openInbound.supplier }} · {{ openInbound.dock }} · {{ openInbound.eta }}
            </div>
          </div>
        </div>
      </div>
      <div class="flex items-center mt-5">
        <template v-for="(s, i) in recvStages" :key="s.k">
          <div class="flex flex-col items-center gap-1.5 flex-shrink-0" style="width: 110px">
            <span class="w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold" :class="i <= rStage ? 'bg-emerald-500 text-white' : 'bg-stone-100 text-stone-400'">
              <Icon v-if="i <= rStage" name="check" :size="14" /><template v-else>{{ i + 1 }}</template>
            </span>
            <span class="text-[11px] font-medium" :class="i <= rStage ? 'text-stone-900' : 'text-stone-400'">{{ s.l }}</span>
          </div>
          <div v-if="i < recvStages.length - 1" class="flex-1 h-0.5 -mt-6" :class="i < rStage ? 'bg-emerald-300' : 'bg-stone-200'" />
        </template>
      </div>
      <div class="text-[11.5px] text-stone-500 mt-4 flex items-center gap-1.5 rounded-lg bg-stone-50 px-3 py-2">
        <Icon name="info" :size="13" class="text-stone-400 flex-shrink-0" />Verify each received line against the ASN, then scan to put away to the suggested bin.
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
      <Panel title="Verify &amp; put away" :sub="`${openInbound.items} SKUs · ${openInbound.units} units`">
        <template #right><Badge v-if="rStage >= 2" :tone="rDone >= recvLines.length ? 'emerald' : 'cyan'" dot>{{ rDone }}/{{ recvLines.length }}</Badge></template>
        <div v-if="rStage >= 2 && rStage < 3" class="p-4 border-b border-stone-100">
          <button @click="scanRecv" class="w-full flex items-center gap-3 px-4 h-14 rounded-2xl ring-2 ring-stone-300 bg-white hover:ring-stone-400 transition-all active:scale-[0.99]">
            <span class="w-10 h-10 rounded-xl bg-stone-900 text-white flex items-center justify-center flex-shrink-0"><Icon name="scan-barcode" :size="18" /></span>
            <span class="text-[14px] font-medium text-stone-600 flex-1 text-start">Scan item to put away</span>
          </button>
        </div>
        <div class="divide-y divide-stone-100">
          <div v-for="(l, i) in recvLines" :key="i" class="grid grid-cols-[1fr_auto_auto_auto] items-center gap-3 px-4 py-2.5">
            <div class="min-w-0">
              <div class="text-[12.5px] font-medium text-stone-900 truncate">{{ l.name }}</div>
              <div class="font-mono text-[10.5px] text-stone-400">{{ l.sku }}</div>
            </div>
            <span class="text-[11px] text-stone-500 tabular-nums font-mono">Exp {{ l.expected }}</span>
            <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stone-900 text-white text-[10.5px] font-bold font-mono"><Icon name="map-pin" :size="9" />{{ l.bin }}</span>
            <template v-if="rStage >= 2">
              <Badge v-if="i < rDone" tone="emerald" dot>Put away</Badge>
              <span v-else class="text-[11px] text-stone-300">—</span>
            </template>
            <Badge v-else tone="cyan" dot>{{ l.received }}</Badge>
          </div>
        </div>
      </Panel>

      <div class="space-y-4">
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <button v-if="rStage === 0" @click="rStage = 1" class="w-full inline-flex items-center justify-center gap-2 h-11 rounded-xl bg-[var(--accent-600)] text-white text-[14px] font-semibold hover:opacity-90"><Icon name="check-circle" :size="18" />Start check-in</button>
          <button v-else-if="rStage === 1" @click="rStage = 2" class="w-full inline-flex items-center justify-center gap-2 h-11 rounded-xl ring-1 ring-stone-200 text-stone-800 text-[14px] font-semibold hover:bg-stone-50"><Icon name="boxes" :size="18" />To put away</button>
          <button v-else-if="rStage === 2" @click="postReceipt" :disabled="rDone < recvLines.length" class="w-full inline-flex items-center justify-center gap-2 h-11 rounded-xl bg-emerald-500 text-white text-[14px] font-semibold hover:opacity-90 disabled:opacity-50"><Icon name="check-circle" :size="18" />Confirm receipt</button>
          <div v-else class="text-center text-[12.5px] text-emerald-600 font-medium py-2 flex items-center justify-center gap-1.5"><Icon name="check-circle" :size="16" />Material Receipt posted</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Main warehouse page -->
  <div v-else class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <div class="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">Warehouse</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">Floor map, re-slotting, cycle counts &amp; receiving · {{ WAREHOUSE }}</p>
      </div>
    </div>

    <div class="flex items-center gap-1 border-b border-stone-200/70 overflow-x-auto">
      <button
        v-for="tb in tabs"
        :key="tb.k"
        @click="tab = tb.k"
        class="px-3 h-9 text-[13px] font-medium border-b-2 -mb-px whitespace-nowrap transition-colors"
        :class="tab === tb.k ? 'border-[var(--accent-600)] text-stone-900' : 'border-transparent text-stone-500 hover:text-stone-800'"
      >{{ tb.l }}</button>
    </div>

    <!-- MAP -->
    <div v-if="tab === 'map'" class="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
      <Panel title="Floor plan" sub="Capacity fill · click a zone">
        <template #right>
          <div class="flex items-center gap-2.5">
            <span v-for="lg in mapLegend" :key="lg.k" class="inline-flex items-center gap-1 text-[10.5px] text-stone-500"><span class="w-2.5 h-2.5 rounded-sm" :style="{ background: MOVE_COLOR[lg.k] }" />{{ lg.l }}</span>
          </div>
        </template>
        <div class="p-4 overflow-x-auto">
          <div class="relative mx-auto" :style="{ width: (MAP.cols * cell + (MAP.cols - 1) * gap) + 'px', height: (MAP.rows * cell + (MAP.rows - 1) * gap) + 'px' }">
            <button
              v-for="z in MAP.zones"
              :key="z.id"
              @click="sel = z.id"
              class="absolute rounded-xl ring-1 p-2.5 text-start transition-all overflow-hidden"
              :class="sel === z.id ? 'ring-2 ring-stone-900 z-10' : 'ring-stone-200 hover:ring-stone-400'"
              :style="zoneStyle(z)"
            >
              <div class="flex items-center justify-between">
                <span class="text-[12.5px] font-bold text-stone-900">{{ z.short }}</span>
                <span class="w-2 h-2 rounded-full" :style="{ background: MOVE_COLOR[z.move] }" />
              </div>
              <div class="text-[10.5px] text-stone-600 mt-0.5">{{ z.skus }} SKUs</div>
              <div class="absolute bottom-2 start-2.5 end-2.5">
                <div class="flex items-center justify-between text-[10px] text-stone-600 mb-0.5"><span class="tabular-nums">{{ Math.round(z.units / z.cap * 100) }}%</span><span class="font-mono">{{ z.aisles.join(' ') }}</span></div>
                <div class="h-1.5 rounded-full bg-white/60 overflow-hidden"><div class="h-full rounded-full" :style="{ width: (z.units / z.cap * 100) + '%', background: MOVE_COLOR[z.move] }" /></div>
              </div>
            </button>
          </div>
        </div>
      </Panel>

      <div class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <Kpi icon="boxes" tone="stone" label="SKUs" :value="totSku" />
          <Kpi icon="package" tone="violet" label="Units" :value="fmtMAD(totUnits)" />
        </div>
        <Panel v-if="selZone" :title="selZone.short" :sub="selZone.id">
          <div class="p-4 space-y-3">
            <div class="flex items-center gap-2"><Badge :tone="MOVE_TONE[selZone.move]" dot>{{ MOVE_LABEL[selZone.move] }} velocity</Badge></div>
            <div class="grid grid-cols-2 gap-2">
              <WhStat label="SKUs" :value="selZone.skus" />
              <WhStat label="Units" :value="selZone.units" />
              <WhStat label="Fill" :value="Math.round(selZone.units / selZone.cap * 100) + '%'" />
              <WhStat label="Picks 7d" :value="selZone.picks7d" />
            </div>
            <div class="flex items-center gap-2 pt-1"><span class="text-[11px] text-stone-500">Owner</span><Avatar :name="byId(selZone.owner).name" :size="22" /><span class="text-[12px] font-medium text-stone-800">{{ byId(selZone.owner).short }}</span></div>
            <div class="text-[11px] text-stone-500">Aisles <span class="font-mono text-stone-700">{{ selZone.aisles.join(' · ') }}</span></div>
          </div>
        </Panel>
        <Panel v-else title="Density">
          <div class="p-3 space-y-1.5">
            <button v-for="z in MAP.zones" :key="z.id" @click="sel = z.id" class="w-full flex items-center gap-2.5 px-1.5 py-1.5 rounded-lg hover:bg-stone-50 text-start">
              <span class="w-2.5 h-2.5 rounded-sm flex-shrink-0" :style="{ background: MOVE_COLOR[z.move] }" />
              <span class="text-[12px] text-stone-700 flex-1 truncate">{{ z.short }}</span>
              <div class="w-[70px] h-1.5 rounded-full bg-stone-100 overflow-hidden"><div class="h-full rounded-full" :style="{ width: (z.units / z.cap * 100) + '%', background: MOVE_COLOR[z.move] }" /></div>
              <span class="text-[11px] text-stone-500 tabular-nums w-[34px] text-end">{{ Math.round(z.units / z.cap * 100) }}%</span>
            </button>
          </div>
        </Panel>
      </div>
    </div>

    <!-- RESLOT -->
    <div v-else-if="tab === 'reslot'">
      <div class="rounded-xl bg-[var(--accent-50)]/50 ring-1 ring-[var(--accent-200)]/50 px-4 py-3 mb-4 flex items-center gap-3">
        <Icon name="zap" :size="18" class="text-[var(--accent-600)] flex-shrink-0" />
        <div class="text-[12.5px] text-stone-700 flex-1"><span class="font-semibold">{{ reslotRows.length }} suggested moves</span> — fast movers in slow slots &amp; dead stock in prime bins.</div>
        <button @click="success('Sent to Pick Autopilot', `${reslotRows.length} moves queued`)" class="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg ring-1 ring-stone-200 text-[12px] font-medium text-stone-700 hover:bg-stone-50"><Icon name="zap" :size="14" />Tie to Autopilot</button>
      </div>
      <div class="space-y-2.5">
        <div v-for="r in reslotRows" :key="r.sku" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center justify-between gap-3 flex-wrap">
            <div class="min-w-0">
              <div class="text-[13px] font-medium text-stone-900">{{ r.name }}</div>
              <div class="font-mono text-[10.5px] text-stone-400">{{ r.sku }} · {{ r.picks7d }} picks 7d</div>
            </div>
            <div class="flex items-center gap-2">
              <Badge tone="amber">{{ r.gain }}</Badge>
              <button v-if="moving[r.sku] === undefined" @click="startMove(r.sku)" class="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-[var(--accent-600)] text-white text-[12px] font-medium hover:opacity-90"><Icon name="arrow-right" :size="14" />Apply move</button>
            </div>
          </div>
          <div v-if="moving[r.sku] !== undefined" class="grid grid-cols-2 gap-2 mt-3">
            <button @click="moving[r.sku] < 1 && stepMove(r.sku)" class="flex items-center gap-2 px-3 h-12 rounded-xl ring-2 transition-all" :class="moving[r.sku] >= 1 ? 'ring-emerald-300 bg-emerald-50/50' : 'ring-stone-300 bg-white hover:ring-stone-400'">
              <span class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" :class="moving[r.sku] >= 1 ? 'bg-emerald-500 text-white' : 'bg-stone-900 text-white'"><Icon v-if="moving[r.sku] >= 1" name="check" :size="15" /><Icon v-else name="scan-barcode" :size="14" /></span>
              <div class="text-start"><div class="text-[11px] text-stone-500">Scan source</div><div class="font-mono text-[11px] font-medium text-stone-800">{{ r.fromBin }}</div></div>
            </button>
            <button @click="moving[r.sku] >= 1 && stepMove(r.sku)" :disabled="moving[r.sku] < 1" class="flex items-center gap-2 px-3 h-12 rounded-xl ring-2 transition-all" :class="moving[r.sku] >= 2 ? 'ring-emerald-300 bg-emerald-50/50' : moving[r.sku] < 1 ? 'ring-stone-200 bg-stone-50 opacity-50' : 'ring-stone-300 bg-white hover:ring-stone-400'">
              <span class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" :class="moving[r.sku] >= 2 ? 'bg-emerald-500 text-white' : 'bg-emerald-500/80 text-white'"><Icon name="map-pin" :size="14" /></span>
              <div class="text-start"><div class="text-[11px] text-stone-500">Scan destination</div><div class="font-mono text-[11px] font-medium text-stone-800">{{ r.toBin }}</div></div>
            </button>
          </div>
          <div v-else class="flex items-center gap-3 mt-3">
            <div class="flex-1 rounded-lg bg-stone-50 ring-1 ring-stone-200/60 px-3 py-2"><div class="text-[10px] text-stone-400 uppercase tracking-wide">From</div><div class="text-[12px] font-medium text-stone-800">{{ r.from.replace(' - JM', '') }}</div><div class="font-mono text-[10.5px] text-stone-500">{{ r.fromBin }}</div></div>
            <Icon name="arrow-right" :size="16" class="text-stone-400 flex-shrink-0" />
            <div class="flex-1 rounded-lg bg-emerald-50 ring-1 ring-emerald-200/60 px-3 py-2"><div class="text-[10px] text-emerald-600 uppercase tracking-wide">To</div><div class="text-[12px] font-medium text-stone-800">{{ r.to.replace(' - JM', '') }}</div><div class="font-mono text-[10.5px] text-stone-500">{{ r.toBin }}</div></div>
          </div>
          <div class="text-[11px] text-stone-500 mt-2 flex items-center gap-1.5"><Icon name="info" :size="11" />{{ r.reason }}</div>
        </div>
        <div v-if="reslotRows.length === 0" class="text-center text-[12.5px] text-emerald-600 py-12 flex items-center justify-center gap-1.5"><Icon name="check-circle" :size="16" />All slots optimized</div>
      </div>
    </div>

    <!-- SMART -->
    <div v-else-if="tab === 'smart'" class="space-y-4">
      <div class="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-4">
        <Panel title="Reorder alerts" sub="Days-of-cover forecast">
          <template #right><Badge tone="rose" dot>{{ criticalReorder }} cover now</Badge></template>
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead><tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
                <th class="text-start px-4 py-2.5">SKU</th><th class="text-end px-4 py-2.5">On hand</th><th class="text-end px-4 py-2.5 hidden sm:table-cell">Demand</th><th class="text-start px-4 py-2.5 w-[120px]">Days cover</th><th class="px-4 py-2.5"></th>
              </tr></thead>
              <tbody class="divide-y divide-stone-100">
                <tr v-for="r in REORDER" :key="r.sku" :class="r.cover < 1 ? 'bg-rose-50/30' : ''">
                  <td class="px-4 py-2.5">
                    <div class="flex items-center gap-1.5">
                      <span class="text-[9px] font-bold w-4 h-4 rounded flex items-center justify-center" :class="r.cls === 'A' ? 'bg-emerald-100 text-emerald-700' : r.cls === 'B' ? 'bg-amber-100 text-amber-700' : 'bg-stone-100 text-stone-500'">{{ r.cls }}</span>
                      <div><div class="text-[12px] font-medium text-stone-900 truncate max-w-[150px]">{{ r.name }}</div><div class="font-mono text-[10px] text-stone-400">{{ r.sku }}</div></div>
                    </div>
                  </td>
                  <td class="px-4 py-2.5 text-end text-[12.5px] font-semibold tabular-nums font-mono"><span :class="r.cover < 1 ? 'text-rose-600' : 'text-stone-900'">{{ r.onHand }}</span></td>
                  <td class="px-4 py-2.5 text-end text-[12px] text-stone-500 tabular-nums font-mono hidden sm:table-cell">{{ r.daily }}/d</td>
                  <td class="px-4 py-2.5">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden"><div class="h-full rounded-full" :style="{ width: Math.max(4, Math.min(1, r.cover / 7) * 100) + '%', background: r.cover < 1 ? '#ef4444' : r.cover < 3 ? '#f59e0b' : '#10b981' }" /></div>
                      <span class="text-[11px] tabular-nums w-[34px]" :class="r.cover < 1 ? 'text-rose-600 font-medium' : 'text-stone-500'">{{ r.cover === 0 ? '0d' : r.cover + 'd' }}</span>
                    </div>
                  </td>
                  <td class="px-4 py-2.5 text-end">
                    <button v-if="r.cover < 1" @click="success('Material Request drafted', `${r.sku} ×${r.reorder}`)" class="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg ring-1 ring-stone-200 text-[11px] font-medium text-stone-700 hover:bg-stone-50"><Icon name="scan-barcode" :size="12" />PO</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="ABC analysis" sub="By pick velocity">
          <div class="p-4">
            <div class="flex h-3 rounded-full overflow-hidden mb-4">
              <div v-for="a in ABC" :key="a.cls" :style="{ width: a.share + '%', background: a.color }" />
            </div>
            <div class="space-y-2.5">
              <div v-for="a in ABC" :key="a.cls" class="flex items-center gap-3">
                <span class="w-6 h-6 rounded-lg flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0" :style="{ background: a.color }">{{ a.cls }}</span>
                <div class="min-w-0 flex-1"><div class="text-[12px] font-medium text-stone-900">{{ a.skus }} SKUs · {{ a.share }}% of picks</div><div class="text-[11px] text-stone-500 truncate">{{ a.note }}</div></div>
              </div>
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Bin-to-bin transfer" sub="Scan source → destination">
        <div class="p-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
            <button @click="success('Source bin scanned')" class="flex items-center gap-3 px-4 h-12 rounded-xl ring-2 ring-stone-300 bg-white hover:ring-stone-400 transition-all"><span class="w-8 h-8 rounded-lg bg-stone-900 text-white flex items-center justify-center flex-shrink-0"><Icon name="scan-barcode" :size="15" /></span><span class="text-[13px] font-medium text-stone-600">Scan source bin</span></button>
            <button @click="success('Destination scanned', 'Transfer logged')" class="flex items-center gap-3 px-4 h-12 rounded-xl ring-2 ring-stone-300 bg-white hover:ring-stone-400 transition-all"><span class="w-8 h-8 rounded-lg bg-emerald-500 text-white flex items-center justify-center flex-shrink-0"><Icon name="map-pin" :size="15" /></span><span class="text-[13px] font-medium text-stone-600">Scan destination bin</span></button>
          </div>
          <div class="divide-y divide-stone-100 -mx-4">
            <div v-for="tr in BIN_TRANSFERS" :key="tr.id" class="flex items-center gap-3 px-4 py-2.5">
              <span class="font-mono text-[11.5px] font-semibold text-stone-900 w-[60px]">{{ tr.id }}</span>
              <span class="font-mono text-[11px] text-stone-600 flex-1 truncate">{{ tr.sku }} · {{ tr.from.replace(' - JM', '') }} → {{ tr.to }}</span>
              <span class="text-[12px] font-semibold text-stone-800 tabular-nums font-mono">×{{ tr.qty }}</span>
              <Badge :tone="tr.status === 'done' ? 'emerald' : 'cyan'" dot>{{ tr.status === 'done' ? 'Done' : 'In progress' }}</Badge>
            </div>
          </div>
        </div>
      </Panel>
    </div>

    <!-- COUNT -->
    <div v-else-if="tab === 'count'" class="space-y-4">
      <div class="rounded-2xl ring-1 ring-[var(--accent-300)]/50 bg-gradient-to-br from-[var(--accent-50)]/50 to-white p-4">
        <div class="flex items-center justify-between gap-3 flex-wrap mb-3">
          <div class="flex items-center gap-2.5">
            <span class="w-9 h-9 rounded-xl bg-gradient-to-br from-[var(--accent-500)] to-[var(--accent-700)] text-white flex items-center justify-center"><Icon name="zap" :size="18" /></span>
            <div><div class="text-[14.5px] font-semibold text-stone-900">Smart count planner</div><div class="text-[11.5px] text-stone-500">ABC-driven auto plan</div></div>
          </div>
          <button @click="info('Today\'s count plan generated', `${COUNT_PLAN.today.bins} bins queued`)" class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg bg-[var(--accent-600)] text-white text-[13px] font-medium hover:opacity-90"><Icon name="scan-barcode" :size="16" />Start today</button>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-[180px_1fr] gap-4">
          <div class="flex items-center gap-3 bg-white rounded-xl ring-1 ring-stone-200/60 p-3">
            <svg width="74" height="74" class="-rotate-90 flex-shrink-0"><circle cx="37" cy="37" r="30" fill="none" stroke="#f0eeec" stroke-width="7" /><circle cx="37" cy="37" r="30" fill="none" stroke="#10b981" stroke-width="7" :stroke-dasharray="ringCirc" :stroke-dashoffset="ringCirc * (1 - COUNT_PLAN.coverage / 100)" stroke-linecap="round" /></svg>
            <div><div class="text-[20px] font-bold text-stone-900 tabular-nums leading-none">{{ COUNT_PLAN.coverage }}%</div><div class="text-[11px] text-stone-500 mt-1">Coverage</div><div class="text-[10px] text-stone-400 mt-0.5">{{ COUNT_PLAN.countedSkus }}/{{ COUNT_PLAN.totalSkus }} · {{ COUNT_PLAN.period }}</div></div>
          </div>
          <div class="space-y-3">
            <div class="flex items-center gap-3 rounded-xl bg-white ring-1 ring-stone-200/60 px-3 py-2.5">
              <Icon name="calendar" :size="16" class="text-[var(--accent-600)] flex-shrink-0" />
              <div class="flex-1 text-[12.5px] text-stone-700"><span class="font-semibold">Today:</span> {{ COUNT_PLAN.today.bins }} bins · {{ COUNT_PLAN.today.skus }} SKUs · ≈{{ COUNT_PLAN.today.mins }} min</div>
              <span class="text-[11px] text-stone-400 hidden sm:block">{{ COUNT_PLAN.today.zones.map(z => z.replace(' - JM', '')).join(', ') }}</span>
            </div>
            <div class="grid grid-cols-3 gap-2">
              <div v-for="c in COUNT_PLAN.cadence" :key="c.cls" class="rounded-xl bg-white ring-1 ring-stone-200/60 p-2.5">
                <div class="flex items-center gap-1.5"><span class="w-5 h-5 rounded text-[10px] font-bold text-white flex items-center justify-center" :style="{ background: c.color }">{{ c.cls }}</span><span class="text-[11px] font-medium text-stone-700">{{ c.every }}</span></div>
                <div class="text-[11px] text-stone-500 mt-1.5">{{ c.skus }} SKUs · <span class="text-amber-600 font-medium">{{ c.due }} due</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between">
        <span class="text-[13px] font-semibold text-stone-700">Cycle counting · Stock Reconciliations</span>
        <button @click="info('New count', 'Open the planner to schedule')" class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg ring-1 ring-stone-200 text-[13px] font-medium text-stone-700 hover:bg-stone-50"><Icon name="plus" :size="16" />New count</button>
      </div>

      <Panel>
        <div class="divide-y divide-stone-100">
          <button v-for="c in CYCLE_COUNTS" :key="c.no" @click="startCount(c)" class="w-full grid grid-cols-[170px_1fr_auto_auto] items-center gap-3 px-4 py-3 text-start transition-colors hover:bg-stone-50">
            <span class="font-mono text-[11.5px] font-semibold text-stone-900">{{ c.no }}</span>
            <div class="min-w-0">
              <div class="text-[12.5px] text-stone-800 truncate flex items-center gap-1.5"><span class="text-[9px] font-bold w-4 h-4 rounded flex items-center justify-center" :class="c.cls === 'A' ? 'bg-emerald-100 text-emerald-700' : c.cls === 'B' ? 'bg-amber-100 text-amber-700' : 'bg-stone-100 text-stone-500'">{{ c.cls }}</span>{{ c.zone.replace(' - JM', '') }}</div>
              <div class="text-[11px] text-stone-500">{{ c.counted }}/{{ c.bins }} bins{{ c.variances > 0 ? ` · ${c.variances} var` : '' }}</div>
            </div>
            <Avatar :name="byId(c.owner).name" :size="22" />
            <Badge :tone="SC_TONE[c.status]" dot>{{ c.status }}</Badge>
          </button>
        </div>
      </Panel>
    </div>

    <!-- RECEIVING -->
    <div v-else-if="tab === 'receiving'">
      <div class="flex justify-end mb-3"><button @click="info('Check-in', 'Scan an inbound ASN to begin')" class="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-lg bg-[var(--accent-600)] text-white text-[13px] font-medium hover:opacity-90"><Icon name="plus" :size="16" />Check in</button></div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <div v-for="r in INBOUND" :key="r.no" @click="startInbound(r)" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 cursor-pointer hover:ring-stone-300 hover:shadow-[0_8px_24px_-8px_rgba(0,0,0,0.1)] transition-all">
          <div class="flex items-center justify-between"><span class="font-mono text-[12px] font-semibold text-stone-900">{{ r.no }}</span><Badge :tone="IN_TONE[r.status]" dot>{{ r.status }}</Badge></div>
          <div class="text-[13px] font-medium text-stone-900 mt-2">{{ r.supplier }}</div>
          <div class="flex items-center gap-3 mt-2 text-[11.5px] text-stone-500"><span class="tabular-nums">{{ r.items }} SKUs</span><span class="text-stone-300">·</span><span class="tabular-nums">{{ r.units }} units</span></div>
          <div class="flex items-center justify-between mt-3 pt-3 border-t border-stone-100">
            <div class="flex items-center gap-1.5 text-[11.5px] text-stone-600"><Icon name="clock" :size="12" class="text-stone-400" />{{ r.eta }} · {{ r.dock }}</div>
            <Avatar :name="byId(r.owner).name" :size="20" />
          </div>
          <button v-if="r.status !== 'done'" @click.stop="startInbound(r)" class="w-full mt-3 inline-flex items-center justify-center gap-1.5 h-8 px-3 rounded-lg ring-1 ring-stone-200 text-[12px] font-medium text-stone-700 hover:bg-stone-50"><Icon name="boxes" :size="14" />Put away</button>
        </div>
      </div>
    </div>

    <!-- ZONES -->
    <div v-else-if="tab === 'zones'">
      <Panel>
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead><tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th class="text-start px-4 py-2.5">Zone</th><th class="text-start px-4 py-2.5">Velocity</th><th class="text-start px-4 py-2.5">Owner</th>
              <th class="text-end px-4 py-2.5 hidden sm:table-cell">SKUs</th><th class="text-end px-4 py-2.5">Fill</th><th class="px-4 py-2.5"></th>
            </tr></thead>
            <tbody class="divide-y divide-stone-100">
              <tr v-for="z in MAP.zones" :key="z.id" class="hover:bg-stone-50">
                <td class="px-4 py-2.5"><div class="text-[12.5px] font-medium text-stone-900">{{ z.short }}</div><div class="font-mono text-[10.5px] text-stone-400">{{ z.aisles.join(' · ') }}</div></td>
                <td class="px-4 py-2.5"><Badge :tone="MOVE_TONE[z.move]" dot>{{ MOVE_LABEL[z.move] }}</Badge></td>
                <td class="px-4 py-2.5"><div class="flex items-center gap-1.5"><Avatar :name="byId(z.owner).name" :size="22" /><span class="text-[12px] text-stone-700">{{ byId(z.owner).short }}</span></div></td>
                <td class="px-4 py-2.5 text-end text-[12.5px] text-stone-700 tabular-nums hidden sm:table-cell">{{ z.skus }}</td>
                <td class="px-4 py-2.5 text-end"><div class="flex items-center gap-2 justify-end"><div class="w-[60px] h-1.5 rounded-full bg-stone-100 overflow-hidden"><div class="h-full rounded-full" :style="{ width: (z.units / z.cap * 100) + '%', background: MOVE_COLOR[z.move] }" /></div><span class="text-[11.5px] text-stone-500 tabular-nums w-[30px]">{{ Math.round(z.units / z.cap * 100) }}%</span></div></td>
                <td class="px-4 py-2.5 text-end"><button @click="info('Reassign owner', z.short)" class="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg ring-1 ring-stone-200 text-[11px] font-medium text-stone-700 hover:bg-stone-50"><Icon name="users" :size="12" />Assign owner</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, h, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import { byId, fmtMAD, WAREHOUSE, getInitial } from "@/lib/handoffData.js";
import { api, liveOr } from "@/lib/resource";

const { success, info } = useToast();

// ── Data not exported from handoffData.js — inlined from data.jsx ────────
const DEMO_MAP = {
  cols: 6, rows: 4,
  zones: [
    { id: "FAST ZONE - JM",      short: "FAST",      col: 0, row: 0, w: 2, h: 2, skus: 142, units: 4820, cap: 5400, move: "fast",    owner: "marouane", aisles: ["J7", "J8"],  picks7d: 980 },
    { id: "Cosmetic zone - JM",  short: "Cosmetic",  col: 2, row: 0, w: 2, h: 1, skus: 64,  units: 1180, cap: 2000, move: "fast",    owner: "asmaa",    aisles: ["I4", "H13"], picks7d: 540 },
    { id: "MU Zone - JM",        short: "Makeup",    col: 4, row: 0, w: 2, h: 1, skus: 51,  units: 1390, cap: 1800, move: "medium",  owner: "asmaa",    aisles: ["H13", "H14"], picks7d: 360 },
    { id: "Accessory Zone - JM", short: "Accessory", col: 2, row: 1, w: 2, h: 1, skus: 38,  units: 980,  cap: 1500, move: "medium",  owner: "oussama",  aisles: ["H14", "I4"], picks7d: 290 },
    { id: "Textile Zone - JM",   short: "Textile",   col: 4, row: 1, w: 2, h: 1, skus: 44,  units: 1620, cap: 1700, move: "slow",    owner: "said",     aisles: ["F13", "G13"], picks7d: 110 },
    { id: "SLOW ZONE - JM",      short: "SLOW",      col: 0, row: 2, w: 3, h: 2, skus: 98,  units: 5210, cap: 5600, move: "slow",    owner: "saad",     aisles: ["F13", "F14"], picks7d: 130 },
    { id: "Stores - JM",         short: "Reserve",   col: 3, row: 2, w: 3, h: 2, skus: 703, units: 12400,cap: 16000,move: "reserve", owner: "reda",     aisles: ["Bulk"], picks7d: 0 },
  ],
};
const RESLOT = [
  { sku: "MCH100020", name: "Recharge huile lavande", from: "SLOW ZONE - JM",    fromBin: "F14B - JM", to: "FAST ZONE - JM",      toBin: "J7C - JM",  picks7d: 201, reason: "High velocity in slow zone", gain: "−18% walk" },
  { sku: "ACC11015",  name: "Miroir LED pliable",     from: "Textile Zone - JM", fromBin: "G13A - JM", to: "Accessory Zone - JM", toBin: "H14C - JM", picks7d: 154, reason: "Misclassified category",     gain: "−12% walk" },
  { sku: "TXT55088",  name: "Châle hiver laine",      from: "FAST ZONE - JM",    fromBin: "J8A - JM",  to: "SLOW ZONE - JM",      toBin: "F13C - JM", picks7d: 6,   reason: "Dead stock in prime slot",   gain: "Free fast slot" },
];
const CYCLE_COUNTS = [
  { no: "MAT-RECO-2026-00061", zone: "FAST ZONE - JM",     cls: "A", bins: 24, counted: 24, system: 482,  actual: 480, variances: 1, status: "review",    owner: "marouane" },
  { no: "MAT-RECO-2026-00060", zone: "Cosmetic zone - JM", cls: "A", bins: 14, counted: 6,  system: 188,  actual: 0,   variances: 0, status: "counting",  owner: "asmaa" },
  { no: "MAT-RECO-2026-00059", zone: "MU Zone - JM",       cls: "B", bins: 12, counted: 12, system: 139,  actual: 139, variances: 0, status: "done",      owner: "asmaa" },
  { no: "MAT-RECO-2026-00058", zone: "SLOW ZONE - JM",     cls: "C", bins: 22, counted: 0,  system: 2885, actual: 0,   variances: 0, status: "scheduled", owner: "saad" },
];
const COUNT_PLAN = {
  coverage: 78, period: "30d", countedSkus: 343, totalSkus: 441,
  cadence: [
    { cls: "A", every: "Weekly",    skus: 88,  due: 12, color: "#10b981" },
    { cls: "B", every: "Bi-weekly", skus: 142, due: 9,  color: "#f59e0b" },
    { cls: "C", every: "Monthly",   skus: 211, due: 7,  color: "#a8a29e" },
  ],
  today: { bins: 18, mins: 22, zones: ["FAST ZONE - JM", "Cosmetic zone - JM"], skus: 28 },
};
const INBOUND = [
  { no: "PR-2026-0418", supplier: "MCH Supplies", items: 12, units: 480, eta: "Today 15:00", status: "putaway",   owner: "reda",    dock: "Dock 2" },
  { no: "PR-2026-0417", supplier: "Cosmetica MA", items: 8,  units: 320, eta: "Arrived",     status: "checking",  owner: "oussama", dock: "Dock 1" },
  { no: "PR-2026-0415", supplier: "Textil Group", items: 5,  units: 140, eta: "Tomorrow",    status: "scheduled", owner: "said",    dock: "—" },
];
const ABC = [
  { cls: "A", share: 72, skus: 88,  color: "#10b981", note: "Top 20% SKUs · 72% of picks" },
  { cls: "B", share: 21, skus: 142, color: "#f59e0b", note: "Mid movers" },
  { cls: "C", share: 7,  skus: 211, color: "#a8a29e", note: "Long tail · review for clearance" },
];
const REORDER = [
  { sku: "CSM44021",  name: "Sérum éclat 30ml",         bin: "I4A - JM",  onHand: 0,  daily: 11, cover: 0,   reorder: 24, cls: "A" },
  { sku: "ACC11008",  name: "Trousse maquillage zip",   bin: "H14A - JM", onHand: 3,  daily: 7,  cover: 0.4, reorder: 20, cls: "A" },
  { sku: "MUZ22014",  name: "Palette ombres MU",        bin: "H13B - JM", onHand: 2,  daily: 4,  cover: 0.5, reorder: 18, cls: "B" },
  { sku: "TXT55012",  name: "Foulard soie imprimé",     bin: "F13C - JM", onHand: 7,  daily: 2,  cover: 3.5, reorder: 12, cls: "B" },
  { sku: "MCH100020", name: "Recharge huile lavande",   bin: "J7B - JM",  onHand: 58, daily: 29, cover: 2,   reorder: 25, cls: "A" },
];
const BIN_TRANSFERS = [
  { id: "BT-308", sku: "MCH100013", from: "Stores - JM", to: "J8C - JM", qty: 24, owner: "reda",    status: "done" },
  { id: "BT-307", sku: "CSM44021",  from: "Stores - JM", to: "I4A - JM", qty: 24, owner: "oussama", status: "inprogress" },
];

// ── Color / tone maps ───────────────────────────────────────────────────
const MOVE_COLOR = { fast: "#10b981", medium: "#f59e0b", slow: "#a8a29e", reserve: "#6366f1" };
const MOVE_TONE  = { fast: "emerald", medium: "amber", slow: "stone", reserve: "violet" };
const MOVE_LABEL = { fast: "Fast", medium: "Medium", slow: "Slow", reserve: "Reserve" };
const SC_TONE    = { scheduled: "stone", counting: "cyan", review: "amber", done: "emerald" };
const IN_TONE    = { scheduled: "stone", checking: "cyan", putaway: "amber", done: "emerald" };

// ── Tabs / map state ────────────────────────────────────────────────────
const tabs = [
  { k: "map", l: "Floor map" }, { k: "reslot", l: "Re-slotting" }, { k: "smart", l: "Smart inventory" },
  { k: "count", l: "Cycle counting" }, { k: "receiving", l: "Receiving" }, { k: "zones", l: "Zones" },
];
const tab = ref("map");
const mapLegend = [{ k: "fast", l: "Fast" }, { k: "slow", l: "Slow" }, { k: "reserve", l: "Reserve" }];
const cell = 96, gap = 8;
const sel = ref(null);

// Live-or-demo floor map. `inventory.zones` returns the RESTOCK shape
// ({ zone, bins, skus, low, out, blocking, fill }); we merge it onto the demo
// MAP zones by id, keeping layout/velocity/owner/aisles from demo and overwriting
// skus + fill (fill 0..1 → units via demo cap) and low/out counts.
const MAP = ref(DEMO_MAP);

onMounted(async () => {
  const live = await liveOr(null, () => api("inventory.zones"));
  if (Array.isArray(live) && live.length) {
    const byZone = Object.fromEntries(live.map((z) => [z.zone, z]));
    MAP.value = {
      ...DEMO_MAP,
      zones: DEMO_MAP.zones.map((z) => {
        const lz = byZone[z.id] || byZone[z.short];
        if (!lz) return z;
        const fill = typeof lz.fill === "number" ? lz.fill : z.units / z.cap;
        return {
          ...z,
          skus: lz.skus ?? z.skus,
          units: Math.round(fill * z.cap),
          low: lz.low ?? z.low,
          out: lz.out ?? z.out,
        };
      }),
    };
  }
});

const selZone = computed(() => MAP.value.zones.find((z) => z.id === sel.value) || null);
const totSku = computed(() => MAP.value.zones.reduce((a, z) => a + z.skus, 0));
const totUnits = computed(() => MAP.value.zones.reduce((a, z) => a + z.units, 0));
function zoneStyle(z) {
  const fill = z.units / z.cap;
  const col = MOVE_COLOR[z.move];
  return {
    left: z.col * (cell + gap) + "px", top: z.row * (cell + gap) + "px",
    width: (z.w * cell + (z.w - 1) * gap) + "px", height: (z.h * cell + (z.h - 1) * gap) + "px",
    background: `color-mix(in oklab, ${col} ${Math.round(fill * 55 + 8)}%, white)`,
  };
}

// ── Re-slotting ─────────────────────────────────────────────────────────
const reslotRows = ref(RESLOT.map((r) => ({ ...r })));
const moving = reactive({});
function startMove(sku) { moving[sku] = 0; }
function stepMove(sku) {
  const s = (moving[sku] || 0) + 1;
  moving[sku] = s;
  if (s >= 2) {
    setTimeout(() => {
      reslotRows.value = reslotRows.value.filter((r) => r.sku !== sku);
      delete moving[sku];
      success("Re-slot complete", "Material Transfer posted");
    }, 400);
  }
}

// ── Smart inventory derived ─────────────────────────────────────────────
const criticalReorder = computed(() => REORDER.filter((r) => r.cover < 1).length);
const ringCirc = 2 * Math.PI * 30;

// ── Cycle count detail ──────────────────────────────────────────────────
const openCount = ref(null);
const cStage = ref(0);
const cCounted = ref(0);
const countStages = [{ k: "scheduled", l: "Scheduled" }, { k: "counting", l: "Counting" }, { k: "review", l: "Review" }, { k: "posted", l: "Posted" }];
const countBins = computed(() => {
  const c = openCount.value;
  if (!c) return [];
  const aisle = MAP.value.zones.find((z) => z.id === c.zone)?.aisles?.[0] || "J8";
  return Array.from({ length: c.bins }).map((_, i) => {
    const exp = 8 + (i * 13) % 40;
    const off = (c.no.charCodeAt(6) + i) % 11 === 0 ? -2 : (i % 17 === 0 ? 1 : 0);
    return { bin: `${aisle}${String.fromCharCode(65 + (i % 6))}${i % 9} - JM`, expected: exp, found: exp + off, off };
  });
});
const cDone = computed(() => (cStage.value >= 2 ? countBins.value.length : cCounted.value));
const cVarList = computed(() => countBins.value.filter((b) => b.off !== 0));
function startCount(c) {
  openCount.value = c;
  cStage.value = c.status === "done" ? 3 : c.status === "review" ? 2 : c.status === "counting" ? 1 : 0;
  cCounted.value = cStage.value >= 2 ? c.bins : c.counted;
}
function scanBin() {
  const n = Math.min(countBins.value.length, cCounted.value + 1);
  cCounted.value = n;
  if (n >= countBins.value.length) cStage.value = 2;
}
function postCount() {
  cStage.value = 3;
  success(`${openCount.value.no} posted`, "Stock Reconciliation");
}

// ── Receiving detail ────────────────────────────────────────────────────
const openInbound = ref(null);
const rStage = ref(0);
const rDone = ref(0);
const recvStages = [{ k: "checkin", l: "Check-in" }, { k: "verify", l: "Verify" }, { k: "putaway", l: "Put away" }, { k: "done", l: "Done" }];
const recvNames = [
  ["MCH100013", "Diffuseur huile MCH", "J8C - JM"], ["CSM44021", "Sérum éclat 30ml", "I4A - JM"],
  ["ACC11008", "Trousse maquillage", "H14A - JM"], ["MUZ22014", "Palette ombres MU", "H13B - JM"],
  ["TXT55012", "Foulard soie", "G13C - JM"], ["ACC11015", "Miroir LED", "H14C - JM"],
];
const recvLines = computed(() => {
  const r = openInbound.value;
  if (!r) return [];
  return Array.from({ length: Math.min(r.items, 6) }).map((_, i) => {
    const [sku, nm, bin] = recvNames[i % recvNames.length];
    const exp = 20 + (i * 17) % 60;
    return { sku, name: nm, bin, expected: exp, received: exp };
  });
});
function startInbound(r) {
  openInbound.value = r;
  rStage.value = r.status === "putaway" ? 2 : r.status === "checking" ? 1 : 0;
  rDone.value = 0;
}
function scanRecv() {
  const n = Math.min(recvLines.value.length, rDone.value + 1);
  rDone.value = n;
  if (n >= recvLines.value.length) rStage.value = 3;
}
function postReceipt() {
  rStage.value = 3;
  success(`${openInbound.value.no} · Material Receipt posted`);
}

// ── Local presentational primitives (match handoff Tailwind) ────────────
const BADGE_TONE = {
  stone: "bg-stone-100 text-stone-600", emerald: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-700", rose: "bg-rose-100 text-rose-700",
  violet: "bg-violet-100 text-violet-700", cyan: "bg-cyan-100 text-cyan-700",
};
const KPI_TONE = { stone: "#a8a29e", violet: "#8b5cf6", amber: "#f59e0b", rose: "#f43f5e", emerald: "#10b981" };

const Badge = (props, { slots }) =>
  h("span", { class: `inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10.5px] font-medium whitespace-nowrap ${BADGE_TONE[props.tone] || BADGE_TONE.stone}` }, [
    props.dot ? h("span", { class: "w-1.5 h-1.5 rounded-full bg-current opacity-70" }) : null,
    slots.default?.(),
  ]);
Badge.props = ["tone", "dot"];

const Avatar = (props) =>
  h("span", {
    class: "inline-flex items-center justify-center rounded-full bg-stone-200 text-stone-600 font-semibold flex-shrink-0",
    style: { width: props.size + "px", height: props.size + "px", fontSize: props.size * 0.4 + "px" },
  }, getInitial(props.name));
Avatar.props = ["name", "size"];

const Panel = (props, { slots }) =>
  h("div", { class: "bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden" }, [
    (props.title || slots.right) ? h("div", { class: "flex items-center justify-between px-4 pt-4 pb-3 border-b border-stone-100" }, [
      h("div", {}, [
        props.title ? h("div", { class: "text-[13px] font-semibold text-stone-800" }, props.title) : null,
        props.sub ? h("div", { class: "text-[11.5px] text-stone-500" }, props.sub) : null,
      ]),
      slots.right ? h("div", {}, slots.right()) : null,
    ]) : null,
    slots.default?.(),
  ]);
Panel.props = ["title", "sub"];

const Kpi = (props) =>
  h("div", { class: "bg-white rounded-xl ring-1 ring-stone-200/70 p-4 relative overflow-hidden" }, [
    h("span", { class: "absolute inset-x-0 top-0 h-1", style: { background: KPI_TONE[props.tone] || KPI_TONE.stone } }),
    h("div", { class: "flex items-center justify-between mb-2" }, [
      h("span", { class: "text-[11px] font-medium uppercase tracking-wide text-stone-400" }, props.label),
      h(Icon, { name: props.icon, size: 15, class: "text-stone-400" }),
    ]),
    h("div", { class: "text-[22px] font-bold text-stone-900 tabular-nums leading-none" }, String(props.value)),
  ]);
Kpi.props = ["icon", "tone", "label", "value"];

const WhStat = (props) =>
  h("div", { class: "bg-stone-50 rounded-lg px-3 py-2" }, [
    h("div", { class: "text-[16px] font-semibold text-stone-900 tabular-nums leading-none" }, String(props.value)),
    h("div", { class: "text-[10.5px] text-stone-500 mt-1" }, props.label),
  ]);
WhStat.props = ["label", "value"];
</script>
