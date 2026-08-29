[TECH] erpnext-1
[OBJ] Open-source ERP (accounts/CRM/inventory/HR) (2026). GPL-3.0 (frappe/erpnext, ~39k★). Self-host free. Use as external service — DO NOT vendor core code (GPL). aiZee freelance-financials (VAT) option.
[DATA]
- Version/License: GPL-3.0. Self-host free (Frappe framework + MariaDB). Cloud (Frappe Cloud) paid. Covers accounting, sales, purchasing, HR, projects.
- Core Data Model: DocType (metadata-driven entity) → e.g. Customer, Item, Sales Invoice, Purchase Invoice, Journal Entry, Ledger, Payment Entry, Account. Tree of Accounts (chart of accounts). Multi-currency + multi-company.
- Free-tier/Limits: Self-host full ERP unlimited. Cloud paid. REST + RPC API. Role-based permissions built-in.
[API]
- Endpoint: `https://your.erpnext/api/`. Auth: Bearer token / session. Methods: `GET /api/resource/{DocType}`, `POST /api/resource/{DocType}` (create), `POST /api/method/...` (whitelisted fn). SDK: `frappe-client` (Python/Node).
- Key: `POST /api/resource/Sales Invoice`, `GET /api/resource/Customer`, `POST /api/resource/Payment Entry`.
[CTX] Context7 ID: `websites/frappe_erpnext` (real)
[RTL]
- RTL note: ERPNext has Arabic translation (partial) + RTL; set user language `ar`. Handles Arabic VAT/GST (MENA tax templates) — ideal for freelance-financials. Charts of accounts in local currency (SAR/AED/EGP). Self-host for residency.
[PROHIBIT] ⛔ GPL — don't vendor/redistribute modified core without license. ⛔ Use as service/plugin. ⛔ Respect role permissions (no privilege bypass).
