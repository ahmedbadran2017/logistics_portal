<template>
  <span>{{ display }}</span>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from "vue";

const props = defineProps({
  value: { type: [Number, String], required: true },
  duration: { type: Number, default: 900 },
  decimals: { type: Number, default: 0 },
  prefix: { type: String, default: "" },
  suffix: { type: String, default: "" },
});

const display = ref("");
let raf = null;

function animate(from, to) {
  if (raf) cancelAnimationFrame(raf);
  const start = performance.now();
  const dur = props.duration;
  const fmt = (v) => {
    const n = Number(v);
    if (isNaN(n)) return props.prefix + "—" + props.suffix;
    return props.prefix + n.toLocaleString("en-US", {
      minimumFractionDigits: props.decimals,
      maximumFractionDigits: props.decimals,
    }) + props.suffix;
  };
  const step = (t) => {
    const p = Math.min(1, (t - start) / dur);
    const eased = 1 - Math.pow(1 - p, 3); // ease-out cubic
    const cur = from + (to - from) * eased;
    display.value = fmt(cur);
    if (p < 1) raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
}

watch(() => props.value, (n, o) => {
  const to = Number(n);
  const from = Number(o ?? 0);
  if (isNaN(to)) { display.value = props.prefix + "—" + props.suffix; return; }
  animate(isNaN(from) ? 0 : from, to);
});

onMounted(() => {
  const n = Number(props.value);
  if (isNaN(n)) { display.value = props.prefix + "—" + props.suffix; return; }
  animate(0, n);
});

onBeforeUnmount(() => { if (raf) cancelAnimationFrame(raf); });
</script>
