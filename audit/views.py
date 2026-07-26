from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import AuditLog


@login_required
def audit_log_view(request):
    query = request.GET.get('q', '')
    action_filter = request.GET.get('action', '')
    logs = AuditLog.objects.select_related('user').all()
    if query:
        logs = logs.filter(
            Q(model_name__icontains=query) |
            Q(object_repr__icontains=query) |
            Q(user__username__icontains=query)
        )
    if action_filter:
        logs = logs.filter(action=action_filter)
    paginator = Paginator(logs, 30)
    page = request.GET.get('page', 1)
    logs_page = paginator.get_page(page)
    return render(request, 'audit/audit_log.html', {
        'logs': logs_page, 'query': query, 'selected_action': action_filter,
    })
