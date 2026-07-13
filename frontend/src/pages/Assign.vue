<template>
  <div class="max-w-7xl mx-auto space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h1 class="text-h2 text-stone-900 flex items-center gap-2 tracking-[-0.01em]">
          <Icon name="users" :size="22" class="text-[var(--accent-600)]" /> Assignment Board
        </h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">Balance unassigned orders across your pickers.</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="inline-flex items-center gap-1.5 px-3 h-9 rounded-lg ring-1 ring-stone-200 bg-white text-[13px] font-medium text-stone-700 hover:bg-stone-50 transition-colors"
                @click="autoBalance">
          <Icon name="zap" :size="16" /> Auto-balance
        </button>
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-stone-100 text-stone-600 text-[11.5px] font-medium">
          <span class="w-1.5 h-1.5 rounded-full bg-stone-400" />
          {{ unassigned.length }} unassigned
        </span>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-4 min-h-0">
      <!-- LEFT — ready to assign -->
      <div class="flex flex-col rounded-xl ring-1 ring-stone-200/70 bg-white/60 overflow-hidden min-h-0">
        <div class="px-4 py-2.5 flex items-center justify-between border-b border-stone-100">
          <span class="text-[12px] font-semibold text-stone-700">Ready to Prepare</span>
          <button v-if="selected.size" @click="clearSelection"
                  class="text-[11.5px] text-stone-500 hover:text-stone-800">
            {{ selected.size }} selected · clear
          </button>
        </div>

        <!-- filter chips -->
        <div class="px-3 pt-3 flex flex-wrap gap-1.5">
          <button v-for="f in filters" :key="f"
                  class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11.5px] font-medium transition-colors"
                  :class="filter === f ? 'bg-[var(--accent-600)] text-white' : 'bg-stone-100 text-stone-600 hover:text-stone-900'"
                  @click="filter = f">
            {{ f }}
            <span class="opacity-70 tabular-nums">{{ countFor(f) }}</span>
          </button>
        </div>

        <!-- order list -->
        <div class="flex-1 overflow-y-auto p-3 space-y-2 max-h-[560px]">
          <button v-for="o in filteredRows" :key="o.no" @click="toggle(o.no)"
                  class="w-full text-start rounded-xl ring-1 p-3 transition-all"
                  :class="selected.has(o.no)
                    ? 'ring-[var(--accent-400)] bg-[var(--accent-50)]/50 shadow-[0_2px_12px_-4px_var(--accent-200)]'
                    : 'ring-stone-200/70 bg-white hover:ring-stone-300'">
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0">
                <span class="w-4 h-4 rounded-md flex items-center justify-center ring-1 flex-shrink-0"
                      :class="selected.has(o.no) ? 'bg-[var(--accent-600)] ring-[var(--accent-600)] text-white' : 'ring-stone-300 bg-white'">
                  <Icon v-if="selected.has(o.no)" name="check" :size="11" />
                </span>
                <span class="font-mono text-[12px] font-semibold text-stone-900 truncate">{{ o.no }}</span>
              </div>
              <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium ring-1"
                    :class="stockChip(o).cls">
                <span class="w-1.5 h-1.5 rounded-full" :class="stockChip(o).dot" />
                {{ stockChip(o).label }}
              </span>
            </div>
            <div class="mt-2 flex items-center justify-between">
              <span class="text-[12.5px] text-stone-700 truncate">{{ o.customer }}</span>
              <span class="text-[12px] font-semibold text-stone-900 tabular-nums">
                {{ fmtMAD(o.total) }} <span class="text-[10px] text-stone-400">MAD</span>
              </span>
            </div>
            <div class="mt-1.5 flex items-center gap-2 text-[11px] text-stone-500">
              <span class="truncate">{{ o.zone }}</span>
              <span class="text-stone-300">·</span>
              <span class="tabular-nums">{{ o.items }} items</span>
              <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium ring-1"
                    :class="slaChip(o.sla).cls">
                <span class="w-1.5 h-1.5 rounded-full" :class="slaChip(o.sla).dot" />
                {{ SLA_LABEL[o.sla] }}
              </span>
            </div>
          </button>

          <div v-if="filteredRows.length === 0" class="text-center text-[12.5px] text-stone-400 py-12">
            All orders assigned ✓
          </div>
        </div>

        <!-- assign bar -->
        <transition name="fade">
          <div v-if="selected.size" class="border-t border-stone-200/70 bg-white p-3">
            <div class="text-[11px] font-semibold uppercase tracking-[0.05em] text-stone-400 mb-1.5">Assign to…</div>
            <div class="flex items-center gap-2">
              <select v-model="assignTo" class="flex-1 h-9 px-2 rounded-lg ring-1 ring-stone-200 bg-white text-[12.5px] text-stone-800 focus:outline-none focus:ring-[var(--accent-400)]">
                <option value="" disabled>Choose a picker…</option>
                <option v-for="p in pickers" :key="p.id" :value="p.id">
                  {{ p.short }} ({{ loadFor(p.id) }}/{{ capacity }})
                </option>
              </select>
              <button class="inline-flex items-center gap-1.5 px-3 h-9 rounded-lg bg-[var(--accent-600)] text-white text-[12.5px] font-medium hover:bg-[var(--accent-700)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      :disabled="!assignTo" @click="doAssign(assignTo)">
                <Icon name="check" :size="15" /> Assign
              </button>
            </div>
            <div class="grid grid-cols-2 gap-1.5 mt-2">
              <button v-for="p in pickers" :key="p.id" @click="doAssign(p.id)"
                      class="flex items-center gap-2 px-2 py-1.5 rounded-lg ring-1 ring-stone-200 hover:ring-[var(--accent-400)] hover:bg-[var(--accent-50)]/40 transition-all">
                <span class="w-[22px] h-[22px] rounded-full grid place-items-center text-white text-[10px] font-semibold shrink-0"
                      :style="{ background: avatarBg(p.id) }">{{ initials(p.name) }}</span>
                <span class="text-[12px] font-medium text-stone-800 truncate">{{ p.short }}</span>
              </button>
            </div>
          </div>
        </transition>
      </div>

      <!-- RIGHT — picker columns (kanban) -->
      <div class="overflow-x-auto">
        <div class="flex gap-3 min-w-min">
          <div v-for="p in pickers" :key="p.id"
               class="w-[250px] flex-shrink-0 flex flex-col bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
            <div class="px-3 py-2.5 border-b border-stone-100">
              <div class="flex items-center gap-2">
                <span class="w-7 h-7 rounded-full grid place-items-center text-white text-[11px] font-semibold shrink-0"
                      :style="{ background: avatarBg(p.id) }">{{ initials(p.name) }}</span>
                <div class="min-w-0 flex-1 leading-tight">
                  <div class="text-[12.5px] font-semibold text-stone-900 truncate flex items-center gap-1">
                    {{ p.short }}<span v-if="p.top" class="text-[10px]">⭐</span>
                  </div>
                  <div class="text-[10.5px] text-stone-500 tabular-nums">{{ loadFor(p.id) }} / {{ capacity }} load</div>
                </div>
                <span class="text-[11px] font-bold tabular-nums"
                      :class="loadPct(p.id) > 80 ? 'text-rose-600' : 'text-stone-500'">{{ loadPct(p.id) }}%</span>
              </div>
              <div class="h-1.5 mt-2.5 rounded-full bg-stone-100 overflow-hidden">
                <div class="h-full rounded-full transition-all"
                     :class="capBar(p.id)"
                     :style="{ width: Math.min(100, loadPct(p.id)) + '%' }" />
              </div>
            </div>
            <div class="flex-1 p-2 space-y-1.5 overflow-y-auto bg-stone-50/40 min-h-[300px]">
              <div v-for="o in assignedTo(p.id)" :key="o.no"
                   class="rounded-lg bg-white ring-1 ring-[var(--accent-300)] p-2">
                <div class="flex items-center justify-between">
                  <span class="font-mono text-[11.5px] font-semibold text-stone-900">{{ o.no }}</span>
                  <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-[var(--accent-50)] text-[var(--accent-700)] ring-1 ring-[var(--accent-200)]">
                    <span class="w-1.5 h-1.5 rounded-full bg-[var(--accent-500)]" /> Assigned
                  </span>
                </div>
                <div class="text-[11.5px] text-stone-600 mt-1 truncate">{{ o.customer }}</div>
              </div>
              <div v-for="o in inProgress(p.id)" :key="o.no"
                   class="rounded-lg bg-white ring-1 ring-stone-200 p-2">
                <div class="flex items-center justify-between">
                  <span class="font-mono text-[11.5px] font-semibold text-stone-700">{{ o.no }}</span>
                  <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium ring-1"
                        :class="stageChip(o.stage).cls">
                    <span class="w-1.5 h-1.5 rounded-full" :class="stageChip(o.stage).dot" />
                    {{ STAGE_LABEL[o.stage] }}
                  </span>
                </div>
                <div class="text-[11.5px] text-stone-500 mt-1 truncate">{{ o.customer }}</div>
              </div>
              <div v-if="assignedTo(p.id).length === 0 && inProgress(p.id).length === 0"
                   class="text-center text-[11.5px] text-stone-400 py-10">
                Idle — ready for work
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from "vue-router";
import { ref, reactive, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import {
  ORDERS, TEAM, byId, fmtMAD, STAGE, SLA, STAGE_LABEL, SLA_LABEL, getInitial,
} from "@/lib/handoffData.js";
import { api, apiPost, liveOr } from "@/lib/resource";

const { success, info, warn } = useToast();

const capacity = 12;

// Live-or-demo orders + pickers. Seed from handoff demo data; onMounted overwrites
// with live `orders.list` (ORDERS shape) and `picking.pickers` ([{id,name,load,capacity}]).
const DEMO_PICKERS = TEAM.filter((p) => p.role === "picker");
const orders = ref(ORDERS);
const pickers = ref(DEMO_PICKERS);

// Live load per picker (from picking.pickers). When set, overrides the derived
// baseLoad so the kanban capacity bars reflect the backend.
const liveLoad = ref(null);

const route = typeof useRoute === "function" ? useRoute() : null;
onMounted(async () => {
  const [liveOrders, livePickers] = await Promise.all([
    liveOr(null, () => api("orders.list", { scope: "queue", limit: 40 })),
    liveOr(null, () => api("picking.pickers")),
  ]);
  if (Array.isArray(liveOrders) && liveOrders.length) orders.value = liveOrders;
  if (Array.isArray(livePickers) && livePickers.length) {
    pickers.value = livePickers.map((p) => {
      const demo = DEMO_PICKERS.find((d) => d.id === p.id) || {};
      return {
        id: p.id,
        email: p.email || "",
        name: p.name || demo.name || p.id,
        short: demo.short || p.name || p.id,
        top: demo.top || false,
      };
    
  // Preselect orders handed over from the Orders board (?orders=a,b,c)
  const pre = (route && route.query.orders ? String(route.query.orders) : "").split(",").filter(Boolean);
  if (pre.length && typeof selected !== "undefined") {
    const s = new Set(selected.value || selected);
    pre.forEach((no) => s.add(no));
    if (selected.value !== undefined) selected.value = s;
  }
});
    liveLoad.value = Object.fromEntries(
      livePickers.map((p) => [p.id, typeof p.load === "number" ? p.load : 0])
    );
  }
});

const filters = ["Ready", "Partial", "Out of Stock", "Combined"];
const filter = ref("Ready");
const selected = ref(new Set());
const assignTo = ref("");

// orderNo -> pickerId (dispatcher assignments made this session)
const assign = reactive({});
const assigning = ref(false);

// seed base loads from orders already in-flight for each picker (demo fallback);
// live picker loads (when present) take precedence via loadFor().
const baseLoad = computed(() => {
  const bl = {};
  pickers.value.forEach((p) => {
    bl[p.id] = liveLoad.value?.[p.id]
      ?? orders.value.filter((o) => o.picker === p.id && ["picking", "picked"].includes(o.stage)).length;
  });
  return bl;
});

const avatarColors = {
  marouane: "#3b82f6", asmaa: "#10b981", saad: "#f97316", oussama: "#8b5cf6", said: "#06b6d4",
};
function avatarBg(id) { return avatarColors[id] || "#78716c"; }
function initials(name) { return getInitial(name); }

function stock(o) {
  if (o.stage === "oos") return "oos";
  if (o.items >= 4) return "partial";
  return "instock";
}
function bucketOf(o) {
  const s = stock(o);
  if (s === "oos") return "Out of Stock";
  if (s === "partial") return "Partial";
  return "Ready";
}

const unassigned = computed(() => orders.value.filter((o) => o.stage === "pending" && !assign[o.no]));
const filteredRows = computed(() => {
  if (filter.value === "Combined") return [];
  return unassigned.value.filter((o) => bucketOf(o) === filter.value);
});
function countFor(f) {
  if (f === "Combined") return 0;
  return unassigned.value.filter((o) => bucketOf(o) === f).length;
}

function loadFor(pid) {
  return (baseLoad.value[pid] || 0) + Object.values(assign).filter((x) => x === pid).length;
}
function loadPct(pid) {
  return Math.round((loadFor(pid) / capacity) * 100);
}
function capBar(pid) {
  const pct = loadPct(pid);
  return pct > 80 ? "bg-rose-500" : pct > 60 ? "bg-amber-500" : "bg-emerald-500";
}

function assignedTo(pid) {
  return Object.entries(assign)
    .filter(([, p]) => p === pid)
    .map(([no]) => orders.value.find((o) => o.no === no))
    .filter(Boolean);
}
function inProgress(pid) {
  return orders.value.filter((o) => o.picker === pid && ["picking", "picked"].includes(o.stage));
}

const stockDefs = {
  instock: { label: "In Stock", cls: "text-emerald-700 bg-emerald-50 ring-emerald-200", dot: "bg-emerald-500" },
  partial: { label: "Partial",  cls: "text-amber-700 bg-amber-50 ring-amber-200",       dot: "bg-amber-500" },
  oos:     { label: "Out of Stock", cls: "text-rose-700 bg-rose-50 ring-rose-200",       dot: "bg-rose-500" },
};
function stockChip(o) { return stockDefs[stock(o)]; }
function slaChip(key) {
  const s = SLA[key] || SLA.ontrack;
  return { cls: `${s.txt} ${s.bg} ${s.ring}`, dot: s.dot };
}
function stageChip(key) {
  const s = STAGE[key] || STAGE.pending;
  return { cls: `${s.txt} ${s.bg} ${s.ring}`, dot: s.dot };
}

function toggle(no) {
  const s = new Set(selected.value);
  s.has(no) ? s.delete(no) : s.add(no);
  selected.value = s;
}
function clearSelection() {
  selected.value = new Set();
  assignTo.value = "";
}
async function doAssign(pid) {
  if (!pid || selected.value.size === 0 || assigning.value) return;
  const picker = pickers.value.find((x) => x.id === pid);
  const orderNos = [...selected.value];
  assigning.value = true;
  try {
    // REAL assignment: one draft Pick List for the batch, assigned to the picker.
    // It lands in their my_queue immediately.
    const res = await apiPost("picking.create_pick_list_from_orders", {
      orders: orderNos,
      picker: picker?.email || undefined,
    });
    orderNos.forEach((no) => { assign[no] = pid; });
    const nSkip = (res.skipped || []).length;
    success(
      `${res.orders} assigned → ${picker?.short || pid}`,
      `${res.pl}` + (nSkip ? ` · ${nSkip} skipped` : ""),
    );
    clearSelection();
  } catch (e) {
    warn("Couldn't assign", String(e.message || e));
  } finally {
    assigning.value = false;
  }
}
async function autoBalance() {
  const pool = unassigned.value;
  if (pool.length === 0) {
    info("Auto-balance", "No unassigned orders to balance.");
    return;
  }
  if (assigning.value) return;
  // Allocate to the least-loaded pickers, then persist ONE pick list per picker.
  const live = {};
  const chunks = {};
  pickers.value.forEach((p) => { live[p.id] = loadFor(p.id); chunks[p.id] = []; });
  pool.forEach((o) => {
    const pid = pickers.value.slice().sort((x, y) => live[x.id] - live[y.id])[0].id;
    chunks[pid].push(o.no);
    live[pid]++;
  });
  assigning.value = true;
  try {
    let made = 0;
    for (const p of pickers.value) {
      if (!chunks[p.id].length) continue;
      const res = await apiPost("picking.create_pick_list_from_orders", {
        orders: chunks[p.id],
        picker: p.email || undefined,
      });
      chunks[p.id].forEach((no) => { assign[no] = p.id; });
      made += 1;
      info(`${p.short || p.id} ← ${res.orders} orders`, res.pl);
    }
    success("Auto-balance done", `${made} pick lists created`);
  } catch (e) {
    warn("Auto-balance stopped", String(e.message || e));
  } finally {
    assigning.value = false;
  }
  info("Auto-balance", `${pool.length} orders balanced across ${pickers.value.length} pickers`);
  clearSelection();
}
</script>

<style scoped>
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(-4px); }
.fade-enter-active, .fade-leave-active { transition: all 0.2s ease; }
</style>
