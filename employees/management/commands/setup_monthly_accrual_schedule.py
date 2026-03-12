"""
Management command to set up automatic monthly leave accrual schedule.

This creates a periodic task in django-celery-beat that runs hourly
to check if it's the 1st of the month in any employee's timezone.

Usage:
    python manage.py setup_monthly_accrual_schedule
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Set up automatic monthly leave accrual schedule (runs hourly)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Setting up monthly leave accrual schedule..."))

        # Create or get hourly schedule (runs at the start of every hour)
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute="0",  # At minute 0
            hour="*",  # Every hour
            day_of_week="*",  # Every day of week
            day_of_month="*",  # Every day of month
            month_of_year="*",  # Every month
        )

        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created hourly crontab schedule"))
        else:
            self.stdout.write("  Hourly schedule already exists")

        # Create or update the periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name="Monthly Leave Accrual (Automatic)",
            defaults={
                "crontab": schedule,
                "task": "core.tasks.run_monthly_leave_accrual",
                "enabled": True,
            },
        )

        if not created:
            # Update existing task
            task.crontab = schedule
            task.task = "core.tasks.run_monthly_leave_accrual"
            task.enabled = True
            task.save()
            self.stdout.write(self.style.SUCCESS("✓ Updated existing periodic task"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ Created new periodic task"))

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("✅ Monthly Leave Accrual Schedule Setup Complete!"))
        self.stdout.write("=" * 70)
        self.stdout.write("\nSchedule Details:")
        self.stdout.write(f"  • Task Name: {task.name}")
        self.stdout.write("  • Runs: Every hour (at minute 0)")
        self.stdout.write(f"  • Status: {'Enabled' if task.enabled else 'Disabled'}")
        self.stdout.write(f"  • Task Function: {task.task}")
        self.stdout.write("\nHow It Works:")
        self.stdout.write("  1. Task runs every hour")
        self.stdout.write("  2. Checks if it's the 1st of the month in each employee's timezone")
        self.stdout.write("  3. Adds 1 leave per month for employees who completed probation")
        self.stdout.write("  4. Skips employees already accrued for the current month")
        self.stdout.write("\nLeave Allocation Rules:")
        self.stdout.write("  • Petabytz: +1 Sick Leave + 1 Casual Leave")
        self.stdout.write("  • Bluebix/Softstandard: +1 Combined Sick/Casual Leave")
        self.stdout.write("  • Other companies: +1 Sick Leave + 1 Casual Leave")
        self.stdout.write("\nRequirements:")
        self.stdout.write("  • Celery worker must be running")
        self.stdout.write("  • Celery beat must be running")
        self.stdout.write("  • Redis must be running")
        self.stdout.write("\nTo Start Services:")
        self.stdout.write("  celery -A hrms_core worker -l info")
        self.stdout.write("  celery -A hrms_core beat -l info")
        self.stdout.write("\nOr combined (development only):")
        self.stdout.write("  celery -A hrms_core worker --beat -l info")
        self.stdout.write("\n" + "=" * 70 + "\n")
