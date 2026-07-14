<template>
  <div class="max-w-7xl mx-auto p-6">
    <div class="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4">
      <!-- builder -->
      <div class="space-y-4">
        <!-- manifest header -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4">
          <div class="flex items-center justify-between flex-wrap gap-3">
            <div class="flex items-center gap-3">
              <span class="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <Icon name="truck" :size="20" />
              </span>
              <div>
                <div class="font-mono text-[15px] font-semibold text-stone-900">{{ MANIFEST.no }}</div>
                <div class="text-[11.5px] text-stone-500">{{ CARRIER }} · {{ MANIFEST.pickupDate }} · {{ MANIFEST.window }}</div>
              </div>
            </div>
            <div class="flex items-center gap-5">
              <div class="text-end">
                <div class="text-[24px] font-semibold text-stone-900 tabular-nums leading-none">{{ parcels.length }}</div>
                <div class="text-[10.5px] text-stone-500 uppercase tracking-wide">Parcels</div>
              </div>
              <div class="text-end">
                <div class="text-[24px] font-semibold text-stone-900 tabular-nums leading-none">{{ fmtMAD(totalValue) }}</div>
                <div class="text-[10.5px] text-stone-500 uppercase tracking-wide">MAD</div>
              </div>
            </div>
          </div>
        </div>

        <!-- stale open manifests: they hold their parcels hostage — discard to free them -->
        <div v-if="staleDrafts.length" class="rounded-lg bg-rose-50 ring-1 ring-rose-200/70 px-4 py-3 space-y-2">
          <div class="flex items-center gap-2 text-[12.5px] font-semibold text-rose-700">
            <Icon name="alert-triangle" :size="15" class="flex-shrink-0" />
            {{ t("mani.staleTitle") }}
          </div>
          <div v-for="d in staleDrafts" :key="d.name" class="flex items-center gap-3 text-[12.5px]">
            <span class="font-mono font-semibold text-stone-900">{{ d.name }}</span>
            <span class="text-stone-500 flex-1 tabular-nums">{{ d.date }} · {{ d.parcels }} · {{ fmtMAD(d.value) }} MAD</span>
            <button
              class="h-7 px-2.5 rounded-lg text-[11.5px] font-semibold ring-1 transition-colors"
              :class="armedDiscard === d.name
                ? 'text-white bg-rose-600 ring-rose-600'
                : 'text-rose-700 bg-white ring-rose-200 hover:bg-rose-100'"
              :disabled="discarding"
              @click="discard(d.name)"
            >{{ armedDiscard === d.name ? t("mani.discardSure") : t("mani.discard") }}</button>
          </div>
          <p class="text-[11.5px] text-rose-600/80">{{ t("mani.staleBody") }}</p>
        </div>

        <!-- not-yet-labeled warning -->
        <div
          v-if="notLabeled > 0"
          class="rounded-lg bg-amber-50 ring-1 ring-amber-200/70 px-4 py-2.5 flex items-center gap-2 text-[12.5px] text-amber-800"
        >
          <Icon name="alert-triangle" :size="16" class="text-amber-500 flex-shrink-0" />
          {{ t('px.mani.notLabeled').replace('{n}', notLabeled) }}
        </div>

        <!-- scan to add -->
        <ScanInput ref="scanner" :placeholder="t('px.mani.scanPh')" @scan="onScan" />

        <!-- added parcels -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-700 flex items-center justify-between">
            <span>{{ t("mani.onManifest") }}</span>
            <span class="text-stone-400 tabular-nums">{{ parcels.length }} · {{ t('px.mani.onCount') }}</span>
          </div>
          <div class="divide-y divide-stone-100 max-h-[420px] overflow-y-auto">
            <div v-if="manifestLoading" class="p-3 space-y-2">
              <div v-for="n in 5" :key="n" class="h-[46px] rounded-lg bg-stone-50 ring-1 ring-stone-200/60 animate-pulse" />
            </div>
            <div v-else-if="!parcels.length" class="px-4 py-10 text-center text-[12.5px] text-stone-400">
              <Icon name="scan-barcode" :size="26" class="mx-auto mb-2 opacity-60" />
              {{ t('px.mani.emptyHint').replace('{c}', CARRIER) }}
            </div>
            <div
              v-for="(p, i) in parcels"
              :key="p.dn + i"
              class="flex items-center gap-3 px-4 py-2.5"
            >
              <Icon name="check-circle" :size="16" class="text-emerald-500 flex-shrink-0" />
              <div class="min-w-0 flex-1">
                <div class="font-mono text-[12px] font-medium text-stone-900">{{ p.dn }}</div>
                <div class="text-[11px] text-stone-500">{{ p.customer }} · {{ p.awb }} · {{ p.order }}</div>
              </div>
              <span
                v-if="p.sla === 'late' || p.sla === 'atrisk' || p.sla === 'breached'"
                class="inline-flex items-center gap-1 px-1.5 h-[18px] rounded text-[10.5px] font-medium ring-1"
                :class="[SLA[p.sla]?.txt, SLA[p.sla]?.bg, SLA[p.sla]?.ring]"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="SLA[p.sla]?.dot" />{{ SLA_LABEL[p.sla] }}
              </span>
              <span class="text-[12px] font-semibold text-stone-800 tabular-nums">{{ fmtMAD(p.value) }}</span>
              <button
                class="inline-flex items-center justify-center w-6 h-6 rounded-md text-stone-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                :title="t('px.common.remove')"
                @click="remove(i)"
              >
                <Icon name="x" :size="15" />
              </button>
            </div>
          </div>
        </div>

        <!-- recent manifests -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-700">{{ t("mani.recent") }}</div>
          <div class="divide-y divide-stone-100">
            <div
              v-for="m in RECENT_MANIFESTS"
              :key="m.no"
              class="flex items-center gap-3 px-4 py-2.5 text-[12.5px]"
            >
              <Icon name="truck" :size="15" class="text-stone-400 flex-shrink-0" />
              <span class="font-mono font-semibold text-stone-900 w-[90px]">{{ m.no }}</span>
              <span class="text-stone-500 flex-1">{{ m.date }}</span>
              <span class="tabular-nums text-stone-600">{{ m.parcels }} parcels</span>
              <span class="tabular-nums text-stone-600 w-[80px] text-end">{{ fmtMAD(m.value) }} MAD</span>
              <span class="inline-flex items-center px-2 h-[20px] rounded-md text-[11px] font-medium text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200">{{ m.status }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- cutoff + close -->
      <div class="space-y-3">
        <div
          class="bg-gradient-to-br from-amber-50 to-white rounded-xl ring-1 p-4"
          :class="cutoffUrgent ? 'ring-rose-200/70' : 'ring-amber-200/70'"
        >
          <div class="flex items-center gap-2" :class="cutoffUrgent ? 'text-rose-700' : 'text-amber-700'">
            <Icon name="clock" :size="16" />
            <span class="text-[12px] font-semibold uppercase tracking-wide">{{ t("mani.cutoffIn") }}</span>
          </div>
          <div
            class="text-[34px] font-bold tabular-nums mt-1.5 leading-none"
            :class="cutoffUrgent ? 'text-rose-600' : 'text-stone-900'"
          >{{ countdown }}</div>
          <div class="text-[11.5px] text-stone-500 mt-1">Cutoff {{ CUTOFF }} · pickup {{ MANIFEST.window }}</div>
        </div>

        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-4 space-y-3">
          <div class="space-y-1.5 text-[12.5px]">
            <div class="flex items-center justify-between">
              <span class="text-stone-400">Parcels</span><span class="font-medium text-stone-800 tabular-nums">{{ parcels.length }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-stone-400">Value</span><span class="font-medium text-stone-800 tabular-nums">{{ fmtMAD(totalValue) }} MAD</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-stone-400">Carrier</span><span class="font-medium text-stone-800">{{ CARRIER }}</span>
            </div>
          </div>
          <button
            class="inline-flex items-center justify-center gap-1.5 w-full h-9 rounded-lg text-[13px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors disabled:opacity-40"
            :disabled="!parcels.length || printing"
            @click="printSheet"
          >
            <Icon name="printer" :size="15" /> {{ printing ? "…" : t('mani.print') }}
          </button>
          <button
            class="inline-flex items-center justify-center gap-1.5 w-full h-11 rounded-lg text-[14px] font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="!parcels.length || closing"
            @click="closeManifest"
          >
            <Icon name="send" :size="16" /> {{ closing ? t('px.mani.closing') : t('px.mani.closeBtn') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm: closing submits the Shipment (real carrier handover) -->
    <div v-if="confirmClose" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-stone-900/40" @click="confirmClose = false" />
      <div class="relative bg-white rounded-2xl ring-1 ring-stone-200 shadow-xl w-full max-w-md p-5">
        <div class="flex items-center gap-2.5 mb-2">
          <span class="inline-flex w-9 h-9 rounded-xl items-center justify-center bg-emerald-50 text-emerald-600">
            <Icon name="send" :size="18" />
          </span>
          <h3 class="text-[15px] font-semibold text-stone-900">{{ t('px.mani.confirmTitle') }}</h3>
        </div>
        <p class="text-[13px] text-stone-600 leading-relaxed">
          This submits the Shipment for <b class="tabular-nums">{{ parcels.length }}</b> parcels
          (<b class="tabular-nums">{{ fmtMAD(totalValue) }} MAD</b>) to {{ CARRIER }}. Every order
          is marked <b>Shipped</b> and its invoice drafted. This can't be undone from the portal.
        </p>
        <p v-if="notLabeled > 0" class="mt-2 text-[12px] text-amber-700 bg-amber-50 ring-1 ring-amber-200/60 rounded-lg px-3 py-2">
          {{ notLabeled }} picked orders aren't labeled yet — they won't be on this manifest.
        </p>
        <div class="flex items-center justify-end gap-2 mt-4">
          <button class="h-9 px-4 rounded-lg text-[13px] font-medium text-stone-600 hover:bg-stone-100"
                  :disabled="closing" @click="confirmClose = false">{{ t("mani.keepOpen") }}</button>
          <button class="h-9 px-4 rounded-lg text-[13px] font-semibold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
                  :disabled="closing" @click="doClose">
            {{ closing ? "Closing…" : "Close & submit" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import ScanInput from "@/components/ui/ScanInput.vue";
import { SLA, SLA_LABEL, CARRIER, fmtMAD } from "@/lib/handoffData.js";
import { api, apiPost, liveOr } from "@/lib/resource";
import { printManifestSheet } from "@/lib/manifestPrint";
import { useToast } from "@/composables/useToast";
import { useI18n } from "@/composables/useI18n";

const { success, warn } = useToast();
const { t } = useI18n();

// Closing the manifest is a real submit: it hands the parcels to the carrier,
// flips every order to Shipped and drafts their invoices — so it's confirmed.
const closing = ref(false);
const confirmClose = ref(false);
const printing = ref(false);

// Driver handover sheet — printable list of today's manifest with signatures.
async function printSheet() {
  printing.value = true;
  try {
    const sheet = await api("shipping.manifest_sheet");
    if (!printManifestSheet(sheet)) warn(t("mani.printBlocked"), "");
  } catch (e) {
    warn(t("mani.printFail"), String(e.message || e));
  } finally {
    printing.value = false;
  }
}

// Live-or-demo refs (same names as the demo consts so the template keeps working).
const MANIFEST = ref({ no: "—", pickupDate: "", window: "" });
const RECENT_MANIFESTS = ref([]);
const CUTOFF = ref("17:00");

const scanner = ref(null);
const isLive = ref(false);
const manifestLoading = ref(true);
const parcels = ref([]);
const readyCount = ref(0); // ready-to-ship parcels waiting to be scanned onto the manifest
const pool = ref([]);
const notLabeled = ref(0);

const totalValue = computed(() => parcels.value.reduce((s, p) => s + Number(p.value || 0), 0));

// live cutoff countdown from CUTOFF "14:00"
const now = ref(new Date());
let timer = null;

const minsToCutoff = computed(() => {
  const [h, m] = String(CUTOFF.value || "14:00").split(":").map(Number);
  const target = new Date(now.value);
  target.setHours(h, m, 0, 0);
  return Math.round((target - now.value) / 60000);
});
const cutoffUrgent = computed(() => minsToCutoff.value < 30);
const countdown = computed(() => {
  const mins = minsToCutoff.value;
  if (mins <= 0) return "Past cutoff";
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h}h ${m}m`;
});

async function onScan(code) {
  const c = String(code || "").trim();
  if (isLive.value) {
    if (!c) return;
    if (parcels.value.some((p) => (p.awb || "").toLowerCase() === c.toLowerCase())) {
      scanner.value?.showError(t("mani.already")); return;
    }
    const res = await liveOr(null, () => apiPost("shipping.manifest_scan", { code: c }));
    if (!res || !res.ok) {
      scanner.value?.showError(
        res && res.reason === "already" ? t("mani.alreadyShip")
          : res && res.reason === "not_ready" ? t("mani.notReady")
            : t("mani.unknownAwb"));
      return;
    }
    parcels.value.unshift({ dn: res.dn, awb: res.awb, order: res.order,
      customer: res.customer, value: res.value, sla: "ontrack" });
    scanner.value?.showSuccess(`✓ ${res.awb} · ${parcels.value.length}`);
    return;
  }
  // Not live = no backend session. Never invent a parcel — reload instead.
  scanner.value?.showError("لا يوجد اتصال بالسيرفر — أعد تحميل الصفحة");
}

async function remove(i) {
  const p = parcels.value[i];
  if (!p) return;
  if (isLive.value) {
    // Really take it off the draft Shipment — the old local-only splice left
    // the row on the server, so the "removed" parcel shipped anyway.
    try {
      const res = await apiPost("shipping.manifest_remove", { dn: p.dn });
      if (!res || !res.ok) {
        warn(t("mani.removeFail"), res && res.reason === "no_manifest" ? t("mani.noOpen") : p.dn);
        return;
      }
    } catch (e) {
      warn(t("mani.removeFail"), String(e.message || e));
      return;
    }
  }
  parcels.value.splice(i, 1);
}

// ── stale open manifests (previous days) — two-tap discard ──────────
const staleDrafts = ref([]);
const armedDiscard = ref("");
const discarding = ref(false);
let disarmTimer = null;

async function discard(name) {
  if (armedDiscard.value !== name) {
    armedDiscard.value = name;
    clearTimeout(disarmTimer);
    disarmTimer = setTimeout(() => (armedDiscard.value = ""), 4000);
    return;
  }
  discarding.value = true;
  try {
    await apiPost("shipping.discard_manifest", { name });
    staleDrafts.value = staleDrafts.value.filter((d) => d.name !== name);
    success(t("mani.discarded"), name);
    await loadManifest(); // freed parcels re-enter the ready pool
  } catch (e) {
    warn(t("mani.removeFail"), String(e.message || e));
  } finally {
    discarding.value = false;
    armedDiscard.value = "";
  }
}

function closeManifest() {
  if (!parcels.value.length) return;
  if (!isLive.value) {
    warn("لا يوجد اتصال بالسيرفر", "أعد تحميل الصفحة قبل إقفال المانيفست");
    return;
  }
  confirmClose.value = true;
}
async function doClose() {
  closing.value = true;
  try {
    const res = await apiPost("shipping.close_manifest");
    confirmClose.value = false;
    success(
      `Shipment ${res.shipment} submitted`,
      `${res.parcels} parcels · ${fmtMAD(res.value)} MAD handed to ${CARRIER} — orders marked Shipped`
        + (res.dropped ? ` · ${res.dropped} ${t("mani.droppedNote")}` : ""),
    );
    await loadManifest();
  } catch (e) {
    warn("Couldn't close the manifest", String(e.message || e));
  } finally {
    closing.value = false;
  }
}

async function loadManifest() {
  // Live only: today's manifest from `shipping.today_manifest`. No demo.
  manifestLoading.value = true;
  const live = await liveOr(null, () => api("shipping.today_manifest"));
  manifestLoading.value = false;
  if (live && live.no) {
    isLive.value = true;
    MANIFEST.value = { window: "09:00 – 17:00", ...live };
    if (live.cutoff) CUTOFF.value = live.cutoff;
    // Scan-built manifest: the parcels are the ones already scanned onto today's
    // draft Shipment (resumed on reload); readyCount is what's still to scan.
    readyCount.value = Number(live.readyCount || 0);
    parcels.value = (Array.isArray(live.parcelRows) ? live.parcelRows : []).map((p) => ({
      dn: p.dn || "—", awb: p.awb || "—", order: p.order || "—",
      customer: p.customer || "—", value: Number(p.value || 0), sla: "ontrack",
    }));
    pool.value = [];
    if (live.notOnManifest != null) notLabeled.value = Number(live.notOnManifest) || 0;
    staleDrafts.value = Array.isArray(live.staleDrafts) ? live.staleDrafts : [];
  }

  // Recent manifests from `shipping.shipments` (demo rows stay as fallback).
  const recents = await liveOr(null, () => api("shipping.shipments", { limit: 5 }));
  if (Array.isArray(recents) && recents.length) {
    RECENT_MANIFESTS.value = recents.map((m) => ({
      no: m.no || m.name || "—",
      date: m.date || "—",
      parcels: Number(m.parcels || 0),
      value: Number(m.value || 0),
      status: m.status || "—",
    }));
  }
}

onMounted(() => {
  timer = setInterval(() => (now.value = new Date()), 30000);
  loadManifest();
});
onUnmounted(() => timer && clearInterval(timer));
</script>
