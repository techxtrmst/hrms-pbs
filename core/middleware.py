import threading
import time
import uuid
import pytz
from django.utils import timezone
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from companies.models import Company
from loguru import logger

_thread_locals = threading.local()


def get_current_company():
    """Get the current company from thread local storage"""
    return getattr(_thread_locals, "company", None)


def get_current_user():
    """Get the current user from thread local storage"""
    return getattr(_thread_locals, "user", None)


class CompanyIsolationMiddleware:
    """
    Multi-tenant middleware that:
    1. Identifies company by domain (e.g., petabytz.com, bluebix.com)
    2. Ensures complete data isolation between companies
    3. Validates user belongs to the correct company
    4. Enforces password change on first login
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def get_company_from_domain(self, request):
        """
        Identify company from the request domain
        Supports both primary domain and allowed domains
        """
        host = request.get_host().split(":")[0]  # Remove port if present

        # Try to find company by primary domain
        try:
            company = Company.objects.filter(
                primary_domain__iexact=host, is_active=True
            ).first()
            if company:
                return company
        except Company.DoesNotExist:
            pass

        # Try to find by allowed domains
        for company in Company.objects.filter(is_active=True):
            if company.is_domain_allowed(host):
                return company

        # For development: if localhost or 127.0.0.1, try to get from user's email domain
        if host in ["localhost", "127.0.0.1"]:
            return None  # Will be determined by user's company

        return None

    def __call__(self, request):
        # Store user in thread locals
        _thread_locals.user = getattr(request, "user", None)

        # Get company from domain
        domain_company = self.get_company_from_domain(request)

        if request.user and request.user.is_authenticated:
            # Import User model to check role
            from accounts.models import User

            # Get current path
            path = request.path_info

            # Skip company validation for:
            # 1. Django admin panel (for superusers)
            # 2. Static/media files
            # 3. SuperAdmin custom portal
            # 4. Account management pages
            if (
                path.startswith("/admin/")
                or path.startswith("/static/")
                or path.startswith("/media/")
                or path.startswith("/superadmin/")
                or path.startswith("/accounts/logout/")
                or path.startswith("/accounts/change-password/")
            ):
                # Still store company info if available
                request.company = request.user.company or domain_company
                _thread_locals.company = request.company

                # Check password change requirement (but EXCLUDE /admin/)
                if (
                    request.user.must_change_password
                    and not path.startswith("/admin/")
                    and not path.startswith("/accounts/logout/")
                    and not path.startswith("/accounts/change-password/")
                    and not path.startswith("/static/")
                    and not path.startswith("/media/")
                ):
                    return redirect("change_password")

                response = self.get_response(request)
                return response

            # Skip company validation for SUPERADMIN users (for non-admin paths)
            is_superadmin = (
                hasattr(request.user, "role")
                and request.user.role == User.Role.SUPERADMIN
            )

            user_company = request.user.company

            # Validate user belongs to the correct company (if domain company is identified)
            if (
                not is_superadmin
                and domain_company
                and user_company
                and domain_company.id != user_company.id
            ):
                # User is trying to access wrong company's domain
                return HttpResponseForbidden(
                    f"Access Denied: You are not authorized to access {domain_company.name}. "
                    f"Please use your company's domain: {user_company.primary_domain}"
                )

            # Set company (prefer user's company for localhost development)
            request.company = user_company or domain_company
            _thread_locals.company = request.company

            # Validate user has a company assigned (skip for SUPERADMIN)
            if not is_superadmin and not request.company:
                return HttpResponseForbidden(
                    "Access Denied: Your account is not associated with any company. "
                    "Please contact your administrator."
                )

            # Force Password Change on First Login
            if (
                request.user.must_change_password
                and not path.startswith("/accounts/logout/")
                and not path.startswith("/accounts/change-password/")
                and not path.startswith("/static/")
                and not path.startswith("/media/")
            ):
                return redirect("change_password")

        else:
            # For unauthenticated users, store domain company for login page customization
            request.company = domain_company
            _thread_locals.company = domain_company

        # Activate User Timezone
        tz_name = "UTC"
        if request.user.is_authenticated:
            # Try employee profile first
            if (
                hasattr(request.user, "employee_profile")
                and request.user.employee_profile.location
                and request.user.employee_profile.location.timezone
            ):
                tz_name = request.user.employee_profile.location.timezone
            # Fallback to Company settings
            elif request.company:
                if request.company.location == "INDIA":
                    tz_name = "Asia/Kolkata"
                elif request.company.location == "US":
                    tz_name = "America/New_York"

        try:
            timezone.activate(pytz.timezone(tz_name))
        except pytz.UnknownTimeZoneError:
            logger.warning("Unknown timezone", timezone=tz_name)

        response = self.get_response(request)
        return response


class LoggingMiddleware:
    """
    Middleware for request/response logging using Loguru.

    Logs:
    - Request start with method, path, user
    - Response with status code and duration
    - Provides request_id for tracing
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id

        # Skip logging for static files and health checks
        if self._should_skip_logging(request.path):
            return self.get_response(request)

        # Get user identifier
        user = "anonymous"
        if hasattr(request, "user") and request.user.is_authenticated:
            user = request.user.email or str(request.user.id)

        # Bind context to logger for this request
        with logger.contextualize(
            request_id=request_id,
            user=user,
            method=request.method,
            path=request.path,
        ):
            start_time = time.time()

            logger.debug(
                "Request started",
                client_ip=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:100],
            )

            try:
                response = self.get_response(request)
            except Exception as e:
                # Log exception and re-raise
                logger.exception(
                    "Request failed with exception",
                    exception_type=type(e).__name__,
                )
                raise

            # Calculate duration
            duration = (time.time() - start_time) * 1000  # ms

            # Log access with status
            log_level = (
                "info"
                if response.status_code < 400
                else "warning"
                if response.status_code < 500
                else "error"
            )

            # Log access entry
            logger.bind(
                access_log=True,
                status=response.status_code,
                duration=f"{duration:.2f}",
            ).log(
                log_level.upper(),
                f"{request.method} {request.path} - {response.status_code}",
            )

            return response

    def _should_skip_logging(self, path: str) -> bool:
        """Check if path should skip logging."""
        skip_prefixes = [
            "/static/",
            "/media/",
            "/favicon.ico",
            "/api/health/",
            "/__debug__/",
        ]
        return any(path.startswith(prefix) for prefix in skip_prefixes)

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
