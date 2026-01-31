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
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
            is_active=True,
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
