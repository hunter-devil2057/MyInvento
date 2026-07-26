import random
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils import timezone
from accounts.models import UserProfile
from catalog.models import Category, Product, ProductVariant, Batch
from inventory.models import Warehouse, StockLevel, StockMovement, ReasonCode
from suppliers.models import Supplier
from purchasing.models import PurchaseOrder, PurchaseOrderLine
from sales.models import SalesChannel, Customer, SalesTransaction, SalesTransactionLine, Payment
from notifications.models import Alert, Notification


class Command(BaseCommand):
    help = 'Seed the database with realistic demo data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        self.create_groups()
        self.create_users()
        self.create_warehouses()
        self.create_reason_codes()
        self.create_categories()
        self.create_products()
        self.create_suppliers()
        self.create_channels()
        self.create_customers()
        self.create_stock_levels()
        self.create_sales()
        self.create_alerts()
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

    def create_groups(self):
        for name in ['Admin', 'Warehouse Staff', 'Sales', 'Purchasing', 'Auditor']:
            Group.objects.get_or_create(name=name)
        self.stdout.write('  Groups created')

    def create_users(self):
        admin = User.objects.create_superuser('admin', 'admin@ims.com', 'admin123', first_name='Rajesh', last_name='Kumar')
        UserProfile.objects.get_or_create(user=admin, defaults={'role': 'admin', 'phone': '9876543210'})

        warehouse = User.objects.create_user('warehouse', 'warehouse@ims.com', 'warehouse123', first_name='Priya', last_name='Sharma')
        UserProfile.objects.get_or_create(user=warehouse, defaults={'role': 'warehouse', 'phone': '9876543211'})

        sales = User.objects.create_user('sales', 'sales@ims.com', 'sales123', first_name='Amit', last_name='Patel')
        UserProfile.objects.get_or_create(user=sales, defaults={'role': 'sales', 'phone': '9876543212'})

        purchasing = User.objects.create_user('purchase', 'purchase@ims.com', 'purchase123', first_name='Neha', last_name='Gupta')
        UserProfile.objects.get_or_create(user=purchasing, defaults={'role': 'purchasing', 'phone': '9876543213'})

        self.stdout.write('  Users created')

    def create_warehouses(self):
        Warehouse.objects.get_or_create(name='Main Warehouse', defaults={'address': '123 Industrial Area, Mumbai, Maharashtra'})
        Warehouse.objects.get_or_create(name='Store Front', defaults={'address': '456 MG Road, Mumbai, Maharashtra'})
        Warehouse.objects.get_or_create(name='Backup Storage', defaults={'address': '789 Andheri East, Mumbai, Maharashtra'})
        self.stdout.write('  Warehouses created')

    def create_reason_codes(self):
        codes = [
            ('DAMAGED', 'Damaged in transit/handling', True),
            ('EXPIRED', 'Expired product', True),
            ('LOST_THEFT', 'Lost or stolen', True),
            ('RECOUNT', 'Recount correction', False),
            ('SAMPLE', 'Sample given away', True),
            ('INTERNAL_USE', 'Internal use', True),
            ('FOUND', 'Found/recount correction', False),
        ]
        for code, label, shrink in codes:
            ReasonCode.objects.get_or_create(code=code, defaults={'label': label, 'affects_shrinkage_report': shrink})
        self.stdout.write('  Reason codes created')

    def create_categories(self):
        cats = ['Electronics', 'Clothing', 'Food & Beverages', 'Home & Garden', 'Sports', 'Books', 'Beauty', 'Automotive']
        for name in cats:
            Category.objects.get_or_create(name=name, defaults={'slug': name.lower().replace(' & ', '-')})
        self.stdout.write('  Categories created')

    def create_products(self):
        products_data = [
            ('SKU001', 'Wireless Bluetooth Headphones', 'Electronics', 850, 1499),
            ('SKU002', 'USB-C Charging Cable (2m)', 'Electronics', 45, 149),
            ('SKU003', 'Mechanical Keyboard RGB', 'Electronics', 1200, 2499),
            ('SKU004', 'Laptop Stand Adjustable', 'Electronics', 600, 1199),
            ('SKU005', 'Webcam HD 1080p', 'Electronics', 500, 999),
            ('SKU006', 'Cotton T-Shirt Blue', 'Clothing', 180, 499),
            ('SKU007', 'Denim Jeans Slim Fit', 'Clothing', 450, 1299),
            ('SKU008', 'Running Shoes Pro', 'Clothing', 800, 1999),
            ('SKU009', 'Organic Green Tea (100 bags)', 'Food & Beverages', 120, 349),
            ('SKU010', 'Protein Powder 1kg', 'Food & Beverages', 350, 899),
            ('SKU011', 'Stainless Steel Water Bottle', 'Home & Garden', 150, 449),
            ('SKU012', 'LED Desk Lamp', 'Home & Garden', 400, 999),
            ('SKU013', 'Yoga Mat Premium', 'Sports', 250, 699),
            ('SKU014', 'Resistance Bands Set', 'Sports', 180, 499),
            ('SKU015', 'Notebook Journal A5', 'Books', 60, 199),
            ('SKU016', 'Python Programming Guide', 'Books', 200, 599),
            ('SKU017', 'Sunscreen SPF 50', 'Beauty', 100, 349),
            ('SKU018', 'Moisturizer Cream', 'Beauty', 150, 449),
            ('SKU019', 'Car Phone Mount', 'Automotive', 200, 599),
            ('SKU020', 'LED Car Interior Lights', 'Automotive', 250, 699),
            ('SKU021', 'Smart Watch Fitness', 'Electronics', 1500, 3499),
            ('SKU022', 'Portable Speaker Mini', 'Electronics', 400, 999),
            ('SKU023', 'Winter Jacket Warm', 'Clothing', 600, 1799),
            ('SKU024', 'Coffee Beans Premium 500g', 'Food & Beverages', 280, 699),
            ('SKU025', 'Air Purifier HEPA', 'Home & Garden', 1800, 4499),
        ]
        categories = {c.name: c for c in Category.objects.all()}
        for sku, name, cat, cost, sale in products_data:
            Product.objects.get_or_create(sku=sku, defaults={
                'name': name, 'slug': sku.lower(), 'category': categories.get(cat),
                'cost_price': Decimal(str(cost)), 'sale_price': Decimal(str(sale)),
                'tax_class': 'Standard', 'is_active': True, 'is_published': True,
                'description': f'High quality {name.lower()} for everyday use.',
            })
        self.stdout.write('  Products created')

    def create_suppliers(self):
        suppliers_data = [
            ('TechSource India', 'Rahul Mehta', 'rahul@techsource.in', '9876543301', 7),
            ('FabricWorld', 'Sunita Verma', 'sunita@fabricworld.in', '9876543302', 10),
            ('FreshGoods Co', 'Arun Singh', 'arun@freshgoods.in', '9876543303', 3),
            ('HomePlus Supply', 'Kavita Reddy', 'kavita@homeplus.in', '9876543304', 5),
            ('SportsHub', 'Vikram Joshi', 'vikram@sportshub.in', '9876543305', 8),
        ]
        for name, contact, email, phone, lead in suppliers_data:
            Supplier.objects.get_or_create(name=name, defaults={
                'contact_name': contact, 'email': email, 'phone': phone,
                'lead_time_days': lead, 'on_time_pct': Decimal(str(random.randint(85, 98))),
            })
        self.stdout.write('  Suppliers created')

    def create_channels(self):
        for name in ['In-Store', 'Online/Self-Service', 'Shopify', 'WhatsApp']:
            SalesChannel.objects.get_or_create(name=name)
        self.stdout.write('  Sales channels created')

    def create_customers(self):
        customers_data = [
            ('Aarav Mehta', 'aarav@gmail.com', '9876543401'),
            ('Diya Patel', 'diya@gmail.com', '9876543402'),
            ('Arjun Nair', 'arjun@gmail.com', '9876543403'),
            ('Ananya Sharma', 'ananya@gmail.com', '9876543404'),
            ('Kabir Kumar', 'kabir@gmail.com', '9876543405'),
            ('Walk-in Customer', '', ''),
        ]
        for name, email, phone in customers_data:
            Customer.objects.get_or_create(name=name, defaults={'email': email, 'phone': phone})
        self.stdout.write('  Customers created')

    def create_stock_levels(self):
        warehouses = list(Warehouse.objects.filter(is_active=True))
        products = list(Product.objects.filter(is_active=True))
        main_wh = warehouses[0] if warehouses else None
        store_wh = warehouses[1] if len(warehouses) > 1 else None

        for product in products:
            qty_main = random.randint(20, 200)
            qty_store = random.randint(5, 50)

            if main_wh:
                sl, _ = StockLevel.objects.get_or_create(
                    product=product, warehouse=main_wh,
                    defaults={'quantity_on_hand': qty_main}
                )
            if store_wh:
                sl, _ = StockLevel.objects.get_or_create(
                    product=product, warehouse=store_wh,
                    defaults={'quantity_on_hand': qty_store}
                )

            # Create some stock movements
            user = User.objects.first()
            if main_wh and random.random() > 0.5:
                StockMovement.objects.create(
                    product=product, warehouse=main_wh,
                    movement_type='PURCHASE', quantity_delta=qty_main,
                    user=user, notes='Initial stock purchase',
                    created_at=timezone.now() - datetime.timedelta(days=random.randint(1, 30))
                )

        self.stdout.write('  Stock levels and movements created')

    def create_sales(self):
        customers = list(Customer.objects.filter(is_active=True))
        products = list(Product.objects.filter(is_active=True))
        channels = list(SalesChannel.objects.all())
        warehouses = list(Warehouse.objects.filter(is_active=True))
        user = User.objects.first()
        if not customers or not products or not channels or not warehouses:
            return

        statuses = ['Completed', 'Completed', 'Completed', 'Completed', 'Draft', 'Completed']
        payment_methods = ['Cash', 'Card', 'Mobile Wallet', 'Bank Transfer']

        for i in range(25):
            customer = random.choice(customers)
            channel = random.choice(channels)
            warehouse = random.choice(warehouses)
            status = random.choice(statuses)
            days_ago = random.randint(0, 60)
            created = timezone.now() - datetime.timedelta(days=days_ago)
            completed = created + datetime.timedelta(minutes=random.randint(2, 60)) if status == 'Completed' else None

            tx = SalesTransaction.objects.create(
                customer=customer if customer.name != 'Walk-in Customer' else None,
                channel=channel,
                warehouse=warehouse,
                cashier=user,
                status=status,
                created_at=created,
                completed_at=completed,
            )

            num_lines = random.randint(1, 5)
            line_products = random.sample(products, min(num_lines, len(products)))
            subtotal = Decimal('0')

            for p in line_products:
                qty = random.randint(1, 10)
                unit_price = p.sale_price
                line_total = unit_price * qty
                subtotal += line_total
                SalesTransactionLine.objects.create(
                    transaction=tx, product=p,
                    quantity=qty, unit_price=unit_price,
                    subtotal=line_total,
                )

                if status == 'Completed':
                    stock_levels = StockLevel.objects.filter(product=p)
                    for sl in stock_levels:
                        deduct = min(sl.quantity_on_hand, qty)
                        if deduct > 0:
                            sl.quantity_on_hand -= deduct
                            sl.save()
                            StockMovement.objects.create(
                                product=p, warehouse=sl.warehouse,
                                movement_type='SALE', quantity_delta=-deduct,
                                user=user, notes=f'Sale deducted {deduct} units',
                                created_at=completed or created,
                            )
                            qty -= deduct
                        if qty <= 0:
                            break

            tax = subtotal * Decimal('0.05')
            grand_total = subtotal + tax
            tx.subtotal = subtotal
            tx.tax_total = tax
            tx.grand_total = grand_total
            tx.save(update_fields=['subtotal', 'tax_total', 'grand_total'])

            if status == 'Completed':
                inv = f'INV-{completed.strftime("%Y%m%d")}-{str(i+1).zfill(4)}'
                tx.invoice_number = inv
                tx.save(update_fields=['invoice_number'])
                Payment.objects.create(
                    transaction=tx, method=random.choice(payment_methods),
                    amount=grand_total, amount_tendered=grand_total + Decimal(str(random.randint(0, 500))),
                    change_given=Decimal(str(random.randint(0, 500))),
                )

        self.stdout.write('  Sales transactions created')

    def create_alerts(self):
        low_products = StockLevel.objects.filter(quantity_on_hand__lte=10).select_related('product', 'warehouse')
        for sl in low_products[:5]:
            Alert.objects.get_or_create(
                alert_type='Low Stock', product=sl.product, warehouse=sl.warehouse,
                defaults={
                    'message': f'{sl.product.name} is low at {sl.warehouse.name} ({sl.quantity_on_hand} remaining)',
                    'severity': 'Warning' if sl.quantity_on_hand > 0 else 'Critical',
                }
            )
        self.stdout.write('  Alerts created')
