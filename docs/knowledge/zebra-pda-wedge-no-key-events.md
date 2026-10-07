---
name: zebra-pda-wedge-no-key-events
description: "The floor runs Zebra TC26; DataWedge sends scans as committed text, not key events — never build scan handling on keydown/Enter"
metadata: 
  type: project
---

**The device is the Zebra TC26**: 5" HD (720×1280), SE4710 1D/2D scanner,
Android 10 with later releases supported, GMS — with a *Restricted Mode* option
worth remembering if Chrome is ever missing or stuck old, since PWA install from
the menu needs Chrome 108+.

Zebra doesn't publish the density. 720px across a 5" diagonal is ~293ppi, which
falls **between** Android's hdpi and xhdpi buckets, so the TC26 is either
**360 CSS px @ dpr 2** or **411 @ dpr 1.75**. Don't guess: `?scandebug=1` prints
the device's real css size / dpr / Chrome version. Every floor screen is verified
clean at 320, 360 **and** 411, so either way it's covered.

The warehouse scans via **DataWedge Keystroke output**. Its defaults are not
what a web app expects:

- **"Send Characters as Events" is OFF by default** — the barcode's printable
  characters (ASCII 32-126) are committed as a **string** through Android's
  InputConnection. The field fills and **no keydown ever fires**.
- **"Action key character"** = None / Tab / Line feed / Carriage return. On
  `None` there is **no terminator at all**.
- Anything through an Android IME reports keydown as `key="Unidentified",
  keyCode=229`, so Vue's `@keydown.enter` (matches on `e.key`) can never fire.
- Vue's **v-model suppresses model updates while a composition is open**, so the
  ref can be empty while the field visibly holds the scan. Reading the ref in a
  submit handler is how "the SKU shows but nothing happens" happens.

**Rules for any scan field here:**
1. Read `el.value` (the DOM), never the v-model ref, at submit time.
2. Accept a terminator in every form: Enter/Tab key, `keyCode` 13/9,
   `inputType === "insertLineBreak"`, or a CR/LF character in the value.
3. Fall back to a settle timer (~140ms) when no terminator arrives — but only
   for entries that arrived **without** trusted printable key events, or manual
   typing on the laptop gets submitted mid-word.

`ScanInput.vue` backs **nine** stations (pick, pack, manifest, goods-in, move,
count, restock, return receiving, pick lists) — a bug there is a floor-wide bug.

**Debugging:** open any scanning screen with **`?scandebug=1`** — a panel lists
every raw event the device produces. There is no console on a PDA.

Device-side improvement worth making anyway: set Action key character =
Carriage return so scans submit instantly rather than after the settle window.

Fixed 2026-07-16. Related: [measure-dont-trust-audits](measure-dont-trust-audits.md), [logistics-portal-project](logistics-portal-project.md)
