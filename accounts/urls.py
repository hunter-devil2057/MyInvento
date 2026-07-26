from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('password-change/', views.password_change_view, name='password_change'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('users/', views.user_list_view, name='user_list'),
    path('users/bulk/', views.user_bulk_action_view, name='user_bulk_action'),
    path('users/<int:pk>/', views.user_detail_view, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:pk>/deactivate/', views.user_deactivate_view, name='user_deactivate'),
    path('users/<int:pk>/activate/', views.user_activate_view, name='user_activate'),
    path('users/<int:pk>/delete/', views.user_delete_view, name='user_delete'),
    path('users/<int:pk>/role/', views.user_role_change_view, name='user_role_change'),
    path('users/<int:pk>/reset-password/', views.admin_reset_password_view, name='admin_reset_password'),
]
