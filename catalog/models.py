import os
import uuid
from django.db import models
from django.utils.text import slugify
from django.core.files.base import ContentFile
import barcode
from io import BytesIO


class Category(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    VALUATION_CHOICES = [('FIFO', 'FIFO'), ('LIFO', 'LIFO')]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    unit_of_measure = models.CharField(max_length=20, default='pcs')
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_class = models.CharField(max_length=30, default='Standard')
    valuation_method = models.CharField(max_length=10, choices=VALUATION_CHOICES, blank=True, null=True)
    track_batches = models.BooleanField(default=False)
    track_serials = models.BooleanField(default=False)
    image_url = models.URLField(max_length=500, blank=True, help_text='Online image URL (e.g. from Google Images, Amazon, etc.)')
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sku} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.sku + '-' + self.name)
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        return img if img else self.images.first()

    @property
    def total_stock(self):
        from inventory.models import StockLevel
        result = StockLevel.objects.filter(product=self).aggregate(
            total=models.Sum('quantity_on_hand')
        )
        return result['total'] or 0


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    attributes = models.JSONField(default=dict, blank=True)
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True)
    cost_price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sale_price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sku']

    def __str__(self):
        attrs = ', '.join(f"{k}: {v}" for k, v in self.attributes.items())
        return f"{self.product.name} ({attrs})" if attrs else self.sku

    @property
    def display_name(self):
        attrs = ', '.join(f"{v}" for k, v in self.attributes.items())
        return f"{self.product.name} - {attrs}" if attrs else self.product.name

    @property
    def effective_cost(self):
        return self.cost_price_override or self.product.cost_price

    @property
    def effective_sale_price(self):
        return self.sale_price_override or self.product.sale_price

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        return img if img else self.product.primary_image


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='images')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        target = self.product or self.variant
        return f"Image of {target}"


class Batch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='batches')
    batch_number = models.CharField(max_length=50)
    expiry_date = models.DateField(null=True, blank=True)
    received_date = models.DateField()
    quantity_received = models.IntegerField()
    quantity_remaining = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['received_date']

    def __str__(self):
        return f"Batch {self.batch_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        if not self.quantity_remaining:
            self.quantity_remaining = self.quantity_received
        super().save(*args, **kwargs)


class SerialNumber(models.Model):
    STATUS_CHOICES = [
        ('In Stock', 'In Stock'),
        ('Sold', 'Sold'),
        ('Returned', 'Returned'),
        ('Damaged', 'Damaged'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='serial_numbers')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='serial_numbers')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='serial_numbers')
    serial_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='In Stock')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.serial_number


class SupplierProduct(models.Model):
    from suppliers.models import Supplier
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='supplier_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='supplier_products')
    supplier_sku = models.CharField(max_length=50, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    lead_time_override_days = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('supplier', 'product')

    def __str__(self):
        return f"{self.supplier.name} -> {self.product.name}"
