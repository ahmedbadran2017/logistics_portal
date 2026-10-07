---
name: backdated-admin-recos
description: "854 Administrator Stock Reconciliations (posting_time 23:59, mostly backdated to Apr–Jul) run from bench console in bursts; one proven stock DUPLICATION (TKT-2608-3629783); who runs the script = unanswered"
metadata: 
  type: project
---

**Discovered 2026-08-27 investigating Hub Ticket TKT-2608-3629783 ("Duplicated of Quantity").** The portal Move Stock was innocent — STE-09654 (200u Receiving→D1C, 24/08 14:46) executed perfectly. The duplication came from **MAT-RECO-2026-03506**: created 14:44 by **Administrator** from a STALE snapshot (recorded current_qty=0 while the bin held 200), **posted at 23:59** — so it re-stated Receiving Zone back to 200 AFTER the move, creating 200 phantom units. DNs then shipped ~13 units against the phantom (pickers sent to an empty zone; the pieces physically sat on D1C).

**The pattern:** 854 submitted Stock Reconciliations, owner=Administrator, posting_time='23:59:00', in three bursts — 21/08 (42), 24/08 (407), 26/08 (405, last at 14:59, ~6 docs/sec) — i.e. a **bench-console bulk script, not a cron** (no matching Scheduled Job Log). **851 of 854 are backdated to Apr–Jul 2026**; lines concentrate on Return Zone (316) and Receiving (249) — looks like a "restore lost returns/receiving stock" project running on stale data. Same-day race proven only once (the ticket case, 2 racy lines), but every backdated reco reposts all later SLEs and can silently shift current balances.

**Why the mechanism is poison:** a reco created at time T from a snapshot but POSTED later (23:59 or a past date) overwrites every legitimate movement between snapshot and posting position. Any bulk-reco fix MUST post at now-time from a fresh snapshot.

**Open question (asked Ahmed, unanswered):** who runs the script? If not him, someone with Administrator console access (ties into [measure-dont-trust-audits](measure-dont-trust-audits.md) and the System Manager cleanup). Next burst will mint new duplications.

**Ticket resolution:** replied on the Hub Ticket as Ahmed (comment n7n8gcq8cf) — move correct, reco at fault, action = physically count item 9135229141246 in D1C. + Receiving Zone and post via portal Cycle Count. Ticket left Open pending the count.
