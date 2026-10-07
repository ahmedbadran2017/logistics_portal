---
name: orders-without-delivery-notes
description: Exchange (-ex) and J- orders ship with NO Delivery Note; carrier events are Comments on the Sales Order; draft DNs carry printed labels — any engine that reads only documents misreads them
metadata: 
  type: project
---

Measured 2026-09-13 on the live confirmed set (30 days, 8,026 orders): 36 orders delivered, 33 labelled and 13 with the carrier had **no Delivery Note at all** — exchange (`-ex`) orders and `J-` orders get their Cathedis label straight from the Sales Order (`custom_tracking_number`, `custom_logistics_status`, `custom_track_shipment_status`, `custom_delivered_at`). A few parcels sit on a **draft** DN (docstatus 0) with `custom_awb` already set. One Confirmed order was `status = Closed`.

The carrier webhook writes its events as **Comments on the Sales Order**: "Newly created parcel by Justyol" (label), "Shipped to destination hub" / "The parcel is present on Hub…" (handover), "Out for delivery", "Package Delivered" — ~6.5k orders / 45 days, MIN(creation) GROUP BY reference_name costs ~630 ms. `custom_shipped_at` / `custom_picked_at` are empty; `custom_labeled_at` covers 2%; Version rows exist for `custom_logistics_status` changes (Label Generated mostly) but not for the db_set Shipped/Delivered path.

**Why:** the tracking portal's first blocked screen showed a delivered order as "picking for 20 days" (J-003711) because its stage came from Pick List / DN / Shipment joins only. 16 of 73 blocked rows were wrong, all this class.

**How to apply:** derive stages from three witnesses in order — terminal SO stamps, carrier comments + manifest, label (SO awb or DN incl. drafts), pick list — see `shipments._stage_of`. Exclude `so.status IN ('Closed','Cancelled')`. Never trust a DN-only join for exchange/J- flows. Related: [stranded-confirmed-orders](stranded-confirmed-orders.md), [silent-parcel-drop](silent-parcel-drop.md).
