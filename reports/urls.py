from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_home_view, name='reports_home'),
    path('stock-valuation/', views.stock_valuation_view, name='stock_valuation'),
    path('sales-report/', views.sales_report_view, name='sales_report'),
    path('purchase-report/', views.purchase_report_view, name='purchase_report'),
    path('shrinkage/', views.shrinkage_report_view, name='shrinkage_report'),
    path('supplier-performance/', views.supplier_performance_view, name='supplier_performance'),
    path('product-performance/', views.product_performance_view, name='product_performance'),
    path('profit-loss/', views.profit_loss_view, name='profit_loss'),
    path('payment-methods/', views.payment_methods_view, name='payment_methods'),
    path('returns-analysis/', views.returns_analysis_view, name='returns_analysis'),
    path('category-analysis/', views.category_analysis_view, name='category_analysis'),
    path('stock-health/', views.stock_health_view, name='stock_health'),
    path('pdf/<str:report_type>/', views.generate_pdf_view, name='generate_pdf'),
    path('export/csv/<str:report_type>/', views.export_csv_view, name='export_csv'),
]
