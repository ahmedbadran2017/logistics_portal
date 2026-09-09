"""The floor's clock.

Frappe stores naive datetimes in the SITE's timezone, and this site is set to
`Europe/Istanbul` — the parent's clock. The warehouse and the contact centre
are in Morocco. Measured 2026-09-09: `now_datetime()` read 22:32 while the
wall clock in Casablanca said 20:32, so every stored timestamp is two hours
ahead of the time the people using this portal actually live in.

That is not a cosmetic problem. It made a first pass at "how much work happens
after 6pm" read 31%; in Moroccan hours the answer is 7.0% — the opposite
conclusion, from the same rows.

What this module does NOT do is change `System Settings.time_zone`. Frappe
stores naive local datetimes, so flipping that setting would silently
re-interpret every timestamp already in the database: eight years of history
would move two hours and nothing would say so. The site keeps its clock; the
portal translates at the edges.

The offset is COMPUTED, never written down. Morocco is UTC+1 but drops to
UTC+0 for Ramadan every year, and a hardcoded "-2" would be quietly wrong for
a month each spring — exactly the kind of constant that is right when it is
written and wrong when it matters.
"""

import frappe

_BUSINESS_TZ = "Africa/Casablanca"
_SETTING = "lp_business_tz"


def business_tz():
    """Overridable per site, so this file is not the place a move is recorded."""
    return (frappe.db.get_default(_SETTING) or _BUSINESS_TZ).strip()


def offset_hours(at=None):
    """Hours to ADD to a stored timestamp to get the floor's wall clock.

    Resolved against both zones at the given instant, so a DST or Ramadan
    shift on either side is handled by the timezone database rather than by
    someone remembering to edit a number. Returns 0.0 — a no-op — if the two
    zones agree or if anything at all goes wrong: a clock that cannot be
    resolved must not take the portal down with it.
    """
    try:
        from zoneinfo import ZoneInfo
        from frappe.utils import get_system_timezone, now_datetime
        site = ZoneInfo(get_system_timezone())
        floor = ZoneInfo(business_tz())
        at = (at or now_datetime()).replace(tzinfo=None)
        return round((at.replace(tzinfo=floor).utcoffset()
                      - at.replace(tzinfo=site).utcoffset()).total_seconds() / 3600.0, 2)
    except Exception:
        return 0.0


def to_floor(dt):
    """A stored timestamp, as the floor reads it on the wall."""
    if not dt:
        return dt
    from frappe.utils import add_to_date, get_datetime
    off = offset_hours()
    return add_to_date(get_datetime(dt), hours=off) if off else get_datetime(dt)


def floor_now():
    from frappe.utils import now_datetime
    return to_floor(now_datetime())


def floor_today():
    """Today, on the floor's calendar — which is what "my day so far" means."""
    return str(floor_now())[:10]


def day_bounds(day):
    """The STORED half-open range covering one of the floor's days.

    Shifts the boundaries rather than the column: `creation >= a AND
    creation < b` still uses an index, while `DATE(creation - INTERVAL 2 HOUR)
    = x` would scan. That matters — the confirmation lane's speed came from
    those indexes.
    """
    from frappe.utils import add_to_date, get_datetime
    off = offset_hours()
    start = add_to_date(get_datetime(str(day)[:10] + " 00:00:00"), hours=-off)
    return str(start)[:19], str(add_to_date(start, days=1))[:19]


def sql_local(col):
    """The expression to GROUP BY when bucketing rows into the floor's days.

    Only ever for a SELECT/GROUP BY — never a WHERE, where it would cost the
    index. Pair it with day_bounds() on the WHERE side.
    """
    off = offset_hours()
    if not off:
        return f"DATE({col})"
    return f"DATE(DATE_ADD({col}, INTERVAL {int(off * 60)} MINUTE))"


@frappe.whitelist()
def info():
    """What clock is this portal on? Read by the UI so a wrong one is visible
    rather than merely wrong."""
    from frappe.utils import get_system_timezone
    return {"stored": get_system_timezone(), "floor": business_tz(),
            "offsetH": offset_hours(), "floorNow": str(floor_now())[:19]}
