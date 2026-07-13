<template>
  <div class="max-w-7xl mx-auto p-6">
    <!-- Header -->
    <div class="flex items-center justify-between gap-3 mb-4">
      <div>
        <h1 class="text-[19px] font-semibold text-stone-900 tracking-[-0.01em]">Label &amp; Print</h1>
        <p class="text-[12.5px] text-stone-500 mt-0.5">{{ CARRIER }} · {{ WAREHOUSE }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
      <!-- queue -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <span class="text-[13px] font-semibold text-stone-700">
            {{ rows.length }} orders · {{ pending }} to print
          </span>
          <button
            class="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg text-[13px] font-medium text-white bg-[var(--accent-600)] hover:bg-[var(--accent-700)] transition-colors"
            @click="printAll"
          >
            <Icon name="tag" :size="15" /> Generate label · all
          </button>
        </div>

        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 overflow-hidden">
          <div class="divide-y divide-stone-100">
            <div
              v-for="r in rows"
              :key="r.order"
              class="flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors"
              :class="preview === r.order ? 'bg-[var(--accent-50)]/40' : 'hover:bg-stone-50'"
              @click="preview = r.order"
            >
              <span class="font-mono text-[12px] font-semibold text-stone-900 w-[80px] flex-shrink-0 truncate">{{ r.order }}</span>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-1.5">
                  <span class="text-[13px] text-stone-800 truncate">{{ r.customer }}</span>
                  <span
                    class="inline-flex items-center px-1.5 h-[17px] rounded text-[10px] font-medium ring-1"
                    :class="channelChip(r.channel)"
                  >{{ CHANNELS[r.channel]?.label }}</span>
                </div>
                <div class="text-[11px] text-stone-500 tabular-nums">{{ r.parcels }} parcels · {{ fmtMAD(r.value) }} MAD</div>
              </div>
              <span
                class="inline-flex items-center gap-1 px-1.5 h-[18px] rounded text-[10.5px] font-medium ring-1"
                :class="[SLA[r.sla]?.txt, SLA[r.sla]?.bg, SLA[r.sla]?.ring]"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="SLA[r.sla]?.dot" />{{ SLA_LABEL[r.sla] }}
              </span>
              <span
                v-if="r.printed"
                class="inline-flex items-center gap-1 px-2 h-[22px] rounded-md text-[11px] font-medium text-emerald-700 bg-emerald-50 ring-1 ring-emerald-200"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Printed
              </span>
              <button
                v-else
                class="inline-flex items-center gap-1 h-[26px] px-2 rounded-md text-[11px] font-medium text-stone-700 bg-white ring-1 ring-stone-200 hover:bg-stone-50 transition-colors"
                @click.stop="print(r.order)"
              >
                <Icon name="tag" :size="13" /> Print
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- label preview -->
      <div>
        <div class="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-[0.05em] text-stone-400 mb-2">
          <Icon name="scan-barcode" :size="14" /> Label preview
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
          <div class="flex items-center justify-between pb-3 border-b border-dashed border-stone-300">
            <div class="font-bold text-[15px] text-stone-900">{{ CARRIER }}</div>
            <span class="inline-flex items-center px-2 h-[20px] rounded text-[11px] font-medium text-stone-600 bg-stone-100 ring-1 ring-stone-200">AWB</span>
          </div>
          <div class="py-4 text-center">
            <div class="font-mono text-[15px] font-semibold text-stone-900 tracking-wider">{{ awb }}</div>
            <!-- faux barcode -->
            <div class="mt-3 flex items-end justify-center gap-[2px] h-12">
              <span
                v-for="(b, i) in barcode"
                :key="i"
                class="bg-stone-900"
                :style="{ width: b.w + 'px', height: b.h + '%' }"
              />
            </div>
          </div>
          <div class="pt-3 border-t border-dashed border-stone-300 space-y-1.5 text-[12px]">
            <div class="flex items-center justify-between">
              <span class="text-stone-400">Order</span><span class="font-mono font-medium text-stone-800">{{ sel?.order }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-stone-400">Customer</span><span class="font-medium text-stone-800">{{ sel?.customer }}</span>
            </div>
            <div class="pt-1.5 mt-1.5 border-t border-stone-100">
              <div class="text-stone-400 mb-0.5">Ship to</div>
              <div class="text-stone-800 leading-snug text-[11.5px]">
                {{ sel?.customer }}<br />
                {{ sel?.city || "—" }} · Maroc
              </div>
            </div>
            <div class="flex items-center justify-between pt-1.5">
              <span class="text-stone-400">From</span><span class="font-medium text-stone-800">{{ WAREHOUSE }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-stone-400">Parcels</span>
              <span class="inline-flex items-center gap-1 font-medium text-stone-800">
                <Icon name="package" :size="14" /> {{ sel?.parcels }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-stone-400">Value</span><span class="font-medium text-stone-800 tabular-nums">{{ fmtMAD(sel?.value) }} MAD</span>
            </div>
          </div>
          <button
            class="inline-flex items-center justify-center gap-1.5 w-full h-9 mt-4 rounded-lg text-[13px] font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors"
            @click="sel && print(sel.order)"
          >
            <Icon name="printer" :size="15" /> Print label
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import Icon from "@/components/ui/Icon.vue";
import { LABEL_QUEUE as DEMO_LABEL_QUEUE, CHANNELS, SLA, SLA_LABEL, CARRIER, WAREHOUSE, CITY, fmtMAD } from "@/lib/handoffData.js";
import { api, apiPost, liveOr } from "@/lib/resource";
import { useToast } from "@/composables/useToast";

const { success, warn } = useToast();

const labelRows = ref(DEMO_LABEL_QUEUE.map((r) => ({ ...r })));
const rows = labelRows;
const preview = ref(DEMO_LABEL_QUEUE[0].order);

onMounted(async () => {
  const live = await liveOr(null, () => api("shipping.label_queue", { limit: 50 }));
  if (live && live.length) {
    labelRows.value = live.map((r) => ({ ...r }));
    preview.value = live[0].order;
  }
});

const sel = computed(() => rows.value.find((r) => r.order === preview.value));
const pending = computed(() => rows.value.filter((r) => !r.printed).length);

// The REAL carrier AWB from the backend — em-dash when it doesn't exist yet.
const awb = computed(() => sel.value?.awb || "—");

// faux barcode bars — deterministic so they don't jitter between renders
const barcode = Array.from({ length: 42 }, (_, i) => ({
  w: i % 4 === 0 ? 3 : i % 3 === 0 ? 1 : 2,
  h: 60 + ((i * 37) % 40),
}));

function channelChip(key) {
  const tone = CHANNELS[key]?.tone || "slate";
  const map = {
    emerald: "text-emerald-700 bg-emerald-50 ring-emerald-200",
    violet: "text-violet-700 bg-violet-50 ring-violet-200",
    amber: "text-amber-700 bg-amber-50 ring-amber-200",
    green: "text-green-700 bg-green-50 ring-green-200",
    slate: "text-slate-600 bg-slate-50 ring-slate-200",
  };
  return map[tone] || map.slate;
}

async function print(order) {
  const row = rows.value.find((r) => r.order === order);
  if (!row) return;
  if (!row.labelUrl) {
    warn("لا توجد بوليصة لهذا الأوردر بعد", "استخدم Retry AWB من لوحة الطلبات");
    return;
  }
  printLabel(row.labelUrl);
  try {
    await apiPost("shipping.mark_labels_printed", { orders: [order] });
    row.printed = true;
  } catch (e) {
    warn("لم يتم تحديث الحالة", String(e.message || e));
  }
}

function printAll() {
  // Thermal printing is one dialog at a time — open the next unprinted label.
  const next = rows.value.find((r) => !r.printed && r.labelUrl);
  if (next) { preview.value = next.order; print(next.order); }
  else warn("لا توجد بوالص جاهزة للطباعة");
}

// Same hidden-iframe thermal print used by the sorting station.
function printLabel(url) {
  if (!url) return;
  try {
    let f = document.getElementById("lp-print-frame");
    if (!f) { f = document.createElement("iframe"); f.id = "lp-print-frame"; f.style.display = "none"; document.body.appendChild(f); }
    f.onload = () => { try { f.contentWindow.focus(); f.contentWindow.print(); } catch (e) { window.open(url, "_blank"); } };
    f.src = url;
  } catch (e) { window.open(url, "_blank"); }
}
</script>
