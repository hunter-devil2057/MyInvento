from .models import AuditLog


def log_action(user, action, model_name, object_id=None, object_repr='', before_json=None, after_json=None, ip_address=None):
    AuditLog.objects.create(
        user=user, action=action, model_name=model_name,
        object_id=object_id, object_repr=object_repr,
        before_json=before_json, after_json=after_json,
        ip_address=ip_address,
    )
