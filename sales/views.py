from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse
from django.conf import settings
from django.db import transaction as db_transaction
from .models import (SalesTransaction, SalesTransactionLine, Payment,
                     Return, ReturnLine, SalesChannel, Customer, CustomerAddress)
from .forms import (SalesTransactionForm, SalesTransactionLineForm,
                    PaymentForm, ReturnForm, ReturnLineForm, CustomerForm, SalesChannelForm)
from inventory.models import Warehouse, StockLevel, StockMovement
from catalog.models import Product, ProductVariant
from audit.utils import log_action
from . import khalti


@login_required
def transaction_list_view(request):
    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '')
    transactions = SalesTransaction.objects.select_related(
        'customer', 'channel', 'warehouse', 'cashier'
    ).all()
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    if query:
        transactions = transactions.filter(
            Q(invoice_number__icontains=query) |
            Q(customer__name__icontains=query)
        )
    paginator = Paginator(transactions, 20)
    page = request.GET.get('page', 1)
    transactions_page = paginator.get_page(page)
    return render(request, 'sales/transaction_list.html', {
        'transactions': transactions_page, 'selected_status': status_filter, 'query': query,
    })


@login_required
def pos_view(request):
    drafts = list(SalesTransaction.objects.filter(
        status='Draft', cashier=request.user
    ).order_by('-created_at'))
    if len(drafts) > 1:
        draft = drafts[0]
        SalesTransaction.objects.filter(pk__in=[d.pk for d in drafts[1:]]).delete()
    elif drafts:
        draft = drafts[0]
    else:
        draft = SalesTransaction.objects.create(
            status='Draft', cashier=request.user,
            channel=SalesChannel.objects.get_or_create(name='In-Store')[0],
            warehouse=Warehouse.objects.first(),
        )
    lines = draft.lines.select_related('product', 'variant').all()
    products = Product.objects.filter(is_active=True).order_by('name')
    draft.calculate_totals()
    return render(request, 'sales/pos.html', {
        'transaction': draft, 'lines': lines, 'products': products,
    })


@login_required
def cart_api_view(request):
    drafts = list(SalesTransaction.objects.filter(
        status='Draft', cashier=request.user
    ).order_by('-created_at'))
    if len(drafts) > 1:
        draft = drafts[0]
        SalesTransaction.objects.filter(pk__in=[d.pk for d in drafts[1:]]).delete()
    elif drafts:
        draft = drafts[0]
    else:
        return JsonResponse({'transaction_id': None, 'lines': [], 'subtotal': '0', 'tax': '0', 'total': '0', 'count': 0})
    draft.calculate_totals()
    lines = []
    for line in draft.lines.select_related('product', 'variant', 'product__category').all():
        product = line.product
        image = ''
        if product.image_url:
            image = product.image_url
        elif product.primary_image:
            try:
                image = product.primary_image.image.url
            except Exception:
                pass
        stock = product.total_stock
        lines.append({
            'id': line.pk,
            'product_name': product.name,
            'sku': product.sku,
            'category': product.category.name if product.category else '',
            'image': image,
            'stock': stock,
            'unit_price': str(line.unit_price),
            'quantity': line.quantity,
            'discount': str(line.discount),
            'subtotal': str(line.subtotal),
        })
    return JsonResponse({
        'transaction_id': draft.pk,
        'lines': lines,
        'subtotal': str(draft.subtotal),
        'tax': str(draft.tax_total),
        'total': str(draft.grand_total),
        'count': len(lines),
    })


@login_required
def transaction_create_view(request):
    channels = SalesChannel.objects.all()
    warehouses = Warehouse.objects.filter(is_active=True)
    customers = Customer.objects.filter(is_active=True)
    if request.method == 'POST':
        channel = get_object_or_404(SalesChannel, pk=request.POST.get('channel'))
        warehouse = get_object_or_404(Warehouse, pk=request.POST.get('warehouse'))
        customer_id = request.POST.get('customer')
        customer = get_object_or_404(Customer, pk=customer_id) if customer_id else None
        transaction = SalesTransaction.objects.create(
            channel=channel, warehouse=warehouse, customer=customer,
            cashier=request.user, status='Draft',
        )
        log_action(request.user, 'Create', 'SalesTransaction', transaction.pk, f'Created draft TXN {transaction.invoice_number}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'Sale Started: {transaction.invoice_number or "Draft"}',
            body=f'Transaction {transaction.invoice_number or "Draft"} created by {request.user.username}. Warehouse: {transaction.warehouse.name if transaction.warehouse else "N/A"}. Channel: {transaction.channel.name if transaction.channel else "N/A"}. Items in cart: {transaction.lines.count()}.',
            link=f'/sales/{transaction.uuid}/',
        )
        messages.success(request, f'Transaction created. Add items and complete.')
        return redirect('pos')
    return render(request, 'sales/transaction_create.html', {
        'channels': channels, 'warehouses': warehouses, 'customers': customers,
    })


@login_required
def cart_add_view(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        try:
            quantity = max(1, int(request.POST.get('quantity', 1)))
        except (ValueError, TypeError):
            quantity = 1
        product = get_object_or_404(Product, pk=product_id)
        drafts = list(SalesTransaction.objects.filter(
            status='Draft', cashier=request.user
        ).order_by('-created_at'))
        if len(drafts) > 1:
            draft = drafts[0]
            SalesTransaction.objects.filter(pk__in=[d.pk for d in drafts[1:]]).delete()
        elif drafts:
            draft = drafts[0]
        else:
            draft = SalesTransaction.objects.create(
                status='Draft', cashier=request.user,
                channel=SalesChannel.objects.get_or_create(name='In-Store')[0],
                warehouse=Warehouse.objects.first(),
            )
        variant_id = request.POST.get('variant_id')
        variant = get_object_or_404(ProductVariant, pk=variant_id) if variant_id else None
        existing = draft.lines.filter(product=product, variant=variant).first()
        if existing:
            existing.quantity += quantity
            existing.save()
        else:
            price = variant.effective_sale_price if variant else product.sale_price
            SalesTransactionLine.objects.create(
                transaction=draft, product=product, variant=variant,
                quantity=quantity, unit_price=price,
            )
        draft.calculate_totals()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'total': str(draft.grand_total), 'lines': draft.lines.count()})
    return redirect('pos')


@login_required
def cart_remove_view(request, item_id):
    line = get_object_or_404(SalesTransactionLine, pk=item_id, transaction__status='Draft', transaction__cashier=request.user)
    transaction = line.transaction
    line.delete()
    transaction.calculate_totals()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'total': str(transaction.grand_total), 'lines': transaction.lines.count()})
    return redirect('pos')


@login_required
def cart_update_view(request, item_id):
    line = get_object_or_404(SalesTransactionLine, pk=item_id, transaction__status='Draft', transaction__cashier=request.user)
    if request.method == 'POST':
        try:
            qty = max(1, int(request.POST.get('quantity', 1)))
        except (ValueError, TypeError):
            qty = 1
        try:
            discount = max(0, float(request.POST.get('discount', 0)))
        except (ValueError, TypeError):
            discount = 0
        if qty <= 0:
            line.delete()
        else:
            line.quantity = qty
            line.discount = discount
            line.save()
        line.transaction.calculate_totals()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'total': str(line.transaction.grand_total), 'lines': line.transaction.lines.count()})
    return redirect('pos')


@login_required
def transaction_detail_view(request, uuid):
    transaction = get_object_or_404(SalesTransaction.objects.select_related(
        'customer', 'channel', 'warehouse', 'cashier'
    ), uuid=uuid)
    lines = transaction.lines.select_related('product', 'variant').all()
    payments = transaction.payments.all()
    returns = transaction.returns.all()
    return render(request, 'sales/transaction_detail.html', {
        'transaction': transaction, 'lines': lines, 'payments': payments, 'returns': returns,
    })


def _finalize_sale(transaction, user):
    """
    Deduct stock and mark a Draft transaction Completed, generating its invoice
    number. Shared by the cash/card checkout path and the Khalti callback so
    stock is only ever deducted once, after payment is confirmed.
    Returns (invoice_num, error_message). error_message is set (and nothing
    is changed) if stock is insufficient.
    """
    with db_transaction.atomic():
        for line in transaction.lines.select_related('product').all():
            stock_level, _ = StockLevel.objects.get_or_create(
                product=line.product, variant=line.variant,
                warehouse=transaction.warehouse,
                defaults={'quantity_on_hand': 0}
            )
            if stock_level.quantity_on_hand < line.quantity:
                return None, f'Insufficient stock for {line.product.name}. Available: {stock_level.quantity_on_hand}'
            stock_level.quantity_on_hand -= line.quantity
            stock_level.save()
            StockMovement.objects.create(
                product=line.product, variant=line.variant,
                warehouse=transaction.warehouse,
                movement_type='SALE', quantity_delta=-line.quantity,
                reference_type='SalesTransactionLine', reference_id=line.pk,
                user=user, notes=f'Transaction {transaction.invoice_number or transaction.pk}',
            )
        invoice_num = f"INV-{timezone.now().strftime('%Y%m%d')}-{SalesTransaction.objects.exclude(invoice_number__isnull=True).count() + 1:04d}"
        transaction.invoice_number = invoice_num
        transaction.status = 'Completed'
        transaction.completed_at = timezone.now()
        transaction.calculate_totals()
        transaction.save()
    return invoice_num, None


@login_required
def transaction_complete_view(request, uuid):
    transaction = get_object_or_404(SalesTransaction, uuid=uuid, status='Draft')
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'Cash')
        try:
            amount = max(0, float(request.POST.get('amount', transaction.grand_total)))
        except (ValueError, TypeError):
            amount = float(transaction.grand_total)
        amount_tendered = request.POST.get('amount_tendered')
        try:
            at = max(0, float(amount_tendered)) if amount_tendered else amount
        except (ValueError, TypeError):
            at = amount
        change = at - amount if at > amount else 0
        invoice_num, error = _finalize_sale(transaction, request.user)
        if error:
            messages.error(request, error)
            return redirect('pos')
        Payment.objects.create(
            transaction=transaction, method=payment_method,
            amount=amount, status='Paid',
            amount_tendered=at,
            change_given=change,
        )
        log_action(request.user, 'Create', 'SalesTransaction', transaction.pk,
                   f'Completed transaction {invoice_num}')
        from notifications.utils import notify_role
        items_summary = ', '.join(f'{line.product.name} x{line.quantity}' for line in transaction.lines.select_related('product').all())
        notify_role('warehouse',
            title=f'Sale Completed: {invoice_num}',
            body=f'Transaction {invoice_num} completed by {request.user.username}. Items: {items_summary}. Total: Rs. {transaction.grand_total:,.2f}. Payment: {payment_method}. Amount tendered: Rs. {at:,.2f}. Change given: Rs. {change:,.2f}. Stock deducted at "{transaction.warehouse.name}".',
            link=f'/sales/{transaction.uuid}/',
        )
        messages.success(request, f'Transaction {invoice_num} completed successfully!')
        return redirect('transaction_detail', uuid=uuid)
    return redirect('pos')


@login_required
def khalti_initiate_view(request):
    """
    Start a Khalti payment for the cashier's current draft transaction.
    Does NOT deduct stock or complete the sale — that only happens once the
    callback confirms payment via the lookup API.
    """
    if request.method != 'POST':
        return redirect('pos')

    draft = SalesTransaction.objects.filter(status='Draft', cashier=request.user).order_by('-created_at').first()
    if not draft or draft.lines.count() == 0:
        return JsonResponse({'error': 'Cart is empty'}, status=400)

    draft.calculate_totals()
    amount_paisa = int(round(float(draft.grand_total) * 100))
    if amount_paisa < 1000:  # Khalti minimum is Rs 10
        return JsonResponse({'error': 'Amount must be at least Rs. 10 for Khalti.'}, status=400)

    customer_info = None
    if draft.customer:
        customer_info = {'name': draft.customer.name}
        if draft.customer.email:
            customer_info['email'] = draft.customer.email
        if draft.customer.phone:
            customer_info['phone'] = draft.customer.phone

    return_url = request.build_absolute_uri(reverse('khalti_callback'))
    website_url = getattr(settings, 'SITE_BASE_URL', request.build_absolute_uri('/'))

    try:
        result = khalti.initiate_payment(
            amount_paisa=amount_paisa,
            purchase_order_id=f'TXN-{draft.pk}-{int(timezone.now().timestamp())}',
            purchase_order_name=f'POS Sale #{draft.pk}',
            return_url=return_url,
            website_url=website_url,
            customer_info=customer_info,
        )
    except khalti.KhaltiError as exc:
        return JsonResponse({'error': str(exc), 'detail': exc.detail}, status=400)

    # Record a Pending payment now so the callback can find it via pidx.
    Payment.objects.filter(transaction=draft, method='Khalti', status='Pending').delete()
    Payment.objects.create(
        transaction=draft, method='Khalti', amount=draft.grand_total,
        status='Pending', khalti_pidx=result['pidx'],
    )
    return JsonResponse({'payment_url': result['payment_url'], 'pidx': result['pidx']})


@login_required
def khalti_callback_view(request):
    """
    Khalti redirects the user's browser here after they complete/cancel
    checkout. Per Khalti's docs, the query params are NOT trusted for the
    final decision — the pidx is looked up against the lookup API to confirm
    the real status before completing the sale.
    """
    pidx = request.GET.get('pidx')
    payment = get_object_or_404(Payment, khalti_pidx=pidx, method='Khalti')
    transaction = payment.transaction

    if transaction.status == 'Completed':
        # Already finalized (e.g. user refreshed the callback URL).
        return redirect('transaction_detail', uuid=transaction.uuid)

    try:
        result = khalti.lookup_payment(pidx)
    except khalti.KhaltiError as exc:
        messages.error(request, f'Could not verify Khalti payment: {exc}')
        return redirect('pos')

    if result.get('status') == 'Completed':
        invoice_num, error = _finalize_sale(transaction, request.user)
        if error:
            messages.error(request, error)
            return redirect('pos')
        payment.status = 'Paid'
        payment.amount_tendered = payment.amount
        payment.khalti_transaction_id = result.get('transaction_id')
        payment.save()
        log_action(request.user, 'Create', 'SalesTransaction', transaction.pk,
                   f'Completed transaction {invoice_num} via Khalti')
        from notifications.utils import notify_admins
        items_summary = ', '.join(f'{line.product.name} x{line.quantity}' for line in transaction.lines.select_related('product').all())
        notify_admins(
            title=f'Online Payment Confirmed: {invoice_num}',
            body=f'Transaction {invoice_num} paid via Khalti by {request.user.username}. Amount: Rs. {transaction.grand_total:,.2f}. Khalti transaction ID: {result.get("transaction_id", "N/A")}. Items: {items_summary}. Warehouse: {transaction.warehouse.name}.',
            link=f'/sales/{transaction.uuid}/',
        )
        messages.success(request, f'Transaction {invoice_num} paid via Khalti!')
        return redirect('transaction_detail', uuid=transaction.uuid)
    else:
        payment.delete()
        messages.error(request, f"Khalti payment {result.get('status', 'failed')}. Please try again.")
        return redirect('pos')


@login_required
def transaction_void_view(request, uuid):
    transaction = get_object_or_404(SalesTransaction, uuid=uuid)
    if request.method == 'POST' and transaction.status == 'Draft':
        transaction.status = 'Void'
        transaction.save()
        log_action(request.user, 'Update', 'SalesTransaction', transaction.pk, f'Voided TXN {transaction.invoice_number}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        items_summary = ', '.join(f'{line.product.name} x{line.quantity}' for line in transaction.lines.select_related('product').all())
        notify_admins(
            title=f'Transaction Voided: {transaction.invoice_number or "Draft"}',
            body=f'Transaction {transaction.invoice_number or "Draft"} voided by {request.user.username}. Amount: Rs. {transaction.grand_total:,.2f}. Items: {items_summary or "None"}. Warehouse: {transaction.warehouse.name if transaction.warehouse else "N/A"}.',
            link=f'/sales/{transaction.uuid}/',
        )
        messages.success(request, 'Transaction voided.')
    return redirect('transaction_list')


@login_required
def transaction_receipt_view(request, uuid):
    transaction = get_object_or_404(SalesTransaction.objects.select_related(
        'customer', 'channel', 'warehouse', 'cashier'
    ), uuid=uuid)
    lines = transaction.lines.select_related('product', 'variant').all()
    payments = transaction.payments.all()
    return render(request, 'sales/receipt.html', {
        'transaction': transaction, 'lines': lines, 'payments': payments,
    })


@login_required
def return_create_view(request, uuid):
    transaction = get_object_or_404(SalesTransaction, uuid=uuid, status='Completed')
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        return_request = Return.objects.create(
            original_transaction=transaction, requested_by=request.user,
            reason=reason, status='Requested',
        )
        total_refund = 0
        for line in transaction.lines.all():
            qty_key = f'return_qty_{line.pk}'
            try:
                qty = max(0, int(request.POST.get(qty_key, 0)))
            except (ValueError, TypeError):
                qty = 0
            qty = min(qty, line.quantity)
            if qty > 0:
                restock = f'restock_{line.pk}' in request.POST
                ReturnLine.objects.create(
                    return_request=return_request, transaction_line=line,
                    quantity_returned=qty, restock=restock,
                    condition='Sellable' if restock else 'Damaged',
                )
                total_refund += qty * float(line.unit_price)
        return_request.refund_amount = total_refund
        return_request.save()
        log_action(request.user, 'Create', 'Return', return_request.pk, f'Return requested for TXN {return_request.original_transaction.invoice_number}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        return_items = ', '.join(f'{rl.transaction_line.product.name} x{rl.quantity_returned}' for rl in return_request.lines.select_related('transaction_line__product').all())
        notify_admins(
            title=f'Return Requested: #{return_request.pk}',
            body=f'Return #{return_request.pk} requested for invoice {return_request.original_transaction.invoice_number} by {request.user.username}. Items: {return_items}. Refund amount: Rs. {total_refund:,.2f}. Reason: {reason or "Not specified"}.',
            link=f'/sales/returns/{return_request.uuid}/',
        )
        messages.success(request, f'Return #{return_request.pk} created. Awaiting processing.')
        return redirect('transaction_detail', uuid=uuid)
    return render(request, 'sales/return_create.html', {'transaction': transaction})


@login_required
def return_list_view(request):
    returns = Return.objects.select_related(
        'original_transaction', 'requested_by', 'processed_by'
    ).all()
    paginator = Paginator(returns, 20)
    page = request.GET.get('page', 1)
    returns_page = paginator.get_page(page)
    return render(request, 'sales/return_list.html', {'returns': returns_page})


@login_required
def return_detail_view(request, uuid):
    return_request = get_object_or_404(Return.objects.select_related(
        'original_transaction', 'requested_by', 'processed_by'
    ), uuid=uuid)
    lines = return_request.lines.select_related('transaction_line__product').all()
    return render(request, 'sales/return_detail.html', {
        'return_request': return_request, 'lines': lines,
    })


@login_required
def return_process_view(request, uuid):
    return_request = get_object_or_404(Return, uuid=uuid)
    if request.method == 'POST' and return_request.status in ('Requested',):
        action = request.POST.get('action')
        if action == 'approve':
            return_request.status = 'Approved'
            return_request.processed_by = request.user
            return_request.processed_at = timezone.now()
            refund_method = request.POST.get('refund_method', 'Cash')
            return_request.refund_method = refund_method
            for line in return_request.lines.all():
                if line.restock:
                    stock_level, _ = StockLevel.objects.get_or_create(
                        product=line.transaction_line.product,
                        variant=line.transaction_line.variant,
                        warehouse=return_request.original_transaction.warehouse,
                        defaults={'quantity_on_hand': 0}
                    )
                    stock_level.quantity_on_hand += line.quantity_returned
                    stock_level.save()
                    movement = StockMovement.objects.create(
                        product=line.transaction_line.product,
                        variant=line.transaction_line.variant,
                        warehouse=return_request.original_transaction.warehouse,
                        movement_type='RETURN', quantity_delta=line.quantity_returned,
                        user=request.user, notes=f'Return #{return_request.pk}',
                    )
                    line.movement = movement
                    line.save()
            messages.success(request, f'Return #{return_request.pk} approved and processed.')
        elif action == 'reject':
            return_request.status = 'Rejected'
            return_request.processed_by = request.user
            return_request.processed_at = timezone.now()
            messages.success(request, f'Return #{return_request.pk} rejected.')
        return_request.save()
        log_action(request.user, 'Update', 'Return', return_request.pk, f'Return {return_request.status} for TXN {return_request.original_transaction.invoice_number}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        if action == 'approve':
            restock_items = ', '.join(f'{rl.transaction_line.product.name} x{rl.quantity_returned}' for rl in return_request.lines.filter(restock=True).select_related('transaction_line__product'))
            notify_admins(
                title=f'Return Approved: #{return_request.pk}',
                body=f'Return #{return_request.pk} for invoice {return_request.original_transaction.invoice_number} approved by {request.user.username}. Refund: Rs. {return_request.refund_amount:,.2f}. Refund method: {refund_method}. Items restocked: {restock_items or "None"}.',
                link=f'/sales/returns/{return_request.uuid}/',
            )
        elif action == 'reject':
            notify_admins(
                title=f'Return Rejected: #{return_request.pk}',
                body=f'Return #{return_request.pk} for invoice {return_request.original_transaction.invoice_number} rejected by {request.user.username}. Refund amount was: Rs. {return_request.refund_amount:,.2f}.',
                link=f'/sales/returns/{return_request.uuid}/',
            )
    return redirect('return_detail', uuid=uuid)


@login_required
def channel_list_view(request):
    channels = SalesChannel.objects.all()
    paginator = Paginator(channels, 20)
    page = request.GET.get('page', 1)
    channels_page = paginator.get_page(page)
    return render(request, 'sales/channel_list.html', {'channels': channels_page})


@login_required
def channel_create_view(request):
    if request.method == 'POST':
        form = SalesChannelForm(request.POST)
        if form.is_valid():
            channel = form.save()
            log_action(request.user, 'Create', 'SalesChannel', channel.pk, f'Created channel: {channel.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Sales Channel Created: {channel.name}',
                body=f'Sales channel "{channel.name}" (UUID: {channel.uuid}) created by {request.user.username}.',
                link=f'/sales/channels/',
            )
            messages.success(request, f'Channel "{channel.name}" created.')
            return redirect('channel_list')
    else:
        form = SalesChannelForm()
    return render(request, 'sales/channel_form.html', {'form': form, 'title': 'Create Channel'})


@login_required
def channel_edit_view(request, uuid):
    channel = get_object_or_404(SalesChannel, uuid=uuid)
    if request.method == 'POST':
        form = SalesChannelForm(request.POST, instance=channel)
        if form.is_valid():
            form.save()
            log_action(request.user, 'Update', 'SalesChannel', channel.pk, f'Updated channel: {channel.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Sales Channel Updated: {channel.name}',
                body=f'Sales channel "{channel.name}" (UUID: {channel.uuid}) updated by {request.user.username}.',
                link=f'/sales/channels/',
            )
            messages.success(request, f'Channel "{channel.name}" updated.')
            return redirect('channel_list')
    else:
        form = SalesChannelForm(instance=channel)
    return render(request, 'sales/channel_form.html', {'form': form, 'channel': channel, 'title': f'Edit: {channel.name}'})


@login_required
def channel_delete_view(request, uuid):
    channel = get_object_or_404(SalesChannel, uuid=uuid)
    if request.method == 'POST':
        name = channel.name
        channel.delete()
        log_action(request.user, 'Delete', 'SalesChannel', None, f'Deleted channel: {name}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'Sales Channel Deleted: {name}',
            body=f'Sales channel "{name}" deleted by {request.user.username}. Transactions using this channel may need review.',
            link='/sales/channels/',
        )
        messages.success(request, f'Channel "{name}" deleted.')
        return redirect('channel_list')
    return render(request, 'sales/channel_confirm_delete.html', {'channel': channel})


@login_required
def customer_list_view(request):
    query = request.GET.get('q', '')
    customers = Customer.objects.all()
    if query:
        customers = customers.filter(Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query))
    paginator = Paginator(customers, 20)
    page = request.GET.get('page', 1)
    customers_page = paginator.get_page(page)
    return render(request, 'sales/customer_list.html', {'customers': customers_page, 'query': query})


@login_required
def customer_create_view(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            log_action(request.user, 'Create', 'Customer', customer.pk, f'Created customer: {customer.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Customer Created: {customer.name}',
                body=f'Customer "{customer.name}" (email: {customer.email or "N/A"}, phone: {customer.phone or "N/A"}) created by {request.user.username}.',
                link=f'/sales/customers/{customer.uuid}/',
            )
            messages.success(request, f'Customer "{customer.name}" created.')
            return redirect('customer_detail', uuid=customer.uuid)
    else:
        form = CustomerForm()
    return render(request, 'sales/customer_form.html', {'form': form, 'title': 'Create Customer', 'editing': False})


@login_required
def customer_detail_view(request, uuid):
    customer = get_object_or_404(Customer, uuid=uuid)
    transactions = customer.transactions.select_related('channel', 'cashier').all()[:20]
    return render(request, 'sales/customer_detail.html', {
        'customer': customer, 'transactions': transactions,
    })


@login_required
def customer_edit_view(request, uuid):
    customer = get_object_or_404(Customer, uuid=uuid)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            log_action(request.user, 'Update', 'Customer', customer.pk, f'Updated customer: {customer.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Customer Updated: {customer.name}',
                body=f'Customer "{customer.name}" (email: {customer.email or "N/A"}, phone: {customer.phone or "N/A"}) updated by {request.user.username}. Orders: {customer.transactions.exclude(status="Draft").count()}.',
                link=f'/sales/customers/{customer.uuid}/',
            )
            messages.success(request, f'Customer "{customer.name}" updated.')
            return redirect('customer_detail', uuid=customer.uuid)
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'sales/customer_form.html', {'form': form, 'customer': customer, 'title': f'Edit: {customer.name}', 'editing': True})


@login_required
def customer_delete_view(request, uuid):
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard')
    customer = get_object_or_404(Customer, uuid=uuid)
    if request.method == 'POST':
        name = customer.name
        if customer.user:
            customer.user = None
            customer.save()
        log_action(request.user, 'Delete', 'Customer', customer.pk, f'Deleted customer: {name}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        order_count = customer.transactions.exclude(status='Draft').count()
        notify_admins(
            title=f'Customer Deleted: {name}',
            body=f'Customer "{name}" (email: {customer.email or "N/A"}, phone: {customer.phone or "N/A"}) deleted by {request.user.username}. Order count: {order_count}.',
            link='/sales/customers/',
        )
        customer.delete()
        messages.success(request, f'Customer "{name}" has been deleted.')
        return redirect('customer_list')
    return render(request, 'sales/customer_confirm_delete.html', {'customer': customer})
