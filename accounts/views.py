import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import UserProfile
from .forms import LoginForm, UserRegistrationForm, UserProfileForm, UserForm
from audit.utils import log_action


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            log_action(user, 'Login', 'User', user.pk, f'{user.username} logged in', ip_address=request.META.get('REMOTE_ADDR'))
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        log_action(request.user, 'Logout', 'User', request.user.pk, f'{request.user.username} logged out', ip_address=request.META.get('REMOTE_ADDR'))
    logout(request)
    return redirect('login')


@login_required
def password_change_view(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        elif len(new_password) < 6:
            messages.error(request, 'New password must be at least 6 characters.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            log_action(request.user, 'Update', 'User', request.user.pk, 'Changed own password')
            messages.success(request, 'Password changed successfully. Please log in again.')
            return redirect('login')
    return render(request, 'accounts/password_change.html')


def password_reset_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email address.')
            return render(request, 'accounts/password_reset.html')
        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        elif new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, 'Password reset successful. You can now log in.')
            return redirect('login')
    return render(request, 'accounts/password_reset.html')


@login_required
def register_view(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin_role:
        messages.error(request, 'Only administrators can create new user accounts.')
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = request.POST.get('role', 'sales')
            profile = user.profile
            profile.role = role
            profile.save()
            log_action(request.user, 'Create', 'User', user.pk, f'Created user {user.username} with role {role}', ip_address=request.META.get('REMOTE_ADDR'))
            messages.success(request, f'Account created for {user.username}.')
            return redirect('user_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'role': 'admin' if request.user.is_superuser else 'sales'}
    )
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'accounts/profile.html', {'form': form, 'profile': profile})


@login_required
def user_list_view(request):
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    from audit.models import AuditLog
    query = request.GET.get('q', '')
    users = User.objects.select_related('profile').all()
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    active_count = User.objects.filter(is_active=True).count()
    login_counts = {}
    for row in AuditLog.objects.filter(action='Login').values('user__pk').annotate(cnt=Count('id')):
        login_counts[str(row['user__pk'])] = row['cnt']
    paginator = Paginator(users, 10)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    return render(request, 'accounts/user_list.html', {
        'users': users_page, 'query': query, 'active_count': active_count,
        'login_counts_json': json.dumps(login_counts),
    })


@login_required
def user_detail_view(request, pk):
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    from audit.models import AuditLog
    from sales.models import SalesTransaction, Payment
    from django.db.models import Count, Sum
    from django.core.paginator import Paginator

    target_user = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=target_user, defaults={'role': 'sales'})

    logs_qs = AuditLog.objects.filter(user=target_user).order_by('-timestamp')
    logs_paginator = Paginator(logs_qs, 15)
    logs_page = logs_paginator.get_page(request.GET.get('logs_page', 1))

    total_actions = AuditLog.objects.filter(user=target_user).exclude(action__in=['Login', 'Logout', 'View']).count()
    login_count = AuditLog.objects.filter(user=target_user, action='Login').count()
    last_login_log = AuditLog.objects.filter(user=target_user, action='Login').order_by('-timestamp').first()

    sales_made = SalesTransaction.objects.filter(cashier=target_user, status='Completed')
    sales_count = sales_made.count()
    sales_revenue = sales_made.aggregate(total=Sum('grand_total'))['total'] or 0
    recent_sales = sales_made.order_by('-completed_at')[:10]

    payments_received = Payment.objects.filter(transaction__cashier=target_user)

    context = {
        'target_user': target_user,
        'profile': profile,
        'logs_page': logs_page,
        'total_actions': total_actions,
        'login_count': login_count,
        'last_login_log': last_login_log,
        'sales_count': sales_count,
        'sales_revenue': sales_revenue,
        'recent_sales': recent_sales,
        'payments_count': payments_received.count(),
    }
    return render(request, 'accounts/user_detail.html', context)


@login_required
def admin_reset_password_view(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
    target_user = get_object_or_404(User, pk=pk)
    if target_user.is_superuser:
        messages.error(request, 'The main admin password cannot be reset from here.')
        return redirect('user_detail', pk=pk)
    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        if len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        else:
            target_user.set_password(new_password)
            target_user.save()
            log_action(request.user, 'Update', 'User', target_user.pk,
                       f'Reset password for {target_user.username}', ip_address=request.META.get('REMOTE_ADDR'))
            messages.success(request, f'Password updated for {target_user.username}.')
    return redirect('user_detail', pk=pk)


@login_required
def user_edit_view(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
    target_user = get_object_or_404(User, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(
        user=target_user,
        defaults={'role': 'sales'}
    )
    if target_user.is_superuser and target_user.pk != request.user.pk:
        messages.error(request, 'The main admin account cannot be edited by others.')
        return redirect('user_list')
    if request.method == 'POST':
        old_role = profile.get_role_display()
        old_email = target_user.email
        target_user.first_name = request.POST.get('first_name', '')
        target_user.last_name = request.POST.get('last_name', '')
        target_user.email = request.POST.get('email', '')
        target_user.is_active = 'is_active' in request.POST
        target_user.save()
        profile.role = request.POST.get('role', profile.role)
        profile.phone = request.POST.get('phone', '')
        profile.save()
        log_action(request.user, 'Update', 'User', target_user.pk, f'Updated user: {target_user.username}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'User Updated: {target_user.username}',
            body=f'User "{target_user.username}" updated by {request.user.username}. Old role: {old_role} → New role: {profile.get_role_display()}. Email changed: {old_email} → {target_user.email}. Active: {"Yes" if target_user.is_active else "No"}',
            link=f'/accounts/users/{target_user.pk}/',
        )
        messages.success(request, f'User {target_user.username} updated.')
        return redirect('user_list')
    return render(request, 'accounts/user_edit.html', {'target_user': target_user, 'profile': profile})


@login_required
def user_deactivate_view(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
    target_user = get_object_or_404(User, pk=pk)
    if target_user.is_superuser:
        messages.error(request, 'The main admin account cannot be deactivated.')
        return redirect('user_detail', pk=pk)
    if request.method == 'POST':
        target_user.is_active = False
        target_user.save()
        user_profile, _ = UserProfile.objects.get_or_create(user=target_user, defaults={'role': 'sales'})
        log_action(request.user, 'Update', 'User', target_user.pk, f'Deactivated user: {target_user.username}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'User Deactivated: {target_user.username}',
            body=f'User "{target_user.username}" (role: {user_profile.get_role_display()}, email: {target_user.email}) deactivated by {request.user.username}. They can no longer log in.',
            link=f'/accounts/users/{target_user.pk}/',
        )
        messages.success(request, f'User {target_user.username} has been deactivated. They can no longer log in.')
        return redirect('user_detail', pk=pk)
    return render(request, 'accounts/user_confirm_deactivate.html', {'target_user': target_user})


@login_required
def user_activate_view(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
    target_user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        target_user.is_active = True
        target_user.save()
        user_profile, _ = UserProfile.objects.get_or_create(user=target_user, defaults={'role': 'sales'})
        log_action(request.user, 'Update', 'User', target_user.pk, f'Activated user: {target_user.username}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'User Activated: {target_user.username}',
            body=f'User "{target_user.username}" (role: {user_profile.get_role_display()}, email: {target_user.email}) activated by {request.user.username}. They can now log in.',
            link=f'/accounts/users/{target_user.pk}/',
        )
        messages.success(request, f'User {target_user.username} has been activated. They can now log in.')
    return redirect('user_detail', pk=pk)


@login_required
def user_delete_view(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
    target_user = get_object_or_404(User, pk=pk)
    if target_user.is_superuser:
        messages.error(request, 'The main admin account cannot be deleted.')
        return redirect('user_list')
    if target_user.pk == request.user.pk:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    if request.method == 'POST':
        username = target_user.username
        target_profile, _ = UserProfile.objects.get_or_create(user=target_user, defaults={'role': 'sales'})
        target_role = target_profile.get_role_display()
        from sales.models import Customer as SalesCustomer
        SalesCustomer.objects.filter(user=target_user).update(user=None)
        log_action(request.user, 'Delete', 'User', target_user.pk, f'Deleted user: {username}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'User Deleted: {username}',
            body=f'User "{username}" (role: {target_role}, email: {target_user.email}) permanently deleted by {request.user.username}.',
            link='/accounts/users/',
        )
        target_user.delete()
        messages.success(request, f'User "{username}" has been permanently deleted.')
        return redirect('user_list')
    return render(request, 'accounts/user_confirm_delete.html', {'target_user': target_user})


@login_required
def user_role_change_view(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
    target_user = get_object_or_404(User, pk=pk)
    if target_user.is_superuser:
        messages.error(request, 'The main admin role cannot be changed.')
        return redirect('user_detail', pk=pk)
    if target_user.pk == request.user.pk:
        messages.error(request, 'You cannot change your own role.')
        return redirect('user_detail', pk=pk)
    if request.method == 'POST':
        new_role = request.POST.get('role', '')
        valid_roles = dict(UserProfile.ROLE_CHOICES).keys()
        if new_role not in valid_roles:
            messages.error(request, 'Invalid role.')
            return redirect('user_detail', pk=pk)
        profile, _ = UserProfile.objects.get_or_create(user=target_user, defaults={'role': 'customer'})
        old_role = profile.get_role_display()
        profile.role = new_role
        profile.save()
        if new_role in ('admin', 'warehouse', 'sales', 'purchasing', 'auditor'):
            target_user.is_staff = True
            target_user.save(update_fields=['is_staff'])
        elif new_role == 'customer':
            target_user.is_staff = False
            target_user.save(update_fields=['is_staff'])
        log_action(request.user, 'Update', 'User', target_user.pk,
                   f'Changed role of {target_user.username} from {old_role} to {profile.get_role_display()}',
                   ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'User Role Changed',
            body=f'Role of "{target_user.username}" changed from {old_role} to {profile.get_role_display()} by {request.user.username}.',
            link=f'/accounts/users/{target_user.pk}/',
        )
        messages.success(request, f'{target_user.username} is now {profile.get_role_display()}.')
    return redirect('user_detail', pk=pk)


@login_required
def user_bulk_action_view(request):
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
    if request.method != 'POST':
        return redirect('user_list')
    action = request.POST.get('bulk_action', '')
    user_ids = request.POST.getlist('selected_users')
    if not user_ids:
        messages.error(request, 'No users selected.')
        return redirect('user_list')
    users = User.objects.filter(pk__in=user_ids).exclude(pk=request.user.pk).exclude(is_superuser=True)
    count = users.count()
    if count == 0:
        messages.error(request, 'No valid users selected.')
        return redirect('user_list')
    if action == 'bulk_delete':
        from sales.models import Customer as SalesCustomer
        SalesCustomer.objects.filter(user__in=users).update(user=None)
        for u in users:
            log_action(request.user, 'Delete', 'User', u.pk, f'Bulk deleted user: {u.username}', ip_address=request.META.get('REMOTE_ADDR'))
        users.delete()
        messages.success(request, f'{count} user(s) deleted.')
    elif action == 'bulk_activate':
        users.update(is_active=True)
        log_action(request.user, 'Update', 'User', None, f'Bulk activated {count} users', ip_address=request.META.get('REMOTE_ADDR'))
        messages.success(request, f'{count} user(s) activated.')
    elif action == 'bulk_deactivate':
        users.update(is_active=False)
        log_action(request.user, 'Update', 'User', None, f'Bulk deactivated {count} users', ip_address=request.META.get('REMOTE_ADDR'))
        messages.success(request, f'{count} user(s) deactivated.')
    elif action == 'bulk_role':
        new_role = request.POST.get('bulk_role_value', '')
        valid_roles = dict(UserProfile.ROLE_CHOICES).keys()
        if new_role not in valid_roles:
            messages.error(request, 'Invalid role selected.')
            return redirect('user_list')
        for u in users:
            profile, _ = UserProfile.objects.get_or_create(user=u, defaults={'role': 'sales'})
            old_role = profile.get_role_display()
            profile.role = new_role
            profile.save()
            if new_role in ('admin', 'warehouse', 'sales', 'purchasing', 'auditor'):
                u.is_staff = True
                u.save(update_fields=['is_staff'])
            elif new_role == 'customer':
                u.is_staff = False
                u.save(update_fields=['is_staff'])
            log_action(request.user, 'Update', 'User', u.pk,
                       f'Bulk role change: {u.username} -> {profile.get_role_display()}',
                       ip_address=request.META.get('REMOTE_ADDR'))
        messages.success(request, f'{count} user(s) changed to {dict(UserProfile.ROLE_CHOICES).get(new_role, new_role)}.')
    else:
        messages.error(request, 'Unknown action.')
    return redirect('user_list')


@login_required
def admin_panel_view(request):
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard')
    from django.contrib.auth.models import User
    from inventory.models import Warehouse, StockLevel, StockMovement, StockAdjustment, StockTransfer
    from suppliers.models import Supplier
    from catalog.models import Product, Category
    from sales.models import SalesTransaction, Customer, Return, Payment
    from purchasing.models import PurchaseOrder
    from notifications.models import Alert, Notification
    from audit.models import AuditLog
    from customers.models import Complaint
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    users = User.objects.select_related('profile').all()
    active_users = users.filter(is_active=True)
    admin_count = users.filter(profile__role='admin').count()
    sales_count_stat = users.filter(profile__role='sales').count()
    warehouse_count_stat = users.filter(profile__role='warehouse').count()
    customer_count_stat = users.filter(profile__role='customer').count()

    recent_activity = AuditLog.objects.select_related('user').all()[:15]
    login_today = AuditLog.objects.filter(action='Login', timestamp__gte=last_24h).count()
    actions_today = AuditLog.objects.filter(timestamp__gte=last_24h).count()
    actions_this_week = AuditLog.objects.filter(timestamp__gte=last_7d).count()

    top_users_this_week = (
        AuditLog.objects.filter(timestamp__gte=last_7d)
        .exclude(action__in=['Login', 'Logout', 'View'])
        .values('user__username')
        .annotate(action_count=Count('id'))
        .order_by('-action_count')[:5]
    )

    low_stock_products = StockLevel.objects.filter(quantity_on_hand__lte=10, quantity_on_hand__gt=0).select_related('product', 'warehouse').count()
    out_of_stock = StockLevel.objects.filter(quantity_on_hand=0).select_related('product', 'warehouse').count()
    total_stock_value = sum(sl.quantity_on_hand * sl.product.cost_price for sl in StockLevel.objects.select_related('product') if sl.product.cost_price)

    recent_sales_7d = SalesTransaction.objects.filter(status='Completed', completed_at__gte=last_7d)
    sales_count_7d = recent_sales_7d.count()
    sales_revenue_7d = recent_sales_7d.aggregate(total=Sum('grand_total'))['total'] or 0

    recent_purchases = PurchaseOrder.objects.exclude(status__in=['Cancelled', 'Closed']).count()
    pending_pos = PurchaseOrder.objects.filter(status='Draft').count()
    open_alerts = Alert.objects.filter(is_resolved=False).count()
    critical_alerts = Alert.objects.filter(is_resolved=False, severity='Critical').count()
    total_returns = Return.objects.filter(status='Requested').count()
    pending_transfers = StockTransfer.objects.filter(status='Requested').count()
    open_complaints = Complaint.objects.filter(status='open').count()

    today = now.date()
    txns_today = SalesTransaction.objects.filter(completed_at__date=today)
    revenue_today = txns_today.aggregate(total=Sum('grand_total'))['total'] or 0
    items_sold_today = SalesTransaction.objects.filter(status='Completed', completed_at__date=today).aggregate(
        total=Sum('lines__quantity')
    )['total'] or 0

    context = {
        'users': users,
        'active_users': active_users,
        'warehouse_count': Warehouse.objects.filter(is_active=True).count(),
        'supplier_count': Supplier.objects.filter(is_active=True).count(),
        'product_count': Product.objects.filter(is_active=True).count(),
        'category_count': Category.objects.count(),
        'customer_count': Customer.objects.filter(is_active=True).count(),
        'unresolved_alerts': open_alerts,
        'critical_alerts': critical_alerts,
        'recent_activity': recent_activity,
        'login_today': login_today,
        'actions_today': actions_today,
        'actions_this_week': actions_this_week,
        'top_users_this_week': top_users_this_week,
        'low_stock_products': low_stock_products,
        'out_of_stock': out_of_stock,
        'total_stock_value': total_stock_value,
        'sales_count_7d': sales_count_7d,
        'sales_revenue_7d': sales_revenue_7d,
        'recent_purchases': recent_purchases,
        'pending_pos': pending_pos,
        'total_returns': total_returns,
        'pending_transfers': pending_transfers,
        'open_complaints': open_complaints,
        'total_users': users.count(),
        'admin_count': admin_count,
        'sales_count_stat': sales_count_stat,
        'warehouse_count_stat': warehouse_count_stat,
        'customer_count_stat': customer_count_stat,
        'revenue_today': revenue_today,
        'items_sold_today': items_sold_today,
        'db_size': round(os.path.getsize(os.path.join(settings.BASE_DIR, 'db.sqlite3')) / (1024*1024), 2) if os.path.exists(os.path.join(settings.BASE_DIR, 'db.sqlite3')) else 0,
    }
    return render(request, 'accounts/admin_panel.html', context)


@login_required
def system_settings_view(request):
    if not request.user.is_superuser:
        messages.error(request, 'Admin access required.')
        return redirect('dashboard')
    from .models import SystemSettings
    sys_settings = SystemSettings.load()
    if request.method == 'POST':
        sys_settings.company_name = request.POST.get('company_name', sys_settings.company_name)
        sys_settings.company_email = request.POST.get('company_email', sys_settings.company_email)
        sys_settings.company_phone = request.POST.get('company_phone', sys_settings.company_phone)
        sys_settings.company_address = request.POST.get('company_address', sys_settings.company_address)
        sys_settings.currency_code = request.POST.get('currency_code', sys_settings.currency_code)
        sys_settings.currency_symbol = request.POST.get('currency_symbol', sys_settings.currency_symbol)
        sys_settings.default_valuation_method = request.POST.get('default_valuation_method', sys_settings.default_valuation_method)
        sys_settings.low_stock_threshold = int(request.POST.get('low_stock_threshold', sys_settings.low_stock_threshold))
        sys_settings.overstock_threshold = int(request.POST.get('overstock_threshold', sys_settings.overstock_threshold))
        sys_settings.auto_reorder_enabled = 'auto_reorder_enabled' in request.POST
        sys_settings.require_purchase_order_approval = 'require_purchase_order_approval' in request.POST
        sys_settings.enable_batch_tracking = 'enable_batch_tracking' in request.POST
        sys_settings.enable_serial_tracking = 'enable_serial_tracking' in request.POST
        sys_settings.session_timeout_minutes = int(request.POST.get('session_timeout_minutes', sys_settings.session_timeout_minutes))
        sys_settings.max_login_attempts = int(request.POST.get('max_login_attempts', sys_settings.max_login_attempts))
        sys_settings.lockout_duration_minutes = int(request.POST.get('lockout_duration_minutes', sys_settings.lockout_duration_minutes))
        sys_settings.enable_email_notifications = 'enable_email_notifications' in request.POST
        sys_settings.enable_low_stock_alerts = 'enable_low_stock_alerts' in request.POST
        sys_settings.enable_expiry_alerts = 'enable_expiry_alerts' in request.POST
        sys_settings.expiry_alert_days = int(request.POST.get('expiry_alert_days', sys_settings.expiry_alert_days))
        sys_settings.default_tax_rate = float(request.POST.get('default_tax_rate', sys_settings.default_tax_rate))
        sys_settings.receipt_footer_text = request.POST.get('receipt_footer_text', sys_settings.receipt_footer_text)
        sys_settings.save()
        log_action(request.user, 'Update', 'SystemSettings', sys_settings.pk, 'Updated system settings', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title='System Settings Updated',
            body=f'System settings updated by {request.user.username}. Low stock threshold: {sys_settings.low_stock_threshold}. Company: {sys_settings.company_name}. Currency: {sys_settings.currency_symbol} ({sys_settings.currency_code}). Auto reorder: {"Enabled" if sys_settings.auto_reorder_enabled else "Disabled"}.',
            link='/admin-panel/settings/',
        )
        messages.success(request, 'Settings saved successfully.')
        return redirect('system_settings')
    return render(request, 'accounts/system_settings.html', {'sys_settings': sys_settings})


@login_required
def admin_user_activity_view(request):
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard')
    from django.contrib.auth.models import User
    from audit.models import AuditLog
    from django.core.paginator import Paginator
    from django.db.models import Count

    user_filter = request.GET.get('user', '')
    action_filter = request.GET.get('action', '')
    logs = AuditLog.objects.select_related('user').all()
    if user_filter:
        logs = logs.filter(user__username=user_filter)
    if action_filter:
        logs = logs.filter(action=action_filter)

    user_stats = (
        AuditLog.objects.exclude(action__in=['Login', 'Logout'])
        .values('user__username')
        .annotate(total_actions=Count('id'))
        .order_by('-total_actions')[:20]
    )

    paginator = Paginator(logs, 30)
    page = request.GET.get('page', 1)
    logs_page = paginator.get_page(page)

    all_users = User.objects.filter(is_active=True).order_by('username')
    context = {
        'logs': logs_page,
        'user_stats': user_stats,
        'all_users': all_users,
        'selected_user': user_filter,
        'selected_action': action_filter,
    }
    return render(request, 'accounts/admin_user_activity.html', context)


@login_required
def admin_system_health_view(request):
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard')
    import os
    import platform
    from django.conf import settings
    from django.contrib.auth.models import User
    from inventory.models import Warehouse, StockLevel, StockMovement
    from catalog.models import Product, Category, Batch, SerialNumber
    from sales.models import SalesTransaction, Payment, Customer
    from purchasing.models import PurchaseOrder
    from suppliers.models import Supplier
    from customers.models import Cart, CartItem
    from notifications.models import Alert, Notification
    from audit.models import AuditLog
    from django.db.models import Sum, Count

    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
    db_size = round(os.path.getsize(db_path) / (1024*1024), 2) if os.path.exists(db_path) else 0

    context = {
        'db_size': db_size,
        'python_version': platform.python_version(),
        'django_version': __import__('django').get_version(),
        'platform': f"{platform.system()} {platform.release()}",
        'timezone': settings.TIME_ZONE,
        'debug_mode': settings.DEBUG,
        'session_expiry': settings.SESSION_COOKIE_AGE // 60,
        'model_counts': {
            'Users': User.objects.count(),
            'Products': Product.objects.count(),
            'Categories': Category.objects.count(),
            'Warehouses': Warehouse.objects.filter(is_active=True).count(),
            'Suppliers': Supplier.objects.filter(is_active=True).count(),
            'Customers': Customer.objects.filter(is_active=True).count(),
            'Stock Movements': StockMovement.objects.count(),
            'Transactions': SalesTransaction.objects.count(),
            'Purchase Orders': PurchaseOrder.objects.count(),
            'Alerts': Alert.objects.count(),
            'Notifications': Notification.objects.count(),
            'Audit Logs': AuditLog.objects.count(),
            'Batches': Batch.objects.count(),
            'Serial Numbers': SerialNumber.objects.count(),
            'Carts': Cart.objects.count(),
        },
        'storage_info': {
            'DB Size (MB)': db_size,
            'Total Stock Lines': StockLevel.objects.count(),
            'Total Payments': Payment.objects.count(),
        },
    }
    return render(request, 'accounts/admin_system_health.html', context)


@login_required
def admin_quick_actions_view(request):
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard')
    from notifications.models import Alert
    if request.method == 'POST':
        action_type = request.POST.get('action_type', '')
        if action_type == 'resolve_all_alerts':
            Alert.objects.filter(is_resolved=False).update(is_resolved=True)
            log_action(request.user, 'Update', 'Alert', None, 'Bulk resolved all alerts', ip_address=request.META.get('REMOTE_ADDR'))
            messages.success(request, 'All alerts resolved.')
        elif action_type == 'deactivate_inactive_users':
            from django.contrib.auth.models import User
            from django.utils import timezone
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(days=90)
            inactive = User.objects.filter(is_active=True, last_login__lt=cutoff).exclude(is_superuser=True)
            count = inactive.update(is_active=False)
            log_action(request.user, 'Update', 'User', None, f'Deactivated {count} users inactive for 90+ days', ip_address=request.META.get('REMOTE_ADDR'))
            messages.success(request, f'{count} inactive users deactivated.')
        elif action_type == 'clear_read_notifications':
            from notifications.models import Notification
            count, _ = Notification.objects.filter(is_read=True).delete()
            log_action(request.user, 'Delete', 'Notification', None, f'Cleared {count} read notifications', ip_address=request.META.get('REMOTE_ADDR'))
            messages.success(request, f'{count} read notifications cleared.')
        elif action_type == 'export_audit_log':
            from django.http import HttpResponse
            import csv
            logs = AuditLog.objects.select_related('user').all()[:5000]
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="audit_log_export.csv"'
            writer = csv.writer(response)
            writer.writerow(['Timestamp', 'User', 'Action', 'Model', 'Object', 'IP Address'])
            for log in logs:
                writer.writerow([log.timestamp, log.user or 'System', log.action, log.model_name, log.object_repr, log.ip_address or ''])
            return response
        return redirect('admin_quick_actions')
    return render(request, 'accounts/admin_quick_actions.html')


@login_required
def admin_complaint_list_view(request):
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard')
    from customers.models import Complaint
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    q = request.GET.get('q', '')
    complaints = Complaint.objects.select_related('user', 'order', 'product', 'responded_by').all()
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    if category_filter:
        complaints = complaints.filter(category=category_filter)
    if q:
        complaints = complaints.filter(Q(subject__icontains=q) | Q(user__username__icontains=q) | Q(user__email__icontains=q))
    paginator = Paginator(complaints, 15)
    page = request.GET.get('page', 1)
    complaints_page = paginator.get_page(page)
    counts = {
        'total': Complaint.objects.count(),
        'open': Complaint.objects.filter(status='open').count(),
        'in_progress': Complaint.objects.filter(status='in_progress').count(),
        'resolved': Complaint.objects.filter(status='resolved').count(),
        'closed': Complaint.objects.filter(status='closed').count(),
    }
    return render(request, 'accounts/admin_complaint_list.html', {
        'complaints': complaints_page, 'status_filter': status_filter,
        'category_filter': category_filter, 'query': q, 'counts': counts,
    })


@login_required
def admin_complaint_detail_view(request, pk):
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard')
    from customers.models import Complaint, ComplaintReply
    from django.utils import timezone
    complaint = get_object_or_404(Complaint, pk=pk)
    replies = complaint.replies.select_related('user').all()
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'reply':
            message = request.POST.get('message', '').strip()
            if message:
                ComplaintReply.objects.create(complaint=complaint, user=request.user, message=message)
                from notifications.utils import notify_user
                notify_user(complaint.user,
                    title=f'Reply to Complaint: {complaint.subject}',
                    body=f'{request.user.get_full_name() or request.user.username} replied to your complaint "{complaint.subject}" (status: {complaint.get_status_display()}). Message preview: "{message[:150]}{"..." if len(message) > 150 else ""}"',
                    link=f'/customers/support/{complaint.pk}/',
                )
                messages.success(request, 'Reply sent.')
        elif action == 'update_status':
            new_status = request.POST.get('new_status', '')
            if new_status in dict(Complaint.STATUS_CHOICES):
                old_status = complaint.get_status_display()
                complaint.status = new_status
                complaint.save()
                log_action(request.user, 'Update', 'Complaint', complaint.pk,
                           f'Complaint status changed to {complaint.get_status_display()}',
                           ip_address=request.META.get('REMOTE_ADDR'))
                messages.success(request, f'Complaint marked as {complaint.get_status_display()}.')
                from notifications.utils import notify_user
                if complaint.user:
                    notify_user(complaint.user,
                        title=f'Complaint Status Updated: {complaint.subject}',
                        body=f'Your complaint "{complaint.subject}" (category: {complaint.get_category_display()}, priority: {complaint.get_priority_display()}) status changed from "{old_status}" to "{complaint.get_status_display()}".',
                        link=f'/customers/support/{complaint.pk}/',
                    )
        elif action == 'admin_response':
            response_text = request.POST.get('admin_response', '').strip()
            if response_text:
                complaint.admin_response = response_text
                complaint.responded_by = request.user
                complaint.responded_at = timezone.now()
                complaint.save()
                log_action(request.user, 'Update', 'Complaint', complaint.pk,
                           'Admin response added to complaint',
                           ip_address=request.META.get('REMOTE_ADDR'))
                from notifications.utils import notify_user
                if complaint.user:
                    notify_user(complaint.user,
                        title=f'Complaint Response: {complaint.subject}',
                        body=f'Admin ({request.user.get_full_name() or request.user.username}) responded to your complaint "{complaint.subject}" (priority: {complaint.get_priority_display()}). Response preview: "{response_text[:150]}{"..." if len(response_text) > 150 else ""}"',
                        link=f'/customers/support/{complaint.pk}/',
                    )
                messages.success(request, 'Response saved.')
        return redirect('admin_complaint_detail', pk=pk)
    return render(request, 'accounts/admin_complaint_detail.html', {
        'complaint': complaint, 'replies': replies,
    })
