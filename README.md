# MyInvento - Inventory Management System

A comprehensive Django-based inventory management system with role-based access control, real-time stock tracking, POS sales, customer portal, and notification system.

## Features

- **Role-based Access Control**: Admin, Warehouse Manager, Purchase Manager, Sales Staff, Customer
- **Product Catalog**: Full CRUD with variants, images, and categorization
- **Multi-warehouse Inventory**: Track stock levels across multiple locations
- **Purchase Orders**: Complete workflow from creation to receiving
- **POS Sales System**: Point-of-sale interface for retail transactions
- **Customer Portal**: Self-service portal with shopping cart
- **Stock Alerts**: Automatic notifications for low/out-of-stock items
- **Notifications**: System-wide notifications for all actions (78+ notification types)
- **PDF Reports**: Generate sales, inventory, and purchase reports
- **REST API**: API endpoints for external integrations
- **Audit Logging**: Track all system changes for security

## Tech Stack

- **Backend**: Django 6.0.7, Python 3.14.4
- **Database**: SQLite (easily switchable to PostgreSQL)
- **Frontend**: HTML5, CSS3, JavaScript (Tailwind CSS removed, custom flat design)
- **API**: Django REST Framework
- **PDF Generation**: ReportLab
- **Deployment**: Vercel-ready with Whitenoise static files

## Installation

### Prerequisites

- Python 3.14.4
- pip

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/hunter-devil2057/MyInvento.git
   cd MyInvento
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Load sample data (optional)**
   ```bash
   python manage.py loaddata fixtures/sample_data.json
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

## Usage

### Default Login Credentials

| Role               | Username     | Password    |
|-------------------|--------------|-------------|
| Admin             | admin        | admin123    |
| Warehouse Manager | warehouse    | warehouse   |
| Sales Staff       | sales        | sales123    |
| Purchase Manager  | purchase     | purchase123 |

### URLs

- **Main App**: http://localhost:8000/
- **Customer Portal**: http://localhost:8000/portal/
- **Admin Panel**: http://localhost:8000/admin/
- **API**: http://localhost:8000/api/

## Project Structure

```
MyInvento/
├── accounts/          # User management & authentication
├── catalog/           # Product catalog management
├── inventory/         # Stock levels & warehouse management
├── suppliers/         # Supplier management
├── purchasing/        # Purchase order workflow
├── sales/             # POS sales system
├── customers/         # Customer portal & shopping cart
├── reports/           # PDF report generation
├── notifications/     # System notification system
├── audit/             # Audit logging
├── static/            # CSS, JS, images
├── templates/         # HTML templates
├── api/               # REST API endpoints
├── ims_project/       # Django project settings
├── requirements.txt   # Python dependencies
└── manage.py          # Django management script
```

## API Endpoints

### Products
- `GET /api/products/` - List all products
- `POST /api/products/` - Create new product
- `GET /api/products/{id}/` - Get product details
- `PUT /api/products/{id}/` - Update product
- `DELETE /api/products/{id}/` - Delete product

### Stock Levels
- `GET /api/stock-levels/` - List stock levels
- `POST /api/stock-levels/` - Create stock entry
- `GET /api/stock-levels/{id}/` - Get stock details

### Purchase Orders
- `GET /api/purchase-orders/` - List purchase orders
- `POST /api/purchase-orders/` - Create purchase order
- `GET /api/purchase-orders/{id}/` - Get order details

### Sales
- `GET /api/sales/` - List sales
- `POST /api/sales/` - Create new sale

## Configuration

### Environment Variables

Create a `.env` file:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Database Switch

To use PostgreSQL instead of SQLite:

1. Install psycopg2: `pip install psycopg2-binary`
2. Update DATABASES in settings.py:
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

## Features in Detail

### Notification System

Every action in the system generates detailed notifications:

- **Stock Updates**: When stock levels change
- **Order Status**: Purchase/sales order updates
- **User Actions**: Logins, registrations, profile changes
- **System Alerts**: Low stock, out-of-stock warnings

Notifications are clickable and redirect to relevant pages.

### Stock Management

- Real-time stock tracking across warehouses
- Automatic low-stock alerts
- Stock transfer between warehouses
- Inventory adjustment with audit trail
- Barcode support (optional)

### Sales & POS

- Quick sales interface
- Customer management
- Invoice generation
- Payment tracking
- Sales history and analytics

### Reports

- Sales reports (daily, weekly, monthly)
- Inventory valuation reports
- Purchase order reports
- Customer purchase history
- Export to PDF

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

**Manish** - hunter-devil2057

Project Link: [https://github.com/hunter-devil2057/MyInvento](https://github.com/hunter-devil2057/MyInvento)
