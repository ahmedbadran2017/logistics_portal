---
name: arabic-city-breaks-awb
description: Shipping city entered in Arabic makes Cathedis AWB/label generation fail — the root cause of no-label parcels
metadata: 
  type: project
---

**A shipping CITY entered in Arabic is the main reason Cathedis fails to generate an AWB/label.** Cathedis matches the city against its own city list (Latin: "Chefchaouen", "Casablanca", …); an Arabic city ("شفشاون") doesn't match → the AWB call fails after the Delivery Note is created, so the SO ends up with a DN but no `custom_awb` / `custom_label_url` / label PDF.

Validated on prod 2026-08-03 (last 14 days, Justyol Morocco, confirmed orders with a submitted DN):
- No-AWB orders: **79% have an Arabic city** (75% Arabic address).
- Got-AWB orders: **4% Arabic city** (20% Arabic address).
So the CITY is the killer (~20×); the street/address in Arabic matters far less (it's free text on the label). Example: J-001872, city "شفشاون".

**Downstream damage:**
- `sort_scan` (picking.py) used to flip the SO to 'Label Printed' on scan-completion WITHOUT checking a label exists — silently sending a label-less parcel to the driver. Fixed (commit 545fcf6): it now returns `noLabel=true`, leaves the status, and PackStation shows the slot amber ("sorted, but no label"). ~9 orders had been mis-flipped.
- `retry_awb` (shipping.py) CANNOT fix these: it re-enqueues `ecommerce_integrations…create_delivery_notes_background`, which SKIPS orders that already have a Delivery Note — and these have a DN without an AWB. So the existing remedy has a gap.

**Prevention built (commit 4406414): City check.** picking._BAD_CITY marks an order's effective city (SO field, else the linked Address — 76% carry it only there) as un-labelable if it's empty, Arabic (_ARABIC_CLASS explicit letter class), or contains digits (phone in the city box). Added to the to-pick pool predicate (both _POOL_WHERE AND the duplicated suggest_batches copy — keep them in sync), so those orders are HELD OUT of the pick pool (verified: 346→327, only Arabic/junk dropped, no clean Latin town). New api/city.py: city_check_queue (blocked=held, warn=unmatched Latin town still pickable), cathedis_cities (searchable list of Latin cities that actually produced an AWB, cached 10min), set_shipping_city (writes SO + Address). CityCheck.vue page, dispatcher/manager. Accepted-city match must be done in SQL (accent/case-insensitive collation) — a Python `.lower()` set membership wrongly flags Fès/Salé/Témara.

**Still lives outside the portal (not done):** the actual AWB (re)generation for an order once its city is fixed — that call is in codx_erp / ecommerce_integrations. retry_awb also can't regenerate for a DN-without-AWB (its job skips orders that already have a DN).

Related: [measure-dont-trust-audits](measure-dont-trust-audits.md), [confirmation-tracking-modules](confirmation-tracking-modules.md).
