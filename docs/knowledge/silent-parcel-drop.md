---
name: silent-parcel-drop
description: "A pick list finishing while one parcel never shipped — the sort wall's window hid it, and retry_awb was a no-op on exactly that population"
metadata: 
  type: project
---

**Found 2026-09-08 from PL-55740.** 16 orders, 15 `Label Printed`, one (`J-005976`, city "Marrakech tamansourt") with no AWB, still `Pending` — yet with a **submitted Delivery Note** (`per_delivered=100`, stock deducted). The system believed it shipped; the box stood in dispatch.

**Correct the scary number:** a first pass counted **142** orders "submitted pick list, no AWB, Pending". Wrong framing — 133 have DNs and are old/cancelled, 9 are cancelled. The live leak is **6 orders in 60 days**. Measure `submitted DN + no AWB + sales status <> Cancelled`, not the logistics status alone.

**Three defects (all in `6cd00f2`):**
1. `picking.sorting_lists` had `HAVING pending > 0` where `pending` counted **only `Label Generated`**. A no-AWB order sits at **`Pending`**, so the whole list dropped off the sort wall once its list-mates printed. 6 lists in 30d vanished that way. Now the window is "not in `_SORT_DONE` (Label Printed/Shipped/Delivered/Not Delivered/Returned) and not Cancelled", plus a `blocked` count. Replayed on prod: **7 lists return, 0 removed**.
2. **`shipping.retry_awb` was a no-op on this exact population.** It re-enqueues `create_delivery_notes_background`, whose `CustomPickList.create_delivery_note_on_submit` first **skips every SO that already has a DN** ("All Sales Orders already have Delivery Notes … Nothing to Create"). Every stuck order has one. The real path is **`CathedisShipping.create_delivery_note_shipment(dn_doc)`** — it writes `custom_awb`, `custom_label_url`, `Label Generated`, downloads the label. New `picking.relabel_order(pick_list, order, city=None)` does city-fix + that call; `retry_awb` now delegates when a DN exists.
3. Multi-piece orders got only a "2/3" toast on the sort wall (`PackStation.vue`) — read as a count of what was just scanned, box taped short. Now a modal lists the owed pieces; any scan dismisses it.

**Cause is NOT only the Arabic city** — and NOT only the city at all (see the prod run below). The first pass classified `Taza` and `Bouskoura` as "valid city, call just flaked"; **both were wrong** — Taza's Address said `had wlad zbair` and Bouskoura's failure was an Italian phone. Classifying on the SO city field produces wrong answers.

`city.suggest_city(order)` scores the 505 accepted cities against the *words* of the order's city (**should read `Address.city`, not the SO field**) (no regex; `_tokens`). Verified: returns `['Marrakech','TAMANSOURT',...]` first.

`city.city_check_queue` does **not** cover these — it is a **pre-pick** queue (7 rows; J-005976 absent).

## Ran it on prod 2026-09-08 — the diagnosis was too narrow

**The carrier reads the city from the linked `Address`, NOT `Sales Order.custom_shipping_city`** — the field the portal shows, filters and validates. That SO field is **EMPTY on 57%** of the last 30 days' orders (5,499/9,726) and **disagrees** with the Address on another 10% (983). `Address.city` is never empty. It is also the sharper predictor: Address city outside the carrier list → **54.9%** get an AWB vs **80.6%** inside (SO field: 74.5% vs 86%).

**Seven stuck parcels, FOUR different causes** — a city picker fixes only one:
| order | carrier said |
|---|---|
| J-005924 | `Ville introuvable: had wlad zbair` (address_line1 IS the city — a douar) |
| #258996 | `Ville introuvable: BROUJ-Settat` |
| J-005827 | Arabic city `السويد` |
| J-005948 | `Ville introuvable: \` — city stored as `"Al Aaroui` with a **leading double-quote** that reached the API as a backslash. Stripping it → shipped |
| SAL-ORD-2026-03016 | `Numero de Téléphone invalide: +393339575381` — **Italian phone**, nothing to do with the city |
| SAL-ORD-2026-02883 | `Exception: Address None not found` — DN has **no shipping address** (SO only has a Billing address) |
| J-005976 | fixed via the new panel (city→Marrakech) → `LD008456607` |

**ee swallows the rejection**: `create_delivery_note_shipment` catches and `log_error`s instead of raising, so `relabel_order`'s `except` never fires and it could only say "no label yet". `_carrier_complaint(dn, since)` now re-reads the Error Log (`importErrors` → `col`/`reason`) and the slot prints it (`cf2e149`).

**Shipped by the repair:** J-005976 (`LD008456607`), J-005948 (`LD008456640`).

## City Check audit 2026-09-08 — same `Pending` blind spot, and the city is NOT the main blocker

`city_check_queue` runs **two** queries and an order on a pick list + `Pending` + no AWB fell through **both**: the pre-pick one excludes anything on a pick list (`docstatus<2`), the in-flow one only accepted `('Picked','Label Generated')`. **57 of 57** such orders appeared on neither. Fixed by adding `Pending` to the in-flow query, fenced to **submitted** lists so live drafts stay out (verified: surfaces the 5 real ones, excludes 46 draft orders).

**MariaDB `TRIM()` strips SPACES ONLY.** A city stored `'Sale\n'` stayed `'Sale\n'` through every comparison — never matched the carrier list, sat as an unmatched town forever, went to Cathedis with the newline attached. **134 addresses/30d** carry `\n` or `\t` inside a valid city (Salé, Eljadida, MARRAKECH, Beni Mellal). `picking._clean_city()` now strips `\r \n \t "` inside `_EFF_CITY`. Verified: **45 orders stop being false "unmatched"**, none newly appear.

**Correction to the premise:** of those 57, exactly **1** has a bad city. What actually breaks pick lists is **stock** — 292 `combined_insert_fell_back` in 30d: 105 TimestampMismatch, 72 `picked quantity > available in warehouse`, 56 `units not available`, 29 empty-combined, 21 stripped rows, 8 item_name.

**Loud but harmless:** `Delivery Note Auto-creation Failed` fires on nearly every submit — **745 in 30d over 744 lists**, 100% TimestampMismatchError — yet only **5 of the 4,577** orders involved lack an AWB. It aborts a trailing `self.save()` after the DNs already exist. Noise, not the cause; do not chase it as the root of no-AWB.

**Role reality:** NO enabled user resolves to `dispatcher`. 5 manager, 2 packer, 2 cs, 84 unset. Saad (`lamdanisaad12@`) = **packer**, and `suggest_city`/`relabel_order` raised PermissionError for him — that, not the UI, is why the repair looked manager-only. Both now accept `_SORT_ROLES`; `city.apply_city()` is the ungated split of `set_shipping_city` so an already-authorised caller isn't re-checked.

Related: [arabic-city-breaks-awb](arabic-city-breaks-awb.md), [picklist-batch-shattering](picklist-batch-shattering.md), [measure-dont-trust-audits](measure-dont-trust-audits.md), [assign-vs-allocated-to](assign-vs-allocated-to.md).
