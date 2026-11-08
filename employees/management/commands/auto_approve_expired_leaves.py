"""
Management command to auto-approve leave requests that have been pending for 60+ days
without manager or admin action.

Usage:
    python manage.py auto_approve_expired_leaves
    python manage.py auto_approve_expired_leaves --days 60
    python manage.py auto_approve_expired_leaves --dry-run
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.tasks import safe_delay, send_leave_approval_notification_task
from employees.models import LeaveRequest

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Auto-approve leave requests pending for 60+ days without manager/admin action"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=60,
            help="Number of days pending before auto-approval (default: 60)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show requests that would be auto-approved without modifying them",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(
            f"Checking for leave requests pending for more than {days} days (created before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})..."
        )

        expired_requests = LeaveRequest.objects.filter(
            status="PENDING",
            created_at__lte=cutoff_date,
        ).select_related("employee", "employee__user")

        count = expired_requests.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS(f"No pending leave requests older than {days} days found."))
            return

        self.stdout.write(f"Found {count} pending leave request(s) eligible for auto-approval.")

        approved_count = 0
        error_count = 0

        for req in expired_requests:
            emp_name = req.employee.user.get_full_name() if req.employee and req.employee.user else "Unknown"
            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would auto-approve Leave #{req.id} for {emp_name} ({req.get_leave_type_display()}, created {req.created_at.strftime('%Y-%m-%d')})"
                )
                approved_count += 1
                continue

            try:
                reason = f"Auto-approved after {days} days with no action from manager/admin"
                result = req.process_auto_approval(
                    user_or_system=None,
                    reason_suffix=reason,
                )

                # Send approval notification email
                safe_delay(send_leave_approval_notification_task, req.id)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [OK] Auto-approved Leave #{req.id} for {emp_name} ({result.get('approval_type')})"
                    )
                )
                logger.info(f"LeaveRequest #{req.id} for {emp_name} auto-approved after {days} days of inactivity.")
                approved_count += 1
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"  [ERROR] Failed to auto-approve Leave #{req.id}: {e}"))
                logger.error(f"Error auto-approving LeaveRequest #{req.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Finished: {approved_count} auto-approved, {error_count} errors."))
