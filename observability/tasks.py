"""
Celery tasks for the observability app.

Provides periodic tasks for:
- Cleaning up old data
- Aggregating metrics
- System health monitoring
"""

import platform
import statistics
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Avg
from django.utils import timezone
from loguru import logger


@shared_task(name="observability.cleanup_old_data")
def cleanup_old_data():
    """
    Periodic task to clean up old observability data.

    Should be run daily.
    """
    from django.core.management import call_command

    logger.info("Starting observability data cleanup task")
    try:
        call_command("cleanup_observability")
        logger.info("Observability data cleanup completed")
    except Exception as e:
        logger.exception("Failed to clean up observability data", error=str(e))
        raise


@shared_task(name="observability.aggregate_metrics")
def aggregate_metrics():
    """
    Periodic task to aggregate performance metrics.

    Should be run hourly.
    """
    from django.core.management import call_command

    logger.info("Starting metric aggregation task")
    try:
        call_command("aggregate_metrics", "--hours=2")
        logger.info("Metric aggregation completed")
    except Exception as e:
        logger.exception("Failed to aggregate metrics", error=str(e))
        raise


@shared_task(name="observability.aggregate_daily_metrics")
def aggregate_daily_metrics():
    """
    Periodic task to aggregate daily performance metrics.

    Should be run once daily.
    """
    from django.core.management import call_command

    logger.info("Starting daily metric aggregation task")
    try:
        call_command("aggregate_metrics", "--hours=24", "--daily")
        logger.info("Daily metric aggregation completed")
    except Exception as e:
        logger.exception("Failed to aggregate daily metrics", error=str(e))
        raise


@shared_task(name="observability.capture_system_metrics")
def capture_system_metrics():
    """
    Capture system-level metrics.

    Should be run every minute.
    """
    from .models import RequestLog, SystemMetric

    now = timezone.now()
    one_minute_ago = now - timedelta(minutes=1)
    five_minutes_ago = now - timedelta(minutes=5)

    try:
        # Calculate request metrics for the last minute
        recent_requests = RequestLog.objects.filter(timestamp__gte=one_minute_ago)
        requests_per_minute = recent_requests.count()
        errors_per_minute = recent_requests.filter(has_error=True).count()

        # Calculate response time metrics
        response_stats = recent_requests.aggregate(
            avg_response=Avg("duration_ms"),
        )

        # Calculate P95 for response time
        durations = list(recent_requests.values_list("duration_ms", flat=True))
        p95_response = 0
        if len(durations) >= 5:
            p95_response = statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations)
        elif durations:
            p95_response = max(durations)

        # Count active users (unique users in last 5 minutes)
        active_users = (
            RequestLog.objects.filter(timestamp__gte=five_minutes_ago)
            .exclude(user_id="")
            .values("user_id")
            .distinct()
            .count()
        )

        # Try to get memory info (requires psutil)
        memory_used = None
        memory_available = None
        cpu_percent = None

        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_used = memory.used / (1024 * 1024)  # Convert to MB
            memory_available = memory.available / (1024 * 1024)
            cpu_percent = psutil.cpu_percent(interval=None)
        except ImportError:
            pass  # psutil not installed
        except Exception:
            pass  # Error getting system metrics

        # Create system metric record
        SystemMetric.objects.create(
            server_name=platform.node(),
            requests_per_minute=requests_per_minute,
            errors_per_minute=errors_per_minute,
            avg_response_time_ms=response_stats["avg_response"] or 0,
            p95_response_time_ms=p95_response,
            active_users=active_users,
            memory_used_mb=memory_used,
            memory_available_mb=memory_available,
            cpu_percent=cpu_percent,
        )

        logger.debug(
            "System metrics captured",
            requests_per_minute=requests_per_minute,
            errors_per_minute=errors_per_minute,
            active_users=active_users,
        )

    except Exception as e:
        logger.exception("Failed to capture system metrics", error=str(e))
        raise


@shared_task(name="observability.check_error_thresholds")
def check_error_thresholds():
    """
    Check if error rates exceed thresholds and send alerts.

    Should be run every 5 minutes.
    """
    from .models import ErrorLog

    now = timezone.now()
    five_minutes_ago = now - timedelta(minutes=5)

    # Get error count in last 5 minutes
    error_count = ErrorLog.objects.filter(timestamp__gte=five_minutes_ago).count()

    # Get threshold from settings (default: 50 errors in 5 minutes)
    obs_config = getattr(settings, "OBSERVABILITY", {})
    threshold = obs_config.get("ERROR_THRESHOLD", 50)

    if error_count >= threshold:
        logger.warning(
            "Error threshold exceeded",
            error_count=error_count,
            threshold=threshold,
            period_minutes=5,
        )

        # Could integrate with notification system here
        # send_alert_notification(f"High error rate: {error_count} errors in last 5 minutes")

    return error_count
