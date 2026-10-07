---
name: return-zone-repair-tool
description: Supplier-bound returns physically in Return Zone but off the books (sheet "Return"/Feuille 10); 3 causes; /logistics/return-zone-repair tool built 2026-10-06 (43142f3)
metadata:
  type: project
---
Feuille 10 (112 lines, mostly Town Team) "not in Return Zone" = three different things:
already handed back via PR return (68), zeroed by RZ counts MAT-RECO-2026-22740/00086/22784 (18),
customer return never booked as return DN (24), plus unknown SKUs.

Tool `api/return_zone_repair.py` + `ReturnZoneRepair.vue` (manager): restore = one-line Stock Reco today
at the count's current_valuation_rate, capped by min(expected−current, zeroed−already restored; remark tag
"Return Zone repair"); register = make_return_doc on the order's DN into RZ. Hand-back still via Supplier pickup.
The big counts can't be cancelled (hundreds of correct lines + later moves).

**Why:** RZ counts zero pieces that are waiting for the supplier → purchasing can't book the hand-back.
**How to apply:** future RZ counts must exclude supplier-bound returns, or this repeats. Related: [crossdock-lane-state](crossdock-lane-state.md), [reco-count-vs-revaluation](reco-count-vs-revaluation.md), [return-credit-loop-aborts](return-credit-loop-aborts.md).
