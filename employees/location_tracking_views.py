import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from loguru import logger

from accounts.models import User

from .models import Attendance, Employee, LocationLog


@csrf_exempt
@login_required
def submit_hourly_location(request):
    """
    API endpoint for hourly location tracking.
    Called automatically by frontend every hour when employee is clocked in.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body)

        # Ensure employee profile exists
        if not hasattr(request.user, "employee_profile"):
            return JsonResponse({"status": "error", "message": "No employee profile found"}, status=400)

        employee = request.user.employee_profile
        lat = data.get("latitude")
        lng = data.get("longitude")
        accuracy = data.get("accuracy")

        if lat is None or lng is None:
            return JsonResponse(
                {"status": "error", "message": "Latitude and longitude required"},
                status=400,
            )

        # Check if currently clocked in
        today = timezone.localdate()
        try:
            attendance = Attendance.objects.get(employee=employee, date=today)

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

            # Prevent Duplicate Hourly Logs (Rate Limit)
            last_hourly_log = (
                LocationLog.objects.filter(employee=employee, log_type="HOURLY").order_by("-timestamp").first()
            )

            if last_hourly_log:
                time_diff = timezone.now() - last_hourly_log.timestamp
                if time_diff.total_seconds() < 3300:  # 55 minutes
                    return JsonResponse(
                        {
                            "status": "ignored",
                            "message": "Hourly location already logged recently",
                            "location_tracking_active": True,
                        }
                    )

            # Create location log
            LocationLog.objects.create(
                employee=employee,
                attendance_session=current_session,
                latitude=lat,
                longitude=lng,
                accuracy=accuracy,
                log_type="HOURLY",
                is_valid=True,
            )

            # Also create session-specific log
            from employees.models import SessionLocationLog

            SessionLocationLog.objects.create(
                session=current_session,
                latitude=lat,
                longitude=lng,
                accuracy=accuracy,
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Location logged successfully",
                    "location_tracking_active": True,
                }
            )

        except Attendance.DoesNotExist:
            return JsonResponse(
                {
                    "status": "no_attendance",
                    "message": "No attendance record found for today",
                    "location_tracking_active": False,
                }
            )

    except Exception as e:
        logger.error(f"Hourly location tracking error: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@login_required
def get_location_tracking_status(request):
    """
    Get the current location tracking status for the logged-in employee.
    Returns whether location tracking is active and if a location update is needed.
    """
    try:
        if not hasattr(request.user, "employee_profile"):
            return JsonResponse({"status": "error", "message": "No employee profile found"}, status=400)

        employee = request.user.employee_profile
        today = timezone.localdate()

        try:
            attendance = Attendance.objects.get(employee=employee, date=today)

            # Check if tracking should stop (shift complete or clocked out)
            tracking_stopped = False
            if not attendance.is_currently_clocked_in or attendance.should_stop_location_tracking():
                tracking_stopped = True

            # Determine if we need a location update (every hour)
            needs_location = False
            if attendance.is_currently_clocked_in and not tracking_stopped:
                # Check last location log time or clock-in time
                last_log = (
                    LocationLog.objects.filter(employee=employee, log_type="HOURLY").order_by("-timestamp").first()
                )

                # Determine reference time (latest of clock-in or last log)
                reference_time = attendance.clock_in

                # If we have a current session, use its clock-in as baseline if it's later
                current_session = attendance.get_current_session()
                if current_session and current_session.clock_in:
                    if not reference_time or current_session.clock_in > reference_time:
                        reference_time = current_session.clock_in

                if last_log and last_log.timestamp > reference_time:
                    reference_time = last_log.timestamp

                if reference_time:
                    # STRICT 1 Hour Interval (3600 seconds)
                    time_since_last = timezone.now() - reference_time
                    if time_since_last.total_seconds() >= 3600:  # 60 minutes
                        needs_location = True
                else:
                    # Should not trigger if clocked in properly
                    needs_location = True

            return JsonResponse(
                {
                    "status": "success",
                    "is_clocked_in": attendance.is_currently_clocked_in,
                    "location_tracking_active": attendance.location_tracking_active,
                    "session_count": attendance.daily_sessions_count,
                    "needs_location": needs_location,
                    "tracking_stopped": tracking_stopped,
                    "clock_in_time": attendance.clock_in.isoformat() if attendance.clock_in else None,
                    "last_log_time": last_log.timestamp.isoformat() if last_log else None,
                    "message": "Shift completed" if tracking_stopped else "Tracking active",
                }
            )
        except Attendance.DoesNotExist:
            return JsonResponse(
                {
                    "status": "success",
                    "is_clocked_in": False,
                    "location_tracking_active": False,
                    "session_count": 0,
                    "needs_location": False,
                    "tracking_stopped": False,
                }
            )

    except Exception as e:
        logger.error(f"Location tracking status error: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def get_employee_location_history(request, employee_id):
    """
    Get location history for a specific employee (admin/manager only).
    """
    try:
        # Permission check
        is_admin = request.user.role == User.Role.COMPANY_ADMIN or request.user.is_superuser

        employee = Employee.objects.get(pk=employee_id)

        # Check if user has permission to view this employee's data
        is_manager = False
        if request.user.role == User.Role.MANAGER and hasattr(request.user, "employee_profile"):
            if employee.manager:
                is_manager = employee.manager == request.user

        is_self = employee.user == request.user

        if not (is_admin or is_manager or is_self):
            return JsonResponse({"status": "error", "message": "Permission denied"}, status=403)

        # Get date range from query params
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        logs = LocationLog.objects.filter(employee=employee)

        if from_date:
            from datetime import datetime

            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            logs = logs.filter(timestamp__gte=from_dt)

        if to_date:
            from datetime import datetime

            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            logs = logs.filter(timestamp__lte=to_dt)

        logs = logs.order_by("-timestamp")[:100]  # Limit to 100 most recent

        location_data = []
        for log in logs:
            location_data.append(
                {
                    "latitude": float(log.latitude),
                    "longitude": float(log.longitude),
                    "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "log_type": log.get_log_type_display(),
                    "accuracy": log.accuracy,
                }
            )

        return JsonResponse(
            {
                "status": "success",
                "data": location_data,
                "count": len(location_data),
            }
        )

    except Employee.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Employee not found"}, status=404)
    except Exception as e:
        logger.error(f"Location history error: {str(e)}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
