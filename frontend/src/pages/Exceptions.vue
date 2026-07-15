<template>
  <div class="p-5 sm:p-6 space-y-5 max-w-[1400px] mx-auto animate-fade-in">
    <div>
      <h1 class="text-[20px] font-semibold text-stone-900 tracking-[-0.01em]">{{ t("exc.title") }}</h1>
      <p class="text-[12.5px] text-stone-500 mt-0.5">{{ isLive ? t("exc.subtitleLive").replace("{n}", days) : t("exc.subtitleDemo") }}</p>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="k in kpis" :key="k.label" class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
        <div class="flex items-center gap-2 mb-2">
          <span class="w-7 h-7 rounded-lg flex items-center justify-center" :class="[k.bg, k.fg]">
            <Icon :name="k.icon" :size="15" />
          </span>
          <span class="text-[11px] font-medium text-stone-500">{{ k.label }}</span>
        </div>
        <div class="text-[24px] font-semibold text-stone-900 tabular-nums leading-none">
          {{ k.value }}<span v-if="k.unit" class="text-[12px] text-stone-400 ms-0.5">{{ k.unit }}</span>
        </div>
      </div>
    </div>

    <!-- open/handled tabs -->
    <div v-if="isLive" class="flex items-center gap-1.5">
      <button
        v-for="tb in ['open', 'handled']" :key="tb"
        class="px-3 h-9 text-[12.5px] font-semibold rounded-lg ring-1 whitespace-nowrap"
        :class="tab === tb ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'"
        @click="tab = tb; page = 1; loadLive()"
      >
        {{ tb === 'open' ? t('exc.tabOpen') : t('exc.tabHandled') }}
      </button>
    </div>

    <!-- kind filter -->
    <div class="flex items-center gap-1.5 overflow-x-auto pb-1">
      <button
        v-for="k in kinds"
        :key="k"
        class="px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 whitespace-nowrap"
        :class="filter === k ? 'bg-stone-900 text-white ring-stone-900' : 'bg-white text-stone-600 ring-stone-200 hover:ring-stone-300'"
        @click="filter = k"
      >
        {{ kindLabel(k) }}
      </button>
    </div>

    <!-- rows -->
    <div class="space-y-2">
      <!-- bulk triage bar -->
      <div v-if="selected.size" class="sticky top-2 z-40">
        <div class="flex items-center gap-2.5 flex-wrap bg-stone-900 text-white rounded-2xl shadow-xl px-4 py-2.5">
          <span class="text-[12.5px] font-semibold tabular-nums">{{ selected.size }} {{ t('px.blk.selected') }}</span>
          <span class="w-px h-5 bg-white/20" />
          <button v-for="a in BULK_ACTIONS" :key="a.action"
                  class="h-8 px-3 rounded-lg text-[12px] font-semibold bg-white/10 hover:bg-white/20 disabled:opacity-50"
                  :disabled="bulkBusy" @click="bulkTriage(a.action)">{{ t(a.label) }}</button>
          <button class="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center ms-auto" @click="selected = new Set()">
            <Icon name="x" :size="15" />
          </button>
        </div>
      </div>

      <div
        v-for="e in shown"
        :key="e.id"
        class="relative bg-white rounded-xl ring-1 ring-stone-200/70 p-3.5 ps-4 overflow-hidden flex items-center gap-3 flex-wrap"
      >
        <span class="absolute inset-y-0 start-0 w-1" :class="sevColor(e.sev)" />
        <input v-if="isLive && tab === 'open' && e.dn" type="checkbox" class="blk-cb flex-shrink-0"
               :checked="selected.has(e.dn)" @change="toggleSel(e.dn)" />
        <span
          class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          :class="[toneBg(EXC_KIND[e.kind].tone), toneFg(EXC_KIND[e.kind].tone)]"
        >
          <Icon :name="kindIcon(e.kind)" :size="15" />
        </span>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="font-mono text-[12px] font-semibold text-stone-900">{{ e.id }}</span>
            <span
              class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap"
              :class="[toneFg(badgeTone(e.kind)), toneBg(badgeTone(e.kind)), toneRing(badgeTone(e.kind))]"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="toneDot(badgeTone(e.kind))" />{{ e.labelKey ? t(e.labelKey) : e.label }}
            </span>
            <span
              v-if="e.age > e.sla"
              class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap text-rose-700 bg-rose-50 ring-rose-200"
            >{{ t("exc.overdue") }}</span>
          </div>
          <div class="text-[12px] text-stone-600 mt-0.5 truncate">{{ e.detail }}</div>
        </div>
        <div class="flex items-center gap-1.5 text-[11px] text-stone-400">
          <span v-if="e.owner" class="w-5 h-5 rounded-full bg-stone-200 text-stone-600 flex items-center justify-center text-[9px] font-semibold">{{ initials(byId(e.owner).name) }}</span>
          <span class="tabular-nums" :class="e.age > e.sla ? 'text-rose-600 font-medium' : ''">{{ e.labelKey ? t('exc.dOld').replace('{n}', e.age) : e.age + 'm' }}</span>
        </div>
        <div class="flex items-center gap-1.5">
          <template v-if="e.phone">
            <a :href="'tel:' + e.phone" :title="e.phone"
               class="w-8 h-8 rounded-lg ring-1 ring-stone-200 bg-white text-stone-500 hover:ring-emerald-300 hover:text-emerald-700 flex items-center justify-center">
              <Icon name="phone" :size="13" />
            </a>
            <a :href="waLink(e.phone)" target="_blank" title="WhatsApp"
               class="w-8 h-8 rounded-lg ring-1 ring-stone-200 bg-white text-stone-500 hover:ring-emerald-300 hover:text-emerald-700 flex items-center justify-center">
              <Icon name="message-circle" :size="13" />
            </a>
          </template>
          <a v-if="e.dn" :href="'/app/delivery-note/' + encodeURIComponent(e.dn)" target="_blank"
             class="inline-flex items-center gap-1.5 px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 ring-stone-200 text-stone-700 bg-white hover:ring-stone-300">
            <Icon name="file-text" :size="13" />{{ t("exc.dn") }}
          </a>
          <button
            v-if="e.order || String(e.id).startsWith('#')"
            class="inline-flex items-center gap-1.5 px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 whitespace-nowrap text-white"
            :style="{ background: 'var(--accent-600)', borderColor: 'var(--accent-600)' }"
            @click="openOrder(e.order || e.id)"
          >
            <Icon name="arrow-right" :size="13" class="flip-rtl" />{{ t("exc.order") }}
          </button>
          <!-- Triage (live, open tab): record the decision -->
          <template v-if="isLive && tab === 'open'">
            <button class="triage-btn text-amber-700 ring-amber-200 hover:bg-amber-50" :disabled="busy === e.id"
                    :title="t('exc.actRedeliverHint')" @click="triage(e, 'Redeliver')">
              <Icon name="refresh-cw" :size="12" />{{ t('exc.actRedeliver') }}
            </button>
            <button class="triage-btn text-violet-700 ring-violet-200 hover:bg-violet-50" :disabled="busy === e.id"
                    :title="t('exc.actReturnHint')" @click="triage(e, 'Return Requested')">
              <Icon name="rotate-ccw" :size="12" />{{ t('exc.actReturn') }}
            </button>
            <button class="triage-btn text-emerald-700 ring-emerald-200 hover:bg-emerald-50" :disabled="busy === e.id"
                    :title="t('exc.actResolvedHint')" @click="triage(e, 'Resolved')">
              <Icon name="check" :size="12" />{{ t('exc.actResolved') }}
            </button>
            <button v-if="e.order" class="triage-btn text-stone-700 ring-stone-200 hover:bg-stone-50" :disabled="busy === e.id"
                    :title="t('exc.actReshipHint')" @click="doReship(e)">
              <Icon name="send" :size="12" />{{ t('exc.actReship') }}
            </button>
            <button v-if="isManager && e.dn" class="triage-btn hover:bg-rose-50"
                    :class="armedCancel === e.id ? 'text-white bg-rose-600 ring-rose-600' : 'text-rose-700 ring-rose-200'"
                    :disabled="busy === e.id"
                    :title="t('exc.cancelHint')" @click="doCancel(e)">
              <Icon name="x" :size="12" />{{ armedCancel === e.id ? t('exc.cancelSure') : t('exc.cancelParcel') }}
            </button>
          </template>
          <span v-else-if="isLive && e.action"
                class="inline-flex items-center gap-1 px-2 h-7 rounded-md text-[11px] font-semibold ring-1 text-stone-600 bg-stone-50 ring-stone-200">
            <Icon name="check" :size="11" />{{ e.action }}
          </span>
          <button
            v-else-if="!isLive"
            class="inline-flex items-center gap-1.5 px-2.5 h-8 text-[12px] font-medium rounded-lg ring-1 whitespace-nowrap text-white"
            :style="{ background: 'var(--accent-600)', borderColor: 'var(--accent-600)' }"
            @click="resolveExc(e.id)"
          >
            <Icon name="check" :size="13" />{{ t("exc.resolve") }}
          </button>
        </div>
      </div>
      <div v-if="shown.length === 0" class="text-center text-[12.5px] text-emerald-600 py-12 flex items-center justify-center gap-1.5">
        <Icon name="check-circle" :size="16" />{{ t("exc.allClear") }}
      </div>
      <div v-if="isLive && total > pageSize" class="flex items-center justify-between px-1 pt-1">
        <span class="text-[11.5px] text-stone-500 tabular-nums">
          {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, total) }} {{ t("exc.of") }} {{ total }}
        </span>
        <div class="flex items-center gap-1">
          <button class="pager-btn" :disabled="page <= 1" @click="page--; loadLive()">
            <Icon name="chevron-left" :size="13" class="flip-rtl" />
          </button>
          <span class="text-[11.5px] text-stone-600 tabular-nums px-1.5">{{ page }} / {{ Math.max(1, Math.ceil(total / pageSize)) }}</span>
          <button class="pager-btn" :disabled="page * pageSize >= total" @click="page++; loadLive()">
            <Icon name="chevron-right" :size="13" class="flip-rtl" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { useToast } from "@/composables/useToast";
import { byId } from "@/lib/handoffData";
import { api, apiPost, liveOr } from "@/lib/resource";
import { useI18n } from "@/composables/useI18n";
import { useAuth } from "@/composables/useAuth";

const router = useRouter();
const { success, warn } = useToast();
const { t } = useI18n();
const { role } = useAuth();
const isManager = computed(() => role.value === "manager");

// ── local data (not exported from handoffData) ─────────────────────
const EXCEPTIONS = [
  { id: "#242638", kind: "oos", label: "Out of stock", detail: "Mohmad Mohmad · Cosmetic zone · 2 items OOS", owner: "asmaa", age: 158, sev: "red", sla: 30 },
  { id: "#240682", kind: "carrier", label: "Failed delivery", detail: "Edghir hanane · 2nd failed attempt · LD007744422", owner: "nadia", age: 142, sev: "red", sla: 60 },
  { id: "#242128", kind: "carrier", label: "Carrier exception", detail: "Fatima Fatima · address not found", owner: "nadia", age: 86, sev: "orange", sla: 60 },
  { id: "PL-51388", kind: "shortpick", label: "Short-pick", detail: "Nezili kaoutar · MUZ22014 missing 1", owner: "asmaa", age: 47, sev: "orange", sla: 45 },
  { id: "RET-26-3137317", kind: "return", label: "Missing on return", detail: "3 SKUs not in carrier return batch", owner: "nadia", age: 220, sev: "yellow", sla: 120 },
  { id: "CR-2026-0141", kind: "cod", label: "COD discrepancy", detail: "Cathedis · −1,240 MAD short on remittance", owner: "sara", age: 300, sev: "red", sla: 240 },
];
const EXC_KIND = {
  oos: { tone: "rose", icon: "package" },
  carrier: { tone: "orange", icon: "globe" },
  shortpick: { tone: "amber", icon: "alert-circle" },
  return: { tone: "violet", icon: "rotate-ccw" },
  cod: { tone: "rose", icon: "dollar-sign" },
};

const rows = ref([]);
const filter = ref("all");
const kinds = computed(() => isLive.value ? ["all", "exception", "failed"] : ["all", "oos", "carrier", "shortpick", "return", "cod"]);

// Live data from the windowed `shipping.exceptions` ({rows,total,failed,days});
// the demo seed only survives when the backend is truly unreachable.
const isLive = ref(false);
const tab = ref("open");
const busy = ref("");
const total = ref(0);
const failedN = ref(0);
const days = ref(14);
const page = ref(1);
const pageSize = 50;

async function loadLive() {
  const live = await liveOr(null, () => api("shipping.exceptions", {
    days: days.value, limit: pageSize, offset: (page.value - 1) * pageSize,
    tab: tab.value,
  }));
  if (live && Array.isArray(live.rows)) {
    isLive.value = true;
    total.value = live.total || 0;
    failedN.value = live.failed || 0;
    days.value = live.days || 14;
    rows.value = live.rows.map((r) => ({
      id: r.id, dn: r.id, awb: r.awb, customer: r.customer, order: r.order || "",
      kind: "carrier", rawKind: r.kind,
      labelKey: r.kind === "failed" ? "exc.failedDelivery" : "exc.carrierException",
      detail: [r.customer, r.city, r.awb].filter(Boolean).join(" · "),
      value: r.value ?? null, phone: r.phone || "",
      action: r.action || "",
      owner: null, age: r.age ?? 0,
      sev: r.kind === "failed" ? "red" : "orange", sla: 3,
    }));
  }
}
onMounted(loadLive);

// Moroccan mobile → wa.me international format (0612… → 212612…).
function waLink(phone) {
  let d = (phone || "").replace(/\D/g, "");
  if (d.startsWith("00")) d = d.slice(2);
  if (d.startsWith("0")) d = "212" + d.slice(1);
  else if (!d.startsWith("212")) d = "212" + d;
  return `https://wa.me/${d}`;
}

const shown = computed(() => rows.value.filter((e) => filter.value === "all" || e.kind === filter.value || e.rawKind === filter.value));
const critical = computed(() => rows.value.filter((e) => e.sev === "red").length);
const overdue = computed(() => rows.value.filter((e) => e.age > e.sla).length);
const avgAge = computed(() =>
  Math.round(rows.value.reduce((a, e) => a + e.age, 0) / (rows.value.length || 1))
);

const kpis = computed(() => isLive.value ? [
  { label: t("exc.open").replace("{n}", days.value), value: total.value, icon: "alert-circle", bg: "bg-stone-100", fg: "text-stone-600" },
  { label: t("exc.failed"), value: failedN.value, icon: "alert-circle", bg: "bg-rose-50", fg: "text-rose-600" },
  { label: t("exc.exceptions"), value: total.value - failedN.value, icon: "clock", bg: "bg-amber-50", fg: "text-amber-600" },
  { label: t("exc.avgAge"), value: avgAge.value, unit: "d", icon: "activity", bg: "bg-violet-50", fg: "text-violet-600" },
] : [
  { label: t("exc.openPlain"), value: rows.value.length, icon: "alert-circle", bg: "bg-stone-100", fg: "text-stone-600" },
  { label: t("exc.critical"), value: critical.value, icon: "alert-circle", bg: "bg-rose-50", fg: "text-rose-600" },
  { label: t("exc.overdue"), value: overdue.value, icon: "clock", bg: "bg-amber-50", fg: "text-amber-600" },
  { label: t("exc.avgAge"), value: avgAge.value, unit: "m", icon: "activity", bg: "bg-violet-50", fg: "text-violet-600" },
]);

function kindLabel(k) {
  return k === "all" ? t("exc.allKinds")
    : k === "exception" ? t("exc.exceptions")
    : k === "failed" ? t("exc.failed")
    : k === "oos" ? "Out of stock"
    : k === "carrier" ? "Carrier"
    : k === "shortpick" ? "Short-pick"
    : k === "return" ? "Returns"
    : "COD";
}
function kindIcon(k) {
  return (EXC_KIND[k] || EXC_KIND.carrier).icon;
}
function badgeTone(k) {
  const t = EXC_KIND[k].tone;
  return t === "orange" ? "amber" : t;
}
function sevColor(sev) {
  return sev === "red" ? "bg-rose-500" : sev === "orange" ? "bg-orange-500" : "bg-amber-500";
}
const toneBg = (t) => ({ rose: "bg-rose-50", orange: "bg-orange-50", amber: "bg-amber-50", violet: "bg-violet-50" }[t] || "bg-stone-50");
const toneFg = (t) => ({ rose: "text-rose-600", orange: "text-orange-600", amber: "text-amber-600", violet: "text-violet-600" }[t] || "text-stone-600");
const toneRing = (t) => ({ rose: "ring-rose-200", orange: "ring-orange-200", amber: "ring-amber-200", violet: "ring-violet-200" }[t] || "ring-stone-200");
const toneDot = (t) => ({ rose: "bg-rose-500", orange: "bg-orange-500", amber: "bg-amber-500", violet: "bg-violet-500" }[t] || "bg-stone-400");

function initials(name) {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p.length > 1 ? p[p.length - 1][0] : "")).toUpperCase();
}
function resolveExc(id) {
  rows.value = rows.value.filter((e) => e.id !== id);
  success(`${id} resolved`);
}
// ── bulk triage ────────────────────────────────────────────────────
const selected = ref(new Set());
const bulkBusy = ref(false);
const BULK_ACTIONS = [
  { action: "Redeliver", label: "exc.actRedeliver" },
  { action: "Return Requested", label: "exc.actReturn" },
  { action: "Resolved", label: "exc.actResolved" },
];
function toggleSel(dn) {
  const s = new Set(selected.value);
  s.has(dn) ? s.delete(dn) : s.add(dn);
  selected.value = s;
}
async function bulkTriage(action) {
  bulkBusy.value = true;
  try {
    const res = await apiPost("shipping.bulk_exceptions", { action, dns: [...selected.value] });
    const sel = new Set(selected.value);
    rows.value = rows.value.filter((x) => !(x.dn && sel.has(x.dn)));
    total.value = Math.max(0, total.value - res.done);
    if (res.failed?.length) {
      warn(`${t("exc.triaged")}: ${res.done} · ${res.failed.length} ✗`,
           res.failed.slice(0, 3).map((f) => `${f.name}: ${f.error}`).join(" · "));
    } else {
      success(t("exc.triaged"), `${res.done} · ${action}`);
    }
    selected.value = new Set();
  } catch (e) {
    warn(t("exc.triageFail"), String(e.message || e));
  } finally {
    bulkBusy.value = false;
  }
}

async function triage(e, action) {
  busy.value = e.id;
  try {
    await apiPost("shipping.handle_exception", { dn: e.dn, action });
    rows.value = rows.value.filter((x) => x.id !== e.id);
    total.value = Math.max(0, total.value - 1);
    success(t("exc.triaged"), `${e.id} · ${action}`);
  } catch (err) {
    warn(t("exc.triageFail"), String(err.message || err));
  } finally {
    busy.value = "";
  }
}

// Cancel a labelled parcel that never left (manager, two-tap). The server
// blocks anything already handed to Cathedis or delivered.
const armedCancel = ref("");
async function doCancel(e) {
  if (armedCancel.value !== e.id) {
    armedCancel.value = e.id;
    setTimeout(() => { if (armedCancel.value === e.id) armedCancel.value = ""; }, 4000);
    return;
  }
  armedCancel.value = "";
  busy.value = e.id;
  try {
    await apiPost("shipping.cancel_parcel", { dn: e.dn, reason: e.label || "Cancelled from Exceptions" });
    rows.value = rows.value.filter((x) => x.id !== e.id);
    total.value = Math.max(0, total.value - 1);
    success(t("exc.cancelled"), e.id);
  } catch (err) {
    warn(t("exc.cancelFail"), String(err.message || err));
  } finally {
    busy.value = "";
  }
}

async function doReship(e) {
  busy.value = e.id;
  try {
    const res = await apiPost("orders.reship", { order: e.order });
    await apiPost("shipping.handle_exception", { dn: e.dn, action: "Redeliver",
      note: `Reshipped as ${res.order}` }).catch(() => {});
    rows.value = rows.value.filter((x) => x.id !== e.id);
    success(t("exc.reshipped"), `${e.order} → ${res.order}`);
  } catch (err) {
    warn(t("exc.reshipFail"), String(err.message || err));
  } finally {
    busy.value = "";
  }
}

function openOrder(id) {
  if (!id) return;
  router.push({ name: "OrderDetail", params: { name: String(id).replace("#", "") } });
}
</script>

<style scoped>
.triage-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding-inline: 8px;
  height: 28px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  background: #fff;
  /* ring-1: the ring-color utility classes on each button set --tw-ring-color */
  box-shadow: 0 0 0 1px var(--tw-ring-color, #e7e5e4);
}
.triage-btn:disabled { opacity: 0.5; pointer-events: none; }
.blk-cb { width: 15px; height: 15px; accent-color: var(--accent-600); cursor: pointer; }
</style>
