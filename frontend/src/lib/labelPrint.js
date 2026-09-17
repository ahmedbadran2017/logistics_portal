/**
 * Printing a parcel label, safely.
 *
 * The old path set `iframe.src = <label endpoint>` and called print() from
 * onload. When the endpoint answered with anything other than a PDF — and
 * Frappe answers a throw with a full HTML error page — the iframe loaded that
 * page happily, onload fired, and the station printed a Python traceback onto
 * thermal label stock, one roll at a time (2026-09-17, the sort wall).
 *
 * So the rule here is simple and absolute: FETCH first, check that what came
 * back is really a PDF, and only then print it, from a blob of the bytes we
 * already hold. Anything else prints nothing and says why on the screen.
 */

const FRAME_ID = "lp-print-frame";

function frame() {
  let f = document.getElementById(FRAME_ID);
  if (!f) {
    f = document.createElement("iframe");
    f.id = FRAME_ID;
    f.style.display = "none";
    document.body.appendChild(f);
  }
  return f;
}

/** The human sentence out of a Frappe error page, if it left one. */
function reasonFrom(text) {
  if (!text) return "";
  const m = text.match(/(?:ValidationError|PermissionError|Exception):\s*([^\n<]{3,160})/);
  if (m) return m[1].trim();
  try {
    const j = JSON.parse(text);
    const msgs = JSON.parse(j._server_messages || "[]");
    if (msgs.length) return String(JSON.parse(msgs[0]).message || "").slice(0, 160);
    // The endpoint answers a missing label as data, not as a thrown page.
    if (j.message && j.message.reason) return String(j.message.reason).slice(0, 160);
    if (typeof j.message === "string") return j.message.slice(0, 160);
  } catch { /* not JSON — fall through */ }
  return "";
}

/**
 * Print one parcel's carrier label.
 * @returns {Promise<{ok: boolean, reason?: string}>} — ok only when the job
 *          actually reached the browser's print pipeline.
 */
export async function printParcelLabel(order, { onSpooled } = {}) {
  if (!order) return { ok: false, reason: "no order" };
  const url = `/api/method/logistics_portal.api.picking.label_pdf?order=${encodeURIComponent(order)}`;
  let blobUrl = "";
  try {
    const res = await fetch(url, { credentials: "same-origin" });
    const type = (res.headers.get("content-type") || "").toLowerCase();
    if (!res.ok || !type.includes("pdf")) {
      let why = "";
      try { why = reasonFrom(await res.text()); } catch { /* body already gone */ }
      return { ok: false, reason: why || `HTTP ${res.status}` };
    }
    const blob = await res.blob();
    // Belt and braces: a proxy or a login redirect can answer 200 with the
    // right header and the wrong bytes. A PDF starts with %PDF.
    const head = new Uint8Array(await blob.slice(0, 5).arrayBuffer());
    if (String.fromCharCode(...head).indexOf("%PDF") !== 0) {
      return { ok: false, reason: "not a PDF" };
    }
    blobUrl = URL.createObjectURL(blob);
  } catch (e) {
    return { ok: false, reason: String(e.message || e) };
  }

  return new Promise((resolve) => {
    const f = frame();
    let settled = false;
    const finish = (r) => {
      if (settled) return;
      settled = true;
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
      resolve(r);
    };
    f.onload = () => {
      const w = f.contentWindow;
      try {
        if (onSpooled) {
          const done = () => { w.removeEventListener("afterprint", done); onSpooled(); };
          w.addEventListener("afterprint", done);
        }
        w.focus();
        w.print();
        finish({ ok: true });
      } catch (e) {
        finish({ ok: false, reason: String(e.message || e) });
      }
    };
    f.src = blobUrl;
    // A frame that never loads must not leave the caller waiting forever.
    setTimeout(() => finish({ ok: false, reason: "print timed out" }), 15000);
  });
}
