"""The carrier's vocabulary, in one place.

Cathedis says everything in comments on the order, in a closed set of
sentences — 30 distinct ones in 45 days, measured 2026-09-22. Three modules
knew those sentences by heart (shipments, rescue, shipping: 24 references),
and each knew a slightly different subset. That is how the lane ended up
reading "The driver has confirmed an appointment" as a reason to work the
parcel again: the classifier that knows better lived in shipments, and the
queue that needed it was matching strings of its own.

So the words live here, once, as data. Python asks `kind_of`; SQL asks
`sql_like_any`. Nothing else should carry a carrier sentence in a literal.

This module imports nothing from the app on purpose: it is a leaf, so both
the clock and the rescue lane can use it without an import cycle between
them.
"""

# First match wins, so the cancellations are tested before the looser
# prefixes that would otherwise swallow them.
EVENT_KINDS = (
    ("cancelled", ("Customer cancelled", "The customer has cancelled",
                   "Cancelled on site", "Cancellation Reason",
                   "Justyol has requested")),
    ("unreachable", ("Customer unreachable",)),
    ("appointment", ("The driver",)),
    ("ofd", ("Out for",)),
    ("hub", ("The parcel", "Shipped to")),
    ("delivered", ("Package",)),
    ("label", ("Newly created",)),
)

# ── What each kind MEANS for a promise we already made ───────────────────
#
# Measured 2026-09-22 over 45 days: 82 of the 108 parcels the team actioned
# came back into the working queue on an event that was not a failure, a
# median of 9 minutes after the agent acted, and 65 of them inside half an
# hour. The commonest culprit was the carrier CONFIRMING the appointment we
# had just asked it for.
#
# The rule that follows from that: only a failure re-opens a decision. The
# carrier agreeing with us is not news the queue should act on.

# The carrier tried again and the customer was not reached. The promise
# broke, so the parcel goes back to a human.
BROKE_THE_PROMISE = ("unreachable",)

# Nothing left to chase — settled one way or the other.
ENDED = ("delivered", "cancelled")

# The carrier is doing what we asked. Never re-opens anything.
PROGRESS = ("appointment", "ofd", "hub", "label")


def kind_of(text):
    """Classify one carrier sentence. Empty string when it says nothing."""
    t = (text or "").strip()
    if not t:
        return ""
    for kind, prefixes in EVENT_KINDS:
        if t.startswith(prefixes):
            return kind
    return "other"


def prefixes_for(kinds):
    """Every sentence-opening that maps to one of these kinds."""
    want = set(kinds or ())
    out = []
    for kind, prefixes in EVENT_KINDS:
        if kind in want:
            out.extend(prefixes)
    return tuple(out)


def sql_like_any(col, kinds, escape=True):
    """SQL predicate: `col` starts like one of these kinds.

    `escape` doubles the % because every query these land in is
    parameterised, and a lone % is read by the driver as a placeholder.
    Returns a predicate that is false rather than NULL-ish when nothing
    matches, so a caller can safely negate it.
    """
    pref = prefixes_for(kinds)
    if not pref:
        return "1 = 0"
    pct = "%%" if escape else "%"
    return "(" + " OR ".join(f"{col} LIKE '{p}{pct}'" for p in pref) + ")"
