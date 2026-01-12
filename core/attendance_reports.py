from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import models
from datetime import timedelta
from employees.models import Attendance
from accounts.models import User


@login_required
def attendance_late_early_report(request):
    """Report showing employees who arrived late or left early"""
    if request.user.role not in [User.Role.COMPANY_ADMIN, User.Role.MANAGER]:
        from django.contrib import messages

        messages.error(request, "You do not have permission to view this report.")
        from django.shortcuts import redirect

        return redirect("dashboard")

    # Get date range from request or default to last 7 days
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=7)

    if request.GET.get("start_date"):
        from datetime import datetime

        start_date = datetime.strptime(request.GET.get("start_date"), "%Y-%m-%d").date()
    if request.GET.get("end_date"):
        from datetime import datetime

        end_date = datetime.strptime(request.GET.get("end_date"), "%Y-%m-%d").date()

    # Filter attendance records
    attendance_query = Attendance.objects.filter(
        date__range=[start_date, end_date], employee__company=request.user.company
    ).select_related("employee", "employee__user", "employee__shift_schedule")

    # Filter by manager if user is a manager
    if request.user.role == User.Role.MANAGER:
        attendance_query = attendance_query.filter(
            employee__manager=request.user.employee_profile
        )

    # Get late arrivals
    late_arrivals = attendance_query.filter(is_late=True).order_by(
        "-date", "-late_by_minutes"
    )

    # Get early departures
    early_departures = attendance_query.filter(is_early_departure=True).order_by(
        "-date", "-early_departure_minutes"
    )

    # Statistics
    total_late = late_arrivals.count()
    total_early = early_departures.count()
    avg_late_minutes = (
        late_arrivals.aggregate(avg=models.Avg("late_by_minutes"))["avg"] or 0
    )
    avg_early_minutes = (
        early_departures.aggregate(avg=models.Avg("early_departure_minutes"))["avg"]
        or 0
    )

    # Top offenders
    from django.db.models import Count, Sum

    late_offenders = (
        late_arrivals.values(
            "employee__id",
            "employee__user__first_name",
            "employee__user__last_name",
            "employee__badge_id",
        )
        .annotate(late_count=Count("id"), total_late_minutes=Sum("late_by_minutes"))
        .order_by("-late_count")[:10]
    )

    early_offenders = (
        early_departures.values(
            "employee__id",
            "employee__user__first_name",
            "employee__user__last_name",
            "employee__badge_id",
        )
        .annotate(
            early_count=Count("id"), total_early_minutes=Sum("early_departure_minutes")
        )
        .order_by("-early_count")[:10]
    )

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "late_arrivals": late_arrivals[:50],  # Limit to 50 for performance
        "early_departures": early_departures[:50],
        "total_late": total_late,
        "total_early": total_early,
        "avg_late_minutes": round(avg_late_minutes, 1),
        "avg_early_minutes": round(avg_early_minutes, 1),
        "late_offenders": late_offenders,
        "early_offenders": early_offenders,
    }

    return render(request, "core/attendance_late_early_report.html", context)
