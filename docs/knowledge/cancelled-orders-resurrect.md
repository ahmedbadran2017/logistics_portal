---
name: cancelled-orders-resurrect
description: Automation reopens cancelled orders (Administrator writes); the validate guard silently never fired because get_doc_before_save is not always loaded
metadata: 
  type: project
---

TKT-2609-3709664, re-measured 2026-09-23.

An external automation writes to Sales Orders **as `Administrator`**, flipping
`custom_sales_status` out of `Cancelled` — one field, no comment, cancellation
reason left intact. 259 orders affected: **245 → Follow Up, 70 → Confirmed**.

**The guard was there and never fired once** — registered on `validate`,
importable, zero witness comments against 245 flips. Cause: it read the old
status from `doc.get_doc_before_save()`, which **is not populated on every save
path**. Proved on prod by running `validate()` both ways on a cancelled order:
without the before-save doc the guard returns silently; with it, it reverts.
→ Read the previous value with `frappe.db.get_value` instead; during validate
the row still holds the committed value. Never trust `get_doc_before_save()`
for a guard.

It also only covered `Follow Up`. `Confirmed` is the worse half — it ships.

**Cost already paid: 174 of the reopened orders SHIPPED** (AWB / shipped stamp
/ delivered / returned). They are deliberately NOT reverted — the parcel left.
Only 12 that never moved were restored (`restore_resurrected_cancels_2`).

Humans reopening is legitimate and untouched: every portal write runs under the
agent's login, never Administrator. 188 human reopens to Confirmed are fine.

Who runs the automation is still open — same open question as
[backdated-admin-recos](backdated-admin-recos.md). See also [desk-decisions-leave-no-portal-fields](desk-decisions-leave-no-portal-fields.md).
