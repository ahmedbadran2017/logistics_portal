---
name: picked-qty-vs-scanned-qty
description: "ERPNext validates picked_qty on Pick List submit (gated on scan_mode, default 1) — custom_scanned_qty alone is invisible to it"
metadata: 
  type: project
---

**`picked_qty` is the field that matters on a Pick List.** ERPNext's
`before_submit` → `validate_picked_items` throws:

> Row {n} picked quantity is less than the required quantity, additional {x} {uom} required.

whenever **`scan_mode`** is on **and** `picked_qty < stock_qty`. On this site
`scan_mode`'s field default is **`1`**, so **every** pick list has it.

The portal's `scan_pick` used to write only `custom_scanned_qty`, never
`picked_qty` — so the board showed a full 1/1 and submit was refused. Fixed
2026-07-16: `scan_pick` bumps both in one atomic UPDATE, and
`submit_pick_list` reconciles picked_qty from the scan counter (then
**`pl.reload()`** — `submit()` rewrites child rows from the in-memory doc, so
raw SQL before it is silently discarded without a reload).

**Why it hid for months:** the pickers submitted from the **ERPNext desk**,
whose form fills `picked_qty` for them. On submitted rows `picked_qty ==
stock_qty` exactly (2,892/2,892, zero over/under) — an automatic fill, not
human entry. The portal path was broken from the day it was written and only
surfaced once the PDA scanning fix let someone work a list end to end.

**Gotchas:**
- `picked_qty` is in **stock UOM** — compare against `stock_qty`
  (= `qty × conversion_factor`), not `qty`. Every row here has factor 1, but
  incrementing by `conversion_factor` keeps it honest if that changes.
- `scan_pick` writes via **raw SQL**, so `modified` doesn't move and the
  `on_update` hook (`sync_pick_progress`) never fires. If `modified ==
  creation` on a Pick List, nothing ever saved the document.
- `report_short_pick` removes a whole order's lines, so what remains at submit
  is fully picked by construction — the scan_mode gate never fights it.

Related: [zebra-pda-wedge-no-key-events](zebra-pda-wedge-no-key-events.md), [desk-elimination-progress](desk-elimination-progress.md), [measure-dont-trust-audits](measure-dont-trust-audits.md)

**SRE ≠ Bin.reserved_qty (found 2026-08-26, `93260fb`):** Stock Reservation Entries lock stock to a specific SO but leave `Bin.reserved_qty` at 0 — 243 (item,wh) pairs on prod shelves held an active SRE the bin didn't show (238 items / 298 units). So `actual − Bin.reserved_qty` OVERSTATES free stock for those; ERPNext's `set_item_locations` honours SREs and throws "N units of Item X is not available in any of the warehouses" at pick-list save → the whole Create-list batch 417'd. Fix: `picking._sre_by_order` + SRE-aware coverage in `_allocate_and_insert` — subtract ALL active SREs from the shared pool, hand each order back its OWN reservation (voucher_no = SO); reserved-away orders SKIP with a reason, reservation-backed orders still pick. Board availability deliberately untouched (per [measure-dont-trust-audits](measure-dont-trust-audits.md) — do not change the board formula).

**ee rejected-warehouses ≠ portal pickable policy (found 2026-08-26, `8cc02e2`):** ee's `get_rejected_warehouses()` (SLOW ZONE, STOCK ZONE, old-site AG-*/BAB-* shelves...) is a warehouse universe the portal's `pickable_condition` does NOT exclude. Poison-draft mechanism (PL-54830): create passes validate with all rows → `before_save`'s `set_item_locations` strips the row whose only stock is in an ee-rejected wh (SLOW ZONE, 1,980u) → draft saves PARTIALLY covering its SO with no re-validate → scans to 100% but submit's `remove_incomplete_orders` empties it ("Cannot save an empty Pick List"). Fix: `picking._ee_rejected()` excluded in `_resolve_bins` + `_available_totals` (create-time only), plus a post-insert full-coverage guard in `_insert_one` that drops partially-stripped orders. 15 items had their only "pickable" stock in the mismatch set. Board availability still counts SLOW ZONE (deliberate — board formula untouched); the real cure for those items is SLOW→shelf replenish via MoveStock.

**Poison-draft radar (2026-08-26, `15a7b61`):** `audit.problem_radar` gained a critical `poisonDrafts` check — set-based query counting open-draft (PL, SO) pairs where the PL's rows don't fully cover the SO's pending items (the "Cannot save an empty Pick List" class). Rides the 10-min rule engine → Audit page + manager notifications. Verified 8/8 against the known poisoned drafts. Third stripping variant found on #255967/PL-54829: item 47539725893886 is BATCHED and its batch (5D28FAE) ledger sits at GLP-MU China, so ee's batch-aware availability = [] in JM even though Bin E1B shows 2 — batch-data inconsistency class, cure = batch correction, not replenish.

**Batch-truth cap (2026-08-26, `910eb22`) — the variant that emptied whole creates:** batch-tracked items can show Bin shelf stock while the batch ledger puts the batch elsewhere (boots 47249811374334: Bin 5 @ E5A + 5 SREs, ee batch-aware = []). By 15:00 the to-pick pool's remnant was ~all batch-blocked → combined AND per-order inserts all threw → Create list 417'd with ee's raw message (fell_back logs, zero PLs). Fix: `picking._batch_truth()` — for has_batch_no/has_serial_no items call **ee's own `get_available_item_locations`** (safe with required_qty=1e6, verified) and CAP `_available_totals` by it; per-item cache 600s (75% of pool is batch-tracked: 520/696). Availability-mismatch classes now covered at create: (1) ee-rejected warehouses, (2) SRE-vs-Bin, (3) batch-ledger-elsewhere. UI note: toasts show sm[0] = ee's FIRST logged message even when our wrapped throw ends the request (message_log pollution) — don't be misled by raw messages in toasts.
