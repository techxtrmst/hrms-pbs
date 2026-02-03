"""
Middleware for capturing requests, errors, and performance metrics.

Provides:
- ObservabilityMiddleware: Main middleware for request/error capture
- SQLQueryMiddleware: Captures SQL queries for profiling
"""

import platform
import sys
import threading
import time
import traceback
import uuid
from functools import lru_cache

import django
from django.conf import settings
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.urls import resolve
from django.utils import timezone
from loguru import logger

# Thread-local storage for request context
_thread_locals = threading.local()


def get_current_request_id() -> str | None:
    """Get the current request ID from thread-local storage."""
    return getattr(_thread_locals, "request_id", None)


def get_current_request() -> HttpRequest | None:
    """Get the current request from thread-local storage."""
    return getattr(_thread_locals, "request", None)


@lru_cache(maxsize=1)
def get_server_info() -> dict:
    """Get cached server information."""
    return {
        "server_name": platform.node(),
        "python_version": platform.python_version(),
        "django_version": django.get_version(),
    }


class SQLQueryCapture:
    """Context manager to capture SQL queries."""

    def __init__(self, capture_queries: bool = True, max_queries: int = 100):
        self.capture_queries = capture_queries
        self.max_queries = max_queries
        self.queries = []
        self.start_query_count = 0

    def __enter__(self):
        if self.capture_queries:
            self.start_query_count = len(connection.queries)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.capture_queries:
            end_query_count = len(connection.queries)
            self.queries = connection.queries[self.start_query_count : end_query_count]
            # Limit stored queries
            if len(self.queries) > self.max_queries:
                self.queries = self.queries[: self.max_queries]

    @property
    def query_count(self) -> int:
        return len(self.queries)

    @property
    def total_time_ms(self) -> float:
        return sum(float(q.get("time", 0)) for q in self.queries) * 1000


class ObservabilityMiddleware:
    """
    Main middleware for observability: request logging, error capture, and metrics.

    Features:
    - Assigns unique request ID for tracing
    - Captures request/response details
    - Records timing and performance metrics
    - Captures exceptions with full stack traces
    - Profiles SQL queries (configurable)
    """

    # Paths to skip logging (static files, health checks, etc.)
    SKIP_PATHS = frozenset(
        [
            "/static/",
            "/media/",
            "/favicon.ico",
            "/api/health/",
            "/__debug__/",
            "/observability/api/",  # Avoid recursion
        ]
    )

    # Headers to exclude from logging (sensitive data)
    EXCLUDED_HEADERS = frozenset(
        [
            "authorization",
            "cookie",
            "x-csrftoken",
            "x-api-key",
        ]
    )

    # Content types that can be logged
    LOGGABLE_CONTENT_TYPES = frozenset(
        [
            "application/json",
            "application/x-www-form-urlencoded",
            "text/plain",
            "text/html",
        ]
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self._config = None

    @property
    def config(self) -> dict:
        """Get observability configuration with defaults."""
        if self._config is None:
            self._config = getattr(settings, "OBSERVABILITY", {})
        return self._config

    def should_skip(self, path: str) -> bool:
        """Check if path should skip observability logging."""
        return any(path.startswith(skip) for skip in self.SKIP_PATHS)

    def should_capture_sql(self) -> bool:
        """Check if SQL query capture is enabled."""
        return self.config.get("CAPTURE_SQL_QUERIES", settings.DEBUG)

    def should_log_body(self) -> bool:
        """Check if request/response body logging is enabled."""
        return self.config.get("LOG_REQUEST_BODY", True)

    def get_max_body_size(self) -> int:
        """Get maximum body size to log."""
        return self.config.get("MAX_BODY_SIZE", 10000)  # 10KB default

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:12]
        request.request_id = request_id
        _thread_locals.request_id = request_id
        _thread_locals.request = request

        # Skip observability for certain paths
        if self.should_skip(request.path):
            return self.get_response(request)

        start_time = time.perf_counter()
        error_log = None
        response = None

        # Capture SQL queries if enabled
        with SQLQueryCapture(capture_queries=self.should_capture_sql()) as sql_capture:
            try:
                response = self.get_response(request)
            except Exception as exc:
                # Capture the exception
                error_log = self._capture_exception(request, exc, sql_capture)
                raise

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log the request (async to avoid blocking if possible, or skip if internal)
        try:
            # Check if we should log based on configuration
            if self.config.get("ENABLED", True):
                self._log_request(
                    request=request,
                    response=response,
                    duration_ms=duration_ms,
                    sql_capture=sql_capture,
                    error_log=error_log,
                )
        except Exception as e:
            # Use bind to avoid double logging if already in context
            logger.warning(f"Observability failed to log: {e}")

        return response

    def _get_client_ip(self, request: HttpRequest) -> str | None:
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def _get_user_info(self, request: HttpRequest) -> dict:
        """Extract user information from request."""
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return {
                "user_id": str(user.id),
                "user_email": getattr(user, "email", ""),
            }
        return {"user_id": "", "user_email": ""}

    def _get_company_info(self, request: HttpRequest) -> str:
        """Extract company ID for multi-tenant context."""
        company = getattr(request, "company", None)
        if company:
            return str(company.id)
        return ""

    def _sanitize_headers(self, request: HttpRequest) -> dict:
        """Extract and sanitize headers (remove sensitive data)."""
        headers = {}
        for key, value in request.META.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].lower().replace("_", "-")
                if header_name not in self.EXCLUDED_HEADERS:
                    headers[header_name] = value[:200]  # Truncate long headers
        return headers

    def _get_request_body(self, request: HttpRequest) -> str:
        """Get request body if appropriate."""
        if not self.should_log_body():
            return ""

        content_type = request.content_type or ""
        if not any(ct in content_type for ct in self.LOGGABLE_CONTENT_TYPES):
            return ""

        try:
            body = request.body.decode("utf-8", errors="replace")
            max_size = self.get_max_body_size()
            if len(body) > max_size:
                return body[:max_size] + "... [truncated]"
            return body
        except Exception:
            return ""

    def _get_view_info(self, request: HttpRequest) -> dict:
        """Get view/URL information."""
        try:
            match = resolve(request.path_info)
            return {
                "view_name": match.view_name or "",
                "view_class": (
                    f"{match.func.__module__}.{match.func.__name__}" if hasattr(match.func, "__name__") else ""
                ),
            }
        except Exception:
            return {"view_name": "", "view_class": ""}

    def _log_request(
        self,
        request: HttpRequest,
        response: HttpResponse,
        duration_ms: float,
        sql_capture: SQLQueryCapture,
        error_log=None,
    ):
        """Log request details to the database."""
        from .models import RequestLog

        user_info = self._get_user_info(request)
        view_info = self._get_view_info(request)
        server_info = get_server_info()

        # Prepare SQL query data
        sql_queries = []
        if self.config.get("STORE_SQL_QUERIES", False) and sql_capture.queries:
            sql_queries = [
                {
                    "sql": q["sql"][:1000],  # Truncate long queries
                    "time": float(q.get("time", 0)) * 1000,
                }
                for q in sql_capture.queries[:50]  # Limit stored queries
            ]

        try:
            RequestLog.objects.create(
                request_id=request.request_id,
                method=request.method,
                path=request.path[:2000],
                full_url=request.build_absolute_uri()[:2000],
                query_params=dict(request.GET),
                request_headers=self._sanitize_headers(request),
                request_body=self._get_request_body(request),
                request_content_type=request.content_type or "",
                status_code=response.status_code,
                response_headers=dict(response.headers) if hasattr(response, "headers") else {},
                response_body_size=len(response.content) if hasattr(response, "content") else None,
                user_id=user_info["user_id"],
                user_email=user_info["user_email"],
                user_ip=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                company_id=self._get_company_info(request),
                duration_ms=duration_ms,
                sql_query_count=sql_capture.query_count,
                sql_query_time_ms=sql_capture.total_time_ms,
                sql_queries=sql_queries,
                view_name=view_info["view_name"],
                view_class=view_info["view_class"],
                server_name=server_info["server_name"],
                environment="development" if settings.DEBUG else "production",
                error_log=error_log,
                has_error=response.status_code >= 400,
                timestamp=timezone.now(),
            )
        except Exception as e:
            logger.error(f"Failed to save RequestLog: {e}")

    def _capture_exception(
        self,
        request: HttpRequest,
        exception: Exception,
        sql_capture: SQLQueryCapture,
    ):
        """Capture and store exception details."""
        from .models import ErrorLog

        # Get exception info
        exc_type, exc_value, exc_tb = sys.exc_info()

        # Format traceback
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        traceback_text = "".join(tb_lines)

        # Extract structured frames
        frames = []
        for frame_info in traceback.extract_tb(exc_tb):
            frames.append(
                {
                    "filename": frame_info.filename,
                    "lineno": frame_info.lineno,
                    "function": frame_info.name,
                    "code": frame_info.line,
                }
            )

        # Get culprit (last frame in application code)
        culprit = ""
        filename = ""
        function = ""
        lineno = None

        for frame in reversed(frames):
            # Skip framework/library code
            if "site-packages" not in frame["filename"] and "lib/python" not in frame["filename"]:
                culprit = f"{frame['filename']}:{frame['function']}:{frame['lineno']}"
                filename = frame["filename"]
                function = frame["function"]
                lineno = frame["lineno"]
                break

        if not culprit and frames:
            last_frame = frames[-1]
            culprit = f"{last_frame['filename']}:{last_frame['function']}:{last_frame['lineno']}"
            filename = last_frame["filename"]
            function = last_frame["function"]
            lineno = last_frame["lineno"]

        user_info = self._get_user_info(request)
        server_info = get_server_info()

        try:
            error_log = ErrorLog.objects.create(
                exception_type=exc_type.__name__ if exc_type else "Unknown",
                exception_value=str(exc_value)[:10000] if exc_value else "",
                exception_module=exc_type.__module__ if exc_type else "",
                traceback_text=traceback_text[:50000],  # Limit size
                traceback_frames=frames,
                culprit=culprit[:500],
                filename=filename[:500],
                function=function[:255],
                lineno=lineno,
                request_id=request.request_id,
                request_method=request.method,
                request_path=request.path[:2000],
                request_url=request.build_absolute_uri()[:2000],
                request_query=request.META.get("QUERY_STRING", "")[:2000],
                request_headers=self._sanitize_headers(request),
                request_body=self._get_request_body(request),
                user_id=user_info["user_id"],
                user_email=user_info["user_email"],
                user_ip=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                server_name=server_info["server_name"],
                environment="development" if settings.DEBUG else "production",
                django_version=server_info["django_version"],
                python_version=server_info["python_version"],
                level="error",
                sql_query_count=sql_capture.query_count,
                sql_query_time_ms=sql_capture.total_time_ms,
                timestamp=timezone.now(),
            )
            return error_log
        except Exception as e:
            logger.error(f"Failed to save ErrorLog: {e}")
            return None


def capture_exception(
    exception: Exception,
    request: HttpRequest = None,
    level: str = "error",
    extra_context: dict = None,
    tags: dict = None,
):
    """
    Manually capture an exception.

    Use this function to capture exceptions that are handled (not raised).

    Args:
        exception: The exception to capture
        request: Optional HTTP request for context
        level: Log level (error, warning, etc.)
        extra_context: Additional context data
        tags: Tags for categorization
    """
    from .models import ErrorLog

    exc_type = type(exception)
    exc_tb = exception.__traceback__

    # Format traceback
    tb_lines = traceback.format_exception(exc_type, exception, exc_tb)
    traceback_text = "".join(tb_lines)

    # Extract structured frames
    frames = []
    if exc_tb:
        for frame_info in traceback.extract_tb(exc_tb):
            frames.append(
                {
                    "filename": frame_info.filename,
                    "lineno": frame_info.lineno,
                    "function": frame_info.name,
                    "code": frame_info.line,
                }
            )

    # Get culprit
    culprit = ""
    filename = ""
    function = ""
    lineno = None

    for frame in reversed(frames):
        if "site-packages" not in frame["filename"]:
            culprit = f"{frame['filename']}:{frame['function']}:{frame['lineno']}"
            filename = frame["filename"]
            function = frame["function"]
            lineno = frame["lineno"]
            break

    server_info = get_server_info()

    # Get request from thread-local if not provided
    if request is None:
        request = get_current_request()

    request_data = {}
    user_data = {"user_id": "", "user_email": "", "user_ip": None, "user_agent": ""}

    if request:
        request_data = {
            "request_id": getattr(request, "request_id", ""),
            "request_method": request.method,
            "request_path": request.path[:2000],
            "request_url": request.build_absolute_uri()[:2000],
        }

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            user_data["user_id"] = str(user.id)
            user_data["user_email"] = getattr(user, "email", "")

        user_data["user_ip"] = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
            "REMOTE_ADDR"
        )
        user_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:500]

    try:
        return ErrorLog.objects.create(
            exception_type=exc_type.__name__,
            exception_value=str(exception)[:10000],
            exception_module=exc_type.__module__,
            traceback_text=traceback_text[:50000],
            traceback_frames=frames,
            culprit=culprit[:500],
            filename=filename[:500],
            function=function[:255],
            lineno=lineno,
            **request_data,
            **user_data,
            server_name=server_info["server_name"],
            environment="development" if settings.DEBUG else "production",
            django_version=server_info["django_version"],
            python_version=server_info["python_version"],
            level=level,
            extra_context=extra_context or {},
            tags=tags or {},
            timestamp=timezone.now(),
        )
    except Exception as e:
        logger.error(f"Failed to capture exception: {e}")
        return None


def capture_message(
    message: str,
    level: str = "info",
    logger_name: str = "app",
    extra: dict = None,
    request: HttpRequest = None,
):
    """
    Capture a log message.

    Args:
        message: The message to log
        level: Log level
        logger_name: Logger name for categorization
        extra: Additional context
        request: Optional HTTP request for context
    """
    from .models import LogEntry

    if request is None:
        request = get_current_request()

    request_id = ""
    user_id = ""

    if request:
        request_id = getattr(request, "request_id", "")
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            user_id = str(user.id)

    try:
        return LogEntry.objects.create(
            level=level,
            logger_name=logger_name,
            message=message[:10000],
            request_id=request_id,
            user_id=user_id,
            extra=extra or {},
            timestamp=timezone.now(),
        )
    except Exception as e:
        logger.error(f"Failed to capture message: {e}")
        return None
