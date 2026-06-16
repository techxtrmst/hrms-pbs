from .models import Notification


def notification_count(request):
    """
    Context processor to add unread notification count to all templates
    """
    from accounts.models import User
    from finance_portal.models import PurchaseRequest

    context = {
        "unread_notification_count": 0,
        "pending_purchase_requests_count": 0,
    }

    if not request.user.is_authenticated:
        return context

    # Only allow managers, admins, and HR department users
    emp = getattr(request.user, "employee_profile", None)
    is_hr = emp and str(getattr(emp, "department", "")).upper() == "HR"

    if request.user.role in [User.Role.COMPANY_ADMIN, User.Role.MANAGER] or is_hr:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        context["unread_notification_count"] = unread_count

    # Check for superadmin or is_superuser to get pending purchase requests
    if request.user.role == "SUPERADMIN" or request.user.is_superuser:
        pending_qs = PurchaseRequest.objects.filter(status="pending")
        pending_count = pending_qs.count()

        if hasattr(request, "session"):
            current_path = request.path
            if "finance/purchases" in current_path:
                request.session["purchases_last_seen_count"] = pending_count
                request.session.modified = True
                context["pending_purchase_requests_count"] = 0
            else:
                last_seen_count = request.session.get("purchases_last_seen_count", 0)
                if pending_count != last_seen_count:
                    if pending_count > last_seen_count:
                        context["pending_purchase_requests_count"] = pending_count - last_seen_count
                    else:
                        request.session["purchases_last_seen_count"] = pending_count
                        request.session.modified = True
                        context["pending_purchase_requests_count"] = 0
                else:
                    context["pending_purchase_requests_count"] = 0
        else:
            context["pending_purchase_requests_count"] = pending_count

    return context


def google_maps_api_key(request):
    """Expose GOOGLE_MAPS_API_KEY to all templates."""
    from django.conf import settings

    return {
        "GOOGLE_MAPS_API_KEY": getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
    }
