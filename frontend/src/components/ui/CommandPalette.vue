<template>
  <div v-if="open" class="fixed inset-0 z-[130] flex items-start justify-center pt-[12vh] px-4">
    <!-- backdrop -->
    <div class="absolute inset-0 bg-stone-900/25 backdrop-blur-sm animate-fade-in" @click="close" />

    <!-- panel -->
    <div
      class="relative w-full max-w-[560px] bg-white rounded-2xl shadow-floating ring-1 ring-stone-200/70 overflow-hidden animate-scale-in"
    >
      <!-- search field -->
      <div class="flex items-center gap-2.5 px-4 h-[52px] border-b border-stone-100">
        <Icon name="search" :size="16" class="text-stone-400 flex-shrink-0" />
        <input
          ref="inputEl"
          v-model="query"
          type="text"
          :placeholder="t('common.search')"
          class="flex-1 bg-transparent text-[14px] text-stone-900 placeholder:text-stone-400 outline-none"
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="run(active)"
          @keydown.esc.prevent="close"
        />
        <kbd class="inline-flex items-center h-[20px] px-1.5 text-[10.5px] font-medium text-stone-500 bg-stone-50 border border-stone-200/80 rounded-md">esc</kbd>
      </div>

      <!-- results -->
      <div class="max-h-[52vh] overflow-y-auto py-2">
        <template v-for="(grp, gi) in groups" :key="grp.label">
          <div v-if="grp.items.length" :class="gi > 0 ? 'mt-1' : ''">
            <div class="px-4 py-1 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-stone-400">
              {{ grp.label }}
            </div>
            <button
              v-for="item in grp.items"
              :key="item.id"
              type="button"
              class="w-full flex items-center gap-3 px-3 mx-1 py-2 rounded-lg text-start"
              style="width: calc(100% - 0.5rem)"
              :class="active === item.id ? 'bg-[var(--accent-50)]' : 'hover:bg-stone-50'"
              @click="run(item.id)"
              @mousemove="active = item.id"
            >
              <span
                class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                :class="active === item.id ? 'bg-white text-[var(--accent-700)] ring-1 ring-stone-200' : 'bg-stone-100 text-stone-500'"
              >
                <Icon :name="item.icon" :size="14" />
              </span>
              <div class="min-w-0 flex-1">
                <div class="text-[13px] font-medium text-stone-900 truncate">{{ item.title }}</div>
                <div v-if="item.sub" class="text-[11px] text-stone-500 truncate font-mono">{{ item.sub }}</div>
              </div>
              <Icon
                v-if="active === item.id"
                name="corner-down-left"
                :size="13"
                class="text-stone-400 flex-shrink-0"
              />
            </button>
          </div>
        </template>

        <div v-if="!flat.length" class="px-4 py-10 text-center text-[13px] text-stone-400">
          {{ t("common.allCaught", "No results") }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import Icon from "@/components/ui/Icon.vue";
import { useAuth } from "@/composables/useAuth";
import { useI18n } from "@/composables/useI18n";
import { navItemsFor } from "@/lib/roles";

const props = defineProps({ open: { type: Boolean, default: false } });
const emit = defineEmits(["close"]);

const router = useRouter();
const { role, hiddenPages } = useAuth();
const { t } = useI18n();

const query = ref("");
const active = ref("");
const inputEl = ref(null);

// A few demo orders so the palette matches AWB / order queries.
const DEMO_ORDERS = [
  { no: "#242638", awb: "LD007744422" },
  { no: "#240682", awb: "LD007748688" },
  { no: "#242128", awb: "AWB-51433" },
];

const pages = computed(() =>
  navItemsFor(role.value, hiddenPages.value).map((it, i) => ({
    id: `p-${i}`,
    kind: "page",
    to: it.to,
    icon: it.icon,
    title: t(it.label),
    sub: "",
  }))
);

const orders = computed(() =>
  DEMO_ORDERS.map((o, i) => ({
    id: `o-${i}`,
    kind: "order",
    to: "OrderDetail",
    param: o.no,
    icon: "shopping-bag",
    title: o.no,
    sub: o.awb,
  }))
);

function match(item, q) {
  if (!q) return true;
  return (item.title + " " + (item.sub || "")).toLowerCase().includes(q);
}

const filteredPages = computed(() => {
  const q = query.value.trim().toLowerCase();
  return pages.value.filter((p) => match(p, q));
});
const filteredOrders = computed(() => {
  const q = query.value.trim().toLowerCase();
  return orders.value.filter((o) => match(o, q));
});

const groups = computed(() => [
  { label: t("cmd.pages", "Pages"), items: filteredPages.value },
  { label: t("cmd.orders", "Orders"), items: filteredOrders.value },
]);

const flat = computed(() => [...filteredPages.value, ...filteredOrders.value]);

watch(flat, (list) => {
  if (!list.find((i) => i.id === active.value)) {
    active.value = list.length ? list[0].id : "";
  }
});

watch(
  () => props.open,
  async (v) => {
    if (v) {
      query.value = "";
      active.value = flat.value.length ? flat.value[0].id : "";
      await nextTick();
      inputEl.value?.focus();
    }
  }
);

function move(dir) {
  const list = flat.value;
  if (!list.length) return;
  const idx = list.findIndex((i) => i.id === active.value);
  const next = (idx + dir + list.length) % list.length;
  active.value = list[next].id;
}

function run(id) {
  const item = flat.value.find((i) => i.id === id);
  if (!item) return;
  if (item.kind === "order") {
    router.push({ name: "OrderDetail", params: { name: item.param } });
  } else {
    router.push({ name: item.to });
  }
  close();
}

function close() {
  emit("close");
}
</script>
