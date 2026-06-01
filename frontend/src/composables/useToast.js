import { reactive } from "vue";

// Singleton store of active toasts
export const toasts = reactive([]);
let nextId = 1;
const MAX_TOASTS = 8; // cap so a runaway error loop can't spawn hundreds

export function useToast() {
  function show(opts) {
    const id = nextId++;
    const t = {
      id,
      type: opts.type || "info", // success | error | warning | info
      title: opts.title || "",
      message: opts.message || "",
      // duration: ms before auto-dismiss. Pass 0 or negative to make the toast sticky.
      duration: opts.duration ?? 5000,
      actions: opts.actions || [],
      // Structured safe links: [{ label, href }] — rendered without v-html.
      links: opts.links || [],
    };
    toasts.push(t);
    // Evict oldest when we exceed the cap.
    while (toasts.length > MAX_TOASTS) toasts.shift();
    if (t.duration > 0) {
      setTimeout(() => dismiss(id), t.duration);
    }
    return id;
  }
  function dismiss(id) {
    const i = toasts.findIndex((t) => t.id === id);
    if (i >= 0) toasts.splice(i, 1);
  }
  function success(title, message, opts = {}) { return show({ ...opts, type: "success", title, message }); }
  function error(title, message, opts = {})   { return show({ ...opts, type: "error", title, message, duration: 7000 }); }
  function warning(title, message, opts = {}) { return show({ ...opts, type: "warning", title, message }); }
  function info(title, message, opts = {})    { return show({ ...opts, type: "info", title, message }); }
  return { show, dismiss, success, error, warning, info };
}
