---
name: ready-double-promise
description: "The Orders board called an order Ready without spending the stock — same unit promised to every order, and own-SRE added on top of a zeroed pool"
metadata:
  type: project
---

**Found 2026-09-09** from "orders show in Ready to prepare but are out of stock".

`orders._pick_availability` tested each order **independently** against the pool and **never decremented** it:
```python
aq = shared.get(code, 0) + sre.get((so, code), 0)   # pool never spent
if aq >= need: ready
```
Two defects in one line:
1. **No decrement** → the last unit is promised to every order that wants it.
2. **Own SRE added on top of a floored pool** → when `_available_totals` is 0 for a reason unrelated to reservations, `0 + own_sre` invents a unit.

**Measured on the live pool: 81 Ready, 28 unpickable, 9 with NO pickable bin anywhere.**

**Three causes of a zero `_available_totals`, all assumed away by the old comment** ("a genuinely empty item has no reservation to hand back either"):
| cause | example |
|---|---|
| open **draft pick list** holds the piece | `PL-55772` held all 6 units of `45867689246974` |
| **batch ledger** answers 0 for a shelf the Bin says has 2 | `47249811374334`, E5A=2, no drafts, totals=0 (`_batch_truth` cap) |
| stock only in **ee-rejected / non-pickable** warehouses | Yakuplu, CORRECTING SOFT, Return Zone, Container |

**Fix (`bfa42e1`): spend from ONE ceiling** = `max(0, _available_totals[c])`, orders drawing in turn, sorted **own-SRE-holders first, then oldest**. A reservation buys priority, never an extra unit — which preserves the 2026-09-02 fix (47 orders freed whose piece was genuinely reserved on a pickable shelf).

**Replay before shipping: 81 → 53 Ready; 28 removed; 0 newly added; 0 of the new Ready set lack a pickable bin (was 9).**

`some` (the OOS-vs-Partial split) still reads the **item's own** availability, not the contended remainder — otherwise "nothing in stock" would change because another order was served first. Contention-only blocks land in **Partial**; the false-OOS panel already labels them "held by a draft".

**Rule:** any screen that answers "can this be picked?" must spend from the same pool `_allocate_and_insert` spends from, in the same order. Independent per-order tests over a shared pool always over-promise.

## Draft radar (`9cc8ea8`)

`picking.draft_radar()` + `snapshot_draft_holds()` (daily cron), panel on **BatchRepair.vue**.

**Measured draft lifetimes** (751 lists/14d, from the **Version row flipping docstatus 0→1** — a Pick List's `modified` keeps moving after submit, so it answers a different question): p50 **67 min**, p75 3.3h, p90 **17.6h**, p99 48h. Longer than 12h = 1 in 8 (normal overnight); longer than **24h = 1 in 27** → `_DRAFT_WATCH_H=12`, `_DRAFT_STALE_H=24`.

**Age, NOT idleness.** `scan_pick` writes `picked_qty` with a raw `UPDATE` and never touches the parent's `modified` — an "idle" column on that field is fiction. Use age + `picked_qty > 0` (started vs never started; only never-started is safe to release).

**Value = sum over DISTINCT orders per list** (the [dn-item-fanout-trap](dn-item-fanout-trap.md) again). Cross-check: 20,296 per-list vs 20,139 distinct — gap = orders sitting on >1 draft.

Baseline 2026-09-09: 21 drafts, 127 units, 98 orders, 20,296 MAD, **0 stale**.

## Round 2 (`9e7bf12`) — the board asked a different question than the button

Creating a pick list from the 40 orders the board called Ready produced a list of **2**; the other **38** were skipped with `short-picked recently (shelf empty)`.

`_pick_availability` decided Ready from **stock alone**. `_pick_gate` (what the create runs) checks four more things; three are already in the board's SQL (submitted, Confirmed+Pending, not on a pick list). The fourth was never asked: **`custom_short_picked_at` + `settings.get_ops("shortPickCooldownH")` (=24h)**.

Fix: a **`cooling` bucket** with its own chip — NOT folded into OOS (different remedy, and it clears itself). Only an order that would otherwise be *ready* moves there; partial/oos keep their class. Verified: 40 → 2 ready + 38 cooling, and the create gate refuses **0** of the new ready set.

**Operational, not a bug:** 91 orders were short-picked in ONE day (204 flagged total), each a separate action by a named picker on a distinct item — verified from the per-order comments. At that volume a 24h cooldown swallows most of the pick pool. Whether 24h is right is Ahmed's call; the chip now makes the cost visible.

**Rule (generalised):** any screen that says "can this be picked?" must run the SAME gate the create runs, not a subset. Stock is only one of the four conditions.

**How to reproduce a create failure safely:** call `picking.create_pick_list_from_orders(...)` on prod then `frappe.db.rollback()` — no commit inside `_build_pick_list`. A pure read-only replay of the gate logic will NOT reproduce it, because `_build_pick_list` applies `_pick_gate` per order before `_allocate_and_insert` ever runs.

## Round 3 (`127fdcd`) — the mark belonged on the SHELF, not the order

The 24h cool-down was on the **order** (`custom_short_picked_at`), and the item went into **comment text** (unqueryable). Measured in one day: **195 reports / 116 items, one item reported 12×, another 8×** — every repeat is a picker walking to the same empty shelf, because only *already-reported orders* were held, never the next order carrying that item. And **62 of 116** items still showed pickable stock in Bin.

So it punished orders, and did not stop the wasted walk or fix the lying count.

**New model — `api/short_shelf.py`:** the mark is `(item_code, warehouse)` in a site default `lp_short_shelf` (pruned on write, 60s cache), subtracted inside **`_available_totals` AND `_resolve_bins`**. One report suppresses that bin for everyone; stock of the same item in another bin is untouched; the order is never punished.

- `report_short_pick` marks the bin from the order's own pick-list rows (that IS where the picker stood).
- **`Stock Reconciliation.on_submit` → `clear()`**: a counted shelf is a stronger observation and replaces the glance rather than queuing behind it.
- The `_pick_gate` cool-down and the `cooling` bucket/chip (both added hours earlier) were **removed** — with the mark in the right place an order lands in Partial/OOS by ordinary arithmetic, with the blocking item named.
- `short_shelf.count_worklist()` → panel on **CycleCount.vue**: the lying bins, ranked by waiting orders.

Verified on prod: 29 marks held, every currently-ready order survives the subtraction, 0 create-gate refusals.

**Round 4 (`e34e03c`) — the shelf mark must carry a QUANTITY.** Round 3 treated one report as "bin empty". True on a pick face holding 1–2 pieces; nonsense in **staging** (`PLT`, `Receiving Zone`): a picker missing one piece hid all **223** units and told J-005384 (1 order, 1 unit) "out of stock". Of 68 live marks, **5 sat on bins ≥20 units and hid 830**. Now `mark(item, wh, qty)` subtracts the qty sought (repeats accumulate); legacy bare-timestamp rows read as 1. `active()` returns `{(item,wh): qty}`; `_available_totals` and `_resolve_bins` subtract instead of skipping. Replayed: **883 units returned across 67 items**, J-005384's item 0 → 222.

**Principle:** record evidence against the object it is evidence about — *and at the magnitude it actually supports.* An order-level flag for a shelf-level fact is both too broad (punishes one order for 24h) and too narrow (lets every other order repeat the walk).

Related: [batch-ledger-corruption](batch-ledger-corruption.md), [stale-sre-holds](stale-sre-holds.md), [picklist-batch-shattering](picklist-batch-shattering.md), [measure-dont-trust-audits](measure-dont-trust-audits.md).
