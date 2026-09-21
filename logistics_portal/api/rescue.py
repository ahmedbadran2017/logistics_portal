"""Contact Center — Lane 2: post-ship rescue.

The parcel left the building and the delivery is failing (carrier exception,
failed attempt, customer unreachable, or silently stuck in transit). The same
contact-center agents call the CUSTOMER and decide: redeliver, reship, request
the return, or cancel — every decision recorded on both the parcel (Delivery
Note exception trail) and the order. Shares the confirmation lane's contact
fields (attempt counter, next-call time) — one engine, two lanes.

Production workload at build time: 3,678 untriaged Delivery Exceptions +
1,166 Failed Attempts + 658 parcels silently stuck in transit >7 days.
"""

import re

import frappe


def _site_now():
    """The SITE clock as a bound param. The DB server runs on its own
    time zone, so NOW() made fresh rows read negative ages."""
    from frappe.utils import now_datetime
    return str(now_datetime())[:19]
from frappe.utils import add_to_date, now_datetime

# ── what an agent can decide, and what it means on the parcel ────────────
#
# `reship` used to stamp "Redeliver" here, which made the two the same word
# on the Delivery Note. They are not the same thing: a redeliver asks the
# CARRIER to try the same parcel again, a reship sends a NEW parcel and
# lets the old one come home. Different money, different watch, and the
# board could not tell them apart — which is why they could not have
# separate queues.
#
# `followup` is new: the parcel is stuck at the carrier and the job is to
# chase them. That is not a promise to the customer, so it does not belong
# with redeliver, and it is not a closure, so it does not belong with
# resolve. It had nowhere to live, so it was never recorded at all.
ACTIONS = ("redeliver", "reship", "followup", "returnreq", "dna",
           "cancel", "resolve")

_DN_ACTION = {
    "redeliver": "Redeliver",
    "reship": "Reship",
    "followup": "Follow Up",
    "returnreq": "Return Requested",
    "cancel": "Return Requested",
    "resolve": "Resolved",
}

# A decision that PROMISES the customer the parcel is still coming. These
# are the ones worth watching afterwards — the promise is only worth what
# happens next.
_PROMISE = ("Redeliver", "Reship")

# ── the board, in three questions instead of six piles ───────────────────
#
# Audited 2026-09-21: six tabs stood over 128 live parcels (89 exceptions +
# 39 failed). Everything else was either a filter of those (mine, 18), a
# different team's work (notdelivered, 17), history (backlog, 5,137) or
# empty (stale, 0). Adding a tab per new action would have made nine.
#
# So the tabs answer QUESTIONS and the piles became chips inside them:
#
#   todo     who is waiting on me right now
#   watch    I decided something — did it move?
#   history  what already ended
#
# The internal queue names below are unchanged, so every existing query,
# count and cache keeps working; this is a routing layer, not a rewrite.
TABS = ("todo", "watch", "history")

CHIPS = {
    # "mine" is not a pile, it is a filter — but it is the one an agent
    # reaches for most, so it keeps a chip rather than becoming a switch
    # nobody finds.
    "todo": ("exceptions", "failed", "callback", "stale", "notdelivered", "mine"),
    "watch": ("promised", "followup"),
    "history": ("done", "backlog"),
}

# What each tab opens on when no chip is chosen.
_TAB_DEFAULT = {"todo": "exceptions", "watch": "promised", "history": "done"}

# Old links, old bookmarks and the pulse poller all still say "exceptions".
_LEGACY_TAB = {
    "exceptions": ("todo", "exceptions"), "failed": ("todo", "failed"),
    "stale": ("todo", "stale"), "notdelivered": ("todo", "notdelivered"),
    "backlog": ("history", "backlog"), "mine": ("todo", "mine"),
}


def resolve_tab(tab, chip=""):
    """(tab, chip) from whatever the caller said — new names, old names or
    nothing. Returns a chip only when it is valid for that tab."""
    tab = (tab or "").strip().lower()
    chip = (chip or "").strip().lower()
    if tab in _LEGACY_TAB:
        ltab, lchip = _LEGACY_TAB[tab]
        return ltab, (chip if chip in CHIPS[ltab] else lchip)
    if tab not in TABS:
        tab = "todo"
    return tab, (chip if chip in CHIPS[tab] else "")


_ALL_QUEUES = ("mine", "exceptions", "failed", "notdelivered", "stale",
               "backlog", "promised", "followup", "callback", "done")
# Morocco only. The instance also carries China / Maslak / Holding, whose
# orders share this database. Carrier exceptions happen to be Morocco-only in
# practice (Cathedis is the Moroccan carrier), but the SO-backed "Not
# Delivered" tab is not, so every query here is company-scoped for safety.
_CO = "Justyol Morocco"

# The carrier's two words for a parcel that did not arrive, and what each
# actually turns out to mean. Measured 2026-09-21 on the LAST carrier event
# per parcel (not every comment it ever collected, which is history):
#
#   Failed Attempt      534 parcels. 64% say literally "customer
#                       unreachable", 35% carry no carrier word at all, and
#                       nothing else reaches 3%. One meaning, no mixture:
#                       the driver could not get hold of them, so a call is
#                       the whole job. The screen calls it "Unreachable".
#
#   Delivery Exception  1,796 parcels, and a mixture: 38% are a refusal or
#                       cancellation (437 cancelled by phone, 252 cancelled
#                       at the door, plus refused-ID and non-compliant),
#                       36% carry no word, 9% unreachable, 4% a return we
#                       asked for ourselves, then wrong destination, damaged,
#                       "already received it". The screen calls it "Refused
#                       or stuck", and the row shows the carrier's own
#                       sentence, because here you must read before you call.
#
# The keys stay the carrier's words: they are what the tracking column
# holds, and renaming a database value to suit a label is how the two drift.
_DN_TRACK = {"exceptions": "Delivery Exception", "failed": "Failed Attempt"}
_STALE_TRACKS = ("Out For Delivery", "In Transit", "Pending")
_STALE_DAYS = 7
# Everything the working queues track, for the older-than-window backlog.
_BACKLOG_TRACKS = ("Delivery Exception", "Failed Attempt") + _STALE_TRACKS

# The carrier's last word on the parcel, written by its webhook as a comment
# on the order. Measured 2026-09-13 on the 30-day exceptions queue: of ~1,000
# untriaged parcels, 570 said "customer cancelled", 91 "return requested",
# 171 "customer unreachable", 129 "out for delivery" — a rescue call can
# only save the last two kinds, and the queue showed none of this.
_CARRIER_LIKE = ("Newly created%", "Shipped to%", "The parcel%", "Out for%", "Package%",
                 "The driver%", "Customer unreachable%", "Customer cancelled%",
                 "The customer has cancelled%", "Cancelled on site%", "Cancellation Reason%",
                 "Justyol has requested%", "%eturned%")
_CANCELLED_LIKE = ("Customer cancelled%", "The customer has cancelled%", "Cancelled on site%",
                   "Cancellation Reason%", "Justyol has requested%")


def _sql_like(p):
    """Every query these land in is parameterised, so a literal % in a LIKE
    pattern must be doubled or the driver reads it as a placeholder."""
    return p.replace("%", "%%")


def _last_event_sql(col="content"):
    ors = " OR ".join(f"c.content LIKE '{_sql_like(p)}'" for p in _CARRIER_LIKE)
    return (f"(SELECT c.{col} FROM `tabComment` c WHERE c.reference_doctype = 'Sales Order' "
            f"AND c.reference_name = so.name AND c.comment_type = 'Comment' AND ({ors}) "
            f"ORDER BY c.creation DESC LIMIT 1)")


_ALERT_WINDOW_MIN = 30


def run_alerts():
    """Scheduled every 15 min: page the lane the moment the carrier hits a
    wall with a customer.

    The carrier's own record reaches us within minutes — measured 2026-09-17
    across six live parcels, between two and ten minutes behind Cathedis'
    own timestamp — so a failed delivery is actionable while the driver is
    still in the neighbourhood. Nobody was being told. This counts the
    problems that landed in the last half hour and that no one has answered
    yet, and names the freshest one so the first call is obvious.
    """
    try:
        from logistics_portal.api.shipments import _emit
        from logistics_portal.api import clock as _clk
        now = _clk.floor_now()
        # Nobody answers a phone at 3am; the carrier's own retry window is
        # the working day anyway.
        if not (8 <= now.hour < 21):
            return
        ev = _last_event_sql("creation")
        rows = frappe.db.sql(
            f"""SELECT dn.name, dn.customer_name AS customer, so.name AS so,
                       {_last_event_sql("content")} AS ev
                FROM `tabDelivery Note` dn {_SO_JOIN}
                WHERE dn.docstatus = 1 AND dn.company = %(co)s
                  AND dn.custom_track_shipment_status IN %(tracks)s
                  AND dn.posting_date >= %(line)s
                  AND {_RETURNED}
                  AND {_untriaged_cond()}
                  AND {ev} >= DATE_SUB(%(snow)s, INTERVAL %(m)s MINUTE)
                ORDER BY {ev} DESC LIMIT 60""",
            {"co": _CO, "m": _ALERT_WINDOW_MIN, "snow": _site_now(),
             # Page only about parcels the team can actually open. Without
             # this the alert would name a parcel that lives in the backlog
             # and the agent would click through to nothing.
             "line": _start_line() or str(add_to_date(now_datetime(), days=-30))[:10],
             "tracks": tuple(_DN_TRACK.values())}, as_dict=True)
        if not rows:
            return
        first = rows[0]
        _emit("rescue_fresh",
              {"n": len(rows), "m": _ALERT_WINDOW_MIN,
               "customer": first.customer or "",
               "order": first.so or first.name,
               "what": _clean(first.ev or "")[:60]},
              # The floor runs about four of these an hour; a dozen inside
              # half an hour is a driver, a district or the carrier itself.
              severity="critical" if len(rows) >= 12 else "warning",
              cooldown_h=1, order=first.so, audience=("tracking", "manager"))
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "rescue.run_alerts")


def _cancelled_cond():
    ev = _last_event_sql()
    return "(" + " OR ".join(f"{ev} LIKE '{_sql_like(p)}'" for p in _CANCELLED_LIKE) + ")"


_FRESH_MIN = 90


def _fresh_ev(at):
    """Did the carrier say this within the last hour and a half? Both sides
    are on the site clock — never compare one of these to SQL NOW()."""
    if not at:
        return False
    try:
        return str(at)[:19] >= str(add_to_date(now_datetime(), minutes=-_FRESH_MIN))[:19]
    except Exception:
        return False


def _clean(text):
    """The carrier writes HTML entities into its comments ('Call &amp; SMS')."""
    import html as _html
    return _html.unescape(frappe.utils.strip_html(text or "")).strip()


def _verdict(text):
    t = (text or "")
    if any(t.startswith(p.rstrip("%")) for p in _CANCELLED_LIKE):
        return "cancelled"
    if t.startswith("Customer unreachable"):
        return "unreachable"
    if t.startswith("The driver"):
        return "appointment"
    if t.startswith(("Out for", "The parcel", "Shipped to")):
        return "moving"
    if "eturned" in t:
        return "returned"
    return "other" if t else ""


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("confirmation", "tracking", "manager"):
        frappe.throw("Not authorized for the rescue workspace.", frappe.PermissionError)
    return role


def _allowed_tabs(role, surface=""):
    """"Not Delivered" is a CONFIRMATION queue, not a carrier one: it is an
    order the shop never got out the door, worked by the people who own the
    customer conversation. It sat in this screen because both lanes read the
    same rescue endpoint — 154 of the 247 decisions logged in the last two
    weeks landed there, which is confirmation's work recorded under tracking.

    Gated by the SURFACE first, not only the role. The screen is reachable
    from three navs: the tracking role's, the tracking manager's, and the
    confirmation manager's. A role test alone left the queue standing for
    anyone with "manager" — which is how it was still on the tracking
    portal after the split. The rule the building actually follows is the
    door you came in: on /tracking there is no Not-Delivered, whoever you
    are; on /confirmation there is."""
    if (surface or "").strip().lower() == "ship" or role == "tracking":
        return [t for t in _ALL_QUEUES if t != "notdelivered"]
    return list(_ALL_QUEUES)


# ── section settings + admins (same pattern as the confirmation section) ──
_RS_KEY = "lp_rescue_settings"
# The day this lane started working inside the portal. Everything the
# carrier was already holding before it was settled with Cathedis directly,
# over months of daily calls that left no record here — so the queues were
# opening on a pile of work that was finished, and the team learned to
# scroll past it. Before the line is history (the Backlog tab, still worked
# in bulk); after it is the live desk. Blank turns the line off.
_START_LINE = "2026-09-15"

_RS_DEFAULTS = {
    "startLine": _START_LINE,
    "claimHours": 4,
    "retryDna": 6,
    "slaTriageH": 24,   # a failing parcel untouched longer than this is late
    # A promise is not late the day it is made. The clock that matters is
    # the CARRIER's: how long since anything happened to the parcel after
    # we told the customer it was coming.
    "promiseSlaH": 48,
    # Kept: the vocabulary for ENDING a parcel (return / cancel).
    "reasons": ["Client injoignable", "Refuse le colis", "Adresse introuvable",
                "Reporté par le client", "Annulé par le client"],
    # A reason list PER ACTION. One shared list meant the board asked "why?"
    # on 2 of its 5 actions and threw the answer away on the other 3 — and
    # the one list it had spoke only the language of cancelling, which is
    # the wrong vocabulary for a customer who still wants their parcel.
    "reasonsBy": {
        "redeliver": ["Le client veut toujours le colis",
                      "Nouvelle date convenue avec le client",
                      "Adresse corrigée",
                      "Transporteur informé",
                      "Le client passera à l'agence"],
        "reship": ["Colis perdu par le transporteur",
                   "Colis endommagé",
                   "Mauvais article envoyé",
                   "Retourné — le client le veut encore"],
        "followup": ["Aucun mouvement chez le transporteur",
                     "Colis bloqué à l'agence",
                     "Statut incohérent",
                     "En attente de réponse du transporteur"],
        "dna": ["Téléphone éteint", "Ne répond pas", "Faux numéro",
                "Rappeler plus tard"],
    },
    "admins": [],
}


def _rs_settings():
    import json as _json
    raw = frappe.db.get_default(_RS_KEY)
    out = dict(_RS_DEFAULTS)
    if raw:
        try:
            saved = _json.loads(raw)
            if isinstance(saved, dict):
                out.update({k: saved[k] for k in _RS_DEFAULTS if k in saved})
        except Exception:
            pass
    return out


def _start_line():
    """The date the live queues begin. Empty = no line."""
    v = str(_rs_settings().get("startLine") or "").strip()[:10]
    return v if re.match(r"^\d{4}-\d{2}-\d{2}$", v or "") else ""


def _is_rs_admin():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role == "manager":
        return True
    # Capability requires a live portal role — leaving the team must revoke
    # it even if the admins list is stale.
    if role not in ("confirmation", "cs", "tracking"):
        return False
    return frappe.session.user in _rs_settings().get("admins", [])


@frappe.whitelist()
def rs_settings():
    _gate()
    return {**_rs_settings(), "canEdit": _is_rs_admin()}


@frappe.whitelist(methods=["POST"])
def save_rs_settings(settings=None):
    import json as _json
    _gate()
    if not _is_rs_admin():
        frappe.throw("Only the portal manager or a rescue section admin can "
                     "change these settings.", frappe.PermissionError)
    if isinstance(settings, str):
        settings = _json.loads(settings)
    settings = settings or {}
    out = dict(_rs_settings())
    if "reasonsBy" in settings and isinstance(settings["reasonsBy"], dict):
        clean = {}
        for act_name, lst in settings["reasonsBy"].items():
            if act_name not in ACTIONS:
                continue
            vals = [str(r).strip()[:60] for r in (lst or []) if str(r).strip()]
            if vals:
                clean[act_name] = vals[:12]
        out["reasonsBy"] = clean
    for k in ("retryDna", "slaTriageH", "claimHours", "promiseSlaH"):
        if k in settings:
            v = int(settings[k])
            if not (1 <= v <= 168):
                frappe.throw(f"{k} must be between 1 and 168 hours.")
            out[k] = v
    if "startLine" in settings:
        line = str(settings["startLine"] or "").strip()[:10]
        if line and not re.match(r"^\d{4}-\d{2}-\d{2}$", line):
            frappe.throw("The start line must be a date (YYYY-MM-DD) or empty.")
        out["startLine"] = line
    if "reasons" in settings:
        reasons = [str(r).strip()[:60] for r in (settings["reasons"] or []) if str(r).strip()]
        if not reasons:
            frappe.throw("Keep at least one reason.")
        out["reasons"] = reasons[:20]
    if "admins" in settings:
        from logistics_portal.api.auth import resolve_role
        if resolve_role(frappe.session.user) != "manager":
            frappe.throw("Only the portal manager can change section admins.",
                         frappe.PermissionError)
        admins = [str(a).strip().lower() for a in (settings["admins"] or []) if str(a).strip()]
        for a in admins:
            if not frappe.db.exists("User", a):
                frappe.throw(f"Unknown user: {a}")
            # The _is_*_admin checks ignore users without a live CC role —
            # accepting one here would be a silent no-op.
            if resolve_role(a) not in ("confirmation", "cs", "tracking",
                                       "manager"):
                frappe.throw(f"{a} has no contact-center role — assign one "
                             "in Team first.")
        out["admins"] = admins[:10]
    frappe.db.set_default(_RS_KEY, _json.dumps(out))
    frappe.db.commit()
    return {"ok": True, **out}


# ── the board ───────────────────────────────────────────────────────────────
_DN_SELECT = """
    SELECT dn.name AS dn, dn.customer_name AS customer, dn.grand_total AS total,
           dn.custom_awb AS awb, dn.custom_track_shipment_status AS track,
           so.name AS so_name,
           COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
           so.custom_shipping_city AS city,
           COALESCE(so.custom_call_attempts, 0) AS attempts,
           so.custom_next_call_at AS next_call,
           dn.custom_exception_action AS prior_action, dn.custom_exception_actioned_at AS prior_at,
           {claim_cols}
           """ + _last_event_sql("content") + """ AS last_event,
           """ + _last_event_sql("creation") + """ AS last_event_at,
           DATEDIFF(CURDATE(), dn.posting_date) AS age_d,
           TIMESTAMPDIFF(HOUR, dn.creation, %(snow)s) AS age_h
    FROM `tabDelivery Note` dn
    LEFT JOIN `tabSales Order` so
      ON so.name = (SELECT MIN(dni.against_sales_order)
                    FROM `tabDelivery Note Item` dni WHERE dni.parent = dn.name)
"""
# NB the SO link is a correlated MIN, not a whole-table GROUP BY: the old
# derived table materialised every DN line on the site per board load (the
# slowest query in the section), and MAX here vs an arbitrary row in act()
# could show one order and act on another. MIN everywhere, evaluated only for
# the filtered page.


_RETURNED = ("NOT EXISTS (SELECT 1 FROM `tabDelivery Note` r WHERE r.is_return = 1 "
             "AND r.return_against = dn.name AND r.docstatus = 1)")
_SO_JOIN = ("LEFT JOIN `tabSales Order` so ON so.name = (SELECT MIN(dni.against_sales_order) "
            "FROM `tabDelivery Note Item` dni WHERE dni.parent = dn.name)")


def _untriaged_cond():
    """No decision yet — OR a Redeliver whose parcel the carrier failed AGAIN
    afterwards. A decision must not hide a parcel forever: #258701 got
    Redeliver on 09-10, the carrier tried on 09-12, found nobody, and the
    parcel would have stayed 'handled' for good."""
    ev_at = _last_event_sql("creation")
    # Reship joins Redeliver here now that it is a word of its own — before
    # this it WAS "Redeliver" on the parcel and inherited the rule by
    # accident. Naming it properly would have quietly dropped it out.
    return ("(COALESCE(dn.custom_exception_action,'') = '' OR "
            "(dn.custom_exception_action IN ('Redeliver', 'Reship') "
            "AND dn.custom_exception_actioned_at IS NOT NULL "
            f"AND {ev_at} > dn.custom_exception_actioned_at))")


def _dn_where(tab, vals, reason=""):
    vals["co"] = _CO
    vals["snow"] = _site_now()
    extra = []
    # A parcel that is already back in the building needs no rescue call;
    # 679 of the 30-day exceptions had a submitted return note behind them.
    extra.append(_RETURNED)
    if reason == "cancelled":
        extra.append(_cancelled_cond())
    elif reason == "rescuable":
        # A parcel the carrier never commented on is NOT cancelled — but
        # NOT (NULL LIKE ...) is NULL, which a WHERE reads as false and
        # silently dropped 686 such parcels from the rescuable list.
        extra.append("(" + _last_event_sql() + " IS NULL OR NOT " + _cancelled_cond() + ")")
    if tab == "mine":
        if not _has_claim_fields():
            return "1 = 0"
        vals["me"] = frappe.session.user
        vals["claimcut"] = _claim_cutoff()
        return " AND ".join([
            "dn.docstatus = 1", "dn.company = %(co)s",
            "dn.custom_rescue_by = %(me)s",
            "COALESCE(dn.custom_rescue_at,'1900-01-01') >= %(claimcut)s"] + extra)
    if tab == "backlog":
        # What is actually UNACCOUNTED FOR before the start line.
        #
        # This tab used to hold everything on the other side of the line —
        # 31,768 parcels, which nobody opened once, and they were right not
        # to. Audited 2026-09-18: 16,953 of them already have a submitted
        # return note. They came back months ago; only the tracking status
        # never caught up. That is a data problem wearing a queue's clothes,
        # and a queue of 31,768 items teaches people to ignore the tab.
        #
        # (The headline number was wrong too, and worse than wrong: summing
        # grand_total over the pile counted the return notes themselves, one
        # bucket totalling MINUS 199,215 MAD. Excluding returns and the
        # already-returned leaves 1,583 parcels and about 294,000 MAD, which
        # is a real and finite thing somebody can reconcile with Cathedis.)
        vals["backtracks"] = _BACKLOG_TRACKS
        _claim_vals(vals)
        line = _start_line()
        if line:
            vals["line"] = line
            before = "dn.posting_date < %(line)s"
        else:
            before = "dn.posting_date < DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)"
        return " AND ".join([
            "dn.docstatus = 1", "dn.company = %(co)s", "dn.is_return = 0",
            "COALESCE(dn.custom_exception_action,'') = ''",
            _claim_cond(),
            "dn.custom_track_shipment_status IN %(backtracks)s",
            before] + extra)
    conds = ["dn.docstatus = 1", "dn.company = %(co)s",
             _untriaged_cond(),
             _claim_cond(),
             "dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)"]
    _claim_vals(vals)
    # The line wins over the day window whenever it is the later of the two,
    # which is the whole point of drawing it.
    line = _start_line()
    if line:
        vals["line"] = line
        conds.append("dn.posting_date >= %(line)s")
    if tab in ("promised", "followup", "done"):
        # These are the DECIDED parcels — the exact opposite of the working
        # queues above, which show only what nobody has touched. `conds`
        # carries _untriaged_cond, so it is rebuilt rather than extended.
        base = ["dn.docstatus = 1", "dn.company = %(co)s", _RETURNED]
        line = _start_line()
        if line:
            vals["line"] = line
            base.append("dn.posting_date >= %(line)s")
        base.append("dn.custom_exception_actioned_at IS NOT NULL")
        if tab == "promised":
            # Still watching: a promise with no verdict yet.
            base.append("dn.custom_exception_action IN ('Redeliver', 'Reship')")
            base.append("COALESCE(dn.custom_rescue_outcome,'') = ''")
        elif tab == "followup":
            base.append("dn.custom_exception_action = 'Follow Up'")
            base.append("COALESCE(dn.custom_rescue_outcome,'') = ''")
        else:
            # Ended — either the watch settled, or the decision was itself
            # an ending (returned / resolved).
            base.append("(COALESCE(dn.custom_rescue_outcome,'') <> '' OR "
                        "dn.custom_exception_action IN "
                        "('Return Requested', 'Resolved', 'Returned (reconciled)'))")
        return " AND ".join(base + extra)
    if tab in _DN_TRACK:
        conds.append("dn.custom_track_shipment_status = %(track)s")
        vals["track"] = _DN_TRACK[tab]
    else:  # stale
        conds.append("dn.custom_track_shipment_status IN %(tracks)s")
        conds.append("dn.posting_date <= DATE_SUB(CURDATE(), INTERVAL %(staledays)s DAY)")
        vals["tracks"] = _STALE_TRACKS
        vals["staledays"] = _STALE_DAYS
    return " AND ".join(conds + extra)


_CLAIM_COLS = ("dn.custom_rescue_by AS held_by, dn.custom_rescue_at AS held_at, "
               "dn.custom_rescue_wait_until AS wait_until,")
_NO_CLAIM_COLS = ("NULL AS held_by, NULL AS held_at, NULL AS wait_until,")


def _dn_select():
    return _DN_SELECT.replace(
        "{claim_cols}", _CLAIM_COLS if _has_claim_fields() else _NO_CLAIM_COLS)


def _cached_counts(days):
    ck = f"lp_rescue_counts:{days}"
    try:
        hit = frappe.cache().get_value(ck, expires=True)
        if isinstance(hit, dict):
            return dict(hit)
    except Exception:
        pass
    counts = {}
    for t in ("exceptions", "failed", "stale", "backlog",
              "promised", "followup", "done"):
        v = {"days": days}
        counts[t] = int(frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabDelivery Note` dn {_SO_JOIN} WHERE {_dn_where(t, v)}",
            v)[0][0])
    counts["notdelivered"] = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabSales Order`
           WHERE docstatus = 1 AND company = %(co)s
             AND custom_sales_status = 'Not Delivered'
             AND creation >= DATE_SUB(NOW(), INTERVAL %(days)s DAY)""",
        {"days": max(days, 60), "co": _CO})[0][0])
    # The callback chip counts what is DUE, not what exists: a queue badge
    # showing 308 when 176 need calling today is a number nobody can act on.
    counts["callback"] = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabSales Order`
           WHERE docstatus = 1 AND company = %(co)s
             AND custom_next_call_at IS NOT NULL
             AND custom_next_call_at <= %(snow)s
             AND custom_sales_status <> 'Cancelled'
             AND COALESCE(custom_logistics_status,'') NOT IN ('Delivered', 'Returned')
             AND COALESCE(custom_track_shipment_status,'')
                 NOT IN ('Delivered', 'Return', 'Returned')""",
        {"co": _CO, "snow": _site_now()})[0][0])
    try:
        frappe.cache().set_value(ck, counts, expires_in_sec=60)
    except Exception:
        pass
    return counts


def _q_phone(q, vals, col):
    """The phone half of a search box, or "" when what was typed is not a
    number. Moroccan numbers are stored in every shape a person types —
    55% of them carry spaces INSIDE the digits — so a plain LIKE on the
    column finds almost nothing; see api/utils.phone_tail_sql."""
    from logistics_portal.api.utils import phone_digits, phone_tail_sql
    ph = phone_digits(q)
    if not ph:
        return ""
    vals["ph"] = f"%{ph}"
    return " OR " + phone_tail_sql(col)


def _mine_count(days):
    """Outside the shared cache on purpose: this depth belongs to one person,
    and a cached one would show an agent somebody else's pile."""
    if not _has_claim_fields():
        return 0
    v = {"days": days}
    where = _dn_where("mine", v)
    return int(frappe.db.sql(
        f"SELECT COUNT(*) FROM `tabDelivery Note` dn {_SO_JOIN} WHERE {where}", v)[0][0])


def _bust():
    """A decision changes every depth on the page: forget the shared counts
    so the reload right after it shows the parcel gone."""
    try:
        for pat in ("lp_rescue_counts:", "lp_rescue_total:", "lp_rescue_verdict:"):
            frappe.cache().delete_keys(pat)   # wildcard delete, site-prefixed once
    except Exception:
        pass


@frappe.whitelist()
def board(tab="todo", days=30, q="", limit=30, offset=0, reason="", surface="",
          chip=""):
    """One rescue tab + its chips + counts + my day, in one call.

    `tab` is the QUESTION (todo / watch / history) and `chip` is the pile
    inside it. Old callers still say "exceptions" or "backlog" and are
    routed by resolve_tab, so bookmarks and the pulse poller keep working.
    `reason` narrows the parcel queues by the carrier's last word."""
    role = _gate()
    tab, chip = resolve_tab(tab, chip)
    queue = chip or _TAB_DEFAULT[tab]
    # Gate the DATA, not just the chip: a pile hidden from the nav that
    # still answers on a hand-typed request is not hidden at all.
    allowed = _allowed_tabs(role, surface)
    if queue not in allowed:
        queue = next((c for c in CHIPS[tab] if c in allowed), None) \
            or next((c for c in CHIPS["todo"] if c in allowed), "exceptions")
        chip = queue
    reason = reason if reason in ("rescuable", "cancelled") else ""
    days = min(max(int(days or 30), 1), 90)
    limit = min(max(int(limit or 30), 1), 100)
    offset = max(int(offset or 0), 0)
    vals = {"days": days, "limit": limit, "offset": offset}

    # The four queue depths cost ~0.6 s together (a correlated last-event
    # read per parcel); a decision busts them, otherwise a minute is fine.
    counts = _cached_counts(days)
    counts["mine"] = _mine_count(days)
    # The split that decides whether a call can save anything, for the two
    # queues a call is made from. Cached: it is a correlated read per parcel.
    if queue in ("exceptions", "failed"):
        ck = f"lp_rescue_verdict:{queue}:{days}"
        split = None
        try:
            split = frappe.cache().get_value(ck, expires=True)
        except Exception:
            pass
        if not split:
            v = dict(vals)
            canc = int(frappe.db.sql(
                f"SELECT COUNT(*) FROM `tabDelivery Note` dn {_SO_JOIN} WHERE {_dn_where(queue, v, 'cancelled')}", v)[0][0])
            split = {"cancelled": canc, "rescuable": max(0, counts[queue] - canc)}
            try:
                frappe.cache().set_value(ck, split, expires_in_sec=120)
            except Exception:
                pass
        counts["cancelled"] = split["cancelled"]
        counts["rescuable"] = split["rescuable"]

    if queue == "callback":
        # 308 orders carry a next-call time and 176 of them are already past
        # it (measured 2026-09-21). The timer has been written on every
        # no-answer since the lane opened; no screen has ever shown it, so
        # two thirds of the callbacks are late and nobody could have known.
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_next_call_at IS NOT NULL",
                 # NOT custom_sales_status for the delivered test. That column
                 # only ever holds Pending / Confirmed / Did not Answer /
                 # Follow Up / On Hold / Duplicated / Not Delivered /
                 # Cancelled — "Delivered" is not one of its values, so the
                 # first version of this filter excluded nothing at all and
                 # 73 of the 159 callbacks on the tab were parcels that had
                 # already arrived, the oldest waiting since 30 July.
                 # Whether the parcel finished lives in the OTHER two columns.
                 "so.custom_sales_status <> 'Cancelled'",
                 "COALESCE(so.custom_logistics_status,'') NOT IN ('Delivered', 'Returned')",
                 "COALESCE(so.custom_track_shipment_status,'') "
                 "NOT IN ('Delivered', 'Return', 'Returned')"]
        vals["co"] = _CO
        if q and str(q).strip():
            vals["q"] = f"%{str(q).strip()}%"
            conds.append("(so.name LIKE %(q)s OR so.customer_name LIKE %(q)s"
                         " OR so.custom_awb LIKE %(q)s"
                         + _q_phone(q, vals,
                                    "NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone")
                         + ")")
        where = " AND ".join(conds)
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabSales Order` so WHERE {where}", vals)[0][0]
        rows = frappe.db.sql(
            f"""SELECT so.name AS so_name, so.customer_name AS customer,
                       so.grand_total AS total, so.custom_awb AS awb,
                       COALESCE(NULLIF(so.custom_track_shipment_status,''),
                                so.custom_sales_status) AS track,
                       NULL AS dn,
                       COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
                       so.custom_shipping_city AS city,
                       COALESCE(so.custom_call_attempts, 0) AS attempts,
                       so.custom_next_call_at AS next_call,
                       DATEDIFF(NOW(), so.creation) AS age_d,
                       TIMESTAMPDIFF(HOUR, so.creation, %(now)s) AS age_h
                FROM `tabSales Order` so WHERE {where}
                ORDER BY so.custom_next_call_at
                LIMIT %(limit)s OFFSET %(offset)s""",
            {**vals, "now": _site_now()}, as_dict=True)
    elif queue == "notdelivered":
        conds = ["so.docstatus = 1", "so.company = %(co)s",
                 "so.custom_sales_status = 'Not Delivered'",
                 "so.creation >= DATE_SUB(NOW(), INTERVAL %(ndays)s DAY)"]
        vals["ndays"] = max(days, 60)
        vals["co"] = _CO
        if q and str(q).strip():
            vals["q"] = f"%{str(q).strip()}%"
            conds.append("(so.name LIKE %(q)s OR so.customer_name LIKE %(q)s"
                         " OR so.custom_awb LIKE %(q)s"
                         + _q_phone(q, vals,
                                    "NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone")
                         + ")")
        where = " AND ".join(conds)
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabSales Order` so WHERE {where}", vals)[0][0]
        rows = frappe.db.sql(
            f"""SELECT so.name AS so_name, so.customer_name AS customer,
                       so.grand_total AS total, so.custom_awb AS awb,
                       'Not Delivered' AS track, NULL AS dn,
                       COALESCE(NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone) AS phone,
                       so.custom_shipping_city AS city,
                       COALESCE(so.custom_call_attempts, 0) AS attempts,
                       so.custom_next_call_at AS next_call,
                       DATEDIFF(NOW(), so.creation) AS age_d,
                       TIMESTAMPDIFF(HOUR, so.creation, %(now)s) AS age_h
                FROM `tabSales Order` so WHERE {where}
                ORDER BY COALESCE(so.custom_next_call_at, so.creation)
                LIMIT %(limit)s OFFSET %(offset)s""", {**vals, "now": _site_now()}, as_dict=True)
    else:
        where = _dn_where(queue, vals, reason)
        if q and str(q).strip():
            vals["q"] = f"%{str(q).strip()}%"
            where += (" AND (dn.name LIKE %(q)s OR dn.customer_name LIKE %(q)s"
                      " OR dn.custom_awb LIKE %(q)s"
                      + _q_phone(q, vals,
                                 "NULLIF(so.custom_customer_phone,''), so.custom_shipping_phone")
                      + ")")
        # The verdict condition reads the order, so the count needs the join.
        # Shared only when the number really IS the same for everyone: "mine"
        # is one person's pile and must never ride a team-wide key. It did,
        # and it showed — a colleague holding 15 parcels had her 15 served to
        # every other agent's empty Mine tab, pager and all.
        tk = (f"lp_rescue_total:{queue}:{days}:{reason}"
              if not (q and str(q).strip()) and queue != "mine" else "")
        total = None
        if tk:
            try:
                total = frappe.cache().get_value(tk, expires=True)
            except Exception:
                total = None
        if total is None:
            total = frappe.db.sql(
                f"SELECT COUNT(*) FROM `tabDelivery Note` dn {_SO_JOIN} WHERE {where}", vals)[0][0]
            if tk:
                try:
                    frappe.cache().set_value(tk, int(total), expires_in_sec=60)
                except Exception:
                    pass
        # Newest PROBLEM first, not newest parcel. The posting date is when
        # the parcel shipped; sorting by it put a parcel whose driver failed
        # an hour ago below one that shipped the same morning and has been
        # quiet since. What a rescue agent needs at the top is the thing the
        # carrier just did — including on an old parcel, because a driver
        # touching a thirteen-day-old shipment is exactly the moment a call
        # still saves it. Costs ~350 ms against 11 ms for the date sort
        # (measured on 2,019 live exceptions); worth it for a working queue.
        # ("notdelivered" never reaches here — it is the SO branch above,
        # whose order is a call queue by next_call_at and stays that way.)
        # The working piles are read newest-trouble-first; the decided ones
        # are read oldest-promise-first, because a promise nobody has heard
        # about in four days is the one that needs chasing, not the one made
        # this morning. (`queue`, not `tab` — a tab is three piles now and
        # this test silently stopped matching any of them.)
        order_by = ("last_event_at DESC, dn.posting_date DESC"
                    if queue in ("exceptions", "failed", "stale")
                    else "dn.custom_exception_actioned_at"
                    if queue in ("promised", "followup")
                    else "dn.posting_date")
        rows = frappe.db.sql(
            _dn_select() + f" WHERE {where} ORDER BY {order_by}"
                         " LIMIT %(limit)s OFFSET %(offset)s", vals, as_dict=True)

    # The floor's today (api/clock) — the site date rolls at 22:00 Morocco
    # and rescue is an evening lane; the tally must not zero mid-shift.
    from logistics_portal.api import clock as _clock
    _d0, _d1 = _clock.day_bounds(_clock.floor_today())
    mine = {"redeliver": 0, "reship": 0, "returnreq": 0, "dna": 0, "cancel": 0}
    # SO comments only: act() writes the same tag on the parcel AND the order,
    # so counting both doctypes doubled every decision. The section report
    # counts SO comments too — same convention. (A DN-queue decision with no
    # linked order writes only the DN comment and is missed here — rare.)
    for r in frappe.db.sql(
            """SELECT c.content, COUNT(*) n FROM `tabComment` c
               WHERE c.reference_doctype = 'Sales Order'
                 AND c.owner = %s AND c.creation >= %s AND c.creation < %s
                 AND c.content LIKE 'Rescue: %%'
               GROUP BY c.content""",
            (frappe.session.user, _d0, _d1), as_dict=True):
        for k in mine:
            if r.content.startswith(f"Rescue: {k}"):
                mine[k] += int(r.n or 0)

    now = str(now_datetime())
    sla_h = _rs_settings().get("slaTriageH", 24)
    return {
        "tab": tab, "chip": chip or _TAB_DEFAULT[tab],
        "tabs": list(TABS),
        # Only the chips this door is allowed to open — the Not-Delivered
        # pile stays off /tracking whoever is looking.
        "chips": {t: [c for c in CHIPS[t] if c in allowed] for t in TABS},
        "counts": counts, "total": int(total or 0),
        "rows": [{
            "id": r.dn or r.so_name, "dn": r.dn or "", "order": r.so_name or "",
            "customer": r.customer or "", "total": float(r.total or 0),
            "awb": r.awb or "", "track": r.track or "",
            "phone": (r.phone or "").strip(), "city": (r.city or "").strip().title(),
            "ageD": int(r.age_d or 0), "attempts": int(r.attempts or 0),
            "lastEvent": _clean(getattr(r, "last_event", "") or "")[:90],
            "lastEventAt": str(getattr(r, "last_event_at", "") or "")[:16],
            # The carrier's word lands here within minutes, so a parcel whose
            # event is an hour old is still a live call, not a queue entry.
            "fresh": bool(_fresh_ev(getattr(r, "last_event_at", None))),
            "heldBy": (getattr(r, "held_by", "") or "").split("@")[0]
                      if str(getattr(r, "held_at", "") or "")[:19] >= _claim_cutoff() else "",
            "heldMine": bool(getattr(r, "held_by", "") == frappe.session.user
                             and str(getattr(r, "held_at", "") or "")[:19] >= _claim_cutoff()),
            "waitUntil": str(getattr(r, "wait_until", "") or "")[:16],
            "verdict": _verdict(getattr(r, "last_event", "") or ""),
            "again": bool(getattr(r, "prior_action", None)),
            "priorAt": str(getattr(r, "prior_at", "") or "")[:16],
            "nextCall": str(r.next_call)[:16] if r.next_call else "",
            "due": bool(r.next_call and str(r.next_call) <= now),
            # Triage SLA in HOURS: the old day-grain math (age_d * 24) needed
            # a full 2 days to breach a 24h target, understating every breach.
            "slaBreached": bool(int(r.attempts or 0) == 0
                                and int(getattr(r, "age_h", 0) or 0) > sla_h),
        } for r in rows],
        "mine": mine,
        "reasons": _rs_settings().get("reasons", []),
        "reasonsBy": _rs_settings().get("reasonsBy", {}),
        "promiseSlaH": _promise_sla_h(),
        "serverNow": now[:19],
    }


# The carrier's status, read as an answer to "did my rescue work?".
# Anything unlisted (including no status at all) counts as still open —
# never as a failure the agent has to wear.
_OUTCOME = {
    "Delivered": "landed",
    "Out For Delivery": "open", "In Transit": "open",
    "Picked up": "open", "Pending": "open",
    "Delivery Exception": "failed", "Failed Attempt": "failed",
    "Return": "failed",
}


@frappe.whitelist()
def my_report(days=7, frm=None, to=None):
    """The tracking agent's OWN numbers — measured in THEIR craft: rescue
    decisions, the save rate (kept moving vs. sent back), and how many of the
    parcels they touched actually got delivered afterwards."""
    _gate()
    from logistics_portal.api.confirmation import _range
    me = frappe.session.user
    rng, rng_vals = _range(days, frm, to)
    rng_vals = {**rng_vals, "me": me}
    c_rng = rng.format(col="c.creation")

    acts = {"redeliver": 0, "reship": 0, "returnreq": 0, "dna": 0,
            "cancel": 0, "resolve": 0}
    daily = {}
    for r in frappe.db.sql(
            f"""SELECT DATE(c.creation) d, c.content, COUNT(*) n
                FROM `tabComment` c
                WHERE c.owner = %(me)s AND c.content LIKE 'Rescue: %%' AND {c_rng}
                GROUP BY DATE(c.creation), c.content""", rng_vals, as_dict=True):
        if "(bulk)" in (r.content or ""):
            continue
        action = (r.content.split("Rescue: ", 1)[1] or "").split(" ", 1)[0].strip("()—-→ ")
        if action not in acts:
            continue
        n = int(r.n or 0)
        acts[action] += n
        day = daily.setdefault(str(r.d), {"save": 0, "dna": 0, "back": 0})
        if action in ("redeliver", "reship"):
            day["save"] += n
        elif action == "dna":
            day["dna"] += n
        elif action in ("returnreq", "cancel"):
            day["back"] += n

    saves = acts["redeliver"] + acts["reship"]
    closed = saves + acts["returnreq"] + acts["cancel"]

    # Of the orders this agent touched in the window: how many are DELIVERED
    # now — the number that says the rescue actually worked.
    outcome = frappe.db.sql(
        f"""SELECT COUNT(DISTINCT c.reference_name),
                   COUNT(DISTINCT CASE WHEN dn.custom_track_shipment_status
                                            = 'Delivered'
                                       THEN c.reference_name END)
            FROM `tabComment` c
            JOIN `tabDelivery Note Item` dni
              ON dni.against_sales_order = c.reference_name AND dni.docstatus = 1
            JOIN `tabDelivery Note` dn
              ON dn.name = dni.parent AND dn.docstatus = 1
            WHERE c.owner = %(me)s AND c.reference_doctype = 'Sales Order'
              AND c.content LIKE 'Rescue: %%' AND {c_rng}""", rng_vals)[0]

    # Where the parcels this agent tried to SAVE actually got to.
    #
    # `acted`/`deliveredAfter` above answer a different question — every
    # order touched, and how many of those are delivered — and the screen
    # was reading them as a success rate. They cannot be one: the agent's
    # own return requests sit in that denominator and can never be
    # delivered. Measured 2026-09-18 on a real week: one agent's card read
    # "3 of 113" (2.7%) for work that was 3 landed and 5 still moving out
    # of 12 save attempts. Only the saves belong in this count.
    save_out = {"n": 0, "landed": 0, "open": 0, "failed": 0}
    for r in frappe.db.sql(
            f"""SELECT COALESCE(x.st, '') st, COUNT(*) n FROM (
                    SELECT c.reference_name so,
                           MAX(dn.custom_track_shipment_status) st
                    FROM `tabComment` c
                    JOIN `tabDelivery Note Item` dni
                      ON dni.against_sales_order = c.reference_name
                     AND dni.docstatus = 1
                    JOIN `tabDelivery Note` dn
                      ON dn.name = dni.parent AND dn.docstatus = 1
                    WHERE c.owner = %(me)s
                      AND c.reference_doctype = 'Sales Order'
                      AND (c.content LIKE 'Rescue: redeliver%%'
                           OR c.content LIKE 'Rescue: reship%%')
                      AND {c_rng}
                    GROUP BY c.reference_name
                ) x GROUP BY COALESCE(x.st, '')""", rng_vals, as_dict=True):
        n = int(r.n or 0)
        save_out["n"] += n
        save_out[_OUTCOME.get(r.st, "open")] += n

    return {
        "acts": acts,
        "daily": [{"date": d, **v} for d, v in sorted(daily.items())],
        "saveRate": round(saves * 100 / closed) if closed else None,
        "acted": int(outcome[0] or 0),
        "deliveredAfter": int(outcome[1] or 0),
        "saved": save_out,
    }


def _parse_tag(content):
    """"Rescue: redeliver — note · by x" → ("redeliver", "note")."""
    body = _clean(content or "").split("Rescue: ", 1)[-1]
    body = body.split(" · by ", 1)[0]
    action = body.split(" ", 1)[0].strip("()—-→ ")
    note = body.split(" — ", 1)[1].strip() if " — " in body else ""
    return action, note[:120]


@frappe.whitelist()
def my_log(days=7, frm=None, to=None, action="", limit=60, offset=0):
    """Every decision this agent made, newest first, with WHERE THE PARCEL
    GOT TO after it.

    The dashboard above counts; this one remembers. An agent who made 223
    decisions in three days could see totals and a bar chart but had no way
    to answer "what did I do on this customer, and did it work?" — so the
    work was invisible the moment it left the queue, and a redeliver that
    fell over again looked exactly like one that landed.

    Sales Order comments only, the same spine as `mine` and `my_report`:
    act() writes the identical tag on the parcel AND the order, and counting
    both doctypes would double every decision. (A DN-queue decision with no
    linked order writes only the parcel comment and is missed here — rare,
    and the same gap the counters already carry.)"""
    _gate()
    from logistics_portal.api.confirmation import _range
    rng, rng_vals = _range(days, frm, to)
    rng_vals = {**rng_vals, "me": frappe.session.user}
    limit = min(max(int(limit or 60), 1), 200)
    offset = max(int(offset or 0), 0)

    pat = "Rescue: %"
    if action and action in ("redeliver", "reship", "returnreq", "dna",
                             "cancel", "resolve"):
        pat = f"Rescue: {action}%"
    rng_vals["pat"] = pat
    c_rng = rng.format(col="c.creation")

    total = int(frappe.db.sql(
        f"""SELECT COUNT(*) FROM `tabComment` c
            WHERE c.owner = %(me)s AND c.reference_doctype = 'Sales Order'
              AND c.content LIKE %(pat)s AND {c_rng}""", rng_vals)[0][0] or 0)

    rows = frappe.db.sql(
        f"""SELECT c.creation at, c.content, c.reference_name so
            FROM `tabComment` c
            WHERE c.owner = %(me)s AND c.reference_doctype = 'Sales Order'
              AND c.content LIKE %(pat)s AND {c_rng}
            ORDER BY c.creation DESC
            LIMIT {limit} OFFSET {offset}""", rng_vals, as_dict=True)
    if not rows:
        return {"rows": [], "total": total}

    # Two flat lookups instead of a join: joining Delivery Note Item to a
    # per-comment query fans out on basket size and would multiply both the
    # row count and the money.
    orders = list({r.so for r in rows if r.so})
    ph = ", ".join(["%s"] * len(orders))
    so_by = {r.name: r for r in frappe.db.sql(
        f"""SELECT name, customer_name, custom_shipping_city city,
                   grand_total total
            FROM `tabSales Order` WHERE name IN ({ph})""",
        orders, as_dict=True)}
    # Latest submitted parcel per order — GROUP_CONCAT ordered by creation,
    # first element. Statuses carry no commas.
    dn_by = {r.so: r for r in frappe.db.sql(
        f"""SELECT dni.against_sales_order so,
                   SUBSTRING_INDEX(GROUP_CONCAT(dn.name
                       ORDER BY dn.creation DESC), ',', 1) dn,
                   SUBSTRING_INDEX(GROUP_CONCAT(
                       COALESCE(dn.custom_track_shipment_status, '')
                       ORDER BY dn.creation DESC), ',', 1) st
            FROM `tabDelivery Note Item` dni
            JOIN `tabDelivery Note` dn
              ON dn.name = dni.parent AND dn.docstatus = 1
            WHERE dni.against_sales_order IN ({ph}) AND dni.docstatus = 1
            GROUP BY dni.against_sales_order""", orders, as_dict=True)}

    out = []
    for r in rows:
        act_name, note = _parse_tag(r.content)
        so = so_by.get(r.so)
        parcel = dn_by.get(r.so)
        st = (parcel.st if parcel else "") or ""
        # Only a save has a delivery outcome to report. Sending a parcel
        # back or cancelling an order IS the outcome — painting those
        # "failed" because the carrier never delivered them would be a lie.
        # A no-answer is neither: the customer still owes us a call.
        if act_name in ("redeliver", "reship"):
            outcome = _OUTCOME.get(st, "open")
        elif act_name == "dna":
            outcome = "retry"
        else:
            outcome = "closed"
        out.append({
            "at": str(r.at)[:19],
            "action": act_name,
            "note": note,
            "order": r.so or "",
            "dn": (parcel.dn if parcel else "") or "",
            "customer": (so.customer_name if so else "") or "",
            "city": ((so.city if so else "") or "").strip().title(),
            "total": float(so.total or 0) if so else 0.0,
            "status": st,
            "outcome": outcome,
        })
    return {"rows": out, "total": total}


@frappe.whitelist(methods=["POST"])
def act(id=None, action=None, note=None):
    """One rescue decision. `id` is the Delivery Note (DN queues) or the Sales
    Order (Not-Delivered queue).

    redeliver  record the Redeliver decision on the parcel (carrier retries)
    reship     new SO copy through the normal flow (orders.reship) + record it
    returnreq  the parcel comes back — Return Requested on the parcel
    dna        customer unreachable: bump attempts, set the retry timer
    cancel     order is dead: Cancelled with a reason (+ return the parcel)
    """
    _gate()
    id = (id or "").strip()
    note = (note or "").strip()
    if action not in ACTIONS:
        frappe.throw("Unknown action.")

    is_dn = frappe.db.exists("Delivery Note", id)
    is_so = not is_dn and frappe.db.exists("Sales Order", id)
    if not (is_dn or is_so):
        frappe.throw("Unknown parcel/order.")
    # Every rescue queue is company-scoped; the write must be too.
    if frappe.db.get_value("Delivery Note" if is_dn else "Sales Order",
                           id, "company") != _CO:
        frappe.throw("Unknown parcel/order.")
    dn = id if is_dn else ""
    # MIN, matching the board's SO link — get_value picked an arbitrary line,
    # so on multi-order parcels the agent could act on a different order than
    # the one the row displayed.
    order = id if is_so else (frappe.db.sql(
        """SELECT MIN(against_sales_order) FROM `tabDelivery Note Item`
           WHERE parent = %s""", (dn,))[0][0] or "")

    # Ownership fence for the per-agent Not-Delivered scope: the confirmation
    # board filters rows by _assign, but this endpoint used to accept ANY order
    # id — one call could act on (and, worse, claim credit for) a colleague's
    # order. Managers and section admins stay unrestricted; the shared DN
    # queues (exceptions/failed/stale/backlog) are team-worked by design.
    if is_so and not _is_rs_admin():
        assigned = frappe.db.get_value("Sales Order", id, "_assign") or ""
        if f'"{frappe.session.user}"' not in assigned:
            frappe.throw("This order is assigned to another agent.",
                         frappe.PermissionError)

    if action == "cancel" and not note:
        frappe.throw("A cancel needs a reason.")

    now = now_datetime()
    attempts = 0
    tag = f"Rescue: {action}" + (f" — {note}" if note else "") + f" · by {frappe.session.user}"

    if action == "reship":
        if not order:
            frappe.throw("No order linked to this parcel.")
        from logistics_portal.api.orders import reship
        res = reship(order)
        new_order = res.get("order") if isinstance(res, dict) else ""
        tag = f"Rescue: reship → {new_order}" + (f" — {note}" if note else "") \
              + f" · by {frappe.session.user}"

    # Parcel-side record (turns the exceptions pile into a worked queue).
    if dn and action in _DN_ACTION:
        dn_action = _DN_ACTION[action]
        doc = frappe.get_doc("Delivery Note", dn)
        if frappe.get_meta("Delivery Note").has_field("custom_exception_action"):
            doc.db_set("custom_exception_action", dn_action, update_modified=False)
            doc.db_set("custom_exception_actioned_at", now, update_modified=False)
            # A new decision reopens the question of how it ends.
            if frappe.get_meta("Delivery Note").has_field("custom_rescue_outcome"):
                doc.db_set("custom_rescue_outcome", "", update_modified=False)
                doc.db_set("custom_rescue_outcome_at", None, update_modified=False)
        if note and frappe.get_meta("Delivery Note").has_field("custom_exception_reason"):
            doc.db_set("custom_exception_reason", note[:140], update_modified=False)
        doc.add_comment("Comment", tag)
        # A decision ends the holding — the parcel is finished, not owned —
        # and joins the same trail as the notes and the carrier calls, so the
        # card reads as one story instead of two.
        if _has_claim_fields():
            frappe.db.set_value("Delivery Note", dn,
                                {"custom_rescue_by": "", "custom_rescue_at": None,
                                 "custom_rescue_wait_until": None},
                                update_modified=False)
        _log(dn, order, "decision", f"{action}" + (f" — {note}" if note else ""))

    # Order-side record + state. Attribution: a rescue touch must NOT steal
    # the confirming agent's credit — custom_allocated_to feeds the done tabs,
    # the money report and the delivered bonus points, and this line used to
    # overwrite it unconditionally (a one-call transfer of a colleague's
    # delivered-parcel bonus). Claim it only when nobody holds it.
    if order:
        so_updates = {"custom_last_call_at": now}
        if not (frappe.db.get_value("Sales Order", order, "custom_allocated_to") or ""):
            so_updates["custom_allocated_to"] = frappe.session.user
        if action == "dna":
            attempts = int(frappe.db.get_value(
                "Sales Order", order, "custom_call_attempts") or 0) + 1
            so_updates["custom_call_attempts"] = attempts
            so_updates["custom_next_call_at"] = add_to_date(
                now, hours=_rs_settings()["retryDna"])
        else:
            so_updates["custom_next_call_at"] = None
        if action == "cancel":
            so_updates["custom_sales_status"] = "Cancelled"
            if note and frappe.get_meta("Sales Order").has_field(
                    "custom_cancellation_reason"):
                so_updates["custom_cancellation_reason"] = note[:140]
        frappe.db.set_value("Sales Order", order, so_updates, update_modified=True)
        frappe.get_doc("Sales Order", order).add_comment(
            "Comment", tag + (f" (attempt {attempts})" if action == "dna" else ""))

    frappe.db.commit()
    _bust()
    # A pinned parcel leaves the actor's workspace queue with the decision —
    # same contract as confirmation.act, or the pin serves it forever.
    try:
        from logistics_portal.api.confirmation import unpin_after_decision
        unpin_after_decision(order or id)
    except Exception:
        pass
    return {"ok": True, "id": id, "action": action, "attempts": attempts,
            "order": order or ""}


def settle_outcomes(limit=400):
    """Stamp how a promise ENDED, once, when it ends.

    The board used to infer the outcome from the live tracking status at
    read time. That answers "where is it now", not "did the promise hold" —
    a parcel that failed and was later delivered read `landed`, and the
    failure it cost us disappeared from history. Measured 2026-09-21: of 83
    redelivers in 30 days, 31 had failed, 22 had landed and 30 were still
    moving. None of that was recorded anywhere; it was recomputed on every
    page load and true only for that second.

    Scheduled. Idempotent — it only ever writes a blank outcome."""
    try:
        if not frappe.get_meta("Delivery Note").has_field("custom_rescue_outcome"):
            return
        rows = frappe.db.sql(
            f"""SELECT dn.name, dn.custom_track_shipment_status trk,
                       dn.custom_return_shipment ret
                FROM `tabDelivery Note` dn
                WHERE dn.docstatus = 1 AND dn.company = %(co)s
                  AND dn.custom_exception_action IN ('Redeliver', 'Reship', 'Follow Up')
                  AND dn.custom_exception_actioned_at IS NOT NULL
                  AND COALESCE(dn.custom_rescue_outcome,'') = ''
                LIMIT {int(limit)}""", {"co": _CO}, as_dict=True)
        now = now_datetime()
        done = 0
        for r in rows:
            # A parcel physically back in the building is settled whatever
            # the tracker says — the return note is the harder evidence.
            if r.ret:
                out = "returned"
            else:
                out = {"Delivered": "landed",
                       "Return": "returned", "Returned": "returned"}.get(r.trk or "")
            if not out:
                continue
            frappe.db.set_value("Delivery Note", r.name, {
                "custom_rescue_outcome": out,
                "custom_rescue_outcome_at": now}, update_modified=False)
            done += 1
        if done:
            frappe.db.commit()
            _bust()
        return {"settled": done, "scanned": len(rows)}
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "rescue.settle_outcomes")


def _promise_sla_h():
    return int(_rs_settings().get("promiseSlaH", 48))


@frappe.whitelist(methods=["POST"])
def bulk_act(ids=None, action=None, note=None):
    """Bulk triage for the backlog pile: mark parcels Return Requested or
    Resolved without the per-customer call flow. Section admins/manager only —
    it moves hundreds of parcels in one click."""
    import json as _json
    _gate()
    if not _is_rs_admin():
        frappe.throw("Only the portal manager or a rescue section admin can "
                     "bulk-triage.", frappe.PermissionError)
    if isinstance(ids, str):
        ids = _json.loads(ids)
    ids = [str(x).strip() for x in (ids or []) if str(x).strip()]
    if not ids:
        frappe.throw("Nothing selected.")
    if len(ids) > 200:
        frappe.throw("200 parcels max per batch.")
    if action not in ("returnreq", "resolve"):
        frappe.throw("Unknown bulk action.")
    note = (note or "").strip()
    dn_action = {"returnreq": "Return Requested", "resolve": "Resolved"}[action]
    now = now_datetime()
    tag = (f"Rescue: {action} (bulk)" + (f" — {note}" if note else "")
           + f" · by {frappe.session.user}")
    done, skipped = [], []
    has_field = frappe.get_meta("Delivery Note").has_field("custom_exception_action")
    for dn in ids:
        # Per-item isolation: one bad parcel must not abort (and discard) the
        # rest of a 200-parcel triage batch.
        try:
            if frappe.db.get_value("Delivery Note", dn, "company") != _CO:
                skipped.append(dn)
                continue
            doc = frappe.get_doc("Delivery Note", dn)
            if has_field:
                doc.db_set("custom_exception_action", dn_action, update_modified=False)
                doc.db_set("custom_exception_actioned_at", now, update_modified=False)
            doc.add_comment("Comment", tag)
            # Mirror the tag on the ORDER too: the board's "mine" tally and the
            # section report count SO comments only, so bulk triage — the tool
            # built for the 17k backlog — was invisible in every rescue metric.
            # The "(bulk)" marker keeps it out of bonus scoring.
            so = frappe.db.sql(
                """SELECT MIN(against_sales_order) FROM `tabDelivery Note Item`
                   WHERE parent = %s""", (dn,))[0][0]
            if so and frappe.db.exists("Sales Order", so):
                frappe.get_doc("Sales Order", so).add_comment("Comment", tag)
            done.append(dn)
        except Exception:
            skipped.append(dn)
            frappe.log_error(frappe.get_traceback(), "rescue.bulk_act")
    frappe.db.commit()
    _bust()
    return {"ok": True, "done": len(done), "skipped": skipped}


@frappe.whitelist()
def report(days=7):
    """Rescue-section report: per-agent decisions, RESCUE RATE (saved parcels
    vs lost), reasons, day by day. Manager or rescue section admin."""
    _gate()
    if not _is_rs_admin():
        frappe.throw("Only the portal manager or a section admin can open the "
                     "section report.", frappe.PermissionError)
    days = min(max(int(days or 7), 1), 90)
    since = f"DATE_SUB(NOW(), INTERVAL {days} DAY)"

    per_agent = {}
    for r in frappe.db.sql(
            f"""SELECT c.owner, c.content FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order'
                  AND c.content LIKE 'Rescue: %%' AND c.creation >= {since}""",
            as_dict=True):
        action = (r.content.split("Rescue: ", 1)[1] or "").split(" ", 1)[0].strip("()—-→ ")
        a = per_agent.setdefault(r.owner, {"redeliver": 0, "reship": 0,
                                           "returnreq": 0, "dna": 0, "cancel": 0})
        if action in a:
            a[action] += 1

    agents = []
    for user, a in per_agent.items():
        saved = a["redeliver"] + a["reship"]
        lost = a["returnreq"] + a["cancel"]
        agents.append({
            "agent": user.split("@")[0], "user": user, **a,
            "total": sum(a.values()),
            "rescueRate": round(saved * 100.0 / (saved + lost), 1) if (saved + lost) else 0,
        })
    agents.sort(key=lambda x: -x["total"])

    reasons = {}
    for r in frappe.db.sql(
            f"""SELECT c.content FROM `tabComment` c
                WHERE c.reference_doctype = 'Sales Order'
                  AND (c.content LIKE 'Rescue: cancel%%' OR c.content LIKE 'Rescue: returnreq%%')
                  AND c.creation >= {since}""", as_dict=True):
        txt = r.content
        reason = txt.split("—", 1)[1].split("· by", 1)[0].strip() if "—" in txt else ""
        reasons[reason or "(no reason)"] = reasons.get(reason or "(no reason)", 0) + 1
    reason_rows = sorted(({"reason": k, "n": v} for k, v in reasons.items()),
                         key=lambda x: -x["n"])[:12]

    funnel = frappe.db.sql(
        f"""SELECT DATE(c.creation) d,
                   SUM(c.content LIKE 'Rescue: redeliver%%' OR c.content LIKE 'Rescue: reship%%') saved,
                   SUM(c.content LIKE 'Rescue: returnreq%%' OR c.content LIKE 'Rescue: cancel%%') lost,
                   SUM(c.content LIKE 'Rescue: dna%%') dna
            FROM `tabComment` c
            WHERE c.reference_doctype = 'Sales Order'
              AND c.content LIKE 'Rescue: %%' AND c.creation >= {since}
            GROUP BY DATE(c.creation) ORDER BY d""", as_dict=True)

    return {
        "days": days,
        "agents": agents,
        "reasons": reason_rows,
        "funnel": [{"date": str(f.d), "saved": int(f.saved or 0),
                    "lost": int(f.lost or 0), "dna": int(f.dna or 0)} for f in funnel],
    }


@frappe.whitelist()
def dashboard():
    """The rescue lane's queue-health view — the sibling the other two lanes
    always had. All panels describe RIGHT NOW (there is no snapshot history):
    queue depths with value at stake, how long failing parcels have waited
    untouched, and the day-by-day inflow vs. decisions for two weeks.

    Team-level view — with the ten oldest failures' customer names and
    phones. Section admins and the manager only."""
    _gate()
    if not _is_rs_admin():
        frappe.throw("Not authorized.", frappe.PermissionError)
    sla_h = _rs_settings().get("slaTriageH", 24)

    cards = {}
    for tab in ("exceptions", "failed", "stale", "backlog"):
        vals = {"days": 30}
        where = _dn_where(tab, vals)
        r = frappe.db.sql(
            f"""SELECT COUNT(*), ROUND(COALESCE(SUM(dn.grand_total), 0))
                FROM `tabDelivery Note` dn {_SO_JOIN} WHERE {where}""", vals)[0]
        cards[tab] = {"n": int(r[0] or 0), "value": int(r[1] or 0)}

    # Untouched-vs-SLA and age spread of the two active failure queues.
    vals = {"days": 30}
    where = _dn_where("exceptions", vals)
    where = where.replace("dn.custom_track_shipment_status = %(track)s",
                          "dn.custom_track_shipment_status IN "
                          "('Delivery Exception', 'Failed Attempt')")
    vals.pop("track", None)
    aging = frappe.db.sql(
        f"""SELECT
              SUM(TIMESTAMPDIFF(HOUR, dn.creation, %(now)s) <= 24),
              SUM(TIMESTAMPDIFF(HOUR, dn.creation, %(now)s) BETWEEN 25 AND 72),
              SUM(TIMESTAMPDIFF(HOUR, dn.creation, %(now)s) > 72),
              SUM(COALESCE(so.custom_call_attempts, 0) = 0
                  AND TIMESTAMPDIFF(HOUR, dn.creation, %(now)s) > %(sla)s)
            FROM `tabDelivery Note` dn
            LEFT JOIN `tabSales Order` so
              ON so.name = (SELECT MIN(dni.against_sales_order)
                            FROM `tabDelivery Note Item` dni
                            WHERE dni.parent = dn.name)
            WHERE {where}""", {"now": _site_now(), **vals, "sla": sla_h})[0]
    ages = {"d1": int(aging[0] or 0), "d3": int(aging[1] or 0),
            "older": int(aging[2] or 0), "breached": int(aging[3] or 0)}

    # 14 days: parcels that STARTED failing vs. rescue decisions taken.
    inflow = {str(r[0]): int(r[1] or 0) for r in frappe.db.sql(
        """SELECT dn.posting_date, COUNT(*) FROM `tabDelivery Note` dn
           WHERE dn.docstatus = 1 AND dn.company = %s
             AND dn.custom_track_shipment_status IN
                 ('Delivery Exception', 'Failed Attempt')
             AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
           GROUP BY dn.posting_date""", (_CO,))}
    decided = {str(r[0]): int(r[1] or 0) for r in frappe.db.sql(
        """SELECT DATE(c.creation), COUNT(*) FROM `tabComment` c
           JOIN `tabSales Order` so ON so.name = c.reference_name
           WHERE c.reference_doctype = 'Sales Order'
             AND so.company = %s
             AND c.content LIKE 'Rescue: %%'
             AND c.creation >= DATE_SUB(CURDATE(), INTERVAL 14 DAY)
           GROUP BY DATE(c.creation)""", (_CO,))}
    days_axis = [str(r[0]) for r in frappe.db.sql(
        """SELECT DATE_SUB(CURDATE(), INTERVAL n DAY) FROM
           (SELECT 13 n UNION SELECT 12 UNION SELECT 11 UNION SELECT 10
            UNION SELECT 9 UNION SELECT 8 UNION SELECT 7 UNION SELECT 6
            UNION SELECT 5 UNION SELECT 4 UNION SELECT 3 UNION SELECT 2
            UNION SELECT 1 UNION SELECT 0) t ORDER BY 1""")]
    daily = [{"d": d, "inflow": inflow.get(d, 0), "decided": decided.get(d, 0)}
             for d in days_axis]

    # The ten longest-waiting untouched failures — the call list.
    oldest = frappe.db.sql(
        _dn_select() + """ WHERE dn.docstatus = 1 AND dn.company = %(co)s
              AND COALESCE(dn.custom_exception_action,'') = ''
              AND dn.custom_track_shipment_status IN
                  ('Delivery Exception', 'Failed Attempt')
              AND dn.posting_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            ORDER BY dn.posting_date LIMIT 10""",
        {"co": _CO, "snow": _site_now()}, as_dict=True)

    return {
        "cards": cards, "ages": ages, "slaH": sla_h, "daily": daily,
        "oldest": [{
            "dn": r.dn, "order": r.so_name or "", "customer": r.customer or "",
            "phone": (r.phone or "").strip(), "track": r.track or "",
            "ageD": int(r.age_d or 0), "attempts": int(r.attempts or 0),
            "lastEvent": _clean(getattr(r, "last_event", "") or "")[:90],
            "lastEventAt": str(getattr(r, "last_event_at", "") or "")[:16],
            "verdict": _verdict(getattr(r, "last_event", "") or ""),
            "again": bool(getattr(r, "prior_action", None)),
            "priorAt": str(getattr(r, "prior_at", "") or "")[:16],
            "value": float(r.total or 0),
        } for r in oldest],
        "serverNow": str(now_datetime())[:19],
    }


# ══ The desk: who is holding this parcel, and what has been done to it ═════
#
# Audited 2026-09-17 before writing any of this. In thirty days exactly ONE
# parcel was decided by two different people, so this is not a collision
# guard — agents were not stepping on each other. What was missing is every
# other thing a desk needs: nobody could see who was holding what, an agent
# had no list of their own work, a parcel escalated to Cathedis kept
# screaming in the queue with no way to say "they are looking at it until
# Thursday", and the entire conversation with the carrier — the actual daily
# job — lived in WhatsApp and died there. The decision trail itself was
# honest (93 of 93 decisions wrote both the comment and the field); it just
# stopped at the decision and recorded nothing on the way to it.

RESCUE_DT = "LP Rescue Event"
# claim / release / takeover / note / carrier / wait / decision
_EV_KINDS = ("claim", "release", "takeover", "note", "carrier", "wait", "decision")


def ensure_doctype():
    """The desk's witness. Custom doctype: lives in the DB, no schema files,
    safe to run on every migrate."""
    try:
        if frappe.db.exists("DocType", RESCUE_DT):
            return
        frappe.get_doc({
            "doctype": "DocType", "name": RESCUE_DT, "module": "Core",
            "custom": 1, "naming_rule": "Autoincrement", "autoname": "autoincrement",
            "fields": [
                {"fieldname": "parcel", "fieldtype": "Data", "label": "Parcel",
                 "in_standard_filter": 1},
                {"fieldname": "so", "fieldtype": "Data", "label": "Order",
                 "in_standard_filter": 1},
                {"fieldname": "kind", "fieldtype": "Data", "label": "Kind",
                 "in_standard_filter": 1},
                {"fieldname": "agent", "fieldtype": "Data", "label": "Agent",
                 "in_standard_filter": 1},
                {"fieldname": "text", "fieldtype": "Small Text", "label": "Text"},
                # A carrier promise with a date: the parcel sleeps until then.
                {"fieldname": "due", "fieldtype": "Datetime", "label": "Follow up"},
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "rescue.ensure_doctype")


def _log(parcel, order, kind, text="", due=None):
    """Never let bookkeeping break the action it is recording."""
    try:
        frappe.get_doc({
            "doctype": RESCUE_DT, "parcel": parcel or "", "so": order or "",
            "kind": kind, "agent": frappe.session.user, "text": (text or "")[:1000],
            "due": due,
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "rescue._log")


def _claim_h():
    """How long a claim survives without a decision. An agent who goes home
    holding thirty parcels must not take them with him."""
    try:
        return min(max(int(_rs_settings().get("claimHours") or 4), 1), 24)
    except Exception:
        return 4


def _claim_cutoff():
    return str(add_to_date(now_datetime(), hours=-_claim_h()))[:19]


def _has_claim_fields():
    try:
        return frappe.get_meta("Delivery Note").has_field("custom_rescue_by")
    except Exception:
        return False


def _claim_cond(alias="dn"):
    """A shared queue shows only work nobody has taken.

    Deliberately blind to WHO holds it, mine included: the moment I claim a
    parcel it leaves this queue and appears in "Mine", which is the whole
    point — one parcel, one place. It also keeps the team-wide depths
    shareable; a per-agent condition would have made the cached counts show
    whoever happened to warm them. A parcel asleep on a carrier promise is
    out of every queue until the promise falls due."""
    if not _has_claim_fields():
        return "1 = 1"
    return (f"(COALESCE({alias}.custom_rescue_by,'') = '' "
            f" OR COALESCE({alias}.custom_rescue_at, '1900-01-01') < %(claimcut)s) "
            f"AND ({alias}.custom_rescue_wait_until IS NULL "
            f"     OR {alias}.custom_rescue_wait_until <= %(snow)s)")


def _claim_vals(vals):
    vals["claimcut"] = _claim_cutoff()
    vals.setdefault("snow", _site_now())
    return vals


def _holder(dn):
    """(who, since) — empty when nobody holds it or the claim went stale."""
    if not _has_claim_fields():
        return ("", "")
    row = frappe.db.get_value("Delivery Note", dn,
                              ["custom_rescue_by", "custom_rescue_at"], as_dict=True)
    if not row or not row.custom_rescue_by:
        return ("", "")
    if str(row.custom_rescue_at or "")[:19] < _claim_cutoff():
        return ("", "")
    return (row.custom_rescue_by, str(row.custom_rescue_at or "")[:16])


def _set_claim(dn, who, at=None):
    frappe.db.set_value("Delivery Note", dn, {
        "custom_rescue_by": who or "",
        "custom_rescue_at": at,
    }, update_modified=False)


def _order_of(dn):
    return frappe.db.sql("""SELECT MIN(against_sales_order) FROM `tabDelivery Note Item`
                           WHERE parent = %s""", (dn,))[0][0] or ""


def _check_parcel(dn):
    """Rescue-queue parcels only, this company only — an id off the wire must
    not become a write on someone else's document."""
    if not frappe.db.exists("Delivery Note", dn):
        frappe.throw("Unknown parcel.")
    if frappe.db.get_value("Delivery Note", dn, "company") != _CO:
        frappe.throw("Unknown parcel.")
    return dn


@frappe.whitelist(methods=["POST"])
def claim(dn):
    """Take the parcel. It leaves everyone else's queue and joins mine.

    Serialized on the parcel: two agents pressing at the same instant must
    not both be told yes. GET_LOCK spans workers; a Python lock would not."""
    _gate()
    dn = _check_parcel((dn or "").strip())
    if not _has_claim_fields():
        return {"ok": False, "reason": "no_fields"}
    from logistics_portal.api.locks import named_lock
    with named_lock(f"rescue_claim_{dn}"):
        who, since = _holder(dn)
        me = frappe.session.user
        if who and who != me:
            return {"ok": False, "reason": "taken", "by": who, "at": since}
        if who == me:
            return {"ok": True, "by": me, "at": since, "already": True}
        now = now_datetime()
        _set_claim(dn, me, now)
        # Commit INSIDE the lock. The named lock serializes the two workers,
        # but an uncommitted write is invisible to the next transaction under
        # REPEATABLE READ — without this the second agent would read an empty
        # holder and both would be told the parcel is theirs.
        frappe.db.commit()
    _log(dn, _order_of(dn), "claim")
    _bust()
    return {"ok": True, "by": frappe.session.user, "at": str(now)[:16]}


@frappe.whitelist(methods=["POST"])
def release(dn, reason=""):
    """Put it back in the pool — the honest move when you cannot finish it."""
    _gate()
    dn = _check_parcel((dn or "").strip())
    if not _has_claim_fields():
        return {"ok": False, "reason": "no_fields"}
    who, _since = _holder(dn)
    if who and who != frappe.session.user and not _is_rs_admin():
        return {"ok": False, "reason": "taken", "by": who}
    _set_claim(dn, "", None)
    _log(dn, _order_of(dn), "release", reason)
    _bust()
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def take_over(dn, reason=""):
    """A lead moving work off someone — with a reason, on the record. The
    reason is not decoration: an unexplained hand-off is the one thing that
    makes a claim system feel like surveillance instead of a desk."""
    _gate()
    if not _is_rs_admin():
        frappe.throw("Only a lead can take a parcel from another agent.",
                     frappe.PermissionError)
    dn = _check_parcel((dn or "").strip())
    reason = (reason or "").strip()
    if not reason:
        frappe.throw("Say why you are taking it over.")
    who, _since = _holder(dn)
    _set_claim(dn, frappe.session.user, now_datetime())
    _log(dn, _order_of(dn), "takeover", f"from {who or '—'}: {reason}")
    _bust()
    return {"ok": True, "from": who}


@frappe.whitelist(methods=["POST"])
def note(dn, text=""):
    """A line of what happened. Kept on our own witness rather than as a
    Comment: this is what the agent's day is counted from, and Comments do
    not answer 'how many, by whom, today' without scanning free text."""
    _gate()
    dn = _check_parcel((dn or "").strip())
    text = (text or "").strip()
    if not text:
        frappe.throw("Nothing to save.")
    _log(dn, _order_of(dn), "note", text)
    return {"ok": True}


@frappe.whitelist(methods=["POST"])
def carrier_log(dn, asked="", answer="", days=0):
    """What we asked Cathedis and what they said — the daily job, recorded.

    `days` parks the parcel on their answer: it leaves every queue until the
    promise falls due, then comes back by itself. Without this an escalated
    parcel keeps shouting every morning, so the team learns to ignore the
    queue — the exact failure that made this pile 2,019 deep."""
    _gate()
    dn = _check_parcel((dn or "").strip())
    asked, answer = (asked or "").strip(), (answer or "").strip()
    days = min(max(int(days or 0), 0), 14)
    # Parking with no text is the normal case, not an error. The team talks to
    # Cathedis in a WhatsApp group we cannot read (the Business API has no
    # groups), and asking them to retype the conversation here got exactly
    # zero entries in a day of live use. What the portal actually needs from
    # that group is one fact — this parcel is with them until Thursday — so
    # that is all it asks for.
    if not (asked or answer or days):
        frappe.throw("Nothing to save.")
    due = None
    if days:
        due = add_to_date(now_datetime(), days=days)
        if _has_claim_fields():
            frappe.db.set_value("Delivery Note", dn,
                                {"custom_rescue_wait_until": due},
                                update_modified=False)
    body = ((f"→ {asked}" if asked else "") + (f"\n← {answer}" if answer else "")
            or (f"with Cathedis, {days}d" if days else ""))
    _log(dn, _order_of(dn), "carrier", body, due)
    _bust()
    return {"ok": True, "due": str(due)[:16] if due else ""}


@frappe.whitelist()
def timeline(dn, limit=40):
    """Everything this parcel has been through, ours and the carrier's."""
    _gate()
    dn = (dn or "").strip()
    order = _order_of(dn) if frappe.db.exists("Delivery Note", dn) else dn
    limit = min(max(int(limit or 40), 1), 100)
    rows = frappe.db.sql(
        f"""SELECT kind, agent, text, due, creation FROM `tab{RESCUE_DT}`
            WHERE parcel = %(dn)s OR (so = %(o)s AND %(o)s <> '')
            ORDER BY creation DESC LIMIT %(l)s""",
        {"dn": dn, "o": order, "l": limit}, as_dict=True) if frappe.db.exists("DocType", RESCUE_DT) else []
    who, since = _holder(dn) if dn else ("", "")
    return {
        "holder": who, "holderAt": since, "mine": who == frappe.session.user,
        "events": [{
            "kind": r.kind, "agent": (r.agent or "").split("@")[0],
            "text": r.text or "", "due": str(r.due or "")[:16],
            "at": str(r.creation or "")[:16],
        } for r in rows],
    }


# The carrier's own words for a parcel that hit a wall. Narrower than
# _CARRIER_LIKE on purpose: "Out for delivery" is movement, not a problem,
# and a heartbeat that flashes on movement teaches the team to ignore it.
_PROBLEM_LIKE = ("Customer unreachable%", "Customer cancelled%",
                 "The customer has cancelled%", "Cancelled on site%",
                 "Cancellation Reason%", "The driver%", "Justyol has requested%")


@frappe.whitelist()
def pulse(tab="todo", days=30, since="", surface="", chip=""):
    """Has anything happened since the screen last looked?

    Deliberately tiny — one indexed count on the comment table, measured at
    1 ms against the 350 ms a board reload costs. The screen used to reload
    itself whole every two minutes, which was expensive, blind (no way to
    know something HAD arrived) and rude: the list changed under the agent's
    thumb mid-read. This answers the question instead, and the screen decides
    what to do with the answer.

    Two signals, because two different things move a queue. `n` is new
    carrier trouble. `depth` is the tab's depth from the shared 60-second
    cache, which also catches a colleague taking or deciding a parcel — the
    row leaving someone else's list is invisible to the carrier feed."""
    role = _gate()
    since = str(since or "")[:19]
    if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", since):
        since = str(add_to_date(now_datetime(), minutes=-10))[:19]
    ors = " OR ".join(f"content LIKE '{_sql_like(p)}'" for p in _PROBLEM_LIKE)
    row = frappe.db.sql(
        f"""SELECT COUNT(*) n, MAX(creation) at FROM `tabComment`
            WHERE comment_type = 'Comment' AND reference_doctype = 'Sales Order'
              AND creation > %(s)s AND ({ors})""",
        {"s": since}, as_dict=True)[0]
    days = min(max(int(days or 30), 1), 90)
    depth = None
    try:
        # The screen says which QUESTION it is on; the depth it watches is
        # the pile inside it. Without this the poller asked for the depth of
        # "todo", which is not a queue, and silently got None — the board
        # would never have noticed a colleague clearing a row.
        ptab, pchip = resolve_tab(tab, chip)
        queue = pchip or _TAB_DEFAULT[ptab]
        if queue in _allowed_tabs(role, surface) and queue != "mine":
            depth = int(_cached_counts(days).get(queue) or 0)
    except Exception:
        depth = None
    return {"n": int(row.n or 0), "at": str(row.at or "")[:19],
            "depth": depth, "now": _site_now()}


@frappe.whitelist()
def my_day(days=1):
    """The agent's own craft, measured in it: how much they took, how much
    they closed, and how long a parcel sits in their hands before it moves.
    Holding is not working — the gap between claims and decisions is the
    number a lead should look at."""
    _gate()
    days = min(max(int(days or 1), 1), 30)
    me = frappe.session.user
    since = str(add_to_date(now_datetime(), days=-days))[:19]
    if not frappe.db.exists("DocType", RESCUE_DT):
        return {"kinds": {}, "holding": 0, "oldestH": 0}
    rows = frappe.db.sql(
        f"""SELECT kind, COUNT(*) n FROM `tab{RESCUE_DT}`
            WHERE agent = %(me)s AND creation >= %(s)s GROUP BY kind""",
        {"me": me, "s": since}, as_dict=True)
    holding, oldest = 0, 0
    if _has_claim_fields():
        r = frappe.db.sql(
            """SELECT COUNT(*) n, MIN(custom_rescue_at) oldest FROM `tabDelivery Note`
               WHERE custom_rescue_by = %(me)s AND COALESCE(custom_rescue_at,'1900-01-01') >= %(c)s""",
            {"me": me, "c": _claim_cutoff()}, as_dict=True)[0]
        holding = int(r.n or 0)
        if r.oldest:
            oldest = max(0, int((now_datetime() - r.oldest).total_seconds() // 3600))
    return {"kinds": {r.kind: int(r.n) for r in rows},
            "holding": holding, "oldestH": oldest}


_SETTLED = "Returned (reconciled)"


@frappe.whitelist()
def settled_backlog(apply=0, limit=2000):
    """Parcels still flagged as a carrier problem that physically came back.

    A submitted return note against the parcel is the end of its story; the
    tracking status simply never caught up, and 16,953 of these were sitting
    in a queue pretending to be work. Stamping the decision takes them out of
    every rescue query for good — and out of the count that made the tab
    unreadable.

    Read-only unless `apply` is set, and capped per run: this touches
    thousands of live documents and nobody should discover the scale of it
    from the result of a click."""
    _gate()
    if not _is_rs_admin():
        frappe.throw("lp:leadsOnly", frappe.PermissionError)
    limit = min(max(int(limit or 2000), 1), 5000)
    rows = frappe.db.sql(
        """SELECT dn.name, dn.posting_date FROM `tabDelivery Note` dn
           WHERE dn.docstatus = 1 AND dn.company = %(co)s AND dn.is_return = 0
             AND COALESCE(dn.custom_exception_action,'') = ''
             AND dn.custom_track_shipment_status IN %(tracks)s
             AND EXISTS (SELECT 1 FROM `tabDelivery Note` r
                         WHERE r.is_return = 1 AND r.return_against = dn.name
                           AND r.docstatus = 1)
           ORDER BY dn.posting_date LIMIT %(l)s""",
        {"co": _CO, "tracks": _BACKLOG_TRACKS, "l": limit}, as_dict=True)
    total = int(frappe.db.sql(
        """SELECT COUNT(*) FROM `tabDelivery Note` dn
           WHERE dn.docstatus = 1 AND dn.company = %(co)s AND dn.is_return = 0
             AND COALESCE(dn.custom_exception_action,'') = ''
             AND dn.custom_track_shipment_status IN %(tracks)s
             AND EXISTS (SELECT 1 FROM `tabDelivery Note` r
                         WHERE r.is_return = 1 AND r.return_against = dn.name
                           AND r.docstatus = 1)""",
        {"co": _CO, "tracks": _BACKLOG_TRACKS})[0][0] or 0)
    if not int(apply or 0):
        return {"ok": True, "applied": 0, "matched": total,
                "wouldStamp": len(rows),
                "oldest": str(rows[0].posting_date)[:10] if rows else "",
                "sample": [r.name for r in rows[:5]]}
    now = now_datetime()
    done = 0
    for r in rows:
        try:
            frappe.db.set_value("Delivery Note", r.name, {
                "custom_exception_action": _SETTLED,
                "custom_exception_actioned_at": now,
            }, update_modified=False)
            done += 1
        except Exception:
            continue
    frappe.db.commit()
    _bust()
    return {"ok": True, "applied": done, "matched": total, "left": max(0, total - done)}


def release_stale_claims():
    """Scheduled hourly: hand back what nobody is actually working.

    A claim is a promise to finish, not a reservation. Anything held past the
    window without a decision goes back to the pool so the queue never quietly
    empties into private piles."""
    try:
        if not _has_claim_fields():
            return
        cut = _claim_cutoff()
        rows = frappe.db.sql(
            """SELECT name, custom_rescue_by FROM `tabDelivery Note`
               WHERE COALESCE(custom_rescue_by,'') <> ''
                 AND COALESCE(custom_rescue_at,'1900-01-01') < %(c)s LIMIT 500""",
            {"c": cut}, as_dict=True)
        for r in rows:
            frappe.db.set_value("Delivery Note", r.name,
                                {"custom_rescue_by": "", "custom_rescue_at": None},
                                update_modified=False)
        if rows:
            _bust()
            frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "rescue.release_stale_claims")
