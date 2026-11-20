"""Souk web pack: the in-house photos → clean website photos (Ahmed, 2026-11-19).

The rule: the product is NEVER redrawn. A photo that is prettier than the
goods comes back as a return. So the only thing an outside model does is the
cut-out (a background-removal model returns the original pixels with a new
alpha channel); everything else is plain image arithmetic done here, the same
way for every product:

    raw photo ─(EXIF upright, ≤2048 px)─▶ provider: remove background (PNG)
              ─▶ trim to the product ─▶ gentle levels (tone kept)
              ─▶ centred on a white 2048² square, 8 % margin, soft contact shadow
              ─▶ JPEG, attached to the card as a SUGGESTION

Suggestions are not finals. Marketing accepts (→ finals_json, then the normal
studio_send to the Shopify Draft), regenerates or rejects each one; nothing
reaches Shopify that a person did not accept.

When it runs: photos_send (floor → studio) queues the angles that matter for
the website — front, back, side — when the pack is enabled and set to auto.
Any other photo (detail, in hand, extras) is done on request from the studio
screen.

Off until the manager enables it in /souk/settings and saves the provider key
there (stored encrypted, never returned to a browser). A monthly image cap
stops the spend; every image counts, a failed one too (the provider bills
the attempt).
"""

import base64
import io
import json

import frappe
import requests
from frappe.utils import cint, now_datetime

from logistics_portal.api import souk as S

KEY_DT, KEY_NAME, KEY_FIELD = "LP Souk Settings", "ai", "fal_key"
USAGE_KEY = "lp_souk_ai_usage"
FIELD = "ai_json"

# The cut-out models we allow, cheapest last. Price per image, USD, as the
# provider listed it on 2026-11-19 (birefnet bills compute seconds: ~1 s).
MODELS = {
    "bria/rmbg-3": {"label": "Bria RMBG 3.0", "usd": 0.018},
    "fal-ai/birefnet/v2": {"label": "BiRefNet v2", "usd": 0.001},
}
DEFAULTS = {"enabled": False, "auto": True, "model": "bria/rmbg-3", "monthlyCap": 300}
AUTO_SLOTS = ("front", "back", "side")

SEND_EDGE = 2048        # longest edge sent to the provider
CANVAS = 2048           # Shopify square
MARGIN = 0.08           # white space around the product, each side
JPEG_Q = 90
LEVELS = 0.3          # how much of the auto-levels to apply (0 = none)
MAX_SHIFT = 6         # most the product's mean colour may move, per channel (of 255)
HTTP_TIMEOUT = 120
JOB_TIMEOUT = 1800


# --- config ------------------------------------------------------------------

def cfg(s=None):
    raw = (s or S.settings()).get("aiWebPack")
    out = dict(DEFAULTS)
    if isinstance(raw, dict):
        out.update({k: raw[k] for k in DEFAULTS if k in raw})
    if out["model"] not in MODELS:
        out["model"] = DEFAULTS["model"]
    return out


def clean_cfg(v):
    """What /souk/settings may save under aiWebPack."""
    if not isinstance(v, dict):
        frappe.throw("Bad web pack settings.")
    model = str(v.get("model") or DEFAULTS["model"])
    if model not in MODELS:
        frappe.throw("Unknown background-removal model.")
    return {"enabled": bool(v.get("enabled")), "auto": bool(v.get("auto", True)), "model": model,
            "monthlyCap": S._as_int(v.get("monthlyCap"), "The monthly image cap", 0, 100000)}


def api_key():
    from frappe.utils.password import get_decrypted_password
    return (get_decrypted_password(KEY_DT, KEY_NAME, KEY_FIELD, raise_exception=False)
            or frappe.conf.get("souk_fal_key") or "")


@frappe.whitelist(methods=["POST"])
def save_key(key="", clear=0):
    """Manager only. The key is written encrypted and never read back."""
    if S._role() != "manager":
        frappe.throw("Only a manager sets the provider key.", frappe.PermissionError)
    from frappe.utils.password import delete_all_passwords_for, set_encrypted_password
    if cint(clear):
        delete_all_passwords_for(KEY_DT, KEY_NAME)
    else:
        key = (key or "").strip()
        if len(key) < 20 or " " in key:
            frappe.throw("That does not look like a provider key.")
        set_encrypted_password(KEY_DT, KEY_NAME, key, KEY_FIELD)
    frappe.db.commit()
    return {"keySet": bool(api_key())}


def _month():
    return str(now_datetime())[:7]


def usage():
    try:
        u = json.loads(frappe.db.get_default(USAGE_KEY) or "{}")
    except ValueError:
        u = {}
    return cint(u.get(_month())) if isinstance(u, dict) else 0


def _count(n=1):
    try:
        u = json.loads(frappe.db.get_default(USAGE_KEY) or "{}")
    except ValueError:
        u = {}
    if not isinstance(u, dict):
        u = {}
    m = _month()
    u = {k: v for k, v in u.items() if k >= str(int(m[:4]) - 1) + m[4:]}   # a year of history
    u[m] = cint(u.get(m)) + n
    frappe.db.set_default(USAGE_KEY, json.dumps(u))


def settings_block():
    """What the settings screen shows about the pack."""
    c = cfg()
    return {"keySet": bool(api_key()), "used": usage(), "month": _month(),
            "models": [{"id": k, "label": v["label"], "usd": v["usd"]} for k, v in MODELS.items()],
            "slots": list(AUTO_SLOTS), "config": c}


def _why_not():
    """'' when the pack can run, else the reason the studio screen shows."""
    if not S._has_col(S.DT_PRODUCT, FIELD):
        return "migrate"
    c = cfg()
    if not c["enabled"]:
        return "off"
    if not api_key():
        return "key"
    if c["monthlyCap"] and usage() >= c["monthlyCap"]:
        return "cap"
    return ""


# --- the card's state ----------------------------------------------------------

def _state(doc):
    st = S._loads(doc.get(FIELD)) if S._has_col(S.DT_PRODUCT, FIELD) else None
    if not isinstance(st, dict):
        st = {}
    st.setdefault("state", "")
    st.setdefault("items", [])
    st.setdefault("todo", [])
    return st


def _save(doc, st):
    doc.db_set(FIELD, json.dumps(st, ensure_ascii=False), update_modified=False)


def block(doc):
    """The studio screen's view of the pack for one card."""
    st = _state(doc)
    c = cfg()
    why = _why_not()
    raws = {p.get("url") for p in (S._loads(doc.photos_json) or [])}
    return {
        "state": st["state"], "error": st.get("error") or "", "at": st.get("at") or "",
        "todo": [u for u in st["todo"] if u in raws], "failed": st.get("failed") or [],
        "items": [i for i in st["items"] if i.get("src") in raws],
        "ready": not why, "why": why, "auto": c["auto"], "autoSlots": list(AUTO_SLOTS),
        "usd": MODELS[c["model"]]["usd"], "used": usage(), "cap": c["monthlyCap"],
    }


def _queue(name, srcs, by):
    doc = S._lock_product(name)
    st = _state(doc)
    todo = list(dict.fromkeys(st["todo"] + srcs))
    st.update({"state": "queued", "todo": todo, "error": "", "by": by, "at": str(now_datetime())[:16],
               "failed": [f for f in (st.get("failed") or []) if f.get("src") not in srcs]})
    _save(doc, st)
    frappe.db.commit()
    frappe.enqueue("logistics_portal.api.souk_ai.run", queue="long", timeout=JOB_TIMEOUT,
                   job_id=f"souk-ai-{name}", deduplicate=True, enqueue_after_commit=True, name=name)


def auto_start(name):
    """photos_send's hook. Never blocks the floor: any problem is logged."""
    try:
        if _why_not() or not cfg()["auto"]:
            return
        doc = frappe.get_doc(S.DT_PRODUCT, name)
        srcs = [p["url"] for p in (S._loads(doc.photos_json) or []) if p.get("slot") in AUTO_SLOTS]
        if srcs:
            _queue(name, srcs, frappe.session.user)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:3000], f"souk_ai.auto_start {name}")


def clear(doc):
    """Card leaves the studio (sent back, or finals sent): drop the
    suggestions nobody accepted, and their files."""
    if not S._has_col(S.DT_PRODUCT, FIELD):
        return
    st = _state(doc)
    finals = {f.get("url") for f in (S._loads(doc.get("finals_json")) or [])}
    S._drop_files(doc.name, [i["url"] for i in st["items"] if i.get("url") not in finals])
    _save(doc, {"state": "", "items": [], "todo": []})


# --- the studio's buttons -------------------------------------------------------

def _studio_card(name):
    S._gate_studio()
    doc = S._lock_product(name)
    if doc.stage != "studio":
        frappe.throw("This product is not with marketing.")
    return doc


@frappe.whitelist(methods=["POST"])
def start(name, srcs=None):
    """Make (or remake) the web version of these in-house photos; none given
    = the website angles (front, back, side)."""
    doc = _studio_card(name)
    why = _why_not()
    if why:
        frappe.throw({"off": "The web pack is switched off in Settings.",
                      "key": "The provider key is not set in Settings.",
                      "cap": "This month's image cap is reached (Settings).",
                      "migrate": "The site needs its migrate first."}[why])
    want = json.loads(srcs) if isinstance(srcs, str) and srcs.startswith("[") else (srcs or [])
    raws = S._loads(doc.photos_json) or []
    urls = {p["url"] for p in raws}
    want = [u for u in want if u in urls] or [p["url"] for p in raws if p.get("slot") in AUTO_SLOTS]
    if not want:
        frappe.throw("No in-house photo to work from.")
    _queue(doc.name, want, frappe.session.user)
    return S._studio_detail(doc.name)


@frappe.whitelist(methods=["POST"])
def accept(name, urls):
    """Suggestions → finals, in the order given, each tied to its colour."""
    want = json.loads(urls) if isinstance(urls, str) else (urls or [])
    doc = _studio_card(name)
    st = _state(doc)
    by_url = {i["url"]: i for i in st["items"]}
    pick = [by_url[u] for u in want if u in by_url]
    if not pick:
        frappe.throw("Nothing to accept — reload.")
    finals = S._loads(doc.finals_json) or []
    if len(finals) + len(pick) > S.MAX_FINALS:
        frappe.throw(f"{S.MAX_FINALS} final photos at most.")
    who = S._user_name(frappe.session.user)
    for i in pick:
        finals.append({"url": i["url"], "color": i.get("color") or "", "by": who,
                       "at": str(now_datetime())[:16], "ai": 1, "src": i.get("src")})
    st["items"] = [i for i in st["items"] if i["url"] not in {p["url"] for p in pick}]
    doc.db_set("finals_json", json.dumps(finals, ensure_ascii=False), update_modified=False)
    _save(doc, st)
    frappe.db.commit()
    return S._studio_detail(doc.name)


@frappe.whitelist(methods=["POST"])
def reject(name, url):
    doc = _studio_card(name)
    st = _state(doc)
    if url not in {i["url"] for i in st["items"]}:
        frappe.throw("Suggestion not found — reload.")
    st["items"] = [i for i in st["items"] if i["url"] != url]
    _save(doc, st)
    S._drop_files(doc.name, [url])
    frappe.db.commit()
    return S._studio_detail(doc.name)


@frappe.whitelist()
def poll(name):
    """The studio screen asks every few seconds while a job works. A todo
    with no job behind it (a worker restart, or a request that landed just
    as the last job finished) is queued again here."""
    S._gate_studio()
    from frappe.utils.background_jobs import is_job_enqueued
    doc = frappe.get_doc(S.DT_PRODUCT, name)
    st = _state(doc)
    if (doc.stage == "studio" and st["todo"] and st["state"] in ("queued", "running")
            and not _why_not() and not is_job_enqueued(f"souk-ai-{name}")):
        frappe.enqueue("logistics_portal.api.souk_ai.run", queue="long", timeout=JOB_TIMEOUT,
                       job_id=f"souk-ai-{name}", deduplicate=True, name=name)
    return S._studio_detail(name)


# --- the job ------------------------------------------------------------------

def run(name):
    """Works the card's todo list one photo at a time; each result is saved
    as soon as it exists, so the screen fills in while the job runs."""
    while True:
        doc = S._lock_product(name)
        st = _state(doc)
        if doc.stage != "studio" or not st["todo"]:
            st["state"] = "done" if st["items"] or not st.get("failed") else "error"
            st["todo"] = [] if doc.stage != "studio" else st["todo"]
            _save(doc, st)
            frappe.db.commit()
            return
        why = _why_not()
        if why:
            st.update({"state": "error", "error": why, "todo": []})
            _save(doc, st)
            frappe.db.commit()
            return
        src = st["todo"][0]
        st["state"] = "running"
        _save(doc, st)
        frappe.db.commit()          # releases the row lock while the provider works

        raw = next((p for p in (S._loads(doc.photos_json) or []) if p.get("url") == src), None)
        item, err = None, ""
        if raw:
            try:
                out = _web_version(src)
                fdoc = S._insert_file("web", S.DT_PRODUCT, name, out, "jpg")
                item = {"url": fdoc.file_url, "src": src, "color": raw.get("color") or "",
                        "slot": raw.get("slot"), "model": cfg()["model"], "at": str(now_datetime())[:16]}
            except Exception as e:
                err = str(e)[:300] or e.__class__.__name__
                frappe.log_error(frappe.get_traceback()[:3000], f"souk_ai.run {name}")
            finally:
                _count()

        doc = S._lock_product(name)
        st = _state(doc)
        st["todo"] = [u for u in st["todo"] if u != src]
        if item:
            old = [i["url"] for i in st["items"] if i.get("src") == src]
            st["items"] = [i for i in st["items"] if i.get("src") != src] + [item]
            S._drop_files(name, old)
        elif raw:
            st["failed"] = [f for f in (st.get("failed") or []) if f.get("src") != src] + [{"src": src, "error": err}]
        _save(doc, st)
        frappe.db.commit()


def _file_bytes(url):
    fname = frappe.db.get_value("File", {"file_url": url}, "name")
    if not fname:
        raise Exception("the in-house photo file is gone")
    return frappe.get_doc("File", fname).get_content()


def _web_version(src_url):
    from PIL import Image, ImageOps

    im = Image.open(io.BytesIO(_file_bytes(src_url)))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((SEND_EDGE, SEND_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    cut = _remove_background(buf.getvalue())
    return compose(cut)


def _remove_background(jpeg):
    key = api_key()
    model = cfg()["model"]
    uri = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
    r = requests.post(f"https://fal.run/{model}", json={"image_url": uri},
                      headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                      timeout=HTTP_TIMEOUT)
    if r.status_code >= 400:
        raise Exception(f"provider answered {r.status_code}: {r.text[:200]}")
    url = ((r.json() or {}).get("image") or {}).get("url")
    if not url:
        raise Exception("provider returned no image")
    if url.startswith("data:"):
        return base64.b64decode(url.split(",", 1)[1])
    g = requests.get(url, timeout=HTTP_TIMEOUT)
    g.raise_for_status()
    return g.content


def compose(cutout_png):
    """Cut-out → the house look. Pure arithmetic: the product's pixels are
    only resized and their levels stretched (hue kept)."""
    from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat

    im = Image.open(io.BytesIO(cutout_png)).convert("RGBA")
    alpha = im.getchannel("A")
    box = alpha.point(lambda v: 255 if v > 10 else 0).getbbox()
    if not box:
        raise Exception("the cut-out is empty (no product found)")
    im = im.crop(box)
    alpha = im.getchannel("A")
    # Levels from the product's own pixels only, blended in at LEVELS:
    # a dull phone shot gets lifted, but a colour never moves far — a
    # "red" that turns into another red is a return.
    base = im.convert("RGB")
    solid = alpha.point(lambda v: 255 if v > 200 else 0)
    try:
        stretched = ImageOps.autocontrast(base, cutoff=0.5, mask=solid, preserve_tone=True)
    except TypeError:
        stretched = ImageOps.autocontrast(base, cutoff=0.5)
    # Hard ceiling: the product's average colour may move MAX_SHIFT at most
    # on any channel; a flat or single-colour product gets less (or none).
    m0 = ImageStat.Stat(base, solid).mean
    m1 = ImageStat.Stat(stretched, solid).mean
    worst = max(abs(x - y) for x, y in zip(m0, m1)) if m0 and m1 else 0
    k = LEVELS if worst * LEVELS <= MAX_SHIFT else MAX_SHIFT / worst
    rgb = Image.blend(base, stretched, k)
    im = Image.merge("RGBA", (*rgb.split(), alpha))

    inner = CANVAS * (1 - 2 * MARGIN)
    scale = min(inner / im.width, inner / im.height)
    w, h = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    im = im.resize((w, h), Image.LANCZOS)
    x = (CANVAS - w) // 2
    # Sit a little high: the shadow needs the room under the product.
    y = max(0, (CANVAS - h) // 2 - round(CANVAS * 0.015))

    canvas = Image.new("RGB", (CANVAS, CANVAS), (255, 255, 255))
    shadow = Image.new("L", (CANVAS, CANVAS), 0)
    sw, sh = w * 0.42, max(CANVAS * 0.012, h * 0.035)
    cx, cy = x + w / 2, y + h - sh * 0.35
    ImageDraw.Draw(shadow).ellipse((cx - sw, cy - sh, cx + sw, cy + sh), fill=70)
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(6, sh * 0.9)))
    canvas.paste((40, 40, 40), mask=shadow)
    canvas.paste(im, (x, y), im)

    out = io.BytesIO()
    canvas.save(out, "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
    return out.getvalue()
