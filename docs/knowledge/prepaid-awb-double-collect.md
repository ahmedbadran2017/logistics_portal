---
name: prepaid-awb-double-collect
description: Cathedis AWB amount = grand_total − advance_paid, ignores payment_type; Payzone payments posted by hand days after the label → every Payzone AWB since July asked COD again; patched in logistics_portal 1d383f7
metadata:
  type: project
---

Found 2026-10-05 from #262346 (Payzone Maroc, 217.6, AWB at full amount, delivered).

- `ecommerce_integrations.shipping.cathedis.CathedisShipping.get_delivery_note_cash_on_delivery_amount` / `get_cash_on_delivery_amount` = round(grand_total − advance_paid) as a string; `_prepare_*` sends paymentType **PAYE when amount is "0.0"/"0", else ESPECES**. declaredValue = grand_total either way.
- Payzone payments are Payment Entries by hananekh (account `108.021.006 - Payzone Transactions - JM`), almost always AFTER the DN/AWB → advance_paid 0 at label time. 32 Payzone orders since 2026-07-01, all delivered. Reconciled invoices (to early Aug) show Cathedis remittance (`108.021.003 - Cathadis Transactions`, PEs owned by ahmed@) paying the SI on top of the Payzone PE = double collection (#245956, #246043, #246786, #247856, #249406, #250422, #252930, #253079, #254086; #251552 reversed). Bank transfer ("Virement bancaire", Deposite Transactions) shows the same pattern (#246427, #247117) — NOT patched, unconfirmed whether paid before shipping.
- Fix: `logistics_portal/overrides/cathedis.py` monkey-patches both methods for payment_type in PREPAID=("Payzone Maroc",), applied on import of logistics_portal.overrides (AWB job loads Pick List override first) + relabel path. Root fix still belongs in the ee fork.

**How to apply:** if someone adds a prepaid method, extend PREPAID; refunds/customer list is accounting's (Hanane). Related: [orders-without-delivery-notes](orders-without-delivery-notes.md).

**Bank transfer rule (Ahmed 2026-10-05, ab9e7cf):** accounting must confirm the transfer BEFORE preparation. `picking._TRANSFER_HELD` = payment_type "Virement bancaire" AND advance_paid + 1 < grand_total → out of `_POOL_WHERE` (now `_POOL_BASE` + NOT held), suggest_batches, orders._pick_availability, `_pick_gate`, and dropped from Desk pick lists in the PickList override validate. Board chip "Awaiting transfer" (`picking.transfer_held`). Posting the PE releases it; Cathedis patch also zeroes any remainder < 1 MAD (whole-dirham PEs). Double-collection list for accounting delivered as xlsx (Payzone: 9 confirmed 2,691 MAD, 14 likely 3,301, 5 with no Payzone PE 1,697; transfers 3 = 905).

**Accounting side (2026-10-05, accounting_portal 41da86c on main):** Sales tab "Transfers to confirm" (`accounting_portal/api/transfers.py` awaiting/confirm, page `frontend/src/pages/sales/TransfersQueue.vue`). Confirm = advance Payment Entry referencing the Sales Order via payments.create_payment_entry (write gateway; default account 108.021.007 Deposite Transactions). Held condition must stay identical in both apps: payment_type IN ('Virement bancaire','Bank Transfer') AND advance_paid + 1 < grand_total (logistics fa13a59). accounting_portal live repo = ~/Accounting/accounting_portal (the "~/Accounting portal" folder is a stale March scaffold); built bundle is committed; another session works there — use a worktree.
