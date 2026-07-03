<template>
  <div class="min-h-full bg-stone-50">
    <!-- Greeting + stat strip -->
    <div class="px-4 py-3.5 space-y-3.5">
      <div class="leading-tight">
        <div class="text-[11px] text-stone-500">Hi,</div>
        <div class="text-[16px] font-semibold text-stone-900">{{ firstName }}</div>
      </div>

      <!-- stat chips -->
      <div class="grid grid-cols-3 gap-2">
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
          <div class="text-[19px] font-semibold tabular-nums leading-none text-stone-900">{{ completedToday }}</div>
          <div class="text-[10px] text-stone-500 mt-1 leading-tight">today</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
          <div class="text-[19px] font-semibold tabular-nums leading-none text-emerald-600">{{ slaHit }}%</div>
          <div class="text-[10px] text-stone-500 mt-1 leading-tight">SLA hit-rate</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
          <div class="text-[19px] font-semibold tabular-nums leading-none" :class="nextDue < 20 ? 'text-rose-600' : 'text-amber-600'">{{ nextDue }}min</div>
          <div class="text-[10px] text-stone-500 mt-1 leading-tight">Next due</div>
        </div>
      </div>

      <!-- title -->
      <div class="flex items-center justify-between pt-1">
        <h2 class="text-[15px] font-semibold text-stone-900">My queue</h2>
        <span class="text-[11px] text-stone-500">Most urgent first</span>
      </div>

      <!-- queue -->
      <div v-if="!queue.length" class="text-center py-10 text-stone-400">
        <Icon name="check-circle" :size="32" class="mx-auto text-stone-300" />
        <div class="text-[14px] font-medium text-stone-600 mt-2">All caught up</div>
        <div class="text-[12px] text-stone-400 mt-0.5">No orders in your queue.</div>
      </div>

      <div v-else class="space-y-2.5">
        <button
          v-for="o in queue"
          :key="o.no"
          class="w-full text-start bg-white rounded-2xl ring-1 p-3.5 transition-all active:scale-[0.99]"
          :class="isUrgent(o) ? 'ring-rose-200' : 'ring-stone-200/70'"
          @click="openPick(o)"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2 min-w-0">
              <span class="font-mono text-[13px] font-bold text-stone-900 truncate">{{ o.no }}</span>
              <span
                class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap"
                :class="[SLA[o.sla].txt, SLA[o.sla].bg, SLA[o.sla].ring]"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="SLA[o.sla].dot" />
                {{ SLA_LABEL[o.sla] }}
              </span>
            </div>
            <span class="text-[13px] font-semibold text-stone-900 tabular-nums flex-shrink-0 ps-2">
              {{ fmtMAD(o.total) }} <span class="text-[10px] text-stone-400">MAD</span>
            </span>
          </div>
          <div class="flex items-center justify-between">
            <div class="min-w-0">
              <div class="text-[13.5px] font-medium text-stone-800 truncate">{{ o.customer }}</div>
              <div class="text-[11.5px] text-stone-500 mt-0.5 flex items-center gap-1.5">
                <Icon name="map-pin" :size="11" class="text-stone-400 flex-shrink-0" />{{ o.zone }}
              </div>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0 ps-2">
              <div class="text-end">
                <div class="text-[15px] font-bold text-stone-900 tabular-nums leading-none">{{ o.items }}</div>
                <div class="text-[9.5px] text-stone-400 uppercase">items</div>
              </div>
              <span class="w-9 h-9 rounded-full bg-stone-900 text-white flex items-center justify-center">
                <Icon name="arrow-right" :size="16" />
              </span>
            </div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { ORDERS as DEMO_ORDERS, SLA, SLA_LABEL, fmtMAD, byId } from "@/lib/handoffData";
import { api, liveOr } from "@/lib/resource";

const router = useRouter();

const me = byId("marouane");
const firstName = me.short;
const completedToday = 38;
const slaHit = 94;

// Live-or-demo orders. `orders.list` (queue scope) fills this once installed;
// falls back to the demo seed in local preview / on error.
const orders = ref(DEMO_ORDERS);

onMounted(async () => {
  const live = await liveOr(null, () => api("orders.list", { scope: "queue", limit: 40 }));
  if (live && live.length) orders.value = live;
});

// picker-relevant stages, most-urgent-first
const SLA_ORDER = { breached: 0, atrisk: 1, ontrack: 2, late: 2, returned: 3 };
const queue = computed(() =>
  orders.value
    .filter((o) => ["pending", "picking", "picked"].includes(o.stage))
    .filter((o) => !o.picker || o.picker === "marouane")
    .slice()
    .sort((a, b) => (SLA_ORDER[a.sla] - SLA_ORDER[b.sla]) || (a.mins - b.mins))
    .slice(0, 5)
);

const nextDue = computed(() => queue.value[0]?.mins ?? 0);

function isUrgent(o) {
  return o.sla === "breached" || o.sla === "atrisk";
}
function openPick(o) {
  router.push({ name: "PickMode", params: { id: o.no.replace("#", "") } });
}
</script>
