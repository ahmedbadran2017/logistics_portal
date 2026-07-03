# Justyol Logistics Portal

Role-aware warehouse & fulfillment portal for **Justyol Morocco** (COD, carrier
Cathedis, SoftPark Aïn Sebaâ). One Frappe app + Vue 3 SPA serves five operational
roles across desktop and a mobile handheld-scanner experience, in EN / FR / AR (RTL).

Covers the full ERPNext cycle — **Sales Order → Pick List → Delivery Note →
Shipment → Return Shipment** — plus inventory, team performance, SLA governance,
COD reconciliation and carrier management. Design spine: **Capture → Reflect →
Audit**. Visual language from the Claude Design handoff (warm stone + Rust accent,
JetBrains Mono for codes; see `design_handoff/`).

## Layout
```
logistics_portal/            Frappe app
  hooks.py                   /logistics route, doc_events, scheduler, fixtures
  api/*.py                   whitelisted endpoints (auth, picking, orders,
                             shipping, returns, performance, sla, audit)
  fixtures/custom_field.json custom fields created on migrate
  templates/pages/logistics.html   SPA mount page
  public/                    built bundle lands here
frontend/                    Vue 3 SPA (vite + tailwind)
  src/lib/handoffData.js     mock data (ported from the design; swap for live RPC)
  src/lib/roles.js           role → grouped nav
  src/components/…           shell (Sidebar/TopBar/AppLayout) + ui kit + overlays
  src/pages/…                one component per screen
design_handoff/              the Claude Design source (JSX prototype + screenshots)
```

## Roles & home screens
manager → Cockpit · dispatcher → Assignment board · picker → My Queue (phone) ·
packer → Label queue · returns → Returns.

## Develop
```bash
cd frontend && npm install && npm run dev     # http://localhost:5177/logistics
```
A dev-only demo auth fallback lets the SPA run without a backend (inert in prod).

## Deploy
See **[INSTALL.md](INSTALL.md)** for bench install, migrate (custom fields),
`npm run build`, and scheduler setup.
