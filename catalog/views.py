from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from .models import Product, ProductVariant, ProductImage, Category, Batch
from .forms import ProductForm, CategoryForm, ProductVariantForm, ProductImageFormSet
from inventory.models import StockLevel, Warehouse, StockMovement
from audit.utils import log_action


@login_required
def product_list_view(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')
    products = Product.objects.select_related('category').prefetch_related('images', 'variants').all()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query))
    if category_id:
        products = products.filter(category_id=category_id)
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)
    paginator = Paginator(products, 20)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)
    categories = Category.objects.all()
    return render(request, 'catalog/product_list.html', {
        'products': products_page,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'selected_status': status,
    })


def _build_stock_forms(warehouses, product=None):
    forms_list = []
    for w in warehouses:
        qty = 0
        if product:
            sl = StockLevel.objects.filter(product=product, warehouse=w, variant=None).first()
            if sl:
                qty = sl.quantity_on_hand
        forms_list.append({
            'warehouse_id': w.pk,
            'warehouse_name': w.name,
            'quantity': qty,
        })
    return forms_list


@login_required
def product_create_view(request):
    warehouses = Warehouse.objects.filter(is_active=True)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            primary_file = form.cleaned_data.get('primary_image_file')
            if primary_file:
                ProductImage.objects.create(product=product, image=primary_file, is_primary=True, order=0)
            image_formset = ProductImageFormSet(request.POST, request.FILES, prefix='images', instance=product)
            if image_formset.is_valid():
                image_formset.save()
            for w in warehouses:
                qty_str = request.POST.get(f'stock_{w.pk}', '0')
                try:
                    qty = int(qty_str)
                except (ValueError, TypeError):
                    qty = 0
                if qty < 0:
                    qty = 0
                sl, created = StockLevel.objects.get_or_create(
                    product=product, variant=None, warehouse=w,
                    defaults={'quantity_on_hand': qty}
                )
                if not created and qty != sl.quantity_on_hand:
                    sl.quantity_on_hand = qty
                    sl.save()
                if qty > 0:
                    StockMovement.objects.create(
                        product=product, warehouse=w,
                        movement_type='ADJUSTMENT', quantity_delta=qty,
                        user=request.user, notes='Initial stock on product creation',
                    )
            log_action(request.user, 'Create', 'Product', product.pk, f'Created product: {product.name}')
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Product Created: {product.name}',
                body=f'New product "{product.name}" (SKU: {product.sku}, category: {product.category.name if product.category else "Uncategorized"}, cost: Rs. {product.cost_price:,.2f}, sale price: Rs. {product.sale_price:,.2f}) created by {request.user.username}.',
                link=f'/catalog/{product.uuid}/',
            )
            messages.success(request, f'Product "{product.name}" created successfully.')
            return redirect('product_detail', uuid=product.uuid)
    else:
        form = ProductForm()
        image_formset = ProductImageFormSet(prefix='images')
    stock_forms = _build_stock_forms(warehouses)
    return render(request, 'catalog/product_form.html', {
        'form': form,
        'image_formset': image_formset,
        'stock_forms': stock_forms,
        'title': 'Create Product',
        'editing': False,
    })


@login_required
def product_detail_view(request, uuid):
    product = get_object_or_404(Product.objects.select_related('category'), uuid=uuid)
    stock_levels = StockLevel.objects.filter(product=product).select_related('warehouse')
    total_stock = stock_levels.aggregate(total=Sum('quantity_on_hand'))['total'] or 0
    images = product.images.all()
    variants = product.variants.all()
    batches = product.batches.all()
    recent_movements = product.stock_movements.select_related('warehouse', 'user')[:10]
    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'stock_levels': stock_levels,
        'total_stock': total_stock,
        'images': images,
        'variants': variants,
        'batches': batches,
        'recent_movements': recent_movements,
    })


@login_required
def product_edit_view(request, uuid):
    product = get_object_or_404(Product, uuid=uuid)
    warehouses = Warehouse.objects.filter(is_active=True)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            primary_file = form.cleaned_data.get('primary_image_file')
            if primary_file:
                ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)
                ProductImage.objects.create(product=product, image=primary_file, is_primary=True, order=0)
            image_formset = ProductImageFormSet(request.POST, request.FILES, prefix='images', instance=product)
            if image_formset.is_valid():
                image_formset.save()
            for w in warehouses:
                qty_str = request.POST.get(f'stock_{w.pk}')
                if qty_str is None:
                    continue
                try:
                    new_qty = int(qty_str)
                except (ValueError, TypeError):
                    continue
                if new_qty < 0:
                    new_qty = 0
                sl, created = StockLevel.objects.get_or_create(
                    product=product, variant=None, warehouse=w,
                    defaults={'quantity_on_hand': new_qty}
                )
                if not created:
                    old_qty = sl.quantity_on_hand
                    if new_qty != old_qty:
                        delta = new_qty - old_qty
                        sl.quantity_on_hand = new_qty
                        sl.save()
                        StockMovement.objects.create(
                            product=product, warehouse=w,
                            movement_type='ADJUSTMENT', quantity_delta=delta,
                            user=request.user, notes=f'Stock updated from product edit ({old_qty} -> {new_qty})',
                        )
                elif new_qty > 0:
                    StockMovement.objects.create(
                        product=product, warehouse=w,
                        movement_type='ADJUSTMENT', quantity_delta=new_qty,
                        user=request.user, notes='Initial stock on product edit',
                    )
            log_action(request.user, 'Update', 'Product', product.pk, f'Updated product: {product.name}')
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Product Updated: {product.name}',
                body=f'Product "{product.name}" (SKU: {product.sku}, category: {product.category.name if product.category else "Uncategorized"}, sale price: Rs. {product.sale_price:,.2f}) updated by {request.user.username}.',
                link=f'/catalog/{product.uuid}/',
            )
            messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('product_detail', uuid=product.uuid)
    else:
        form = ProductForm(instance=product)
        image_formset = ProductImageFormSet(prefix='images', instance=product)
    stock_forms = _build_stock_forms(warehouses, product)
    return render(request, 'catalog/product_form.html', {
        'form': form,
        'image_formset': image_formset,
        'stock_forms': stock_forms,
        'title': f'Edit: {product.name}',
        'editing': True,
        'product': product,
    })


@login_required
def product_delete_view(request, uuid):
    product = get_object_or_404(Product, uuid=uuid)
    if request.method == 'POST':
        product.is_active = False
        product.save()
        log_action(request.user, 'Update', 'Product', product.pk, f'Archived product: {product.name}')
        from notifications.utils import notify_admins
        notify_admins(
            title=f'Product Archived',
            body=f'Product "{product.name}" (SKU: {product.sku}) archived by {request.user.username}.',
            link='/catalog/',
        )
        messages.success(request, f'Product "{product.name}" has been archived.')
        return redirect('product_list')
    return render(request, 'catalog/product_confirm_delete.html', {'product': product})


@login_required
def category_list_view(request):
    categories = Category.objects.annotate(product_count=Count('products', distinct=True)).all()
    paginator = Paginator(categories, 20)
    page = request.GET.get('page', 1)
    categories_page = paginator.get_page(page)
    return render(request, 'catalog/category_list.html', {'categories': categories_page})


@login_required
def category_create_view(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            log_action(request.user, 'Create', 'Category', category.pk, f'Created category: {category.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Category Created: {category.name}',
                body=f'New category "{category.name}" created by {request.user.username}. Products in category: {category.products.count()}. UUID: {category.uuid}',
                link='/catalog/categories/',
            )
            messages.success(request, f'Category "{category.name}" created.')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'catalog/category_form.html', {'form': form, 'title': 'Create Category'})


@login_required
def category_edit_view(request, uuid):
    category = get_object_or_404(Category, uuid=uuid)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            log_action(request.user, 'Update', 'Category', category.pk, f'Updated category: {category.name}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Category Updated: {category.name}',
                body=f'Category "{category.name}" updated by {request.user.username}. Products in category: {category.products.count()}. UUID: {category.uuid}',
                link='/catalog/categories/',
            )
            messages.success(request, f'Category "{category.name}" updated.')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'catalog/category_form.html', {'form': form, 'title': f'Edit: {category.name}'})


@login_required
def category_delete_view(request, uuid):
    category = get_object_or_404(Category, uuid=uuid)
    if request.method == 'POST':
        if category.products.exists():
            messages.error(request, 'Cannot delete category with linked products. Reassign them first.')
            return redirect('category_list')
        category.delete()
        log_action(request.user, 'Delete', 'Category', category.pk, f'Deleted category: {category.name}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title='Category Deleted',
            body=f'Category "{category.name}" deleted by {request.user.username}.',
            link='/catalog/categories/',
        )
        messages.success(request, f'Category "{category.name}" deleted.')
        return redirect('category_list')
    return render(request, 'catalog/category_confirm_delete.html', {'category': category})


@login_required
def variant_create_view(request, product_uuid):
    product = get_object_or_404(Product, uuid=product_uuid)
    if request.method == 'POST':
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product
            variant.save()
            log_action(request.user, 'Create', 'ProductVariant', variant.pk, f'Created variant: {variant}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Variant Created: {variant.product.name}',
                body=f'New variant created for "{variant.product.name}" (SKU: {variant.sku}, attributes: {variant.attributes}, sale price: Rs. {variant.effective_sale_price:,.2f}) by {request.user.username}.',
                link=f'/catalog/{variant.product.uuid}/',
            )
            messages.success(request, 'Variant created.')
            return redirect('product_detail', uuid=product.uuid)
    else:
        form = ProductVariantForm()
    return render(request, 'catalog/variant_form.html', {'form': form, 'product': product, 'creating': True})


@login_required
def variant_edit_view(request, uuid):
    variant = get_object_or_404(ProductVariant, uuid=uuid)
    if request.method == 'POST':
        form = ProductVariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            log_action(request.user, 'Update', 'ProductVariant', variant.pk, f'Updated variant: {variant}', ip_address=request.META.get('REMOTE_ADDR'))
            from notifications.utils import notify_admins
            notify_admins(
                title=f'Variant Updated: {variant.product.name}',
                body=f'Variant updated for "{variant.product.name}" (SKU: {variant.sku}, attributes: {variant.attributes}, sale price: Rs. {variant.effective_sale_price:,.2f}) by {request.user.username}.',
                link=f'/catalog/{variant.product.uuid}/',
            )
            messages.success(request, 'Variant updated.')
            return redirect('product_detail', uuid=variant.product.uuid)
    else:
        form = ProductVariantForm(instance=variant)
    return render(request, 'catalog/variant_form.html', {'form': form, 'variant': variant})


@login_required
def variant_delete_view(request, uuid):
    variant = get_object_or_404(ProductVariant, uuid=uuid)
    if request.method == 'POST':
        parent_product = variant.product
        variant_name = str(variant)
        variant_sku = variant.sku
        variant.delete()
        log_action(request.user, 'Delete', 'ProductVariant', variant.pk, f'Deleted variant: {variant}', ip_address=request.META.get('REMOTE_ADDR'))
        from notifications.utils import notify_admins
        notify_admins(
            title=f'Variant Deleted: {parent_product.name}',
                body=f'Variant "{variant_name}" (SKU: {variant_sku}) deleted from product "{parent_product.name}" (SKU: {parent_product.sku}) by {request.user.username}.',
                link=f'/catalog/{parent_product.uuid}/',
        )
        messages.success(request, 'Variant deleted.')
        return redirect('product_detail', uuid=variant.product.uuid)
    return render(request, 'catalog/variant_confirm_delete.html', {'variant': variant})


@login_required
def product_api_list(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(is_active=True)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    data = []
    for p in products[:50]:
        stock = p.stock_levels.aggregate(total=Sum('quantity_on_hand'))['total'] or 0
        img_url = ''
        if p.primary_image and p.primary_image.image:
            try:
                img_url = p.primary_image.image.url
            except Exception:
                pass
        if not img_url and p.image_url:
            img_url = p.image_url
        data.append({
            'id': str(p.uuid),
            'name': p.name,
            'sku': p.sku,
            'sale_price': str(p.sale_price),
            'stock': stock,
            'primary_image': img_url,
        })
    return JsonResponse({'products': data})


@login_required
def product_image_upload_view(request, uuid):
    product = get_object_or_404(Product, uuid=uuid)
    if request.method == 'POST' and request.FILES.get('image'):
        img_file = request.FILES['image']
        is_primary = not product.images.exists()
        ProductImage.objects.create(product=product, image=img_file, is_primary=is_primary, order=product.images.count())
        log_action(request.user, 'Update', 'Product', product.pk, f'Uploaded image for: {product.name}')
        messages.success(request, 'Image uploaded successfully.')
    return redirect('product_detail', uuid=product.uuid)
