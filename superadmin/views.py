from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator

from companies.models import Company
from employees.models import Employee, Attendance, LeaveRequest
from .decorators import superadmin_required, company_context_optional
from .utils import (
    get_dashboard_metrics,
    get_attendance_today_data,
    get_leaves_today_data,
    get_employee_lifecycle_data,
    get_leave_analytics,
    get_attendance_heatmap_data,
    get_company_summary,
)

import csv
from datetime import datetime


@login_required
@superadmin_required
@company_context_optional
def superadmin_dashboard(request, selected_company=None, selected_company_id=None):
    """
    Main SuperAdmin dashboard with company context switching
    """
    # Get all companies for dropdown
    companies = Company.objects.filter(is_active=True).order_by("name")

    # Get metrics based on selected company context
    metrics = get_dashboard_metrics(selected_company_id)

    # Get company overview for table
    company_overview = (
        Company.objects.filter(is_active=True)
        .annotate(employee_count=Count("employees"))
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
            return JsonResponse(
                {"success": False, "message": "Company not found"}, status=404
            )

    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)


@login_required
@superadmin_required
def company_list_view(request):
    """
    Detailed company list view
    """
    companies = Company.objects.annotate(
        employee_count=Count("employees"),
        active_employee_count=Count(
            "employees", filter=Q(employees__user__is_active=True)
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
    # Get company filter from query params (for drill-down from dashboard)
    company_filter = request.GET.get("company_id")
    if company_filter:
        try:
            selected_company_id = int(company_filter)
            selected_company = Company.objects.get(id=selected_company_id)
        except (ValueError, Company.DoesNotExist):
            pass

    # Base queryset
    employees = Employee.objects.select_related("user", "company", "manager").order_by(
        "-date_of_joining"
    )

    # Apply company filter
    if selected_company_id:
        employees = employees.filter(company_id=selected_company_id)

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
def company_monitor_dashboard(request, company_id):
    """
    Deep dive company analytics dashboard
    """
    company = get_object_or_404(Company, id=company_id)

    # Get company summary
    summary = get_company_summary(company_id)

    # Get employee lifecycle data
    employee_lifecycle = get_employee_lifecycle_data(company_id)

    # Get leave analytics
    leave_analytics = get_leave_analytics(company_id)

    # Get attendance heatmap
    now = timezone.localtime()
    heatmap_data = get_attendance_heatmap_data(company_id, now.year, now.month)

    context = {
        "company": company,
        "summary": summary,
        "employee_lifecycle": employee_lifecycle,
        "leave_analytics": leave_analytics,
        "heatmap_data": heatmap_data,
        "current_month": now.strftime("%B %Y"),
    }

    return render(request, "superadmin/company_monitor.html", context)


@login_required
@superadmin_required
def export_data_view(request, report_type):
    """
    Export data to CSV
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{report_type}_{datetime.now().strftime("%Y%m%d")}.csv"'
    )

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
                    emp.date_of_joining.strftime("%Y-%m-%d")
                    if emp.date_of_joining
                    else "",
                    "Active" if emp.user.is_active else "Inactive",
                ]
            )

    elif report_type == "attendance":
        # Export today's attendance
        writer.writerow(
            ["Employee", "Company", "Date", "Clock In", "Clock Out", "Status", "Hours"]
        )

        today = timezone.localtime().date()
        attendance = Attendance.objects.filter(date=today).select_related(
            "employee__user", "employee__company"
        )

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

        leaves = LeaveRequest.objects.select_related(
            "employee__user", "employee__company"
        ).all()

        company_id = request.GET.get("company_id")
        if company_id:
            leaves = leaves.filter(employee__company_id=company_id)

        for leave in leaves:
            writer.writerow(
                [
                    leave.employee.user.get_full_name(),
                    leave.employee.company.name,
                    leave.get_leave_type_display(),
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
    Comprehensive employee detail view with all analytics
    """
    from .utils import get_employee_detailed_analytics

    # Get all employee analytics
    analytics = get_employee_detailed_analytics(employee_id)

    if not analytics:
        messages.error(request, "Employee not found")
        return redirect("superadmin:employees")

    employee = analytics["employee"]

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
    }

    return render(request, "superadmin/employee_detail.html", context)
