"""Velocity board — is fulfillment keeping pace, and what's stuck.

The section dashboards and the cockpit show a SNAPSHOT of the queue; this shows
the TREND: orders coming IN (demand) vs labels going OUT (throughput) per day,
the create->label cycle time, and the live backlog — plus the stuck tails, a
parcel sitting in a stage far longer than that stage should take. Manager-only,
Justyol Morocco.

"Out" is measured off the Cathedis label File stamped on each order when the
label is generated (the same PDF the sorting station prints) — a real, carrier-
side event, not a portal action, so it counts desk work too.
"""

import frappe
from frappe.utils import add_days, now_datetime, nowdate

_CO = "Justyol Morocco"


def _mgr():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("The velocity board is manager-only.", frappe.PermissionError)


@frappe.whitelist()
def board(days=14):
    _mgr()
    days = min(max(int(days or 14), 7), 60)

    # IN = orders created that day that need fulfilment (not cancelled/duplicated).
    din = frappe.db.sql(
        """SELECT DATE(creation) d, COUNT(*) n FROM `tabSales Order`
           WHERE company = %s AND docstatus = 1
             AND custom_sales_status NOT IN ('Cancelled', 'Duplicated')
             AND creation >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
           GROUP BY DATE(creation)""", (_CO, days), as_dict=True)
    # OUT = distinct orders that got a Cathedis label that day, + that day's cycle.
    dout = frappe.db.sql(
        """SELECT DATE(f.creation) d, COUNT(DISTINCT f.attached_to_name) n,
                  ROUND(AVG(TIMESTAMPDIFF(HOUR, so.creation, f.creation))) cyc
           FROM `tabFile` f
           JOIN `tabSales Order` so ON so.name = f.attached_to_name
           WHERE f.attached_to_doctype = 'Sales Order'
             AND f.file_name LIKE '%%Cathedis_Label%%'
             AND f.creation >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
             AND TIMESTAMPDIFF(HOUR, so.creation, f.creation) BETWEEN 0 AND 2000
           GROUP BY DATE(f.creation)""", (days,), as_dict=True)
    inmap = {str(r.d): int(r.n) for r in din}
    outmap = {str(r.d): int(r.n) for r in dout}
    cycmap = {str(r.d): int(r.cyc or 0) for r in dout}

    daily = []
    for i in range(days - 1, -1, -1):
        d = str(add_days(nowdate(), -i))
        i_n, o_n = inmap.get(d, 0), outmap.get(d, 0)
        daily.append({"date": d, "in": i_n, "out": o_n, "net": i_n - o_n,
                      "cycleH": cycmap.get(d, 0)})

    # Backlog now: Confirmed orders not yet labelled (Pending / AWB-ready / picked).
    bk = frappe.db.sql(
        """SELECT COUNT(*) n, ROUND(AVG(TIMESTAMPDIFF(HOUR, creation, NOW()))) age
           FROM `tabSales Order`
           WHERE company = %s AND docstatus = 1 AND custom_sales_status = 'Confirmed'
             AND custom_logistics_status IN ('Pending', 'Label Generated', 'Picked')""",
        _CO, as_dict=True)[0]

    last7 = daily[-7:]
    tin = sum(x["in"] for x in last7)
    tout = sum(x["out"] for x in last7)
    cyc_vals = [x["cycleH"] for x in daily if x["cycleH"] > 0]
    kpis = {
        "in7": tin, "out7": tout,
        "pacePct": round(tout * 100 / tin) if tin else 0,
        "backlog": int(bk.n or 0), "backlogAgeH": int(bk.age or 0),
        "cycleH": round(sum(cyc_vals) / len(cyc_vals)) if cyc_vals else 0,
        "todayIn": daily[-1]["in"], "todayOut": daily[-1]["out"],
    }
    return {"daily": daily, "kpis": kpis, "stuck": _stuck(),
            "serverNow": str(now_datetime())[:19]}


def _stuck():
    """The tails: parcels past the age their stage should take. Each is a
    different owner's fix, so they're separate buckets."""
    def _rows(where, thresh_h, extra_join=""):
        return frappe.db.sql(
            f"""SELECT so.name, so.customer_name customer,
                       ROUND(TIMESTAMPDIFF(HOUR, so.creation, NOW()) / 24) age_d
                FROM `tabSales Order` so {extra_join}
                WHERE so.docstatus = 1 AND so.company = %s
                  AND so.custom_sales_status = 'Confirmed'
                  AND {where}
                  AND TIMESTAMPDIFF(HOUR, so.creation, NOW()) > %s
                GROUP BY so.name ORDER BY so.creation LIMIT 40""",
            (_CO, thresh_h), as_dict=True)

    # Has a submitted DN but no AWB on EITHER the order or the DN, still Pending
    # in logistics — labelling failed (most often an Arabic city). NB the SO's
    # custom_awb is empty on plenty of old shipped orders (the AWB lives on the
    # DN), so both must be empty to be a real stuck-at-label case.
    no_awb = frappe.db.sql(
        """SELECT so.name, so.customer_name customer,
                  ROUND(TIMESTAMPDIFF(HOUR, so.creation, NOW()) / 24) age_d
           FROM `tabSales Order` so
           JOIN `tabDelivery Note Item` dni ON dni.against_sales_order = so.name
           JOIN `tabDelivery Note` dn ON dn.name = dni.parent AND dn.docstatus = 1
           WHERE so.docstatus = 1 AND so.company = %s
             AND so.custom_sales_status = 'Confirmed'
             AND so.custom_logistics_status = 'Pending'
             AND (so.custom_awb IS NULL OR so.custom_awb = '')
             AND (dn.custom_awb IS NULL OR dn.custom_awb = '')
             AND TIMESTAMPDIFF(HOUR, so.creation, NOW()) > 24
           GROUP BY so.name ORDER BY so.creation LIMIT 40""", _CO, as_dict=True)
    # Picked / AWB-ready but never sorted+printed, > 3 days.
    picked = _rows("so.custom_logistics_status IN ('Picked', 'Label Generated')", 24 * 3)
    # Printed/sorted but not handed to the carrier, > 5 days.
    labelled = _rows("so.custom_logistics_status = 'Label Printed'", 24 * 5)

    def pack(rows, key, route):
        return {
            "key": key, "route": route, "n": len(rows),
            "oldestD": max((int(r.age_d or 0) for r in rows), default=0),
            "rows": [{"order": r.name, "customer": r.customer or "",
                      "ageD": int(r.age_d or 0)} for r in rows[:8]],
        }

    return [
        pack(no_awb, "noAwb", "CityCheck"),
        pack(picked, "pickedStale", "PickLists"),
        pack(labelled, "labelledStale", "PackStation"),
    ]
