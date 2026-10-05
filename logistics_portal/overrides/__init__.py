# Importing any override applies the Cathedis prepaid-amount patch first: the
# pick-list job that creates AWBs loads the Pick List override before it calls
# Cathedis (see overrides/cathedis.py).
from logistics_portal.overrides import cathedis  # noqa: F401
