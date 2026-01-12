from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Location, LocationWeekOff, Company
from employees.models import Employee


@login_required
def week_off_config(request):
    # Ensure admin/HR access
    # Assuming 'role' attribute exists on User model or we check checking group/permission
    if not (
        request.user.role in ["COMPANY_ADMIN", "SUPERADMIN", "HR", "MANAGER"]
        or request.user.is_superuser
    ):
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    # helper for company
    company = None
    if hasattr(request.user, "company"):
        company = request.user.company
    elif request.user.employee_profile and request.user.employee_profile.company:
        company = request.user.employee_profile.company

    if not company:
        # Handle superuser without company or error
        if request.user.is_superuser:
            # Just pick first company for demo or handle appropriately
            company = Company.objects.first()
        else:
            messages.error(request, "No company associated.")
            return redirect("dashboard")

    locations = Location.objects.filter(company=company)
    selected_location_id = request.GET.get("location")
    selected_location = None
    employees = []
    config = None

    if selected_location_id:
        selected_location = get_object_or_404(
            Location, id=selected_location_id, company=company
        )
        config, created = LocationWeekOff.objects.get_or_create(
            location=selected_location, defaults={"company": company}
        )
        employees = Employee.objects.filter(company=company, location=selected_location)

        if request.method == "POST":
            # Update Config
            config.monday = "monday" in request.POST
            config.tuesday = "tuesday" in request.POST
            config.wednesday = "wednesday" in request.POST
            config.thursday = "thursday" in request.POST
            config.friday = "friday" in request.POST
            config.saturday = "saturday" in request.POST
            config.sunday = "sunday" in request.POST
            config.save()

            # Apply week-offs directly to employees
            count = 0
            for emp in employees:
                emp.week_off_monday = config.monday
                emp.week_off_tuesday = config.tuesday
                emp.week_off_wednesday = config.wednesday
                emp.week_off_thursday = config.thursday
                emp.week_off_friday = config.friday
                emp.week_off_saturday = config.saturday
                emp.week_off_sunday = config.sunday
                emp.save()
                count += 1

            messages.success(
                request,
                f"Week-off configuration updated for {selected_location.name} and applied to {count} employees.",
            )
            return redirect(f"{request.path}?location={selected_location.id}")

    # Prepare locations list with selection state to avoid template logic issues
    locations_list = []
    for loc in locations:
        loc.is_selected = selected_location and loc.id == selected_location.id
        locations_list.append(loc)

    return render(
        request,
        "companies/week_off_config.html",
        {
            "locations": locations_list,
            "selected_location": selected_location,
            "employees": employees,
            "config": config,
        },
    )


@login_required
def role_configuration(request):
    # Access Check
    if not (
        request.user.role in ["COMPANY_ADMIN", "SUPERADMIN", "HR"]
        or request.user.is_superuser
    ):
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    # Get Company
    company = None
    if hasattr(request.user, "company") and request.user.company:
        company = request.user.company
    elif request.user.employee_profile and request.user.employee_profile.company:
        company = request.user.employee_profile.company

    if not company:
        messages.error(request, "No company associated.")
        return redirect("dashboard")

    from .models import Department, Designation

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_department":
            name = request.POST.get("name")
            if name:
                Department.objects.get_or_create(company=company, name=name)
                messages.success(request, f"Department '{name}' added.")

        elif action == "delete_department":
            dept_id = request.POST.get("id")
            Department.objects.filter(id=dept_id, company=company).delete()
            # Note: Cascade delete might delete designations if linked, or set null.
            messages.success(request, "Department deleted.")

        elif action == "add_designation":
            name = request.POST.get("name")
            dept_id = request.POST.get("department_id")
            if name:
                dept = None
                if dept_id:
                    dept = Department.objects.filter(
                        id=dept_id, company=company
                    ).first()
                Designation.objects.get_or_create(
                    company=company, name=name, defaults={"department": dept}
                )
                messages.success(request, f"Designation '{name}' added.")

        elif action == "delete_designation":
            desig_id = request.POST.get("id")
            Designation.objects.filter(id=desig_id, company=company).delete()
            messages.success(request, "Designation deleted.")

        return redirect("role_configuration")

    departments = Department.objects.filter(company=company)
    designations = Designation.objects.filter(company=company).select_related(
        "department"
    )

    return render(
        request,
        "companies/role_configuration.html",
        {"departments": departments, "designations": designations},
    )


from django.http import JsonResponse
import json


@login_required
def quick_add_department(request):
    """API view to quickly add a department"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")

            # Get Company
            company = None
            if hasattr(request.user, "company") and request.user.company:
                company = request.user.company
            elif (
                request.user.employee_profile and request.user.employee_profile.company
            ):
                company = request.user.employee_profile.company

            if not company:
                return JsonResponse(
                    {"status": "error", "message": "Company not found"}, status=400
                )

            # Check for duplicates
            from .models import Department

            dept, created = Department.objects.get_or_create(
                company=company, name__iexact=name, defaults={"name": name}
            )

            if not created:
                # If likely duplicates with different casing, return the existing one
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Department already exists",
                        "id": dept.id,
                        "name": dept.name,
                    }
                )

            return JsonResponse({"status": "success", "name": dept.name, "id": dept.id})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse(
        {"status": "error", "message": "Invalid request method"}, status=405
    )


@login_required
def quick_add_designation(request):
    """API view to quickly add a designation"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")

            # Get Company
            company = None
            if hasattr(request.user, "company") and request.user.company:
                company = request.user.company
            elif (
                request.user.employee_profile and request.user.employee_profile.company
            ):
                company = request.user.employee_profile.company

            if not company:
                return JsonResponse(
                    {"status": "error", "message": "Company not found"}, status=400
                )

            # Check for duplicates
            from .models import Designation

            desig, created = Designation.objects.get_or_create(
                company=company, name__iexact=name, defaults={"name": name}
            )

            if not created:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Designation already exists",
                        "id": desig.id,
                        "name": desig.name,
                    }
                )

            return JsonResponse(
                {"status": "success", "name": desig.name, "id": desig.id}
            )

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse(
        {"status": "error", "message": "Invalid request method"}, status=405
    )


@login_required
def quick_add_shift(request):
    """API view to quickly add a shift schedule"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")
            start_time = data.get("start_time")
            end_time = data.get("end_time")

            if not (name and start_time and end_time):
                return JsonResponse(
                    {"status": "error", "message": "Missing required fields"},
                    status=400,
                )

            # Get Company
            company = None
            if hasattr(request.user, "company") and request.user.company:
                company = request.user.company
            elif (
                request.user.employee_profile and request.user.employee_profile.company
            ):
                company = request.user.employee_profile.company

            if not company:
                return JsonResponse(
                    {"status": "error", "message": "Company not found"}, status=400
                )

            from .models import ShiftSchedule

            # Create Shift
            shift = ShiftSchedule.objects.create(
                company=company,
                name=name,
                start_time=start_time,
                end_time=end_time,
                shift_type="MORNING",  # Default, can be inferred or added to form
            )

            return JsonResponse(
                {
                    "status": "success",
                    "name": str(shift),
                    "id": shift.id,
                    "display": str(shift),
                }
            )

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse(
        {"status": "error", "message": "Invalid request method"}, status=405
    )
