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
                <div class="text-[11.5px] text-stone-500">{{ CARRIER }} · Today {{ MANIFEST.pickupDate }} · {{ MANIFEST.window }}</div>
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

        <!-- not-yet-labeled warning -->
        <div
          v-if="notLabeled > 0"
          class="rounded-lg bg-amber-50 ring-1 ring-amber-200/70 px-4 py-2.5 flex items-center gap-2 text-[12.5px] text-amber-800"
        >
          <Icon name="alert-triangle" :size="16" class="text-amber-500 flex-shrink-0" />
          {{ notLabeled }} picked orders not yet labeled — label them before closing the manifest.
        </div>

        <!-- scan to add -->
        <ScanInput ref="scanner" placeholder="Scan parcel / AWB to add to manifest" @scan="onScan" />

        <!-- added parcels -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-700 flex items-center justify-between">
            <span>On manifest · last added</span>
            <span class="text-stone-400 tabular-nums">{{ parcels.length }} on manifest</span>
          </div>
          <div class="divide-y divide-stone-100 max-h-[420px] overflow-y-auto">
            <div v-if="!parcels.length" class="px-4 py-10 text-center text-[12.5px] text-stone-400">
              <Icon name="scan-barcode" :size="26" class="mx-auto mb-2 opacity-60" />
              Scan a parcel or AWB above to start building today's {{ CARRIER }} handover.
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
                title="Remove"
                @click="remove(i)"
              >
                <Icon name="x" :size="15" />
              </button>
            </div>
          </div>
        </div>

        <!-- recent manifests -->
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="px-4 py-2.5 border-b border-stone-100 text-[12px] font-semibold text-stone-700">Recent manifests</div>
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
            <span class="text-[12px] font-semibold uppercase tracking-wide">Cutoff in</span>
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
            class="inline-flex items-center justify-center gap-1.5 w-full h-11 rounded-lg text-[14px] font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="!parcels.length"
            @click="closeManifest"
          >
            <Icon name="send" :size="16" /> Close manifest &amp; hand to carrier
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
import {
  MANIFEST as DEMO_MANIFEST, RECENT_MANIFESTS as DEMO_RECENT_MANIFESTS, PARCELS, SLA, SLA_LABEL,
  CARRIER, CUTOFF as DEMO_CUTOFF, fmtMAD,
} from "@/lib/handoffData.js";
import { api, liveOr } from "@/lib/resource";
import { useToast } from "@/composables/useToast";

const { success, warn } = useToast();

// Live-or-demo refs (same names as the demo consts so the template keeps working).
const MANIFEST = ref({ ...DEMO_MANIFEST });
const RECENT_MANIFESTS = ref(DEMO_RECENT_MANIFESTS);
const CUTOFF = ref(DEMO_CUTOFF);

const scanner = ref(null);
// preload the first two parcels as "just added" so the manifest isn't empty
const parcels = ref(PARCELS.slice(0, 2).map((p) => ({ ...p })));
const pool = ref(PARCELS.slice(2).map((p) => ({ ...p })));
const notLabeled = ref(3);

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

function onScan(code) {
  let parcel;
  if (pool.value.length) {
    parcel = pool.value.shift();
    parcel = { ...parcel, awb: code };
  } else {
    parcel = {
      dn: "MAT-DN-2026-" + (77100 + parcels.value.length),
      awb: code,
      order: "#" + (242600 + parcels.value.length),
      customer: "Scanned parcel",
      value: 149,
      sla: "ontrack",
    };
  }
  parcels.value.unshift(parcel);
  if (notLabeled.value > 0) notLabeled.value -= 1;
  scanner.value?.showSuccess(`${parcel.dn} → ${MANIFEST.value.no}`);
}

function remove(i) {
  parcels.value.splice(i, 1);
}

function closeManifest() {
  if (!parcels.value.length) return;
  if (notLabeled.value > 0) {
    warn(`${notLabeled.value} picked orders not yet labeled`, "Label them before closing the manifest.");
  }
  success("Shipment SH-000180 submitted", `${parcels.value.length} parcels handed to ${CARRIER}`);
}

onMounted(async () => {
  timer = setInterval(() => (now.value = new Date()), 30000);

  // Live-or-demo: today's manifest from `shipping.today_manifest`.
  const live = await liveOr(null, () => api("shipping.today_manifest"));
  if (live && live.no) {
    MANIFEST.value = { ...DEMO_MANIFEST, ...live };
    if (live.cutoff) CUTOFF.value = live.cutoff;
    if (Array.isArray(live.parcelRows) && live.parcelRows.length) {
      parcels.value = live.parcelRows.map((p) => ({
        dn: p.dn || "—",
        awb: p.awb || "—",
        order: p.order || "—",
        customer: p.customer || "—",
        value: Number(p.value || 0),
        sla: p.sla || "ontrack",
      }));
      pool.value = [];
    }
    if (live.notOnManifest != null) notLabeled.value = Number(live.notOnManifest) || 0;
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
});
onUnmounted(() => timer && clearInterval(timer));
</script>
