# Handoff — state as of 2026-10-07

What was built last, what is waiting, and what was found but not acted on.
`git log` has the full story; commit messages carry the measured case behind each change.

## Pushed, waiting for deploy / first use on the floor
| Commit | What | Verify after deploy |
|---|---|---|
| 9182c3a | Pick List submit drops orders cancelled while picking (`overrides/pick_list.py`, `stop.stopped_set`); `shipping.retry_awb` refuses stopped orders; Floor Pulse skips cancelled orders in its door counts and has an **Orders** panel (`pulse.list_orders`) naming the held order per list | Submit a list holding a cancelled order → no DN/AWB for it, toast names it. PL-56599 / PL-56601 leave "stuck at Packed" |
| 43142f3, b29bc42, 91d659e | Return Zone repair (`api/return_zone_repair.py`, page `/logistics/return-zone-repair`, manager): paste sheet lines or an order number → status per line; **Restore** (one-line Stock Reconciliation at the count's rate) and **Register return** (return DN into Return Zone) | Try ONE zeroed line first (e.g. SKU 600041714 on #247619). Both buttons write to prod and have not been exercised yet |
| a429715 | Manifest submit no longer rewinds delivered parcels to Shipped (snapshot + `restore_departed`); portal "Submit manifest" button | Next late manifest submit: delivered parcels stay Delivered |
| ab9e7cf, fa13a59 | Bank-transfer orders held from picking until accounting posts the payment (`picking._TRANSFER_HELD`) | Accounting queue lives in accounting_portal (TransfersQueue) |
| 1d383f7 | Payzone (card-paid) orders: Cathedis AWB COD amount forced to 0 (`overrides/cathedis.py`) | New Payzone AWB shows 0 to collect |
| 5fa4bfd, 31eabd6 | Picker dropdown built from roles; Pulse stage-filter shadowing + UTC window fixes | — |

## Found, measured, NOT fixed — need Ahmed's decision
1. **Shopify oversells (root cause of most "out of stock" orders).** The Shopify "ERPNext" location
   gets `available = Σ(actual − reserved)` over ~390 mapped shelves, but Sales Order reservations
   sit on `Morocco - JM` / `ERPNext - JM` (unmapped), so orders confirmed-but-not-picked are never
   subtracted; every stock move re-offers units already sold. 2026-10-07: 37 of 81 blocked lines
   were one SKU (MCH09045). Proposed fix: push `availability(scope="sell") − open-order demand −
   short-shelf reports`. Changes what customers see → needs his go.
2. **Cleanup of orders labelled after cancel**: #264068, J-010521, J-010023, #260243 (cancel DN +
   Cathedis AWB, piece back to shelf); SAL-ORD-2026-03568 is In Transit → recall. Prod + carrier writes.
3. **Cross-dock lane leaks**: 11 blocked cross-dock lines with no PO, 3 with a draft PO (several are
   manual SAL-ORD orders). supplier_portal branch `crossdock-po-settle-sweep` (settle POs in the
   sweep when the supplier user cannot write the SO) is **not merged**.
4. **NOW() sweep**: ~128 SQL windows use `NOW()` (UTC) against Istanbul timestamps → 3h off.
5. **Roles**: several floor staff hold the `manager` portal role (can edit bonus, run repairs).
   Role changes are his call.
6. Orders on archived / unavailable products (the "Justyol COD" Shopify app, id 392944517121,
   creates most orders); who owns that app is open.
7. Stale On Hold pile (1,757 legacy) data cleanup, 3,734 open per-order consignment POs unexamined,
   PO `before_submit` guard for cancelled orders.

## How prod was read
Through a Frappe Assistant MCP connector on admin.justyol.com (read-only SQL + a Python sandbox).
A second connector points at **admin-dev**, not prod — check which one you hold before trusting a
number. The sandbox blocks imports, file access, `any`/`next`/`repr`, and returns every leftover
variable (wrap work in a function and `del` it).

## Where the deeper knowledge is
Ahmed keeps a set of notes — one measured fact per topic: batch ledger holds, stale SREs,
return credit aborts, slotting, label barcodes, short-pick radar, bonus scheme, exchanges,
cancelled-order resurrection, manifest rewinds, PDA scanner behaviour, etc. Ask him for them
(`docs/knowledge/` if he adds them to the repo) before touching those areas.
