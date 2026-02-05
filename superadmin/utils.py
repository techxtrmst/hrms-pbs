import json
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from companies.models import Company
from employees.models import Attendance, Employee, LeaveBalance, LeaveRequest


def get_company_context(request):
    """
    Get the selected company from session or return None for global view
    """
    company_id = request.session.get("selected_company_id", None)
    if company_id:
        try:
            return Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            request.session.pop("selected_company_id", None)
    return None


def filter_by_company(queryset, company_id=None):
    """
    Filter queryset by company_id if provided
    """
    if company_id:
        return queryset.filter(company_id=company_id)
    return queryset


def get_dashboard_metrics(company_id=None):
    """
    Calculate dashboard metrics for SuperAdmin
    Returns dict with total_companies, total_employees, present_today, on_leave_today
    """
    today = timezone.localtime().date()

    # Total Companies (always global)
    total_companies = Company.objects.filter(is_active=True).count()

    # Total Employees (filtered by company if selected)
    employees_qs = Employee.objects.all()
    if company_id:
        employees_qs = employees_qs.filter(company_id=company_id)
    total_employees = employees_qs.count()

    # Present Today (filtered by company if selected)
    attendance_qs = Attendance.objects.filter(date=today, status="PRESENT")
    if company_id:
        attendance_qs = attendance_qs.filter(employee__company_id=company_id)
    present_today = attendance_qs.count()

    # On Leave Today (filtered by company if selected)
    leave_qs = LeaveRequest.objects.filter(start_date__lte=today, end_date__gte=today, status="APPROVED")
    if company_id:
        leave_qs = leave_qs.filter(employee__company_id=company_id)
    on_leave_today = leave_qs.count()

    return {
        "total_companies": total_companies,
        "total_employees": total_employees,
        "present_today": present_today,
        "on_leave_today": on_leave_today,
    }


def get_attendance_today_data(company_id=None):
    """
    Get detailed attendance data for today
    """
    today = timezone.localtime().date()

    attendance_qs = (
        Attendance.objects.filter(date=today, status="PRESENT")
        .select_related("employee__user", "employee__company", "employee__assigned_shift")
        .order_by("-clock_in")
    )

    if company_id:
        attendance_qs = attendance_qs.filter(employee__company_id=company_id)

    return attendance_qs


def get_leaves_today_data(company_id=None):
    """
    Get approved leaves for today
    """
    today = timezone.localtime().date()

    leave_qs = (
        LeaveRequest.objects.filter(start_date__lte=today, end_date__gte=today, status="APPROVED")
        .select_related("employee__user", "employee__company")
        .order_by("-start_date")
    )

    if company_id:
        leave_qs = leave_qs.filter(employee__company_id=company_id)

    return leave_qs


def get_employee_lifecycle_data(company_id):
    """
    Get employee lifecycle analytics for a specific company
    Returns list of dicts with employee stats
    """

    employees = (
        Employee.objects.filter(company_id=company_id)
        .select_related("user")
        .prefetch_related("attendances", "leave_requests")
    )

    result = []
    for emp in employees:
        # Calculate working days
        working_days = emp.attendances.filter(status__in=["PRESENT", "HALF_DAY", "WFH", "ON_DUTY"]).count()

        # Calculate leaves taken
        leaves_taken = emp.leave_requests.filter(status="APPROVED").count()

        # Calculate LOP days
        lop_days = emp.attendances.filter(status="ABSENT").count()

        # Calculate attendance percentage
        total_days = emp.attendances.count()
        attendance_pct = (working_days / total_days * 100) if total_days > 0 else 0

        result.append(
            {
                "employee": emp,
                "name": emp.user.get_full_name(),
                "join_date": emp.date_of_joining,
                "working_days": working_days,
                "leaves_taken": leaves_taken,
                "lop_days": lop_days,
                "attendance_percentage": round(attendance_pct, 2),
            }
        )

    return result


def get_leave_analytics(company_id, months=None, year=None):
    """
    Get leave analytics for a company.
    If months/year provided, returns specific analytics for that month.
    Else returns default overview (last 6 months).
    """
    import datetime

    from django.db.models.functions import TruncDay, TruncMonth

    # Handle parameter name change
    month = months

    target_date = timezone.localtime().date()
    start_date = target_date - timedelta(days=6 * 30)

    # Filter params for distribution
    dist_filters = {"employee__company_id": company_id, "status": "APPROVED"}

    # Filter params for trends
    trend_filters = {"employee__company_id": company_id, "status": "APPROVED"}

    if month and year:
        # Specific month analysis
        start_date = datetime.date(year, month, 1)
        # Handle end of month logic logic
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime.date(year, month + 1, 1) - timedelta(days=1)

        # For distribution, we count leaves that overlap with this month
        dist_filters["start_date__lte"] = end_date
        dist_filters["end_date__gte"] = start_date

        # For daily trends in this month
        trend_filters["start_date__gte"] = start_date
        trend_filters["start_date__lte"] = end_date
    else:
        # Default 6 month lookback
        dist_filters["start_date__gte"] = start_date
        trend_filters["start_date__gte"] = start_date

    # Leave type distribution
    leave_distribution = (
        LeaveRequest.objects.filter(**dist_filters).values("leave_type").annotate(count=Count("id")).order_by("-count")
    )

    # Trends Analysis
    if month and year:
        # Daily breakdown for selected month
        trends_data = (
            LeaveRequest.objects.filter(**trend_filters)
            .annotate(period=TruncDay("start_date"))
            .values("period", "leave_type")
            .annotate(count=Count("id"))
            .order_by("period")
        )
    else:
        # Monthly breakdown for last 6 months
        trends_data = (
            LeaveRequest.objects.filter(**trend_filters)
            .annotate(period=TruncMonth("start_date"))
            .values("period", "leave_type")
            .annotate(count=Count("id"))
            .order_by("period")
        )

    # Process into chart format
    periods = sorted(list(set(item["period"] for item in trends_data)))
    leave_types = list(set(item["leave_type"] for item in trends_data))

    series = []
    for l_type in leave_types:
        data = []
        for period in periods:
            # Find count for this type and period
            match = next(
                (item for item in trends_data if item["period"] == period and item["leave_type"] == l_type), None
            )
            data.append(match["count"] if match else 0)

        # Map code to display name
        display_name = dict(LeaveRequest.LEAVE_TYPES).get(l_type, l_type)
        series.append({"name": display_name, "data": data})

    chart_data = {"categories": [p.strftime("%Y-%m-%d") for p in periods], "series": series}

    # Frequent leave takers (using same time window)
    frequent_takers = (
        Employee.objects.filter(company_id=company_id)
        .annotate(
            leave_count=Count(
                "leave_requests",
                filter=Q(
                    leave_requests__status="APPROVED",
                    leave_requests__start_date__gte=start_date,
                    # If end date is set (specific month), restrict to that
                    **({"leave_requests__start_date__lte": end_date} if month and year else {}),
                ),
            )
        )
        .filter(leave_count__gt=0)
        .order_by("-leave_count")[:10]
    )

    return {
        "distribution": list(leave_distribution),
        "monthly_trends": chart_data,
        "frequent_takers": frequent_takers,
    }


def get_attendance_heatmap_data(company_id, year=None, month=None):
    """
    Get comprehensive attendance heatmap data for a specific month
    """
    if not year or not month:
        now = timezone.localtime()
        year = now.year
        month = now.month

    # Get all attendance records for the month with daily breakdown
    import calendar
    from datetime import date, timedelta

    # Get first and last day of month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # Get daily attendance data
    daily_attendance = {}
    current_date = first_day

    while current_date <= last_day:
        day_attendance = Attendance.objects.filter(employee__company_id=company_id, date=current_date).aggregate(
            total_records=Count("id"),
            present_count=Count("id", filter=Q(status="PRESENT")),
            absent_count=Count("id", filter=Q(status="ABSENT")),
            late_count=Count("id", filter=Q(is_late=True)),
            early_departure_count=Count("id", filter=Q(is_early_departure=True)),
        )

        # Calculate attendance percentage for the day
        total_employees = Employee.objects.filter(company_id=company_id, is_active=True).count()
        attendance_percentage = (day_attendance["present_count"] / total_employees * 100) if total_employees > 0 else 0

        daily_attendance[current_date.day] = {
            "date": current_date,
            "attendance_percentage": round(attendance_percentage, 1),
            "present_count": day_attendance["present_count"],
            "absent_count": day_attendance["absent_count"],
            "late_count": day_attendance["late_count"],
            "early_departure_count": day_attendance["early_departure_count"],
            "total_employees": total_employees,
        }

        current_date += timedelta(days=1)

    # Calculate overall statistics
    total_employees = Employee.objects.filter(company_id=company_id, is_active=True).count()

    # Monthly totals
    monthly_stats = Attendance.objects.filter(
        employee__company_id=company_id, date__year=year, date__month=month
    ).aggregate(
        total_records=Count("id"),
        present_days=Count("id", filter=Q(status="PRESENT")),
        absent_days=Count("id", filter=Q(status="ABSENT")),
        late_logins=Count("id", filter=Q(is_late=True)),
        early_logouts=Count("id", filter=Q(is_early_departure=True)),
    )

    # Calculate absenteeism percentage
    working_days = len([d for d in daily_attendance.values() if d["date"].weekday() < 5])  # Mon-Fri
    expected_attendance = total_employees * working_days
    absenteeism_pct = (monthly_stats["absent_days"] / expected_attendance * 100) if expected_attendance > 0 else 0

    # Get top late arrivals
    late_arrivals = (
        Employee.objects.filter(company_id=company_id)
        .annotate(
            late_count=Count(
                "attendances",
                filter=Q(attendances__date__year=year, attendances__date__month=month, attendances__is_late=True),
            )
        )
        .filter(late_count__gt=0)
        .order_by("-late_count")[:5]
    )

    # Weekly trends (last 4 weeks)
    weekly_trends = []
    for week in range(4):
        week_start = first_day + timedelta(weeks=week)
        week_end = min(week_start + timedelta(days=6), last_day)

        week_attendance = Attendance.objects.filter(
            employee__company_id=company_id, date__range=[week_start, week_end]
        ).aggregate(present=Count("id", filter=Q(status="PRESENT")), total=Count("id"))

        week_percentage = (
            (week_attendance["present"] / week_attendance["total"] * 100) if week_attendance["total"] > 0 else 0
        )
        weekly_trends.append(round(week_percentage, 1))

    return {
        "daily_attendance": daily_attendance,
        "present_days": monthly_stats["present_days"],
        "late_logins": monthly_stats["late_logins"],
        "early_logouts": monthly_stats["early_logouts"],
        "absenteeism_percentage": round(absenteeism_pct, 2),
        "total_employees": total_employees,
        "late_arrivals": late_arrivals,
        "weekly_trends": weekly_trends,
        "working_days": working_days,
    }


def get_company_summary(company_id):
    """
    Get comprehensive summary for a company
    """
    company = Company.objects.get(id=company_id)

    # Employee counts
    total_employees = Employee.objects.filter(company_id=company_id).count()
    active_employees = Employee.objects.filter(company_id=company_id, user__is_active=True).count()
    inactive_employees = total_employees - active_employees

    # Locations
    locations_count = company.locations.filter(is_active=True).count()

    return {
        "company": company,
        "total_employees": total_employees,
        "active_employees": active_employees,
        "inactive_employees": inactive_employees,
        "locations_count": locations_count,
    }


# ============================================================================
# EMPLOYEE DETAIL ANALYTICS FUNCTIONS
# ============================================================================


def get_employee_detailed_analytics(employee_id):
    """
    Get comprehensive analytics for a single employee
    Returns all data needed for employee detail view
    """
    try:
        employee = Employee.objects.select_related("user", "company", "manager", "assigned_shift", "location").get(
            id=employee_id
        )
    except Employee.DoesNotExist:
        return None

    # Get all analytics
    personal_info = get_employee_personal_info(employee)
    location_access = get_employee_location_access(employee)
    leave_summary = get_employee_leave_summary(employee)
    attendance_stats = get_employee_attendance_stats(employee)
    recent_attendance = get_employee_recent_attendance(employee, days=30)
    punctuality_analysis = get_employee_punctuality_analysis(employee)
    working_hours_compliance = get_employee_working_hours_compliance(employee)
    recent_activity = get_employee_recent_activity(employee, limit=10)

    return {
        "employee": employee,
        "personal_info": personal_info,
        "location_access": location_access,
        "leave_summary": leave_summary,
        "attendance_stats": attendance_stats,
        "recent_attendance": recent_attendance,
        "punctuality_analysis": punctuality_analysis,
        "working_hours_compliance": working_hours_compliance,
        "recent_activity": recent_activity,
    }


def get_employee_personal_info(employee):
    """
    Get employee personal information
    """
    return {
        "full_name": employee.user.get_full_name(),
        "email": employee.user.email,
        "phone": employee.mobile_number,
        "designation": employee.designation,
        "department": employee.department,
        "company": employee.company.name,
        "join_date": employee.date_of_joining,
        "status": "Active" if employee.user.is_active else "Inactive",
        "manager": employee.manager.get_full_name() if employee.manager else None,
        "shift": employee.assigned_shift.name if employee.assigned_shift else None,
        "location": employee.location.name if employee.location else None,
    }


def get_employee_location_access(employee):
    """
    Get locations the employee can access
    Only shows the employee's assigned location (not all company locations)
    """
    locations = []

    # Only show the employee's assigned location
    if employee.location:
        locations.append(
            {
                "name": employee.location.name,
                "code": employee.location.country_code,
                "timezone": employee.location.timezone,
                "is_primary": True,  # This is their only accessible location
            }
        )
    else:
        # If no location assigned, show a message
        locations.append(
            {
                "name": "No Location Assigned",
                "code": "-",
                "timezone": "-",
                "is_primary": False,
            }
        )

    return locations


def get_employee_leave_summary(employee):
    """
    Get comprehensive leave summary for employee
    """
    # Get leave balances
    try:
        leave_balance = LeaveBalance.objects.get(employee=employee)
        balances = {
            "CL": leave_balance.casual_leave_balance,
            "SL": leave_balance.sick_leave_balance,
        }
    except LeaveBalance.DoesNotExist:
        balances = {"CL": 0, "SL": 0}

    # Get leave history
    current_year = timezone.localtime().year
    leave_history = LeaveRequest.objects.filter(employee=employee, start_date__year=current_year).order_by(
        "-start_date"
    )

    # Count by type
    leave_counts = (
        LeaveRequest.objects.filter(employee=employee, start_date__year=current_year, status="APPROVED")
        .values("leave_type")
        .annotate(count=Count("id"))
    )

    taken_by_type = {item["leave_type"]: item["count"] for item in leave_counts}

    # Calculate LOP days (Unpaid Leave) - total_days is a property, so we need to calculate manually
    lop_requests = LeaveRequest.objects.filter(
        employee=employee,
        start_date__year=current_year,
        leave_type="UL",  # Unpaid Leave
        status="APPROVED",
    )

    lop_days = sum(leave.total_days for leave in lop_requests)

    return {
        "balances": balances,
        "taken_by_type": taken_by_type,
        "total_taken": sum(taken_by_type.values()),
        "leave_history": leave_history,
        "lop_days": lop_days,
    }


def get_employee_attendance_stats(employee, months=3):
    """
    Get attendance statistics for employee including missed days
    """
    from companies.models import Holiday

    end_date = timezone.localtime().date()
    start_date = end_date - timedelta(days=months * 30)

    # Fetch data
    attendance_records = {
        att.date: att for att in Attendance.objects.filter(employee=employee, date__range=[start_date, end_date])
    }

    leaves = LeaveRequest.objects.filter(
        employee=employee, status="APPROVED", start_date__lte=end_date, end_date__gte=start_date
    )
    leave_dates = set()
    for l in leaves:
        curr = max(l.start_date, start_date)
        while curr <= min(l.end_date, end_date):
            leave_dates.add(curr)
            curr += timedelta(days=1)

    holiday_q = Q(location__isnull=True)
    if employee.location:
        holiday_q |= Q(location=employee.location)
    holidays = Holiday.objects.filter(
        company=employee.company, date__range=[start_date, end_date], is_active=True
    ).filter(holiday_q)
    holiday_dates = {h.date: h.name for h in holidays}

    total_days = 0
    present_days = 0
    late_days = 0
    early_departures = 0
    absent_days = 0  # Includes MISSED

    curr_date = start_date
    while curr_date <= end_date:
        if curr_date in attendance_records:
            att = attendance_records[curr_date]
            if att.status == "PRESENT":
                present_days += 1
                if att.is_late:
                    late_days += 1
                if att.is_early_departure:
                    early_departures += 1
            elif att.status == "ABSENT":
                absent_days += 1
        else:
            if employee.is_week_off(curr_date) or curr_date in holiday_dates or curr_date in leave_dates:
                pass
            elif curr_date == end_date:
                pass  # Not logged in yet
            else:
                absent_days += 1

        # Count only non-week-off non-holiday days as total working days for percentage?
        # Actually, let's just count all days for the attendance record base
        if not employee.is_week_off(curr_date) and curr_date not in holiday_dates:
            total_days += 1

        curr_date += timedelta(days=1)

    on_time_days = present_days - late_days
    on_time_percentage = (on_time_days / present_days * 100) if present_days > 0 else 0
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

    return {
        "total_days": total_days,
        "present_days": present_days,
        "late_days": late_days,
        "early_departures": early_departures,
        "absent_days": absent_days,
        "on_time_days": on_time_days,
        "on_time_percentage": round(on_time_percentage, 2),
        "attendance_percentage": round(attendance_percentage, 2),
        "missing_punches": Attendance.objects.filter(
            employee=employee, date__range=[start_date, end_date], clock_in__isnull=False, clock_out__isnull=True
        ).count(),
    }


def get_employee_recent_attendance(employee, days=30):
    """
    Get comprehensive recent attendance records including missed days, week-offs, and holidays
    """
    from companies.models import Holiday

    end_date = timezone.localtime().date()
    start_date = end_date - timedelta(days=days)

    # Fetch existing records
    attendance_records = {
        att.date: att for att in Attendance.objects.filter(employee=employee, date__range=[start_date, end_date])
    }

    # Fetch leaves
    leaves = LeaveRequest.objects.filter(
        employee=employee, status="APPROVED", start_date__lte=end_date, end_date__gte=start_date
    )
    leave_dates = {}
    for l in leaves:
        curr = max(l.start_date, start_date)
        while curr <= min(l.end_date, end_date):
            leave_dates[curr] = "LEAVE"
            curr += timedelta(days=1)

    # Fetch Holidays
    holiday_q = Q(location__isnull=True)
    if employee.location:
        holiday_q |= Q(location=employee.location)
    holidays = Holiday.objects.filter(
        company=employee.company, date__range=[start_date, end_date], is_active=True
    ).filter(holiday_q)
    holiday_dates = {h.date: h.name for h in holidays}

    history = []
    curr_date = end_date
    while curr_date >= start_date:
        if curr_date in attendance_records:
            history.append(attendance_records[curr_date])
        else:
            if employee.is_week_off(curr_date):
                status = "WEEKLY_OFF"
            elif curr_date in holiday_dates:
                status = "HOLIDAY"
            elif curr_date in leave_dates:
                status = "LEAVE"
            elif curr_date == end_date:  # Today
                status = "NOT_LOGGED_IN"
            else:
                status = "MISSED"

            history.append(
                {
                    "date": curr_date,
                    "status": status,
                    "status_display": status.replace("_", " ").title(),
                    "clock_in": None,
                    "clock_out": None,
                    "effective_hours": "-",
                    "id": None,
                }
            )
        curr_date -= timedelta(days=1)

    return history


def get_employee_punctuality_analysis(employee, days=30):
    """
    Analyze employee punctuality patterns
    """
    end_date = timezone.localtime().date()
    start_date = end_date - timedelta(days=days)

    attendance_records = Attendance.objects.filter(employee=employee, date__gte=start_date, status="PRESENT").order_by(
        "date"
    )

    # Collect clock-in times
    clock_in_times = []
    for record in attendance_records:
        if record.clock_in:
            clock_in_times.append(
                {
                    "date": record.date.strftime("%b %d"),  # Format: "Dec 26"
                    "time": record.clock_in.strftime("%H:%M"),
                    "is_late": record.is_late,
                    "is_grace": record.is_grace_used,
                }
            )

    # Calculate averages
    late_count = sum(1 for t in clock_in_times if t["is_late"])
    grace_count = sum(1 for t in clock_in_times if t["is_grace"])
    on_time_count = len(clock_in_times) - late_count - grace_count

    return {
        "clock_in_times": clock_in_times,
        "clock_in_times_json": json.dumps(clock_in_times),
        "late_count": late_count,
        "grace_count": grace_count,
        "on_time_count": on_time_count,
        "total_days": len(clock_in_times),
    }


def get_employee_working_hours_compliance(employee, months=1):
    """
    Calculate working hours compliance
    """
    end_date = timezone.localtime().date()
    start_date = end_date - timedelta(days=months * 30)

    attendance_records = Attendance.objects.filter(employee=employee, date__gte=start_date, status="PRESENT")

    total_hours = 0
    expected_hours = 0
    overtime_hours = 0
    undertime_count = 0

    for record in attendance_records:
        if record.effective_hours:
            # Parse HH:MM format to decimal hours
            try:
                if ":" in str(record.effective_hours):
                    hours, minutes = str(record.effective_hours).split(":")
                    decimal_hours = float(hours) + float(minutes) / 60
                else:
                    decimal_hours = float(record.effective_hours)

                total_hours += decimal_hours
                expected_hours += 9  # Assuming 9 hours per day

                if decimal_hours > 9:
                    overtime_hours += decimal_hours - 9
                elif decimal_hours < 9:
                    undertime_count += 1
            except (ValueError, AttributeError):
                # Skip records with invalid time format
                continue

    compliance_percentage = (total_hours / expected_hours * 100) if expected_hours > 0 else 0

    return {
        "total_hours": round(total_hours, 2),
        "expected_hours": round(expected_hours, 2),
        "overtime_hours": round(overtime_hours, 2),
        "undertime_count": undertime_count,
        "compliance_percentage": round(compliance_percentage, 2),
    }


def get_employee_recent_activity(employee, limit=10):
    """
    Get recent activity timeline for employee
    """
    activities = []

    # Recent attendance
    recent_attendance = Attendance.objects.filter(employee=employee).order_by("-date")[:5]

    for att in recent_attendance:
        if att.clock_in:
            # clock_in is already a datetime object, use it directly
            activities.append(
                {
                    "type": "clock_in",
                    "timestamp": att.clock_in if timezone.is_aware(att.clock_in) else timezone.make_aware(att.clock_in),
                    "description": f"Clocked in at {att.clock_in.strftime('%H:%M')}",
                    "icon": "fa-sign-in-alt",
                    "color": "success" if not att.is_late else "warning",
                }
            )
        if att.clock_out:
            # clock_out is already a datetime object, use it directly
            activities.append(
                {
                    "type": "clock_out",
                    "timestamp": att.clock_out
                    if timezone.is_aware(att.clock_out)
                    else timezone.make_aware(att.clock_out),
                    "description": f"Clocked out at {att.clock_out.strftime('%H:%M')}",
                    "icon": "fa-sign-out-alt",
                    "color": "info",
                }
            )

    # Recent leave requests
    recent_leaves = LeaveRequest.objects.filter(employee=employee).order_by("-created_at")[:3]

    for leave in recent_leaves:
        activities.append(
            {
                "type": "leave_request",
                "timestamp": leave.created_at,
                "description": f"{leave.get_leave_type_display()} - {leave.total_days} days ({leave.get_status_display()})",
                "icon": "fa-calendar-alt",
                "color": "primary" if leave.status == "APPROVED" else "secondary",
            }
        )

    # Sort by timestamp and limit
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:limit]
