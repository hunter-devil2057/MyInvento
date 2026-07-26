from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StockLevel


@receiver(post_save, sender='catalog.Product')
def create_stock_levels_for_new_product(sender, instance, created, **kwargs):
    if not created:
        return
    from inventory.models import Warehouse
    warehouses = Warehouse.objects.filter(is_active=True)
    for warehouse in warehouses:
        StockLevel.objects.get_or_create(
            product=instance, variant=None, warehouse=warehouse,
            defaults={'quantity_on_hand': 0}
        )


@receiver(post_save, sender='inventory.Warehouse')
def create_stock_levels_for_new_warehouse(sender, instance, created, **kwargs):
    if not created:
        return
    from catalog.models import Product
    products = Product.objects.filter(is_active=True)
    for product in products:
        StockLevel.objects.get_or_create(
            product=product, variant=None, warehouse=instance,
            defaults={'quantity_on_hand': 0}
        )


@receiver(post_save, sender=StockLevel)
def generate_low_stock_alert(sender, instance, **kwargs):
    try:
        from accounts.models import SystemSettings
        threshold = SystemSettings.objects.first().low_stock_threshold
    except Exception:
        threshold = 10
    from notifications.models import Alert, Notification
    from django.contrib.auth.models import User

    existing = Alert.objects.filter(
        product=instance.product,
        warehouse=instance.warehouse,
        is_resolved=False,
    )

    if instance.quantity_on_hand <= 0:
        alert, created_alert = Alert.objects.update_or_create(
            product=instance.product,
            warehouse=instance.warehouse,
            alert_type='Out of Stock',
            is_resolved=False,
            defaults={
                'message': f'{instance.product.name} is out of stock at {instance.warehouse.name}.',
                'severity': 'Critical',
            }
        )
        if created_alert:
            _notify_admins(
                title=f'Out of Stock: {instance.product.name}',
                message=f'{instance.product.name} is now out of stock at {instance.warehouse.name}. Customers cannot purchase this item.',
                link='/notifications/alerts/',
                severity='Critical',
            )
    elif instance.quantity_on_hand <= threshold:
        alert, created_alert = Alert.objects.update_or_create(
            product=instance.product,
            warehouse=instance.warehouse,
            alert_type='Low Stock',
            is_resolved=False,
            defaults={
                'message': f'{instance.product.name} is low on stock at {instance.warehouse.name} ({instance.quantity_on_hand} remaining).',
                'severity': 'Warning',
            }
        )
        if created_alert:
            _notify_admins(
                title=f'Low Stock: {instance.product.name}',
                message=f'{instance.product.name} has only {instance.quantity_on_hand} units left at {instance.warehouse.name}.',
                link='/notifications/alerts/',
                severity='Warning',
            )
    else:
        existing.filter(alert_type__in=['Low Stock', 'Out of Stock']).update(is_resolved=True)


def _notify_admins(title, message, link='', severity='Info'):
    """Create a notification for all admin users."""
    from notifications.models import Notification
    from django.contrib.auth.models import User
    from accounts.models import UserProfile

    admins = User.objects.filter(
        is_active=True,
        profile__role__in=['admin', 'warehouse']
    ).distinct()

    for admin in admins:
        Notification.objects.get_or_create(
            user=admin,
            title=title,
            defaults={'body': message, 'link': link},
        )
