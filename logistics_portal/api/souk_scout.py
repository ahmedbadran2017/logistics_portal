"""The market round (جولة السوق, 2026-11-25): the person walking Derb Omar
and the other wholesale markets registers each shop from the phone, instead
of sending its photo, location, Telegram link and business card on WhatsApp.

One shop takes four steps on the screen (SoukScout.vue):

  1. the storefront photo; the GPS fix is taken at the same moment;
  2. the business card: a model reads the name, the phones and the links
     and fills the fields (read_card); the person checks them;
  3. the Telegram link (from the card, pasted or a scanned QR), checked on
     the spot against its public preview (check_telegram);
  4. the market, the place inside it, what it sells, a note.

Where it lands
* The SHOP is a Supplier, as every source of the selection is: a new one is
  a lead (group "Souk Leads", souk_picks.LEAD_GROUP); the first purchase makes
  it a stall ("Souk Suppliers"). Phone on the primary Contact, storefront on
  Supplier.image, place in supplier_details ("Souk stall · <market> · <row>"),
  categories and note in the same fields souk_stalls uses. A public Telegram
  channel goes in Supplier.website, so the 3-hourly read picks it up — and
  the first read is queued at once.
* The VISIT (LP Souk Visit) is the field log: who, when, where (lat/lng and
  the fix's accuracy), both photos, what the card said, what was decided
  (new shop / added to an existing one). The same shop visited twice is one
  Supplier and two visits.

The same shop twice: before saving, the screen asks similar() — the same
phone, the same channel, or a shop a few metres away with a name that reads
the same — and the person says "the same shop" or "another one". A save that
was queued offline never asked: then only a phone or a channel match joins
an existing shop; anything weaker makes a new lead, marked on the visit.

Who: the "scout" portal role (this screen only, their own visits), the
buyers and the manager (everyone's). No prices, no balances here.
"""

import json
import math
import re

import frappe
from frappe.utils import cint, flt, now_datetime

from logistics_portal.api import souk as S

DT_VISIT = "LP Souk Visit"
ROLES = ("manager", "sourcing", "scout")
TG_STATES = ("public", "private", "none")
CARD_MODEL = "claude-haiku-5-5"
NEAR_M = 25            # two shops closer than this with a similar name: ask
MARKETS = ["درب عمر", "القريعة", "كراج علال", "درب السلطان", "باب مراكش", "الحفاري"]

VISIT_FIELDS = [
    {"fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "label": "Shop", "in_list_view": 1,
     "search_index": 1},
    {"fieldname": "scout", "fieldtype": "Data", "label": "Registered by (user)", "in_list_view": 1,
     "search_index": 1},
    {"fieldname": "visited_at", "fieldtype": "Datetime", "label": "Visited at", "search_index": 1},
    {"fieldname": "outcome", "fieldtype": "Select", "label": "Outcome", "options": "new\nsame\nauto",
     "in_list_view": 1},
    {"fieldname": "client_key", "fieldtype": "Data", "label": "Client request id", "unique": 1},
    {"fieldname": "market", "fieldtype": "Data", "label": "Market"},
    {"fieldname": "place", "fieldtype": "Data", "label": "Place in the market"},
    {"fieldname": "lat", "fieldtype": "Float", "label": "Latitude", "precision": "7"},
    {"fieldname": "lng", "fieldtype": "Float", "label": "Longitude", "precision": "7"},
    {"fieldname": "accuracy", "fieldtype": "Int", "label": "GPS accuracy (m)"},
    {"fieldname": "shop_photo", "fieldtype": "Attach Image", "label": "Storefront"},
    {"fieldname": "card_photo", "fieldtype": "Attach Image", "label": "Business card"},
    {"fieldname": "shop_name", "fieldtype": "Data", "label": "Name as registered"},
    {"fieldname": "phone", "fieldtype": "Data", "label": "Phone"},
    {"fieldname": "phone2", "fieldtype": "Data", "label": "Second phone"},
    {"fieldname": "telegram", "fieldtype": "Data", "label": "Telegram link"},
    {"fieldname": "tg_state", "fieldtype": "Select", "label": "Telegram", "options": "\npublic\nprivate\nnone"},
    {"fieldname": "instagram", "fieldtype": "Data", "label": "Instagram"},
    {"fieldname": "sells", "fieldtype": "Data", "label": "Sells (category keys)"},
    {"fieldname": "note", "fieldtype": "Small Text", "label": "Note"},
    {"fieldname": "card_json", "fieldtype": "Long Text", "label": "What the card said"},
    {"fieldname": "dup_hint", "fieldtype": "Data", "label": "Looks like (not joined)"},
]


def ensure():
    """Called from souk.ensure_doctype (after_migrate)."""
    if not frappe.db.exists("DocType", DT_VISIT):
        frappe.get_doc({
            "doctype": "DocType", "name": DT_VISIT, "module": "Core", "custom": 1,
            "naming_rule": "Autoincrement", "autoname": "autoincrement",
            "fields": VISIT_FIELDS,
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}],
        }).insert(ignore_permissions=True)
    else:
        S._add_missing_fields(DT_VISIT, VISIT_FIELDS)


def _ready():
    return bool(frappe.db.exists("DocType", DT_VISIT))


def _need_ready():
    if not _ready():
        frappe.throw("The market round is being installed — it works after the next update.")


def _gate():
    if S._role() not in ROLES:
        frappe.throw("Not authorized for the market round.", frappe.PermissionError)


def _sees_all():
    return S._role() in ("manager", "sourcing")


def _P():
    from logistics_portal.api import souk_picks
    return souk_picks


def _ST():
    from logistics_portal.api import souk_stalls
    return souk_stalls


# --- small helpers ---------------------------------------------------------------

def _metres(a_lat, a_lng, b_lat, b_lng):
    r = 6371000.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lng - a_lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def _gps(lat, lng):
    lat, lng = flt(lat), flt(lng)
    if not (-90 <= lat <= 90 and -180 <= lng <= 180) or (not lat and not lng):
        return None, None
    return round(lat, 7), round(lng, 7)


def _text(v, n):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _tg_of(link):
    """(state, handle, link): public channel, private invite, or none."""
    raw = _text(link, 200)
    if not raw:
        return "none", "", ""
    h = _P().handle_of(raw)
    if h:
        return "public", h, _P()._link(h)
    if re.search(r"(t(?:elegram)?\.me|telegram\.dog)/", raw, re.I):
        return "private", "", raw if raw.lower().startswith("http") else "https://" + raw
    return "none", "", ""


def _place_text(market, place):
    return " · ".join(x for x in (_text(market, 40), _text(place, 80)) if x)


def _markets():
    """The defaults, then every market the rounds used, the busiest first."""
    used = []
    if _ready():
        used = [r[0] for r in frappe.db.sql(
            f"""SELECT market FROM `tab{DT_VISIT}` WHERE IFNULL(market, '') != ''
                GROUP BY market ORDER BY COUNT(*) DESC LIMIT 30""")]
    return list(dict.fromkeys(used + MARKETS))


def _row(v, names):
    return {"name": v.name, "supplier": v.supplier, "label": v.supplier_name or v.shop_name or v.supplier,
            "market": v.market or "", "place": v.place or "", "tg": v.tg_state or "none",
            "outcome": v.outcome or "new", "at": str(v.visited_at or "")[:16], "photo": v.shop_photo or "",
            "by": names.get(v.scout, v.scout or ""), "dup": v.dup_hint or ""}


def _visits(where, args, limit=200):
    rows = frappe.db.sql(
        f"""SELECT v.name, v.supplier, v.scout, v.visited_at, v.market, v.place, v.tg_state, v.outcome,
                   v.shop_photo, v.shop_name, v.dup_hint, s.supplier_name
            FROM `tab{DT_VISIT}` v LEFT JOIN `tabSupplier` s ON s.name = v.supplier
            WHERE {where} ORDER BY v.visited_at DESC LIMIT {cint(limit)}""", args, as_dict=True)
    names = {u: S._user_name(u) for u in {r.scout for r in rows if r.scout}}
    return [_row(r, names) for r in rows]


# --- the screen ------------------------------------------------------------------

@frappe.whitelist()
def scout_boot(who="me", day=""):
    """Today's round: the markets, the categories, the shops registered."""
    _gate()
    from logistics_portal.api import clock
    s = S.settings()
    out = {
        "ready": _ready(), "me": frappe.session.user, "role": S._role(), "seesAll": _sees_all(),
        "markets": _markets(),
        "categories": [{"key": c["key"], "ar": c.get("ar") or c["key"], "fr": c.get("fr") or c["key"]}
                       for c in s["categories"]],
        "day": clock.floor_today(), "rows": [], "stats": {"shops": 0, "channels": 0, "new": 0},
        "cardReader": _card_reader_ok(),
    }
    if not out["ready"]:
        return out
    day = str(day or out["day"])[:10]
    a, b = clock.day_bounds(day)
    where, args = "v.visited_at >= %(a)s AND v.visited_at < %(b)s", {"a": a, "b": b}
    if not (_sees_all() and who == "all"):
        where += " AND v.scout = %(u)s"
        args["u"] = frappe.session.user
    rows = _visits(where, args)
    out.update(day=day, rows=rows, stats={
        "shops": len(rows), "channels": sum(1 for r in rows if r["tg"] == "public"),
        "new": sum(1 for r in rows if r["outcome"] == "new")})
    return out


# --- step 2: the business card -----------------------------------------------------

CARD_SYSTEM = """You read the business card of a wholesale shop in a Moroccan market (Derb Omar in Casablanca and similar). Cards are in French, Arabic or both, sometimes with Darija, decorative fonts, several phone numbers and social links or QR codes.

Return only what is printed on the card:
- name: the shop's trading name, in Latin capital letters. If it is printed only in Arabic, transliterate it the way Moroccans write it in French (e.g. محلات الأمين → AMINE). Drop words like "Sté", "SARL", "Ets" unless they are the whole name.
- phones: every phone number, as printed, mobile numbers first. Moroccan numbers only start with 05, 06, 07 or +212.
- whatsapp: the number shown with a WhatsApp logo or label, if any.
- telegram: a t.me link or an @handle shown with a Telegram logo or label, if any.
- instagram, facebook: the handle or link, if any.
- place: where the shop is inside the market (row, number, floor, "Derb Omar", street), as printed.
- sells: a few words on what the card says they sell, in French.
Use "" for anything that is not on the card. Never invent a number or a link."""

CARD_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["name", "phones", "whatsapp", "telegram", "instagram", "facebook", "place", "sells", "is_card"],
    "properties": {
        "is_card": {"type": "boolean", "description": "false when the photo is not a business card"},
        "name": {"type": "string"}, "phones": {"type": "array", "items": {"type": "string"}},
        "whatsapp": {"type": "string"}, "telegram": {"type": "string"}, "instagram": {"type": "string"},
        "facebook": {"type": "string"}, "place": {"type": "string"}, "sells": {"type": "string"},
    },
}


def _card_reader_ok():
    from logistics_portal.api import souk_write
    return bool(souk_write._key()) and souk_write._sdk_ok()


def _read_card_bytes(content):
    """The card photo → the fields printed on it (CARD_SCHEMA, cleaned)."""
    import base64
    import io
    import anthropic
    from PIL import Image, ImageOps
    from logistics_portal.api import souk_write
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(content))).convert("RGB")
    im.thumbnail((1568, 1568))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    client = anthropic.Anthropic(api_key=souk_write._key(), timeout=60, max_retries=1)
    resp = client.messages.create(
        model=CARD_MODEL, max_tokens=1500, system=CARD_SYSTEM,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": CARD_SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.b64encode(buf.getvalue()).decode()}},
            {"type": "text", "text": "Read this card."}]}],
    )
    if resp.stop_reason in ("refusal", "max_tokens"):
        raise Exception(f"card read stopped: {resp.stop_reason}")
    raw = json.loads(next((b.text for b in resp.content if b.type == "text"), "") or "{}")
    return _clean_card(raw)


def _clean_card(raw):
    ST = _ST()
    phones = []
    for p in list(raw.get("phones") or []) + [raw.get("whatsapp") or ""]:
        c = ST._clean_phone(str(p))
        if len(re.sub(r"\D", "", c)) >= 9 and ST._phone_key(c) not in {ST._phone_key(x) for x in phones}:
            phones.append(c)
    tg = _text(raw.get("telegram"), 200)
    if tg.startswith("@"):
        tg = "t.me/" + tg[1:]
    return {"isCard": bool(raw.get("is_card", True)), "name": ST._clean_name(raw.get("name"))[:80],
            "phones": phones[:4], "whatsapp": ST._clean_phone(str(raw.get("whatsapp") or "")),
            "telegram": tg, "instagram": _text(raw.get("instagram"), 120),
            "facebook": _text(raw.get("facebook"), 120), "place": _text(raw.get("place"), 120),
            "sells": _text(raw.get("sells"), 160)}


@frappe.whitelist(methods=["POST"])
def read_card():
    """The card photo from the phone: kept (attached to its visit at the
    save) and read. Returns {url, card} — card is null when no reader."""
    _gate()
    content, ext = S._read_upload()
    # Not attached yet: the visit does not exist until the save.
    fdoc = frappe.get_doc({"doctype": "File", "is_private": 0, "content": content,
                           "file_name": f"souk-scout-card-{frappe.generate_hash(length=16)}.{ext}"}
                          ).insert(ignore_permissions=True)
    card, why = None, ""
    if _card_reader_ok():
        try:
            card = _read_card_bytes(content)
        except Exception:
            why = "failed"
            frappe.log_error(frappe.get_traceback()[:2500], "souk_scout.read_card")
    else:
        why = "off"
    frappe.db.commit()
    return {"url": fdoc.file_url, "card": card, "why": why}


# --- step 3: Telegram ---------------------------------------------------------------

def _preview(h):
    """The channel's public page: title, subscribers, last posts. None when it
    has no public preview (a group, a person, a wrong name)."""
    import requests
    from bs4 import BeautifulSoup
    P = _P()
    resp = requests.get(f"https://t.me/s/{h}", headers={"User-Agent": P.UA, "Accept-Language": "fr,ar;q=0.8"},
                        timeout=12, allow_redirects=True)
    if resp.status_code != 200:
        return None
    posts = P.parse_channel(resp.text, h)
    if posts is None:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.select_one(".tgme_channel_info_header_title")
    subs = 0
    for c in soup.select(".tgme_channel_info_counter"):
        kind = c.select_one(".counter_type")
        if kind and "subscriber" in kind.get_text().lower():
            v = (c.select_one(".counter_value").get_text() if c.select_one(".counter_value") else "").strip().upper()
            m = re.match(r"([\d.,]+)\s*([KM]?)", v)
            if m:
                n = flt(m.group(1).replace(",", "."))
                subs = int(n * (1000 if m.group(2) == "K" else 1000000 if m.group(2) == "M" else 1))
    last = max((p["at"] for p in posts if p.get("at")), default="")
    photos = [p["photo"] for p in sorted(posts, key=lambda x: -x["id"]) if p.get("photo")][:4]
    return {"title": _text(title.get_text() if title else h, 120), "subscribers": subs,
            "last": str(P._when(last))[:16] if last else "", "posts": len(posts), "photos": photos}


@frappe.whitelist()
def check_telegram(link):
    """Is this the shop's public channel? Asked while the person still
    stands at the shop, so a wrong link is fixed there."""
    _gate()
    state, h, url = _tg_of(link)
    out = {"state": state, "handle": h, "link": url, "known": None, "preview": None}
    if state != "public":
        return out
    known = _P()._source_by_handle(h)
    if known:
        out["known"] = {"name": known.name, "label": known.supplier_name or known.name,
                        "lead": known.supplier_group == _P().LEAD_GROUP}
    key = f"lp_scout_tg:{h.lower()}"
    cached = frappe.cache().get_value(key)
    if cached is None:
        try:
            cached = _preview(h) or {}
        except Exception:
            cached = {"error": 1}
        if not cached.get("error"):
            frappe.cache().set_value(key, cached, expires_in_sec=600)
    if cached.get("error"):
        out["state"], out["unreachable"] = "public", True
    elif not cached:
        out["state"] = "nopreview"        # no public page: cannot be read automatically
    else:
        out["preview"] = cached
    return out


# --- the same shop twice? ----------------------------------------------------------------

def _shops():
    P = _P()
    return frappe.db.sql(
        """SELECT name, supplier_name, supplier_group, mobile_no, website, supplier_details, image, owner, creation
           FROM `tabSupplier` WHERE supplier_group IN %(g)s AND disabled = 0""",
        {"g": (P.LEAD_GROUP, S.SUPPLIER_GROUP)}, as_dict=True)


def _contact_phones(names):
    """Every phone on the shops' Contacts (the second number lives there)."""
    out = {}
    if not names:
        return out
    for r in frappe.db.sql(
            """SELECT dl.link_name, cp.phone FROM `tabDynamic Link` dl
               JOIN `tabContact Phone` cp ON cp.parent = dl.parent
               WHERE dl.link_doctype = 'Supplier' AND dl.parenttype = 'Contact' AND dl.link_name IN %s""",
            (tuple(names),)):
        out.setdefault(r[0], set()).add(_ST()._phone_key(r[1]))
    return out


def _last_fix(names):
    if not (names and _ready()):
        return {}
    out = {}
    for r in frappe.db.sql(
            f"""SELECT supplier, lat, lng FROM `tab{DT_VISIT}`
                WHERE supplier IN %s AND lat IS NOT NULL AND lat != 0 ORDER BY visited_at""",
            (tuple(names),), as_dict=True):
        out[r.supplier] = (r.lat, r.lng)
    return out


def find_same(name="", phones=(), handle="", lat=None, lng=None, limit=4):
    """Shops (leads and stalls) that may be this one, strongest first.
    why: phone | telegram | near | name."""
    import difflib
    ST = _ST()
    keys = {k for k in (ST._phone_key(ST._clean_phone(p)) for p in phones) if k}
    nn = ST._norm_name(name)
    rows = _shops()
    extra = _contact_phones([r.name for r in rows]) if keys else {}
    fixes = _last_fix([r.name for r in rows]) if lat is not None else {}
    out = []
    for r in rows:
        why, dist = [], None
        rk = {ST._phone_key(ST._clean_phone(r.mobile_no or ""))} | extra.get(r.name, set())
        if keys & rk:
            why.append("phone")
        if handle and _P().handle_of(r.website or "").lower() == handle.lower():
            why.append("telegram")
        rn = ST._norm_name(r.supplier_name or r.name)
        similar = len(nn) >= 3 and (rn == nn or (min(len(rn), len(nn)) >= 4 and (rn in nn or nn in rn))
                                    or difflib.SequenceMatcher(None, rn, nn).ratio() >= 0.82)
        if lat is not None and r.name in fixes:
            dist = _metres(lat, lng, *fixes[r.name])
            if dist <= NEAR_M and similar:
                why.append("near")
        if similar and rn == nn and "near" not in why:
            why.append("name")
        if not why:
            continue
        out.append({"name": r.name, "label": r.supplier_name or r.name, "lead": r.supplier_group == _P().LEAD_GROUP,
                    "place": ST._place_of(r.supplier_details), "photo": r.image or "",
                    "by": S._user_name(r.owner), "at": str(r.creation)[:10], "why": why,
                    "metres": int(round(dist)) if dist is not None and dist < 1000 else None,
                    "strong": bool({"phone", "telegram"} & set(why))})
    out.sort(key=lambda m: (not m["strong"], "near" not in m["why"], m["metres"] if m["metres"] is not None else 9e9))
    return out[:limit]


@frappe.whitelist()
def similar(name="", phone="", phone2="", telegram="", lat=None, lng=None):
    _gate()
    la, ln = _gps(lat, lng)
    _, h, _ = _tg_of(telegram)
    return {"rows": find_same(name, [phone, phone2], h, la, ln)}


# --- save ----------------------------------------------------------------------------------

def _payload(raw):
    p = frappe.parse_json(raw) if isinstance(raw, str) else (raw or {})
    if not isinstance(p, dict):
        frappe.throw("Bad request.")
    return p


def _free_name(label):
    if not frappe.db.exists("Supplier", label):
        return label
    for n in range(2, 50):
        alt = f"{label} {n}"[:140]
        if not frappe.db.exists("Supplier", alt):
            return alt
    frappe.throw(f"{label} already exists: give this shop another name.")


def _add_phone(sup, label, phone):
    """A second number on the shop's Contact, next to the primary one."""
    ST = _ST()
    phone = ST._clean_phone(phone)
    if len(re.sub(r"\D", "", phone)) < 9:
        return
    cur = frappe.db.get_value("Supplier", sup, "supplier_primary_contact")
    if not (cur and frappe.db.exists("Contact", cur)):
        ST._set_phone(sup, label, phone)
        return
    c = frappe.get_doc("Contact", cur)
    if ST._phone_key(phone) in {ST._phone_key(p.phone) for p in c.phone_nos}:
        return
    c.append("phone_nos", {"phone": phone})
    c.save(ignore_permissions=True)


def _sells(v):
    return _ST()._clean_sells(v)


def _about(p, card):
    """The shop's description lines: the person's note, what the card says
    the shop sells, and its Instagram (the selection reads these; nothing
    else on the Supplier holds them)."""
    lines = [_text(p.get("note"), 300)]
    sells = _text((card or {}).get("sells"), 160)
    if sells:
        lines.append("Sells: " + sells)
    ig = _text(p.get("instagram") or (card or {}).get("instagram"), 80).lstrip("@")
    if ig:
        lines.append("Instagram: @" + ig)
    return [x for x in lines if x]


def _add_about(sup, lines):
    """Append the lines the description does not hold yet (never replaces)."""
    if not lines or not S._has_col("Supplier", "custom_business_description"):
        return
    had = frappe.db.get_value("Supplier", sup, "custom_business_description") or ""
    new = [x for x in lines if x not in had]
    if new:
        frappe.db.set_value("Supplier", sup, "custom_business_description",
                            "\n".join(([had] if had else []) + new)[:500], update_modified=False)


def _card_extra_phones(card, have):
    """The card's numbers past the two that fill the phone fields (the person
    may have corrected those): every printed number reaches the Contact."""
    ST = _ST()
    keys = {ST._phone_key(x) for x in have if x}
    out = []
    for ph in list((card or {}).get("phones") or [])[2:]:
        k = ST._phone_key(ph)
        if k and k not in keys:
            keys.add(k)
            out.append(ph)
    return out


def _create_shop(p, tg_state, tg_link, card=None):
    ST, P = _ST(), _P()
    label = _free_name(ST._clean_name(p.get("name"))[:140])
    sup = frappe.get_doc({
        "doctype": "Supplier", "supplier_name": label, "supplier_group": P._lead_group(),
        "supplier_type": "Company", "country": "Morocco", "default_currency": "MAD",
        "website": tg_link if tg_state in ("public", "private") else "",
        "supplier_details": ST.PLACE_PREFIX + (_place_text(p.get("market"), p.get("place")) or "Derb Omar"),
    }).insert(ignore_permissions=True)
    rest = {"sells": _sells(p.get("sells"))}
    about = _about(p, card)
    if about:
        rest["note"] = "\n".join(about)[:500]
    ST._apply(sup.name, rest, label)
    if p.get("phone"):
        ST._set_phone(sup.name, label, p.get("phone"))
    for ph in [p.get("phone2")] + _card_extra_phones(card, [p.get("phone"), p.get("phone2")]):
        if ph:
            _add_phone(sup.name, label, ph)
    return sup.name


def _fill_shop(sup, p, tg_state, tg_link, card=None):
    """An existing shop gets what it was missing; nothing it had is replaced
    (a buyer's corrections win over a second visit)."""
    ST, P = _ST(), _P()
    cur = frappe.db.get_value("Supplier", sup, ["supplier_name", "website", "supplier_details", "mobile_no"],
                              as_dict=True)
    label = cur.supplier_name or sup
    upd = {}
    if tg_state == "public" and not P.handle_of(cur.website or ""):
        upd["website"] = tg_link
    elif tg_state == "private" and not (cur.website or "").strip():
        upd["website"] = tg_link
    if not ST._place_of(cur.supplier_details) and _place_text(p.get("market"), p.get("place")):
        upd["supplier_details"] = ST.PLACE_PREFIX + _place_text(p.get("market"), p.get("place"))
    if upd:
        frappe.db.set_value("Supplier", sup, upd, update_modified=True)
    if S._has_col("Supplier", "custom_product_categories"):
        had = [x for x in (frappe.db.get_value("Supplier", sup, "custom_product_categories") or "").split(",") if x]
        both = _sells(had + _sells(p.get("sells")))
        if both != had:
            frappe.db.set_value("Supplier", sup, "custom_product_categories", ",".join(both), update_modified=False)
    _add_about(sup, _about(p, card))
    for ph in [p.get("phone"), p.get("phone2")] + _card_extra_phones(card, [p.get("phone"), p.get("phone2")]):
        if ph:
            if cur.mobile_no:
                _add_phone(sup, label, ph)
            else:
                ST._set_phone(sup, label, ph)
                cur.mobile_no = ph
    return upd.get("website") == tg_link and tg_state == "public"


def _result(v):
    sup = frappe.db.get_value("Supplier", v.supplier, ["supplier_name", "supplier_group"], as_dict=True) or {}
    return {"visit": v.name, "supplier": v.supplier, "label": sup.get("supplier_name") or v.supplier,
            "lead": sup.get("supplier_group") == _P().LEAD_GROUP, "outcome": v.outcome,
            "tg": v.tg_state or "none", "market": v.market or "", "place": v.place or "",
            "dup": v.dup_hint or ""}


@frappe.whitelist(methods=["POST"])
def save_visit(payload):
    """One shop from the round. payload: clientKey, target ("" | a shop's
    name = the same shop | "new" = another shop), name, phone, phone2,
    telegram, instagram, market, place, sells, note, lat, lng, accuracy,
    cardUrl, card (what the reader said). A retry with the same clientKey
    answers with the visit already made."""
    _gate()
    _need_ready()
    p = _payload(payload)
    key = _text(p.get("clientKey"), 60)
    if key:
        old = frappe.db.get_value(DT_VISIT, {"client_key": key}, ["name", "supplier", "outcome", "tg_state",
                                                                  "market", "place", "dup_hint"], as_dict=True)
        if old:
            return _result(old)
    ST, P = _ST(), _P()
    name = ST._clean_name(p.get("name"))
    if len(name) < 3:
        frappe.throw("The shop's name, in Latin letters (e.g. AMINE DECO).")
    for k in ("phone", "phone2"):
        p[k] = ST._clean_phone(p.get(k))
        if p[k] and len(re.sub(r"\D", "", p[k])) < 9:
            frappe.throw("The phone number is too short.")
    tg_state, h, tg_link = _tg_of(p.get("telegram"))
    la, ln = _gps(p.get("lat"), p.get("lng"))
    target = _text(p.get("target"), 140)
    outcome, dup = "new", ""

    if target and target != "new":
        if frappe.db.get_value("Supplier", target, "supplier_group") not in (P.LEAD_GROUP, S.SUPPLIER_GROUP):
            frappe.throw("That shop is not in the souk.")
        sup, outcome = target, "same"
    else:
        same = find_same(name, [p["phone"], p["phone2"]], h, la, ln)
        strong = [m for m in same if m["strong"]]
        if target != "new" and strong:
            # Saved offline, never asked: only a phone or a channel joins.
            sup, outcome = strong[0]["name"], "auto"
        else:
            sup = None
            dup = same[0]["label"] if same else ""
    card = p.get("card") if isinstance(p.get("card"), dict) else None
    if card and card.get("isCard") is False:
        card_for_shop = None
    else:
        card_for_shop = card
    if sup:
        new_channel = _fill_shop(sup, p, tg_state, tg_link, card_for_shop)
    else:
        sup = _create_shop(p, tg_state, tg_link, card_for_shop)
        new_channel = tg_state == "public"
    v = frappe.get_doc({
        "doctype": DT_VISIT, "supplier": sup, "scout": frappe.session.user, "visited_at": now_datetime(),
        "outcome": outcome, "client_key": key or None, "market": _text(p.get("market"), 40),
        "place": _text(p.get("place"), 80), "lat": la, "lng": ln,
        "accuracy": max(0, min(cint(p.get("accuracy")), 100000)) if la is not None else 0,
        "shop_name": name, "phone": p["phone"], "phone2": p["phone2"], "telegram": tg_link,
        "tg_state": tg_state, "instagram": _text(p.get("instagram"), 120),
        "sells": ",".join(_sells(p.get("sells"))), "note": _text(p.get("note"), 500),
        "card_json": json.dumps(card, ensure_ascii=False)[:5000] if card else None, "dup_hint": dup[:140],
    }).insert(ignore_permissions=True)
    url = _text(p.get("cardUrl"), 300)
    if url:
        _attach(v.name, "card_photo", url)
    frappe.db.commit()
    if new_channel and h and P._ready():
        frappe.enqueue("logistics_portal.api.souk_picks.scrape_one", queue="long", timeout=600,
                       handle=h, enqueue_after_commit=True)
    return _result(v)


def _attach(visit, field, url):
    fname = frappe.db.get_value("File", {"file_url": url}, "name")
    if fname and not frappe.db.get_value("File", fname, "attached_to_name"):
        frappe.db.set_value("File", fname, {"attached_to_doctype": DT_VISIT, "attached_to_name": str(visit),
                                            "attached_to_field": field}, update_modified=False)
    frappe.db.set_value(DT_VISIT, visit, field, url, update_modified=False)


def _own_visit(visit):
    v = frappe.db.get_value(DT_VISIT, visit, ["name", "scout", "supplier", "card_json"], as_dict=True)
    if not v:
        frappe.throw("Visit not found.")
    if v.scout != frappe.session.user and S._role() != "manager":
        frappe.throw("This is somebody else's visit.", frappe.PermissionError)
    return v


@frappe.whitelist(methods=["POST"])
def visit_photo(visit, kind):
    """A photo sent after the visit (the outbox: saved offline). kind: shop
    (the storefront; also the shop's own image when it has none) | card
    (the business card; read in the background when nobody read it yet)."""
    _gate()
    v = _own_visit(visit)
    if kind not in ("shop", "card"):
        frappe.throw("Unknown photo kind.")
    content, ext = S._read_upload()
    fdoc = S._insert_file("scout-" + kind, DT_VISIT, v.name, content, ext)
    field = "shop_photo" if kind == "shop" else "card_photo"
    frappe.db.set_value(DT_VISIT, v.name, field, fdoc.file_url, update_modified=False)
    if kind == "shop" and not frappe.db.get_value("Supplier", v.supplier, "image"):
        frappe.db.set_value("Supplier", v.supplier, "image", fdoc.file_url, update_modified=False)
    frappe.db.commit()
    if kind == "card" and not v.card_json and _card_reader_ok():
        frappe.enqueue("logistics_portal.api.souk_scout.read_later", queue="default", timeout=300,
                       visit=v.name, enqueue_after_commit=True)
    return {"url": fdoc.file_url}


def read_later(visit):
    """A card that came in offline: read it now and fill what the shop is
    still missing (the person already typed the name; never replaced)."""
    v = frappe.get_doc(DT_VISIT, visit)
    if v.card_json or not v.card_photo:
        return
    fname = frappe.db.get_value("File", {"file_url": v.card_photo}, "name")
    if not fname:
        return
    try:
        card = _read_card_bytes(frappe.get_doc("File", fname).get_content())
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2500], "souk_scout.read_later")
        return
    v.db_set("card_json", json.dumps(card, ensure_ascii=False)[:5000], update_modified=False)
    if card.get("isCard") is False:
        frappe.db.commit()
        return
    p = {"phone": "", "phone2": "", "sells": [], "note": "", "market": "", "place": "",
         "instagram": v.instagram or ""}
    phones = [x for x in card.get("phones") or [] if _ST()._phone_key(x) not in
              {_ST()._phone_key(v.phone or ""), _ST()._phone_key(v.phone2 or "")}]
    tg_state, h, tg_link = _tg_of(card.get("telegram"))
    # Every printed number the person did not type goes on the Contact; the
    # fill never replaces anything the shop already holds.
    new_channel = _fill_shop(v.supplier, p, tg_state, tg_link,
                             {**card, "phones": [None, None] + phones})
    if tg_state != "none" and (v.tg_state or "none") == "none":
        v.db_set({"telegram": tg_link, "tg_state": tg_state}, update_modified=False)
    frappe.db.commit()
    if new_channel and h and _P()._ready():
        _P().scrape_one(h)


@frappe.whitelist()
def visit(name):
    """One registered shop, as the round saw it (the done screen, the list)."""
    _gate()
    _need_ready()
    v = frappe.get_doc(DT_VISIT, name)
    if v.scout != frappe.session.user and not _sees_all():
        frappe.throw("This is somebody else's visit.", frappe.PermissionError)
    out = _result(v)
    out.update({"shopPhoto": v.shop_photo or "", "cardPhoto": v.card_photo or "", "phone": v.phone or "",
                "phone2": v.phone2 or "", "telegram": v.telegram or "", "sells": [x for x in (v.sells or "").split(",") if x],
                "note": v.note or "", "lat": v.lat, "lng": v.lng, "accuracy": v.accuracy,
                "at": str(v.visited_at)[:16], "by": S._user_name(v.scout), "name": v.shop_name})
    return out
