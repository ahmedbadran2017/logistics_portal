---
name: site-clock-is-istanbul
description: "Every stored timestamp is Europe/Istanbul (UTC+3) while the floor works in Morocco (UTC+1) — subtract 2h for any hour-of-day rule or displayed time"
metadata:
  type: project
---

**Verified 2026-09-09 on prod.** `System Settings.time_zone = Europe/Istanbul`
(UTC+3, the Turkish parent's clock). The business runs in **Morocco, UTC+1**.

```
frappe now_datetime()  22:32:55      <- stored in every creation/modified
DB UTC_TIMESTAMP()     19:32:55
Morocco wall clock     20:32         <- what the floor sees
```

**Every stored timestamp is 2 hours ahead of Moroccan wall-clock time.** Any
hour-of-day analysis or rule ("after 6pm", shift windows, hourly charts) must
subtract 2, and the portal displays these times raw — the attendance chip's
"since 09:12" is 07:12 in Morocco.

**How badly it misled me:** the first pass at "work after 18:00" read **31%**
of decisions; in Morocco time it is **7.0%**. Opposite conclusion.

Day-boundary corruption is negligible *today* only because the team stops
before 22:00 Morocco (= 00:00 stored): measured 0 decisions in stored hours
00:00–01:00 over 60 days. If anyone starts working past 22:00 Morocco, their
work lands on the next day's tally, target, streak and "my day so far".

Not necessarily a misconfiguration — it may be deliberate for the parent —
but it IS a decision Ahmed has to make, not something to silently change.

Related: [attendance-lives-in-hrms](attendance-lives-in-hrms.md), [measure-dont-trust-audits](measure-dont-trust-audits.md).

**Third clock (2026-10-06):** MariaDB `NOW()` = UTC (`@@system_time_zone` UTC), stored timestamps = Istanbul. Any SQL `DATE_SUB(NOW(), INTERVAL n HOUR)` window is 3h too wide; 128 NOW() uses across logistics_portal/api (confirmation 21, contact_center 19, audit 11…). Bind the site clock instead (`velocity._site_now()` pattern; pulse fixed in 31eabd6). Systemic fix (session time_zone or sweep) proposed, not done. Also: the portal header "Live" clock is the VIEWER's browser time (Ahmed browses from Istanbul), not floor time.
