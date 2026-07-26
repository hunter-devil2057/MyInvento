from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from .models import PurchaseOrder, PurchaseOrderLine, ReorderRule
from .forms import PurchaseOrderForm, PurchaseOrderLineFormSet, ReorderRuleForm
from inventory.models import Warehouse, StockLevel, StockMovement
from suppliers.models import Supplier
from catalog.models import Product
from audit.utils import log_action
import datetime


@login_required
def po_list_view(request):
    status_filter = request.GET.get('status', '')
    pos = PurchaseOrder.objects.select_related('supplier', 'destination_warehouse', 'created_by').all()
    if status_filter:
        pos = pos.filter(status=status_filter)
    paginator = Paginator(pos, 20)
    page = request.GET.get('page', 1)
    pos_page = paginator.get_page(page)
    return render(request, 'purchasing/po_list.html', {'pos': pos_page, 'selected_status': status_filter})


@login_required
def po_create_view(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            po = form.save(commit=False)
            po.created_by = request.user
            po.po_number = f"PO-{timezone.now().strftime('%Y%m%d')}-{PurchaseOrder.objects.count() + 1:04d}"
            po.save()
            formset = PurchaseOrderLineFormSet(request.POST, instance=po)
            if formset.is_valid():
                formset.save()
                log_action(request.user, 'Create', 'PurchaseOrder', po.pk, f'Created PO {po.po_number}', ip_address=request.META.get('REMOTE_ADDR'))
                from notifications.utils import notify_admins
                notify_admins(
                    title=f'PO Created: {po.po_number}',
                    body=f'Purchase order {po.po_number} created for supplier "{po.supplier.name}" (email: {po.supplier.email or "N/A"}, phone: {po.supplier.phone or "N/A"}) to warehouse "{po.destination_warehouse.name}" by {request.user.username}. Line items: {po.lines.count()}. Expected date: {po.expected_date or "Not set"}. Total: Rs. {po.total_cost:,.2f}',
                    link=f'/purchasing/{po.uuid}/',
                )
                messages.success(request, f'PO {po.po_number} created.')
                return redirect('po_detail', uuid=po.uuid)
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderLineFormSet()
    return render(request, 'purchasing/po_form.html', {'form': form, 'formset': formset})


@login_required
def po_detail_view(request, uuid):
    po = get_object_or_404(PurchaseOrder.objects.select_related(
        'supplier', 'destination_warehouse', 'created_by'
    ), uuid=uuid)
    lines = po.lines.select_related('product', 'variant').all()
    return render(request, 'purchasing/po_detail.html', {'po': po, 'lines': lines})


@login_required
def po_edit_view(request, uuid):
    po = get_object_or_404(PurchaseOrder, uuid=uuid)
    if po.status not in ('Draft', 'Sent'):
        messages.error(request, 'PO can only be edited while in Draft or Sent status.')
        return redirect('po_detail', uuid=uuid)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=po)
        if form.is_valid():
            form.save()
            formset = PurchaseOrderLineFormSet(request.POST, instance=po)
            if formset.is_valid():
                formset.save()
                log_action(request.user, 'Update', 'PurchaseOrder', po.pk, f'Updated PO {po.po_number}', ip_address=request.META.get('REMOTE_ADDR'))
                from notifications.utils import notify_admins
                notify_admins(
                    title=f'PO Updated: {po.po_number}',
                    body=f'Purchase order {po.po_number} (supplier: {po.supplier.name}, warehouse: {po.destination_warehouse.name}) updated by {request.user.username}. Status: {po.get_status_display()}. Line items: {po.lines.count()}. Total: Rs. {po.total_cost:,.2f}',
                    link=f'/purchasing/{po.uuid}/',
                )
                messages.success(request, f'PO {po.po_number} updated.')
                return redirect('po_detail', uuid=uuid)
    else:
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderLineFormSet(instance=po)
    return render(request, 'purchasing/po_form.html', {'form': form, 'formset': formset, 'po': po})


@login_required
def po_send_view(request, uuid):
    po = get_object_or_404(PurchaseOrder, uuid=uuid)
    if request.method == 'POST' and po.status == 'Draft':
        po.status = 'Sent'
        po.save()
        log_action(request.user, 'Update', 'PurchaseOrder', po.pk, f'Sent PO {po.po_number}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'PO Sent: {po.po_number}',
            body=f'Purchase order {po.po_number} sent to supplier "{po.supplier.name}" (contact: {po.supplier.contact_name or "N/A"}, email: {po.supplier.email or "N/A"}, phone: {po.supplier.phone or "N/A"}) by {request.user.username}. Expected date: {po.expected_date or "Not set"}. Line items: {po.lines.count()}. Total: Rs. {po.total_cost:,.2f}',
            link=f'/purchasing/{po.uuid}/',
        )
        messages.success(request, f'PO {po.po_number} marked as Sent.')
    return redirect('po_detail', uuid=uuid)


@login_required
def po_receive_view(request, uuid):
    po = get_object_or_404(PurchaseOrder, uuid=uuid)
    if request.method == 'POST':
        for line in po.lines.all():
            qty_key = f'received_{line.pk}'
            cost_key = f'cost_{line.pk}'
            qty = request.POST.get(qty_key)
            cost = request.POST.get(cost_key)
            try:
                qty_int = int(qty) if qty else 0
            except (ValueError, TypeError):
                qty_int = 0
            if qty_int > 0:
                qty_received = min(qty_int, line.remaining_quantity)
                try:
                    received_cost = max(0, float(cost)) if cost else float(line.unit_cost)
                except (ValueError, TypeError):
                    received_cost = float(line.unit_cost)
                line.quantity_received += qty_received
                line.received_unit_cost = received_cost
                line.save()
                movement = StockMovement.objects.create(
                    product=line.product, variant=line.variant,
                    warehouse=po.destination_warehouse,
                    movement_type='PURCHASE', quantity_delta=qty_received,
                    reference_type='PurchaseOrderLine', reference_id=line.pk,
                    user=request.user, notes=f'PO {po.po_number}',
                )
                stock_level, _ = StockLevel.objects.get_or_create(
                    product=line.product, variant=line.variant,
                    warehouse=po.destination_warehouse,
                    defaults={'quantity_on_hand': 0}
                )
                stock_level.quantity_on_hand += qty_received
                stock_level.save()
        all_received = all(l.is_fully_received for l in po.lines.all())
        any_received = any(l.quantity_received > 0 for l in po.lines.all())
        if all_received:
            po.status = 'Received'
        elif any_received:
            po.status = 'Partially Received'
        po.save()
        log_action(request.user, 'Update', 'PurchaseOrder', po.pk, f'Received stock for PO {po.po_number}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        status_msg = 'fully received' if all_received else 'partially received'
        received_items = ', '.join(f'{l.product.name} x{l.quantity_received}/{l.quantity_ordered}' for l in po.lines.select_related('product').all() if l.quantity_received > 0)
        notify_admins(
            title=f'PO {po.po_number} {status_msg.title()}',
            body=f'PO {po.po_number} from supplier "{po.supplier.name}" {status_msg} by {request.user.username}. Items received: {received_items or "None"}. Stock updated at "{po.destination_warehouse.name}". Status: {po.get_status_display()}',
            link=f'/purchasing/{po.uuid}/',
        )
        messages.success(request, f'PO {po.po_number} receiving updated.')
        return redirect('po_detail', uuid=uuid)
    return redirect('po_detail', uuid=uuid)


@login_required
def po_cancel_view(request, uuid):
    po = get_object_or_404(PurchaseOrder, uuid=uuid)
    if request.method == 'POST' and po.status == 'Draft':
        po.status = 'Cancelled'
        po.save()
        log_action(request.user, 'Update', 'PurchaseOrder', po.pk, f'Cancelled PO {po.po_number}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'PO Cancelled: {po.po_number}',
            body=f'Purchase order {po.po_number} to {po.supplier.name} was cancelled by {request.user.username}.',
            link=f'/purchasing/{po.uuid}/',
        )
        messages.success(request, f'PO {po.po_number} cancelled.')
    return redirect('po_detail', uuid=uuid)


@login_required
def reorder_rule_list_view(request):
    rules = ReorderRule.objects.select_related(
        'product', 'variant', 'warehouse', 'default_supplier'
    ).all()
    paginator = Paginator(rules, 20)
    page = request.GET.get('page', 1)
    rules_page = paginator.get_page(page)
    return render(request, 'purchasing/reorder_rule_list.html', {'rules': rules_page})


@login_required
def reorder_rule_create_view(request):
    if request.method == 'POST':
        form = ReorderRuleForm(request.POST)
        if form.is_valid():
            rule = form.save()
            log_action(request.user, 'Create', 'ReorderRule', rule.pk, f'Created reorder rule for {rule.product.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Reorder Rule Created: {rule.product.name}',
                body=f'Reorder rule for "{rule.product.name}" (SKU: {rule.product.sku}) created by {request.user.username}. Min qty: {rule.min_quantity}, Max qty: {rule.max_quantity}. Supplier: {rule.default_supplier.name}. Warehouse: {rule.warehouse.name if rule.warehouse else "Any"}.',
                link=f'/purchasing/reorder-rules/',
            )
            messages.success(request, 'Reorder rule created.')
            return redirect('reorder_rule_list')
    else:
        form = ReorderRuleForm()
    return render(request, 'purchasing/reorder_rule_form.html', {'form': form, 'title': 'Create Reorder Rule'})


@login_required
def reorder_rule_edit_view(request, uuid):
    rule = get_object_or_404(ReorderRule, uuid=uuid)
    if request.method == 'POST':
        form = ReorderRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            log_action(request.user, 'Update', 'ReorderRule', rule.pk, f'Updated reorder rule for {rule.product.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Reorder Rule Updated: {rule.product.name}',
                body=f'Reorder rule for "{rule.product.name}" (SKU: {rule.product.sku}) updated by {request.user.username}. Min qty: {rule.min_quantity}, Max qty: {rule.max_quantity}. Supplier: {rule.default_supplier.name}. Warehouse: {rule.warehouse.name if rule.warehouse else "Any"}.',
                link=f'/purchasing/reorder-rules/',
            )
            messages.success(request, 'Reorder rule updated.')
            return redirect('reorder_rule_list')
    else:
        form = ReorderRuleForm(instance=rule)
    return render(request, 'purchasing/reorder_rule_form.html', {'form': form, 'title': 'Edit Reorder Rule'})


@login_required
def reorder_rule_delete_view(request, uuid):
    rule = get_object_or_404(ReorderRule, uuid=uuid)
    if request.method == 'POST':
        product_name = rule.product.name
        product_sku = rule.product.sku
        supplier_name = rule.default_supplier.name
        min_qty = rule.min_quantity
        max_qty = rule.max_quantity
        rule.delete()
        log_action(request.user, 'Delete', 'ReorderRule', None, 'Deleted reorder rule', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'Reorder Rule Deleted: {product_name}',
            body=f'Reorder rule for "{product_name}" (SKU: {product_sku}, min: {min_qty}, max: {max_qty}, supplier: {supplier_name}) deleted by {request.user.username}.',
            link='/purchasing/reorder-rules/',
        )
        messages.success(request, 'Reorder rule deleted.')
        return redirect('reorder_rule_list')
    return render(request, 'purchasing/reorder_rule_confirm_delete.html', {'rule': rule})


@login_required
def po_delete_view(request, uuid):
    po = get_object_or_404(PurchaseOrder, uuid=uuid)
    if po.status != 'Draft':
        messages.error(request, 'Only draft purchase orders can be deleted.')
        return redirect('po_detail', uuid=po.uuid)
    if request.method == 'POST':
        po_num = po.po_number
        supplier_name = po.supplier.name
        line_count = po.lines.count()
        po.delete()
        log_action(request.user, 'Delete', 'PurchaseOrder', None, f'Deleted PO: {po_num}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'PO Deleted: {po_num}',
            body=f'Purchase order "{po_num}" (supplier: {supplier_name}, {line_count} line items) deleted by {request.user.username}.',
            link='/purchasing/',
        )
        messages.success(request, f'Purchase order "{po_num}" deleted.')
        return redirect('po_list')
    return render(request, 'purchasing/po_confirm_delete.html', {'po': po})
