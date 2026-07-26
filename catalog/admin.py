from django.contrib import admin
from .models import Category, Product, ProductVariant, ProductImage, Batch, SerialNumber, SupplierProduct


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'category', 'sale_price', 'is_published', 'is_active']
    list_filter = ['is_published', 'is_active', 'category']
    search_fields = ['name', 'sku']
    fieldsets = [
        (None, {'fields': ['sku', 'name', 'slug', 'description', 'category']}),
        ('Pricing', {'fields': ['cost_price', 'sale_price', 'tax_class', 'valuation_method']}),
        ('Image', {'fields': ['image_url'], 'description': 'Paste an online image URL (e.g. from Google Images, Amazon, etc.)'}),
        ('Settings', {'fields': ['unit_of_measure', 'track_batches', 'track_serials', 'is_active', 'is_published']}),
    ]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['sku', 'product', 'is_active']


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'variant', 'is_primary', 'order']


admin.site.register(Batch)
admin.site.register(SerialNumber)
admin.site.register(SupplierProduct)
