---
name: measure-dont-trust-audits
description: Confirmed by experience on this repo — audit findings and my own tooling both lie; measure on production before acting
metadata: 
  type: feedback
---

Ahmed's standing rule "validate on PRODUCTION not dev" earns its keep beyond
data. On 2026-07-16 an audit produced a confident, well-argued finding list, and
measuring changed the conclusion three times:

- **"Unbounded derived tables materialise 250k rows per page load"** — false.
  The rows query it feeds runs in ~1.3ms; bounding it made things **slower**.
  The real cost was those joins being attached to COUNT queries that read no
  column from them. Dropping them there: ~3× faster, identical answers.
- **"Comment.reference_name is unindexed, add an index"** — false. Frappe already
  ships `reference_doctype_reference_name_index`. `SHOW INDEX` settled it.
- **"custom_awb is unindexed"** — true, and worse than claimed. `EXPLAIN` gave
  `type=ALL, key=NULL, rows=111,635` and 90.8ms **per parcel scanned**, with an
  operator standing at the handover station.

**My own tooling lied too:** a grep for "does this locale key exist" matched the
leaf name under any namespace and reported keys as present that `t()` could never
resolve — resolve by full path instead. A regex over `<button ...>` silently
skipped every button whose attributes contain `>` (`:disabled="page >= total"`).
And `getComputedStyle` after setting `data-theme` by hand reads nothing useful:
the app's own watcher reverts it. Use the app's real toggle.

**Why:** a plausible mechanism is not a measurement, and a fix aimed at the wrong
mechanism can make things worse while looking like diligence.

**How to apply:** before changing anything on a perf or correctness finding, run
the exact query on prod, `EXPLAIN` it, and time old vs new. Report what the
measurement killed, not just what it confirmed.

Related: [dn-item-fanout-trap](dn-item-fanout-trap.md), [logistics-portal-project](logistics-portal-project.md)
