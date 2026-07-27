from .models import Notification, Alert


def notification_context(request):
    context = {}
    if request.user.is_authenticated:
        notif_unread = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        alert_unread = Alert.objects.filter(is_resolved=False).count()
        context['unread_notifications'] = notif_unread + alert_unread
        context['recent_notifications'] = Notification.objects.filter(
            user=request.user
        )[:5]
    return context
