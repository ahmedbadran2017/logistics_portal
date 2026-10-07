---
name: assign-vs-allocated-to
description: "Two parallel order-ownership fields on Sales Order; confirmation portal scopes agents by _assign, not custom_allocated_to"
metadata: 
  type: reference
---

Justyol runs **two independent "who owns this order" fields** on Sales Order, and they diverge badly:
- **`_assign`** — ERPNext's native ToDo assignment (JSON array string, e.g. `["hjustyol@gmail.com"]`). This is what the team actually divides work by, and what the desk's "Assigned to me" list view uses.
- **`custom_allocated_to`** — the confirmation intake round-robin (single email). Auto-set at intake.

Measured 2026-07-30: across the 19 live Not-Delivered orders (JM) the two fields agreed on **1 of 19**. An order is routinely `custom_allocated_to` agent A but `_assign` agent B. Both are set on ~100% of the live confirmation queue, so either can scope without orphaning.

**Decision (user, 2026-07-30): `_assign` is the authoritative owner for the portal.** The confirmation portal now scopes each agent's session by `_assign` (commit 5701fb4):
- Working queues, Monitoring, Not Delivered, the section dashboard, and the write-guard → `_assign`.
- The DONE tabs (Confirmed/Cancelled/Duplicated) stay on `custom_allocated_to` — `act()` stamps it with the acting agent, so they're a true "what I did" trail. The write-guard accepts EITHER field so reopening an order you decided still works.

**Matching `_assign` in SQL:** it's a JSON array text, so match the QUOTED email — `_assign LIKE CONCAT('%"', email, '"%')` — never a bare substring (one address could substring-match another). Verified equal to `JSON_CONTAINS(_assign, '"email"')` on prod. Multi-assignee is rare (1 of 1,835 live).

Gotcha seen: an ERPNext list view filtered to an agent's `_assign` can read STALE — it showed 8 "Not Delivered" when 3 had already changed to Cancelled/Confirmed (real = 5). Refresh before comparing to the portal.

Related: [confirmation-tracking-modules](confirmation-tracking-modules.md), [measure-dont-trust-audits](measure-dont-trust-audits.md).
