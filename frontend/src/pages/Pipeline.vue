<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1500px] mx-auto animate-fade-in">
    <!-- Title -->
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-[22px] font-semibold text-stone-900 tracking-[-0.01em]">Orders</h1>
        <p class="text-[13px] text-stone-500 mt-0.5 flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          Operations theater — the Confirmed flow · {{ WAREHOUSE }}
        </p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <div class="relative">
          <Icon name="search" :size="14" class="absolute top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none" style="inset-inline-start:.65rem" />
          <input
            v-model="q"
            placeholder="Order · customer · AWB…"
            class="h-9 w-[230px] ps-8 pe-8 rounded-lg bg-white ring-1 ring-stone-200 text-[13px] text-stone-900 placeholder:text-stone-400 focus:ring-2 focus:outline-none transition"
            style="--tw-ring-color: var(--accent-400)"
            @input="onSearch"
          />
          <button v-if="q" class="absolute top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600" style="inset-inline-end:.5rem"
                  @click="q=''; onSearch()">
            <Icon name="x" :size="13" />
          </button>
        </div>
        <button
          class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
          :class="loading ? 'opacity-60 pointer-events-none' : ''"
          @click="load(activeStage, activeTrack)"
        >
          <Icon name="refresh-cw" :size="14" :class="loading ? 'animate-spin' : ''" /> Refresh
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
        <div class="text-[13.5px] font-semibold text-stone-900 leading-tight">Needs a human</div>
        <div class="text-[11.5px] text-stone-500">faults, not stages</div>
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

    <!-- Flow strip -->
    <div class="overflow-x-auto py-1 -mx-1 px-1">
      <div class="flex items-stretch gap-0 min-w-[980px]">
        <template v-for="(s, i) in stages" :key="s.key">
          <button
            class="relative flex-1 text-start rounded-xl p-3 ring-1 transition-all duration-200 group overflow-hidden"
            :class="activeStage === s.key
              ? 'bg-white shadow-[0_8px_24px_-8px_rgba(0,0,0,0.14)] ring-2'
              : 'bg-white/60 ring-stone-200/70 hover:bg-white hover:shadow-[0_4px_16px_-6px_rgba(0,0,0,0.1)]'"
            :style="activeStage === s.key ? { '--tw-ring-color': s.hex } : {}"
            @click="load(s.key)"
          >
            <span class="absolute top-0 inset-x-0 h-[3px] transition-opacity"
                  :style="{ background: s.hex, opacity: activeStage === s.key ? 1 : 0 }" />
            <div class="flex items-center gap-2 whitespace-nowrap">
              <span class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                    :style="{ background: s.hex + '1c', color: s.hex }">
                <Icon :name="s.icon" :size="15" />
              </span>
              <span class="text-[10.5px] font-semibold uppercase tracking-[0.04em]"
                    :class="activeStage === s.key ? 'text-stone-900' : 'text-stone-500'">{{ s.label }}</span>
            </div>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-[24px] leading-none font-semibold tabular-nums"
                    :style="{ color: (counts[s.key] ?? 0) > 0 ? s.hex : '#d6d3d1' }">
                {{ counts[s.key] ?? "—" }}
              </span>
              <span v-if="values[s.key]" class="text-[10.5px] font-mono font-medium text-stone-400 tabular-nums">
                {{ fmtK(values[s.key]) }}
              </span>
              <span v-if="s.key === 'to_pick' && counts.to_pick_late > 0"
                    class="ms-auto text-[9.5px] font-bold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded-md ring-1 ring-rose-200/60 tabular-nums whitespace-nowrap">
                {{ counts.to_pick_late }} late
              </span>
            </div>
            <div class="mt-1 text-[10.5px] text-stone-400 leading-tight">{{ s.hint }}</div>
            <div class="mt-2 h-[3px] rounded-full bg-stone-100 overflow-hidden">
              <div class="h-full rounded-full transition-all duration-500"
                   :style="{ width: stageShare(s.key) + '%', background: s.hex, opacity: 0.7 }" />
            </div>
          </button>
          <div v-if="i < stages.length - 1" class="flex items-center px-0.5 text-stone-300 flex-shrink-0">
            <Icon name="chevron-right" :size="14" class="flip-rtl" />
          </div>
        </template>
      </div>
    </div>

    <!-- Shipped sub-segmentation -->
    <div v-if="activeStage === 'shipped'" class="flex items-center gap-2 flex-wrap">
      <span class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400">Carrier status</span>
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
        <div class="text-[14.5px] font-semibold text-stone-900">{{ q ? "No matches" : activeMeta.emptyTitle }}</div>
        <div class="text-[12.5px] text-stone-500 mt-0.5">
          {{ q ? `Nothing in ${activeMeta.label} matches “${q}”.` : activeMeta.emptyHint }}
        </div>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-[13px]">
          <thead class="sticky top-0 z-10">
            <tr class="text-start border-b border-stone-100 bg-white/95 backdrop-blur-sm">
              <th v-if="activeStage === 'to_pick'" class="w-10 px-3 py-2.5 text-center">
                <input type="checkbox" class="board-cb" :checked="allSelected" @change="toggleAll" />
              </th>
              <th class="text-start px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">Order</th>
              <th class="text-start px-3 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">Customer</th>
              <th class="text-start px-3 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">Documents</th>
              <th v-if="activeStage === 'attention'" class="text-start px-3 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">Fault</th>
              <th class="text-start px-3 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">Picker</th>
              <th class="text-start px-3 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">In stage</th>
              <th class="text-end px-3 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">Value</th>
              <th class="text-end px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-stone-100">
            <tr v-for="r in rows" :key="r.no" class="hover:bg-stone-50/70 transition-colors cursor-pointer group"
                :class="selected.has(r.no) ? 'bg-amber-50/50' : ''"
                :style="activeStage === 'to_pick' && missedCutoff(r)
                  ? { boxShadow: 'inset 3px 0 0 #f43f5e' } : {}"
                @click="openOrder(r)">
              <td v-if="activeStage === 'to_pick'" class="px-3 py-3 text-center" @click.stop>
                <input type="checkbox" class="board-cb" :checked="selected.has(r.no)" @change="toggleRow(r.no)" />
              </td>
              <td class="px-4 py-3">
                <div class="font-mono font-bold text-stone-900 flex items-center gap-1.5">
                  {{ r.no }}
                  <span v-if="activeStage === 'to_pick' && missedCutoff(r)"
                        class="text-[9.5px] font-sans font-semibold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded ring-1 ring-rose-200/70 whitespace-nowrap">
                    missed cutoff
                  </span>
                </div>
                <div class="text-[11px] text-stone-400 flex items-center gap-1 mt-0.5 capitalize">
                  <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :style="{ background: channelHex(channelOf(r)) }" />
                  {{ channelOf(r) }}<span v-if="r.city"> · {{ r.city }}</span>
                </div>
              </td>
              <td class="px-3 py-3">
                <div class="font-medium text-stone-800 truncate max-w-[200px]">{{ r.customer }}</div>
                <div v-if="r.itemsDesc" class="text-[10.5px] text-stone-400 truncate max-w-[200px] mt-0.5" :title="r.itemsDesc">
                  {{ r.itemsDesc }}
                </div>
                <div class="flex items-center gap-1.5 mt-0.5">
                  <span class="text-[11px] text-stone-400 tabular-nums">{{ r.items }} item{{ r.items > 1 ? "s" : "" }}</span>
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
              <td class="px-3 py-3">
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
                    {{ r.track }}
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
                <div v-if="r.picker" class="flex items-center gap-1.5">
                  <span class="w-6 h-6 rounded-full bg-stone-100 text-stone-600 text-[10px] font-bold flex items-center justify-center">
                    {{ initials(r.picker) }}
                  </span>
                  <span class="text-[12px] text-stone-600 truncate max-w-[90px]">{{ pickerShort(r.picker) }}</span>
                </div>
                <span v-else class="text-[11px] text-stone-300">—</span>
              </td>
              <td class="px-3 py-3">
                <span class="inline-flex items-center gap-1 text-[12px] font-semibold tabular-nums"
                      :style="{ color: ageHex(r.ageMins) }">
                  <Icon name="clock" :size="12" />{{ ageFmt(r.ageMins) }}
                </span>
                <div v-if="r.created" class="text-[10px] text-stone-400 tabular-nums mt-0.5">{{ createdFmt(r.created) }}</div>
              </td>
              <td class="px-3 py-3 text-end">
                <span class="font-mono font-semibold text-stone-900 tabular-nums">{{ fmtMAD(r.total) }}</span>
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
        <div class="flex items-center justify-between px-4 py-2.5 border-t border-stone-100 bg-stone-50/50">
          <span class="text-[11.5px] text-stone-500 tabular-nums">
            {{ rows.length }} order{{ rows.length === 1 ? "" : "s" }} shown
            <span v-if="(counts[activeStage] ?? 0) > rows.length" class="text-stone-400">of {{ counts[activeStage] }}</span>
          </span>
          <div class="flex items-center gap-3">
            <button
              v-if="canLoadMore"
              class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11.5px] font-semibold text-stone-600 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
              :class="loadingMore ? 'opacity-60 pointer-events-none' : ''"
              @click="loadMore"
            >
              <Icon name="chevron-down" :size="12" :class="loadingMore ? 'animate-bounce' : ''" /> Load more
            </button>
            <span class="text-[12px] font-mono font-semibold text-stone-700 tabular-nums">
              {{ fmtMAD(rowsTotal) }} <span class="text-[10px] font-sans font-normal text-stone-400">MAD</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="text-[11px] text-stone-400 text-center">
      Stage is derived from documents (Pick List → AWB → print → manifest → tracking) — updated {{ updatedAgo }}
    </div>

    <!-- Floating selection bar -->
    <transition name="selbar">
      <div v-if="selected.size" class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
        <div class="flex items-center gap-3 bg-stone-900 text-white rounded-2xl ps-4 pe-2 py-2 shadow-[0_16px_48px_-12px_rgba(0,0,0,0.45)]">
          <span class="text-[13px] font-semibold tabular-nums whitespace-nowrap">{{ selected.size }} selected</span>
          <span class="text-[12px] font-mono text-stone-300 tabular-nums whitespace-nowrap">{{ fmtMAD(selectedTotal) }} MAD</span>
          <button
            class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-[12.5px] font-semibold text-white transition-all"
            :class="creating ? 'opacity-60 pointer-events-none' : 'hover:brightness-110'"
            style="background: var(--accent-600)"
            @click="createPL"
          >
            <Icon name="package" :size="14" :class="creating ? 'animate-pulse' : ''" />
            {{ creating ? "Creating…" : "Create Pick List" }}
          </button>
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
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { WAREHOUSE, fmtMAD } from "@/lib/handoffData";
import { api, apiPost, liveOr } from "@/lib/resource";
import { useToast } from "@/composables/useToast";

const router = useRouter();
const { success, warn } = useToast();

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
  { key: "In Transit",         label: "In Transit",       hex: "#0891b2" },
  { key: "Out For Delivery",   label: "Out for Delivery", hex: "#4f46e5" },
  { key: "Delivery Exception", label: "Exception",        hex: "#e11d48" },
  { key: "Failed Attempt",     label: "Failed",           hex: "#ea580c" },
  { key: "Pending",            label: "Pending",          hex: "#a8a29e" },
  { key: "Delivered",          label: "Awaiting sync",    hex: "#10b981" },
  { key: "none",               label: "No tracking",      hex: "#78716c" },
];

// ── Demo fallback (preview without a backend) ────────────────────────
const DEMO_BOARD = {
  counts: { to_pick: 12, picking: 4, prepared: 6, ready: 5, shipped: 42, delivered: 210, to_return: 9, returned: 6 },
  shippedTracks: { "In Transit": 12, "Out For Delivery": 9, "Delivery Exception": 11, "Failed Attempt": 5, Pending: 3, none: 2 },
  attention: { cancelled_midflow: 2, no_awb: 1, sync_lag: 3 },
  rows: [
    { no: "#242646", customer: "oualid elmouden", total: 149, channel: "shopify", items: 1, city: "Casablanca", awb: "", track: "", ageMins: 41 },
    { no: "#242644", customer: "Chada Rami", total: 198, channel: "shopify", items: 2, city: "Rabat", awb: "", track: "", ageMins: 12 },
    { no: "SAL-ORD-2026-00299", customer: "Salma", total: 149, channel: "manual", items: 1, city: "Tangier", awb: "", track: "", ageMins: 8 },
  ],
};

// ── State ────────────────────────────────────────────────────────────
const counts = ref(DEMO_BOARD.counts);
const values = ref({ to_pick: 5900, picking: 2100, prepared: 3400, ready: 2800, shipped: 21400 });
const shippedTracks = ref(DEMO_BOARD.shippedTracks);
const attention = ref(DEMO_BOARD.attention);
const rows = ref(DEMO_BOARD.rows);
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
  { key: "cancelled_midflow", label: "Cancelled mid-flow", count: attention.value.cancelled_midflow || 0, hex: "#e11d48" },
  { key: "no_awb", label: "PL submitted · no AWB", count: attention.value.no_awb || 0, hex: "#ea580c" },
  { key: "sync_lag", label: "Delivered · not synced", count: attention.value.sync_lag || 0, hex: "#d97706" },
].filter((c) => c.count > 0));

const trackChips = computed(() => {
  const chips = [{ key: "", label: "All", count: counts.value.shipped || 0, hex: "#059669" }];
  for (const t of TRACK_ORDER) {
    const c = shippedTracks.value[t.key] || 0;
    if (c > 0) chips.push({ ...t, count: c });
  }
  return chips;
});

const selected = ref(new Set());
const creating = ref(false);
const offset = ref(0);
const loadingMore = ref(false);

async function load(stage, track = "") {
  activeStage.value = stage;
  activeTrack.value = stage === "shipped" ? track : "";
  loading.value = true;
  offset.value = 0;
  selected.value = new Set();
  const live = await liveOr(null, () =>
    api("orders.board", { stage, track: track || undefined, limit: 50, q: q.value.trim() || undefined })
  );
  if (live && live.counts) {
    counts.value = live.counts;
    values.value = live.values || {};
    shippedTracks.value = live.shippedTracks || {};
    attention.value = live.attention || {};
    rows.value = live.rows || [];
    updatedAt.value = Date.now();
  } else {
    rows.value = stage === "to_pick" ? DEMO_BOARD.rows : [];
  }
  loading.value = false;
}
function setTrack(t) { load("shipped", t); }

const canLoadMore = computed(() =>
  rows.value.length >= 50 && (counts.value[activeStage.value] ?? 0) > rows.value.length
);
async function loadMore() {
  loadingMore.value = true;
  offset.value += 50;
  const live = await liveOr(null, () =>
    api("orders.board", {
      stage: activeStage.value, track: activeTrack.value || undefined,
      limit: 50, offset: offset.value, q: q.value.trim() || undefined,
    })
  );
  if (live && live.rows) rows.value = rows.value.concat(live.rows);
  loadingMore.value = false;
}

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
function missedCutoff(r) {
  if (!r.created) return false;
  const created = new Date(r.created.replace(" ", "T"));
  const cut = new Date(); cut.setHours(14, 0, 0, 0);
  const now = new Date();
  const startOfToday = new Date(); startOfToday.setHours(0, 0, 0, 0);
  if (created < startOfToday) return true;           // from a previous day
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
  return s < 5 ? "just now" : s < 60 ? `${s}s ago` : `${Math.round(s / 60)}m ago`;
});

let refreshTimer = null;
onMounted(() => {
  load("to_pick");
  timer = setInterval(() => { tick.value++; }, 5000);
  // Silent refresh — skipped while the dispatcher has a selection in hand.
  refreshTimer = setInterval(() => {
    if (!selected.value.size && !loading.value && document.visibilityState === "visible") {
      load(activeStage.value, activeTrack.value);
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
  const [d, t] = created.split(" ");
  const today = new Date().toISOString().slice(0, 10);
  if (d === today) return t;
  const dt = new Date(d + "T00:00:00");
  return dt.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + " · " + t;
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
  return { shopify: "#10b981", youcan: "#7c3aed", landing: "#d97706", manual: "#78716c", whatsapp: "#16a34a" }[ch] || "#a8a29e";
}
// 77% of orders have no custom_channel — derive it from the naming series.
function channelOf(r) {
  if (r.channel) return r.channel;
  const no = r.no || "";
  if (no.startsWith("#")) return "shopify";
  if (no.startsWith("YC-")) return "youcan";
  if (no.startsWith("J-")) return "landing";
  if (no.startsWith("WA-")) return "whatsapp";
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
function faultHex(kind) {
  return { cancelled_midflow: "#e11d48", no_awb: "#ea580c", sync_lag: "#d97706" }[kind] || "#78716c";
}
function faultLabel(kind) {
  return { cancelled_midflow: "Cancelled mid-flow — restock", no_awb: "AWB automation failed", sync_lag: "Delivered — status stuck" }[kind] || kind;
}
function actionFor(r) {
  switch (activeStage.value) {
    case "to_pick":   return { label: "Assign", go: () => router.push({ name: "Assign" }) };
    case "picking":   return r.pl ? { label: "Open PL", href: desk("pick-list", r.pl) } : null;
    case "prepared":  return r.labelUrl ? { label: "Print", href: r.labelUrl } : { label: "Open", href: desk("sales-order", r.no) };
    case "ready":     return { label: "Manifest", go: () => router.push({ name: "Manifest" }) };
    case "shipped":   return { label: "Track", href: desk("sales-order", r.no) };
    case "to_return": return { label: "Track", href: desk("sales-order", r.no) };
    case "returned":  return r.ret ? { label: "Open RET", href: desk("return-shipment", r.ret) } : null;
    case "attention": return r.pl ? { label: "Fix", href: desk("pick-list", r.pl) } : { label: "Open", href: desk("sales-order", r.no) };
    default: return null;
  }
}
</script>

<style scoped>
.doc-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 9px; border-radius: 7px;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 11px; font-weight: 500;
  box-shadow: inset 0 0 0 1px var(--chip-ring, transparent);
  transition: background-color .15s;
}
.board-cb {
  width: 15px; height: 15px; cursor: pointer;
  accent-color: var(--accent-600);
}
.selbar-enter-from, .selbar-leave-to { opacity: 0; transform: translate(-50%, 12px); }
.selbar-enter-active, .selbar-leave-active { transition: all .22s cubic-bezier(.16,1,.3,1); }
</style>
