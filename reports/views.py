from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F, DecimalField, ExpressionWrapper, Avg, Value
from django.db.models.functions import TruncMonth
from django.db import models
from django.http import HttpResponse
from .pdf_utils import pdf_response
from django.utils import timezone
import csv
import datetime
from inventory.models import StockLevel, StockMovement, Warehouse
from catalog.models import Product, Category
from sales.models import SalesTransaction, SalesTransactionLine, Payment, Return, ReturnLine
from purchasing.models import PurchaseOrder, PurchaseOrderLine
from suppliers.models import Supplier
from accounts.models import SystemSettings
from notifications.models import Alert


@login_required
def dashboard_view(request):
    profile = None
    role = 'admin'
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
        role = profile.role
        if role == 'customer':
            return redirect('portal_home')

    now = timezone.now()
    thirty_days_ago = now - datetime.timedelta(days=30)

    total_stock_value = StockLevel.objects.filter(
        product__is_active=True
    ).aggregate(
        total=Sum(F('quantity_on_hand') * F('product__sale_price'), output_field=DecimalField())
    )['total'] or 0

    try:
        threshold = SystemSettings.objects.first().low_stock_threshold
    except Exception:
        threshold = 10

    low_stock_count = StockLevel.objects.filter(
        product__is_active=True, quantity_on_hand__lte=threshold
    ).count()

    pending_pos = PurchaseOrder.objects.filter(status__in=('Draft', 'Sent')).count()
    pending_sales = SalesTransaction.objects.filter(status='Draft').count()

    recent_sales_total = SalesTransaction.objects.filter(
        status='Completed', completed_at__gte=thirty_days_ago
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    recent_sales_count = SalesTransaction.objects.filter(
        status='Completed', completed_at__gte=thirty_days_ago
    ).count()

    top_products = SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__gte=thirty_days_ago
    ).values('product__name').annotate(
        total_qty=Sum('quantity'), total_revenue=Sum('subtotal')
    ).order_by('-total_revenue')[:5]

    recent_transactions = SalesTransaction.objects.select_related(
        'customer', 'channel'
    ).exclude(status='Draft')[:5]

    recent_pos = PurchaseOrder.objects.select_related('supplier').all()[:5]

    pending_returns = Return.objects.filter(status='Requested').count()

    context = {
        'role': role,
        'profile': profile,
        'total_stock_value': total_stock_value,
        'low_stock_count': low_stock_count,
        'pending_pos': pending_pos,
        'pending_sales': pending_sales,
        'recent_sales_total': recent_sales_total,
        'recent_sales_count': recent_sales_count,
        'top_products': top_products,
        'recent_transactions': recent_transactions,
        'recent_pos': recent_pos,
        'pending_returns': pending_returns,
        'unresolved_alerts': Alert.objects.filter(is_resolved=False).count(),
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def reports_home_view(request):
    now = timezone.now()
    thirty_days_ago = now - datetime.timedelta(days=30)
    total_sales = SalesTransaction.objects.filter(
        status='Completed', completed_at__gte=thirty_days_ago
    ).aggregate(total=Sum('grand_total'))['total'] or 0
    total_purchases = PurchaseOrderLine.objects.filter(
        po__status__in=['Received', 'Partially Received', 'Closed']
    ).aggregate(total=Sum(F('quantity_received') * F('unit_cost'), output_field=DecimalField()))['total'] or 0
    total_stock = StockLevel.objects.filter(
        product__is_active=True
    ).aggregate(
        total=Sum(F('quantity_on_hand') * F('product__sale_price'), output_field=DecimalField())
    )['total'] or 0
    total_returns_value = Return.objects.filter(
        status='Completed'
    ).aggregate(total=Sum('refund_amount'))['total'] or 0

    context = {
        'total_sales_30d': total_sales,
        'total_purchases_30d': total_purchases,
        'total_stock_value': total_stock,
        'total_returns_value': total_returns_value,
    }
    return render(request, 'reports/reports_home.html', context)


@login_required
def stock_valuation_view(request):
    stock_levels = StockLevel.objects.select_related('product', 'warehouse', 'variant').filter(
        product__is_active=True
    ).annotate(
        value=ExpressionWrapper(
            F('quantity_on_hand') * F('product__sale_price'),
            output_field=DecimalField()
        )
    )
    total_value = stock_levels.aggregate(total=Sum('value'))['total'] or 0
    by_category = stock_levels.values('product__category__name').annotate(
        total=Sum('value')
    ).order_by('-total')

    cost_value = StockLevel.objects.filter(
        product__is_active=True
    ).aggregate(
        total=Sum(F('quantity_on_hand') * F('product__cost_price'), output_field=DecimalField())
    )['total'] or 0

    potential_profit = total_value - cost_value

    out_of_stock = StockLevel.objects.filter(quantity_on_hand=0, product__is_active=True).count()
    low_stock = StockLevel.objects.filter(quantity_on_hand__lte=10, quantity_on_hand__gt=0, product__is_active=True).count()
    total_items = StockLevel.objects.filter(product__is_active=True).aggregate(total=Sum('quantity_on_hand'))['total'] or 0

    return render(request, 'reports/stock_valuation.html', {
        'stock_levels': stock_levels, 'total_value': total_value, 'by_category': by_category,
        'cost_value': cost_value, 'potential_profit': potential_profit,
        'out_of_stock': out_of_stock, 'low_stock': low_stock, 'total_items': total_items,
    })


@login_required
def sales_report_view(request):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - datetime.timedelta(days=days)
    prev_start = start_date - datetime.timedelta(days=days)

    transactions = SalesTransaction.objects.filter(
        status='Completed', completed_at__date__gte=start_date
    )
    prev_transactions = SalesTransaction.objects.filter(
        status='Completed', completed_at__date__gte=prev_start, completed_at__date__lt=start_date
    )

    total_sales = transactions.aggregate(total=Sum('grand_total'))['total'] or 0
    prev_sales = prev_transactions.aggregate(total=Sum('grand_total'))['total'] or 0
    total_transactions = transactions.count()
    avg_order_value = transactions.aggregate(avg=Avg('grand_total'))['avg'] or 0

    total_discount = transactions.aggregate(total=Sum('discount_total'))['total'] or 0
    total_tax = transactions.aggregate(total=Sum('tax_total'))['total'] or 0
    total_subtotal = transactions.aggregate(total=Sum('subtotal'))['total'] or 0

    by_day = transactions.extra(
        select={'date': "date(completed_at)"}
    ).values('date').annotate(
        total=Sum('grand_total'), count=Count('id')
    ).order_by('date')

    top_products = SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__date__gte=start_date
    ).values('product__name').annotate(
        total_qty=Sum('quantity'), total_revenue=Sum('subtotal')
    ).order_by('-total_revenue')[:10]

    by_payment = Payment.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__date__gte=start_date
    ).values('method').annotate(
        count=Count('id'), total=Sum('amount')
    ).order_by('-total')

    by_channel = transactions.values('channel__name').annotate(
        count=Count('id'), total=Sum('grand_total')
    ).order_by('-total')

    by_category = SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__date__gte=start_date
    ).values('product__category__name').annotate(
        total_qty=Sum('quantity'), total_revenue=Sum('subtotal')
    ).order_by('-total_revenue')

    hourly = transactions.extra(
        select={'hour': "strftime('%%H', completed_at)"}
    ).values('hour').annotate(count=Count('id'), total=Sum('grand_total')).order_by('hour')

    growth_pct = 0
    if prev_sales > 0:
        growth_pct = round(((total_sales - prev_sales) / prev_sales) * 100, 1)

    unique_customers = transactions.values('customer').distinct().count()

    return render(request, 'reports/sales_report.html', {
        'total_sales': total_sales, 'total_transactions': total_transactions,
        'by_day': list(by_day), 'top_products': top_products, 'days': days,
        'avg_order_value': avg_order_value, 'total_discount': total_discount,
        'total_tax': total_tax, 'total_subtotal': total_subtotal,
        'by_payment': by_payment, 'by_channel': by_channel,
        'by_category': by_category, 'hourly': hourly,
        'growth_pct': growth_pct, 'prev_sales': prev_sales,
        'unique_customers': unique_customers,
    })


@login_required
def purchase_report_view(request):
    days = int(request.GET.get('days', 90))
    start_date = timezone.now().date() - datetime.timedelta(days=days)

    pos = PurchaseOrder.objects.filter(
        status__in=('Received', 'Partially Received', 'Closed'),
        order_date__gte=start_date
    )
    all_pos = pos | PurchaseOrder.objects.filter(order_date__gte=start_date)

    total_cost = PurchaseOrderLine.objects.filter(
        po__in=pos
    ).aggregate(total=Sum(F('quantity_received') * F('unit_cost'), output_field=DecimalField()))['total'] or 0

    total_items_received = PurchaseOrderLine.objects.filter(
        po__in=pos
    ).aggregate(total=Sum('quantity_received'))['total'] or 0

    by_supplier = PurchaseOrderLine.objects.filter(
        po__in=pos
    ).values('po__supplier__name').annotate(
        count=Count('po_id', distinct=True),
        total_cost=Sum(F('quantity_received') * F('unit_cost'), output_field=DecimalField())
    ).order_by('-total_cost')

    by_status = all_pos.values('status').annotate(count=Count('id'))

    monthly_pos = pos.annotate(
        month=TruncMonth('order_date')
    ).values('month').annotate(
        count=Count('id'),
        total=Sum(F('lines__quantity_received') * F('lines__unit_cost'), output_field=DecimalField())
    ).order_by('month')

    recent_pos = all_pos.select_related('supplier').order_by('-order_date')[:20]

    supplier_receiving = PurchaseOrderLine.objects.filter(
        po__in=pos
    ).values('po__supplier__name').annotate(
        total_ordered=Sum('quantity_ordered'),
        total_received=Sum('quantity_received'),
    ).order_by('-total_received')

    total_pos_count = all_pos.count()

    return render(request, 'reports/purchase_report.html', {
        'recent_pos': recent_pos, 'by_supplier': by_supplier,
        'total_cost': total_cost, 'total_items_received': total_items_received,
        'by_status': by_status, 'monthly_pos': monthly_pos,
        'supplier_receiving': supplier_receiving, 'days': days,
        'total_pos_count': total_pos_count,
    })


@login_required
def shrinkage_report_view(request):
    from inventory.models import ReasonCode
    shrinkage_movements = StockMovement.objects.filter(
        reason_code__affects_shrinkage_report=True
    ).select_related('product', 'warehouse', 'reason_code', 'user')
    total_shrinkage = shrinkage_movements.aggregate(
        total=Sum('quantity_delta')
    )['total'] or 0
    by_reason = shrinkage_movements.values('reason_code__code', 'reason_code__label').annotate(
        total=Sum('quantity_delta')
    )
    by_product = shrinkage_movements.values('product__name').annotate(
        total=Sum('quantity_delta')
    ).order_by('total')[:10]
    by_warehouse = shrinkage_movements.values('warehouse__name').annotate(
        total=Sum('quantity_delta')
    )
    by_user = shrinkage_movements.values('user__username').annotate(
        total=Count('id')
    ).order_by('-total')[:10]

    return render(request, 'reports/shrinkage_report.html', {
        'movements': shrinkage_movements, 'total_shrinkage': total_shrinkage,
        'by_reason': by_reason, 'by_product': by_product,
        'by_warehouse': by_warehouse, 'by_user': by_user,
    })


@login_required
def supplier_performance_view(request):
    suppliers = Supplier.objects.filter(is_active=True).annotate(
        po_count=Count('purchase_orders'),
        total_spend=Sum(F('purchase_orders__lines__quantity_received') * F('purchase_orders__lines__unit_cost'), output_field=DecimalField()),
        avg_lead_time=Avg('lead_time_days'),
    )

    total_suppliers = suppliers.count()
    total_spend = suppliers.aggregate(total=Sum('total_spend'))['total'] or 0
    avg_lead = suppliers.aggregate(avg=Avg('lead_time_days'))['avg'] or 0
    avg_on_time = suppliers.aggregate(avg=Avg('on_time_pct'))['avg'] or 0

    return render(request, 'reports/supplier_performance.html', {
        'suppliers': suppliers,
        'total_suppliers': total_suppliers, 'total_spend': total_spend,
        'avg_lead': avg_lead, 'avg_on_time': avg_on_time,
    })


@login_required
def product_performance_view(request):
    days = int(request.GET.get('days', 90))
    start_date = timezone.now().date() - datetime.timedelta(days=days)

    products = Product.objects.filter(is_active=True).annotate(
        total_sold=Sum('sale_lines__quantity', filter=Q(sale_lines__transaction__status='Completed', sale_lines__transaction__completed_at__date__gte=start_date)),
        total_revenue=Sum('sale_lines__subtotal', filter=Q(sale_lines__transaction__status='Completed', sale_lines__transaction__completed_at__date__gte=start_date)),
        total_cost=Sum(F('sale_lines__quantity') * F('cost_price'), filter=Q(sale_lines__transaction__status='Completed', sale_lines__transaction__completed_at__date__gte=start_date), output_field=DecimalField()),
        transaction_count=Count('sale_lines__transaction', filter=Q(sale_lines__transaction__status='Completed', sale_lines__transaction__completed_at__date__gte=start_date), distinct=True),
    ).order_by('-total_revenue')

    products_list = list(products)
    total_products_sold = len([p for p in products_list if (p.total_sold or 0) > 0])
    total_revenue = sum(p.total_revenue or 0 for p in products_list)
    total_sold_qty = sum(p.total_sold or 0 for p in products_list)
    total_profit = sum((p.total_revenue or 0) - (p.total_cost or 0) for p in products_list)

    return render(request, 'reports/product_performance.html', {
        'products': products_list[:50], 'days': days,
        'total_products_sold': total_products_sold, 'total_revenue': total_revenue,
        'total_sold_qty': total_sold_qty, 'total_profit': total_profit,
    })


@login_required
def profit_loss_view(request):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - datetime.timedelta(days=days)

    revenue = SalesTransaction.objects.filter(
        status='Completed', completed_at__date__gte=start_date
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    cost_of_goods = SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__date__gte=start_date
    ).annotate(
        line_cost=F('quantity') * F('product__cost_price')
    ).aggregate(total=Sum('line_cost'))['total'] or 0

    discounts = SalesTransaction.objects.filter(
        status='Completed', completed_at__date__gte=start_date
    ).aggregate(total=Sum('discount_total'))['total'] or 0

    taxes = SalesTransaction.objects.filter(
        status='Completed', completed_at__date__gte=start_date
    ).aggregate(total=Sum('tax_total'))['total'] or 0

    refunds = Return.objects.filter(
        status='Completed', processed_at__date__gte=start_date
    ).aggregate(total=Sum('refund_amount'))['total'] or 0

    gross_profit = revenue - cost_of_goods
    gross_margin = round((gross_profit / revenue * 100), 1) if revenue > 0 else 0
    net_profit = gross_profit - discounts - refunds

    by_day = SalesTransaction.objects.filter(
        status='Completed', completed_at__date__gte=start_date
    ).extra(
        select={'date': "date(completed_at)"}
    ).values('date').annotate(
        revenue=Sum('grand_total'),
        discount=Sum('discount_total'),
        tax=Sum('tax_total'),
    ).order_by('date')

    by_category = SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__date__gte=start_date
    ).values('product__category__name').annotate(
        revenue=Sum('subtotal'),
        cost=Sum(F('quantity') * F('product__cost_price'), output_field=DecimalField()),
    ).order_by('-revenue')

    return render(request, 'reports/profit_loss.html', {
        'revenue': revenue, 'cost_of_goods': cost_of_goods,
        'gross_profit': gross_profit, 'gross_margin': gross_margin,
        'net_profit': net_profit, 'discounts': discounts,
        'taxes': taxes, 'refunds': refunds, 'days': days,
        'by_day': list(by_day), 'by_category': by_category,
    })


@login_required
def payment_methods_view(request):
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - datetime.timedelta(days=days)

    payments = Payment.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__date__gte=start_date
    )

    by_method = payments.values('method').annotate(
        count=Count('id'),
        total=Sum('amount'),
        avg=Avg('amount'),
    ).order_by('-total')

    total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
    total_count = payments.count()

    by_day = payments.extra(
        select={'date': "date(paid_at)"}
    ).values('date', 'method').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('date')

    by_status = payments.values('status').annotate(
        count=Count('id'), total=Sum('amount')
    )

    return render(request, 'reports/payment_methods.html', {
        'by_method': by_method, 'total_amount': total_amount,
        'total_count': total_count, 'by_day': list(by_day),
        'by_status': by_status, 'days': days,
        'avg_payment': total_amount / total_count if total_count else 0,
    })


@login_required
def returns_analysis_view(request):
    days = int(request.GET.get('days', 90))
    start_date = timezone.now().date() - datetime.timedelta(days=days)

    returns = Return.objects.filter(created_at__date__gte=start_date).select_related(
        'original_transaction', 'requested_by', 'processed_by'
    )

    total_returns = returns.count()
    total_refund = returns.filter(status='Completed').aggregate(total=Sum('refund_amount'))['total'] or 0
    pending_returns = returns.filter(status='Requested').count()

    by_status = returns.values('status').annotate(count=Count('id'), total=Sum('refund_amount'))

    by_product = ReturnLine.objects.filter(
        return_request__created_at__date__gte=start_date
    ).values('transaction_line__product__name').annotate(
        qty_returned=Sum('quantity_returned'),
        count=Count('return_request'),
    ).order_by('-qty_returned')[:10]

    by_reason = returns.exclude(reason='').values('reason').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    by_condition = ReturnLine.objects.filter(
        return_request__created_at__date__gte=start_date
    ).values('condition').annotate(count=Count('id'), qty=Sum('quantity_returned'))

    by_day = returns.extra(
        select={'date': "date(created_at)"}
    ).values('date').annotate(count=Count('id')).order_by('date')

    total_transactions = SalesTransaction.objects.filter(
        status='Completed', completed_at__date__gte=start_date
    ).count()
    return_rate = round((total_returns / total_transactions * 100), 1) if total_transactions > 0 else 0

    return render(request, 'reports/returns_analysis.html', {
        'returns': returns[:30], 'total_returns': total_returns,
        'total_refund': total_refund, 'pending_returns': pending_returns,
        'by_status': by_status, 'by_product': by_product,
        'by_reason': by_reason, 'by_condition': by_condition,
        'by_day': list(by_day), 'days': days, 'return_rate': return_rate,
        'total_transactions': total_transactions,
    })


@login_required
def category_analysis_view(request):
    days = int(request.GET.get('days', 90))
    start_date = timezone.now().date() - datetime.timedelta(days=days)

    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True)),
        total_sold=Sum('products__sale_lines__quantity', filter=Q(
            products__sale_lines__transaction__status='Completed',
            products__sale_lines__transaction__completed_at__date__gte=start_date
        )),
        total_revenue=Sum('products__sale_lines__subtotal', filter=Q(
            products__sale_lines__transaction__status='Completed',
            products__sale_lines__transaction__completed_at__date__gte=start_date
        )),
        stock_qty=Sum('products__stock_levels__quantity_on_hand'),
    ).order_by('-total_revenue')

    total_revenue = SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__date__gte=start_date
    ).aggregate(total=Sum('subtotal'))['total'] or 0

    total_products = Category.objects.filter(
        products__is_active=True
    ).aggregate(total=Count('products'))['total'] or 0

    total_stock = Category.objects.aggregate(
        total=Sum('products__stock_levels__quantity_on_hand')
    )['total'] or 0

    return render(request, 'reports/category_analysis.html', {
        'categories': categories, 'total_revenue': total_revenue, 'days': days,
        'total_products': total_products, 'total_stock': total_stock,
    })


@login_required
def stock_health_view(request):
    stock_levels = StockLevel.objects.filter(
        product__is_active=True
    ).select_related('product', 'warehouse')

    healthy = stock_levels.filter(
        quantity_on_hand__gt=F('reorder_min')
    ).exclude(reorder_min__isnull=True).count()
    healthy += stock_levels.filter(reorder_min__isnull=True, quantity_on_hand__gt=0).count()

    out_of_stock = stock_levels.filter(quantity_on_hand=0).count()
    low_stock = stock_levels.filter(
        quantity_on_hand__gt=0, quantity_on_hand__lte=10
    ).count()
    overstocked = stock_levels.filter(
        quantity_on_hand__gte=500
    ).count()

    turnover_data = SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__gte=timezone.now() - datetime.timedelta(days=30)
    ).values('product__name', 'product__sku').annotate(
        sold=Sum('quantity'),
        revenue=Sum('subtotal'),
    ).order_by('-sold')[:20]

    return render(request, 'reports/stock_health.html', {
        'out_of_stock': out_of_stock, 'low_stock': low_stock,
        'overstocked': overstocked, 'turnover_data': turnover_data,
        'total_lines': stock_levels.count(), 'healthy': healthy,
    })


@login_required
def generate_pdf_view(request, report_type):
    from django.utils import timezone as tz
    from accounts.models import SystemSettings
    sys_settings = SystemSettings.load()
    base_ctx = {
        'generated_at': tz.now().strftime('%d %b %Y, %I:%M %p'),
        'company_name': sys_settings.company_name,
    }

    if report_type == 'sales':
        days = int(request.GET.get('days', 30))
        start_date = tz.now().date() - datetime.timedelta(days=days)
        txns = SalesTransaction.objects.filter(status='Completed', completed_at__date__gte=start_date)
        total = txns.aggregate(t=Sum('grand_total'))['t'] or 0
        count = txns.count()
        avg = txns.aggregate(a=Avg('grand_total'))['a'] or 0
        top_products = SalesTransactionLine.objects.filter(
            transaction__status='Completed', transaction__completed_at__date__gte=start_date
        ).values('product__name').annotate(qty=Sum('quantity'), rev=Sum('subtotal')).order_by('-rev')[:10]
        by_payment = Payment.objects.filter(
            transaction__status='Completed', transaction__completed_at__date__gte=start_date
        ).values('method').annotate(count=Count('id'), total=Sum('amount')).order_by('-total')
        base_ctx.update({
            'title': 'Sales Report', 'subtitle': f'Last {days} days ({start_date} to {tz.now().date()})',
            'total_sales': total, 'total_transactions': count, 'avg_order': avg,
            'top_products': top_products, 'by_payment': by_payment, 'days': days,
        })
        return pdf_response('reports/pdf/sales_report_pdf.html', base_ctx, f'sales_report_{days}d.pdf')

    elif report_type == 'purchase':
        days = int(request.GET.get('days', 90))
        start_date = tz.now().date() - datetime.timedelta(days=days)
        pos = PurchaseOrder.objects.filter(status__in=['Received', 'Partially Received', 'Closed'], order_date__gte=start_date)
        total_cost = PurchaseOrderLine.objects.filter(po__in=pos).aggregate(
            t=Sum(F('quantity_received') * F('unit_cost'), output_field=DecimalField())
        )['t'] or 0
        total_items = PurchaseOrderLine.objects.filter(po__in=pos).aggregate(t=Sum('quantity_received'))['t'] or 0
        by_supplier = pos.values('supplier__name').annotate(
            count=Count('id'), total=Sum(F('quantity_received') * F('unit_cost'), output_field=DecimalField())
        ).order_by('-total')
        base_ctx.update({
            'title': 'Purchase Report', 'subtitle': f'Last {days} days',
            'total_cost': total_cost, 'total_items': total_items,
            'by_supplier': by_supplier, 'pos': pos.select_related('supplier')[:30], 'days': days,
        })
        return pdf_response('reports/pdf/purchase_report_pdf.html', base_ctx, f'purchase_report_{days}d.pdf')

    elif report_type == 'stock_valuation':
        stock = StockLevel.objects.filter(product__is_active=True).select_related('product', 'warehouse').annotate(
            value=ExpressionWrapper(F('quantity_on_hand') * F('product__sale_price'), output_field=DecimalField()),
            cost=ExpressionWrapper(F('quantity_on_hand') * F('product__cost_price'), output_field=DecimalField()),
        )
        total_val = stock.aggregate(t=Sum('value'))['t'] or 0
        total_cost = stock.aggregate(t=Sum('cost'))['t'] or 0
        by_cat = stock.values('product__category__name').annotate(val=Sum('value')).order_by('-val')
        base_ctx.update({
            'title': 'Stock Valuation Report', 'subtitle': f'All active products',
            'total_value': total_val, 'total_cost': total_cost, 'stock': stock[:50], 'by_category': by_cat,
        })
        return pdf_response('reports/pdf/stock_valuation_pdf.html', base_ctx, 'stock_valuation.pdf')

    elif report_type == 'profit_loss':
        days = int(request.GET.get('days', 30))
        start_date = tz.now().date() - datetime.timedelta(days=days)
        revenue = SalesTransaction.objects.filter(status='Completed', completed_at__date__gte=start_date).aggregate(t=Sum('grand_total'))['t'] or 0
        cogs = SalesTransactionLine.objects.filter(transaction__status='Completed', transaction__completed_at__date__gte=start_date).annotate(lc=F('quantity') * F('product__cost_price')).aggregate(t=Sum('lc'))['t'] or 0
        discounts = SalesTransaction.objects.filter(status='Completed', completed_at__date__gte=start_date).aggregate(t=Sum('discount_total'))['t'] or 0
        taxes = SalesTransaction.objects.filter(status='Completed', completed_at__date__gte=start_date).aggregate(t=Sum('tax_total'))['t'] or 0
        refunds = Return.objects.filter(status='Completed', processed_at__date__gte=start_date).aggregate(t=Sum('refund_amount'))['t'] or 0
        gp = revenue - cogs
        gm = round((gp / revenue * 100), 1) if revenue > 0 else 0
        base_ctx.update({
            'title': 'Profit & Loss Statement', 'subtitle': f'Last {days} days',
            'revenue': revenue, 'cogs': cogs, 'gross_profit': gp, 'gross_margin': gm,
            'discounts': discounts, 'taxes': taxes, 'refunds': refunds, 'days': days,
        })
        return pdf_response('reports/pdf/profit_loss_pdf.html', base_ctx, f'profit_loss_{days}d.pdf')

    elif report_type == 'payment_methods':
        days = int(request.GET.get('days', 30))
        start_date = tz.now().date() - datetime.timedelta(days=days)
        payments = Payment.objects.filter(transaction__status='Completed', transaction__completed_at__date__gte=start_date)
        by_method = payments.values('method').annotate(count=Count('id'), total=Sum('amount'), avg=Avg('amount')).order_by('-total')
        total_amt = payments.aggregate(t=Sum('amount'))['t'] or 0
        total_cnt = payments.count()
        base_ctx.update({
            'title': 'Payment Methods Report', 'subtitle': f'Last {days} days',
            'by_method': by_method, 'total_amount': total_amt, 'total_count': total_cnt, 'days': days,
        })
        return pdf_response('reports/pdf/payment_methods_pdf.html', base_ctx, f'payment_methods_{days}d.pdf')

    elif report_type == 'returns_analysis':
        days = int(request.GET.get('days', 90))
        start_date = tz.now().date() - datetime.timedelta(days=days)
        returns = Return.objects.filter(created_at__date__gte=start_date)
        total_ret = returns.count()
        total_refund = returns.filter(status='Completed').aggregate(t=Sum('refund_amount'))['t'] or 0
        by_status = returns.values('status').annotate(count=Count('id'), total=Sum('refund_amount'))
        by_product = ReturnLine.objects.filter(return_request__created_at__date__gte=start_date).values(
            'transaction_line__product__name'
        ).annotate(qty=Sum('quantity_returned'), count=Count('return_request')).order_by('-qty')[:10]
        base_ctx.update({
            'title': 'Returns Analysis Report', 'subtitle': f'Last {days} days',
            'total_returns': total_ret, 'total_refund': total_refund,
            'by_status': by_status, 'by_product': by_product, 'days': days,
        })
        return pdf_response('reports/pdf/returns_analysis_pdf.html', base_ctx, f'returns_analysis_{days}d.pdf')

    elif report_type == 'shrinkage':
        shrinkage = StockMovement.objects.filter(reason_code__affects_shrinkage_report=True).select_related('product', 'warehouse', 'reason_code', 'user')
        total_sh = shrinkage.aggregate(t=Sum('quantity_delta'))['t'] or 0
        by_reason = shrinkage.values('reason_code__code', 'reason_code__label').annotate(t=Sum('quantity_delta'))
        by_product = shrinkage.values('product__name').annotate(t=Sum('quantity_delta')).order_by('t')[:10]
        base_ctx.update({
            'title': 'Shrinkage Report', 'subtitle': 'Damage, theft, and wastage tracking',
            'total_shrinkage': total_sh, 'by_reason': by_reason,
            'movements': shrinkage[:30], 'by_product': by_product,
        })
        return pdf_response('reports/pdf/shrinkage_report_pdf.html', base_ctx, 'shrinkage_report.pdf')

    elif report_type == 'supplier_performance':
        suppliers = Supplier.objects.filter(is_active=True).annotate(
            po_count=Count('purchase_orders'),
            total_spend=Sum(F('purchase_orders__lines__quantity_received') * F('purchase_orders__lines__unit_cost'), output_field=DecimalField()),
        )
        base_ctx.update({
            'title': 'Supplier Performance Report', 'subtitle': 'All active suppliers',
            'suppliers': suppliers,
        })
        return pdf_response('reports/pdf/supplier_performance_pdf.html', base_ctx, 'supplier_performance.pdf')

    elif report_type == 'product_performance':
        days = int(request.GET.get('days', 90))
        start_date = tz.now().date() - datetime.timedelta(days=days)
        products = Product.objects.filter(is_active=True).annotate(
            total_sold=Sum('sale_lines__quantity', filter=Q(sale_lines__transaction__status='Completed', sale_lines__transaction__completed_at__date__gte=start_date)),
            total_revenue=Sum('sale_lines__subtotal', filter=Q(sale_lines__transaction__status='Completed', sale_lines__transaction__completed_at__date__gte=start_date)),
        ).order_by('-total_revenue')[:50]
        base_ctx.update({
            'title': 'Product Performance Report', 'subtitle': f'Last {days} days',
            'products': products, 'days': days,
        })
        return pdf_response('reports/pdf/product_performance_pdf.html', base_ctx, f'product_performance_{days}d.pdf')

    elif report_type == 'category_analysis':
        days = int(request.GET.get('days', 90))
        start_date = tz.now().date() - datetime.timedelta(days=days)
        categories = Category.objects.annotate(
            product_count=Count('products', filter=Q(products__is_active=True)),
            total_sold=Sum('products__sale_lines__quantity', filter=Q(products__sale_lines__transaction__status='Completed', products__sale_lines__transaction__completed_at__date__gte=start_date)),
            total_revenue=Sum('products__sale_lines__subtotal', filter=Q(products__sale_lines__transaction__status='Completed', products__sale_lines__transaction__completed_at__date__gte=start_date)),
        ).order_by('-total_revenue')
        base_ctx.update({
            'title': 'Category Analysis Report', 'subtitle': f'Last {days} days',
            'categories': categories, 'days': days,
        })
        return pdf_response('reports/pdf/category_analysis_pdf.html', base_ctx, f'category_analysis_{days}d.pdf')

    elif report_type == 'stock_health':
        out_of_stock = StockLevel.objects.filter(quantity_on_hand=0, product__is_active=True).count()
        low_stock = StockLevel.objects.filter(quantity_on_hand__gt=0, quantity_on_hand__lte=10, product__is_active=True).count()
        overstocked = StockLevel.objects.filter(quantity_on_hand__gte=500, product__is_active=True).count()
        top_sellers = SalesTransactionLine.objects.filter(
            transaction__status='Completed', transaction__completed_at__gte=tz.now() - datetime.timedelta(days=30)
        ).values('product__name', 'product__sku').annotate(sold=Sum('quantity'), revenue=Sum('subtotal')).order_by('-sold')[:20]
        base_ctx.update({
            'title': 'Stock Health Report', 'subtitle': 'Inventory health analysis',
            'out_of_stock': out_of_stock, 'low_stock': low_stock,
            'overstocked': overstocked, 'top_sellers': top_sellers,
        })
        return pdf_response('reports/pdf/stock_health_pdf.html', base_ctx, 'stock_health.pdf')

    return HttpResponse('Invalid report type', status=400)


@login_required
def export_csv_view(request, report_type):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    writer = csv.writer(response)
    if report_type == 'stock':
        writer.writerow(['Product', 'SKU', 'Warehouse', 'Quantity', 'Cost Price', 'Sale Price', 'Value'])
        for sl in StockLevel.objects.select_related('product', 'warehouse').filter(product__is_active=True):
            writer.writerow([sl.product.name, sl.product.sku, sl.warehouse.name,
                           sl.quantity_on_hand, sl.product.cost_price, sl.product.sale_price,
                           sl.quantity_on_hand * sl.product.sale_price])
    elif report_type == 'sales':
        writer.writerow(['Invoice', 'Date', 'Customer', 'Subtotal', 'Discount', 'Tax', 'Total', 'Status'])
        for t in SalesTransaction.objects.filter(status='Completed').select_related('customer'):
            writer.writerow([t.invoice_number, t.completed_at, t.customer or 'Walk-in',
                           t.subtotal, t.discount_total, t.tax_total, t.grand_total, t.status])
    elif report_type == 'purchases':
        writer.writerow(['PO Number', 'Supplier', 'Date', 'Status', 'Total Cost', 'Items Received'])
        for po in PurchaseOrder.objects.all().select_related('supplier'):
            total = po.lines.aggregate(total=Sum(F('quantity_received') * F('unit_cost'), output_field=DecimalField()))['total'] or 0
            items = po.lines.aggregate(total=Sum('quantity_received'))['total'] or 0
            writer.writerow([po.po_number, po.supplier.name, po.order_date,
                           po.status, total, items])
    elif report_type == 'transactions':
        writer.writerow(['Invoice', 'Customer', 'Channel', 'Subtotal', 'Discount', 'Tax', 'Total', 'Status', 'Date'])
        for t in SalesTransaction.objects.all().select_related('customer', 'channel'):
            writer.writerow([t.invoice_number or 'Draft', t.customer or 'Walk-in',
                           t.channel, t.subtotal, t.discount_total, t.tax_total,
                           t.grand_total, t.status,
                           t.created_at.strftime('%d %b %Y %H:%M')])
    elif report_type == 'customers':
        from sales.models import Customer
        writer.writerow(['Name', 'Email', 'Phone', 'Status', 'Orders', 'Total Spent'])
        for c in Customer.objects.all():
            orders = c.transactions.filter(status='Completed').count()
            spent = c.transactions.filter(status='Completed').aggregate(total=Sum('grand_total'))['total'] or 0
            writer.writerow([c.name, c.email or '', c.phone or '',
                           'Active' if c.is_active else 'Inactive', orders, spent])
    elif report_type == 'profit_loss':
        writer.writerow(['Date', 'Revenue', 'Discounts', 'Tax', 'COGS', 'Gross Profit'])
        SalesTransaction.objects.filter(status='Completed').extra(
            select={'date': "date(completed_at)"}
        ).values('date').annotate(
            rev=Sum('grand_total'), disc=Sum('discount_total'), tax=Sum('tax_total')
        ).order_by('date')
        for row in SalesTransaction.objects.filter(status='Completed').extra(
            select={'date': "date(completed_at)"}
        ).values('date').annotate(
            rev=Sum('grand_total'), disc=Sum('discount_total'), tax=Sum('tax_total')
        ).order_by('date'):
            writer.writerow([row['date'], row['rev'], row['disc'], row['tax'],
                           '', (row['rev'] or 0) - (row['disc'] or 0)])
    return response
