---
name: desk-decisions-leave-no-portal-fields
description: "Portal-only fields (custom_next_call_at, custom_call_attempts, Confirmation comments) are empty on every Desk decision — any portal logic keyed on them silently excludes ~90% of the work"
metadata:
  type: project
---

**Found 2026-09-09 auditing the confirmation team's day.** The two trails are
**disjoint** (verified: 0 of 39 portal decisions also left a Version row):

- **Portal** `act()` writes a `Confirmation: …` Comment, `custom_next_call_at`,
  `custom_call_attempts` — and **no Version row**.
- **Desk** writes a **Version row** — and none of those three fields.

Anything keyed on a portal-only field therefore sees only portal work. Measured
that day: **39 portal decisions vs 299 by named agents in the Desk** (plus 192
by `Administrator` = the automation, `_AUTOMATION_USERS`). So ~12% of human
decisions.

**The bug this caused:** `next_order` / `next_up` defined "due" as
`custom_next_call_at IS NOT NULL AND <= now`. **127 of the 140 retry-status
orders in hand had no timer** (105 Did not Answer, 22 Follow Up), all with 0
attempts, 36 past 72h, oldest 14 days. Workspace offered the two agents
carrying that queue **3 and 2 orders while 119 sat unreachable in their own
tabs**. Self-feeding loop: work in the Desk → no timer → Workspace empty → go
back to the Desk. Fixed by one shared `_DUE`/`_DUE_AT` =
`COALESCE(custom_next_call_at, creation)`, matching the expression the board's
retry tabs already window on, with `_PARKED` still excluded.

**Watch for the same class elsewhere**: first-call SLA, "never called" counts,
call-attempt histograms and anything reading `custom_call_attempts` are all
blind to Desk work in the same way (131 of 144 live orders showed 0 attempts).

`resolve_role` is NOT the blocker for portal adoption — it falls back to
`Employee.department`, and all nine confirmation agents resolve to
`confirmation` and can open the workspace even though only ONE has
`custom_logistics_role` set. Habit, not permissions.

Related: [assign-vs-allocated-to](assign-vs-allocated-to.md), [confirmation-tracking-modules](confirmation-tracking-modules.md),
[stale-onhold-pile](stale-onhold-pile.md), [desk-elimination-progress](desk-elimination-progress.md).
