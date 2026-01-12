from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from accounts.models import User


def role_required(allowed_roles):
    """
    Decorator to ensure user has one of the required roles.
    allowed_roles: List of User.Role values (e.g. [User.Role.MANAGER, User.Role.COMPANY_ADMIN])
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")

            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(
                    request,
                    "Access Denied: You do not have permission to view this page.",
                )
                return redirect("dashboard")

        return _wrapped_view

    return decorator


def manager_required(view_func):
    """Decorator for Manager or Company Admin access"""
    return role_required([User.Role.MANAGER, User.Role.COMPANY_ADMIN])(view_func)


def admin_required(view_func):
    """Decorator for Company Admin access only"""
    return role_required([User.Role.COMPANY_ADMIN])(view_func)
