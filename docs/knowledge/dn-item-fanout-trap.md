---
name: dn-item-fanout-trap
description: "Joining tabDelivery Note Item and aggregating with SUM/COUNT(*) multiplies every number by basket size — it hit bonus pay, reports and customer LTV"
metadata: 
  type: project
---

Any query that joins `tabDelivery Note Item` produces **one row per LINE**, not
per parcel. Aggregating it with `SUM(...)` / `COUNT(*)` multiplies the result by
the basket size. About a fifth of delivery notes carry 2+ lines, so the error is
large and — worse — **uneven**: it scales with what the customer bought.

Always `COUNT(DISTINCT dn.name)` for parcels, or collapse per order in a
subquery first when summing money.

Found in four places at once (fixed 2026-07-16): the bonus board's delivered
points (real MAD paid to agents), `delivery_rate` (the payout quality gate and
My Performance), `confirmation.report`'s money KPIs, and `customers.history_for`
lifetime value.

The tell for why it stayed invisible: an order with **no** delivery note produces
one row and stays honest. The error only appears on orders that shipped well, so
the numbers look plausible and the worst-affected agent looks like the best one.

Related: [logistics-erpnext-fields](logistics-erpnext-fields.md), [confirmation-tracking-modules](confirmation-tracking-modules.md)
