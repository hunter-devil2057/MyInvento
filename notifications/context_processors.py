from .models import Notification


def notification_context(request):
    context = {}
    if request.user.is_authenticated:
        context['unread_notifications'] = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        context['recent_notifications'] = Notification.objects.filter(
            user=request.user
        )[:5]
    return context
