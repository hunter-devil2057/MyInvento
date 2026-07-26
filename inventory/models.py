import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Warehouse(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ReasonCode(models.Model):
    code = models.CharField(max_length=30, unique=True)
    label = models.CharField(max_length=100)
    affects_shrinkage_report = models.BooleanField(default=False)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.label}"


class StockLevel(models.Model):
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='stock_levels')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_levels')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_levels')
    quantity_on_hand = models.IntegerField(default=0)
    quantity_reserved = models.IntegerField(default=0)
    reorder_min = models.IntegerField(null=True, blank=True)
    reorder_max = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'variant', 'warehouse')
        ordering = ['warehouse', 'product']

    def __str__(self):
        variant_str = f" ({self.variant})" if self.variant else ""
        return f"{self.product.name}{variant_str} @ {self.warehouse.name}: {self.quantity_on_hand}"

    @property
    def available_quantity(self):
        return self.quantity_on_hand - self.quantity_reserved

    def clean(self):
        if self.quantity_on_hand < 0:
            raise ValidationError('Stock cannot go negative.')


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('SALE', 'Sale'),
        ('PURCHASE', 'Purchase'),
        ('ADJUSTMENT', 'Adjustment'),
        ('TRANSFER_OUT', 'Transfer Out'),
        ('TRANSFER_IN', 'Transfer In'),
        ('COUNT_CORRECTION', 'Count Correction'),
        ('RETURN', 'Return'),
    ]
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='stock_movements')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_movements')
    batch = models.ForeignKey('catalog.Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    serial = models.ForeignKey('catalog.SerialNumber', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, db_index=True)
    quantity_delta = models.IntegerField()
    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.IntegerField(null=True, blank=True, db_index=True)
    reason_code = models.ForeignKey(ReasonCode, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stock_movements')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()}: {self.product.name} ({self.quantity_delta:+d}) @ {self.warehouse.name}"


class StockAdjustment(models.Model):
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='adjustments')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='adjustments')
    quantity_delta = models.IntegerField()
    reason_code = models.ForeignKey(ReasonCode, on_delete=models.CASCADE)
    note = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stock_adjustments')
    movement = models.OneToOneField(StockMovement, on_delete=models.CASCADE, related_name='adjustment_detail')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Adjustment: {self.product.name} ({self.quantity_delta:+d})"


class StockTransfer(models.Model):
    STATUS_CHOICES = [
        ('Requested', 'Requested'),
        ('In Transit', 'In Transit'),
        ('Received', 'Received'),
        ('Cancelled', 'Cancelled'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    source_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_out')
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_in')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Requested')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_transfers')
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transfers')
    requested_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Transfer {self.pk}: {self.source_warehouse.name} -> {self.destination_warehouse.name} ({self.status})"


class StockTransferLine(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    movement_out = models.ForeignKey(StockMovement, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfer_out_lines')
    movement_in = models.ForeignKey(StockMovement, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfer_in_lines')

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class StockCountSession(models.Model):
    STATUS_CHOICES = [
        ('In Progress', 'In Progress'),
        ('Committed', 'Committed'),
        ('Cancelled', 'Cancelled'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='count_sessions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='In Progress')
    started_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='started_counts')
    started_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Count Session #{self.pk} at {self.warehouse.name} ({self.status})"


class StockCountLine(models.Model):
    session = models.ForeignKey(StockCountSession, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    expected_qty = models.IntegerField()
    counted_qty = models.IntegerField(null=True, blank=True)
    movement = models.ForeignKey(StockMovement, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def variance(self):
        if self.counted_qty is not None:
            return self.counted_qty - self.expected_qty
        return None

    def __str__(self):
        return f"{self.product.name}: expected {self.expected_qty}, counted {self.counted_qty}"
