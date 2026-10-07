---
name: shopify-sync-ignores-pending-orders
description: ROOT CAUSE of oversell/OOS orders — Shopify "ERPNext" location available = shelf Bin qty; SO reservations sit on Morocco - JM / ERPNext - JM (unmapped) so pending orders are never subtracted
metadata:
  type: project
---
Measured 2026-10-07 on 77 blocked orders / 81 lines (19 OOS, 28 partial, 30 local):
- 37 lines = ONE SKU MCH09045 (JHome storage box, ~50/day). 232 arrived 09-30, sold out by 10-05; Shopify still showed available=1 while 37 orders waited. 52 units sat in Return Zone (69 returns booked 10-06), 273 Defective, 1727 in Yakuplu (Turkey).
- 32 lines cross-dock (waiting supplier; 11 with NO PO, 3 draft PO = lane leak).
- 6 MU Group lines: stock in "GLP-MU temporary storage area - JCH" (other company, not pickable).
- 2 ghost shelves: short_shelf report active but Bin still 1 → Shopify keeps selling it.
- 1 duplicate SKU, 2 consignment, 1 truly out.

Mechanism: Shopify Warehouse Mapping = ~390 JM shelves (incl. SLOW ZONE, PLT, CN sections) → location 82935283966 "ERPNext". Prod ecommerce_integrations fork has sync_single_item_inventory_to_shopify (on SLE/SRE submit). available = Σ mapped (actual − reserved_qty); SO reserved_qty lands on Morocco - JM / ERPNext - JM / In Transit / Stores (never mapped) → 0 subtracted. Each SLE resets available to shelf qty, re-offering units already sold to unpicked orders. Shopify "committed" is meaningless (orders never fulfilled in Shopify). Shopify "Morocco" location = cross-dock supplier-declared stock (supplier_portal crossdock_stock.sync_store). inventoryPolicy DENY, and COD app sales DID drop to ~0 when shelf was 0 (09-27..30) → a correct available number would stop it.

**Why:** "out of stock" orders are mostly manufactured by the sync, not by purchasing.
**How to apply:** fix = push available = availability(scope="sell") − open-order demand − short_shelf ghosts. Outward-facing; get Ahmed's go first. Related: [availability-one-definition](availability-one-definition.md), [short-pick-radar](short-pick-radar.md), [crossdock-lane-state](crossdock-lane-state.md), [sku-item-code-duplication](sku-item-code-duplication.md).
