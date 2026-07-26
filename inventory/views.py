from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F, DecimalField, ExpressionWrapper
from django.utils import timezone
from .models import (Warehouse, StockLevel, StockMovement, StockAdjustment,
                     StockTransfer, StockTransferLine, StockCountSession,
                     StockCountLine, ReasonCode)
from .forms import (WarehouseForm, StockAdjustForm, StockTransferForm,
                    StockTransferLineFormSet, StockCountForm, StockCountLineFormSet)
from catalog.models import Product, ProductVariant
from audit.utils import log_action


def _get_low_stock_threshold():
    from accounts.models import SystemSettings
    try:
        return SystemSettings.objects.first().low_stock_threshold
    except Exception:
        return 10


@login_required
def stock_overview_view(request):
    query = request.GET.get('q', '')
    warehouse_id = request.GET.get('warehouse', '')
    low_stock = request.GET.get('low_stock', '')
    threshold = _get_low_stock_threshold()
    stock_levels = StockLevel.objects.select_related(
        'product', 'variant', 'warehouse'
    ).filter(product__is_active=True)
    if query:
        stock_levels = stock_levels.filter(
            Q(product__name__icontains=query) | Q(product__sku__icontains=query)
        )
    if warehouse_id:
        stock_levels = stock_levels.filter(warehouse_id=warehouse_id)
    if low_stock == '1':
        stock_levels = stock_levels.filter(quantity_on_hand__lte=threshold)
    paginator = Paginator(stock_levels, 20)
    page = request.GET.get('page', 1)
    stock_page = paginator.get_page(page)
    warehouses = Warehouse.objects.filter(is_active=True)
    total_value = stock_levels.aggregate(
        total=Sum(F('quantity_on_hand') * F('product__sale_price'), output_field=DecimalField())
    )['total'] or 0
    return render(request, 'inventory/stock_overview.html', {
        'stock_levels': stock_page,
        'warehouses': warehouses,
        'query': query,
        'selected_warehouse': warehouse_id,
        'low_stock': low_stock,
        'total_value': total_value,
    })


@login_required
def stock_adjust_view(request):
    products = Product.objects.filter(is_active=True).order_by('name')
    return render(request, 'inventory/stock_adjust.html', {'products': products})


@login_required
def stock_adjust_product_view(request, product_uuid):
    product = get_object_or_404(Product, uuid=product_uuid)
    warehouses = Warehouse.objects.filter(is_active=True)
    reason_codes = ReasonCode.objects.all()
    if request.method == 'POST':
        warehouse_id = int(request.POST.get('warehouse'))
        quantity_delta = int(request.POST.get('quantity_delta'))
        reason_code_id = int(request.POST.get('reason_code'))
        note = request.POST.get('note', '')
        warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
        reason_code = get_object_or_404(ReasonCode, pk=reason_code_id)
        variant_id = request.POST.get('variant')
        variant = get_object_or_404(ProductVariant, pk=variant_id) if variant_id else None
        movement = StockMovement.objects.create(
            product=product,
            variant=variant,
            warehouse=warehouse,
            movement_type='ADJUSTMENT',
            quantity_delta=quantity_delta,
            reason_code=reason_code,
            user=request.user,
            notes=note,
        )
        stock_level, _ = StockLevel.objects.get_or_create(
            product=product, variant=variant, warehouse=warehouse,
            defaults={'quantity_on_hand': 0}
        )
        stock_level.quantity_on_hand += quantity_delta
        try:
            stock_level.full_clean()
        except ValidationError as e:
            messages.error(request, f'Cannot adjust: {e.message}')
            return redirect('stock_adjust_product', product_uuid=product_uuid)
        stock_level.save()
        StockAdjustment.objects.create(
            product=product, variant=variant, warehouse=warehouse,
            quantity_delta=quantity_delta, reason_code=reason_code,
            note=note, user=request.user, movement=movement,
        )
        log_action(request.user, 'Update', 'StockLevel', stock_level.pk,
                   f'Adjusted {product.name} by {quantity_delta:+d} at {warehouse.name}')
        from notifications.utils import notify_admins
        notify_admins(
            title=f'Stock Adjustment: {product.name}',
            body=f'{product.name} (SKU: {product.sku}) adjusted by {quantity_delta:+d} at {warehouse.name}. Old qty: {stock_level.quantity_on_hand - quantity_delta}, New qty: {stock_level.quantity_on_hand}. Reason: {reason_code.label} ({reason_code.code}). Adjusted by {request.user.username}. Note: {note or "None"}',
            link=f'/catalog/{product.uuid}/',
        )
        messages.success(request, f'Stock adjusted: {product.name} ({quantity_delta:+d}) at {warehouse.name}')
        return redirect('stock_overview')
    return render(request, 'inventory/stock_adjust_form.html', {
        'product': product, 'warehouses': warehouses, 'reason_codes': reason_codes,
    })


@login_required
def stock_transfer_list_view(request):
    transfers = StockTransfer.objects.select_related(
        'source_warehouse', 'destination_warehouse', 'requested_by', 'received_by'
    ).all()
    paginator = Paginator(transfers, 20)
    page = request.GET.get('page', 1)
    transfers_page = paginator.get_page(page)
    return render(request, 'inventory/stock_transfer_list.html', {'transfers': transfers_page})


@login_required
def stock_transfer_create_view(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True)
    if request.method == 'POST':
        form = StockTransferForm(request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.requested_by = request.user
            transfer.save()
            formset = StockTransferLineFormSet(request.POST, instance=transfer)
            if formset.is_valid():
                formset.save()
                log_action(request.user, 'Create', 'StockTransfer', transfer.pk, f'Transfer {transfer.pk} from {transfer.source_warehouse} to {transfer.destination_warehouse}', ip_address=request.META.get('REMOTE_ADDR'))
                from notifications.utils import notify_admins
                items_summary = ', '.join(f'{l.product.name} x{l.quantity}' for l in transfer.lines.select_related('product').all()[:5])
                more_items = f' (+{transfer.lines.count() - 5} more)' if transfer.lines.count() > 5 else ''
                notify_admins(
                    title=f'Stock Transfer Created: #{transfer.pk}',
                    body=f'Transfer #{transfer.pk} from {transfer.source_warehouse.name} to {transfer.destination_warehouse.name} requested by {request.user.username}. Items ({transfer.lines.count()}): {items_summary}{more_items}.',
                    link=f'/inventory/transfer/{transfer.uuid}/',
                )
                messages.success(request, f'Transfer #{transfer.pk} created.')
                return redirect('stock_transfer_detail', uuid=transfer.uuid)
    else:
        form = StockTransferForm()
        formset = StockTransferLineFormSet()
    return render(request, 'inventory/stock_transfer_form.html', {
        'form': form, 'formset': formset, 'warehouses': warehouses, 'products': products,
    })


@login_required
def stock_transfer_detail_view(request, uuid):
    transfer = get_object_or_404(StockTransfer.objects.select_related(
        'source_warehouse', 'destination_warehouse', 'requested_by', 'received_by'
    ), uuid=uuid)
    lines = transfer.lines.select_related('product', 'variant').all()
    return render(request, 'inventory/stock_transfer_detail.html', {
        'transfer': transfer, 'lines': lines,
    })


@login_required
def stock_transfer_receive_view(request, uuid):
    transfer = get_object_or_404(StockTransfer, uuid=uuid)
    if request.method == 'POST' and transfer.status == 'In Transit':
        transfer.status = 'Received'
        transfer.received_by = request.user
        transfer.received_at = timezone.now()
        transfer.save()
        for line in transfer.lines.all():
            movement_out = StockMovement.objects.create(
                product=line.product, variant=line.variant,
                warehouse=transfer.source_warehouse,
                movement_type='TRANSFER_OUT', quantity_delta=-line.quantity,
                user=request.user, notes=f'Transfer #{transfer.pk} out',
            )
            source_sl, _ = StockLevel.objects.get_or_create(
                product=line.product, variant=line.variant,
                warehouse=transfer.source_warehouse,
                defaults={'quantity_on_hand': 0}
            )
            source_sl.quantity_on_hand -= line.quantity
            try:
                source_sl.full_clean()
            except ValidationError:
                source_sl.quantity_on_hand += line.quantity
                source_sl.save()
                messages.error(request, f'Insufficient stock for {line.product.name} at {transfer.source_warehouse.name}.')
                return redirect('stock_transfer_detail', uuid=uuid)
            source_sl.save()
            line.movement_out = movement_out

            movement_in = StockMovement.objects.create(
                product=line.product, variant=line.variant,
                warehouse=transfer.destination_warehouse,
                movement_type='TRANSFER_IN', quantity_delta=line.quantity,
                user=request.user, notes=f'Transfer #{transfer.pk} received',
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
        log_action(request.user, 'Update', 'StockTransfer', transfer.pk, f'Received transfer {transfer.pk}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        items_summary = ', '.join(f'{line.product.name} x{line.quantity}' for line in transfer.lines.select_related('product').all()[:5])
        more_items = f' (+{transfer.lines.count() - 5} more)' if transfer.lines.count() > 5 else ''
        notify_admins(
            title=f'Stock Transfer Received: #{transfer.pk}',
            body=f'Transfer #{transfer.pk} from {transfer.source_warehouse.name} to {transfer.destination_warehouse.name} received by {request.user.username}. Items ({transfer.lines.count()}): {items_summary}{more_items}. Stock updated at destination.',
            link=f'/inventory/transfer/{transfer.uuid}/',
        )
        messages.success(request, f'Transfer #{transfer.pk} received successfully.')
    return redirect('stock_transfer_detail', uuid=uuid)


@login_required
def stock_count_list_view(request):
    sessions = StockCountSession.objects.select_related('warehouse', 'started_by').all()
    paginator = Paginator(sessions, 20)
    page = request.GET.get('page', 1)
    sessions_page = paginator.get_page(page)
    return render(request, 'inventory/stock_count_list.html', {'sessions': sessions_page})


@login_required
def stock_count_create_view(request):
    if request.method == 'POST':
        form = StockCountForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.started_by = request.user
            session.save()
            stock_levels = StockLevel.objects.filter(
                warehouse=session.warehouse, product__is_active=True
            ).select_related('product', 'variant')
            for sl in stock_levels:
                StockCountLine.objects.create(
                    session=session, product=sl.product, variant=sl.variant,
                    expected_qty=sl.quantity_on_hand,
                )
            log_action(request.user, 'Create', 'StockCountSession', session.pk, f'Started count for {session.warehouse}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Stock Count Started: #{session.pk}',
                body=f'Stock count session #{session.pk} started at warehouse "{session.warehouse.name}" by {request.user.username}. Items to count: {stock_levels.count()}. Status: {session.status}.',
                link=f'/inventory/counts/{session.uuid}/',
            )
            messages.success(request, f'Count session #{session.pk} created with {stock_levels.count()} items.')
            return redirect('stock_count_detail', uuid=session.uuid)
    else:
        form = StockCountForm()
    return render(request, 'inventory/stock_count_form.html', {'form': form})


@login_required
def stock_count_detail_view(request, uuid):
    session = get_object_or_404(StockCountSession.objects.select_related('warehouse', 'started_by'), uuid=uuid)
    lines = session.lines.select_related('product', 'variant').all()
    formset = StockCountLineFormSet(queryset=lines)
    if request.method == 'POST' and session.status == 'In Progress':
        formset = StockCountLineFormSet(request.POST, queryset=lines)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Count quantities saved.')
            return redirect('stock_count_detail', uuid=uuid)
    return render(request, 'inventory/stock_count_detail.html', {
        'session': session, 'lines': lines, 'formset': formset,
    })


@login_required
def stock_count_commit_view(request, uuid):
    session = get_object_or_404(StockCountSession, uuid=uuid)
    if request.method == 'POST' and session.status == 'In Progress':
        for line in session.lines.all():
            if line.counted_qty is not None and line.counted_qty != line.expected_qty:
                delta = line.counted_qty - line.expected_qty
                movement = StockMovement.objects.create(
                    product=line.product, variant=line.variant,
                    warehouse=session.warehouse,
                    movement_type='COUNT_CORRECTION', quantity_delta=delta,
                    user=request.user, notes=f'Count session #{session.pk}',
                )
                stock_level, _ = StockLevel.objects.get_or_create(
                    product=line.product, variant=line.variant,
                    warehouse=session.warehouse,
                    defaults={'quantity_on_hand': 0}
                )
                stock_level.quantity_on_hand = line.counted_qty
                stock_level.save()
                line.movement = movement
                line.save()
        session.status = 'Committed'
        session.committed_at = timezone.now()
        session.save()
        log_action(request.user, 'Update', 'StockCountSession', session.pk, f'Committed count for {session.warehouse}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        variance_count = session.lines.exclude(counted_qty=F('expected_qty')).filter(counted_qty__isnull=False).count()
        total_lines = session.lines.count()
        notify_admins(
            title=f'Stock Count Committed: #{session.pk}',
            body=f'Stock count session #{session.pk} at "{session.warehouse.name}" committed by {request.user.username}. Total items: {total_lines}. Variances found: {variance_count}.',
            link=f'/inventory/counts/{session.uuid}/',
        )
        messages.success(request, f'Count session #{session.pk} committed. Variances adjusted.')
        return redirect('stock_count_detail', uuid=uuid)
    return redirect('stock_count_detail', uuid=uuid)


@login_required
def stock_movement_list_view(request):
    movements = StockMovement.objects.select_related(
        'product', 'variant', 'warehouse', 'user', 'reason_code'
    ).all()
    type_filter = request.GET.get('type', '')
    if type_filter:
        movements = movements.filter(movement_type=type_filter)
    paginator = Paginator(movements, 20)
    page = request.GET.get('page', 1)
    movements_page = paginator.get_page(page)
    return render(request, 'inventory/stock_movement_list.html', {
        'movements': movements_page, 'selected_type': type_filter,
    })


@login_required
def warehouse_list_view(request):
    warehouses = Warehouse.objects.all()
    paginator = Paginator(warehouses, 20)
    page = request.GET.get('page', 1)
    warehouses_page = paginator.get_page(page)
    return render(request, 'inventory/warehouse_list.html', {'warehouses': warehouses_page})


@login_required
def warehouse_create_view(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            warehouse = form.save()
            log_action(request.user, 'Create', 'Warehouse', warehouse.pk, f'Created warehouse: {warehouse.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Warehouse Created: {warehouse.name}',
                body=f'New warehouse "{warehouse.name}" (address: {warehouse.address or "Not specified"}) created by {request.user.username}. Status: {"Active" if warehouse.is_active else "Inactive"}.',
                link=f'/inventory/warehouses/',
            )
            messages.success(request, 'Warehouse created.')
            return redirect('warehouse_list')
    else:
        form = WarehouseForm()
    return render(request, 'inventory/warehouse_form.html', {'form': form, 'title': 'Create Warehouse'})


@login_required
def warehouse_edit_view(request, uuid):
    warehouse = get_object_or_404(Warehouse, uuid=uuid)
    if request.method == 'POST':
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            old_name = warehouse.name
            form.save()
            log_action(request.user, 'Update', 'Warehouse', warehouse.pk, f'Updated warehouse: {warehouse.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Warehouse Updated: {warehouse.name}',
                body=f'Warehouse "{warehouse.name}" updated by {request.user.username}. Name changed: "{old_name}" → "{warehouse.name}". Address: {warehouse.address or "Not specified"}. Active: {"Yes" if warehouse.is_active else "No"}.',
                link=f'/inventory/warehouses/',
            )
            messages.success(request, 'Warehouse updated.')
            return redirect('warehouse_list')
    else:
        form = WarehouseForm(instance=warehouse)
    return render(request, 'inventory/warehouse_form.html', {'form': form, 'warehouse': warehouse, 'title': f'Edit: {warehouse.name}'})


@login_required
def warehouse_delete_view(request, uuid):
    warehouse = get_object_or_404(Warehouse, uuid=uuid)
    if request.method == 'POST':
        warehouse.is_active = False
        warehouse.save()
        log_action(request.user, 'Update', 'Warehouse', warehouse.pk, f'Archived warehouse: {warehouse.name}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        product_count = warehouse.stock_levels.count()
        notify_admins(
            title=f'Warehouse Archived: {warehouse.name}',
            body=f'Warehouse "{warehouse.name}" (address: {warehouse.address or "Not specified"}) archived by {request.user.username}. Products affected: {product_count}.',
            link=f'/inventory/warehouses/',
        )
        messages.success(request, f'Warehouse "{warehouse.name}" has been archived.')
        return redirect('warehouse_list')
    return render(request, 'inventory/warehouse_confirm_delete.html', {'warehouse': warehouse})
