"""
Utility functions for the observability app.

Provides easy-to-use functions for:
- Capturing exceptions manually
- Adding breadcrumbs
- Setting user context
- Performance profiling
"""

import functools
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from django.http import HttpRequest

from .middleware import capture_exception, capture_message, get_current_request


def capture_error(
    exception: Exception,
    level: str = "error",
    extra: dict = None,
    tags: dict = None,
    request: HttpRequest = None,
):
    """
    Capture an exception that was handled (not raised).

    This is useful for try/except blocks where you catch an error
    but want to track it in observability.

    Args:
        exception: The exception to capture
        level: Log level (error, warning, etc.)
        extra: Additional context data
        tags: Tags for categorization
        request: Optional HTTP request for context

    Example:
        try:
            risky_operation()
        except SomeError as e:
            capture_error(e, extra={"operation": "risky"})
            # Handle gracefully...
    """
    return capture_exception(
        exception=exception,
        request=request,
        level=level,
        extra_context=extra,
        tags=tags,
    )


def log_message(
    message: str,
    level: str = "info",
    logger_name: str = "app",
    extra: dict = None,
):
    """
    Log a message to observability.

    Args:
        message: The message to log
        level: Log level (debug, info, warning, error, critical)
        logger_name: Logger name for categorization
        extra: Additional context data

    Example:
        log_message("User completed checkout", extra={"order_id": 123})
    """
    return capture_message(
        message=message,
        level=level,
        logger_name=logger_name,
        extra=extra,
    )


def observe_function(
    name: str = None,
    capture_args: bool = False,
    capture_result: bool = False,
):
    """
    Decorator to observe a function's execution.

    Captures timing and any exceptions that occur.

    Args:
        name: Optional name for the operation (defaults to function name)
        capture_args: Whether to capture function arguments
        capture_result: Whether to capture function result

    Example:
        @observe_function(name="process_payment")
        def process_payment(amount, user_id):
            ...
    """

    def decorator(func: Callable):
        op_name = name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            extra = {"operation": op_name}

            if capture_args:
                # Capture args (be careful with sensitive data)
                extra["args"] = str(args)[:500]
                extra["kwargs"] = str(kwargs)[:500]

            try:
                result = func(*args, **kwargs)

                duration_ms = (time.perf_counter() - start_time) * 1000
                extra["duration_ms"] = duration_ms

                if capture_result:
                    extra["result"] = str(result)[:500]

                # Log slow operations
                if duration_ms > 1000:
                    log_message(
                        f"Slow operation: {op_name} took {duration_ms:.0f}ms",
                        level="warning",
                        logger_name="performance",
                        extra=extra,
                    )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                extra["duration_ms"] = duration_ms
                capture_error(e, extra=extra, tags={"operation": op_name})
                raise

        return wrapper

    return decorator


@contextmanager
def observe_block(name: str, extra: dict = None):
    """
    Context manager to observe a code block.

    Captures timing and any exceptions.

    Args:
        name: Name for the operation
        extra: Additional context data

    Example:
        with observe_block("process_batch", extra={"batch_size": 100}):
            process_items(batch)
    """
    start_time = time.perf_counter()
    context = {"operation": name, **(extra or {})}

    try:
        yield
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        context["duration_ms"] = duration_ms
        capture_error(e, extra=context)
        raise
    else:
        duration_ms = (time.perf_counter() - start_time) * 1000
        context["duration_ms"] = duration_ms

        # Log slow blocks
        if duration_ms > 1000:
            log_message(
                f"Slow block: {name} took {duration_ms:.0f}ms",
                level="warning",
                logger_name="performance",
                extra=context,
            )


class Breadcrumb:
    """
    Helper for adding breadcrumbs to track user flow.

    Breadcrumbs are stored in thread-local storage and attached
    to any errors that occur.
    """

    _breadcrumbs = []

    @classmethod
    def add(
        cls,
        message: str,
        category: str = "default",
        level: str = "info",
        data: dict = None,
    ):
        """
        Add a breadcrumb.

        Args:
            message: Description of the action
            category: Category for grouping (e.g., "http", "database", "ui")
            level: Level (debug, info, warning, error)
            data: Additional data

        Example:
            Breadcrumb.add("User clicked checkout", category="ui")
            Breadcrumb.add("API call to payment service", category="http", data={"amount": 100})
        """
        import time

        breadcrumb = {
            "timestamp": time.time(),
            "message": message,
            "category": category,
            "level": level,
            "data": data or {},
        }

        # Keep last 50 breadcrumbs
        if len(cls._breadcrumbs) >= 50:
            cls._breadcrumbs.pop(0)

        cls._breadcrumbs.append(breadcrumb)

    @classmethod
    def get_all(cls) -> list:
        """Get all breadcrumbs."""
        return cls._breadcrumbs.copy()

    @classmethod
    def clear(cls):
        """Clear all breadcrumbs."""
        cls._breadcrumbs.clear()


def set_user_context(user_id: str = None, email: str = None, extra: dict = None):
    """
    Set user context for the current request.

    This is useful when you need to set user information outside
    of the normal request flow.

    Args:
        user_id: User identifier
        email: User email
        extra: Additional user data
    """
    request = get_current_request()
    if request:
        if user_id:
            request._observability_user_id = user_id
        if email:
            request._observability_user_email = email
        if extra:
            request._observability_user_extra = extra


def set_tag(key: str, value: Any):
    """
    Set a tag for the current request.

    Tags are searchable in the observability UI.

    Args:
        key: Tag key
        value: Tag value

    Example:
        set_tag("payment_provider", "stripe")
        set_tag("feature_flag", "new_checkout")
    """
    request = get_current_request()
    if request:
        if not hasattr(request, "_observability_tags"):
            request._observability_tags = {}
        request._observability_tags[key] = value


def set_context(key: str, value: dict):
    """
    Set additional context for the current request.

    Context provides extra information for debugging.

    Args:
        key: Context key
        value: Context data (must be a dict)

    Example:
        set_context("order", {"id": 123, "total": 99.99})
    """
    request = get_current_request()
    if request:
        if not hasattr(request, "_observability_context"):
            request._observability_context = {}
        request._observability_context[key] = value
