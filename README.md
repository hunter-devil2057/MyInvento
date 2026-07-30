# MyInvento

**A full-featured, production-ready Inventory Management System built with Django.**

MyInvento is a centralized platform designed to manage every aspect of inventory operations — from procurement and warehousing to sales and customer engagement. It eliminates manual tracking overhead by automating stock updates, purchase workflows, and order fulfillment while providing full visibility across all operations through real-time dashboards and detailed PDF reports.

Built with a role-based architecture, MyInvento ensures that administrators, warehouse managers, purchase managers, sales staff, and customers each see exactly what they need — nothing more, nothing less. Every action in the system — whether it's a stock adjustment, a purchase order approval, or a new sale — automatically generates notifications that keep stakeholders informed and link directly to the relevant context.

Whether you're running a single warehouse or coordinating across multiple locations, MyInvento provides the tools to track stock in real time, process sales through a built-in POS interface, manage supplier relationships, handle customer complaints, and generate actionable reports — all from a single application.

---

## Features

### Core Inventory
- **Multi-Warehouse Management** — Create, edit, and manage warehouses; track stock per product per warehouse with real-time quantities
- **Stock Tracking** — `StockLevel` (on-hand, reserved, available), `StockMovement` (full audit trail of every quantity change), `StockAdjustment` with reason codes
- **Stock Transfers** — Move inventory between warehouses with a requested → in-transit → received workflow
- **Stock Count Sessions** — Cycle counting with variance detection; commit corrections that auto-generate adjustment movements
- **Shrinkage Tracking** — 12+ reason codes (Damage, Expired, Theft, System Error, etc.) with shrinkage reports filtering by date range and category
- **Reorder Rules** — Per-product min/max thresholds with automatic low-stock alerts and optional auto-reorder

### Product Catalog
- **Full CRUD** — Products with SKU, description, unit of measure, cost/sale prices, tax class, valuation method (FIFO/LIFO)
- **Product Variants** — JSON attribute storage (size, color, etc.), variant-level price overrides, barcodes
- **Batch Tracking** — Per-batch quantity, expiry dates, unit costs for FIFO/LIFO valuation
- **Serial Number Tracking** — Individual item serial numbers with status tracking (In Stock, Sold, Returned, Damaged)
- **Category Hierarchy** — Parent/child category tree with slug-based URLs
- **Product Images** — Multiple images per product/variant with primary image and ordering
- **Supplier Products** — Link suppliers to products with supplier-specific SKUs and pricing

### Purchase Orders
- **Full Workflow** — Draft → Sent → Partially Received → Received → Closed (with Cancel)
- **Line Items** — Per-line product, variant, quantity ordered/received, unit cost, batch number, expiry date
- **Partial Receiving** — Receive specific quantities per line; system tracks remaining
- **Supplier Management** — Contact info, lead times, on-time delivery percentage tracking
- **Reorder Rules** — Automatic low-stock alerts; optional auto-PO generation

### Sales & POS
- **Point-of-Sale Interface** — Fast retail checkout with product search, category filtering, quantity adjustment
- **Multiple Sales Channels** — Walk-in, Online, Phone, Market, Wholesale, Retail
- **Payment Methods** — Cash, Card, Mobile Wallet, Bank Transfer, Store Credit, Khalti
- **Khalti Payment Gateway** — Full integration with initiation, callback verification, and status tracking
- **Transactions** — Subtotal, discount, tax (13% VAT), shipping, grand total with line-item detail
- **Returns** — Requested → Approved/Rejected → Completed workflow; per-line restock decisions and condition tracking (Sellable/Damaged)
- **Receipt Generation** — PDF receipts for completed transactions

### Customer Portal
- **Self-Service Storefront** — Public product catalog with category filtering and product detail pages
- **Shopping Cart** — Session-based cart with add/update/remove; supports both authenticated and anonymous users
- **Checkout** — Address selection, Khalti online payment, order confirmation
- **Order History** — View past orders with status tracking and detail pages
- **Return Requests** — Submit return requests from order detail page
- **Complaint System** — Submit complaints by category (product quality, delivery, payment, service, website, refund, other) with priority levels and threaded admin replies
- **Account Settings** — Profile management for portal users
- **Smart Registration** — Portal registration detects existing email addresses and offers login instead of blocking; get-or-create logic links returning customers to their existing records

### Notification System
- **Automatic Notifications** — 13+ signal handlers trigger notifications on every system action (stock adjustments, PO status changes, sales, returns, complaints, user changes, transfers, shrinkage)
- **Notification Types** — Stock Adjusted, Low Stock, Out of Stock, Transfer Requested, PO Created, PO Sent, PO Received, PO Cancelled, Sale Completed, Return Processed, User Created/Activated/Deactivated/Password Reset, Complaint Created/Replied/Status Changed, and more
- **Alert System** — `Alert` model with severity levels (Critical, Warning, Info) and categories (Low Stock, Out of Stock, Shrinkage, Expiry, System Health, etc.)
- **In-App Panel** — Real-time notification dropdown in navbar; merges Notification + Alert objects sorted by datetime; category and severity filter tabs
- **Clickable Navigation** — Every notification includes a deep-link URL; clicking navigates directly to the relevant page
- **User Preferences** — Per-user notification settings with bulk mark-as-read
- **Badge Counts** — Navbar badge shows unread count from both Notifications and unresolved Alerts

### Reports & Analytics
- **12 Report Types** — Dashboard, Stock Valuation, Sales Report, Purchase Report, Shrinkage Report, Supplier Performance, Product Performance, Profit & Loss, Payment Methods, Returns Analysis, Category Analysis, Stock Health
- **KPI Cards** — Each report shows 4 key metrics with trend indicators
- **Date Range Filtering** — Filter reports by start/end date; dynamic query recalculation on filter
- **PDF Export** — ReportLab-based PDF generation for all 12 report types
- **CSV Export** — CSV download for all report types
- **REST API** — Django REST Framework ViewSets for Products, Customers, Suppliers, Transactions, Stock Levels + dashboard and POS-specific endpoints
- **Swagger Documentation** — Auto-generated API docs via drf-spectacular at `/api/schema/docs/`

### Security & Audit
- **Role-Based Access Control** — Admin, Warehouse, Sales, Purchasing, Auditor, Customer roles with `LoginRequiredMiddleware`
- **Customer Access Restriction** — Customers are automatically redirected from the admin dashboard to the customer portal on login; direct `/dashboard/` access also redirects away
- **Audit Logging** — Every Create/Update/Delete/Login/Logout action logged with user, timestamp, IP, before/after JSON snapshots
- **Session Management** — Configurable session timeout, max login attempts, lockout duration
- **Admin-Only Registration** — User registration restricted to admin users via role check
- **Duplicate Value Prevention** — Unique database constraints on email, phone, SKU, barcode, name, and other identifiers across all models (products, suppliers, customers, staff, warehouses, categories, reorder rules); form-level validation provides user-friendly error messages on duplicates; get-or-create logic handles existing records gracefully during registration and creation flows

### UI/UX
- **Responsive Design** — Mobile-first layout; notification panel becomes bottom-sheet on ≤480px
- **Consistent Theming** — Indigo/purple primary (`#6366f1`), warm white backgrounds (`#FAF9F6`), Linen borders (`#E9DCC9`)
- **Form Headers** — Consistent back-button + centered title pattern across all forms and detail pages including profile settings
- **Sidebar Navigation** — Role-aware sidebar with badge pills for notifications and alerts; admin panel link hidden for non-admin roles
- **Alpine.js Integration** — Interactive notification panel, dropdowns, and dynamic content
- **Nepali Rupee (रू)** — All price displays formatted with NPR currency symbol

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0.7, Python 3.14.4 |
| Database | SQLite (switchable to PostgreSQL via `dj-database-url`) |
| Frontend | HTML5, CSS3, JavaScript, Alpine.js, Font Awesome icons |
| API | Django REST Framework, drf-spectacular (Swagger/OpenAPI) |
| PDF Generation | ReportLab, xhtml2pdf |
| Image Handling | Pillow, django-cleanup |
| Barcodes/QR | python-barcode, qrcode |
| Payment Gateway | Khalti (REST API integration) |
| HTTP Client | requests (for Khalti API calls) |
| Static Files | Whitenoise with CompressedManifestStaticFilesStorage |
| Environment | python-dotenv |
| CORS | django-cors-headers |

---

## Installation

### Prerequisites

- Python 3.10+ (tested on 3.14.4)
- pip
- Git

### Ubuntu / Linux

```bash
# Clone the repository
git clone https://github.com/hunter-devil2057/MyInvento.git
cd MyInvento

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed sample data (optional)
python manage.py seed_all

# Create a superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

### Windows

```powershell
# Clone the repository
git clone https://github.com/hunter-devil2057/MyInvento.git
cd MyInvento

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Seed sample data (optional)
python manage.py seed_all

# Create a superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

### Environment Variables

Create a `.env` file in the project root:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
KHALTI_SECRET_KEY=your-khalti-secret-key
KHALTI_BASE_URL=https://dev.khalti.com/api/v2
SITE_BASE_URL=http://127.0.0.1:8000
```

---

## Running the Application

Once the server starts, access the application at:

| Page | URL |
|---|---|
| Main Dashboard | http://localhost:8000/dashboard/ |
| Admin Panel | http://localhost:8000/admin-panel/ |
| Customer Portal | http://localhost:8000/customers/ |
| REST API | http://localhost:8000/api/ |
| Swagger Docs | http://localhost:8000/api/schema/docs/ |

### Default Login Credentials

| Role | Username | Password |
|---|---|---|
| Administrator | admin | admin123 |
| Warehouse Manager | warehouse | warehouse |
| Sales Staff | sales | sales123 |
| Purchase Manager | purchase | purchase123 |

### Khalti Test Credentials (Sandbox)

Use these when testing Khalti payment integration:

| Field | Value |
|---|---|
| Phone Number | 9800000005 |
| PIN | 1111 |
| OTP | 987654 |

---

## Project Structure

```
MyInvento/
│
├── ims_project/                    # Django project configuration
│   ├── settings.py                 # Main settings (installed apps, middleware, DB, etc.)
│   ├── urls.py                     # Root URL configuration (24 URL patterns)
│   ├── asgi.py                     # ASGI entry point
│   └── wsgi.py                     # WSGI entry point
│
├── accounts/                       # User management and authentication (2 models)
│   ├── models.py                   # UserProfile (role, phone, avatar), SystemSettings (singleton)
│   ├── views.py                    # Login, register (admin-only), profile, password, user management
│   ├── forms.py                    # Registration, profile, user edit forms
│   ├── urls.py                     # 20 URL patterns (login, register, profile, user CRUD)
│   ├── admin_panel_urls.py         # 7 admin panel URLs (settings, health, activity, complaints)
│   ├── middleware.py               # LoginRequiredMiddleware
│   ├── context_processors.py       # Global template context processors
│   └── migrations/
│
├── catalog/                        # Product catalog management (6 models)
│   ├── models.py                   # Product, Category, ProductVariant, ProductImage, Batch, SerialNumber, SupplierProduct
│   ├── views.py                    # Product/category/variant CRUD, image upload, product API
│   ├── forms.py                    # Product, category, variant forms
│   ├── urls.py                     # 19 URL patterns (products, categories, variants, images, API)
│   ├── templatetags/
│   │   ├── number_tags.py          # Number formatting filters
│   │   └── pagination_tags.py      # Pagination utilities
│   └── migrations/
│
├── inventory/                      # Stock and warehouse management (8 models)
│   ├── models.py                   # Warehouse, ReasonCode, StockLevel, StockMovement, StockAdjustment,
│   │                               # StockTransfer, StockTransferLine, StockCountSession, StockCountLine
│   ├── views.py                    # Stock overview, adjustments, transfers, count sessions, warehouses, movements
│   ├── forms.py                    # Stock adjustment, transfer, count, warehouse forms
│   ├── urls.py                     # 23 URL patterns (stock, transfers, counts, movements, warehouses, API)
│   ├── api.py                      # Warehouse stock API endpoint
│   └── migrations/
│
├── suppliers/                      # Supplier management (1 model)
│   ├── models.py                   # Supplier (contact, lead time, on-time %)
│   ├── views.py                    # Supplier CRUD
│   ├── forms.py                    # Supplier forms
│   ├── urls.py                     # 5 URL patterns
│   └── migrations/
│
├── purchasing/                     # Purchase order workflow (3 models)
│   ├── models.py                   # PurchaseOrder, PurchaseOrderLine, ReorderRule
│   ├── views.py                    # PO CRUD, send, receive, cancel; reorder rule CRUD
│   ├── forms.py                    # Purchase order and reorder rule forms
│   ├── urls.py                     # 16 URL patterns (POs, reorder rules)
│   └── migrations/
│
├── sales/                          # POS and sales management (7 models)
│   ├── models.py                   # SalesChannel, Customer, CustomerAddress, SalesTransaction,
│   │                               # SalesTransactionLine, Payment (incl. Khalti), Return, ReturnLine
│   ├── views.py                    # POS, transactions, returns, customers, channels, Khalti integration
│   ├── forms.py                    # Sales, customer, return forms
│   ├── urls.py                     # 31 URL patterns (POS, transactions, returns, customers, channels, cart)
│   ├── khalti.py                   # Khalti payment gateway integration
│   └── migrations/
│
├── customers/                      # Customer-facing portal (4 models)
│   ├── models.py                   # Cart, CartItem, Complaint, ComplaintReply
│   ├── views.py                    # Portal: catalog, cart, checkout, orders, returns, complaints, settings
│   ├── urls.py                     # 24 URL patterns (portal home, catalog, cart, checkout, orders, support)
│   └── migrations/
│
├── reports/                        # PDF report generation and analytics (0 models — computed dynamically)
│   ├── views.py                    # 12+ report views with KPI calculations, PDF/CSV export
│   ├── api.py                      # DRF ViewSets: Product, Customer, Supplier, Transaction, StockLevel
│   ├── api_urls.py                 # REST API router (5 ViewSets + dashboard, stock-search, POS endpoints)
│   ├── dashboard_urls.py           # Dashboard URL
│   ├── schema_urls.py              # drf-spectacular Swagger/OpenAPI schema URLs
│   ├── pdf_utils.py                # PDF generation utilities (ReportLab)
│   ├── serializers.py              # DRF serializers for all API models
│   └── urls.py                     # 18 URL patterns (12 reports + PDF export + CSV export)
│
├── notifications/                  # System notification engine (2 models)
│   ├── models.py                   # Notification (user, title, body, link, is_read), Alert (severity, category)
│   ├── views.py                    # Notification list, mark-read, API endpoint (merges Notification + Alert)
│   ├── urls.py                     # 6 URL patterns (list, read, mark-all, API, alerts, resolve)
│   ├── utils.py                    # Helper functions: notify_user(), notify_admins(), notify_role()
│   ├── context_processors.py       # Unread notification count for templates
│   └── migrations/
│
├── audit/                          # Audit logging (1 model)
│   ├── models.py                   # AuditLog (user, action, model, before/after JSON, IP, timestamp)
│   ├── views.py                    # Audit log viewing
│   ├── utils.py                    # Audit logging utilities
│   ├── urls.py                     # 1 URL pattern
│   └── migrations/
│
├── templates/                      # HTML templates (150+ files)
│   ├── base.html                   # Main layout: navbar, sidebar, notification panel (Alpine.js)
│   ├── 404.html                    # Custom 404 error page
│   ├── 500.html                    # Custom 500 error page
│   ├── accounts/                   # Auth, profile, admin panel, user management templates
│   ├── catalog/                    # Product and category templates
│   ├── inventory/                  # Stock overview, transfers, count sessions, warehouses
│   ├── suppliers/                  # Supplier management templates
│   ├── purchasing/                 # Purchase orders and reorder rules
│   ├── sales/                      # POS, transactions, returns, customers, channels
│   ├── customers/                  # Customer portal (login, register, catalog, cart, checkout, orders)
│   ├── reports/                    # Report pages + pdf/ subdirectory (12 PDF templates)
│   ├── notifications/              # Notification and alert list templates
│   ├── audit/                      # Audit log templates
│   └── dashboard/                  # Dashboard template
│
├── static/                         # Static assets
│   └── css/
│       └── style.css               # Main stylesheet (1500+ lines, custom flat design, responsive)
│
├── frontend/                       # React frontend source (Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── DashboardApp.jsx    # Dashboard React component
│   │   │   └── POSApp.jsx          # POS React component
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
├── manage.py                       # Django management script
├── requirements.txt                # 13 Python dependencies
├── .env                            # Environment variables (not committed)
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
```

---

## Models Reference

**36 models** across 10 Django apps:

| App | Models | Key Entities |
|---|---|---|
| accounts | 2 | UserProfile, SystemSettings |
| catalog | 6 | Product, Category, ProductVariant, ProductImage, Batch, SerialNumber, SupplierProduct |
| inventory | 8 | Warehouse, ReasonCode, StockLevel, StockMovement, StockAdjustment, StockTransfer, StockTransferLine, StockCountSession, StockCountLine |
| suppliers | 1 | Supplier |
| purchasing | 3 | PurchaseOrder, PurchaseOrderLine, ReorderRule |
| sales | 7 | SalesChannel, Customer, CustomerAddress, SalesTransaction, SalesTransactionLine, Payment, Return, ReturnLine |
| customers | 4 | Cart, CartItem, Complaint, ComplaintReply |
| reports | 0 | (computed dynamically via aggregations) |
| notifications | 2 | Notification, Alert |
| audit | 1 | AuditLog |

---

## API Reference

### REST Endpoints (DRF)

| Method | Endpoint | Description |
|---|---|---|
| `GET/POST` | `/api/products/` | List/create products |
| `GET/PUT/DELETE` | `/api/products/{id}/` | Retrieve/update/delete product |
| `GET/POST` | `/api/customers/` | List/create customers |
| `GET/PUT/DELETE` | `/api/customers/{id}/` | Retrieve/update/delete customer |
| `GET/POST` | `/api/suppliers/` | List/create suppliers |
| `GET/PUT/DELETE` | `/api/suppliers/{id}/` | Retrieve/update/delete supplier |
| `GET/POST` | `/api/transactions/` | List/create sales transactions |
| `GET/PUT/DELETE` | `/api/transactions/{id}/` | Retrieve/update/delete transaction |
| `GET/POST` | `/api/stock-levels/` | List/create stock levels |
| `GET/PUT/DELETE` | `/api/stock-levels/{id}/` | Retrieve/update/delete stock level |
| `GET` | `/api/dashboard/` | Dashboard summary data |
| `GET` | `/api/stock-search/` | Search stock by product name |
| `GET` | `/api/pos/products/` | POS-optimized product list |
| `GET` | `/api/pos/categories/` | POS category list |

### Swagger/OpenAPI

| Endpoint | Description |
|---|---|
| `/api/schema/` | OpenAPI 3.0 schema (YAML) |
| `/api/schema/docs/` | Interactive Swagger UI |

### Internal API Endpoints

| Endpoint | Description |
|---|---|
| `/catalog/api/products/` | Product list for catalog autocomplete |
| `/inventory/api/warehouse-stock/{id}/` | Stock levels for a specific warehouse |
| `/notifications/api/recent/` | Recent notifications + alerts merged (30 items) |
| `/sales/cart/api/` | POS cart API (add/update/remove/get) |

---

## URL Structure

| Prefix | App | Patterns |
|---|---|---|
| `/accounts/` | accounts | Login, logout, register, profile, password change/reset, user management (20) |
| `/admin-panel/` | accounts | Admin panel, settings, user activity, system health, quick actions, complaints (7) |
| `/catalog/` | catalog | Products, categories, variants, images, product API (19) |
| `/inventory/` | inventory | Stock overview, adjustments, transfers, counts, movements, warehouses (23) |
| `/suppliers/` | suppliers | Supplier CRUD (5) |
| `/purchasing/` | purchasing | Purchase orders, reorder rules (16) |
| `/sales/` | sales | POS, transactions, returns, customers, channels, cart (31) |
| `/customers/` | customers | Portal: catalog, cart, checkout, orders, support, settings (24) |
| `/reports/` | reports | 12 report types + PDF/CSV export (18) |
| `/notifications/` | notifications | Notification list, mark-read, API, alerts, resolve (6) |
| `/audit/` | audit | Audit log (1) |
| `/dashboard/` | reports | Dashboard (1) |
| `/api/` | reports | REST API: 5 ViewSets + dashboard + POS + search (14) |
| `/api/schema/` | reports | Swagger/OpenAPI schema + docs (2) |

**Total: 188 URL patterns across 13 URL files**

---

## Notification System

### Signal Handlers (13+)

| Signal | Trigger | Notification Types |
|---|---|---|
| `StockAdjustment` post_save | Stock adjusted | Stock Adjusted, Low Stock, Out of Stock |
| `StockTransfer` post_save | Transfer status changed | Transfer Requested, Transfer Received |
| `PurchaseOrder` post_save | PO status changed | PO Created, PO Sent, PO Received, PO Cancelled |
| `SalesTransaction` post_save | Sale completed | Sale Completed, Low Stock (post-sale) |
| `Return` post_save | Return processed | Return Processed |
| `User` post_save | User created | User Created |
| `UserProfile` post_save | User activated/deactivated | User Activated, User Deactivated |
| `Complaint` post_save | Complaint created/status changed | Complaint Created, Complaint Status Changed |
| `ComplaintReply` post_save | Admin reply | Complaint Replied |
| `StockLevel` post_save | Stock threshold breach | Low Stock Alert, Out of Stock Alert |
| `Shrinkage` detection | Stock count variance | Shrinkage Alert |
| Password reset | Admin reset | Password Reset |
| User role change | Admin change | Role Changed |

### Notification Attributes

Each notification includes:
- `icon` — Font Awesome icon class (e.g., `fas fa-box`, `fas fa-shopping-cart`)
- `icon_bg` — Badge background color
- `icon_color` — Badge icon color
- `badge_pill` — Badge pill style class
- `category` — Notification category (stock, purchasing, sales, users, support)
- `severity` — Critical, Warning, or Info
- `link` — Deep-link URL to relevant page

---

## Reports

| Report | Description | KPIs |
|---|---|---|
| Dashboard | Overview with recent activity, alerts, quick stats | Total Products, Total Stock Value, Low Stock Items, Open Alerts |
| Stock Valuation | Inventory value by warehouse/category using FIFO/LIFO | Total Value, Product Count, Category Count, Warehouse Count |
| Sales Report | Sales performance over date range | Total Revenue, Transaction Count, Avg Order Value, Return Rate |
| Purchase Report | Purchase order analysis | Total Spent, PO Count, Avg Order Value, Pending Orders |
| Shrinkage Report | Stock loss tracking by reason code and category | Total Shrinkage Units, Total Value Lost, Shrinkage Rate, Top Reason |
| Supplier Performance | Supplier scoring based on delivery, cost, reliability | Avg On-Time %, Active Suppliers, Total POs, Avg Lead Time |
| Product Performance | Top/bottom products by sales volume and revenue | Total Products Sold, Revenue, Top Product, Avg Margin |
| Profit & Loss | Revenue vs COGS vs Expenses with net profit | Total Revenue, COGS, Gross Profit, Net Profit |
| Payment Methods | Payment method distribution analysis | Total Transactions, Cash %, Digital %, Avg Transaction |
| Returns Analysis | Return rate and reasons | Total Returns, Return Rate, Total Refunded, Avg Refund |
| Category Analysis | Category-wise sales and stock breakdown | Categories, Top Category, Total Stock, Avg Price |
| Stock Health | Stock level health check across warehouses | Healthy %, Low Stock Count, Overstock Count, Out of Stock |

All reports support:
- **Date range filtering** with dynamic recalculation
- **PDF export** via ReportLab
- **CSV export** for spreadsheet analysis

---

## Database

### Default: SQLite

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Switch to PostgreSQL

```bash
pip install psycopg2-binary
```

Update `DATABASES` in `ims_project/settings.py`:

```python
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default='postgres://user:password@localhost:5432/inventory_db'
    )
}
```

---

## Development

### Run Tests

```bash
python manage.py test
```

### Check System

```bash
python manage.py check
```

### Collect Static Files

```bash
python manage.py collectstatic
```

---

## License

This project is proprietary software. All rights reserved.

---

## Contact

**Manish Shiwakoti**

| Platform | Link |
|---|---|
| Email | [manishshiwakoti42@gmail.com](mailto:manishshiwakoti42@gmail.com) |
| Phone | +977-9866556820 |
| GitHub | [hunter-devil2057](https://github.com/hunter-devil2057/) |
| LinkedIn | [Manish Shiwakoti](https://www.linkedin.com/in/manish-shiwakoti-01721b260) |
| Instagram | [@shiwakoti.manish](https://www.instagram.com/shiwakoti.manish/) |
