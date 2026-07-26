from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list_view, name='product_list'),
    path('create/', views.product_create_view, name='product_create'),
    path('<uuid:uuid>/', views.product_detail_view, name='product_detail'),
    path('<uuid:uuid>/edit/', views.product_edit_view, name='product_edit'),
    path('<uuid:uuid>/delete/', views.product_delete_view, name='product_delete'),
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/create/', views.category_create_view, name='category_create'),
    path('categories/<uuid:uuid>/edit/', views.category_edit_view, name='category_edit'),
    path('categories/<uuid:uuid>/delete/', views.category_delete_view, name='category_delete'),
    path('products/<uuid:product_uuid>/variants/create/', views.variant_create_view, name='variant_create'),
    path('variants/<uuid:uuid>/edit/', views.variant_edit_view, name='variant_edit'),
    path('variants/<uuid:uuid>/delete/', views.variant_delete_view, name='variant_delete'),
    path('<uuid:uuid>/upload-image/', views.product_image_upload_view, name='product_image_upload'),
    path('api/products/', views.product_api_list, name='product_api_list'),
]
