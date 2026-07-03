# Handoff: Justyol Logistics Portal

> Warehouse & fulfillment operations portal for **Justyol** (Morocco-first e‑commerce, COD, carrier Cathedis).
> Role-aware web app: one codebase serves five operational roles across desktop and a mobile handheld-scanner experience, in **English / French / Arabic (RTL)**.

---

## Overview

The Justyol Logistics Portal is the operational cockpit for a Casablanca fulfillment center (**SoftPark Aïn Sebaâ**). It covers the full order lifecycle that today lives across ERPNext doctypes — **Sales Order → Pick List → Delivery Note → Shipment → Return Shipment** — plus inventory (bin/zone management, cycle counting, receiving, re‑slotting), team performance & incentives, SLA governance, COD cash reconciliation, and carrier management.

It is **role-aware**: the same shell renders a different navigation tree, landing page, and (for the Picker) a completely different device form‑factor, depending on who is logged in. A floating **"View as role"** switcher exists only because this is a prototype — in production the role comes from the authenticated user.

The design's spine is **Capture → Reflect → Audit**: capture work as it happens on the floor (scans, assignments, counts), reflect it into live dashboards and performance, and make every state auditable (SLA breaches, COD variances, stock variances).

---

## About the Design Files

**The files in this bundle are design references created in HTML/React-via-Babel — high-fidelity prototypes showing intended look and behavior, not production code to ship directly.**

They run entirely in the browser from CDN scripts (React 18 UMD + Babel standalone + Tailwind CDN) with **all data mocked** in `logistics/data.jsx`. The task is to **recreate these designs in the target codebase's real environment** — wiring each screen to the live ERPNext / Frappe backend and its actual doctypes — using the target app's established framework, component library, state management, and data-fetching patterns.

Where this prototype fakes a value (a countdown, a KPI, a scan result), production must read it from ERPNext. Every action button that shows a success toast (e.g. "assigned", "labeled", "posted") maps to a real doctype write — those are flagged throughout this document.

If no frontend environment exists yet, a sensible target is **React + TypeScript + Tailwind**, which maps 1:1 to what's here.

---

## Fidelity

**High-fidelity (hifi).** Final colors, typography, spacing, interaction patterns, empty/loading/error states, and animation timings are all specified and should be recreated pixel-faithfully using the codebase's existing primitives. The one deliberately "prototype-only" affordance is the **role switcher** (production keys off auth). Charts here are lightweight inline SVG sparklines/bars — production may substitute the app's charting library as long as the visual weight matches.

---

## Tech Stack (prototype) vs. Target

| Concern | Prototype | Recreate as |
|---|---|---|
| Rendering | React 18 UMD + Babel `text/babel` in-browser | Your app's build pipeline (Vite/Next/etc.) |
| Module sharing | Every component assigned to `window.*`; loaded via ordered `<script>` tags | Real ES module imports |
| Styling | Tailwind CDN + CSS variables for accent ramp | Your Tailwind config / design tokens |
| State | React `useState` in a single root `App` | Your router + state layer; role/lang from auth/i18n context |
| Data | Mock objects in `logistics/data.jsx` | ERPNext REST/RPC (`frappe.client`, report queries) |
| i18n | Hand-rolled `STRINGS` dict + `makeT(lang)` | Your i18n framework (keys map 1:1) |
| Icons | `I.*` set from shared `frontend/v2/primitives.jsx` | Your icon set (Lucide-equivalent) |

---

## Design Tokens

### Color — neutrals (warm "stone" ramp)
The entire UI is built on Tailwind's **stone** scale (warm grey), never pure/cool grey.
- Page background: `#f5f5f4` (stone‑100) / surfaces `#ffffff`
- Text: `#1c1917` (stone‑900) primary · `#44403c` secondary · `#78716c` muted · `#a8a29e` faint
- Borders/rings: `stone-200/70` hairlines, `stone-100` dividers

### Color — accent (themeable, CSS variables)
Accent is a full 50→900 ramp exposed as `--accent-50 … --accent-900`. Default is **Rust**. The Tweaks panel can swap the ramp live; components only ever reference `var(--accent-*)`, never hard-coded accent hex.

| Accent | 500 | 600 | 700 |
|---|---|---|---|
| **Rust** (default) | `#d45d3e` | `#c4492a` | `#a33a22` |
| Indigo | `#6366f1` | `#4f46e5` | `#4338ca` |
| Emerald | `#10b981` | `#059669` | `#047857` |
| Violet | `#8b5cf6` | `#7c3aed` | `#6d28d9` |
| Teal | `#14b8a6` | `#0d9488` | `#0f766e` |

Full Rust ramp: `50 #fdf5f3 · 100 #fbe6e0 · 200 #f6ccbf · 300 #eea894 · 400 #e17f62 · 500 #d45d3e · 600 #c4492a · 700 #a33a22 · 800 #852f1e · 900 #6d291d`

### Color — semantic status
Two parallel vocabularies, each a `{text, bg, ring, dot}` Tailwind quad (see `STAGE` and `SLA` maps in `data.jsx`):

**Stage** (`custom_logistics_status` flow): pending=stone · picking=amber · picked=orange · labelgen/label=violet · shipped/delivered=emerald · transit=cyan · exception=orange · returned/oos=rose · partial=amber

**SLA**: ontrack=emerald (`#10b981`) · atrisk=amber (`#f59e0b`) · late/breached=orange→rose · returned=stone. SLA meters interpolate green→amber→red by remaining fraction (`≥0.66` green, `≥0.33` amber, else red).

**Channel**: Shopify=emerald · YouCan=violet · Landing=amber · Manual=slate · WhatsApp=green.

### Typography
- **Sans:** `Inter` (weights 400/500/600/700), with `Noto Sans Arabic` as the Arabic face (auto-swaps when `dir="rtl"`).
- **Mono:** `JetBrains Mono` — used for all IDs, codes, AWBs, SKUs, bin codes, and tabular figures.
- Feature settings: `"cv11","ss01"`; numbers use `tabular-nums` everywhere they align in columns.
- Tight display headings: `letter-spacing: -0.01em` (`tracking-tight`) / `-0.02em` (`tracking-tighter`).
- Type scale in use (px): 10 / 10.5 / 11 / 11.5 / 12 / 12.5 / 13 / 13.5 / 14 / 15 / 16 / 18 / 19 / 20 / 22 / 26 / 34 / 44. Body default 13px; sidebar nav 13px; section titles 13.5–14px; page titles 19–22px; hero numerals 22–44px.

### Spacing, radius, shadow
- Spacing follows Tailwind's 4px base; card padding 16px (`p-4`), tight lists `py-1.5/py-2.5`.
- **Radius:** controls/buttons `rounded-lg` (8px) / `rounded-md` (6px); cards `rounded-xl` (12px); modals & the phone screen `rounded-2xl`→`rounded-[36px]`; pills/badges `rounded-md`; avatars/dots full.
- **Shadows** (soft, low-spread): cards `0 1px 2px rgba(0,0,0,0.03)`; hover lift `0 4px 16px -6px rgba(0,0,0,0.1)`; drawers `0 0 60px -10px rgba(0,0,0,0.3)`; floating panels `0 24px 64px -16px rgba(0,0,0,0.22)`.
- Focus ring: `2px solid var(--accent-500)`, offset 2px.

### Motion
Named keyframes, all easing `cubic-bezier(0.16, 1, 0.3, 1)`: `fade-in` 220ms, `scale-in` 240ms, `menu` 140ms, `toast-in` 280ms, `drawer-in` 280ms (RTL mirror `drawerInL`). **Important:** entrance keyframes keep `opacity:1` at 0% (translate/scale only) so content is never invisible if animations are paused (print/reduced-motion/offscreen). Preserve this rule.

### Density & theme (global data-attributes on `<html>`)
- `data-density="comfortable|compact"` — compact drops root font-size to 13.5px.
- `data-theme="light|dark"` — dark mode is a **curated utility remap** (see `<style>` in the HTML): stone surfaces → `#292524/#1c1917/#3a3530`, text ramp inverted, rings → `#44403c`. In a real app, implement dark mode via your token system rather than the `!important` overrides used here.
- `dir="rtl"` + `lang` set on `<html>` drive Arabic layout mirroring.

---

## App Shell & Layout

### Desktop shell (`DesktopShell`, in `shell.jsx`)
- **Sidebar** — fixed `236px`, white, `border-e` hairline. Top: Justyol logo lockup + "LOGISTICS" tag. Below: a `⌘K` search launcher button. Then the **role-specific nav** grouped into labeled sections. Bottom: the **role switcher** card.
- **Top bar** — `52px`, translucent (`bg-white/80 backdrop-blur`). Left: a brand-accent role badge + the current page's home label. Right: **LiveClock** (ticking `HH:MM:SS`, pulsing green dot), **LangSwitcher** (EN/FR/ع segmented), and a **notification bell** with unread count badge.
- **Main** — scroll container; each page renders inside.
- Logical properties (`ps/pe/ms/me/border-s/e`, `start/end`) are used throughout so RTL mirrors correctly. Keep this.

### Mobile stage (`MobileStage`)
The Picker role renders **not** in the sidebar shell but as a centered **iPhone-style device frame** (`PhoneFrame`, 390×800, notch, status bar) on a soft gradient backdrop, with the role switcher floating top-start. This is the handheld-scanner experience.

### Global overlays (mounted at root, `App`)
- **Command palette** (`CommandPalette`) — `⌘K`/`Ctrl+K` toggles; fuzzy jump to pages & orders.
- **Notification center** (`NotifCenter`) — right (LTR) / left (RTL) slide-over listing audit alerts.
- **Order timeline drawer** (`OrderTimelineDrawer`) — quick-look order lifecycle.
- **Confirm dialog** (`ConfirmDialog`) — destructive-action guard.
- **Offline banner** (`OfflineBanner`) — shows queued-writes count when the "connection" tweak is offline (models flaky warehouse wifi; production should implement real optimistic-queue behavior).
- **Toast** (`Toast`) — transient success/info, bottom-center, auto-dismiss 3s.
- **Tweaks panel** — prototype-only; see "Tweaks" section. Not part of production.

---

## Roles, Navigation & Landing Pages

Roles are defined in `LG_ROLES`; nav trees in `LG_ROLE_NAV` (`shell.jsx`). Each role has a `home` route it lands on.

| Role | Person (mock) | Device | Home | Navigation |
|---|---|---|---|---|
| **Manager / Supervisor** | Sara Benali | desktop | `cockpit` | **Overview:** Cockpit · Floor Board · SLA · Alerts — **Fulfillment:** Orders · Waves · Pick Lists · Pack · Shipments · Routes · Tracking · Exceptions · Returns · COD · Carriers — **Inventory:** Warehouse · Stock · Reports — **Team:** Team · Roster · Bonus · Settings |
| **Dispatcher** | Anass Mouakkal | desktop | `assign` | **Operations:** Assignment · Orders · Pick Lists — **Inventory:** Warehouse · Stock — **Me:** Tracking · My Performance |
| **Picker** | Marouane El Messaoudi | **mobile** | `queue` | **Operations:** My Queue · My Performance |
| **Packer / Shipper** | Reda ZAARI | desktop | `label` | **Operations:** Label · Manifest · Shipments · Carriers — **Me:** My Performance |
| **Returns** | Nadia Berrada | desktop | `returns` | **Operations:** Returns · Tracking — **Me:** My Performance |

Access control is by nav composition here; in production enforce it server-side per role, not just by hiding nav.

---

## Route → Component Map

Every route (the `page` state in `App.renderPage()`) and the component + file that renders it. Use this as your screen inventory.

| Route key | Component | File | Purpose |
|---|---|---|---|
| `cockpit` | `Cockpit` | cockpit.jsx | Manager floor cockpit: breach banner, today's-flow strip w/ cutoff countdown, same-day/breach/at-risk/in-transit KPIs, 9-stage pipeline, team leaderboard |
| `andon` | `FloorBoard` | floor.jsx | Big-screen live throughput / Andon board |
| `sla` | `SlaBoard` | analytics.jsx | SLA governance: per-stage SLA settings, breaches, at-risk queue |
| `alerts` | `NotificationsPage` | ux.jsx | Full alerts/notifications page |
| `orders` | `OrdersList` | workspaces.jsx | Master orders table: channel/stage/SLA filters, search |
| `order` | `OrderDetail` | order.jsx | Full order page (ERPNext Sales Order analog): items w/ product images, connections to Pick List / Sales Invoice / Delivery Note, activity log + notes |
| `waves` | `WavePicking` | floor.jsx | Scheduled batch wave releases |
| `picklists` | `PickLists` | workspaces.jsx | Pick List queue + manual create modal |
| `picklists → detail` | `PickListDetail` | picklist.jsx | Inside a pick list: line items, bins, zone routing |
| `picklists → autopilot` | `AutopilotPage`, `PickAutopilot` | picklist.jsx | **Smart auto pick-list** AI agent: groups orders by shared SKU/zone, assigns, monitors; rules + activity log |
| `picklists → smart create` | `SmartPickModal` | picklist.jsx | Smart grouping preview before committing a batch |
| `pack` | `PackStation` | floor.jsx | Scan-verify packing station: box suggestion, item scan check |
| `label` / `manifest` | `Packer` | packer.jsx | Packer label print + manifest tabs (`initialTab`) |
| `shipments` | `Shipments` | workspaces.jsx | Shipment list + full shipment page (Delivery Note / AWB scan flow) |
| `routes` | `RoutesBoard` (+`RouteDetail`) | returns.jsx | Delivery trips: driver, zone, stops, live progress |
| `tracking` | `Tracking` | returns.jsx | Carrier parcel tracking board + parcel timeline |
| `exceptions` | `ExceptionCenter` | ops.jsx | Delivery exceptions triage |
| `returns` | `Returns` | returns.jsx | Return Shipment queue: AWB scan → item scan → ready-for-return states |
| `cod` | `CODReconcile` | ops.jsx | COD cash: carrier collects → remits reconciliation |
| `carriers` | `CarrierScorecard` / `Carriers` | ops.jsx / workspaces.jsx | Carrier performance scorecards + routing suggestions |
| `warehouse` | `Warehouse` | warehouse.jsx | Physical floor map + density heatmap, cycle count, receiving, re-slot, zone owners |
| `stock` | `Stock` (+`ItemDetail`) | analytics.jsx | Stock/SKU list + item detail |
| `restocking` | `Restocking` | analytics.jsx | Reorder alerts (days-of-cover) + bin transfers |
| `analysis` | `StockAnalysis` | analytics.jsx | ABC analysis, slow/fast movers |
| `reports` | `Reports` | analytics.jsx | Exportable operational reports |
| `team` | `TeamAdmin` (+ member profile) | team.jsx | Team admin: members, caps, tiers, status |
| `bonus` | `BonusBoard` | team.jsx | Incentive/bonus engine board |
| `roster` | `Roster` | team.jsx | Shift roster |
| `settings` | `LogisticsSettings` | settings.jsx | SLA thresholds, cutoff, capacity settings |
| `performance` | `TeamPerformance` | returns.jsx | Personal performance (coaching tone) |
| `queue` (mobile) | `PickerApp` | picker.jsx | Picker mobile: urgency-sorted queue → scan-to-complete → next |

---

## Key Screens — detail

### 1. Manager Cockpit (`cockpit`) — the hero
- **Breach banner** (full-width, rose): count of breached + at-risk orders, "Breached orders →" action.
- **Today's flow strip**: four big numerals — Orders in / Shipped / Printed / To ship — with a **live cutoff countdown** chip ("Past cutoff +HH:MM:SS · 14:00") and a same-day progress bar ("143 / 328 before 14:00 cutoff", % at end).
- **KPI row** (4 cards): Shipped same-day (%), SLA breaches, At risk now, In Transit — each with trend arrow + inline sparkline. Numbers animate up via `CountUp` (foreground only; falls back to final value).
- **Pipeline** (9 stages): horizontal bars per stage (Pending→In Transit), count inside the bar, MAD value at end, colored by the `STAGE` map.
- **Team leaderboard**: ranked pickers w/ avatar, orders count, avg pick time, SLA %, sparkline; #1 gets a ⭐.
- Layout: max-width container, `px-6 py-6`; KPI row is a 4-col grid collapsing to 2 on small; pipeline + leaderboard sit in a 2-col split.

### 2. Orders list (`orders`)
Master table with channel badges (Shopify/YouCan/Landing/Manual), stage + SLA badges, customer, city, value (MAD, mono tabular), item count. Filter chips + search. Row click → `OrderDetail`.

### 3. Order detail (`order`)
The ERPNext **Sales Order** analog. Header with order id (mono), customer, channel, value. **Line items with product images**. A **Connections** panel linking the Pick List, Sales Invoice, and Delivery Note (mirrors ERPNext's linked-documents pattern). Right/bottom: **Activity log** with the ability to **add a note** (Frappe-style timeline comment). Two-column: documents/connections above, activity log below.

### 4. Pick Lists + Smart Autopilot (`picklists`)
- List of pick lists with status, picker, zone, line/unit counts.
- **Manual create** modal (fallback when autopilot is off).
- **Autopilot**: the flagship efficiency feature. `autoPickGroups()` batches the pending pick pool by shared SKU and bin-zone/aisle to minimize walking; an **AI agent** view shows it generating daily batches, assigning pickers, monitoring execution, and emitting alerts, with a rules panel and live activity log. Recreate the grouping logic server-side; the UI visualizes batches, walking saved, and per-batch stats.
- Pick list detail: line items with bin codes, zone routing, serial flags.

### 5. Pack Station (`pack`)
Scan-verify packing: scan order → suggested box (from `BOXES` by weight/dims) → scan each item to verify against expected → complete. Big scan affordance, per-item check state (emerald when scanned), progress bar.

### 6. Shipments (`shipments`)
Shipment/Delivery Note list and full shipment page. The real flow: a Shipment is created, then the delivery person **scans the AWB barcode on the Delivery Note** and it's recorded. Return Shipment has its own state machine: Draft → AWB Scanning → Item Scanning → Ready for Return → Returned.

### 7. Warehouse (`warehouse`)
Physical **floor-plan grid** with a **density heatmap** (bin occupancy), plus tabs/sections for **cycle counting** (weekly/daily count plans with variance capture), **receiving** (inbound ASN / purchase receipt to dock), **re-slotting** (move SKUs slow↔fast zone), and **zone owners** (team member responsible per zone). Bins use real codes (e.g. `X1C - JM`) grouped into zones (FAST/SLOW/Accessory/Cosmetic/MU/Textile).

### 8. Picker mobile (`queue`, in `PhoneFrame`)
- **Queue view**: greeting, three stat tiles (today count / SLA hit-rate / next-due minutes), then order cards sorted **most-urgent-first** (breached→at-risk→on-track), each with order id, SLA badge, customer, zone, value, item count, and a dark circular "go" button.
- **Scan-to-complete**: tap an order → scan items one by one (big scan target, per-item check, progress) → completion → auto-advance to next.
- Bottom tab bar: My Queue / My Performance. Performance uses a **coaching tone** (encouraging, goal-oriented) — this is a tweakable dimension (coaching vs neutral).

### 9. SLA board (`sla`)
Per-stage SLA settings (`LG_SLA_SETTINGS`: cutoff 14:00, same-day target 90%, delivery 3 days, max pick 2 / label 1 / ship 3), breach list, at-risk queue.

### 10. COD reconciliation (`cod`)
Carriers collect cash on delivery, then remit. Screen reconciles collected vs expected vs fees, flags variances. (A parallel, deeper COD cash-lifecycle module also exists in the sibling Accounting portal — coordinate account postings with finance.)

---

## Interactions & Behavior

- **Role switch** (`changeRole`): sets role, jumps to that role's `home`, closes notifications. *Prototype affordance — production uses auth.*
- **Language switch**: sets `lang`, updates `<html lang>` + `dir`; Arabic → full RTL mirror + Arabic font. Keys resolve via `makeT(lang)` with EN fallback.
- **⌘K / Ctrl+K**: toggles command palette (global keydown).
- **Notification bell**: opens slide-over, zeroes unread count.
- **Toasts**: every mutating action (assign, generate label, add to manifest, post, complete pick, count submit) fires a success toast and auto-dismisses in 3s. **Each is a real backend write in production.**
- **Confirm dialog**: guards destructive actions.
- **Offline mode** (tweak): shows a persistent banner with queued-writes count — model for real optimistic queueing on flaky floor wifi.
- **Live clock**: ticks every second (`setInterval`), pulsing green "Live" dot — signals real-time data.
- **CountUp**: KPI numerals animate from 0 to target on mount (foreground only; guaranteed to show the final value).
- **Hover**: cards lift (ring darkens + soft shadow); nav items get `stone-100` wash; buttons per the shared primitive states.
- **Empty states**: e.g. Picker queue clear → celebratory empty state ("Queue clear — nice.").
- **Responsive**: desktop-first (dense operational UI). KPI grids collapse 4→2; tables hide secondary columns on small widths (`hidden md:table-cell`). The Picker is intrinsically mobile.

---

## State Management

The prototype holds everything in one root `App`:
- `role`, `lang` (→ `dir`, `t`), `page` (router), `orderNo`/`tlOrder` (detail targets), `cmdOpen`, `notif`/`unread`, `confirmState`, `toast`, plus `tweaks`.
- Context (`LgContext`) exposes `{ t, lang, dir, setLang, openOrder, openOrderPage, go, openCmd, askConfirm }` to all pages.

**In production**, replace with: a real **router** (route per screen), **auth/role** context, an **i18n** provider, server state via your data layer (React Query/RTK Query/etc.), and per-screen local UI state. `page`-based `switch` → real routes; `openOrderPage(no)` → navigate to `/orders/:no`.

---

## Data Model (mock → ERPNext mapping)

All mock data is in `logistics/data.jsx`, deliberately shaped to match live **ERPNext / Frappe** doctypes at `admin.justyol.com`. Wire each to its source:

| Mock (`LG_DATA.*` / `LG_*`) | ERPNext doctype / source |
|---|---|
| `ORDERS`, `PICK_POOL` | Sales Order (+ items), `custom_channel`, `custom_logistics_status` |
| `PICKLISTS`, `autoPickGroups()` | Pick List (+ locations) — grouping is custom logic |
| `PARCELS`, `TRACK_STATES`, shipments | Delivery Note / Shipment, AWB, carrier status |
| Returns | Return Shipment doctype state machine |
| `WAREHOUSE_MAP`, `BIN_ZONE`, bins | Warehouse / Bin (" - JM" suffix), zones |
| `CYCLE_COUNTS`, `CYCLE_VARIANCES`, `COUNT_PLAN` | Stock Reconciliation / count plan |
| `INBOUND` | Purchase Receipt / ASN |
| `ABC_CLASSES`, `REORDER_ALERTS`, `BIN_TRANSFERS` | Bin qty, reorder levels, Stock Entry (transfer) |
| `TEAM`, `TEAM_MEMBERS`, `CAPS`, `TIERS` | User / Employee (real emails included) |
| `BONUS`, `computeBonus()` | Custom incentive logic |
| `SLA_SETTINGS` | Custom settings |
| `COD` | COD collection/remittance |
| `CARRIER_SCORES`, `ROUTING_SUGGESTIONS`, `ROUTES` | Carrier / Trip data |
| `LEADERBOARD`, `ANDON`, `PIPELINE` | Aggregations/reports over the above |

Real anchors already in the data: warehouse **SoftPark Aïn Sebaâ** (Casablanca), carrier **Cathedis** (+ Sendit, Ozonexpress), **14:00** cutoff, currency **MAD** (`fmtMAD` → `en-US` grouping, no decimals), channels **Shopify 82% / Landing 7% / YouCan 5% / Manual 1%**, real team members & emails, real bin codes and naming series (`#`, `YC-`, `J-`, `SAL-ORD-`).

---

## Internationalization

- Three locales: **en**, **fr**, **ar**. `STRINGS[lang]` holds a flat key dict; `makeT(lang)` returns `t(key)` with English fallback. `_dir` per locale drives `ltr`/`rtl`.
- Arabic is a **full RTL** experience: layout mirrors (logical CSS props already used), font swaps to Noto Sans Arabic, nav/labels translated. See screenshot `10-arabic-rtl.png`.
- Keys are namespaced (`nav.*`, `role.*`, `c.*` common, `s.*` stage, `sla.*`, `t.*` tracking, plus page groups). Map these 1:1 into your i18n framework. Data values (names, cities, SKUs) stay raw; only chrome/labels translate.

---

## Component Inventory (shared kit)

Reusable pieces exported from `components.jsx` / `shell.jsx` (recreate as your design-system components):
`StageBadge`, `SlaBadge`, `TrackBadge`, `ChannelBadge`, `SlaRing`, `SlaBar`, `SlaMeter` (ring|bar via tweak), `KpiCard`, `CountUp`, `PageHead`, `Panel`/section cards, `PhoneFrame`, `ScanInput`, `EmptyState`, `Toast`, `LgModal`, `FilterChip`, `LangSwitcher`, `RoleSwitcher`, `LiveClock`, `JustyolLogo`, `DesktopShell`, `CommandPalette`, `ConfirmDialog`, `OfflineBanner`, `ActivityFeed`, `AttachPanel`.
Lower-level primitives (`I` icons, `Avatar`, `Badge`, `Button`, `IconButton`, `Dropdown`, `MenuItem`, `Kbd`, `Tip`, `Sparkline`) come from the shared **`frontend/v2/primitives.jsx`** (bundled).

---

## Tweaks (prototype-only — do NOT ship)

A dev panel toggles: **accent** (5 ramps), **SLA meter** style (ring/bar), **performance tone** (coaching/neutral), **density** (comfortable/compact), **theme** (light/dark), **connection** (online/offline). These exist to demonstrate design dimensions. Keep the *capabilities* they preview (theming, density, dark mode, coaching copy, offline queueing) but implement them through your real settings/theme system — the floating panel itself is not production UI.

---

## Assets

- **Justyol logo:** `logistics/justyol-logo.png` (and `.jpg`). Used in the sidebar lockup and mobile stage. In dark mode it's inverted via CSS filter — prefer a proper light-on-dark logo variant in production.
- **Icons:** the `I.*` set from `frontend/v2/primitives.jsx` (Lucide-style line icons). Swap for your icon library; names are descriptive (`Dashboard`, `Box`, `Truck`, `Tag`, `Return`, `AlertCircle`, `TrendUp`, etc.).
- **Product images:** placeholders on the order detail; wire to real item images.
- **Fonts:** Inter, JetBrains Mono, Noto Sans Arabic — loaded from Google Fonts.
- No hand-drawn SVG illustrations beyond the logo mark and simple sparklines/bars.

---

## Files in this bundle

```
Justyol Logistics Portal.html      ← entry point; theme config, root App, shell wiring, Tweaks
logistics/
  data.jsx          ← ALL mock data + i18n STRINGS + helpers (fmtMAD, makeT, autoPickGroups, computeBonus)
  components.jsx     ← shared logistics component kit
  shell.jsx          ← roles, nav trees, DesktopShell, switchers, logo, live clock
  cockpit.jsx        ← Manager cockpit
  dispatcher.jsx     ← Assignment board
  picker.jsx         ← Picker mobile (queue + scan-to-complete)
  packer.jsx         ← Packer label/manifest
  floor.jsx          ← PackStation, WavePicking, FloorBoard (Andon)
  picklist.jsx       ← Autopilot, SmartPickModal, PickListDetail
  workspaces.jsx     ← OrdersList, PickLists, Shipments, Carriers, shared PageHead/Modal
  order.jsx          ← Order detail + activity
  ordertimeline.jsx  ← Order timeline drawer
  returns.jsx        ← Returns, Tracking, RoutesBoard, TeamPerformance
  ops.jsx            ← CODReconcile, ExceptionCenter, CarrierScorecard
  warehouse.jsx      ← Warehouse map/count/receiving/re-slot
  inventory.jsx      ← Inventory overview
  analytics.jsx      ← SlaBoard, Stock, ItemDetail, Restocking, StockAnalysis, Reports
  team.jsx           ← TeamAdmin, BonusBoard, Roster
  settings.jsx       ← LogisticsSettings
  ux.jsx             ← CommandPalette, ConfirmDialog, OfflineBanner, NotificationsPage, ActivityFeed, AttachPanel
  justyol-logo.png / .jpg
frontend/v2/primitives.jsx          ← shared base primitives (icons, Avatar, Badge, Button, Dropdown, Sparkline…)
screens/                            ← reference screenshots (see below)
```

### Reference screenshots
`screens/01-manager-cockpit.png` · `02-orders-list.png` · `03-picklists-autopilot.png` · `04-pack-station.png` · `05-warehouse.png` · `06-shipments.png` · `07-sla-board.png` · `08-order-detail.png` · `09-picker-mobile.png` · `10-arabic-rtl.png`

---

## Recommended build order

1. **Shell + tokens + i18n + role/auth** — get the desktop shell, accent tokens, EN/FR/AR(RTL), and role-gated nav working against your stack.
2. **Orders → Order detail** — the read model + ERPNext linkage (connections, activity/notes).
3. **Pick Lists + Autopilot grouping** — highest operational leverage; port `autoPickGroups()` server-side.
4. **Picker mobile scan-to-complete** — the floor's daily driver.
5. **Pack → Shipments → Returns** — the fulfillment tail + AWB scan flows.
6. **Warehouse (map/count/receiving/re-slot)** and **Stock/Restocking/Analysis**.
7. **Cockpit / SLA / Andon / Reports** — aggregations over everything above.
8. **Team / Bonus / Roster / Settings**, **COD / Carriers / Routes / Exceptions**.

Cross-cutting from day one: theming tokens, RTL logical properties, the status color maps, toast-on-write pattern, and optimistic/offline queueing for floor devices.
