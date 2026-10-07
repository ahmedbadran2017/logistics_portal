---
name: return-credit-loop-aborts
description: Return Shipment marks rows received but its credit loop dies part-way — stock never posted; Return Repair tool built in the portal
metadata: 
  type: project
---

**Found 2026-08-28** (MCH100013 "returned 10 today but Return Zone empty"). A submitted **Return Shipment** (RET-26-…) flags every row `is_complete=1` with `actual_qty`, but only the first N rows get a return Delivery Note. Proof: credited rows are always a **contiguous prefix** of the child table (1..15, 1..16, 1..88, 1..182 on four sampled docs) and DNs are created ~0.5s apart → a row-by-row loop aborting mid-way. Earlier rows are already committed, later rows never run, the parent still submits, **nothing is logged**. Re-running `make_return_doc` on the first uncredited row succeeds, so it is transient/exception mid-loop, not bad data (suspect the same `Document has been modified after you have opened it` concurrency error seen on pick lists).

**Consequence:** the warehouse physically holds units ERPNext cannot see → Restock Returns shows an empty Return Zone, stock unpickable, value invisible.

**The loop lives in the Return Shipment app (NOT logistics_portal)** — real fix belongs to its owner: per-row try/except + retry + error log, and don't leave `is_complete` set for rows that never posted.

**Portal safety net built (`a8dcfb5`)**: `api/returns_repair.py` — `scan(days)` (row-level truth: received minus already-returned for that exact (original DN, item), capped by shipped qty) + `complete(ret, limit)` (POST, manager; posts a normal return DN per row into Return Zone dated today; per-row try/except; can't double-credit; comments the shipment; busts stock caches). UI = third section on the Batch Repair page. Ahmed runs it (limit=1 first).

**Key lesson:** the naive counter (rows-complete − DNs-created) is WRONG — it flagged 4 of 5 shipments that were actually fine (later shipments had credited them). Always compare at (original DN, item) grain. Measured real gap: 74 units (RET-26-3656905) + 147 units (RET-26-3644882).

Related: [batch-ledger-corruption](batch-ledger-corruption.md), [stale-sre-holds](stale-sre-holds.md) — same family: holds/credits that outlive the flow that made them.
