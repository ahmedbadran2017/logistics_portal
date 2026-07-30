"""Admin team scorecard — whole-operation performance in one manager view.

Stronger than the per-section reports on purpose. Those count only the portal's
own comment trail (`Confirmation:` / `Rescue:` / `CS:` tags) and so are blind to
the work the team still does on the ERPNext desk — on prod that hid ~99% of the
real activity. Every number here is instead read straight off the orders and
parcels (full coverage, desk + portal):

  - OUTCOME by assignment — for each agent, the orders assigned to them
    (`_assign`, the field the team divides work by) that ARRIVED in the window,
    and what became of them: confirmed / cancelled, then delivered / returned /
    collected. This is the agent's book and what it was actually worth.
  - ACTIVITY by author — from the change log (`tabVersion`): who physically
    touched orders, capturing desk edits the outcome view attributes to the
    assignee. Reveals the heavy desk workers who own few orders themselves.
  - WAREHOUSE — pickers by distinct orders on their submitted pick lists.

Manager-only. Company-scoped to Justyol Morocco (the market this portal serves).
"""

import json

import frappe
from frappe.utils import now_datetime

from logistics_portal.api.confirmation import _CO, _SANE_MAX, _range

# Logistics stages that mean the parcel is out of the confirmation lane's hands
# but not yet a final delivered/returned outcome — "in flight".
_INFLIGHT = ("Label Generated", "Label Printed", "Picked", "Shipped", "Received")


def _manager_gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("The team scorecard is manager-only.", frappe.PermissionError)


def _names(emails):
    """email -> display name, one query."""
    out = {}
    emails = [e for e in {e for e in emails if e}]
    if emails:
        for u in frappe.get_all("User", filters={"name": ["in", emails]},
                                fields=["name", "full_name"]):
            out[u.name] = (u.full_name or "").strip() or u.name.split("@")[0]
    return out


def _short(email):
    return (email or "").split("@")[0]


def _activity(rng, rng_vals, key_sig):
    """Per-user Sales-Order edit count from the change log — desk AND portal.
    tabVersion is large and this scans ~a month of it (~5s on prod), so it's
    cached 5 min, the same TTL the section reports use."""
    ck = "lp_teamperf_act_" + key_sig
    cached = frappe.cache().get_value(ck)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass
    rows = frappe.db.sql(
        f"""SELECT owner, COUNT(*) n
            FROM `tabVersion`
            WHERE ref_doctype = 'Sales Order'
              AND {rng.format(col='creation')}
              AND owner NOT IN ('Administrator', 'Guest')
            GROUP BY owner""", rng_vals, as_dict=True)
    out = {r.owner: int(r.n or 0) for r in rows}
    frappe.cache().set_value(ck, json.dumps(out), expires_in_sec=300)
    return out


@frappe.whitelist()
def team_scorecard(days=30, frm=None, to=None):
    """One manager view of the whole operation's performance over a window."""
    _manager_gate()
    days = min(max(int(days or 30), 1), 365)
    rng, rng_vals = _range(days, frm, to)
    rng_vals["co"] = _CO
    rng_vals["sane"] = _SANE_MAX
    rng_vals["inflight"] = _INFLIGHT
    cohort = rng.format(col="so.creation")   # cohort = orders that ARRIVED

    # ── Confirmation: outcome of each assignee's book (arrived in window) ──
    cc = frappe.db.sql(
        f"""SELECT JSON_UNQUOTE(JSON_EXTRACT(so._assign, '$[0]')) agent,
                   COUNT(*) book,
                   SUM(so.custom_sales_status = 'Confirmed') confirmed,
                   SUM(so.custom_sales_status = 'Cancelled') cancelled,
                   SUM(so.custom_logistics_status = 'Delivered') delivered,
                   SUM(so.custom_logistics_status = 'Returned') returned,
                   SUM(so.custom_logistics_status IN %(inflight)s) inflight,
                   ROUND(SUM(CASE WHEN so.custom_logistics_status = 'Delivered'
                                  AND so.grand_total <= %(sane)s
                                  THEN so.grand_total ELSE 0 END)) collected
            FROM `tabSales Order` so
            WHERE so.docstatus = 1 AND so.company = %(co)s AND {cohort}
              AND so._assign IS NOT NULL AND so._assign NOT IN ('', '[]')
            GROUP BY agent
            HAVING agent IS NOT NULL
            ORDER BY collected DESC""", rng_vals, as_dict=True)

    # ── Activity (who physically touched orders) — desk + portal ──
    key_sig = f"{days}_{frm or ''}_{to or ''}"
    act = _activity(rng, dict(rng_vals), key_sig)

    # ── Warehouse: pickers by distinct orders on submitted pick lists ──
    pk = frappe.db.sql(
        f"""SELECT COALESCE(NULLIF(pl.custom_assigned_picker, ''), pl.owner) picker,
                   COUNT(DISTINCT pli.sales_order) picks,
                   COUNT(DISTINCT DATE(pl.creation)) active_days,
                   COUNT(DISTINCT CASE WHEN DATE(pl.creation) = DATE(so.creation)
                                       THEN pli.sales_order END) sameday
            FROM `tabPick List` pl
            JOIN `tabPick List Item` pli ON pli.parent = pl.name
            LEFT JOIN `tabSales Order` so ON so.name = pli.sales_order
            WHERE pl.docstatus = 1 AND {rng.format(col='pl.creation')}
              AND COALESCE(NULLIF(pl.custom_assigned_picker, ''), pl.owner)
                  NOT IN ('Administrator', 'Guest')
            GROUP BY picker
            ORDER BY picks DESC""", rng_vals, as_dict=True)

    # ── Tickets (CS) — by agent, if any exist in the window ──
    tk = []
    if frappe.db.has_column("Issue", "custom_agent"):
        tk = frappe.db.sql(
            f"""SELECT custom_agent agent, COUNT(*) handled,
                       SUM(status IN ('Resolved', 'Closed')) resolved
                FROM `tabIssue`
                WHERE {rng.format(col='creation')}
                  AND custom_agent IS NOT NULL AND custom_agent != ''
                GROUP BY agent ORDER BY handled DESC""", rng_vals, as_dict=True)

    # ── names for every email that shows up anywhere ──
    emails = ([r.agent for r in cc] + list(act.keys())
              + [r.picker for r in pk] + [r.agent for r in tk])
    names = _names(emails)

    def rate(a, b):
        return round(a * 100 / b) if b else 0

    confirmation = [{
        "user": r.agent, "name": names.get(r.agent, _short(r.agent)),
        "book": int(r.book), "confirmed": int(r.confirmed or 0),
        "cancelled": int(r.cancelled or 0),
        "confirmRate": rate(int(r.confirmed or 0),
                            int(r.confirmed or 0) + int(r.cancelled or 0)),
        "delivered": int(r.delivered or 0), "returned": int(r.returned or 0),
        "inflight": int(r.inflight or 0),
        "deliveryRate": rate(int(r.delivered or 0),
                             int(r.delivered or 0) + int(r.returned or 0)),
        "collected": int(r.collected or 0),
        "edits": int(act.get(r.agent, 0)),
    } for r in cc]

    warehouse = [{
        "user": r.picker, "name": names.get(r.picker, _short(r.picker)),
        "picks": int(r.picks or 0), "activeDays": int(r.active_days or 0),
        "perDay": round(int(r.picks or 0) / int(r.active_days or 1), 1),
        "sameday": int(r.sameday or 0),
        "samedayRate": rate(int(r.sameday or 0), int(r.picks or 0)),
        "edits": int(act.get(r.picker, 0)),
    } for r in pk]

    tickets = [{
        "user": r.agent, "name": names.get(r.agent, _short(r.agent)),
        "handled": int(r.handled or 0), "resolved": int(r.resolved or 0),
        "resolveRate": rate(int(r.resolved or 0), int(r.handled or 0)),
    } for r in tk]

    # Heavy order-touchers the outcome/pick views DON'T already name — genuine
    # desk workers who neither own an assigned book nor a pick list. (Most heavy
    # editors turn out to be pickers updating status; those belong in Warehouse,
    # so they're excluded here to avoid double-listing.) Top 8.
    seen = {r["user"] for r in confirmation} | {r["user"] for r in warehouse}
    activity = sorted(
        ({"user": u, "name": names.get(u, _short(u)), "edits": n}
         for u, n in act.items() if u not in seen and n > 0),
        key=lambda x: -x["edits"])[:8]

    # ── team totals (the confirmation cohort is the operation's spine) ──
    tb = lambda k: sum(r[k] for r in confirmation)
    book, conf, canc = tb("book"), tb("confirmed"), tb("cancelled")
    deliv, ret = tb("delivered"), tb("returned")
    kpis = {
        "book": book, "confirmed": conf, "cancelled": canc,
        "confirmRate": rate(conf, conf + canc),
        "delivered": deliv, "returned": ret,
        "deliveryRate": rate(deliv, deliv + ret),
        "collected": tb("collected"),
        "agents": len(confirmation), "pickers": len(warehouse),
        "picks": sum(r["picks"] for r in warehouse),
    }

    return {
        "range": {"days": days, "from": frm or "", "to": to or "",
                  "custom": bool(frm or to)},
        "kpis": kpis,
        "confirmation": confirmation,
        "warehouse": warehouse,
        "tickets": tickets,
        "activity": activity,
        "serverNow": str(now_datetime())[:19],
    }
