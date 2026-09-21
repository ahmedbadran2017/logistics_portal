/**
 * What the CS button is looking at right now.
 *
 * The handover lives in the app header, in the same place on every screen —
 * so it has to learn the order from the page underneath it rather than from
 * where it was clicked. A page showing one order publishes it here; the
 * button reads it, shows what it is about to hand over, and the agent never
 * retypes an order number they are already looking at.
 *
 * Cleared on every navigation. A stale order following the agent to the next
 * screen would file a complaint against the wrong customer, which is worse
 * than asking them to type it.
 */
import { ref } from "vue";

const ctx = ref({ order: "", phone: "", customer: "" });

export function setCsContext(order = "", phone = "", customer = "") {
  ctx.value = {
    order: String(order || "").trim(),
    phone: String(phone || "").trim(),
    customer: String(customer || "").trim(),
  };
}

export function clearCsContext() {
  ctx.value = { order: "", phone: "", customer: "" };
}

export function useCsContext() {
  return { csContext: ctx, setCsContext, clearCsContext };
}
