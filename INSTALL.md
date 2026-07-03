# Justyol Logistics Portal — Install & Deploy

A Frappe app (Python API + doc-events + scheduler) that serves a Vue 3 SPA at
`/logistics`, styled to the Claude Design handoff. Same architecture as
`supplier_portal`.

## Prerequisites
- A Frappe/ERPNext bench (v14/v15) with the Justyol site (the one behind
  `admin.justyol.com`).
- Node 18+ and `yarn`/`npm` on the bench host (to build the SPA bundle).

## 1. Get the app onto the bench
```bash
cd ~/frappe-bench
# from a git remote:
bench get-app logistics_portal <git-url>
# …or copy this folder into ~/frappe-bench/apps/logistics_portal then:
bench build   # picks up the app
```

## 2. Install on the site
```bash
bench --site <your-site> install-app logistics_portal
bench --site <your-site> migrate     # imports fixtures → creates the custom fields below
```

## 3. Build the SPA bundle
```bash
cd apps/logistics_portal/frontend
npm install        # (or yarn)
npm run build      # outputs logistics_portal.bundle.{js,css} → logistics_portal/public/
```
The Frappe page `logistics_portal/templates/pages/logistics.html` includes those
bundles; `website_route_rules` in `hooks.py` routes `/logistics/<path>` to it.

## 4. Enable the scheduler (SLA + audit jobs)
```bash
bench --site <your-site> enable-scheduler
```
- `logistics_portal.api.sla.run_sla_engine` — every 15 min, populates the empty
  Delivery Note SLA fields.
- `logistics_portal.api.audit.run_rule_engine` — every 10 min, writes Notification
  Log alerts.
- `logistics_portal.api.audit.generate_daily_digest` — daily narrative digest.

## 5. Verify
Open `https://<your-site>/logistics` while logged in. The portal reads
`frappe.session.user` → resolves a logistics role → lands on that role's home.

---

## Custom fields added (via `fixtures/custom_field.json`, created on `migrate`)
| DocType | Field | Type | Purpose |
|---|---|---|---|
| Sales Order | `custom_picked_at` | Datetime | precise stage timestamp (SLA / time-in-stage) |
| Sales Order | `custom_labeled_at` | Datetime | " |
| Sales Order | `custom_shipped_at` | Datetime | " |
| Sales Order | `custom_delivered_at` | Datetime | " |
| Delivery Note | `custom_assigned_packer` | Link → User | explicit packer capture |
| User | `custom_logistics_role` | Select | portal role override |
| User | `custom_logistics_zone` | Data | role-badge zone |

All other fields the portal relies on already exist on the live site (verified:
Pick List `custom_assigned_picker`/`custom_scan_barcode_sku`, Sales Order
`custom_logistics_status`/`custom_channel`/`custom_awb`/…, Delivery Note
`custom_sla_status`/`custom_sla_days_remaining`/`custom_expected_delivery_date`,
Shipment `custom_scan_barcode`).

## Roles
On first use, roles resolve in order: (1) `User.custom_logistics_role`, (2) a seed
map of the known `Logistics - JM` team (`logistics_portal/api/auth.py`), (3) a
department heuristic. Set `custom_logistics_role` per user to make it explicit.

## Optional doctypes (backend no-ops until created)
- `Logistics SLA Settings` (Single) — `default_delivery_days`, cutoff, per-region
  targets. Until created, the SLA engine uses a 3-day default.
- `Logistics Audit Note` — stores the daily LLM digest.
Create these as ERPNext DocTypes when you want to tune thresholds / persist the
digest; the code guards for their absence.

---

## Frontend data wiring (current state)
Every screen currently renders from `frontend/src/lib/handoffData.js` (mock data
ported 1:1 from the design, grounded in real ERPNext values). The whitelisted API
in `logistics_portal/api/*.py` is real and queries live doctypes; to switch a
screen from mock to live, replace its `handoffData` import with an `api('…')` call
(helper in `frontend/src/lib/resource.js`) and map the response. A dev-only demo
auth fallback (`useAuth`, gated on `import.meta.env.DEV`) lets the SPA run without
a backend for design review; it is inert in the production bundle.
