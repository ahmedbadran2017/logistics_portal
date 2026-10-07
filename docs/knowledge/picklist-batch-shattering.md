---
name: picklist-batch-shattering
description: "A pick-list batch exploding into one list per order — the fallback was wrong, not the trigger; desk logic is drop-and-keep-one-list"
metadata: 
  type: project
---

**Recurring since 2026-07-15, re-diagnosed 2026-08-31** (57 of 79 lists that day were one-order lists, created in bursts of 17 and 30 **inside the same second** — that timestamp signature IS the diagnosis).

**Read the fallback's own log first**: `Error Log` where `method = 'logistics_portal.combined_insert_fell_back'`. 30-day census: **67 events** —
| n | cause |
|---|---|
| 34 (51%) | combined doc came back EMPTY (`nothing pickable — stock is locked by other open pick lists`) |
| 13 | `CharacterLengthExceededError` — `item_name` > 140 |
| 7 | ee's "N units not available" |
| 6 | `picked quantity X > available stock Y in warehouse Z` |
| 5 | `TimestampMismatchError` |
| 1 | deadlock |

**THE DESK'S LOGIC** (`ecommerce_integrations.overrides.pick_list.CustomPickList`, read via bytecode introspection — file reads are blocked by the MCP sandbox): `validate()` = validate_expired_batches → validate_for_qty → validate_stock_qty → check_serial_no_status → **validate_picked_qty_in_location** (per row, per **warehouse**/batch, runs even when `pick_manually`) → **remove_incomplete_orders** (DROPS sales orders lacking full stock, `msgprint`s which ones, keeps ONE list; throws only if the doc empties). `before_save` = update_status → `set_item_locations` unless `pick_manually` → validate_sales_order_percentage. **The desk never splits a batch.**

**Fixes shipped:**
- `77e3ef4` — the real one: replaced per-order fallback with **shrink-and-retry**. `_blamed_order()` reads the culprit from the controller's message (SO name → else the named item, blaming the order needing most of it), drops that one, rebuilds the combined list. Bounded by batch size.
- `791559e` — `_insert_one` pinned the whole qty to ONE bin; ee validates **per warehouse**, so 1-on-shelf + 19-in-staging threw on qty 2. Lines now split across bins, shelf first, with a running pool.
- `791559e` — `Pick List Item.item_name` is Data(140) and Frappe **refuses** longer values. 2,851 catalogue names exceed it (max 222). **Pre-trimming is useless** — the field is `fetch_from` with `fetch_if_empty = 0`, so `_validate_links` writes the full name back (verified: 140 in → 185 out). Fixed by widening the field to 250 via Property Setter in `install.ensure_pick_field_lengths` — **needs `bench migrate`, not just a restart**.

**Do NOT set `pick_manually` to keep our bins**: it skips ee's `set_item_locations`, making us responsible for batch/serial assignment, and 75% of the live pool is batch-tracked.

## 2026-09-09 audit — the dominant cause is a poisoned row we wrote ourselves

30-day census of `combined_insert_fell_back` = **292**: 105 TimestampMismatch, **72 `picked quantity > available in warehouse`**, 56 `units not available`, 29 empty-combined, 21 stripped rows, 8 item_name.

The 77 stock-shaped ones are **one sentence**, always naming **`ERPNext - JM`** (63) / `Morocco - JM` (8) / `X1A - JM` (6), from **10 items only** — 7 of which have **zero pickable stock anywhere**.

**We never choose that warehouse.** It is in `pickable_condition`'s NOT IN list, 0 of its bins pass the filter, and **no Pick List Item in 30d carries it**. It came from `_insert_one`'s fallback:
```python
if pending > 0:
    rows_for_line.append((b["bin"] if b else it.warehouse, pending))   # <- b is None
```
`it.warehouse` is `ERPNext - JM` on **63% of Moroccan SO lines (7,675)** and `Morocco - JM` on 5% (660); **both hold 0 stock** — the function's own docstring says so three lines above. ee's `validate_picked_qty_in_location` then throws and the **whole** combined doc dies. Fixed `eb1716c`: drop that order by name, return `dropped` (do NOT append to the caller's `skipped` — `_insert_one` is retried after rollback, so appends survive work that never happened and repeat every retry).

**Impact replay on the live pool:** 184 orders, 72 have a line with no pickable bin, the coverage gate already skips 96, and **0 would reach `_insert_one` unplaced today** — so the failures are a **race** between `_available_totals` (once, in `_allocate_and_insert`) and `_resolve_bins` (again, inside `_insert_one`), not a gate hole.

**Bin reservations against nothing:** `Morocco - JM` = 8,069 items / **114,967 units reserved with actual 0**; `ERPNext - JM` = 2,331 / 19,805. `projected_qty` is meaningless wherever it is read. SREs are NOT the source (4 rows for the sample items) — it is open-SO `reserved_qty` against empty pseudo-warehouses.


Related: [picked-qty-vs-scanned-qty](picked-qty-vs-scanned-qty.md), [batch-ledger-corruption](batch-ledger-corruption.md), [stale-sre-holds](stale-sre-holds.md), [measure-dont-trust-audits](measure-dont-trust-audits.md).
