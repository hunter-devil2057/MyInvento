from .models import UserProfile


def role_context(request):
    context = {}
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            context['user_role'] = profile.role
            context['user_profile'] = profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user, role='admin' if request.user.is_superuser else 'sales')
            context['user_role'] = profile.role
            context['user_profile'] = profile
    return context
