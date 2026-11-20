"""Souk content writer: the product page written by Claude (Ahmed, 2026-11-20).

The content step used to start from a fixed template ("Draft for me", no AI),
which gave pages like «مطبخ — Stanley bottle». Here one model call reads the
product's FINAL photos (the ones going to Shopify) plus a few floor shots
that show labels and sizes, and the facts the cycle already holds (category,
house brand, colours, sizes, the floor's specs, weights), and returns:

    French title + description   (the storefront's language)
    Arabic title + description   (the shop's translation; MSA or Darija, a setting)
    SEO title + description, tags
    verify[]                     claims the writer must check on the goods

Same rule as the photos: a page prettier than the goods comes back as a
return. The prompt forbids anything not visible or recorded, and every
guess goes to `verify` instead of the page. Third-party brands and logos are
never named (the shop sells under its house brands).

Nothing is written onto the card by the job. The result waits in the cache
(a day); the content screen shows it and the writer applies it to the
fields, edits, and sends to review as before — review still checks it.

Uses the server's Anthropic key (site_config `anthropic_api_key`, the same
one the Audit digest uses) and the `anthropic` SDK already on the bench.
Off until the manager enables it in /souk/settings. Product photos go to
Anthropic only when a writer presses the button.
"""

import base64
import io
import json
import re

import frappe
from frappe.utils import cint, flt, now_datetime

from logistics_portal.api import souk as S

USAGE_KEY = "lp_souk_write_usage"
CACHE_KEY = "souk-write:{}"
CACHE_TTL = 86400
JOB_TIMEOUT = 600

# USD per million tokens (input, output), from the Anthropic price list
# (2026-11). `usd` = a typical product (6 photos, thinking at medium effort).
MODELS = {
    "claude-opus-5-5": {"label": "Claude Opus 5.5", "in": 4.0, "out": 20.0, "usd": 0.10},
    "claude-sonnet-5-5": {"label": "Claude Sonnet 5.5", "in": 2.0, "out": 10.0, "usd": 0.05},
}
DEFAULTS = {"enabled": False, "model": "claude-opus-5-5", "arabic": "msa", "monthlyCap": 300}
ARABIC = ("msa", "darija")

IMG_EDGE = 1024          # longest edge sent; enough to read a label
MAX_FINALS = 4
MAX_FLOOR = 2            # extra floor shots that tend to show text and scale
FLOOR_SLOTS = ("detail", "size", "label", "hand")


# --- config ------------------------------------------------------------------

def cfg(s=None):
    raw = (s or S.settings()).get("aiContent")
    out = dict(DEFAULTS)
    if isinstance(raw, dict):
        out.update({k: raw[k] for k in DEFAULTS if k in raw})
    if out["model"] not in MODELS:
        out["model"] = DEFAULTS["model"]
    if out["arabic"] not in ARABIC:
        out["arabic"] = DEFAULTS["arabic"]
    return out


def clean_cfg(v):
    """What /souk/settings may save under aiContent."""
    if not isinstance(v, dict):
        frappe.throw("Bad content-writer settings.")
    model = str(v.get("model") or DEFAULTS["model"])
    if model not in MODELS:
        frappe.throw("Unknown writing model.")
    arabic = str(v.get("arabic") or DEFAULTS["arabic"])
    if arabic not in ARABIC:
        frappe.throw("Unknown Arabic style.")
    return {"enabled": bool(v.get("enabled")), "model": model, "arabic": arabic,
            "monthlyCap": S._as_int(v.get("monthlyCap"), "The monthly page cap", 0, 100000)}


def _key():
    return frappe.conf.get("anthropic_api_key") or ""


def _sdk_ok():
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _month():
    return str(now_datetime())[:7]


def _usage_all():
    try:
        u = json.loads(frappe.db.get_default(USAGE_KEY) or "{}")
    except ValueError:
        u = {}
    return u if isinstance(u, dict) else {}


def usage():
    """This month: {pages, usd}."""
    m = _usage_all().get(_month()) or {}
    return {"pages": cint(m.get("pages")), "usd": round(flt(m.get("usd")), 2)}


def _count(usd):
    u = _usage_all()
    m = _month()
    u = {k: v for k, v in u.items() if k >= str(int(m[:4]) - 1) + m[4:]}   # a year of history
    cur = u.get(m) if isinstance(u.get(m), dict) else {}
    u[m] = {"pages": cint(cur.get("pages")) + 1, "usd": round(flt(cur.get("usd")) + usd, 4)}
    frappe.db.set_default(USAGE_KEY, json.dumps(u))


def settings_block():
    c = cfg()
    return {"keySet": bool(_key()), "sdk": _sdk_ok(), "used": usage(), "month": _month(),
            "models": [{"id": k, "label": v["label"], "usd": v["usd"]} for k, v in MODELS.items()],
            "config": c}


def _why_not():
    c = cfg()
    if not c["enabled"]:
        return "off"
    if not _key():
        return "key"
    if not _sdk_ok():
        return "sdk"
    if c["monthlyCap"] and usage()["pages"] >= c["monthlyCap"]:
        return "cap"
    return ""


# --- state (cache: the result is a suggestion, not the card's content) --------

def _get(name):
    st = frappe.cache().get_value(CACHE_KEY.format(name))
    return st if isinstance(st, dict) else {}


def _put(name, st):
    frappe.cache().set_value(CACHE_KEY.format(name), st, expires_in_sec=CACHE_TTL)


def block(name):
    """What the content screen shows: can it run, and the last result."""
    c = cfg()
    st = _get(name)
    if st.get("state") in ("queued", "running"):
        from frappe.utils.background_jobs import is_job_enqueued
        if not is_job_enqueued(f"souk-write-{name}"):
            st = {**st, "state": "error", "error": "The writing job stopped. Try again."}
            _put(name, st)
    return {"state": st.get("state") or "", "error": st.get("error") or "", "at": st.get("at") or "",
            "by": st.get("by") or "", "result": st.get("result"), "why": _why_not(),
            "model": MODELS[c["model"]]["label"], "usd": MODELS[c["model"]]["usd"], "arabic": c["arabic"]}


def _content_card(name):
    S._gate_content()
    doc = frappe.get_doc(S.DT_PRODUCT, name)
    if doc.stage != "content":
        frappe.throw("This product is not waiting for its content.")
    return doc


@frappe.whitelist(methods=["POST"])
def start(name, note=""):
    doc = _content_card(name)
    why = _why_not()
    if why:
        frappe.throw({"off": "The content writer is switched off in the souk settings.",
                      "key": "The server has no Anthropic key (site_config anthropic_api_key).",
                      "sdk": "The anthropic package is not installed on the server.",
                      "cap": "This month's page limit has been reached."}[why])
    if not (S._loads(doc.finals_json) or []):
        frappe.throw("The product has no final photos to write from.")
    st = _get(name)
    if st.get("state") in ("queued", "running"):
        return block(name)
    _put(name, {"state": "queued", "at": str(now_datetime())[:16], "by": S._user_name(frappe.session.user)})
    frappe.enqueue("logistics_portal.api.souk_write.run", queue="default", timeout=JOB_TIMEOUT,
                   job_id=f"souk-write-{name}", deduplicate=True, name=name,
                   note=str(note or "")[:500])
    return block(name)


@frappe.whitelist()
def poll(name):
    S._gate_content()
    return block(name)


# --- the job ------------------------------------------------------------------

def run(name, note=""):
    st = _get(name)
    st.update({"state": "running"})
    _put(name, st)
    c = cfg()
    usd = 0.0
    try:
        doc = frappe.get_doc(S.DT_PRODUCT, name)
        result, usd = _write(doc, c, note)
        _put(name, {**st, "state": "done", "result": result, "error": "", "at": str(now_datetime())[:16],
                    "model": MODELS[c["model"]]["label"]})
    except Exception as e:
        frappe.log_error(frappe.get_traceback()[:4000], f"souk_write.run {name}")
        _put(name, {**st, "state": "error", "error": str(e)[:300]})
    finally:
        try:
            _count(usd)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()


def _img_block(url):
    from PIL import Image, ImageOps
    fname = frappe.db.get_value("File", {"file_url": url}, "name")
    if not fname:
        return None
    raw = frappe.get_doc("File", fname).get_content()
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    im.thumbnail((IMG_EDGE, IMG_EDGE))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.standard_b64encode(buf.getvalue()).decode()}}


def _facts(doc, note):
    s = S.settings()
    variants = S._loads(doc.variants_json) or []
    cat = next((x for x in s.get("categories") or [] if x.get("key") == doc.category), {}) or {}
    cmap = {x["code"]: x for x in s.get("colors") or []}
    cols = [x for x in dict.fromkeys(v.get("color") for v in variants) if x]
    sizes = [x for x in dict.fromkeys(v.get("sizeLabel") for v in variants) if x]
    grams = S._weights(variants)
    w = {}
    for v in variants:
        if grams.get(v.get("itemCode")):
            w[v.get("sizeLabel") or "all"] = grams[v["itemCode"]]
    specs = [ln.strip(" -•\t") for ln in (doc.specs or "").splitlines() if ln.strip(" -•\t")]
    out = {
        "workingName": doc.title,
        "category": {"fr": cat.get("fr") or doc.category, "ar": cat.get("ar") or ""},
        "shopBrand": doc.brand or "",
        "colours": [{"fr": cmap.get(x, {}).get("fr") or x, "ar": cmap.get(x, {}).get("ar") or ""} for x in cols],
        "sizes": sizes,
        "floorSpecs": specs,
        "weightGramsPerPiece": w,
    }
    if note:
        out["writerNote"] = note
    return out


SCHEMA = {
    "type": "object",
    "properties": {
        "fr": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}},
               "required": ["title", "description"], "additionalProperties": False},
        "ar": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}},
               "required": ["title", "description"], "additionalProperties": False},
        "metaTitle": {"type": "string"},
        "metaDescription": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "verify": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["fr", "ar", "metaTitle", "metaDescription", "tags", "verify"],
    "additionalProperties": False,
}

ARABIC_STYLE = {
    "msa": ("Modern Standard Arabic: commercial, warm and plain, the register of a good Arab online shop. "
            "Not Egyptian, not Moroccan dialect. Heading for the list: «المواصفات:». "
            "Last line exactly: «التوصيل لجميع مدن المغرب · الدفع عند الاستلام»."),
    "darija": ("Moroccan Darija in Arabic letters, the way the shop already writes its Arabic pages "
               "(«كتشوف», «البلاصة», «الخلاص عند الاستلام»): natural, short, friendly. Heading for the list: "
               "«شنو كاين:». Last line exactly: «التوصيل لكل المغرب · الخلاص عند الاستلام»."),
}

SYSTEM = """You write product pages for Justyol, a Moroccan online shop: cash on delivery, delivery everywhere in Morocco. The storefront's main language is French; Arabic is its translation.

You receive the product's final photos (photo 1 is the main one), sometimes a few raw floor photos that show labels or scale, and the facts the team recorded when buying and receiving it. Write the page from what you can see and what the facts say.

Accuracy — a page that promises more than the goods comes back as a return:
- State only what is visible in the photos or given in the facts. Never invent a material, capacity, dimension, power, certification, origin, compatibility or use you cannot see or read. When a detail would help but you cannot confirm it, leave it out of the page and put it in "verify".
- A number you read on a label or packaging (capacity, size) may be used; add a "verify" note saying which photo it came from.
- Never name a third-party brand, logo or trademark, in any field, even when it is printed on the product or in workingName (the buyer's shorthand). Describe the product generically. The shop's own brand (shopBrand) may be used.
- Colours: use the names given in the facts.
- No prices, discounts, stock levels or delivery times.

French ("fr"), address the customer as "vous":
- title: at most 70 characters. Product type first, then the one to three attributes a shopper looks for (capacity, number of pieces, size; material only if certain). Capitalised like "Gourde Isotherme 1,2 L avec Poignée et Paille". No emoji. A colour only if the product comes in one colour.
- description: plain text, no HTML, no markdown, no emoji. Blocks separated by one blank line:
  1. One or two short paragraphs: what it is and the everyday need it answers, concretely. No hype words (révolutionnaire, incroyable, le meilleur, parfait).
  2. The line "Caractéristiques :" followed by 4 to 7 lines that each start with "• ", facts only.
  3. When colours or sizes vary: one line listing them.
  4. Last line exactly: "Livraison partout au Maroc · paiement à la livraison."

Arabic ("ar"): {arabic_style}
- Same facts and structure as the French, written for an Arabic reader, not a word-for-word translation. title at most 70 characters. List lines start with "• ". Western digits; units in Arabic (مل، لتر، سم، غ).

SEO, in French: metaTitle at most 60 characters, the main search phrase first. metaDescription 120 to 155 characters: what it is, the key benefit, then "Paiement à la livraison partout au Maroc."

tags: 3 to 8 short French tags for the shop's filters (type, use, room; material only if certain), lowercase.

verify: 0 to 6 short notes in Modern Standard Arabic for the person who checks the page: each one a claim to confirm on the actual product before sending, or something the photos could not settle. Empty when there is nothing."""


def _write(doc, c, note):
    import anthropic

    finals = (S._loads(doc.finals_json) or [])[:MAX_FINALS]
    floor = [p for p in (S._loads(doc.photos_json) or []) if p.get("slot") in FLOOR_SLOTS][:MAX_FLOOR]
    content = []
    n = 0
    for i, f in enumerate(finals):
        b = _img_block(f["url"])
        if b:
            n += 1
            content += [{"type": "text", "text": f"Photo {n} — final{' (main)' if i == 0 else ''}"
                                                 f"{', colour ' + f['color'] if f.get('color') else ''}"}, b]
    for p in floor:
        b = _img_block(p["url"])
        if b:
            n += 1
            content += [{"type": "text", "text": f"Photo {n} — raw floor shot ({p.get('slot')})"}, b]
    if not n:
        raise Exception("no readable photo")
    content.append({"type": "text", "text": "Facts:\n" + json.dumps(_facts(doc, note), ensure_ascii=False, indent=1)})

    client = anthropic.Anthropic(api_key=_key(), timeout=300, max_retries=2)
    # Plain messages.create: the call shape the Audit digest already runs on
    # this bench. The refusal fallback rides as a beta header + body field so
    # an older SDK does not trip on an unknown keyword.
    resp = client.messages.create(
        model=c["model"],
        max_tokens=16000,
        system=SYSTEM.replace("{arabic_style}", ARABIC_STYLE[c["arabic"]]),
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": content}],
        extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
        extra_body={"fallbacks": "default"},
    )
    rate = MODELS[c["model"]]
    u = resp.usage
    usd = ((u.input_tokens + (getattr(u, "cache_creation_input_tokens", 0) or 0)) * rate["in"]
           + u.output_tokens * rate["out"]) / 1e6
    if resp.stop_reason == "refusal":
        raise Exception("The model declined to write this page.")
    if resp.stop_reason == "max_tokens":
        raise Exception("The answer was cut off. Try again.")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    data = json.loads(text)
    return _tidy(data, doc), usd


def _cut(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    if len(s) <= n:
        return s
    return s[:n].rsplit(" ", 1)[0].rstrip(" ,;:·-")


def _tidy(d, doc):
    def para(s):
        return re.sub(r"\n{3,}", "\n\n", str(s or "").replace("\r", "")).strip()[:6000]

    fr = d.get("fr") or {}
    ar = d.get("ar") or {}
    title = re.sub(r"\s+", " ", str(fr.get("title") or "")).strip()
    import unicodedata
    plain = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    handle = re.sub(r"[^a-z0-9]+", "-", plain).strip("-")[:120].strip("-")
    tags = []
    for t in d.get("tags") or []:
        t = str(t).strip()[:40]
        if t and t not in tags:
            tags.append(t)
    return {
        "fr": {"title": title[:255], "description": para(fr.get("description"))},
        "ar": {"title": re.sub(r"\s+", " ", str(ar.get("title") or "")).strip()[:255],
               "description": para(ar.get("description"))},
        "metaTitle": _cut(d.get("metaTitle"), S.META_TITLE_MAX),
        "metaDescription": _cut(d.get("metaDescription"), S.META_DESC_MAX),
        "handle": f"{handle}-{doc.name.lower()}"[:200] if handle else "",
        "tags": tags[:8],
        "verify": [str(v).strip()[:300] for v in (d.get("verify") or []) if str(v).strip()][:6],
    }
