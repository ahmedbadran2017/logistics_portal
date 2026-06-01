# Justyol Logistics Portal

Logistics & Warehouse operations portal for the Justyol team — sibling app to `purchasing_portal`. Same architecture (Frappe Web Page + Vue 3 SPA + shared Frappe auth) so the look-and-feel matches the rest of the toolset.

## Routes

| Route | Purpose | Status |
|---|---|---|
| `/logistics` | Dashboard with operational KPIs | 🟡 scaffold |

(More routes will land as the modules are built.)

## Planned modules

### Warehouse
- Receiving (Stock Entry: Receipt) + Putaway suggestions
- Picking & Packing (wave picking lists)
- Cycle counts + variance tracking
- Inter-warehouse transfers (Soft Group / Fast / Slow / In Transit)
- Bin map & utilization
- Stock aging

### Logistics
- Inbound shipments tracker (PO → in-transit → received)
- Customs status (especially China + Turkey ↔ Morocco)
- Lead-time analytics (planned vs actual)
- Carrier performance
- Document vault (BL, packing lists, commercial invoices)

### Returns
- RMA tracking
- Damage log / write-offs
- Restocking queue

## Architecture

```
logistics_portal/             ← Frappe app (Python)
  hooks.py                    website_route_rules + install hooks
  install.py                  roles + setup
  api/                        whitelisted REST endpoints
  www/                        Jinja shell that hosts the SPA
  logistics_portal/doctype/   custom DocTypes
  public/                     built Vue bundle (committed)

frontend/                     Vue 3 SPA source
  src/
    main.js / App.vue / router.js
    components/               shared UI (KpiCard, Drawer, Pill, ...)
    composables/              useApi.js / useToast.js / usePersist.js
    pages/                    one .vue per route
```

The SPA proxies `/api`, `/login`, `/app`, `/assets` to the production Frappe site during development (`vite.config.js`), and writes its production bundle into `logistics_portal/public/` so Frappe can serve it from the Jinja template.

## Deploying to the bench

```bash
cd /home/frappe/frappe-bench
bench get-app https://github.com/ahmedbadran2017/logistics_portal.git
bench --site admin.justyol.com install-app logistics_portal
bench --site admin.justyol.com migrate
bench build --app logistics_portal
bench restart
```

Land in the browser at:

**https://admin.justyol.com/logistics**

## Roles

The install hook creates three portal roles:

- `Logistics Portal Admin`
- `Logistics Portal User`
- `Warehouse Portal User`

In addition, any user with **Stock User**, **Stock Manager**, or **System Manager** has access by default.

## Local dev

```bash
cd frontend
npm install
npm run dev          # http://localhost:8082/logistics
npm run build        # writes ../logistics_portal/public/*
```

The dev server proxies API calls to `https://admin.justyol.com` by default. Override via `FRAPPE_DEV_URL` in `.env.local`.
