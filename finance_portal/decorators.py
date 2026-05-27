from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def finance_manager_required(view_func):
    """
    Decorator to ensure user is authenticated and is either a finance manager,
    a superadmin, or a Django superuser.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.is_finance_manager:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(
                request,
                "Access Denied: You do not have permission to view this page.",
            )
            return redirect("dashboard")

    return _wrapped_view
