---
name: stale-sre-holds
description: "Cancelled orders keep live Stock Reservation Entries (sales cancel flips status, never cancels the doc) — false-OOS in the pick pool; SRE repair built into Batch Repair"
metadata: 
  type: project
---

**Found 2026-08-28** chasing item 45779760283902 ("24 orders OOS" with 3,354 units on hand): the pick pool subtracts every active Stock Reservation Entry, and the item's only pickable stock (63 in PLT - JM) was fully reserved by orders **sales-cancelled in Mar–Jun 2026** — the sales flow flips `custom_sales_status` to Cancelled WITHOUT cancelling the SO document, so ERPNext never auto-releases its SREs. Sibling of [batch-ledger-corruption](batch-ledger-corruption.md) (same pattern: holds outlive the flow that made them).

Measured on prod 2026-08-28: **497 live SREs on Cancelled orders → 539 units across 212 items** (+126 legit on Confirmed). Each one is a false-OOS.

**Fix built (`266bd62`)**: `batch_repair.sre_scan` / `sre_release(limit)` (POST, manager-gated) — framework cancel (Bin.reserved_qty updates itself), audit Comment per order, pick-pool caches busted. UI = second section on the Batch Repair page, validate with limit=1 first. Ahmed runs it himself.

Also learned: the rest of that item's stock (3,264) sits in SLOW ZONE — ee-rejected **by design** (reserve feeds the fast wall, see [slotting-project](slotting-project.md)); the ee rejected-warehouses list also correctly rejects the legacy sites (Agora AG-*, Babel BAB-*, Eldorado). "OOS with reserve stock" = replenishment job → blocking worklist now shows an amber "{n} in reserve" chip deep-linking Move Stock.

**Why:** any "item shows OOS but stock exists" report → check, in order: (1) which bins are pickable ∩ not ee-rejected, (2) active SREs vs the orders' real status, (3) batch holds, (4) draft PL claims.
**How to apply:** don't trust Bin totals as availability; `picking._available_totals` + SRE accounting is the single truth the portal uses.
