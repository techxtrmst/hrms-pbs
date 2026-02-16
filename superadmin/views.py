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
    from django.utils import timezone

    today = timezone.localtime().date()

    # Get all companies for dropdown
    companies = Company.objects.filter(is_active=True).order_by("name")

    # Get metrics based on selected company context
    metrics = get_dashboard_metrics(selected_company_id)

    # Get company overview for table - exclude employees whose exit_date is in the past
    company_overview = (
        Company.objects.filter(is_active=True)
        .annotate(
            employee_count=Count(
                "employees", filter=Q(employees__exit_date__isnull=True) | Q(employees__exit_date__gte=today)
            )
        )
        .order_by("name")
    )

    context = {
        "companies": companies,
        "selected_company": selected_company,
        "selected_company_id": selected_company_id,
        "metrics": metrics,
        "company_overview": company_overview,
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
    from django.utils import timezone

    today = timezone.localtime().date()

    companies = Company.objects.annotate(
        employee_count=Count(
            "employees", filter=Q(employees__exit_date__isnull=True) | Q(employees__exit_date__gte=today)
        ),
        active_employee_count=Count(
            "employees",
            filter=Q(employees__user__is_active=True)
            & (Q(employees__exit_date__isnull=True) | Q(employees__exit_date__gte=today)),
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
    from django.utils import timezone

    today = timezone.localtime().date()

    employees = (
        Employee.objects.filter(Q(exit_date__isnull=True) | Q(exit_date__gte=today))
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
                    "Active" if emp.user.is_active else "Inactive",
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
