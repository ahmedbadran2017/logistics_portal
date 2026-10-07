---
name: slotting-audit-findings
description: "Final pre-execution slotting audit (2026-08-31) — velocity was cross-company, and 111 of 317 A-movers have no shelf face at all"
metadata: 
  type: project
---

**Audit run 2026-08-31**, right before the floor physically re-arranges the warehouse. Findings measured on prod, fixes shipped in `277982c`.

**Defects fixed**
- `_velocity` had **no company filter** — 483 Justyol China pick lines counted as Moroccan demand. **161 SKUs were in the wrong class**; A shrank 355 → 317 once fenced. This is the number the whole re-slot is built on.
- `overstock_list`'s demand query: not fenced, and counted **Cancelled + Duplicated** orders as demand (a dead order is never picked). Real impact only ~1% of excess — I predicted more and was wrong; fixed anyway because it sets the keep level.
- No guard that a role letter is actually pickable (`lp_excluded_zones`). None collides today (excluded list has no `[A-Z][0-9]` bin); `target_plan` now returns `excludedConflicts`.

**The big gap — the plan only had one half.** `move_list` answered "which A-movers are outside E+G" and nothing else. Two worklists added:
- **`no_face_list`** — **111 of 317 A-movers have NO picking face**. The single most-picked SKU in the building (3,608 picks/90d) sits only in SLOW ZONE. 44 pullable now, 53 have stock only where we may not pull (Maslak `- ML`, China `- JCH`, blocked families), 14 have none anywhere. Sources respect `stock_moves._movable_condition(as_source=True)`.
- **`evacuate_list`** — the fast wall holds **334 non-A SKUs (1,311 units)** and only **13 empty bins** across E+G. Cold facings first (95 rows / 312u free a whole bin). Without this the crew hits a full wall.

**Capacity verdict: the plan is feasible.** A = 206 stocked SKUs into 65 bins = 3.2 SKU/bin, while H already runs 29 SKU/bin. Not the constraint. Total moves ≈ 812 (131 A + 337 B + 344 C) plus 228 A-placements.

**Watch:** H has **0 empty bins** and **1,432 cold SKUs** — the crowding is dead stock, not volume. 19 real SKUs are picked under >1 item_code; only 2 misclassify (see [sku-item-code-duplication](sku-item-code-duplication.md)).

Related: [slotting-project](slotting-project.md), [receiving-zone-pickable](receiving-zone-pickable.md), [measure-dont-trust-audits](measure-dont-trust-audits.md).
