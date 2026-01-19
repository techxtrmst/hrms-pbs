"""
Centralized error handling utilities for HRMS.

This module provides decorators and helper functions for consistent
error handling with proper logging via Loguru and PostHog tracking.
"""

from functools import wraps
from typing import Any, Callable, Optional, TypeVar
from loguru import logger
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages

# Import PostHog capture functions
from hrms_core.posthog_config import capture_exception

T = TypeVar("T")


def safe_get_employee_profile(user) -> Optional[Any]:
    """
    Safely get employee profile from user with proper error handling.

    Args:
        user: Django user instance

    Returns:
        Employee instance or None if not found
    """
    try:
        return user.employee_profile
    except AttributeError:
        logger.debug("User has no employee_profile attribute", user_id=user.id)
        return None
    except Exception as e:
        logger.warning(
            "Failed to get employee profile",
            user_id=user.id,
            error=str(e),
            exception_type=type(e).__name__,
        )
        capture_exception(
            e, distinct_id=str(user.id), properties={"action": "get_employee_profile"}
        )
        return None


def safe_queryset_filter(model_class, **filter_kwargs):
    """
    Safely filter a queryset with proper error handling.

    Args:
        model_class: Django model class
        **filter_kwargs: Filter keyword arguments

    Returns:
        Filtered queryset or empty queryset on error
    """
    try:
        return model_class.objects.filter(**filter_kwargs)
    except Exception as e:
        logger.warning(
            "Queryset filter failed",
            model=model_class.__name__,
            filters=str(filter_kwargs),
            error=str(e),
        )
        capture_exception(
            e, properties={"model": model_class.__name__, "action": "queryset_filter"}
        )
        return model_class.objects.none()


def safe_parse_location(loc_str: str) -> tuple[Optional[float], Optional[float]]:
    """
    Safely parse a location string to lat/lng coordinates.

    Args:
        loc_str: Location string in format "lat,lng"

    Returns:
        Tuple of (latitude, longitude) or (None, None) on failure
    """
    if not loc_str:
        return None, None

    try:
        parts = loc_str.strip().split(",")
        if len(parts) != 2:
            logger.debug("Invalid location string format", location=loc_str)
            return None, None
        return float(parts[0].strip()), float(parts[1].strip())
    except (ValueError, AttributeError) as e:
        logger.debug("Failed to parse location string", location=loc_str, error=str(e))
        return None, None


def safe_parse_date(date_str: str, formats: list[str] = None):
    """
    Safely parse a date string with multiple format support.

    Args:
        date_str: Date string to parse
        formats: List of formats to try (default: ["%Y-%m-%d"])

    Returns:
        date object or None on failure
    """
    from datetime import datetime

    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str.date()

    formats = formats or ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue

    # Try ISO format as fallback
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except (ValueError, TypeError, AttributeError):
        pass

    logger.debug("Failed to parse date string", date_str=date_str)
    return None


def safe_parse_datetime(dt_str: str):
    """
    Safely parse a datetime string.

    Args:
        dt_str: Datetime string to parse

    Returns:
        datetime object or None on failure
    """
    from datetime import datetime

    if not dt_str:
        return None

    if isinstance(dt_str, datetime):
        return dt_str

    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug(
            "Failed to parse datetime string", datetime_str=dt_str, error=str(e)
        )
        return None


def handle_view_exception(
    redirect_url: str = "dashboard",
    error_message: str = "An error occurred. Please try again.",
    json_response: bool = False,
):
    """
    Decorator for view functions to handle exceptions consistently.

    Args:
        redirect_url: URL to redirect to on error (for regular views)
        error_message: Message to display to user
        json_response: If True, return JSON error instead of redirect

    Example:
        @handle_view_exception(redirect_url="employee_list")
        def my_view(request):
            # ... view logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                return func(request, *args, **kwargs)
            except Exception as e:
                logger.exception(
                    "View exception",
                    view=func.__name__,
                    user=getattr(request.user, "email", "anonymous"),
                    path=request.path,
                )
                capture_exception(
                    e,
                    distinct_id=str(request.user.id)
                    if request.user.is_authenticated
                    else "anonymous",
                    properties={
                        "view": func.__name__,
                        "path": request.path,
                        "method": request.method,
                    },
                )

                if json_response:
                    return JsonResponse(
                        {"error": error_message, "detail": str(e)},
                        status=500,
                    )

                messages.error(request, error_message)
                return redirect(redirect_url)

        return wrapper

    return decorator


def log_exception(context: str = "", reraise: bool = True):
    """
    Context manager and decorator for logging exceptions.

    Args:
        context: Additional context string for the log
        reraise: Whether to re-raise the exception

    Example:
        with log_exception("processing payment"):
            process_payment()

        @log_exception("data import")
        def import_data():
            ...
    """

    class ExceptionLogger:
        def __init__(self):
            self.context = context
            self.reraise = reraise

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_val is not None:
                logger.exception(
                    f"Exception in {self.context}"
                    if self.context
                    else "Exception occurred",
                    exception_type=exc_type.__name__ if exc_type else "Unknown",
                )
                capture_exception(exc_val, properties={"context": self.context})
                return not self.reraise
            return False

        def __call__(self, func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self:
                    return func(*args, **kwargs)

            return wrapper

    return ExceptionLogger()


def safe_delete(queryset, context: str = ""):
    """
    Safely delete objects from a queryset with logging.

    Args:
        queryset: Django queryset to delete
        context: Context string for logging

    Returns:
        Tuple of (deleted_count, deleted_items_dict) or (0, {}) on error
    """
    try:
        result = queryset.delete()
        logger.debug(
            f"Deleted objects{f' ({context})' if context else ''}", count=result[0]
        )
        return result
    except Exception as e:
        logger.warning(
            f"Failed to delete objects{f' ({context})' if context else ''}",
            error=str(e),
        )
        capture_exception(e, properties={"action": "delete", "context": context})
        return (0, {})


def safe_get_or_none(model_class, **kwargs):
    """
    Safely get a single object or return None.

    Args:
        model_class: Django model class
        **kwargs: Filter arguments

    Returns:
        Model instance or None
    """
    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None
    except Exception as e:
        logger.warning(
            "Error getting object",
            model=model_class.__name__,
            filters=str(kwargs),
            error=str(e),
        )
        capture_exception(
            e, properties={"model": model_class.__name__, "action": "get"}
        )
        return None
