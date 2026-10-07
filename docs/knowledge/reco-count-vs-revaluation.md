---
name: reco-count-vs-revaluation
description: Stock Reconciliation is used for BOTH counting and cost revaluation; the ledger cannot tell them apart — test qty <> current_qty on the item rows
metadata: 
  type: project
---

On this site the Stock Reconciliation doctype carries two completely
different jobs: the floor counting a shelf, and Accounts revaluing stock
(same quantity, new rate). Measured 2026-09-12 over 30 days: **22,085 of
22,320 reconciliations changed no quantity at all** — the counting work is
the 1% minority.

**The obvious test is wrong.** A reconciliation's Stock Ledger Entries carry
`actual_qty = 0` whether it counted or revalued (see [sle-chain-vs-sum-invalid](sle-chain-vs-sum-invalid.md)),
so any ledger-based filter discards real counts too. The discriminator lives
on the item rows:

```sql
EXISTS (SELECT 1 FROM `tabStock Reconciliation Item` i
        WHERE i.parent = sr.name AND i.qty <> i.current_qty)
```

Applied in `scanlog._sys_actions`, `scanlog.floor_history` and
`cycle_count._evidence` (constant `COUNTED_ONLY` in scanlog). Without it an
accountant posting 425 revaluations in six minutes tops the floor board above
every picker, and a revalued zone reports itself as freshly counted.

This also **corrects** the earlier audit reading of those bulk reconciliations
as inbound stock arriving through counts — they are a costing routine, not an
inbound path. Whether that routine belongs where it sits is a governance
question for Ahmed, still open. Related: [backdated-admin-recos](backdated-admin-recos.md),
[cycle-count-batch-bundle](cycle-count-batch-bundle.md).
