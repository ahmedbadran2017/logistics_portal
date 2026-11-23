"""Souk image set: the product page's photo set, built to sell (Ahmed, 2026-11-20).

The cut-out pack (souk_ai.py) gives one clean white photo per angle. The
pages that convert carry a SET, in this order:

    1 hero       white packshot, no text (Google Shopping rules), one per colour
    2 benefits   product on cream, the 3–5 verified benefits + cash-on-delivery
    3 lifestyle  in use in a Moroccan home
    4 scale      in the hand / the size, with the one number that matters
    5 box        "Vous recevez 6 verres": exactly the pieces, numbered
    6 colours    every colour side by side (2+ colours)
    7 detail     the floor's own close-up of the texture, untouched
    8 real       the floor's own photo, badged "Photo réelle du produit"

How a set is made — the rule is still "never prettier than the goods":

    floor photos + the facts ─▶ Claude: the BRIEF (what the product is, what
         must not change, the verified texts, which photos to use, what to verify)
    ─▶ the image model draws shots 1–5 from the floor photos (parallel)
    ─▶ Claude compares every result with the floor photos (QC); a failed shot
         is drawn once more with the reasons, and stays flagged if it fails again
    ─▶ the WORDS are drawn here, by code (exact spelling, one house style);
         the image model never writes text
    ─▶ 6–8 are plain image arithmetic on the floor's own photos
    ─▶ suggestions on the studio card; a person reads the verify list, fixes
         any text (re-rendered free, no new image), accepts or rejects

Nothing reaches Shopify that a person did not accept. Uses the web pack's
provider key, switch and monthly cap (souk_ai) and the server's Anthropic
key (souk_write). State lives in the card's ai_json under "set".
"""

import base64
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

import frappe
import requests
from frappe.utils import cint, flt, now_datetime

from logistics_portal.api import kv
from logistics_portal.api import souk as S
from logistics_portal.api import souk_ai as A
from logistics_portal.api import souk_write as W

KEY = "set"
USAGE_KEY = "lp_souk_set_usage"

# The drawing models. Price per 2048² image, USD, an estimate (the provider
# bills in units); the invoice is the truth.
MODELS = {
    "openai/gpt-image-2.6/flare/edit": {"label": "GPT Image 2.6", "usd": 0.20},
    "google/nano-banana-2.1/edit": {"label": "Nano Banana 2.1", "usd": 0.12},
}
DEFAULT_MODEL = "openai/gpt-image-2.6/flare/edit"
JUDGE = "claude-opus-5-5"          # brief + QC: fidelity is the whole point
CLAUDE_USD = {"brief": 0.06, "qc": 0.03}

ORDER = ("hero", "benefits", "lifestyle", "scale", "box", "colours", "detail", "real")
AI_SHOTS = ("hero", "benefits", "lifestyle", "scale", "box")
TEXT_SHOTS = ("benefits", "scale", "box")   # drawn over a base: text edits re-render free
MAX_COLOURS = 6
MAX_REFS = 4
MAX_TRIES = 2
SIZE = 2048
REF_EDGE = 1536
PARALLEL = 4
FAL_WAIT = 420
JOB_TIMEOUT = 2400

CREAM = (243, 235, 221)
INK = (23, 23, 23)
MUTED = (96, 88, 80)
ACCENT = (180, 83, 42)            # terracotta, warm with the cream
GREEN = (22, 163, 74)
TRUST = ("Paiement à la livraison", "Livraison partout au Maroc")


# --- switches -------------------------------------------------------------------

def model():
    m = A.cfg().get("setModel")
    return m if m in MODELS else DEFAULT_MODEL


def _why_not():
    why = A._why_not()
    if why:
        return why
    if not A.cfg().get("set"):
        return "setoff"
    if not W._key():
        return "claude"
    if not W._sdk_ok():
        return "sdk"
    return ""


def _usage_all():
    try:
        u = json.loads(frappe.db.get_default(USAGE_KEY) or "{}")
    except ValueError:
        u = {}
    return u if isinstance(u, dict) else {}


def usage():
    m = _usage_all().get(str(now_datetime())[:7]) or {}
    return {"sets": cint(m.get("sets")), "usd": round(flt(m.get("usd")), 2)}


def _count(usd, sets=0):
    u = _usage_all()
    m = str(now_datetime())[:7]
    u = {k: v for k, v in u.items() if k >= str(int(m[:4]) - 1) + m[4:]}
    cur = u.get(m) if isinstance(u.get(m), dict) else {}
    u[m] = {"sets": cint(cur.get("sets")) + sets, "usd": round(flt(cur.get("usd")) + usd, 4)}
    kv.set_default(USAGE_KEY, json.dumps(u))


def estimate(n_ai):
    """USD for a set of n_ai drawn shots: drawing + one QC each + the brief,
    with a retry on a third of them (what the tests ran at)."""
    per = MODELS[model()]["usd"] + CLAUDE_USD["qc"]
    return round(CLAUDE_USD["brief"] + n_ai * per * 1.33, 2)


# --- state ------------------------------------------------------------------------

def _get(st):
    s = st.get(KEY)
    if not isinstance(s, dict):
        s = {}
    s.setdefault("state", "")
    s.setdefault("items", [])
    s.setdefault("todo", [])
    s.setdefault("failed", [])
    return s


def _colours(doc):
    return S._colors(S._loads(doc.variants_json) or [])[:MAX_COLOURS]


def _sid(shot, color=""):
    return f"{shot}:{color}" if color else shot


def _rank(it):
    shot = it.get("shot") or ""
    main = ORDER.index(shot) if shot in ORDER else 99
    # The first colour's hero leads; the other colours' heroes close the set
    # (each one is its colour's variant image).
    if shot == "hero" and it.get("extra"):
        main = 50
    return (main, it.get("color") or "")


def block(doc):
    """The studio screen's view of the set for one card."""
    if not S._has_col(S.DT_PRODUCT, A.FIELD):
        return None
    st = _get(A._state(doc))
    why = _why_not()
    brief = st.get("brief") or {}
    items = sorted(st["items"], key=_rank)
    n_ai = len(_plan(doc, brief)[0]) if brief else 4 + (len(_colours(doc)) - 1)
    return {
        "ready": not why, "why": why, "state": st["state"], "error": st.get("error") or "",
        "at": st.get("at") or "", "by": st.get("by") or "",
        "items": [{k: v for k, v in i.items() if k != "base"} | {"editable": bool(i.get("base"))} for i in items],
        "todo": st["todo"], "failed": st["failed"], "step": st.get("step") or "",
        "brief": _public_brief(brief) if brief else None,
        "model": MODELS[model()]["label"], "usd": estimate(n_ai), "spent": round(flt(st.get("usd")), 2),
    }


def _public_brief(b):
    return {k: b.get(k) for k in ("headlineFr", "benefitsFr", "scaleValue", "scaleLine1Fr", "scaleLine2Fr",
                                  "piecesFr", "packCount", "verify", "keep", "boxSubFr", "trust")}


def clear(doc, st):
    """souk_ai.clear's half for the set: drop every file nobody accepted."""
    s = _get(st)
    finals = {f.get("url") for f in (S._loads(doc.get("finals_json")) or [])}
    drop = [i["url"] for i in s["items"] if i.get("url") not in finals]
    drop += [i["base"] for i in s["items"] if i.get("base")]
    S._drop_files(doc.name, drop)
    st.pop(KEY, None)


# --- the studio's buttons -----------------------------------------------------------

def _queue(name, ids, by, fresh=False):
    doc = S._lock_product(name)
    st = A._state(doc)
    s = _get(st)
    if fresh:
        s.pop("brief", None)
    s.update({"state": "queued", "todo": list(dict.fromkeys(s["todo"] + ids)) if ids else ["*"],
              "error": "", "by": by, "at": str(now_datetime())[:16], "step": "",
              "failed": [f for f in s["failed"] if ids and f.get("id") not in ids]})
    st[KEY] = s
    A._save(doc, st)
    frappe.db.commit()
    frappe.enqueue("logistics_portal.api.souk_set.run", queue="long", timeout=JOB_TIMEOUT,
                   job_id=f"souk-set-{name}", deduplicate=True, enqueue_after_commit=True, name=name)


def auto_start(name):
    """photos_send → the whole set, when the manager chose the set."""
    if _why_not():
        return False
    _queue(name, [], frappe.session.user)
    return True


@frappe.whitelist(methods=["POST"])
def start(name, ids=None, fresh=0):
    """The whole set (no ids), or remake these shots. fresh=1 also writes a
    new brief (after the floor re-shot, or when the brief read it wrong)."""
    doc = A._studio_card(name)
    why = _why_not()
    if why:
        frappe.throw(_WHY.get(why, why))
    want = json.loads(ids) if isinstance(ids, str) and ids.startswith("[") else (ids or [])
    if not (S._loads(doc.photos_json) or []):
        frappe.throw("No in-house photo to work from.")
    s = _get(A._state(doc))
    if s["state"] in ("queued", "running"):
        return S._studio_detail(doc.name)
    _queue(doc.name, [str(i) for i in want][:20], frappe.session.user, fresh=bool(cint(fresh)))
    return S._studio_detail(doc.name)


_WHY = {"off": "The website-photo service is switched off in Settings.",
        "key": "The provider key is not set in Settings.",
        "cap": "This month's image cap is reached (Settings).",
        "migrate": "The site needs its migrate first.",
        "setoff": "The photo set is switched off in Settings.",
        "claude": "The server has no Anthropic key (site_config anthropic_api_key).",
        "sdk": "The anthropic package is not installed on the server."}


@frappe.whitelist(methods=["POST"])
def accept(name, urls):
    """Suggestions → finals. Several at once land in the set's order, the
    first colour's hero first, each hero tied to its colour."""
    want = json.loads(urls) if isinstance(urls, str) else (urls or [])
    doc = A._studio_card(name)
    st = A._state(doc)
    s = _get(st)
    pick = sorted([i for i in s["items"] if i["url"] in set(want)], key=_rank)
    if not pick:
        frappe.throw("Nothing to accept — reload.")
    finals = S._loads(doc.finals_json) or []
    if len(finals) + len(pick) > S.MAX_FINALS:
        frappe.throw(f"{S.MAX_FINALS} final photos at most.")
    who = S._user_name(frappe.session.user)
    for i in pick:
        finals.append({"url": i["url"], "color": i.get("color") or "", "by": who,
                       "at": str(now_datetime())[:16], "ai": 1 if i.get("shot") in AI_SHOTS else 0,
                       "shot": i.get("shot")})
    taken = {p["url"] for p in pick}
    S._drop_files(doc.name, [i["base"] for i in pick if i.get("base")])
    s["items"] = [i for i in s["items"] if i["url"] not in taken]
    st[KEY] = s
    doc.db_set("finals_json", json.dumps(finals, ensure_ascii=False), update_modified=False)
    A._save(doc, st)
    frappe.db.commit()
    return S._studio_detail(doc.name)


@frappe.whitelist(methods=["POST"])
def reject(name, url):
    doc = A._studio_card(name)
    st = A._state(doc)
    s = _get(st)
    it = next((i for i in s["items"] if i["url"] == url), None)
    if not it:
        frappe.throw("Suggestion not found — reload.")
    s["items"] = [i for i in s["items"] if i["url"] != url]
    st[KEY] = s
    A._save(doc, st)
    S._drop_files(doc.name, [url] + ([it["base"]] if it.get("base") else []))
    frappe.db.commit()
    return S._studio_detail(doc.name)


@frappe.whitelist(methods=["POST"])
def retext(name, texts):
    """The person fixes the words (a claim the goods do not back, a typo):
    the text shots are drawn again over the same picture. No model is
    called, nothing is billed."""
    t = json.loads(texts) if isinstance(texts, str) else (texts or {})
    doc = A._studio_card(name)
    st = A._state(doc)
    s = _get(st)
    b = s.get("brief")
    if not b:
        frappe.throw("No brief yet — make the set first.")
    clip = lambda v, n: " ".join(str(v or "").split())[:n]
    if "headlineFr" in t:
        b["headlineFr"] = clip(t["headlineFr"], 48)
    if "benefitsFr" in t:
        b["benefitsFr"] = [clip(x, 40) for x in (t.get("benefitsFr") or []) if clip(x, 40)][:5]
    for k, n in (("scaleValue", 12), ("scaleLine1Fr", 44), ("scaleLine2Fr", 52), ("piecesFr", 24), ("boxSubFr", 48)):
        if k in t:
            b[k] = clip(t[k], n)
    if "trust" in t:
        b["trust"] = bool(t["trust"])
    if "packCount" in t:
        b["packCount"] = max(0, min(24, cint(t["packCount"])))
    s["brief"] = b
    old = []
    for i in s["items"]:
        if i.get("shot") in TEXT_SHOTS and i.get("base"):
            try:
                out, extra = _overlay(i["shot"], A._file_bytes(i["base"]), b)
            except Exception as e:
                frappe.throw(f"Could not redraw {i['shot']}: {e}")
            old.append(i["url"])
            f = S._insert_file("set", S.DT_PRODUCT, doc.name, out, "jpg")
            i.update({"url": f.file_url, **extra, "edited": 1})
    st[KEY] = s
    A._save(doc, st)
    S._drop_files(doc.name, old)
    frappe.db.commit()
    return S._studio_detail(doc.name)


@frappe.whitelist()
def poll(name):
    S._gate_studio()
    from frappe.utils.background_jobs import is_job_enqueued
    doc = frappe.get_doc(S.DT_PRODUCT, name)
    s = _get(A._state(doc))
    if (doc.stage == "studio" and s["todo"] and s["state"] in ("queued", "running")
            and not _why_not() and not is_job_enqueued(f"souk-set-{name}")):
        frappe.enqueue("logistics_portal.api.souk_set.run", queue="long", timeout=JOB_TIMEOUT,
                       job_id=f"souk-set-{name}", deduplicate=True, name=name)
    return S._studio_detail(name)


# --- the job --------------------------------------------------------------------------

def _patch(name, fn):
    """Read-modify-write the set state under the row lock, then commit."""
    doc = S._lock_product(name)
    st = A._state(doc)
    s = _get(st)
    fn(s, doc)
    st[KEY] = s
    A._save(doc, st)
    frappe.db.commit()
    return doc, s


def _fail(name, msg):
    _patch(name, lambda s, d: s.update({"state": "error", "error": str(msg)[:300], "todo": [], "step": ""}))


def run(name):
    usd = 0.0
    try:
        usd = _run(name)
    except Exception as e:
        frappe.log_error(frappe.get_traceback()[:4000], f"souk_set.run {name}")
        _fail(name, e)
    finally:
        try:
            _count(usd, sets=1)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()


def _run(name):
    doc = frappe.get_doc(S.DT_PRODUCT, name)
    s = _get(A._state(doc))
    if doc.stage != "studio" or not s["todo"]:
        return 0.0
    why = _why_not()
    if why:
        _fail(name, _WHY.get(why, why))
        return 0.0
    photos = S._loads(doc.photos_json) or []
    usd = 0.0
    client = _client()

    # 1. the brief (kept for remakes; a fresh one on request)
    brief = s.get("brief")
    if not brief:
        _patch(name, lambda s, d: s.update({"state": "running", "step": "brief"}))
        brief, u = _brief(client, doc, photos)
        usd += u
        _patch(name, lambda s, d: s.update({"brief": brief}))

    ai, code = _plan(doc, brief)
    want = s["todo"]
    if want != ["*"]:
        ai = [x for x in ai if x["id"] in want]
        code = [x for x in code if x["id"] in want]
    cap = A.cfg()["monthlyCap"]
    if cap and A.usage() + len(ai) > cap:
        _fail(name, _WHY["cap"])
        return usd
    _patch(name, lambda s, d: s.update({"state": "running", "step": "draw",
                                        "todo": [x["id"] for x in ai + code]}))

    # 2. the drawn shots, in parallel; each one is saved the moment it exists
    refs = {u: _ref_jpeg(u) for u in {r for x in ai for r in x["refs"]}}
    mdl, key = model(), A.api_key()      # read here: the threads have no site context
    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        futs = {pool.submit(_make, client, key, mdl, x, [refs[r] for r in x["refs"] if refs.get(r)], brief): x for x in ai}
        for f in as_completed(futs):
            spec = futs[f]
            try:
                res = f.result()
            except Exception as e:
                res = {"error": str(e)[:300] or e.__class__.__name__}
            usd += res.get("usd", 0)
            if res.get("images"):
                A._count(res["images"])
            _land(name, spec, res, brief)

    # 3. the shots made from the floor's own photos (no model)
    for spec in code:
        try:
            out = _code_shot(spec, doc, brief, name)
            res = {"bytes": out, "ok": True} if out else {"error": "nothing to build it from"}
        except Exception as e:
            frappe.log_error(frappe.get_traceback()[:3000], f"souk_set.{spec['shot']} {name}")
            res = {"error": str(e)[:300]}
        _land(name, spec, res, brief)

    def done(s, d):
        s["state"] = "done" if s["items"] else "error"
        s["todo"], s["step"] = [], ""
        s["usd"] = round(flt(s.get("usd")) + usd, 4)
        if not s["items"] and not s.get("error"):
            s["error"] = "No shot could be made."
    _patch(name, done)
    return usd


def _land(name, spec, res, brief):
    """One finished shot onto the card (or into failed)."""
    item, old = None, []
    if res.get("bytes"):
        base = None
        out, extra = res["bytes"], {}
        if spec["shot"] in TEXT_SHOTS:
            base = S._insert_file("setbase", S.DT_PRODUCT, name, res["bytes"], "jpg").file_url
            out, extra = _overlay(spec["shot"], res["bytes"], brief)
        f = S._insert_file("set", S.DT_PRODUCT, name, out, "jpg")
        item = {"id": spec["id"], "shot": spec["shot"], "color": spec.get("color") or "",
                "extra": 1 if spec.get("extra") else 0, "url": f.file_url, "base": base,
                "ok": res.get("ok"), "notes": res.get("notes") or [], "tries": res.get("tries") or 0,
                "model": res.get("model") or "", "at": str(now_datetime())[:16], **extra}

    def put(s, d):
        s["todo"] = [i for i in s["todo"] if i != spec["id"]]
        if item:
            for i in s["items"]:
                if i.get("id") == spec["id"]:
                    old.extend([i["url"]] + ([i["base"]] if i.get("base") else []))
            s["items"] = [i for i in s["items"] if i.get("id") != spec["id"]] + [item]
            s["failed"] = [x for x in s["failed"] if x.get("id") != spec["id"]]
        else:
            s["failed"] = [x for x in s["failed"] if x.get("id") != spec["id"]] + [
                {"id": spec["id"], "shot": spec["shot"], "color": spec.get("color") or "",
                 "error": res.get("error") or "failed"}]
    _patch(name, put)
    if old:
        S._drop_files(name, old)
        frappe.db.commit()


# --- the plan: which shots, from which floor photos --------------------------------------

def _plan(doc, brief):
    photos = S._loads(doc.photos_json) or []
    cols = _colours(doc)
    main = cols[0]["code"] if cols else ""
    num = {i + 1: p["url"] for i, p in enumerate(_numbered(photos, doc))}
    refs = [num[n] for n in (brief.get("refs") or []) if n in num][:MAX_REFS]
    if not refs:
        refs = [p["url"] for p in photos if (p.get("color") or "") == main and p.get("slot") in ("front", "side", "back")][:MAX_REFS]
    if not refs:
        refs = [p["url"] for p in photos][:MAX_REFS]
    ai = [{"id": _sid("hero", main), "shot": "hero", "color": main, "refs": refs}]
    for c in cols[1:]:
        front = [p["url"] for p in photos if (p.get("color") or "") == c["code"] and p.get("slot") == "front"]
        if front:
            ai.append({"id": _sid("hero", c["code"]), "shot": "hero", "color": c["code"], "extra": 1,
                       "refs": front + refs[:2], "colour": c.get("fr") or c["code"]})
    ai += [{"id": k, "shot": k, "refs": refs} for k in ("benefits", "lifestyle", "scale")]
    n = cint(brief.get("packCount"))
    if 2 <= n <= 12:
        ai.append({"id": "box", "shot": "box", "refs": refs})
    code = []
    if len([c for c in cols if c["code"]]) >= 2:
        code.append({"id": "colours", "shot": "colours"})
    det = num.get(cint(brief.get("detailPhoto"))) or next((p["url"] for p in photos if p.get("slot") == "detail"), None)
    if det:
        code.append({"id": "detail", "shot": "detail", "src": det})
    real = num.get(cint(brief.get("realPhoto"))) or next((p["url"] for p in photos if p.get("slot") == "front"), None)
    if real:
        code.append({"id": "real", "shot": "real", "src": real})
    return ai, code


def _numbered(photos, doc):
    """The order the brief saw the photos in (its numbers point here): the
    main colour's angles first, then each other colour's."""
    rank = {s: i for i, s in enumerate(S.RAW_SLOTS + (S.EXTRA_SLOT,))}
    cols = {c["code"]: i for i, c in enumerate(_colours(doc))}
    return sorted(photos, key=lambda p: (cols.get(p.get("color") or "", 0), rank.get(p.get("slot"), 9)))[:12]


# --- Claude: the brief and the QC ---------------------------------------------------------

def _client():
    import anthropic
    return anthropic.Anthropic(api_key=W._key(), timeout=300, max_retries=2)


def _claude(client, system, content, schema, max_tokens=8000):
    resp = client.messages.create(
        model=JUDGE, max_tokens=max_tokens, system=system,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": content}],
        extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
        extra_body={"fallbacks": "default"},
    )
    rate = W.MODELS[JUDGE]
    u = resp.usage
    usd = ((u.input_tokens + (getattr(u, "cache_creation_input_tokens", 0) or 0)) * rate["in"]
           + u.output_tokens * rate["out"]) / 1e6
    if resp.stop_reason == "refusal":
        raise Exception("The model declined.")
    if resp.stop_reason == "max_tokens":
        raise Exception("The answer was cut off.")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text), usd


def _jpeg_block(jpeg, edge=1024):
    from PIL import Image
    im = Image.open(io.BytesIO(jpeg)).convert("RGB")
    im.thumbnail((edge, edge))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.standard_b64encode(buf.getvalue()).decode()}}


BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "product": {"type": "string"},
        "keep": {"type": "array", "items": {"type": "string"}},
        "scene": {"type": "string"},
        "handHeld": {"type": "boolean"},
        "packCount": {"type": "integer"},
        "pieceFr": {"type": "string"},
        "piecesFr": {"type": "string"},
        "headlineFr": {"type": "string"},
        "benefitsFr": {"type": "array", "items": {"type": "string"}},
        "scaleValue": {"type": "string"},
        "scaleLine1Fr": {"type": "string"},
        "scaleLine2Fr": {"type": "string"},
        "boxSubFr": {"type": "string"},
        "refs": {"type": "array", "items": {"type": "integer"}},
        "realPhoto": {"type": "integer"},
        "detailPhoto": {"type": "integer"},
        "verify": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["product", "keep", "scene", "handHeld", "packCount", "pieceFr", "piecesFr", "headlineFr",
                 "benefitsFr", "scaleValue", "scaleLine1Fr", "scaleLine2Fr", "boxSubFr", "refs",
                 "realPhoto", "detailPhoto", "verify"],
    "additionalProperties": False,
}

BRIEF_SYSTEM = """You prepare the photo set of a product page for Justyol, a Moroccan online shop (French storefront, cash on delivery). You receive the in-house photos the warehouse floor took of the real goods (numbered, with their angle) and the facts recorded when buying them. An image model will redraw the product in new settings from these photos; code will print your texts on some images. A photo or a text that promises more than the goods is a return, so accuracy beats salesmanship everywhere.

Fields:
- product: one English paragraph for the image model describing exactly what is sold as it looks in the photos: type, shape and proportions, colours, material as it LOOKS (glass, matte plastic...), every decoration and where it sits, number of parts, what is in the pack. Do not name third-party brands.
- keep: 2 to 6 short English sentences naming the details an image model is most likely to get wrong and that must stay identical (e.g. "exactly 6 heating tubes", "the white floral band sits in the upper third, two rows of petals", "the lid is dark grey, not black").
- scene: one English sentence for a lifestyle photo: where in a bright modern Moroccan home this product is used, on which surface, by whom if anyone, the action. Props must be ordinary context (table, plants, a plate of food) and never of the same kind as the product, so nobody thinks they are included.
- handHeld: true if a person naturally holds one piece in one hand.
- packCount: how many pieces the customer receives in one order of this product, if the facts or the packaging show it clearly; 0 for a single item or when unsure (then add a verify note).
- pieceFr / piecesFr: the French noun for one piece and for several ("verre"/"verres", "boîte"/"boîtes").
- headlineFr: the benefits slide title, French, at most 32 characters, concrete (what it does for you), no hype words (révolutionnaire, incroyable, parfait, le meilleur), no exclamation mark.
- benefitsFr: 3 to 5 French lines, each at most 30 characters, each a fact a shopper cares about: count, capacity, size, use, care. Only what a photo shows or the facts state. A claim printed on the packaging may be used only if the packaging is clearly the one of THIS variant; then add a verify note naming the photo. Never invent a material, certification, dishwasher/microwave safety, power or origin.
- scaleValue: the one number that tells the size (e.g. "20 cl", "1,2 L", "30 cm") when read on a label/package or given in the facts; "" otherwise. scaleLine1Fr (at most 34 characters) and scaleLine2Fr (at most 40) describe size and use plainly, e.g. "Taille réelle, en main" / "Idéal pour l'eau, le jus et le thé".
- boxSubFr: the line under "Vous recevez N ...", at most 40 characters, e.g. "Le lot complet, prêt à servir"; "" when packCount is 0.
- refs: the numbers of the 2 to 4 photos that best show the whole product's shape and colours, best first (the main colour only).
- realPhoto: the number of the floor photo that shows the whole product sharpest, used untouched with a "real photo" badge.
- detailPhoto: the number of a sharp close-up of the texture or decoration, or 0 if none is sharp enough.
- verify: 0 to 6 short notes in Modern Standard Arabic for the marketing person: every claim to check on the goods before accepting, and anything the photos could not settle."""


def _brief(client, doc, photos):
    content, n = [], 0
    for p in _numbered(photos, doc):
        b = W._img_block(p["url"])
        if b:
            n += 1
            content += [{"type": "text", "text": f"Photo {n} — {p.get('slot')}"
                                                 f"{', colour ' + p['color'] if p.get('color') else ''}"}, b]
    if not n:
        raise Exception("no readable in-house photo")
    content.append({"type": "text", "text": "Facts:\n" + json.dumps(W._facts(doc, ""), ensure_ascii=False, indent=1)})
    data, usd = _claude(client, BRIEF_SYSTEM, content, BRIEF_SCHEMA, max_tokens=12000)
    clip = lambda v, k: " ".join(str(v or "").split())[:k]
    data["headlineFr"] = clip(data.get("headlineFr"), 48)
    data["benefitsFr"] = [clip(x, 40) for x in (data.get("benefitsFr") or []) if clip(x, 40)][:5]
    data["verify"] = [clip(x, 300) for x in (data.get("verify") or []) if clip(x, 300)][:6]
    data["keep"] = [clip(x, 200) for x in (data.get("keep") or []) if clip(x, 200)][:6]
    data["packCount"] = max(0, min(24, cint(data.get("packCount"))))
    data["trust"] = True
    data["brand"] = (doc.brand or "").strip()[:30]     # the shop's own brand only
    data["at"] = str(now_datetime())[:16]
    return data, usd


QC_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "count": {"type": "integer"},
        "problems": {"type": "array", "items": {"type": "string"}},
        "problemsAr": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ok", "count", "problems", "problemsAr"],
    "additionalProperties": False,
}

QC_SYSTEM = """You are the last check before an AI-made product photo can be shown to a shopper. The first images are real photos of the goods; the LAST image is the AI-made photo. A photo that shows a different product than the one delivered is a return, so be strict: when unsure, fail.

Fail (ok=false) when any of these is true:
- the product's shape, proportions, colour, material look, decoration or pattern, or number of parts differs in a way a shopper could notice;
- text, a logo or a label was added to or changed on the product;
- the number of pieces is wrong for this shot;
- a hand or a person is deformed;
- the area the shot reserves for text is not empty;
- something in the image could be taken as included in the order when it is not.
Plain context props (a table, plants, food) are fine in a lifestyle photo.

count: the number of product pieces visible in the AI image. problems: short English reasons, written as instructions to fix (empty when ok). problemsAr: the same reasons in Modern Standard Arabic for the marketing person."""


def _qc(client, refs, out, spec, brief):
    content = []
    for k, r in enumerate(refs[:3], 1):
        content += [{"type": "text", "text": f"Real photo {k}"}, _jpeg_block(r, 768)]
    content += [{"type": "text", "text": "AI-made photo (the one to judge)"}, _jpeg_block(out, 1024)]
    rule = {"hero": "Shot: white packshot, only the product, one piece unless the product is a set shown together.",
            "benefits": "Shot: product on the right, the LEFT 45% must be empty background for text.",
            "lifestyle": "Shot: the product in use in a home; it must be the clear hero.",
            "scale": "Shot: the product with a hand or in use to show its true size; the TOP-LEFT quarter must be empty for text.",
            "box": f"Shot: exactly {cint(brief.get('packCount'))} pieces in a row, the TOP 30% must be empty for text."}[spec["shot"]]
    content.append({"type": "text", "text": rule + "\nWhat the product is: " + (brief.get("product") or "")
                    + "\nMust stay identical: " + "; ".join(brief.get("keep") or [])
                    + (f"\nThis is the {spec.get('colour')} colour." if spec.get("colour") else "")})
    return _claude(client, QC_SYSTEM, content, QC_SCHEMA, max_tokens=4000)


# --- the image model ----------------------------------------------------------------------

KEEP = ("The reference photos show the exact item being sold. Reproduce it exactly: same shape, proportions, "
        "colours, material, decoration and number of parts. {keep} Do not add any text, logo, label or "
        "decoration that is not on the references. Photorealistic, true colours, sharp focus.")


def _prompt(spec, brief):
    p = brief.get("product") or "the product in the reference photos"
    keep = KEEP.replace("{keep}", " ".join(brief.get("keep") or []))
    n = cint(brief.get("packCount"))
    piece = brief.get("piecesFr") or "pieces"
    shot = spec["shot"]
    if shot == "hero":
        col = f" This image must show the {spec['colour']} colour version, exactly as in the first reference photo." if spec.get("colour") else ""
        body = (f"Professional e-commerce packshot of {p}.{col} Pure white background (#FFFFFF), a soft natural "
                "contact shadow, the product centred and filling about 80% of the square frame, three-quarter "
                "front view as in the references, crisp even studio light. Only the product: no props, no text.")
    elif shot == "benefits":
        body = (f"Premium advertising photo of {p}, standing in the RIGHT half of a square frame on a warm cream "
                "seamless background (#F3EBDD), soft daylight from the left, a gentle shadow. The LEFT 45% of the "
                "image is completely empty cream background with nothing in it (text goes there later). No text.")
    elif shot == "lifestyle":
        body = (f"Lifestyle photograph: {brief.get('scene') or 'the product in use in a bright modern Moroccan home'} "
                f"The product is {p} It is the clear hero, sharp, in natural daylight, shallow depth of field, "
                "realistic and not staged-looking. No text, no logos.")
    elif shot == "scale":
        how = ("an adult's hand naturally holding one piece, realistic hand with five fingers"
               if brief.get("handHeld") else "the product in use on a kitchen counter or table, an adult hand resting on it")
        body = (f"Photo of {p} showing its true size: {how}. Soft neutral warm-grey background, the product in the "
                "RIGHT two thirds; the TOP-LEFT quarter of the image is empty background (text goes there later). "
                "The product's size relative to the hand must be realistic. No text.")
    else:  # box
        lay = "in one neat straight row" if n <= 8 else "in a neat grid"
        body = (f"Exactly {n} pieces ({piece}) of {p}, all identical, {lay}, evenly spaced and not overlapping, seen "
                f"from the front on pure white, soft shadows. Exactly {n} pieces, no more, no fewer. The TOP 30% of "
                "the image is empty white (text goes there later). No text, no packaging.")
    return body + " " + keep


def _fal(key, mdl, prompt, refs):
    uris = ["data:image/jpeg;base64," + base64.b64encode(r).decode() for r in refs]
    if mdl.startswith("openai/"):
        body = {"prompt": prompt, "image_urls": uris[:16], "image_size": {"width": SIZE, "height": SIZE},
                "quality": "high", "output_format": "jpeg", "num_images": 1}
    else:
        body = {"prompt": prompt, "image_urls": uris[:14], "aspect_ratio": "1:1", "resolution": "2K",
                "output_format": "jpeg", "num_images": 1}
    h = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    r = requests.post(f"https://queue.fal.run/{mdl}", json=body, headers=h, timeout=120)
    if r.status_code >= 400:
        raise Exception(f"provider answered {r.status_code}: {r.text[:200]}")
    j = r.json() or {}
    status_url, response_url = j.get("status_url"), j.get("response_url")
    if not (status_url and response_url):
        raise Exception("provider gave no job handle")
    end = time.time() + FAL_WAIT
    while True:
        st = requests.get(status_url, headers=h, timeout=60).json() or {}
        if st.get("status") == "COMPLETED":
            break
        if time.time() > end:
            raise Exception("the provider took too long")
        time.sleep(3)
    g = requests.get(response_url, headers=h, timeout=120)
    if g.status_code >= 400:
        raise Exception(f"provider answered {g.status_code}: {g.text[:200]}")
    url = (((g.json() or {}).get("images") or [{}])[0] or {}).get("url")
    if not url:
        raise Exception("provider returned no image")
    if url.startswith("data:"):
        raw = base64.b64decode(url.split(",", 1)[1])
    else:
        d = requests.get(url, timeout=120)
        d.raise_for_status()
        raw = d.content
    return _square(raw)


def _make(client, key, mdl, spec, refs, brief):
    """One drawn shot: draw → QC → (once) draw again with the reasons.
    Runs in a thread: no frappe calls in here."""
    if not refs:
        return {"error": "no reference photo"}
    base = _prompt(spec, brief)
    prompt, tries, usd, images = base, [], 0.0, 0
    other = next(m for m in MODELS if m != mdl)
    for k in range(MAX_TRIES):
        used = mdl
        try:
            out = _fal(key, mdl, prompt, refs)
        except Exception:
            used = other       # one fallback to the other model (moderation, outage)
            images += 1
            out = _fal(key, other, prompt, refs)
        images += 1
        usd += MODELS[used]["usd"]
        try:
            qc, u = _qc(client, refs, out, spec, brief)
            usd += u
        except Exception as e:
            qc = {"ok": None, "problems": [], "problemsAr": [f"تعذّر الفحص الآلي: {str(e)[:120]}"], "count": 0}
        tries.append((out, qc, used))
        if qc.get("ok") is not False:
            break
        prompt = base + " A previous attempt was rejected for these reasons; fix exactly them: " + "; ".join(qc.get("problems") or [])
    out, qc, used = tries[-1]
    notes = [] if qc.get("ok") is True else (qc.get("problemsAr") or [])[:4]
    return {"bytes": out, "ok": qc.get("ok"), "notes": notes, "count": cint(qc.get("count")),
            "tries": len(tries), "model": MODELS[used]["label"], "usd": usd, "images": images}


def _ref_jpeg(url):
    from PIL import Image, ImageOps
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(A._file_bytes(url)))).convert("RGB")
    except Exception:
        return None
    im.thumbnail((REF_EDGE, REF_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def _square(raw):
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    if im.size != (SIZE, SIZE):
        side = min(im.size)
        im = im.crop(((im.width - side) // 2, (im.height - side) // 2,
                      (im.width + side) // 2, (im.height + side) // 2)).resize((SIZE, SIZE), Image.LANCZOS)
    return _jpeg(im)


def _jpeg(im, q=92):
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=q, optimize=True, progressive=True)
    return buf.getvalue()


# --- the words, drawn by code -------------------------------------------------------------

# Bundled fonts first (logistics_portal/public/fonts/souk-*.ttf, if someone
# adds the house font), then the Mac the prototype was made on, then the
# DejaVu every Debian server and matplotlib carry.
_FONTS = {
    "bold": [("souk-bold.ttf", 0), ("/System/Library/Fonts/Avenir Next.ttc", 0),
             ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0), ("mpl:DejaVuSans-Bold.ttf", 0)],
    "medium": [("souk-medium.ttf", 0), ("/System/Library/Fonts/Avenir Next.ttc", 5),
               ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0), ("mpl:DejaVuSans.ttf", 0)],
    "regular": [("souk-regular.ttf", 0), ("/System/Library/Fonts/Avenir Next.ttc", 7),
                ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0), ("mpl:DejaVuSans.ttf", 0)],
}


@lru_cache(maxsize=8)
def _font_path(weight):
    from PIL import ImageFont
    here = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public", "fonts")
    for path, idx in _FONTS[weight]:
        if path.startswith("mpl:"):
            try:
                import matplotlib
                path = os.path.join(matplotlib.get_data_path(), "fonts", "ttf", path[4:])
            except Exception:
                continue
        elif not path.startswith("/"):
            path = os.path.join(here, path)
        if os.path.exists(path):
            try:
                ImageFont.truetype(path, 20, index=idx)
                return path, idx
            except Exception:
                continue
    return None, 0


@lru_cache(maxsize=256)
def _font(size, weight="medium"):
    from PIL import ImageFont
    path, idx = _font_path(weight)
    if path:
        return ImageFont.truetype(path, size, index=idx)
    return ImageFont.load_default(size=size)


def _fit(d, text, weight, size, width, floor=40):
    while size > floor and d.textlength(text, font=_font(size, weight)) > width:
        size -= 4
    return size


def _wrap(d, text, weight, size, width, lines=2):
    """Greedy wrap into at most `lines` lines; shrinks until it fits."""
    while True:
        f = _font(size, weight)
        out, cur = [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= width or not cur:
                cur = t
            else:
                out.append(cur)
                cur = w
        out.append(cur)
        if (len(out) <= lines and all(d.textlength(x, font=f) <= width for x in out)) or size <= 56:
            return out[:lines], size
        size -= 4


def _veil(im, box, fade, axis="x"):
    """A soft panel of the photo's own background colour behind the text, so
    the words read even when the model left a shadow or a prop there."""
    from PIL import Image, ImageDraw, ImageStat
    x0, y0, x1, y1 = box
    strip = im.crop((x0, y0, max(x0 + 8, x0 + (x1 - x0) // 6), y1)) if axis == "x" else im.crop((x0, y0, x1, max(y0 + 8, y0 + (y1 - y0) // 6)))
    col = tuple(int(v) for v in ImageStat.Stat(strip).median)
    mask = Image.new("L", im.size, 0)
    dr = ImageDraw.Draw(mask)
    if axis == "x":
        dr.rectangle((x0, y0, x1, y1), fill=215)
        for i in range(fade):
            dr.line([(x1 + i, y0), (x1 + i, y1)], fill=int(215 * (1 - i / fade)))
    else:
        dr.rectangle((x0, y0, x1, y1), fill=215)
        for i in range(fade):
            dr.line([(x0, y1 + i), (x1, y1 + i)], fill=int(215 * (1 - i / fade)))
    im.paste(col, mask=mask)


def _check(d, x, y, r=34):
    d.ellipse((x, y, x + 2 * r, y + 2 * r), fill=ACCENT)
    d.line([(x + r * .55, y + r * 1.02), (x + r * .9, y + r * 1.38), (x + r * 1.5, y + r * .68)],
           fill="white", width=max(4, r // 4), joint="curve")


def _pill(d, x, y, text, size=44, dot=GREEN):
    f = _font(size, "medium")
    w = d.textlength(text, font=f)
    h = int(size * 2.0)
    d.rounded_rectangle((x, y, x + w + size * 2.4, y + h), radius=h // 2, fill=(255, 255, 255, 235))
    r = size * 0.32
    cy = y + h / 2
    d.ellipse((x + size * 0.7 - r, cy - r, x + size * 0.7 + r, cy + r), fill=dot)
    d.text((x + size * 1.4, cy), text, font=f, fill=INK, anchor="lm")
    return h


def _overlay(shot, base_jpeg, b):
    """Base picture + the brief's words → the slide. Returns (jpeg, extra)."""
    from PIL import Image, ImageDraw
    im = Image.open(io.BytesIO(base_jpeg)).convert("RGB")
    if im.size != (SIZE, SIZE):
        im = im.resize((SIZE, SIZE), Image.LANCZOS)
    extra = {}
    if shot == "benefits":
        x, right = 130, int(0.43 * SIZE)
        _veil(im, (0, 0, right + 30, SIZE), 140)
        d = ImageDraw.Draw(im, "RGBA")
        y = 280
        brand = (b.get("brand") or "").strip()
        if brand:
            d.text((x, y), brand.upper(), font=_font(46, "bold"), fill=ACCENT)
            y += 80
        lines, size = _wrap(d, b.get("headlineFr") or "", "bold", 112, right - x, 3)
        for ln in lines:
            d.text((x, y), ln, font=_font(size, "bold"), fill=INK)
            y += int(size * 1.15)
        y += 90
        items = (b.get("benefitsFr") or [])[:5]
        bs = min(_fit(d, t, "medium", 64, right - x - 100) for t in items) if items else 64
        for t in items:
            _check(d, x, y + int(bs * 0.1), r=int(bs * 0.53))
            d.text((x + int(bs * 1.55), y), t, font=_font(bs, "medium"), fill=INK)
            y += int(bs * 2.3)
        if b.get("trust", True):
            ty = max(y + 40, SIZE - 330)
            for t in TRUST:
                ty += _pill(d, x, ty, t, 46) + 22
    elif shot == "scale":
        x, y = 150, 240
        _veil(im, (0, 0, int(SIZE * 0.55), int(SIZE * 0.40)), 160, axis="y")
        d = ImageDraw.Draw(im, "RGBA")
        val = (b.get("scaleValue") or "").strip()
        w = int(SIZE * 0.44)
        if val:
            s = _fit(d, val, "bold", 260, w, 120)
            d.text((x, y), val, font=_font(s, "bold"), fill=INK)
            y += int(s * 1.2)
            l1 = b.get("scaleLine1Fr") or ""
            d.text((x + 8, y), l1, font=_font(_fit(d, l1, "medium", 70, w), "medium"), fill=MUTED)
            y += 100
        else:
            lines, s = _wrap(d, b.get("scaleLine1Fr") or "", "bold", 104, w, 2)
            for ln in lines:
                d.text((x, y), ln, font=_font(s, "bold"), fill=INK)
                y += int(s * 1.15)
            y += 20
        l2 = b.get("scaleLine2Fr") or ""
        if l2:
            d.text((x + 8, y), l2, font=_font(_fit(d, l2, "regular", 56, w), "regular"), fill=MUTED)
    elif shot == "box":
        n = cint(b.get("packCount"))
        _veil(im, (0, 0, SIZE, int(SIZE * 0.29)), 120, axis="y")
        xs, bottom = _pieces(im)
        d = ImageDraw.Draw(im, "RGBA")
        t = f"Vous recevez {n} {b.get('piecesFr') or ''}".strip()
        s = _fit(d, t, "bold", 108, int(SIZE * 0.86))
        d.text((SIZE / 2, 330), t, font=_font(s, "bold"), fill=INK, anchor="mt")
        sub = b.get("boxSubFr") or ""
        if sub:
            d.text((SIZE / 2, 330 + int(s * 1.35)), sub, font=_font(_fit(d, sub, "medium", 60, int(SIZE * 0.8)), "medium"),
                   fill=MUTED, anchor="mt")
        # Numbers only when the picture really holds n separate pieces: a
        # wrong count printed on the image is worse than none.
        extra["numbered"] = 1 if (len(xs) == n and n <= 8) else 0
        if extra["numbered"]:
            cy = min(bottom + 90, SIZE - 80)
            for k, cx in enumerate(xs, 1):
                r = 48
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ACCENT)
                d.text((cx, cy), str(k), font=_font(56, "bold"), fill="white", anchor="mm")
    return _jpeg(im), extra


def _pieces(im):
    """Centres of the separate objects in a row on white (column runs of
    non-white below the title band), and their lowest row."""
    import numpy as np
    a = np.asarray(im.convert("L")).astype(int)
    y0 = int(SIZE * 0.32)
    band = a[y0:int(SIZE * 0.97)]
    dark = band < 232
    on = dark.sum(axis=0) > 30
    xs, start = [], None
    for i, v in enumerate(list(on) + [False]):
        if v and start is None:
            start = i
        if not v and start is not None:
            if i - start > 50:
                xs.append((start + i) // 2)
            start = None
    rows = np.where(dark.sum(axis=1) > 20)[0]
    bottom = y0 + int(rows.max()) if len(rows) else int(SIZE * 0.8)
    return xs, bottom


# --- the shots made from the floor's own photos ---------------------------------------------

def _badge(im, text, dot=GREEN):
    from PIL import ImageDraw
    d = ImageDraw.Draw(im, "RGBA")
    _pill(d, 80, 80, text, 56, dot)
    return im


def _floor_square(url):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(A._file_bytes(url)))).convert("RGB")
    side = min(im.size)
    im = im.crop(((im.width - side) // 2, (im.height - side) // 2,
                  (im.width + side) // 2, (im.height + side) // 2))
    return im.resize((SIZE, SIZE), Image.LANCZOS)


def _code_shot(spec, doc, brief, name):
    from PIL import Image, ImageDraw
    shot = spec["shot"]
    if shot == "real":
        return _jpeg(_badge(_floor_square(spec["src"]), "Photo réelle du produit"))
    if shot == "detail":
        return _jpeg(_badge(_floor_square(spec["src"]), "Détail réel, sans retouche"))
    if shot == "colours":
        st = _get(A._state(frappe.get_doc(S.DT_PRODUCT, name)))
        heroes = {i.get("color"): i["url"] for i in st["items"] if i.get("shot") == "hero"}
        cols = [c for c in _colours(doc) if c["code"] and heroes.get(c["code"])]
        if len(cols) < 2:
            return None
        g = Image.new("RGB", (SIZE, SIZE), (255, 255, 255))
        d = ImageDraw.Draw(g)
        t = f"Disponible en {len(cols)} couleurs"
        ts = _fit(d, t, "bold", 104, int(SIZE * 0.86))
        per = 2 if len(cols) <= 4 else 3
        rows = -(-len(cols) // per)
        gap, lab = 48, 110
        cell = min((SIZE - 200 - gap * (per - 1)) // per, (SIZE - 420 - rows * lab - gap * (rows - 1)) // rows)
        block = int(ts * 1.2) + 90 + rows * (cell + lab) + (rows - 1) * gap
        top = max(80, (SIZE - block) // 2)
        d.text((SIZE / 2, top), t, font=_font(ts, "bold"), fill=INK, anchor="mt")
        top += int(ts * 1.2) + 90
        mask = Image.new("L", (cell, cell), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, cell - 1, cell - 1), radius=cell // 14, fill=255)
        for k, c in enumerate(cols):
            r, q = divmod(k, per)
            n_in_row = min(per, len(cols) - r * per)
            x0 = (SIZE - (n_in_row * cell + (n_in_row - 1) * gap)) // 2 + q * (cell + gap)
            y0 = top + r * (cell + lab + gap)
            tile = Image.open(io.BytesIO(A._file_bytes(heroes[c["code"]]))).convert("RGB").resize((cell, cell), Image.LANCZOS)
            g.paste(tile, (x0, y0), mask)
            d.rounded_rectangle((x0, y0, x0 + cell - 1, y0 + cell - 1), radius=cell // 14, outline=(231, 229, 228), width=3)
            label = c.get("fr") or c["code"]
            d.text((x0 + cell / 2, y0 + cell + 26), label, font=_font(_fit(d, label, "medium", 60, cell), "medium"),
                   fill=INK, anchor="mt")
        return _jpeg(g)
    return None
