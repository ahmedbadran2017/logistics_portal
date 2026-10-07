---
name: cycle-count-batch-bundle
description: "Counting a batch-tracked bin needs a hand-built Serial and Batch Bundle; reconcile_all_serial_batch silently overwrites the counted qty with the book's"
metadata:
  type: project
---

**Found 2026-09-09.** `cycle_count.submit_count` died on *"Row # 1: Please add
Serial and Batch Bundle for Item …"*. A batch-tracked item cannot be reconciled
by quantity alone, and that is **27% of the bins holding stock** (1,979 of
7,274) — including the shelves the short-pick worklist points at.

`StockReconciliation.set_current_serial_and_batch_bundle` throws unless one of
`use_serial_batch_fields`, `reconcile_all_serial_batch`, or
`serial_and_batch_bundle` is set. **Two of the three are traps:**

- **`reconcile_all_serial_batch` is the one that looks right and is worst.**
  For any non-zero qty, `set_new_serial_and_batch_bundle` then runs
  `item.qty = abs(current_doc.total_qty)` — it replaces the counted number
  with the book's and copies the same batches back in, so the count posts
  nothing. (It happens to be correct for qty=0 only, because that method
  starts with `if not item.qty: continue`.)
- **`use_serial_batch_fields` + `batch_no`** reconciles ONE batch. Fine for the
  **91.3%** of these bins holding a single batch, silently wrong for the rest.

**The fix (built): construct the Inward bundle ourselves**, listing EVERY batch
in the bin with its resulting qty — including the ones ending at 0. A batch
left out is never touched, so its stock survives a count that said the shelf
was empty. Zero-qty rows are legal for exactly this case: `validate_serial_and_
batch_no` skips the "Qty is mandatory for the batch" throw when
`voucher_type == "Stock Reconciliation"` and `type_of_transaction == "Inward"`.
Shortfall comes off the FRONT of the picking queue, surplus on the back.

**TWO different functions are named `get_available_batches`** —
`batch.batch` returns an `OrderedDict` batch→qty in picking order (this is the
one Stock Reconciliation imports); `serial_and_batch_bundle` returns a list of
dicts *including* zero-qty batches. Using the wrong one makes your plan and
ERPNext's view of the same shelf disagree.

**Do not read batches from `Stock Ledger Entry.batch_no`** — in v15 it is NULL
even for batched items (batches live in the bundle). Measured: 107 SLEs for one
item, 107 with a bundle, 0 with `batch_no`. That column made me wrongly
conclude the stock had no batch behind it.

Verified read-only on prod: 200 random batched-item bins all have batch totals
exactly equal to `Bin.actual_qty`, and 15 bundles passed the real validation
(the failing count, 2- and 8-batch bins, zero/decrease/surplus) with
`total_qty` = the counted number every time.

Related: [batch-ledger-corruption](batch-ledger-corruption.md), [measure-dont-trust-audits](measure-dont-trust-audits.md),
[availability-one-definition](availability-one-definition.md).
