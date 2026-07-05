<template>
  <div class="max-w-[1240px] mx-auto px-6 py-6">
    <!-- Header -->
    <div class="flex items-start justify-between gap-3 mb-5 flex-wrap">
      <div>
        <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t("ret.title") }}</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ t("ret.subtitle").replace("{c}", CARRIER) }}</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center rounded-lg ring-1 ring-stone-200 bg-white p-0.5">
          <button
            v-for="d in [7, 30, 90]" :key="d"
            class="px-2.5 h-7 text-[12px] font-medium rounded-md transition-colors"
            :class="daysF === d ? 'bg-stone-900 text-white' : 'text-stone-500 hover:text-stone-800'"
            @click="daysF = d; load()"
          >{{ d }}d</button>
        </div>
        <button
          class="inline-flex items-center gap-1.5 px-3 h-9 text-[12.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300"
          :class="loading ? 'opacity-60 pointer-events-none' : ''"
          @click="load(true)"
        >
          <Icon name="refresh-cw" :size="15" :class="loading ? 'animate-spin' : ''" />{{ t("common.refresh") }}
        </button>
      </div>
    </div>

    <!-- KPI strip -->
    <div v-if="mode === 'loading'" class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
      <div v-for="n in 4" :key="n" class="bg-white/70 rounded-xl ring-1 ring-stone-200/60 p-4 animate-pulse">
        <div class="h-3 w-24 rounded bg-stone-100" />
        <div class="h-6 w-14 rounded bg-stone-100 mt-3" />
      </div>
    </div>
    <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
            <Icon name="rotate-ccw" :size="16" />
          </span>
          <span class="text-[11px] font-medium text-stone-500 uppercase tracking-wide">{{ t("ret.kAwaiting") }}</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums mt-2 leading-none">
          {{ kpis.awaiting ?? 0 }}
          <span class="text-[11.5px] font-mono font-medium text-stone-400">{{ fmtMAD(kpis.awaitingValue || 0) }} MAD</span>
        </div>
        <div class="text-[11px] text-stone-400 mt-1">{{ t("ret.kAwaitingSub") }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Icon name="check-circle" :size="16" />
          </span>
          <span class="text-[11px] font-medium text-stone-500 uppercase tracking-wide">{{ t("ret.kReceived") }}</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums mt-2 leading-none">{{ kpis.receivedOrders ?? 0 }}</div>
        <div class="text-[11px] text-stone-400 mt-1">{{ t("ret.kReceivedSub").replace("{n}", kpis.batches ?? 0) }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
            <Icon name="alert-triangle" :size="16" />
          </span>
          <span class="text-[11px] font-medium text-stone-500 uppercase tracking-wide">{{ t("ret.kMissing") }}</span>
        </div>
        <div class="text-[24px] font-semibold tabular-nums mt-2 leading-none" :class="(kpis.missingQty || 0) > 0 ? 'text-rose-600' : 'text-stone-900'">{{ kpis.missingQty ?? 0 }}</div>
        <div class="text-[11px] text-stone-400 mt-1">{{ t("ret.kMissingSub") }}</div>
      </div>
      <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2">
          <span class="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center">
            <Icon name="trending-up" :size="16" />
          </span>
          <span class="text-[11px] font-medium text-stone-500 uppercase tracking-wide">{{ t("ret.kAvgPct") }}</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums mt-2 leading-none">{{ kpis.avgPct ?? 0 }}%</div>
        <div class="text-[11px] text-stone-400 mt-1">{{ t("ret.kAvgPctSub") }}</div>
      </div>
    </div>

    <!-- Tabs + search -->
    <div class="flex items-center gap-2 mb-3 flex-wrap">
      <div class="inline-flex bg-stone-100/80 rounded-lg p-0.5">
        <button
          v-for="tb in [['awaiting', t('ret.tabAwaiting'), kpis.awaiting], ['batches', t('ret.tabBatches'), kpis.batches]]"
          :key="tb[0]"
          class="px-3 h-8 text-[12.5px] font-medium rounded-md transition-all inline-flex items-center gap-1.5"
          :class="tab === tb[0] ? 'bg-white text-stone-900 shadow-[0_1px_2px_rgba(0,0,0,0.06)]' : 'text-stone-500 hover:text-stone-800'"
          @click="setTab(tb[0])"
        >
          {{ tb[1] }}
          <span class="font-mono text-[10.5px] tabular-nums" :class="tab === tb[0] ? 'text-[var(--accent-700)]' : 'text-stone-400'">{{ tb[2] ?? 0 }}</span>
        </button>
      </div>
      <div class="relative flex-1 min-w-[200px] max-w-[320px]">
        <Icon name="search" :size="13" class="absolute start-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
        <input
          v-model="q"
          :placeholder="tab === 'awaiting' ? t('ret.searchAwaitingPh') : t('ret.searchBatchesPh')"
          class="w-full h-8 ps-8 pe-3 text-[12.5px] bg-white rounded-lg ring-1 ring-stone-200 focus:ring-stone-400 outline-none"
          @input="onSearch"
        />
      </div>
    </div>

    <!-- ══════════ AWAITING RETURN ══════════ -->
    <div v-if="tab === 'awaiting'" class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden mb-5">
      <div v-if="loading" class="divide-y divide-stone-100">
        <div v-for="n in 6" :key="n" class="px-4 py-3.5 flex items-center gap-4">
          <div class="h-3.5 w-24 rounded bg-stone-100 animate-pulse" />
          <div class="h-3.5 w-44 rounded bg-stone-100 animate-pulse" />
          <div class="h-3.5 w-20 rounded bg-stone-100 animate-pulse ms-auto" />
        </div>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[860px]">
          <thead>
            <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th class="text-start px-4 py-2.5">{{ t("ret.thOrder") }}</th>
              <th class="text-start px-4 py-2.5">{{ t("ret.thCustomer") }}</th>
              <th class="text-start px-4 py-2.5">{{ t("ret.thCity") }}</th>
              <th class="text-start px-4 py-2.5 hidden md:table-cell">{{ t("ret.thAwb") }}</th>
              <th class="text-start px-4 py-2.5 hidden lg:table-cell">{{ t("ret.thDn") }}</th>
              <th class="text-end px-4 py-2.5">{{ t("ret.thValue") }}</th>
              <th class="text-end px-4 py-2.5">{{ t("ret.thAge") }}</th>
              <th class="text-end px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr v-for="r in rows" :key="r.order" class="cursor-pointer hover:bg-stone-50 transition-colors group" @click="openOrder(r.order)">
              <td class="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900 whitespace-nowrap">{{ r.order }}</td>
              <td class="px-4 py-2.5">
                <div class="flex items-center gap-1.5">
                  <span class="text-[12.5px] text-stone-800 truncate max-w-[180px]">{{ r.customer }}</span>
                  <template v-if="r.phone">
                    <a :href="'tel:' + r.phone" @click.stop :title="r.phone"
                       class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-emerald-100 hover:text-emerald-700 flex items-center justify-center flex-shrink-0">
                      <Icon name="phone" :size="11" />
                    </a>
                    <a :href="waLink(r.phone)" target="_blank" @click.stop title="WhatsApp"
                       class="w-5 h-5 rounded-md bg-stone-100 text-stone-500 hover:bg-emerald-100 hover:text-emerald-700 flex items-center justify-center flex-shrink-0">
                      <Icon name="message-circle" :size="11" />
                    </a>
                  </template>
                </div>
              </td>
              <td class="px-4 py-2.5 text-[12px] text-stone-600 capitalize whitespace-nowrap">{{ r.city || "—" }}</td>
              <td class="px-4 py-2.5 hidden md:table-cell">
                <a v-if="r.awb" :href="'https://cathedis.ma/shipment/?track_number=' + r.awb" target="_blank" @click.stop
                   class="font-mono text-[11.5px] text-stone-500 hover:text-[var(--accent-700)]">{{ r.awb }}</a>
                <span v-else class="text-stone-300">—</span>
              </td>
              <td class="px-4 py-2.5 hidden lg:table-cell">
                <a v-if="r.dn" :href="'/app/delivery-note/' + encodeURIComponent(r.dn)" target="_blank" @click.stop
                   class="font-mono text-[11.5px] text-stone-500 hover:text-[var(--accent-700)]">{{ r.dn }}</a>
                <span v-else class="text-stone-300">—</span>
              </td>
              <td class="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums whitespace-nowrap">{{ fmtMAD(r.value) }}</td>
              <td class="px-4 py-2.5 text-end text-[11.5px] tabular-nums whitespace-nowrap"
                  :class="r.age > 14 ? 'text-rose-600 font-medium' : r.age > 7 ? 'text-amber-600' : 'text-stone-400'">
                {{ t("ret.dOld").replace("{n}", r.age) }}
              </td>
              <td class="px-4 py-2.5 text-end">
                <Icon name="chevron-right" :size="13" class="text-stone-300 group-hover:text-stone-500 flip-rtl inline" />
              </td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="8" class="text-center text-[12.5px] text-emerald-600 py-12">{{ t("ret.noAwaiting") }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PagerBar />
    </div>

    <!-- ══════════ RECEIVING BATCHES ══════════ -->
    <div v-else class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden mb-5">
      <div v-if="loading" class="divide-y divide-stone-100">
        <div v-for="n in 5" :key="n" class="px-4 py-3.5 flex items-center gap-4">
          <div class="h-3.5 w-32 rounded bg-stone-100 animate-pulse" />
          <div class="h-3.5 w-40 rounded bg-stone-100 animate-pulse" />
          <div class="h-3.5 w-16 rounded bg-stone-100 animate-pulse ms-auto" />
        </div>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[860px]">
          <thead>
            <tr class="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-stone-400 border-b border-stone-100">
              <th class="text-start px-4 py-2.5">{{ t("ret.thBatch") }}</th>
              <th class="text-start px-4 py-2.5">{{ t("ret.thDate") }}</th>
              <th class="text-start px-4 py-2.5">{{ t("ret.thReceiver") }}</th>
              <th class="text-end px-4 py-2.5">{{ t("ret.thOrders") }}</th>
              <th class="text-end px-4 py-2.5">{{ t("ret.thQty") }}</th>
              <th class="text-end px-4 py-2.5">{{ t("ret.thMissing") }}</th>
              <th class="text-start px-4 py-2.5 w-[130px]">{{ t("ret.thPct") }}</th>
              <th class="text-start px-4 py-2.5 hidden md:table-cell">{{ t("ret.thSr") }}</th>
              <th class="text-start px-4 py-2.5">{{ t("ret.thStatus") }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr v-for="b in rows" :key="b.no" class="cursor-pointer hover:bg-stone-50 transition-colors" @click="openBatch(b)">
              <td class="px-4 py-2.5 font-mono text-[12px] font-semibold text-stone-900 whitespace-nowrap">{{ b.no }}</td>
              <td class="px-4 py-2.5 text-[12px] text-stone-600 whitespace-nowrap tabular-nums">{{ b.date }}</td>
              <td class="px-4 py-2.5">
                <div class="flex items-center gap-1.5">
                  <span class="w-5 h-5 rounded-full bg-stone-200 text-stone-600 flex items-center justify-center text-[9px] font-bold">{{ ownerInitials(b.owner) }}</span>
                  <span class="text-[12px] text-stone-700">{{ ownerShort(b.owner) }}</span>
                </div>
              </td>
              <td class="px-4 py-2.5 text-end text-[12.5px] font-semibold text-stone-900 tabular-nums">{{ b.orders }}</td>
              <td class="px-4 py-2.5 text-end text-[12px] text-stone-600 tabular-nums whitespace-nowrap">{{ b.actual }}/{{ b.ordered }}</td>
              <td class="px-4 py-2.5 text-end text-[12.5px] font-semibold tabular-nums" :class="b.missing > 0 ? 'text-rose-600' : 'text-stone-300'">{{ b.missing || "—" }}</td>
              <td class="px-4 py-2.5">
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-1.5 rounded-full bg-stone-100 overflow-hidden">
                    <div class="h-full rounded-full" :class="b.pct >= 100 ? 'bg-emerald-500' : b.pct >= 90 ? 'bg-amber-500' : 'bg-rose-500'" :style="{ width: Math.min(100, b.pct) + '%' }" />
                  </div>
                  <span class="text-[10.5px] text-stone-400 tabular-nums w-[38px]">{{ b.pct }}%</span>
                </div>
              </td>
              <td class="px-4 py-2.5 hidden md:table-cell">
                <Icon v-if="b.srCreated" name="check-circle" :size="14" class="text-emerald-500" />
                <span v-else class="text-[11px] text-amber-600">—</span>
              </td>
              <td class="px-4 py-2.5">
                <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ring-1"
                      :class="b.status === 'Returned' ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-stone-100 text-stone-600 ring-stone-200'">
                  <span class="w-1.5 h-1.5 rounded-full" :class="b.status === 'Returned' ? 'bg-emerald-500' : 'bg-stone-400'" />
                  {{ b.status === 'Returned' ? t("ret.stReturned") : t("ret.stDraft") }}
                </span>
              </td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="9" class="text-center text-[12.5px] text-stone-400 py-12">{{ t("ret.noBatches") }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PagerBar />
    </div>

    <!-- Top missing SKUs -->
    <div v-if="(kpis.topMissing || []).length" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
      <div class="flex items-center gap-2 mb-4 text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">
        <Icon name="alert-triangle" :size="15" /> {{ t("ret.topMissing") }}
      </div>
      <div class="space-y-3">
        <div v-for="m in kpis.topMissing" :key="m.sku">
          <div class="flex items-center justify-between gap-3 text-[12px] mb-1">
            <span class="min-w-0 flex-1 truncate text-stone-700" :title="m.name">
              <span class="font-mono text-stone-500">{{ m.sku }}</span> · {{ m.name }}
            </span>
            <span class="tabular-nums font-semibold flex-shrink-0" :style="{ color: m.qty >= 3 ? '#e11d48' : '#d97706' }">{{ m.qty }}</span>
          </div>
          <div class="h-1.5 rounded-full bg-stone-100 overflow-hidden">
            <div class="h-full rounded-full" :style="{ width: (m.qty / missingMax * 100) + '%', background: m.qty >= 3 ? '#f43f5e' : '#f59e0b' }" />
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="mode === 'live'" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-6 text-center text-[12.5px] text-emerald-600">
      {{ t("ret.noMissing") }}
    </div>

    <!-- ══════════ BATCH DETAIL DRAWER ══════════ -->
    <transition name="lp-drawer">
      <div v-if="activeBatch" class="fixed inset-0 z-40" @keydown.esc="activeBatch = null">
        <div class="absolute inset-0 bg-stone-900/30" @click="activeBatch = null" />
        <aside class="absolute top-0 h-full w-full max-w-lg bg-stone-50 ring-1 ring-stone-200 shadow-2xl overflow-y-auto" style="inset-inline-end:0">
          <div class="p-5 border-b border-stone-200/70 flex items-center justify-between sticky top-0 bg-white z-10">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-mono text-[16px] font-bold text-stone-900">{{ activeBatch.no }}</span>
                <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1"
                      :class="activeBatch.status === 'Returned' ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-stone-100 text-stone-600 ring-stone-200'">
                  {{ activeBatch.status === 'Returned' ? t("ret.stReturned") : t("ret.stDraft") }}
                </span>
              </div>
              <div class="text-[12px] text-stone-500 mt-0.5">{{ t("ret.batch") }} · {{ activeBatch.date }} · {{ ownerShort(activeBatch.owner) }}</div>
            </div>
            <div class="flex items-center gap-1.5">
              <a :href="'/app/return-shipment/' + encodeURIComponent(activeBatch.no)" target="_blank"
                 class="inline-flex items-center gap-1 px-2.5 h-8 text-[11.5px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300">
                {{ t("ret.openErp") }}
              </a>
              <button class="w-8 h-8 rounded-lg flex items-center justify-center text-stone-500 hover:bg-stone-100" @click="activeBatch = null">
                <Icon name="x" :size="17" />
              </button>
            </div>
          </div>

          <div class="p-4 space-y-4">
            <!-- totals -->
            <div class="grid grid-cols-4 gap-2">
              <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
                <div class="text-[18px] font-semibold text-stone-900 tabular-nums leading-none">{{ activeBatch.orders }}</div>
                <div class="text-[10px] text-stone-500 mt-1.5">{{ t("ret.dOrders") }}</div>
              </div>
              <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
                <div class="text-[18px] font-semibold text-stone-900 tabular-nums leading-none">{{ activeBatch.actual }}</div>
                <div class="text-[10px] text-stone-500 mt-1.5">{{ t("ret.dScanned") }}</div>
              </div>
              <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
                <div class="text-[18px] font-semibold text-stone-900 tabular-nums leading-none">{{ activeBatch.ordered }}</div>
                <div class="text-[10px] text-stone-500 mt-1.5">{{ t("ret.dOrdered") }}</div>
              </div>
              <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
                <div class="text-[18px] font-semibold tabular-nums leading-none" :class="activeBatch.missing > 0 ? 'text-rose-600' : 'text-emerald-600'">{{ activeBatch.missing }}</div>
                <div class="text-[10px] text-stone-500 mt-1.5">{{ t("ret.dMissingU") }}</div>
              </div>
            </div>

            <div class="flex items-center gap-2 text-[11.5px]">
              <Icon :name="activeBatch.srCreated ? 'check-circle' : 'clock'" :size="13"
                    :class="activeBatch.srCreated ? 'text-emerald-500' : 'text-amber-500'" />
              <span :class="activeBatch.srCreated ? 'text-emerald-700' : 'text-amber-700'">
                {{ activeBatch.srCreated ? t("ret.srCreated") : t("ret.srPending") }}
              </span>
            </div>

            <!-- missing note -->
            <div v-if="batchDetail && batchDetail.missingSkus" class="rounded-xl bg-rose-50 ring-1 ring-rose-200/60 p-3">
              <div class="text-[11px] font-semibold uppercase tracking-wide text-rose-600 mb-1">{{ t("ret.missingNote") }}</div>
              <p class="text-[12px] text-rose-800 whitespace-pre-line">{{ batchDetail.missingSkus }}</p>
            </div>

            <!-- items -->
            <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
              <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-900">
                {{ batchDetail ? batchDetail.items.length : "…" }} {{ t("ret.items") }}
              </div>
              <div v-if="!batchDetail" class="p-4 space-y-2">
                <div v-for="n in 4" :key="n" class="h-10 rounded-lg bg-stone-100 animate-pulse" />
              </div>
              <div v-else class="divide-y divide-stone-100 max-h-[48vh] overflow-y-auto">
                <div v-for="(it, i) in batchDetail.items" :key="i" class="px-4 py-2.5 flex items-center gap-3">
                  <span class="w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0"
                        :class="it.complete ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'">
                    <Icon :name="it.complete ? 'check-circle' : 'alert-circle'" :size="13" />
                  </span>
                  <div class="min-w-0 flex-1">
                    <div class="text-[12px] font-medium text-stone-900 truncate">{{ it.name }}</div>
                    <div class="font-mono text-[10.5px] text-stone-400 truncate">
                      {{ it.sku }}<template v-if="it.awb"> · {{ it.awb }}</template>
                    </div>
                  </div>
                  <div class="text-end flex-shrink-0">
                    <div class="text-[12px] font-semibold tabular-nums" :class="it.complete ? 'text-stone-900' : 'text-rose-600'">
                      {{ it.actual }}/{{ it.ordered }}
                    </div>
                    <div class="text-[10px]" :class="it.complete ? 'text-emerald-600' : 'text-rose-500'">
                      {{ it.complete ? t("ret.complete") : t("ret.missing") + " " + it.missing }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, h, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { CARRIER, fmtMAD } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";

const router = useRouter();
const { t } = useI18n();

// ── state ────────────────────────────────────────────────────────────
const mode = ref("loading"); // loading → skeleton · live · demo
const loading = ref(false);
const tab = ref("awaiting");
const rows = ref([]);
const kpis = ref({});
const total = ref(0);
const page = ref(1);
const pageSize = 30;
const daysF = ref(30);
const q = ref("");
let searchTimer = null;

// Demo fallback (backend unreachable) — a small awaiting-shaped seed.
const DEMO = {
  kpis: { awaiting: 4, awaitingValue: 1180, batches: 2, receivedOrders: 61, missingQty: 3, avgPct: 97.2,
          topMissing: [{ sku: "MUZ22014", name: "Palette ombres MU", qty: 2 }, { sku: "CSM44021", name: "Sérum éclat 30ml", qty: 1 }] },
  awaiting: [
    { order: "#240682", customer: "Edghir hanane", value: 349, awb: "LD007744422", dn: "MAT-DN-2026-71104", age: 6, phone: "+212661234567", city: "Rabat" },
    { order: "#238900", customer: "Meryem Meryem", value: 195, awb: "LD007803359", dn: "MAT-DN-2026-79208", age: 3, phone: "+212645934101", city: "Kenitra" },
  ],
  batches: [
    { no: "RET-26-3137317", date: "2026-06-28", status: "Returned", owner: "redazaari47@gmail.com", orders: 32, ordered: 40, actual: 38, missing: 2, pct: 95, srCreated: true },
    { no: "RET-26-3137320", date: "2026-07-02", status: "Returned", owner: "redazaari47@gmail.com", orders: 29, ordered: 31, actual: 31, missing: 0, pct: 100, srCreated: true },
  ],
};

async function load(keepPage = false) {
  if (!keepPage) page.value = 1;
  loading.value = true;
  const live = await liveOr(null, () => api("returns.board", {
    tab: tab.value, days: daysF.value, q: q.value.trim() || undefined,
    limit: pageSize, offset: (page.value - 1) * pageSize,
  }));
  if (live && Array.isArray(live.rows)) {
    mode.value = "live";
    rows.value = live.rows;
    kpis.value = live.kpis || {};
    total.value = live.total || 0;
  } else if (mode.value !== "live") {
    mode.value = "demo";
    kpis.value = DEMO.kpis;
    rows.value = tab.value === "awaiting" ? DEMO.awaiting : DEMO.batches;
    total.value = rows.value.length;
  }
  loading.value = false;
}
onMounted(load);

function setTab(tb) {
  tab.value = tb;
  q.value = "";
  load();
}
function onSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => load(), 350);
}

const missingMax = computed(() => Math.max(1, ...(kpis.value.topMissing || []).map((m) => m.qty)));

// ── batch drawer ─────────────────────────────────────────────────────
const activeBatch = ref(null);
const batchDetail = ref(null);
async function openBatch(b) {
  activeBatch.value = b;
  batchDetail.value = null;
  const d = await liveOr(null, () => api("returns.batch_detail", { name: b.no }));
  if (d && d.no) batchDetail.value = d;
  else batchDetail.value = { items: [], missingSkus: "" };
}

// ── helpers ──────────────────────────────────────────────────────────
const OWNER_SHORT = {
  marouaneelmessaoudi07: "Marouane", mouakkalanass: "Anass", anaskarrassi: "Anas K.",
  asmaazirary7: "Asmaa", lamdanisaad12: "Saad", ossamanahila: "Oussama",
  saidnakri65: "Said", redazaari47: "Reda", elabdouny99: "Abdouny", Administrator: "System",
};
function ownerShort(email) {
  const k = String(email || "").split("@")[0];
  return OWNER_SHORT[k] || k || "—";
}
function ownerInitials(email) {
  const s = ownerShort(email);
  return ((s[0] || "?") + (s[1] || "")).toUpperCase();
}
// Moroccan mobile → wa.me international format (0612… → 212612…).
function waLink(phone) {
  let d = (phone || "").replace(/\D/g, "");
  if (d.startsWith("00")) d = d.slice(2);
  if (d.startsWith("0")) d = "212" + d.slice(1);
  else if (!d.startsWith("212")) d = "212" + d;
  return `https://wa.me/${d}`;
}
function openOrder(no) {
  router.push({ name: "OrderDetail", params: { name: String(no).replace("#", "") } });
}

// ── shared pagination footer ─────────────────────────────────────────
const PagerBar = () => {
  if (!(total.value > pageSize)) return null;
  const tp = Math.max(1, Math.ceil(total.value / pageSize));
  const btn = (dis, go, icon) => h("button", {
    class: "pager-btn", disabled: dis,
    onClick: () => { go(); load(true); },
  }, [h(Icon, { name: icon, size: 13, class: "flip-rtl" })]);
  return h("div", { class: "flex items-center justify-between px-4 py-2.5 border-t border-stone-100 bg-stone-50/50" }, [
    h("span", { class: "text-[11.5px] text-stone-500 tabular-nums" },
      `${(page.value - 1) * pageSize + 1}–${Math.min(page.value * pageSize, total.value)} ${t("ret.of")} ${total.value}`),
    h("div", { class: "flex items-center gap-1" }, [
      btn(page.value <= 1, () => { page.value--; }, "chevron-left"),
      h("span", { class: "text-[11.5px] text-stone-600 tabular-nums px-1.5" }, `${page.value} / ${tp}`),
      btn(page.value * pageSize >= total.value, () => { page.value++; }, "chevron-right"),
    ]),
  ]);
};
</script>

<style scoped>
.lp-drawer-enter-active,
.lp-drawer-leave-active { transition: opacity 0.2s ease; }
.lp-drawer-enter-from,
.lp-drawer-leave-to { opacity: 0; }
</style>
