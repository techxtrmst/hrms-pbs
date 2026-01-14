"""
PostHog analytics and error tracking integration.

This module provides:
- PostHog client initialization with exception autocapture
- Django middleware for automatic error capture
- Helper functions for manual event tracking
- User identification and feature flags
"""

import os
from functools import wraps
from typing import Any, Dict

from loguru import logger

# PostHog client instance - initialized lazily
_posthog_client = None


def get_posthog_client():
    """
    Get or create the PostHog client instance.
    
    Returns:
        PostHog client instance or None if not configured
    """
    global _posthog_client
    
    if _posthog_client is not None:
        return _posthog_client
    
    api_key = os.environ.get("POSTHOG_API_KEY")
    
    if not api_key:
        logger.warning("PostHog API key not configured - analytics disabled")
        return None
    
    try:
        from posthog import Posthog
        
        host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")
        debug = os.environ.get("DEBUG", "True").lower() == "true"
        
        _posthog_client = Posthog(
            project_api_key=api_key,
            host=host,
            debug=debug,
            on_error=lambda error: logger.error(f"PostHog error: {error}"),
            # Queue and batching configuration
            max_queue_size=10000,
            flush_at=100,
            flush_interval=0.5,
            # Network configuration
            gzip=True,
            timeout=15,
            max_retries=3,
            # Exception tracking - key feature
            enable_exception_autocapture=True,
            log_captured_exceptions=True,
        )
        
        logger.info("PostHog client initialized successfully", host=host)
        return _posthog_client
        
    except ImportError:
        logger.error("PostHog package not installed")
        return None
    except Exception as e:
        logger.exception("Failed to initialize PostHog client", error=str(e))
        return None


def capture_event(
    event_name: str,
    distinct_id: str = None,
    properties: Dict[str, Any] = None,
):
    """
    Capture a custom event in PostHog.
    
    Args:
        event_name: Name of the event
        distinct_id: User identifier (optional - uses 'anonymous' if not provided)
        properties: Additional event properties
    """
    client = get_posthog_client()
    if not client:
        return
    
    try:
        client.capture(
            distinct_id=distinct_id or "anonymous",
            event=event_name,
            properties=properties or {},
        )
    except Exception as e:
        logger.error(f"Failed to capture PostHog event: {e}", event=event_name)


def capture_exception(
    exception: Exception,
    distinct_id: str = None,
    properties: Dict[str, Any] = None,
):
    """
    Manually capture an exception in PostHog.
    
    Args:
        exception: The exception to capture
        distinct_id: User identifier (optional)
        properties: Additional context properties
    """
    client = get_posthog_client()
    if not client:
        # Still log the exception even if PostHog is not available
        logger.exception("Exception captured (PostHog unavailable)", exception=str(exception))
        return
    
    try:
        client.capture_exception(
            exception,
            distinct_id=distinct_id or "anonymous",
            properties={
                **(properties or {}),
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            },
        )
    except Exception as e:
        logger.error(f"Failed to capture exception in PostHog: {e}")


def identify_user(
    distinct_id: str,
    properties: Dict[str, Any] = None,
):
    """
    Identify a user in PostHog by setting their properties.
    
    Args:
        distinct_id: User identifier
        properties: User properties (name, email, company, etc.)
    """
    client = get_posthog_client()
    if not client:
        return
    
    try:
        # PostHog Python SDK uses set() to set person properties
        client.set(
            distinct_id=distinct_id,
            properties=properties or {},
        )
    except Exception as e:
        logger.error(f"Failed to identify user in PostHog: {e}")


def shutdown_posthog():
    """
    Gracefully shutdown PostHog client.
    
    Should be called when the application is shutting down to flush
    any pending events.
    """
    global _posthog_client
    
    if _posthog_client:
        try:
            _posthog_client.shutdown()
            logger.info("PostHog client shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down PostHog client: {e}")
        finally:
            _posthog_client = None


class PostHogMiddleware:
    """
    Django middleware for PostHog integration.
    
    This middleware:
    - Captures all unhandled exceptions and sends them to PostHog
    - Identifies users on each request
    - Tracks request context for exceptions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Initialize PostHog client on middleware creation
        get_posthog_client()
    
    def __call__(self, request):
        # Add request context for exception capture
        request._posthog_context = self._build_request_context(request)
        
        # Identify user if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            self._identify_request_user(request)
        
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """
        Process unhandled exceptions and send to PostHog.
        
        This is called by Django when an unhandled exception occurs.
        """
        distinct_id = "anonymous"
        properties = getattr(request, '_posthog_context', {})
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            distinct_id = str(request.user.id)
            properties.update({
                "user_email": request.user.email,
                "user_role": getattr(request.user, 'role', 'unknown'),
                "company_id": str(request.user.company_id) if hasattr(request.user, 'company_id') and request.user.company_id else None,
            })
        
        # Log the exception
        logger.exception(
            "Unhandled exception in request",
            path=request.path,
            method=request.method,
            user=distinct_id,
            exception_type=type(exception).__name__,
        )
        
        # Capture in PostHog
        capture_exception(
            exception,
            distinct_id=distinct_id,
            properties=properties,
        )
        
        # Return None to let Django continue with its normal exception handling
        return None
    
    def _build_request_context(self, request) -> Dict[str, Any]:
        """Build context dict from request for exception properties."""
        return {
            "request_path": request.path,
            "request_method": request.method,
            "request_host": request.get_host(),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "ip_address": self._get_client_ip(request),
            "referer": request.META.get("HTTP_REFERER", ""),
        }
    
    def _identify_request_user(self, request):
        """Identify the authenticated user in PostHog."""
        user = request.user
        properties = {
            "email": user.email,
            "name": user.get_full_name() if hasattr(user, 'get_full_name') else str(user),
            "role": getattr(user, 'role', 'unknown'),
        }
        
        if hasattr(user, 'company') and user.company:
            properties["company_id"] = str(user.company.id)
            properties["company_name"] = user.company.name
        
        identify_user(str(user.id), properties)
    
    def _get_client_ip(self, request) -> str:
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


def track_error(error_type: str = None, reraise: bool = True):
    """
    Decorator to track errors in functions and send to PostHog.
    
    Args:
        error_type: Custom error type label
        reraise: Whether to re-raise the exception after capturing
        
    Example:
        @track_error(error_type="payment_processing")
        def process_payment(amount):
            # ... payment logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(
                    f"Error in {func.__name__}",
                    function=func.__name__,
                    error_type=error_type or type(e).__name__,
                )
                capture_exception(
                    e,
                    properties={
                        "function": func.__name__,
                        "error_type": error_type or type(e).__name__,
                        "module": func.__module__,
                    },
                )
                if reraise:
                    raise
        return wrapper
    return decorator
