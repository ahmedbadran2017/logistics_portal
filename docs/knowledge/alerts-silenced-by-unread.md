---
name: alerts-silenced-by-unread
description: shipments._emit skipped any alert with ONE unread row of the same title at any age — every floor alert paged once (mid-Sept) then went silent; fixed 8232c7d (24h window)
metadata:
  type: project
---

Found 2026-10-02 chasing 4 parcels stuck 6 days after the sort wall (#261679, #261860, #262169, SAL-ORD-2026-03576 — sorted by Ossama, never packed/manifested, never on any Shipment; siblings on the same lists were manifested within 30 min).

- The shortfall WAS detected (comments on PL-56396/PL-56346 at SH-000284 close, 09-29) but `shipments._emit` returned early because an unread "manifest closed with parcels left behind" row from 09-15 existed. Same for ~all Notification Log alerts with `lp-i18n` body: each fired once 09-14..09-21 and never again. Fix: unread check limited to last 24h.
- `_record_shortfall` ran only from portal `close_manifest` (today's draft only); Mehdi submits most manifests from Desk next noon → now `doc_events Shipment.on_submit` → `shipping.on_manifest_submit`.
- velocity `labelledStale` aged from so.creation → now from last sort/pack scan (`_LABEL_SINCE`); `custom_labeled_at` is empty on 413/430 Label Printed orders because the sort wall uses db.set_value (no stamp hook).

**How to apply:** when an alert "should have fired", check Notification Log for an old unread same-subject row before assuming the detector failed. Related: [silent-parcel-drop](silent-parcel-drop.md), [desk-decisions-leave-no-portal-fields](desk-decisions-leave-no-portal-fields.md).
