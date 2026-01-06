from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db import transaction
from .models import (
    Employee,
    Attendance,
    LocationLog,
    LeaveRequest,
    LeaveBalance,
    RegularizationRequest,
)
from core.email_utils import send_leave_request_notification
from .forms import (
    EmployeeCreationForm,
    LeaveApplicationForm,
    EmployeeUpdateForm,
    EmployeeBulkImportForm,
    RegularizationRequestForm,
)
from accounts.models import User
from django.http import JsonResponse
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required


class CompanyAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == User.Role.COMPANY_ADMIN


class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = "employees/employee_list.html"
    context_object_name = "employees"

    def get_queryset(self):
        user = self.request.user

        # Base queryset based on role
        if user.role == User.Role.COMPANY_ADMIN:
            queryset = Employee.objects.filter(company=user.company)
        elif user.role == User.Role.MANAGER:
            # Show only employees who report to this manager AND are in the same location
            try:
                manager_employee = Employee.objects.get(user=user)
                manager_location = manager_employee.location

                # Filter by manager AND same location
                queryset = Employee.objects.filter(
                    manager=user,
                    location=manager_location,  # Only same location employees
                )
            except Employee.DoesNotExist:
                queryset = Employee.objects.none()
        else:
            try:
                queryset = Employee.objects.filter(user=user)
            except:
                queryset = Employee.objects.none()

        # Apply employment status filter
        status_filter = self.request.GET.get("status", "active")

        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)
        elif status_filter == "resigned":
            queryset = queryset.filter(employment_status="RESIGNED")
        elif status_filter == "absconded":
            queryset = queryset.filter(employment_status="ABSCONDED")
        elif status_filter == "terminated":
            queryset = queryset.filter(employment_status="TERMINATED")
        # 'all' shows everyone

        return queryset.select_related("user", "company", "manager")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employees = self.get_queryset()
        departments = employees.values_list("department", flat=True).distinct()
        departments_count = len([d for d in departments if d])
        context["departments_count"] = departments_count

        # Add counts for different statuses
        user = self.request.user
        if user.role == User.Role.COMPANY_ADMIN:
            all_employees = Employee.objects.filter(company=user.company)
        elif user.role == User.Role.MANAGER:
            # Show only employees who report to this manager AND are in the same location
            try:
                manager_employee = Employee.objects.get(user=user)
                manager_location = manager_employee.location
                all_employees = Employee.objects.filter(
                    manager=user,
                    location=manager_location,  # Only same location employees
                )
            except Employee.DoesNotExist:
                all_employees = Employee.objects.none()
        else:
            try:
                all_employees = Employee.objects.filter(user=user)
            except:
                all_employees = Employee.objects.none()

        context["active_count"] = all_employees.filter(is_active=True).count()
        context["inactive_count"] = all_employees.filter(is_active=False).count()
        context["selected_filter"] = self.request.GET.get("status", "active")

        return context


class EmployeeCreateView(LoginRequiredMixin, CompanyAdminRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeCreationForm
    template_name = "employees/employee_form.html"
    success_url = reverse_lazy("employee_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        return super().form_valid(form)


class EmployeeUpdateView(LoginRequiredMixin, CompanyAdminRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeUpdateForm
    template_name = "employees/employee_form.html"
    success_url = reverse_lazy("employee_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_queryset(self):
        return Employee.objects.filter(company=self.request.user.company)

    def form_valid(self, form):
        response = super().form_valid(form)
        employee = self.object

        # Handle emergency contacts
        from .models import EmergencyContact

        # Collect emergency contacts from POST data
        contact_index = 0
        processed_contact_ids = []

        while True:
            name_key = f"emergency_contact_name_{contact_index}"

            if name_key not in self.request.POST:
                break

            name = self.request.POST.get(name_key, "").strip()
            phone = self.request.POST.get(
                f"emergency_contact_phone_{contact_index}", ""
            ).strip()
            relationship = self.request.POST.get(
                f"emergency_contact_relationship_{contact_index}", ""
            ).strip()
            is_primary = (
                f"emergency_contact_primary_{contact_index}" in self.request.POST
            )
            contact_id = self.request.POST.get(
                f"emergency_contact_id_{contact_index}", ""
            ).strip()

            # Only process if at least name and phone are provided
            if name and phone:
                if contact_id:
                    # Update existing contact
                    try:
                        contact = EmergencyContact.objects.get(
                            id=contact_id, employee=employee
                        )
                        contact.name = name
                        contact.phone_number = phone
                        contact.relationship = relationship
                        contact.is_primary = is_primary
                        contact.save()
                        processed_contact_ids.append(int(contact_id))
                    except EmergencyContact.DoesNotExist:
                        pass
                else:
                    # Create new contact
                    contact = EmergencyContact.objects.create(
                        employee=employee,
                        name=name,
                        phone_number=phone,
                        relationship=relationship,
                        is_primary=is_primary,
                    )
                    processed_contact_ids.append(contact.id)

            contact_index += 1

        # Delete contacts that were marked for deletion
        for key in self.request.POST:
            if key.startswith("emergency_contact_delete_"):
                contact_id = key.replace("emergency_contact_delete_", "")
                try:
                    EmergencyContact.objects.filter(
                        id=contact_id, employee=employee
                    ).delete()
                except:
                    pass

        # Delete contacts that were removed (not in processed list)
        # This handles contacts that were removed from the form
        existing_contacts = EmergencyContact.objects.filter(employee=employee)
        for contact in existing_contacts:
            if contact.id not in processed_contact_ids:
                # Check if it's marked for deletion
                if f"emergency_contact_delete_{contact.id}" in self.request.POST:
                    contact.delete()

        return response


class EmployeeDeleteView(LoginRequiredMixin, CompanyAdminRequiredMixin, DeleteView):
    model = Employee
    template_name = "employees/employee_confirm_delete.html"
    success_url = reverse_lazy("employee_list")

    def get_queryset(self):
        return Employee.objects.filter(company=self.request.user.company)

    def form_valid(self, form):
        from django.shortcuts import redirect

        employee = self.get_object()
        if employee.user:
            employee.user.delete()
        else:
            employee.delete()
        return redirect(self.success_url)


# --- Attendance & Tracking Views ---


@csrf_exempt
@login_required
def clock_in(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            lat = data.get("latitude")
            lng = data.get("longitude")

            # Ensure employee profile exists
            if not hasattr(request.user, "employee_profile"):
                return JsonResponse(
                    {"status": "error", "message": "No employee profile found"},
                    status=400,
                )

            employee = request.user.employee_profile
            today = timezone.localdate()

            # Try to get existing attendance record for today
            try:
                attendance = Attendance.objects.get(employee=employee, date=today)

                # Check if already clocked in
                if attendance.clock_in:
                    # Increment attempt counter (max 3)
                    if attendance.clock_in_attempts < 3:
                        attendance.clock_in_attempts += 1
                        attendance.save()

                    # Log the duplicate attempt
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"Duplicate clock-in attempt #{attendance.clock_in_attempts} by {employee.user.username} on {today}"
                    )

                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "You are already clocked in.",
                            "already_clocked_in": True,
                            "clock_in_time": attendance.clock_in.strftime("%H:%M:%S"),
                        }
                    )

            except Attendance.DoesNotExist:
                # Create new attendance record
                attendance = Attendance(employee=employee, date=today)

            # Determine Status based on Type
            clock_in_type = data.get("type")
            if clock_in_type == "remote":
                status = "WFH"
            elif clock_in_type == "on_duty":
                status = "ON_DUTY"
            else:
                status = "PRESENT"

            # Set clock-in details
            attendance.clock_in = timezone.now()
            attendance.location_in = f"{lat},{lng}"
            attendance.status = status
            attendance.clock_in_attempts = 1  # First valid attempt

            # Start location tracking
            attendance.location_tracking_active = True

            # Calculate location tracking end time based on shift duration
            shift = employee.assigned_shift
            if shift:
                shift_duration = shift.get_shift_duration_timedelta()
                attendance.location_tracking_end_time = (
                    attendance.clock_in + shift_duration
                )
            else:
                # Default to 9 hours if no shift assigned
                from datetime import timedelta

                attendance.location_tracking_end_time = attendance.clock_in + timedelta(
                    hours=9
                )

            # Calculate late arrival based on shift
            attendance.calculate_late_arrival()

            attendance.save()

            # Send WFH Notification
            if status == "WFH":
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings

                    subject = f"WFH Alert: {employee.user.get_full_name()} has clocked in remotely"
                    message = f"""
                    Employee: {employee.user.get_full_name()}
                    Designation: {employee.designation}
                    Department: {employee.department}
                    
                    Clock In Time: {attendance.clock_in.strftime("%d-%m-%Y %H:%M:%S")}
                    
                    This user has clocked in using 'Work From Home' mode.
                    """

                    # Send to HR/Admin emails (configure in settings or fetch dynamically)
                    # For now, sending to ADMINs
                    recipient_list = [
                        admin.email
                        for admin in User.objects.filter(role=User.Role.COMPANY_ADMIN)
                        if admin.email
                    ]

                    # Also notify manager
                    if employee.manager and employee.manager.email:
                        recipient_list.append(employee.manager.email)

                    if recipient_list:
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL,
                            recipient_list,
                            fail_silently=True,
                        )
                except Exception as email_err:
                    # Non-blocking error
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send WFH email: {str(email_err)}")

            # Prepare response with late status
            response_data = {
                "status": "success",
                "time": attendance.clock_in.strftime("%H:%M:%S"),
                "location_tracking_active": True,
                "tracking_end_time": attendance.location_tracking_end_time.strftime(
                    "%H:%M:%S"
                ),
            }

            if attendance.is_late:
                response_data["is_late"] = True
                response_data["late_by_minutes"] = attendance.late_by_minutes
                response_data["message"] = (
                    f"Clocked in successfully. You are {attendance.late_by_minutes} minutes late."
                )
            else:
                response_data["message"] = "Clocked in successfully."

            return JsonResponse(response_data)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Clock-in error: {str(e)}", exc_info=True)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)


@csrf_exempt
@login_required
def clock_out(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            lat = data.get("latitude")
            lng = data.get("longitude")
            force_clockout = data.get("force_clockout", False)  # Confirmation flag

            if not hasattr(request.user, "employee_profile"):
                return JsonResponse(
                    {"status": "error", "message": "No employee profile found"},
                    status=400,
                )

            employee = request.user.employee_profile
            today = timezone.localdate()

            try:
                attendance = Attendance.objects.get(employee=employee, date=today)

                # Check if shift is complete (unless forced)
                if not force_clockout and not attendance.is_shift_complete():
                    # Calculate completion percentage and remaining hours
                    if attendance.clock_in:
                        worked_hours = (
                            timezone.now() - attendance.clock_in
                        ).total_seconds() / 3600
                        expected_hours = attendance.get_shift_duration_hours()
                        completion_percentage = (worked_hours / expected_hours) * 100
                        remaining_hours = expected_hours - worked_hours

                        return JsonResponse(
                            {
                                "status": "confirmation_required",
                                "requires_confirmation": True,
                                "message": "Your shift is not completed yet. Are you sure you want to clock out?",
                                "worked_hours": round(worked_hours, 2),
                                "expected_hours": round(expected_hours, 2),
                                "completion_percentage": round(
                                    completion_percentage, 1
                                ),
                                "remaining_hours": round(remaining_hours, 2),
                            }
                        )

                # Process clock-out
                attendance.clock_out = timezone.now()
                attendance.location_out = f"{lat},{lng}"

                # Stop location tracking
                attendance.location_tracking_active = False

                # Calculate early departure based on shift
                attendance.calculate_early_departure()

                attendance.save()

                # Prepare response with early departure status
                response_data = {
                    "status": "success",
                    "time": attendance.clock_out.strftime("%H:%M:%S"),
                    "location_tracking_active": False,
                    "message": "Clocked out successfully.",
                }

                if attendance.is_early_departure:
                    response_data["is_early"] = True
                    response_data["early_by_minutes"] = (
                        attendance.early_departure_minutes
                    )
                    response_data["message"] = (
                        f"Clocked out. You left {attendance.early_departure_minutes} minutes early."
                    )

                return JsonResponse(response_data)
            except Attendance.DoesNotExist:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "No attendance record found for today",
                    }
                )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Clock-out error: {str(e)}", exc_info=True)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)


@csrf_exempt
@login_required
def update_location(request):
    """API endpoint to update employee's location (or log coordinates).
    Accepts POST JSON with either 'location_id' to set location, or 'latitude'/'longitude' to log coordinates.
    """
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Invalid method"}, status=405
        )
    try:
        data = json.loads(request.body)
        # Ensure employee profile exists
        if not hasattr(request.user, "employee_profile"):
            return JsonResponse(
                {"status": "error", "message": "No employee profile found"}, status=400
            )
        employee = request.user.employee_profile

        # Update location if provided
        location_id = data.get("location_id")
        if location_id:
            from companies.models import Location

            try:
                location = Location.objects.get(
                    id=location_id, company=employee.company
                )
                employee.location = location
                employee.save()
                return JsonResponse(
                    {"status": "success", "message": "Location updated"}
                )
            except Location.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": "Location not found"}, status=404
                )

        # Otherwise log latitude/longitude (only if tracking is active)
        lat = data.get("latitude")
        lng = data.get("longitude")
        if lat is not None and lng is not None:
            # Check if location tracking is active for today's attendance
            today = timezone.localdate()
            try:
                attendance = Attendance.objects.get(employee=employee, date=today)

                # Check if tracking should be stopped
                if attendance.should_stop_location_tracking():
                    attendance.location_tracking_active = False
                    attendance.save()
                    return JsonResponse(
                        {
                            "status": "tracking_stopped",
                            "message": "Location tracking stopped (shift duration completed)",
                            "location_tracking_active": False,
                        }
                    )

                # Only log if tracking is active
                if attendance.location_tracking_active:
                    LocationLog.objects.create(
                        employee=employee, latitude=lat, longitude=lng
                    )
                    return JsonResponse(
                        {
                            "status": "success",
                            "message": "Coordinates logged",
                            "location_tracking_active": True,
                        }
                    )
                else:
                    return JsonResponse(
                        {
                            "status": "tracking_inactive",
                            "message": "Location tracking is not active",
                            "location_tracking_active": False,
                        }
                    )

            except Attendance.DoesNotExist:
                # No attendance record, don't log location
                return JsonResponse(
                    {
                        "status": "no_attendance",
                        "message": "No attendance record found for today",
                        "location_tracking_active": False,
                    }
                )

        # Return 200 even if no data to prevent log spam
        return JsonResponse(
            {"status": "ignored", "message": "No valid data provided"}, status=200
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Update location error: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


from django.shortcuts import redirect
from .models import EmployeeIDProof


@login_required
def employee_profile(request):
    user = request.user

    # Try to get or create employee profile if User is a Company Admin/Manager
    # This prevents the "blank page" issue for the initial admin user.
    try:
        employee = user.employee_profile
    except Exception:
        employee = None

    if not employee:
        if user.company:
            # Auto-create basic profile for Admin/Manager to avoid UI block
            employee = Employee.objects.create(
                user=user,
                company=user.company,
                designation="Administrator"
                if user.role == User.Role.COMPANY_ADMIN
                else "Employee",
                department="Management",
                badge_id=f"ADM{user.id}",  # Simple fallback ID
            )
        else:
            # Fallback if no company (shouldn't happen for active users)
            # We must pass the 'content' block to a template that extends base.html
            return render(
                request,
                "core/general_message.html",
                {
                    "title": "Profile Not Found",
                    "message": "No employee profile found. Please contact your administrator.",
                },
            )

    id_proofs, created = EmployeeIDProof.objects.get_or_create(employee=employee)
    locations = employee.company.locations.all()

    if request.method == "POST":
        # Handle Profile Picture Upload
        if "profile_picture" in request.FILES:
            employee.profile_picture = request.FILES["profile_picture"]
            employee.save()
            return redirect("employee_profile")

        is_admin = request.user.role == User.Role.COMPANY_ADMIN

        # Helper to check if upload allowed
        def can_upload(current_file):
            return not current_file or is_admin

        if "aadhar_front" in request.FILES:
            if can_upload(id_proofs.aadhar_front):
                id_proofs.aadhar_front = request.FILES["aadhar_front"]

        if "aadhar_back" in request.FILES:
            if can_upload(id_proofs.aadhar_back):
                id_proofs.aadhar_back = request.FILES["aadhar_back"]

        if "pan_card" in request.FILES:
            if can_upload(id_proofs.pan_card):
                id_proofs.pan_card = request.FILES["pan_card"]

        id_proofs.save()

        # Deletion logic for Admins
        if is_admin:
            if request.POST.get("delete_aadhar_front") == "on":
                id_proofs.aadhar_front.delete(save=False)
                id_proofs.aadhar_front = None
            if request.POST.get("delete_aadhar_back") == "on":
                id_proofs.aadhar_back.delete(save=False)
                id_proofs.aadhar_back = None
            if request.POST.get("delete_pan_card") == "on":
                id_proofs.pan_card.delete(save=False)
                id_proofs.pan_card = None
            id_proofs.save()

        return redirect("employee_profile")

    # Get emergency contacts for this employee
    emergency_contacts = employee.emergency_contacts.all().order_by(
        "-is_primary", "created_at"
    )

    return render(
        request,
        "employees/employee_profile.html",
        {
            "employee": employee,
            "id_proofs": id_proofs,
            "is_admin": request.user.role == User.Role.COMPANY_ADMIN,
            "locations": locations,
            "emergency_contacts": emergency_contacts,
        },
    )


@login_required
def set_location(request):
    """Handle location update from personal details form."""
    if request.method != "POST":
        return redirect("employee_profile")
    location_id = request.POST.get("location_id")
    if not location_id:
        messages.error(request, "No location selected.")
        return redirect("employee_profile")
    try:
        from .models import Location

        location = Location.objects.get(id=location_id, company=request.user.company)
        employee = request.user.employee_profile
        employee.location = location
        employee.save()
        messages.success(request, f"Location updated to {location.name}.")
    except Location.DoesNotExist:
        messages.error(request, "Location not found.")
    except Exception as e:
        messages.error(request, f"Error updating location: {str(e)}")
    return redirect("employee_profile")


# --- Leave Management Views ---


class LeaveApplyView(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveApplicationForm
    template_name = "employees/leave_form.html"
    success_url = reverse_lazy("employee_profile")  # Or dashboard

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            employee = self.request.user.employee_profile
            if hasattr(employee, "leave_balance"):
                context["cl_balance"] = employee.leave_balance.casual_leave_balance
                context["el_balance"] = employee.leave_balance.earned_leave_balance
            else:
                context["cl_balance"] = 0
                context["el_balance"] = 0
        except Exception as e:
            # Fallback if something goes wrong (e.g. no profile)
            context["cl_balance"] = 0
            context["el_balance"] = 0
        return context

    def form_valid(self, form):
        form.instance.employee = self.request.user.employee_profile
        # Logic to check balance? Optional, but good practice.
        # We rely on 'is_negative_balance' property validation if we were strict,
        # but user requirement didn't specify strict blocking on balance, just 0.5 rules.
        response = super().form_valid(form)

        # Send email notifications
        send_leave_request_notification(self.object)

        return response


@login_required
def approve_leave(request, pk):
    if request.method == "POST":
        leave_request = LeaveRequest.objects.get(pk=pk)

        # Security check: Only Manager or Admin can approve
        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN
        is_manager = (
            user.role == User.Role.MANAGER and leave_request.employee.manager == user
        )

        if not (is_admin or is_manager):
            # For demo purposes, maybe looser? No, stick to roles.
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        leave_request.status = "APPROVED"
        leave_request.approved_by = user
        leave_request.approved_at = timezone.now()
        leave_request.save()

        # Deduct Balance
        balance = leave_request.employee.leave_balance
        days = leave_request.total_days

        if leave_request.leave_type == "CL":
            balance.casual_leave_used += days
        elif leave_request.leave_type == "SL":
            balance.sick_leave_used += days
        elif leave_request.leave_type == "EL":
            balance.earned_leave_used += days
        elif leave_request.leave_type == "CO":
            balance.comp_off_used += days
        elif leave_request.leave_type == "UL":
            balance.unpaid_leave += days

        balance.save()

        return redirect(request.META.get("HTTP_REFERER", "admin_dashboard"))
    return redirect("admin_dashboard")


@login_required
def reject_leave(request, pk):
    if request.method == "POST":
        leave_request = LeaveRequest.objects.get(pk=pk)

        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN
        is_manager = (
            user.role == User.Role.MANAGER and leave_request.employee.manager == user
        )

        if not (is_admin or is_manager):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        leave_request.status = "REJECTED"
        leave_request.rejection_reason = request.POST.get("rejection_reason", "")
        leave_request.approver = user  # Track who rejected
        leave_request.save()

        return redirect(request.META.get("HTTP_REFERER", "admin_dashboard"))
    return redirect("admin_dashboard")


@login_required
def attendance_map(request, pk):
    try:
        attendance = Attendance.objects.get(pk=pk)
        employee = attendance.employee

        # Permission Check
        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN
        is_manager = user.role == User.Role.MANAGER and user == employee.manager
        is_self = user == employee.user

        if not (is_admin or is_manager or is_self):
            messages.error(request, "Permission Denied")
            return redirect("dashboard")

        # Get logs within the attendance period
        logs = LocationLog.objects.filter(employee=employee)

        if attendance.clock_in:
            logs = logs.filter(timestamp__gte=attendance.clock_in)

        if attendance.clock_out:
            logs = logs.filter(timestamp__lte=attendance.clock_out)

        logs = logs.order_by("timestamp")

        # Prepare Map Data
        map_locations = []

        def parse_loc(loc_str):
            try:
                parts = loc_str.split(",")
                return float(parts[0]), float(parts[1])
            except:
                return None, None

        # 1. Clock In
        if attendance.location_in:
            lat, lng = parse_loc(attendance.location_in)
            if lat:
                map_locations.append(
                    {
                        "lat": lat,
                        "lng": lng,
                        "title": f"Clock In: {attendance.clock_in.strftime('%I:%M %p')}",
                        "type": "in",
                    }
                )

        # 2. Logs
        for log in logs:
            map_locations.append(
                {
                    "lat": float(log.latitude),
                    "lng": float(log.longitude),
                    "title": f"Log: {log.timestamp.strftime('%I:%M %p')}",
                    "type": "log",
                }
            )

        # 3. Clock Out
        if attendance.location_out:
            lat, lng = parse_loc(attendance.location_out)
            if lat:
                map_locations.append(
                    {
                        "lat": lat,
                        "lng": lng,
                        "title": f"Clock Out: {attendance.clock_out.strftime('%I:%M %p')}",
                        "type": "out",
                    }
                )

        return render(
            request,
            "core/attendance_map.html",
            {
                "attendance": attendance,
                "logs": logs,
                "map_data_json": map_locations,
                "title": "Location History",
            },
        )
    except Attendance.DoesNotExist:
        messages.error(request, "Attendance record not found")
        return redirect("dashboard")


@login_required
def employee_detail(request, pk):
    try:
        employee = Employee.objects.get(pk=pk)

        # Permission Check (Company Admin or Manager of the employee)
        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN
        is_manager = user.role == User.Role.MANAGER and employee.manager == user

        if not (is_admin or is_manager):
            messages.error(request, "Permission denied")
            return redirect("employee_list")

        today = timezone.localdate()

        # Date Filter (Default to current month)
        import calendar

        month = int(request.GET.get("month", today.month))
        year = int(request.GET.get("year", today.year))

        # Get start and end of month
        num_days = calendar.monthrange(year, month)[1]
        start_date = timezone.datetime(year, month, 1).date()
        end_date = timezone.datetime(year, month, num_days).date()

        # Fetch Attendance for the period
        attendance_qs = Attendance.objects.filter(
            employee=employee, date__range=[start_date, end_date]
        ).order_by("-date")

        # Calculate Stats
        total_days = attendance_qs.count()
        present = attendance_qs.filter(status="PRESENT").count()
        wfh = attendance_qs.filter(status="WFH").count()
        leave = attendance_qs.filter(status="LEAVE").count()
        absent = attendance_qs.filter(status="ABSENT").count()

        # Location Data for Map (Today's path or last active day)
        # We try to get today's attendance first
        map_date = today
        map_attendance = attendance_qs.filter(date=today).first()

        # If no attendance today, grab the last one with location data
        if not map_attendance or (
            not map_attendance.location_in and not map_attendance.location_out
        ):
            # Find last record with location
            last_loc_att = attendance_qs.exclude(location_in__isnull=True).first()
            if last_loc_att:
                map_attendance = last_loc_att
                map_date = last_loc_att.date

        map_data = []
        if map_attendance:
            # Parse Lat/Lng helper
            def parse_loc(loc_str):
                try:
                    parts = loc_str.split(",")
                    return float(parts[0]), float(parts[1])
                except:
                    return None, None

            # Clock In Marker
            if map_attendance.location_in:
                lat, lng = parse_loc(map_attendance.location_in)
                if lat:
                    map_data.append(
                        {
                            "lat": lat,
                            "lng": lng,
                            "title": f"Clock In ({map_attendance.clock_in.strftime('%H:%M')})",
                            "type": "start",
                        }
                    )

            # Logs (If we had a LocationLog model linked to attendance date/time, we'd query it here)
            # Query LocationLog for this employee on this date
            # Assuming LocationLog has a timestamp field
            if map_attendance.clock_in:
                day_start = timezone.make_aware(
                    timezone.datetime.combine(map_date, timezone.datetime.min.time())
                )
                day_end = timezone.make_aware(
                    timezone.datetime.combine(map_date, timezone.datetime.max.time())
                )

                logs = LocationLog.objects.filter(
                    employee=employee, timestamp__range=[day_start, day_end]
                ).order_by("timestamp")

                for log in logs:
                    map_data.append(
                        {
                            "lat": float(log.latitude),
                            "lng": float(log.longitude),
                            "title": f"Log: {log.timestamp.strftime('%H:%M')}",
                            "type": "log",
                        }
                    )

            # Clock Out Marker
            if map_attendance.location_out:
                lat, lng = parse_loc(map_attendance.location_out)
                if lat:
                    map_data.append(
                        {
                            "lat": lat,
                            "lng": lng,
                            "title": f"Clock Out ({map_attendance.clock_out.strftime('%H:%M')})",
                            "type": "end",
                        }
                    )

        context = {
            "employee": employee,
            "attendance_history": attendance_qs,
            "current_month": start_date.strftime("%B"),
            "current_year": year,
            "stats": {
                "total": total_days,
                "present": present,
                "wfh": wfh,
                "leave": leave,
                "absent": absent,
            },
            "map_data": json.dumps(map_data),
            "map_date": map_date,
        }
        return render(request, "employees/employee_detail.html", context)

    except Employee.DoesNotExist:
        messages.error(request, "Employee not found")
        return redirect("employee_list")


from django.views.decorators.http import require_http_methods
from django.contrib import messages


@csrf_exempt
@login_required
def employee_exit_action(request, pk):
    """
    Handle employee exit actions (Resignation, Absconding, Termination)
    - Resignation: Creates pending exit initiative, sends email to admin/manager
    - Absconding/Termination: Calculates last working day, disables login immediately
    Only accessible by Company Admin or Super Admin
    """
    from .models import ExitInitiative
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta

    # Permission check
    if request.user.role not in [User.Role.COMPANY_ADMIN, User.Role.SUPERADMIN]:
        return JsonResponse(
            {
                "status": "error",
                "message": "Permission denied. Only admins can perform exit actions.",
            },
            status=403,
        )

    try:
        employee = Employee.objects.get(pk=pk)

        # Prevent exiting already exited employees
        if not employee.is_active:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "This employee has already been exited from the organization.",
                },
                status=400,
            )

        # Get form data
        exit_type = request.POST.get("exit_type")  # RESIGNATION, ABSCONDED, TERMINATED
        submission_date_str = request.POST.get("submission_date")
        exit_note = request.POST.get("exit_note", "").strip()
        notice_period_days = request.POST.get("notice_period_days", "").strip()

        # Validation
        if not exit_type or exit_type not in ["RESIGNATION", "ABSCONDED", "TERMINATED"]:
            return JsonResponse(
                {"status": "error", "message": "Invalid exit type selected."},
                status=400,
            )

        if not submission_date_str:
            return JsonResponse(
                {"status": "error", "message": "Submission date is required."},
                status=400,
            )

        if not exit_note:
            return JsonResponse(
                {"status": "error", "message": "Exit reason/note is required."},
                status=400,
            )

        # Parse and validate date
        try:
            submission_date = timezone.datetime.strptime(
                submission_date_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            return JsonResponse(
                {"status": "error", "message": "Invalid date format."}, status=400
            )

        # Handle different exit types
        if exit_type == "RESIGNATION":
            # Create ExitInitiative with PENDING status
            exit_initiative = ExitInitiative.objects.create(
                employee=employee,
                exit_type=exit_type,
                submission_date=submission_date,
                exit_note=exit_note,
                status="PENDING",
            )

            # Update employee status but keep them active
            # Update employee status but keep them active
            employee.employment_status = exit_type
            employee.exit_note = exit_note
            # Don't set exit_date yet - will be set upon approval
            # Don't disable login - employee can work until last working day
            employee.save()

            # --- Email Notification ---
            try:
                from django.core.mail import send_mail
                from companies.models import Announcement

                # 1. Recipients
                recipients = []

                # Reporting Manager
                if employee.manager and employee.manager.user.email:
                    recipients.append(employee.manager.user.email)

                # HR/Admins
                company_admins = User.objects.filter(
                    company=employee.company, role="COMPANY_ADMIN"
                ).values_list("email", flat=True)
                recipients.extend(list(company_admins))

                # Company HR Email
                if employee.company.hr_email:
                    recipients.append(employee.company.hr_email)

                # Deduplicate
                recipients = list(set(filter(None, recipients)))

                if recipients:
                    subject = f"Resignation Submitted: {employee.user.get_full_name()} ({employee.designation})"
                    message = f"""
                    Dear Team,
                    
                    This is to inform you that {employee.user.get_full_name()} ({employee.designation}) has submitted their resignation on {submission_date.strftime("%d %b %Y")}.
                    
                    Reason:
                    {exit_note}
                    
                    Current Status: Pending Approval
                    
                    Please login to the HRMS portal to review and take necessary action.
                    
                    Regards,
                    HRMS System
                    """
                    send_mail(
                        subject,
                        message,
                        settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL,
                        recipients,
                        fail_silently=True,
                    )

                # --- Dashboard Announcement ---
                # Note: Announcements are visible to specific locations or company-wide.
                # Since we want it on the dashboard, we create a targeted announcement.
                # Limitation: Standard Announcement model is public.
                try:
                    Announcement.objects.create(
                        company=employee.company,
                        title=f"Resignation Alert: {employee.user.get_full_name()}",
                        content=f"Resignation submitted by {employee.user.get_full_name()} on {submission_date.strftime('%Y-%m-%d')}. Pending Approval.",
                        location=employee.location,  # Target to same location at least
                    )
                except Exception as e:
                    print(f"Error creating announcement: {e}")

            except Exception as e:
                print(f"Error in resignation notification: {e}")

            messages.success(
                request,
                f"Resignation request from {employee.user.get_full_name()} has been submitted for approval.",
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Resignation request submitted successfully. Awaiting approval.",
                    "redirect_url": reverse("employee_list"),
                }
            )

        elif exit_type in ["ABSCONDED", "TERMINATED"]:
            # Validate notice period
            if not notice_period_days:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Notice period (in days) is required for absconding/termination.",
                    },
                    status=400,
                )

            try:
                notice_period = int(notice_period_days)
                if notice_period < 0:
                    raise ValueError("Notice period cannot be negative")
            except ValueError:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Invalid notice period. Please enter a valid number of days.",
                    },
                    status=400,
                )

            # Calculate last working day
            last_working_day = submission_date + timedelta(days=notice_period)

            # Create ExitInitiative with APPROVED status (no approval needed)
            exit_initiative = ExitInitiative.objects.create(
                employee=employee,
                exit_type=exit_type,
                submission_date=submission_date,
                exit_note=exit_note,
                notice_period_days=notice_period,
                last_working_day=last_working_day,
                status="APPROVED",
                approved_by=request.user,
                approved_at=timezone.now(),
            )

            # Update employee record
            employee.employment_status = exit_type
            employee.exit_date = last_working_day
            employee.exit_note = exit_note

            # Check if exit is effective today/past or future
            today = timezone.localdate()
            is_immediate = last_working_day <= today

            if is_immediate:
                # Immediate Exit
                employee.is_active = False
                employee.save()

                # Disable user login immediately
                user = employee.user
                user.is_active = False
                user.save()

                action_msg = f"Employee {employee.user.get_full_name()} marked as {exit_type.lower()}. Access blocked immediately."
            else:
                # Future Exit
                # Keep active until that date
                employee.is_active = True
                employee.save()

                # Ensure user is active (in case they were blocked)
                user = employee.user
                user.is_active = True
                user.save()

                action_msg = f"Employee {employee.user.get_full_name()} marked as {exit_type.lower()}. Access will be blocked on {last_working_day.strftime('%d %b %Y')}."

            # TODO: Create announcement for last working day
            # create_exit_announcement(employee, exit_initiative)

            messages.success(request, action_msg)

            return JsonResponse(
                {
                    "status": "success",
                    "message": action_msg,
                    "redirect_url": reverse("employee_list"),
                }
            )

    except Employee.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Employee not found."}, status=404
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JsonResponse(
            {"status": "error", "message": f"An error occurred: {str(e)}"}, status=500
        )


@csrf_exempt
@login_required
def get_attendance_map_data(request, pk):
    try:
        attendance = Attendance.objects.get(pk=pk)

        # Permission check
        is_admin = (
            request.user.role == User.Role.COMPANY_ADMIN or request.user.is_superuser
        )

        # Safe manager check
        is_manager = False
        if request.user.role == User.Role.MANAGER and hasattr(
            request.user, "employee_profile"
        ):
            is_manager = attendance.employee.manager == request.user

        is_self = attendance.employee.user == request.user

        if not (is_admin or is_manager or is_self):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        map_locations = []

        def parse_loc(loc_str):
            try:
                parts = loc_str.split(",")
                return float(parts[0]), float(parts[1])
            except:
                return None, None

        # 1. Clock In
        if attendance.location_in:
            lat, lng = parse_loc(attendance.location_in)
            if lat:
                map_locations.append(
                    {
                        "lat": lat,
                        "lng": lng,
                        "title": f"Clock In: {attendance.clock_in.strftime('%I:%M %p')}",
                        "time_display": attendance.clock_in.strftime("%I:%M %p"),
                        "type": "start",
                        "type_display": "Clock In",
                    }
                )

        # 2. Logs
        if attendance.clock_in:
            # Determine end time for log query (clock_out or now)
            end_time = attendance.clock_out if attendance.clock_out else timezone.now()

            logs = LocationLog.objects.filter(
                employee=attendance.employee,
                timestamp__gte=attendance.clock_in,
                timestamp__lte=end_time,
            ).order_by("timestamp")

            for log in logs:
                map_locations.append(
                    {
                        "lat": float(log.latitude),
                        "lng": float(log.longitude),
                        "title": f"Log: {log.timestamp.strftime('%I:%M %p')}",
                        "time_display": log.timestamp.strftime("%I:%M %p"),
                        "type": "log",
                        "type_display": "Location Log",
                    }
                )

        # 3. Clock Out
        if attendance.location_out:
            lat, lng = parse_loc(attendance.location_out)
            if lat:
                map_locations.append(
                    {
                        "lat": lat,
                        "lng": lng,
                        "title": f"Clock Out: {attendance.clock_out.strftime('%I:%M %p')}",
                        "time_display": attendance.clock_out.strftime("%I:%M %p"),
                        "type": "end",
                        "type_display": "Clock Out",
                    }
                )

        # Sort by type to ensure logical connecting line (Start -> Logs -> End) is somewhat respected,
        # OR better: if we have timestamps for all events, sort by them.
        # But `map_locations` does not store raw datetime objects right now.
        # Let's rely on the current append order: Start -> Logs -> End. This assumes Logs are between Start and End.
        # This is generally true.

        return JsonResponse({"status": "success", "data": map_locations})

    except Attendance.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Attendance not found"}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


class BulkEmployeeImportView(LoginRequiredMixin, CompanyAdminRequiredMixin, FormView):
    template_name = "employees/bulk_import.html"
    form_class = EmployeeBulkImportForm
    success_url = reverse_lazy("employee_list")

    def form_valid(self, form):
        import pandas as pd
        from django.contrib import messages
        from .utils import send_activation_email

        file = form.cleaned_data["import_file"]
        try:
            # Read Excel
            try:
                df = pd.read_excel(file)
            except Exception as e:
                messages.error(self.request, f"Error reading Excel file: {str(e)}")
                return self.form_invalid(form)

            # Normalize columns
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

            # DOJ and DOB are now mandatory
            required_columns = [
                "first_name",
                "last_name",
                "email",
                "designation",
                "department",
                "date_of_joining",
                "date_of_birth",
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                messages.error(
                    self.request,
                    f"Missing required columns: {', '.join(missing_columns)}",
                )
                return self.form_invalid(form)

            success_count = 0
            errors = []

            for index, row in df.iterrows():
                try:
                    with transaction.atomic():
                        # 1. Basic Data
                        email = str(row.get("email", "")).strip()
                        if not email:
                            raise ValueError("Email is required")

                        if User.objects.filter(email=email).exists():
                            # Skip existing users
                            raise ValueError(f"User with email {email} already exists")

                        first_name = str(row.get("first_name", "")).strip()
                        last_name = str(row.get("last_name", "")).strip()

                        # 2. Create User (Unusable password for activation)
                        user = User.objects.create_user(
                            username=email,
                            email=email,
                            password=None,
                            first_name=first_name,
                            last_name=last_name,
                            role="EMPLOYEE",
                            company=self.request.user.company,
                        )
                        user.set_unusable_password()
                        user.save()

                        # 3. Parse Dates
                        doj = row.get("date_of_joining")
                        if pd.isna(doj):
                            raise ValueError("Date of Joining is mandatory")
                        elif hasattr(doj, "date"):
                            doj = doj.date()
                        else:
                            # Try parsing string
                            doj = pd.to_datetime(doj).date()

                        dob = row.get("date_of_birth")
                        if pd.isna(dob):
                            raise ValueError("Date of Birth is mandatory")
                        elif hasattr(dob, "date"):
                            dob = dob.date()
                        else:
                            # Try parsing string
                            dob = pd.to_datetime(dob).date()

                        # 4. Parse Location
                        from companies.models import Location

                        location_name = str(row.get("location", "")).strip()
                        location = None
                        if location_name:
                            location = Location.objects.filter(
                                company=self.request.user.company,
                                name__iexact=location_name,
                            ).first()

                        # Fallback location
                        if not location:
                            location = Location.objects.filter(
                                company=self.request.user.company
                            ).first()

                        # 5. Create Employee
                        badge_id = str(row.get("badge_id", ""))
                        if badge_id == "nan":
                            badge_id = None
                        elif badge_id.endswith(".0"):
                            badge_id = badge_id[:-2]  # 101.0 -> 101

                        employee = Employee.objects.create(
                            user=user,
                            company=self.request.user.company,
                            designation=str(row.get("designation", "Employee")),
                            department=str(row.get("department", "General")),
                            location=location,
                            badge_id=badge_id,
                            mobile_number=str(row.get("mobile", ""))
                            if not pd.isna(row.get("mobile"))
                            else None,
                            gender=str(row.get("gender", "M"))[0].upper(),
                            marital_status=str(row.get("marital_status", "S"))[
                                0
                            ].upper(),
                            date_of_joining=doj,
                            dob=dob,
                            annual_ctc=row.get("annual_ctc")
                            if not pd.isna(row.get("annual_ctc"))
                            else 0,
                        )

                        # 6. Create Leave Balance (Default)
                        LeaveBalance.objects.create(employee=employee)

                        # 7. Send Activation Email
                        send_activation_email(user, self.request)

                        success_count += 1

                except Exception as e:
                    errors.append(
                        f"Row {index + 2} ({row.get('email', 'Unknown')}): {str(e)}"
                    )

            if success_count > 0:
                messages.success(
                    self.request,
                    f"Successfully created {success_count} employees. Activation emails sent.",
                )

            if errors:
                # Show first 5 errors
                error_msg = "Errors occurred:<br>" + "<br>".join(errors[:5])
                if len(errors) > 5:
                    error_msg += f"<br>...and {len(errors) - 5} more."
                messages.warning(self.request, error_msg)

            return super().form_valid(form)

        except Exception as e:
            messages.error(self.request, f"System Error: {str(e)}")
            return self.form_invalid(form)


@login_required
def download_sample_import_file(request):
    """
    Downloads a sample Excel file for bulk employee import.
    """
    import pandas as pd
    from django.http import HttpResponse

    # Define columns
    columns = [
        "First Name",
        "Last Name",
        "Email",
        "Designation",
        "Department",
        "Mobile",
        "Date of Joining",
        "Date of Birth",
        "Badge ID",
        "Gender",
        "Marital Status",
        "Annual CTC",
        "Location",
    ]

    # Create empty DataFrame
    df = pd.DataFrame(columns=columns)

    # Add a dummy row to guide user
    dummy_data = {
        "First Name": "John",
        "Last Name": "Doe",
        "Email": "john.doe@example.com",
        "Designation": "Software Engineer",
        "Department": "IT",
        "Mobile": "9876543210",
        "Date of Joining": "2025-01-01",
        "Date of Birth": "1990-05-15",
        "Badge ID": "E001",
        "Gender": "M",
        "Marital Status": "S",
        "Annual CTC": 1200000,
        "Location": "Head Office",
    }
    df = pd.concat([df, pd.DataFrame([dummy_data])], ignore_index=True)

    # Create response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        "attachment; filename=employee_bulk_import_sample.xlsx"
    )

    try:
        # Use openpyxl engine
        df.to_excel(response, index=False, engine="openpyxl")
    except ImportError:
        # Fallback if openpyxl missing
        return HttpResponse(
            "Error: openpyxl library not found. Please contact admin to install it.",
            status=500,
        )
    except Exception as e:
        return HttpResponse(f"Error generating file: {str(e)}", status=500)

    return response


# --- Regularization Views ---


class RegularizationCreateView(LoginRequiredMixin, CreateView):
    model = RegularizationRequest
    form_class = RegularizationRequestForm
    template_name = "employees/regularization_form.html"
    success_url = reverse_lazy("regularization_list")  # Redirect to list or profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass user's regularizations to show history on same page if needed
        if hasattr(self.request.user, "employee_profile"):
            context["history"] = RegularizationRequest.objects.filter(
                employee=self.request.user.employee_profile
            )
        return context

    def form_valid(self, form):
        if not hasattr(self.request.user, "employee_profile"):
            form.add_error(None, "You do not have an employee profile.")
            return self.form_invalid(form)

        form.instance.employee = self.request.user.employee_profile
        response = super().form_valid(form)

        # Send Email Notification using the new utility
        try:
            from core.email_utils import send_regularization_request_notification

            send_regularization_request_notification(self.object)
        except Exception as e:
            print(f"Error sending regularization email: {e}")

        return response

    def get_success_url(self):
        # If admin/manager, maybe go to list, if employee go to profile/home
        return reverse_lazy(
            "personal_home"
        )  # Or wherever "My Regularizations" are shown


class RegularizationListView(LoginRequiredMixin, ListView):
    model = RegularizationRequest
    template_name = "employees/regularization_list.html"
    context_object_name = "requests"
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = RegularizationRequest.objects.all()

        if user.role == User.Role.COMPANY_ADMIN:
            return qs.filter(employee__company=user.company)
        elif user.role == User.Role.MANAGER:
            # Show requests from subordinates
            return qs.filter(employee__manager=user)
        else:
            # Employees see their own
            try:
                return qs.filter(employee=user.employee_profile)
            except:
                return qs.none()


@login_required
def approve_regularization(request, pk):
    if request.method == "POST":
        reg_request = RegularizationRequest.objects.get(pk=pk)

        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN
        is_manager = (
            user.role == User.Role.MANAGER and reg_request.employee.manager == user
        )

        if not (is_admin or is_manager):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        # Approve
        reg_request.status = "APPROVED"
        reg_request.approved_by = user
        reg_request.approved_at = timezone.now()
        reg_request.manager_comment = request.POST.get("manager_comment", "")
        reg_request.save()

        # Update Attendance
        # We need to find or create the attendance record for that date
        attendance, created = Attendance.objects.get_or_create(
            employee=reg_request.employee, date=reg_request.date
        )

        if reg_request.check_in:
            # We need to combine date with time
            attendance.clock_in = timezone.make_aware(
                timezone.datetime.combine(reg_request.date, reg_request.check_in)
            )

        if reg_request.check_out:
            attendance.clock_out = timezone.make_aware(
                timezone.datetime.combine(reg_request.date, reg_request.check_out)
            )

        # Update status to Present if not already (or whatever logic user wants, implicitly if regulating, they were present)
        attendance.status = "PRESENT"

        # Re-calc late/early
        attendance.calculate_late_arrival()
        attendance.calculate_early_departure()

        attendance.save()

        return redirect(request.META.get("HTTP_REFERER", "regularization_list"))

    return redirect("regularization_list")


@login_required
def reject_regularization(request, pk):
    if request.method == "POST":
        reg_request = RegularizationRequest.objects.get(pk=pk)

        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN
        is_manager = (
            user.role == User.Role.MANAGER and reg_request.employee.manager == user
        )

        if not (is_admin or is_manager):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        reg_request.status = "REJECTED"
        reg_request.manager_comment = request.POST.get(
            "rejection_reason", ""
        )  # Use manager_comment for rejection reason
        reg_request.save()

        return redirect(request.META.get("HTTP_REFERER", "regularization_list"))

    return redirect("regularization_list")


# --- Leave Configuration ---


@login_required
def leave_configuration(request):
    from django.contrib import messages

    user = request.user
    if user.role not in [User.Role.COMPANY_ADMIN, User.Role.MANAGER]:
        messages.error(request, "Permission Denied")
        return redirect("dashboard")

    company = user.company

    # Manager sees team, Admin sees all
    if user.role == User.Role.MANAGER:
        employees = Employee.objects.filter(manager=user)
    else:
        employees = Employee.objects.filter(company=company)

    # Prefetch leave balances and user for names
    employees = employees.select_related("leave_balance", "user").order_by(
        "user__first_name"
    )

    return render(
        request, "employees/leave_configuration.html", {"employees": employees}
    )


@csrf_exempt
@login_required
def update_leave_balance(request, pk):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Invalid method"}, status=405
        )

    user = request.user
    if user.role not in [User.Role.COMPANY_ADMIN, User.Role.MANAGER]:
        return JsonResponse(
            {"status": "error", "message": "Permission Denied"}, status=403
        )

    try:
        employee = Employee.objects.get(pk=pk)
        # Verify access rights
        if user.role == User.Role.MANAGER and employee.manager != user:
            return JsonResponse(
                {"status": "error", "message": "Permission Denied"}, status=403
            )

        if user.role == User.Role.COMPANY_ADMIN and employee.company != user.company:
            return JsonResponse(
                {"status": "error", "message": "Permission Denied"}, status=403
            )

        balance = employee.leave_balance

        # Get data
        data = json.loads(request.body)
        sick_allocated = data.get("sick_leave_allocated")
        casual_allocated = data.get("casual_leave_allocated")

        if sick_allocated is not None:
            # Handle empty strings or invalid input gracefully
            try:
                balance.sick_leave_allocated = float(sick_allocated)
            except ValueError:
                pass  # Ignore invalid

        if casual_allocated is not None:
            try:
                balance.casual_leave_allocated = float(casual_allocated)
            except ValueError:
                pass

        balance.save()

        return JsonResponse(
            {"status": "success", "message": "Balance updated successfully"}
        )

    except Employee.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Employee not found"}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def run_monthly_accrual(request):
    from django.contrib import messages

    user = request.user
    if user.role not in [User.Role.COMPANY_ADMIN, User.Role.MANAGER]:
        messages.error(request, "Permission Denied")
        return redirect("leave_configuration")

    from django.core.management import call_command

    try:
        # Run the command
        # Capture stdout to log if needed, or just let it run
        call_command("accrue_monthly_leaves")
        messages.success(
            request,
            "Monthly accrual processed: +1 Sick and +1 Casual leave added to all employees.",
        )
    except Exception as e:
        messages.error(request, f"Error running accrual: {str(e)}")

    return redirect("leave_configuration")


# --- ID Proof Management Views ---


@login_required
def employee_id_proofs(request, pk):
    """
    View and manage employee ID proofs.
    Admin has full access (view, edit, delete, upload).
    Employee can only upload if not already uploaded.
    """
    try:
        employee = Employee.objects.get(pk=pk)

        # Permission Check
        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN
        is_self = (
            hasattr(user, "employee_profile") and user.employee_profile == employee
        )

        if not (is_admin or is_self):
            messages.error(request, "Permission denied")
            return redirect("employee_list")

        # Get or create ID proofs
        id_proofs, created = EmployeeIDProof.objects.get_or_create(employee=employee)

        if request.method == "POST":
            action = request.POST.get("action")

            # Upload functionality
            if action == "upload":
                # Helper to check if upload allowed
                def can_upload(current_file):
                    return not current_file or is_admin

                uploaded = False

                if "aadhar_front" in request.FILES:
                    if can_upload(id_proofs.aadhar_front):
                        id_proofs.aadhar_front = request.FILES["aadhar_front"]
                        uploaded = True
                    else:
                        messages.warning(
                            request,
                            "Aadhar Front already uploaded. Only admin can replace.",
                        )

                if "aadhar_back" in request.FILES:
                    if can_upload(id_proofs.aadhar_back):
                        id_proofs.aadhar_back = request.FILES["aadhar_back"]
                        uploaded = True
                    else:
                        messages.warning(
                            request,
                            "Aadhar Back already uploaded. Only admin can replace.",
                        )

                if "pan_card" in request.FILES:
                    if can_upload(id_proofs.pan_card):
                        id_proofs.pan_card = request.FILES["pan_card"]
                        uploaded = True
                    else:
                        messages.warning(
                            request,
                            "PAN Card already uploaded. Only admin can replace.",
                        )

                if uploaded:
                    id_proofs.save()
                    messages.success(request, "ID proof(s) uploaded successfully!")

            # Delete functionality (Admin only)
            elif action == "delete" and is_admin:
                delete_type = request.POST.get("delete_type")

                if delete_type == "aadhar_front" and id_proofs.aadhar_front:
                    id_proofs.aadhar_front.delete(save=False)
                    id_proofs.aadhar_front = None
                    messages.success(request, "Aadhar Front deleted successfully!")

                elif delete_type == "aadhar_back" and id_proofs.aadhar_back:
                    id_proofs.aadhar_back.delete(save=False)
                    id_proofs.aadhar_back = None
                    messages.success(request, "Aadhar Back deleted successfully!")

                elif delete_type == "pan_card" and id_proofs.pan_card:
                    id_proofs.pan_card.delete(save=False)
                    id_proofs.pan_card = None
                    messages.success(request, "PAN Card deleted successfully!")

                id_proofs.save()

            return redirect("employee_id_proofs", pk=pk)

        context = {
            "employee": employee,
            "id_proofs": id_proofs,
            "is_admin": is_admin,
            "is_self": is_self,
        }

        return render(request, "employees/employee_id_proofs.html", context)

    except Employee.DoesNotExist:
        messages.error(request, "Employee not found")
        return redirect("employee_list")


# Emergency Contact Management Views


@login_required
@require_http_methods(["POST"])
def add_emergency_contact(request):
    """
    AJAX endpoint to add a new emergency contact
    """
    try:
        employee = request.user.employee_profile

        from .forms import EmergencyContactForm

        form = EmergencyContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.employee = employee
            contact.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Emergency contact added successfully",
                    "contact": {
                        "id": contact.id,
                        "name": contact.name,
                        "phone_number": contact.phone_number,
                        "relationship": contact.relationship,
                        "is_primary": contact.is_primary,
                    },
                }
            )
        else:
            return JsonResponse(
                {"status": "error", "message": "Invalid data", "errors": form.errors},
                status=400,
            )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def delete_emergency_contact(request, contact_id):
    """
    AJAX endpoint to delete an emergency contact
    """
    try:
        employee = request.user.employee_profile
        from .models import EmergencyContact

        contact = EmergencyContact.objects.get(id=contact_id, employee=employee)
        contact.delete()

        return JsonResponse(
            {"status": "success", "message": "Emergency contact deleted successfully"}
        )
    except EmergencyContact.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Contact not found"}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def update_emergency_contact(request, contact_id):
    """
    AJAX endpoint to update an emergency contact
    """
    try:
        employee = request.user.employee_profile
        from .models import EmergencyContact
        from .forms import EmergencyContactForm

        contact = EmergencyContact.objects.get(id=contact_id, employee=employee)

        form = EmergencyContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Emergency contact updated successfully",
                    "contact": {
                        "id": contact.id,
                        "name": contact.name,
                        "phone_number": contact.phone_number,
                        "relationship": contact.relationship,
                        "is_primary": contact.is_primary,
                    },
                }
            )
        else:
            return JsonResponse(
                {"status": "error", "message": "Invalid data", "errors": form.errors},
                status=400,
            )
    except EmergencyContact.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Contact not found"}, status=404
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
