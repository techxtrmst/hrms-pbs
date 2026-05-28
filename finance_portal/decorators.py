from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

# Roles that are always granted finance portal access
_FINANCE_ALLOWED_ROLES = {"FINANCE_MANAGER", "SUPERADMIN"}


def finance_manager_required(view_func):
    """
    Decorator to ensure the user is authenticated and has finance portal access.
    Access is granted if ANY of the following is true:
      1. user.is_finance_manager flag is True  (explicitly granted via admin)
      2. user.role is 'FINANCE_MANAGER'        (role-based assignment)
      3. user.role is 'SUPERADMIN'             (platform superadmins)
      4. user.is_superuser                     (Django superuser)
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        user = request.user
        is_allowed = (
            getattr(user, "is_finance_manager", False)
            or getattr(user, "role", "") in _FINANCE_ALLOWED_ROLES
            or getattr(user, "is_superuser", False)
        )

        if is_allowed:
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            "Access Denied: You do not have permission to view the Finance Portal.",
        )
        return redirect("dashboard")

    return _wrapped_view
