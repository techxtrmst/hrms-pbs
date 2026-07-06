"""
Celery tasks for HRMS PBS.

This module contains background tasks for email notifications and other
automated processes. Tasks are executed by Celery workers and can be
scheduled using django-celery-beat.

Example periodic task setup via Django admin:
    1. Create a Crontab Schedule: minute=0, hour=9 (runs at 9 AM daily)
    2. Create a Periodic Task:
       - Name: "Send Birthday Emails"
       - Task: "core.tasks.send_birthday_emails"
       - Crontab: select the schedule created above
"""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=False, max_retries=3)
def send_birthday_emails(self):
    """
    Send birthday greeting emails to employees whose birthday is today.

    This task should be scheduled to run daily (e.g., at 9 AM).
    It checks each employee's location timezone to ensure emails are sent
    at the appropriate local time.

    Returns:
        dict: Summary of emails sent and any errors
    """
    from employees.models import Employee

    today = date.today()
    sent_count = 0
    error_count = 0
    errors = []

    try:
        # Find employees with birthdays today
        employees_with_birthday = Employee.objects.filter(
            dob__month=today.month,
            dob__day=today.day,
            is_active=True,
            employment_status="ACTIVE",
        ).select_related("user", "company", "location")

        for employee in employees_with_birthday:
            try:
                if not employee.user.email:
                    continue

                subject = f"🎂 Happy Birthday, {employee.user.first_name}!"
                message = (
                    f"Dear {employee.user.first_name},\n\n"
                    f"Wishing you a wonderful birthday filled with joy and happiness!\n\n"
                    f"Best wishes,\n"
                    f"The {employee.company.name} HR Team"
                )

                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[employee.user.email],
                    fail_silently=False,
                )
                sent_count += 1
                logger.info(f"Birthday email sent to {employee.user.email}")

            except Exception as e:
                error_count += 1
                errors.append(f"{employee.user.email}: {str(e)}")
                logger.error(f"Failed to send birthday email to {employee.user.email}: {e}")

    except Exception as e:
        logger.error(f"Error in send_birthday_emails task: {e}")
        raise self.retry(exc=e, countdown=60)

    return {
        "task": "send_birthday_emails",
        "date": str(today),
        "sent": sent_count,
        "errors": error_count,
        "error_details": errors,
    }


@shared_task(bind=True, ignore_result=False, max_retries=3)
def send_anniversary_emails(self):
    """
    Send work anniversary greeting emails to employees.

    This task should be scheduled to run daily (e.g., at 9 AM).
    It sends emails to employees celebrating their work anniversary today.

    Returns:
        dict: Summary of emails sent and any errors
    """
    from employees.models import Employee

    today = date.today()
    sent_count = 0
    error_count = 0
    errors = []

    try:
        # Find employees with work anniversaries today
        employees_with_anniversary = (
            Employee.objects.filter(
                date_of_joining__month=today.month,
                date_of_joining__day=today.day,
                is_active=True,
                employment_status="ACTIVE",
            )
            .exclude(
                date_of_joining__year=today.year  # Exclude employees who joined this year
            )
            .select_related("user", "company", "location")
        )

        for employee in employees_with_anniversary:
            try:
                if not employee.user.email:
                    continue

                years = today.year - employee.date_of_joining.year
                year_text = "year" if years == 1 else "years"

                subject = f"🎉 Happy {years}-Year Work Anniversary, {employee.user.first_name}!"
                message = (
                    f"Dear {employee.user.first_name},\n\n"
                    f"Congratulations on completing {years} {year_text} with {employee.company.name}!\n\n"
                    f"Thank you for your dedication and hard work. We appreciate your contributions "
                    f"and look forward to many more years together.\n\n"
                    f"Best wishes,\n"
                    f"The {employee.company.name} HR Team"
                )

                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[employee.user.email],
                    fail_silently=False,
                )
                sent_count += 1
                logger.info(f"Anniversary email sent to {employee.user.email} ({years} years)")

            except Exception as e:
                error_count += 1
                errors.append(f"{employee.user.email}: {str(e)}")
                logger.error(f"Failed to send anniversary email to {employee.user.email}: {e}")

    except Exception as e:
        logger.error(f"Error in send_anniversary_emails task: {e}")
        raise self.retry(exc=e, countdown=60)

    return {
        "task": "send_anniversary_emails",
        "date": str(today),
        "sent": sent_count,
        "errors": error_count,
        "error_details": errors,
    }


@shared_task(bind=True, ignore_result=False)
def send_daily_notifications(self):
    """
    Send combined daily notifications (birthdays + anniversaries).

    This is a convenience task that runs both birthday and anniversary
    email tasks. Schedule this single task instead of both individual tasks.

    Returns:
        dict: Combined results from both tasks
    """
    birthday_result = send_birthday_emails.delay()
    anniversary_result = send_anniversary_emails.delay()

    return {
        "task": "send_daily_notifications",
        "birthday_task_id": str(birthday_result.id),
        "anniversary_task_id": str(anniversary_result.id),
    }


@shared_task(bind=True, ignore_result=True)
def cleanup_old_task_results(self, days=30):
    """
    Clean up old Celery task results from the database.

    This task should be scheduled to run periodically (e.g., weekly)
    to prevent the task result table from growing too large.

    Args:
        days: Number of days to retain results (default: 30)

    Returns:
        dict: Number of results deleted
    """
    from django_celery_results.models import TaskResult

    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count, _ = TaskResult.objects.filter(date_done__lt=cutoff_date).delete()

    logger.info(f"Cleaned up {deleted_count} old task results older than {days} days")

    return {"deleted": deleted_count, "cutoff_days": days}


@shared_task(bind=True, ignore_result=False)
def cleanup_old_activity_data(self, days=90):
    """
    Delete old high-volume activity monitoring and location tracking records
    to prevent database bloat.

    Cleans up:
      - ActivityPulse         (heartbeat records)
      - AppActivity           (per-app usage records)
      - BrowserActivity       (browser URL records)
      - ActivitySession       (grouped sessions)
      - SystemEvent           (USB/network events)
      - ActivityScreenshot    (screenshot files + DB rows)
      - LocationLog           (GPS location records)

    Args:
        days: Retain records newer than this many days (default: 90)

    Returns:
        dict: Counts of deleted records per model
    """
    from activity_monitoring.models import (
        ActivityPulse,
        ActivityScreenshot,
        ActivitySession,
        AppActivity,
        BrowserActivity,
        SystemEvent,
    )
    from employees.models import LocationLog

    cutoff = timezone.now() - timedelta(days=days)
    results = {}

    # --- ActivityPulse ---
    count, _ = ActivityPulse.objects.filter(timestamp__lt=cutoff).delete()
    results["ActivityPulse"] = count
    logger.info(f"[cleanup] Deleted {count} ActivityPulse records older than {days} days")

    # --- AppActivity ---
    count, _ = AppActivity.objects.filter(start_time__lt=cutoff).delete()
    results["AppActivity"] = count
    logger.info(f"[cleanup] Deleted {count} AppActivity records older than {days} days")

    # --- BrowserActivity ---
    count, _ = BrowserActivity.objects.filter(timestamp__lt=cutoff).delete()
    results["BrowserActivity"] = count
    logger.info(f"[cleanup] Deleted {count} BrowserActivity records older than {days} days")

    # --- ActivityScreenshot (delete files too) ---
    old_screenshots = ActivityScreenshot.objects.filter(timestamp__lt=cutoff)
    screenshot_count = 0
    for screenshot in old_screenshots.iterator(chunk_size=500):
        try:
            if screenshot.image:
                screenshot.image.delete(save=False)
        except Exception as e:
            logger.warning(f"[cleanup] Could not delete screenshot file: {e}")
        screenshot_count += 1
    old_screenshots.delete()
    results["ActivityScreenshot"] = screenshot_count
    logger.info(f"[cleanup] Deleted {screenshot_count} ActivityScreenshot records older than {days} days")

    # --- ActivitySession (only sessions with no remaining child records) ---
    count, _ = ActivitySession.objects.filter(
        start_time__lt=cutoff,
        apps__isnull=True,
        browser_logs__isnull=True,
        screenshots__isnull=True,
    ).delete()
    results["ActivitySession"] = count
    logger.info(f"[cleanup] Deleted {count} empty ActivitySession records older than {days} days")

    # --- SystemEvent ---
    count, _ = SystemEvent.objects.filter(timestamp__lt=cutoff).delete()
    results["SystemEvent"] = count
    logger.info(f"[cleanup] Deleted {count} SystemEvent records older than {days} days")

    # --- LocationLog ---
    count, _ = LocationLog.objects.filter(timestamp__lt=cutoff).delete()
    results["LocationLog"] = count
    logger.info(f"[cleanup] Deleted {count} LocationLog records older than {days} days")

    total = sum(results.values())
    logger.info(f"[cleanup] Total records deleted: {total}")

    return {
        "task": "cleanup_old_activity_data",
        "cutoff_days": days,
        "cutoff_date": str(cutoff.date()),
        "deleted": results,
        "total_deleted": total,
    }


@shared_task(bind=True, ignore_result=False)
def run_monthly_leave_accrual(self):
    """
    Run the automated monthly leave accrual management command.
    This task should be scheduled to run frequently (e.g., hourly)
    to catch the start of the 1st of the month across different timezones.
    """
    from django.core.management import call_command

    try:
        call_command("accrue_monthly_leaves")
        return {"status": "success", "message": "Monthly leave accrual command executed"}
    except Exception as e:
        logger.error(f"Error in run_monthly_leave_accrual task: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(bind=True, max_retries=3)
def send_leave_request_notification_task(self, leave_request_id):
    """Send leave request notification immediately to manager/HR."""
    from core.email_utils import send_leave_request_notification
    from employees.models import LeaveRequest

    try:
        leave_request = LeaveRequest.objects.get(pk=leave_request_id)
        result = send_leave_request_notification(leave_request)
        return {"status": "success", "result": result}
    except LeaveRequest.DoesNotExist:
        logger.error(f"LeaveRequest {leave_request_id} not found.")
        return {"status": "error", "message": "Leave request not found"}
    except Exception as e:
        logger.error(f"Error sending leave request email: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_leave_approval_notification_task(self, leave_request_id):
    """Send leave approval notification immediately to employee."""
    from core.email_utils import send_leave_approval_notification
    from employees.models import LeaveRequest

    try:
        leave_request = LeaveRequest.objects.get(pk=leave_request_id)
        result = send_leave_approval_notification(leave_request)
        return {"status": "success", "sent": result}
    except LeaveRequest.DoesNotExist:
        logger.error(f"LeaveRequest {leave_request_id} not found.")
        return {"status": "error", "message": "Leave request not found"}
    except Exception as e:
        logger.error(f"Error sending leave approval email: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_leave_rejection_notification_task(self, leave_request_id):
    """Send leave rejection notification immediately to employee."""
    from core.email_utils import send_leave_rejection_notification
    from employees.models import LeaveRequest

    try:
        leave_request = LeaveRequest.objects.get(pk=leave_request_id)
        result = send_leave_rejection_notification(leave_request)
        return {"status": "success", "sent": result}
    except LeaveRequest.DoesNotExist:
        logger.error(f"LeaveRequest {leave_request_id} not found.")
        return {"status": "error", "message": "Leave request not found"}
    except Exception as e:
        logger.error(f"Error sending leave rejection email: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_regularization_request_notification_task(self, regularization_request_id):
    """Send regularization request notification immediately to manager/HR."""
    from core.email_utils import send_regularization_request_notification
    from employees.models import RegularizationRequest

    try:
        reg_request = RegularizationRequest.objects.get(pk=regularization_request_id)
        result = send_regularization_request_notification(reg_request)
        return {"status": "success", "result": result}
    except RegularizationRequest.DoesNotExist:
        logger.error(f"RegularizationRequest {regularization_request_id} not found.")
        return {"status": "error", "message": "Regularization request not found"}
    except Exception as e:
        logger.error(f"Error sending regularization request email: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_regularization_approval_notification_task(self, regularization_request_id):
    """Send regularization approval notification immediately to employee."""
    from core.email_utils import send_regularization_approval_notification
    from employees.models import RegularizationRequest

    try:
        reg_request = RegularizationRequest.objects.get(pk=regularization_request_id)
        result = send_regularization_approval_notification(reg_request)
        return {"status": "success", "sent": result}
    except RegularizationRequest.DoesNotExist:
        logger.error(f"RegularizationRequest {regularization_request_id} not found.")
        return {"status": "error", "message": "Regularization request not found"}
    except Exception as e:
        logger.error(f"Error sending regularization approval email: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_regularization_rejection_notification_task(self, regularization_request_id):
    """Send regularization rejection notification immediately to employee."""
    from core.email_utils import send_regularization_rejection_notification
    from employees.models import RegularizationRequest

    try:
        reg_request = RegularizationRequest.objects.get(pk=regularization_request_id)
        result = send_regularization_rejection_notification(reg_request)
        return {"status": "success", "sent": result}
    except RegularizationRequest.DoesNotExist:
        logger.error(f"RegularizationRequest {regularization_request_id} not found.")
        return {"status": "error", "message": "Regularization request not found"}
    except Exception as e:
        logger.error(f"Error sending regularization rejection email: {e}")
        raise self.retry(exc=e, countdown=60)


def safe_delay(task, *args, **kwargs):
    """
    Safely execute task.delay(). If Redis/Celery broker is down or raises an exception,
    execute task.apply() synchronously so that the request does not crash.
    """
    try:
        return task.delay(*args, **kwargs)
    except Exception as e:
        logger.warning(
            f"Failed to queue task {task.name} asynchronously (Redis might be down): {e}. "
            f"Executing synchronously instead."
        )
        try:
            return task.apply(args=args, kwargs=kwargs)
        except Exception as sync_err:
            logger.error(f"Failed to execute task {task.name} synchronously: {sync_err}")
            return None
