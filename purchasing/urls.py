from django.urls import path
from . import views

urlpatterns = [
    path('', views.po_list_view, name='po_list'),
    path('create/', views.po_create_view, name='po_create'),
    path('<uuid:uuid>/', views.po_detail_view, name='po_detail'),
    path('<uuid:uuid>/edit/', views.po_edit_view, name='po_edit'),
    path('<uuid:uuid>/send/', views.po_send_view, name='po_send'),
    path('<uuid:uuid>/receive/', views.po_receive_view, name='po_receive'),
    path('<uuid:uuid>/cancel/', views.po_cancel_view, name='po_cancel'),
    path('<uuid:uuid>/delete/', views.po_delete_view, name='po_delete'),
    path('reorder-rules/', views.reorder_rule_list_view, name='reorder_rule_list'),
    path('reorder-rules/create/', views.reorder_rule_create_view, name='reorder_rule_create'),
    path('reorder-rules/<uuid:uuid>/edit/', views.reorder_rule_edit_view, name='reorder_rule_edit'),
    path('reorder-rules/<uuid:uuid>/delete/', views.reorder_rule_delete_view, name='reorder_rule_delete'),
]
