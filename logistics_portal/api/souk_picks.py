"""Selection: what the wholesalers post, what we choose to buy (2026-11-20).

Phase A of the selection cycle (Ahmed's approval; Manal decides):

  Sources   the wholesalers' public Telegram channels. Each one is a Supplier
            in the "Souk Leads" group (a lead, not a stall yet) whose Telegram
            link lives in the standard Supplier.website field. Buying from a
            lead makes it a stall: its group becomes "Souk Suppliers".
  Posts     every 3 hours the public preview of each channel
            (https://t.me/s/<handle>) is read. The first photo of each new
            post becomes a small thumbnail (internal reference only; never
            published) with a 64-bit difference hash (dHash).
  Picks     posts whose photos hash within PICK_DISTANCE bits are the same
            product: one Pick, however many channels post it. A product that
            3 sources post within 7 days is "trending"; one posted for weeks
            by many is "saturated".
  Flow      anyone in the souk marks a pick "interested" → the decider
            (settings: selectionDeciders, default Manal) says buy (target
            quantity, max price, from which source) or no (with a reason) →
            the shopping list, grouped by source → the buyer opens SoukBuy
            from it: the photo, the stall and the max price come prefilled,
            and the new card is linked back to the pick ("bought").

Unflagged posts older than 30 days are deleted with their thumbnails.
Doctypes are System Manager only; the portal gates (souk._gate_view / buy).
"""

import io
import json
import re
from contextlib import contextmanager

import frappe
from frappe.utils import add_days, cint, flt, get_datetime, now_datetime

from logistics_portal.api import souk as S

DT_POST = "LP Souk Post"
DT_PICK = "LP Souk Pick"
LEAD_GROUP = "Souk Leads"
STATE_KEY = "lp_souk_picks_state"        # per handle: last read, error, count
CONF_KEY = "lp_souk_picks_conf"          # deciders
DEFAULT_DECIDERS = ["manal@justyol.com"]

PICK_DISTANCE = 6        # dHash bits: ≤ 6 of 64 = the same photo, resized/re-encoded
MATCH_DAYS = 60          # a post is matched against picks seen in this window
TREND_SOURCES = 3        # distinct sources within TREND_DAYS = trending
TREND_DAYS = 7
SATURATED_DAYS = 21      # first seen this long ago and posted by ≥ SATURATED_SOURCES
SATURATED_SOURCES = 5
KEEP_DAYS = 30
THUMB_PX = 480
MAX_PAGES = 4            # pages of 20 posts read back per channel per run
RUN_BUDGET = 400         # new posts per run, all channels together
REASONS = ("price", "quality", "have_it", "style", "saturated", "other")
STATUSES = ("new", "interested", "approved", "rejected", "bought")
UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36")


# --- schema ------------------------------------------------------------------

def ensure():
    """Called from souk.ensure_doctype (after_migrate)."""
    if not frappe.db.exists("DocType", DT_PICK):
        frappe.get_doc({
            "doctype": "DocType", "name": DT_PICK, "module": "Core", "custom": 1,
            "naming_rule": "Autoincrement", "autoname": "autoincrement", "track_changes": 1,
            "fields": [
                {"fieldname": "title", "fieldtype": "Data", "label": "Title", "in_list_view": 1},
                {"fieldname": "photo", "fieldtype": "Attach Image", "label": "Photo"},
                {"fieldname": "dhash", "fieldtype": "Data", "label": "Photo hash", "search_index": 1},
                {"fieldname": "caption", "fieldtype": "Small Text", "label": "First caption"},
                {"fieldname": "status", "fieldtype": "Select", "label": "Status", "in_list_view": 1,
                 "options": "\n".join(STATUSES), "default": "new", "search_index": 1},
                {"fieldname": "first_seen", "fieldtype": "Datetime", "label": "First seen"},
                {"fieldname": "last_seen", "fieldtype": "Datetime", "label": "Last seen", "search_index": 1},
                {"fieldname": "sources_n", "fieldtype": "Int", "label": "Sources"},
                {"fieldname": "posts_n", "fieldtype": "Int", "label": "Posts"},
                {"fieldname": "trend_n", "fieldtype": "Int", "label": "Sources in the last 7 days"},
                {"fieldname": "interested_json", "fieldtype": "Small Text", "label": "Interested (users)"},
                {"fieldname": "interested_at", "fieldtype": "Datetime", "label": "First interest"},
                {"fieldname": "decided_by", "fieldtype": "Data", "label": "Decided by"},
                {"fieldname": "decided_at", "fieldtype": "Datetime", "label": "Decided at"},
                {"fieldname": "reason", "fieldtype": "Data", "label": "Reason (no)"},
                {"fieldname": "note", "fieldtype": "Small Text", "label": "Note"},
                {"fieldname": "target_qty", "fieldtype": "Int", "label": "Target quantity"},
                {"fieldname": "max_price", "fieldtype": "Currency", "label": "Max cost per piece"},
                {"fieldname": "source", "fieldtype": "Link", "options": "Supplier", "label": "Buy from"},
                {"fieldname": "category", "fieldtype": "Data", "label": "Category"},
                {"fieldname": "product", "fieldtype": "Data", "label": "Souk card"},
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}],
        }).insert(ignore_permissions=True)
    if not frappe.db.exists("DocType", DT_POST):
        frappe.get_doc({
            "doctype": "DocType", "name": DT_POST, "module": "Core", "custom": 1,
            "naming_rule": "Random", "autoname": "hash",
            "fields": [
                {"fieldname": "source", "fieldtype": "Link", "options": "Supplier", "label": "Source", "in_list_view": 1},
                {"fieldname": "channel", "fieldtype": "Data", "label": "Channel", "search_index": 1},
                {"fieldname": "post_id", "fieldtype": "Int", "label": "Post id"},
                {"fieldname": "posted_at", "fieldtype": "Datetime", "label": "Posted at", "search_index": 1},
                {"fieldname": "caption", "fieldtype": "Small Text", "label": "Caption"},
                {"fieldname": "thumb", "fieldtype": "Attach Image", "label": "Thumbnail"},
                {"fieldname": "dhash", "fieldtype": "Data", "label": "Photo hash"},
                {"fieldname": "pick", "fieldtype": "Data", "label": "Pick", "search_index": 1},
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}],
        }).insert(ignore_permissions=True)
        try:
            frappe.db.add_unique(DT_POST, ["channel", "post_id"], constraint_name="souk_post_channel_id")
        except Exception:
            frappe.log_error(frappe.get_traceback()[:1500], "souk_picks.ensure unique")


def _ready():
    return frappe.db.exists("DocType", DT_PICK) and frappe.db.exists("DocType", DT_POST)


def _need_ready():
    if not _ready():
        frappe.throw("The selection screen is being installed — it works after the next update.")


def _lead_group():
    if not frappe.db.exists("Supplier Group", LEAD_GROUP):
        frappe.get_doc({"doctype": "Supplier Group", "supplier_group_name": LEAD_GROUP,
                        "parent_supplier_group": "All Supplier Groups"}).insert(ignore_permissions=True)
    return LEAD_GROUP


# --- settings: who decides -----------------------------------------------------

def _conf():
    try:
        c = json.loads(frappe.db.get_default(CONF_KEY) or "{}")
    except ValueError:
        c = {}
    c = c if isinstance(c, dict) else {}
    d = c.get("deciders")
    c["deciders"] = [str(x).strip().lower() for x in d if str(x).strip()] if isinstance(d, list) else list(DEFAULT_DECIDERS)
    return c


def _deciders():
    return _conf()["deciders"]


def _can_decide():
    me = (frappe.session.user or "").lower()
    d = _deciders()
    # An empty list falls back to the managers: someone must be able to.
    return me in d or (not d and S._role() == "manager")


def _gate_decide():
    if not _can_decide():
        names = ", ".join(S._user_name(u) for u in _deciders()) or "the manager"
        frappe.throw(f"The buying decision is {names}'s.", frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def save_deciders(users):
    """Manager only: who says buy / no. users: JSON list of User ids."""
    if S._role() != "manager":
        frappe.throw("Managers only.", frappe.PermissionError)
    lst = frappe.parse_json(users) if isinstance(users, str) else (users or [])
    if not isinstance(lst, list):
        frappe.throw("Bad list.")
    out = []
    for u in lst:
        u = str(u or "").strip().lower()
        if not u:
            continue
        if not frappe.db.exists("User", u) or not cint(frappe.db.get_value("User", u, "enabled")):
            frappe.throw(f"{u} is not an active user.")
        if u not in out:
            out.append(u)
    c = _conf()
    c["deciders"] = out[:5]
    frappe.db.set_default(CONF_KEY, json.dumps(c))
    frappe.db.commit()
    return _people(c["deciders"])


def _people(users):
    return [{"user": u, "name": S._user_name(u)} for u in users]


# --- sources -------------------------------------------------------------------

_HANDLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")


def handle_of(link):
    """t.me/x, https://t.me/s/x, telegram.me/x, @x, x → x (or "")."""
    s = str(link or "").strip()
    m = re.search(r"(?:t(?:elegram)?\.me|telegram\.dog)/(?:s/)?([A-Za-z0-9_+]+)", s, re.I)
    h = m.group(1) if m else s.lstrip("@").split("/")[0].split("?")[0]
    if h.startswith("+") or h.lower() in ("joinchat", "addlist", "c"):
        return ""          # an invite link: a private group, not readable here
    return h if _HANDLE.match(h) else ""


def _link(h):
    return f"https://t.me/{h}"


def _source_rows(include_disabled=False):
    """Every Supplier with a Telegram link: the leads and the stalls."""
    groups = (LEAD_GROUP, S.SUPPLIER_GROUP)
    rows = frappe.db.sql(
        """SELECT name, supplier_name, supplier_group, website, mobile_no, disabled, creation, owner
           FROM `tabSupplier`
           WHERE supplier_group IN %(g)s AND (website LIKE '%%t.me/%%' OR website LIKE '%%telegram.me/%%')
           ORDER BY supplier_name""", {"g": groups}, as_dict=True)
    out = []
    for r in rows:
        h = handle_of(r.website)
        if not h or (r.disabled and not include_disabled):
            continue
        out.append(dict(r, handle=h))
    return out


def _source_by_handle(h):
    h = (h or "").lower()
    for r in _source_rows(include_disabled=True):
        if r.handle.lower() == h:
            return r
    return None


def _state():
    try:
        s = json.loads(frappe.db.get_default(STATE_KEY) or "{}")
    except ValueError:
        s = {}
    return s if isinstance(s, dict) else {}


def _save_state(st):
    frappe.db.set_default(STATE_KEY, json.dumps(st))


def add_source(name, link, phone="", note=""):
    """A lead from its Telegram link; the existing one when the channel is
    already known (as a lead or a stall). Returns (supplier, created)."""
    from logistics_portal.api import souk_stalls as ST
    h = handle_of(link)
    if not h:
        frappe.throw("A public Telegram link, like t.me/channelname. "
                     "Private groups (t.me/+…) cannot be read automatically.")
    known = _source_by_handle(h)
    if known:
        if known.disabled:
            frappe.db.set_value("Supplier", known.name, "disabled", 0, update_modified=False)
        return known.name, False
    label = ST._clean_name(name)
    if len(label) < 3:
        label = ST._clean_name(h.replace("_", " "))
    if frappe.db.exists("Supplier", label):
        grp, web = frappe.db.get_value("Supplier", label, ["supplier_group", "website"])
        if grp in (LEAD_GROUP, S.SUPPLIER_GROUP) and not handle_of(web):
            # A stall we know, now with its channel.
            frappe.db.set_value("Supplier", label, "website", _link(h), update_modified=False)
            return label, False
        label = ST._clean_name(f"{label} {h}")[:140]
        if frappe.db.exists("Supplier", label):
            frappe.throw(f"{label} already exists: give this source another name.")
    sup = frappe.get_doc({
        "doctype": "Supplier", "supplier_name": label, "supplier_group": _lead_group(),
        "supplier_type": "Company", "country": "Morocco", "default_currency": "MAD",
        "website": _link(h),
        "supplier_details": "Souk lead · Telegram" + (f" · {str(note).strip()[:200]}" if note else ""),
    }).insert(ignore_permissions=True)
    ph = ST._clean_phone(phone)
    if ph and len(re.sub(r"\D", "", ph)) >= 9:
        ST._set_phone(sup.name, label, ph)
    return sup.name, True


@frappe.whitelist(methods=["POST"])
def create_source(name="", link="", phone="", note=""):
    """Anyone in the souk adds a wholesaler's channel."""
    S._gate_view()
    sup, created = add_source(name, link, phone, note)
    frappe.db.commit()
    if created:
        frappe.enqueue("logistics_portal.api.souk_picks.scrape_one", queue="long", timeout=600,
                       handle=handle_of(link), enqueue_after_commit=True)
    return {"name": sup, "created": created, "sources": _sources_out()}


@frappe.whitelist(methods=["POST"])
def import_sources(text):
    """Manager: one source per line — "name <tab or comma> link" or a link."""
    if S._role() != "manager":
        frappe.throw("Managers only.", frappe.PermissionError)
    added, known, bad = [], [], []
    for raw in str(text or "").splitlines()[:300]:
        line = raw.strip()
        if not line:
            continue
        m = re.search(r"(https?://)?(t(elegram)?\.me/\S+|@[A-Za-z0-9_]{4,})", line, re.I)
        if not m:
            bad.append(line[:80])
            continue
        link = m.group(0)
        name = (line[:m.start()] + " " + line[m.end():]).strip(" \t,;|-")
        try:
            sup, created = add_source(name, link)
            (added if created else known).append(sup)
        except frappe.ValidationError as e:
            frappe.clear_last_message()
            bad.append(f"{line[:60]} — {str(e)[:80]}")
    frappe.db.commit()
    if added:
        frappe.enqueue("logistics_portal.api.souk_picks.scrape_all", queue="long", timeout=1800,
                       job_id="souk_picks_scrape", deduplicate=True, enqueue_after_commit=True)
    return {"added": len(added), "known": len(set(known)), "bad": bad, "sources": _sources_out()}


@frappe.whitelist(methods=["POST"])
def disable_source(name, off=1):
    """Manager: stop (or restart) reading a channel. Its posts stay."""
    if S._role() != "manager":
        frappe.throw("Managers only.", frappe.PermissionError)
    r = frappe.db.get_value("Supplier", name, ["supplier_group", "website"], as_dict=True)
    if not r or not handle_of(r.website):
        frappe.throw("Unknown source.")
    if r.supplier_group == LEAD_GROUP:
        frappe.db.set_value("Supplier", name, "disabled", 1 if cint(off) else 0, update_modified=False)
    else:
        # A stall stays a stall: only its channel is forgotten.
        if cint(off):
            frappe.db.set_value("Supplier", name, "website", None, update_modified=False)
    frappe.db.commit()
    return {"sources": _sources_out()}


@frappe.whitelist(methods=["POST"])
def scrape_now():
    """Manager: read every channel now (the 3-hour job, early)."""
    if S._role() != "manager":
        frappe.throw("Managers only.", frappe.PermissionError)
    _need_ready()
    frappe.enqueue("logistics_portal.api.souk_picks.scrape_all", queue="long", timeout=1800,
                   job_id="souk_picks_scrape", deduplicate=True)
    return {"queued": True}


def _sources_out():
    st = _state()
    week = add_days(now_datetime(), -7)
    counts = {}
    if _ready():
        for r in frappe.db.sql(f"""SELECT source, COUNT(*) n, MAX(posted_at) last FROM `tab{DT_POST}`
                                   WHERE posted_at >= %s GROUP BY source""", (week,), as_dict=True):
            counts[r.source] = r
    out = []
    for r in _source_rows(include_disabled=True):
        s = st.get(r.handle.lower()) or {}
        c = counts.get(r.name) or {}
        out.append({
            "name": r.name, "label": r.supplier_name or r.name, "handle": r.handle, "link": _link(r.handle),
            "phone": r.mobile_no or "", "wa": _wa(r.mobile_no), "stall": r.supplier_group == S.SUPPLIER_GROUP,
            "disabled": bool(r.disabled), "week": cint(c.get("n")),
            "lastPost": str(c.get("last") or s.get("lastPost") or "")[:16],
            "readAt": str(s.get("at") or "")[:16], "error": s.get("err") or "",
        })
    return out


def _wa(phone):
    from logistics_portal.api import souk_stalls as ST
    try:
        return ST._wa(phone or "")
    except Exception:
        return ""


# --- reading the channels --------------------------------------------------------

def run_scrape():
    """hooks: every 3 hours. The work itself runs on the long queue."""
    if not _ready():
        return
    frappe.enqueue("logistics_portal.api.souk_picks.scrape_all", queue="long", timeout=1800,
                   job_id="souk_picks_scrape", deduplicate=True)


def scrape_all():
    if not _ready():
        return
    budget = [RUN_BUDGET]
    hashes = _recent_hashes()
    for r in _source_rows():
        if budget[0] <= 0:
            break
        _scrape_source(r, budget, hashes)


def scrape_one(handle):
    if not _ready():
        return
    r = _source_by_handle(handle)
    if r and not r.disabled:
        _scrape_source(r, [RUN_BUDGET], _recent_hashes())


def _scrape_source(src, budget, hashes):
    import requests
    h = src.handle
    st = _state()
    rec = st.get(h.lower()) or {}
    last_id = cint(frappe.db.sql(f"SELECT MAX(post_id) FROM `tab{DT_POST}` WHERE channel=%s", (h.lower(),))[0][0])
    new, err, before = 0, "", None
    try:
        msgs = []
        for _ in range(MAX_PAGES):
            url = f"https://t.me/s/{h}" + (f"?before={before}" if before else "")
            resp = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "fr,ar;q=0.8,en;q=0.5"},
                                timeout=20, allow_redirects=True)
            if resp.status_code != 200:
                err = f"http {resp.status_code}"
                break
            page = parse_channel(resp.text, h)
            if page is None:
                err = "private"     # no public preview: a private group or a wrong name
                break
            msgs += page
            ids = [m["id"] for m in page]
            # First read of a channel: one page only, no history.
            if not ids or not last_id or min(ids) <= last_id:
                break
            before = min(ids)
        seen = set()
        for m in sorted(msgs, key=lambda x: x["id"]):
            if m["id"] <= last_id or m["id"] in seen or not m.get("photo"):
                continue
            seen.add(m["id"])
            if budget[0] <= 0:
                break
            try:
                if _save_post(src, h, m, hashes):
                    new += 1
                    budget[0] -= 1
                frappe.db.commit()
            except Exception:
                frappe.db.rollback()
                frappe.log_error(frappe.get_traceback()[:2000], f"souk_picks post {h}/{m['id']}")
    except Exception as e:
        err = str(e)[:160] or "error"
    rec.update({"at": str(now_datetime())[:19], "err": err, "new": new})
    if msgs_last := _last_post(h):
        rec["lastPost"] = msgs_last
    st = _state()
    st[h.lower()] = rec
    _save_state(st)
    frappe.db.commit()


def _last_post(h):
    v = frappe.db.sql(f"SELECT MAX(posted_at) FROM `tab{DT_POST}` WHERE channel=%s", (h.lower(),))[0][0]
    return str(v)[:19] if v else ""


_BG = re.compile(r"background-image\s*:\s*url\(\s*['\"]?([^'\")]+)")


def parse_channel(html, handle):
    """The public preview page → [{id, at, text, photo}], or None when the
    channel has no public preview."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or "", "html.parser")
    wraps = soup.select(".tgme_widget_message")
    if not wraps:
        return None if not soup.select(".tgme_channel_history, .tgme_widget_message_wrap") else []
    out = []
    for w in wraps:
        post = w.get("data-post") or ""
        m = re.match(r"([^/]+)/(\d+)$", post)
        if not m:
            continue
        photo = ""
        for el in w.select(".tgme_widget_message_photo_wrap, .tgme_widget_message_video_thumb, .link_preview_image"):
            mm = _BG.search(el.get("style") or "")
            if mm:
                photo = mm.group(1)
                break
        t = w.select_one(".tgme_widget_message_text")
        text = t.get_text("\n", strip=True) if t else ""
        tm = w.select_one("time[datetime]")
        out.append({"id": int(m.group(2)), "at": tm.get("datetime") if tm else "", "text": text[:2000],
                    "photo": photo})
    return out


def _when(iso):
    """Telegram's ISO time (UTC, with offset) → the site's naive local time."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo:
            from frappe.utils import get_system_timezone
            from zoneinfo import ZoneInfo
            dt = dt.astimezone(ZoneInfo(get_system_timezone())).replace(tzinfo=None)
        return dt
    except Exception:
        return now_datetime()


def dhash(img):
    """64-bit difference hash, as 16 hex characters."""
    from PIL import Image
    g = img.convert("L").resize((9, 8), Image.LANCZOS)
    px = list(g.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (1 if px[row * 9 + col] > px[row * 9 + col + 1] else 0)
    return f"{bits:016x}"


def _dist(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def _recent_hashes():
    """[(pick, hash)] of the picks seen in the matching window."""
    since = add_days(now_datetime(), -MATCH_DAYS)
    return [[r.name, r.dhash] for r in frappe.get_all(
        DT_PICK, filters={"last_seen": [">=", since], "dhash": ["is", "set"]}, fields=["name", "dhash"],
        limit_page_length=0)]


def _nearest(hx, hashes):
    best, bd = None, 65
    for name, other in hashes:
        try:
            d = _dist(hx, other)
        except ValueError:
            continue
        if d < bd:
            best, bd = name, d
    return best if bd <= PICK_DISTANCE else None


def _fetch_image(url):
    import requests
    from PIL import Image
    if not re.match(r"^https://[A-Za-z0-9.-]*(telesco\.pe|telegram\.org|t\.me|cdn-telegram\.org)/", url):
        return None
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20, stream=True)
    if r.status_code != 200:
        return None
    data = r.raw.read(8 * 1024 * 1024 + 1, decode_content=True)
    if len(data) > 8 * 1024 * 1024:
        return None
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


def _thumb_bytes(img):
    from PIL import Image
    im = img.convert("RGB")
    im.thumbnail((THUMB_PX, THUMB_PX), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=78, optimize=True)
    return buf.getvalue()


_PRICE = re.compile(r"(\d{1,6}(?:[.,]\d{1,2})?)\s*(?:dh|dhs|mad|drh|درهم|دراهم|د\.?م)(?![A-Za-z])", re.I)


def _title_of(text):
    for line in str(text or "").splitlines():
        line = re.sub(r"\s+", " ", line).strip(" .-_*•|")
        # A line with at least two letters in any script, and not just a price.
        if len(re.findall(r"[^\W\d_]", _PRICE.sub("", line))) >= 2:
            return line[:120]
    return ""


def price_seen(text):
    """The first price written in a caption ("27dh", "110 درهم"): a hint for
    the decider, not a cost."""
    m = _PRICE.search(str(text or ""))
    if not m:
        return 0
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return 0


def _save_post(src, h, m, hashes):
    if frappe.db.exists(DT_POST, {"channel": h.lower(), "post_id": m["id"]}):
        return False
    img = _fetch_image(m["photo"])
    if img is None:
        return False
    hx = dhash(img)
    thumb = _thumb_bytes(img)
    at = _when(m["at"])
    post = frappe.get_doc({
        "doctype": DT_POST, "source": src.name, "channel": h.lower(), "post_id": m["id"],
        "posted_at": at, "caption": m["text"], "dhash": hx,
    }).insert(ignore_permissions=True)
    f = frappe.get_doc({
        "doctype": "File", "file_name": f"souk-lead-{frappe.generate_hash(length=16)}.jpg",
        "content": thumb, "attached_to_doctype": DT_POST, "attached_to_name": post.name,
        # Public with an unguessable name, like every souk photo (souk._insert_file):
        # the buyer and the decider have no rights on System Manager private files.
        "is_private": 0,
    }).insert(ignore_permissions=True)
    pick = _nearest(hx, hashes)
    if pick:
        post.db_set("pick", pick, update_modified=False)
        _refresh_pick(pick, at)
    else:
        p = frappe.get_doc({
            "doctype": DT_PICK, "title": _title_of(m["text"]) or src.supplier_name or h,
            "photo": f.file_url, "dhash": hx, "caption": m["text"][:1000], "status": "new",
            "first_seen": at, "last_seen": at, "sources_n": 1, "posts_n": 1, "trend_n": 1,
            "source": src.name,
        }).insert(ignore_permissions=True)
        post.db_set("pick", str(p.name), update_modified=False)
        hashes.append([str(p.name), hx])
    post.db_set("thumb", f.file_url, update_modified=False)
    return True


def _refresh_pick(pick, at=None):
    week = add_days(now_datetime(), -TREND_DAYS)
    r = frappe.db.sql(f"""SELECT COUNT(*) posts, COUNT(DISTINCT source) sources,
                                 COUNT(DISTINCT CASE WHEN posted_at >= %s THEN source END) trend,
                                 MIN(posted_at) first, MAX(posted_at) last
                          FROM `tab{DT_POST}` WHERE pick=%s""", (week, pick), as_dict=True)[0]
    upd = {"posts_n": cint(r.posts), "sources_n": cint(r.sources), "trend_n": cint(r.trend)}
    if r.last:
        upd["last_seen"] = r.last
    if r.first:
        upd["first_seen"] = r.first
    p = frappe.db.get_value(DT_PICK, pick, ["title", "caption"], as_dict=True) or {}
    if not p.get("title") or not p.get("caption"):
        c = frappe.db.sql(f"""SELECT caption FROM `tab{DT_POST}` WHERE pick=%s AND IFNULL(caption,'')!=''
                              ORDER BY posted_at LIMIT 1""", (pick,))
        if c:
            if not p.get("caption"):
                upd["caption"] = c[0][0][:1000]
            if not p.get("title"):
                upd["title"] = _title_of(c[0][0])
    frappe.db.set_value(DT_PICK, pick, upd, update_modified=False)


def cleanup():
    """hooks: daily. Posts older than KEEP_DAYS whose pick nobody flagged go,
    with their thumbnails; a pick left with no post goes too."""
    if not _ready():
        return
    cut = add_days(now_datetime(), -KEEP_DAYS)
    rows = frappe.db.sql(
        f"""SELECT po.name, po.pick FROM `tab{DT_POST}` po
            LEFT JOIN `tab{DT_PICK}` pk ON pk.name = po.pick
            WHERE po.posted_at < %s AND IFNULL(pk.status, 'new') = 'new'
              AND (pk.last_seen IS NULL OR pk.last_seen < %s)
            LIMIT 5000""", (cut, cut), as_dict=True)
    picks = set()
    for r in rows:
        for fn in frappe.get_all("File", filters={"attached_to_doctype": DT_POST, "attached_to_name": r.name},
                                 pluck="name"):
            try:
                frappe.delete_doc("File", fn, ignore_permissions=True, force=True)
            except Exception:
                pass
        frappe.db.delete(DT_POST, {"name": r.name})
        if r.pick:
            picks.add(r.pick)
    for p in picks:
        if not frappe.db.exists(DT_POST, {"pick": p}):
            frappe.db.delete(DT_PICK, {"name": p, "status": "new"})
    frappe.db.commit()


# --- the screen ----------------------------------------------------------------

def _loads(v, default=None):
    try:
        return json.loads(v) if v else default
    except ValueError:
        return default


def _signals(r):
    now = now_datetime()
    first = get_datetime(r.first_seen) if r.first_seen else now
    age = (now - first).days
    return {
        "trending": cint(r.trend_n) >= TREND_SOURCES,
        "saturated": age >= SATURATED_DAYS and cint(r.sources_n) >= SATURATED_SOURCES,
        "fresh": age <= 2,
        "age": age,
    }


def _sources_of(picks):
    """{pick: [{name,label,phone,wa,handle,last}]} newest poster first."""
    if not picks:
        return {}
    rows = frappe.db.sql(
        f"""SELECT po.pick, po.source, MAX(po.posted_at) last, s.supplier_name, s.mobile_no, s.website,
                   s.supplier_group
            FROM `tab{DT_POST}` po JOIN `tabSupplier` s ON s.name = po.source
            WHERE po.pick IN %(p)s GROUP BY po.pick, po.source ORDER BY last DESC""",
        {"p": tuple(picks)}, as_dict=True)
    out = {}
    for r in rows:
        out.setdefault(r.pick, []).append({
            "name": r.source, "label": r.supplier_name or r.source, "phone": r.mobile_no or "",
            "wa": _wa(r.mobile_no), "handle": handle_of(r.website), "stall": r.supplier_group == S.SUPPLIER_GROUP,
            "last": str(r.last or "")[:16],
        })
    return out


def _card(r, srcs, me):
    who = _loads(r.interested_json, []) or []
    return {
        "name": str(r.name), "title": r.title or "", "photo": r.photo or "", "caption": (r.caption or "")[:400],
        "priceSeen": price_seen(r.caption), "status": r.status, "firstSeen": str(r.first_seen or "")[:16], "lastSeen": str(r.last_seen or "")[:16],
        "posts": cint(r.posts_n), "sourcesN": cint(r.sources_n), "trendN": cint(r.trend_n),
        **_signals(r),
        "interested": [{"user": u, "name": S._user_name(u)} for u in who], "mine": me in who,
        "decidedBy": S._user_name(r.decided_by) if r.decided_by else "", "decidedAt": str(r.decided_at or "")[:16],
        "reason": r.reason or "", "note": r.note or "", "targetQty": cint(r.target_qty),
        "maxPrice": flt(r.max_price), "source": r.source or "", "category": r.category or "",
        "product": r.product or "", "sources": srcs.get(str(r.name), []),
    }


PICK_FIELDS = ["name", "title", "photo", "caption", "status", "first_seen", "last_seen", "posts_n", "sources_n",
               "trend_n", "interested_json", "decided_by", "decided_at", "reason", "note", "target_qty",
               "max_price", "source", "category", "product", "interested_at"]


@frappe.whitelist()
def picks_boot(tab="feed", q="", start=0, only=""):
    """tab: feed (new, last 14 days) · interest (waiting for the decision) ·
    list (approved: the shopping list) · done (bought / no, last 30 days).
    only: trending | saturated | <source supplier name>."""
    S._gate_view()
    me = frappe.session.user
    base = {"canDecide": _can_decide(), "isManager": S._role() == "manager",
            "canBuy": S._role() in ("manager", "sourcing"), "deciders": _people(_deciders()),
            "reasons": list(REASONS), "ready": bool(_ready()),
            "categories": [{"key": c["key"], "ar": c.get("ar"), "fr": c.get("fr")}
                           for c in S.settings().get("categories") or []]}
    if not _ready():
        return dict(base, tab=tab, picks=[], counts={}, sources=[], more=False)
    counts = {r.status: cint(r.n) for r in frappe.db.sql(
        f"""SELECT status, COUNT(*) n FROM `tab{DT_PICK}`
            WHERE status != 'new' OR last_seen >= %s GROUP BY status""",
        (add_days(now_datetime(), -14),), as_dict=True)}
    if tab == "sources":
        return dict(base, tab=tab, picks=[], counts=counts, sources=_sources_out(), more=False)
    start = max(0, cint(start))
    page = 40
    cond, args = [], {}
    if tab == "interest":
        cond.append("status = 'interested'")
        order = "interested_at ASC"
    elif tab == "list":
        cond.append("status = 'approved'")
        order = "source, decided_at ASC"
        page = 300
    elif tab == "done":
        cond.append("status IN ('bought', 'rejected') AND decided_at >= %(d30)s")
        args["d30"] = add_days(now_datetime(), -30)
        order = "decided_at DESC"
    else:
        tab = "feed"
        cond.append("status = 'new' AND last_seen >= %(d14)s")
        args["d14"] = add_days(now_datetime(), -14)
        order = "(trend_n >= %(tr)s) DESC, last_seen DESC" % {"tr": TREND_SOURCES}
    if only == "trending":
        cond.append(f"trend_n >= {TREND_SOURCES}")
    elif only == "saturated":
        cond.append(f"sources_n >= {SATURATED_SOURCES} AND first_seen <= %(sat)s")
        args["sat"] = add_days(now_datetime(), -SATURATED_DAYS)
    elif only:
        cond.append(f"name IN (SELECT pick FROM `tab{DT_POST}` WHERE source = %(src)s)")
        args["src"] = only
    if q:
        cond.append("(title LIKE %(q)s OR caption LIKE %(q)s)")
        args["q"] = f"%{str(q).strip()[:60]}%"
    rows = frappe.db.sql(
        f"""SELECT {", ".join(PICK_FIELDS)} FROM `tab{DT_PICK}` WHERE {" AND ".join(cond)}
            ORDER BY {order} LIMIT {page + 1} OFFSET {start}""", args, as_dict=True)
    more = len(rows) > page
    rows = rows[:page]
    srcs = _sources_of([str(r.name) for r in rows])
    out = dict(base, tab=tab, counts=counts, more=more, picks=[_card(r, srcs, me) for r in rows])
    if tab == "list":
        # Grouped by the stall to buy from: one visit, one call.
        groups = {}
        for c in out["picks"]:
            groups.setdefault(c["source"] or "", []).append(c)
        names = [g for g in groups if g]
        info = {r.name: r for r in frappe.get_all(
            "Supplier", filters={"name": ["in", names or ["-"]]},
            fields=["name", "supplier_name", "mobile_no", "website", "supplier_group"])}
        out["groups"] = [{
            "source": g, "label": (info[g].supplier_name if g in info else "") or g,
            "phone": info[g].mobile_no if g in info else "", "wa": _wa(info[g].mobile_no) if g in info else "",
            "handle": handle_of(info[g].website) if g in info else "",
            "stall": bool(g in info and info[g].supplier_group == S.SUPPLIER_GROUP),
            "picks": [c["name"] for c in lst],
            "pieces": sum(c["targetQty"] for c in lst),
            "budget": round(sum(c["targetQty"] * c["maxPrice"] for c in lst), 2),
        } for g, lst in groups.items()]
    return out


@frappe.whitelist()
def pick(name):
    """One pick and every post of it (who posted it, when, with what caption)."""
    S._gate_view()
    _need_ready()
    r = frappe.db.get_value(DT_PICK, name, PICK_FIELDS, as_dict=True)
    if not r:
        frappe.throw("Unknown pick.")
    srcs = _sources_of([str(r.name)])
    posts = frappe.db.sql(
        f"""SELECT po.name, po.source, po.channel, po.post_id, po.posted_at, po.caption, po.thumb,
                   s.supplier_name FROM `tab{DT_POST}` po LEFT JOIN `tabSupplier` s ON s.name = po.source
            WHERE po.pick = %s ORDER BY po.posted_at DESC LIMIT 60""", (name,), as_dict=True)
    out = _card(r, srcs, frappe.session.user)
    out["posts"] = [{
        "name": p.name, "source": p.source, "label": p.supplier_name or p.source, "at": str(p.posted_at or "")[:16],
        "caption": p.caption or "", "thumb": p.thumb or "", "url": f"https://t.me/{p.channel}/{p.post_id}",
    } for p in posts]
    out["postsN"] = cint(r.posts_n)
    if r.product and frappe.db.exists(S.DT_PRODUCT, r.product):
        out["card"] = frappe.db.get_value(S.DT_PRODUCT, r.product, ["name", "title", "stage", "sku_base"], as_dict=True)
    return out


@contextmanager
def _locked(name):
    frappe.db.sql(f"SELECT name FROM `tab{DT_PICK}` WHERE name=%s FOR UPDATE", (name,))
    yield


@frappe.whitelist(methods=["POST"])
def pick_interest(name, on=1, note=""):
    """Anyone in the souk: "I'd sell this" (or take it back)."""
    S._gate_view()
    _need_ready()
    me = frappe.session.user
    with _locked(name):
        d = frappe.get_doc(DT_PICK, name)
        if d.status not in ("new", "interested"):
            frappe.throw("This one is already decided.")
        who = _loads(d.interested_json, []) or []
        if cint(on) and me not in who:
            who.append(me)
        elif not cint(on) and me in who:
            who.remove(me)
        d.interested_json = json.dumps(who)
        if who and d.status == "new":
            d.status = "interested"
            d.interested_at = now_datetime()
        elif not who and d.status == "interested":
            d.status = "new"
            d.interested_at = None
        if note and cint(on):
            d.note = (f"{S._user_name(me)}: {str(note).strip()[:300]}\n" + (d.note or ""))[:2000]
        d.save(ignore_permissions=True)
    frappe.db.commit()
    return _one(name)


@frappe.whitelist(methods=["POST"])
def pick_decide(name, verdict, reason="", note="", target_qty=0, max_price=0, source="", category=""):
    """The decider: verdict buy | no | undo. Buy needs a quantity, a max cost
    per piece and the source to buy from; no needs a reason."""
    _gate_decide()
    _need_ready()
    with _locked(name):
        d = frappe.get_doc(DT_PICK, name)
        if d.status == "bought":
            frappe.throw("Already bought: the card is on the board.")
        if verdict == "undo":
            d.status = "interested" if _loads(d.interested_json, []) else "new"
            d.decided_by = d.decided_at = None
            d.reason = ""
        elif verdict == "buy":
            qty = cint(target_qty)
            price = flt(max_price)
            if qty < 1 or qty > 100000:
                frappe.throw("How many pieces?")
            if price <= 0 or price > 1000000:
                frappe.throw("The highest cost per piece we accept.")
            if not source or not frappe.db.exists("Supplier", source):
                frappe.throw("Buy from which source?")
            if frappe.db.get_value("Supplier", source, "supplier_group") not in (LEAD_GROUP, S.SUPPLIER_GROUP):
                frappe.throw("Choose a souk source.")
            cats = {c["key"] for c in S.settings().get("categories") or []}
            d.update({"status": "approved", "target_qty": qty, "max_price": price, "source": source,
                      "category": category if category in cats else "", "reason": ""})
            d.decided_by, d.decided_at = frappe.session.user, now_datetime()
        elif verdict == "no":
            if reason not in REASONS:
                frappe.throw("Why not?")
            d.update({"status": "rejected", "reason": reason})
            d.decided_by, d.decided_at = frappe.session.user, now_datetime()
        else:
            frappe.throw("Bad verdict.")
        if note:
            d.note = (f"{S._user_name(frappe.session.user)}: {str(note).strip()[:300]}\n" + (d.note or ""))[:2000]
        d.save(ignore_permissions=True)
    frappe.db.commit()
    return _one(name)


def _one(name):
    r = frappe.db.get_value(DT_PICK, name, PICK_FIELDS, as_dict=True)
    return _card(r, _sources_of([str(name)]), frappe.session.user)


# --- the buy ---------------------------------------------------------------------

@frappe.whitelist()
def pick_for_buy(name):
    """SoukBuy opened from the shopping list: what to prefill."""
    S._gate_buy()
    _need_ready()
    r = frappe.db.get_value(DT_PICK, name, PICK_FIELDS, as_dict=True)
    if not r or r.status != "approved":
        frappe.throw("This pick is not on the shopping list.")
    src = frappe.db.get_value("Supplier", r.source, ["name", "supplier_name", "mobile_no", "supplier_group"],
                              as_dict=True) if r.source else None
    # The buyer names the product: a source's name or a caption is no title.
    title = r.title or ""
    if title.upper() == ((src.supplier_name if src else "") or "").upper() or not _title_of(title):
        title = ""
    return {
        "name": str(r.name), "title": title, "photo": r.photo or "", "targetQty": cint(r.target_qty),
        "maxPrice": flt(r.max_price), "category": r.category or "", "note": r.note or "",
        "decidedBy": S._user_name(r.decided_by) if r.decided_by else "",
        "stall": ({"name": src.name, "label": src.supplier_name or src.name, "phone": src.mobile_no or "",
                   "lead": src.supplier_group == LEAD_GROUP} if src else None),
    }


def promote_lead(supplier):
    """Buying from a lead makes it a stall (create_basket calls this)."""
    if supplier and frappe.db.get_value("Supplier", supplier, "supplier_group") == LEAD_GROUP:
        frappe.db.set_value("Supplier", supplier, {"supplier_group": S.SUPPLIER_GROUP, "disabled": 0})
        det = frappe.db.get_value("Supplier", supplier, "supplier_details") or ""
        if not det.startswith("Souk stall · "):
            frappe.db.set_value("Supplier", supplier, "supplier_details", "Souk stall · Derb Omar",
                                update_modified=False)


def pick_photo(name):
    """The pick's photo URL when it is still on the shopping list."""
    if not name or not _ready():
        return ""
    r = frappe.db.get_value(DT_PICK, name, ["status", "photo"], as_dict=True)
    return (r.photo or "") if r and r.status == "approved" else ""


def link_card(name, card):
    """The new card bought from this pick: the pick is done."""
    if not name or not _ready() or not frappe.db.exists(DT_PICK, name):
        return
    frappe.db.set_value(DT_PICK, name, {"status": "bought", "product": card})
