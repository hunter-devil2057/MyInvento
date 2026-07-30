from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('warehouse', 'Warehouse'),
        ('sales', 'Sales'),
        ('purchasing', 'Purchasing'),
        ('auditor', 'Auditor'),
        ('customer', 'Customer'),
    ]
    ROLE_ICONS = {
        'admin': 'fa-solid fa-crown',
        'warehouse': 'fa-solid fa-warehouse',
        'sales': 'fa-solid fa-cash-register',
        'purchasing': 'fa-solid fa-cart-shopping',
        'auditor': 'fa-solid fa-clipboard-check',
        'customer': 'fa-solid fa-user',
    }
    ROLE_COLORS = {
        'admin': '#6366f1',
        'warehouse': '#8b5cf6',
        'sales': '#10b981',
        'purchasing': '#f59e0b',
        'auditor': '#06b6d4',
        'customer': '#f97316',
    }
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='sales')
    phone = models.CharField(max_length=20, blank=True, null=True, default=None, unique=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def role_icon(self):
        return self.ROLE_ICONS.get(self.role, 'fa-solid fa-user')

    @property
    def role_color(self):
        return self.ROLE_COLORS.get(self.role, '#64748b')

    @property
    def is_admin_role(self):
        return self.role == 'admin'

    @property
    def is_warehouse_role(self):
        return self.role == 'warehouse'

    @property
    def is_sales_role(self):
        return self.role == 'sales'

    @property
    def is_purchasing_role(self):
        return self.role == 'purchasing'

    @property
    def is_auditor_role(self):
        return self.role == 'auditor'

    @property
    def is_customer_role(self):
        return self.role == 'customer'


class SystemSettings(models.Model):
    VALUATION_CHOICES = [
        ('FIFO', 'FIFO (First In, First Out)'),
        ('LIFO', 'LIFO (Last In, First Out)'),
    ]

    company_name = models.CharField(max_length=200, default='MyInvento IMS')
    company_email = models.EmailField(default='admin@myinvento.com')
    company_phone = models.CharField(max_length=20, default='+977-1-4200000')
    company_address = models.TextField(default='Kathmandu, Nepal')
    currency_code = models.CharField(max_length=10, default='NPR')
    currency_symbol = models.CharField(max_length=5, default='रू')
    default_valuation_method = models.CharField(max_length=10, choices=VALUATION_CHOICES, default='FIFO')
    low_stock_threshold = models.IntegerField(default=10)
    overstock_threshold = models.IntegerField(default=500)
    auto_reorder_enabled = models.BooleanField(default=False)
    require_purchase_order_approval = models.BooleanField(default=True)
    enable_batch_tracking = models.BooleanField(default=True)
    enable_serial_tracking = models.BooleanField(default=False)
    session_timeout_minutes = models.IntegerField(default=60)
    max_login_attempts = models.IntegerField(default=5)
    lockout_duration_minutes = models.IntegerField(default=15)
    enable_email_notifications = models.BooleanField(default=False)
    enable_low_stock_alerts = models.BooleanField(default=True)
    enable_expiry_alerts = models.BooleanField(default=True)
    expiry_alert_days = models.IntegerField(default=30)
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=13.00)
    receipt_footer_text = models.CharField(max_length=300, default='Thank you for shopping with us!')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return f"Settings: {self.company_name}"

    def save(self, *args, **kwargs):
        if not self.pk and SystemSettings.objects.exists():
            raise ValueError('Only one SystemSettings instance is allowed.')
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
