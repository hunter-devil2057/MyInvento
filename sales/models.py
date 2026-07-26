import uuid
from django.db import models
from django.contrib.auth.models import User


class SalesChannel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='customer_profile')
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    default_address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomerAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=50, default='Home')
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='India')
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', 'label']

    def __str__(self):
        return f"{self.label}: {self.address_line1}, {self.city}"


class SalesTransaction(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Completed', 'Completed'),
        ('Partially Returned', 'Partially Returned'),
        ('Returned', 'Returned'),
        ('Void', 'Void'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    invoice_number = models.CharField(max_length=30, unique=True, blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    channel = models.ForeignKey(SalesChannel, on_delete=models.CASCADE, related_name='transactions')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.CASCADE, related_name='sales_transactions')
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_transactions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft', db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        inv = self.invoice_number or f"Draft-{self.pk}"
        return f"Transaction {inv}"

    @property
    def is_editable(self):
        return self.status == 'Draft'

    def calculate_totals(self):
        from django.db.models import Sum, F, DecimalField, ExpressionWrapper
        lines = self.lines.all()
        self.subtotal = sum(line.subtotal for line in lines)
        self.discount_total = sum(line.discount for line in lines)
        self.tax_total = sum(line.tax for line in lines)
        self.grand_total = self.subtotal - self.discount_total + self.tax_total + self.shipping_total
        self.save(update_fields=['subtotal', 'discount_total', 'tax_total', 'grand_total', 'shipping_total'])


class SalesTransactionLine(models.Model):
    transaction = models.ForeignKey(SalesTransaction, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='sale_lines')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    batch = models.ForeignKey('catalog.Batch', on_delete=models.SET_NULL, null=True, blank=True)
    serial = models.ForeignKey('catalog.SerialNumber', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.subtotal = (self.quantity * self.unit_price) - self.discount + self.tax
        super().save(*args, **kwargs)


class Payment(models.Model):
    METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Mobile Wallet', 'Mobile Wallet'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Store Credit', 'Store Credit'),
        ('Khalti', 'Khalti'),
    ]
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Partially Paid', 'Partially Paid'),
        ('Refunded', 'Refunded'),
        ('Pending', 'Pending'),
    ]
    transaction = models.ForeignKey(SalesTransaction, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Paid')
    amount_tendered = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    change_given = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    # Khalti ePayment (KPG-2) tracking
    khalti_pidx = models.CharField(max_length=64, blank=True, null=True, unique=True)
    khalti_transaction_id = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"Payment {self.method}: {self.amount} for {self.transaction}"


class Return(models.Model):
    STATUS_CHOICES = [
        ('Requested', 'Requested'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Completed', 'Completed'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    original_transaction = models.ForeignKey(SalesTransaction, on_delete=models.CASCADE, related_name='returns')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_returns')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_returns')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Requested')
    reason = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refund_method = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Return #{self.pk} for {self.original_transaction}"


class ReturnLine(models.Model):
    return_request = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='lines')
    transaction_line = models.ForeignKey(SalesTransactionLine, on_delete=models.CASCADE)
    quantity_returned = models.IntegerField()
    restock = models.BooleanField(default=True)
    condition = models.CharField(max_length=20, choices=[('Sellable', 'Sellable'), ('Damaged', 'Damaged')], default='Sellable')
    movement = models.ForeignKey('inventory.StockMovement', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Return {self.transaction_line.product.name} x{self.quantity_returned}"
