---
name: shelf-label-barcode-limits
description: "Long SKUs printed unscannable Code 128 shelf labels — fixed by paper-derived module width, subset C, and an item_code payload fallback"
metadata: 
  type: project
---

**Found 2026-08-31** from a photo of a label the floor scanner refused to read (`MB000340312-18 Ay`). Not an outlier: measured on prod, of **3,195 SKUs stocked on shelves** the median is **16 chars**, p90 **21**, max **47** — only **918** are short enough for a readable Code 128 on a 50×30mm label.

**Three defects, all fixed in `d524e00`:**
1. **Bars were sized by CSS, not paper.** `shelfLabelPrint.js` drew at a fixed `module: 1.4` then let `max-width: (w-4)mm` shrink the finished SVG → ~0.2mm modules. Below the ~**0.25mm** handheld floor, and finer than the **0.125mm dot** of a 203dpi Zebra head, so each bar printed as an unstable 1-or-2-dot smear. Now: `module = label_w / (modules + 20 quiet)`.
2. **Encoder was subset B only** — 11 modules per character. Added **B/C auto-switching**: a 14-digit code goes 189 → **112 modules**. Verified by round-trip decoding the generated symbols + mod-103 checksum.
3. **143 SKUs contain Turkish letters** (İ ı Ş ş). Code 128 is printable-ASCII only, so those characters were dropped **silently** and the label scanned back to a string matching no item. Such SKUs can never be the payload.

**The fix that works: `warehouses._label_payloads()` picks the barcode server-side.** SKU when it fits → else the **numeric item_code** (all 3,195 are pure digits; subset C → **0.38mm** on 50mm stock). `picking.resolve_scan` already accepts it (custom_sku → Item Barcode → item_code). The human line still prints the SKU.

**Trap handled:** **9 items** have a `custom_sku` equal to a DIFFERENT item's `item_code` — scanning the fallback would resolve to the wrong product (custom_sku wins in resolve_scan). Those are excluded from the fallback and flagged "needs 57mm".

Result on the busiest shelf (D1C., 190 items) at the narrowest 40mm stock: 44 SKU / 146 item_code / **0 unreadable**.

**Rule:** the Python counter in `warehouses.py` and the JS encoder in `lib/code128.js` are twins — change one, change both; they are cross-checked to agree.

Related: [zebra-pda-wedge-no-key-events](zebra-pda-wedge-no-key-events.md), [sku-item-code-duplication](sku-item-code-duplication.md), [measure-dont-trust-audits](measure-dont-trust-audits.md).
