from django.conf import settings
from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db import transaction
from datetime import timedelta
from .models import (
    Employee,
    Attendance,
    AttendanceSession,
    LocationLog,
    LeaveRequest,
    LeaveBalance,
    RegularizationRequest,
)
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
from django.contrib import messages
from timezonefinder import TimezoneFinder
from loguru import logger
from core.error_handling import (
    safe_get_employee_profile,
    safe_queryset_filter,
    safe_parse_location,
    capture_exception,
)
from .location_tracking_views import (
    submit_hourly_location,
    get_location_tracking_status,
    get_employee_location_history,
)


def detect_timezone_from_coordinates(lat, lng):
    """
    Detect timezone from latitude and longitude coordinates
    """
    try:
        tf = TimezoneFinder()
        timezone_name = tf.timezone_at(lat=float(lat), lng=float(lng))
        return timezone_name if timezone_name else "Asia/Kolkata"
    except Exception as e:
        logger.warning("Error detecting timezone", lat=lat, lng=lng, error=str(e))
        return "Asia/Kolkata"


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
            queryset = safe_queryset_filter(Employee, user=user)

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
            all_employees = safe_queryset_filter(Employee, user=user)

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
                except Exception as e:
                    logger.warning(
                        "Failed to delete emergency contact",
                        contact_id=contact_id,
                        error=str(e),
                    )

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

    @transaction.atomic
    def form_valid(self, form):
        """
        Perform complete permanent deletion of employee and all related data.
        This mimics Keka's permanent delete functionality.
        """
        from django.shortcuts import redirect
        from django.contrib import messages

        employee = self.get_object()
        employee_name = employee.user.get_full_name() if employee.user else "Employee"

        try:
            # Log the deletion for audit purposes
            logger.info(
                f"Permanent deletion initiated for employee: {employee_name} (ID: {employee.id})",
                user=self.request.user.email,
            )

            # Delete all related data in the correct order to avoid foreign key constraints

            # 1. Delete Attendance Sessions and Location Logs
            if hasattr(employee, "attendances"):
                for attendance in employee.attendances.all():
                    # Delete session location logs
                    if hasattr(attendance, "sessions"):
                        for session in attendance.sessions.all():
                            # Delete session-specific location logs
                            if hasattr(session, "location_logs"):
                                session.location_logs.all().delete()
                            session.delete()
                    attendance.delete()

            # 2. Delete Location Logs (general)
            if hasattr(employee, "location_logs"):
                employee.location_logs.all().delete()

            # 3. Delete Leave Requests
            if hasattr(employee, "leave_requests"):
                employee.leave_requests.all().delete()

            # 4. Delete Leave Balances
            if hasattr(employee, "leave_balances"):
                employee.leave_balances.all().delete()

            # 5. Delete Regularization Requests
            if hasattr(employee, "regularization_requests"):
                employee.regularization_requests.all().delete()

            # 6. Delete Emergency Contacts
            if hasattr(employee, "emergency_contacts"):
                employee.emergency_contacts.all().delete()

            # 7. Delete ID Proofs
            if hasattr(employee, "id_proofs"):
                try:
                    employee.id_proofs.delete()
                except Exception as e:
                    logger.warning(f"Error deleting ID proofs: {e}")

            # 8. Delete the User account (this will cascade delete the Employee due to CASCADE)
            user = employee.user
            if user:
                user_email = user.email
                user.delete()  # This will also delete the employee due to CASCADE
                logger.info(f"Successfully deleted user account: {user_email}")
            else:
                # If no user exists, delete employee directly
                employee.delete()
                logger.info(f"Successfully deleted employee: {employee_name}")

            # Success message
            messages.success(
                self.request,
                f"Employee '{employee_name}' and all associated data have been permanently deleted.",
            )

            logger.info(f"Permanent deletion completed for: {employee_name}")

        except Exception as e:
            logger.error(f"Error during permanent deletion: {str(e)}", exc_info=True)
            messages.error(self.request, f"An error occurred during deletion: {str(e)}")

        return redirect(self.success_url)


@login_required
def resend_welcome_email(request, pk):
    """
    Resend welcome email with activation link to the employee.
    """
    if request.user.role != User.Role.COMPANY_ADMIN:
        messages.error(request, "Permission denied.")
        return redirect("employee_list")

    try:
        employee = Employee.objects.get(pk=pk, company=request.user.company)
        from core.email_utils import send_welcome_email_with_link

        domain = request.get_host()
        if send_welcome_email_with_link(employee, domain):
            messages.success(request, f"Welcome email resent to {employee.user.email}")
        else:
            messages.error(
                request, "Failed to send email. Please check email settings."
            )

    except Employee.DoesNotExist:
        messages.error(request, "Employee not found.")

    return redirect("employee_list")


# --- Attendance & Tracking Views ---


@csrf_exempt
@login_required
def clock_in(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            lat = data.get("latitude")
            lng = data.get("longitude")
            accuracy = data.get("accuracy")
            clock_in_type = data.get("type", "office")  # 'office' or 'remote'

            # Ensure employee profile exists
            if not hasattr(request.user, "employee_profile"):
                # Auto-create for Company Admin to prevent setup deadlock
                if (
                    request.user.role == User.Role.COMPANY_ADMIN
                    and request.user.company
                ):
                    from .models import Employee

                    try:
                        Employee.objects.create(
                            user=request.user,
                            company=request.user.company,
                            designation="Administrator",
                            department="Management",
                            badge_id=f"ADM{request.user.id}",
                        )
                        # Refresh user to get the profile
                        request.user.refresh_from_db()
                    except Exception as e:
                        logger.error(f"Failed to auto-create profile in clock-in: {e}")
                        return JsonResponse(
                            {
                                "status": "error",
                                "message": "No employee profile found. Please contact support.",
                            },
                            status=400,
                        )
                else:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "No employee profile found. Please set up your profile first.",
                        },
                        status=400,
                    )

            employee = request.user.employee_profile
            today = timezone.localdate()

            # Get or create attendance record for today
            attendance, created = Attendance.objects.get_or_create(
                employee=employee,
                date=today,
                defaults={
                    "status": "ABSENT",
                    "daily_sessions_count": 0,
                    "is_currently_clocked_in": False,
                },
            )

            # Check if employee can clock in
            # FORCE OVERRIDE: Allow up to 3 sessions/day regardless of model setting (user request)
            MAX_ALLOWED_SESSIONS = 3

            if not attendance.can_clock_in():
                if attendance.is_currently_clocked_in:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "You are already clocked in. Please clock out first.",
                            "already_clocked_in": True,
                        }
                    )
                # Use loose check instead of strict model field check
                elif attendance.daily_sessions_count >= MAX_ALLOWED_SESSIONS:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": f"Maximum {MAX_ALLOWED_SESSIONS} sessions per day reached.",
                        }
                    )

            # Ensure model reflects this override if needed
            if attendance.max_daily_sessions < MAX_ALLOWED_SESSIONS:
                attendance.max_daily_sessions = MAX_ALLOWED_SESSIONS

            # Get timezone from request data or detect from coordinates
            user_timezone = data.get("timezone")

            if not user_timezone:
                # Try to detect timezone from coordinates
                user_timezone = detect_timezone_from_coordinates(lat, lng)

            if not user_timezone:
                # Fallback to employee location timezone
                if employee.location and hasattr(employee.location, "timezone"):
                    user_timezone = employee.location.timezone
                else:
                    user_timezone = "Asia/Kolkata"

            # Determine session type and status
            session_type = "WEB" if clock_in_type == "office" else "REMOTE"

            # Use database transaction to prevent race conditions
            from django.db import transaction

            try:
                with transaction.atomic():
                    # Refresh attendance from database to get latest state
                    attendance.refresh_from_db()

                    # Create new session with proper session number
                    session_number = attendance.daily_sessions_count + 1

                    # Check if session already exists (race condition protection)
                    existing_session = AttendanceSession.objects.filter(
                        employee=employee, date=today, session_number=session_number
                    ).first()

                    if existing_session:
                        return JsonResponse(
                            {
                                "status": "error",
                                "message": "Session already exists. Please refresh the page.",
                            }
                        )

                    session = AttendanceSession.objects.create(
                        employee=employee,
                        date=today,
                        session_number=session_number,
                        clock_in=timezone.now(),
                        session_type=session_type,
                        clock_in_latitude=lat if lat is not None else None,
                        clock_in_longitude=lng if lng is not None else None,
                        is_active=True,
                    )

                    # Log clock-in location only if coordinates are available
                    if lat is not None and lng is not None:
                        LocationLog.objects.create(
                            employee=employee,
                            attendance_session=session,
                            latitude=lat,
                            longitude=lng,
                            accuracy=accuracy
                            if accuracy is not None
                            else 9999,  # Use high value for unknown accuracy
                            log_type="CLOCK_IN",
                            is_valid=True,
                        )
                    else:
                        # Log with null coordinates to track that location was unavailable
                        logger.warning(
                            f"Clock-in without location data for {employee.user.get_full_name()}"
                        )

                    # Update attendance record
                    attendance.daily_sessions_count = session_number
                    attendance.is_currently_clocked_in = True
                    attendance.current_session_type = session_type
                    attendance.user_timezone = user_timezone

                    # Set first clock-in of the day
                    if not attendance.clock_in:
                        attendance.clock_in = session.clock_in
                        attendance.location_in = (
                            f"{lat},{lng}"
                            if lat is not None and lng is not None
                            else "N/A"
                        )

                    # Determine overall status
                    if session_number == 1:
                        attendance.status = (
                            "WFH" if session_type == "REMOTE" else "PRESENT"
                        )
                    else:
                        # Multiple sessions - check if mixed types
                        session_types = set(
                            AttendanceSession.objects.filter(
                                employee=employee, date=today
                            ).values_list("session_type", flat=True)
                        )
                        if len(session_types) > 1:
                            attendance.status = "HYBRID"
                        else:
                            attendance.status = (
                                "WFH" if session_type == "REMOTE" else "PRESENT"
                            )

                    # Start location tracking
                    attendance.location_tracking_active = True

                    # Calculate location tracking end time based on shift duration
                    shift = employee.assigned_shift
                    if shift:
                        if hasattr(shift, "get_shift_duration_timedelta"):
                            shift_duration = shift.get_shift_duration_timedelta()
                        else:
                            from datetime import datetime, timedelta

                            today_date = timezone.localdate()
                            s_start = datetime.combine(today_date, shift.start_time)
                            s_end = datetime.combine(today_date, shift.end_time)
                            if s_end < s_start:
                                s_end += timedelta(days=1)
                            shift_duration = s_end - s_start

                        attendance.location_tracking_end_time = (
                            session.clock_in + shift_duration
                        )
                    else:
                        # Default to 9 hours if no shift assigned
                        from datetime import timedelta

                        attendance.location_tracking_end_time = (
                            session.clock_in + timedelta(hours=9)
                        )

                    # Calculate late arrival for first session only
                    if session_number == 1:
                        attendance.calculate_late_arrival()

                    attendance.save()

            except Exception as db_error:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Database error: {str(db_error)}. Please try again.",
                    },
                    status=500,
                )
                if len(session_types) > 1:
                    attendance.status = "HYBRID"
                else:
                    attendance.status = "WFH" if session_type == "REMOTE" else "PRESENT"

            # Start location tracking
            attendance.location_tracking_active = True

            # Calculate location tracking end time based on shift duration
            shift = employee.assigned_shift
            attendance.location_tracking_end_time = None

            if shift and shift.start_time and shift.end_time:
                try:
                    if hasattr(shift, "get_shift_duration_timedelta"):
                        shift_duration = shift.get_shift_duration_timedelta()
                    else:
                        from datetime import datetime, timedelta

                        today_date = timezone.localdate()
                        s_start = datetime.combine(today_date, shift.start_time)
                        s_end = datetime.combine(today_date, shift.end_time)
                        if s_end < s_start:
                            s_end += timedelta(days=1)
                        shift_duration = s_end - s_start

                    attendance.location_tracking_end_time = (
                        session.clock_in + shift_duration
                    )
                except Exception as e:
                    logger.warning(
                        f"Error calculating shift duration for {employee}: {e}.Using default 9h."
                    )

            if not attendance.location_tracking_end_time:
                # Default to 9 hours if no shift assigned or error occurred
                from datetime import timedelta

                attendance.location_tracking_end_time = session.clock_in + timedelta(
                    hours=9
                )

            # Calculate late arrival for first session only
            if session_number == 1:
                attendance.calculate_late_arrival()

            attendance.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Successfully clocked in for session {session_number} ({session_type.lower()})",
                    "session_number": session_number,
                    "session_type": session_type,
                    "clock_in_time": session.clock_in.strftime("%H:%M:%S"),
                    "total_sessions_today": attendance.daily_sessions_count,
                    "max_sessions": attendance.max_daily_sessions,
                }
            )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Clock-in error: {str(e)}", exc_info=True)
            print(f"Clock-in error: {str(e)}")
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
            accuracy = data.get("accuracy")
            force_clockout = data.get("force_clockout", False)

            if not hasattr(request.user, "employee_profile"):
                return JsonResponse(
                    {"status": "error", "message": "No employee profile found"},
                    status=400,
                )

            employee = request.user.employee_profile
            today = timezone.localdate()

            try:
                attendance = Attendance.objects.get(employee=employee, date=today)

                # Check if currently clocked in
                if not attendance.is_currently_clocked_in:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "You are not currently clocked in.",
                        }
                    )

                # Get current active session
                current_session = attendance.get_current_session()
                print(f"DEBUG: Clock-out attempt by {employee.user.get_full_name()}")
                print(
                    f"DEBUG: Attendance is_currently_clocked_in: {attendance.is_currently_clocked_in}"
                )
                print(f"DEBUG: Current session found: {current_session}")
                if current_session:
                    print(
                        f"DEBUG: Session details - Number: {current_session.session_number}, Type: {current_session.session_type}"
                    )

                if not current_session:
                    return JsonResponse(
                        {
                            "status": "error",
                            "message": "No active session found.",
                        }
                    )

                # Check if shift is complete (unless forced)
                if not force_clockout and current_session.clock_in:
                    worked_hours = (
                        timezone.now() - current_session.clock_in
                    ).total_seconds() / 3600
                    expected_hours = 9.0  # Default 9 hours shift

                    if worked_hours < expected_hours:
                        completion_percentage = (worked_hours / expected_hours) * 100
                        remaining_hours = expected_hours - worked_hours

                        return JsonResponse(
                            {
                                "status": "confirmation_required",
                                "requires_confirmation": True,
                                "message": f"Your {int(expected_hours)}-hour shift is not completed yet. Do you want to clock out?",
                                "worked_hours": round(worked_hours, 1),
                                "expected_hours": round(expected_hours, 1),
                                "completion_percentage": round(
                                    completion_percentage, 1
                                ),
                                "remaining_hours": round(remaining_hours, 1),
                            }
                        )

                # Process clock-out for current session
                current_session.clock_out = timezone.now()
                current_session.clock_out_latitude = lat if lat is not None else None
                current_session.clock_out_longitude = lng if lng is not None else None
                current_session.is_active = False
                current_session.save()  # This will auto-calculate duration

                # Log clock-out location only if coordinates are available
                if lat is not None and lng is not None:
                    LocationLog.objects.create(
                        employee=employee,
                        attendance_session=current_session,
                        latitude=lat,
                        longitude=lng,
                        accuracy=accuracy
                        if accuracy is not None
                        else 9999,  # Use high value for unknown accuracy
                        log_type="CLOCK_OUT",
                        is_valid=True,
                    )
                else:
                    # Log that location was unavailable
                    logger.warning(
                        f"Clock-out without location data for {employee.user.get_full_name()}"
                    )

                # Update attendance record
                attendance.is_currently_clocked_in = False
                attendance.current_session_type = None
                attendance.clock_out = (
                    current_session.clock_out
                )  # Update last clock-out
                attendance.location_out = (
                    f"{lat},{lng}" if lat is not None and lng is not None else "N/A"
                )

                # Stop location tracking
                attendance.location_tracking_active = False

                # Calculate total working hours
                attendance.calculate_total_working_hours()
                attendance.save()

                return JsonResponse(
                    {
                        "status": "success",
                        "message": f"Successfully clocked out from session {current_session.session_number} ({current_session.session_type.lower()})",
                        "session_number": current_session.session_number,
                        "session_type": current_session.session_type,
                        "session_duration": current_session.duration_hours,
                        "clock_out_time": current_session.clock_out.strftime(
                            "%H:%M:%S"
                        ),
                        "total_working_hours": attendance.total_working_hours,
                        "sessions_remaining": attendance.max_daily_sessions
                        - attendance.daily_sessions_count,
                    }
                )

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


def perform_auto_clock_out(attendance, session, lat, lng):
    """
    Helper to perform system-triggered clock out when shift ends
    """
    try:
        current_time = timezone.now()

        # Process clock-out
        session.clock_out = current_time
        session.clock_out_latitude = lat
        session.clock_out_longitude = lng
        session.is_active = False
        session.save()

        # Update attendance
        attendance.is_currently_clocked_in = False
        attendance.current_session_type = None
        attendance.clock_out = current_time
        attendance.location_out = f"{lat},{lng}"
        attendance.location_tracking_active = False

        attendance.calculate_total_working_hours()
        attendance.save()

        return True
    except Exception as e:
        logger.error(f"Auto clock-out failed: {str(e)}")
        return False


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
        accuracy = data.get("accuracy")

        if lat is not None and lng is not None:
            # Check if location tracking is active for today's attendance
            today = timezone.localdate()
            try:
                attendance = Attendance.objects.get(employee=employee, date=today)

                # Check if currently clocked in and has active session
                if not attendance.is_currently_clocked_in:
                    return JsonResponse(
                        {
                            "status": "not_clocked_in",
                            "message": "Not currently clocked in",
                            "location_tracking_active": False,
                        }
                    )

                # Get current active session
                current_session = attendance.get_current_session()
                if not current_session:
                    return JsonResponse(
                        {
                            "status": "no_active_session",
                            "message": "No active session found",
                            "location_tracking_active": False,
                        }
                    )

                # Check if shift is complete (9 hours)
                if current_session.clock_in:
                    session_duration = timezone.now() - current_session.clock_in
                    # Auto-stop after 9 hours (Exact shift duration)
                    if session_duration.total_seconds() >= 9 * 3600:
                        # Perform auto clock-out
                        if perform_auto_clock_out(
                            attendance, current_session, lat, lng
                        ):
                            return JsonResponse(
                                {
                                    "status": "shift_completed",
                                    "message": "Shift completed (9 hours). Auto clocked out.",
                                    "location_tracking_active": False,
                                    "clock_out_performed": True,
                                }
                            )
                        else:
                            # Fallback if auto-clockout fails, just stop tracking
                            attendance.location_tracking_active = False
                            attendance.save()
                            return JsonResponse(
                                {
                                    "status": "tracking_stopped",
                                    "message": "Shift time exceeded. Tracking stopped.",
                                    "location_tracking_active": False,
                                }
                            )

                # Log location for current session
                if attendance.location_tracking_active:
                    # Create session-specific location log
                    from employees.models import SessionLocationLog

                    SessionLocationLog.objects.create(
                        session=current_session,
                        latitude=lat,
                        longitude=lng,
                        accuracy=accuracy,
                    )

                    # Log to generic LocationLog as well - ONLY if accuracy is good
                    # Filter out poor accuracy (likely network based or bad signal) to avoid "fake" look
                    # Threshold: 2500 meters (Relaxed to ensure tracking works for all users/devices)
                    is_accurate = True
                    if accuracy and float(accuracy) > 2500:
                        is_accurate = False

                    if is_accurate:
                        # Also create general location log for backward compatibility
                        LocationLog.objects.create(
                            employee=employee, latitude=str(lat), longitude=str(lng)
                        )

                    # Prepare response
                    response_data = {
                        "status": "success",
                        "message": f"Location logged for Session {current_session.session_number}",
                        "location_tracking_active": True,
                        "session_number": current_session.session_number,
                        "session_type": current_session.session_type,
                    }

                    # Check session duration and provide notifications
                    session_duration = timezone.now() - current_session.clock_in
                    session_hours = session_duration.total_seconds() / 3600
                    if session_hours >= 8:
                        response_data["session_completed"] = True
                        response_data["notification"] = (
                            f"Session {current_session.session_number} completed ({session_hours:.1f} hours). Consider clocking out."
                        )
                    elif session_hours >= 4:
                        response_data["session_progress"] = (
                            f"Session {current_session.session_number} in progress ({session_hours:.1f} hours)"
                        )

                    return JsonResponse(response_data)
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
    employee = safe_get_employee_profile(user)

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
        from django.contrib import messages

        messages.success(request, "ID Documents updated successfully.")

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
                balance = employee.leave_balance
                context["cl_balance"] = balance.casual_leave_balance
                context["sl_balance"] = balance.sick_leave_balance
                context["leave_balance"] = balance
            else:
                context["cl_balance"] = 0
                context["sl_balance"] = 0
        except Exception:
            # Fallback if something goes wrong (e.g. no profile)
            context["cl_balance"] = 0
            context["sl_balance"] = 0
        return context

    def form_valid(self, form):
        employee = self.request.user.employee_profile
        form.instance.employee = employee

        # Server-side duplicate prevention: Check for recent duplicate submissions
        from django.utils import timezone
        from datetime import timedelta

        recent_duplicate = LeaveRequest.objects.filter(
            employee=employee,
            start_date=form.cleaned_data["start_date"],
            end_date=form.cleaned_data["end_date"],
            leave_type=form.cleaned_data["leave_type"],
            created_at__gte=timezone.now() - timedelta(seconds=10),
        ).exists()

        if recent_duplicate:
            from django.contrib import messages

            messages.warning(
                self.request,
                "You just submitted a leave request for these dates. Please wait before submitting again.",
            )
            return self.form_invalid(form)

        # Check if this is a confirmation submission
        confirm_lop = self.request.POST.get("confirm_lop", "false").lower() == "true"

        # Validate leave application before saving
        temp_leave_request = LeaveRequest(
            employee=form.instance.employee,
            leave_type=form.cleaned_data["leave_type"],
            start_date=form.cleaned_data["start_date"],
            end_date=form.cleaned_data["end_date"],
            duration=form.cleaned_data.get("duration", "FULL"),
        )

        validation = temp_leave_request.validate_leave_application()

        # If validation shows issues and user hasn't confirmed, ask for confirmation
        if (
            validation.get("will_be_lop", False)
            and form.cleaned_data["leave_type"] != "UL"
            and not confirm_lop
        ):
            from django.contrib import messages

            messages.error(
                self.request,
                f"⚠️ Insufficient Leave Balance: {validation['message']} Please confirm if you want to proceed with LOP (Loss of Pay).",
            )

            # Return form with validation warning for user confirmation
            return self.render_to_response(
                self.get_context_data(
                    form=form, validation_warning=validation, show_confirmation=True
                )
            )

        # Add a comment to the leave request if it involves LOP
        if (
            validation.get("will_be_lop", False)
            and form.cleaned_data["leave_type"] != "UL"
        ):
            original_reason = form.cleaned_data.get("reason", "")
            lop_note = f"\n\n[System Note: This application involves {validation.get('shortfall', 0)} days of LOP due to insufficient balance. Available: {validation.get('available_balance', 0)} days, Requested: {validation.get('requested_days', 0)} days]"
            form.instance.reason = original_reason + lop_note

        # Proceed with normal save
        response = super().form_valid(form)

        # Send email notifications asynchronously to avoid blocking the response
        import threading

        def send_email_async():
            try:
                from core.email_utils import send_leave_request_notification
                import logging

                logger = logging.getLogger(__name__)
                result = send_leave_request_notification(self.object)
                if not result.get("hr", False):
                    logger.error(
                        f"Failed to send leave request email to HR for {self.object.id}"
                    )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Leave request email error: {str(e)}")

        # Start email sending in background thread
        email_thread = threading.Thread(target=send_email_async)
        email_thread.daemon = True
        email_thread.start()

        return response


@csrf_exempt
@login_required
def check_leave_balance(request):
    """AJAX endpoint to check leave balance for real-time validation"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            leave_type = data.get("leave_type")
            start_date = data.get("start_date")
            end_date = data.get("end_date")
            duration = data.get("duration", "FULL")

            if not hasattr(request.user, "employee_profile"):
                return JsonResponse(
                    {"status": "error", "message": "No employee profile found"},
                    status=400,
                )

            employee = request.user.employee_profile

            # Create temporary leave request for validation
            from datetime import datetime

            temp_leave = LeaveRequest(
                employee=employee,
                leave_type=leave_type,
                start_date=datetime.strptime(start_date, "%Y-%m-%d").date(),
                end_date=datetime.strptime(end_date, "%Y-%m-%d").date(),
                duration=duration,
            )

            validation = temp_leave.validate_leave_application()

            # Get current balances
            balance = employee.leave_balance
            balances = {
                "CL": balance.casual_leave_balance,
                "SL": balance.sick_leave_balance,
            }

            return JsonResponse(
                {
                    "status": "success",
                    "validation": validation,
                    "balances": balances,
                    "requested_days": temp_leave.total_days,
                }
            )

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)


@login_required
def approve_leave(request, pk):
    if request.method == "POST":
        leave_request = LeaveRequest.objects.get(pk=pk)

        # Security check: Only Manager or Admin can approve
        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN or user.is_superuser
        is_manager = (
            user.role == User.Role.MANAGER
            and leave_request.employee.manager
            and leave_request.employee.manager.user == user
        )

        if not (is_admin or is_manager):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        # Get approval type from POST data
        approval_type = request.POST.get("approval_type", "FULL")

        # Validate approval type
        if approval_type not in ["FULL", "WITH_LOP", "ONLY_AVAILABLE"]:
            approval_type = "FULL"

        # Use the new approval method from the model
        if leave_request.approve_leave(user, approval_type=approval_type):
            # Update Attendance Records
            from datetime import timedelta

            current_date = leave_request.start_date
            while current_date <= leave_request.end_date:
                # Get or Create Attendance
                att_record, created = Attendance.objects.get_or_create(
                    employee=leave_request.employee, date=current_date
                )

                # Update status
                if leave_request.leave_type == "OD":
                    att_record.status = "ON_DUTY"
                elif approval_type == "WITH_LOP" or leave_request.leave_type == "UL":
                    # Mark as LOP for days beyond available balance
                    validation = leave_request.validate_leave_application()
                    days_from_start = (current_date - leave_request.start_date).days
                    available_days = validation.get("available_balance", 0)

                    if days_from_start < available_days:
                        att_record.status = "LEAVE"
                    else:
                        att_record.status = (
                            "LEAVE"  # Still mark as leave, LOP tracked in balance
                        )
                else:
                    att_record.status = "LEAVE"

                att_record.save()
                current_date += timedelta(days=1)

            # Send Approval Email with approval type info asynchronously
            import threading

            def send_email_async():
                try:
                    from core.email_utils import send_leave_approval_notification
                    import logging

                    logger = logging.getLogger(__name__)
                    if not send_leave_approval_notification(leave_request):
                        logger.warning("Leave approval email notification failed")
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(f"Leave approval email error: {str(e)}")

            # Start email sending in background thread
            email_thread = threading.Thread(target=send_email_async)
            email_thread.daemon = True
            email_thread.start()

            # Show success message immediately
            from django.contrib import messages

            approval_msg = {
                "FULL": "Leave approved successfully (Full Balance).",
                "WITH_LOP": "Leave approved with LOP for excess days.",
                "ONLY_AVAILABLE": "Leave approved for available days only.",
            }.get(approval_type, "Leave approved successfully.")
            messages.success(
                request,
                f"{approval_msg} Notification will be sent to {leave_request.employee.user.first_name}.",
            )

    # Redirect back to leave requests page or dashboard
    return redirect("leave_requests")


@login_required
def reject_leave(request, pk):
    if request.method == "POST":
        leave_request = LeaveRequest.objects.get(pk=pk)

        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN or user.is_superuser
        is_manager = (
            user.role == User.Role.MANAGER
            and leave_request.employee.manager
            and leave_request.employee.manager.user == user
        )

        if not (is_admin or is_manager):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        leave_request.status = "REJECTED"
        leave_request.rejection_reason = request.POST.get("rejection_reason", "")
        leave_request.approved_by = user  # Store acts as 'processed_by'
        leave_request.approved_at = timezone.now()
        leave_request.save()

        # Send Rejection Email asynchronously
        import threading

        def send_email_async():
            try:
                from core.email_utils import send_leave_rejection_notification
                import logging

                logger = logging.getLogger(__name__)
                if not send_leave_rejection_notification(leave_request):
                    logger.warning("Leave rejection email notification failed")
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error sending rejection email: {e}")

        # Start email sending in background thread
        email_thread = threading.Thread(target=send_email_async)
        email_thread.daemon = True
        email_thread.start()

        messages.success(request, "Leave rejected. Notification will be sent.")

        return redirect(request.META.get("HTTP_REFERER", "leave_requests"))
    return redirect("leave_requests")


@login_required
def attendance_map(request, pk):
    try:
        attendance = Attendance.objects.get(pk=pk)
        employee = attendance.employee

        # Permission Check
        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN or user.is_superuser
        is_manager = (
            user.role == User.Role.MANAGER
            and employee.manager
            and employee.manager.user == user
        )
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

        # 1. Clock In
        if attendance.location_in:
            lat, lng = safe_parse_location(attendance.location_in)
            if lat:
                map_locations.append(
                    {
                        "lat": lat,
                        "lng": lng,
                        "title": f"Clock In: {attendance.clock_in.strftime('%I:%M %p')}",
                        "type": "in",
                    }
                )

        # Filter logs to show only hourly points (approx)
        filtered_logs = []
        if logs:
            last_added_time = None
            for log in logs:
                if last_added_time is None:
                    filtered_logs.append(log)
                    last_added_time = log.timestamp
                else:
                    diff = log.timestamp - last_added_time
                    # Only show if > 50 mins apart to satisfying "Every 1 Hour" request
                    if diff.total_seconds() >= 3000: 
                        filtered_logs.append(log)
                        last_added_time = log.timestamp

        # 2. Logs
        for log in filtered_logs:
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
            lat, lng = safe_parse_location(attendance.location_out)
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
        is_admin = user.role == User.Role.COMPANY_ADMIN or user.is_superuser
        is_manager = (
            user.role == User.Role.MANAGER
            and employee.manager
            and employee.manager.user == user
        )

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
            # Clock In Marker
            if map_attendance.location_in:
                lat, lng = safe_parse_location(map_attendance.location_in)
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
                lat, lng = safe_parse_location(map_attendance.location_out)
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
            # Compare manager's user object with request user
            if attendance.employee.manager:
                is_manager = attendance.employee.manager.user == request.user

        is_self = attendance.employee.user == request.user

        if not (is_admin or is_manager or is_self):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        map_locations = []

        # 1. Clock In
        if attendance.location_in:
            lat, lng = safe_parse_location(attendance.location_in)
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
            lat, lng = safe_parse_location(attendance.location_out)
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

                        # Check if user already exists
                        user = User.objects.filter(email=email).first()
                        if user:
                            # Check if the user already has an employee profile (is a real employee)
                            if hasattr(user, 'employee_profile'):
                                raise ValueError(f"User with email {email} already exists")
                            else:
                                # User exists but no employee profile (Zombie record) -> Reuse it
                                user.first_name = str(row.get("first_name", "")).strip()
                                user.last_name = str(row.get("last_name", "")).strip()
                                user.save()
                        else:
                            # 2. Create New User
                            first_name = str(row.get("first_name", "")).strip()
                            last_name = str(row.get("last_name", "")).strip()
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

                        # Sync Department & Designation with Role Configuration
                        from companies.models import Department, Designation

                        dept_name = (
                            str(row.get("department", "General")).strip().title()
                        )
                        desig_name = (
                            str(row.get("designation", "Employee")).strip().title()
                        )

                        # Ensure they exist in Role Config (prevents duplicates)
                        Department.objects.get_or_create(
                            company=self.request.user.company, name=dept_name
                        )
                        Designation.objects.get_or_create(
                            company=self.request.user.company, name=desig_name
                        )

                        employee = Employee.objects.create(
                            user=user,
                            company=self.request.user.company,
                            designation=desig_name,
                            department=dept_name,
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

                        # 6. Create Leave Balance (handled by signal)
                        # LeaveBalance.objects.create(...) - REMOVED to avoid duplicate key error

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

        employee = self.request.user.employee_profile

        # Server-side duplicate prevention: Check for recent duplicate submissions
        from django.utils import timezone
        from datetime import timedelta

        recent_duplicate = RegularizationRequest.objects.filter(
            employee=employee,
            date=form.cleaned_data["date"],
            created_at__gte=timezone.now() - timedelta(seconds=10),
        ).exists()

        if recent_duplicate:
            from django.contrib import messages

            messages.warning(
                self.request,
                "You just submitted a regularization request for this date. Please wait before submitting again.",
            )
            return self.form_invalid(form)

        form.instance.employee = employee
        response = super().form_valid(form)

        # Send Email Notification asynchronously to avoid blocking the response
        import threading

        def send_email_async():
            try:
                from core.email_utils import send_regularization_request_notification
                import logging

                logger = logging.getLogger(__name__)
                result = send_regularization_request_notification(self.object)
                if not result.get("hr", False):
                    logger.error(
                        f"Failed to send regularization request email to HR for {self.object.id}"
                    )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error calling regularization email utility: {e}")

        # Start email sending in background thread
        email_thread = threading.Thread(target=send_email_async)
        email_thread.daemon = True
        email_thread.start()

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
            employee = safe_get_employee_profile(user)
            if employee:
                return qs.filter(employee=employee)
            return qs.none()


@login_required
def approve_regularization(request, pk):
    if request.method == "POST":
        reg_request = RegularizationRequest.objects.get(pk=pk)

        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN or user.is_superuser
        is_manager = (
            user.role == User.Role.MANAGER
            and reg_request.employee.manager
            and reg_request.employee.manager.user == user
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

        # Recalculate working hours after regularization
        attendance.calculate_total_working_hours()

        attendance.save()

        # Send Approval Email asynchronously
        import threading

        def send_email_async():
            try:
                from core.email_utils import send_regularization_approval_notification
                import logging

                logger = logging.getLogger(__name__)
                if not send_regularization_approval_notification(reg_request):
                    logger.warning("Regularization approval email notification failed")
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error sending regularization approval email: {e}")

        # Start email sending in background thread
        email_thread = threading.Thread(target=send_email_async)
        email_thread.daemon = True
        email_thread.start()

        messages.success(request, "Regularization approved. Notification will be sent.")

        return redirect(request.META.get("HTTP_REFERER", "regularization_list"))

    return redirect("regularization_list")


@login_required
def reject_regularization(request, pk):
    if request.method == "POST":
        reg_request = RegularizationRequest.objects.get(pk=pk)

        user = request.user
        is_admin = user.role == User.Role.COMPANY_ADMIN or user.is_superuser
        is_manager = (
            user.role == User.Role.MANAGER
            and reg_request.employee.manager
            and reg_request.employee.manager.user == user
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

        # Send Rejection Email asynchronously
        import threading

        def send_email_async():
            try:
                from core.email_utils import send_regularization_rejection_notification
                import logging

                logger = logging.getLogger(__name__)
                if not send_regularization_rejection_notification(reg_request):
                    logger.warning("Regularization rejection email notification failed")
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error sending regularization rejection email: {e}")

        # Start email sending in background thread
        email_thread = threading.Thread(target=send_email_async)
        email_thread.daemon = True
        email_thread.start()

        messages.success(request, "Regularization rejected. Notification will be sent.")

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

    # Prefetch leave balances
    employees = employees.select_related("user").order_by("user__first_name")

    # Ensure all employees have leave balance records
    from django.core.exceptions import ObjectDoesNotExist

    for employee in employees:
        try:
            _ = employee.leave_balance
        except ObjectDoesNotExist:
            # Create with 0 leaves for new employees (probation period)
            LeaveBalance.objects.create(
                employee=employee,
                casual_leave_allocated=0.0,
                sick_leave_allocated=0.0
            )

    # Context for Accrual Modal (Safe from template syntax errors)
    import calendar
    from django.utils import timezone

    now = timezone.now()
    current_month = now.month
    current_year = now.year

    months_ctx = []
    for i in range(1, 13):
        months_ctx.append(
            {
                "value": i,
                "name": calendar.month_name[i],
                "selected": "selected" if i == current_month else "",
            }
        )

    years_ctx = []
    # Show current year and next 2 years, or surrounding
    for y in [2024, 2025, 2026]:
        years_ctx.append(
            {"value": y, "selected": "selected" if y == current_year else ""}
        )

    return render(
        request,
        "employees/leave_configuration.html",
        {"employees": employees, "months_ctx": months_ctx, "years_ctx": years_ctx},
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
    import calendar

    user = request.user
    if user.role not in [User.Role.COMPANY_ADMIN, User.Role.MANAGER]:
        messages.error(request, "Permission Denied")
        return redirect("leave_configuration")

    from django.core.management import call_command

    try:
        month = request.POST.get("month")
        year = request.POST.get("year")

        period_msg = ""
        if month and year:
            try:
                month_name = calendar.month_name[int(month)]
                period_msg = f"for {month_name} {year}"
            except (ValueError, IndexError) as e:
                logger.debug(
                    "Failed to parse month/year for accrual message",
                    month=month,
                    year=year,
                    error=str(e),
                )

        # Run the command
        call_command("accrue_monthly_leaves")

        success_msg = (
            f"Monthly accrual processed {period_msg}: +1 Sick and +1 Casual leave added to all employees."
            if period_msg
            else "Monthly accrual processed: +1 Sick and +1 Casual leave added to all employees."
        )

        messages.success(request, success_msg)

    except Exception as e:
        logger.exception("Error running monthly leave accrual", error=str(e))
        capture_exception(e, properties={"action": "manual_accrual"})
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


# --- Location Tracking API Endpoints ---


@csrf_exempt
@login_required
def submit_hourly_location(request):
    """
    API endpoint for employees to submit their hourly location updates
    """
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Invalid method"}, status=405
        )

    try:
        data = json.loads(request.body)
        lat = data.get("latitude")
        lng = data.get("longitude")
        accuracy = data.get("accuracy")

        if not lat or not lng:
            return JsonResponse(
                {"status": "error", "message": "Latitude and longitude are required"},
                status=400,
            )

        if not hasattr(request.user, "employee_profile"):
            return JsonResponse(
                {"status": "error", "message": "No employee profile found"}, status=400
            )

        employee = request.user.employee_profile
        today = timezone.localdate()

        # Find the current active session
        active_session = AttendanceSession.objects.filter(
            employee=employee, date=today, clock_out__isnull=True, is_active=True
        ).first()

        if not active_session:
            return JsonResponse(
                {"status": "error", "message": "No active session found"}, status=400
            )

        # Check for 9-hour limit
        time_since_clockin = timezone.now() - active_session.clock_in
        if time_since_clockin >= timedelta(hours=9):
            return JsonResponse(
                {
                    "status": "tracking_stopped",
                    "message": "Shift limit reached (9 hours)",
                }
            )

        # Create location log
        location_log = LocationLog.objects.create(
            employee=employee,
            attendance_session=active_session,
            latitude=lat,
            longitude=lng,
            log_type="HOURLY",
            accuracy=accuracy,
            is_valid=True,
        )

        return JsonResponse(
            {
                "status": "success",
                "message": "Location updated successfully",
                "log_id": location_log.id,
                "timestamp": location_log.timestamp.isoformat(),
            }
        )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Hourly location update error: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@login_required
def get_location_tracking_status(request):
    """
    API endpoint to check if employee needs to provide location update
    """
    if request.method != "GET":
        return JsonResponse(
            {"status": "error", "message": "Invalid method"}, status=405
        )

    try:
        if not hasattr(request.user, "employee_profile"):
            return JsonResponse(
                {"status": "error", "message": "No employee profile found"}, status=400
            )

        employee = request.user.employee_profile
        today = timezone.localdate()
        current_time = timezone.now()

        # Find the current active session
        active_session = AttendanceSession.objects.filter(
            employee=employee, date=today, clock_out__isnull=True, is_active=True
        ).first()

        if not active_session:
            return JsonResponse(
                {
                    "status": "success",
                    "needs_location": False,
                    "message": "No active session",
                }
            )

        # Check if location update is needed
        last_log = (
            LocationLog.objects.filter(
                attendance_session=active_session, log_type__in=["CLOCK_IN", "HOURLY"]
            )
            .order_by("-timestamp")
            .first()
        )

        needs_location = False
        next_update_time = None

        if not last_log:
            # Check if shift duration (9 hours) exceeded
            time_since_clockin = current_time - active_session.clock_in
            if time_since_clockin >= timedelta(hours=9):
                return JsonResponse(
                    {
                        "status": "success",
                        "needs_location": False,
                        "tracking_stopped": True,
                        "message": "Shift limit reached",
                    }
                )

            if time_since_clockin >= timedelta(hours=1):
                needs_location = True
        else:
            # Check if it's been 1 hour since last log
            time_since_last_log = current_time - last_log.timestamp
            if time_since_last_log >= timedelta(hours=1):
                needs_location = True
            else:
                # Calculate when next update is needed
                next_update_time = (last_log.timestamp + timedelta(hours=1)).isoformat()

        return JsonResponse(
            {
                "status": "success",
                "needs_location": needs_location,
                "active_session": True,
                "session_start": active_session.clock_in.isoformat(),
                "next_update_time": next_update_time,
                "last_update": last_log.timestamp.isoformat() if last_log else None,
            }
        )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Location tracking status error: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def get_employee_location_history(request, employee_id):
    """
    API endpoint to get location history for an employee (for managers/admins)
    """
    try:
        # Check permissions
        if request.user.role not in [User.Role.COMPANY_ADMIN, User.Role.MANAGER]:
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )

        employee = Employee.objects.get(id=employee_id)

        # If manager, ensure they can only see their subordinates
        if request.user.role == User.Role.MANAGER:
            if employee.manager != request.user:
                return JsonResponse(
                    {"status": "error", "message": "Permission denied"}, status=403
                )

        # Get date range from query params
        from datetime import datetime

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date = timezone.localdate() - timedelta(
                days=7
            )  # Default to last 7 days

        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end_date = timezone.localdate()

        # Get location logs
        location_logs = (
            LocationLog.objects.filter(
                employee=employee,
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date,
                is_valid=True,
            )
            .select_related("attendance_session")
            .order_by("-timestamp")
        )

        # Format response
        logs_data = []
        for log in location_logs:
            logs_data.append(
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "latitude": float(log.latitude),
                    "longitude": float(log.longitude),
                    "log_type": log.log_type,
                    "accuracy": log.accuracy,
                    "session_number": log.attendance_session.session_number
                    if log.attendance_session
                    else None,
                    "session_type": log.attendance_session.session_type
                    if log.attendance_session
                    else None,
                }
            )

        return JsonResponse(
            {
                "status": "success",
                "employee": {
                    "id": employee.id,
                    "name": employee.user.get_full_name(),
                    "email": employee.user.email,
                },
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "location_logs": logs_data,
                "total_logs": len(logs_data),
            }
        )

    except Employee.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Employee not found"}, status=404
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Location history error: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
