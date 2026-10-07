# logistics_portal — working notes for the next session

Frappe v15 app (`app_name = logistics_portal`) + Vue 3 SPA for the Justyol Morocco
warehouse and contact-centre floor. Production site: **admin.justyol.com**
(company "Justyol Morocco", warehouses `… - JM`). Repo: `ahmedbadran2017/logistics_portal`, branch `main`.
Read `docs/HANDOFF.md` next: current state, what is waiting for deploy, open decisions.
Before changing an area, read its notes in `docs/knowledge/` (index: `docs/knowledge/README.md`).

## Layout
- `logistics_portal/api/*.py` — whitelisted endpoints, one module per area (picking, orders,
  shipping, pulse, stop, purchasing/goods-in, crossdock_in, crossdock_pickup, return_zone_repair,
  confirmation, cs, …). The frontend calls them as `api("module.fn")` / `apiPost("module.fn")`.
- `logistics_portal/overrides/` — doctype class overrides and monkey-patches (`pick_list.py`
  subclasses ecommerce_integrations' CustomPickList; `cathedis.py` patches the AWB COD amount).
- `logistics_portal/hooks.py` — routes, `override_doctype_class`, `doc_events`, scheduler.
- `frontend/` — Vue 3 + Tailwind, no frappe-ui (dropped; `src/lib/resource.js` is the RPC client).
  Pages in `src/pages`, routes in `src/router.js`, nav per role in `src/lib/roles.js`,
  strings in `src/locales/{en,fr,ar}.js` (every string in all three; Arabic is Egyptian-friendly MSA).
- Base routes: `/logistics`, `/confirmation`, `/tracking`. Never use `/shipments`, `/orders` etc. —
  ERPNext's customer portal owns them.

## Build & ship
- `cd frontend && npm run build` → writes `logistics_portal/public/logistics_portal.bundle.{js,css}`.
  **The bundle is committed**; rebuild and commit it with every frontend change.
- Commit to `main` and push. **Ahmed deploys production himself** — never run `/usr/bin/update`
  or any deploy/migrate on the server. Tell him what was pushed and whether it needs a restart.
- After a `hooks.py` change: restart BEFORE clear-cache, or the old hooks stay loaded.
- No `bench migrate` on prod from a session. Custom fields/doctypes are created idempotently
  in code (`ensure_*` helpers) or by Ahmed.

## Rules that are not obvious from the code
- **Clock**: stored timestamps are Istanbul (UTC+3); the floor is Morocco (UTC+1) → subtract 2h
  when you talk to people. **MariaDB `NOW()` is UTC** — never use it in a window; bind the site
  clock (`str(now_datetime())`) as a parameter.
- **Availability has one definition**: `picking.availability()` / `_available_totals()`. Every
  screen asks it. Do not add a second arithmetic on Bin.
- **A cancelled order must not move**: any step that creates a DN, AWB, label or pushes a parcel
  one door further must ask `picking.is_stopped(order)` or `stop.stopped_set(orders)`.
- `custom_sku` is the real SKU; `item_code` is the Shopify variant id. One SKU can have several
  items (duplicates) — look up by `custom_sku`, not by name.
- Order ownership: `_assign` (JSON array of emails) is what the portal scopes agents by;
  `custom_allocated_to` diverges and is a sales field.
- Supplier models (`Supplier.custom_fulfillment_model`): Cross-dock (bought per order, PO per
  order), Fulfillment = consignment (shelves `CN - <supplier> - JM`, owner = `Item.default_supplier`),
  or our own stock.
- `-ex` and `J-` orders may ship with no Delivery Note; carrier events are Comments on the SO.
- Joining `Delivery Note Item` then `SUM`/`COUNT(*)` multiplies money by basket size.
- Most Stock Reconciliations are cost revaluations, not counts: test `qty <> current_qty`.
- Stock Reconciliation and Delivery Note have **no `remarks` column** on prod — tag with a comment.

## Working style that has held up
- Measure on prod before changing anything; audits (and our own greps) have been wrong often.
  Read-only SQL first, then code.
- Comments explain *why*, with the measured case that motivated the line (order numbers, dates,
  counts). Keep that density when you edit nearby code.
- Prod writes (data fixes, cancelling DNs/AWBs, role changes) need Ahmed's explicit OK each time.
  Changes to what Shopify shows customers need his OK too.
- Ahmed writes in Egyptian Arabic or English; answer in the same language.

## Sister repos
- `ahmedbadran2017/Supplier_portal` (`supplier_portal` app: supplier side of cross-dock, store
  stock sync to the Shopify "Morocco" location).
- `ahmedbadran2017/Accounting-portal` (`accounting_portal`: bank-transfer confirmation queue that
  releases held orders to picking).
