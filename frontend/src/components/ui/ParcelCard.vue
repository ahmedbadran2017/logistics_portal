<template>
  <div
    class="lp-card p-4 transition-all duration-150 active:scale-[.99]"
    :class="urgent ? 'border-danger/60' : 'hover:border-brand-400'"
    :style="urgent ? { borderInlineStartWidth: '4px', borderInlineStartColor: '#ef4444' } : {}"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <span class="font-bold text-content">{{ order.name || order.order }}</span>
          <span v-if="order.channel" class="caption">{{ order.channel }}</span>
        </div>
        <div class="text-sm text-content-2 truncate mt-0.5">{{ order.customer }}</div>
      </div>
      <StatusBadge v-if="order.stage" :value="order.stage" kind="stage" />
    </div>

    <div class="flex items-center gap-4 mt-3 text-sm text-content-3">
      <span class="tabular">{{ order.items }} items</span>
      <span class="tabular font-semibold text-content-2">{{ mad(order.total) }}</span>
    </div>

    <div v-if="order.sla" class="mt-3">
      <SlaMeter :status="order.sla" :remaining="order.remaining" :ratio="order.ratio ?? 1" />
    </div>

    <button v-if="action" class="btn-primary w-full mt-4" @click="$emit('action', order)">
      <Icon :name="actionIcon" :size="18" /> {{ action }}
    </button>
  </div>
</template>

<script setup>
import Icon from "./Icon.vue";
import StatusBadge from "./StatusBadge.vue";
import SlaMeter from "./SlaMeter.vue";
import { mad } from "@/lib/resource";

defineProps({
  order: { type: Object, required: true },
  action: String,
  actionIcon: { type: String, default: "package" },
  urgent: Boolean,
});
defineEmits(["action"]);
</script>
