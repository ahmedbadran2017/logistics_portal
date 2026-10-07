---
name: availability-one-definition
description: "The single availability contract — picking.availability() — and the audited layers underneath it (what subtracts what, and what does NOT double-count)"
metadata:
  type: project
---

**Full audit 2026-09-09 (`bdaba15`).** Every screen that answers "can this be picked?" must call **`picking.availability(item_codes) -> (totals, sre, free)`**. Do not build a sixth variant.

## The layers, in order

`_available_totals(items)` — per **pickable** bin (`warehouses.pickable_condition`), skipping `_ee_rejected()`:
1. `GREATEST(actual_qty - reserved_qty, 0)`
2. **minus the short-shelf qty** for that (item, bin) — see [ready-double-promise](ready-double-promise.md) round 4
3. capped by **`_batch_truth`** (ee's batch-aware answer)
4. minus **open-draft** claims (`docstatus=0`, `qty - picked_qty`), filtered to pickable + non-rejected bins

`availability()` then:
- `ceiling[c] = max(0, totals[c])` — what physically exists
- `shared[c] = ceiling - ALL SREs`, floored
- **`free(order, c) = min(ceiling, shared + own_SRE)`** ← the cap is the whole point

**Sequential spenders** (`_pick_availability`, `pick_candidates`, `_allocate_and_insert`) keep BOTH ledgers: `ceiling` always pays the full qty; `shared` is spared only the part drawn from the order's own reservation.

## What is NOT a bug (verified, do not "fix")

- **No double-count of reservations.** An SRE does **not** set `Bin.reserved_qty` here — all **62** live SRE bins carry 0. So subtracting `reserved_qty` and subtracting SREs are different commitments.
- **`reserved_qty` on pickable bins = 3,532 units, all on `In Transit - JM` with `actual_qty = 0`** (old open-SO reservations). Withholds **0** real availability.

## The bug class that keeps recurring

`shared + own_SRE` **without a cap** invents units whenever `totals` was zeroed for a NON-reservation reason (draft / batch ledger / shelf mark). Measured: **31 of 126** pool orders promised stock that is not there. Five callers had drifted into their own arithmetic.

**Verified after the fix:** board = create gate = confirmation card on all 132 pool orders (9 pickable each; 0 disagreements).

`_resolve_bins` now also applies the batch cap (it did not) — 6 items were being offered bins their batch ledger denies, which is the `picked quantity > available` shatter family in [picklist-batch-shattering](picklist-batch-shattering.md).

## Known, deliberate divergence

The **duplicate-SKU lookups** (`orders.py` `net_sub`, `inventory.py` `bs.net`) answer a different question and use a **hardcoded** warehouse list — a zone toggled in Settings does not reach them.

Related: [ready-double-promise](ready-double-promise.md), [batch-ledger-corruption](batch-ledger-corruption.md), [stale-sre-holds](stale-sre-holds.md), [measure-dont-trust-audits](measure-dont-trust-audits.md).
