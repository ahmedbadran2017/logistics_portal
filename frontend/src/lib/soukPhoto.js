// Souk photos from a phone or a desk. The market's connection is thin, so a
// photo is shrunk before it leaves: a 4 MB shot becomes ~250 KB at 1600 px /
// JPEG 0.8. Marketing's finals go out at 2048 px / 0.9 — Shopify's own
// recommended size. Backend: souk.upload_photo, photo_add, final_add.

function csrf() {
  return window.csrf_token || (window.frappe_boot && window.frappe_boot.csrf_token) || "";
}

export async function shrink(file, max = 1600, quality = 0.8) {
  if (!file || !/^image\//.test(file.type || "")) return file;
  try {
    const url = URL.createObjectURL(file);
    const img = await new Promise((ok, ko) => {
      const i = new Image();
      i.onload = () => ok(i);
      i.onerror = ko;
      i.src = url;
    });
    const k = Math.min(1, max / Math.max(img.width, img.height));
    const c = document.createElement("canvas");
    c.width = Math.round(img.width * k);
    c.height = Math.round(img.height * k);
    const g = c.getContext("2d");
    // A transparent PNG would turn black in a JPEG: lay it on white.
    g.fillStyle = "#fff";
    g.fillRect(0, 0, c.width, c.height);
    g.drawImage(img, 0, 0, c.width, c.height);
    URL.revokeObjectURL(url);
    const blob = await new Promise((ok) => c.toBlob(ok, "image/jpeg", quality));
    return blob ? new File([blob], (file.name || "photo").replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" }) : file;
  } catch (_) {
    return file;
  }
}

/** POST one photo with form fields to a souk method; returns its message.
 *  `method` is a souk.py name ("upload_photo") or a module path
 *  ("souk_scout.visit_photo"). */
export async function postPhoto(method, fields, file, { max = 1600, quality = 0.8 } = {}) {
  const small = await shrink(file, max, quality);
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields || {})) fd.append(k, String(v ?? ""));
  fd.append("file", small, small.name || "photo.jpg");
  const path = method.includes(".") ? method : "souk." + method;
  const res = await fetch("/api/method/logistics_portal.api." + path, {
    method: "POST",
    credentials: "include",
    headers: { "X-Frappe-CSRF-Token": csrf(), "X-Requested-With": "XMLHttpRequest" },
    body: fd,
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = "HTTP " + res.status;
    try {
      const sm = j._server_messages ? JSON.parse(j._server_messages) : null;
      if (sm && sm.length) msg = JSON.parse(sm[0]).message || msg;
    } catch (_) { /* keep the status */ }
    throw new Error(msg);
  }
  return j.message;
}

/** kind: ref | receipt | transport | broken; target: product SKU, PO name or trip id. */
export function uploadPhoto(kind, target, file) {
  return postPhoto("upload_photo", { kind, target }, file);
}
