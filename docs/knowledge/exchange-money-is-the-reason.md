---
name: exchange-money-is-the-reason
description: Sales Exchange money — original_items IS original_total, the rate trap, the four outcomes, no GL, Shopify's model
metadata:
  type: project
---

Sales Exchange money, established on prod 2026-09-23.

**`original_items` is the money.** It lives in child doctype **`Sales Exchange
Original Item`** (NOT `Sales Exchange Item` — counting that one says 0 rows and
is wrong). Every exchange is created with its lines already in it: 1,131 rows
across 1,002 exchanges. `original_total = SUM(rate × qty)` over those rows — a
row with no rate reads 0.00, and an emptied table reads 0.00.

So editing that table edits the refund. Selecting only some lines = a **partial
return**, which settles against what actually comes back (new; the desk always
refunded the whole order). `validate()` refuses a row not on the Sales Order.

`exchange_total = exchange_items + SUM(tax rows)`; `difference = exchange_total
− original_total`. **The tax table is the only lever** — `original_total` is
recomputed every validate, so writing it is discarded, and reading it BEFORE
validate gives a stale value (this bug made "missing piece" read as
collect-the-whole-order). Always sum the rows.

`Sales Exchange` is NOT submittable and has produced **0 GL Entries** ever →
`account_head` on a tax row is a label, not a posting.

REPLACEMENT PRICING: prices live in Shopify — 242 of 248 replacement items have
no Item Price. Catalogue lookup covers 17.9%; "last rate this item sold at on a
submitted SO" takes it to 96.9%. Rate 0 ≠ free: it makes the settlement read
"refund the whole order".

The four outcomes (`_apply_money`): our fault + replacement out → 0; our fault +
nothing out → full refund, no fee; their call + replacement → new − back + 25;
their call + nothing → back − 25.

SHOPIFY'S MODEL (matches ours): `returnLineItems` = quantity against a fulfilled
order line, never a typed code; `exchangeLineItems` = separate list, a variantId;
`returnShippingFee` on the return (our 25), `restockingFee` per line. Reason enum
is per LINE there, single here.

See [confirmation-tracking-modules](confirmation-tracking-modules.md), [availability-one-definition](availability-one-definition.md).
Still open: the return leg posting stock back, and settlement closure.
