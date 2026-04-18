from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*allowed_roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                raise PermissionDenied("Недостаточно прав для выполнения действия.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
