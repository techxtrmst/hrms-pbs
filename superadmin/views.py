import csv
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from companies.models import Company
from employees.models import Attendance, Employee, LeaveRequest

from .decorators import company_context_optional, superadmin_required
from .utils import (
    get_attendance_heatmap_data,
    get_attendance_today_data,
    get_company_summary,
    get_dashboard_metrics,
    get_employee_lifecycle_data,
    get_leave_analytics,
    get_leaves_today_data,
)


@login_required
@superadmin_required
@company_context_optional
def superadmin_dashboard(request, selected_company=None, selected_company_id=None):
    """
    Main SuperAdmin dashboard with company context switching
    """
    from companies.models import BiometricDevice

    # Get all companies for dropdown
    companies = Company.objects.filter(is_active=True).order_by("name")

    # Get metrics based on selected company context
    metrics = get_dashboard_metrics(selected_company_id)

    # Get company overview for table - count strictly ACTIVE employees
    company_overview = (
        Company.objects.filter(is_active=True)
        .annotate(
            employee_count=Count(
                "employees", filter=Q(employees__is_active=True, employees__employment_status="ACTIVE")
            )
        )
        .order_by("name")
    )

    # --- Extra real data for the new dashboard design ---
    today = timezone.localtime().date()

    # Employee distribution (active / on-leave / inactive)
    total_emp = Employee.objects.count()
    active_emp = Employee.objects.filter(is_active=True, employment_status="ACTIVE").count()
    on_leave_count = LeaveRequest.objects.filter(start_date__lte=today, end_date__gte=today, status="APPROVED").count()
    inactive_emp = total_emp - active_emp

    active_pct = round((active_emp / total_emp * 100), 1) if total_emp > 0 else 0
    on_leave_pct = round((on_leave_count / total_emp * 100), 1) if total_emp > 0 else 0
    inactive_pct = round((inactive_emp / total_emp * 100), 1) if total_emp > 0 else 0

    # Active biometric / kiosk devices across all orgs
    active_devices = BiometricDevice.objects.filter(is_active=True).count()

    # Pending leave requests (not yet actioned) across all orgs
    pending_requests = LeaveRequest.objects.filter(status="PENDING").count()

    # Live (clocked-in right now) users — employees with a clock_in today but no clock_out
    live_users = Attendance.objects.filter(date=today, clock_in__isnull=False, clock_out__isnull=True).count()

    context = {
        "companies": companies,
        "selected_company": selected_company,
        "selected_company_id": selected_company_id,
        "metrics": metrics,
        "company_overview": company_overview,
        # extra
        "active_emp": active_emp,
        "on_leave_count": on_leave_count,
        "inactive_emp": inactive_emp,
        "active_pct": active_pct,
        "on_leave_pct": on_leave_pct,
        "inactive_pct": inactive_pct,
        "active_devices": active_devices,
        "pending_requests": pending_requests,
        "live_users": live_users,
    }

    return render(request, "superadmin/dashboard.html", context)


@login_required
@superadmin_required
def switch_company_api(request):
    """
    AJAX endpoint for switching company context
    """
    if request.method == "POST":
        company_id = request.POST.get("company_id")

        if company_id == "null" or company_id == "" or company_id is None:
            # Clear company context (global view)
            request.session.pop("selected_company_id", None)
            return JsonResponse(
                {
                    "success": True,
                    "message": "Switched to global view",
                    "company_id": None,
                }
            )

        try:
            company = Company.objects.get(id=company_id)
            request.session["selected_company_id"] = company.id
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Switched to {company.name}",
                    "company_id": company.id,
                    "company_name": company.name,
                }
            )
        except Company.DoesNotExist:
            return JsonResponse({"success": False, "message": "Company not found"}, status=404)

    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)


@login_required
@superadmin_required
def company_list_view(request):
    """
    Detailed company list view
    """
    companies = Company.objects.annotate(
        employee_count=Count("employees", filter=Q(employees__is_active=True, employees__employment_status="ACTIVE")),
        active_employee_count=Count(
            "employees",
            filter=Q(employees__is_active=True, employees__employment_status="ACTIVE"),
        ),
    ).order_by("name")

    # Search functionality
    search_query = request.GET.get("search", "")
    if search_query:
        companies = companies.filter(
            Q(name__icontains=search_query)
            | Q(primary_domain__icontains=search_query)
            | Q(email_domain__icontains=search_query)
        )

    context = {
        "companies": companies,
        "search_query": search_query,
    }

    return render(request, "superadmin/companies.html", context)


@login_required
@superadmin_required
@company_context_optional
def employee_list_view(request, selected_company=None, selected_company_id=None):
    """
    Global employee list with company filtering
    """
    # Get filters from query params
    company_filter = request.GET.get("company_id")
    role_filter = request.GET.get("role")

    if company_filter:
        try:
            selected_company_id = int(company_filter)
            selected_company = Company.objects.get(id=selected_company_id)
        except (ValueError, Company.DoesNotExist):
            pass

    # Base queryset - exclude employees whose exit_date is in the past
    employees = (
        Employee.objects.filter(is_active=True, employment_status="ACTIVE")
        .select_related("user", "company", "manager")
        .order_by("-date_of_joining")
    )

    # Apply company filter
    if selected_company_id:
        employees = employees.filter(company_id=selected_company_id)

    # Apply role filter
    if role_filter:
        if role_filter == "admin":
            employees = employees.filter(user__role__in=["SUPERADMIN", "COMPANY_ADMIN"])
        elif role_filter == "manager":
            employees = employees.filter(user__role="MANAGER")
        elif role_filter == "employee":
            employees = employees.filter(user__role="EMPLOYEE")

    # Search functionality
    search_query = request.GET.get("search", "")
    if search_query:
        employees = employees.filter(
            Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(designation__icontains=search_query)
            | Q(department__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(employees, 50)
    page_number = request.GET.get("page", 1)
    employees_page = paginator.get_page(page_number)

    # Get all companies for filter dropdown
    companies = Company.objects.filter(is_active=True).order_by("name")

    context = {
        "employees": employees_page,
        "companies": companies,
        "selected_company": selected_company,
        "selected_company_id": selected_company_id,
        "selected_role": role_filter,
        "search_query": search_query,
        "total_count": employees.count(),
    }

    return render(request, "superadmin/employees.html", context)


@login_required
@superadmin_required
@company_context_optional
def attendance_today_view(request, selected_company=None, selected_company_id=None):
    """
    Today's attendance across companies
    """
    # Get company filter from query params
    company_filter = request.GET.get("company_id")
    if company_filter:
        try:
            selected_company_id = int(company_filter)
            selected_company = Company.objects.get(id=selected_company_id)
        except (ValueError, Company.DoesNotExist):
            pass

    # Get attendance data
    attendance_records = get_attendance_today_data(selected_company_id)

    # Get all companies for filter dropdown
    companies = Company.objects.filter(is_active=True).order_by("name")

    context = {
        "attendance_records": attendance_records,
        "companies": companies,
        "selected_company": selected_company,
        "selected_company_id": selected_company_id,
        "today": timezone.localtime().date(),
    }

    return render(request, "superadmin/attendance_today.html", context)


@login_required
@superadmin_required
@company_context_optional
def leaves_today_view(request, selected_company=None, selected_company_id=None):
    """
    Today's approved leaves
    """
    # Get company filter from query params
    company_filter = request.GET.get("company_id")
    if company_filter:
        try:
            selected_company_id = int(company_filter)
            selected_company = Company.objects.get(id=selected_company_id)
        except (ValueError, Company.DoesNotExist):
            pass

    # Get leave data
    leave_records = get_leaves_today_data(selected_company_id)

    # Get all companies for filter dropdown
    companies = Company.objects.filter(is_active=True).order_by("name")

    context = {
        "leave_records": leave_records,
        "companies": companies,
        "selected_company": selected_company,
        "selected_company_id": selected_company_id,
        "today": timezone.localtime().date(),
    }

    return render(request, "superadmin/leaves_today.html", context)


@login_required
@superadmin_required
@login_required
@superadmin_required
def company_monitor_dashboard(request, company_id):
    """
    Deep dive company analytics dashboard
    """
    company = get_object_or_404(Company, id=company_id)

    # Date Handling for filtering
    now = timezone.localtime()
    try:
        selected_month = int(request.GET.get("month", now.month))
        selected_year = int(request.GET.get("year", now.year))
    except (ValueError, TypeError):
        selected_month = now.month
        selected_year = now.year

    # Get company summary
    summary = get_company_summary(company_id)

    # Get employee lifecycle data
    employee_lifecycle = get_employee_lifecycle_data(company_id)

    # Get leave analytics (Pass selected month/year)
    leave_analytics_raw = get_leave_analytics(company_id, months=selected_month, year=selected_year)

    # Convert data to JSON for JavaScript
    import json

    from django.core.serializers.json import DjangoJSONEncoder

    leave_analytics = {
        "distribution": json.dumps(leave_analytics_raw["distribution"], cls=DjangoJSONEncoder),
        "monthly_trends": json.dumps(leave_analytics_raw["monthly_trends"], cls=DjangoJSONEncoder),
        "frequent_takers": leave_analytics_raw["frequent_takers"],
    }

    # Get attendance heatmap (Pass selected month/year)
    heatmap_data_raw = get_attendance_heatmap_data(company_id, selected_year, selected_month)

    # Serialize daily attendance data for JavaScript
    heatmap_data = {
        **heatmap_data_raw,
        "daily_attendance": json.dumps(heatmap_data_raw["daily_attendance"], cls=DjangoJSONEncoder),
        "weekly_trends": json.dumps(heatmap_data_raw["weekly_trends"], cls=DjangoJSONEncoder),
    }

    # Context for filters
    import calendar

    month_list = [(i, calendar.month_name[i]) for i in range(1, 13)]
    year_list = range(2024, now.year + 2)  # Show a reasonable range

    current_month_name = calendar.month_name[selected_month]

    context = {
        "company": company,
        "summary": summary,
        "employee_lifecycle": employee_lifecycle,
        "leave_analytics": leave_analytics,
        "heatmap_data": heatmap_data,
        "current_month": f"{current_month_name} {selected_year}",
        "current_month_display": f"{current_month_name} {selected_year}",
        "months": month_list,
        "years": year_list,
        "selected_month": selected_month,
        "selected_year": selected_year,
    }

    return render(request, "superadmin/company_monitor.html", context)


@login_required
@superadmin_required
def export_data_view(request, report_type):
    """
    Export data to CSV
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{report_type}_{datetime.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)

    if report_type == "employees":
        # Export employees
        writer.writerow(
            [
                "Name",
                "Email",
                "Company",
                "Department",
                "Designation",
                "Join Date",
                "Status",
            ]
        )

        employees = Employee.objects.select_related("user", "company").all()
        company_id = request.GET.get("company_id")
        if company_id:
            employees = employees.filter(company_id=company_id)

        for emp in employees:
            writer.writerow(
                [
                    emp.user.get_full_name(),
                    emp.user.email,
                    emp.company.name,
                    emp.department,
                    emp.designation,
                    emp.date_of_joining.strftime("%Y-%m-%d") if emp.date_of_joining else "",
                    emp.get_employment_status_display(),
                ]
            )

    elif report_type == "attendance":
        # Export today's attendance
        writer.writerow(["Employee", "Company", "Date", "Clock In", "Clock Out", "Status", "Hours"])

        today = timezone.localtime().date()
        attendance = Attendance.objects.filter(date=today).select_related("employee__user", "employee__company")

        company_id = request.GET.get("company_id")
        if company_id:
            attendance = attendance.filter(employee__company_id=company_id)

        for att in attendance:
            writer.writerow(
                [
                    att.employee.user.get_full_name(),
                    att.employee.company.name,
                    att.date.strftime("%Y-%m-%d"),
                    att.clock_in.strftime("%H:%M") if att.clock_in else "",
                    att.clock_out.strftime("%H:%M") if att.clock_out else "",
                    att.get_status_display(),
                    att.effective_hours,
                ]
            )

    elif report_type == "leaves":
        # Export leaves
        writer.writerow(
            [
                "Employee",
                "Company",
                "Leave Type",
                "Start Date",
                "End Date",
                "Days",
                "Status",
            ]
        )

        leaves = LeaveRequest.objects.select_related("employee__user", "employee__company").all()

        company_id = request.GET.get("company_id")
        if company_id:
            leaves = leaves.filter(employee__company_id=company_id)

        for leave in leaves:
            writer.writerow(
                [
                    leave.employee.user.get_full_name(),
                    leave.employee.company.name,
                    "SL"
                    if leave.leave_type == "SL"
                    else (
                        "PL"
                        if leave.leave_type == "CL"
                        else ("LOP" if leave.leave_type == "UL" else leave.get_leave_type_display())
                    ),
                    leave.start_date.strftime("%Y-%m-%d"),
                    leave.end_date.strftime("%Y-%m-%d"),
                    leave.total_days,
                    leave.get_status_display(),
                ]
            )

    return response


@login_required
@superadmin_required
def employee_detail_view(request, employee_id):
    """
    Comprehensive employee detail view with all analytics and role management
    """
    from accounts.models import User

    from .utils import get_employee_detailed_analytics

    # Get all employee analytics
    analytics = get_employee_detailed_analytics(employee_id)

    if not analytics:
        messages.error(request, "Employee not found")
        return redirect("superadmin:employees")

    employee = analytics["employee"]
    user = employee.user

    # Handle Access Configuration Update
    if request.method == "POST" and "update_access" in request.POST:
        role = request.POST.get("role")
        is_active = request.POST.get("is_active") == "on"

        if role:
            user.role = role
        user.is_active = is_active

        # Django staff/superuser logic
        if role == User.Role.SUPERADMIN:
            user.is_staff = True
            user.is_superuser = True
        elif role == User.Role.COMPANY_ADMIN:
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False

        user.save()
        messages.success(request, f"Access configuration updated for {user.get_full_name()}")
        return redirect("superadmin:employee_detail", employee_id=employee_id)

    # Handle Password Reset
    if request.method == "POST" and "reset_password" in request.POST:
        # Set a temporary password or just force change
        temp_pass = f"{employee.company.name.replace(' ', '')}@2026"
        user.set_password(temp_pass)
        user.must_change_password = True
        user.save()
        messages.warning(
            request,
            f"Password has been reset to '{temp_pass}' for {user.get_full_name()}. They will be forced to change it on next login.",
        )
        return redirect("superadmin:employee_detail", employee_id=employee_id)

    # Quick stats for cards
    quick_stats = {
        "total_working_days": analytics["attendance_stats"]["total_days"],
        "leaves_taken": analytics["leave_summary"]["total_taken"],
        "attendance_percentage": analytics["attendance_stats"]["attendance_percentage"],
        "on_time_percentage": analytics["attendance_stats"]["on_time_percentage"],
    }

    # --- Real PetaBytz-style data calculations ---
    import calendar
    import json
    from datetime import date, timedelta

    from django.db.models import Q

    from companies.models import Holiday

    # Date Handling for filtering heatmap and monthly summary
    now = timezone.localtime()
    try:
        selected_month = int(request.GET.get("month", now.month))
        selected_year = int(request.GET.get("year", now.year))
    except (ValueError, TypeError):
        selected_month = now.month
        selected_year = now.year

    today = now.date()

    # 1. 6-Month Attendance Trend
    months_labels = []
    attendance_trend_data = []
    for i in range(5, -1, -1):
        year_offset = (today.month - i - 1) // 12
        m = (today.month - i - 1) % 12 + 1
        y = today.year + year_offset

        first_day = date(y, m, 1)
        last_day = date(y, m, calendar.monthrange(y, m)[1])

        # Total working days for this employee in this month (not week off)
        total_work_days = 0
        curr_d = first_day
        while curr_d <= last_day:
            if not employee.is_week_off(curr_d):
                total_work_days += 1
            curr_d += timedelta(days=1)

        recs_count = Attendance.objects.filter(
            employee=employee, date__range=[first_day, last_day], status__in=["PRESENT", "WFH", "ON_DUTY", "HALF_DAY"]
        ).count()

        rate = round((recs_count / total_work_days * 100), 1) if total_work_days > 0 else 0
        months_labels.append(calendar.month_abbr[m])
        attendance_trend_data.append(rate)

    # 2. Selected Month Summary
    first_of_month = date(selected_year, selected_month, 1)
    last_of_month = date(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1])

    month_recs = Attendance.objects.filter(employee=employee, date__range=[first_of_month, last_of_month])
    present_this_month = month_recs.filter(status__in=["PRESENT", "WFH", "ON_DUTY", "HALF_DAY"]).count()
    late_this_month = month_recs.filter(is_late=True).count()
    on_time_this_month = max(0, present_this_month - late_this_month)

    # Calculate approved leave days this month
    leaves_this_month = LeaveRequest.objects.filter(
        employee=employee, status="APPROVED", start_date__lte=last_of_month, end_date__gte=first_of_month
    )
    leave_days_this_month = 0
    approved_leave_dates = set()
    for leave in leaves_this_month:
        curr = max(leave.start_date, first_of_month)
        while curr <= min(leave.end_date, last_of_month):
            approved_leave_dates.add(curr)
            if not employee.is_week_off(curr):
                leave_days_this_month += 1
            curr += timedelta(days=1)

    this_month_summary = {
        "present_days": present_this_month,
        "on_time_arrivals": on_time_this_month,
        "late_arrivals": late_this_month,
        "leaves_taken": leave_days_this_month,
    }

    # 3. Attendance Heatmap
    first_weekday_idx = (first_of_month.weekday() + 1) % 7  # Sunday = 0
    grid_days = []

    # Pad prefix days
    for _ in range(first_weekday_idx):
        grid_days.append({"day": "", "status": "empty", "tooltip": ""})

    # Get holidays for location/company
    holiday_q = Q(location__isnull=True)
    if employee.location:
        holiday_q |= Q(location=employee.location)
    holidays_this_month = Holiday.objects.filter(
        company=employee.company, date__range=[first_of_month, last_of_month], is_active=True
    ).filter(holiday_q)
    holiday_dates = {h.date: h.name for h in holidays_this_month}

    attendance_by_date = {att.date: att for att in month_recs}
    curr_d = first_of_month
    while curr_d <= last_of_month:
        day_status = "ABSENT"
        tooltip = "Absent"

        if curr_d in attendance_by_date:
            att = attendance_by_date[curr_d]
            if att.status in ["PRESENT", "HALF_DAY", "WFH", "ON_DUTY"]:
                in_time = att.clock_in.strftime("%I:%M %p") if att.clock_in else "N/A"
                out_time = att.clock_out.strftime("%I:%M %p") if att.clock_out else "N/A"
                hours = f"{att.effective_hours} hrs" if att.effective_hours else "N/A"
                if att.is_late:
                    day_status = "LATE"
                    tooltip = f"Late Clock-In: {in_time} | Out: {out_time} ({hours})"
                else:
                    day_status = "PRESENT"
                    tooltip = f"Present | In: {in_time} | Out: {out_time} ({hours})"
            elif att.status == "ABSENT":
                day_status = "ABSENT"
                tooltip = "Absent"
            elif att.status == "LEAVE":
                day_status = "LEAVE"
                tooltip = "Approved Leave"
        else:
            if curr_d in approved_leave_dates:
                day_status = "LEAVE"
                tooltip = "Approved Leave"
            elif employee.is_week_off(curr_d):
                day_status = "WEEK_OFF"
                tooltip = "Week Off"
            elif curr_d in holiday_dates:
                day_status = "HOLIDAY"
                tooltip = f"Holiday: {holiday_dates[curr_d]}"
            elif curr_d > today:
                day_status = "FUTURE"
                tooltip = "Future Date"
            else:
                day_status = "ABSENT"
                tooltip = "Absent"

        grid_days.append({"day": curr_d.day, "status": day_status, "tooltip": tooltip})
        curr_d += timedelta(days=1)

    heatmap_month_name = calendar.month_name[selected_month]
    heatmap_month_year = f"{heatmap_month_name} {selected_year}"

    month_list = [(i, calendar.month_name[i]) for i in range(1, 13)]
    year_list = range(2024, today.year + 2)

    context = {
        "employee": employee,
        "personal_info": analytics["personal_info"],
        "location_access": analytics["location_access"],
        "leave_summary": analytics["leave_summary"],
        "attendance_stats": analytics["attendance_stats"],
        "recent_attendance": analytics["recent_attendance"],
        "punctuality_analysis": analytics["punctuality_analysis"],
        "working_hours_compliance": analytics["working_hours_compliance"],
        "recent_activity": analytics["recent_activity"],
        "quick_stats": quick_stats,
        "roles": User.Role.choices,
        # Real customized properties
        "attendance_trend_labels": json.dumps(months_labels),
        "attendance_trend_data": json.dumps(attendance_trend_data),
        "this_month_summary": this_month_summary,
        "heatmap_grid_days": grid_days,
        "heatmap_month_year": heatmap_month_year,
        "months": month_list,
        "years": year_list,
        "selected_month": selected_month,
        "selected_year": selected_year,
    }

    return render(request, "superadmin/employee_detail.html", context)


@login_required
@superadmin_required
def platform_settings(request):
    """
    Global system configuration view
    """
    import sys

    import django
    from django.conf import settings

    from core.models import GlobalConfiguration

    config = GlobalConfiguration.load()

    if request.method == "POST":
        # Handle Security Settings
        if "session_timeout" in request.POST:
            config.enforce_2fa = request.POST.get("enforce_2fa") == "on"
            config.session_timeout = int(request.POST.get("session_timeout", 30))
            messages.success(request, "Security settings updated.")

        # Handle Modules
        elif "module_attendance" in request.POST or "save_modules" in request.POST:
            config.module_attendance = request.POST.get("module_attendance") == "on"
            config.module_payroll = request.POST.get("module_payroll") == "on"
            config.module_ai = request.POST.get("module_ai") == "on"
            messages.success(request, "Module configuration saved.")

        # Handle Localization
        elif "default_currency" in request.POST:
            config.default_currency = request.POST.get("default_currency")
            config.date_format = request.POST.get("date_format")
            messages.success(request, "Localization settings updated.")

        config.save()
        return redirect("superadmin:platform_settings")

    context = {
        "python_version": sys.version.split()[0],
        "django_version": django.get_version(),
        "debug": settings.DEBUG,
        "time_zone": settings.TIME_ZONE,
        "config": config,
    }
    return render(request, "superadmin/platform_settings.html", context)


@login_required
@superadmin_required
def create_company_view(request):
    """
    View to create a new organization/tenant
    """
    from companies.models import Company

    if request.method == "POST":
        name = request.POST.get("name")
        domain = request.POST.get("domain")
        email_domain = request.POST.get("email_domain")
        location = request.POST.get("location")

        if name and domain:
            time_zone = request.POST.get("timezone", "UTC")
            currency = request.POST.get("currency", "USD")

            try:
                Company.objects.create(
                    name=name,
                    primary_domain=domain,
                    email_domain=email_domain,
                    location=location,
                    time_zone=time_zone,
                    currency=currency,
                    is_active=True,
                )
                messages.success(request, f"Organization '{name}' created successfully.")
                return redirect("superadmin:companies")
            except Exception as e:
                messages.error(request, f"Error creating organization: {str(e)}")
        else:
            messages.error(request, "Name and Domain are required.")

    return render(request, "superadmin/company_form.html")


@login_required
@superadmin_required
@company_context_optional
def biometric_integration_view(request, selected_company=None, selected_company_id=None):
    """
    Manage biometric devices across companies or for a specific company
    """
    from companies.models import BiometricDevice, Location

    if not selected_company_id:
        company_filter = request.GET.get("company_id")
        if company_filter and company_filter != "null":
            selected_company_id = int(company_filter)
            selected_company = Company.objects.get(id=selected_company_id)

    # Base queryset
    devices = BiometricDevice.objects.select_related("company", "location").all()
    if selected_company_id:
        devices = devices.filter(company_id=selected_company_id)

    # Get active companies and locations for forms
    companies = Company.objects.filter(is_active=True).order_by("name")
    locations = Location.objects.filter(is_active=True)
    if selected_company_id:
        locations = locations.filter(company_id=selected_company_id)

    if request.method == "POST":
        if "add_device" in request.POST:
            comp_id = request.POST.get("company") or selected_company_id
            loc_id = request.POST.get("location")
            name = request.POST.get("name")
            ip = request.POST.get("ip_address")
            port = request.POST.get("port", 4370)
            sn = request.POST.get("serial_number")
            device_type = request.POST.get("device_type")

            try:
                BiometricDevice.objects.create(
                    company_id=comp_id,
                    location_id=loc_id if loc_id else None,
                    name=name,
                    ip_address=ip,
                    port=port,
                    serial_number=sn,
                    device_type=device_type,
                )
                messages.success(request, f"Biometric device '{name}' added successfully.")
            except Exception as e:
                messages.error(request, f"Error adding device: {str(e)}")
            return redirect("superadmin:biometric_integration")

        elif "delete_device" in request.POST:
            device_id = request.POST.get("device_id")
            BiometricDevice.objects.filter(id=device_id).delete()
            messages.success(request, "Device removed.")
            return redirect("superadmin:biometric_integration")

    context = {
        "devices": devices,
        "companies": companies,
        "locations": locations,
        "selected_company": selected_company,
        "selected_company_id": selected_company_id,
        "device_types": BiometricDevice.DEVICE_TYPES,
    }

    return render(request, "superadmin/biometric_integration.html", context)


@login_required
@superadmin_required
@company_context_optional
def workflow_configuration_view(request, selected_company=None, selected_company_id=None):
    """
    Manage approval workflows across companies
    """
    from core.models import ApprovalWorkflow

    if not selected_company_id:
        company_filter = request.GET.get("company_id")
        if company_filter and company_filter != "null":
            selected_company_id = int(company_filter)
            selected_company = Company.objects.get(id=selected_company_id)

    # Base queryset
    workflows = ApprovalWorkflow.objects.select_related("company").all()
    if selected_company_id:
        workflows = workflows.filter(company_id=selected_company_id)

    # Handle workflow creation
    if request.method == "POST" and "add_workflow" in request.POST:
        comp_id = request.POST.get("company") or selected_company_id
        wf_type = request.POST.get("workflow_type")
        name = request.POST.get("name")
        levels = int(request.POST.get("levels", 1))

        # Simple config logic (can be expanded)
        config = {}
        for i in range(1, levels + 1):
            config[str(i)] = {"role": "MANAGER" if i == 1 else "COMPANY_ADMIN"}

        try:
            ApprovalWorkflow.objects.create(
                company_id=comp_id, workflow_type=wf_type, name=name, levels=levels, levels_config=config
            )
            messages.success(request, f"Workflow '{name}' created successfully.")
        except Exception as e:
            messages.error(request, f"Error creating workflow: {str(e)}")
        return redirect("superadmin:workflow_configuration")

    # Get companies for filter/form
    companies = Company.objects.filter(is_active=True).order_by("name")

    context = {
        "workflows": workflows,
        "companies": companies,
        "selected_company": selected_company,
        "selected_company_id": selected_company_id,
        "workflow_types": ApprovalWorkflow.WORKFLOW_TYPES,
    }

    return render(request, "superadmin/workflow_configuration.html", context)


@csrf_exempt
@login_required
@superadmin_required
def test_biometric_sync_api(request):
    """
    Simulate a biometric device packet for testing purposes
    """
    import json

    from django.http import JsonResponse
    from django.urls import reverse

    from companies.models import BiometricDevice

    device_id = request.POST.get("device_id")
    device = BiometricDevice.objects.get(id=device_id)

    # Use a random active employee from this company
    employee = device.company.employees.filter(is_active=True).first()
    if not employee or not employee.biometric_id:
        return JsonResponse({"success": False, "message": "No employee with Biometric ID found in this organization."})

    # Prepare payload
    payload = {
        "serial_number": device.serial_number,
        "biometric_id": employee.biometric_id,
        "timestamp": timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "CHECK",
    }

    # Internal call to the actual sync API to verify logic
    # In a real app, this would be an external hit, but here we can simulate logic
    # Mocking a request object
    from django.test import RequestFactory

    from core.views import biometric_sync_api

    factory = RequestFactory()
    mock_request = factory.post(
        reverse("biometric_sync_api"), data=json.dumps(payload), content_type="application/json"
    )

    biometric_sync_api(mock_request)
    return JsonResponse(
        {"success": True, "message": f"Test signal sent for {employee.user.get_full_name()}. Check attendance logs!"}
    )
