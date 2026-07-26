from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_panel_view, name='admin_panel'),
    path('settings/', views.system_settings_view, name='system_settings'),
    path('user-activity/', views.admin_user_activity_view, name='admin_user_activity'),
    path('system-health/', views.admin_system_health_view, name='admin_system_health'),
    path('quick-actions/', views.admin_quick_actions_view, name='admin_quick_actions'),
    path('complaints/', views.admin_complaint_list_view, name='admin_complaint_list'),
    path('complaints/<int:pk>/', views.admin_complaint_detail_view, name='admin_complaint_detail'),
]
