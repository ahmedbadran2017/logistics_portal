// Persist a ref to localStorage. Refs are cached per key so multiple
// components sharing the same key share state and don't leak watchers.
import { ref, watch } from "vue";

const cache = new Map();

export function usePersist(key, defaultValue) {
  if (cache.has(key)) return cache.get(key);

  let saved = null;
  try {
    const raw = localStorage.getItem(key);
    saved = raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn(`[usePersist] failed to read "${key}" — falling back to default`, e);
  }
  const r = ref(saved === null ? defaultValue : saved);

  watch(r, (v) => {
    try {
      localStorage.setItem(key, JSON.stringify(v));
    } catch (e) {
      // QuotaExceededError, circular JSON, private-mode restrictions, etc.
      console.warn(`[usePersist] failed to persist "${key}"`, e);
    }
  }, { deep: true });

  // Cross-tab sync — keep two tabs in step when one writes the same key.
  if (typeof window !== "undefined" && window.addEventListener) {
    window.addEventListener("storage", (ev) => {
      if (ev.key !== key) return;
      try {
        r.value = ev.newValue ? JSON.parse(ev.newValue) : defaultValue;
      } catch { /* ignore malformed cross-tab payloads */ }
    });
  }

  cache.set(key, r);
  return r;
}
