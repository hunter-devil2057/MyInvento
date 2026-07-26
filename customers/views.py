from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Subquery, IntegerField
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from .models import Cart, CartItem, Complaint, ComplaintReply
from catalog.models import Product, ProductVariant, Category
from sales.models import (SalesTransaction, SalesTransactionLine, Payment,
                          SalesChannel, Customer, Return, ReturnLine)
from inventory.models import StockLevel, Warehouse, StockMovement
from audit.utils import log_action
from sales import khalti


def _products_with_stock():
    """Return a queryset of products that have total stock > 0 across all warehouses."""
    return Product.objects.filter(
        is_active=True, is_published=True
    ).annotate(
        available_stock=Sum('stock_levels__quantity_on_hand')
    ).filter(available_stock__gt=0)


def portal_home_view(request):
    products = _products_with_stock().select_related('category')[:8]
    categories = Category.objects.all()
    return render(request, 'customers/portal_home.html', {'products': products, 'categories': categories})


def portal_register_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone = request.POST.get('phone', '')
        from django.contrib.auth.models import User
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return redirect('portal_register')
        user = User.objects.create_user(
            username=email, email=email, password=password,
            first_name=name.split()[0] if name else '',
            last_name=' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''
        )
        customer = Customer.objects.create(user=user, name=name, email=email, phone=phone)
        from accounts.models import UserProfile
        UserProfile.objects.create(user=user, role='customer')
        log_action(user, 'Create', 'Customer', customer.pk, f'Portal registration: {customer.name}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'New Customer Registration: {customer.name}',
            body=f'New customer "{customer.name}" registered via portal. Email: {customer.email or "N/A"}, phone: {customer.phone or "N/A"}. User account: {user.username}.',
            link=f'/sales/customers/{customer.uuid}/',
        )
        login(request, user)
        log_action(user, 'Login', 'User', user.pk, f'{user.username} registered and logged in via portal', ip_address=request.META.get('REMOTE_ADDR'))
        messages.success(request, 'Account created successfully!')
        return redirect('portal_catalog')
    return render(request, 'customers/portal_register.html')


def portal_login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            log_action(user, 'Login', 'User', user.pk, f'{user.username} logged in via portal', ip_address=request.META.get('REMOTE_ADDR'))
            return redirect('portal_catalog')
        messages.error(request, 'Invalid credentials.')
    return render(request, 'customers/portal_login.html')


def portal_logout_view(request):
    if request.user.is_authenticated:
        log_action(request.user, 'Logout', 'User', request.user.pk, f'{request.user.username} logged out from portal', ip_address=request.META.get('REMOTE_ADDR'))
    logout(request)
    return redirect('portal_home')


def portal_catalog_view(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    products = _products_with_stock().select_related('category').prefetch_related('images')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    if category_id:
        products = products.filter(category_id=category_id)
    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)
    categories = Category.objects.all()

    cart_product_ids = set()
    cart_items_map = {}
    cart = _get_cart(request)
    for ci in cart.items.select_related('product').all():
        cart_product_ids.add(ci.product_id)
        cart_items_map[ci.product_id] = ci.pk

    for p in products_page:
        p.in_cart = p.pk in cart_product_ids
        p.cart_item_id = cart_items_map.get(p.pk)

    return render(request, 'customers/portal_catalog.html', {
        'products': products_page, 'categories': categories,
        'query': query, 'selected_category': category_id,
        'cart_product_ids': cart_product_ids,
    })


def portal_product_detail_view(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True, is_published=True)
    total_stock = StockLevel.objects.filter(product=product).aggregate(
        total=Sum('quantity_on_hand')
    )['total'] or 0
    if total_stock <= 0:
        messages.warning(request, f'{product.name} is currently out of stock.')
        return redirect('portal_catalog')
    images = product.images.all()
    variants = product.variants.filter(is_active=True)
    return render(request, 'customers/portal_product_detail.html', {
        'product': product, 'images': images, 'variants': variants,
    })


def _get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        session_cart = Cart.objects.filter(session_key=request.session.session_key).exclude(user=request.user).first()
        if session_cart:
            for item in session_cart.items.all():
                existing = CartItem.objects.filter(cart=cart, product=item.product, variant=item.variant).first()
                if existing:
                    existing.quantity += item.quantity
                    existing.save()
                    item.delete()
                else:
                    item.cart = cart
                    item.save()
            session_cart.delete()
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart


def portal_cart_add_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    total_stock = StockLevel.objects.filter(product=product).aggregate(
        total=Sum('quantity_on_hand')
    )['total'] or 0
    if total_stock <= 0:
        messages.error(request, f'{product.name} is out of stock and cannot be added to cart.')
        return redirect('portal_catalog')
    cart = _get_cart(request)
    variant_id = request.POST.get('variant_id')
    variant = get_object_or_404(ProductVariant, pk=variant_id) if variant_id else None
    try:
        quantity = max(1, int(request.POST.get('quantity', 1)))
    except (ValueError, TypeError):
        quantity = 1
    if quantity > total_stock:
        messages.warning(request, f'Only {total_stock} units available. Adding {total_stock} instead.')
        quantity = total_stock
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, variant=variant,
        defaults={'quantity': quantity}
    )
    if not created:
        new_qty = min(item.quantity + quantity, total_stock)
        item.quantity = new_qty
        item.save()
    messages.success(request, f'{product.name} added to cart.')
    return redirect('portal_cart')


def portal_cart_remove_view(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id)
    item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('portal_cart')


def portal_cart_update_view(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id)
    try:
        quantity = max(1, int(request.POST.get('quantity', 1)))
    except (ValueError, TypeError):
        quantity = 1
    total_stock = StockLevel.objects.filter(product=item.product).aggregate(
        total=Sum('quantity_on_hand')
    )['total'] or 0
    if total_stock <= 0:
        item.delete()
        messages.warning(request, f'{item.product.name} is now out of stock. Item removed from cart.')
        return redirect('portal_cart')
    quantity = min(quantity, total_stock)
    if quantity < 1:
        item.delete()
        messages.success(request, 'Item removed from cart.')
    else:
        item.quantity = quantity
        item.save()
        messages.success(request, f'{item.product.name} quantity updated to {quantity}.')
    return redirect('portal_cart')


def portal_cart_view(request):
    cart = _get_cart(request)
    items = cart.items.select_related('product', 'variant').all()
    out_of_stock_items = []
    for item in items:
        total = StockLevel.objects.filter(product=item.product).aggregate(
            total=Sum('quantity_on_hand')
        )['total'] or 0
        if total <= 0:
            out_of_stock_items.append(item)
        elif item.quantity > total:
            item.quantity = total
            item.save()
    if out_of_stock_items:
        names = ', '.join(i.product.name for i in out_of_stock_items)
        for i in out_of_stock_items:
            i.delete()
        messages.warning(request, f'Removed out-of-stock items: {names}')
        return redirect('portal_cart')
    return render(request, 'customers/portal_cart.html', {'cart': cart, 'items': items})


def _finalize_portal_sale(transaction, warehouse, user):
    """
    Deduct stock and mark a Draft portal order Completed, generating its
    WEB- invoice number. Shared by the immediate (Cash/Card) checkout path
    and the Khalti callback so stock is only ever deducted once, after
    payment is confirmed.
    Returns (invoice_num, error_message). error_message is set (and nothing
    is changed) if stock is insufficient.
    """
    from django.db import transaction as db_transaction
    with db_transaction.atomic():
        for line in transaction.lines.select_related('product').all():
            stock_level, _ = StockLevel.objects.get_or_create(
                product=line.product, variant=line.variant,
                warehouse=warehouse, defaults={'quantity_on_hand': 0}
            )
            if stock_level.quantity_on_hand < line.quantity:
                return None, f'Insufficient stock for {line.product.name}. Available: {stock_level.quantity_on_hand}'
            stock_level.quantity_on_hand -= line.quantity
            stock_level.save()
            StockMovement.objects.create(
                product=line.product, variant=line.variant,
                warehouse=warehouse, movement_type='SALE', quantity_delta=-line.quantity,
                reference_type='SalesTransactionLine', reference_id=line.pk,
                user=user, notes='Portal order',
            )
        invoice_num = f"WEB-{timezone.now().strftime('%Y%m%d')}-{SalesTransaction.objects.exclude(invoice_number__isnull=True).count() + 1:04d}"
        transaction.invoice_number = invoice_num
        transaction.status = 'Completed'
        transaction.completed_at = timezone.now()
        transaction.save()
    return invoice_num, None


@login_required
def portal_checkout_view(request):
    cart = _get_cart(request)
    items = cart.items.select_related('product', 'variant').all()
    if not items:
        messages.error(request, 'Your cart is empty.')
        return redirect('portal_catalog')
    oos = []
    for item in items:
        avail = StockLevel.objects.filter(product=item.product).aggregate(
            total=Sum('quantity_on_hand'))['total'] or 0
        if avail <= 0:
            oos.append(item)
        elif item.quantity > avail:
            item.quantity = avail
            item.save()
    if oos:
        for i in oos:
            i.delete()
        names = ', '.join(i.product.name for i in oos)
        messages.warning(request, f'Removed out-of-stock items: {names}. Please review your cart.')
        return redirect('portal_cart')
    customer, _ = Customer.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.get_full_name() or request.user.username, 'email': request.user.email}
    )
    if request.method == 'POST':
        warehouse = Warehouse.objects.first()
        if not warehouse:
            messages.error(request, 'No warehouse available. Please contact support.')
            return redirect('portal_cart')
        channel = SalesChannel.objects.get_or_create(name='Online/Self-Service')[0]
        payment_method = request.POST.get('payment_method', 'Cash')
        transaction = SalesTransaction.objects.create(
            customer=customer, channel=channel, warehouse=warehouse, status='Draft',
        )
        for item in items:
            SalesTransactionLine.objects.create(
                transaction=transaction, product=item.product,
                variant=item.variant, quantity=item.quantity, unit_price=item.unit_price,
            )
        transaction.calculate_totals()

        if payment_method == 'Khalti':
            amount_paisa = int(round(float(transaction.grand_total) * 100))
            if amount_paisa < 1000:
                messages.error(request, 'Order total must be at least Rs. 10 to pay with Khalti.')
                transaction.delete()
                return redirect('portal_cart')
            customer_info = {'name': customer.name}
            if customer.email:
                customer_info['email'] = customer.email
            if customer.phone:
                customer_info['phone'] = customer.phone
            return_url = request.build_absolute_uri(reverse('portal_khalti_callback'))
            website_url = getattr(settings, 'SITE_BASE_URL', request.build_absolute_uri('/'))
            try:
                result = khalti.initiate_payment(
                    amount_paisa=amount_paisa,
                    purchase_order_id=f'WEB-{transaction.pk}-{int(timezone.now().timestamp())}',
                    purchase_order_name=f'Online Order #{transaction.pk}',
                    return_url=return_url, website_url=website_url,
                    customer_info=customer_info,
                )
            except khalti.KhaltiError as exc:
                messages.error(request, f'Could not start Khalti payment: {exc}')
                transaction.delete()
                return redirect('portal_checkout')
            Payment.objects.create(
                transaction=transaction, method='Khalti', amount=transaction.grand_total,
                status='Pending', khalti_pidx=result['pidx'],
            )
            # Cart items stay put until the callback confirms payment, so
            # nothing is lost if the customer cancels on Khalti's page.
            return redirect(result['payment_url'])

        # Cash / Card — complete immediately, as before.
        invoice_num, error = _finalize_portal_sale(transaction, warehouse, request.user)
        if error:
            messages.error(request, error)
            transaction.delete()
            return redirect('portal_cart')
        Payment.objects.create(
            transaction=transaction, method=payment_method,
            amount=transaction.grand_total, status='Paid',
        )
        log_action(request.user if request.user.is_authenticated else None, 'Create', 'SalesTransaction', transaction.pk, f'Portal checkout TXN {transaction.invoice_number}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        items_list = ', '.join(f'{item.product.name} x{item.quantity}' for item in items[:10])
        more_items = f' (+{len(items) - 10} more)' if len(items) > 10 else ''
        notify_admins(
            title=f'Online Order: {invoice_num}',
            body=f'New online order {invoice_num} placed by "{customer.name}" (email: {customer.email or "N/A"}, phone: {customer.phone or "N/A"}). Items ({len(items)}): {items_list}{more_items}. Total: Rs. {transaction.grand_total:,.2f}. Payment: {payment_method}. Warehouse: {warehouse.name}.',
            link=f'/sales/{transaction.uuid}/',
        )
        cart.items.all().delete()
        messages.success(request, f'Order {invoice_num} placed successfully!')
        return redirect('portal_order_detail', pk=transaction.pk)
    return render(request, 'customers/portal_checkout.html', {'cart': cart, 'items': items, 'customer': customer})


@login_required
def portal_khalti_callback_view(request):
    """
    Khalti redirects the customer's browser here after checkout. The pidx is
    verified against the lookup API (never trusting the redirect's query
    params alone) before the order is finalized and stock is deducted.
    """
    pidx = request.GET.get('pidx')
    payment = get_object_or_404(Payment, khalti_pidx=pidx, method='Khalti')
    transaction = payment.transaction

    if transaction.status == 'Completed':
        return redirect('portal_order_detail', pk=transaction.pk)

    try:
        result = khalti.lookup_payment(pidx)
    except khalti.KhaltiError as exc:
        messages.error(request, f'Could not verify Khalti payment: {exc}')
        return redirect('portal_cart')

    if result.get('status') == 'Completed':
        invoice_num, error = _finalize_portal_sale(transaction, transaction.warehouse, request.user)
        if error:
            messages.error(request, error)
            return redirect('portal_cart')
        payment.status = 'Paid'
        payment.amount_tendered = payment.amount
        payment.khalti_transaction_id = result.get('transaction_id')
        payment.save()
        log_action(request.user if request.user.is_authenticated else None, 'Create', 'SalesTransaction', transaction.pk, f'Portal checkout TXN {transaction.invoice_number} via Khalti', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        items_list = ', '.join(f'{line.product.name} x{line.quantity}' for line in transaction.lines.select_related('product').all()[:10])
        more_items = f' (+{transaction.lines.count() - 10} more)' if transaction.lines.count() > 10 else ''
        notify_admins(
            title=f'Online Order (Khalti): {transaction.invoice_number}',
            body=f'Online order {transaction.invoice_number} paid via Khalti. Amount: Rs. {transaction.grand_total:,.2f}. Khalti transaction ID: {result.get("transaction_id", "N/A")}. Customer: "{customer.name}". Items ({transaction.lines.count()}): {items_list}{more_items}. Warehouse: {transaction.warehouse.name}.',
            link=f'/sales/{transaction.uuid}/',
        )
        cart = _get_cart(request)
        cart.items.all().delete()
        messages.success(request, f'Order {invoice_num} placed successfully!')
        return redirect('portal_order_detail', pk=transaction.pk)
    else:
        payment.delete()
        transaction.delete()
        messages.error(request, f"Khalti payment {result.get('status', 'failed')}. Please try again.")
        return redirect('portal_cart')


@login_required
def portal_order_list_view(request):
    customer = Customer.objects.filter(user=request.user).first()
    if not customer:
        return render(request, 'customers/portal_order_list.html', {'orders': []})
    orders = SalesTransaction.objects.filter(customer=customer).select_related('channel').exclude(status='Draft')
    return render(request, 'customers/portal_order_list.html', {'orders': orders})


@login_required
def portal_order_detail_view(request, pk):
    order = get_object_or_404(SalesTransaction, pk=pk)
    if order.customer and order.customer.user != request.user:
        messages.error(request, 'Access denied.')
        return redirect('portal_order_list')
    lines = order.lines.select_related('product', 'variant').all()
    payments = order.payments.all()
    return render(request, 'customers/portal_order_detail.html', {
        'order': order, 'lines': lines, 'payments': payments,
    })


@login_required
def portal_return_request_view(request, pk):
    order = get_object_or_404(SalesTransaction, pk=pk, status='Completed')
    if order.customer and order.customer.user != request.user:
        messages.error(request, 'Access denied.')
        return redirect('portal_order_list')
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        return_request = Return.objects.create(
            original_transaction=order, requested_by=request.user,
            reason=reason, status='Requested',
        )
        total_refund = 0
        for line in order.lines.all():
            try:
                qty = max(0, int(request.POST.get(f'return_qty_{line.pk}', 0)))
            except (ValueError, TypeError):
                qty = 0
            qty = min(qty, line.quantity)
            if qty > 0:
                ReturnLine.objects.create(
                    return_request=return_request, transaction_line=line,
                    quantity_returned=qty, restock=True,
                )
                total_refund += qty * float(line.unit_price)
        return_request.refund_amount = total_refund
        return_request.save()
        log_action(request.user, 'Create', 'Return', return_request.pk, f'Portal return request for TXN {return_request.original_transaction.invoice_number}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        return_items = ', '.join(f'{rl.transaction_line.product.name} x{rl.quantity_returned}' for rl in return_request.lines.select_related('transaction_line__product').all())
        notify_admins(
            title=f'Portal Return Request: #{return_request.pk}',
            body=f'Customer "{request.user.get_full_name() or request.user.username}" requested return for order {return_request.original_transaction.invoice_number}. Items: {return_items}. Refund: Rs. {total_refund:,.2f}. Reason: {reason or "Not specified"}.',
            link=f'/sales/returns/{return_request.uuid}/',
        )
        messages.success(request, 'Return request submitted.')
        return redirect('portal_order_detail', pk=pk)
    lines = order.lines.select_related('product', 'variant').all()
    return render(request, 'customers/portal_return_request.html', {'order': order, 'lines': lines})


@login_required
def portal_settings_view(request):
    customer = Customer.objects.filter(user=request.user).first()
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        if customer:
            customer.name = f"{request.user.first_name} {request.user.last_name}".strip()
            customer.email = request.user.email
            customer.phone = request.POST.get('phone', customer.phone)
            customer.save()
        log_action(request.user, 'Update', 'Customer', customer.pk, f'Portal profile updated: {customer.name}', ip_address=request.META.get('REMOTE_ADDR'))
        messages.success(request, 'Settings updated.')
        return redirect('portal_settings')
    return render(request, 'customers/portal_settings.html', {'customer': customer})


@login_required
def portal_complaint_list_view(request):
    complaints = Complaint.objects.filter(user=request.user).select_related('order', 'product', 'responded_by')
    status_filter = request.GET.get('status', '')
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    paginator = Paginator(complaints, 10)
    page = request.GET.get('page', 1)
    complaints_page = paginator.get_page(page)
    counts = {
        'total': Complaint.objects.filter(user=request.user).count(),
        'open': Complaint.objects.filter(user=request.user, status='open').count(),
        'in_progress': Complaint.objects.filter(user=request.user, status='in_progress').count(),
        'resolved': Complaint.objects.filter(user=request.user, status='resolved').count(),
    }
    return render(request, 'customers/portal_complaint_list.html', {
        'complaints': complaints_page, 'status_filter': status_filter, 'counts': counts,
    })


@login_required
def portal_complaint_create_view(request):
    from sales.models import SalesTransaction
    orders = SalesTransaction.objects.filter(
        customer__user=request.user, status='Completed'
    ).exclude(invoice_number__isnull=True).order_by('-created_at')[:20]
    products = _products_with_stock().order_by('name')[:100]
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'other')
        priority = request.POST.get('priority', 'medium')
        order_id = request.POST.get('order_id')
        product_id = request.POST.get('product_id')
        if not subject or not description:
            messages.error(request, 'Subject and description are required.')
            return redirect('portal_complaint_create')
        complaint = Complaint.objects.create(
            user=request.user, subject=subject, description=description,
            category=category, priority=priority,
            order_id=order_id if order_id else None,
            product_id=product_id if product_id else None,
        )
        log_action(request.user, 'Create', 'Complaint', complaint.pk,
                   f'Complaint submitted: {complaint.subject}',
                   ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'New Complaint: {complaint.subject}',
            body=f'Customer "{request.user.get_full_name() or request.user.username}" (email: {request.user.email or "N/A"}) submitted a {complaint.priority} priority complaint in category "{complaint.get_category_display()}". Subject: {complaint.subject}. Description preview: "{description[:150]}{"..." if len(description) > 150 else ""}"',
            link=f'/admin-panel/complaints/{complaint.pk}/',
        )
        messages.success(request, 'Complaint submitted successfully. Our team will review it shortly.')
        return redirect('portal_complaint_detail', pk=complaint.pk)
    return render(request, 'customers/portal_complaint_create.html', {
        'orders': orders, 'products': products,
    })


@login_required
def portal_complaint_detail_view(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, user=request.user)
    replies = complaint.replies.select_related('user').all()
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if message:
            ComplaintReply.objects.create(
                complaint=complaint, user=request.user, message=message,
            )
            complaint.updated_at = timezone.now()
            complaint.save()
            messages.success(request, 'Reply sent.')
        return redirect('portal_complaint_detail', pk=pk)
    return render(request, 'customers/portal_complaint_detail.html', {
        'complaint': complaint, 'replies': replies,
    })
