---
name: portal-base-routes
description: "The three portal bases (/logistics, /confirmation, /tracking) and the ERPNext customer-portal routes that must never be used as a base (/shipments, /orders, ...)"
metadata: 
  type: project
---

Portal bases on admin.justyol.com: `/logistics` (floor), `/confirmation` (contact center), `/tracking` (shipment-tracking team, since 2026-09-13). Each is a `website_route_rules` entry `/<base>/<path:app_path>` → a page template of the same name in `logistics_portal/templates/pages/`, all serving one SPA bundle; `frontend/src/lib/portal.js` reads the prefix.

**Why:** the tracking portal was first built on `/shipments` and rendered ERPNext's customer Delivery Note list instead — ERPNext's own `website_route_rules` own `/shipments`, `/orders`, `/invoices`, `/quotations`, `/issues`, `/addresses`, `/projects`, `/timesheets`, `/material-requests`, `/rfq`, `/supplier-quotations`, `/purchase-orders`, `/purchase-invoices`, `/newsletters`, and their rules win over ours. Ahmed asked for `/orders` as an alternative; same trap, declined.

**How to apply:** never pick a base from that list; check `frappe.get_hooks("website_route_rules")` on prod before adding one. After a deploy that changes hooks: `bench restart` FIRST, then `bench --site admin.justyol.com clear-cache` — clearing first lets a dying worker refill the `app_hooks` Redis key with the old module (that exact sequence cost an hour of 404s). See [deploy-protocol](deploy-protocol.md).
