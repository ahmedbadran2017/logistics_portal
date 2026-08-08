"""Operations settings — every tunable the portal used to hardcode, in one
manager-controlled place. Consumers call get_ops("key"); the Settings page
reads/writes the whole dict.

Keys:
  cutoff             manifest / carrier hand-off cutoff (HH:MM) — drives the
                     Manifest countdown, the floor-board countdown, the orders
                     board's "today's cycle" boundary and the cockpit cutoff%
  floorStart         hour the floor day starts (rate denominators, charts)
  floorEnd           last hour shown on the intake chart
  dayTarget          per-person orders SHIPPED per DAY — the picker scorecard
                     and the team leaderboard measure each person against this.
                     Stored in lp_day_target.
  hourlyStandard     per-person orders/HOUR — the floor board's live pace bar.
                     Kept separate from dayTarget because one is a daily
                     scorecard number and the other an hourly pace signal; a
                     single knob can't be both. Stored in lp_floor_target
                     (legacy key name — its value is now the hourly standard).
  lowThreshold       units at/below which a SKU counts as low stock
  shortPickCooldownH hours an order stays off the pick pool after a short-pick
  slaDays            delivery promise in days (SLA engine fallback when the
                     Logistics SLA Settings single isn't set)
"""

import json

import frappe

DEFAULTS = {
    "cutoff": "14:00",
    "floorStart": 8,
    "floorEnd": 20,
    "dayTarget": 320,       # orders shipped per person per DAY (scorecard)
    "hourlyStandard": 40,   # orders per person per HOUR (floor pace)
    "lowThreshold": 10,
    "shortPickCooldownH": 24,
    "slaDays": 3,
}
_KEY = "lp_ops_settings"


def get_ops(key=None):
    """The effective ops settings (defaults ⊕ saved overrides)."""
    conf = dict(DEFAULTS)
    raw = frappe.db.get_default(_KEY)
    if raw:
        try:
            saved = json.loads(raw)
            if isinstance(saved, dict):
                conf.update({k: saved[k] for k in DEFAULTS if k in saved})
        except Exception:
            pass
    # dayTarget (daily scorecard) and hourlyStandard (floor pace) live in their
    # own defaults, NOT the ops JSON — sourced here with the hard-coded DEFAULTS
    # as fallback so a stale copy in the JSON blob can never poison them. The Team
    # page + set_floor_target write lp_day_target; lp_floor_target keeps its
    # legacy name but now holds the hourly standard.
    conf["dayTarget"] = int(frappe.db.get_default("lp_day_target") or DEFAULTS["dayTarget"])
    conf["hourlyStandard"] = int(frappe.db.get_default("lp_floor_target") or DEFAULTS["hourlyStandard"])
    return conf.get(key) if key else conf


def _require_manager():
    from logistics_portal.api.auth import resolve_role
    if resolve_role(frappe.session.user) != "manager":
        frappe.throw("Only a manager can change operations settings.",
                     frappe.PermissionError)


@frappe.whitelist()
def ops_settings():
    _require_manager()
    return get_ops()


@frappe.whitelist()
def save_ops_settings(settings=None):
    """Validate + persist. Every value is range-checked — a typo'd cutoff must
    not quietly break the manifest countdown portal-wide."""
    import re

    _require_manager()
    if isinstance(settings, str):
        settings = json.loads(settings)
    s = settings or {}

    out = get_ops()
    if "cutoff" in s:
        v = str(s["cutoff"]).strip()
        if not re.match(r"^([01]?\d|2[0-3]):[0-5]\d$", v):
            frappe.throw("Cutoff must be HH:MM (e.g. 14:00).")
        out["cutoff"] = f"{int(v.split(':')[0]):02d}:{v.split(':')[1]}"
    for key, lo, hi in (("floorStart", 0, 23), ("floorEnd", 1, 23),
                        ("lowThreshold", 0, 1000), ("shortPickCooldownH", 0, 168),
                        ("slaDays", 1, 30), ("dayTarget", 1, 2000),
                        ("hourlyStandard", 1, 200)):
        if key in s:
            try:
                v = int(s[key])
            except Exception:
                frappe.throw(f"{key} must be a number.")
            if not (lo <= v <= hi):
                frappe.throw(f"{key} must be between {lo} and {hi}.")
            out[key] = v
    if out["floorEnd"] <= out["floorStart"]:
        frappe.throw("Floor end must be after floor start.")

    # The two scorecard knobs persist to their own keys; everything else rides
    # in the ops JSON. dayTarget/hourlyStandard are deliberately EXCLUDED from
    # the JSON so a stale copy can't shadow the dedicated storage on read.
    frappe.db.set_default("lp_day_target", out["dayTarget"])
    frappe.db.set_default("lp_floor_target", out["hourlyStandard"])
    frappe.db.set_default(_KEY, json.dumps(
        {k: out[k] for k in DEFAULTS if k not in ("dayTarget", "hourlyStandard")}))
    # These caches bake in cutoff/threshold-derived numbers.
    for k in ("lp_board_summary", "lp_pick_avail", "lp_consolidation",
              "lp_problem_radar", "lp_leaderboard"):
        frappe.cache().delete_value(k)
    return get_ops()
