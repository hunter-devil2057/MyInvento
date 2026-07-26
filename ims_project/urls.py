from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda r: redirect('dashboard'), name='home'),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('reports.dashboard_urls')),
    path('catalog/', include('catalog.urls')),
    path('inventory/', include('inventory.urls')),
    path('suppliers/', include('suppliers.urls')),
    path('purchasing/', include('purchasing.urls')),
    path('sales/', include('sales.urls')),
    path('customers/', include('customers.urls')),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),
    path('audit/', include('audit.urls')),
    path('admin-panel/', include('accounts.admin_panel_urls')),
    path('api/', include('reports.api_urls')),
    path('api/schema/', include('reports.schema_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
