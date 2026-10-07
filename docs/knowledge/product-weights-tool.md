---
name: product-weights-tool
description: Portal Weights tool + the grams-in/kg-stored rule for Item weights
metadata: 
  type: project
---

Item weight lives on the **Item master**: `weight_per_unit` (Float) + `weight_uom` (Link) — the value Purchase Receipts/transactions default from, so it's what feeds accounting + **landed cost** (Ahmed's stated purpose). Built the **Weights tool** 2026-08-24 (`2a2363e`): `logistics_portal/api/weights.py` (coverage / queue / lookup / set_weight, gated manager+dispatcher+returns) + `frontend/src/pages/Weights.vue` at `/logistics/weights` — scan-first PDA flow (scan → grams input → Save → auto-advance) + searchable worklist (missing-weight first, most-recently-received first) + coverage bar. Nav under Inventory for those 3 roles; added a `scale` icon to Icon.vue.

**CRITICAL unit rule:** the catalog is stored in **Kg** — 115,314 items on `weight_uom='Kg'`, only 7 on Gram. So the tool **enters in grams (scale-friendly) but STORES in kg** (`weight_per_unit = g/1000`, `weight_uom='Kg'`). Storing grams would give a mixed-unit catalog and **corrupt any weight SUM a landed-cost report does**. Never store grams. Range-guarded 1g–50kg. `set_weight` uses `db.set_value` (not doc.save) so it never fires the Item on_update / Shopify item sync. `apply_siblings` copies to same-`custom_sku` codes only when 2–8 codes (variant-level = same physical unit; a bare style SKU spans different sizes → different weights). See [sku-item-code-duplication](sku-item-code-duplication.md) for the ≤8-codes heuristic.

Scope measured 2026-08-24: in-stock JM items 4,406; **missing weight 1,937 (44%)**. Whole enabled catalog: 174,826 items, 60,804 missing (35%) — but only the stocked ones can physically be weighed, so that's the worklist. Deploy = restart only (backend + prebuilt frontend), no migrate.
