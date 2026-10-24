import { ref } from "vue";
import { explainError } from "@/lib/explainError";

// One French popup at a time for errors that stop work (see lib/explainError).
// Only SERVER messages come here: the client records each raw one as it
// arrives (resource.js), and a toast whose text carries it is diverted. The
// portal's own translated warnings stay toasts.
const current = ref(null);
let last = { msg: "", at: 0 };
const FRESH_MS = 20000;

export function recordServerError(msg, method) {
  last = { msg: String(msg || "").trim(), method: method || "", at: Date.now() };
}

/** The raw server message this text carries, if it came from the server just now. */
export function serverMessageIn(...texts) {
  if (!last.msg || last.msg.length < 6 || Date.now() - last.at > FRESH_MS) return "";
  const head = last.msg.slice(0, 120);
  return texts.some((t) => t && String(t).includes(head)) ? last.msg : "";
}

export function openErrorPopup(raw, context = "") {
  current.value = { raw: String(raw || ""), context: context || "", method: last.method,
                    at: new Date().toISOString().slice(0, 19).replace("T", " "),
                    ...explainError(raw) };
}

export function useErrorPopup() {
  return { current, close: () => { current.value = null; } };
}
