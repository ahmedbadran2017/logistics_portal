---
name: stranded-confirmed-orders
description: Confirmed orders with no pick list die silently — the biggest hole found in the portal audit; Stranded queue built to surface them in three buckets
metadata: 
  type: project
---

**The biggest gap the July 2026 audit found — and it is not in the contact
centre.** A confirmed order with no pick list belongs to nobody: it is not on the
confirmation board (it is decided), not on the pick floor (there is no list), and
not in Tracking (there is no parcel). It just ages.

Built `api/stranded.py` + `pages/Stranded.vue` (route `/logistics/stranded`, in
the manager, dispatcher and confirmation navs) to surface them in **three
buckets, because each needs a different person**:

- **ready** — stock is on a pickable shelf; a pick list was simply never made → dispatcher
- **zone** — stock is in Morocco but in a warehouse the pick engine can't pull from → floor moves it
- **nostock** — not in Morocco at all → agent calls the customer or cancels with a reason

Roughly equal thirds on the live data, plus a long dead tail (months old) that
needs closing, not picking. Hence the two windows: recent = the work,
"everything" = cleanup.

**Two things that made the numbers honest:**
1. Classify against `warehouses.pickable_condition()` — the app's own configured
   policy, the same predicate the pick engine allocates against. My first ad-hoc
   regex for "aisle bins" was wrong: real picking happens mostly from
   `PLT - JM` and `Receiving Zone - JM`.
2. Scope to `company = "Justyol Morocco"`. Stock under **Justyol China (JCH)** and
   **Maslak LTD (ML)** is real but unreachable. One headline item looked
   well-stocked at 103 units until that filter went in — 100 of them were in China.

Related: [dn-item-fanout-trap](dn-item-fanout-trap.md), [catalog-hub-project](catalog-hub-project.md), [sku-item-code-duplication](sku-item-code-duplication.md)
