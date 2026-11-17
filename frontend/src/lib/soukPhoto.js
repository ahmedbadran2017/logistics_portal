// Souk photos from the buyer's phone. The market's connection is thin, so a
// photo is shrunk on the phone (longest side 1600 px, JPEG 0.8) before it
// leaves: a 4 MB shot becomes ~250 KB. Backend: souk.upload_photo.

function csrf() {
  return window.csrf_token || (window.frappe_boot && window.frappe_boot.csrf_token) || "";
}

export async function shrink(file, max = 1600) {
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
    c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
    URL.revokeObjectURL(url);
    const blob = await new Promise((ok) => c.toBlob(ok, "image/jpeg", 0.8));
    return blob ? new File([blob], (file.name || "photo").replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" }) : file;
  } catch (_) {
    return file;
  }
}

/** kind: ref | receipt | transport; target: product SKU, PO name or trip id. */
export async function uploadPhoto(kind, target, file) {
  const small = await shrink(file);
  const fd = new FormData();
  fd.append("kind", kind);
  fd.append("target", String(target));
  fd.append("file", small, small.name || "photo.jpg");
  const res = await fetch("/api/method/logistics_portal.api.souk.upload_photo", {
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
