---
name: stale-onhold-pile
description: "Confirmation queue polluted by a 1,757 legacy On Hold pile; dashboard fixed, prod data cleanup still pending"
metadata: 
  type: project
---

The Confirmation section dashboard read as a near-total SLA breach (1,816 "waiting to be called", 98% older than 3 days) because a stale **On Hold** pile dominated it. Investigated on prod 2026-07-30.

**The pile (1,757 On Hold, Justyol Morocco, docstatus=1):**
- 100% have `custom_call_attempts=0` AND `custom_next_call_at=NULL` → never went through the portal's on-hold call flow, so the 48h On-Hold retry can never resurface them.
- Dominated by a **Nov-2025 batch (1,260)**; oldest Sept 2025 (~313 days).
- **181 already moved physically** while still tagged On Hold: 23 Delivered, 50 Shipped, 5 Returned, 69 Label Printed, etc. (e.g. #136027 delivered with AWB LD006463412). Their sales-status lies.
- Genuine callable backlog is only ~58 (DNA 47 + Follow Up 10 + Pending 1), ~9,937 MAD — not 383k.

**Portal fix shipped** (commit 84da282): `dashboard()` in confirmation.py now measures the ACTIONABLE queue via two predicates — `_IN_HAND` (logistics_status NULL/Pending/'' — not yet picked/shipped) and `_PARKED` (On Hold + attempts=0 + next_call NULL). The parked pile and the moved-but-live count are returned separately (`parked`, `movedButOnHold`) and shown on their own card, never dropped. Same reasoning as act()'s reopen guard: once the warehouse has it, confirmation doesn't.

**STILL PENDING — prod data cleanup (user deferred, no script yet, 2026-07-30):**
1. The 181 moved-but-On-Hold → correct their sales-status (Delivered/Shipped → Confirmed).
2. The 1,576 abandoned On Hold (Nov-2025 batch, COD orders 9+ months old = dead) → bulk cancel/archive decision.
I'm read-only on prod (MCP); a bench script for the user to run is the delivery path when they're ready.

Related: [stranded-confirmed-orders](stranded-confirmed-orders.md), [measure-dont-trust-audits](measure-dont-trust-audits.md).
