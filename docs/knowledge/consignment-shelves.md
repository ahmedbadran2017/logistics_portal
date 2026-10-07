---
name: consignment-shelves
description: Third supplier model — consignment goods live one-supplier-per-shelf under Consignment - JM; membership IS the shelf (no Consignment option on custom_fulfillment_model); owner = Item.default_supplier (99.6% filled)
metadata:
  type: project
---

**Built by Ahmed from the supplier portal on 2026-09-28.** Warehouse tree:
`Soft Warehouse - JM` → `Consignment - JM` (group) → `Consignment Receiving - JM` + **20 shelves named `CN - <supplier> - JM`**. All 20 shelf names resolve to a real Supplier exactly via `TRIM(SUBSTRING(warehouse_name, 6))`. Shelves are `is_rejected_warehouse=0`, not in `lp_excluded_zones` → **consignment stock is pickable/sellable**, unlike [receiving-zone-pickable](receiving-zone-pickable.md).

**CORRECTED by the supplier_portal spec (2026-09-30):** consignment IS stored on `Supplier.custom_fulfillment_model`, as the value **`"Fulfillment"`** — that Select offers only `Fulfillment` and `Cross-dock`, and supplier_portal reuses Fulfillment for consignment. My first reading (membership = the section exists) gave identical results — the 20 "Fulfillment" suppliers are exactly the 20 with a section, set difference empty both ways — but the field is authoritative, so key off it.

**Import, never copy — `supplier_portal.api.consignment`:** `is_consignment_warehouse(wh)`, `section_of(supplier)`, `section_supplier(wh)`, `golive()` (reads site_config `consignment_golive`; **still None**, so supplier_portal's own guards are off). After go-live it enforces: a Delivery Note may ship consignment goods only from the owner's section; a Stock Entry may NOT move them out of the area into our bins; goods moving INTO the area must belong to that section's supplier. `logistics_portal/api/consignment.py` is our single import point and degrades quietly if the app is missing, like `picking._ee_rejected()`.

**Owner of a piece = `Item.default_supplier`** (a Custom Field, Link→Supplier), set on **176,215 of 176,970 live items = 99.6%**. Worked example from the Move Stock screen: SKU `chrs-010` → item `9135223668990` → `default_supplier` "Christelle Paris" → shelf `CN - Christelle Paris - JM`. `Item Supplier` child table (185 rows/3 suppliers) and `Item.brand` (0 set) are both useless for this — do not use them.

**Supplier-portal doctypes that back this:** `Consignment Supply Request` (+ Item child: item_code/qty/rate/received_qty; parent carries supplier, status, expected_date, purchase_receipts) and `Supplier Handover`. As of 2026-09-30 **zero** Consignment Supply Requests exist and **zero** units sit in any CN shelf — the lane is new and nothing has flowed through it yet.

**Waiting work:** **1,444 units across 296 item-rows for 13 suppliers already sit in `Receiving Zone - JM`** needing put-away to their own shelves (Parfumora 709u, Christelle Paris 329u, NutriPulse 128u). Note Receiving is currently vetoed for picking, so that stock is invisible to selling until it is moved.

**Guard built 2026-09-30** in `api/stock_moves.py`: `consignment_owner(item_code) -> (supplier, shelf)`; `move_lookup` returns `consignment: {supplier, warehouse}` so the screen locks the target, and `move_stock` throws if `target != shelf`. Covers **1,947 items**. A supplier whose shelf is missing or disabled falls back to unguarded on purpose — better a normal move than pointing the floor at a bin ERPNext refuses. Hand-back to the supplier has NO Move Stock path by design (that is `Supplier Handover` territory).

**DEPLOYED to prod 2026-09-30** (branch `consignment-cycle`) and verified live: `move_lookup("chrs-010")` returns the locked section, put-away queue shows 18 consignment rows of 40 with **zero** pointed at our shelves, Goods In lists 24 POs with **zero** lane-owned leaks, floor map builds (41 groups). `Consignment Receiving - JM` does not appear in the Settings zone panel — correct: `warehouse_settings()` skips `_family_excluded` zones holding 0 units ("empty AND permanently locked"), so it will appear as locked once stock lands there.

**Goods In routing BUILT 2026-10-01 (commit 0e3f589, needs deploy):** `purchasing._routes()` fixes the bin per item — consignment item → its CN section (via `sections_for`), whatever the typed target; a CN section typed as target for non-consignment items is refused. Measured before: since 2026-08-01, 1,271u received into Receiving and **989u straight onto OUR shelves** (D3C, D2C, C4C, H12B) — mixed stock. Item owner == PO supplier on every row.
**Surprise:** consignment suppliers have **3,734 open per-order POs** (`#<order>-<supplier>-JM`, 4,667 lines, many from old orders like #135266) — they buy per sold order like cross-dock, not by stock request. Unexamined: are these stale, and should a per-order consignment piece also be reserved for its order?
