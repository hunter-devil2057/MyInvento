from rest_framework import serializers
from django.db.models import Sum
from catalog.models import Product, ProductVariant
from sales.models import Customer, SalesTransaction, SalesTransactionLine
from suppliers.models import Supplier
from inventory.models import StockLevel


class ProductSerializer(serializers.ModelSerializer):
    stock = serializers.SerializerMethodField()
    category = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'sku', 'name', 'sale_price', 'cost_price', 'is_active', 'category', 'stock']

    def get_stock(self, obj):
        qs = getattr(obj, 'stock_levels', None)
        if qs is not None:
            return qs.aggregate(total=Sum('quantity_on_hand'))['total'] or 0
        return 0


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True, default='')

    class Meta:
        model = SalesTransaction
        fields = '__all__'


class StockLevelSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = StockLevel
        fields = '__all__'
