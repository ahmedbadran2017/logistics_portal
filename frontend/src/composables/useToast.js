import { ref } from "vue";

// Shared toast stack. Severity: critical (🔴) | warn (🟠) | info (🟡) | success
const toasts = ref([]);
let seq = 0;

function push(toast) {
  const id = ++seq;
  const t = { id, severity: "info", timeout: 4000, ...toast };
  toasts.value.push(t);
  // Critical alerts persist until acknowledged; others auto-dismiss.
  if (t.severity !== "critical" && t.timeout) {
    setTimeout(() => dismiss(id), t.timeout);
  }
  // Keep at most 3 visible; older collapse away.
  if (toasts.value.length > 3) toasts.value.shift();
  return id;
}
function dismiss(id) {
  toasts.value = toasts.value.filter((t) => t.id !== id);
}

export function useToast() {
  return {
    toasts,
    dismiss,
    success: (title, detail) => push({ severity: "success", title, detail }),
    info: (title, detail) => push({ severity: "info", title, detail }),
    warn: (title, detail) => push({ severity: "warn", title, detail }),
    critical: (title, detail, action) => push({ severity: "critical", title, detail, action, timeout: 0 }),
  };
}
