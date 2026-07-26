from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F, Avg, DecimalField
from django.db.models.functions import Coalesce, TruncDate
from django.db import models
from catalog.models import Product, Category
from sales.models import Customer, SalesTransaction, SalesTransactionLine
from suppliers.models import Supplier
from inventory.models import StockLevel, StockMovement
from purchasing.models import PurchaseOrder, PurchaseOrderLine
from notifications.models import Alert
from .serializers import (ProductSerializer, CustomerSerializer,
                          SupplierSerializer, TransactionSerializer,
                          StockLevelSerializer)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.filter(is_active=True)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = SalesTransaction.objects.exclude(status='Draft')
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]


class StockLevelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockLevel.objects.select_related('product', 'warehouse', 'variant')
    serializer_class = StockLevelSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api_view(request):
    from datetime import timedelta
    from django.utils import timezone
    now = timezone.now()
    days = int(request.GET.get('days', 30))
    since = now - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    try:
        from accounts.models import SystemSettings
        threshold = SystemSettings.objects.first().low_stock_threshold
    except Exception:
        threshold = 10

    total_stock_value = StockLevel.objects.filter(
        product__is_active=True
    ).aggregate(
        total=Sum(F('quantity_on_hand') * F('product__sale_price'), output_field=DecimalField())
    )['total'] or 0

    low_stock_count = StockLevel.objects.filter(
        product__is_active=True, quantity_on_hand__lte=threshold
    ).count()

    pending_pos = PurchaseOrder.objects.filter(status__in=('Draft', 'Sent')).count()
    pending_sales = SalesTransaction.objects.filter(status='Draft').count()

    recent_sales = SalesTransaction.objects.filter(
        status='Completed', completed_at__gte=since
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    recent_sales_count = SalesTransaction.objects.filter(
        status='Completed', completed_at__gte=since
    ).count()

    top_products = list(SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__gte=since
    ).values('product__name').annotate(
        total_qty=Sum('quantity'), total_revenue=Sum('subtotal')
    ).order_by('-total_revenue')[:10])

    recent_transactions = list(SalesTransaction.objects.select_related(
        'customer'
    ).exclude(status='Draft').order_by('-created_at')[:10].values(
        'id', 'invoice_number', 'customer__name', 'grand_total', 'status', 'completed_at'
    ))

    product_count = Product.objects.filter(is_active=True).count()
    category_count = Category.objects.count()
    customer_count = Customer.objects.filter(is_active=True).count()
    supplier_count = Supplier.objects.filter(is_active=True).count()

    from sales.models import Return
    pending_returns = Return.objects.filter(status='Requested').count()
    unresolved_alerts = Alert.objects.filter(is_resolved=False).count()

    # Sales trend (daily for the period)
    sales_trend = SalesTransaction.objects.filter(
        status='Completed', completed_at__gte=since
    ).annotate(
        date=TruncDate('completed_at')
    ).values('date').annotate(
        total=Sum('grand_total')
    ).order_by('date')

    # Stock movement summary
    stock_movements = StockMovement.objects.filter(
        created_at__gte=since
    ).values('movement_type').annotate(
        count=Count('id')
    )

    # Stock by category (rich data)
    stock_by_category = list(StockLevel.objects.filter(
        product__is_active=True
    ).values('product__category__name').annotate(
        total=Sum(F('quantity_on_hand') * F('product__sale_price'), output_field=DecimalField()),
        product_count=Count('product_id', distinct=True),
        total_units=Sum('quantity_on_hand'),
        avg_price=Avg('product__sale_price'),
    ).order_by('-total')[:10])

    # === NEW DASHBOARD DATA ===

    # 1. Purchase cost in period (cost of goods received)
    purchase_cost = PurchaseOrderLine.objects.filter(
        po__status__in=('Received', 'Closed', 'Partially Received'),
        po__created_at__gte=since,
    ).aggregate(
        total=Sum(F('quantity_received') * F('unit_cost'), output_field=DecimalField())
    )['total'] or 0

    # 2. Sales by category (revenue distribution)
    sales_by_category = list(SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__gte=since,
        product__category__isnull=False
    ).values('product__category__name').annotate(
        total_revenue=Sum('subtotal'),
        total_quantity=Sum('quantity'),
    ).order_by('-total_revenue')[:10])

    # 3. Top customers
    top_customers = list(SalesTransaction.objects.filter(
        status='Completed',
        completed_at__gte=since,
        customer__isnull=False
    ).values('customer__name').annotate(
        total_spent=Sum('grand_total'),
        transaction_count=Count('id'),
    ).order_by('-total_spent')[:10])

    # 4. Stock health (per warehouse, uses reorder_min if available else 10)
    sl_all = StockLevel.objects.filter(product__is_active=True).annotate(
        thr=Coalesce('reorder_min', 10)
    )
    out_of_stock = sl_all.filter(quantity_on_hand=0).count()
    low_stk = sl_all.filter(quantity_on_hand__gte=1, quantity_on_hand__lte=F('thr')).count()
    healthy = sl_all.filter(quantity_on_hand__gt=F('thr')).count()
    stock_health = {'out_of_stock': out_of_stock, 'low_stock': low_stk, 'healthy': healthy}

    # 5. Profit margin by category
    profit_by_category = list(SalesTransactionLine.objects.filter(
        transaction__status='Completed',
        transaction__completed_at__gte=since,
        product__category__isnull=False,
        product__cost_price__gt=0,
    ).values('product__category__name').annotate(
        revenue=Sum('subtotal'),
        cost=Sum(F('quantity') * F('product__cost_price'), output_field=DecimalField()),
    ).order_by('-revenue')[:10])

    # 6. Previous period sales (for growth comparison)
    previous_sales = SalesTransaction.objects.filter(
        status='Completed',
        completed_at__gte=prev_since,
        completed_at__lt=since,
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    # 7. Daily purchase cost trend (for cash-flow chart)
    purchase_trend = PurchaseOrderLine.objects.filter(
        po__status__in=('Received', 'Closed', 'Partially Received'),
        po__created_at__gte=since,
    ).annotate(
        date=TruncDate('po__created_at')
    ).values('date').annotate(
        total=Sum(F('quantity_received') * F('unit_cost'), output_field=DecimalField())
    ).order_by('date')

    return Response({
        'total_stock_value': float(total_stock_value),
        'low_stock_count': low_stock_count,
        'pending_pos': pending_pos,
        'pending_sales': pending_sales,
        'recent_sales': float(recent_sales),
        'recent_sales_count': recent_sales_count,
        'top_products': top_products,
        'recent_transactions': recent_transactions,
        'product_count': product_count,
        'category_count': category_count,
        'customer_count': customer_count,
        'supplier_count': supplier_count,
        'pending_returns': pending_returns,
        'unresolved_alerts': unresolved_alerts,
        'sales_trend': list(sales_trend),
        'stock_movements': {m['movement_type']: m['count'] for m in stock_movements},
        'stock_by_category': stock_by_category,
        # New fields
        'purchase_cost': float(purchase_cost),
        'sales_by_category': sales_by_category,
        'top_customers': top_customers,
        'stock_health': stock_health,
        'profit_by_category': profit_by_category,
        'previous_sales': float(previous_sales),
        'purchase_trend': list(purchase_trend),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_search_api_view(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return Response([])
    products = Product.objects.filter(
        is_active=True
    ).filter(
        Q(name__icontains=query) | Q(sku__icontains=query)
    )[:20]
    data = []
    for p in products:
        stock = p.stock_levels.aggregate(total=Sum('quantity_on_hand'))['total'] or 0
        data.append({
            'id': p.id, 'name': p.name, 'sku': p.sku,
            'price': str(p.sale_price), 'stock': stock,
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pos_products_api_view(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    products = Product.objects.filter(is_active=True).select_related('category')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    if category_id:
        products = products.filter(category_id=category_id)
    data = []
    for p in products[:60]:
        stock = p.stock_levels.aggregate(total=Sum('quantity_on_hand'))['total'] or 0
        img = ''
        pi = p.images.filter(is_primary=True).first() or p.images.first()
        if pi and pi.image:
            img = pi.image.url
        elif p.image_url:
            img = p.image_url
        data.append({
            'id': p.id, 'name': p.name, 'sku': p.sku,
            'price': str(p.sale_price), 'stock': stock,
            'image': img,
            'category': p.category.name if p.category else '',
            'category_id': p.category_id,
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pos_categories_api_view(request):
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0).order_by('name')
    data = [{'id': c.id, 'name': c.name, 'count': c.product_count} for c in categories]
    return Response(data)
