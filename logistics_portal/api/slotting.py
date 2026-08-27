"""Slotting analysis (Phase 1, read-only) — where the fast movers actually are.

Classifies every picked SKU by velocity (ABC over a rolling window from real Pick
List demand), maps it to where it currently sits, and scores how scattered the
work is. The headline it surfaces: a small A-class of SKUs drives ~80% of all
picking, and if those are spread across many zones the floor walks the whole
warehouse for the bulk of the day.

Nothing here moves stock — it's the evidence layer. Phase 2 (the fast-zone plan +
move worklist) and Phase 3 (pick-path order) build on it, and need the physical
layout (which zone is nearest packing) that only a human can supply.
"""

import json

import frappe

_ROLES = ("manager", "dispatcher")

# A real, stocked shelf bin (zone-letter + number, JM). Same universe as the
# shelf-label / pick tools.
_SH = "b.warehouse REGEXP '^[A-Z][0-9]{1,2}[A-Z]?[.]? - JM'"
_SH_PLI = "pli.warehouse REGEXP '^[A-Z][0-9]{1,2}[A-Z]?[.]? - JM'"


def _gate():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) not in _ROLES:
        frappe.throw("Not authorized for slotting analysis.", frappe.PermissionError)


def _velocity(days):
    """item_code -> pick-line count over the window (real demand at the shelf)."""
    rows = frappe.db.sql(
        """SELECT pli.item_code ic, COUNT(*) picks
           FROM `tabPick List Item` pli JOIN `tabPick List` pl ON pl.name = pli.parent
           WHERE pl.creation >= DATE_SUB(NOW(), INTERVAL %s DAY) AND pl.docstatus < 2
           GROUP BY pli.item_code""", int(days), as_dict=True)
    return {r.ic: int(r.picks) for r in rows}


def _placement():
    """item_code -> (primary shelf, qty). Primary = the shelf holding the most,
    for the ~4% of SKUs split across two shelves."""
    rows = frappe.db.sql(
        f"""SELECT item_code ic, warehouse wh, actual_qty q
            FROM `tabBin` b WHERE {_SH} AND actual_qty > 0""", as_dict=True)
    best = {}
    for r in rows:
        q = float(r.q or 0)
        if r.ic not in best or q > best[r.ic][1]:
            best[r.ic] = (r.wh, q)
    return best


def _abc(pmap):
    """item_code -> 'A'/'B'/'C' by cumulative pick share (80/15/5)."""
    total = sum(pmap.values()) or 1
    cls, cum = {}, 0
    for ic, p in sorted(pmap.items(), key=lambda x: -x[1]):
        cum += p
        cls[ic] = "A" if cum <= 0.8 * total else ("B" if cum <= 0.95 * total else "C")
    return cls, total


@frappe.whitelist()
def overview(days=90):
    """The scorecard + class table + zone heat table. Cached an hour (heavy)."""
    _gate()
    days = min(max(int(days or 90), 7), 365)
    ck = f"lp_slotting_ov_{days}"
    hit = frappe.cache().get_value(ck)
    if hit:
        try:
            return json.loads(hit)
        except Exception:
            pass

    pmap = _velocity(days)
    place = _placement()
    cls, total = _abc(pmap)

    def zof(wh):
        return (wh or " ")[0]

    zones = {}
    for ic, (wh, q) in place.items():
        z = zof(wh)
        r = zones.setdefault(z, {"skus": 0, "units": 0.0, "picks": 0,
                                 "A": 0, "B": 0, "C": 0, "cold": 0, "_sh": set()})
        r["skus"] += 1
        r["units"] += q
        r["_sh"].add(wh)
        r["picks"] += pmap.get(ic, 0)
        c = cls.get(ic)
        if c:
            r[c] += 1
        else:
            r["cold"] += 1  # stocked but not picked in the window

    ztab = sorted(
        [{"zone": z, "shelves": len(r["_sh"]), "skus": r["skus"],
          "units": round(r["units"]), "picks": r["picks"],
          "A": r["A"], "B": r["B"], "C": r["C"], "cold": r["cold"]}
         for z, r in zones.items()],
        key=lambda x: -x["picks"])

    cnt = {"A": 0, "B": 0, "C": 0}
    share = {"A": 0, "B": 0, "C": 0}
    for ic, c in cls.items():
        cnt[c] += 1
        share[c] += pmap.get(ic, 0)

    a_stock = [ic for ic in cls if cls[ic] == "A" and ic in place]
    a_zones = len({zof(place[ic][0]) for ic in a_stock})
    cold = [ic for ic in place if ic not in pmap]

    pp = frappe.db.sql(
        f"""SELECT AVG(zc) FROM (
              SELECT pl.name, COUNT(DISTINCT LEFT(pli.warehouse, 1)) zc
              FROM `tabPick List Item` pli JOIN `tabPick List` pl ON pl.name = pli.parent
              WHERE pl.creation >= DATE_SUB(NOW(), INTERVAL %s DAY) AND pl.docstatus < 2
                AND {_SH_PLI}
              GROUP BY pl.name) t""", days)[0][0]

    out = {
        "days": days, "totalPicks": total, "pickedSkus": len(pmap),
        "zonesTotal": len(zones),
        "classes": [{"cls": c, "skus": cnt[c],
                     "pickShare": round(100 * share[c] / total, 1)} for c in ("A", "B", "C")],
        "zones": ztab,
        "scorecard": {
            "aMovers": cnt["A"], "aStocked": len(a_stock), "aZones": a_zones,
            "coldItems": len(cold),
            "coldUnits": round(sum(place[ic][1] for ic in cold)),
            "coldShelves": len({place[ic][0] for ic in cold}),
            "pickPathZones": round(float(pp or 0), 2),
        },
    }
    frappe.cache().set_value(ck, json.dumps(out), expires_in_sec=3600)
    return out


@frappe.whitelist()
def movers(cls="A", q="", limit=60, offset=0, days=90):
    """Drill-down: the SKUs of one velocity class, with their pick count and where
    they sit now. This is what a re-slot decision reads."""
    _gate()
    days = min(max(int(days or 90), 7), 365)
    cls = (cls or "A").upper()
    if cls not in ("A", "B", "C"):
        frappe.throw("Unknown class.")
    limit = min(max(int(limit or 60), 1), 200)
    offset = max(int(offset or 0), 0)

    pmap = _velocity(days)
    place = _placement()
    classmap, _ = _abc(pmap)

    items = [ic for ic in sorted(pmap, key=lambda x: -pmap[x]) if classmap.get(ic) == cls]

    q = (q or "").strip().lower()
    meta = {}
    if items:
        ph = ",".join(["%s"] * len(items))
        for r in frappe.db.sql(
                f"""SELECT name, custom_sku, item_name, image FROM `tabItem`
                    WHERE name IN ({ph})""", tuple(items), as_dict=True):
            meta[r.name] = r

    rows = []
    for ic in items:
        m = meta.get(ic) or {}
        sku = (m.get("custom_sku") or "").strip()
        name = m.get("item_name") or ic
        if q and q not in sku.lower() and q not in name.lower() and q not in ic.lower():
            continue
        wh, qty = place.get(ic, ("", 0))
        rows.append({
            "itemCode": ic, "sku": sku, "name": name, "image": m.get("image") or "",
            "picks": pmap.get(ic, 0),
            "shelf": (wh or "").replace(" - JM", ""), "zone": (wh or "?")[0] if wh else "—",
            "stock": int(qty), "placed": bool(wh),
        })
    total = len(rows)
    return {"cls": cls, "total": total, "rows": rows[offset:offset + limit]}


# ---------------------------------------------------------------------------
# Phase 2 — the target layout. Roles are FIXED by design (2026-08-27, sized on
# real capacity + velocity; the floor re-arranges to match this, not vice
# versa):
#   E+G  (65 bins)  = FAST WALL, the 322 A-movers (80% of picks) — E and G were
#                     already the two hottest aisles and held 83 A-movers, so
#                     this role costs the fewest moves.
#   H+J+F (127 bins) = B zone (15% of picks).
#   A+B+C+D+I (164)  = C zone, the long tail.
#   X                = reserved (exchanges/special — untouched by the plan).
#   AG-/BAB- racks   = overstock reserve feeding the fast wall; SLOW ZONE =
#                      cold storage. Neither is a pick face in this plan.
ZONE_ROLES = {"A": ("E", "G"), "B": ("H", "J", "F"), "C": ("A", "B", "C", "D", "I")}
_ROLE_OF = {}
for _cls, _letters in ZONE_ROLES.items():
    for _l in _letters:
        _ROLE_OF[_l] = _cls


def _letter_load():
    """letter -> (bins, distinct stocked SKUs) for capacity-aware suggestions."""
    bins = {}
    for r in frappe.db.sql(
            "SELECT name FROM `tabWarehouse` WHERE is_group=0 AND disabled=0 "
            "AND name REGEXP '^[A-Z][0-9]{1,2}[A-Z]?[.]? - JM'"):
        bins[r[0][0]] = bins.get(r[0][0], 0) + 1
    skus = dict(frappe.db.sql(
        f"""SELECT LEFT(b.warehouse,1), COUNT(DISTINCT b.item_code)
            FROM `tabBin` b WHERE {_SH} AND b.actual_qty > 0
            GROUP BY LEFT(b.warehouse,1)"""))
    return {L: (bins.get(L, 0), int(skus.get(L, 0))) for L in bins}


@frappe.whitelist()
def target_plan(days=90):
    """The Phase-2 blueprint: per-zone role, capacity, and compliance — how much
    of each class already sits inside its target letters. Cached 10 minutes."""
    _gate()
    days = min(max(int(days or 90), 7), 365)
    ck = f"lp_slotting_plan_{days}"
    hit = frappe.cache().get_value(ck)
    if hit:
        try:
            return json.loads(hit)
        except Exception:
            pass

    pmap = _velocity(days)
    place = _placement()
    cls, _total = _abc(pmap)
    load = _letter_load()

    zones = []
    for c in ("A", "B", "C"):
        letters = ZONE_ROLES[c]
        zones.append({
            "cls": c, "letters": list(letters),
            "bins": sum(load.get(L, (0, 0))[0] for L in letters),
            "skusNow": sum(load.get(L, (0, 0))[1] for L in letters),
        })

    comp = {c: {"inPlace": 0, "toMove": 0, "unitsToMove": 0} for c in ("A", "B", "C")}
    for ic, c in cls.items():
        if ic not in place:
            continue
        wh, qty = place[ic]
        if wh[0] in ZONE_ROLES[c]:
            comp[c]["inPlace"] += 1
        else:
            comp[c]["toMove"] += 1
            comp[c]["unitsToMove"] += int(qty)

    out = {
        "days": days, "zones": zones,
        "reserved": {"X": load.get("X", (0, 0))[0]},
        "compliance": [{"cls": c, **comp[c]} for c in ("A", "B", "C")],
    }
    frappe.cache().set_value(ck, json.dumps(out), expires_in_sec=600)
    return out


@frappe.whitelist()
def move_list(cls="A", limit=40, offset=0, days=90):
    """The physical worklist: SKUs of one class sitting OUTSIDE their target
    letters, hottest first, each with a suggested target letter (the least
    crowded letter of the class, by SKUs per bin). The floor executes each row
    with Move Stock, which records the real transfer."""
    _gate()
    days = min(max(int(days or 90), 7), 365)
    cls = (cls or "A").upper()
    if cls not in ("A", "B", "C"):
        frappe.throw("Unknown class.")
    limit = min(max(int(limit or 40), 1), 200)
    offset = max(int(offset or 0), 0)

    pmap = _velocity(days)
    place = _placement()
    classmap, _ = _abc(pmap)
    load = _letter_load()
    letters = ZONE_ROLES[cls]

    # Track the running fill so consecutive suggestions spread, not pile up.
    fill = {L: (load.get(L, (1, 0))[1] / max(load.get(L, (1, 0))[0], 1)) for L in letters}

    wrong = []
    for ic in sorted(pmap, key=lambda x: -pmap[x]):
        if classmap.get(ic) != cls or ic not in place:
            continue
        wh, qty = place[ic]
        if wh[0] in letters:
            continue
        wrong.append((ic, wh, qty))
    total = len(wrong)
    page = wrong[offset:offset + limit]

    meta = {}
    if page:
        ph = ",".join(["%s"] * len(page))
        for r in frappe.db.sql(
                f"""SELECT name, custom_sku, item_name, image FROM `tabItem`
                    WHERE name IN ({ph})""",
                tuple(ic for ic, _w, _q in page), as_dict=True):
            meta[r.name] = r

    rows = []
    for ic, wh, qty in page:
        target = min(fill, key=lambda L: fill[L])
        fill[target] += 1.0 / max(load.get(target, (1, 0))[0], 1)
        m = meta.get(ic) or {}
        rows.append({
            "itemCode": ic, "sku": (m.get("custom_sku") or "").strip(),
            "name": m.get("item_name") or ic, "image": m.get("image") or "",
            "picks": pmap.get(ic, 0), "qty": int(qty),
            "from": (wh or "").replace(" - JM", ""), "target": target,
        })
    return {"cls": cls, "total": total, "rows": rows}
