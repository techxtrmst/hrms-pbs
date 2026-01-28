import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required
from employees.models import Employee

from .models import Announcement, Company, Location, LocationWeekOff


@login_required
@admin_required
def announcement_configuration(request):
    """
    Announcement Configuration View - Admin can create and manage announcements
    """
    # Get Company
    company = None
    if hasattr(request.user, "company") and request.user.company:
        company = request.user.company
    elif request.user.employee_profile and request.user.employee_profile.company:
        company = request.user.employee_profile.company

    if not company:
        messages.error(request, "No company associated.")
        return redirect("dashboard")

    # Get all locations for this company
    locations = Location.objects.filter(company=company, is_active=True)

    # Handle POST requests (Create/Update/Delete)
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            title = request.POST.get("title")
            content = request.POST.get("content")
            location_id = request.POST.get("location")

            is_active = request.POST.get("is_active") == "on"
            send_email = request.POST.get("send_email") == "on"
            image = request.FILES.get("image")

            if image:
                pass  # Allow any ratio, display handled in template

            if title and content:
                location = None
                if location_id:
                    location = Location.objects.filter(id=location_id, company=company).first()

                Announcement.objects.create(
                    company=company,
                    location=location,
                    title=title,
                    content=content,
                    image=image,
                    is_active=is_active,
                )

                if send_email:
                    recipients = Employee.objects.filter(company=company, is_active=True)
                    if location:
                        recipients = recipients.filter(location=location)

                    recipient_emails = [emp.user.email for emp in recipients if emp.user.email]

                    if recipient_emails:
                        try:
                            from django.core.mail import EmailMultiAlternatives
                            from django.template.loader import render_to_string

                            # Prepare content
                            content_html_formatted = content.replace(chr(10), "<br>")
                            
                            # Determine Logo URL
                            company_logo_url = None
                            if company.logo:
                                try:
                                    company_logo_url = request.build_absolute_uri(company.logo.url)
                                except Exception:
                                    pass

                            # Context for template
                            context = {
                                "title": title,
                                "content_html": content_html_formatted,
                                "company_name": company.name,
                                "has_image": True if image else False,
                                "company_logo_url": company_logo_url,
                            }

                            # Render HTML content
                            html_content = render_to_string("companies/emails/new_announcement.html", context)

                            # Create plain text version
                            text_content = f"{title}\n\n{content}\n\n--\n{company.name} HR Team"

                            email_msg = EmailMultiAlternatives(
                                subject=f"New Announcement: {title}",
                                body=text_content,
                                from_email="hrms@petabytz.com",
                                to=[],
                                bcc=recipient_emails,
                            )
                            email_msg.attach_alternative(html_content, "text/html")

                            # Attach image if present
                            if image:
                                import mimetypes

                                # Get the image content
                                image.seek(0)
                                img_data = image.read()

                                # Determine MIME type
                                mime_type = mimetypes.guess_type(image.name)[0] or "image/jpeg"

                                # Attach as inline image
                                email_msg.attach(image.name, img_data, mime_type)

                                # Also add as inline for HTML display
                                from email.mime.image import MIMEImage

                                img = MIMEImage(img_data)
                                img.add_header("Content-ID", "<announcement_image>")
                                img.add_header("Content-Disposition", "inline", filename=image.name)
                                email_msg.attach(img)

                                # Reset file pointer
                                image.seek(0)

                            email_msg.send(fail_silently=True)
                            messages.success(
                                request,
                                f"Announcement '{title}' created and emailed to {len(recipient_emails)} employees.",
                            )
                        except Exception as e:
                            messages.warning(request, f"Announcement created but email sending failed: {str(e)}")
                    else:
                        messages.success(
                            request, f"Announcement '{title}' created successfully! (No employees found to email)"
                        )
                else:
                    messages.success(request, f"Announcement '{title}' created successfully!")
            else:
                messages.error(request, "Title and content are required.")

        elif action == "update":
            announcement_id = request.POST.get("announcement_id")
            announcement = get_object_or_404(Announcement, id=announcement_id, company=company)

            announcement.title = request.POST.get("title")
            announcement.content = request.POST.get("content")
            location_id = request.POST.get("location")
            announcement.location = (
                Location.objects.filter(id=location_id, company=company).first() if location_id else None
            )
            announcement.is_active = request.POST.get("is_active") == "on"

            if "image" in request.FILES:
                announcement.image = request.FILES["image"]

            announcement.save()

            messages.success(request, f"Announcement '{announcement.title}' updated successfully!")

        elif action == "delete":
            announcement_id = request.POST.get("announcement_id")
            announcement = get_object_or_404(Announcement, id=announcement_id, company=company)
            title = announcement.title
            announcement.delete()
            messages.success(request, f"Announcement '{title}' deleted successfully!")

        return redirect("announcement_configuration")

    # Get all announcements for this company
    announcements = Announcement.objects.filter(company=company).order_by("-created_at")

    return render(
        request,
        "companies/announcement_configuration.html",
        {
            "announcements": announcements,
            "locations": locations,
            "company": company,
        },
    )


@login_required
def week_off_config(request):
    # Ensure admin/HR access
    # Assuming 'role' attribute exists on User model or we check checking group/permission
    if not (request.user.role in ["COMPANY_ADMIN", "SUPERADMIN", "HR", "MANAGER"] or request.user.is_superuser):
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
    selected_employee_id = request.GET.get("employee")
    selected_location = None
    selected_employee = None
    employees = []
    config = None

    if selected_location_id:
        selected_location = get_object_or_404(Location, id=selected_location_id, company=company)
        employees = Employee.objects.filter(company=company, location=selected_location)

        if selected_employee_id:
            selected_employee = get_object_or_404(Employee, id=selected_employee_id, company=company, location=selected_location)
            # Use employee's week-off fields
            config = {
                "monday": selected_employee.week_off_monday,
                "tuesday": selected_employee.week_off_tuesday,
                "wednesday": selected_employee.week_off_wednesday,
                "thursday": selected_employee.week_off_thursday,
                "friday": selected_employee.week_off_friday,
                "saturday": selected_employee.week_off_saturday,
                "sunday": selected_employee.week_off_sunday,
            }
        else:
            config, created = LocationWeekOff.objects.get_or_create(
                location=selected_location, defaults={"company": company}
            )

        if request.method == "POST":
            # Update Config
            monday = "monday" in request.POST
            tuesday = "tuesday" in request.POST
            wednesday = "wednesday" in request.POST
            thursday = "thursday" in request.POST
            friday = "friday" in request.POST
            saturday = "saturday" in request.POST
            sunday = "sunday" in request.POST

            if selected_employee:
                selected_employee.week_off_monday = monday
                selected_employee.week_off_tuesday = tuesday
                selected_employee.week_off_wednesday = wednesday
                selected_employee.week_off_thursday = thursday
                selected_employee.week_off_friday = friday
                selected_employee.week_off_saturday = saturday
                selected_employee.week_off_sunday = sunday
                selected_employee.save()
                messages.success(
                    request,
                    f"Week-off configuration updated specifically for {selected_employee.user.get_full_name()}.",
                )
            else:
                config.monday = monday
                config.tuesday = tuesday
                config.wednesday = wednesday
                config.thursday = thursday
                config.friday = friday
                config.saturday = saturday
                config.sunday = sunday
                config.save()

                # Apply week-offs directly to employees in this location
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
            
            redirect_url = f"{request.path}?location={selected_location.id}"
            if selected_employee:
                redirect_url += f"&employee={selected_employee.id}"
            return redirect(redirect_url)

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
            "selected_employee": selected_employee,
            "employees": employees,
            "config": config,
        },
    )


@login_required
def role_configuration(request):
    # Access Check
    if not (request.user.role in ["COMPANY_ADMIN", "SUPERADMIN", "HR"] or request.user.is_superuser):
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
                    dept = Department.objects.filter(id=dept_id, company=company).first()
                Designation.objects.get_or_create(company=company, name=name, defaults={"department": dept})
                messages.success(request, f"Designation '{name}' added.")

        elif action == "delete_designation":
            desig_id = request.POST.get("id")
            Designation.objects.filter(id=desig_id, company=company).delete()
            messages.success(request, "Designation deleted.")

        return redirect("role_configuration")

    departments = Department.objects.filter(company=company)
    designations = Designation.objects.filter(company=company).select_related("department")

    return render(
        request,
        "companies/role_configuration.html",
        {"departments": departments, "designations": designations},
    )


@login_required
def quick_add_department(request):
    """API view to quickly add a department"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")
            company_id = data.get("company_id")

            # Get Company
            company = None

            if company_id:
                from .models import Company

                try:
                    # Allow if superuser or if ID matches user's company
                    target_company = Company.objects.get(id=company_id)
                    if (
                        request.user.is_superuser
                        or (hasattr(request.user, "company") and request.user.company == target_company)
                        or (request.user.employee_profile and request.user.employee_profile.company == target_company)
                    ):
                        company = target_company
                except Company.DoesNotExist:
                    pass

            # Fallback if no ID or lookup failed
            if not company:
                if hasattr(request.user, "company") and request.user.company:
                    company = request.user.company
                elif request.user.employee_profile and request.user.employee_profile.company:
                    company = request.user.employee_profile.company

            if not company:
                return JsonResponse({"status": "error", "message": "Company not found"}, status=400)

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
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


@login_required
def quick_add_designation(request):
    """API view to quickly add a designation"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")
            company_id = data.get("company_id")

            # Get Company
            company = None

            if company_id:
                from .models import Company

                try:
                    target_company = Company.objects.get(id=company_id)
                    if (
                        request.user.is_superuser
                        or (hasattr(request.user, "company") and request.user.company == target_company)
                        or (request.user.employee_profile and request.user.employee_profile.company == target_company)
                    ):
                        company = target_company
                except Company.DoesNotExist:
                    pass

            if not company:
                if hasattr(request.user, "company") and request.user.company:
                    company = request.user.company
                elif request.user.employee_profile and request.user.employee_profile.company:
                    company = request.user.employee_profile.company

            if not company:
                return JsonResponse({"status": "error", "message": "Company not found"}, status=400)

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

            return JsonResponse({"status": "success", "name": desig.name, "id": desig.id})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


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

            company_id = data.get("company_id")

            # Get Company
            company = None

            if company_id:
                from .models import Company

                try:
                    target_company = Company.objects.get(id=company_id)
                    if (
                        request.user.is_superuser
                        or (hasattr(request.user, "company") and request.user.company == target_company)
                        or (request.user.employee_profile and request.user.employee_profile.company == target_company)
                    ):
                        company = target_company
                except Company.DoesNotExist:
                    pass

            if not company:
                if hasattr(request.user, "company") and request.user.company:
                    company = request.user.company
                elif request.user.employee_profile and request.user.employee_profile.company:
                    company = request.user.employee_profile.company

            if not company:
                return JsonResponse({"status": "error", "message": "Company not found"}, status=400)

            from .models import ShiftSchedule

            # Check for existing shift with same name (case-insensitive)
            existing_shift = ShiftSchedule.objects.filter(company=company, name__iexact=name).first()

            if existing_shift:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Shift '{existing_shift.name}' already exists",
                        "id": existing_shift.id,
                        "name": str(existing_shift),
                        "display": str(existing_shift),
                    }
                )

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
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)
