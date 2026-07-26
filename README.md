# MyInvento

**A full-featured, production-ready Inventory Management System built with Django.**

MyInvento streamlines warehouse operations, sales, purchasing, and customer engagement through a single unified platform with role-based access, real-time stock tracking, PDF reports, REST APIs, and a comprehensive notification system.

---

## Features

- **Role-Based Access Control** — Admin, Warehouse Manager, Purchase Manager, Sales Staff, and Customer roles with granular permissions
- **Product Catalog** — Full CRUD with variants, images, categories, and SKU management
- **Multi-Warehouse Inventory** — Real-time stock tracking, transfers, adjustments, and stock count sessions across multiple warehouses
- **Purchase Order Workflow** — Create, approve, receive, and track purchase orders with supplier management and reorder rules
- **Point-of-Sale (POS)** — Fast retail checkout interface with multiple sales channels and Khalti payment integration
- **Customer Portal** — Self-service storefront with shopping cart, order tracking, returns, and complaint submission
- **Notification System** — 78+ notification types triggered automatically on every system action, clickable to navigate directly to relevant pages
- **PDF Report Generation** — Sales, inventory valuation, profit/loss, stock health, supplier performance, category analysis, and shrinkage reports via ReportLab
- **REST API** — Full API endpoints built with Django REST Framework for products, stock levels, orders, and sales
- **Audit Logging** — Comprehensive trail of all system changes for security and compliance
- **Responsive UI** — Clean, professional interface with a custom flat design theme

---

## Tech Stack

| Layer          | Technology                                          |
|----------------|-----------------------------------------------------|
| Backend        | Django 6.0.7, Python 3.14.4                         |
| Database       | SQLite (switchable to PostgreSQL)                   |
| Frontend       | HTML5, CSS3, JavaScript, Tailwind CSS utilities     |
| API            | Django REST Framework, django-filter                |
| PDF Generation | ReportLab                                           |
| Image Handling | Pillow, django-cleanup                              |
| Deployment     | Vercel, Whitenoise (static files), Gunicorn         |

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

# Create a superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## Running the Application

Once the server starts, access the application at:

| Page              | URL                                    |
|-------------------|----------------------------------------|
| Main Application  | http://localhost:8000/                  |
| Customer Portal   | http://localhost:8000/portal/           |
| Admin Panel       | http://localhost:8000/admin/            |
| REST API          | http://localhost:8000/api/              |

### Default Login Credentials

| Role               | Username     | Password    |
|--------------------|-------------|-------------|
| Administrator      | admin       | admin123    |
| Warehouse Manager  | warehouse   | warehouse   |
| Sales Staff        | sales       | sales123    |
| Purchase Manager   | purchase    | purchase123 |

---

## Project Structure

```
MyInvento/
│
├── ims_project/                    # Django project configuration
│   ├── __init__.py
│   ├── settings.py                 # Main settings (installed apps, middleware, DB, etc.)
│   ├── urls.py                     # Root URL configuration
│   ├── asgi.py                     # ASGI entry point
│   └── wsgi.py                     # WSGI entry point
│
├── accounts/                       # User management and authentication
│   ├── models.py                   # UserProfile, SystemSettings models
│   ├── views.py                    # Login, register, profile, admin panel views
│   ├── forms.py                    # Registration, profile, and user edit forms
│   ├── urls.py                     # Account URL patterns
│   ├── admin_panel_urls.py         # Admin panel URL patterns
│   ├── middleware.py               # LoginRequiredMiddleware
│   ├── context_processors.py       # Global template context processors
│   ├── admin.py                    # Admin site configuration
│   └── migrations/                 # Database migrations
│
├── catalog/                        # Product catalog management
│   ├── models.py                   # Product, Category, ProductVariant models
│   ├── views.py                    # Product and category CRUD views
│   ├── forms.py                    # Product and category forms
│   ├── urls.py                     # Catalog URL patterns
│   ├── templatetags/               # Custom template tags
│   │   ├── number_tags.py          # Number formatting filters
│   │   └── pagination_tags.py      # Pagination utilities
│   └── migrations/                 # Database migrations
│
├── inventory/                      # Stock and warehouse management
│   ├── models.py                   # Warehouse, StockLevel, StockMovement, StockTransfer, StockCountSession
│   ├── views.py                    # Stock overview, adjustments, transfers, count sessions
│   ├── forms.py                    # Stock adjustment, transfer, and count forms
│   ├── urls.py                     # Inventory URL patterns
│   ├── signals.py                  # Post-save signals for stock events
│   └── migrations/                 # Database migrations
│
├── suppliers/                      # Supplier management
│   ├── models.py                   # Supplier model
│   ├── views.py                    # Supplier CRUD views
│   ├── forms.py                    # Supplier forms
│   ├── urls.py                     # Supplier URL patterns
│   └── migrations/                 # Database migrations
│
├── purchasing/                     # Purchase order workflow
│   ├── models.py                   # PurchaseOrder, PurchaseOrderItem, ReorderRule models
│   ├── views.py                    # PO creation, approval, receiving views
│   ├── forms.py                    # Purchase order and reorder rule forms
│   ├── urls.py                     # Purchasing URL patterns
│   └── migrations/                 # Database migrations
│
├── sales/                          # POS and sales management
│   ├── models.py                   # SalesTransaction, Payment, Customer, Return, SalesChannel models
│   ├── views.py                    # POS, transaction, return, and customer views
│   ├── forms.py                    # Sales and customer forms
│   ├── urls.py                     # Sales URL patterns
│   ├── khalti.py                   # Khalti payment gateway integration
│   └── migrations/                 # Database migrations
│
├── customers/                      # Customer-facing portal
│   ├── models.py                   # CustomerComplaint, ComplaintReply models
│   ├── views.py                    # Portal views (catalog, cart, checkout, orders, returns, complaints)
│   ├── urls.py                     # Customer portal URL patterns
│   └── migrations/                 # Database migrations
│
├── reports/                        # PDF report generation
│   ├── models.py                   # Report configuration models
│   ├── views.py                    # Report generation views (12 report types)
│   ├── api.py                      # Report API views
│   ├── api_urls.py                 # Report API URL patterns
│   ├── dashboard_urls.py           # Dashboard-specific report URLs
│   ├── schema_urls.py              # Schema-based report URLs
│   ├── pdf_utils.py                # PDF generation utilities (ReportLab)
│   ├── serializers.py              # DRF serializers for reports
│   └── urls.py                     # Report URL patterns
│
├── notifications/                  # System notification engine
│   ├── models.py                   # Notification model (user, title, body, link, is_read)
│   ├── views.py                    # Notification list and mark-as-read views
│   ├── urls.py                     # Notification URL patterns
│   ├── utils.py                    # Helper functions: notify_user(), notify_admins(), notify_role()
│   ├── context_processors.py       # Unread notification count for templates
│   └── migrations/                 # Database migrations
│
├── audit/                          # Audit logging
│   ├── models.py                   # AuditLog model
│   ├── views.py                    # Audit log viewing
│   ├── utils.py                    # Audit logging utilities
│   ├── urls.py                     # Audit URL patterns
│   └── migrations/                 # Database migrations
│
├── templates/                      # HTML templates (150+ files)
│   ├── base.html                   # Main application base template
│   ├── 404.html                    # Custom 404 error page
│   ├── 500.html                    # Custom 500 error page
│   ├── accounts/                   # Auth, profile, admin panel, user management templates
│   ├── catalog/                    # Product and category templates
│   ├── inventory/                  # Stock overview, transfers, count session templates
│   ├── suppliers/                  # Supplier management templates
│   ├── purchasing/                 # Purchase order and reorder rule templates
│   ├── sales/                      # POS, transactions, returns, customer management templates
│   ├── customers/                  # Customer portal templates (login, catalog, cart, checkout, orders)
│   ├── reports/                    # Report pages and PDF templates
│   │   └── pdf/                    # PDF-specific templates (12 report types)
│   ├── notifications/              # Notification and alert list templates
│   ├── audit/                      # Audit log templates
│   └── dashboard/                  # Dashboard template
│
├── static/                         # Static assets
│   ├── css/
│   │   └── style.css               # Main stylesheet (1500+ lines, custom flat design)
│   └── frontend/                   # Built frontend assets (Vite/React)
│       ├── dashboard.js
│       ├── pos.js
│       └── chunks/
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
├── api/                            # Vercel serverless entry point
│   └── index.py                    # WSGI handler for Vercel deployment
│
├── manage.py                       # Django management script
├── requirements.txt                # Python dependencies
├── runtime.txt                     # Python runtime version (for Vercel)
├── build_files.sh                  # Vercel build script
├── .env                            # Environment variables (not committed)
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
```

---

## API Reference

### Products
| Method   | Endpoint                | Description              |
|----------|-------------------------|--------------------------|
| `GET`    | `/api/products/`        | List all products        |
| `POST`   | `/api/products/`        | Create a new product     |
| `GET`    | `/api/products/{id}/`   | Retrieve product details |
| `PUT`    | `/api/products/{id}/`   | Update a product         |
| `DELETE` | `/api/products/{id}/`   | Delete a product         |

### Stock Levels
| Method   | Endpoint                    | Description               |
|----------|-----------------------------|---------------------------|
| `GET`    | `/api/stock-levels/`        | List all stock levels     |
| `POST`   | `/api/stock-levels/`        | Create a stock entry      |
| `GET`    | `/api/stock-levels/{id}/`   | Retrieve stock details    |

### Purchase Orders
| Method   | Endpoint                       | Description                 |
|----------|--------------------------------|-----------------------------|
| `GET`    | `/api/purchase-orders/`        | List all purchase orders    |
| `POST`   | `/api/purchase-orders/`        | Create a purchase order     |
| `GET`    | `/api/purchase-orders/{id}/`   | Retrieve order details      |

### Sales
| Method   | Endpoint                | Description              |
|----------|-------------------------|--------------------------|
| `GET`    | `/api/sales/`           | List all sales           |
| `POST`   | `/api/sales/`           | Create a new sale        |

---

## Database Switch (PostgreSQL)

To switch from SQLite to PostgreSQL:

```bash
pip install psycopg2-binary
```

Update `DATABASES` in `ims_project/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'inventory_db',
        'USER': 'postgres',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## Contact

**Manish Shiwakoti**

| Platform   | Link                                                          |
|------------|---------------------------------------------------------------|
| Email      | [manishshiwakoti42@gmail.com](mailto:manishshiwakoti42@gmail.com) |
| Phone      | +977-9866556820                                               |
| GitHub     | [hunter-devil2057](https://github.com/hunter-devil2057/)     |
| LinkedIn   | [Manish Shiwakoti](https://www.linkedin.com/in/manish-shiwakoti-01721b260) |
| Instagram  | [@shiwakoti.manish](https://www.instagram.com/shiwakoti.manish/) |
