---
name: batch-ledger-corruption
description: "Batch ledger ≠ Bin on JM shelves — ROOT CAUSE: Pick List batch holds never released after ee's DN ships with its own bundle; Batch Repair tool built to cancel stale holds"
metadata: 
  type: project
---

**Root cause NAILED 2026-08-26 (prod forensics, supersedes the earlier "over-consumption / batch-less inflow" hypothesis):** Pick List submit creates an **Outward Serial and Batch Bundle** (a reservation — no SLE). ee's background Delivery Note then consumes the stock with a **fresh bundle of its own** and the PL hold is **never released** → every shipped batched unit is double-counted in batch availability, forever. Boots 47249811374334 @ E5A: all 16 SLE rows carry correct bundles summing +5 = Bin exactly; the visible −2 batch net = 7 orphan PL bundles (PL-48978/51668/53519/53906/53964/54010/54067 — all docstatus=1, shipped). SR per-batch restatement moves Bin AND batch ledger equally (verified via MAT-RECO-2026-00086: usbf=1+batch+qty=0 → SLE −1), so the divergence is **invariant under stock documents** — only bundle-level cancellation fixes it. Stock Reconciliation repair (old plan item 1) is therefore WRONG — do not use it.

**Scale at discovery:** 21,896 live PL bundles holding −33,836 units site-wide; **9,203 bundles / −20,950 units stale** (every SO on the PL has per_delivered=100) = the immediately releasable set. Draft PLs hold 0 (bundles are made at submit). Symptom: 520/696 pool items batch-tracked; 37 items Bin>0 but ee=0 (unpickable), 444 pending orders touched.

**DEPLOYED 2026-08-27; live scan confirmed: 9,236 stale / 20,985 units hidden (of 21,929 holds / 33,871 units — UI sums match SQL exactly).** Monthly bundle distribution shows the leak is a YEAR old (since 2025-09: 580→3,467→3,095/mo...), tracking shipped-batched volume — validates the numbers as accumulation, not a bug. Ahmed had the tool open, release run pending.

**Batch Repair tool BUILT (commit 8bc699a):** `logistics_portal/api/batch_repair.py` + `/logistics/batch-repair` (manager nav). `scan()` counts stale vs all holds; `release(limit)` cancels stale bundles oldest-first — query-guarded to zero-SLE bundles whose PL orders are ALL delivered (or PL cancelled/deleted), framework `doc.cancel()` with raw `is_cancelled=1` fallback, audit Comment per PL, clears `lp_bt_*` caches; `probe(item)` shows shelf-Bin vs ee-pickable convergence. **Validation protocol: run limit=1 first** (one of the boots' 7 bundles), probe 47249811374334 — eeAvailable should jump 0→~5 — then scale to the full ~9.2k.

**Still open:** (a) prevention — ee's DN flow will keep accruing new stale holds per shipped batched order; after the first validated release run, wire an hourly scheduled sweep (release with no limit-anxiety since the query self-guards). (b) Strategic: stop enabling has_batch_no for JM-destined items (China/GLP artifact — Morocco ops don't need batch tracking). (c) problem_radar batch-drift check (Bin>0 & ee=0) still worth adding.

Create-time symptom already neutralized in the portal (`910eb22` `_batch_truth` cap, `15a7b61` poisonDrafts radar). See [picked-qty-vs-scanned-qty](picked-qty-vs-scanned-qty.md) for the three create-time mismatch classes.
