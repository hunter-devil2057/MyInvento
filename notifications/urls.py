from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list_view, name='notification_list'),
    path('<int:pk>/read/', views.notification_read_view, name='notification_read'),
    path('mark-all-read/', views.notification_mark_all_read_view, name='notification_mark_all_read'),
    path('alerts/', views.alert_list_view, name='alert_list'),
    path('alerts/<int:pk>/resolve/', views.alert_resolve_view, name='alert_resolve'),
]
