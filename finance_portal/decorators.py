from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

# Roles with FULL finance portal access (same as Finance Manager)
_FINANCE_FULL_ACCESS_ROLES = {"FINANCE_MANAGER", "SUPERADMIN", "COMPANY_ADMIN"}

# Roles with READ-ONLY + limited access (can only view + submit purchase requests)
_FINANCE_READONLY_ROLES = {"TECH_SUPPORT"}


def finance_manager_required(view_func):
    """
    Decorator to ensure the user is authenticated and has finance portal access.

    FULL ACCESS granted if ANY of the following is true:
      1. user.is_finance_manager flag is True  (explicitly granted via admin)
      2. user.role is 'FINANCE_MANAGER'        (role-based assignment)
      3. user.role is 'SUPERADMIN'             (platform superadmins)
      4. user.role is 'COMPANY_ADMIN'          (company admins — full access)
      5. user.is_superuser                     (Django superuser)

    READ-ONLY ACCESS granted if:
      6. user.role is 'TECH_SUPPORT'           (view-only + can submit purchase requests)
         → request.is_finance_readonly = True is injected for template checks
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        user = request.user
        user_role = getattr(user, "role", "")

        is_full_access = (
            getattr(user, "is_finance_manager", False)
            or user_role in _FINANCE_FULL_ACCESS_ROLES
            or getattr(user, "is_superuser", False)
        )
        is_readonly_access = user_role in _FINANCE_READONLY_ROLES

        if is_full_access:
            request.is_finance_readonly = False
            return view_func(request, *args, **kwargs)

        if is_readonly_access:
            request.is_finance_readonly = True
            return view_func(request, *args, **kwargs)

        messages.error(
            request,
            "Access Denied: You do not have permission to view the Finance Portal.",
        )
        return redirect("dashboard")

    return _wrapped_view
