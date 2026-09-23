"""Stopping an order the customer no longer wants.

The problem this exists for, measured on production 2026-09-21:

A customer changes their mind after confirming. The agent opens the order and
presses cancel — and the confirmation lane REFUSES it the moment the warehouse
has touched the order, with an English sentence telling them to "ask the
dispatcher to pull it first" or "route it through Rescue/Exceptions". Neither
of those is a thing. There is no dispatcher pull anywhere in the portal, and
Rescue is built on delivery notes the CARRIER has already failed — a healthy
parcel still on its way appears in none of its tabs.

So the cancel is never recorded at all. The order stays Confirmed and ships.
September: 180 parcels were refused at the customer's door ("cancelled on the
spot in the presence of the driver"); 309 more came back from Cathedis with
the reason "Customer cancelled order by phone", and 302 of those are STILL
marked Confirmed in our own database. August's door figure was 207.

And when the status IS Cancelled — set from the desk, which has no such guard
— nothing physical stops either. The sort wall's scan reads the pick list and
the label state and never asks whether the order is still wanted, so it
allocates the piece, closes the box and prints the label. Thirteen orders in
September were cancelled BEFORE their parcel was cut and shipped anyway.

There is time to act: pick list to delivery note runs a mean of 129 minutes,
and 90% of orders take more than a quarter of an hour. The window is not the
problem. Carrying the message into the warehouse is.

THE RULE HERE: never refuse the request. A customer saying "I don't want it"
is a fact, and a fact the system rejects is a fact the system loses. What the
order's physical position changes is what we can DO about it, not whether we
are willing to hear it.

    new        nothing has moved          -> cancel it outright, as today
    picking    on a live pick list        -> cancel + tell the floor to pull it
    packed     labelled, not handed over  -> cancel + pull it off the manifest
    gone       with the carrier           -> keep it live, open a recall task
    delivered  it arrived                 -> not a cancel; a return

`gone` deliberately does NOT flip the status. A parcel in transit is real, and
marking its order Cancelled would drop it out of the tracking board while it
is still moving — hiding the very parcel someone has to chase. It flips when
the parcel actually comes back, which the return flow already handles.
"""

import frappe
from frappe.utils import now_datetime

DT = "LP Stop Request"
_CO = "Justyol Morocco"

# What can be done about it, worst case last.
MODES = ("cancel_now", "stop", "recall", "too_late")

# An open request is one nobody has closed out yet.
_OPEN = "open"

# The carrier has it from here on.
_CARRIER_HAS_IT = ("Picked up", "In Transit", "Out For Delivery")
_ARRIVED = ("Delivered",)
# Already not going to reach the customer. A recall is pointless here — the
# parcel is on its way back under its own steam, or sitting at the depot
# after a failed attempt — and telling CS to phone Cathedis for a recall
# would be work with nothing at the end of it. Caught in testing against
# production: SAL-ORD-2026-03324 is logistics "Returned" with the carrier
# still saying "Delivery Exception", and the first draft called it `gone`.
_COMING_BACK = ("Return", "Returned", "Delivery Exception", "Failed Attempt")
_BACK_STAGES = ("Returned", "Received")


def _gate():
    from logistics_portal.api.auth import resolve_role
    role = resolve_role(frappe.session.user)
    if role not in ("cs", "confirmation", "tracking", "manager"):
        frappe.throw("lp:csOnly", frappe.PermissionError)
    return role


def ensure_doctype():
    """Create the table on migrate. Custom doctype: lives in the DB, no
    schema files, safe to run every time."""
    try:
        if frappe.db.exists("DocType", DT):
            return
        frappe.get_doc({
            "doctype": "DocType", "name": DT, "module": "Core",
            "custom": 1, "naming_rule": "Expression (old style)",
            "autoname": "naming_series:", "title_field": "so",
            "fields": [
                {"fieldname": "naming_series", "fieldtype": "Data",
                 "label": "Series", "default": "STOP-.YY..MM.-.####", "hidden": 1},
                # Indexed: the sort wall's scan asks "is this order stopped?"
                # on every single piece that crosses the station.
                {"fieldname": "so", "fieldtype": "Data", "label": "Order",
                 "search_index": 1, "in_list_view": 1, "in_standard_filter": 1},
                {"fieldname": "state", "fieldtype": "Data", "label": "State",
                 "default": _OPEN, "search_index": 1, "in_standard_filter": 1,
                 "in_list_view": 1},
                {"fieldname": "mode", "fieldtype": "Data", "label": "What we can do",
                 "in_list_view": 1, "in_standard_filter": 1},
                {"fieldname": "stage_at", "fieldtype": "Data",
                 "label": "Stage when asked"},
                {"fieldname": "customer_name", "fieldtype": "Data", "label": "Customer",
                 "in_list_view": 1},
                {"fieldname": "phone", "fieldtype": "Data", "label": "Phone"},
                {"fieldname": "reason", "fieldtype": "Data", "label": "Reason"},
                {"fieldname": "note", "fieldtype": "Small Text", "label": "Note"},
                {"fieldname": "asked_by", "fieldtype": "Data", "label": "Asked by"},
                {"fieldname": "asked_at", "fieldtype": "Datetime", "label": "Asked at"},
                # The point of the whole exercise: did we actually catch it?
                {"fieldname": "outcome", "fieldtype": "Data", "label": "Outcome",
                 "in_standard_filter": 1},
                {"fieldname": "resolved_by", "fieldtype": "Data", "label": "Closed by"},
                {"fieldname": "resolved_at", "fieldtype": "Datetime", "label": "Closed at"},
            ],
            "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback()[:2000], "stop.ensure_doctype")


_HAVE = False


def have_table():
    """Phase 1 (the scan guard) must work before this table exists, so every
    reader asks first instead of assuming.

    Cached once true and never re-checked: this is called inside the sort
    wall's scan, and a DocType lookup per scanned piece is a query the floor
    pays for all day. It can only go from absent to present, and that
    happens during a migrate, which restarts the workers anyway."""
    global _HAVE
    if _HAVE:
        return True
    try:
        _HAVE = bool(frappe.db.exists("DocType", DT))
    except Exception:
        return False
    return _HAVE


def stopped_sql(so_col):
    """A SQL boolean for "this order must not move", for callers that are
    already selecting from the order. Cancelled through ANY route counts —
    the desk has no guard and produces cancels of its own."""
    cond = f"COALESCE({so_col}.custom_sales_status,'') = 'Cancelled'"
    if have_table():
        # EXISTS, not a join: an order can carry more than one request over
        # its life and a join would duplicate the row it is filtering.
        cond += (f" OR EXISTS (SELECT 1 FROM `tab{DT}` st_ "
                 f"WHERE st_.so = {so_col}.name AND st_.state = '{_OPEN}')")
    return "(" + cond + ")"


def open_orders(orders):
    """Which of these order names have a live stop request."""
    if not orders or not have_table():
        return set()
    rows = frappe.db.sql(
        f"SELECT DISTINCT so FROM `tab{DT}` WHERE state = %(s)s AND so IN %(o)s",
        {"s": _OPEN, "o": tuple(orders)})
    return {r[0] for r in rows}


# ── where the order actually is ───────────────────────────────────────────

def _handed_over(order):
    """A submitted Shipment carrying this order's parcel: it left the door."""
    return bool(frappe.db.sql(
        """SELECT 1 FROM `tabShipment Delivery Note` sdn
             JOIN `tabShipment` sh ON sh.name = sdn.parent AND sh.docstatus = 1
             JOIN `tabDelivery Note Item` di ON di.parent = sdn.delivery_note
            WHERE di.against_sales_order = %s LIMIT 1""", (order,)))


def stage_of(order):
    """(stage, mode) — where the goods are, and therefore what we can do.

    Read in this order deliberately: the carrier's own word outranks our
    internal stage, because ours is written by a sync that can lag."""
    so = frappe.db.get_value(
        "Sales Order", order,
        ["custom_logistics_status", "custom_track_shipment_status",
         "custom_sales_status", "custom_awb", "custom_label_url"], as_dict=True)
    if not so:
        frappe.throw("Unknown order.")
    trk = so.custom_track_shipment_status or ""
    stage = so.custom_logistics_status or ""
    # Our stage and the carrier's word disagree on ~300 live orders because
    # they are written by different jobs at different times. Where they
    # disagree, the FURTHEST-ALONG reading wins, because every one of these
    # answers is about what we can still do, and claiming we can do more
    # than we can is the expensive direction to be wrong in.
    #
    # Caught by sweeping every combination that actually exists rather than
    # a few examples: 26 orders read logistics "Delivered" with the tracker
    # still on "Pending", and the first draft sent those to a carrier recall
    # — a phone call about a parcel the customer already has.
    if trk in _ARRIVED or stage == "Delivered":
        return "delivered", "too_late"
    if trk in _COMING_BACK or stage in _BACK_STAGES:
        return "back", "too_late"
    if trk in _CARRIER_HAS_IT or _handed_over(order):
        return "gone", "recall"
    if stage in ("Label Generated", "Label Printed") \
            or so.custom_awb or so.custom_label_url:
        return "packed", "stop"
    if frappe.db.exists("Pick List Item",
                        {"sales_order": order, "docstatus": ["<", 2]}):
        return "picking", "stop"
    if stage not in ("", "Pending"):
        # The warehouse moved it somewhere we have no finer word for.
        return "picking", "stop"
    return "new", "cancel_now"


@frappe.whitelist()
def preview(order):
    """What the agent is told BEFORE they commit — so the dialog can name the
    real situation instead of showing a button that throws."""
    _gate()
    from logistics_portal.api.utils import resolve_order
    order = resolve_order(order)
    if not order or frappe.db.get_value("Sales Order", order, "company") != _CO:
        frappe.throw("Unknown order.")
    stage, mode = stage_of(order)
    existing = ""
    if have_table():
        existing = frappe.db.get_value(
            DT, {"so": order, "state": _OPEN}, "name") or ""
    return {"order": order, "stage": stage, "mode": mode,
            "already": existing,
            # The vocabulary rides along so the dialog needs one call, not two.
            # It is the SAME list confirmation.act validates against, which is
            # why a stop and a plain cancel group together in every report.
            "reasons": _reasons(),
            "status": frappe.db.get_value("Sales Order", order,
                                          "custom_sales_status") or ""}


# ── the action ────────────────────────────────────────────────────────────

# The confirmation lane validates its cancels against a fixed reason list so
# the desk's reports can group portal cancels alongside desk ones. A stop is
# a cancel, so it answers to the same list.
def _reasons():
    try:
        from logistics_portal.api.confirmation import reason_options
        return reason_options() or []
    except Exception:
        return []


def _cancel_fields(reason, now):
    """Exactly what confirmation.act writes, so a stop and a plain cancel are
    the same row afterwards and no report has to learn a second shape."""
    f = {"custom_sales_status": "Cancelled",
         "custom_allocated_to": frappe.session.user,
         "custom_last_call_at": now, "custom_next_call_at": None}
    if frappe.get_meta("Sales Order").has_field("custom_cancellation_reason"):
        f["custom_cancellation_reason"] = reason
    return f


@frappe.whitelist(methods=["POST"])
def request_stop(order, reason="", note=""):
    """The customer does not want it. Record that, whatever stage it is at.

    This call does not have a failure mode for "too late" — being too late is
    an answer, not an error. What changes with the stage is what happens
    next, and the caller is told which of the four it got."""
    role = _gate()
    from logistics_portal.api.utils import resolve_order
    order = resolve_order(order)
    if not order or frappe.db.get_value("Sales Order", order, "company") != _CO:
        frappe.throw("Unknown order.")
    if frappe.db.get_value("Sales Order", order, "docstatus") != 1:
        frappe.throw("Order is not submitted.")
    # A confirmation agent works their own queue; that lane's discipline
    # stands. CS and tracking answer whoever rings, about any order — which
    # is precisely how these calls arrive, so scoping them by allocation
    # would put the wall back one door further along.
    if role == "confirmation":
        from logistics_portal.api.confirmation import _own_guard
        _own_guard(role, order)

    reason = (reason or "").strip()
    note = (note or "").strip()[:1000]
    opts = _reasons()
    if not reason:
        frappe.throw("lp:stopNeedsReason")
    if opts and reason not in opts:
        frappe.throw("Pick a reason from the list.")

    stage, mode = stage_of(order)
    now = now_datetime()
    info = frappe.db.get_value(
        "Sales Order", order,
        ["customer_name", "custom_customer_phone", "custom_sales_status"],
        as_dict=True) or {}

    ensure_doctype()
    if not have_table():
        # ensure_doctype swallows its own errors by design (it runs on every
        # migrate). If the table still is not there, say so instead of
        # failing on the next line with a Frappe internal.
        frappe.throw("The stop list is not installed on this site yet.")
    existing = frappe.db.get_value(DT, {"so": order, "state": _OPEN},
                                   ["name", "mode"], as_dict=True)
    if existing:
        # Two agents, one customer, one afternoon. Add to the trail rather
        # than opening a second request the floor has to reconcile.
        frappe.get_doc(DT, existing.name).add_comment(
            "Comment", f"Asked again by {frappe.session.user}"
                       + (f" — {note}" if note else ""))
        req = existing.name
    else:
        req = frappe.get_doc({
            "doctype": DT, "so": order, "state": _OPEN, "mode": mode,
            "stage_at": stage, "customer_name": info.get("customer_name") or "",
            "phone": info.get("custom_customer_phone") or "",
            "reason": reason, "note": note,
            "asked_by": frappe.session.user, "asked_at": now,
        }).insert(ignore_permissions=True).name

    doc = frappe.get_doc("Sales Order", order)
    if mode in ("cancel_now", "stop"):
        # Nothing is with the carrier, so the order's truth is: cancelled.
        # Every downstream guard keys on that word — the sort wall now
        # refuses it, the manifest already did.
        frappe.db.set_value("Sales Order", order, _cancel_fields(reason, now),
                            update_modified=True)
        if mode == "cancel_now":
            # Nothing to go and fetch: the request is answered on the spot.
            frappe.db.set_value(DT, req, {
                "state": "done", "outcome": "stopped",
                "resolved_by": frappe.session.user, "resolved_at": now},
                update_modified=False)
        doc.add_comment(
            "Comment",
            f"Stop: {'cancelled' if mode == 'cancel_now' else 'cancel + pull from the floor'}"
            f" ({stage}) — {reason}" + (f" · {note}" if note else "")
            + f" · by {frappe.session.user}")
        try:
            from logistics_portal.api.confirmation import _free_card
            _free_card(order)
        except Exception:
            pass
    else:
        # The parcel is out. Saying Cancelled here would take a live parcel
        # off the tracking board while it is still moving, and the person who
        # has to chase it would lose sight of it. The status flips when the
        # parcel comes back; until then this is a job, not a status.
        doc.add_comment(
            "Comment",
            f"Stop requested too late ({stage}) — {reason}"
            + (f" · {note}" if note else "") + f" · by {frappe.session.user}")
        try:
            from logistics_portal.api.cs import raise_request
            # Three different jobs wear the same "too late" hat, and handing
            # all three the same sentence would send someone to phone the
            # carrier about a parcel that is already on its way back.
            what, kind = {
                "gone": ("The customer cancelled — the parcel is already with the "
                         "carrier. Call Cathedis to recall it.", "other"),
                "back": ("The customer cancelled — the parcel is already coming "
                         "back. See it lands and close the order.", "other"),
            }.get(stage, ("The customer cancelled after delivery — arrange the "
                          "return.", "refund"))
            raise_request(kind=kind,
                          note=f"{what} Reason: {reason}" + (f". {note}" if note else ""),
                          order=order, source="system")
        except Exception:
            # The stop is recorded either way; a CS desk hiccup must not
            # swallow the customer's words a second time.
            frappe.log_error(frappe.get_traceback()[:2000], "stop.request_stop cs")

    frappe.db.commit()
    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation"):
        frappe.cache().delete_value(k)
    return {"ok": True, "request": req, "mode": mode, "stage": stage,
            "cancelled": mode in ("cancel_now", "stop")}


@frappe.whitelist(methods=["POST"])
def resolve_stop(name, outcome="stopped", note=""):
    """Close one out. `outcome` is the only number that says whether any of
    this works: stopped | shipped | recalled | refused."""
    _gate()
    if outcome not in ("stopped", "shipped", "recalled", "refused"):
        frappe.throw("Unknown outcome.")
    r = frappe.db.get_value(DT, name, ["so", "state"], as_dict=True)
    if not r:
        frappe.throw("Unknown request.")
    now = now_datetime()
    frappe.db.set_value(DT, name, {
        "state": "done", "outcome": outcome,
        "resolved_by": frappe.session.user, "resolved_at": now},
        update_modified=True)
    if r.so:
        frappe.get_doc("Sales Order", r.so).add_comment(
            "Comment", f"Stop closed: {outcome}"
                       + (f" — {note.strip()}" if (note or "").strip() else "")
                       + f" · by {frappe.session.user}")
    frappe.db.commit()
    return {"ok": True, "outcome": outcome}
