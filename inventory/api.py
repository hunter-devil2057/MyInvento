from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from inventory.models import StockLevel, Warehouse
from decimal import Decimal


@login_required
def warehouse_stock_api_view(request, warehouse_id):
    try:
        warehouse = Warehouse.objects.get(pk=warehouse_id)
    except Warehouse.DoesNotExist:
        return JsonResponse({'error': 'Warehouse not found'}, status=404)

    stock_levels = StockLevel.objects.select_related(
        'product', 'variant', 'product__category'
    ).filter(
        warehouse=warehouse,
        product__is_active=True,
        quantity_on_hand__gt=0
    ).order_by('product__name')

    stock_data = []
    for sl in stock_levels:
        p = sl.product
        img = ''
        pi = p.images.filter(is_primary=True).first() or p.images.first()
        if pi and pi.image:
            img = pi.image.url
        elif p.image_url:
            img = p.image_url

        stock_data.append({
            'product_id': p.id,
            'product_name': p.name,
            'product_sku': p.sku,
            'description': (p.description[:120] + '...') if len(p.description) > 120 else p.description,
            'full_description': p.description,
            'category': p.category.name if p.category else 'Uncategorized',
            'category_id': p.category_id,
            'unit_of_measure': p.unit_of_measure,
            'cost_price': str(p.cost_price),
            'sale_price': str(p.sale_price),
            'tax_class': p.tax_class,
            'quantity': sl.quantity_on_hand,
            'quantity_reserved': sl.quantity_reserved,
            'available_quantity': sl.available_quantity,
            'total_cost_value': str(Decimal(str(sl.quantity_on_hand)) * p.cost_price),
            'total_sale_value': str(Decimal(str(sl.quantity_on_hand)) * p.sale_price),
            'image_url': img,
            'variant_id': sl.variant_id,
            'variant_name': sl.variant.__str__() if sl.variant else None,
            'track_batches': p.track_batches,
            'track_serials': p.track_serials,
        })

    total_cost = sum(Decimal(s['total_cost_value']) for s in stock_data)
    total_sale = sum(Decimal(s['total_sale_value']) for s in stock_data)
    total_units = sum(s['quantity'] for s in stock_data)

    return JsonResponse({
        'warehouse': {
            'id': warehouse.id,
            'name': warehouse.name,
        },
        'summary': {
            'total_products': len(stock_data),
            'total_units': total_units,
            'total_cost_value': str(total_cost),
            'total_sale_value': str(total_sale),
        },
        'stock': stock_data,
    })
