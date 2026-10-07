---
name: attendance-lives-in-hrms
description: "Attendance is Frappe HR's app at /hrms with GPS — the portal only reads it; never build a second writer to Employee Checkin"
metadata:
  type: project
---

**Established 2026-09-09** when the desk block raised "can the team still clock in?".

**They never lost it.** The floor punches in **Frappe HR's own mobile app at `/hrms`** (hrms 15.47.5; `website_route_rules` also maps `/hr/<path>` → `roster`). That is a *website* route, so `deskguard` — which only guards `/app` — never touched it. Proof: every checkin carries **GPS coordinates** (the Desk form records none), and `Route History` for the team is **empty**. 46 Attendance rows in 7 days for the 9 guarded users.

**Never build a second writer.** `Employee Checkin` is what payroll reads. A portal writer would have to re-implement geolocation capture, shift resolution and the checkin→attendance job = two sources of truth for someone's pay.

**What was built instead:**
- `deskguard`: `/app/hr*` → `/hrms` (someone asking for HR gets HR, not the pick floor).
- Sidebar nav supports `item.href` (external); every role's "me" section has an **Attendance** link. One `<template v-for>` renders both kinds so roles.js order = screen order; `isActive` and `navFor`'s hidden-pages filter both key off `i.to`, so an href item is safely ignored by them.
- `api/attendance.py` → `my_status()`, **read-only**, fenced to the Employee whose `user_id` is the session user.

**Rules learned from the real data:**
- Read state from the **LAST log, any date** — not today's. Prod had last logs from **February and August**, and one person who punched OUT this morning against an IN from *yesterday*. Saying "not clocked in" because the date rolled over is a confident lie.
- `out` + stale (previous day) must display as **"not clocked in"**, not "out at 14:48".
- Hours worked = **today only**, pairing IN→OUT; a stray extra IN doesn't restart the clock and an unmatched OUT is ignored — a messy day degrades to a *smaller* number, never a wrong one.
- Use the log's **`time`**, never `creation`: the HR app backdates a late entry (prod: created 11:01 for a 09:01 punch) and `time` is what payroll reads.
- Use `frappe.utils.now_datetime()` (site clock), not SQL `NOW()`/`CURDATE()` — same DB-vs-site skew as [silent-parcel-drop](silent-parcel-drop.md)'s `_site_now`.

Related: [logistics-portal-project](logistics-portal-project.md), [measure-dont-trust-audits](measure-dont-trust-audits.md).
