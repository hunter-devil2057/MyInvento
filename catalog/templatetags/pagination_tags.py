from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def smart_pagination(context, page_obj, param_name='page', **extra_params):
    """
    Renders smart pagination with page numbers: 1 ... 4 5 6 ... 20
    Usage: {% smart_pagination products 'page' category=selected_category %}
    """
    paginator = page_obj.paginator
    current = page_obj.number
    total = paginator.num_pages

    if total <= 1:
        return ''

    # Build query string from extra_params (exclude empty values)
    query_parts = []
    for key, value in extra_params.items():
        if value is not None and value != '':
            query_parts.append(f'{key}={value}')
    query_suffix = ('&' + '&'.join(query_parts)) if query_parts else ''

    # Determine which page numbers to show
    pages = set()
    pages.add(1)
    pages.add(total)
    for i in range(max(1, current - 2), min(total, current + 2) + 1):
        pages.add(i)

    sorted_pages = sorted(pages)

    # Build the page number elements
    elements = []

    # Previous button
    if page_obj.has_previous():
        elements.append(f'<a href="?{param_name}={page_obj.previous_page_number()}{query_suffix}" class="page-btn page-prev" title="Previous page">&#8592;</a>')
    else:
        elements.append('<span class="page-btn page-disabled">&#8592;</span>')

    # Page numbers with ellipsis
    last_shown = 0
    for p in sorted_pages:
        if p - last_shown > 1:
            elements.append('<span class="page-ellipsis">&hellip;</span>')
        if p == current:
            elements.append(f'<span class="page-btn page-current">{p}</span>')
        else:
            elements.append(f'<a href="?{param_name}={p}{query_suffix}" class="page-btn">{p}</a>')
        last_shown = p

    # Next button
    if page_obj.has_next():
        elements.append(f'<a href="?{param_name}={page_obj.next_page_number()}{query_suffix}" class="page-btn page-next" title="Next page">&#8594;</a>')
    else:
        elements.append('<span class="page-btn page-disabled">&#8594;</span>')

    html = '<nav class="pagination" aria-label="Page navigation">' + ''.join(elements) + '</nav>'
    return mark_safe(html)
