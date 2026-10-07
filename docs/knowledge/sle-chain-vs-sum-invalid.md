---
name: sle-chain-vs-sum-invalid
description: SUM(actual_qty) vs qty_after_transaction is an INVALID integrity test across Stock Reconciliations — broken means chain ≠ Bin only
metadata: 
  type: project
---

**2026-09-11.** A Stock Reconciliation SLE carries `actual_qty = 0` while setting `qty_after_transaction` to an absolute count — the additive relationship `SUM(actual_qty) == chain tail` breaks legitimately at every reco and never recovers. JM has hundreds of recos (see [backdated-admin-recos](backdated-admin-recos.md)), so a sum-based scan flags most of the warehouse forever.

Proven on prod: the Batch Repair "Ledger chain" bench counted 726 broken in Return Zone with the sum test while the real test showed **0** — every completed Repost Item Valuation had healed the store, but the counter never moved, and Ahmed queued ~300 pointless (harmless) reposts chasing it.

**Why:** the only mismatch that refuses a stock move is `qty_after_transaction` (what validation reads) disagreeing with `Bin.actual_qty` (what the screen shows).

**How to apply:** integrity test = `|chain tail − Bin| > 0.001` only; keep sum as display context, never as a broken criterion. Fixed in `ledger_chain_scan` (commit f1ca79b). Cure for a true mismatch remains Repost Item Valuation from the pair's first posting date (verified end-to-end on item 48135354482942: chain 0 → 2 = bin, move unblocked). Related: [batch-ledger-corruption](batch-ledger-corruption.md) (different corruption class: bundle holds).
