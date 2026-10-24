import { ref } from "vue";
import { openErrorPopup, serverMessageIn } from "@/composables/useErrorPopup";

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

// A server refusal in English becomes the French popup (useErrorPopup); the
// floor read "insufficient stock (45779757236478)" and forwarded it to a
// manager when the fix was one stock move away.
function explained(title, detail) {
  const raw = serverMessageIn(detail, title);
  if (!raw) return 0;
  openErrorPopup(raw, title);
  return -1;
}

export function useToast() {
  return {
    toasts,
    dismiss,
    success: (title, detail) => push({ severity: "success", title, detail }),
    info: (title, detail) => push({ severity: "info", title, detail }),
    warn: (title, detail) => explained(title, detail) || push({ severity: "warn", title, detail }),
    critical: (title, detail, action) => explained(title, detail)
      || push({ severity: "critical", title, detail, action, timeout: 0 }),
  };
}
