from .models import Notification


def notification_count(request):
    """
    Context processor to add unread notification count to all templates
    """
    from accounts.models import User
    from .models import Notification

    # Only allow managers, admins, and HR department users
    emp = getattr(request.user, "employee_profile", None)
    is_hr = emp and str(getattr(emp, "department", "")).upper() == "HR"

    if request.user.is_authenticated and (request.user.role in [User.Role.COMPANY_ADMIN, User.Role.MANAGER] or is_hr):
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

        return {"unread_notification_count": unread_count}

    return {"unread_notification_count": 0}
