from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Supplier
from .forms import SupplierForm
from audit.utils import log_action


@login_required
def supplier_list_view(request):
    query = request.GET.get('q', '')
    suppliers = Supplier.objects.all()
    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query) | Q(contact_name__icontains=query) | Q(email__icontains=query)
        )
    paginator = Paginator(suppliers, 20)
    page = request.GET.get('page', 1)
    suppliers_page = paginator.get_page(page)
    return render(request, 'suppliers/supplier_list.html', {'suppliers': suppliers_page, 'query': query})


@login_required
def supplier_create_view(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            log_action(request.user, 'Create', 'Supplier', supplier.pk, f'Created supplier: {supplier.name}')
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Supplier Created: {supplier.name}',
                body=f'New supplier "{supplier.name}" (email: {supplier.email or "N/A"}, phone: {supplier.phone or "N/A"}, contact: {supplier.contact_name or "N/A"}, lead time: {supplier.lead_time_days} days) added by {request.user.username}.',
                link=f'/suppliers/{supplier.uuid}/',
            )
            messages.success(request, f'Supplier "{supplier.name}" created.')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'suppliers/supplier_form.html', {'form': form, 'title': 'Create Supplier', 'editing': False})


@login_required
def supplier_detail_view(request, uuid):
    supplier = get_object_or_404(Supplier, uuid=uuid)
    products = supplier.supplier_products.select_related('product').all()
    purchase_orders = supplier.purchase_orders.all()[:10]
    return render(request, 'suppliers/supplier_detail.html', {
        'supplier': supplier, 'products': products, 'purchase_orders': purchase_orders,
    })


@login_required
def supplier_edit_view(request, uuid):
    supplier = get_object_or_404(Supplier, uuid=uuid)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            log_action(request.user, 'Update', 'Supplier', supplier.pk, f'Updated supplier: {supplier.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Supplier Updated: {supplier.name}',
                body=f'Supplier "{supplier.name}" (email: {supplier.email or "N/A"}, phone: {supplier.phone or "N/A"}, contact: {supplier.contact_name or "N/A"}, lead time: {supplier.lead_time_days} days) updated by {request.user.username}. Products linked: {supplier.supplier_products.count()}. Active POs: {supplier.purchase_orders.exclude(status__in=["Cancelled", "Closed"]).count()}.',
                link=f'/suppliers/{supplier.uuid}/',
            )
            messages.success(request, f'Supplier "{supplier.name}" updated.')
            return redirect('supplier_detail', uuid=supplier.uuid)
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'suppliers/supplier_form.html', {'form': form, 'title': f'Edit: {supplier.name}', 'supplier': supplier, 'editing': True})


@login_required
def supplier_delete_view(request, uuid):
    supplier = get_object_or_404(Supplier, uuid=uuid)
    if request.method == 'POST':
        supplier.is_active = False
        supplier.save()
        log_action(request.user, 'Update', 'Supplier', supplier.pk, f'Deactivated supplier: {supplier.name}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        product_count = supplier.supplier_products.count()
        active_pos = supplier.purchase_orders.exclude(status__in=['Cancelled', 'Closed']).count()
        notify_admins(
            title=f'Supplier Deactivated: {supplier.name}',
            body=f'Supplier "{supplier.name}" (email: {supplier.email or "N/A"}, phone: {supplier.phone or "N/A"}) deactivated by {request.user.username}. Products linked: {product_count}. Active POs: {active_pos}.',
            link=f'/suppliers/{supplier.uuid}/',
        )
        messages.success(request, f'Supplier "{supplier.name}" deactivated.')
        return redirect('supplier_list')
    return render(request, 'suppliers/supplier_confirm_delete.html', {'supplier': supplier})
