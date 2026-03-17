import os
import textwrap
from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from loguru import logger
from rest_framework import authentication, permissions, status, views
from rest_framework.response import Response

from employees.models import Employee

from .models import ActivityPulse, ActivitySession, AppActivity, BrowserActivity, EmployeeDevice, SystemEvent
from .serializers import ActivityBatchSerializer


class ActivityIngestView(views.APIView):
    """
    API endpoint for the Desktop Agent or Extension to sync activity data.
    """

    authentication_classes = []  # Strictly manual token validation
    permission_classes = [permissions.AllowAny]

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            # Log the request for debugging
            logger.info(f"Activity sync request from {request.META.get('REMOTE_ADDR')}")

            auth_header = request.headers.get("Authorization", "")
            if not auth_header:
                # Try alternate header names
                auth_header = request.META.get("HTTP_AUTHORIZATION", "")

            logger.info(
                f"Auth header present: {bool(auth_header)}, starts with Token: {auth_header.startswith('Token ') if auth_header else False}"
            )

            if not auth_header or not auth_header.startswith("Token "):
                logger.warning(f"No valid token in request. Headers: {dict(request.headers)}")
                return Response({"error": "No token provided"}, status=status.HTTP_401_UNAUTHORIZED)

            token_str = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else ""
            if not token_str:
                logger.warning("Token string is empty after split")
                return Response({"error": "Invalid token format"}, status=status.HTTP_401_UNAUTHORIZED)

            logger.info(f"Looking up device with token (first 10 chars): {token_str[:10]}...")
            device = EmployeeDevice.objects.filter(token=token_str, is_active=True).first()

            if not device:
                logger.warning("No active device found for token. Checking if token exists at all...")
                any_device = EmployeeDevice.objects.filter(token=token_str).first()
                if any_device:
                    logger.warning(f"Device exists but is_active={any_device.is_active}")
                else:
                    logger.warning("Token doesn't match any device in database")
                return Response({"error": "Invalid or inactive token"}, status=status.HTTP_401_UNAUTHORIZED)

            logger.info(f"✅ Valid device found for employee: {device.employee.user.get_full_name()}")
            employee = device.employee
            serializer = ActivityBatchSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Activity sync validation failed: {serializer.errors}")
                logger.debug(f"Payload was: {str(request.data)[:500]}...")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            data = serializer.validated_data

            # Update device last seen
            device.last_seen = timezone.now()
            device.save(update_fields=["last_seen"])

            # 1. Get or create an active session
            session = ActivitySession.objects.filter(employee=employee, end_time__isnull=True).first()
            if not session:
                session = ActivitySession.objects.create(employee=employee)

            # Limit batch sizes to prevent "Request Too Large" errors
            app_list = [
                AppActivity(employee=employee, session=session, **d) for d in data.get("app_activities", [])[:100]
            ]
            if app_list:
                AppActivity.objects.bulk_create(app_list)

            browser_list = [
                BrowserActivity(employee=employee, session=session, **d)
                for d in data.get("browser_activities", [])[:100]
            ]
            if browser_list:
                BrowserActivity.objects.bulk_create(browser_list)

            event_list = [SystemEvent(employee=employee, **d) for d in data.get("system_events", [])[:50]]
            if event_list:
                SystemEvent.objects.bulk_create(event_list)

            pulse = ActivityPulse.objects.create(
                employee=employee, is_idle=data.get("is_idle", False), idle_duration_seconds=data.get("idle_seconds", 0)
            )

            logger.info(
                f"✅ Sync Success for {employee.user.get_full_name()} "
                f"(Device: {device.device_name}, Pulse ID: {pulse.id})"
            )
            logger.debug(f"Payload: {len(app_list)} apps, {len(browser_list)} browser, {len(event_list)} events")
            return Response({"status": "success", "pulse_id": pulse.id}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Activity sync error: {str(e)}", exc_info=True)
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HeartbeatView(views.APIView):
    """
    Lightweight heartbeat endpoint for web-based activity tracking.
    """

    authentication_classes = [authentication.SessionAuthentication, authentication.BasicAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, employee_id, *args, **kwargs):
        try:
            # Check if user is authenticated
            if not request.user.is_authenticated:
                logger.warning("Heartbeat: Unauthenticated request")
                return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

            employee = Employee.objects.get(id=employee_id)

            # Verify user can only send heartbeat for themselves
            if request.user.employee_profile.id != employee.id:
                logger.warning(f"Heartbeat: User {request.user.id} tried to send for employee {employee_id}")
                return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

            # Simple pulse recording
            ActivityPulse.objects.create(employee=employee, is_idle=False, idle_duration_seconds=0)

            logger.debug(f"Heartbeat recorded for {employee.user.get_full_name()}")
            return Response({"status": "pulse_recorded"}, status=status.HTTP_200_OK)
        except Employee.DoesNotExist:
            logger.warning(f"Heartbeat: Employee {employee_id} not found")
            return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Heartbeat error: {str(e)}", exc_info=True)
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ActivityDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "activity_monitoring/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_employee = self.request.user.employee_profile

        # Determine target employee (self or subordinate)
        employee = user_employee
        target_id = self.request.GET.get("employee_id")

        is_admin = self.request.user.role in ["COMPANY_ADMIN", "SUPERADMIN"]
        is_manager = self.request.user.role == "MANAGER"

        if target_id:
            from django.shortcuts import get_object_or_404

            if is_admin:
                employee = get_object_or_404(Employee, id=target_id, company=user_employee.company)
            elif is_manager:
                # Subordinates where manager is the current user
                employee = get_object_or_404(Employee, id=target_id, manager=self.request.user)

        # Date Filtering for the dashboard
        selected_date_str = self.request.GET.get("date")
        if selected_date_str:
            try:
                # Expecting YYYY-MM-DD
                today = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                today = timezone.localdate()
        else:
            today = timezone.localdate()

        context["selected_date"] = today
        context["today_date"] = timezone.localdate()
        context["yesterday_date"] = timezone.localdate() - timedelta(days=1)

        # Precise account identification
        account_ids = [employee.id]

        # 1. Total productive vs unproductive time (Selected Date)
        today_apps = AppActivity.objects.filter(employee_id__in=account_ids, start_time__date=today)
        productive_time = today_apps.filter(is_productive=True).aggregate(total=Sum("duration"))["total"] or timedelta(
            0
        )
        context["productive_hours"] = round(productive_time.total_seconds() / 3600, 1)

        # 1.1 Idle Time (Selected Date) - Sum of pulse idle durations
        idle_total = (
            ActivityPulse.objects.filter(employee_id__in=account_ids, timestamp__date=today, is_idle=True).aggregate(
                total=Sum("idle_duration_seconds")
            )["total"]
            or 0
        )
        context["unproductive_hours"] = round(idle_total / 3600, 1)

        # 2. Top Apps (Selected Date range)
        top_apps_qs = AppActivity.objects.filter(employee_id__in=account_ids, start_time__date=today)
        if not top_apps_qs.exists() and today == timezone.now().date():
            # Fallback: if today is selected and empty, show last 24 hours to avoid blank screen
            top_apps_qs = AppActivity.objects.filter(
                employee_id__in=account_ids, start_time__gte=timezone.now() - timedelta(days=1)
            )

        top_apps = (
            top_apps_qs.values("app_name").annotate(total_duration=Sum("duration")).order_by("-total_duration")[:5]
        )

        # Convert duration to hours for display
        for app in top_apps:
            app["hours"] = round(app["total_duration"].total_seconds() / 3600, 1) if app["total_duration"] else 0

        context["top_apps"] = top_apps

        # 3. Recent Activity (Searches + URLs)
        context["recent_activity"] = BrowserActivity.objects.filter(employee_id__in=account_ids).order_by("-timestamp")[
            :15
        ]

        # 3b. System Events (USB / File Transfer security alerts)
        from .models import SystemEvent

        if is_admin and not target_id:
            # Admin default view: show ALL company events newest-first
            all_company_employees = Employee.objects.filter(company=user_employee.company)
            context["system_events"] = (
                SystemEvent.objects.filter(employee__in=all_company_employees)
                .select_related("employee__user")
                .order_by("-timestamp")[:25]
            )
        elif is_manager and not target_id:
            # Manager default view: show ALL subordinates events
            subordinates = Employee.objects.filter(manager=self.request.user)
            context["system_events"] = (
                SystemEvent.objects.filter(employee__in=subordinates)
                .select_related("employee__user")
                .order_by("-timestamp")[:25]
            )
        else:
            context["system_events"] = (
                SystemEvent.objects.filter(employee_id__in=account_ids)
                .select_related("employee__user")
                .order_by("-timestamp")[:25]
            )

        # 4. Productivity Trend (Hourly for Today)
        trend_data = []
        for hour in range(24):
            hour_start = timezone.make_aware(datetime.combine(today, time(hour, 0)))
            hour_end = hour_start + timedelta(hours=1)

            stats = AppActivity.objects.filter(
                employee_id__in=account_ids, start_time__gte=hour_start, start_time__lt=hour_end
            ).aggregate(
                prod=Sum("duration", filter=Q(is_productive=True)),
                unprod=Sum("duration", filter=Q(is_productive=False)),
            )

            # Add idle time into unproductive for the hour
            hour_idle = (
                ActivityPulse.objects.filter(
                    employee_id__in=account_ids, timestamp__gte=hour_start, timestamp__lt=hour_end, is_idle=True
                ).aggregate(total=Sum("idle_duration_seconds"))["total"]
                or 0
            )

            trend_data.append(
                {
                    "label": f"{hour}:00",
                    "productive": round((stats["prod"] or timedelta(0)).total_seconds() / 3600, 2),
                    "unproductive": round(((stats["unprod"] or timedelta(0)).total_seconds() + hour_idle) / 3600, 2),
                }
            )

        context["trend_data"] = trend_data

        # 5. Admin/Manager Features: List of Employees with Status
        employees = Employee.objects.none()
        if is_admin:
            employees = Employee.objects.filter(company=user_employee.company).order_by("user__first_name")
        elif is_manager:
            employees = Employee.objects.filter(manager=self.request.user).order_by("user__first_name")

        if employees.exists():
            # Enrich employees with tracking status
            now = timezone.now()
            for emp in employees:
                # Use precise employee ID for status check (no fuzzy email prefix match)
                latest_pulse = ActivityPulse.objects.filter(employee_id=emp.id).order_by("-timestamp").first()
                if latest_pulse:
                    is_active = (now - latest_pulse.timestamp) < timedelta(minutes=10)
                    emp.tracking_status = "Online" if is_active else "Offline"
                    emp.last_sync = latest_pulse.timestamp
                else:
                    emp.tracking_status = "Never Synced"
                    emp.last_sync = None

            context["employees_list"] = employees

        # 6. Selected Employee Status (Precise match)
        latest_pulse = ActivityPulse.objects.filter(employee_id=employee.id).order_by("-timestamp").first()
        if latest_pulse:
            is_active = (timezone.now() - latest_pulse.timestamp) < timedelta(minutes=10)
            context["is_online"] = is_active
            context["last_sync"] = latest_pulse.timestamp
        else:
            context["is_online"] = False
            context["last_sync"] = None

        context["selected_employee"] = employee
        return context


class BrowserActivityDetailView(LoginRequiredMixin, TemplateView):
    """
    Full-page view for browsing activity with date filtering.
    """

    template_name = "activity_monitoring/browser_activity.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_employee = self.request.user.employee_profile

        is_admin = self.request.user.role in ["COMPANY_ADMIN", "SUPERADMIN"]
        is_manager = self.request.user.role == "MANAGER"

        # Resolve which employee to show
        employee = user_employee
        target_id = self.request.GET.get("employee_id")
        if target_id:
            from django.shortcuts import get_object_or_404

            if is_admin:
                employee = get_object_or_404(Employee, id=target_id, company=user_employee.company)
            elif is_manager:
                employee = get_object_or_404(Employee, id=target_id, manager=self.request.user)

        # Date filter
        date_str = self.request.GET.get("date")
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                selected_date = timezone.localdate()
        else:
            selected_date = timezone.localdate()

        activity_qs = BrowserActivity.objects.filter(employee=employee, timestamp__date=selected_date).order_by(
            "-timestamp"
        )

        context["browser_activity"] = activity_qs
        context["selected_employee"] = employee
        context["selected_date"] = selected_date
        context["total_count"] = activity_qs.count()

        # Employee list for switcher (admin/manager only)
        if is_admin:
            context["employees_list"] = Employee.objects.filter(company=user_employee.company).order_by(
                "user__first_name"
            )
        elif is_manager:
            context["employees_list"] = Employee.objects.filter(manager=self.request.user).order_by("user__first_name")

        return context


class AppActivityDetailView(LoginRequiredMixin, TemplateView):
    """
    Full-page view for app/toolset activity with date filtering.
    """

    template_name = "activity_monitoring/app_activity.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_employee = self.request.user.employee_profile

        is_admin = self.request.user.role in ["COMPANY_ADMIN", "SUPERADMIN"]
        is_manager = self.request.user.role == "MANAGER"

        # ── Resolve Employee ──────────────────────────────────────
        employee = user_employee
        target_id = self.request.GET.get("employee_id")
        if target_id:
            from django.shortcuts import get_object_or_404

            if is_admin:
                employee = get_object_or_404(Employee, id=target_id, company=user_employee.company)
            elif is_manager:
                employee = get_object_or_404(Employee, id=target_id, manager=self.request.user)

        # ── Date Filter ───────────────────────────────────────────
        date_str = self.request.GET.get("date")
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.localdate()
        except ValueError:
            selected_date = timezone.localdate()

        # ── Fetch raw records ordered by time ────────────────────
        raw_qs = AppActivity.objects.filter(employee=employee, start_time__date=selected_date).order_by("start_time")

        # ── Merge consecutive heartbeats into real sessions ──────
        # Two records belong to the same session if they share the same
        # app_name and the gap between end of one and start of next is
        # ≤ GAP_THRESHOLD seconds (tolerate 1 missed heartbeat).
        from datetime import timedelta

        GAP_THRESHOLD = timedelta(seconds=35)  # 3 × 10s heartbeat + buffer

        consolidated = []  # list of dicts: app, start, end, duration, ...
        for rec in raw_qs:
            if not rec.start_time or not rec.end_time:
                continue
            if (
                consolidated
                and consolidated[-1]["app_name"] == rec.app_name
                and (rec.start_time - consolidated[-1]["end_time"]) <= GAP_THRESHOLD
            ):
                # Extend the current session
                consolidated[-1]["end_time"] = rec.end_time
                consolidated[-1]["total_seconds"] += int((rec.duration or timedelta()).total_seconds())
            else:
                # Start a new session block
                consolidated.append(
                    {
                        "app_name": rec.app_name,
                        "category": rec.category,
                        "is_productive": rec.is_productive,
                        "window_title": rec.window_title,
                        "start_time": rec.start_time,
                        "end_time": rec.end_time,
                        "total_seconds": int((rec.duration or timedelta()).total_seconds()),
                    }
                )

        # Sort by start_time descending for display (most recent first)
        consolidated.sort(key=lambda x: x["start_time"], reverse=True)

        # ── Per-App Summary (total time per app, sorted) ─────────
        from collections import defaultdict

        app_totals = defaultdict(
            lambda: {
                "total_seconds": 0,
                "sessions": 0,
                "is_productive": True,
                "category": None,
                "first_seen": None,
                "last_seen": None,
            }
        )
        for sess in consolidated:
            name = sess["app_name"]
            app_totals[name]["total_seconds"] += sess["total_seconds"]
            app_totals[name]["sessions"] += 1
            app_totals[name]["is_productive"] = sess["is_productive"]
            app_totals[name]["category"] = sess["category"]
            # Track first/last seen
            if app_totals[name]["first_seen"] is None or sess["start_time"] < app_totals[name]["first_seen"]:
                app_totals[name]["first_seen"] = sess["start_time"]
            if app_totals[name]["last_seen"] is None or sess["end_time"] > app_totals[name]["last_seen"]:
                app_totals[name]["last_seen"] = sess["end_time"]

        app_summary = sorted(
            [{"app_name": k, **v} for k, v in app_totals.items()], key=lambda x: x["total_seconds"], reverse=True
        )

        # ── Stats ─────────────────────────────────────────────────
        productive_secs = sum(s["total_seconds"] for s in consolidated if s["is_productive"])
        unproductive_secs = sum(s["total_seconds"] for s in consolidated if not s["is_productive"])
        max_dur_secs = max((s["total_seconds"] for s in consolidated), default=1)

        context["app_sessions"] = consolidated  # merged sessions
        context["app_summary"] = app_summary  # per-app totals
        context["selected_employee"] = employee
        context["selected_date"] = selected_date
        context["total_count"] = len(consolidated)  # session count
        context["max_duration_seconds"] = max(max_dur_secs, 1)
        context["productive_total_seconds"] = productive_secs
        context["unproductive_total_seconds"] = unproductive_secs

        # Employee list for switcher
        if is_admin:
            context["employees_list"] = Employee.objects.filter(company=user_employee.company).order_by(
                "user__first_name"
            )
        elif is_manager:
            context["employees_list"] = Employee.objects.filter(manager=self.request.user).order_by("user__first_name")

        return context


@login_required
def download_agent(request):
    """
    Generates a personalized Python agent script with a secure Device Token.
    """
    employee = request.user.employee_profile

    # 1. Get or create a device token for this user
    device, _ = EmployeeDevice.objects.get_or_create(
        employee=employee, device_name=request.META.get("HTTP_USER_AGENT", "Unknown Device")[:255]
    )

    agent_path = os.path.join(os.path.dirname(__file__), "agent_src", "activity_agent.py")
    with open(agent_path, encoding="utf-8") as f:
        content = f.read()

    # Pre-fill data
    server_url = request.build_absolute_uri("/activity-tracking/api/sync/")
    content = content.replace(
        'SERVER_URL = "http://your-hrms-domain.com/activity-tracking/api/sync/"', f'SERVER_URL = "{server_url}"'
    )
    content = content.replace('API_TOKEN = ""', f'API_TOKEN = "{device.token}"')

    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

    if "win" in user_agent:
        filename = "setup_tracker.bat"
        # Absolute URL for the static EXE
        exe_url = request.build_absolute_uri("/static/activity_monitoring/bin/ActivityTracker.exe")

        content = textwrap.dedent(f"""
            @echo off
            setlocal enabledelayedexpansion

            set "APP_NAME=PetaBytz-Tracker"
            set "BASE_DIR=%LOCALAPPDATA%\\%APP_NAME%"
            set "TRACKER_EXE=%BASE_DIR%\\ActivityTracker.exe"
            set "CONFIG_FILE=%BASE_DIR%\\config.json"

            echo ===========================================
            echo    HRMS ACTIVITY TRACKER SETUP
            echo ===========================================

            :: 1. Setup hidden folder
            mkdir "%BASE_DIR%" >nul 2>&1
            attrib +h "%BASE_DIR%"

            :: 2. Download tracker EXE (Much faster than echoing)
            echo Downloading standalone tracker components...
            curl -L -o "%TRACKER_EXE%" "{exe_url}"

            :: 3. Create personalized config
            echo {{"server_url": "{server_url}", "api_token": "{device.token}"}} > "%CONFIG_FILE%"

            :: 4. Setup Persistence (Runs on startup)
            reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "%APP_NAME%" /t REG_SZ /d "\"%TRACKER_EXE%\"" /f >nul

            :: 5. Start Now
            echo Starting tracker...
            start "" "%TRACKER_EXE%"

            echo --------------------------------------------
            echo ✅ TRACKER IS NOW ACTIVE (STANDALONE)
            echo This setup file will now self-delete.
            echo --------------------------------------------

            timeout /t 3 >nul
            start /b "" cmd /c del "%~f0"&exit
        """).strip()
    else:
        # Fallback for others
        filename = "setup_tracker.sh"
        content = "#!/bin/bash\necho 'Unsupported platform' & exit"

    response = HttpResponse(content, content_type="application/x-bat" if "win" in user_agent else "text/plain")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
