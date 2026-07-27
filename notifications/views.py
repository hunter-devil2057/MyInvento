from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Max
from django.http import JsonResponse
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Notification, Alert
from inventory.models import (StockLevel, StockTransfer, StockTransferLine,
                               StockMovement, Warehouse)
from purchasing.models import PurchaseOrder, PurchaseOrderLine, ReorderRule
from audit.utils import log_action
import datetime


@login_required
def notification_api_recent_view(request):
    notifs = list(Notification.objects.filter(user=request.user).order_by('-created_at')[:30])
    recent_alerts = list(Alert.objects.order_by('-created_at')[:50])

    all_items = []
    for n in notifs:
        severity = _notif_severity(n.title)
        category = _notif_category(n.title)
        all_items.append({
            'id': f'n-{n.pk}',
            'title': n.title,
            'body': n.body,
            'link': n.link or '/notifications/',
            'is_read': n.is_read,
            '_dt': n.created_at,
            'severity': severity,
            'category': category,
            'icon': _notif_detail_icon(n.title),
            'icon_bg': _notif_detail_icon_bg(n.title),
            'icon_color': _notif_detail_icon_color(n.title),
            'source': 'notification',
        })
    for a in recent_alerts:
        title = f'[{a.severity}] {a.alert_type}: {a.message[:80]}'
        sev = a.severity.lower() if a.severity else 'info'
        if sev == 'critical':
            icon = 'fa-solid fa-triangle-exclamation'
            icon_bg = '#fef2f2'
            icon_color = '#dc2626'
        elif sev == 'warning':
            icon = 'fa-solid fa-circle-exclamation'
            icon_bg = '#fffbeb'
            icon_color = '#d97706'
        else:
            icon = 'fa-solid fa-circle-info'
            icon_bg = '#eff6ff'
            icon_color = '#2563eb'
        all_items.append({
            'id': f'a-{a.pk}',
            'title': title,
            'body': a.message,
            'link': '/notifications/alerts/',
            'is_read': a.is_resolved,
            '_dt': a.created_at,
            'severity': sev,
            'category': 'Inventory',
            'icon': icon,
            'icon_bg': icon_bg,
            'icon_color': icon_color,
            'source': 'alert',
        })

    all_items.sort(key=lambda x: x['_dt'], reverse=True)

    data = []
    for item in all_items:
        item['created_at'] = _time_ago(item['_dt'])
        del item['_dt']
        data.append(item)

    unread_count = Notification.objects.filter(user=request.user, is_read=False).count() + Alert.objects.filter(is_resolved=False).count()
    return JsonResponse({'notifications': data, 'unread_count': unread_count})


def _notif_severity(title):
    t = title.lower()
    if 'out of stock' in t or 'critical' in t:
        return 'critical'
    if 'low stock' in t or 'warning' in t:
        return 'warning'
    if 'resolved' in t or 'completed' in t or 'success' in t:
        return 'success'
    return 'info'


def _notif_detail_icon(title):
    t = title.lower()
    if 'out of stock' in t:
        return 'fa-solid fa-box-archive'
    if 'low stock' in t:
        return 'fa-solid fa-triangle-exclamation'
    if 'transfer' in t:
        return 'fa-solid fa-truck-moving'
    if 'purchase order' in t or t.startswith('po ') or 'receiving' in t:
        return 'fa-solid fa-file-invoice'
    if 'sale' in t or 'order' in t or 'invoice' in t:
        return 'fa-solid fa-cart-shopping'
    if 'return' in t:
        return 'fa-solid fa-rotate-left'
    if 'complaint' in t or 'support' in t:
        return 'fa-solid fa-headset'
    if 'user' in t or 'account' in t or 'role' in t:
        return 'fa-solid fa-user-plus'
    if 'warehouse' in t:
        return 'fa-solid fa-warehouse'
    if 'product' in t:
        return 'fa-solid fa-box'
    if 'resolved' in t:
        return 'fa-solid fa-circle-check'
    if 'adjust' in t or 'count' in t:
        return 'fa-solid fa-clipboard-list'
    if 'supplier' in t:
        return 'fa-solid fa-truck'
    return 'fa-solid fa-bell'


def _notif_detail_icon_bg(title):
    t = title.lower()
    if 'out of stock' in t:
        return '#fef2f2'
    if 'low stock' in t:
        return '#fffbeb'
    if 'transfer' in t:
        return '#f0f9ff'
    if 'purchase order' in t or t.startswith('po ') or 'receiving' in t:
        return '#fefce8'
    if 'sale' in t or 'order' in t or 'invoice' in t:
        return '#ecfdf5'
    if 'return' in t:
        return '#fff1f2'
    if 'complaint' in t or 'support' in t:
        return '#fff7ed'
    if 'user' in t or 'account' in t or 'role' in t:
        return '#fdf4ff'
    if 'warehouse' in t:
        return '#f0f9ff'
    if 'product' in t:
        return '#faf5ff'
    if 'resolved' in t:
        return '#f0fdf4'
    if 'supplier' in t:
        return '#fef3c7'
    return '#eff6ff'


def _notif_detail_icon_color(title):
    t = title.lower()
    if 'out of stock' in t:
        return '#dc2626'
    if 'low stock' in t:
        return '#d97706'
    if 'transfer' in t:
        return '#0284c7'
    if 'purchase order' in t or t.startswith('po ') or 'receiving' in t:
        return '#ca8a04'
    if 'sale' in t or 'order' in t or 'invoice' in t:
        return '#059669'
    if 'return' in t:
        return '#e11d48'
    if 'complaint' in t or 'support' in t:
        return '#ea580c'
    if 'user' in t or 'account' in t or 'role' in t:
        return '#c026d3'
    if 'warehouse' in t:
        return '#0284c7'
    if 'product' in t:
        return '#9333ea'
    if 'resolved' in t:
        return '#16a34a'
    if 'supplier' in t:
        return '#b45309'
    return '#2563eb'


def _time_ago(dt):
    from django.utils import timezone as tz
    diff = tz.now() - dt
    secs = int(diff.total_seconds())
    if secs < 60:
        return 'just now'
    mins = secs // 60
    if mins < 60:
        return f'{mins}m ago'
    hours = mins // 60
    if hours < 24:
        return f'{hours}h ago'
    days = hours // 24
    if days < 7:
        return f'{days}d ago'
    return dt.strftime('%b %d')


def _notif_category(title):
    t = title.lower()
    if any(w in t for w in ['stock', 'out of stock', 'low stock', 'reorder']):
        return 'Inventory'
    if any(w in t for w in ['purchase order', 'po ', 'receiving', 'supplier']):
        return 'Purchasing'
    if any(w in t for w in ['sale', 'transaction', 'pos', 'payment', 'invoice']):
        return 'Sales'
    if any(w in t for w in ['complaint', 'support', 'ticket']):
        return 'Support'
    if any(w in t for w in ['user', 'account', 'password', 'login']):
        return 'Account'
    if any(w in t for w in ['transfer', 'warehouse', 'count']):
        return 'Inventory'
    return 'General'


def _notif_icon(cat):
    return {
        'Inventory': 'fa-solid fa-boxes-stacked',
        'Purchasing': 'fa-solid fa-cart-shopping',
        'Sales': 'fa-solid fa-cash-register',
        'Support': 'fa-solid fa-headset',
        'Account': 'fa-solid fa-user-shield',
        'General': 'fa-solid fa-bell',
    }.get(cat, 'fa-solid fa-bell')


def _notif_color(cat):
    return {
        'Inventory': '#6366f1',
        'Purchasing': '#a855f7',
        'Sales': '#059669',
        'Support': '#f59e0b',
        'Account': '#3b82f6',
        'General': '#64748b',
    }.get(cat, '#64748b')


def _notif_tag(cat):
    return {
        'Inventory': 'INV',
        'Purchasing': 'PUR',
        'Sales': 'SAL',
        'Support': 'SUP',
        'Account': 'ACC',
        'General': 'GEN',
    }.get(cat, 'GEN')


@login_required
def notification_list_view(request):
    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications, 'unread_count': unread_count,
    })


@login_required
def notification_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    log_action(request.user, 'Update', 'Notification', notification.pk, f'Marked notification as read: {notification.title}', ip_address=request.META.get('REMOTE_ADDR'))
    if notification.link:
        return redirect(notification.link)
    return redirect('notification_list')


@login_required
def notification_mark_all_read_view(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('notification_list')


@login_required
def alert_list_view(request):
    from inventory.models import StockLevel, Warehouse

    alerts = Alert.objects.select_related('product', 'warehouse').all()

    if request.method == 'POST':
        severity_filter = request.POST.get('severity', '')
        status_filter = request.POST.get('status', '')
        warehouse_filter = request.POST.get('warehouse', '')
    else:
        severity_filter = ''
        status_filter = ''
        warehouse_filter = ''

    if severity_filter:
        alerts = alerts.filter(severity=severity_filter)
    if status_filter == 'resolved':
        alerts = alerts.filter(is_resolved=True)
    elif status_filter == 'active':
        alerts = alerts.filter(is_resolved=False)
    if warehouse_filter:
        alerts = alerts.filter(warehouse_id=warehouse_filter)

    product_totals = dict(
        StockLevel.objects.values_list('product_id')
        .annotate(total=Sum('quantity_on_hand'))
        .values_list('product_id', 'total')
    )

    alert_data = []
    for alert in alerts:
        total_qty = product_totals.get(alert.product_id, 0) if alert.product_id else None
        warehouse_qty = None
        if alert.product and alert.warehouse:
            sl = StockLevel.objects.filter(
                product=alert.product, warehouse=alert.warehouse
            ).first()
            warehouse_qty = sl.quantity_on_hand if sl else 0
        alert_data.append({
            'alert': alert,
            'qty': total_qty,
            'warehouse_qty': warehouse_qty,
        })

    warehouses = Warehouse.objects.filter(is_active=True)
    summary = {
        'total': Alert.objects.count(),
        'active': Alert.objects.filter(is_resolved=False).count(),
        'resolved': Alert.objects.filter(is_resolved=True).count(),
        'critical': Alert.objects.filter(is_resolved=False, severity='Critical').count(),
        'warning': Alert.objects.filter(is_resolved=False, severity='Warning').count(),
    }

    return render(request, 'notifications/alert_list.html', {
        'alert_data': alert_data,
        'warehouses': warehouses,
        'severity_filter': severity_filter,
        'status_filter': status_filter,
        'warehouse_filter': warehouse_filter,
        'summary': summary,
    })


@login_required
def alert_resolve_view(request, pk):
    alert = get_object_or_404(Alert, pk=pk, is_resolved=False)
    if request.method != 'POST':
        return redirect('alert_list')

    product = alert.product
    warehouse = alert.warehouse

    if not product:
        alert.is_resolved = True
        alert.save()
        messages.success(request, 'Alert resolved.')
        return redirect('alert_list')

    if alert.alert_type == 'Out of Stock' and warehouse:
        source = StockLevel.objects.filter(
            product=product, warehouse__is_active=True
        ).exclude(warehouse=warehouse).filter(
            quantity_on_hand__gt=0
        ).order_by('-quantity_on_hand').first()

        if source:
            qty_to_transfer = min(source.quantity_on_hand, 20)
            transfer = StockTransfer.objects.create(
                source_warehouse=source.warehouse,
                destination_warehouse=warehouse,
                status='In Transit',
                requested_by=request.user,
                received_by=request.user,
                received_at=timezone.now(),
                notes=f'Auto-created to resolve alert: {product.name} out of stock at {warehouse.name}',
            )
            StockTransferLine.objects.create(
                transfer=transfer, product=product, quantity=qty_to_transfer,
            )
            for line in transfer.lines.select_related('product', 'variant').all():
                movement_out = StockMovement.objects.create(
                    product=line.product, variant=line.variant,
                    warehouse=transfer.source_warehouse,
                    movement_type='TRANSFER_OUT', quantity_delta=-line.quantity,
                    user=request.user, notes=f'Transfer #{transfer.pk} out (auto-resolve alert)',
                )
                src_sl = StockLevel.objects.get(
                    product=line.product, variant=line.variant,
                    warehouse=transfer.source_warehouse,
                )
                src_sl.quantity_on_hand -= line.quantity
                src_sl.save()
                line.movement_out = movement_out

                movement_in = StockMovement.objects.create(
                    product=line.product, variant=line.variant,
                    warehouse=transfer.destination_warehouse,
                    movement_type='TRANSFER_IN', quantity_delta=line.quantity,
                    user=request.user, notes=f'Transfer #{transfer.pk} received (auto-resolve alert)',
                )
                dest_sl, _ = StockLevel.objects.get_or_create(
                    product=line.product, variant=line.variant,
                    warehouse=transfer.destination_warehouse,
                    defaults={'quantity_on_hand': 0}
                )
                dest_sl.quantity_on_hand += line.quantity
                dest_sl.save()
                line.movement_in = movement_in
                line.save()
            transfer.status = 'Received'
            transfer.save()

            alert.is_resolved = True
            alert.save()
            log_action(request.user, 'Create', 'StockTransfer', transfer.pk,
                       f'Auto-transfer + receive: {product.name} x{qty_to_transfer} from {source.warehouse.name} to {warehouse.name}',
                       ip_address=request.META.get('REMOTE_ADDR'))
            messages.success(request,
                f'Transfer completed: {qty_to_transfer}x {product.name} moved from {source.warehouse.name} → {warehouse.name}')
            return redirect('stock_transfer_detail', uuid=transfer.uuid)
        else:
            reorder = ReorderRule.objects.filter(
                product=product, is_active=True
            ).select_related('default_supplier', 'warehouse').first()

            if reorder:
                po = _create_restock_po(reorder, product, request.user)
                alert.is_resolved = True
                alert.save()
                messages.success(request, f'PO {po.po_number} created: {product.name} x{reorder.max_quantity} from {reorder.default_supplier.name}')
                return redirect('po_detail', uuid=po.uuid)
            else:
                alert.is_resolved = True
                alert.save()
                messages.warning(request,
                    f'No stock available at other warehouses and no reorder rule for {product.name}. Please create a PO manually.')
                return redirect('alert_list')

    elif alert.alert_type == 'Low Stock':
        reorder = ReorderRule.objects.filter(
            product=product, is_active=True
        ).select_related('default_supplier', 'warehouse').first()

        if reorder:
            po = _create_restock_po(reorder, product, request.user)
            alert.is_resolved = True
            alert.save()
            messages.success(request, f'PO {po.po_number} created: {product.name} x{reorder.max_quantity} from {reorder.default_supplier.name}')
            return redirect('po_detail', uuid=po.uuid)
        else:
            alert.is_resolved = True
            alert.save()
            messages.warning(request,
                f'No reorder rule for {product.name}. Please create a PO manually.')
            return redirect('alert_list')

    else:
        alert.is_resolved = True
        alert.save()
        messages.success(request, 'Alert resolved.')
        return redirect('alert_list')


def _create_restock_po(reorder, product, user):
    from django.utils import timezone as tz
    from suppliers.models import Supplier
    from catalog.models import Product

    destination = reorder.warehouse or Warehouse.objects.first()
    po = PurchaseOrder.objects.create(
        po_number=f"PO-{tz.now().strftime('%Y%m%d')}-{(PurchaseOrder.objects.aggregate(m=Max('pk'))['m'] or 0) + 1:04d}",
        supplier=reorder.default_supplier,
        destination_warehouse=destination,
        status='Draft',
        order_date=tz.now().date(),
        expected_date=tz.now().date() + datetime.timedelta(days=reorder.default_supplier.lead_time_days),
        created_by=user,
        notes=f'Auto-created from reorder rule: {product.name} (min={reorder.min_quantity}, max={reorder.max_quantity})',
    )
    unit_cost = product.cost_price or 0
    PurchaseOrderLine.objects.create(
        po=po, product=product,
        quantity_ordered=reorder.max_quantity,
        unit_cost=unit_cost,
    )
    log_action(user, 'Create', 'PurchaseOrder', po.pk,
               f'Auto PO {po.po_number}: {product.name} x{reorder.max_quantity}',
               ip_address=None)
    return po
