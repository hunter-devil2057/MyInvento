from django.urls import path
from . import views

urlpatterns = [
    path('', views.supplier_list_view, name='supplier_list'),
    path('create/', views.supplier_create_view, name='supplier_create'),
    path('<uuid:uuid>/', views.supplier_detail_view, name='supplier_detail'),
    path('<uuid:uuid>/edit/', views.supplier_edit_view, name='supplier_edit'),
    path('<uuid:uuid>/delete/', views.supplier_delete_view, name='supplier_delete'),
]
