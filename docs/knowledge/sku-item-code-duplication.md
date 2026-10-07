---
name: sku-item-code-duplication
description: "How SKU vs item_code works in Justyol ERPNext, and the duplicate-item false-OOS problem"
metadata: 
  type: project
---

On Justyol's ERPNext, an **`Item.name`/`item_code` = the Shopify variant ID** (a number like 47769249743102), and **`variant_of` = the Shopify product ID**. The real, human SKU lives in **`Item.custom_sku`** (Data field, e.g. `JST0672-NavyBlue-L/XL` — encodes size+colour, so same custom_sku = the same sellable unit).

**The problem:** the same physical product gets re-imported and ends up as **several ERPNext Items (different item_code) sharing one custom_sku**. Shopify links an order line to one item_code; if that code has no stock, the order shows **OOS even though a sibling item_code (same SKU) holds stock**.

Scale on production (2026-07): 170k Items, 151k with custom_sku, **6,498 SKUs map to >1 item_code** (one had 96). Live false-OOS impact is modest at any moment (~2 orders net-honest, up to ~11 by the looser per-bin definition) but recurs daily.

Two data caveats: `custom_sku` was **not indexed** (added `lp_item_sku_idx` via after_migrate); and **negative-stock bins** make the portal's "any bin with (actual−reserved)>0 = pickable" definition unreliable (can show net-negative items as available) — Ahmed chose to leave that definition as-is for now.

Built (Layer 1, safe/read-only): **`inventory.sku_lookup(query)`** + `SkuLookupModal.vue` — accepts a SKU / item_code / order no / name and returns every sibling item_code grouped by custom_sku with net available + bins, flagging the ordered one. Entry points on the Orders board (SKU-lookup button + click-through from blocking-SKU restock rows). Deliberately does NOT edit the order's item_code (would break Shopify sync + accounting).

**CRITICAL nuance (found 2026-07):** `custom_sku` is used at TWO granularities — **variant-level** (e.g. `JST0672-NavyBlue-L/XL`, encodes colour+size → siblings ARE the same sellable unit, safe to rescue/merge) and **bare style-level** (e.g. `SS10019` with 82 codes, `G10097` with 96 → siblings are DIFFERENT sizes/colours, NOT interchangeable). Naive SKU matching would ship the wrong size. Rule used: only trust SKUs with **≤8 item codes** as variant-level. Also many bins carry NEGATIVE stock (oversold/data), so use net = SUM(actual−reserved) not per-bin.

Layer 2 (built): `orders._sku_rescue()` flags OOS/partial orders whose missing variant-level SKU has a net-positive sibling → board `rescuable` map → green "In stock under another code" badge on Pipeline rows (opens SKU lookup). Guarded to ≤8 codes. Live: ~2 orders.

Layer 3 (built): `inventory.sku_duplicates()` (cached 600s) — merge candidates = variant-level SKUs (2–8 codes) with stock SPLIT across codes (some empty). Shown in a "Duplicates to clean" tab on the SKU Finder page. Live examples: `J.SHORTS-*`, `JST0672-*`.

Still open: the actual **merge** of duplicate Items (root fix) is Ahmed's accounting decision — the report finds them. And the negative-stock bins are a separate stock-reconciliation problem. See [desk-elimination-progress](desk-elimination-progress.md).
