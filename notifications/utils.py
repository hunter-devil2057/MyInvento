from notifications.models import Notification
from django.contrib.auth.models import User


def notify_user(user, title, body, link=''):
    Notification.objects.get_or_create(
        user=user, title=title,
        defaults={'body': body, 'link': link},
    )


def notify_admins(title, body, link='', exclude_user=None):
    from accounts.models import UserProfile
    users = User.objects.filter(
        is_active=True,
        profile__role__in=['admin', 'warehouse']
    ).distinct()
    if exclude_user:
        users = users.exclude(pk=exclude_user.pk)
    for user in users:
        Notification.objects.get_or_create(
            user=user, title=title,
            defaults={'body': body, 'link': link},
        )


def notify_role(role, title, body, link='', exclude_user=None):
    from accounts.models import UserProfile
    users = User.objects.filter(
        is_active=True, profile__role=role
    ).distinct()
    if exclude_user:
        users = users.exclude(pk=exclude_user.pk)
    for user in users:
        Notification.objects.get_or_create(
            user=user, title=title,
            defaults={'body': body, 'link': link},
        )
