---
name: stop-left-row-on-picklist
description: Stop (cancel while picking) left the row on the pick list; the PL submit labelled it anyway — fixed 9182c3a (drop at submit + Pulse drill-down)
metadata:
  type: project
---
ecommerce_integrations creates DN + Cathedis AWB for EVERY order on a pick list at submit, never asking custom_sales_status. stop.request_stop (mode "stop") only flips the status + comment, so an order cancelled mid-picking got a label 30 min later (#264068/PL-56599, J-010521/PL-56601, 2026-10-06; 5 since 09-22, SAL-ORD-2026-03568 In Transit).
Fix 9182c3a: overrides/pick_list.PickList.validate drops stop.stopped_set() orders when _action=="submit"; retry_awb refuses stopped; Pulse excludes cancelled-unmanifested from door counts + pulse.list_orders drill-down.
Still open (needs Ahmed's OK, prod writes + carrier): cancel the 4 Pending DNs/AWBs (#264068, J-010521, J-010023, #260243), recall SAL-ORD-2026-03568.

**Why:** the sort wall refused the piece, so the list sat "stuck at Packed" forever and a pickup was booked for a parcel nobody sends.
**How to apply:** any new step that creates DN/AWB must ask picking.is_stopped / stop.stopped_set. Related: [cancelled-orders-resurrect](cancelled-orders-resurrect.md), [site-clock-is-istanbul](site-clock-is-istanbul.md).
