from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api

router = DefaultRouter()
router.register(r'products', api.ProductViewSet)
router.register(r'customers', api.CustomerViewSet)
router.register(r'suppliers', api.SupplierViewSet)
router.register(r'transactions', api.TransactionViewSet)
router.register(r'stock-levels', api.StockLevelViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', api.dashboard_api_view, name='api_dashboard'),
    path('stock-search/', api.stock_search_api_view, name='api_stock_search'),
    path('pos/products/', api.pos_products_api_view, name='api_pos_products'),
    path('pos/categories/', api.pos_categories_api_view, name='api_pos_categories'),
]
