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


def _offset_now():
    """offset_hours() for "now", remembered for the rest of this request.

    Measured 2026-09-13: the tracking board converts five timestamps on each
    of 8,000 rows, and each conversion was resolving two time zones and
    reading a site default — 1.4 of the board's 1.8 shaping seconds. The
    offset cannot change inside one request, so it is computed once.
    """
    import datetime as _d
    cached = getattr(frappe.local, "lp_floor_offset", None)
    if cached is not None:
        return cached
    off = offset_hours()
    try:
        frappe.local.lp_floor_offset = off
    except Exception:
        pass
    return off


def to_floor(dt):
    """A stored timestamp, as the floor reads it on the wall."""
    if not dt:
        return dt
    import datetime as _d
    if not isinstance(dt, _d.datetime):
        from frappe.utils import get_datetime
        dt = get_datetime(dt)
    off = _offset_now()
    return dt + _d.timedelta(hours=off) if off else dt


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


def span(days=30, frm=None, to=None, cap=365):
    """(start, end) STORED timestamps for a window the reader chose.

    The same contract the confirmation board settled on: `days` is a rolling
    default, and an explicit from/to overrides it — a manager reviewing last
    month does not want "the last N days from right now". Either end may be
    given alone.

    Returns stored-clock strings, so callers keep comparing the column
    directly and keep their index.
    """
    import re
    ok = lambda d: bool(d and re.match(r"^\d{4}-\d{2}-\d{2}$", str(d).strip()))
    if ok(frm) or ok(to):
        first = str(frm).strip()[:10] if ok(frm) else None
        last = str(to).strip()[:10] if ok(to) else floor_today()
        if not first:
            # "up to this date" with no start: keep the rolling width, ending
            # where they asked, rather than silently scanning all of history.
            from frappe.utils import add_days
            first = str(add_days(last, -(min(max(int(days or 30), 1), cap) - 1)))[:10]
        if first > last:
            first, last = last, first
        return day_bounds(first)[0], day_bounds(last)[1], first, last
    from frappe.utils import add_days
    n = min(max(int(days or 30), 1), cap)
    last = floor_today()
    first = str(add_days(last, -(n - 1)))[:10]
    return day_bounds(first)[0], day_bounds(last)[1], first, last


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
