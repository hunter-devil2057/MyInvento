import uuid
from django.db import models
from django.contrib.auth.models import User


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent', 'Sent'),
        ('Partially Received', 'Partially Received'),
        ('Received', 'Received'),
        ('Closed', 'Closed'),
        ('Cancelled', 'Cancelled'),
    ]
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    po_number = models.CharField(max_length=30, unique=True)
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE, related_name='purchase_orders')
    destination_warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.CASCADE, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    order_date = models.DateField()
    expected_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_pos')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PO {self.po_number} - {self.supplier.name}"

    @property
    def total_cost(self):
        return sum(line.quantity_ordered * line.unit_cost for line in self.lines.all())

    @property
    def total_received_cost(self):
        return sum(
            line.quantity_received * (line.received_unit_cost or line.unit_cost)
            for line in self.lines.all()
        )


class PurchaseOrderLine(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='po_lines')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    quantity_ordered = models.IntegerField()
    quantity_received = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    received_unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    batch_number = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} x{self.quantity_ordered}"

    @property
    def is_fully_received(self):
        return self.quantity_received >= self.quantity_ordered

    @property
    def remaining_quantity(self):
        return max(0, self.quantity_ordered - self.quantity_received)


class ReorderRule(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='reorder_rules')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, null=True, blank=True)
    min_quantity = models.IntegerField()
    max_quantity = models.IntegerField()
    default_supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE, related_name='reorder_rules')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['product']

    def __str__(self):
        return f"Reorder {self.product.name}: min={self.min_quantity}, max={self.max_quantity}"
