<template>
  <div class="lp-card overflow-hidden">
    <!-- Desktop table -->
    <div class="hidden sm:block overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-border">
            <th
              v-for="col in columns"
              :key="col.key"
              class="text-start px-4 py-3 caption select-none"
              :class="col.sortable ? 'cursor-pointer hover:text-content-2' : ''"
              @click="col.sortable && sortBy(col.key)"
            >
              {{ col.label }}
              <span v-if="sort.key === col.key">{{ sort.dir === 'asc' ? '↑' : '↓' }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="n in 5" :key="n" class="border-b border-border/60">
              <td v-for="col in columns" :key="col.key" class="px-4 py-3"><div class="skeleton h-4 w-full" /></td>
            </tr>
          </template>
          <tr
            v-for="(row, i) in sortedRows"
            v-else
            :key="row[rowKey] || i"
            class="border-b border-border/60 hover:bg-card2 transition-colors"
            :class="rowClickable ? 'cursor-pointer' : ''"
            @click="rowClickable && $emit('row', row)"
          >
            <td v-for="col in columns" :key="col.key" class="px-4 py-3 text-content-2"
                :class="col.numeric ? 'tabular text-end' : ''">
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">{{ row[col.key] }}</slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Mobile: rows collapse into cards via the #card slot -->
    <div class="sm:hidden divide-y divide-border">
      <div v-for="(row, i) in sortedRows" :key="row[rowKey] || i" class="p-4" @click="rowClickable && $emit('row', row)">
        <slot name="card" :row="row" />
      </div>
    </div>

    <EmptyState
      v-if="!loading && !rows.length"
      v-bind="empty"
    />
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import EmptyState from "./EmptyState.vue";

const props = defineProps({
  columns: { type: Array, required: true }, // [{key,label,sortable,numeric}]
  rows: { type: Array, default: () => [] },
  rowKey: { type: String, default: "name" },
  loading: Boolean,
  rowClickable: Boolean,
  empty: { type: Object, default: () => ({ title: "Nothing here yet" }) },
});
defineEmits(["row"]);

const sort = ref({ key: null, dir: "asc" });
function sortBy(key) {
  if (sort.value.key === key) sort.value.dir = sort.value.dir === "asc" ? "desc" : "asc";
  else sort.value = { key, dir: "asc" };
}
const sortedRows = computed(() => {
  if (!sort.value.key) return props.rows;
  const k = sort.value.key, dir = sort.value.dir === "asc" ? 1 : -1;
  return [...props.rows].sort((a, b) => (a[k] > b[k] ? dir : a[k] < b[k] ? -dir : 0));
});
</script>
