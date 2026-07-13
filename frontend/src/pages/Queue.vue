<template>
  <div class="min-h-full bg-stone-50">
    <div class="px-4 py-3.5 space-y-3.5">
      <!-- Greeting -->
      <div class="leading-tight">
        <div class="text-[11px] text-stone-500">{{ t("queue.hi") }}</div>
        <div class="text-[16px] font-semibold text-stone-900">{{ firstName }}</div>
      </div>

      <!-- stat chips — all real -->
      <div class="grid grid-cols-3 gap-2">
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
          <div class="text-[19px] font-semibold tabular-nums leading-none text-stone-900">{{ todayCount }}</div>
          <div class="text-[10px] text-stone-500 mt-1 leading-tight">{{ t("queue.today") }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
          <div class="text-[19px] font-semibold tabular-nums leading-none text-[var(--accent-600)]">{{ queue.length }}</div>
          <div class="text-[10px] text-stone-500 mt-1 leading-tight">{{ t("queue.waiting") }}</div>
        </div>
        <div class="bg-white rounded-xl ring-1 ring-stone-200/70 px-3 py-2.5 text-center">
          <div class="text-[19px] font-semibold tabular-nums leading-none" :class="oldestMins > 120 ? 'text-rose-600' : 'text-amber-600'">
            {{ oldestLabel }}
          </div>
          <div class="text-[10px] text-stone-500 mt-1 leading-tight">{{ t("queue.oldest") }}</div>
        </div>
      </div>

      <!-- title -->
      <div class="flex items-center justify-between pt-1">
        <h2 class="text-[15px] font-semibold text-stone-900">{{ t("queue.title") }}</h2>
        <span class="text-[11px] text-stone-500">{{ t("queue.orderHint") }}</span>
      </div>

      <!-- loading -->
      <div v-if="loading" class="space-y-2.5">
        <div v-for="n in 3" :key="n" class="h-[86px] rounded-2xl ring-1 ring-stone-200/60 bg-white animate-pulse" />
      </div>

      <!-- empty -->
      <div v-else-if="!queue.length" class="text-center py-10 text-stone-400">
        <Icon name="check-circle" :size="32" class="mx-auto text-stone-300" />
        <div class="text-[14px] font-medium text-stone-600 mt-2">{{ t("queue.emptyTitle") }}</div>
        <div class="text-[12px] text-stone-400 mt-0.5">{{ t("queue.emptyBody") }}</div>
      </div>

      <!-- queue: the picker's draft pick lists, oldest first -->
      <div v-else class="space-y-2.5">
        <button
          v-for="pl in queue"
          :key="pl.pick_list"
          class="w-full text-start bg-white rounded-2xl ring-1 p-3.5 transition-all active:scale-[0.99]"
          :class="ageMins(pl) > 120 ? 'ring-rose-200' : 'ring-stone-200/70'"
          @click="openPick(pl)"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2 min-w-0">
              <span class="font-mono text-[13px] font-bold text-stone-900 truncate">{{ pl.pick_list }}</span>
              <span v-if="pl.orders > 1"
                class="inline-flex items-center px-1.5 py-0.5 rounded-md text-[10px] font-semibold ring-1 whitespace-nowrap text-violet-700 bg-violet-50 ring-violet-200/60">
                {{ pl.orders }} {{ t("ordersPg.blOrders") }}
              </span>
            </div>
            <span class="text-[11px] text-stone-400 tabular-nums flex-shrink-0 ps-2">{{ fmtAge(ageMins(pl)) }}</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="min-w-0">
              <div class="text-[13.5px] font-medium text-stone-800 truncate">{{ pl.customer }}</div>
              <div class="text-[11.5px] text-stone-500 mt-0.5">{{ pl.qty }} {{ t("queue.pieces") }}</div>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0 ps-2">
              <div class="text-end">
                <div class="text-[15px] font-bold text-stone-900 tabular-nums leading-none">{{ pl.items }}</div>
                <div class="text-[9.5px] text-stone-400 uppercase">{{ t("queue.lines") }}</div>
              </div>
              <span class="w-9 h-9 rounded-full bg-stone-900 text-white flex items-center justify-center">
                <Icon name="arrow-right" :size="16" class="rtl:rotate-180" />
              </span>
            </div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { api } from "@/lib/resource";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";

const router = useRouter();
const { t } = useI18n();
const { fullName } = useAuth();

const firstName = computed(() => (fullName.value || "").split(" ")[0] || "");
const queue = ref([]);
const todayCount = ref(0);
const loading = ref(true);
const nowMs = ref(Date.now());

onMounted(async () => {
  try {
    const [q, me] = await Promise.all([
      api("picking.my_queue"),
      api("performance.me").catch(() => null),
    ]);
    queue.value = Array.isArray(q) ? q : [];
    todayCount.value = Number(me?.todayCount) || 0;
  } finally {
    loading.value = false;
  }
  setInterval(() => (nowMs.value = Date.now()), 30000);
});

function ageMins(pl) {
  const created = new Date(String(pl.created).replace(" ", "T"));
  return Math.max(0, Math.round((nowMs.value - created.getTime()) / 60000));
}
function fmtAge(m) {
  if (m < 60) return `${m}m`;
  if (m < 1440) return `${Math.floor(m / 60)}h`;
  return `${Math.floor(m / 1440)}d`;
}
const oldestMins = computed(() => (queue.value.length ? ageMins(queue.value[0]) : 0));
const oldestLabel = computed(() => (queue.value.length ? fmtAge(oldestMins.value) : "—"));

function openPick(pl) {
  router.push({ name: "PickMode", params: { id: pl.pick_list } });
}
</script>
