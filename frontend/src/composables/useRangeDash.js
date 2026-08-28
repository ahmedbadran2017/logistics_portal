// Shared engine for the personal dashboards (confirmation / cs / tracking):
// window math for the range chips, previous-window deltas, and the count-up
// animation. One place, three pages that must feel identical.
import { onUnmounted, ref, watch } from "vue";

export const RANGES = ["today", "yest", "7d", "month", "lastMonth"];
const day = 86400000;

const localIso = (dt) =>
  `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;

export function windowFor(key) {
  const now = new Date();
  if (key === "today") { const d0 = localIso(now); return [d0, d0]; }
  if (key === "yest") { const d0 = localIso(new Date(now.getTime() - day)); return [d0, d0]; }
  if (key === "7d") return [localIso(new Date(now.getTime() - 6 * day)), localIso(now)];
  if (key === "month") return [localIso(new Date(now.getFullYear(), now.getMonth(), 1)), localIso(now)];
  return [localIso(new Date(now.getFullYear(), now.getMonth() - 1, 1)),
          localIso(new Date(now.getFullYear(), now.getMonth(), 0))];
}

// The window right before the picked one, same length — the Δ chips' baseline.
export function prevWindowFor(key) {
  const now = new Date();
  if (key === "month") return windowFor("lastMonth");
  if (key === "lastMonth") {
    return [localIso(new Date(now.getFullYear(), now.getMonth() - 2, 1)),
            localIso(new Date(now.getFullYear(), now.getMonth() - 1, 0))];
  }
  const [f, t2] = windowFor(key);
  const len = Math.round((new Date(t2) - new Date(f)) / day) + 1;
  return [localIso(new Date(new Date(f).getTime() - len * day)),
          localIso(new Date(new Date(f).getTime() - day))];
}

// Δ vs the previous window. Rate-like values compare in points, counts in %.
export function deltaOf(cur, prev, isPts = false) {
  if (cur == null || prev == null || (!prev && !isPts)) return null;
  const d2 = isPts ? cur - prev : Math.round(((cur - prev) * 100) / prev);
  return { v: d2, up: d2 > 0, txt: (d2 > 0 ? "+" : "") + d2 + (isPts ? " pt" : "%") };
}

// The numbers roll to their value — no libraries, one cancellable RAF each.
export function useCountUp(target) {
  const shown = ref(0);
  let raf = 0;
  watch(target, (to) => {
    cancelAnimationFrame(raf);
    const from = shown.value;
    const t0 = performance.now();
    const step = (now2) => {
      const p2 = Math.min(1, (now2 - t0) / 800);
      const eased = 1 - Math.pow(1 - p2, 3);
      shown.value = Math.round(from + (to - from) * eased);
      if (p2 < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
  }, { immediate: true });
  onUnmounted(() => cancelAnimationFrame(raf));
  return shown;
}

export function fmtN(v) {
  return Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 0 });
}
