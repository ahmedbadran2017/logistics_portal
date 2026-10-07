---
name: manifest-submit-rewinds-status
description: codx_erp Shipment on_submit sets logistics_status='Shipped' on every DN/SO of the manifest — late submits rewind Delivered/Returned; snapshot+restore built (a429715); portal can now submit past drafts
metadata:
  type: project
---

Found 2026-10-06. `codx_erp.overrides.shipment.CustomShipment.on_submit` enqueues `update_shipment_documents` (raw UPDATE DN + SO `custom_logistics_status='Shipped'`, unconditional) and `create_draft_sales_invoices_for_shipment`. Mehdi/Reda submit manifests from the Desk the next noon (or days later), so delivered parcels get rewound: 286 SO / 398 DN in 90 days read Shipped while track = Delivered; carrier_sync never fixes it (it compares carrier vs track field, which agree).

Fix (logistics_portal a429715, needs deploy): `shipping.on_manifest_submit` → `_snapshot_departed` (DefaultValue `lp_departed:<SH>` JSON, 2-day TTL) + enqueue `restore_departed`; `restore_departed` also runs in hourly `carrier_sync.run`; restores snapshot statuses where current='Shipped', and sets Shipped→Delivered where track='Delivered' (90d). Returned never inferred (logistics Returned is set by the return flow, not by track status).

Portal: `shipping.submit_manifest(name)` + "Submit manifest" button on Shipments detail (dispatcher/manager, two taps). `close_manifest` still only closes TODAY's draft by design. Past-day submit uses `_prune_manifest_rows(keep_departed=True)` — the default prune drops delivered parcels, which is wrong for a late close. On 2026-10-06 three drafts were open: SH-000289 (10-01, 318), SH-000294 (10-03, 194), SH-000296 (10-05, 648). Related: [alerts-silenced-by-unread](alerts-silenced-by-unread.md).
