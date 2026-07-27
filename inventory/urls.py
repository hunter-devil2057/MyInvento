from django.urls import path
from . import views
from .api import warehouse_stock_api_view

urlpatterns = [
    path('api/warehouse-stock/<int:warehouse_id>/', warehouse_stock_api_view, name='warehouse_stock_api'),
    path('', views.stock_overview_view, name='stock_overview'),
    path('adjust/', views.stock_adjust_view, name='stock_adjust'),
    path('adjust/<uuid:product_uuid>/', views.stock_adjust_product_view, name='stock_adjust_product'),
    path('transfer/', views.stock_transfer_list_view, name='stock_transfer_list'),
    path('transfer/create/', views.stock_transfer_create_view, name='stock_transfer_create'),
    path('transfer/<uuid:uuid>/', views.stock_transfer_detail_view, name='stock_transfer_detail'),
    path('transfer/<uuid:uuid>/receive/', views.stock_transfer_receive_view, name='stock_transfer_receive'),
    path('counts/', views.stock_count_list_view, name='stock_count_list'),
    path('counts/create/', views.stock_count_create_view, name='stock_count_create'),
    path('counts/<uuid:uuid>/', views.stock_count_detail_view, name='stock_count_detail'),
    path('counts/<uuid:uuid>/commit/', views.stock_count_commit_view, name='stock_count_commit'),
    path('movements/', views.stock_movement_list_view, name='stock_movement_list'),
    path('warehouses/', views.warehouse_list_view, name='warehouse_list'),
    path('warehouses/create/', views.warehouse_create_view, name='warehouse_create'),
    path('warehouses/<uuid:uuid>/edit/', views.warehouse_edit_view, name='warehouse_edit'),
    path('warehouses/<uuid:uuid>/delete/', views.warehouse_delete_view, name='warehouse_delete'),
]
