from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from accounts.models import User


def superadmin_required(view_func):
    """
    Decorator to ensure only SuperAdmin users can access the view
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access this page.")
            return redirect("login")

        if request.user.role != User.Role.SUPERADMIN:
            messages.error(request, "You don't have permission to access this page.")
            return redirect("dashboard")

        return view_func(request, *args, **kwargs)

    return wrapper


def company_context_optional(view_func):
    """
    Decorator that adds company context to the view if selected
    Adds 'selected_company' and 'selected_company_id' to kwargs
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from companies.models import Company

        selected_company_id = request.session.get("selected_company_id", None)
        selected_company = None

        if selected_company_id:
            try:
                selected_company = Company.objects.get(id=selected_company_id)
            except Company.DoesNotExist:
                # Clear invalid session data
                request.session.pop("selected_company_id", None)

        kwargs["selected_company"] = selected_company
        kwargs["selected_company_id"] = selected_company_id

        return view_func(request, *args, **kwargs)

    return wrapper
