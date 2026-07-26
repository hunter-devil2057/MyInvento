from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
import re

EXEMPT_URLS = [
    r'^/accounts/login/',
    r'^/accounts/register/',
    r'^/accounts/logout/',
    r'^/admin/',
    r'^/api/schema/',
    r'^/static/',
    r'^/media/',
    r'^/customers/$',                     # portal home
    r'^/customers/register/',
    r'^/customers/login/',
    r'^/customers/logout/',
    r'^/customers/catalog/',
]


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        path = request.path_info
        for pattern in EXEMPT_URLS:
            if re.match(pattern, path):
                return self.get_response(request)

        if path.startswith('/customers/'):
            try:
                portal_login = reverse('portal_login')
            except NoReverseMatch:
                portal_login = '/customers/login/'
            return redirect(f'{portal_login}?next={path}')

        try:
            login_url = reverse('login')
        except NoReverseMatch:
            login_url = '/accounts/login/'

        return redirect(f'{login_url}?next={path}')
