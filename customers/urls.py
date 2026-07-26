from django.urls import path
from . import views

urlpatterns = [
    path('', views.portal_home_view, name='portal_home'),
    path('register/', views.portal_register_view, name='portal_register'),
    path('login/', views.portal_login_view, name='portal_login'),
    path('logout/', views.portal_logout_view, name='portal_logout'),
    path('catalog/', views.portal_catalog_view, name='portal_catalog'),
    path('catalog/<int:pk>/', views.portal_product_detail_view, name='portal_product_detail'),
    path('cart/', views.portal_cart_view, name='portal_cart'),
    path('cart/add/<int:product_id>/', views.portal_cart_add_view, name='portal_cart_add'),
    path('cart/update/<int:item_id>/', views.portal_cart_update_view, name='portal_cart_update'),
    path('cart/remove/<int:item_id>/', views.portal_cart_remove_view, name='portal_cart_remove'),
    path('checkout/', views.portal_checkout_view, name='portal_checkout'),
    path('checkout/khalti/callback/', views.portal_khalti_callback_view, name='portal_khalti_callback'),
    path('orders/', views.portal_order_list_view, name='portal_order_list'),
    path('orders/<int:pk>/', views.portal_order_detail_view, name='portal_order_detail'),
    path('orders/<int:pk>/return/', views.portal_return_request_view, name='portal_return_request'),
    path('settings/', views.portal_settings_view, name='portal_settings'),
    path('support/', views.portal_complaint_list_view, name='portal_complaint_list'),
    path('support/new/', views.portal_complaint_create_view, name='portal_complaint_create'),
    path('support/<int:pk>/', views.portal_complaint_detail_view, name='portal_complaint_detail'),
]
