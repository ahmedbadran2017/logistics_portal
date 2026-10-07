---
name: logistics-erpnext-fields
description: "Key ERPNext custom fields/doctypes for the Justyol logistics cycle (Pick List, Sales Order, Delivery Note, Shipment, Return Shipment)"
metadata: 
  type: reference
---

ERPNext custom fields backing the Justyol logistics cycle (verify still present before relying on them). Project: [logistics-portal-project](logistics-portal-project.md).

**Pick List:** `custom_assigned_picker`(Link User), `custom_logistics_status`(Pending/Partially Shipped/Shipped), `custom_shipped_percentage`, `custom_items_count`, `custom_total_quantity`, `custom_scan_barcode_sku`, `scan_mode`, `custom_errors`. Pick List Item: `custom_sku`, `custom_supplier`. Picking timing = creation→modified.

**Sales Order (58 custom fields):** `custom_logistics_status`(Pending/Picked/In transit/Received/Label Generated/Label Printed/Shipped/Delivered/Returned), `custom_sales_status`(Pending/Confirmed/Did not Answer/Follow Up/Cancelled/On Hold/Not Delivered/Duplicated), `custom_allocated_to`(Link User), `custom_apply_assignemt`, `custom_awb`, `custom_label_url`, `custom_tracking_number/url/company`, `custom_track_shipment_status`(Pending/Picked up/In Transit/Out For Delivery/Delivery Exception/Return/Delivered/Failed Attempt), `custom_expected_ship_date`, `custom_dropshipper`, `custom_channel`, `custom_shipment_delivery_logs`(HTML).

**Delivery Note:** `custom_sla_status`(""/On Track/At Risk/Breached/Delivered/Delivered Late/Returned), `custom_sla_days_remaining`(Int), `custom_expected_delivery_date`(Date), `custom_return_shipment`(Link Return Shipment), `custom_awb`, `custom_track_shipment_status`, tracking + label fields. Naming MAT-DN-YYYY-#####.

**Shipment** (standard ERPNext doctype, SH-000###): daily handover manifest. pickup=Company (Justyol/SoftPark Ain Sebaa) → delivery_to=carrier (e.g. CATHEDIS). Child `shipment_delivery_note` holds ~300 DNs. Has pickup_date, value_of_goods, status Submitted.

**Return Shipment** (RET-26-#######): 163 docs, status Returned; linked from Delivery Note.custom_return_shipment.

MCP server id for this ERPNext: `22f16c59-34e4-41d3-b3a9-5ea947dfcc3c`.
